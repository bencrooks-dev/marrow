"""Tool registry — Python tools dispatched through the C++ registry."""
import json

from marrow import Runtime, ToolBox, tool


@tool(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b


@tool(description="Echo a string")
def echo(text: str) -> str:
    return text


def main() -> None:
    rt = Runtime()
    ToolBox().add(add).add(echo).bind(rt)

    print("registered tools:", rt.tools.names())
    print("add schema      :", rt.tools.schema("add"))

    print("invoke add      :", rt.tools.invoke("add", json.dumps({"a": 2, "b": 5})))
    print("invoke echo     :", rt.tools.invoke("echo", json.dumps({"text": "hi"})))
    print("invoke missing  :", end=" ")
    try:
        rt.tools.invoke("nope", "{}")
    except RuntimeError as e:
        print(f"raised RuntimeError: {e}")


if __name__ == "__main__":
    main()
