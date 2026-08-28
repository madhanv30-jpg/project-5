import json
from datetime import datetime
from pathlib import Path

from config import OWNER_NAME, ESCALATION_CONTACT, PROJECT_ROOT
from src.logger import log_escalation

ESCALATION_THRESHOLD = 3
LOOP_LIMIT = 5

ESCALATIONS_FILE = PROJECT_ROOT / "escalations.jsonl"


def should_escalate(loop_count: int, no_answer_count: int) -> tuple[bool, str]:
    if loop_count >= LOOP_LIMIT:
        return True, "Maximum loop limit reached without resolution."
    if no_answer_count >= ESCALATION_THRESHOLD:
        return True, "Knowledge base could not answer after multiple attempts."
    return False, ""


def format_escalation_message(query: str, conversation_history: list[dict]) -> str:
    history_text = "\n".join(
        f"  [{h['role']}] {h['content'][:300]}" for h in conversation_history[-6:]
    )
    return (
        f"ESCALATION TO {OWNER_NAME.upper()}\n"
        f"Query: {query}\n"
        f"Reason: Support agent could not resolve within {LOOP_LIMIT} steps.\n"
        f"Conversation context:\n{history_text}\n"
        f"Action required: Please review and assist."
    )


def handle_escalation(session_id: str, query: str, conversation_history: list[dict]) -> str:
    msg = format_escalation_message(query, conversation_history)
    log_escalation(session_id, "Agent escalation", query)
    ESCALATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ESCALATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": session_id,
            "escalated_to": ESCALATION_CONTACT,
            "query": query,
            "summary": msg,
        }, default=str) + "\n")
    return (
        f"I've been unable to resolve your query after multiple attempts. "
        f"I'm escalating this to {OWNER_NAME} for review. "
        f"He will be notified and will follow up with you.\n\nEscalation summary:\n{msg}"
    )
