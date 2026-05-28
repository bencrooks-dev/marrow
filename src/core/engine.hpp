// marrow — lightweight C++ core for AI agent orchestration.
// PoC. Not production-ready. See docs/design-notes.md.
#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <shared_mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace marrow {

// ---------- Message ----------

enum class Role : std::uint8_t { System, User, Assistant, Tool };

struct Message {
    Role role = Role::User;
    std::string content;
    std::string name;
    std::int64_t timestamp_ms = 0;
    std::unordered_map<std::string, std::string> metadata;

    // Hard cap on content size. A 4 MiB ceiling fits the largest LLM
    // outputs comfortably while blocking the OOM-via-runaway-tool case.
    // Callers needing larger bodies should chunk or store-and-reference.
    static constexpr std::size_t kMaxContentBytes = 4 * 1024 * 1024;

    static Message make(Role role, std::string content, std::string name = "");
};

// ---------- Cancellation ----------

// A simple cooperative cancellation flag. Pass via GenerationRequest;
// providers and long-running tools should check `cancelled()` at
// natural yield points.
class CancelToken {
public:
    void cancel() noexcept;
    void reset() noexcept;
    bool cancelled() const noexcept;
private:
    std::atomic<bool> cancelled_{false};
};

// ---------- Provider ----------

struct GenerationRequest {
    std::string model;
    std::vector<Message> messages;
    double temperature = 0.7;
    int max_tokens = 1024;
    // Wall-clock timeout in milliseconds. 0 disables the timeout.
    // Providers MAY honor this; implementations that ignore it should
    // be wrapped by the AsyncRuntime which enforces it externally.
    int timeout_ms = 0;
    // Optional cancellation token. nullptr disables cancellation.
    std::shared_ptr<CancelToken> cancel_token;
};

struct GenerationResponse {
    std::string content;
    int prompt_tokens = 0;
    int completion_tokens = 0;
};

// Token callback for streaming. Invoked once per chunk; whole content
// can be reconstructed by concatenating chunks.
using StreamCallback = std::function<void(const std::string&)>;

class Provider {
public:
    virtual ~Provider() = default;
    virtual std::string name() const = 0;
    virtual GenerationResponse generate(const GenerationRequest& req) = 0;

    // Default: call generate and emit content as a single chunk. Real
    // streaming providers (OpenAI/Anthropic SSE) override this.
    virtual void generate_stream(const GenerationRequest& req,
                                 StreamCallback on_chunk) {
        GenerationResponse r = generate(req);
        on_chunk(r.content);
    }
};

class MockProvider : public Provider {
public:
    explicit MockProvider(std::string name = "mock");
    std::string name() const override { return name_; }
    GenerationResponse generate(const GenerationRequest& req) override;
    // Splits the mock response into word-sized chunks so streaming
    // demos and tests have something visible to consume.
    void generate_stream(const GenerationRequest& req,
                         StreamCallback on_chunk) override;
private:
    std::string name_;
};

// ---------- AgentState ----------

class AgentState {
public:
    explicit AgentState(std::string agent_id);
    const std::string& id() const noexcept { return id_; }

    void append(Message msg);
    std::vector<Message> history() const;
    std::size_t size() const;
    void clear();

    void set_system_prompt(std::string prompt);
    std::optional<std::string> system_prompt() const;

    std::vector<Message> trimmed(std::size_t max_messages) const;

private:
    const std::string id_;
    mutable std::shared_mutex mtx_;
    std::optional<std::string> system_prompt_;
    std::vector<Message> messages_;
};

// ---------- MemoryCache ----------

class MemoryCache {
public:
    explicit MemoryCache(std::size_t capacity = 1024);

    void put(const std::string& key, std::string value);
    std::optional<std::string> get(const std::string& key);
    bool contains(const std::string& key) const;
    void erase(const std::string& key);
    void clear();
    std::size_t size() const;

private:
    struct Entry { std::string key; std::string value; };
    void touch_locked(const std::string& key);

    std::size_t capacity_;
    mutable std::mutex mtx_;
    std::list<Entry> order_;
    std::unordered_map<std::string, std::list<Entry>::iterator> index_;
};

// ---------- AgentRouter ----------

struct RoutedMessage {
    std::string from;
    std::string to;
    Message message;
};

// What happens when a send() targets a full inbox.
enum class OverflowPolicy : std::uint8_t {
    Reject = 0,    // throw — backpressure surfaced to the producer
    DropOldest,    // evict the oldest pending message
    DropNewest,    // silently drop the new message
};

class AgentRouter {
public:
    AgentRouter();

    void register_agent(const std::string& agent_id);
    void unregister_agent(const std::string& agent_id);
    bool has_agent(const std::string& agent_id) const;
    std::vector<std::string> agents() const;

    // Set an inbox size cap and overflow behavior for one agent.
    // max_size == 0 disables the cap (default).
    void set_inbox_limit(const std::string& agent_id,
                         std::size_t max_size,
                         OverflowPolicy policy = OverflowPolicy::Reject);
    std::size_t inbox_size(const std::string& agent_id) const;

    void send(const std::string& from, const std::string& to, Message msg);
    std::vector<RoutedMessage> drain(const std::string& agent_id);

    bool handoff(const std::string& from, const std::string& to,
                 std::optional<Message> seed);

    std::optional<std::string> active() const;
    void set_active(const std::string& agent_id);

private:
    struct InboxConfig {
        std::size_t max = 0;
        OverflowPolicy policy = OverflowPolicy::Reject;
    };
    mutable std::shared_mutex mtx_;
    std::unordered_set<std::string> known_;
    std::unordered_map<std::string, std::vector<RoutedMessage>> inboxes_;
    std::unordered_map<std::string, InboxConfig> inbox_config_;
    std::optional<std::string> active_;
};

// ---------- ToolRegistry ----------
//
// Stores tools as type-erased std::function<string(string)> — JSON in,
// JSON out. The core stays pure C++. The Python binding wraps a
// py::function into this signature so Python tools "just work" while
// the registry and dispatch remain in C++.

using ToolFn = std::function<std::string(const std::string&)>;

struct ToolSpec {
    std::string name;
    std::string description;
    std::string schema_json;
    ToolFn fn;
};

class ToolRegistry {
public:
    void register_tool(ToolSpec spec);
    bool has(const std::string& name) const;
    std::vector<std::string> names() const;

    std::string description(const std::string& name) const;
    std::string schema(const std::string& name) const;

    // Throws std::runtime_error if name is unknown.
    std::string invoke(const std::string& name, const std::string& args_json) const;

    void clear();

private:
    mutable std::shared_mutex mtx_;
    std::unordered_map<std::string, ToolSpec> tools_;
};

// ---------- Engine ----------

class Engine {
public:
    Engine();

    std::shared_ptr<AgentState> create_agent(const std::string& id);
    std::shared_ptr<AgentState> agent(const std::string& id) const;

    AgentRouter& router() noexcept { return router_; }
    MemoryCache& cache() noexcept { return cache_; }
    ToolRegistry& tools() noexcept { return tools_; }

    // Signal that no new top-level work should start. Callers (especially
    // AsyncRuntime) should consult is_shutdown() before scheduling new
    // operations. Public mutating methods that take ownership of new
    // resources check this flag at entry and throw if set.
    void shutdown() noexcept;
    bool is_shutdown() const noexcept;

private:
    mutable std::shared_mutex mtx_;
    std::unordered_map<std::string, std::shared_ptr<AgentState>> agents_;
    AgentRouter router_;
    MemoryCache cache_;
    ToolRegistry tools_;
    std::atomic<bool> shutdown_{false};
};

}  // namespace marrow
