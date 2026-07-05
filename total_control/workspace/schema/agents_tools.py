from __future__ import annotations

import copy
import re
import uuid
from typing import Any

from ...constants import *  # noqa: F403
from ...tools.registry import TOOL_SIDE_EFFECTS, tool_side_effect
from ...utils import *  # noqa: F403
from ..errors import WorkspaceWorkflowReadinessError


def _tool_side_effect_value(value: Any, fallback: str = "read") -> str:
    if hasattr(value, "value"):
        return str(value.value or fallback).strip() or fallback
    return str(value or fallback).strip() or fallback


def workspace_default_agents() -> list[dict[str, Any]]:
    return copy.deepcopy(DEFAULT_WORKSPACE_AGENTS)

def workspace_default_tools() -> list[dict[str, Any]]:
    return copy.deepcopy(DEFAULT_WORKSPACE_TOOLS)

def normalize_workspace_tool(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    preset_seed = str(
        current.get("id")
        or previous.get("id")
        or current.get("label")
        or previous.get("label")
        or current.get("name")
        or previous.get("name")
        or "",
    ).strip()
    preset = next(
        (
            item for item in DEFAULT_WORKSPACE_TOOLS
            if preset_seed and preset_seed in {
                str(item.get("id") or "").strip(),
                str(item.get("label") or "").strip(),
            }
        ),
        {},
    )
    base = {}
    if isinstance(preset, dict):
        base.update(copy.deepcopy(preset))
    base.update(copy.deepcopy(previous))
    base.update(copy.deepcopy(current))
    tool_id = safe_id(str(base.get("id") or base.get("name") or f"tool-{index + 1}")) or f"tool-{index + 1}"
    label = str(base.get("label") or base.get("display_name") or tool_id).strip() or tool_id
    category = str(base.get("category") or "general").strip() or "general"
    capability = str(base.get("capability") or "read").strip() or "read"
    registry_meta = TOOL_SIDE_EFFECTS.get(tool_id) if isinstance(TOOL_SIDE_EFFECTS.get(tool_id), dict) else {}
    side_effect = _tool_side_effect_value(
        base.get("side_effect") or registry_meta.get("side_effect") or tool_side_effect(tool_id),
    )
    implemented = bool(registry_meta.get("implemented", False)) if registry_meta else False
    if registry_meta and "implemented" in base:
        implemented = bool(base.get("implemented"))
    return {
        "id": tool_id,
        "label": label,
        "category": category,
        "capability": capability,
        "side_effect": side_effect,
        "implemented": implemented,
        "requires_runtime": bool(base.get("requires_runtime", registry_meta.get("requires_runtime", False))),
        "fallback": str(base.get("fallback") or registry_meta.get("fallback") or "").strip(),
        "runtime_control": str(base.get("runtime_control") or registry_meta.get("runtime_control") or "").strip(),
        "provider_profile_id": str(base.get("provider_profile_id") or "").strip(),
        "description": str(base.get("description") or "").strip(),
        "enabled": bool(base.get("enabled", True)),
        "notes": str(base.get("notes") or "").strip(),
    }

def normalize_workspace_tools(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_tools()
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        tool = normalize_workspace_tool(item, index=index, existing=existing_item)
        if tool["id"] in seen:
            continue
        seen.add(tool["id"])
        tools.append(tool)
    if tools:
        return tools
    return [normalize_workspace_tool(item, index=index) for index, item in enumerate(workspace_default_tools())]

def normalize_workspace_agent(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
    tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    preset_seed = str(current.get("id") or previous.get("id") or current.get("role") or previous.get("role") or "").strip()
    preset = next(
        (
            item for item in DEFAULT_WORKSPACE_AGENTS
            if preset_seed and preset_seed in {str(item.get("id") or "").strip(), str(item.get("role") or "").strip()}
        ),
        {},
    )
    base = {}
    if isinstance(preset, dict):
        base.update(copy.deepcopy(preset))
    base.update(copy.deepcopy(previous))
    base.update(copy.deepcopy(current))
    name = str(base.get("name") or f"Agent {index + 1}").strip() or f"Agent {index + 1}"
    role = str(base.get("role") or safe_id(name) or f"agent-{index + 1}").strip() or f"agent-{index + 1}"
    agent_id = safe_id(str(base.get("id") or role or name or f"agent-{index + 1}")) or f"agent-{index + 1}"
    tools = parse_tag_list(base.get("tools", []))
    allowed_tools = {str(item or "").strip() for item in (tool_ids or []) if str(item or "").strip()}
    if allowed_tools:
        filtered_tools = [tool for tool in tools if tool in allowed_tools]
        if filtered_tools:
            tools = filtered_tools
    max_iterations_raw = base.get("max_iterations")
    max_iterations = safe_int(max_iterations_raw, 0) if max_iterations_raw not in (None, "") else 0
    timeout_raw = base.get("timeout_seconds")
    timeout_seconds = float(timeout_raw) if timeout_raw not in (None, "") and safe_int(timeout_raw, 0) > 0 else 0.0
    output_format = str(base.get("output_format") or "").strip().lower()
    if output_format not in {"", "text", "json"}:
        output_format = ""
    result: dict[str, Any] = {
        "id": agent_id,
        "name": name,
        "role": role,
        "prompt": str(base.get("prompt") or "").strip(),
        "tools": tools,
        "provider_profile_id": str(base.get("provider_profile_id") or "").strip(),
        "enabled": bool(base.get("enabled", True)),
    }
    if max_iterations > 0:
        result["max_iterations"] = max_iterations
    if timeout_seconds > 0:
        result["timeout_seconds"] = timeout_seconds
    if output_format:
        result["output_format"] = output_format
    return result

def normalize_workspace_agents(
    value: Any,
    *,
    existing: Any = None,
    tool_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_agents()
    agents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        agent = normalize_workspace_agent(item, index=index, existing=existing_item, tool_ids=tool_ids)
        if agent["id"] in seen:
            continue
        seen.add(agent["id"])
        agents.append(agent)
    if agents:
        return agents
    return [normalize_workspace_agent(item, index=index, tool_ids=tool_ids) for index, item in enumerate(workspace_default_agents())]

def normalize_global_tool_definition(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tool = normalize_workspace_tool(value, index=index, existing=existing)
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    created_at = str(previous.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        **tool,
        "created_at": created_at,
        "updated_at": now_iso(),
    }

def normalize_global_tool_definitions(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id = {
        str(item.get("id") or "").strip(): item
        for item in previous_list
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_tools()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        tool = normalize_global_tool_definition(item, index=index, existing=existing_item)
        if tool["id"] in seen:
            continue
        seen.add(tool["id"])
        items.append(tool)
    return items or [
        normalize_global_tool_definition(item, index=index)
        for index, item in enumerate(workspace_default_tools())
    ]

def normalize_global_agent_definition(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
    tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    agent = normalize_workspace_agent(value, index=index, existing=existing, tool_ids=tool_ids)
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    created_at = str(previous.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        **agent,
        "description": str(current.get("description") or previous.get("description") or "").strip(),
        "created_at": created_at,
        "updated_at": now_iso(),
    }

def normalize_global_agent_definitions(
    value: Any,
    *,
    existing: Any = None,
    tool_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id = {
        str(item.get("id") or "").strip(): item
        for item in previous_list
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_agents()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        agent = normalize_global_agent_definition(
            item,
            index=index,
            existing=existing_item,
            tool_ids=tool_ids,
        )
        if agent["id"] in seen:
            continue
        seen.add(agent["id"])
        items.append(agent)
    return items or [
        normalize_global_agent_definition(item, index=index, tool_ids=tool_ids)
        for index, item in enumerate(workspace_default_agents())
    ]

def default_tool_definition_by_id(tool_id: str) -> dict[str, Any] | None:
    target = str(tool_id or "").strip()
    return next(
        (
            copy.deepcopy(item)
            for item in DEFAULT_WORKSPACE_TOOLS
            if str(item.get("id") or "").strip() == target
        ),
        None,
    )

def default_agent_preset_for(agent: dict[str, Any]) -> dict[str, Any] | None:
    agent_id = str(agent.get("id") or "").strip()
    role = str(agent.get("role") or "").strip()
    return next(
        (
            copy.deepcopy(item)
            for item in DEFAULT_WORKSPACE_AGENTS
            if str(item.get("id") or "").strip() in {agent_id, role}
            or str(item.get("role") or "").strip() in {agent_id, role}
        ),
        None,
    )

def backfill_default_tool_definitions(
    tools: list[dict[str, Any]],
    *,
    required_tool_ids: list[str] | None = None,
    global_definitions: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    available_ids = {
        str(item.get("id") or "").strip()
        for item in tools
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    required_ids = [
        str(item or "").strip()
        for item in (required_tool_ids or [str(item.get("id") or "") for item in DEFAULT_WORKSPACE_TOOLS])
        if str(item or "").strip()
    ]
    updated = [copy.deepcopy(item) for item in tools if isinstance(item, dict)]
    applied: list[dict[str, Any]] = []
    for tool_id in required_ids:
        if tool_id in available_ids:
            continue
        preset = default_tool_definition_by_id(tool_id)
        if not preset:
            continue
        tool = (
            normalize_global_tool_definition(preset, index=len(updated))
            if global_definitions
            else normalize_workspace_tool(preset, index=len(updated))
        )
        updated.append(tool)
        available_ids.add(tool_id)
        applied.append(
            {
                "field": "tools",
                "label": "默认工具定义",
                "value": tool_id,
                "source": "default_tool_backfill",
            }
        )
    return updated, applied

def default_agent_required_tool_ids(agents: list[dict[str, Any]]) -> list[str]:
    tool_ids: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        preset = default_agent_preset_for(agent)
        if not preset:
            continue
        for tool_id in parse_tag_list(preset.get("tools", [])):
            if tool_id in seen:
                continue
            seen.add(tool_id)
            tool_ids.append(tool_id)
    return tool_ids

def workspace_required_default_tool_ids(workspace: dict[str, Any]) -> list[str]:
    from ..automation.run_plan import workspace_node_required_tool_id

    tool_ids: list[str] = []
    seen: set[str] = set()
    for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        tool_id = workspace_node_required_tool_id(str(node.get("kind") or "").strip())
        if tool_id and tool_id not in seen:
            seen.add(tool_id)
            tool_ids.append(tool_id)
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for tool_id in default_agent_required_tool_ids(agents):
        if tool_id in seen:
            continue
        seen.add(tool_id)
        tool_ids.append(tool_id)
    return tool_ids

def backfill_default_agent_tools(
    agents: list[dict[str, Any]],
    *,
    tool_ids: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed_tool_ids = {
        str(item or "").strip()
        for item in (tool_ids or [])
        if str(item or "").strip()
    }
    updated: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        current = copy.deepcopy(agent)
        preset = default_agent_preset_for(current)
        if not preset:
            updated.append(current)
            continue
        current_tools = parse_tag_list(current.get("tools", []))
        seen = set(current_tools)
        missing: list[str] = []
        for tool_id in parse_tag_list(preset.get("tools", [])):
            if allowed_tool_ids and tool_id not in allowed_tool_ids:
                continue
            if tool_id in seen:
                continue
            seen.add(tool_id)
            current_tools.append(tool_id)
            missing.append(tool_id)
        if missing:
            current["tools"] = current_tools
            if "updated_at" in current:
                current["updated_at"] = now_iso()
            applied.append(
                {
                    "field": f"agents.{str(current.get('id') or '').strip()}.tools",
                    "label": f"{str(current.get('name') or current.get('id') or 'Agent').strip()} 工具授权",
                    "value": ", ".join(missing),
                    "source": "default_agent_tool_backfill",
                }
            )
        updated.append(current)
    return updated, applied
