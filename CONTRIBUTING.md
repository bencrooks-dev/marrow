# Contributing to marrow

Thanks for your interest. `marrow` is pre-alpha and we welcome contributions across the C++ core, Python SDK, providers, tests, and docs.

---

## Development setup

```bash
git clone https://github.com/bencrooks-dev/marrow
cd marrow
python -m venv .venv && source .venv/bin/activate
pip install -U pip scikit-build-core pybind11 cmake
pip install -e ".[test,all]"
pytest -v
```

The build is editable: after the first `pip install -e .`, edits to `python/` reload instantly. Edits to C++ (`src/core/`, `src/bindings/`) require `pip install -e .` again to recompile the extension.

---

## What we'd love help with

- **Real provider tests** behind environment-variable gates (so CI runs them only when keys are present)
- **Tool-use protocol** — full multi-turn function calling integrated with the step loop
- **`StateStore` interface** + SQLite implementation
- **`TraceSink` interface** + OpenTelemetry exporter
- **Benchmarks** against LangGraph / CrewAI on realistic workloads
- **Documentation** — tutorials, recipes, deep dives into the C++ side

If you're picking up something larger than a one-file change, open an issue first so we can sanity-check the approach.

---

## Code style

### C++

- **C++17 only.** No `concepts`, no coroutines (yet), no `std::format`.
- `std::shared_mutex` for read-heavy state; plain `std::mutex` when mutations dominate reads (`MemoryCache`).
- `std::optional`, `std::variant`, `std::shared_ptr` over raw owning pointers.
- Header guards via `#pragma once`.
- Compile clean under `-Wall -Wextra -Wpedantic` (or `/W4 /permissive-` on MSVC).
- No third-party C++ deps in the core beyond `pybind11`.

### Python

- **Python 3.9+** (one runtime; we test 3.9–3.12).
- Prefer `@dataclass` and explicit type hints. `from __future__ import annotations` at the top.
- No emojis in source or output.
- Provider implementations live in `python/marrow/providers/`. New providers should:
  - Subclass `PyProviderBase` (which is the C++ `Provider` exposed via Pybind11)
  - Implement `name()`, `generate(req)`, and `generate_stream(req, on_chunk)`
  - Use lazy imports of the backing SDK with a clear install hint in the error message

### Tests

- `pytest` only. No `unittest.TestCase`.
- Add a test for every new public method or behavior.
- Tests must not require network access. Provider tests that hit real APIs should be gated by environment variables and skipped if missing.

---

## Commit messages

Conventional Commits style:

- `feat: ...` for new user-facing functionality
- `fix: ...` for bug fixes
- `docs: ...` for documentation
- `refactor: ...` for non-behavioral changes
- `test: ...` for test-only changes
- `build: ...`, `ci: ...`, `chore: ...` as appropriate

Keep the subject line under 72 characters; explain *why* in the body.

---

## Pull requests

1. Fork and create a topic branch from `main`.
2. Run `pytest -v` and `python examples/main.py` locally before pushing.
3. Open a PR with a clear description. Link any related issues.
4. CI must be green on Linux / macOS / Windows × Python 3.9–3.12 before merge.

---

## Licensing of contributions

By submitting a pull request, you confirm — under Apache License 2.0 §5 — that:

1. Your contribution is your original work, or you have the right to submit it.
2. You grant the project the license described in [`LICENSE`](LICENSE), including the patent grant in §3.
3. Your contribution will be distributed under the same Apache 2.0 terms as the rest of the project, without additional restrictions.

We do not require a separate CLA. The Apache 2.0 inbound = outbound model (the "Apache way") covers this.

---

## Reporting security issues

If you find a security issue (memory safety, RCE through tool dispatch, etc.), please **do not** open a public issue. Email the maintainers (see repo profile) with the details so we can coordinate a fix before disclosure.

---

## Code of conduct

Be kind. Assume good faith. We do not have a formal CoC document yet; until we do, the [Contributor Covenant](https://www.contributor-covenant.org/) is a reasonable default expectation.

---

## License

By contributing, you license your work under the terms of [Apache License 2.0](LICENSE).
