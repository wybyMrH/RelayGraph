"""Execution run delivery closure helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .run_artifacts import normalize_workspace_run_step_artifacts


def _workspace_delivery_path_candidates(path_text: str, workspace_dir: str = "") -> set[str]:
    text = str(path_text or "").strip()
    if not text:
        return set()
    root = os.path.normpath(os.path.expanduser(str(workspace_dir or "").strip())) if str(workspace_dir or "").strip() else ""
    values: set[str] = set()

    def add(value: str) -> None:
        candidate = str(value or "").strip()
        if not candidate:
            return
        trimmed = candidate.rstrip("/\\") or candidate
        normalized = os.path.normpath(os.path.expanduser(trimmed))
        for item in (candidate, trimmed, normalized):
            item_text = str(item or "").strip()
            if item_text and item_text != ".":
                values.add(item_text)

    add(text)
    normalized_text = os.path.normpath(os.path.expanduser(text.rstrip("/\\") or text))
    if root:
        if os.path.isabs(normalized_text):
            try:
                relative = os.path.relpath(normalized_text, root)
            except ValueError:
                relative = ""
            if relative and relative != "." and not relative.startswith(".."):
                add(relative)
                add("./" + relative)
        else:
            add(os.path.join(root, normalized_text))
    return values


def workspace_execution_run_delivery_closure(
    package_snapshot: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = package_snapshot.get("package_manifest") if isinstance(package_snapshot.get("package_manifest"), dict) else {}
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    commands = manifest.get("commands") if isinstance(manifest.get("commands"), dict) else {}
    target = package_snapshot.get("target") if isinstance(package_snapshot.get("target"), dict) else {}
    if not target and isinstance(manifest.get("target"), dict):
        target = manifest.get("target") or {}
    workspace_dir = str(target.get("workspace_dir") or "").strip()
    expected_artifact_paths = [
        str(item or "").strip()
        for item in (paths.get("artifact_paths") if isinstance(paths.get("artifact_paths"), list) else [])
        if str(item or "").strip()
    ][:12]
    expected_metric_paths = [
        str(item or "").strip()
        for item in (paths.get("metric_paths") if isinstance(paths.get("metric_paths"), list) else [])
        if str(item or "").strip()
    ][:12]
    observed_artifacts: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    report_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_kind = str(step.get("node_kind") or "").strip()
        if step_kind == "eval.report":
            report_steps.append(
                {
                    "node_id": str(step.get("node_id") or "").strip(),
                    "status": str(step.get("status") or "").strip(),
                    "job_id": str(step.get("job_id") or "").strip(),
                    "agent_execution_id": str(step.get("agent_execution_id") or "").strip(),
                }
            )
        for artifact in step.get("artifacts") if isinstance(step.get("artifacts"), list) else []:
            if isinstance(artifact, dict):
                observed_artifacts.append(
                    {
                        **artifact,
                        "node_id": str(artifact.get("node_id") or step.get("node_id") or "").strip(),
                        "node_kind": str(artifact.get("node_kind") or step_kind).strip(),
                    }
                )
        resources = step.get("resources") if isinstance(step.get("resources"), dict) else {}
        step_metrics = resources.get("metrics") if isinstance(resources.get("metrics"), dict) else {}
        for key, value in step_metrics.items():
            metrics[str(key)] = value
    observed_artifacts = normalize_workspace_run_step_artifacts(observed_artifacts)
    report_artifacts = [
        item for item in observed_artifacts
        if str(item.get("type") or "").strip() == "report"
        or str(item.get("node_kind") or "").strip() == "eval.report"
        or str(item.get("label") or "").strip().lower() in {"report", "eval_report", "evaluation_report"}
    ][:6]
    def artifact_is_observed(item: dict[str, Any]) -> bool:
        return bool(item.get("exists")) or str(item.get("status") or "") in {"found", "ready", "done"}

    found_count = sum(1 for item in observed_artifacts if artifact_is_observed(item))
    def expected_path_observed(path: str) -> bool:
        expected_candidates = _workspace_delivery_path_candidates(path, workspace_dir)
        return any(
            artifact_is_observed(item)
            and bool(
                expected_candidates
                & (
                    _workspace_delivery_path_candidates(str(item.get("path") or ""), workspace_dir)
                    | _workspace_delivery_path_candidates(str(item.get("resolved_path") or ""), workspace_dir)
                )
            )
            for item in observed_artifacts
        )

    missing_artifact_paths = [
        path for path in expected_artifact_paths
        if path and not expected_path_observed(path)
    ]
    missing_metric_paths = [
        path for path in expected_metric_paths
        if path and not expected_path_observed(path)
    ]
    missing_expected = [*missing_artifact_paths, *missing_metric_paths]
    report_command = str(commands.get("report_command") or "").strip()
    failed_report_steps = [
        item for item in report_steps
        if str(item.get("status") or "").strip() in {"failed", "blocked", "stopped"}
    ]
    completed_report_steps = [
        item for item in report_steps
        if str(item.get("status") or "").strip() == "done"
    ]
    report_ready = bool(report_artifacts or (metrics and completed_report_steps))
    if failed_report_steps:
        status = "failed"
    elif missing_expected:
        status = "warning"
    elif metrics and (found_count or completed_report_steps or report_artifacts):
        status = "done"
    elif found_count or metrics or report_artifacts or completed_report_steps:
        status = "ready"
    elif expected_artifact_paths or expected_metric_paths or report_command:
        status = "warning"
    else:
        status = "draft"
    if failed_report_steps:
        report_status = "failed"
    elif report_ready:
        report_status = "ready"
    elif report_command or report_steps or metrics:
        report_status = "warning"
    else:
        report_status = "draft"
    return {
        "status": status,
        "expected_artifact_paths": expected_artifact_paths,
        "expected_metric_paths": expected_metric_paths,
        "observed_artifacts": observed_artifacts[:24],
        "observed_count": len(observed_artifacts),
        "found_count": found_count,
        "missing_expected": missing_expected[:12],
        "missing_artifact_count": len(missing_artifact_paths),
        "missing_metric_count": len(missing_metric_paths),
        "metrics": metrics,
        "report": {
            "status": report_status,
            "report_command": report_command,
            "steps": report_steps[:6],
            "artifacts": copy.deepcopy(report_artifacts),
            "artifact_count": len(report_artifacts),
            "failed_steps": failed_report_steps[:6],
            "failed_step_count": len(failed_report_steps),
        },
    }
