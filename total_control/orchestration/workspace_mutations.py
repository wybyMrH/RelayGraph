from __future__ import annotations

from typing import Any

WORKFLOW_EDIT_ALLOWED_CONFIG_KEYS = frozenset(
    {
        "focus_paths",
        "entry_script",
        "manifest_paths",
        "setup_command",
        "env_name",
        "env_manager",
        "python_version",
        "data_roots",
        "dataset_hints",
        "query",
        "run_command",
        "server_id",
        "gpu_index",
        "workspace_dir",
        "repo_url",
        "questions",
        "goal",
        "notes",
    }
)


def find_workspace_node(
    workspace: dict[str, Any],
    *,
    node_id: str = "",
    node_kind: str = "",
) -> dict[str, Any] | None:
    for node in workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        if node_id and str(node.get("id") or "").strip() == node_id:
            return node
        if node_kind and str(node.get("kind") or "").strip() == node_kind:
            return node
    return None


def apply_workflow_edit(
    workspace: dict[str, Any],
    *,
    node_id: str = "",
    node_kind: str = "",
    config_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node = find_workspace_node(workspace, node_id=node_id, node_kind=node_kind)
    if not node:
        raise ValueError("target node not found for workflow.edit")
    patch = config_patch if isinstance(config_patch, dict) else {}
    if not patch:
        raise ValueError("workflow.edit requires a config patch")
    rejected = [key for key in patch if key not in WORKFLOW_EDIT_ALLOWED_CONFIG_KEYS]
    if rejected:
        raise ValueError(f"workflow.edit rejected keys: {', '.join(rejected)}")
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    updated = {**config}
    for key, value in patch.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    node["config"] = updated
    node["updated_at"] = workspace.get("updated_at") or ""
    return {
        "node_id": str(node.get("id") or "").strip(),
        "node_kind": str(node.get("kind") or "").strip(),
        "config": updated,
        "applied_keys": sorted(patch.keys()),
    }


def apply_artifact_write(
    workspace: dict[str, Any],
    *,
    node_id: str = "",
    node_kind: str = "",
    label: str = "",
    path: str = "",
    content: str = "",
    output_key: str = "",
    artifact_type: str = "note",
) -> dict[str, Any]:
    node = find_workspace_node(workspace, node_id=node_id, node_kind=node_kind)
    if not node:
        raise ValueError("target node not found for artifact.write")
    artifact_label = str(label or path or "artifact").strip() or "artifact"
    artifact_path = str(path or "").strip()
    artifact_content = str(content or "").strip()
    if not artifact_path and not artifact_content:
        raise ValueError("artifact.write requires path and/or content")
    entry = {
        "label": artifact_label,
        "path": artifact_path,
        "type": str(artifact_type or "note").strip() or "note",
        "summary": artifact_content[:240] if artifact_content else "",
    }
    if artifact_content and len(artifact_content) <= 4000:
        entry["content"] = artifact_content
    runtime = node.get("runtime") if isinstance(node.get("runtime"), dict) else {}
    artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), list) else []
    if not artifacts and isinstance(node.get("artifacts"), list):
        artifacts = [item for item in node.get("artifacts") if isinstance(item, dict)]
    artifacts.append(entry)
    runtime["artifacts"] = artifacts
    node["runtime"] = runtime
    node["artifacts"] = artifacts

    normalized_output_key = str(output_key or "").strip()
    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
    if not normalized_output_key:
        normalized_output_key = str(handler.get("output_key") or node.get("output_key") or "").strip()
    if normalized_output_key:
        automation = workspace.setdefault("automation", {})
        if not isinstance(automation, dict):
            automation = {}
            workspace["automation"] = automation
        context = automation.setdefault("execution_context", {})
        if not isinstance(context, dict):
            context = {}
            automation["execution_context"] = context
        outputs = context.setdefault("outputs", {})
        if not isinstance(outputs, dict):
            outputs = {}
            context["outputs"] = outputs
        outputs[normalized_output_key] = {
            "label": artifact_label,
            "path": artifact_path,
            "summary": entry.get("summary") or artifact_label,
            "node_id": str(node.get("id") or "").strip(),
            "node_kind": str(node.get("kind") or "").strip(),
        }
    return {
        "node_id": str(node.get("id") or "").strip(),
        "node_kind": str(node.get("kind") or "").strip(),
        "artifact": entry,
        "output_key": normalized_output_key,
    }
