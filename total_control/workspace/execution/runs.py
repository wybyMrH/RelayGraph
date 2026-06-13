"""Execution — runs helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .jobs import workspace_job_binding, workspace_job_sort_key
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

def make_workspace_execution_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]

def make_agent_execution_id() -> str:
    return "aex-" + uuid.uuid4().hex[:12]

def workspace_run_step_status_from_job(job: dict[str, Any]) -> str:
    status = str(job.get("status") or "queued").strip()
    if status in {"starting", "running"}:
        return "running"
    if status in {"failed", "stopped"}:
        return "failed"
    if status == "done":
        return "done"
    if status == "blocked":
        return "blocked"
    return "queued"

def normalize_workspace_run_step(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing if isinstance(existing, dict) else {}
    payload = value if isinstance(value, dict) else {}
    index = safe_int(payload.get("index"), safe_int(current.get("index"), 0))
    status = str(payload.get("status") or current.get("status") or "queued").strip() or "queued"
    payload_agent_steps = payload.get("agent_steps") if isinstance(payload.get("agent_steps"), list) else None
    payload_mapped_inputs = payload.get("mapped_inputs") if isinstance(payload.get("mapped_inputs"), list) else None
    return {
        "index": index,
        "node_id": str(payload.get("node_id") or current.get("node_id") or "").strip(),
        "node_kind": str(payload.get("node_kind") or current.get("node_kind") or "").strip(),
        "node_title": str(payload.get("node_title") or current.get("node_title") or payload.get("node_kind") or current.get("node_kind") or "").strip(),
        "executor": str(payload.get("executor") or current.get("executor") or "job").strip() or "job",
        "job_id": str(payload.get("job_id") or current.get("job_id") or "").strip(),
        "agent_execution_id": str(payload.get("agent_execution_id") or current.get("agent_execution_id") or "").strip(),
        "output_key": str(payload.get("output_key") or current.get("output_key") or "").strip(),
        "artifact_count": safe_int(payload.get("artifact_count"), safe_int(current.get("artifact_count"), 0)),
        "mapped_inputs": [
            item for item in (payload_mapped_inputs if payload_mapped_inputs else (current.get("mapped_inputs") or []))
            if isinstance(item, dict)
        ][:6],
        "agent_steps": [
            item for item in (payload_agent_steps if payload_agent_steps else (current.get("agent_steps") or []))
            if isinstance(item, dict)
        ][:24],
        "status": status,
        "started_at": str(payload.get("started_at") or current.get("started_at") or "").strip(),
        "completed_at": str(payload.get("completed_at") or current.get("completed_at") or "").strip(),
        "error": str(payload.get("error") or current.get("error") or "").strip(),
    }

def derive_workspace_execution_run_status(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "pending"
    statuses = [str(step.get("status") or "").strip() for step in steps]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "running" for status in statuses):
        return "running"
    if any(status == "queued" for status in statuses):
        return "queued"
    if all(status == "done" for status in statuses):
        return "done"
    return "pending"

def derive_workspace_execution_run_progress(steps: list[dict[str, Any]]) -> dict[str, int]:
    total = len(steps)
    done = sum(1 for step in steps if str(step.get("status") or "") == "done")
    failed = sum(1 for step in steps if str(step.get("status") or "") in {"failed", "blocked"})
    running = sum(1 for step in steps if str(step.get("status") or "") == "running")
    queued = sum(1 for step in steps if str(step.get("status") or "") == "queued")
    percent = int((done / total) * 100) if total else 0
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "running": running,
        "queued": queued,
        "percent": percent,
    }

def normalize_workspace_execution_run(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing if isinstance(existing, dict) else {}
    payload = value if isinstance(value, dict) else {}
    run_id = str(payload.get("id") or current.get("id") or "").strip() or make_workspace_execution_run_id()
    workspace_id = str(payload.get("workspace_id") or current.get("workspace_id") or "").strip()
    kind = str(payload.get("kind") or current.get("kind") or "node").strip() or "node"
    if kind not in WORKSPACE_EXECUTION_RUN_KINDS:
        kind = "node"
    raw_steps = payload.get("steps") if isinstance(payload.get("steps"), list) else current.get("steps")
    existing_steps = current.get("steps") if isinstance(current.get("steps"), list) else []
    steps = [
        normalize_workspace_run_step(
            item,
            existing=existing_steps[index] if index < len(existing_steps) and isinstance(existing_steps[index], dict) else None,
        )
        for index, item in enumerate(raw_steps or [])
        if isinstance(item, dict)
    ]
    steps.sort(key=lambda item: safe_int(item.get("index"), 0))
    status = str(payload.get("status") or current.get("status") or derive_workspace_execution_run_status(steps)).strip()
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else current.get("progress")
    if not isinstance(progress, dict):
        progress = derive_workspace_execution_run_progress(steps)
    else:
        progress = derive_workspace_execution_run_progress(steps)
    created_at = str(payload.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        "id": run_id,
        "workspace_id": workspace_id,
        "kind": kind,
        "status": status,
        "trigger": str(payload.get("trigger") or current.get("trigger") or "user").strip() or "user",
        "summary": str(payload.get("summary") or current.get("summary") or "").strip(),
        "steps": steps,
        "progress": progress,
        "created_at": created_at,
        "updated_at": str(payload.get("updated_at") or current.get("updated_at") or created_at).strip() or created_at,
    }

def normalize_workspace_execution_runs(
    value: Any,
    *,
    existing: list[dict[str, Any]] | None = None,
    limit: int = WORKSPACE_EXECUTION_RUN_MAX,
) -> list[dict[str, Any]]:
    raw_items = value if isinstance(value, list) else []
    existing_items = existing if isinstance(existing, list) else []
    existing_by_id = {
        str(item.get("id") or "").strip(): item
        for item in existing_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    runs = [
        normalize_workspace_execution_run(
            item,
            existing=existing_by_id.get(str(item.get("id") or "").strip()),
        )
        for item in raw_items
        if isinstance(item, dict)
    ]
    runs.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    return runs[: max(limit, 1)]

def workspace_execution_run_sort_key(run: dict[str, Any]) -> tuple[str, str]:
    return (str(run.get("created_at") or ""), str(run.get("id") or ""))

def workspace_run_step_from_job(job: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    return normalize_workspace_run_step(
        {
            "index": index,
            "node_id": str(metadata.get("node_id") or "").strip(),
            "node_kind": str(metadata.get("node_kind") or "").strip(),
            "node_title": str(metadata.get("node_title") or metadata.get("node_kind") or "").strip(),
            "executor": "job",
            "job_id": str(job.get("id") or "").strip(),
            "status": workspace_run_step_status_from_job(job),
            "started_at": str(job.get("started_at") or "").strip(),
            "completed_at": str(job.get("finished_at") or "").strip(),
            "error": str(job.get("error") or "").strip(),
        }
    )

def workspace_run_step_from_agent(
    node: dict[str, Any],
    step_result: StepResult | dict[str, Any],
    index: int,
) -> dict[str, Any]:
    payload = step_result.as_dict() if isinstance(step_result, StepResult) else step_result
    raw_status = str(payload.get("status") or "").strip()
    if payload.get("skipped"):
        step_status = "done"
    elif raw_status in {"completed", "warning"}:
        step_status = "done"
    elif raw_status == "failed":
        step_status = "failed"
    elif raw_status == "blocked":
        step_status = "blocked"
    else:
        step_status = "blocked"
    timestamp = now_iso()
    mapped_inputs = payload.get("mapped_inputs") if isinstance(payload.get("mapped_inputs"), list) else []
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), list) else []
    agent_steps = payload.get("agent_steps") if isinstance(payload.get("agent_steps"), list) else []
    return normalize_workspace_run_step(
        {
            "index": index,
            "node_id": str(node.get("id") or "").strip(),
            "node_kind": str(node.get("kind") or "").strip(),
            "node_title": str(node.get("title") or node.get("kind") or "").strip(),
            "executor": "agent",
            "agent_execution_id": str(payload.get("agent_execution_id") or "").strip(),
            "output_key": str(payload.get("output_key") or "").strip(),
            "artifact_count": len([item for item in artifacts if isinstance(item, dict)]),
            "mapped_inputs": [item for item in mapped_inputs if isinstance(item, dict)][:6],
            "agent_steps": [item for item in agent_steps if isinstance(item, dict)][:24],
            "status": step_status,
            "started_at": timestamp,
            "completed_at": timestamp,
            "error": str(payload.get("reason") or payload.get("detail") or "").strip(),
        }
    )

def refresh_workspace_execution_run(
    run: dict[str, Any],
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    steps = run.get("steps") if isinstance(run.get("steps"), list) else []
    refreshed_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        executor = str(step.get("executor") or "job").strip()
        job_id = str(step.get("job_id") or "").strip()
        job = jobs_by_id.get(job_id)
        if executor == "agent":
            refreshed_steps.append(normalize_workspace_run_step(step, existing=step))
        elif job:
            refreshed_steps.append(
                normalize_workspace_run_step(
                    workspace_run_step_from_job(job, safe_int(step.get("index"), len(refreshed_steps))),
                    existing=step,
                )
            )
        else:
            refreshed_steps.append(normalize_workspace_run_step(step, existing=step))
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
    refreshed = [refresh_workspace_execution_run(run, jobs_by_id) for run in normalized]
    refreshed.sort(key=workspace_execution_run_sort_key, reverse=True)
    return refreshed

def workspace_execution_run_snapshot(run: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    steps = run.get("steps") if isinstance(run.get("steps"), list) else []
    return (
        str(run.get("status") or ""),
        tuple(
            (
                str(step.get("status") or ""),
                str(step.get("error") or ""),
                str(step.get("started_at") or ""),
                str(step.get("completed_at") or ""),
            )
            for step in steps
            if isinstance(step, dict)
        ),
    )
