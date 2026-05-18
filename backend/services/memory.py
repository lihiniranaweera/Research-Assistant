"""In-memory per-session chat history store."""
from __future__ import annotations

from collections import defaultdict
from threading import Lock

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

_store: dict[str, list[BaseMessage]] = defaultdict(list)
_lock = Lock()

MAX_HISTORY = 20  # keep last N message pairs


def get_history(session_id: str) -> list[BaseMessage]:
    with _lock:
        return list(_store[session_id])


def append_exchange(session_id: str, human: str, ai: str) -> None:
    with _lock:
        _store[session_id].append(HumanMessage(content=human))
        _store[session_id].append(AIMessage(content=ai))
        if len(_store[session_id]) > MAX_HISTORY * 2:
            _store[session_id] = _store[session_id][-(MAX_HISTORY * 2):]


def clear_history(session_id: str) -> None:
    with _lock:
        _store.pop(session_id, None)


def list_sessions() -> list[str]:
    with _lock:
        return list(_store.keys())
