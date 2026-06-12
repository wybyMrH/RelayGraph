import unittest
from unittest.mock import MagicMock

from total_control.orchestration.types import ExecutionRunContext, StepResult
from total_control.orchestration.workflow_runner import (
    WorkflowRunner,
    WorkflowRunnerCallbacks,
    run_workflow_sequence,
)


class WorkflowRunnerTests(unittest.TestCase):
    def test_run_workflow_sequence_mixed_agent_and_job(self) -> None:
        jobs_created: list[dict] = []
        agent_calls: list[str] = []
        seen_contexts: list[ExecutionRunContext] = []

        def refresh_workspace() -> dict:
            return {"id": "ws-1"}

        def execute_agent_node(ws_id: str, node: dict, ctx: ExecutionRunContext) -> StepResult:
            agent_calls.append(str(node.get("kind") or ""))
            seen_contexts.append(ctx)
            return StepResult(status="completed", executor="agent", output_key="repo_profile")

        def build_job_payload(_workspace: dict, node: dict, **kwargs) -> dict:
            return {"metadata": {"node_kind": node.get("kind")}}

        def create_job(payload: dict) -> dict:
            job = {"id": f"job-{len(jobs_created)}", "metadata": payload.get("metadata", {})}
            jobs_created.append(job)
            return job

        callbacks = WorkflowRunnerCallbacks(
            refresh_workspace=refresh_workspace,
            execute_agent_node=execute_agent_node,
            build_job_payload=build_job_payload,
            create_job=create_job,
            step_from_job=lambda job, index: {"index": index, "executor": "job", "job_id": job["id"], "status": "queued"},
            step_from_agent=lambda node, result, index: {
                "index": index,
                "executor": "agent",
                "node_kind": node.get("kind"),
                "status": "done",
            },
            executable_node_kinds=frozenset({"repo.clone", "repo.inspect", "run.command"}),
        )

        nodes = [
            {"id": "n1", "kind": "repo.inspect", "handler": {"mode": "agent", "agent_id": "repo-scout"}},
            {"id": "n2", "kind": "repo.clone", "handler": {"mode": "human"}},
        ]
        result = run_workflow_sequence(
            "ws-1",
            nodes,
            {"id": "ws-1"},
            executor_prefer="auto",
            callbacks=callbacks,
        )

        self.assertEqual(agent_calls, ["repo.inspect"])
        self.assertEqual(len(seen_contexts), 1)
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0]["metadata"]["node_kind"], "repo.clone")
        self.assertEqual(len(result.run_steps), 2)
        self.assertEqual(result.agent_step_count, 1)

    def test_run_workflow_sequence_propagates_agent_outputs(self) -> None:
        contexts: list[ExecutionRunContext] = []

        def execute_agent_node(_ws_id: str, node: dict, ctx: ExecutionRunContext) -> StepResult:
            contexts.append(ctx)
            kind = str(node.get("kind") or "")
            if kind == "repo.inspect":
                ctx.with_output("repo_profile", {"summary": "entry train.py"})
                return StepResult(status="completed", executor="agent", output_key="repo_profile")
            if kind == "env.infer":
                self.assertIn("repo_profile", ctx.outputs)
                return StepResult(status="completed", executor="agent", output_key="env_requirements")
            return StepResult(status="failed", executor="agent")

        callbacks = WorkflowRunnerCallbacks(
            refresh_workspace=lambda: {"id": "ws-1"},
            execute_agent_node=execute_agent_node,
            build_job_payload=lambda *_args, **_kwargs: {},
            create_job=lambda _payload: {"id": "job-1", "metadata": {}},
            step_from_job=lambda job, index: {"index": index, "executor": "job", "status": "queued"},
            step_from_agent=lambda node, result, index: {"index": index, "executor": "agent", "status": "done"},
            executable_node_kinds=frozenset({"repo.inspect", "env.infer"}),
        )
        nodes = [
            {"id": "n1", "kind": "repo.inspect", "handler": {"mode": "agent", "agent_id": "repo-scout", "output_key": "repo_profile"}},
            {"id": "n2", "kind": "env.infer", "handler": {"mode": "agent", "agent_id": "env-builder", "output_key": "env_requirements"}},
        ]
        result = run_workflow_sequence("ws-1", nodes, {"id": "ws-1"}, callbacks=callbacks)
        self.assertEqual(len(contexts), 2)
        self.assertEqual(result.agent_step_count, 2)
        self.assertFalse(result.stopped_early)

    def test_workflow_runner_class_wraps_sequence(self) -> None:
        callbacks = WorkflowRunnerCallbacks(
            refresh_workspace=lambda: {},
            execute_agent_node=MagicMock(return_value=StepResult(status="completed", executor="agent")),
            build_job_payload=MagicMock(return_value={}),
            create_job=MagicMock(return_value={"id": "job-1", "metadata": {}}),
            step_from_job=lambda job, index: {"index": index, "executor": "job", "status": "queued"},
            step_from_agent=lambda node, result, index: {"index": index, "executor": "agent", "status": "done"},
            executable_node_kinds=frozenset({"repo.clone"}),
        )
        runner = WorkflowRunner(callbacks)
        nodes = [{"id": "n1", "kind": "repo.clone", "handler": {"mode": "human"}}]
        result = runner.run("ws-1", nodes, {"id": "ws-1"})
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(len(result.run_steps), 1)


if __name__ == "__main__":
    unittest.main()
