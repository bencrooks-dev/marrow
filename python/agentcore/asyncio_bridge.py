"""asyncio compatibility layer.

Resolves the 'async-by-default in C++' resistance. Instead of
building a C++ coroutine machine, we keep the core synchronous
and provide awaitable wrappers on the Python side. The Pybind11
``call_guard<py::gil_scoped_release>`` on provider calls already
releases the GIL, so a thread-pool executor scales linearly with
network-bound providers.

When/if the day comes to push concurrency into C++, the surface
changed here stays the same — only the implementation moves.
"""
from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
from functools import partial
from typing import Any, Callable

_DEFAULT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="agentcore-async"
)


@atexit.register
def _shutdown_default_executor() -> None:
    # On some platforms (notably Windows) leaving worker threads alive
    # at interpreter exit can hang. Shutdown is non-blocking; in-flight
    # work is allowed to finish but no new work is accepted.
    _DEFAULT_EXECUTOR.shutdown(wait=False)


def set_executor(executor: concurrent.futures.Executor) -> None:
    """Override the default executor (useful for tests / pool tuning).

    The previous executor is shut down to release its worker threads."""
    global _DEFAULT_EXECUTOR
    old = _DEFAULT_EXECUTOR
    _DEFAULT_EXECUTOR = executor
    old.shutdown(wait=False)


async def to_thread(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """Run a blocking function on the shared executor.

    Equivalent to ``asyncio.to_thread`` but with a tunable pool.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_DEFAULT_EXECUTOR, partial(fn, *args, **kwargs))


class AsyncAgent:
    """Awaitable wrapper around an SDK Agent."""

    def __init__(self, agent) -> None:
        self._agent = agent

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def inner(self):
        return self._agent

    async def step(self, model: str = "mock", max_tokens: int = 512) -> str:
        return await to_thread(self._agent.step, model=model, max_tokens=max_tokens)

    def append_user(self, text: str) -> None:
        self._agent.append_user(text)


class AsyncRuntime:
    """Awaitable wrapper around an SDK Runtime."""

    def __init__(self, runtime) -> None:
        self._rt = runtime

    @property
    def inner(self):
        return self._rt

    def add(self, agent) -> AsyncAgent:
        self._rt.add(agent)
        return AsyncAgent(agent)

    async def gather_steps(self, agents: list[AsyncAgent]) -> list[str]:
        """Step many agents concurrently. Each step releases the GIL
        during the provider call, so this scales with the executor pool."""
        return await asyncio.gather(*(a.step() for a in agents))

    def handoff(self, frm: str, to: str, text: str | None = None) -> bool:
        return self._rt.handoff(frm, to, text)

    def deliver(self, agent: AsyncAgent) -> int:
        return self._rt.deliver(agent.inner)
