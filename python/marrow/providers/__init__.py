"""Real LLM provider implementations.

Imports are lazy so that ``import marrow`` does not require the
``openai`` / ``anthropic`` / ``httpx`` packages. The provider modules
import their backing SDKs at module load; we catch that to produce a
helpful install hint.
"""
from __future__ import annotations


def __getattr__(name: str):
    if name == "OpenAIProvider":
        try:
            from .openai import OpenAIProvider
        except ImportError as e:
            raise ImportError(
                "OpenAIProvider requires the openai SDK. "
                "Install with: pip install 'marrow-rt[openai]'"
            ) from e
        return OpenAIProvider

    if name == "AnthropicProvider":
        try:
            from .anthropic import AnthropicProvider
        except ImportError as e:
            raise ImportError(
                "AnthropicProvider requires the anthropic SDK. "
                "Install with: pip install 'marrow-rt[anthropic]'"
            ) from e
        return AnthropicProvider

    if name == "OllamaProvider":
        try:
            from .ollama import OllamaProvider
        except ImportError as e:
            raise ImportError(
                "OllamaProvider requires httpx. "
                "Install with: pip install 'marrow-rt[ollama]'"
            ) from e
        return OllamaProvider

    raise AttributeError(f"module 'marrow.providers' has no attribute {name!r}")


__all__ = ["OpenAIProvider", "AnthropicProvider", "OllamaProvider"]
