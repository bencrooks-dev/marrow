"""ARI-Embedded structural conformance (spec §10.2).

These checks verify the *structural* requirements of the ARI-Embedded profile —
the ones that make the runtime embeddable in robots / edge / native hosts. They
read source and packaging metadata, so they run without compiling the extension.

Maps to ARI-SPEC.md §10.2 requirements 1 (no managed-language runtime in the
core) and 5 (declared, near-zero dependency footprint).
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_core_header_has_no_managed_runtime_dependency():
    """§10.2(1): the native core MUST NOT require a GC'd interpreter."""
    hdr = (REPO / "src" / "core" / "engine.hpp").read_text(encoding="utf-8")
    assert "pybind11" not in hdr, "core header must not depend on pybind11"
    assert "Python.h" not in hdr, "core header must not depend on CPython"


def test_core_impl_has_no_managed_runtime_dependency():
    """§10.2(1): the binding layer — not the core — owns Python interop."""
    src = (REPO / "src" / "core" / "engine.cpp").read_text(encoding="utf-8")
    assert "pybind11" not in src, "core impl must not depend on pybind11"
    assert "Python.h" not in src, "core impl must not depend on CPython"


def test_core_has_no_required_runtime_dependencies():
    """§10.2(5): minimal build declares a near-zero dependency footprint.

    The core package must declare no required runtime dependencies — heavy
    frameworks (langgraph/langchain/crewai) may appear ONLY in opt-in extras.
    """
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    # No top-level [project] dependencies array => zero required runtime deps.
    assert "\ndependencies = [" not in pyproject, (
        "core must not declare required runtime dependencies"
    )
    # Build backend is the only hard requirement, plus pybind11 for bindings.
    assert "scikit_build_core.build" in pyproject


def test_no_agent_framework_in_required_path():
    """§10.2(5): other agent frameworks must not be on the required path."""
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    bench_idx = pyproject.find("bench = [")
    for forbidden in ("langgraph", "langchain", "crewai", "autogen"):
        idx = pyproject.find(forbidden)
        if idx == -1:
            continue
        # If present at all, it must be inside the opt-in `bench` extra.
        assert bench_idx != -1 and idx > bench_idx, (
            f"{forbidden!r} must only appear in the opt-in bench extra"
        )


def test_embeddable_cpp_example_present():
    """§10.2(1): a pure-C++ embedding example proves embeddability."""
    embed = REPO / "examples" / "embed_cpp"
    assert embed.is_dir(), "examples/embed_cpp/ must exist"
    assert (embed / "main.cpp").is_file()
    assert (embed / "CMakeLists.txt").is_file()


def test_spec_and_strategy_present():
    """The standard's normative + strategy documents ship with the impl."""
    assert (REPO / "ARI-SPEC.md").is_file()
    assert (REPO / "docs" / "ari-strategy.md").is_file()
