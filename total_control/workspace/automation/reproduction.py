from __future__ import annotations

from ._deps import *  # noqa: F403
from .bundle import (
    workspace_checkout_command,
    workspace_execution_bundle_command_script,
    workspace_execution_bundle_missing_item,
    workspace_execution_bundle_step,
    workspace_execution_package_manifest,
)
from .deployment import workspace_delivery_contract, workspace_deployment_plan
from .evidence import workspace_evidence_group


def workspace_reproduction_manifest_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    value: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    evidence_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "value": compact_workspace_command(str(value or "").strip(), limit=180),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
    }

def workspace_reproduction_intent(workspace: dict[str, Any]) -> dict[str, str]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    text = " ".join(
        [
            str(inputs.get("goal_text") or ""),
            str(source.get("idea_text") or ""),
            str(workspace.get("brief") or ""),
            str(workspace.get("name") or ""),
        ]
    ).lower()
    deploy_tokens = ["部署", "deploy", "serve", "service", "api", "docker", "上线"]
    reproduce_tokens = ["复现", "reproduce", "baseline", "paper", "实验", "指标"]
    deploy = any(token in text for token in deploy_tokens)
    reproduce = any(token in text for token in reproduce_tokens)
    if deploy and reproduce:
        mode = "mixed"
        label = "复现 + 部署"
    elif deploy:
        mode = "deploy"
        label = "自动部署"
    else:
        mode = "reproduce"
        label = "自动复现"
    return {
        "mode": mode,
        "label": label,
        "source_type": str(inputs.get("source_mode") or source.get("type") or "idea").strip() or "idea",
    }

def derive_workspace_reproduction_manifest(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    resource_orchestration: dict[str, Any],
    dataset_discovery: dict[str, Any],
    execution_context: dict[str, Any],
) -> dict[str, Any]:
    from ..cockpit.discovery import derive_workspace_dataset_discovery_plan, workspace_dataset_discovery_bundle_command

    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    resource_items = resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else []
    resource_index = {
        str(item.get("id") or "").strip(): item
        for item in resource_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    context_totals = execution_context.get("totals") if isinstance(execution_context.get("totals"), dict) else {}
    repo_urls = inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else []
    paper_urls = inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else []
    references = inputs.get("references") if isinstance(inputs.get("references"), list) else []
    source_value = (
        repo_urls[0] if repo_urls else
        paper_urls[0] if paper_urls else
        str(inputs.get("goal_text") or source.get("repo_url") or source.get("paper_url") or source.get("idea_text") or workspace.get("brief") or "").strip()
    )
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    env_prepare_config = workspace_node_config_by_kind(workspace, "env.prepare")
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")
    eval_config = workspace_node_config_by_kind(workspace, "eval.report")
    data_roots = workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots"))
    output_roots = workspace_config_values(path_config.get("output_roots"))
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints"))
    dataset_plan = dataset_discovery if isinstance(dataset_discovery, dict) else derive_workspace_dataset_discovery_plan(workspace, execution, evidence)
    dataset_queries = dataset_plan.get("queries") if isinstance(dataset_plan.get("queries"), list) else []
    dataset_roots = dataset_plan.get("local_roots") if isinstance(dataset_plan.get("local_roots"), list) else []
    dataset_sources = dataset_plan.get("source_refs") if isinstance(dataset_plan.get("source_refs"), list) else []
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths"))
    metric_paths = workspace_config_values(artifact_config.get("metric_paths")) + workspace_config_values(eval_config.get("metric_paths"))
    setup_command = str(env_prepare_config.get("setup_command") or "").strip()
    run_command = str(run_config.get("run_command") or "").strip()
    report_command = str(eval_config.get("report_command") or "").strip()
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip() or "auto"
    resource_candidates = resource_orchestration.get("resource_candidates") if isinstance(resource_orchestration.get("resource_candidates"), dict) else {}
    evidence_count = sum(safe_int(group.get("count"), 0) for group in evidence if isinstance(group, dict))
    metric_count = safe_int(workspace_evidence_group(evidence, "metric").get("count"), 0)
    artifact_count = safe_int(workspace_evidence_group(evidence, "artifact").get("count"), 0)
    source_check = check_index.get("source", {})
    path_item = resource_index.get("paths", {})
    dataset_item = resource_index.get("dataset", {})
    env_item = resource_index.get("env", {})
    gpu_item = resource_index.get("gpu", {})
    run_item = resource_index.get("run", {})
    artifact_item = resource_index.get("artifact", {})
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    node_by_kind = {
        str(node.get("kind") or "").strip(): str(node.get("id") or "").strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip()
    }
    source_node_id = next(
        (
            str(node.get("id") or "").strip()
            for node in nodes
            if isinstance(node, dict)
            and str(node.get("kind") or "").strip() in {"source.repo", "source.paper", "source.idea", "research.search"}
        ),
        "",
    )
    manifest_items = [
        workspace_reproduction_manifest_item(
            "source",
            "目标/来源",
            str(source_check.get("status") or "draft"),
            str(source_check.get("title") or "等待目标输入"),
            source_value or "等待目标、repo 或论文",
            f"{len(repo_urls)} repo · {len(paper_urls)} paper · {len(references)} 参考",
            str(source_check.get("action") or "补目标、repo、论文、数据路径或约束。"),
            node_id=source_node_id,
        ),
        workspace_reproduction_manifest_item(
            "checkout",
            "源码/路径",
            str(path_item.get("status") or "warning"),
            str(path_item.get("title") or ("工作目录已设置" if workspace_dir else "路径等待解析")),
            workspace_dir or str(path_item.get("value") or ""),
            f"{len(data_roots)} 数据根 · {len(output_roots)} 输出根",
            str(path_item.get("action") or "运行 path.resolve 或补 workspace_dir/data_roots/output_roots。"),
            node_kind="path.resolve",
            node_id=node_by_kind.get("path.resolve", ""),
            evidence_count=safe_int(path_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "dataset",
            "数据集",
            str(dataset_item.get("status") or dataset_plan.get("status") or "warning"),
            str(dataset_item.get("title") or ("发现计划已生成" if dataset_queries or dataset_roots else "缺数据集线索")),
            str(dataset_item.get("value") or (dataset_hints[0] if dataset_hints else dataset_queries[0] if dataset_queries else dataset_roots[0] if dataset_roots else "")),
            f"{len(dataset_queries)} 查询 · {len(dataset_roots)} 本地根 · {len(dataset_sources)} 资料入口 · {len(dataset_hints)} 手动线索",
            str(dataset_item.get("action") or (dataset_plan.get("next_action") or {}).get("detail") or "运行 dataset.find 或补数据集名称、本地路径、下载页。"),
            node_kind="dataset.find",
            node_id=node_by_kind.get("dataset.find", ""),
            evidence_count=safe_int(dataset_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "environment",
            "环境",
            str(env_item.get("status") or "warning"),
            str(env_item.get("title") or ("环境入口已具备" if setup_command or env.get("name") else "缺环境入口")),
            setup_command or str(env.get("name") or env_item.get("value") or ""),
            f"{env.get('manager') or 'conda'} · Python {env.get('python') or '待定'}",
            str(env_item.get("action") or "运行 env.infer/env.prepare 或补 setup_command。"),
            node_kind="env.prepare",
            node_id=node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", ""),
            evidence_count=safe_int(env_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "gpu",
            "GPU/服务器",
            str(gpu_item.get("status") or "warning"),
            str(gpu_item.get("title") or "GPU 快照不足"),
            str(gpu_item.get("value") or resource_candidates.get("recommended_server_id") or "auto"),
            f"policy={gpu_policy} · 空闲 GPU {safe_int(resource_candidates.get('idle_gpu_count'), 0)}/{safe_int(resource_candidates.get('gpu_count'), 0)}",
            str(gpu_item.get("action") or "刷新资源或设置 server_id/gpu_policy/min_free_memory_gib。"),
            node_kind="gpu.allocate",
            node_id=node_by_kind.get("gpu.allocate", ""),
            evidence_count=safe_int(gpu_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "run",
            "运行/部署入口",
            str(run_item.get("status") or "blocked"),
            str(run_item.get("title") or ("运行命令已设置" if run_command else "缺 run command")),
            run_command or "等待可提交命令",
            str(run_plan.get("summary") or "等待运行预案"),
            str(run_item.get("action") or "补 run.command，或运行发现链让 Agent 推断入口。"),
            node_kind="run.command",
            node_id=node_by_kind.get("run.command", ""),
        ),
        workspace_reproduction_manifest_item(
            "artifacts",
            "产物/指标",
            str(artifact_item.get("status") or "warning"),
            str(artifact_item.get("title") or ("产物入口已设置" if artifact_paths or metric_paths else "缺产物路径")),
            str(artifact_item.get("value") or (artifact_paths[0] if artifact_paths else metric_paths[0] if metric_paths else "")),
            f"{len(artifact_paths)} 产物路径 · {len(metric_paths)} 指标路径 · {artifact_count} 产物证据 · {metric_count} 指标证据",
            str(artifact_item.get("action") or "运行 artifact.collect/eval.report，收集 logs、checkpoints、metrics。"),
            node_kind="artifact.collect",
            node_id=node_by_kind.get("artifact.collect", ""),
            evidence_count=safe_int(artifact_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "report",
            "报告/交付",
            "ready" if metric_count or report_command else "warning",
            "可以整理报告" if metric_count or report_command else "等待报告入口",
            report_command or "等待 eval.report / 指标证据",
            f"{safe_int(context_totals.get('produced_output_count'), 0)} 个上下文输出已产生 · {evidence_count} 条证据",
            "运行 eval.report 或让报告 Agent 汇总命令、指标、产物和失败原因。",
            node_kind="eval.report",
            node_id=node_by_kind.get("eval.report", ""),
            evidence_count=metric_count,
        ),
    ]
    status_counts: dict[str, int] = {}
    for item in manifest_items:
        status = str(item.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    hard_blockers = [
        item for item in manifest_items
        if str(item.get("id") or "") in {"source", "run"} and str(item.get("status") or "") in {"blocked", "failed", "draft"}
    ]
    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    if status_counts.get("failed") or hard_blockers or run_blocking:
        status = "blocked"
    elif status_counts.get("running"):
        status = "running"
    elif status_counts.get("blocked"):
        status = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    next_item = next(
        (
            item for item in manifest_items
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        manifest_items[-1] if manifest_items else {},
    )
    intent = workspace_reproduction_intent(workspace)
    delivery_contract = workspace_delivery_contract(
        workspace,
        intent,
        run_command=run_command,
        setup_command=setup_command,
        artifact_paths=artifact_paths,
        metric_paths=metric_paths,
    )
    ready_count = status_counts.get("ready", 0) + status_counts.get("done", 0)
    checkout_source = copy.deepcopy(source)
    if not str(checkout_source.get("repo_url") or "").strip() and repo_urls:
        checkout_source["repo_url"] = repo_urls[0]
    checkout_command = workspace_checkout_command(checkout_source, workspace_dir)
    recommended_server_id = str(resource_candidates.get("recommended_server_id") or gpu_config.get("server_id") or run_config.get("server_id") or "auto").strip() or "auto"
    recommended_gpu_index = str(resource_candidates.get("recommended_gpu_index") or "").strip()
    cuda_env = {}
    if recommended_gpu_index and gpu_policy.lower() not in {"cpu", "none", "no_gpu"}:
        cuda_env["CUDA_VISIBLE_DEVICES"] = recommended_gpu_index
    command_env = {
        **cuda_env,
        **({"CONDA_DEFAULT_ENV": str(env.get("name") or "").strip()} if str(env.get("name") or "").strip() else {}),
    }
    dataset_command = workspace_dataset_discovery_bundle_command(dataset_plan)
    bundle_steps = [
        workspace_execution_bundle_step(
            "checkout",
            "准备源码/路径",
            checkout_command,
            "ready" if checkout_command or workspace_dir else "warning",
            "克隆或确认工作目录，后续节点都以这里作为 cwd。",
            node_kind="repo.clone",
            node_id=node_by_kind.get("repo.clone", "") or node_by_kind.get("path.resolve", ""),
            cwd=os.path.dirname(workspace_dir.rstrip("/")) if workspace_dir else "",
        ),
        workspace_execution_bundle_step(
            "dataset",
            "定位数据集",
            dataset_command,
            "ready" if str(dataset_plan.get("status") or "") in {"ready", "done"} else "warning",
            str(dataset_plan.get("summary") or "从目标、论文、README、参考路径和本地数据根定位数据集。"),
            node_kind="dataset.find",
            node_id=node_by_kind.get("dataset.find", ""),
            cwd=workspace_dir,
        ),
        workspace_execution_bundle_step(
            "setup",
            "准备环境",
            setup_command,
            "ready" if setup_command else "warning",
            "安装依赖或激活环境；缺失时先运行 env.infer/env.prepare。",
            node_kind="env.prepare",
            node_id=node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", ""),
            cwd=workspace_dir,
            env={"CONDA_DEFAULT_ENV": str(env.get("name") or "").strip()},
        ),
        workspace_execution_bundle_step(
            "run",
            "运行/部署",
            run_command,
            "ready" if run_command and str(run_plan.get("status") or "") == "ready" else "blocked" if not run_command else "warning",
            "提交核心训练、推理、服务启动或 smoke test 命令。",
            node_kind="run.command",
            node_id=node_by_kind.get("run.command", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
        workspace_execution_bundle_step(
            "collect",
            "收集产物",
            " && ".join([f"find {shlex.quote(path)} -maxdepth 2 -type f | head -50" for path in (artifact_paths + metric_paths)[:4]]),
            "ready" if artifact_paths or metric_paths else "warning",
            "回收 logs、checkpoints、outputs、metrics，供报告和下游复跑使用。",
            node_kind="artifact.collect",
            node_id=node_by_kind.get("artifact.collect", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
        workspace_execution_bundle_step(
            "report",
            "整理报告",
            report_command,
            "ready" if report_command or metric_count else "warning",
            "汇总指标、产物、命令、资源占用和失败原因。",
            node_kind="eval.report",
            node_id=node_by_kind.get("eval.report", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
    ]
    path_node_id = node_by_kind.get("path.resolve", "") or node_by_kind.get("repo.clone", "")
    env_node_id = node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", "")
    gpu_node_id = node_by_kind.get("gpu.allocate", "")
    run_node_id = node_by_kind.get("run.command", "")
    artifact_node_id = node_by_kind.get("artifact.collect", "") or node_by_kind.get("eval.report", "")
    bundle_missing = []
    if not workspace_dir:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "workspace_dir",
                "工作目录",
                "blocked",
                "补 workspace_dir 或运行 path.resolve。",
                node_kind="path.resolve" if node_by_kind.get("path.resolve", "") else "repo.clone",
                node_id=path_node_id,
                button_label="定位路径节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if not run_command:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "run_command",
                "运行命令",
                "blocked",
                "补 run.command 或让自动发现推断入口。",
                node_kind="run.command",
                node_id=run_node_id,
                button_label="定位运行节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if not setup_command:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "setup_command",
                "环境安装命令",
                "warning",
                "运行 env.infer/env.prepare 生成安装建议。",
                node_kind="env.prepare" if node_by_kind.get("env.prepare", "") else "env.infer",
                node_id=env_node_id,
                button_label="自动发现",
                button_action="run-workspace-discovery",
                target_id="workspaceExecutionDetail",
            )
        )
    if not artifact_paths and not metric_paths:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "artifact_paths",
                "产物路径",
                "warning",
                "补 runs/outputs/checkpoints/logs/metrics 路径。",
                node_kind="artifact.collect" if node_by_kind.get("artifact.collect", "") else "eval.report",
                node_id=artifact_node_id,
                button_label="定位产物节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if recommended_server_id == "auto" and not safe_int(resource_candidates.get("online_server_count"), 0):
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "server_id",
                "目标服务器",
                "warning",
                "刷新资源或选择可用服务器。",
                node_kind="gpu.allocate",
                node_id=gpu_node_id,
                button_label="刷新资源",
                button_action="refresh-workspace-resources",
                target_id="workspaceCockpitOperations",
            )
        )
    bundle_status = "blocked" if any(item["status"] == "blocked" for item in bundle_missing) else "warning" if bundle_missing else "ready"
    first_missing = bundle_missing[0] if bundle_missing else {}
    missing_field = str(first_missing.get("field") or "").strip()
    if bundle_status == "ready" and str(run_plan.get("status") or "") == "ready":
        bundle_next_action = {
            "label": "提交执行包",
            "action": "run-selected-workspace",
            "status": "ready",
            "title": "提交完整执行链",
            "detail": "按执行包里的 checkout/setup/run/collect/report 顺序提交工作流。",
            "node_id": run_node_id,
        }
    elif missing_field == "workspace_dir":
        bundle_next_action = {
            "label": "定位路径节点",
            "action": "select-execution-node",
            "status": "blocked",
            "title": "补工作目录",
            "detail": str(first_missing.get("action") or "补 workspace_dir 或运行 path.resolve。"),
            "node_id": node_by_kind.get("path.resolve", "") or node_by_kind.get("repo.clone", ""),
        }
    elif missing_field == "run_command":
        bundle_next_action = {
            "label": "定位运行节点",
            "action": "select-execution-node",
            "status": "blocked",
            "title": "补运行命令",
            "detail": str(first_missing.get("action") or "补 run.command 后再提交执行包。"),
            "node_id": run_node_id,
        }
    elif missing_field == "server_id":
        bundle_next_action = {
            "label": "刷新资源",
            "action": "refresh-workspace-resources",
            "status": "warning",
            "title": "刷新服务器/GPU",
            "detail": str(first_missing.get("action") or "刷新资源后重新计算执行包目标。"),
            "node_id": node_by_kind.get("gpu.allocate", ""),
        }
    elif missing_field in {"setup_command", "artifact_paths"}:
        bundle_next_action = {
            "label": "自动发现",
            "action": "run-workspace-discovery",
            "status": "warning",
            "title": "补执行包证据",
            "detail": str(first_missing.get("action") or "运行安全发现链补齐环境、产物或路径证据。"),
            "node_id": node_by_kind.get("env.infer", "") if missing_field == "setup_command" else node_by_kind.get("artifact.collect", ""),
        }
    else:
        bundle_next_action = {
            "label": "自动推进",
            "action": "advance-workspace-automation",
            "status": bundle_status,
            "title": "推进执行包",
            "detail": "让系统按当前执行包、门禁和证据决定下一步。",
            "node_id": run_node_id,
        }
    ready_to_execute = bundle_status == "ready" and str(run_plan.get("status") or "") == "ready"
    bundle_target = {
        "mode": intent["mode"],
        "label": intent["label"],
        "workspace_dir": workspace_dir,
        "server_id": recommended_server_id,
        "gpu_index": recommended_gpu_index or "auto",
        "gpu_policy": gpu_policy,
        "env_name": str(env.get("name") or "").strip(),
        "env_manager": str(env.get("manager") or "").strip() or "conda",
        "python": str(env.get("python") or "").strip(),
    }
    deployment_plan = workspace_deployment_plan(
        workspace,
        intent,
        run_command=run_command,
        workspace_dir=workspace_dir,
        target=bundle_target,
    )
    command_script = workspace_execution_bundle_command_script(
        bundle_target,
        bundle_steps,
        bundle_missing,
        delivery_contract,
        ready_to_execute=ready_to_execute,
    )
    bundle_evidence = {
        "total_count": evidence_count,
        "artifact_count": artifact_count,
        "metric_count": metric_count,
        "data_roots": data_roots[:6],
        "dataset_hints": dataset_hints[:6],
    }
    manifest_commands = {
        "checkout_command": compact_workspace_command(checkout_command, limit=180),
        "setup_command": compact_workspace_command(setup_command, limit=180),
        "run_command": compact_workspace_command(run_command, limit=180),
        "report_command": compact_workspace_command(report_command, limit=180),
    }
    manifest_paths = {
        "workspace_dir": workspace_dir,
        "data_roots": data_roots[:6],
        "output_roots": output_roots[:6],
        "artifact_paths": artifact_paths[:8],
        "metric_paths": metric_paths[:8],
    }
    package_manifest = workspace_execution_package_manifest(
        workspace,
        intent,
        delivery_contract,
        bundle_target,
        bundle_steps,
        bundle_missing,
        command_script,
        commands=manifest_commands,
        paths=manifest_paths,
        evidence=bundle_evidence,
        scheduler=resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {},
        dataset_discovery=dataset_plan,
        deployment_plan=deployment_plan,
    )
    execution_bundle = {
        "status": bundle_status,
        "ready_to_execute": ready_to_execute,
        "next_action": bundle_next_action,
        "target": bundle_target,
        "steps": bundle_steps,
        "missing": bundle_missing,
        "command_script": command_script,
        "package_manifest": package_manifest,
        "evidence": bundle_evidence,
        "delivery_contract": delivery_contract,
        "deployment_plan": deployment_plan,
    }
    return {
        "status": status,
        "intent": intent,
        "delivery_contract": delivery_contract,
        "deployment_plan": deployment_plan,
        "summary": f"{intent['label']}清单 · {ready_count}/{len(manifest_items)} 项就绪 · {status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
        "items": manifest_items,
        "counts": status_counts,
        "next_action": {
            "id": str(next_item.get("id") or "").strip(),
            "title": str(next_item.get("title") or next_item.get("label") or "等待下一步").strip(),
            "detail": str(next_item.get("detail") or "").strip(),
            "action": str(next_item.get("action") or "").strip(),
            "node_kind": str(next_item.get("node_kind") or "").strip(),
            "node_id": str(next_item.get("node_id") or "").strip(),
            "status": str(next_item.get("status") or status).strip(),
        },
        "commands": manifest_commands,
        "paths": manifest_paths,
        "dataset_discovery": copy.deepcopy(dataset_plan),
        "execution_bundle": execution_bundle,
        "ready_to_run": status == "ready" and str(run_plan.get("status") or "") == "ready",
    }
