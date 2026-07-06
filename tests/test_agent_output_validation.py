"""Phase 3 #2 — structured Agent output validation.

Guards the contract that structured Agent nodes (repo.inspect, env.infer,
dataset.find, eval.report) must produce parseable JSON, and that malformed
output is surfaced (status + error) instead of silently accepted as text.
"""

from __future__ import annotations

from total_control.orchestration.input_mapping import (
    apply_final_answer_output,
    expected_output_format,
    validate_agent_output,
)
from total_control.orchestration.types import StepResult
from total_control.workspace.execution.runs import (
    normalize_workspace_run_step,
    workspace_run_step_from_agent,
)


def _workspace() -> dict:
    return {
        "nodes": [
            {"id": "repo-inspect-1", "kind": "repo.inspect", "config": {}},
        ],
    }


# --- validate_agent_output -------------------------------------------------


def test_validate_accepts_valid_json():
    result = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer='{"entry": "main.py", "deps": ["requirements.txt"]}',
    )
    assert result["status"] == "ok"
    assert result["parsed"] == {"entry": "main.py", "deps": ["requirements.txt"]}
    assert result["errors"] == []


def test_validate_accepts_fenced_json():
    result = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer='```json\n{"entry": "main.py"}\n```',
    )
    assert result["status"] == "ok"
    assert result["parsed"] == {"entry": "main.py"}


def test_validate_flags_prose_when_json_required():
    result = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer="该仓库入口为 main.py，依赖见 requirements.txt",
    )
    assert result["status"] == "warning"
    assert result["parsed"] is None
    assert result["errors"], "expected a validation error explaining the parse failure"


def test_validate_flags_malformed_json():
    result = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer='{"entry": "main.py"',  # truncated
    )
    assert result["status"] == "warning"
    assert result["parsed"] is None
    assert result["errors"]


def test_validate_text_format_is_ok_without_parse():
    result = validate_agent_output(
        output_key="research_brief",
        output_format="",
        final_answer="自由格式的检索结论",
    )
    assert result["status"] == "ok"
    assert result["parsed"] is None


def test_validate_empty_answer_is_failed():
    result = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer="",
    )
    assert result["status"] == "failed"
    assert result["parsed"] is None


def test_validate_missing_output_key_is_failed():
    result = validate_agent_output(
        output_key="",
        output_format="json",
        final_answer="{}",
    )
    assert result["status"] == "failed"


# --- apply_final_answer_output --------------------------------------------


def test_apply_stores_json_when_valid_and_does_not_stamp_validation():
    workspace = _workspace()
    node = workspace["nodes"][0]
    validation = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer='{"entry": "main.py"}',
    )
    result = apply_final_answer_output(
        workspace,
        node,
        output_key="repo_profile",
        final_answer='{"entry": "main.py"}',
        output_format="json",
        validation=validation,
    )
    assert result is not None
    assert result["artifact"]["type"] == "json"
    assert result["artifact"]["path"].endswith("repo_profile.json")
    assert "validation" not in result  # status ok → no stamp


def test_apply_keeps_text_and_stamps_warning_when_malformed():
    workspace = _workspace()
    node = workspace["nodes"][0]
    validation = validate_agent_output(
        output_key="repo_profile",
        output_format="json",
        final_answer="not json at all",
    )
    result = apply_final_answer_output(
        workspace,
        node,
        output_key="repo_profile",
        final_answer="not json at all",
        output_format="json",
        validation=validation,
    )
    assert result is not None
    assert result["artifact"]["type"] == "note"
    assert result["artifact"]["path"].endswith("repo_profile.txt")
    assert result["validation"]["status"] == "warning"
    assert result["validation"]["errors"]


# --- expected_output_format -----------------------------------------------


def test_expected_format_prefers_handler_then_contract():
    from total_control.constants_pkg.workspace_contracts import WORKSPACE_NODE_IO_CONTRACTS

    contract = WORKSPACE_NODE_IO_CONTRACTS["repo.inspect"]
    assert expected_output_format({"handler": {}}, contract) == "json"
    assert expected_output_format({"handler": {"output_format": "text"}}, contract) == "text"


# --- run step persistence --------------------------------------------------


def test_run_step_carries_validation_from_step_result():
    node = {"id": "repo-inspect-1", "kind": "repo.inspect", "title": "仓库检查"}
    step = StepResult(
        status="completed",
        executor="agent",
        output_key="repo_profile",
        validation={"status": "warning", "expected_format": "json", "errors": ["解析失败"]},
    )
    normalized = workspace_run_step_from_agent(node, step, index=0)
    assert normalized["validation"]["status"] == "warning"
    assert normalized["validation"]["errors"] == ["解析失败"]


def test_normalize_run_step_round_trips_validation():
    step = workspace_run_step_from_agent(
        {"id": "n1", "kind": "env.infer"},
        StepResult(
            status="completed",
            executor="agent",
            output_key="env_requirements",
            validation={"status": "warning", "expected_format": "json", "errors": ["bad"]},
        ),
        index=2,
    )
    again = normalize_workspace_run_step(step, existing=step)
    assert again["validation"]["status"] == "warning"
    assert again["validation"]["expected_format"] == "json"


def test_normalize_run_step_drops_empty_validation():
    step = normalize_workspace_run_step({"executor": "job", "status": "done", "index": 0})
    assert step["validation"] == {}
