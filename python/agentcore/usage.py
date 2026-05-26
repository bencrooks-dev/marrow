"""Token usage / cost accounting.

A :class:`UsageTracker` aggregates prompt + completion tokens across
provider calls, optionally tagged by agent name and model. Pricing
tables are configurable; with no pricing the tracker still records raw
token counts.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class UsageRecord:
    agent: str
    model: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class _Aggregate:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0


# Prices are USD per 1,000 tokens, (prompt, completion). Update as
# providers change pricing; callers can also supply their own table.
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI (illustrative — verify before relying on these for billing)
    "gpt-4o":          (2.50 / 1000, 10.00 / 1000),
    "gpt-4o-mini":     (0.15 / 1000, 0.60 / 1000),
    # Anthropic
    "claude-opus-4-7":     (15.00 / 1000, 75.00 / 1000),
    "claude-sonnet-4-6":   (3.00 / 1000, 15.00 / 1000),
    "claude-haiku-4-5":    (1.00 / 1000, 5.00 / 1000),
}


class UsageTracker:
    """Thread-safe accumulator of token usage and (optional) cost."""

    def __init__(
        self,
        pricing: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._pricing = pricing if pricing is not None else dict(DEFAULT_PRICING)
        self._records: list[UsageRecord] = []
        self._by_agent: dict[str, _Aggregate] = {}
        self._by_model: dict[str, _Aggregate] = {}
        self._total = _Aggregate()

    def record(self, rec: UsageRecord) -> None:
        with self._lock:
            self._records.append(rec)
            for bucket, key in ((self._by_agent, rec.agent),
                                (self._by_model, rec.model)):
                agg = bucket.setdefault(key, _Aggregate())
                agg.prompt_tokens += rec.prompt_tokens
                agg.completion_tokens += rec.completion_tokens
                agg.calls += 1
            self._total.prompt_tokens += rec.prompt_tokens
            self._total.completion_tokens += rec.completion_tokens
            self._total.calls += 1

    def totals(self) -> _Aggregate:
        with self._lock:
            agg = self._total
            return _Aggregate(agg.prompt_tokens, agg.completion_tokens, agg.calls)

    def by_agent(self) -> dict[str, _Aggregate]:
        with self._lock:
            return {k: _Aggregate(v.prompt_tokens, v.completion_tokens, v.calls)
                    for k, v in self._by_agent.items()}

    def by_model(self) -> dict[str, _Aggregate]:
        with self._lock:
            return {k: _Aggregate(v.prompt_tokens, v.completion_tokens, v.calls)
                    for k, v in self._by_model.items()}

    def estimated_cost(self, currency: str = "USD") -> float:
        """Sum prompt+completion tokens × the configured per-model rate.
        Unknown models contribute 0; tracker exposes the raw counts so
        callers can apply their own pricing if they prefer."""
        with self._lock:
            cost = 0.0
            for model, agg in self._by_model.items():
                price = self._pricing.get(model)
                if price is None:
                    continue
                p_rate, c_rate = price
                cost += agg.prompt_tokens * p_rate
                cost += agg.completion_tokens * c_rate
            return cost
