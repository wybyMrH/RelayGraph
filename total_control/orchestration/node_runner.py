from __future__ import annotations

from typing import Any, Literal

from .input_mapping import build_agent_node_input_text
from .types import ExecutionRunContext, StepResult
from ..tools.registry import summarize_mapped_inputs

ExecutorMode = Literal["auto", "job", "agent", "skip"]

# Phase 3 V1: inspect/infer/report nodes can be delegated to AgentExecutor.
AGENT_EXECUTABLE_KINDS: frozenset[str] = frozenset(
    {
        "repo.inspect",
        "env.infer",
        "dataset.find",
        "eval.report",
        "research.search",
    }
)

# Heavy operations stay on the existing tmux/job queue.
JOB_EXECUTABLE_KINDS: frozenset[str] = frozenset(
    {
        "repo.clone",
        "path.resolve",
        "env.prepare",
        "gpu.allocate",
        "run.command",
        "artifact.collect",
    }
)

# Agent-capable nodes that still have shell job implementations when handler.mode != agent.
SHELL_DISCOVERY_KINDS: frozenset[str] = frozenset(
    {
        "repo.inspect",
        "dataset.find",
        "env.infer",
        "eval.report",
    }
)


def _node_handler_mode(node: dict[str, Any]) -> str:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    return str(handler.get("mode") or "human").strip().lower() or "human"


def _node_agent_id(node: dict[str, Any]) -> str:
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    return str(handler.get("agent_id") or "").strip()


def resolve_node_executor_mode(node: dict[str, Any], prefer: ExecutorMode = "auto") -> ExecutorMode:
    kind = str(node.get("kind") or "").strip()
    if prefer in {"job", "agent", "skip"}:
        return prefer
    if kind in JOB_EXECUTABLE_KINDS:
        return "job"
    if kind in AGENT_EXECUTABLE_KINDS and _node_handler_mode(node) == "agent" and _node_agent_id(node):
        return "agent"
    if kind in SHELL_DISCOVERY_KINDS:
        return "job"
    return "skip"


def run_agent_node(
    workspace: dict[str, Any],
    node: dict[str, Any],
    run_context: ExecutionRunContext,
    *,
    debug_runner: Any = None,
    mapped_inputs: dict[str, Any] | None = None,
    input_text: str = "",
) -> StepResult:
    """Execute an agent-backed node.

    `debug_runner` should be a callable compatible with TotalControlState.debug_workspace_agent
    until WorkflowRunner owns the full execution path.
    """
    kind = str(node.get("kind") or "").strip()
    agent_id = _node_agent_id(node)
    if kind not in AGENT_EXECUTABLE_KINDS:
        return StepResult(skipped=True, reason=f"{kind or 'unknown'} is not agent-executable in V1")
    if _node_handler_mode(node) != "agent" or not agent_id:
        return StepResult(skipped=True, reason="node handler is not configured for agent execution")
    if debug_runner is None:
        return StepResult(
            status="blocked",
            executor="agent",
            reason="agent node runner is not wired yet; use debug_workspace_agent during Phase 3 rollout",
        )

    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    output_key = str(handler.get("output_key") or node.get("output_key") or "").strip()
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    node_title = str(node.get("title") or kind or "node").strip()
    resolved_inputs = mapped_inputs if isinstance(mapped_inputs, dict) else {}
    if not input_text:
        inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
        goal_text = str(inputs.get("goal_text") or workspace.get("brief") or "").strip()
        input_text = build_agent_node_input_text(
            node_kind=kind,
            node_title=node_title,
            output_key=output_key,
            mapped_inputs=resolved_inputs,
            goal_text=goal_text,
            node_config=config,
        )
    payload = {
        "input": input_text,
        "node_kind": kind,
        "output_key": output_key,
        "mapped_inputs": resolved_inputs,
        "execute_llm": True,
    }
    result = debug_runner(str(workspace.get("id") or run_context.workspace_id), agent_id, payload)
    execution = (result or {}).get("execution") if isinstance(result, dict) else {}
    success = bool(isinstance(execution, dict) and execution.get("success"))
    status = "completed" if success else "failed"
    if isinstance(result, dict) and result.get("execution") is None and result.get("debug"):
        status = "blocked"
    artifacts = execution.get("artifacts") if isinstance(execution, dict) and isinstance(execution.get("artifacts"), list) else []
    output_value = execution.get("output_value") if isinstance(execution, dict) else None
    agent_steps = execution.get("steps") if isinstance(execution, dict) and isinstance(execution.get("steps"), list) else []
    if success and output_key and isinstance(output_value, dict):
        run_context.with_output(output_key, output_value)
        run_context.previous_output = {
            "output_key": output_key,
            "node_id": str(node.get("id") or "").strip(),
            "node_kind": kind,
            "produced": True,
            "status": "ready",
            **output_value,
        }
    return StepResult(
        status=status,
        executor="agent",
        output_key=output_key,
        artifacts=[item for item in artifacts if isinstance(item, dict)],
        mapped_inputs=summarize_mapped_inputs(resolved_inputs),
        detail="agent node executed" if success else str(execution.get("error") or "agent execution failed"),
        agent_execution_id=str(execution.get("id") or "") if isinstance(execution, dict) else "",
        agent_steps=[item for item in agent_steps if isinstance(item, dict)],
    )
