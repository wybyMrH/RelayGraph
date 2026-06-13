from __future__ import annotations

import csv
import os
import pty
import re
import select
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


def _run_command_impl(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    override = public_api_override("run_command", run_command)
    if override:
        return override(command, timeout)
    return _run_command_impl(command, timeout)

def run_shell(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return run_command(["bash", "-lc", script], timeout)

def run_pty_password_command(command: list[str], password: str, timeout: int) -> subprocess.CompletedProcess[str]:
    pid, master_fd = pty.fork()
    env = os.environ.copy()
    env.setdefault("TERM", "dumb")
    if pid == 0:
        os.execvpe(command[0], command, env)

    output = bytearray()
    password_prompts = 0
    yes_prompts = 0
    deadline = time.monotonic() + timeout
    try:
        while True:
            if time.monotonic() > deadline:
                try:
                    os.kill(pid, 9)
                finally:
                    os.waitpid(pid, 0)
                text = output.decode("utf-8", errors="replace").replace(password, "******")
                return subprocess.CompletedProcess(command, 124, text, "timeout")

            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if chunk:
                    output.extend(chunk)
                    recent = output[-4096:].lower()
                    if b"are you sure you want to continue connecting" in recent and yes_prompts < 1:
                        os.write(master_fd, b"yes\n")
                        yes_prompts += 1
                    if (b"password:" in recent or b"passphrase" in recent) and password_prompts < 3:
                        os.write(master_fd, (password + "\n").encode("utf-8"))
                        password_prompts += 1

            child_pid, status = os.waitpid(pid, os.WNOHANG)
            if child_pid == pid:
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0)
                    if not ready:
                        break
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)
                text = output.decode("utf-8", errors="replace").replace(password, "******")
                return subprocess.CompletedProcess(command, os.waitstatus_to_exitcode(status), text, "")
    finally:
        os.close(master_fd)
