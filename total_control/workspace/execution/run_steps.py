"""Execution run step normalization and construction helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from ...orchestration.types import StepResult
from .agent_trace import normalize_agent_trace_events
from .log_parser import (
    parse_workspace_artifacts_from_log,
    parse_workspace_metrics_from_log,
    parse_workspace_resources_from_log,
)
from .paths import workspace_job_cached_log_tail
from .run_artifacts import normalize_workspace_run_step_artifacts
from .run_refs import WORKSPACE_RUN_CHILD_REF_MAX, _unique_run_ref_list


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
