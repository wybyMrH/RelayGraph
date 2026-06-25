from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

from .node_runner import ExecutorMode, resolve_node_executor_mode
from .types import ExecutionRunContext, StepResult


@dataclass(slots=True)
class WorkflowRunResult:
    jobs: list[dict[str, Any]] = field(default_factory=list)
    run_steps: list[dict[str, Any]] = field(default_factory=list)
    agent_step_count: int = 0
    stopped_early: bool = False


@dataclass(slots=True)
class WorkflowRunnerCallbacks:
    """Host-provided side effects for mixed Agent + Job workflow execution."""

    refresh_workspace: Callable[[], dict[str, Any]]
    execute_agent_node: Callable[[str, dict[str, Any], ExecutionRunContext], StepResult]
    build_job_payload: Callable[..., dict[str, Any]]
    create_job: Callable[[dict[str, Any]], dict[str, Any]]
    step_from_job: Callable[[dict[str, Any], int], dict[str, Any]]
    step_from_agent: Callable[[dict[str, Any], StepResult, int], dict[str, Any]]
    executable_node_kinds: frozenset[str]
    record_run_steps: Callable[[str, list[dict[str, Any]], list[dict[str, Any]]], Any] | None = None


def run_workflow_sequence(
    workspace_id: str,
    nodes: list[dict[str, Any]],
    workspace: dict[str, Any],
    *,
    executor_prefer: ExecutorMode = "auto",
    automation: dict[str, Any] | None = None,
    until_node_id: str = "",
    target_node: dict[str, Any] | None = None,
    run_id: str = "",
    callbacks: WorkflowRunnerCallbacks,
) -> WorkflowRunResult:
    """Run an ordered node list with auto/job/agent executor resolution."""
    jobs: list[dict[str, Any]] = []
    run_steps: list[dict[str, Any]] = []
    previous_job_id = ""
    agent_step_count = 0
    stopped_early = False
    current_workspace = workspace
    accumulated_outputs: dict[str, Any] = {}
    automation_context = automation if isinstance(automation, dict) else {}
    execution_context = (
        automation_context.get("execution_context")
        if isinstance(automation_context.get("execution_context"), dict)
        else {}
    )
    persisted_outputs = execution_context.get("outputs") if isinstance(execution_context.get("outputs"), dict) else {}
    accumulated_outputs.update(copy.deepcopy(persisted_outputs))
    previous_step_output: dict[str, Any] | None = None

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        mode = resolve_node_executor_mode(node, executor_prefer)
        if mode == "agent":
            current_workspace = callbacks.refresh_workspace()
            run_context = ExecutionRunContext(
                workspace_id=workspace_id,
                run_id=run_id,
                step_index=len(run_steps),
                outputs=copy.deepcopy(accumulated_outputs),
                previous_output=copy.deepcopy(previous_step_output) if previous_step_output else None,
            )
            step_result = callbacks.execute_agent_node(workspace_id, node, run_context)
            if step_result.status in {"completed", "warning"}:
                run_steps.append(callbacks.step_from_agent(node, step_result, len(run_steps)))
                if run_id and callbacks.record_run_steps:
                    callbacks.record_run_steps(run_id, copy.deepcopy(run_steps), copy.deepcopy(jobs))
                agent_step_count += 1
                if step_result.output_key and step_result.output_key in run_context.outputs:
                    accumulated_outputs[step_result.output_key] = run_context.outputs[step_result.output_key]
                    previous_step_output = {
                        "output_key": step_result.output_key,
                        "node_id": str(node.get("id") or "").strip(),
                        "node_kind": str(node.get("kind") or "").strip(),
                        "produced": True,
                        "status": "ready",
                        **(
                            run_context.outputs[step_result.output_key]
                            if isinstance(run_context.outputs[step_result.output_key], dict)
                            else {"value": run_context.outputs[step_result.output_key]}
                        ),
                    }
                continue
            if (
                executor_prefer == "auto"
                and str(node.get("kind") or "").strip() in callbacks.executable_node_kinds
            ):
                mode = "job"
            else:
                run_steps.append(callbacks.step_from_agent(node, step_result, len(run_steps)))
                if run_id and callbacks.record_run_steps:
                    callbacks.record_run_steps(run_id, copy.deepcopy(run_steps), copy.deepcopy(jobs))
                agent_step_count += 1
                stopped_early = True
                break
        if mode == "skip":
            continue
        payload = callbacks.build_job_payload(
            current_workspace,
            node,
            previous_job_id=previous_job_id,
            automation=automation,
        )
        payload["wait_for_idle"] = True
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        metadata["workflow_index"] = index
        if run_id:
            metadata["execution_run_id"] = run_id
            metadata["step_index"] = len(run_steps)
        if until_node_id:
            metadata["workflow_phase"] = "run_to_node"
            metadata["workflow_until_node_id"] = until_node_id
            metadata["workflow_until_node_title"] = str((target_node or {}).get("title") or "").strip()
            metadata["workflow_until_node_kind"] = str((target_node or {}).get("kind") or "").strip()
        payload["metadata"] = metadata
        job = callbacks.create_job(payload)
        jobs.append(job)
        run_steps.append(callbacks.step_from_job(job, len(run_steps)))
        if run_id and callbacks.record_run_steps:
            callbacks.record_run_steps(run_id, copy.deepcopy(run_steps), copy.deepcopy(jobs))
        previous_job_id = str(job.get("id") or "")

    return WorkflowRunResult(
        jobs=jobs,
        run_steps=run_steps,
        agent_step_count=agent_step_count,
        stopped_early=stopped_early,
    )


class WorkflowRunner:
    """Mixed Agent + Job workflow executor with host-provided callbacks."""

    def __init__(self, callbacks: WorkflowRunnerCallbacks) -> None:
        self.callbacks = callbacks

    def run(
        self,
        workspace_id: str,
        nodes: list[dict[str, Any]],
        workspace: dict[str, Any],
        *,
        executor_prefer: ExecutorMode = "auto",
        automation: dict[str, Any] | None = None,
        until_node_id: str = "",
        target_node: dict[str, Any] | None = None,
        run_id: str = "",
    ) -> WorkflowRunResult:
        return run_workflow_sequence(
            workspace_id,
            nodes,
            workspace,
            executor_prefer=executor_prefer,
            automation=automation,
            until_node_id=until_node_id,
            target_node=target_node,
            run_id=run_id,
            callbacks=self.callbacks,
        )
