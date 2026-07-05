from __future__ import annotations

from ._deps import *  # noqa: F403

class ServersMixin:
    def list_servers_admin(self) -> dict[str, Any]:
        overlay = load_user_overlay(self.config_path)
        discovery_config = dict(overlay.get("ssh_discovery", {}) or {})
        discovery_path = str(discovery_config.get("config_path") or "~/.ssh/config")
        user_ids = {str(item.get("id") or "") for item in overlay["servers"]}
        with self.lock:
            servers = [
                {
                    "id": server.id,
                    "name": server.name,
                    "mode": server.mode,
                    "ssh_alias": server.ssh_alias,
                    "host_name": server.host_name,
                    "user": server.user,
                    "port": server.port,
                    "labels": server.labels,
                    "is_user": server.id in user_ids,
                    "source": "user_servers.toml" if server.id in user_ids else discovery_path,
                }
                for server in self.servers
            ]
        return {
            "servers": servers,
            "aliases": overlay["server_aliases"],
            "disabled_discovery": overlay["disabled_discovery"],
            "discovery_config_path": discovery_path,
        }


    def set_server_alias(self, server_id: str, alias: str) -> None:
        server_id = str(server_id or "").strip()
        alias = str(alias or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        # Use the most distinctive available key so it survives id/discovery changes.
        keys = [server.ssh_alias, server_id, server.host_name]
        if server.user and server.host_name:
            keys.append(f"{server.user}@{server.host_name}")
        keys = [key for key in keys if key]
        primary_key = keys[0] if keys else server_id

        overlay = load_user_overlay(self.config_path)
        if alias:
            overlay["server_aliases"][primary_key] = alias
        else:
            for key in keys:
                overlay["server_aliases"].pop(key, None)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()


    def add_server(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = str(payload.get("mode") or "ssh").strip().lower()
        if mode not in ("ssh", "local"):
            raise ValueError("mode must be ssh or local")
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        entry: dict[str, Any] = {"name": name, "mode": mode, "enabled": True}
        if mode == "local":
            entry["id"] = safe_id(payload.get("id") or name or "local")
        else:
            host_name = str(payload.get("host_name") or "").strip()
            ssh_alias = str(payload.get("ssh_alias") or "").strip()
            if not host_name and not ssh_alias:
                raise ValueError("ssh server requires host_name or ssh_alias")
            entry["id"] = safe_id(payload.get("id") or ssh_alias or host_name or name)
            if host_name:
                entry["host_name"] = host_name
            if ssh_alias:
                entry["ssh_alias"] = ssh_alias
            user = str(payload.get("user") or "").strip()
            if user:
                entry["user"] = user
            port = str(payload.get("port") or "").strip()
            if port:
                entry["port"] = port
            password = str(payload.get("password") or "").strip()
            if password:
                entry["password"] = password
            ssh_config_path = str(payload.get("ssh_config_path") or "").strip()
            if ssh_config_path:
                entry["ssh_config_path"] = ssh_config_path

        overlay = load_user_overlay(self.config_path)
        # If id collides with an existing user-server, replace it; otherwise append.
        existing = [
            index for index, item in enumerate(overlay["servers"])
            if str(item.get("id")) == entry["id"]
        ]
        if existing:
            overlay["servers"][existing[0]] = entry
        else:
            overlay["servers"].append(entry)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()
        return entry


    def update_server(self, server_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")

        overlay = load_user_overlay(self.config_path)
        match_index = None
        for i, item in enumerate(overlay["servers"]):
            if str(item.get("id") or "") == server_id:
                match_index = i
                break

        if match_index is not None:
            # User-defined server: update in place
            existing = overlay["servers"][match_index]
        else:
            # Discovered server: promote to user-defined entry
            server = self.server_by_id(server_id)
            if not server:
                raise ValueError("server not found")
            existing: dict[str, Any] = {"id": server.id, "name": server.name, "mode": server.mode, "enabled": True}
            if server.ssh_alias:
                existing["ssh_alias"] = server.ssh_alias
            if server.host_name:
                existing["host_name"] = server.host_name
            if server.user:
                existing["user"] = server.user
            if server.port:
                existing["port"] = server.port
            if server.password:
                existing["password"] = server.password
            if server.ssh_config_path:
                existing["ssh_config_path"] = server.ssh_config_path
            if server.labels:
                existing["labels"] = list(server.labels)

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        mode = str(payload.get("mode") or existing.get("mode") or "ssh").strip().lower()
        if mode not in ("ssh", "local"):
            raise ValueError("mode must be ssh or local")

        entry: dict[str, Any] = {"id": existing.get("id", server_id), "name": name, "mode": mode, "enabled": existing.get("enabled", True)}
        if mode == "ssh":
            host_name = str(payload.get("host_name") or "").strip()
            ssh_alias = str(payload.get("ssh_alias") or "").strip()
            if not host_name and not ssh_alias:
                host_name = str(existing.get("host_name") or "").strip()
                ssh_alias = str(existing.get("ssh_alias") or "").strip()
            if host_name:
                entry["host_name"] = host_name
            if ssh_alias:
                entry["ssh_alias"] = ssh_alias
            user = str(payload.get("user") or "").strip()
            if user:
                entry["user"] = user
            elif existing.get("user"):
                entry["user"] = existing["user"]
            port = str(payload.get("port") or "").strip()
            if port:
                entry["port"] = port
            elif existing.get("port"):
                entry["port"] = existing["port"]
            password = str(payload.get("password") or "").strip()
            if password:
                entry["password"] = password
            elif existing.get("password"):
                entry["password"] = existing["password"]
            ssh_config_path = str(payload.get("ssh_config_path") or "").strip()
            if ssh_config_path:
                entry["ssh_config_path"] = ssh_config_path
            elif existing.get("ssh_config_path"):
                entry["ssh_config_path"] = existing["ssh_config_path"]
        if existing.get("labels"):
            entry["labels"] = existing["labels"]

        if match_index is not None:
            overlay["servers"][match_index] = entry
        else:
            overlay["servers"].append(entry)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()
        return entry


    def remove_server(self, server_id: str) -> None:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        overlay = load_user_overlay(self.config_path)
        before = len(overlay["servers"])
        overlay["servers"] = [
            item for item in overlay["servers"] if safe_id(str(item.get("id") or "")) != server_id
        ]
        removed_user_entry = len(overlay["servers"]) != before
        if not removed_user_entry:
            # Treat as a discovery hide.
            server = self.server_by_id(server_id)
            target = server.ssh_alias if server and server.ssh_alias else server_id
            if target not in overlay["disabled_discovery"]:
                overlay["disabled_discovery"].append(target)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()


    def restore_discovery(self, alias: str) -> None:
        alias = str(alias or "").strip()
        if not alias:
            raise ValueError("alias is required")
        overlay = load_user_overlay(self.config_path)
        overlay["disabled_discovery"] = [item for item in overlay["disabled_discovery"] if item != alias]
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()


    def check_server(self, server_id: str) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        return run_server_checks(server, max(self.config.remote_timeout_seconds, 4))


    def cached_process_stop_context(self, server_id: str, pid: Any) -> dict[str, Any]:
        target_pid = safe_int(pid, 0)
        if target_pid <= 0:
            raise ValueError("invalid pid")
        with self.lock:
            status = next(
                (
                    copy.deepcopy(item)
                    for item in getattr(self, "statuses", [])
                    if str(item.get("id") or "") == str(server_id)
                ),
                {},
        )
        host_resources = status.get("host_resources") if isinstance(status.get("host_resources"), dict) else {}
        current_user = str(status.get("current_user") or host_resources.get("current_user") or "").strip()
        current_uid = str(status.get("current_uid") or host_resources.get("current_uid") or "").strip()
        process = next(
            (
                item
                for item in (status.get("processes") if isinstance(status.get("processes"), list) else [])
                if str(item.get("pid") or "") == str(target_pid)
            ),
            {},
        )
        process_exists = bool(process)
        owner_uid = str(process.get("uid") or "").strip() if isinstance(process, dict) else ""
        owner = str(process.get("user") or "").strip() if isinstance(process, dict) else ""
        command = str(process.get("command") or process.get("process_name") or "").strip() if isinstance(process, dict) else ""
        if not process_exists:
            confirmation_required = False
        elif current_uid and owner_uid:
            confirmation_required = current_uid != owner_uid
        elif current_user and owner:
            confirmation_required = owner != current_user
        else:
            confirmation_required = True
        reason = ""
        if confirmation_required:
            reason = "owner_unknown" if not current_user or not owner else "not_current_user"
        elif not process_exists:
            reason = "process_not_found"
        return {
            "server_id": server_id,
            "pid": target_pid,
            "current_user": current_user,
            "current_uid": current_uid,
            "owner": owner,
            "owner_uid": owner_uid,
            "command": command,
            "process_exists": process_exists,
            "confirmation_required": confirmation_required,
            "reason": reason,
            "source": "monitor_cache",
        }


    def realtime_process_stop_context(self, server: Any, pid: Any) -> dict[str, Any]:
        target_pid = safe_int(pid, 0)
        if target_pid <= 0:
            raise ValueError("invalid pid")
        script = r"""
import getpass
import json
import os
import pwd
import subprocess
import sys

pid = str(sys.argv[1])
payload = {
    "pid": int(pid),
    "current_uid": str(os.geteuid()),
    "current_user": "",
    "owner_uid": "",
    "owner": "",
    "command": "",
    "process_exists": False,
}
try:
    payload["current_user"] = pwd.getpwuid(os.geteuid()).pw_name
except Exception:
    payload["current_user"] = getpass.getuser()
try:
    result = subprocess.run(
        ["ps", "-o", "uid=,user:32=,pid=,command=", "-p", pid],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) >= 3 and parts[2] == pid:
            payload["owner_uid"] = parts[0]
            payload["owner"] = parts[1]
            payload["command"] = parts[3] if len(parts) > 3 else ""
            payload["process_exists"] = True
            break
except Exception as exc:
    payload["error"] = str(exc)
print(json.dumps(payload, ensure_ascii=False))
"""
        if server.mode == "local":
            result = run_command(["python3", "-c", script, str(target_pid)], timeout=5)
        else:
            result = ssh_command(
                server,
                "python3 -c " + shlex.quote(script) + " " + shlex.quote(str(target_pid)),
                timeout=min(max(self.config.remote_timeout_seconds + 2, 4), 12),
            )
        output = (result.stdout or "").strip()
        payload: dict[str, Any] = {}
        if result.returncode == 0 and output:
            try:
                parsed = json.loads(output.splitlines()[-1])
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = {}
        if not payload:
            fallback = self.cached_process_stop_context(server.id, target_pid)
            fallback["source"] = "monitor_cache_fallback"
            fallback["error"] = (result.stderr.strip() or result.stdout.strip() or "process owner check failed")[-500:]
            fallback["confirmation_required"] = True
            fallback["reason"] = "owner_check_failed"
            return fallback
        process_exists = bool(payload.get("process_exists"))
        current_uid = str(payload.get("current_uid") or "").strip()
        owner_uid = str(payload.get("owner_uid") or "").strip()
        current_user = str(payload.get("current_user") or "").strip()
        owner = str(payload.get("owner") or "").strip()
        if not process_exists:
            confirmation_required = False
            reason = "process_not_found"
        elif current_uid and owner_uid:
            confirmation_required = current_uid != owner_uid
            reason = "not_current_user" if confirmation_required else ""
        elif current_user and owner:
            confirmation_required = current_user != owner
            reason = "not_current_user" if confirmation_required else ""
        else:
            confirmation_required = True
            reason = "owner_unknown"
        return {
            "server_id": server.id,
            "pid": target_pid,
            "current_user": current_user,
            "current_uid": current_uid,
            "owner": owner,
            "owner_uid": owner_uid,
            "command": str(payload.get("command") or "").strip(),
            "process_exists": process_exists,
            "confirmation_required": confirmation_required,
            "reason": reason,
            "source": "realtime",
        }


    def process_stop_context(self, server_id: str, pid: Any, *, realtime: bool = False) -> dict[str, Any]:
        if not realtime:
            return self.cached_process_stop_context(server_id, pid)
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        return self.realtime_process_stop_context(server, pid)


    def stop_process(self, server_id: str, pid: Any, body: dict[str, Any] | None = None) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        target_pid = safe_int(pid, 0)
        if target_pid <= 0:
            raise ValueError("invalid pid")
        context = self.realtime_process_stop_context(server, target_pid)
        data = body if isinstance(body, dict) else {}
        if context["confirmation_required"] and not bool(data.get("confirm_non_owner")):
            raise PermissionError("关闭非当前用户或归属未知的进程前需要确认。")
        result = stop_server_process(
            server,
            target_pid,
            grace_seconds=10,
        )
        result["process_stop"] = context
        return result
