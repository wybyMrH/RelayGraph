"""Workspace automation derivation — split by concern."""

from .core import (
    workspace_execution_node_by_kind,
    workspace_automation_check,
    workspace_enrich_readiness_issue,
    workspace_status_priority,
)

from .evidence import (
    workspace_evidence_item,
    workspace_add_evidence_item,
    derive_workspace_automation_evidence,
    workspace_group_evidence_by_kind,
    workspace_evidence_group,
)

from .run_plan import (
    workspace_run_node_phase,
    workspace_run_phase_label,
    workspace_node_required_tool_id,
    workspace_node_command_summary_for_plan,
    derive_workspace_run_plan,
)

from .topology import (
    workspace_model_route_for_agent,
    workspace_agent_topology_gap,
    workspace_topology_status,
    derive_workspace_agent_topology,
)

from .contracts import (
    workspace_io_contract_for_kind,
    workspace_node_config_signal,
    workspace_io_input_mapping,
    workspace_has_explicit_input_mapping,
    workspace_contract_output_key_for_node,
    workspace_contract_input_ref_state,
    workspace_contract_input_refs,
    workspace_apply_auto_input_mapping_fallbacks,
    derive_workspace_workflow_contract,
    workspace_orchestration_gap_matches_node,
    workspace_orchestration_status,
    derive_workspace_orchestration_contract,
    workspace_node_workflow_contract_metadata,
    workspace_context_ref_value,
    workspace_context_value_present,
    workspace_input_data_for_context,
    workspace_context_input_summary,
    workspace_context_mapping_status,
    derive_workspace_execution_context,
)

from .helpers import compact_contract_items

from .reproduction import (
    workspace_reproduction_manifest_item,
    workspace_reproduction_intent,
    derive_workspace_reproduction_manifest,
)

from .deployment import (
    workspace_delivery_contract,
    workspace_deployment_health_path,
    workspace_deployment_service_kind,
    workspace_deployment_port,
    workspace_deployment_host,
    workspace_deployment_stop_command,
    workspace_deployment_plan,
)

from .bundle import (
    make_execution_package_id,
    make_stable_execution_package_id,
    workspace_execution_bundle_step,
    workspace_execution_bundle_missing_item,
    workspace_checkout_command,
    workspace_script_export_line,
    workspace_execution_bundle_command_script,
    workspace_execution_package_manifest,
    workspace_execution_bundle_step_for_node,
    workspace_execution_bundle_job_metadata,
    workspace_scheduler_binding_metadata,
    workspace_execution_bundle_result,
)

from .preflight import (
    workspace_execution_readiness_step,
    workspace_resource_item,
    workspace_preflight_action,
    workspace_preflight_item,
    workspace_preflight_combined_status,
    derive_workspace_preflight,
    derive_workspace_resource_orchestration,
)

from .report import (
    workspace_report_highlight,
    workspace_report_next_action,
    derive_workspace_automation_report,
    derive_workspace_execution_readiness,
)

from .advance import (
    workspace_advance_from_fsm,
    resolve_workspace_advance_bundle,
    derive_workspace_advance_state,
    derive_workspace_automation_advance_hint,
    workspace_playbook_step,
    derive_workspace_automation_playbook,
    derive_workspace_automation_state,
)

__all__ = [
    "workspace_execution_node_by_kind",
    "workspace_automation_check",
    "workspace_enrich_readiness_issue",
    "workspace_status_priority",
    "workspace_evidence_item",
    "workspace_add_evidence_item",
    "derive_workspace_automation_evidence",
    "workspace_group_evidence_by_kind",
    "workspace_evidence_group",
    "workspace_run_node_phase",
    "workspace_run_phase_label",
    "workspace_node_required_tool_id",
    "workspace_node_command_summary_for_plan",
    "derive_workspace_run_plan",
    "workspace_model_route_for_agent",
    "workspace_agent_topology_gap",
    "workspace_topology_status",
    "derive_workspace_agent_topology",
    "workspace_io_contract_for_kind",
    "workspace_node_config_signal",
    "workspace_io_input_mapping",
    "workspace_has_explicit_input_mapping",
    "workspace_contract_output_key_for_node",
    "workspace_contract_input_ref_state",
    "workspace_contract_input_refs",
    "workspace_apply_auto_input_mapping_fallbacks",
    "derive_workspace_workflow_contract",
    "workspace_orchestration_gap_matches_node",
    "workspace_orchestration_status",
    "derive_workspace_orchestration_contract",
    "workspace_node_workflow_contract_metadata",
    "workspace_context_ref_value",
    "workspace_context_value_present",
    "workspace_input_data_for_context",
    "workspace_context_input_summary",
    "workspace_context_mapping_status",
    "derive_workspace_execution_context",
    "workspace_reproduction_manifest_item",
    "workspace_reproduction_intent",
    "compact_contract_items",
    "derive_workspace_reproduction_manifest",
    "workspace_delivery_contract",
    "workspace_deployment_health_path",
    "workspace_deployment_service_kind",
    "workspace_deployment_port",
    "workspace_deployment_host",
    "workspace_deployment_stop_command",
    "workspace_deployment_plan",
    "make_execution_package_id",
    "make_stable_execution_package_id",
    "workspace_execution_bundle_step",
    "workspace_execution_bundle_missing_item",
    "workspace_checkout_command",
    "workspace_script_export_line",
    "workspace_execution_bundle_command_script",
    "workspace_execution_package_manifest",
    "workspace_execution_bundle_step_for_node",
    "workspace_execution_bundle_job_metadata",
    "workspace_scheduler_binding_metadata",
    "workspace_execution_bundle_result",
    "workspace_execution_readiness_step",
    "workspace_resource_item",
    "workspace_preflight_action",
    "workspace_preflight_item",
    "workspace_preflight_combined_status",
    "derive_workspace_preflight",
    "derive_workspace_resource_orchestration",
    "workspace_report_highlight",
    "workspace_report_next_action",
    "derive_workspace_automation_report",
    "derive_workspace_execution_readiness",
    "workspace_advance_from_fsm",
    "resolve_workspace_advance_bundle",
    "derive_workspace_advance_state",
    "derive_workspace_automation_advance_hint",
    "workspace_playbook_step",
    "derive_workspace_automation_playbook",
    "derive_workspace_automation_state",
]
