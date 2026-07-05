from __future__ import annotations

import copy
import re
import uuid
from datetime import datetime
from typing import Any

from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ..errors import WorkspaceWorkflowReadinessError
from .agents_tools import (
    normalize_global_agent_definitions,
    normalize_global_tool_definitions,
    workspace_default_agents,
    workspace_default_tools,
)
from .chat import normalize_workspace_chat
from .nodes import (
    build_recommended_handler,
    finalize_agent_executable_nodes,
    normalize_workspace_links,
    normalize_workspace_nodes,
    should_upgrade_default_workflow_chain,
    sync_workspace_nodes_with_overview,
)
from .recipe import (
    normalize_source_mode,
    normalize_workspace_inputs,
    normalize_workspace_model,
    normalize_workspace_recipe,
    source_type_for_chain,
    workspace_input_source_summary,
)
from ..execution import normalize_workspace_execution_runs



def workflow_template_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("updated_at") or ""),
        str(item.get("created_at") or ""),
        str(item.get("id") or ""),
    )

def normalize_workflow_template_version_history(raw: Any, *, limit: int = 20) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        record = {
            "schema": "relaygraph.workflow_template.version_record.v1",
            "id": str(item.get("id") or "").strip()[:80],
            "mode": str(item.get("mode") or "update").strip() or "update",
            "recorded_at": str(item.get("recorded_at") or "").strip(),
            "template_id": str(item.get("template_id") or "").strip(),
            "template_name": str(item.get("template_name") or "").strip(),
            "from_updated_at": str(item.get("from_updated_at") or "").strip(),
            "to_updated_at": str(item.get("to_updated_at") or "").strip(),
            "from_node_count": safe_int(item.get("from_node_count"), 0),
            "to_node_count": safe_int(item.get("to_node_count"), 0),
            "summary": {
                "changed_count": safe_int(summary.get("changed_count"), 0),
                "added_node_count": safe_int(summary.get("added_node_count"), 0),
                "removed_node_count": safe_int(summary.get("removed_node_count"), 0),
                "changed_node_count": safe_int(summary.get("changed_node_count"), 0),
                "added_link_count": safe_int(summary.get("added_link_count"), 0),
                "removed_link_count": safe_int(summary.get("removed_link_count"), 0),
                "link_topology_changed": bool(summary.get("link_topology_changed")),
                "link_order_changed": bool(summary.get("link_order_changed")),
            },
            "changed_fields": [
                str(field or "").strip()
                for field in item.get("changed_fields", [])
                if str(field or "").strip()
            ][:12] if isinstance(item.get("changed_fields"), list) else [],
            "changed_nodes": [
                {
                    "id": str(node.get("id") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                    "changed_fields": [
                        str(field or "").strip()
                        for field in node.get("changed_fields", [])
                        if str(field or "").strip()
                    ][:8] if isinstance(node.get("changed_fields"), list) else [],
                }
                for node in item.get("changed_nodes", [])
                if isinstance(node, dict)
            ][:8] if isinstance(item.get("changed_nodes"), list) else [],
            "added_nodes": [
                {
                    "id": str(node.get("id") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                }
                for node in item.get("added_nodes", [])
                if isinstance(node, dict)
            ][:8] if isinstance(item.get("added_nodes"), list) else [],
            "removed_nodes": [
                {
                    "id": str(node.get("id") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                }
                for node in item.get("removed_nodes", [])
                if isinstance(node, dict)
            ][:8] if isinstance(item.get("removed_nodes"), list) else [],
            "warnings": [
                str(warning or "").strip()
                for warning in item.get("warnings", [])
                if str(warning or "").strip()
            ][:12] if isinstance(item.get("warnings"), list) else [],
        }
        if not record["id"]:
            record["id"] = safe_id(f"template-version-{record['recorded_at']}-{record['mode']}") or uuid.uuid4().hex[:12]
        history.append(record)
    history.sort(key=lambda row: str(row.get("recorded_at") or ""), reverse=True)
    return history[: max(1, safe_int(limit, 20))]

def workflow_template_version_record(
    previous_template: dict[str, Any] | None,
    current_template: dict[str, Any],
    *,
    agent_definitions: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
    mode: str = "update",
) -> dict[str, Any] | None:
    current = current_template if isinstance(current_template, dict) else {}
    previous = previous_template if isinstance(previous_template, dict) else None
    recorded_at = now_iso()
    current_snapshot = build_template_snapshot(current, agent_definitions, tool_definitions)
    if previous:
        previous_snapshot = build_template_snapshot(previous, agent_definitions, tool_definitions)
        diff = workflow_template_snapshot_diff(previous_snapshot, current_snapshot)
        metadata_fields = ("name", "description", "status", "brief", "tags", "notes")
        metadata_changed = [
            f"metadata.{field}"
            for field in metadata_fields
            if copy.deepcopy(previous.get(field)) != copy.deepcopy(current.get(field))
        ]
        if not diff.get("changed") and not metadata_changed:
            return None
        if metadata_changed:
            summary = diff.get("summary") if isinstance(diff.get("summary"), dict) else {}
            details = diff.get("diff") if isinstance(diff.get("diff"), dict) else {}
            changed_fields = details.get("changed_fields") if isinstance(details.get("changed_fields"), list) else []
            details["changed_fields"] = [*changed_fields, *metadata_changed]
            summary["changed_count"] = safe_int(summary.get("changed_count"), 0) + len(metadata_changed)
            summary["field_change_count"] = safe_int(summary.get("field_change_count"), 0) + len(metadata_changed)
            diff["summary"] = summary
            diff["diff"] = details
    else:
        node_count = len(current.get("nodes") if isinstance(current.get("nodes"), list) else [])
        link_count = len(current.get("links") if isinstance(current.get("links"), list) else [])
        diff = {
            "summary": {
                "changed_count": node_count + link_count,
                "added_node_count": node_count,
                "removed_node_count": 0,
                "changed_node_count": 0,
                "added_link_count": link_count,
                "removed_link_count": 0,
                "link_topology_changed": bool(link_count),
                "link_order_changed": False,
            },
            "diff": {
                "added_nodes": [
                    {
                        "id": _snapshot_node_key(node),
                        "title": str(node.get("title") or node.get("kind") or _snapshot_node_key(node)).strip(),
                        "kind": str(node.get("kind") or "").strip(),
                    }
                    for node in current.get("nodes", [])
                    if isinstance(node, dict)
                ][:8],
                "removed_nodes": [],
                "changed_nodes": [],
                "changed_fields": ["template_created"],
            },
            "migration_plan": {"warnings": []},
        }
    details = diff.get("diff") if isinstance(diff.get("diff"), dict) else {}
    summary = diff.get("summary") if isinstance(diff.get("summary"), dict) else {}
    plan = diff.get("migration_plan") if isinstance(diff.get("migration_plan"), dict) else {}
    record = {
        "schema": "relaygraph.workflow_template.version_record.v1",
        "id": safe_id(f"{recorded_at}-{current.get('id') or 'template'}-{mode}") or uuid.uuid4().hex[:12],
        "mode": str(mode or "update").strip() or "update",
        "recorded_at": recorded_at,
        "template_id": str(current.get("id") or "").strip(),
        "template_name": str(current.get("name") or "").strip(),
        "from_updated_at": str(previous.get("updated_at") or "") if previous else "",
        "to_updated_at": str(current.get("updated_at") or "").strip(),
        "from_node_count": len(previous.get("nodes") if previous and isinstance(previous.get("nodes"), list) else []),
        "to_node_count": len(current.get("nodes") if isinstance(current.get("nodes"), list) else []),
        "summary": copy.deepcopy(summary),
        "changed_fields": copy.deepcopy(details.get("changed_fields") if isinstance(details.get("changed_fields"), list) else []),
        "added_nodes": copy.deepcopy(details.get("added_nodes") if isinstance(details.get("added_nodes"), list) else []),
        "removed_nodes": copy.deepcopy(details.get("removed_nodes") if isinstance(details.get("removed_nodes"), list) else []),
        "changed_nodes": copy.deepcopy(details.get("changed_nodes") if isinstance(details.get("changed_nodes"), list) else []),
        "warnings": copy.deepcopy(plan.get("warnings") if isinstance(plan.get("warnings"), list) else []),
    }
    return normalize_workflow_template_version_history([record], limit=1)[0]

def collect_template_agent_ids(
    nodes: list[dict[str, Any]],
    model: dict[str, Any],
) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or "").strip()
        if agent_id and agent_id not in seen:
            seen.add(agent_id)
            ids.append(agent_id)
    chat_agent_id = str(model.get("chat_agent_id") or "").strip()
    if chat_agent_id and chat_agent_id not in seen:
        ids.append(chat_agent_id)
    return ids

def collect_template_tool_ids(
    agent_ids: list[str],
    agent_definitions: list[dict[str, Any]],
) -> list[str]:
    tools: list[str] = []
    seen: set[str] = set()
    by_id = {
        str(agent.get("id") or "").strip(): agent
        for agent in agent_definitions
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    for agent_id in agent_ids:
        agent = by_id.get(str(agent_id or "").strip())
        if not agent:
            continue
        for tool_id in parse_tag_list(agent.get("tools", [])):
            if tool_id in seen:
                continue
            seen.add(tool_id)
            tools.append(tool_id)
    return tools

def normalize_workflow_template(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    agent_definitions: list[dict[str, Any]] | None = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    source_current = current.get("source") if isinstance(current.get("source"), dict) else {}
    env_current = current.get("env") if isinstance(current.get("env"), dict) else {}
    env_payload = payload.get("env") if isinstance(payload.get("env"), dict) else {}
    recipes_current = current.get("recipes") if isinstance(current.get("recipes"), list) else []
    recipe_existing = recipes_current[0] if recipes_current and isinstance(recipes_current[0], dict) else None

    source_type = normalize_source_mode(
        str(payload.get("source_type") or source_current.get("type") or current.get("source_type") or "repo")
    )
    repo_url = str(payload.get("repo_url") or source_current.get("repo_url") or "").strip()
    paper_url = str(payload.get("paper_url") or source_current.get("paper_url") or "").strip()
    idea_text = str(payload.get("idea_text") or source_current.get("idea_text") or "").strip()
    brief = str(payload.get("brief") or current.get("brief") or "").strip()

    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if repo_url:
            name = repo_name_from_url(repo_url) or "Repo 复现默认流"
        elif paper_url:
            name = "Paper 复现默认流"
        elif idea_text or brief:
            name = "Idea 探索默认流"
        else:
            name = "新工作流模板"

    template_id = str(current.get("id") or payload.get("id") or safe_id(name) or uuid.uuid4().hex[:8]).strip()
    created_at = str(current.get("created_at") or payload.get("created_at") or now_iso()).strip() or now_iso()
    recipe = normalize_workspace_recipe(payload, existing=recipe_existing)
    workspace_dir = str(payload.get("workspace_dir") or current.get("workspace_dir") or "").strip()
    env_name = str(payload.get("env_name") or env_payload.get("name") or env_current.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_payload.get("manager") or env_current.get("manager") or "").strip()
    python_version = str(payload.get("python_version") or env_payload.get("python") or env_current.get("python") or "").strip()

    raw_nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else current.get("nodes")
    raw_links = payload.get("links") if isinstance(payload.get("links"), list) else current.get("links")
    use_default_chain = bool(payload.get("rebuild_graph")) or should_upgrade_default_workflow_chain(
        template_id,
        source_type_for_chain(source_type),
        raw_nodes,
    )
    nodes = normalize_workspace_nodes(
        raw_nodes if isinstance(raw_nodes, list) else None,
        source_type_for_chain(source_type),
        brief=brief,
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=current.get("nodes") if isinstance(current.get("nodes"), list) else None,
        use_default_chain=use_default_chain,
    )
    nodes = sync_workspace_nodes_with_overview(
        nodes,
        brief=brief,
        source_type=source_type_for_chain(source_type),
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        recipe_command_overrides={
            key
            for key in ("setup_command", "run_command", "report_command", "schedule")
            if key in payload
        },
    )

    agent_defs = agent_definitions if isinstance(agent_definitions, list) else workspace_default_agents()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if handler and (str(handler.get("name") or "").strip() or str(handler.get("agent_id") or "").strip()):
            continue
        node["handler"] = build_recommended_handler(str(node.get("kind") or ""), agent_defs)
    nodes = finalize_agent_executable_nodes(nodes, agent_defs)

    links = normalize_workspace_links(None if use_default_chain else raw_links if isinstance(raw_links, list) else None, nodes)
    model = normalize_workspace_model(payload.get("model") if "model" in payload else current.get("model"), existing=current.get("model"))
    agent_ids = collect_template_agent_ids(nodes, model)
    tool_ids = collect_template_tool_ids(agent_ids, agent_defs)

    valid_tool_ids = {
        str(tool.get("id") or "").strip()
        for tool in (tool_definitions if isinstance(tool_definitions, list) else workspace_default_tools())
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    tool_ids = [tool_id for tool_id in tool_ids if tool_id in valid_tool_ids]

    return {
        "id": safe_id(template_id) or template_id,
        "name": name,
        "description": str(payload.get("description") or current.get("description") or brief).strip(),
        "status": str(payload.get("status") or current.get("status") or "ready").strip() or "ready",
        "brief": brief,
        "source": {
            "type": source_type,
            "repo_url": repo_url,
            "repo_ref": str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
            "paper_url": paper_url,
            "idea_text": idea_text,
        },
        "workspace_dir": workspace_dir,
        "env": {
            "name": env_name,
            "manager": env_manager,
            "python": python_version,
        },
        "recipes": [recipe],
        "model": model,
        "agent_ids": agent_ids,
        "tool_ids": tool_ids,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "version_history": normalize_workflow_template_version_history(
            payload.get("version_history") if isinstance(payload.get("version_history"), list) else current.get("version_history"),
        ),
        "created_at": created_at,
        "updated_at": now_iso(),
    }

def build_default_workflow_templates(
    agent_definitions: list[dict[str, Any]] | None = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    agents = agent_definitions if isinstance(agent_definitions, list) else normalize_global_agent_definitions(None)
    tools = tool_definitions if isinstance(tool_definitions, list) else normalize_global_tool_definitions(None)
    seeds = [
        {
            "id": "repo-default-flow",
            "name": "Repo 复现默认流",
            "description": "从 repo 输入、环境准备到运行与结果整理的顺序链路。",
            "source_type": "repo",
            "brief": "给定仓库地址后，自动完成克隆、检查、环境准备、运行与结果整理。",
            "status": "ready",
        },
        {
            "id": "paper-default-flow",
            "name": "Paper 复现默认流",
            "description": "从论文输入、资料检索到运行与评估的顺序链路。",
            "source_type": "paper",
            "brief": "给定论文链接后，先检索资料与候选实现，再继续环境准备、运行与评估。",
            "status": "ready",
        },
        {
            "id": "idea-default-flow",
            "name": "Idea 探索默认流",
            "description": "从自然语言目标出发，先检索再逐步形成执行链。",
            "source_type": "idea",
            "brief": "给定目标文本后，先拆解问题、检索相关资料，再准备环境、运行与整理结果。",
            "status": "ready",
        },
    ]
    return [
        normalize_workflow_template(seed, agent_definitions=agents, tool_definitions=tools)
        for seed in seeds
    ]

def build_template_snapshot(
    template: dict[str, Any],
    agent_definitions: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    agent_index = {
        str(agent.get("id") or "").strip(): copy.deepcopy(agent)
        for agent in agent_definitions
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    tool_index = {
        str(tool.get("id") or "").strip(): copy.deepcopy(tool)
        for tool in tool_definitions
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    agent_ids = [str(item).strip() for item in template.get("agent_ids", []) if str(item).strip()]
    tool_ids = [str(item).strip() for item in template.get("tool_ids", []) if str(item).strip()]
    return {
        "template_id": str(template.get("id") or "").strip(),
        "template_name": str(template.get("name") or "").strip(),
        "source": copy.deepcopy(template.get("source") if isinstance(template.get("source"), dict) else {}),
        "env": copy.deepcopy(template.get("env") if isinstance(template.get("env"), dict) else {}),
        "recipes": copy.deepcopy(template.get("recipes") if isinstance(template.get("recipes"), list) else []),
        "model": copy.deepcopy(template.get("model") if isinstance(template.get("model"), dict) else {}),
        "nodes": copy.deepcopy(template.get("nodes") if isinstance(template.get("nodes"), list) else []),
        "links": copy.deepcopy(template.get("links") if isinstance(template.get("links"), list) else []),
        "agents": [agent_index[agent_id] for agent_id in agent_ids if agent_id in agent_index],
        "tools": [tool_index[tool_id] for tool_id in tool_ids if tool_id in tool_index],
        "created_at": now_iso(),
    }

def _snapshot_node_key(node: dict[str, Any]) -> str:
    return str(node.get("id") or node.get("kind") or node.get("title") or "").strip()

def _snapshot_node_signature(node: dict[str, Any]) -> dict[str, Any]:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    runtime = node.get("runtime") if isinstance(node.get("runtime"), dict) else {}
    input_mapping = node.get("input_mapping") if isinstance(node.get("input_mapping"), dict) else {}
    return {
        "kind": str(node.get("kind") or "").strip(),
        "title": str(node.get("title") or "").strip(),
        "handler_mode": str(handler.get("mode") or "").strip(),
        "handler_agent_id": str(handler.get("agent_id") or "").strip(),
        "handler_tool_id": str(handler.get("tool_id") or "").strip(),
        "handler_output_key": str(handler.get("output_key") or "").strip(),
        "output_key": str(node.get("output_key") or "").strip(),
        "input_mapping": copy.deepcopy(input_mapping),
        "config": copy.deepcopy(config),
        "runtime": copy.deepcopy(runtime),
    }

def _snapshot_named_ids(items: Any) -> list[str]:
    result = [
        str(item.get("id") or "").strip()
        for item in (items if isinstance(items, list) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    return sorted(dict.fromkeys(result))

def _snapshot_node_preview_item(
    node: dict[str, Any],
    *,
    index: int,
    status: str,
) -> dict[str, Any]:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    return {
        "id": _snapshot_node_key(node),
        "index": index,
        "kind": str(node.get("kind") or "").strip(),
        "title": str(node.get("title") or node.get("kind") or _snapshot_node_key(node)).strip(),
        "status": status,
        "handler_mode": str(handler.get("mode") or "").strip(),
        "handler_agent_id": str(handler.get("agent_id") or "").strip(),
        "handler_tool_id": str(handler.get("tool_id") or "").strip(),
        "handler_output_key": str(handler.get("output_key") or "").strip(),
        "output_key": str(node.get("output_key") or "").strip(),
        "has_input_mapping": isinstance(node.get("input_mapping"), dict) and bool(node.get("input_mapping")),
    }

def _snapshot_link_key(link: dict[str, Any]) -> str:
    from_id = str(link.get("from") or "").strip()
    to_id = str(link.get("to") or "").strip()
    if not from_id or not to_id or from_id == to_id:
        return ""
    return f"{from_id}->{to_id}"

def _snapshot_node_label_index(nodes: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, node in enumerate(nodes):
        node_id = _snapshot_node_key(node)
        if not node_id:
            continue
        title = str(node.get("title") or node.get("kind") or node_id).strip()
        result[node_id] = title or f"节点 {index + 1}"
    return result

def _snapshot_link_preview_item(
    link: dict[str, Any],
    *,
    index: int,
    status: str,
    node_labels: dict[str, str],
) -> dict[str, Any]:
    from_id = str(link.get("from") or "").strip()
    to_id = str(link.get("to") or "").strip()
    from_label = node_labels.get(from_id) or from_id
    to_label = node_labels.get(to_id) or to_id
    return {
        "id": str(link.get("id") or "").strip(),
        "index": index,
        "from": from_id,
        "to": to_id,
        "from_label": from_label,
        "to_label": to_label,
        "label": f"{from_label} -> {to_label}",
        "status": status,
    }

def _snapshot_link_maps(links: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    ordered: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for link in links if isinstance(links, list) else []:
        if not isinstance(link, dict):
            continue
        key = _snapshot_link_key(link)
        if not key or key in index:
            continue
        copied = copy.deepcopy(link)
        ordered.append(copied)
        index[key] = copied
    return ordered, index

def _workflow_template_migration_plan(
    *,
    status: str,
    changed_count: int,
    added_nodes: list[dict[str, Any]],
    removed_nodes: list[dict[str, Any]],
    changed_nodes: list[dict[str, Any]],
    field_changes: list[str],
    agent_added: list[str],
    agent_removed: list[str],
    tool_added: list[str],
    tool_removed: list[str],
    link_topology_changed: bool = False,
    link_order_changed: bool = False,
    link_metadata_changed: bool = False,
) -> dict[str, Any]:
    structural_fields = {"recipes"}
    config_fields = {"source", "env", "model"}
    structural_changed = bool(
        added_nodes
        or removed_nodes
        or structural_fields.intersection(field_changes)
        or link_topology_changed
        or link_order_changed
    )
    mapping_changed = any(
        any(field in {"input_mapping", "output_key", "handler_output_key"} for field in (node.get("changed_fields") or []))
        for node in changed_nodes
    )
    runtime_changed = any(
        any(field in {"handler_mode", "handler_agent_id", "handler_tool_id", "runtime", "config"} for field in (node.get("changed_fields") or []))
        for node in changed_nodes
    )
    capability_changed = bool(agent_added or agent_removed or tool_added or tool_removed)

    can_manual_apply = status == "changed" and not removed_nodes and not added_nodes and not link_topology_changed and not link_order_changed
    can_create_draft = status in {"changed", "missing_snapshot"}
    apply_scope: list[str] = []
    if can_manual_apply:
        if changed_nodes:
            apply_scope.append("nodes")
        if any(field in field_changes for field in ("env", "recipes", "model")):
            apply_scope.extend([field for field in ("env", "recipes", "model") if field in field_changes])
        if capability_changed:
            apply_scope.append("capabilities")

    if status == "same":
        plan_status = "ready"
        strategy = "no_action"
        recommended_action = "实例快照与当前模板一致，无需迁移。"
        risk_level = "low"
    elif status in {"missing_template", "missing_snapshot"}:
        plan_status = "blocked"
        strategy = "manual_rebuild"
        recommended_action = "缺少模板或实例快照，请先保留当前实例，再用当前模板新建实例进行对比。"
        risk_level = "high"
    elif removed_nodes or link_topology_changed or link_order_changed:
        plan_status = "manual_review"
        strategy = "create_new_workspace"
        recommended_action = "模板链路或节点删除发生变化，建议新建实例验证；不要直接覆盖当前实例。"
        risk_level = "high"
    elif structural_changed or mapping_changed:
        plan_status = "manual_review"
        strategy = "sync_draft_then_validate"
        recommended_action = "先把节点/映射变更作为草稿复核，通过链路诊断和执行包 gate 后再运行。"
        risk_level = "medium"
    elif runtime_changed or capability_changed or config_fields.intersection(field_changes):
        plan_status = "review"
        strategy = "sync_safe_fields"
        recommended_action = "可按模板同步配置/能力字段，但运行前仍需重新校验 provider、tool、package gate。"
        risk_level = "medium"
    else:
        plan_status = "review"
        strategy = "inspect_changes"
        recommended_action = "逐项检查模板变化，再决定是否迁移到当前实例。"
        risk_level = "medium"

    steps: list[dict[str, Any]] = []
    if status == "same":
        steps.append(
            {
                "id": "no-action",
                "label": "无需迁移",
                "status": "ready",
                "scope": "workspace",
                "detail": "当前实例仍匹配创建时的模板快照。",
            }
        )
    else:
        if added_nodes:
            steps.append(
                {
                    "id": "review-added-nodes",
                    "label": "复核新增节点",
                    "status": "manual",
                    "scope": "nodes",
                    "detail": f"{len(added_nodes)} 个新增节点需要确认 input_mapping、output_key 和 runtime 边界。",
                    "items": copy.deepcopy(added_nodes[:12]),
                }
            )
        if removed_nodes:
            steps.append(
                {
                    "id": "review-removed-nodes",
                    "label": "处理已删除节点",
                    "status": "manual",
                    "scope": "nodes",
                    "detail": f"{len(removed_nodes)} 个旧节点不在当前模板中；直接覆盖可能丢失实例配置。",
                    "items": copy.deepcopy(removed_nodes[:12]),
                }
            )
        if changed_nodes:
            steps.append(
                {
                    "id": "review-changed-nodes",
                    "label": "复核节点字段",
                    "status": "manual",
                    "scope": "nodes",
                    "detail": f"{len(changed_nodes)} 个节点字段变化，重点检查 handler、input_mapping、output_key、config。",
                    "items": copy.deepcopy(changed_nodes[:12]),
                }
            )
        if field_changes:
            steps.append(
                {
                    "id": "review-template-fields",
                    "label": "复核模板级字段",
                    "status": "manual",
                    "scope": "template",
                    "detail": "模板级字段变化会影响 source/env/model/links/recipes 的默认行为。",
                    "fields": list(field_changes),
                }
            )
        if capability_changed:
            steps.append(
                {
                    "id": "check-capabilities",
                    "label": "校验能力依赖",
                    "status": "manual",
                    "scope": "capabilities",
                    "detail": "Agent/Tool 集合变化后，需要在配置中心确认 provider route 和 tool side-effect 策略。",
                    "agents": {"added": agent_added, "removed": agent_removed},
                    "tools": {"added": tool_added, "removed": tool_removed},
                }
            )
        steps.append(
            {
                "id": "validate-before-run",
                "label": "运行前重新校验",
                "status": "required",
                "scope": "readiness",
                "detail": "迁移或新建实例后，必须重新通过链路诊断、执行包 readiness gate 和必要 smoke。",
            }
        )

    blockers: list[str] = []
    warnings: list[str] = []
    if status == "missing_template":
        blockers.append("current_template_missing")
    if status == "missing_snapshot":
        blockers.append("workspace_snapshot_missing")
    if removed_nodes:
        warnings.append("removed_nodes_need_manual_review")
    if link_topology_changed:
        warnings.append("link_topology_changed")
    if link_order_changed:
        warnings.append("link_order_changed")
    if link_metadata_changed:
        warnings.append("link_metadata_changed")
    if mapping_changed:
        warnings.append("input_mapping_or_output_key_changed")
    if capability_changed:
        warnings.append("capability_set_changed")

    return {
        "schema": "relaygraph.workflow_template.migration_plan.v1",
        "status": plan_status,
        "strategy": strategy,
        "risk_level": risk_level,
        "changed_count": changed_count,
        "can_auto_apply": False,
        "can_manual_apply": can_manual_apply,
        "can_create_draft": can_create_draft,
        "apply_scope": apply_scope,
        "recommended_action": recommended_action,
        "blockers": blockers,
        "warnings": warnings,
        "steps": steps,
    }

def workflow_template_snapshot_diff(
    workspace_snapshot: dict[str, Any] | None,
    current_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    previous = workspace_snapshot if isinstance(workspace_snapshot, dict) else {}
    current = current_snapshot if isinstance(current_snapshot, dict) else {}
    previous_node_list = [
        node
        for node in (previous.get("nodes") if isinstance(previous.get("nodes"), list) else [])
        if isinstance(node, dict) and _snapshot_node_key(node)
    ]
    current_node_list = [
        node
        for node in (current.get("nodes") if isinstance(current.get("nodes"), list) else [])
        if isinstance(node, dict) and _snapshot_node_key(node)
    ]
    previous_nodes = {
        _snapshot_node_key(node): node
        for node in previous_node_list
    }
    current_nodes = {
        _snapshot_node_key(node): node
        for node in current_node_list
    }
    previous_keys = set(previous_nodes)
    current_keys = set(current_nodes)
    previous_link_list, previous_links = _snapshot_link_maps(previous.get("links"))
    current_link_list, current_links = _snapshot_link_maps(current.get("links"))
    previous_link_keys = set(previous_links)
    current_link_keys = set(current_links)
    previous_link_sequence = [_snapshot_link_key(link) for link in previous_link_list]
    current_link_sequence = [_snapshot_link_key(link) for link in current_link_list]
    added_links = [
        _snapshot_link_preview_item(
            current_links[key],
            index=current_link_sequence.index(key) if key in current_link_sequence else 0,
            status="added",
            node_labels=_snapshot_node_label_index(current_node_list),
        )
        for key in current_link_sequence
        if key and key not in previous_link_keys
    ]
    removed_links = [
        _snapshot_link_preview_item(
            previous_links[key],
            index=previous_link_sequence.index(key) if key in previous_link_sequence else 0,
            status="removed",
            node_labels=_snapshot_node_label_index(previous_node_list),
        )
        for key in previous_link_sequence
        if key and key not in current_link_keys
    ]
    link_topology_changed = bool(added_links or removed_links)
    link_order_changed = (
        not link_topology_changed
        and previous_link_sequence != current_link_sequence
        and previous_link_keys == current_link_keys
    )
    link_metadata_changed = (
        copy.deepcopy(previous.get("links") if isinstance(previous.get("links"), list) else [])
        != copy.deepcopy(current.get("links") if isinstance(current.get("links"), list) else [])
        and not link_topology_changed
        and not link_order_changed
    )
    added_nodes = [
        {
            "id": key,
            "kind": str(current_nodes[key].get("kind") or "").strip(),
            "title": str(current_nodes[key].get("title") or current_nodes[key].get("kind") or key).strip(),
        }
        for key in sorted(current_keys - previous_keys)
    ]
    removed_nodes = [
        {
            "id": key,
            "kind": str(previous_nodes[key].get("kind") or "").strip(),
            "title": str(previous_nodes[key].get("title") or previous_nodes[key].get("kind") or key).strip(),
        }
        for key in sorted(previous_keys - current_keys)
    ]
    changed_nodes = []
    for key in sorted(previous_keys & current_keys):
        before = _snapshot_node_signature(previous_nodes[key])
        after = _snapshot_node_signature(current_nodes[key])
        changed_fields = [
            field for field in ("kind", "title", "handler_mode", "handler_agent_id", "handler_tool_id", "handler_output_key", "output_key", "input_mapping", "config", "runtime")
            if before.get(field) != after.get(field)
        ]
        if changed_fields:
            changed_nodes.append(
                {
                    "id": key,
                    "kind": str(after.get("kind") or before.get("kind") or "").strip(),
                    "title": str(after.get("title") or before.get("title") or key).strip(),
                    "changed_fields": changed_fields,
                }
            )

    field_changes = []
    for field in ("source", "env", "recipes", "model", "links"):
        if copy.deepcopy(previous.get(field)) != copy.deepcopy(current.get(field)):
            field_changes.append(field)
    previous_agents = _snapshot_named_ids(previous.get("agents"))
    current_agents = _snapshot_named_ids(current.get("agents"))
    previous_tools = _snapshot_named_ids(previous.get("tools"))
    current_tools = _snapshot_named_ids(current.get("tools"))
    agent_added = sorted(set(current_agents) - set(previous_agents))
    agent_removed = sorted(set(previous_agents) - set(current_agents))
    tool_added = sorted(set(current_tools) - set(previous_tools))
    tool_removed = sorted(set(previous_tools) - set(current_tools))
    changed_count = len(added_nodes) + len(removed_nodes) + len(changed_nodes) + len(field_changes) + len(agent_added) + len(agent_removed) + len(tool_added) + len(tool_removed)
    status = "changed" if changed_count else "same"
    if not previous:
        status = "missing_snapshot"
    elif not current:
        status = "missing_template"
    migration_plan = _workflow_template_migration_plan(
        status=status,
        changed_count=changed_count,
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        changed_nodes=changed_nodes,
        field_changes=field_changes,
        agent_added=agent_added,
        agent_removed=agent_removed,
        tool_added=tool_added,
        tool_removed=tool_removed,
        link_topology_changed=link_topology_changed,
        link_order_changed=link_order_changed,
        link_metadata_changed=link_metadata_changed,
    )
    changed_node_ids = {str(item.get("id") or "").strip() for item in changed_nodes}
    structure_preview = {
        "schema": "relaygraph.workflow_template.structure_preview.v1",
        "topology_changed": bool(added_nodes or removed_nodes or link_topology_changed or link_order_changed),
        "previous_nodes": [
            _snapshot_node_preview_item(
                node,
                index=index,
                status="removed" if _snapshot_node_key(node) not in current_keys else "changed" if _snapshot_node_key(node) in changed_node_ids else "same",
            )
            for index, node in enumerate(previous_node_list[:40])
        ],
        "current_nodes": [
            _snapshot_node_preview_item(
                node,
                index=index,
                status="added" if _snapshot_node_key(node) not in previous_keys else "changed" if _snapshot_node_key(node) in changed_node_ids else "same",
            )
            for index, node in enumerate(current_node_list[:40])
        ],
        "previous_count": len(previous_node_list),
        "current_count": len(current_node_list),
        "truncated": len(previous_node_list) > 40 or len(current_node_list) > 40,
    }
    previous_node_labels = _snapshot_node_label_index(previous_node_list)
    current_node_labels = _snapshot_node_label_index(current_node_list)
    link_preview = {
        "schema": "relaygraph.workflow_template.link_preview.v1",
        "topology_changed": link_topology_changed,
        "order_changed": link_order_changed,
        "metadata_changed": link_metadata_changed,
        "previous_links": [
            _snapshot_link_preview_item(
                link,
                index=index,
                status="removed" if _snapshot_link_key(link) not in current_link_keys else "same",
                node_labels=previous_node_labels,
            )
            for index, link in enumerate(previous_link_list[:40])
        ],
        "current_links": [
            _snapshot_link_preview_item(
                link,
                index=index,
                status="added" if _snapshot_link_key(link) not in previous_link_keys else "same",
                node_labels=current_node_labels,
            )
            for index, link in enumerate(current_link_list[:40])
        ],
        "added_links": copy.deepcopy(added_links[:24]),
        "removed_links": copy.deepcopy(removed_links[:24]),
        "previous_count": len(previous_link_list),
        "current_count": len(current_link_list),
        "truncated": len(previous_link_list) > 40 or len(current_link_list) > 40,
    }
    return {
        "schema": "relaygraph.workflow_template.snapshot_diff.v1",
        "status": status,
        "changed": changed_count > 0,
        "summary": {
            "changed_count": changed_count,
            "added_node_count": len(added_nodes),
            "removed_node_count": len(removed_nodes),
            "changed_node_count": len(changed_nodes),
            "field_change_count": len(field_changes),
            "agent_change_count": len(agent_added) + len(agent_removed),
            "tool_change_count": len(tool_added) + len(tool_removed),
            "added_link_count": len(added_links),
            "removed_link_count": len(removed_links),
            "link_topology_changed": link_topology_changed,
            "link_order_changed": link_order_changed,
        },
        "workspace_snapshot": {
            "template_id": str(previous.get("template_id") or "").strip(),
            "template_name": str(previous.get("template_name") or "").strip(),
            "created_at": str(previous.get("created_at") or "").strip(),
            "node_count": len(previous_nodes),
            "agent_ids": previous_agents,
            "tool_ids": previous_tools,
        },
        "current_template": {
            "template_id": str(current.get("template_id") or "").strip(),
            "template_name": str(current.get("template_name") or "").strip(),
            "created_at": str(current.get("created_at") or "").strip(),
            "node_count": len(current_nodes),
            "agent_ids": current_agents,
            "tool_ids": current_tools,
        },
        "diff": {
            "added_nodes": added_nodes[:24],
            "removed_nodes": removed_nodes[:24],
            "changed_nodes": changed_nodes[:24],
            "changed_fields": field_changes,
            "added_links": added_links[:24],
            "removed_links": removed_links[:24],
            "agents": {"added": agent_added, "removed": agent_removed},
            "tools": {"added": tool_added, "removed": tool_removed},
        },
        "migration_plan": migration_plan,
        "structure_preview": structure_preview,
        "link_preview": link_preview,
    }

def normalize_workspace_instance_from_template(
    payload: dict[str, Any],
    *,
    template: dict[str, Any],
    agent_definitions: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    template_snapshot = build_template_snapshot(template, agent_definitions, tool_definitions)
    inputs = normalize_workspace_inputs(payload.get("inputs") if isinstance(payload.get("inputs"), dict) else payload, existing=current.get("inputs"))
    chain_source_type, repo_url, paper_url, idea_text = workspace_input_source_summary(inputs)
    source_template = template_snapshot.get("source") if isinstance(template_snapshot.get("source"), dict) else {}
    env_template = template_snapshot.get("env") if isinstance(template_snapshot.get("env"), dict) else {}
    env_payload = payload.get("env") if isinstance(payload.get("env"), dict) else {}
    recipes = template_snapshot.get("recipes") if isinstance(template_snapshot.get("recipes"), list) else []
    template_recipe = recipes[0] if recipes and isinstance(recipes[0], dict) else {}
    recipe = normalize_workspace_recipe(payload, existing=template_recipe)

    workspace_id = str(current.get("id") or "").strip() or (
        datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    )
    brief = str(payload.get("brief") or current.get("brief") or inputs.get("goal_text") or template.get("brief") or "").strip()
    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if brief:
            name = brief.splitlines()[0][:60]
        else:
            name = str(template.get("name") or "新任务实例").strip() or "新任务实例"

    workspace_dir = str(
        payload.get("workspace_dir")
        or current.get("workspace_dir")
        or template.get("workspace_dir")
        or ""
    ).strip()
    env_name = str(payload.get("env_name") or env_payload.get("name") or current.get("env", {}).get("name") or env_template.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_payload.get("manager") or current.get("env", {}).get("manager") or env_template.get("manager") or "").strip()
    python_version = str(payload.get("python_version") or env_payload.get("python") or current.get("env", {}).get("python") or env_template.get("python") or "").strip()

    nodes = normalize_workspace_nodes(
        template_snapshot.get("nodes") if isinstance(template_snapshot.get("nodes"), list) else None,
        chain_source_type,
        brief=brief,
        repo_url=repo_url or str(source_template.get("repo_url") or "").strip(),
        repo_ref=str(source_template.get("repo_ref") or "").strip(),
        paper_url=paper_url or str(source_template.get("paper_url") or "").strip(),
        idea_text=idea_text or str(source_template.get("idea_text") or "").strip(),
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=current.get("nodes") if isinstance(current.get("nodes"), list) else None,
    )
    nodes = sync_workspace_nodes_with_overview(
        nodes,
        brief=brief,
        source_type=chain_source_type,
        repo_url=repo_url or str(source_template.get("repo_url") or "").strip(),
        repo_ref=str(source_template.get("repo_ref") or "").strip(),
        paper_url=paper_url or str(source_template.get("paper_url") or "").strip(),
        idea_text=idea_text or str(source_template.get("idea_text") or "").strip(),
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        recipe_command_overrides={
            key
            for key in ("setup_command", "run_command", "report_command", "schedule")
            if key in payload
        },
    )
    nodes = finalize_agent_executable_nodes(nodes, agent_definitions)
    links = normalize_workspace_links(
        template_snapshot.get("links") if isinstance(template_snapshot.get("links"), list) else None,
        nodes,
    )
    created_at = str(current.get("created_at") or now_iso()).strip() or now_iso()
    source_mode = normalize_source_mode(inputs.get("source_mode") or "")
    source = {
        "type": source_mode,
        "repo_url": repo_url or str(source_template.get("repo_url") or "").strip(),
        "repo_ref": str(source_template.get("repo_ref") or "").strip(),
        "paper_url": paper_url or str(source_template.get("paper_url") or "").strip(),
        "idea_text": idea_text or str(source_template.get("idea_text") or "").strip(),
    }
    model = copy.deepcopy(template_snapshot.get("model") if isinstance(template_snapshot.get("model"), dict) else {})
    agents = copy.deepcopy(template_snapshot.get("agents") if isinstance(template_snapshot.get("agents"), list) else [])
    tools = copy.deepcopy(template_snapshot.get("tools") if isinstance(template_snapshot.get("tools"), list) else [])
    return {
        "id": workspace_id,
        "name": name,
        "status": str(payload.get("status") or current.get("status") or "ready").strip() or "ready",
        "brief": brief,
        "references": parse_line_list(inputs.get("references", [])),
        "inputs": inputs,
        "source": source,
        "workspace_dir": workspace_dir,
        "env": {
            "name": env_name,
            "manager": env_manager,
            "python": python_version,
        },
        "recipes": [recipe],
        "agents": agents,
        "model": model,
        "chat": normalize_workspace_chat(
            payload.get("chat") if "chat" in payload else current.get("chat"),
            existing=current.get("chat"),
        ),
        "tools": tools,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "template_id": str(template.get("id") or "").strip(),
        "template_name": str(template.get("name") or "").strip(),
        "template_snapshot": template_snapshot,
        "execution": copy.deepcopy(current.get("execution") if isinstance(current.get("execution"), dict) else {}),
        "runs": normalize_workspace_execution_runs(current.get("runs")),
        "created_at": created_at,
        "updated_at": now_iso(),
    }
