"""research_agent — three-agent research → write → edit pipeline.

This is a small but real agentcore application. Run with::

    python -m examples.apps.research_agent --topic "graph databases"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agentcore import (
    Agent,
    Graph,
    MockProvider,
    PrintTraceSink,
    Runtime,
    SQLiteStateStore,
    ToolBox,
    UsageTracker,
    restore_into,
    run_graph,
    tool,
)


@tool(description="Search the web for facts about a topic (stubbed)")
def search(topic: str, max_results: int = 5) -> list[str]:
    """Stub — in a real app this would call a search API."""
    return [
        f"Fact about {topic}: nodes connect via edges",
        f"Fact about {topic}: queries use traversals not joins",
        f"Fact about {topic}: index-free adjacency is the key property",
    ][:max_results]


def _make_provider(name: str, model: str | None):
    """Resolve a Provider by short name. Falls back to MockProvider."""
    if name == "openai":
        from agentcore.providers import OpenAIProvider
        return OpenAIProvider(model=model or "gpt-4o-mini")
    if name == "anthropic":
        from agentcore.providers import AnthropicProvider
        return AnthropicProvider(model=model or "claude-sonnet-4-6")
    if name == "ollama":
        from agentcore.providers import OllamaProvider
        return OllamaProvider(model=model or "llama3.2")
    return MockProvider(model or "mock")


def build_pipeline(provider, *, with_tracing: bool, with_usage: bool,
                   db_path: Path | None):
    """Construct the Runtime, agents, graph, and (optionally) restore from disk."""
    rt = Runtime(
        trace_sink=PrintTraceSink() if with_tracing else None,
        usage=UsageTracker() if with_usage else None,
    )

    researcher = rt.add(Agent(
        "researcher", provider,
        system_prompt="You research the user's topic and return concise bullet points."))
    writer = rt.add(Agent(
        "writer", provider,
        system_prompt="You write a short essay from research bullets."))
    editor = rt.add(Agent(
        "editor", provider,
        system_prompt="You polish the writer's draft and return a final version."))

    # Register the search tool.
    ToolBox().add(search).bind(rt)

    g = (Graph()
         .start("researcher")
         .then("researcher", "writer")
         .then("writer", "editor")
         .finish("editor"))

    agents_by_name = {"researcher": researcher, "writer": writer, "editor": editor}

    # Persistence: rehydrate from disk if a snapshot exists.
    store = SQLiteStateStore(db_path) if db_path else None
    if store is not None:
        for name in agents_by_name:
            if restore_into(rt, name, store):
                print(f"[restored] {name} from {db_path}", file=sys.stderr)

    return rt, agents_by_name, g, store


def main() -> int:
    p = argparse.ArgumentParser(description="research_agent example app")
    p.add_argument("--topic", default="graph databases",
                   help="Topic for the research pipeline")
    p.add_argument("--provider", default="mock",
                   choices=["mock", "openai", "anthropic", "ollama"])
    p.add_argument("--model", default=None,
                   help="Model name override for the chosen provider")
    p.add_argument("--persist", default=None,
                   help="SQLite path to save+restore state (default: no persistence)")
    p.add_argument("--no-trace", action="store_true")
    p.add_argument("--no-usage", action="store_true")
    args = p.parse_args()

    provider = _make_provider(args.provider, args.model)
    db_path = Path(args.persist) if args.persist else None

    rt, agents, graph, store = build_pipeline(
        provider,
        with_tracing=not args.no_trace,
        with_usage=not args.no_usage,
        db_path=db_path,
    )

    print(f"\n=== research_agent: topic={args.topic!r} provider={provider.name()} ===\n")

    try:
        result = run_graph(rt, agents, graph,
                           initial_input=f"Topic: {args.topic}")
    except Exception as e:  # noqa: BLE001
        print(f"pipeline failed: {e}", file=sys.stderr)
        return 1

    print(f"\n=== final ({result.steps_taken} steps) ===\n{result.output}\n")

    if rt.usage is not None:
        totals = rt.usage.totals()
        print("== usage ==")
        print(f"prompt tokens     : {totals.prompt_tokens:>6}")
        print(f"completion tokens : {totals.completion_tokens:>6}")
        cost = rt.usage.estimated_cost()
        if cost > 0:
            print(f"estimated cost    : ${cost:.4f}")
        else:
            print("estimated cost    : (no pricing for this model)")

    if store is not None:
        for name, agent in agents.items():
            store.save(name, agent._state)
        print(f"\n[saved] snapshot to {db_path}", file=sys.stderr)

    rt.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
