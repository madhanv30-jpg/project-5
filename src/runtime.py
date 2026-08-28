import contextvars

_session_id = contextvars.ContextVar("madhan_session", default=None)
_escalated = contextvars.ContextVar("madhan_escalated", default=(False, None))


def set_session(session_id: str | None):
    _session_id.set(session_id)


def get_session() -> str | None:
    return _session_id.get()


def mark_escalated(reason: str | None = None):
    _escalated.set((True, reason))


def get_escalation() -> tuple[bool, str | None]:
    return _escalated.get()


def reset_escalation():
    _escalated.set((False, None))
