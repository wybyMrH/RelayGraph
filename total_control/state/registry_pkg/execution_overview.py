from __future__ import annotations

import copy
from typing import Any

from ...utils import parse_iso_timestamp


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
