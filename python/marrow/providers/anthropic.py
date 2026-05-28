"""Anthropic provider — Messages API with streaming + prompt caching.

Requires: ``pip install 'marrow-rt[anthropic]'``

System prompts are sent with ``cache_control: ephemeral`` so repeat
calls in an agent loop benefit from Anthropic's prompt caching
(saves cost on long, stable system prompts). The first call seeds
the cache; subsequent calls hit it.
"""
from __future__ import annotations

import os

from anthropic import Anthropic

from .. import _marrow as _c
from ..sdk import PyProviderBase, raise_if_cancelled, request_timeout_seconds

_CHAT_ROLE_MAP = {
    _c.Role.User: "user",
    _c.Role.Assistant: "assistant",
}


class AnthropicProvider(PyProviderBase):
    """Provider backed by the official Anthropic Python SDK."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        client: Anthropic | None = None,
        enable_prompt_cache: bool = True,
    ) -> None:
        super().__init__()
        self._model = model
        self._enable_cache = enable_prompt_cache
        self._client = client or Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    def name(self) -> str:
        return f"anthropic:{self._model}"

    @staticmethod
    def _split_messages(messages):
        """Anthropic separates `system` from `messages`. Map roles and
        collapse any System messages into the system param."""
        system_parts: list[str] = []
        chat: list[dict] = []
        for m in messages:
            if m.role == _c.Role.System:
                system_parts.append(m.content)
            elif m.role in _CHAT_ROLE_MAP:
                chat.append({"role": _CHAT_ROLE_MAP[m.role], "content": m.content})
            elif m.role == _c.Role.Tool:
                # v0: surface tool output as user message; full tool-use
                # blocks are a v0.2 addition.
                chat.append({"role": "user",
                             "content": f"[tool:{m.name}] {m.content}"})
        return "\n\n".join(system_parts), chat

    def _build_kwargs(self, req):
        system, chat = self._split_messages(req.messages)
        kwargs = {
            "model": req.model or self._model,
            "messages": chat,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if system:
            if self._enable_cache:
                kwargs["system"] = [{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }]
            else:
                kwargs["system"] = system
        timeout = request_timeout_seconds(req)
        if timeout is not None:
            # Honored by the Anthropic SDK as a per-request wall-clock timeout.
            kwargs["timeout"] = timeout
        return kwargs

    @staticmethod
    def _extract_text(content_blocks) -> str:
        """Concatenate text from all TextBlock entries; ignore tool_use
        and other non-text blocks (we don't process tool calls in v0)."""
        if not content_blocks:
            return ""
        parts = []
        for block in content_blocks:
            # SDK returns objects with a `type` attribute; "text" blocks
            # have a `.text` attribute. tool_use, etc. have no `.text`.
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)

    def generate(self, req):
        raise_if_cancelled(req)
        resp = self._client.messages.create(**self._build_kwargs(req))
        out = _c.GenerationResponse()
        out.content = self._extract_text(resp.content)
        out.prompt_tokens = resp.usage.input_tokens
        out.completion_tokens = resp.usage.output_tokens
        return out

    def generate_stream(self, req, on_chunk):
        raise_if_cancelled(req)
        with self._client.messages.stream(**self._build_kwargs(req)) as stream:
            for text in stream.text_stream:
                raise_if_cancelled(req)
                on_chunk(text)
