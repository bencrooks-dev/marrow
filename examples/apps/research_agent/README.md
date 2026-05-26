# research_agent

A small but real agentcore application: a three-agent pipeline that researches a topic, writes a draft, and polishes it. Demonstrates:

- Multi-agent handoff via `Graph`
- Real provider (defaults to `MockProvider`; flip to OpenAI/Anthropic via env)
- Tools registered through `ToolBox` (a stub "search" tool)
- Token usage tracking + cost estimate
- Structured tracing to stderr
- Persistence — save the conversation to SQLite and resume on restart

## Run

```bash
# from repo root
pip install -e ".[all]"

# with mock provider (no keys needed)
python -m examples.apps.research_agent --topic "graph databases"

# with a real provider
ANTHROPIC_API_KEY=sk-ant-... python -m examples.apps.research_agent \
    --topic "graph databases" \
    --provider anthropic \
    --model claude-sonnet-4-6
```

## What it shows

```
$ python -m examples.apps.research_agent --topic "graph databases"
[trace] starting pipeline for: graph databases
[researcher] ...
[writer] ...
[editor] ...

== usage ==
prompt tokens     :   1240
completion tokens :    580
estimated cost    : $0.0012
```

## What this proves

That `agentcore` can drive a real-shaped agent application — three agents, a graph, tools, observability, persistence — without falling apart at the seams. Use this as a template for your own app.
