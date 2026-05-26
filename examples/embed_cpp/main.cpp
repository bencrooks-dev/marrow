// Pure-C++ usage of the agentcore engine — no Python involved.
//
// Proves the README claim that the core is embeddable from C++: the
// libagentcore_core.a static library can be linked directly into a
// C++ application that wants the agent primitives (state, history,
// router, cache, tool registry) without the Python interpreter.
//
// Build:
//
//     mkdir build && cd build
//     cmake .. && cmake --build .
//     ./agentcore_embed_demo

#include <iostream>
#include <string>

#include "engine.hpp"

using namespace agentcore;

int main() {
    Engine engine;

    auto researcher = engine.create_agent("researcher");
    auto writer     = engine.create_agent("writer");

    researcher->set_system_prompt("Research a topic and return bullets.");
    writer->set_system_prompt("Write a paragraph from bullets.");

    researcher->append(Message::make(Role::User, "Three facts about graph DBs."));

    // Drive a mock provider directly — no Python wrapping needed.
    MockProvider provider("embedded");
    GenerationRequest req;
    req.model = "mock";
    req.messages = researcher->history();
    auto resp = provider.generate(req);
    researcher->append(Message::make(Role::Assistant, resp.content, "researcher"));

    std::cout << "[researcher] " << resp.content << "\n";

    // Hand off via the router and verify the writer received it.
    engine.router().handoff(
        "researcher", "writer",
        Message::make(Role::User, resp.content, "researcher"));

    for (auto& routed : engine.router().drain("writer")) {
        writer->append(routed.message);
    }

    req.messages = writer->history();
    auto essay = provider.generate(req);
    writer->append(Message::make(Role::Assistant, essay.content, "writer"));

    std::cout << "[writer]     " << essay.content << "\n";
    std::cout << "writer.history()  = " << writer->size() << " messages\n";
    std::cout << "router.active() = "
              << engine.router().active().value_or("<none>") << "\n";

    // Tools also work without Python — register a plain C++ lambda.
    engine.tools().register_tool(ToolSpec{
        "add", "Add two ints", "{}",
        [](const std::string& args) -> std::string {
            (void)args;  // demo: real impl would parse JSON
            return R"({"ok": true, "result": 42})";
        }});
    std::cout << "tool result: " << engine.tools().invoke("add", "{}") << "\n";

    return 0;
}
