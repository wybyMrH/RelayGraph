"""Cockpit — helpers helpers."""

from __future__ import annotations

from ._deps import *  # noqa: F403

def workspace_jobs_for_workspace(
    workspace_id: str,
    jobs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return []
    return [
        job for job in (jobs or [])
        if isinstance(job, dict) and workspace_job_binding(job)[0] == workspace_id
    ]

def workspace_node_config_ready_status(
    workspace: dict[str, Any],
    node: dict[str, Any],
) -> str:
    kind = str(node.get("kind") or "").strip()
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
    if kind in {"source.repo", "repo.clone"}:
        repo_url = str(config.get("repo_url") or (workspace.get("source") or {}).get("repo_url") or "").strip()
        return "ready" if repo_url else "blocked"
    if kind in {"source.paper"}:
        paper_url = str(config.get("paper_url") or (workspace.get("source") or {}).get("paper_url") or "").strip()
        return "ready" if paper_url else "blocked"
    if kind in {"source.idea"}:
        idea = str(config.get("idea_text") or workspace.get("brief") or "").strip()
        return "ready" if idea else "draft"
    if kind in {"path.resolve", "repo.inspect", "dataset.find", "env.infer", "env.prepare", "artifact.collect"}:
        return "ready" if workspace_dir else "blocked"
    if kind == "gpu.allocate":
        policy = str(config.get("gpu_policy") or "").strip()
        return "ready" if policy else "warning"
    if kind == "run.command":
        run_command = str(config.get("run_command") or "").strip()
        return "ready" if run_command and workspace_dir else "blocked" if not run_command else "warning"
    if kind in WORKSPACE_EXECUTABLE_NODE_KINDS:
        return "ready" if workspace_dir else "warning"
    return "draft"

def append_unique_text(target: list[str], value: Any, *, limit: int = 12) -> None:
    text = compact_workspace_command(str(value or "").strip(), limit=180)
    if not text or text in target or len(target) >= limit:
        return
    target.append(text)

def workspace_payload_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default) if isinstance(payload, dict) else default
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)

def workspace_backfill_request_matches(item: dict[str, Any], requested: dict[str, Any]) -> bool:
    node_kind = str(requested.get("node_kind") or requested.get("nodeKind") or "").strip()
    field = str(requested.get("field") or "").strip()
    if node_kind and str(item.get("node_kind") or "").strip() != node_kind:
        return False
    if field and str(item.get("field") or "").strip() != field:
        return False
    label = str(requested.get("label") or "").strip()
    if label and str(item.get("label") or "").strip() != label:
        return False
    value = str(requested.get("value") or "").strip()
    if value and str(item.get("value") or "").strip() != value:
        return False
    return bool(node_kind and field)

def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))
