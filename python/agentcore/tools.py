"""Tool registration helpers.

Resolves the 'tools in C++' resistance: the *registry* and *dispatch*
live in C++ (fast, thread-safe), while tool *bodies* stay in Python so
the contract can evolve without rebuilding the extension.

Usage:

    @tool(name="search", description="Search the web")
    def search(query: str) -> str: ...

    runtime.tools.register(...)  # done automatically by ToolBox.bind
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# Map Python annotations to a minimal JSON-schema type string.
_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class ToolDef:
    name: str
    description: str
    schema: Dict[str, Any]
    fn: Callable[..., Any]

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


def _schema_for(fn: Callable[..., Any]) -> Dict[str, Any]:
    sig = inspect.signature(fn)
    properties: Dict[str, Any] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
        properties[pname] = {"type": _PY_TO_JSON.get(ann, "string")}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {"type": "object", "properties": properties, "required": required}


def tool(
    name: Optional[str] = None,
    description: str = "",
) -> Callable[[Callable[..., Any]], ToolDef]:
    """Decorator that wraps a function into a ToolDef with auto-schema."""

    def wrap(fn: Callable[..., Any]) -> ToolDef:
        return ToolDef(
            name=name or fn.__name__,
            description=description or (fn.__doc__ or "").strip(),
            schema=_schema_for(fn),
            fn=fn,
        )

    return wrap


class ToolBox:
    """A collection of tools that can be bound to a Runtime in one call."""

    def __init__(self) -> None:
        self._defs: list[ToolDef] = []

    def add(self, t: ToolDef) -> "ToolBox":
        self._defs.append(t)
        return self

    def bind(self, runtime) -> "ToolBox":
        """Register every tool with the runtime's C++ ToolRegistry."""
        for t in self._defs:
            self._register_one(runtime.tools, t)
        return self

    @staticmethod
    def _register_one(registry, t: ToolDef) -> None:
        # The C++ side hands us a JSON string; we parse, dispatch, and
        # return a JSON string. Errors become {"error": "..."} so the
        # C++ caller never has to translate Python exceptions.
        def adapter(args_json: str) -> str:
            try:
                args = json.loads(args_json) if args_json else {}
                if not isinstance(args, dict):
                    raise TypeError("tool args must be a JSON object")
                result = t.fn(**args)
                return json.dumps({"ok": True, "result": result})
            except Exception as e:  # noqa: BLE001
                return json.dumps({"ok": False, "error": str(e)})

        registry.register(
            name=t.name,
            description=t.description,
            schema=json.dumps(t.schema),
            fn=adapter,
        )
