"""Phase 3 integration — real workspace agent path + controlled runtime tool."""

from __future__ import annotations

from pathlib import Path

from total_control.llm_client import LLMResponse
from total_control.state import TotalControlState
from total_control.workspace.cockpit.payload import normalize_workspace_payload


def test_execute_workspace_agent_node_submits_controlled_runtime_job(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    jobs_path = runtime_dir / "jobs.json"
    workspaces_path = runtime_dir / "workspaces.json"
    profiles_path = runtime_dir / "provider_profiles.json"
    jobs_path.write_text("[]", encoding="utf-8")
    workspaces_path.write_text("[]", encoding="utf-8")
    profiles_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr("total_control.secrets_crypto.MASTER_KEY_PATH", runtime_dir / ".master_key")
    monkeypatch.setattr("total_control.state.base.JOBS_PATH", jobs_path)
    monkeypatch.setattr("total_control.state.base.WORKSPACES_PATH", workspaces_path)
    monkeypatch.setattr("total_control.state.base.PROVIDER_PROFILES_PATH", profiles_path)
    monkeypatch.setattr("total_control.state.persistence.JOBS_PATH", jobs_path)
    monkeypatch.setattr("total_control.state.persistence.WORKSPACES_PATH", workspaces_path)
    monkeypatch.setattr("total_control.state.persistence.PROVIDER_PROFILES_PATH", profiles_path)

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

    state = TotalControlState(Path("config/servers.toml"))
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

        assert len(state.jobs) == 1
        job = state.jobs[0]
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
        assert any(str(run.get("summary") or "").startswith("Agent 工具任务 · env.prepare") for run in runs)
        assert result.artifacts
        assert result.artifacts[-1]["path"].endswith("research_brief.txt")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)
