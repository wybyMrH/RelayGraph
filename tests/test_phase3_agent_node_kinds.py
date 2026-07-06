"""Phase 3 #7 — broader Agent node coverage for inspection/summary kinds."""

from __future__ import annotations

from total_control.orchestration.node_runner import (
    AGENT_EXECUTABLE_KINDS,
    resolve_node_executor_mode,
    run_agent_node,
)
from total_control.orchestration.types import ExecutionRunContext
from total_control.constants_pkg.workspace_contracts import AGENT_NODE_DEFAULT_INPUT_MAPPINGS
from total_control.workspace.execution.runs import workspace_run_step_from_agent


def test_path_resolve_and_artifact_collect_are_agent_executable():
    assert "path.resolve" in AGENT_EXECUTABLE_KINDS
    assert "artifact.collect" in AGENT_EXECUTABLE_KINDS


def test_agent_handler_selects_agent_executor_for_path_resolve():
    node = {
        "kind": "path.resolve",
        "handler": {"mode": "agent", "agent_id": "repo-scout"},
    }
    assert resolve_node_executor_mode(node) == "agent"


def test_agent_handler_selects_agent_executor_for_artifact_collect():
    node = {
        "kind": "artifact.collect",
        "handler": {"mode": "agent", "agent_id": "evaluator"},
    }
    assert resolve_node_executor_mode(node) == "agent"


def test_path_resolve_without_agent_handler_stays_job():
    node = {"kind": "path.resolve", "handler": {"mode": "human"}}
    assert resolve_node_executor_mode(node) == "job"


def test_default_input_mappings_include_new_agent_kinds():
    assert "path.resolve" in AGENT_NODE_DEFAULT_INPUT_MAPPINGS
    assert "artifact.collect" in AGENT_NODE_DEFAULT_INPUT_MAPPINGS


def test_forced_runtime_node_agent_execution_blocks_not_skips_done():
    node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "handler": {"mode": "agent", "agent_id": "runner"},
    }

    result = run_agent_node(
        {"id": "workspace-1", "inputs": {"goal_text": "run"}},
        node,
        ExecutionRunContext(workspace_id="workspace-1", run_id="run-1"),
        agent_executor=lambda *_args, **_kwargs: {"execution": {"success": True}},
    )
    step = workspace_run_step_from_agent(node, result, 0)

    assert result.status == "blocked"
    assert result.skipped is False
    assert step["status"] == "blocked"


def test_agent_runtime_tool_failure_blocks_even_with_final_answer():
    node = {
        "id": "env-agent",
        "kind": "env.infer",
        "title": "Infer Env",
        "handler": {"mode": "agent", "agent_id": "runner", "output_key": "env_plan"},
    }

    result = run_agent_node(
        {"id": "workspace-1", "inputs": {"goal_text": "prepare env"}},
        node,
        ExecutionRunContext(workspace_id="workspace-1", run_id="run-1"),
        agent_executor=lambda *_args, **_kwargs: {
            "execution": {
                "success": True,
                "final_answer": "I handled it.",
                "id": "aex-runtime-blocked",
                "steps": [
                    {
                        "action": "env.prepare",
                        "side_effect": "mutate_runtime",
                        "controlled": True,
                        "job_id": "job-runtime",
                        "run_id": "run-runtime",
                        "runtime_control": "workspace_job_queue",
                        "runtime_status": "blocked",
                        "observation": '{"status":"blocked","error":"runtime unavailable"}',
                    }
                ],
            }
        },
    )
    step = workspace_run_step_from_agent(node, result, 0)

    assert result.status == "blocked"
    assert "runtime tool env.prepare blocked" in result.detail
    assert step["status"] == "blocked"
    assert step["child_job_ids"] == ["job-runtime"]
    assert step["runtime_status"] == "blocked"
