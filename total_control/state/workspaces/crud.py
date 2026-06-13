"""Workspace state — crud operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class CrudMixin:
    def workspace_by_id(self, workspace_id: str) -> dict[str, Any] | None:
        return next((item for item in self.workspaces if str(item.get("id")) == str(workspace_id)), None)


    def list_workspaces(self) -> dict[str, Any]:
        with self.lock:
            items = [
                self.workspace_public_payload(item)
                for item in sorted(self.workspaces, key=workspace_sort_key, reverse=True)
            ]
        return {"workspaces": items}


    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        requested_payload = payload if isinstance(payload, dict) else {}
        template_id = str(requested_payload.get("template_id") or "").strip()
        has_template_inputs = "inputs" in requested_payload or any(
            key in requested_payload
            for key in ("goal_text", "repo_urls", "paper_urls", "context_blocks", "source_mode")
        )
        workflow_templates = getattr(self, "workflow_templates", [])
        if template_id or (has_template_inputs and workflow_templates):
            with self.lock:
                template = self.workflow_template_by_id(template_id) if template_id else None
                if not template:
                    template = workflow_templates[0] if workflow_templates else None
                if not template:
                    raise ValueError("workflow template not found")
                workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=template,
                    agent_definitions=getattr(self, "agent_definitions", workspace_default_agents()),
                    tool_definitions=getattr(self, "tool_definitions", workspace_default_tools()),
                )
        else:
            workspace = normalize_workspace_payload(requested_payload)
        with self.lock:
            self.workspaces.insert(0, workspace)
        self.save_workspaces()
        with self.lock:
            return self.workspace_public_payload(workspace)


    def update_workspace(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            requested_payload = payload if isinstance(payload, dict) else {}
            merged = dict(current)
            merged.update(requested_payload)
            if str(current.get("template_id") or "").strip() or isinstance(current.get("template_snapshot"), dict):
                updated = normalize_workspace_payload(merged, existing=current)
                updated["template_id"] = str(merged.get("template_id") or current.get("template_id") or "").strip()
                updated["template_name"] = str(merged.get("template_name") or current.get("template_name") or "").strip()
                updated["template_snapshot"] = copy.deepcopy(
                    merged.get("template_snapshot")
                    if isinstance(merged.get("template_snapshot"), dict)
                    else current.get("template_snapshot")
                    if isinstance(current.get("template_snapshot"), dict)
                    else {}
                )
                updated["inputs"] = normalize_workspace_inputs(
                    merged.get("inputs") if isinstance(merged.get("inputs"), dict) else merged,
                    existing=current.get("inputs"),
                )
                updated["execution"] = copy.deepcopy(
                    merged.get("execution")
                    if isinstance(merged.get("execution"), dict)
                    else current.get("execution")
                    if isinstance(current.get("execution"), dict)
                    else {}
                )
            else:
                updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
        self.save_workspaces()
        with self.lock:
            return self.workspace_public_payload(updated)


    def delete_workspace(self, workspace_id: str) -> None:
        """Delete a workspace by ID."""
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            del self.workspaces[index]
        self.save_workspaces()
