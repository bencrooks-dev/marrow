"""End-to-end: a multi-agent loop with a mock provider.

Measures realistic per-step cost of a 3-agent pipeline running for many
iterations. Mock provider returns instantly so the measurement is
dominated by marrow overhead (state copy, routing, tool dispatch).
"""
from __future__ import annotations

import time

from marrow import Agent, MockProvider, Runtime

from ._harness import Result, print_header, print_row


def run_pipeline(iterations: int) -> Result:
    rt = Runtime()
    provider = MockProvider("bench")

    researcher = rt.add(Agent("researcher", provider))
    writer     = rt.add(Agent("writer", provider))
    editor     = rt.add(Agent("editor", provider))

    pipeline = [researcher, writer, editor]
    researcher.append_user("Topic: graph databases")

    t0 = time.perf_counter()
    for _ in range(iterations):
        # researcher → writer → editor → drop result
        researcher.step()
        rt.handoff(frm="researcher", to="writer",
                   text="hand off " + researcher._state.history()[-1].content[:20])
        rt.deliver(writer)
        writer.step()
        rt.handoff(frm="writer", to="editor", text="hand off")
        rt.deliver(editor)
        editor.step()
        # Reset for next iteration to keep history bounded.
        for a in pipeline:
            a._state.clear()
        researcher.append_user("Topic: graph databases")
    elapsed = time.perf_counter() - t0

    return Result(
        name=f"3-agent pipeline × {iterations} iters",
        ops=iterations,
        duration_s=elapsed,
        p50_us=elapsed / iterations * 1e6,
        p99_us=elapsed / iterations * 1e6,  # no per-iter sample here
        ops_per_s=iterations / elapsed,
    )


def main() -> None:
    print_header("marrow end-to-end (mock provider)")
    print_row(run_pipeline(2_000))
    print_row(run_pipeline(10_000))


if __name__ == "__main__":
    main()
