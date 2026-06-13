from __future__ import annotations

from typing import Any


def execution_package_payload(workspace: dict[str, Any]) -> dict[str, Any]:
    automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
    manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
    bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
    package_manifest = bundle.get("package_manifest") if isinstance(bundle.get("package_manifest"), dict) else {}
    resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
    scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
    selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
    backfill = automation.get("evidence_backfill") if isinstance(automation.get("evidence_backfill"), dict) else {}
    backfill_items = backfill.get("items") if isinstance(backfill.get("items"), list) else []
    readiness = automation.get("execution_readiness") if isinstance(automation.get("execution_readiness"), dict) else {}
    command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
    return {
        "status": str(bundle.get("status") or manifest.get("status") or "draft").strip(),
        "ready_to_execute": bool(bundle.get("ready_to_execute")),
        "next_action": bundle.get("next_action") if isinstance(bundle.get("next_action"), dict) else {},
        "target": bundle.get("target") if isinstance(bundle.get("target"), dict) else {},
        "commands": package_manifest.get("commands") if isinstance(package_manifest.get("commands"), dict) else {},
        "paths": package_manifest.get("paths") if isinstance(package_manifest.get("paths"), dict) else {},
        "dataset_discovery": package_manifest.get("dataset_discovery") if isinstance(package_manifest.get("dataset_discovery"), dict) else {},
        "scheduler": {
            "status": str(scheduler.get("status") or "").strip(),
            "mode": str(scheduler.get("mode") or "").strip(),
            "policy": str(scheduler.get("policy") or "").strip(),
            "summary": str(scheduler.get("summary") or "").strip(),
            "selected": selected,
            "candidate_count": int(scheduler.get("candidate_count") or 0),
            "ready_count": int(scheduler.get("ready_count") or 0),
        },
        "missing": bundle.get("missing") if isinstance(bundle.get("missing"), list) else [],
        "backfill": {
            "status": str(backfill.get("status") or "").strip(),
            "summary": str(backfill.get("summary") or "").strip(),
            "ready_count": int(backfill.get("ready_count") or 0),
            "items": [
                {
                    "node_kind": str(item.get("node_kind") or "").strip(),
                    "field": str(item.get("field") or "").strip(),
                    "label": str(item.get("label") or "").strip(),
                    "value": str(item.get("value") or "").strip(),
                    "status": str(item.get("status") or "").strip(),
                }
                for item in backfill_items[:12]
                if isinstance(item, dict)
            ],
        },
        "readiness": {
            "status": str(readiness.get("status") or "").strip(),
            "summary": str(readiness.get("summary") or "").strip(),
            "gate": readiness.get("gate") if isinstance(readiness.get("gate"), dict) else {},
        },
        "script": {
            "shell": str(command_script.get("shell") or "bash").strip(),
            "status": str(command_script.get("status") or "").strip(),
            "ready": bool(command_script.get("ready")),
            "summary": str(command_script.get("summary") or "").strip(),
            "text": str(command_script.get("text") or "")[:4000],
        },
    }


def workspace_artifacts(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for node in workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        runtime = node.get("runtime") if isinstance(node.get("runtime"), dict) else {}
        node_artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), list) else []
        if not node_artifacts and isinstance(node.get("artifacts"), list):
            node_artifacts = node.get("artifacts")
        for artifact in node_artifacts:
            if not isinstance(artifact, dict):
                continue
            artifacts.append(
                {
                    **artifact,
                    "node_id": str(node.get("id") or "").strip(),
                    "node_kind": str(node.get("kind") or "").strip(),
                    "source": "node.runtime",
                }
            )
    automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
    context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
    outputs = context.get("outputs") if isinstance(context.get("outputs"), dict) else {}
    for key, value in outputs.items():
        if not isinstance(value, dict):
            continue
        artifacts.append(
            {
                "label": str(value.get("label") or key).strip(),
                "path": str(value.get("path") or "").strip(),
                "summary": str(value.get("summary") or "").strip(),
                "output_key": str(key).strip(),
                "node_id": str(value.get("node_id") or "").strip(),
                "node_kind": str(value.get("node_kind") or "").strip(),
                "source": "context.outputs",
            }
        )
    return artifacts
