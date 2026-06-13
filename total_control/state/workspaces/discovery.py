"""Workspace state — discovery operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class DiscoveryMixin:
    def run_workspace_discovery(self, workspace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_payload = payload if isinstance(payload, dict) else {}
        apply_defaults = bool(requested_payload.get("apply_defaults", True))
        include_source_raw = requested_payload.get("include_source", requested_payload.get("bootstrap_source", True))
        include_source = (
            include_source_raw.strip().lower() not in {"0", "false", "no", "off"}
            if isinstance(include_source_raw, str)
            else bool(include_source_raw)
        )
        force = bool(requested_payload.get("force") or False)
        applied: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            workspace = copy.deepcopy(current)
            if apply_defaults:
                workspace, applied = apply_workspace_automation_defaults_to_payload(
                    workspace,
                    getattr(self, "statuses", []),
                    force=force,
                )
                index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                if index < 0:
                    raise ValueError("workspace not found")
                self.workspaces[index] = workspace
        if apply_defaults:
            self.save_workspaces()

        nodes: list[dict[str, Any]] = []
        source_bootstrap_queued = False
        workspace_nodes = [
            node for node in (workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else [])
            if isinstance(node, dict)
        ]
        clone_node = next((node for node in workspace_nodes if str(node.get("kind") or "").strip() == "repo.clone"), None)
        if clone_node and include_source:
            node = clone_node
            kind = "repo.clone"
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            source = workspace.get("source") if isinstance(workspace.get("source"), dict) else {}
            repo_url = str(config.get("repo_url") or source.get("repo_url") or "").strip()
            should_queue_clone = bool(repo_url and workspace_dir)
            if not should_queue_clone:
                skipped.append(
                    {
                        "node_id": str(node.get("id") or "").strip(),
                        "node_kind": kind,
                        "reason": "repo_url or workspace_dir missing",
                    }
                )
            else:
                target = Path(workspace_dir).expanduser()
                if target.exists():
                    if not target.is_dir():
                        should_queue_clone = False
                        skipped.append(
                            {
                                "node_id": str(node.get("id") or "").strip(),
                                "node_kind": kind,
                                "reason": "workspace_dir exists but is not a directory",
                            }
                        )
                    else:
                        try:
                            has_files = any(target.iterdir())
                        except OSError:
                            should_queue_clone = False
                            skipped.append(
                                {
                                    "node_id": str(node.get("id") or "").strip(),
                                    "node_kind": kind,
                                    "reason": "workspace_dir cannot be inspected",
                                }
                            )
                        else:
                            if has_files:
                                should_queue_clone = False
                if should_queue_clone:
                    nodes.append(node)
                    source_bootstrap_queued = True

        for node in workspace_nodes:
            kind = str(node.get("kind") or "").strip()
            if kind == "repo.clone" or kind not in WORKSPACE_DISCOVERY_NODE_KINDS:
                continue
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            workspace_dir = str(config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            if kind == "repo.inspect":
                target = Path(workspace_dir).expanduser() if workspace_dir else None
                if not workspace_dir:
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir missing",
                        }
                    )
                    continue
                if not source_bootstrap_queued and (not target or not target.exists()):
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir does not exist yet",
                        }
                    )
                    continue
                if target and target.exists() and not target.is_dir():
                    skipped.append(
                        {
                            "node_id": str(node.get("id") or "").strip(),
                            "node_kind": kind,
                            "reason": "workspace_dir is not a directory",
                        }
                    )
                    continue
            nodes.append(node)
        if not nodes:
            raise ValueError("workspace has no discovery nodes")

        jobs: list[dict[str, Any]] = []
        previous_job_id = ""
        for index, node in enumerate(nodes):
            job_payload = self.workspace_node_job_payload(workspace, node, previous_job_id=previous_job_id)
            job_payload["wait_for_idle"] = True
            metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
            metadata["workflow_phase"] = "discovery"
            metadata["discovery_index"] = index
            job_payload["metadata"] = metadata
            job = self.create_job(job_payload, publish_events=False)
            jobs.append(job)
            previous_job_id = str(job.get("id") or "")

        run = self.register_workspace_execution_run(
            workspace_id,
            kind="discovery",
            trigger="user",
            summary=f"安全发现链 · {len(jobs)} 步",
            jobs=jobs,
        )
        with self.lock:
            refreshed_workspace = self.workspace_by_id(workspace_id) or workspace
            payload_workspace = self.workspace_public_payload(refreshed_workspace)
        return {
            "workspace": payload_workspace,
            "jobs": jobs,
            "run": run,
            "run_id": run["id"],
            "applied": applied,
            "skipped": skipped,
        }
