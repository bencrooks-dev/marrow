"""Tiny benchmark harness: print stable rows, capture timings."""
from __future__ import annotations

import gc
import json
import platform
import time
from dataclasses import asdict, dataclass


@dataclass
class Result:
    name: str
    ops: int
    duration_s: float
    p50_us: float
    p99_us: float
    ops_per_s: float


def time_loop(name: str, fn, ops: int, *, warmup: int = 1) -> Result:
    """Run `fn` `ops` times, recording per-call latencies and summary."""
    for _ in range(warmup):
        fn()
    gc.disable()
    samples: list[float] = []
    t0 = time.perf_counter()
    for _ in range(ops):
        s = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - s) * 1e6)
    elapsed = time.perf_counter() - t0
    gc.enable()
    samples.sort()
    p50 = samples[ops // 2]
    p99 = samples[min(ops - 1, int(ops * 0.99))]
    return Result(
        name=name, ops=ops, duration_s=elapsed,
        p50_us=p50, p99_us=p99, ops_per_s=ops / elapsed,
    )


def print_header(suite: str) -> None:
    print(f"\n=== {suite} ===")
    print(f"python  : {platform.python_version()}  {platform.machine()}  "
          f"{platform.system()}")
    print(f"impl    : {platform.python_implementation()}")
    print(f"{'name':40} {'ops':>9} {'p50 (μs)':>10} {'p99 (μs)':>10} "
          f"{'ops/s':>12}")
    print("-" * 88)


def print_row(r: Result) -> None:
    print(f"{r.name:40} {r.ops:>9d} {r.p50_us:>10.2f} {r.p99_us:>10.2f} "
          f"{r.ops_per_s:>12.0f}")


def emit_json(results: list[Result], path: str) -> None:
    with open(path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
