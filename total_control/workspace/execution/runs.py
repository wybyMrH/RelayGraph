"""Execution — runs helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .jobs import workspace_job_binding, workspace_job_sort_key
from .run_artifacts import normalize_workspace_run_step_artifacts
from .run_delivery import _workspace_delivery_path_candidates, workspace_execution_run_delivery_closure
from .run_events import (
    _compact_run_event_payload,
    _compact_run_event_text,
    _workspace_delta_event_text,
    _workspace_delta_evidence_id_list,
    normalize_workspace_run_delta_evidence,
    normalize_workspace_run_event,
    normalize_workspace_run_events,
    workspace_run_delta_evidence_from_event,
)
from .run_refs import (
    WORKSPACE_LINKED_RUN_CLOSURE_MAX,
    WORKSPACE_RUN_CHILD_REF_MAX,
    _unique_run_ref_list,
    workspace_execution_run_linked_run_closure,
    workspace_execution_run_linked_runs,
    workspace_job_matches_run_scope,
    workspace_run_allowed_child_run_ids,
    workspace_run_child_run_ids,
    workspace_run_job_ids,
    workspace_run_step_agent_execution_ids,
    workspace_run_step_child_run_ids,
    workspace_run_step_job_ids,
    workspace_runs_job_ids,
)
from .run_records import (
    derive_workspace_execution_run_progress,
    derive_workspace_execution_run_status,
    filter_workspace_execution_runs,
    make_agent_execution_id,
    make_workspace_execution_run_id,
    normalize_workspace_execution_run,
    normalize_workspace_execution_runs,
    workspace_execution_run_snapshot,
    workspace_execution_run_sort_key,
)
from .run_replay import (
    workspace_execution_run_replay_payload,
    workspace_execution_run_replay_run_summary,
    workspace_execution_run_timeline,
)
from .run_steps import (
    _normalize_agent_meta,
    normalize_workspace_run_step,
    normalize_workspace_run_step_resources,
    workspace_agent_runtime_refs,
    workspace_run_step_artifacts_from_job,
    workspace_run_step_from_agent,
    workspace_run_step_from_job,
    workspace_run_step_resources_from_job,
    workspace_run_step_status_from_job,
)
from .run_compare import workspace_execution_run_compare_payload
from .run_export import (
    workspace_execution_run_export_payload,
    workspace_run_export_manifest,
    workspace_run_export_readme,
)
from .trace import workspace_node_artifacts, workspace_node_resources, workspace_node_trace


def derive_workspace_execution_state(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    workspace_id = str(workspace.get("id") or "").strip()
    counts = {
        "pending": 0,
        "queued": 0,
        "running": 0,
        "done": 0,
        "failed": 0,
    }
    node_states: list[dict[str, Any]] = []
    latest_job: dict[str, Any] | None = None
    latest_error_job: dict[str, Any] | None = None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        bound_jobs = [
            job for job in jobs
            if workspace_job_binding(job) == (workspace_id, node_id)
        ]
        bound_jobs.sort(key=workspace_job_sort_key, reverse=True)
        latest = bound_jobs[0] if bound_jobs else None
        state = "pending"
        if latest:
            job_status = str(latest.get("status") or "").strip()
            if job_status in {"queued", "blocked", "starting"}:
                state = "queued"
            elif job_status == "running":
                state = "running"
            elif job_status == "done":
                state = "done"
            else:
                state = "failed"
            if latest_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_job):
                latest_job = latest
            if str(latest.get("error") or "").strip():
                if latest_error_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_error_job):
                    latest_error_job = latest
        counts[state] += 1
        resources = workspace_node_resources(workspace, node, latest)
        artifacts = workspace_node_artifacts(workspace, node, latest)
        trace = workspace_node_trace(node, bound_jobs, state)
        latest_metadata = latest.get("metadata") if latest and isinstance(latest.get("metadata"), dict) else {}
        runtime_contract = latest_metadata.get("workflow_contract_node") if isinstance(latest_metadata.get("workflow_contract_node"), dict) else {}
        runtime_bundle = latest_metadata.get("execution_bundle") if isinstance(latest_metadata.get("execution_bundle"), dict) else {}
        if not runtime_contract:
            from ..automation.contracts import workspace_node_workflow_contract_metadata

            runtime_contract = workspace_node_workflow_contract_metadata(workspace, node)
        node_states.append(
            {
                "id": node_id,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "status": state,
                "agent_id": str(handler.get("agent_id") or "").strip(),
                "agent_name": str(handler.get("name") or "").strip(),
                "job_id": str(latest.get("id") or "").strip() if latest else "",
                "job_status": str(latest.get("status") or "").strip() if latest else "",
                "error": str(latest.get("error") or "").strip() if latest else "",
                "run_count": len(bound_jobs),
                "trace": trace,
                "artifacts": artifacts,
                "resources": resources,
                "workflow_contract_node": runtime_contract,
                "execution_bundle": runtime_bundle,
            }
        )

    selected_node = (
        next((item for item in node_states if item["status"] == "running"), None)
        or next((item for item in node_states if item["status"] == "queued"), None)
        or next((item for item in node_states if item["status"] == "failed"), None)
        or next((item for item in node_states if item["status"] == "pending"), None)
        or (node_states[-1] if node_states else None)
    )
    current_node_id = str(selected_node.get("id") or "").strip() if selected_node else ""
    current_agent_id = str(selected_node.get("agent_id") or "").strip() if selected_node else ""

    return {
        "current_node_id": current_node_id,
        "current_agent_id": current_agent_id,
        "counts": counts,
        "nodes": node_states,
        "last_job_id": str(latest_job.get("id") or "").strip() if latest_job else "",
        "last_job_status": str(latest_job.get("status") or "").strip() if latest_job else "",
        "latest_error": str(latest_error_job.get("error") or "").strip() if latest_error_job else "",
    }

def _workspace_child_run_status(run: dict[str, Any]) -> str:
    status = str(run.get("status") or "").strip()
    if status in {"done", "failed", "stopped", "blocked", "running"}:
        return status
    return "queued" if status else ""


def _workspace_child_run_error(run: dict[str, Any], status: str) -> str:
    detail = str(run.get("error") or "").strip()
    if detail:
        return detail
    for step in run.get("steps") if isinstance(run.get("steps"), list) else []:
        if not isinstance(step, dict):
            continue
        step_status = str(step.get("status") or "").strip()
        if step_status == status or step_status in {"failed", "stopped", "blocked"}:
            detail = str(step.get("error") or "").strip()
            if detail:
                return detail
    return ""


def _workspace_agent_child_runtime_status(
    child_jobs: list[tuple[str, dict[str, Any]]],
    child_runs: list[tuple[str, dict[str, Any]]] | None = None,
) -> tuple[str, str, str, str]:
    if not child_jobs and not child_runs:
        return "", "", "", ""
    statuses = [
        ("job", job_id, workspace_run_step_status_from_job(job), job)
        for job_id, job in child_jobs
        if isinstance(job, dict)
    ]
    statuses.extend(
        (
            "run",
            run_id,
            _workspace_child_run_status(run),
            run,
        )
        for run_id, run in (child_runs or [])
        if isinstance(run, dict)
    )
    if not statuses:
        return "", "", "", ""
    for terminal_status in ("failed", "stopped", "blocked"):
        for ref_kind, ref_id, status, payload in statuses:
            if status != terminal_status:
                continue
            detail = (
                _workspace_child_run_error(payload, status)
                if ref_kind == "run"
                else str(payload.get("error") or "").strip()
            )
            error = detail or f"child {ref_kind} {ref_id} {terminal_status}"
            return terminal_status, terminal_status, ref_id, error
    if any(status == "running" for _, _, status, _ in statuses):
        return "running", "running", "", ""
    if any(status == "queued" for _, _, status, _ in statuses):
        return "running", "queued", "", ""
    if all(status == "done" for _, _, status, _ in statuses):
        return "done", "done", "", ""
    return "", "", "", ""


def refresh_workspace_agent_run_step_from_child_jobs(
    step: dict[str, Any],
    jobs_by_id: dict[str, dict[str, Any]],
    runs_by_id: dict[str, dict[str, Any]] | None = None,
    *,
    current_run_id: str = "",
) -> dict[str, Any]:
    normalized = normalize_workspace_run_step(step, existing=step)
    child_job_ids = _unique_run_ref_list(normalized.get("child_job_ids"))
    child_jobs = [
        (job_id, jobs_by_id[job_id])
        for job_id in child_job_ids
        if job_id in jobs_by_id and isinstance(jobs_by_id[job_id], dict)
    ]
    child_run_ids = _unique_run_ref_list(normalized.get("child_run_ids"))
    run_lookup = runs_by_id if isinstance(runs_by_id, dict) else {}
    child_runs = [
        (run_id, run_lookup[run_id])
        for run_id in child_run_ids
        if run_id != current_run_id and run_id in run_lookup and isinstance(run_lookup[run_id], dict)
    ]
    if not child_jobs and not child_runs:
        return normalized

    step_status, runtime_status, failed_child_id, error = _workspace_agent_child_runtime_status(child_jobs, child_runs)
    if not step_status:
        return normalized

    completed_at = str(normalized.get("completed_at") or "").strip()
    if step_status in {"done", "failed", "stopped", "blocked"}:
        finished_times = [
            str(job.get("finished_at") or job.get("completed_at") or "").strip()
            for _, job in child_jobs
            if str(job.get("finished_at") or job.get("completed_at") or "").strip()
        ]
        finished_times.extend(
            str(run.get("finished_at") or run.get("completed_at") or run.get("updated_at") or "").strip()
            for _, run in child_runs
            if str(run.get("finished_at") or run.get("completed_at") or run.get("updated_at") or "").strip()
        )
        completed_at = max(finished_times) if finished_times else completed_at

    refreshed = normalize_workspace_run_step(
        {
            **normalized,
            "status": step_status,
            "runtime_status": runtime_status,
            "completed_at": completed_at,
            "error": error or str(normalized.get("error") or "").strip(),
        },
        existing=normalized,
    )
    if step_status in {"running", "queued"}:
        refreshed["completed_at"] = ""
        refreshed["error"] = ""
    elif not failed_child_id and step_status == "done":
        refreshed["error"] = ""
    return refreshed

def workspace_jobs_bound_to_execution_run(
    jobs_by_id: dict[str, dict[str, Any]],
    run_id: str,
) -> list[dict[str, Any]]:
    target_run_id = str(run_id or "").strip()
    if not target_run_id:
        return []
    jobs: list[dict[str, Any]] = []
    for job in jobs_by_id.values():
        if not isinstance(job, dict):
            continue
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        if str(metadata.get("execution_run_id") or "").strip() == target_run_id:
            jobs.append(job)

    def sort_key(job: dict[str, Any]) -> tuple[int, str, str]:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        raw_index = metadata.get("step_index")
        if raw_index is None or str(raw_index).strip() == "":
            index = len(jobs)
        else:
            index = safe_int(raw_index, len(jobs))
        created_at = str(job.get("created_at") or job.get("started_at") or job.get("updated_at") or "").strip()
        return (index, created_at, str(job.get("id") or "").strip())

    jobs.sort(key=sort_key)
    return jobs

def refresh_workspace_execution_run(
    run: dict[str, Any],
    jobs_by_id: dict[str, dict[str, Any]],
    runs_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    steps = run.get("steps") if isinstance(run.get("steps"), list) else []
    refreshed_steps: list[dict[str, Any]] = []
    step_job_ids: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        executor = str(step.get("executor") or "job").strip()
        job_id = str(step.get("job_id") or "").strip()
        if job_id:
            step_job_ids.add(job_id)
        job = jobs_by_id.get(job_id)
        if executor == "agent":
            refreshed_steps.append(
                refresh_workspace_agent_run_step_from_child_jobs(
                    step,
                    jobs_by_id,
                    runs_by_id,
                    current_run_id=str(run.get("id") or "").strip(),
                )
            )
        elif job:
            job_step = workspace_run_step_from_job(job, safe_int(step.get("index"), len(refreshed_steps)))
            for key in ("child_job_ids", "child_run_ids"):
                if not job_step.get(key) and isinstance(step.get(key), list):
                    job_step[key] = copy.deepcopy(step.get(key))
            for key in ("artifacts", "mapped_inputs", "trace_events"):
                if not job_step.get(key) and isinstance(step.get(key), list):
                    job_step[key] = copy.deepcopy(step.get(key))
            if isinstance(job_step.get("artifacts"), list):
                job_step["artifact_count"] = len([item for item in job_step["artifacts"] if isinstance(item, dict)])
            for key in ("resources", "validation"):
                if not job_step.get(key) and isinstance(step.get(key), dict):
                    job_step[key] = copy.deepcopy(step.get(key))
            for key in ("runtime_control", "runtime_status", "runtime_side_effect"):
                if not str(job_step.get(key) or "").strip() and str(step.get(key) or "").strip():
                    job_step[key] = str(step.get(key) or "").strip()
            refreshed_steps.append(
                normalize_workspace_run_step(
                    job_step,
                    existing=step,
                )
            )
        else:
            refreshed_steps.append(normalize_workspace_run_step(step, existing=step))
    for job in workspace_jobs_bound_to_execution_run(jobs_by_id, str(run.get("id") or "").strip()):
        job_id = str(job.get("id") or "").strip()
        if not job_id or job_id in step_job_ids:
            continue
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        raw_index = metadata.get("step_index")
        step_index = (
            safe_int(raw_index, len(refreshed_steps))
            if raw_index is not None and str(raw_index).strip() != ""
            else len(refreshed_steps)
        )
        refreshed_steps.append(workspace_run_step_from_job(job, step_index))
        step_job_ids.add(job_id)
    return normalize_workspace_execution_run(
        {
            **run,
            "steps": refreshed_steps,
            "status": derive_workspace_execution_run_status(refreshed_steps),
            "progress": derive_workspace_execution_run_progress(refreshed_steps),
            "updated_at": now_iso(),
        },
        existing=run,
    )

def workspace_execution_runs_public(
    runs: Any,
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs_by_id = {
        str(job.get("id") or "").strip(): job
        for job in jobs
        if isinstance(job, dict) and str(job.get("id") or "").strip()
    }
    normalized = normalize_workspace_execution_runs(runs)
    runs_by_id = {
        str(run.get("id") or "").strip(): run
        for run in normalized
        if isinstance(run, dict) and str(run.get("id") or "").strip()
    }
    refreshed = [refresh_workspace_execution_run(run, jobs_by_id, runs_by_id) for run in normalized]
    refreshed.sort(key=workspace_execution_run_sort_key, reverse=True)
    return refreshed
