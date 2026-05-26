// Pybind11 bindings for agentcore.
//
// Provider is exposed as a base class with a trampoline (PyProvider)
// so Python can subclass it and have C++ call back into Python.
//
// Tools registered from Python are wrapped into a std::function<string(string)>;
// the captured py::function is held until the registry is cleared / engine
// destructs (both happen with the GIL held).

#include "engine.hpp"

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace agentcore;

// Trampoline so Python can subclass Provider.
class PyProvider : public Provider {
public:
    using Provider::Provider;
    std::string name() const override {
        PYBIND11_OVERRIDE_PURE(std::string, Provider, name);
    }
    GenerationResponse generate(const GenerationRequest& req) override {
        PYBIND11_OVERRIDE_PURE(GenerationResponse, Provider, generate, req);
    }
    void generate_stream(const GenerationRequest& req,
                         StreamCallback on_chunk) override {
        PYBIND11_OVERRIDE(void, Provider, generate_stream, req, on_chunk);
    }
};

PYBIND11_MODULE(_agentcore, m) {
    m.doc() = "agentcore — C++ engine for lightweight agent orchestration";

    py::enum_<Role>(m, "Role")
        .value("System",    Role::System)
        .value("User",      Role::User)
        .value("Assistant", Role::Assistant)
        .value("Tool",      Role::Tool);

    py::class_<Message>(m, "Message")
        .def(py::init<>())
        .def_static("make", &Message::make,
                    py::arg("role"), py::arg("content"), py::arg("name") = "")
        .def_readwrite("role",         &Message::role)
        .def_readwrite("content",      &Message::content)
        .def_readwrite("name",         &Message::name)
        .def_readwrite("timestamp_ms", &Message::timestamp_ms)
        .def_readwrite("metadata",     &Message::metadata)
        .def("__repr__", [](const Message& m) {
            return "<Message role=" + std::to_string(static_cast<int>(m.role)) +
                   " name='" + m.name + "' content='" +
                   (m.content.size() > 60 ? m.content.substr(0, 57) + "..." : m.content) +
                   "'>";
        });

    py::class_<GenerationRequest>(m, "GenerationRequest")
        .def(py::init<>())
        .def_readwrite("model",       &GenerationRequest::model)
        .def_readwrite("messages",    &GenerationRequest::messages)
        .def_readwrite("temperature", &GenerationRequest::temperature)
        .def_readwrite("max_tokens",  &GenerationRequest::max_tokens);

    py::class_<GenerationResponse>(m, "GenerationResponse")
        .def(py::init<>())
        .def_readwrite("content",           &GenerationResponse::content)
        .def_readwrite("prompt_tokens",     &GenerationResponse::prompt_tokens)
        .def_readwrite("completion_tokens", &GenerationResponse::completion_tokens);

    // call_guard releases the GIL during generate/generate_stream so other
    // Python threads can make progress. The PYBIND11_OVERRIDE_* macros in
    // the PyProvider trampoline re-acquire the GIL when calling back into
    // Python — this is required for correctness when a Python subclass
    // (OpenAIProvider, AnthropicProvider, etc.) is invoked from a worker
    // thread via AsyncRuntime.
    py::class_<Provider, PyProvider, std::shared_ptr<Provider>>(m, "Provider")
        .def(py::init<>())
        .def("name",            &Provider::name)
        .def("generate",        &Provider::generate,
             py::call_guard<py::gil_scoped_release>())
        .def("generate_stream", &Provider::generate_stream,
             py::call_guard<py::gil_scoped_release>(),
             py::arg("req"), py::arg("on_chunk"));

    py::class_<MockProvider, Provider, std::shared_ptr<MockProvider>>(m, "MockProvider")
        .def(py::init<std::string>(), py::arg("name") = "mock")
        .def("name",            &MockProvider::name)
        .def("generate",        &MockProvider::generate,
             py::call_guard<py::gil_scoped_release>())
        .def("generate_stream", &MockProvider::generate_stream,
             py::call_guard<py::gil_scoped_release>(),
             py::arg("req"), py::arg("on_chunk"));

    py::class_<AgentState, std::shared_ptr<AgentState>>(m, "AgentState")
        .def_property_readonly("id", &AgentState::id)
        .def("append",            &AgentState::append)
        .def("history",           &AgentState::history)
        .def("size",              &AgentState::size)
        .def("clear",             &AgentState::clear)
        .def("set_system_prompt", &AgentState::set_system_prompt)
        .def("system_prompt",     &AgentState::system_prompt)
        .def("trimmed",           &AgentState::trimmed, py::arg("max_messages"));

    py::class_<MemoryCache>(m, "MemoryCache")
        .def(py::init<std::size_t>(), py::arg("capacity") = 1024)
        .def("put",      &MemoryCache::put)
        .def("get",      &MemoryCache::get)
        .def("contains", &MemoryCache::contains)
        .def("erase",    &MemoryCache::erase)
        .def("clear",    &MemoryCache::clear)
        .def("size",     &MemoryCache::size);

    py::class_<RoutedMessage>(m, "RoutedMessage")
        .def_readwrite("from_",   &RoutedMessage::from)
        .def_readwrite("to",      &RoutedMessage::to)
        .def_readwrite("message", &RoutedMessage::message);

    py::class_<AgentRouter>(m, "AgentRouter")
        .def("register_agent",   &AgentRouter::register_agent)
        .def("unregister_agent", &AgentRouter::unregister_agent)
        .def("has_agent",        &AgentRouter::has_agent)
        .def("agents",           &AgentRouter::agents)
        .def("send",             &AgentRouter::send,
             py::arg("from"), py::arg("to"), py::arg("msg"))
        .def("drain",            &AgentRouter::drain)
        .def("handoff",          &AgentRouter::handoff,
             py::arg("from"), py::arg("to"), py::arg("seed") = std::nullopt)
        .def("active",           &AgentRouter::active)
        .def("set_active",       &AgentRouter::set_active);

    py::class_<ToolRegistry>(m, "ToolRegistry")
        .def("has",         &ToolRegistry::has)
        .def("names",       &ToolRegistry::names)
        .def("description", &ToolRegistry::description)
        .def("schema",      &ToolRegistry::schema)
        .def("clear",       &ToolRegistry::clear)
        .def("register",
             [](ToolRegistry& self, std::string name, std::string description,
                std::string schema, py::function fn) {
                 // Hold the py::function in a shared_ptr whose deleter
                 // acquires the GIL. This makes the captured function
                 // safe to destruct from any thread (including a worker
                 // thread that doesn't hold the GIL, or interpreter
                 // shutdown). Copying the lambda copies the shared_ptr
                 // (atomic refcount, no GIL required), not the py::function.
                 auto fn_holder = std::shared_ptr<py::function>(
                     new py::function(std::move(fn)),
                     [](py::function* p) {
                         py::gil_scoped_acquire gil;
                         delete p;
                     });
                 ToolFn wrapped =
                     [fn_holder = std::move(fn_holder)](const std::string& args) -> std::string {
                         py::gil_scoped_acquire gil;
                         py::object result = (*fn_holder)(args);
                         return py::cast<std::string>(result);
                     };
                 self.register_tool(ToolSpec{
                     std::move(name), std::move(description),
                     std::move(schema), std::move(wrapped)});
             },
             py::arg("name"), py::arg("description") = "",
             py::arg("schema") = "{}", py::arg("fn"))
        // NOTE: no gil_scoped_release here.
        // Tools registered from Python are stored as std::function objects
        // that capture a py::function by value. Copying the std::function
        // (which `invoke` does to release the registry lock before calling)
        // copies the captured py::function, which increments a PyObject
        // refcount — that operation requires the GIL. Tools run Python
        // bodies anyway, so releasing/re-acquiring would save nothing.
        .def("invoke", &ToolRegistry::invoke,
             py::arg("name"), py::arg("args_json"));

    // reference_internal returns by reference and keeps the Engine alive
    // for as long as the returned handle is alive — defends against
    // `r = engine.router; del engine; r.send(...)` use-after-free.
    py::class_<Engine>(m, "Engine")
        .def(py::init<>())
        .def("create_agent", &Engine::create_agent)
        .def("agent",        &Engine::agent)
        .def_property_readonly("router", &Engine::router,
                               py::return_value_policy::reference_internal)
        .def_property_readonly("cache",  &Engine::cache,
                               py::return_value_policy::reference_internal)
        .def_property_readonly("tools",  &Engine::tools,
                               py::return_value_policy::reference_internal);
}
