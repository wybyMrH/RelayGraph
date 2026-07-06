"""Execution run event normalization and delta evidence helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403


def _compact_run_event_text(value: Any, limit: int = 800) -> str:
    text = str(value or "").strip()
    if limit <= 0:
        return ""
    return text[:limit]


def _compact_run_event_payload(payload: Any, *, event_type: str = "") -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    is_delta_event = str(event_type or "").strip().endswith(".delta")
    compact: dict[str, Any] = {}
    for key in (
        "node_id",
        "node_kind",
        "workspace_id",
        "agent_id",
        "chat",
        "at",
        "job_id",
        "run_id",
        "agent_execution_id",
        "tool_id",
        "step_number",
        "status",
        "side_effect",
        "controlled",
        "runtime_control",
        "runtime_side_effect",
        "runtime_status",
        "byte_count",
        "line_count",
        "truncated",
        "skipped_bytes",
        "final",
    ):
        if key in source:
            compact[key] = copy.deepcopy(source.get(key))
    if source.get("arguments_summary") is not None:
        compact["arguments_summary"] = _compact_run_event_text(source.get("arguments_summary"), 500)
    if source.get("observation_summary") is not None:
        compact["observation_summary"] = _compact_run_event_text(source.get("observation_summary"), 1000)
    if source.get("error") is not None:
        compact["error"] = _compact_run_event_text(source.get("error"), 500)
    if is_delta_event:
        compact["content_retention"] = "summary_only"
        compact["content"] = "omitted"
    elif source.get("delta") is not None:
        compact["delta"] = _compact_run_event_text(source.get("delta"), 500)
    if not is_delta_event and source.get("accumulated") is not None:
        compact["accumulated"] = _compact_run_event_text(source.get("accumulated"), 2000)

    run = source.get("run") if isinstance(source.get("run"), dict) else {}
    if run:
        compact["run"] = {
            "id": str(run.get("id") or "").strip(),
            "kind": str(run.get("kind") or "").strip(),
            "status": str(run.get("status") or "").strip(),
            "summary": _compact_run_event_text(run.get("summary"), 240),
            "progress": copy.deepcopy(run.get("progress") if isinstance(run.get("progress"), dict) else {}),
            "updated_at": str(run.get("updated_at") or "").strip(),
        }

    step = source.get("step") if isinstance(source.get("step"), dict) else {}
    if step:
        compact["step"] = {
            "index": safe_int(step.get("index"), 0),
            "node_id": str(step.get("node_id") or "").strip(),
            "node_kind": str(step.get("node_kind") or "").strip(),
            "node_title": str(step.get("node_title") or "").strip(),
            "executor": str(step.get("executor") or "").strip(),
            "status": str(step.get("status") or "").strip(),
            "job_id": str(step.get("job_id") or "").strip(),
            "agent_execution_id": str(step.get("agent_execution_id") or "").strip(),
            "error": _compact_run_event_text(step.get("error"), 500),
        }

    job = source.get("job") if isinstance(source.get("job"), dict) else {}
    if job:
        compact["job"] = {
            "id": str(job.get("id") or "").strip(),
            "status": str(job.get("status") or "").strip(),
            "server_id": str(job.get("server_id") or "").strip(),
            "queue_rank": safe_int(job.get("queue_rank"), 0),
            "started_at": str(job.get("started_at") or "").strip(),
            "finished_at": str(job.get("finished_at") or "").strip(),
            "error": _compact_run_event_text(job.get("error"), 500),
        }

    execution = source.get("execution") if isinstance(source.get("execution"), dict) else {}
    if execution:
        compact["execution"] = {
            "id": str(execution.get("id") or "").strip(),
            "success": bool(execution.get("success")),
            "model": str(execution.get("model") or "").strip(),
            "total_tokens": safe_int(execution.get("total_tokens"), 0),
            "total_steps": safe_int(execution.get("total_steps"), 0),
            "error": _compact_run_event_text(execution.get("error"), 500),
            "final_answer": _compact_run_event_text(execution.get("final_answer"), 1000),
        }

    if source.get("message") and isinstance(source.get("message"), dict):
        message = source["message"]
        compact["message"] = {
            "id": str(message.get("id") or "").strip(),
            "role": str(message.get("role") or "").strip(),
            "status": str(message.get("status") or "").strip(),
        }
        if not is_delta_event:
            compact["message"]["text"] = _compact_run_event_text(message.get("text"), 1000)
    return compact


def normalize_workspace_run_event(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {}
    event_type = str(payload.get("type") or "message").strip() or "message"
    compact_payload = _compact_run_event_payload(payload.get("payload"), event_type=event_type)
    workspace_id = str(payload.get("workspace_id") or compact_payload.get("workspace_id") or "").strip()
    run_id = str(payload.get("run_id") or compact_payload.get("run_id") or "").strip()
    if not workspace_id or not run_id:
        return {}
    return {
        "sse_id": safe_int(payload.get("sse_id"), safe_int(payload.get("id"), 0)),
        "type": event_type,
        "workspace_id": workspace_id,
        "run_id": run_id,
        "job_id": str(payload.get("job_id") or compact_payload.get("job_id") or "").strip(),
        "agent_execution_id": str(payload.get("agent_execution_id") or compact_payload.get("agent_execution_id") or "").strip(),
        "created_at": str(payload.get("created_at") or now_iso()).strip() or now_iso(),
        "payload": compact_payload,
    }


def normalize_workspace_run_events(
    value: Any,
    *,
    limit: int = WORKSPACE_RUN_EVENT_MAX,
) -> list[dict[str, Any]]:
    raw_events = value if isinstance(value, list) else []
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        event = normalize_workspace_run_event(item)
        if not event:
            continue
        sse_id = safe_int(event.get("sse_id"), 0)
        if sse_id > 0:
            key = f"sse:{sse_id}"
        else:
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            step = payload.get("step") if isinstance(payload.get("step"), dict) else {}
            job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
            execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else {}
            key = "|".join(
                [
                    str(event.get("type") or ""),
                    str(event.get("run_id") or ""),
                    str(event.get("job_id") or ""),
                    str(event.get("agent_execution_id") or execution.get("id") or ""),
                    str(step.get("index") if step.get("index") is not None else ""),
                    str(step.get("status") or ""),
                    str(job.get("status") or ""),
                    str(event.get("created_at") or ""),
                ]
            )
        if key in seen:
            continue
        seen.add(key)
        events.append(event)
    return events[-max(limit, 1):]


def _workspace_delta_event_text(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "job.log.delta":
        return str(payload.get("log") or "")
    delta = str(payload.get("delta") or "")
    if delta:
        return delta
    return str(payload.get("accumulated") or "")


def _workspace_delta_evidence_id_list(value: Any, *, limit: int = 24) -> list[str]:
    raw_items = value if isinstance(value, list) else []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def normalize_workspace_run_delta_evidence(value: Any) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    by_type_source = data.get("by_type") if isinstance(data.get("by_type"), dict) else {}
    by_type: dict[str, dict[str, Any]] = {}
    for event_type, item in by_type_source.items():
        event_key = str(event_type or "").strip()
        if not event_key:
            continue
        source = item if isinstance(item, dict) else {}
        by_type[event_key] = {
            "event_count": safe_int(source.get("event_count"), 0),
            "byte_count": safe_int(source.get("byte_count"), 0),
            "line_count": safe_int(source.get("line_count"), 0),
            "truncated_count": safe_int(source.get("truncated_count"), 0),
            "skipped_bytes": safe_int(source.get("skipped_bytes"), 0),
            "last_at": str(source.get("last_at") or "").strip(),
        }
    recent: list[dict[str, Any]] = []
    for item in data.get("recent") if isinstance(data.get("recent"), list) else []:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or "").strip()
        if not event_type:
            continue
        recent.append(
            {
                "type": event_type,
                "created_at": str(item.get("created_at") or "").strip(),
                "job_id": str(item.get("job_id") or "").strip(),
                "agent_execution_id": str(item.get("agent_execution_id") or "").strip(),
                "byte_count": safe_int(item.get("byte_count"), 0),
                "line_count": safe_int(item.get("line_count"), 0),
                "truncated": bool(item.get("truncated")),
                "skipped_bytes": safe_int(item.get("skipped_bytes"), 0),
                "content": "omitted",
            }
        )
    recent = recent[-WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX:]
    return {
        "schema": "relaygraph.run.delta_evidence.v1",
        "content_retention": "summary_only",
        "total_events": safe_int(data.get("total_events"), 0),
        "total_bytes": safe_int(data.get("total_bytes"), 0),
        "total_lines": safe_int(data.get("total_lines"), 0),
        "truncated_events": safe_int(data.get("truncated_events"), 0),
        "skipped_bytes": safe_int(data.get("skipped_bytes"), 0),
        "event_types": sorted(by_type),
        "job_ids": _workspace_delta_evidence_id_list(data.get("job_ids")),
        "agent_execution_ids": _workspace_delta_evidence_id_list(data.get("agent_execution_ids")),
        "by_type": by_type,
        "recent": recent,
        "updated_at": str(data.get("updated_at") or "").strip(),
    }


def workspace_run_delta_evidence_from_event(current: Any, event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("type") or "").strip()
    if not event_type.endswith(".delta"):
        return normalize_workspace_run_delta_evidence(current)
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    text = _workspace_delta_event_text(event_type, payload)
    fallback_byte_count = len(text.encode("utf-8", errors="replace"))
    fallback_line_count = len(text.splitlines()) if text else 0
    byte_count = safe_int(payload.get("byte_count"), -1)
    if byte_count <= 0 and fallback_byte_count:
        byte_count = fallback_byte_count
    byte_count = max(byte_count, 0)
    line_count = safe_int(payload.get("line_count"), -1)
    if line_count <= 0 and fallback_line_count:
        line_count = fallback_line_count
    line_count = max(line_count, 0)
    skipped_bytes = safe_int(payload.get("skipped_bytes"), 0)
    truncated = bool(payload.get("truncated")) or skipped_bytes > 0
    created_at = str(event.get("created_at") or now_iso()).strip() or now_iso()
    job_id = str(event.get("job_id") or payload.get("job_id") or "").strip()
    agent_execution_id = str(event.get("agent_execution_id") or payload.get("agent_execution_id") or "").strip()

    evidence = normalize_workspace_run_delta_evidence(current)
    evidence["total_events"] = safe_int(evidence.get("total_events"), 0) + 1
    evidence["total_bytes"] = safe_int(evidence.get("total_bytes"), 0) + byte_count
    evidence["total_lines"] = safe_int(evidence.get("total_lines"), 0) + line_count
    evidence["skipped_bytes"] = safe_int(evidence.get("skipped_bytes"), 0) + skipped_bytes
    if truncated:
        evidence["truncated_events"] = safe_int(evidence.get("truncated_events"), 0) + 1
    evidence["updated_at"] = created_at
    if job_id:
        evidence["job_ids"] = _workspace_delta_evidence_id_list([*evidence.get("job_ids", []), job_id])
    if agent_execution_id:
        evidence["agent_execution_ids"] = _workspace_delta_evidence_id_list(
            [*evidence.get("agent_execution_ids", []), agent_execution_id]
        )

    by_type = evidence.get("by_type") if isinstance(evidence.get("by_type"), dict) else {}
    item = by_type.get(event_type) if isinstance(by_type.get(event_type), dict) else {}
    by_type[event_type] = {
        "event_count": safe_int(item.get("event_count"), 0) + 1,
        "byte_count": safe_int(item.get("byte_count"), 0) + byte_count,
        "line_count": safe_int(item.get("line_count"), 0) + line_count,
        "truncated_count": safe_int(item.get("truncated_count"), 0) + (1 if truncated else 0),
        "skipped_bytes": safe_int(item.get("skipped_bytes"), 0) + skipped_bytes,
        "last_at": created_at,
    }
    evidence["by_type"] = by_type
    evidence["event_types"] = sorted(by_type)
    recent = evidence.get("recent") if isinstance(evidence.get("recent"), list) else []
    recent.append(
        {
            "type": event_type,
            "created_at": created_at,
            "job_id": job_id,
            "agent_execution_id": agent_execution_id,
            "byte_count": byte_count,
            "line_count": line_count,
            "truncated": truncated,
            "skipped_bytes": skipped_bytes,
            "content": "omitted",
        }
    )
    evidence["recent"] = recent[-WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX:]
    return normalize_workspace_run_delta_evidence(evidence)
