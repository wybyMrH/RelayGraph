from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepResult:
    status: str = "skipped"
    executor: str = "none"
    output_key: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    job_id: str = ""
    agent_execution_id: str = ""
    detail: str = ""
    skipped: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "executor": self.executor,
            "output_key": self.output_key,
            "artifacts": list(self.artifacts),
            "detail": self.detail,
            "skipped": self.skipped,
        }
        if self.job_id:
            payload["job_id"] = self.job_id
        if self.agent_execution_id:
            payload["agent_execution_id"] = self.agent_execution_id
        if self.reason:
            payload["reason"] = self.reason
        return payload


@dataclass(slots=True)
class ExecutionRunContext:
    workspace_id: str
    run_id: str = ""
    kind: str = "node"
    trigger: str = "user"
    outputs: dict[str, Any] = field(default_factory=dict)
    step_index: int = 0

    def with_output(self, key: str, value: Any) -> None:
        normalized = str(key or "").strip()
        if not normalized:
            return
        self.outputs[normalized] = value
