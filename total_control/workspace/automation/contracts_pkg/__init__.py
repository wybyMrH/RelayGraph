"""Workspace IO / workflow / orchestration contracts."""

from __future__ import annotations

from .context import (
    workspace_node_workflow_contract_metadata,
    workspace_context_ref_value,
    workspace_context_value_present,
    workspace_input_data_for_context,
    workspace_context_input_summary,
    workspace_context_mapping_status,
    derive_workspace_execution_context,
)

from .io import (
    workspace_io_contract_for_kind,
    workspace_node_config_signal,
    workspace_io_input_mapping,
    workspace_has_explicit_input_mapping,
    workspace_contract_output_key_for_node,
    workspace_contract_input_ref_state,
    workspace_contract_input_refs,
    workspace_apply_auto_input_mapping_fallbacks,
    workspace_required_input_names,
    workspace_unmapped_required_inputs,
)

from .orchestration import (
    workspace_orchestration_gap_matches_node,
    workspace_orchestration_status,
    derive_workspace_orchestration_contract,
)

from .workflow import (
    derive_workspace_workflow_contract,
)

__all__ = [
    "workspace_node_workflow_contract_metadata",
    "workspace_context_ref_value",
    "workspace_context_value_present",
    "workspace_input_data_for_context",
    "workspace_context_input_summary",
    "workspace_context_mapping_status",
    "derive_workspace_execution_context",
    "workspace_io_contract_for_kind",
    "workspace_node_config_signal",
    "workspace_io_input_mapping",
    "workspace_has_explicit_input_mapping",
    "workspace_contract_output_key_for_node",
    "workspace_contract_input_ref_state",
    "workspace_contract_input_refs",
    "workspace_apply_auto_input_mapping_fallbacks",
    "workspace_required_input_names",
    "workspace_unmapped_required_inputs",
    "workspace_orchestration_gap_matches_node",
    "workspace_orchestration_status",
    "derive_workspace_orchestration_contract",
    "derive_workspace_workflow_contract",
]
