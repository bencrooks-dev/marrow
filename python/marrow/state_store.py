"""Persistence for agent state.

Provides a :class:`StateStore` Protocol with two concrete implementations:

- :class:`InMemoryStateStore` — what the engine already does, exposed
  behind the same interface so swapping is trivial.
- :class:`SQLiteStateStore` — durable; survives process restart.

A store snapshots an :class:`marrow.AgentState` to its backend and
loads it back later. Callers handle the lifecycle (when to snapshot,
when to load on startup, when to garbage-collect).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from . import _marrow as _c


def _msg_to_dict(m: _c.Message) -> dict:
    return {
        "role": int(m.role),
        "content": m.content,
        "name": m.name,
        "timestamp_ms": m.timestamp_ms,
        "metadata": dict(m.metadata) if m.metadata else {},
    }


def _dict_to_msg(d: dict) -> _c.Message:
    m = _c.Message.make(_c.Role(d["role"]), d["content"], d.get("name", ""))
    m.timestamp_ms = d.get("timestamp_ms", 0)
    # ARI §2.2/§8: metadata MUST survive a persistence round-trip. It was
    # serialized by _msg_to_dict; restore it here so load() is lossless.
    meta = d.get("metadata")
    if meta:
        m.metadata = meta
    return m


@runtime_checkable
class StateStore(Protocol):
    """Snapshot and restore agent state by id."""

    def save(self, agent_id: str, state: _c.AgentState) -> None: ...
    def load(self, agent_id: str) -> list[_c.Message] | None: ...
    def delete(self, agent_id: str) -> None: ...
    def keys(self) -> Iterable[str]: ...


class InMemoryStateStore:
    """Reference impl. Thread-safe."""

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def save(self, agent_id: str, state: _c.AgentState) -> None:
        history = [_msg_to_dict(m) for m in state.history()]
        sys_prompt = state.system_prompt()
        with self._lock:
            self._data[agent_id] = {
                "messages": history,
                "system_prompt": sys_prompt,
            }

    def load(self, agent_id: str) -> list[_c.Message] | None:
        with self._lock:
            entry = self._data.get(agent_id)
        if entry is None:
            return None
        return [_dict_to_msg(d) for d in entry["messages"]]

    def load_system_prompt(self, agent_id: str) -> str | None:
        with self._lock:
            entry = self._data.get(agent_id)
        return entry["system_prompt"] if entry else None

    def delete(self, agent_id: str) -> None:
        with self._lock:
            self._data.pop(agent_id, None)

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self._data.keys())


class SQLiteStateStore:
    """SQLite-backed durable store. Uses one file; safe to share between
    threads in the same process (separate connections per thread)."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS agent_state (
        agent_id      TEXT PRIMARY KEY,
        system_prompt TEXT,
        history_json  TEXT NOT NULL,
        updated_at    INTEGER NOT NULL
    );
    """

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        # check_same_thread=False is safe because every method opens its
        # own connection. We do NOT share connections across threads.
        with sqlite3.connect(self._path) as conn:
            conn.executescript(self._SCHEMA)
            conn.commit()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._path)
        c.execute("PRAGMA journal_mode=WAL")  # safer concurrent writes
        return c

    def save(self, agent_id: str, state: _c.AgentState) -> None:
        history_json = json.dumps([_msg_to_dict(m) for m in state.history()])
        sys_prompt = state.system_prompt() or None
        import time as _t
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO agent_state "
                "(agent_id, system_prompt, history_json, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (agent_id, sys_prompt, history_json, int(_t.time())),
            )
            conn.commit()

    def load(self, agent_id: str) -> list[_c.Message] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT history_json FROM agent_state WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return [_dict_to_msg(d) for d in json.loads(row[0])]

    def load_system_prompt(self, agent_id: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT system_prompt FROM agent_state WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return row[0] if row else None

    def delete(self, agent_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM agent_state WHERE agent_id = ?", (agent_id,))
            conn.commit()

    def keys(self) -> Iterable[str]:
        with self._conn() as conn:
            return [r[0] for r in conn.execute("SELECT agent_id FROM agent_state")]


def restore_into(runtime, agent_id: str, store: StateStore) -> bool:
    """Re-hydrate an agent's history from a store into a Runtime that
    already has the agent registered. Returns True if the store had a
    snapshot. Caller is responsible for re-attaching providers."""
    msgs = store.load(agent_id)
    if msgs is None:
        return False
    state = runtime.engine.agent(agent_id)
    if state is None:
        raise RuntimeError(f"agent {agent_id!r} is not registered")
    state.clear()
    sys = getattr(store, "load_system_prompt", lambda _: None)(agent_id)
    if sys:
        state.set_system_prompt(sys)
    for m in msgs:
        state.append(m)
    return True
