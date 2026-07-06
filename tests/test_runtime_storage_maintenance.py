from __future__ import annotations

import copy
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from total_control.config import ServerConfig
from total_control.state.files import FilesMixin
from total_control.state.jobs_pkg.crud import CrudJobsMixin
from total_control.state.jobs_pkg.execution import ExecutionJobsMixin
from total_control.state.servers import ServersMixin
from total_control.state.workspaces.runs import RunsMixin
from total_control import utils
from total_control.workspace.execution import workspace_job_cached_log_tail, workspace_job_cached_log_tail_payload


def _write_log(path: Path, text: str, *, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_local_runtime_log_stats_exposes_newest_and_largest_paths(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    now = time.time()
    _write_log(root / "local" / "old.log", "old\n", mtime=now - 3600)
    _write_log(root / "remote-a" / "new.log", "new\n", mtime=now)
    _write_log(root / "local" / "large.log", "x" * 4096, mtime=now - 120)
    monkeypatch.setattr(utils, "LOG_DIR", root)

    stats = utils.local_runtime_log_stats()

    assert stats["file_count"] == 3
    assert stats["newest_path"] == "data/logs/remote-a/new.log"
    assert stats["largest_path"] == "data/logs/local/large.log"


def test_cleanup_runtime_logs_without_limits_keeps_logs(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    _write_log(root / "local" / "keep.log", "keep\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(remove_all=False)

    assert result["removed_count"] == 0
    assert (root / "local" / "keep.log").exists()


def test_cleanup_runtime_logs_remove_all_is_explicit(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    _write_log(root / "local" / "remove.log", "remove\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(remove_all=True)

    assert result["removed_count"] == 1
    assert not (root / "local" / "remove.log").exists()


def test_cleanup_runtime_logs_remove_all_preserves_active_paths(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    old_path = root / "local" / "remove.log"
    active_path = root / "local" / "active.log"
    _write_log(old_path, "remove\n", mtime=time.time())
    _write_log(active_path, "active\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(remove_all=True, preserve_paths=[str(active_path)])

    assert result["removed_count"] == 1
    assert result["preserved_count"] == 1
    assert not old_path.exists()
    assert active_path.exists()


def test_cleanup_runtime_logs_exact_remove_paths_only(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    target_path = root / "local" / "target.log"
    other_path = root / "local" / "other.log"
    _write_log(target_path, "target\n", mtime=time.time())
    _write_log(other_path, "other\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(remove_paths=[str(target_path)])

    assert result["removed_count"] == 1
    assert not target_path.exists()
    assert other_path.exists()


def test_cleanup_runtime_logs_preserves_active_paths(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    now = time.time()
    old_path = root / "local" / "old.log"
    active_path = root / "local" / "active.log"
    _write_log(old_path, "old\n", mtime=now - 7200)
    _write_log(active_path, "active\n", mtime=now - 7200)
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(max_age_hours=1, preserve_paths=[str(active_path)])

    assert result["removed_count"] == 1
    assert not old_path.exists()
    assert active_path.exists()


def test_cleanup_runtime_logs_removes_oversized_files_but_preserves_active(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    large_path = root / "local" / "large.log"
    active_path = root / "local" / "active.log"
    small_path = root / "local" / "small.log"
    _write_log(large_path, "x" * (2 * 1024 * 1024), mtime=time.time())
    _write_log(active_path, "x" * (2 * 1024 * 1024), mtime=time.time())
    _write_log(small_path, "small\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    result = utils.cleanup_runtime_logs(max_file_mib=1, preserve_paths=[str(active_path)])

    assert result["removed_count"] == 1
    assert result["preserved_count"] == 1
    assert not large_path.exists()
    assert active_path.exists()
    assert small_path.exists()


def test_workspace_cached_log_tail_only_reads_runtime_log_root_regular_files(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    inside = root / "local" / "inside.log"
    outside = tmp_path / "outside.log"
    _write_log(inside, "inside\n", mtime=time.time())
    _write_log(outside, "outside\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    assert workspace_job_cached_log_tail({"log_path": str(inside)}) == "inside"
    payload = workspace_job_cached_log_tail_payload({"log_path": str(inside)}, max_lines=1, max_bytes=4)
    assert payload["tail"] == "ide"
    assert payload["tail_source"] == "file"
    assert payload["truncated"] is True
    assert "byte_window" in payload["truncation_reasons"]
    assert payload["display_log_path"] == "data/logs/local/inside.log"
    assert workspace_job_cached_log_tail({"log_path": str(outside)}) == ""

    symlink_path = root / "local" / "link.log"
    symlink_path.symlink_to(inside)
    assert workspace_job_cached_log_tail({"log_path": str(symlink_path)}) == ""


class _StopProcessState(ServersMixin):
    def __init__(self, *, current_user: str, owner: str, current_uid: str = "1000", owner_uid: str = "1000"):
        self.lock = threading.RLock()
        self.servers = [ServerConfig(id="local", name="Local", mode="local")]
        self.statuses = [
            {
                "id": "local",
                "current_user": current_user,
                "current_uid": current_uid,
                "processes": [
                    {
                        "pid": "123",
                        "uid": owner_uid,
                        "user": owner,
                        "command": "python train.py",
                    }
                ],
            }
        ]

    def server_by_id(self, server_id: str):
        return next((server for server in self.servers if server.id == server_id), None)

    def realtime_process_stop_context(self, server, pid):
        return self.cached_process_stop_context(server.id, pid)


class _RuntimeStorageState(FilesMixin, RunsMixin, ExecutionJobsMixin, CrudJobsMixin):
    def __init__(self, active_log: Path | None = None):
        self.lock = threading.RLock()
        self.file_preview_cache = {}
        self.servers = [ServerConfig(id="local", name="Local", mode="local")]
        self.statuses = []
        self.config = type("Config", (), {"remote_timeout_seconds": 4})()
        self.jobs = []
        self.workspaces = []
        self.saved_jobs = False
        self.saved_workspaces = False
        if active_log:
            self.jobs.append(
                {
                    "id": "job-active",
                    "server_id": "local",
                    "status": "running",
                    "log_path": str(active_log),
                }
            )

    def save_jobs(self):
        self.saved_jobs = True

    def save_workspaces(self):
        self.saved_workspaces = True

    def workspace_by_id(self, workspace_id):
        return next((workspace for workspace in self.workspaces if workspace.get("id") == workspace_id), None)

    def workspace_public_payload(self, workspace):
        return copy.deepcopy(workspace)

    def sync_workspace_execution_runs_from_jobs(self, workspace_id=None):
        return None

    def server_by_id(self, server_id):
        return next((server for server in self.servers if server.id == server_id), None)


def test_manual_runtime_storage_cleanup_uses_request_threshold_and_preserves_active_logs(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    now = time.time()
    old_path = root / "local" / "old.log"
    active_path = root / "local" / "active.log"
    _write_log(old_path, "old\n", mtime=now - 7200)
    _write_log(active_path, "active\n", mtime=now - 7200)
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)

    state = _RuntimeStorageState(active_log=active_path)
    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": False,
            "remove_all": False,
            "log_max_age_hours": 1,
            "log_max_size_mib": 0,
        }
    )

    assert result["local_logs"]["removed_count"] == 1
    assert not old_path.exists()
    assert active_path.exists()


def test_manual_runtime_storage_cleanup_uses_single_file_threshold(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    large_path = root / "local" / "large.log"
    _write_log(large_path, "x" * (2 * 1024 * 1024), mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)

    state = _RuntimeStorageState()
    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": False,
            "remove_all": False,
            "log_max_age_hours": 0,
            "log_max_file_mib": 1,
            "log_max_size_mib": 0,
        }
    )

    assert result["local_logs"]["removed_count"] == 1
    assert not large_path.exists()


def test_manual_runtime_storage_cleanup_passes_exact_remote_remove_paths(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    target_path = root / "local" / "target.log"
    other_path = root / "local" / "other.log"
    _write_log(target_path, "target\n", mtime=time.time())
    _write_log(other_path, "other\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)
    state = _RuntimeStorageState()
    state.servers.append(ServerConfig(id="remote-a", name="Remote A", mode="ssh", enabled=True))
    remote_cleanup_calls = []

    def fake_remote_statuses(**kwargs):
        remote_cleanup_calls.append(kwargs)
        return [{"server_id": "remote-a", "server_name": "Remote A", "removed_count": 1}]

    monkeypatch.setattr(state, "remote_runtime_log_statuses", fake_remote_statuses)

    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": True,
            "remove_all": False,
            "remove_log_paths": {
                "local": [str(target_path)],
                "remote_by_server": {
                    "remote-a": ["$HOME/.total_control/logs/free-smoke.log"],
                },
            },
        }
    )

    assert result["local_logs"]["removed_count"] == 1
    assert not target_path.exists()
    assert other_path.exists()
    assert remote_cleanup_calls[0]["remove_paths_by_server"] == {
        "remote-a": ["$HOME/.total_control/logs/free-smoke.log"]
    }


def test_runtime_state_cleanup_preserves_jobs_referenced_by_retained_runs(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    log_path = root / "local" / "job-retained.log"
    _write_log(log_path, "retained job log\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)
    state = _RuntimeStorageState()
    state.jobs = [
        {
            "id": "job-retained",
            "status": "done",
            "server_id": "local",
            "command": "echo retained",
            "log_path": str(log_path),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-retained"},
        },
        {
            "id": "job-free",
            "status": "done",
            "server_id": "local",
            "command": "echo free",
            "log_path": str(root / "local" / "job-free.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-free"},
        },
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Runtime Cleanup",
            "runs": [
                {
                    "id": "run-retained",
                    "workspace_id": "workspace-1",
                    "kind": "reproduction",
                    "status": "done",
                    "created_at": "2026-06-24T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "run-1",
                            "node_kind": "run.command",
                            "status": "done",
                            "job_id": "job-retained",
                        }
                    ],
                }
            ],
        }
    ]

    result = state.cleanup_runtime_state_manual(
        {
            "clear_completed_jobs": True,
            "prune_workspace_runs": True,
            "max_runs_per_workspace": 20,
        }
    )
    export = state.get_workspace_execution_run_export("workspace-1", "run-retained")["export"]

    assert result["removed_jobs"] == 1
    assert result["preserved_jobs"] == 1
    assert [job["id"] for job in state.jobs] == ["job-retained"]
    assert export["summary"]["linked_job_count"] == 1
    assert export["logs"][0]["job_id"] == "job-retained"


def test_runtime_state_cleanup_preserves_child_run_closure(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    for name in ("parent", "child", "grandchild", "free"):
        _write_log(root / "local" / f"job-{name}.log", f"{name} evidence\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)
    state = _RuntimeStorageState()
    state.jobs = [
        {
            "id": "job-parent",
            "status": "done",
            "server_id": "local",
            "command": "echo parent",
            "log_path": str(root / "local" / "job-parent.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-parent"},
        },
        {
            "id": "job-child",
            "status": "done",
            "server_id": "local",
            "command": "echo child",
            "log_path": str(root / "local" / "job-child.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-child"},
        },
        {
            "id": "job-grandchild",
            "status": "done",
            "server_id": "local",
            "command": "echo grandchild",
            "log_path": str(root / "local" / "job-grandchild.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-grandchild"},
        },
        {
            "id": "job-free",
            "status": "done",
            "server_id": "local",
            "command": "echo free",
            "log_path": str(root / "local" / "job-free.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-free"},
        },
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Runtime Closure",
            "runs": [
                {
                    "id": "run-parent",
                    "workspace_id": "workspace-1",
                    "status": "done",
                    "created_at": "2026-06-24T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "parent",
                            "node_kind": "agent.plan",
                            "status": "done",
                            "job_id": "job-parent",
                            "child_run_ids": ["run-child"],
                        }
                    ],
                },
                {
                    "id": "run-child",
                    "workspace_id": "workspace-1",
                    "status": "done",
                    "created_at": "2026-06-23T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "child",
                            "node_kind": "run.command",
                            "status": "done",
                            "job_id": "job-child",
                            "child_run_ids": ["run-grandchild"],
                        }
                    ],
                },
                {
                    "id": "run-grandchild",
                    "workspace_id": "workspace-1",
                    "status": "done",
                    "created_at": "2026-06-22T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "grandchild",
                            "node_kind": "eval.report",
                            "status": "done",
                            "job_id": "job-grandchild",
                        }
                    ],
                },
                {
                    "id": "run-free",
                    "workspace_id": "workspace-1",
                    "status": "done",
                    "created_at": "2026-06-21T10:00:00",
                    "steps": [{"index": 0, "node_id": "free", "job_id": "job-free"}],
                },
            ],
        }
    ]

    with pytest.raises(ValueError, match="执行记录引用"):
        state.delete_job("job-grandchild")
    result = state.cleanup_runtime_state_manual(
        {
            "clear_completed_jobs": True,
            "prune_workspace_runs": True,
            "max_runs_per_workspace": 1,
        }
    )
    export = state.get_workspace_execution_run_export("workspace-1", "run-parent")["export"]

    assert result["removed_jobs"] == 1
    assert result["preserved_jobs"] == 3
    assert result["removed_runs"] == 1
    assert {job["id"] for job in state.jobs} == {"job-parent", "job-child", "job-grandchild"}
    assert {run["id"] for run in state.workspaces[0]["runs"]} == {"run-parent", "run-child", "run-grandchild"}
    assert export["summary"]["linked_run_count"] == 2
    assert export["summary"]["linked_job_count"] == 3


def test_direct_completed_job_cleanup_preserves_retained_run_references(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    monkeypatch.setattr(utils, "LOG_DIR", root)
    state = _RuntimeStorageState()
    state.jobs = [
        {
            "id": "job-retained",
            "status": "done",
            "server_id": "local",
            "command": "echo retained",
            "log_path": str(root / "local" / "job-retained.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-retained"},
        },
        {
            "id": "job-free",
            "status": "done",
            "server_id": "local",
            "command": "echo free",
            "log_path": str(root / "local" / "job-free.log"),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-free"},
        },
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Direct Cleanup",
            "runs": [
                {
                    "id": "run-retained",
                    "workspace_id": "workspace-1",
                    "status": "done",
                    "steps": [{"index": 0, "node_id": "run-1", "job_id": "job-retained"}],
                }
            ],
        }
    ]

    with pytest.raises(ValueError, match="执行记录引用"):
        state.delete_job("job-retained")
    deleted = state.clear_completed_jobs()

    assert deleted == 1
    assert [job["id"] for job in state.jobs] == ["job-retained"]


def test_runtime_log_cleanup_snapshots_retained_run_job_tail_before_delete(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    log_path = root / "local" / "job-export.log"
    _write_log(log_path, "line one\nfinal export evidence\n", mtime=time.time() - 7200)
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)
    state = _RuntimeStorageState()
    state.jobs = [
        {
            "id": "job-export",
            "status": "done",
            "server_id": "local",
            "command": "echo export",
            "log_path": str(log_path),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-export"},
        }
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Export Evidence",
            "runs": [
                {
                    "id": "run-export",
                    "workspace_id": "workspace-1",
                    "kind": "reproduction",
                    "status": "done",
                    "created_at": "2026-06-24T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "run-1",
                            "node_kind": "run.command",
                            "status": "done",
                            "job_id": "job-export",
                        }
                    ],
                }
            ],
        }
    ]

    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": False,
            "remove_all": True,
        }
    )
    export = state.get_workspace_execution_run_export("workspace-1", "run-export")["export"]
    log_payload = state.job_log_payload(state.jobs[0], lines=80)

    assert result["log_tail_snapshots"]["captured_count"] == 1
    assert result["local_logs"]["removed_count"] == 0
    assert result["local_logs"]["preserved_count"] == 1
    assert log_path.exists()
    assert export["summary"]["log_count"] == 1
    assert export["logs"][0]["tail_source"] == "file"
    assert export["logs"][0]["display_log_path"] == "data/logs/local/job-export.log"
    assert str(tmp_path) not in export["logs"][0]["display_log_path"]
    assert "final export evidence" in export["logs"][0]["tail"]
    assert log_payload["source"] == "file"
    assert "final export evidence" in log_payload["log"]


def test_runtime_log_cleanup_preserves_child_run_job_log(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    child_log = root / "local" / "job-child-export.log"
    stale_log = root / "local" / "stale.log"
    _write_log(child_log, "child retained full log\n", mtime=time.time() - 7200)
    _write_log(stale_log, "stale log\n", mtime=time.time() - 7200)
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)
    state = _RuntimeStorageState()
    state.jobs = [
        {
            "id": "job-child-export",
            "status": "done",
            "server_id": "local",
            "command": "echo child",
            "log_path": str(child_log),
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-child"},
        }
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Child Log Evidence",
            "runs": [
                {
                    "id": "run-parent",
                    "workspace_id": "workspace-1",
                    "kind": "reproduction",
                    "status": "done",
                    "created_at": "2026-06-24T10:00:00",
                    "steps": [{"index": 0, "node_id": "agent", "child_run_ids": ["run-child"]}],
                },
                {
                    "id": "run-child",
                    "workspace_id": "workspace-1",
                    "kind": "node",
                    "status": "done",
                    "created_at": "2026-06-23T10:00:00",
                    "steps": [{"index": 0, "node_id": "child", "job_id": "job-child-export"}],
                },
            ],
        }
    ]

    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": False,
            "remove_all": True,
        }
    )
    export = state.get_workspace_execution_run_export("workspace-1", "run-parent")["export"]

    assert result["local_logs"]["removed_count"] == 1
    assert result["local_logs"]["preserved_count"] == 1
    assert child_log.exists()
    assert not stale_log.exists()
    assert export["logs"][0]["job_id"] == "job-child-export"
    assert export["logs"][0]["tail_source"] == "file"
    assert "child retained full log" in export["logs"][0]["tail"]


def test_runtime_log_cleanup_snapshots_remote_retained_run_job_tail_before_delete(monkeypatch, tmp_path):
    root = tmp_path / "logs"
    preview_root = tmp_path / "preview-cache"
    monkeypatch.setattr(utils, "LOG_DIR", root)
    monkeypatch.setattr(utils, "FILE_PREVIEW_CACHE_DIR", preview_root)
    state = _RuntimeStorageState()
    state.servers.append(ServerConfig(id="remote-a", name="Remote A", mode="ssh", enabled=True))
    state.jobs = [
        {
            "id": "job-remote-export",
            "status": "done",
            "server_id": "remote-a",
            "command": "echo export",
            "log_path": str(root / "remote-a" / "job-remote-export.log"),
            "remote_log_path": "$HOME/.total_control/logs/job-remote-export.log",
            "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-export"},
        }
    ]
    state.workspaces = [
        {
            "id": "workspace-1",
            "name": "Remote Export Evidence",
            "runs": [
                {
                    "id": "run-export",
                    "workspace_id": "workspace-1",
                    "kind": "reproduction",
                    "status": "done",
                    "created_at": "2026-06-24T10:00:00",
                    "steps": [
                        {
                            "index": 0,
                            "node_id": "run-1",
                            "node_kind": "run.command",
                            "status": "done",
                            "job_id": "job-remote-export",
                        }
                    ],
                }
            ],
        }
    ]
    remote_chunks = []
    remote_cleanup_calls = []

    def fake_remote_chunk(job, *, offset=0, max_bytes=131072):
        remote_chunks.append({"job_id": job.get("id"), "offset": offset, "max_bytes": max_bytes})
        return {
            "log": "line one\nfinal remote export evidence\n",
            "offset": 0,
            "next_offset": 39,
            "file_size": 39,
            "byte_count": 39,
            "exists": True,
            "truncated": False,
            "skipped_bytes": 0,
        }

    def fake_remote_statuses(**kwargs):
        remote_cleanup_calls.append(kwargs)
        return [{"server_id": "remote-a", "server_name": "Remote A", "removed_count": 1}]

    state._remote_job_log_chunk = fake_remote_chunk
    monkeypatch.setattr(state, "remote_runtime_log_statuses", fake_remote_statuses)

    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": True,
            "remove_all": True,
        }
    )
    export = state.get_workspace_execution_run_export("workspace-1", "run-export")["export"]
    snapshot = state.jobs[0]["metadata"]["log_tail_snapshot"]

    assert result["log_tail_snapshots"]["captured_count"] == 1
    assert remote_chunks == [{"job_id": "job-remote-export", "offset": 0, "max_bytes": 24000}]
    assert remote_cleanup_calls
    assert remote_cleanup_calls[0]["preserve_paths_by_server"] == {
        "remote-a": ["$HOME/.total_control/logs/job-remote-export.log"]
    }
    assert snapshot["source"] == "remote_runtime_log"
    assert "final remote export evidence" in snapshot["tail"]
    assert snapshot["file_size"] == 39
    assert snapshot["read_bytes"] == 39
    assert snapshot["truncated"] is False
    assert export["summary"]["log_count"] == 1
    assert export["logs"][0]["tail_source"] == "snapshot"
    assert export["logs"][0]["file_size"] == 39
    assert export["logs"][0]["truncated"] is False
    assert "final remote export evidence" in export["logs"][0]["tail"]


def test_manual_runtime_storage_remove_all_preserves_active_local_and_remote_logs(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "logs"
    active_path = root / "local" / "active.log"
    stale_path = root / "local" / "stale.log"
    _write_log(active_path, "active\n", mtime=time.time())
    _write_log(stale_path, "stale\n", mtime=time.time())
    monkeypatch.setattr(utils, "LOG_DIR", root)

    state = _RuntimeStorageState(active_log=active_path)
    state.jobs.append(
        {
            "id": "remote-active",
            "server_id": "remote-a",
            "status": "running",
            "remote_log_path": "$HOME/.total_control/logs/remote-active.log",
        }
    )
    calls = []

    def fake_remote_statuses(**kwargs):
        calls.append(kwargs)
        return [
            {
                "server_id": "remote-a",
                "server_name": "Remote A",
                "removed_bytes": 0,
                "preserved_count": 1,
            }
        ]

    monkeypatch.setattr(state, "remote_runtime_log_statuses", fake_remote_statuses)

    result = state.cleanup_runtime_storage_manual(
        {
            "include_preview": False,
            "include_logs": True,
            "include_remote": True,
            "remove_all": True,
        }
    )

    assert result["local_logs"]["removed_count"] == 1
    assert result["local_logs"]["preserved_count"] == 1
    assert active_path.exists()
    assert not stale_path.exists()
    assert calls
    assert calls[0]["remove_all"] is True
    assert calls[0]["preserve_paths_by_server"] == {
        "remote-a": ["$HOME/.total_control/logs/remote-active.log"]
    }


def test_remote_runtime_log_script_exact_cleanup_preserves_root_and_display_paths(tmp_path):
    home = tmp_path / "remote-home"
    log_root = home / ".total_control" / "logs"
    log_root.mkdir(parents=True)
    free_log = log_root / "free.log"
    retained_log = log_root / "retained.log"
    text_file = log_root / "notes.txt"
    symlink_log = log_root / "retained-link.log"
    outside_log = home / "outside.log"
    _write_log(free_log, "free\n", mtime=time.time())
    _write_log(retained_log, "retained\n", mtime=time.time())
    text_file.write_text("not a runtime log\n", encoding="utf-8")
    outside_log.write_text("outside\n", encoding="utf-8")
    symlink_log.symlink_to(retained_log)

    marker = "__TC_RUNTIME_LOG_JSON__"
    options = {
        "cleanup": True,
        "remove_all": True,
        "preserve_paths": ["$HOME/.total_control/logs/retained.log"],
        "remove_paths": [],
    }
    result = subprocess.run(
        ["python3", "-c", utils.remote_runtime_log_script(), marker, json.dumps(options)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env={**os.environ, "HOME": str(home)},
    )

    assert result.returncode == 0, result.stderr
    payload = utils.parse_remote_marked_json(result.stdout, marker, label="运行日志")
    assert payload["removed_count"] == 1
    assert payload["preserved_count"] == 1
    assert payload["file_count"] == 1
    assert payload["newest_path"] == "$HOME/.total_control/logs/retained.log"
    assert payload["largest_path"] == "$HOME/.total_control/logs/retained.log"
    assert str(home) not in json.dumps(payload, ensure_ascii=False)
    assert not free_log.exists()
    assert retained_log.exists()
    assert text_file.exists()
    assert symlink_log.is_symlink()
    assert outside_log.exists()


def test_stop_process_current_user_does_not_require_confirmation(monkeypatch):
    calls = []

    def fake_stop(server, pid, *, grace_seconds):
        calls.append((server.id, pid, grace_seconds))
        return {"ok": True, "pid": pid}

    monkeypatch.setattr("total_control.state.servers.stop_server_process", fake_stop)
    state = _StopProcessState(current_user="alice", owner="alice")

    result = state.stop_process("local", "123", {})

    assert result["ok"] is True
    assert result["process_stop"]["confirmation_required"] is False
    assert calls == [("local", 123, 10)]


def test_stop_process_check_only_current_user_never_sends_signal(monkeypatch):
    calls = []

    def fake_stop(server, pid, *, grace_seconds):
        calls.append((server.id, pid, grace_seconds))
        return {"ok": True, "pid": pid}

    monkeypatch.setattr("total_control.state.servers.stop_server_process", fake_stop)
    state = _StopProcessState(current_user="alice", owner="alice")

    result = state.stop_process("local", "123", {"check_only": True})

    assert result["ok"] is True
    assert result["check_only"] is True
    assert result["requires_confirmation"] is False
    assert result["would_require_confirmation"] is False
    assert result["process_stop"]["confirmation_required"] is False
    assert calls == []


def test_stop_process_non_owner_requires_explicit_confirmation(monkeypatch):
    calls = []

    def fake_stop(server, pid, *, grace_seconds):
        calls.append((server.id, pid, grace_seconds))
        return {"ok": True, "pid": pid}

    monkeypatch.setattr("total_control.state.servers.stop_server_process", fake_stop)
    state = _StopProcessState(current_user="alice", owner="bob", current_uid="1000", owner_uid="1001")

    with pytest.raises(PermissionError):
        state.stop_process("local", "123", {})

    assert calls == []
    result = state.stop_process("local", "123", {"confirm_non_owner": True})
    assert result["ok"] is True
    assert result["process_stop"]["confirmation_required"] is True
    assert result["process_stop"]["reason"] == "not_current_user"
    assert calls == [("local", 123, 10)]


def test_stop_process_check_only_non_owner_reports_confirmation_without_signal(monkeypatch):
    calls = []

    def fake_stop(server, pid, *, grace_seconds):
        calls.append((server.id, pid, grace_seconds))
        return {"ok": True, "pid": pid}

    monkeypatch.setattr("total_control.state.servers.stop_server_process", fake_stop)
    state = _StopProcessState(current_user="alice", owner="bob", current_uid="1000", owner_uid="1001")

    result = state.stop_process("local", "123", {"check_only": True})

    assert result["ok"] is True
    assert result["check_only"] is True
    assert result["requires_confirmation"] is True
    assert result["would_require_confirmation"] is True
    assert result["process_stop"]["confirmation_required"] is True
    assert result["process_stop"]["reason"] == "not_current_user"
    assert calls == []
