"""Phase 3 #3 — Agent step timeout, cancel, and run-step metadata."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from total_control.agent_executor import AgentExecutor
from total_control import agent_runtime
from total_control.orchestration.types import StepResult
from total_control.workspace.execution.runs import (
    normalize_workspace_run_step,
    workspace_run_step_from_agent,
)


class _FakeResp:
    def __init__(self, content: str, success: bool = True):
        self.content = content
        self.success = success
        self.total_tokens = 1
        self.error = ""


class _FakeClient:
    provider = "openai"
    base_url = "x"
    api_key = "k"
    models = ["m"]

    def __init__(self, content: str = '{"tool": "echo", "arguments": {}}'):
        self._content = content

    def chat(self, messages, model=None, **kw):
        return _FakeResp(self._content)

    def chat_stream(self, messages, model=None, on_delta=None, **kw):
        return _FakeResp(self._content)


def _slow_tool(_tool_id: str, _args: dict[str, Any]) -> str:
    time.sleep(0.02)
    return "ok"


def _tools():
    return [{"id": "echo"}]


def test_timeout_aborts_loop_and_flags_result():
    executor = AgentExecutor(
        agent={"max_iterations": 100},
        llm_client=_FakeClient(),  # always emits a tool call → loops forever
        tools=_tools(),
        tool_executor=_slow_tool,
        timeout_seconds=0.1,
    )
    result = executor.run("go")
    assert result.timed_out is True
    assert result.cancelled is False
    assert result.success is False
    assert "timeout" in result.error
    assert result.max_iterations == 100
    assert result.timeout_seconds == 0.1


def test_cancel_aborts_loop_and_flags_result():
    flag = {"on": False}
    executor = AgentExecutor(
        agent={"max_iterations": 100},
        llm_client=_FakeClient(),
        tools=_tools(),
        tool_executor=_slow_tool,
        cancel_check=lambda: flag["on"],
    )

    def trip() -> None:
        time.sleep(0.05)
        flag["on"] = True

    threading.Thread(target=trip).start()
    result = executor.run("go")
    assert result.cancelled is True
    assert result.timed_out is False
    assert result.success is False
    assert result.error == "agent cancelled"


def test_normal_completion_has_no_flags():
    executor = AgentExecutor(
        agent={"max_iterations": 5},
        llm_client=_FakeClient("final answer prose"),  # not a tool call → final answer
        tools=_tools(),
        tool_executor=_slow_tool,
        timeout_seconds=10,
    )
    result = executor.run("go")
    assert result.success is True
    assert result.timed_out is False
    assert result.cancelled is False
    assert result.max_iterations == 5


def test_cancel_registry_round_trip():
    assert agent_runtime.agent_run_is_active("aex-1") is False
    check = agent_runtime.register_agent_cancel("aex-1")
    assert agent_runtime.agent_run_is_active("aex-1") is True
    assert check() is False
    assert agent_runtime.cancel_agent_run("aex-1") is True
    assert check() is True
    agent_runtime.release_agent_cancel("aex-1")
    assert agent_runtime.agent_run_is_active("aex-1") is False
    # cancelling an unknown/not-running id is a no-op
    assert agent_runtime.cancel_agent_run("nope") is False


def test_run_step_surfaces_cancelled_as_stopped():
    node = {"id": "n1", "kind": "repo.inspect", "title": "检查"}
    step = StepResult(
        status="failed",
        executor="agent",
        output_key="repo_profile",
        cancelled=True,
    )
    normalized = workspace_run_step_from_agent(node, step, index=0)
    assert normalized["status"] == "stopped"
    assert normalized["cancelled"] is True
    assert normalized["timed_out"] is False


def test_run_step_surfaces_timed_out():
    node = {"id": "n1", "kind": "env.infer"}
    step = StepResult(status="failed", executor="agent", timed_out=True)
    normalized = workspace_run_step_from_agent(node, step, index=1)
    assert normalized["timed_out"] is True
    assert normalized["status"] == "failed"
    # round-trips through normalize
    again = normalize_workspace_run_step(normalized, existing=normalized)
    assert again["timed_out"] is True


def test_run_step_default_flags_false():
    step = normalize_workspace_run_step({"executor": "job", "status": "done", "index": 0})
    assert step["timed_out"] is False
    assert step["cancelled"] is False


# --- Phase 3 #4: tool policy tagging on agent steps -----------------------

def test_agent_step_records_tool_policy():
    from total_control.agent_executor import AgentExecutor

    class _R:
        success = True
        content = '{"tool": "host.exec", "arguments": {"command": "ls"}}'
        total_tokens = 1
        error = ""

    class _C:
        provider = "openai"; base_url = "x"; api_key = "k"; models = ["m"]
        def chat(self, m, model=None, **k): return _R()
        def chat_stream(self, m, model=None, on_delta=None, **k): return _R()

    executor = AgentExecutor(
        agent={"max_iterations": 2},
        llm_client=_C(),
        tools=[{"id": "host.exec"}],
        tool_executor=lambda t, a: "ok",
    )
    result = executor.run("run ls")
    step = result.steps[0]
    assert step.action == "host.exec"
    assert step.side_effect == "mutate_runtime"
    assert step.controlled is True  # runtime tools go through the job queue
    assert result.to_dict()["steps"][0]["side_effect"] == "mutate_runtime"


def test_dangerous_tool_flagged_not_controlled():
    from total_control.agent_executor import AgentExecutor

    class _R:
        success = True
        content = '{"tool": "job.stop", "arguments": {"job_id": "j1"}}'
        total_tokens = 1
        error = ""

    class _C:
        provider = "openai"; base_url = "x"; api_key = "k"; models = ["m"]
        def chat(self, m, model=None, **k): return _R()
        def chat_stream(self, m, model=None, on_delta=None, **k): return _R()

    executor = AgentExecutor(
        agent={"max_iterations": 2},
        llm_client=_C(),
        tools=[{"id": "job.stop"}],
        tool_executor=lambda t, a: "stopped",
    )
    step = executor.run("stop j1").steps[0]
    assert step.side_effect == "dangerous"
    assert step.controlled is False
