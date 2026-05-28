"""High-level Python SDK over the agentcore C++ engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from . import _agentcore as _c
from .policy import RateLimiter, RetryPolicy
from .tracing import TraceSink, get_default_sink
from .usage import UsageRecord, UsageTracker

Role = _c.Role
Message = _c.Message
MockProvider = _c.MockProvider
PyProviderBase = _c.Provider  # subclass this in Python to write a real provider
CancelToken = _c.CancelToken
OverflowPolicy = _c.OverflowPolicy


def request_timeout_seconds(req) -> float | None:
    """Convert a GenerationRequest's timeout_ms into seconds for provider
    SDKs that take a wall-clock timeout. Returns None when unset (0), so
    the provider's own default applies."""
    ms = getattr(req, "timeout_ms", 0) or 0
    return (ms / 1000.0) if ms > 0 else None


def raise_if_cancelled(req) -> None:
    """Raise if the request carries an already-cancelled CancelToken.

    Providers SHOULD call this at entry and at streaming yield points so a
    cancellation requested from another thread is honored promptly (ARI §3.5).
    """
    ct = getattr(req, "cancel_token", None)
    if ct is not None and ct.cancelled():
        raise RuntimeError("generation cancelled")


class ProviderProtocol(Protocol):
    def name(self) -> str: ...
    def generate(self, req: _c.GenerationRequest) -> _c.GenerationResponse: ...


def _msg(role: _c.Role, content: str, name: str = "") -> _c.Message:
    return _c.Message.make(role, content, name)


@dataclass
class Agent:
    """Thin Python facade over a C++ AgentState bound to a Provider."""

    name: str
    provider: ProviderProtocol
    system_prompt: str | None = None
    _state: _c.AgentState | None = field(default=None, repr=False)
    # Per-agent runtime hooks. These are populated by Runtime.add() so
    # callers can configure policy at the Runtime level and have it
    # automatically apply to every agent.
    _runtime: Runtime | None = field(default=None, repr=False)

    def append_user(self, text: str) -> None:
        self._state.append(_msg(Role.User, text))

    def append_assistant(self, text: str) -> None:
        self._state.append(_msg(Role.Assistant, text, self.name))

    def append_tool(self, tool_name: str, text: str) -> None:
        self._state.append(_msg(Role.Tool, text, tool_name))

    def _build_request(
        self,
        model: str,
        max_tokens: int,
        trim_to: int | None,
        temperature: float | None,
        timeout_ms: int = 0,
        cancel_token: _c.CancelToken | None = None,
    ) -> _c.GenerationRequest:
        req = _c.GenerationRequest()
        req.model = model
        req.max_tokens = max_tokens
        if temperature is not None:
            req.temperature = temperature
        if timeout_ms > 0:
            req.timeout_ms = timeout_ms
        if cancel_token is not None:
            req.cancel_token = cancel_token
        msgs = self._state.trimmed(trim_to) if trim_to else list(self._state.history())
        if self.system_prompt:
            msgs.insert(0, _msg(Role.System, self.system_prompt))
        req.messages = msgs
        return req

    def _invoke_provider(self, do_call):
        """Wrap provider invocation in rate limit + retry + tracing +
        usage if the Runtime supplied them. Plain pass-through if not."""
        rt = self._runtime
        if rt is None:
            return do_call()

        sink = rt.trace_sink
        with sink.span("agent.step", {"agent": self.name, "provider": self.provider.name()}) as sp:
            if rt.rate_limiter is not None:
                rt.rate_limiter.acquire(1.0)
            try:
                if rt.retry_policy is not None:
                    result = rt.retry_policy.run(do_call)
                else:
                    result = do_call()
                sp.set_status(True)
                return result
            except BaseException as e:
                sp.record_exception(e)
                raise

    def step(
        self,
        model: str = "mock",
        max_tokens: int = 512,
        trim_to: int | None = None,
        temperature: float | None = None,
        timeout_ms: int = 0,
        cancel_token: _c.CancelToken | None = None,
    ) -> str:
        if cancel_token is not None and cancel_token.cancelled():
            raise RuntimeError("operation cancelled before provider call")
        req = self._build_request(model, max_tokens, trim_to, temperature,
                                  timeout_ms, cancel_token)

        def do_call():
            resp = self.provider.generate(req)
            # Usage tracking: best-effort. Providers that don't fill in
            # token counts will contribute zeros, which is correct.
            rt = self._runtime
            if rt is not None and rt.usage is not None:
                rt.usage.record(UsageRecord(
                    agent=self.name,
                    model=req.model or self.provider.name(),
                    prompt_tokens=int(resp.prompt_tokens or 0),
                    completion_tokens=int(resp.completion_tokens or 0),
                ))
            return resp

        resp = self._invoke_provider(do_call)
        self.append_assistant(resp.content)
        return resp.content

    def stream(
        self,
        model: str = "mock",
        max_tokens: int = 512,
        trim_to: int | None = None,
        temperature: float | None = None,
        on_chunk: callable | None = None,
        timeout_ms: int = 0,
        cancel_token: _c.CancelToken | None = None,
    ) -> str:
        """Streaming variant of `step`. Collects chunks into the final
        assistant message and returns the full text. Each chunk is also
        forwarded to `on_chunk` if provided."""
        if cancel_token is not None and cancel_token.cancelled():
            raise RuntimeError("operation cancelled before provider call")
        req = self._build_request(model, max_tokens, trim_to, temperature,
                                  timeout_ms, cancel_token)
        chunks: list[str] = []

        def collect(chunk: str) -> None:
            chunks.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)

        def do_call():
            self.provider.generate_stream(req, collect)
            return None

        self._invoke_provider(do_call)
        full = "".join(chunks)
        self.append_assistant(full)
        return full


class Runtime:
    """Owns the engine, registers agents, mediates routing and tools.

    Optional cross-cutting concerns (rate limiting, retry, tracing,
    usage accounting) are configured at construction time and applied
    automatically to every agent that this Runtime owns.
    """

    def __init__(
        self,
        *,
        rate_limiter: RateLimiter | None = None,
        retry_policy: RetryPolicy | None = None,
        trace_sink: TraceSink | None = None,
        usage: UsageTracker | None = None,
    ) -> None:
        self.engine = _c.Engine()
        self.rate_limiter = rate_limiter
        self.retry_policy = retry_policy
        self.trace_sink = trace_sink or get_default_sink()
        self.usage = usage

    def add(self, agent: Agent) -> Agent:
        agent._state = self.engine.create_agent(agent.name)
        agent._runtime = self
        if agent.system_prompt:
            agent._state.set_system_prompt(agent.system_prompt)
        return agent

    @property
    def router(self) -> _c.AgentRouter:
        return self.engine.router

    @property
    def cache(self) -> _c.MemoryCache:
        return self.engine.cache

    @property
    def tools(self) -> _c.ToolRegistry:
        return self.engine.tools

    def send(self, frm: str, to: str, text: str) -> None:
        self.router.send(frm, to, _msg(Role.User, text, frm))

    def deliver(self, agent: Agent) -> int:
        delivered = self.router.drain(agent.name)
        for routed in delivered:
            agent._state.append(routed.message)
        return len(delivered)

    def handoff(self, frm: str, to: str, text: str | None = None) -> bool:
        seed = _msg(Role.User, text, frm) if text else None
        return self.router.handoff(frm, to, seed)

    def shutdown(self) -> None:
        """Signal that no new top-level work should start. After this,
        `engine.is_shutdown()` is True and `create_agent` calls throw.
        In-flight work in other threads is allowed to finish."""
        self.engine.shutdown()
