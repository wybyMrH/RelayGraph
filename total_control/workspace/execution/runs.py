"""Execution — runs helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from ...orchestration.types import StepResult
from .jobs import workspace_job_binding, workspace_job_sort_key
from .agent_trace import normalize_agent_trace_events
from .log_parser import (
    parse_workspace_artifacts_from_log,
    parse_workspace_metrics_from_log,
    parse_workspace_resources_from_log,
    workspace_dedupe_artifacts,
)
from .paths import workspace_job_cached_log_tail, workspace_job_cached_log_tail_payload
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
    _unique_run_ref_list,
    workspace_execution_run_linked_run_closure,
    workspace_execution_run_linked_runs,
    workspace_job_matches_run_scope,
    workspace_jobs_for_run,
    workspace_run_allowed_child_run_ids,
    workspace_run_child_run_ids,
    workspace_run_job_ids,
    workspace_run_step_agent_execution_ids,
    workspace_run_step_child_run_ids,
    workspace_run_step_job_ids,
    workspace_runs_job_ids,
)
from .run_replay import (
    workspace_execution_run_replay_payload,
    workspace_execution_run_replay_run_summary,
    workspace_execution_run_timeline,
)
from .trace import workspace_node_artifacts, workspace_node_resources, workspace_node_trace

WORKSPACE_RUN_CHILD_REF_MAX = 64


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
    if status == "failed":
        return "failed"
    if status == "stopped":
        return "stopped"
    if status == "done":
        return "done"
    if status == "blocked":
        return "blocked"
    return "queued"

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

def _normalize_agent_meta(payload: Any, current: Any) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) and payload else (current if isinstance(current, dict) else {})
    if not source:
        return {}
    return {
        "model": str(source.get("model") or "").strip(),
        "total_tokens": safe_int(source.get("total_tokens"), 0),
        "execution_time_ms": round(float(source.get("execution_time_ms") or 0), 1),
        "max_iterations": safe_int(source.get("max_iterations"), 0),
    }


def normalize_workspace_run_step_artifacts(value: Any, current: Any = None) -> list[dict[str, Any]]:
    raw_items = value if isinstance(value, list) else (current if isinstance(current, list) else [])
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("name") or item.get("kind") or "artifact").strip()
        path = str(item.get("resolved_path") or item.get("path") or item.get("value") or "").strip()
        if not label and not path:
            continue
        normalized = {
            "label": label or "artifact",
            "path": path,
            "resolved_path": str(item.get("resolved_path") or path).strip(),
            "source": str(item.get("source") or "").strip(),
            "status": str(item.get("status") or "planned").strip() or "planned",
            "exists": bool(item.get("exists")) if item.get("exists") is not None else False,
        }
        artifact_type = str(item.get("type") or item.get("artifact_type") or "").strip()
        if artifact_type:
            normalized["type"] = artifact_type
        summary = str(item.get("summary") or "").strip()
        if summary:
            normalized["summary"] = summary[:240]
        content = str(item.get("content") or "").strip()
        if content:
            normalized["content"] = content[:4000]
        if item.get("node_id"):
            normalized["node_id"] = str(item.get("node_id") or "").strip()
        if item.get("node_kind"):
            normalized["node_kind"] = str(item.get("node_kind") or "").strip()
        items.append(normalized)
    return workspace_dedupe_artifacts(items)[:24]


def normalize_workspace_run_step_resources(value: Any, current: Any = None) -> dict[str, Any]:
    source = value if isinstance(value, dict) and value else (current if isinstance(current, dict) else {})
    if not source:
        return {}
    normalized: dict[str, Any] = {}
    for key in (
        "server_id",
        "requested_server_id",
        "gpu_index",
        "gpu_policy",
        "execution_mode",
        "cwd",
        "env_name",
        "scheduler_status",
        "scheduler_summary",
    ):
        text = str(source.get(key) or "").strip()
        if text:
            normalized[key] = text
    for key in ("wait_for_idle",):
        if key in source:
            normalized[key] = bool(source.get(key))
    for key in ("depends_on", "scheduler_reasons"):
        values = source.get(key) if isinstance(source.get(key), list) else []
        if values:
            normalized[key] = [str(item or "").strip() for item in values if str(item or "").strip()][:8]
    metrics = source.get("metrics") if isinstance(source.get("metrics"), dict) else {}
    if metrics:
        normalized["metrics"] = copy.deepcopy(metrics)
    runtime_binding = source.get("runtime_binding") if isinstance(source.get("runtime_binding"), dict) else {}
    if runtime_binding:
        normalized["runtime_binding"] = copy.deepcopy(runtime_binding)
    scheduler_binding = source.get("scheduler_binding") if isinstance(source.get("scheduler_binding"), dict) else {}
    if scheduler_binding:
        normalized["scheduler_binding"] = copy.deepcopy(scheduler_binding)
    return normalized


def workspace_run_step_artifacts_from_job(job: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    artifacts = metadata.get("artifact_plan") if isinstance(metadata.get("artifact_plan"), list) else []
    log_text = workspace_job_cached_log_tail(job)
    if log_text:
        artifacts = [
            *[item for item in artifacts if isinstance(item, dict)],
            *parse_workspace_artifacts_from_log(str(metadata.get("node_kind") or ""), log_text),
        ]
    return normalize_workspace_run_step_artifacts(artifacts)


def workspace_run_step_resources_from_job(job: dict[str, Any]) -> dict[str, Any]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    resources = metadata.get("resource_plan") if isinstance(metadata.get("resource_plan"), dict) else {}
    next_resources = copy.deepcopy(resources)
    for key in ("runtime_binding", "scheduler_binding"):
        if isinstance(metadata.get(key), dict):
            next_resources[key] = copy.deepcopy(metadata[key])
    log_text = workspace_job_cached_log_tail(job)
    if log_text:
        node_kind = str(metadata.get("node_kind") or "").strip()
        next_resources.update(parse_workspace_resources_from_log(node_kind, log_text))
        metrics = parse_workspace_metrics_from_log(node_kind, log_text)
        if metrics:
            next_resources["metrics"] = metrics
    return normalize_workspace_run_step_resources(next_resources)


def workspace_agent_runtime_refs(agent_steps: Any, trace_events: Any) -> dict[str, Any]:
    refs: dict[str, list[str]] = {
        "job_ids": [],
        "run_ids": [],
        "runtime_controls": [],
        "runtime_statuses": [],
        "runtime_side_effects": [],
    }
    sources = [
        *(agent_steps if isinstance(agent_steps, list) else []),
        *(trace_events if isinstance(trace_events, list) else []),
    ]
    for item in sources:
        if not isinstance(item, dict):
            continue
        for source_key, bucket_key in (
            ("job_id", "job_ids"),
            ("run_id", "run_ids"),
            ("runtime_control", "runtime_controls"),
            ("runtime_status", "runtime_statuses"),
            ("runtime_side_effect", "runtime_side_effects"),
        ):
            text = str(item.get(source_key) or "").strip()
            if text and text not in refs[bucket_key]:
                refs[bucket_key].append(text)
    return {
        "job_id": "",
        "child_job_ids": refs["job_ids"],
        "child_run_ids": refs["run_ids"],
        "child_job_ref_count": len(refs["job_ids"]),
        "child_run_ref_count": len(refs["run_ids"]),
        "child_job_ids_truncated": len(refs["job_ids"]) > WORKSPACE_RUN_CHILD_REF_MAX,
        "child_run_ids_truncated": len(refs["run_ids"]) > WORKSPACE_RUN_CHILD_REF_MAX,
        "runtime_control": refs["runtime_controls"][0] if refs["runtime_controls"] else "",
        "runtime_status": refs["runtime_statuses"][0] if refs["runtime_statuses"] else "",
        "runtime_side_effect": refs["runtime_side_effects"][0] if refs["runtime_side_effects"] else "",
    }


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
    payload_trace_events = payload.get("trace_events") if isinstance(payload.get("trace_events"), list) else None
    payload_mapped_inputs = payload.get("mapped_inputs") if isinstance(payload.get("mapped_inputs"), list) else None
    payload_artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), list) else None
    payload_resources = payload.get("resources") if isinstance(payload.get("resources"), dict) else None
    payload_validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else None
    child_job_ids = _unique_run_ref_list(
        payload.get("child_job_ids")
        if isinstance(payload.get("child_job_ids"), list)
        else current.get("child_job_ids")
    )
    child_run_ids = _unique_run_ref_list(
        payload.get("child_run_ids")
        if isinstance(payload.get("child_run_ids"), list)
        else current.get("child_run_ids")
    )
    child_job_ref_count = max(
        len(child_job_ids),
        safe_int(payload.get("child_job_ref_count"), safe_int(current.get("child_job_ref_count"), len(child_job_ids))),
    )
    child_run_ref_count = max(
        len(child_run_ids),
        safe_int(payload.get("child_run_ref_count"), safe_int(current.get("child_run_ref_count"), len(child_run_ids))),
    )
    child_job_ids = child_job_ids[:WORKSPACE_RUN_CHILD_REF_MAX]
    child_run_ids = child_run_ids[:WORKSPACE_RUN_CHILD_REF_MAX]
    child_job_ids_truncated = (
        bool(payload.get("child_job_ids_truncated"))
        or bool(current.get("child_job_ids_truncated"))
        or child_job_ref_count > len(child_job_ids)
    )
    child_run_ids_truncated = (
        bool(payload.get("child_run_ids_truncated"))
        or bool(current.get("child_run_ids_truncated"))
        or child_run_ref_count > len(child_run_ids)
    )
    validation_source = payload_validation if payload_validation else (current.get("validation") if isinstance(current.get("validation"), dict) else {})
    validation: dict[str, Any] = {}
    if isinstance(validation_source, dict) and validation_source:
        validation = {
            "status": str(validation_source.get("status") or "ok").strip() or "ok",
            "expected_format": str(validation_source.get("expected_format") or "").strip(),
            "errors": [
                str(item or "").strip()
                for item in (validation_source.get("errors") or [])
                if isinstance(item, str) and str(item or "").strip()
            ][:4],
        }
    completed_at = payload.get("completed_at") if "completed_at" in payload else current.get("completed_at")
    error = payload.get("error") if "error" in payload else current.get("error")
    return {
        "index": index,
        "node_id": str(payload.get("node_id") or current.get("node_id") or "").strip(),
        "node_kind": str(payload.get("node_kind") or current.get("node_kind") or "").strip(),
        "node_title": str(payload.get("node_title") or current.get("node_title") or payload.get("node_kind") or current.get("node_kind") or "").strip(),
        "executor": str(payload.get("executor") or current.get("executor") or "job").strip() or "job",
        "job_id": str(payload.get("job_id") or current.get("job_id") or "").strip(),
        "child_job_ids": child_job_ids,
        "child_run_ids": child_run_ids,
        "child_job_ref_count": child_job_ref_count,
        "child_run_ref_count": child_run_ref_count,
        "child_job_ids_truncated": child_job_ids_truncated,
        "child_run_ids_truncated": child_run_ids_truncated,
        "runtime_control": str(payload.get("runtime_control") or current.get("runtime_control") or "").strip(),
        "runtime_status": str(payload.get("runtime_status") or current.get("runtime_status") or "").strip(),
        "runtime_side_effect": str(payload.get("runtime_side_effect") or current.get("runtime_side_effect") or "").strip(),
        "agent_execution_id": str(payload.get("agent_execution_id") or current.get("agent_execution_id") or "").strip(),
        "output_key": str(payload.get("output_key") or current.get("output_key") or "").strip(),
        "artifact_count": safe_int(
            payload.get("artifact_count"),
            len(payload_artifacts) if payload_artifacts is not None else safe_int(current.get("artifact_count"), 0),
        ),
        "artifacts": normalize_workspace_run_step_artifacts(
            payload_artifacts if payload_artifacts is not None else None,
            current.get("artifacts") if isinstance(current.get("artifacts"), list) else [],
        ),
        "resources": normalize_workspace_run_step_resources(
            payload_resources if payload_resources is not None else None,
            current.get("resources") if isinstance(current.get("resources"), dict) else {},
        ),
        "mapped_inputs": [
            item for item in (payload_mapped_inputs if payload_mapped_inputs else (current.get("mapped_inputs") or []))
            if isinstance(item, dict)
        ][:6],
        "agent_steps": [
            item for item in (payload_agent_steps if payload_agent_steps else (current.get("agent_steps") or []))
            if isinstance(item, dict)
        ][:24],
        "trace_events": normalize_agent_trace_events(
            payload_trace_events if payload_trace_events is not None else (current.get("trace_events") or []),
        ),
        "validation": validation,
        "timed_out": bool(payload.get("timed_out")) if payload.get("timed_out") is not None else bool(current.get("timed_out")),
        "cancelled": bool(payload.get("cancelled")) if payload.get("cancelled") is not None else bool(current.get("cancelled")),
        "agent_meta": _normalize_agent_meta(payload.get("agent_meta"), current.get("agent_meta")),
        "status": status,
        "started_at": str(payload.get("started_at") or current.get("started_at") or "").strip(),
        "completed_at": str(completed_at or "").strip(),
        "error": str(error or "").strip(),
    }

def derive_workspace_execution_run_status(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "pending"
    statuses = [str(step.get("status") or "").strip() for step in steps]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "stopped" for status in statuses):
        return "stopped"
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
    stopped = sum(1 for step in steps if str(step.get("status") or "") == "stopped")
    failed = sum(1 for step in steps if str(step.get("status") or "") in {"failed", "blocked", "stopped"})
    running = sum(1 for step in steps if str(step.get("status") or "") == "running")
    queued = sum(1 for step in steps if str(step.get("status") or "") == "queued")
    percent = int((done / total) * 100) if total else 0
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "stopped": stopped,
        "running": running,
        "queued": queued,
        "percent": percent,
    }


def _workspace_delivery_path_candidates(path_text: str, workspace_dir: str = "") -> set[str]:
    text = str(path_text or "").strip()
    if not text:
        return set()
    root = os.path.normpath(os.path.expanduser(str(workspace_dir or "").strip())) if str(workspace_dir or "").strip() else ""
    values: set[str] = set()

    def add(value: str) -> None:
        candidate = str(value or "").strip()
        if not candidate:
            return
        trimmed = candidate.rstrip("/\\") or candidate
        normalized = os.path.normpath(os.path.expanduser(trimmed))
        for item in (candidate, trimmed, normalized):
            item_text = str(item or "").strip()
            if item_text and item_text != ".":
                values.add(item_text)

    add(text)
    normalized_text = os.path.normpath(os.path.expanduser(text.rstrip("/\\") or text))
    if root:
        if os.path.isabs(normalized_text):
            try:
                relative = os.path.relpath(normalized_text, root)
            except ValueError:
                relative = ""
            if relative and relative != "." and not relative.startswith(".."):
                add(relative)
                add("./" + relative)
        else:
            add(os.path.join(root, normalized_text))
    return values


def workspace_execution_run_delivery_closure(
    package_snapshot: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = package_snapshot.get("package_manifest") if isinstance(package_snapshot.get("package_manifest"), dict) else {}
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    commands = manifest.get("commands") if isinstance(manifest.get("commands"), dict) else {}
    target = package_snapshot.get("target") if isinstance(package_snapshot.get("target"), dict) else {}
    if not target and isinstance(manifest.get("target"), dict):
        target = manifest.get("target") or {}
    workspace_dir = str(target.get("workspace_dir") or "").strip()
    expected_artifact_paths = [
        str(item or "").strip()
        for item in (paths.get("artifact_paths") if isinstance(paths.get("artifact_paths"), list) else [])
        if str(item or "").strip()
    ][:12]
    expected_metric_paths = [
        str(item or "").strip()
        for item in (paths.get("metric_paths") if isinstance(paths.get("metric_paths"), list) else [])
        if str(item or "").strip()
    ][:12]
    observed_artifacts: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    report_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_kind = str(step.get("node_kind") or "").strip()
        if step_kind == "eval.report":
            report_steps.append(
                {
                    "node_id": str(step.get("node_id") or "").strip(),
                    "status": str(step.get("status") or "").strip(),
                    "job_id": str(step.get("job_id") or "").strip(),
                    "agent_execution_id": str(step.get("agent_execution_id") or "").strip(),
                }
            )
        for artifact in step.get("artifacts") if isinstance(step.get("artifacts"), list) else []:
            if isinstance(artifact, dict):
                observed_artifacts.append(
                    {
                        **artifact,
                        "node_id": str(artifact.get("node_id") or step.get("node_id") or "").strip(),
                        "node_kind": str(artifact.get("node_kind") or step_kind).strip(),
                    }
                )
        resources = step.get("resources") if isinstance(step.get("resources"), dict) else {}
        step_metrics = resources.get("metrics") if isinstance(resources.get("metrics"), dict) else {}
        for key, value in step_metrics.items():
            metrics[str(key)] = value
    observed_artifacts = normalize_workspace_run_step_artifacts(observed_artifacts)
    report_artifacts = [
        item for item in observed_artifacts
        if str(item.get("type") or "").strip() == "report"
        or str(item.get("node_kind") or "").strip() == "eval.report"
        or str(item.get("label") or "").strip().lower() in {"report", "eval_report", "evaluation_report"}
    ][:6]
    def artifact_is_observed(item: dict[str, Any]) -> bool:
        return bool(item.get("exists")) or str(item.get("status") or "") in {"found", "ready", "done"}

    found_count = sum(1 for item in observed_artifacts if artifact_is_observed(item))
    def expected_path_observed(path: str) -> bool:
        expected_candidates = _workspace_delivery_path_candidates(path, workspace_dir)
        return any(
            artifact_is_observed(item)
            and bool(
                expected_candidates
                & (
                    _workspace_delivery_path_candidates(str(item.get("path") or ""), workspace_dir)
                    | _workspace_delivery_path_candidates(str(item.get("resolved_path") or ""), workspace_dir)
                )
            )
            for item in observed_artifacts
        )

    missing_artifact_paths = [
        path for path in expected_artifact_paths
        if path and not expected_path_observed(path)
    ]
    missing_metric_paths = [
        path for path in expected_metric_paths
        if path and not expected_path_observed(path)
    ]
    missing_expected = [*missing_artifact_paths, *missing_metric_paths]
    report_command = str(commands.get("report_command") or "").strip()
    failed_report_steps = [
        item for item in report_steps
        if str(item.get("status") or "").strip() in {"failed", "blocked", "stopped"}
    ]
    completed_report_steps = [
        item for item in report_steps
        if str(item.get("status") or "").strip() == "done"
    ]
    report_ready = bool(report_artifacts or (metrics and completed_report_steps))
    if failed_report_steps:
        status = "failed"
    elif missing_expected:
        status = "warning"
    elif metrics and (found_count or completed_report_steps or report_artifacts):
        status = "done"
    elif found_count or metrics or report_artifacts or completed_report_steps:
        status = "ready"
    elif expected_artifact_paths or expected_metric_paths or report_command:
        status = "warning"
    else:
        status = "draft"
    if failed_report_steps:
        report_status = "failed"
    elif report_ready:
        report_status = "ready"
    elif report_command or report_steps or metrics:
        report_status = "warning"
    else:
        report_status = "draft"
    return {
        "status": status,
        "expected_artifact_paths": expected_artifact_paths,
        "expected_metric_paths": expected_metric_paths,
        "observed_artifacts": observed_artifacts[:24],
        "observed_count": len(observed_artifacts),
        "found_count": found_count,
        "missing_expected": missing_expected[:12],
        "missing_artifact_count": len(missing_artifact_paths),
        "missing_metric_count": len(missing_metric_paths),
        "metrics": metrics,
        "report": {
            "status": report_status,
            "report_command": report_command,
            "steps": report_steps[:6],
            "artifacts": copy.deepcopy(report_artifacts),
            "artifact_count": len(report_artifacts),
            "failed_steps": failed_report_steps[:6],
            "failed_step_count": len(failed_report_steps),
        },
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
    package_snapshot = payload.get("package_snapshot") if isinstance(payload.get("package_snapshot"), dict) else {}
    if not package_snapshot and isinstance(current.get("package_snapshot"), dict):
        package_snapshot = current.get("package_snapshot") or {}
    package_id = ""
    if isinstance(package_snapshot, dict):
        package_id = str(package_snapshot.get("package_id") or "").strip()
        if not package_id:
            manifest = package_snapshot.get("package_manifest")
            if isinstance(manifest, dict):
                package_id = str(manifest.get("package_id") or "").strip()
    if not package_id:
        package_id = str(payload.get("package_id") or current.get("package_id") or "").strip()
    if isinstance(package_snapshot, dict) and package_snapshot:
        package_snapshot = {
            **package_snapshot,
            "delivery_closure": workspace_execution_run_delivery_closure(package_snapshot, steps),
        }
    raw_events = payload.get("events") if isinstance(payload.get("events"), list) else current.get("events")
    events = normalize_workspace_run_events(raw_events)
    delta_evidence = normalize_workspace_run_delta_evidence(
        payload.get("delta_evidence") if isinstance(payload.get("delta_evidence"), dict) else current.get("delta_evidence")
    )
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
        "package_snapshot": copy.deepcopy(package_snapshot) if isinstance(package_snapshot, dict) else {},
        "package_id": package_id,
        "events": events,
        "delta_evidence": delta_evidence,
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


def filter_workspace_execution_runs(
    runs: list[dict[str, Any]],
    *,
    status: str = "",
    node_kind: str = "",
    job_id: str = "",
    agent_execution_id: str = "",
    created_after: str = "",
    created_before: str = "",
) -> list[dict[str, Any]]:
    # 按状态、节点类型、任务、Agent 执行 id 或时间范围过滤运行记录。
    filtered = [run for run in runs if isinstance(run, dict)]
    status_filter = str(status or "").strip().lower()
    if status_filter:
        filtered = [run for run in filtered if str(run.get("status") or "").strip().lower() == status_filter]
    after_ts = parse_iso_timestamp(created_after)
    before_ts = parse_iso_timestamp(created_before)
    if after_ts or before_ts:
        def run_ts(run: dict[str, Any]) -> float:
            return (
                parse_iso_timestamp(run.get("created_at"))
                or parse_iso_timestamp(run.get("started_at"))
                or parse_iso_timestamp(run.get("updated_at"))
                or parse_iso_timestamp(run.get("completed_at"))
            )

        if after_ts:
            filtered = [run for run in filtered if run_ts(run) >= after_ts]
        if before_ts:
            filtered = [run for run in filtered if run_ts(run) <= before_ts]
    node_kind_filter = str(node_kind or "").strip()
    if node_kind_filter:
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict) and str(step.get("node_kind") or "").strip() == node_kind_filter
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    job_id_filter = str(job_id or "").strip()
    if job_id_filter:
        job_id_filter_lower = job_id_filter.lower()
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict)
                and any(job_id_filter_lower in item.lower() for item in workspace_run_step_job_ids(step))
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    agent_filter = str(agent_execution_id or "").strip()
    if agent_filter:
        agent_filter_lower = agent_filter.lower()
        filtered = [
            run for run in filtered
            if any(
                isinstance(step, dict)
                and any(agent_filter_lower in item.lower() for item in workspace_run_step_agent_execution_ids(step))
                for step in (run.get("steps") if isinstance(run.get("steps"), list) else [])
            )
        ]
    return filtered


def workspace_execution_run_compare_payload(
    workspace: dict[str, Any],
    base_run: dict[str, Any],
    target_run: dict[str, Any],
    *,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = workspace_execution_run_replay_payload(workspace, base_run, jobs=jobs)
    target = workspace_execution_run_replay_payload(workspace, target_run, jobs=jobs)

    def metric(replay: dict[str, Any]) -> dict[str, Any]:
        timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
        linked_runs = replay.get("linked_runs") if isinstance(replay.get("linked_runs"), list) else []
        linked_timeline = [
            step
            for item in linked_runs
            if isinstance(item, dict) and isinstance(item.get("timeline"), list)
            for step in item.get("timeline", [])
        ]
        all_timeline = [*timeline, *linked_timeline]
        linked_jobs = replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []
        delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
        node_keys = [
            (
                f"{str(step.get('run_id') or '').strip()}:"
                f"{str(step.get('node_kind') or '').strip()}:"
                f"{str(step.get('node_id') or '').strip()}"
            )
            for step in all_timeline
            if isinstance(step, dict)
        ]
        status_counts: dict[str, int] = {}
        executor_counts: dict[str, int] = {}
        for step in all_timeline:
            if not isinstance(step, dict):
                continue
            status = str(step.get("status") or "unknown").strip() or "unknown"
            executor = str(step.get("executor") or "unknown").strip() or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            executor_counts[executor] = executor_counts.get(executor, 0) + 1
        return {
            "run_id": str(replay.get("run", {}).get("id") if isinstance(replay.get("run"), dict) else "").strip(),
            "status": str(replay.get("run", {}).get("status") if isinstance(replay.get("run"), dict) else "").strip(),
            "package_id": str(replay.get("run", {}).get("package_id") if isinstance(replay.get("run"), dict) else "").strip(),
            "step_count": len(all_timeline),
            "linked_run_count": len(linked_runs),
            "job_count": len(linked_jobs),
            "agent_count": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "failed_step_count": sum(1 for step in all_timeline if isinstance(step, dict) and str(step.get("status") or "") in {"failed", "blocked", "stopped"}),
            "artifact_count": sum(safe_int(step.get("artifact_count"), 0) for step in all_timeline if isinstance(step, dict)),
            "trace_event_count": sum(safe_int(step.get("trace_event_count"), 0) for step in all_timeline if isinstance(step, dict)),
            "delivery_status": str(delivery.get("status") or "").strip(),
            "node_keys": node_keys,
            "status_counts": status_counts,
            "executor_counts": executor_counts,
        }

    base_metric = metric(base)
    target_metric = metric(target)
    base_nodes = set(base_metric["node_keys"])
    target_nodes = set(target_metric["node_keys"])

    numeric_keys = (
        "step_count",
        "linked_run_count",
        "job_count",
        "agent_count",
        "failed_step_count",
        "artifact_count",
        "trace_event_count",
    )
    metric_delta = {
        key: safe_int(target_metric.get(key), 0) - safe_int(base_metric.get(key), 0)
        for key in numeric_keys
    }
    changes = []
    for key, label in (
        ("status", "运行状态"),
        ("package_id", "执行包"),
        ("delivery_status", "交付闭环"),
    ):
        if str(base_metric.get(key) or "") != str(target_metric.get(key) or ""):
            changes.append(
                {
                    "field": key,
                    "label": label,
                    "base": str(base_metric.get(key) or ""),
                    "target": str(target_metric.get(key) or ""),
                }
            )
    for key, delta in metric_delta.items():
        if delta:
            changes.append(
                {
                    "field": key,
                    "label": key,
                    "base": safe_int(base_metric.get(key), 0),
                    "target": safe_int(target_metric.get(key), 0),
                    "delta": delta,
                }
            )

    return {
        "schema": "relaygraph.run.compare.v1",
        "exported_at": now_iso(),
        "workspace": copy.deepcopy(base.get("workspace") if isinstance(base.get("workspace"), dict) else {}),
        "base": {
            "run": copy.deepcopy(base.get("run") if isinstance(base.get("run"), dict) else {}),
            "metrics": base_metric,
        },
        "target": {
            "run": copy.deepcopy(target.get("run") if isinstance(target.get("run"), dict) else {}),
            "metrics": target_metric,
        },
        "diff": {
            "metric_delta": metric_delta,
            "added_nodes": sorted(target_nodes - base_nodes),
            "removed_nodes": sorted(base_nodes - target_nodes),
            "common_node_count": len(base_nodes & target_nodes),
            "changes": changes,
        },
    }

def workspace_run_export_manifest(
    replay: dict[str, Any],
    *,
    logs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
    event_timeline = replay.get("event_timeline") if isinstance(replay.get("event_timeline"), list) else []
    linked_runs = replay.get("linked_runs") if isinstance(replay.get("linked_runs"), list) else []
    linked_timeline_steps = sum(
        len(item.get("timeline")) for item in linked_runs if isinstance(item, dict) and isinstance(item.get("timeline"), list)
    )
    linked_event_count = sum(
        len(item.get("event_timeline"))
        for item in linked_runs
        if isinstance(item, dict) and isinstance(item.get("event_timeline"), list)
    )
    delta_evidence = replay.get("delta_evidence") if isinstance(replay.get("delta_evidence"), dict) else {}
    linked_delta_event_count = sum(
        safe_int(item.get("delta_evidence", {}).get("total_events"), 0)
        for item in linked_runs
        if isinstance(item, dict) and isinstance(item.get("delta_evidence"), dict)
    )
    all_timeline = [
        *timeline,
        *[
            step
            for item in linked_runs
            if isinstance(item, dict) and isinstance(item.get("timeline"), list)
            for step in item.get("timeline", [])
        ],
    ]
    run = replay.get("run") if isinstance(replay.get("run"), dict) else {}
    linked_run_closure = replay.get("linked_run_closure") if isinstance(replay.get("linked_run_closure"), dict) else {}
    delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
    package_snapshot = replay.get("package_snapshot") if isinstance(replay.get("package_snapshot"), dict) else {}
    package_manifest = package_snapshot.get("package_manifest") if isinstance(package_snapshot.get("package_manifest"), dict) else {}
    commands = package_manifest.get("commands") if isinstance(package_manifest.get("commands"), dict) else {}
    failed_steps = [
        {
            "index": safe_int(step.get("index"), 0),
            "node_id": str(step.get("node_id") or "").strip(),
            "node_kind": str(step.get("node_kind") or "").strip(),
            "status": str(step.get("status") or "").strip(),
            "error": str(step.get("error") or "").strip(),
        }
        for step in all_timeline
        if isinstance(step, dict) and str(step.get("status") or "").strip() in {"failed", "blocked", "stopped"}
    ]
    status_counts: dict[str, int] = {}
    executor_counts: dict[str, int] = {}
    for step in all_timeline:
        if not isinstance(step, dict):
            continue
        status = str(step.get("status") or "unknown").strip() or "unknown"
        executor = str(step.get("executor") or "unknown").strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        executor_counts[executor] = executor_counts.get(executor, 0) + 1
    truncated_logs = [item for item in logs if isinstance(item, dict) and bool(item.get("truncated"))]
    omitted_log_bytes = sum(safe_int(item.get("skipped_bytes"), 0) for item in truncated_logs)
    return {
        "schema": "relaygraph.run.export.manifest.v1",
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("status") or "").strip(),
        "package_id": str(run.get("package_id") or package_snapshot.get("package_id") or "").strip(),
        "delivery_status": str(delivery.get("status") or "").strip(),
        "status_counts": status_counts,
        "executor_counts": executor_counts,
        "failed_steps": failed_steps[:12],
        "commands": {
            "checkout": str(commands.get("checkout_command") or "").strip(),
            "setup": str(commands.get("setup_command") or "").strip(),
            "run": str(commands.get("run_command") or "").strip(),
            "collect": str(commands.get("collect_command") or "").strip(),
            "report": str(commands.get("report_command") or "").strip(),
        },
        "included": {
            "timeline_steps": len(timeline),
            "event_timeline": len(event_timeline),
            "delta_evidence_events": safe_int(delta_evidence.get("total_events"), 0),
            "linked_runs": len(linked_runs),
            "linked_runs_truncated": bool(linked_run_closure.get("truncated")),
            "linked_timeline_steps": linked_timeline_steps,
            "linked_event_timeline": linked_event_count,
            "linked_delta_evidence_events": linked_delta_event_count,
            "linked_jobs": len(replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []),
            "agent_executions": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "logs_returned": len(logs),
            "logs_truncated": len(truncated_logs),
            "artifacts_returned": len(artifacts),
            "reports_returned": len(reports),
        },
        "limits": {
            "logs": 12,
            "log_tail_bytes_each": 12000,
            "log_read_bytes_each": 24000,
            "log_tail_lines_each": 80,
            "artifacts": 48,
            "reports": 12,
            "child_refs_per_step": WORKSPACE_RUN_CHILD_REF_MAX,
            "linked_runs": safe_int(linked_run_closure.get("limit"), WORKSPACE_LINKED_RUN_CLOSURE_MAX),
            "delta_evidence_recent_per_run": WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX,
        },
        "truncation": {
            "linked_runs": bool(linked_run_closure.get("truncated")),
            "linked_run_pending_count": safe_int(linked_run_closure.get("pending_count"), 0),
            "missing_linked_run_count": safe_int(linked_run_closure.get("missing_count"), 0),
            "log_tails": len(truncated_logs),
            "omitted_log_bytes": omitted_log_bytes,
            "delta_evidence_truncated_events": safe_int(delta_evidence.get("truncated_events"), 0)
            + sum(
                safe_int(item.get("delta_evidence", {}).get("truncated_events"), 0)
                for item in linked_runs
                if isinstance(item, dict) and isinstance(item.get("delta_evidence"), dict)
            ),
            "delta_evidence_omitted_content": bool(
                safe_int(delta_evidence.get("total_events"), 0) or linked_delta_event_count
            ),
            "child_ref_steps": sum(
                1
                for step in all_timeline
                if isinstance(step, dict)
                and (bool(step.get("child_job_ids_truncated")) or bool(step.get("child_run_ids_truncated")))
            ),
        },
    }

def workspace_run_export_readme(manifest: dict[str, Any]) -> str:
    included = manifest.get("included") if isinstance(manifest.get("included"), dict) else {}
    failed_steps = manifest.get("failed_steps") if isinstance(manifest.get("failed_steps"), list) else []
    commands = manifest.get("commands") if isinstance(manifest.get("commands"), dict) else {}
    truncation = manifest.get("truncation") if isinstance(manifest.get("truncation"), dict) else {}
    lines = [
        "# RelayGraph Run Export",
        "",
        f"- Run: {str(manifest.get('run_id') or '').strip() or 'unknown'}",
        f"- Status: {str(manifest.get('run_status') or '').strip() or 'unknown'}",
        f"- Package: {str(manifest.get('package_id') or '').strip() or 'none'}",
        f"- Delivery: {str(manifest.get('delivery_status') or '').strip() or 'unknown'}",
        f"- Steps: {safe_int(included.get('timeline_steps'), 0)}",
        f"- Events: {safe_int(included.get('event_timeline'), 0)}",
        f"- Realtime delta evidence: {safe_int(included.get('delta_evidence_events'), 0)} summary-only events",
        f"- Linked runs: {safe_int(included.get('linked_runs'), 0)}",
        f"- Linked jobs: {safe_int(included.get('linked_jobs'), 0)}",
        f"- Logs included: {safe_int(included.get('logs_returned'), 0)}",
        f"- Artifacts included: {safe_int(included.get('artifacts_returned'), 0)}",
        f"- Reports included: {safe_int(included.get('reports_returned'), 0)}",
        "",
        "## Commands",
    ]
    if truncation and any(bool(value) for value in truncation.values()):
        lines[-1:] = [
            "## Truncation",
            "",
            f"- Linked runs truncated: {bool(truncation.get('linked_runs'))}",
            f"- Pending linked runs beyond limit: {safe_int(truncation.get('linked_run_pending_count'), 0)}",
            f"- Missing linked run references: {safe_int(truncation.get('missing_linked_run_count'), 0)}",
            f"- Logs with truncated tails: {safe_int(truncation.get('log_tails'), 0)}",
            f"- Omitted log bytes before included tails: {safe_int(truncation.get('omitted_log_bytes'), 0)}",
            f"- Realtime delta content omitted: {bool(truncation.get('delta_evidence_omitted_content'))}",
            f"- Realtime delta events with skipped content: {safe_int(truncation.get('delta_evidence_truncated_events'), 0)}",
            f"- Steps with truncated child refs: {safe_int(truncation.get('child_ref_steps'), 0)}",
            "",
            "## Commands",
        ]
    command_count = 0
    for key in ("checkout", "setup", "run", "collect", "report"):
        command = str(commands.get(key) or "").strip()
        if command:
            command_count += 1
            lines.append(f"- {key}: `{command}`")
    if command_count == 0:
        lines.append("- No package commands were recorded.")
    lines.extend(["", "## Triage"])
    if failed_steps:
        lines.append("- Failed or stopped steps:")
        for step in failed_steps[:8]:
            label = str(step.get("node_kind") or step.get("node_id") or "step").strip()
            status = str(step.get("status") or "").strip()
            error = str(step.get("error") or "").strip()
            lines.append(f"  - #{safe_int(step.get('index'), 0) + 1} {label}: {status}{' - ' + error if error else ''}")
    else:
        lines.append("- No failed, blocked, or stopped steps were recorded.")
    lines.append("- Use `replay.timeline` for ordered step history, `replay.event_timeline` for persisted runtime events, `replay.delta_evidence` for summary-only realtime stream coverage, and `logs[].tail` for cached job output.")
    return "\n".join(lines).strip() + "\n"


def workspace_execution_run_export_payload(
    workspace: dict[str, Any],
    run: dict[str, Any],
    *,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    replay = workspace_execution_run_replay_payload(workspace, run, jobs=jobs)
    timeline = replay.get("timeline") if isinstance(replay.get("timeline"), list) else []
    event_timeline = replay.get("event_timeline") if isinstance(replay.get("event_timeline"), list) else []
    workspace_payload = replay.get("workspace") if isinstance(replay.get("workspace"), dict) else {}
    workspace_id = str(workspace_payload.get("id") or "").strip()
    linked_runs = workspace_execution_run_linked_runs(workspace, run)
    source_runs = [run, *linked_runs]
    job_index = workspace_jobs_for_run(workspace_id, run, jobs, linked_runs=linked_runs)
    log_items: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    seen_log_job_ids: set[str] = set()
    for source_run in source_runs:
        source_run_id = str(source_run.get("id") or "").strip()
        source_steps = [step for step in (source_run.get("steps") if isinstance(source_run.get("steps"), list) else []) if isinstance(step, dict)]
        source_timeline = workspace_execution_run_timeline(source_run)
        for step_index, step in enumerate(source_timeline):
            if not isinstance(step, dict):
                continue
            source_step = next(
                (
                    item for item in source_steps
                    if safe_int(item.get("index"), -1) == safe_int(step.get("index"), -2)
                    and str(item.get("node_id") or "").strip() == str(step.get("node_id") or "").strip()
                ),
                source_steps[step_index] if step_index < len(source_steps) else {},
            )
            for job_id in workspace_run_step_job_ids(step):
                job = job_index.get(job_id)
                if not job or job_id in seen_log_job_ids:
                    continue
                log_payload = workspace_job_cached_log_tail_payload(
                    job,
                    max_lines=80,
                    max_bytes=24000,
                    tail_chars=12000,
                )
                log_text = str(log_payload.get("tail") or "")
                if not log_text:
                    continue
                seen_log_job_ids.add(job_id)
                tail_source = str(log_payload.get("tail_source") or "snapshot").strip() or "snapshot"
                display_log_path = str(log_payload.get("display_log_path") or "").strip()
                if not display_log_path:
                    display_log_path = runtime_log_display_path(log_payload.get("log_path") or job.get("log_path"))
                log_items.append(
                    {
                        "run_id": source_run_id,
                        "job_id": job_id,
                        "node_id": str(step.get("node_id") or "").strip(),
                        "node_kind": str(step.get("node_kind") or "").strip(),
                        "status": str(job.get("status") or step.get("status") or "").strip(),
                        "log_path": display_log_path,
                        "display_log_path": display_log_path,
                        "remote_log_path": remote_runtime_log_display_path(log_payload.get("remote_log_path") or job.get("remote_log_path")),
                        "tail_source": tail_source,
                        "snapshot_captured_at": str(log_payload.get("snapshot_captured_at") or "").strip() if tail_source == "snapshot" else "",
                        "file_size": safe_int(log_payload.get("file_size"), 0),
                        "read_bytes": safe_int(log_payload.get("read_bytes"), 0),
                        "tail_bytes": safe_int(log_payload.get("tail_bytes"), len(log_text.encode("utf-8", errors="replace"))),
                        "skipped_bytes": safe_int(log_payload.get("skipped_bytes"), 0),
                        "line_count": safe_int(log_payload.get("line_count"), len(log_text.splitlines())),
                        "truncated": bool(log_payload.get("truncated")),
                        "truncation_reasons": list(log_payload.get("truncation_reasons") if isinstance(log_payload.get("truncation_reasons"), list) else []),
                        "tail": log_text,
                    }
                )
            for artifact in source_step.get("artifacts") if isinstance(source_step.get("artifacts"), list) else []:
                if not isinstance(artifact, dict):
                    continue
                item = copy.deepcopy(artifact)
                item.setdefault("run_id", source_run_id)
                item.setdefault("node_id", str(step.get("node_id") or "").strip())
                item.setdefault("node_kind", str(step.get("node_kind") or "").strip())
                artifacts.append(item)
                artifact_type = str(item.get("type") or "").strip()
                label = str(item.get("label") or "").strip().lower()
                if artifact_type == "report" or label in {"report", "eval_report", "evaluation_report"}:
                    reports.append(copy.deepcopy(item))

        source_package = source_run.get("package_snapshot") if isinstance(source_run.get("package_snapshot"), dict) else {}
        source_delivery = source_package.get("delivery_closure") if isinstance(source_package.get("delivery_closure"), dict) else {}
        report_payload = source_delivery.get("report") if isinstance(source_delivery.get("report"), dict) else {}
        for report in report_payload.get("artifacts") if isinstance(report_payload.get("artifacts"), list) else []:
            if isinstance(report, dict):
                item = copy.deepcopy(report)
                item.setdefault("run_id", source_run_id)
                reports.append(item)

    artifacts = workspace_dedupe_artifacts(artifacts)[:48]
    reports = reports[:12]
    log_items = log_items[:12]
    manifest = workspace_run_export_manifest(replay, logs=log_items, artifacts=artifacts, reports=reports)
    readme = workspace_run_export_readme(manifest)
    run_payload = replay.get("run") if isinstance(replay.get("run"), dict) else {}
    delivery = replay.get("delivery_closure") if isinstance(replay.get("delivery_closure"), dict) else {}
    run_id = str(run_payload.get("id") or "").strip()
    package_id = str(run_payload.get("package_id") or "").strip()
    filename_bits = [workspace_id or "workspace", run_id or "run", package_id or "export"]
    filename = "relaygraph-run-" + "-".join(safe_id(bit) for bit in filename_bits if bit) + ".json"
    return {
        "schema": "relaygraph.run.export.v1",
        "exported_at": now_iso(),
        "filename": filename,
        "workspace": copy.deepcopy(workspace_payload),
        "run": copy.deepcopy(run_payload),
        "summary": {
            "step_count": len(timeline),
            "linked_run_count": len(linked_runs),
            "linked_step_count": sum(
                len(workspace_execution_run_timeline(linked_run))
                for linked_run in linked_runs
                if isinstance(linked_run, dict)
            ),
            "linked_job_count": len(replay.get("linked_jobs") if isinstance(replay.get("linked_jobs"), list) else []),
            "agent_execution_count": len(replay.get("agent_execution_ids") if isinstance(replay.get("agent_execution_ids"), list) else []),
            "event_count": len(event_timeline),
            "artifact_count": len(artifacts),
            "report_count": len(reports),
            "log_count": len(log_items),
            "delivery_status": str(delivery.get("status") or "").strip(),
        },
        "manifest": manifest,
        "readme_markdown": readme,
        "replay": replay,
        "logs": log_items,
        "artifacts": artifacts,
        "reports": reports,
    }

def workspace_run_step_from_job(job: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    artifacts = workspace_run_step_artifacts_from_job(job)
    resources = workspace_run_step_resources_from_job(job)
    return normalize_workspace_run_step(
        {
            "index": index,
            "node_id": str(metadata.get("node_id") or "").strip(),
            "node_kind": str(metadata.get("node_kind") or "").strip(),
            "node_title": str(metadata.get("node_title") or metadata.get("node_kind") or "").strip(),
            "executor": "job",
            "job_id": str(job.get("id") or "").strip(),
            "status": workspace_run_step_status_from_job(job),
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "resources": resources,
            "started_at": str(job.get("started_at") or "").strip(),
            "completed_at": str(job.get("finished_at") or "").strip(),
            "error": str(job.get("error") or "").strip(),
        }
    )

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

def workspace_run_step_from_agent(
    node: dict[str, Any],
    step_result: StepResult | dict[str, Any],
    index: int,
) -> dict[str, Any]:
    payload = step_result.as_dict() if isinstance(step_result, StepResult) else step_result
    raw_status = str(payload.get("status") or "").strip()
    if payload.get("skipped"):
        step_status = "blocked"
    elif payload.get("cancelled"):
        step_status = "stopped"
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
    trace_events = payload.get("trace_events") if isinstance(payload.get("trace_events"), list) else []
    runtime_refs = workspace_agent_runtime_refs(agent_steps, trace_events)
    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    timed_out = bool(payload.get("timed_out"))
    cancelled = bool(payload.get("cancelled"))
    raw_meta = payload.get("agent_meta") if isinstance(payload.get("agent_meta"), dict) else {}
    agent_meta = {
        "model": str(raw_meta.get("model") or "").strip(),
        "total_tokens": safe_int(raw_meta.get("total_tokens"), 0),
        "execution_time_ms": round(float(raw_meta.get("execution_time_ms") or 0), 1),
        "max_iterations": safe_int(raw_meta.get("max_iterations"), 0),
    } if raw_meta else {}
    return normalize_workspace_run_step(
        {
            "index": index,
            "node_id": str(node.get("id") or "").strip(),
            "node_kind": str(node.get("kind") or "").strip(),
            "node_title": str(node.get("title") or node.get("kind") or "").strip(),
            "executor": "agent",
            "child_job_ids": runtime_refs.get("child_job_ids", []),
            "child_run_ids": runtime_refs.get("child_run_ids", []),
            "child_job_ref_count": runtime_refs.get("child_job_ref_count", 0),
            "child_run_ref_count": runtime_refs.get("child_run_ref_count", 0),
            "child_job_ids_truncated": runtime_refs.get("child_job_ids_truncated", False),
            "child_run_ids_truncated": runtime_refs.get("child_run_ids_truncated", False),
            "runtime_control": runtime_refs.get("runtime_control", ""),
            "runtime_status": runtime_refs.get("runtime_status", ""),
            "runtime_side_effect": runtime_refs.get("runtime_side_effect", ""),
            "agent_execution_id": str(payload.get("agent_execution_id") or "").strip(),
            "output_key": str(payload.get("output_key") or "").strip(),
            "artifact_count": len([item for item in artifacts if isinstance(item, dict)]),
            "artifacts": [item for item in artifacts if isinstance(item, dict)][:24],
            "resources": payload.get("resources") if isinstance(payload.get("resources"), dict) else {},
            "mapped_inputs": [item for item in mapped_inputs if isinstance(item, dict)][:6],
            "agent_steps": [item for item in agent_steps if isinstance(item, dict)][:24],
            "trace_events": normalize_agent_trace_events(trace_events),
            "validation": validation,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "agent_meta": agent_meta,
            "status": step_status,
            "started_at": timestamp,
            "completed_at": timestamp,
            "error": str(payload.get("reason") or payload.get("detail") or "").strip(),
        }
    )

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

def workspace_execution_run_snapshot(run: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    steps = run.get("steps") if isinstance(run.get("steps"), list) else []
    return (
        str(run.get("status") or ""),
        tuple(
            (
                str(step.get("status") or ""),
                str(step.get("error") or ""),
                str(step.get("artifact_count") or ""),
                json.dumps(step.get("artifacts") if isinstance(step.get("artifacts"), list) else [], sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("resources") if isinstance(step.get("resources"), dict) else {}, sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("child_job_ids") if isinstance(step.get("child_job_ids"), list) else [], sort_keys=True, ensure_ascii=True),
                json.dumps(step.get("child_run_ids") if isinstance(step.get("child_run_ids"), list) else [], sort_keys=True, ensure_ascii=True),
                str(step.get("runtime_control") or ""),
                str(step.get("runtime_status") or ""),
                str(step.get("runtime_side_effect") or ""),
                str(step.get("started_at") or ""),
                str(step.get("completed_at") or ""),
            )
            for step in steps
            if isinstance(step, dict)
        ),
    )
