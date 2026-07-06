from __future__ import annotations

import csv
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from ...config import AppConfig, ServerConfig
from ...constants import *  # noqa: F403
from ...compat import public_api_override
from ...path_safety import sensitive_path_block_reason
from ...utils import *  # noqa: F403
from .command import run_command, run_shell
from .ssh import ssh_command
from ..web_terminal import set_terminal_winsize

SENSITIVE_TRANSFER_EXCLUDES = [
    ".ssh/***",
    ".gnupg/***",
    ".aws/***",
    ".azure/***",
    ".config/gcloud/***",
    ".kube/***",
    ".docker/***",
    ".env",
    ".master_key",
    ".netrc",
    ".pypirc",
    ".npmrc",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
    "authorized_keys",
    "api_key*",
    "access_token*",
    "auth_token*",
    "secret*",
    "secrets/***",
    "password*",
    "passwd",
    "credential*",
    "credentials/***",
    "run/secrets/***",
]


def rsync_endpoint_prefix(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = text.split(":", 1)
    if len(parts) != 2 or not parts[1].startswith("/"):
        return ""
    prefix = parts[0].strip()
    if not prefix or "/" in prefix:
        return ""
    return prefix

def server_matches_rsync_prefix(server: ServerConfig, prefix: str) -> bool:
    text = str(prefix or "")
    host = text.split("@", 1)[1] if "@" in text else text
    candidates = {
        server.id,
        server.name,
        server.target_label(),
        server.ssh_alias or "",
        server.host_name or "",
    }
    if server.user and server.host_name:
        candidates.add(f"{server.user}@{server.host_name}")
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate)
        if value == text or value == host or value.endswith(f"@{host}"):
            return True
    return False

def server_for_rsync_endpoint(servers: list[ServerConfig], endpoint: str) -> ServerConfig | None:
    prefix = rsync_endpoint_prefix(endpoint)
    if not prefix:
        return None
    return next((server for server in servers if server.mode != "local" and server_matches_rsync_prefix(server, prefix)), None)

def looks_like_rsync_endpoint(value: str) -> bool:
    text = str(value or "").strip()
    if not text or text.startswith("/"):
        return False
    if ":" not in text:
        return False
    prefix = text.split(":", 1)[0].strip()
    return bool(prefix and "/" not in prefix and "\\" not in prefix)

def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)

def rsync_remote_shell(server: ServerConfig | None, has_password: bool) -> str:
    parts = ["ssh"]
    if server and server.ssh_config_path:
        parts.extend(["-F", server.ssh_config_path])
    parts.extend(
        [
            "-o",
            "ClearAllForwardings=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=6",
        ]
    )
    if has_password:
        parts.extend(
            [
                "-o",
                "PreferredAuthentications=password,keyboard-interactive",
                "-o",
                "PubkeyAuthentication=no",
                "-o",
                "BatchMode=no",
                "-o",
                "NumberOfPasswordPrompts=3",
            ]
        )
    else:
        parts.extend(["-o", "BatchMode=yes", "-o", "NumberOfPasswordPrompts=0"])
    parts.extend(["-o", "StrictHostKeyChecking=accept-new"])
    return shell_join(parts)

def rsync_password_wrapper(password: str, rsync_args: list[str]) -> str:
    script = r"""
import os
import pty
import select
import signal
import sys

password = os.environ.get("TC_SSH_PASSWORD", "")
command = sys.argv[1:]
if not command:
    raise SystemExit("missing rsync command")

pid, master_fd = pty.fork()
if pid == 0:
    os.execvp(command[0], command)

password_bytes = password.encode("utf-8", errors="ignore")
recent = bytearray()
password_prompts = 0
yes_prompts = 0

def forward(sig, _frame):
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass

for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, forward)

try:
    while True:
        ready, _, _ = select.select([master_fd], [], [], 0.1)
        if ready:
            try:
                chunk = os.read(master_fd, 4096)
            except OSError:
                chunk = b""
            if chunk:
                recent.extend(chunk.lower())
                del recent[:-4096]
                visible = chunk.replace(password_bytes, b"******") if password_bytes else chunk
                sys.stdout.buffer.write(visible)
                sys.stdout.buffer.flush()
                if b"are you sure you want to continue connecting" in recent and yes_prompts < 1:
                    os.write(master_fd, b"yes\n")
                    yes_prompts += 1
                if password and (b"password:" in recent or b"passphrase" in recent) and password_prompts < 3:
                    os.write(master_fd, (password + "\n").encode("utf-8"))
                    password_prompts += 1

        child, status = os.waitpid(pid, os.WNOHANG)
        if child == pid:
            raise SystemExit(os.waitstatus_to_exitcode(status))
finally:
    try:
        os.close(master_fd)
    except OSError:
        pass
"""
    return (
        "TC_SSH_PASSWORD="
        + shlex.quote(password)
        + " python3 -c "
        + shlex.quote(script)
        + " "
        + shell_join(rsync_args)
    )

def remote_file_download_endpoint(server: ServerConfig, path_text: str) -> str:
    return f"{server.target_label()}:{str(path_text or '').strip()}"

def rsync_endpoint_path(value: str) -> str:
    text = str(value or "").strip()
    prefix = rsync_endpoint_prefix(text)
    if prefix:
        return text.split(":", 1)[1]
    return text

def transfer_path_block_reason(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        reason = sensitive_path_block_reason(text, rsync_endpoint_path(text))
        if reason:
            return reason.replace("读取/枚举", "传输")
    return ""

def ensure_transfer_path_safe(label: str, *values: Any) -> None:
    reason = transfer_path_block_reason(*values)
    if reason:
        prefix = f"{label}：" if label else ""
        raise ValueError(prefix + reason)

def validate_transfer_endpoint(value: Any, servers: list[ServerConfig], *, label: str) -> None:
    text = str(value or "").strip()
    if not text:
        return
    if "\n" in text or "\r" in text:
        raise ValueError(f"{label}：传输路径不能包含换行。")
    path_text = rsync_endpoint_path(text)
    if path_text.startswith("-"):
        raise ValueError(f"{label}：传输路径不能以 '-' 开头。")
    prefix = rsync_endpoint_prefix(text)
    if prefix:
        if not server_for_rsync_endpoint(servers, text):
            raise ValueError(f"{label}：远程传输只能使用已配置服务器。")
        return
    if looks_like_rsync_endpoint(text):
        raise ValueError(f"{label}：远程传输路径必须使用已配置服务器的绝对路径，例如 server:/path。")

def _download_remote_file_to_local_impl(
    server: ServerConfig,
    path_text: str,
    destination_dir: Path,
    timeout: int = 45,
) -> Path:
    source_path = str(path_text or "").strip()
    if not source_path:
        raise ValueError("请选择要预览的远程文件。")
    reason = sensitive_path_block_reason(source_path)
    if reason:
        raise ValueError(reason)
    destination = destination_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    args = [
        "rsync",
        "-a",
        "--protect-args",
        "--partial",
        "--append-verify",
        "-e",
        rsync_remote_shell(server, bool(server.password)),
        remote_file_download_endpoint(server, source_path),
        str(destination) + "/",
    ]
    if server.password:
        result = run_shell(rsync_password_wrapper(server.password, args), timeout)
    else:
        result = run_command(args, timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError(output.strip() or "远程文件下载失败")
    candidate_name = Path(source_path.rstrip("/")).name or "download"
    candidate = destination / candidate_name
    if candidate.exists():
        return candidate.resolve()
    children = sorted(destination.iterdir(), key=lambda item: item.name.lower())
    if len(children) == 1:
        return children[0].resolve()
    raise ValueError("远程文件已下载，但没有找到本机缓存文件。")

def download_remote_file_to_local(
    server: ServerConfig,
    path_text: str,
    destination_dir: Path,
    timeout: int = 45,
) -> Path:
    override = public_api_override("download_remote_file_to_local", download_remote_file_to_local)
    if override:
        return override(server, path_text, destination_dir, timeout)
    return _download_remote_file_to_local_impl(server, path_text, destination_dir, timeout)

def normalize_rsync_directory_source(value: str, is_dir: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if is_dir and text.endswith("/"):
        return text.rstrip("/")
    return text

def transfer_item_destination_path(source_path: str, is_dir: bool, target: str) -> str:
    text = str(source_path or "").strip()
    target_text = str(target or "").strip()
    if not text or not target_text:
        return ""
    prefix = rsync_endpoint_prefix(target_text)
    remote_path = target_text.split(":", 1)[1] if prefix else target_text
    target_dir = remote_path if remote_path.endswith("/") else f"{remote_path.rstrip('/')}/"
    name = Path(text.rstrip("/")).name
    dest_path = str(Path(target_dir) / name)
    if prefix:
        return f"{prefix}:{dest_path}"
    return dest_path

def transfer_conflict_candidate_paths(source_path: str, is_dir: bool, target: str, *, source_count: int = 1) -> list[str]:
    primary = transfer_item_destination_path(source_path, is_dir, target)
    target_text = str(target or "").strip()
    if source_count != 1 or is_dir or not target_text or target_text.endswith("/"):
        return [primary] if primary else []
    candidates = [target_text]
    if primary and primary != target_text:
        candidates.append(primary)
    return candidates

def transfer_path_exists(path_text: str, servers: list[ServerConfig], timeout: int = 8) -> bool:
    text = str(path_text or "").strip()
    if not text:
        return False
    ensure_transfer_path_safe("传输目标", text)
    validate_transfer_endpoint(text, servers, label="传输目标")
    prefix = rsync_endpoint_prefix(text)
    remote_path = text.split(":", 1)[1] if prefix else text
    if prefix:
        server = server_for_rsync_endpoint(servers, text)
        if not server:
            raise ValueError("传输目标：远程传输只能使用已配置服务器。")
        script = f"test -e {shlex.quote(remote_path)}"
        result = ssh_command(server, f"bash -lc {shlex.quote(script)}", timeout)
        return result.returncode == 0
    return Path(remote_path).exists()

def iter_transfer_source_specs(raw_sources: Any) -> list[tuple[str, str, bool]]:
    result: list[tuple[str, str, bool]] = []
    for item in raw_sources if isinstance(raw_sources, list) else []:
        if isinstance(item, dict):
            source_path = str(item.get("path") or item.get("value") or "").strip()
            is_dir = bool(item.get("is_dir"))
            source_value = str(item.get("value") or source_path).strip()
        else:
            source_path = str(item or "").strip()
            is_dir = source_path.endswith("/")
            source_value = source_path
        if source_path or source_value:
            result.append((source_path, source_value, is_dir))
    return result

def validate_transfer_spec_paths(spec: dict[str, Any], servers: list[ServerConfig] | None = None) -> None:
    server_list = servers or []
    target = str(spec.get("target") or "").strip()
    raw_sources = spec.get("sources") or []
    if target:
        ensure_transfer_path_safe("传输目标", target)
        validate_transfer_endpoint(target, server_list, label="传输目标")
    if not target or not raw_sources:
        return
    for source_path, source_value, is_dir in iter_transfer_source_specs(raw_sources):
        ensure_transfer_path_safe("传输源", source_path, source_value)
        validate_transfer_endpoint(source_value or source_path, server_list, label="传输源")
        for destination in transfer_conflict_candidate_paths(source_path or source_value, is_dir, target):
            ensure_transfer_path_safe("传输目标", destination)
            validate_transfer_endpoint(destination, server_list, label="传输目标")

def check_transfer_conflicts(spec: dict[str, Any], servers: list[ServerConfig]) -> dict[str, Any]:
    target = str(spec.get("target") or "").strip()
    raw_sources = spec.get("sources") or []
    if not target or not raw_sources:
        return {"conflicts": [], "checked": False}
    validate_transfer_spec_paths(spec, servers)
    conflicts: list[dict[str, Any]] = []
    source_specs = iter_transfer_source_specs(raw_sources)
    for source_path, source_value, is_dir in source_specs:
        if not source_path:
            continue
        for destination in transfer_conflict_candidate_paths(source_path, is_dir, target, source_count=len(source_specs)):
            if not destination:
                continue
            if transfer_path_exists(destination, servers):
                conflicts.append(
                    {
                        "source_path": source_path,
                        "source_value": source_value,
                        "is_dir": is_dir,
                        "destination": destination,
                        "name": Path(source_path.rstrip("/")).name,
                    }
                )
                break
    return {"conflicts": conflicts, "checked": True}

def build_transfer_command(spec: dict[str, Any], servers: list[ServerConfig]) -> tuple[str, str]:
    raw_sources = spec.get("sources") or []
    validate_transfer_spec_paths(spec, servers)
    skip_sources = {
        str(item).strip()
        for item in spec.get("skip_sources") or []
        if str(item).strip()
    }
    sources: list[str] = []
    for item in raw_sources:
        if isinstance(item, dict):
            value = str(item.get("value") or item.get("path") or "").strip()
            is_dir = bool(item.get("is_dir"))
            source_path = str(item.get("path") or value).strip()
        else:
            value = str(item or "").strip()
            is_dir = value.endswith("/")
            source_path = value
        if not value:
            continue
        if source_path in skip_sources or value in skip_sources:
            continue
        value = normalize_rsync_directory_source(value, is_dir)
        if value:
            sources.append(value)
    target = str(spec.get("target") or "").strip()
    if not sources or not target:
        raise ValueError("transfer source and target are required")

    target_is_remote = bool(rsync_endpoint_prefix(target))
    if target_is_remote and any(rsync_endpoint_prefix(source) for source in sources):
        raise ValueError("暂不支持远程服务器到远程服务器传输，请让源或目标至少一个是本机。")

    options = dict(spec.get("options") or {})
    excludes = [str(item).strip() for item in spec.get("excludes") or [] if str(item).strip()]
    base_args = ["rsync", "-avPh", "--protect-args", "--info=progress2"]
    if bool(options.get("checksum")):
        base_args.append("--checksum")
    elif bool(options.get("size_only", True)):
        base_args.append("--size-only")
    if bool(options.get("resume_partial", True)):
        base_args.extend(["--partial", "--append-verify"])
    if bool(options.get("ignore_existing")):
        base_args.append("--ignore-existing")
    for item in SENSITIVE_TRANSFER_EXCLUDES:
        base_args.extend(["--exclude", item])
    for item in excludes:
        base_args.extend(["--exclude", item])

    actual_lines: list[str] = []
    display_lines: list[str] = []
    for source in sources:
        remote_endpoint = target if target_is_remote else source if rsync_endpoint_prefix(source) else ""
        remote_server = server_for_rsync_endpoint(servers, remote_endpoint) if remote_endpoint else None
        password = remote_server.password if remote_server else None
        args = list(base_args)
        if remote_endpoint:
            if not remote_server:
                raise ValueError("传输路径：远程传输只能使用已配置服务器。")
            args.extend(["-e", rsync_remote_shell(remote_server, bool(password))])
        args.extend(["--", source, target])
        display = shell_join(args)
        if remote_endpoint and password:
            display += "  # 使用 secrets.toml 中的 SSH 密码"
            actual_lines.append(rsync_password_wrapper(password, args))
        else:
            actual_lines.append(shell_join(args))
        display_lines.append(display)

    if len(actual_lines) == 1:
        return actual_lines[0], display_lines[0]
    return "set -e\n" + "\n".join(actual_lines), "set -e\n" + "\n".join(display_lines)

def check_detail_text(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        text = fallback
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback
    return lines[0][:240]
