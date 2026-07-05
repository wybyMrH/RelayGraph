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
from .ssh import ssh_command
from ..web_terminal import set_terminal_winsize


def ps_lookup_local(pids: list[str], timeout: int) -> dict[str, dict[str, str]]:
    if not pids:
        return {}
    result = run_command(["ps", "-o", "uid=,user=,pid=,command=", "-p", ",".join(pids)], timeout)
    return parse_ps_output(result.stdout)

def ps_lookup_remote(server: ServerConfig, pids: list[str], timeout: int) -> dict[str, dict[str, str]]:
    if not pids:
        return {}
    cmd = "ps -o uid=,user=,pid=,command= -p " + shlex.quote(",".join(pids))
    result = ssh_command(server, cmd, timeout)
    return parse_ps_output(result.stdout)

def parse_ps_output(text: str) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) >= 3 and parts[0].isdigit():
            pid = parts[2]
            data[pid] = {
                "uid": parts[0],
                "user": parts[1],
                "command": parts[3] if len(parts) == 4 else "",
            }
            continue
        parts = line.strip().split(None, 2)
        if len(parts) >= 2:
            pid = parts[1]
            data[pid] = {
                "uid": "",
                "user": parts[0],
                "command": parts[2] if len(parts) == 3 else "",
            }
    return data

def percent(used: int | float, total: int | float) -> float:
    total_value = float(total or 0)
    if total_value <= 0:
        return 0.0
    return round(max(float(used or 0), 0.0) * 100 / total_value, 1)
