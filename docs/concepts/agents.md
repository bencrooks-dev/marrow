# Agents and Runtime

An `Agent` is a thin Python facade over a C++ `AgentState`. State (message history, system prompt) lives in C++; the Python class adds policy (which provider to call, how to format requests, when to step).

A `Runtime` owns the `Engine`, registers agents, and provides routing + persistence + tracing + usage tracking helpers.

## Creating agents

```python
from agentcore import Agent, Runtime, MockProvider

rt = Runtime()
agent = rt.add(Agent(name="researcher",
                     provider=MockProvider(),
                     system_prompt="You research a topic and answer in bullets."))
```

## Stepping

```python
agent.append_user("Find three facts about graph databases.")
output = agent.step()
```

`Agent.step()` accepts `model`, `max_tokens`, `temperature`, `trim_to`, `timeout_ms`, `cancel_token`. The system prompt is automatically prepended.

## Streaming

```python
agent.stream(on_chunk=lambda c: print(c, end="", flush=True))
```

Same arguments as `step` plus `on_chunk`. The full text is also appended to history.

## Routing

```python
rt.send(frm="user", to="researcher", text="Topic: graph databases")
rt.deliver(agent)   # move inbox into history
rt.handoff(frm="researcher", to="writer", text="research result here")
```

## Cancellation

```python
from agentcore import CancelToken

token = CancelToken()
# ... start work, in another thread:
token.cancel()
# Long-running providers should check `req.cancel_token.cancelled()` and bail.
```

## Per-agent policies via Runtime

Cross-cutting concerns are configured on the `Runtime` and apply to every agent it owns:

```python
from agentcore import Runtime, RateLimiter, RetryPolicy, PrintTraceSink, UsageTracker

rt = Runtime(
    rate_limiter=RateLimiter(rate=10, capacity=20),    # 10 calls/s, burst 20
    retry_policy=RetryPolicy(attempts=3, base_delay=0.5),
    trace_sink=PrintTraceSink(),
    usage=UsageTracker(),
)
```
