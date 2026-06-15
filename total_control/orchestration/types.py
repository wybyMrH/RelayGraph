from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepResult:
    status: str = "skipped"
    executor: str = "none"
    output_key: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    mapped_inputs: list[dict[str, str]] = field(default_factory=list)
    job_id: str = ""
    agent_execution_id: str = ""
    agent_steps: list[dict[str, Any]] = field(default_factory=list)
    detail: str = ""
    skipped: bool = False
    reason: str = ""
    validation: dict[str, Any] = field(default_factory=dict)
    timed_out: bool = False
    cancelled: bool = False
    agent_meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "executor": self.executor,
            "output_key": self.output_key,
            "artifacts": list(self.artifacts),
            "detail": self.detail,
            "skipped": self.skipped,
        }
        if self.mapped_inputs:
            payload["mapped_inputs"] = list(self.mapped_inputs)
        if self.job_id:
            payload["job_id"] = self.job_id
        if self.agent_execution_id:
            payload["agent_execution_id"] = self.agent_execution_id
        if self.agent_steps:
            payload["agent_steps"] = list(self.agent_steps)
        if self.reason:
            payload["reason"] = self.reason
        if self.validation:
            payload["validation"] = dict(self.validation)
        if self.timed_out:
            payload["timed_out"] = True
        if self.cancelled:
            payload["cancelled"] = True
        if self.agent_meta:
            payload["agent_meta"] = dict(self.agent_meta)
        return payload


@dataclass(slots=True)
class ExecutionRunContext:
    workspace_id: str
    run_id: str = ""
    kind: str = "node"
    trigger: str = "user"
    outputs: dict[str, Any] = field(default_factory=dict)
    previous_output: dict[str, Any] | None = None
    step_index: int = 0

    def with_output(self, key: str, value: Any) -> None:
        normalized = str(key or "").strip()
        if not normalized:
            return
        self.outputs[normalized] = value
