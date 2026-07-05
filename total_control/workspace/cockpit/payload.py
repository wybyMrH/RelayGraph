"""Cockpit — payload helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .commands import infer_workspace_run_command, infer_workspace_setup_command
from .discovery import (
    infer_workspace_data_roots,
    infer_workspace_dir_from_inputs,
    workspace_default_name_seed,
)
from .scheduler import (
    apply_workspace_config_value,
    apply_workspace_scheduler_config_value,
    derive_workspace_scheduler_values,
    workspace_scheduler_values_from_candidate,
)

def apply_workspace_automation_defaults_to_payload(
    workspace: dict[str, Any],
    statuses: list[dict[str, Any]],
    *,
    force: bool = False,
    scheduler_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    applied: list[dict[str, Any]] = []
    current_tools = normalize_workspace_tools(updated.get("tools"), existing=updated.get("tools"))
    required_tool_ids = workspace_required_default_tool_ids(updated)
    current_tools, default_tool_applied = backfill_default_tool_definitions(
        current_tools,
        required_tool_ids=required_tool_ids,
    )
    if default_tool_applied:
        updated["tools"] = current_tools
        applied.extend(default_tool_applied)
    tool_ids = [str(item.get("id") or "").strip() for item in current_tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
    current_agents = normalize_workspace_agents(
        updated.get("agents"),
        existing=updated.get("agents"),
        tool_ids=tool_ids,
    )
    current_agents, default_agent_applied = backfill_default_agent_tools(
        current_agents,
        tool_ids=tool_ids,
    )
    if default_agent_applied:
        updated["agents"] = current_agents
        applied.extend(default_agent_applied)
    workspace_dir = infer_workspace_dir_from_inputs(updated)
    if workspace_dir and (force or not str(updated.get("workspace_dir") or "").strip()):
        updated["workspace_dir"] = workspace_dir
        applied.append({"field": "workspace_dir", "label": "工作目录", "value": workspace_dir})
    else:
        workspace_dir = str(updated.get("workspace_dir") or workspace_dir or "").strip()

    env = updated.get("env") if isinstance(updated.get("env"), dict) else {}
    env_name = str(env.get("name") or "").strip()
    if (force or not env_name) and workspace_default_name_seed(updated):
        env_name = f"rg-{safe_id(workspace_default_name_seed(updated))}"[:64]
        env["name"] = env_name
        applied.append({"field": "env.name", "label": "环境名", "value": env_name})
    updated["env"] = env

    data_roots = infer_workspace_data_roots(updated, workspace_dir)
    setup_command = infer_workspace_setup_command(workspace_dir)
    run_command = infer_workspace_run_command(workspace_dir)
    report_command = "echo '[eval.report] inspect metrics, results and reports'"
    scheduler_values = derive_workspace_scheduler_values(updated, statuses)
    explicit_scheduler_values = workspace_scheduler_values_from_candidate(
        scheduler_candidate,
        scheduler_values.get("scheduler") if isinstance(scheduler_values.get("scheduler"), dict) else {},
    )
    if explicit_scheduler_values.get("server_id"):
        scheduler_values.update(explicit_scheduler_values)
    artifact_paths = "runs\noutputs\ncheckpoints\nlogs"

    for node in (updated.get("nodes") if isinstance(updated.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        if workspace_dir and kind in {"repo.clone", "path.resolve", "repo.inspect", "env.infer", "env.prepare", "run.command", "artifact.collect"}:
            apply_workspace_config_value(config, "workspace_dir", workspace_dir, applied, f"{kind} 工作目录", force=force)
        if env_name and kind in {"env.infer", "env.prepare", "run.command"}:
            apply_workspace_config_value(config, "env_name", env_name, applied, f"{kind} 环境名", force=force)
        if kind == "path.resolve":
            apply_workspace_config_value(config, "data_roots", "\n".join(data_roots), applied, "数据根目录", force=force)
            apply_workspace_config_value(config, "output_roots", artifact_paths, applied, "输出目录", force=force)
        elif kind == "dataset.find":
            source = updated.get("source") if isinstance(updated.get("source"), dict) else {}
            query = str(source.get("repo_url") or source.get("paper_url") or updated.get("brief") or updated.get("name") or "").strip()
            apply_workspace_config_value(config, "query", query, applied, "数据集检索词", force=force)
            apply_workspace_config_value(config, "data_roots", "\n".join(data_roots), applied, "数据候选根", force=force)
            if data_roots:
                apply_workspace_config_value(config, "dataset_hints", "\n".join(data_roots), applied, "数据集线索", force=force)
        elif kind == "env.infer":
            apply_workspace_config_value(
                config,
                "manifest_paths",
                "requirements.txt, pyproject.toml, environment.yml, conda.yml, setup.py",
                applied,
                "环境清单候选",
                force=force,
            )
        elif kind == "env.prepare":
            apply_workspace_config_value(config, "setup_command", setup_command, applied, "环境安装命令", force=force)
        elif kind == "gpu.allocate":
            if scheduler_values.get("server_id"):
                apply_workspace_scheduler_config_value(config, "server_id", scheduler_values["server_id"], applied, "调度服务器", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_policy", scheduler_values["gpu_policy"], applied, "调度 GPU 策略", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_index", scheduler_values["gpu_index"], applied, "调度 GPU 编号", force=force)
                if scheduler_values.get("min_free_memory_gib"):
                    apply_workspace_scheduler_config_value(config, "min_free_memory_gib", scheduler_values["min_free_memory_gib"], applied, "最低空闲显存", force=force)
        elif kind == "run.command":
            if scheduler_values.get("server_id"):
                apply_workspace_scheduler_config_value(config, "server_id", scheduler_values["server_id"], applied, "运行服务器", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_policy", scheduler_values["gpu_policy"], applied, "运行 GPU 策略", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_index", scheduler_values["gpu_index"], applied, "运行 GPU 编号", force=force)
                if scheduler_values.get("min_free_memory_gib"):
                    apply_workspace_scheduler_config_value(config, "min_free_memory_gib", scheduler_values["min_free_memory_gib"], applied, "运行最低空闲显存", force=force)
            apply_workspace_config_value(config, "run_command", run_command, applied, "运行命令", force=force)
        elif kind == "artifact.collect":
            apply_workspace_config_value(config, "artifact_paths", artifact_paths, applied, "产物路径", force=force)
            apply_workspace_config_value(config, "metric_paths", "metrics\nresults\nreports", applied, "指标路径", force=force)
        elif kind == "eval.report":
            apply_workspace_config_value(config, "metric_paths", "metrics\nresults\nreports", applied, "报告指标路径", force=force)
            apply_workspace_config_value(config, "report_command", report_command, applied, "报告命令", force=force)
        node["config"] = config
    updated["updated_at"] = now_iso()
    return updated, applied

def apply_workspace_job_runtime(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    copy_workspace = copy.deepcopy(workspace)
    workspace_id = str(copy_workspace.get("id") or "").strip()
    if not workspace_id:
        return copy_workspace
    for node in copy_workspace.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        runtime = normalize_workspace_runtime(node.get("runtime"))
        matches = [
            job for job in jobs
            if workspace_job_binding(job) == (workspace_id, node_id)
        ]
        if matches:
            matches.sort(key=workspace_job_sort_key, reverse=True)
            latest = matches[0]
            runtime.update(
                {
                    "run_count": len(matches),
                    "last_job_id": str(latest.get("id") or "").strip(),
                    "last_job_name": str(latest.get("name") or "").strip(),
                    "last_job_kind": str(latest.get("kind") or "").strip(),
                    "last_job_status": str(latest.get("status") or "").strip(),
                    "last_run_at": str(latest.get("started_at") or latest.get("created_at") or "").strip(),
                    "last_finished_at": str(latest.get("finished_at") or "").strip(),
                    "last_error": str(latest.get("error") or "").strip(),
                }
            )
        node["runtime"] = runtime
    return copy_workspace

def clean_workspace_placeholder_config_values(workspace: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(workspace)
    for node in updated.get("nodes", []) if isinstance(updated.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        node["config"] = {
            key: clean_workspace_config_default(kind, key, value)
            for key, value in config.items()
        }
    return updated

def normalize_workspace_payload(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    source_current = current.get("source") if isinstance(current.get("source"), dict) else {}
    env_current = current.get("env") if isinstance(current.get("env"), dict) else {}
    env_payload = payload.get("env") if isinstance(payload.get("env"), dict) else {}
    recipes_current = current.get("recipes") if isinstance(current.get("recipes"), list) else []
    recipe_existing = recipes_current[0] if recipes_current and isinstance(recipes_current[0], dict) else None

    source_type = normalize_source_mode(
        str(payload.get("source_type") or source_current.get("type") or "repo").strip().lower()
    )

    repo_url = str(payload.get("repo_url") or source_current.get("repo_url") or "").strip()
    paper_url = str(payload.get("paper_url") or source_current.get("paper_url") or "").strip()
    idea_text = str(payload.get("idea_text") or source_current.get("idea_text") or "").strip()
    brief = str(payload.get("brief") or current.get("brief") or "").strip()

    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if repo_url:
            name = repo_name_from_url(repo_url)
        elif paper_url:
            name = "Paper Workspace"
        elif brief:
            name = brief.splitlines()[0][:40]
        elif idea_text:
            name = idea_text.splitlines()[0][:40]
        else:
            name = "新工作区"

    workspace_id = str(current.get("id") or "").strip() or (
        datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    )
    recipe = normalize_workspace_recipe(payload, existing=recipe_existing)
    created_at = str(current.get("created_at") or "").strip() or now_iso()
    status = str(payload.get("status") or current.get("status") or "draft").strip() or "draft"
    workspace_dir = str(payload.get("workspace_dir") or current.get("workspace_dir") or "").strip()
    env_name = str(payload.get("env_name") or env_payload.get("name") or env_current.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_payload.get("manager") or env_current.get("manager") or "").strip()
    python_version = str(payload.get("python_version") or env_payload.get("python") or env_current.get("python") or "").strip()
    raw_nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else None
    raw_links = payload.get("links") if isinstance(payload.get("links"), list) else None
    raw_tools = payload.get("tools") if isinstance(payload.get("tools"), list) else None
    rebuild_graph = bool(payload.get("rebuild_graph"))
    node_payload = raw_nodes
    if node_payload is None and not rebuild_graph and isinstance(current.get("nodes"), list):
        node_payload = current.get("nodes")
    tools = normalize_workspace_tools(
        raw_tools if raw_tools is not None else current.get("tools"),
        existing=current.get("tools") if isinstance(current.get("tools"), list) else None,
    )
    tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
    nodes = normalize_workspace_nodes(
        node_payload,
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
        use_default_chain=rebuild_graph,
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
    nodes = finalize_agent_executable_nodes(nodes, workspace_default_agents())
    if raw_links is None and not rebuild_graph:
        raw_links = current.get("links") if isinstance(current.get("links"), list) else None
    links = normalize_workspace_links(raw_links, nodes)
    agents = normalize_workspace_agents(
        payload.get("agents") if "agents" in payload else current.get("agents"),
        existing=current.get("agents"),
        tool_ids=tool_ids,
    )
    model = normalize_workspace_model(
        payload.get("model") if "model" in payload else current.get("model"),
        existing=current.get("model"),
    )
    chat = normalize_workspace_chat(
        payload.get("chat") if "chat" in payload else current.get("chat"),
        existing=current.get("chat"),
    )
    inputs = normalize_workspace_inputs(
        payload.get("inputs") if isinstance(payload.get("inputs"), dict) else payload,
        existing=current.get("inputs"),
    )
    template_snapshot = payload.get("template_snapshot") if isinstance(payload.get("template_snapshot"), dict) else current.get("template_snapshot")
    execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else current.get("execution")
    automation = payload.get("automation") if isinstance(payload.get("automation"), dict) else current.get("automation")
    runs = payload.get("runs") if isinstance(payload.get("runs"), list) else current.get("runs")

    return {
        "id": workspace_id,
        "name": name,
        "status": status,
        "brief": brief,
        "references": parse_line_list(payload.get("references", current.get("references", []))),
        "inputs": inputs,
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
        "agents": agents,
        "model": model,
        "chat": chat,
        "tools": tools,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "template_id": str(payload.get("template_id") or current.get("template_id") or "").strip(),
        "template_name": str(payload.get("template_name") or current.get("template_name") or "").strip(),
        "template_snapshot": copy.deepcopy(template_snapshot) if isinstance(template_snapshot, dict) else {},
        "execution": copy.deepcopy(execution) if isinstance(execution, dict) else {},
        "automation": copy.deepcopy(automation) if isinstance(automation, dict) else {},
        "runs": normalize_workspace_execution_runs(runs),
        "created_at": created_at,
        "updated_at": now_iso(),
    }
