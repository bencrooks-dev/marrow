# agentcore

**A lightweight C++ core for AI agent orchestration, exposed to Python via Pybind11.**

`agentcore` runs the performance-sensitive parts of multi-agent systems — message state, history, routing, tool dispatch — in native C++17 with `std::shared_mutex` for read-heavy workloads. The developer-facing API stays in clean, ergonomic Python.

It is a deliberate alternative to Python-heavy frameworks like LangGraph, CrewAI, and AutoGen for use cases where the orchestration layer is the bottleneck — high agent counts, large histories, hot tool dispatch, or embedding the agent runtime into a C++ application.

!!! warning "Pre-alpha"
    The public API is stable as documented in [the stability policy](stability.md), but the library has not yet been through an extended production deployment. Treat 0.x.y as a green-light to experiment, a yellow-light for prototype, and a red-light for mission-critical systems.

## Why agentcore

- **Native hot path.** Per-step state ops are in C++ and run with the GIL released so threaded provider calls scale.
- **Tiny dependency footprint.** Core requires only Pybind11. Real providers are opt-in extras.
- **Streaming + tools + graphs out of the box.** Every provider implements the same `generate` and `generate_stream` interface; tools dispatch through a C++ registry; graphs are fluent Python.
- **Embeddable.** The C++ core compiles as a static library independent of Pybind11. There's a [working pure-C++ demo](https://github.com/bencrooks-dev/agentcore/tree/main/examples/embed_cpp) in the repo.

## A 30-second example

```python
from agentcore import Agent, Runtime, MockProvider

rt = Runtime()
provider = MockProvider()

researcher = rt.add(Agent("researcher", provider, system_prompt="Research a topic."))
writer     = rt.add(Agent("writer",     provider, system_prompt="Write a paragraph."))

researcher.append_user("Find three facts about graph databases.")
findings = researcher.step()

rt.handoff(frm="researcher", to="writer", text=findings)
rt.deliver(writer)
print(writer.step())
```

## Next steps

- [Getting started](getting-started.md) — install, run the examples, understand the layout.
- [Architecture](architecture.md) — what lives in C++ vs Python and why.
- [Production checklist](stability.md) — what's stable, what's not, deprecation flow.
- [Roadmap](roadmap.md) — what's coming.
