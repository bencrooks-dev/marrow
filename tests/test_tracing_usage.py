"""Tracing + usage tracking via Runtime."""
from __future__ import annotations

import io

from marrow import (
    Agent,
    GenerationResponse,
    MockProvider,
    PrintTraceSink,
    PyProviderBase,
    Runtime,
    UsageTracker,
)


class UsageProvider(PyProviderBase):
    """Returns deterministic token counts so we can assert on them."""
    def name(self): return "test-model"
    def generate(self, req):
        r = GenerationResponse()
        r.content = "answer"
        r.prompt_tokens = 100
        r.completion_tokens = 50
        return r


def test_trace_sink_receives_spans():
    buf = io.StringIO()
    sink = PrintTraceSink(file=buf)
    rt = Runtime(trace_sink=sink)
    a = rt.add(Agent("a", MockProvider()))
    a.append_user("hi")
    a.step()
    out = buf.getvalue()
    assert "agent.step" in out
    assert "agent=a" in out or "agent" in out


def test_usage_tracker_accumulates():
    tracker = UsageTracker()
    rt = Runtime(usage=tracker)
    a = rt.add(Agent("a", UsageProvider()))
    a.append_user("q1")
    a.step()
    a.append_user("q2")
    a.step()
    totals = tracker.totals()
    assert totals.prompt_tokens == 200
    assert totals.completion_tokens == 100
    assert totals.calls == 2


def test_usage_tracker_by_agent():
    tracker = UsageTracker()
    rt = Runtime(usage=tracker)
    rt.add(Agent("alice", UsageProvider()))
    rt.add(Agent("bob", UsageProvider()))
    rt.engine.agent("alice")
    a = rt.add(Agent("alice2", UsageProvider()))
    b = rt.add(Agent("bob2", UsageProvider()))
    a.append_user("q")
    a.step()
    b.append_user("q")
    b.step()
    b.step()  # bob2 used twice
    per_agent = tracker.by_agent()
    assert per_agent["alice2"].calls == 1
    assert per_agent["bob2"].calls == 2


def test_usage_estimated_cost_with_pricing():
    tracker = UsageTracker(pricing={"test-model": (1.0 / 1000, 2.0 / 1000)})
    rt = Runtime(usage=tracker)
    a = rt.add(Agent("a", UsageProvider()))
    a.append_user("q")
    a.step(model="test-model")  # set the request's model so it's recorded
    # 100 prompt × 1.0/1000 + 50 completion × 2.0/1000 = 0.1 + 0.1 = 0.2
    assert abs(tracker.estimated_cost() - 0.2) < 1e-9
