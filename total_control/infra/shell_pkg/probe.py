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
from ...utils import parse_iso_timestamp  # noqa: F401 — re-exported via shell_pkg
from ..web_terminal import set_terminal_winsize
from .gpu import nvidia_smi_output_looks_failed, nvidia_smi_probe_script
from .transfer import check_detail_text


def remote_check_script(script: str) -> str:
    escaped = script.replace("'", "'\"'\"'")
    return f"bash -lc 'set -o pipefail; {escaped}'"

def server_check_ok(key: str, result: subprocess.CompletedProcess[str], label: str) -> bool:
    if result.returncode != 0:
        return False
    detail = check_detail_text(result, f"{label} ok")
    if key == "nvidia-smi" and nvidia_smi_output_looks_failed(detail):
        return False
    if key == "nvidia-smi":
        return bool((result.stdout or "").strip())
    return True

def server_check_scripts() -> list[tuple[str, str, str]]:
    return [
        ("ssh", "SSH", "printf 'ssh ok\\n'"),
        ("python3", "python3", "python3 --version"),
        ("nvidia-smi", "nvidia-smi", nvidia_smi_probe_script()),
        ("tmux", "tmux", "tmux -V"),
        ("rsync", "rsync", "rsync --version | head -n 1"),
    ]
