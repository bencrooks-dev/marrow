"""Fluent graph builder for multi-agent workflows.

Resolves the 'DSL' resistance. Instead of YAML/JSON config, you
compose a plan in Python and freeze it. The frozen plan is
introspectable, serialisable, and (later) compilable to a
C++ plan structure for high-throughput execution. The build
API stays in Python where iteration is cheap.

Example:

    g = (Graph()
         .start("researcher")
         .then("researcher", "writer")
         .then("writer", "editor", when=lambda s: "DRAFT" in s)
         .finish("editor"))
    final_text = run(runtime, agents_by_name, g, initial_input="...")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    # condition runs against the latest output text; None = unconditional.
    condition: Optional[Callable[[str], bool]] = None


@dataclass
class Graph:
    entry: Optional[str] = None
    nodes: List[str] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    end: set = field(default_factory=set)

    def add(self, name: str) -> "Graph":
        if name not in self.nodes:
            self.nodes.append(name)
        return self

    def start(self, name: str) -> "Graph":
        self.entry = name
        return self.add(name)

    def then(
        self,
        src: str,
        dst: str,
        when: Optional[Callable[[str], bool]] = None,
    ) -> "Graph":
        self.add(src)
        self.add(dst)
        self.edges.append(Edge(src, dst, when))
        return self

    def finish(self, name: str) -> "Graph":
        self.end.add(name)
        return self.add(name)

    def freeze(self) -> "FrozenGraph":
        if not self.entry:
            raise ValueError("graph has no entry node")
        return FrozenGraph(
            entry=self.entry,
            nodes=tuple(self.nodes),
            edges=tuple(self.edges),
            end=frozenset(self.end),
        )


@dataclass(frozen=True)
class FrozenGraph:
    entry: str
    nodes: Tuple[str, ...]
    edges: Tuple[Edge, ...]
    end: FrozenSet[str]


def run(
    runtime,
    agents_by_name: Dict[str, "Agent"],  # noqa: F821 — forward ref
    graph: Graph,
    initial_input: str,
    max_steps: int = 16,
) -> str:
    """Step through a graph, driving each agent via the SDK."""
    frozen = graph.freeze()
    current = frozen.entry
    runtime.router.set_active(current)
    runtime.send(frm="<user>", to=current, text=initial_input)

    payload = initial_input
    for _ in range(max_steps):
        agent = agents_by_name.get(current)
        if agent is None:
            raise RuntimeError(f"no SDK agent registered for node: {current}")
        runtime.deliver(agent)
        payload = agent.step()
        if current in frozen.end:
            return payload
        next_edge = next(
            (
                e for e in frozen.edges
                if e.src == current and (e.condition is None or e.condition(payload))
            ),
            None,
        )
        if next_edge is None:
            return payload
        runtime.handoff(frm=current, to=next_edge.dst, text=payload)
        current = next_edge.dst
        runtime.router.set_active(current)
    return payload
