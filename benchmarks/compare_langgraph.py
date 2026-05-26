"""Comparison: same workload, agentcore vs. LangGraph.

Run with the bench extras installed::

    pip install '.[bench]'
    python -m benchmarks.compare_langgraph

This is a deliberately tiny workload (in-memory pipeline, mock LLM,
zero network) so we measure the orchestration layer overhead, not the
provider. Apples-to-apples is hard with very different mental models;
treat the numbers as directional, not absolute.
"""
from __future__ import annotations

import time

from agentcore import Agent, MockProvider, Runtime

from ._harness import Result, print_header, print_row


def bench_agentcore(iters: int) -> Result:
    rt = Runtime()
    provider = MockProvider()
    a = rt.add(Agent("step", provider))
    a.append_user("hi")

    t0 = time.perf_counter()
    for _ in range(iters):
        a.step()
        a._state.clear()
        a.append_user("hi")
    elapsed = time.perf_counter() - t0
    return Result(
        name="agentcore: single-step loop",
        ops=iters, duration_s=elapsed,
        p50_us=elapsed / iters * 1e6, p99_us=elapsed / iters * 1e6,
        ops_per_s=iters / elapsed,
    )


def bench_langgraph(iters: int) -> Result | None:
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        print("skipping LangGraph comparison — install with 'pip install .[bench]'")
        return None

    # Minimal LangGraph state graph that just echoes the input. This is
    # the smallest possible workload — any larger graph adds work to
    # both sides equally and doesn't change the relative orchestration
    # overhead.

    def echo(state):
        return {"output": state["input"]}

    g = StateGraph(dict)
    g.add_node("echo", echo)
    g.set_entry_point("echo")
    g.add_edge("echo", END)
    compiled = g.compile()

    payload = {"input": "hi"}
    t0 = time.perf_counter()
    for _ in range(iters):
        compiled.invoke(payload)
    elapsed = time.perf_counter() - t0
    return Result(
        name="langgraph: 1-node graph",
        ops=iters, duration_s=elapsed,
        p50_us=elapsed / iters * 1e6, p99_us=elapsed / iters * 1e6,
        ops_per_s=iters / elapsed,
    )


def main() -> None:
    print_header("agentcore vs LangGraph (orchestration overhead only)")
    print("note: mock LLM, no network, no tools — measures orchestration cost.\n")
    iters = 5_000
    a = bench_agentcore(iters)
    print_row(a)
    b = bench_langgraph(iters)
    if b is not None:
        print_row(b)
        ratio = b.ops_per_s / a.ops_per_s if a.ops_per_s > 0 else 0
        print(f"\nratio (LangGraph / agentcore ops/s) = {ratio:.2f}x")
        if ratio < 1:
            print(f"agentcore is {1/ratio:.2f}x faster on this microbench.")
        else:
            print(f"LangGraph is {ratio:.2f}x faster on this microbench.")


if __name__ == "__main__":
    main()
