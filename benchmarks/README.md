# Benchmarks

Quick numbers on the orchestration overhead of marrow. **These measure native overhead, not LLM latency** — every benchmark uses `MockProvider` or a trivial echo so the LLM call cost is zero. That isolates the cost of the framework itself.

## Run

```bash
pip install -e .
python -m benchmarks.run             # full suite (~10s on M-series Mac)
python -m benchmarks.micro           # primitive operations
python -m benchmarks.e2e             # 3-agent pipeline
python -m benchmarks.compare_langgraph  # head-to-head (needs '.[bench]')
```

## What's measured

| Benchmark | What it tests |
|---|---|
| `Message.make` | C++ side: allocation, timestamp generation |
| `AgentState.append` | C++ side: `shared_mutex` write lock + vector push_back |
| `AgentState.history` | C++ side: shared_lock + vector copy |
| `MemoryCache.put/get` | C++ side: hash insert + LRU touch |
| `Router.send+drain` | C++ side: lock + push_back + drain |
| `ToolRegistry.invoke` | C++ side: lookup + Python adapter round-trip |
| 3-agent pipeline | End-to-end: 3 agents, full step + handoff per iteration |
| vs LangGraph | Orchestration-only comparison on a 1-node echo graph |

## Reading the numbers

Higher ops/s = lower per-operation overhead.
Lower p50/p99 = faster individual operations.

These numbers are **not** the speed of a real agent application — that is dominated by network latency to whichever LLM you call. They tell you how much overhead `marrow` adds on top.

If you see `marrow` outperforming LangGraph by 2-10× on the orchestration microbench but only 1.05× end-to-end, that's the expected pattern: most real workloads are I/O-bound regardless of framework choice.

## Reproducibility

- Run on a quiet machine (close browsers, disable spotlight indexing, etc).
- The JSON output (`--json out.json`) is stable enough to diff across commits.
- Numbers vary 5-15% between runs even on the same machine; treat differences below that threshold as noise.

## Caveats

- LangGraph comparison uses a trivial 1-node graph. Larger graphs add work to both sides; the relative overhead ratio is what matters.
- We do **not** publish hardware-specific numbers in the README because they go stale and vary by machine.
- For real workload comparison, wrap your actual application in a benchmark and run it.
