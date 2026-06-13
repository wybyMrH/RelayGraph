"""Auto-split from jobs.py — paths."""

from __future__ import annotations

from ._deps import *  # noqa: F403


class PathsJobsMixin:
    def _format_remote_path(self, template: str, server: ServerConfig | None = None) -> str:
        user = (server.user if server else None) or "user"
        host = (server.host_name if server else None) or ""
        try:
            return template.format(user=user, host=host)
        except (KeyError, ValueError):
            return template


    def apply_server_paths(self, job: dict[str, Any], server: ServerConfig) -> None:
        if server.mode == "local":
            cwd = str(job.get("cwd_local") or job.get("cwd") or "").strip()
        else:
            cwd = str(job.get("cwd_remote") or job.get("cwd") or "").strip()
            cwd = self._format_remote_path(cwd, server)
        if cwd:
            job["cwd"] = cwd
