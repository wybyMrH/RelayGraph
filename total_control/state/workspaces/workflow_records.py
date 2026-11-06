"""Bridge execution evidence into the existing runner, Job queue and public run projection."""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

from ...agent_runtime import agent_run_is_active
from ...orchestration.run_store import RunConflictError, RunStoreError, content_hash
from ...orchestration.job_coordinator import (
    AGENT_CHILD_JOB_ENGINE_VERSION,
    JOB_ENGINE_VERSION,
    REPORT_ENGINE_VERSION,
    GRAPH_ENGINE_VERSIONS,
)
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
    def stop_workspace_run_continuation(self, workspace_id: str, run_id: str,
                                         body: dict[str, Any]) -> dict[str, Any]:
        """Stop only a confirmed waiting N04 continuation, retaining its child."""
        if (not isinstance(body, dict) or body.get("child_policy") != "keep_running"
                or not isinstance(body.get("parent_attempt_id"), str)
                or not isinstance(body.get("child_job_id"), str) or not body["child_job_id"]):
            raise ValueError("parent_attempt_id, child_job_id and child_policy=keep_running are required")
        with self.execution_store.run_lock(run_id):
            evidence = self.execution_store.read(run_id)
            plan = evidence["plan"]
            if plan["workspace_id"] != workspace_id:
                raise ValueError("execution plan belongs to another workspace")
            if (plan["engine_version"] != AGENT_CHILD_JOB_ENGINE_VERSION
                    or len(plan["steps"]) != 2):
                raise RunConflictError("only a waiting N04 child continuation can be stopped")
            step_id = plan["steps"][0]["step_id"]
            attempt = next((item for item in reversed(evidence["attempts"]) if item["step_id"] == step_id), None)
            if not attempt or body["parent_attempt_id"] != f"a{attempt['attempt_no']}":
                raise RunConflictError("parent attempt identity conflict")
            if not evidence["record"].get("continuation_stop"):
                intent = next((item for item in evidence["submissions"] if item["step_id"] == step_id
                               and item["attempt_no"] == attempt["attempt_no"] and item["operation"] == "child-job"), None)
                if not intent or intent["state"] != "submitted" or intent["external_ref"] != body["child_job_id"]:
                    raise RunConflictError("child submission requires reconciliation before stopping continuation")
                with self.lock:
                    if not self.workspace_by_id(workspace_id):
                        raise ValueError("workspace not found")
                    job = self._job_for_submission(intent, workspace_id)
                    if not job or job["id"] != body["child_job_id"]:
                        raise RunConflictError("confirmed child Job receipt required")
                    # A just-completed child is allowed if no follow attempt exists.
                    # Known failure/stop must keep its original causal outcome.
                    if job.get("status") not in {"queued", "starting", "running", "done"}:
                        raise RunConflictError("child outcome requires observation before stopping continuation")
            receipt, changed = self.execution_store.stop_waiting_continuation(
                run_id, step_id, attempt["attempt_no"], body["child_job_id"],
                expected_engine_version=AGENT_CHILD_JOB_ENGINE_VERSION,
            )
            run = self.update_workspace_execution_run_steps(workspace_id, run_id)
            return {"run": run, "continuation_stop": receipt, "replayed": not changed,
                    "child_policy": "keep_running", "child_stop_requested": False}

    def _job_log_handoff(self, job: dict[str, Any]) -> dict[str, Any]:
        """Bounded, redacted evidence shared by report and child continuations."""
        try:
            chunk = self.job_log_payload(job, offset=0, max_bytes=8192)
        except (OSError, ValueError, RuntimeError):
            chunk = {"exists": False, "error": "Job log read failed"}
        raw = str(chunk.get("log") or "")
        replacement_characters = raw.count("\ufffd")
        # Snapshot adapters can return a character-bounded tail: enforce the
        # delivery byte limit too, without pretending it is the original range.
        delivery_limited = len(raw.encode("utf-8")) > 8192
        if delivery_limited:
            raw = raw.encode("utf-8")[-8192:].decode("utf-8", errors="ignore")
        text = redact_runtime_observation_text(raw)
        redacted = text != raw
        if len(text.encode("utf-8")) > 8192:
            text = text.encode("utf-8")[-8192:].decode("utf-8", errors="ignore")
            delivery_limited = True
        evidence = {key: chunk.get(key) for key in (
            "mode", "source", "exists", "offset", "requested_offset", "next_offset", "file_size",
            "byte_count", "skipped_bytes", "snapshot_captured_at", "snapshot_schema",
        )}
        truncated = bool(delivery_limited or chunk.get("truncated") or chunk.get("skipped_bytes")
                         or (isinstance(chunk.get("offset"), int) and chunk["offset"] > 0))
        offsets = [chunk.get(key) for key in ("offset", "next_offset", "file_size", "byte_count")]
        valid_range = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in offsets)
        truncated = truncated or (valid_range and offsets[1] < offsets[2]) or delivery_limited
        complete = (valid_range and chunk.get("exists") is True and not chunk.get("error") and not truncated
                    and not replacement_characters
                    and offsets[0] == 0 and offsets[1] == offsets[2] and offsets[3] == offsets[1])
        if valid_range and offsets[1] - offsets[0] > offsets[3]:
            evidence["error"] = "Job log range could not be fully read"
        if chunk.get("error"):
            evidence["error"] = "Job log read failed"  # Never expose adapter paths/commands.
        state = ("error" if evidence.get("error") else "missing" if chunk.get("exists") is False and not raw
                 else "complete" if complete else "partial")
        evidence.update(schema="job-log-handoff/v1", complete=bool(complete), state=state,
                        delivery_limited=delivery_limited, redacted=redacted,
                        text_replacement_characters=replacement_characters,
                        delivered_byte_count=len(text.encode("utf-8")))
        return {"host_id": str(job.get("server_id") or ""), "log": text,
                "log_evidence": evidence, "log_truncated": truncated}

    def _settle_child_submission_error(self, run_id: str, step_id: str, attempt_no: int,
                                       result: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """One interpretation of the durable failure, shared by finish and recovery."""
        evidence = self.execution_store.read(run_id)
        attempt = next(item for item in evidence["attempts"] if item["step_id"] == step_id
                       and item["attempt_no"] == attempt_no)
        failure = attempt["result"].get("child_submission_error")
        if not failure:
            return None
        if attempt["status"] in self.execution_store.TERMINAL:
            return copy.deepcopy(attempt["result"])
        settled = {**attempt["result"], **(result or {}), "node_id": step_id,
                   "status": failure["status"], "runtime_status": failure["status"],
                   "error": failure["error"], "child_submission_error": failure}
        # A Job may already exist when the model response/trace is interrupted.
        # Preserve its authoritative receipt, without declaring it stopped/done.
        for intent in evidence["submissions"]:
            if intent["step_id"] == step_id and intent["attempt_no"] == attempt_no and intent["operation"] == "child-job":
                settled.update(child_submit_key=intent["submit_key"], child_payload_hash=intent["payload_hash"])
                child_id = intent["external_ref"]
                if not child_id:
                    # Creation may have persisted before binding its receipt.
                    # Reuse the exact metadata matcher; do not bind or guess.
                    with self.lock:
                        try:
                            job = self._job_for_submission(intent, evidence["plan"]["workspace_id"])
                        except RunConflictError:
                            job = None
                    child_id = str(job["id"]) if job else ""
                if child_id:
                    settled.update(child_job_id=child_id,
                                   child_job_ids=list(dict.fromkeys([*settled.get("child_job_ids", []), child_id])))
        settled.pop("child_status", None)  # Parent failure must not route as child success.
        self.execution_store.record_result(run_id, step_id, attempt_no, settled)
        return settled

    def _job_for_submission(self, intent: dict[str, Any], workspace_id: str) -> dict[str, Any] | None:
        matches = [job for job in self.jobs
                   if job.get("metadata", {}).get("submission_key") == intent["submit_key"]
                   or job.get("metadata", {}).get("child_submit_key") == intent["submit_key"]]
        if len(matches) > 1:
            raise RunConflictError("duplicate durable Job receipts; manual reconciliation required")
        if not matches:
            return None
        job = matches[0]
        metadata = job["metadata"]
        if intent.get("operation") == "child-job":
            expected = {"workspace_id": workspace_id, "parent_run_id": intent["run_id"],
                        "parent_step_id": intent["step_id"], "parent_attempt_id": f"a{intent['attempt_no']}",
                        "child_submit_key": intent["submit_key"],
                        "child_payload_hash": intent["payload_hash"]}
        else:
            expected = {"submission_payload_hash": intent["payload_hash"], "workspace_id": workspace_id,
                        "execution_run_id": intent["run_id"], "node_id": intent["step_id"],
                        "execution_attempt_id": f"a{intent['attempt_no']}"}
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise RunConflictError("durable Job receipt identity conflict")
        return job

    def _active_child_submission(self, evidence: dict[str, Any], intent: dict[str, Any]) -> bool:
        """Recognize only the current process's exact N04 in-flight submission.

        This is a momentary projection hint, never permission to replay a claim.
        Persisted claims alone cannot establish liveness after a restart.
        """
        plan = evidence["plan"]
        if (plan["engine_version"] != AGENT_CHILD_JOB_ENGINE_VERSION
                or evidence["error"] or evidence["record"].get("continuation_stop")
                or len(evidence["attempts"]) != 1 or len(evidence["submissions"]) != 1):
            return False
        parent = plan["steps"][0]
        attempt = evidence["attempts"][0]
        result = attempt["result"]
        execution_id = f"{plan['run_id']}:{parent['step_id']}:a{attempt['attempt_no']}"
        return bool(
            parent["executor"] == "agent" and parent["index"] == 0
            and attempt["step_id"] == parent["step_id"]
            and attempt["status"] == result.get("status") == "running"
            and result.get("invocation_state") == "claimed"
            and result.get("agent_execution_id") == execution_id
            and not result.get("error") and not result.get("child_submission_error")
            and intent["run_id"] == plan["run_id"]
            and intent["step_id"] == parent["step_id"]
            and intent["attempt_no"] == attempt["attempt_no"]
            and intent["operation"] == "child-job" and intent["state"] == "submitting"
            and intent["submit_key"] == f"{plan['run_id']}/{parent['step_id']}/a{attempt['attempt_no']}/child-job"
            and not intent["external_ref"] and not intent["error"]
            and agent_run_is_active(execution_id)
        )

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
                if self._active_child_submission(evidence, intent):
                    status = "running"
                    result.update(runtime_status="submitting")
                else:
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
            "submit_key", "step_id", "attempt_no", "payload_hash", "state", "external_ref", "error", "operation"
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
            elif (intent["state"] in {"submitting", "reconciling", "submitted"}
                  and not self._active_child_submission(evidence, intent)):
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
        agent_route_hashes: dict[str, str] | None = None,
        engine_version: str = "",
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
        selected_engine = engine_version or (REPORT_ENGINE_VERSION if report_route_hash else JOB_ENGINE_VERSION)
        plan = RunPlan(
            run_id=planned_run_id, workspace_id=workspace["id"],
            engine_version=selected_engine,
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
                route_hash = (agent_route_hashes or {}).get(step["step_id"], report_route_hash)
                step.update(provider_route_hash=route_hash,
                            invocation_mode="single-call-no-tools" if selected_engine == REPORT_ENGINE_VERSION else "controlled-handoff")
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

    def start_coordinated_agent(self, run_id: str) -> str:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        if plan["engine_version"] != AGENT_CHILD_JOB_ENGINE_VERSION:
            raise RunConflictError("child Agent callback cannot execute this plan")
        step = plan["steps"][0]
        attempt_no = self.execution_store.begin_attempt(run_id, step["step_id"], inputs={
            "plan_hash": evidence["plan_hash"], "input_mapping": copy.deepcopy(step["node"].get("input_mapping", {})),
        })
        attempt = next(item for item in self.execution_store.read(run_id)["attempts"]
                       if item["step_id"] == step["step_id"] and item["attempt_no"] == attempt_no)
        failure = self._settle_child_submission_error(run_id, step["step_id"], attempt_no)
        if failure or attempt["status"] in self.execution_store.TERMINAL:
            return str((failure or attempt["result"]).get("child_job_id") or "")
        if attempt["result"].get("child_job_id"):
            return str(attempt["result"]["child_job_id"])
        prior_intent = next((item for item in evidence["submissions"]
                             if item.get("operation") == "child-job"
                             and item["step_id"] == step["step_id"]
                             and item["attempt_no"] == attempt_no), None)
        if prior_intent:
            child = self._job_for_submission(prior_intent, plan["workspace_id"])
            if child and prior_intent.get("external_ref") == child.get("id"):
                child_id = str(child["id"])
                self.execution_store.record_result(
                    run_id, step["step_id"], attempt_no,
                    {**attempt["result"], "node_id": step["step_id"], "status": "waiting",
                     "executor": "agent", "runtime_status": "waiting_child",
                     "child_status": child.get("status", "unknown"), "child_job_id": child_id,
                     "child_job_ids": [child_id], "child_submit_key": prior_intent["submit_key"],
                     "child_payload_hash": prior_intent["payload_hash"]},
                )
                return child_id
            if prior_intent.get("state") in {"submitting", "reconciling"}:
                raise RunConflictError("child Job submission outcome unknown; reconciliation required")
        execution_id = f"{run_id}:{step['step_id']}:a{attempt_no}"
        if not self.execution_store.claim_agent_invocation(run_id, step["step_id"], attempt_no, execution_id):
            self.execution_store.record_result(
                run_id, step["step_id"], attempt_no,
                {**attempt["result"], "node_id": step["step_id"], "status": "blocked",
                 "executor": "agent", "invocation_state": "unknown",
                 "error": "Agent invocation outcome unknown; automatic replay refused"},
            )
            raise RunConflictError("Agent invocation already claimed; automatic replay refused")
        context = ExecutionRunContext(
            workspace_id=plan["workspace_id"], run_id=run_id, kind="workflow", step_index=0,
            parent_attempt={"run_id": run_id, "step_id": step["step_id"], "attempt_no": attempt_no,
                            "agent_execution_id": execution_id},
        )
        result = self.execute_workspace_agent_node(
            plan["workspace_id"], copy.deepcopy(step["node"]), run_context=context,
            frozen_workspace=copy.deepcopy(plan["workspace_snapshot"]), execution_id=execution_id,
            expected_route_hash=step.get("provider_route_hash", ""),
        )
        recorded = workspace_run_step_from_agent(step["node"], result, step["index"])
        recorded.update(agent_execution_id=execution_id, invocation_state="recorded")
        failure = self._settle_child_submission_error(run_id, step["step_id"], attempt_no, recorded)
        if failure:
            return str(failure.get("child_job_id") or "")
        child_ids = recorded.get("child_job_ids") if isinstance(recorded.get("child_job_ids"), list) else []
        if recorded["status"] in {"failed", "blocked", "stopped"}:
            self.execution_store.record_result(run_id, step["step_id"], attempt_no, recorded)
            return str(child_ids[0]) if child_ids else ""
        if child_ids:
            recorded.update(status="waiting", runtime_status="waiting_child", completed_at="", error="")
        self.execution_store.record_result(run_id, step["step_id"], attempt_no, recorded)
        if not child_ids:
            raise RunConflictError("parent Agent did not submit a controlled child Job")
        return str(child_ids[0])

    def resume_coordinated_agent(self, run_id: str) -> dict[str, Any]:
        evidence = self.execution_store.read(run_id)
        plan = evidence["plan"]
        if plan["engine_version"] != AGENT_CHILD_JOB_ENGINE_VERSION:
            raise RunConflictError("child Agent callback cannot execute this plan")
        source = plan["steps"][0]
        follow = plan["steps"][1]
        source_attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == source["step_id"])
        failure = self._settle_child_submission_error(run_id, source["step_id"], source_attempt["attempt_no"])
        if failure or source_attempt["status"] in {"failed", "stopped", "blocked"}:
            return copy.deepcopy(failure or source_attempt["result"])
        if source_attempt["result"].get("continuation_state") == "resumed":
            return copy.deepcopy(source_attempt["result"])
        number = self.execution_store.begin_attempt(run_id, follow["step_id"], inputs={
            "plan_hash": evidence["plan_hash"], "source_step_id": source["step_id"],
            "source_attempt_id": f"a{source_attempt['attempt_no']}",
            "child_job_id": source_attempt["result"].get("child_job_id", ""),
        })
        existing_follow = next(item for item in self.execution_store.read(run_id)["attempts"]
                              if item["step_id"] == follow["step_id"] and item["attempt_no"] == number)
        if existing_follow["result"]:
            if existing_follow["result"].get("invocation_state") == "claimed":
                result = {**existing_follow["result"], "status": "blocked", "invocation_state": "unknown",
                          "error": "Agent invocation outcome unknown; automatic replay refused"}
                self.execution_store.record_result(run_id, follow["step_id"], number, result)
                return result
            self.execution_store.record_result(
                run_id,
                source["step_id"],
                source_attempt["attempt_no"],
                {**source_attempt["result"], "node_id": source["step_id"], "status": "done",
                 "runtime_status": "done", "continuation_state": "resumed"},
            )
            return copy.deepcopy(existing_follow["result"])
        execution_id = f"{run_id}:{follow['step_id']}:a{number}"
        if not self.execution_store.claim_agent_invocation(run_id, follow["step_id"], number, execution_id):
            raise RunConflictError("Agent invocation already claimed; automatic replay refused")
        child_output = copy.deepcopy(source_attempt["result"].get("output_value", {}))
        result = self.execute_workspace_agent_node(plan["workspace_id"], copy.deepcopy(follow["node"]),
                                                   run_context=ExecutionRunContext(
                                                       workspace_id=plan["workspace_id"], run_id=run_id,
                                                       kind="workflow", step_index=1,
                                                       previous_output=child_output or None,
                                                       outputs={str(child_output.get("output_key") or ""): child_output}
                                                       if child_output.get("output_key") else {},
                                                   ),
                                                   frozen_workspace=copy.deepcopy(plan["workspace_snapshot"]), execution_id=execution_id,
                                                   expected_route_hash=follow.get("provider_route_hash", ""),
                                                   preserve_job_evidence=True)
        recorded = workspace_run_step_from_agent(follow["node"], result, follow["index"])
        recorded.update(agent_execution_id=execution_id, continuation_state="resumed")
        self.execution_store.record_result(run_id, follow["step_id"], number, recorded)
        source_result = {
            **source_attempt["result"],
            "node_id": source["step_id"],
            "status": "done",
            "runtime_status": "done",
            "continuation_state": "resumed",
        }
        self.execution_store.record_result(run_id, source["step_id"], source_attempt["attempt_no"], source_result)
        return recorded.as_dict() if hasattr(recorded, "as_dict") else recorded

    def fail_coordinated_agent(self, run_id: str, observation: dict[str, Any]) -> dict[str, Any]:
        evidence = self.execution_store.read(run_id)
        step = evidence["plan"]["steps"][0]
        attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == step["step_id"])
        if attempt["status"] in self.execution_store.TERMINAL:
            return copy.deepcopy(attempt["result"])
        child_status = observation.get("child_status") or observation.get("status")
        terminal = "failed" if child_status == "failed" else "blocked" if child_status in {"blocked", "reconciling", "unknown"} else "stopped"
        result = {**attempt["result"], "node_id": step["step_id"], "status": terminal,
                  "runtime_status": child_status or "failed", "error": observation.get("error") or "child Job did not complete"}
        self.execution_store.record_result(run_id, step["step_id"], attempt["attempt_no"], result)
        return result

    def observe_coordinated_job(self, run_id: str, job_id: str) -> dict[str, Any]:
        evidence = self.execution_store.read(run_id)
        step = evidence["plan"]["steps"][0]
        attempt = next(item for item in reversed(evidence["attempts"]) if item["step_id"] == step["step_id"])
        if evidence["plan"]["engine_version"] == AGENT_CHILD_JOB_ENGINE_VERSION:
            failure = self._settle_child_submission_error(run_id, step["step_id"], attempt["attempt_no"])
            if failure:
                return failure
        if attempt["status"] in self.execution_store.TERMINAL:
            return copy.deepcopy(attempt["result"])
        intent = next(item for item in evidence["submissions"] if item["step_id"] == step["step_id"]
                      and item["attempt_no"] == attempt["attempt_no"]
                      and (evidence["plan"]["engine_version"] != AGENT_CHILD_JOB_ENGINE_VERSION
                           or item.get("operation") == "child-job"))
        with self.lock:
            job = self._job_for_submission(intent, evidence["plan"]["workspace_id"])
            if job and job["id"] == job_id and intent["external_ref"] == job_id:
                job = copy.deepcopy(job)
                result = workspace_run_step_from_job(job, step["index"])
                if evidence["plan"]["engine_version"] == AGENT_CHILD_JOB_ENGINE_VERSION:
                    child_status = result["status"]
                    output = {
                        "run_id": run_id,
                        "node_id": step["step_id"],
                        "attempt_id": f"a{attempt['attempt_no']}",
                        "job_id": job_id,
                        "status": child_status,
                        "output_key": workspace_contract_output_key_for_node(step["node"], step["index"]),
                        "artifact_manifest": {"items": copy.deepcopy(result.get("artifacts", [])),
                                              "verification": "Child Job declarations; files not verified by this handoff"},
                    }
                    if child_status == "done":
                        previous = attempt["result"].get("output_value", {})
                        identity = {"run_id": run_id, "node_id": step["step_id"],
                                    "attempt_id": f"a{attempt['attempt_no']}", "job_id": job_id,
                                    "host_id": str(job["server_id"]), "status": "done"}
                        if (all(previous.get(key) == value for key, value in identity.items())
                                and previous.get("log_evidence", {}).get("schema") == "job-log-handoff/v1"):
                            output = copy.deepcopy(previous)
                        else:
                            output.update(self._job_log_handoff(job))
                    return {
                        **attempt["result"],
                        "node_id": step["step_id"],
                        "status": "waiting",
                        "executor": "agent",
                        "job_id": job_id,
                        "child_job_ids": [job_id],
                        "child_status": child_status,
                        "runtime_status": "waiting_child",
                        "error": result.get("error", "") if child_status != "done" else "",
                        "agent_execution_id": attempt["result"].get("agent_execution_id", ""),
                        "child_submit_key": intent["submit_key"],
                        "child_payload_hash": intent["payload_hash"],
                        "output_value": output,
                    }
                if evidence["plan"]["engine_version"] == REPORT_ENGINE_VERSION and result["status"] == "done":
                    result["output_value"] = {
                        "run_id": run_id, "node_id": step["step_id"], "attempt_id": f"a{attempt['attempt_no']}",
                        "job_id": job_id, "host_id": job["server_id"], "status": "done",
                        "output_key": workspace_contract_output_key_for_node(step["node"], step["index"]),
                        "artifact_manifest": {"items": copy.deepcopy(result["artifacts"]),
                                              "verification": "Job declarations; files not verified by this handoff"},
                        **self._job_log_handoff(job),
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
