"""Bounded local report files for persisted workflow answers; no workflow state here."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from ..path_safety import sensitive_path_block_reason_for_path


class ReportFileError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def report_file_descriptor(workspace_id: str, run_id: str, step_id: str, attempt_id: str,
                           content: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip() or len(content) > 4000:
        raise ReportFileError("report_content_invalid_or_too_long")
    identity = "\0".join((workspace_id, run_id, step_id, attempt_id))
    raw = content.encode("utf-8")
    return {"report_id": hashlib.sha256(identity.encode()).hexdigest(), "run_id": run_id,
            "step_id": step_id, "attempt_id": attempt_id, "host_id": "local",
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _root_path(root: str, *, create: bool = False) -> Path:
    path = Path(root)
    if path.is_symlink():
        raise ReportFileError("report_directory_invalid_or_symlink")
    try:
        canonical = path.resolve()
    except (OSError, RuntimeError) as exc:
        raise ReportFileError("report_directory_invalid_or_symlink") from exc
    if not root or not path.is_absolute() or path != canonical:
        raise ReportFileError("report_directory_invalid_or_symlink")
    if sensitive_path_block_reason_for_path(path):
        raise ReportFileError("report_sensitive_path_blocked")
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise ReportFileError("report_directory_unavailable")
    return path


def read_report_file(root: str, descriptor: dict[str, Any]) -> str:
    """Read only the generated file, bound and hash checked; never repair on reads."""
    try:
        path = _root_path(root) / (descriptor["report_id"] + ".txt")
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ReportFileError("report_not_regular_file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as handle:
            current = os.fstat(handle.fileno())
            if (not stat.S_ISREG(current.st_mode) or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)):
                raise ReportFileError("report_file_changed_during_read")
            if current.st_size != descriptor["size_bytes"]:
                raise ReportFileError("report_file_hash_or_size_mismatch")
            raw = handle.read(descriptor["size_bytes"] + 1)
        if len(raw) != descriptor["size_bytes"] or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
            raise ReportFileError("report_file_hash_or_size_mismatch")
        return raw.decode("utf-8")
    except FileNotFoundError as exc:
        raise ReportFileError("report_file_missing") from exc
    except (OSError, UnicodeError) as exc:
        raise ReportFileError("report_file_unreadable") from exc


def publish_report_file(root: str, descriptor: dict[str, Any], content: str) -> None:
    """Publish without overwriting. Re-entry can adopt exactly the expected bytes."""
    temp_path = None
    try:
        directory = _root_path(root, create=True)
        path = directory / (descriptor["report_id"] + ".txt")
        if os.path.lexists(path):
            read_report_file(root, descriptor)
            return
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".report-", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        # Hardlink creation is atomic and fails if the destination already exists.
        # An interrupted process leaves either no target or the whole fsynced file.
        _root_path(root)
        try:
            os.link(temp_path, path)
        except FileExistsError:
            pass  # Concurrent/existing content must still pass the same check.
        read_report_file(root, descriptor)
    except OSError as exc:
        raise ReportFileError("report_file_publish_failed") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass  # An orphan temporary file cannot invalidate an already verified target.


def report_file_view(root: str, descriptor: dict[str, Any], receipt: dict[str, Any] | None) -> dict[str, Any]:
    """Public current verification, separate from the immutable Agent answer."""
    view = {**descriptor, "path": "report:" + descriptor["report_id"], "type": "report",
            "label": "evaluation_report", "source": "persisted-agent-answer",
            "exists": False, "file_verified": False, "status": "incomplete", "content": None,
            "reason": "report_file_not_written_or_verified", "verified_at": ""}
    if not receipt:
        return view
    if any(receipt.get(k) != v for k, v in descriptor.items()):
        view["reason"] = "report_receipt_identity_mismatch"
        return view
    view["verified_at"] = receipt.get("verified_at", "")
    if receipt.get("status") != "verified":
        view["reason"] = receipt.get("error") or "report_file_pending"
        return view
    try:
        view["content"] = read_report_file(root, descriptor)
        view.update(exists=True, file_verified=True, status="ready", reason="")
    except ReportFileError as exc:
        view["reason"] = exc.code
    return view
