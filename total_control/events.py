from __future__ import annotations

import json
import threading
from collections import deque
from http import HTTPStatus
from typing import Any

from .utils import now_iso, public_job_payload, safe_int


class EventBroker:
    """In-process event broker for workspace Server-Sent Events."""

    def __init__(self, *, maxlen: int = 500) -> None:
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._maxlen = max(safe_int(maxlen, 500), 1)
        self._events: deque[dict[str, Any]] = deque()
        self._dropped_broadcast_until = 0
        self._dropped_workspace_until: dict[str, int] = {}
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
            if len(self._events) >= self._maxlen:
                self._record_dropped_event_locked(self._events.popleft())
            self._events.append(event)
            self._condition.notify_all()
        return event

    def _record_dropped_event_locked(self, event: dict[str, Any]) -> None:
        event_id = safe_int(event.get("id"), 0)
        if event_id <= 0:
            return
        workspace_id = str(event.get("workspace_id") or "").strip()
        if not workspace_id:
            self._dropped_broadcast_until = max(self._dropped_broadcast_until, event_id)
            return
        previous = self._dropped_workspace_until.get(workspace_id, 0)
        self._dropped_workspace_until[workspace_id] = max(previous, event_id)

    def latest_event_id(self) -> int:
        with self._lock:
            return max(safe_int(self._next_id, 1) - 1, 0)

    def first_retained_event_id(self, *, workspace_id: str = "") -> int:
        target = str(workspace_id or "").strip()
        with self._lock:
            for event in self._events:
                if target and str(event.get("workspace_id") or "").strip() not in {"", target}:
                    continue
                event_id = safe_int(event.get("id"), 0)
                if event_id > 0:
                    return event_id
        return 0

    def replay_gap(self, last_id: int = 0, *, workspace_id: str = "") -> dict[str, Any] | None:
        marker = safe_int(last_id, 0)
        if marker <= 0:
            return None
        target = str(workspace_id or "").strip()
        with self._lock:
            latest_id = max(safe_int(self._next_id, 1) - 1, 0)
            if marker > latest_id:
                return {
                    "reason": "event_id_reset_or_server_restart",
                    "requested_since_id": marker,
                    "dropped_until_id": 0,
                    "first_retained_id": self.first_retained_event_id(workspace_id=target),
                    "latest_id": latest_id,
                }
            dropped_until_id = self._dropped_broadcast_until
            if target:
                dropped_until_id = max(dropped_until_id, self._dropped_workspace_until.get(target, 0))
            elif self._dropped_workspace_until:
                dropped_until_id = max(dropped_until_id, max(self._dropped_workspace_until.values()))
            if dropped_until_id > marker:
                return {
                    "reason": "buffer_overflow",
                    "requested_since_id": marker,
                    "dropped_until_id": dropped_until_id,
                    "first_retained_id": self.first_retained_event_id(workspace_id=target),
                    "latest_id": latest_id,
                }
        return None

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


def public_job_event_payload(job: dict[str, Any]) -> dict[str, Any]:
    return public_job_payload(job)


def stream_workspace_events(
    handler: Any,
    broker: EventBroker,
    workspace_id: str,
    *,
    since_id: int = 0,
    stop_event: Any = None,
    prelude_events: list[dict[str, Any]] | None = None,
) -> None:
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
    for event in prelude_events or []:
        last_id = safe_int(event.get("id"), last_id)
        if not write(sse_encode(event)):
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
