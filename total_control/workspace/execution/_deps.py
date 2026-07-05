"""Shared imports for execution submodules."""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

from ...constants import *  # noqa: F403
from ...utils import *  # noqa: F403
from ..schema import *  # noqa: F403

WORKSPACE_EXECUTION_RUN_KINDS = frozenset({"discovery", "reproduction", "node", "agent_debug", "advance"})
WORKSPACE_EXECUTION_RUN_MAX = 50
WORKSPACE_RUN_EVENT_MAX = 160

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

WORKSPACE_METRIC_PATTERN = re.compile(
    r"(?i)\b(?P<key>"
    r"val[_\s-]?loss|train[_\s-]?loss|test[_\s-]?loss|loss|"
    r"accuracy|acc|top[_\s-]?1|top[_\s-]?5|f1|precision|recall|auc|"
    r"mAP|map|bleu|rouge[_\s-]?l|rougeL|perplexity|ppl|wer|cer|psnr|ssim"
    r")\b\s*[:=]\s*(?P<value>-?\d+(?:\.\d+)?(?:e[-+]?\d+)?%?)"
)
