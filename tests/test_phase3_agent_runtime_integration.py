"""Phase 3 integration — real workspace agent path + controlled runtime tool."""

from __future__ import annotations

import json
from pathlib import Path

from total_control.llm_client import LLMResponse
from total_control.orchestration.types import StepResult
from total_control.state import TotalControlState
from total_control.workspace.cockpit.payload import normalize_workspace_payload
from total_control.workspace.execution import normalize_workspace_execution_run


def _isolated_runtime_paths(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    paths = {
        "jobs": runtime_dir / "jobs.json",
        "workspaces": runtime_dir / "workspaces.json",
        "provider_profiles": runtime_dir / "provider_profiles.json",
        "tool_definitions": runtime_dir / "tool_definitions.json",
        "agent_definitions": runtime_dir / "agent_definitions.json",
        "workflow_templates": runtime_dir / "workflow_templates.json",
    }
    for path in paths.values():
        path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr("total_control.secrets_crypto.MASTER_KEY_PATH", runtime_dir / ".master_key")
    for module in ("total_control.state.base", "total_control.state.persistence"):
        monkeypatch.setattr(f"{module}.JOBS_PATH", paths["jobs"])
        monkeypatch.setattr(f"{module}.WORKSPACES_PATH", paths["workspaces"])
        monkeypatch.setattr(f"{module}.PROVIDER_PROFILES_PATH", paths["provider_profiles"])
        monkeypatch.setattr(f"{module}.TOOL_DEFINITIONS_PATH", paths["tool_definitions"])
        monkeypatch.setattr(f"{module}.AGENT_DEFINITIONS_PATH", paths["agent_definitions"])
        monkeypatch.setattr(f"{module}.WORKFLOW_TEMPLATES_PATH", paths["workflow_templates"])
    return paths


def _isolated_state(monkeypatch, tmp_path):
    _isolated_runtime_paths(monkeypatch, tmp_path)
    return TotalControlState(Path("config/servers.toml"))


def test_agent_definition_persistence_dedupes_duplicate_ids(monkeypatch, tmp_path):
    paths = _isolated_runtime_paths(monkeypatch, tmp_path)
    paths["agent_definitions"].write_text(
        json.dumps(
            [
                {
                    "id": "custom-agent",
                    "name": "Custom Agent",
                    "role": "custom_runner",
                    "tools": ["execution.package"],
                    "created_at": "2026-07-01T10:00:00",
                    "updated_at": "2026-07-01T10:00:01",
                },
                {
                    "id": "custom-agent",
                    "name": "Duplicate Agent",
                    "role": "custom_runner",
                    "tools": ["job.run"],
                    "created_at": "2026-07-01T11:00:00",
                    "updated_at": "2026-07-01T11:00:01",
                },
            ]
        ),
        encoding="utf-8",
    )
    state = TotalControlState(Path("config/servers.toml"))
    try:
        assert [agent["id"] for agent in state.agent_definitions].count("custom-agent") == 1
        persisted = json.loads(paths["agent_definitions"].read_text(encoding="utf-8"))
        assert [agent["id"] for agent in persisted].count("custom-agent") == 1
        assert next(agent for agent in persisted if agent["id"] == "custom-agent")["updated_at"] == "2026-07-01T10:00:01"

        state.create_agent_definition(
            {
                "id": "custom-agent",
                "name": "Custom Agent Updated",
                "role": "custom_runner",
                "tools": ["execution.package"],
            }
        )
        assert [agent["id"] for agent in state.agent_definitions].count("custom-agent") == 1
        persisted = json.loads(paths["agent_definitions"].read_text(encoding="utf-8"))
        assert [agent["id"] for agent in persisted].count("custom-agent") == 1
        assert next(agent for agent in persisted if agent["id"] == "custom-agent")["name"] == "Custom Agent Updated"

        state.create_agent_definition({"id": "other-agent", "name": "Other Agent", "role": "runner"})
        try:
            state.update_agent_definition("other-agent", {"id": "custom-agent", "name": "Merged Agent"})
        except ValueError as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("expected duplicate agent id update to fail")
        persisted = json.loads(paths["agent_definitions"].read_text(encoding="utf-8"))
        assert [agent["id"] for agent in persisted].count("custom-agent") == 1
        assert [agent["id"] for agent in persisted].count("other-agent") == 1

        state.workflow_templates = [
            {
                "id": "template-agent-rename",
                "name": "Template Agent Rename",
                "agent_ids": ["custom-agent"],
                "tool_ids": [],
                "nodes": [{"id": "node-agent", "handler": {"agent_id": "custom-agent", "name": "Custom Agent Updated"}}],
                "model": {"chat_agent_id": "custom-agent"},
            }
        ]
        state.update_agent_definition("custom-agent", {"id": "renamed-agent", "name": "Renamed Agent"})
        assert state.workflow_templates[0]["agent_ids"] == ["renamed-agent"]
        assert state.workflow_templates[0]["nodes"][0]["handler"]["agent_id"] == "renamed-agent"
        assert state.workflow_templates[0]["nodes"][0]["handler"]["name"] == "Renamed Agent"
        assert state.workflow_templates[0]["model"]["chat_agent_id"] == "renamed-agent"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def _runtime_workspace(tmp_path, *, name="Runtime Tool"):
    return normalize_workspace_payload(
        {
            "name": name,
            "brief": "Exercise a controlled runtime tool.",
            "workspace_dir": str(tmp_path),
            "nodes": [
                {
                    "id": "node-run",
                    "kind": "run.command",
                    "title": "Run",
                    "config": {
                        "server_id": "local",
                        "workspace_dir": str(tmp_path),
                        "run_command": "echo default",
                    },
                }
            ],
        }
    )


def test_agent_node_input_mapping_blocker_stops_before_llm(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    calls = {"chat": 0}

    def fake_chat_stream(self, messages, model=None, on_delta=None, **kwargs):
        calls["chat"] += 1
        return LLMResponse(content="should not run", model="fake-model", provider=self.provider)

    monkeypatch.setattr("total_control.llm_client.LLMClient.chat_stream", fake_chat_stream)
    monkeypatch.setattr("total_control.llm_client.LLMClient.chat", fake_chat_stream)

    workspace = normalize_workspace_payload(
        {
            "name": "Blocked Mapping",
            "brief": "Do not call the LLM when upstream output is missing.",
            "workspace_dir": str(tmp_path),
            "inputs": {"goal_text": "infer env"},
            "agents": [
                {
                    "id": "agent-env",
                    "name": "Env Agent",
                    "role": "engineer",
                    "prompt": "Infer environment.",
                    "tools": ["workflow.edit"],
                }
            ],
            "nodes": [
                {
                    "id": "env-agent",
                    "kind": "env.infer",
                    "title": "Infer Env",
                    "handler": {
                        "mode": "agent",
                        "agent_id": "agent-env",
                        "output_key": "env_requirements",
                        "output_format": "json",
                    },
                    "input_mapping": {
                        "repo_profile": "$context.outputs.repo_profile",
                        "path_map": "$context.outputs.path_map",
                    },
                }
            ],
        }
    )
    state.workspaces = [workspace]
    state.save_workspaces()
    try:
        node = state.workspace_by_id(workspace["id"])["nodes"][0]
        result = state.execute_workspace_agent_node(workspace["id"], node)

        assert result.status == "blocked"
        assert result.reason == "input_mapping_blocked"
        assert result.validation["code"] == "input_mapping_blocked"
        assert "repo_profile" in result.detail
        assert calls["chat"] == 0
        assert state.jobs == []
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_execute_workspace_agent_node_submits_controlled_runtime_job(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_chat_stream(self, messages, model=None, on_delta=None, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return LLMResponse(
                content='{"tool": "env.prepare", "arguments": {"setup_command": "echo integration-prepare", "wait_for_idle": true}}',
                model="fake-model",
                provider=self.provider,
                total_tokens=111,
            )
        content = "Environment queued via controlled runtime."
        if on_delta:
            accumulated = ""
            for piece in ("Environment ", "queued ", "via ", "controlled ", "runtime."):
                accumulated += piece
                on_delta(piece, accumulated, {"choices": [{"delta": {"content": piece}}]})
        return LLMResponse(
            content=content,
            model="fake-model",
            provider=self.provider,
            total_tokens=222,
        )

    def fake_chat(self, messages, model=None, **kwargs):
        return fake_chat_stream(self, messages, model=model, **kwargs)

    monkeypatch.setattr("total_control.llm_client.LLMClient.chat_stream", fake_chat_stream)
    monkeypatch.setattr("total_control.llm_client.LLMClient.chat", fake_chat)

    state = _isolated_state(monkeypatch, tmp_path)
    try:
        state.provider_profiles = [
            {
                "id": "p1",
                "name": "Test DeepSeek",
                "provider": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-test-1234567890",
                "models": ["deepseek-v4-pro"],
                "is_default": True,
            }
        ]
        state.save_provider_profiles()

        env_prepare_tool = next(item for item in state.tool_definitions if item.get("id") == "env.prepare")
        workspace = normalize_workspace_payload(
            {
                "name": "Phase 3 Integration",
                "brief": "Queue a controlled runtime job from an agent node.",
                "workspace_dir": str(tmp_path),
                "inputs": {"goal_text": "Use env.prepare once, then summarize the result."},
                "model": {"provider_profile_id": "p1", "routing_mode": "workspace_default"},
                "tools": [env_prepare_tool],
                "agents": [
                    {
                        "id": "agent-runtime",
                        "name": "Runtime Agent",
                        "role": "researcher",
                        "prompt": "Use env.prepare when setup is needed, then provide a short summary.",
                        "tools": ["env.prepare"],
                        "max_iterations": 3,
                    }
                ],
                "nodes": [
                    {
                        "id": "node-env",
                        "kind": "env.prepare",
                        "title": "Prepare Environment",
                        "config": {
                            "server_id": "local",
                            "workspace_dir": str(tmp_path),
                            "setup_command": "echo default-prepare",
                        },
                        "handler": {"mode": "system", "name": "Env Builder", "output_key": "env_setup"},
                    },
                    {
                        "id": "node-research",
                        "kind": "research.search",
                        "title": "Research Runtime Plan",
                        "config": {"workspace_dir": str(tmp_path)},
                        "handler": {
                            "mode": "agent",
                            "agent_id": "agent-runtime",
                            "name": "Runtime Agent",
                            "output_key": "research_brief",
                            "output_format": "text",
                        },
                    },
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        current = state.workspace_by_id(workspace["id"])
        assert current is not None
        node = next(item for item in current["nodes"] if item["id"] == "node-research")

        result = state.execute_workspace_agent_node(workspace["id"], node)

        assert result.status == "completed"
        assert result.executor == "agent"
        assert result.output_key == "research_brief"
        assert result.agent_meta["model"] == "fake-model"
        assert result.agent_meta["total_tokens"] == 333
        assert len(result.agent_steps) == 1
        assert result.agent_steps[0]["action"] == "env.prepare"
        assert result.agent_steps[0]["side_effect"] == "mutate_runtime"
        assert result.agent_steps[0]["controlled"] is True
        assert result.agent_steps[0]["runtime_control"] == "workspace_job_queue"
        assert result.agent_steps[0]["runtime_status"] == "submitted"

        assert len(state.jobs) == 1
        job = state.jobs[0]
        assert result.agent_steps[0]["job_id"] == job["id"]
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        assert metadata["tool_id"] == "env.prepare"
        assert metadata["runtime_control"] == "workspace_job_queue"
        assert metadata["submitted_by"] == "agent_tool"
        assert metadata["workspace_id"] == workspace["id"]
        assert job["status"] == "queued"
        assert job["command"] == "echo integration-prepare"

        persisted = state.workspace_by_id(workspace["id"])
        runs = persisted.get("runs") if isinstance(persisted, dict) and isinstance(persisted.get("runs"), list) else []
        assert runs
        assert result.agent_steps[0]["run_id"]
        assert any(run.get("id") == result.agent_steps[0]["run_id"] for run in runs)
        assert any(str(run.get("summary") or "").startswith("Agent 工具任务 · env.prepare") for run in runs)
        assert result.artifacts
        assert result.artifacts[-1]["path"].endswith("research_brief.txt")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_execute_workspace_agent_node_observes_runtime_tool_completion(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    calls = {"count": 0}

    def fake_chat_stream(self, messages, model=None, on_delta=None, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return LLMResponse(
                content=(
                    '{"tool": "env.prepare", "arguments": {'
                    '"setup_command": "echo observed-from-agent", '
                    '"wait_for_completion": true, '
                    '"wait_timeout_seconds": 1, '
                    '"poll_interval_seconds": 0.01'
                    "}}"
                ),
                model="fake-model",
                provider=self.provider,
                total_tokens=101,
            )
        content = "Runtime tool completed."
        if on_delta:
            on_delta(content, content, {"choices": [{"delta": {"content": content}}]})
        return LLMResponse(
            content=content,
            model="fake-model",
            provider=self.provider,
            total_tokens=202,
        )

    def fake_chat(self, messages, model=None, **kwargs):
        return fake_chat_stream(self, messages, model=model, **kwargs)

    monkeypatch.setattr("total_control.llm_client.LLMClient.chat_stream", fake_chat_stream)
    monkeypatch.setattr("total_control.llm_client.LLMClient.chat", fake_chat)
    monkeypatch.setattr(state, "refresh_status", lambda: None)

    def fake_monitor_jobs():
        with state.lock:
            if not state.jobs:
                return
            state.jobs[0]["status"] = "done"
            state.jobs[0]["finished_at"] = "2026-07-05T10:02:00"
            state.jobs[0]["error"] = ""

    monkeypatch.setattr(state, "monitor_jobs", fake_monitor_jobs)
    monkeypatch.setattr(
        state,
        "job_log_payload",
        lambda job, lines=120, offset=None, max_bytes=131072: {
            "job_id": job["id"],
            "mode": "tail",
            "log": "agent observed runtime completion\n[total-control] exit_code=0\n",
            "line_count": 2,
        },
    )

    try:
        state.provider_profiles = [
            {
                "id": "p1",
                "name": "Runtime Observer",
                "provider": "openai",
                "base_url": "https://example.invalid/v1",
                "api_key": "sk-test-1234567890",
                "models": ["fake-model"],
                "is_default": True,
            }
        ]
        state.save_provider_profiles()

        env_prepare_tool = next(item for item in state.tool_definitions if item.get("id") == "env.prepare")
        workspace = normalize_workspace_payload(
            {
                "name": "Agent Runtime Observe",
                "brief": "Observe a controlled runtime job through the Agent loop.",
                "workspace_dir": str(tmp_path),
                "inputs": {"goal_text": "Prepare env and wait for the short diagnostic command."},
                "model": {"provider_profile_id": "p1", "routing_mode": "workspace_default"},
                "tools": [env_prepare_tool],
                "agents": [
                    {
                        "id": "agent-runtime",
                        "name": "Runtime Agent",
                        "role": "runner",
                        "prompt": "Call env.prepare with wait_for_completion, then summarize.",
                        "tools": ["env.prepare"],
                        "max_iterations": 3,
                    }
                ],
                "nodes": [
                    {
                        "id": "node-env",
                        "kind": "env.prepare",
                        "title": "Prepare Environment",
                        "config": {
                            "server_id": "local",
                            "workspace_dir": str(tmp_path),
                            "setup_command": "echo default-prepare",
                        },
                        "handler": {"mode": "system", "name": "Env Builder", "output_key": "env_ready"},
                    },
                    {
                        "id": "node-research",
                        "kind": "research.search",
                        "title": "Observe Runtime Tool",
                        "config": {"workspace_dir": str(tmp_path)},
                        "handler": {
                            "mode": "agent",
                            "agent_id": "agent-runtime",
                            "name": "Runtime Agent",
                            "output_key": "research_brief",
                            "output_format": "text",
                        },
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        node = next(item for item in state.workspace_by_id(workspace["id"])["nodes"] if item["id"] == "node-research")
        result = state.execute_workspace_agent_node(workspace["id"], node)

        assert result.status == "completed"
        assert result.agent_steps
        step = result.agent_steps[0]
        assert step["action"] == "env.prepare"
        assert step["runtime_control"] == "workspace_job_queue"
        assert step["runtime_status"] == "done"
        assert step["job_id"]
        assert step["run_id"]
        assert '"observed": true' in step["observation"]
        assert '"status": "done"' in step["observation"]
        assert "agent observed runtime completion" in step["observation"]

        trace_events = result.trace_events
        assert any(
            event.get("type") == "agent.tool.result"
            and event.get("runtime_status") == "done"
            and event.get("job_id") == step["job_id"]
            for event in trace_events
        ), trace_events
        persisted = state.workspace_by_id(workspace["id"])
        child_run = next(run for run in persisted["runs"] if run["id"] == step["run_id"])
        assert child_run["status"] == "done"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_gpu_allocate_runtime_tool_returns_plan_without_mutating_workspace(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "GPU Plan Only",
                "brief": "Plan GPU binding without writing configuration.",
                "workspace_dir": str(tmp_path),
                "nodes": [
                    {
                        "id": "node-gpu",
                        "kind": "gpu.allocate",
                        "title": "GPU Plan",
                        "config": {"server_id": "", "gpu_policy": "", "gpu_index": ""},
                    },
                    {
                        "id": "node-run",
                        "kind": "run.command",
                        "title": "Run",
                        "config": {"server_id": "", "gpu_policy": "", "gpu_index": "", "run_command": "echo ok"},
                    },
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.bind_workspace_tool_gpu_allocation(
            workspace,
            {
                "selected": {
                    "server_id": "local",
                    "server_name": "Local",
                    "gpu_index": "0",
                    "eligible": True,
                },
                "min_free_mib": 2048,
            },
            None,
        )

        assert result["status"] == "planned"
        assert result["runtime_control"] == "scheduler_plan"
        assert result["runtime_side_effect"] == "none"
        assert result["plan_only"] is True
        assert result["persisted"] is False
        assert result["recommended_binding"]["server_id"] == "local"
        assert result["recommended_binding"]["gpu_index"] == "0"

        persisted = state.workspace_by_id(workspace["id"])
        configs = {
            node["kind"]: node.get("config", {})
            for node in persisted.get("nodes", [])
        }
        assert configs["gpu.allocate"]["server_id"] == ""
        assert configs["gpu.allocate"]["gpu_policy"] == ""
        assert configs["run.command"]["gpu_index"] == ""
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_host_exec_allows_diagnostic_command(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _runtime_workspace(tmp_path, name="Host Exec Diagnostic")
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.submit_workspace_tool_job(
            workspace,
            "host.exec",
            {
                "command": "uname -a",
                "server_id": "local",
            },
            None,
        )

        assert result["status"] == "submitted"
        assert result["runtime_control"] == "workspace_job_queue"
        assert result["runtime_side_effect"] == "workspace_job"
        assert result["job"]["command"] == "uname -a"
        assert result["job"]["gpu_index"] == "none"
        metadata = result["job"].get("metadata", {})
        assert metadata["tool_id"] == "host.exec"
        assert metadata["agent_runtime_tool"] is True
        assert metadata["runtime_binding"]["gpu_policy"] == "cpu"
        assert metadata["runtime_binding"]["gpu_index"] == "none"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_host_exec_blocks_non_diagnostic_command(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _runtime_workspace(tmp_path, name="Host Exec Blocked")
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.submit_workspace_tool_job(
            workspace,
            "host.exec",
            {
                "command": "python train.py",
                "server_id": "local",
            },
            None,
        )

        assert result["status"] == "blocked"
        assert result["controlled"] is True
        assert result["runtime_control"] == "workspace_job_queue"
        assert "job.run" in result["error"]
        assert state.jobs == []
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_host_exec_blocks_diagnostic_command_with_mutating_options(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _runtime_workspace(tmp_path, name="Host Exec Mutating Option")
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.submit_workspace_tool_job(
            workspace,
            "host.exec",
            {
                "command": "nvidia-smi -pm 1",
                "server_id": "local",
            },
            None,
        )

        assert result["status"] == "blocked"
        assert "只允许查询" in result["error"]
        assert state.jobs == []
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_host_exec_blocks_sensitive_path_diagnostics(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _runtime_workspace(tmp_path, name="Host Exec Sensitive Path")
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.submit_workspace_tool_job(
            workspace,
            "host.exec",
            {
                "command": "ls ~/.ssh",
                "server_id": "local",
            },
            None,
        )

        assert result["status"] == "blocked"
        assert "敏感路径" in result["error"]
        assert state.jobs == []
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_job_run_still_allows_configured_runtime_command(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _runtime_workspace(tmp_path, name="Job Run Runtime")
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.submit_workspace_tool_job(
            workspace,
            "job.run",
            {
                "command": "python train.py",
                "server_id": "local",
            },
            None,
        )

        assert result["status"] == "submitted"
        assert result["tool"] == "job.run"
        assert result["job"]["command"] == "python train.py"
        assert len(state.jobs) == 1
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_agent_runtime_tool_can_observe_job_completion(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Observe Runtime Job",
                "brief": "Agent tool should submit and observe a short job.",
                "workspace_dir": str(tmp_path),
                "nodes": [
                    {
                        "id": "node-run",
                        "kind": "run.command",
                        "title": "Run",
                        "config": {
                            "server_id": "local",
                            "workspace_dir": str(tmp_path),
                            "run_command": "echo default",
                        },
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        monkeypatch.setattr(state, "refresh_status", lambda: None)

        def fake_monitor_jobs():
            with state.lock:
                if not state.jobs:
                    return
                state.jobs[0]["status"] = "done"
                state.jobs[0]["finished_at"] = "2026-07-05T10:00:00"
                state.jobs[0]["error"] = ""

        monkeypatch.setattr(state, "monitor_jobs", fake_monitor_jobs)
        monkeypatch.setattr(
            state,
            "tail_log",
            lambda job, lines=200: "observed ok\n[total-control] exit_code=0\n",
        )

        result = state.submit_workspace_tool_job(
            workspace,
            "job.run",
            {
                "command": "echo observed",
                "server_id": "local",
                "wait_for_idle": True,
                "wait_for_completion": True,
                "wait_timeout_seconds": 1,
                "poll_interval_seconds": 0.01,
            },
            None,
        )

        assert result["status"] == "done"
        assert result["runtime_status"] == "done"
        assert result["observed"] is True
        assert result["timed_out"] is False
        assert result["job_status"] == "done"
        assert "observed ok" in result["log_tail"]
        assert result["job"]["status"] == "done"
        assert result["run"]["status"] == "done"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_agent_runtime_tool_observation_timeout_keeps_job_live(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Observe Runtime Timeout",
                "brief": "Agent tool should not block forever while observing.",
                "workspace_dir": str(tmp_path),
                "nodes": [
                    {
                        "id": "node-run",
                        "kind": "run.command",
                        "title": "Run",
                        "config": {
                            "server_id": "local",
                            "workspace_dir": str(tmp_path),
                            "run_command": "echo default",
                        },
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        monkeypatch.setattr(state, "refresh_status", lambda: None)

        def fake_monitor_jobs():
            with state.lock:
                if not state.jobs:
                    return
                state.jobs[0]["status"] = "running"
                state.jobs[0]["started_at"] = "2026-07-05T10:00:00"

        monkeypatch.setattr(state, "monitor_jobs", fake_monitor_jobs)
        monkeypatch.setattr(state, "tail_log", lambda job, lines=200: "still running\n")

        result = state.submit_workspace_tool_job(
            workspace,
            "job.run",
            {
                "command": "sleep 60",
                "server_id": "local",
                "wait_for_idle": True,
                "observe_seconds": 0.001,
                "poll_interval_seconds": 0.001,
            },
            None,
        )

        assert result["status"] == "timeout"
        assert result["runtime_status"] == "timeout"
        assert result["observed"] is True
        assert result["timed_out"] is True
        assert result["job_status"] == "running"
        assert state.jobs[0]["status"] == "running"
        assert "still running" in result["log_tail"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_agent_runtime_tool_observes_job_failure(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Observe Runtime Failure",
                "brief": "Agent tool should observe a failed job.",
                "workspace_dir": str(tmp_path),
                "nodes": [
                    {
                        "id": "node-run",
                        "kind": "run.command",
                        "title": "Run",
                        "config": {
                            "server_id": "local",
                            "workspace_dir": str(tmp_path),
                            "run_command": "false",
                        },
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()
        monkeypatch.setattr(state, "refresh_status", lambda: None)

        def fake_monitor_jobs():
            with state.lock:
                if not state.jobs:
                    return
                state.jobs[0]["status"] = "failed"
                state.jobs[0]["finished_at"] = "2026-07-05T10:01:00"
                state.jobs[0]["error"] = "process exited with code 2"

        monkeypatch.setattr(state, "monitor_jobs", fake_monitor_jobs)
        monkeypatch.setattr(
            state,
            "tail_log",
            lambda job, lines=200: "boom\n[total-control] exit_code=2\n",
        )

        result = state.submit_workspace_tool_job(
            workspace,
            "job.run",
            {
                "command": "false",
                "server_id": "local",
                "wait_for_idle": True,
                "wait_for_completion": True,
                "wait_timeout_seconds": 1,
                "poll_interval_seconds": 0.01,
            },
            None,
        )

        assert result["status"] == "failed"
        assert result["runtime_status"] == "failed"
        assert result["observed"] is True
        assert result["timed_out"] is False
        assert result["job_status"] == "failed"
        assert result["error"] == "process exited with code 2"
        assert "boom" in result["log_tail"]
        assert result["run"]["status"] == "failed"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_sync_refreshes_parent_agent_run_from_child_job(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Parent Agent Runtime Sync",
                "brief": "Parent Agent run should follow child runtime job.",
                "workspace_dir": str(tmp_path),
                "nodes": [
                    {
                        "id": "node-agent",
                        "kind": "research.search",
                        "title": "Agent Node",
                        "handler": {"mode": "agent", "agent_id": "agent-runtime"},
                    }
                ],
            }
        )
        parent_run = normalize_workspace_execution_run(
            {
                "id": "run-parent",
                "workspace_id": workspace["id"],
                "status": "done",
                "summary": "Parent Agent",
                "steps": [
                    {
                        "index": 0,
                        "node_id": "node-agent",
                        "node_kind": "research.search",
                        "node_title": "Agent Node",
                        "executor": "agent",
                        "status": "done",
                        "child_job_ids": ["job-child"],
                        "child_run_ids": ["run-child"],
                        "runtime_control": "workspace_job_queue",
                        "runtime_status": "submitted",
                    }
                ],
            }
        )
        child_run = normalize_workspace_execution_run(
            {
                "id": "run-child",
                "workspace_id": workspace["id"],
                "status": "queued",
                "summary": "Agent tool job",
                "steps": [
                    {
                        "index": 0,
                        "node_id": "node-agent",
                        "node_kind": "env.prepare",
                        "node_title": "Prepare",
                        "executor": "job",
                        "job_id": "job-child",
                        "status": "queued",
                    }
                ],
            }
        )
        workspace["runs"] = [parent_run, child_run]
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-child",
                "status": "queued",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "execution_run_id": "run-child",
                    "step_index": 0,
                    "tool_id": "env.prepare",
                    "agent_runtime_tool": True,
                },
            }
        ]
        state.save_workspaces()
        state.save_jobs()

        assert state.sync_workspace_execution_runs_from_jobs(workspace["id"]) is True
        synced = state.workspace_by_id(workspace["id"])
        parent = next(run for run in synced["runs"] if run["id"] == "run-parent")
        assert parent["status"] == "running"
        assert parent["steps"][0]["status"] == "running"
        assert parent["steps"][0]["runtime_status"] == "queued"

        state.jobs[0]["status"] = "failed"
        state.jobs[0]["error"] = "child runtime failed"
        assert state.sync_workspace_execution_runs_from_jobs(workspace["id"]) is True
        synced = state.workspace_by_id(workspace["id"])
        parent = next(run for run in synced["runs"] if run["id"] == "run-parent")
        assert parent["status"] == "failed"
        assert parent["steps"][0]["status"] == "failed"
        assert parent["steps"][0]["runtime_status"] == "failed"
        assert parent["steps"][0]["error"] == "child runtime failed"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_single_agent_node_run_exists_before_agent_events(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    events = []
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Single Agent Node",
                "brief": "Run a single agent node.",
                "workspace_dir": str(tmp_path),
                "agents": [{"id": "agent-one", "name": "Agent One", "role": "assistant"}],
                "nodes": [
                    {
                        "id": "node-agent",
                        "kind": "research.search",
                        "title": "Agent Node",
                        "handler": {"mode": "agent", "agent_id": "agent-one"},
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()
        original_publish = state.publish_event

        def capture_event(event_type, **kwargs):
            events.append((event_type, kwargs.get("run_id") or ""))
            return original_publish(event_type, **kwargs)

        def fake_execute(workspace_id, node, *, run_context=None, input_text=""):
            assert run_context is not None
            assert run_context.run_id
            assert any(run.get("id") == run_context.run_id for run in state.workspace_by_id(workspace_id).get("runs", []))
            state.publish_event(
                "agent.step.created",
                workspace_id=workspace_id,
                run_id=run_context.run_id,
                agent_execution_id="aex-single",
                payload={"step": {"step_number": 1, "action": "answer"}, "agent_id": "agent-one"},
            )
            return StepResult(
                status="completed",
                executor="agent",
                detail="done",
                agent_execution_id="aex-single",
                agent_steps=[{"step_number": 1, "action": "answer", "observation": "done"}],
            )

        monkeypatch.setattr(state, "publish_event", capture_event)
        monkeypatch.setattr(state, "execute_workspace_agent_node", fake_execute)

        result = state.run_workspace_node(workspace["id"], "node-agent", {"prefer": "agent"})

        assert result["executor"] == "agent"
        assert result["run_id"]
        assert ("run.created", result["run_id"]) in events
        assert ("agent.step.created", result["run_id"]) in events
        assert ("run.updated", result["run_id"]) in events
        persisted = state.workspace_by_id(workspace["id"])
        run = next(item for item in persisted["runs"] if item["id"] == result["run_id"])
        assert run["status"] == "done"
        assert run["steps"][0]["agent_execution_id"] == "aex-single"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)
