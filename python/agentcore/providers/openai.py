"""OpenAI provider — Chat Completions API with streaming support.

Requires: ``pip install 'agentcore[openai]'``
"""
from __future__ import annotations

import os

from openai import OpenAI

from .. import _agentcore as _c
from ..sdk import PyProviderBase, raise_if_cancelled, request_timeout_seconds

_ROLE_MAP = {
    _c.Role.System: "system",
    _c.Role.User: "user",
    _c.Role.Assistant: "assistant",
    _c.Role.Tool: "tool",
}


class OpenAIProvider(PyProviderBase):
    """Provider backed by the official OpenAI Python SDK."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        client: OpenAI | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__()
        self._model = model
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(
                api_key=api_key or os.environ.get("OPENAI_API_KEY"),
                base_url=base_url,
            )

    def name(self) -> str:
        return f"openai:{self._model}"

    def _to_messages(self, msgs):
        return [
            {"role": _ROLE_MAP[m.role], "content": m.content}
            for m in msgs
        ]

    def _create_kwargs(self, req, *, stream: bool) -> dict:
        kwargs = {
            "model": req.model or self._model,
            "messages": self._to_messages(req.messages),
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if stream:
            kwargs["stream"] = True
        timeout = request_timeout_seconds(req)
        if timeout is not None:
            # Honored by the OpenAI SDK as a per-request wall-clock timeout.
            kwargs["timeout"] = timeout
        return kwargs

    def generate(self, req):
        raise_if_cancelled(req)
        resp = self._client.chat.completions.create(
            **self._create_kwargs(req, stream=False)
        )
        out = _c.GenerationResponse()
        out.content = resp.choices[0].message.content or ""
        if resp.usage:
            out.prompt_tokens = resp.usage.prompt_tokens
            out.completion_tokens = resp.usage.completion_tokens
        return out

    def generate_stream(self, req, on_chunk):
        raise_if_cancelled(req)
        stream = self._client.chat.completions.create(
            **self._create_kwargs(req, stream=True)
        )
        for chunk in stream:
            raise_if_cancelled(req)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                on_chunk(delta)
