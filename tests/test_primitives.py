"""Production primitives — cancellation, bounded inboxes, shutdown, size cap."""
from __future__ import annotations

import threading
import time

import pytest

from marrow import (
    Agent,
    CancelToken,
    GenerationResponse,
    Message,
    MockProvider,
    OverflowPolicy,
    PyProviderBase,
    Role,
    Runtime,
)

# --- CancelToken ---------------------------------------------------------

def test_cancel_token_basic():
    t = CancelToken()
    assert not t.cancelled()
    t.cancel()
    assert t.cancelled()
    t.reset()
    assert not t.cancelled()


def test_cancel_token_threaded():
    """A cancel flagged on one thread must be visible on another."""
    t = CancelToken()
    seen = []

    def worker():
        for _ in range(50):
            if t.cancelled():
                seen.append(True)
                return
            time.sleep(0.001)

    th = threading.Thread(target=worker)
    th.start()
    time.sleep(0.01)
    t.cancel()
    th.join(timeout=1.0)
    assert seen == [True]


def test_cancel_token_in_request_struct():
    """A provider can read the cancel token from the request."""

    class CancellingProvider(PyProviderBase):
        def name(self): return "cp"
        def generate(self, req):
            if req.cancel_token and req.cancel_token.cancelled():
                raise RuntimeError("cancelled")
            r = GenerationResponse()
            r.content = "ok"
            return r

    rt = Runtime()
    a = rt.add(Agent("a", CancellingProvider()))
    a.append_user("hi")

    token = CancelToken()
    token.cancel()
    with pytest.raises(RuntimeError, match="cancelled"):
        a.step(cancel_token=token)


# --- bounded inbox -------------------------------------------------------

def test_inbox_reject_throws_when_full():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    rt.router.set_inbox_limit("a", 2, OverflowPolicy.Reject)
    rt.send("x", "a", "one")
    rt.send("x", "a", "two")
    with pytest.raises(RuntimeError, match="inbox full"):
        rt.send("x", "a", "three")


def test_inbox_drop_oldest():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    rt.router.set_inbox_limit("a", 2, OverflowPolicy.DropOldest)
    rt.send("x", "a", "one")
    rt.send("x", "a", "two")
    rt.send("x", "a", "three")
    drained = rt.router.drain("a")
    assert [r.message.content for r in drained] == ["two", "three"]


def test_inbox_drop_newest():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    rt.router.set_inbox_limit("a", 2, OverflowPolicy.DropNewest)
    rt.send("x", "a", "one")
    rt.send("x", "a", "two")
    rt.send("x", "a", "three")  # silently dropped
    drained = rt.router.drain("a")
    assert [r.message.content for r in drained] == ["one", "two"]


def test_inbox_size_reporting():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    assert rt.router.inbox_size("a") == 0
    rt.send("x", "a", "one")
    rt.send("x", "a", "two")
    assert rt.router.inbox_size("a") == 2


# --- Engine shutdown -----------------------------------------------------

def test_shutdown_blocks_new_agents():
    rt = Runtime()
    rt.shutdown()
    assert rt.engine.is_shutdown()
    with pytest.raises(RuntimeError, match="engine is shutdown"):
        rt.add(Agent("a", MockProvider()))


def test_shutdown_does_not_break_existing_agents():
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    a.append_user("hi")
    rt.shutdown()
    # Existing operations on already-created agents still work.
    out = a.step()
    assert "hi" in out


# --- Message size cap ----------------------------------------------------

def test_message_size_cap_throws():
    with pytest.raises(RuntimeError, match="exceeds"):
        Message.make(Role.User, "x" * (4 * 1024 * 1024 + 1))


def test_message_at_size_cap_is_ok():
    # 4 MiB exactly is allowed.
    Message.make(Role.User, "x" * (4 * 1024 * 1024))
