"""Auto-split from jobs.py — execution."""

from __future__ import annotations

from ._deps import *  # noqa: F403


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


    def start_job(self, job: dict[str, Any], allow_busy: bool = False) -> None:
        gpuless = str(job.get("gpu_index") or "").strip().lower() in {"none", "no_gpu", "cpu"}
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
            self.save_jobs()
            self.sync_workspace_execution_runs_from_jobs()
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
                self.save_jobs()
                self.sync_workspace_execution_runs_from_jobs()
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
        self.save_jobs()
        self.sync_workspace_execution_runs_from_jobs()
        self.publish_job_event(job, "job.updated")


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
        local_path = Path(str(job.get("log_path") or local_log_path(job["server_id"], job["id"])))
        if server.mode == "local":
            if not local_path.exists():
                return ""
            data = local_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(data[-lines:])
        remote_path = str(job.get("remote_log_path") or remote_log_path(job["id"]))
        result = ssh_command(
            server,
            f"tail -n {int(lines)} {remote_path} 2>/dev/null || true",
            timeout=self.config.remote_timeout_seconds,
        )
        if result.returncode == 0:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(result.stdout, encoding="utf-8")
            return result.stdout
        if local_path.exists():
            data = local_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(data[-lines:])
        return result.stderr.strip()


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
