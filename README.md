# agentcore

A lightweight C++ core for AI agent orchestration, exposed to Python via Pybind11.

Designed as a high-performance, ultra-thin alternative to Python-heavy frameworks (LangGraph, CrewAI, AutoGen). The hot path — state, history, cache, routing, tool dispatch — runs in native C++. The ergonomic API is in Python.

> **Status: pre-alpha proof-of-concept.** Not production ready. APIs will change.

## What's in C++

- `Message`, `AgentState` — message history with `shared_mutex`-based read/write
- `MemoryCache` — bounded LRU, thread-safe
- `AgentRouter` — agent registry, inboxes, handoff
- `ToolRegistry` — type-erased tool dispatch (`std::function<string(string)>`)
- `Provider` interface with `MockProvider` for tests
- `Engine` — top-level handle owning all of the above

## What's in Python

- Ergonomic `Agent` / `Runtime` wrappers
- Real provider implementations (OpenAI/Anthropic/Ollama — community-contributed)
- `@tool` decorator + `ToolBox` for tool registration with auto JSON-schema
- `Graph` fluent builder for multi-agent workflows
- `AsyncRuntime` / `AsyncAgent` asyncio bridge

## Install (local, editable)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip scikit-build-core pybind11 cmake
pip install -e .
```

## Hello world

```python
from agentcore import Agent, Runtime, MockProvider

rt = Runtime()
provider = MockProvider()

researcher = rt.add(Agent("researcher", provider, system_prompt="Research."))
writer     = rt.add(Agent("writer",     provider, system_prompt="Write."))

researcher.append_user("Find three facts about graph databases.")
findings = researcher.step()

rt.handoff(frm="researcher", to="writer", text=findings)
rt.deliver(writer)
print(writer.step())
```

## Examples

- `examples/main.py` — two-agent pipeline (researcher → writer)
- `examples/tools_example.py` — Python tools through the C++ registry
- `examples/graph_example.py` — three-agent graph (researcher → writer → editor)
- `examples/async_example.py` — concurrent agent steps via asyncio

## Tests

```bash
pip install -e ".[test]"
pytest
```

## Why C++?

LLM I/O is network-bound, so a C++ core won't speed up your provider calls. Where C++ *does* help:

- Cache-friendly contiguous storage of message history
- Lock-friendly read-heavy access via `shared_mutex`
- GIL release on hot paths so Python threads can run concurrently
- Predictable memory + zero-overhead tool dispatch

If your bottleneck is the network, this won't be 10x faster than a pure-Python framework. If your bottleneck is in-memory orchestration (high agent counts, large histories, many tools), it should be measurably better.

## Design notes

See [`docs/design-notes.md`](docs/design-notes.md) for the design rationale, in particular the rebuttal of three "resists" called out in the initial design:

1. Why tool *bodies* stay in Python while the registry is C++
2. Why a fluent Python graph builder beats a YAML DSL
3. Why an asyncio bridge beats native C++ coroutines (for now)

## License

Apache 2.0. See [LICENSE](LICENSE).
