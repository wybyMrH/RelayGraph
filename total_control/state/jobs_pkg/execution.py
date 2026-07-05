"""Auto-split from jobs.py — execution."""

from __future__ import annotations

import base64

from ._deps import *  # noqa: F403


def _read_text_file_tail(path: Path, *, lines: int = 200, max_bytes: int = 4 * 1024 * 1024) -> str:
    line_count = max(1, int(lines or 1))
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    if size <= 0:
        return ""

    read_bytes = min(size, 64 * 1024)
    max_read = max(read_bytes, min(size, max_bytes))
    raw = b""
    while True:
        try:
            with path.open("rb") as handle:
                handle.seek(max(0, size - read_bytes))
                raw = handle.read(read_bytes)
        except OSError:
            return ""
        if read_bytes >= size or raw.count(b"\n") >= line_count or read_bytes >= max_read:
            break
        read_bytes = min(size, read_bytes * 2, max_read)

    return "\n".join(raw.decode("utf-8", errors="replace").splitlines()[-line_count:])


def _read_text_file_chunk(path: Path, *, offset: int = 0, max_bytes: int = 131072) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError:
        return {
            "log": "",
            "offset": max(0, int(offset or 0)),
            "next_offset": max(0, int(offset or 0)),
            "file_size": 0,
            "byte_count": 0,
            "truncated": False,
            "skipped_bytes": 0,
            "exists": False,
        }
    start = max(0, int(offset or 0))
    if size < start:
        start = 0
    limit = max(1024, min(int(max_bytes or 131072), 1024 * 1024))
    read_from = start
    skipped_bytes = 0
    if size - start > limit:
        read_from = max(0, size - limit)
        skipped_bytes = max(0, read_from - start)
    if size <= read_from:
        return {
            "log": "",
            "offset": read_from,
            "next_offset": size,
            "file_size": size,
            "byte_count": 0,
            "truncated": skipped_bytes > 0,
            "skipped_bytes": skipped_bytes,
            "exists": True,
        }
    try:
        with path.open("rb") as handle:
            handle.seek(read_from)
            raw = handle.read(limit)
    except OSError:
        raw = b""
    return {
        "log": raw.decode("utf-8", errors="replace"),
        "offset": read_from,
        "requested_offset": start,
        "next_offset": size,
        "file_size": size,
        "byte_count": len(raw),
        "truncated": skipped_bytes > 0,
        "skipped_bytes": skipped_bytes,
        "exists": True,
    }


def _job_log_snapshot(job: dict[str, Any], *, lines: int = 200, max_bytes: int = 131072) -> dict[str, Any]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    snapshot = metadata.get("log_tail_snapshot") if isinstance(metadata.get("log_tail_snapshot"), dict) else {}
    text = str(snapshot.get("tail") or "")
    if not text:
        return {}
    reasons = [
        str(item or "").strip()
        for item in snapshot.get("truncation_reasons", [])
        if str(item or "").strip()
    ] if isinstance(snapshot.get("truncation_reasons"), list) else []
    limited = text[-max(max_bytes, 0):] if max_bytes > 0 else text
    if max_bytes > 0 and len(text) > max_bytes:
        reasons.append("snapshot_request_limit")
    tail = "\n".join(limited.splitlines()[-max(1, int(lines or 1)):])
    if len(limited.splitlines()) > max(1, int(lines or 1)):
        reasons.append("line_limit")
    byte_count = len(tail.encode("utf-8"))
    file_size = safe_int(snapshot.get("file_size"), byte_count)
    read_bytes = safe_int(snapshot.get("read_bytes"), safe_int(snapshot.get("byte_count"), byte_count))
    skipped_bytes = safe_int(snapshot.get("skipped_bytes"), max(file_size - read_bytes, 0) if file_size and read_bytes else 0)
    return {
        "log": tail,
        "source": "snapshot",
        "mode": "snapshot",
        "snapshot_captured_at": str(snapshot.get("captured_at") or "").strip(),
        "snapshot_schema": str(snapshot.get("schema") or "").strip(),
        "exists": False,
        "file_size": file_size,
        "snapshot_size": byte_count,
        "byte_count": byte_count,
        "offset": 0,
        "requested_offset": 0,
        "next_offset": byte_count,
        "truncated": bool(snapshot.get("truncated")) or bool(reasons) or skipped_bytes > 0,
        "skipped_bytes": skipped_bytes,
        "truncation_reasons": list(dict.fromkeys(reasons)),
    }


class ExecutionJobsMixin:
    def find_gpu(self, job: dict[str, Any]) -> tuple[bool, str | None, int | None, str]:
        with self.lock:
            statuses = list(self.statuses)
        requested_server = str(job.get("server_id") or job.get("requested_server_id") or "local")
        candidate_server_ids = {str(item) for item in job.get("candidate_server_ids", []) if str(item)}
        if requested_server != "auto":
            candidate_server_ids = {requested_server}

        server_statuses = [
            item for item in statuses
            if item.get("online") and (not candidate_server_ids or item.get("id") in candidate_server_ids)
        ]
        if not statuses:
            return False, None, None, "no status yet"
        if not server_statuses:
            if requested_server != "auto":
                server_status = next((item for item in statuses if item["id"] == requested_server), None)
                return False, None, None, (server_status or {}).get("error") or "server offline"
            return False, None, None, "no online candidate server"

        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        requested = job.get("gpu_index", job.get("requested_gpu_index", "auto"))
        for server_status in server_statuses:
            for gpu in server_status.get("gpus", []):
                if requested != "auto" and gpu.get("index") != requested:
                    continue
                free_ok = gpu.get("memory_free_mib", 0) >= job.get("min_free_mib", self.config.idle_min_free_mib)
                util_ok = gpu.get("gpu_util", 100) <= job.get("max_gpu_util", self.config.idle_max_gpu_util)
                if free_ok and util_ok:
                    candidates.append((server_status, gpu))
        if not candidates:
            return False, None, None, "waiting for idle GPU"
        candidates.sort(
            key=lambda item: (item[1].get("memory_free_mib", 0), -item[1].get("gpu_util", 100)),
            reverse=True,
        )
        server_status, gpu = candidates[0]
        return True, str(server_status["id"]), int(gpu["index"]), ""


    def pick_server_for_job(self, job: dict[str, Any]) -> tuple[bool, str | None, str]:
        requested_server = str(job.get("server_id") or job.get("requested_server_id") or "local").strip() or "local"
        candidate_server_ids = {str(item) for item in job.get("candidate_server_ids", []) if str(item)}
        with self.lock:
            statuses = list(self.statuses)

        if requested_server != "auto":
            server = self.server_by_id(requested_server)
            if not server:
                return False, None, f"unknown server: {requested_server}"
            return True, requested_server, ""

        server_statuses = [
            item for item in statuses
            if item.get("online") and (not candidate_server_ids or item.get("id") in candidate_server_ids)
        ]
        if not server_statuses:
            return False, None, "no online candidate server"

        def server_priority(status: dict[str, Any]) -> tuple[int, int, int, str]:
            process_count = len(status.get("processes") or [])
            busy_gpu_count = sum(1 for gpu in status.get("gpus", []) if gpu.get("state") == "busy")
            return (
                0 if status.get("id") == "local" else 1,
                process_count,
                busy_gpu_count,
                str(status.get("id") or ""),
            )

        server_statuses.sort(key=server_priority)
        return True, str(server_statuses[0].get("id") or ""), ""


    def start_job(
        self,
        job: dict[str, Any],
        allow_busy: bool = False,
        *,
        publish_events: bool = True,
    ) -> None:
        running_probe_job: dict[str, Any] | None = None
        with self.lock:
            status = str(job.get("status") or "").strip()
            if status == "running":
                running_probe_job = copy.deepcopy(job)
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            launching_at = safe_float(metadata.get("_launching_at"), 0.0)
            if launching_at and time.time() - launching_at < 30:
                return
        if running_probe_job and self.tmux_running(running_probe_job):
            return
        with self.lock:
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            launching_at = safe_float(metadata.get("_launching_at"), 0.0)
            if launching_at and time.time() - launching_at < 30:
                return
            metadata["_launching_at"] = time.time()
            job["metadata"] = metadata
        gpuless = str(job.get("gpu_index") or "").strip().lower() in {"none", "no_gpu", "cpu"}
        try:
            if gpuless:
                job["gpu_index"] = "none"
                if str(job.get("server_id") or "").strip() in {"", "auto"}:
                    ok, selected_server_id, reason = self.pick_server_for_job(job)
                    if not ok:
                        job["error"] = reason
                        return
                    job["server_id"] = selected_server_id
            elif not allow_busy:
                ok, selected_server_id, gpu_index, reason = self.find_gpu(job)
                if not ok:
                    job["error"] = reason
                    return
                job["server_id"] = selected_server_id
                job["gpu_index"] = gpu_index
            elif job.get("gpu_index") == "auto":
                ok, selected_server_id, gpu_index, _reason = self.find_gpu(job)
                if selected_server_id:
                    job["server_id"] = selected_server_id
                job["gpu_index"] = gpu_index if ok else 0

            server = self.server_by_id(str(job.get("server_id") or ""))
            if not server:
                job["status"] = "failed"
                job["error"] = "unknown server"
                metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                metadata.pop("_launching_at", None)
                job["metadata"] = metadata
                self.save_jobs()
                self.sync_workspace_execution_runs_from_jobs()
                if publish_events:
                    self.publish_job_event(job, "job.updated")
                return
            self.apply_server_paths(job, server)

            runtime_command = str(job.get("command") or "")
            runtime_display = str(job.get("command_display") or runtime_command)
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            transfer_spec = metadata.get("transfer_spec") if isinstance(metadata.get("transfer_spec"), dict) else None
            if str(job.get("kind") or "") == "transfer" and transfer_spec:
                try:
                    runtime_command, runtime_display = build_transfer_command(transfer_spec, self.servers)
                    job["command"] = runtime_display
                    job["command_display"] = runtime_display
                except ValueError as exc:
                    job["status"] = "failed"
                    job["finished_at"] = now_iso()
                    job["error"] = str(exc)
                    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                    metadata.pop("_launching_at", None)
                    job["metadata"] = metadata
                    self.save_jobs()
                    self.sync_workspace_execution_runs_from_jobs()
                    if publish_events:
                        self.publish_job_event(job, "job.updated")
                    return

            session = job["session"]
            if server.mode == "local":
                log_path = str(local_log_path(server.id, job["id"]).resolve())
                script = build_job_script(
                    job,
                    log_path,
                    remote=False,
                    server=server,
                    command_override=runtime_command,
                    command_display=runtime_display,
                )
                command = tmux_new_session_args(session, "bash -lc " + shlex.quote(script))
                result = run_command(command, timeout=5)
            else:
                log_path = str(local_log_path(server.id, job["id"]).resolve())
                remote_path = remote_log_path(job["id"])
                script = build_job_script(
                    job,
                    remote_path,
                    remote=True,
                    server=server,
                    command_override=runtime_command,
                    command_display=runtime_display,
                )
                shell_command = "bash -lc " + shlex.quote(script)
                remote_command = (
                    f"tmux new-session -d -s {shlex.quote(session)} "
                    f"-x {TMUX_DEFAULT_COLUMNS} -y {TMUX_DEFAULT_ROWS} "
                    f"{shlex.quote(shell_command)}"
                )
                result = ssh_command(server, remote_command, timeout=self.config.remote_timeout_seconds)

            job["log_path"] = log_path
            if server.mode != "local":
                job["remote_log_path"] = remote_log_path(job["id"])
            if result.returncode == 0:
                job["status"] = "running"
                job["started_at"] = now_iso()
                job["error"] = ""
            else:
                job["status"] = "failed"
                job["finished_at"] = now_iso()
                job["error"] = (result.stderr.strip() or result.stdout.strip() or "tmux start failed")[-1000:]
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            metadata.pop("_launching_at", None)
            job["metadata"] = metadata
            self.save_jobs()
            self.sync_workspace_execution_runs_from_jobs()
            if publish_events:
                self.publish_job_event(job, "job.updated")
        finally:
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            metadata.pop("_launching_at", None)
            job["metadata"] = metadata


    def tmux_running(self, job: dict[str, Any]) -> bool:
        server = self.server_by_id(job["server_id"])
        if not server:
            return False
        session = str(job.get("session") or "")
        if not session:
            return False
        if server.mode == "local":
            result = run_command(["tmux", "has-session", "-t", session], timeout=3)
        else:
            result = ssh_command(server, f"tmux has-session -t {shlex.quote(session)}", timeout=self.config.remote_timeout_seconds)
        return result.returncode == 0


    def tail_log(self, job: dict[str, Any], lines: int = 200) -> str:
        server = self.server_by_id(job["server_id"])
        if not server:
            return "unknown server"
        local_path = normalize_allowed_local_job_log_path(job, local_log_path(job["server_id"], job["id"]))
        if server.mode == "local":
            if not local_path or not local_path.exists():
                return str(_job_log_snapshot(job, lines=lines).get("log") or "")
            return _read_text_file_tail(local_path, lines=lines)
        chunk = self._remote_job_log_chunk(job, offset=0, max_bytes=4 * 1024 * 1024)
        if not chunk.get("error") and chunk.get("log"):
            text = "\n".join(str(chunk.get("log") or "").splitlines()[-max(1, int(lines or 1)):])
            if local_path:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(text, encoding="utf-8")
            return text
        if local_path and local_path.exists():
            return _read_text_file_tail(local_path, lines=lines)
        snapshot = _job_log_snapshot(job, lines=lines)
        return str(snapshot.get("log") or chunk.get("error") or "").strip()


    def _remote_job_log_chunk(self, job: dict[str, Any], *, offset: int = 0, max_bytes: int = 131072) -> dict[str, Any]:
        server = self.server_by_id(job["server_id"])
        if not server:
            return {"log": "unknown server", "offset": 0, "next_offset": 0, "file_size": 0, "byte_count": 0}
        marker = "TC_JOB_LOG_CHUNK_" + uuid.uuid4().hex
        remote_path_text = str(job.get("remote_log_path") or remote_log_path(job["id"]))
        script = r'''
import base64
import json
import os
import sys

marker = sys.argv[1]
path_text = sys.argv[2]
offset = max(0, int(sys.argv[3]))
max_bytes = max(1024, min(int(sys.argv[4]), 1048576))
root = os.path.realpath(os.path.expanduser("~/.total_control/logs"))

def emit(payload):
    print(marker + json.dumps(payload, separators=(",", ":")))

def normalize(path):
    text = str(path or "").strip()
    if text == "$HOME" or text.startswith("$HOME/"):
        text = os.path.join(os.path.expanduser("~"), text[6:].lstrip("/"))
    text = os.path.expanduser(text)
    real = os.path.realpath(text)
    if real == root or real.startswith(root.rstrip(os.sep) + os.sep):
        return real
    return ""

path = normalize(path_text)
if not path:
    emit({"error": "path outside log root", "offset": offset, "next_offset": offset, "data": ""})
    raise SystemExit(0)
if os.path.islink(path) or not os.path.isfile(path):
    emit({"exists": False, "offset": offset, "next_offset": offset, "file_size": 0, "data": ""})
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
    emit({"exists": True, "offset": read_from, "next_offset": size, "file_size": size, "data": "", "skipped_bytes": skipped, "truncated": skipped > 0})
    raise SystemExit(0)
with open(path, "rb") as handle:
    handle.seek(read_from)
    data = handle.read(max_bytes)
emit({
    "exists": True,
    "offset": read_from,
    "requested_offset": offset,
    "next_offset": size,
    "file_size": size,
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
                for item in (marker, remote_path_text, str(max(0, int(offset or 0))), str(max_bytes))
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
            return {
                "log": result.stderr.strip(),
                "offset": max(0, int(offset or 0)),
                "next_offset": max(0, int(offset or 0)),
                "file_size": 0,
                "byte_count": 0,
                "error": result.stderr.strip() or "remote log read failed",
            }
        line = next((item for item in result.stdout.splitlines() if item.startswith(marker)), "")
        if not line:
            return {
                "log": "",
                "offset": max(0, int(offset or 0)),
                "next_offset": max(0, int(offset or 0)),
                "file_size": 0,
                "byte_count": 0,
                "error": "remote log marker missing",
            }
        try:
            payload = json.loads(line[len(marker):])
        except json.JSONDecodeError:
            payload = {}
        raw = b""
        if payload.get("data"):
            try:
                raw = base64.b64decode(str(payload.get("data") or ""))
            except Exception:
                raw = b""
        return {
            "log": raw.decode("utf-8", errors="replace"),
            "offset": safe_int(payload.get("offset"), offset),
            "requested_offset": safe_int(payload.get("requested_offset"), offset),
            "next_offset": safe_int(payload.get("next_offset"), offset),
            "file_size": safe_int(payload.get("file_size"), 0),
            "byte_count": safe_int(payload.get("byte_count"), len(raw)),
            "truncated": bool(payload.get("truncated")),
            "skipped_bytes": safe_int(payload.get("skipped_bytes"), 0),
            "exists": bool(payload.get("exists")),
            **({"error": str(payload.get("error") or "").strip()} if payload.get("error") else {}),
        }


    def job_log_payload(
        self,
        job: dict[str, Any],
        *,
        lines: int = 200,
        offset: int | None = None,
        max_bytes: int = 131072,
    ) -> dict[str, Any]:
        job_id = str(job.get("id") or "").strip()
        if offset is None:
            snapshot = _job_log_snapshot(job, lines=lines)
            server = self.server_by_id(job["server_id"])
            local_path = normalize_allowed_local_job_log_path(job, local_log_path(job["server_id"], job_id))
            local_exists = False
            file_size = 0
            if local_path:
                try:
                    local_exists = local_path.exists() and not local_path.is_symlink() and local_path.is_file()
                    file_size = local_path.stat().st_size if local_exists else 0
                except OSError:
                    local_exists = False
                    file_size = 0
            source = "file"
            exists = local_exists
            error = ""
            if not server:
                log = "unknown server"
                source = "error"
            elif server.mode == "local":
                if local_exists and local_path:
                    log = _read_text_file_tail(local_path, lines=lines)
                    source = "file"
                    exists = True
                elif snapshot:
                    log = str(snapshot.get("log") or "")
                    source = "snapshot"
                    file_size = safe_int(snapshot.get("file_size"), 0)
                    exists = False
                else:
                    log = str(self.tail_log(job, lines=lines))
                    exists = False
            else:
                chunk = self._remote_job_log_chunk(job, offset=0, max_bytes=4 * 1024 * 1024)
                if not chunk.get("error") and chunk.get("log"):
                    log = "\n".join(str(chunk.get("log") or "").splitlines()[-max(1, int(lines or 1)):])
                    source = "remote"
                    exists = bool(chunk.get("exists", True))
                    file_size = safe_int(chunk.get("file_size"), safe_int(chunk.get("next_offset"), 0))
                    if local_path:
                        try:
                            local_path.parent.mkdir(parents=True, exist_ok=True)
                            local_path.write_text(log, encoding="utf-8")
                        except OSError:
                            pass
                elif local_exists and local_path:
                    log = _read_text_file_tail(local_path, lines=lines)
                    source = "file"
                    exists = True
                elif snapshot:
                    log = str(snapshot.get("log") or "")
                    source = "snapshot"
                    file_size = safe_int(snapshot.get("file_size"), 0)
                    exists = False
                else:
                    log = str(chunk.get("error") or self.tail_log(job, lines=lines))
                    source = "remote"
                    error = str(chunk.get("error") or "")
                    exists = bool(chunk.get("exists", False))
                    file_size = safe_int(chunk.get("file_size"), 0)
            payload = {
                "job_id": job_id,
                "mode": "tail",
                "log": log,
                "line_count": len(log.splitlines()),
                "source": source,
                "exists": exists,
            }
            if error:
                payload["error"] = error
            if source == "snapshot":
                payload.update(
                    {
                        "exists": False,
                        "snapshot_captured_at": snapshot.get("snapshot_captured_at", ""),
                        "snapshot_schema": snapshot.get("snapshot_schema", ""),
                    }
                )
            payload.update({"next_offset": file_size, "file_size": file_size})
            return payload
        server = self.server_by_id(job["server_id"])
        if not server:
            return {"job_id": job_id, "mode": "chunk", "log": "unknown server", "offset": 0, "next_offset": 0}
        if server.mode == "local":
            local_path = normalize_allowed_local_job_log_path(job, local_log_path(job["server_id"], job_id))
            if local_path and local_path.exists() and not local_path.is_symlink() and local_path.is_file():
                chunk = _read_text_file_chunk(local_path, offset=offset, max_bytes=max_bytes)
            else:
                snapshot = _job_log_snapshot(job, lines=200, max_bytes=max_bytes)
                chunk = snapshot or {
                    "log": "",
                    "offset": max(0, int(offset or 0)),
                    "next_offset": max(0, int(offset or 0)),
                    "file_size": 0,
                    "byte_count": 0,
                    "exists": False,
                    "truncated": False,
                    "skipped_bytes": 0,
                }
        else:
            chunk = self._remote_job_log_chunk(job, offset=offset, max_bytes=max_bytes)
            local_path = normalize_allowed_local_job_log_path(job, local_log_path(job["server_id"], job_id))
            if chunk.get("log"):
                if local_path:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_text(str(chunk.get("log") or ""), encoding="utf-8")
        log = str(chunk.get("log") or "")
        return {
            "job_id": job_id,
            "mode": "chunk",
            **chunk,
            "line_count": len(log.splitlines()),
        }


    def list_tmux_sessions(self, server_id: str) -> list[dict[str, Any]]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        fmt = "#{session_name}|#{session_created}|#{session_windows}|#{session_attached}"
        if server.mode == "local":
            result = run_command(["tmux", "list-sessions", "-F", fmt], timeout=4)
        else:
            result = ssh_command(server, f"tmux list-sessions -F {shlex.quote(fmt)}", timeout=self.config.remote_timeout_seconds)
        if result.returncode != 0:
            text = (result.stderr or result.stdout or "").strip()
            if "no server running" in text.lower() or "failed to connect" in text.lower():
                return []
            raise ValueError(text or "tmux list failed")
        sessions = []
        for line in result.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) != 4:
                continue
            sessions.append(
                {
                    "name": parts[0],
                    "created": safe_int(parts[1]),
                    "windows": safe_int(parts[2]),
                    "attached": parts[3] == "1",
                }
            )
        return sessions


    def capture_tmux(self, server_id: str, session: str, lines: int = 2000) -> str:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        session = session.strip()
        if not session:
            raise ValueError("session name required")
        history = max(50, min(int(lines), 50000))
        # -p print to stdout, -J join wrapped lines, -S -N start N lines back into history
        if server.mode == "local":
            prepare_tmux_for_capture(session)
            result = run_command(
                ["tmux", "capture-pane", "-p", "-J", "-S", f"-{history}", "-t", session],
                timeout=4,
            )
        else:
            remote_cmd = (
                "bash -lc "
                + shlex.quote(
                    tmux_resize_shell_script(session)
                    + "\n"
                    + f"tmux capture-pane -p -J -S -{history} -t {shlex.quote(session)}"
                )
            )
            result = ssh_command(server, remote_cmd, timeout=self.config.remote_timeout_seconds)
        if result.returncode != 0:
            text = (result.stderr or result.stdout or "").strip()
            raise ValueError(text or "tmux capture-pane failed")
        return result.stdout


    def stop_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        server = self.server_by_id(job["server_id"])
        if server:
            session = str(job.get("session") or "")
            if session and str(job.get("status") or "") in {"running", "starting"}:
                if server.mode == "local":
                    run_command(["tmux", "send-keys", "-t", session, "C-c"], timeout=3)
                    deadline = time.monotonic() + 2.0
                    while time.monotonic() < deadline:
                        if run_command(["tmux", "has-session", "-t", session], timeout=1).returncode != 0:
                            break
                        time.sleep(0.2)
                    if run_command(["tmux", "has-session", "-t", session], timeout=1).returncode == 0:
                        run_command(["tmux", "kill-session", "-t", session], timeout=3)
                else:
                    quoted = shlex.quote(session)
                    remote_script = (
                        f"tmux send-keys -t {quoted} C-c 2>/dev/null || true; "
                        "for i in 1 2 3 4 5 6 7 8 9 10; do "
                        f"tmux has-session -t {quoted} 2>/dev/null || exit 0; "
                        "sleep 0.2; "
                        "done; "
                        f"tmux kill-session -t {quoted} 2>/dev/null || true"
                    )
                    ssh_command(
                        server,
                        "bash -lc " + shlex.quote(remote_script),
                        timeout=self.config.remote_timeout_seconds + 3,
                    )
        job["status"] = "stopped"
        job["finished_at"] = now_iso()
        self.save_jobs()
        self.sync_workspace_execution_runs_from_jobs()
        self.publish_job_log_delta(job, final=True)
        self.publish_job_event(job, "job.updated")
        return job


    def job_dependencies_state(self, job: dict[str, Any]) -> tuple[bool, str]:
        dependency_ids = [str(item).strip() for item in job.get("target_job_ids", []) if str(item).strip()]
        if not dependency_ids:
            return True, ""
        jobs_by_id = {str(item.get("id") or ""): item for item in self.jobs if str(item.get("id") or "").strip()}
        for dependency_id in dependency_ids:
            dependency = jobs_by_id.get(dependency_id)
            if not dependency:
                return False, f"waiting for dependency {dependency_id}"
            status = str(dependency.get("status") or "")
            if status in {"failed", "stopped"}:
                return False, f"dependency failed: {dependency_id}"
            if status != "done":
                return False, f"waiting for dependency {dependency_id}"
        return True, ""
