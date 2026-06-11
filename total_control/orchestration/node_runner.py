from __future__ import annotations

from typing import Any, Literal

from .types import ExecutionRunContext, StepResult

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
    return "skip"


def run_agent_node(
    workspace: dict[str, Any],
    node: dict[str, Any],
    run_context: ExecutionRunContext,
    *,
    debug_runner: Any = None,
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
    payload = {
        "input": str(run_context.outputs.get("input") or "").strip(),
        "node_kind": kind,
        "execute_llm": True,
    }
    result = debug_runner(str(workspace.get("id") or run_context.workspace_id), agent_id, payload)
    status = "completed" if isinstance(result, dict) and result.get("execution") else "warning"
    return StepResult(
        status=status,
        executor="agent",
        output_key=output_key,
        detail="agent node executed via debug runner bridge",
        agent_execution_id=str((result or {}).get("execution", {}).get("id") or ""),
    )
