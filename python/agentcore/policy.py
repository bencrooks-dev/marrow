"""Retry policies and rate limiters.

Both are deliberately stateless functors so they can be passed through
the public API without smuggling locks or singletons. The
:class:`RateLimiter` is the exception — it carries a token bucket and is
therefore stateful and thread-safe.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

T = TypeVar("T")


# --- retry ---------------------------------------------------------------

@dataclass
class RetryPolicy:
    """Exponential backoff with jitter.

    ``attempts`` is the total number of tries including the first call.
    ``base_delay`` is the wait after the first failure. Each retry
    doubles the wait, capped at ``max_delay``. A random jitter of up to
    ``jitter`` * delay is added to avoid thundering herd.
    """
    attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 30.0
    jitter: float = 0.2
    # Exceptions that should be retried. By default we retry everything
    # except CancelledError / KeyboardInterrupt / SystemExit.
    retry_on: tuple[type[BaseException], ...] = (Exception,)
    skip: tuple[type[BaseException], ...] = (
        KeyboardInterrupt, SystemExit, MemoryError,
    )

    def run(self, fn: Callable[[], T]) -> T:
        last_exc: BaseException | None = None
        delay = self.base_delay
        for attempt in range(1, max(1, self.attempts) + 1):
            try:
                return fn()
            except self.skip:
                raise
            except self.retry_on as e:
                last_exc = e
                if attempt >= self.attempts:
                    break
                sleep_for = min(delay, self.max_delay)
                sleep_for += random.random() * self.jitter * sleep_for
                time.sleep(sleep_for)
                delay *= 2
        # We only reach here when retries are exhausted.
        assert last_exc is not None
        raise last_exc


# --- rate limit ----------------------------------------------------------

@dataclass
class RateLimiter:
    """Token-bucket rate limiter. Thread-safe.

    ``rate`` is tokens added per second; ``capacity`` is the bucket size
    (also the maximum burst). ``acquire(n)`` blocks until ``n`` tokens
    are available.
    """
    rate: float
    capacity: float
    _tokens: float = field(default=0.0, init=False)
    _last: float = field(default_factory=time.monotonic, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity

    def _refill_locked(self) -> None:
        now = time.monotonic()
        delta = (now - self._last) * self.rate
        if delta > 0:
            self._tokens = min(self.capacity, self._tokens + delta)
            self._last = now

    def try_acquire(self, n: float = 1.0) -> bool:
        """Take ``n`` tokens if available; return False otherwise."""
        with self._lock:
            self._refill_locked()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def acquire(self, n: float = 1.0, timeout: float | None = None) -> bool:
        """Take ``n`` tokens, sleeping until they're available. Returns
        False if a timeout expires without acquiring."""
        deadline = (time.monotonic() + timeout) if timeout is not None else None
        while True:
            with self._lock:
                self._refill_locked()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                # How long until n tokens accumulate at our refill rate?
                need = n - self._tokens
                wait = need / self.rate if self.rate > 0 else float("inf")
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            time.sleep(max(0.0, min(wait, 0.1)))  # cap sleep for responsiveness
