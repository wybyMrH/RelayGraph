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

    def test_resolve_node_executor_mode_falls_back_to_job_for_human_inspect(self) -> None:
        node = {"kind": "repo.inspect", "handler": {"mode": "human"}}
        self.assertEqual(resolve_node_executor_mode(node), "job")

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

    def test_workflow_edit_and_artifact_write_mutate_workspace(self) -> None:
        from total_control.orchestration.workspace_mutations import apply_artifact_write, apply_workflow_edit

        workspace = {
            "id": "ws-1",
            "nodes": [
                {
                    "id": "node-inspect",
                    "kind": "repo.inspect",
                    "handler": {"mode": "agent", "agent_id": "repo-scout", "output_key": "repo_profile"},
                    "config": {},
                    "artifacts": [],
                }
            ],
            "automation": {"execution_context": {"outputs": {}}},
        }
        edit_result = apply_workflow_edit(
            workspace,
            node_kind="repo.inspect",
            config_patch={"focus_paths": ["README.md", "requirements.txt"]},
        )
        self.assertEqual(edit_result["applied_keys"], ["focus_paths"])
        self.assertEqual(workspace["nodes"][0]["config"]["focus_paths"], ["README.md", "requirements.txt"])

        write_result = apply_artifact_write(
            workspace,
            node_kind="repo.inspect",
            label="repo profile",
            path="artifacts/repo_profile.json",
            content='{"entry":"train.py"}',
        )
        self.assertEqual(write_result["output_key"], "repo_profile")
        self.assertEqual(len(workspace["nodes"][0]["artifacts"]), 1)
        self.assertIn("repo_profile", workspace["automation"]["execution_context"]["outputs"])

    def test_agent_executable_kind_set_contains_phase3_targets(self) -> None:
        for kind in ("repo.inspect", "env.infer", "dataset.find", "eval.report"):
            self.assertIn(kind, AGENT_EXECUTABLE_KINDS)


if __name__ == "__main__":
    unittest.main()
