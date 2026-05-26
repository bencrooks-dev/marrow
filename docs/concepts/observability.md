# Observability

`agentcore` exposes three hooks for production observability:

- **`TraceSink`** — emit spans around `agent.step`, `provider.generate`, `tool.invoke`.
- **`UsageTracker`** — count tokens and estimate cost per agent and per model.
- **Structured logging** — opt-in JSON-line output via `agentcore.logging_config`.

## Tracing

The default sink is `NullTraceSink` (zero overhead). For development, use `PrintTraceSink`:

```python
from agentcore import PrintTraceSink, Runtime

rt = Runtime(trace_sink=PrintTraceSink())
```

For production, wrap an OpenTelemetry tracer:

```python
from opentelemetry import trace
from agentcore import OpenTelemetryTraceSink, Runtime

tracer = trace.get_tracer("my-app")
rt = Runtime(trace_sink=OpenTelemetryTraceSink(tracer))
```

Spans currently emitted by the SDK: `agent.step`. Adding more spans in C++ is a v0.2 item; the interface is in place.

## Usage tracking

```python
from agentcore import Runtime, UsageTracker

usage = UsageTracker()
rt = Runtime(usage=usage)

# ... run some agents ...

print(usage.totals())
print(usage.by_agent())
print(usage.by_model())
print(f"~${usage.estimated_cost():.4f}")
```

The default pricing table covers OpenAI's gpt-4o family and Anthropic's claude-* family. Override with your own:

```python
usage = UsageTracker(pricing={
    "gpt-4o-mini": (0.15 / 1000, 0.60 / 1000),    # (prompt $/tok, completion $/tok)
    "claude-sonnet-4-6": (3.00 / 1000, 15.00 / 1000),
})
```

## Structured logging

```python
import agentcore.logging_config as lc
lc.configure_json(level="INFO")

import logging
logging.getLogger("agentcore").info("started", extra={"agent": "alice"})
```

Output:

```json
{"ts": 1716750000.123, "level": "INFO", "logger": "agentcore", "msg": "started", "agent": "alice"}
```
