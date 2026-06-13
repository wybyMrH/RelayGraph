"""Workspace state — automation operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class AutomationMixin:
    def advance_workspace_automation(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        force_run = bool(requested_payload.get("force_run") or False)
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            workspace_job_ids = {
                str(job.get("id") or "").strip()
                for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
            }
            active_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and str(job.get("status") or "") in {"queued", "blocked", "starting", "running"}
            ]
            failed_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and str(job.get("status") or "") in {"failed", "stopped"}
            ]
            discovery_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and (
                    str((job.get("metadata") if isinstance(job.get("metadata"), dict) else {}).get("workflow_phase") or "") == "discovery"
                    or str((job.get("metadata") if isinstance(job.get("metadata"), dict) else {}).get("node_kind") or "") in WORKSPACE_DISCOVERY_NODE_KINDS
                )
            ]
            public_workspace = self.workspace_public_payload(current)

        if active_jobs:
            decision = workspace_cockpit_decision_from_public_workspace(public_workspace)
            return {
                "action": "watch",
                "message": "已有任务在队列或运行中，先观察当前执行。",
                "decision": decision,
                "workspace": public_workspace,
                "jobs": [],
                "active_job_ids": [str(job.get("id") or "").strip() for job in active_jobs if str(job.get("id") or "").strip()],
            }

        if failed_jobs and not force_run:
            decision = workspace_cockpit_decision_from_public_workspace(public_workspace)
            return {
                "action": "review_failed",
                "message": "存在失败或停止的任务，先查看输出再继续自动推进。",
                "decision": decision,
                "workspace": public_workspace,
                "jobs": [],
                "failed_job_ids": [str(job.get("id") or "").strip() for job in failed_jobs[:8] if str(job.get("id") or "").strip()],
            }

        if not workspace_job_ids or not discovery_jobs:
            result = self.run_workspace_discovery(
                workspace_id,
                {
                    "apply_defaults": True,
                    "include_source": True,
                },
            )
            result_workspace = result.get("workspace") if isinstance(result.get("workspace"), dict) else public_workspace
            result["action"] = "discover"
            result["message"] = "已提交安全自动发现链。"
            result["decision"] = workspace_cockpit_decision_from_public_workspace(result_workspace)
            return result

        apply_result = self.apply_workspace_automation_defaults(
            workspace_id,
            {
                "apply_evidence": True,
            },
        )
        workspace_after_apply = apply_result.get("workspace") if isinstance(apply_result.get("workspace"), dict) else public_workspace
        applied = apply_result.get("applied") if isinstance(apply_result.get("applied"), list) else []
        evidence_applied = apply_result.get("evidence_applied") if isinstance(apply_result.get("evidence_applied"), list) else []

        automation = workspace_after_apply.get("automation") if isinstance(workspace_after_apply.get("automation"), dict) else {}
        blocked_checks = workspace_workflow_blocking_checks(automation)
        if blocked_checks and not force_run:
            return {
                "action": "blocked",
                "message": workspace_readiness_message(blocked_checks),
                "decision": workspace_cockpit_decision_from_public_workspace(workspace_after_apply),
                "workspace": workspace_after_apply,
                "jobs": [],
                "applied": applied,
                "evidence_applied": evidence_applied,
                "blocked_checks": blocked_checks,
            }

        try:
            run_result = self.run_workspace_workflow(
                workspace_id,
                {
                    "auto_apply": True,
                    "apply_evidence": True,
                    "force": force_run,
                },
            )
        except WorkspaceWorkflowReadinessError as exc:
            error_workspace = exc.workspace or workspace_after_apply
            return {
                "action": "blocked",
                "message": str(exc),
                "decision": workspace_cockpit_decision_from_public_workspace(error_workspace),
                "workspace": error_workspace,
                "jobs": [],
                "applied": exc.applied or applied,
                "evidence_applied": exc.evidence_applied or evidence_applied,
                "blocked_checks": exc.blocked_checks,
            }

        run_result["action"] = "run"
        run_result["message"] = "已完成回填并提交完整工作流。"
        run_applied = run_result.get("applied") if isinstance(run_result.get("applied"), list) else []
        run_evidence_applied = run_result.get("evidence_applied") if isinstance(run_result.get("evidence_applied"), list) else []
        run_result["applied"] = applied + run_applied
        run_result["evidence_applied"] = evidence_applied + run_evidence_applied
        run_workspace = run_result.get("workspace") if isinstance(run_result.get("workspace"), dict) else workspace_after_apply
        run_result["decision"] = workspace_cockpit_decision_from_public_workspace(run_workspace)
        return run_result
