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
from ...utils import *  # noqa: F403
from ..web_terminal import set_terminal_winsize


def parse_smoke_peak_mib(text: str) -> int:
    for line in text.splitlines():
        if "Peak allocated:" in line:
            parts = line.replace(":", " ").split()
            for index, part in enumerate(parts):
                if part.lower() == "allocated" and index + 1 < len(parts):
                    return safe_int(parts[index + 1])
        if "Peak MiB" in line:
            parts = line.split()
            for part in parts:
                value = safe_int(part, -1)
                if value > 0:
                    return value
    return 0

def render_task_template(template: str, values: dict[str, Any]) -> str:
    if not template:
        return ""
    try:
        return template.format_map(_TemplateMap(values))
    except (KeyError, ValueError):
        return template

def parse_param_matrix(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        rows = [
            dict(item)
            for item in value
            if isinstance(item, dict)
        ]
    else:
        rows = []
        text = str(value or "").strip()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"参数矩阵 JSON 行解析失败: {exc}") from exc
                if not isinstance(parsed, dict):
                    raise ValueError("参数矩阵 JSON 行必须是对象")
                rows.append(parsed)
                continue
            row: dict[str, Any] = {}
            for cell in next(csv.reader([line])):
                part = cell.strip()
                if not part:
                    continue
                if "=" not in part:
                    row.setdefault("value", part)
                    continue
                key, cell_value = part.split("=", 1)
                key = key.strip()
                if key:
                    row[key] = cell_value.strip()
            if row:
                rows.append(row)
    if not rows:
        rows = [{}]
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        item = dict(row)
        item.setdefault("index", index)
        item.setdefault("i", index)
        normalized.append(item)
    return normalized

def conda_bootstrap(env_name: str, server_user: str | None = None) -> str:
    env = shlex.quote(env_name)
    if "/" in env_name:
        env_path = shlex.quote(env_name.rstrip("/"))
        return "\n".join(
            [
                f"if [ -f {env_path}/bin/activate ]; then",
                f"  . {env_path}/bin/activate",
                "else",
                f"  conda activate {env}",
                "fi",
            ]
        )
    user_env_path = f"/home/{server_user}/envs/{env_name}" if server_user else ""
    home_activate = f"\"$HOME/envs\"/{env}/bin/activate"
    lines = []
    if user_env_path:
        lines.append(f"if [ -f {shlex.quote(user_env_path)}/bin/activate ]; then")
        lines.append(f"  . {shlex.quote(user_env_path)}/bin/activate")
        lines.append(f"elif [ -f {home_activate} ]; then")
        lines.append(f"  . {home_activate}")
    else:
        lines.append(f"if [ -f {home_activate} ]; then")
        lines.append(f"  . {home_activate}")
    lines.append("else")
    lines.append(
        "  if [ -f ~/software/anaconda3/etc/profile.d/conda.sh ]; then "
        ". ~/software/anaconda3/etc/profile.d/conda.sh; "
        "elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then "
        ". ~/anaconda3/etc/profile.d/conda.sh; "
        "elif [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then "
        ". ~/miniconda3/etc/profile.d/conda.sh; "
        "fi"
    )
    lines.append(f"  conda activate {env}")
    lines.append("fi")
    return "\n".join(lines)

def build_job_script(
    job: dict[str, Any],
    log_path: str,
    remote: bool,
    server: ServerConfig | None = None,
    command_override: str | None = None,
    command_display: str | None = None,
) -> str:
    if remote:
        log_target = f'"$HOME/.total_control/logs/{job["id"]}.log"'
        mkdir_line = 'mkdir -p "$HOME/.total_control/logs"'
        exec_line = f"exec > {log_target} 2>&1"
    else:
        mkdir_line = f"mkdir -p {shlex.quote(str(Path(log_path).parent))}"
        exec_line = f"exec > {shlex.quote(log_path)} 2>&1"
    lines = [
        "set -o pipefail",
        mkdir_line,
        exec_line,
        f"echo '[total-control] job {job['id']} started at '$(date '+%F %T')",
    ]
    cwd = str(job.get("cwd") or "").strip()
    if cwd:
        lines.append(f"cd {shlex.quote(cwd)}")
    env_name = str(job.get("env_name") or "").strip()
    if env_name:
        lines.append(conda_bootstrap(env_name, server.user if server else None))
    gpu_index = job.get("gpu_index")
    gpu_index_text = str(gpu_index).strip().lower() if gpu_index is not None else ""
    if gpu_index_text in {"none", "no_gpu", "cpu"}:
        lines.append("unset CUDA_VISIBLE_DEVICES")
    elif gpu_index is not None and gpu_index != "":
        lines.append(f"export CUDA_VISIBLE_DEVICES={shlex.quote(str(gpu_index))}")
    command = str(command_override if command_override is not None else job.get("command") or "")
    display = str(command_display if command_display is not None else job.get("command_display") or command)
    lines.extend(
        [
            "echo '[total-control] server='$(hostname)' gpu='${CUDA_VISIBLE_DEVICES:-none}",
            "echo '[total-control] command:'",
            f"echo {shlex.quote(display)}",
            command,
            "code=$?",
            "echo '[total-control] finished at '$(date '+%F %T')",
            'echo "[total-control] exit_code=$code"',
            "exit $code",
        ]
    )
    return "\n".join(lines)
