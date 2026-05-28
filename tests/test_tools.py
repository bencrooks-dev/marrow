"""Tool registry tests — Python tools through C++ dispatch."""
import json
from typing import Optional

import pytest

from marrow import Runtime, ToolBox, tool
from marrow.tools import MAX_TOOL_ARGS_BYTES


@tool(name="multiply", description="multiply two integers")
def multiply(a: int, b: int) -> int:
    return a * b


def test_register_and_invoke():
    rt = Runtime()
    ToolBox().add(multiply).bind(rt)
    assert "multiply" in rt.tools.names()
    result = json.loads(rt.tools.invoke("multiply", json.dumps({"a": 3, "b": 4})))
    assert result == {"ok": True, "result": 12}


def test_bad_args_returns_error():
    rt = Runtime()
    ToolBox().add(multiply).bind(rt)
    result = json.loads(rt.tools.invoke("multiply", json.dumps({"a": 3})))
    assert result["ok"] is False
    assert "b" in result["error"] or "missing" in result["error"].lower()


def test_unknown_tool_raises():
    rt = Runtime()
    with pytest.raises(RuntimeError, match="unknown tool"):
        rt.tools.invoke("nope", "{}")


def test_args_size_cap():
    rt = Runtime()
    ToolBox().add(multiply).bind(rt)
    huge = json.dumps({"a": 1, "b": "x" * (MAX_TOOL_ARGS_BYTES + 100)})
    result = json.loads(rt.tools.invoke("multiply", huge))
    assert result["ok"] is False
    assert "exceeds" in result["error"]


def test_error_redactor_strips_paths():
    """The default redactor should drop absolute-path fragments so
    file paths don't leak into LLM context via tool errors."""
    rt = Runtime()

    @tool(name="boom")
    def boom() -> str:
        raise FileNotFoundError("/Users/secret/path/to/file.txt missing")

    ToolBox().add(boom).bind(rt)
    result = json.loads(rt.tools.invoke("boom", "{}"))
    assert result["ok"] is False
    assert "/Users/secret/path" not in result["error"]
    assert "FileNotFoundError" in result["error"]


def test_optional_schema_generation():
    """Optional[X] and list[X] should produce structured schemas, not
    fall through to plain "string"."""
    @tool(name="t")
    def t(name: str, count: Optional[int] = None, tags: list[str] = None):
        return name

    box = ToolBox().add(t)
    schema = box._defs[0].schema
    assert schema["properties"]["name"] == {"type": "string"}
    # Optional[int] → ["integer", "null"] or {"type": "integer"} variants
    count_schema = schema["properties"]["count"]
    assert "integer" in str(count_schema)
    # list[str] should produce an array schema
    assert schema["properties"]["tags"]["type"] == "array"
    assert schema["properties"]["tags"]["items"] == {"type": "string"}
