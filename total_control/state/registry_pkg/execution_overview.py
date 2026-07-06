from __future__ import annotations

import copy
from typing import Any

from ...utils import parse_iso_timestamp, safe_int
from ...workspace.execution import workspace_execution_runs_public


def execution_overview_status_group(status: Any) -> str:
    value = str(status or "pending").strip().lower()
    if value in {"done", "ready", "completed", "success", "succeeded"}:
        return "done"
    if value in {"failed", "blocked", "stopped", "cancelled", "canceled"}:
        return "failed"
    return "active"


def execution_overview_search_text(record: dict[str, Any], record_type: str) -> str:
    progress = record.get("progress") if isinstance(record.get("progress"), dict) else {}
    fields: list[Any] = [
        record_type,
        record.get("id"),
        record.get("run_id"),
        record.get("execution_run_id"),
        record.get("job_id"),
        record.get("workspace_id"),
        record.get("workspace_name"),
        record.get("summary"),
        record.get("kind"),
        record.get("status"),
        record.get("server_id"),
        record.get("node_id"),
        record.get("agent_id"),
        record.get("agent_execution_id"),
        progress.get("done"),
        progress.get("total"),
        progress.get("percent"),
    ]
    for key in (
        "job_ids",
        "agent_execution_ids",
        "node_ids",
        "node_kinds",
        "server_ids",
        "_filter_job_ids",
        "_filter_agent_execution_ids",
        "_filter_node_ids",
        "_filter_node_kinds",
    ):
        value = record.get(key)
        if isinstance(value, list):
            fields.append(" ".join(str(item or "") for item in value))
    return " ".join(str(item or "").strip().lower() for item in fields if str(item or "").strip())


def execution_overview_text_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    text = str(value or "").strip()
    return [text] if text else []


def execution_overview_contains(value: Any, needle: str) -> bool:
    needle = str(needle or "").strip().lower()
    if not needle:
        return True
    return any(needle in item.lower() for item in execution_overview_text_values(value))


def execution_overview_node_kind_matches(record: dict[str, Any], record_type: str, node_kind: str) -> bool:
    node_kind = str(node_kind or "").strip().lower()
    if not node_kind:
        return True
    values: list[str] = []
    if record_type == "run":
        values.extend(execution_overview_text_values(record.get("_filter_node_kinds")))
        values.extend(execution_overview_text_values(record.get("node_kinds")))
    values.extend(execution_overview_text_values(record.get("kind")))
    return any(item.lower() == node_kind for item in values)


def execution_overview_record_timestamp(record: dict[str, Any]) -> float:
    return (
        parse_iso_timestamp(record.get("created_at"))
        or parse_iso_timestamp(record.get("started_at"))
        or parse_iso_timestamp(record.get("updated_at"))
        or parse_iso_timestamp(record.get("completed_at"))
        or parse_iso_timestamp(record.get("finished_at"))
    )


def execution_overview_public_record(record: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(record)
    for key in list(public):
        if str(key).startswith("_filter_"):
            public.pop(key, None)
    return public


def execution_overview_record_matches(
    record: dict[str, Any],
    record_type: str,
    *,
    query: str = "",
    status: str = "",
    node_kind: str = "",
    job_id: str = "",
    agent_execution_id: str = "",
    created_after_ts: float = 0.0,
    created_before_ts: float = 0.0,
) -> bool:
    if status and execution_overview_status_group(record.get("status")) != status:
        return False
    if query and query not in execution_overview_search_text(record, record_type):
        return False
    if not execution_overview_node_kind_matches(record, record_type, node_kind):
        return False
    if job_id:
        job_values: list[str] = []
        if record_type == "run":
            job_values.extend(execution_overview_text_values(record.get("_filter_job_ids")))
            job_values.extend(execution_overview_text_values(record.get("job_ids")))
        job_values.extend(execution_overview_text_values(record.get("id" if record_type == "job" else "job_id")))
        if not execution_overview_contains(job_values, job_id):
            return False
    if agent_execution_id:
        agent_values = execution_overview_text_values(record.get("_filter_agent_execution_ids"))
        agent_values.extend(execution_overview_text_values(record.get("agent_execution_ids")))
        agent_values.extend(execution_overview_text_values(record.get("agent_execution_id")))
        if not execution_overview_contains(agent_values, agent_execution_id):
            return False
    if created_after_ts or created_before_ts:
        record_ts = execution_overview_record_timestamp(record)
        if not record_ts:
            return False
        if created_after_ts and record_ts < created_after_ts:
            return False
        if created_before_ts and record_ts > created_before_ts:
            return False
    return True


def build_execution_overview_payload(
    requested: dict[str, Any],
    workspaces: list[Any],
    jobs: list[Any],
) -> dict[str, Any]:
    limit = max(1, min(safe_int(requested.get("limit"), 50), 200))
    query_text = str(requested.get("query") or requested.get("q") or "").strip().lower()
    status_filter = str(requested.get("status") or "").strip().lower()
    if status_filter not in {"", "active", "done", "failed"}:
        status_filter = ""
    kind_filter = str(requested.get("kind") or "all").strip().lower()
    if kind_filter not in {"all", "runs", "jobs"}:
        kind_filter = "all"
    node_kind_filter = str(requested.get("node_kind") or "").strip()
    job_id_filter = str(requested.get("job_id") or "").strip()
    agent_execution_id_filter = str(requested.get("agent_execution_id") or "").strip()
    created_after_filter = str(requested.get("created_after") or requested.get("created_after_iso") or "").strip()
    created_before_filter = str(requested.get("created_before") or requested.get("created_before_iso") or "").strip()
    created_after_ts = parse_iso_timestamp(created_after_filter)
    created_before_ts = parse_iso_timestamp(created_before_filter)
    workspace_names = {
        str(workspace.get("id") or "").strip(): str(workspace.get("name") or workspace.get("brief") or workspace.get("id") or "").strip()
        for workspace in workspaces
        if isinstance(workspace, dict) and str(workspace.get("id") or "").strip()
    }
    jobs_by_id = {
        str(job.get("id") or "").strip(): job
        for job in jobs
        if isinstance(job, dict) and str(job.get("id") or "").strip()
    }
    runs: list[dict[str, Any]] = []
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        workspace_id = str(workspace.get("id") or "").strip()
        workspace_name = workspace_names.get(workspace_id, workspace_id)
        for run in workspace_execution_runs_public(workspace.get("runs"), jobs):
            if not isinstance(run, dict):
                continue
            steps = run.get("steps") if isinstance(run.get("steps"), list) else []
            job_ids = [
                str(step.get("job_id") or "").strip()
                for step in steps
                if isinstance(step, dict) and str(step.get("job_id") or "").strip()
            ]
            child_job_ids = [
                str(child_id or "").strip()
                for step in steps
                if isinstance(step, dict) and isinstance(step.get("child_job_ids"), list)
                for child_id in step.get("child_job_ids")
                if str(child_id or "").strip()
            ]
            linked_job_ids = [*job_ids, *child_job_ids]
            agent_execution_ids = [
                str(step.get("agent_execution_id") or "").strip()
                for step in steps
                if isinstance(step, dict) and str(step.get("agent_execution_id") or "").strip()
            ]
            node_ids = [
                str(step.get("node_id") or "").strip()
                for step in steps
                if isinstance(step, dict) and str(step.get("node_id") or "").strip()
            ]
            node_kinds = [
                str(step.get("node_kind") or "").strip()
                for step in steps
                if isinstance(step, dict) and str(step.get("node_kind") or "").strip()
            ]
            server_ids = sorted(
                {
                    str((jobs_by_id.get(job_id) or {}).get("server_id") or "").strip()
                    for job_id in linked_job_ids
                    if str((jobs_by_id.get(job_id) or {}).get("server_id") or "").strip()
                }
            )
            runs.append(
                {
                    "id": str(run.get("id") or "").strip(),
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_name,
                    "kind": str(run.get("kind") or "").strip(),
                    "status": str(run.get("status") or "").strip(),
                    "summary": str(run.get("summary") or "").strip(),
                    "progress": copy.deepcopy(run.get("progress") if isinstance(run.get("progress"), dict) else {}),
                    "step_count": len(steps),
                    "job_ids": linked_job_ids[:8],
                    "agent_execution_ids": agent_execution_ids[:8],
                    "node_ids": node_ids[:12],
                    "node_kinds": node_kinds[:12],
                    "server_ids": server_ids[:8],
                    "_filter_job_ids": linked_job_ids,
                    "_filter_agent_execution_ids": agent_execution_ids,
                    "_filter_node_ids": node_ids,
                    "_filter_node_kinds": node_kinds,
                    "created_at": str(run.get("created_at") or "").strip(),
                    "updated_at": str(run.get("updated_at") or "").strip(),
                }
            )
    runs.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)

    job_items: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        workspace_id = str(metadata.get("workspace_id") or job.get("workspace_id") or "").strip()
        job_items.append(
            {
                "id": str(job.get("id") or "").strip(),
                "workspace_id": workspace_id,
                "workspace_name": workspace_names.get(workspace_id, workspace_id or "未绑定 workspace"),
                "status": str(job.get("status") or "").strip(),
                "kind": str(metadata.get("node_kind") or job.get("kind") or "").strip(),
                "server_id": str(job.get("server_id") or metadata.get("server_id") or "").strip(),
                "summary": str(job.get("summary") or metadata.get("node_title") or "").strip(),
                "execution_run_id": str(metadata.get("execution_run_id") or "").strip(),
                "agent_execution_id": str(metadata.get("agent_execution_id") or "").strip(),
                "created_at": str(job.get("created_at") or "").strip(),
                "updated_at": str(job.get("updated_at") or job.get("finished_at") or job.get("created_at") or "").strip(),
            }
        )
    job_items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    matched_runs = [
        run for run in runs
        if kind_filter != "jobs"
        and execution_overview_record_matches(
            run,
            "run",
            query=query_text,
            status=status_filter,
            node_kind=node_kind_filter,
            job_id=job_id_filter,
            agent_execution_id=agent_execution_id_filter,
            created_after_ts=created_after_ts,
            created_before_ts=created_before_ts,
        )
    ]
    matched_jobs = [
        job for job in job_items
        if kind_filter != "runs"
        and execution_overview_record_matches(
            job,
            "job",
            query=query_text,
            status=status_filter,
            node_kind=node_kind_filter,
            job_id=job_id_filter,
            agent_execution_id=agent_execution_id_filter,
            created_after_ts=created_after_ts,
            created_before_ts=created_before_ts,
        )
    ]
    return {
        "runs": [execution_overview_public_record(item) for item in matched_runs[:limit]],
        "jobs": [execution_overview_public_record(item) for item in matched_jobs[:limit]],
        "filters": {
            "query": query_text,
            "status": status_filter,
            "kind": kind_filter,
            "node_kind": node_kind_filter,
            "job_id": job_id_filter,
            "agent_execution_id": agent_execution_id_filter,
            "created_after": created_after_filter,
            "created_before": created_before_filter,
            "limit": limit,
        },
        "result": {
            "run_count": len(matched_runs),
            "job_count": len(matched_jobs),
            "returned_run_count": min(len(matched_runs), limit),
            "returned_job_count": min(len(matched_jobs), limit),
            "limited": len(matched_runs) > limit or len(matched_jobs) > limit,
        },
        "summary": {
            "run_count": len(runs),
            "job_count": len(job_items),
            "active_run_count": sum(1 for item in runs if str(item.get("status") or "") in {"queued", "running", "pending"}),
            "active_job_count": sum(1 for item in job_items if str(item.get("status") or "") in {"queued", "blocked", "starting", "running"}),
            "failed_run_count": sum(1 for item in runs if str(item.get("status") or "") in {"failed", "blocked", "stopped"}),
            "failed_job_count": sum(1 for item in job_items if str(item.get("status") or "") in {"failed", "stopped"}),
        },
    }
