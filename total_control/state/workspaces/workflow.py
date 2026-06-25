"""Workspace state — workflow operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class WorkflowMixin:
    def workflow_runner_callbacks(
        self,
        workspace_id: str,
        automation: dict[str, Any] | None = None,
    ) -> WorkflowRunnerCallbacks:
        workspace_id = str(workspace_id or "").strip()
        automation_snapshot = automation if isinstance(automation, dict) else {}

        def refresh_workspace() -> dict[str, Any]:
            with self.lock:
                current = self.workspace_by_id(workspace_id)
                return copy.deepcopy(current) if current else {}

        def execute_agent_node(
            ws_id: str,
            node: dict[str, Any],
            run_context: ExecutionRunContext,
        ) -> StepResult:
            return self.execute_workspace_agent_node(ws_id, node, run_context=run_context)

        def build_job_payload(
            workspace: dict[str, Any],
            node: dict[str, Any],
            *,
            previous_job_id: str = "",
            automation: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return self.workspace_node_job_payload(
                workspace,
                node,
                previous_job_id=previous_job_id,
                automation=automation if isinstance(automation, dict) else automation_snapshot,
            )

        def create_workspace_job(payload: dict[str, Any]) -> dict[str, Any]:
            return self.create_job(payload, publish_events=False)

        def record_run_steps(
            run_id: str,
            steps: list[dict[str, Any]],
            jobs: list[dict[str, Any]],
        ) -> dict[str, Any]:
            return self.update_workspace_execution_run_steps(
                workspace_id,
                str(run_id or "").strip(),
                steps=steps,
                jobs=jobs,
            )

        return WorkflowRunnerCallbacks(
            refresh_workspace=refresh_workspace,
            execute_agent_node=execute_agent_node,
            build_job_payload=build_job_payload,
            create_job=create_workspace_job,
            step_from_job=workspace_run_step_from_job,
            step_from_agent=workspace_run_step_from_agent,
            executable_node_kinds=WORKSPACE_EXECUTABLE_NODE_KINDS,
            record_run_steps=record_run_steps,
        )


    def run_workspace_workflow(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
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

        runtime_workspace = apply_workspace_job_runtime(workspace, jobs_snapshot)
        execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
        automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        blocked_checks = workspace_workflow_blocking_checks(automation)
        if until_node_id:
            blocked_checks = [
                check for check in blocked_checks
                if str(check.get("id") or "") == "starter_chain"
            ]
        elif not force:
            blocked_checks = [
                *blocked_checks,
                *workspace_execution_package_blocking_checks(automation, full_workflow=True),
            ]
        if blocked_checks and not force:
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
        for node in nodes:
            if resolve_node_executor_mode(node, executor_prefer) != "job":
                continue
            try:
                self.workspace_node_job_payload(workspace, node, automation=automation)
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

        planned_modes = [resolve_node_executor_mode(node, executor_prefer) for node in nodes]
        if not any(mode != "skip" for mode in planned_modes):
            raise ValueError("workspace has no runnable steps")

        initial_agent_count = sum(1 for node in nodes if resolve_node_executor_mode(node, executor_prefer) == "agent")
        run_summary = (
            f"运行至节点 · {str((target_node or {}).get('title') or until_node_id).strip()}"
            if until_node_id
            else (
                f"混合工作流 · {initial_agent_count} agent · {max(len(nodes) - initial_agent_count, 0)} job"
                if initial_agent_count and len(nodes) - initial_agent_count
                else f"Agent 工作流 · {initial_agent_count} 步"
                if initial_agent_count
                else f"完整工作流 · {len(nodes)} 步"
            )
        )
        initial_package = workspace_execution_bundle_result(automation, [])
        if until_node_id:
            initial_package["scope"] = {
                "mode": "run_to_node",
                "target_node_id": until_node_id,
                "target_node_title": str((target_node or {}).get("title") or "").strip(),
                "target_node_kind": str((target_node or {}).get("kind") or "").strip(),
            }
        run = self.register_workspace_execution_run(
            workspace_id,
            kind="reproduction",
            trigger="user",
            summary=run_summary,
            steps=[],
            package_snapshot=initial_package,
        )
        run_id = str(run.get("id") or "").strip()
        workflow_runner = WorkflowRunner(self.workflow_runner_callbacks(workspace_id, automation))
        try:
            sequence_result = workflow_runner.run(
                workspace_id,
                nodes,
                workspace,
                executor_prefer=executor_prefer,
                automation=automation,
                until_node_id=until_node_id,
                target_node=target_node,
                run_id=run_id,
            )
        except Exception as exc:
            failed_step = normalize_workspace_run_step(
                {
                    "index": 0,
                    "node_id": "",
                    "node_kind": "workflow",
                    "node_title": "工作流提交",
                    "executor": "system",
                    "status": "failed",
                    "completed_at": now_iso(),
                    "error": str(exc),
                }
            )
            self.update_workspace_execution_run_steps(
                workspace_id,
                run_id,
                steps=[failed_step],
                package_snapshot=initial_package,
            )
            raise
        jobs = sequence_result.jobs
        run_steps = sequence_result.run_steps
        agent_step_count = sequence_result.agent_step_count

        if not run_steps:
            failed_step = normalize_workspace_run_step(
                {
                    "index": 0,
                    "node_id": "",
                    "node_kind": "workflow",
                    "node_title": "工作流提交",
                    "executor": "system",
                    "status": "failed",
                    "completed_at": now_iso(),
                    "error": "workspace has no runnable steps",
                }
            )
            self.update_workspace_execution_run_steps(
                workspace_id,
                run_id,
                steps=[failed_step],
                package_snapshot=initial_package,
            )
            raise ValueError("workspace has no runnable steps")

        final_summary = (
            f"运行至节点 · {str((target_node or {}).get('title') or until_node_id).strip()}"
            if until_node_id
            else (
                f"混合工作流 · {agent_step_count} agent · {len(jobs)} job"
                if agent_step_count and jobs
                else f"Agent 工作流 · {agent_step_count} 步"
                if agent_step_count
                else f"完整工作流 · {len(jobs)} 步"
            )
        )
        execution_package = workspace_execution_bundle_result(automation, jobs)
        if until_node_id:
            execution_package["scope"] = {
                "mode": "run_to_node",
                "target_node_id": until_node_id,
                "target_node_title": str((target_node or {}).get("title") or "").strip(),
                "target_node_kind": str((target_node or {}).get("kind") or "").strip(),
            }
        run = self.update_workspace_execution_run_steps(
            workspace_id,
            run_id,
            jobs=jobs,
            steps=run_steps,
            summary=final_summary,
            package_snapshot=execution_package,
        )
        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        return {
            "workspace": payload_workspace,
            "jobs": jobs,
            "run": run,
            "run_id": run_id,
            "applied": applied,
            "evidence_applied": evidence_applied,
            "execution_package": execution_package,
        }
