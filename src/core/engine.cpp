#include "engine.hpp"

#include <stdexcept>

namespace agentcore {

namespace {
std::int64_t now_ms() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(
        system_clock::now().time_since_epoch()).count();
}
}  // namespace

// ---------- Message ----------

Message Message::make(Role role, std::string content, std::string name) {
    Message m;
    m.role = role;
    m.content = std::move(content);
    m.name = std::move(name);
    m.timestamp_ms = now_ms();
    return m;
}

// ---------- MockProvider ----------

MockProvider::MockProvider(std::string name) : name_(std::move(name)) {}

GenerationResponse MockProvider::generate(const GenerationRequest& req) {
    std::string last_user;
    for (auto it = req.messages.rbegin(); it != req.messages.rend(); ++it) {
        if (it->role == Role::User) { last_user = it->content; break; }
    }
    GenerationResponse r;
    r.content = "[mock:" + name_ + "] " +
                (last_user.empty() ? "(no input)" : last_user);
    r.prompt_tokens     = static_cast<int>(last_user.size() / 4);
    r.completion_tokens = static_cast<int>(r.content.size() / 4);
    return r;
}

void MockProvider::generate_stream(const GenerationRequest& req,
                                   StreamCallback on_chunk) {
    GenerationResponse r = generate(req);
    std::string buf;
    for (char c : r.content) {
        buf += c;
        if (c == ' ') {
            on_chunk(buf);
            buf.clear();
        }
    }
    if (!buf.empty()) on_chunk(buf);
}

// ---------- AgentState ----------

AgentState::AgentState(std::string id) : id_(std::move(id)) {}

void AgentState::append(Message msg) {
    std::unique_lock lock(mtx_);
    messages_.push_back(std::move(msg));
}
std::vector<Message> AgentState::history() const {
    std::shared_lock lock(mtx_);
    return messages_;
}
std::size_t AgentState::size() const {
    std::shared_lock lock(mtx_);
    return messages_.size();
}
void AgentState::clear() {
    std::unique_lock lock(mtx_);
    messages_.clear();
}
void AgentState::set_system_prompt(std::string prompt) {
    std::unique_lock lock(mtx_);
    system_prompt_ = std::move(prompt);
}
std::optional<std::string> AgentState::system_prompt() const {
    std::shared_lock lock(mtx_);
    return system_prompt_;
}
std::vector<Message> AgentState::trimmed(std::size_t max_messages) const {
    std::shared_lock lock(mtx_);
    if (messages_.size() <= max_messages) return messages_;
    return {messages_.end() - max_messages, messages_.end()};
}

// ---------- MemoryCache ----------

MemoryCache::MemoryCache(std::size_t capacity) : capacity_(capacity) {}

void MemoryCache::touch_locked(const std::string& key) {
    auto it = index_.find(key);
    if (it == index_.end()) return;
    order_.splice(order_.begin(), order_, it->second);
}
void MemoryCache::put(const std::string& key, std::string value) {
    std::lock_guard lock(mtx_);
    auto it = index_.find(key);
    if (it != index_.end()) {
        it->second->value = std::move(value);
        touch_locked(key);
        return;
    }
    order_.push_front(Entry{key, std::move(value)});
    index_[key] = order_.begin();
    if (order_.size() > capacity_) {
        index_.erase(order_.back().key);
        order_.pop_back();
    }
}
std::optional<std::string> MemoryCache::get(const std::string& key) {
    std::lock_guard lock(mtx_);
    auto it = index_.find(key);
    if (it == index_.end()) return std::nullopt;
    touch_locked(key);
    return it->second->value;
}
bool MemoryCache::contains(const std::string& key) const {
    std::lock_guard lock(mtx_);
    return index_.count(key) > 0;
}
void MemoryCache::erase(const std::string& key) {
    std::lock_guard lock(mtx_);
    auto it = index_.find(key);
    if (it == index_.end()) return;
    order_.erase(it->second);
    index_.erase(it);
}
void MemoryCache::clear() {
    std::lock_guard lock(mtx_);
    order_.clear();
    index_.clear();
}
std::size_t MemoryCache::size() const {
    std::lock_guard lock(mtx_);
    return order_.size();
}

// ---------- AgentRouter ----------

AgentRouter::AgentRouter() = default;

void AgentRouter::register_agent(const std::string& id) {
    std::unique_lock lock(mtx_);
    known_.insert(id);
    inboxes_.try_emplace(id);
}
void AgentRouter::unregister_agent(const std::string& id) {
    std::unique_lock lock(mtx_);
    known_.erase(id);
    inboxes_.erase(id);
    if (active_ && *active_ == id) active_.reset();
}
bool AgentRouter::has_agent(const std::string& id) const {
    std::shared_lock lock(mtx_);
    return known_.count(id) > 0;
}
std::vector<std::string> AgentRouter::agents() const {
    std::shared_lock lock(mtx_);
    return {known_.begin(), known_.end()};
}
void AgentRouter::send(const std::string& from, const std::string& to,
                       Message msg) {
    std::unique_lock lock(mtx_);
    if (!known_.count(to)) throw std::runtime_error("unknown recipient: " + to);
    inboxes_[to].push_back(RoutedMessage{from, to, std::move(msg)});
}
std::vector<RoutedMessage> AgentRouter::drain(const std::string& id) {
    std::unique_lock lock(mtx_);
    auto it = inboxes_.find(id);
    if (it == inboxes_.end()) return {};
    std::vector<RoutedMessage> out;
    out.swap(it->second);
    return out;
}
bool AgentRouter::handoff(const std::string& from, const std::string& to,
                          std::optional<Message> seed) {
    std::unique_lock lock(mtx_);
    if (!known_.count(from) || !known_.count(to)) return false;
    if (seed) inboxes_[to].push_back(RoutedMessage{from, to, std::move(*seed)});
    active_ = to;
    return true;
}
std::optional<std::string> AgentRouter::active() const {
    std::shared_lock lock(mtx_);
    return active_;
}
void AgentRouter::set_active(const std::string& id) {
    std::unique_lock lock(mtx_);
    if (!known_.count(id)) throw std::runtime_error("unknown agent: " + id);
    active_ = id;
}

// ---------- ToolRegistry ----------

void ToolRegistry::register_tool(ToolSpec spec) {
    std::unique_lock lock(mtx_);
    tools_[spec.name] = std::move(spec);
}
bool ToolRegistry::has(const std::string& name) const {
    std::shared_lock lock(mtx_);
    return tools_.count(name) > 0;
}
std::vector<std::string> ToolRegistry::names() const {
    std::shared_lock lock(mtx_);
    std::vector<std::string> out;
    out.reserve(tools_.size());
    for (const auto& [k, _] : tools_) out.push_back(k);
    return out;
}
std::string ToolRegistry::description(const std::string& name) const {
    std::shared_lock lock(mtx_);
    auto it = tools_.find(name);
    return it == tools_.end() ? "" : it->second.description;
}
std::string ToolRegistry::schema(const std::string& name) const {
    std::shared_lock lock(mtx_);
    auto it = tools_.find(name);
    return it == tools_.end() ? "" : it->second.schema_json;
}
std::string ToolRegistry::invoke(const std::string& name,
                                 const std::string& args_json) const {
    // Copy fn out under lock; invoke without holding it. Tools may
    // be slow (network, IO) and we don't want to block other lookups.
    ToolFn fn;
    {
        std::shared_lock lock(mtx_);
        auto it = tools_.find(name);
        if (it == tools_.end())
            throw std::runtime_error("unknown tool: " + name);
        fn = it->second.fn;
    }
    return fn(args_json);
}
void ToolRegistry::clear() {
    std::unique_lock lock(mtx_);
    tools_.clear();
}

// ---------- Engine ----------

Engine::Engine() = default;

std::shared_ptr<AgentState> Engine::create_agent(const std::string& id) {
    // Hold the engine lock across router.register_agent so no other
    // thread can observe an agent in the engine map before the router
    // knows about it — without this, a concurrent send() could fail
    // with "unknown recipient" right after create_agent returned.
    // Safe because AgentRouter never calls back into Engine (no
    // inverse lock order → no deadlock risk).
    std::unique_lock lock(mtx_);
    auto [it, inserted] = agents_.try_emplace(id);
    if (inserted) it->second = std::make_shared<AgentState>(id);
    router_.register_agent(id);
    return it->second;
}
std::shared_ptr<AgentState> Engine::agent(const std::string& id) const {
    std::shared_lock lock(mtx_);
    auto it = agents_.find(id);
    return it == agents_.end() ? nullptr : it->second;
}

}  // namespace agentcore
