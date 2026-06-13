from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import DEFAULT_CONFIG  # noqa: F401
from .utils import safe_id, safe_int  # noqa: F401


@dataclass
class ServerConfig:
    id: str
    name: str
    mode: str = "local"
    enabled: bool = True
    labels: list[str] = field(default_factory=list)
    ssh_alias: str | None = None
    ssh_config_path: str | None = None
    host_name: str | None = None
    user: str | None = None
    port: str | None = None
    password: str | None = None

    def target_label(self) -> str:
        if self.mode == "local":
            return "local"
        if self.user and self.host_name:
            return f"{self.user}@{self.host_name}"
        return self.ssh_alias or self.host_name or self.id


@dataclass
class AppConfig:
    poll_interval_seconds: int = 5
    remote_timeout_seconds: int = 6
    idle_min_free_mib: int = 1024
    idle_max_gpu_util: int = 10
    servers: list[ServerConfig] = field(default_factory=list)


def load_secrets(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    passwords = raw.get("ssh_passwords", {})
    if not isinstance(passwords, dict):
        return {}
    return {str(key): str(value) for key, value in passwords.items() if str(value)}


def secret_password(secrets: dict[str, str], *, alias: str, server_id: str, host_name: str | None, user: str | None) -> str | None:
    keys = [alias, server_id]
    if host_name:
        keys.append(host_name)
    if user and host_name:
        keys.append(f"{user}@{host_name}")
    for key in keys:
        if key in secrets:
            return secrets[key]
    return None


def config_alias(aliases: dict[str, str], *, alias: str, server_id: str, host_name: str | None, user: str | None, fallback: str) -> str:
    keys = [alias, server_id]
    if host_name:
        keys.append(host_name)
    if user and host_name:
        keys.append(f"{user}@{host_name}")
    for key in keys:
        if key in aliases:
            return aliases[key]
    return fallback


def parse_ssh_config(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    hosts: list[dict[str, str]] = []
    active: list[dict[str, str]] = []

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        key, value = parts[0].lower(), parts[1].strip()
        if key == "host":
            active = []
            for pattern in value.split():
                if any(mark in pattern for mark in ("*", "?", "!")):
                    continue
                entry = {"host": pattern}
                hosts.append(entry)
                active.append(entry)
            continue
        for entry in active:
            entry[key] = value

    return hosts


def load_config(path: Path) -> AppConfig:
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))

    user_path = path.with_name("user_servers.toml")
    user_raw: dict[str, Any] = {}
    if user_path.exists():
        try:
            user_raw = tomllib.loads(user_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            user_raw = {}

    app = raw.get("app", {})
    aliases = {str(key): str(value) for key, value in raw.get("server_aliases", {}).items()}
    user_aliases = {str(key): str(value) for key, value in user_raw.get("server_aliases", {}).items()}
    aliases.update(user_aliases)
    user_disabled = {str(item) for item in user_raw.get("disabled_discovery", [])}
    secrets = load_secrets(path.with_name("secrets.toml"))
    config = AppConfig(
        poll_interval_seconds=safe_int(app.get("poll_interval_seconds"), 5),
        remote_timeout_seconds=safe_int(app.get("remote_timeout_seconds"), 6),
        idle_min_free_mib=safe_int(app.get("idle_min_free_mib"), 1024),
        idle_max_gpu_util=safe_int(app.get("idle_max_gpu_util"), 10),
    )

    seen: set[str] = set()
    server_items = list(raw.get("servers", [])) + list(user_raw.get("servers", []))
    for item in server_items:
        server_id = safe_id(str(item.get("id") or item.get("name") or "server"))
        if server_id in seen:
            continue
        seen.add(server_id)
        config.servers.append(
            ServerConfig(
                id=server_id,
                name=config_alias(
                    aliases,
                    alias=str(item.get("ssh_alias") or item.get("id") or item.get("name") or ""),
                    server_id=server_id,
                    host_name=item.get("host_name"),
                    user=item.get("user"),
                    fallback=str(item.get("name") or server_id),
                ),
                mode=str(item.get("mode") or "local"),
                enabled=bool(item.get("enabled", True)),
                labels=list(item.get("labels", [])),
                ssh_alias=item.get("ssh_alias"),
                ssh_config_path=item.get("ssh_config_path"),
                host_name=item.get("host_name"),
                user=item.get("user"),
                port=str(item["port"]) if "port" in item else None,
                password=item.get("password")
                or secret_password(
                    secrets,
                    alias=str(item.get("ssh_alias") or item.get("id") or item.get("name") or ""),
                    server_id=server_id,
                    host_name=item.get("host_name"),
                    user=item.get("user"),
                ),
            )
        )

    discovery = dict(raw.get("ssh_discovery", {}) or {})
    discovery.update(dict(user_raw.get("ssh_discovery", {}) or {}))
    if discovery.get("enabled", False):
        ssh_path = Path(str(discovery.get("config_path") or "~/.ssh/config")).expanduser()
        includes = list(discovery.get("include", ["*"])) or ["*"]
        excludes = set(discovery.get("exclude", []))
        for host in parse_ssh_config(ssh_path):
            alias = host.get("host", "")
            if not alias or alias in excludes:
                continue
            if alias in user_disabled:
                continue
            if not any(fnmatch.fnmatch(alias, pattern) for pattern in includes):
                continue
            server_id = safe_id(alias)
            if server_id in seen:
                continue
            if server_id in user_disabled:
                continue
            seen.add(server_id)
            labels = ["ssh"]
            if host.get("hostname"):
                labels.append(host["hostname"])
            config.servers.append(
                ServerConfig(
                    id=server_id,
                    name=config_alias(
                        aliases,
                        alias=alias,
                        server_id=server_id,
                        host_name=host.get("hostname"),
                        user=host.get("user"),
                        fallback=alias,
                    ),
                    mode="ssh",
                    enabled=True,
                    labels=labels,
                    ssh_alias=alias,
                    host_name=host.get("hostname"),
                    user=host.get("user"),
                    port=host.get("port"),
                    password=secret_password(
                        secrets,
                        alias=alias,
                        server_id=server_id,
                        host_name=host.get("hostname"),
                        user=host.get("user"),
                    ),
                )
            )

    if not config.servers:
        config.servers.append(ServerConfig(id="local", name="Local"))
    return config


_TOML_BARE_RE = None


def _toml_str(value: str) -> str:
    text = str(value)
    out = ['"']
    for char in text:
        code = ord(char)
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return _toml_str(value)


def dump_toml(data: dict[str, Any]) -> str:
    """Minimal TOML writer for our user overlay file."""
    lines: list[str] = []

    # Bare keys MUST come before any [table] header.
    disabled = data.get("disabled_discovery", [])
    if disabled:
        lines.append(f"disabled_discovery = {_toml_value(list(disabled))}")
        lines.append("")

    discovery = data.get("ssh_discovery", {})
    if discovery:
        lines.append("[ssh_discovery]")
        for key, value in discovery.items():
            if value is None or value == "":
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    aliases = data.get("server_aliases", {})
    if aliases:
        lines.append("[server_aliases]")
        for key, value in aliases.items():
            lines.append(f"{_toml_str(key)} = {_toml_str(str(value))}")
        lines.append("")

    for server in data.get("servers", []):
        lines.append("[[servers]]")
        for key, value in server.items():
            if value is None or value == "":
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_user_overlay(config_path: Path) -> dict[str, Any]:
    user_path = config_path.with_name("user_servers.toml")
    if not user_path.exists():
        return {"server_aliases": {}, "disabled_discovery": [], "servers": [], "ssh_discovery": {}}
    try:
        raw = tomllib.loads(user_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {"server_aliases": {}, "disabled_discovery": [], "servers": [], "ssh_discovery": {}}
    return {
        "server_aliases": dict(raw.get("server_aliases", {}) or {}),
        "disabled_discovery": list(raw.get("disabled_discovery", []) or []),
        "servers": list(raw.get("servers", []) or []),
        "ssh_discovery": dict(raw.get("ssh_discovery", {}) or {}),
    }


def save_user_overlay(config_path: Path, overlay: dict[str, Any]) -> None:
    user_path = config_path.with_name("user_servers.toml")
    user_path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_toml(overlay)
    user_path.write_text(text, encoding="utf-8")
