# Design Notes

Decisions that shaped agentcore, and why.

---

## The three "resists" — and how they're addressed

In the initial design, three things were marked as deliberately deferred:

1. Putting tool implementations in C++.
2. Building a YAML/JSON DSL.
3. Making the C++ core async-by-default.

This document explains the reasoning, the workarounds we shipped, and the conditions under which each decision would flip.

---

### 1. Tool implementations in C++

**Why resist:** Tool contracts evolve constantly. Adding a new tool argument, changing return shape, swapping out a service — these happen weekly in a real agent system. Every change that crosses the Python/C++ boundary requires a rebuild, an ABI think, and (eventually) a wheel re-publish. The friction would dominate the workflow.

**What we shipped instead:** The *registry* and *dispatch* are pure C++ — fast lookup, thread-safe, no GIL contention. Tool *bodies* stay in Python, captured as `py::function` and type-erased into `std::function<std::string(const std::string&)>` at registration time. The C++ core never knows it's calling Python.

```
Python                          C++
+-------------+                 +------------------+
| @tool       |   register      | ToolRegistry     |
| def add():  |  ─────────────► | name→ToolFn      |
+-------------+                 +------------------+
                                     │ invoke(name, json)
                                     ▼
                                +------------------+
                                | std::function    |
                                | wraps py::func   |  ◄── GIL re-acquired
                                +------------------+
```

The JSON-schema for each tool is also stored in C++ (as a string), so providers that need it (OpenAI tool-calling, Anthropic tool-use) can hand the schema directly to the LLM without round-tripping through Python.

**When this flips:** If profiling shows a measurable fraction of CPU time burned in trivially-C++-able tools (string manip, math, regex), those *specific* tools can be implemented as `Provider`-style C++ plugins. The registry already accepts any `ToolFn` — no API change needed.

**Code:** `src/core/engine.hpp` (`ToolRegistry`), `src/bindings/bindings.cpp` (`ToolRegistry::register` binding), `python/agentcore/tools.py` (`@tool` + `ToolBox`).

---

### 2. YAML/JSON DSL for graphs

**Why resist:** Config-file DSLs ossify before you've understood the right abstraction. Once a YAML schema is published, breaking it is a community event. You end up smuggling Python through `eval:` strings, hooks, and template tags — which is just an inferior DSL on top of an inferior DSL.

**What we shipped instead:** A fluent **Python graph builder** (`Graph`). It's introspectable, composable, debuggable with `pdb`, and serialisable with `pickle` or any custom serialiser. You compose in Python and call `.freeze()` to get an immutable `FrozenGraph`.

```python
g = (Graph()
     .start("researcher")
     .then("researcher", "writer")
     .then("writer", "editor", when=lambda s: "DRAFT" in s)
     .finish("editor"))
```

**Workaround for the YAML use case:** If a user actually wants declarative configs (CI/CD pipelines, GitOps, multi-tenant configs), a `from_yaml(path)` adapter is a 30-line script that parses YAML into `Graph` builder calls. It's intentionally not in the core — users with that need add a thin layer they control.

**When this flips:** If a `Graph` becomes the dominant interchange format and *needs* to be serialised across language/process boundaries (e.g. a graph defined in Python, executed by a Go scheduler), we add `to_proto()` / `from_proto()`. Protobuf, not YAML.

**Code:** `python/agentcore/graph.py`, `examples/graph_example.py`.

---

### 3. Async-by-default in C++

**Why resist:** Real cross-platform async C++ is one of: `boost::asio` (heavyweight, hard to vendor), C++20 coroutines (still maturing, painful to bind through Pybind11), or hand-rolled (a maintenance trap). All three slow down contribution velocity for an early-stage open-source project where the bottleneck is *not* the C++ scheduler — it's network I/O happening at the Python edge.

**What we shipped instead:** The C++ core is **synchronous and thread-safe**. All blocking methods on Pybind11 bindings declare `py::call_guard<py::gil_scoped_release>`, so they release the GIL during the call. The Python `AsyncRuntime` wraps `Agent.step()` in a `ThreadPoolExecutor` and returns an awaitable. The thread pool is shared, tunable, and overridable.

```
asyncio loop ──► run_in_executor ──► thread ──► [Pybind11 GIL release]
                                                       │
                                                       ▼
                                                C++ engine call
                                                       │
                                                       ▼
                                              Python provider impl (re-acquires GIL)
```

Crucially: because `Provider::generate` releases the GIL, multiple worker threads make *real* progress in parallel even when both are running Python provider code — the provider re-acquires the GIL only briefly per network op.

**When this flips:** If we ever ship a C++ provider (e.g. a llama.cpp embed), or if benchmarks show that thread-pool dispatch is dominating at very high agent counts (~10k), then a C++ task queue with `std::condition_variable` worker threads becomes worthwhile. The Python `AsyncRuntime` surface stays unchanged — only the internals move.

**Code:** `python/agentcore/asyncio_bridge.py`, `examples/async_example.py`, plus the `call_guard` on `MockProvider::generate` in `src/bindings/bindings.cpp`.

---

## Other deliberate choices

### `shared_mutex` instead of `mutex` everywhere

`AgentState`, `AgentRouter`, `Engine`, `ToolRegistry` all use `std::shared_mutex`. Reads massively outnumber writes in agent workflows (every step reads history; only step boundaries write to it). `MemoryCache` uses a plain `mutex` because LRU touches mutate order on read — `shared_mutex` would be incorrect.

### Inboxes are unbounded

Production systems will need bounded inboxes with a drop / block / DLQ policy. Right now `AgentRouter::send` is non-blocking and just appends. This is a known PoC limitation.

### Streaming is not in the binding yet

`Provider::generate` returns a complete response. A streaming version (`generate_stream(req, callback)`) is a small addition — the callback would be a `py::function` invoked from C++ with the GIL re-acquired, similar to how tools work. Punted for v0.1.

### No persistence

State is in-memory only. A `StateStore` interface (in-memory default + SQLite impl) is a planned v0.2 addition.

### No tracing

Important and missing. A `TraceSink` interface with span events (`agent.step`, `provider.generate`, `tool.invoke`) belongs in the C++ core so it can capture timing across the boundary. Planned for v0.2.
