import json
from datetime import datetime
from pathlib import Path
from config import MEMORY_DB


def _load_memory() -> dict:
    if MEMORY_DB.exists():
        return json.loads(MEMORY_DB.read_text(encoding="utf-8"))
    return {"sessions": {}, "facts": [], "preferences": [], "reminders": []}


def _save_memory(data: dict):
    MEMORY_DB.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def save_session_turn(session_id: str, turn: int, role: str, content: str):
    mem = _load_memory()
    if session_id not in mem["sessions"]:
        mem["sessions"][session_id] = {"turns": [], "started": str(datetime.now())}
    mem["sessions"][session_id]["turns"].append({
        "turn": turn,
        "role": role,
        "content": content,
        "timestamp": str(datetime.now()),
    })
    _save_memory(mem)


def recall_recent(session_id: str, n: int = 5) -> list[dict]:
    mem = _load_memory()
    if session_id not in mem["sessions"]:
        return []
    turns = mem["sessions"][session_id]["turns"]
    return turns[-n:]


def store_fact(fact: str, source: str = "user"):
    mem = _load_memory()
    mem["facts"].append({
        "fact": fact,
        "source": source,
        "timestamp": str(datetime.now()),
    })
    _save_memory(mem)


def recall_facts() -> list[str]:
    mem = _load_memory()
    return [f["fact"] for f in mem["facts"]]


def store_preference(pref: str):
    mem = _load_memory()
    mem["preferences"].append({
        "preference": pref,
        "timestamp": str(datetime.now()),
    })
    _save_memory(mem)


def recall_preferences() -> list[str]:
    mem = _load_memory()
    return [p["preference"] for p in mem["preferences"]]


def get_all_memory() -> dict:
    return _load_memory()


def format_memory_context(session_id: str) -> str:
    parts = []
    recent = recall_recent(session_id, n=5)
    if recent:
        parts.append("Recent conversation:")
        for t in recent:
            parts.append(f"  [{t['role']}] {t['content'][:200]}")
    facts = recall_facts()
    if facts:
        parts.append("Known facts:")
        for f in facts[-10:]:
            parts.append(f"  - {f}")
    prefs = recall_preferences()
    if prefs:
        parts.append("Preferences:")
        for p in prefs[-5:]:
            parts.append(f"  - {p}")
    return "\n".join(parts) if parts else "No prior memory."
