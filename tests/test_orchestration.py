import unittest

from total_control.orchestration.input_mapping import (
    build_agent_node_input_text,
    resolve_input_mapping_ref,
    resolve_mapped_inputs,
)
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
        runtime_artifacts = workspace["nodes"][0]["runtime"]["artifacts"]
        self.assertEqual(len(runtime_artifacts), 1)
        self.assertIn("repo_profile", workspace["automation"]["execution_context"]["outputs"])

    def test_finalize_agent_executable_nodes_sets_mapping_and_output_key(self) -> None:
        from total_control.server import finalize_agent_executable_nodes, workspace_default_agents

        nodes = [
            {"id": "n1", "kind": "repo.clone", "handler": {"mode": "system", "agent_id": "repo-scout"}},
            {"id": "n2", "kind": "path.resolve", "handler": {"mode": "agent", "agent_id": "repo-scout"}},
            {"id": "n3", "kind": "repo.inspect", "handler": {"mode": "agent", "agent_id": "repo-scout"}},
            {"id": "n4", "kind": "dataset.find", "handler": {"mode": "agent", "agent_id": "researcher"}},
            {"id": "n5", "kind": "env.infer", "handler": {"mode": "agent", "agent_id": "env-builder"}},
        ]
        finalized = finalize_agent_executable_nodes(nodes, workspace_default_agents())
        inspect_node = finalized[2]
        dataset_node = finalized[3]
        self.assertEqual(inspect_node["handler"]["output_key"], "repo_profile")
        self.assertEqual(inspect_node["input_mapping"]["repo_checkout"], "$context.outputs.repo_checkout")
        self.assertEqual(dataset_node["handler"]["output_key"], "dataset_profile")
        self.assertEqual(dataset_node["input_mapping"]["repo_profile"], "$context.outputs.repo_profile")

    def test_agent_executable_kind_set_contains_phase3_targets(self) -> None:
        for kind in ("repo.inspect", "env.infer", "dataset.find", "eval.report"):
            self.assertIn(kind, AGENT_EXECUTABLE_KINDS)

    def test_resolve_input_mapping_ref_reads_context_and_prev(self) -> None:
        input_data = {"goal_text": "train model", "repo_url": "https://example.com/a.git"}
        context_outputs = {
            "repo_profile": {"summary": "entry train.py", "path": "artifacts/repo_profile.json"},
        }
        previous_output = {"output_key": "repo_checkout", "path": "/tmp/repo", "produced": True}
        self.assertEqual(
            resolve_input_mapping_ref("$input.goal_text", input_data=input_data),
            "train model",
        )
        self.assertEqual(
            resolve_input_mapping_ref("$context.outputs.repo_profile", input_data=input_data, context_outputs=context_outputs)["summary"],
            "entry train.py",
        )
        self.assertEqual(
            resolve_input_mapping_ref("$prev.output.path", input_data=input_data, previous_output=previous_output),
            "/tmp/repo",
        )

    def test_resolve_mapped_inputs_builds_agent_prompt(self) -> None:
        mapped = resolve_mapped_inputs(
            {"repo_profile": "$context.outputs.repo_profile", "goal": "$input.goal_text"},
            input_data={"goal_text": "benchmark"},
            context_outputs={"repo_profile": {"summary": "ready"}},
        )
        prompt = build_agent_node_input_text(
            node_kind="env.infer",
            node_title="环境推断",
            output_key="env_requirements",
            mapped_inputs=mapped,
            goal_text="benchmark",
            node_config={"python_version": "3.11"},
        )
        self.assertIn("env.infer", prompt)
        self.assertIn("env_requirements", prompt)
        self.assertIn("repo_profile", prompt)


if __name__ == "__main__":
    unittest.main()
