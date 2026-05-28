"""StateStore — in-memory and SQLite."""
from __future__ import annotations

import pytest

from marrow import (
    Agent,
    InMemoryStateStore,
    MockProvider,
    Runtime,
    SQLiteStateStore,
    restore_into,
)


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        yield InMemoryStateStore()
    else:
        yield SQLiteStateStore(tmp_path / "agents.db")


def test_save_and_load_roundtrip(store):
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider(),
                     system_prompt="You are a careful researcher."))
    a.append_user("hello")
    a.append_assistant("hi there")

    store.save("a", a._state)
    msgs = store.load("a")
    assert msgs is not None
    assert len(msgs) == 2
    assert msgs[0].content == "hello"
    assert msgs[1].content == "hi there"
    # Anything implementing the optional load_system_prompt method should
    # return the prompt.
    if hasattr(store, "load_system_prompt"):
        assert store.load_system_prompt("a") == "You are a careful researcher."


def test_load_missing_returns_none(store):
    assert store.load("nonexistent") is None


def test_delete(store):
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    a.append_user("x")
    store.save("a", a._state)
    assert store.load("a") is not None
    store.delete("a")
    assert store.load("a") is None


def test_restore_into_replays_history(store):
    rt1 = Runtime()
    a1 = rt1.add(Agent("a", MockProvider(),
                       system_prompt="Be careful."))
    a1.append_user("question 1")
    a1.append_assistant("answer 1")
    a1.append_user("question 2")
    store.save("a", a1._state)

    rt2 = Runtime()
    rt2.add(Agent("a", MockProvider()))
    assert restore_into(rt2, "a", store) is True

    state2 = rt2.engine.agent("a")
    assert state2.size() == 3
    if hasattr(store, "load_system_prompt"):
        sp = state2.system_prompt()
        assert sp == "Be careful."


def test_keys(store):
    rt = Runtime()
    for i in range(3):
        a = rt.add(Agent(f"a{i}", MockProvider()))
        store.save(f"a{i}", a._state)
    assert set(store.keys()) == {"a0", "a1", "a2"}
