import json
from datetime import datetime
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent.parent / "reminders.json"


def _load_reminders() -> list[dict]:
    if REMINDERS_FILE.exists():
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    return []


def _save_reminders(reminders: list[dict]):
    REMINDERS_FILE.write_text(
        json.dumps(reminders, indent=2, default=str), encoding="utf-8"
    )


def add_reminder(message: str, remind_at: str | None = None, priority: str = "normal") -> dict:
    reminders = _load_reminders()
    reminder = {
        "id": len(reminders) + 1,
        "message": message,
        "remind_at": remind_at,
        "priority": priority,
        "created": str(datetime.now()),
        "acknowledged": False,
    }
    reminders.append(reminder)
    _save_reminders(reminders)
    return reminder


def get_pending_reminders() -> list[dict]:
    return [r for r in _load_reminders() if not r["acknowledged"]]


def get_due_reminders() -> list[dict]:
    now = datetime.now()
    pending = get_pending_reminders()
    due = []
    for r in pending:
        if r["remind_at"]:
            try:
                remind_time = datetime.fromisoformat(r["remind_at"])
                if remind_time <= now:
                    due.append(r)
            except ValueError:
                due.append(r)
        else:
            due.append(r)
    return due


def acknowledge_reminder(reminder_id: int):
    reminders = _load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["acknowledged"] = True
            r["acknowledged_at"] = str(datetime.now())
    _save_reminders(reminders)


def format_reminders_for_prompt() -> str:
    due = get_due_reminders()
    if not due:
        return ""
    parts = ["ACTIVE REMINDERS FOR MADHAN:"]
    for r in due:
        flag = " [HIGH]" if r["priority"] == "high" else ""
        parts.append(f"  - #{r['id']}: {r['message']}{flag}")
    return "\n".join(parts)
