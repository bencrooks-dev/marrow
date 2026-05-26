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

    py::class_<Provider, PyProvider, std::shared_ptr<Provider>>(m, "Provider")
        .def(py::init<>())
        .def("name",     &Provider::name)
        .def("generate", &Provider::generate);

    py::class_<MockProvider, Provider, std::shared_ptr<MockProvider>>(m, "MockProvider")
        .def(py::init<std::string>(), py::arg("name") = "mock")
        .def("name",     &MockProvider::name)
        .def("generate", &MockProvider::generate,
             py::call_guard<py::gil_scoped_release>());

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
                 ToolFn wrapped = [fn = std::move(fn)](const std::string& args) -> std::string {
                     py::gil_scoped_acquire gil;
                     py::object result = fn(args);
                     return py::cast<std::string>(result);
                 };
                 self.register_tool(ToolSpec{
                     std::move(name), std::move(description),
                     std::move(schema), std::move(wrapped)});
             },
             py::arg("name"), py::arg("description") = "",
             py::arg("schema") = "{}", py::arg("fn"))
        .def("invoke", &ToolRegistry::invoke,
             py::call_guard<py::gil_scoped_release>(),
             py::arg("name"), py::arg("args_json"));

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
