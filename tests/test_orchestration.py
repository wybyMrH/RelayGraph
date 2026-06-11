import unittest

from total_control.orchestration.node_runner import (
    AGENT_EXECUTABLE_KINDS,
    resolve_node_executor_mode,
    run_agent_node,
)
from total_control.orchestration.types import ExecutionRunContext, StepResult
from total_control.tools.registry import ToolSideEffect, tool_side_effect


class OrchestrationPhase3Tests(unittest.TestCase):
    def test_resolve_node_executor_mode_prefers_job_for_clone(self) -> None:
        node = {"kind": "repo.clone", "handler": {"mode": "agent", "agent_id": "repo-scout"}}
        self.assertEqual(resolve_node_executor_mode(node), "job")

    def test_resolve_node_executor_mode_allows_agent_inspect(self) -> None:
        node = {"kind": "repo.inspect", "handler": {"mode": "agent", "agent_id": "repo-scout"}}
        self.assertEqual(resolve_node_executor_mode(node), "agent")

    def test_run_agent_node_requires_debug_runner_bridge(self) -> None:
        workspace = {"id": "ws-1", "nodes": []}
        node = {
            "kind": "repo.inspect",
            "handler": {"mode": "agent", "agent_id": "repo-scout", "output_key": "repo_profile"},
        }
        result = run_agent_node(workspace, node, ExecutionRunContext(workspace_id="ws-1"))
        self.assertTrue(isinstance(result, StepResult))
        self.assertEqual(result.executor, "agent")
        self.assertEqual(result.status, "blocked")

    def test_tool_side_effect_defaults_to_read(self) -> None:
        self.assertEqual(tool_side_effect("unknown.tool"), ToolSideEffect.READ)
        self.assertEqual(tool_side_effect("workflow.edit"), ToolSideEffect.MUTATE_CONFIG)

    def test_agent_executable_kind_set_contains_phase3_targets(self) -> None:
        for kind in ("repo.inspect", "env.infer", "dataset.find", "eval.report"):
            self.assertIn(kind, AGENT_EXECUTABLE_KINDS)


if __name__ == "__main__":
    unittest.main()
