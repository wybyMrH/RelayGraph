from __future__ import annotations

from ._deps import *  # noqa: F403
from ..execution import (
    compact_workspace_command,
    workspace_config_values,
    workspace_has_node_kind,
    workspace_node_config_by_kind,
)
from .contracts import (
    derive_workspace_execution_context,
    derive_workspace_orchestration_contract,
    derive_workspace_workflow_contract,
)
from .core import workspace_automation_check, workspace_execution_node_by_kind, workspace_status_priority
from .evidence import derive_workspace_automation_evidence
from .preflight import derive_workspace_preflight, derive_workspace_resource_orchestration
from .report import derive_workspace_automation_report, derive_workspace_execution_readiness
from .reproduction import derive_workspace_reproduction_manifest
from .run_plan import derive_workspace_run_plan
from .topology import derive_workspace_agent_topology


def workspace_advance_from_fsm(fsm: dict[str, Any]) -> dict[str, str]:
    """Map unified FSM snapshot to automation.advance."""
    from ..cockpit.fsm import workspace_advance_decision

    return workspace_advance_decision(
        str(fsm.get("action") or "").strip(),
        str(fsm.get("title") or "").strip(),
        str(fsm.get("reason") or "").strip(),
        str(fsm.get("next_action") or "").strip(),
        status=str(fsm.get("status") or "ready").strip() or "ready",
    )

def resolve_workspace_advance_bundle(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Single FSM entry: advance dict, cockpit buttons, and chain snapshot."""
    from ..cockpit.fsm import (
        derive_workspace_cockpit_chain,
        resolve_workspace_advance_fsm,
        workspace_next_action_from_fsm,
    )

    automation = automation if isinstance(automation, dict) else {}
    fsm = resolve_workspace_advance_fsm(workspace, execution, automation, jobs=jobs)
    return {
        "fsm": fsm,
        "advance": workspace_advance_from_fsm(fsm),
        "next_action": workspace_next_action_from_fsm(fsm, workspace, execution, automation),
        "chain": derive_workspace_cockpit_chain(workspace, execution),
    }

def derive_workspace_advance_state(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Advance decision slice from the unified workspace FSM."""
    return resolve_workspace_advance_bundle(workspace, execution, automation, jobs=jobs)["advance"]

def derive_workspace_automation_advance_hint(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    return derive_workspace_advance_state(workspace, execution, automation, jobs=jobs)

def workspace_playbook_step(
    step_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    button_action: str = "",
    node_id: str = "",
    server_id: str = "",
    phase: str = "",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "button_action": str(button_action or "").strip(),
        "node_id": str(node_id or "").strip(),
        "server_id": str(server_id or "").strip(),
        "phase": str(phase or "").strip(),
        "metrics": metrics or {},
    }

def derive_workspace_automation_playbook(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    advance: dict[str, Any],
    execution_readiness: dict[str, Any],
    resource_orchestration: dict[str, Any],
    reproduction_manifest: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    readiness_steps = {
        str(step.get("id") or "").strip(): step
        for step in (execution_readiness.get("steps") if isinstance(execution_readiness.get("steps"), list) else [])
        if isinstance(step, dict) and str(step.get("id") or "").strip()
    }
    manifest_items = {
        str(item.get("id") or "").strip(): item
        for item in (reproduction_manifest.get("items") if isinstance(reproduction_manifest.get("items"), list) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    job_state = execution_readiness.get("job_state") if isinstance(execution_readiness.get("job_state"), dict) else {}
    gate = execution_readiness.get("gate") if isinstance(execution_readiness.get("gate"), dict) else {}
    bundle = reproduction_manifest.get("execution_bundle") if isinstance(reproduction_manifest.get("execution_bundle"), dict) else {}
    scheduler = resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {}
    selected_resource = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    intent = reproduction_manifest.get("intent") if isinstance(reproduction_manifest.get("intent"), dict) else {}
    report_actions = report.get("next_actions") if isinstance(report.get("next_actions"), list) else []
    active_count = safe_int(job_state.get("active_count"), 0)
    failed_count = safe_int(job_state.get("failed_count"), 0)
    discovery_run_count = safe_int(job_state.get("discovery_run_count"), 0)
    evidence_payload = bundle.get("evidence") if isinstance(bundle.get("evidence"), dict) else {}
    evidence_count = safe_int(evidence_payload.get("total_count"), 0)
    last_job_id = str(job_state.get("last_job_id") or execution.get("last_job_id") or "").strip()
    run_node_id = str((manifest_items.get("run") or {}).get("node_id") or bundle.get("next_action", {}).get("node_id") or "").strip() if isinstance(bundle.get("next_action"), dict) else str((manifest_items.get("run") or {}).get("node_id") or "").strip()

    safe_discovery = readiness_steps.get("safe_discovery", {})
    backfill = readiness_steps.get("defaults_evidence", {})
    resources = readiness_steps.get("resource_binding", {})
    hard_gate = readiness_steps.get("hard_gate", {})
    full_run = readiness_steps.get("full_run", {})
    collect = readiness_steps.get("collect_report", {})

    steps = [
        workspace_playbook_step(
            "observe",
            "观察/复查",
            "running" if active_count else "failed" if failed_count else "done",
            "当前任务未结束" if active_count else "失败任务待复查" if failed_count else "没有未处理任务",
            f"{active_count} 活跃 · {failed_count} 失败 · 最近任务 {last_job_id or '无'}",
            "打开最近输出，确认任务状态。" if active_count or failed_count else "可以进入自动发现或执行准备。",
            button_action="open-last-workspace-log" if last_job_id and (active_count or failed_count) else "advance-workspace-automation",
            phase="observe",
            metrics={"active": active_count, "failed": failed_count},
        ),
        workspace_playbook_step(
            "discover",
            "安全发现",
            str(safe_discovery.get("status") or ("done" if discovery_run_count else "ready")),
            str(safe_discovery.get("title") or ("已有发现链记录" if discovery_run_count else "提交安全发现")),
            str(safe_discovery.get("detail") or f"{discovery_run_count} 次发现 · {evidence_count} 条证据"),
            str(safe_discovery.get("action") or "先收集源码、路径、数据、环境、GPU 和产物入口证据。"),
            button_action="run-workspace-discovery" if not discovery_run_count else "advance-workspace-automation",
            phase="discover",
            metrics={"discovery_runs": discovery_run_count, "evidence": evidence_count},
        ),
        workspace_playbook_step(
            "backfill",
            "证据回填",
            str(backfill.get("status") or ("ready" if evidence_count else "draft")),
            str(backfill.get("title") or ("发现证据可回填" if evidence_count else "等待发现证据")),
            str(backfill.get("detail") or f"{evidence_count} 条证据会进入路径、数据、环境、GPU、产物配置。"),
            str(backfill.get("action") or "把发现证据写回节点配置，后续执行包使用这些默认值。"),
            button_action="apply-workspace-automation" if evidence_count else "run-workspace-discovery",
            phase="prepare",
            metrics={"evidence": evidence_count},
        ),
        workspace_playbook_step(
            "schedule",
            "资源调度",
            str(resources.get("status") or resource_orchestration.get("status") or "draft"),
            str(resources.get("title") or resource_orchestration.get("summary") or "等待资源调度"),
            str(resources.get("detail") or scheduler.get("summary") or "根据 GPU、主机资源和快照新鲜度选择执行目标。"),
            str(resources.get("action") or scheduler.get("next_action") or "刷新资源或调整 server/GPU 策略。"),
            button_action="refresh-workspace-resource-server" if str(selected_resource.get("server_id") or "").strip() else "refresh-workspace-resources",
            server_id=str(selected_resource.get("server_id") or "").strip(),
            phase="schedule",
            metrics={
                "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
                "ready_count": safe_int(scheduler.get("ready_count"), 0),
                "selected_score": safe_int(selected_resource.get("score"), 0),
            },
        ),
        workspace_playbook_step(
            "gate",
            "门禁确认",
            str(hard_gate.get("status") or gate.get("status") or "draft"),
            str(hard_gate.get("title") or gate.get("title") or "等待门禁"),
            str(hard_gate.get("detail") or gate.get("detail") or "确认 Starter Chain、Agent、Tool、运行命令和资源绑定。"),
            str(hard_gate.get("action") or gate.get("action") or "处理阻塞后再继续自动推进。"),
            button_action="switch-workspace-manage" if str(gate.get("status") or hard_gate.get("status") or "") in {"blocked", "failed"} else "advance-workspace-automation",
            phase="gate",
            metrics={"blockers": len(execution_readiness.get("blockers") if isinstance(execution_readiness.get("blockers"), list) else [])},
        ),
        workspace_playbook_step(
            "execute",
            "提交执行包",
            str(full_run.get("status") or bundle.get("status") or "draft"),
            str(full_run.get("title") or ("执行包可提交" if bundle.get("ready_to_execute") else "执行包未就绪")),
            str(full_run.get("detail") or bundle.get("next_action", {}).get("detail") or "按 checkout/setup/run/collect/report 顺序提交。") if isinstance(bundle.get("next_action"), dict) else str(full_run.get("detail") or "按 checkout/setup/run/collect/report 顺序提交。"),
            str(full_run.get("action") or bundle.get("next_action", {}).get("detail") or "提交完整执行链。") if isinstance(bundle.get("next_action"), dict) else str(full_run.get("action") or "提交完整执行链。"),
            button_action="run-selected-workspace" if bundle.get("ready_to_execute") else "advance-workspace-automation",
            node_id=run_node_id,
            phase="execute",
            metrics={"ready_to_execute": bool(bundle.get("ready_to_execute")), "missing": len(bundle.get("missing") if isinstance(bundle.get("missing"), list) else [])},
        ),
        workspace_playbook_step(
            "collect",
            "产物/报告",
            str(collect.get("status") or report.get("status") or "draft"),
            str(collect.get("title") or report.get("headline") or "等待产物回收"),
            str(collect.get("detail") or report.get("summary") or "收集 logs、checkpoints、metrics、复跑命令和报告。"),
            str(collect.get("action") or (report_actions[0].get("action") if report_actions and isinstance(report_actions[0], dict) else "整理复现/部署报告。")),
            button_action="advance-workspace-automation",
            phase="report",
            metrics={"report_actions": len(report_actions)},
        ),
    ]

    current_step = next(
        (
            step for step in steps
            if str(step.get("status") or "") in {"running", "failed", "blocked", "warning", "draft"}
        ),
        steps[-1] if steps else {},
    )
    if str(advance.get("action") or "") == "watch":
        current_step = steps[0]
    elif str(advance.get("action") or "") == "discover":
        current_step = next((step for step in steps if step["id"] == "discover"), current_step)
    elif str(advance.get("action") or "") == "run":
        current_step = next((step for step in steps if step["id"] == "execute"), current_step)
    elif str(advance.get("action") or "") == "blocked":
        current_step = next((step for step in steps if step["id"] == "gate"), current_step)

    ready_count = sum(1 for step in steps if str(step.get("status") or "") in {"ready", "done"})
    status = str(current_step.get("status") or execution_readiness.get("status") or "draft")
    return {
        "status": status,
        "mode": str(intent.get("mode") or "reproduce").strip() or "reproduce",
        "label": str(intent.get("label") or "自动复现/部署").strip(),
        "summary": f"{ready_count}/{len(steps)} 步闭环 · 当前：{str(current_step.get('label') or '等待')}",
        "current_step_id": str(current_step.get("id") or "").strip(),
        "current_action": {
            "label": str(current_step.get("label") or advance.get("title") or "自动推进").strip(),
            "action": str(current_step.get("button_action") or "advance-workspace-automation").strip(),
            "title": str(current_step.get("title") or advance.get("title") or "").strip(),
            "detail": str(current_step.get("detail") or advance.get("reason") or "").strip(),
            "node_id": str(current_step.get("node_id") or "").strip(),
            "server_id": str(current_step.get("server_id") or "").strip(),
        },
        "steps": steps,
    }

def derive_workspace_automation_state(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    statuses: list[dict[str, Any]],
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    jobs_counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    source_texts = [
        str(source.get("repo_url") or "").strip(),
        str(source.get("paper_url") or "").strip(),
        str(source.get("idea_text") or "").strip(),
        str(workspace.get("brief") or "").strip(),
        str(inputs.get("goal_text") or "").strip(),
    ]
    repo_count = len(inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else [])
    paper_count = len(inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else [])
    reference_count = len(inputs.get("references") if isinstance(inputs.get("references"), list) else [])
    context_count = len(inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])
    has_source = any(source_texts) or repo_count or paper_count or reference_count or context_count

    checks: list[dict[str, Any]] = [
        workspace_automation_check(
            "source",
            "目标输入",
            "ready" if has_source else "draft",
            "输入已绑定" if has_source else "缺少复现目标",
            f"{repo_count} repo · {paper_count} paper · {reference_count} 参考 · {context_count} 上下文",
            "补目标、repo、论文、数据路径或约束，让系统能推导 Starter Chain。",
        )
    ]

    required_kinds = ["path.resolve", "dataset.find", "env.infer", "gpu.allocate", "run.command", "artifact.collect"]
    missing_kinds = [kind for kind in required_kinds if not workspace_has_node_kind(workspace, kind)]
    checks.append(
        workspace_automation_check(
            "starter_chain",
            "节点链",
            "ready" if not missing_kinds else "blocked",
            f"{len(nodes)} 个节点" if not missing_kinds else "Starter Chain 不完整",
            "已覆盖路径、数据、环境、GPU、运行、产物闭环。" if not missing_kinds else "缺少 " + ", ".join(missing_kinds),
            "回配置中心恢复默认链或补齐缺失节点。",
        )
    )

    missing_handlers = 0
    executable_nodes = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        executable_nodes += 1
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if str(handler.get("mode") or "agent").strip() != "human" and not str(handler.get("agent_id") or "").strip():
            missing_handlers += 1
    checks.append(
        workspace_automation_check(
            "agents",
            "Agent 归属",
            "ready" if executable_nodes and not missing_handlers else "blocked" if missing_handlers else "warning",
            f"{executable_nodes} 个可执行节点已分层" if not missing_handlers else f"{missing_handlers} 个节点缺 Agent",
            "节点已经挂到对应 Agent/Tool 职责。" if not missing_handlers else "没有 Agent 的节点无法形成可解释交接。",
            "在配置中心把规划、仓库、数据、环境、GPU、运行、报告 Agent 绑定到节点。",
        )
    )

    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    path_node = workspace_execution_node_by_kind(execution, "path.resolve")
    path_artifacts = path_node.get("artifacts") if isinstance(path_node.get("artifacts"), list) else []
    found_paths = [item for item in path_artifacts if isinstance(item, dict) and str(item.get("status") or "") == "found"]
    checks.append(
        workspace_automation_check(
            "paths",
            "路径解析",
            "ready" if workspace_dir or found_paths else "warning",
            "工作目录已设置" if workspace_dir else "路径等待解析",
            workspace_dir or (str(found_paths[0].get("resolved_path") or found_paths[0].get("path") or "") if found_paths else "还没有 workspace_dir / data_roots / output_roots。"),
            "补工作目录、数据根目录、输出目录；运行 path.resolve 后会回填路径快照。",
            node_kind="path.resolve",
        )
    )

    dataset_node = workspace_execution_node_by_kind(execution, "dataset.find")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    dataset_artifacts = dataset_node.get("artifacts") if isinstance(dataset_node.get("artifacts"), list) else []
    dataset_hits = [
        item for item in dataset_artifacts
        if isinstance(item, dict) and str(item.get("label") or "") in {"候选数据集", "候选数据根", "数据根目录", "数据集线索"} and str(item.get("status") or "") in {"found", "planned"}
    ]
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints")) + workspace_config_values(dataset_config.get("data_roots"))
    checks.append(
        workspace_automation_check(
            "dataset",
            "数据集",
            "ready" if dataset_hits or dataset_hints or reference_count else "warning",
            "数据线索已出现" if dataset_hits or dataset_hints or reference_count else "缺数据集线索",
            f"{len(dataset_hits)} 个候选 · {len(dataset_hints)} 条配置线索 · {reference_count} 条参考",
            "补数据集名称、下载页、本地数据根，或运行 dataset.find 自动扫描候选。",
            node_kind="dataset.find",
        )
    )

    env_node = workspace_execution_node_by_kind(execution, "env.infer")
    env_config = workspace_node_config_by_kind(workspace, "env.prepare")
    env_resources = env_node.get("resources") if isinstance(env_node.get("resources"), dict) else {}
    workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    env_ready = bool(
        str(workspace_env.get("name") or "").strip()
        or str(env_config.get("setup_command") or "").strip()
        or env_resources.get("setup_suggestion")
        or env_resources.get("found_manifests")
    )
    checks.append(
        workspace_automation_check(
            "env",
            "环境推断",
            "ready" if env_ready else "warning",
            "环境入口已具备" if env_ready else "缺环境入口",
            str(env_resources.get("setup_suggestion") or workspace_env.get("name") or env_config.get("setup_command") or "还没有 env_name、setup_command 或 manifest 发现。"),
            "运行 env.infer 或补 requirements/environment/pyproject 对应的 setup 命令。",
            node_kind="env.infer",
        )
    )

    run_config = workspace_node_config_by_kind(workspace, "run.command")
    gpu_node = workspace_execution_node_by_kind(execution, "gpu.allocate")
    gpu_resources = gpu_node.get("resources") if isinstance(gpu_node.get("resources"), dict) else {}
    run_gpu_policy = str(run_config.get("gpu_policy") or gpu_resources.get("gpu_policy") or "auto").strip().lower()
    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]
    all_gpus = [
        gpu for status in online_statuses
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else [])
        if isinstance(gpu, dict)
    ]
    idle_gpus = [gpu for gpu in all_gpus if str(gpu.get("state") or "") == "idle"]
    cpu_mode = run_gpu_policy in {"cpu", "none", "no_gpu"}
    checks.append(
        workspace_automation_check(
            "gpu",
            "GPU 调度",
            "ready" if cpu_mode or idle_gpus else "warning" if online_statuses or all_gpus else "blocked",
            "资源策略可执行" if cpu_mode or idle_gpus else "GPU 快照不足",
            "CPU/无 GPU 模式" if cpu_mode else f"{len(online_statuses)} 台在线 · {len(idle_gpus)}/{len(all_gpus)} 张空闲 GPU",
            "刷新监控或在 gpu.allocate / run.command 设置 server_id、gpu_policy、min_free_memory_gib。",
            node_kind="gpu.allocate",
        )
    )

    run_command = str(run_config.get("run_command") or "").strip()
    checks.append(
        workspace_automation_check(
            "run",
            "运行命令",
            "ready" if run_command else "blocked",
            "运行命令已设置" if run_command else "缺 run command",
            compact_workspace_command(run_command) if run_command else "没有可提交的训练、推理、部署或 smoke test 命令。",
            "补 run.command 的命令，或者让 Agent 从 README/脚本中推断。",
            node_kind="run.command",
        )
    )

    artifact_node = workspace_execution_node_by_kind(execution, "artifact.collect")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")
    artifact_artifacts = artifact_node.get("artifacts") if isinstance(artifact_node.get("artifacts"), list) else []
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths")) + workspace_config_values(artifact_config.get("metric_paths"))
    checks.append(
        workspace_automation_check(
            "artifact",
            "产物收集",
            "ready" if artifact_paths or artifact_artifacts else "warning",
            "产物入口已设置" if artifact_paths or artifact_artifacts else "缺产物路径",
            f"{len(artifact_paths)} 条配置路径 · {len(artifact_artifacts)} 条运行快照",
            "补 runs/outputs/checkpoints/logs/metrics 路径，运行 artifact.collect 后收集报告证据。",
            node_kind="artifact.collect",
        )
    )

    status_counts: dict[str, int] = {}
    for check in checks:
        status = str(check.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    if jobs_counts.get("failed"):
        overall = "failed"
    elif jobs_counts.get("running") or jobs_counts.get("queued"):
        overall = "running"
    elif status_counts.get("blocked"):
        overall = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        overall = "warning"
    elif jobs_counts.get("done"):
        overall = "done"
    else:
        overall = "ready"

    weighted = sum(max(workspace_status_priority(str(check.get("status") or "")), 0) for check in checks)
    score = round((weighted / max(len(checks) * workspace_status_priority("ready"), 1)) * 100)
    evidence = derive_workspace_automation_evidence(execution)
    from ..cockpit.discovery import derive_workspace_dataset_discovery_plan
    from ..cockpit.evidence import derive_workspace_evidence_backfill_plan
    from ..cockpit.fsm import workspace_advance_decision

    dataset_discovery = derive_workspace_dataset_discovery_plan(workspace, execution, evidence)
    run_plan = derive_workspace_run_plan(workspace, execution, checks)
    agent_topology = derive_workspace_agent_topology(workspace, run_plan)
    resource_orchestration = derive_workspace_resource_orchestration(
        workspace,
        execution,
        statuses,
        checks,
        evidence,
        run_plan,
    )
    workflow_contract = derive_workspace_workflow_contract(
        workspace,
        execution,
        evidence,
        resource_orchestration,
        run_plan,
        agent_topology,
    )
    orchestration_contract = derive_workspace_orchestration_contract(agent_topology, workflow_contract)
    execution_context = derive_workspace_execution_context(workspace, execution, workflow_contract)
    reproduction_manifest = derive_workspace_reproduction_manifest(
        workspace,
        execution,
        checks,
        evidence,
        run_plan,
        resource_orchestration,
        dataset_discovery,
        execution_context,
    )
    report = derive_workspace_automation_report(workspace, execution, checks, evidence, run_plan, status_counts)
    evidence_backfill = derive_workspace_evidence_backfill_plan(workspace, execution, resource_orchestration)
    placeholder_advance = workspace_advance_decision(
        "run",
        "自动推进",
        "等待系统判断下一步。",
        "点击自动推进。",
    )
    execution_readiness = derive_workspace_execution_readiness(
        workspace,
        execution,
        checks,
        evidence,
        run_plan,
        placeholder_advance,
        agent_topology,
        resource_orchestration,
    )
    playbook = derive_workspace_automation_playbook(
        workspace,
        execution,
        placeholder_advance,
        execution_readiness,
        resource_orchestration,
        reproduction_manifest,
        report,
    )
    preflight = derive_workspace_preflight(
        workspace,
        execution,
        checks,
        run_plan,
        dataset_discovery,
        resource_orchestration,
        agent_topology,
        reproduction_manifest,
        execution_readiness,
        report,
    )
    automation_body: dict[str, Any] = {
        "status": overall,
        "score": max(0, min(score, 100)),
        "counts": status_counts,
        "checks": checks,
        "evidence": evidence,
        "evidence_backfill": evidence_backfill,
        "run_plan": run_plan,
        "workflow_contract": workflow_contract,
        "orchestration_contract": orchestration_contract,
        "execution_context": execution_context,
        "dataset_discovery": dataset_discovery,
        "reproduction_manifest": reproduction_manifest,
        "agent_topology": agent_topology,
        "resource_orchestration": resource_orchestration,
        "execution_readiness": execution_readiness,
        "playbook": playbook,
        "preflight": preflight,
        "report": report,
        "missing": [check for check in checks if str(check.get("status") or "") in {"blocked", "warning", "draft"}],
        "summary": f"{status_counts.get('ready', 0) + status_counts.get('done', 0)} 项就绪 · {status_counts.get('warning', 0)} 项提示 · {status_counts.get('blocked', 0)} 项阻塞",
    }
    advance_bundle = resolve_workspace_advance_bundle(workspace, execution, automation_body, jobs=jobs)
    advance = advance_bundle["advance"]
    execution_readiness["next_action"] = advance
    playbook = derive_workspace_automation_playbook(
        workspace,
        execution,
        advance,
        execution_readiness,
        resource_orchestration,
        reproduction_manifest,
        report,
    )
    automation_body["playbook"] = playbook
    automation_body["execution_readiness"] = execution_readiness
    advance_bundle = resolve_workspace_advance_bundle(workspace, execution, automation_body, jobs=jobs)
    advance = advance_bundle["advance"]
    execution_readiness["next_action"] = advance
    next_check = next(
        (
            check for check in checks
            if str(check.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        checks[-1] if checks else {},
    )
    return {
        **automation_body,
        "advance": advance,
        "next_check": next_check,
    }
