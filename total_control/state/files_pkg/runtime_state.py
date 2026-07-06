from __future__ import annotations

from typing import Any


def build_runtime_state_status_payload(
    jobs: list[dict[str, Any]],
    workspaces: list[dict[str, Any]],
) -> dict[str, Any]:
    terminal_statuses = {"done", "failed", "stopped"}
    active_statuses = {"queued", "starting", "running", "blocked"}
    status_counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status") or "unknown").strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
    workspace_items: list[dict[str, Any]] = []
    total_runs = 0
    total_events = 0
    active_runs = 0
    for workspace in workspaces:
        runs = [run for run in workspace["runs"] if isinstance(run, dict)]
        run_events = sum(
            len(run.get("events")) for run in runs if isinstance(run.get("events"), list)
        )
        active_count = sum(1 for run in runs if str(run.get("status") or "") in active_statuses)
        total_runs += len(runs)
        total_events += run_events
        active_runs += active_count
        workspace_items.append(
            {
                "workspace_id": workspace["id"],
                "name": workspace["name"],
                "run_count": len(runs),
                "active_run_count": active_count,
                "event_count": run_events,
            }
        )
    workspace_items.sort(key=lambda item: (int(item.get("run_count") or 0), str(item.get("name") or "")), reverse=True)
    completed_jobs = sum(1 for job in jobs if str(job.get("status") or "") in terminal_statuses)
    return {
        "jobs": {
            "total": len(jobs),
            "active": sum(1 for job in jobs if str(job.get("status") or "") in active_statuses),
            "completed": completed_jobs,
            "status_counts": status_counts,
            "deletable_statuses": sorted(terminal_statuses),
        },
        "workspaces": {
            "total": len(workspaces),
            "total_runs": total_runs,
            "active_runs": active_runs,
            "total_events": total_events,
            "items": workspace_items[:20],
        },
        "cleanup_defaults": {
            "clear_completed_jobs": True,
            "prune_workspace_runs": True,
            "max_runs_per_workspace": 20,
        },
    }
