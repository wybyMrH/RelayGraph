"""Execution run refresh and job synchronization helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_records import (
    derive_workspace_execution_run_progress,
    derive_workspace_execution_run_status,
    normalize_workspace_execution_run,
    normalize_workspace_execution_runs,
    workspace_execution_run_sort_key,
)
from .run_refs import _unique_run_ref_list
from .run_steps import (
    normalize_workspace_run_step,
    workspace_run_step_from_job,
    workspace_run_step_status_from_job,
)


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
