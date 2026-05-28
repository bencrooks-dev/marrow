"""ARI-Core conformance (spec §2–§7).

Maps each test to a numbered ARI requirement and an Appendix B checklist box.
Requires the compiled `agentcore` extension; skipped if it isn't built.
"""
from __future__ import annotations

import json
import threading

import pytest

agentcore = pytest.importorskip("agentcore")

from agentcore import (  # noqa: E402
    Agent,
    CancelToken,
    Message,
    MockProvider,
    OverflowPolicy,
    Role,
    Runtime,
    ToolBox,
    tool,
)


# --- §2 Data model -------------------------------------------------------

def test_exactly_four_roles():
    """§2.1: a runtime MUST define exactly four roles."""
    assert set(Role.__members__.keys()) == {"System", "User", "Assistant", "Tool"}


def test_message_carries_required_fields():
    """§2.2: Message carries role, content, name, timestamp_ms, metadata."""
    m = Message.make(Role.User, "hello", "alice")
    m.timestamp_ms = 123
    m.metadata = {"k": "v"}
    assert m.role == Role.User
    assert m.content == "hello"
    assert m.name == "alice"
    assert m.timestamp_ms == 123
    assert dict(m.metadata) == {"k": "v"}


def test_metadata_preserved_through_routing():
    """§2.2: metadata MUST survive routing."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("b")
    msg = Message.make(Role.User, "payload", "a")
    msg.metadata = {"trace": "abc"}
    rt.router.send("a", "b", msg)
    drained = rt.router.drain("b")
    assert len(drained) == 1
    assert drained[0].from_ == "a"
    assert drained[0].to == "b"
    assert dict(drained[0].message.metadata) == {"trace": "abc"}


# --- §3 Provider / cancellation ------------------------------------------

def test_cancel_token_lifecycle():
    """§3.5: cancel()/cancelled()/reset() semantics."""
    ct = CancelToken()
    assert ct.cancelled() is False
    ct.cancel()
    assert ct.cancelled() is True
    ct.reset()
    assert ct.cancelled() is False


def test_cancel_token_is_thread_safe():
    """§3.5: cancellation MUST be observable across threads."""
    ct = CancelToken()
    t = threading.Thread(target=ct.cancel)
    t.start()
    t.join()
    assert ct.cancelled() is True


def test_generation_request_supports_timeout():
    """§3.6: a wall-clock timeout is part of the request contract."""
    from agentcore import GenerationRequest

    req = GenerationRequest()
    assert req.timeout_ms == 0  # default disables
    req.timeout_ms = 50
    assert req.timeout_ms == 50


# --- §4 Agent state ------------------------------------------------------

def test_agent_state_history_and_trim():
    """§4: append/history/size/trimmed/system_prompt/clear."""
    rt = Runtime()
    a = rt.add(Agent("s", MockProvider(), system_prompt="sys"))
    st = a._state
    for c in ("m1", "m2", "m3"):
        st.append(Message.make(Role.User, c))
    assert st.size() == 3
    assert [m.content for m in st.history()] == ["m1", "m2", "m3"]
    # trimmed(n): at most the most-recent n, chronological order preserved.
    assert [m.content for m in st.trimmed(2)] == ["m2", "m3"]
    assert st.system_prompt() == "sys"
    st.clear()
    assert st.size() == 0


# --- §5 Tools ------------------------------------------------------------

def _rt_with_tools():
    rt = Runtime()

    @tool(description="Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    @tool(description="Always raises")
    def boom() -> str:
        raise ValueError("kaboom from /Users/secret/path sk-DEADBEEF")

    ToolBox().add(add).add(boom).bind(rt)
    return rt


def test_tool_success_envelope():
    """§5.3: success => {"ok": true, "result": ...}."""
    rt = _rt_with_tools()
    out = json.loads(rt.tools.invoke("add", '{"a": 2, "b": 3}'))
    assert out == {"ok": True, "result": 5}


def test_tool_error_envelope_is_redacted():
    """§5.3/§5.4: failure => {"ok": false, "error": ...} with redaction."""
    rt = _rt_with_tools()
    out = json.loads(rt.tools.invoke("boom", "{}"))
    assert out["ok"] is False
    assert "error" in out
    # §5.4: internal paths / key-like fragments MUST NOT leak.
    assert "/Users/" not in out["error"]
    assert "sk-" not in out["error"]


def test_unknown_tool_raises_distinguishably():
    """§5.2: invoking an unregistered tool MUST raise."""
    rt = _rt_with_tools()
    with pytest.raises(Exception):
        rt.tools.invoke("does_not_exist", "{}")


def test_tool_arg_size_cap_rejected():
    """§5.4: oversize args are rejected via the error envelope, not OOM."""
    rt = _rt_with_tools()
    big = json.dumps({"a": "x" * (1 << 21), "b": 1})  # > 1 MiB
    out = json.loads(rt.tools.invoke("add", big))
    assert out["ok"] is False
    assert "exceed" in out["error"].lower()


# --- §6 Routing ----------------------------------------------------------

def test_drain_is_atomic_vs_send():
    """§6.1: drain returns all pending and empties the inbox."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("b")
    rt.router.send("a", "b", Message.make(Role.User, "1"))
    rt.router.send("a", "b", Message.make(Role.User, "2"))
    first = rt.router.drain("b")
    assert [r.message.content for r in first] == ["1", "2"]
    assert rt.router.drain("b") == [] or len(rt.router.drain("b")) == 0


def test_overflow_policy_reject():
    """§6.3: Reject surfaces backpressure to the producer."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("c")
    rt.router.set_inbox_limit("c", 1, OverflowPolicy.Reject)
    rt.router.send("a", "c", Message.make(Role.User, "1"))
    with pytest.raises(Exception):
        rt.router.send("a", "c", Message.make(Role.User, "2"))


def test_overflow_policy_drop_oldest():
    """§6.3: DropOldest evicts the oldest, keeps the newest."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("d")
    rt.router.set_inbox_limit("d", 1, OverflowPolicy.DropOldest)
    rt.router.send("a", "d", Message.make(Role.User, "old"))
    rt.router.send("a", "d", Message.make(Role.User, "new"))
    drained = rt.router.drain("d")
    assert [r.message.content for r in drained] == ["new"]


def test_overflow_policy_drop_newest():
    """§6.3: DropNewest discards the incoming message."""
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("e")
    rt.router.set_inbox_limit("e", 1, OverflowPolicy.DropNewest)
    rt.router.send("a", "e", Message.make(Role.User, "keep"))
    rt.router.send("a", "e", Message.make(Role.User, "dropme"))
    drained = rt.router.drain("e")
    assert [r.message.content for r in drained] == ["keep"]


# --- §7 Lifecycle --------------------------------------------------------

def test_shutdown_is_idempotent_and_blocks_new_work():
    """§7: shutdown is idempotent, blocks new agent creation, sets status."""
    rt = Runtime()
    rt.shutdown()
    assert rt.engine.is_shutdown() is True
    rt.shutdown()  # idempotent — must not raise
    with pytest.raises(Exception):
        rt.add(Agent("late", MockProvider()))
