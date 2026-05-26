"""High-level Python SDK over the agentcore C++ engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from . import _agentcore as _c

Role = _c.Role
Message = _c.Message
MockProvider = _c.MockProvider
PyProviderBase = _c.Provider  # subclass this in Python to write a real provider


class ProviderProtocol(Protocol):
    def name(self) -> str: ...
    def generate(self, req: "_c.GenerationRequest") -> "_c.GenerationResponse": ...


def _msg(role: "_c.Role", content: str, name: str = "") -> "_c.Message":
    return _c.Message.make(role, content, name)


@dataclass
class Agent:
    """Thin Python facade over a C++ AgentState bound to a Provider."""

    name: str
    provider: ProviderProtocol
    system_prompt: Optional[str] = None
    _state: Optional["_c.AgentState"] = field(default=None, repr=False)

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
        trim_to: Optional[int],
    ) -> "_c.GenerationRequest":
        req = _c.GenerationRequest()
        req.model = model
        req.max_tokens = max_tokens
        msgs = self._state.trimmed(trim_to) if trim_to else list(self._state.history())
        if self.system_prompt:
            msgs.insert(0, _msg(Role.System, self.system_prompt))
        req.messages = msgs
        return req

    def step(
        self,
        model: str = "mock",
        max_tokens: int = 512,
        trim_to: Optional[int] = None,
    ) -> str:
        req = self._build_request(model, max_tokens, trim_to)
        resp = self.provider.generate(req)
        self.append_assistant(resp.content)
        return resp.content

    def stream(
        self,
        model: str = "mock",
        max_tokens: int = 512,
        trim_to: Optional[int] = None,
        on_chunk: Optional[callable] = None,
    ) -> str:
        """Streaming variant of `step`. Collects chunks into the final
        assistant message and returns the full text. Each chunk is also
        forwarded to `on_chunk` if provided."""
        req = self._build_request(model, max_tokens, trim_to)
        chunks: list[str] = []

        def collect(chunk: str) -> None:
            chunks.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)

        self.provider.generate_stream(req, collect)
        full = "".join(chunks)
        self.append_assistant(full)
        return full


class Runtime:
    """Owns the engine, registers agents, mediates routing and tools."""

    def __init__(self) -> None:
        self.engine = _c.Engine()

    def add(self, agent: Agent) -> Agent:
        agent._state = self.engine.create_agent(agent.name)
        if agent.system_prompt:
            agent._state.set_system_prompt(agent.system_prompt)
        return agent

    @property
    def router(self) -> "_c.AgentRouter":
        return self.engine.router

    @property
    def cache(self) -> "_c.MemoryCache":
        return self.engine.cache

    @property
    def tools(self) -> "_c.ToolRegistry":
        return self.engine.tools

    def send(self, frm: str, to: str, text: str) -> None:
        self.router.send(frm, to, _msg(Role.User, text, frm))

    def deliver(self, agent: Agent) -> int:
        delivered = self.router.drain(agent.name)
        for routed in delivered:
            agent._state.append(routed.message)
        return len(delivered)

    def handoff(self, frm: str, to: str, text: Optional[str] = None) -> bool:
        seed = _msg(Role.User, text, frm) if text else None
        return self.router.handoff(frm, to, seed)
