"""Process-wide registry of running agent executions for cancel signalling.

Agent executions are synchronous loops (LLM call → tool call → repeat). They
check ``cancel_check`` between iterations, so a separate request can ask a
running execution to abort by setting its flag here, keyed by execution id.

Keys are added when an execution starts and removed when it finishes, so the
registry only holds in-flight executions.
"""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_cancel_flags: dict[str, threading.Event] = {}


def register_agent_cancel(execution_id: str) -> Callable[[], bool]:
    """Register an in-flight execution and return its cancel-check callable."""
    normalized = str(execution_id or "").strip()
    event = threading.Event()
    with _lock:
        if normalized:
            _cancel_flags[normalized] = event
    return lambda: event.is_set()


def cancel_agent_run(execution_id: str) -> bool:
    """Signal cancellation for an execution. Returns True if it was running."""
    normalized = str(execution_id or "").strip()
    with _lock:
        event = _cancel_flags.get(normalized)
    if event is None:
        return False
    event.set()
    return True


def release_agent_cancel(execution_id: str) -> None:
    normalized = str(execution_id or "").strip()
    with _lock:
        _cancel_flags.pop(normalized, None)


def agent_run_is_active(execution_id: str) -> bool:
    with _lock:
        return str(execution_id or "").strip() in _cancel_flags
