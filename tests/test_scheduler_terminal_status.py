from __future__ import annotations

import threading

from total_control import utils
from total_control.config import ServerConfig
from total_control.state.jobs_pkg.execution import ExecutionJobsMixin
from total_control.state.scheduler import SchedulerMixin
from total_control.state.jobs_pkg.execution import _read_text_file_tail


def _runtime_log_path(monkeypatch, tmp_path, name: str):
    root = tmp_path / "logs"
    monkeypatch.setattr(utils, "LOG_DIR", root)
    path = root / "local" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class _SchedulerState(SchedulerMixin):
    def __init__(self, tail: str):
        self.lock = threading.RLock()
        self.jobs = [
            {
                "id": "job-terminal",
                "status": "running",
                "server_id": "local",
                "session": "tc-terminal",
            }
        ]
        self.statuses = []
        self.tail = tail
        self.saved = False
        self.synced = False
        self.events = []

    def queue_sort_key(self, job):
        return (0, str(job.get("id") or ""))

    def tmux_running(self, job):
        return False

    def tail_log(self, job, lines=200):
        return self.tail

    def save_jobs(self):
        self.saved = True

    def sync_workspace_execution_runs_from_jobs(self):
        self.synced = True

    def publish_job_event(self, job, event_type):
        self.events.append((event_type, job["status"], job.get("error", "")))


class _LogDeltaState(SchedulerMixin):
    def __init__(self):
        self.job_log_stream_positions = {}
        self.events = []
        self.server = ServerConfig(id="local", name="Local", mode="local")

    def server_by_id(self, server_id):
        return self.server if server_id == "local" else None

    def publish_event(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))


class _StopJobState(ExecutionJobsMixin):
    def __init__(self):
        self.lock = threading.RLock()
        self.jobs = [{"id": "job-stop", "status": "running", "server_id": "missing", "session": "tc-stop"}]
        self.calls = []

    def server_by_id(self, server_id):
        return None

    def save_jobs(self):
        self.calls.append("save_jobs")

    def sync_workspace_execution_runs_from_jobs(self):
        self.calls.append("sync_runs")

    def publish_job_log_delta(self, job, *, final=False):
        self.calls.append(("log_delta", job["status"], final))
        return True

    def publish_job_event(self, job, event_type):
        self.calls.append((event_type, job["status"]))


class _JobLogPayloadState(ExecutionJobsMixin):
    def __init__(self):
        self.server = ServerConfig(id="local", name="Local", mode="local")

    def server_by_id(self, server_id):
        return self.server if server_id == "local" else None


def test_monitor_jobs_requires_exit_code_marker_for_success():
    state = _SchedulerState("training output\nmetrics ready\n")

    state.monitor_jobs()

    job = state.jobs[0]
    assert job["status"] == "failed"
    assert "exit_code marker" in job["error"]
    assert job["finished_at"]
    assert state.saved is True
    assert state.synced is True
    assert state.events == [("job.updated", "failed", job["error"])]


def test_monitor_jobs_marks_done_only_for_zero_exit_code():
    state = _SchedulerState("ok\n[total-control] exit_code=0\n")

    state.monitor_jobs()

    job = state.jobs[0]
    assert job["status"] == "done"
    assert job["error"] == ""


def test_monitor_jobs_marks_nonzero_exit_code_failed():
    state = _SchedulerState("boom\n[total-control] exit_code=2\n")

    state.monitor_jobs()

    job = state.jobs[0]
    assert job["status"] == "failed"
    assert job["error"] == "process exited with code 2"


def test_job_log_delta_publishes_only_new_tail_text(monkeypatch, tmp_path):
    state = _LogDeltaState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "job.log")
    job = {
        "id": "job-log",
        "status": "running",
        "server_id": "local",
        "log_path": str(log_path),
        "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-1"},
    }

    log_path.write_text("line 1\n", encoding="utf-8")
    assert state.publish_job_log_delta(job) is True
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("line 2\n")
    assert state.publish_job_log_delta(job) is True
    assert state.publish_job_log_delta(job) is False

    assert state.events[0][0] == "job.log.delta"
    assert state.events[0][1]["workspace_id"] == "workspace-1"
    assert state.events[0][1]["run_id"] == "run-1"
    assert state.events[0][1]["job_id"] == "job-log"
    assert state.events[0][1]["payload"]["log"] == "line 1\n"
    assert state.events[1][1]["payload"]["log"] == "line 2\n"


def test_job_log_delta_caps_large_growth(monkeypatch, tmp_path):
    state = _LogDeltaState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "large.log")
    log_path.write_text("0123456789abcdef", encoding="utf-8")
    job = {
        "id": "job-large-log",
        "status": "running",
        "server_id": "local",
        "log_path": str(log_path),
        "metadata": {"workspace_id": "workspace-1", "execution_run_id": "run-1"},
    }

    delta = state.read_job_log_delta(job, max_bytes=8)

    assert delta["log"] == "89abcdef"
    assert delta["offset"] == 8
    assert delta["next_offset"] == 16
    assert delta["truncated"] is True
    assert delta["skipped_bytes"] == 8


def test_local_log_tail_reads_latest_lines_without_full_file(tmp_path):
    log_path = tmp_path / "large-local.log"
    with log_path.open("w", encoding="utf-8") as handle:
        for index in range(6000):
            handle.write(f"line {index}\n")

    tail = _read_text_file_tail(log_path, lines=3)

    assert tail == "line 5997\nline 5998\nline 5999"


def test_job_log_payload_preserves_tail_mode(monkeypatch, tmp_path):
    state = _JobLogPayloadState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "job-tail.log")
    log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    job = {"id": "job-tail", "server_id": "local", "log_path": str(log_path)}

    payload = state.job_log_payload(job, lines=2)

    assert payload["job_id"] == "job-tail"
    assert payload["mode"] == "tail"
    assert payload["log"] == "two\nthree"
    assert payload["line_count"] == 2
    assert payload["source"] == "file"
    assert payload["exists"] is True
    assert payload["next_offset"] == len("one\ntwo\nthree\n".encode("utf-8"))


def test_job_log_payload_prefers_existing_file_over_matching_snapshot(monkeypatch, tmp_path):
    state = _JobLogPayloadState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "job-same.log")
    log_path.write_text("same tail\n", encoding="utf-8")
    job = {
        "id": "job-same",
        "server_id": "local",
        "log_path": str(log_path),
        "metadata": {
            "log_tail_snapshot": {
                "schema": "relaygraph.job.log_tail_snapshot.v1",
                "captured_at": "2026-06-24T10:00:00",
                "tail": "same tail\n",
            }
        },
    }

    payload = state.job_log_payload(job, lines=20)

    assert payload["log"] == "same tail"
    assert payload["source"] == "file"
    assert payload["exists"] is True


def test_job_log_payload_reads_offset_chunk(monkeypatch, tmp_path):
    state = _JobLogPayloadState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "job-chunk.log")
    log_path.write_text("line 1\nline 2\n", encoding="utf-8")
    job = {"id": "job-chunk", "server_id": "local", "log_path": str(log_path)}

    first = state.job_log_payload(job, offset=0, max_bytes=1024)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("line 3\n")
    second = state.job_log_payload(job, offset=first["next_offset"], max_bytes=1024)

    assert first["mode"] == "chunk"
    assert first["log"] == "line 1\nline 2\n"
    assert first["offset"] == 0
    assert first["next_offset"] == len("line 1\nline 2\n".encode("utf-8"))
    assert second["log"] == "line 3\n"
    assert second["offset"] == first["next_offset"]
    assert second["next_offset"] == len("line 1\nline 2\nline 3\n".encode("utf-8"))


def test_job_log_payload_chunk_falls_back_to_snapshot(monkeypatch, tmp_path):
    state = _JobLogPayloadState()
    log_path = _runtime_log_path(monkeypatch, tmp_path, "job-snapshot.log")
    job = {
        "id": "job-snapshot",
        "server_id": "local",
        "log_path": str(log_path),
        "metadata": {
            "log_tail_snapshot": {
                "schema": "relaygraph.job.log_tail_snapshot.v1",
                "captured_at": "2026-06-24T10:00:00",
                "tail": "old line\nsnapshot tail\n",
            }
        },
    }

    payload = state.job_log_payload(job, offset=0, max_bytes=1024)

    assert payload["mode"] == "snapshot"
    assert payload["source"] == "snapshot"
    assert payload["exists"] is False
    assert payload["offset"] == 0
    assert payload["next_offset"] == len("old line\nsnapshot tail".encode("utf-8"))
    assert payload["truncated"] is False
    assert "snapshot tail" in payload["log"]


def test_job_log_payload_rejects_untrusted_external_local_path(tmp_path):
    delta_state = _LogDeltaState()
    payload_state = _JobLogPayloadState()
    log_path = tmp_path / "external.log"
    log_path.write_text("do not expose\n", encoding="utf-8")
    job = {"id": "job-external", "server_id": "local", "log_path": str(log_path)}

    assert delta_state.publish_job_log_delta(job) is False
    tail = payload_state.job_log_payload(job, lines=20)
    chunk = payload_state.job_log_payload(job, offset=0, max_bytes=1024)

    assert tail["log"] == ""
    assert tail["file_size"] == 0
    assert chunk["log"] == ""
    assert chunk["exists"] is False


def test_stop_job_flushes_final_log_delta_before_job_update():
    state = _StopJobState()

    stopped = state.stop_job("job-stop")

    assert stopped["status"] == "stopped"
    assert state.calls[-2:] == [("log_delta", "stopped", True), ("job.updated", "stopped")]
