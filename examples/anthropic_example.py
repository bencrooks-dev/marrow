"""Real provider — Anthropic. Requires ANTHROPIC_API_KEY.

    pip install 'marrow-rt[anthropic]'
    ANTHROPIC_API_KEY=sk-ant-... python examples/anthropic_example.py
"""
import os
import sys

from marrow import Agent, Runtime
from marrow.providers import AnthropicProvider


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set; skipping.")
        return

    rt = Runtime()
    provider = AnthropicProvider(model="claude-sonnet-4-6")
    agent = rt.add(Agent("assistant", provider,
                         system_prompt="You are a concise assistant."))

    agent.append_user("In one sentence, what is a graph database?")
    print("non-streaming:", agent.step(model="claude-sonnet-4-6"))

    agent.append_user("Now give me a streamed haiku about graph databases.")
    print("streaming   : ", end="", flush=True)
    agent.stream(model="claude-sonnet-4-6",
                 on_chunk=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
    print()


if __name__ == "__main__":
    main()
