import json
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR


def _session_dir(session_id: str) -> Path:
    d = LOGS_DIR / f"session_{session_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _next_turn(session_id: str) -> int:
    d = _session_dir(session_id)
    existing = list(d.glob("turn_*.json"))
    return len(existing) + 1


def log_turn(session_id: str, role: str, content: str, *, step: int | None = None,
             kind: str = "message", metadata: dict | None = None) -> int:
    d = _session_dir(session_id)
    turn = _next_turn(session_id)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "turn": turn,
        "step": step,
        "kind": kind,
        "role": role,
        "content": content,
    }
    if metadata:
        entry["metadata"] = metadata
    # separate file for THIS turn
    (d / f"turn_{turn:03d}.json").write_text(
        json.dumps(entry, indent=2, default=str), encoding="utf-8"
    )
    # combined session stream (one JSONL line per event)
    with open(d / "session.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return turn


def log_guardrail(session_id: str, user_input: str, reason: str):
    return log_turn(
        session_id, "guardrail", f"BLOCKED: {reason}", kind="guardrail",
        metadata={"original_input": user_input, "reason": reason},
    )


def log_escalation(session_id: str, reason: str, query: str):
    return log_turn(
        session_id, "escalation", f"Escalated to madhan: {reason}", kind="escalation",
        metadata={"reason": reason, "original_query": query, "escalated_to": "madhan"},
    )


def log_search(session_id: str, step: int, query: str, results_count: int,
                sources: list[str] | None = None):
    return log_turn(
        session_id, "search", f"Hybrid search: {results_count} results", step=step,
        kind="search",
        metadata={"query": query, "results_count": results_count, "sources": sources or []},
    )


def log_tool_call(session_id: str, step: int, tool: str, args: dict, ok: bool,
                  error: str | None = None):
    return log_turn(
        session_id, "tool", f"tool={tool} ok={ok}", step=step, kind="tool",
        metadata={"tool": tool, "args": args, "ok": ok, "error": error},
    )


def read_session_log(session_id: str) -> list[dict]:
    path = _session_dir(session_id) / "session.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_turn(session_id: str, turn: int) -> dict | None:
    path = _session_dir(session_id) / f"turn_{turn:03d}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[str]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return [
        f.stem.replace("session_", "")
        for f in sorted(LOGS_DIR.glob("session_*"), reverse=True)
        if f.is_dir()
    ]
