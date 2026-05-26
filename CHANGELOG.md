# Changelog

All notable changes to `agentcore` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/) once it reaches 1.0; until then, API breaks may happen at any 0.0.x bump.

## [Unreleased]

### Fixed

- **Critical: GIL race in `ToolRegistry::invoke`.** The Pybind11 binding previously declared `py::call_guard<py::gil_scoped_release>` while the C++ implementation copies a `std::function` that captures a `py::function`. The copy increments a `PyObject` refcount, which is undefined behavior in CPython without the GIL held. Removed the `call_guard`; the GIL is now held through invocation (which is correct since tools run Python anyway).
- **Critical: TOCTOU race in `Engine::create_agent`.** The engine previously released its mutex before calling `router_.register_agent`, opening a window where another thread could observe the agent in the engine map but get "unknown recipient" when sending to it. The engine lock is now held across both operations. Safe because `AgentRouter` never calls into `Engine`, so there's no inverse lock order.

### Added

- `tests/test_concurrency.py` — four contention tests that would have detected both bugs above. Covers concurrent create+send, concurrent tool invocation, cache contention, and history append/read races.
- `SECURITY.md` — vulnerability disclosure policy, threat model, and known security-relevant limitations.
- `CHANGELOG.md` (this file).
- `CODEOWNERS`, issue templates, PR template, Dependabot config — standard OSS hygiene.

### Changed

- `README.md` — toned down unbenchmarked "fast" claims pending real measurements; added a "Known limitations" callout near the top.

---

## [0.0.2] — 2026-05-26

### Added

- Streaming through the C++ core: `Provider::generate_stream(req, on_chunk)`, `Agent.stream(on_chunk=...)`. Pybind11 trampoline supports Python subclasses overriding `generate_stream`.
- Real provider implementations under `agentcore.providers`:
  - `OpenAIProvider` — Chat Completions API with streaming.
  - `AnthropicProvider` — Messages API with `cache_control: ephemeral` on system prompts (prompt caching).
  - `OllamaProvider` — local daemon at `http://localhost:11434`, no API key.
- Optional install extras: `agentcore[openai]`, `agentcore[anthropic]`, `agentcore[ollama]`, `agentcore[all]`.
- GitHub Actions workflows:
  - `ci.yml` — pytest matrix on Linux / macOS / Windows × Python 3.9–3.12, plus example smoke runs.
  - `wheels.yml` — `cibuildwheel` on `v*` tags or manual dispatch.

### Fixed

- Windows CI failed under cp1252 codec when example output contained Unicode (`→`). Added `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` to all CI jobs.

---

## [0.0.1] — 2026-05-26

### Added

- Initial proof-of-concept release.
- C++17 core (`src/core/engine.{hpp,cpp}`):
  - `Message`, `AgentState` (shared_mutex), `MemoryCache` (LRU), `AgentRouter` (registry + inboxes + handoff), `ToolRegistry` (type-erased dispatch), `Engine` (top-level handle), `Provider` interface with `MockProvider`.
- Pybind11 bindings exposing the full core to Python.
- Python SDK:
  - `Agent` / `Runtime` ergonomic wrappers.
  - `@tool` decorator + `ToolBox` with auto-generated JSON schemas.
  - `Graph` fluent builder for multi-agent workflows.
  - `AsyncRuntime` / `AsyncAgent` for concurrent steps over `ThreadPoolExecutor`.
- Four examples (two-agent pipeline, tools, graph, async).
- Eleven pytest tests covering smoke, router, tools.
- Apache 2.0 license; design notes documenting deliberate trade-offs.
