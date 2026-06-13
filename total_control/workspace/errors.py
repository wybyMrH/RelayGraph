from __future__ import annotations

from typing import Any


class WorkspaceWorkflowReadinessError(ValueError):
    def __init__(
        self,
        message: str,
        blocked_checks: list[dict[str, Any]] | None = None,
        *,
        workspace: dict[str, Any] | None = None,
        applied: list[dict[str, Any]] | None = None,
        evidence_applied: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.blocked_checks = blocked_checks or []
        self.workspace = workspace
        self.applied = applied or []
        self.evidence_applied = evidence_applied or []
