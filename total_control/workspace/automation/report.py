from __future__ import annotations

from ._deps import *  # noqa: F403
from .core import workspace_enrich_readiness_issue
from .evidence import workspace_evidence_group
from .preflight import workspace_execution_readiness_step


def workspace_report_highlight(label: str, value: str, detail: str = "", status: str = "ready") -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "detail": detail,
        "status": status,
    }

def workspace_report_next_action(label: str, detail: str, action: str, status: str = "ready") -> dict[str, Any]:
    return {
        "label": label,
        "detail": detail,
        "action": action,
        "status": status,
    }

def derive_workspace_automation_report(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    status_counts: dict[str, int],
) -> dict[str, Any]:
    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    metric_group = workspace_evidence_group(evidence, "metric")
    artifact_group = workspace_evidence_group(evidence, "artifact")
    dataset_group = workspace_evidence_group(evidence, "dataset")
    env_group = workspace_evidence_group(evidence, "env")
    gpu_group = workspace_evidence_group(evidence, "gpu")
    metric_items = metric_group.get("items") if isinstance(metric_group.get("items"), list) else []
    artifact_items = artifact_group.get("items") if isinstance(artifact_group.get("items"), list) else []
    dataset_items = dataset_group.get("items") if isinstance(dataset_group.get("items"), list) else []
    env_items = env_group.get("items") if isinstance(env_group.get("items"), list) else []
    gpu_items = gpu_group.get("items") if isinstance(gpu_group.get("items"), list) else []
    blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    warnings = run_plan.get("warnings") if isinstance(run_plan.get("warnings"), list) else []

    if counts.get("failed"):
        status = "failed"
        headline = "运行存在失败节点"
    elif blocking:
        status = "blocked"
        headline = "完整运行前仍有阻塞项"
    elif counts.get("running") or counts.get("queued"):
        status = "running"
        headline = "工作流正在运行"
    elif metric_items:
        status = "done"
        headline = "已捕获运行指标"
    elif warnings:
        status = "warning"
        headline = "运行预案可执行但仍有提示"
    else:
        status = "ready"
        headline = "运行预案已就绪"

    metric_value = " · ".join(str(item.get("value") or "") for item in metric_items[:3] if isinstance(item, dict) and str(item.get("value") or "").strip())
    env_value = str((env_items[0] if env_items else {}).get("value") or "等待环境证据")
    dataset_value = str((dataset_items[0] if dataset_items else {}).get("value") or "等待数据证据")
    gpu_value = str((gpu_items[0] if gpu_items else {}).get("value") or "等待 GPU 证据")
    highlights = [
        workspace_report_highlight(
            "就绪度",
            f"{status_counts.get('ready', 0) + status_counts.get('done', 0)} 项就绪",
            f"{status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
            "blocked" if status_counts.get("blocked") else "ready",
        ),
        workspace_report_highlight(
            "运行预案",
            str(run_plan.get("summary") or "等待生成"),
            "完整运行前的节点和阶段预览。",
            str(run_plan.get("status") or "draft"),
        ),
        workspace_report_highlight(
            "核心指标",
            metric_value or "等待运行指标",
            f"{safe_int(metric_group.get('count'), 0)} 条指标证据",
            "ready" if metric_items else "draft",
        ),
        workspace_report_highlight(
            "数据/环境/GPU",
            dataset_value,
            f"环境：{env_value} · GPU：{gpu_value}",
            "ready" if dataset_items or env_items or gpu_items else "draft",
        ),
        workspace_report_highlight(
            "产物",
            f"{safe_int(artifact_group.get('count'), 0)} 条产物/日志证据",
            str((artifact_items[0] if artifact_items else {}).get("value") or "等待产物收集"),
            "ready" if artifact_items else "draft",
        ),
    ]

    next_actions: list[dict[str, Any]] = []
    if blocking:
        first = blocking[0]
        next_actions.append(
            workspace_report_next_action(
                "处理运行阻塞",
                str(first.get("detail") or first.get("title") or ""),
                str(first.get("action") or "先运行自动发现或补齐节点配置。"),
                "blocked",
            )
        )
    if not any(safe_int(item.get("count"), 0) for item in evidence if isinstance(item, dict)):
        next_actions.append(
            workspace_report_next_action(
                "运行自动发现",
                "先收集路径、数据、环境、GPU 和产物入口证据。",
                "点击“自动发现”。",
                "ready",
            )
        )
    if not metric_items and (counts.get("done") or counts.get("running") or counts.get("queued")):
        next_actions.append(
            workspace_report_next_action(
                "补指标证据",
                "已有运行记录，但还没有解析到核心指标。",
                "查看运行日志或补 metric_paths 后运行 artifact.collect / eval.report。",
                "warning",
            )
        )
    if warnings and not blocking:
        first_warning = warnings[0]
        next_actions.append(
            workspace_report_next_action(
                "处理提示项",
                str(first_warning.get("detail") or first_warning.get("title") or ""),
                str(first_warning.get("action") or "可以先运行自动发现补齐证据。"),
                "warning",
            )
        )
    if not next_actions:
        next_actions.append(
            workspace_report_next_action(
                "整理最终报告",
                "关键证据已经进入驾驶舱，可以汇总运行命令、指标、产物路径和复跑建议。",
                "运行 eval.report 或把证据交给报告 Agent。",
                "ready",
            )
        )

    return {
        "status": status,
        "title": "复现/部署报告草稿",
        "headline": headline,
        "summary": f"{safe_int(counts.get('done'), 0)} 完成 · {safe_int(counts.get('running'), 0)} 运行 · {safe_int(counts.get('failed'), 0)} 失败 · {safe_int(metric_group.get('count'), 0)} 指标",
        "highlights": highlights,
        "next_actions": next_actions[:5],
        "blockers": blocking[:6],
        "warnings": warnings[:6],
    }

def derive_workspace_execution_readiness(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    advance: dict[str, Any],
    agent_topology: dict[str, Any],
    resource_orchestration: dict[str, Any],
) -> dict[str, Any]:
    from ..cockpit.fsm import workspace_readiness_message, workspace_workflow_blocking_checks

    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    queued_count = safe_int(counts.get("queued"), 0)
    starting_count = safe_int(counts.get("starting"), 0)
    running_count = safe_int(counts.get("running"), 0)
    active_count = queued_count + starting_count + running_count + safe_int(counts.get("blocked"), 0)
    failed_count = safe_int(counts.get("failed"), 0) + safe_int(counts.get("stopped"), 0)
    done_count = safe_int(counts.get("done"), 0)
    discovery_run_count = sum(
        safe_int(node.get("run_count"), 0)
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_DISCOVERY_NODE_KINDS
    )
    evidence_count = sum(
        safe_int(item.get("count"), 0)
        for item in evidence
        if isinstance(item, dict)
    )
    artifact_count = safe_int(workspace_evidence_group(evidence, "artifact").get("count"), 0)
    metric_count = safe_int(workspace_evidence_group(evidence, "metric").get("count"), 0)
    blocked_checks = workspace_workflow_blocking_checks({"checks": checks})
    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    run_warnings = run_plan.get("warnings") if isinstance(run_plan.get("warnings"), list) else []
    topology_gaps = agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []
    topology_blocking = [
        item for item in topology_gaps
        if isinstance(item, dict) and str(item.get("status") or "") in {"blocked", "failed"}
    ]
    resource_items = resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else []
    resource_blocking = [
        item for item in resource_items
        if isinstance(item, dict) and str(item.get("status") or "") in {"blocked", "failed"}
    ]
    resource_warnings = [
        item for item in resource_items
        if isinstance(item, dict) and str(item.get("status") or "") in {"warning", "draft"}
    ]
    run_node_count = safe_int(run_plan.get("node_count"), 0)
    first_blocker = next(
        (
            item for item in [*blocked_checks, *run_blocking, *resource_blocking, *topology_blocking]
            if isinstance(item, dict)
        ),
        {},
    )
    first_warning = next(
        (
            item for item in [*run_warnings, *resource_warnings, *topology_gaps]
            if isinstance(item, dict)
        ),
        {},
    )

    if failed_count:
        gate_status = "failed"
        gate_title = "失败任务待复查"
        gate_detail = f"{failed_count} 个任务失败或停止，继续前先看日志和节点输出。"
        gate_action = "打开失败任务日志，修正配置后再自动推进。"
    elif active_count:
        gate_status = "running"
        gate_title = "当前任务未结束"
        gate_detail = f"{queued_count} 个排队 · {running_count} 个运行，先等当前执行稳定。"
        gate_action = "观察当前任务，完成后再次自动推进。"
    elif blocked_checks:
        gate_status = "blocked"
        gate_title = "硬门禁未通过"
        gate_detail = workspace_readiness_message(blocked_checks)
        gate_action = str(first_blocker.get("action") or "补齐节点链、Agent 归属或运行命令后再提交完整链。")
    else:
        gate_status = "ready"
        gate_title = "硬门禁已通过"
        gate_detail = "节点链、Agent 归属和运行命令没有硬阻塞。"
        gate_action = "可以继续自动推进；若还没有 discovery 记录，会先提交安全发现。"

    if run_blocking:
        force_status = "blocked"
        force_title = "强制运行仍会被节点校验挡住"
        force_action = "先处理节点 payload 阻塞，再考虑 force_run。"
    elif blocked_checks:
        force_status = "warning"
        force_title = "强制运行会跳过硬门禁"
        force_action = "只在你确认风险可控时使用 force_run，提交前仍会逐节点校验 payload。"
    elif run_warnings or resource_warnings or topology_gaps:
        force_status = "warning"
        force_title = "不建议强制运行"
        force_action = str(first_warning.get("action") or "先处理提示项，降低运行失败概率。")
    else:
        force_status = "ready"
        force_title = "无需强制运行"
        force_action = "按正常自动推进或运行工作流即可。"
    force_run = {
        "status": force_status,
        "title": force_title,
        "detail": f"{len(blocked_checks)} 个硬门禁 · {len(run_blocking)} 个节点阻塞 · {len(run_warnings)} 个提示",
        "action": force_action,
        "blockers": run_blocking[:6],
        "warnings": run_warnings[:6],
    }

    if active_count:
        discovery_status = "running"
        discovery_title = "发现/执行任务进行中"
        discovery_action = "等待当前任务完成后再继续推进。"
    elif discovery_run_count:
        discovery_status = "done"
        discovery_title = "已有发现链记录"
        discovery_action = "可以回填发现证据，再提交完整执行链。"
    else:
        discovery_status = "ready"
        discovery_title = "可以提交安全发现"
        discovery_action = "点击自动推进或自动发现，先跑 repo/path/data/env/GPU/artifact 安全节点。"

    if evidence_count:
        apply_status = "ready"
        apply_title = "发现证据可回填"
        apply_action = "点击回填建议/发现，或由自动推进在完整运行前自动回填。"
    elif discovery_run_count:
        apply_status = "warning"
        apply_title = "发现记录缺少可用证据"
        apply_action = "查看发现节点输出，补数据根、环境清单或产物路径。"
    else:
        apply_status = "draft"
        apply_title = "等待发现证据"
        apply_action = "先提交安全发现，再回填路径、数据、环境和产物证据。"

    resource_status = str(resource_orchestration.get("status") or "draft")
    resource_next = resource_orchestration.get("next_action") if isinstance(resource_orchestration.get("next_action"), dict) else {}
    resource_summary = str(resource_orchestration.get("summary") or "等待资源调度")

    if active_count:
        full_run_status = "running"
        full_run_title = "完整链正在执行或排队"
        full_run_action = "先观察当前任务输出。"
    elif failed_count:
        full_run_status = "failed"
        full_run_title = "完整链存在失败记录"
        full_run_action = "打开失败日志，修正后再重试。"
    else:
        full_run_status = str(run_plan.get("status") or "draft")
        full_run_title = "完整执行链已就绪" if full_run_status == "ready" else "完整执行链未就绪"
        full_run_action = (
            "点击自动推进或运行工作流提交完整链。"
            if full_run_status == "ready"
            else str(first_blocker.get("action") or "先处理运行预案中的阻塞项。")
        )

    if metric_count:
        collect_status = "done"
        collect_title = "指标已回收"
        collect_action = "可以整理复现/部署报告。"
    elif artifact_count:
        collect_status = "ready"
        collect_title = "产物入口已出现"
        collect_action = "继续运行 artifact.collect / eval.report 汇总指标。"
    elif active_count:
        collect_status = "running"
        collect_title = "等待运行产物"
        collect_action = "任务结束后自动或手动收集产物和指标。"
    elif failed_count:
        collect_status = "warning"
        collect_title = "失败后缺少可用产物"
        collect_action = "先复查失败日志，再收集可用的输出片段。"
    elif done_count:
        collect_status = "warning"
        collect_title = "运行完成但指标不足"
        collect_action = "补 artifact_paths / metric_paths 后运行产物收集。"
    else:
        collect_status = "draft"
        collect_title = "等待产物/指标回收"
        collect_action = "完整运行完成后收集 logs、checkpoints、metrics 和报告。"

    steps = [
        workspace_execution_readiness_step(
            "safe_discovery",
            "安全发现",
            discovery_status,
            discovery_title,
            f"{discovery_run_count} 次发现节点运行 · {evidence_count} 条证据",
            discovery_action,
            evidence_count=evidence_count,
            job_count=discovery_run_count,
        ),
        workspace_execution_readiness_step(
            "defaults_evidence",
            "默认/证据回填",
            apply_status,
            apply_title,
            f"{evidence_count} 条发现证据可用于路径、环境、数据和产物默认值。",
            apply_action,
            evidence_count=evidence_count,
        ),
        workspace_execution_readiness_step(
            "resource_binding",
            "资源调度",
            resource_status,
            str(resource_next.get("title") or resource_summary),
            str(resource_next.get("detail") or resource_summary),
            str(resource_next.get("action") or "补齐路径、数据、环境、GPU 和产物配置。"),
            blocker_count=len(resource_blocking),
            warning_count=len(resource_warnings),
        ),
        workspace_execution_readiness_step(
            "hard_gate",
            "门禁检查",
            gate_status,
            gate_title,
            gate_detail,
            gate_action,
            blocker_count=len(blocked_checks),
        ),
        workspace_execution_readiness_step(
            "full_run",
            "完整执行链",
            full_run_status,
            full_run_title,
            str(run_plan.get("summary") or "等待运行预案"),
            full_run_action,
            blocker_count=len(run_blocking),
            warning_count=len(run_warnings),
            node_count=run_node_count,
        ),
        workspace_execution_readiness_step(
            "collect_report",
            "产物/指标回收",
            collect_status,
            collect_title,
            f"{artifact_count} 条产物证据 · {metric_count} 条指标证据",
            collect_action,
            evidence_count=artifact_count + metric_count,
        ),
    ]

    if failed_count:
        status = "failed"
    elif active_count:
        status = "running"
    elif blocked_checks or run_blocking or resource_blocking or topology_blocking:
        status = "blocked"
    elif run_warnings or resource_warnings or topology_gaps:
        status = "warning"
    else:
        status = "ready"

    ready_count = sum(1 for step in steps if str(step.get("status") or "") in {"ready", "done"})
    blockers = [
        workspace_enrich_readiness_issue(workspace, item)
        for item in [*blocked_checks, *run_blocking, *resource_blocking, *topology_blocking]
        if isinstance(item, dict)
    ]
    warnings = [
        workspace_enrich_readiness_issue(workspace, item)
        for item in [*run_warnings, *resource_warnings, *topology_gaps]
        if isinstance(item, dict)
    ]
    gate_blockers = [workspace_enrich_readiness_issue(workspace, item) for item in blocked_checks[:6] if isinstance(item, dict)]
    force_run["blockers"] = [workspace_enrich_readiness_issue(workspace, item) for item in force_run.get("blockers", []) if isinstance(item, dict)]
    force_run["warnings"] = [workspace_enrich_readiness_issue(workspace, item) for item in force_run.get("warnings", []) if isinstance(item, dict)]
    return {
        "status": status,
        "summary": f"{ready_count}/{len(steps)} 项准备完成 · {len(blockers)} 阻塞 · {active_count} 活跃 · {failed_count} 失败",
        "steps": steps,
        "gate": {
            "status": gate_status,
            "title": gate_title,
            "detail": gate_detail,
            "action": gate_action,
            "blockers": gate_blockers,
        },
        "job_state": {
            "active_count": active_count,
            "queued_count": queued_count,
            "running_count": running_count,
            "failed_count": failed_count,
            "done_count": done_count,
            "discovery_run_count": discovery_run_count,
            "full_run_node_count": run_node_count,
            "last_job_id": str(execution.get("last_job_id") or "").strip(),
            "last_job_status": str(execution.get("last_job_status") or "").strip(),
        },
        "force_run": force_run,
        "next_action": advance,
        "blockers": blockers[:8],
        "warnings": warnings[:8],
    }
