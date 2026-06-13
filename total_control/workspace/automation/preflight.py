from __future__ import annotations

from ._deps import *  # noqa: F403
from .evidence import workspace_evidence_group


def workspace_execution_readiness_step(
    step_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    evidence_count: int = 0,
    blocker_count: int = 0,
    warning_count: int = 0,
    node_count: int = 0,
    job_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
        "blocker_count": safe_int(blocker_count, 0),
        "warning_count": safe_int(warning_count, 0),
        "node_count": safe_int(node_count, 0),
        "job_count": safe_int(job_count, 0),
    }

def workspace_resource_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    value: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
    phase: str = "",
    evidence_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "value": str(value or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "phase": str(phase or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
    }

def workspace_preflight_action(
    label: str,
    action: str,
    *,
    tone: str = "secondary",
    title: str = "",
    node_id: str = "",
    server_id: str = "",
    tab: str = "",
    mode: str = "",
) -> dict[str, Any]:
    return {
        "label": str(label or "操作").strip(),
        "action": str(action or "").strip(),
        "tone": "primary" if tone == "primary" else "secondary",
        "title": str(title or label or "").strip(),
        "node_id": str(node_id or "").strip(),
        "server_id": str(server_id or "").strip(),
        "tab": str(tab or "").strip(),
        "mode": str(mode or "").strip(),
    }

def workspace_preflight_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    layer: str = "",
    phase: str = "",
    node_kind: str = "",
    node_id: str = "",
    requires: list[str] | None = None,
    missing: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    action_button: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "layer": str(layer or "").strip(),
        "phase": str(phase or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "requires": [str(item or "").strip() for item in (requires or []) if str(item or "").strip()],
        "missing": [str(item or "").strip() for item in (missing or []) if str(item or "").strip()],
        "metrics": metrics or {},
        "action_button": action_button or {},
    }

def workspace_preflight_combined_status(*statuses: Any) -> str:
    normalized = [str(status or "").strip() for status in statuses if str(status or "").strip()]
    for status in ("failed", "blocked", "warning", "draft", "running", "ready", "done"):
        if status in normalized:
            return status
    return "draft"

def derive_workspace_preflight(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    run_plan: dict[str, Any],
    dataset_discovery: dict[str, Any],
    resource_orchestration: dict[str, Any],
    agent_topology: dict[str, Any],
    reproduction_manifest: dict[str, Any],
    execution_readiness: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    bundle = reproduction_manifest.get("execution_bundle") if isinstance(reproduction_manifest.get("execution_bundle"), dict) else {}
    scheduler = resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {}
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    job_state = execution_readiness.get("job_state") if isinstance(execution_readiness.get("job_state"), dict) else {}
    readiness_steps = {
        str(step.get("id") or "").strip(): step
        for step in (execution_readiness.get("steps") if isinstance(execution_readiness.get("steps"), list) else [])
        if isinstance(step, dict) and str(step.get("id") or "").strip()
    }

    def check(check_id: str) -> dict[str, Any]:
        return check_index.get(check_id, {})

    def node_id(kind: str) -> str:
        node = workspace_node_by_kind(workspace, kind)
        return str(node.get("id") or "").strip() if node else ""

    def missing_from_checks(*check_ids: str) -> list[str]:
        values: list[str] = []
        for check_id in check_ids:
            item = check(check_id)
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft"}:
                text = str(item.get("title") or item.get("detail") or item.get("label") or check_id).strip()
                if text:
                    values.append(text)
        return values

    source_count = sum(
        1
        for value in (
            source.get("repo_url"),
            source.get("paper_url"),
            source.get("idea_text"),
            workspace.get("brief"),
            inputs.get("goal_text"),
        )
        if str(value or "").strip()
    )
    source_count += len(inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else [])
    source_count += len(inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else [])
    source_count += len(inputs.get("references") if isinstance(inputs.get("references"), list) else [])
    source_check = check("source")
    starter_check = check("starter_chain")
    path_check = check("paths")
    dataset_check = check("dataset")
    env_check = check("env")
    gpu_check = check("gpu")
    run_check = check("run")
    artifact_check = check("artifact")
    agents_check = check("agents")

    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    bundle_missing = bundle.get("missing") if isinstance(bundle.get("missing"), list) else []
    topology_layers = agent_topology.get("layers") if isinstance(agent_topology.get("layers"), dict) else {}
    model_layer = topology_layers.get("ai") if isinstance(topology_layers.get("ai"), dict) else {}
    agent_layer = topology_layers.get("agent") if isinstance(topology_layers.get("agent"), dict) else {}
    tool_layer = topology_layers.get("tool") if isinstance(topology_layers.get("tool"), dict) else {}
    dataset_queries = dataset_discovery.get("queries") if isinstance(dataset_discovery.get("queries"), list) else []
    dataset_roots = dataset_discovery.get("local_roots") if isinstance(dataset_discovery.get("local_roots"), list) else []
    resource_candidates = resource_orchestration.get("resource_candidates") if isinstance(resource_orchestration.get("resource_candidates"), dict) else {}
    active_count = safe_int(job_state.get("active_count"), 0)
    failed_count = safe_int(job_state.get("failed_count"), 0)
    done_count = safe_int(job_state.get("done_count"), 0)

    items = [
        workspace_preflight_item(
            "launcher",
            "项目启动器",
            str(source_check.get("status") or "draft"),
            str(source_check.get("title") or ("输入已绑定" if source_count else "等待输入")),
            str(source_check.get("detail") or f"{source_count} 条输入线索"),
            str(source_check.get("action") or "补 repo、论文、目标描述、参考路径和约束。"),
            layer="project",
            phase="launch",
            requires=["repo / paper / idea", "目标简报", "参考路径或约束"],
            missing=missing_from_checks("source"),
            metrics={"input_count": source_count},
            action_button=workspace_preflight_action("项目设置", "switch-workspace-tab", tab="project", title="打开项目设置，补齐启动输入和目录环境。"),
        ),
        workspace_preflight_item(
            "workflow_chain",
            "工作流节点链",
            workspace_preflight_combined_status(starter_check.get("status"), run_plan.get("status")),
            str(run_plan.get("summary") or starter_check.get("title") or "等待节点链"),
            str(starter_check.get("detail") or f"{safe_int(run_plan.get('node_count'), 0)} 个可执行节点"),
            str(starter_check.get("action") or "补齐路径、数据、环境、GPU、运行、产物和报告节点。"),
            layer="workflow",
            phase="orchestrate",
            requires=["Starter Chain", "节点 I/O 契约", "可执行 run node"],
            missing=missing_from_checks("starter_chain", "run") + [
                str(item.get("detail") or item.get("title") or item.get("field") or "").strip()
                for item in run_blocking[:4]
                if isinstance(item, dict)
            ],
            metrics={"node_count": len(nodes), "run_node_count": safe_int(run_plan.get("node_count"), 0), "blocking_count": len(run_blocking)},
            action_button=workspace_preflight_action("节点链", "switch-workspace-tab", tab="workflow", title="打开工作流页，查看节点链和 I/O 交接。"),
        ),
        workspace_preflight_item(
            "data_paths",
            "数据和路径",
            workspace_preflight_combined_status(path_check.get("status"), dataset_check.get("status"), dataset_discovery.get("status")),
            str(dataset_discovery.get("summary") or dataset_check.get("title") or "等待数据计划"),
            f"{len(dataset_queries)} 查询 · {len(dataset_roots)} 本地根 · workspace_dir={str(workspace.get('workspace_dir') or '未设置')}",
            str(dataset_check.get("action") or path_check.get("action") or "运行 path.resolve / dataset.find，或补本地数据根。"),
            layer="data",
            phase="discover",
            node_kind="dataset.find",
            node_id=node_id("dataset.find"),
            requires=["workspace_dir", "data_roots", "dataset hints / query"],
            missing=missing_from_checks("paths", "dataset"),
            metrics={"query_count": len(dataset_queries), "local_root_count": len(dataset_roots)},
            action_button=workspace_preflight_action("自动发现", "run-workspace-discovery", tone="primary", title="运行安全发现链，收集路径和数据候选。"),
        ),
        workspace_preflight_item(
            "environment",
            "环境准备",
            str(env_check.get("status") or "warning"),
            str(env_check.get("title") or "等待环境入口"),
            str(env_check.get("detail") or "等待 env_name、setup_command 或环境清单。"),
            str(env_check.get("action") or "运行 env.infer 或补 setup_command。"),
            layer="env",
            phase="setup",
            node_kind="env.prepare",
            node_id=node_id("env.prepare"),
            requires=["env_name", "setup_command", "requirements / environment manifest"],
            missing=missing_from_checks("env"),
            metrics={"manifest_count": len(workspace_config_values(workspace_node_config_by_kind(workspace, "env.infer").get("manifest_paths")))},
            action_button=workspace_preflight_action("环境节点", "switch-workspace-tab", tab="workflow", title="打开工作流页，定位环境推断和准备节点。"),
        ),
        workspace_preflight_item(
            "scheduler",
            "资源/GPU 调度",
            workspace_preflight_combined_status(gpu_check.get("status"), resource_orchestration.get("status"), scheduler.get("status")),
            str(scheduler.get("summary") or resource_orchestration.get("summary") or gpu_check.get("title") or "等待调度"),
            str(resource_orchestration.get("next_action", {}).get("detail") if isinstance(resource_orchestration.get("next_action"), dict) else "") or str(gpu_check.get("detail") or ""),
            str(gpu_check.get("action") or "刷新资源快照，或设置 server_id/gpu_policy/min_free_memory_gib。"),
            layer="resource",
            phase="schedule",
            node_kind="gpu.allocate",
            node_id=node_id("gpu.allocate"),
            requires=["server snapshot", "GPU policy", "host/GPU availability"],
            missing=missing_from_checks("gpu"),
            metrics={
                "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
                "ready_count": safe_int(scheduler.get("ready_count"), 0),
                "online_server_count": safe_int(resource_candidates.get("online_server_count"), 0),
                "idle_gpu_count": safe_int(resource_candidates.get("idle_gpu_count"), 0),
            },
            action_button=workspace_preflight_action(
                "刷新调度",
                "refresh-workspace-resource-server" if str(selected.get("server_id") or "").strip() else "refresh-workspace-resources",
                tone="primary" if str(resource_orchestration.get("status") or "") in {"blocked", "warning", "draft"} else "secondary",
                title="刷新资源快照并更新 GPU/主机调度候选。",
                server_id=str(selected.get("server_id") or "").strip(),
            ),
        ),
        workspace_preflight_item(
            "agent_tool_ai",
            "Agent / Tool / AI",
            workspace_preflight_combined_status(agents_check.get("status"), agent_topology.get("status"), model_layer.get("status")),
            str(agent_topology.get("summary") or agents_check.get("title") or "等待分层"),
            f"Agent {agent_layer.get('assigned_count', 0)}/{agent_layer.get('required_count', 0)} · Tool {tool_layer.get('assigned_count', 0)}/{tool_layer.get('required_count', 0)} · AI {model_layer.get('title') or model_layer.get('status') or '待配置'}",
            str(agents_check.get("action") or "补 Agent 归属、工具 allowlist 和 Provider Profile。"),
            layer="agent_tool_ai",
            phase="delegate",
            requires=["node owner Agent", "tool allowlist", "Provider Profile / routing"],
            missing=missing_from_checks("agents") + [
                str(item.get("title") or item.get("detail") or item.get("type") or "").strip()
                for item in (agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else [])[:4]
                if isinstance(item, dict)
            ],
            metrics={
                "agent_assigned": safe_int(agent_layer.get("assigned_count"), 0),
                "tool_assigned": safe_int(tool_layer.get("assigned_count"), 0),
                "gap_count": len(agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []),
            },
            action_button=workspace_preflight_action("分层配置", "switch-workspace-tab", tab="agents", title="打开 Agent 分层页，检查角色、工具和模型覆盖。"),
        ),
        workspace_preflight_item(
            "execution_package",
            "执行包",
            str(bundle.get("status") or reproduction_manifest.get("status") or "draft"),
            "执行包可提交" if bundle.get("ready_to_execute") else str(bundle.get("next_action", {}).get("label") if isinstance(bundle.get("next_action"), dict) else "") or "执行包未就绪",
            str(bundle.get("command_script", {}).get("summary") if isinstance(bundle.get("command_script"), dict) else "") or str(reproduction_manifest.get("summary") or ""),
            str(bundle.get("next_action", {}).get("detail") if isinstance(bundle.get("next_action"), dict) else "") or "先补齐执行包缺失字段。",
            layer="package",
            phase="execute",
            node_kind="run.command",
            node_id=node_id("run.command"),
            requires=["checkout/setup/run/report script", "target server/GPU", "delivery contract"],
            missing=[
                str(item.get("field") or item.get("label") or item.get("detail") or "").strip()
                for item in bundle_missing[:6]
                if isinstance(item, dict)
            ],
            metrics={"ready_to_execute": bool(bundle.get("ready_to_execute")), "missing_count": len(bundle_missing)},
            action_button=workspace_preflight_action(
                "提交执行包" if bundle.get("ready_to_execute") else "自动推进",
                "run-selected-workspace" if bundle.get("ready_to_execute") else "advance-workspace-automation",
                tone="primary",
                title="提交完整执行包，或让系统先自动补齐缺失项。",
            ),
        ),
        workspace_preflight_item(
            "run_records",
            "运行/报告闭环",
            "failed" if failed_count else "running" if active_count else str(report.get("status") or readiness_steps.get("collect_report", {}).get("status") or "draft"),
            str(report.get("headline") or readiness_steps.get("collect_report", {}).get("title") or "等待运行记录"),
            str(report.get("summary") or f"{active_count} 活跃 · {failed_count} 失败 · {done_count} 完成"),
            str((report.get("next_actions") if isinstance(report.get("next_actions"), list) and report.get("next_actions") else [{}])[0].get("action") or "运行完成后收集日志、指标、产物和复跑报告。"),
            layer="report",
            phase="collect",
            requires=["job logs", "artifacts", "metrics", "re-run report"],
            missing=[] if active_count or failed_count or done_count else ["还没有运行记录"],
            metrics={"active": active_count, "failed": failed_count, "done": done_count},
            action_button=workspace_preflight_action(
                "打开输出" if active_count or failed_count else "运行记录",
                "open-last-workspace-log" if active_count or failed_count else "switch-workspace-tab",
                tone="primary" if active_count or failed_count else "secondary",
                tab="" if active_count or failed_count else "runs",
                title="打开最近任务输出，或进入运行记录查看历史。",
            ),
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "draft")
        counts[status] = counts.get(status, 0) + 1
    if counts.get("failed"):
        status = "failed"
    elif counts.get("running"):
        status = "running"
    elif counts.get("blocked"):
        status = "blocked"
    elif counts.get("warning") or counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    ready_count = counts.get("ready", 0) + counts.get("done", 0)
    next_item = next(
        (
            item for item in items
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft", "running"}
        ),
        items[-1] if items else {},
    )
    return {
        "status": status,
        "summary": f"{ready_count}/{len(items)} 环节就绪 · {counts.get('blocked', 0)} 阻塞 · {counts.get('warning', 0)} 提示 · {counts.get('running', 0)} 运行",
        "items": items,
        "counts": counts,
        "ready_count": ready_count,
        "blocked_count": counts.get("blocked", 0),
        "warning_count": counts.get("warning", 0) + counts.get("draft", 0),
        "running_count": counts.get("running", 0),
        "failed_count": counts.get("failed", 0),
        "next_action": next_item,
    }

def derive_workspace_resource_orchestration(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    statuses: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
) -> dict[str, Any]:
    from ..cockpit.commands import infer_workspace_best_gpu
    from ..cockpit.scheduler import derive_workspace_resource_scheduler

    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    env_prepare_config = workspace_node_config_by_kind(workspace, "env.prepare")
    env_infer_config = workspace_node_config_by_kind(workspace, "env.infer")
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")

    path_group = workspace_evidence_group(evidence, "paths")
    dataset_group = workspace_evidence_group(evidence, "dataset")
    env_group = workspace_evidence_group(evidence, "env")
    gpu_group = workspace_evidence_group(evidence, "gpu")
    run_group = workspace_evidence_group(evidence, "run")
    artifact_group = workspace_evidence_group(evidence, "artifact")
    metric_group = workspace_evidence_group(evidence, "metric")

    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]
    all_gpus = [
        gpu for status in online_statuses
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else [])
        if isinstance(gpu, dict)
    ]
    idle_gpus = [gpu for gpu in all_gpus if str(gpu.get("state") or "") == "idle"]

    data_roots = workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots"))
    output_roots = workspace_config_values(path_config.get("output_roots"))
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints"))
    manifest_paths = workspace_config_values(env_infer_config.get("manifest_paths"))
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths"))
    metric_paths = workspace_config_values(artifact_config.get("metric_paths"))
    setup_command = str(env_prepare_config.get("setup_command") or "").strip()
    run_command = str(run_config.get("run_command") or "").strip()
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip().lower() or "auto"
    cpu_mode = gpu_policy in {"cpu", "none", "no_gpu"}
    requested_server_id = str(run_config.get("server_id") or gpu_config.get("server_id") or "auto").strip() or "auto"
    requested_gpu_index = str(run_config.get("gpu_index") or gpu_config.get("gpu_index") or "").strip()
    min_free_memory_gib = safe_int(run_config.get("min_free_memory_gib") or gpu_config.get("min_free_memory_gib"), 0)
    scheduler = derive_workspace_resource_scheduler(
        statuses,
        gpu_policy=gpu_policy,
        requested_server_id=requested_server_id,
        requested_gpu_index=requested_gpu_index,
        min_free_memory_gib=min_free_memory_gib,
    )
    selected_candidate = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    best_gpu = selected_candidate if selected_candidate.get("mode") == "gpu" else infer_workspace_best_gpu(statuses)

    path_check = check_index.get("paths", {})
    dataset_check = check_index.get("dataset", {})
    env_check = check_index.get("env", {})
    gpu_check = check_index.get("gpu", {})
    run_check = check_index.get("run", {})
    artifact_check = check_index.get("artifact", {})

    first_dataset_item = next((item for item in dataset_group.get("items", []) if isinstance(item, dict)), {})
    first_env_item = next((item for item in env_group.get("items", []) if isinstance(item, dict)), {})
    first_run_item = next((item for item in run_group.get("items", []) if isinstance(item, dict)), {})
    first_artifact_item = next((item for item in artifact_group.get("items", []) if isinstance(item, dict)), {})
    repo_or_paper = str(source.get("repo_url") or source.get("paper_url") or source.get("idea_text") or workspace.get("brief") or "").strip()

    items = [
        workspace_resource_item(
            "paths",
            "路径",
            str(path_check.get("status") or "warning"),
            str(path_check.get("title") or ("工作目录已设置" if workspace_dir else "路径等待解析")),
            workspace_dir or str((path_group.get("items") or [{}])[0].get("value") if path_group.get("items") else ""),
            f"{len(data_roots)} 条数据根 · {len(output_roots)} 条输出根 · {safe_int(path_group.get('count'), 0)} 条证据",
            str(path_check.get("action") or "补 workspace_dir/data_roots/output_roots，或运行 path.resolve。"),
            node_kind="path.resolve",
            phase="discover",
            evidence_count=safe_int(path_group.get("count"), 0),
        ),
        workspace_resource_item(
            "dataset",
            "数据集",
            str(dataset_check.get("status") or "warning"),
            str(dataset_check.get("title") or ("数据线索已出现" if dataset_hints or first_dataset_item else "缺数据集线索")),
            str(first_dataset_item.get("value") or dataset_config.get("query") or repo_or_paper or "等待数据线索"),
            f"{len(dataset_hints)} 条线索 · {len(data_roots)} 条候选根 · {safe_int(dataset_group.get('count'), 0)} 条证据",
            str(dataset_check.get("action") or "补数据集名称、下载页、本地数据根，或运行 dataset.find。"),
            node_kind="dataset.find",
            phase="discover",
            evidence_count=safe_int(dataset_group.get("count"), 0),
        ),
        workspace_resource_item(
            "env",
            "环境",
            str(env_check.get("status") or "warning"),
            str(env_check.get("title") or ("环境入口已具备" if setup_command or env.get("name") else "缺环境入口")),
            str(first_env_item.get("value") or setup_command or env.get("name") or "等待环境推断"),
            f"{env.get('manager') or 'conda'} · {env.get('python') or 'Python 待定'} · {len(manifest_paths)} 个清单候选",
            str(env_check.get("action") or "运行 env.infer 或补 setup_command。"),
            node_kind="env.infer",
            phase="setup",
            evidence_count=safe_int(env_group.get("count"), 0),
        ),
        workspace_resource_item(
            "gpu",
            "GPU",
            str(gpu_check.get("status") or "warning"),
            str(gpu_check.get("title") or ("资源策略可执行" if cpu_mode or idle_gpus else "GPU 快照不足")),
            "CPU/无 GPU 模式" if cpu_mode else (
                f"{best_gpu.get('server_id', 'auto')} · GPU {best_gpu.get('gpu_index', 'auto')}" if best_gpu else "等待 GPU 快照"
            ),
            f"{len(online_statuses)} 台在线 · {len(idle_gpus)}/{len(all_gpus)} 张空闲 · policy={gpu_policy}",
            str(gpu_check.get("action") or "刷新监控或设置 server_id/gpu_policy/min_free_memory_gib。"),
            node_kind="gpu.allocate",
            phase="run",
            evidence_count=safe_int(gpu_group.get("count"), 0),
        ),
        workspace_resource_item(
            "run",
            "运行入口",
            str(run_check.get("status") or "blocked"),
            str(run_check.get("title") or ("运行命令已设置" if run_command else "发现运行候选" if first_run_item else "缺 run command")),
            compact_workspace_command(run_command) if run_command else str(first_run_item.get("value") or "等待可提交命令"),
            str(run_plan.get("summary") or "等待运行预案"),
            str(run_check.get("action") or ("回填发现运行命令后再提交完整工作流。" if first_run_item else "补 run.command，或让 Agent 从 README/脚本中推断。")),
            node_kind="run.command",
            phase="run",
            evidence_count=safe_int(run_group.get("count"), 0),
        ),
        workspace_resource_item(
            "artifact",
            "产物/指标",
            str(artifact_check.get("status") or "warning"),
            str(artifact_check.get("title") or ("产物入口已设置" if artifact_paths or first_artifact_item else "缺产物路径")),
            str(first_artifact_item.get("value") or (artifact_paths[0] if artifact_paths else "等待产物入口")),
            f"{len(artifact_paths)} 条产物路径 · {len(metric_paths)} 条指标路径 · {safe_int(metric_group.get('count'), 0)} 条指标证据",
            str(artifact_check.get("action") or "补 runs/outputs/checkpoints/logs/metrics 路径并运行 artifact.collect。"),
            node_kind="artifact.collect",
            phase="collect",
            evidence_count=safe_int(artifact_group.get("count"), 0) + safe_int(metric_group.get("count"), 0),
        ),
    ]

    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    if status_counts.get("blocked") or status_counts.get("failed"):
        status = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    next_item = next(
        (item for item in items if str(item.get("status") or "") in {"blocked", "failed", "warning", "draft"}),
        items[-1] if items else {},
    )
    ready_count = status_counts.get("ready", 0) + status_counts.get("done", 0)
    return {
        "status": status,
        "summary": f"{ready_count}/{len(items)} 项调度就绪 · {status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
        "counts": status_counts,
        "items": items,
        "next_action": next_item,
        "resource_candidates": {
            "online_server_count": len(online_statuses),
            "gpu_count": len(all_gpus),
            "idle_gpu_count": len(idle_gpus),
            "recommended_server_id": str(selected_candidate.get("server_id") or best_gpu.get("server_id") or "").strip(),
            "recommended_gpu_index": str(selected_candidate.get("gpu_index") or best_gpu.get("gpu_index") or "").strip(),
            "recommended_gpu_free_mib": safe_int(best_gpu.get("memory_free_mib"), 0),
        },
        "scheduler": scheduler,
    }
