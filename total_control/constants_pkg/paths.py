"""Auto-split from constants.py — paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
DATA_DIR = Path(os.environ.get("TOTAL_CONTROL_DATA_DIR") or ROOT / "data").expanduser()
JOBS_PATH = DATA_DIR / "jobs.json"
WORKSPACES_PATH = DATA_DIR / "workspaces.json"
PROVIDER_PROFILES_PATH = DATA_DIR / "provider_profiles.json"
WORKFLOW_TEMPLATES_PATH = DATA_DIR / "workflow_templates.json"
AGENT_DEFINITIONS_PATH = DATA_DIR / "agent_definitions.json"
TOOL_DEFINITIONS_PATH = DATA_DIR / "tool_definitions.json"
LOG_DIR = DATA_DIR / "logs"
FILE_PREVIEW_CACHE_DIR = Path(
    os.environ.get("TOTAL_CONTROL_FILE_PREVIEW_CACHE_DIR") or "/tmp/total-control-file-preview"
).expanduser()
PREVIEW_CACHE_SETTINGS_PATH = DATA_DIR / "preview_cache_settings.json"
DEFAULT_PREVIEW_CACHE_SETTINGS = {
    "max_age_hours": 24,
    "max_size_mib": 512,
}
RUNTIME_STORAGE_SETTINGS_PATH = DATA_DIR / "runtime_storage_settings.json"
DEFAULT_RUNTIME_STORAGE_SETTINGS = {
    "preview_max_age_hours": 24,
    "preview_max_size_mib": 512,
    "log_max_age_hours": 168,
    "log_max_size_mib": 2048,
    "auto_cleanup_interval_minutes": 60,
    "remote_log_cleanup_enabled": True,
}
DEFAULT_CONFIG = ROOT / "config" / "servers.toml"

GPU_QUERY = (
    "index,uuid,name,memory.total,memory.used,utilization.gpu,"
    "temperature.gpu,power.draw,power.limit"
)
PROC_QUERY = "gpu_uuid,pid,process_name,used_memory"

TMUX_DEFAULT_COLUMNS = 240
TMUX_DEFAULT_ROWS = 80
TMUX_RESIZE_TIMEOUT_SECONDS = 2
HOST_RESOURCE_MARKER = "__TC_HOST_RESOURCES_JSON__"
REACHABILITY_PROBE_TIMEOUT_SECONDS = 2
CONNECTION_REFRESH_BACKOFF_SECONDS = 90

PSEUDO_FS_TYPES = {
    "autofs", "binfmt_misc", "bpf", "cgroup", "cgroup2", "configfs", "debugfs",
    "devpts", "devtmpfs", "efivarfs", "fusectl", "hugetlbfs", "mqueue", "nsfs",
    "overlay", "proc", "pstore", "rpc_pipefs", "securityfs", "sysfs", "tmpfs", "tracefs",
}
PSEUDO_MOUNT_PREFIXES = (
    "/dev", "/proc", "/run", "/snap", "/sys", "/var/lib/docker", "/var/lib/containers", "/var/lib/kubelet",
)
