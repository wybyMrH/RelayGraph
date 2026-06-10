from __future__ import annotations

import argparse
import base64
import copy
import csv
import fcntl
import fnmatch
import json
import mimetypes
import os
import pty
import re
import select
import shlex
import signal
import subprocess
import struct
import termios
import threading
import time
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from .preset_matrix import DEFAULT_DATA_ROOT as PRESET_DEFAULT_DATA_ROOT
from .preset_matrix import DEFAULT_PROJECT_DIR as PRESET_DEFAULT_PROJECT_DIR
from .preset_matrix import DEFAULT_REMOTE_PROJECT_DIR as PRESET_DEFAULT_REMOTE_PROJECT_DIR
from .preset_matrix import generate_experiments as generate_preset_experiments
from .preset_matrix import make_session_name as make_preset_session_name

from .llm_client import LLMClient, ChatMessage, LLMResponse
from .agent_executor import AgentExecutor, AgentExecutionResult, create_workspace_tool_executor


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
JOBS_PATH = DATA_DIR / "jobs.json"
WORKSPACES_PATH = DATA_DIR / "workspaces.json"
PROVIDER_PROFILES_PATH = DATA_DIR / "provider_profiles.json"
WORKFLOW_TEMPLATES_PATH = DATA_DIR / "workflow_templates.json"
AGENT_DEFINITIONS_PATH = DATA_DIR / "agent_definitions.json"
TOOL_DEFINITIONS_PATH = DATA_DIR / "tool_definitions.json"
LOG_DIR = DATA_DIR / "logs"
FILE_PREVIEW_CACHE_DIR = Path("/tmp/total-control-file-preview")
PREVIEW_CACHE_SETTINGS_PATH = DATA_DIR / "preview_cache_settings.json"
DEFAULT_PREVIEW_CACHE_SETTINGS = {
    "max_age_hours": 24,
    "max_size_mib": 512,
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

WORKSPACE_NODE_LIBRARY: dict[str, dict[str, Any]] = {
    "source.repo": {
        "title": "仓库输入",
        "category": "source",
        "config_defaults": {
            "repo_url": "",
            "repo_ref": "",
        },
    },
    "source.paper": {
        "title": "论文输入",
        "category": "source",
        "config_defaults": {
            "paper_url": "",
        },
    },
    "source.idea": {
        "title": "想法输入",
        "category": "source",
        "config_defaults": {
            "idea_text": "",
        },
    },
    "research.search": {
        "title": "检索资料",
        "category": "research",
        "config_defaults": {
            "query": "",
            "goal": "",
            "repo_url": "",
            "paper_url": "",
        },
    },
    "repo.clone": {
        "title": "克隆仓库",
        "category": "repo",
        "config_defaults": {
            "repo_url": "",
            "repo_ref": "",
            "workspace_dir": "",
        },
    },
    "path.resolve": {
        "title": "解析路径",
        "category": "path",
        "config_defaults": {
            "workspace_dir": "",
            "data_roots": "",
            "output_roots": "runs\noutputs\ncheckpoints\nlogs",
        },
    },
    "repo.inspect": {
        "title": "检查仓库",
        "category": "repo",
        "config_defaults": {
            "workspace_dir": "",
            "focus_paths": "",
            "questions": "",
        },
    },
    "dataset.find": {
        "title": "发现数据集",
        "category": "data",
        "config_defaults": {
            "query": "",
            "dataset_hints": "",
            "data_roots": "",
            "expected_layout": "",
        },
    },
    "env.infer": {
        "title": "推断环境",
        "category": "env",
        "config_defaults": {
            "workspace_dir": "",
            "manifest_paths": "requirements.txt, pyproject.toml, environment.yml, setup.py",
            "env_name": "",
            "python_version": "",
        },
    },
    "env.prepare": {
        "title": "准备环境",
        "category": "env",
        "config_defaults": {
            "workspace_dir": "",
            "env_name": "",
            "env_manager": "conda",
            "python_version": "",
            "setup_command": "",
        },
    },
    "gpu.allocate": {
        "title": "分配 GPU",
        "category": "gpu",
        "config_defaults": {
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "notes": "",
        },
    },
    "run.command": {
        "title": "运行任务",
        "category": "run",
        "config_defaults": {
            "workspace_dir": "",
            "env_name": "",
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "run_command": "",
            "schedule": "",
        },
    },
    "artifact.collect": {
        "title": "收集产物",
        "category": "artifact",
        "config_defaults": {
            "workspace_dir": "",
            "artifact_paths": "runs\noutputs\ncheckpoints\nlogs",
            "metric_paths": "",
            "notes": "",
        },
    },
    "eval.report": {
        "title": "结果整理",
        "category": "eval",
        "config_defaults": {
            "report_command": "",
            "metric_paths": "",
            "notes": "",
        },
    },
    "notify.user": {
        "title": "通知用户",
        "category": "notify",
        "config_defaults": {
            "channel": "ui",
            "message": "",
        },
    },
    "custom.step": {
        "title": "自定义步骤",
        "category": "custom",
        "config_defaults": {
            "goal": "",
            "command": "",
            "output_expectation": "",
        },
    },
}

WORKSPACE_SOURCE_NODE_TYPES = {"source.repo", "source.paper", "source.idea"}
DEFAULT_WORKFLOW_TEMPLATE_IDS = {"repo-default-flow", "paper-default-flow", "idea-default-flow"}
WORKSPACE_EXECUTABLE_NODE_KINDS = {
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
}
WORKSPACE_DISCOVERY_NODE_KINDS = {
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "gpu.allocate",
    "artifact.collect",
}
WORKSPACE_NO_CWD_NODE_KINDS = {
    "path.resolve",
    "dataset.find",
    "env.infer",
    "gpu.allocate",
    "artifact.collect",
}
WORKSPACE_NODE_IO_CONTRACTS: dict[str, dict[str, Any]] = {
    "source.repo": {
        "inputs": ["目标", "仓库 URL", "分支 / 提交"],
        "output_key": "source_repo",
        "evidence": "仓库来源、版本和启动目标",
    },
    "source.paper": {
        "inputs": ["目标", "论文 / 资料", "参考线索"],
        "output_key": "paper_context",
        "evidence": "论文、任务和候选实现线索",
    },
    "source.idea": {
        "inputs": ["目标描述", "约束", "成功标准"],
        "output_key": "idea_brief",
        "evidence": "需求、约束和验收标准",
    },
    "research.search": {
        "inputs": ["source_context", "论文 / 资料", "参考线索"],
        "output_key": "research_brief",
        "evidence": "候选 repo、issue、论文和资料结论",
    },
    "repo.clone": {
        "inputs": ["source_repo", "repo_url", "repo_ref"],
        "output_key": "repo_checkout",
        "evidence": "本地仓库路径、分支和提交",
    },
    "path.resolve": {
        "inputs": ["repo_checkout", "工作目录", "数据 / 输出线索"],
        "output_key": "path_map",
        "evidence": "工作目录、数据目录、输出目录和日志目录",
    },
    "repo.inspect": {
        "inputs": ["repo_checkout", "path_map"],
        "output_key": "repo_profile",
        "evidence": "入口脚本、依赖文件、默认参数和结果目录",
    },
    "dataset.find": {
        "inputs": ["paper_context", "repo_profile", "数据集 / 路径线索"],
        "output_key": "dataset_profile",
        "evidence": "数据集名称、本地路径候选和结构要求",
    },
    "env.infer": {
        "inputs": ["repo_profile", "path_map"],
        "output_key": "env_requirements",
        "evidence": "Python/CUDA/依赖文件和安装建议",
    },
    "env.prepare": {
        "inputs": ["env_requirements", "setup_command"],
        "output_key": "env_ready",
        "evidence": "环境名、安装命令、依赖检查结果",
    },
    "gpu.allocate": {
        "inputs": ["env_ready", "run_profile", "GPU 快照"],
        "output_key": "gpu_allocation",
        "evidence": "目标服务器、GPU 编号、显存和调度策略",
    },
    "run.command": {
        "inputs": ["repo_profile", "dataset_profile", "env_ready", "gpu_allocation"],
        "output_key": "run_result",
        "evidence": "任务 ID、命令、日志、退出状态和运行路径",
    },
    "artifact.collect": {
        "inputs": ["run_result", "path_map"],
        "output_key": "artifact_manifest",
        "evidence": "日志、指标、模型文件和复跑命令",
    },
    "eval.report": {
        "inputs": ["artifact_manifest", "run_result"],
        "output_key": "evaluation_report",
        "evidence": "指标、结论、失败原因和下一步建议",
    },
}

DEFAULT_WORKSPACE_TOOLS: list[dict[str, Any]] = [
    {
        "id": "workflow.plan",
        "label": "工作流规划",
        "category": "workflow",
        "capability": "write",
        "description": "拆分目标、编排节点、补交接说明。",
        "enabled": True,
    },
    {
        "id": "workflow.edit",
        "label": "工作流编辑",
        "category": "workflow",
        "capability": "control",
        "description": "新增、移动、删除或重排工作流节点。",
        "enabled": True,
    },
    {
        "id": "web.search",
        "label": "网络检索",
        "category": "research",
        "capability": "read",
        "description": "搜索论文、repo、issue、文档和公开说明。",
        "enabled": True,
    },
    {
        "id": "repo.search",
        "label": "仓库搜寻",
        "category": "research",
        "capability": "read",
        "description": "围绕关键字找候选仓库、star、issue 和镜像。",
        "enabled": True,
    },
    {
        "id": "repo.clone",
        "label": "仓库克隆",
        "category": "repo",
        "capability": "execute",
        "description": "把仓库拉到目标工作目录。",
        "enabled": True,
    },
    {
        "id": "repo.read",
        "label": "仓库阅读",
        "category": "repo",
        "capability": "read",
        "description": "读取源码、README、配置和入口说明。",
        "enabled": True,
    },
    {
        "id": "repo.inspect",
        "label": "仓库检查",
        "category": "repo",
        "capability": "read",
        "description": "扫描依赖、入口、默认参数和输出目录。",
        "enabled": True,
    },
    {
        "id": "path.resolve",
        "label": "路径解析",
        "category": "path",
        "capability": "read",
        "description": "确认工作目录、数据目录、日志目录和输出路径。",
        "enabled": True,
    },
    {
        "id": "dataset.find",
        "label": "数据集发现",
        "category": "data",
        "capability": "read",
        "description": "从论文、README、线索和本地数据盘定位数据集。",
        "enabled": True,
    },
    {
        "id": "file.browse",
        "label": "文件浏览",
        "category": "file",
        "capability": "read",
        "description": "浏览本地或远端目录树。",
        "enabled": True,
    },
    {
        "id": "file.read",
        "label": "文件预览",
        "category": "file",
        "capability": "read",
        "description": "读取文本、日志和配置文件的片段。",
        "enabled": True,
    },
    {
        "id": "dir.scan",
        "label": "目录扫描",
        "category": "host",
        "capability": "read",
        "description": "查看可用工作目录、挂载盘和项目目录。",
        "enabled": True,
    },
    {
        "id": "host.exec",
        "label": "主机执行",
        "category": "host",
        "capability": "execute",
        "description": "在目标主机上运行检查、命令和维护脚本。",
        "enabled": True,
    },
    {
        "id": "gpu.inspect",
        "label": "GPU 探测",
        "category": "gpu",
        "capability": "read",
        "description": "查询可用显卡、利用率、显存和温度。",
        "enabled": True,
    },
    {
        "id": "gpu.allocate",
        "label": "GPU 选择",
        "category": "gpu",
        "capability": "control",
        "description": "为任务挑选空闲或最合适的显卡。",
        "enabled": True,
    },
    {
        "id": "env.inspect",
        "label": "环境检查",
        "category": "env",
        "capability": "read",
        "description": "检查 conda、python3、tmux、rsync 等依赖。",
        "enabled": True,
    },
    {
        "id": "env.infer",
        "label": "环境推断",
        "category": "env",
        "capability": "read",
        "description": "从依赖文件、README 和运行脚本推断安装步骤。",
        "enabled": True,
    },
    {
        "id": "env.prepare",
        "label": "环境准备",
        "category": "env",
        "capability": "execute",
        "description": "创建或激活 conda / venv 并安装依赖。",
        "enabled": True,
    },
    {
        "id": "env.create",
        "label": "环境创建",
        "category": "env",
        "capability": "execute",
        "description": "初始化新的 Python 环境与基础依赖。",
        "enabled": True,
    },
    {
        "id": "job.run",
        "label": "任务提交",
        "category": "run",
        "capability": "execute",
        "description": "把命令提交到任务中心并落到 tmux 后台。",
        "enabled": True,
    },
    {
        "id": "job.stop",
        "label": "任务停止",
        "category": "run",
        "capability": "control",
        "description": "停止正在运行的任务或进程。",
        "enabled": True,
    },
    {
        "id": "job.reorder",
        "label": "队列重排",
        "category": "run",
        "capability": "control",
        "description": "调整等待中任务的优先顺序。",
        "enabled": True,
    },
    {
        "id": "execution.package",
        "label": "执行包读取",
        "category": "run",
        "capability": "read",
        "description": "读取当前执行包、调度目标、缺口、回填建议和复跑脚本摘要。",
        "enabled": True,
    },
    {
        "id": "log.read",
        "label": "日志读取",
        "category": "log",
        "capability": "read",
        "description": "读取任务日志、输出和 tmux 片段。",
        "enabled": True,
    },
    {
        "id": "artifact.read",
        "label": "产物读取",
        "category": "artifact",
        "capability": "read",
        "description": "查看项目产物、指标和中间结果。",
        "enabled": True,
    },
    {
        "id": "artifact.collect",
        "label": "产物收集",
        "category": "artifact",
        "capability": "read",
        "description": "收集日志、指标、模型文件和复跑命令。",
        "enabled": True,
    },
    {
        "id": "artifact.write",
        "label": "产物写入",
        "category": "artifact",
        "capability": "write",
        "description": "写入整理后的结论、摘要和检查点。",
        "enabled": True,
    },
    {
        "id": "report.write",
        "label": "结果报告",
        "category": "artifact",
        "capability": "write",
        "description": "输出评估报告、对比摘要和下一步建议。",
        "enabled": True,
    },
    {
        "id": "notify.user",
        "label": "用户通知",
        "category": "notify",
        "capability": "write",
        "description": "把关键结论、失败原因或待确认项推回给用户。",
        "enabled": True,
    },
    {
        "id": "chat.write",
        "label": "项目对话",
        "category": "chat",
        "capability": "write",
        "description": "把自然语言输入写入项目上下文与对话历史。",
        "enabled": True,
    },
    {
        "id": "schedule.plan",
        "label": "调度规划",
        "category": "workflow",
        "capability": "write",
        "description": "记录定时运行、批量 sweep 和重复执行计划。",
        "enabled": True,
    },
]


class WorkspaceWorkflowReadinessError(ValueError):
    def __init__(
        self,
        message: str,
        blocked_checks: list[dict[str, Any]] | None = None,
        *,
        workspace: dict[str, Any] | None = None,
        applied: list[dict[str, Any]] | None = None,
        evidence_applied: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.blocked_checks = blocked_checks or []
        self.workspace = workspace
        self.applied = applied or []
        self.evidence_applied = evidence_applied or []

DEFAULT_WORKSPACE_AGENTS: list[dict[str, Any]] = [
    {
        "id": "planner",
        "name": "Planner",
        "role": "planner",
        "prompt": "把用户目标整理成可执行节点和审批点。",
        "tools": ["workflow.edit", "workflow.plan", "execution.package", "artifact.write", "chat.write"],
        "provider_profile_id": "",
    },
    {
        "id": "researcher",
        "name": "Researcher",
        "role": "researcher",
        "prompt": "检索论文、repo、issue、文档和候选方案。",
        "tools": ["web.search", "repo.search", "dataset.find", "artifact.read", "artifact.write"],
        "provider_profile_id": "",
    },
    {
        "id": "repo-scout",
        "name": "Repo Scout",
        "role": "repo_scout",
        "prompt": "理解仓库结构、依赖、入口和运行方式。",
        "tools": ["repo.clone", "repo.read", "repo.inspect", "path.resolve", "file.read"],
        "provider_profile_id": "",
    },
    {
        "id": "gpu-scout",
        "name": "GPU Scout",
        "role": "gpu_scout",
        "prompt": "找可用显卡、判断忙碌程度并给出可运行的主机。",
        "tools": ["gpu.inspect", "gpu.allocate", "host.exec", "dir.scan"],
        "provider_profile_id": "",
    },
    {
        "id": "env-builder",
        "name": "Env Builder",
        "role": "env_builder",
        "prompt": "准备环境、检查依赖并整理安装步骤。",
        "tools": ["env.inspect", "env.infer", "env.prepare", "env.create", "host.exec"],
        "provider_profile_id": "",
    },
    {
        "id": "runner",
        "name": "Runner",
        "role": "runner",
        "prompt": "把运行配方转换为实际任务并跟踪输出。",
        "tools": ["execution.package", "job.run", "job.stop", "job.reorder", "gpu.allocate", "log.read"],
        "provider_profile_id": "",
    },
    {
        "id": "evaluator",
        "name": "Evaluator",
        "role": "evaluator",
        "prompt": "解析结果、指标、产出文件和回归结论。",
        "tools": ["execution.package", "artifact.collect", "artifact.read", "log.read", "report.write", "notify.user"],
        "provider_profile_id": "",
    },
    {
        "id": "watcher",
        "name": "Watcher",
        "role": "watcher",
        "prompt": "监控运行异常、卡住的任务和日志里的错误信号。",
        "tools": ["log.read", "job.stop", "notify.user", "artifact.write"],
        "provider_profile_id": "",
    },
    {
        "id": "reporter",
        "name": "Reporter",
        "role": "reporter",
        "prompt": "把过程、结果和下一步建议整理成可分享的总结。",
        "tools": ["execution.package", "artifact.read", "artifact.write", "report.write", "chat.write"],
        "provider_profile_id": "",
    },
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def iso_at(timestamp: float) -> str:
    if timestamp <= 0:
        return ""
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def human_file_size(size: int) -> str:
    value = float(max(size, 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def file_browser_roots() -> list[dict[str, str]]:
    roots: list[tuple[str, Path]] = [
        ("项目", ROOT),
        ("Home", Path.home()),
        ("临时目录", Path("/tmp")),
    ]
    mnt = Path("/mnt")
    if mnt.exists():
        for child in sorted(mnt.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                roots.append((f"{child.name.upper()} 盘", child))
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for label, path in roots:
        try:
            resolved = str(path.expanduser().resolve())
        except OSError:
            continue
        if resolved in seen or not Path(resolved).exists():
            continue
        seen.add(resolved)
        result.append({"label": label, "path": resolved})
    return result


def file_browser_allowed(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    allowed_roots = [ROOT.resolve(), Path.home().resolve(), Path("/tmp").resolve()]
    if Path("/mnt").exists():
        allowed_roots.append(Path("/mnt").resolve())
    return any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots)


def file_entry(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        is_dir = path.is_dir()
        size = 0 if is_dir else int(stat.st_size)
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    except OSError:
        is_dir = path.is_dir()
        size = 0
        mtime = ""
    return {
        "name": path.name or str(path),
        "path": str(path),
        "is_dir": is_dir,
        "size": size,
        "size_text": "" if is_dir else human_file_size(size),
        "mtime": mtime,
    }


def resolve_local_browser_target(path_text: str = "") -> Path:
    if path_text:
        target = Path(path_text).expanduser()
    else:
        target = ROOT
    if not target.is_absolute():
        target = (ROOT / target).resolve()
    try:
        target = target.resolve()
    except OSError as exc:
        raise ValueError(f"路径不可访问：{path_text}") from exc
    if not file_browser_allowed(target):
        raise ValueError("只能浏览项目目录、Home、/tmp 或 /mnt 下的本机路径")
    if not target.exists():
        raise ValueError(f"路径不存在：{target}")
    return target


def browse_local_files(path_text: str = "", max_entries: int = 300, dirs_only: bool = False) -> dict[str, Any]:
    roots = file_browser_roots()
    target = resolve_local_browser_target(path_text)
    selected = file_entry(target)
    directory = target if target.is_dir() else target.parent
    entries: list[dict[str, Any]] = []
    limit = max(10, min(max_entries, 1000))
    if directory.exists() and directory.is_dir():
        try:
            children = list(directory.iterdir())
        except OSError as exc:
            raise ValueError(f"目录不可读取：{directory}") from exc
        if dirs_only:
            children = [child for child in children if child.is_dir()]
        children.sort(key=lambda item: (not item.is_dir(), item.name.lower()))
        for child in children[:limit]:
            entries.append(file_entry(child))
    parent = directory.parent if directory.parent != directory and file_browser_allowed(directory.parent) else None
    return {
        "roots": roots,
        "path": str(directory),
        "selected": selected,
        "parent": str(parent) if parent else "",
        "entries": entries,
        "truncated": len(children) > limit if directory.exists() and directory.is_dir() else False,
    }


def clamp_file_preview_limit(limit: Any, default: int = 131072) -> int:
    value = safe_int(limit, default)
    if value <= 0:
        value = default
    return max(1, min(value, 2_000_000))


def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    sample = data[:4096]
    control = sum(1 for byte in sample if byte < 32 and byte not in (9, 10, 13))
    return control / max(len(sample), 1) > 0.3


def decode_text_preview(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            text = data.decode(encoding)
            return text, "utf-8" if encoding == "utf-8-sig" else encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8"


def build_text_preview_payload(path: str, data: bytes, *, truncated: bool, server_id: str) -> dict[str, Any]:
    if is_probably_binary(data):
        raise ValueError("暂不预览二进制文件，请选择文本、日志、脚本或配置文件。")
    text, encoding = decode_text_preview(data)
    return {
        "path": path,
        "server_id": server_id,
        "text": text,
        "truncated": truncated,
        "encoding": encoding,
    }


TEXT_PREVIEW_SUFFIXES = {
    ".bat",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".dockerfile",
    ".env",
    ".err",
    ".go",
    ".h",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".ipynb",
    ".java",
    ".js",
    ".json",
    ".jsonc",
    ".jsx",
    ".kt",
    ".less",
    ".log",
    ".lua",
    ".md",
    ".mjs",
    ".out",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".sass",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".svg",
    ".swift",
    ".toml",
    ".ts",
    ".tsv",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}

TEXT_PREVIEW_BASENAMES = {
    "dockerfile",
    "makefile",
    "gemfile",
    "rakefile",
    "procfile",
    "license",
    "readme",
    "changelog",
    "authors",
    "contributing",
    "copying",
    "notice",
}


def guess_file_mime_type(path_text: str) -> str:
    mime_type, _ = mimetypes.guess_type(path_text)
    return mime_type or "application/octet-stream"


def preview_kind_for_path(path_text: str, mime_type: str = "") -> str:
    path = Path(str(path_text or ""))
    suffix = path.suffix.lower()
    name = path.name.lower()
    kind = str(mime_type or guess_file_mime_type(path_text)).lower()
    if suffix in TEXT_PREVIEW_SUFFIXES:
        return "text"
    if name in TEXT_PREVIEW_BASENAMES:
        return "text"
    if name.startswith(".") and len(name) > 1:
        return "text"
    if kind in {"text/html", "application/xhtml+xml", "image/svg+xml"}:
        return "text"
    if kind.startswith("text/"):
        return "text"
    if kind.startswith("image/"):
        return "image"
    if kind == "application/pdf":
        return "pdf"
    if kind.startswith("audio/"):
        return "audio"
    if kind.startswith("video/"):
        return "video"
    return "binary"


def read_local_text_file(path_text: str = "", limit_bytes: int = 131072) -> dict[str, Any]:
    target = resolve_local_browser_target(path_text)
    if target.is_dir():
        raise ValueError("当前路径是目录，请选择文件。")
    limit = clamp_file_preview_limit(limit_bytes)
    try:
        with target.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as exc:
        raise ValueError(f"文件不可读取：{target}") from exc
    truncated = len(raw) > limit
    return build_text_preview_payload(
        str(target),
        raw[:limit],
        truncated=truncated,
        server_id="local",
    )


def parse_remote_marked_json(output: str, marker: str, *, label: str) -> dict[str, Any]:
    start_marker = f"{marker}_BEGIN"
    end_marker = f"{marker}_END"
    start_index = output.rfind(start_marker)
    if start_index < 0:
        raise ValueError((output.strip() or f"远程{label}没有返回结果标记")[-1000:])
    start_index += len(start_marker)
    end_index = output.find(end_marker, start_index)
    if end_index < 0:
        raise ValueError((output.strip() or f"远程{label}没有返回结束标记")[-1000:])
    encoded = "".join(line.strip() for line in output[start_index:end_index].splitlines()).strip()
    if not encoded:
        raise ValueError(f"远程{label}返回为空。")
    try:
        raw = base64.b64decode(encoded)
    except Exception as exc:  # noqa: BLE001 - surface parsing issue to UI
        raise ValueError(f"远程{label}编码损坏：{exc}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"远程{label}格式损坏：{exc}") from exc


def browse_remote_files(
    server: ServerConfig,
    path_text: str = "",
    max_entries: int = 300,
    dirs_only: bool = False,
    timeout: int = 8,
) -> dict[str, Any]:
    marker = "__TC_FILE_BROWSE_JSON__"
    script = r"""
import base64
import datetime
import json
import os
import pathlib
import sys

marker = sys.argv[1]
path_text = sys.argv[2] if len(sys.argv) > 2 else ""
max_entries = int(sys.argv[3]) if len(sys.argv) > 3 else 300
dirs_only = (sys.argv[4] if len(sys.argv) > 4 else "0") == "1"
target = pathlib.Path(os.path.expanduser(path_text or "~"))
try:
    target = target.resolve()
except OSError:
    target = target.absolute()
if not target.exists():
    raise SystemExit(f"路径不存在：{target}")

def human_size(size):
    value = float(max(int(size), 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024

def entry(path):
    try:
        stat = path.stat()
        is_dir = path.is_dir()
        size = 0 if is_dir else int(stat.st_size)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    except OSError:
        is_dir = path.is_dir()
        size = 0
        mtime = ""
    return {
        "name": path.name or str(path),
        "path": str(path),
        "is_dir": is_dir,
        "size": size,
        "size_text": "" if is_dir else human_size(size),
        "mtime": mtime,
    }

selected = entry(target)
directory = target if target.is_dir() else target.parent
try:
    children = list(directory.iterdir()) if directory.exists() and directory.is_dir() else []
except OSError as exc:
    raise SystemExit(f"目录不可读取：{directory}: {exc}")
if dirs_only:
    children = [child for child in children if child.is_dir()]
children.sort(key=lambda item: (not item.is_dir(), item.name.lower()))
limit = max(10, min(max_entries, 1000))
home = pathlib.Path.home()
roots = [
    {"label": "Home", "path": str(home)},
    {"label": "根目录", "path": "/"},
    {"label": "临时目录", "path": "/tmp"},
]
payload = {
    "roots": roots,
    "path": str(directory),
    "selected": selected,
    "parent": str(directory.parent) if directory.parent != directory else "",
    "entries": [entry(child) for child in children[:limit]],
    "truncated": len(children) > limit,
}
encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(marker + "_BEGIN")
print(encoded)
print(marker + "_END")
"""
    command = (
        "python3 -c "
        + shlex.quote(script)
        + " "
        + shlex.quote(marker)
        + " "
        + shlex.quote(path_text or "")
        + " "
        + shlex.quote(str(max_entries))
        + " "
        + ("1" if dirs_only else "0")
    )
    result = ssh_command(server, command, timeout=timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError(output.strip() or "远程目录读取失败")
    return parse_remote_marked_json(output, marker, label="目录读取结果")


def read_remote_text_file(
    server: ServerConfig,
    path_text: str = "",
    limit_bytes: int = 131072,
    timeout: int = 8,
) -> dict[str, Any]:
    marker = "__TC_FILE_READ_JSON__"
    limit = clamp_file_preview_limit(limit_bytes)
    script = r"""
import base64
import json
import os
import pathlib
import sys

marker = sys.argv[1]
path_text = sys.argv[2] if len(sys.argv) > 2 else ""
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 131072
target = pathlib.Path(os.path.expanduser(path_text or "~"))
try:
    target = target.resolve()
except OSError:
    target = target.absolute()
if not target.exists():
    raise SystemExit(f"路径不存在：{target}")
if target.is_dir():
    raise SystemExit("当前路径是目录，请选择文件。")

with target.open("rb") as handle:
    raw = handle.read(limit + 1)
truncated = len(raw) > limit
data = raw[:limit]

if b"\x00" in data:
    raise SystemExit("暂不预览二进制文件，请选择文本、日志、脚本或配置文件。")
sample = data[:4096]
control = sum(1 for byte in sample if byte < 32 and byte not in (9, 10, 13))
if sample and control / len(sample) > 0.3:
    raise SystemExit("暂不预览二进制文件，请选择文本、日志、脚本或配置文件。")

text = None
encoding = ""
for candidate in ("utf-8", "utf-8-sig", "gb18030"):
    try:
        text = data.decode(candidate)
        encoding = "utf-8" if candidate == "utf-8-sig" else candidate
        break
    except UnicodeDecodeError:
        continue
if text is None:
    text = data.decode("utf-8", errors="replace")
    encoding = "utf-8"

payload = {
    "path": str(target),
    "text": text,
    "truncated": truncated,
    "encoding": encoding,
}
encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(marker + "_BEGIN")
print(encoded)
print(marker + "_END")
"""
    command = (
        "python3 -c "
        + shlex.quote(script)
        + " "
        + shlex.quote(marker)
        + " "
        + shlex.quote(path_text or "")
        + " "
        + shlex.quote(str(limit))
    )
    result = ssh_command(server, command, timeout=timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError(output.strip() or "远程文件读取失败")
    payload = parse_remote_marked_json(output, marker, label="文件预览结果")
    payload["server_id"] = server.id
    return payload


def safe_id(value: str) -> str:
    cleaned = []
    for char in value.strip():
        if char.isalnum() or char in ("-", "_", "."):
            cleaned.append(char)
        else:
            cleaned.append("-")
    result = "".join(cleaned).strip("-._")
    return result or "server"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if text.lower() in {"n/a", "[not supported]", "not supported", ""}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def preview_cache_root() -> Path:
    return FILE_PREVIEW_CACHE_DIR.resolve()


def is_under_preview_cache(path: Path | str) -> bool:
    try:
        Path(path).expanduser().resolve().relative_to(preview_cache_root())
        return True
    except (ValueError, OSError):
        return False


def normalize_preview_cache_settings(raw: Any) -> dict[str, int]:
    data = raw if isinstance(raw, dict) else {}
    max_age_hours = max(0, safe_int(data.get("max_age_hours"), DEFAULT_PREVIEW_CACHE_SETTINGS["max_age_hours"]))
    max_size_mib = max(0, safe_int(data.get("max_size_mib"), DEFAULT_PREVIEW_CACHE_SETTINGS["max_size_mib"]))
    return {"max_age_hours": max_age_hours, "max_size_mib": max_size_mib}


def load_preview_cache_settings() -> dict[str, int]:
    return normalize_preview_cache_settings(read_json(PREVIEW_CACHE_SETTINGS_PATH, DEFAULT_PREVIEW_CACHE_SETTINGS))


def save_preview_cache_settings(settings: dict[str, Any]) -> dict[str, int]:
    normalized = normalize_preview_cache_settings(settings)
    write_json(PREVIEW_CACHE_SETTINGS_PATH, normalized)
    return normalized


def iter_preview_cache_dirs() -> list[dict[str, Any]]:
    root = preview_cache_root()
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir() or not is_under_preview_cache(child):
            continue
        try:
            size = sum(item.stat().st_size for item in child.rglob("*") if item.is_file())
            stat = child.stat()
        except OSError:
            continue
        entries.append({"path": child, "size": size, "mtime": stat.st_mtime})
    return entries


def preview_cache_disk_stats() -> dict[str, Any]:
    entries = iter_preview_cache_dirs()
    total_bytes = sum(int(item["size"]) for item in entries)
    return {
        "cache_dir": str(preview_cache_root()),
        "entry_count": len(entries),
        "total_bytes": total_bytes,
        "total_text": format_size_text(total_bytes),
    }


def cleanup_preview_cache(
    *,
    max_age_hours: int = 0,
    max_size_mib: int = 0,
    remove_all: bool = False,
) -> dict[str, Any]:
    import shutil

    entries = iter_preview_cache_dirs()
    to_remove: list[dict[str, Any]] = []
    if remove_all:
        to_remove = list(entries)
    else:
        now = time.time()
        remaining = list(entries)
        if max_age_hours > 0:
            cutoff = now - max_age_hours * 3600
            expired = [item for item in remaining if float(item["mtime"]) < cutoff]
            to_remove.extend(expired)
            remaining = [item for item in remaining if item not in expired]
        if max_size_mib > 0:
            limit_bytes = max_size_mib * 1024 * 1024
            total_bytes = sum(int(item["size"]) for item in remaining)
            for item in sorted(remaining, key=lambda row: float(row["mtime"])):
                if total_bytes <= limit_bytes:
                    break
                if item in to_remove:
                    continue
                to_remove.append(item)
                total_bytes -= int(item["size"])

    removed_count = 0
    removed_bytes = 0
    for item in to_remove:
        path = Path(item["path"])
        if not is_under_preview_cache(path):
            continue
        removed_bytes += int(item["size"])
        shutil.rmtree(path, ignore_errors=True)
        removed_count += 1
    remaining_entries = iter_preview_cache_dirs()
    remaining_bytes = sum(int(item["size"]) for item in remaining_entries)
    return {
        "removed_count": removed_count,
        "removed_bytes": removed_bytes,
        "removed_text": format_size_text(removed_bytes),
        "remaining_count": len(remaining_entries),
        "remaining_bytes": remaining_bytes,
        "remaining_text": format_size_text(remaining_bytes),
    }


def format_size_text(value: int) -> str:
    size = max(0, int(value or 0))
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(size)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if amount < 1024 or candidate == units[-1]:
            break
        amount /= 1024
    if unit == "B":
        return f"{int(amount)} {unit}"
    return f"{amount:.1f} {unit}"


def repo_name_from_url(url: str) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    tail = text.rsplit("/", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail.strip()


def parse_tag_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        tags.append(text)
    return tags


def parse_line_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").splitlines()
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def workspace_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("updated_at") or ""),
        str(item.get("created_at") or ""),
        str(item.get("id") or ""),
    )


def normalize_workspace_recipe(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    recipe_id = str(payload.get("recipe_id") or current.get("id") or "default").strip() or "default"
    name = str(payload.get("recipe_name") or current.get("name") or "默认运行").strip() or "默认运行"
    return {
        "id": safe_id(recipe_id),
        "name": name,
        "setup_command": str(payload.get("setup_command") or current.get("setup_command") or "").strip(),
        "run_command": str(payload.get("run_command") or current.get("run_command") or "").strip(),
        "report_command": str(payload.get("report_command") or current.get("report_command") or "").strip(),
        "schedule": str(payload.get("schedule") or current.get("schedule") or "").strip(),
        "notes": str(payload.get("recipe_notes") or current.get("notes") or "").strip(),
        "enabled": bool(payload.get("recipe_enabled", current.get("enabled", True))),
    }


def workspace_node_definition(kind: str) -> dict[str, Any]:
    key = str(kind or "").strip()
    definition = WORKSPACE_NODE_LIBRARY.get(key)
    if definition:
        return copy.deepcopy(definition)
    fallback = copy.deepcopy(WORKSPACE_NODE_LIBRARY["custom.step"])
    fallback["title"] = key or fallback["title"]
    return fallback


def workspace_node_kinds_for_source(source_type: str) -> list[str]:
    source = str(source_type or "").strip().lower()
    if source == "repo":
        return [
            "source.repo",
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
    if source == "paper":
        return [
            "source.paper",
            "research.search",
            "repo.clone",
            "path.resolve",
            "repo.inspect",
            "dataset.find",
            "env.infer",
            "env.prepare",
            "gpu.allocate",
            "run.command",
            "artifact.collect",
            "eval.report",
        ]
    return [
        "source.idea",
        "research.search",
        "repo.clone",
        "path.resolve",
        "repo.inspect",
        "dataset.find",
        "env.infer",
        "env.prepare",
        "gpu.allocate",
        "run.command",
        "artifact.collect",
        "eval.report",
    ]


def should_upgrade_default_workflow_chain(
    template_id: str,
    source_type: str,
    raw_nodes: Any,
) -> bool:
    if str(template_id or "").strip() not in DEFAULT_WORKFLOW_TEMPLATE_IDS:
        return False
    if not isinstance(raw_nodes, list) or not raw_nodes:
        return True
    existing_kinds = [
        str(node.get("kind") or "").strip()
        for node in raw_nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip()
    ]
    expected_kinds = workspace_node_kinds_for_source(source_type)
    return any(kind not in existing_kinds for kind in expected_kinds)


def normalize_workspace_handler(value: Any) -> dict[str, str]:
    current = value if isinstance(value, dict) else {}
    mode = str(current.get("mode") or "human").strip().lower()
    if mode not in {"human", "agent", "system"}:
        mode = "human"
    return {
        "mode": mode,
        "agent_id": safe_id(str(current.get("agent_id") or "")) if str(current.get("agent_id") or "").strip() else "",
        "name": str(current.get("name") or "").strip(),
        "handoff": str(current.get("handoff") or "").strip(),
    }


def normalize_workspace_runtime(value: Any) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    return {
        "run_count": max(safe_int(current.get("run_count"), 0), 0),
        "last_job_id": str(current.get("last_job_id") or "").strip(),
        "last_job_name": str(current.get("last_job_name") or "").strip(),
        "last_job_kind": str(current.get("last_job_kind") or "").strip(),
        "last_job_status": str(current.get("last_job_status") or "").strip(),
        "last_run_at": str(current.get("last_run_at") or "").strip(),
        "last_finished_at": str(current.get("last_finished_at") or "").strip(),
        "last_error": str(current.get("last_error") or "").strip(),
        "trace": copy.deepcopy(current.get("trace")) if isinstance(current.get("trace"), list) else [],
        "artifacts": copy.deepcopy(current.get("artifacts")) if isinstance(current.get("artifacts"), list) else [],
        "resources": copy.deepcopy(current.get("resources")) if isinstance(current.get("resources"), dict) else {},
    }


def workspace_default_agents() -> list[dict[str, Any]]:
    return copy.deepcopy(DEFAULT_WORKSPACE_AGENTS)


def workspace_default_tools() -> list[dict[str, Any]]:
    return copy.deepcopy(DEFAULT_WORKSPACE_TOOLS)


def normalize_workspace_tool(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    preset_seed = str(
        current.get("id")
        or previous.get("id")
        or current.get("label")
        or previous.get("label")
        or current.get("name")
        or previous.get("name")
        or "",
    ).strip()
    preset = next(
        (
            item for item in DEFAULT_WORKSPACE_TOOLS
            if preset_seed and preset_seed in {
                str(item.get("id") or "").strip(),
                str(item.get("label") or "").strip(),
            }
        ),
        {},
    )
    base = {}
    if isinstance(preset, dict):
        base.update(copy.deepcopy(preset))
    base.update(copy.deepcopy(previous))
    base.update(copy.deepcopy(current))
    tool_id = safe_id(str(base.get("id") or base.get("name") or f"tool-{index + 1}")) or f"tool-{index + 1}"
    label = str(base.get("label") or base.get("display_name") or tool_id).strip() or tool_id
    category = str(base.get("category") or "general").strip() or "general"
    capability = str(base.get("capability") or "read").strip() or "read"
    return {
        "id": tool_id,
        "label": label,
        "category": category,
        "capability": capability,
        "description": str(base.get("description") or "").strip(),
        "enabled": bool(base.get("enabled", True)),
        "notes": str(base.get("notes") or "").strip(),
    }


def normalize_workspace_tools(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_tools()
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        tool = normalize_workspace_tool(item, index=index, existing=existing_item)
        if tool["id"] in seen:
            continue
        seen.add(tool["id"])
        tools.append(tool)
    if tools:
        return tools
    return [normalize_workspace_tool(item, index=index) for index, item in enumerate(workspace_default_tools())]


def normalize_workspace_agent(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
    tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    preset_seed = str(current.get("id") or previous.get("id") or current.get("role") or previous.get("role") or "").strip()
    preset = next(
        (
            item for item in DEFAULT_WORKSPACE_AGENTS
            if preset_seed and preset_seed in {str(item.get("id") or "").strip(), str(item.get("role") or "").strip()}
        ),
        {},
    )
    base = {}
    if isinstance(preset, dict):
        base.update(copy.deepcopy(preset))
    base.update(copy.deepcopy(previous))
    base.update(copy.deepcopy(current))
    name = str(base.get("name") or f"Agent {index + 1}").strip() or f"Agent {index + 1}"
    role = str(base.get("role") or safe_id(name) or f"agent-{index + 1}").strip() or f"agent-{index + 1}"
    agent_id = safe_id(str(base.get("id") or role or name or f"agent-{index + 1}")) or f"agent-{index + 1}"
    tools = parse_tag_list(base.get("tools", []))
    allowed_tools = {str(item or "").strip() for item in (tool_ids or []) if str(item or "").strip()}
    if allowed_tools:
        filtered_tools = [tool for tool in tools if tool in allowed_tools]
        if filtered_tools:
            tools = filtered_tools
    return {
        "id": agent_id,
        "name": name,
        "role": role,
        "prompt": str(base.get("prompt") or "").strip(),
        "tools": tools,
        "provider_profile_id": str(base.get("provider_profile_id") or "").strip(),
        "enabled": bool(base.get("enabled", True)),
    }


def normalize_workspace_agents(
    value: Any,
    *,
    existing: Any = None,
    tool_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_agents()
    agents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        agent = normalize_workspace_agent(item, index=index, existing=existing_item, tool_ids=tool_ids)
        if agent["id"] in seen:
            continue
        seen.add(agent["id"])
        agents.append(agent)
    if agents:
        return agents
    return [normalize_workspace_agent(item, index=index, tool_ids=tool_ids) for index, item in enumerate(workspace_default_agents())]


def normalize_workspace_model(
    value: Any,
    *,
    existing: Any = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    routing_mode = str(current.get("routing_mode") or previous.get("routing_mode") or "workspace_default").strip()
    if routing_mode not in {"workspace_default", "agent_override"}:
        routing_mode = "workspace_default"
    return {
        "provider_profile_id": str(current.get("provider_profile_id") or previous.get("provider_profile_id") or "").strip(),
        "routing_mode": routing_mode,
        "chat_agent_id": safe_id(str(current.get("chat_agent_id") or previous.get("chat_agent_id") or ""))
        if str(current.get("chat_agent_id") or previous.get("chat_agent_id") or "").strip()
        else "",
        "notes": str(current.get("notes") or previous.get("notes") or "").strip(),
    }


def normalize_global_tool_definition(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tool = normalize_workspace_tool(value, index=index, existing=existing)
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    created_at = str(previous.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        **tool,
        "created_at": created_at,
        "updated_at": now_iso(),
    }


def normalize_global_tool_definitions(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id = {
        str(item.get("id") or "").strip(): item
        for item in previous_list
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_tools()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        tool = normalize_global_tool_definition(item, index=index, existing=existing_item)
        if tool["id"] in seen:
            continue
        seen.add(tool["id"])
        items.append(tool)
    return items or [
        normalize_global_tool_definition(item, index=index)
        for index, item in enumerate(workspace_default_tools())
    ]


def normalize_global_agent_definition(
    value: Any,
    *,
    index: int = 0,
    existing: dict[str, Any] | None = None,
    tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    agent = normalize_workspace_agent(value, index=index, existing=existing, tool_ids=tool_ids)
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    created_at = str(previous.get("created_at") or current.get("created_at") or now_iso()).strip() or now_iso()
    return {
        **agent,
        "description": str(current.get("description") or previous.get("description") or "").strip(),
        "created_at": created_at,
        "updated_at": now_iso(),
    }


def normalize_global_agent_definitions(
    value: Any,
    *,
    existing: Any = None,
    tool_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id = {
        str(item.get("id") or "").strip(): item
        for item in previous_list
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    raw_items = value if isinstance(value, list) else previous_list or workspace_default_agents()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        agent = normalize_global_agent_definition(
            item,
            index=index,
            existing=existing_item,
            tool_ids=tool_ids,
        )
        if agent["id"] in seen:
            continue
        seen.add(agent["id"])
        items.append(agent)
    return items or [
        normalize_global_agent_definition(item, index=index, tool_ids=tool_ids)
        for index, item in enumerate(workspace_default_agents())
    ]


def default_tool_definition_by_id(tool_id: str) -> dict[str, Any] | None:
    target = str(tool_id or "").strip()
    return next(
        (
            copy.deepcopy(item)
            for item in DEFAULT_WORKSPACE_TOOLS
            if str(item.get("id") or "").strip() == target
        ),
        None,
    )


def default_agent_preset_for(agent: dict[str, Any]) -> dict[str, Any] | None:
    agent_id = str(agent.get("id") or "").strip()
    role = str(agent.get("role") or "").strip()
    return next(
        (
            copy.deepcopy(item)
            for item in DEFAULT_WORKSPACE_AGENTS
            if str(item.get("id") or "").strip() in {agent_id, role}
            or str(item.get("role") or "").strip() in {agent_id, role}
        ),
        None,
    )


def backfill_default_tool_definitions(
    tools: list[dict[str, Any]],
    *,
    required_tool_ids: list[str] | None = None,
    global_definitions: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    available_ids = {
        str(item.get("id") or "").strip()
        for item in tools
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    required_ids = [
        str(item or "").strip()
        for item in (required_tool_ids or [str(item.get("id") or "") for item in DEFAULT_WORKSPACE_TOOLS])
        if str(item or "").strip()
    ]
    updated = [copy.deepcopy(item) for item in tools if isinstance(item, dict)]
    applied: list[dict[str, Any]] = []
    for tool_id in required_ids:
        if tool_id in available_ids:
            continue
        preset = default_tool_definition_by_id(tool_id)
        if not preset:
            continue
        tool = (
            normalize_global_tool_definition(preset, index=len(updated))
            if global_definitions
            else normalize_workspace_tool(preset, index=len(updated))
        )
        updated.append(tool)
        available_ids.add(tool_id)
        applied.append(
            {
                "field": "tools",
                "label": "默认工具定义",
                "value": tool_id,
                "source": "default_tool_backfill",
            }
        )
    return updated, applied


def default_agent_required_tool_ids(agents: list[dict[str, Any]]) -> list[str]:
    tool_ids: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        preset = default_agent_preset_for(agent)
        if not preset:
            continue
        for tool_id in parse_tag_list(preset.get("tools", [])):
            if tool_id in seen:
                continue
            seen.add(tool_id)
            tool_ids.append(tool_id)
    return tool_ids


def workspace_required_default_tool_ids(workspace: dict[str, Any]) -> list[str]:
    tool_ids: list[str] = []
    seen: set[str] = set()
    for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        tool_id = workspace_node_required_tool_id(str(node.get("kind") or "").strip())
        if tool_id and tool_id not in seen:
            seen.add(tool_id)
            tool_ids.append(tool_id)
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for tool_id in default_agent_required_tool_ids(agents):
        if tool_id in seen:
            continue
        seen.add(tool_id)
        tool_ids.append(tool_id)
    return tool_ids


def backfill_default_agent_tools(
    agents: list[dict[str, Any]],
    *,
    tool_ids: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed_tool_ids = {
        str(item or "").strip()
        for item in (tool_ids or [])
        if str(item or "").strip()
    }
    updated: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        current = copy.deepcopy(agent)
        preset = default_agent_preset_for(current)
        if not preset:
            updated.append(current)
            continue
        current_tools = parse_tag_list(current.get("tools", []))
        seen = set(current_tools)
        missing: list[str] = []
        for tool_id in parse_tag_list(preset.get("tools", [])):
            if allowed_tool_ids and tool_id not in allowed_tool_ids:
                continue
            if tool_id in seen:
                continue
            seen.add(tool_id)
            current_tools.append(tool_id)
            missing.append(tool_id)
        if missing:
            current["tools"] = current_tools
            if "updated_at" in current:
                current["updated_at"] = now_iso()
            applied.append(
                {
                    "field": f"agents.{str(current.get('id') or '').strip()}.tools",
                    "label": f"{str(current.get('name') or current.get('id') or 'Agent').strip()} 工具授权",
                    "value": ", ".join(missing),
                    "source": "default_agent_tool_backfill",
                }
            )
        updated.append(current)
    return updated, applied


def normalize_source_mode(value: str) -> str:
    source_mode = str(value or "").strip().lower()
    if source_mode in {"repo", "paper", "idea", "mixed"}:
        return source_mode
    return "idea"


def infer_source_mode_from_inputs(
    *,
    repo_urls: list[str],
    paper_urls: list[str],
    goal_text: str,
) -> str:
    has_repo = bool(repo_urls)
    has_paper = bool(paper_urls)
    has_goal = bool(str(goal_text or "").strip())
    count = sum(1 for flag in (has_repo, has_paper, has_goal) if flag)
    if count > 1 and (has_repo or has_paper):
        return "mixed"
    if has_repo:
        return "repo"
    if has_paper:
        return "paper"
    return "idea"


def normalize_workspace_inputs(
    payload: Any,
    *,
    existing: Any = None,
) -> dict[str, Any]:
    current = payload if isinstance(payload, dict) else {}
    previous = existing if isinstance(existing, dict) else {}

    repo_urls = parse_line_list(
        current.get("repo_urls")
        if "repo_urls" in current
        else current.get("repo_references")
        if "repo_references" in current
        else previous.get("repo_urls", [])
    )
    paper_urls = parse_line_list(
        current.get("paper_urls")
        if "paper_urls" in current
        else current.get("paper_references")
        if "paper_references" in current
        else previous.get("paper_urls", [])
    )
    references = parse_line_list(current.get("references", previous.get("references", [])))
    context_blocks = parse_line_list(
        current.get("context_blocks")
        if "context_blocks" in current
        else current.get("context")
        if "context" in current
        else previous.get("context_blocks", [])
    )
    goal_text = str(
        current.get("goal_text")
        or current.get("brief")
        or current.get("idea_text")
        or previous.get("goal_text")
        or previous.get("brief")
        or ""
    ).strip()
    source_mode = normalize_source_mode(
        current.get("source_mode")
        or previous.get("source_mode")
        or infer_source_mode_from_inputs(repo_urls=repo_urls, paper_urls=paper_urls, goal_text=goal_text)
    )
    return {
        "goal_text": goal_text,
        "repo_urls": repo_urls,
        "paper_urls": paper_urls,
        "references": references,
        "context_blocks": context_blocks,
        "source_mode": source_mode,
    }


def source_type_for_chain(value: str) -> str:
    source_mode = normalize_source_mode(value)
    if source_mode == "mixed":
        return "idea"
    return source_mode


def recommended_node_assignment(kind: str) -> dict[str, str]:
    mapping = {
        "source.repo": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "确认仓库地址、目标分支、成功标准和运行约束。",
        },
        "source.paper": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "补齐论文链接、任务目标和希望复现的指标。",
        },
        "source.idea": {
            "mode": "human",
            "role": "",
            "name": "你",
            "handoff": "把目标、限制条件和成功标准写清楚，再交给 Planner 和 Researcher。",
        },
        "research.search": {
            "mode": "agent",
            "role": "researcher",
            "name": "Researcher",
            "handoff": "输出候选仓库、关键依赖、相关文章和可信度说明。",
        },
        "repo.clone": {
            "mode": "system",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "记录克隆目录、分支或提交，并确认代码已经落地。",
        },
        "path.resolve": {
            "mode": "agent",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "输出工作目录、数据目录、日志目录和结果目录的候选路径。",
        },
        "repo.inspect": {
            "mode": "agent",
            "role": "repo_scout",
            "name": "Repo Scout",
            "handoff": "产出入口、依赖、默认命令、配置文件和结果目录。",
        },
        "dataset.find": {
            "mode": "agent",
            "role": "researcher",
            "name": "Researcher",
            "handoff": "输出数据集名称、来源、本地路径候选、下载方式和结构要求。",
        },
        "env.infer": {
            "mode": "agent",
            "role": "env_builder",
            "name": "Env Builder",
            "handoff": "输出 Python/CUDA/依赖文件判断和建议安装命令。",
        },
        "env.prepare": {
            "mode": "system",
            "role": "env_builder",
            "name": "Env Builder",
            "handoff": "记录环境名、安装结果、失败依赖和替代方案。",
        },
        "gpu.allocate": {
            "mode": "system",
            "role": "gpu_scout",
            "name": "GPU Scout",
            "handoff": "记录目标服务器、GPU 编号、空闲显存和调度约束。",
        },
        "run.command": {
            "mode": "system",
            "role": "runner",
            "name": "Runner",
            "handoff": "记录服务器、GPU、会话、日志路径和下一步评估入口。",
        },
        "artifact.collect": {
            "mode": "agent",
            "role": "evaluator",
            "name": "Evaluator",
            "handoff": "输出日志、指标、模型文件、运行命令和可复现产物路径。",
        },
        "eval.report": {
            "mode": "agent",
            "role": "evaluator",
            "name": "Evaluator",
            "handoff": "汇总核心指标、主要输出文件、异常和下一步建议。",
        },
        "notify.user": {
            "mode": "agent",
            "role": "reporter",
            "name": "Reporter",
            "handoff": "把关键结论、风险和待确认项反馈给用户。",
        },
    }
    return mapping.get(str(kind or "").strip(), {
        "mode": "human",
        "role": "",
        "name": "你",
        "handoff": "补充这个节点的职责、输入输出和交接要求。",
    })


def build_recommended_handler(
    kind: str,
    agent_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendation = recommended_node_assignment(kind)
    role = str(recommendation.get("role") or "").strip()
    agent = next(
        (
            item for item in agent_definitions
            if str(item.get("role") or "").strip() == role or str(item.get("id") or "").strip() == role
        ),
        None,
    )
    return {
        "mode": str(recommendation.get("mode") or "human"),
        "agent_id": str(agent.get("id") or "").strip() if agent else "",
        "name": str((agent.get("name") if agent else "") or recommendation.get("name") or "").strip(),
        "handoff": str(recommendation.get("handoff") or "").strip(),
    }


def workflow_template_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("updated_at") or ""),
        str(item.get("created_at") or ""),
        str(item.get("id") or ""),
    )


def collect_template_agent_ids(
    nodes: list[dict[str, Any]],
    model: dict[str, Any],
) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or "").strip()
        if agent_id and agent_id not in seen:
            seen.add(agent_id)
            ids.append(agent_id)
    chat_agent_id = str(model.get("chat_agent_id") or "").strip()
    if chat_agent_id and chat_agent_id not in seen:
        ids.append(chat_agent_id)
    return ids


def collect_template_tool_ids(
    agent_ids: list[str],
    agent_definitions: list[dict[str, Any]],
) -> list[str]:
    tools: list[str] = []
    seen: set[str] = set()
    by_id = {
        str(agent.get("id") or "").strip(): agent
        for agent in agent_definitions
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    for agent_id in agent_ids:
        agent = by_id.get(str(agent_id or "").strip())
        if not agent:
            continue
        for tool_id in parse_tag_list(agent.get("tools", [])):
            if tool_id in seen:
                continue
            seen.add(tool_id)
            tools.append(tool_id)
    return tools


def normalize_workflow_template(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    agent_definitions: list[dict[str, Any]] | None = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    source_current = current.get("source") if isinstance(current.get("source"), dict) else {}
    env_current = current.get("env") if isinstance(current.get("env"), dict) else {}
    recipes_current = current.get("recipes") if isinstance(current.get("recipes"), list) else []
    recipe_existing = recipes_current[0] if recipes_current and isinstance(recipes_current[0], dict) else None

    source_type = normalize_source_mode(
        str(payload.get("source_type") or source_current.get("type") or current.get("source_type") or "repo")
    )
    repo_url = str(payload.get("repo_url") or source_current.get("repo_url") or "").strip()
    paper_url = str(payload.get("paper_url") or source_current.get("paper_url") or "").strip()
    idea_text = str(payload.get("idea_text") or source_current.get("idea_text") or "").strip()
    brief = str(payload.get("brief") or current.get("brief") or "").strip()

    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if repo_url:
            name = repo_name_from_url(repo_url) or "Repo 复现默认流"
        elif paper_url:
            name = "Paper 复现默认流"
        elif idea_text or brief:
            name = "Idea 探索默认流"
        else:
            name = "新工作流模板"

    template_id = str(current.get("id") or payload.get("id") or safe_id(name) or uuid.uuid4().hex[:8]).strip()
    created_at = str(current.get("created_at") or payload.get("created_at") or now_iso()).strip() or now_iso()
    recipe = normalize_workspace_recipe(payload, existing=recipe_existing)
    workspace_dir = str(payload.get("workspace_dir") or current.get("workspace_dir") or "").strip()
    env_name = str(payload.get("env_name") or env_current.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_current.get("manager") or "conda").strip() or "conda"
    python_version = str(payload.get("python_version") or env_current.get("python") or "").strip()

    raw_nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else current.get("nodes")
    raw_links = payload.get("links") if isinstance(payload.get("links"), list) else current.get("links")
    use_default_chain = bool(payload.get("rebuild_graph")) or should_upgrade_default_workflow_chain(
        template_id,
        source_type_for_chain(source_type),
        raw_nodes,
    )
    nodes = normalize_workspace_nodes(
        raw_nodes if isinstance(raw_nodes, list) else None,
        source_type_for_chain(source_type),
        brief=brief,
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=current.get("nodes") if isinstance(current.get("nodes"), list) else None,
        use_default_chain=use_default_chain,
    )
    nodes = sync_workspace_nodes_with_overview(
        nodes,
        brief=brief,
        source_type=source_type_for_chain(source_type),
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        recipe_command_overrides={
            key
            for key in ("setup_command", "run_command", "report_command", "schedule")
            if key in payload
        },
    )

    agent_defs = agent_definitions if isinstance(agent_definitions, list) else workspace_default_agents()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if handler and (str(handler.get("name") or "").strip() or str(handler.get("agent_id") or "").strip()):
            continue
        node["handler"] = build_recommended_handler(str(node.get("kind") or ""), agent_defs)

    links = normalize_workspace_links(None if use_default_chain else raw_links if isinstance(raw_links, list) else None, nodes)
    model = normalize_workspace_model(payload.get("model") if "model" in payload else current.get("model"), existing=current.get("model"))
    agent_ids = collect_template_agent_ids(nodes, model)
    tool_ids = collect_template_tool_ids(agent_ids, agent_defs)

    valid_tool_ids = {
        str(tool.get("id") or "").strip()
        for tool in (tool_definitions if isinstance(tool_definitions, list) else workspace_default_tools())
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    tool_ids = [tool_id for tool_id in tool_ids if tool_id in valid_tool_ids]

    return {
        "id": safe_id(template_id) or template_id,
        "name": name,
        "description": str(payload.get("description") or current.get("description") or brief).strip(),
        "status": str(payload.get("status") or current.get("status") or "ready").strip() or "ready",
        "brief": brief,
        "source": {
            "type": source_type,
            "repo_url": repo_url,
            "repo_ref": str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
            "paper_url": paper_url,
            "idea_text": idea_text,
        },
        "workspace_dir": workspace_dir,
        "env": {
            "name": env_name,
            "manager": env_manager,
            "python": python_version,
        },
        "recipes": [recipe],
        "model": model,
        "agent_ids": agent_ids,
        "tool_ids": tool_ids,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "created_at": created_at,
        "updated_at": now_iso(),
    }


def normalize_workspace_chat_message(
    value: Any,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = value if isinstance(value, dict) else {}
    previous = existing if isinstance(existing, dict) else {}
    role = str(current.get("role") or previous.get("role") or "user").strip().lower()
    if role not in {"system", "user", "assistant"}:
        role = "user"
    text = str(current.get("text") or previous.get("text") or "").strip()
    return {
        "id": str(current.get("id") or previous.get("id") or f"chat-{uuid.uuid4().hex[:8]}").strip(),
        "role": role,
        "text": text,
        "agent_id": safe_id(str(current.get("agent_id") or previous.get("agent_id") or ""))
        if str(current.get("agent_id") or previous.get("agent_id") or "").strip()
        else "",
        "agent_name": str(current.get("agent_name") or previous.get("agent_name") or "").strip(),
        "created_at": str(current.get("created_at") or previous.get("created_at") or now_iso()).strip() or now_iso(),
    }


def normalize_workspace_chat(
    value: Any,
    *,
    existing: Any = None,
) -> list[dict[str, Any]]:
    previous_list = existing if isinstance(existing, list) else []
    previous_by_id: dict[str, dict[str, Any]] = {}
    for item in previous_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            previous_by_id[str(item.get("id") or "").strip()] = item
    raw_items = value if isinstance(value, list) else previous_list
    messages: list[dict[str, Any]] = []
    for item in raw_items[-200:]:
        if not isinstance(item, dict):
            continue
        existing_item = previous_by_id.get(str(item.get("id") or "").strip(), {})
        message = normalize_workspace_chat_message(item, existing=existing_item)
        if not message["text"]:
            continue
        messages.append(message)
    return messages[-200:]


def make_workspace_chat_message(
    role: str,
    text: str,
    *,
    agent_id: str = "",
    agent_name: str = "",
) -> dict[str, Any]:
    return normalize_workspace_chat_message(
        {
            "role": role,
            "text": text,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "created_at": now_iso(),
        }
    )


def workspace_agent_name(workspace: dict[str, Any], agent_id: str) -> str:
    target = str(agent_id or "").strip()
    if not target:
        return ""
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "").strip() == target:
            return str(agent.get("name") or target).strip() or target
    return target


def workspace_source_brief(workspace: dict[str, Any]) -> str:
    brief = str(workspace.get("brief") or "").strip()
    if brief:
        return brief
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    return (
        str(source.get("idea_text") or "").strip()
        or str(source.get("paper_url") or "").strip()
        or str(source.get("repo_url") or "").strip()
    )


def build_workspace_chat_reply(
    workspace: dict[str, Any],
    user_text: str,
    *,
    agent_id: str = "",
) -> str:
    lines: list[str] = []
    agent_name = workspace_agent_name(workspace, agent_id)
    if agent_name:
        lines.append(f"已记录到 {agent_name} 的上下文。")
    brief = workspace_source_brief(workspace)
    if brief:
        first_line = brief.splitlines()[0].strip()
        if first_line:
            lines.append(f"当前项目目标：{first_line[:120]}")
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    flow = [str(node.get("title") or node.get("kind") or "").strip() for node in nodes if isinstance(node, dict)]
    flow = [item for item in flow if item]
    if flow:
        lines.append(f"现有工作流：{' -> '.join(flow[:4])}{' ...' if len(flow) > 4 else ''}")
    next_node = next(
        (
            node for node in nodes
            if isinstance(node, dict) and str(node.get("status") or "draft") in {"draft", "ready", "running", "blocked"}
        ),
        nodes[0] if nodes else {},
    )
    if isinstance(next_node, dict) and next_node:
        node_name = str(next_node.get("title") or next_node.get("kind") or "").strip()
        if node_name:
            lines.append(f"建议先检查节点：{node_name}")
    user_line = user_text.splitlines()[0].strip()
    if user_line:
        lines.append(f"你的新输入已归档：{user_line[:120]}")
    lines.append("外部模型调用还未接入，这里先保存对话、agent 路由和项目上下文。")
    return "\n".join(lines)


def workspace_agent_by_id(workspace: dict[str, Any], agent_id: str) -> dict[str, Any] | None:
    target = str(agent_id or "").strip()
    if not target:
        return None
    agents = workspace.get("agents") if isinstance(workspace.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "").strip() == target:
            return agent
    return None


def workspace_tool_index(workspace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tools = workspace.get("tools") if isinstance(workspace.get("tools"), list) else []
    indexed: dict[str, dict[str, Any]] = {}
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            continue
        normalized = normalize_workspace_tool(tool, index=index, existing=tool)
        tool_id = str(normalized.get("id") or "").strip()
        if tool_id and tool_id not in indexed:
            indexed[tool_id] = normalized
    return indexed


def workspace_agent_focus_node(
    workspace: dict[str, Any],
    agent: dict[str, Any],
    *,
    requested_node_kind: str = "",
) -> dict[str, Any] | None:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    target_kind = str(requested_node_kind or "").strip()
    if target_kind:
        for node in nodes:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == target_kind:
                return node

    agent_id = str(agent.get("id") or "").strip()
    if agent_id:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            if str(handler.get("agent_id") or "").strip() == agent_id:
                return node

    role = str(agent.get("role") or "").strip().lower()
    role_hints = {
        "planner": ["source.repo", "source.paper", "source.idea", "research.search"],
        "researcher": ["research.search", "dataset.find", "source.paper", "source.idea"],
        "repo_scout": ["repo.clone", "path.resolve", "repo.inspect", "source.repo"],
        "gpu_scout": ["gpu.allocate", "run.command", "env.prepare"],
        "env_builder": ["env.infer", "env.prepare", "repo.inspect"],
        "runner": ["run.command"],
        "evaluator": ["artifact.collect", "eval.report", "run.command"],
        "watcher": ["run.command", "gpu.allocate", "eval.report"],
        "reporter": ["eval.report", "artifact.collect", "notify.user"],
    }
    for kind in role_hints.get(role, []):
        for node in nodes:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == kind:
                return node

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("status") or "draft").strip() in {"draft", "ready", "running", "blocked"}:
            return node

    return next((node for node in nodes if isinstance(node, dict)), None)


def build_workspace_agent_debug(
    workspace: dict[str, Any],
    agent: dict[str, Any],
    *,
    input_text: str = "",
    requested_node_kind: str = "",
    requested_tool_ids: list[str] | None = None,
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    model = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
    chat = workspace.get("chat") if isinstance(workspace.get("chat"), list) else []
    tool_map = workspace_tool_index(workspace)
    requested_tool_set = {
        str(item or "").strip()
        for item in (requested_tool_ids or [])
        if str(item or "").strip()
    }
    allowed_tool_ids = [
        tool_id
        for tool_id in parse_tag_list(agent.get("tools", []))
        if tool_id in tool_map and (not requested_tool_set or tool_id in requested_tool_set)
    ]
    allowed_tools = [tool_map[tool_id] for tool_id in allowed_tool_ids]
    focus_node = workspace_agent_focus_node(
        workspace,
        agent,
        requested_node_kind=requested_node_kind,
    )
    brief = workspace_source_brief(workspace)
    source_summary = (
        str(source.get("repo_url") or "").strip()
        or str(source.get("paper_url") or "").strip()
        or str(source.get("idea_text") or "").strip()
        or brief
    )
    routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
    workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
    agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
    effective_profile_id = workspace_profile_id
    profile_source = "workspace_default" if workspace_profile_id else "unconfigured"
    if routing_mode == "agent_override" and agent_profile_id:
        effective_profile_id = agent_profile_id
        profile_source = "agent_override"

    focus_title = ""
    focus_kind = ""
    focus_summary = ""
    focus_status = ""
    focus_handler = {}
    if isinstance(focus_node, dict):
        focus_title = str(focus_node.get("title") or focus_node.get("kind") or "").strip()
        focus_kind = str(focus_node.get("kind") or "").strip()
        focus_status = str(focus_node.get("status") or "").strip()
        focus_summary = str((focus_node.get("config") or {}).get("goal") or "").strip()
        if not focus_summary:
            focus_summary = str((focus_node.get("config") or {}).get("run_command") or "").strip()
        if not focus_summary:
            focus_summary = str((focus_node.get("config") or {}).get("questions") or "").strip()
        focus_handler = focus_node.get("handler") if isinstance(focus_node.get("handler"), dict) else {}

    input_line = str(input_text or "").strip().splitlines()[0].strip() if str(input_text or "").strip() else ""
    role = str(agent.get("role") or "").strip().lower()
    plan: list[str] = []
    if input_line:
        plan.append(f"先吸收本轮输入：{input_line[:120]}")
    if focus_title:
        plan.append(f"聚焦节点“{focus_title}”，先明确这个节点当前缺什么输入、要交付什么输出。")
    role_plan_map = {
        "planner": "把当前目标拆成节点、交接说明和需要人工确认的检查点。",
        "researcher": "先检索论文、候选仓库、依赖说明和运行方式，再回写可执行线索。",
        "repo_scout": "优先读仓库入口、依赖文件、配置目录和 README，确认真正的运行入口。",
        "gpu_scout": "先判断哪台主机和哪块 GPU 适合当前任务，再补工作目录和资源提示。",
        "env_builder": "优先核对环境管理方式、Python 版本和安装命令，减少首次运行失败。",
        "runner": "把节点配置转成真实任务，先保证命令、目录、环境和 GPU 策略都闭合。",
        "evaluator": "围绕日志、指标和产物路径整理评估结果，并补出最终结论。",
        "watcher": "盯住日志、失败信号和资源异常，及时把风险和错误回推给用户。",
        "reporter": "把过程、结论、风险和下一步建议整理成可交付摘要。",
    }
    if role_plan_map.get(role):
        plan.append(role_plan_map[role])
    tool_categories = list(dict.fromkeys(str(tool.get("category") or "general") for tool in allowed_tools))
    category_hints = {
        "research": "如需补资料，优先用检索类工具拉齐 repo、论文和 issue 线索。",
        "repo": "仓库类工具可以帮助确认入口、目录结构和默认参数。",
        "env": "环境类工具适合先补 conda / venv、安装依赖和 Python 版本。",
        "gpu": "GPU 类工具适合先看利用率、显存和资源分配策略。",
        "run": "运行类工具适合把当前步骤正式送进任务队列。",
        "artifact": "产物类工具适合把结果整理回项目上下文或报告。",
        "notify": "通知类工具适合把阶段结果或异常同步给用户。",
        "workflow": "工作流类工具适合继续编辑节点或调整交接关系。",
        "chat": "对话类工具适合把本轮理解和结论写回项目上下文。",
    }
    for category in tool_categories:
        hint = category_hints.get(category)
        if hint and hint not in plan:
            plan.append(hint)
    if not plan:
        plan.append("先检查项目目标、工作流节点和当前 agent 边界，再决定下一步。")

    warnings: list[str] = []
    if agent.get("enabled") is False:
        warnings.append("这个 agent 当前处于停用状态。")
    if not str(agent.get("prompt") or "").strip():
        warnings.append("这个 agent 还没有提示词，调试结果只能基于角色和工具边界推断。")
    if not allowed_tools:
        warnings.append("这个 agent 目前没有可用工具。")
    if routing_mode != "agent_override" and agent_profile_id and not workspace_profile_id:
        warnings.append("项目路由还是 workspace_default，agent 上的模型覆盖暂时不会生效。")
    if requested_tool_set and not allowed_tools:
        warnings.append("请求调试的工具与当前 agent allowlist 没有交集。")
    if not focus_node:
        warnings.append("当前没有找到合适的聚焦节点。")

    next_actions: list[str] = []
    if not str(input_text or "").strip():
        next_actions.append("补一段更具体的调试输入，让 agent 有明确本轮任务。")
    if not str(agent.get("prompt") or "").strip():
        next_actions.append("先补提示词，明确该角色应该产出什么。")
    if not allowed_tools:
        next_actions.append("先给这个 agent 绑定至少一类工具。")
    if not effective_profile_id:
        next_actions.append("给项目或 agent 配一个 Provider Profile。")
    if isinstance(focus_node, dict):
        handler_agent_id = str(focus_handler.get("agent_id") or "").strip()
        if handler_agent_id and handler_agent_id != str(agent.get("id") or "").strip():
            next_actions.append("如果要让这个 agent 真接手当前节点，记得把节点绑定到它。")
        if focus_kind == "run.command" and not str((focus_node.get("config") or {}).get("run_command") or "").strip():
            next_actions.append("当前运行节点还没有命令，先补 run_command。")

    prompt_lines = [
        f"角色：{str(agent.get('name') or agent.get('id') or '').strip()} ({str(agent.get('role') or '').strip()})",
        str(agent.get("prompt") or "").strip(),
        f"项目目标：{brief}" if brief else "",
        f"当前聚焦节点：{focus_title} ({focus_kind})" if focus_title and focus_kind else "",
        f"输入摘要：{input_line}" if input_line else "",
    ]
    assigned_nodes = []
    for node in workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if str(handler.get("agent_id") or "").strip() != str(agent.get("id") or "").strip():
            continue
        assigned_nodes.append(
            {
                "id": str(node.get("id") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "kind": str(node.get("kind") or "").strip(),
                "status": str(node.get("status") or "").strip(),
            }
        )

    return {
        "workspace_id": str(workspace.get("id") or "").strip(),
        "workspace_name": str(workspace.get("name") or "").strip(),
        "generated_at": now_iso(),
        "agent": {
            "id": str(agent.get("id") or "").strip(),
            "name": str(agent.get("name") or "").strip(),
            "role": str(agent.get("role") or "").strip(),
            "enabled": bool(agent.get("enabled", True)),
            "provider_profile_id": agent_profile_id,
        },
        "input_text": str(input_text or "").strip(),
        "prompt_preview": "\n".join([line for line in prompt_lines if line]).strip(),
        "allowed_tools": allowed_tools,
        "assigned_nodes": assigned_nodes[:8],
        "focus_node": {
            "id": str(focus_node.get("id") or "").strip() if isinstance(focus_node, dict) else "",
            "title": focus_title,
            "kind": focus_kind,
            "status": focus_status,
            "summary": focus_summary,
            "handler_mode": str(focus_handler.get("mode") or "").strip(),
            "handler_agent_id": str(focus_handler.get("agent_id") or "").strip(),
        },
        "context": {
            "source_type": str(source.get("type") or "").strip(),
            "source_summary": source_summary,
            "brief": brief,
            "workspace_dir": str(workspace.get("workspace_dir") or "").strip(),
            "reference_count": len(workspace.get("references")) if isinstance(workspace.get("references"), list) else 0,
            "node_count": len(workspace.get("nodes")) if isinstance(workspace.get("nodes"), list) else 0,
            "chat_message_count": len(chat),
        },
        "model": {
            "routing_mode": routing_mode,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "effective_profile_id": effective_profile_id,
            "source": profile_source,
            "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
        },
        "plan": plan[:6],
        "next_actions": next_actions[:5],
        "warnings": warnings[:5],
    }


def workspace_node_default_config(
    kind: str,
    *,
    brief: str,
    source_type: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
) -> dict[str, Any]:
    idea_seed = idea_text or brief
    idea_line = idea_seed.splitlines()[0].strip() if idea_seed else ""
    search_query = paper_url or idea_line or repo_url or repo_name_from_url(repo_url)
    defaults = {
        "source.repo": {
            "repo_url": repo_url,
            "repo_ref": repo_ref,
        },
        "source.paper": {
            "paper_url": paper_url,
        },
        "source.idea": {
            "idea_text": idea_seed,
        },
        "research.search": {
            "query": search_query,
            "goal": "检索相关代码仓库、依赖和运行方式",
            "repo_url": repo_url,
            "paper_url": paper_url,
        },
        "repo.clone": {
            "repo_url": repo_url,
            "repo_ref": repo_ref,
            "workspace_dir": workspace_dir,
        },
        "path.resolve": {
            "workspace_dir": workspace_dir,
            "data_roots": "",
            "output_roots": "runs\noutputs\ncheckpoints\nlogs",
        },
        "repo.inspect": {
            "workspace_dir": workspace_dir,
            "focus_paths": "",
            "questions": "入口、依赖、默认配置、结果目录",
        },
        "dataset.find": {
            "query": search_query,
            "dataset_hints": "",
            "data_roots": "",
            "expected_layout": "",
        },
        "env.infer": {
            "workspace_dir": workspace_dir,
            "manifest_paths": "requirements.txt, pyproject.toml, environment.yml, setup.py",
            "env_name": env_name,
            "python_version": python_version,
        },
        "env.prepare": {
            "workspace_dir": workspace_dir,
            "env_name": env_name,
            "env_manager": env_manager,
            "python_version": python_version,
            "setup_command": str(recipe.get("setup_command") or "").strip(),
        },
        "gpu.allocate": {
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "notes": "",
        },
        "run.command": {
            "workspace_dir": workspace_dir,
            "env_name": env_name,
            "server_id": "",
            "gpu_policy": "auto",
            "gpu_index": "",
            "min_free_memory_gib": "",
            "run_command": str(recipe.get("run_command") or "").strip(),
            "schedule": str(recipe.get("schedule") or "").strip(),
        },
        "artifact.collect": {
            "workspace_dir": workspace_dir,
            "artifact_paths": "runs\noutputs\ncheckpoints\nlogs",
            "metric_paths": "",
            "notes": str(recipe.get("notes") or "").strip(),
        },
        "eval.report": {
            "report_command": str(recipe.get("report_command") or "").strip(),
            "metric_paths": "",
            "notes": str(recipe.get("notes") or "").strip(),
        },
        "notify.user": {
            "channel": "ui",
            "message": "",
        },
        "custom.step": {
            "goal": "",
            "command": "",
            "output_expectation": "",
        },
    }
    base = defaults.get(kind) or defaults["custom.step"]
    return copy.deepcopy(base)


def make_workspace_node(
    kind: str,
    title: str,
    *,
    config: dict[str, Any] | None = None,
    node_id: str | None = None,
    position: dict[str, int] | None = None,
    status: str = "draft",
    handler: dict[str, Any] | None = None,
    notes: str = "",
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(node_id or safe_id(f"{kind}-{uuid.uuid4().hex[:8]}")),
        "kind": str(kind),
        "title": str(title),
        "status": str(status or "draft"),
        "config": dict(config or {}),
        "handler": normalize_workspace_handler(handler),
        "notes": str(notes or "").strip(),
        "runtime": normalize_workspace_runtime(runtime),
        "position": {
            "x": safe_int((position or {}).get("x"), 0),
            "y": safe_int((position or {}).get("y"), 0),
        },
    }


def normalize_workspace_nodes(
    raw_nodes: list[dict[str, Any]] | None,
    source_type: str,
    *,
    brief: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
    existing_nodes: list[dict[str, Any]] | None = None,
    use_default_chain: bool = False,
) -> list[dict[str, Any]]:
    existing_by_id: dict[str, dict[str, Any]] = {}
    if existing_nodes:
        for node in existing_nodes:
            if isinstance(node, dict) and str(node.get("id") or "").strip():
                existing_by_id[str(node.get("id")).strip()] = node

    defaults = raw_nodes if raw_nodes and not use_default_chain else None
    if defaults is None:
        defaults = [{"kind": kind} for kind in workspace_node_kinds_for_source(source_type)]

    nodes: list[dict[str, Any]] = []
    for index, raw in enumerate(defaults):
        if not isinstance(raw, dict):
            continue
        raw_kind = str(raw.get("kind") or "").strip()
        if not raw_kind:
            continue
        existing = existing_by_id.get(str(raw.get("id") or "").strip(), {})
        definition = workspace_node_definition(raw_kind)
        config = definition.get("config_defaults", {})
        if isinstance(config, dict):
            config = copy.deepcopy(config)
        else:
            config = {}
        config.update(
            workspace_node_default_config(
                raw_kind,
                brief=brief,
                source_type=source_type,
                repo_url=repo_url,
                repo_ref=repo_ref,
                paper_url=paper_url,
                idea_text=idea_text,
                workspace_dir=workspace_dir,
                env_name=env_name,
                env_manager=env_manager,
                python_version=python_version,
                recipe=recipe,
            )
        )
        if isinstance(existing.get("config"), dict):
            config.update(existing["config"])
        if isinstance(raw.get("config"), dict):
            config.update(raw["config"])
        node = make_workspace_node(
            raw_kind,
            str(raw.get("title") or existing.get("title") or definition.get("title") or raw_kind).strip() or raw_kind,
            config=config,
            node_id=str(raw.get("id") or existing.get("id") or "").strip() or None,
            position=(
                raw.get("position")
                if isinstance(raw.get("position"), dict)
                else existing.get("position")
                if isinstance(existing.get("position"), dict)
                else {"x": index * 240, "y": 0}
            ),
            status=str(raw.get("status") or existing.get("status") or "draft").strip() or "draft",
            handler=raw.get("handler") if raw.get("handler") is not None else existing.get("handler"),
            notes=str(raw.get("notes") or existing.get("notes") or "").strip(),
            runtime=raw.get("runtime") if raw.get("runtime") is not None else existing.get("runtime"),
        )
        input_mapping = (
            raw.get("input_mapping")
            if isinstance(raw.get("input_mapping"), dict)
            else existing.get("input_mapping")
            if isinstance(existing.get("input_mapping"), dict)
            else {}
        )
        if input_mapping:
            node["input_mapping"] = {
                str(key or "").strip(): str(value or "").strip()
                for key, value in input_mapping.items()
                if str(key or "").strip()
            }
        output_key = str(raw.get("output_key") or existing.get("output_key") or "").strip()
        if output_key:
            node["output_key"] = output_key
        nodes.append(node)

    if nodes:
        return nodes
    return normalize_workspace_nodes(
        [{"kind": kind} for kind in workspace_node_kinds_for_source(source_type)],
        source_type,
        brief=brief,
        repo_url=repo_url,
        repo_ref=repo_ref,
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=existing_nodes,
    )


def normalize_workspace_links(
    raw_links: list[dict[str, Any]] | None,
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    node_ids = [str(node.get("id") or "").strip() for node in nodes if str(node.get("id") or "").strip()]
    valid_ids = set(node_ids)
    seen: set[tuple[str, str]] = set()
    links: list[dict[str, Any]] = []
    if raw_links:
        for index, raw in enumerate(raw_links):
            if not isinstance(raw, dict):
                continue
            from_id = str(raw.get("from") or "").strip()
            to_id = str(raw.get("to") or "").strip()
            if from_id not in valid_ids or to_id not in valid_ids or from_id == to_id:
                continue
            pair = (from_id, to_id)
            if pair in seen:
                continue
            seen.add(pair)
            links.append(
                {
                    "id": safe_id(str(raw.get("id") or f"link-{index + 1}-{from_id}-{to_id}")),
                    "from": from_id,
                    "to": to_id,
                }
            )
    if links:
        return links
    for index in range(len(node_ids) - 1):
        from_id = node_ids[index]
        to_id = node_ids[index + 1]
        links.append(
            {
                "id": safe_id(f"link-{index + 1}-{from_id}-{to_id}"),
                "from": from_id,
                "to": to_id,
            }
        )
    return links


def sync_workspace_nodes_with_overview(
    nodes: list[dict[str, Any]],
    *,
    brief: str,
    source_type: str,
    repo_url: str,
    repo_ref: str,
    paper_url: str,
    idea_text: str,
    workspace_dir: str,
    env_name: str,
    env_manager: str,
    python_version: str,
    recipe: dict[str, Any],
    recipe_command_overrides: set[str] | None = None,
) -> list[dict[str, Any]]:
    synced = copy.deepcopy(nodes)
    force_recipe_commands = recipe_command_overrides is None
    recipe_command_overrides = recipe_command_overrides or set()

    def sync_recipe_command(config: dict[str, Any], key: str) -> None:
        value = str(recipe.get(key) or "").strip()
        if force_recipe_commands or key in recipe_command_overrides:
            config[key] = value
        elif value and not str(config.get(key) or "").strip():
            config[key] = value

    idea_seed = idea_text or brief
    idea_line = idea_seed.splitlines()[0].strip() if idea_seed else ""
    source_index = next((idx for idx, node in enumerate(synced) if str(node.get("kind") or "").startswith("source.")), -1)
    search_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "research.search"), -1)
    clone_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "repo.clone"), -1)
    path_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "path.resolve"), -1)
    inspect_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "repo.inspect"), -1)
    dataset_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "dataset.find"), -1)
    env_infer_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "env.infer"), -1)
    env_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "env.prepare"), -1)
    gpu_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "gpu.allocate"), -1)
    run_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "run.command"), -1)
    artifact_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "artifact.collect"), -1)
    eval_index = next((idx for idx, node in enumerate(synced) if node.get("kind") == "eval.report"), -1)
    if source_index >= 0:
        node = synced[source_index]
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        if node.get("kind") == "source.repo":
            config.update({"repo_url": repo_url, "repo_ref": repo_ref})
        elif node.get("kind") == "source.paper":
            config.update({"paper_url": paper_url})
        elif node.get("kind") == "source.idea":
            config.update({"idea_text": idea_seed})
        node["config"] = config
    if search_index >= 0:
        config = synced[search_index].get("config") if isinstance(synced[search_index].get("config"), dict) else {}
        config.update({"repo_url": repo_url, "paper_url": paper_url, "source_type": source_type})
        if not str(config.get("query") or "").strip():
            config["query"] = paper_url or idea_line or repo_url
        synced[search_index]["config"] = config
    if clone_index >= 0:
        config = synced[clone_index].get("config") if isinstance(synced[clone_index].get("config"), dict) else {}
        config.update({"repo_url": repo_url, "repo_ref": repo_ref, "workspace_dir": workspace_dir})
        synced[clone_index]["config"] = config
    if path_index >= 0:
        config = synced[path_index].get("config") if isinstance(synced[path_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[path_index]["config"] = config
    if inspect_index >= 0:
        config = synced[inspect_index].get("config") if isinstance(synced[inspect_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[inspect_index]["config"] = config
    if dataset_index >= 0:
        config = synced[dataset_index].get("config") if isinstance(synced[dataset_index].get("config"), dict) else {}
        if not str(config.get("query") or "").strip():
            config["query"] = paper_url or idea_line or repo_url
        synced[dataset_index]["config"] = config
    if env_infer_index >= 0:
        config = synced[env_infer_index].get("config") if isinstance(synced[env_infer_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir, "env_name": env_name, "python_version": python_version})
        synced[env_infer_index]["config"] = config
    if env_index >= 0:
        config = synced[env_index].get("config") if isinstance(synced[env_index].get("config"), dict) else {}
        config.update(
            {
                "workspace_dir": workspace_dir,
                "env_name": env_name,
                "env_manager": env_manager,
                "python_version": python_version,
            }
        )
        sync_recipe_command(config, "setup_command")
        synced[env_index]["config"] = config
    if gpu_index >= 0:
        config = synced[gpu_index].get("config") if isinstance(synced[gpu_index].get("config"), dict) else {}
        if not str(config.get("gpu_policy") or "").strip():
            config["gpu_policy"] = "auto"
        synced[gpu_index]["config"] = config
    if run_index >= 0:
        config = synced[run_index].get("config") if isinstance(synced[run_index].get("config"), dict) else {}
        config.update(
            {
                "workspace_dir": workspace_dir,
                "env_name": env_name,
            }
        )
        sync_recipe_command(config, "run_command")
        sync_recipe_command(config, "schedule")
        synced[run_index]["config"] = config
    if artifact_index >= 0:
        config = synced[artifact_index].get("config") if isinstance(synced[artifact_index].get("config"), dict) else {}
        config.update({"workspace_dir": workspace_dir})
        synced[artifact_index]["config"] = config
    if eval_index >= 0:
        config = synced[eval_index].get("config") if isinstance(synced[eval_index].get("config"), dict) else {}
        sync_recipe_command(config, "report_command")
        synced[eval_index]["config"] = config
    return synced


def build_default_workflow_templates(
    agent_definitions: list[dict[str, Any]] | None = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    agents = agent_definitions if isinstance(agent_definitions, list) else normalize_global_agent_definitions(None)
    tools = tool_definitions if isinstance(tool_definitions, list) else normalize_global_tool_definitions(None)
    seeds = [
        {
            "id": "repo-default-flow",
            "name": "Repo 复现默认流",
            "description": "从 repo 输入、环境准备到运行与结果整理的顺序链路。",
            "source_type": "repo",
            "brief": "给定仓库地址后，自动完成克隆、检查、环境准备、运行与结果整理。",
            "status": "ready",
        },
        {
            "id": "paper-default-flow",
            "name": "Paper 复现默认流",
            "description": "从论文输入、资料检索到运行与评估的顺序链路。",
            "source_type": "paper",
            "brief": "给定论文链接后，先检索资料与候选实现，再继续环境准备、运行与评估。",
            "status": "ready",
        },
        {
            "id": "idea-default-flow",
            "name": "Idea 探索默认流",
            "description": "从自然语言目标出发，先检索再逐步形成执行链。",
            "source_type": "idea",
            "brief": "给定目标文本后，先拆解问题、检索相关资料，再准备环境、运行与整理结果。",
            "status": "ready",
        },
    ]
    return [
        normalize_workflow_template(seed, agent_definitions=agents, tool_definitions=tools)
        for seed in seeds
    ]


def build_template_snapshot(
    template: dict[str, Any],
    agent_definitions: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    agent_index = {
        str(agent.get("id") or "").strip(): copy.deepcopy(agent)
        for agent in agent_definitions
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    tool_index = {
        str(tool.get("id") or "").strip(): copy.deepcopy(tool)
        for tool in tool_definitions
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    agent_ids = [str(item).strip() for item in template.get("agent_ids", []) if str(item).strip()]
    tool_ids = [str(item).strip() for item in template.get("tool_ids", []) if str(item).strip()]
    return {
        "template_id": str(template.get("id") or "").strip(),
        "template_name": str(template.get("name") or "").strip(),
        "source": copy.deepcopy(template.get("source") if isinstance(template.get("source"), dict) else {}),
        "env": copy.deepcopy(template.get("env") if isinstance(template.get("env"), dict) else {}),
        "recipes": copy.deepcopy(template.get("recipes") if isinstance(template.get("recipes"), list) else []),
        "model": copy.deepcopy(template.get("model") if isinstance(template.get("model"), dict) else {}),
        "nodes": copy.deepcopy(template.get("nodes") if isinstance(template.get("nodes"), list) else []),
        "links": copy.deepcopy(template.get("links") if isinstance(template.get("links"), list) else []),
        "agents": [agent_index[agent_id] for agent_id in agent_ids if agent_id in agent_index],
        "tools": [tool_index[tool_id] for tool_id in tool_ids if tool_id in tool_index],
        "created_at": now_iso(),
    }


def workspace_input_source_summary(inputs: dict[str, Any]) -> tuple[str, str, str, str]:
    repo_urls = parse_line_list(inputs.get("repo_urls", []))
    paper_urls = parse_line_list(inputs.get("paper_urls", []))
    goal_text = str(inputs.get("goal_text") or "").strip()
    source_mode = normalize_source_mode(inputs.get("source_mode") or "")
    repo_url = repo_urls[0] if repo_urls else ""
    paper_url = paper_urls[0] if paper_urls else ""
    idea_text = goal_text
    chain_source_type = source_type_for_chain(source_mode)
    return chain_source_type, repo_url, paper_url, idea_text


def normalize_workspace_instance_from_template(
    payload: dict[str, Any],
    *,
    template: dict[str, Any],
    agent_definitions: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    template_snapshot = build_template_snapshot(template, agent_definitions, tool_definitions)
    inputs = normalize_workspace_inputs(payload.get("inputs") if isinstance(payload.get("inputs"), dict) else payload, existing=current.get("inputs"))
    chain_source_type, repo_url, paper_url, idea_text = workspace_input_source_summary(inputs)
    source_template = template_snapshot.get("source") if isinstance(template_snapshot.get("source"), dict) else {}
    env_template = template_snapshot.get("env") if isinstance(template_snapshot.get("env"), dict) else {}
    recipes = template_snapshot.get("recipes") if isinstance(template_snapshot.get("recipes"), list) else []
    recipe = recipes[0] if recipes and isinstance(recipes[0], dict) else {}

    workspace_id = str(current.get("id") or "").strip() or (
        datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    )
    brief = str(payload.get("brief") or current.get("brief") or inputs.get("goal_text") or template.get("brief") or "").strip()
    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if brief:
            name = brief.splitlines()[0][:60]
        else:
            name = str(template.get("name") or "新任务实例").strip() or "新任务实例"

    workspace_dir = str(
        payload.get("workspace_dir")
        or current.get("workspace_dir")
        or template.get("workspace_dir")
        or ""
    ).strip()
    env_name = str(payload.get("env_name") or current.get("env", {}).get("name") or env_template.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or current.get("env", {}).get("manager") or env_template.get("manager") or "conda").strip() or "conda"
    python_version = str(payload.get("python_version") or current.get("env", {}).get("python") or env_template.get("python") or "").strip()

    nodes = normalize_workspace_nodes(
        template_snapshot.get("nodes") if isinstance(template_snapshot.get("nodes"), list) else None,
        chain_source_type,
        brief=brief,
        repo_url=repo_url or str(source_template.get("repo_url") or "").strip(),
        repo_ref=str(source_template.get("repo_ref") or "").strip(),
        paper_url=paper_url or str(source_template.get("paper_url") or "").strip(),
        idea_text=idea_text or str(source_template.get("idea_text") or "").strip(),
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=current.get("nodes") if isinstance(current.get("nodes"), list) else None,
    )
    nodes = sync_workspace_nodes_with_overview(
        nodes,
        brief=brief,
        source_type=chain_source_type,
        repo_url=repo_url or str(source_template.get("repo_url") or "").strip(),
        repo_ref=str(source_template.get("repo_ref") or "").strip(),
        paper_url=paper_url or str(source_template.get("paper_url") or "").strip(),
        idea_text=idea_text or str(source_template.get("idea_text") or "").strip(),
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        recipe_command_overrides={
            key
            for key in ("setup_command", "run_command", "report_command", "schedule")
            if key in payload
        },
    )
    links = normalize_workspace_links(
        template_snapshot.get("links") if isinstance(template_snapshot.get("links"), list) else None,
        nodes,
    )
    created_at = str(current.get("created_at") or now_iso()).strip() or now_iso()
    source_mode = normalize_source_mode(inputs.get("source_mode") or "")
    source = {
        "type": source_mode,
        "repo_url": repo_url or str(source_template.get("repo_url") or "").strip(),
        "repo_ref": str(source_template.get("repo_ref") or "").strip(),
        "paper_url": paper_url or str(source_template.get("paper_url") or "").strip(),
        "idea_text": idea_text or str(source_template.get("idea_text") or "").strip(),
    }
    model = copy.deepcopy(template_snapshot.get("model") if isinstance(template_snapshot.get("model"), dict) else {})
    agents = copy.deepcopy(template_snapshot.get("agents") if isinstance(template_snapshot.get("agents"), list) else [])
    tools = copy.deepcopy(template_snapshot.get("tools") if isinstance(template_snapshot.get("tools"), list) else [])
    return {
        "id": workspace_id,
        "name": name,
        "status": str(payload.get("status") or current.get("status") or "ready").strip() or "ready",
        "brief": brief,
        "references": parse_line_list(inputs.get("references", [])),
        "inputs": inputs,
        "source": source,
        "workspace_dir": workspace_dir,
        "env": {
            "name": env_name,
            "manager": env_manager,
            "python": python_version,
        },
        "recipes": copy.deepcopy(template_snapshot.get("recipes") if isinstance(template_snapshot.get("recipes"), list) else []),
        "agents": agents,
        "model": model,
        "chat": normalize_workspace_chat(
            payload.get("chat") if "chat" in payload else current.get("chat"),
            existing=current.get("chat"),
        ),
        "tools": tools,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "template_id": str(template.get("id") or "").strip(),
        "template_name": str(template.get("name") or "").strip(),
        "template_snapshot": template_snapshot,
        "execution": copy.deepcopy(current.get("execution") if isinstance(current.get("execution"), dict) else {}),
        "created_at": created_at,
        "updated_at": now_iso(),
    }


def derive_workspace_execution_state(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    workspace_id = str(workspace.get("id") or "").strip()
    counts = {
        "pending": 0,
        "queued": 0,
        "running": 0,
        "done": 0,
        "failed": 0,
    }
    node_states: list[dict[str, Any]] = []
    latest_job: dict[str, Any] | None = None
    latest_error_job: dict[str, Any] | None = None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        bound_jobs = [
            job for job in jobs
            if workspace_job_binding(job) == (workspace_id, node_id)
        ]
        bound_jobs.sort(key=workspace_job_sort_key, reverse=True)
        latest = bound_jobs[0] if bound_jobs else None
        state = "pending"
        if latest:
            job_status = str(latest.get("status") or "").strip()
            if job_status in {"queued", "blocked", "starting"}:
                state = "queued"
            elif job_status == "running":
                state = "running"
            elif job_status == "done":
                state = "done"
            else:
                state = "failed"
            if latest_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_job):
                latest_job = latest
            if str(latest.get("error") or "").strip():
                if latest_error_job is None or workspace_job_sort_key(latest) > workspace_job_sort_key(latest_error_job):
                    latest_error_job = latest
        counts[state] += 1
        resources = workspace_node_resources(workspace, node, latest)
        artifacts = workspace_node_artifacts(workspace, node, latest)
        trace = workspace_node_trace(node, bound_jobs, state)
        latest_metadata = latest.get("metadata") if latest and isinstance(latest.get("metadata"), dict) else {}
        runtime_contract = latest_metadata.get("workflow_contract_node") if isinstance(latest_metadata.get("workflow_contract_node"), dict) else {}
        runtime_bundle = latest_metadata.get("execution_bundle") if isinstance(latest_metadata.get("execution_bundle"), dict) else {}
        if not runtime_contract:
            runtime_contract = workspace_node_workflow_contract_metadata(workspace, node)
        node_states.append(
            {
                "id": node_id,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "status": state,
                "agent_id": str(handler.get("agent_id") or "").strip(),
                "agent_name": str(handler.get("name") or "").strip(),
                "job_id": str(latest.get("id") or "").strip() if latest else "",
                "job_status": str(latest.get("status") or "").strip() if latest else "",
                "error": str(latest.get("error") or "").strip() if latest else "",
                "run_count": len(bound_jobs),
                "trace": trace,
                "artifacts": artifacts,
                "resources": resources,
                "workflow_contract_node": runtime_contract,
                "execution_bundle": runtime_bundle,
            }
        )

    selected_node = (
        next((item for item in node_states if item["status"] == "running"), None)
        or next((item for item in node_states if item["status"] == "queued"), None)
        or next((item for item in node_states if item["status"] == "failed"), None)
        or next((item for item in node_states if item["status"] == "pending"), None)
        or (node_states[-1] if node_states else None)
    )
    current_node_id = str(selected_node.get("id") or "").strip() if selected_node else ""
    current_agent_id = str(selected_node.get("agent_id") or "").strip() if selected_node else ""

    return {
        "current_node_id": current_node_id,
        "current_agent_id": current_agent_id,
        "counts": counts,
        "nodes": node_states,
        "last_job_id": str(latest_job.get("id") or "").strip() if latest_job else "",
        "last_job_status": str(latest_job.get("status") or "").strip() if latest_job else "",
        "latest_error": str(latest_error_job.get("error") or "").strip() if latest_error_job else "",
    }


def workspace_job_binding(job: dict[str, Any]) -> tuple[str, str]:
    metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    return (
        str(metadata.get("workspace_id") or "").strip(),
        str(metadata.get("node_id") or "").strip(),
    )


def workspace_job_sort_key(job: dict[str, Any]) -> tuple[int, str, str]:
    status = str(job.get("status") or "")
    active = 1 if status in {"running", "starting", "queued", "blocked"} else 0
    return (
        active,
        str(job.get("started_at") or job.get("created_at") or ""),
        str(job.get("id") or ""),
    )


def workspace_config_values(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").replace(",", "\n").splitlines()
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def compact_workspace_command(value: Any, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").strip().split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def workspace_path_probe(path_value: str, *, root: str = "", label: str = "path", source: str = "config") -> dict[str, Any]:
    raw = str(path_value or "").strip()
    item: dict[str, Any] = {
        "label": label,
        "path": raw,
        "source": source,
        "status": "planned",
    }
    if not raw:
        item["status"] = "missing"
        return item
    path = Path(raw).expanduser()
    if root and not path.is_absolute():
        path = Path(root).expanduser() / path
    item["path"] = str(path)
    try:
        item["resolved_path"] = str(path.resolve())
        item["exists"] = path.exists()
        item["status"] = "found" if item["exists"] else "expected"
        if item["exists"]:
            item["kind"] = "dir" if path.is_dir() else "file"
    except OSError:
        item["exists"] = False
        item["status"] = "unreadable"
    return item


def workspace_job_cached_log_tail(job: dict[str, Any] | None, *, max_lines: int = 240, max_bytes: int = 65536) -> str:
    if not job:
        return ""
    path_text = str(job.get("log_path") or "").strip()
    if not path_text:
        return ""
    path = Path(path_text).expanduser()
    try:
        if not path.exists() or path.is_dir():
            return ""
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0), os.SEEK_SET)
            data = handle.read(max_bytes)
    except OSError:
        return ""
    text = data.decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-max_lines:])


def workspace_log_path_artifact(label: str, path_text: str, exists_text: str, source: str) -> dict[str, Any]:
    exists = str(exists_text or "").strip().lower() == "true"
    return {
        "label": label,
        "path": str(path_text or "").strip(),
        "resolved_path": str(path_text or "").strip(),
        "source": source,
        "status": "found" if exists else "expected",
        "exists": exists,
    }


WORKSPACE_ENV_MANIFEST_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "environment.yml",
    "conda.yml",
    "conda.yaml",
}

WORKSPACE_DATA_DIR_NAMES = {"data", "dataset", "datasets", "dataset-cache", "data-cache"}
WORKSPACE_OUTPUT_DIR_NAMES = {"output", "outputs", "result", "results"}
WORKSPACE_ARTIFACT_DIR_NAMES = {"run", "runs", "log", "logs", "checkpoint", "checkpoints", "ckpt", "artifacts"}
WORKSPACE_RUN_ENTRY_NAMES = ("pytest.ini", "tests", "train.py", "main.py", "app.py")


def workspace_manifest_setup_suggestion(manifests: list[str]) -> str:
    names = {Path(str(item or "").strip()).name.lower() for item in manifests if str(item or "").strip()}
    if names.intersection({"environment.yml", "conda.yml", "conda.yaml"}):
        return "conda env update -f environment.yml"
    if "requirements.txt" in names:
        return "pip install -r requirements.txt"
    if "pyproject.toml" in names or "setup.py" in names:
        return "pip install -e ."
    return ""


def workspace_run_command_suggestion_from_entries(entries: list[str] | set[str] | tuple[str, ...]) -> str:
    names = {Path(str(item or "").strip().rstrip("/")).name.lower() for item in entries if str(item or "").strip()}
    if "pytest.ini" in names or "tests" in names:
        return "python -m pytest -q"
    if "train.py" in names:
        return "python train.py --help"
    if "main.py" in names:
        return "python main.py --help"
    if "app.py" in names:
        return "python app.py"
    return ""


def workspace_repo_inspect_top_level_artifacts(workspace_dir: str, top_level_text: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for raw_entry in str(top_level_text or "").split(","):
        entry = raw_entry.strip()
        if not entry or not entry.endswith("/"):
            continue
        name = entry.rstrip("/").strip()
        if not name:
            continue
        normalized = name.lower()
        path_text = str(Path(workspace_dir) / name) if workspace_dir else name
        if normalized in WORKSPACE_DATA_DIR_NAMES or "dataset" in normalized:
            artifacts.append(workspace_log_path_artifact("候选数据根", path_text, "True", "log"))
        elif normalized in WORKSPACE_OUTPUT_DIR_NAMES:
            artifacts.append(workspace_log_path_artifact("输出目录", path_text, "True", "log"))
            if normalized in {"result", "results"}:
                artifacts.append(workspace_log_path_artifact("指标路径", path_text, "True", "log"))
        elif normalized in WORKSPACE_ARTIFACT_DIR_NAMES:
            artifacts.append(workspace_log_path_artifact("产物路径", path_text, "True", "log"))
    return artifacts


def workspace_dedupe_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        path_text = str(item.get("resolved_path") or item.get("path") or "").strip()
        source = str(item.get("source") or "").strip()
        key = (label, path_text, source)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def parse_workspace_artifacts_from_log(kind: str, log_text: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    workspace_dir = ""
    current_candidate_root = ""
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("workspace_dir:"):
            workspace_dir = line.split(":", 1)[1].strip()
            if workspace_dir:
                artifacts.append(workspace_log_path_artifact("工作目录", workspace_dir, "True", "log"))
            continue
        for prefix, label in (
            ("data_root:", "数据根目录"),
            ("output_root:", "输出目录"),
            ("candidate_root:", "候选数据根"),
            ("artifact:", "产物路径"),
            ("metric:", "指标路径"),
        ):
            if not line.startswith(prefix):
                continue
            payload = line.split(":", 1)[1].strip()
            path_text, exists_text = payload, ""
            if " exists=" in payload:
                path_text, exists_text = payload.rsplit(" exists=", 1)
            artifacts.append(workspace_log_path_artifact(label, path_text.strip(), exists_text, "log"))
            if prefix == "candidate_root:" and str(exists_text).strip().lower() == "true":
                current_candidate_root = path_text.strip()
            break
        else:
            if line.startswith(("dataset_query:", "dataset_plan_query:")):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "检索词",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("dataset_source:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "数据来源线索",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("expected_layout:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    artifacts.append(
                        {
                            "label": "数据结构要求",
                            "path": value,
                            "source": "log",
                            "status": "planned",
                        }
                    )
            elif line.startswith("match:") and current_candidate_root:
                name = line.split(":", 1)[1].strip().split(" (", 1)[0].strip()
                if name:
                    artifacts.append(
                        {
                            "label": "候选数据集",
                            "path": str(Path(current_candidate_root) / name),
                            "resolved_path": str(Path(current_candidate_root) / name),
                            "source": "log",
                            "status": "found",
                            "exists": True,
                        }
                    )
            elif line.startswith("found:"):
                name = line.split(":", 1)[1].strip()
                if name:
                    normalized = Path(name).name.lower()
                    path_text = str(Path(workspace_dir) / name) if workspace_dir else name
                    if normalized in WORKSPACE_ENV_MANIFEST_NAMES:
                        artifacts.append(workspace_log_path_artifact("环境清单", path_text, "True", "log"))
                    elif normalized.startswith("readme"):
                        artifacts.append(workspace_log_path_artifact("项目文档", path_text, "True", "log"))
            elif line.startswith("top_level:"):
                artifacts.extend(workspace_repo_inspect_top_level_artifacts(workspace_dir, line.split(":", 1)[1].strip()))
            elif line.startswith("found_manifest:"):
                name = line.split(":", 1)[1].strip()
                if name:
                    artifacts.append(workspace_path_probe(name, root=workspace_dir, label="环境清单", source="log"))
    return workspace_dedupe_artifacts(artifacts)


def parse_workspace_resources_from_log(kind: str, log_text: str) -> dict[str, Any]:
    resources: dict[str, Any] = {}
    manifests: list[str] = []
    gpu_snapshot: list[dict[str, Any]] = []
    repo_entries: list[str] = []
    dataset_queries: list[str] = []
    dataset_sources: list[str] = []
    expected_layout = ""
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("suggest_setup:"):
            resources["setup_suggestion"] = line.split(":", 1)[1].strip()
        elif line.startswith("suggest_run:"):
            resources["run_suggestion"] = line.split(":", 1)[1].strip()
        elif line.startswith("found_manifest:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in manifests:
                manifests.append(value)
        elif line.startswith("found:"):
            value = line.split(":", 1)[1].strip()
            if Path(value).name.lower() in WORKSPACE_ENV_MANIFEST_NAMES and value not in manifests:
                manifests.append(value)
            if value:
                repo_entries.append(value)
        elif line.startswith("top_level:"):
            repo_entries.extend(
                [item.strip().rstrip("/") for item in line.split(":", 1)[1].split(",") if item.strip()]
            )
        elif line.startswith("[gpu.allocate]"):
            resources["gpu_policy_summary"] = line
        elif line.startswith("CUDA_VISIBLE_DEVICES=") or line.startswith("CUDA_VISIBLE_DEVICES:"):
            resources["cuda_visible_devices"] = line.split("=", 1)[1].strip() if "=" in line else line.split(":", 1)[1].strip()
        elif kind == "gpu.allocate" and "," in line:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 4 and parts[0].isdigit():
                gpu_snapshot.append(
                    {
                        "index": parts[0],
                        "name": parts[1],
                        "memory_free": parts[2],
                        "utilization": parts[3],
                    }
                )
        elif kind == "dataset.find" and line.startswith(("dataset_query:", "dataset_plan_query:")):
            value = line.split(":", 1)[1].strip()
            if value and value not in dataset_queries:
                dataset_queries.append(value)
        elif kind == "dataset.find" and line.startswith("dataset_source:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in dataset_sources:
                dataset_sources.append(value)
        elif kind == "dataset.find" and line.startswith("expected_layout:"):
            expected_layout = line.split(":", 1)[1].strip()
    if manifests:
        resources["found_manifests"] = manifests
    if manifests and not resources.get("setup_suggestion"):
        setup_suggestion = workspace_manifest_setup_suggestion(manifests)
        if setup_suggestion:
            resources["setup_suggestion"] = setup_suggestion
    if kind == "repo.inspect" and not resources.get("run_suggestion"):
        run_suggestion = workspace_run_command_suggestion_from_entries(repo_entries)
        if run_suggestion:
            resources["run_suggestion"] = run_suggestion
    if dataset_queries:
        resources["dataset_queries"] = dataset_queries[:12]
    if dataset_sources:
        resources["dataset_sources"] = dataset_sources[:12]
    if expected_layout:
        resources["expected_layout"] = expected_layout
    if gpu_snapshot:
        resources["gpu_snapshot"] = gpu_snapshot[:16]
    return resources


WORKSPACE_METRIC_PATTERN = re.compile(
    r"(?i)\b(?P<key>"
    r"val[_\s-]?loss|train[_\s-]?loss|test[_\s-]?loss|loss|"
    r"accuracy|acc|top[_\s-]?1|top[_\s-]?5|f1|precision|recall|auc|"
    r"mAP|map|bleu|rouge[_\s-]?l|rougeL|perplexity|ppl|wer|cer|psnr|ssim"
    r")\b\s*[:=]\s*(?P<value>-?\d+(?:\.\d+)?(?:e[-+]?\d+)?%?)"
)


def normalize_workspace_metric_key(value: str) -> str:
    key = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "acc": "accuracy",
        "map": "mAP",
        "rougel": "rougeL",
        "rouge_l": "rougeL",
        "ppl": "perplexity",
        "top_1": "top1",
        "top_5": "top5",
    }
    return aliases.get(key, key)


def parse_workspace_metrics_from_log(kind: str, log_text: str) -> list[dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for raw_line in str(log_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for match in WORKSPACE_METRIC_PATTERN.finditer(line):
            key = normalize_workspace_metric_key(match.group("key"))
            value = match.group("value")
            metrics[key] = {
                "key": key,
                "label": key,
                "value": value,
                "raw": compact_workspace_command(line, limit=180),
                "source": "log",
                "node_kind": kind,
                "status": "found",
            }
    return list(metrics.values())[:24]


def workspace_node_artifacts(
    workspace: dict[str, Any],
    node: dict[str, Any],
    latest_job: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    kind = str(node.get("kind") or "").strip()
    workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
    artifacts: list[dict[str, Any]] = []

    if workspace_dir and kind in {"repo.clone", "path.resolve", "repo.inspect", "env.infer", "env.prepare", "run.command", "artifact.collect"}:
        artifacts.append(workspace_path_probe(workspace_dir, label="工作目录", source="workspace"))

    if kind == "path.resolve":
        for value in workspace_config_values(config.get("data_roots"))[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="数据根目录", source="path.resolve"))
        for value in workspace_config_values(config.get("output_roots") or "runs\noutputs\ncheckpoints\nlogs")[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="输出目录", source="path.resolve"))
    elif kind == "dataset.find":
        for value in workspace_config_values(config.get("dataset_hints"))[:12]:
            artifacts.append(workspace_path_probe(value, label="数据集线索", source="dataset.find"))
        for value in workspace_config_values(config.get("data_roots"))[:12]:
            artifacts.append(workspace_path_probe(value, label="数据根目录", source="dataset.find"))
        query = str(config.get("query") or workspace.get("brief") or "").strip()
        if query:
            artifacts.append(
                {
                    "label": "检索词",
                    "path": query,
                    "source": "dataset.find",
                    "status": "planned",
                }
            )
    elif kind == "env.infer":
        for value in workspace_config_values(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py")[:12]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="环境清单", source="env.infer"))
    elif kind == "artifact.collect":
        for value in workspace_config_values(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs")[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="产物路径", source="artifact.collect"))
        for value in workspace_config_values(config.get("metric_paths"))[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="指标路径", source="artifact.collect"))
    elif kind == "eval.report":
        for value in workspace_config_values(config.get("metric_paths"))[:16]:
            artifacts.append(workspace_path_probe(value, root=workspace_dir, label="指标路径", source="eval.report"))

    if latest_job:
        log_path = str(latest_job.get("log_path") or "").strip()
        if log_path:
            artifacts.append(workspace_path_probe(log_path, label="最近日志", source="job"))
        remote_log_path = str(latest_job.get("remote_log_path") or "").strip()
        if remote_log_path:
            artifacts.append(
                {
                    "label": "远端日志",
                    "path": remote_log_path,
                    "source": "job",
                    "status": "expected",
                }
            )
        log_text = workspace_job_cached_log_tail(latest_job)
        if log_text:
            artifacts.extend(parse_workspace_artifacts_from_log(kind, log_text))

    return workspace_dedupe_artifacts(artifacts)


def workspace_node_resources(
    workspace: dict[str, Any],
    node: dict[str, Any],
    latest_job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    metadata = latest_job.get("metadata") if latest_job and isinstance(latest_job.get("metadata"), dict) else {}
    kind = str(node.get("kind") or "").strip()
    gpu_policy = str(config.get("gpu_policy") or ("none" if kind in {"repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "env.prepare", "artifact.collect", "eval.report"} else "auto")).strip().lower() or "auto"
    if latest_job:
        gpu_value = latest_job.get("gpu_index")
    elif gpu_policy in {"cpu", "none", "no_gpu"}:
        gpu_value = "none"
    else:
        gpu_value = str(config.get("gpu_index") or "auto").strip() or "auto"
    if gpu_value is None or not str(gpu_value).strip():
        gpu_value = "auto"
    resources = {
        "server_id": str((latest_job or {}).get("server_id") or config.get("server_id") or "auto").strip() or "auto",
        "requested_server_id": str((latest_job or {}).get("requested_server_id") or config.get("server_id") or "auto").strip() or "auto",
        "gpu_index": str(gpu_value),
        "gpu_policy": gpu_policy,
        "execution_mode": str(metadata.get("execution_mode") or ("gpu" if kind in {"gpu.allocate", "run.command"} and gpu_policy not in {"cpu", "none", "no_gpu"} else "cpu")),
        "cwd": str((latest_job or {}).get("cwd") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip(),
        "env_name": str((latest_job or {}).get("env_name") or config.get("env_name") or workspace_env.get("name") or "").strip(),
        "depends_on": [str(item) for item in ((latest_job or {}).get("target_job_ids") or []) if str(item).strip()],
        "wait_for_idle": bool((latest_job or {}).get("wait_for_idle", kind in WORKSPACE_EXECUTABLE_NODE_KINDS)),
    }
    runtime_binding = metadata.get("runtime_binding") if isinstance(metadata.get("runtime_binding"), dict) else {}
    if runtime_binding:
        resources["runtime_binding"] = copy.deepcopy(runtime_binding)
        for key in ("server_id", "gpu_index", "gpu_policy", "execution_mode", "cwd", "env_name", "wait_for_idle"):
            if key in runtime_binding and runtime_binding.get(key) not in (None, ""):
                resources[key] = runtime_binding[key]
    scheduler_binding = metadata.get("scheduler_binding") if isinstance(metadata.get("scheduler_binding"), dict) else {}
    if scheduler_binding:
        resources["scheduler_binding"] = copy.deepcopy(scheduler_binding)
        resources["scheduler_status"] = str(scheduler_binding.get("status") or "").strip()
        resources["scheduler_summary"] = str(scheduler_binding.get("summary") or "").strip()
        resources["scheduler_reasons"] = copy.deepcopy(
            scheduler_binding.get("reasons") if isinstance(scheduler_binding.get("reasons"), list) else []
        )
    log_text = workspace_job_cached_log_tail(latest_job)
    if log_text:
        resources.update(parse_workspace_resources_from_log(kind, log_text))
        metrics = parse_workspace_metrics_from_log(kind, log_text)
        if metrics:
            resources["metrics"] = metrics
    return resources


def workspace_node_trace(
    node: dict[str, Any],
    bound_jobs: list[dict[str, Any]],
    state: str,
) -> list[dict[str, Any]]:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    trace: list[dict[str, Any]] = [
        {
            "status": "planned",
            "label": "节点已编排",
            "detail": f"{str(node.get('kind') or '').strip()} · {str(handler.get('name') or handler.get('agent_id') or '未指派 Agent').strip()}",
            "at": str(node.get("updated_at") or node.get("created_at") or "").strip(),
        }
    ]
    if not bound_jobs:
        if state == "pending":
            trace.append(
                {
                    "status": "pending",
                    "label": "等待执行",
                    "detail": "还没有提交到调度队列。",
                    "at": "",
                }
            )
        return trace

    for job in sorted(bound_jobs, key=workspace_job_sort_key):
        job_id = str(job.get("id") or "").strip()
        created_at = str(job.get("created_at") or "").strip()
        trace.append(
            {
                "status": "queued",
                "label": "已提交队列",
                "detail": f"{job_id} · {compact_workspace_command(job.get('command_display') or job.get('command'))}",
                "at": created_at,
                "job_id": job_id,
            }
        )
        dependency_ids = [str(item).strip() for item in job.get("target_job_ids", []) if str(item).strip()]
        if dependency_ids:
            trace.append(
                {
                    "status": "blocked" if str(job.get("status") or "") == "queued" and str(job.get("error") or "").startswith("waiting for dependency") else "queued",
                    "label": "上游依赖",
                    "detail": "等待 " + ", ".join(dependency_ids),
                    "at": created_at,
                    "job_id": job_id,
                }
            )
        started_at = str(job.get("started_at") or "").strip()
        if started_at:
            server_id = str(job.get("server_id") or "").strip() or "auto"
            gpu_index = str(job.get("gpu_index") if job.get("gpu_index") is not None else "auto")
            trace.append(
                {
                    "status": "running",
                    "label": "开始执行",
                    "detail": f"server={server_id} · gpu={gpu_index}",
                    "at": started_at,
                    "job_id": job_id,
                }
            )
        error = str(job.get("error") or "").strip()
        finished_at = str(job.get("finished_at") or "").strip()
        job_status = str(job.get("status") or "").strip() or "queued"
        if finished_at:
            trace.append(
                {
                    "status": job_status,
                    "label": workspace_execution_trace_label(job_status),
                    "detail": error or f"任务状态：{job_status}",
                    "at": finished_at,
                    "job_id": job_id,
                }
            )
        elif error:
            trace.append(
                {
                    "status": "blocked" if job_status == "queued" else job_status,
                    "label": "调度提示",
                    "detail": error,
                    "at": started_at or created_at,
                    "job_id": job_id,
                }
            )
    return trace[-10:]


def workspace_execution_trace_label(status: str) -> str:
    if status == "done":
        return "执行完成"
    if status == "failed":
        return "执行失败"
    if status == "stopped":
        return "已停止"
    if status == "running":
        return "运行中"
    if status in {"queued", "blocked"}:
        return "等待中"
    return "状态更新"


def workspace_node_config_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    node = next(
        (
            item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        None,
    )
    return node.get("config") if node and isinstance(node.get("config"), dict) else {}


def workspace_node_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(
        (
            item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        {},
    )


def workspace_has_node_kind(workspace: dict[str, Any], kind: str) -> bool:
    return any(
        isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
    )


def workspace_execution_node_by_kind(execution: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(
        (
            item for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        {},
    )


def workspace_automation_check(
    check_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": check_id,
        "label": label,
        "status": normalized,
        "title": title,
        "detail": detail,
        "action": action,
        "node_kind": node_kind,
    }


WORKSPACE_ISSUE_FIELD_BY_KIND = {
    "path.resolve": "workspace_dir/data_roots/output_roots",
    "dataset.find": "query/data_roots/dataset_hints",
    "env.infer": "manifest_paths",
    "env.prepare": "setup_command",
    "gpu.allocate": "server_id/gpu_policy",
    "run.command": "run_command",
    "artifact.collect": "artifact_paths/metric_paths",
    "eval.report": "report_command/metric_paths",
}


def workspace_enrich_readiness_issue(workspace: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    issue = copy.deepcopy(item)
    node_kind = str(issue.get("node_kind") or issue.get("kind") or "").strip()
    node = workspace_node_by_kind(workspace, node_kind) if node_kind else {}
    if node:
        issue.setdefault("node_id", str(node.get("id") or "").strip())
        issue.setdefault("node_title", str(node.get("title") or node_kind).strip())
        issue.setdefault("node_kind", node_kind)
    if node_kind and not issue.get("field"):
        issue["field"] = WORKSPACE_ISSUE_FIELD_BY_KIND.get(node_kind, "")
    if not issue.get("fix_action"):
        issue["fix_action"] = str(issue.get("action") or issue.get("detail") or "定位节点后补齐配置。").strip()
    if not issue.get("origin"):
        issue["origin"] = str(issue.get("id") or issue.get("type") or "readiness").strip()
    return issue


def workspace_status_priority(status: str) -> int:
    return {
        "failed": 0,
        "blocked": 1,
        "warning": 2,
        "draft": 3,
        "running": 4,
        "ready": 5,
        "done": 6,
    }.get(status, 2)


def workspace_evidence_item(
    label: str,
    value: str,
    *,
    status: str = "planned",
    source: str = "",
    node_kind: str = "",
) -> dict[str, Any]:
    return {
        "label": str(label or "").strip(),
        "value": str(value or "").strip(),
        "status": str(status or "planned").strip() or "planned",
        "source": str(source or "").strip(),
        "node_kind": str(node_kind or "").strip(),
    }


def workspace_add_evidence_item(
    group: dict[str, Any],
    item: dict[str, Any],
    seen: set[tuple[str, str, str]],
    *,
    limit: int = 8,
) -> None:
    value = str(item.get("value") or "").strip()
    if not value:
        return
    key = (
        str(item.get("label") or "").strip(),
        value,
        str(item.get("node_kind") or "").strip(),
    )
    if key in seen:
        return
    seen.add(key)
    group["count"] = safe_int(group.get("count"), 0) + 1
    if len(group["items"]) < limit:
        group["items"].append(item)


def derive_workspace_automation_evidence(execution: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {
        "paths": {"id": "paths", "label": "路径", "title": "路径证据", "count": 0, "items": []},
        "dataset": {"id": "dataset", "label": "数据集", "title": "数据证据", "count": 0, "items": []},
        "env": {"id": "env", "label": "环境", "title": "环境证据", "count": 0, "items": []},
        "gpu": {"id": "gpu", "label": "GPU", "title": "资源证据", "count": 0, "items": []},
        "run": {"id": "run", "label": "运行入口", "title": "运行入口证据", "count": 0, "items": []},
        "artifact": {"id": "artifact", "label": "产物", "title": "产物证据", "count": 0, "items": []},
        "metric": {"id": "metric", "label": "指标", "title": "指标证据", "count": 0, "items": []},
    }
    seen: set[tuple[str, str, str]] = set()
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    artifact_label_groups = {
        "工作目录": "paths",
        "项目文档": "paths",
        "数据根目录": "paths",
        "输出目录": "paths",
        "候选数据根": "dataset",
        "候选数据集": "dataset",
        "数据集线索": "dataset",
        "检索词": "dataset",
        "数据来源线索": "dataset",
        "数据结构要求": "dataset",
        "环境清单": "env",
        "产物路径": "artifact",
        "指标路径": "artifact",
        "最近日志": "artifact",
        "远端日志": "artifact",
    }
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_kind = str(node.get("kind") or "").strip()
        artifacts = node.get("artifacts") if isinstance(node.get("artifacts"), list) else []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            label = str(artifact.get("label") or artifact.get("source") or "").strip()
            group_id = artifact_label_groups.get(label)
            if not group_id:
                continue
            value = str(artifact.get("resolved_path") or artifact.get("path") or "").strip()
            workspace_add_evidence_item(
                groups[group_id],
                workspace_evidence_item(
                    label,
                    value,
                    status=str(artifact.get("status") or "planned"),
                    source=str(artifact.get("source") or ""),
                    node_kind=node_kind,
                ),
                seen,
            )
        resources = node.get("resources") if isinstance(node.get("resources"), dict) else {}
        if node_kind in {"env.infer", "repo.inspect"}:
            setup = str(resources.get("setup_suggestion") or "").strip()
            if setup:
                workspace_add_evidence_item(
                    groups["env"],
                    workspace_evidence_item("安装建议", setup, status="found", source="resource", node_kind=node_kind),
                    seen,
                )
            for manifest in (resources.get("found_manifests") if isinstance(resources.get("found_manifests"), list) else []):
                workspace_add_evidence_item(
                    groups["env"],
                    workspace_evidence_item("清单文件", str(manifest), status="found", source="resource", node_kind=node_kind),
                    seen,
                )
        if node_kind in {"repo.inspect", "run.command"}:
            run_suggestion = str(resources.get("run_suggestion") or "").strip()
            if run_suggestion:
                workspace_add_evidence_item(
                    groups["run"],
                    workspace_evidence_item("运行命令候选", run_suggestion, status="found", source="resource", node_kind=node_kind),
                    seen,
                )
        if node_kind == "gpu.allocate":
            server_id = str(resources.get("server_id") or "").strip()
            gpu_index = str(resources.get("gpu_index") or "").strip()
            gpu_policy = str(resources.get("gpu_policy") or "").strip()
            if server_id or gpu_index or gpu_policy:
                workspace_add_evidence_item(
                    groups["gpu"],
                    workspace_evidence_item(
                        "调度计划",
                        f"server={server_id or 'auto'} · gpu={gpu_index or gpu_policy or 'auto'}",
                        status="planned",
                        source="resource",
                        node_kind=node_kind,
                    ),
                    seen,
                )
        metrics = resources.get("metrics") if isinstance(resources.get("metrics"), list) else []
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            key = str(metric.get("label") or metric.get("key") or "metric").strip()
            value = str(metric.get("value") or "").strip()
            if not value:
                continue
            workspace_add_evidence_item(
                groups["metric"],
                workspace_evidence_item(
                    key,
                    f"{key}={value}",
                    status=str(metric.get("status") or "found"),
                    source=str(metric.get("source") or "log"),
                    node_kind=node_kind,
                ),
                seen,
            )
            for gpu in (resources.get("gpu_snapshot") if isinstance(resources.get("gpu_snapshot"), list) else []):
                if not isinstance(gpu, dict):
                    continue
                workspace_add_evidence_item(
                    groups["gpu"],
                    workspace_evidence_item(
                        "GPU 快照",
                        f"{gpu.get('index', '')} · {gpu.get('name', '')} · {gpu.get('memory_free', '')} free · {gpu.get('utilization', '')}",
                        status="found",
                        source="resource",
                        node_kind=node_kind,
                    ),
                    seen,
                )
    evidence = []
    for group in groups.values():
        count = safe_int(group.get("count"), 0)
        group["status"] = "ready" if count else "draft"
        group["detail"] = f"{count} 条证据" if count else "等待自动发现"
        evidence.append(group)
    return evidence


def workspace_run_node_phase(kind: str) -> str:
    if kind in {"repo.clone", "source.repo", "source.paper", "source.idea"}:
        return "source"
    if kind in {"path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate"}:
        return "discover"
    if kind == "env.prepare":
        return "setup"
    if kind == "run.command":
        return "run"
    if kind == "artifact.collect":
        return "collect"
    if kind == "eval.report":
        return "report"
    return "other"


def workspace_run_phase_label(phase: str) -> str:
    return {
        "source": "来源",
        "discover": "发现",
        "setup": "环境",
        "run": "运行",
        "collect": "收集",
        "report": "报告",
        "other": "其他",
    }.get(phase, phase)


def workspace_node_required_tool_id(kind: str) -> str:
    return {
        "repo.clone": "repo.clone",
        "path.resolve": "path.resolve",
        "repo.inspect": "repo.inspect",
        "dataset.find": "dataset.find",
        "env.infer": "env.infer",
        "env.prepare": "env.prepare",
        "gpu.allocate": "gpu.allocate",
        "run.command": "job.run",
        "artifact.collect": "artifact.collect",
        "eval.report": "report.write",
    }.get(str(kind or "").strip(), "")


def workspace_model_route_for_agent(model: dict[str, Any], agent: dict[str, Any] | None) -> dict[str, str]:
    routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
    workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
    agent_profile_id = str((agent or {}).get("provider_profile_id") or "").strip()
    if routing_mode == "agent_override" and agent_profile_id:
        return {
            "status": "ready",
            "routing_mode": routing_mode,
            "source": "agent_override",
            "effective_profile_id": agent_profile_id,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "label": "Agent 覆盖",
        }
    if workspace_profile_id:
        return {
            "status": "ready",
            "routing_mode": routing_mode,
            "source": "workspace_default",
            "effective_profile_id": workspace_profile_id,
            "workspace_profile_id": workspace_profile_id,
            "agent_profile_id": agent_profile_id,
            "label": "项目默认",
        }
    return {
        "status": "warning",
        "routing_mode": routing_mode,
        "source": "unconfigured",
        "effective_profile_id": "",
        "workspace_profile_id": workspace_profile_id,
        "agent_profile_id": agent_profile_id,
        "label": "未配置 Profile",
    }


def workspace_agent_topology_gap(
    gap_type: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    phase: str = "",
    node_id: str = "",
    node_kind: str = "",
    agent_id: str = "",
    tool_id: str = "",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "type": str(gap_type or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "phase": str(phase or "").strip(),
        "node_id": str(node_id or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "agent_id": str(agent_id or "").strip(),
        "tool_id": str(tool_id or "").strip(),
    }


def workspace_topology_status(gaps: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("status") or "") for item in gaps if isinstance(item, dict)}
    if statuses.intersection({"blocked", "failed"}):
        return "blocked"
    if statuses.intersection({"warning", "draft"}):
        return "warning"
    return "ready"


def derive_workspace_agent_topology(workspace: dict[str, Any], run_plan: dict[str, Any]) -> dict[str, Any]:
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {
        str(tool.get("id") or "").strip(): tool
        for tool in tools
        if isinstance(tool, dict) and str(tool.get("id") or "").strip()
    }
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {
        str(agent.get("id") or "").strip(): agent
        for agent in agents
        if isinstance(agent, dict) and str(agent.get("id") or "").strip()
    }
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    plan_nodes = {
        str(item.get("id") or "").strip(): item
        for item in (run_plan.get("nodes") if isinstance(run_plan.get("nodes"), list) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]
    stage_index: dict[str, dict[str, Any]] = {}
    stage_agent_ids: dict[str, set[str]] = {}
    stage_tool_ids: dict[str, set[str]] = {}
    assigned_agent_ids: set[str] = set()
    required_tool_ids: set[str] = set()
    topology_gaps: list[dict[str, Any]] = []
    missing_agent_count = 0

    def stage_for_phase(phase: str) -> dict[str, Any]:
        phase_id = phase if phase in phase_order else "other"
        if phase_id not in stage_index:
            stage_index[phase_id] = {
                "id": phase_id,
                "label": workspace_run_phase_label(phase_id),
                "status": "ready",
                "node_count": 0,
                "assigned_node_count": 0,
                "node_kinds": [],
                "nodes": [],
                "agents": [],
                "tools": [],
                "model_profiles": [],
                "gaps": [],
            }
            stage_agent_ids[phase_id] = set()
            stage_tool_ids[phase_id] = set()
        return stage_index[phase_id]

    def add_gap(stage: dict[str, Any], gap: dict[str, Any]) -> None:
        stage["gaps"].append(gap)
        topology_gaps.append(gap)

    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        phase = workspace_run_node_phase(kind)
        stage = stage_for_phase(phase)
        phase_id = str(stage["id"])
        plan_node = plan_nodes.get(str(node.get("id") or "").strip(), {})
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        mode = str(handler.get("mode") or "agent").strip() or "agent"
        agent_id = str(handler.get("agent_id") or plan_node.get("agent_id") or "").strip()
        agent = agent_index.get(agent_id)
        required_tool_id = workspace_node_required_tool_id(kind)
        if required_tool_id:
            required_tool_ids.add(required_tool_id)
            stage_tool_ids[phase_id].add(required_tool_id)
        stage["node_count"] = safe_int(stage.get("node_count"), 0) + 1
        if kind not in stage["node_kinds"]:
            stage["node_kinds"].append(kind)
        if len(stage["nodes"]) < 8:
            stage["nodes"].append(
                {
                    "id": str(node.get("id") or "").strip(),
                    "kind": kind,
                    "title": str(node.get("title") or kind).strip(),
                    "status": str(plan_node.get("status") or "warning").strip(),
                    "agent_id": agent_id,
                    "agent_name": str(handler.get("name") or (agent.get("name") if agent else "") or plan_node.get("agent_name") or "").strip(),
                    "required_tool_id": required_tool_id,
                }
            )

        if mode != "human" and not agent_id:
            missing_agent_count += 1
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "missing_agent",
                    "blocked",
                    "节点缺 Agent",
                    f"{str(node.get('title') or kind).strip()} 没有绑定执行 Agent。",
                    "在配置中心把节点绑定到对应 Agent。",
                    phase=phase_id,
                    node_id=str(node.get("id") or "").strip(),
                    node_kind=kind,
                ),
            )
            continue
        if not agent_id:
            continue
        if not agent:
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "unknown_agent",
                    "blocked",
                    "Agent 不在实例快照里",
                    f"{agent_id} 没有对应的 Agent 定义。",
                    "恢复默认 Agent 或重新选择节点执行者。",
                    phase=phase_id,
                    node_id=str(node.get("id") or "").strip(),
                    node_kind=kind,
                    agent_id=agent_id,
                ),
            )
            continue

        stage["assigned_node_count"] = safe_int(stage.get("assigned_node_count"), 0) + 1
        assigned_agent_ids.add(agent_id)
        if agent_id not in stage_agent_ids[phase_id]:
            stage_agent_ids[phase_id].add(agent_id)
            agent_tool_ids = parse_tag_list(agent.get("tools", []))
            valid_tools = [tool_index[tool_id] for tool_id in agent_tool_ids if tool_id in tool_index]
            enabled_tools = [tool for tool in valid_tools if tool.get("enabled", True)]
            route = workspace_model_route_for_agent(model, agent)
            stage["agents"].append(
                {
                    "id": agent_id,
                    "name": str(agent.get("name") or agent_id).strip(),
                    "role": str(agent.get("role") or "").strip(),
                    "enabled": bool(agent.get("enabled", True)),
                    "tool_count": len(valid_tools),
                    "enabled_tool_count": len(enabled_tools),
                    "tools": [
                        {
                            "id": str(tool.get("id") or "").strip(),
                            "label": str(tool.get("label") or tool.get("id") or "").strip(),
                            "category": str(tool.get("category") or "general").strip(),
                            "enabled": bool(tool.get("enabled", True)),
                        }
                        for tool in valid_tools[:8]
                    ],
                    "model": route,
                }
            )
            if not agent.get("enabled", True):
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "agent_disabled",
                        "blocked",
                        "Agent 已停用",
                        f"{str(agent.get('name') or agent_id).strip()} 已绑定到节点但处于停用状态。",
                        "启用 Agent 或把节点交给其他 Agent。",
                        phase=phase_id,
                        agent_id=agent_id,
                    ),
                )
            if not valid_tools:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "agent_without_tools",
                        "warning",
                        "Agent 没有可用工具",
                        f"{str(agent.get('name') or agent_id).strip()} 的工具 allowlist 为空或全都不存在。",
                        "给 Agent 绑定对应工具，至少覆盖它负责的节点动作。",
                        phase=phase_id,
                        agent_id=agent_id,
                    ),
                )

        if required_tool_id:
            agent_tool_ids = parse_tag_list(agent.get("tools", []))
            required_tool = tool_index.get(required_tool_id)
            if required_tool_id not in agent_tool_ids:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "required_tool_unbound",
                        "blocked",
                        "关键工具未授权",
                        f"{str(agent.get('name') or agent_id).strip()} 负责 {kind}，但 allowlist 没有 {required_tool_id}。",
                        "把关键工具加入该 Agent，或重新分配节点。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )
            elif not required_tool:
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "tool_missing",
                        "blocked",
                        "工具定义缺失",
                        f"{required_tool_id} 不在当前实例工具表里。",
                        "恢复默认工具或在工具注册里补齐定义。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )
            elif not required_tool.get("enabled", True):
                add_gap(
                    stage,
                    workspace_agent_topology_gap(
                        "tool_disabled",
                        "blocked",
                        "关键工具已停用",
                        f"{str(required_tool.get('label') or required_tool_id).strip()} 已停用。",
                        "启用工具或换一个可执行工具。",
                        phase=phase_id,
                        node_id=str(node.get("id") or "").strip(),
                        node_kind=kind,
                        agent_id=agent_id,
                        tool_id=required_tool_id,
                    ),
                )

    stages = [stage_index[phase] for phase in phase_order if phase in stage_index]
    for stage in stages:
        phase_id = str(stage.get("id") or "")
        for tool_id in sorted(stage_tool_ids.get(phase_id, set())):
            tool = tool_index.get(tool_id)
            stage["tools"].append(
                {
                    "id": tool_id,
                    "label": str((tool or {}).get("label") or tool_id).strip(),
                    "category": str((tool or {}).get("category") or "general").strip(),
                    "enabled": bool((tool or {}).get("enabled", bool(tool))),
                }
            )
        ready_profiles = [
            str(agent.get("model", {}).get("effective_profile_id") or "").strip()
            for agent in stage.get("agents", [])
            if isinstance(agent, dict)
        ]
        ready_profiles = [item for item in ready_profiles if item]
        stage["model_profiles"] = list(dict.fromkeys(ready_profiles))
        if stage.get("agents") and not ready_profiles:
            add_gap(
                stage,
                workspace_agent_topology_gap(
                    "model_profile",
                    "warning",
                    "AI Profile 未配置",
                    f"{str(stage.get('label') or phase_id)} 阶段的 Agent 还没有有效模型路由。",
                    "给项目设置默认 Provider Profile，或启用 agent_override 并给 Agent 单独配置。",
                    phase=phase_id,
                ),
            )
        stage["status"] = workspace_topology_status(stage.get("gaps") if isinstance(stage.get("gaps"), list) else [])

    enabled_tools = [tool for tool in tools if tool.get("enabled", True)]
    enabled_agents = [agent for agent in agents if agent.get("enabled", True)]
    tool_gap_count = len([
        gap for gap in topology_gaps
        if str(gap.get("type") or "") in {"required_tool_unbound", "tool_missing", "tool_disabled", "agent_without_tools"}
    ])
    effective_profile_count = len({
        str(agent.get("model", {}).get("effective_profile_id") or "").strip()
        for stage in stages
        for agent in (stage.get("agents") if isinstance(stage.get("agents"), list) else [])
        if isinstance(agent, dict) and str(agent.get("model", {}).get("effective_profile_id") or "").strip()
    })
    layers = {
        "agent": {
            "label": "Agent",
            "status": "blocked" if missing_agent_count or any(str(gap.get("type") or "") in {"unknown_agent", "agent_disabled"} for gap in topology_gaps) else "ready" if assigned_agent_ids else "warning",
            "total_count": len(agents),
            "enabled_count": len(enabled_agents),
            "assigned_count": len(assigned_agent_ids),
            "missing_count": missing_agent_count,
        },
        "tool": {
            "label": "Tool",
            "status": "blocked" if tool_gap_count else "ready" if required_tool_ids else "warning",
            "total_count": len(tools),
            "enabled_count": len(enabled_tools),
            "required_count": len(required_tool_ids),
            "gap_count": tool_gap_count,
        },
        "ai": {
            "label": "AI",
            "status": "ready" if effective_profile_count else "warning" if assigned_agent_ids else "draft",
            "routing_mode": str(model.get("routing_mode") or "workspace_default"),
            "workspace_profile_id": str(model.get("provider_profile_id") or "").strip(),
            "effective_profile_count": effective_profile_count,
            "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
        },
    }
    status = workspace_topology_status(topology_gaps)
    return {
        "status": status,
        "summary": f"{len(stages)} 个阶段 · {len(assigned_agent_ids)} 个 Agent · {len(required_tool_ids)} 个关键工具 · {len(topology_gaps)} 个缺口",
        "stage_count": len(stages),
        "agent_count": len(assigned_agent_ids),
        "required_tool_count": len(required_tool_ids),
        "gap_count": len(topology_gaps),
        "layers": layers,
        "stages": stages,
        "gaps": topology_gaps[:12],
    }


def workspace_node_command_summary_for_plan(workspace: dict[str, Any], node: dict[str, Any]) -> tuple[str, str]:
    kind = str(node.get("kind") or "").strip()
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    if kind == "repo.clone":
        repo_url = str(config.get("repo_url") or source.get("repo_url") or "").strip()
        return (repo_url or "等待仓库地址", "ready" if repo_url else "blocked")
    if kind == "path.resolve":
        values = workspace_config_values(config.get("data_roots")) + workspace_config_values(config.get("output_roots"))
        detail = " · ".join([workspace_dir or "未设工作目录", f"{len(values)} 条路径线索"])
        return (detail, "ready" if workspace_dir or values else "warning")
    if kind == "repo.inspect":
        return (workspace_dir or "等待工作目录", "ready" if workspace_dir else "warning")
    if kind == "dataset.find":
        query = str(config.get("query") or workspace.get("brief") or source.get("repo_url") or source.get("paper_url") or "").strip()
        hints = len(workspace_config_values(config.get("dataset_hints")) + workspace_config_values(config.get("data_roots")))
        return (query or f"{hints} 条数据线索" or "等待数据线索", "ready" if query or hints else "warning")
    if kind == "env.infer":
        manifest_paths = workspace_config_values(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py")
        return (", ".join(manifest_paths[:4]) or "等待环境清单", "ready" if workspace_dir or manifest_paths else "warning")
    if kind == "env.prepare":
        command = str(config.get("setup_command") or "").strip()
        return (compact_workspace_command(command) if command else "缺 setup_command", "ready" if command else "blocked")
    if kind == "gpu.allocate":
        server_id = str(config.get("server_id") or "auto").strip() or "auto"
        gpu_policy = str(config.get("gpu_policy") or "auto").strip() or "auto"
        gpu_index = str(config.get("gpu_index") or "").strip()
        min_free = str(config.get("min_free_memory_gib") or "").strip()
        gpu_text = f" · gpu={gpu_index}" if gpu_index else ""
        return (f"server={server_id} · policy={gpu_policy}{gpu_text}" + (f" · min={min_free}GiB" if min_free else ""), "ready")
    if kind == "run.command":
        command = str(config.get("run_command") or "").strip()
        return (compact_workspace_command(command) if command else "缺 run_command", "ready" if command else "blocked")
    if kind == "artifact.collect":
        paths = workspace_config_values(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs")
        metrics = workspace_config_values(config.get("metric_paths"))
        return (f"{len(paths)} 条产物路径 · {len(metrics)} 条指标路径", "ready" if paths or metrics else "warning")
    if kind == "eval.report":
        command = str(config.get("report_command") or "").strip()
        metrics = workspace_config_values(config.get("metric_paths"))
        if command:
            return (compact_workspace_command(command), "ready")
        return (f"缺 report_command · {len(metrics)} 条指标路径", "blocked")
    command = str(config.get("command") or config.get("goal") or "").strip()
    return (compact_workspace_command(command) if command else "没有命令摘要", "warning")


def derive_workspace_run_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    execution_nodes = {
        str(item.get("id") or ""): item
        for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    plan_nodes: list[dict[str, Any]] = []
    phase_counts: dict[str, int] = {}
    hard_gate_ids = {"starter_chain", "agents", "run"}
    blocking_items = [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed"}
    ]
    warning_items = [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") not in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed", "warning", "draft"}
    ]
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        phase = workspace_run_node_phase(kind)
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        summary, status = workspace_node_command_summary_for_plan(workspace, node)
        runtime = execution_nodes.get(str(node.get("id") or ""), {})
        plan_nodes.append(
            {
                "index": len(plan_nodes) + 1,
                "id": str(node.get("id") or "").strip(),
                "kind": kind,
                "title": str(node.get("title") or node.get("kind") or "").strip(),
                "phase": phase,
                "phase_label": workspace_run_phase_label(phase),
                "status": status,
                "summary": summary,
                "agent_id": str(handler.get("agent_id") or runtime.get("agent_id") or "").strip(),
                "agent_name": str(handler.get("name") or runtime.get("agent_name") or "").strip(),
                "last_job_id": str(runtime.get("job_id") or "").strip(),
                "last_job_status": str(runtime.get("job_status") or "").strip(),
                "depends_on_previous": len(plan_nodes) > 0,
            }
        )
    for node in plan_nodes:
        if node["status"] in {"blocked", "failed"}:
            blocking_items.append(
                {
                    "id": node["id"],
                    "label": node["title"],
                    "status": "blocked",
                    "title": node["title"],
                    "detail": node["summary"],
                    "action": "先运行自动发现、应用体检建议或补齐节点配置。",
                    "node_kind": node["kind"],
                }
            )
        elif node["status"] in {"warning", "draft"}:
            warning_items.append(
                {
                    "id": node["id"],
                    "label": node["title"],
                    "status": node["status"],
                    "title": node["title"],
                    "detail": node["summary"],
                    "action": "可以先运行自动发现补齐证据。",
                    "node_kind": node["kind"],
                }
            )
    status = "blocked" if blocking_items else "warning" if warning_items else "ready"
    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]
    phases = [
        {
            "id": phase,
            "label": workspace_run_phase_label(phase),
            "count": phase_counts.get(phase, 0),
        }
        for phase in phase_order
        if phase_counts.get(phase, 0)
    ]
    return {
        "status": status,
        "node_count": len(plan_nodes),
        "phases": phases,
        "nodes": plan_nodes,
        "blocking": blocking_items,
        "warnings": warning_items,
        "summary": f"{len(plan_nodes)} 个可执行节点 · {len(phases)} 个阶段 · {len(blocking_items)} 个阻塞项 · {len(warning_items)} 个提示",
    }


def workspace_io_contract_for_kind(kind: str, index: int) -> dict[str, Any]:
    normalized = str(kind or "").strip()
    contract = WORKSPACE_NODE_IO_CONTRACTS.get(normalized)
    if contract:
        return copy.deepcopy(contract)
    output_key = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_") or f"step_{index + 1}"
    return {
        "inputs": ["上一节点输出", "节点配置"] if index else ["启动输入", "节点配置"],
        "output_key": output_key,
        "evidence": "节点配置、运行结果和交接备注",
    }


def workspace_node_config_signal(node: dict[str, Any]) -> str:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    for key in (
        "repo_url",
        "workspace_dir",
        "data_roots",
        "dataset_hints",
        "setup_command",
        "run_command",
        "server_id",
        "gpu_index",
        "artifact_paths",
        "metric_paths",
        "report_command",
    ):
        value = str(config.get(key) or "").strip()
        if value:
            return compact_workspace_command(value, limit=140)
    return ""


def workspace_io_input_mapping(node: dict[str, Any], contract: dict[str, Any], index: int) -> dict[str, str]:
    raw_mapping = node.get("input_mapping")
    if isinstance(raw_mapping, dict) and raw_mapping:
        return {
            str(key or "").strip(): str(value or "").strip()
            for key, value in raw_mapping.items()
            if str(key or "").strip()
        }
    inputs = contract.get("inputs") if isinstance(contract.get("inputs"), list) else []
    mapping: dict[str, str] = {}
    for raw in inputs[:6]:
        label = str(raw or "").strip()
        if not label:
            continue
        if index == 0:
            mapping[label] = "$input"
        elif label in {"上一节点输出", "source_context"}:
            mapping[label] = "$prev.output"
        elif label.endswith("_context") or label.endswith("_profile") or label.endswith("_ready") or label.endswith("_allocation"):
            mapping[label] = f"$context.outputs.{label}"
        else:
            mapping[label] = f"$input.{safe_id(label) or label}"
    return mapping


def workspace_has_explicit_input_mapping(node: dict[str, Any]) -> bool:
    raw_mapping = node.get("input_mapping")
    return isinstance(raw_mapping, dict) and any(str(key or "").strip() for key in raw_mapping.keys())


def workspace_contract_output_key_for_node(node: dict[str, Any], index: int) -> str:
    kind = str(node.get("kind") or "").strip()
    contract = workspace_io_contract_for_kind(kind, index)
    return str(node.get("output_key") or contract.get("output_key") or f"step_{index + 1}").strip()


def workspace_contract_input_ref_state(
    source: str,
    index: int,
    output_catalog: dict[str, dict[str, Any]],
    previous_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ref = str(source or "").strip()
    if not ref:
        return {"status": "draft", "source_type": "empty", "detail": "等待输入来源"}
    if ref == "$input" or ref.startswith("$input."):
        return {"status": "ready", "source_type": "input", "detail": "来自启动输入 input_data"}
    if ref == "$prev.output" or ref.startswith("$prev.output."):
        if index > 0 and previous_outputs:
            upstream = next(reversed(previous_outputs.values()))
            return {
                "status": "ready",
                "source_type": "previous",
                "detail": f"来自上一节点 {upstream.get('output_key') or 'output'}",
                "upstream_node_id": str(upstream.get("node_id") or "").strip(),
                "upstream_output_key": str(upstream.get("output_key") or "").strip(),
            }
        return {"status": "blocked", "source_type": "previous", "detail": "首节点不能引用 $prev.output"}
    if ref == "$context":
        return {"status": "ready" if previous_outputs else "warning", "source_type": "context", "detail": "引用整个工作流上下文"}
    if ref.startswith("$context.outputs."):
        output_key = ref[len("$context.outputs."):].split(".", 1)[0]
        previous = previous_outputs.get(output_key)
        if previous:
            return {
                "status": "ready",
                "source_type": "context_output",
                "detail": f"{output_key} 来自上游节点",
                "upstream_node_id": str(previous.get("node_id") or "").strip(),
                "upstream_output_key": output_key,
            }
        owner = output_catalog.get(output_key)
        if owner:
            owner_index = safe_int(owner.get("index"), -1)
            if owner_index == index:
                detail = f"{output_key} 引用了本节点自己的输出"
            elif owner_index > index:
                detail = f"{output_key} 来自下游节点，执行顺序倒挂"
            else:
                detail = f"{output_key} 上游未进入当前上下文"
            return {
                "status": "blocked",
                "source_type": "context_output",
                "detail": detail,
                "upstream_node_id": str(owner.get("node_id") or "").strip(),
                "upstream_output_key": output_key,
            }
        return {
            "status": "blocked",
            "source_type": "context_output",
            "detail": f"{output_key} 没有对应 output_key",
            "upstream_output_key": output_key,
        }
    if ref.startswith("$context."):
        return {"status": "warning", "source_type": "context", "detail": "上下文字段会在运行时解析"}
    return {"status": "ready", "source_type": "literal", "detail": "固定值或节点配置"}


def workspace_contract_input_refs(
    input_mapping: dict[str, str],
    index: int,
    output_catalog: dict[str, dict[str, Any]],
    previous_outputs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for key, value in input_mapping.items():
        name = str(key or "").strip()
        if not name:
            continue
        source = str(value or "").strip()
        state = workspace_contract_input_ref_state(source, index, output_catalog, previous_outputs)
        refs.append(
            {
                "name": name,
                "source": source,
                "status": str(state.get("status") or "draft").strip(),
                "source_type": str(state.get("source_type") or "").strip(),
                "detail": str(state.get("detail") or "").strip(),
                "upstream_node_id": str(state.get("upstream_node_id") or "").strip(),
                "upstream_output_key": str(state.get("upstream_output_key") or "").strip(),
            }
        )
    return refs


def workspace_apply_auto_input_mapping_fallbacks(
    input_mapping: dict[str, str],
    input_refs: list[dict[str, Any]],
) -> None:
    for ref in input_refs:
        if not isinstance(ref, dict):
            continue
        if str(ref.get("status") or "").strip() != "blocked":
            continue
        if str(ref.get("source_type") or "").strip() != "context_output":
            continue
        if str(ref.get("upstream_node_id") or "").strip():
            continue
        detail = str(ref.get("detail") or "").strip()
        if "没有对应 output_key" not in detail:
            continue
        name = str(ref.get("name") or "").strip()
        if not name:
            continue
        input_mapping[name] = "$input"
        ref["source"] = "$input"
        ref["status"] = "ready"
        ref["source_type"] = "input_fallback"
        ref["detail"] = "默认映射未找到上游 output_key，已回退到启动输入或节点配置"
        ref["upstream_output_key"] = ""


def workspace_group_evidence_by_kind(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for group in evidence:
        if not isinstance(group, dict):
            continue
        group_label = str(group.get("label") or group.get("id") or "证据").strip()
        for item in (group.get("items") if isinstance(group.get("items"), list) else []):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("node_kind") or "").strip()
            if not kind:
                continue
            grouped.setdefault(kind, []).append(
                {
                    "group": group_label,
                    "label": str(item.get("label") or item.get("source") or "发现").strip(),
                    "value": str(item.get("value") or "").strip(),
                    "status": str(item.get("status") or "found").strip(),
                }
            )
    return grouped


def derive_workspace_workflow_contract(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    evidence: list[dict[str, Any]],
    resource_orchestration: dict[str, Any],
    run_plan: dict[str, Any],
    agent_topology: dict[str, Any],
) -> dict[str, Any]:
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    execution_nodes = {
        str(item.get("id") or ""): item
        for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    plan_nodes = {
        str(item.get("id") or ""): item
        for item in (run_plan.get("nodes") if isinstance(run_plan.get("nodes"), list) else [])
        if isinstance(item, dict)
    }
    resource_items = {
        str(item.get("node_kind") or ""): item
        for item in (resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else [])
        if isinstance(item, dict) and str(item.get("node_kind") or "").strip()
    }
    evidence_by_kind = workspace_group_evidence_by_kind(evidence)
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {str(tool.get("id") or "").strip(): tool for tool in tools if isinstance(tool, dict)}
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {str(agent.get("id") or "").strip(): agent for agent in agents if isinstance(agent, dict)}
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    output_catalog: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or node.get("kind") or f"node-{index}").strip()
        output_key = workspace_contract_output_key_for_node(node, index)
        if output_key and output_key not in output_catalog:
            output_catalog[output_key] = {
                "output_key": output_key,
                "node_id": node_id,
                "index": index,
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or f"节点 {index + 1}").strip(),
            }

    contract_nodes: list[dict[str, Any]] = []
    previous_outputs: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        contract = workspace_io_contract_for_kind(kind, index)
        node_id = str(node.get("id") or kind or f"node-{index}").strip()
        execution_node = execution_nodes.get(node_id, {})
        plan_node = plan_nodes.get(node_id, {})
        resource_item = resource_items.get(kind, {})
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or execution_node.get("agent_id") or plan_node.get("agent_id") or "").strip()
        agent = agent_index.get(agent_id, {})
        agent_tool_ids = parse_tag_list(agent.get("tools", []) if agent else [])
        required_tool_id = workspace_node_required_tool_id(kind)
        tool_ids = list(dict.fromkeys([*(agent_tool_ids[:3]), *([required_tool_id] if required_tool_id else [])]))
        route = workspace_model_route_for_agent(model, agent if agent else None)
        next_node = nodes[index + 1] if index + 1 < len(nodes) and isinstance(nodes[index + 1], dict) else {}
        input_mapping = workspace_io_input_mapping(node, contract, index)
        input_refs = workspace_contract_input_refs(input_mapping, index, output_catalog, previous_outputs)
        if not workspace_has_explicit_input_mapping(node):
            workspace_apply_auto_input_mapping_fallbacks(input_mapping, input_refs)
        missing_inputs = [
            ref for ref in input_refs
            if str(ref.get("status") or "") in {"blocked", "failed"}
        ]
        waiting_inputs = [
            ref for ref in input_refs
            if str(ref.get("status") or "") in {"draft", "warning", "pending"}
        ]
        evidence_items = evidence_by_kind.get(kind, [])
        raw_status = str(resource_item.get("status") or plan_node.get("status") or execution_node.get("status") or "draft").strip()
        if missing_inputs:
            status = "blocked"
            input_status = "blocked"
        elif waiting_inputs:
            status = raw_status if raw_status in {"blocked", "failed"} else "warning"
            input_status = "warning"
        elif input_refs:
            status = raw_status
            input_status = "ready"
        else:
            status = raw_status
            input_status = "draft"
        evidence_label = ""
        if evidence_items:
            first = evidence_items[0]
            evidence_label = f"{first.get('group', '')} · {first.get('label', '')}".strip(" ·")
            if len(evidence_items) > 1:
                evidence_label += f" +{len(evidence_items) - 1}"
        elif str(resource_item.get("value") or "").strip():
            evidence_label = str(resource_item.get("value") or "").strip()
        else:
            evidence_label = str(contract.get("evidence") or "等待证据").strip()
        contract_nodes.append(
            {
                "id": node_id,
                "index": len(contract_nodes) + 1,
                "kind": kind,
                "title": str(node.get("title") or kind or f"节点 {index + 1}").strip(),
                "phase": workspace_run_node_phase(kind),
                "phase_label": workspace_run_phase_label(workspace_run_node_phase(kind)),
                "status": status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft", "pending"} else "warning",
                "inputs": list(input_mapping.keys()),
                "input_mapping": input_mapping,
                "input_refs": input_refs,
                "input_status": input_status,
                "missing_inputs": copy.deepcopy(missing_inputs),
                "input_gap_count": len(missing_inputs),
                "output_key": workspace_contract_output_key_for_node(node, index),
                "context": {
                    "input_key": "$input",
                    "outputs_key": "$context.outputs",
                    "previous_key": "$prev.output",
                },
                "evidence": evidence_label,
                "evidence_count": len(evidence_items),
                "config_signal": workspace_node_config_signal(node),
                "handoff": str(handler.get("handoff") or resource_item.get("action") or "").strip(),
                "next_node_id": str(next_node.get("id") or "").strip(),
                "next_node_title": str(next_node.get("title") or next_node.get("kind") or "最终报告").strip(),
                "agent": {
                    "id": agent_id,
                    "name": str(handler.get("name") or (agent.get("name") if agent else "") or execution_node.get("agent_name") or "未指派 Agent").strip(),
                    "role": str((agent.get("role") if agent else "") or "").strip(),
                    "enabled": bool(agent.get("enabled", True)) if agent else False,
                },
                "tools": [
                    {
                        "id": tool_id,
                        "label": str((tool_index.get(tool_id) or {}).get("label") or tool_id).strip(),
                        "enabled": bool((tool_index.get(tool_id) or {}).get("enabled", bool(tool_index.get(tool_id)))),
                    }
                    for tool_id in tool_ids
                    if tool_id
                ],
                "model": route,
            }
        )
        output_key = str(contract_nodes[-1].get("output_key") or "").strip()
        if output_key:
            previous_outputs[output_key] = {
                "output_key": output_key,
                "node_id": node_id,
                "index": index,
                "kind": kind,
                "title": str(node.get("title") or kind or f"节点 {index + 1}").strip(),
            }

    mapped_count = sum(1 for item in contract_nodes if item.get("input_mapping") and item.get("output_key"))
    blocked_count = sum(1 for item in contract_nodes if str(item.get("status") or "") in {"blocked", "failed"})
    ready_count = sum(1 for item in contract_nodes if str(item.get("status") or "") in {"ready", "done"})
    input_gap_count = sum(safe_int(item.get("input_gap_count"), 0) for item in contract_nodes)
    if blocked_count:
        status = "blocked"
    elif mapped_count < len(contract_nodes):
        status = "warning"
    else:
        status = "ready"
    return {
        "status": status,
        "summary": f"{mapped_count}/{len(contract_nodes)} 节点有输入/输出契约 · {ready_count} 就绪 · {blocked_count} 阻塞 · {input_gap_count} 输入断点",
        "node_count": len(contract_nodes),
        "mapped_count": mapped_count,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "input_gap_count": input_gap_count,
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "nodes": contract_nodes,
    }


def workspace_orchestration_gap_matches_node(gap: dict[str, Any], node: dict[str, Any]) -> bool:
    gap_node_id = str(gap.get("node_id") or "").strip()
    gap_node_kind = str(gap.get("node_kind") or "").strip()
    gap_agent_id = str(gap.get("agent_id") or "").strip()
    gap_tool_id = str(gap.get("tool_id") or "").strip()
    node_agent = node.get("agent") if isinstance(node.get("agent"), dict) else {}
    node_tools = node.get("tools") if isinstance(node.get("tools"), list) else []
    if gap_node_id and gap_node_id == str(node.get("id") or "").strip():
        return True
    if gap_node_kind and gap_node_kind == str(node.get("kind") or "").strip():
        return True
    if gap_agent_id and gap_agent_id == str(node_agent.get("id") or "").strip():
        return True
    if gap_tool_id and any(gap_tool_id == str(tool.get("id") or "").strip() for tool in node_tools if isinstance(tool, dict)):
        return True
    return False


def workspace_orchestration_status(statuses: list[str], *, default: str = "draft") -> str:
    values = [str(status or "").strip() for status in statuses if str(status or "").strip()]
    if not values:
        return default
    return min(values, key=workspace_status_priority)


def derive_workspace_orchestration_contract(
    agent_topology: dict[str, Any],
    workflow_contract: dict[str, Any],
) -> dict[str, Any]:
    layers = agent_topology.get("layers") if isinstance(agent_topology.get("layers"), dict) else {}
    topology_stages = agent_topology.get("stages") if isinstance(agent_topology.get("stages"), list) else []
    contract_nodes = workflow_contract.get("nodes") if isinstance(workflow_contract.get("nodes"), list) else []
    gaps = agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []
    stage_index = {
        str(stage.get("id") or "").strip(): stage
        for stage in topology_stages
        if isinstance(stage, dict) and str(stage.get("id") or "").strip()
    }
    lanes: dict[str, dict[str, Any]] = {}
    phase_order = ["source", "discover", "setup", "run", "collect", "report", "other"]

    def lane_for_phase(phase: str) -> dict[str, Any]:
        phase_id = phase if phase in phase_order else "other"
        if phase_id not in lanes:
            stage = stage_index.get(phase_id, {})
            lanes[phase_id] = {
                "id": phase_id,
                "label": str(stage.get("label") or workspace_run_phase_label(phase_id)).strip(),
                "status": str(stage.get("status") or "draft").strip(),
                "node_count": 0,
                "ready_count": 0,
                "blocked_count": 0,
                "agent_count": len(stage.get("agents") if isinstance(stage.get("agents"), list) else []),
                "tool_count": len(stage.get("tools") if isinstance(stage.get("tools"), list) else []),
                "model_profile_count": len(stage.get("model_profiles") if isinstance(stage.get("model_profiles"), list) else []),
                "nodes": [],
                "gaps": [
                    copy.deepcopy(gap)
                    for gap in (stage.get("gaps") if isinstance(stage.get("gaps"), list) else [])
                    if isinstance(gap, dict)
                ][:5],
            }
        return lanes[phase_id]

    for node in contract_nodes:
        if not isinstance(node, dict):
            continue
        phase = str(node.get("phase") or "other").strip() or "other"
        lane = lane_for_phase(phase)
        node_gaps = [
            copy.deepcopy(gap)
            for gap in gaps
            if isinstance(gap, dict) and workspace_orchestration_gap_matches_node(gap, node)
        ][:3]
        input_gaps = []
        for ref in (node.get("missing_inputs") if isinstance(node.get("missing_inputs"), list) else []):
            if not isinstance(ref, dict):
                continue
            input_gaps.append(
                {
                    "type": "input_mapping",
                    "status": str(ref.get("status") or "blocked").strip(),
                    "title": f"输入断点：{str(ref.get('name') or 'input').strip()}",
                    "detail": str(ref.get("detail") or "").strip(),
                    "action": "检查 input_mapping 或上游 output_key。",
                    "node_id": str(node.get("id") or "").strip(),
                    "node_kind": str(node.get("kind") or "").strip(),
                    "phase": phase,
                    "field": str(ref.get("name") or "").strip(),
                    "source": str(ref.get("source") or "").strip(),
                    "upstream_output_key": str(ref.get("upstream_output_key") or "").strip(),
                }
            )
        node_gaps = [*input_gaps, *node_gaps][:3]
        agent = node.get("agent") if isinstance(node.get("agent"), dict) else {}
        model = node.get("model") if isinstance(node.get("model"), dict) else {}
        tools = node.get("tools") if isinstance(node.get("tools"), list) else []
        node_status = workspace_orchestration_status(
            [
                str(node.get("status") or "draft"),
                *[str(gap.get("status") or "warning") for gap in node_gaps if isinstance(gap, dict)],
                "warning" if not str(agent.get("id") or "").strip() else "ready",
                "warning" if not str(model.get("effective_profile_id") or "").strip() else "ready",
            ],
            default="draft",
        )
        if node_status in {"ready", "done"}:
            lane["ready_count"] = safe_int(lane.get("ready_count"), 0) + 1
        if node_status in {"blocked", "failed"}:
            lane["blocked_count"] = safe_int(lane.get("blocked_count"), 0) + 1
        lane["node_count"] = safe_int(lane.get("node_count"), 0) + 1
        lane["nodes"].append(
            {
                "id": str(node.get("id") or "").strip(),
                "index": safe_int(node.get("index"), len(lane["nodes"]) + 1),
                "kind": str(node.get("kind") or "").strip(),
                "title": str(node.get("title") or node.get("kind") or "节点").strip(),
                "status": node_status,
                "input_count": len(node.get("inputs") if isinstance(node.get("inputs"), list) else []),
                "input_status": str(node.get("input_status") or "draft").strip(),
                "input_gap_count": safe_int(node.get("input_gap_count"), 0),
                "missing_inputs": copy.deepcopy(node.get("missing_inputs") if isinstance(node.get("missing_inputs"), list) else []),
                "output_key": str(node.get("output_key") or "").strip(),
                "handoff": str(node.get("handoff") or "").strip(),
                "next_node_title": str(node.get("next_node_title") or "最终报告").strip(),
                "agent": {
                    "id": str(agent.get("id") or "").strip(),
                    "name": str(agent.get("name") or "未指派 Agent").strip(),
                    "role": str(agent.get("role") or "").strip(),
                    "enabled": bool(agent.get("enabled", False)),
                },
                "tools": [
                    {
                        "id": str(tool.get("id") or "").strip(),
                        "label": str(tool.get("label") or tool.get("id") or "").strip(),
                        "enabled": bool(tool.get("enabled", False)),
                    }
                    for tool in tools
                    if isinstance(tool, dict)
                ][:5],
                "model": {
                    "label": str(model.get("label") or model.get("source") or "未配置 Profile").strip(),
                    "source": str(model.get("source") or "").strip(),
                    "effective_profile_id": str(model.get("effective_profile_id") or "").strip(),
                    "status": str(model.get("status") or "warning").strip(),
                },
                "gaps": node_gaps,
                "next_action": str((node_gaps[0] if node_gaps else {}).get("action") or node.get("handoff") or "").strip(),
            }
        )

    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        phase = str(gap.get("phase") or "").strip()
        if not phase:
            continue
        lane = lane_for_phase(phase)
        if not any(str(existing.get("title") or existing.get("type") or "") == str(gap.get("title") or gap.get("type") or "") for existing in lane.get("gaps", [])):
            lane["gaps"].append(copy.deepcopy(gap))

    lane_items = [lanes[phase] for phase in phase_order if phase in lanes]
    for lane in lane_items:
        lane_statuses = [
            str(lane.get("status") or "draft"),
            *[str(node.get("status") or "draft") for node in (lane.get("nodes") if isinstance(lane.get("nodes"), list) else [])],
            *[str(gap.get("status") or "warning") for gap in (lane.get("gaps") if isinstance(lane.get("gaps"), list) else []) if isinstance(gap, dict)],
        ]
        lane["status"] = workspace_orchestration_status(lane_statuses, default="draft")
        lane["summary"] = (
            f"{safe_int(lane.get('node_count'), 0)} 节点 · "
            f"{safe_int(lane.get('agent_count'), 0)} Agent · "
            f"{safe_int(lane.get('tool_count'), 0)} 工具 · "
            f"{safe_int(lane.get('model_profile_count'), 0)} Profile"
        )
        lane["gaps"] = (lane.get("gaps") if isinstance(lane.get("gaps"), list) else [])[:5]

    all_node_statuses = [
        str(node.get("status") or "draft")
        for lane in lane_items
        for node in (lane.get("nodes") if isinstance(lane.get("nodes"), list) else [])
        if isinstance(node, dict)
    ]
    status = workspace_orchestration_status(
        [str(agent_topology.get("status") or "draft"), str(workflow_contract.get("status") or "draft"), *all_node_statuses],
        default="draft",
    )
    ready_nodes = sum(1 for status_value in all_node_statuses if status_value in {"ready", "done"})
    blocked_nodes = sum(1 for status_value in all_node_statuses if status_value in {"blocked", "failed"})
    next_gap = next(
        (
            gap for gap in gaps
            if isinstance(gap, dict) and str(gap.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        {},
    )
    return {
        "status": status,
        "summary": f"{len(lane_items)} 个阶段车道 · {ready_nodes}/{len(all_node_statuses)} 节点闭环 · {blocked_nodes} 阻塞 · {len(gaps)} 缺口",
        "lane_count": len(lane_items),
        "node_count": len(all_node_statuses),
        "ready_node_count": ready_nodes,
        "blocked_node_count": blocked_nodes,
        "layers": copy.deepcopy(layers),
        "lanes": lane_items,
        "gaps": copy.deepcopy(gaps[:12]),
        "next_action": {
            "status": str(next_gap.get("status") or status).strip(),
            "title": str(next_gap.get("title") or "编排契约已形成").strip(),
            "detail": str(next_gap.get("detail") or workflow_contract.get("summary") or "").strip(),
            "action": str(next_gap.get("action") or "按当前执行包继续推进。").strip(),
            "phase": str(next_gap.get("phase") or "").strip(),
            "node_id": str(next_gap.get("node_id") or "").strip(),
            "node_kind": str(next_gap.get("node_kind") or "").strip(),
        },
    }


def workspace_node_workflow_contract_metadata(workspace: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
        if isinstance(item, dict)
    ]
    node_id = str(node.get("id") or "").strip()
    index = next(
        (
            idx for idx, item in enumerate(nodes)
            if str(item.get("id") or "").strip() == node_id
        ),
        0,
    )
    kind = str(node.get("kind") or "").strip()
    contract = workspace_io_contract_for_kind(kind, index)
    input_mapping = workspace_io_input_mapping(node, contract, index)
    next_node = nodes[index + 1] if index + 1 < len(nodes) and isinstance(nodes[index + 1], dict) else {}
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    tools = normalize_workspace_tools(workspace.get("tools"))
    tool_index = {str(tool.get("id") or "").strip(): tool for tool in tools if isinstance(tool, dict)}
    agents = normalize_workspace_agents(workspace.get("agents"), tool_ids=list(tool_index.keys()))
    agent_index = {str(agent.get("id") or "").strip(): agent for agent in agents if isinstance(agent, dict)}
    agent_id = str(handler.get("agent_id") or "").strip()
    agent = agent_index.get(agent_id, {})
    agent_tool_ids = parse_tag_list(agent.get("tools", []) if agent else [])
    required_tool_id = workspace_node_required_tool_id(kind)
    tool_ids = list(dict.fromkeys([*(agent_tool_ids[:3]), *([required_tool_id] if required_tool_id else [])]))
    model = normalize_workspace_model(workspace.get("model"), existing=workspace.get("model"))
    route = workspace_model_route_for_agent(model, agent if agent else None)
    handoff = str(handler.get("handoff") or "").strip()
    if not handoff:
        handoff = (
            f"交给 {str(next_node.get('title') or next_node.get('kind') or '下游节点').strip()}"
            if next_node
            else "交给报告/归档"
        )
    return {
        "node_id": node_id,
        "node_kind": kind,
        "input_mapping": input_mapping,
        "inputs": list(input_mapping.keys()),
        "output_key": str(node.get("output_key") or contract.get("output_key") or f"step_{index + 1}").strip(),
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "handoff": handoff,
        "next_node_id": str(next_node.get("id") or "").strip(),
        "next_node_title": str(next_node.get("title") or next_node.get("kind") or "最终报告").strip(),
        "agent": {
            "id": agent_id,
            "name": str(handler.get("name") or (agent.get("name") if agent else "") or "未指派 Agent").strip(),
            "role": str((agent.get("role") if agent else "") or "").strip(),
            "enabled": bool(agent.get("enabled", True)) if agent else False,
        },
        "tools": [
            {
                "id": tool_id,
                "label": str((tool_index.get(tool_id) or {}).get("label") or tool_id).strip(),
                "enabled": bool((tool_index.get(tool_id) or {}).get("enabled", bool(tool_index.get(tool_id)))),
            }
            for tool_id in tool_ids
            if tool_id
        ],
        "model": route,
    }


def workspace_context_ref_value(data: Any, path: str) -> Any:
    current = data
    for part in [item for item in str(path or "").split(".") if item]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current


def workspace_context_value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def workspace_input_data_for_context(workspace: dict[str, Any]) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    payload = copy.deepcopy(inputs)
    payload.setdefault("goal_text", str(inputs.get("goal_text") or workspace.get("brief") or source.get("idea_text") or "").strip())
    payload.setdefault("repo_url", str(source.get("repo_url") or "").strip())
    payload.setdefault("paper_url", str(source.get("paper_url") or "").strip())
    payload.setdefault("workspace_dir", str(workspace.get("workspace_dir") or "").strip())
    payload.setdefault("source_mode", str(inputs.get("source_mode") or source.get("type") or "idea").strip())
    return payload


def workspace_context_input_summary(input_data: dict[str, Any]) -> dict[str, Any]:
    repo_urls = input_data.get("repo_urls") if isinstance(input_data.get("repo_urls"), list) else []
    paper_urls = input_data.get("paper_urls") if isinstance(input_data.get("paper_urls"), list) else []
    references = input_data.get("references") if isinstance(input_data.get("references"), list) else []
    context_blocks = input_data.get("context_blocks") if isinstance(input_data.get("context_blocks"), list) else []
    keys = [
        key for key, value in input_data.items()
        if workspace_context_value_present(value)
    ]
    return {
        "source_mode": str(input_data.get("source_mode") or "idea"),
        "key_count": len(keys),
        "keys": keys[:12],
        "repo_count": len(repo_urls) + (1 if str(input_data.get("repo_url") or "").strip() else 0),
        "paper_count": len(paper_urls) + (1 if str(input_data.get("paper_url") or "").strip() else 0),
        "reference_count": len(references),
        "context_count": len(context_blocks),
        "goal_present": bool(str(input_data.get("goal_text") or "").strip()),
    }


def workspace_context_mapping_status(
    source: str,
    *,
    input_data: dict[str, Any],
    output_state: dict[str, dict[str, Any]],
    previous_output: dict[str, Any] | None,
) -> dict[str, str]:
    ref = str(source or "").strip()
    if not ref:
        return {"status": "draft", "detail": "等待来源"}
    if ref == "$input":
        return {
            "status": "ready" if workspace_context_value_present(input_data) else "draft",
            "detail": "启动输入",
        }
    if ref.startswith("$input."):
        value = workspace_context_ref_value(input_data, ref[len("$input."):])
        return {
            "status": "ready" if workspace_context_value_present(value) else "draft",
            "detail": "启动输入字段" if workspace_context_value_present(value) else "启动输入缺字段",
        }
    if ref == "$prev.output" or ref.startswith("$prev.output."):
        if previous_output and previous_output.get("produced"):
            return {"status": str(previous_output.get("status") or "ready"), "detail": str(previous_output.get("output_key") or "上一节点输出")}
        return {"status": "draft", "detail": "等待上一节点输出"}
    if ref == "$context":
        return {"status": "ready" if output_state else "draft", "detail": "工作流上下文"}
    if ref.startswith("$context.outputs."):
        key = ref[len("$context.outputs."):].split(".", 1)[0]
        state = output_state.get(key)
        if state and state.get("produced"):
            return {"status": str(state.get("status") or "ready"), "detail": f"{key} 已写入 context.outputs"}
        if state:
            status = str(state.get("status") or "draft")
            return {"status": status, "detail": f"{key} 尚未产生"}
        return {"status": "draft", "detail": f"{key} 尚无上游输出"}
    if ref.startswith("$context."):
        return {"status": "ready" if output_state else "draft", "detail": "上下文引用"}
    return {"status": "ready", "detail": "固定值或配置值"}


def derive_workspace_execution_context(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    workflow_contract: dict[str, Any],
) -> dict[str, Any]:
    input_data = workspace_input_data_for_context(workspace)
    input_summary = workspace_context_input_summary(input_data)
    contract_nodes = workflow_contract.get("nodes") if isinstance(workflow_contract.get("nodes"), list) else []
    execution_nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    execution_by_id = {
        str(node.get("id") or "").strip(): node
        for node in execution_nodes
        if isinstance(node, dict)
    }
    execution_by_kind: dict[str, dict[str, Any]] = {}
    for node in execution_nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind and kind not in execution_by_kind:
            execution_by_kind[kind] = node

    output_state: dict[str, dict[str, Any]] = {}
    previous_output: dict[str, Any] | None = None
    step_results: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    for index, contract_node in enumerate(contract_nodes):
        if not isinstance(contract_node, dict):
            continue
        node_id = str(contract_node.get("id") or contract_node.get("node_id") or "").strip()
        kind = str(contract_node.get("kind") or contract_node.get("node_kind") or "").strip()
        execution_node = execution_by_id.get(node_id) or execution_by_kind.get(kind) or {}
        status = str(execution_node.get("status") or contract_node.get("status") or "draft").strip() or "draft"
        job_status = str(execution_node.get("job_status") or "").strip()
        job_id = str(execution_node.get("job_id") or "").strip()
        output_key = str(contract_node.get("output_key") or f"step_{index + 1}").strip()
        input_mapping = contract_node.get("input_mapping") if isinstance(contract_node.get("input_mapping"), dict) else {}
        static_input_refs = {
            str(item.get("name") or "").strip(): item
            for item in (contract_node.get("input_refs") if isinstance(contract_node.get("input_refs"), list) else [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        resolved_inputs: list[dict[str, str]] = []
        for key, value in input_mapping.items():
            name = str(key or "").strip()
            if not name:
                continue
            source = str(value or "").strip()
            static_state = static_input_refs.get(name, {})
            if static_state and str(static_state.get("status") or "") in {"blocked", "failed"}:
                source_state = {
                    "status": str(static_state.get("status") or "blocked"),
                    "detail": str(static_state.get("detail") or "输入映射断开"),
                }
            else:
                source_state = workspace_context_mapping_status(
                    source,
                    input_data=input_data,
                    output_state=output_state,
                    previous_output=previous_output,
                )
            resolved_inputs.append(
                {
                    "name": name,
                    "source": source,
                    "status": source_state["status"],
                    "detail": source_state["detail"],
                    "source_type": str(static_state.get("source_type") or "").strip(),
                    "upstream_output_key": str(static_state.get("upstream_output_key") or "").strip(),
                    "upstream_node_id": str(static_state.get("upstream_node_id") or "").strip(),
                }
            )
        input_blocked_count = len([item for item in resolved_inputs if item["status"] in {"blocked", "failed"}])
        input_waiting_count = len([item for item in resolved_inputs if item["status"] in {"draft", "warning", "pending"}])
        if input_blocked_count:
            input_status = "blocked"
        elif input_waiting_count:
            input_status = "warning"
        elif resolved_inputs:
            input_status = "ready"
        else:
            input_status = "draft"

        produced = status == "done" or job_status == "done"
        if status in {"failed", "stopped"} or job_status in {"failed", "stopped"}:
            output_status = "failed"
        elif status in {"running", "queued"} or job_status in {"running", "queued", "starting", "blocked"}:
            output_status = "running"
        elif produced:
            output_status = "ready"
        elif input_status == "blocked":
            output_status = "blocked"
        else:
            output_status = "draft"
        artifact_count = len(execution_node.get("artifacts") if isinstance(execution_node.get("artifacts"), list) else [])
        resources = execution_node.get("resources") if isinstance(execution_node.get("resources"), dict) else {}
        trace = execution_node.get("trace") if isinstance(execution_node.get("trace"), list) else []
        agent = contract_node.get("agent") if isinstance(contract_node.get("agent"), dict) else {}
        model = contract_node.get("model") if isinstance(contract_node.get("model"), dict) else {}
        tools = contract_node.get("tools") if isinstance(contract_node.get("tools"), list) else []
        output_item = {
            "key": output_key,
            "node_id": node_id,
            "node_kind": kind,
            "title": str(contract_node.get("title") or execution_node.get("title") or kind).strip(),
            "status": output_status,
            "produced": produced,
            "job_id": job_id,
            "artifact_count": artifact_count,
            "resource_key_count": len(resources),
            "handoff": str(contract_node.get("handoff") or "").strip(),
            "next_node_id": str(contract_node.get("next_node_id") or "").strip(),
            "next_node_title": str(contract_node.get("next_node_title") or "最终报告").strip(),
        }
        outputs.append(output_item)
        output_state[output_key] = output_item
        previous_output = output_item
        step_results.append(
            {
                "step_order": safe_int(contract_node.get("index"), index + 1),
                "node_id": node_id,
                "node_kind": kind,
                "title": str(contract_node.get("title") or execution_node.get("title") or kind).strip(),
                "status": status,
                "input_status": input_status,
                "input_waiting_count": input_waiting_count,
                "input_blocked_count": input_blocked_count,
                "input_mapping": input_mapping,
                "resolved_inputs": resolved_inputs,
                "output_key": output_key,
                "output_status": output_status,
                "output_produced": produced,
                "job_id": job_id,
                "job_status": job_status,
                "run_count": safe_int(execution_node.get("run_count"), 0),
                "trace_count": len(trace),
                "artifact_count": artifact_count,
                "resource_key_count": len(resources),
                "agent": {
                    "id": str(agent.get("id") or execution_node.get("agent_id") or "").strip(),
                    "name": str(agent.get("name") or execution_node.get("agent_name") or "未指派 Agent").strip(),
                    "role": str(agent.get("role") or "").strip(),
                },
                "tools": tools[:6],
                "model": model,
                "error": str(execution_node.get("error") or "").strip(),
            }
        )

    done_count = len([item for item in step_results if str(item.get("status") or "") == "done"])
    running_count = len([item for item in step_results if str(item.get("status") or "") in {"running", "queued"}])
    failed_count = len([item for item in step_results if str(item.get("status") or "") in {"failed", "stopped"}])
    blocked_count = len([item for item in step_results if str(item.get("input_status") or "") == "blocked"])
    produced_count = len([item for item in outputs if item.get("produced")])
    if failed_count:
        status = "failed"
    elif running_count:
        status = "running"
    elif blocked_count:
        status = "blocked"
    elif produced_count == len(outputs) and outputs:
        status = "ready"
    elif step_results:
        status = "warning"
    else:
        status = "draft"
    return {
        "status": status,
        "summary": f"{len(step_results)} 步 · {produced_count}/{len(outputs)} 个输出已产生 · {running_count} 运行 · {failed_count} 失败",
        "context": {
            "input_key": "$input",
            "outputs_key": "$context.outputs",
            "previous_key": "$prev.output",
        },
        "input_data": input_summary,
        "outputs": outputs,
        "step_results": step_results,
        "totals": {
            "step_count": len(step_results),
            "output_count": len(outputs),
            "produced_output_count": produced_count,
            "done_count": done_count,
            "running_count": running_count,
            "failed_count": failed_count,
            "blocked_input_count": blocked_count,
            "total_tokens_used": 0,
        },
    }


def workspace_reproduction_manifest_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    value: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    evidence_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "value": compact_workspace_command(str(value or "").strip(), limit=180),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
    }


def workspace_reproduction_intent(workspace: dict[str, Any]) -> dict[str, str]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    text = " ".join(
        [
            str(inputs.get("goal_text") or ""),
            str(source.get("idea_text") or ""),
            str(workspace.get("brief") or ""),
            str(workspace.get("name") or ""),
        ]
    ).lower()
    deploy_tokens = ["部署", "deploy", "serve", "service", "api", "docker", "上线"]
    reproduce_tokens = ["复现", "reproduce", "baseline", "paper", "实验", "指标"]
    deploy = any(token in text for token in deploy_tokens)
    reproduce = any(token in text for token in reproduce_tokens)
    if deploy and reproduce:
        mode = "mixed"
        label = "复现 + 部署"
    elif deploy:
        mode = "deploy"
        label = "自动部署"
    else:
        mode = "reproduce"
        label = "自动复现"
    return {
        "mode": mode,
        "label": label,
        "source_type": str(inputs.get("source_mode") or source.get("type") or "idea").strip() or "idea",
    }


def compact_contract_items(values: list[Any], *, limit: int = 6) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = compact_workspace_command(str(raw or "").strip(), limit=180)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if len(items) >= limit:
            break
    return items


def workspace_delivery_contract(
    workspace: dict[str, Any],
    intent: dict[str, str],
    *,
    run_command: str = "",
    setup_command: str = "",
    artifact_paths: list[str] | None = None,
    metric_paths: list[str] | None = None,
) -> dict[str, Any]:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    references = inputs.get("references") if isinstance(inputs.get("references"), list) else []
    context_blocks = inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else []
    goal_text = str(inputs.get("goal_text") or workspace.get("brief") or "").strip()
    mode = str(intent.get("mode") or "reproduce")
    criteria: list[str] = []
    criteria.extend(context_blocks)
    if mode in {"reproduce", "mixed"}:
        criteria.extend(
            [
                "记录可复现命令、依赖安装方式、数据路径和 GPU/服务器选择。",
                "收集指标、日志、checkpoint 或输出样例，能说明结果是否达到预期。",
            ]
        )
    if mode in {"deploy", "mixed"}:
        criteria.extend(
            [
                "给出服务启动命令、端口/API/入口说明和最小健康检查方式。",
                "保留部署日志、配置路径、回滚或停止方式，避免只留下一个后台进程。",
            ]
        )
    if run_command:
        criteria.append(f"核心命令可执行：{run_command}")
    if setup_command:
        criteria.append(f"环境准备可复用：{setup_command}")
    artifact_values = compact_contract_items([*(artifact_paths or []), *(metric_paths or [])], limit=4)
    deliverables = compact_contract_items(
        [
            *(artifact_paths or []),
            *(metric_paths or []),
            "运行日志",
            "执行报告",
            "复跑命令与环境摘要",
        ],
        limit=6,
    )
    safety_checks = compact_contract_items(
        [
            "先跑安全发现链，再提交完整运行或部署命令。",
            "运行前确认 workspace_dir、run_command、server/GPU、env 和 artifact_paths。",
            "长任务必须落到 tmux/job 队列，保留日志路径。",
            "部署模式需要有健康检查或 smoke test，避免只看进程存在。",
        ],
        limit=5,
    )
    criteria = compact_contract_items(criteria, limit=6)
    status = "ready" if run_command and (artifact_values or criteria) else "warning" if goal_text or criteria else "draft"
    return {
        "mode": mode,
        "label": str(intent.get("label") or "自动复现/部署"),
        "status": status,
        "goal": compact_workspace_command(goal_text, limit=220),
        "acceptance_criteria": criteria,
        "deliverables": deliverables,
        "safety_checks": safety_checks,
        "reference_count": len(references),
        "context_count": len(context_blocks),
        "summary": f"{len(criteria)} 条验收项 · {len(deliverables)} 个交付物 · {len(safety_checks)} 条安全检查",
    }


def workspace_deployment_health_path(workspace: dict[str, Any], run_command: str) -> str:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    text = " ".join(
        [
            str(inputs.get("goal_text") or ""),
            " ".join(str(item or "") for item in (inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])),
            " ".join(str(item or "") for item in (inputs.get("references") if isinstance(inputs.get("references"), list) else [])),
            str(source.get("idea_text") or ""),
            str(workspace.get("brief") or ""),
            str(run_command or ""),
        ]
    )
    matches = re.findall(r"(?<![A-Za-z0-9_])/(?:api/)?(?:health|ready|readiness|live|liveness|ping|status)(?:/[A-Za-z0-9_.-]+)?", text, flags=re.IGNORECASE)
    if matches:
        return matches[0]
    return "/health"


def workspace_deployment_service_kind(run_command: str) -> str:
    lower = str(run_command or "").lower()
    if "docker compose" in lower or "docker-compose" in lower:
        return "docker-compose"
    if "uvicorn" in lower:
        return "asgi"
    if "gunicorn" in lower:
        return "gunicorn"
    if "streamlit" in lower:
        return "streamlit"
    if "gradio" in lower:
        return "gradio"
    if "flask run" in lower:
        return "flask"
    if "vite" in lower or "npm run dev" in lower or "npm run start" in lower or "pnpm" in lower:
        return "web"
    if "serve" in lower or "server" in lower or " app.py" in lower or lower.startswith("python app.py"):
        return "service"
    return "command"


def workspace_deployment_port(run_command: str) -> str:
    text = str(run_command or "")
    patterns = [
        r"(?:--port|-p)\s+([0-9]{2,5})",
        r"(?:PORT|port)=([0-9]{2,5})",
        r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):([0-9]{2,5})",
        r"\s-p\s+[0-9.]*:([0-9]{2,5})(?::|/|\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def workspace_deployment_host(run_command: str) -> str:
    text = str(run_command or "")
    match = re.search(r"--host\s+([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(?:HOST|host)=([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "127.0.0.1"


def workspace_deployment_stop_command(run_command: str, service_kind: str) -> str:
    command = str(run_command or "").strip()
    if not command:
        return ""
    if service_kind == "docker-compose":
        return "docker compose down || docker-compose down"
    try:
        tokens = shlex.split(command, posix=True) if command else []
    except ValueError:
        tokens = []
    process_hint = " ".join(tokens[:3]) if tokens else command[:80]
    return f"pkill -f {shlex.quote(process_hint)}"


def workspace_deployment_plan(
    workspace: dict[str, Any],
    intent: dict[str, str],
    *,
    run_command: str = "",
    workspace_dir: str = "",
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(intent.get("mode") or "reproduce").strip() or "reproduce"
    service_kind = workspace_deployment_service_kind(run_command)
    relevant = mode in {"deploy", "mixed"} or service_kind not in {"command"}
    port = workspace_deployment_port(run_command)
    host = workspace_deployment_host(run_command)
    health_path = workspace_deployment_health_path(workspace, run_command) if relevant else ""
    health_url = f"http://127.0.0.1:{port}{health_path}" if port and health_path else ""
    smoke_command = f"curl -fsS {shlex.quote(health_url)}" if health_url else ""
    observe_commands = compact_contract_items(
        [
            f"ss -ltnp | grep ':{port}' || true" if port else "",
            smoke_command,
            "docker compose ps || docker-compose ps" if service_kind == "docker-compose" else "",
        ],
        limit=4,
    )
    stop_command = workspace_deployment_stop_command(run_command, service_kind) if relevant else ""
    missing: list[dict[str, str]] = []
    if relevant and not run_command:
        missing.append({"field": "run_command", "label": "服务启动命令", "status": "blocked", "action": "补 run.command，例如 uvicorn/gunicorn/docker compose。"})
    if relevant and not workspace_dir:
        missing.append({"field": "workspace_dir", "label": "部署目录", "status": "warning", "action": "补 workspace_dir，便于部署命令、日志和停止命令可复用。"})
    if relevant and service_kind != "docker-compose" and not port:
        missing.append({"field": "port", "label": "服务端口", "status": "warning", "action": "在目标或命令里补 --port/PORT，才能生成健康检查。"})
    if relevant and port and not health_path:
        missing.append({"field": "health_path", "label": "健康检查路径", "status": "warning", "action": "补 /health、/ready、/ping 或 smoke test 路径。"})
    blocked = any(str(item.get("status") or "") == "blocked" for item in missing)
    status = "blocked" if blocked else "warning" if missing and relevant else "ready" if relevant and run_command else "draft"
    target_info = target if isinstance(target, dict) else {}
    first_missing = missing[0] if missing else {}
    first_field = str(first_missing.get("field") or "").strip()
    run_node = workspace_node_by_kind(workspace, "run.command")
    path_node = workspace_node_by_kind(workspace, "path.resolve") or workspace_node_by_kind(workspace, "repo.clone")
    next_node_id = (
        str(path_node.get("id") or "").strip()
        if first_field == "workspace_dir" and path_node
        else str(run_node.get("id") or "").strip()
        if run_node
        else ""
    )
    return {
        "schema": "relaygraph.deployment_plan.v1",
        "relevant": bool(relevant),
        "status": status,
        "mode": mode,
        "service_kind": service_kind,
        "workspace_dir": str(workspace_dir or "").strip(),
        "server_id": str(target_info.get("server_id") or "auto").strip() or "auto",
        "gpu_policy": str(target_info.get("gpu_policy") or "auto").strip() or "auto",
        "host": host,
        "port": port,
        "health_path": health_path,
        "health_url": health_url,
        "start_command": compact_workspace_command(run_command, limit=220),
        "smoke_test_command": smoke_command,
        "observe_commands": observe_commands,
        "stop_command": stop_command,
        "missing": missing,
        "summary": "非部署目标" if not relevant else f"{service_kind} · {port or '端口待定'} · {health_path or '健康检查待定'}",
        "next_action": {
            "label": "补部署入口" if blocked else "补健康检查" if missing else "验证部署",
            "action": "select-execution-node" if blocked or missing else "run-selected-workspace",
            "status": status,
            "title": "部署计划待补齐" if blocked or missing else "部署计划可验证",
            "detail": str((missing[0] if missing else {}).get("action") or "运行服务后执行 smoke test，并保留观察/停止命令。"),
            "node_id": next_node_id,
        },
    }


def workspace_execution_bundle_step(
    step_id: str,
    label: str,
    command: str,
    status: str,
    detail: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    cwd: str = "",
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "command": compact_workspace_command(command, limit=260),
        "detail": str(detail or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "cwd": str(cwd or "").strip(),
        "env": {str(key): str(value) for key, value in (env or {}).items() if str(value).strip()},
    }


def workspace_execution_bundle_missing_item(
    field: str,
    label: str,
    status: str,
    action: str,
    *,
    node_kind: str = "",
    node_id: str = "",
    button_label: str = "",
    button_action: str = "",
    target_id: str = "",
    tab: str = "home",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    action_name = str(button_action or ("select-execution-node" if node_id else "advance-workspace-automation")).strip()
    fix_action = {
        "label": str(button_label or "处理缺项").strip(),
        "action": action_name,
        "title": str(action or "").strip(),
        "detail": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "target_id": str(target_id or "workspaceExecutionBoard").strip(),
        "tab": str(tab or "home").strip(),
    }
    return {
        "field": str(field or "").strip(),
        "label": str(label or field or "").strip(),
        "status": normalized,
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "fix_action": fix_action,
    }


def workspace_checkout_command(source: dict[str, Any], workspace_dir: str) -> str:
    repo_url = str(source.get("repo_url") or "").strip()
    repo_ref = str(source.get("repo_ref") or "").strip()
    if not repo_url or not workspace_dir:
        return ""
    parent_dir = os.path.dirname(workspace_dir.rstrip("/")) or "."
    clone_name = os.path.basename(workspace_dir.rstrip("/")) or workspace_dir.rstrip("/")
    parts = ["git", "clone"]
    if repo_ref:
        parts.extend(["--branch", shlex.quote(repo_ref)])
    parts.extend([shlex.quote(repo_url), shlex.quote(clone_name)])
    return f"mkdir -p {shlex.quote(parent_dir)} && cd {shlex.quote(parent_dir)} && " + " ".join(parts)


def workspace_script_export_line(key: str, value: Any) -> str:
    normalized_key = re.sub(r"[^A-Za-z0-9_]", "_", str(key or "").strip().upper())
    if not normalized_key or normalized_key[0].isdigit():
        normalized_key = f"RELAYGRAPH_{normalized_key or 'VALUE'}"
    return f"export {normalized_key}={shlex.quote(str(value))}"


def workspace_execution_bundle_command_script(
    target: dict[str, Any],
    steps: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    delivery_contract: dict[str, Any],
    *,
    ready_to_execute: bool,
) -> dict[str, Any]:
    env_name = str(target.get("env_name") or "").strip()
    env_manager = str(target.get("env_manager") or "conda").strip().lower() or "conda"
    workspace_dir = str(target.get("workspace_dir") or "").strip()
    server_id = str(target.get("server_id") or "auto").strip() or "auto"
    gpu_index = str(target.get("gpu_index") or "auto").strip() or "auto"
    gpu_policy = str(target.get("gpu_policy") or "auto").strip() or "auto"
    mode = str(target.get("mode") or delivery_contract.get("mode") or "reproduce").strip() or "reproduce"
    label = str(target.get("label") or delivery_contract.get("label") or "自动复现/部署").strip()
    blocked = [
        {
            "field": str(item.get("field") or "").strip(),
            "label": str(item.get("label") or item.get("field") or "").strip(),
            "status": str(item.get("status") or "warning").strip(),
            "action": str(item.get("action") or "").strip(),
        }
        for item in missing
        if isinstance(item, dict) and str(item.get("status") or "") == "blocked"
    ]
    warnings = [
        {
            "field": str(item.get("field") or "").strip(),
            "label": str(item.get("label") or item.get("field") or "").strip(),
            "status": str(item.get("status") or "warning").strip(),
            "action": str(item.get("action") or "").strip(),
        }
        for item in missing
        if isinstance(item, dict) and str(item.get("status") or "") != "blocked"
    ]
    lines: list[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# RelayGraph execution bundle",
        f"# mode: {mode} · {label}",
        f"# server: {server_id}",
        f"# gpu: {gpu_index} · policy={gpu_policy}",
    ]
    if workspace_dir:
        lines.append(workspace_script_export_line("RELAYGRAPH_WORKSPACE_DIR", workspace_dir))
    lines.append(workspace_script_export_line("RELAYGRAPH_SERVER_ID", server_id))
    lines.append(workspace_script_export_line("RELAYGRAPH_GPU_POLICY", gpu_policy))
    if env_name:
        lines.append(workspace_script_export_line("RELAYGRAPH_ENV_NAME", env_name))
    if gpu_index and gpu_index != "auto" and gpu_policy.lower() not in {"cpu", "none", "no_gpu"}:
        lines.append(workspace_script_export_line("CUDA_VISIBLE_DEVICES", gpu_index))
    elif gpu_policy.lower() in {"cpu", "none", "no_gpu"}:
        lines.append("unset CUDA_VISIBLE_DEVICES")
    if blocked or warnings:
        lines.extend(["", "# Missing inputs"])
        for item in [*blocked, *warnings]:
            field = item["field"] or item["label"] or "unknown"
            action = item["action"] or "等待补齐"
            lines.append(f"# - {field}: {action}")
    if env_name:
        lines.extend(["", "# Environment activation"])
        if env_manager == "conda":
            lines.append(conda_bootstrap(env_name))
        elif env_manager == "venv":
            env_path = shlex.quote(env_name)
            lines.extend(
                [
                    f"if [ -f {env_path}/bin/activate ]; then",
                    f"  . {env_path}/bin/activate",
                    'elif [ -n "${RELAYGRAPH_WORKSPACE_DIR:-}" ] && [ -f "$RELAYGRAPH_WORKSPACE_DIR/.venv/bin/activate" ]; then',
                    '  . "$RELAYGRAPH_WORKSPACE_DIR/.venv/bin/activate"',
                    "fi",
                ]
            )
        else:
            lines.append(f"# env_manager={env_manager}; activate {shlex.quote(env_name)} if your runner requires it.")
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "step").strip()
        label_text = str(step.get("label") or step_id).strip()
        status = str(step.get("status") or "draft").strip()
        command = str(step.get("command") or "").strip()
        cwd = str(step.get("cwd") or "").strip()
        env_values = step.get("env") if isinstance(step.get("env"), dict) else {}
        detail = str(step.get("detail") or "").strip()
        lines.extend(["", f"# Step: {label_text} ({step_id})", f"# status: {status}"])
        if cwd:
            lines.append(f"cd {shlex.quote(cwd)}")
        for key, value in env_values.items():
            value_text = str(value or "").strip()
            if value_text:
                lines.append(workspace_script_export_line(key, value_text))
        if command:
            lines.append(command)
        else:
            lines.append(f"# TODO {step_id}: {detail or '等待命令生成'}")
    text = "\n".join(lines).strip() + "\n"
    return {
        "shell": "bash",
        "status": "ready" if ready_to_execute and not blocked else "blocked" if blocked else "warning" if warnings else "draft",
        "ready": bool(ready_to_execute and not blocked),
        "text": text,
        "lines": lines,
        "blocked": blocked,
        "warnings": warnings,
        "summary": f"{len([step for step in steps if isinstance(step, dict)])} 个步骤 · {len(blocked)} 阻塞 · {len(warnings)} 提示",
    }


def workspace_execution_package_manifest(
    workspace: dict[str, Any],
    intent: dict[str, str],
    delivery_contract: dict[str, Any],
    target: dict[str, Any],
    steps: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    command_script: dict[str, Any],
    *,
    commands: dict[str, Any],
    paths: dict[str, Any],
    evidence: dict[str, Any],
    scheduler: dict[str, Any],
    dataset_discovery: dict[str, Any] | None = None,
    deployment_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    candidates = scheduler.get("candidates") if isinstance(scheduler.get("candidates"), list) else []
    dataset_plan = dataset_discovery if isinstance(dataset_discovery, dict) else {}
    deploy_plan = deployment_plan if isinstance(deployment_plan, dict) else {}
    return {
        "schema": "relaygraph.execution_package.v1",
        "workspace": {
            "id": str(workspace.get("id") or "").strip(),
            "name": str(workspace.get("name") or "").strip(),
            "template_id": str(workspace.get("template_id") or "").strip(),
            "template_name": str(workspace.get("template_name") or "").strip(),
        },
        "intent": copy.deepcopy(intent),
        "status": str(command_script.get("status") or "").strip(),
        "ready_to_execute": bool(command_script.get("ready")),
        "delivery_contract": copy.deepcopy(delivery_contract),
        "deployment_plan": copy.deepcopy(deploy_plan),
        "target": copy.deepcopy(target),
        "commands": copy.deepcopy(commands),
        "paths": copy.deepcopy(paths),
        "dataset_discovery": {
            "status": str(dataset_plan.get("status") or "").strip(),
            "summary": str(dataset_plan.get("summary") or "").strip(),
            "queries": copy.deepcopy(dataset_plan.get("queries") if isinstance(dataset_plan.get("queries"), list) else []),
            "local_roots": copy.deepcopy(dataset_plan.get("local_roots") if isinstance(dataset_plan.get("local_roots"), list) else []),
            "source_refs": copy.deepcopy(dataset_plan.get("source_refs") if isinstance(dataset_plan.get("source_refs"), list) else []),
            "expected_layout": str(dataset_plan.get("expected_layout") or "").strip(),
            "next_action": copy.deepcopy(dataset_plan.get("next_action") if isinstance(dataset_plan.get("next_action"), dict) else {}),
        },
        "steps": copy.deepcopy(steps),
        "missing": copy.deepcopy(missing),
        "evidence": copy.deepcopy(evidence),
        "scheduler": {
            "status": str(scheduler.get("status") or "").strip(),
            "mode": str(scheduler.get("mode") or "").strip(),
            "policy": str(scheduler.get("policy") or "").strip(),
            "summary": str(scheduler.get("summary") or "").strip(),
            "selected": copy.deepcopy(selected),
            "candidate_count": len(candidates),
        },
        "command_script": {
            "shell": str(command_script.get("shell") or "bash").strip(),
            "status": str(command_script.get("status") or "").strip(),
            "ready": bool(command_script.get("ready")),
            "summary": str(command_script.get("summary") or "").strip(),
            "text": str(command_script.get("text") or ""),
        },
    }


def workspace_execution_bundle_step_for_node(bundle: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    steps = bundle.get("steps") if isinstance(bundle.get("steps"), list) else []
    node_id = str(node.get("id") or "").strip()
    kind = str(node.get("kind") or "").strip()
    step_id_by_kind = {
        "repo.clone": "checkout",
        "path.resolve": "checkout",
        "env.infer": "setup",
        "env.prepare": "setup",
        "gpu.allocate": "run",
        "run.command": "run",
        "artifact.collect": "collect",
        "eval.report": "report",
    }
    return next(
        (
            step for step in steps
            if isinstance(step, dict)
            and (
                (node_id and str(step.get("node_id") or "").strip() == node_id)
                or (kind and str(step.get("node_kind") or "").strip() == kind)
                or str(step.get("id") or "").strip() == step_id_by_kind.get(kind, "")
            )
        ),
        {},
    )


def workspace_execution_bundle_job_metadata(automation: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    if not bundle:
        return {}
    command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
    step = workspace_execution_bundle_step_for_node(bundle, node)
    script_meta = {
        "shell": str(command_script.get("shell") or "bash").strip(),
        "status": str(command_script.get("status") or "").strip(),
        "ready": bool(command_script.get("ready")),
        "summary": str(command_script.get("summary") or "").strip(),
    }
    metadata: dict[str, Any] = {
        "status": str(bundle.get("status") or "").strip(),
        "ready_to_execute": bool(bundle.get("ready_to_execute")),
        "target": copy.deepcopy(bundle.get("target") if isinstance(bundle.get("target"), dict) else {}),
        "script": script_meta,
    }
    if step:
        metadata["step"] = {
            "id": str(step.get("id") or "").strip(),
            "label": str(step.get("label") or "").strip(),
            "status": str(step.get("status") or "").strip(),
            "node_kind": str(step.get("node_kind") or "").strip(),
            "node_id": str(step.get("node_id") or "").strip(),
            "cwd": str(step.get("cwd") or "").strip(),
            "env": copy.deepcopy(step.get("env") if isinstance(step.get("env"), dict) else {}),
        }
    if str(node.get("kind") or "").strip() == "run.command" and str(command_script.get("text") or "").strip():
        metadata["command_script"] = {
            **script_meta,
            "text": str(command_script.get("text") or ""),
        }
    return metadata


def workspace_scheduler_binding_metadata(
    automation: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    automation = automation if isinstance(automation, dict) else {}
    config = config if isinstance(config, dict) else {}
    resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
    scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    values = workspace_scheduler_values_from_selection(scheduler) if scheduler else {}

    fallback_policy = str(config.get("gpu_policy") or "").strip().lower()
    fallback_gpu_index = str(config.get("gpu_index") if config.get("gpu_index") is not None else "").strip()
    fallback_server_id = str(config.get("server_id") or "").strip()
    cpu_mode = (
        str(values.get("mode") or selected.get("mode") or "").strip().lower() == "cpu"
        or str(values.get("gpu_policy") or fallback_policy).strip().lower() in {"cpu", "none", "no_gpu"}
        or fallback_gpu_index in {"cpu", "none", "no_gpu"}
    )
    gpu_index = str(values.get("gpu_index") or fallback_gpu_index or ("none" if cpu_mode else "auto")).strip()
    server_id = str(values.get("server_id") or selected.get("server_id") or fallback_server_id or "auto").strip() or "auto"
    min_free_memory_gib = str(values.get("min_free_memory_gib") or config.get("min_free_memory_gib") or "").strip()
    selected_host = selected.get("host") if isinstance(selected.get("host"), dict) else {}
    compact_selected = {
        "id": str(selected.get("id") or "").strip(),
        "status": str(selected.get("status") or "").strip(),
        "mode": str(selected.get("mode") or values.get("mode") or ("cpu" if cpu_mode else "gpu")).strip(),
        "score": safe_int(selected.get("score") if selected.get("score") is not None else values.get("score"), 0),
        "server_id": str(selected.get("server_id") or server_id).strip(),
        "server_name": str(selected.get("server_name") or "").strip(),
        "gpu_index": str(selected.get("gpu_index") if selected.get("gpu_index") is not None else gpu_index).strip(),
        "gpu_name": str(selected.get("gpu_name") or "").strip(),
        "gpu_state": str(selected.get("gpu_state") or "").strip(),
        "memory_free_mib": safe_int(selected.get("memory_free_mib"), 0),
        "memory_total_mib": safe_int(selected.get("memory_total_mib"), 0),
        "gpu_util": safe_int(selected.get("gpu_util"), 0),
        "process_count": safe_int(selected.get("process_count"), 0),
        "snapshot_age_seconds": safe_int(selected.get("snapshot_age_seconds"), 0),
        "collected_at": str(selected.get("collected_at") or "").strip(),
    }
    return {
        "status": str(scheduler.get("status") or values.get("status") or "draft").strip(),
        "mode": "cpu" if cpu_mode else str(values.get("mode") or scheduler.get("mode") or selected.get("mode") or "gpu").strip(),
        "policy": str(values.get("gpu_policy") or scheduler.get("policy") or fallback_policy or ("cpu" if cpu_mode else "auto")).strip(),
        "server_id": server_id,
        "gpu_index": "none" if cpu_mode else gpu_index,
        "min_free_memory_gib": min_free_memory_gib,
        "summary": str(scheduler.get("summary") or resource.get("summary") or "").strip(),
        "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
        "ready_count": safe_int(scheduler.get("ready_count"), 0),
        "requested_server_id": str(scheduler.get("requested_server_id") or "").strip(),
        "requested_gpu_index": str(scheduler.get("requested_gpu_index") or "").strip(),
        "selected": compact_selected,
        "host": copy.deepcopy(selected_host),
        "reasons": copy.deepcopy(selected.get("reasons") if isinstance(selected.get("reasons"), list) else []),
        "warnings": copy.deepcopy(selected.get("warnings") if isinstance(selected.get("warnings"), list) else []),
    }


def workspace_execution_bundle_result(automation: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    if not bundle:
        return {}
    command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
    package_manifest = bundle.get("package_manifest") if isinstance(bundle.get("package_manifest"), dict) else {}
    return {
        "status": str(bundle.get("status") or "").strip(),
        "ready_to_execute": bool(bundle.get("ready_to_execute")),
        "target": copy.deepcopy(bundle.get("target") if isinstance(bundle.get("target"), dict) else {}),
        "script": {
            "shell": str(command_script.get("shell") or "bash").strip(),
            "status": str(command_script.get("status") or "").strip(),
            "ready": bool(command_script.get("ready")),
            "summary": str(command_script.get("summary") or "").strip(),
        },
        "package_manifest": copy.deepcopy(package_manifest),
        "job_count": len(jobs),
        "job_ids": [str(job.get("id") or "").strip() for job in jobs if isinstance(job, dict) and str(job.get("id") or "").strip()],
    }


def derive_workspace_reproduction_manifest(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    resource_orchestration: dict[str, Any],
    dataset_discovery: dict[str, Any],
    execution_context: dict[str, Any],
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    resource_items = resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else []
    resource_index = {
        str(item.get("id") or "").strip(): item
        for item in resource_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    context_totals = execution_context.get("totals") if isinstance(execution_context.get("totals"), dict) else {}
    repo_urls = inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else []
    paper_urls = inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else []
    references = inputs.get("references") if isinstance(inputs.get("references"), list) else []
    source_value = (
        repo_urls[0] if repo_urls else
        paper_urls[0] if paper_urls else
        str(inputs.get("goal_text") or source.get("repo_url") or source.get("paper_url") or source.get("idea_text") or workspace.get("brief") or "").strip()
    )
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    env_prepare_config = workspace_node_config_by_kind(workspace, "env.prepare")
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")
    eval_config = workspace_node_config_by_kind(workspace, "eval.report")
    data_roots = workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots"))
    output_roots = workspace_config_values(path_config.get("output_roots"))
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints"))
    dataset_plan = dataset_discovery if isinstance(dataset_discovery, dict) else derive_workspace_dataset_discovery_plan(workspace, execution, evidence)
    dataset_queries = dataset_plan.get("queries") if isinstance(dataset_plan.get("queries"), list) else []
    dataset_roots = dataset_plan.get("local_roots") if isinstance(dataset_plan.get("local_roots"), list) else []
    dataset_sources = dataset_plan.get("source_refs") if isinstance(dataset_plan.get("source_refs"), list) else []
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths"))
    metric_paths = workspace_config_values(artifact_config.get("metric_paths")) + workspace_config_values(eval_config.get("metric_paths"))
    setup_command = str(env_prepare_config.get("setup_command") or "").strip()
    run_command = str(run_config.get("run_command") or "").strip()
    report_command = str(eval_config.get("report_command") or "").strip()
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip() or "auto"
    resource_candidates = resource_orchestration.get("resource_candidates") if isinstance(resource_orchestration.get("resource_candidates"), dict) else {}
    evidence_count = sum(safe_int(group.get("count"), 0) for group in evidence if isinstance(group, dict))
    metric_count = safe_int(workspace_evidence_group(evidence, "metric").get("count"), 0)
    artifact_count = safe_int(workspace_evidence_group(evidence, "artifact").get("count"), 0)
    source_check = check_index.get("source", {})
    path_item = resource_index.get("paths", {})
    dataset_item = resource_index.get("dataset", {})
    env_item = resource_index.get("env", {})
    gpu_item = resource_index.get("gpu", {})
    run_item = resource_index.get("run", {})
    artifact_item = resource_index.get("artifact", {})
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    node_by_kind = {
        str(node.get("kind") or "").strip(): str(node.get("id") or "").strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip()
    }
    source_node_id = next(
        (
            str(node.get("id") or "").strip()
            for node in nodes
            if isinstance(node, dict)
            and str(node.get("kind") or "").strip() in {"source.repo", "source.paper", "source.idea", "research.search"}
        ),
        "",
    )
    manifest_items = [
        workspace_reproduction_manifest_item(
            "source",
            "目标/来源",
            str(source_check.get("status") or "draft"),
            str(source_check.get("title") or "等待目标输入"),
            source_value or "等待目标、repo 或论文",
            f"{len(repo_urls)} repo · {len(paper_urls)} paper · {len(references)} 参考",
            str(source_check.get("action") or "补目标、repo、论文、数据路径或约束。"),
            node_id=source_node_id,
        ),
        workspace_reproduction_manifest_item(
            "checkout",
            "源码/路径",
            str(path_item.get("status") or "warning"),
            str(path_item.get("title") or ("工作目录已设置" if workspace_dir else "路径等待解析")),
            workspace_dir or str(path_item.get("value") or ""),
            f"{len(data_roots)} 数据根 · {len(output_roots)} 输出根",
            str(path_item.get("action") or "运行 path.resolve 或补 workspace_dir/data_roots/output_roots。"),
            node_kind="path.resolve",
            node_id=node_by_kind.get("path.resolve", ""),
            evidence_count=safe_int(path_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "dataset",
            "数据集",
            str(dataset_item.get("status") or dataset_plan.get("status") or "warning"),
            str(dataset_item.get("title") or ("发现计划已生成" if dataset_queries or dataset_roots else "缺数据集线索")),
            str(dataset_item.get("value") or (dataset_hints[0] if dataset_hints else dataset_queries[0] if dataset_queries else dataset_roots[0] if dataset_roots else "")),
            f"{len(dataset_queries)} 查询 · {len(dataset_roots)} 本地根 · {len(dataset_sources)} 资料入口 · {len(dataset_hints)} 手动线索",
            str(dataset_item.get("action") or (dataset_plan.get("next_action") or {}).get("detail") or "运行 dataset.find 或补数据集名称、本地路径、下载页。"),
            node_kind="dataset.find",
            node_id=node_by_kind.get("dataset.find", ""),
            evidence_count=safe_int(dataset_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "environment",
            "环境",
            str(env_item.get("status") or "warning"),
            str(env_item.get("title") or ("环境入口已具备" if setup_command or env.get("name") else "缺环境入口")),
            setup_command or str(env.get("name") or env_item.get("value") or ""),
            f"{env.get('manager') or 'conda'} · Python {env.get('python') or '待定'}",
            str(env_item.get("action") or "运行 env.infer/env.prepare 或补 setup_command。"),
            node_kind="env.prepare",
            node_id=node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", ""),
            evidence_count=safe_int(env_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "gpu",
            "GPU/服务器",
            str(gpu_item.get("status") or "warning"),
            str(gpu_item.get("title") or "GPU 快照不足"),
            str(gpu_item.get("value") or resource_candidates.get("recommended_server_id") or "auto"),
            f"policy={gpu_policy} · 空闲 GPU {safe_int(resource_candidates.get('idle_gpu_count'), 0)}/{safe_int(resource_candidates.get('gpu_count'), 0)}",
            str(gpu_item.get("action") or "刷新资源或设置 server_id/gpu_policy/min_free_memory_gib。"),
            node_kind="gpu.allocate",
            node_id=node_by_kind.get("gpu.allocate", ""),
            evidence_count=safe_int(gpu_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "run",
            "运行/部署入口",
            str(run_item.get("status") or "blocked"),
            str(run_item.get("title") or ("运行命令已设置" if run_command else "缺 run command")),
            run_command or "等待可提交命令",
            str(run_plan.get("summary") or "等待运行预案"),
            str(run_item.get("action") or "补 run.command，或运行发现链让 Agent 推断入口。"),
            node_kind="run.command",
            node_id=node_by_kind.get("run.command", ""),
        ),
        workspace_reproduction_manifest_item(
            "artifacts",
            "产物/指标",
            str(artifact_item.get("status") or "warning"),
            str(artifact_item.get("title") or ("产物入口已设置" if artifact_paths or metric_paths else "缺产物路径")),
            str(artifact_item.get("value") or (artifact_paths[0] if artifact_paths else metric_paths[0] if metric_paths else "")),
            f"{len(artifact_paths)} 产物路径 · {len(metric_paths)} 指标路径 · {artifact_count} 产物证据 · {metric_count} 指标证据",
            str(artifact_item.get("action") or "运行 artifact.collect/eval.report，收集 logs、checkpoints、metrics。"),
            node_kind="artifact.collect",
            node_id=node_by_kind.get("artifact.collect", ""),
            evidence_count=safe_int(artifact_item.get("evidence_count"), 0),
        ),
        workspace_reproduction_manifest_item(
            "report",
            "报告/交付",
            "ready" if metric_count or report_command else "warning",
            "可以整理报告" if metric_count or report_command else "等待报告入口",
            report_command or "等待 eval.report / 指标证据",
            f"{safe_int(context_totals.get('produced_output_count'), 0)} 个上下文输出已产生 · {evidence_count} 条证据",
            "运行 eval.report 或让报告 Agent 汇总命令、指标、产物和失败原因。",
            node_kind="eval.report",
            node_id=node_by_kind.get("eval.report", ""),
            evidence_count=metric_count,
        ),
    ]
    status_counts: dict[str, int] = {}
    for item in manifest_items:
        status = str(item.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    hard_blockers = [
        item for item in manifest_items
        if str(item.get("id") or "") in {"source", "run"} and str(item.get("status") or "") in {"blocked", "failed", "draft"}
    ]
    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    if status_counts.get("failed") or hard_blockers or run_blocking:
        status = "blocked"
    elif status_counts.get("running"):
        status = "running"
    elif status_counts.get("blocked"):
        status = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    next_item = next(
        (
            item for item in manifest_items
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        manifest_items[-1] if manifest_items else {},
    )
    intent = workspace_reproduction_intent(workspace)
    delivery_contract = workspace_delivery_contract(
        workspace,
        intent,
        run_command=run_command,
        setup_command=setup_command,
        artifact_paths=artifact_paths,
        metric_paths=metric_paths,
    )
    ready_count = status_counts.get("ready", 0) + status_counts.get("done", 0)
    checkout_source = copy.deepcopy(source)
    if not str(checkout_source.get("repo_url") or "").strip() and repo_urls:
        checkout_source["repo_url"] = repo_urls[0]
    checkout_command = workspace_checkout_command(checkout_source, workspace_dir)
    recommended_server_id = str(resource_candidates.get("recommended_server_id") or gpu_config.get("server_id") or run_config.get("server_id") or "auto").strip() or "auto"
    recommended_gpu_index = str(resource_candidates.get("recommended_gpu_index") or "").strip()
    cuda_env = {}
    if recommended_gpu_index and gpu_policy.lower() not in {"cpu", "none", "no_gpu"}:
        cuda_env["CUDA_VISIBLE_DEVICES"] = recommended_gpu_index
    command_env = {
        **cuda_env,
        **({"CONDA_DEFAULT_ENV": str(env.get("name") or "").strip()} if str(env.get("name") or "").strip() else {}),
    }
    dataset_command = workspace_dataset_discovery_bundle_command(dataset_plan)
    bundle_steps = [
        workspace_execution_bundle_step(
            "checkout",
            "准备源码/路径",
            checkout_command,
            "ready" if checkout_command or workspace_dir else "warning",
            "克隆或确认工作目录，后续节点都以这里作为 cwd。",
            node_kind="repo.clone",
            node_id=node_by_kind.get("repo.clone", "") or node_by_kind.get("path.resolve", ""),
            cwd=os.path.dirname(workspace_dir.rstrip("/")) if workspace_dir else "",
        ),
        workspace_execution_bundle_step(
            "dataset",
            "定位数据集",
            dataset_command,
            "ready" if str(dataset_plan.get("status") or "") in {"ready", "done"} else "warning",
            str(dataset_plan.get("summary") or "从目标、论文、README、参考路径和本地数据根定位数据集。"),
            node_kind="dataset.find",
            node_id=node_by_kind.get("dataset.find", ""),
            cwd=workspace_dir,
        ),
        workspace_execution_bundle_step(
            "setup",
            "准备环境",
            setup_command,
            "ready" if setup_command else "warning",
            "安装依赖或激活环境；缺失时先运行 env.infer/env.prepare。",
            node_kind="env.prepare",
            node_id=node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", ""),
            cwd=workspace_dir,
            env={"CONDA_DEFAULT_ENV": str(env.get("name") or "").strip()},
        ),
        workspace_execution_bundle_step(
            "run",
            "运行/部署",
            run_command,
            "ready" if run_command and str(run_plan.get("status") or "") == "ready" else "blocked" if not run_command else "warning",
            "提交核心训练、推理、服务启动或 smoke test 命令。",
            node_kind="run.command",
            node_id=node_by_kind.get("run.command", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
        workspace_execution_bundle_step(
            "collect",
            "收集产物",
            " && ".join([f"find {shlex.quote(path)} -maxdepth 2 -type f | head -50" for path in (artifact_paths + metric_paths)[:4]]),
            "ready" if artifact_paths or metric_paths else "warning",
            "回收 logs、checkpoints、outputs、metrics，供报告和下游复跑使用。",
            node_kind="artifact.collect",
            node_id=node_by_kind.get("artifact.collect", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
        workspace_execution_bundle_step(
            "report",
            "整理报告",
            report_command,
            "ready" if report_command or metric_count else "warning",
            "汇总指标、产物、命令、资源占用和失败原因。",
            node_kind="eval.report",
            node_id=node_by_kind.get("eval.report", ""),
            cwd=workspace_dir,
            env=command_env,
        ),
    ]
    path_node_id = node_by_kind.get("path.resolve", "") or node_by_kind.get("repo.clone", "")
    env_node_id = node_by_kind.get("env.prepare", "") or node_by_kind.get("env.infer", "")
    gpu_node_id = node_by_kind.get("gpu.allocate", "")
    run_node_id = node_by_kind.get("run.command", "")
    artifact_node_id = node_by_kind.get("artifact.collect", "") or node_by_kind.get("eval.report", "")
    bundle_missing = []
    if not workspace_dir:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "workspace_dir",
                "工作目录",
                "blocked",
                "补 workspace_dir 或运行 path.resolve。",
                node_kind="path.resolve" if node_by_kind.get("path.resolve", "") else "repo.clone",
                node_id=path_node_id,
                button_label="定位路径节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if not run_command:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "run_command",
                "运行命令",
                "blocked",
                "补 run.command 或让自动发现推断入口。",
                node_kind="run.command",
                node_id=run_node_id,
                button_label="定位运行节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if not setup_command:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "setup_command",
                "环境安装命令",
                "warning",
                "运行 env.infer/env.prepare 生成安装建议。",
                node_kind="env.prepare" if node_by_kind.get("env.prepare", "") else "env.infer",
                node_id=env_node_id,
                button_label="自动发现",
                button_action="run-workspace-discovery",
                target_id="workspaceExecutionDetail",
            )
        )
    if not artifact_paths and not metric_paths:
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "artifact_paths",
                "产物路径",
                "warning",
                "补 runs/outputs/checkpoints/logs/metrics 路径。",
                node_kind="artifact.collect" if node_by_kind.get("artifact.collect", "") else "eval.report",
                node_id=artifact_node_id,
                button_label="定位产物节点",
                button_action="select-execution-node",
                target_id="workspaceExecutionDetail",
            )
        )
    if recommended_server_id == "auto" and not safe_int(resource_candidates.get("online_server_count"), 0):
        bundle_missing.append(
            workspace_execution_bundle_missing_item(
                "server_id",
                "目标服务器",
                "warning",
                "刷新资源或选择可用服务器。",
                node_kind="gpu.allocate",
                node_id=gpu_node_id,
                button_label="刷新资源",
                button_action="refresh-workspace-resources",
                target_id="workspaceCockpitOperations",
            )
        )
    bundle_status = "blocked" if any(item["status"] == "blocked" for item in bundle_missing) else "warning" if bundle_missing else "ready"
    first_missing = bundle_missing[0] if bundle_missing else {}
    missing_field = str(first_missing.get("field") or "").strip()
    if bundle_status == "ready" and str(run_plan.get("status") or "") == "ready":
        bundle_next_action = {
            "label": "提交执行包",
            "action": "run-selected-workspace",
            "status": "ready",
            "title": "提交完整执行链",
            "detail": "按执行包里的 checkout/setup/run/collect/report 顺序提交工作流。",
            "node_id": run_node_id,
        }
    elif missing_field == "workspace_dir":
        bundle_next_action = {
            "label": "定位路径节点",
            "action": "select-execution-node",
            "status": "blocked",
            "title": "补工作目录",
            "detail": str(first_missing.get("action") or "补 workspace_dir 或运行 path.resolve。"),
            "node_id": node_by_kind.get("path.resolve", "") or node_by_kind.get("repo.clone", ""),
        }
    elif missing_field == "run_command":
        bundle_next_action = {
            "label": "定位运行节点",
            "action": "select-execution-node",
            "status": "blocked",
            "title": "补运行命令",
            "detail": str(first_missing.get("action") or "补 run.command 后再提交执行包。"),
            "node_id": run_node_id,
        }
    elif missing_field == "server_id":
        bundle_next_action = {
            "label": "刷新资源",
            "action": "refresh-workspace-resources",
            "status": "warning",
            "title": "刷新服务器/GPU",
            "detail": str(first_missing.get("action") or "刷新资源后重新计算执行包目标。"),
            "node_id": node_by_kind.get("gpu.allocate", ""),
        }
    elif missing_field in {"setup_command", "artifact_paths"}:
        bundle_next_action = {
            "label": "自动发现",
            "action": "run-workspace-discovery",
            "status": "warning",
            "title": "补执行包证据",
            "detail": str(first_missing.get("action") or "运行安全发现链补齐环境、产物或路径证据。"),
            "node_id": node_by_kind.get("env.infer", "") if missing_field == "setup_command" else node_by_kind.get("artifact.collect", ""),
        }
    else:
        bundle_next_action = {
            "label": "自动推进",
            "action": "advance-workspace-automation",
            "status": bundle_status,
            "title": "推进执行包",
            "detail": "让系统按当前执行包、门禁和证据决定下一步。",
            "node_id": run_node_id,
        }
    ready_to_execute = bundle_status == "ready" and str(run_plan.get("status") or "") == "ready"
    bundle_target = {
        "mode": intent["mode"],
        "label": intent["label"],
        "workspace_dir": workspace_dir,
        "server_id": recommended_server_id,
        "gpu_index": recommended_gpu_index or "auto",
        "gpu_policy": gpu_policy,
        "env_name": str(env.get("name") or "").strip(),
        "env_manager": str(env.get("manager") or "").strip() or "conda",
        "python": str(env.get("python") or "").strip(),
    }
    deployment_plan = workspace_deployment_plan(
        workspace,
        intent,
        run_command=run_command,
        workspace_dir=workspace_dir,
        target=bundle_target,
    )
    command_script = workspace_execution_bundle_command_script(
        bundle_target,
        bundle_steps,
        bundle_missing,
        delivery_contract,
        ready_to_execute=ready_to_execute,
    )
    bundle_evidence = {
        "total_count": evidence_count,
        "artifact_count": artifact_count,
        "metric_count": metric_count,
        "data_roots": data_roots[:6],
        "dataset_hints": dataset_hints[:6],
    }
    manifest_commands = {
        "checkout_command": compact_workspace_command(checkout_command, limit=180),
        "setup_command": compact_workspace_command(setup_command, limit=180),
        "run_command": compact_workspace_command(run_command, limit=180),
        "report_command": compact_workspace_command(report_command, limit=180),
    }
    manifest_paths = {
        "workspace_dir": workspace_dir,
        "data_roots": data_roots[:6],
        "output_roots": output_roots[:6],
        "artifact_paths": artifact_paths[:8],
        "metric_paths": metric_paths[:8],
    }
    package_manifest = workspace_execution_package_manifest(
        workspace,
        intent,
        delivery_contract,
        bundle_target,
        bundle_steps,
        bundle_missing,
        command_script,
        commands=manifest_commands,
        paths=manifest_paths,
        evidence=bundle_evidence,
        scheduler=resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {},
        dataset_discovery=dataset_plan,
        deployment_plan=deployment_plan,
    )
    execution_bundle = {
        "status": bundle_status,
        "ready_to_execute": ready_to_execute,
        "next_action": bundle_next_action,
        "target": bundle_target,
        "steps": bundle_steps,
        "missing": bundle_missing,
        "command_script": command_script,
        "package_manifest": package_manifest,
        "evidence": bundle_evidence,
        "delivery_contract": delivery_contract,
        "deployment_plan": deployment_plan,
    }
    return {
        "status": status,
        "intent": intent,
        "delivery_contract": delivery_contract,
        "deployment_plan": deployment_plan,
        "summary": f"{intent['label']}清单 · {ready_count}/{len(manifest_items)} 项就绪 · {status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
        "items": manifest_items,
        "counts": status_counts,
        "next_action": {
            "id": str(next_item.get("id") or "").strip(),
            "title": str(next_item.get("title") or next_item.get("label") or "等待下一步").strip(),
            "detail": str(next_item.get("detail") or "").strip(),
            "action": str(next_item.get("action") or "").strip(),
            "node_kind": str(next_item.get("node_kind") or "").strip(),
            "node_id": str(next_item.get("node_id") or "").strip(),
            "status": str(next_item.get("status") or status).strip(),
        },
        "commands": manifest_commands,
        "paths": manifest_paths,
        "dataset_discovery": copy.deepcopy(dataset_plan),
        "execution_bundle": execution_bundle,
        "ready_to_run": status == "ready" and str(run_plan.get("status") or "") == "ready",
    }


def workspace_evidence_group(evidence: list[dict[str, Any]], group_id: str) -> dict[str, Any]:
    return next(
        (
            item for item in evidence
            if isinstance(item, dict) and str(item.get("id") or "") == group_id
        ),
        {"id": group_id, "count": 0, "items": []},
    )


def workspace_report_highlight(label: str, value: str, detail: str = "", status: str = "ready") -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "detail": detail,
        "status": status,
    }


def workspace_report_next_action(label: str, detail: str, action: str, status: str = "ready") -> dict[str, Any]:
    return {
        "label": label,
        "detail": detail,
        "action": action,
        "status": status,
    }


def workspace_execution_readiness_step(
    step_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    evidence_count: int = 0,
    blocker_count: int = 0,
    warning_count: int = 0,
    node_count: int = 0,
    job_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
        "blocker_count": safe_int(blocker_count, 0),
        "warning_count": safe_int(warning_count, 0),
        "node_count": safe_int(node_count, 0),
        "job_count": safe_int(job_count, 0),
    }


def workspace_resource_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    value: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
    phase: str = "",
    evidence_count: int = 0,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "value": str(value or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "phase": str(phase or "").strip(),
        "evidence_count": safe_int(evidence_count, 0),
    }


def workspace_preflight_action(
    label: str,
    action: str,
    *,
    tone: str = "secondary",
    title: str = "",
    node_id: str = "",
    server_id: str = "",
    tab: str = "",
    mode: str = "",
) -> dict[str, Any]:
    return {
        "label": str(label or "操作").strip(),
        "action": str(action or "").strip(),
        "tone": "primary" if tone == "primary" else "secondary",
        "title": str(title or label or "").strip(),
        "node_id": str(node_id or "").strip(),
        "server_id": str(server_id or "").strip(),
        "tab": str(tab or "").strip(),
        "mode": str(mode or "").strip(),
    }


def workspace_preflight_item(
    item_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    layer: str = "",
    phase: str = "",
    node_kind: str = "",
    node_id: str = "",
    requires: list[str] | None = None,
    missing: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    action_button: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(item_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "layer": str(layer or "").strip(),
        "phase": str(phase or "").strip(),
        "node_kind": str(node_kind or "").strip(),
        "node_id": str(node_id or "").strip(),
        "requires": [str(item or "").strip() for item in (requires or []) if str(item or "").strip()],
        "missing": [str(item or "").strip() for item in (missing or []) if str(item or "").strip()],
        "metrics": metrics or {},
        "action_button": action_button or {},
    }


def workspace_preflight_combined_status(*statuses: Any) -> str:
    normalized = [str(status or "").strip() for status in statuses if str(status or "").strip()]
    for status in ("failed", "blocked", "warning", "draft", "running", "ready", "done"):
        if status in normalized:
            return status
    return "draft"


def derive_workspace_preflight(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    run_plan: dict[str, Any],
    dataset_discovery: dict[str, Any],
    resource_orchestration: dict[str, Any],
    agent_topology: dict[str, Any],
    reproduction_manifest: dict[str, Any],
    execution_readiness: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    bundle = reproduction_manifest.get("execution_bundle") if isinstance(reproduction_manifest.get("execution_bundle"), dict) else {}
    scheduler = resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {}
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    job_state = execution_readiness.get("job_state") if isinstance(execution_readiness.get("job_state"), dict) else {}
    readiness_steps = {
        str(step.get("id") or "").strip(): step
        for step in (execution_readiness.get("steps") if isinstance(execution_readiness.get("steps"), list) else [])
        if isinstance(step, dict) and str(step.get("id") or "").strip()
    }

    def check(check_id: str) -> dict[str, Any]:
        return check_index.get(check_id, {})

    def node_id(kind: str) -> str:
        node = workspace_node_by_kind(workspace, kind)
        return str(node.get("id") or "").strip() if node else ""

    def missing_from_checks(*check_ids: str) -> list[str]:
        values: list[str] = []
        for check_id in check_ids:
            item = check(check_id)
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft"}:
                text = str(item.get("title") or item.get("detail") or item.get("label") or check_id).strip()
                if text:
                    values.append(text)
        return values

    source_count = sum(
        1
        for value in (
            source.get("repo_url"),
            source.get("paper_url"),
            source.get("idea_text"),
            workspace.get("brief"),
            inputs.get("goal_text"),
        )
        if str(value or "").strip()
    )
    source_count += len(inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else [])
    source_count += len(inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else [])
    source_count += len(inputs.get("references") if isinstance(inputs.get("references"), list) else [])
    source_check = check("source")
    starter_check = check("starter_chain")
    path_check = check("paths")
    dataset_check = check("dataset")
    env_check = check("env")
    gpu_check = check("gpu")
    run_check = check("run")
    artifact_check = check("artifact")
    agents_check = check("agents")

    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    bundle_missing = bundle.get("missing") if isinstance(bundle.get("missing"), list) else []
    topology_layers = agent_topology.get("layers") if isinstance(agent_topology.get("layers"), dict) else {}
    model_layer = topology_layers.get("ai") if isinstance(topology_layers.get("ai"), dict) else {}
    agent_layer = topology_layers.get("agent") if isinstance(topology_layers.get("agent"), dict) else {}
    tool_layer = topology_layers.get("tool") if isinstance(topology_layers.get("tool"), dict) else {}
    dataset_queries = dataset_discovery.get("queries") if isinstance(dataset_discovery.get("queries"), list) else []
    dataset_roots = dataset_discovery.get("local_roots") if isinstance(dataset_discovery.get("local_roots"), list) else []
    resource_candidates = resource_orchestration.get("resource_candidates") if isinstance(resource_orchestration.get("resource_candidates"), dict) else {}
    active_count = safe_int(job_state.get("active_count"), 0)
    failed_count = safe_int(job_state.get("failed_count"), 0)
    done_count = safe_int(job_state.get("done_count"), 0)

    items = [
        workspace_preflight_item(
            "launcher",
            "项目启动器",
            str(source_check.get("status") or "draft"),
            str(source_check.get("title") or ("输入已绑定" if source_count else "等待输入")),
            str(source_check.get("detail") or f"{source_count} 条输入线索"),
            str(source_check.get("action") or "补 repo、论文、目标描述、参考路径和约束。"),
            layer="project",
            phase="launch",
            requires=["repo / paper / idea", "目标简报", "参考路径或约束"],
            missing=missing_from_checks("source"),
            metrics={"input_count": source_count},
            action_button=workspace_preflight_action("项目设置", "switch-workspace-tab", tab="project", title="打开项目设置，补齐启动输入和目录环境。"),
        ),
        workspace_preflight_item(
            "workflow_chain",
            "工作流节点链",
            workspace_preflight_combined_status(starter_check.get("status"), run_plan.get("status")),
            str(run_plan.get("summary") or starter_check.get("title") or "等待节点链"),
            str(starter_check.get("detail") or f"{safe_int(run_plan.get('node_count'), 0)} 个可执行节点"),
            str(starter_check.get("action") or "补齐路径、数据、环境、GPU、运行、产物和报告节点。"),
            layer="workflow",
            phase="orchestrate",
            requires=["Starter Chain", "节点 I/O 契约", "可执行 run node"],
            missing=missing_from_checks("starter_chain", "run") + [
                str(item.get("detail") or item.get("title") or item.get("field") or "").strip()
                for item in run_blocking[:4]
                if isinstance(item, dict)
            ],
            metrics={"node_count": len(nodes), "run_node_count": safe_int(run_plan.get("node_count"), 0), "blocking_count": len(run_blocking)},
            action_button=workspace_preflight_action("节点链", "switch-workspace-tab", tab="workflow", title="打开工作流页，查看节点链和 I/O 交接。"),
        ),
        workspace_preflight_item(
            "data_paths",
            "数据和路径",
            workspace_preflight_combined_status(path_check.get("status"), dataset_check.get("status"), dataset_discovery.get("status")),
            str(dataset_discovery.get("summary") or dataset_check.get("title") or "等待数据计划"),
            f"{len(dataset_queries)} 查询 · {len(dataset_roots)} 本地根 · workspace_dir={str(workspace.get('workspace_dir') or '未设置')}",
            str(dataset_check.get("action") or path_check.get("action") or "运行 path.resolve / dataset.find，或补本地数据根。"),
            layer="data",
            phase="discover",
            node_kind="dataset.find",
            node_id=node_id("dataset.find"),
            requires=["workspace_dir", "data_roots", "dataset hints / query"],
            missing=missing_from_checks("paths", "dataset"),
            metrics={"query_count": len(dataset_queries), "local_root_count": len(dataset_roots)},
            action_button=workspace_preflight_action("自动发现", "run-workspace-discovery", tone="primary", title="运行安全发现链，收集路径和数据候选。"),
        ),
        workspace_preflight_item(
            "environment",
            "环境准备",
            str(env_check.get("status") or "warning"),
            str(env_check.get("title") or "等待环境入口"),
            str(env_check.get("detail") or "等待 env_name、setup_command 或环境清单。"),
            str(env_check.get("action") or "运行 env.infer 或补 setup_command。"),
            layer="env",
            phase="setup",
            node_kind="env.prepare",
            node_id=node_id("env.prepare"),
            requires=["env_name", "setup_command", "requirements / environment manifest"],
            missing=missing_from_checks("env"),
            metrics={"manifest_count": len(workspace_config_values(workspace_node_config_by_kind(workspace, "env.infer").get("manifest_paths")))},
            action_button=workspace_preflight_action("环境节点", "switch-workspace-tab", tab="workflow", title="打开工作流页，定位环境推断和准备节点。"),
        ),
        workspace_preflight_item(
            "scheduler",
            "资源/GPU 调度",
            workspace_preflight_combined_status(gpu_check.get("status"), resource_orchestration.get("status"), scheduler.get("status")),
            str(scheduler.get("summary") or resource_orchestration.get("summary") or gpu_check.get("title") or "等待调度"),
            str(resource_orchestration.get("next_action", {}).get("detail") if isinstance(resource_orchestration.get("next_action"), dict) else "") or str(gpu_check.get("detail") or ""),
            str(gpu_check.get("action") or "刷新资源快照，或设置 server_id/gpu_policy/min_free_memory_gib。"),
            layer="resource",
            phase="schedule",
            node_kind="gpu.allocate",
            node_id=node_id("gpu.allocate"),
            requires=["server snapshot", "GPU policy", "host/GPU availability"],
            missing=missing_from_checks("gpu"),
            metrics={
                "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
                "ready_count": safe_int(scheduler.get("ready_count"), 0),
                "online_server_count": safe_int(resource_candidates.get("online_server_count"), 0),
                "idle_gpu_count": safe_int(resource_candidates.get("idle_gpu_count"), 0),
            },
            action_button=workspace_preflight_action(
                "刷新调度",
                "refresh-workspace-resource-server" if str(selected.get("server_id") or "").strip() else "refresh-workspace-resources",
                tone="primary" if str(resource_orchestration.get("status") or "") in {"blocked", "warning", "draft"} else "secondary",
                title="刷新资源快照并更新 GPU/主机调度候选。",
                server_id=str(selected.get("server_id") or "").strip(),
            ),
        ),
        workspace_preflight_item(
            "agent_tool_ai",
            "Agent / Tool / AI",
            workspace_preflight_combined_status(agents_check.get("status"), agent_topology.get("status"), model_layer.get("status")),
            str(agent_topology.get("summary") or agents_check.get("title") or "等待分层"),
            f"Agent {agent_layer.get('assigned_count', 0)}/{agent_layer.get('required_count', 0)} · Tool {tool_layer.get('assigned_count', 0)}/{tool_layer.get('required_count', 0)} · AI {model_layer.get('title') or model_layer.get('status') or '待配置'}",
            str(agents_check.get("action") or "补 Agent 归属、工具 allowlist 和 Provider Profile。"),
            layer="agent_tool_ai",
            phase="delegate",
            requires=["node owner Agent", "tool allowlist", "Provider Profile / routing"],
            missing=missing_from_checks("agents") + [
                str(item.get("title") or item.get("detail") or item.get("type") or "").strip()
                for item in (agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else [])[:4]
                if isinstance(item, dict)
            ],
            metrics={
                "agent_assigned": safe_int(agent_layer.get("assigned_count"), 0),
                "tool_assigned": safe_int(tool_layer.get("assigned_count"), 0),
                "gap_count": len(agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []),
            },
            action_button=workspace_preflight_action("分层配置", "switch-workspace-tab", tab="agents", title="打开 Agent 分层页，检查角色、工具和模型覆盖。"),
        ),
        workspace_preflight_item(
            "execution_package",
            "执行包",
            str(bundle.get("status") or reproduction_manifest.get("status") or "draft"),
            "执行包可提交" if bundle.get("ready_to_execute") else str(bundle.get("next_action", {}).get("label") if isinstance(bundle.get("next_action"), dict) else "") or "执行包未就绪",
            str(bundle.get("command_script", {}).get("summary") if isinstance(bundle.get("command_script"), dict) else "") or str(reproduction_manifest.get("summary") or ""),
            str(bundle.get("next_action", {}).get("detail") if isinstance(bundle.get("next_action"), dict) else "") or "先补齐执行包缺失字段。",
            layer="package",
            phase="execute",
            node_kind="run.command",
            node_id=node_id("run.command"),
            requires=["checkout/setup/run/report script", "target server/GPU", "delivery contract"],
            missing=[
                str(item.get("field") or item.get("label") or item.get("detail") or "").strip()
                for item in bundle_missing[:6]
                if isinstance(item, dict)
            ],
            metrics={"ready_to_execute": bool(bundle.get("ready_to_execute")), "missing_count": len(bundle_missing)},
            action_button=workspace_preflight_action(
                "提交执行包" if bundle.get("ready_to_execute") else "自动推进",
                "run-selected-workspace" if bundle.get("ready_to_execute") else "advance-workspace-automation",
                tone="primary",
                title="提交完整执行包，或让系统先自动补齐缺失项。",
            ),
        ),
        workspace_preflight_item(
            "run_records",
            "运行/报告闭环",
            "failed" if failed_count else "running" if active_count else str(report.get("status") or readiness_steps.get("collect_report", {}).get("status") or "draft"),
            str(report.get("headline") or readiness_steps.get("collect_report", {}).get("title") or "等待运行记录"),
            str(report.get("summary") or f"{active_count} 活跃 · {failed_count} 失败 · {done_count} 完成"),
            str((report.get("next_actions") if isinstance(report.get("next_actions"), list) and report.get("next_actions") else [{}])[0].get("action") or "运行完成后收集日志、指标、产物和复跑报告。"),
            layer="report",
            phase="collect",
            requires=["job logs", "artifacts", "metrics", "re-run report"],
            missing=[] if active_count or failed_count or done_count else ["还没有运行记录"],
            metrics={"active": active_count, "failed": failed_count, "done": done_count},
            action_button=workspace_preflight_action(
                "打开输出" if active_count or failed_count else "运行记录",
                "open-last-workspace-log" if active_count or failed_count else "switch-workspace-tab",
                tone="primary" if active_count or failed_count else "secondary",
                tab="" if active_count or failed_count else "runs",
                title="打开最近任务输出，或进入运行记录查看历史。",
            ),
        ),
    ]

    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "draft")
        counts[status] = counts.get(status, 0) + 1
    if counts.get("failed"):
        status = "failed"
    elif counts.get("running"):
        status = "running"
    elif counts.get("blocked"):
        status = "blocked"
    elif counts.get("warning") or counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    ready_count = counts.get("ready", 0) + counts.get("done", 0)
    next_item = next(
        (
            item for item in items
            if str(item.get("status") or "") in {"failed", "blocked", "warning", "draft", "running"}
        ),
        items[-1] if items else {},
    )
    return {
        "status": status,
        "summary": f"{ready_count}/{len(items)} 环节就绪 · {counts.get('blocked', 0)} 阻塞 · {counts.get('warning', 0)} 提示 · {counts.get('running', 0)} 运行",
        "items": items,
        "counts": counts,
        "ready_count": ready_count,
        "blocked_count": counts.get("blocked", 0),
        "warning_count": counts.get("warning", 0) + counts.get("draft", 0),
        "running_count": counts.get("running", 0),
        "failed_count": counts.get("failed", 0),
        "next_action": next_item,
    }


def derive_workspace_resource_orchestration(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    statuses: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
) -> dict[str, Any]:
    check_index = {
        str(check.get("id") or "").strip(): check
        for check in checks
        if isinstance(check, dict) and str(check.get("id") or "").strip()
    }
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    env_prepare_config = workspace_node_config_by_kind(workspace, "env.prepare")
    env_infer_config = workspace_node_config_by_kind(workspace, "env.infer")
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")

    path_group = workspace_evidence_group(evidence, "paths")
    dataset_group = workspace_evidence_group(evidence, "dataset")
    env_group = workspace_evidence_group(evidence, "env")
    gpu_group = workspace_evidence_group(evidence, "gpu")
    run_group = workspace_evidence_group(evidence, "run")
    artifact_group = workspace_evidence_group(evidence, "artifact")
    metric_group = workspace_evidence_group(evidence, "metric")

    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]
    all_gpus = [
        gpu for status in online_statuses
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else [])
        if isinstance(gpu, dict)
    ]
    idle_gpus = [gpu for gpu in all_gpus if str(gpu.get("state") or "") == "idle"]

    data_roots = workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots"))
    output_roots = workspace_config_values(path_config.get("output_roots"))
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints"))
    manifest_paths = workspace_config_values(env_infer_config.get("manifest_paths"))
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths"))
    metric_paths = workspace_config_values(artifact_config.get("metric_paths"))
    setup_command = str(env_prepare_config.get("setup_command") or "").strip()
    run_command = str(run_config.get("run_command") or "").strip()
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip().lower() or "auto"
    cpu_mode = gpu_policy in {"cpu", "none", "no_gpu"}
    requested_server_id = str(run_config.get("server_id") or gpu_config.get("server_id") or "auto").strip() or "auto"
    requested_gpu_index = str(run_config.get("gpu_index") or gpu_config.get("gpu_index") or "").strip()
    min_free_memory_gib = safe_int(run_config.get("min_free_memory_gib") or gpu_config.get("min_free_memory_gib"), 0)
    scheduler = derive_workspace_resource_scheduler(
        statuses,
        gpu_policy=gpu_policy,
        requested_server_id=requested_server_id,
        requested_gpu_index=requested_gpu_index,
        min_free_memory_gib=min_free_memory_gib,
    )
    selected_candidate = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    best_gpu = selected_candidate if selected_candidate.get("mode") == "gpu" else infer_workspace_best_gpu(statuses)

    path_check = check_index.get("paths", {})
    dataset_check = check_index.get("dataset", {})
    env_check = check_index.get("env", {})
    gpu_check = check_index.get("gpu", {})
    run_check = check_index.get("run", {})
    artifact_check = check_index.get("artifact", {})

    first_dataset_item = next((item for item in dataset_group.get("items", []) if isinstance(item, dict)), {})
    first_env_item = next((item for item in env_group.get("items", []) if isinstance(item, dict)), {})
    first_run_item = next((item for item in run_group.get("items", []) if isinstance(item, dict)), {})
    first_artifact_item = next((item for item in artifact_group.get("items", []) if isinstance(item, dict)), {})
    repo_or_paper = str(source.get("repo_url") or source.get("paper_url") or source.get("idea_text") or workspace.get("brief") or "").strip()

    items = [
        workspace_resource_item(
            "paths",
            "路径",
            str(path_check.get("status") or "warning"),
            str(path_check.get("title") or ("工作目录已设置" if workspace_dir else "路径等待解析")),
            workspace_dir or str((path_group.get("items") or [{}])[0].get("value") if path_group.get("items") else ""),
            f"{len(data_roots)} 条数据根 · {len(output_roots)} 条输出根 · {safe_int(path_group.get('count'), 0)} 条证据",
            str(path_check.get("action") or "补 workspace_dir/data_roots/output_roots，或运行 path.resolve。"),
            node_kind="path.resolve",
            phase="discover",
            evidence_count=safe_int(path_group.get("count"), 0),
        ),
        workspace_resource_item(
            "dataset",
            "数据集",
            str(dataset_check.get("status") or "warning"),
            str(dataset_check.get("title") or ("数据线索已出现" if dataset_hints or first_dataset_item else "缺数据集线索")),
            str(first_dataset_item.get("value") or dataset_config.get("query") or repo_or_paper or "等待数据线索"),
            f"{len(dataset_hints)} 条线索 · {len(data_roots)} 条候选根 · {safe_int(dataset_group.get('count'), 0)} 条证据",
            str(dataset_check.get("action") or "补数据集名称、下载页、本地数据根，或运行 dataset.find。"),
            node_kind="dataset.find",
            phase="discover",
            evidence_count=safe_int(dataset_group.get("count"), 0),
        ),
        workspace_resource_item(
            "env",
            "环境",
            str(env_check.get("status") or "warning"),
            str(env_check.get("title") or ("环境入口已具备" if setup_command or env.get("name") else "缺环境入口")),
            str(first_env_item.get("value") or setup_command or env.get("name") or "等待环境推断"),
            f"{env.get('manager') or 'conda'} · {env.get('python') or 'Python 待定'} · {len(manifest_paths)} 个清单候选",
            str(env_check.get("action") or "运行 env.infer 或补 setup_command。"),
            node_kind="env.infer",
            phase="setup",
            evidence_count=safe_int(env_group.get("count"), 0),
        ),
        workspace_resource_item(
            "gpu",
            "GPU",
            str(gpu_check.get("status") or "warning"),
            str(gpu_check.get("title") or ("资源策略可执行" if cpu_mode or idle_gpus else "GPU 快照不足")),
            "CPU/无 GPU 模式" if cpu_mode else (
                f"{best_gpu.get('server_id', 'auto')} · GPU {best_gpu.get('gpu_index', 'auto')}" if best_gpu else "等待 GPU 快照"
            ),
            f"{len(online_statuses)} 台在线 · {len(idle_gpus)}/{len(all_gpus)} 张空闲 · policy={gpu_policy}",
            str(gpu_check.get("action") or "刷新监控或设置 server_id/gpu_policy/min_free_memory_gib。"),
            node_kind="gpu.allocate",
            phase="run",
            evidence_count=safe_int(gpu_group.get("count"), 0),
        ),
        workspace_resource_item(
            "run",
            "运行入口",
            str(run_check.get("status") or "blocked"),
            str(run_check.get("title") or ("运行命令已设置" if run_command else "发现运行候选" if first_run_item else "缺 run command")),
            compact_workspace_command(run_command) if run_command else str(first_run_item.get("value") or "等待可提交命令"),
            str(run_plan.get("summary") or "等待运行预案"),
            str(run_check.get("action") or ("回填发现运行命令后再提交完整工作流。" if first_run_item else "补 run.command，或让 Agent 从 README/脚本中推断。")),
            node_kind="run.command",
            phase="run",
            evidence_count=safe_int(run_group.get("count"), 0),
        ),
        workspace_resource_item(
            "artifact",
            "产物/指标",
            str(artifact_check.get("status") or "warning"),
            str(artifact_check.get("title") or ("产物入口已设置" if artifact_paths or first_artifact_item else "缺产物路径")),
            str(first_artifact_item.get("value") or (artifact_paths[0] if artifact_paths else "等待产物入口")),
            f"{len(artifact_paths)} 条产物路径 · {len(metric_paths)} 条指标路径 · {safe_int(metric_group.get('count'), 0)} 条指标证据",
            str(artifact_check.get("action") or "补 runs/outputs/checkpoints/logs/metrics 路径并运行 artifact.collect。"),
            node_kind="artifact.collect",
            phase="collect",
            evidence_count=safe_int(artifact_group.get("count"), 0) + safe_int(metric_group.get("count"), 0),
        ),
    ]

    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    if status_counts.get("blocked") or status_counts.get("failed"):
        status = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        status = "warning"
    else:
        status = "ready"
    next_item = next(
        (item for item in items if str(item.get("status") or "") in {"blocked", "failed", "warning", "draft"}),
        items[-1] if items else {},
    )
    ready_count = status_counts.get("ready", 0) + status_counts.get("done", 0)
    return {
        "status": status,
        "summary": f"{ready_count}/{len(items)} 项调度就绪 · {status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
        "counts": status_counts,
        "items": items,
        "next_action": next_item,
        "resource_candidates": {
            "online_server_count": len(online_statuses),
            "gpu_count": len(all_gpus),
            "idle_gpu_count": len(idle_gpus),
            "recommended_server_id": str(selected_candidate.get("server_id") or best_gpu.get("server_id") or "").strip(),
            "recommended_gpu_index": str(selected_candidate.get("gpu_index") or best_gpu.get("gpu_index") or "").strip(),
            "recommended_gpu_free_mib": safe_int(best_gpu.get("memory_free_mib"), 0),
        },
        "scheduler": scheduler,
    }


def derive_workspace_automation_report(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    status_counts: dict[str, int],
) -> dict[str, Any]:
    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    metric_group = workspace_evidence_group(evidence, "metric")
    artifact_group = workspace_evidence_group(evidence, "artifact")
    dataset_group = workspace_evidence_group(evidence, "dataset")
    env_group = workspace_evidence_group(evidence, "env")
    gpu_group = workspace_evidence_group(evidence, "gpu")
    metric_items = metric_group.get("items") if isinstance(metric_group.get("items"), list) else []
    artifact_items = artifact_group.get("items") if isinstance(artifact_group.get("items"), list) else []
    dataset_items = dataset_group.get("items") if isinstance(dataset_group.get("items"), list) else []
    env_items = env_group.get("items") if isinstance(env_group.get("items"), list) else []
    gpu_items = gpu_group.get("items") if isinstance(gpu_group.get("items"), list) else []
    blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    warnings = run_plan.get("warnings") if isinstance(run_plan.get("warnings"), list) else []

    if counts.get("failed"):
        status = "failed"
        headline = "运行存在失败节点"
    elif blocking:
        status = "blocked"
        headline = "完整运行前仍有阻塞项"
    elif counts.get("running") or counts.get("queued"):
        status = "running"
        headline = "工作流正在运行"
    elif metric_items:
        status = "done"
        headline = "已捕获运行指标"
    elif warnings:
        status = "warning"
        headline = "运行预案可执行但仍有提示"
    else:
        status = "ready"
        headline = "运行预案已就绪"

    metric_value = " · ".join(str(item.get("value") or "") for item in metric_items[:3] if isinstance(item, dict) and str(item.get("value") or "").strip())
    env_value = str((env_items[0] if env_items else {}).get("value") or "等待环境证据")
    dataset_value = str((dataset_items[0] if dataset_items else {}).get("value") or "等待数据证据")
    gpu_value = str((gpu_items[0] if gpu_items else {}).get("value") or "等待 GPU 证据")
    highlights = [
        workspace_report_highlight(
            "就绪度",
            f"{status_counts.get('ready', 0) + status_counts.get('done', 0)} 项就绪",
            f"{status_counts.get('blocked', 0)} 阻塞 · {status_counts.get('warning', 0)} 提示",
            "blocked" if status_counts.get("blocked") else "ready",
        ),
        workspace_report_highlight(
            "运行预案",
            str(run_plan.get("summary") or "等待生成"),
            "完整运行前的节点和阶段预览。",
            str(run_plan.get("status") or "draft"),
        ),
        workspace_report_highlight(
            "核心指标",
            metric_value or "等待运行指标",
            f"{safe_int(metric_group.get('count'), 0)} 条指标证据",
            "ready" if metric_items else "draft",
        ),
        workspace_report_highlight(
            "数据/环境/GPU",
            dataset_value,
            f"环境：{env_value} · GPU：{gpu_value}",
            "ready" if dataset_items or env_items or gpu_items else "draft",
        ),
        workspace_report_highlight(
            "产物",
            f"{safe_int(artifact_group.get('count'), 0)} 条产物/日志证据",
            str((artifact_items[0] if artifact_items else {}).get("value") or "等待产物收集"),
            "ready" if artifact_items else "draft",
        ),
    ]

    next_actions: list[dict[str, Any]] = []
    if blocking:
        first = blocking[0]
        next_actions.append(
            workspace_report_next_action(
                "处理运行阻塞",
                str(first.get("detail") or first.get("title") or ""),
                str(first.get("action") or "先运行自动发现或补齐节点配置。"),
                "blocked",
            )
        )
    if not any(safe_int(item.get("count"), 0) for item in evidence if isinstance(item, dict)):
        next_actions.append(
            workspace_report_next_action(
                "运行自动发现",
                "先收集路径、数据、环境、GPU 和产物入口证据。",
                "点击“自动发现”。",
                "ready",
            )
        )
    if not metric_items and (counts.get("done") or counts.get("running") or counts.get("queued")):
        next_actions.append(
            workspace_report_next_action(
                "补指标证据",
                "已有运行记录，但还没有解析到核心指标。",
                "查看运行日志或补 metric_paths 后运行 artifact.collect / eval.report。",
                "warning",
            )
        )
    if warnings and not blocking:
        first_warning = warnings[0]
        next_actions.append(
            workspace_report_next_action(
                "处理提示项",
                str(first_warning.get("detail") or first_warning.get("title") or ""),
                str(first_warning.get("action") or "可以先运行自动发现补齐证据。"),
                "warning",
            )
        )
    if not next_actions:
        next_actions.append(
            workspace_report_next_action(
                "整理最终报告",
                "关键证据已经进入驾驶舱，可以汇总运行命令、指标、产物路径和复跑建议。",
                "运行 eval.report 或把证据交给报告 Agent。",
                "ready",
            )
        )

    return {
        "status": status,
        "title": "复现/部署报告草稿",
        "headline": headline,
        "summary": f"{safe_int(counts.get('done'), 0)} 完成 · {safe_int(counts.get('running'), 0)} 运行 · {safe_int(counts.get('failed'), 0)} 失败 · {safe_int(metric_group.get('count'), 0)} 指标",
        "highlights": highlights,
        "next_actions": next_actions[:5],
        "blockers": blocking[:6],
        "warnings": warnings[:6],
    }


def derive_workspace_automation_advance_hint(
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, str]:
    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    queued = safe_int(counts.get("queued"), 0)
    running = safe_int(counts.get("running"), 0)
    failed = safe_int(counts.get("failed"), 0)
    if queued or running:
        return workspace_advance_decision(
            "watch",
            "观察当前任务",
            f"{queued} 个排队 · {running} 个运行，继续提交前先看当前输出。",
            "打开运行记录或日志面板，等任务完成后再自动推进。",
            status="running",
        )
    if failed:
        return workspace_advance_decision(
            "review_failed",
            "复查失败任务",
            f"{failed} 个任务失败或停止，继续前需要确认失败原因。",
            "查看失败任务日志，修正配置后再次自动推进。",
            status="failed",
        )

    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    discovery_runs = sum(
        safe_int(node.get("run_count"), 0)
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_DISCOVERY_NODE_KINDS
    )
    if not discovery_runs:
        return workspace_advance_decision(
            "discover",
            "提交安全发现",
            "还没有发现链证据，先探测源码、路径、数据、环境、GPU 和产物入口。",
            "点击自动推进提交发现链，完成后再次自动推进。",
            status="ready",
        )

    hard_gate_ids = {"starter_chain", "agents", "run"}
    blocked = [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed"}
    ]
    if blocked:
        labels = [
            str(item.get("label") or item.get("title") or item.get("id") or "").strip()
            for item in blocked
            if isinstance(item, dict)
        ]
        return workspace_advance_decision(
            "blocked",
            "处理运行阻塞",
            "硬门禁未通过：" + "、".join([item for item in labels if item][:5]),
            "补齐阻塞项后再次自动推进。",
            status="blocked",
        )

    return workspace_advance_decision(
        "run",
        "整理并提交运行",
        "已有发现记录且硬门禁没有阻塞，自动推进会先回填证据再提交完整执行链。",
        "点击自动推进后跟踪第一个运行任务输出。",
        status="ready",
    )


def derive_workspace_execution_readiness(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    run_plan: dict[str, Any],
    advance: dict[str, Any],
    agent_topology: dict[str, Any],
    resource_orchestration: dict[str, Any],
) -> dict[str, Any]:
    counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    nodes = execution.get("nodes") if isinstance(execution.get("nodes"), list) else []
    queued_count = safe_int(counts.get("queued"), 0)
    starting_count = safe_int(counts.get("starting"), 0)
    running_count = safe_int(counts.get("running"), 0)
    active_count = queued_count + starting_count + running_count + safe_int(counts.get("blocked"), 0)
    failed_count = safe_int(counts.get("failed"), 0) + safe_int(counts.get("stopped"), 0)
    done_count = safe_int(counts.get("done"), 0)
    discovery_run_count = sum(
        safe_int(node.get("run_count"), 0)
        for node in nodes
        if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_DISCOVERY_NODE_KINDS
    )
    evidence_count = sum(
        safe_int(item.get("count"), 0)
        for item in evidence
        if isinstance(item, dict)
    )
    artifact_count = safe_int(workspace_evidence_group(evidence, "artifact").get("count"), 0)
    metric_count = safe_int(workspace_evidence_group(evidence, "metric").get("count"), 0)
    blocked_checks = workspace_workflow_blocking_checks({"checks": checks})
    run_blocking = run_plan.get("blocking") if isinstance(run_plan.get("blocking"), list) else []
    run_warnings = run_plan.get("warnings") if isinstance(run_plan.get("warnings"), list) else []
    topology_gaps = agent_topology.get("gaps") if isinstance(agent_topology.get("gaps"), list) else []
    topology_blocking = [
        item for item in topology_gaps
        if isinstance(item, dict) and str(item.get("status") or "") in {"blocked", "failed"}
    ]
    resource_items = resource_orchestration.get("items") if isinstance(resource_orchestration.get("items"), list) else []
    resource_blocking = [
        item for item in resource_items
        if isinstance(item, dict) and str(item.get("status") or "") in {"blocked", "failed"}
    ]
    resource_warnings = [
        item for item in resource_items
        if isinstance(item, dict) and str(item.get("status") or "") in {"warning", "draft"}
    ]
    run_node_count = safe_int(run_plan.get("node_count"), 0)
    first_blocker = next(
        (
            item for item in [*blocked_checks, *run_blocking, *resource_blocking, *topology_blocking]
            if isinstance(item, dict)
        ),
        {},
    )
    first_warning = next(
        (
            item for item in [*run_warnings, *resource_warnings, *topology_gaps]
            if isinstance(item, dict)
        ),
        {},
    )

    if failed_count:
        gate_status = "failed"
        gate_title = "失败任务待复查"
        gate_detail = f"{failed_count} 个任务失败或停止，继续前先看日志和节点输出。"
        gate_action = "打开失败任务日志，修正配置后再自动推进。"
    elif active_count:
        gate_status = "running"
        gate_title = "当前任务未结束"
        gate_detail = f"{queued_count} 个排队 · {running_count} 个运行，先等当前执行稳定。"
        gate_action = "观察当前任务，完成后再次自动推进。"
    elif blocked_checks:
        gate_status = "blocked"
        gate_title = "硬门禁未通过"
        gate_detail = workspace_readiness_message(blocked_checks)
        gate_action = str(first_blocker.get("action") or "补齐节点链、Agent 归属或运行命令后再提交完整链。")
    else:
        gate_status = "ready"
        gate_title = "硬门禁已通过"
        gate_detail = "节点链、Agent 归属和运行命令没有硬阻塞。"
        gate_action = "可以继续自动推进；若还没有 discovery 记录，会先提交安全发现。"

    if run_blocking:
        force_status = "blocked"
        force_title = "强制运行仍会被节点校验挡住"
        force_action = "先处理节点 payload 阻塞，再考虑 force_run。"
    elif blocked_checks:
        force_status = "warning"
        force_title = "强制运行会跳过硬门禁"
        force_action = "只在你确认风险可控时使用 force_run，提交前仍会逐节点校验 payload。"
    elif run_warnings or resource_warnings or topology_gaps:
        force_status = "warning"
        force_title = "不建议强制运行"
        force_action = str(first_warning.get("action") or "先处理提示项，降低运行失败概率。")
    else:
        force_status = "ready"
        force_title = "无需强制运行"
        force_action = "按正常自动推进或运行工作流即可。"
    force_run = {
        "status": force_status,
        "title": force_title,
        "detail": f"{len(blocked_checks)} 个硬门禁 · {len(run_blocking)} 个节点阻塞 · {len(run_warnings)} 个提示",
        "action": force_action,
        "blockers": run_blocking[:6],
        "warnings": run_warnings[:6],
    }

    if active_count:
        discovery_status = "running"
        discovery_title = "发现/执行任务进行中"
        discovery_action = "等待当前任务完成后再继续推进。"
    elif discovery_run_count:
        discovery_status = "done"
        discovery_title = "已有发现链记录"
        discovery_action = "可以回填发现证据，再提交完整执行链。"
    else:
        discovery_status = "ready"
        discovery_title = "可以提交安全发现"
        discovery_action = "点击自动推进或自动发现，先跑 repo/path/data/env/GPU/artifact 安全节点。"

    if evidence_count:
        apply_status = "ready"
        apply_title = "发现证据可回填"
        apply_action = "点击回填建议/发现，或由自动推进在完整运行前自动回填。"
    elif discovery_run_count:
        apply_status = "warning"
        apply_title = "发现记录缺少可用证据"
        apply_action = "查看发现节点输出，补数据根、环境清单或产物路径。"
    else:
        apply_status = "draft"
        apply_title = "等待发现证据"
        apply_action = "先提交安全发现，再回填路径、数据、环境和产物证据。"

    resource_status = str(resource_orchestration.get("status") or "draft")
    resource_next = resource_orchestration.get("next_action") if isinstance(resource_orchestration.get("next_action"), dict) else {}
    resource_summary = str(resource_orchestration.get("summary") or "等待资源调度")

    if active_count:
        full_run_status = "running"
        full_run_title = "完整链正在执行或排队"
        full_run_action = "先观察当前任务输出。"
    elif failed_count:
        full_run_status = "failed"
        full_run_title = "完整链存在失败记录"
        full_run_action = "打开失败日志，修正后再重试。"
    else:
        full_run_status = str(run_plan.get("status") or "draft")
        full_run_title = "完整执行链已就绪" if full_run_status == "ready" else "完整执行链未就绪"
        full_run_action = (
            "点击自动推进或运行工作流提交完整链。"
            if full_run_status == "ready"
            else str(first_blocker.get("action") or "先处理运行预案中的阻塞项。")
        )

    if metric_count:
        collect_status = "done"
        collect_title = "指标已回收"
        collect_action = "可以整理复现/部署报告。"
    elif artifact_count:
        collect_status = "ready"
        collect_title = "产物入口已出现"
        collect_action = "继续运行 artifact.collect / eval.report 汇总指标。"
    elif active_count:
        collect_status = "running"
        collect_title = "等待运行产物"
        collect_action = "任务结束后自动或手动收集产物和指标。"
    elif failed_count:
        collect_status = "warning"
        collect_title = "失败后缺少可用产物"
        collect_action = "先复查失败日志，再收集可用的输出片段。"
    elif done_count:
        collect_status = "warning"
        collect_title = "运行完成但指标不足"
        collect_action = "补 artifact_paths / metric_paths 后运行产物收集。"
    else:
        collect_status = "draft"
        collect_title = "等待产物/指标回收"
        collect_action = "完整运行完成后收集 logs、checkpoints、metrics 和报告。"

    steps = [
        workspace_execution_readiness_step(
            "safe_discovery",
            "安全发现",
            discovery_status,
            discovery_title,
            f"{discovery_run_count} 次发现节点运行 · {evidence_count} 条证据",
            discovery_action,
            evidence_count=evidence_count,
            job_count=discovery_run_count,
        ),
        workspace_execution_readiness_step(
            "defaults_evidence",
            "默认/证据回填",
            apply_status,
            apply_title,
            f"{evidence_count} 条发现证据可用于路径、环境、数据和产物默认值。",
            apply_action,
            evidence_count=evidence_count,
        ),
        workspace_execution_readiness_step(
            "resource_binding",
            "资源调度",
            resource_status,
            str(resource_next.get("title") or resource_summary),
            str(resource_next.get("detail") or resource_summary),
            str(resource_next.get("action") or "补齐路径、数据、环境、GPU 和产物配置。"),
            blocker_count=len(resource_blocking),
            warning_count=len(resource_warnings),
        ),
        workspace_execution_readiness_step(
            "hard_gate",
            "门禁检查",
            gate_status,
            gate_title,
            gate_detail,
            gate_action,
            blocker_count=len(blocked_checks),
        ),
        workspace_execution_readiness_step(
            "full_run",
            "完整执行链",
            full_run_status,
            full_run_title,
            str(run_plan.get("summary") or "等待运行预案"),
            full_run_action,
            blocker_count=len(run_blocking),
            warning_count=len(run_warnings),
            node_count=run_node_count,
        ),
        workspace_execution_readiness_step(
            "collect_report",
            "产物/指标回收",
            collect_status,
            collect_title,
            f"{artifact_count} 条产物证据 · {metric_count} 条指标证据",
            collect_action,
            evidence_count=artifact_count + metric_count,
        ),
    ]

    if failed_count:
        status = "failed"
    elif active_count:
        status = "running"
    elif blocked_checks or run_blocking or resource_blocking or topology_blocking:
        status = "blocked"
    elif run_warnings or resource_warnings or topology_gaps:
        status = "warning"
    else:
        status = "ready"

    ready_count = sum(1 for step in steps if str(step.get("status") or "") in {"ready", "done"})
    blockers = [
        workspace_enrich_readiness_issue(workspace, item)
        for item in [*blocked_checks, *run_blocking, *resource_blocking, *topology_blocking]
        if isinstance(item, dict)
    ]
    warnings = [
        workspace_enrich_readiness_issue(workspace, item)
        for item in [*run_warnings, *resource_warnings, *topology_gaps]
        if isinstance(item, dict)
    ]
    gate_blockers = [workspace_enrich_readiness_issue(workspace, item) for item in blocked_checks[:6] if isinstance(item, dict)]
    force_run["blockers"] = [workspace_enrich_readiness_issue(workspace, item) for item in force_run.get("blockers", []) if isinstance(item, dict)]
    force_run["warnings"] = [workspace_enrich_readiness_issue(workspace, item) for item in force_run.get("warnings", []) if isinstance(item, dict)]
    return {
        "status": status,
        "summary": f"{ready_count}/{len(steps)} 项准备完成 · {len(blockers)} 阻塞 · {active_count} 活跃 · {failed_count} 失败",
        "steps": steps,
        "gate": {
            "status": gate_status,
            "title": gate_title,
            "detail": gate_detail,
            "action": gate_action,
            "blockers": gate_blockers,
        },
        "job_state": {
            "active_count": active_count,
            "queued_count": queued_count,
            "running_count": running_count,
            "failed_count": failed_count,
            "done_count": done_count,
            "discovery_run_count": discovery_run_count,
            "full_run_node_count": run_node_count,
            "last_job_id": str(execution.get("last_job_id") or "").strip(),
            "last_job_status": str(execution.get("last_job_status") or "").strip(),
        },
        "force_run": force_run,
        "next_action": advance,
        "blockers": blockers[:8],
        "warnings": warnings[:8],
    }


def workspace_playbook_step(
    step_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    button_action: str = "",
    node_id: str = "",
    server_id: str = "",
    phase: str = "",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": str(step_id or "").strip(),
        "label": str(label or "").strip(),
        "status": normalized,
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "action": str(action or "").strip(),
        "button_action": str(button_action or "").strip(),
        "node_id": str(node_id or "").strip(),
        "server_id": str(server_id or "").strip(),
        "phase": str(phase or "").strip(),
        "metrics": metrics or {},
    }


def derive_workspace_automation_playbook(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    advance: dict[str, Any],
    execution_readiness: dict[str, Any],
    resource_orchestration: dict[str, Any],
    reproduction_manifest: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    readiness_steps = {
        str(step.get("id") or "").strip(): step
        for step in (execution_readiness.get("steps") if isinstance(execution_readiness.get("steps"), list) else [])
        if isinstance(step, dict) and str(step.get("id") or "").strip()
    }
    manifest_items = {
        str(item.get("id") or "").strip(): item
        for item in (reproduction_manifest.get("items") if isinstance(reproduction_manifest.get("items"), list) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    job_state = execution_readiness.get("job_state") if isinstance(execution_readiness.get("job_state"), dict) else {}
    gate = execution_readiness.get("gate") if isinstance(execution_readiness.get("gate"), dict) else {}
    bundle = reproduction_manifest.get("execution_bundle") if isinstance(reproduction_manifest.get("execution_bundle"), dict) else {}
    scheduler = resource_orchestration.get("scheduler") if isinstance(resource_orchestration.get("scheduler"), dict) else {}
    selected_resource = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    intent = reproduction_manifest.get("intent") if isinstance(reproduction_manifest.get("intent"), dict) else {}
    report_actions = report.get("next_actions") if isinstance(report.get("next_actions"), list) else []
    active_count = safe_int(job_state.get("active_count"), 0)
    failed_count = safe_int(job_state.get("failed_count"), 0)
    discovery_run_count = safe_int(job_state.get("discovery_run_count"), 0)
    evidence_payload = bundle.get("evidence") if isinstance(bundle.get("evidence"), dict) else {}
    evidence_count = safe_int(evidence_payload.get("total_count"), 0)
    last_job_id = str(job_state.get("last_job_id") or execution.get("last_job_id") or "").strip()
    run_node_id = str((manifest_items.get("run") or {}).get("node_id") or bundle.get("next_action", {}).get("node_id") or "").strip() if isinstance(bundle.get("next_action"), dict) else str((manifest_items.get("run") or {}).get("node_id") or "").strip()

    safe_discovery = readiness_steps.get("safe_discovery", {})
    backfill = readiness_steps.get("defaults_evidence", {})
    resources = readiness_steps.get("resource_binding", {})
    hard_gate = readiness_steps.get("hard_gate", {})
    full_run = readiness_steps.get("full_run", {})
    collect = readiness_steps.get("collect_report", {})

    steps = [
        workspace_playbook_step(
            "observe",
            "观察/复查",
            "running" if active_count else "failed" if failed_count else "done",
            "当前任务未结束" if active_count else "失败任务待复查" if failed_count else "没有未处理任务",
            f"{active_count} 活跃 · {failed_count} 失败 · 最近任务 {last_job_id or '无'}",
            "打开最近输出，确认任务状态。" if active_count or failed_count else "可以进入自动发现或执行准备。",
            button_action="open-last-workspace-log" if last_job_id and (active_count or failed_count) else "advance-workspace-automation",
            phase="observe",
            metrics={"active": active_count, "failed": failed_count},
        ),
        workspace_playbook_step(
            "discover",
            "安全发现",
            str(safe_discovery.get("status") or ("done" if discovery_run_count else "ready")),
            str(safe_discovery.get("title") or ("已有发现链记录" if discovery_run_count else "提交安全发现")),
            str(safe_discovery.get("detail") or f"{discovery_run_count} 次发现 · {evidence_count} 条证据"),
            str(safe_discovery.get("action") or "先收集源码、路径、数据、环境、GPU 和产物入口证据。"),
            button_action="run-workspace-discovery" if not discovery_run_count else "advance-workspace-automation",
            phase="discover",
            metrics={"discovery_runs": discovery_run_count, "evidence": evidence_count},
        ),
        workspace_playbook_step(
            "backfill",
            "证据回填",
            str(backfill.get("status") or ("ready" if evidence_count else "draft")),
            str(backfill.get("title") or ("发现证据可回填" if evidence_count else "等待发现证据")),
            str(backfill.get("detail") or f"{evidence_count} 条证据会进入路径、数据、环境、GPU、产物配置。"),
            str(backfill.get("action") or "把发现证据写回节点配置，后续执行包使用这些默认值。"),
            button_action="apply-workspace-automation" if evidence_count else "run-workspace-discovery",
            phase="prepare",
            metrics={"evidence": evidence_count},
        ),
        workspace_playbook_step(
            "schedule",
            "资源调度",
            str(resources.get("status") or resource_orchestration.get("status") or "draft"),
            str(resources.get("title") or resource_orchestration.get("summary") or "等待资源调度"),
            str(resources.get("detail") or scheduler.get("summary") or "根据 GPU、主机资源和快照新鲜度选择执行目标。"),
            str(resources.get("action") or scheduler.get("next_action") or "刷新资源或调整 server/GPU 策略。"),
            button_action="refresh-workspace-resource-server" if str(selected_resource.get("server_id") or "").strip() else "refresh-workspace-resources",
            server_id=str(selected_resource.get("server_id") or "").strip(),
            phase="schedule",
            metrics={
                "candidate_count": safe_int(scheduler.get("candidate_count"), 0),
                "ready_count": safe_int(scheduler.get("ready_count"), 0),
                "selected_score": safe_int(selected_resource.get("score"), 0),
            },
        ),
        workspace_playbook_step(
            "gate",
            "门禁确认",
            str(hard_gate.get("status") or gate.get("status") or "draft"),
            str(hard_gate.get("title") or gate.get("title") or "等待门禁"),
            str(hard_gate.get("detail") or gate.get("detail") or "确认 Starter Chain、Agent、Tool、运行命令和资源绑定。"),
            str(hard_gate.get("action") or gate.get("action") or "处理阻塞后再继续自动推进。"),
            button_action="switch-workspace-manage" if str(gate.get("status") or hard_gate.get("status") or "") in {"blocked", "failed"} else "advance-workspace-automation",
            phase="gate",
            metrics={"blockers": len(execution_readiness.get("blockers") if isinstance(execution_readiness.get("blockers"), list) else [])},
        ),
        workspace_playbook_step(
            "execute",
            "提交执行包",
            str(full_run.get("status") or bundle.get("status") or "draft"),
            str(full_run.get("title") or ("执行包可提交" if bundle.get("ready_to_execute") else "执行包未就绪")),
            str(full_run.get("detail") or bundle.get("next_action", {}).get("detail") or "按 checkout/setup/run/collect/report 顺序提交。") if isinstance(bundle.get("next_action"), dict) else str(full_run.get("detail") or "按 checkout/setup/run/collect/report 顺序提交。"),
            str(full_run.get("action") or bundle.get("next_action", {}).get("detail") or "提交完整执行链。") if isinstance(bundle.get("next_action"), dict) else str(full_run.get("action") or "提交完整执行链。"),
            button_action="run-selected-workspace" if bundle.get("ready_to_execute") else "advance-workspace-automation",
            node_id=run_node_id,
            phase="execute",
            metrics={"ready_to_execute": bool(bundle.get("ready_to_execute")), "missing": len(bundle.get("missing") if isinstance(bundle.get("missing"), list) else [])},
        ),
        workspace_playbook_step(
            "collect",
            "产物/报告",
            str(collect.get("status") or report.get("status") or "draft"),
            str(collect.get("title") or report.get("headline") or "等待产物回收"),
            str(collect.get("detail") or report.get("summary") or "收集 logs、checkpoints、metrics、复跑命令和报告。"),
            str(collect.get("action") or (report_actions[0].get("action") if report_actions and isinstance(report_actions[0], dict) else "整理复现/部署报告。")),
            button_action="advance-workspace-automation",
            phase="report",
            metrics={"report_actions": len(report_actions)},
        ),
    ]

    current_step = next(
        (
            step for step in steps
            if str(step.get("status") or "") in {"running", "failed", "blocked", "warning", "draft"}
        ),
        steps[-1] if steps else {},
    )
    if str(advance.get("action") or "") == "watch":
        current_step = steps[0]
    elif str(advance.get("action") or "") == "discover":
        current_step = next((step for step in steps if step["id"] == "discover"), current_step)
    elif str(advance.get("action") or "") == "run":
        current_step = next((step for step in steps if step["id"] == "execute"), current_step)
    elif str(advance.get("action") or "") == "blocked":
        current_step = next((step for step in steps if step["id"] == "gate"), current_step)

    ready_count = sum(1 for step in steps if str(step.get("status") or "") in {"ready", "done"})
    status = str(current_step.get("status") or execution_readiness.get("status") or "draft")
    return {
        "status": status,
        "mode": str(intent.get("mode") or "reproduce").strip() or "reproduce",
        "label": str(intent.get("label") or "自动复现/部署").strip(),
        "summary": f"{ready_count}/{len(steps)} 步闭环 · 当前：{str(current_step.get('label') or '等待')}",
        "current_step_id": str(current_step.get("id") or "").strip(),
        "current_action": {
            "label": str(current_step.get("label") or advance.get("title") or "自动推进").strip(),
            "action": str(current_step.get("button_action") or "advance-workspace-automation").strip(),
            "title": str(current_step.get("title") or advance.get("title") or "").strip(),
            "detail": str(current_step.get("detail") or advance.get("reason") or "").strip(),
            "node_id": str(current_step.get("node_id") or "").strip(),
            "server_id": str(current_step.get("server_id") or "").strip(),
        },
        "steps": steps,
    }


def derive_workspace_automation_state(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    jobs_counts = execution.get("counts") if isinstance(execution.get("counts"), dict) else {}
    source_texts = [
        str(source.get("repo_url") or "").strip(),
        str(source.get("paper_url") or "").strip(),
        str(source.get("idea_text") or "").strip(),
        str(workspace.get("brief") or "").strip(),
        str(inputs.get("goal_text") or "").strip(),
    ]
    repo_count = len(inputs.get("repo_urls") if isinstance(inputs.get("repo_urls"), list) else [])
    paper_count = len(inputs.get("paper_urls") if isinstance(inputs.get("paper_urls"), list) else [])
    reference_count = len(inputs.get("references") if isinstance(inputs.get("references"), list) else [])
    context_count = len(inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])
    has_source = any(source_texts) or repo_count or paper_count or reference_count or context_count

    checks: list[dict[str, Any]] = [
        workspace_automation_check(
            "source",
            "目标输入",
            "ready" if has_source else "draft",
            "输入已绑定" if has_source else "缺少复现目标",
            f"{repo_count} repo · {paper_count} paper · {reference_count} 参考 · {context_count} 上下文",
            "补目标、repo、论文、数据路径或约束，让系统能推导 Starter Chain。",
        )
    ]

    required_kinds = ["path.resolve", "dataset.find", "env.infer", "gpu.allocate", "run.command", "artifact.collect"]
    missing_kinds = [kind for kind in required_kinds if not workspace_has_node_kind(workspace, kind)]
    checks.append(
        workspace_automation_check(
            "starter_chain",
            "节点链",
            "ready" if not missing_kinds else "blocked",
            f"{len(nodes)} 个节点" if not missing_kinds else "Starter Chain 不完整",
            "已覆盖路径、数据、环境、GPU、运行、产物闭环。" if not missing_kinds else "缺少 " + ", ".join(missing_kinds),
            "回配置中心恢复默认链或补齐缺失节点。",
        )
    )

    missing_handlers = 0
    executable_nodes = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            continue
        executable_nodes += 1
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        if str(handler.get("mode") or "agent").strip() != "human" and not str(handler.get("agent_id") or "").strip():
            missing_handlers += 1
    checks.append(
        workspace_automation_check(
            "agents",
            "Agent 归属",
            "ready" if executable_nodes and not missing_handlers else "blocked" if missing_handlers else "warning",
            f"{executable_nodes} 个可执行节点已分层" if not missing_handlers else f"{missing_handlers} 个节点缺 Agent",
            "节点已经挂到对应 Agent/Tool 职责。" if not missing_handlers else "没有 Agent 的节点无法形成可解释交接。",
            "在配置中心把规划、仓库、数据、环境、GPU、运行、报告 Agent 绑定到节点。",
        )
    )

    workspace_dir = str(workspace.get("workspace_dir") or "").strip()
    path_node = workspace_execution_node_by_kind(execution, "path.resolve")
    path_artifacts = path_node.get("artifacts") if isinstance(path_node.get("artifacts"), list) else []
    found_paths = [item for item in path_artifacts if isinstance(item, dict) and str(item.get("status") or "") == "found"]
    checks.append(
        workspace_automation_check(
            "paths",
            "路径解析",
            "ready" if workspace_dir or found_paths else "warning",
            "工作目录已设置" if workspace_dir else "路径等待解析",
            workspace_dir or (str(found_paths[0].get("resolved_path") or found_paths[0].get("path") or "") if found_paths else "还没有 workspace_dir / data_roots / output_roots。"),
            "补工作目录、数据根目录、输出目录；运行 path.resolve 后会回填路径快照。",
            node_kind="path.resolve",
        )
    )

    dataset_node = workspace_execution_node_by_kind(execution, "dataset.find")
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    dataset_artifacts = dataset_node.get("artifacts") if isinstance(dataset_node.get("artifacts"), list) else []
    dataset_hits = [
        item for item in dataset_artifacts
        if isinstance(item, dict) and str(item.get("label") or "") in {"候选数据集", "候选数据根", "数据根目录", "数据集线索"} and str(item.get("status") or "") in {"found", "planned"}
    ]
    dataset_hints = workspace_config_values(dataset_config.get("dataset_hints")) + workspace_config_values(dataset_config.get("data_roots"))
    checks.append(
        workspace_automation_check(
            "dataset",
            "数据集",
            "ready" if dataset_hits or dataset_hints or reference_count else "warning",
            "数据线索已出现" if dataset_hits or dataset_hints or reference_count else "缺数据集线索",
            f"{len(dataset_hits)} 个候选 · {len(dataset_hints)} 条配置线索 · {reference_count} 条参考",
            "补数据集名称、下载页、本地数据根，或运行 dataset.find 自动扫描候选。",
            node_kind="dataset.find",
        )
    )

    env_node = workspace_execution_node_by_kind(execution, "env.infer")
    env_config = workspace_node_config_by_kind(workspace, "env.prepare")
    env_resources = env_node.get("resources") if isinstance(env_node.get("resources"), dict) else {}
    workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
    env_ready = bool(
        str(workspace_env.get("name") or "").strip()
        or str(env_config.get("setup_command") or "").strip()
        or env_resources.get("setup_suggestion")
        or env_resources.get("found_manifests")
    )
    checks.append(
        workspace_automation_check(
            "env",
            "环境推断",
            "ready" if env_ready else "warning",
            "环境入口已具备" if env_ready else "缺环境入口",
            str(env_resources.get("setup_suggestion") or workspace_env.get("name") or env_config.get("setup_command") or "还没有 env_name、setup_command 或 manifest 发现。"),
            "运行 env.infer 或补 requirements/environment/pyproject 对应的 setup 命令。",
            node_kind="env.infer",
        )
    )

    run_config = workspace_node_config_by_kind(workspace, "run.command")
    gpu_node = workspace_execution_node_by_kind(execution, "gpu.allocate")
    gpu_resources = gpu_node.get("resources") if isinstance(gpu_node.get("resources"), dict) else {}
    run_gpu_policy = str(run_config.get("gpu_policy") or gpu_resources.get("gpu_policy") or "auto").strip().lower()
    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]
    all_gpus = [
        gpu for status in online_statuses
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else [])
        if isinstance(gpu, dict)
    ]
    idle_gpus = [gpu for gpu in all_gpus if str(gpu.get("state") or "") == "idle"]
    cpu_mode = run_gpu_policy in {"cpu", "none", "no_gpu"}
    checks.append(
        workspace_automation_check(
            "gpu",
            "GPU 调度",
            "ready" if cpu_mode or idle_gpus else "warning" if online_statuses or all_gpus else "blocked",
            "资源策略可执行" if cpu_mode or idle_gpus else "GPU 快照不足",
            "CPU/无 GPU 模式" if cpu_mode else f"{len(online_statuses)} 台在线 · {len(idle_gpus)}/{len(all_gpus)} 张空闲 GPU",
            "刷新监控或在 gpu.allocate / run.command 设置 server_id、gpu_policy、min_free_memory_gib。",
            node_kind="gpu.allocate",
        )
    )

    run_command = str(run_config.get("run_command") or "").strip()
    checks.append(
        workspace_automation_check(
            "run",
            "运行命令",
            "ready" if run_command else "blocked",
            "运行命令已设置" if run_command else "缺 run command",
            compact_workspace_command(run_command) if run_command else "没有可提交的训练、推理、部署或 smoke test 命令。",
            "补 run.command 的命令，或者让 Agent 从 README/脚本中推断。",
            node_kind="run.command",
        )
    )

    artifact_node = workspace_execution_node_by_kind(execution, "artifact.collect")
    artifact_config = workspace_node_config_by_kind(workspace, "artifact.collect")
    artifact_artifacts = artifact_node.get("artifacts") if isinstance(artifact_node.get("artifacts"), list) else []
    artifact_paths = workspace_config_values(artifact_config.get("artifact_paths")) + workspace_config_values(artifact_config.get("metric_paths"))
    checks.append(
        workspace_automation_check(
            "artifact",
            "产物收集",
            "ready" if artifact_paths or artifact_artifacts else "warning",
            "产物入口已设置" if artifact_paths or artifact_artifacts else "缺产物路径",
            f"{len(artifact_paths)} 条配置路径 · {len(artifact_artifacts)} 条运行快照",
            "补 runs/outputs/checkpoints/logs/metrics 路径，运行 artifact.collect 后收集报告证据。",
            node_kind="artifact.collect",
        )
    )

    status_counts: dict[str, int] = {}
    for check in checks:
        status = str(check.get("status") or "warning")
        status_counts[status] = status_counts.get(status, 0) + 1
    if jobs_counts.get("failed"):
        overall = "failed"
    elif jobs_counts.get("running") or jobs_counts.get("queued"):
        overall = "running"
    elif status_counts.get("blocked"):
        overall = "blocked"
    elif status_counts.get("warning") or status_counts.get("draft"):
        overall = "warning"
    elif jobs_counts.get("done"):
        overall = "done"
    else:
        overall = "ready"

    weighted = sum(max(workspace_status_priority(str(check.get("status") or "")), 0) for check in checks)
    score = round((weighted / max(len(checks) * workspace_status_priority("ready"), 1)) * 100)
    evidence = derive_workspace_automation_evidence(execution)
    dataset_discovery = derive_workspace_dataset_discovery_plan(workspace, execution, evidence)
    run_plan = derive_workspace_run_plan(workspace, execution, checks)
    agent_topology = derive_workspace_agent_topology(workspace, run_plan)
    resource_orchestration = derive_workspace_resource_orchestration(
        workspace,
        execution,
        statuses,
        checks,
        evidence,
        run_plan,
    )
    workflow_contract = derive_workspace_workflow_contract(
        workspace,
        execution,
        evidence,
        resource_orchestration,
        run_plan,
        agent_topology,
    )
    orchestration_contract = derive_workspace_orchestration_contract(agent_topology, workflow_contract)
    execution_context = derive_workspace_execution_context(workspace, execution, workflow_contract)
    reproduction_manifest = derive_workspace_reproduction_manifest(
        workspace,
        execution,
        checks,
        evidence,
        run_plan,
        resource_orchestration,
        dataset_discovery,
        execution_context,
    )
    report = derive_workspace_automation_report(workspace, execution, checks, evidence, run_plan, status_counts)
    advance = derive_workspace_automation_advance_hint(execution, checks)
    evidence_backfill = derive_workspace_evidence_backfill_plan(workspace, execution, resource_orchestration)
    execution_readiness = derive_workspace_execution_readiness(
        workspace,
        execution,
        checks,
        evidence,
        run_plan,
        advance,
        agent_topology,
        resource_orchestration,
    )
    playbook = derive_workspace_automation_playbook(
        workspace,
        execution,
        advance,
        execution_readiness,
        resource_orchestration,
        reproduction_manifest,
        report,
    )
    preflight = derive_workspace_preflight(
        workspace,
        execution,
        checks,
        run_plan,
        dataset_discovery,
        resource_orchestration,
        agent_topology,
        reproduction_manifest,
        execution_readiness,
        report,
    )
    next_check = next(
        (
            check for check in checks
            if str(check.get("status") or "") in {"failed", "blocked", "warning", "draft"}
        ),
        checks[-1] if checks else {},
    )
    return {
        "status": overall,
        "score": max(0, min(score, 100)),
        "counts": status_counts,
        "checks": checks,
        "evidence": evidence,
        "evidence_backfill": evidence_backfill,
        "run_plan": run_plan,
        "workflow_contract": workflow_contract,
        "orchestration_contract": orchestration_contract,
        "execution_context": execution_context,
        "dataset_discovery": dataset_discovery,
        "reproduction_manifest": reproduction_manifest,
        "agent_topology": agent_topology,
        "resource_orchestration": resource_orchestration,
        "execution_readiness": execution_readiness,
        "playbook": playbook,
        "preflight": preflight,
        "report": report,
        "advance": advance,
        "missing": [check for check in checks if str(check.get("status") or "") in {"blocked", "warning", "draft"}],
        "next_action": next_check,
        "summary": f"{status_counts.get('ready', 0) + status_counts.get('done', 0)} 项就绪 · {status_counts.get('warning', 0)} 项提示 · {status_counts.get('blocked', 0)} 项阻塞",
    }


def workspace_workflow_blocking_checks(automation: dict[str, Any]) -> list[dict[str, Any]]:
    hard_gate_ids = {"starter_chain", "agents", "run"}
    checks = automation.get("checks") if isinstance(automation.get("checks"), list) else []
    return [
        check for check in checks
        if isinstance(check, dict)
        and str(check.get("id") or "") in hard_gate_ids
        and str(check.get("status") or "") in {"blocked", "failed"}
    ]


def workspace_readiness_message(blocked_checks: list[dict[str, Any]]) -> str:
    labels = [
        str(check.get("label") or check.get("title") or check.get("id") or "").strip()
        for check in blocked_checks
        if isinstance(check, dict)
    ]
    labels = [label for label in labels if label]
    if not labels:
        return "工作流运行前检查未通过"
    return "工作流运行前检查未通过：" + "、".join(labels[:6])


def workspace_advance_decision(
    action: str,
    title: str,
    reason: str,
    next_action: str,
    *,
    status: str = "ready",
) -> dict[str, str]:
    return {
        "action": str(action or "").strip(),
        "status": str(status or "ready").strip() or "ready",
        "title": str(title or "").strip(),
        "reason": str(reason or "").strip(),
        "next_action": str(next_action or "").strip(),
    }


def workspace_path_like_values(workspace: dict[str, Any]) -> list[str]:
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    raw_values: list[Any] = []
    for key in ("references", "context_blocks"):
        values = inputs.get(key)
        if isinstance(values, list):
            raw_values.extend(values)
    raw_values.extend(workspace.get("references") if isinstance(workspace.get("references"), list) else [])
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = str(raw or "").strip()
        if not text or text.startswith(("http://", "https://")):
            continue
        for token in text.replace(",", "\n").splitlines():
            value = token.strip()
            if not value:
                continue
            if value.startswith(("~", "/", "./", "../")) or ":\\" in value:
                if value not in seen:
                    seen.add(value)
                    candidates.append(value)
    return candidates


def workspace_project_path_score(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    markers = {
        ".git": 3,
        "README.md": 2,
        "README.rst": 2,
        "pyproject.toml": 3,
        "requirements.txt": 3,
        "environment.yml": 3,
        "conda.yml": 3,
        "setup.py": 3,
        "train.py": 2,
        "main.py": 2,
        "tests": 1,
    }
    score = 0
    for marker, weight in markers.items():
        if (path / marker).exists():
            score += weight
    return score


def workspace_default_name_seed(workspace: dict[str, Any]) -> str:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    repo_name = repo_name_from_url(str(source.get("repo_url") or ""))
    if repo_name:
        return repo_name
    for value in (workspace.get("name"), workspace.get("brief"), workspace.get("template_name"), workspace.get("id")):
        text = str(value or "").strip()
        if text:
            return text
    return "workspace"


def infer_workspace_dir_from_inputs(workspace: dict[str, Any]) -> str:
    existing = str(workspace.get("workspace_dir") or "").strip()
    if existing:
        return existing
    best_path = ""
    best_score = 0
    for value in workspace_path_like_values(workspace):
        path = Path(value).expanduser()
        score = workspace_project_path_score(path)
        if score > best_score:
            best_score = score
            best_path = str(path)
    if best_path:
        return best_path
    return str((DATA_DIR / "workspaces" / safe_id(workspace_default_name_seed(workspace))).resolve())


def infer_workspace_data_roots(workspace: dict[str, Any], workspace_dir: str = "") -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        text = str(value or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        roots.append(text)

    workspace_path = Path(workspace_dir).expanduser() if workspace_dir else None
    for value in workspace_path_like_values(workspace):
        path = Path(value).expanduser()
        if workspace_path and str(path) == str(workspace_path):
            continue
        if path.exists() and path.is_dir():
            add(str(path))
    if workspace_path:
        for local_name in ("data", "datasets"):
            candidate = workspace_path / local_name
            if candidate.exists():
                add(str(candidate))
    for default_root in ("/mnt/e/datasets", "/mnt/f/datasets", "/data", "data", "datasets"):
        path = Path(default_root).expanduser()
        if default_root.startswith("/") and not path.exists():
            continue
        add(default_root)
    return roots


def workspace_dataset_value_kind(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lower = text.lower()
    if lower.startswith(("http://", "https://", "doi:", "arxiv:", "hf://", "kaggle:")):
        return "source"
    if text.startswith(("~", "/", "./", "../")) or ":\\" in text:
        return "path"
    if any(token in lower for token in ("dataset", "数据集", "benchmark", "imagenet", "coco", "kaggle", "huggingface")):
        return "query"
    return "query"


def append_unique_text(target: list[str], value: Any, *, limit: int = 12) -> None:
    text = compact_workspace_command(str(value or "").strip(), limit=180)
    if not text or text in target or len(target) >= limit:
        return
    target.append(text)


def derive_workspace_dataset_discovery_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
    inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
    dataset_config = workspace_node_config_by_kind(workspace, "dataset.find")
    path_config = workspace_node_config_by_kind(workspace, "path.resolve")
    nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
    dataset_node_id = next(
        (
            str(node.get("id") or "").strip()
            for node in nodes
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == "dataset.find"
        ),
        "",
    )

    queries: list[str] = []
    local_roots: list[str] = []
    source_refs: list[str] = []
    hints: list[str] = []
    expected_layout = str(dataset_config.get("expected_layout") or "").strip()

    for value in workspace_config_values(dataset_config.get("query")):
        append_unique_text(queries, value)
    for value in workspace_config_values(dataset_config.get("dataset_hints")):
        kind = workspace_dataset_value_kind(value)
        append_unique_text(hints, value)
        if kind == "path":
            append_unique_text(local_roots, value)
        elif kind == "source":
            append_unique_text(source_refs, value)
        else:
            append_unique_text(queries, value)
    for value in workspace_config_values(path_config.get("data_roots")) + workspace_config_values(dataset_config.get("data_roots")):
        append_unique_text(local_roots, value)

    repo_url = str(source.get("repo_url") or "").strip()
    paper_url = str(source.get("paper_url") or "").strip()
    if repo_url:
        append_unique_text(source_refs, repo_url)
        repo_name = repo_name_from_url(repo_url)
        if repo_name:
            append_unique_text(queries, f"{repo_name} dataset")
    if paper_url:
        append_unique_text(source_refs, paper_url)
        append_unique_text(queries, paper_url)

    for value in parse_line_list(inputs.get("paper_urls", [])):
        append_unique_text(source_refs, value)
        append_unique_text(queries, value)
    for value in parse_line_list(inputs.get("repo_urls", [])):
        append_unique_text(source_refs, value)
        repo_name = repo_name_from_url(value)
        append_unique_text(queries, f"{repo_name or value} dataset")
    for value in parse_line_list(inputs.get("references", [])) + parse_line_list(workspace.get("references", [])):
        kind = workspace_dataset_value_kind(value)
        append_unique_text(hints, value)
        if kind == "path":
            append_unique_text(local_roots, value)
        elif kind == "source":
            append_unique_text(source_refs, value)
        else:
            append_unique_text(queries, value)
    for value in parse_line_list(inputs.get("context_blocks", [])):
        lowered = value.lower()
        if any(token in lowered for token in ("dataset", "数据", "benchmark", "kaggle", "huggingface", "imagenet", "coco")):
            append_unique_text(queries, value)
    for value in (
        inputs.get("goal_text"),
        source.get("idea_text"),
        workspace.get("brief"),
        workspace.get("name"),
    ):
        text = str(value or "").strip()
        if text and (not queries or any(token in text.lower() for token in ("dataset", "数据", "benchmark", "复现", "baseline"))):
            append_unique_text(queries, text)

    inferred_roots = infer_workspace_data_roots(workspace, str(workspace.get("workspace_dir") or "").strip())
    for value in inferred_roots:
        append_unique_text(local_roots, value)

    evidence_group = workspace_evidence_group(evidence or [], "dataset")
    evidence_items = evidence_group.get("items") if isinstance(evidence_group.get("items"), list) else []
    found_datasets = [
        str(item.get("value") or "").strip()
        for item in evidence_items
        if isinstance(item, dict)
        and str(item.get("label") or "") in {"候选数据集", "数据集线索"}
        and str(item.get("value") or "").strip()
    ]
    for value in found_datasets:
        append_unique_text(hints, value)

    if not dataset_node_id:
        status = "blocked"
    elif found_datasets:
        status = "ready"
    elif queries or local_roots or source_refs or hints:
        status = "ready"
    else:
        status = "warning"

    actions: list[dict[str, Any]] = []
    if local_roots:
        actions.append(
            {
                "id": "scan_local_roots",
                "label": "扫描本地数据根",
                "status": "ready",
                "detail": f"扫描 {len(local_roots)} 个候选根目录，匹配查询词和目录名。",
            }
        )
    if queries or source_refs:
        actions.append(
            {
                "id": "derive_queries",
                "label": "派生数据集查询",
                "status": "ready" if queries else "warning",
                "detail": f"{len(queries)} 个查询词 · {len(source_refs)} 个资料入口。",
            }
        )
    actions.append(
        {
            "id": "verify_layout",
            "label": "验证数据结构",
            "status": "ready" if found_datasets or expected_layout else "warning",
            "detail": expected_layout or "确认 train/val、images/annotations、metadata 或项目 README 要求。",
        }
    )

    if not dataset_node_id:
        next_action = {
            "action": "switch-workspace-manage",
            "title": "补 dataset.find 节点",
            "detail": "当前链路缺少数据集发现节点，无法形成数据证据。",
            "node_id": "",
        }
    elif found_datasets:
        next_action = {
            "action": "apply-workspace-automation",
            "title": "回填数据集证据",
            "detail": "把发现的数据集路径或线索写回 dataset.find / path.resolve。",
            "node_id": dataset_node_id,
        }
    elif local_roots or queries:
        next_action = {
            "action": "run-workspace-discovery",
            "title": "运行数据集发现",
            "detail": "提交安全发现链，扫描本地数据根并输出 dataset_profile。",
            "node_id": dataset_node_id,
        }
    else:
        next_action = {
            "action": "select-execution-node",
            "title": "补数据集线索",
            "detail": "填写数据集名、下载页、本地路径或论文资料后再发现。",
            "node_id": dataset_node_id,
        }

    return {
        "status": status,
        "summary": f"{len(queries)} 个查询 · {len(local_roots)} 个本地根 · {len(source_refs)} 个资料入口 · {safe_int(evidence_group.get('count'), 0)} 条证据",
        "node_kind": "dataset.find",
        "node_id": dataset_node_id,
        "queries": queries[:12],
        "local_roots": local_roots[:12],
        "source_refs": source_refs[:12],
        "hints": hints[:12],
        "expected_layout": expected_layout,
        "found_datasets": found_datasets[:12],
        "evidence_count": safe_int(evidence_group.get("count"), 0),
        "actions": actions,
        "next_action": next_action,
    }


def workspace_dataset_discovery_bundle_command(plan: dict[str, Any]) -> str:
    queries = plan.get("queries") if isinstance(plan.get("queries"), list) else []
    local_roots = plan.get("local_roots") if isinstance(plan.get("local_roots"), list) else []
    source_refs = plan.get("source_refs") if isinstance(plan.get("source_refs"), list) else []
    expected_layout = str(plan.get("expected_layout") or "").strip()
    if not queries and not local_roots and not source_refs and not expected_layout:
        return ""
    return f"""python3 - <<'PY'
from pathlib import Path

queries = {json.dumps(queries[:12], ensure_ascii=False)}
local_roots = {json.dumps(local_roots[:12], ensure_ascii=False)}
source_refs = {json.dumps(source_refs[:12], ensure_ascii=False)}
expected_layout = {json.dumps(expected_layout, ensure_ascii=False)}

for query in queries:
    print("dataset_plan_query:", query)
for source in source_refs:
    print("dataset_source:", source)
if expected_layout:
    print("expected_layout:", expected_layout)
terms = [part.lower() for query in queries for part in query.replace("/", " ").replace("_", " ").replace("-", " ").split() if len(part) >= 3]
for raw in local_roots:
    path = Path(raw).expanduser()
    print(f"candidate_root: {{path}} exists={{path.exists()}}")
    if not path.exists() or not path.is_dir():
        continue
    matches = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        name = child.name.lower()
        if not terms or any(term in name for term in terms):
            matches.append(child)
        if len(matches) >= 12:
            break
    for child in matches:
        kind = "dir" if child.is_dir() else "file"
        print(f"  match: {{child.name}} ({{kind}})")
PY"""


def infer_workspace_setup_command(workspace_dir: str) -> str:
    root = Path(workspace_dir).expanduser()
    if not workspace_dir or not root.exists():
        return ""
    for name in ("environment.yml", "conda.yml", "conda.yaml"):
        if (root / name).exists():
            return f"conda env update -f {name}"
    if (root / "requirements.txt").exists():
        return "pip install -r requirements.txt"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "pip install -e ."
    return ""


def infer_workspace_run_command(workspace_dir: str) -> str:
    root = Path(workspace_dir).expanduser()
    if not workspace_dir or not root.exists():
        return ""
    if (root / "pytest.ini").exists() or (root / "tests").exists():
        return "python -m pytest -q"
    if (root / "train.py").exists():
        return "python train.py --help"
    if (root / "main.py").exists():
        return "python main.py --help"
    if (root / "app.py").exists():
        return "python app.py"
    return ""


def infer_workspace_best_gpu(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_free = -1
    for status in statuses:
        if not isinstance(status, dict) or not status.get("online"):
            continue
        server_id = str(status.get("id") or "").strip()
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else []):
            if not isinstance(gpu, dict):
                continue
            free = safe_int(gpu.get("memory_free_mib"), 0)
            if str(gpu.get("state") or "") == "idle":
                free += 1_000_000
            if free <= best_free:
                continue
            best_free = free
            best = {
                "server_id": server_id,
                "gpu_index": str(gpu.get("index") if gpu.get("index") is not None else "auto"),
                "memory_free_mib": safe_int(gpu.get("memory_free_mib"), 0),
                "state": str(gpu.get("state") or ""),
            }
    return best


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def workspace_status_age_seconds(status: dict[str, Any], now_ts: float | None = None) -> int:
    collected_ts = parse_iso_timestamp(status.get("collected_at"))
    if collected_ts <= 0:
        return 0
    current = now_ts if now_ts is not None else time.time()
    return max(0, int(round(current - collected_ts)))


def workspace_host_resource_summary_for_scheduler(status: dict[str, Any]) -> dict[str, Any]:
    resources = status.get("host_resources") if isinstance(status.get("host_resources"), dict) else {}
    if not resources:
        return {
            "ok": False,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "load1": 0.0,
            "summary": "主机资源待采集",
        }
    if resources.get("ok") is False:
        return {
            "ok": False,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "load1": 0.0,
            "summary": str(resources.get("error") or "主机资源采集异常"),
        }
    cpu = resources.get("cpu") if isinstance(resources.get("cpu"), dict) else {}
    memory = resources.get("memory") if isinstance(resources.get("memory"), dict) else {}
    cpu_percent = safe_float(cpu.get("util_percent"), 0.0)
    memory_percent = safe_float(memory.get("used_percent"), 0.0)
    load1 = safe_float(cpu.get("load1"), 0.0)
    return {
        "ok": True,
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory_percent, 1),
        "load1": round(load1, 2),
        "summary": f"CPU {cpu_percent:.1f}% · 内存 {memory_percent:.1f}%",
    }


def workspace_scheduler_candidate_status(
    *,
    mode: str,
    gpu_state: str = "",
    memory_free_mib: int = 0,
    min_free_memory_mib: int = 0,
    host: dict[str, Any] | None = None,
) -> str:
    host = host or {}
    if mode == "cpu":
        if host.get("ok") is False:
            return "warning"
        if safe_float(host.get("cpu_percent"), 0.0) >= 92 or safe_float(host.get("memory_percent"), 0.0) >= 94:
            return "warning"
        return "ready"
    if min_free_memory_mib and memory_free_mib < min_free_memory_mib:
        return "blocked"
    if gpu_state == "idle":
        return "ready"
    return "warning"


def workspace_scheduler_score(
    *,
    mode: str,
    status_value: str,
    memory_free_mib: int = 0,
    gpu_state: str = "",
    gpu_util: int = 0,
    process_count: int = 0,
    host: dict[str, Any] | None = None,
    age_seconds: int = 0,
) -> int:
    host = host or {}
    score = 70.0 if mode == "cpu" else 45.0
    if mode == "gpu":
        score += min(memory_free_mib / 1024 * 1.8, 34)
        score += 18 if gpu_state == "idle" else -16
        score -= min(max(gpu_util, 0) / 2.5, 24)
        score -= min(max(process_count, 0) * 7, 21)
    score -= max(safe_float(host.get("cpu_percent"), 0.0) - 70, 0) * 0.35
    score -= max(safe_float(host.get("memory_percent"), 0.0) - 78, 0) * 0.45
    if host.get("ok") is False:
        score -= 7
    if age_seconds > 180:
        score -= min((age_seconds - 180) / 30, 18)
    if status_value == "blocked":
        score -= 45
    elif status_value == "warning":
        score -= 12
    return clamp_score(score)


def workspace_scheduler_reasons(
    *,
    mode: str,
    candidate_status: str,
    memory_free_mib: int = 0,
    min_free_memory_mib: int = 0,
    gpu_state: str = "",
    gpu_util: int = 0,
    process_count: int = 0,
    host: dict[str, Any] | None = None,
    age_seconds: int = 0,
) -> tuple[list[str], list[str]]:
    host = host or {}
    reasons: list[str] = []
    warnings: list[str] = []
    if mode == "cpu":
        reasons.append("CPU/无 GPU 模式")
    else:
        reasons.append(f"{memory_free_mib // 1024} GiB 显存空闲")
        reasons.append("GPU 空闲" if gpu_state == "idle" else f"GPU {gpu_state or '未知'}")
        if gpu_util:
            warnings.append(f"GPU util {gpu_util}%")
        if process_count:
            warnings.append(f"{process_count} 个 GPU 进程")
        if min_free_memory_mib and memory_free_mib < min_free_memory_mib:
            warnings.append(f"低于最小显存 {min_free_memory_mib // 1024} GiB")
    if host.get("summary"):
        reasons.append(str(host.get("summary")))
    if host.get("ok") is False:
        warnings.append(str(host.get("summary") or "主机资源异常"))
    if safe_float(host.get("cpu_percent"), 0.0) >= 90:
        warnings.append("主机 CPU 偏高")
    if safe_float(host.get("memory_percent"), 0.0) >= 90:
        warnings.append("主机内存偏高")
    if age_seconds > 180:
        warnings.append(f"快照 {age_seconds}s 前")
    if candidate_status == "ready" and not warnings:
        reasons.append("可作为执行包目标")
    return (compact_contract_items(reasons, limit=5), compact_contract_items(warnings, limit=5))


def derive_workspace_resource_scheduler(
    statuses: list[dict[str, Any]],
    *,
    gpu_policy: str = "auto",
    requested_server_id: str = "",
    requested_gpu_index: str = "",
    min_free_memory_gib: int = 0,
) -> dict[str, Any]:
    policy = str(gpu_policy or "auto").strip().lower() or "auto"
    cpu_mode = policy in {"cpu", "none", "no_gpu"}
    mode = "cpu" if cpu_mode else "gpu"
    min_free_memory_mib = max(safe_int(min_free_memory_gib, 0), 0) * 1024
    now_ts = time.time()
    candidates: list[dict[str, Any]] = []
    rejected_count = 0
    online_statuses = [item for item in statuses if isinstance(item, dict) and item.get("online")]

    for status in online_statuses:
        server_id = str(status.get("id") or "").strip()
        if requested_server_id and requested_server_id not in {"auto", server_id}:
            continue
        server_name = str(status.get("name") or server_id).strip()
        host = workspace_host_resource_summary_for_scheduler(status)
        age_seconds = workspace_status_age_seconds(status, now_ts)
        process_count_by_gpu: dict[str, int] = {}
        for process in (status.get("processes") if isinstance(status.get("processes"), list) else []):
            if not isinstance(process, dict):
                continue
            key = str(process.get("gpu_index") if process.get("gpu_index") is not None else "").strip()
            if key:
                process_count_by_gpu[key] = process_count_by_gpu.get(key, 0) + 1
        if cpu_mode:
            candidate_status = workspace_scheduler_candidate_status(mode="cpu", host=host)
            score = workspace_scheduler_score(mode="cpu", status_value=candidate_status, host=host, age_seconds=age_seconds)
            reasons, warnings = workspace_scheduler_reasons(
                mode="cpu",
                candidate_status=candidate_status,
                host=host,
                age_seconds=age_seconds,
            )
            candidates.append(
                {
                    "id": f"{server_id}:cpu",
                    "status": candidate_status,
                    "mode": "cpu",
                    "score": score,
                    "server_id": server_id,
                    "server_name": server_name,
                    "gpu_index": "cpu",
                    "gpu_name": "CPU",
                    "gpu_state": "cpu",
                    "memory_free_mib": 0,
                    "memory_total_mib": 0,
                    "gpu_util": 0,
                    "process_count": 0,
                    "host": host,
                    "snapshot_age_seconds": age_seconds,
                    "collected_at": str(status.get("collected_at") or "").strip(),
                    "reasons": reasons,
                    "warnings": warnings,
                }
            )
            continue
        for gpu in (status.get("gpus") if isinstance(status.get("gpus"), list) else []):
            if not isinstance(gpu, dict):
                continue
            gpu_index = str(gpu.get("index") if gpu.get("index") is not None else "auto")
            if requested_gpu_index and requested_gpu_index not in {"auto", gpu_index}:
                rejected_count += 1
                continue
            memory_free_mib = safe_int(gpu.get("memory_free_mib"), 0)
            gpu_state = str(gpu.get("state") or "").strip()
            gpu_util = safe_int(gpu.get("gpu_util"), 0)
            process_count = process_count_by_gpu.get(gpu_index, 0)
            candidate_status = workspace_scheduler_candidate_status(
                mode="gpu",
                gpu_state=gpu_state,
                memory_free_mib=memory_free_mib,
                min_free_memory_mib=min_free_memory_mib,
                host=host,
            )
            score = workspace_scheduler_score(
                mode="gpu",
                status_value=candidate_status,
                memory_free_mib=memory_free_mib,
                gpu_state=gpu_state,
                gpu_util=gpu_util,
                process_count=process_count,
                host=host,
                age_seconds=age_seconds,
            )
            reasons, warnings = workspace_scheduler_reasons(
                mode="gpu",
                candidate_status=candidate_status,
                memory_free_mib=memory_free_mib,
                min_free_memory_mib=min_free_memory_mib,
                gpu_state=gpu_state,
                gpu_util=gpu_util,
                process_count=process_count,
                host=host,
                age_seconds=age_seconds,
            )
            candidates.append(
                {
                    "id": f"{server_id}:{gpu_index}",
                    "status": candidate_status,
                    "mode": "gpu",
                    "score": score,
                    "server_id": server_id,
                    "server_name": server_name,
                    "gpu_index": gpu_index,
                    "gpu_name": str(gpu.get("name") or f"GPU {gpu_index}").strip(),
                    "gpu_state": gpu_state,
                    "memory_free_mib": memory_free_mib,
                    "memory_total_mib": safe_int(gpu.get("memory_total_mib"), 0),
                    "gpu_util": gpu_util,
                    "process_count": process_count,
                    "host": host,
                    "snapshot_age_seconds": age_seconds,
                    "collected_at": str(status.get("collected_at") or "").strip(),
                    "reasons": reasons,
                    "warnings": warnings,
                }
            )

    candidates.sort(
        key=lambda item: (
            workspace_status_priority(str(item.get("status") or "draft")),
            safe_int(item.get("score"), 0),
            safe_int(item.get("memory_free_mib"), 0),
        ),
        reverse=True,
    )
    selected = candidates[0] if candidates else {}
    ready_count = sum(1 for item in candidates if str(item.get("status") or "") == "ready")
    if not online_statuses:
        status = "blocked"
    elif selected and str(selected.get("status") or "") == "ready":
        status = "ready"
    elif candidates:
        status = "warning"
    else:
        status = "blocked"
    return {
        "status": status,
        "mode": mode,
        "policy": policy,
        "requested_server_id": requested_server_id or "auto",
        "requested_gpu_index": requested_gpu_index or ("cpu" if cpu_mode else "auto"),
        "min_free_memory_mib": min_free_memory_mib,
        "selected": copy.deepcopy(selected),
        "candidates": copy.deepcopy(candidates[:8]),
        "candidate_count": len(candidates),
        "ready_count": ready_count,
        "rejected_count": rejected_count,
        "summary": (
            f"{ready_count}/{len(candidates)} 个候选可用 · "
            f"{'CPU 模式' if cpu_mode else f'最小显存 {min_free_memory_mib // 1024} GiB'}"
        ),
        "next_action": "刷新单机或调整 gpu_policy/server_id/min_free_memory_gib" if status != "ready" else "调度目标可写入执行包",
    }


def workspace_scheduler_values_from_selection(scheduler: dict[str, Any]) -> dict[str, Any]:
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    if not selected:
        return {
            "server_id": "",
            "gpu_index": "",
            "gpu_policy": "",
            "min_free_memory_gib": "",
            "mode": str(scheduler.get("mode") or "").strip(),
            "status": str(scheduler.get("status") or "draft").strip(),
        }
    mode = str(selected.get("mode") or scheduler.get("mode") or "gpu").strip().lower()
    cpu_mode = mode == "cpu" or str(scheduler.get("policy") or "").strip().lower() in {"cpu", "none", "no_gpu"}
    policy = str(scheduler.get("policy") or ("cpu" if cpu_mode else "auto")).strip().lower() or ("cpu" if cpu_mode else "auto")
    server_id = str(selected.get("server_id") or "").strip()
    gpu_index = "none" if cpu_mode else str(selected.get("gpu_index") or "").strip()
    min_free_memory_gib = ""
    if not cpu_mode:
        requested_min_mib = safe_int(scheduler.get("min_free_memory_mib"), 0)
        if requested_min_mib > 0:
            min_free_memory_gib = str(max(requested_min_mib // 1024, 1))
        else:
            memory_free_mib = safe_int(selected.get("memory_free_mib"), 0)
            if memory_free_mib:
                min_free_memory_gib = str(max(memory_free_mib // 1024 - 2, 1))
    return {
        "server_id": server_id,
        "gpu_index": gpu_index,
        "gpu_policy": policy if cpu_mode else "auto",
        "min_free_memory_gib": min_free_memory_gib,
        "mode": "cpu" if cpu_mode else "gpu",
        "status": str(scheduler.get("status") or selected.get("status") or "draft").strip(),
        "score": safe_int(selected.get("score"), 0),
    }


def workspace_scheduler_values_from_candidate(
    candidate: dict[str, Any] | None,
    scheduler: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    scheduler = scheduler if isinstance(scheduler, dict) else {}
    server_id = str(candidate.get("server_id") or candidate.get("serverId") or "").strip()
    if not server_id:
        return {}
    raw_mode = str(candidate.get("mode") or "").strip().lower()
    raw_policy = str(candidate.get("gpu_policy") or candidate.get("policy") or scheduler.get("policy") or "").strip().lower()
    raw_gpu_index = str(
        candidate.get("gpu_index")
        if candidate.get("gpu_index") is not None
        else candidate.get("gpuIndex")
        if candidate.get("gpuIndex") is not None
        else ""
    ).strip()
    cpu_mode = (
        raw_mode in {"cpu", "none", "no_gpu"}
        or raw_policy in {"cpu", "none", "no_gpu"}
        or raw_gpu_index in {"cpu", "none", "no_gpu"}
    )
    policy = "cpu" if cpu_mode else (raw_policy if raw_policy not in {"cpu", "none", "no_gpu"} else "") or "auto"
    gpu_index = "none" if cpu_mode else raw_gpu_index or "auto"
    min_free_memory_gib = ""
    if not cpu_mode:
        requested_min_gib = safe_int(candidate.get("min_free_memory_gib") or candidate.get("minFreeMemoryGib"), 0)
        if requested_min_gib > 0:
            min_free_memory_gib = str(requested_min_gib)
        else:
            requested_min_mib = safe_int(candidate.get("min_free_memory_mib") or scheduler.get("min_free_memory_mib"), 0)
            if requested_min_mib > 0:
                min_free_memory_gib = str(max(requested_min_mib // 1024, 1))
            else:
                memory_free_mib = safe_int(candidate.get("memory_free_mib") or candidate.get("memoryFreeMib"), 0)
                if memory_free_mib:
                    min_free_memory_gib = str(max(memory_free_mib // 1024 - 2, 1))
    return {
        "server_id": server_id,
        "gpu_index": gpu_index,
        "gpu_policy": policy,
        "min_free_memory_gib": min_free_memory_gib,
        "mode": "cpu" if cpu_mode else "gpu",
        "status": str(candidate.get("status") or scheduler.get("status") or "draft").strip(),
        "score": safe_int(candidate.get("score"), 0),
    }


def derive_workspace_scheduler_values(
    workspace: dict[str, Any],
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    gpu_config = workspace_node_config_by_kind(workspace, "gpu.allocate")
    run_config = workspace_node_config_by_kind(workspace, "run.command")
    gpu_policy = str(run_config.get("gpu_policy") or gpu_config.get("gpu_policy") or "auto").strip().lower() or "auto"
    requested_server_id = str(run_config.get("server_id") or gpu_config.get("server_id") or "auto").strip() or "auto"
    requested_gpu_index = str(run_config.get("gpu_index") or gpu_config.get("gpu_index") or "").strip()
    min_free_memory_gib = safe_int(run_config.get("min_free_memory_gib") or gpu_config.get("min_free_memory_gib"), 0)
    scheduler = derive_workspace_resource_scheduler(
        statuses,
        gpu_policy=gpu_policy,
        requested_server_id=requested_server_id,
        requested_gpu_index=requested_gpu_index,
        min_free_memory_gib=min_free_memory_gib,
    )
    values = workspace_scheduler_values_from_selection(scheduler)
    values["scheduler"] = scheduler
    return values


def apply_workspace_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    if value in (None, ""):
        return
    if not force and str(config.get(key) or "").strip():
        return
    config[key] = value
    applied.append({"field": key, "label": label, "value": value})


def apply_workspace_scheduler_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    if value in (None, ""):
        return
    text_value = str(value).strip()
    current = str(config.get(key) or "").strip()
    replace_default_auto = key in {"server_id", "gpu_policy", "gpu_index"} and current == "auto" and text_value != "auto"
    if not force and current and not replace_default_auto:
        return
    if current == text_value:
        return
    config[key] = value
    applied.append({"field": key, "label": label, "value": value, "source": "scheduler"})


def workspace_mutable_node_config_by_kind(workspace: dict[str, Any], kind: str) -> dict[str, Any]:
    for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []):
        if not isinstance(node, dict) or str(node.get("kind") or "").strip() != kind:
            continue
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        node["config"] = config
        return config
    return {}


def apply_workspace_evidence_config_value(
    config: dict[str, Any],
    key: str,
    value: Any,
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    before = len(applied)
    apply_workspace_config_value(config, key, value, applied, label, force=force)
    for item in applied[before:]:
        item["source"] = "evidence"


def merge_workspace_evidence_config_values(
    config: dict[str, Any],
    key: str,
    values: list[str],
    applied: list[dict[str, Any]],
    label: str,
    *,
    force: bool = False,
) -> None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    if not cleaned:
        return

    current = [] if force else workspace_config_values(config.get(key))
    merged = list(current)
    changed_values: list[str] = []
    existing = set(current)
    for value in cleaned:
        if value in existing:
            continue
        existing.add(value)
        merged.append(value)
        changed_values.append(value)
    if not changed_values and not force:
        return
    new_value = "\n".join(cleaned if force else merged)
    if str(config.get(key) or "").strip() == new_value:
        return
    config[key] = new_value
    applied.append(
        {
            "field": key,
            "label": label,
            "value": "\n".join(changed_values or cleaned),
            "source": "evidence",
        }
    )


def workspace_discovery_evidence_values(execution: dict[str, Any]) -> dict[str, Any]:
    dataset_candidates: list[str] = []
    data_roots: list[str] = []
    output_roots: list[str] = []
    artifact_paths: list[str] = []
    metric_paths: list[str] = []
    found_manifests: list[str] = []
    setup_suggestion = ""
    run_suggestion = ""
    gpu_server_id = ""

    def append_unique(items: list[str], value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in items:
            items.append(text)

    for node in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        resources = node.get("resources") if isinstance(node.get("resources"), dict) else {}
        if kind in {"env.infer", "repo.inspect"}:
            setup_suggestion = str(resources.get("setup_suggestion") or setup_suggestion or "").strip()
            run_suggestion = str(resources.get("run_suggestion") or run_suggestion or "").strip()
            for manifest in (resources.get("found_manifests") if isinstance(resources.get("found_manifests"), list) else []):
                append_unique(found_manifests, manifest)
        elif kind == "run.command":
            run_suggestion = str(resources.get("run_suggestion") or run_suggestion or "").strip()
        elif kind == "gpu.allocate":
            server_id = str(resources.get("server_id") or "").strip()
            if server_id and server_id != "auto":
                gpu_server_id = server_id

        for artifact in (node.get("artifacts") if isinstance(node.get("artifacts"), list) else []):
            if not isinstance(artifact, dict) or str(artifact.get("source") or "").strip() != "log":
                continue
            label = str(artifact.get("label") or "").strip()
            status = str(artifact.get("status") or "").strip()
            value = str(artifact.get("resolved_path") or artifact.get("path") or "").strip()
            if not value:
                continue
            if label == "候选数据集" and status == "found":
                append_unique(dataset_candidates, value)
                parent = str(Path(value).expanduser().parent)
                append_unique(data_roots, parent)
            elif label in {"候选数据根", "数据根目录"} and status == "found":
                append_unique(data_roots, value)
            elif label == "输出目录":
                append_unique(output_roots, value)
                if status == "found":
                    append_unique(artifact_paths, value)
            elif label == "产物路径":
                append_unique(artifact_paths, value)
            elif label == "指标路径":
                append_unique(metric_paths, value)
            elif label == "环境清单" and status == "found":
                append_unique(found_manifests, artifact.get("path") or value)

    return {
        "dataset_candidates": dataset_candidates,
        "data_roots": data_roots,
        "output_roots": output_roots,
        "artifact_paths": artifact_paths,
        "metric_paths": metric_paths,
        "found_manifests": found_manifests,
        "setup_suggestion": setup_suggestion,
        "run_suggestion": run_suggestion,
        "gpu_server_id": gpu_server_id,
    }


def workspace_evidence_backfill_item(
    workspace: dict[str, Any],
    node_kind: str,
    field: str,
    label: str,
    values: list[str] | str,
    *,
    mode: str = "append",
) -> dict[str, Any]:
    config = workspace_node_config_by_kind(workspace, node_kind)
    candidate_values = (
        [str(value or "").strip() for value in values]
        if isinstance(values, list)
        else [str(values or "").strip()]
    )
    candidate_values = [value for value in candidate_values if value]
    current_values = workspace_config_values(config.get(field)) if isinstance(config, dict) else []
    current_text = str(config.get(field) or "").strip() if isinstance(config, dict) else ""
    existing = set(current_values)
    new_values = [value for value in candidate_values if value not in existing]
    if not config:
        status = "blocked"
        action = f"缺少 {node_kind} 节点，无法回填 {field}。"
    elif not candidate_values:
        status = "draft"
        action = "等待安全发现产生可用证据。"
    elif mode == "replace" and current_text and current_text != candidate_values[0]:
        status = "warning"
        action = "已有人工/模板值；自动回填默认不会覆盖，强制回填才会替换。"
    elif mode == "replace" and current_text == candidate_values[0]:
        status = "done"
        action = "证据已经写入该字段。"
    elif mode == "replace" and field in {"server_id", "gpu_policy", "gpu_index"} and current_text == "auto":
        status = "ready"
        action = "回填会替换默认自动值。"
    elif mode == "replace":
        status = "ready"
        action = "回填证据会写入当前空字段。"
    elif new_values:
        status = "ready"
        action = "回填证据会追加新值，不覆盖已有值。"
    else:
        status = "done"
        action = "候选证据已经存在于该字段。"
    return {
        "node_kind": node_kind,
        "field": field,
        "label": label,
        "status": status,
        "mode": mode,
        "current": "\n".join(current_values) if current_values else current_text,
        "value": "\n".join(new_values or candidate_values),
        "candidate_count": len(candidate_values),
        "new_count": len(new_values) if mode != "replace" else (0 if status == "done" else len(candidate_values)),
        "action": action,
    }


def derive_workspace_evidence_backfill_plan(
    workspace: dict[str, Any],
    execution: dict[str, Any],
    resource_orchestration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = workspace_discovery_evidence_values(execution)
    items = [
        workspace_evidence_backfill_item(workspace, "path.resolve", "data_roots", "发现数据根", values["data_roots"]),
        workspace_evidence_backfill_item(workspace, "path.resolve", "output_roots", "发现输出目录", values["output_roots"]),
        workspace_evidence_backfill_item(workspace, "dataset.find", "data_roots", "发现数据候选根", values["data_roots"]),
        workspace_evidence_backfill_item(workspace, "dataset.find", "dataset_hints", "发现数据集线索", values["dataset_candidates"]),
        workspace_evidence_backfill_item(workspace, "env.infer", "manifest_paths", "发现环境清单", values["found_manifests"]),
        workspace_evidence_backfill_item(workspace, "env.prepare", "setup_command", "发现环境安装命令", values["setup_suggestion"], mode="replace"),
        workspace_evidence_backfill_item(workspace, "run.command", "run_command", "发现运行命令", values["run_suggestion"], mode="replace"),
        workspace_evidence_backfill_item(workspace, "artifact.collect", "artifact_paths", "发现产物路径", values["artifact_paths"]),
        workspace_evidence_backfill_item(workspace, "artifact.collect", "metric_paths", "发现指标路径", values["metric_paths"]),
        workspace_evidence_backfill_item(workspace, "eval.report", "metric_paths", "发现报告指标路径", values["metric_paths"]),
    ]
    scheduler = (
        resource_orchestration.get("scheduler")
        if isinstance(resource_orchestration, dict) and isinstance(resource_orchestration.get("scheduler"), dict)
        else {}
    )
    scheduler_values = workspace_scheduler_values_from_selection(scheduler) if scheduler else {}
    scheduler_server_id = str(scheduler_values.get("server_id") or "").strip()
    scheduler_gpu_index = str(scheduler_values.get("gpu_index") or "").strip()
    scheduler_gpu_policy = str(scheduler_values.get("gpu_policy") or "").strip()
    scheduler_min_free = str(scheduler_values.get("min_free_memory_gib") or "").strip()
    if scheduler_server_id:
        scheduler_items = [
            ("gpu.allocate", "server_id", "调度目标服务器", scheduler_server_id),
            ("gpu.allocate", "gpu_policy", "调度 GPU 策略", scheduler_gpu_policy),
            ("gpu.allocate", "gpu_index", "调度 GPU 编号", scheduler_gpu_index),
            ("run.command", "server_id", "调度运行服务器", scheduler_server_id),
            ("run.command", "gpu_policy", "调度运行 GPU 策略", scheduler_gpu_policy),
            ("run.command", "gpu_index", "调度运行 GPU 编号", scheduler_gpu_index),
        ]
        if scheduler_min_free:
            scheduler_items.extend(
                [
                    ("gpu.allocate", "min_free_memory_gib", "调度最低空闲显存", scheduler_min_free),
                    ("run.command", "min_free_memory_gib", "调度最低空闲显存", scheduler_min_free),
                ]
            )
        items.extend(
            [
                workspace_evidence_backfill_item(workspace, node_kind, field, label, value, mode="replace")
                for node_kind, field, label, value in scheduler_items
                if str(value or "").strip()
            ]
        )
    gpu_server_id = str(values.get("gpu_server_id") or "").strip()
    if gpu_server_id and not scheduler_server_id:
        items.extend(
            [
                workspace_evidence_backfill_item(workspace, "gpu.allocate", "server_id", "发现调度服务器", gpu_server_id, mode="replace"),
                workspace_evidence_backfill_item(workspace, "gpu.allocate", "gpu_policy", "发现 GPU 策略", "auto", mode="replace"),
                workspace_evidence_backfill_item(workspace, "run.command", "server_id", "发现运行服务器", gpu_server_id, mode="replace"),
                workspace_evidence_backfill_item(workspace, "run.command", "gpu_policy", "发现 GPU 策略", "auto", mode="replace"),
            ]
        )
    ready_items = [item for item in items if str(item.get("status") or "") == "ready"]
    done_items = [item for item in items if str(item.get("status") or "") == "done"]
    blocked_items = [item for item in items if str(item.get("status") or "") == "blocked"]
    warning_items = [item for item in items if str(item.get("status") or "") == "warning"]
    if blocked_items:
        status = "blocked"
    elif ready_items:
        status = "ready"
    elif warning_items:
        status = "warning"
    elif done_items:
        status = "done"
    else:
        status = "draft"
    return {
        "status": status,
        "summary": f"{len(ready_items)} 项可回填 · {len(done_items)} 项已存在 · {len(warning_items)} 项需确认 · {len(blocked_items)} 项阻塞",
        "items": items,
        "ready_count": len(ready_items),
        "done_count": len(done_items),
        "warning_count": len(warning_items),
        "blocked_count": len(blocked_items),
        "next_action": ready_items[0] if ready_items else warning_items[0] if warning_items else blocked_items[0] if blocked_items else {},
    }


def apply_workspace_discovery_evidence_to_payload(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
    *,
    force: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    applied: list[dict[str, Any]] = []
    execution = derive_workspace_execution_state(updated, jobs)
    values = workspace_discovery_evidence_values(execution)
    dataset_candidates = values["dataset_candidates"]
    data_roots = values["data_roots"]
    output_roots = values["output_roots"]
    artifact_paths = values["artifact_paths"]
    metric_paths = values["metric_paths"]
    found_manifests = values["found_manifests"]
    setup_suggestion = values["setup_suggestion"]
    run_suggestion = values["run_suggestion"]
    gpu_server_id = values["gpu_server_id"]

    path_config = workspace_mutable_node_config_by_kind(updated, "path.resolve")
    if path_config:
        merge_workspace_evidence_config_values(path_config, "data_roots", data_roots, applied, "发现数据根", force=force)
        merge_workspace_evidence_config_values(path_config, "output_roots", output_roots, applied, "发现输出目录", force=force)

    dataset_config = workspace_mutable_node_config_by_kind(updated, "dataset.find")
    if dataset_config:
        merge_workspace_evidence_config_values(dataset_config, "data_roots", data_roots, applied, "发现数据候选根", force=force)
        merge_workspace_evidence_config_values(dataset_config, "dataset_hints", dataset_candidates, applied, "发现数据集线索", force=force)

    env_infer_config = workspace_mutable_node_config_by_kind(updated, "env.infer")
    if env_infer_config:
        merge_workspace_evidence_config_values(env_infer_config, "manifest_paths", found_manifests, applied, "发现环境清单", force=force)

    env_prepare_config = workspace_mutable_node_config_by_kind(updated, "env.prepare")
    if env_prepare_config and setup_suggestion:
        apply_workspace_evidence_config_value(
            env_prepare_config,
            "setup_command",
            setup_suggestion,
            applied,
            "发现环境安装命令",
            force=force,
        )

    run_config = workspace_mutable_node_config_by_kind(updated, "run.command")
    if run_config and run_suggestion:
        apply_workspace_evidence_config_value(
            run_config,
            "run_command",
            run_suggestion,
            applied,
            "发现运行命令",
            force=force,
        )

    artifact_config = workspace_mutable_node_config_by_kind(updated, "artifact.collect")
    if artifact_config:
        merge_workspace_evidence_config_values(artifact_config, "artifact_paths", artifact_paths, applied, "发现产物路径", force=force)
        merge_workspace_evidence_config_values(artifact_config, "metric_paths", metric_paths, applied, "发现指标路径", force=force)

    eval_config = workspace_mutable_node_config_by_kind(updated, "eval.report")
    if eval_config:
        merge_workspace_evidence_config_values(eval_config, "metric_paths", metric_paths, applied, "发现报告指标路径", force=force)

    if gpu_server_id:
        for kind, label in (("gpu.allocate", "发现调度服务器"), ("run.command", "发现运行服务器")):
            config = workspace_mutable_node_config_by_kind(updated, kind)
            if config:
                apply_workspace_evidence_config_value(config, "server_id", gpu_server_id, applied, label, force=force)
                apply_workspace_evidence_config_value(config, "gpu_policy", "auto", applied, "发现 GPU 策略", force=force)

    if applied:
        updated["updated_at"] = now_iso()
    return updated, applied


def workspace_payload_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default) if isinstance(payload, dict) else default
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def workspace_backfill_request_matches(item: dict[str, Any], requested: dict[str, Any]) -> bool:
    node_kind = str(requested.get("node_kind") or requested.get("nodeKind") or "").strip()
    field = str(requested.get("field") or "").strip()
    if node_kind and str(item.get("node_kind") or "").strip() != node_kind:
        return False
    if field and str(item.get("field") or "").strip() != field:
        return False
    label = str(requested.get("label") or "").strip()
    if label and str(item.get("label") or "").strip() != label:
        return False
    value = str(requested.get("value") or "").strip()
    if value and str(item.get("value") or "").strip() != value:
        return False
    return bool(node_kind and field)


def apply_workspace_evidence_backfill_item_to_payload(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
    requested_item: dict[str, Any],
    *,
    statuses: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    execution = derive_workspace_execution_state(updated, jobs)
    if statuses is not None:
        automation = derive_workspace_automation_state(updated, execution, statuses)
        plan = (
            automation.get("evidence_backfill")
            if isinstance(automation.get("evidence_backfill"), dict)
            else {}
        )
    else:
        plan = derive_workspace_evidence_backfill_plan(updated, execution)
    plan_items = plan.get("items") if isinstance(plan.get("items"), list) else []
    item = next(
        (
            candidate for candidate in plan_items
            if isinstance(candidate, dict) and workspace_backfill_request_matches(candidate, requested_item)
        ),
        None,
    )
    if not item:
        raise ValueError("backfill item not found")
    status = str(item.get("status") or "").strip()
    if status in {"blocked", "draft", "failed"}:
        raise ValueError(str(item.get("action") or "this backfill item is not ready"))
    node_kind = str(item.get("node_kind") or "").strip()
    field = str(item.get("field") or "").strip()
    label = str(item.get("label") or field or "证据回填").strip()
    mode = str(item.get("mode") or "append").strip()
    value = str(item.get("value") or "").strip()
    if not node_kind or not field or not value:
        raise ValueError("backfill item is missing node kind, field or value")
    config = workspace_mutable_node_config_by_kind(updated, node_kind)
    if not config:
        raise ValueError(f"missing {node_kind} node")

    applied: list[dict[str, Any]] = []
    if mode == "replace":
        apply_workspace_evidence_config_value(config, field, value, applied, label, force=force)
    else:
        merge_workspace_evidence_config_values(config, field, workspace_config_values(value), applied, label, force=force)
    for applied_item in applied:
        applied_item["node_kind"] = node_kind
        applied_item["mode"] = mode
        applied_item["source"] = "evidence"
    if applied:
        updated["updated_at"] = now_iso()
    return updated, applied


def apply_workspace_automation_defaults_to_payload(
    workspace: dict[str, Any],
    statuses: list[dict[str, Any]],
    *,
    force: bool = False,
    scheduler_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated = copy.deepcopy(workspace)
    applied: list[dict[str, Any]] = []
    current_tools = normalize_workspace_tools(updated.get("tools"), existing=updated.get("tools"))
    required_tool_ids = workspace_required_default_tool_ids(updated)
    current_tools, default_tool_applied = backfill_default_tool_definitions(
        current_tools,
        required_tool_ids=required_tool_ids,
    )
    if default_tool_applied:
        updated["tools"] = current_tools
        applied.extend(default_tool_applied)
    tool_ids = [str(item.get("id") or "").strip() for item in current_tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
    current_agents = normalize_workspace_agents(
        updated.get("agents"),
        existing=updated.get("agents"),
        tool_ids=tool_ids,
    )
    current_agents, default_agent_applied = backfill_default_agent_tools(
        current_agents,
        tool_ids=tool_ids,
    )
    if default_agent_applied:
        updated["agents"] = current_agents
        applied.extend(default_agent_applied)
    workspace_dir = infer_workspace_dir_from_inputs(updated)
    if workspace_dir and (force or not str(updated.get("workspace_dir") or "").strip()):
        updated["workspace_dir"] = workspace_dir
        applied.append({"field": "workspace_dir", "label": "工作目录", "value": workspace_dir})
    else:
        workspace_dir = str(updated.get("workspace_dir") or workspace_dir or "").strip()

    env = updated.get("env") if isinstance(updated.get("env"), dict) else {}
    env_name = str(env.get("name") or "").strip()
    if (force or not env_name) and workspace_default_name_seed(updated):
        env_name = f"rg-{safe_id(workspace_default_name_seed(updated))}"[:64]
        env["name"] = env_name
        applied.append({"field": "env.name", "label": "环境名", "value": env_name})
    if not str(env.get("manager") or "").strip():
        env["manager"] = "conda"
    updated["env"] = env

    data_roots = infer_workspace_data_roots(updated, workspace_dir)
    setup_command = infer_workspace_setup_command(workspace_dir)
    run_command = infer_workspace_run_command(workspace_dir)
    report_command = "echo '[eval.report] inspect metrics, results and reports'"
    scheduler_values = derive_workspace_scheduler_values(updated, statuses)
    explicit_scheduler_values = workspace_scheduler_values_from_candidate(
        scheduler_candidate,
        scheduler_values.get("scheduler") if isinstance(scheduler_values.get("scheduler"), dict) else {},
    )
    if explicit_scheduler_values.get("server_id"):
        scheduler_values.update(explicit_scheduler_values)
    artifact_paths = "runs\noutputs\ncheckpoints\nlogs"

    for node in (updated.get("nodes") if isinstance(updated.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        kind = str(node.get("kind") or "").strip()
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        if workspace_dir and kind in {"repo.clone", "path.resolve", "repo.inspect", "env.infer", "env.prepare", "run.command", "artifact.collect"}:
            apply_workspace_config_value(config, "workspace_dir", workspace_dir, applied, f"{kind} 工作目录", force=force)
        if env_name and kind in {"env.infer", "env.prepare", "run.command"}:
            apply_workspace_config_value(config, "env_name", env_name, applied, f"{kind} 环境名", force=force)
        if kind == "path.resolve":
            apply_workspace_config_value(config, "data_roots", "\n".join(data_roots), applied, "数据根目录", force=force)
            apply_workspace_config_value(config, "output_roots", artifact_paths, applied, "输出目录", force=force)
        elif kind == "dataset.find":
            source = updated.get("source") if isinstance(updated.get("source"), dict) else {}
            query = str(source.get("repo_url") or source.get("paper_url") or updated.get("brief") or updated.get("name") or "").strip()
            apply_workspace_config_value(config, "query", query, applied, "数据集检索词", force=force)
            apply_workspace_config_value(config, "data_roots", "\n".join(data_roots), applied, "数据候选根", force=force)
            if data_roots:
                apply_workspace_config_value(config, "dataset_hints", "\n".join(data_roots), applied, "数据集线索", force=force)
        elif kind == "env.infer":
            apply_workspace_config_value(
                config,
                "manifest_paths",
                "requirements.txt, pyproject.toml, environment.yml, conda.yml, setup.py",
                applied,
                "环境清单候选",
                force=force,
            )
        elif kind == "env.prepare":
            apply_workspace_config_value(config, "setup_command", setup_command, applied, "环境安装命令", force=force)
        elif kind == "gpu.allocate":
            if scheduler_values.get("server_id"):
                apply_workspace_scheduler_config_value(config, "server_id", scheduler_values["server_id"], applied, "调度服务器", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_policy", scheduler_values["gpu_policy"], applied, "调度 GPU 策略", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_index", scheduler_values["gpu_index"], applied, "调度 GPU 编号", force=force)
                if scheduler_values.get("min_free_memory_gib"):
                    apply_workspace_scheduler_config_value(config, "min_free_memory_gib", scheduler_values["min_free_memory_gib"], applied, "最低空闲显存", force=force)
        elif kind == "run.command":
            if scheduler_values.get("server_id"):
                apply_workspace_scheduler_config_value(config, "server_id", scheduler_values["server_id"], applied, "运行服务器", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_policy", scheduler_values["gpu_policy"], applied, "运行 GPU 策略", force=force)
                apply_workspace_scheduler_config_value(config, "gpu_index", scheduler_values["gpu_index"], applied, "运行 GPU 编号", force=force)
                if scheduler_values.get("min_free_memory_gib"):
                    apply_workspace_scheduler_config_value(config, "min_free_memory_gib", scheduler_values["min_free_memory_gib"], applied, "运行最低空闲显存", force=force)
            apply_workspace_config_value(config, "run_command", run_command, applied, "运行命令", force=force)
        elif kind == "artifact.collect":
            apply_workspace_config_value(config, "artifact_paths", artifact_paths, applied, "产物路径", force=force)
            apply_workspace_config_value(config, "metric_paths", "metrics\nresults\nreports", applied, "指标路径", force=force)
        elif kind == "eval.report":
            apply_workspace_config_value(config, "metric_paths", "metrics\nresults\nreports", applied, "报告指标路径", force=force)
            apply_workspace_config_value(config, "report_command", report_command, applied, "报告命令", force=force)
        node["config"] = config
    updated["updated_at"] = now_iso()
    return updated, applied


def apply_workspace_job_runtime(
    workspace: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    copy_workspace = copy.deepcopy(workspace)
    workspace_id = str(copy_workspace.get("id") or "").strip()
    if not workspace_id:
        return copy_workspace
    for node in copy_workspace.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        runtime = normalize_workspace_runtime(node.get("runtime"))
        matches = [
            job for job in jobs
            if workspace_job_binding(job) == (workspace_id, node_id)
        ]
        if matches:
            matches.sort(key=workspace_job_sort_key, reverse=True)
            latest = matches[0]
            runtime.update(
                {
                    "run_count": len(matches),
                    "last_job_id": str(latest.get("id") or "").strip(),
                    "last_job_name": str(latest.get("name") or "").strip(),
                    "last_job_kind": str(latest.get("kind") or "").strip(),
                    "last_job_status": str(latest.get("status") or "").strip(),
                    "last_run_at": str(latest.get("started_at") or latest.get("created_at") or "").strip(),
                    "last_finished_at": str(latest.get("finished_at") or "").strip(),
                    "last_error": str(latest.get("error") or "").strip(),
                }
            )
        node["runtime"] = runtime
    return copy_workspace


def normalize_workspace_payload(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    source_current = current.get("source") if isinstance(current.get("source"), dict) else {}
    env_current = current.get("env") if isinstance(current.get("env"), dict) else {}
    recipes_current = current.get("recipes") if isinstance(current.get("recipes"), list) else []
    recipe_existing = recipes_current[0] if recipes_current and isinstance(recipes_current[0], dict) else None

    source_type = normalize_source_mode(
        str(payload.get("source_type") or source_current.get("type") or "repo").strip().lower()
    )

    repo_url = str(payload.get("repo_url") or source_current.get("repo_url") or "").strip()
    paper_url = str(payload.get("paper_url") or source_current.get("paper_url") or "").strip()
    idea_text = str(payload.get("idea_text") or source_current.get("idea_text") or "").strip()
    brief = str(payload.get("brief") or current.get("brief") or "").strip()

    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        if repo_url:
            name = repo_name_from_url(repo_url)
        elif paper_url:
            name = "Paper Workspace"
        elif brief:
            name = brief.splitlines()[0][:40]
        elif idea_text:
            name = idea_text.splitlines()[0][:40]
        else:
            name = "新工作区"

    workspace_id = str(current.get("id") or "").strip() or (
        datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    )
    recipe = normalize_workspace_recipe(payload, existing=recipe_existing)
    created_at = str(current.get("created_at") or "").strip() or now_iso()
    status = str(payload.get("status") or current.get("status") or "draft").strip() or "draft"
    workspace_dir = str(payload.get("workspace_dir") or current.get("workspace_dir") or "").strip()
    env_name = str(payload.get("env_name") or env_current.get("name") or "").strip()
    env_manager = str(payload.get("env_manager") or env_current.get("manager") or "conda").strip() or "conda"
    python_version = str(payload.get("python_version") or env_current.get("python") or "").strip()
    raw_nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else None
    raw_links = payload.get("links") if isinstance(payload.get("links"), list) else None
    raw_tools = payload.get("tools") if isinstance(payload.get("tools"), list) else None
    rebuild_graph = bool(payload.get("rebuild_graph"))
    node_payload = raw_nodes
    if node_payload is None and not rebuild_graph and isinstance(current.get("nodes"), list):
        node_payload = current.get("nodes")
    tools = normalize_workspace_tools(
        raw_tools if raw_tools is not None else current.get("tools"),
        existing=current.get("tools") if isinstance(current.get("tools"), list) else None,
    )
    tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
    nodes = normalize_workspace_nodes(
        node_payload,
        source_type_for_chain(source_type),
        brief=brief,
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        existing_nodes=current.get("nodes") if isinstance(current.get("nodes"), list) else None,
        use_default_chain=rebuild_graph,
    )
    nodes = sync_workspace_nodes_with_overview(
        nodes,
        brief=brief,
        source_type=source_type_for_chain(source_type),
        repo_url=repo_url,
        repo_ref=str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
        paper_url=paper_url,
        idea_text=idea_text,
        workspace_dir=workspace_dir,
        env_name=env_name,
        env_manager=env_manager,
        python_version=python_version,
        recipe=recipe,
        recipe_command_overrides={
            key
            for key in ("setup_command", "run_command", "report_command", "schedule")
            if key in payload
        },
    )
    if raw_links is None and not rebuild_graph:
        raw_links = current.get("links") if isinstance(current.get("links"), list) else None
    links = normalize_workspace_links(raw_links, nodes)
    agents = normalize_workspace_agents(
        payload.get("agents") if "agents" in payload else current.get("agents"),
        existing=current.get("agents"),
        tool_ids=tool_ids,
    )
    model = normalize_workspace_model(
        payload.get("model") if "model" in payload else current.get("model"),
        existing=current.get("model"),
    )
    chat = normalize_workspace_chat(
        payload.get("chat") if "chat" in payload else current.get("chat"),
        existing=current.get("chat"),
    )
    inputs = normalize_workspace_inputs(
        payload.get("inputs") if isinstance(payload.get("inputs"), dict) else payload,
        existing=current.get("inputs"),
    )
    template_snapshot = payload.get("template_snapshot") if isinstance(payload.get("template_snapshot"), dict) else current.get("template_snapshot")
    execution = payload.get("execution") if isinstance(payload.get("execution"), dict) else current.get("execution")

    return {
        "id": workspace_id,
        "name": name,
        "status": status,
        "brief": brief,
        "references": parse_line_list(payload.get("references", current.get("references", []))),
        "inputs": inputs,
        "source": {
            "type": source_type,
            "repo_url": repo_url,
            "repo_ref": str(payload.get("repo_ref") or source_current.get("repo_ref") or "").strip(),
            "paper_url": paper_url,
            "idea_text": idea_text,
        },
        "workspace_dir": workspace_dir,
        "env": {
            "name": env_name,
            "manager": env_manager,
            "python": python_version,
        },
        "recipes": [recipe],
        "agents": agents,
        "model": model,
        "chat": chat,
        "tools": tools,
        "nodes": nodes,
        "links": links,
        "notes": str(payload.get("notes") or current.get("notes") or "").strip(),
        "tags": parse_tag_list(payload.get("tags", current.get("tags", []))),
        "template_id": str(payload.get("template_id") or current.get("template_id") or "").strip(),
        "template_name": str(payload.get("template_name") or current.get("template_name") or "").strip(),
        "template_snapshot": copy.deepcopy(template_snapshot) if isinstance(template_snapshot, dict) else {},
        "execution": copy.deepcopy(execution) if isinstance(execution, dict) else {},
        "created_at": created_at,
        "updated_at": now_iso(),
    }


@dataclass
class ServerConfig:
    id: str
    name: str
    mode: str = "local"
    enabled: bool = True
    labels: list[str] = field(default_factory=list)
    ssh_alias: str | None = None
    ssh_config_path: str | None = None
    host_name: str | None = None
    user: str | None = None
    port: str | None = None
    password: str | None = None

    def target_label(self) -> str:
        if self.mode == "local":
            return "local"
        if self.user and self.host_name:
            return f"{self.user}@{self.host_name}"
        return self.ssh_alias or self.host_name or self.id


@dataclass
class AppConfig:
    poll_interval_seconds: int = 5
    remote_timeout_seconds: int = 6
    idle_min_free_mib: int = 1024
    idle_max_gpu_util: int = 10
    servers: list[ServerConfig] = field(default_factory=list)


def load_secrets(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    passwords = raw.get("ssh_passwords", {})
    if not isinstance(passwords, dict):
        return {}
    return {str(key): str(value) for key, value in passwords.items() if str(value)}


def secret_password(secrets: dict[str, str], *, alias: str, server_id: str, host_name: str | None, user: str | None) -> str | None:
    keys = [alias, server_id]
    if host_name:
        keys.append(host_name)
    if user and host_name:
        keys.append(f"{user}@{host_name}")
    for key in keys:
        if key in secrets:
            return secrets[key]
    return None


def config_alias(aliases: dict[str, str], *, alias: str, server_id: str, host_name: str | None, user: str | None, fallback: str) -> str:
    keys = [alias, server_id]
    if host_name:
        keys.append(host_name)
    if user and host_name:
        keys.append(f"{user}@{host_name}")
    for key in keys:
        if key in aliases:
            return aliases[key]
    return fallback


def parse_ssh_config(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    hosts: list[dict[str, str]] = []
    active: list[dict[str, str]] = []

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        key, value = parts[0].lower(), parts[1].strip()
        if key == "host":
            active = []
            for pattern in value.split():
                if any(mark in pattern for mark in ("*", "?", "!")):
                    continue
                entry = {"host": pattern}
                hosts.append(entry)
                active.append(entry)
            continue
        for entry in active:
            entry[key] = value

    return hosts


def load_config(path: Path) -> AppConfig:
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))

    user_path = path.with_name("user_servers.toml")
    user_raw: dict[str, Any] = {}
    if user_path.exists():
        try:
            user_raw = tomllib.loads(user_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            user_raw = {}

    app = raw.get("app", {})
    aliases = {str(key): str(value) for key, value in raw.get("server_aliases", {}).items()}
    user_aliases = {str(key): str(value) for key, value in user_raw.get("server_aliases", {}).items()}
    aliases.update(user_aliases)
    user_disabled = {str(item) for item in user_raw.get("disabled_discovery", [])}
    secrets = load_secrets(path.with_name("secrets.toml"))
    config = AppConfig(
        poll_interval_seconds=safe_int(app.get("poll_interval_seconds"), 5),
        remote_timeout_seconds=safe_int(app.get("remote_timeout_seconds"), 6),
        idle_min_free_mib=safe_int(app.get("idle_min_free_mib"), 1024),
        idle_max_gpu_util=safe_int(app.get("idle_max_gpu_util"), 10),
    )

    seen: set[str] = set()
    server_items = list(raw.get("servers", [])) + list(user_raw.get("servers", []))
    for item in server_items:
        server_id = safe_id(str(item.get("id") or item.get("name") or "server"))
        if server_id in seen:
            continue
        seen.add(server_id)
        config.servers.append(
            ServerConfig(
                id=server_id,
                name=config_alias(
                    aliases,
                    alias=str(item.get("ssh_alias") or item.get("id") or item.get("name") or ""),
                    server_id=server_id,
                    host_name=item.get("host_name"),
                    user=item.get("user"),
                    fallback=str(item.get("name") or server_id),
                ),
                mode=str(item.get("mode") or "local"),
                enabled=bool(item.get("enabled", True)),
                labels=list(item.get("labels", [])),
                ssh_alias=item.get("ssh_alias"),
                ssh_config_path=item.get("ssh_config_path"),
                host_name=item.get("host_name"),
                user=item.get("user"),
                port=str(item["port"]) if "port" in item else None,
                password=item.get("password")
                or secret_password(
                    secrets,
                    alias=str(item.get("ssh_alias") or item.get("id") or item.get("name") or ""),
                    server_id=server_id,
                    host_name=item.get("host_name"),
                    user=item.get("user"),
                ),
            )
        )

    discovery = dict(raw.get("ssh_discovery", {}) or {})
    discovery.update(dict(user_raw.get("ssh_discovery", {}) or {}))
    if discovery.get("enabled", False):
        ssh_path = Path(str(discovery.get("config_path") or "~/.ssh/config")).expanduser()
        includes = list(discovery.get("include", ["*"])) or ["*"]
        excludes = set(discovery.get("exclude", []))
        for host in parse_ssh_config(ssh_path):
            alias = host.get("host", "")
            if not alias or alias in excludes:
                continue
            if alias in user_disabled:
                continue
            if not any(fnmatch.fnmatch(alias, pattern) for pattern in includes):
                continue
            server_id = safe_id(alias)
            if server_id in seen:
                continue
            if server_id in user_disabled:
                continue
            seen.add(server_id)
            labels = ["ssh"]
            if host.get("hostname"):
                labels.append(host["hostname"])
            config.servers.append(
                ServerConfig(
                    id=server_id,
                    name=config_alias(
                        aliases,
                        alias=alias,
                        server_id=server_id,
                        host_name=host.get("hostname"),
                        user=host.get("user"),
                        fallback=alias,
                    ),
                    mode="ssh",
                    enabled=True,
                    labels=labels,
                    ssh_alias=alias,
                    host_name=host.get("hostname"),
                    user=host.get("user"),
                    port=host.get("port"),
                    password=secret_password(
                        secrets,
                        alias=alias,
                        server_id=server_id,
                        host_name=host.get("hostname"),
                        user=host.get("user"),
                    ),
                )
            )

    if not config.servers:
        config.servers.append(ServerConfig(id="local", name="Local"))
    return config


_TOML_BARE_RE = None


def _toml_str(value: str) -> str:
    text = str(value)
    out = ['"']
    for char in text:
        code = ord(char)
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return _toml_str(value)


def dump_toml(data: dict[str, Any]) -> str:
    """Minimal TOML writer for our user overlay file."""
    lines: list[str] = []

    # Bare keys MUST come before any [table] header.
    disabled = data.get("disabled_discovery", [])
    if disabled:
        lines.append(f"disabled_discovery = {_toml_value(list(disabled))}")
        lines.append("")

    discovery = data.get("ssh_discovery", {})
    if discovery:
        lines.append("[ssh_discovery]")
        for key, value in discovery.items():
            if value is None or value == "":
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    aliases = data.get("server_aliases", {})
    if aliases:
        lines.append("[server_aliases]")
        for key, value in aliases.items():
            lines.append(f"{_toml_str(key)} = {_toml_str(str(value))}")
        lines.append("")

    for server in data.get("servers", []):
        lines.append("[[servers]]")
        for key, value in server.items():
            if value is None or value == "":
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_user_overlay(config_path: Path) -> dict[str, Any]:
    user_path = config_path.with_name("user_servers.toml")
    if not user_path.exists():
        return {"server_aliases": {}, "disabled_discovery": [], "servers": [], "ssh_discovery": {}}
    try:
        raw = tomllib.loads(user_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {"server_aliases": {}, "disabled_discovery": [], "servers": [], "ssh_discovery": {}}
    return {
        "server_aliases": dict(raw.get("server_aliases", {}) or {}),
        "disabled_discovery": list(raw.get("disabled_discovery", []) or []),
        "servers": list(raw.get("servers", []) or []),
        "ssh_discovery": dict(raw.get("ssh_discovery", {}) or {}),
    }


def save_user_overlay(config_path: Path, overlay: dict[str, Any]) -> None:
    user_path = config_path.with_name("user_servers.toml")
    user_path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_toml(overlay)
    user_path.write_text(text, encoding="utf-8")


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


def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_shell(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return run_command(["bash", "-lc", script], timeout)


def tmux_new_session_args(session: str, shell_command: str) -> list[str]:
    return [
        "tmux",
        "new-session",
        "-d",
        "-s",
        session,
        "-x",
        str(TMUX_DEFAULT_COLUMNS),
        "-y",
        str(TMUX_DEFAULT_ROWS),
        shell_command,
    ]


def tmux_resize_commands(session: str) -> list[list[str]]:
    columns = str(TMUX_DEFAULT_COLUMNS)
    rows = str(TMUX_DEFAULT_ROWS)
    return [
        ["tmux", "resize-window", "-t", session, "-x", columns, "-y", rows],
        ["tmux", "resize-pane", "-t", session, "-x", columns, "-y", rows],
    ]


def tmux_resize_shell_script(session: str) -> str:
    target = shlex.quote(session)
    columns = str(TMUX_DEFAULT_COLUMNS)
    rows = str(TMUX_DEFAULT_ROWS)
    return "\n".join(
        [
            f"tmux resize-window -t {target} -x {columns} -y {rows} 2>/dev/null || true",
            f"tmux resize-pane -t {target} -x {columns} -y {rows} 2>/dev/null || true",
        ]
    )


def prepare_tmux_for_capture(session: str) -> None:
    for command in tmux_resize_commands(session):
        try:
            run_command(command, timeout=TMUX_RESIZE_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            pass


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


def ssh_command(server: ServerConfig, remote_command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    command = ssh_command_base(server, connect_timeout=timeout)
    command.append(remote_command)
    if server.password:
        return run_pty_password_command(command, server.password, timeout=timeout + 8)
    return run_command(command, timeout=timeout + 2)


def ssh_command_base(server: ServerConfig, connect_timeout: int = 20) -> list[str]:
    # 用 user@host_name 连接更明确，不依赖 SSH config alias
    if server.user and server.host_name:
        target = f"{server.user}@{server.host_name}"
    else:
        target = server.ssh_alias or server.host_name or server.id
    command = ["ssh"]
    # 不传 -F，让 SSH 使用系统默认 config（~/.ssh/config），自动读取 IdentityFile 等配置
    if server.port:
        command.extend(["-p", str(server.port)])
    if server.password:
        command.extend(
            [
                "-o",
                "PreferredAuthentications=password,keyboard-interactive",
                "-o",
                "PubkeyAuthentication=no",
            ]
        )
    command.extend(
        [
            "-o",
            "BatchMode=no" if server.password else "BatchMode=yes",
            "-o",
            f"ConnectTimeout={max(1, min(connect_timeout, 20))}",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "NumberOfPasswordPrompts=3" if server.password else "NumberOfPasswordPrompts=0",
            target,
        ]
    )
    return command


def parse_csv_lines(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in csv.reader(text.splitlines()):
        if not row:
            continue
        rows.append([cell.strip() for cell in row])
    return rows


def ps_lookup_local(pids: list[str], timeout: int) -> dict[str, dict[str, str]]:
    if not pids:
        return {}
    result = run_command(["ps", "-o", "user=,pid=,command=", "-p", ",".join(pids)], timeout)
    return parse_ps_output(result.stdout)


def ps_lookup_remote(server: ServerConfig, pids: list[str], timeout: int) -> dict[str, dict[str, str]]:
    if not pids:
        return {}
    cmd = "ps -o user=,pid=,command= -p " + shlex.quote(",".join(pids))
    result = ssh_command(server, cmd, timeout)
    return parse_ps_output(result.stdout)


def parse_ps_output(text: str) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2:
            pid = parts[1]
            data[pid] = {
                "user": parts[0],
                "command": parts[2] if len(parts) == 3 else "",
            }
    return data


PSEUDO_FS_TYPES = {
    "autofs",
    "binfmt_misc",
    "bpf",
    "cgroup",
    "cgroup2",
    "configfs",
    "debugfs",
    "devpts",
    "devtmpfs",
    "efivarfs",
    "fusectl",
    "hugetlbfs",
    "mqueue",
    "nsfs",
    "overlay",
    "proc",
    "pstore",
    "rpc_pipefs",
    "securityfs",
    "sysfs",
    "tmpfs",
    "tracefs",
}
PSEUDO_MOUNT_PREFIXES = (
    "/dev",
    "/proc",
    "/run",
    "/snap",
    "/sys",
    "/var/lib/docker",
    "/var/lib/containers",
    "/var/lib/kubelet",
)
HOST_RESOURCE_MARKER = "__TC_HOST_RESOURCES_JSON__"
REACHABILITY_PROBE_TIMEOUT_SECONDS = 2
CONNECTION_REFRESH_BACKOFF_SECONDS = 90


def percent(used: int | float, total: int | float) -> float:
    total_value = float(total or 0)
    if total_value <= 0:
        return 0.0
    return round(max(float(used or 0), 0.0) * 100 / total_value, 1)


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


def collect_host_resources(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
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


def probe_ssh_reachable(server: ServerConfig, timeout: int) -> bool:
    if server.mode == "local":
        return True
    try:
        result = ssh_command(
            server,
            remote_check_script("printf '%s\\n' __tc_ok__"),
            timeout=min(max(timeout, 1), REACHABILITY_PROBE_TIMEOUT_SECONDS),
        )
        output = f"{result.stdout or ''}\n{result.stderr or ''}".strip()
        if result.returncode != 0 or "__tc_ok__" not in output:
            return False
        return not ssh_transport_output_looks_failed(output)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return False
    except Exception:  # noqa: BLE001 - keep polling resilient for one bad host.
        return False


def apply_remote_reachability(
    status: dict[str, Any],
    server: ServerConfig,
    app_config: AppConfig,
    *,
    default_error_kind: str,
) -> None:
    if server.mode == "local":
        status["reachable"] = True
        status["error_kind"] = status.get("error_kind") or "gpu_probe"
        return
    if probe_ssh_reachable(server, app_config.remote_timeout_seconds):
        status["reachable"] = True
        status["error_kind"] = "gpu_probe"
    else:
        status["reachable"] = False
        status["error_kind"] = default_error_kind or "connection"


def collect_server(server: ServerConfig, app_config: AppConfig) -> dict[str, Any]:
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
        "gpus": [],
        "processes": [],
        "host_resources": {},
    }

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
            status["host_resources"] = (
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
        status["host_resources"] = collect_host_resources(server, app_config)
        status["reachable"] = True
        status["monitor_ok"] = True
        status["online"] = True
        return status
    except subprocess.TimeoutExpired:
        status["error"] = "timeout"
        apply_remote_reachability(status, server, app_config, default_error_kind="connection")
        status["host_resources"] = (
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    except FileNotFoundError as exc:
        status["error"] = f"missing command: {exc.filename}"
        status["reachable"] = server.mode == "local"
        status["error_kind"] = "gpu_probe"
        status["host_resources"] = (
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    except Exception as exc:  # noqa: BLE001 - keep API alive for one bad host.
        status["error"] = str(exc)
        apply_remote_reachability(status, server, app_config, default_error_kind="connection")
        status["host_resources"] = (
            collect_host_resources(server, app_config)
            if status.get("reachable")
            else host_resource_error_payload("server unreachable")
        )
        return status
    finally:
        status["elapsed_ms"] = int((time.time() - started) * 1000)


def parse_iso_timestamp(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value or "")).timestamp()
    except (TypeError, ValueError):
        return 0.0


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


def make_session_name(job_id: str) -> str:
    return "tc_" + "".join(char for char in job_id if char.isalnum())[:24]


def local_log_path(server_id: str, job_id: str) -> Path:
    return LOG_DIR / safe_id(server_id) / f"{job_id}.log"


def remote_log_path(job_id: str) -> str:
    return f"$HOME/.total_control/logs/{job_id}.log"


def parse_smoke_peak_mib(text: str) -> int:
    for line in text.splitlines():
        if "Peak allocated:" in line:
            parts = line.replace(":", " ").split()
            for index, part in enumerate(parts):
                if part.lower() == "allocated" and index + 1 < len(parts):
                    return safe_int(parts[index + 1])
        if "Peak MiB" in line:
            parts = line.split()
            for part in parts:
                value = safe_int(part, -1)
                if value > 0:
                    return value
    return 0


class _TemplateMap(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_task_template(template: str, values: dict[str, Any]) -> str:
    if not template:
        return ""
    try:
        return template.format_map(_TemplateMap(values))
    except (KeyError, ValueError):
        return template


def parse_param_matrix(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        rows = [
            dict(item)
            for item in value
            if isinstance(item, dict)
        ]
    else:
        rows = []
        text = str(value or "").strip()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"参数矩阵 JSON 行解析失败: {exc}") from exc
                if not isinstance(parsed, dict):
                    raise ValueError("参数矩阵 JSON 行必须是对象")
                rows.append(parsed)
                continue
            row: dict[str, Any] = {}
            for cell in next(csv.reader([line])):
                part = cell.strip()
                if not part:
                    continue
                if "=" not in part:
                    row.setdefault("value", part)
                    continue
                key, cell_value = part.split("=", 1)
                key = key.strip()
                if key:
                    row[key] = cell_value.strip()
            if row:
                rows.append(row)
    if not rows:
        rows = [{}]
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        item = dict(row)
        item.setdefault("index", index)
        item.setdefault("i", index)
        normalized.append(item)
    return normalized


def conda_bootstrap(env_name: str, server_user: str | None = None) -> str:
    env = shlex.quote(env_name)
    if "/" in env_name:
        env_path = shlex.quote(env_name.rstrip("/"))
        return "\n".join(
            [
                f"if [ -f {env_path}/bin/activate ]; then",
                f"  . {env_path}/bin/activate",
                "else",
                f"  conda activate {env}",
                "fi",
            ]
        )
    user_env_path = f"/home/{server_user}/envs/{env_name}" if server_user else ""
    home_activate = f"\"$HOME/envs\"/{env}/bin/activate"
    lines = []
    if user_env_path:
        lines.append(f"if [ -f {shlex.quote(user_env_path)}/bin/activate ]; then")
        lines.append(f"  . {shlex.quote(user_env_path)}/bin/activate")
        lines.append(f"elif [ -f {home_activate} ]; then")
        lines.append(f"  . {home_activate}")
    else:
        lines.append(f"if [ -f {home_activate} ]; then")
        lines.append(f"  . {home_activate}")
    lines.append("else")
    lines.append(
        "  if [ -f ~/software/anaconda3/etc/profile.d/conda.sh ]; then "
        ". ~/software/anaconda3/etc/profile.d/conda.sh; "
        "elif [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then "
        ". ~/anaconda3/etc/profile.d/conda.sh; "
        "elif [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then "
        ". ~/miniconda3/etc/profile.d/conda.sh; "
        "fi"
    )
    lines.append(f"  conda activate {env}")
    lines.append("fi")
    return "\n".join(lines)


def build_job_script(
    job: dict[str, Any],
    log_path: str,
    remote: bool,
    server: ServerConfig | None = None,
    command_override: str | None = None,
    command_display: str | None = None,
) -> str:
    if remote:
        log_target = f'"$HOME/.total_control/logs/{job["id"]}.log"'
        mkdir_line = 'mkdir -p "$HOME/.total_control/logs"'
        exec_line = f"exec > {log_target} 2>&1"
    else:
        mkdir_line = f"mkdir -p {shlex.quote(str(Path(log_path).parent))}"
        exec_line = f"exec > {shlex.quote(log_path)} 2>&1"
    lines = [
        "set -o pipefail",
        mkdir_line,
        exec_line,
        f"echo '[total-control] job {job['id']} started at '$(date '+%F %T')",
    ]
    cwd = str(job.get("cwd") or "").strip()
    if cwd:
        lines.append(f"cd {shlex.quote(cwd)}")
    env_name = str(job.get("env_name") or "").strip()
    if env_name:
        lines.append(conda_bootstrap(env_name, server.user if server else None))
    gpu_index = job.get("gpu_index")
    gpu_index_text = str(gpu_index).strip().lower() if gpu_index is not None else ""
    if gpu_index_text in {"none", "no_gpu", "cpu"}:
        lines.append("unset CUDA_VISIBLE_DEVICES")
    elif gpu_index is not None and gpu_index != "":
        lines.append(f"export CUDA_VISIBLE_DEVICES={shlex.quote(str(gpu_index))}")
    command = str(command_override if command_override is not None else job.get("command") or "")
    display = str(command_display if command_display is not None else job.get("command_display") or command)
    lines.extend(
        [
            "echo '[total-control] server='$(hostname)' gpu='${CUDA_VISIBLE_DEVICES:-none}",
            "echo '[total-control] command:'",
            f"echo {shlex.quote(display)}",
            command,
            "code=$?",
            "echo '[total-control] finished at '$(date '+%F %T')",
            'echo "[total-control] exit_code=$code"',
            "exit $code",
        ]
    )
    return "\n".join(lines)


def rsync_endpoint_prefix(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = text.split(":", 1)
    if len(parts) != 2 or not parts[1].startswith("/"):
        return ""
    prefix = parts[0].strip()
    if not prefix or "/" in prefix:
        return ""
    return prefix


def server_matches_rsync_prefix(server: ServerConfig, prefix: str) -> bool:
    text = str(prefix or "")
    host = text.split("@", 1)[1] if "@" in text else text
    candidates = {
        server.id,
        server.name,
        server.target_label(),
        server.ssh_alias or "",
        server.host_name or "",
    }
    if server.user and server.host_name:
        candidates.add(f"{server.user}@{server.host_name}")
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate)
        if value == text or value == host or value.endswith(f"@{host}"):
            return True
    return False


def server_for_rsync_endpoint(servers: list[ServerConfig], endpoint: str) -> ServerConfig | None:
    prefix = rsync_endpoint_prefix(endpoint)
    if not prefix:
        return None
    return next((server for server in servers if server.mode != "local" and server_matches_rsync_prefix(server, prefix)), None)


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def rsync_remote_shell(server: ServerConfig | None, has_password: bool) -> str:
    parts = ["ssh"]
    if server and server.ssh_config_path:
        parts.extend(["-F", server.ssh_config_path])
    if has_password:
        parts.extend(
            [
                "-o",
                "PreferredAuthentications=password,keyboard-interactive",
                "-o",
                "PubkeyAuthentication=no",
                "-o",
                "BatchMode=no",
                "-o",
                "NumberOfPasswordPrompts=3",
            ]
        )
    else:
        parts.extend(["-o", "BatchMode=yes", "-o", "NumberOfPasswordPrompts=0"])
    parts.extend(["-o", "StrictHostKeyChecking=accept-new"])
    return shell_join(parts)


def rsync_password_wrapper(password: str, rsync_args: list[str]) -> str:
    script = r"""
import os
import pty
import select
import signal
import sys

password = os.environ.get("TC_SSH_PASSWORD", "")
command = sys.argv[1:]
if not command:
    raise SystemExit("missing rsync command")

pid, master_fd = pty.fork()
if pid == 0:
    os.execvp(command[0], command)

password_bytes = password.encode("utf-8", errors="ignore")
recent = bytearray()
password_prompts = 0
yes_prompts = 0

def forward(sig, _frame):
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass

for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, forward)

try:
    while True:
        ready, _, _ = select.select([master_fd], [], [], 0.1)
        if ready:
            try:
                chunk = os.read(master_fd, 4096)
            except OSError:
                chunk = b""
            if chunk:
                recent.extend(chunk.lower())
                del recent[:-4096]
                visible = chunk.replace(password_bytes, b"******") if password_bytes else chunk
                sys.stdout.buffer.write(visible)
                sys.stdout.buffer.flush()
                if b"are you sure you want to continue connecting" in recent and yes_prompts < 1:
                    os.write(master_fd, b"yes\n")
                    yes_prompts += 1
                if password and (b"password:" in recent or b"passphrase" in recent) and password_prompts < 3:
                    os.write(master_fd, (password + "\n").encode("utf-8"))
                    password_prompts += 1

        child, status = os.waitpid(pid, os.WNOHANG)
        if child == pid:
            raise SystemExit(os.waitstatus_to_exitcode(status))
finally:
    try:
        os.close(master_fd)
    except OSError:
        pass
"""
    return (
        "TC_SSH_PASSWORD="
        + shlex.quote(password)
        + " python3 -c "
        + shlex.quote(script)
        + " "
        + shell_join(rsync_args)
    )


def remote_file_download_endpoint(server: ServerConfig, path_text: str) -> str:
    return f"{server.target_label()}:{str(path_text or '').strip()}"


def download_remote_file_to_local(
    server: ServerConfig,
    path_text: str,
    destination_dir: Path,
    timeout: int = 45,
) -> Path:
    source_path = str(path_text or "").strip()
    if not source_path:
        raise ValueError("请选择要预览的远程文件。")
    destination = destination_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    args = [
        "rsync",
        "-a",
        "--protect-args",
        "--partial",
        "--append-verify",
        "-e",
        rsync_remote_shell(server, bool(server.password)),
        remote_file_download_endpoint(server, source_path),
        str(destination) + "/",
    ]
    if server.password:
        result = run_shell(rsync_password_wrapper(server.password, args), timeout)
    else:
        result = run_command(args, timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError(output.strip() or "远程文件下载失败")
    candidate_name = Path(source_path.rstrip("/")).name or "download"
    candidate = destination / candidate_name
    if candidate.exists():
        return candidate.resolve()
    children = sorted(destination.iterdir(), key=lambda item: item.name.lower())
    if len(children) == 1:
        return children[0].resolve()
    raise ValueError("远程文件已下载，但没有找到本机缓存文件。")


def build_transfer_command(spec: dict[str, Any], servers: list[ServerConfig]) -> tuple[str, str]:
    raw_sources = spec.get("sources") or []
    sources: list[str] = []
    for item in raw_sources:
        if isinstance(item, dict):
            value = str(item.get("value") or item.get("path") or "").strip()
        else:
            value = str(item or "").strip()
        if value:
            sources.append(value)
    target = str(spec.get("target") or "").strip()
    if not sources or not target:
        raise ValueError("transfer source and target are required")

    target_is_remote = bool(rsync_endpoint_prefix(target))
    if target_is_remote and any(rsync_endpoint_prefix(source) for source in sources):
        raise ValueError("暂不支持远程服务器到远程服务器传输，请让源或目标至少一个是本机。")

    options = dict(spec.get("options") or {})
    excludes = [str(item).strip() for item in spec.get("excludes") or [] if str(item).strip()]
    base_args = ["rsync", "-avPh", "--info=progress2"]
    if bool(options.get("checksum")):
        base_args.append("--checksum")
    elif bool(options.get("size_only", True)):
        base_args.append("--size-only")
    if bool(options.get("resume_partial", True)):
        base_args.extend(["--partial", "--append-verify"])
    for item in excludes:
        base_args.extend(["--exclude", item])

    actual_lines: list[str] = []
    display_lines: list[str] = []
    for source in sources:
        remote_endpoint = target if target_is_remote else source if rsync_endpoint_prefix(source) else ""
        remote_server = server_for_rsync_endpoint(servers, remote_endpoint) if remote_endpoint else None
        password = remote_server.password if remote_server else None
        args = list(base_args)
        if remote_endpoint:
            args.extend(["-e", rsync_remote_shell(remote_server, bool(password))])
        args.extend([source, target])
        display = shell_join(args)
        if remote_endpoint and password:
            display += "  # 使用 secrets.toml 中的 SSH 密码"
            actual_lines.append(rsync_password_wrapper(password, args))
        else:
            actual_lines.append(shell_join(args))
        display_lines.append(display)

    if len(actual_lines) == 1:
        return actual_lines[0], display_lines[0]
    return "set -e\n" + "\n".join(actual_lines), "set -e\n" + "\n".join(display_lines)


def check_detail_text(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        text = fallback
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback
    return lines[0][:240]


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


class TotalControlState:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.servers = self.config.servers
        self.lock = threading.RLock()
        self.statuses: list[dict[str, Any]] = []
        self.last_refresh = 0.0
        self.last_refreshed_at = ""
        self.jobs: list[dict[str, Any]] = read_json(JOBS_PATH, [])
        raw_tool_definitions = read_json(TOOL_DEFINITIONS_PATH, [])
        self.tool_definitions: list[dict[str, Any]] = normalize_global_tool_definitions(raw_tool_definitions)
        self.tool_definitions, default_tools_applied = backfill_default_tool_definitions(
            self.tool_definitions,
            global_definitions=True,
        )
        raw_agent_definitions = read_json(AGENT_DEFINITIONS_PATH, [])
        self.agent_definitions: list[dict[str, Any]] = normalize_global_agent_definitions(
            raw_agent_definitions,
            tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
        )
        self.agent_definitions, default_agent_tools_applied = backfill_default_agent_tools(
            self.agent_definitions,
            tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
        )
        raw_workflow_templates = read_json(WORKFLOW_TEMPLATES_PATH, [])
        if isinstance(raw_workflow_templates, list) and raw_workflow_templates:
            self.workflow_templates = [
                normalize_workflow_template(
                    item,
                    existing=item if isinstance(item, dict) else None,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
                for item in raw_workflow_templates
                if isinstance(item, dict)
            ]
        else:
            self.workflow_templates = build_default_workflow_templates(self.agent_definitions, self.tool_definitions)
        raw_workspaces = read_json(WORKSPACES_PATH, [])
        self.workspaces: list[dict[str, Any]] = raw_workspaces if isinstance(raw_workspaces, list) else []
        raw_provider_profiles = read_json(PROVIDER_PROFILES_PATH, [])
        self.provider_profiles: list[dict[str, Any]] = raw_provider_profiles if isinstance(raw_provider_profiles, list) else []
        self.next_queue_rank = 1
        self.terminals: dict[str, WebTerminal] = {}
        self.terminals_lock = threading.Lock()
        self.file_preview_cache: dict[str, dict[str, Any]] = {}
        self.last_preview_cache_cleanup = 0.0
        self.stop_event = threading.Event()
        if self.bootstrap_queue_ranks():
            write_json(JOBS_PATH, self.jobs)
        if (not isinstance(raw_tool_definitions, list) or not raw_tool_definitions) or default_tools_applied:
            write_json(TOOL_DEFINITIONS_PATH, self.tool_definitions)
        if (not isinstance(raw_agent_definitions, list) or not raw_agent_definitions) or default_agent_tools_applied:
            write_json(AGENT_DEFINITIONS_PATH, self.agent_definitions)
        if not isinstance(raw_workflow_templates, list) or not raw_workflow_templates:
            write_json(WORKFLOW_TEMPLATES_PATH, self.workflow_templates)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        FILE_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.thread.start()

    def public_config(self) -> dict[str, Any]:
        return {
            "poll_interval_seconds": self.config.poll_interval_seconds,
            "idle_min_free_mib": self.config.idle_min_free_mib,
            "idle_max_gpu_util": self.config.idle_max_gpu_util,
            "config_path": str(self.config_path),
            "server_count": len(self.servers),
        }

    def server_by_id(self, server_id: str) -> ServerConfig | None:
        return next((server for server in self.servers if server.id == server_id), None)

    def bootstrap_queue_ranks(self) -> bool:
        changed = False
        queued = [job for job in reversed(self.jobs) if str(job.get("status") or "") in {"queued", "blocked", "starting"}]
        for index, job in enumerate(queued, 1):
            if safe_int(job.get("queue_rank"), 0) != index:
                job["queue_rank"] = index
                changed = True
        self.next_queue_rank = len(queued) + 1
        return changed

    def reserve_queue_ranks(self, jobs: list[dict[str, Any]]) -> None:
        for job in jobs:
            job["queue_rank"] = self.next_queue_rank
            self.next_queue_rank += 1

    def queue_sort_key(self, job: dict[str, Any]) -> tuple[int, str, str]:
        return (
            safe_int(job.get("queue_rank"), 10**9),
            str(job.get("created_at") or ""),
            str(job.get("id") or ""),
        )

    def browse_files(
        self,
        server_id: str | None,
        path_text: str = "",
        max_entries: int = 300,
        dirs_only: bool = False,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        if not server or server.mode == "local":
            return browse_local_files(path_text, max_entries=max_entries, dirs_only=dirs_only)
        return browse_remote_files(
            server,
            path_text=path_text,
            max_entries=max_entries,
            dirs_only=dirs_only,
            timeout=self.config.remote_timeout_seconds + 4,
        )

    def read_file_text(
        self,
        server_id: str | None,
        path_text: str = "",
        limit_bytes: int = 131072,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        if not server or server.mode == "local":
            payload = read_local_text_file(path_text, limit_bytes=limit_bytes)
            if server:
                payload["server_id"] = server.id
            return payload
        return read_remote_text_file(
            server,
            path_text=path_text,
            limit_bytes=limit_bytes,
            timeout=self.config.remote_timeout_seconds + 4,
        )

    def ensure_file_preview_cache(self) -> dict[str, dict[str, Any]]:
        cache = getattr(self, "file_preview_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self.file_preview_cache = cache
        FILE_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return cache

    def register_file_preview(
        self,
        *,
        source_path: str,
        local_path: Path,
        server_id: str,
        mime_type: str,
        preview_kind: str,
        cached: bool,
    ) -> dict[str, Any]:
        cache = self.ensure_file_preview_cache()
        cache_id = uuid.uuid4().hex
        entry = {
            "cache_id": cache_id,
            "source_path": source_path,
            "local_path": str(local_path),
            "server_id": server_id or "local",
            "mime_type": mime_type,
            "preview_kind": preview_kind,
            "cached": bool(cached),
            "created_at": now_iso(),
        }
        with self.lock:
            cache[cache_id] = entry
        return entry

    def file_preview_entry(self, cache_id: str) -> dict[str, Any]:
        cache = self.ensure_file_preview_cache()
        with self.lock:
            entry = copy.deepcopy(cache.get(str(cache_id or "").strip()) or {})
        if not entry:
            raise ValueError("预览缓存不存在或已失效。")
        local_path = Path(str(entry.get("local_path") or "")).expanduser()
        if not local_path.exists() or not local_path.is_file():
            raise ValueError("预览缓存文件不存在。")
        entry["local_path"] = str(local_path.resolve())
        return entry

    def prune_preview_cache_index(self) -> int:
        removed = 0
        with self.lock:
            stale_ids = []
            for cache_id, entry in self.file_preview_cache.items():
                if not entry.get("cached"):
                    continue
                local_path = Path(str(entry.get("local_path") or ""))
                if not local_path.exists() or not is_under_preview_cache(local_path):
                    stale_ids.append(cache_id)
            for cache_id in stale_ids:
                self.file_preview_cache.pop(cache_id, None)
                removed += 1
        return removed

    def preview_cache_status(self) -> dict[str, Any]:
        stats = preview_cache_disk_stats()
        with self.lock:
            memory_cached = sum(1 for entry in self.file_preview_cache.values() if entry.get("cached"))
        settings = load_preview_cache_settings()
        return {
            **stats,
            "settings": settings,
            "memory_cached_entries": memory_cached,
        }

    def update_preview_cache_settings(self, body: dict[str, Any]) -> dict[str, Any]:
        settings = save_preview_cache_settings(body or {})
        return {"settings": settings, **self.preview_cache_status()}

    def cleanup_preview_cache_manual(self) -> dict[str, Any]:
        result = cleanup_preview_cache(remove_all=True)
        self.prune_preview_cache_index()
        return {**result, **self.preview_cache_status()}

    def maybe_auto_cleanup_preview_cache(self, *, force: bool = False) -> dict[str, Any] | None:
        settings = load_preview_cache_settings()
        max_age_hours = int(settings.get("max_age_hours") or 0)
        max_size_mib = int(settings.get("max_size_mib") or 0)
        if max_age_hours <= 0 and max_size_mib <= 0:
            return None
        now = time.time()
        if not force and now - float(getattr(self, "last_preview_cache_cleanup", 0.0) or 0.0) < 300:
            return None
        self.last_preview_cache_cleanup = now
        result = cleanup_preview_cache(max_age_hours=max_age_hours, max_size_mib=max_size_mib)
        self.prune_preview_cache_index()
        return result

    def fetch_file_preview(
        self,
        server_id: str | None,
        path_text: str = "",
        limit_bytes: int = 131072,
    ) -> dict[str, Any]:
        server = self.server_by_id(server_id or "")
        source_path = str(path_text or "").strip()
        if not source_path:
            raise ValueError("请选择要预览的文件。")
        if not server or server.mode == "local":
            local_path = resolve_local_browser_target(source_path)
            if local_path.is_dir():
                raise ValueError("当前路径是目录，请选择文件。")
            resolved_server_id = server.id if server else "local"
            cached = False
        else:
            cache_dir = FILE_PREVIEW_CACHE_DIR / uuid.uuid4().hex
            local_path = download_remote_file_to_local(
                server,
                source_path,
                cache_dir,
                timeout=max(30, self.config.remote_timeout_seconds + 30),
            )
            if local_path.is_dir():
                raise ValueError("当前路径是目录，请选择文件。")
            resolved_server_id = server.id
            cached = True
        mime_type = guess_file_mime_type(str(local_path))
        preview_kind = preview_kind_for_path(str(local_path), mime_type)
        registered = self.register_file_preview(
            source_path=source_path,
            local_path=local_path.resolve(),
            server_id=resolved_server_id,
            mime_type=mime_type,
            preview_kind=preview_kind,
            cached=cached,
        )
        file_info = file_entry(local_path.resolve())
        payload = {
            "cache_id": registered["cache_id"],
            "cached": cached,
            "created_at": registered["created_at"],
            "download_url": f"/api/files/cache/{registered['cache_id']}?download=1",
            "inline_supported": preview_kind in {"text", "image", "pdf", "audio", "video"},
            "local_path": str(local_path.resolve()),
            "mime_type": mime_type,
            "name": file_info["name"],
            "path": source_path,
            "preview_kind": preview_kind,
            "preview_url": f"/api/files/cache/{registered['cache_id']}",
            "server_id": resolved_server_id,
            "size": file_info["size"],
            "size_text": file_info["size_text"],
            "mtime": file_info["mtime"],
        }
        if preview_kind == "text":
            text_payload = read_local_text_file(str(local_path.resolve()), limit_bytes=limit_bytes)
            payload["text"] = text_payload["text"]
            payload["encoding"] = text_payload["encoding"]
            payload["truncated"] = bool(text_payload["truncated"])
        if cached:
            self.maybe_auto_cleanup_preview_cache()
        return payload

    def reload_config(self) -> None:
        config = load_config(self.config_path)
        with self.lock:
            self.config = config
            self.servers = config.servers

    def refresh_status(self) -> None:
        self.reload_config()
        with self.lock:
            servers = list(self.servers)
            config = self.config
            previous_statuses = copy.deepcopy(self.statuses)
        statuses = collect_all(servers, config, previous_statuses=previous_statuses)
        refreshed_at = time.time()
        with self.lock:
            self.statuses = statuses
            self.last_refresh = refreshed_at
            self.last_refreshed_at = iso_at(refreshed_at)

    def refresh_server_status(self, server_id: str) -> dict[str, Any]:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        self.reload_config()
        with self.lock:
            server = self.server_by_id(server_id)
            config = self.config
        if not server:
            raise ValueError("server not found")
        status = collect_server(server, config)
        refreshed_at = time.time()
        with self.lock:
            existing = [item for item in self.statuses if str(item.get("id") or "") != server_id]
            order = {server_config.id: index for index, server_config in enumerate(self.servers)}
            existing.append(status)
            existing.sort(key=lambda item: order.get(str(item.get("id") or ""), 9999))
            self.statuses = existing
            self.last_refresh = refreshed_at
            self.last_refreshed_at = iso_at(refreshed_at)
        return status

    def workspace_public_payload(self, workspace: dict[str, Any]) -> dict[str, Any]:
        payload = apply_workspace_job_runtime(workspace, getattr(self, "jobs", []))
        payload["execution"] = derive_workspace_execution_state(payload, getattr(self, "jobs", []))
        payload["automation"] = derive_workspace_automation_state(
            payload,
            payload["execution"],
            getattr(self, "statuses", []),
        )
        return payload

    def workflow_template_public_payload(self, template: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(template)
        snapshot = build_template_snapshot(payload, self.agent_definitions, self.tool_definitions)
        payload["agent_ids"] = [str(item.get("id") or "").strip() for item in snapshot.get("agents", []) if str(item.get("id") or "").strip()]
        payload["tool_ids"] = [str(item.get("id") or "").strip() for item in snapshot.get("tools", []) if str(item.get("id") or "").strip()]
        payload["node_count"] = len(payload.get("nodes")) if isinstance(payload.get("nodes"), list) else 0
        payload["agent_count"] = len(payload["agent_ids"])
        payload["tool_count"] = len(payload["tool_ids"])
        return payload

    def status_payload(self) -> dict[str, Any]:
        with self.lock:
            workspaces = [
                self.workspace_public_payload(item)
                for item in sorted(self.workspaces, key=workspace_sort_key, reverse=True)
            ]
            workflow_templates = [
                self.workflow_template_public_payload(item)
                for item in sorted(getattr(self, "workflow_templates", []), key=workflow_template_sort_key, reverse=True)
            ]
            return {
                "config": self.public_config(),
                "refreshed_at": self.last_refreshed_at,
                "status_age_seconds": round(max(time.time() - self.last_refresh, 0), 1),
                "servers": self.statuses,
                "jobs": self.jobs,
                "workspaces": workspaces,
                "workflow_templates": workflow_templates,
                "agent_definitions": copy.deepcopy(getattr(self, "agent_definitions", [])),
                "tool_definitions": copy.deepcopy(getattr(self, "tool_definitions", [])),
            }

    def save_jobs(self) -> None:
        with self.lock:
            write_json(JOBS_PATH, self.jobs)

    def save_workspaces(self) -> None:
        with self.lock:
            write_json(WORKSPACES_PATH, self.workspaces)

    def save_provider_profiles(self) -> None:
        with self.lock:
            write_json(PROVIDER_PROFILES_PATH, self.provider_profiles)

    def save_workflow_templates(self) -> None:
        with self.lock:
            write_json(WORKFLOW_TEMPLATES_PATH, self.workflow_templates)

    def save_agent_definitions(self) -> None:
        with self.lock:
            write_json(AGENT_DEFINITIONS_PATH, self.agent_definitions)

    def save_tool_definitions(self) -> None:
        with self.lock:
            write_json(TOOL_DEFINITIONS_PATH, self.tool_definitions)

    def tool_definition_by_id(self, tool_id: str) -> dict[str, Any] | None:
        return next((item for item in self.tool_definitions if str(item.get("id") or "") == str(tool_id)), None)

    def agent_definition_by_id(self, agent_id: str) -> dict[str, Any] | None:
        return next((item for item in self.agent_definitions if str(item.get("id") or "") == str(agent_id)), None)

    def workflow_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        return next((item for item in self.workflow_templates if str(item.get("id") or "") == str(template_id)), None)

    def list_tool_definitions(self) -> dict[str, Any]:
        with self.lock:
            return {"tool_definitions": copy.deepcopy(self.tool_definitions)}

    def list_agent_definitions(self) -> dict[str, Any]:
        with self.lock:
            return {"agent_definitions": copy.deepcopy(self.agent_definitions)}

    def list_workflow_templates(self) -> dict[str, Any]:
        with self.lock:
            items = [
                self.workflow_template_public_payload(item)
                for item in sorted(self.workflow_templates, key=workflow_template_sort_key, reverse=True)
            ]
        return {"workflow_templates": items}

    def create_tool_definition(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool = normalize_global_tool_definition(payload, index=len(self.tool_definitions))
        with self.lock:
            self.tool_definitions.insert(0, tool)
        self.save_tool_definitions()
        return tool

    def update_tool_definition(self, tool_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        tool_id = str(tool_id or "").strip()
        with self.lock:
            current = self.tool_definition_by_id(tool_id)
            if not current:
                raise ValueError("tool definition not found")
            updated = normalize_global_tool_definition({**current, **payload}, existing=current)
            index = next((idx for idx, item in enumerate(self.tool_definitions) if str(item.get("id") or "") == tool_id), -1)
            if index < 0:
                raise ValueError("tool definition not found")
            previous_id = str(current.get("id") or "").strip()
            self.tool_definitions[index] = updated
            if updated["id"] != previous_id:
                for agent in self.agent_definitions:
                    tools = parse_tag_list(agent.get("tools", []))
                    agent["tools"] = [updated["id"] if item == previous_id else item for item in tools]
                self.agent_definitions = normalize_global_agent_definitions(
                    self.agent_definitions,
                    existing=self.agent_definitions,
                    tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
                )
        self.save_tool_definitions()
        self.save_agent_definitions()
        return updated

    def delete_tool_definition(self, tool_id: str) -> None:
        tool_id = str(tool_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.tool_definitions) if str(item.get("id") or "") == tool_id), -1)
            if index < 0:
                raise ValueError("tool definition not found")
            del self.tool_definitions[index]
            for agent in self.agent_definitions:
                agent["tools"] = [item for item in parse_tag_list(agent.get("tools", [])) if item != tool_id]
        self.save_tool_definitions()
        self.save_agent_definitions()

    def create_agent_definition(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool_ids = [str(item.get("id") or "").strip() for item in self.tool_definitions]
        agent = normalize_global_agent_definition(payload, index=len(self.agent_definitions), tool_ids=tool_ids)
        with self.lock:
            self.agent_definitions.insert(0, agent)
        self.save_agent_definitions()
        return agent

    def update_agent_definition(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(agent_id or "").strip()
        tool_ids = [str(item.get("id") or "").strip() for item in self.tool_definitions]
        with self.lock:
            current = self.agent_definition_by_id(agent_id)
            if not current:
                raise ValueError("agent definition not found")
            updated = normalize_global_agent_definition({**current, **payload}, existing=current, tool_ids=tool_ids)
            index = next((idx for idx, item in enumerate(self.agent_definitions) if str(item.get("id") or "") == agent_id), -1)
            if index < 0:
                raise ValueError("agent definition not found")
            previous_id = str(current.get("id") or "").strip()
            self.agent_definitions[index] = updated
            if updated["id"] != previous_id:
                for template in self.workflow_templates:
                    nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
                        if str(handler.get("agent_id") or "").strip() != previous_id:
                            continue
                        handler["agent_id"] = updated["id"]
                        handler["name"] = updated["name"]
                        node["handler"] = handler
                    model = template.get("model") if isinstance(template.get("model"), dict) else {}
                    if str(model.get("chat_agent_id") or "").strip() == previous_id:
                        model["chat_agent_id"] = updated["id"]
                        template["model"] = model
        self.save_agent_definitions()
        self.save_workflow_templates()
        return updated

    def delete_agent_definition(self, agent_id: str) -> None:
        agent_id = str(agent_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.agent_definitions) if str(item.get("id") or "") == agent_id), -1)
            if index < 0:
                raise ValueError("agent definition not found")
            del self.agent_definitions[index]
            for template in self.workflow_templates:
                nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
                    if str(handler.get("agent_id") or "").strip() != agent_id:
                        continue
                    handler["agent_id"] = ""
                    node["handler"] = handler
                model = template.get("model") if isinstance(template.get("model"), dict) else {}
                if str(model.get("chat_agent_id") or "").strip() == agent_id:
                    model["chat_agent_id"] = ""
                    template["model"] = model
        self.save_agent_definitions()
        self.save_workflow_templates()

    def create_workflow_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = normalize_workflow_template(
            payload,
            agent_definitions=self.agent_definitions,
            tool_definitions=self.tool_definitions,
        )
        with self.lock:
            self.workflow_templates.insert(0, template)
        self.save_workflow_templates()
        return self.workflow_template_public_payload(template)

    def update_workflow_template(self, template_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        template_id = str(template_id or "").strip()
        with self.lock:
            current = self.workflow_template_by_id(template_id)
            if not current:
                raise ValueError("workflow template not found")
            merged = dict(current)
            merged.update(payload)
            updated = normalize_workflow_template(
                merged,
                existing=current,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
            )
            index = next((idx for idx, item in enumerate(self.workflow_templates) if str(item.get("id") or "") == template_id), -1)
            if index < 0:
                raise ValueError("workflow template not found")
            self.workflow_templates[index] = updated
        self.save_workflow_templates()
        return self.workflow_template_public_payload(updated)

    def delete_workflow_template(self, template_id: str) -> None:
        template_id = str(template_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workflow_templates) if str(item.get("id") or "") == template_id), -1)
            if index < 0:
                raise ValueError("workflow template not found")
            del self.workflow_templates[index]
        self.save_workflow_templates()

    def provider_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        return next((item for item in self.provider_profiles if str(item.get("id")) == str(profile_id)), None)

    def list_provider_profiles(self) -> dict[str, Any]:
        """List all provider profiles (API keys masked)."""
        with self.lock:
            items = []
            for profile in self.provider_profiles:
                public_profile = dict(profile)
                # Mask API key for security
                api_key = str(public_profile.get("api_key") or "")
                if api_key:
                    public_profile["api_key_masked"] = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    del public_profile["api_key"]
                items.append(public_profile)
        return {"provider_profiles": items}

    def create_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new provider profile."""
        profile_id = str(payload.get("id") or uuid.uuid4().hex[:8]).strip()
        name = str(payload.get("name") or "").strip()
        provider = str(payload.get("provider") or "openai").strip()
        base_url = str(payload.get("base_url") or "").strip()
        api_key = str(payload.get("api_key") or "").strip()
        models = payload.get("models") if isinstance(payload.get("models"), list) else []
        is_default = bool(payload.get("is_default"))

        if not name:
            name = f"{provider.title()} Profile"

        profile: dict[str, Any] = {
            "id": profile_id,
            "name": name,
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "models": models,
            "is_default": is_default,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

        # If this is default, unset other defaults
        if is_default:
            for p in self.provider_profiles:
                p["is_default"] = False

        with self.lock:
            self.provider_profiles.append(profile)
        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        return result

    def update_provider_profile(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            profile = self.provider_profile_by_id(profile_id)
            if not profile:
                raise ValueError("provider profile not found")

            # Update fields
            if "name" in payload:
                profile["name"] = str(payload["name"] or "").strip()
            if "provider" in payload:
                profile["provider"] = str(payload["provider"] or "openai").strip()
            if "base_url" in payload:
                profile["base_url"] = str(payload["base_url"] or "").strip()
            if "api_key" in payload and payload["api_key"]:
                profile["api_key"] = str(payload["api_key"] or "").strip()
            if "models" in payload:
                profile["models"] = payload["models"] if isinstance(payload["models"], list) else []
            if "is_default" in payload:
                is_default = bool(payload["is_default"])
                if is_default:
                    for p in self.provider_profiles:
                        p["is_default"] = False
                profile["is_default"] = is_default

            profile["updated_at"] = now_iso()

        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        return result

    def delete_provider_profile(self, profile_id: str) -> None:
        """Delete a provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.provider_profiles) if item.get("id") == profile_id), -1)
            if index < 0:
                raise ValueError("provider profile not found")
            del self.provider_profiles[index]
        self.save_provider_profiles()

    def workspace_by_id(self, workspace_id: str) -> dict[str, Any] | None:
        return next((item for item in self.workspaces if str(item.get("id")) == str(workspace_id)), None)

    def list_workspaces(self) -> dict[str, Any]:
        with self.lock:
            items = [
                self.workspace_public_payload(item)
                for item in sorted(self.workspaces, key=workspace_sort_key, reverse=True)
            ]
        return {"workspaces": items}

    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        requested_payload = payload if isinstance(payload, dict) else {}
        template_id = str(requested_payload.get("template_id") or "").strip()
        has_template_inputs = "inputs" in requested_payload or any(
            key in requested_payload
            for key in ("goal_text", "repo_urls", "paper_urls", "context_blocks", "source_mode")
        )
        workflow_templates = getattr(self, "workflow_templates", [])
        if template_id or (has_template_inputs and workflow_templates):
            with self.lock:
                template = self.workflow_template_by_id(template_id) if template_id else None
                if not template:
                    template = workflow_templates[0] if workflow_templates else None
                if not template:
                    raise ValueError("workflow template not found")
                workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=template,
                    agent_definitions=getattr(self, "agent_definitions", workspace_default_agents()),
                    tool_definitions=getattr(self, "tool_definitions", workspace_default_tools()),
                )
        else:
            workspace = normalize_workspace_payload(requested_payload)
        with self.lock:
            self.workspaces.insert(0, workspace)
        self.save_workspaces()
        with self.lock:
            return self.workspace_public_payload(workspace)

    def update_workspace(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            requested_payload = payload if isinstance(payload, dict) else {}
            merged = dict(current)
            merged.update(requested_payload)
            if str(current.get("template_id") or "").strip() or isinstance(current.get("template_snapshot"), dict):
                updated = normalize_workspace_payload(merged, existing=current)
                updated["template_id"] = str(merged.get("template_id") or current.get("template_id") or "").strip()
                updated["template_name"] = str(merged.get("template_name") or current.get("template_name") or "").strip()
                updated["template_snapshot"] = copy.deepcopy(
                    merged.get("template_snapshot")
                    if isinstance(merged.get("template_snapshot"), dict)
                    else current.get("template_snapshot")
                    if isinstance(current.get("template_snapshot"), dict)
                    else {}
                )
                updated["inputs"] = normalize_workspace_inputs(
                    merged.get("inputs") if isinstance(merged.get("inputs"), dict) else merged,
                    existing=current.get("inputs"),
                )
                updated["execution"] = copy.deepcopy(
                    merged.get("execution")
                    if isinstance(merged.get("execution"), dict)
                    else current.get("execution")
                    if isinstance(current.get("execution"), dict)
                    else {}
                )
            else:
                updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
        self.save_workspaces()
        with self.lock:
            return self.workspace_public_payload(updated)

    def apply_workspace_automation_defaults(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        force = workspace_payload_bool(requested_payload, "force", False)
        apply_defaults = workspace_payload_bool(requested_payload, "apply_defaults", True)
        apply_evidence = workspace_payload_bool(requested_payload, "apply_evidence", True)
        scheduler_candidate = requested_payload.get("scheduler_candidate")
        if not isinstance(scheduler_candidate, dict):
            scheduler_candidate = None
        backfill_item = requested_payload.get("backfill_item")
        if not isinstance(backfill_item, dict):
            backfill_item = None
        evidence_applied: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            if apply_defaults:
                updated, applied = apply_workspace_automation_defaults_to_payload(
                    current,
                    statuses_snapshot,
                    force=force,
                    scheduler_candidate=scheduler_candidate,
                )
            else:
                updated, applied = copy.deepcopy(current), []
            if backfill_item:
                updated, evidence_applied = apply_workspace_evidence_backfill_item_to_payload(
                    updated,
                    jobs_snapshot,
                    backfill_item,
                    statuses=statuses_snapshot,
                    force=force,
                )
                applied.extend(evidence_applied)
            elif apply_evidence:
                updated, evidence_applied = apply_workspace_discovery_evidence_to_payload(
                    updated,
                    jobs_snapshot,
                    force=force,
                )
                applied.extend(evidence_applied)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
        self.save_workspaces()
        with self.lock:
            return {
                "workspace": self.workspace_public_payload(updated),
                "applied": applied,
                "evidence_applied": evidence_applied,
            }

    def run_workspace_discovery(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        apply_defaults = bool(requested_payload.get("apply_defaults", True))
        include_source_raw = requested_payload.get("include_source", requested_payload.get("bootstrap_source", True))
        include_source = (
            include_source_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(include_source_raw, str)
            else bool(include_source_raw)
        )
        force = bool(requested_payload.get("force") or False)
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            workspace = copy.deepcopy(current)
            if apply_defaults:
                workspace, applied = apply_workspace_automation_defaults_to_payload(
                    workspace,
                    getattr(self, "statuses", []),
                    force=force,
                )
                index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                if index < 0:
                    raise ValueError("workspace not found")
                self.workspaces[index] = workspace
        if apply_defaults:
            self.save_workspaces()

        nodes: list[dict[str, Any]] = []
        source_bootstrap_queued = False
        workspace_nodes = [
            node for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(node, dict)
        ]
        clone_node = next((node for node in workspace_nodes if str(node.get("kind") or "").strip() == "repo.clone"), None)
        if clone_node and include_source:
            node = clone_node
            kind = "repo.clone"
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
            repo_url = str(config.get("repo_url") or source.get("repo_url") or "").strip()
            should_queue_clone = bool(repo_url and workspace_dir)
            if not should_queue_clone:
                skipped.append(
                    {
                        "node_id": str(node.get("id") or "").strip(),
                        "node_kind": kind,
                        "reason": "repo_url or workspace_dir missing",
                    }
                )
            else:
                target = Path(workspace_dir).expanduser()
                if target.exists():
                    if not target.is_dir():
                        should_queue_clone = False
                        skipped.append(
                            {
                                "node_id": str(node.get("id") or "").strip(),
                                "node_kind": kind,
                                "reason": "workspace_dir exists but is not a directory",
                            }
                        )
                    else:
                        try:
                            has_files = any(target.iterdir())
                        except OSError:
                            should_queue_clone = False
                            skipped.append(
                                {
                                    "node_id": str(node.get("id") or "").strip(),
                                    "node_kind": kind,
                                    "reason": "workspace_dir cannot be inspected",
                                }
                            )
                        else:
                            if has_files:
                                should_queue_clone = False
                if should_queue_clone:
                    nodes.append(node)
                    source_bootstrap_queued = True

        for node in workspace_nodes:
            kind = str(node.get("kind") or "").strip()
            if kind == "repo.clone" or kind not in WORKSPACE_DISCOVERY_NODE_KINDS:
                continue
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            if kind == "repo.inspect":
                target = Path(workspace_dir).expanduser() if workspace_dir else None
                if not workspace_dir:
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir missing",
                        }
                    )
                    continue
                if not source_bootstrap_queued and (not target or not target.exists()):
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir does not exist yet",
                        }
                    )
                    continue
                if target and target.exists() and not target.is_dir():
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir is not a directory",
                        }
                    )
                    continue
            nodes.append(node)
        if not nodes:
            raise ValueError("workspace has no discovery nodes")

        jobs: list[dict[str, Any]] = []
        previous_job_id = ""
        for index, node in enumerate(nodes):
            job_payload = self.workspace_node_job_payload(workspace, node, previous_job_id=previous_job_id)
            job_payload["wait_for_idle"] = True
            metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
            metadata["workflow_phase"] = "discovery"
            metadata["discovery_index"] = index
            job_payload["metadata"] = metadata
            job = self.create_job(job_payload)
            jobs.append(job)
            previous_job_id = str(job.get("id") or "")

        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        return {
            "workspace": payload_workspace,
            "jobs": jobs,
            "applied": applied,
            "skipped": skipped,
        }

    def advance_workspace_automation(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        force_run = bool(requested_payload.get("force_run") or False)
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            workspace_job_ids = {
                str(job.get("id") or "").strip()
                for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
            }
            active_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and str(job.get("status") or "") in {"queued", "blocked", "starting", "running"}
            ]
            failed_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and str(job.get("status") or "") in {"failed", "stopped"}
            ]
            discovery_jobs = [
                job for job in jobs_snapshot
                if workspace_job_binding(job)[0] == workspace_id
                and (
                    str((job.get("metadata") if isinstance(job.get("metadata"), dict) else {}).get("workflow_phase") or "") == "discovery"
                    or str((job.get("metadata") if isinstance(job.get("metadata"), dict) else {}).get("node_kind") or "") in WORKSPACE_DISCOVERY_NODE_KINDS
                )
            ]
            public_workspace = self.workspace_public_payload(current)

        if active_jobs:
            return {
                "action": "watch",
                "message": "已有任务在队列或运行中，先观察当前执行。",
                "decision": workspace_advance_decision(
                    "watch",
                    "观察当前任务",
                    f"{len(active_jobs)} 个任务仍在等待、启动或运行，继续提交会让状态变乱。",
                    "打开第一个活跃任务日志，等它完成后再自动推进。",
                    status="running",
                ),
                "workspace": public_workspace,
                "jobs": [],
                "active_job_ids": [str(job.get("id") or "").strip() for job in active_jobs if str(job.get("id") or "").strip()],
            }

        if failed_jobs and not force_run:
            return {
                "action": "review_failed",
                "message": "存在失败或停止的任务，先查看输出再继续自动推进。",
                "decision": workspace_advance_decision(
                    "review_failed",
                    "复查失败任务",
                    f"{len(failed_jobs)} 个任务失败或停止，继续自动运行前需要确认失败原因。",
                    "打开失败任务日志，修正节点配置或使用 force_run 明确继续。",
                    status="failed",
                ),
                "workspace": public_workspace,
                "jobs": [],
                "failed_job_ids": [str(job.get("id") or "").strip() for job in failed_jobs[:8] if str(job.get("id") or "").strip()],
            }

        if not workspace_job_ids or not discovery_jobs:
            result = self.run_workspace_discovery(
                workspace_id,
                {
                    "apply_defaults": True,
                    "include_source": True,
                },
            )
            result["action"] = "discover"
            result["message"] = "已提交安全自动发现链。"
            result["decision"] = workspace_advance_decision(
                "discover",
                "提交安全发现",
                "当前实例还没有可用的 discovery 记录，先收集路径、数据、环境、GPU 和产物入口。",
                "等待发现链完成后再次点击自动推进，系统会回填证据并尝试完整运行。",
                status="running",
            )
            return result

        apply_result = self.apply_workspace_automation_defaults(
            workspace_id,
            {
                "apply_evidence": True,
            },
        )
        workspace_after_apply = apply_result.get("workspace") if isinstance(apply_result.get("workspace"), dict) else public_workspace
        applied = apply_result.get("applied") if isinstance(apply_result.get("applied"), list) else []
        evidence_applied = apply_result.get("evidence_applied") if isinstance(apply_result.get("evidence_applied"), list) else []

        automation = workspace_after_apply.get("automation") if isinstance(workspace_after_apply.get("automation"), dict) else {}
        blocked_checks = workspace_workflow_blocking_checks(automation)
        if blocked_checks and not force_run:
            blocked_labels = [
                str(item.get("label") or item.get("title") or item.get("id") or "").strip()
                for item in blocked_checks
                if isinstance(item, dict)
            ]
            return {
                "action": "blocked",
                "message": workspace_readiness_message(blocked_checks),
                "decision": workspace_advance_decision(
                    "blocked",
                    "运行门禁阻塞",
                    "已回填建议和发现证据，但仍有硬阻塞：" + "、".join([item for item in blocked_labels if item][:5]),
                    "按阻塞项补齐节点链、Agent 归属或运行命令后再次自动推进。",
                    status="blocked",
                ),
                "workspace": workspace_after_apply,
                "jobs": [],
                "applied": applied,
                "evidence_applied": evidence_applied,
                "blocked_checks": blocked_checks,
            }

        try:
            run_result = self.run_workspace_workflow(
                workspace_id,
                {
                    "auto_apply": True,
                    "apply_evidence": True,
                    "force": force_run,
                },
            )
        except WorkspaceWorkflowReadinessError as exc:
            blocked_labels = [
                str(item.get("label") or item.get("title") or item.get("id") or "").strip()
                for item in exc.blocked_checks
                if isinstance(item, dict)
            ]
            return {
                "action": "blocked",
                "message": str(exc),
                "decision": workspace_advance_decision(
                    "blocked",
                    "运行门禁阻塞",
                    "提交前最终检查未通过：" + "、".join([item for item in blocked_labels if item][:5]),
                    "按阻塞项修正配置，再次点击自动推进。",
                    status="blocked",
                ),
                "workspace": exc.workspace or workspace_after_apply,
                "jobs": [],
                "applied": exc.applied or applied,
                "evidence_applied": exc.evidence_applied or evidence_applied,
                "blocked_checks": exc.blocked_checks,
            }

        run_result["action"] = "run"
        run_result["message"] = "已完成回填并提交完整工作流。"
        run_applied = run_result.get("applied") if isinstance(run_result.get("applied"), list) else []
        run_evidence_applied = run_result.get("evidence_applied") if isinstance(run_result.get("evidence_applied"), list) else []
        run_result["applied"] = applied + run_applied
        run_result["evidence_applied"] = evidence_applied + run_evidence_applied
        run_result["decision"] = workspace_advance_decision(
            "run",
            "提交完整运行",
            f"门禁已通过，已整理 {len(run_result['applied'])} 项建议/发现，可以进入完整执行链。",
            "跟踪第一个运行任务输出，后续产物和指标会继续回到驾驶舱。",
            status="running",
        )
        return run_result

    def debug_agent_definition(self, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        requested_agent_id = safe_id(str(agent_id or "").strip()) if str(agent_id or "").strip() else ""
        requested_payload = payload if isinstance(payload, dict) else {}
        template_id = str(requested_payload.get("template_id") or "").strip()
        input_text = str(requested_payload.get("input") or requested_payload.get("text") or "").strip()
        requested_node_kind = str(requested_payload.get("node_kind") or "").strip()
        requested_tool_ids = parse_tag_list(requested_payload.get("tool_ids", []))
        execute_llm = bool(requested_payload.get("execute_llm") or False)

        with self.lock:
            agent = self.agent_definition_by_id(requested_agent_id)
            if not agent:
                raise ValueError("agent definition not found")
            template = self.workflow_template_by_id(template_id) if template_id else None
            if template:
                preview_workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=template,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
            else:
                inputs = normalize_workspace_inputs(
                    requested_payload.get("inputs") if isinstance(requested_payload.get("inputs"), dict) else requested_payload
                )
                debug_source_type = source_type_for_chain(inputs.get("source_mode") or "idea")
                template_payload = {
                    "id": f"debug-{requested_agent_id or 'agent'}",
                    "name": str(requested_payload.get("template_name") or "Agent 调试预览").strip() or "Agent 调试预览",
                    "brief": str(requested_payload.get("brief") or inputs.get("goal_text") or f"调试 {agent.get('name') or requested_agent_id}").strip(),
                    "source_type": inputs.get("source_mode") or "idea",
                    "repo_url": parse_line_list(inputs.get("repo_urls", []))[0] if parse_line_list(inputs.get("repo_urls", [])) else "",
                    "paper_url": parse_line_list(inputs.get("paper_urls", []))[0] if parse_line_list(inputs.get("paper_urls", [])) else "",
                    "idea_text": str(inputs.get("goal_text") or requested_payload.get("brief") or "").strip(),
                    "references": parse_line_list(inputs.get("references", [])),
                    "workspace_dir": str(requested_payload.get("workspace_dir") or "").strip(),
                    "env_name": str(requested_payload.get("env_name") or "").strip(),
                    "env_manager": str(requested_payload.get("env_manager") or "conda").strip() or "conda",
                    "python_version": str(requested_payload.get("python_version") or "").strip(),
                    "model": {
                        "chat_agent_id": requested_agent_id,
                        "provider_profile_id": str(requested_payload.get("provider_profile_id") or "").strip(),
                        "routing_mode": str(requested_payload.get("routing_mode") or "agent_override").strip() or "agent_override",
                    },
                    "nodes": [
                        {
                            "id": "debug-node",
                            "kind": requested_node_kind or f"source.{debug_source_type}",
                            "title": str(requested_payload.get("node_title") or "调试节点").strip() or "调试节点",
                            "handler": {
                                "agent_id": requested_agent_id,
                                "name": str(agent.get("name") or requested_agent_id).strip(),
                            },
                            "config": {
                                "goal": str(requested_payload.get("node_goal") or inputs.get("goal_text") or "").strip(),
                            },
                        }
                    ],
                }
                debug_template = normalize_workflow_template(
                    template_payload,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
                preview_workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=debug_template,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )

            preview_workspace["agents"] = copy.deepcopy(self.agent_definitions)
            preview_workspace["tools"] = copy.deepcopy(self.tool_definitions)
            model = normalize_workspace_model(preview_workspace.get("model"), existing=preview_workspace.get("model"))
            if requested_payload.get("provider_profile_id"):
                model["provider_profile_id"] = str(requested_payload.get("provider_profile_id") or "").strip()
            if requested_payload.get("routing_mode"):
                model["routing_mode"] = str(requested_payload.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            if not str(model.get("chat_agent_id") or "").strip():
                model["chat_agent_id"] = requested_agent_id
            preview_workspace["model"] = model
            preview_workspace["chat"] = normalize_workspace_chat(
                requested_payload.get("chat") if "chat" in requested_payload else preview_workspace.get("chat"),
                existing=preview_workspace.get("chat"),
            )
            preview_workspace_public = self.workspace_public_payload(preview_workspace)

        debug = build_workspace_agent_debug(
            preview_workspace_public,
            agent,
            input_text=input_text,
            requested_node_kind=requested_node_kind,
            requested_tool_ids=requested_tool_ids,
        )
        result = {
            "debug": debug,
            "workspace": preview_workspace_public,
            "agent_definition": copy.deepcopy(agent),
        }

        if execute_llm and input_text:
            model_config = preview_workspace_public.get("model") if isinstance(preview_workspace_public.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id

            if effective_profile_id:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    tool_map = {
                        t.get("id"): t
                        for t in preview_workspace_public.get("tools", [])
                        if isinstance(t, dict) and t.get("id")
                    }
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map and (not requested_tool_ids or tid in requested_tool_ids)
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace_public,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                    )
                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                    )
                    execution_result = executor.run(input_text, context={
                        "workspace_id": str(preview_workspace_public.get("id") or "").strip(),
                        "workspace_name": preview_workspace_public.get("name", ""),
                        "source_type": preview_workspace_public.get("source", {}).get("type", ""),
                    })
                    result["execution"] = execution_result.to_dict()
                else:
                    result["execution"] = {
                        "success": False,
                        "error": "Provider profile not found or API key not configured",
                        "final_answer": "",
                    }
            else:
                result["execution"] = {
                    "success": False,
                    "error": "No provider profile configured for this agent/template",
                    "final_answer": "",
                }

        return result

    def delete_workspace(self, workspace_id: str) -> None:
        """Delete a workspace by ID."""
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            del self.workspaces[index]
        self.save_workspaces()

    def workspace_node_job_payload(
        self,
        workspace: dict[str, Any],
        node: dict[str, Any],
        *,
        previous_job_id: str = "",
        automation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kind = str(node.get("kind") or "").strip()
        if kind not in WORKSPACE_EXECUTABLE_NODE_KINDS:
            raise ValueError("node kind is not executable yet")
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
        workspace_source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
        workspace_recipe = workspace.get("recipes") if isinstance(workspace.get("recipes"), list) and workspace.get("recipes") else []
        recipe = workspace_recipe[0] if workspace_recipe and isinstance(workspace_recipe[0], dict) else {}

        command = ""
        name_suffix = str(node.get("title") or kind).strip() or kind
        workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
        if kind == "run.command":
            command = str(config.get("run_command") or "").strip()
        elif kind == "env.prepare":
            command = str(config.get("setup_command") or recipe.get("setup_command") or "").strip()
        elif kind == "eval.report":
            command = str(config.get("report_command") or recipe.get("report_command") or "").strip()
        elif kind == "repo.clone":
            repo_url = str(config.get("repo_url") or workspace_source.get("repo_url") or "").strip()
            repo_ref = str(config.get("repo_ref") or workspace_source.get("repo_ref") or "").strip()
            if repo_url and workspace_dir:
                parent_dir = os.path.dirname(workspace_dir.rstrip("/")) or "."
                clone_name = os.path.basename(workspace_dir.rstrip("/")) or workspace_dir.rstrip("/")
                clone_parts = ["git", "clone"]
                if repo_ref:
                    clone_parts.extend(["--branch", shlex.quote(repo_ref)])
                clone_parts.extend([shlex.quote(repo_url), shlex.quote(clone_name)])
                command = f"mkdir -p {shlex.quote(parent_dir)} && cd {shlex.quote(parent_dir)} && " + " ".join(clone_parts)
            else:
                command = (
                    "echo "
                    + shlex.quote("[repo.clone] repo_url or workspace_dir missing; waiting for upstream research output")
                )
        elif kind == "path.resolve":
            data_roots = str(config.get("data_roots") or "").strip()
            output_roots = str(config.get("output_roots") or "runs\noutputs\ncheckpoints\nlogs").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
data_roots = {json.dumps(data_roots)}
output_roots = {json.dumps(output_roots)}

root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())
print("workspace_exists:", root.exists())

for label, raw in [("data_root", data_roots), ("output_root", output_roots)]:
    values = [item.strip() for item in raw.replace(",", "\\n").splitlines() if item.strip()]
    if not values:
        print(f"{{label}}: none")
        continue
    for value in values[:20]:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        print(f"{{label}}: {{path.resolve()}} exists={{path.exists()}}")
PY"""
        elif kind == "dataset.find":
            query = str(config.get("query") or workspace_source.get("paper_url") or workspace_source.get("repo_url") or workspace.get("brief") or "").strip()
            dataset_hints = str(config.get("dataset_hints") or "").strip()
            data_roots = str(config.get("data_roots") or "").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

query = {json.dumps(query)}
dataset_hints = {json.dumps(dataset_hints)}
data_roots = {json.dumps(data_roots)}

terms = [part.lower() for part in query.replace("/", " ").replace("_", " ").replace("-", " ").split() if len(part) >= 3]
roots = [item.strip() for item in (data_roots + "\\n" + dataset_hints).replace(",", "\\n").splitlines() if item.strip()]
roots.extend(["/mnt/e/datasets", "/mnt/f/datasets", "/data", "data", "datasets"])
seen = set()
print("dataset_query:", query or "未填写")
for raw in roots:
    path = Path(raw).expanduser()
    key = str(path)
    if key in seen:
        continue
    seen.add(key)
    if not path.exists():
        print(f"candidate_root: {{path}} exists=False")
        continue
    print(f"candidate_root: {{path.resolve()}} exists=True")
    matches = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        text = child.name.lower()
        if not terms or any(term in text for term in terms):
            matches.append(child)
        if len(matches) >= 12:
            break
    for child in matches:
        kind = "dir" if child.is_dir() else "file"
        print(f"  match: {{child.name}} ({{kind}})")
PY"""
        elif kind == "env.infer":
            manifest_paths = str(config.get("manifest_paths") or "requirements.txt, pyproject.toml, environment.yml, setup.py").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
manifest_paths = {json.dumps(manifest_paths)}
root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())

found = []
for raw in manifest_paths.replace(",", "\\n").splitlines():
    value = raw.strip()
    if not value:
        continue
    path = root / value
    if path.exists():
        found.append(value)
        print("found_manifest:", value)

if "environment.yml" in found or "conda.yml" in found or "conda.yaml" in found:
    print("suggest_setup: conda env update -f environment.yml")
elif "requirements.txt" in found:
    print("suggest_setup: pip install -r requirements.txt")
elif "pyproject.toml" in found:
    print("suggest_setup: pip install -e .")
else:
    print("suggest_setup: inspect README and build custom setup command")
PY"""
        elif kind == "gpu.allocate":
            gpu_policy = str(config.get("gpu_policy") or "auto").strip()
            min_free_memory_gib = str(config.get("min_free_memory_gib") or "").strip()
            gpu_message = f"[gpu.allocate] policy={gpu_policy} min_free_memory_gib={min_free_memory_gib or '-'}"
            command = (
                "echo "
                + shlex.quote(gpu_message)
                + "; echo \"CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}\"; "
                + "nvidia-smi --query-gpu=index,name,memory.free,utilization.gpu --format=csv,noheader 2>/dev/null || true"
            )
        elif kind == "repo.inspect":
            command = """python3 - <<'PY'
from pathlib import Path

root = Path(".").resolve()
print(f"workspace_dir: {root}")

interesting = [
    "README.md",
    "README.rst",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "environment.yml",
    "conda.yml",
    "conda.yaml",
]
for name in interesting:
    path = root / name
    if path.exists():
        print(f"found: {name}")

top_level = []
for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
    if item.name.startswith("."):
        continue
    if item.name in {"__pycache__", "node_modules", "dist", "build"}:
        continue
    suffix = "/" if item.is_dir() else ""
    top_level.append(f"{item.name}{suffix}")
    if len(top_level) >= 30:
        break
print("top_level:", ", ".join(top_level))

entry_names = {item.rstrip("/") for item in top_level}
if "pytest.ini" in entry_names or "tests" in entry_names:
    print("suggest_run: python -m pytest -q")
elif "train.py" in entry_names:
    print("suggest_run: python train.py --help")
elif "main.py" in entry_names:
    print("suggest_run: python main.py --help")
elif "app.py" in entry_names:
    print("suggest_run: python app.py")
PY"""
        elif kind == "artifact.collect":
            artifact_paths = str(config.get("artifact_paths") or "runs\noutputs\ncheckpoints\nlogs").strip()
            metric_paths = str(config.get("metric_paths") or "").strip()
            command = f"""python3 - <<'PY'
from pathlib import Path

workspace_dir = {json.dumps(workspace_dir)}
artifact_paths = {json.dumps(artifact_paths)}
metric_paths = {json.dumps(metric_paths)}
root = Path(workspace_dir or ".").expanduser()
print("workspace_dir:", root.resolve())

for label, raw in [("artifact", artifact_paths), ("metric", metric_paths)]:
    values = [item.strip() for item in raw.replace(",", "\\n").splitlines() if item.strip()]
    if not values:
        print(f"{{label}}: none")
        continue
    for value in values[:30]:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        print(f"{{label}}: {{path.resolve()}} exists={{path.exists()}}")
PY"""
        if not command:
            raise ValueError("node has no executable command yet")

        gpu_policy = str(config.get("gpu_policy") or "auto").strip().lower()
        server_id = str(config.get("server_id") or "auto").strip() or "auto"
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")
        is_gpu_job = kind in {"run.command", "gpu.allocate"}
        wait_for_idle = kind in {"run.command", "gpu.allocate"} or kind in {"repo.clone", "env.prepare", "eval.report"}
        gpu_index: int | str = "auto"
        if kind in {"repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "env.prepare", "artifact.collect", "eval.report"}:
            gpu_index = "none"
        elif gpu_policy in {"cpu", "none", "no_gpu"}:
            gpu_index = "none"
        else:
            configured_gpu_index = str(config.get("gpu_index") or "").strip()
            if configured_gpu_index and configured_gpu_index != "auto":
                gpu_index = configured_gpu_index
        job_cwd = workspace_dir
        if kind == "repo.clone":
            job_cwd = ""
        elif kind in WORKSPACE_NO_CWD_NODE_KINDS:
            job_cwd = ""
        if automation is None:
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            runtime_workspace = apply_workspace_job_runtime(workspace, jobs_snapshot)
            execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
            automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        runtime_execution_mode = (
            "gpu"
            if is_gpu_job and str(gpu_index).strip().lower() not in {"none", "cpu", "no_gpu"}
            else "cpu"
        )
        execution_bundle_metadata = workspace_execution_bundle_job_metadata(automation, node)
        scheduler_binding = workspace_scheduler_binding_metadata(automation, config)
        runtime_binding = {
            "node_kind": kind,
            "server_id": server_id,
            "gpu_index": str(gpu_index),
            "gpu_policy": gpu_policy,
            "execution_mode": runtime_execution_mode,
            "cwd": job_cwd,
            "env_name": str(config.get("env_name") or workspace_env.get("name") or "").strip(),
            "wait_for_idle": wait_for_idle,
            "scheduler_status": str(scheduler_binding.get("status") or "").strip(),
            "scheduler_summary": str(scheduler_binding.get("summary") or "").strip(),
        }
        payload: dict[str, Any] = {
            "name": f"{workspace.get('name') or workspace.get('id') or 'workspace'} · {name_suffix}",
            "server_id": server_id,
            "gpu_index": gpu_index,
            "wait_for_idle": wait_for_idle,
            "command": command,
            "command_display": command,
            "cwd": job_cwd,
            "env_name": str(config.get("env_name") or workspace_env.get("name") or "").strip(),
            "target_job_ids": [str(previous_job_id)] if previous_job_id else [],
            "metadata": {
                "workspace_id": str(workspace.get("id") or "").strip(),
                "node_id": str(node.get("id") or "").strip(),
                "node_kind": kind,
                "node_title": name_suffix,
                "execution_mode": runtime_execution_mode,
                "resource_plan": workspace_node_resources(workspace, node, None),
                "artifact_plan": workspace_node_artifacts(workspace, node, None),
                "workflow_contract_node": workspace_node_workflow_contract_metadata(workspace, node),
                "execution_bundle": execution_bundle_metadata,
                "scheduler_binding": scheduler_binding,
                "runtime_binding": runtime_binding,
            },
            "kind": "command",
        }
        if previous_job_id:
            payload["metadata"]["workflow_prev_job_id"] = previous_job_id
        return payload

    def run_workspace_node(self, workspace_id: str, node_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        node_id = str(node_id or "").strip()
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            node = next(
                (
                    item for item in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
                    if isinstance(item, dict) and str(item.get("id") or "").strip() == node_id
                ),
                None,
            )
            if not node:
                raise ValueError("node not found")
        job_payload = self.workspace_node_job_payload(workspace, node)
        job = self.create_job(job_payload)
        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        return {
            "job": job,
            "workspace": payload_workspace,
        }

    def run_workspace_workflow(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        force = bool(requested_payload.get("force") or False)
        until_node_id = str(requested_payload.get("until_node_id") or requested_payload.get("target_node_id") or "").strip()
        auto_apply_raw = requested_payload.get("auto_apply", requested_payload.get("apply_defaults", True))
        auto_apply = (
            auto_apply_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(auto_apply_raw, str)
            else bool(auto_apply_raw)
        )
        apply_evidence_raw = requested_payload.get("apply_evidence", True)
        apply_evidence = (
            apply_evidence_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(apply_evidence_raw, str)
            else bool(apply_evidence_raw)
        )
        applied: list[dict[str, Any]] = []
        evidence_applied: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            workspace = copy.deepcopy(current)
            if auto_apply:
                workspace, applied = apply_workspace_automation_defaults_to_payload(
                    workspace,
                    statuses_snapshot,
                    force=False,
                )
                if apply_evidence:
                    workspace, evidence_applied = apply_workspace_discovery_evidence_to_payload(
                        workspace,
                        jobs_snapshot,
                        force=False,
                    )
                    applied.extend(evidence_applied)
                index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                if index < 0:
                    raise ValueError("workspace not found")
                self.workspaces[index] = workspace
            nodes = [
                node for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
                if isinstance(node, dict) and str(node.get("kind") or "").strip() in WORKSPACE_EXECUTABLE_NODE_KINDS
            ]
            target_node: dict[str, Any] | None = None
            if until_node_id:
                target_index = next(
                    (
                        index for index, node in enumerate(nodes)
                        if str(node.get("id") or "").strip() == until_node_id
                    ),
                    -1,
                )
                if target_index < 0:
                    raise ValueError("target node is not executable or not found")
                target_node = copy.deepcopy(nodes[target_index])
                nodes = nodes[:target_index + 1]
        if auto_apply:
            self.save_workspaces()
        if not nodes:
            raise ValueError("workspace has no executable nodes")

        runtime_workspace = apply_workspace_job_runtime(workspace, jobs_snapshot)
        execution = derive_workspace_execution_state(runtime_workspace, jobs_snapshot)
        automation = derive_workspace_automation_state(runtime_workspace, execution, statuses_snapshot)
        blocked_checks = workspace_workflow_blocking_checks(automation)
        if until_node_id:
            blocked_checks = [
                check for check in blocked_checks
                if str(check.get("id") or "") == "starter_chain"
            ]
        if blocked_checks and not force:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(blocked_checks),
                blocked_checks=blocked_checks,
                workspace=payload_workspace,
                applied=applied,
                evidence_applied=evidence_applied,
            )

        invalid_checks: list[dict[str, Any]] = []
        for node in nodes:
            try:
                self.workspace_node_job_payload(workspace, node, automation=automation)
            except ValueError as exc:
                invalid_checks.append(
                    {
                        "id": str(node.get("id") or "").strip(),
                        "label": str(node.get("title") or node.get("kind") or "节点").strip(),
                        "status": "blocked",
                        "title": str(node.get("title") or node.get("kind") or "节点").strip(),
                        "detail": str(exc),
                        "action": "先运行自动发现或补齐节点配置，再提交完整工作流。",
                        "node_kind": str(node.get("kind") or "").strip(),
                    }
                )
        if invalid_checks:
            with self.lock:
                payload_workspace = self.workspace_public_payload(self.workspace_by_id(workspace_id) or workspace)
            raise WorkspaceWorkflowReadinessError(
                workspace_readiness_message(invalid_checks),
                blocked_checks=invalid_checks,
                workspace=payload_workspace,
                applied=applied,
                evidence_applied=evidence_applied,
            )

        jobs: list[dict[str, Any]] = []
        previous_job_id = ""
        for index, node in enumerate(nodes):
            payload = self.workspace_node_job_payload(workspace, node, previous_job_id=previous_job_id, automation=automation)
            payload["wait_for_idle"] = True
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            metadata["workflow_index"] = index
            if until_node_id:
                metadata["workflow_phase"] = "run_to_node"
                metadata["workflow_until_node_id"] = until_node_id
                metadata["workflow_until_node_title"] = str((target_node or {}).get("title") or "").strip()
                metadata["workflow_until_node_kind"] = str((target_node or {}).get("kind") or "").strip()
            payload["metadata"] = metadata
            job = self.create_job(payload)
            jobs.append(job)
            previous_job_id = str(job.get("id") or "")

        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        execution_package = workspace_execution_bundle_result(automation, jobs)
        if until_node_id:
            execution_package["scope"] = {
                "mode": "run_to_node",
                "target_node_id": until_node_id,
                "target_node_title": str((target_node or {}).get("title") or "").strip(),
                "target_node_kind": str((target_node or {}).get("kind") or "").strip(),
            }
        return {
            "workspace": payload_workspace,
            "jobs": jobs,
            "applied": applied,
            "evidence_applied": evidence_applied,
            "execution_package": execution_package,
        }

    def append_workspace_chat(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("text is required")
        role = str(payload.get("role") or "user").strip().lower()
        if role not in {"user", "assistant", "system"}:
            role = "user"
        requested_agent_id = safe_id(str(payload.get("agent_id") or "").strip()) if str(payload.get("agent_id") or "").strip() else ""
        use_llm = bool(payload.get("use_llm") or False)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            agent_id = requested_agent_id if any(agent["id"] == requested_agent_id for agent in agents) else ""
            if agent_id:
                model["chat_agent_id"] = agent_id
            agent_name = workspace_agent_name({"agents": agents}, agent_id)
            user_message = make_workspace_chat_message(role, text, agent_id=agent_id, agent_name=agent_name)
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat + [user_message]
            preview_workspace_public = self.workspace_public_payload(preview_workspace)

        # Generate reply - either from LLM or from placeholder
        reply_text = ""
        execution_info = None

        if use_llm and agent_id:
            # Try to use actual LLM
            model_config = preview_workspace.get("model") if isinstance(preview_workspace.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()

            agent = next((item for item in agents if item["id"] == agent_id), None)
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip() if agent else ""
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id

            if effective_profile_id and agent:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    # Get allowed tools
                    tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]

                    # Create and execute agent
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                    )
                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                    )

                    # Build context from chat history
                    chat_context = []
                    for msg in chat[-10:]:  # Last 10 messages as context
                        msg_role = str(msg.get("role") or "user")
                        msg_text = str(msg.get("text") or "")
                        if msg_text:
                            chat_context.append(f"{msg_role}: {msg_text}")

                    execution_result = executor.run(text, context={
                        "workspace_id": workspace_id,
                        "workspace_name": preview_workspace.get("name", ""),
                        "chat_history": chat_context,
                    })

                    if execution_result.success:
                        reply_text = execution_result.final_answer
                    else:
                        reply_text = f"[Agent execution failed: {execution_result.error}]"

                    execution_info = execution_result.to_dict()

        # If no LLM used or failed, use placeholder reply
        if not reply_text:
            reply_text = build_workspace_chat_reply(preview_workspace, text, agent_id=agent_id)

        assistant_message = make_workspace_chat_message("assistant", reply_text, agent_id=agent_id, agent_name=agent_name)

        with self.lock:
            merged = copy.deepcopy(current)
            merged["agents"] = agents
            merged["tools"] = tools
            merged["model"] = model
            merged["chat"] = chat + [user_message, assistant_message]
            updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
            result_workspace = self.workspace_public_payload(updated)

        self.save_workspaces()

        result = {
            "workspace": result_workspace,
            "messages": [user_message, assistant_message],
        }
        if execution_info:
            result["execution"] = execution_info

        return result

    def debug_workspace_agent(self, workspace_id: str, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_agent_id = safe_id(str(agent_id or "").strip()) if str(agent_id or "").strip() else ""
        requested_payload = payload if isinstance(payload, dict) else {}
        input_text = str(requested_payload.get("input") or requested_payload.get("text") or "").strip()
        requested_node_kind = str(requested_payload.get("node_kind") or "").strip()
        requested_tool_ids = parse_tag_list(requested_payload.get("tool_ids", []))
        execute_llm = bool(requested_payload.get("execute_llm") or False)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            agent = next((item for item in agents if item["id"] == requested_agent_id), None)
            if not agent:
                raise ValueError("agent not found")
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat
            preview_workspace = self.workspace_public_payload(preview_workspace)

        debug = build_workspace_agent_debug(
            preview_workspace,
            agent,
            input_text=input_text,
            requested_node_kind=requested_node_kind,
            requested_tool_ids=requested_tool_ids,
        )

        result = {"debug": debug}

        # Execute LLM if requested and input is provided
        if execute_llm and input_text:
            model_config = preview_workspace.get("model") if isinstance(preview_workspace.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id

            if effective_profile_id:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    # Get allowed tools for this agent
                    tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]

                    # Create LLM client and agent executor
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                    )
                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                    )

                    # Execute agent
                    execution_result = executor.run(input_text, context={
                        "workspace_id": workspace_id,
                        "workspace_name": preview_workspace.get("name", ""),
                        "source_type": preview_workspace.get("source", {}).get("type", ""),
                    })

                    result["execution"] = execution_result.to_dict()
                else:
                    result["execution"] = {
                        "success": False,
                        "error": "Provider profile not found or API key not configured",
                        "final_answer": "",
                    }
            else:
                result["execution"] = {
                    "success": False,
                    "error": "No provider profile configured for this workspace/agent",
                    "final_answer": "",
                }

        return result

    def reorder_job(self, job_id: str, direction: str) -> dict[str, Any]:
        job_id = str(job_id or "").strip()
        move = str(direction or "").strip().lower()
        if move not in {"top", "up", "down"}:
            raise ValueError("direction must be top, up or down")
        with self.lock:
            job = next((item for item in self.jobs if item.get("id") == job_id), None)
            if not job:
                raise ValueError("job not found")
            if str(job.get("status") or "") not in {"queued", "blocked"}:
                raise ValueError("只能调整等待中的任务顺序")
            waiting = sorted(
                [item for item in self.jobs if str(item.get("status") or "") in {"queued", "blocked"}],
                key=self.queue_sort_key,
            )
            index = next((idx for idx, item in enumerate(waiting) if item.get("id") == job_id), -1)
            if index < 0:
                raise ValueError("job not found")
            if move == "top":
                target_index = 0
            elif move == "up":
                target_index = max(0, index - 1)
            else:
                target_index = min(len(waiting) - 1, index + 1)
            if target_index != index:
                moved = waiting.pop(index)
                waiting.insert(target_index, moved)
                for order, item in enumerate(waiting, 1):
                    item["queue_rank"] = order
            self.next_queue_rank = len(waiting) + 1
            queue_position = next(
                (idx + 1 for idx, item in enumerate(waiting) if item.get("id") == job_id),
                0,
            )
        self.save_jobs()
        return {
            "job": job,
            "queue_position": queue_position,
            "total_waiting": len(waiting),
        }

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = getattr(self, "config", AppConfig())
        command = str(payload.get("command") or "").strip()
        if not command:
            raise ValueError("command is required")
        server_id = str(payload.get("server_id") or "local")
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")

        gpu_value = payload.get("gpu_index", "auto")
        gpu_index: int | str | None
        gpu_value_text = str(gpu_value).strip().lower() if gpu_value is not None else ""
        if gpu_value in (None, "", "auto"):
            gpu_index = "auto"
        elif gpu_value_text in {"none", "no_gpu", "cpu"}:
            gpu_index = "none"
        else:
            gpu_index = safe_int(gpu_value)

        wait_for_idle = bool(payload.get("wait_for_idle", True))
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        job_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
        job = {
            "id": job_id,
            "name": str(payload.get("name") or command.splitlines()[0][:80]),
            "server_id": server_id,
            "requested_server_id": server_id,
            "candidate_server_ids": list(payload.get("candidate_server_ids") or []),
            "gpu_index": gpu_index,
            "requested_gpu_index": gpu_index,
            "command": command,
            "command_display": str(payload.get("command_display") or command),
            "cwd": str(payload.get("cwd") or "").strip(),
            "env_name": str(payload.get("env_name") or "").strip(),
            "min_free_mib": safe_int(payload.get("min_free_mib"), config.idle_min_free_mib),
            "max_gpu_util": safe_int(payload.get("max_gpu_util"), config.idle_max_gpu_util),
            "wait_for_idle": wait_for_idle,
            "status": "queued" if wait_for_idle else "starting",
            "session": make_session_name(job_id),
            "kind": str(payload.get("kind") or "command"),
            "target_job_ids": list(payload.get("target_job_ids") or []),
            "profile_key": str(payload.get("profile_key") or ""),
            "profile_measured_mib": 0,
            "created_at": now_iso(),
            "started_at": "",
            "finished_at": "",
            "error": "",
            "queue_rank": 0,
            "log_path": str(local_log_path(server_id, job_id).resolve()),
            "remote_log_path": "",
            "metadata": metadata,
        }
        with self.lock:
            self.reserve_queue_ranks([job])
            self.jobs.insert(0, job)
        if wait_for_idle:
            self.save_jobs()
        else:
            self.start_job(job, allow_busy=True)
        return job

    def _format_remote_path(self, template: str, server: ServerConfig | None = None) -> str:
        user = (server.user if server else None) or "user"
        host = (server.host_name if server else None) or ""
        try:
            return template.format(user=user, host=host)
        except (KeyError, ValueError):
            return template

    def apply_server_paths(self, job: dict[str, Any], server: ServerConfig) -> None:
        if server.mode == "local":
            cwd = str(job.get("cwd_local") or job.get("cwd") or "").strip()
        else:
            cwd = str(job.get("cwd_remote") or job.get("cwd") or "").strip()
            cwd = self._format_remote_path(cwd, server)
        if cwd:
            job["cwd"] = cwd

    def preset_command(self, experiment: Any, *, data_root: str, smoke: bool = False) -> str:
        parts = [
            "python",
            "smoke_test_single.py" if smoke else "train.py",
            "--arch",
            experiment.arch,
            "--ablation",
            experiment.ablation,
        ]
        if smoke:
            parts.extend(["--dino", experiment.dino, "--bs", str(experiment.batch_size), "--gpu_id", "0"])
        else:
            parts.extend(
                [
                    "--data_name",
                    experiment.dataset,
                    "--batchsize",
                    str(experiment.batch_size),
                    "--gpu_id",
                    "0",
                    "--data_root",
                    data_root,
                ]
            )
            if experiment.dino != "none":
                parts.extend(["--dino_variant", experiment.dino])
        return " ".join(shlex.quote(part) for part in parts)

    def task_plan_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        template = str(payload.get("template") or "custom").strip().lower() or "custom"
        if template == "preset":
            datasets = str(payload.get("datasets") or "dataset_a").strip() or "dataset_a"
            experiments = generate_preset_experiments(datasets)
            limit = safe_int(payload.get("limit"), 0)
            if limit > 0:
                experiments = experiments[:limit]
            data_root = str(payload.get("data_root") or PRESET_DEFAULT_DATA_ROOT).strip()
            user_mem = safe_int(payload.get("max_memory_mib") or payload.get("min_free_mib"), 0)
            items: list[dict[str, Any]] = []
            for order, experiment in enumerate(experiments, 1):
                session = make_preset_session_name(
                    experiment.dataset, experiment.arch, experiment.ablation, experiment.dino
                )
                metadata = {
                    "template": "preset",
                    "order": order,
                    "dataset": experiment.dataset,
                    "arch": experiment.arch,
                    "ablation": experiment.ablation,
                    "dino": experiment.dino,
                    "batch_size": experiment.batch_size,
                    "priority": experiment.priority,
                    "estimated_mib": experiment.estimated_mib,
                }
                items.append(
                    {
                        "name": f"Preset {session}",
                        "session": session,
                        "profile_session": f"profile_{session[:40]}",
                        "command": self.preset_command(experiment, data_root=data_root, smoke=False),
                        "profile_command": self.preset_command(experiment, data_root=data_root, smoke=True),
                        "estimated_mib": experiment.estimated_mib,
                        "min_free_mib": user_mem or experiment.estimated_mib,
                        "profile_key": experiment.key,
                        "metadata": metadata,
                    }
                )
            return items

        command_template = str(payload.get("command_template") or payload.get("command") or "").strip()
        if not command_template:
            raise ValueError("command_template is required")
        name_template = str(payload.get("name_template") or payload.get("name") or "批量任务 {index}").strip()
        session_template = str(payload.get("session_template") or name_template).strip()
        profile_template = str(payload.get("profile_command_template") or "").strip()
        params = parse_param_matrix(payload.get("params") or payload.get("params_text") or "")
        default_min_free = safe_int(payload.get("min_free_mib") or payload.get("max_memory_mib"), self.config.idle_min_free_mib)
        items = []
        for row in params:
            name = render_task_template(name_template, row) or f"批量任务 {row['index']}"
            session = safe_id(render_task_template(session_template, row) or name)
            metadata = {
                "template": "custom",
                "order": row["index"],
                "params": row,
            }
            items.append(
                {
                    "name": name,
                    "session": f"tc_{session[:45]}",
                    "profile_session": f"profile_{session[:40]}",
                    "command": render_task_template(command_template, row).strip(),
                    "profile_command": render_task_template(profile_template, row).strip(),
                    "estimated_mib": default_min_free,
                    "min_free_mib": default_min_free,
                    "profile_key": session,
                    "metadata": metadata,
                }
            )
        return items

    def task_plan_preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = str(payload.get("template") or "custom").strip().lower() or "custom"
        items = self.task_plan_items(payload)
        profile_first = bool(payload.get("profile_first", payload.get("smoke_first", False)))
        return {
            "template": template,
            "count": len(items),
            "profile_first": profile_first,
            "items": items,
            "metadata": {
                "datasets": str(payload.get("datasets") or "dataset_a").strip() or "dataset_a"
                if template == "preset"
                else "",
            },
        }

    def create_task_plan_jobs(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.task_plan_preview(payload)
        items = preview["items"]
        if not items:
            raise ValueError("no task items selected")

        server_id = str(payload.get("server_id") or "auto").strip() or "auto"
        if server_id != "auto" and not self.server_by_id(server_id):
            raise ValueError(f"unknown server: {server_id}")
        candidate_server_ids = [
            str(item)
            for item in payload.get("candidate_server_ids", [])
            if str(item)
        ]
        requested_gpu = payload.get("gpu_index", "auto")
        gpu_index: int | str = "auto" if requested_gpu in (None, "", "auto") else safe_int(requested_gpu)
        env_name = str(payload.get("env_name") or "").strip()
        template = str(preview["template"])
        local_project = str(
            payload.get("local_project_dir")
            or payload.get("cwd_local")
            or (PRESET_DEFAULT_PROJECT_DIR if template == "preset" else payload.get("cwd") or "")
        ).strip()
        remote_project = str(
            payload.get("remote_project_dir")
            or payload.get("cwd_remote")
            or (PRESET_DEFAULT_REMOTE_PROJECT_DIR if template == "preset" else payload.get("cwd") or "")
        ).strip()
        cwd = str(payload.get("cwd") or "").strip()
        max_gpu_util = safe_int(payload.get("max_gpu_util"), self.config.idle_max_gpu_util)
        profile_first = bool(payload.get("profile_first", payload.get("smoke_first", False)))
        safety = max(1.0, safe_float(payload.get("profile_safety", payload.get("smoke_safety", 1.2)), 1.2))
        profile_free_override = safe_int(
            payload.get("profile_min_free_mib", payload.get("smoke_min_free_mib")),
            0,
        )
        dry_run = bool(payload.get("dry_run", False))

        now_prefix = datetime.now().strftime("%Y%m%d-%H%M%S-")
        batch_jobs: list[dict[str, Any]] = []
        profile_jobs: list[dict[str, Any]] = []
        for item in items:
            train_id = now_prefix + uuid.uuid4().hex[:8]
            item_min_free = safe_int(item.get("min_free_mib"), self.config.idle_min_free_mib)
            can_profile = profile_first and bool(item.get("profile_command"))
            metadata = dict(item.get("metadata") or {})
            metadata.update(
                {
                    "template": template,
                    "estimated_mib": safe_int(item.get("estimated_mib"), item_min_free),
                    "profile_safety": safety,
                }
            )
            batch_job = {
                "id": train_id,
                "name": str(item.get("name") or f"批量任务 {train_id}"),
                "server_id": server_id,
                "requested_server_id": server_id,
                "candidate_server_ids": candidate_server_ids,
                "gpu_index": gpu_index,
                "requested_gpu_index": gpu_index,
                "command": str(item.get("command") or ""),
                "cwd": cwd,
                "cwd_local": local_project,
                "cwd_remote": remote_project,
                "env_name": env_name,
                "min_free_mib": item_min_free,
                "max_gpu_util": max_gpu_util,
                "wait_for_idle": True,
                "status": "blocked" if can_profile else "queued",
                "session": str(item.get("session") or make_session_name(train_id)),
                "kind": "profiled-batch-item" if can_profile else "batch-item",
                "target_job_ids": [],
                "profile_key": str(item.get("profile_key") or ""),
                "profile_measured_mib": 0,
                "created_at": now_iso(),
                "started_at": "",
                "finished_at": "",
                "error": "等待 profile/smoke 完成" if can_profile else "",
                "queue_rank": 0,
                "log_path": str(local_log_path(server_id, train_id).resolve()),
                "remote_log_path": "",
                "metadata": metadata,
            }
            batch_jobs.append(batch_job)

            if can_profile:
                profile_id = now_prefix + uuid.uuid4().hex[:8]
                profile_metadata = dict(metadata)
                profile_metadata.update({"parser": "peak_allocated_mib"})
                profile_jobs.append(
                    {
                        "id": profile_id,
                        "name": f"Profile {batch_job['name']}",
                        "server_id": server_id,
                        "requested_server_id": server_id,
                        "candidate_server_ids": candidate_server_ids,
                        "gpu_index": gpu_index,
                        "requested_gpu_index": gpu_index,
                        "command": str(item.get("profile_command") or ""),
                        "cwd": cwd,
                        "cwd_local": local_project,
                        "cwd_remote": remote_project,
                        "env_name": env_name,
                        "min_free_mib": profile_free_override or item_min_free,
                        "max_gpu_util": max_gpu_util,
                        "wait_for_idle": True,
                        "status": "queued",
                        "session": str(item.get("profile_session") or f"profile_{batch_job['session'][:40]}"),
                        "kind": "profile",
                        "target_job_ids": [train_id],
                        "profile_key": str(item.get("profile_key") or ""),
                        "profile_measured_mib": 0,
                        "created_at": now_iso(),
                        "started_at": "",
                        "finished_at": "",
                        "error": "",
                        "queue_rank": 0,
                        "log_path": str(local_log_path(server_id, profile_id).resolve()),
                        "remote_log_path": "",
                        "metadata": profile_metadata,
                    }
                )

        new_jobs = [*profile_jobs, *batch_jobs] if profile_jobs else batch_jobs
        if not dry_run:
            with self.lock:
                self.reserve_queue_ranks(new_jobs)
                self.jobs = [*new_jobs, *self.jobs]
            self.save_jobs()
        return {
            "template": template,
            "created": len(new_jobs),
            "profile_jobs": len(profile_jobs),
            "batch_jobs": len(batch_jobs),
            "jobs": new_jobs,
            "dry_run": dry_run,
        }

    def preset_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.task_plan_preview({**payload, "template": "preset"})
        experiments = []
        for item in preview.get("items", []):
            metadata = dict(item.get("metadata") or {})
            experiments.append(
                {
                    "estimated_mib": metadata.get("estimated_mib", item.get("estimated_mib", 0)),
                    "dataset": metadata.get("dataset", ""),
                    "arch": metadata.get("arch", ""),
                    "ablation": metadata.get("ablation", ""),
                    "dino": metadata.get("dino", ""),
                    "batch_size": metadata.get("batch_size", ""),
                    "priority": metadata.get("priority", ""),
                    "session": item.get("session", ""),
                    "command": item.get("command", ""),
                    "profile_command": item.get("profile_command", ""),
                }
            )
        return {
            **preview,
            "datasets": preview.get("metadata", {}).get("datasets", ""),
            "experiments": experiments,
        }

    def create_preset_jobs(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.create_task_plan_jobs({**payload, "template": "preset"})
        return {
            **result,
            "smoke_jobs": result.get("profile_jobs", 0),
            "train_jobs": result.get("batch_jobs", 0),
        }

    def find_gpu(self, job: dict[str, Any]) -> tuple[bool, str | None, int | None, str]:
        with self.lock:
            statuses = list(self.statuses)
        requested_server = str(job.get("server_id") or job.get("requested_server_id") or "local")
        candidate_server_ids = {str(item) for item in job.get("candidate_server_ids", []) if str(item)}
        if requested_server != "auto":
            candidate_server_ids = {requested_server}

        server_statuses = [
            item for item in statuses
            if item.get("online") and (not candidate_server_ids or item.get("id") in candidate_server_ids)
        ]
        if not statuses:
            return False, None, None, "no status yet"
        if not server_statuses:
            if requested_server != "auto":
                server_status = next((item for item in statuses if item["id"] == requested_server), None)
                return False, None, None, (server_status or {}).get("error") or "server offline"
            return False, None, None, "no online candidate server"

        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        requested = job.get("gpu_index", job.get("requested_gpu_index", "auto"))
        for server_status in server_statuses:
            for gpu in server_status.get("gpus", []):
                if requested != "auto" and gpu.get("index") != requested:
                    continue
                free_ok = gpu.get("memory_free_mib", 0) >= job.get("min_free_mib", self.config.idle_min_free_mib)
                util_ok = gpu.get("gpu_util", 100) <= job.get("max_gpu_util", self.config.idle_max_gpu_util)
                if free_ok and util_ok:
                    candidates.append((server_status, gpu))
        if not candidates:
            return False, None, None, "waiting for idle GPU"
        candidates.sort(
            key=lambda item: (item[1].get("memory_free_mib", 0), -item[1].get("gpu_util", 100)),
            reverse=True,
        )
        server_status, gpu = candidates[0]
        return True, str(server_status["id"]), int(gpu["index"]), ""

    def pick_server_for_job(self, job: dict[str, Any]) -> tuple[bool, str | None, str]:
        requested_server = str(job.get("server_id") or job.get("requested_server_id") or "local").strip() or "local"
        candidate_server_ids = {str(item) for item in job.get("candidate_server_ids", []) if str(item)}
        with self.lock:
            statuses = list(self.statuses)

        if requested_server != "auto":
            server = self.server_by_id(requested_server)
            if not server:
                return False, None, f"unknown server: {requested_server}"
            return True, requested_server, ""

        server_statuses = [
            item for item in statuses
            if item.get("online") and (not candidate_server_ids or item.get("id") in candidate_server_ids)
        ]
        if not server_statuses:
            return False, None, "no online candidate server"

        def server_priority(status: dict[str, Any]) -> tuple[int, int, int, str]:
            process_count = len(status.get("processes") or [])
            busy_gpu_count = sum(1 for gpu in status.get("gpus", []) if gpu.get("state") == "busy")
            return (
                0 if status.get("id") == "local" else 1,
                process_count,
                busy_gpu_count,
                str(status.get("id") or ""),
            )

        server_statuses.sort(key=server_priority)
        return True, str(server_statuses[0].get("id") or ""), ""

    def start_job(self, job: dict[str, Any], allow_busy: bool = False) -> None:
        gpuless = str(job.get("gpu_index") or "").strip().lower() in {"none", "no_gpu", "cpu"}
        if gpuless:
            job["gpu_index"] = "none"
            if str(job.get("server_id") or "").strip() in {"", "auto"}:
                ok, selected_server_id, reason = self.pick_server_for_job(job)
                if not ok:
                    job["error"] = reason
                    return
                job["server_id"] = selected_server_id
        elif not allow_busy:
            ok, selected_server_id, gpu_index, reason = self.find_gpu(job)
            if not ok:
                job["error"] = reason
                return
            job["server_id"] = selected_server_id
            job["gpu_index"] = gpu_index
        elif job.get("gpu_index") == "auto":
            ok, selected_server_id, gpu_index, _reason = self.find_gpu(job)
            if selected_server_id:
                job["server_id"] = selected_server_id
            job["gpu_index"] = gpu_index if ok else 0

        server = self.server_by_id(str(job.get("server_id") or ""))
        if not server:
            job["status"] = "failed"
            job["error"] = "unknown server"
            self.save_jobs()
            return
        self.apply_server_paths(job, server)

        runtime_command = str(job.get("command") or "")
        runtime_display = str(job.get("command_display") or runtime_command)
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        transfer_spec = metadata.get("transfer_spec") if isinstance(metadata.get("transfer_spec"), dict) else None
        if str(job.get("kind") or "") == "transfer" and transfer_spec:
            try:
                runtime_command, runtime_display = build_transfer_command(transfer_spec, self.servers)
                job["command"] = runtime_display
                job["command_display"] = runtime_display
            except ValueError as exc:
                job["status"] = "failed"
                job["finished_at"] = now_iso()
                job["error"] = str(exc)
                self.save_jobs()
                return

        session = job["session"]
        if server.mode == "local":
            log_path = str(local_log_path(server.id, job["id"]).resolve())
            script = build_job_script(
                job,
                log_path,
                remote=False,
                server=server,
                command_override=runtime_command,
                command_display=runtime_display,
            )
            command = tmux_new_session_args(session, "bash -lc " + shlex.quote(script))
            result = run_command(command, timeout=5)
        else:
            log_path = str(local_log_path(server.id, job["id"]).resolve())
            remote_path = remote_log_path(job["id"])
            script = build_job_script(
                job,
                remote_path,
                remote=True,
                server=server,
                command_override=runtime_command,
                command_display=runtime_display,
            )
            shell_command = "bash -lc " + shlex.quote(script)
            remote_command = (
                f"tmux new-session -d -s {shlex.quote(session)} "
                f"-x {TMUX_DEFAULT_COLUMNS} -y {TMUX_DEFAULT_ROWS} "
                f"{shlex.quote(shell_command)}"
            )
            result = ssh_command(server, remote_command, timeout=self.config.remote_timeout_seconds)

        job["log_path"] = log_path
        if server.mode != "local":
            job["remote_log_path"] = remote_log_path(job["id"])
        if result.returncode == 0:
            job["status"] = "running"
            job["started_at"] = now_iso()
            job["error"] = ""
        else:
            job["status"] = "failed"
            job["finished_at"] = now_iso()
            job["error"] = (result.stderr.strip() or result.stdout.strip() or "tmux start failed")[-1000:]
        self.save_jobs()

    def tmux_running(self, job: dict[str, Any]) -> bool:
        server = self.server_by_id(job["server_id"])
        if not server:
            return False
        session = str(job.get("session") or "")
        if not session:
            return False
        if server.mode == "local":
            result = run_command(["tmux", "has-session", "-t", session], timeout=3)
        else:
            result = ssh_command(server, f"tmux has-session -t {shlex.quote(session)}", timeout=self.config.remote_timeout_seconds)
        return result.returncode == 0

    def tail_log(self, job: dict[str, Any], lines: int = 200) -> str:
        server = self.server_by_id(job["server_id"])
        if not server:
            return "unknown server"
        local_path = Path(str(job.get("log_path") or local_log_path(job["server_id"], job["id"])))
        if server.mode == "local":
            if not local_path.exists():
                return ""
            data = local_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(data[-lines:])
        remote_path = str(job.get("remote_log_path") or remote_log_path(job["id"]))
        result = ssh_command(
            server,
            f"tail -n {int(lines)} {remote_path} 2>/dev/null || true",
            timeout=self.config.remote_timeout_seconds,
        )
        if result.returncode == 0:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(result.stdout, encoding="utf-8")
            return result.stdout
        if local_path.exists():
            data = local_path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(data[-lines:])
        return result.stderr.strip()

    def list_tmux_sessions(self, server_id: str) -> list[dict[str, Any]]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        fmt = "#{session_name}|#{session_created}|#{session_windows}|#{session_attached}"
        if server.mode == "local":
            result = run_command(["tmux", "list-sessions", "-F", fmt], timeout=4)
        else:
            result = ssh_command(server, f"tmux list-sessions -F {shlex.quote(fmt)}", timeout=self.config.remote_timeout_seconds)
        if result.returncode != 0:
            text = (result.stderr or result.stdout or "").strip()
            if "no server running" in text.lower() or "failed to connect" in text.lower():
                return []
            raise ValueError(text or "tmux list failed")
        sessions = []
        for line in result.stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) != 4:
                continue
            sessions.append(
                {
                    "name": parts[0],
                    "created": safe_int(parts[1]),
                    "windows": safe_int(parts[2]),
                    "attached": parts[3] == "1",
                }
            )
        return sessions

    def capture_tmux(self, server_id: str, session: str, lines: int = 2000) -> str:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        session = session.strip()
        if not session:
            raise ValueError("session name required")
        history = max(50, min(int(lines), 50000))
        # -p print to stdout, -J join wrapped lines, -S -N start N lines back into history
        if server.mode == "local":
            prepare_tmux_for_capture(session)
            result = run_command(
                ["tmux", "capture-pane", "-p", "-J", "-S", f"-{history}", "-t", session],
                timeout=4,
            )
        else:
            remote_cmd = (
                "bash -lc "
                + shlex.quote(
                    tmux_resize_shell_script(session)
                    + "\n"
                    + f"tmux capture-pane -p -J -S -{history} -t {shlex.quote(session)}"
                )
            )
            result = ssh_command(server, remote_cmd, timeout=self.config.remote_timeout_seconds)
        if result.returncode != 0:
            text = (result.stderr or result.stdout or "").strip()
            raise ValueError(text or "tmux capture-pane failed")
        return result.stdout

    def stop_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        server = self.server_by_id(job["server_id"])
        if server:
            session = str(job.get("session") or "")
            if session and str(job.get("status") or "") in {"running", "starting"}:
                if server.mode == "local":
                    run_command(["tmux", "send-keys", "-t", session, "C-c"], timeout=3)
                    deadline = time.monotonic() + 2.0
                    while time.monotonic() < deadline:
                        if run_command(["tmux", "has-session", "-t", session], timeout=1).returncode != 0:
                            break
                        time.sleep(0.2)
                    if run_command(["tmux", "has-session", "-t", session], timeout=1).returncode == 0:
                        run_command(["tmux", "kill-session", "-t", session], timeout=3)
                else:
                    quoted = shlex.quote(session)
                    remote_script = (
                        f"tmux send-keys -t {quoted} C-c 2>/dev/null || true; "
                        "for i in 1 2 3 4 5 6 7 8 9 10; do "
                        f"tmux has-session -t {quoted} 2>/dev/null || exit 0; "
                        "sleep 0.2; "
                        "done; "
                        f"tmux kill-session -t {quoted} 2>/dev/null || true"
                    )
                    ssh_command(
                        server,
                        "bash -lc " + shlex.quote(remote_script),
                        timeout=self.config.remote_timeout_seconds + 3,
                    )
        job["status"] = "stopped"
        job["finished_at"] = now_iso()
        self.save_jobs()
        return job

    def clone_job_payload(self, job: dict[str, Any]) -> dict[str, Any]:
        requested_server = str(job.get("requested_server_id") or job.get("server_id") or "local")
        requested_gpu = job.get("requested_gpu_index", job.get("gpu_index", "auto"))
        metadata = copy.deepcopy(job.get("metadata") or {})
        return {
            "name": str(job.get("name") or job.get("command_display") or job.get("command") or "任务"),
            "server_id": requested_server,
            "candidate_server_ids": list(job.get("candidate_server_ids") or []),
            "gpu_index": requested_gpu,
            "command": str(job.get("command_display") or job.get("command") or ""),
            "command_display": str(job.get("command_display") or job.get("command") or ""),
            "cwd": str(job.get("cwd") or ""),
            "env_name": str(job.get("env_name") or ""),
            "min_free_mib": safe_int(job.get("min_free_mib"), self.config.idle_min_free_mib),
            "max_gpu_util": safe_int(job.get("max_gpu_util"), self.config.idle_max_gpu_util),
            "wait_for_idle": bool(job.get("wait_for_idle", True)),
            "kind": str(job.get("kind") or "command"),
            "target_job_ids": [],
            "profile_key": str(job.get("profile_key") or ""),
            "metadata": metadata,
        }

    def job_dependencies_state(self, job: dict[str, Any]) -> tuple[bool, str]:
        dependency_ids = [str(item).strip() for item in job.get("target_job_ids", []) if str(item).strip()]
        if not dependency_ids:
            return True, ""
        jobs_by_id = {str(item.get("id") or ""): item for item in self.jobs if str(item.get("id") or "").strip()}
        for dependency_id in dependency_ids:
            dependency = jobs_by_id.get(dependency_id)
            if not dependency:
                return False, f"waiting for dependency {dependency_id}"
            status = str(dependency.get("status") or "")
            if status in {"failed", "stopped"}:
                return False, f"dependency failed: {dependency_id}"
            if status != "done":
                return False, f"waiting for dependency {dependency_id}"
        return True, ""

    def copy_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        return self.create_job(self.clone_job_payload(job))

    def retry_job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
        if not job:
            raise ValueError("job not found")
        if str(job.get("status") or "") in {"running", "queued", "starting", "blocked"}:
            raise ValueError("任务仍在进行中，不能重试")
        return self.create_job(self.clone_job_payload(job))

    def delete_job(self, job_id: str) -> None:
        """Delete a job from the jobs list."""
        with self.lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
            if not job:
                raise ValueError("job not found")
            if str(job.get("status") or "") in {"running", "queued", "starting", "blocked"}:
                raise ValueError("任务仍在进行中，不能删除")
            self.jobs = [item for item in self.jobs if item["id"] != job_id]
            self.save_jobs()

    def clear_completed_jobs(self) -> int:
        """Clear all completed/failed/stopped jobs. Returns count of deleted jobs."""
        with self.lock:
            deletable_statuses = {"done", "failed", "stopped"}
            before_count = len(self.jobs)
            self.jobs = [item for item in self.jobs if item.get("status") not in deletable_statuses]
            deleted_count = before_count - len(self.jobs)
            if deleted_count > 0:
                self.save_jobs()
            return deleted_count

    def list_servers_admin(self) -> dict[str, Any]:
        overlay = load_user_overlay(self.config_path)
        discovery_config = dict(overlay.get("ssh_discovery", {}) or {})
        discovery_path = str(discovery_config.get("config_path") or "~/.ssh/config")
        user_ids = {str(item.get("id") or "") for item in overlay["servers"]}
        with self.lock:
            servers = [
                {
                    "id": server.id,
                    "name": server.name,
                    "mode": server.mode,
                    "ssh_alias": server.ssh_alias,
                    "host_name": server.host_name,
                    "user": server.user,
                    "port": server.port,
                    "labels": server.labels,
                    "is_user": server.id in user_ids,
                    "source": "user_servers.toml" if server.id in user_ids else discovery_path,
                }
                for server in self.servers
            ]
        return {
            "servers": servers,
            "aliases": overlay["server_aliases"],
            "disabled_discovery": overlay["disabled_discovery"],
            "discovery_config_path": discovery_path,
        }

    def set_server_alias(self, server_id: str, alias: str) -> None:
        server_id = str(server_id or "").strip()
        alias = str(alias or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        # Use the most distinctive available key so it survives id/discovery changes.
        keys = [server.ssh_alias, server_id, server.host_name]
        if server.user and server.host_name:
            keys.append(f"{server.user}@{server.host_name}")
        keys = [key for key in keys if key]
        primary_key = keys[0] if keys else server_id

        overlay = load_user_overlay(self.config_path)
        if alias:
            overlay["server_aliases"][primary_key] = alias
        else:
            for key in keys:
                overlay["server_aliases"].pop(key, None)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()

    def add_server(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = str(payload.get("mode") or "ssh").strip().lower()
        if mode not in ("ssh", "local"):
            raise ValueError("mode must be ssh or local")
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        entry: dict[str, Any] = {"name": name, "mode": mode, "enabled": True}
        if mode == "local":
            entry["id"] = safe_id(payload.get("id") or name or "local")
        else:
            host_name = str(payload.get("host_name") or "").strip()
            ssh_alias = str(payload.get("ssh_alias") or "").strip()
            if not host_name and not ssh_alias:
                raise ValueError("ssh server requires host_name or ssh_alias")
            entry["id"] = safe_id(payload.get("id") or ssh_alias or host_name or name)
            if host_name:
                entry["host_name"] = host_name
            if ssh_alias:
                entry["ssh_alias"] = ssh_alias
            user = str(payload.get("user") or "").strip()
            if user:
                entry["user"] = user
            port = str(payload.get("port") or "").strip()
            if port:
                entry["port"] = port
            password = str(payload.get("password") or "").strip()
            if password:
                entry["password"] = password
            ssh_config_path = str(payload.get("ssh_config_path") or "").strip()
            if ssh_config_path:
                entry["ssh_config_path"] = ssh_config_path

        overlay = load_user_overlay(self.config_path)
        # If id collides with an existing user-server, replace it; otherwise append.
        existing = [
            index for index, item in enumerate(overlay["servers"])
            if str(item.get("id")) == entry["id"]
        ]
        if existing:
            overlay["servers"][existing[0]] = entry
        else:
            overlay["servers"].append(entry)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()
        return entry

    def update_server(self, server_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")

        overlay = load_user_overlay(self.config_path)
        match_index = None
        for i, item in enumerate(overlay["servers"]):
            if str(item.get("id") or "") == server_id:
                match_index = i
                break

        if match_index is not None:
            # User-defined server: update in place
            existing = overlay["servers"][match_index]
        else:
            # Discovered server: promote to user-defined entry
            server = self.server_by_id(server_id)
            if not server:
                raise ValueError("server not found")
            existing: dict[str, Any] = {"id": server.id, "name": server.name, "mode": server.mode, "enabled": True}
            if server.ssh_alias:
                existing["ssh_alias"] = server.ssh_alias
            if server.host_name:
                existing["host_name"] = server.host_name
            if server.user:
                existing["user"] = server.user
            if server.port:
                existing["port"] = server.port
            if server.password:
                existing["password"] = server.password
            if server.ssh_config_path:
                existing["ssh_config_path"] = server.ssh_config_path
            if server.labels:
                existing["labels"] = list(server.labels)

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        mode = str(payload.get("mode") or existing.get("mode") or "ssh").strip().lower()
        if mode not in ("ssh", "local"):
            raise ValueError("mode must be ssh or local")

        entry: dict[str, Any] = {"id": existing.get("id", server_id), "name": name, "mode": mode, "enabled": existing.get("enabled", True)}
        if mode == "ssh":
            host_name = str(payload.get("host_name") or "").strip()
            ssh_alias = str(payload.get("ssh_alias") or "").strip()
            if not host_name and not ssh_alias:
                host_name = str(existing.get("host_name") or "").strip()
                ssh_alias = str(existing.get("ssh_alias") or "").strip()
            if host_name:
                entry["host_name"] = host_name
            if ssh_alias:
                entry["ssh_alias"] = ssh_alias
            user = str(payload.get("user") or "").strip()
            if user:
                entry["user"] = user
            elif existing.get("user"):
                entry["user"] = existing["user"]
            port = str(payload.get("port") or "").strip()
            if port:
                entry["port"] = port
            elif existing.get("port"):
                entry["port"] = existing["port"]
            password = str(payload.get("password") or "").strip()
            if password:
                entry["password"] = password
            elif existing.get("password"):
                entry["password"] = existing["password"]
            ssh_config_path = str(payload.get("ssh_config_path") or "").strip()
            if ssh_config_path:
                entry["ssh_config_path"] = ssh_config_path
            elif existing.get("ssh_config_path"):
                entry["ssh_config_path"] = existing["ssh_config_path"]
        if existing.get("labels"):
            entry["labels"] = existing["labels"]

        if match_index is not None:
            overlay["servers"][match_index] = entry
        else:
            overlay["servers"].append(entry)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()
        return entry

    def remove_server(self, server_id: str) -> None:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        overlay = load_user_overlay(self.config_path)
        before = len(overlay["servers"])
        overlay["servers"] = [
            item for item in overlay["servers"] if safe_id(str(item.get("id") or "")) != server_id
        ]
        removed_user_entry = len(overlay["servers"]) != before
        if not removed_user_entry:
            # Treat as a discovery hide.
            server = self.server_by_id(server_id)
            target = server.ssh_alias if server and server.ssh_alias else server_id
            if target not in overlay["disabled_discovery"]:
                overlay["disabled_discovery"].append(target)
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()

    def restore_discovery(self, alias: str) -> None:
        alias = str(alias or "").strip()
        if not alias:
            raise ValueError("alias is required")
        overlay = load_user_overlay(self.config_path)
        overlay["disabled_discovery"] = [item for item in overlay["disabled_discovery"] if item != alias]
        save_user_overlay(self.config_path, overlay)
        self.refresh_status()

    def check_server(self, server_id: str) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        return run_server_checks(server, max(self.config.remote_timeout_seconds, 4))

    def stop_process(self, server_id: str, pid: Any) -> dict[str, Any]:
        server = self.server_by_id(server_id)
        if not server:
            raise ValueError("server not found")
        target_pid = safe_int(pid, 0)
        if target_pid <= 0:
            raise ValueError("invalid pid")
        return stop_server_process(
            server,
            target_pid,
            grace_seconds=10,
        )

    # ── Web Terminal management ──────────────────────────────────────────

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

    def monitor_jobs(self) -> None:
        changed = False
        with self.lock:
            running_jobs = [job for job in self.jobs if job.get("status") == "running"]
            starting_jobs = sorted(
                [job for job in self.jobs if job.get("status") == "starting"],
                key=self.queue_sort_key,
            )
            queued_jobs = sorted(
                [job for job in self.jobs if job.get("status") == "queued"],
                key=self.queue_sort_key,
            )

        for job in running_jobs:
            if self.tmux_running(job):
                continue
            tail = self.tail_log(job, lines=240)
            if "exit_code=0" in tail:
                job["status"] = "done"
            elif "exit_code=" in tail:
                job["status"] = "failed"
            else:
                job["status"] = "done"
            job["finished_at"] = now_iso()
            if job.get("kind") in {"profile", "preset-profile"}:
                target_ids = [str(item) for item in job.get("target_job_ids", [])]
                peak_mib = parse_smoke_peak_mib(tail)
                metadata = job.get("metadata") or {}
                safety = safe_float(metadata.get("profile_safety", metadata.get("safety", 1.2)), 1.2)
                measured_mib = int(peak_mib * max(safety, 1.0)) if peak_mib else 0
                for target in self.jobs:
                    if target.get("id") not in target_ids:
                        continue
                    if job["status"] == "done" and measured_mib > 0:
                        target["min_free_mib"] = measured_mib
                        target["profile_measured_mib"] = peak_mib
                        target["status"] = "queued"
                        target["error"] = f"profile peak {peak_mib} MiB, reserve {measured_mib} MiB"
                    else:
                        target["status"] = "failed"
                        target["error"] = "profile/smoke failed or peak memory not found"
            changed = True

        for job in starting_jobs:
            if job.get("status") == "starting":
                self.start_job(job, allow_busy=True)
                changed = True
        for job in queued_jobs:
            ready, dependency_reason = self.job_dependencies_state(job)
            if not ready:
                if dependency_reason.startswith("dependency failed:"):
                    if job.get("status") != "failed" or job.get("error") != dependency_reason:
                        job["status"] = "failed"
                        job["error"] = dependency_reason
                        job["finished_at"] = now_iso()
                        changed = True
                elif job.get("error") != dependency_reason:
                        job["error"] = dependency_reason
                        changed = True
                continue
            if str(job.get("gpu_index") or "").strip().lower() in {"none", "no_gpu", "cpu"}:
                self.start_job(job, allow_busy=True)
                changed = True
                continue
            ok, _server_id, _gpu, reason = self.find_gpu(job)
            if ok:
                self.start_job(job, allow_busy=False)
                changed = True
            else:
                if job.get("error") != reason:
                    job["error"] = reason
                    changed = True

        if changed:
            self.save_jobs()

    def scheduler_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.refresh_status()
                self.monitor_jobs()
                self.maybe_auto_cleanup_preview_cache()
            except Exception as exc:  # noqa: BLE001 - background loop must keep running.
                print(f"[total-control] scheduler error: {exc}", flush=True)
            self.stop_event.wait(max(self.config.poll_interval_seconds, 2))


STATE: TotalControlState | None = None


class Handler(SimpleHTTPRequestHandler):
    server_version = "TotalControl/0.1"

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        clean = unquote(parsed.path)
        if clean == "/":
            return str(WEB_DIR / "index.html")
        return str(WEB_DIR / clean.lstrip("/"))

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{now_iso()}] {self.address_string()} {format % args}", flush=True)

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, *, content_type: str, disposition: str, filename: str) -> None:
        target = path.expanduser().resolve()
        stat = target.stat()
        encoded_name = quote(filename or target.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Disposition", f"{disposition}; filename*=UTF-8''{encoded_name}")
        self.end_headers()
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def read_body(self) -> dict[str, Any]:
        size = safe_int(self.headers.get("Content-Length"), 0)
        raw = self.rfile.read(size).decode("utf-8") if size else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/status":
                self.send_json(STATE.status_payload())
                return
            if parsed.path == "/api/refresh":
                STATE.refresh_status()
                STATE.monitor_jobs()
                self.send_json(STATE.status_payload())
                return
            if parsed.path == "/api/jobs":
                self.send_json({"jobs": STATE.jobs})
                return
            if parsed.path == "/api/workspaces":
                self.send_json(STATE.list_workspaces())
                return
            if parsed.path == "/api/workflow-templates":
                self.send_json(STATE.list_workflow_templates())
                return
            if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
                template_id = parsed.path.split("/")[3]
                template = STATE.workflow_template_by_id(template_id)
                if not template:
                    self.send_json({"error": "workflow template not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"workflow_template": STATE.workflow_template_public_payload(template)})
                return
            if parsed.path == "/api/agent-definitions":
                self.send_json(STATE.list_agent_definitions())
                return
            if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
                agent_id = parsed.path.split("/")[3]
                agent = STATE.agent_definition_by_id(agent_id)
                if not agent:
                    self.send_json({"error": "agent definition not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"agent_definition": copy.deepcopy(agent)})
                return
            if parsed.path == "/api/tool-definitions":
                self.send_json(STATE.list_tool_definitions())
                return
            if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
                tool_id = parsed.path.split("/")[3]
                tool = STATE.tool_definition_by_id(tool_id)
                if not tool:
                    self.send_json({"error": "tool definition not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"tool_definition": copy.deepcopy(tool)})
                return
            # GET single workspace by ID
            if parsed.path.startswith("/api/workspaces/") and "/" not in parsed.path[16:]:
                workspace_id = parsed.path.split("/")[3]
                workspace = STATE.workspace_by_id(workspace_id)
                if not workspace:
                    self.send_json({"error": "workspace not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"workspace": STATE.workspace_public_payload(workspace)})
                return
            # Provider profiles API
            if parsed.path == "/api/provider-profiles":
                self.send_json(STATE.list_provider_profiles())
                return
            if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
                profile_id = parsed.path.split("/")[3]
                profile = STATE.provider_profile_by_id(profile_id)
                if not profile:
                    self.send_json({"error": "provider profile not found"}, HTTPStatus.NOT_FOUND)
                    return
                # Return masked version
                result = dict(profile)
                if result.get("api_key"):
                    result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
                    del result["api_key"]
                self.send_json({"provider_profile": result})
                return
            if parsed.path == "/api/files/browse":
                query = parse_qs(parsed.query)
                path = (query.get("path") or [""])[0]
                server_id = (query.get("server_id") or [""])[0]
                max_entries = safe_int((query.get("max") or ["300"])[0], 300)
                dirs_only = str((query.get("dirs_only") or ["0"])[0]).lower() in {"1", "true", "yes", "on"}
                self.send_json(
                    STATE.browse_files(
                        server_id=server_id,
                        path_text=path,
                        max_entries=max_entries,
                        dirs_only=dirs_only,
                    )
                )
                return
            if parsed.path == "/api/files/read":
                query = parse_qs(parsed.query)
                path = (query.get("path") or [""])[0]
                server_id = (query.get("server_id") or [""])[0]
                limit = safe_int((query.get("limit") or ["131072"])[0], 131072)
                self.send_json(
                    STATE.read_file_text(
                        server_id=server_id,
                        path_text=path,
                        limit_bytes=limit,
                    )
                )
                return
            if parsed.path.startswith("/api/files/cache/"):
                parts = parsed.path.split("/")
                cache_id = parts[4] if len(parts) >= 5 else ""
                entry = STATE.file_preview_entry(cache_id)
                query = parse_qs(parsed.query)
                download = str((query.get("download") or ["0"])[0]).lower() in {"1", "true", "yes", "on"}
                self.send_file(
                    Path(str(entry.get("local_path") or "")),
                    content_type=str(entry.get("mime_type") or "application/octet-stream"),
                    disposition="attachment" if download else "inline",
                    filename=Path(str(entry.get("source_path") or entry.get("local_path") or "preview")).name or "preview",
                )
                return
            if parsed.path == "/api/admin/servers":
                self.send_json(STATE.list_servers_admin())
                return
            if parsed.path == "/api/admin/preview-cache":
                self.send_json(STATE.preview_cache_status())
                return
            if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/tmux"):
                server_id = parsed.path.split("/")[3]
                try:
                    sessions = STATE.list_tmux_sessions(server_id)
                except ValueError as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self.send_json({"server_id": server_id, "sessions": sessions})
                return
            if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/refresh"):
                server_id = parsed.path.split("/")[3]
                try:
                    server_status = STATE.refresh_server_status(server_id)
                    STATE.monitor_jobs()
                except ValueError as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                payload = STATE.status_payload()
                payload["server"] = server_status
                self.send_json(payload)
                return
            if (
                parsed.path.startswith("/api/servers/")
                and "/tmux/" in parsed.path
                and parsed.path.endswith("/capture")
            ):
                parts = parsed.path.split("/")
                # /api/servers/<id>/tmux/<session>/capture
                if len(parts) >= 7:
                    server_id = parts[3]
                    session = unquote(parts[5])
                    query = parse_qs(parsed.query)
                    lines = safe_int((query.get("lines") or ["10000"])[0], 10000)
                    try:
                        text = STATE.capture_tmux(server_id, session, lines=lines)
                        self.send_json({"server_id": server_id, "session": session, "log": text})
                    except ValueError as exc:
                        self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
            if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/output"):
                parts = parsed.path.split("/")
                # /api/terminal/sessions/<id>/output
                if len(parts) >= 6:
                    terminal_id = parts[4]
                    query = parse_qs(parsed.query)
                    cursor = safe_int((query.get("cursor") or ["0"])[0], 0)
                    self.send_json(STATE.terminal_read(terminal_id, cursor))
                    return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/log"):
                job_id = parsed.path.split("/")[3]
                job = next((item for item in STATE.jobs if item["id"] == job_id), None)
                if not job:
                    self.send_json({"error": "job not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"job_id": job_id, "log": STATE.tail_log(job)})
                return
            if parsed.path.startswith("/api/"):
                self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/workspaces":
                workspace = STATE.create_workspace(self.read_body())
                self.send_json({"workspace": workspace}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/workflow-templates":
                template = STATE.create_workflow_template(self.read_body())
                self.send_json({"workflow_template": template}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/agent-definitions":
                agent = STATE.create_agent_definition(self.read_body())
                self.send_json({"agent_definition": agent}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/tool-definitions":
                tool = STATE.create_tool_definition(self.read_body())
                self.send_json({"tool_definition": tool}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/provider-profiles":
                profile = STATE.create_provider_profile(self.read_body())
                self.send_json({"provider_profile": profile}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/jobs":
                job = STATE.create_job(self.read_body())
                self.send_json({"job": job}, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/task-plans/preview":
                self.send_json(STATE.task_plan_preview(self.read_body()))
                return
            if parsed.path == "/api/files/fetch":
                body = self.read_body()
                self.send_json(
                    STATE.fetch_file_preview(
                        server_id=str(body.get("server_id") or ""),
                        path_text=str(body.get("path") or ""),
                        limit_bytes=safe_int(body.get("limit_bytes"), 131072),
                    )
                )
                return
            if parsed.path == "/api/task-plans/schedule":
                result = STATE.create_task_plan_jobs(self.read_body())
                status = HTTPStatus.OK if result.get("dry_run") else HTTPStatus.CREATED
                self.send_json(result, status)
                return
            if parsed.path == "/api/presets/plan":
                self.send_json(STATE.preset_plan(self.read_body()))
                return
            if parsed.path == "/api/presets/schedule":
                result = STATE.create_preset_jobs(self.read_body())
                status = HTTPStatus.OK if result.get("dry_run") else HTTPStatus.CREATED
                self.send_json(result, status)
                return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/stop"):
                job_id = parsed.path.split("/")[3]
                job = STATE.stop_job(job_id)
                self.send_json({"job": job})
                return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/retry"):
                job_id = parsed.path.split("/")[3]
                job = STATE.retry_job(job_id)
                self.send_json({"job": job}, HTTPStatus.CREATED)
                return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/copy"):
                job_id = parsed.path.split("/")[3]
                job = STATE.copy_job(job_id)
                self.send_json({"job": job}, HTTPStatus.CREATED)
                return
            if (
                parsed.path.startswith("/api/servers/")
                and "/processes/" in parsed.path
                and parsed.path.endswith("/stop")
            ):
                parts = parsed.path.split("/")
                # /api/servers/<id>/processes/<pid>/stop
                if len(parts) >= 7:
                    server_id = parts[3]
                    pid = parts[5]
                    result = STATE.stop_process(server_id, pid)
                    self.send_json(result)
                    return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/reorder"):
                job_id = parsed.path.split("/")[3]
                body = self.read_body()
                result = STATE.reorder_job(job_id, str(body.get("direction") or ""))
                self.send_json(result)
                return
            if parsed.path == "/api/terminal/open":
                result = STATE.terminal_open(str(self.read_body().get("server_id") or ""))
                self.send_json(result, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/terminal/sessions":
                result = STATE.terminal_open(str(self.read_body().get("server_id") or ""))
                self.send_json(result, HTTPStatus.CREATED)
                return
            if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/input"):
                terminal_id = parsed.path.split("/")[4]
                body = self.read_body()
                STATE.terminal_write(terminal_id, str(body.get("data") or ""))
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/terminal/sessions/") and parsed.path.endswith("/signal"):
                terminal_id = parsed.path.split("/")[4]
                body = self.read_body()
                sig = safe_int(body.get("signal"), signal.SIGINT)
                STATE.terminal_signal(terminal_id, sig)
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/admin/servers":
                entry = STATE.add_server(self.read_body())
                self.send_json({"server": entry}, HTTPStatus.CREATED)
                return
            if (
                parsed.path.startswith("/api/agent-definitions/")
                and parsed.path.endswith("/debug")
            ):
                parts = parsed.path.split("/")
                if len(parts) >= 5:
                    agent_id = parts[3]
                    result = STATE.debug_agent_definition(agent_id, self.read_body())
                    self.send_json(result, HTTPStatus.CREATED)
                    return
            if (
                parsed.path.startswith("/api/workspaces/")
                and "/nodes/" in parsed.path
                and parsed.path.endswith("/run")
            ):
                parts = parsed.path.split("/")
                if len(parts) >= 7:
                    workspace_id = parts[3]
                    node_id = parts[5]
                    result = STATE.run_workspace_node(workspace_id, node_id)
                    self.send_json(result, HTTPStatus.CREATED)
                    return
            if (
                parsed.path.startswith("/api/workspaces/")
                and "/agents/" in parsed.path
                and parsed.path.endswith("/debug")
            ):
                parts = parsed.path.split("/")
                if len(parts) >= 7:
                    workspace_id = parts[3]
                    agent_id = parts[5]
                    result = STATE.debug_workspace_agent(workspace_id, agent_id, self.read_body())
                    self.send_json(result, HTTPStatus.CREATED)
                    return
            if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/chat"):
                parts = parsed.path.split("/")
                workspace_id = parts[3] if len(parts) > 3 else ""
                result = STATE.append_workspace_chat(workspace_id, self.read_body())
                self.send_json(result, HTTPStatus.CREATED)
                return
            if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/automation/apply"):
                parts = parsed.path.split("/")
                workspace_id = parts[3] if len(parts) > 3 else ""
                result = STATE.apply_workspace_automation_defaults(workspace_id, self.read_body())
                self.send_json(result)
                return
            if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/discovery/run"):
                parts = parsed.path.split("/")
                workspace_id = parts[3] if len(parts) > 3 else ""
                result = STATE.run_workspace_discovery(workspace_id, self.read_body())
                self.send_json(result, HTTPStatus.CREATED)
                return
            if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/advance"):
                parts = parsed.path.split("/")
                workspace_id = parts[3] if len(parts) > 3 else ""
                result = STATE.advance_workspace_automation(workspace_id, self.read_body())
                status = HTTPStatus.CREATED if result.get("jobs") else HTTPStatus.OK
                self.send_json(result, status)
                return
            if parsed.path.startswith("/api/workspaces/") and parsed.path.endswith("/run"):
                parts = parsed.path.split("/")
                workspace_id = parts[3] if len(parts) > 3 else ""
                try:
                    result = STATE.run_workspace_workflow(workspace_id, self.read_body())
                    self.send_json(result, HTTPStatus.CREATED)
                except WorkspaceWorkflowReadinessError as exc:
                    self.send_json(
                        {
                            "error": str(exc),
                            "blocked_checks": exc.blocked_checks,
                            "workspace": exc.workspace,
                            "applied": exc.applied,
                            "evidence_applied": exc.evidence_applied,
                        },
                        HTTPStatus.CONFLICT,
                    )
                return
            if parsed.path.startswith("/api/workspaces/"):
                workspace_id = parsed.path.split("/")[3] if len(parsed.path.split("/")) > 3 else ""
                workspace = STATE.update_workspace(workspace_id, self.read_body())
                self.send_json({"workspace": workspace})
                return
            if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
                template_id = parsed.path.split("/")[3]
                template = STATE.update_workflow_template(template_id, self.read_body())
                self.send_json({"workflow_template": template})
                return
            if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
                agent_id = parsed.path.split("/")[3]
                agent = STATE.update_agent_definition(agent_id, self.read_body())
                self.send_json({"agent_definition": agent})
                return
            if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
                tool_id = parsed.path.split("/")[3]
                tool = STATE.update_tool_definition(tool_id, self.read_body())
                self.send_json({"tool_definition": tool})
                return
            # PUT provider profiles
            if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
                profile_id = parsed.path.split("/")[3]
                profile = STATE.update_provider_profile(profile_id, self.read_body())
                self.send_json({"provider_profile": profile})
                return
            if (
                parsed.path.startswith("/api/admin/servers/")
                and parsed.path.endswith("/edit")
            ):
                server_id = parsed.path.split("/")[4]
                entry = STATE.update_server(server_id, self.read_body())
                self.send_json({"server": entry})
                return
            if (
                parsed.path.startswith("/api/admin/servers/")
                and parsed.path.endswith("/alias")
            ):
                server_id = parsed.path.split("/")[4]
                body = self.read_body()
                STATE.set_server_alias(server_id, str(body.get("alias") or ""))
                self.send_json({"ok": True})
                return
            if (
                parsed.path.startswith("/api/admin/servers/")
                and parsed.path.endswith("/check")
            ):
                server_id = parsed.path.split("/")[4]
                self.send_json(STATE.check_server(server_id))
                return
            if parsed.path == "/api/admin/discovery/restore":
                body = self.read_body()
                STATE.restore_discovery(str(body.get("alias") or ""))
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/admin/preview-cache/cleanup":
                self.send_json(STATE.cleanup_preview_cache_manual())
                return
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/workspaces/") and "/" not in parsed.path[16:]:
                workspace_id = parsed.path.split("/")[3]
                workspace = STATE.update_workspace(workspace_id, self.read_body())
                self.send_json({"workspace": workspace})
                return
            if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
                template_id = parsed.path.split("/")[3]
                template = STATE.update_workflow_template(template_id, self.read_body())
                self.send_json({"workflow_template": template})
                return
            if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
                agent_id = parsed.path.split("/")[3]
                agent = STATE.update_agent_definition(agent_id, self.read_body())
                self.send_json({"agent_definition": agent})
                return
            if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
                tool_id = parsed.path.split("/")[3]
                tool = STATE.update_tool_definition(tool_id, self.read_body())
                self.send_json({"tool_definition": tool})
                return
            if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
                profile_id = parsed.path.split("/")[3]
                profile = STATE.update_provider_profile(profile_id, self.read_body())
                self.send_json({"provider_profile": profile})
                return
            if parsed.path == "/api/admin/preview-cache/settings":
                body = self.read_body()
                self.send_json(STATE.update_preview_cache_settings(body))
                return
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self.send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:  # noqa: N802
        assert STATE is not None
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/jobs/"):
                job_id = parsed.path.split("/")[3]
                STATE.delete_job(job_id)
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/jobs/clear-completed":
                count = STATE.clear_completed_jobs()
                self.send_json({"deleted": count})
                return
            if parsed.path.startswith("/api/workspaces/"):
                workspace_id = parsed.path.split("/")[3]
                STATE.delete_workspace(workspace_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/workflow-templates/") and "/" not in parsed.path[24:]:
                template_id = parsed.path.split("/")[3]
                STATE.delete_workflow_template(template_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/agent-definitions/") and "/" not in parsed.path[23:]:
                agent_id = parsed.path.split("/")[3]
                STATE.delete_agent_definition(agent_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/tool-definitions/") and "/" not in parsed.path[22:]:
                tool_id = parsed.path.split("/")[3]
                STATE.delete_tool_definition(tool_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/provider-profiles/") and "/" not in parsed.path[19:]:
                profile_id = parsed.path.split("/")[3]
                STATE.delete_provider_profile(profile_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/admin/servers/"):
                server_id = parsed.path.split("/")[4]
                STATE.remove_server(server_id)
                self.send_json({"ok": True})
                return
            if parsed.path.startswith("/api/terminal/sessions/"):
                terminal_id = parsed.path.split("/")[4]
                STATE.terminal_close(terminal_id)
                self.send_json({"ok": True})
                return
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def run(host: str, port: int, config_path: Path) -> None:
    global STATE
    os.chdir(ROOT)
    STATE = TotalControlState(config_path)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[total-control] serving http://{host}:{port}", flush=True)
    print(f"[total-control] config {config_path}", flush=True)
    print("[total-control] press Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STATE:
            STATE.stop_event.set()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="RelayGraph GPU monitor and command launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    run(args.host, args.port, args.config)


if __name__ == "__main__":
    main()
