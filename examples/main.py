"""Two-agent pipeline: Researcher hands findings to Writer."""
from marrow import Agent, MockProvider, Runtime


def main() -> None:
    rt = Runtime()
    provider = MockProvider("local")

    researcher = rt.add(Agent(
        name="researcher",
        provider=provider,
        system_prompt="You research a topic and return concise bullet points.",
    ))
    writer = rt.add(Agent(
        name="writer",
        provider=provider,
        system_prompt="You write a short essay from research bullets.",
    ))

    researcher.append_user("Find three facts about graph databases.")
    findings = researcher.step()
    print(f"[researcher] {findings}")

    rt.handoff(frm="researcher", to="writer", text=findings)
    rt.deliver(writer)
    essay = writer.step()
    print(f"[writer]     {essay}")

    print(f"active agent     = {rt.router.active()}")
    print(f"writer history   = {writer._state.size()} messages")
    print(f"cache size       = {rt.cache.size()}")


if __name__ == "__main__":
    main()
