"""Workspace state — runs operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class RunsMixin:
    def register_workspace_execution_run(
        self,
        workspace_id: str,
        *,
        kind: str,
        trigger: str = "user",
        summary: str = "",
        jobs: list[dict[str, Any]] | None = None,
        steps: list[dict[str, Any]] | None = None,
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
        return run


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
                refreshed_run = refresh_workspace_execution_run(current_run, jobs_by_id)
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


    def list_workspace_execution_runs(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        self.sync_workspace_execution_runs_from_jobs(workspace_id)
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public_workspace = self.workspace_public_payload(workspace)
        return {
            "workspace_id": workspace_id,
            "runs": public_workspace.get("runs") if isinstance(public_workspace.get("runs"), list) else [],
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
