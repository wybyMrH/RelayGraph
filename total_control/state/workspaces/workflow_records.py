"""Bridge execution evidence into the existing runner, Job queue and public run projection."""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

from ...orchestration.run_store import RunConflictError, RunStoreError, content_hash
from ...orchestration.job_coordinator import JOB_ENGINE_VERSION, REPORT_ENGINE_VERSION, GRAPH_ENGINE_VERSIONS
from ...orchestration.types import RunPlan, ExecutionRunContext
from ...workspace.automation.contracts_pkg.io import workspace_contract_output_key_for_node
from .agent_runtime_safety import redact_runtime_observation_text
from ...infra.report_files import ReportFileError, report_file_descriptor, report_file_view, publish_report_file
from ...workspace.execution import (
    make_workspace_execution_run_id,
    normalize_workspace_execution_run,
    normalize_workspace_execution_runs,
    normalize_workspace_run_step,
    refresh_workspace_execution_run,
    workspace_run_step_from_job,
    workspace_run_step_from_agent,
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
            if latest and plan.get("report_output_root") and node.get("kind") == "eval.report" and status == "done":
                output = result.get("output_value", {})
                if output.get("storage") == "inline-answer":
                    descriptor = report_file_descriptor(workspace_id, run_id, planned["step_id"],
                                                        f"a{latest['attempt_no']}", output.get("content"))
                    receipt = evidence["record"].get("report_files", {}).get(f"{planned['step_id']}/a{latest['attempt_no']}")
                    view = report_file_view(plan["report_output_root"], descriptor, receipt)
                    output.update(file_verified=view["file_verified"], report_file={k: v for k, v in view.items() if k != "content"})
                    result["artifacts"] = [{k: v for k, v in view.items() if v is not None}]
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
            "updated_at": max([existing.get("updated_at", ""), evidence["record"].get("updated_at", ""),
                               *(item["updated_at"] for item in attempts)]),
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
        executor_prefer: str, job_payloads: dict[str, dict[str, Any]],
        report_route_hash: str = "",
    ) -> tuple[dict[str, Any], bool]:
        snapshot = {key: copy.deepcopy(value) for key, value in workspace.items()
                    if key not in {"runs", "chat", "execution", "automation", "updated_at"}}
        snapshot["nodes"] = copy.deepcopy(nodes)
        planned_run_id = make_workspace_execution_run_id()
        frozen_payloads = copy.deepcopy(job_payloads)
        for index, node in enumerate(nodes):
            if modes[index] != "job":
                continue
            payload = frozen_payloads[node["id"]]
            payload["wait_for_idle"] = True
            payload["metadata"].update(execution_run_id=planned_run_id, step_index=index, workflow_index=index)
            scope = package_snapshot.get("scope", {})
            if scope.get("mode") == "run_to_node":
                payload["metadata"].update(workflow_phase="run_to_node", workflow_until_node_id=scope["target_node_id"],
                                           workflow_until_node_title=scope["target_node_title"],
                                           workflow_until_node_kind=scope["target_node_kind"])
        plan = RunPlan(
            run_id=planned_run_id, workspace_id=workspace["id"],
            engine_version=REPORT_ENGINE_VERSION if report_route_hash else JOB_ENGINE_VERSION,
            steps=[{"step_id": node["id"], "index": index, "executor": modes[index], "node": copy.deepcopy(node)}
                   for index, node in enumerate(nodes)],
            workspace_snapshot=snapshot, package_snapshot=copy.deepcopy(package_snapshot), executor_prefer=executor_prefer,
            report_output_root=str(Path(self.config.report_output_dir) if self.config.report_output_dir
                                   else self.execution_store.path.resolve().parent / "reports") if report_route_hash else "",
        )
        for step in plan.steps:
            if step["executor"] == "job":
                step["job_payload"] = frozen_payloads[step["step_id"]]
            else:
                step.update(provider_route_hash=report_route_hash, invocation_mode="single-call-no-tools")
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

    def submit_coordinated_job(self, run_id: str) -> str:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        expected_modes = (["job", "agent"] if plan["engine_version"] == REPORT_ENGINE_VERSION else ["job"])
        if (plan["engine_version"] not in GRAPH_ENGINE_VERSIONS
                or [item["executor"] for item in plan["steps"]] != expected_modes):
            raise RunConflictError("coordinator cannot execute this plan")
        step = plan["steps"][0]
        self.begin_workflow_step(run_id, step["node"], step["index"])
        return self.submit_workflow_job(copy.deepcopy(step["job_payload"]))["id"]

    def observe_coordinated_job(self, run_id: str, job_id: str) -> dict[str, Any]:
        evidence = self.execution_store.read(run_id)
        step = evidence["plan"]["steps"][0]
        attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == step["step_id"])
        if attempt["status"] in self.execution_store.TERMINAL:
            return copy.deepcopy(attempt["result"])
        intent = next(item for item in evidence["submissions"] if item["step_id"] == step["step_id"]
                      and item["attempt_no"] == attempt["attempt_no"])
        with self.lock:
            job = self._job_for_submission(intent, evidence["plan"]["workspace_id"])
            if job and job["id"] == job_id and intent["external_ref"] == job_id:
                job = copy.deepcopy(job)
                result = workspace_run_step_from_job(job, step["index"])
                if evidence["plan"]["engine_version"] == REPORT_ENGINE_VERSION and result["status"] == "done":
                    log = self.job_log_payload(job, offset=0, max_bytes=8192)
                    result["output_value"] = {
                        "run_id": run_id, "node_id": step["step_id"], "attempt_id": f"a{attempt['attempt_no']}",
                        "job_id": job_id, "host_id": job["server_id"], "status": "done",
                        "output_key": workspace_contract_output_key_for_node(step["node"], step["index"]),
                        "artifact_manifest": {"items": copy.deepcopy(result["artifacts"]),
                                              "verification": "Job declarations; files not verified by this handoff"},
                        "log": redact_runtime_observation_text(log.get("log", "")),
                        "log_evidence": {key: log.get(key) for key in (
                            "mode", "exists", "offset", "next_offset", "file_size", "byte_count", "skipped_bytes", "error",
                        )},
                        "log_truncated": bool(log.get("truncated") or log.get("next_offset", 0) < log.get("file_size", 0)),
                    }
                return result
        return {"index": step["index"], "node_id": step["step_id"], "job_id": job_id,
                "status": "blocked", "runtime_status": "reconciling",
                "error": "Job receipt unavailable; automatic resubmission refused"}

    def record_coordinated_job(self, run_id: str, result: dict[str, Any]) -> None:
        self.record_workflow_steps(run_id, [result])

    def execute_coordinated_report(self, run_id: str) -> dict[str, Any]:
        """Graph callback; consume this attempt only, persist claim before any model call."""
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        if plan["engine_version"] != REPORT_ENGINE_VERSION or len(plan["steps"]) != 2:
            raise RunConflictError("report callback cannot execute this plan")
        upstream, step = plan["steps"]
        source = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == upstream["step_id"])
        inputs = {"plan_hash": evidence["plan_hash"], "source_step_id": upstream["step_id"],
                  "source_attempt_id": f"a{source['attempt_no']}", "source_result_hash": content_hash(source["result"]),
                  "input_mapping": copy.deepcopy(step["node"].get("input_mapping", {}))}
        number = self.execution_store.begin_attempt(run_id, step["step_id"], inputs=inputs)
        attempt = next(item for item in self.execution_store.read(run_id)["attempts"]
                       if item["step_id"] == step["step_id"] and item["attempt_no"] == number)
        if attempt["result"]:
            if attempt["result"].get("invocation_state") == "claimed":
                result = {**attempt["result"], "status": "blocked", "invocation_state": "unknown",
                          "error": "Agent invocation outcome unknown; automatic replay refused"}
                self.execution_store.record_result(run_id, step["step_id"], number, result)
                return result
            self._publish_coordinated_report(run_id, step["step_id"], number, attempt["result"])
            return copy.deepcopy(attempt["result"])
        if source["status"] != "done":
            result = {"node_id": step["step_id"], "status": "skipped", "executor": "agent",
                      "reason": "upstream_not_successful", "error": "Job failed or stopped; report Agent was not invoked"}
            self.execution_store.record_result(run_id, step["step_id"], number, result)
            return result
        output = copy.deepcopy(source["result"].get("output_value", {}))
        expected = {"run_id": run_id, "node_id": upstream["step_id"], "attempt_id": f"a{source['attempt_no']}",
                    "job_id": source["result"]["job_id"]}
        if not output or any(output.get(key) != value for key, value in expected.items()):
            raise RunConflictError("current Job output provenance unavailable; history fallback refused")
        if not output.get("log_evidence", {}).get("exists") or output["log_evidence"].get("error"):
            result = {"node_id": step["step_id"], "status": "blocked", "executor": "agent",
                      "invocation_state": "not_started", "error": "Current Job log unavailable; history fallback refused"}
            self.execution_store.record_result(run_id, step["step_id"], number, result)
            return result
        execution_id = f"{run_id}:{step['step_id']}:a{number}"
        if not self.execution_store.claim_agent_invocation(run_id, step["step_id"], number, execution_id):
            raise RunConflictError("Agent invocation already claimed; automatic replay refused")
        context = ExecutionRunContext(
            workspace_id=plan["workspace_id"], run_id=run_id, kind="workflow", step_index=1,
            outputs={output["output_key"]: output}, previous_output=output,
        )
        result = self.execute_workspace_agent_node(
            plan["workspace_id"], copy.deepcopy(step["node"]), run_context=context,
            frozen_workspace=copy.deepcopy(plan["workspace_snapshot"]), execution_id=execution_id,
            expected_route_hash=step["provider_route_hash"], report_only=True,
        )
        recorded = workspace_run_step_from_agent(step["node"], result, step["index"])
        recorded.update(agent_execution_id=execution_id, invocation_state="recorded")
        if recorded.get("output_value"):
            recorded["output_value"].update(run_id=run_id, node_id=step["step_id"], attempt_id=f"a{number}",
                                            agent_execution_id=execution_id, source=expected)
        self.execution_store.record_result(run_id, step["step_id"], number, recorded)
        self._publish_coordinated_report(run_id, step["step_id"], number, recorded)
        return recorded

    def _publish_coordinated_report(self, run_id: str, step_id: str, number: int, result: dict[str, Any]) -> None:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        output = result.get("output_value", {})
        if (not plan.get("report_output_root") or result.get("status") != "done"
                or result.get("validation", {}).get("status") != "ok" or output.get("storage") != "inline-answer"):
            return  # Legacy plans and invalid/failed answers are never migrated by a wakeup.
        descriptor = report_file_descriptor(plan["workspace_id"], run_id, step_id, f"a{number}", output.get("content"))
        receipt = self.execution_store.prepare_report_file(run_id, step_id, number, descriptor)
        if receipt["status"] != "prepared":
            return
        error = ""
        try:
            publish_report_file(plan["report_output_root"], descriptor, output["content"])
        except ReportFileError as exc:
            error = exc.code
        self.execution_store.finish_report_file(run_id, step_id, number, error=error)

    def advance_workflow_runs(self) -> None:
        """One serial graph worker; a model call must not block the Job monitor loop."""
        if self.stop_event.is_set() or (self.workflow_wake_thread and self.workflow_wake_thread.is_alive()):
            return
        self.workflow_wake_thread = threading.Thread(target=self._advance_workflow_runs, daemon=True,
                                                     name="relaygraph-workflow-wake")
        self.workflow_wake_thread.start()

    def _advance_workflow_runs(self) -> None:
        """Scheduler-owned wakeup batch; the graph is still the sole step coordinator."""
        from ...orchestration.run_store import RunBusyError

        with self.lock:
            identities = [(workspace["id"], run_id) for workspace in self.workspaces
                          for run_id in self.execution_store.run_ids(workspace["id"])]
        for workspace_id, run_id in identities:
            if self.stop_event.is_set():
                return
            evidence = self.execution_store.read(run_id)
            if evidence["plan"]["engine_version"] not in GRAPH_ENGINE_VERSIONS:
                continue
            try:
                with self.lock:
                    self.reconcile_workflow_submissions(workspace_id, run_id)
                evidence = self.execution_store.read(run_id)
                if any(item["state"] == "reconciling" for item in evidence["submissions"]):
                    continue  # Unknown side effects require facts, not another graph retry.
                changed = self.workflow_coordinator.advance(run_id)
                if evidence["error"]:
                    self.execution_store.fail_run(run_id, "")
                    changed = True
            except RunBusyError:
                continue
            except Exception as exc:  # Keep evidence; never fall back to another runner.
                error = "Workflow coordinator unavailable; retained state requires reconciliation"
                if evidence["error"] == error:
                    continue
                print(f"[total-control] workflow {run_id} coordinator error: {exc}", flush=True)
                # The existing error column is diagnostic; new graph projections show blocked.
                self.execution_store.fail_run(run_id, error)
                changed = True
            if changed:
                self.update_workspace_execution_run_steps(workspace_id, run_id)

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
