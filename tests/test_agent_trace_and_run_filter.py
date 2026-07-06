"""Agent trace persistence and run filter helpers."""

from __future__ import annotations

from total_control.workspace.execution import (
    build_agent_execution_trace,
    filter_workspace_execution_runs,
    make_agent_trace_event,
    normalize_workspace_execution_run,
    normalize_agent_trace_events,
    refresh_workspace_execution_run,
    tool_observation_failed,
    workspace_run_step_from_agent,
)


def test_make_and_normalize_agent_trace_events():
    events = [
        make_agent_trace_event(
            "agent.tool.called",
            step_number=1,
            tool_id="repo.read",
            arguments_summary='{"path":"README.md"}',
            side_effect="read",
        ),
        make_agent_trace_event(
            "agent.tool.result",
            step_number=1,
            tool_id="repo.read",
            observation_summary="ok",
            status="ok",
        ),
    ]
    normalized = normalize_agent_trace_events(events)
    assert len(normalized) == 2
    assert normalized[0]["type"] == "agent.tool.called"
    assert normalized[0]["tool_id"] == "repo.read"
    assert normalized[1]["status"] == "ok"


def test_tool_observation_failed_flags_runtime_terminal_failures():
    assert tool_observation_failed('{"status":"failed","job_status":"failed"}') is True
    assert tool_observation_failed('{"status":"timeout","job_status":"running"}') is True
    assert tool_observation_failed('{"status":"done","job_status":"done"}') is False


def test_build_agent_execution_trace_includes_events():
    trace = build_agent_execution_trace(
        "agent-exec-1",
        model="test-model",
        total_tokens=42,
        total_steps=1,
        success=True,
        trace_events=[
            make_agent_trace_event("agent.answer.delta", accumulated="done"),
            make_agent_trace_event(
                "agent.tool.result",
                step_number=1,
                tool_id="env.prepare",
                observation_summary="submitted",
                job_id="job-1",
                run_id="run-1",
                runtime_control="workspace_job_queue",
                runtime_status="submitted",
            ),
        ],
        agent_steps=[
            {
                "step_number": 1,
                "thought": "think",
                "action": "env.prepare",
                "observation": "ok",
                "side_effect": "mutate_runtime",
                "controlled": True,
                "job_id": "job-1",
                "run_id": "run-1",
                "runtime_control": "workspace_job_queue",
                "runtime_status": "submitted",
            }
        ],
    )
    assert trace["id"] == "agent-exec-1"
    assert trace["model"] == "test-model"
    assert trace["total_tokens"] == 42
    assert len(trace["trace_events"]) == 2
    assert trace["trace_events"][0]["type"] == "agent.answer.delta"
    assert trace["trace_events"][1]["job_id"] == "job-1"
    assert trace["trace_events"][1]["run_id"] == "run-1"
    assert trace["trace_events"][1]["runtime_control"] == "workspace_job_queue"
    assert len(trace["steps"]) == 1
    assert trace["steps"][0]["job_id"] == "job-1"
    assert trace["steps"][0]["run_id"] == "run-1"
    assert trace["steps"][0]["runtime_status"] == "submitted"


def test_filter_workspace_execution_runs():
    runs = [
        {
            "id": "run-1",
            "status": "done",
            "created_at": "2026-06-20T10:00:00",
            "steps": [
                {"node_kind": "repo.inspect", "executor": "agent", "agent_execution_id": "agent-1"},
            ],
        },
        {
            "id": "run-2",
            "status": "failed",
            "created_at": "2026-06-24T10:00:00",
            "steps": [
                {"node_kind": "run.command", "executor": "job", "job_id": "job-9"},
            ],
        },
        {
            "id": "run-3",
            "status": "done",
            "created_at": "2026-06-25T10:00:00",
            "steps": [
                {"node_kind": "eval.report", "executor": "agent", "agent_execution_id": "agent-3"},
            ],
        },
    ]
    assert len(filter_workspace_execution_runs(runs, status="done")) == 2
    assert filter_workspace_execution_runs(runs, node_kind="run.command")[0]["id"] == "run-2"
    assert filter_workspace_execution_runs(runs, job_id="job-9")[0]["id"] == "run-2"
    assert filter_workspace_execution_runs(runs, agent_execution_id="agent-1")[0]["id"] == "run-1"
    assert [item["id"] for item in filter_workspace_execution_runs(runs, created_after="2026-06-24T10:00:00")] == [
        "run-2",
        "run-3",
    ]
    assert [item["id"] for item in filter_workspace_execution_runs(runs, created_before="2026-06-24T10:00:00")] == [
        "run-1",
        "run-2",
    ]
    assert [item["id"] for item in filter_workspace_execution_runs(
        runs,
        created_after="2026-06-20T10:00:00",
        created_before="2026-06-24T10:00:00",
    )] == ["run-1", "run-2"]


def test_workspace_agent_run_step_promotes_controlled_runtime_refs():
    step = workspace_run_step_from_agent(
        {"id": "node-agent", "kind": "research.search", "title": "Agent Node"},
        {
            "status": "completed",
            "agent_execution_id": "agent-exec-1",
            "agent_steps": [
                {
                    "step_number": 1,
                    "action": "env.prepare",
                    "job_id": "job-runtime-1",
                    "run_id": "run-runtime-1",
                    "runtime_control": "workspace_job_queue",
                    "runtime_status": "submitted",
                }
            ],
        },
        0,
    )

    assert step["executor"] == "agent"
    assert step["job_id"] == ""
    assert step["child_job_ids"] == ["job-runtime-1"]
    assert step["child_run_ids"] == ["run-runtime-1"]
    assert step["runtime_control"] == "workspace_job_queue"
    assert step["runtime_status"] == "submitted"


def test_refresh_agent_run_step_tracks_child_job_status():
    run = normalize_workspace_execution_run(
        {
            "id": "run-parent",
            "workspace_id": "workspace-1",
            "status": "done",
            "steps": [
                {
                    "index": 0,
                    "node_id": "node-agent",
                    "node_kind": "research.search",
                    "node_title": "Agent Node",
                    "executor": "agent",
                    "status": "done",
                    "child_job_ids": ["job-child"],
                    "child_run_ids": ["run-child"],
                    "runtime_control": "workspace_job_queue",
                    "runtime_status": "submitted",
                    "completed_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
    )

    queued = refresh_workspace_execution_run(
        run,
        {"job-child": {"id": "job-child", "status": "queued"}},
    )
    assert queued["status"] == "running"
    assert queued["steps"][0]["status"] == "running"
    assert queued["steps"][0]["runtime_status"] == "queued"
    assert queued["steps"][0]["completed_at"] == ""

    done = refresh_workspace_execution_run(
        queued,
        {"job-child": {"id": "job-child", "status": "done", "finished_at": "2026-01-01T00:01:00Z"}},
    )
    assert done["status"] == "done"
    assert done["steps"][0]["status"] == "done"
    assert done["steps"][0]["runtime_status"] == "done"

    failed = refresh_workspace_execution_run(
        done,
        {"job-child": {"id": "job-child", "status": "failed", "error": "runtime boom"}},
    )
    assert failed["status"] == "failed"
    assert failed["steps"][0]["status"] == "failed"
    assert failed["steps"][0]["runtime_status"] == "failed"
    assert failed["steps"][0]["error"] == "runtime boom"


def test_refresh_empty_run_materializes_later_bound_job_step():
    run = normalize_workspace_execution_run(
        {
            "id": "run-empty",
            "workspace_id": "workspace-1",
            "status": "pending",
            "steps": [],
        }
    )
    job = {
        "id": "job-later",
        "status": "done",
        "created_at": "2026-07-05T10:00:00",
        "started_at": "2026-07-05T10:00:01",
        "finished_at": "2026-07-05T10:00:02",
        "metadata": {
            "workspace_id": "workspace-1",
            "execution_run_id": "run-empty",
            "step_index": 0,
            "node_id": "manual-smoke",
            "node_kind": "run.command",
            "node_title": "Manual Smoke",
        },
    }

    refreshed = refresh_workspace_execution_run(run, {"job-later": job})

    assert refreshed["status"] == "done"
    assert refreshed["progress"]["total"] == 1
    assert refreshed["progress"]["done"] == 1
    assert refreshed["steps"][0]["job_id"] == "job-later"
    assert refreshed["steps"][0]["status"] == "done"
    assert refreshed["steps"][0]["node_kind"] == "run.command"


def test_refresh_agent_run_step_tracks_child_run_status_without_child_job():
    parent = normalize_workspace_execution_run(
        {
            "id": "run-parent",
            "workspace_id": "workspace-1",
            "status": "done",
            "steps": [
                {
                    "index": 0,
                    "node_id": "node-agent",
                    "node_kind": "research.search",
                    "node_title": "Agent Node",
                    "executor": "agent",
                    "status": "done",
                    "child_run_ids": ["run-child"],
                    "runtime_control": "workspace_job_queue",
                    "runtime_status": "submitted",
                    "completed_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
    )
    child_queued = normalize_workspace_execution_run(
        {
            "id": "run-child",
            "workspace_id": "workspace-1",
            "status": "queued",
            "updated_at": "2026-01-01T00:01:00Z",
            "steps": [{"index": 0, "executor": "job", "status": "queued"}],
        }
    )

    queued = refresh_workspace_execution_run(parent, {}, {"run-parent": parent, "run-child": child_queued})

    assert queued["status"] == "running"
    assert queued["steps"][0]["status"] == "running"
    assert queued["steps"][0]["runtime_status"] == "queued"
    assert queued["steps"][0]["completed_at"] == ""

    child_failed = normalize_workspace_execution_run(
        {
            "id": "run-child",
            "workspace_id": "workspace-1",
            "status": "failed",
            "updated_at": "2026-01-01T00:02:00Z",
            "steps": [
                {
                    "index": 0,
                    "executor": "job",
                    "status": "failed",
                    "error": "child run failed",
                    "completed_at": "2026-01-01T00:02:00Z",
                }
            ],
        }
    )

    failed = refresh_workspace_execution_run(queued, {}, {"run-parent": queued, "run-child": child_failed})

    assert failed["status"] == "failed"
    assert failed["steps"][0]["status"] == "failed"
    assert failed["steps"][0]["runtime_status"] == "failed"
    assert failed["steps"][0]["completed_at"] == "2026-01-01T00:02:00Z"
    assert failed["steps"][0]["error"] == "child run failed"
