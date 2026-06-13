from __future__ import annotations

import copy
import re
import uuid
from typing import Any

from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ..errors import WorkspaceWorkflowReadinessError
from ...orchestration.node_runner import AGENT_EXECUTABLE_KINDS
from .agents_tools import workspace_default_agents
from .recipe import normalize_workspace_handler, normalize_workspace_runtime
from ..automation import (
    workspace_has_explicit_input_mapping,
    workspace_io_contract_for_kind,
    workspace_io_input_mapping,
)



def workspace_node_definition(kind: str) -> dict[str, Any]:
    key = str(kind or "").strip()
    definition = WORKSPACE_NODE_LIBRARY.get(key)
    if definition:
        return copy.deepcopy(definition)
    fallback = copy.deepcopy(WORKSPACE_NODE_LIBRARY["custom.step"])
    fallback["title"] = key or fallback["title"]
    return fallback

def workspace_node_kinds_for_source(source_type: str) -> list[str]:
    source = str(source_type or "").strip().lower()
    if source == "repo":
        return [
            "source.repo",
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
    if source == "paper":
        return [
            "source.paper",
            "research.search",
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
    return [
        "source.idea",
        "research.search",
        "repo.clone",
        "path.resolve",
        "repo.inspect",
        "dataset.find",
        "env.infer",
        "env.prepare",
        "gpu.allocate",
        "run.command",
        "artifact.collect",
        "eval.report",
    ]

def should_upgrade_default_workflow_chain(
    template_id: str,
    source_type: str,
    raw_nodes: Any,
) -> bool:
    if str(template_id or "").strip() not in DEFAULT_WORKFLOW_TEMPLATE_IDS:
        return False
    if not isinstance(raw_nodes, list) or not raw_nodes:
        return True
    existing_kinds = [
        str(node.get("kind") or "").strip()
        for node in raw_nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip()
    ]
    expected_kinds = workspace_node_kinds_for_source(source_type)
    return any(kind not in existing_kinds for kind in expected_kinds)

def recommended_node_assignment(kind: str) -> dict[str, str]:
    mapping = {
        "source.repo": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "确认仓库地址、目标分支、成功标准和运行约束。",
        },
        "source.paper": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "补齐论文链接、任务目标和希望复现的指标。",
        },
        "source.idea": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "把目标、限制条件和成功标准写清楚，再交给 Planner 和 Researcher。",
        },
        "research.search": {
            "mode": "agent",
            "role": "researcher",
            "name": "Researcher",
            "handoff": "输出候选仓库、关键依赖、相关文章和可信度说明。",
        },
        "repo.clone": {
            "mode": "system",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "记录克隆目录、分支或提交，并确认代码已经落地。",
        },
        "path.resolve": {
            "mode": "agent",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "输出工作目录、数据目录、日志目录和结果目录的候选路径。",
        },
        "repo.inspect": {
            "mode": "agent",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "产出入口、依赖、默认命令、配置文件和结果目录。",
        },
        "dataset.find": {
            "mode": "agent",
            "role": "researcher",
            "name": "Researcher",
            "handoff": "输出数据集名称、来源、本地路径候选、下载方式和结构要求。",
        },
        "env.infer": {
            "mode": "agent",
            "role": "env_builder",
            "name": "Env Builder",
            "handoff": "输出 Python/CUDA/依赖文件判断和建议安装命令。",
        },
        "env.prepare": {
            "mode": "system",
            "role": "env_builder",
            "name": "Env Builder",
            "handoff": "记录环境名、安装结果、失败依赖和替代方案。",
        },
        "gpu.allocate": {
            "mode": "system",
            "role": "gpu_scout",
            "name": "GPU Scout",
            "handoff": "记录目标服务器、GPU 编号、空闲显存和调度约束。",
        },
        "run.command": {
            "mode": "system",
            "role": "runner",
            "name": "Runner",
            "handoff": "记录服务器、GPU、会话、日志路径和下一步评估入口。",
        },
        "artifact.collect": {
            "mode": "agent",
            "role": "evaluator",
            "name": "Evaluator",
            "handoff": "输出日志、指标、模型文件、运行命令和可复现产物路径。",
        },
        "eval.report": {
            "mode": "agent",
            "role": "evaluator",
            "name": "Evaluator",
            "handoff": "汇总核心指标、主要输出文件、异常和下一步建议。",
        },
        "notify.user": {
            "mode": "agent",
            "role": "reporter",
            "name": "Reporter",
            "handoff": "把关键结论、风险和待确认项反馈给用户。",
        },
    }
    return mapping.get(str(kind or "").strip(), {
        "mode": "human",
        "role": "",
        "name": "你",
        "handoff": "补充这个节点的职责、输入输出和交接要求。",
    })

def workspace_prior_output_keys(nodes: list[dict[str, Any]], index: int) -> set[str]:
    keys: set[str] = set()
    for prior_index, prior_node in enumerate(nodes[:index]):
        if not isinstance(prior_node, dict):
            continue
        prior_kind = str(prior_node.get("kind") or "").strip()
        prior_contract = workspace_io_contract_for_kind(prior_kind, prior_index)
        output_key = str(
            prior_node.get("output_key")
            or (prior_node.get("handler") or {}).get("output_key")
            or prior_contract.get("output_key")
            or ""
        ).strip()
        if output_key:
            keys.add(output_key)
    return keys

def finalize_agent_executable_nodes(
    nodes: list[dict[str, Any]],
    agent_definitions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Ensure agent-backed nodes have handler, output_key and input_mapping for WorkflowRunner."""
    agent_defs = agent_definitions if isinstance(agent_definitions, list) else workspace_default_agents()
    finalized = copy.deepcopy(nodes)
    for index, node in enumerate(finalized):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in AGENT_EXECUTABLE_KINDS:
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        mode = str(handler.get("mode") or "").strip().lower()
        agent_id = str(handler.get("agent_id") or "").strip()
        if mode != "agent" or not agent_id:
            handler = build_recommended_handler(kind, agent_defs)
        contract = workspace_io_contract_for_kind(kind, index)
        output_key = str(
            handler.get("output_key")
            or node.get("output_key")
            or contract.get("output_key")
            or ""
        ).strip()
        if output_key:
            handler["output_key"] = output_key
            node["output_key"] = output_key
        node["handler"] = normalize_workspace_handler(handler)
        if not workspace_has_explicit_input_mapping(node):
            prior_keys = workspace_prior_output_keys(finalized, index)
            default_mapping = dict(AGENT_NODE_DEFAULT_INPUT_MAPPINGS.get(kind) or {})
            if not default_mapping:
                default_mapping = workspace_io_input_mapping(node, contract, index)
                for key, source in list(default_mapping.items()):
                    if str(source or "").startswith("$input.") and str(source).split(".", 1)[-1] in prior_keys:
                        default_mapping[key] = f"$context.outputs.{str(source).split('.', 1)[-1]}"
            else:
                resolved_mapping: dict[str, str] = {}
                for key, source in default_mapping.items():
                    ref = str(source or "").strip()
                    if ref.startswith("$context.outputs."):
                        output_key = ref[len("$context.outputs.") :].split(".", 1)[0]
                        if output_key in prior_keys:
                            resolved_mapping[key] = ref
                        continue
                    resolved_mapping[key] = ref
                default_mapping = resolved_mapping
            if default_mapping:
                node["input_mapping"] = {
                    str(key or "").strip(): str(value or "").strip()
                    for key, value in default_mapping.items()
                    if str(key or "").strip()
                }
    return finalized

def build_recommended_handler(
    kind: str,
    agent_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendation = recommended_node_assignment(kind)
    role = str(recommendation.get("role") or "").strip()
    agent = next(
        (
            item for item in agent_definitions
            if str(item.get("role") or "").strip() == role or str(item.get("id") or "").strip() == role
        ),
        None,
    )
    contract = WORKSPACE_NODE_IO_CONTRACTS.get(str(kind or "").strip(), {})
    output_key = str(contract.get("output_key") or "").strip()
    payload = {
        "mode": str(recommendation.get("mode") or "human"),
        "agent_id": str(agent.get("id") or "").strip() if agent else "",
        "name": str((agent.get("name") if agent else "") or recommendation.get("name") or "").strip(),
        "handoff": str(recommendation.get("handoff") or "").strip(),
    }
    if output_key:
        payload["output_key"] = output_key
    return payload

def workspace_node_default_config(
    kind: str,
    *,
    brief: str,
    source_type: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
) -> dict[str, Any]:
    idea_seed = idea_text or brief
    idea_line = idea_seed.splitlines()[0].strip() if idea_seed else ""
    search_query = paper_url or idea_line or repo_url or repo_name_from_url(repo_url)
    defaults = {
        "source.repo": {
            "repo_url": repo_url,
            "repo_ref": repo_ref,
        },
        "source.paper": {
            "paper_url": paper_url,
        },
        "source.idea": {
            "idea_text": idea_seed,
        },
        "research.search": {
            "query": search_query,
            "goal": "检索相关代码仓库、依赖和运行方式",
            "repo_url": repo_url,
            "paper_url": paper_url,
        },
        "repo.clone": {
            "repo_url": repo_url,
            "repo_ref": repo_ref,
            "workspace_dir": workspace_dir,
        },
        "path.resolve": {
            "workspace_dir": workspace_dir,
            "data_roots": "",
            "output_roots": "runs\noutputs\ncheckpoints\nlogs",
        },
        "repo.inspect": {
            "workspace_dir": workspace_dir,
            "focus_paths": "",
            "questions": "入口、依赖、默认配置、结果目录",
        },
        "dataset.find": {
            "query": search_query,
            "dataset_hints": "",
            "data_roots": "",
            "expected_layout": "",
        },
        "env.infer": {
            "workspace_dir": workspace_dir,
            "manifest_paths": "requirements.txt, pyproject.toml, environment.yml, setup.py",
            "env_name": env_name,
            "python_version": python_version,
        },
        "env.prepare": {
            "workspace_dir": workspace_dir,
            "env_name": env_name,
            "env_manager": env_manager,
            "python_version": python_version,
            "setup_command": str(recipe.get("setup_command") or "").strip(),
        },
        "gpu.allocate": {
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "notes": "",
        },
        "run.command": {
            "workspace_dir": workspace_dir,
            "env_name": env_name,
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "run_command": str(recipe.get("run_command") or "").strip(),
            "schedule": str(recipe.get("schedule") or "").strip(),
        },
        "artifact.collect": {
            "workspace_dir": workspace_dir,
            "artifact_paths": "runs\noutputs\ncheckpoints\nlogs",
            "metric_paths": "",
            "notes": str(recipe.get("notes") or "").strip(),
        },
        "eval.report": {
            "report_command": str(recipe.get("report_command") or "").strip(),
            "metric_paths": "",
            "notes": str(recipe.get("notes") or "").strip(),
        },
        "notify.user": {
            "channel": "ui",
            "message": "",
        },
        "custom.step": {
            "goal": "",
            "command": "",
            "output_expectation": "",
        },
    }
    base = defaults.get(kind) or defaults["custom.step"]
    return copy.deepcopy(base)

def make_workspace_node(
    kind: str,
    title: str,
    *,
    config: dict[str, Any] | None = None,
    node_id: str | None = None,
    position: dict[str, int] | None = None,
    status: str = "draft",
    handler: dict[str, Any] | None = None,
    notes: str = "",
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(node_id or safe_id(f"{kind}-{uuid.uuid4().hex[:8]}")),
        "kind": str(kind),
        "title": str(title),
        "status": str(status or "draft"),
        "config": dict(config or {}),
        "handler": normalize_workspace_handler(handler),
        "notes": str(notes or "").strip(),
        "runtime": normalize_workspace_runtime(runtime),
        "position": {
            "x": safe_int((position or {}).get("x"), 0),
            "y": safe_int((position or {}).get("y"), 0),
        },
    }

def normalize_workspace_nodes(
    raw_nodes: list[dict[str, Any]] | None,
    source_type: str,
    *,
    brief: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
    existing_nodes: list[dict[str, Any]] | None = None,
    use_default_chain: bool = False,
) -> list[dict[str, Any]]:
    existing_by_id: dict[str, dict[str, Any]] = {}
    if existing_nodes:
        for node in existing_nodes:
            if isinstance(node, dict) and str(node.get("id") or "").strip():
                existing_by_id[str(node.get("id")).strip()] = node

    defaults = raw_nodes if raw_nodes and not use_default_chain else None
    if defaults is None:
        defaults = [{"kind": kind} for kind in workspace_node_kinds_for_source(source_type)]

    nodes: list[dict[str, Any]] = []
    for index, raw in enumerate(defaults):
        if not isinstance(raw, dict):
            continue
        raw_kind = str(raw.get("kind") or "").strip()
        if not raw_kind:
            continue
        existing = existing_by_id.get(str(raw.get("id") or "").strip(), {})
        definition = workspace_node_definition(raw_kind)
        config = definition.get("config_defaults", {})
        if isinstance(config, dict):
            config = copy.deepcopy(config)
        else:
            config = {}
        config.update(
            workspace_node_default_config(
                raw_kind,
                brief=brief,
                source_type=source_type,
                repo_url=repo_url,
                repo_ref=repo_ref,
                paper_url=paper_url,
                idea_text=idea_text,
                workspace_dir=workspace_dir,
                env_name=env_name,
                env_manager=env_manager,
                python_version=python_version,
                recipe=recipe,
            )
        )
        if isinstance(existing.get("config"), dict):
            config.update(existing["config"])
        if isinstance(raw.get("config"), dict):
            config.update(raw["config"])
        node = make_workspace_node(
            raw_kind,
            str(raw.get("title") or existing.get("title") or definition.get("title") or raw_kind).strip() or raw_kind,
            config=config,
            node_id=str(raw.get("id") or existing.get("id") or "").strip() or None,
            position=(
                raw.get("position")
                if isinstance(raw.get("position"), dict)
                else existing.get("position")
                if isinstance(existing.get("position"), dict)
                else {"x": index * 240, "y": 0}
            ),
            status=str(raw.get("status") or existing.get("status") or "draft").strip() or "draft",
            handler=raw.get("handler") if raw.get("handler") is not None else existing.get("handler"),
            notes=str(raw.get("notes") or existing.get("notes") or "").strip(),
            runtime=raw.get("runtime") if raw.get("runtime") is not None else existing.get("runtime"),
        )
        input_mapping = (
            raw.get("input_mapping")
            if isinstance(raw.get("input_mapping"), dict)
            else existing.get("input_mapping")
            if isinstance(existing.get("input_mapping"), dict)
            else {}
        )
        if input_mapping:
            node["input_mapping"] = {
                str(key or "").strip(): str(value or "").strip()
                for key, value in input_mapping.items()
                if str(key or "").strip()
            }
        output_key = str(raw.get("output_key") or existing.get("output_key") or "").strip()
        if output_key:
            node["output_key"] = output_key
        nodes.append(node)

    if nodes:
        return nodes
    return normalize_workspace_nodes(
        [{"kind": kind} for kind in workspace_node_kinds_for_source(source_type)],
        source_type,
        brief=brief,
        repo_url=repo_url,
        repo_ref=repo_ref,
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=existing_nodes,
    )

def normalize_workspace_links(
    raw_links: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    node_ids = [str(node.get("id") or "").strip() for node in nodes if str(node.get("id") or "").strip()]
    valid_ids = set(node_ids)
    seen: set[tuple[str, str]] = set()
    links: list[dict[str, Any]] = []
    if raw_links:
        for index, raw in enumerate(raw_links):
            if not isinstance(raw, dict):
                continue
            from_id = str(raw.get("from") or "").strip()
            to_id = str(raw.get("to") or "").strip()
            if from_id not in valid_ids or to_id not in valid_ids or from_id == to_id:
                continue
            pair = (from_id, to_id)
            if pair in seen:
                continue
            seen.add(pair)
            links.append(
                {
                    "id": safe_id(str(raw.get("id") or f"link-{index + 1}-{from_id}-{to_id}")),
                    "from": from_id,
                    "to": to_id,
                }
            )
    if links:
        return links
    for index in range(len(node_ids) - 1):
        from_id = node_ids[index]
        to_id = node_ids[index + 1]
        links.append(
            {
                "id": safe_id(f"link-{index + 1}-{from_id}-{to_id}"),
                "from": from_id,
                "to": to_id,
            }
        )
    return links

def sync_workspace_nodes_with_overview(
    nodes: list[dict[str, Any]],
    *,
    brief: str,
    source_type: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
    recipe_command_overrides: set[str] | None = None,
) -> list[dict[str, Any]]:
    synced = copy.deepcopy(nodes)
    force_recipe_commands = recipe_command_overrides is None
    recipe_command_overrides = recipe_command_overrides or set()

    def sync_recipe_command(config: dict[str, Any], key: str) -> None:
        value = str(recipe.get(key) or "").strip()
        if force_recipe_commands or key in recipe_command_overrides:
            config[key] = value
        elif value and not str(config.get(key) or "").strip():
            config[key] = value

    idea_seed = idea_text or brief
    idea_line = idea_seed.splitlines()[0].strip() if idea_seed else ""
    source_index = next((idx for idx, node in enumerate(synced) if str(node.get("kind") or "").startswith("source.")), -1)
    search_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "research.search"), -1)
    clone_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "repo.clone"), -1)
    path_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "path.resolve"), -1)
    inspect_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "repo.inspect"), -1)
    dataset_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "dataset.find"), -1)
    env_infer_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "env.infer"), -1)
    env_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "env.prepare"), -1)
    gpu_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "gpu.allocate"), -1)
    run_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "run.command"), -1)
    artifact_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "artifact.collect"), -1)
    eval_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "eval.report"), -1)
    if source_index >= 0:
        node = synced[source_index]
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        if node.get("kind") == "source.repo":
            config.update({"repo_url": repo_url, "repo_ref": repo_ref})
        elif node.get("kind") == "source.paper":
            config.update({"paper_url": paper_url})
        elif node.get("kind") == "source.idea":
            config.update({"idea_text": idea_seed})
        node["config"] = config
    if search_index >= 0:
        config = synced[search_index].get("config") if isinstance(synced[search_index].get("config"), dict) else {}
        config.update({"repo_url": repo_url, "paper_url": paper_url, "source_type": source_type})
        if not str(config.get("query") or "").strip():
            config["query"] = paper_url or idea_line or repo_url
        synced[search_index]["config"] = config
    if clone_index >= 0:
        config = synced[clone_index].get("config") if isinstance(synced[clone_index].get("config"), dict) else {}
        config.update({"repo_url": repo_url, "repo_ref": repo_ref, "workspace_dir": workspace_dir})
        synced[clone_index]["config"] = config
    if path_index >= 0:
        config = synced[path_index].get("config") if isinstance(synced[path_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[path_index]["config"] = config
    if inspect_index >= 0:
        config = synced[inspect_index].get("config") if isinstance(synced[inspect_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[inspect_index]["config"] = config
    if dataset_index >= 0:
        config = synced[dataset_index].get("config") if isinstance(synced[dataset_index].get("config"), dict) else {}
        if not str(config.get("query") or "").strip():
            config["query"] = paper_url or idea_line or repo_url
        synced[dataset_index]["config"] = config
    if env_infer_index >= 0:
        config = synced[env_infer_index].get("config") if isinstance(synced[env_infer_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir, "env_name": env_name, "python_version": python_version})
        synced[env_infer_index]["config"] = config
    if env_index >= 0:
        config = synced[env_index].get("config") if isinstance(synced[env_index].get("config"), dict) else {}
        config.update(
            {
                "workspace_dir": workspace_dir,
                "env_name": env_name,
                "env_manager": env_manager,
                "python_version": python_version,
            }
        )
        sync_recipe_command(config, "setup_command")
        synced[env_index]["config"] = config
    if gpu_index >= 0:
        config = synced[gpu_index].get("config") if isinstance(synced[gpu_index].get("config"), dict) else {}
        if not str(config.get("gpu_policy") or "").strip():
            config["gpu_policy"] = "auto"
        synced[gpu_index]["config"] = config
    if run_index >= 0:
        config = synced[run_index].get("config") if isinstance(synced[run_index].get("config"), dict) else {}
        config.update(
            {
                "workspace_dir": workspace_dir,
                "env_name": env_name,
            }
        )
        sync_recipe_command(config, "run_command")
        sync_recipe_command(config, "schedule")
        synced[run_index]["config"] = config
    if artifact_index >= 0:
        config = synced[artifact_index].get("config") if isinstance(synced[artifact_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[artifact_index]["config"] = config
    if eval_index >= 0:
        config = synced[eval_index].get("config") if isinstance(synced[eval_index].get("config"), dict) else {}
        sync_recipe_command(config, "report_command")
        synced[eval_index]["config"] = config
    return synced
