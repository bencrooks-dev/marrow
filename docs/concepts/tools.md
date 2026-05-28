# Tools

Tools are Python callables that an agent can invoke. The **registry and dispatch** are C++ (fast, thread-safe lookup, lock-friendly); **tool bodies** are Python so the contract can evolve without rebuilding the extension.

## Define a tool

```python
from marrow import tool, ToolBox

@tool(description="Multiply two integers.")
def multiply(a: int, b: int) -> int:
    return a * b
```

## Register and invoke

```python
from marrow import Runtime

rt = Runtime()
ToolBox().add(multiply).bind(rt)

result = rt.tools.invoke("multiply", '{"a": 6, "b": 7}')
# {"ok": true, "result": 42}
```

## Schemas

A best-effort JSON schema is generated from the function's type annotations:

```python
@tool
def search(query: str, max_results: int = 10) -> list[str]:
    ...
```

produces:

```json
{
  "type": "object",
  "properties": {
    "query":       {"type": "string"},
    "max_results": {"type": "integer"}
  },
  "required": ["query"]
}
```

For complex types (Pydantic models, dataclasses) pass `schema=` explicitly:

```python
@tool(schema=MyModel.model_json_schema())
def my_tool(payload: MyModel) -> str:
    ...
```

## Error redaction

Tool exceptions are caught and returned to the LLM as `{"ok": false, "error": "..."}`. The default redactor strips absolute paths and API-key prefixes so tracebacks don't leak secrets.

Customize the redactor:

```python
from marrow import ToolBox

def my_redactor(exc: BaseException) -> str:
    return type(exc).__name__       # drop everything but the exception type

ToolBox(error_redactor=my_redactor).add(multiply).bind(rt)
```

## Size caps

`marrow.tools.MAX_TOOL_ARGS_BYTES` (default 1 MiB) and `MAX_TOOL_RESULT_BYTES` (default 4 MiB) cap input and output. Override at the module level if your workload needs different limits — there is no per-tool cap yet.
