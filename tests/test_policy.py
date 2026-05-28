"""RetryPolicy + RateLimiter."""
from __future__ import annotations

import time

import pytest

from marrow import RateLimiter, RetryPolicy

# --- RetryPolicy ---------------------------------------------------------

def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    p = RetryPolicy(attempts=5, base_delay=0.001)
    assert p.run(flaky) == "ok"
    assert calls["n"] == 3


def test_retry_exhausts_and_reraises_last():
    p = RetryPolicy(attempts=3, base_delay=0.001)
    with pytest.raises(ValueError, match="final"):
        p.run(lambda: (_ for _ in ()).throw(ValueError("final")))


def test_retry_does_not_retry_skip_exceptions():
    """KeyboardInterrupt / SystemExit should propagate immediately."""
    p = RetryPolicy(attempts=5, base_delay=0.001)
    n = {"v": 0}

    def fn():
        n["v"] += 1
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        p.run(fn)
    assert n["v"] == 1


# --- RateLimiter ---------------------------------------------------------

def test_rate_limiter_capacity_burst():
    rl = RateLimiter(rate=100, capacity=5)
    # Burst up to capacity should succeed immediately.
    for _ in range(5):
        assert rl.try_acquire(1.0)
    # Sixth should fail try_acquire (no time for refill yet).
    assert not rl.try_acquire(1.0)


def test_rate_limiter_refills():
    rl = RateLimiter(rate=200, capacity=2)  # 200 tokens/s ⇒ 5ms per token
    for _ in range(2):
        rl.try_acquire(1.0)
    time.sleep(0.05)  # ~10 tokens accumulated; capped at capacity=2
    assert rl.try_acquire(1.0)


def test_rate_limiter_acquire_blocks_until_available():
    rl = RateLimiter(rate=1000, capacity=1)
    rl.try_acquire(1.0)
    t0 = time.perf_counter()
    ok = rl.acquire(1.0, timeout=0.5)
    elapsed = time.perf_counter() - t0
    assert ok
    # Should have waited briefly but not the full timeout.
    assert elapsed < 0.5
