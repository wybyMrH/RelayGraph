"""Phase 3 #6 — workflow data contract: input-mapping resolution + blocked detection."""

from __future__ import annotations

from total_control.orchestration.input_mapping import resolve_mapped_inputs
from total_control.workspace.automation.contracts_pkg.io import (
    workspace_contract_input_ref_state,
    workspace_contract_input_refs,
)


def test_context_output_resolves_when_present():
    resolved = resolve_mapped_inputs(
        {"repo_profile": "$context.outputs.repo_profile"},
        input_data={},
        context_outputs={"repo_profile": {"entry": "main.py"}},
    )
    assert resolved["repo_profile"] == {"entry": "main.py"}


def test_context_output_missing_returns_none():
    resolved = resolve_mapped_inputs(
        {"repo_profile": "$context.outputs.repo_profile"},
        input_data={},
        context_outputs={},
    )
    assert resolved["repo_profile"] is None


def test_prev_output_resolves_and_blocks_on_first_node():
    # first node (index 0) referencing $prev.output → blocked
    resolved = resolve_mapped_inputs(
        {"x": "$prev.output"},
        input_data={},
        previous_output=None,
    )
    assert resolved["x"] is None


def test_input_ref_state_blocks_on_missing_context_output():
    catalog = {"repo_profile": {"index": 0, "node_id": "n0"}}
    state = workspace_contract_input_ref_state(
        "$context.outputs.repo_profile",
        index=2,
        output_catalog=catalog,
        previous_outputs={},
    )
    assert state["status"] == "blocked"
    assert "repo_profile" in state["detail"]


def test_input_ref_state_ready_when_upstream_output_present():
    previous = {"repo_profile": {"node_id": "n0", "output_key": "repo_profile"}}
    state = workspace_contract_input_ref_state(
        "$context.outputs.repo_profile",
        index=2,
        output_catalog={},
        previous_outputs=previous,
    )
    assert state["status"] == "ready"
    assert state["upstream_node_id"] == "n0"


def test_input_ref_state_blocks_forward_reference():
    catalog = {"repo_profile": {"index": 5, "node_id": "n5"}}  # downstream of index 2
    state = workspace_contract_input_ref_state(
        "$context.outputs.repo_profile",
        index=2,
        output_catalog=catalog,
        previous_outputs={},
    )
    assert state["status"] == "blocked"
    assert "倒挂" in state["detail"]  # execution order inverted


def test_input_refs_aggregate_blocked_for_visibility():
    mapping = {"repo_profile": "$context.outputs.repo_profile", "goal": "$input"}
    catalog = {"repo_profile": {"index": 0, "node_id": "n0"}}
    refs = workspace_contract_input_refs(mapping, index=1, output_catalog=catalog, previous_outputs={})
    by_name = {r["name"]: r for r in refs}
    assert by_name["repo_profile"]["status"] == "blocked"
    assert by_name["goal"]["status"] == "ready"


def test_multi_agent_chain_handoff_via_context_outputs():
    """Simulate two agent steps handing data off through accumulated outputs."""
    accumulated = {}
    # step 1 produces repo_profile
    accumulated["repo_profile"] = {"entry": "train.py"}
    # step 2 consumes it via $context.outputs.repo_profile
    resolved = resolve_mapped_inputs(
        {"repo_profile": "$context.outputs.repo_profile", "path_map": "$context.outputs.path_map"},
        input_data={},
        context_outputs=accumulated,
    )
    assert resolved["repo_profile"] == {"entry": "train.py"}
    # path_map not produced yet → None (blocked upstream)
    assert resolved["path_map"] is None
