"""Tool registration helpers.

Resolves the 'tools in C++' resistance: the *registry* and *dispatch*
live in C++ (fast, thread-safe), while tool *bodies* stay in Python so
the contract can evolve without rebuilding the extension.

Usage:

    @tool(name="search", description="Search the web")
    def search(query: str) -> str: ...

    ToolBox().add(search).bind(runtime)
"""
from __future__ import annotations

import inspect
import json
import sys
import typing
from dataclasses import dataclass
from typing import Any, Callable, Union, get_args, get_origin

# --- size caps -----------------------------------------------------------

# Reject tool calls whose JSON args exceed this size. A malicious or buggy
# upstream model can otherwise OOM the host by streaming a multi-GB payload
# into a single tool call.
MAX_TOOL_ARGS_BYTES = 1 << 20  # 1 MiB

# Cap the size of stringified results too — same OOM reasoning, from the
# other direction (a runaway tool body returning huge text).
MAX_TOOL_RESULT_BYTES = 4 << 20  # 4 MiB

# --- schema generation ---------------------------------------------------

_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    type(None): "null",
}

_NoneType = type(None)


def _annotation_to_schema(ann: Any) -> dict[str, Any]:
    """Best-effort JSON-schema for a Python type annotation.

    Handles primitives, ``Optional[X]``, ``Union[A, B]``, ``list[X]``,
    ``dict``, ``Literal[...]``. Falls through to ``"string"`` for anything
    unrecognised — callers needing precise schemas for complex models
    (Pydantic, dataclasses) should supply ``schema=`` explicitly on the
    ``@tool`` decorator.
    """
    if ann is None or ann is _NoneType:
        return {"type": "null"}
    if ann in _PY_TO_JSON:
        return {"type": _PY_TO_JSON[ann]}

    origin = get_origin(ann)
    args = get_args(ann)

    # Optional[X] / Union[A, B, ...]
    if origin is Union or (sys.version_info >= (3, 10)
                           and isinstance(ann, type(int | str))):
        non_null = [a for a in args if a is not _NoneType]
        nullable = len(non_null) < len(args)
        if len(non_null) == 1:
            schema = _annotation_to_schema(non_null[0])
            if nullable:
                # JSON Schema permits ["X", "null"] for nullable types.
                t = schema.get("type")
                if isinstance(t, str):
                    schema = {**schema, "type": [t, "null"]}
            return schema
        return {"anyOf": [_annotation_to_schema(a) for a in non_null]}

    if origin is list or ann is list:
        item_ann = args[0] if args else str
        return {"type": "array", "items": _annotation_to_schema(item_ann)}

    if origin is dict or ann is dict:
        return {"type": "object"}

    if origin is typing.Literal:
        return {"enum": list(args)}

    # Best-effort fallback.
    return {"type": "string"}


@dataclass
class ToolDef:
    name: str
    description: str
    schema: dict[str, Any]
    fn: Callable[..., Any]

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


def _schema_for(fn: Callable[..., Any]) -> dict[str, Any]:
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
        properties[pname] = _annotation_to_schema(ann)
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {"type": "object", "properties": properties, "required": required}


def tool(
    name: str | None = None,
    description: str = "",
    schema: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], ToolDef]:
    """Wrap a function into a ToolDef.

    Auto-generates a JSON schema from annotations. Pass ``schema=`` to
    supply your own (Pydantic / dataclass / hand-written) — useful when
    the auto-generator can't represent the real type.
    """

    def wrap(fn: Callable[..., Any]) -> ToolDef:
        return ToolDef(
            name=name or fn.__name__,
            description=description or (fn.__doc__ or "").strip(),
            schema=schema if schema is not None else _schema_for(fn),
            fn=fn,
        )

    return wrap


# --- error redaction -----------------------------------------------------

def _default_error_redactor(exc: BaseException) -> str:
    """Return a short, structured error string with no traceback and
    no secret-looking content. Callers can override this on ToolBox()
    if they need different behavior."""
    msg = (str(exc).splitlines() or [""])[0]
    # Drop anything that looks like an absolute path or an api key.
    msg = " ".join(
        seg for seg in msg.split(" ")
        if not seg.startswith(("/", "sk-", "Bearer "))
        and "/Users/" not in seg
        and "C:\\" not in seg
    )
    return f"{type(exc).__name__}: {msg[:200]}"


class ToolBox:
    """A collection of tools that can be bound to a Runtime in one call.

    ``error_redactor`` is called whenever a tool body raises; it must
    return a string safe to forward to the LLM. The default redactor
    strips paths and obvious API-key fragments and caps length at 200
    chars. Pass your own for stricter sanitization (e.g. drop all
    error text and return only the exception type)."""

    def __init__(
        self,
        error_redactor: Callable[[BaseException], str] | None = None,
    ) -> None:
        self._defs: list[ToolDef] = []
        self._redactor = error_redactor or _default_error_redactor

    def add(self, t: ToolDef) -> ToolBox:
        self._defs.append(t)
        return self

    def bind(self, runtime) -> ToolBox:
        """Register every tool with the runtime's C++ ToolRegistry."""
        for t in self._defs:
            self._register_one(runtime.tools, t)
        return self

    def _register_one(self, registry, t: ToolDef) -> None:
        redactor = self._redactor

        def adapter(args_json: str) -> str:
            try:
                # Size cap before parsing, in bytes (utf-8). Rejects the
                # pathological case where a model returns megabytes of
                # tool args in a single call.
                if len(args_json.encode("utf-8")) > MAX_TOOL_ARGS_BYTES:
                    return json.dumps({
                        "ok": False,
                        "error": f"args_json exceeds {MAX_TOOL_ARGS_BYTES} bytes",
                    })

                args = json.loads(args_json) if args_json else {}
                if not isinstance(args, dict):
                    raise TypeError("tool args must be a JSON object")
                result = t.fn(**args)
                payload = json.dumps({"ok": True, "result": result})
                if len(payload.encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
                    return json.dumps({
                        "ok": False,
                        "error": f"tool result exceeds {MAX_TOOL_RESULT_BYTES} bytes",
                    })
                return payload
            except Exception as e:  # noqa: BLE001
                return json.dumps({"ok": False, "error": redactor(e)})

        registry.register(
            name=t.name,
            description=t.description,
            schema=json.dumps(t.schema),
            fn=adapter,
        )
