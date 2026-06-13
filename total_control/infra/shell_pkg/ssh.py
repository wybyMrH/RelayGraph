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
from ...utils import *  # noqa: F403
from ..web_terminal import set_terminal_winsize
from .command import run_command, run_pty_password_command


def _ssh_command_impl(server: ServerConfig, remote_command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    command = ssh_command_base(server, connect_timeout=timeout)
    command.append(remote_command)
    if server.password:
        return run_pty_password_command(command, server.password, timeout=timeout + 8)
    return run_command(command, timeout=timeout + 2)

def ssh_command(server: ServerConfig, remote_command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    override = public_api_override("ssh_command", ssh_command)
    if override:
        return override(server, remote_command, timeout)
    return _ssh_command_impl(server, remote_command, timeout)

def ssh_command_base(server: ServerConfig, connect_timeout: int = 20) -> list[str]:
    # 用 user@host_name 连接更明确，不依赖 SSH config alias
    if server.user and server.host_name:
        target = f"{server.user}@{server.host_name}"
    else:
        target = server.ssh_alias or server.host_name or server.id
    command = ["ssh"]
    # 不传 -F，让 SSH 使用系统默认 config（~/.ssh/config），自动读取 IdentityFile 等配置
    if server.port:
        command.extend(["-p", str(server.port)])
    if server.password:
        command.extend(
            [
                "-o",
                "PreferredAuthentications=password,keyboard-interactive",
                "-o",
                "PubkeyAuthentication=no",
            ]
        )
    command.extend(
        [
            "-o",
            "BatchMode=no" if server.password else "BatchMode=yes",
            "-o",
            f"ConnectTimeout={max(1, min(connect_timeout, 20))}",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "NumberOfPasswordPrompts=3" if server.password else "NumberOfPasswordPrompts=0",
            target,
        ]
    )
    return command

def _probe_ssh_reachable_impl(server: ServerConfig, timeout: int) -> bool:
    if server.mode == "local":
        return True
    try:
        result = ssh_command(
            server,
            remote_check_script("printf '%s\\n' __tc_ok__"),
            timeout=min(max(timeout, 1), REACHABILITY_PROBE_TIMEOUT_SECONDS),
        )
        output = f"{result.stdout or ''}\n{result.stderr or ''}".strip()
        if result.returncode != 0 or "__tc_ok__" not in output:
            return False
        return not ssh_transport_output_looks_failed(output)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return False
    except Exception:  # noqa: BLE001 - keep polling resilient for one bad host.
        return False

def probe_ssh_reachable(server: ServerConfig, timeout: int) -> bool:
    override = public_api_override("probe_ssh_reachable", probe_ssh_reachable)
    if override:
        return bool(override(server, timeout))
    return _probe_ssh_reachable_impl(server, timeout)

def apply_remote_reachability(
    status: dict[str, Any],
    server: ServerConfig,
    app_config: AppConfig,
    *,
    default_error_kind: str,
) -> None:
    if server.mode == "local":
        status["reachable"] = True
        status["error_kind"] = status.get("error_kind") or "gpu_probe"
        return
    if probe_ssh_reachable(server, app_config.remote_timeout_seconds):
        status["reachable"] = True
        status["error_kind"] = "gpu_probe"
    else:
        status["reachable"] = False
        status["error_kind"] = default_error_kind or "connection"
