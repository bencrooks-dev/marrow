# Persistence

`StateStore` is the interface for snapshotting and restoring agent state. Two implementations ship:

| Class | Backing | Use for |
|---|---|---|
| `InMemoryStateStore` | Python dict | Tests, short-lived sessions |
| `SQLiteStateStore` | SQLite file (WAL mode) | Single-host durability, demos, low-volume production |

## Save / load

```python
from agentcore import Agent, MockProvider, Runtime, SQLiteStateStore

store = SQLiteStateStore("./agents.db")

rt = Runtime()
agent = rt.add(Agent("alice", MockProvider(), system_prompt="Be helpful."))
agent.append_user("hello")
agent.step()

store.save("alice", agent._state)   # snapshot
```

After a restart:

```python
from agentcore import restore_into

rt = Runtime()
rt.add(Agent("alice", MockProvider()))    # re-register agent
restore_into(rt, "alice", store)           # rehydrate history + system prompt
```

## Designing a backend

A custom `StateStore` implements four methods:

```python
class MyStore:
    def save(self, agent_id: str, state) -> None: ...
    def load(self, agent_id: str) -> list[Message] | None: ...
    def delete(self, agent_id: str) -> None: ...
    def keys(self) -> Iterable[str]: ...
```

Optionally `load_system_prompt(agent_id) -> str | None` so `restore_into` can replay the system prompt.

Backends that may be useful later: Redis, Postgres, S3 + JSON, anything with a key/value interface.

## When to snapshot

`agentcore` does not auto-snapshot. Decide based on your durability requirement:

- After every `step()` — strictest durability, highest write rate
- Every N steps — cheaper, bounded loss window
- At conversation boundaries — natural cutpoint
- On graceful shutdown — minimum viable
