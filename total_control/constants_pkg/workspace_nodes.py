"""Auto-split from constants.py — workspace_nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
            "output_roots": "",
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
            "manifest_paths": "",
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
            "env_manager": "",
            "python_version": "",
            "setup_command": "",
        },
    },
    "gpu.allocate": {
        "title": "分配 GPU",
        "category": "gpu",
        "config_defaults": {
            "server_id": "",
            "gpu_policy": "",
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
            "gpu_policy": "",
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
            "artifact_paths": "",
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
