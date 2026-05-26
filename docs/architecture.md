# Architecture

## Layers

```
+-----------------------------------------------+
|             User code (Python)                |
+----------------------+------------------------+
                       |
+----------------------v------------------------+
|       Python SDK  (agentcore.sdk)             |
|  Agent · Runtime · ToolBox · Graph · Async    |
+----------------------+------------------------+
                       |  Pybind11 (GIL release on hot paths)
+----------------------v------------------------+
|        C++ engine  (libagentcore_core)        |
|                                               |
|  Engine ──► AgentRouter ◄──► AgentState[]     |
|     │                                         |
|     ▼                                         |
|  MemoryCache · ToolRegistry · Provider        |
+----------------------+------------------------+
                       |
        +--------------+--------------+
        |              |              |
    Mock (C++)   OpenAI/Anthropic   Ollama
                  (Python SDKs)     (HTTP)
```

## Layer responsibilities

| Layer | Owns | Does not own |
|---|---|---|
| C++ core | Message storage, history, LRU cache, router, tool registry, Engine lifecycle | LLM I/O, async runtime, tool implementations |
| Bindings | Type marshalling, GIL release, trampoline for Python-subclassed providers | Business logic |
| Python SDK | `Agent` / `Runtime` ergonomics, `@tool` decorator, fluent graph builder, asyncio bridge, retry/rate-limit policy, tracing hooks, usage tracking | C++ data structures, locks |
| Providers | Talking to real LLM APIs | Multi-agent orchestration |

## Concurrency

`AgentState`, `AgentRouter`, `Engine`, `ToolRegistry` all use `std::shared_mutex` because reads massively outnumber writes in agent workflows. `MemoryCache` uses a plain `std::mutex` because LRU touches mutate state on read.

The Pybind11 bindings release the GIL on `Provider::generate` and `generate_stream`. The `PYBIND11_OVERRIDE` trampoline re-acquires the GIL when the call ends up in a Python subclass. Concurrent agent steps from threads scale linearly until your provider's rate limit is the bottleneck.

A dedicated [`tests/test_concurrency.py`](https://github.com/bencrooks-dev/agentcore/blob/main/tests/test_concurrency.py) exercises:

- Concurrent `Engine.create_agent` + `Router.send` (catches TOCTOU)
- Concurrent `ToolRegistry.invoke` (catches GIL races)
- Cache contention
- History append + read races

CI runs the suite under ThreadSanitizer on every push (informational).

## What's in C++, what's in Python, and why

**In C++:**

- `Message`, `AgentState`, `MemoryCache`, `AgentRouter`, `ToolRegistry`, `Engine`, `Provider` interface, `MockProvider`, `CancelToken`.
- Anything called on the hot path of an agent step.
- Anything that benefits from cache-friendly contiguous storage.

**In Python:**

- Real provider implementations. LLM I/O is network-bound; the GIL is a non-issue and Python's async/HTTP ecosystem is excellent.
- Tool bodies. Tool contracts evolve constantly; rebuilding the extension on every tool change would be a tax with no benefit.
- Multi-agent patterns (graphs, retry, rate limit, tracing, persistence, usage). These compose over the C++ primitives.

## Why this layering pays off

For a real workload where the LLM is the bottleneck, the speedup over a pure-Python framework is modest — both sides are waiting on the network.

For a workload where orchestration is the bottleneck — many agents, large histories, hot tool dispatch — the native primitives can be 5-50× faster than the equivalent Python implementations. See [benchmarks](benchmarks.md).

## When this layering does **not** pay off

- Single-agent, low-throughput, network-bound workloads. Use whatever framework feels easiest.
- Heavy use of arbitrary Python tools per step. The C++ → Python boundary is fast but not free; >1000 tool calls per step will dominate the timing.
- Workflows that need first-class distributed routing. `agentcore` is single-process by design today.
