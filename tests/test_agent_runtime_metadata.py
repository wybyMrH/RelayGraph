from __future__ import annotations

import json

from total_control.agent_executor import _tool_runtime_metadata


def test_tool_runtime_metadata_ignores_invalid_observation_payloads():
    assert _tool_runtime_metadata("") == {}
    assert _tool_runtime_metadata("not-json") == {}
    assert _tool_runtime_metadata(json.dumps(["job-runtime"])) == {}


def test_tool_runtime_metadata_reads_existing_top_level_fields():
    metadata = _tool_runtime_metadata(
        json.dumps(
            {
                "job_id": "job-top",
                "run_id": "run-top",
                "runtime_control": "workspace_job_queue",
                "runtime_side_effect": "mutate_runtime",
                "status": "submitted",
            }
        )
    )

    assert metadata == {
        "job_id": "job-top",
        "run_id": "run-top",
        "runtime_control": "workspace_job_queue",
        "runtime_side_effect": "mutate_runtime",
        "runtime_status": "submitted",
    }


def test_tool_runtime_metadata_reads_nested_runtime_adapter_fields():
    metadata = _tool_runtime_metadata(
        json.dumps(
            {
                "job": {"id": "job-nested"},
                "run": {"id": "run-nested"},
                "runtime": {
                    "control": "workspace_job_queue",
                    "side_effect": "mutate_runtime",
                    "status": "waiting",
                },
            }
        )
    )

    assert metadata == {
        "job_id": "job-nested",
        "run_id": "run-nested",
        "runtime_control": "workspace_job_queue",
        "runtime_side_effect": "mutate_runtime",
        "runtime_status": "waiting",
    }


def test_tool_runtime_metadata_keeps_top_level_fields_ahead_of_nested_fields():
    metadata = _tool_runtime_metadata(
        json.dumps(
            {
                "job_id": "job-top",
                "run_id": "run-top",
                "runtime_control": "top-control",
                "runtime_side_effect": "top-side-effect",
                "status": "top-status",
                "job": {"id": "job-nested"},
                "run": {"id": "run-nested"},
                "runtime": {
                    "control": "nested-control",
                    "side_effect": "nested-side-effect",
                    "status": "nested-status",
                },
            }
        )
    )

    assert metadata == {
        "job_id": "job-top",
        "run_id": "run-top",
        "runtime_control": "top-control",
        "runtime_side_effect": "top-side-effect",
        "runtime_status": "top-status",
    }
