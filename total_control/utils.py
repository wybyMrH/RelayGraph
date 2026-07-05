from __future__ import annotations

import base64
import fnmatch
import json
import mimetypes
import re
import shlex
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .compat import public_api_value
from .constants import *  # noqa: F403

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


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def iso_at(timestamp: float) -> str:
    if timestamp <= 0:
        return ""
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")

def parse_iso_timestamp(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value or "")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def human_file_size(size: int) -> str:
    value = float(max(size, 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

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
    from .infra.shell_pkg.ssh import ssh_command

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
    from .infra.shell_pkg.ssh import ssh_command

    result = ssh_command(server, command, timeout=timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError(output.strip() or "远程文件读取失败")
    payload = parse_remote_marked_json(output, marker, label="文件预览结果")
    payload["server_id"] = server.id
    return payload


def preview_cache_root() -> Path:
    return Path(public_api_value("FILE_PREVIEW_CACHE_DIR", FILE_PREVIEW_CACHE_DIR)).resolve()

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


def normalize_runtime_storage_settings(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    defaults = DEFAULT_RUNTIME_STORAGE_SETTINGS
    return {
        "preview_max_age_hours": max(
            0,
            safe_int(data.get("preview_max_age_hours"), defaults["preview_max_age_hours"]),
        ),
        "preview_max_size_mib": max(
            0,
            safe_int(data.get("preview_max_size_mib"), defaults["preview_max_size_mib"]),
        ),
        "log_max_age_hours": max(0, safe_int(data.get("log_max_age_hours"), defaults["log_max_age_hours"])),
        "log_max_file_mib": max(0, safe_int(data.get("log_max_file_mib"), defaults["log_max_file_mib"])),
        "log_max_size_mib": max(0, safe_int(data.get("log_max_size_mib"), defaults["log_max_size_mib"])),
        "auto_cleanup_interval_minutes": max(
            5,
            safe_int(
                data.get("auto_cleanup_interval_minutes"),
                defaults["auto_cleanup_interval_minutes"],
            ),
        ),
        "remote_log_cleanup_enabled": bool(
            data.get("remote_log_cleanup_enabled", defaults["remote_log_cleanup_enabled"])
        ),
    }

def load_runtime_storage_settings() -> dict[str, Any]:
    raw = read_json(RUNTIME_STORAGE_SETTINGS_PATH, None)
    if isinstance(raw, dict):
        return normalize_runtime_storage_settings(raw)
    preview = load_preview_cache_settings()
    return normalize_runtime_storage_settings(
        {
            **DEFAULT_RUNTIME_STORAGE_SETTINGS,
            "preview_max_age_hours": preview.get("max_age_hours"),
            "preview_max_size_mib": preview.get("max_size_mib"),
        }
    )

def save_runtime_storage_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_runtime_storage_settings(settings)
    write_json(RUNTIME_STORAGE_SETTINGS_PATH, normalized)
    save_preview_cache_settings(
        {
            "max_age_hours": normalized["preview_max_age_hours"],
            "max_size_mib": normalized["preview_max_size_mib"],
        }
    )
    return normalized

def reset_runtime_storage_settings() -> dict[str, Any]:
    return save_runtime_storage_settings(dict(DEFAULT_RUNTIME_STORAGE_SETTINGS))

def runtime_log_root() -> Path:
    return Path(public_api_value("LOG_DIR", LOG_DIR)).resolve()

def is_under_runtime_log_root(path: Path | str) -> bool:
    try:
        Path(path).expanduser().resolve().relative_to(runtime_log_root())
        return True
    except (ValueError, OSError):
        return False

def local_job_log_path_allowed(job: Any, path: Path | str) -> bool:
    path_obj = Path(path).expanduser()
    try:
        if path_obj.is_symlink():
            return False
    except OSError:
        return False
    return is_under_runtime_log_root(path_obj)

def normalize_allowed_local_job_log_path(job: Any, fallback_path: Path | str) -> Path | None:
    data = job if isinstance(job, dict) else {}
    candidates = [data.get("log_path"), fallback_path]
    seen: set[str] = set()
    for candidate in candidates:
        path_text = str(candidate or "").strip()
        if not path_text or path_text in seen:
            continue
        seen.add(path_text)
        path = Path(path_text).expanduser()
        if local_job_log_path_allowed(job, path):
            return path
    return None

def iter_runtime_log_files() -> list[dict[str, Any]]:
    root = runtime_log_root()
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in root.rglob("*.log"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
            stat = resolved.stat()
        except OSError:
            continue
        entries.append(
            {
                "path": resolved,
                "size": int(stat.st_size),
                "mtime": float(stat.st_mtime),
                "server_id": resolved.parent.name if resolved.parent != root else "local",
            }
        )
    return entries

def runtime_log_display_path(path: Any) -> str:
    try:
        resolved = Path(path).expanduser().resolve()
        relative = resolved.relative_to(runtime_log_root())
        return str(Path("data/logs") / relative)
    except (ValueError, OSError, TypeError):
        return ""


def remote_runtime_log_display_path(path: Any) -> str:
    text = str(path or "").strip()
    if not text:
        return ""
    normalized = text
    if normalized.startswith("~/"):
        normalized = "$HOME/" + normalized[2:]
    if normalized == "$HOME/.total_control/logs" or normalized.startswith("$HOME/.total_control/logs/"):
        return normalized
    marker = "/.total_control/logs/"
    if marker in normalized:
        tail = normalized.split(marker, 1)[1].lstrip("/")
        return "$HOME/.total_control/logs/" + tail if tail else "$HOME/.total_control/logs"
    if normalized.endswith("/.total_control/logs"):
        return "$HOME/.total_control/logs"
    return ""


def public_job_payload(job: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(job) if isinstance(job, dict) else {}
    for key in (
        "log",
        "output",
        "stdout",
        "stderr",
        "tail",
        "content",
        "raw_output",
    ):
        snapshot.pop(key, None)
    log_display_path = runtime_log_display_path(snapshot.get("log_path"))
    remote_log_display = remote_runtime_log_display_path(snapshot.get("remote_log_path"))
    snapshot["log_display_path"] = log_display_path
    snapshot["remote_log_display_path"] = remote_log_display
    snapshot.pop("log_path", None)
    snapshot.pop("remote_log_path", None)
    snapshot_has_log = False
    metadata = snapshot.get("metadata") if isinstance(snapshot.get("metadata"), dict) else None
    if metadata is not None:
        metadata = dict(metadata)
        log_tail_snapshot = metadata.get("log_tail_snapshot") if isinstance(metadata.get("log_tail_snapshot"), dict) else None
        if log_tail_snapshot is not None:
            log_tail_snapshot = dict(log_tail_snapshot)
            display_path = runtime_log_display_path(log_tail_snapshot.get("log_path"))
            if not display_path:
                display_path = runtime_log_display_path(log_tail_snapshot.get("display_log_path"))
            remote_display = remote_runtime_log_display_path(log_tail_snapshot.get("remote_log_path"))
            log_tail_snapshot["display_log_path"] = display_path
            log_tail_snapshot["remote_log_path"] = remote_display
            log_tail_snapshot.pop("log_path", None)
            snapshot_has_log = bool(display_path or remote_display or str(log_tail_snapshot.get("tail") or "").strip())
            log_tail_snapshot.pop("tail", None)
            metadata["log_tail_snapshot"] = log_tail_snapshot
        snapshot["metadata"] = metadata
    snapshot["has_log"] = bool(log_display_path or remote_log_display or snapshot_has_log)
    return snapshot

def local_runtime_log_stats() -> dict[str, Any]:
    entries = iter_runtime_log_files()
    total_bytes = sum(int(item["size"]) for item in entries)
    by_server: dict[str, dict[str, Any]] = {}
    for item in entries:
        server_id = str(item.get("server_id") or "local")
        bucket = by_server.setdefault(
            server_id,
            {"server_id": server_id, "file_count": 0, "total_bytes": 0, "newest_mtime": 0.0},
        )
        bucket["file_count"] += 1
        bucket["total_bytes"] += int(item["size"])
        bucket["newest_mtime"] = max(float(bucket["newest_mtime"]), float(item["mtime"]))
    servers = []
    for item in by_server.values():
        servers.append(
            {
                **item,
                "total_text": format_size_text(int(item["total_bytes"])),
                "newest_at": iso_at(float(item["newest_mtime"])),
            }
        )
    servers.sort(key=lambda row: str(row.get("server_id") or ""))
    newest = max((float(item["mtime"]) for item in entries), default=0.0)
    newest_entry = max(entries, key=lambda item: float(item["mtime"]), default=None)
    largest = max(entries, key=lambda item: int(item["size"]), default=None)
    return {
        "log_dir": "data/logs",
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "total_text": format_size_text(total_bytes),
        "newest_at": iso_at(newest),
        "newest_path": runtime_log_display_path(newest_entry["path"]) if newest_entry else "",
        "largest_bytes": int(largest["size"]) if largest else 0,
        "largest_text": format_size_text(int(largest["size"])) if largest else "0 B",
        "largest_path": runtime_log_display_path(largest["path"]) if largest else "",
        "servers": servers,
    }

def runtime_storage_error_summary(error: Any) -> str:
    text = str(error or "").strip()
    lower = text.lower()
    if not text:
        return "远程日志状态读取失败"
    if "permission denied" in lower or "authentication" in lower or "publickey" in lower:
        return "SSH 认证失败，未读取远程日志"
    if "connection refused" in lower:
        return "远程主机拒绝连接，未读取远程日志"
    if "no route to host" in lower or "network is unreachable" in lower:
        return "远程主机网络不可达，未读取远程日志"
    if "timed out" in lower or "timeout" in lower:
        return "远程主机连接超时，未读取远程日志"
    if "could not resolve hostname" in lower:
        return "远程主机名无法解析，未读取远程日志"
    return "远程日志状态读取失败"

def cleanup_runtime_logs(
    *,
    max_age_hours: int = 0,
    max_file_mib: int = 0,
    max_size_mib: int = 0,
    remove_all: bool = False,
    preserve_paths: list[str] | None = None,
    remove_paths: list[str] | None = None,
) -> dict[str, Any]:
    root = runtime_log_root()
    entries = iter_runtime_log_files()
    def normalize_runtime_log_path(value: Any) -> Path | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            if text == "data/logs" or text.startswith("data/logs/"):
                path = root / Path(text).relative_to("data/logs")
            else:
                path = Path(text).expanduser()
                if not path.is_absolute():
                    path = (ROOT / path).resolve()
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            return None
        return resolved

    preserved: set[Path] = set()
    for value in preserve_paths or []:
        resolved = normalize_runtime_log_path(value)
        if resolved is not None:
            preserved.add(resolved)
    targeted: set[Path] = set()
    for value in remove_paths or []:
        resolved = normalize_runtime_log_path(value)
        if resolved is not None:
            targeted.add(resolved)
    to_remove: list[dict[str, Any]] = []
    if targeted:
        to_remove = [item for item in entries if Path(item["path"]).resolve() in targeted]
    elif remove_all:
        to_remove = list(entries)
    else:
        now = time.time()
        remaining = list(entries)
        if max_age_hours > 0:
            cutoff = now - max_age_hours * 3600
            expired = [item for item in remaining if float(item["mtime"]) < cutoff]
            to_remove.extend(expired)
            remaining = [item for item in remaining if item not in expired]
        if max_file_mib > 0:
            file_limit_bytes = max_file_mib * 1024 * 1024
            oversized = [item for item in remaining if int(item["size"]) > file_limit_bytes]
            to_remove.extend(oversized)
            remaining = [item for item in remaining if item not in oversized]
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
    preserved_count = 0
    preserved_bytes = 0
    for item in to_remove:
        path = Path(item["path"])
        if path.resolve() in preserved:
            preserved_count += 1
            preserved_bytes += int(item["size"])
            continue
        if path.is_symlink() or not is_under_runtime_log_root(path):
            continue
        try:
            path.relative_to(root)
        except ValueError:
            continue
        removed_bytes += int(item["size"])
        try:
            path.unlink()
            removed_count += 1
        except OSError:
            pass
    stats = local_runtime_log_stats()
    return {
        "removed_count": removed_count,
        "removed_bytes": removed_bytes,
        "removed_text": format_size_text(removed_bytes),
        "preserved_count": preserved_count,
        "preserved_bytes": preserved_bytes,
        "preserved_text": format_size_text(preserved_bytes),
        "remaining_count": stats["file_count"],
        "remaining_bytes": stats["total_bytes"],
        "remaining_text": stats["total_text"],
    }

def remote_runtime_log_script() -> str:
    return r"""
import base64
import json
import os
import sys
import time

MARKER = sys.argv[1]
OPTIONS = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
ROOT = os.path.expanduser("~/.total_control/logs")
PRESERVE_PATHS = set()

def safe_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default

def iso_at(ts):
    if not ts:
        return ""
    try:
        import datetime
        return datetime.datetime.fromtimestamp(float(ts)).isoformat(timespec="seconds")
    except Exception:
        return ""

def format_size(size):
    value = float(max(int(size or 0), 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

def under_root(path):
    try:
        root = os.path.realpath(ROOT)
        real = os.path.realpath(path)
        return real == root or real.startswith(root.rstrip(os.sep) + os.sep)
    except Exception:
        return False

def normalize_remote_log_path(path):
    text = str(path or "").strip()
    if not text:
        return ""
    if text == "$HOME" or text.startswith("$HOME/"):
        text = os.path.join(os.path.expanduser("~"), text[6:].lstrip("/"))
    text = os.path.expanduser(text)
    try:
        real = os.path.realpath(text)
    except Exception:
        return ""
    return real if under_root(real) else ""

for item in OPTIONS.get("preserve_paths") or []:
    normalized = normalize_remote_log_path(item)
    if normalized:
        PRESERVE_PATHS.add(normalized)
REMOVE_PATHS = set()
for item in OPTIONS.get("remove_paths") or []:
    normalized = normalize_remote_log_path(item)
    if normalized:
        REMOVE_PATHS.add(normalized)

def entries():
    result = []
    if not os.path.isdir(ROOT):
        return result
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            name for name in dirnames
            if not os.path.islink(os.path.join(dirpath, name))
        ]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not name.endswith(".log") or not under_root(path):
                continue
            try:
                stat = os.stat(path)
            except OSError:
                continue
            result.append({"path": path, "size": int(stat.st_size), "mtime": float(stat.st_mtime)})
    return result

def summarize(items, removed_count=0, removed_bytes=0, preserved_count=0, preserved_bytes=0):
    total = sum(int(item["size"]) for item in items)
    newest = max((float(item["mtime"]) for item in items), default=0)
    newest_item = max(items, key=lambda item: float(item["mtime"]), default=None)
    largest = max(items, key=lambda item: int(item["size"]), default=None)
    def display_path(item):
        if not item:
            return ""
        try:
            rel = os.path.relpath(item["path"], ROOT)
        except Exception:
            return "$HOME/.total_control/logs/" + os.path.basename(str(item.get("path") or ""))
        if rel.startswith(".."):
            return "$HOME/.total_control/logs/" + os.path.basename(str(item.get("path") or ""))
        return "$HOME/.total_control/logs/" + rel
    return {
        "log_dir": "$HOME/.total_control/logs",
        "exists": os.path.isdir(ROOT),
        "file_count": len(items),
        "total_bytes": total,
        "total_text": format_size(total),
        "newest_at": iso_at(newest),
        "newest_path": display_path(newest_item),
        "largest_bytes": int(largest["size"]) if largest else 0,
        "largest_text": format_size(int(largest["size"])) if largest else "0 B",
        "largest_path": display_path(largest),
        "removed_count": removed_count,
        "removed_bytes": removed_bytes,
        "removed_text": format_size(removed_bytes),
        "preserved_count": preserved_count,
        "preserved_bytes": preserved_bytes,
        "preserved_text": format_size(preserved_bytes),
    }

items = entries()
removed_count = 0
removed_bytes = 0
preserved_count = 0
preserved_bytes = 0
if OPTIONS.get("cleanup"):
    remove_all = bool(OPTIONS.get("remove_all"))
    max_age_hours = safe_int(OPTIONS.get("max_age_hours"))
    max_file_mib = safe_int(OPTIONS.get("max_file_mib"))
    max_size_mib = safe_int(OPTIONS.get("max_size_mib"))
    to_remove = []
    if REMOVE_PATHS:
        to_remove = [item for item in items if os.path.realpath(item["path"]) in REMOVE_PATHS]
    elif remove_all:
        to_remove = list(items)
    else:
        now = time.time()
        remaining = list(items)
        if max_age_hours > 0:
            cutoff = now - max_age_hours * 3600
            expired = [item for item in remaining if float(item["mtime"]) < cutoff]
            to_remove.extend(expired)
            remaining = [item for item in remaining if item not in expired]
        if max_file_mib > 0:
            file_limit_bytes = max_file_mib * 1024 * 1024
            oversized = [item for item in remaining if int(item["size"]) > file_limit_bytes]
            to_remove.extend(oversized)
            remaining = [item for item in remaining if item not in oversized]
        if max_size_mib > 0:
            limit_bytes = max_size_mib * 1024 * 1024
            total = sum(int(item["size"]) for item in remaining)
            for item in sorted(remaining, key=lambda row: float(row["mtime"])):
                if total <= limit_bytes:
                    break
                if item in to_remove:
                    continue
                to_remove.append(item)
                total -= int(item["size"])
    for item in to_remove:
        path = item["path"]
        if os.path.realpath(path) in PRESERVE_PATHS:
            preserved_count += 1
            preserved_bytes += int(item["size"])
            continue
        if not under_root(path) or os.path.islink(path):
            continue
        try:
            os.remove(path)
            removed_count += 1
            removed_bytes += int(item["size"])
        except OSError:
            pass
    items = entries()

payload = summarize(
    items,
    removed_count=removed_count,
    removed_bytes=removed_bytes,
    preserved_count=preserved_count,
    preserved_bytes=preserved_bytes,
)
encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(MARKER + "_BEGIN")
print(encoded)
print(MARKER + "_END")
"""

def remote_runtime_log_payload(
    server: Any,
    *,
    timeout: int,
    cleanup: bool = False,
    max_age_hours: int = 0,
    max_file_mib: int = 0,
    max_size_mib: int = 0,
    remove_all: bool = False,
    preserve_paths: list[str] | None = None,
    remove_paths: list[str] | None = None,
) -> dict[str, Any]:
    from .infra.shell_pkg.ssh import ssh_command

    marker = "__TC_RUNTIME_LOG_JSON__"
    options = {
        "cleanup": bool(cleanup),
        "max_age_hours": max(0, int(max_age_hours or 0)),
        "max_file_mib": max(0, int(max_file_mib or 0)),
        "max_size_mib": max(0, int(max_size_mib or 0)),
        "remove_all": bool(remove_all),
        "preserve_paths": [str(item) for item in (preserve_paths or []) if str(item or "").strip()],
        "remove_paths": [str(item) for item in (remove_paths or []) if str(item or "").strip()],
    }
    command = (
        "python3 -c "
        + shlex.quote(remote_runtime_log_script())
        + " "
        + shlex.quote(marker)
        + " "
        + shlex.quote(json.dumps(options))
    )
    result = ssh_command(server, command, timeout=timeout)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode != 0:
        raise ValueError((output.strip() or "远程运行日志读取失败")[-1000:])
    payload = parse_remote_marked_json(output, marker, label="运行日志")
    payload["server_id"] = server.id
    payload["server_name"] = server.name
    return payload


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
