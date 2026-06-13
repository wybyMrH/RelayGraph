"""Auto-split from jobs.py — crud."""

from __future__ import annotations

from ._deps import *  # noqa: F403


class CrudJobsMixin:
    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = getattr(self, "config", AppConfig())
        command = str(payload.get("command") or "").strip()
        if not command:
            raise ValueError("command is required")
        server_id = str(payload.get("server_id") or "local")
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")

        gpu_value = payload.get("gpu_index", "auto")
        gpu_index: int | str | None
        gpu_value_text = str(gpu_value).strip().lower() if gpu_value is not None else ""
        if gpu_value in (None, "", "auto"):
            gpu_index = "auto"
        elif gpu_value_text in {"none", "no_gpu", "cpu"}:
            gpu_index = "none"
        else:
            gpu_index = safe_int(gpu_value)

        wait_for_idle = bool(payload.get("wait_for_idle", True))
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        job_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
        job = {
            "id": job_id,
            "name": str(payload.get("name") or command.splitlines()[0][:80]),
            "server_id": server_id,
            "requested_server_id": server_id,
            "candidate_server_ids": list(payload.get("candidate_server_ids") or []),
            "gpu_index": gpu_index,
            "requested_gpu_index": gpu_index,
            "command": command,
            "command_display": str(payload.get("command_display") or command),
            "cwd": str(payload.get("cwd") or "").strip(),
            "env_name": str(payload.get("env_name") or "").strip(),
            "min_free_mib": safe_int(payload.get("min_free_mib"), config.idle_min_free_mib),
            "max_gpu_util": safe_int(payload.get("max_gpu_util"), config.idle_max_gpu_util),
            "wait_for_idle": wait_for_idle,
            "status": "queued" if wait_for_idle else "starting",
            "session": make_session_name(job_id),
            "kind": str(payload.get("kind") or "command"),
            "target_job_ids": list(payload.get("target_job_ids") or []),
            "profile_key": str(payload.get("profile_key") or ""),
            "profile_measured_mib": 0,
            "created_at": now_iso(),
            "started_at": "",
            "finished_at": "",
            "error": "",
            "queue_rank": 0,
            "log_path": str(local_log_path(server_id, job_id).resolve()),
            "remote_log_path": "",
            "metadata": metadata,
        }
        with self.lock:
            self.reserve_queue_ranks([job])
            self.jobs.insert(0, job)
        if wait_for_idle:
            self.save_jobs()
        else:
            self.start_job(job, allow_busy=True)
        self.publish_job_event(job, "job.updated")
        return job


    def clone_job_payload(self, job: dict[str, Any]) -> dict[str, Any]:
        requested_server = str(job.get("requested_server_id") or job.get("server_id") or "local")
        requested_gpu = job.get("requested_gpu_index", job.get("gpu_index", "auto"))
        metadata = copy.deepcopy(job.get("metadata") or {})
        return {
            "name": str(job.get("name") or job.get("command_display") or job.get("command") or "任务"),
            "server_id": requested_server,
            "candidate_server_ids": list(job.get("candidate_server_ids") or []),
            "gpu_index": requested_gpu,
            "command": str(job.get("command_display") or job.get("command") or ""),
            "command_display": str(job.get("command_display") or job.get("command") or ""),
            "cwd": str(job.get("cwd") or ""),
            "env_name": str(job.get("env_name") or ""),
            "min_free_mib": safe_int(job.get("min_free_mib"), self.config.idle_min_free_mib),
            "max_gpu_util": safe_int(job.get("max_gpu_util"), self.config.idle_max_gpu_util),
            "wait_for_idle": bool(job.get("wait_for_idle", True)),
            "kind": str(job.get("kind") or "command"),
            "target_job_ids": [],
            "profile_key": str(job.get("profile_key") or ""),
            "metadata": metadata,
        }


    def copy_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        return self.create_job(self.clone_job_payload(job))


    def retry_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        if str(job.get("status") or "") in {"running", "queued", "starting", "blocked"}:
            raise ValueError("任务仍在进行中，不能重试")
        return self.create_job(self.clone_job_payload(job))


    def delete_job(self, job_id: str) -> None:
        """Delete a job from the jobs list."""
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
            if not job:
                raise ValueError("job not found")
            if str(job.get("status") or "") in {"running", "queued", "starting", "blocked"}:
                raise ValueError("任务仍在进行中，不能删除")
            self.jobs = [item for item in self.jobs if item["id"] != job_id]
            self.save_jobs()


    def clear_completed_jobs(self) -> int:
        """Clear all completed/failed/stopped jobs. Returns count of deleted jobs."""
        with self.lock:
            deletable_statuses = {"done", "failed", "stopped"}
            before_count = len(self.jobs)
            self.jobs = [item for item in self.jobs if item.get("status") not in deletable_statuses]
            deleted_count = before_count - len(self.jobs)
            if deleted_count > 0:
                self.save_jobs()
            return deleted_count
