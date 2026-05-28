"""Graph builder — fluent multi-agent workflow, no YAML in sight."""
from marrow import Agent, Graph, MockProvider, Runtime, run_graph


def main() -> None:
    rt = Runtime()
    provider = MockProvider()

    agents = {
        "researcher": rt.add(Agent("researcher", provider,
                                   system_prompt="Research.")),
        "writer":     rt.add(Agent("writer", provider,
                                   system_prompt="Write a draft.")),
        "editor":     rt.add(Agent("editor", provider,
                                   system_prompt="Polish the draft.")),
    }

    g = (Graph()
         .start("researcher")
         .then("researcher", "writer")
         .then("writer", "editor")
         .finish("editor"))

    result = run_graph(rt, agents, g, initial_input="Topic: graph databases.")
    print(f"FINAL    : {result.output}")
    print("path     : researcher -> writer -> editor")
    print(f"steps    : {result.steps_taken}")
    print(f"reached  : {result.reached_end}")
    print(f"active   : {rt.router.active()}")


if __name__ == "__main__":
    main()
