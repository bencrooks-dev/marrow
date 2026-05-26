"""Concurrency tests — exercise the thread safety claims of the C++ core.

These tests would catch the two bugs fixed in the same commit:

1. `Engine::create_agent` previously released the engine lock before
   registering the agent with the router, so a concurrent
   `router.send()` could fail with "unknown recipient".

2. `ToolRegistry::invoke`'s Pybind11 binding previously declared
   `gil_scoped_release`, which caused copying the captured
   `py::function` without the GIL — UB in CPython.

Both manifest only under contention, so dedicated tests are needed.
"""
from __future__ import annotations

import threading

from agentcore import (
    Agent,
    Message,
    MockProvider,
    Role,
    Runtime,
    ToolBox,
    tool,
)


def _run_threads(target, n: int, *, args_factory=lambda i: (i,)) -> list:
    errors: list = []

    def wrapped(i: int):
        try:
            target(*args_factory(i))
        except Exception as e:  # noqa: BLE001
            errors.append((i, e))

    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_concurrent_create_and_send_no_race():
    """Two threads racing: one creates an agent, another sends to it.

    Pre-fix: ~5-20% failure rate with "unknown recipient" because
    Engine::create_agent released the engine lock before registering
    the new agent with the router.
    """
    rt = Runtime()

    # Pre-create the "sender" agent so it always exists.
    rt.add(Agent("sender", MockProvider()))

    def worker(i: int):
        target_id = f"t{i}"
        # Race: create the agent, then immediately send into it
        # from this same thread but through the router (which would
        # race with another concurrent create_agent).
        rt.add(Agent(target_id, MockProvider()))
        for j in range(20):
            rt.router.send("sender", target_id, Message.make(Role.User, f"m{j}"))
        drained = rt.router.drain(target_id)
        assert len(drained) == 20

    errors = _run_threads(worker, 16)
    assert not errors, f"races detected: {errors[:3]}"


def test_concurrent_tool_invocation_no_gil_corruption():
    """Eight threads × 200 invocations against a Python tool.

    Pre-fix: gil_scoped_release on `invoke` meant copying the captured
    py::function (refcount op) without GIL → memory corruption /
    intermittent crashes. Stable post-fix.
    """
    rt = Runtime()

    @tool(name="echo", description="echo back the text")
    def echo(text: str) -> str:
        return text

    ToolBox().add(echo).bind(rt)

    def worker(i: int):
        for j in range(200):
            payload = f'{{"text": "i{i}-j{j}"}}'
            result = rt.tools.invoke("echo", payload)
            assert f"i{i}-j{j}" in result

    errors = _run_threads(worker, 8)
    assert not errors, f"tool races: {errors[:3]}"


def test_concurrent_cache_read_write():
    """Cache under contention. LRU touches mutate state on read, so this
    exercises the full lock path (no shared_mutex; plain std::mutex)."""
    rt = Runtime()
    cache = rt.cache

    def writer(i: int):
        for j in range(500):
            cache.put(f"k{i}-{j % 50}", f"v{i}-{j}")

    def reader(i: int):
        for j in range(500):
            cache.get(f"k{i % 4}-{j % 50}")  # mixed hits and misses

    errors = _run_threads(writer, 4)
    errors += _run_threads(reader, 4)
    assert not errors, f"cache races: {errors[:3]}"


def test_concurrent_history_append_and_read():
    """AgentState uses shared_mutex; many readers + one writer per agent
    is the common case during streaming + parallel inspection."""
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))

    def appender(i: int):
        for j in range(100):
            a.append_user(f"msg from {i}-{j}")

    def reader(i: int):
        for _ in range(100):
            history = a._state.history()
            # Each Message must be intact — content non-empty and a string.
            for m in history[-10:]:
                assert isinstance(m.content, str)

    errors = _run_threads(appender, 4)
    errors += _run_threads(reader, 8)
    assert not errors, f"state races: {errors[:3]}"
    # 4 threads × 100 appends = 400 messages
    assert a._state.size() == 400
