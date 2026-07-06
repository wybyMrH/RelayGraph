from __future__ import annotations

import threading
import time

from total_control.state.jobs_pkg.execution import ExecutionJobsMixin


class _LaunchState(ExecutionJobsMixin):
    def __init__(self):
        self.lock = threading.RLock()
        self.statuses = []
        self.server_lookup_count = 0

    def tmux_running(self, job):
        return False

    def server_by_id(self, server_id):
        self.server_lookup_count += 1
        raise AssertionError("launching job should not reach server lookup")


def test_start_job_skips_duplicate_launch_attempt():
    state = _LaunchState()
    job = {
        "id": "job-launching",
        "status": "starting",
        "server_id": "local",
        "gpu_index": "none",
        "session": "tc_job_launching",
        "metadata": {"_launching_at": time.time()},
    }

    state.start_job(job, allow_busy=True)

    assert state.server_lookup_count == 0
    assert job["status"] == "starting"
