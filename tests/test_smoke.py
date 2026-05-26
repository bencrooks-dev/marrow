"""Smoke tests — module imports, two-agent pipeline runs."""
from agentcore import Agent, MockProvider, Runtime


def test_module_imports():
    import agentcore
    assert agentcore.__version__
    assert hasattr(agentcore, "Engine") is False  # Engine is internal
    assert agentcore.Role.User is not None


def test_two_agent_handoff():
    rt = Runtime()
    provider = MockProvider()
    a = rt.add(Agent("a", provider))
    b = rt.add(Agent("b", provider))

    a.append_user("ping")
    out_a = a.step()
    assert "ping" in out_a

    assert rt.handoff(frm="a", to="b", text=out_a) is True
    delivered = rt.deliver(b)
    assert delivered == 1

    out_b = b.step()
    assert "ping" in out_b  # echoed through the mock
    assert rt.router.active() == "b"


def test_cache_lru():
    rt = Runtime()
    cache = rt.cache
    cache.put("k1", "v1")
    cache.put("k2", "v2")
    assert cache.get("k1") == "v1"
    assert cache.contains("k2") is True
    cache.erase("k1")
    assert cache.contains("k1") is False


def test_history_trim():
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    for i in range(10):
        a.append_user(f"msg {i}")
    assert a._state.size() == 10
    tail = a._state.trimmed(3)
    assert len(tail) == 3
    assert tail[-1].content == "msg 9"
