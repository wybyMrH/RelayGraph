from __future__ import annotations

import csv
import getpass
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
from ...compat import public_api_override
from ...utils import *  # noqa: F403
from .process import percent
from .ssh import ssh_command
from ..web_terminal import set_terminal_winsize


def parse_csv_lines(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in csv.reader(text.splitlines()):
        if not row:
            continue
        rows.append([cell.strip() for cell in row])
    return rows

def parse_meminfo(text: str) -> dict[str, dict[str, Any]]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.strip().split()
        if not parts:
            continue
        value = safe_int(parts[0])
        if len(parts) > 1 and parts[1].lower() == "kb":
            value *= 1024
        values[key] = value

    memory_total = values.get("MemTotal", 0)
    memory_available = values.get("MemAvailable", values.get("MemFree", 0))
    memory_used = max(memory_total - memory_available, 0)
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    swap_used = max(swap_total - swap_free, 0)
    return {
        "memory": {
            "total_bytes": memory_total,
            "available_bytes": memory_available,
            "used_bytes": memory_used,
            "used_percent": percent(memory_used, memory_total),
        },
        "swap": {
            "total_bytes": swap_total,
            "free_bytes": swap_free,
            "used_bytes": swap_used,
            "used_percent": percent(swap_used, swap_total),
        },
    }

def parse_loadavg(text: str, cpu_count: int = 0) -> dict[str, Any]:
    parts = text.strip().split()
    load1 = safe_float(parts[0]) if len(parts) > 0 else 0.0
    load5 = safe_float(parts[1]) if len(parts) > 1 else 0.0
    load15 = safe_float(parts[2]) if len(parts) > 2 else 0.0
    running = 0
    total_processes = 0
    if len(parts) > 3 and "/" in parts[3]:
        running_text, total_text = parts[3].split("/", 1)
        running = safe_int(running_text)
        total_processes = safe_int(total_text)
    return {
        "load1": load1,
        "load5": load5,
        "load15": load15,
        "load_percent": percent(load1, cpu_count or 1),
        "running_processes": running,
        "processes": total_processes,
    }

def parse_cpu_times(text: str) -> tuple[int, int]:
    for line in text.splitlines():
        if not line.startswith("cpu "):
            continue
        values = [safe_int(item) for item in line.split()[1:]]
        if len(values) < 4:
            break
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        return total, idle
    return 0, 0

def cpu_utilization_percent(delay: float = 0.08) -> float:
    try:
        first_total, first_idle = parse_cpu_times(Path("/proc/stat").read_text(encoding="utf-8", errors="replace"))
        time.sleep(max(delay, 0))
        second_total, second_idle = parse_cpu_times(Path("/proc/stat").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return 0.0
    total_delta = second_total - first_total
    idle_delta = second_idle - first_idle
    if total_delta <= 0:
        return 0.0
    return round(max(total_delta - idle_delta, 0) * 100 / total_delta, 1)

def parse_proc_net_dev(text: str, max_interfaces: int = 8) -> dict[str, Any]:
    interfaces: list[dict[str, Any]] = []
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        name, values_text = line.split(":", 1)
        iface = name.strip()
        values = values_text.split()
        if iface == "lo" or len(values) < 16:
            continue
        rx_bytes = safe_int(values[0])
        tx_bytes = safe_int(values[8])
        interfaces.append(
            {
                "name": iface,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_packets": safe_int(values[1]),
                "tx_packets": safe_int(values[9]),
            }
        )
    interfaces.sort(key=lambda item: int(item.get("rx_bytes", 0)) + int(item.get("tx_bytes", 0)), reverse=True)
    selected = interfaces[:max_interfaces]
    return {
        "rx_bytes": sum(safe_int(item.get("rx_bytes")) for item in interfaces),
        "tx_bytes": sum(safe_int(item.get("tx_bytes")) for item in interfaces),
        "interfaces": selected,
    }

def host_mount_allowed(device: str, mount_point: str, fs_type: str) -> bool:
    if not mount_point or fs_type in PSEUDO_FS_TYPES:
        return False
    if mount_point != "/" and mount_point.startswith(PSEUDO_MOUNT_PREFIXES):
        return False
    if device in {"", "none", "tmpfs"}:
        return False
    return True

def disk_payload_for_mount(device: str, mount_point: str, fs_type: str) -> dict[str, Any] | None:
    try:
        stats = os.statvfs(mount_point)
    except OSError:
        return None
    total = int(stats.f_blocks * stats.f_frsize)
    if total <= 0:
        return None
    free = int(stats.f_bavail * stats.f_frsize)
    used = max(total - free, 0)
    inode_total = int(stats.f_files or 0)
    inode_free = int(stats.f_favail or 0)
    inode_used = max(inode_total - inode_free, 0) if inode_total else 0
    return {
        "mount": mount_point,
        "device": device,
        "fs_type": fs_type,
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": percent(used, total),
        "inode_total": inode_total,
        "inode_used": inode_used,
        "inode_free": inode_free,
        "inode_used_percent": percent(inode_used, inode_total),
    }

def collect_local_disks(max_disks: int = 8) -> list[dict[str, Any]]:
    try:
        mounts_text = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace")
    except OSError:
        mounts_text = ""
    seen: set[str] = set()
    disks: list[dict[str, Any]] = []
    for line in mounts_text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount_point, fs_type = parts[:3]
        mount_point = mount_point.replace("\\040", " ")
        if mount_point in seen or not host_mount_allowed(device, mount_point, fs_type):
            continue
        payload = disk_payload_for_mount(device, mount_point, fs_type)
        if not payload:
            continue
        seen.add(mount_point)
        disks.append(payload)
    disks.sort(key=lambda item: (0 if item.get("mount") == "/" else 1, -safe_int(item.get("total_bytes"))))
    return disks[:max_disks]

def collect_local_host_resources() -> dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    meminfo = parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace"))
    load = parse_loadavg(Path("/proc/loadavg").read_text(encoding="utf-8", errors="replace"), cpu_count=cpu_count)
    try:
        network = parse_proc_net_dev(Path("/proc/net/dev").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        network = {"rx_bytes": 0, "tx_bytes": 0, "interfaces": []}
    return {
        "ok": True,
        "source": "local",
        "collected_at": now_iso(),
        "current_user": getpass.getuser(),
        "current_uid": str(os.geteuid()),
        "cpu": {
            "cores": cpu_count,
            "util_percent": cpu_utilization_percent(),
            **load,
        },
        **meminfo,
        "disks": collect_local_disks(),
        "network": network,
    }

def remote_host_resource_probe_script() -> str:
    return r"""
import base64
import datetime
import getpass
import json
import os
import sys
import time

MARKER = sys.argv[1]
PSEUDO_FS_TYPES = {
    "autofs", "binfmt_misc", "bpf", "cgroup", "cgroup2", "configfs", "debugfs",
    "devpts", "devtmpfs", "efivarfs", "fusectl", "hugetlbfs", "mqueue", "nsfs",
    "overlay", "proc", "pstore", "rpc_pipefs", "securityfs", "sysfs", "tmpfs", "tracefs",
}
PSEUDO_MOUNT_PREFIXES = (
    "/dev", "/proc", "/run", "/snap", "/sys", "/var/lib/docker", "/var/lib/containers", "/var/lib/kubelet",
)

def safe_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default

def safe_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except Exception:
        return default

def pct(used, total):
    total = float(total or 0)
    if total <= 0:
        return 0.0
    return round(max(float(used or 0), 0.0) * 100 / total, 1)

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()

def parse_meminfo(text):
    values = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.strip().split()
        if not parts:
            continue
        value = safe_int(parts[0])
        if len(parts) > 1 and parts[1].lower() == "kb":
            value *= 1024
        values[key] = value
    memory_total = values.get("MemTotal", 0)
    memory_available = values.get("MemAvailable", values.get("MemFree", 0))
    memory_used = max(memory_total - memory_available, 0)
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    swap_used = max(swap_total - swap_free, 0)
    return {
        "memory": {
            "total_bytes": memory_total,
            "available_bytes": memory_available,
            "used_bytes": memory_used,
            "used_percent": pct(memory_used, memory_total),
        },
        "swap": {
            "total_bytes": swap_total,
            "free_bytes": swap_free,
            "used_bytes": swap_used,
            "used_percent": pct(swap_used, swap_total),
        },
    }

def parse_loadavg(text, cpu_count):
    parts = text.strip().split()
    load1 = safe_float(parts[0]) if len(parts) > 0 else 0.0
    load5 = safe_float(parts[1]) if len(parts) > 1 else 0.0
    load15 = safe_float(parts[2]) if len(parts) > 2 else 0.0
    running = 0
    total_processes = 0
    if len(parts) > 3 and "/" in parts[3]:
        running_text, total_text = parts[3].split("/", 1)
        running = safe_int(running_text)
        total_processes = safe_int(total_text)
    return {
        "load1": load1,
        "load5": load5,
        "load15": load15,
        "load_percent": pct(load1, cpu_count or 1),
        "running_processes": running,
        "processes": total_processes,
    }

def parse_cpu_times(text):
    for line in text.splitlines():
        if line.startswith("cpu "):
            values = [safe_int(item) for item in line.split()[1:]]
            if len(values) < 4:
                return 0, 0
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            return sum(values), idle
    return 0, 0

def cpu_util():
    first_total, first_idle = parse_cpu_times(read_text("/proc/stat"))
    time.sleep(0.08)
    second_total, second_idle = parse_cpu_times(read_text("/proc/stat"))
    total_delta = second_total - first_total
    idle_delta = second_idle - first_idle
    if total_delta <= 0:
        return 0.0
    return round(max(total_delta - idle_delta, 0) * 100 / total_delta, 1)

def mount_allowed(device, mount_point, fs_type):
    if not mount_point or fs_type in PSEUDO_FS_TYPES:
        return False
    if mount_point != "/" and mount_point.startswith(PSEUDO_MOUNT_PREFIXES):
        return False
    if device in ("", "none", "tmpfs"):
        return False
    return True

def disk_payload(device, mount_point, fs_type):
    try:
        stats = os.statvfs(mount_point)
    except OSError:
        return None
    total = int(stats.f_blocks * stats.f_frsize)
    if total <= 0:
        return None
    free = int(stats.f_bavail * stats.f_frsize)
    used = max(total - free, 0)
    inode_total = int(stats.f_files or 0)
    inode_free = int(stats.f_favail or 0)
    inode_used = max(inode_total - inode_free, 0) if inode_total else 0
    return {
        "mount": mount_point,
        "device": device,
        "fs_type": fs_type,
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": pct(used, total),
        "inode_total": inode_total,
        "inode_used": inode_used,
        "inode_free": inode_free,
        "inode_used_percent": pct(inode_used, inode_total),
    }

def collect_disks():
    disks = []
    seen = set()
    for line in read_text("/proc/mounts").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount_point, fs_type = parts[:3]
        mount_point = mount_point.replace("\\040", " ")
        if mount_point in seen or not mount_allowed(device, mount_point, fs_type):
            continue
        item = disk_payload(device, mount_point, fs_type)
        if item:
            seen.add(mount_point)
            disks.append(item)
    disks.sort(key=lambda item: (0 if item.get("mount") == "/" else 1, -safe_int(item.get("total_bytes"))))
    return disks[:8]

def parse_network():
    interfaces = []
    for line in read_text("/proc/net/dev").splitlines()[2:]:
        if ":" not in line:
            continue
        name, values_text = line.split(":", 1)
        iface = name.strip()
        values = values_text.split()
        if iface == "lo" or len(values) < 16:
            continue
        item = {
            "name": iface,
            "rx_bytes": safe_int(values[0]),
            "tx_bytes": safe_int(values[8]),
            "rx_packets": safe_int(values[1]),
            "tx_packets": safe_int(values[9]),
        }
        interfaces.append(item)
    interfaces.sort(key=lambda item: item["rx_bytes"] + item["tx_bytes"], reverse=True)
    return {
        "rx_bytes": sum(item["rx_bytes"] for item in interfaces),
        "tx_bytes": sum(item["tx_bytes"] for item in interfaces),
        "interfaces": interfaces[:8],
    }

cpu_count = os.cpu_count() or 1
payload = {
    "ok": True,
    "source": "ssh",
    "collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "current_user": getpass.getuser(),
    "current_uid": str(os.geteuid()),
    "cpu": {
        "cores": cpu_count,
        "util_percent": cpu_util(),
        **parse_loadavg(read_text("/proc/loadavg"), cpu_count),
    },
    **parse_meminfo(read_text("/proc/meminfo")),
    "disks": collect_disks(),
    "network": parse_network(),
}
encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(MARKER + "_BEGIN")
print(encoded)
print(MARKER + "_END")
"""

def collect_remote_host_resources(server: ServerConfig, timeout: int) -> dict[str, Any]:
    command = "python3 -c " + shlex.quote(remote_host_resource_probe_script()) + " " + shlex.quote(HOST_RESOURCE_MARKER)
    result = ssh_command(server, command, timeout=min(max(timeout, 1), 8))
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError((output.strip() or "远程主机资源采集失败")[-500:])
    payload = parse_remote_marked_json(output, HOST_RESOURCE_MARKER, label="主机资源")
    if not isinstance(payload, dict):
        raise ValueError("远程主机资源格式不是对象")
    payload["source"] = "ssh"
    return payload

def host_resource_error_payload(message: str, *, started: float | None = None) -> dict[str, Any]:
    payload = {
        "ok": False,
        "error": (message or "主机资源未采集")[-500:],
        "collected_at": now_iso(),
    }
    if started is not None:
        payload["elapsed_ms"] = int((time.time() - started) * 1000)
    return payload

def _collect_host_resources_impl(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
    started = time.time()
    try:
        payload = (
            collect_local_host_resources()
            if server.mode == "local"
            else collect_remote_host_resources(server, app_config.remote_timeout_seconds)
        )
        payload.setdefault("ok", True)
        payload.setdefault("collected_at", now_iso())
        payload["elapsed_ms"] = int((time.time() - started) * 1000)
        return payload
    except subprocess.TimeoutExpired:
        return host_resource_error_payload("timeout", started=started)
    except FileNotFoundError as exc:
        return host_resource_error_payload(f"missing command: {exc.filename}", started=started)
    except Exception as exc:  # noqa: BLE001 - host resource details should not break GPU polling.
        return host_resource_error_payload(str(exc), started=started)

def collect_host_resources(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
    override = public_api_override("collect_host_resources", collect_host_resources)
    if override:
        return override(server, app_config)
    return _collect_host_resources_impl(server, app_config)
