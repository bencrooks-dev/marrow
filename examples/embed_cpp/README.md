# Embedding marrow from C++

This demo links the marrow C++ core into a plain C++ executable — no Python interpreter involved. It's the proof that the "embeddable from C++" claim is real.

## Build & run

```bash
cd examples/embed_cpp
mkdir build && cd build
cmake ..
cmake --build .
./marrow_embed_demo
```

Expected output:

```
[researcher] [mock:embedded] Three facts about graph DBs.
[writer]     [mock:embedded] [mock:embedded] Three facts about graph DBs.
writer.history()  = 2 messages
router.active() = writer
tool result: {"ok": true, "result": 42}
```

## What this proves

- `marrow::Engine`, `AgentState`, `AgentRouter`, `MemoryCache`, `ToolRegistry`, `MockProvider` all work without Pybind11
- The C++ tool registry accepts native `std::function<std::string(std::string)>` — registering a tool from C++ is one line
- Shared-mutex locking still works under pure-C++ contention

## What this does **not** prove

- A real downstream user would build marrow as a shared library (`add_library(marrow_core SHARED ...)`) and link against it, not vendor `engine.cpp` into their own executable. The demo cuts that corner for simplicity.
- No real LLM provider is wired up. Plug in your own `Provider` subclass to talk to a real backend.
