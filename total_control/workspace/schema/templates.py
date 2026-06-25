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
    env_name = str(payload.get("env_name") or env_current.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_current.get("manager") or "").strip()
    python_version = str(payload.get("python_version") or env_current.get("python") or "").strip()

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
    env_name = str(payload.get("env_name") or current.get("env", {}).get("name") or env_template.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or current.get("env", {}).get("manager") or env_template.get("manager") or "").strip()
    python_version = str(payload.get("python_version") or current.get("env", {}).get("python") or env_template.get("python") or "").strip()

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
