"""Execution run reference and linked-run closure helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

WORKSPACE_LINKED_RUN_CLOSURE_MAX = 64


def _unique_run_ref_list(value: Any) -> list[str]:
    refs: list[str] = []
    for item in value if isinstance(value, list) else []:
        text = str(item or "").strip()
        if text and text not in refs:
            refs.append(text)
    return refs


def workspace_run_step_job_ids(step: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    direct = str(step.get("job_id") or "").strip()
    if direct:
        ids.append(direct)
    ids.extend(_unique_run_ref_list(step.get("child_job_ids") if isinstance(step.get("child_job_ids"), list) else []))
    return _unique_run_ref_list(ids)


def workspace_run_step_agent_execution_ids(step: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    direct = str(step.get("agent_execution_id") or "").strip()
    if direct:
        ids.append(direct)
    ids.extend(_unique_run_ref_list(step.get("agent_execution_ids") if isinstance(step.get("agent_execution_ids"), list) else []))
    return _unique_run_ref_list(ids)


def workspace_run_job_ids(run: dict[str, Any]) -> list[str]:
    return _unique_run_ref_list(
        [
            job_id
            for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            if isinstance(step, dict)
            for job_id in workspace_run_step_job_ids(step)
        ]
    )


def workspace_runs_job_ids(runs: Any) -> list[str]:
    return _unique_run_ref_list(
        [
            job_id
            for run in (runs if isinstance(runs, list) else [])
            if isinstance(run, dict)
            for job_id in workspace_run_job_ids(run)
        ]
    )


def workspace_run_step_child_run_ids(step: dict[str, Any]) -> list[str]:
    return _unique_run_ref_list(step.get("child_run_ids") if isinstance(step.get("child_run_ids"), list) else [])


def workspace_run_child_run_ids(run: dict[str, Any]) -> list[str]:
    return _unique_run_ref_list(
        [
            run_id
            for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            if isinstance(step, dict)
            for run_id in workspace_run_step_child_run_ids(step)
        ]
    )


def workspace_run_allowed_child_run_ids(run: dict[str, Any]) -> set[str]:
    return set(workspace_run_child_run_ids(run))


def workspace_execution_run_linked_runs(
    workspace: dict[str, Any],
    run: dict[str, Any],
    *,
    max_runs: int = WORKSPACE_LINKED_RUN_CLOSURE_MAX,
) -> list[dict[str, Any]]:
    return workspace_execution_run_linked_run_closure(workspace, run, max_runs=max_runs)["runs"]


def workspace_execution_run_linked_run_closure(
    workspace: dict[str, Any],
    run: dict[str, Any],
    *,
    max_runs: int = WORKSPACE_LINKED_RUN_CLOSURE_MAX,
) -> dict[str, Any]:
    workspace_id = str(workspace.get("id") or run.get("workspace_id") or "").strip()
    root_run_id = str(run.get("id") or "").strip()
    runs = workspace.get("runs") if isinstance(workspace.get("runs"), list) else []
    runs_by_id = {
        str(item.get("id") or "").strip(): item
        for item in runs
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    seen = {root_run_id} if root_run_id else set()
    queue = workspace_run_child_run_ids(run)
    linked: list[dict[str, Any]] = []
    missing_run_ids: list[str] = []
    cross_workspace_run_ids: list[str] = []
    limit = max(0, min(safe_int(max_runs, WORKSPACE_LINKED_RUN_CLOSURE_MAX), WORKSPACE_LINKED_RUN_CLOSURE_MAX))
    while queue and len(linked) < limit:
        child_run_id = queue.pop(0)
        if not child_run_id or child_run_id in seen:
            continue
        seen.add(child_run_id)
        child_run = runs_by_id.get(child_run_id)
        if not isinstance(child_run, dict):
            missing_run_ids.append(child_run_id)
            continue
        child_workspace_id = str(child_run.get("workspace_id") or workspace_id).strip()
        if workspace_id and child_workspace_id and child_workspace_id != workspace_id:
            cross_workspace_run_ids.append(child_run_id)
            continue
        linked.append(copy.deepcopy(child_run))
        for nested_id in workspace_run_child_run_ids(child_run):
            if nested_id and nested_id not in seen:
                queue.append(nested_id)
    pending_run_ids = [
        item for item in queue
        if str(item or "").strip() and str(item or "").strip() not in seen
    ]
    return {
        "runs": linked,
        "limit": limit,
        "included_count": len(linked),
        "truncated": bool(queue),
        "pending_count": len(pending_run_ids),
        "pending_run_ids": pending_run_ids[:12],
        "missing_count": len(missing_run_ids),
        "missing_run_ids": missing_run_ids[:12],
        "cross_workspace_count": len(cross_workspace_run_ids),
        "cross_workspace_run_ids": cross_workspace_run_ids[:12],
    }


def workspace_job_matches_run_scope(
    job: dict[str, Any],
    *,
    workspace_id: str,
    run_id: str,
    allowed_child_run_ids: set[str] | None = None,
) -> bool:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    job_workspace_id = str(metadata.get("workspace_id") or "").strip()
    if job_workspace_id and workspace_id and job_workspace_id != workspace_id:
        return False
    job_run_id = str(metadata.get("execution_run_id") or "").strip()
    allowed_run_ids = {str(run_id or "").strip()}
    allowed_run_ids.update(allowed_child_run_ids or set())
    allowed_run_ids = {item for item in allowed_run_ids if item}
    if job_run_id and allowed_run_ids and job_run_id not in allowed_run_ids:
        return False
    return True


def workspace_jobs_for_run(
    workspace_id: str,
    run: dict[str, Any],
    jobs: list[dict[str, Any]] | None,
    *,
    linked_runs: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    run_id = str(run.get("id") or "").strip()
    linked = [item for item in (linked_runs or []) if isinstance(item, dict)]
    referenced_job_ids = set(workspace_runs_job_ids([run, *linked]))
    allowed_child_run_ids = workspace_run_allowed_child_run_ids(run)
    for linked_run in linked:
        linked_run_id = str(linked_run.get("id") or "").strip()
        if linked_run_id:
            allowed_child_run_ids.add(linked_run_id)
        allowed_child_run_ids.update(workspace_run_allowed_child_run_ids(linked_run))
    scoped: dict[str, dict[str, Any]] = {}
    for job in jobs or []:
        if not isinstance(job, dict):
            continue
        job_id = str(job.get("id") or "").strip()
        if not job_id or job_id not in referenced_job_ids:
            continue
        if not workspace_job_matches_run_scope(
            job,
            workspace_id=workspace_id,
            run_id=run_id,
            allowed_child_run_ids=allowed_child_run_ids,
        ):
            continue
        scoped[job_id] = job
    return scoped
