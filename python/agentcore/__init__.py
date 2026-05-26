"""agentcore — lightweight C++ core for AI agent orchestration."""

from . import _agentcore as _c
from . import providers
from .asyncio_bridge import AsyncAgent, AsyncRuntime, to_thread
from .graph import Graph, GraphExhausted, GraphResult
from .graph import run as run_graph
from .sdk import Agent, MockProvider, PyProviderBase, Runtime
from .tools import ToolBox, tool

Role = _c.Role
Message = _c.Message
GenerationRequest = _c.GenerationRequest
GenerationResponse = _c.GenerationResponse

__all__ = [
    "Agent",
    "Runtime",
    "MockProvider",
    "PyProviderBase",
    "Role",
    "Message",
    "GenerationRequest",
    "GenerationResponse",
    "tool",
    "ToolBox",
    "Graph",
    "GraphResult",
    "GraphExhausted",
    "run_graph",
    "AsyncAgent",
    "AsyncRuntime",
    "to_thread",
    "providers",
]

__version__ = "0.0.3"
