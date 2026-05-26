<div align="center">

# agentcore

**A lightweight C++ core for AI agent orchestration — fast, embeddable, ergonomic from Python.**

[![CI](https://github.com/bencrooks-dev/agentcore/actions/workflows/ci.yml/badge.svg)](https://github.com/bencrooks-dev/agentcore/actions/workflows/ci.yml)
[![Wheels](https://github.com/bencrooks-dev/agentcore/actions/workflows/wheels.yml/badge.svg)](https://github.com/bencrooks-dev/agentcore/actions/workflows/wheels.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C.svg)](src/core/engine.hpp)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#project-status)

</div>

---

`agentcore` is a Pybind11-bound C++ engine that handles the performance-sensitive parts of multi-agent systems — message state, history, routing, tool dispatch — while keeping the developer-facing API in clean, ergonomic Python.

It's designed as a deliberate alternative to Python-heavy frameworks like **LangGraph**, **CrewAI**, and **AutoGen**: the hot path runs in native C++17 with proper read-heavy locking; the orchestration surface stays in Python where iteration is cheap. Real LLM providers (OpenAI, Anthropic, Ollama) ship as Python subclasses that hook back into the C++ core through a trampoline.

> **Project status: 0.1.0, public API frozen per [`STABILITY.md`](STABILITY.md).** The C++ core is buildable, tested, and works on Linux / macOS / Windows × Python 3.9–3.12. Production primitives — timeouts, cancellation, bounded inboxes, persistence, tracing, usage tracking — all shipped. Real-world soak testing and bus-factor-of-2 are the remaining items before this should be your default choice for a live system. See [`ROADMAP.md`](ROADMAP.md).

> **Benchmarks** — see [`benchmarks/`](benchmarks/). M-series Mac, Python 3.12: ~1.4M `AgentState.append`/s, ~672K router send+drain/s, ~64K full 3-agent pipeline iterations/s with `MockProvider`. Run `python -m benchmarks.compare_langgraph` for a head-to-head against LangGraph on a 1-node echo graph (`pip install '.[bench]'`).

---

## Highlights

- **Native C++ core** — Message history, LRU cache, agent router, tool registry, `CancelToken`. C++17, `std::shared_mutex` for read-heavy access, no third-party C++ deps beyond Pybind11.
- **Ergonomic Python** — `Agent` + `Runtime` dataclass API. Two lines from import to your first generated message.
- **Real providers** — `OpenAIProvider`, `AnthropicProvider` (with prompt caching), `OllamaProvider`. Adding a new one is a ~30-line subclass.
- **Streaming first-class** — Every provider implements `generate_stream`. `Agent.stream(on_chunk=...)` works the same way regardless of vendor.
- **Per-call timeouts + cancellation** — Pass `timeout_ms=` and a `CancelToken` to any `step()` or `stream()` call.
- **Backpressure** — `Router.set_inbox_limit(agent_id, max_size, policy)` with three policies (`Reject` / `DropOldest` / `DropNewest`).
- **Graceful shutdown** — `Runtime.shutdown()` blocks new agent creation; in-flight work finishes.
- **Persistence** — `StateStore` interface with `InMemoryStateStore` and `SQLiteStateStore`. Restart your app, resume your conversations.
- **Observability** — `TraceSink` Protocol with `NullTraceSink` / `PrintTraceSink` / `OpenTelemetryTraceSink`. Structured logging via `agentcore.logging_config`.
- **Usage tracking + cost estimation** — `UsageTracker` aggregates tokens per agent + model with configurable pricing tables.
- **Retry + rate limiting** — `RetryPolicy` (exponential backoff with jitter) and `RateLimiter` (token bucket); configure once on the `Runtime` and every agent inherits them.
- **Tools dispatched from C++** — Registry lookup and dispatch in native code; tool bodies stay in Python. Tool errors are redacted; args and results have configurable size caps.
- **Fluent graphs, not YAML** — `Graph().start().then().finish()`. Returns a structured `GraphResult` so callers can distinguish "reached end" from "ran out of steps" — no silent truncation.
- **Asyncio bridge** — `AsyncRuntime` wraps the C++ engine in a `ThreadPoolExecutor`. Pybind11 bindings release the GIL on `Provider::generate` and `generate_stream`, so threaded provider calls scale.
- **Thread-safe core** — `Engine`, `AgentRouter`, `AgentState`, `MemoryCache`, `ToolRegistry` verified by [`tests/test_concurrency.py`](tests/test_concurrency.py). CI runs the suite under ThreadSanitizer (informational).
- **Embeddable from C++** — The core compiles as a static library independent of Pybind11. See [`examples/embed_cpp/`](examples/embed_cpp/) for a pure-C++ demo.
- **Stability promise** — Public API stable per [`STABILITY.md`](STABILITY.md) with documented semver + deprecation flow.
- **Tiny dependency footprint** — Core requires only Pybind11. Real providers are opt-in extras.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                       User code (Python)                           │
│           Agents, prompts, business logic, asyncio loop            │
└──────────────────────────────┬─────────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────┐
│                  Python SDK  (agentcore.sdk)                       │
│    Agent · Runtime · ToolBox · Graph · AsyncRuntime · @tool        │
└──────────────────────────────┬─────────────────────────────────────┘
                               │   (Pybind11 — releases GIL on
                               │    blocking provider calls)
┌──────────────────────────────▼─────────────────────────────────────┐
│                C++ engine  (libagentcore_core)                     │
│                                                                    │
│    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│    │   Engine     │───▶│ AgentRouter  │◀──▶│ AgentState[] │        │
│    └──────┬───────┘    └──────────────┘    └──────────────┘        │
│           │                                                        │
│    ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐        │
│    │ MemoryCache  │    │ ToolRegistry │    │   Provider   │        │
│    │   (LRU)      │    │ (typed disp.)│    │ (interface)  │        │
│    └──────────────┘    └──────────────┘    └──────┬───────┘        │
└──────────────────────────────────────────────────┬│────────────────┘
                                                   ││
              ┌────────────────────┬───────────────┘└─────────────┐
              ▼                    ▼                              ▼
      ┌──────────────┐    ┌──────────────┐              ┌──────────────┐
      │ MockProvider │    │  OpenAI /    │              │   Ollama     │
      │    (C++)     │    │  Anthropic   │              │   (HTTP,     │
      │              │    │  (Py SDKs)   │              │    httpx)    │
      └──────────────┘    └──────────────┘              └──────────────┘
```

**What lives where**

| Layer | Responsibilities | Files |
|---|---|---|
| C++ core | `Message`, `AgentState`, `MemoryCache`, `AgentRouter`, `ToolRegistry`, `Engine`, `Provider` interface | `src/core/engine.{hpp,cpp}` |
| Bindings | Pybind11 module, `PyProvider` trampoline, GIL release on hot paths | `src/bindings/bindings.cpp` |
| Python SDK | `Agent`, `Runtime`, `Graph`, `ToolBox`, `AsyncRuntime` | `python/agentcore/` |
| Providers | `OpenAIProvider`, `AnthropicProvider`, `OllamaProvider` (optional extras) | `python/agentcore/providers/` |

See [`docs/design-notes.md`](docs/design-notes.md) for the design rationale and deliberate trade-offs.

---

## How agentcore compares

| | **agentcore** | LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| Native hot path | **C++17** | Python | Python | Python |
| GIL released during providers | **yes** | partial | no | no |
| Streaming | **built-in** | yes | yes | yes |
| Tool dispatch | **C++ registry** | Python | Python | Python |
| Graph builder | fluent Python | fluent Python | declarative | declarative |
| Required dependencies | **Pybind11 only** | many | many | many |
| Multi-agent concurrency | **threads + GIL release** | asyncio | sequential | asyncio |
| Embeddable from C++ | **yes** | no | no | no |
| Status | pre-alpha | stable | stable | stable |

Read this honestly: LangGraph / CrewAI / AutoGen are mature, supported, and have far more features today. `agentcore` is a focused alternative for the case where **the orchestration layer is your bottleneck** — high agent counts, large histories, hot tool dispatch, or embedding into a C++ application. If your bottleneck is network I/O (it usually is), the speedup will be modest.

---

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip scikit-build-core pybind11 cmake
pip install -e .
```

With real providers:

```bash
pip install 'agentcore[openai]'      # OpenAI Chat Completions
pip install 'agentcore[anthropic]'   # Anthropic Messages + prompt caching
pip install 'agentcore[ollama]'      # local Ollama daemon
pip install 'agentcore[all]'         # everything above
```

The `wheels.yml` workflow builds Linux / macOS / Windows × Python 3.9–3.12 wheels and uploads them as GitHub artifacts on `v*` tag pushes. PyPI publishing is **not** yet wired up; install via git or the artifact downloads until v0.1.

---

## Quickstart

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

---

## Usage

### Real providers

```python
from agentcore import Agent, Runtime
from agentcore.providers import AnthropicProvider

rt = Runtime()
provider = AnthropicProvider(model="claude-sonnet-4-6")  # caches system prompt
agent = rt.add(Agent("assistant", provider, system_prompt="Be concise."))

agent.append_user("What is a graph database?")
print(agent.step())
```

### Streaming

```python
agent.append_user("Write a haiku about graph databases.")
agent.stream(on_chunk=lambda c: print(c, end="", flush=True))
```

Works identically for `OpenAIProvider`, `AnthropicProvider`, `OllamaProvider`, `MockProvider`, and any Python subclass of `PyProviderBase`.

### Tools

```python
from agentcore import Runtime, ToolBox, tool

@tool(description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b

rt = Runtime()
ToolBox().add(add).bind(rt)            # registered in the C++ registry

print(rt.tools.invoke("add", '{"a": 2, "b": 3}'))
# {"ok": true, "result": 5}
```

JSON-schema is auto-generated from annotations for the common cases — primitives, `Optional[X]`, `Union`, `list[X]`, `dict`, `Literal[...]`. Stored as a string alongside the tool in C++. For complex types (Pydantic models, dataclasses) pass `schema=` explicitly on `@tool` rather than relying on the auto-generator.

### Multi-agent graphs

```python
from agentcore import Graph, run_graph

g = (Graph()
     .start("researcher")
     .then("researcher", "writer")
     .then("writer", "editor", when=lambda s: "DRAFT" in s)
     .finish("editor"))

final = run_graph(rt, agents_by_name, g, initial_input="Topic: graphs.")
```

Fluent, introspectable, no YAML. See [design-notes](docs/design-notes.md#2-yamljson-dsl-for-graphs) for why.

### Async / concurrency

```python
import asyncio
from agentcore import AsyncRuntime, Agent, MockProvider, Runtime

async def main():
    rt = AsyncRuntime(Runtime())
    agents = [rt.add(Agent(f"w{i}", MockProvider())) for i in range(8)]
    for i, a in enumerate(agents):
        a.append_user(f"hello from worker {i}")
    results = await rt.gather_steps(agents)   # concurrent

asyncio.run(main())
```

The C++ binding releases the GIL during `Provider::generate`, so threaded steps make real parallel progress while their Python provider code runs.

---

## Examples

All runnable. From the repo root after `pip install -e .`:

| File | Demonstrates |
|---|---|
| [`examples/main.py`](examples/main.py) | Two-agent handoff |
| [`examples/tools_example.py`](examples/tools_example.py) | Tool registry, schema generation, invocation |
| [`examples/graph_example.py`](examples/graph_example.py) | Three-node graph execution |
| [`examples/streaming_example.py`](examples/streaming_example.py) | Word-by-word streaming |
| [`examples/async_example.py`](examples/async_example.py) | Concurrent agent steps |
| [`examples/openai_example.py`](examples/openai_example.py) | OpenAI provider (requires `OPENAI_API_KEY`) |
| [`examples/anthropic_example.py`](examples/anthropic_example.py) | Anthropic provider with prompt caching |
| [`examples/embed_cpp/`](examples/embed_cpp/) | Embedding the C++ core into a non-Python application |

---

## Tests

```bash
pip install -e ".[test]"
pytest -v
```

Current suite: ~20 tests across smoke, router edge cases, tool registry (including args/result size caps and error redaction), streaming (Python-subclassed `Provider` trampoline path), and a dedicated concurrency suite that exercises the `shared_mutex` paths under contention.

---

## Project status

This is a **pre-alpha proof of concept**. The C++ core builds and runs on three platforms. The Python API is ergonomic. The architecture has been pressure-tested in the design and the most controversial trade-offs are documented in [`docs/design-notes.md`](docs/design-notes.md).

What is stable enough to play with:

- Core message / state / cache / router APIs
- Tool registration via `@tool` + `ToolBox`
- Graph builder
- `AsyncRuntime` for concurrent steps
- Mock + OpenAI + Anthropic + Ollama providers (best-effort, not battle-tested)

What is **not** done and should not be relied on:

- API stability — expect breaking changes between 0.0.x versions
- Persistence (state is in-memory only)
- Tracing / observability hooks
- Backpressure on router inboxes (currently unbounded — see [`SECURITY.md`](SECURITY.md))
- Per-call timeouts on the `Provider` interface
- Cancellation tokens for in-flight provider / tool calls
- Full tool-use protocol with multi-turn function calling
- Published benchmarks — claims of "fast" are architectural, not measured
- PyPI publishing — wheels build to GitHub artifacts; nothing is on PyPI yet
- ABI stability across versions

### Roadmap

- **v0.1** — Real provider tests w/ key-gated CI; ToolCall integration in the step loop; streaming benchmark vs LangGraph
- **v0.2** — `StateStore` interface + SQLite impl; `TraceSink` for OTel; bounded inboxes
- **v0.3** — DAG executor; async-iterator streaming API; first stable API contract
- **v1.0** — ABI promise per module; cibuildwheel wheels on PyPI; plugin loader for C++ providers

---

## License

`agentcore` is licensed under the **Apache License, Version 2.0**. The full text is in [`LICENSE`](LICENSE) and required attribution is in [`NOTICE`](NOTICE).

### Why Apache 2.0?

Picked over MIT specifically for the **explicit patent grant in §3** — contributors grant a perpetual, worldwide, royalty-free patent license to users for any patents reading on their contributions. This protects downstream commercial adopters from patent ambushes by contributors. Picked over GPL because `agentcore` is intended to be embedded in proprietary products without forcing them to be open-sourced.

### What the license permits

- **Commercial use** — including embedding in proprietary or closed-source products, no royalty
- **Modification** and creation of derivative works
- **Distribution** of source and binary forms
- **Private use** without disclosure
- **Sublicensing** under different terms (e.g. a downstream MIT package can include agentcore)

### What you must do

- **Preserve** the copyright and license notice in source distributions of agentcore code
- **Carry forward** the contents of `NOTICE` in derivative distributions, where applicable
- **State modifications** if you redistribute a modified version (Apache §4(b))
- **Not use** "agentcore" as the primary brand of a competing or derivative product (see *Trademark* below). The Apache license does *not* grant trademark rights.

### What you do not get

- Warranty of any kind — `agentcore` is provided "AS IS" (Apache §7)
- Liability — contributors are not liable for damages from use (Apache §8)
- Trademark license — see below

### Trademark

The name "agentcore" is not currently a registered trademark. We ask the community to:

- **Welcome:** use the name to describe integrations, plugins, or compatible implementations ("X for agentcore", "agentcore-compatible Y")
- **Avoid:** using "agentcore" as the primary brand of a competing or derivative product to prevent user confusion

### Patent statement

By contributing to `agentcore`, you grant — under Apache §3 — a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable (except as stated) patent license to make, have made, use, offer to sell, sell, import, and otherwise transfer the work, where such license applies only to those patent claims licensable by you that are necessarily infringed by your contribution alone or in combination with the work.

If any entity institutes patent litigation against another entity claiming the work infringes their patents, all patent licenses granted to that entity under this License terminate as of the filing date.

---

## Contributing

Pull requests are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, code style, and how submissions are licensed.

By submitting a PR you confirm — under Apache §5 — that your contribution is licensed to the project under the same Apache 2.0 terms, without additional restrictions.

---

## Acknowledgements

- [Pybind11](https://github.com/pybind/pybind11) — the seamless C++/Python interop that makes this whole project tractable.
- [scikit-build-core](https://github.com/scikit-build/scikit-build-core) — modern CMake-driven Python builds.
- [cibuildwheel](https://github.com/pypa/cibuildwheel) — wheels for every platform with one workflow.

Inspiration from LangGraph, CrewAI, AutoGen, and the broader open-source agent ecosystem — `agentcore` is an alternative, not a replacement.

---

<div align="center">
<sub>Apache 2.0 · pre-alpha · built with ridiculous attention to where bytes go</sub>
</div>
