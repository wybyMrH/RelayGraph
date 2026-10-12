"""Workspace state — workflow operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from ..registry_pkg.provider_profiles import provider_profile_health
from ...orchestration.run_store import content_hash


def _workspace_env_prepare_failure_checks(execution: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    checks: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("kind") or "").strip() != "env.prepare":
            continue
        status = str(node.get("status") or "").strip()
        job_status = str(node.get("job_status") or "").strip()
        if status != "failed" and job_status not in {"failed", "stopped"}:
            continue
        error = str(node.get("error") or "").strip()
        detail = error or "最近一次 env.prepare 失败或被停止；复查日志后再完整运行，或明确 force 重试。"
        checks.append(
            {
                "id": "env_prepare_failed",
                "label": "环境准备",
                "status": "blocked",
                "title": "环境准备失败未复查",
                "detail": detail,
                "action": "打开 env.prepare 最近任务日志，修复 setup_command/环境后再提交完整工作流。",
                "node_kind": "env.prepare",
                "node_id": str(node.get("id") or "").strip(),
                "job_id": str(node.get("job_id") or "").strip(),
            }
        )
    return checks


def _workspace_agent_execution_checks(
    workspace: dict[str, Any],
    nodes: list[dict[str, Any]],
    provider_profiles: list[dict[str, Any]],
    executor_prefer: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    tools = normalize_workspace_tools(workspace.get("tools"), existing=workspace.get("tools"))
    tool_ids = [
        str(item.get("id") or "").strip()
        for item in tools
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    agents = normalize_workspace_agents(workspace.get("agents"), existing=workspace.get("agents"), tool_ids=tool_ids)
    agent_index = {
        str(agent.get("id") or "").strip(): agent
        for agent in agents
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    profile_index = {
        str(profile.get("id") or "").strip(): profile
        for profile in provider_profiles
        if isinstance(profile, dict) and str(profile.get("id") or "").strip()
    }

    def add_check(
        node: dict[str, Any],
        check_id: str,
        title: str,
        detail: str,
        action: str,
        *,
        agent_id: str = "",
        provider_profile_id: str = "",
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "label": str(node.get("title") or node.get("kind") or "Agent 节点").strip(),
                "status": "blocked",
                "title": title,
                "detail": detail,
                "action": action,
                "node_kind": str(node.get("kind") or "").strip(),
                "node_id": str(node.get("id") or "").strip(),
                "agent_id": agent_id,
                "provider_profile_id": provider_profile_id,
            }
        )

    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or "").strip()
        if (executor_prefer not in {"job", "skip"} and kind in AGENT_EXECUTABLE_KINDS
                and str(handler.get("mode") or "").strip().lower() == "agent" and not agent_id):
            add_check(node, "agent_handler_not_configured", "Agent 节点未完成绑定",
                      "已选择 Agent 执行但没有 agent_id。", "绑定可用 Agent 或明确改为 system/human。")
            continue
        if resolve_node_executor_mode(node, executor_prefer) != "agent":
            continue
        node_title = str(node.get("title") or kind or "Agent 节点").strip()
        if kind not in AGENT_EXECUTABLE_KINDS:
            add_check(
                node,
                "agent_executor_mode_invalid",
                "节点不能强制走 Agent",
                f"{node_title} 是 {kind or 'unknown'}，必须通过受控 job/runtime 队列执行。",
                "把 executor_mode 改回 auto/job，重节点不要直接交给 Agent 执行。",
                agent_id=agent_id,
            )
            continue
        if str(handler.get("mode") or "human").strip().lower() != "agent" or not agent_id:
            add_check(
                node,
                "agent_handler_not_configured",
                "Agent 节点未完成绑定",
                f"{node_title} 没有配置 handler.mode=agent 和 agent_id。",
                "在配置中心把该节点绑定到可用 Agent，或改回 job 执行。",
                agent_id=agent_id,
            )
            continue
        agent = agent_index.get(agent_id)
        if not agent:
            add_check(
                node,
                "agent_not_found",
                "Agent 不存在",
                f"{node_title} 绑定的 Agent {agent_id} 不在当前实例快照中。",
                "恢复默认 Agent 或在配置中心重新选择节点执行者。",
                agent_id=agent_id,
            )
            continue
        if agent.get("enabled") is False:
            add_check(
                node,
                "agent_disabled",
                "Agent 已停用",
                f"{str(agent.get('name') or agent_id).strip()} 已绑定到 {node_title}，但当前处于停用状态。",
                "启用该 Agent，或把节点交给其他可用 Agent。",
                agent_id=agent_id,
            )
            continue
        route = workspace_model_route_for_agent(model, agent)
        profile_id = str(route.get("effective_profile_id") or "").strip()
        if not profile_id:
            add_check(
                node,
                "provider_route_not_configured",
                "AI 路由未配置",
                f"{node_title} 需要真实模型调用，但 workspace/agent 没有有效 Provider Profile。",
                "在配置中心设置项目默认 Provider Profile，或启用 agent_override 并给 Agent 绑定 Profile。",
                agent_id=agent_id,
            )
            continue
        profile = profile_index.get(profile_id)
        if not profile:
            add_check(
                node,
                "provider_route_not_found",
                "AI 路由指向不存在的 Profile",
                f"{node_title} 指向 Provider Profile {profile_id}，但该 Profile 已不存在。",
                "在配置中心重新选择可用 Provider Profile。",
                agent_id=agent_id,
                provider_profile_id=profile_id,
            )
            continue
        health = provider_profile_health(profile)
        if not health.get("ready"):
            missing_fields = [
                str(item or "").strip()
                for item in (health.get("missing_fields") if isinstance(health.get("missing_fields"), list) else [])
                if str(item or "").strip()
            ]
            detail = f"{node_title} 使用的 Provider Profile {profile.get('name') or profile_id} 未就绪。"
            if missing_fields:
                detail = f"{detail} 缺少：{', '.join(missing_fields)}。"
            add_check(
                node,
                "provider_route_not_ready",
                "AI 路由未就绪",
                detail,
                "在配置中心补齐 Provider Profile 后再运行完整工作流。",
                agent_id=agent_id,
                provider_profile_id=profile_id,
            )
    return checks


class WorkflowMixin:
    def run_workspace_workflow(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        request_id = requested_payload.get("request_id", "")
        if not isinstance(request_id, str) or (request_id and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", request_id)):
            raise ValueError("request_id must be a safe nonempty identifier of at most 128 characters")
        request_hash = content_hash({key: value for key, value in requested_payload.items() if key != "request_id"})
        previous_run_id = self.execution_store.find_request(workspace_id, request_id, request_hash)
        if previous_run_id:
            return self.replay_workflow_response(workspace_id, previous_run_id)
        force = bool(requested_payload.get("force") or False)
        until_node_id = str(requested_payload.get("until_node_id") or requested_payload.get("target_node_id") or "").strip()
        auto_apply_raw = requested_payload.get("auto_apply", requested_payload.get("apply_defaults", True))
        auto_apply = (
            auto_apply_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(auto_apply_raw, str)
            else bool(auto_apply_raw)
        )
        apply_evidence_raw = requested_payload.get("apply_evidence", True)
        apply_evidence = (
            apply_evidence_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(apply_evidence_raw, str)
            else bool(apply_evidence_raw)
        )
        executor_mode_raw = str(requested_payload.get("executor_mode") or requested_payload.get("prefer") or "auto").strip().lower()
        executor_prefer = executor_mode_raw if executor_mode_raw in {"auto", "job", "agent", "skip"} else "auto"
        applied: list[dict[str, Any]] = []
        evidence_applied: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            provider_profiles_snapshot = copy.deepcopy(getattr(self, "provider_profiles", []))
            workspace = copy.deepcopy(current)
            if auto_apply:
                workspace, applied = apply_workspace_automation_defaults_to_payload(
                    workspace,
                    statuses_snapshot,
                    force=False,
                )
                if apply_evidence:
                    workspace, evidence_applied = apply_workspace_discovery_evidence_to_payload(
                        workspace,
                        jobs_snapshot,
                        force=False,
                    )
                    applied.extend(evidence_applied)
                index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                if index < 0:
                    raise ValueError("workspace not found")
                self.workspaces[index] = workspace
            nodes = [
                node for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
                if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_EXECUTABLE_NODE_KINDS
            ]
            target_node: dict[str, Any] | None = None
            if until_node_id:
                target_index = next(
                    (
                        index for index, node in enumerate(nodes)
                        if str(node.get("id") or "").strip() == until_node_id
                    ),
                    -1,
                )
                if target_index < 0:
                    raise ValueError("target node is not executable or not found")
                target_node = copy.deepcopy(nodes[target_index])
                nodes = nodes[:target_index + 1]
        if auto_apply:
            self.save_workspaces()
        if not nodes:
            raise ValueError("workspace has no executable nodes")

        planned_modes = [resolve_node_executor_mode(node, executor_prefer) for node in nodes]
        if not any(mode != "skip" for mode in planned_modes):
            raise ValueError("workspace has no runnable steps")

        if len(nodes) != 1 or planned_modes != ["job"]:
            raise WorkspaceWorkflowReadinessError(
                "当前持久工作流仅支持一个 Job；多节点及 Agent 链等待后续切片接入。",
                blocked_checks=[{"id": "workflow_plan_not_supported", "status": "blocked",
                                 "title": "工作流类型尚未接入", "detail": "请选择一个 Job 节点运行。",
                                 "action": "使用运行至节点选择单个 Job，或等待混合链接入。"}],
                workspace=self.workspace_public_payload(workspace), applied=applied,
                evidence_applied=evidence_applied,
            )

        # Compile the actual prefix, not later nodes or their historical failures.
        planned_workspace = copy.deepcopy(workspace)
        planned_workspace["nodes"] = copy.deepcopy(nodes)
        for planned_node in planned_workspace["nodes"]:
            if resolve_node_executor_mode(planned_node, executor_prefer) == "job":
                # Projection only: honor this request's actual executor without
                # changing the instance's configured handler or frozen source.
                planned_node["handler"] = {**(planned_node.get("handler") or {}), "mode": "system"}
        runtime_workspace = apply_workspace_job_runtime(planned_workspace, jobs_snapshot)
        execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
        automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        workflow_checks = workspace_workflow_blocking_checks(automation)
        requires_execution_package = workspace_nodes_require_execution_package(nodes)
        # Warnings no longer block a package; the legacy incomplete-package
        # option therefore cannot be used to bypass its actual hard errors.
        package_checks = workspace_execution_package_blocking_checks(
            automation,
            full_workflow=requires_execution_package or not until_node_id,
        )
        input_checks = [check for check in workflow_checks if check.get("id") == "workflow_input_reference"]
        if force:
            blocked_checks = [*package_checks, *input_checks]
        else:
            blocked_checks = [
                *workflow_checks,
                *package_checks,
                *_workspace_env_prepare_failure_checks(execution),
            ]
        if blocked_checks:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(blocked_checks),
                blocked_checks=blocked_checks,
                workspace=payload_workspace,
                applied=applied,
                evidence_applied=evidence_applied,
            )
        invalid_checks: list[dict[str, Any]] = []
        job_payloads: dict[str, dict[str, Any]] = {}
        for node in nodes:
            try:
                config = node.get("config") if isinstance(node.get("config"), dict) else {}
                requested_server = str(config.get("server_id") or "auto").strip()
                if requested_server != "auto" and not self.server_by_id(requested_server):
                    raise ValueError(f"unknown server: {requested_server}")
                if resolve_node_executor_mode(node, executor_prefer) != "job":
                    continue
                job_payload = self.workspace_node_job_payload(workspace, node, automation=automation)
                job_payloads[node["id"]] = job_payload
                if requires_execution_package:
                    invalid_checks.extend(
                        workspace_execution_package_runtime_binding_checks(
                            automation,
                            node,
                            job_payload,
                        )
                    )
            except ValueError as exc:
                invalid_checks.append(
                    {
                        "id": str(node.get("id") or "").strip(),
                        "label": str(node.get("title") or node.get("kind") or "节点").strip(),
                        "status": "blocked",
                        "title": str(node.get("title") or node.get("kind") or "节点").strip(),
                        "detail": str(exc),
                        "action": "先运行自动发现或补齐节点配置，再提交完整工作流。",
                        "node_kind": str(node.get("kind") or "").strip(),
                    }
                )
        if invalid_checks:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(invalid_checks),
                blocked_checks=invalid_checks,
                workspace=payload_workspace,
                applied=applied,
                evidence_applied=evidence_applied,
            )

        agent_execution_checks = _workspace_agent_execution_checks(
            workspace,
            nodes,
            provider_profiles_snapshot,
            executor_prefer,
        )
        if agent_execution_checks:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(agent_execution_checks),
                blocked_checks=agent_execution_checks,
                workspace=payload_workspace,
                applied=applied,
                evidence_applied=evidence_applied,
            )

        run_summary = (
            f"运行至节点 · {str((target_node or {}).get('title') or until_node_id).strip()}"
            if until_node_id else "工作流 · 1 Job"
        )
        initial_package = workspace_execution_bundle_result(automation, [])
        if until_node_id:
            initial_package["scope"] = {
                "mode": "run_to_node",
                "target_node_id": until_node_id,
                "target_node_title": str((target_node or {}).get("title") or "").strip(),
                "target_node_kind": str((target_node or {}).get("kind") or "").strip(),
            }
        run, created = self.register_planned_workflow_run(
            workspace, nodes, planned_modes, initial_package,
            request_id=request_id, request_hash=request_hash, summary=run_summary, executor_prefer=executor_prefer,
            job_payloads=job_payloads,
        )
        run_id = str(run.get("id") or "").strip()
        if not created:
            return self.replay_workflow_response(workspace_id, run_id)
        # Acceptance contains a durable complete plan, not a claim that a Job is done.
        # The existing scheduler is the only caller that advances the new graph.
        response = self.replay_workflow_response(workspace_id, run_id)
        response.update(applied=applied, evidence_applied=evidence_applied, replayed=False)
        return response
