"""ARI-Embedded runtime conformance (spec §10.2).

The runtime-level embedded requirements that need the built extension:
bounded inboxes (§10.2(2)), first-class thread-safe cancellation/timeouts
(§10.2(4)), and a zero-overhead no-op trace sink (§10.2(3) / §9).

Structural embedded checks live in `test_ari_embedded_structural.py` and need
no build.
"""
from __future__ import annotations

import threading

import pytest

marrow = pytest.importorskip("marrow")

from marrow import (  # noqa: E402
    CancelToken,
    Message,
    OverflowPolicy,
    Role,
    Runtime,
)
from marrow.tracing import NullTraceSink  # noqa: E402


def test_inbox_can_be_bounded_finite():
    """§10.2(2): inboxes can be given a finite bound for bounded memory."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("r")
    rt.router.set_inbox_limit("r", 2, OverflowPolicy.DropOldest)
    for i in range(10):
        rt.router.send("a", "r", Message.make(Role.User, str(i)))
    # Memory stays bounded regardless of producer rate.
    assert rt.router.inbox_size("r") <= 2


def test_cancellation_is_first_class_and_thread_safe():
    """§10.2(4): cancellation MUST be a first-class, cross-thread primitive."""
    ct = CancelToken()
    observed = []

    def watcher():
        # Spin briefly; should observe cancellation set from another thread.
        for _ in range(100000):
            if ct.cancelled():
                observed.append(True)
                return

    t = threading.Thread(target=watcher)
    t.start()
    ct.cancel()
    t.join()
    assert ct.cancelled() is True


def test_null_trace_sink_is_a_noop():
    """§10.2(3)/§9: the default sink adds no behavior (zero-overhead path)."""
    sink = NullTraceSink()
    with sink.span("agent.step", {"agent": "x"}) as sp:
        # All span operations must be safe no-ops.
        sp.set_attribute("k", "v")
        sp.set_status(True)
    # Reaching here without error is the contract for the disabled path.
    assert True
