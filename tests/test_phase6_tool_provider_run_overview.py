from __future__ import annotations

import json
from pathlib import Path

from total_control import utils
from total_control.state import TotalControlState
from total_control.tools.registry import create_workspace_tool_executor
from total_control.tools.workspace_executor_pkg import web_search
from total_control.workspace.schema.agents_tools import normalize_workspace_tool
from total_control.workspace.execution import compact_tool_arguments, normalize_workspace_execution_run


def _state(monkeypatch, tmp_path) -> TotalControlState:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    jobs_path = runtime_dir / "jobs.json"
    workspaces_path = runtime_dir / "workspaces.json"
    profiles_path = runtime_dir / "provider_profiles.json"
    tool_definitions_path = runtime_dir / "tool_definitions.json"
    agent_definitions_path = runtime_dir / "agent_definitions.json"
    workflow_templates_path = runtime_dir / "workflow_templates.json"
    log_root = runtime_dir / "logs"
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
    monkeypatch.setattr(utils, "LOG_DIR", log_root)
    for module in ("total_control.state.base", "total_control.state.persistence"):
        monkeypatch.setattr(f"{module}.JOBS_PATH", jobs_path)
        monkeypatch.setattr(f"{module}.WORKSPACES_PATH", workspaces_path)
        monkeypatch.setattr(f"{module}.PROVIDER_PROFILES_PATH", profiles_path)
        monkeypatch.setattr(f"{module}.TOOL_DEFINITIONS_PATH", tool_definitions_path)
        monkeypatch.setattr(f"{module}.AGENT_DEFINITIONS_PATH", agent_definitions_path)
        monkeypatch.setattr(f"{module}.WORKFLOW_TEMPLATES_PATH", workflow_templates_path)
    return TotalControlState(Path("config/servers.toml"))


def test_tool_safe_payload_blocks_runtime_tools(monkeypatch, tmp_path):
    monkeypatch.delenv("TOTAL_CONTROL_FIRECRAWL_API_KEY", raising=False)
    monkeypatch.delenv("TOTAL_CONTROL_SERPER_API_KEY", raising=False)
    monkeypatch.delenv("TOTAL_CONTROL_WEB_SEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("TOTAL_CONTROL_WEB_SEARCH_ENDPOINT", raising=False)
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Tool Test", "brief": "Inspect package", "source_type": "idea"})

        read_result = state.test_tool_definition(
            "workflow.plan",
            {"workspace_id": workspace["id"], "arguments": {}},
        )
        assert read_result["safe"] is True
        assert read_result["status"] == "ok"
        assert read_result["result"]["workspace_id"] == workspace["id"]

        search_result = state.test_tool_definition(
            "web.search",
            {"workspace_id": workspace["id"], "arguments": {"query": "RelayGraph smoke", "limit": 1}},
        )
        assert search_result["safe"] is True
        assert search_result["status"] == "ok"
        assert search_result["result"]["provider_status"] in {"unconfigured", "blocked", "seeded"}
        assert search_result["result"]["provider_configured"] is False
        assert "result_count" in search_result["result"]

        runtime_result = state.test_tool_definition(
            "job.run",
            {"workspace_id": workspace["id"], "arguments": {"command": "echo should-not-run"}},
        )
        assert runtime_result["safe"] is False
        assert runtime_result["status"] == "blocked"
        assert runtime_result["result"]["plan_only"] is True
        assert state.jobs == []
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_web_search_safe_test_uses_search_provider_profile_and_redacts_arguments(monkeypatch, tmp_path):
    monkeypatch.delenv("TOTAL_CONTROL_FIRECRAWL_API_KEY", raising=False)
    monkeypatch.delenv("TOTAL_CONTROL_WEB_SEARCH_PROVIDER", raising=False)
    captured: dict[str, object] = {}

    def fake_json_request(url, *, payload, headers, timeout=15):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {
            "data": {
                "web": [
                    {
                        "url": "https://example.com/relaygraph",
                        "title": "RelayGraph",
                        "description": "Smoke result",
                    }
                ]
            }
        }

    monkeypatch.setattr(web_search, "_json_request", fake_json_request)
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Search Test", "brief": "search relaygraph", "source_type": "idea"})
        profile = state.create_provider_profile(
            {
                "id": "search-firecrawl",
                "kind": "search",
                "name": "Firecrawl Search",
                "provider": "firecrawl",
                "base_url": "https://firecrawl.local",
                "api_key": "fc-secret-1234567890",
                "is_default": True,
            }
        )
        assert profile["api_key_masked"]
        state.update_tool_definition("web.search", {"provider_profile_id": "search-firecrawl"})

        result = state.test_tool_definition(
            "web.search",
            {
                "workspace_id": workspace["id"],
                "arguments": {"query": "RelayGraph", "limit": 1, "api_key": "accidental-secret"},
            },
        )

        assert captured["url"] == "https://firecrawl.local/v2/search"
        assert captured["headers"]["Authorization"] == "Bearer fc-secret-1234567890"
        assert captured["payload"] == {"query": "RelayGraph", "limit": 1}
        assert result["safe"] is True
        assert result["arguments"]["api_key"] == "***"
        assert result["result"]["provider"] == "firecrawl"
        assert result["result"]["provider_profile_id"] == "search-firecrawl"
        assert result["result"]["result_count"] == 1
        assert "fc-secret-1234567890" not in json.dumps(result, ensure_ascii=False)
        assert "accidental-secret" not in compact_tool_arguments({"api_key": "accidental-secret", "query": "RelayGraph"})
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_unknown_workspace_tool_is_not_marked_implemented_by_default():
    tool = normalize_workspace_tool(
        {
            "id": "custom.future_tool",
            "label": "Future Tool",
            "side_effect": "mutate_runtime",
            "implemented": True,
        }
    )

    assert tool["implemented"] is False
    assert tool["side_effect"] == "mutate_runtime"


def test_repo_search_registry_matches_dispatcher_implementation():
    tool = normalize_workspace_tool({"id": "repo.search", "label": "Repo Search"})
    assert tool["implemented"] is True
    assert tool["side_effect"] == "read"


def test_runtime_tool_without_runtime_callback_blocks_instead_of_plan_only():
    executor = create_workspace_tool_executor(
        {
            "id": "workspace-runtime-block",
            "name": "Runtime Block",
            "workspace_dir": "/tmp",
            "nodes": [
                {
                    "id": "run-1",
                    "kind": "run.command",
                    "config": {"run_command": "echo should-not-run"},
                }
            ],
        },
        runtime=None,
    )

    payload = json.loads(executor("job.run", {"command": "echo should-not-run"}))

    assert payload["status"] == "blocked"
    assert payload["runtime_control"] == "workspace_job_queue"
    assert "plan_only" not in payload
    assert "dry_run" not in payload


def test_provider_route_health_and_execution_overview(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        blocked_health = state.provider_route_health()
        assert blocked_health["status"] == "blocked"
        assert any(issue["code"] == "no_provider_profiles" for issue in blocked_health["issues"])

        search_profile = state.create_provider_profile(
            {
                "id": "search-duckduckgo",
                "kind": "search",
                "name": "Duck Search",
                "provider": "duckduckgo",
                "api_key": "",
                "models": [],
                "is_default": True,
                "key_required": False,
            }
        )
        assert search_profile["status"] == "ready"
        search_only_health = state.provider_route_health()
        assert search_only_health["configured_search_profile_count"] == 1
        assert search_only_health["configured_profile_count"] == 0
        assert any(issue["code"] == "no_provider_profiles" for issue in search_only_health["issues"])

        profile = state.create_provider_profile(
            {
                "id": "phase6-provider",
                "name": "Phase6 Provider",
                "provider": "openai",
                "base_url": "https://example.invalid/v1",
                "api_key": "sk-test-phase6",
                "models": ["test-model"],
                "is_default": True,
            }
        )
        assert profile["api_key_masked"]
        ready_health = state.provider_route_health()
        assert ready_health["configured_profile_count"] == 1
        assert not any(issue["code"] == "no_provider_profiles" for issue in ready_health["issues"])

        state.provider_profiles.append(
            {
                "id": "phase6-draft-provider",
                "name": "Draft Provider",
                "provider": "openai",
                "base_url": "https://example.invalid/v1",
                "api_key": "",
                "models": ["draft-model"],
            }
        )
        mixed_health = state.provider_route_health()
        assert mixed_health["status"] in {"warning", "ready"}
        assert mixed_health["blocking_count"] == 0
        assert any(
            issue["code"] == "provider_missing_api_key" and issue["severity"] == "warning"
            for issue in mixed_health["issues"]
        )

        local_profile = state.create_provider_profile(
            {
                "id": "phase6-ollama",
                "name": "Local Ollama",
                "provider": "ollama",
                "base_url": "http://localhost:11434/v1",
                "api_key": "",
                "models": ["llama3.1"],
                "key_required": False,
            }
        )
        assert local_profile["key_required"] is False
        assert local_profile["status"] == "ready"
        local_health = state.provider_route_health()
        local_summary = next(item for item in local_health["profiles"] if item["id"] == "phase6-ollama")
        assert local_summary["ready"] is True
        assert local_summary["key_required"] is False

        workspace_with_draft_route = state.create_workspace(
            {
                "name": "Draft Route",
                "brief": "Route warning",
                "source_type": "idea",
                "model": {"provider_profile_id": "phase6-draft-provider"},
            }
        )
        route_health = state.provider_route_health()
        assert route_health["blocking_count"] == 0
        assert any(
            issue["code"] == "workspace_provider_profile_not_ready"
            and issue["workspace_id"] == workspace_with_draft_route["id"]
            for issue in route_health["issues"]
        )

        workspace = state.create_workspace({"name": "Overview Test", "brief": "Run overview", "source_type": "idea"})
        run = normalize_workspace_execution_run(
            {
                "workspace_id": workspace["id"],
                "kind": "advance",
                "status": "done",
                "summary": "overview smoke",
                "steps": [],
            }
        )
        state.workspaces[0]["runs"] = [run]
        job = {
            "id": "job-phase6",
            "status": "done",
            "created_at": "2026-06-24T10:00:00",
            "updated_at": "2026-06-24T10:00:01",
            "metadata": {
                "workspace_id": workspace["id"],
                "execution_run_id": run["id"],
                "node_kind": "run.command",
            },
        }
        state.jobs = [job]

        overview = state.execution_overview({"limit": 10})
        assert overview["summary"]["run_count"] == 1
        assert overview["summary"]["job_count"] == 1
        assert overview["runs"][0]["workspace_id"] == workspace["id"]
        assert overview["jobs"][0]["execution_run_id"] == run["id"]

        target_workspace = state.create_workspace(
            {"name": "Needle Workspace", "brief": "Find old failed run", "source_type": "idea"}
        )
        target = next(item for item in state.workspaces if item["id"] == target_workspace["id"])
        target_run = normalize_workspace_execution_run(
            {
                "id": "run-needle",
                "workspace_id": target_workspace["id"],
                "kind": "reproduction",
                "status": "failed",
                "summary": "rare needle failure",
                "created_at": "2026-06-20T10:00:00",
                "updated_at": "2026-06-20T10:00:00",
                "steps": [
                    {
                        "index": 0,
                        "node_id": "run-command",
                        "node_kind": "run.command",
                        "status": "failed",
                        "job_id": "job-needle",
                    }
                ],
            }
        )
        recent_runs = [
            normalize_workspace_execution_run(
                {
                    "id": f"run-recent-{index}",
                    "workspace_id": target_workspace["id"],
                    "kind": "advance",
                    "status": "done",
                    "summary": f"recent run {index}",
                    "created_at": f"2026-06-24T10:{index:02d}:00",
                    "updated_at": f"2026-06-24T10:{index:02d}:00",
                    "steps": [],
                }
            )
            for index in range(12)
        ]
        target["runs"] = [*recent_runs, target_run]
        state.jobs = [
            *state.jobs,
            *[
                {
                    "id": f"job-recent-{index}",
                    "status": "done",
                    "created_at": f"2026-06-24T10:{index:02d}:00",
                    "updated_at": f"2026-06-24T10:{index:02d}:01",
                    "metadata": {"workspace_id": target_workspace["id"], "node_kind": "run.command"},
                }
                for index in range(12)
            ],
            {
                "id": "job-needle",
                "status": "failed",
                "server_id": "remote-a",
                "created_at": "2026-06-20T10:00:00",
                "updated_at": "2026-06-20T10:00:01",
                "metadata": {
                    "workspace_id": target_workspace["id"],
                    "execution_run_id": "run-needle",
                    "node_kind": "run.command",
                    "node_title": "needle runtime job",
                },
            },
        ]

        filtered = state.execution_overview({"limit": 5, "query": "needle", "status": "failed"})
        assert filtered["summary"]["run_count"] > 5
        assert filtered["filters"] == {"query": "needle", "status": "failed", "kind": "all", "limit": 5}
        assert filtered["result"]["run_count"] == 1
        assert filtered["result"]["job_count"] == 1
        assert filtered["runs"][0]["id"] == "run-needle"
        assert filtered["runs"][0]["node_kinds"] == ["run.command"]
        assert filtered["runs"][0]["server_ids"] == ["remote-a"]
        assert filtered["jobs"][0]["id"] == "job-needle"

        jobs_only = state.execution_overview({"limit": 5, "query": "needle", "status": "failed", "kind": "jobs"})
        assert jobs_only["runs"] == []
        assert jobs_only["result"]["run_count"] == 0
        assert jobs_only["result"]["job_count"] == 1
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_workspace_run_replay_payload_links_jobs_and_package(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Replay Test", "brief": "Export run replay", "source_type": "idea"})
        run = normalize_workspace_execution_run(
            {
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "done",
                "summary": "replay smoke",
                "package_snapshot": {
                    "package_id": "pkg-replay-test",
                    "package_manifest": {"commands": {"report_command": "python report.py"}},
                },
                "steps": [
                    {
                        "index": 0,
                        "node_id": "run-1",
                        "node_kind": "run.command",
                        "node_title": "Run",
                        "executor": "job",
                        "status": "done",
                        "job_id": "job-replay",
                    },
                    {
                        "index": 1,
                        "node_id": "report-1",
                        "node_kind": "eval.report",
                        "node_title": "Report",
                        "executor": "agent",
                        "status": "done",
                        "child_job_ids": ["job-agent-child"],
                        "child_run_ids": ["run-agent-child"],
                        "runtime_control": "workspace_job_queue",
                        "runtime_status": "done",
                        "artifacts": [
                            {
                                "label": "report",
                                "type": "report",
                                "path": "reports/final.md",
                                "status": "done",
                                "summary": "Replay report.",
                            }
                        ],
                    }
                ],
            }
        )
        state.workspaces[0]["runs"] = [run]
        state.jobs = [
            {
                "id": "job-replay",
                "status": "done",
                "server_id": "local",
                "command": "echo replay",
                "created_at": "2026-06-24T10:00:00",
                "finished_at": "2026-06-24T10:00:01",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "execution_run_id": run["id"],
                    "node_kind": "run.command",
                },
            },
            {
                "id": "job-agent-child",
                "status": "done",
                "server_id": "local",
                "command": "echo child",
                "created_at": "2026-06-24T10:00:02",
                "finished_at": "2026-06-24T10:00:03",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "execution_run_id": "run-agent-child",
                    "node_kind": "env.prepare",
                    "agent_runtime_tool": True,
                },
            },
        ]

        payload = state.get_workspace_execution_run_replay(workspace["id"], run["id"])

        replay = payload["replay"]
        assert replay["schema"] == "relaygraph.run.replay.v1"
        assert replay["workspace"]["id"] == workspace["id"]
        assert replay["run"]["id"] == run["id"]
        assert replay["run"]["package_id"] == "pkg-replay-test"
        assert replay["timeline"][0]["job_id"] == "job-replay"
        assert replay["timeline"][1]["child_job_ids"] == ["job-agent-child"]
        assert replay["timeline"][1]["child_run_ids"] == ["run-agent-child"]
        assert [item["command"] for item in replay["linked_jobs"]] == ["echo replay", "echo child"]
        assert replay["delivery_closure"]["status"] == "ready"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_workspace_run_replay_and_export_follow_child_run_closure(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Closure Test", "brief": "Child run closure", "source_type": "idea"})
        foreign = state.create_workspace({"name": "Foreign Closure", "brief": "Should not leak", "source_type": "idea"})
        log_root = utils.runtime_log_root()
        parent_log = log_root / "local" / "parent-closure.log"
        child_log = log_root / "local" / "child-closure.log"
        grandchild_log = log_root / "local" / "grandchild-closure.log"
        foreign_log = log_root / "local" / "foreign-closure.log"
        for path, text in (
            (parent_log, "parent closure evidence\n"),
            (child_log, "child closure evidence\n"),
            (grandchild_log, "grandchild closure evidence\n"),
            (foreign_log, "foreign workspace sentinel\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        parent_run = normalize_workspace_execution_run(
            {
                "id": "run-parent",
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "done",
                "summary": "parent",
                "package_snapshot": {"package_id": "pkg-parent"},
                "steps": [
                    {
                        "index": 0,
                        "node_id": "parent-node",
                        "node_kind": "agent.plan",
                        "executor": "agent",
                        "status": "done",
                        "job_id": "job-parent",
                        "child_run_ids": ["run-child"],
                    }
                ],
            }
        )
        child_run = normalize_workspace_execution_run(
            {
                "id": "run-child",
                "workspace_id": workspace["id"],
                "kind": "node",
                "status": "done",
                "summary": "child",
                "package_snapshot": {"package_id": "pkg-child"},
                "events": [
                    {
                        "type": "step.trace",
                        "workspace_id": workspace["id"],
                        "run_id": "run-child",
                        "payload": {"run_id": "run-child", "delta": "child event sentinel"},
                    }
                ],
                "steps": [
                    {
                        "index": 0,
                        "node_id": "child-node",
                        "node_kind": "run.command",
                        "executor": "job",
                        "status": "done",
                        "job_id": "job-child",
                        "child_run_ids": ["run-grandchild"],
                        "artifacts": [
                            {
                                "label": "report",
                                "type": "report",
                                "path": "reports/child.md",
                                "status": "done",
                            }
                        ],
                    }
                ],
            }
        )
        grandchild_run = normalize_workspace_execution_run(
            {
                "id": "run-grandchild",
                "workspace_id": workspace["id"],
                "kind": "node",
                "status": "done",
                "summary": "grandchild",
                "package_snapshot": {"package_id": "pkg-grandchild"},
                "steps": [
                    {
                        "index": 0,
                        "node_id": "grandchild-node",
                        "node_kind": "eval.report",
                        "executor": "job",
                        "status": "done",
                        "job_id": "job-grandchild",
                    }
                ],
            }
        )
        foreign_run = normalize_workspace_execution_run(
            {
                "id": "run-child",
                "workspace_id": foreign["id"],
                "status": "done",
                "summary": "foreign workspace sentinel",
                "steps": [{"index": 0, "node_id": "foreign", "job_id": "job-foreign-child"}],
            }
        )
        current_workspace = next(item for item in state.workspaces if item["id"] == workspace["id"])
        foreign_workspace = next(item for item in state.workspaces if item["id"] == foreign["id"])
        current_workspace["runs"] = [parent_run, child_run, grandchild_run]
        foreign_workspace["runs"] = [foreign_run]
        state.jobs = [
            {
                "id": "job-parent",
                "status": "done",
                "server_id": "local",
                "command": "echo parent",
                "log_path": str(parent_log),
                "metadata": {"workspace_id": workspace["id"], "execution_run_id": "run-parent"},
            },
            {
                "id": "job-child",
                "status": "done",
                "server_id": "local",
                "command": "echo child",
                "log_path": str(child_log),
                "metadata": {"workspace_id": workspace["id"], "execution_run_id": "run-child"},
            },
            {
                "id": "job-grandchild",
                "status": "done",
                "server_id": "local",
                "command": "echo grandchild",
                "log_path": str(grandchild_log),
                "metadata": {"workspace_id": workspace["id"], "execution_run_id": "run-grandchild"},
            },
            {
                "id": "job-foreign-child",
                "status": "done",
                "server_id": "local",
                "command": "echo foreign",
                "log_path": str(foreign_log),
                "metadata": {"workspace_id": foreign["id"], "execution_run_id": "run-child"},
            },
        ]

        replay = state.get_workspace_execution_run_replay(workspace["id"], "run-parent")["replay"]
        exported = state.get_workspace_execution_run_export(workspace["id"], "run-parent")["export"]
        replay_text = json.dumps(replay, ensure_ascii=False)
        export_text = json.dumps(exported, ensure_ascii=False)

        assert [item["run"]["id"] for item in replay["linked_runs"]] == ["run-child", "run-grandchild"]
        assert {item["id"] for item in replay["linked_jobs"]} == {"job-parent", "job-child", "job-grandchild"}
        assert "pkg-child" in replay_text
        assert "child event sentinel" in replay_text
        assert "foreign workspace sentinel" not in replay_text
        assert exported["summary"]["linked_run_count"] == 2
        assert exported["summary"]["linked_job_count"] == 3
        assert exported["summary"]["log_count"] == 3
        assert exported["manifest"]["included"]["linked_runs"] == 2
        assert any(item["run_id"] == "run-child" and item["path"] == "reports/child.md" for item in exported["reports"])
        assert any(item["job_id"] == "job-grandchild" and "grandchild closure evidence" in item["tail"] for item in exported["logs"])
        assert "foreign workspace sentinel" not in export_text
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_workspace_run_replay_marks_child_ref_truncation(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Child Ref Limit", "brief": "Many child refs", "source_type": "idea"})
        child_ids = [f"run-child-{index:02d}" for index in range(70)]
        parent_run = normalize_workspace_execution_run(
            {
                "id": "run-parent-many",
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "done",
                "summary": "parent with many child runs",
                "steps": [
                    {
                        "index": 0,
                        "node_id": "agent-many",
                        "node_kind": "agent.plan",
                        "executor": "agent",
                        "status": "done",
                        "child_run_ids": child_ids,
                    }
                ],
            }
        )
        child_runs = [
            normalize_workspace_execution_run(
                {
                    "id": child_id,
                    "workspace_id": workspace["id"],
                    "kind": "node",
                    "status": "done",
                    "summary": child_id,
                    "steps": [
                        {
                            "index": 0,
                            "node_id": f"node-{index:02d}",
                            "node_kind": "run.command",
                            "executor": "job",
                            "status": "done",
                        }
                    ],
                }
            )
            for index, child_id in enumerate(child_ids)
        ]
        state.workspaces[0]["runs"] = [parent_run, *child_runs]

        replay = state.get_workspace_execution_run_replay(workspace["id"], "run-parent-many")["replay"]
        exported = state.get_workspace_execution_run_export(workspace["id"], "run-parent-many")["export"]

        root_step = replay["timeline"][0]
        assert len(root_step["child_run_ids"]) == 64
        assert root_step["child_run_ref_count"] == 70
        assert root_step["child_run_ids_truncated"] is True
        assert len(replay["linked_runs"]) == 64
        assert replay["linked_run_closure"]["limit"] == 64
        assert exported["manifest"]["limits"]["child_refs_per_step"] == 64
        assert exported["manifest"]["truncation"]["child_ref_steps"] == 1
        assert "Steps with truncated child refs: 1" in exported["readme_markdown"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_workspace_run_compare_payload_reports_deltas(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Compare Test", "brief": "Compare runs", "source_type": "idea"})
        base_run = normalize_workspace_execution_run(
            {
                "id": "run-base",
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "failed",
                "summary": "base run",
                "package_snapshot": {"package_id": "pkg-base"},
                "steps": [
                    {
                        "index": 0,
                        "node_id": "run-1",
                        "node_kind": "run.command",
                        "node_title": "Run",
                        "executor": "job",
                        "status": "failed",
                        "job_id": "job-base",
                    }
                ],
            }
        )
        target_run = normalize_workspace_execution_run(
            {
                "id": "run-target",
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "done",
                "summary": "target run",
                "package_snapshot": {"package_id": "pkg-target"},
                "steps": [
                    {
                        "index": 0,
                        "node_id": "run-1",
                        "node_kind": "run.command",
                        "node_title": "Run",
                        "executor": "job",
                        "status": "done",
                        "job_id": "job-target",
                    },
                    {
                        "index": 1,
                        "node_id": "report-1",
                        "node_kind": "eval.report",
                        "node_title": "Report",
                        "executor": "agent",
                        "status": "done",
                        "agent_execution_id": "aex-target",
                        "artifacts": [{"label": "report", "type": "report", "path": "reports/final.md", "status": "done"}],
                    },
                ],
            }
        )
        state.workspaces[0]["runs"] = [base_run, target_run]
        state.jobs = [
            {"id": "job-base", "status": "failed", "command": "echo base", "metadata": {"workspace_id": workspace["id"], "execution_run_id": base_run["id"]}},
            {"id": "job-target", "status": "done", "command": "echo target", "metadata": {"workspace_id": workspace["id"], "execution_run_id": target_run["id"]}},
        ]

        payload = state.compare_workspace_execution_runs(workspace["id"], base_run["id"], target_run["id"])

        compare = payload["compare"]
        assert compare["schema"] == "relaygraph.run.compare.v1"
        assert compare["base"]["run"]["id"] == "run-base"
        assert compare["target"]["run"]["id"] == "run-target"
        assert compare["diff"]["metric_delta"]["step_count"] == 1
        assert compare["diff"]["metric_delta"]["failed_step_count"] == -1
        assert "run-target:eval.report:report-1" in compare["diff"]["added_nodes"]
        assert any(change["field"] == "status" for change in compare["diff"]["changes"])
        assert any(change["field"] == "package_id" for change in compare["diff"]["changes"])
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_workspace_run_export_payload_includes_replay_logs_and_reports(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Export Test", "brief": "Export run", "source_type": "idea"})
        log_root = utils.runtime_log_root()
        log_path = log_root / "local" / "run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("line one\nmetric acc=0.91\nfinal report ready\n", encoding="utf-8")
        child_log_path = log_root / "local" / "child.log"
        child_log_path.write_text("child runtime queued\nchild runtime done\n", encoding="utf-8")
        foreign_log_path = log_root / "local" / "foreign.log"
        foreign_log_path.write_text("foreign workspace leak\n", encoding="utf-8")
        run = normalize_workspace_execution_run(
            {
                "id": "run-export",
                "workspace_id": workspace["id"],
                "kind": "reproduction",
                "status": "done",
                "summary": "export run",
                "package_snapshot": {
                    "package_id": "pkg-export",
                    "delivery_closure": {
                        "status": "ready",
                        "report": {
                            "status": "ready",
                            "artifacts": [
                                {
                                    "label": "report",
                                    "type": "report",
                                    "path": "reports/final.md",
                                    "summary": "final report",
                                }
                            ],
                        },
                    },
                    "package_manifest": {
                        "commands": {
                            "run_command": "python train.py",
                            "report_command": "python report.py",
                        }
                    },
                },
                "steps": [
                    {
                        "index": 0,
                        "node_id": "run-1",
                        "node_kind": "run.command",
                        "node_title": "Run",
                        "executor": "job",
                        "status": "done",
                        "job_id": "job-export",
                    },
                    {
                        "index": 1,
                        "node_id": "report-1",
                        "node_kind": "eval.report",
                        "node_title": "Report",
                        "executor": "agent",
                        "status": "done",
                        "agent_execution_id": "aex-export",
                        "child_job_ids": ["job-child-export"],
                        "child_run_ids": ["run-child-export"],
                        "runtime_control": "workspace_job_queue",
                        "runtime_status": "done",
                        "artifacts": [
                            {
                                "label": "report",
                                "type": "report",
                                "path": "reports/final.md",
                                "status": "done",
                                "summary": "Agent report.",
                            }
                        ],
                    },
                ],
            }
        )
        state.workspaces[0]["runs"] = [run]
        state.jobs = [
            {
                "id": "job-export",
                "status": "done",
                "server_id": "local",
                "command": "echo export",
                "log_path": str(log_path),
                "metadata": {
                    "workspace_id": workspace["id"],
                    "execution_run_id": run["id"],
                    "node_kind": "run.command",
                },
            },
            {
                "id": "job-child-export",
                "status": "done",
                "server_id": "local",
                "command": "echo child export",
                "log_path": str(child_log_path),
                "metadata": {
                    "workspace_id": workspace["id"],
                    "execution_run_id": "run-child-export",
                    "node_kind": "env.prepare",
                    "agent_runtime_tool": True,
                },
            },
            {
                "id": "job-export",
                "status": "done",
                "server_id": "local",
                "command": "echo foreign",
                "log_path": str(foreign_log_path),
                "metadata": {
                    "workspace_id": "other-workspace",
                    "execution_run_id": run["id"],
                },
            },
        ]

        payload = state.get_workspace_execution_run_export(workspace["id"], run["id"])

        exported = payload["export"]
        assert exported["schema"] == "relaygraph.run.export.v1"
        assert exported["filename"].startswith(f"relaygraph-run-{workspace['id']}-run-export-pkg-export")
        assert exported["replay"]["schema"] == "relaygraph.run.replay.v1"
        assert exported["summary"]["step_count"] == 2
        assert exported["summary"]["linked_job_count"] == 2
        assert exported["summary"]["log_count"] == 2
        assert exported["summary"]["report_count"] >= 1
        assert exported["logs"][0]["job_id"] == "job-export"
        assert exported["logs"][0]["display_log_path"] == "data/logs/local/run.log"
        assert str(tmp_path) not in json.dumps(exported["logs"], ensure_ascii=False)
        assert "final report ready" in exported["logs"][0]["tail"]
        assert "foreign workspace leak" not in json.dumps(exported["logs"], ensure_ascii=False)
        assert any(item["job_id"] == "job-child-export" and "child runtime done" in item["tail"] for item in exported["logs"])
        assert exported["reports"][0]["path"] == "reports/final.md"
        assert exported["manifest"]["schema"] == "relaygraph.run.export.manifest.v1"
        assert exported["manifest"]["run_id"] == "run-export"
        assert exported["manifest"]["included"]["timeline_steps"] == 2
        assert exported["manifest"]["commands"]["run"] == "python train.py"
        assert "RelayGraph Run Export" in exported["readme_markdown"]
        assert "python report.py" in exported["readme_markdown"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)
