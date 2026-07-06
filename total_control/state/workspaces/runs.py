"""Workspace state — runs operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403


def _workspace_public_payload_with_full_runs(state: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    public_workspace = state.workspace_public_payload(workspace)
    raw_runs = workspace.get("runs") if isinstance(workspace.get("runs"), list) else []
    public_workspace["runs"] = normalize_workspace_execution_runs(
        raw_runs,
        limit=max(len(raw_runs), 1),
    )
    return public_workspace


class RunsMixin:
    DELTA_EVIDENCE_SAVE_INTERVAL_SECONDS = 5.0
    DELTA_EVIDENCE_SAVE_EVENT_COUNT = 20
    PERSISTED_RUN_EVENT_TYPES = {
        "run.created",
        "run.updated",
        "run.step.updated",
        "job.updated",
        "agent.step.created",
        "agent.tool.called",
        "agent.tool.result",
        "agent.tool.failed",
        "agent.completed",
        "agent.failed",
    }

    def _workspace_delta_evidence_should_save(self, key: str, *, final: bool = False) -> bool:
        state = getattr(self, "workspace_delta_evidence_save_state", None)
        if not isinstance(state, dict):
            state = {}
            self.workspace_delta_evidence_save_state = state
        now = time.time()
        item = state.get(key) if isinstance(state.get(key), dict) else {}
        pending = safe_int(item.get("pending"), 0) + 1
        last_saved = safe_float(item.get("last_saved"), 0.0)
        should_save = (
            final
            or pending >= self.DELTA_EVIDENCE_SAVE_EVENT_COUNT
            or not last_saved
            or now - last_saved >= self.DELTA_EVIDENCE_SAVE_INTERVAL_SECONDS
        )
        state[key] = {
            "pending": 0 if should_save else pending,
            "last_saved": now if should_save else last_saved,
        }
        return should_save

    def _workspace_delta_evidence_mark_saved(self, key: str) -> None:
        state = getattr(self, "workspace_delta_evidence_save_state", None)
        if not isinstance(state, dict):
            state = {}
            self.workspace_delta_evidence_save_state = state
        state[key] = {"pending": 0, "last_saved": time.time()}

    def record_workspace_run_event(self, event: dict[str, Any]) -> bool:
        if not isinstance(event, dict):
            return False
        event_type = str(event.get("type") or "").strip()
        if event_type.endswith(".delta"):
            normalized_event = normalize_workspace_run_event(event)
            if not normalized_event:
                return False
            workspace_id = str(normalized_event.get("workspace_id") or "").strip()
            run_id = str(normalized_event.get("run_id") or "").strip()
            changed = False
            should_save = False
            with self.lock:
                workspace_index = next(
                    (idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id),
                    -1,
                )
                if workspace_index < 0:
                    return False
                workspace = self.workspaces[workspace_index]
                runs = normalize_workspace_execution_runs(workspace.get("runs"))
                run_index = next((idx for idx, item in enumerate(runs) if str(item.get("id") or "") == run_id), -1)
                if run_index < 0:
                    return False
                current_run = runs[run_index]
                current_run["delta_evidence"] = workspace_run_delta_evidence_from_event(
                    current_run.get("delta_evidence"),
                    event,
                )
                current_run["updated_at"] = str(normalized_event.get("created_at") or now_iso()).strip() or now_iso()
                runs[run_index] = normalize_workspace_execution_run(current_run, existing=current_run)
                workspace["runs"] = normalize_workspace_execution_runs(runs)
                event_payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                should_save = self._workspace_delta_evidence_should_save(
                    f"{workspace_id}:{run_id}",
                    final=bool(event_payload.get("final")),
                )
                changed = True
            if changed and should_save:
                self.save_workspaces()
            return changed
        if event_type not in self.PERSISTED_RUN_EVENT_TYPES:
            return False
        normalized_event = normalize_workspace_run_event(event)
        if not normalized_event:
            return False
        workspace_id = str(normalized_event.get("workspace_id") or "").strip()
        run_id = str(normalized_event.get("run_id") or "").strip()
        changed = False
        with self.lock:
            workspace_index = next(
                (idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id),
                -1,
            )
            if workspace_index < 0:
                return False
            workspace = self.workspaces[workspace_index]
            runs = normalize_workspace_execution_runs(workspace.get("runs"))
            run_index = next((idx for idx, item in enumerate(runs) if str(item.get("id") or "") == run_id), -1)
            if run_index < 0:
                return False
            current_run = runs[run_index]
            events = normalize_workspace_run_events(
                [
                    *(current_run.get("events") if isinstance(current_run.get("events"), list) else []),
                    normalized_event,
                ]
            )
            if events == (current_run.get("events") if isinstance(current_run.get("events"), list) else []):
                return False
            current_run["events"] = events
            runs[run_index] = normalize_workspace_execution_run(current_run, existing=current_run)
            workspace["runs"] = normalize_workspace_execution_runs(runs)
            changed = True
        if changed:
            self.save_workspaces()
            self._workspace_delta_evidence_mark_saved(f"{workspace_id}:{run_id}")
        return changed


    def register_workspace_execution_run(
        self,
        workspace_id: str,
        *,
        kind: str,
        trigger: str = "user",
        summary: str = "",
        jobs: list[dict[str, Any]] | None = None,
        steps: list[dict[str, Any]] | None = None,
        package_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        run_kind = str(kind or "").strip() or "node"
        if run_kind not in WORKSPACE_EXECUTION_RUN_KINDS:
            run_kind = "node"
        run_id = make_workspace_execution_run_id()
        normalized_steps: list[dict[str, Any]] = []
        if steps is not None:
            normalized_steps = [
                normalize_workspace_run_step(item, existing=None)
                for item in steps
                if isinstance(item, dict)
            ]
            job_items = jobs if isinstance(jobs, list) else []
            for job in job_items:
                if not isinstance(job, dict):
                    continue
                metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                metadata["execution_run_id"] = run_id
                job_id = str(job.get("id") or "").strip()
                step_index = next(
                    (
                        safe_int(step.get("index"), idx)
                        for idx, step in enumerate(normalized_steps)
                        if str(step.get("job_id") or "").strip() == job_id
                    ),
                    safe_int(metadata.get("step_index"), len(normalized_steps)),
                )
                metadata["step_index"] = step_index
                job["metadata"] = metadata
        else:
            job_items = jobs if isinstance(jobs, list) else []
            for index, job in enumerate(job_items):
                if not isinstance(job, dict):
                    continue
                metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                metadata["execution_run_id"] = run_id
                metadata["step_index"] = index
                job["metadata"] = metadata
                normalized_steps.append(workspace_run_step_from_job(job, index))
        run = normalize_workspace_execution_run(
            {
                "id": run_id,
                "workspace_id": workspace_id,
                "kind": run_kind,
                "status": derive_workspace_execution_run_status(normalized_steps),
                "trigger": str(trigger or "user").strip() or "user",
                "summary": str(summary or "").strip(),
                "steps": normalized_steps,
                "progress": derive_workspace_execution_run_progress(normalized_steps),
                "package_snapshot": copy.deepcopy(package_snapshot) if isinstance(package_snapshot, dict) else {},
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            workspace = self.workspaces[index]
            runs = normalize_workspace_execution_runs(workspace.get("runs"))
            runs.insert(0, run)
            workspace["runs"] = normalize_workspace_execution_runs(runs)
            workspace["updated_at"] = now_iso()
        self.save_workspaces()
        self.save_jobs()
        self.publish_event(
            "run.created",
            workspace_id=workspace_id,
            run_id=str(run.get("id") or "").strip(),
            payload={"run": copy.deepcopy(run)},
        )
        for job in job_items:
            if isinstance(job, dict):
                self.publish_job_event(job, "job.updated")
        return run


    def update_workspace_execution_run_steps(
        self,
        workspace_id: str,
        run_id: str,
        *,
        steps: list[dict[str, Any]] | None = None,
        jobs: list[dict[str, Any]] | None = None,
        summary: str = "",
        package_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        run_id = str(run_id or "").strip()
        if not workspace_id or not run_id:
            raise ValueError("workspace_id and run_id are required")
        incoming_steps = [copy.deepcopy(item) for item in (steps or []) if isinstance(item, dict)]
        job_items = [copy.deepcopy(item) for item in (jobs or []) if isinstance(item, dict)]
        jobs_by_id = {
            str(job.get("id") or "").strip(): job
            for job in job_items
            if str(job.get("id") or "").strip()
        }
        changed_jobs: list[dict[str, Any]] = []
        previous_run: dict[str, Any] = {}
        updated_run: dict[str, Any] = {}
        with self.lock:
            workspace_index = next(
                (idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id),
                -1,
            )
            if workspace_index < 0:
                raise ValueError("workspace not found")
            workspace = self.workspaces[workspace_index]
            runs = normalize_workspace_execution_runs(workspace.get("runs"))
            run_index = next((idx for idx, item in enumerate(runs) if str(item.get("id") or "") == run_id), -1)
            if run_index < 0:
                raise ValueError("workspace execution run not found")

            current_run = runs[run_index]
            previous_run = copy.deepcopy(current_run)
            normalized_steps = [
                normalize_workspace_run_step(item)
                for item in incoming_steps
                if isinstance(item, dict)
            ] if incoming_steps else copy.deepcopy(current_run.get("steps") if isinstance(current_run.get("steps"), list) else [])

            for step_index, step in enumerate(normalized_steps):
                job_id = str(step.get("job_id") or "").strip()
                if not job_id:
                    continue
                job = jobs_by_id.get(job_id)
                if job is not None:
                    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                    metadata["execution_run_id"] = run_id
                    metadata["step_index"] = safe_int(step.get("index"), step_index)
                    job["metadata"] = metadata
                live_job = next((item for item in self.jobs if str(item.get("id") or "") == job_id), None)
                if isinstance(live_job, dict):
                    metadata = live_job.get("metadata") if isinstance(live_job.get("metadata"), dict) else {}
                    metadata["execution_run_id"] = run_id
                    metadata["step_index"] = safe_int(step.get("index"), step_index)
                    live_job["metadata"] = metadata
                    changed_jobs.append(copy.deepcopy(live_job))

            payload: dict[str, Any] = {
                **current_run,
                "steps": normalized_steps,
                "status": derive_workspace_execution_run_status(normalized_steps),
                "progress": derive_workspace_execution_run_progress(normalized_steps),
                "updated_at": now_iso(),
            }
            if summary:
                payload["summary"] = str(summary or "").strip()
            if isinstance(package_snapshot, dict):
                payload["package_snapshot"] = copy.deepcopy(package_snapshot)
            updated_run = normalize_workspace_execution_run(payload, existing=current_run)
            live_jobs_by_id = {
                str(job.get("id") or "").strip(): job
                for job in getattr(self, "jobs", [])
                if isinstance(job, dict) and str(job.get("id") or "").strip()
            }
            runs_by_id = {
                str(run.get("id") or "").strip(): run
                for run in runs
                if isinstance(run, dict) and str(run.get("id") or "").strip()
            }
            runs_by_id[run_id] = updated_run
            updated_run = refresh_workspace_execution_run(updated_run, live_jobs_by_id, runs_by_id)
            runs[run_index] = updated_run
            workspace["runs"] = normalize_workspace_execution_runs(runs)
            workspace["updated_at"] = now_iso()

        self.save_workspaces()
        if changed_jobs:
            self.save_jobs()
        self.publish_event(
            "run.updated",
            workspace_id=workspace_id,
            run_id=run_id,
            payload={"run": copy.deepcopy(updated_run)},
        )
        previous_steps = {
            str(step.get("job_id") or step.get("agent_execution_id") or step.get("index") or ""): step
            for step in (previous_run.get("steps") if isinstance(previous_run.get("steps"), list) else [])
            if isinstance(step, dict)
        }
        for step in updated_run.get("steps") if isinstance(updated_run.get("steps"), list) else []:
            if not isinstance(step, dict):
                continue
            step_key = str(step.get("job_id") or step.get("agent_execution_id") or step.get("index") or "")
            if previous_steps.get(step_key) == step:
                continue
            self.publish_event(
                "run.step.updated",
                workspace_id=workspace_id,
                run_id=run_id,
                job_id=str(step.get("job_id") or "").strip(),
                agent_execution_id=str(step.get("agent_execution_id") or "").strip(),
                payload={"run": copy.deepcopy(updated_run), "step": copy.deepcopy(step)},
            )
        for job in changed_jobs:
            self.publish_job_event(job, "job.updated")
        return updated_run


    def sync_workspace_execution_runs_from_jobs(self, workspace_id: str | None = None) -> bool:
        jobs_by_id = {
            str(job.get("id") or "").strip(): job
            for job in getattr(self, "jobs", [])
            if isinstance(job, dict) and str(job.get("id") or "").strip()
        }
        run_refs: set[tuple[str, str]] = set()
        for job in jobs_by_id.values():
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            run_id = str(metadata.get("execution_run_id") or "").strip()
            bound_workspace_id = str(metadata.get("workspace_id") or "").strip()
            if not run_id or not bound_workspace_id:
                continue
            if workspace_id and bound_workspace_id != workspace_id:
                continue
            run_refs.add((bound_workspace_id, run_id))
        child_job_ids = set(jobs_by_id)
        referenced_run_ids = {run_id for _workspace_id, run_id in run_refs if run_id}
        for workspace in getattr(self, "workspaces", []):
            if not isinstance(workspace, dict):
                continue
            bound_workspace_id = str(workspace.get("id") or "").strip()
            if not bound_workspace_id or (workspace_id and bound_workspace_id != workspace_id):
                continue
            for run in workspace.get("runs") if isinstance(workspace.get("runs"), list) else []:
                if not isinstance(run, dict):
                    continue
                run_id = str(run.get("id") or "").strip()
                if not run_id:
                    continue
                for step in run.get("steps") if isinstance(run.get("steps"), list) else []:
                    if not isinstance(step, dict):
                        continue
                    raw_child_ids = step.get("child_job_ids") if isinstance(step.get("child_job_ids"), list) else []
                    step_child_ids = {
                        str(item or "").strip()
                        for item in raw_child_ids
                        if str(item or "").strip()
                    }
                    if step_child_ids & child_job_ids:
                        run_refs.add((bound_workspace_id, run_id))
                        break
                    raw_child_run_ids = step.get("child_run_ids") if isinstance(step.get("child_run_ids"), list) else []
                    step_child_run_ids = {
                        str(item or "").strip()
                        for item in raw_child_run_ids
                        if str(item or "").strip()
                    }
                    if step_child_run_ids & referenced_run_ids:
                        run_refs.add((bound_workspace_id, run_id))
                        break
        if not run_refs:
            return False

        changed = False
        changed_runs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        with self.lock:
            for bound_workspace_id, run_id in run_refs:
                workspace_index = next(
                    (idx for idx, item in enumerate(self.workspaces) if item.get("id") == bound_workspace_id),
                    -1,
                )
                if workspace_index < 0:
                    continue
                workspace = self.workspaces[workspace_index]
                runs = normalize_workspace_execution_runs(workspace.get("runs"))
                run_index = next((idx for idx, item in enumerate(runs) if str(item.get("id") or "") == run_id), -1)
                if run_index < 0:
                    continue
                current_run = runs[run_index]
                runs_by_id = {
                    str(run.get("id") or "").strip(): run
                    for run in runs
                    if isinstance(run, dict) and str(run.get("id") or "").strip()
                }
                refreshed_run = refresh_workspace_execution_run(current_run, jobs_by_id, runs_by_id)
                if workspace_execution_run_snapshot(refreshed_run) != workspace_execution_run_snapshot(current_run):
                    runs[run_index] = refreshed_run
                    workspace["runs"] = runs
                    workspace["updated_at"] = now_iso()
                    changed_runs.append((bound_workspace_id, current_run, refreshed_run))
                    changed = True
        if changed:
            self.save_workspaces()
            for bound_workspace_id, previous_run, refreshed_run in changed_runs:
                run_id = str(refreshed_run.get("id") or "").strip()
                self.publish_event(
                    "run.updated",
                    workspace_id=bound_workspace_id,
                    run_id=run_id,
                    payload={"run": copy.deepcopy(refreshed_run)},
                )
                previous_steps = {
                    str(step.get("job_id") or step.get("agent_execution_id") or step.get("index") or ""): step
                    for step in previous_run.get("steps", [])
                    if isinstance(step, dict)
                }
                for step in refreshed_run.get("steps", []):
                    if not isinstance(step, dict):
                        continue
                    step_key = str(step.get("job_id") or step.get("agent_execution_id") or step.get("index") or "")
                    previous_step = previous_steps.get(step_key)
                    if previous_step == step:
                        continue
                    self.publish_event(
                        "run.step.updated",
                        workspace_id=bound_workspace_id,
                        run_id=run_id,
                        job_id=str(step.get("job_id") or "").strip(),
                        agent_execution_id=str(step.get("agent_execution_id") or "").strip(),
                        payload={"run": copy.deepcopy(refreshed_run), "step": copy.deepcopy(step)},
                    )
                    step_job_id = str(step.get("job_id") or "").strip()
                    if step_job_id and step_job_id in jobs_by_id:
                        self.publish_job_event(jobs_by_id[step_job_id], "job.updated")
        return changed


    def create_workspace_execution_run(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested = payload if isinstance(payload, dict) else {}
        kind = str(requested.get("kind") or "node").strip() or "node"
        if kind not in WORKSPACE_EXECUTION_RUN_KINDS:
            raise ValueError(f"unsupported run kind: {kind}")
        trigger = str(requested.get("trigger") or "user").strip() or "user"
        summary = str(requested.get("summary") or "").strip()
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
        run = normalize_workspace_execution_run(
            {
                "workspace_id": workspace_id,
                "kind": kind,
                "status": "pending",
                "trigger": trigger,
                "summary": summary,
                "steps": [],
                "progress": derive_workspace_execution_run_progress([]),
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            workspace = self.workspaces[index]
            runs = normalize_workspace_execution_runs(workspace.get("runs"))
            runs.insert(0, run)
            workspace["runs"] = normalize_workspace_execution_runs(runs)
            workspace["updated_at"] = now_iso()
        self.save_workspaces()
        self.publish_event(
            "run.created",
            workspace_id=workspace_id,
            run_id=str(run.get("id") or "").strip(),
            payload={"run": copy.deepcopy(run)},
        )
        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            public_workspace = self.workspace_public_payload(refreshed_workspace)
        return {"run": run, "workspace": public_workspace}


    def list_workspace_execution_runs(
        self,
        workspace_id: str,
        *,
        status: str = "",
        node_kind: str = "",
        job_id: str = "",
        agent_execution_id: str = "",
        created_after: str = "",
        created_before: str = "",
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = self.workspace_public_payload(workspace)
        runs = public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else []
        filtered_runs = filter_workspace_execution_runs(
            runs,
            status=status,
            node_kind=node_kind,
            job_id=job_id,
            agent_execution_id=agent_execution_id,
            created_after=created_after,
            created_before=created_before,
        )
        return {
            "workspace_id": workspace_id,
            "runs": filtered_runs,
        }


    def get_workspace_execution_run(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        run_id = str(run_id or "").strip()
        if not run_id:
            raise KeyError("workspace execution run not found")
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = self.workspace_public_payload(workspace)
        runs = public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else []
        run = next((item for item in runs if isinstance(item, dict) and str(item.get("id") or "") == run_id), None)
        if not run:
            raise KeyError("workspace execution run not found")
        return {
            "workspace_id": workspace_id,
            "run": run,
        }


    def get_workspace_execution_run_replay(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        run_id = str(run_id or "").strip()
        if not run_id:
            raise KeyError("workspace execution run not found")
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = _workspace_public_payload_with_full_runs(self, workspace)
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        runs = public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else []
        run = next((item for item in runs if isinstance(item, dict) and str(item.get("id") or "") == run_id), None)
        if not run:
            raise KeyError("workspace execution run not found")
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "replay": workspace_execution_run_replay_payload(public_workspace, run, jobs=jobs),
        }


    def compare_workspace_execution_runs(self, workspace_id: str, base_run_id: str, target_run_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        base_run_id = str(base_run_id or "").strip()
        target_run_id = str(target_run_id or "").strip()
        if not base_run_id or not target_run_id:
            raise KeyError("workspace execution run not found")
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = _workspace_public_payload_with_full_runs(self, workspace)
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        runs = public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else []
        base_run = next((item for item in runs if isinstance(item, dict) and str(item.get("id") or "") == base_run_id), None)
        target_run = next((item for item in runs if isinstance(item, dict) and str(item.get("id") or "") == target_run_id), None)
        if not base_run or not target_run:
            raise KeyError("workspace execution run not found")
        return {
            "workspace_id": workspace_id,
            "base_run_id": base_run_id,
            "target_run_id": target_run_id,
            "compare": workspace_execution_run_compare_payload(public_workspace, base_run, target_run, jobs=jobs),
        }


    def get_workspace_execution_run_export(self, workspace_id: str, run_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        run_id = str(run_id or "").strip()
        if not run_id:
            raise KeyError("workspace execution run not found")
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = _workspace_public_payload_with_full_runs(self, workspace)
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        runs = public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else []
        run = next((item for item in runs if isinstance(item, dict) and str(item.get("id") or "") == run_id), None)
        if not run:
            raise KeyError("workspace execution run not found")
        return {
            "workspace_id": workspace_id,
            "run_id": run_id,
            "export": workspace_execution_run_export_payload(public_workspace, run, jobs=jobs),
        }
