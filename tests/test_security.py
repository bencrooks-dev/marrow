"""Security / abuse tests — the adversarial counterpart to the functional suite.

Each test ties to a THREAT-MODEL.md finding (T-id). Requires the compiled
extension; skipped if it isn't built (so it runs in CI where the build exists).
"""
from __future__ import annotations

import json
import threading

import pytest

marrow = pytest.importorskip("marrow")

from marrow import (  # noqa: E402
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
from marrow.tools import (  # noqa: E402
    _default_error_redactor,
    strict_error_redactor,
)

_CAP = 4 * 1024 * 1024  # Message.kMaxContentBytes


# --- T2: content cap cannot be bypassed ----------------------------------

def test_content_cap_enforced_in_make():
    with pytest.raises(RuntimeError):
        Message.make(Role.User, "x" * (_CAP + 1))


def test_content_cap_enforced_on_direct_assignment():
    """T2: setting .content directly must not bypass the cap."""
    m = Message.make(Role.User, "ok")
    with pytest.raises(RuntimeError):
        m.content = "x" * (_CAP + 1)
    # A normal assignment still works.
    m.content = "still fine"
    assert m.content == "still fine"


# --- T3: error redaction --------------------------------------------------

def test_default_redactor_scrubs_secrets_and_paths():
    msg = _default_error_redactor(
        Exception("fail sk-ABCDEFGH12345678 at /Users/bob/secret AKIAIOSFODNN7EXAMPLE")
    )
    assert "sk-ABCDEFGH12345678" not in msg
    assert "AKIAIOSFODNN7EXAMPLE" not in msg
    assert "/Users/bob/secret" not in msg
    assert msg.startswith("Exception:")


def test_strict_redactor_returns_type_only():
    assert strict_error_redactor(ValueError("super secret connection string")) == "ValueError"


def test_toolbox_strict_mode_hides_message():
    rt = Runtime()

    @tool(description="boom")
    def boom() -> str:
        raise ValueError("leak sk-DEADBEEF12345678 /Users/x/.aws/credentials")

    ToolBox(strict=True).add(boom).bind(rt)
    out = json.loads(rt.tools.invoke("boom", "{}"))
    assert out["ok"] is False
    assert out["error"] == "ValueError"  # type only, no message


# --- tool arg cap (OOM guard) --------------------------------------------

def test_oversized_tool_args_rejected():
    rt = Runtime()

    @tool(description="echo")
    def echo(s: str) -> str:
        return s

    ToolBox().add(echo).bind(rt)
    big = json.dumps({"s": "x" * (2 << 20)})  # > 1 MiB
    out = json.loads(rt.tools.invoke("echo", big))
    assert out["ok"] is False
    assert "exceed" in out["error"].lower()


# --- T1: cancellation is honored -----------------------------------------

def test_precancelled_token_blocks_step():
    rt = Runtime()
    a = rt.add(Agent("x", MockProvider()))
    a.append_user("hi")
    ct = CancelToken()
    ct.cancel()
    with pytest.raises(RuntimeError):
        a.step(cancel_token=ct)


def test_cancel_token_observed_across_threads():
    ct = CancelToken()
    threading.Thread(target=ct.cancel).start()
    # give the thread a beat; cancellation must become visible
    for _ in range(100000):
        if ct.cancelled():
            break
    assert ct.cancelled() is True


# --- T4: inbox backpressure bounds memory --------------------------------

def test_bounded_inbox_caps_memory():
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("r")
    rt.router.set_inbox_limit("r", 4, OverflowPolicy.DropOldest)
    for i in range(1000):
        rt.router.send("a", "r", Message.make(Role.User, str(i)))
    assert rt.router.inbox_size("r") <= 4


def test_reject_policy_surfaces_backpressure():
    rt = Runtime()
    rt.router.register_agent("a")
    rt.router.register_agent("r")
    rt.router.set_inbox_limit("r", 1, OverflowPolicy.Reject)
    rt.router.send("a", "r", Message.make(Role.User, "1"))
    with pytest.raises(RuntimeError):
        rt.router.send("a", "r", Message.make(Role.User, "2"))


# --- §5.2: unknown tool is a distinguishable error -----------------------

def test_unknown_tool_raises():
    rt = Runtime()
    with pytest.raises(RuntimeError):
        rt.tools.invoke("nope", "{}")
