"""agentcore — lightweight C++ core for AI agent orchestration."""

from . import _agentcore as _c

from .sdk import Agent, Runtime, MockProvider, PyProviderBase
from .tools import tool, ToolBox
from .graph import Graph, run as run_graph
from .asyncio_bridge import AsyncAgent, AsyncRuntime, to_thread

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
    "run_graph",
    "AsyncAgent",
    "AsyncRuntime",
    "to_thread",
]

__version__ = "0.0.1"
