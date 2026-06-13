from __future__ import annotations

import os
import pty
import select
import signal
import struct
import termios
import threading
import time
import fcntl
from typing import Any

from ..config import ServerConfig
from ..constants import TMUX_DEFAULT_COLUMNS, TMUX_DEFAULT_ROWS
from ..utils import now_iso


def set_terminal_winsize(fd: int, columns: int = TMUX_DEFAULT_COLUMNS, rows: int = TMUX_DEFAULT_ROWS) -> None:
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    except OSError:
        pass


class WebTerminal:
    """Long-lived PTY backing a browser terminal session."""

    MAX_BUFFER = 1_000_000  # bytes of scrollback we retain

    def __init__(self, session_id: str, server: ServerConfig, command: list[str]) -> None:
        self.id = session_id
        self.server_id = server.id
        self.server_name = server.name
        self.command = command
        self.password = server.password
        self.created_at = time.time()
        self.last_access = time.time()
        self.alive = True
        self.exit_code: int | None = None
        self.buffer = bytearray()
        self.lock = threading.Lock()
        self.master_fd: int | None = None
        self.pid: int | None = None
        self._password_prompts = 0
        self._yes_prompts = 0
        self._spawn()
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

    def _spawn(self) -> None:
        pid, master_fd = pty.fork()
        if pid == 0:
            set_terminal_winsize(0)
            env = os.environ.copy()
            env["TERM"] = "dumb"
            env["NO_COLOR"] = "1"
            env["CLICOLOR"] = "0"
            env["COLUMNS"] = str(TMUX_DEFAULT_COLUMNS)
            env["LINES"] = str(TMUX_DEFAULT_ROWS)
            try:
                os.execvpe(self.command[0], self.command, env)
            except Exception:
                os._exit(1)
        self.pid = pid
        self.master_fd = master_fd
        set_terminal_winsize(master_fd)

    def _read_loop(self) -> None:
        assert self.master_fd is not None
        try:
            while True:
                ready, _, _ = select.select([self.master_fd], [], [], 0.5)
                if ready:
                    try:
                        chunk = os.read(self.master_fd, 4096)
                    except OSError:
                        chunk = b""
                    if not chunk:
                        break
                    chunk_lower = chunk.lower()
                    with self.lock:
                        self.buffer.extend(chunk)
                        if len(self.buffer) > self.MAX_BUFFER:
                            del self.buffer[: len(self.buffer) - self.MAX_BUFFER]
                    # auto-handle SSH prompts when password is provided
                    if self.password:
                        if (
                            b"are you sure you want to continue connecting" in chunk_lower
                            and self._yes_prompts < 1
                        ):
                            try:
                                os.write(self.master_fd, b"yes\n")
                                self._yes_prompts += 1
                            except OSError:
                                pass
                        if (
                            (b"password:" in chunk_lower or b"passphrase" in chunk_lower)
                            and self._password_prompts < 1
                        ):
                            try:
                                os.write(
                                    self.master_fd, (self.password + "\n").encode("utf-8")
                                )
                                self._password_prompts += 1
                            except OSError:
                                pass
                # check if child exited
                try:
                    pid, status = os.waitpid(self.pid or 0, os.WNOHANG)
                except ChildProcessError:
                    pid, status = 0, 0
                if pid == self.pid:
                    self.exit_code = os.waitstatus_to_exitcode(status)
                    break
        finally:
            self.alive = False
            try:
                if self.master_fd is not None:
                    os.close(self.master_fd)
            except OSError:
                pass

    def write(self, data: str) -> None:
        if not self.alive or self.master_fd is None:
            raise ValueError("terminal closed")
        try:
            os.write(self.master_fd, data.encode("utf-8"))
        except OSError as exc:
            raise ValueError(f"write failed: {exc}") from exc

    def signal(self, sig: int) -> None:
        if not self.alive or self.pid is None:
            return
        try:
            os.kill(self.pid, sig)
        except ProcessLookupError:
            pass

    def close(self) -> None:
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, b"\x04")  # EOF
            except OSError:
                pass
        if self.pid is not None:
            try:
                os.kill(self.pid, 9)
            except ProcessLookupError:
                pass
        self.alive = False

    def snapshot(self, since: int = 0) -> tuple[bytes, int]:
        with self.lock:
            total = len(self.buffer)
            if since < 0 or since > total:
                since = 0
            data = bytes(self.buffer[since:])
        self.last_access = time.time()
        return data, total
