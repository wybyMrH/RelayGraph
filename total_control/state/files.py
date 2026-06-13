from __future__ import annotations

from ._deps import *  # noqa: F403

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
        if not local_path.exists() or not local_path.is_file():
            raise ValueError("预览缓存文件不存在。")
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
