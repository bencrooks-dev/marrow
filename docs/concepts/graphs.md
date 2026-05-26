# Graphs

`Graph` is a fluent multi-agent workflow builder. Compose in Python, freeze for execution. No YAML, no string-eval magic.

```python
from agentcore import Graph, run_graph

g = (Graph()
     .start("researcher")
     .then("researcher", "writer")
     .then("writer", "editor", when=lambda s: "DRAFT" in s)
     .finish("editor"))

result = run_graph(rt, agents_by_name, g, initial_input="Topic: graphs.")
print(result.output)
print(result.reached_end, result.steps_taken)
```

## GraphResult

`run_graph` returns a `GraphResult`:

| Field | Meaning |
|---|---|
| `output` | The last agent's output text |
| `final_node` | Where we stopped |
| `steps_taken` | Number of agent.step() calls performed |
| `reached_end` | True iff we landed on a `finish()` node |
| `exhausted` | True iff `max_steps` was hit |

By default, `run_graph` raises `GraphExhausted` if `max_steps` is reached without finishing. Pass `raise_on_exhaustion=False` to opt out and inspect the result directly.

## Why not YAML

A fluent Python builder is introspectable, debuggable in `pdb`, and serialisable via any custom serializer. A YAML/JSON DSL ossifies before you've found the right abstraction, and inevitably ends up smuggling Python through `eval:` strings.

If you specifically want declarative configs, write a 30-line YAML→Graph adapter — but the core stays in Python where iteration is cheap.
