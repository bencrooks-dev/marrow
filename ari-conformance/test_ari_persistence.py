"""ARI persistence conformance (spec §8, with §2.2 metadata round-trip).

Persistence is OPTIONAL for ARI-Core and REQUIRED for ARI-Server. These tests
verify the StateStore contract: lossless round-trip (including metadata) and an
explicit "absent" result for an unknown id.

Requires the compiled `marrow` extension; skipped if it isn't built.
"""
from __future__ import annotations

import pytest

marrow = pytest.importorskip("marrow")

from marrow import Agent, Message, MockProvider, Role, Runtime  # noqa: E402
from marrow.state_store import (  # noqa: E402
    InMemoryStateStore,
    SQLiteStateStore,
)


def _seed_agent():
    rt = Runtime()
    a = rt.add(Agent("p", MockProvider(), system_prompt="sp"))
    m = Message.make(Role.User, "hello", "p")
    m.timestamp_ms = 999
    m.metadata = {"trace": "xyz"}
    a._state.append(m)
    return a


@pytest.fixture
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryStateStore()
    return SQLiteStateStore(tmp_path / "state.db")


@pytest.mark.parametrize("store", ["memory", "sqlite"], indirect=True)
def test_roundtrip_is_lossless_including_metadata(store):
    """§8 + §2.2: a save/load round-trip MUST preserve all fields incl. metadata."""
    a = _seed_agent()
    store.save("p", a._state)
    loaded = store.load("p")
    assert loaded is not None
    assert len(loaded) == 1
    msg = loaded[0]
    assert msg.content == "hello"
    assert msg.name == "p"
    assert msg.timestamp_ms == 999
    # The bug this kit caught: metadata was dropped on load. MUST round-trip.
    assert dict(msg.metadata) == {"trace": "xyz"}


@pytest.mark.parametrize("store", ["memory", "sqlite"], indirect=True)
def test_load_unknown_id_returns_absent(store):
    """§8: load() of an unknown id MUST return absent (None), not an error."""
    assert store.load("never-saved") is None


@pytest.mark.parametrize("store", ["memory", "sqlite"], indirect=True)
def test_delete_then_load_is_absent(store):
    a = _seed_agent()
    store.save("p", a._state)
    store.delete("p")
    assert store.load("p") is None
