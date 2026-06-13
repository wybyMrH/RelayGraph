from __future__ import annotations

import re
import shlex
import signal
import subprocess
from typing import Any

from ..config import ServerConfig
from ..utils import now_iso
from .shell import (
    check_detail_text,
    remote_check_script,
    run_shell,
    server_check_ok,
    server_check_scripts,
    ssh_command,
)


def run_server_checks(
    server: ServerConfig,
    timeout: int,
    *,
    local_runner: Any = run_shell,
    remote_runner: Any = ssh_command,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if server.mode == "local":
        checks.append({
            "key": "ssh",
            "label": "SSH",
            "ok": True,
            "detail": "本机服务器，无需 SSH",
        })
        for key, label, script in server_check_scripts()[1:]:
            result = local_runner(script, timeout)
            ok = server_check_ok(key, result, label)
            checks.append({
                "key": key,
                "label": label,
                "ok": ok,
                "detail": check_detail_text(result, f"{label} ok" if ok else f"{label} failed"),
            })
        return {
            "server_id": server.id,
            "server_name": server.name,
            "target": server.target_label(),
            "ok": all(item["ok"] for item in checks),
            "checked_at": now_iso(),
            "checks": checks,
        }

    ssh_script = remote_check_script(server_check_scripts()[0][2])
    ssh_result = remote_runner(server, ssh_script, timeout)
    ssh_ok = ssh_result.returncode == 0
    checks.append({
        "key": "ssh",
        "label": "SSH",
        "ok": ssh_ok,
        "detail": check_detail_text(ssh_result, "ssh ok" if ssh_ok else "ssh failed"),
    })
    for key, label, script in server_check_scripts()[1:]:
        if not ssh_ok:
            checks.append({
                "key": key,
                "label": label,
                "ok": False,
                "detail": "SSH 未通过，未继续检查",
            })
            continue
        wrapped = remote_check_script(script)
        result = remote_runner(server, wrapped, timeout)
        ok = server_check_ok(key, result, label)
        checks.append({
            "key": key,
            "label": label,
            "ok": ok,
            "detail": check_detail_text(result, f"{label} ok" if ok else f"{label} failed"),
        })
    return {
        "server_id": server.id,
        "server_name": server.name,
        "target": server.target_label(),
        "ok": all(item["ok"] for item in checks),
        "checked_at": now_iso(),
        "checks": checks,
    }

def build_process_stop_script(pid: int, grace_seconds: int = 10) -> str:
    checks = max(1, int(grace_seconds * 5))
    return "\n".join(
        [
            "set -u",
            f"pid={shlex.quote(str(pid))}",
            'tmux_session=""',
            'tmux_pane_pid=""',
            'tmux_pane_id=""',
            'pgid=""',
            "process_alive() {",
            '  local target="$1"',
            '  if ! kill -0 "$target" 2>/dev/null; then',
            "    return 1",
            "  fi",
            '  local stat=""',
            '  stat=$(ps -o stat= -p "$target" 2>/dev/null | tr -d " ")',
            '  case "$stat" in',
            '    ""|Z*) return 1 ;;',
            "  esac",
            "  return 0",
            "}",
            "find_tmux_context() {",
            '  command -v tmux >/dev/null 2>&1 || return 1',
            '  local current="$1"',
            '  local panes=""',
            '  local match=""',
            '  local parent=""',
            '  panes=$(tmux list-panes -a -F "#{session_name}|#{pane_pid}|#{pane_id}" 2>/dev/null || true)',
            '  [ -n "$panes" ] || return 1',
            '  while [ -n "$current" ] && [ "$current" -gt 1 ] 2>/dev/null; do',
            '    match=$(printf "%s\\n" "$panes" | awk -F"|" -v cur="$current" \'$2 == cur { print $1 "|" $2 "|" $3; exit }\')',
            '    if [ -n "$match" ]; then',
            '      IFS="|" read -r tmux_session tmux_pane_pid tmux_pane_id <<<"$match"',
            "      return 0",
            "    fi",
            '    parent=$(ps -o ppid= -p "$current" 2>/dev/null | tr -d " ")',
            '    [ -n "$parent" ] || break',
            '    current="$parent"',
            "  done",
            "  return 1",
            "}",
            "send_ctrl_c() {",
            '  [ -n "$tmux_pane_id" ] || return 0',
            '  tmux send-keys -t "$tmux_pane_id" C-c 2>/dev/null || true',
            "}",
            "signal_targets() {",
            '  local sig="$1"',
            '  if [ -n "$tmux_pane_pid" ]; then',
            '    pkill "-$sig" -P "$tmux_pane_pid" 2>/dev/null || true',
            "  fi",
            '  if [ -n "$pgid" ] && [ "$pgid" -gt 1 ] 2>/dev/null; then',
            '    kill "-$sig" -- "-$pgid" 2>/dev/null || true',
            "  fi",
            '  kill "-$sig" "$pid" 2>/dev/null || true',
            "}",
            "close_tmux_pane() {",
            '  [ -n "$tmux_pane_id" ] || return 0',
            '  tmux kill-pane -t "$tmux_pane_id" 2>/dev/null || true',
            "}",
            'if ! process_alive "$pid"; then',
            '  echo "process already stopped"',
            "  exit 0",
            "fi",
            'find_tmux_context "$pid" || true',
            'pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d " ")',
            'if [ -n "$tmux_pane_id" ]; then',
            "  send_ctrl_c",
            "  sleep 1",
            '  if ! process_alive "$pid"; then',
            '    close_tmux_pane',
            '    echo "process stopped after Ctrl-C"',
            "    exit 0",
            "  fi",
            "fi",
            'signal_targets TERM',
            f"for i in $(seq 1 {checks}); do",
            '  if ! process_alive "$pid"; then',
            '    close_tmux_pane',
            '    echo "process stopped after SIGTERM"',
            "    exit 0",
            "  fi",
            "  sleep 0.2",
            "done",
            'signal_targets KILL',
            "for i in $(seq 1 10); do",
            '  if ! process_alive "$pid"; then',
            '    close_tmux_pane',
            '    echo "process stopped after SIGKILL"',
            "    exit 0",
            "  fi",
            "  sleep 0.2",
            "done",
            'echo "process still alive"',
            "exit 1",
        ]
    )


def stop_server_process(
    server: ServerConfig,
    pid: int,
    *,
    grace_seconds: int = 10,
    local_runner: Any = run_shell,
    remote_runner: Any = ssh_command,
) -> dict[str, Any]:
    if pid <= 0:
        raise ValueError("invalid pid")
    script = build_process_stop_script(pid, grace_seconds=grace_seconds)
    timeout = max(6, grace_seconds + 6)
    if server.mode == "local":
        result = local_runner(script, timeout)
    else:
        result = remote_runner(server, "bash -lc " + shlex.quote(script), timeout + 2)
    detail = check_detail_text(
        result,
        "process stopped" if result.returncode == 0 else "process stop failed",
    )
    if result.returncode != 0:
        raise ValueError(detail)
    return {
        "server_id": server.id,
        "server_name": server.name,
        "pid": pid,
        "ok": True,
        "detail": detail,
        "stopped_at": now_iso(),
    }
