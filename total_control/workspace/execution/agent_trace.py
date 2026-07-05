"""Agent trace helpers for fine-grained events and replay persistence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

TRACE_TEXT_LIMIT = 240
TRACE_ARGS_LIMIT = 160
TRACE_OBS_LIMIT = 280
MAX_TRACE_EVENTS = 48
MAX_TRACE_STEPS = 24


def summarize_trace_text(text: str, limit: int = TRACE_TEXT_LIMIT) -> str:
    # 截断过长文本，便于 trace 存储与回放
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "…"


def compact_tool_arguments(arguments: Any) -> str:
    # 工具参数摘要
    if not isinstance(arguments, dict) or not arguments:
        return ""
    try:
        raw = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        raw = str(arguments)
    return summarize_trace_text(raw, TRACE_ARGS_LIMIT)


def compact_tool_observation(observation: str) -> str:
    # 工具观察结果摘要
    return summarize_trace_text(str(observation or ""), TRACE_OBS_LIMIT)


def tool_observation_failed(observation: str) -> bool:
    # 判断工具返回是否表示失败
    text = str(observation or "").strip()
    if not text:
        return False
    if text.startswith("Error"):
        return True
    lowered = text.lower()
    return (
        '"status": "error"' in lowered
        or '"status":"error"' in lowered
        or '"status": "blocked"' in lowered
        or '"status":"blocked"' in lowered
        or '"status": "failed"' in lowered
        or '"status":"failed"' in lowered
        or '"status": "stopped"' in lowered
        or '"status":"stopped"' in lowered
        or '"status": "timeout"' in lowered
        or '"status":"timeout"' in lowered
    )


def make_agent_trace_event(event_type: str, **fields: Any) -> dict[str, Any]:
    # 构造标准 trace 事件
    payload: dict[str, Any] = {
        "type": str(event_type or "").strip(),
        "at": str(fields.pop("at", None) or datetime.now().isoformat()),
    }
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                continue
            payload[key] = normalized
        elif isinstance(value, (int, float, bool)):
            payload[key] = value
        elif isinstance(value, dict) and value:
            payload[key] = value
    return payload


def normalize_agent_trace_event(value: Any) -> dict[str, Any]:
    # 规范化单条 trace 事件
    source = value if isinstance(value, dict) else {}
    event_type = str(source.get("type") or "").strip()
    if not event_type:
        return {}
    normalized: dict[str, Any] = {
        "type": event_type,
        "at": str(source.get("at") or "").strip(),
    }
    for key in (
        "step_number",
        "tool_id",
        "arguments_summary",
        "observation_summary",
        "delta",
        "accumulated",
        "status",
        "side_effect",
        "error",
        "job_id",
        "run_id",
        "runtime_control",
        "runtime_side_effect",
        "runtime_status",
    ):
        if key in source and source.get(key) not in (None, ""):
            normalized[key] = source[key]
    if "controlled" in source:
        normalized["controlled"] = bool(source.get("controlled"))
    return normalized


def normalize_agent_trace_events(
    value: Any,
    *,
    limit: int = MAX_TRACE_EVENTS,
) -> list[dict[str, Any]]:
    # 规范化 trace 事件列表
    raw_items = value if isinstance(value, list) else []
    events: list[dict[str, Any]] = []
    for item in raw_items:
        normalized = normalize_agent_trace_event(item)
        if normalized:
            events.append(normalized)
    return events[: max(limit, 1)]


def compact_agent_step_for_trace(step: dict[str, Any]) -> dict[str, Any]:
    # 压缩 Agent 步用于持久化
    if not isinstance(step, dict):
        return {}
    action = str(step.get("action") or "").strip()
    return {
        "step_number": int(step.get("step_number") or 0),
        "thought": summarize_trace_text(str(step.get("thought") or "")),
        "action": action,
        "action_input_summary": compact_tool_arguments(step.get("action_input")),
        "observation_summary": compact_tool_observation(str(step.get("observation") or step.get("error") or "")),
        "timestamp": str(step.get("timestamp") or "").strip(),
        "side_effect": str(step.get("side_effect") or "").strip(),
        "controlled": bool(step.get("controlled")),
        "job_id": str(step.get("job_id") or "").strip(),
        "run_id": str(step.get("run_id") or "").strip(),
        "runtime_control": str(step.get("runtime_control") or "").strip(),
        "runtime_side_effect": str(step.get("runtime_side_effect") or "").strip(),
        "runtime_status": str(step.get("runtime_status") or "").strip(),
    }


def normalize_agent_execution_trace(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # 规范化 chat/run 附带的 agent 执行 trace
    source = value if isinstance(value, dict) and value else {}
    previous = existing if isinstance(existing, dict) else {}
    execution_id = str(source.get("id") or previous.get("id") or "").strip()
    if not execution_id and not source and not previous:
        return {}
    raw_steps = source.get("steps") if isinstance(source.get("steps"), list) else None
    previous_steps = previous.get("steps") if isinstance(previous.get("steps"), list) else []
    steps_source = raw_steps if raw_steps is not None else previous_steps
    compact_steps = [
        compact_agent_step_for_trace(item)
        for item in steps_source
        if isinstance(item, dict)
    ]
    compact_steps = [item for item in compact_steps if item][:MAX_TRACE_STEPS]
    raw_events = source.get("trace_events") if isinstance(source.get("trace_events"), list) else None
    previous_events = previous.get("trace_events") if isinstance(previous.get("trace_events"), list) else []
    trace_events = normalize_agent_trace_events(
        raw_events if raw_events is not None else previous_events,
    )
    return {
        "id": execution_id,
        "model": str(source.get("model") or previous.get("model") or "").strip(),
        "provider_profile_id": str(source.get("provider_profile_id") or previous.get("provider_profile_id") or "").strip(),
        "total_tokens": int(source.get("total_tokens") if source.get("total_tokens") is not None else previous.get("total_tokens") or 0),
        "total_steps": int(source.get("total_steps") if source.get("total_steps") is not None else previous.get("total_steps") or len(compact_steps)),
        "success": bool(source.get("success")) if "success" in source else bool(previous.get("success")),
        "error": str(source.get("error") or previous.get("error") or "").strip(),
        "steps": compact_steps,
        "trace_events": trace_events,
    }


def build_agent_execution_trace(
    execution_id: str,
    *,
    model: str = "",
    provider_profile_id: str = "",
    total_tokens: int = 0,
    total_steps: int = 0,
    success: bool = False,
    error: str = "",
    trace_events: list[dict[str, Any]] | None = None,
    agent_steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # 从执行结果构造可回放 trace
    compact_steps = [
        compact_agent_step_for_trace(item)
        for item in (agent_steps or [])
        if isinstance(item, dict)
    ]
    compact_steps = [item for item in compact_steps if item][:MAX_TRACE_STEPS]
    return normalize_agent_execution_trace(
        {
            "id": str(execution_id or "").strip(),
            "model": model,
            "provider_profile_id": provider_profile_id,
            "total_tokens": total_tokens,
            "total_steps": total_steps or len(compact_steps),
            "success": success,
            "error": error,
            "steps": compact_steps,
            "trace_events": normalize_agent_trace_events(trace_events or []),
        }
    )
