from __future__ import annotations

from typing import Any


def build_runtime_log_path_payload(jobs: list[dict[str, Any]]) -> dict[str, Any]:
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


def merge_runtime_log_path_payloads(*payloads: dict[str, Any]) -> dict[str, Any]:
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
