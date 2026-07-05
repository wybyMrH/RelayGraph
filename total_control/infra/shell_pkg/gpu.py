from __future__ import annotations

import copy
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
from concurrent.futures import ThreadPoolExecutor, as_completed

from ...compat import public_api_override
from ...utils import *  # noqa: F403
from .command import run_command
from .host import collect_host_resources, host_resource_error_payload, parse_csv_lines
from .process import ps_lookup_local, ps_lookup_remote
from .ssh import apply_remote_reachability, ssh_command
from ..web_terminal import set_terminal_winsize


def gpu_activity_state(
    utilization: int,
    util_threshold: int,
    *,
    memory_used_mib: int = 0,
    memory_total_mib: int = 0,
    memory_free_mib: int = 0,
    idle_min_free_mib: int = 1024,
    has_processes: bool = False,
    memory_used_threshold_pct: int = 8,
) -> str:
    if has_processes:
        return "busy"
    if safe_int(utilization) > safe_int(util_threshold):
        return "busy"
    total = safe_int(memory_total_mib)
    used = safe_int(memory_used_mib)
    if total > 0 and used * 100 / total >= safe_int(memory_used_threshold_pct):
        return "busy"
    if total > 0 and safe_int(memory_free_mib) < safe_int(idle_min_free_mib):
        return "busy"
    return "idle"

def _collect_server_impl(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
    started = time.time()
    status: dict[str, Any] = {
        "id": server.id,
        "name": server.name,
        "mode": server.mode,
        "target": server.target_label(),
        "labels": server.labels,
        "online": False,
        "reachable": server.mode == "local",
        "monitor_ok": False,
        "error": "",
        "error_kind": "",
        "collected_at": now_iso(),
        "elapsed_ms": 0,
        "current_user": "",
        "current_uid": "",
        "gpus": [],
        "processes": [],
        "host_resources": {},
    }
    def set_host_resources(payload: dict[str, Any]) -> None:
        status["host_resources"] = payload
        current_user = str(payload.get("current_user") or "").strip()
        if current_user:
            status["current_user"] = current_user
        current_uid = str(payload.get("current_uid") or "").strip()
        if current_uid:
            status["current_uid"] = current_uid

    if not server.enabled:
        status["error"] = "disabled"
        status["host_resources"] = host_resource_error_payload("disabled")
        return status

    try:
        if server.mode == "local":
            gpu_result = run_command(
                ["nvidia-smi", f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
                timeout=app_config.remote_timeout_seconds,
            )
            proc_result = run_command(
                ["nvidia-smi", f"--query-compute-apps={PROC_QUERY}", "--format=csv,noheader,nounits"],
                timeout=app_config.remote_timeout_seconds,
            )
        else:
            gpu_result = ssh_command(
                server,
                f"nvidia-smi --query-gpu={shlex.quote(GPU_QUERY)} --format=csv,noheader,nounits",
                timeout=app_config.remote_timeout_seconds,
            )
            proc_result = ssh_command(
                server,
                f"nvidia-smi --query-compute-apps={shlex.quote(PROC_QUERY)} --format=csv,noheader,nounits",
                timeout=app_config.remote_timeout_seconds,
            )

        if gpu_result.returncode != 0:
            error = gpu_result.stderr.strip() or gpu_result.stdout.strip() or "nvidia-smi failed"
            status["error"] = error[-500:]
            if server.mode == "local" or not ssh_transport_output_looks_failed(error):
                status["reachable"] = True
                status["error_kind"] = "gpu_probe"
            else:
                apply_remote_reachability(status, server, app_config, default_error_kind="connection")
            set_host_resources(
                collect_host_resources(server, app_config)
                if status.get("reachable")
                else host_resource_error_payload("server unreachable")
            )
            return status

        uuid_to_index: dict[str, int] = {}
        gpu_rows: list[dict[str, Any]] = []
        for row in parse_csv_lines(gpu_result.stdout):
            if len(row) < 9:
                continue
            index = safe_int(row[0])
            total = safe_int(row[3])
            used = safe_int(row[4])
            util = safe_int(row[5])
            temp = safe_int(row[6])
            free = max(total - used, 0)
            uuid_to_index[row[1]] = index
            gpu_rows.append(
                {
                    "index": index,
                    "uuid": row[1],
                    "name": row[2],
                    "memory_total_mib": total,
                    "memory_used_mib": used,
                    "memory_free_mib": free,
                    "gpu_util": util,
                    "temperature": temp,
                    "power_draw": safe_float(row[7]),
                    "power_limit": safe_float(row[8]),
                }
            )

        processes = []
        proc_rows = parse_csv_lines(proc_result.stdout if proc_result.returncode == 0 else "")
        pids = [row[1] for row in proc_rows if len(row) >= 4]
        ps_data = (
            ps_lookup_local(pids, app_config.remote_timeout_seconds)
            if server.mode == "local"
            else ps_lookup_remote(server, pids, app_config.remote_timeout_seconds)
        )
        gpu_process_counts: dict[int, int] = {}
        for row in proc_rows:
            if len(row) < 4:
                continue
            pid = row[1]
            ps_row = ps_data.get(pid, {})
            gpu_index = uuid_to_index.get(row[0])
            if gpu_index is not None:
                gpu_process_counts[gpu_index] = gpu_process_counts.get(gpu_index, 0) + 1
            processes.append(
                {
                    "gpu_index": gpu_index,
                    "pid": pid,
                    "uid": ps_row.get("uid", ""),
                    "user": ps_row.get("user", ""),
                    "process_name": row[2],
                    "used_memory_mib": safe_int(row[3]),
                    "command": ps_row.get("command", row[2]),
                }
            )

        status["gpus"] = [
            {
                **gpu,
                "state": gpu_activity_state(
                    gpu["gpu_util"],
                    app_config.idle_max_gpu_util,
                    memory_used_mib=gpu["memory_used_mib"],
                    memory_total_mib=gpu["memory_total_mib"],
                    memory_free_mib=gpu["memory_free_mib"],
                    idle_min_free_mib=app_config.idle_min_free_mib,
                    has_processes=gpu_process_counts.get(gpu["index"], 0) > 0,
                ),
            }
            for gpu in gpu_rows
        ]
        status["processes"] = processes
        set_host_resources(collect_host_resources(server, app_config))
        status["reachable"] = True
        status["monitor_ok"] = True
        status["online"] = True
        return status
    except subprocess.TimeoutExpired:
        status["error"] = "timeout"
        apply_remote_reachability(status, server, app_config, default_error_kind="connection")
        set_host_resources(
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    except FileNotFoundError as exc:
        status["error"] = f"missing command: {exc.filename}"
        status["reachable"] = server.mode == "local"
        status["error_kind"] = "gpu_probe"
        set_host_resources(
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    except Exception as exc:  # noqa: BLE001 - keep API alive for one bad host.
        status["error"] = str(exc)
        apply_remote_reachability(status, server, app_config, default_error_kind="connection")
        set_host_resources(
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    finally:
        status["elapsed_ms"] = int((time.time() - started) * 1000)

def collect_server(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
    override = public_api_override("collect_server", collect_server)
    if override:
        return override(server, app_config)
    return _collect_server_impl(server, app_config)

def reusable_connection_failure_status(
    status: dict[str, Any] | None,
    now_ts: float | None = None,
    *,
    backoff_seconds: int = CONNECTION_REFRESH_BACKOFF_SECONDS,
) -> bool:
    if not isinstance(status, dict) or backoff_seconds <= 0:
        return False
    if status.get("online") or status.get("reachable"):
        return False
    if str(status.get("error_kind") or "") != "connection":
        return False
    collected_ts = parse_iso_timestamp(status.get("collected_at"))
    if collected_ts <= 0:
        return False
    return (now_ts if now_ts is not None else time.time()) - collected_ts < backoff_seconds

def mark_status_reused(status: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(status)
    payload["refresh_skipped"] = True
    payload["refresh_skip_reason"] = "connection_backoff"
    payload["refresh_skipped_at"] = now_iso()
    return payload

def collect_all(
    servers: list[ServerConfig],
    app_config: AppConfig,
    previous_statuses: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not servers:
        return []
    results: list[dict[str, Any]] = []
    previous_by_id = {
        str(item.get("id") or ""): item
        for item in (previous_statuses or [])
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    now_ts = time.time()
    workers = min(max(len(servers), 1), 8)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for server in servers:
            previous = previous_by_id.get(server.id)
            if server.enabled and reusable_connection_failure_status(previous, now_ts):
                results.append(mark_status_reused(previous))
                continue
            futures.append(pool.submit(collect_server, server, app_config))
        for future in as_completed(futures):
            results.append(future.result())
    order = {server.id: index for index, server in enumerate(servers)}
    results.sort(key=lambda item: order.get(item["id"], 9999))
    return results

def nvidia_smi_probe_script() -> str:
    return (
        f"nvidia-smi --query-gpu={shlex.quote(GPU_QUERY)} --format=csv,noheader,nounits"
    )

def nvidia_smi_output_looks_failed(text: str) -> bool:
    lowered = (text or "").lower()
    failure_markers = (
        "failed to initialize",
        "driver/library version mismatch",
        "nvml",
        "not found",
        "no devices were found",
        "unable to determine",
        "insufficient permissions",
    )
    return any(marker in lowered for marker in failure_markers)

def ssh_transport_output_looks_failed(text: str) -> bool:
    lowered = (text or "").lower()
    failure_markers = (
        "permission denied",
        "host key verification failed",
        "could not resolve hostname",
        "name or service not known",
        "temporary failure in name resolution",
        "no route to host",
        "connection refused",
        "connection timed out",
        "operation timed out",
        "connection closed",
        "connection reset",
        "kex_exchange_identification",
        "ssh_exchange_identification",
        "connection to host",
        "network is unreachable",
    )
    return any(marker in lowered for marker in failure_markers)
