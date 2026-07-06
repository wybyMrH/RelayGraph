"""Phase 3 #5 — Agent execution metadata persists on the run step."""

from __future__ import annotations

from total_control.orchestration.types import StepResult
from total_control.workspace.execution.runs import (
    normalize_workspace_run_step,
    workspace_run_step_from_agent,
)


def test_agent_meta_persists_and_round_trips():
    node = {"id": "n1", "kind": "repo.inspect", "title": "检查"}
    step = StepResult(
        status="completed",
        executor="agent",
        output_key="repo_profile",
        agent_meta={
            "model": "deepseek-chat",
            "total_tokens": 1234,
            "execution_time_ms": 567.89,
            "max_iterations": 8,
        },
    )
    normalized = workspace_run_step_from_agent(node, step, index=0)
    meta = normalized["agent_meta"]
    assert meta["model"] == "deepseek-chat"
    assert meta["total_tokens"] == 1234
    assert meta["execution_time_ms"] == 567.9  # rounded to 1 dp
    assert meta["max_iterations"] == 8
    # survives a normalize pass (refresh/reopen)
    again = normalize_workspace_run_step(normalized, existing=normalized)
    assert again["agent_meta"] == meta


def test_job_step_has_empty_agent_meta():
    step = normalize_workspace_run_step({"executor": "job", "status": "done", "index": 0})
    assert step["agent_meta"] == {}


def test_agent_meta_absent_when_not_provided():
    node = {"id": "n1", "kind": "env.infer"}
    step = workspace_run_step_from_agent(node, StepResult(status="completed", executor="agent"), 0)
    assert step["agent_meta"] == {}
