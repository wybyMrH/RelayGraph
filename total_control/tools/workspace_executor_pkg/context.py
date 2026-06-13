from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .discovery import execute_dataset_find, execute_dir_scan
from .helpers import split_values
from .payloads import execution_package_payload, workspace_artifacts


@dataclass
class WorkspaceToolContext:
    workspace: dict[str, Any]
    statuses: list[dict[str, Any]] = field(default_factory=list)
    jobs: list[dict[str, Any]] = field(default_factory=list)
    runtime: Any = None

    def node_config(self, kind: str) -> dict[str, Any]:
        for node in self.workspace.get("nodes") if isinstance(self.workspace.get("nodes"), list) else []:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == kind:
                config = node.get("config") if isinstance(node.get("config"), dict) else {}
                return config
        return {}

    def source_payload(self) -> dict[str, Any]:
        source = self.workspace.get("source") if isinstance(self.workspace.get("source"), dict) else {}
        inputs = self.workspace.get("inputs") if isinstance(self.workspace.get("inputs"), dict) else {}
        return {
            "goal_text": str(inputs.get("goal_text") or self.workspace.get("brief") or source.get("idea_text") or "").strip(),
            "repo_urls": split_values(inputs.get("repo_urls") or source.get("repo_url")),
            "paper_urls": split_values(inputs.get("paper_urls") or source.get("paper_url")),
            "references": split_values(inputs.get("references")),
            "context_blocks": split_values(inputs.get("context_blocks")),
            "workspace_dir": str(self.workspace.get("workspace_dir") or "").strip(),
        }

    def configured_run_command(self) -> str:
        return str(self.node_config("run.command").get("run_command") or "").strip()

    def workflow_nodes(self) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for index, node in enumerate(self.workspace.get("nodes") if isinstance(self.workspace.get("nodes"), list) else []):
            if not isinstance(node, dict):
                continue
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            nodes.append(
                {
                    "order": index + 1,
                    "id": str(node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or "").strip(),
                    "agent_id": str(handler.get("agent_id") or "").strip(),
                    "input_mapping": node.get("input_mapping") if isinstance(node.get("input_mapping"), dict) else {},
                    "output_key": str(node.get("output_key") or "").strip(),
                    "configured_fields": sorted(key for key, value in config.items() if str(value or "").strip())[:8],
                }
            )
        return nodes

    def gpu_candidates(self, min_free_mib: int = 0, server_id: str = "") -> list[dict[str, Any]]:
        def number_value(value: Any, default: int = 0) -> int:
            if value in (None, ""):
                return default
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return default

        candidates: list[dict[str, Any]] = []
        for status in self.statuses:
            sid = str(status.get("id") or "").strip()
            if server_id and sid != server_id:
                continue
            if status.get("online") is False:
                continue
            for gpu in status.get("gpus") if isinstance(status.get("gpus"), list) else []:
                if not isinstance(gpu, dict):
                    continue
                free_mib = number_value(gpu.get("memory_free_mib"), 0)
                util = number_value(gpu.get("gpu_util"), 100)
                state = str(gpu.get("state") or "").strip() or ("idle" if util <= 10 else "busy")
                candidates.append(
                    {
                        "server_id": sid,
                        "server_name": str(status.get("name") or sid).strip(),
                        "gpu_index": gpu.get("index"),
                        "name": str(gpu.get("name") or "").strip(),
                        "memory_free_mib": free_mib,
                        "memory_total_mib": number_value(gpu.get("memory_total_mib"), 0),
                        "gpu_util": util,
                        "state": state,
                        "eligible": state == "idle" and free_mib >= min_free_mib,
                        "collected_at": str(status.get("collected_at") or "").strip(),
                    }
                )
        candidates.sort(key=lambda item: (bool(item["eligible"]), item["memory_free_mib"], -item["gpu_util"]), reverse=True)
        return candidates

    def automation_selected_gpu(self) -> dict[str, Any]:
        automation = self.workspace.get("automation") if isinstance(self.workspace.get("automation"), dict) else {}
        resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
        scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
        selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
        return selected

    def execution_package_payload(self) -> dict[str, Any]:
        return execution_package_payload(self.workspace)

    def workspace_artifacts(self) -> list[dict[str, Any]]:
        return workspace_artifacts(self.workspace)

    def job_workspace_id(self, job: dict[str, Any]) -> str:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        return str(metadata.get("workspace_id") or job.get("workspace_id") or "").strip()

    def execute_dataset_find(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return execute_dataset_find(self, arguments)

    def execute_dir_scan(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return execute_dir_scan(self, arguments)

    def runtime_callback(self, name: str) -> Callable[..., dict[str, Any]] | None:
        runtime = self.runtime
        if isinstance(runtime, dict):
            callback = runtime.get(name)
        else:
            callback = getattr(runtime, name, None) if runtime is not None else None
        return callback if callable(callback) else None

    def submit_controlled_job(self, tool_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        callback = self.runtime_callback("submit_job")
        if not callback:
            return {}
        return callback(tool_id, arguments if isinstance(arguments, dict) else {}, self)

    def bind_gpu_allocation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        callback = self.runtime_callback("bind_gpu")
        if not callback:
            return {}
        return callback(arguments if isinstance(arguments, dict) else {}, self)

    def execute(self, tool_id: str, arguments: dict[str, Any]) -> str:
        from .dispatcher import execute_tool

        return execute_tool(self, tool_id, arguments)
