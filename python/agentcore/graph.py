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
from typing import Callable


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    # condition runs against the latest output text; None = unconditional.
    condition: Callable[[str], bool] | None = None


@dataclass
class Graph:
    entry: str | None = None
    nodes: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    end: set = field(default_factory=set)

    def add(self, name: str) -> Graph:
        if name not in self.nodes:
            self.nodes.append(name)
        return self

    def start(self, name: str) -> Graph:
        self.entry = name
        return self.add(name)

    def then(
        self,
        src: str,
        dst: str,
        when: Callable[[str], bool] | None = None,
    ) -> Graph:
        self.add(src)
        self.add(dst)
        self.edges.append(Edge(src, dst, when))
        return self

    def finish(self, name: str) -> Graph:
        self.end.add(name)
        return self.add(name)

    def freeze(self) -> FrozenGraph:
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
    nodes: tuple[str, ...]
    edges: tuple[Edge, ...]
    end: frozenset[str]


@dataclass(frozen=True)
class GraphResult:
    """Structured result of a graph run so callers can distinguish
    "reached an end node" from "ran out of steps" or "no edge matched"."""
    output: str
    final_node: str
    steps_taken: int
    reached_end: bool
    exhausted: bool   # True if max_steps was hit without reaching `end`


class GraphExhausted(RuntimeError):
    """Raised when ``run(..., raise_on_exhaustion=True)`` hits
    ``max_steps`` without reaching an ``end`` node."""

    def __init__(self, result: GraphResult) -> None:
        super().__init__(
            f"graph did not reach an end node within {result.steps_taken} steps "
            f"(stopped at '{result.final_node}')"
        )
        self.result = result


def run(
    runtime,
    agents_by_name: dict[str, Agent],  # noqa: F821 — forward ref
    graph: Graph,
    initial_input: str,
    max_steps: int = 16,
    raise_on_exhaustion: bool = True,
) -> GraphResult:
    """Step through a graph, driving each agent via the SDK.

    Returns a :class:`GraphResult` describing what happened. If
    ``raise_on_exhaustion`` is True (the default), hitting ``max_steps``
    without reaching an ``end`` node raises :class:`GraphExhausted` so
    silent truncation can't masquerade as successful completion.
    """
    frozen = graph.freeze()
    current = frozen.entry
    runtime.router.set_active(current)
    runtime.send(frm="<user>", to=current, text=initial_input)

    payload = initial_input
    for step_idx in range(max_steps):
        agent = agents_by_name.get(current)
        if agent is None:
            raise RuntimeError(f"no SDK agent registered for node: {current}")
        runtime.deliver(agent)
        payload = agent.step()
        if current in frozen.end:
            return GraphResult(
                output=payload, final_node=current,
                steps_taken=step_idx + 1, reached_end=True, exhausted=False,
            )
        next_edge = next(
            (
                e for e in frozen.edges
                if e.src == current and (e.condition is None or e.condition(payload))
            ),
            None,
        )
        if next_edge is None:
            return GraphResult(
                output=payload, final_node=current,
                steps_taken=step_idx + 1, reached_end=False, exhausted=False,
            )
        runtime.handoff(frm=current, to=next_edge.dst, text=payload)
        current = next_edge.dst
        runtime.router.set_active(current)

    result = GraphResult(
        output=payload, final_node=current,
        steps_taken=max_steps, reached_end=False, exhausted=True,
    )
    if raise_on_exhaustion:
        raise GraphExhausted(result)
    return result
