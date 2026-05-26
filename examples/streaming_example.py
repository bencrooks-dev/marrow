"""Streaming — MockProvider emits word-sized chunks."""
import sys

from agentcore import Agent, MockProvider, Runtime


def main() -> None:
    rt = Runtime()
    agent = rt.add(Agent("streamer", MockProvider("local"),
                         system_prompt="You stream a response."))
    agent.append_user("Generate a sentence about graph databases.")

    print("streaming: ", end="", flush=True)
    final = agent.stream(on_chunk=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
    print("\n---")
    print(f"final length    = {len(final)} chars")
    print(f"history size    = {agent._state.size()} messages")


if __name__ == "__main__":
    main()
