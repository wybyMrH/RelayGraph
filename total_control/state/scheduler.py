from __future__ import annotations

from ._deps import *  # noqa: F403

class SchedulerMixin:
    def monitor_jobs(self) -> None:
        changed = False
        changed_jobs: list[dict[str, Any]] = []
        with self.lock:
            running_jobs = [job for job in self.jobs if job.get("status") == "running"]
            starting_jobs = sorted(
                [job for job in self.jobs if job.get("status") == "starting"],
                key=self.queue_sort_key,
            )
            queued_jobs = sorted(
                [job for job in self.jobs if job.get("status") == "queued"],
                key=self.queue_sort_key,
            )

        for job in running_jobs:
            if self.tmux_running(job):
                continue
            tail = self.tail_log(job, lines=240)
            if "exit_code=0" in tail:
                job["status"] = "done"
            elif "exit_code=" in tail:
                job["status"] = "failed"
            else:
                job["status"] = "done"
            job["finished_at"] = now_iso()
            changed_jobs.append(job)
            if job.get("kind") in {"profile", "preset-profile"}:
                target_ids = [str(item) for item in job.get("target_job_ids", [])]
                peak_mib = parse_smoke_peak_mib(tail)
                metadata = job.get("metadata") or {}
                safety = safe_float(metadata.get("profile_safety", metadata.get("safety", 1.2)), 1.2)
                measured_mib = int(peak_mib * max(safety, 1.0)) if peak_mib else 0
                for target in self.jobs:
                    if target.get("id") not in target_ids:
                        continue
                    if job["status"] == "done" and measured_mib > 0:
                        target["min_free_mib"] = measured_mib
                        target["profile_measured_mib"] = peak_mib
                        target["status"] = "queued"
                        target["error"] = f"profile peak {peak_mib} MiB, reserve {measured_mib} MiB"
                        changed_jobs.append(target)
                    else:
                        target["status"] = "failed"
                        target["error"] = "profile/smoke failed or peak memory not found"
                        changed_jobs.append(target)
            changed = True

        for job in starting_jobs:
            if job.get("status") == "starting":
                self.start_job(job, allow_busy=True)
                changed_jobs.append(job)
                changed = True
        for job in queued_jobs:
            ready, dependency_reason = self.job_dependencies_state(job)
            if not ready:
                if dependency_reason.startswith("dependency failed:"):
                    if job.get("status") != "failed" or job.get("error") != dependency_reason:
                        job["status"] = "failed"
                        job["error"] = dependency_reason
                        job["finished_at"] = now_iso()
                        changed_jobs.append(job)
                        changed = True
                elif job.get("error") != dependency_reason:
                        job["error"] = dependency_reason
                        changed_jobs.append(job)
                        changed = True
                continue
            if str(job.get("gpu_index") or "").strip().lower() in {"none", "no_gpu", "cpu"}:
                self.start_job(job, allow_busy=True)
                changed_jobs.append(job)
                changed = True
                continue
            ok, _server_id, _gpu, reason = self.find_gpu(job)
            if ok:
                self.start_job(job, allow_busy=False)
                changed_jobs.append(job)
                changed = True
            else:
                if job.get("error") != reason:
                    job["error"] = reason
                    changed_jobs.append(job)
                    changed = True

        if changed:
            self.save_jobs()
            self.sync_workspace_execution_runs_from_jobs()
            seen_job_ids: set[str] = set()
            for job in changed_jobs:
                job_id = str(job.get("id") or "").strip()
                if job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job_id)
                self.publish_job_event(job, "job.updated")


    def scheduler_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.refresh_status()
                self.monitor_jobs()
                self.maybe_auto_cleanup_preview_cache()
            except Exception as exc:  # noqa: BLE001 - background loop must keep running.
                print(f"[total-control] scheduler error: {exc}", flush=True)
            self.stop_event.wait(max(self.config.poll_interval_seconds, 2))
