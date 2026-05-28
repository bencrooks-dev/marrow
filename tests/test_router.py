"""Router-focused tests including failure modes."""
import pytest

from marrow import Agent, MockProvider, Runtime


def test_unknown_recipient_raises():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    with pytest.raises(RuntimeError):
        rt.send(frm="a", to="ghost", text="hi")


def test_handoff_unknown_returns_false():
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    assert rt.handoff(frm="a", to="ghost", text="hi") is False


def test_drain_empty():
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    assert rt.router.drain("a") == []
    assert rt.deliver(a) == 0


def test_register_then_unregister():
    rt = Runtime()
    rt.add(Agent("temp", MockProvider()))
    assert rt.router.has_agent("temp")
    rt.router.unregister_agent("temp")
    assert not rt.router.has_agent("temp")
