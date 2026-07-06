"""Shared path safety helpers for workspace-facing tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SENSITIVE_PATH_PATTERN = re.compile(
    r"(^|/)(\.ssh|\.gnupg|\.aws|\.azure|\.config/gcloud|\.kube|\.docker)(/|$)|"
    r"(^|/)(id_rsa|id_ed25519|known_hosts|authorized_keys|\.master_key|\.netrc|\.pypirc|\.npmrc|\.env)(/|\s|$)|"
    r"(^|/)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|secrets|password|passwd|credential|credentials)(\.[^/\s]+)?(/|\s|$)|"
    r"(^|/)run/secrets(/|$)|"
    r"(^|/)proc/[^/\s]+/(environ|cmdline)(/|\s|$)",
    re.IGNORECASE,
)


def sensitive_path_block_reason(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        normalized = text.replace("\\", "/")
        if SENSITIVE_PATH_PATTERN.search(normalized):
            return "路径指向敏感配置、密钥、令牌或进程环境，已阻止读取/枚举。"
    return ""


def sensitive_path_block_reason_for_path(path: Path | str | None) -> str:
    if path is None:
        return ""
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        resolved = Path(path).expanduser()
    return sensitive_path_block_reason(str(path), str(resolved))
