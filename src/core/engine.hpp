// agentcore — lightweight C++ core for AI agent orchestration.
// PoC. Not production-ready. See docs/design-notes.md.
#pragma once

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

namespace agentcore {

// ---------- Message ----------

enum class Role : std::uint8_t { System, User, Assistant, Tool };

struct Message {
    Role role = Role::User;
    std::string content;
    std::string name;
    std::int64_t timestamp_ms = 0;
    std::unordered_map<std::string, std::string> metadata;

    static Message make(Role role, std::string content, std::string name = "");
};

// ---------- Provider ----------

struct GenerationRequest {
    std::string model;
    std::vector<Message> messages;
    double temperature = 0.7;
    int max_tokens = 1024;
};

struct GenerationResponse {
    std::string content;
    int prompt_tokens = 0;
    int completion_tokens = 0;
};

class Provider {
public:
    virtual ~Provider() = default;
    virtual std::string name() const = 0;
    virtual GenerationResponse generate(const GenerationRequest& req) = 0;
};

class MockProvider : public Provider {
public:
    explicit MockProvider(std::string name = "mock");
    std::string name() const override { return name_; }
    GenerationResponse generate(const GenerationRequest& req) override;
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

class AgentRouter {
public:
    AgentRouter();

    void register_agent(const std::string& agent_id);
    void unregister_agent(const std::string& agent_id);
    bool has_agent(const std::string& agent_id) const;
    std::vector<std::string> agents() const;

    void send(const std::string& from, const std::string& to, Message msg);
    std::vector<RoutedMessage> drain(const std::string& agent_id);

    bool handoff(const std::string& from, const std::string& to,
                 std::optional<Message> seed);

    std::optional<std::string> active() const;
    void set_active(const std::string& agent_id);

private:
    mutable std::shared_mutex mtx_;
    std::unordered_set<std::string> known_;
    std::unordered_map<std::string, std::vector<RoutedMessage>> inboxes_;
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

private:
    mutable std::shared_mutex mtx_;
    std::unordered_map<std::string, std::shared_ptr<AgentState>> agents_;
    AgentRouter router_;
    MemoryCache cache_;
    ToolRegistry tools_;
};

}  // namespace agentcore
