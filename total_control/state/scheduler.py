from __future__ import annotations

import base64

from ._deps import *  # noqa: F403

class SchedulerMixin:
    def _read_local_job_log_delta(
        self,
        job: dict[str, Any],
        *,
        job_id: str,
        max_bytes: int,
    ) -> dict[str, Any] | None:
        local_path = Path(str(job.get("log_path") or local_log_path(str(job.get("server_id") or "local"), job_id)))
        if not local_path.exists() or local_path.is_symlink() or not local_path.is_file():
            return None
        positions = getattr(self, "job_log_stream_positions", None)
        if not isinstance(positions, dict):
            positions = {}
            self.job_log_stream_positions = positions
        key = f"local:{job_id}"
        previous = positions.get(key) if isinstance(positions.get(key), dict) else {}
        try:
            size = local_path.stat().st_size
            offset = safe_int(previous.get("offset"), 0)
            if str(previous.get("path") or "") != str(local_path.resolve()) or size < offset:
                offset = 0
            read_from = offset
            skipped_bytes = 0
            if size - offset > max_bytes:
                read_from = max(0, size - max_bytes)
                skipped_bytes = max(0, read_from - offset)
            if size <= read_from:
                positions[key] = {"path": str(local_path.resolve()), "offset": size}
                return None
            with local_path.open("rb") as handle:
                handle.seek(read_from)
                raw = handle.read(max_bytes)
        except OSError:
            return None
        positions[key] = {"path": str(local_path.resolve()), "offset": size}
        text = raw.decode("utf-8", errors="replace")
        if not text:
            return None
        return {
            "log": text,
            "offset": read_from,
            "next_offset": size,
            "byte_count": len(raw),
            "truncated": skipped_bytes > 0,
            "skipped_bytes": skipped_bytes,
        }

    def _read_remote_job_log_delta(
        self,
        job: dict[str, Any],
        *,
        job_id: str,
        max_bytes: int,
    ) -> dict[str, Any] | None:
        server = self.server_by_id(str(job.get("server_id") or ""))
        if not server:
            return None
        positions = getattr(self, "job_log_stream_positions", None)
        if not isinstance(positions, dict):
            positions = {}
            self.job_log_stream_positions = positions
        key = f"remote:{job_id}:{str(job.get('server_id') or '')}"
        previous = positions.get(key) if isinstance(positions.get(key), dict) else {}
        offset = safe_int(previous.get("offset"), 0)
        marker = "TC_JOB_LOG_DELTA_" + uuid.uuid4().hex
        script = r'''
import base64
import json
import os
import sys

marker = sys.argv[1]
job_id = sys.argv[2]
offset = int(sys.argv[3])
max_bytes = max(1024, min(int(sys.argv[4]), 131072))
root = os.path.expanduser("~/.total_control/logs")
safe_job_id = "".join(ch for ch in job_id if ch.isalnum() or ch in "-_")

def emit(payload):
    print(marker + json.dumps(payload, separators=(",", ":")))

if safe_job_id != job_id:
    emit({"error": "invalid job id"})
    raise SystemExit(0)

path = os.path.realpath(os.path.join(root, safe_job_id + ".log"))
root_real = os.path.realpath(root)
if not (path == root_real or path.startswith(root_real.rstrip(os.sep) + os.sep)):
    emit({"error": "path outside log root"})
    raise SystemExit(0)
if os.path.islink(path) or not os.path.isfile(path):
    emit({"exists": False, "offset": offset, "next_offset": offset, "data": ""})
    raise SystemExit(0)

size = os.path.getsize(path)
if size < offset:
    offset = 0
read_from = offset
skipped = 0
if size - offset > max_bytes:
    read_from = max(0, size - max_bytes)
    skipped = max(0, read_from - offset)
if size <= read_from:
    emit({"exists": True, "offset": read_from, "next_offset": size, "data": ""})
    raise SystemExit(0)
with open(path, "rb") as handle:
    handle.seek(read_from)
    data = handle.read(max_bytes)
emit({
    "exists": True,
    "offset": read_from,
    "next_offset": size,
    "byte_count": len(data),
    "skipped_bytes": skipped,
    "truncated": skipped > 0,
    "data": base64.b64encode(data).decode("ascii"),
})
'''
        remote_command = (
            "python3 - "
            + " ".join(
                shlex.quote(item)
                for item in (marker, job_id, str(offset), str(max_bytes))
            )
            + " <<'PY'\n"
            + script
            + "\nPY"
        )
        result = ssh_command(
            server,
            "bash -lc " + shlex.quote(remote_command),
            timeout=self.config.remote_timeout_seconds,
        )
        if result.returncode != 0:
            return None
        line = next((item for item in result.stdout.splitlines() if item.startswith(marker)), "")
        if not line:
            return None
        try:
            payload = json.loads(line[len(marker):])
        except json.JSONDecodeError:
            return None
        if payload.get("error") or not payload.get("exists"):
            return None
        next_offset = safe_int(payload.get("next_offset"), offset)
        positions[key] = {"offset": next_offset}
        raw = b""
        if payload.get("data"):
            try:
                raw = base64.b64decode(str(payload.get("data") or ""))
            except Exception:
                raw = b""
        if not raw:
            return None
        return {
            "log": raw.decode("utf-8", errors="replace"),
            "offset": safe_int(payload.get("offset"), offset),
            "next_offset": next_offset,
            "byte_count": safe_int(payload.get("byte_count"), len(raw)),
            "truncated": bool(payload.get("truncated")),
            "skipped_bytes": safe_int(payload.get("skipped_bytes"), 0),
        }

    def read_job_log_delta(self, job: dict[str, Any], *, max_bytes: int = 32768) -> dict[str, Any] | None:
        job_id = str(job.get("id") or "").strip()
        if not job_id:
            return None
        server = self.server_by_id(str(job.get("server_id") or ""))
        if not server:
            return None
        if server.mode == "local":
            return self._read_local_job_log_delta(job, job_id=job_id, max_bytes=max_bytes)
        return self._read_remote_job_log_delta(job, job_id=job_id, max_bytes=max_bytes)

    def publish_job_log_delta(
        self,
        job: dict[str, Any],
        *,
        final: bool = False,
    ) -> bool:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        workspace_id = str(metadata.get("workspace_id") or "").strip()
        job_id = str(job.get("id") or "").strip()
        if not workspace_id or not job_id:
            return False
        delta = self.read_job_log_delta(job)
        if not delta:
            if final:
                positions = getattr(self, "job_log_stream_positions", None)
                if isinstance(positions, dict):
                    positions.pop(f"local:{job_id}", None)
                    positions.pop(f"remote:{job_id}:{str(job.get('server_id') or '')}", None)
            return False
        payload = {
            "job_id": job_id,
            "status": str(job.get("status") or "").strip(),
            "server_id": str(job.get("server_id") or "").strip(),
            "log": str(delta.get("log") or ""),
            "final": bool(final),
            "offset": safe_int(delta.get("offset"), 0),
            "next_offset": safe_int(delta.get("next_offset"), 0),
            "byte_count": safe_int(delta.get("byte_count"), 0),
            "truncated": bool(delta.get("truncated")),
            "skipped_bytes": safe_int(delta.get("skipped_bytes"), 0),
            "line_count": len(str(delta.get("log") or "").splitlines()),
        }
        self.publish_event(
            "job.log.delta",
            workspace_id=workspace_id,
            run_id=str(metadata.get("execution_run_id") or "").strip(),
            job_id=job_id,
            payload=payload,
        )
        if final:
            positions = getattr(self, "job_log_stream_positions", None)
            if isinstance(positions, dict):
                positions.pop(f"local:{job_id}", None)
                positions.pop(f"remote:{job_id}:{str(job.get('server_id') or '')}", None)
        return True


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
                self.publish_job_log_delta(job)
                continue
            tail = self.tail_log(job, lines=240)
            exit_match = re.search(r"(?:^|\s)exit_code=(-?\d+)(?:\s|$)", tail)
            if exit_match and safe_int(exit_match.group(1), 1) == 0:
                job["status"] = "done"
                job["error"] = ""
            elif exit_match:
                job["status"] = "failed"
                job["error"] = f"process exited with code {safe_int(exit_match.group(1), 1)}"
            else:
                job["status"] = "failed"
                job["error"] = "tmux session ended before Total Control wrote an exit_code marker"
            job["finished_at"] = now_iso()
            self.publish_job_log_delta(job, final=True)
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
                self.maybe_auto_cleanup_runtime_storage()
            except Exception as exc:  # noqa: BLE001 - background loop must keep running.
                print(f"[total-control] scheduler error: {exc}", flush=True)
            self.stop_event.wait(max(self.config.poll_interval_seconds, 2))
