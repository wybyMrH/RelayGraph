from __future__ import annotations

import json
import threading
from collections import deque
from http import HTTPStatus
from typing import Any

from .utils import now_iso, safe_int


class EventBroker:
    """In-process event broker for workspace Server-Sent Events."""

    def __init__(self, *, maxlen: int = 500) -> None:
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._events: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._next_id = 1

    def publish(
        self,
        event_type: str,
        *,
        workspace_id: str = "",
        payload: dict[str, Any] | None = None,
        run_id: str = "",
        job_id: str = "",
        agent_execution_id: str = "",
    ) -> dict[str, Any]:
        event = {
            "id": self._next_id,
            "type": str(event_type or "message").strip() or "message",
            "workspace_id": str(workspace_id or "").strip(),
            "run_id": str(run_id or "").strip(),
            "job_id": str(job_id or "").strip(),
            "agent_execution_id": str(agent_execution_id or "").strip(),
            "created_at": now_iso(),
            "payload": payload if isinstance(payload, dict) else {},
        }
        with self._condition:
            event["id"] = self._next_id
            self._next_id += 1
            self._events.append(event)
            self._condition.notify_all()
        return event

    def events_after(self, last_id: int = 0, *, workspace_id: str = "") -> list[dict[str, Any]]:
        target = str(workspace_id or "").strip()
        marker = safe_int(last_id, 0)
        with self._lock:
            return [
                dict(event)
                for event in self._events
                if safe_int(event.get("id"), 0) > marker
                and (not target or str(event.get("workspace_id") or "").strip() in {"", target})
            ]

    def wait_for_events(
        self,
        last_id: int = 0,
        *,
        workspace_id: str = "",
        timeout: float = 15.0,
    ) -> list[dict[str, Any]]:
        with self._condition:
            self._condition.wait_for(
                lambda: bool(self.events_after(last_id, workspace_id=workspace_id)),
                timeout=timeout,
            )
        return self.events_after(last_id, workspace_id=workspace_id)


def sse_encode(event: dict[str, Any]) -> bytes:
    event_id = safe_int(event.get("id"), 0)
    event_type = str(event.get("type") or "message").strip() or "message"
    data = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    lines = [f"id: {event_id}", f"event: {event_type}"]
    lines.extend(f"data: {line}" for line in data.splitlines() or ["{}"])
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def sse_heartbeat() -> bytes:
    data = json.dumps(
        {
            "type": "heartbeat",
            "created_at": now_iso(),
            "payload": {},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: heartbeat\ndata: {data}\n\n".encode("utf-8")


def stream_workspace_events(handler: Any, broker: EventBroker, workspace_id: str, *, since_id: int = 0, stop_event: Any = None) -> None:
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()

    last_id = safe_int(since_id, 0)

    def write(chunk: bytes) -> bool:
        try:
            handler.wfile.write(chunk)
            handler.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            return False

    if not write(b"retry: 3000\n\n"):
        return

    while True:
        events = broker.events_after(last_id, workspace_id=workspace_id)
        if not events:
            if stop_event is not None and stop_event.is_set():
                return
            events = broker.wait_for_events(last_id, workspace_id=workspace_id, timeout=15.0)
        if not events:
            if not write(sse_heartbeat()):
                return
            continue
        for event in events:
            last_id = safe_int(event.get("id"), last_id)
            if not write(sse_encode(event)):
                return
