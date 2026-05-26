"""Micro-benchmarks for the C++ hot paths via the Python binding.

Measures the cost of single primitive operations:
  - Message append to AgentState
  - Cache put / get
  - Router send / drain
  - Tool dispatch
"""
from __future__ import annotations

import json

from agentcore import Agent, MockProvider, Runtime, ToolBox, tool

from ._harness import Result, print_header, print_row, time_loop


def bench_message_append() -> Result:
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    return time_loop("AgentState.append", lambda: a.append_user("hi"), ops=10_000)


def bench_history_read() -> Result:
    rt = Runtime()
    a = rt.add(Agent("a", MockProvider()))
    for i in range(100):
        a.append_user(f"msg {i}")
    return time_loop("AgentState.history (100 msgs)",
                     lambda: a._state.history(), ops=5_000)


def bench_cache_put() -> Result:
    rt = Runtime()
    n = {"i": 0}

    def put():
        n["i"] += 1
        rt.cache.put(f"k{n['i'] % 1024}", "x" * 32)

    return time_loop("MemoryCache.put", put, ops=10_000)


def bench_cache_get_hit() -> Result:
    rt = Runtime()
    for i in range(512):
        rt.cache.put(f"k{i}", "v")
    return time_loop("MemoryCache.get (hit)",
                     lambda: rt.cache.get("k0"), ops=20_000)


def bench_router_send_drain() -> Result:
    rt = Runtime()
    rt.add(Agent("a", MockProvider()))
    rt.add(Agent("b", MockProvider()))

    def send_drain():
        rt.send("a", "b", "ping")
        rt.router.drain("b")

    return time_loop("Router.send+drain (pair)", send_drain, ops=10_000)


def bench_tool_invoke() -> Result:
    rt = Runtime()

    @tool(name="add", description="add ints")
    def add(a: int, b: int) -> int:
        return a + b

    ToolBox().add(add).bind(rt)
    payload = json.dumps({"a": 1, "b": 2})

    return time_loop("ToolRegistry.invoke (add)",
                     lambda: rt.tools.invoke("add", payload), ops=5_000)


def run_all() -> list[Result]:
    return [
        bench_message_append(),
        bench_history_read(),
        bench_cache_put(),
        bench_cache_get_hit(),
        bench_router_send_drain(),
        bench_tool_invoke(),
    ]


def main() -> None:
    print_header("agentcore micro-benchmarks")
    for r in run_all():
        print_row(r)


if __name__ == "__main__":
    main()
