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


    def stop_process(self, server_id: str, pid: Any) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        target_pid = safe_int(pid, 0)
        if target_pid <= 0:
            raise ValueError("invalid pid")
        return stop_server_process(
            server,
            target_pid,
            grace_seconds=10,
        )
