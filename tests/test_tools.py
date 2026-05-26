"""Tool registry tests — Python tools through C++ dispatch."""
import json

from agentcore import Runtime, ToolBox, tool


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
    try:
        rt.tools.invoke("nope", "{}")
    except RuntimeError as e:
        assert "unknown tool" in str(e)
    else:
        assert False, "expected RuntimeError"
