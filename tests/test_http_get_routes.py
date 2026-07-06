from __future__ import annotations

from types import SimpleNamespace

from total_control.http_api.get_routes import handle_get


class _SpyState:
    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None

    def execution_overview(self, payload: dict[str, object]) -> dict[str, object]:
        self.payload = payload
        return {"ok": True, "filters": payload}


class _JsonHandler:
    headers: dict[str, str] = {}

    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None
        self.status: object = None

    def send_json(self, payload: dict[str, object], status: object = None) -> None:
        self.payload = payload
        self.status = status


def test_execution_overview_get_route_passes_explicit_filters():
    state = _SpyState()
    handler = _JsonHandler()
    parsed = SimpleNamespace(
        path="/api/execution-overview",
        query=(
            "limit=7&q=needle&status=done&kind=runs"
            "&node_kind=eval.report&job_id=job-123&agent_execution_id=aex-456"
            "&created_after=2026-06-20T10%3A00%3A00&created_before_iso=2026-06-21T10%3A00%3A00"
        ),
    )

    handled = handle_get(handler, state, parsed)

    assert handled is True
    assert state.payload == {
        "limit": "7",
        "query": "needle",
        "status": "done",
        "kind": "runs",
        "node_kind": "eval.report",
        "job_id": "job-123",
        "agent_execution_id": "aex-456",
        "created_after": "2026-06-20T10:00:00",
        "created_before": "2026-06-21T10:00:00",
    }
    assert handler.payload == {"ok": True, "filters": state.payload}
