"""Execution — jobs helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

def workspace_job_binding(job: dict[str, Any]) -> tuple[str, str]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    return (
        str(metadata.get("workspace_id") or "").strip(),
        str(metadata.get("node_id") or "").strip(),
    )

def workspace_job_sort_key(job: dict[str, Any]) -> tuple[int, str, str]:
    status = str(job.get("status") or "")
    active = 1 if status in {"running", "starting", "queued", "blocked"} else 0
    return (
        active,
        str(job.get("started_at") or job.get("created_at") or ""),
        str(job.get("id") or ""),
    )
