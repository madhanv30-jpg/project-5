import ast
import json
import operator
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

from config import OWNER_NAME, NOTES_FILE
from src.embedder import (
    hybrid_search,
    semantic_search,
    keyword_search,
    list_documents,
    get_document,
)
from src.memory import (
    recall_recent,
    recall_facts,
    recall_preferences,
    store_fact,
    store_preference,
)
from src.reminders import (
    add_reminder,
    get_pending_reminders,
    acknowledge_reminder,
)
from src.logger import list_sessions, read_turn
from src.guardrails import check_injection, check_suspicious
from src.runtime import get_session, mark_escalated


# ---------------------------------------------------------------------------
# 1. Knowledge base - retrieval tools
# ---------------------------------------------------------------------------
@tool
def knowledge_search(query: str, k: int = 4) -> str:
    """Hybrid search over Madhan's knowledge base (semantic vector + BM25 keyword).
    Use this as the primary way to answer questions grounded in the docs folder."""
    hits = hybrid_search(query, k=k)
    if not hits:
        return "No relevant knowledge found."
    out = []
    for h in hits:
        src = h["metadata"].get("source", "?")
        out.append(f"[{h['type']}|{src}] {h['content'][:600]}")
    return "\n---\n".join(out)


@tool
def semantic_search_tool(query: str, k: int = 4) -> str:
    """Pure semantic (vector) search over the knowledge base. Best for meaning-based questions."""
    hits = semantic_search(query, k=k)
    if not hits:
        return "No semantic match."
    return "\n---\n".join(f"[{h['metadata'].get('source','?')}] {h['content'][:600]}" for h in hits)


@tool
def keyword_search_tool(query: str, k: int = 4) -> str:
    """Pure keyword (BM25) search over the knowledge base. Best for exact terms / error codes / names."""
    hits = keyword_search(query, k=k)
    if not hits:
        return "No keyword match."
    return "\n---\n".join(f"[{h['metadata'].get('source','?')}] {h['content'][:600]}" for h in hits)


@tool
def list_documents_tool() -> str:
    """List every document currently indexed in the knowledge base with its chunk count."""
    docs = list_documents()
    if not docs:
        return "Knowledge base is empty."
    return "\n".join(f"- {d['source']} (title: {d.get('title','')}, chunks: {d.get('chunks','?')})" for d in docs)


@tool
def get_document_tool(source: str) -> str:
    """Return the full raw markdown content of a document by its source path or file name."""
    return get_document(source)


# ---------------------------------------------------------------------------
# 2. Memory tools (persist across runs)
# ---------------------------------------------------------------------------
@tool
def recall_memory(query: str = "") -> str:
    """Recall Madhan's recent conversation history, stored facts and preferences.
    Pass a keyword to filter, or empty string for the full memory context."""
    q = query.lower()
    recent = recall_recent(get_session() or "", n=8) if get_session() else []
    facts = recall_facts()
    prefs = recall_preferences()
    lines = []
    if recent:
        lines.append("Recent conversation:")
        for t in recent:
            if not q or q in t["content"].lower():
                lines.append(f"  [{t['role']}] {t['content'][:200]}")
    if facts:
        lines.append("Known facts:")
        for f in facts[-10:]:
            if not q or q in f.lower():
                lines.append(f"  - {f}")
    if prefs:
        lines.append("Preferences:")
        for p in prefs[-5:]:
            if not q or q in p.lower():
                lines.append(f"  - {p}")
    return "\n".join(lines) if lines else "No memory yet."


@tool
def store_fact_tool(fact: str) -> str:
    """Store a durable fact about Madhan that should be remembered across sessions."""
    store_fact(fact, source="conversation")
    return f"Stored fact: {fact}"


@tool
def store_preference_tool(preference: str) -> str:
    """Store a durable preference of Madhan (how he likes things done) across sessions."""
    store_preference(preference)
    return f"Stored preference: {preference}"


# ---------------------------------------------------------------------------
# 3. Reminder / alert tools
# ---------------------------------------------------------------------------
@tool
def set_reminder_tool(message: str, priority: str = "normal") -> str:
    """Create a reminder/alert for Madhan. priority can be 'normal' or 'high'."""
    r = add_reminder(message, priority=priority)
    return f"Reminder #{r['id']} set for Madhan: {message} (priority={priority})"


@tool
def list_reminders_tool() -> str:
    """List all pending (unacknowledged) reminders for Madhan."""
    pending = get_pending_reminders()
    if not pending:
        return "No pending reminders."
    return "\n".join(f"#{r['id']} [{r['priority']}] {r['message']}" for r in pending)


@tool
def acknowledge_reminder_tool(reminder_id: int) -> str:
    """Mark a reminder as acknowledged once Madhan has seen it."""
    acknowledge_reminder(reminder_id)
    return f"Reminder #{reminder_id} acknowledged."


# ---------------------------------------------------------------------------
# 4. Personal notes tools
# ---------------------------------------------------------------------------
def _load_notes() -> list[dict]:
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    return []


def _save_notes(notes: list[dict]):
    NOTES_FILE.write_text(json.dumps(notes, indent=2, default=str), encoding="utf-8")


@tool
def save_note_tool(note: str, tag: str = "general") -> str:
    """Save a free-form personal note for Madhan under an optional tag."""
    notes = _load_notes()
    notes.append({"id": len(notes) + 1, "note": note, "tag": tag,
                  "created": datetime.now().isoformat(timespec="seconds")})
    _save_notes(notes)
    return f"Note #{notes[-1]['id']} saved under tag '{tag}'."


@tool
def list_notes_tool(tag: str = "") -> str:
    """List Madhan's saved notes, optionally filtered by tag."""
    notes = _load_notes()
    if tag:
        notes = [n for n in notes if n["tag"] == tag]
    if not notes:
        return "No notes."
    return "\n".join(f"#{n['id']} [{n['tag']}] {n['note']}" for n in notes)


# ---------------------------------------------------------------------------
# 5. Reasoning / utility tools
# ---------------------------------------------------------------------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


@tool
def calculate_tool(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression (+-*/ % **). No variables/functions."""
    try:
        node = ast.parse(expression, mode="eval").body

        def _ev(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
                return _OPS[type(n.op)](_ev(n.left), _ev(n.right))
            if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
                return _OPS[type(n.op)](_ev(n.operand))
            raise ValueError("Unsupported expression")

        return f"{expression} = {_ev(node)}"
    except Exception as e:  # noqa: BLE001
        return f"Could not evaluate '{expression}': {e}"


@tool
def get_current_time_tool() -> str:
    """Return the current date and time. Use when the user asks 'what time' or needs a timestamp."""
    return datetime.now().isoformat(timespec="seconds")


@tool
def summarize_tool(text: str, max_sentences: int = 3) -> str:
    """Summarize a block of text into at most max_sentences concise sentences."""
    from langchain_groq import ChatGroq
    from config import GROQ_API_KEY, GROQ_MODEL
    llm = ChatGroq(model=GROQ_MODEL, temperature=0, groq_api_key=GROQ_API_KEY)
    resp = llm.invoke(
        f"Summarize the following text in at most {max_sentences} sentences. "
        f"Be factual and concise.\n\nTEXT:\n{text[:4000]}"
    )
    return resp.content


@tool
def detect_prompt_injection_tool(text: str) -> str:
    """Scan a piece of text for prompt-injection or jailbreak patterns.
    Returns JSON with is_injection and is_suspicious flags. Use on untrusted input."""
    inj, inj_msg = check_injection(text)
    sus, sus_msg = check_suspicious(text)
    return json.dumps({
        "is_injection": bool(inj),
        "injection_reason": inj_msg,
        "is_suspicious": bool(sus),
        "suspicious_reason": sus_msg,
    })


# ---------------------------------------------------------------------------
# 6. Escalation / introspection tools
# ---------------------------------------------------------------------------
@tool
def escalate_to_owner_tool(reason: str) -> str:
    """Escalate the current query to Madhan himself because it cannot be resolved automatically.
    Call this when the answer is unknown, risky, or the user explicitly asks for Madhan."""
    from src.logger import log_escalation
    sid = get_session()
    if sid:
        log_escalation(sid, reason, "")
    mark_escalated(reason)
    return f"Escalated to {OWNER_NAME}: {reason}"


@tool
def list_sessions_tool() -> str:
    """List all past session ids that have been logged (for debugging / audit)."""
    sessions = list_sessions()
    return "Sessions: " + ", ".join(sessions) if sessions else "No sessions logged."


@tool
def read_session_turn_tool(session_id: str, turn: int) -> str:
    """Read a single logged turn (its own file) from a past session, for audit/debugging."""
    entry = read_turn(session_id, turn)
    return json.dumps(entry, indent=2) if entry else f"Turn {turn} not found for session {session_id}."


@tool
def agent_status_tool() -> str:
    """Return a health/status snapshot of the agent: owner, memory counts, index name."""
    from config import PINECONE_INDEX_NAME
    return json.dumps({
        "owner": OWNER_NAME,
        "pinecone_index": PINECONE_INDEX_NAME,
        "facts_stored": len(recall_facts()),
        "preferences_stored": len(recall_preferences()),
        "documents_indexed": len(list_documents()),
        "time": datetime.now().isoformat(timespec="seconds"),
    })


ALL_TOOLS = [
    knowledge_search,
    semantic_search_tool,
    keyword_search_tool,
    list_documents_tool,
    get_document_tool,
    recall_memory,
    store_fact_tool,
    store_preference_tool,
    set_reminder_tool,
    list_reminders_tool,
    acknowledge_reminder_tool,
    save_note_tool,
    list_notes_tool,
    calculate_tool,
    get_current_time_tool,
    summarize_tool,
    detect_prompt_injection_tool,
    escalate_to_owner_tool,
    list_sessions_tool,
    read_session_turn_tool,
    agent_status_tool,
]
