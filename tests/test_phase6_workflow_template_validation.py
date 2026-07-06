from __future__ import annotations

import copy
import threading
from typing import Any

import pytest

from total_control.state.registry import RegistryMixin
from total_control.state.workspaces.crud import CrudMixin
from total_control.workspace.cockpit import clean_workspace_placeholder_config_values
from total_control.workspace.schema import (
    build_default_workflow_templates,
    build_template_snapshot,
    normalize_workspace_instance_from_template,
    normalize_global_agent_definition,
    workflow_template_snapshot_diff,
    workflow_template_topology_preview,
    workspace_default_agents,
    workspace_default_tools,
)


class _FakeState(RegistryMixin, CrudMixin):
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.tool_definitions = workspace_default_tools()
        self.agent_definitions = workspace_default_agents()
        self.provider_profiles: list[dict[str, Any]] = []
        self.workspaces: list[dict[str, Any]] = []
        self.workflow_templates = build_default_workflow_templates(
            self.agent_definitions,
            self.tool_definitions,
        )

    def workflow_template_public_payload(self, template: dict[str, Any]) -> dict[str, Any]:
        payload = clean_workspace_placeholder_config_values(template)
        payload["node_count"] = len(payload.get("nodes") or [])
        payload["agent_count"] = len(payload.get("agent_ids") or [])
        payload["tool_count"] = len(payload.get("tool_ids") or [])
        return payload

    def save_workflow_templates(self) -> None:
        pass

    def save_agent_definitions(self) -> None:
        pass

    def save_tool_definitions(self) -> None:
        pass

    def save_workspaces(self) -> None:
        pass

    def workspace_public_payload(self, workspace: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(workspace)

    def workspace_by_id(self, workspace_id: str) -> dict[str, Any] | None:
        return next((item for item in self.workspaces if item.get("id") == workspace_id), None)


def _default_template() -> dict[str, Any]:
    state = _FakeState()
    return copy.deepcopy(state.workflow_templates[0])


def test_workflow_template_preview_marks_default_template_ready():
    state = _FakeState()
    result = state.validate_workflow_template(_default_template())
    validation = result["validation"]
    topology = result["preview"]["topology_preview"]

    assert validation["status"] == "ready"
    assert validation["blocking_count"] == 0
    assert result["preview"]["node_count"] == len(result["workflow_template"]["nodes"])
    assert result["preview"]["nodes"][0]["input_mapping"]
    assert topology["schema"] == "relaygraph.workflow_template.topology_preview.v1"
    assert topology["layout_mode"] == "sequence"
    assert topology["node_count"] == len(result["workflow_template"]["nodes"])
    assert topology["control_edge_count"] == len(result["workflow_template"]["links"])
    assert topology["layer_count"] == len(result["workflow_template"]["nodes"])
    assert topology["layers"][0]["node_ids"] == [result["workflow_template"]["nodes"][0]["id"]]
    assert topology["bounds"]["width"] > 0
    assert topology["nodes"][1]["x"] > topology["nodes"][0]["x"]


def test_workflow_template_preview_topology_marks_branch_layout():
    template = _default_template()
    nodes = template["nodes"][:4]
    links = [
        {"id": "root-to-left", "from": nodes[0]["id"], "to": nodes[1]["id"]},
        {"id": "root-to-right", "from": nodes[0]["id"], "to": nodes[2]["id"]},
        {"id": "left-to-join", "from": nodes[1]["id"], "to": nodes[3]["id"]},
        {"id": "right-to-join", "from": nodes[2]["id"], "to": nodes[3]["id"]},
    ]

    topology = workflow_template_topology_preview(nodes, links)

    assert topology["layout_mode"] == "branch"
    assert topology["branch_count"] == 1
    assert topology["join_count"] == 1
    assert topology["layer_count"] == 3
    assert topology["layers"][1]["count"] == 2
    assert topology["nodes"][0]["outgoing_count"] == 2
    assert topology["nodes"][-1]["incoming_count"] == 2
    assert topology["control_edge_count"] == 4
    assert topology["bounds"]["height"] > topology["spacing"]["node_height"]


def test_workflow_template_topology_preview_handles_long_sequence_without_truncating():
    nodes = [
        {"id": f"node-{index}", "kind": "custom.step", "title": f"Node {index}", "output_key": f"out_{index}"}
        for index in range(72)
    ]
    links = [
        {"id": f"link-{index}", "from": f"node-{index}", "to": f"node-{index + 1}"}
        for index in range(len(nodes) - 1)
    ]

    topology = workflow_template_topology_preview(nodes, links)

    assert topology["layout_mode"] == "sequence"
    assert topology["node_count"] == 72
    assert topology["control_edge_count"] == 71
    assert topology["layer_count"] == 72
    assert len(topology["nodes"]) == 72
    assert topology["nodes"][-1]["x"] > topology["nodes"][0]["x"]


def test_workflow_template_topology_preview_adds_data_ref_edges():
    nodes = [
        {"id": "source", "kind": "source.repo", "title": "Source", "output_key": "source_out"},
        {"id": "inspect", "kind": "repo.inspect", "title": "Inspect", "output_key": "inspect_out"},
        {"id": "report", "kind": "eval.report", "title": "Report", "output_key": "report_out"},
    ]
    links = [
        {"id": "source-inspect", "from": "source", "to": "inspect"},
        {"id": "inspect-report", "from": "inspect", "to": "report"},
    ]
    contract_nodes = [
        {"id": "source", "input_refs": []},
        {"id": "inspect", "input_refs": []},
        {
            "id": "report",
            "input_refs": [
                {
                    "name": "analysis",
                    "source": "$context.outputs.inspect_out",
                    "status": "ready",
                    "upstream_node_id": "inspect",
                    "upstream_output_key": "inspect_out",
                }
            ],
        },
    ]

    topology = workflow_template_topology_preview(nodes, links, contract_nodes=contract_nodes)

    assert topology["data_edge_count"] == 1
    data_edge = topology["data_edges"][0]
    assert data_edge["kind"] == "data_ref"
    assert data_edge["from"] == "inspect"
    assert data_edge["to"] == "report"
    assert data_edge["input_name"] == "analysis"


def test_default_template_keeps_user_inputs_empty():
    template = _default_template()
    assert template["source"]["repo_url"] == ""
    assert template["source"]["repo_ref"] == ""
    assert template["workspace_dir"] == ""
    assert template["env"]["name"] == ""
    assert template["env"]["python"] == ""
    assert template["recipes"][0]["setup_command"] == ""

    node_by_kind = {node["kind"]: node for node in template["nodes"]}
    assert node_by_kind["path.resolve"]["config"]["output_roots"] == ""
    assert node_by_kind["repo.inspect"]["config"]["questions"] == ""
    assert node_by_kind["env.infer"]["config"]["manifest_paths"] == ""
    assert node_by_kind["env.prepare"]["config"]["env_manager"] == ""
    assert node_by_kind["gpu.allocate"]["config"]["gpu_policy"] == ""
    assert node_by_kind["run.command"]["config"]["gpu_policy"] == ""
    assert node_by_kind["artifact.collect"]["config"]["artifact_paths"] == ""


def test_template_public_payload_hides_legacy_placeholder_defaults():
    state = _FakeState()
    template = _default_template()
    node_by_kind = {node["kind"]: node for node in template["nodes"]}
    node_by_kind["path.resolve"]["config"]["output_roots"] = "runs\noutputs\ncheckpoints\nlogs"
    node_by_kind["repo.inspect"]["config"]["questions"] = "入口、依赖、默认配置、结果目录"
    node_by_kind["env.infer"]["config"]["manifest_paths"] = "requirements.txt, pyproject.toml, environment.yml, setup.py"
    node_by_kind["artifact.collect"]["config"]["artifact_paths"] = "runs\noutputs\ncheckpoints\nlogs"

    public = state.workflow_template_public_payload(template)
    public_by_kind = {node["kind"]: node for node in public["nodes"]}

    assert public_by_kind["path.resolve"]["config"]["output_roots"] == ""
    assert public_by_kind["repo.inspect"]["config"]["questions"] == ""
    assert public_by_kind["env.infer"]["config"]["manifest_paths"] == ""
    assert public_by_kind["artifact.collect"]["config"]["artifact_paths"] == ""


def test_workflow_template_preview_treats_unknown_id_as_draft():
    state = _FakeState()
    template = _default_template()
    template["id"] = "new-unsaved-template"

    result = state.validate_workflow_template(template)

    assert result["workflow_template"]["id"] == "new-unsaved-template"
    assert result["validation"]["blocking_count"] == 0


def test_workflow_template_validation_blocks_unknown_agent():
    state = _FakeState()
    template = _default_template()
    template["nodes"][1]["handler"]["mode"] = "agent"
    template["nodes"][1]["handler"]["agent_id"] = "missing-agent"

    result = state.validate_workflow_template(template)
    issues = result["validation"]["issues"]

    assert result["validation"]["status"] == "blocked"
    assert any(issue["code"] == "unknown_agent" for issue in issues)


def test_workflow_template_validation_blocks_dangling_link():
    state = _FakeState()
    template = _default_template()
    template["links"] = [
        *template["links"],
        {"id": "bad-link", "from": template["nodes"][0]["id"], "to": "missing-node"},
    ]

    result = state.validate_workflow_template(template)
    issues = result["validation"]["issues"]

    assert result["validation"]["status"] == "blocked"
    assert any(issue["code"] == "dangling_link" for issue in issues)


def test_global_agent_definition_keeps_runtime_boundaries():
    agent = normalize_global_agent_definition(
        {
            "id": "runtime-agent",
            "name": "Runtime Agent",
            "role": "runner",
            "tools": ["job.run"],
            "max_iterations": 4,
            "timeout_seconds": 30,
            "output_format": "json",
        },
        tool_ids=["job.run"],
    )

    assert agent["max_iterations"] == 4
    assert agent["timeout_seconds"] == 30
    assert agent["output_format"] == "json"


def test_workflow_template_validation_warns_on_agent_override_without_profile():
    state = _FakeState()
    template = _default_template()
    template["model"] = {"routing_mode": "agent_override", "provider_profile_id": ""}

    result = state.validate_workflow_template(template)
    issues = result["validation"]["issues"]

    assert result["validation"]["status"] == "warning"
    assert any(issue["code"] == "agent_override_without_profile" for issue in issues)


def test_workspace_template_diff_reports_snapshot_drift():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {"goal_text": "Compare template drift"},
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    current["model"] = {"routing_mode": "agent_override", "provider_profile_id": "profile-new"}
    current["nodes"][1]["handler"]["agent_id"] = "changed-agent"
    current["nodes"].append(
        {
            "id": "extra-report",
            "kind": "eval.report",
            "title": "Extra Report",
            "handler": {"mode": "agent", "agent_id": "changed-agent"},
            "config": {},
        }
    )
    state.workflow_templates[0] = current

    result = state.workspace_template_diff(workspace["id"])
    diff = result["diff"]

    assert diff["schema"] == "relaygraph.workflow_template.snapshot_diff.v1"
    assert diff["status"] == "changed"
    assert diff["summary"]["added_node_count"] == 1
    assert diff["summary"]["changed_node_count"] >= 1
    assert "model" in diff["diff"]["changed_fields"]
    assert diff["diff"]["added_nodes"][0]["id"] == "extra-report"
    plan = diff["migration_plan"]
    assert plan["schema"] == "relaygraph.workflow_template.migration_plan.v1"
    assert plan["status"] in {"manual_review", "review"}
    assert plan["can_auto_apply"] is False
    assert any(step["id"] == "review-added-nodes" for step in plan["steps"])
    assert any(step["id"] == "review-changed-nodes" for step in plan["steps"])
    assert any(step["id"] == "validate-before-run" for step in plan["steps"])
    preview = diff["structure_preview"]
    assert preview["schema"] == "relaygraph.workflow_template.structure_preview.v1"
    assert preview["topology_changed"] is True
    assert preview["current_count"] == len(current["nodes"])
    assert any(node["id"] == "extra-report" and node["status"] == "added" for node in preview["current_nodes"])
    assert any(node["id"] == current["nodes"][1]["id"] and node["status"] == "changed" for node in preview["current_nodes"])


def test_workspace_template_diff_migration_plan_flags_link_changes_for_new_workspace():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {"goal_text": "Compare topology drift"},
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    current["links"] = []
    state.workflow_templates[0] = current

    diff = state.workspace_template_diff(workspace["id"])["diff"]
    plan = diff["migration_plan"]
    link_preview = diff["link_preview"]

    assert diff["status"] == "changed"
    assert "links" in diff["diff"]["changed_fields"]
    assert link_preview["schema"] == "relaygraph.workflow_template.link_preview.v1"
    assert link_preview["topology_changed"] is True
    assert link_preview["removed_links"]
    assert link_preview["previous_count"] == len(template["links"])
    assert link_preview["current_count"] == 0
    assert diff["summary"]["removed_link_count"] == len(template["links"])
    assert plan["status"] == "manual_review"
    assert plan["strategy"] == "create_new_workspace"
    assert plan["risk_level"] == "high"
    assert "link_topology_changed" in plan["warnings"]


def test_workspace_template_diff_includes_previous_and_current_topology_preview():
    state = _FakeState()
    previous_template = _default_template()
    previous_snapshot = build_template_snapshot(previous_template, state.agent_definitions, state.tool_definitions)
    current_snapshot = copy.deepcopy(previous_snapshot)
    nodes = current_snapshot["nodes"][:4]
    current_snapshot["nodes"] = nodes
    current_snapshot["links"] = [
        {"id": "root-to-left", "from": nodes[0]["id"], "to": nodes[1]["id"]},
        {"id": "root-to-right", "from": nodes[0]["id"], "to": nodes[2]["id"]},
        {"id": "left-to-join", "from": nodes[1]["id"], "to": nodes[3]["id"]},
        {"id": "right-to-join", "from": nodes[2]["id"], "to": nodes[3]["id"]},
    ]

    diff = workflow_template_snapshot_diff(previous_snapshot, current_snapshot)
    topology = diff["topology_preview"]

    assert topology["schema"] == "relaygraph.workflow_template.topology_diff_preview.v1"
    assert topology["previous"]["layout_mode"] == "sequence"
    assert topology["current"]["layout_mode"] == "branch"
    assert topology["layout_changed"] is True
    assert topology["current"]["branch_count"] == 1
    assert topology["current"]["join_count"] == 1


def test_workspace_template_diff_distinguishes_link_metadata_from_topology():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {"goal_text": "Compare link metadata drift"},
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    current["links"] = [
        {**link, "id": f"renamed-link-{index}"}
        for index, link in enumerate(current["links"], start=1)
    ]
    state.workflow_templates[0] = current

    diff = state.workspace_template_diff(workspace["id"])["diff"]
    link_preview = diff["link_preview"]
    plan = diff["migration_plan"]

    assert diff["status"] == "changed"
    assert "links" in diff["diff"]["changed_fields"]
    assert link_preview["topology_changed"] is False
    assert link_preview["order_changed"] is False
    assert link_preview["metadata_changed"] is True
    assert link_preview["added_links"] == []
    assert link_preview["removed_links"] == []
    assert diff["summary"]["added_link_count"] == 0
    assert diff["summary"]["removed_link_count"] == 0
    assert "link_metadata_changed" in plan["warnings"]
    assert "link_topology_changed" not in plan["warnings"]


def test_workflow_template_version_history_records_create_update_and_skips_noop():
    state = _FakeState()

    created = state.create_workflow_template(
        {
            "id": "history-template",
            "name": "History Template",
            "source_type": "repo",
            "brief": "Track template versions",
        }
    )
    stored = state.workflow_template_by_id(created["id"])
    assert stored is not None
    assert stored["version_history"][0]["mode"] == "create"
    assert stored["version_history"][0]["summary"]["added_node_count"] == len(stored["nodes"])

    updated = state.update_workflow_template(
        created["id"],
        {
            "description": "Updated description",
            "nodes": [
                *stored["nodes"],
                {
                    "id": "version-extra",
                    "kind": "eval.report",
                    "title": "Version Extra",
                    "handler": {"mode": "agent", "agent_id": state.agent_definitions[0]["id"]},
                    "config": {},
                },
            ],
            "links": stored["links"],
        },
    )
    refreshed = state.workflow_template_by_id(created["id"])
    assert refreshed is not None
    assert updated["version_history"][0]["mode"] == "update"
    assert refreshed["version_history"][0]["mode"] == "update"
    assert refreshed["version_history"][0]["summary"]["added_node_count"] == 1
    assert "metadata.description" in refreshed["version_history"][0]["changed_fields"]
    assert refreshed["version_history"][1]["mode"] == "create"

    before_count = len(refreshed["version_history"])
    state.update_workflow_template(created["id"], copy.deepcopy(refreshed))
    assert len(state.workflow_template_by_id(created["id"])["version_history"]) == before_count


def test_workspace_template_migration_apply_updates_safe_node_changes_and_history():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {"goal_text": "Apply safe template drift"},
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    workspace["runs"] = [{"id": "kept-run", "status": "done"}]
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    target_node = current["nodes"][1]
    target_node["title"] = "Updated node title"
    target_node["input_mapping"] = {"task": "$input.goal_text"}
    state.workflow_templates[0] = current

    before = state.workspace_template_diff(workspace["id"])["diff"]
    assert before["migration_plan"]["can_manual_apply"] is True

    result = state.apply_workspace_template_migration(workspace["id"], {"confirm": True})

    assert result["applied"]["ok"] is True
    assert result["diff"]["status"] == "same"
    updated = state.workspace_by_id(workspace["id"])
    assert updated is not None
    updated_node = next(node for node in updated["nodes"] if node["id"] == target_node["id"])
    assert updated_node["title"] == "Updated node title"
    assert updated_node["input_mapping"] == {"task": "$input.goal_text"}
    assert updated["runs"][0]["id"] == "kept-run"
    assert updated["template_migration_history"][0]["mode"] == "safe_manual"


def test_workspace_template_migration_apply_blocks_topology_changes():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {"goal_text": "Block topology drift"},
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    current["links"] = []
    state.workflow_templates[0] = current

    with pytest.raises(ValueError, match="new workspace or manual rebuild"):
        state.apply_workspace_template_migration(workspace["id"], {"confirm": True})


def test_workspace_template_migration_create_draft_preserves_inputs_without_runs():
    state = _FakeState()
    template = copy.deepcopy(state.workflow_templates[0])
    workspace = normalize_workspace_instance_from_template(
        {
            "goal_text": "Create structural migration draft",
            "context_blocks": ["keep this context"],
            "workspace_dir": "/tmp/source-workspace",
        },
        template=template,
        agent_definitions=state.agent_definitions,
        tool_definitions=state.tool_definitions,
    )
    workspace["runs"] = [{"id": "do-not-copy", "status": "done"}]
    state.workspaces = [workspace]

    current = copy.deepcopy(template)
    current["nodes"].append(
        {
            "id": "new-eval",
            "kind": "eval.report",
            "title": "New Eval",
            "handler": {"mode": "agent", "agent_id": "reporter"},
            "input_mapping": {"metrics": "$context.outputs.metrics"},
            "config": {},
        }
    )
    state.workflow_templates[0] = current

    with pytest.raises(ValueError, match="new workspace or manual rebuild"):
        state.apply_workspace_template_migration(workspace["id"], {"confirm": True})

    result = state.create_workspace_template_migration_draft(workspace["id"], {"confirm": True})

    assert result["created"]["ok"] is True
    assert result["draft_workspace_id"] != workspace["id"]
    assert result["diff"]["status"] == "same"
    assert len(state.workspaces) == 2
    draft = state.workspace_by_id(result["draft_workspace_id"])
    assert draft is not None
    assert draft["inputs"]["context_blocks"] == ["keep this context"]
    assert draft["workspace_dir"] == "/tmp/source-workspace"
    assert draft["runs"] == []
    assert draft["source_migration"]["source_workspace_id"] == workspace["id"]
    assert draft["template_migration_history"][0]["mode"] == "structural_draft"
    assert any(node["id"] == "new-eval" for node in draft["nodes"])
