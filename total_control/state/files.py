from __future__ import annotations

from ._deps import *  # noqa: F403


def _runtime_state_run_job_ids(run: dict[str, Any]) -> set[str]:
    return set(workspace_run_job_ids(run))


def _runtime_state_workspace_run_closure(
    workspace: dict[str, Any],
    root_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    workspace_id = str(workspace.get("id") or "").strip()
    runs = [run for run in (workspace.get("runs") if isinstance(workspace.get("runs"), list) else []) if isinstance(run, dict)]
    workspace_payload = {**workspace, "runs": runs}
    closure: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root_run in root_runs:
        if not isinstance(root_run, dict):
            continue
        source_runs = [root_run, *workspace_execution_run_linked_runs(workspace_payload, root_run, max_runs=64)]
        for run in source_runs:
            run_id = str(run.get("id") or "").strip()
            if not run_id or run_id in seen:
                continue
            run_workspace_id = str(run.get("workspace_id") or workspace_id).strip()
            if workspace_id and run_workspace_id and run_workspace_id != workspace_id:
                continue
            seen.add(run_id)
            closure.append(run)
    return closure


def _merge_runtime_log_path_payloads(*payloads: dict[str, Any]) -> dict[str, Any]:
    local: list[str] = []
    local_seen: set[str] = set()
    remote_by_server: dict[str, list[str]] = {}
    remote_seen: set[tuple[str, str]] = set()
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for path in payload.get("local") if isinstance(payload.get("local"), list) else []:
            text = str(path or "").strip()
            if text and text not in local_seen:
                local_seen.add(text)
                local.append(text)
        remote_payload = payload.get("remote_by_server") if isinstance(payload.get("remote_by_server"), dict) else {}
        for server_id, paths in remote_payload.items():
            server_text = str(server_id or "").strip()
            if not server_text:
                continue
            for path in paths if isinstance(paths, list) else []:
                path_text = str(path or "").strip()
                key = (server_text, path_text)
                if not path_text or key in remote_seen:
                    continue
                remote_seen.add(key)
                remote_by_server.setdefault(server_text, []).append(path_text)
    return {"local": local, "remote_by_server": remote_by_server}

class FilesMixin:
    def browse_files(
        self,
        server_id: str | None,
        path_text: str = "",
        max_entries: int = 300,
        dirs_only: bool = False,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        if not server or server.mode == "local":
            return browse_local_files(path_text, max_entries=max_entries, dirs_only=dirs_only)
        return browse_remote_files(
            server,
            path_text=path_text,
            max_entries=max_entries,
            dirs_only=dirs_only,
            timeout=self.config.remote_timeout_seconds + 4,
        )


    def read_file_text(
        self,
        server_id: str | None,
        path_text: str = "",
        limit_bytes: int = 131072,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        if not server or server.mode == "local":
            payload = read_local_text_file(path_text, limit_bytes=limit_bytes)
            if server:
                payload["server_id"] = server.id
            return payload
        return read_remote_text_file(
            server,
            path_text=path_text,
            limit_bytes=limit_bytes,
            timeout=self.config.remote_timeout_seconds + 4,
        )


    def ensure_file_preview_cache(self) -> dict[str, dict[str, Any]]:
        cache = getattr(self, "file_preview_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self.file_preview_cache = cache
        FILE_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return cache


    def register_file_preview(
        self,
        *,
        source_path: str,
        local_path: Path,
        server_id: str,
        mime_type: str,
        preview_kind: str,
        cached: bool,
    ) -> dict[str, Any]:
        cache = self.ensure_file_preview_cache()
        cache_id = uuid.uuid4().hex
        entry = {
            "cache_id": cache_id,
            "source_path": source_path,
            "local_path": str(local_path),
            "server_id": server_id or "local",
            "mime_type": mime_type,
            "preview_kind": preview_kind,
            "cached": bool(cached),
            "created_at": now_iso(),
        }
        with self.lock:
            cache[cache_id] = entry
        return entry


    def file_preview_entry(self, cache_id: str) -> dict[str, Any]:
        cache = self.ensure_file_preview_cache()
        with self.lock:
            entry = copy.deepcopy(cache.get(str(cache_id or "").strip()) or {})
        if not entry:
            raise ValueError("预览缓存不存在或已失效。")
        local_path = Path(str(entry.get("local_path") or "")).expanduser()
        if file_browser_path_block_reason(entry.get("source_path"), local_path):
            raise ValueError("预览缓存指向敏感路径，已阻止打开。")
        try:
            if local_path.is_symlink():
                raise ValueError("预览缓存拒绝打开符号链接文件。")
        except OSError as exc:
            raise ValueError("预览缓存文件不可访问。") from exc
        if not local_path.exists() or not local_path.is_file():
            raise ValueError("预览缓存文件不存在。")
        if entry.get("cached") and not is_under_preview_cache(local_path):
            raise ValueError("预览缓存文件路径不在受控缓存目录内。")
        if not entry.get("cached") and not file_browser_allowed(local_path):
            raise ValueError("预览文件不在允许的本机浏览范围内。")
        entry["local_path"] = str(local_path.resolve())
        return entry


    def prune_preview_cache_index(self) -> int:
        removed = 0
        with self.lock:
            stale_ids = []
            for cache_id, entry in self.file_preview_cache.items():
                if not entry.get("cached"):
                    continue
                local_path = Path(str(entry.get("local_path") or ""))
                if not local_path.exists() or not is_under_preview_cache(local_path):
                    stale_ids.append(cache_id)
            for cache_id in stale_ids:
                self.file_preview_cache.pop(cache_id, None)
                removed += 1
        return removed


    def preview_cache_status(self) -> dict[str, Any]:
        stats = preview_cache_disk_stats()
        with self.lock:
            memory_cached = sum(1 for entry in self.file_preview_cache.values() if entry.get("cached"))
        settings = load_preview_cache_settings()
        return {
            **stats,
            "settings": settings,
            "memory_cached_entries": memory_cached,
        }


    def update_preview_cache_settings(self, body: dict[str, Any]) -> dict[str, Any]:
        settings = save_preview_cache_settings(body or {})
        runtime_settings = load_runtime_storage_settings()
        runtime_settings["preview_max_age_hours"] = settings["max_age_hours"]
        runtime_settings["preview_max_size_mib"] = settings["max_size_mib"]
        save_runtime_storage_settings(runtime_settings)
        return {"settings": settings, **self.preview_cache_status()}


    def cleanup_preview_cache_manual(self) -> dict[str, Any]:
        result = cleanup_preview_cache(remove_all=True)
        self.prune_preview_cache_index()
        return {**result, **self.preview_cache_status()}


    def maybe_auto_cleanup_preview_cache(self, *, force: bool = False) -> dict[str, Any] | None:
        settings = load_preview_cache_settings()
        max_age_hours = int(settings.get("max_age_hours") or 0)
        max_size_mib = int(settings.get("max_size_mib") or 0)
        if max_age_hours <= 0 and max_size_mib <= 0:
            return None
        now = time.time()
        if not force and now - float(getattr(self, "last_preview_cache_cleanup", 0.0) or 0.0) < 300:
            return None
        self.last_preview_cache_cleanup = now
        result = cleanup_preview_cache(max_age_hours=max_age_hours, max_size_mib=max_size_mib)
        self.prune_preview_cache_index()
        return result


    def runtime_storage_status(self, *, include_remote: bool = True) -> dict[str, Any]:
        settings = load_runtime_storage_settings()
        preview = self.preview_cache_status()
        logs = local_runtime_log_stats()
        return {
            "settings": settings,
            "paths": {
                "local_logs": "data/logs",
                "remote_logs": "$HOME/.total_control/logs",
                "preview_cache": preview.get("cache_dir") or str(FILE_PREVIEW_CACHE_DIR),
            },
            "preview_cache": preview,
            "local_logs": logs,
            "remote_logs": self.remote_runtime_log_statuses() if include_remote else [],
        }


    def runtime_state_status(self) -> dict[str, Any]:
        terminal_statuses = {"done", "failed", "stopped"}
        active_statuses = {"queued", "starting", "running", "blocked"}
        with self.lock:
            jobs = [copy.deepcopy(job) for job in getattr(self, "jobs", []) if isinstance(job, dict)]
            workspaces = [
                {
                    "id": str(workspace.get("id") or "").strip(),
                    "name": str(workspace.get("name") or workspace.get("title") or "").strip(),
                    "runs": copy.deepcopy(workspace.get("runs")) if isinstance(workspace.get("runs"), list) else [],
                }
                for workspace in getattr(self, "workspaces", [])
                if isinstance(workspace, dict)
            ]
        status_counts: dict[str, int] = {}
        for job in jobs:
            status = str(job.get("status") or "unknown").strip() or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
        workspace_items: list[dict[str, Any]] = []
        total_runs = 0
        total_events = 0
        active_runs = 0
        for workspace in workspaces:
            runs = [run for run in workspace["runs"] if isinstance(run, dict)]
            run_events = sum(
                len(run.get("events")) for run in runs if isinstance(run.get("events"), list)
            )
            active_count = sum(1 for run in runs if str(run.get("status") or "") in active_statuses)
            total_runs += len(runs)
            total_events += run_events
            active_runs += active_count
            workspace_items.append(
                {
                    "workspace_id": workspace["id"],
                    "name": workspace["name"],
                    "run_count": len(runs),
                    "active_run_count": active_count,
                    "event_count": run_events,
                }
            )
        workspace_items.sort(key=lambda item: (int(item.get("run_count") or 0), str(item.get("name") or "")), reverse=True)
        completed_jobs = sum(1 for job in jobs if str(job.get("status") or "") in terminal_statuses)
        return {
            "jobs": {
                "total": len(jobs),
                "active": sum(1 for job in jobs if str(job.get("status") or "") in active_statuses),
                "completed": completed_jobs,
                "status_counts": status_counts,
                "deletable_statuses": sorted(terminal_statuses),
            },
            "workspaces": {
                "total": len(workspaces),
                "total_runs": total_runs,
                "active_runs": active_runs,
                "total_events": total_events,
                "items": workspace_items[:20],
            },
            "cleanup_defaults": {
                "clear_completed_jobs": True,
                "prune_workspace_runs": True,
                "max_runs_per_workspace": 20,
            },
        }


    def cleanup_runtime_state_manual(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = body if isinstance(body, dict) else {}
        clear_jobs = bool(data.get("clear_completed_jobs", True))
        prune_runs = bool(data.get("prune_workspace_runs", True))
        dry_run = bool(data.get("dry_run", False))
        max_runs = max(1, min(safe_int(data.get("max_runs_per_workspace"), 20), 200))
        requested_statuses = data.get("statuses")
        if isinstance(requested_statuses, list) and requested_statuses:
            deletable_statuses = {
                str(item or "").strip()
                for item in requested_statuses
                if str(item or "").strip() in {"done", "failed", "stopped"}
            }
        else:
            deletable_statuses = {"done", "failed", "stopped"}
        active_statuses = {"queued", "starting", "running", "blocked"}
        removed_jobs = 0
        preserved_jobs = 0
        removed_runs = 0
        removed_events = 0
        changed_jobs = False
        changed_workspaces = False

        with self.lock:
            protected_job_ids: set[str] = set()
            planned_run_prunes: list[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]] = []
            for workspace in getattr(self, "workspaces", []):
                if not isinstance(workspace, dict) or not isinstance(workspace.get("runs"), list):
                    continue
                runs = [
                    normalize_workspace_execution_run(run, existing=run)
                    for run in workspace.get("runs", [])
                    if isinstance(run, dict)
                ]
                runs.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
                kept: list[dict[str, Any]] = []
                removed: list[dict[str, Any]] = []
                for run in runs:
                    if not prune_runs:
                        kept.append(run)
                        continue
                    if str(run.get("status") or "") in active_statuses:
                        kept.append(run)
                        continue
                    if len(kept) < max_runs:
                        kept.append(run)
                        continue
                    removed.append(run)
                workspace_for_closure = {**workspace, "runs": runs}
                closure_runs = _runtime_state_workspace_run_closure(workspace_for_closure, kept)
                closure_by_id = {
                    str(run.get("id") or "").strip(): run
                    for run in closure_runs
                    if isinstance(run, dict) and str(run.get("id") or "").strip()
                }
                kept_by_id = {
                    str(run.get("id") or "").strip()
                    for run in kept
                    if isinstance(run, dict) and str(run.get("id") or "").strip()
                }
                next_removed: list[dict[str, Any]] = []
                for run in removed:
                    run_id = str(run.get("id") or "").strip()
                    if run_id and run_id in closure_by_id:
                        if run_id not in kept_by_id:
                            kept.append(closure_by_id[run_id])
                            kept_by_id.add(run_id)
                        continue
                    next_removed.append(run)
                removed = next_removed
                planned_run_prunes.append((workspace, kept, removed))
                for run in _runtime_state_workspace_run_closure(workspace_for_closure, kept):
                    protected_job_ids.update(_runtime_state_run_job_ids(run))

            if clear_jobs:
                remaining_jobs = []
                for job in getattr(self, "jobs", []):
                    if not isinstance(job, dict):
                        remaining_jobs.append(job)
                        continue
                    if str(job.get("status") or "") in deletable_statuses:
                        job_id = str(job.get("id") or "").strip()
                        if job_id and job_id in protected_job_ids:
                            preserved_jobs += 1
                            remaining_jobs.append(job)
                            continue
                        removed_jobs += 1
                        if dry_run:
                            remaining_jobs.append(job)
                        continue
                    remaining_jobs.append(job)
                if not dry_run and removed_jobs:
                    self.jobs = remaining_jobs
                    changed_jobs = True

            if prune_runs:
                for workspace, kept, removed in planned_run_prunes:
                    if not removed:
                        continue
                    removed_runs += len(removed)
                    removed_events += sum(
                        len(run.get("events")) for run in removed if isinstance(run.get("events"), list)
                    )
                    if not dry_run:
                        workspace["runs"] = normalize_workspace_execution_runs(kept, limit=max(len(kept), 1))
                        changed_workspaces = True

            if changed_jobs:
                self.save_jobs()
            if changed_workspaces:
                self.save_workspaces()

        return {
            "dry_run": dry_run,
            "removed_jobs": removed_jobs,
            "preserved_jobs": preserved_jobs,
            "removed_runs": removed_runs,
            "removed_events": removed_events,
            "max_runs_per_workspace": max_runs,
            "status": self.runtime_state_status(),
        }


    def retained_workspace_run_job_ids(self) -> set[str]:
        job_ids: set[str] = set()
        with self.lock:
            workspaces = copy.deepcopy(getattr(self, "workspaces", []))
        for workspace in workspaces:
            if not isinstance(workspace, dict):
                continue
            runs = workspace.get("runs") if isinstance(workspace.get("runs"), list) else []
            for run in _runtime_state_workspace_run_closure({**workspace, "runs": runs}, runs):
                if isinstance(run, dict):
                    job_ids.update(_runtime_state_run_job_ids(run))
        return job_ids


    def snapshot_retained_run_job_log_tails(
        self,
        *,
        max_lines: int = 80,
        max_bytes: int = 24000,
        tail_chars: int = 12000,
    ) -> dict[str, Any]:
        retained_job_ids = self.retained_workspace_run_job_ids()
        if not retained_job_ids:
            return {"captured_count": 0, "job_ids": []}
        with self.lock:
            retained_jobs = [
                copy.deepcopy(job)
                for job in getattr(self, "jobs", [])
                if isinstance(job, dict)
                and str(job.get("id") or "").strip()
                and str(job.get("id") or "").strip() in retained_job_ids
            ]

        def snapshot_payload_from_log_tail(
            job: dict[str, Any],
            payload: dict[str, Any],
            *,
            source: str,
        ) -> dict[str, Any]:
            tail = str(payload.get("tail") or "").strip("\n")
            if not tail:
                return {}
            display_log_path = str(payload.get("display_log_path") or "").strip()
            if not display_log_path:
                display_log_path = runtime_log_display_path(payload.get("log_path") or job.get("log_path"))
            return {
                "schema": "relaygraph.job.log_tail_snapshot.v1",
                "captured_at": now_iso(),
                "source": source,
                "line_count": len(tail.splitlines()),
                "file_size": safe_int(payload.get("file_size"), 0),
                "read_bytes": safe_int(payload.get("read_bytes"), safe_int(payload.get("byte_count"), 0)),
                "tail_bytes": safe_int(payload.get("tail_bytes"), len(tail.encode("utf-8", errors="replace"))),
                "skipped_bytes": safe_int(payload.get("skipped_bytes"), 0),
                "truncated": bool(payload.get("truncated")),
                "truncation_reasons": [
                    str(item or "").strip()
                    for item in payload.get("truncation_reasons", [])
                    if str(item or "").strip()
                ],
                "display_log_path": display_log_path,
                "remote_log_path": remote_runtime_log_display_path(payload.get("remote_log_path") or job.get("remote_log_path")),
                "tail": tail,
            }

        def read_local_tail_payload(job: dict[str, Any]) -> dict[str, Any]:
            payload = workspace_job_cached_log_tail_payload(
                job,
                max_lines=max_lines,
                max_bytes=max_bytes,
                tail_chars=tail_chars,
            )
            if str(payload.get("tail_source") or "") != "file":
                return {}
            return payload

        def read_remote_tail_payload(job: dict[str, Any]) -> dict[str, Any]:
            if not str(job.get("remote_log_path") or "").strip():
                return {}
            reader = getattr(self, "_remote_job_log_chunk", None)
            if not callable(reader):
                return {}
            try:
                chunk = reader(job, offset=0, max_bytes=max_bytes)
            except Exception:  # noqa: BLE001 - cleanup must not be blocked by one remote log.
                return {}
            if chunk.get("error"):
                return {}
            text = str(chunk.get("log") or "")
            if not text:
                return {}
            line_limited = "\n".join(text.splitlines()[-max(1, int(max_lines or 1)):])
            reasons = []
            if bool(chunk.get("truncated")) or safe_int(chunk.get("skipped_bytes"), 0) > 0:
                reasons.append("byte_window")
            if len(text.splitlines()) > max(1, int(max_lines or 1)):
                reasons.append("line_limit")
            if tail_chars > 0 and len(line_limited) > tail_chars:
                line_limited = line_limited[-tail_chars:]
                reasons.append("tail_char_limit")
            return {
                "tail": line_limited,
                "tail_source": "remote",
                "file_size": safe_int(chunk.get("file_size"), safe_int(chunk.get("next_offset"), 0)),
                "read_bytes": safe_int(chunk.get("byte_count"), len(text.encode("utf-8", errors="replace"))),
                "tail_bytes": len(line_limited.encode("utf-8", errors="replace")),
                "skipped_bytes": safe_int(chunk.get("skipped_bytes"), 0),
                "truncated": bool(chunk.get("truncated")) or bool(reasons),
                "truncation_reasons": list(dict.fromkeys(reasons)),
                "remote_log_path": remote_runtime_log_display_path(job.get("remote_log_path")),
            }

        snapshots_by_id: dict[str, dict[str, Any]] = {}
        for job in retained_jobs:
            job_id = str(job.get("id") or "").strip()
            if not job_id:
                continue
            local_payload = read_local_tail_payload(job)
            snapshot = snapshot_payload_from_log_tail(job, local_payload, source="runtime_log_cache")
            if not snapshot:
                remote_payload = read_remote_tail_payload(job)
                snapshot = snapshot_payload_from_log_tail(job, remote_payload, source="remote_runtime_log")
            if not snapshot:
                continue
            snapshots_by_id[job_id] = snapshot
        if not snapshots_by_id:
            return {"captured_count": 0, "job_ids": []}
        captured_ids: list[str] = []
        changed = False
        with self.lock:
            for job in getattr(self, "jobs", []):
                if not isinstance(job, dict):
                    continue
                job_id = str(job.get("id") or "").strip()
                if not job_id or job_id not in retained_job_ids:
                    continue
                next_snapshot = snapshots_by_id.get(job_id)
                if not next_snapshot:
                    continue
                metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
                snapshot = metadata.get("log_tail_snapshot") if isinstance(metadata.get("log_tail_snapshot"), dict) else {}
                comparable = {key: value for key, value in next_snapshot.items() if key != "captured_at"}
                existing_comparable = {key: snapshot.get(key) for key in comparable}
                if existing_comparable == comparable:
                    continue
                metadata["log_tail_snapshot"] = next_snapshot
                job["metadata"] = metadata
                captured_ids.append(job_id)
                changed = True
            if changed:
                self.save_jobs()
        return {"captured_count": len(captured_ids), "job_ids": captured_ids[:24]}


    def update_runtime_storage_settings(self, body: dict[str, Any]) -> dict[str, Any]:
        settings = save_runtime_storage_settings(body or {})
        return {**self.runtime_storage_status(), "settings": settings}


    def active_runtime_log_paths(self) -> dict[str, Any]:
        active_statuses = {"queued", "starting", "running", "blocked"}
        with self.lock:
            jobs = [
                copy.deepcopy(job)
                for job in getattr(self, "jobs", [])
                if str(job.get("status") or "") in active_statuses
            ]
        local_paths: list[str] = []
        remote_by_server: dict[str, list[str]] = {}
        for job in jobs:
            log_path = str(job.get("log_path") or "").strip()
            if log_path:
                local_paths.append(log_path)
            remote_path = str(job.get("remote_log_path") or "").strip()
            server_id = str(job.get("server_id") or "").strip()
            if remote_path and server_id:
                remote_by_server.setdefault(server_id, []).append(remote_path)
        return {"local": local_paths, "remote_by_server": remote_by_server}


    def retained_runtime_log_paths(self) -> dict[str, Any]:
        retained_job_ids = self.retained_workspace_run_job_ids()
        if not retained_job_ids:
            return {"local": [], "remote_by_server": {}}
        with self.lock:
            jobs = [
                copy.deepcopy(job)
                for job in getattr(self, "jobs", [])
                if isinstance(job, dict)
                and str(job.get("id") or "").strip()
                and str(job.get("id") or "").strip() in retained_job_ids
            ]
        local_paths: list[str] = []
        remote_by_server: dict[str, list[str]] = {}
        for job in jobs:
            log_path = str(job.get("log_path") or "").strip()
            if log_path:
                local_paths.append(log_path)
            remote_path = str(job.get("remote_log_path") or "").strip()
            server_id = str(job.get("server_id") or "").strip()
            if remote_path and server_id:
                remote_by_server.setdefault(server_id, []).append(remote_path)
        return {"local": local_paths, "remote_by_server": remote_by_server}


    def protected_runtime_log_paths(self) -> dict[str, Any]:
        return _merge_runtime_log_path_payloads(
            self.active_runtime_log_paths(),
            self.retained_runtime_log_paths(),
        )


    def reset_runtime_storage(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = reset_runtime_storage_settings()
        payload: dict[str, Any] = {"settings": settings, **self.runtime_storage_status()}
        if isinstance(body, dict) and body.get("cleanup"):
            payload["cleanup"] = self.cleanup_runtime_storage_manual(
                {
                    "include_preview": True,
                    "include_logs": True,
                    "include_remote": bool(body.get("include_remote", True)),
                    "remove_all": True,
                }
            )
        return payload


    def remote_runtime_log_statuses(
        self,
        *,
        cleanup: bool = False,
        max_age_hours: int = 0,
        max_file_mib: int = 0,
        max_size_mib: int = 0,
        remove_all: bool = False,
        preserve_paths_by_server: dict[str, list[str]] | None = None,
        remove_paths_by_server: dict[str, list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        with self.lock:
            servers = [copy.deepcopy(server) for server in self.servers if server.mode != "local" and server.enabled]
            statuses_by_id = {
                str(status.get("id") or ""): copy.deepcopy(status)
                for status in self.statuses
                if isinstance(status, dict)
            }
            timeout = min(max(int(self.config.remote_timeout_seconds or 4) + 2, 4), 10)
        results: list[dict[str, Any]] = []
        for server in servers:
            cached = statuses_by_id.get(server.id) or {}
            if not cached:
                results.append(
                    {
                        "server_id": server.id,
                        "server_name": server.name,
                        "log_dir": "$HOME/.total_control/logs",
                        "error": "等待监控快照，未读取远程日志",
                        "skipped": True,
                    }
                )
                continue
            if cached and not cached.get("reachable") and not cached.get("online"):
                results.append(
                    {
                        "server_id": server.id,
                        "server_name": server.name,
                        "log_dir": "$HOME/.total_control/logs",
                        "error": runtime_storage_error_summary(cached.get("error") or "server unreachable"),
                        "skipped": True,
                    }
                )
                continue
            try:
                results.append(
                    remote_runtime_log_payload(
                        server,
                        timeout=timeout,
                        cleanup=cleanup,
                        max_age_hours=max_age_hours,
                        max_file_mib=max_file_mib,
                        max_size_mib=max_size_mib,
                        remove_all=remove_all,
                        preserve_paths=(preserve_paths_by_server or {}).get(server.id, []),
                        remove_paths=(remove_paths_by_server or {}).get(server.id, []),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one remote host should not block maintenance UI.
                results.append(
                    {
                        "server_id": server.id,
                        "server_name": server.name,
                        "log_dir": "$HOME/.total_control/logs",
                        "error": runtime_storage_error_summary(exc),
                    }
                )
        return results


    def cleanup_runtime_storage_manual(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = body if isinstance(body, dict) else {}
        include_preview = bool(data.get("include_preview", True))
        include_logs = bool(data.get("include_logs", True))
        include_remote = bool(data.get("include_remote", True))
        remove_all = bool(data.get("remove_all", False))
        remove_log_paths = data.get("remove_log_paths") if isinstance(data.get("remove_log_paths"), dict) else {}
        remove_local_paths = [
            str(item or "").strip()
            for item in (remove_log_paths.get("local") if isinstance(remove_log_paths.get("local"), list) else [])
            if str(item or "").strip()
        ]
        remove_remote_paths_by_server = {
            str(server_id or "").strip(): [
                str(item or "").strip()
                for item in (paths if isinstance(paths, list) else [])
                if str(item or "").strip()
            ]
            for server_id, paths in (remove_log_paths.get("remote_by_server") if isinstance(remove_log_paths.get("remote_by_server"), dict) else {}).items()
            if str(server_id or "").strip()
        }
        settings = normalize_runtime_storage_settings({**load_runtime_storage_settings(), **data})
        log_file_mib = int(settings.get("log_max_file_mib") or 0)
        protected = self.protected_runtime_log_paths()
        result: dict[str, Any] = {
            "preview_cache": None,
            "local_logs": None,
            "remote_logs": [],
            "log_tail_snapshots": None,
        }
        if include_preview:
            result["preview_cache"] = cleanup_preview_cache(
                max_age_hours=0 if remove_all else int(settings.get("preview_max_age_hours") or 0),
                max_size_mib=0 if remove_all else int(settings.get("preview_max_size_mib") or 0),
                remove_all=remove_all,
            )
            self.prune_preview_cache_index()
        if include_logs:
            result["log_tail_snapshots"] = self.snapshot_retained_run_job_log_tails()
            result["local_logs"] = cleanup_runtime_logs(
                max_age_hours=0 if remove_all else int(settings.get("log_max_age_hours") or 0),
                max_file_mib=0 if remove_all else log_file_mib,
                max_size_mib=0 if remove_all else int(settings.get("log_max_size_mib") or 0),
                remove_all=remove_all,
                preserve_paths=protected.get("local") if isinstance(protected, dict) else [],
                remove_paths=remove_local_paths,
            )
            if include_remote:
                result["remote_logs"] = self.remote_runtime_log_statuses(
                    cleanup=True,
                    max_age_hours=0 if remove_all else int(settings.get("log_max_age_hours") or 0),
                    max_file_mib=0 if remove_all else log_file_mib,
                    max_size_mib=0 if remove_all else int(settings.get("log_max_size_mib") or 0),
                    remove_all=remove_all,
                    preserve_paths_by_server=(
                        protected.get("remote_by_server") if isinstance(protected, dict) else {}
                    ),
                    remove_paths_by_server=remove_remote_paths_by_server,
                )
        result["status"] = self.runtime_storage_status(include_remote=include_remote)
        return result


    def maybe_auto_cleanup_runtime_storage(self, *, force: bool = False) -> dict[str, Any] | None:
        settings = load_runtime_storage_settings()
        preview_age = int(settings.get("preview_max_age_hours") or 0)
        preview_size = int(settings.get("preview_max_size_mib") or 0)
        log_age = int(settings.get("log_max_age_hours") or 0)
        log_file_size = int(settings.get("log_max_file_mib") or 0)
        log_size = int(settings.get("log_max_size_mib") or 0)
        if preview_age <= 0 and preview_size <= 0 and log_age <= 0 and log_file_size <= 0 and log_size <= 0:
            return None
        now = time.time()
        interval = max(300, int(settings.get("auto_cleanup_interval_minutes") or 60) * 60)
        if not force and now - float(getattr(self, "last_runtime_storage_cleanup", 0.0) or 0.0) < interval:
            return None
        self.last_runtime_storage_cleanup = now
        protected = self.protected_runtime_log_paths()
        log_tail_snapshots = self.snapshot_retained_run_job_log_tails()
        result: dict[str, Any] = {
            "preview_cache": cleanup_preview_cache(
                max_age_hours=preview_age,
                max_size_mib=preview_size,
            ),
            "local_logs": cleanup_runtime_logs(
                max_age_hours=log_age,
                max_file_mib=log_file_size,
                max_size_mib=log_size,
                preserve_paths=protected.get("local") if isinstance(protected, dict) else [],
            ),
            "remote_logs": [],
            "log_tail_snapshots": log_tail_snapshots,
        }
        self.prune_preview_cache_index()
        if settings.get("remote_log_cleanup_enabled") and (log_age > 0 or log_file_size > 0 or log_size > 0):
            result["remote_logs"] = self.remote_runtime_log_statuses(
                cleanup=True,
                max_age_hours=log_age,
                max_file_mib=log_file_size,
                max_size_mib=log_size,
                preserve_paths_by_server=(
                    protected.get("remote_by_server") if isinstance(protected, dict) else {}
                ),
            )
        return result


    def fetch_file_preview(
        self,
        server_id: str | None,
        path_text: str = "",
        limit_bytes: int = 131072,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        source_path = str(path_text or "").strip()
        if not source_path:
            raise ValueError("请选择要预览的文件。")
        if not server or server.mode == "local":
            local_path = resolve_local_browser_target(source_path)
            if local_path.is_dir():
                raise ValueError("当前路径是目录，请选择文件。")
            resolved_server_id = server.id if server else "local"
            cached = False
        else:
            cache_dir = FILE_PREVIEW_CACHE_DIR / uuid.uuid4().hex
            local_path = download_remote_file_to_local(
                server,
                source_path,
                cache_dir,
                timeout=max(30, self.config.remote_timeout_seconds + 30),
            )
            if file_browser_path_block_reason(source_path, local_path):
                raise ValueError("预览缓存指向敏感路径，已阻止打开。")
            if local_path.is_symlink():
                raise ValueError("预览缓存拒绝打开符号链接文件。")
            if not is_under_preview_cache(local_path):
                raise ValueError("预览缓存文件路径不在受控缓存目录内。")
            if local_path.is_dir():
                raise ValueError("当前路径是目录，请选择文件。")
            resolved_server_id = server.id
            cached = True
        mime_type = guess_file_mime_type(str(local_path))
        preview_kind = preview_kind_for_path(str(local_path), mime_type)
        registered = self.register_file_preview(
            source_path=source_path,
            local_path=local_path.resolve(),
            server_id=resolved_server_id,
            mime_type=mime_type,
            preview_kind=preview_kind,
            cached=cached,
        )
        file_info = file_entry(local_path.resolve())
        payload = {
            "cache_id": registered["cache_id"],
            "cached": cached,
            "created_at": registered["created_at"],
            "download_url": f"/api/files/cache/{registered['cache_id']}?download=1",
            "inline_supported": preview_kind in {"text", "image", "pdf", "audio", "video"},
            "local_path": str(local_path.resolve()),
            "mime_type": mime_type,
            "name": file_info["name"],
            "path": source_path,
            "preview_kind": preview_kind,
            "preview_url": f"/api/files/cache/{registered['cache_id']}",
            "server_id": resolved_server_id,
            "size": file_info["size"],
            "size_text": file_info["size_text"],
            "mtime": file_info["mtime"],
        }
        if preview_kind == "text":
            text_payload = read_local_text_file(str(local_path.resolve()), limit_bytes=limit_bytes)
            payload["text"] = text_payload["text"]
            payload["encoding"] = text_payload["encoding"]
            payload["truncated"] = bool(text_payload["truncated"])
        if cached:
            self.maybe_auto_cleanup_preview_cache()
        return payload
