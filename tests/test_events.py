from __future__ import annotations

import copy
import json
import threading
from io import BytesIO

from total_control.events import EventBroker, public_job_event_payload, stream_workspace_events
from total_control.http_api.get_routes import _workspace_events_replay_payload, _workspace_stream_snapshot_event
from total_control.state.base import BaseMixin
from total_control.state.workspaces.runs import RunsMixin
from total_control.workspace.execution import (
    WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX,
    make_agent_trace_event,
    normalize_agent_trace_event,
    normalize_workspace_execution_run,
    normalize_workspace_run_delta_evidence,
    normalize_workspace_run_event,
    workspace_execution_run_export_payload,
    workspace_execution_run_replay_payload,
    workspace_run_delta_evidence_from_event,
)


def test_broker_reports_gap_when_visible_workspace_event_was_evicted():
    broker = EventBroker(maxlen=2)

    broker.publish("run.updated", workspace_id="ws-a")
    broker.publish("run.step.updated", workspace_id="ws-a")
    broker.publish("run.updated", workspace_id="ws-b")
    broker.publish("job.updated", workspace_id="ws-a")

    gap = broker.replay_gap(1, workspace_id="ws-a")

    assert gap is not None
    assert gap["reason"] == "buffer_overflow"
    assert gap["requested_since_id"] == 1
    assert gap["dropped_until_id"] == 2
    assert gap["first_retained_id"] == 4
    assert [event["id"] for event in broker.events_after(1, workspace_id="ws-a")] == [4]


def test_broker_does_not_gap_for_only_unrelated_workspace_evictions():
    broker = EventBroker(maxlen=2)

    broker.publish("run.updated", workspace_id="ws-a")
    broker.publish("run.updated", workspace_id="ws-b")
    broker.publish("run.step.updated", workspace_id="ws-b")
    broker.publish("job.updated", workspace_id="ws-b")

    assert broker.replay_gap(1, workspace_id="ws-a") is None
    assert broker.events_after(1, workspace_id="ws-a") == []


def test_broker_broadcast_eviction_gaps_every_workspace():
    broker = EventBroker(maxlen=2)

    broker.publish("run.updated", workspace_id="ws-a")
    broker.publish("workspace.updated")
    broker.publish("run.updated", workspace_id="ws-b")
    broker.publish("job.updated", workspace_id="ws-b")

    gap = broker.replay_gap(1, workspace_id="ws-a")

    assert gap is not None
    assert gap["reason"] == "buffer_overflow"
    assert gap["dropped_until_id"] == 2


def test_broker_reports_gap_when_client_event_id_is_ahead_of_server():
    broker = EventBroker(maxlen=2)

    gap = broker.replay_gap(99, workspace_id="ws-a")

    assert gap is not None
    assert gap["reason"] == "event_id_reset_or_server_restart"
    assert gap["latest_id"] == 0


class _FakeHandler:
    def __init__(self) -> None:
        self.wfile = BytesIO()
        self.headers = {}
        self.status = None
        self.response_headers = []
        self.ended = False

    def send_response(self, status) -> None:
        self.status = status

    def send_header(self, name: str, value: str) -> None:
        self.response_headers.append((name, value))

    def end_headers(self) -> None:
        self.ended = True


def test_stream_workspace_events_writes_snapshot_prelude_and_exits_when_stopped():
    broker = EventBroker(maxlen=2)
    handler = _FakeHandler()
    stop_event = threading.Event()
    stop_event.set()

    stream_workspace_events(
        handler,
        broker,
        "ws-a",
        since_id=99,
        stop_event=stop_event,
        prelude_events=[
            {
                "id": 0,
                "type": "workspace.snapshot",
                "workspace_id": "ws-a",
                "payload": {"workspace_id": "ws-a"},
            }
        ],
    )

    content = handler.wfile.getvalue().decode("utf-8")
    assert "retry: 3000" in content
    assert "event: workspace.snapshot" in content
    assert '"workspace_id":"ws-a"' in content


class _ReplayState:
    def __init__(self, broker: EventBroker) -> None:
        self.event_broker = broker
        self.lock = threading.RLock()
        self.workspaces = [
            {
                "id": "ws-a",
                "name": "Workspace A",
                "runs": [{"id": "run-a", "workspace_id": "ws-a", "status": "running"}],
                "automation": {"cockpit": {"status": "running"}},
                "execution": {"status": "running"},
            }
        ]
        self.jobs = [
            {
                "id": "job-a",
                "status": "running",
                "log": "secret log should not be embedded",
                "output": "large output should not be embedded",
                "metadata": {"workspace_id": "ws-a", "execution_run_id": "run-a"},
            },
            {
                "id": "job-b",
                "status": "running",
                "metadata": {"workspace_id": "ws-b", "execution_run_id": "run-b"},
            },
        ]
        self.sync_calls = []

    def sync_workspace_execution_runs_from_jobs(self, workspace_id=None):
        self.sync_calls.append(workspace_id)
        return True

    def workspace_by_id(self, workspace_id):
        return next((item for item in self.workspaces if item["id"] == workspace_id), None)

    def workspace_public_payload(self, workspace):
        return copy.deepcopy(workspace)


def test_workspace_events_replay_payload_returns_incremental_events_without_gap():
    broker = EventBroker(maxlen=4)
    broker.publish("run.updated", workspace_id="ws-a", run_id="run-a")
    broker.publish("run.updated", workspace_id="ws-b", run_id="run-b")
    broker.publish("job.updated", workspace_id="ws-a", run_id="run-a", job_id="job-a")
    state = _ReplayState(broker)

    payload = _workspace_events_replay_payload(state, "ws-a", since_id=1, limit=10)

    assert payload["workspace_id"] == "ws-a"
    assert payload["replay_mode"] == "events"
    assert payload["gap"] is None
    assert payload["limited"] is False
    assert [event["type"] for event in payload["events"]] == ["job.updated"]
    assert payload["next_since_id"] == payload["events"][-1]["id"]


def test_workspace_events_replay_payload_returns_snapshot_on_gap():
    broker = EventBroker(maxlen=2)
    broker.publish("run.updated", workspace_id="ws-a", run_id="run-a")
    broker.publish("run.step.updated", workspace_id="ws-a", run_id="run-a")
    broker.publish("run.updated", workspace_id="ws-b", run_id="run-b")
    broker.publish("job.updated", workspace_id="ws-a", run_id="run-a", job_id="job-a")
    state = _ReplayState(broker)

    payload = _workspace_events_replay_payload(state, "ws-a", since_id=1, limit=10)

    assert payload["replay_mode"] == "snapshot"
    assert payload["gap"]["reason"] == "buffer_overflow"
    assert len(payload["events"]) == 1
    snapshot = payload["events"][0]
    assert snapshot["type"] == "workspace.snapshot"
    assert snapshot["workspace_id"] == "ws-a"
    assert snapshot["payload"]["workspace"]["id"] == "ws-a"
    assert snapshot["payload"]["runs"][0]["id"] == "run-a"
    assert [job["id"] for job in snapshot["payload"]["jobs"]] == ["job-a"]
    assert "log" not in snapshot["payload"]["jobs"][0]
    assert "output" not in snapshot["payload"]["jobs"][0]
    assert state.sync_calls == ["ws-a"]


def test_workspace_events_replay_payload_uses_snapshot_when_limit_would_drop_events():
    broker = EventBroker(maxlen=10)
    broker.publish("run.updated", workspace_id="ws-a", run_id="run-a")
    broker.publish("run.step.updated", workspace_id="ws-a", run_id="run-a")
    broker.publish("job.updated", workspace_id="ws-a", run_id="run-a", job_id="job-a")
    broker.publish("agent.step.created", workspace_id="ws-a", run_id="run-a", agent_execution_id="agent-a")
    state = _ReplayState(broker)

    payload = _workspace_events_replay_payload(state, "ws-a", since_id=1, limit=1)

    assert payload["replay_mode"] == "snapshot"
    assert payload["limited"] is True
    assert payload["gap"]["reason"] == "replay_limit_exceeded"
    assert payload["gap"]["retained_count"] == 3
    assert payload["events"][0]["type"] == "workspace.snapshot"


def test_workspace_snapshot_event_uses_high_water_id_before_sync_events():
    broker = EventBroker(maxlen=10)
    broker.publish("run.updated", workspace_id="ws-a", run_id="run-a")
    state = _ReplayState(broker)

    def sync_with_new_event(workspace_id=None):
        state.sync_calls.append(workspace_id)
        broker.publish("run.step.updated", workspace_id="ws-a", run_id="run-a")
        return True

    state.sync_workspace_execution_runs_from_jobs = sync_with_new_event

    snapshot = _workspace_stream_snapshot_event(state, "ws-a", {"reason": "buffer_overflow"})

    assert snapshot["id"] == 1
    assert broker.latest_event_id() == 2
    assert [event["id"] for event in broker.events_after(snapshot["id"], workspace_id="ws-a")] == [2]


class _JobEventPublisher(BaseMixin):
    def __init__(self) -> None:
        self.events = []

    def publish_event(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))
        return {"id": 1, "type": event_type}


class _RunEventState(RunsMixin):
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.workspace_delta_evidence_save_state = {}
        self.save_calls = 0
        self.workspaces = [
            {
                "id": "ws-a",
                "name": "Workspace A",
                "runs": [
                    normalize_workspace_execution_run(
                        {
                            "id": "run-a",
                            "workspace_id": "ws-a",
                            "status": "running",
                            "steps": [],
                        }
                    )
                ],
            }
        ]

    def save_workspaces(self) -> None:
        self.save_calls += 1


def test_publish_job_event_strips_large_log_fields_from_sse_payload():
    state = _JobEventPublisher()
    state.publish_job_event(
        {
            "id": "job-a",
            "status": "done",
            "log": "large log",
            "output": "large output",
            "stdout": "stdout",
            "stderr": "stderr",
            "metadata": {"workspace_id": "ws-a", "execution_run_id": "run-a"},
        }
    )

    event_type, kwargs = state.events[0]
    job = kwargs["payload"]["job"]
    assert event_type == "job.updated"
    assert job["id"] == "job-a"
    assert job["status"] == "done"
    assert "log" not in job
    assert "output" not in job
    assert "stdout" not in job
    assert "stderr" not in job


def test_public_job_event_payload_strips_common_large_fields():
    payload = public_job_event_payload(
        {
            "id": "job-a",
            "log": "log",
            "output": "output",
            "tail": "tail",
            "raw_output": "raw",
        }
    )

    assert payload == {"id": "job-a", "has_log": False, "log_display_path": "", "remote_log_display_path": ""}


def test_public_job_event_payload_redacts_runtime_log_paths(monkeypatch, tmp_path):
    from total_control import utils

    root = tmp_path / "logs"
    log_path = root / "local" / "job-a.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("tail\n", encoding="utf-8")
    monkeypatch.setattr(utils, "LOG_DIR", root)

    payload = public_job_event_payload(
        {
            "id": "job-a",
            "log_path": str(log_path),
            "remote_log_path": "/home/alice/.total_control/logs/job-a.log",
            "metadata": {
                "workspace_id": "ws-a",
                "log_tail_snapshot": {
                    "log_path": str(log_path),
                    "remote_log_path": "/home/alice/.total_control/logs/job-a.log",
                    "tail": "tail\n",
                },
            },
        }
    )
    text = json.dumps(payload, ensure_ascii=False)

    assert payload["has_log"] is True
    assert payload["log_display_path"] == "data/logs/local/job-a.log"
    assert payload["remote_log_display_path"] == "$HOME/.total_control/logs/job-a.log"
    assert "alice" not in text
    assert str(tmp_path) not in text
    assert "log_path" not in payload


def test_public_job_event_payload_keeps_snapshot_log_available_without_raw_path(monkeypatch, tmp_path):
    from total_control import utils

    root = tmp_path / "logs"
    log_path = root / "local" / "snapshot.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("old tail\n", encoding="utf-8")
    monkeypatch.setattr(utils, "LOG_DIR", root)

    payload = public_job_event_payload(
        {
            "id": "job-snapshot",
            "metadata": {
                "log_tail_snapshot": {
                    "log_path": str(log_path),
                    "display_log_path": "/home/alice/private/snapshot.log",
                    "tail": "old tail\n",
                },
            },
        }
    )
    text = json.dumps(payload, ensure_ascii=False)

    assert payload["has_log"] is True
    assert payload["log_display_path"] == ""
    assert payload["metadata"]["log_tail_snapshot"]["display_log_path"] == "data/logs/local/snapshot.log"
    assert "tail" not in payload["metadata"]["log_tail_snapshot"]
    assert "/home/alice" not in text
    assert str(tmp_path) not in text


def test_workspace_run_delta_events_update_summary_without_event_timeline_text():
    state = _RunEventState()
    raw_delta = "RAW_DELTA_SENTINEL_" + ("x" * 900)
    event = {
        "id": 11,
        "type": "agent.message.delta",
        "workspace_id": "ws-a",
        "run_id": "run-a",
        "agent_execution_id": "aex-delta",
        "created_at": "2026-07-06T10:00:00",
        "payload": {
            "delta": raw_delta,
            "accumulated": raw_delta + "_ACCUMULATED_SHOULD_NOT_PERSIST",
            "node_id": "node-agent",
            "final": True,
        },
    }

    assert state.record_workspace_run_event(event) is True

    run = state.workspaces[0]["runs"][0]
    evidence = run["delta_evidence"]
    replay = workspace_execution_run_replay_payload(state.workspaces[0], run, jobs=[])
    replay_text = json.dumps(replay, ensure_ascii=False)

    assert run["events"] == []
    assert replay["event_timeline"] == []
    assert evidence["content_retention"] == "summary_only"
    assert evidence["total_events"] == 1
    assert evidence["total_bytes"] == len(raw_delta.encode("utf-8"))
    assert evidence["agent_execution_ids"] == ["aex-delta"]
    assert evidence["recent"][0]["content"] == "omitted"
    assert raw_delta not in replay_text
    assert "ACCUMULATED_SHOULD_NOT_PERSIST" not in replay_text
    assert state.save_calls == 1


def test_workspace_run_delta_evidence_caps_recent_and_export_is_summary_only():
    evidence = normalize_workspace_run_delta_evidence({})
    sentinel = "RAW_STREAM_SENTINEL_SHOULD_NOT_EXPORT"
    total = WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX + 3
    for index in range(total):
        evidence = workspace_run_delta_evidence_from_event(
            evidence,
            {
                "id": index + 1,
                "type": "job.log.delta",
                "workspace_id": "ws-a",
                "run_id": "run-a",
                "job_id": "job-a",
                "created_at": f"2026-07-06T10:00:{index:02d}",
                "payload": {
                    "log": f"{sentinel}_{index}\n",
                    "byte_count": 0,
                    "truncated": index % 2 == 0,
                    "skipped_bytes": index,
                    "line_count": 1,
                },
            },
        )
    run = normalize_workspace_execution_run(
        {
            "id": "run-a",
            "workspace_id": "ws-a",
            "status": "done",
            "delta_evidence": evidence,
            "steps": [],
        }
    )

    exported = workspace_execution_run_export_payload(
        {"id": "ws-a", "name": "Workspace A", "runs": [run]},
        run,
        jobs=[],
    )
    export_text = json.dumps(exported, ensure_ascii=False)

    assert exported["replay"]["delta_evidence"]["total_events"] == total
    assert len(exported["replay"]["delta_evidence"]["recent"]) == WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX
    assert all(item["content"] == "omitted" for item in exported["replay"]["delta_evidence"]["recent"])
    assert exported["manifest"]["included"]["delta_evidence_events"] == total
    assert exported["manifest"]["limits"]["delta_evidence_recent_per_run"] == WORKSPACE_RUN_DELTA_EVIDENCE_RECENT_MAX
    assert exported["manifest"]["truncation"]["delta_evidence_omitted_content"] is True
    assert "summary-only events" in exported["readme_markdown"]
    assert sentinel not in export_text


def test_agent_trace_delta_and_accumulated_are_summary_only():
    raw_delta = "RAW_TRACE_DELTA_SENTINEL_" + ("d" * 160)
    raw_accumulated = "RAW_TRACE_ACCUMULATED_SENTINEL_" + ("a" * 420)
    event = normalize_agent_trace_event(
        {
            "type": "agent.message.delta",
            "delta": raw_delta,
            "accumulated": raw_accumulated,
        }
    )

    text = json.dumps(event, ensure_ascii=False)
    assert event["content_retention"] == "summary_only"
    assert event["content"] == "omitted"
    assert event["delta_byte_count"] == len(raw_delta.encode("utf-8"))
    assert event["delta_char_count"] == len(raw_delta)
    assert event["accumulated_byte_count"] == len(raw_accumulated.encode("utf-8"))
    assert event["accumulated_char_count"] == len(raw_accumulated)
    assert raw_delta not in text
    assert raw_accumulated not in text


def test_legacy_delta_run_events_are_summary_only_in_replay_and_export():
    raw_delta = "RAW_LEGACY_DELTA_SENTINEL_SHOULD_NOT_EXPORT"
    event = normalize_workspace_run_event(
        {
            "id": 33,
            "type": "agent.message.delta",
            "workspace_id": "ws-a",
            "run_id": "run-a",
            "agent_execution_id": "aex-legacy",
            "created_at": "2026-07-06T10:00:00",
            "payload": {
                "delta": raw_delta,
                "accumulated": raw_delta + "_ACCUMULATED",
                "message": {"id": "msg-a", "role": "assistant", "status": "streaming", "text": raw_delta},
                "byte_count": len(raw_delta.encode("utf-8")),
                "line_count": 1,
            },
        }
    )
    run = normalize_workspace_execution_run(
        {
            "id": "run-a",
            "workspace_id": "ws-a",
            "status": "done",
            "events": [event],
            "steps": [
                {
                    "index": 0,
                    "node_id": "node-agent",
                    "executor": "agent",
                    "trace_events": [
                        make_agent_trace_event(
                            "agent.message.delta",
                            delta=raw_delta,
                            accumulated=raw_delta + "_TRACE_ACCUMULATED",
                        )
                    ],
                }
            ],
        }
    )

    exported = workspace_execution_run_export_payload(
        {"id": "ws-a", "name": "Workspace A", "runs": [run]},
        run,
        jobs=[],
    )
    export_text = json.dumps(exported, ensure_ascii=False)
    event_payload = exported["replay"]["event_timeline"][0]["payload"]
    trace_payload = exported["replay"]["timeline"][0]["trace_events"][0]

    assert event_payload["content_retention"] == "summary_only"
    assert event_payload["content"] == "omitted"
    assert "delta" not in event_payload
    assert "accumulated" not in event_payload
    assert "text" not in event_payload["message"]
    assert trace_payload["content_retention"] == "summary_only"
    assert trace_payload["content"] == "omitted"
    assert "delta" not in trace_payload
    assert "accumulated" not in trace_payload
    assert raw_delta not in export_text


def test_workspace_run_event_persists_agent_tool_replay_details():
    event = normalize_workspace_run_event(
        {
            "id": 7,
            "type": "agent.tool.result",
            "workspace_id": "ws-a",
            "run_id": "run-a",
            "agent_execution_id": "aex-1",
            "created_at": "2026-07-06T10:00:00",
            "payload": {
                "node_id": "node-agent",
                "node_kind": "agent.node",
                "agent_id": "agent-a",
                "job_id": "job-runtime-1",
                "run_id": "run-runtime-1",
                "tool_id": "env.prepare",
                "step_number": 2,
                "arguments_summary": '{"command":"setup"}',
                "observation_summary": "submitted runtime job",
                "runtime_control": "workspace_job_queue",
                "runtime_side_effect": "mutate_runtime",
                "runtime_status": "submitted",
                "execution": {
                    "id": "aex-1",
                    "success": True,
                    "model": "test-model",
                    "total_tokens": 42,
                    "total_steps": 2,
                    "final_answer": "ready",
                },
            },
        }
    )

    replay = workspace_execution_run_replay_payload(
        {"id": "ws-a", "name": "Workspace A"},
        {
            "id": "run-a",
            "workspace_id": "ws-a",
            "status": "done",
            "events": [event],
            "steps": [
                {
                    "index": 0,
                    "node_id": "node-agent",
                    "executor": "agent",
                    "agent_execution_id": "aex-1",
                    "trace_events": [
                        make_agent_trace_event(
                            "agent.tool.result",
                            tool_id="env.prepare",
                            observation_summary="submitted runtime job",
                            job_id="job-runtime-1",
                            run_id="run-runtime-1",
                            runtime_control="workspace_job_queue",
                        )
                    ],
                }
            ],
        },
        jobs=[],
    )

    event_payload = replay["event_timeline"][0]["payload"]
    assert replay["event_timeline"][0]["job_id"] == "job-runtime-1"
    assert replay["event_timeline"][0]["run_id"] == "run-a"
    assert event_payload["job_id"] == "job-runtime-1"
    assert event_payload["run_id"] == "run-runtime-1"
    assert event_payload["tool_id"] == "env.prepare"
    assert event_payload["arguments_summary"] == '{"command":"setup"}'
    assert event_payload["observation_summary"] == "submitted runtime job"
    assert event_payload["runtime_control"] == "workspace_job_queue"
    assert event_payload["runtime_side_effect"] == "mutate_runtime"
    assert event_payload["runtime_status"] == "submitted"
    assert event_payload["execution"]["final_answer"] == "ready"
    step_trace = replay["timeline"][0]["trace_events"][0]
    assert step_trace["tool_id"] == "env.prepare"
    assert step_trace["job_id"] == "job-runtime-1"
    assert step_trace["run_id"] == "run-runtime-1"
    assert step_trace["runtime_control"] == "workspace_job_queue"
