from __future__ import annotations

from typing import Any


def parse_runtime_storage_cleanup_request(body: dict[str, Any] | None) -> dict[str, Any]:
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
        for server_id, paths in (
            remove_log_paths.get("remote_by_server")
            if isinstance(remove_log_paths.get("remote_by_server"), dict)
            else {}
        ).items()
        if str(server_id or "").strip()
    }
    return {
        "data": data,
        "include_preview": include_preview,
        "include_logs": include_logs,
        "include_remote": include_remote,
        "remove_all": remove_all,
        "remove_local_paths": remove_local_paths,
        "remove_remote_paths_by_server": remove_remote_paths_by_server,
    }
