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
from .command import run_command
from ..web_terminal import set_terminal_winsize


def tmux_new_session_args(session: str, shell_command: str) -> list[str]:
    return [
        "tmux",
        "new-session",
        "-d",
        "-s",
        session,
        "-x",
        str(TMUX_DEFAULT_COLUMNS),
        "-y",
        str(TMUX_DEFAULT_ROWS),
        shell_command,
    ]

def tmux_resize_commands(session: str) -> list[list[str]]:
    columns = str(TMUX_DEFAULT_COLUMNS)
    rows = str(TMUX_DEFAULT_ROWS)
    return [
        ["tmux", "resize-window", "-t", session, "-x", columns, "-y", rows],
        ["tmux", "resize-pane", "-t", session, "-x", columns, "-y", rows],
    ]

def tmux_resize_shell_script(session: str) -> str:
    target = shlex.quote(session)
    columns = str(TMUX_DEFAULT_COLUMNS)
    rows = str(TMUX_DEFAULT_ROWS)
    return "\n".join(
        [
            f"tmux resize-window -t {target} -x {columns} -y {rows} 2>/dev/null || true",
            f"tmux resize-pane -t {target} -x {columns} -y {rows} 2>/dev/null || true",
        ]
    )

def prepare_tmux_for_capture(session: str) -> None:
    for command in tmux_resize_commands(session):
        try:
            run_command(command, timeout=TMUX_RESIZE_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            pass

def make_session_name(job_id: str) -> str:
    return "tc_" + "".join(char for char in job_id if char.isalnum())[:24]

def local_log_path(server_id: str, job_id: str) -> Path:
    return LOG_DIR / safe_id(server_id) / f"{job_id}.log"

def remote_log_path(job_id: str) -> str:
    return f"$HOME/.total_control/logs/{job_id}.log"
