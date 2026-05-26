# Providers

A `Provider` is anything that implements `name()`, `generate(req)`, and `generate_stream(req, on_chunk)`. The base class lives in C++ (`agentcore.PyProviderBase`); Python subclasses are wired through a Pybind11 trampoline so C++ can call back into Python.

## Built-in providers

```python
from agentcore.providers import OpenAIProvider, AnthropicProvider, OllamaProvider

openai     = OpenAIProvider(model="gpt-4o-mini")
anthropic  = AnthropicProvider(model="claude-sonnet-4-6")  # caches system prompt
ollama     = OllamaProvider(model="llama3.2")              # local daemon
```

Each requires its respective install extra: `agentcore[openai]`, `agentcore[anthropic]`, `agentcore[ollama]`.

## Writing your own provider

```python
from agentcore import GenerationResponse, PyProviderBase

class MyProvider(PyProviderBase):
    def name(self):
        return "my-provider"

    def generate(self, req):
        # req.messages, req.model, req.temperature, req.max_tokens
        # req.timeout_ms, req.cancel_token
        out = GenerationResponse()
        out.content = self._call_my_api(req)
        out.prompt_tokens = ...
        out.completion_tokens = ...
        return out

    def generate_stream(self, req, on_chunk):
        for chunk in self._stream_my_api(req):
            on_chunk(chunk)
            if req.cancel_token and req.cancel_token.cancelled():
                break
```

## Respecting timeouts and cancellation

```python
import time

def generate(self, req):
    deadline = (time.monotonic() + req.timeout_ms / 1000.0) if req.timeout_ms else None
    while not_done():
        if req.cancel_token and req.cancel_token.cancelled():
            raise RuntimeError("cancelled")
        if deadline and time.monotonic() > deadline:
            raise RuntimeError(f"timeout after {req.timeout_ms}ms")
        ...
```

## Anthropic prompt caching

`AnthropicProvider` enables prompt caching on the system prompt automatically:

```python
provider = AnthropicProvider(model="claude-sonnet-4-6", enable_prompt_cache=True)
```

Set `enable_prompt_cache=False` to opt out.
