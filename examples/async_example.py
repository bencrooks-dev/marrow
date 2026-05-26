"""asyncio bridge — concurrent agent steps backed by C++ GIL release."""
import asyncio
import time

from agentcore import Agent, AsyncRuntime, MockProvider, Runtime


async def main() -> None:
    rt = AsyncRuntime(Runtime())
    provider = MockProvider("local")

    agents = [
        rt.add(Agent(name=f"worker-{i}", provider=provider,
                     system_prompt=f"You are worker {i}."))
        for i in range(4)
    ]
    for i, a in enumerate(agents):
        a.append_user(f"hello from main, worker {i}")

    t0 = time.perf_counter()
    results = await rt.gather_steps(agents)
    elapsed = time.perf_counter() - t0

    for i, r in enumerate(results):
        print(f"[worker-{i}] {r}")
    print(f"\n4 concurrent steps in {elapsed*1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
