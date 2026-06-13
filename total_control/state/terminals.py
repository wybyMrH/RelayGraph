from __future__ import annotations

from ._deps import *  # noqa: F403

class TerminalsMixin:
    def terminal_open(self, server_id: str) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        if server.mode == "local":
            shell = os.environ.get("SHELL") or "bash"
            command = [shell, "-l"]
        else:
            command = ssh_command_base(server)
        session_id = uuid.uuid4().hex[:12]
        term = WebTerminal(session_id, server, command)
        with self.terminals_lock:
            self.terminals[session_id] = term
        return {
            "id": session_id,
            "server_id": server.id,
            "server_name": server.name,
            "cursor": 0,
            "alive": True,
            "output": "",
        }


    def terminal_read(self, session_id: str, since: int = 0) -> dict[str, Any]:
        with self.terminals_lock:
            term = self.terminals.get(session_id)
        if not term:
            raise ValueError("terminal session not found")
        data, total = term.snapshot(since)
        return {
            "session_id": session_id,
            "output": data.decode("utf-8", errors="replace"),
            "cursor": total,
            "alive": term.alive,
            "exit_code": term.exit_code,
        }


    def terminal_write(self, session_id: str, data: str) -> None:
        with self.terminals_lock:
            term = self.terminals.get(session_id)
        if not term:
            raise ValueError("terminal session not found")
        term.write(data)


    def terminal_signal(self, session_id: str, sig: int) -> None:
        with self.terminals_lock:
            term = self.terminals.get(session_id)
        if not term:
            raise ValueError("terminal session not found")
        term.signal(sig)


    def terminal_close(self, session_id: str) -> None:
        with self.terminals_lock:
            term = self.terminals.pop(session_id, None)
        if not term:
            raise ValueError("terminal session not found")
        term.close()


    def terminal_list(self) -> list[dict[str, Any]]:
        with self.terminals_lock:
            return [
                {
                    "session_id": term.id,
                    "server_id": term.server_id,
                    "server_name": term.server_name,
                    "alive": term.alive,
                }
                for term in self.terminals.values()
            ]
