# Async / concurrency

The C++ core releases the GIL on `Provider::generate` and `generate_stream`. The Python `AsyncRuntime` wraps blocking calls in a `ThreadPoolExecutor` so concurrent agent steps make real parallel progress.

```python
import asyncio
from marrow import AsyncRuntime, Agent, MockProvider, Runtime

async def main():
    rt = AsyncRuntime(Runtime())
    agents = [rt.add(Agent(f"w{i}", MockProvider())) for i in range(8)]
    for i, a in enumerate(agents):
        a.append_user(f"hello from worker {i}")
    results = await rt.gather_steps(agents)
    for i, r in enumerate(results):
        print(f"[{i}] {r}")

asyncio.run(main())
```

## Why not C++ coroutines?

C++ async is a maintenance trap for an early-stage OSS project (Boost.Asio is heavyweight, C++20 coroutines bind poorly through Pybind11, hand-rolled is fragile). Python's `asyncio` ecosystem is mature, the GIL releases on the hot paths anyway, and a `ThreadPoolExecutor` scales linearly with provider concurrency.

When/if the day comes to move concurrency into C++, the `AsyncRuntime` surface stays the same — only the internals change.

## Tuning the executor

```python
import concurrent.futures
from marrow.asyncio_bridge import set_executor

set_executor(concurrent.futures.ThreadPoolExecutor(max_workers=32))
```
