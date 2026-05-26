"""Ollama provider — talks to a local Ollama daemon via its HTTP API.

Requires: ``pip install 'agentcore[ollama]'`` (which installs ``httpx``).
No API key needed; defaults to http://localhost:11434.
"""
from __future__ import annotations

import json
from typing import Optional

import httpx

from .. import _agentcore as _c
from ..sdk import PyProviderBase


_ROLE_MAP = {
    _c.Role.System: "system",
    _c.Role.User: "user",
    _c.Role.Assistant: "assistant",
    _c.Role.Tool: "tool",
}


class OllamaProvider(PyProviderBase):
    """Provider backed by an Ollama daemon."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        super().__init__()
        self._model = model
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def name(self) -> str:
        return f"ollama:{self._model}"

    def _payload(self, req, *, stream: bool) -> dict:
        return {
            "model": req.model or self._model,
            "messages": [
                {"role": _ROLE_MAP[m.role], "content": m.content}
                for m in req.messages
            ],
            "stream": stream,
            "options": {
                "temperature": req.temperature,
                "num_predict": req.max_tokens,
            },
        }

    def generate(self, req):
        r = self._client.post(f"{self._base}/api/chat",
                              json=self._payload(req, stream=False))
        r.raise_for_status()
        data = r.json()
        out = _c.GenerationResponse()
        out.content = data.get("message", {}).get("content", "")
        out.prompt_tokens = data.get("prompt_eval_count", 0) or 0
        out.completion_tokens = data.get("eval_count", 0) or 0
        return out

    def generate_stream(self, req, on_chunk):
        with self._client.stream("POST", f"{self._base}/api/chat",
                                 json=self._payload(req, stream=True)) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message") or {}
                content = msg.get("content")
                if content:
                    on_chunk(content)
                if obj.get("done"):
                    break
