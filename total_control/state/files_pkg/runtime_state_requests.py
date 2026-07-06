from __future__ import annotations

from typing import Any

from ...utils import safe_int


def parse_runtime_state_cleanup_request(body: dict[str, Any] | None) -> dict[str, Any]:
    data = body if isinstance(body, dict) else {}
    clear_jobs = bool(data.get("clear_completed_jobs", True))
    prune_runs = bool(data.get("prune_workspace_runs", True))
    dry_run = bool(data.get("dry_run", False))
    max_runs = max(1, min(safe_int(data.get("max_runs_per_workspace"), 20), 200))
    requested_statuses = data.get("statuses")
    if isinstance(requested_statuses, list) and requested_statuses:
        deletable_statuses = {
            str(item or "").strip()
            for item in requested_statuses
            if str(item or "").strip() in {"done", "failed", "stopped"}
        }
    else:
        deletable_statuses = {"done", "failed", "stopped"}
    return {
        "data": data,
        "clear_jobs": clear_jobs,
        "prune_runs": prune_runs,
        "dry_run": dry_run,
        "max_runs": max_runs,
        "deletable_statuses": deletable_statuses,
        "active_statuses": {"queued", "starting", "running", "blocked"},
    }
