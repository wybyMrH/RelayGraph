"""Bridge execution evidence into the existing runner, Job queue and public run projection."""

from __future__ import annotations

import copy
from typing import Any

from ...orchestration.run_store import RunConflictError, RunStoreError
from ...orchestration.types import RunPlan
from ...utils import now_iso
from ...workspace.execution import (
    make_workspace_execution_run_id,
    normalize_workspace_execution_run,
    normalize_workspace_execution_runs,
    normalize_workspace_run_step,
    refresh_workspace_execution_run,
)


class WorkflowRecordsMixin:
    def _job_for_submission(self, intent: dict[str, Any], workspace_id: str) -> dict[str, Any] | None:
        matches = [job for job in self.jobs if job.get("metadata", {}).get("submission_key") == intent["submit_key"]]
        if len(matches) > 1:
            raise RunConflictError("duplicate durable Job receipts; manual reconciliation required")
        if not matches:
            return None
        job = matches[0]
        metadata = job["metadata"]
        expected = {"submission_payload_hash": intent["payload_hash"], "workspace_id": workspace_id,
                    "execution_run_id": intent["run_id"], "node_id": intent["step_id"],
                    "execution_attempt_id": f"a{intent['attempt_no']}"}
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise RunConflictError("durable Job receipt identity conflict")
        return job

    def project_workflow_run(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        if plan["workspace_id"] != workspace_id:
            raise ValueError("execution plan belongs to another workspace")
        workspace = self.workspace_by_id(workspace_id) or {}
        existing = next((item for item in workspace.get("runs", []) if item.get("id") == run_id), {})
        attempts = evidence["attempts"]
        submissions = evidence["submissions"]
        steps = []
        for planned in plan["steps"]:
            node = planned["node"]
            latest = next((item for item in reversed(attempts) if item["step_id"] == planned["step_id"]), None)
            result = copy.deepcopy(latest["result"]) if latest else {}
            intent = next((item for item in submissions if latest and item["step_id"] == planned["step_id"]
                           and item["attempt_no"] == latest["attempt_no"]), None)
            if intent and intent["external_ref"]:
                result["job_id"] = intent["external_ref"]
            status = result.get("status") or (latest["status"] if latest else "skipped" if planned["executor"] == "skip" else "pending")
            if intent and intent["state"] in {"submitting", "reconciling"}:
                status = "blocked"
                result.update(runtime_status="reconciling", error=intent["error"] or "Job submission requires reconciliation")
            steps.append(normalize_workspace_run_step({
                **result, "index": planned["index"], "step_id": planned["step_id"],
                "attempt_id": f"a{latest['attempt_no']}" if latest else "",
                "node_id": planned["step_id"], "node_kind": node.get("kind", ""),
                "node_title": node.get("title", ""), "executor": planned["executor"], "status": status,
                "submission_state": intent["state"] if intent else "",
            }))
        public_attempts = [{"step_id": item["step_id"], "attempt_id": f"a{item['attempt_no']}",
                            "status": item["status"], "inputs": item["inputs"], "result": item["result"],
                            "created_at": item["created_at"], "updated_at": item["updated_at"]} for item in attempts]
        public_submissions = [{key: item[key] for key in (
            "submit_key", "step_id", "attempt_no", "payload_hash", "state", "external_ref", "error"
        )} for item in submissions]
        record = normalize_workspace_execution_run({
            **existing, **evidence["record"], "id": run_id, "workspace_id": workspace_id,
            "steps": steps, "status": "pending", "submission_error": evidence["error"],
            "package_snapshot": evidence["record"].get("package_snapshot", plan["package_snapshot"]),
            "execution_plan": {key: copy.deepcopy(plan[key]) for key in ("schema_version", "engine_version", "steps")},
            "plan_hash": evidence["plan_hash"], "attempts": public_attempts, "submissions": public_submissions,
        })
        projected = refresh_workspace_execution_run(record, {job["id"]: job for job in self.jobs},
                                                     {item["id"]: item for item in workspace.get("runs", [])})
        for attempt in projected["attempts"]:
            current = next((step for step in projected["steps"] if step["step_id"] == attempt["step_id"]
                            and step["attempt_id"] == attempt["attempt_id"]), None)
            attempt["recorded_status"] = attempt["status"]
            if current:
                attempt["status"] = current["status"]
        return projected

    def reconcile_workflow_submissions(self, workspace_id: str, run_id: str) -> None:
        """Recover durable Job receipts; never start or resubmit work during reconciliation."""
        evidence = self.execution_store.read(run_id)
        if evidence["plan"]["workspace_id"] != workspace_id:
            raise ValueError("execution plan belongs to another workspace")
        for intent in evidence["submissions"]:
            job = self._job_for_submission(intent, workspace_id)
            if job:
                self.execution_store.bind_submission(intent["submit_key"], job["id"])
            elif intent["state"] in {"submitting", "reconciling", "submitted"}:
                self.execution_store.reconcile_submission(intent["submit_key"], "Job receipt missing; automatic resubmission refused")

    def refresh_workflow_records(self, workspace: dict[str, Any]) -> None:
        managed_ids = self.execution_store.run_ids(workspace["id"])
        if not managed_ids:
            return
        legacy = [run for run in workspace.get("runs", []) if run.get("id") not in managed_ids]
        managed = [self.project_workflow_run(workspace["id"], run_id) for run_id in managed_ids]
        workspace["runs"] = normalize_workspace_execution_runs([*managed, *legacy])

    def workflow_receipt_job_ids(self) -> set[str]:
        """Protect durable receipts even before a JSON projection has caught up."""
        protected: set[str] = set()
        with self.lock:
            for workspace in self.workspaces:
                for run_id in self.execution_store.run_ids(workspace["id"]):
                    for intent in self.execution_store.read(run_id)["submissions"]:
                        if intent["external_ref"]:
                            protected.add(intent["external_ref"])
                        job = self._job_for_submission(intent, workspace["id"])
                        if job:
                            protected.add(job["id"])
        return protected

    def register_planned_workflow_run(
        self, workspace: dict[str, Any], nodes: list[dict[str, Any]], modes: list[str],
        package_snapshot: dict[str, Any], *, request_id: str, request_hash: str, summary: str,
        executor_prefer: str,
    ) -> tuple[dict[str, Any], bool]:
        snapshot = {key: copy.deepcopy(value) for key, value in workspace.items()
                    if key not in {"runs", "chat", "execution", "automation", "updated_at"}}
        plan = RunPlan(
            run_id=make_workspace_execution_run_id(), workspace_id=workspace["id"],
            steps=[{"step_id": node["id"], "index": index, "executor": modes[index], "node": copy.deepcopy(node)}
                   for index, node in enumerate(nodes)],
            workspace_snapshot=snapshot, package_snapshot=copy.deepcopy(package_snapshot), executor_prefer=executor_prefer,
        )
        run_id, created = self.execution_store.create(plan, request_id=request_id, request_hash=request_hash, summary=summary)
        with self.lock:
            current = self.workspace_by_id(workspace["id"])
            if not current:
                raise ValueError("workspace not found")
            self.refresh_workflow_records(current)
            run = next(item for item in current["runs"] if item["id"] == run_id)
        try:
            self.save_workspaces()
        except OSError as exc:
            raise RunStoreError("run projection could not be saved; immutable plan retained") from exc
        if created:
            self.publish_event("run.created", workspace_id=workspace["id"], run_id=run_id, payload={"run": run})
        return run, created

    def record_workflow_steps(self, run_id: str, steps: list[dict[str, Any]]) -> None:
        evidence = self.execution_store.read(run_id)
        planned_ids = {step["step_id"] for step in evidence["plan"]["steps"]}
        for step in steps:
            step_id = step.get("node_id", "")
            if step_id not in planned_ids:
                raise RunConflictError("step result is outside the immutable plan")
            attempt = next((item for item in reversed(evidence["attempts"]) if item["step_id"] == step_id), None)
            if attempt and attempt["result"] != step:
                self.execution_store.record_result(run_id, step_id, attempt["attempt_no"], step)

    def begin_workflow_step(self, run_id: str, node: dict[str, Any], index: int) -> None:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        if plan["steps"][index]["step_id"] != node["id"]:
            raise RunConflictError("runner step differs from frozen plan")
        self.execution_store.begin_attempt(run_id, node["id"], inputs={
            "plan_hash": evidence["plan_hash"],
            "input_mapping": copy.deepcopy(node.get("input_mapping", {})),
            "previous_planned_step_id": plan["steps"][index - 1]["step_id"] if index else "",
        })

    def fail_workflow_step(self, run_id: str, node: dict[str, Any], index: int, error: Exception) -> None:
        evidence = self.execution_store.read(run_id)
        attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == node["id"])
        if attempt["status"] not in self.execution_store.TERMINAL:
            self.execution_store.record_result(run_id, node["id"], attempt["attempt_no"], {
                "index": index, "node_id": node["id"], "status": "failed",
                "completed_at": now_iso(), "error": str(error),
            })

    def submit_workflow_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("wait_for_idle") is not True:
            raise ValueError("workflow Jobs must enter the durable queue before execution")
        metadata = payload["metadata"]
        run_id, step_id = metadata["execution_run_id"], metadata["node_id"]
        evidence = self.execution_store.read(run_id)
        attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == step_id)
        intent = self.execution_store.prepare_submission(run_id, step_id, attempt["attempt_no"], payload)
        key = intent["submit_key"]
        with self.lock:
            existing = self._job_for_submission(intent, evidence["plan"]["workspace_id"])
            if existing:
                self.execution_store.bind_submission(key, existing["id"])
                return existing
            if not self.execution_store.claim_submission(key):
                self.execution_store.reconcile_submission(key, "Job reference unavailable; automatic resubmission refused")
                raise RunConflictError("submission outcome unknown; reconciliation required")
            job_payload = copy.deepcopy(payload)
            job_payload["metadata"].update(submission_key=key, submission_payload_hash=intent["payload_hash"],
                                           execution_attempt_id=f"a{attempt['attempt_no']}")
            try:
                job = self.create_job(job_payload, publish_events=False)
            except Exception as exc:
                self.execution_store.reconcile_submission(key, str(exc))
                if isinstance(exc, OSError):
                    raise RunStoreError("Job receipt could not be saved; submission requires reconciliation") from exc
                raise
            self.execution_store.bind_submission(key, job["id"])
            return job

    def replay_workflow_response(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            self.reconcile_workflow_submissions(workspace_id, run_id)
            public = self.workspace_public_payload(workspace)
            run = next(item for item in public["runs"] if item["id"] == run_id)
            jobs = [job for job in self.jobs if job.get("metadata", {}).get("execution_run_id") == run_id]
            return {"workspace": public, "run": run, "run_id": run_id, "jobs": copy.deepcopy(jobs),
                    "execution_package": run["package_snapshot"], "applied": [], "evidence_applied": [],
                    "replayed": True}
