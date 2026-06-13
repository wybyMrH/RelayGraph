"""Workspace state — defaults operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class DefaultsMixin:
    def apply_workspace_automation_defaults(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        force = workspace_payload_bool(requested_payload, "force", False)
        apply_defaults = workspace_payload_bool(requested_payload, "apply_defaults", True)
        apply_evidence = workspace_payload_bool(requested_payload, "apply_evidence", True)
        scheduler_candidate = requested_payload.get("scheduler_candidate")
        if not isinstance(scheduler_candidate, dict):
            scheduler_candidate = None
        backfill_item = requested_payload.get("backfill_item")
        if not isinstance(backfill_item, dict):
            backfill_item = None
        evidence_applied: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            statuses_snapshot = copy.deepcopy(getattr(self, "statuses", []))
            jobs_snapshot = copy.deepcopy(getattr(self, "jobs", []))
            if apply_defaults:
                updated, applied = apply_workspace_automation_defaults_to_payload(
                    current,
                    statuses_snapshot,
                    force=force,
                    scheduler_candidate=scheduler_candidate,
                )
            else:
                updated, applied = copy.deepcopy(current), []
            if backfill_item:
                updated, evidence_applied = apply_workspace_evidence_backfill_item_to_payload(
                    updated,
                    jobs_snapshot,
                    backfill_item,
                    statuses=statuses_snapshot,
                    force=force,
                )
                applied.extend(evidence_applied)
            elif apply_evidence:
                updated, evidence_applied = apply_workspace_discovery_evidence_to_payload(
                    updated,
                    jobs_snapshot,
                    force=force,
                )
                applied.extend(evidence_applied)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
        self.save_workspaces()
        with self.lock:
            return {
                "workspace": self.workspace_public_payload(updated),
                "applied": applied,
                "evidence_applied": evidence_applied,
            }
