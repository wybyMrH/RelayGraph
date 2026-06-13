from __future__ import annotations

from ._deps import *  # noqa: F403

class MonitoringMixin:
    def reload_config(self) -> None:
        config = load_config(self.config_path)
        with self.lock:
            self.config = config
            self.servers = config.servers


    def refresh_status(self) -> None:
        self.reload_config()
        with self.lock:
            servers = list(self.servers)
            config = self.config
            previous_statuses = copy.deepcopy(self.statuses)
        statuses = collect_all(servers, config, previous_statuses=previous_statuses)
        refreshed_at = time.time()
        with self.lock:
            self.statuses = statuses
            self.last_refresh = refreshed_at
            self.last_refreshed_at = iso_at(refreshed_at)


    def refresh_server_status(self, server_id: str) -> dict[str, Any]:
        server_id = str(server_id or "").strip()
        if not server_id:
            raise ValueError("server_id is required")
        self.reload_config()
        with self.lock:
            server = self.server_by_id(server_id)
            config = self.config
        if not server:
            raise ValueError("server not found")
        status = collect_server(server, config)
        refreshed_at = time.time()
        with self.lock:
            existing = [item for item in self.statuses if str(item.get("id") or "") != server_id]
            order = {server_config.id: index for index, server_config in enumerate(self.servers)}
            existing.append(status)
            existing.sort(key=lambda item: order.get(str(item.get("id") or ""), 9999))
            self.statuses = existing
            self.last_refresh = refreshed_at
            self.last_refreshed_at = iso_at(refreshed_at)
        return status


    def workspace_public_payload(self, workspace: dict[str, Any]) -> dict[str, Any]:
        jobs = getattr(self, "jobs", [])
        payload = apply_workspace_job_runtime(workspace, jobs)
        payload["runs"] = workspace_execution_runs_public(workspace.get("runs"), jobs)
        payload["execution"] = derive_workspace_execution_state(payload, jobs)
        automation = derive_workspace_automation_state(
            payload,
            payload["execution"],
            getattr(self, "statuses", []),
            jobs=jobs,
        )
        payload["automation"] = attach_workspace_cockpit(payload, payload["execution"], automation, jobs=jobs)
        return payload


    def workspace_cockpit_payload(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            public = self.workspace_public_payload(workspace)
        return {
            "workspace_id": workspace_id,
            "cockpit": public.get("automation", {}).get("cockpit") if isinstance(public.get("automation"), dict) else {},
            "execution": public.get("execution"),
            "automation": public.get("automation"),
        }


    def workflow_template_public_payload(self, template: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(template)
        snapshot = build_template_snapshot(payload, self.agent_definitions, self.tool_definitions)
        payload["agent_ids"] = [str(item.get("id") or "").strip() for item in snapshot.get("agents", []) if str(item.get("id") or "").strip()]
        payload["tool_ids"] = [str(item.get("id") or "").strip() for item in snapshot.get("tools", []) if str(item.get("id") or "").strip()]
        payload["node_count"] = len(payload.get("nodes")) if isinstance(payload.get("nodes"), list) else 0
        payload["agent_count"] = len(payload["agent_ids"])
        payload["tool_count"] = len(payload["tool_ids"])
        return payload


    def status_payload(self) -> dict[str, Any]:
        with self.lock:
            workspaces = [
                self.workspace_public_payload(item)
                for item in sorted(self.workspaces, key=workspace_sort_key, reverse=True)
            ]
            workflow_templates = [
                self.workflow_template_public_payload(item)
                for item in sorted(getattr(self, "workflow_templates", []), key=workflow_template_sort_key, reverse=True)
            ]
            return {
                "config": self.public_config(),
                "refreshed_at": self.last_refreshed_at,
                "status_age_seconds": round(max(time.time() - self.last_refresh, 0), 1),
                "servers": self.statuses,
                "jobs": self.jobs,
                "workspaces": workspaces,
                "workflow_templates": workflow_templates,
                "agent_definitions": copy.deepcopy(getattr(self, "agent_definitions", [])),
                "tool_definitions": copy.deepcopy(getattr(self, "tool_definitions", [])),
            }
