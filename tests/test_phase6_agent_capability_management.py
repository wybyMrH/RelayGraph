from __future__ import annotations

from pathlib import Path

from total_control.state import TotalControlState


def test_global_agent_runtime_boundaries_round_trip_and_debug(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    jobs_path = runtime_dir / "jobs.json"
    workspaces_path = runtime_dir / "workspaces.json"
    profiles_path = runtime_dir / "provider_profiles.json"
    tool_definitions_path = runtime_dir / "tool_definitions.json"
    agent_definitions_path = runtime_dir / "agent_definitions.json"
    workflow_templates_path = runtime_dir / "workflow_templates.json"
    for path in (
        jobs_path,
        workspaces_path,
        profiles_path,
        tool_definitions_path,
        agent_definitions_path,
        workflow_templates_path,
    ):
        path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr("total_control.secrets_crypto.MASTER_KEY_PATH", runtime_dir / ".master_key")
    for module in ("total_control.state.base", "total_control.state.persistence"):
        monkeypatch.setattr(f"{module}.JOBS_PATH", jobs_path)
        monkeypatch.setattr(f"{module}.WORKSPACES_PATH", workspaces_path)
        monkeypatch.setattr(f"{module}.PROVIDER_PROFILES_PATH", profiles_path)
        monkeypatch.setattr(f"{module}.TOOL_DEFINITIONS_PATH", tool_definitions_path)
        monkeypatch.setattr(f"{module}.AGENT_DEFINITIONS_PATH", agent_definitions_path)
        monkeypatch.setattr(f"{module}.WORKFLOW_TEMPLATES_PATH", workflow_templates_path)

    state = TotalControlState(Path("config/servers.toml"))
    try:
        saved = state.create_agent_definition(
            {
                "id": "phase6-agent",
                "name": "Phase 6 Agent",
                "role": "runner",
                "prompt": "Return structured plans.",
                "tools": ["execution.package"],
                "max_iterations": 6,
                "timeout_seconds": 45,
                "output_format": "json",
            }
        )

        assert saved["max_iterations"] == 6
        assert saved["timeout_seconds"] == 45
        assert saved["output_format"] == "json"

        result = state.debug_agent_definition(
            "phase6-agent",
            {
                "input": "Debug without LLM call.",
                "execute_llm": False,
            },
        )

        assert result["effective_config"] == {
            "max_iterations": 6,
            "timeout_seconds": 45.0,
            "output_format": "json",
        }
        assert result["agent_definition"]["max_iterations"] == 6
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)
