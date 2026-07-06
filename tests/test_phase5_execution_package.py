"""Phase 5 — execution package gate, package_id, and run snapshot persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from total_control.state import TotalControlState
from total_control.workspace.automation.bundle import (
    make_execution_package_id,
    make_stable_execution_package_id,
    workspace_execution_package_runtime_binding,
    workspace_execution_package_runtime_binding_checks,
    workspace_execution_package_manifest,
)
from total_control.state.workspaces.nodes import NodesMixin
from total_control.workspace.cockpit.payload import normalize_workspace_payload
from total_control.workspace.cockpit.discovery import workspace_dataset_root_verification
from total_control.workspace.cockpit.fsm import workspace_execution_package_blocking_checks
from total_control.orchestration.types import StepResult
from total_control.orchestration.workflow_runner import WorkflowRunnerCallbacks, run_workflow_sequence
from total_control.workspace.execution.runs import (
    normalize_workspace_execution_run,
    workspace_execution_run_delivery_closure,
    workspace_run_step_from_agent,
    workspace_run_step_from_job,
)
from total_control.tools.workspace_executor_pkg.web_search import execute_web_search
from total_control.workspace.errors import WorkspaceWorkflowReadinessError


class _StubContext:
    def source_payload(self):
        return {"goal_text": "test query", "repo_urls": ["https://github.com/example/repo"], "paper_urls": [], "references": []}


class _NodePayloadState(NodesMixin):
    def server_by_id(self, server_id):
        return {"id": server_id} if server_id == "local" else None


def _isolated_state(monkeypatch, tmp_path) -> TotalControlState:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    paths = {
        "JOBS_PATH": runtime_dir / "jobs.json",
        "WORKSPACES_PATH": runtime_dir / "workspaces.json",
        "PROVIDER_PROFILES_PATH": runtime_dir / "provider_profiles.json",
        "TOOL_DEFINITIONS_PATH": runtime_dir / "tool_definitions.json",
        "AGENT_DEFINITIONS_PATH": runtime_dir / "agent_definitions.json",
        "WORKFLOW_TEMPLATES_PATH": runtime_dir / "workflow_templates.json",
    }
    for path in paths.values():
        path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("total_control.secrets_crypto.MASTER_KEY_PATH", runtime_dir / ".master_key")
    for module in ("total_control.state.base", "total_control.state.persistence"):
        for name, path in paths.items():
            monkeypatch.setattr(f"{module}.{name}", path)
    return TotalControlState(Path("config/servers.toml"))


def _phase5_node(node_id: str, kind: str, title: str, config: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "id": node_id,
        "kind": kind,
        "title": title,
        "handler": {"mode": "system", "agent_id": "runner", "name": "Runner"},
        "config": config or {},
    }


def _phase5_workspace(tmp_path, *, data_root: str = "", dataset_hints: str = "dataset-name-only") -> dict[str, object]:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(exist_ok=True)
    return normalize_workspace_payload(
        {
            "name": "Phase 5 Ready",
            "brief": "Reproduce a dataset benchmark.",
            "workspace_dir": str(workspace_dir),
            "inputs": {"goal_text": "Run a dataset benchmark."},
            "env": {"name": "xng", "manager": "conda", "python": "3.10"},
            "agents": [{"id": "runner", "name": "Runner", "role": "executor"}],
            "nodes": [
                _phase5_node(
                    "path-1",
                    "path.resolve",
                    "Resolve Paths",
                    {
                        "workspace_dir": str(workspace_dir),
                        "data_roots": data_root,
                        "output_roots": "runs\noutputs\nreports\nlogs",
                    },
                ),
                _phase5_node(
                    "dataset-1",
                    "dataset.find",
                    "Find Dataset",
                    {
                        "dataset_hints": dataset_hints,
                        "data_roots": data_root,
                    },
                ),
                _phase5_node("env-infer-1", "env.infer", "Infer Env", {"workspace_dir": str(workspace_dir)}),
                _phase5_node(
                    "env-prepare-1",
                    "env.prepare",
                    "Prepare Env",
                    {"workspace_dir": str(workspace_dir), "setup_command": "python -V", "server_id": "local"},
                ),
                _phase5_node("gpu-1", "gpu.allocate", "Allocate CPU", {"gpu_policy": "cpu", "server_id": "local"}),
                _phase5_node(
                    "run-1",
                    "run.command",
                    "Run",
                    {
                        "workspace_dir": str(workspace_dir),
                        "run_command": "python -c 'print(1)'",
                        "gpu_policy": "cpu",
                        "server_id": "local",
                    },
                ),
                _phase5_node(
                    "collect-1",
                    "artifact.collect",
                    "Collect",
                    {
                        "workspace_dir": str(workspace_dir),
                        "artifact_paths": "runs/latest\noutputs\nreports\nlogs",
                        "metric_paths": "runs/latest/metrics.json",
                        "server_id": "local",
                    },
                ),
                _phase5_node(
                    "report-1",
                    "eval.report",
                    "Report",
                    {
                        "workspace_dir": str(workspace_dir),
                        "report_command": "python -c 'print(\"report\")'",
                        "server_id": "local",
                    },
                ),
            ],
        }
    )


def test_execution_package_blocks_full_workflow_when_not_ready():
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "ready_to_execute": False,
                "missing": [
                    {
                        "field": "run_command",
                        "label": "运行命令",
                        "status": "blocked",
                        "action": "补 run.command。",
                        "node_kind": "run.command",
                        "node_id": "run-1",
                    }
                ],
            }
        }
    }
    checks = workspace_execution_package_blocking_checks(automation, full_workflow=True)
    assert len(checks) == 1
    assert checks[0]["id"] == "execution_package"
    assert "run.command" in checks[0]["detail"] or "运行" in checks[0]["title"]


def test_execution_package_skips_gate_when_ready():
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {"ready_to_execute": True, "missing": []},
        }
    }
    assert workspace_execution_package_blocking_checks(automation, full_workflow=True) == []


def test_execution_package_gate_skipped_for_partial_run():
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {"ready_to_execute": False, "missing": [{"status": "blocked"}]},
        }
    }
    assert workspace_execution_package_blocking_checks(automation, full_workflow=False) == []


def test_make_execution_package_id_is_stable_prefix():
    package_id = make_execution_package_id("ws-demo-123")
    assert package_id.startswith("pkg-ws-demo-123-")


def test_stable_execution_package_id_tracks_package_content():
    seed = {"target": {"workspace_dir": "/tmp/demo"}, "commands": {"run_command": "python train.py"}}
    same = {"commands": {"run_command": "python train.py"}, "target": {"workspace_dir": "/tmp/demo"}}
    changed = {"target": {"workspace_dir": "/tmp/demo"}, "commands": {"run_command": "python eval.py"}}

    package_id = make_stable_execution_package_id("ws-demo-123", seed)

    assert package_id == make_stable_execution_package_id("ws-demo-123", same)
    assert package_id != make_stable_execution_package_id("ws-demo-123", changed)
    assert package_id.startswith("pkg-ws-demo-123-")


def test_execution_package_manifest_carries_provenance_and_dataset_roots():
    manifest = workspace_execution_package_manifest(
        {"id": "ws-demo-123", "name": "Demo"},
        {"mode": "reproduce"},
        {},
        {"workspace_dir": "/tmp/demo"},
        [],
        [],
        {"ready": True, "status": "ready"},
        commands={"run_command": "python train.py"},
        paths={"workspace_dir": "/tmp/demo"},
        evidence={},
        scheduler={"selected": {"server_id": "local", "gpu_index": "0"}},
        provenance={"commands.run_command": {"source": "run.command.config", "status": "ready"}},
        dataset_discovery={"root_verification": [{"path": "/tmp", "status": "verified"}]},
        package_id="pkg-ws-demo-123-stable",
        selected_nodes=[{"id": "run-1", "kind": "run.command"}],
    )

    assert manifest["provenance"]["commands.run_command"]["source"] == "run.command.config"
    assert manifest["dataset_discovery"]["root_verification"][0]["status"] == "verified"
    assert manifest["selected_nodes"][0]["kind"] == "run.command"


def test_generated_execution_package_manifest_carries_dataset_env_artifact_report(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        data_root = tmp_path / "datasets"
        data_root.mkdir()
        workspace = _phase5_workspace(tmp_path, data_root=str(data_root), dataset_hints=str(data_root))
        public = state.workspace_public_payload(workspace)

        bundle = public["automation"]["reproduction_manifest"]["execution_bundle"]
        manifest = bundle["package_manifest"]
        provenance = manifest["provenance"]

        assert bundle["ready_to_execute"] is True
        assert manifest["dataset_discovery"]["root_verification"][0]["status"] in {"verified", "found"}
        assert manifest["target"]["env_name"] == "xng"
        assert provenance["target.env_name"]["status"] == "ready"
        assert manifest["commands"]["setup_command"] == "python -V"
        assert manifest["commands"]["report_command"]
        assert manifest["paths"]["artifact_paths"]
        assert manifest["paths"]["metric_paths"] == ["runs/latest/metrics.json"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_execution_package_blocks_hint_only_dataset_root(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _phase5_workspace(tmp_path, data_root="", dataset_hints="dataset-name-only")
        state.workspaces = [workspace]
        public = state.workspace_public_payload(workspace)
        bundle = public["automation"]["reproduction_manifest"]["execution_bundle"]
        missing_fields = {item["field"] for item in bundle["missing"]}

        assert bundle["ready_to_execute"] is False
        assert "dataset_root" in missing_fields

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {"auto_apply": False, "executor_mode": "job"},
            )
        assert any(item.get("id") == "execution_package" for item in exc_info.value.blocked_checks)
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_run_to_run_command_does_not_skip_execution_package_gate(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _phase5_workspace(tmp_path, data_root="", dataset_hints="dataset-name-only")
        state.workspaces = [workspace]
        state.save_workspaces()

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {
                    "until_node_id": "run-1",
                    "auto_apply": False,
                    "executor_mode": "job",
                },
            )

        assert any(item.get("id") == "execution_package" for item in exc_info.value.blocked_checks)
        assert not state.workspace_by_id(workspace["id"]).get("runs")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_force_does_not_bypass_execution_package_gate(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _phase5_workspace(tmp_path, data_root="", dataset_hints="dataset-name-only")
        state.workspaces = [workspace]
        state.save_workspaces()

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {
                    "force": True,
                    "auto_apply": False,
                    "executor_mode": "job",
                },
            )

        assert any(item.get("id") == "execution_package" for item in exc_info.value.blocked_checks)
        assert not state.workspace_by_id(workspace["id"]).get("runs")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_single_run_command_node_requires_ready_execution_package(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = _phase5_workspace(tmp_path, data_root="", dataset_hints="dataset-name-only")
        state.workspaces = [workspace]
        state.save_workspaces()

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_node(
                workspace["id"],
                "run-1",
                {"executor_mode": "job"},
            )

        assert any(item.get("id") == "execution_package" for item in exc_info.value.blocked_checks)
        assert state.jobs == []
        assert not state.workspace_by_id(workspace["id"]).get("runs")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_env_prepare_failure_blocks_direct_full_run_without_force(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        data_root = tmp_path / "datasets"
        data_root.mkdir()
        workspace = _phase5_workspace(tmp_path, data_root=str(data_root), dataset_hints=str(data_root))
        state.workspaces = [workspace]
        state.jobs = [
            {
                "id": "job-env-failed",
                "name": "Prepare Env",
                "status": "failed",
                "error": "setup failed",
                "created_at": "2026-06-01T00:00:00",
                "metadata": {
                    "workspace_id": workspace["id"],
                    "node_id": "env-prepare-1",
                    "node_kind": "env.prepare",
                    "node_title": "Prepare Env",
                },
            }
        ]

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {"auto_apply": False, "executor_mode": "job"},
            )

        assert any(item.get("id") == "env_prepare_failed" for item in exc_info.value.blocked_checks)
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_execution_package_runtime_binding_materializes_scheduler_target():
    automation = {
        "resource_orchestration": {
            "scheduler": {
                "status": "ready",
                "policy": "auto",
                "min_free_memory_mib": 8192,
                "selected": {
                    "status": "ready",
                    "mode": "gpu",
                    "server_id": "local",
                    "gpu_index": "0",
                },
            }
        },
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "0",
                    "gpu_policy": "auto",
                    "env_name": "xng",
                },
                "steps": [{"id": "run", "node_kind": "run.command", "node_id": "run-1", "status": "ready"}],
                "command_script": {"status": "ready", "ready": True},
            }
        },
    }
    node = {"id": "run-1", "kind": "run.command"}

    binding = workspace_execution_package_runtime_binding(
        automation,
        node,
        {"run_command": "python train.py", "min_free_memory_gib": "8"},
        fallback={"server_id": "auto", "gpu_index": "auto", "cwd": "/tmp/stale", "env_name": "base"},
    )

    assert binding["server_id"] == "local"
    assert binding["gpu_index"] == "0"
    assert binding["gpu_policy"] == "auto"
    assert binding["cwd"] == "/srv/project"
    assert binding["env_name"] == "xng"
    assert binding["min_free_mib"] == 8192


def test_run_command_job_payload_uses_execution_package_runtime_binding():
    state = _NodePayloadState()
    workspace = {
        "id": "ws-bind",
        "name": "Binding",
        "workspace_dir": "/tmp/stale",
        "env": {"name": "base"},
    }
    node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {
            "run_command": "python train.py",
            "server_id": "auto",
            "gpu_policy": "auto",
            "min_free_memory_gib": "8",
        },
    }
    automation = {
        "resource_orchestration": {
            "scheduler": {
                "status": "ready",
                "policy": "auto",
                "min_free_memory_mib": 8192,
                "selected": {
                    "status": "ready",
                    "mode": "gpu",
                    "server_id": "local",
                    "gpu_index": "0",
                },
            }
        },
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "0",
                    "gpu_policy": "auto",
                    "env_name": "xng",
                },
                "steps": [{"id": "run", "node_kind": "run.command", "node_id": "run-1", "status": "ready"}],
                "command_script": {"status": "ready", "ready": True},
            }
        },
    }

    payload = state.workspace_node_job_payload(workspace, node, automation=automation)

    assert payload["server_id"] == "local"
    assert payload["gpu_index"] == "0"
    assert payload["cwd"] == "/srv/project"
    assert payload["env_name"] == "xng"
    assert payload["min_free_mib"] == 8192
    assert payload["metadata"]["runtime_binding"]["source"] == "execution_package.target"


def test_run_command_job_payload_allows_stale_config_server_when_package_target_is_valid():
    state = _NodePayloadState()
    workspace = {
        "id": "ws-stale-config",
        "name": "Stale Config",
        "workspace_dir": "/tmp/stale",
        "env": {"name": "base"},
    }
    node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {
            "run_command": "python train.py",
            "server_id": "deleted-server",
            "gpu_policy": "auto",
        },
    }
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "none",
                    "gpu_policy": "cpu",
                    "env_name": "xng",
                },
                "steps": [{"id": "run", "node_kind": "run.command", "node_id": "run-1", "status": "ready"}],
            }
        },
    }

    payload = state.workspace_node_job_payload(workspace, node, automation=automation)

    assert payload["server_id"] == "local"
    assert payload["gpu_index"] == "none"
    assert payload["cwd"] == "/srv/project"


def test_job_payload_ignores_execution_package_target_until_package_is_ready():
    state = _NodePayloadState()
    workspace = {
        "id": "ws-not-ready-target",
        "name": "Not Ready Target",
        "workspace_dir": "/tmp/stale",
        "env": {"name": "base"},
    }
    node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {
            "run_command": "python train.py",
            "server_id": "local",
            "gpu_policy": "cpu",
            "workspace_dir": "/tmp/stale",
        },
    }
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "blocked",
                "ready_to_execute": False,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "0",
                    "gpu_policy": "auto",
                    "env_name": "xng",
                },
                "steps": [{"id": "run", "node_kind": "run.command", "node_id": "run-1", "status": "blocked"}],
            }
        },
    }

    payload = state.workspace_node_job_payload(workspace, node, automation=automation)

    assert payload["cwd"] == "/tmp/stale"
    assert payload["env_name"] == "base"
    assert payload["gpu_index"] == "none"
    assert payload["metadata"]["runtime_binding"]["source"] == "node.config"


def test_runtime_binding_check_blocks_payload_drift_after_package_ready():
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "package_id": "pkg-ws-bind",
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "0",
                    "gpu_policy": "auto",
                    "env_name": "xng",
                },
                "package_manifest": {
                    "commands": {"run_command": "python train.py"},
                },
            }
        },
    }
    node = {"id": "run-1", "kind": "run.command"}
    payload = {
        "server_id": "local",
        "gpu_index": "1",
        "cwd": "/tmp/stale",
        "env_name": "base",
        "command": "python other.py",
        "metadata": {
            "runtime_binding": {
                "gpu_policy": "auto",
                "min_free_mib": 8192,
            },
            "scheduler_binding": {"status": "ready"},
        },
    }

    checks = workspace_execution_package_runtime_binding_checks(automation, node, payload)

    assert len(checks) == 1
    assert checks[0]["id"] == "execution_package_runtime_binding"
    fields = {item["field"] for item in checks[0]["mismatches"]}
    assert {"gpu_index", "cwd", "env_name", "run_command", "min_free_mib"} <= fields


def test_run_command_job_payload_keeps_default_min_free_when_binding_has_no_threshold():
    state = _NodePayloadState()
    workspace = {
        "id": "ws-default-threshold",
        "name": "Default Threshold",
        "workspace_dir": "/srv/project",
        "env": {"name": "xng"},
    }
    node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {
            "run_command": "python train.py",
            "server_id": "local",
            "gpu_policy": "auto",
        },
    }

    payload = state.workspace_node_job_payload(workspace, node, automation={})

    assert "min_free_mib" not in payload
    assert payload["metadata"]["runtime_binding"]["min_free_mib"] == 0


def test_workspace_payload_accepts_env_object_shape():
    workspace = normalize_workspace_payload(
        {
            "name": "Env Shape",
            "workspace_dir": "/srv/project",
            "env": {"name": "xng", "manager": "conda", "python": "3.10"},
            "nodes": [
                {
                    "id": "run-1",
                    "kind": "run.command",
                    "config": {"run_command": "python train.py"},
                }
            ],
        }
    )

    assert workspace["env"] == {"name": "xng", "manager": "conda", "python": "3.10"}
    assert workspace["nodes"][0]["config"]["env_name"] == "xng"


def test_runtime_binding_check_treats_cpu_and_none_as_same_gpu_target():
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "cpu",
                    "gpu_policy": "cpu",
                    "env_name": "xng",
                },
                "package_manifest": {"commands": {"run_command": "python train.py"}},
            }
        },
    }
    payload = {
        "server_id": "local",
        "gpu_index": "none",
        "cwd": "/srv/project",
        "env_name": "xng",
        "command": "python train.py",
        "metadata": {
            "runtime_binding": {"gpu_policy": "cpu"},
        },
    }

    assert workspace_execution_package_runtime_binding_checks(
        automation,
        {"id": "run-1", "kind": "run.command"},
        payload,
    ) == []


def test_package_target_applies_to_non_run_execution_steps():
    state = _NodePayloadState()
    workspace = {
        "id": "ws-setup-bind",
        "name": "Setup Bind",
        "workspace_dir": "/tmp/stale",
        "env": {"name": "base"},
    }
    node = {
        "id": "setup-1",
        "kind": "env.prepare",
        "title": "Setup",
        "config": {
            "setup_command": "python -V",
            "server_id": "auto",
        },
    }
    automation = {
        "reproduction_manifest": {
            "execution_bundle": {
                "status": "ready",
                "ready_to_execute": True,
                "target": {
                    "workspace_dir": "/srv/project",
                    "server_id": "local",
                    "gpu_index": "none",
                    "gpu_policy": "cpu",
                    "env_name": "xng",
                },
                "steps": [{"id": "setup", "node_kind": "env.prepare", "node_id": "setup-1", "status": "ready"}],
            }
        },
    }

    payload = state.workspace_node_job_payload(workspace, node, automation=automation)

    assert payload["server_id"] == "local"
    assert payload["gpu_index"] == "none"
    assert payload["cwd"] == "/srv/project"
    assert payload["env_name"] == "xng"
    assert payload["metadata"]["runtime_binding"]["source"] == "execution_package.target"


def test_partial_run_to_upstream_node_skips_downstream_starter_requirements(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Partial Upstream",
                "brief": "Run only path discovery.",
                "workspace_dir": str(tmp_path),
                "agents": [{"id": "runner", "name": "Runner", "role": "executor"}],
                "nodes": [
                    {
                        "id": "path-1",
                        "kind": "path.resolve",
                        "title": "Path",
                        "handler": {"mode": "system", "agent_id": "runner", "name": "Runner"},
                        "config": {
                            "workspace_dir": str(tmp_path),
                            "data_roots": str(tmp_path),
                            "output_roots": "runs\noutputs",
                        },
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        result = state.run_workspace_workflow(
            workspace["id"],
            {"until_node_id": "path-1", "auto_apply": False, "executor_mode": "job"},
        )

        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["metadata"]["node_kind"] == "path.resolve"
        assert result["run_id"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_agent_workflow_blocks_before_run_when_provider_route_missing(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        workspace = normalize_workspace_payload(
            {
                "name": "Agent Route Missing",
                "brief": "Agent route must be ready before execution.",
                "workspace_dir": str(tmp_path),
                "agents": [{"id": "inspector", "name": "Inspector", "role": "researcher"}],
                "nodes": [
                    {
                        "id": "inspect-1",
                        "kind": "repo.inspect",
                        "title": "Inspect",
                        "handler": {"mode": "agent", "agent_id": "inspector"},
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {"until_node_id": "inspect-1", "auto_apply": False},
            )

        assert any(item.get("id") == "provider_route_not_configured" for item in exc_info.value.blocked_checks)
        assert not state.workspace_by_id(workspace["id"]).get("runs")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_agent_workflow_blocks_before_run_when_provider_profile_not_ready(monkeypatch, tmp_path):
    state = _isolated_state(monkeypatch, tmp_path)
    try:
        state.provider_profiles = [
            {
                "id": "draft-provider",
                "name": "Draft Provider",
                "provider": "openai",
                "base_url": "https://example.invalid/v1",
                "api_key": "",
                "models": ["example-model"],
            }
        ]
        workspace = normalize_workspace_payload(
            {
                "name": "Agent Route Draft",
                "brief": "Agent route must have a healthy provider.",
                "workspace_dir": str(tmp_path),
                "model": {"provider_profile_id": "draft-provider"},
                "agents": [{"id": "inspector", "name": "Inspector", "role": "researcher"}],
                "nodes": [
                    {
                        "id": "inspect-1",
                        "kind": "repo.inspect",
                        "title": "Inspect",
                        "handler": {"mode": "agent", "agent_id": "inspector"},
                    }
                ],
            }
        )
        state.workspaces = [workspace]
        state.save_workspaces()

        with pytest.raises(WorkspaceWorkflowReadinessError) as exc_info:
            state.run_workspace_workflow(
                workspace["id"],
                {"until_node_id": "inspect-1", "auto_apply": False},
            )

        assert any(item.get("id") == "provider_route_not_ready" for item in exc_info.value.blocked_checks)
        assert not state.workspace_by_id(workspace["id"]).get("runs")
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_run_record_persists_package_snapshot_and_id():
    run = normalize_workspace_execution_run(
        {
            "id": "20260617-test-abc",
            "workspace_id": "ws-1",
            "kind": "reproduction",
            "steps": [],
            "package_snapshot": {
                "package_id": "pkg-ws-1-20260617120000-deadbeef",
                "ready_to_execute": True,
                "package_manifest": {"schema": "relaygraph.execution_package.v1"},
            },
        }
    )
    assert run["package_id"] == "pkg-ws-1-20260617120000-deadbeef"
    assert run["package_snapshot"]["ready_to_execute"] is True


def test_run_delivery_closure_surfaces_report_artifacts():
    run = normalize_workspace_execution_run(
        {
            "id": "20260624-report-abc",
            "workspace_id": "ws-1",
            "kind": "reproduction",
            "package_snapshot": {
                "package_id": "pkg-ws-1-report",
                "package_manifest": {
                    "schema": "relaygraph.execution_package.v1",
                    "commands": {"report_command": "python report.py"},
                    "paths": {
                        "artifact_paths": ["runs/latest"],
                        "metric_paths": ["runs/latest/metrics.json"],
                    },
                },
            },
            "steps": [
                {
                    "index": 0,
                    "node_id": "eval-1",
                    "node_kind": "eval.report",
                    "node_title": "结果整理",
                    "executor": "agent",
                    "status": "done",
                    "artifacts": [
                        {
                            "label": "final report",
                            "type": "report",
                            "path": "reports/final.md",
                            "status": "done",
                            "summary": "Accuracy 1.0; smoke passed.",
                        }
                    ],
                }
            ],
        }
    )

    closure = run["package_snapshot"]["delivery_closure"]
    assert closure["report"]["status"] == "ready"
    assert closure["report"]["artifacts"][0]["type"] == "report"
    assert closure["report"]["artifacts"][0]["summary"] == "Accuracy 1.0; smoke passed."


def test_run_delivery_closure_done_when_artifacts_metrics_and_report_are_observed():
    closure = workspace_execution_run_delivery_closure(
        {
            "package_manifest": {
                "commands": {"report_command": "python report.py"},
                "paths": {
                    "artifact_paths": ["runs/latest"],
                    "metric_paths": ["runs/latest/metrics.json"],
                },
            }
        },
        [
            {
                "node_id": "collect-1",
                "node_kind": "artifact.collect",
                "status": "done",
                "artifacts": [
                    {"label": "run dir", "path": "runs/latest", "status": "found"},
                    {"label": "metrics", "path": "runs/latest/metrics.json", "status": "found"},
                ],
                "resources": {"metrics": {"accuracy": 1.0}},
            },
            {
                "node_id": "report-1",
                "node_kind": "eval.report",
                "status": "done",
                "artifacts": [{"label": "report", "type": "report", "path": "reports/final.md", "status": "done"}],
            },
        ],
    )

    assert closure["status"] == "done"
    assert closure["metrics"] == {"accuracy": 1.0}
    assert closure["found_count"] == 3
    assert closure["missing_expected"] == []
    assert closure["report"]["status"] == "ready"


def test_run_delivery_closure_matches_absolute_artifacts_against_workspace_target():
    closure = workspace_execution_run_delivery_closure(
        {
            "target": {"workspace_dir": "/srv/project"},
            "package_manifest": {
                "commands": {"report_command": "python report.py"},
                "paths": {
                    "artifact_paths": ["runs/latest"],
                    "metric_paths": ["runs/latest/metrics.json"],
                },
            },
        },
        [
            {
                "node_id": "collect-1",
                "node_kind": "artifact.collect",
                "status": "done",
                "artifacts": [
                    {"label": "run dir", "path": "/srv/project/runs/latest", "status": "found"},
                    {
                        "label": "metrics",
                        "path": "metrics.json",
                        "resolved_path": "/srv/project/runs/latest/metrics.json",
                        "status": "found",
                    },
                ],
                "resources": {"metrics": {"accuracy": 1.0}},
            },
            {
                "node_id": "report-1",
                "node_kind": "eval.report",
                "status": "done",
                "artifacts": [{"label": "report", "type": "report", "path": "/srv/project/reports/final.md", "status": "done"}],
            },
        ],
    )

    assert closure["status"] == "done"
    assert closure["missing_expected"] == []
    assert closure["missing_artifact_count"] == 0
    assert closure["missing_metric_count"] == 0


def test_run_delivery_closure_warns_when_expected_artifacts_are_missing():
    closure = workspace_execution_run_delivery_closure(
        {
            "package_manifest": {
                "commands": {"report_command": "python report.py"},
                "paths": {
                    "artifact_paths": ["runs/latest"],
                    "metric_paths": ["runs/latest/metrics.json"],
                },
            }
        },
        [],
    )

    assert closure["status"] == "warning"
    assert closure["report"]["status"] == "warning"
    assert closure["missing_expected"] == ["runs/latest", "runs/latest/metrics.json"]
    assert closure["missing_artifact_count"] == 1
    assert closure["missing_metric_count"] == 1


def test_run_delivery_closure_does_not_count_planned_artifact_as_observed():
    closure = workspace_execution_run_delivery_closure(
        {
            "package_manifest": {
                "paths": {
                    "artifact_paths": ["runs/latest"],
                    "metric_paths": [],
                },
            }
        },
        [
            {
                "node_id": "collect-1",
                "node_kind": "artifact.collect",
                "status": "done",
                "artifacts": [
                    {
                        "label": "expected output",
                        "path": "runs/latest",
                        "status": "planned",
                        "exists": False,
                    }
                ],
            }
        ],
    )

    assert closure["status"] == "warning"
    assert closure["found_count"] == 0
    assert closure["missing_expected"] == ["runs/latest"]
    assert closure["missing_artifact_count"] == 1


def test_run_delivery_closure_failed_report_step_is_not_ready():
    closure = workspace_execution_run_delivery_closure(
        {
            "package_manifest": {
                "commands": {"report_command": "python report.py"},
                "paths": {"artifact_paths": [], "metric_paths": []},
            }
        },
        [
            {
                "node_id": "report-1",
                "node_kind": "eval.report",
                "status": "failed",
                "error": "report failed",
            }
        ],
    )

    assert closure["status"] == "failed"
    assert closure["report"]["status"] == "failed"
    assert closure["report"]["failed_step_count"] == 1


def test_mixed_agent_and_job_workflow_appends_to_same_run_shell():
    workspace_id = "ws-mixed"
    run_id = "run-mixed-1"
    workspace = {
        "id": workspace_id,
        "name": "Mixed",
        "inputs": {"goal_text": "Inspect then run."},
        "nodes": [],
    }
    agent_node = {
        "id": "inspect-1",
        "kind": "repo.inspect",
        "title": "Inspect",
        "handler": {"mode": "agent", "agent_id": "agent-1", "output_key": "repo_profile"},
    }
    job_node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {"run_command": "echo ok"},
        "handler": {"mode": "system", "output_key": "run_result"},
    }
    recorded: list[dict[str, object]] = []
    created_jobs: list[dict[str, object]] = []

    def build_job_payload(_workspace, node, previous_job_id="", automation=None):
        return {
            "id": "",
            "name": node["title"],
            "status": "queued",
            "metadata": {
                "workspace_id": workspace_id,
                "node_id": node["id"],
                "node_kind": node["kind"],
                "node_title": node["title"],
            },
        }

    def create_job(payload):
        job = {
            **payload,
            "id": f"job-{len(created_jobs) + 1}",
            "status": "queued",
        }
        created_jobs.append(job)
        return job

    def record_run_steps(current_run_id, steps, jobs):
        recorded.append(
            {
                "run_id": current_run_id,
                "step_executors": [step.get("executor") for step in steps],
                "job_run_ids": [
                    job.get("metadata", {}).get("execution_run_id")
                    for job in jobs
                    if isinstance(job.get("metadata"), dict)
                ],
            }
        )

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=lambda: workspace,
        execute_agent_node=lambda _workspace_id, _node, context: (
            context.with_output("repo_profile", {"summary": "ok"})
            or StepResult(
                status="completed",
                executor="agent",
                output_key="repo_profile",
                agent_execution_id="aex-mixed",
                artifacts=[{"label": "inspect", "path": "repo_profile.txt", "status": "done"}],
            )
        ),
        build_job_payload=build_job_payload,
        create_job=create_job,
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"repo.inspect", "run.command"}),
        record_run_steps=record_run_steps,
    )

    result = run_workflow_sequence(
        workspace_id,
        [agent_node, job_node],
        workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.agent_step_count == 1
    assert len(result.jobs) == 1
    assert [step["executor"] for step in result.run_steps] == ["agent", "job"]
    assert result.run_steps[0]["agent_execution_id"] == "aex-mixed"
    assert result.run_steps[1]["job_id"] == "job-1"
    assert result.jobs[0]["metadata"]["execution_run_id"] == run_id
    assert result.jobs[0]["metadata"]["step_index"] == 1
    assert recorded[-1]["run_id"] == run_id
    assert recorded[-1]["step_executors"] == ["agent", "job"]
    assert recorded[-1]["job_run_ids"] == [run_id]


def test_mixed_agent_runtime_child_job_becomes_next_job_dependency():
    workspace_id = "ws-mixed-runtime"
    run_id = "run-mixed-runtime-1"
    workspace = {"id": workspace_id, "name": "Mixed Runtime", "nodes": []}
    agent_node = {
        "id": "prepare-agent",
        "kind": "env.infer",
        "title": "Prepare Via Agent",
        "handler": {"mode": "agent", "agent_id": "agent-runtime"},
    }
    job_node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {"run_command": "echo ok"},
        "handler": {"mode": "system"},
    }
    created_jobs: list[dict[str, object]] = []

    def build_job_payload(_workspace, node, previous_job_id="", automation=None):
        return {
            "name": node["title"],
            "status": "queued",
            "target_job_ids": [previous_job_id] if previous_job_id else [],
            "metadata": {
                "workspace_id": workspace_id,
                "node_id": node["id"],
                "node_kind": node["kind"],
            },
        }

    def create_job(payload):
        job = {**payload, "id": f"job-{len(created_jobs) + 1}", "status": "queued"}
        created_jobs.append(job)
        return job

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=lambda: workspace,
        execute_agent_node=lambda _workspace_id, _node, _context: StepResult(
            status="completed",
            executor="agent",
            output_key="env_plan",
            agent_execution_id="aex-runtime",
            agent_steps=[
                {
                    "action": "env.prepare",
                    "job_id": "job-agent-child",
                    "run_id": "run-agent-child",
                    "runtime_control": "workspace_job_queue",
                    "runtime_side_effect": "workspace_job",
                    "runtime_status": "done",
                }
            ],
        ),
        build_job_payload=build_job_payload,
        create_job=create_job,
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"env.infer", "run.command"}),
    )

    result = run_workflow_sequence(
        workspace_id,
        [agent_node, job_node],
        workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.stopped_early is False
    assert len(result.jobs) == 1
    assert result.run_steps[0]["child_job_ids"] == ["job-agent-child"]
    assert result.run_steps[0]["runtime_status"] == "done"
    assert result.run_steps[1]["job_id"] == "job-1"
    assert created_jobs[0]["target_job_ids"] == ["job-agent-child"]
    assert created_jobs[0]["metadata"]["execution_run_id"] == run_id


def test_mixed_agent_runtime_child_job_waiting_becomes_downstream_dependency():
    workspace_id = "ws-mixed-waiting"
    run_id = "run-mixed-waiting-1"
    workspace = {"id": workspace_id, "name": "Mixed Waiting", "nodes": []}
    agent_node = {
        "id": "prepare-agent",
        "kind": "env.infer",
        "title": "Prepare Via Agent",
        "handler": {"mode": "agent", "agent_id": "agent-runtime"},
    }
    job_node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {"run_command": "echo should-wait"},
        "handler": {"mode": "system"},
    }
    created_jobs: list[dict[str, object]] = []
    recorded: list[list[str]] = []

    def create_job(payload):
        job = {**payload, "id": f"job-{len(created_jobs) + 1}", "status": "queued"}
        created_jobs.append(job)
        return job

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=lambda: workspace,
        execute_agent_node=lambda _workspace_id, _node, _context: StepResult(
            status="completed",
            executor="agent",
            output_key="env_plan",
            agent_execution_id="aex-waiting",
            agent_steps=[
                {
                    "action": "env.prepare",
                    "job_id": "job-agent-child",
                    "run_id": "run-agent-child",
                    "runtime_control": "workspace_job_queue",
                    "runtime_side_effect": "workspace_job",
                    "runtime_status": "submitted",
                }
            ],
        ),
        build_job_payload=lambda _workspace, node, previous_job_id="", automation=None: {
            "name": node["title"],
            "status": "queued",
            "target_job_ids": [previous_job_id] if previous_job_id else [],
            "metadata": {"workspace_id": workspace_id, "node_id": node["id"], "node_kind": node["kind"]},
        },
        create_job=create_job,
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"env.infer", "run.command"}),
        record_run_steps=lambda _run_id, steps, _jobs: recorded.append([step["executor"] for step in steps]),
    )

    result = run_workflow_sequence(
        workspace_id,
        [agent_node, job_node],
        workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.stopped_early is False
    assert len(result.jobs) == 1
    assert [step["executor"] for step in result.run_steps] == ["agent", "job"]
    assert result.run_steps[0]["child_job_ids"] == ["job-agent-child"]
    assert result.run_steps[0]["runtime_status"] == "submitted"
    assert result.run_steps[1]["job_id"] == "job-1"
    assert created_jobs[0]["target_job_ids"] == ["job-agent-child"]
    assert recorded == [["agent"], ["agent", "job"]]


def test_pending_agent_child_runtime_blocks_downstream_agent_without_dependency_barrier():
    workspace_id = "ws-mixed-agent-waiting"
    run_id = "run-mixed-agent-waiting-1"
    workspace = {"id": workspace_id, "name": "Mixed Agent Waiting", "nodes": []}
    first_agent = {
        "id": "prepare-agent",
        "kind": "env.infer",
        "title": "Prepare Via Agent",
        "handler": {"mode": "agent", "agent_id": "agent-runtime"},
    }
    second_agent = {
        "id": "report-agent",
        "kind": "eval.report",
        "title": "Report Via Agent",
        "handler": {"mode": "agent", "agent_id": "agent-report"},
    }
    calls: list[str] = []

    def execute_agent(_workspace_id, node, _context):
        calls.append(str(node.get("id") or ""))
        return StepResult(
            status="completed",
            executor="agent",
            output_key="env_plan",
            agent_execution_id="aex-waiting",
            agent_steps=[
                {
                    "action": "env.prepare",
                    "job_id": "job-agent-child",
                    "run_id": "run-agent-child",
                    "runtime_control": "workspace_job_queue",
                    "runtime_side_effect": "workspace_job",
                    "runtime_status": "submitted",
                }
            ],
        )

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=lambda: workspace,
        execute_agent_node=execute_agent,
        build_job_payload=lambda _workspace, node, previous_job_id="", automation=None: {
            "name": node["title"],
            "target_job_ids": [previous_job_id] if previous_job_id else [],
            "metadata": {"workspace_id": workspace_id, "node_id": node["id"], "node_kind": node["kind"]},
        },
        create_job=lambda payload: {**payload, "id": "job-should-not-exist"},
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"env.infer", "eval.report"}),
    )

    result = run_workflow_sequence(
        workspace_id,
        [first_agent, second_agent],
        workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.stopped_early is True
    assert result.jobs == []
    assert calls == ["prepare-agent"]
    assert [step["executor"] for step in result.run_steps] == ["agent"]
    assert result.run_steps[0]["runtime_status"] == "submitted"


def test_agent_workspace_mutation_refreshes_downstream_job_payload():
    workspace_id = "ws-agent-refresh"
    run_id = "run-agent-refresh-1"
    initial_workspace = {
        "id": workspace_id,
        "name": "Agent Refresh",
        "nodes": [
            {"id": "agent-1", "kind": "repo.inspect", "handler": {"mode": "agent", "agent_id": "agent-editor"}},
            {"id": "run-1", "kind": "run.command", "title": "Run", "config": {"run_command": "echo old"}},
        ],
    }
    mutated_workspace = {
        **initial_workspace,
        "nodes": [
            initial_workspace["nodes"][0],
            {"id": "run-1", "kind": "run.command", "title": "Run", "config": {"run_command": "echo new"}},
        ],
    }
    refresh_calls = {"count": 0}
    created_jobs: list[dict[str, object]] = []

    def refresh_workspace():
        refresh_calls["count"] += 1
        return initial_workspace if refresh_calls["count"] == 1 else mutated_workspace

    def build_job_payload(workspace, node, previous_job_id="", automation=None):
        source_node = next(item for item in workspace["nodes"] if item["id"] == node["id"])
        return {
            "name": node["title"],
            "command": source_node["config"]["run_command"],
            "target_job_ids": [previous_job_id] if previous_job_id else [],
            "metadata": {"workspace_id": workspace_id, "node_id": node["id"], "node_kind": node["kind"]},
        }

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=refresh_workspace,
        execute_agent_node=lambda _workspace_id, _node, context: (
            context.with_output("repo_profile", {"summary": "mutated"})
            or StepResult(status="completed", executor="agent", output_key="repo_profile")
        ),
        build_job_payload=build_job_payload,
        create_job=lambda payload: created_jobs.append({**payload, "id": "job-1", "status": "queued"}) or created_jobs[-1],
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"repo.inspect", "run.command"}),
    )

    result = run_workflow_sequence(
        workspace_id,
        initial_workspace["nodes"],
        initial_workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.stopped_early is False
    assert len(result.jobs) == 1
    assert created_jobs[0]["command"] == "echo new"


def test_mixed_agent_runtime_child_job_failed_stops_downstream_submission():
    workspace_id = "ws-mixed-failed"
    run_id = "run-mixed-failed-1"
    workspace = {"id": workspace_id, "name": "Mixed Failed", "nodes": []}
    agent_node = {
        "id": "prepare-agent",
        "kind": "env.infer",
        "title": "Prepare Via Agent",
        "handler": {"mode": "agent", "agent_id": "agent-runtime"},
    }
    job_node = {
        "id": "run-1",
        "kind": "run.command",
        "title": "Run",
        "config": {"run_command": "echo should-not-run"},
        "handler": {"mode": "system"},
    }

    callbacks = WorkflowRunnerCallbacks(
        refresh_workspace=lambda: workspace,
        execute_agent_node=lambda _workspace_id, _node, _context: StepResult(
            status="completed",
            executor="agent",
            output_key="env_plan",
            agent_execution_id="aex-failed",
            agent_steps=[
                {
                    "action": "env.prepare",
                    "job_id": "job-agent-child",
                    "run_id": "run-agent-child",
                    "runtime_control": "workspace_job_queue",
                    "runtime_side_effect": "workspace_job",
                    "runtime_status": "failed",
                }
            ],
        ),
        build_job_payload=lambda _workspace, node, previous_job_id="", automation=None: {
            "name": node["title"],
            "status": "queued",
            "target_job_ids": [previous_job_id] if previous_job_id else [],
            "metadata": {"workspace_id": workspace_id, "node_id": node["id"], "node_kind": node["kind"]},
        },
        create_job=lambda payload: {**payload, "id": "job-should-not-exist"},
        step_from_job=workspace_run_step_from_job,
        step_from_agent=workspace_run_step_from_agent,
        executable_node_kinds=frozenset({"env.infer", "run.command"}),
    )

    result = run_workflow_sequence(
        workspace_id,
        [agent_node, job_node],
        workspace,
        run_id=run_id,
        callbacks=callbacks,
    )

    assert result.stopped_early is True
    assert result.jobs == []
    assert [step["executor"] for step in result.run_steps] == ["agent"]
    assert result.run_steps[0]["child_job_ids"] == ["job-agent-child"]
    assert result.run_steps[0]["runtime_status"] == "failed"


def test_dataset_root_verification_taxonomy(tmp_path):
    dataset_file = tmp_path / "dataset.zip"
    dataset_file.write_text("placeholder", encoding="utf-8")
    items = workspace_dataset_root_verification(
        local_roots=["/tmp"],
        found_datasets=["/missing/path", str(dataset_file)],
        hints=["dataset-name-only"],
    )
    by_path = {item["path"]: item["status"] for item in items}
    assert by_path["/tmp"] in {"verified", "found", "missing"}
    assert by_path["/missing/path"] in {"hint", "missing", "found"}
    assert by_path[str(dataset_file)] == "hint"
    assert by_path["dataset-name-only"] == "hint"


def test_web_search_includes_provenance_and_latency_metadata():
    payload = execute_web_search(_StubContext(), {"query": "relaygraph", "limit": 2})
    assert "latency_ms" in payload
    assert "result_provenance" in payload
    assert "rate_limit" in payload
    assert payload["result_count"] >= 0


def test_web_search_firecrawl_adapter_uses_configured_key(monkeypatch):
    requests = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return (
                b'{"success":true,"data":{"web":[{"title":"RelayGraph","url":"https://example.com/relaygraph",'
                b'"description":"Search result."}]}}'
            )

    def fake_urlopen(request, timeout=0):
        requests.append((request, timeout))
        return _Response()

    monkeypatch.setenv("TOTAL_CONTROL_FIRECRAWL_API_KEY", "fc-test-key")
    monkeypatch.delenv("TOTAL_CONTROL_SERPER_API_KEY", raising=False)
    monkeypatch.setattr("total_control.tools.workspace_executor_pkg.web_search.urllib.request.urlopen", fake_urlopen)

    payload = execute_web_search(_StubContext(), {"query": "relaygraph", "limit": 2, "provider": "firecrawl"})

    request, timeout = requests[0]
    assert request.full_url == "https://api.firecrawl.dev/v2/search"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer fc-test-key"
    assert json.loads(request.data.decode("utf-8")) == {"query": "relaygraph", "limit": 2}
    assert timeout == 15
    assert payload["status"] == "found"
    assert payload["provider"] == "firecrawl"
    assert payload["results"][0]["source"] == "firecrawl"


def test_web_search_serper_adapter_normalizes_organic_results(monkeypatch):
    requests = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"organic":[{"title":"Paper","link":"https://example.com/paper","snippet":"Candidate."}]}'

    def fake_urlopen(request, timeout=0):
        requests.append((request, timeout))
        return _Response()

    monkeypatch.setenv("TOTAL_CONTROL_SERPER_API_KEY", "serper-test-key")
    monkeypatch.delenv("TOTAL_CONTROL_FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("total_control.tools.workspace_executor_pkg.web_search.urllib.request.urlopen", fake_urlopen)

    payload = execute_web_search(_StubContext(), {"query": "relaygraph", "limit": 1, "provider": "serper"})

    request, _timeout = requests[0]
    assert request.full_url == "https://google.serper.dev/search"
    assert request.get_header("X-api-key") == "serper-test-key"
    assert json.loads(request.data.decode("utf-8")) == {"q": "relaygraph", "num": 1}
    assert payload["status"] == "found"
    assert payload["provider"] == "serper"
    assert payload["results"][0]["url"] == "https://example.com/paper"


def test_web_search_configured_provider_without_key_degrades_to_seeds(monkeypatch):
    monkeypatch.delenv("TOTAL_CONTROL_FIRECRAWL_API_KEY", raising=False)
    payload = execute_web_search(_StubContext(), {"query": "relaygraph", "provider": "firecrawl", "limit": 2})
    assert payload["status"] == "seeded"
    assert payload["provider"] == "firecrawl"
    assert payload["provider_configured"] is False
    assert payload["fallback_used"] is True
    assert payload["results"][0]["source"] == "workspace.input"
