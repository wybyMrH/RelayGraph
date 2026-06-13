from __future__ import annotations

from ._deps import *  # noqa: F403


def workspace_execution_node_by_kind(execution: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(
        (
            item for item in (execution.get("nodes") if isinstance(execution.get("nodes"), list) else [])
            if isinstance(item, dict) and str(item.get("kind") or "").strip() == kind
        ),
        {},
    )

def workspace_automation_check(
    check_id: str,
    label: str,
    status: str,
    title: str,
    detail: str,
    action: str,
    *,
    node_kind: str = "",
) -> dict[str, Any]:
    normalized = status if status in {"ready", "warning", "blocked", "running", "done", "failed", "draft"} else "warning"
    return {
        "id": check_id,
        "label": label,
        "status": normalized,
        "title": title,
        "detail": detail,
        "action": action,
        "node_kind": node_kind,
    }

def workspace_enrich_readiness_issue(workspace: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    issue = copy.deepcopy(item)
    node_kind = str(issue.get("node_kind") or issue.get("kind") or "").strip()
    node = workspace_node_by_kind(workspace, node_kind) if node_kind else {}
    if node:
        issue.setdefault("node_id", str(node.get("id") or "").strip())
        issue.setdefault("node_title", str(node.get("title") or node_kind).strip())
        issue.setdefault("node_kind", node_kind)
    if node_kind and not issue.get("field"):
        issue["field"] = WORKSPACE_ISSUE_FIELD_BY_KIND.get(node_kind, "")
    if not issue.get("fix_action"):
        issue["fix_action"] = str(issue.get("action") or issue.get("detail") or "定位节点后补齐配置。").strip()
    if not issue.get("origin"):
        issue["origin"] = str(issue.get("id") or issue.get("type") or "readiness").strip()
    return issue

def workspace_status_priority(status: str) -> int:
    return {
        "failed": 0,
        "blocked": 1,
        "warning": 2,
        "draft": 3,
        "running": 4,
        "ready": 5,
        "done": 6,
    }.get(status, 2)
