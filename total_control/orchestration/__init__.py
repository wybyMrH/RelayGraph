"""Workflow orchestration primitives for mixed Job + Agent execution."""

from .node_runner import (
    AGENT_EXECUTABLE_KINDS,
    JOB_EXECUTABLE_KINDS,
    SHELL_DISCOVERY_KINDS,
    resolve_node_executor_mode,
    run_agent_node,
)
from .types import ExecutionRunContext, StepResult

__all__ = [
    "AGENT_EXECUTABLE_KINDS",
    "JOB_EXECUTABLE_KINDS",
    "SHELL_DISCOVERY_KINDS",
    "ExecutionRunContext",
    "StepResult",
    "resolve_node_executor_mode",
    "run_agent_node",
]
