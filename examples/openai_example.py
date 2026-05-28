"""Real provider — OpenAI. Requires OPENAI_API_KEY.

    pip install 'marrow-rt[openai]'
    OPENAI_API_KEY=sk-... python examples/openai_example.py
"""
import os
import sys

from marrow import Agent, Runtime
from marrow.providers import OpenAIProvider


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set; skipping.")
        return

    rt = Runtime()
    provider = OpenAIProvider(model="gpt-4o-mini")
    agent = rt.add(Agent("assistant", provider,
                         system_prompt="You are a concise assistant."))

    agent.append_user("In one sentence, what is a graph database?")
    print("non-streaming:", agent.step(model="gpt-4o-mini"))

    agent.append_user("Now give me a streamed haiku about graph databases.")
    print("streaming   : ", end="", flush=True)
    agent.stream(model="gpt-4o-mini",
                 on_chunk=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
    print()


if __name__ == "__main__":
    main()
