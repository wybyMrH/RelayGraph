"""Cockpit — fsm helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .helpers import workspace_jobs_for_workspace, workspace_node_config_ready_status
from ..automation.advance import resolve_workspace_advance_bundle

def attach_workspace_cockpit(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any],
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    bundle = resolve_workspace_advance_bundle(workspace, execution, automation, jobs=jobs)
    next_action = bundle["next_action"]
    automation["advance"] = bundle["advance"]
    automation["cockpit"] = {
        "next_action": next_action,
        "chain": bundle["chain"],
        "summary": str(automation.get("summary") or "").strip(),
        "status": str(next_action.get("status") or automation.get("status") or "draft").strip() or "draft",
    }
    automation["next_action"] = next_action
    return automation

def workspace_workflow_blocking_checks(automation: dict[str, Any]) -> list[dict[str, Any]]:
    hard_gate_ids = {"starter_chain", "agents", "run"}
    checks = automation.get("checks") if isinstance(automation.get("checks"), list) else []
    return [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed"}
    ]

def workspace_readiness_message(blocked_checks: list[dict[str, Any]]) -> str:
    labels = [
        str(check.get("label") or check.get("title") or check.get("id") or "").strip()
        for check in blocked_checks
        if isinstance(check, dict)
    ]
    labels = [label for label in labels if label]
    if not labels:
        return "工作流运行前检查未通过"
    return "工作流运行前检查未通过：" + "、".join(labels[:6])

def _workspace_cockpit_facts(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any],
    bound_jobs: list[dict[str, Any]],
    active_jobs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    playbook = automation.get("playbook") if isinstance(automation.get("playbook"), dict) else {}
    current = playbook.get("current_action") if isinstance(playbook.get("current_action"), dict) else {}
    advance = automation.get("advance") if isinstance(automation.get("advance"), dict) else {}
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    return [
        {
            "label": "阶段",
            "value": str(current.get("title") or advance.get("title") or "自动推进").strip(),
            "status": str(current.get("status") or advance.get("status") or automation.get("status") or "draft").strip(),
        },
        {
            "label": "任务",
            "value": f"{len(bound_jobs)} 个 · {len(active_jobs)} 活跃",
            "status": "running" if active_jobs else "ready",
        },
        {
            "label": "节点",
            "value": (
                f"{safe_int(counts.get('done'), 0)}/"
                f"{len(nodes)} 完成"
            ),
            "status": "failed" if safe_int(counts.get("failed"), 0) else ("running" if active_jobs else "ready"),
        },
    ]

def resolve_workspace_advance_fsm(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Unified FSM for automation.advance and cockpit.next_action."""
    automation = automation if isinstance(automation, dict) else {}
    workspace_id = str(workspace.get("id") or "").strip()
    checks = automation.get("checks") if isinstance(automation.get("checks"), list) else []
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    evidence_backfill = automation.get("evidence_backfill") if isinstance(automation.get("evidence_backfill"), dict) else {}
    playbook = automation.get("playbook") if isinstance(automation.get("playbook"), dict) else {}
    current = playbook.get("current_action") if isinstance(playbook.get("current_action"), dict) else {}
    readiness = automation.get("execution_readiness") if isinstance(automation.get("execution_readiness"), dict) else {}
    gate = readiness.get("gate") if isinstance(readiness.get("gate"), dict) else {}
    focus_node_id = str(execution.get("current_node_id") or "").strip()
    last_job_id = str(execution.get("last_job_id") or "").strip()

    bound_jobs = workspace_jobs_for_workspace(workspace_id, jobs)
    active_jobs = [
        job for job in bound_jobs
        if str(job.get("status") or "") in {"queued", "blocked", "starting", "running"}
    ]
    failed_jobs = [
        job for job in bound_jobs
        if str(job.get("status") or "") in {"failed", "stopped"}
    ]
    blocked_checks = workspace_workflow_blocking_checks(automation) if checks else []
    gate_blockers = [
        item for item in (
            *(gate.get("blockers") if isinstance(gate.get("blockers"), list) else []),
            *(readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []),
            *blocked_checks,
        )
        if isinstance(item, dict)
    ]
    facts = _workspace_cockpit_facts(workspace, execution, automation, bound_jobs, active_jobs)
    base: dict[str, Any] = {
        "focus_node_id": focus_node_id,
        "blocked_checks": blocked_checks[:6],
        "gate_blockers": gate_blockers[:4],
        "facts": facts,
        "active_jobs": active_jobs,
        "failed_jobs": failed_jobs,
    }

    if active_jobs:
        primary_job_id = str(active_jobs[0].get("id") or last_job_id or "").strip()
        return {
            **base,
            "action": "watch",
            "status": "running",
            "phase": "运行中",
            "title": f"{len(active_jobs)} 个任务正在执行",
            "reason": "当前有任务在队列或运行，先观察输出再继续推进。",
            "next_action": "打开最近任务日志，等当前步骤完成后再自动推进。",
            "primary_job_id": primary_job_id,
        }

    if failed_jobs:
        failed_job_id = str(failed_jobs[0].get("id") or "").strip()
        return {
            **base,
            "action": "review_failed",
            "status": "failed",
            "phase": "失败复查",
            "title": f"{len(failed_jobs)} 个任务异常",
            "reason": "存在失败或停止的任务，继续前需要确认日志和节点配置。",
            "next_action": str(
                failed_jobs[0].get("error")
                or execution.get("latest_error")
                or "查看失败任务日志，修正配置后再次自动推进。"
            ).strip(),
            "failed_job_id": failed_job_id,
        }

    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    discovery_runs = sum(
        safe_int(node.get("run_count"), 0)
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_DISCOVERY_NODE_KINDS
    )
    if not discovery_runs:
        return {
            **base,
            "action": "discover",
            "status": "ready",
            "phase": "发现",
            "title": "提交安全发现",
            "reason": "还没有发现链证据，先探测源码、路径、数据、环境、GPU 和产物入口。",
            "next_action": "点击自动推进提交发现链，完成后再次自动推进。",
        }

    if blocked_checks:
        blocker = blocked_checks[0]
        blocker_node_kind = str(blocker.get("node_kind") or "").strip()
        focus_from_blocker = ""
        for chain_node in derive_workspace_cockpit_chain(workspace, execution):
            if blocker_node_kind and chain_node.get("kind") == blocker_node_kind:
                focus_from_blocker = str(chain_node.get("id") or "").strip()
                break
        return {
            **base,
            "action": "blocked",
            "status": "blocked",
            "phase": "门禁",
            "title": str(blocker.get("label") or blocker.get("title") or "运行门禁阻塞").strip(),
            "reason": workspace_readiness_message(blocked_checks),
            "next_action": str(blocker.get("action") or "补齐节点链、Agent 归属或运行命令。").strip(),
            "focus_node_id": focus_from_blocker or focus_node_id,
            "blocker": blocker,
        }

    backfill_ready = safe_int(evidence_backfill.get("ready_count"), 0) > 0
    if backfill_ready and str(evidence_backfill.get("status") or "") in {"ready", "warning"}:
        return {
            **base,
            "action": "backfill",
            "status": "ready",
            "phase": "回填",
            "title": "应用发现证据",
            "reason": str(evidence_backfill.get("summary") or "发现证据已就绪，可写回节点配置。").strip(),
            "next_action": "回填路径、环境、GPU 和运行入口后再提交完整链。",
        }

    if bundle.get("ready_to_execute"):
        bundle_detail = bundle.get("next_action") if isinstance(bundle.get("next_action"), dict) else {}
        return {
            **base,
            "action": "execute_bundle",
            "status": "ready",
            "phase": "执行",
            "title": "提交完整运行",
            "reason": str(bundle_detail.get("detail") or "执行包已就绪。").strip(),
            "next_action": "门禁已通过，可以提交完整工作流。",
        }

    playbook_label = str(current.get("label") or "").strip()
    playbook_action = str(current.get("action") or "").strip()
    if playbook_label and playbook_action:
        return {
            **base,
            "action": "playbook",
            "status": str(current.get("status") or playbook.get("status") or automation.get("status") or "draft").strip(),
            "phase": str(current.get("phase") or playbook_label).strip(),
            "title": str(current.get("title") or playbook_label).strip(),
            "reason": str(current.get("detail") or playbook.get("summary") or "").strip(),
            "next_action": str(current.get("detail") or "按当前 playbook 步骤推进。").strip(),
            "focus_node_id": str(current.get("node_id") or focus_node_id).strip(),
            "playbook_current": current,
        }

    return {
        **base,
        "action": "run",
        "status": "ready",
        "phase": "执行",
        "title": "整理并提交运行",
        "reason": "已有发现记录且门禁没有阻塞，自动推进会先回填证据再提交完整执行链。",
        "next_action": "点击自动推进后跟踪第一个运行任务输出。",
    }

def workspace_advance_decision(
    action: str,
    title: str,
    reason: str,
    next_action: str,
    *,
    status: str = "ready",
) -> dict[str, str]:
    return {
        "action": str(action or "").strip(),
        "status": str(status or "ready").strip() or "ready",
        "title": str(title or "").strip(),
        "reason": str(reason or "").strip(),
        "next_action": str(next_action or "").strip(),
    }

def workspace_cockpit_decision_from_public_workspace(public_workspace: dict[str, Any]) -> dict[str, str]:
    automation = public_workspace.get("automation") if isinstance(public_workspace.get("automation"), dict) else {}
    advance = automation.get("advance") if isinstance(automation.get("advance"), dict) else {}
    if advance:
        return advance
    return workspace_advance_decision("run", "自动推进", "等待系统判断下一步。", "点击自动推进。")

def workspace_next_action_button(
    label: str,
    action: str,
    *,
    tab: str = "",
    node_id: str = "",
    job_id: str = "",
    server_id: str = "",
    tone: str = "primary",
    title: str = "",
) -> dict[str, str]:
    return {
        "label": str(label or "").strip(),
        "action": str(action or "").strip(),
        "tab": str(tab or "").strip(),
        "node_id": str(node_id or "").strip(),
        "job_id": str(job_id or "").strip(),
        "server_id": str(server_id or "").strip(),
        "tone": str(tone or "primary").strip() or "primary",
        "title": str(title or label or "").strip(),
    }

def derive_workspace_cockpit_chain(
    workspace: dict[str, Any],
    execution: dict[str, Any],
) -> list[dict[str, Any]]:
    execution_nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    source_nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    source_index = {
        str(item.get("id") or "").strip(): item
        for item in source_nodes
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    chain: list[dict[str, Any]] = []
    for node in execution_nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        source = source_index.get(node_id) or {}
        config_ready = workspace_node_config_ready_status(workspace, {**source, **node})
        chain.append(
            {
                "id": node_id,
                "kind": str(node.get("kind") or source.get("kind") or "").strip(),
                "title": str(node.get("title") or source.get("title") or node.get("kind") or "").strip(),
                "status": str(node.get("status") or "pending").strip() or "pending",
                "config_ready": config_ready,
                "agent_id": str(node.get("agent_id") or "").strip(),
                "agent_name": str(node.get("agent_name") or "").strip(),
                "job_id": str(node.get("job_id") or "").strip(),
                "job_status": str(node.get("job_status") or "").strip(),
                "run_count": safe_int(node.get("run_count"), 0),
                "error": str(node.get("error") or "").strip(),
            }
        )
    return chain

def workspace_next_action_from_fsm(
    fsm: dict[str, Any],
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any],
) -> dict[str, Any]:
    """Map unified FSM state to cockpit primary/secondary buttons."""
    action = str(fsm.get("action") or "").strip()
    focus_node_id = str(fsm.get("focus_node_id") or "").strip()
    gate_blockers = fsm.get("gate_blockers") if isinstance(fsm.get("gate_blockers"), list) else []
    facts = fsm.get("facts") if isinstance(fsm.get("facts"), list) else []
    blocked_checks = fsm.get("blocked_checks") if isinstance(fsm.get("blocked_checks"), list) else []
    playbook_current = fsm.get("playbook_current") if isinstance(fsm.get("playbook_current"), dict) else {}

    if action == "watch":
        primary_job_id = str(fsm.get("primary_job_id") or "").strip()
        return {
            "status": "running",
            "phase": fsm.get("phase") or "运行中",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": [],
            "primary": workspace_next_action_button(
                "打开输出",
                "open-last-workspace-log",
                job_id=primary_job_id,
                title="打开当前实例最近绑定任务的日志输出。",
            ),
            "secondary": workspace_next_action_button(
                "执行链",
                "focus-workspace-execution-board",
                tone="secondary",
                title="查看节点链与当前阶段状态。",
            ),
            "facts": facts,
        }

    if action == "review_failed":
        failed_job_id = str(fsm.get("failed_job_id") or "").strip()
        return {
            "status": "failed",
            "phase": fsm.get("phase") or "失败复查",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": gate_blockers[:4],
            "primary": workspace_next_action_button(
                "查看运行记录",
                "switch-workspace-tab",
                tab="runs",
                job_id=failed_job_id,
                title="查看失败任务输出和错误信息。",
            ),
            "secondary": workspace_next_action_button(
                "自动推进",
                "advance-workspace-automation",
                tone="secondary",
                title="让系统复查失败状态并给出下一步。",
            ),
            "facts": facts,
        }

    if action == "discover":
        return {
            "status": str(fsm.get("status") or "ready").strip() or "ready",
            "phase": fsm.get("phase") or "发现",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": gate_blockers[:4],
            "primary": workspace_next_action_button(
                "运行自动发现",
                "run-workspace-discovery",
                title="提交安全发现链，收集路径、数据、环境和 GPU 证据。",
            ),
            "secondary": workspace_next_action_button(
                "自动推进",
                "advance-workspace-automation",
                tone="secondary",
                title="由系统自动决定发现、回填与后续步骤。",
            ),
            "facts": facts,
        }

    if action == "blocked":
        blocker = fsm.get("blocker") if isinstance(fsm.get("blocker"), dict) else (blocked_checks[0] if blocked_checks else {})
        return {
            "status": "blocked",
            "phase": fsm.get("phase") or "门禁",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": blocked_checks[:6],
            "primary": workspace_next_action_button(
                "处理阻塞项",
                "focus-workspace-execution-board",
                node_id=focus_node_id,
                title="定位到阻塞节点并查看配置与证据。",
            ),
            "secondary": workspace_next_action_button(
                "分层配置",
                "switch-workspace-tab",
                tab="workflow",
                tone="secondary",
                title="打开工作流页检查节点链与运行入口。",
            ),
            "facts": facts,
        }

    if action == "backfill":
        return {
            "status": "ready",
            "phase": fsm.get("phase") or "回填",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": gate_blockers[:4],
            "primary": workspace_next_action_button(
                "回填建议/发现",
                "apply-workspace-automation",
                title="把默认建议和发现证据写回节点配置。",
            ),
            "secondary": workspace_next_action_button(
                "自动推进",
                "advance-workspace-automation",
                tone="secondary",
                title="自动回填并继续判断是否提交完整运行。",
            ),
            "facts": facts,
        }

    if action == "execute_bundle":
        return {
            "status": "ready",
            "phase": fsm.get("phase") or "执行",
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": gate_blockers[:4],
            "primary": workspace_next_action_button(
                "运行工作流",
                "run-selected-workspace",
                title="在门禁通过后提交完整执行链。",
            ),
            "secondary": workspace_next_action_button(
                "自动推进",
                "advance-workspace-automation",
                tone="secondary",
                title="由系统自动整理并提交运行。",
            ),
            "facts": facts,
        }

    if action == "playbook" and playbook_current:
        return {
            "status": str(fsm.get("status") or automation.get("status") or "draft").strip(),
            "phase": str(fsm.get("phase") or "").strip(),
            "title": fsm.get("title") or "",
            "reason": fsm.get("reason") or "",
            "detail": fsm.get("next_action") or "",
            "focus_node_id": focus_node_id,
            "blocked_checks": gate_blockers[:4],
            "primary": workspace_next_action_button(
                str(playbook_current.get("label") or "继续").strip(),
                str(playbook_current.get("action") or "advance-workspace-automation").strip(),
                node_id=str(playbook_current.get("node_id") or "").strip(),
                server_id=str(playbook_current.get("server_id") or "").strip(),
                title=str(playbook_current.get("detail") or playbook_current.get("label") or "").strip(),
            ),
            "secondary": workspace_next_action_button(
                "自动推进",
                "advance-workspace-automation",
                tone="secondary",
                title="交给系统自动判断下一步。",
            ),
            "facts": facts,
        }

    return {
        "status": str(fsm.get("status") or automation.get("status") or "draft").strip() or "draft",
        "phase": fsm.get("phase") or "执行",
        "title": fsm.get("title") or "",
        "reason": fsm.get("reason") or "",
        "detail": fsm.get("next_action") or "",
        "focus_node_id": focus_node_id,
        "blocked_checks": gate_blockers[:4],
        "primary": workspace_next_action_button(
            "自动推进",
            "advance-workspace-automation",
            title=str(fsm.get("next_action") or "根据当前门禁自动决定下一步。").strip(),
        ),
        "secondary": workspace_next_action_button(
            "运行工作流",
            "run-selected-workspace",
            tone="secondary",
            title="直接提交完整执行链（需门禁通过）。",
        ),
        "facts": facts,
    }

def workspace_next_action(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any],
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Single source of truth for cockpit primary/secondary actions."""
    return resolve_workspace_advance_bundle(workspace, execution, automation, jobs=jobs)["next_action"]

def derive_workspace_cockpit(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    automation: dict[str, Any],
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    next_action = workspace_next_action(workspace, execution, automation, jobs=jobs)
    chain = derive_workspace_cockpit_chain(workspace, execution)
    return {
        "next_action": next_action,
        "chain": chain,
        "summary": str(automation.get("summary") or "").strip(),
        "status": str(next_action.get("status") or automation.get("status") or "draft").strip() or "draft",
    }
