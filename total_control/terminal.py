from __future__ import annotations

import argparse
import os
import pty
import select
import sys
import termios
import time
import tty
from pathlib import Path

from .server import DEFAULT_CONFIG, ServerConfig, load_config, ssh_command_base


def interactive_ssh(server: ServerConfig, timeout: int = 30) -> int:
    command = ssh_command_base(server)
    pid, master_fd = pty.fork()
    if pid == 0:
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        os.execvpe(command[0], command, env)

    stdin_fd = sys.stdin.fileno()
    old_tty = termios.tcgetattr(stdin_fd)
    output = bytearray()
    prompts = 0
    deadline = time.monotonic() + timeout
    try:
        tty.setraw(stdin_fd)
        while True:
            ready, _, _ = select.select([master_fd, stdin_fd], [], [], 0.1)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                output.extend(chunk)
                os.write(sys.stdout.fileno(), chunk)
                recent = output[-4096:].lower()
                if server.password and (b"password:" in recent or b"passphrase" in recent) and prompts < 3:
                    os.write(master_fd, (server.password + "\n").encode("utf-8"))
                    prompts += 1
                    deadline = time.monotonic() + timeout
                elif prompts == 0 and time.monotonic() > deadline:
                    deadline = time.monotonic() + 86400
            if stdin_fd in ready:
                data = os.read(stdin_fd, 4096)
                if not data:
                    break
                os.write(master_fd, data)
            child_pid, status = os.waitpid(pid, os.WNOHANG)
            if child_pid == pid:
                return os.waitstatus_to_exitcode(status)
    finally:
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty)
        os.close(master_fd)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Open a RelayGraph interactive terminal")
    parser.add_argument("server_id")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = load_config(args.config)
    server = next((item for item in config.servers if item.id == args.server_id), None)
    if not server:
        print(f"Unknown server: {args.server_id}", file=sys.stderr)
        raise SystemExit(2)

    if server.mode == "local":
        shell = os.environ.get("SHELL") or "bash"
        os.execvp(shell, [shell, "-l"])
    raise SystemExit(interactive_ssh(server))


if __name__ == "__main__":
    main()
