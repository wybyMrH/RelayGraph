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


    def workspace_template_diff(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            workspace_snapshot = copy.deepcopy(
                workspace.get("template_snapshot") if isinstance(workspace.get("template_snapshot"), dict) else {}
            )
            template_id = str(workspace.get("template_id") or workspace_snapshot.get("template_id") or "").strip()
            template_name = str(workspace.get("template_name") or workspace_snapshot.get("template_name") or "").strip()
            current_template = copy.deepcopy(self.workflow_template_by_id(template_id)) if template_id else None
            current_snapshot = (
                build_template_snapshot(
                    current_template,
                    getattr(self, "agent_definitions", workspace_default_agents()),
                    getattr(self, "tool_definitions", workspace_default_tools()),
                )
                if current_template
                else {}
            )
        diff = workflow_template_snapshot_diff(workspace_snapshot, current_snapshot)
        return {
            "workspace_id": workspace_id,
            "template_id": template_id,
            "template_name": template_name,
            "diff": diff,
        }


    def apply_workspace_template_migration(self, workspace_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested = body if isinstance(body, dict) else {}
        if not requested.get("confirm"):
            raise ValueError("template migration apply requires confirm=true")
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            current = copy.deepcopy(workspace)
            workspace_snapshot = copy.deepcopy(
                current.get("template_snapshot") if isinstance(current.get("template_snapshot"), dict) else {}
            )
            template_id = str(current.get("template_id") or workspace_snapshot.get("template_id") or "").strip()
            current_template = copy.deepcopy(self.workflow_template_by_id(template_id)) if template_id else None
            if not current_template:
                raise ValueError("current workflow template not found")
            current_snapshot = build_template_snapshot(
                current_template,
                getattr(self, "agent_definitions", workspace_default_agents()),
                getattr(self, "tool_definitions", workspace_default_tools()),
            )
            diff = workflow_template_snapshot_diff(workspace_snapshot, current_snapshot)
            plan = diff.get("migration_plan") if isinstance(diff.get("migration_plan"), dict) else {}
            if diff.get("status") == "same":
                return {
                    "workspace_id": workspace_id,
                    "workspace": self.workspace_public_payload(current),
                    "diff": diff,
                    "applied": {
                        "ok": False,
                        "status": "same",
                        "message": "workspace template snapshot is already current",
                    },
                }
            if not plan.get("can_manual_apply"):
                raise ValueError("template migration requires new workspace or manual rebuild")

            field_changes = set(diff.get("diff", {}).get("changed_fields") if isinstance(diff.get("diff"), dict) else [])
            apply_payload = copy.deepcopy(current)
            current_env = current.get("env") if isinstance(current.get("env"), dict) else {}
            template_env = current_snapshot.get("env") if isinstance(current_snapshot.get("env"), dict) else {}
            env_source = template_env if "env" in field_changes else current_env
            apply_payload["env_name"] = str(env_source.get("name") or "").strip()
            apply_payload["env_manager"] = str(env_source.get("manager") or "").strip()
            apply_payload["python_version"] = str(env_source.get("python") or "").strip()

            template_recipes = current_snapshot.get("recipes") if isinstance(current_snapshot.get("recipes"), list) else []
            current_recipes = current.get("recipes") if isinstance(current.get("recipes"), list) else []
            recipe_source = (
                template_recipes[0]
                if "recipes" in field_changes and template_recipes and isinstance(template_recipes[0], dict)
                else current_recipes[0]
                if current_recipes and isinstance(current_recipes[0], dict)
                else {}
            )
            apply_payload["recipe_id"] = str(recipe_source.get("id") or "default").strip() or "default"
            apply_payload["recipe_name"] = str(recipe_source.get("name") or "默认运行").strip() or "默认运行"
            apply_payload["setup_command"] = str(recipe_source.get("setup_command") or "").strip()
            apply_payload["run_command"] = str(recipe_source.get("run_command") or "").strip()
            apply_payload["report_command"] = str(recipe_source.get("report_command") or "").strip()
            apply_payload["schedule"] = str(recipe_source.get("schedule") or "").strip()
            apply_payload["recipe_notes"] = str(recipe_source.get("notes") or "").strip()
            apply_payload["recipe_enabled"] = bool(recipe_source.get("enabled", True))

            updated = normalize_workspace_instance_from_template(
                apply_payload,
                template=current_template,
                agent_definitions=getattr(self, "agent_definitions", workspace_default_agents()),
                tool_definitions=getattr(self, "tool_definitions", workspace_default_tools()),
                existing=current,
            )
            if "model" not in field_changes and isinstance(current.get("model"), dict):
                updated["model"] = copy.deepcopy(current["model"])
            if not any(step in plan.get("apply_scope", []) for step in ("capabilities", "nodes")):
                if isinstance(current.get("agents"), list):
                    updated["agents"] = copy.deepcopy(current["agents"])
                if isinstance(current.get("tools"), list):
                    updated["tools"] = copy.deepcopy(current["tools"])
            if isinstance(current.get("source"), dict):
                updated["source"] = copy.deepcopy(current["source"])
            updated["template_snapshot"] = current_snapshot
            updated["template_id"] = str(current_template.get("id") or template_id).strip()
            updated["template_name"] = str(current_template.get("name") or current.get("template_name") or "").strip()
            history = current.get("template_migration_history") if isinstance(current.get("template_migration_history"), list) else []
            migration_record = {
                "id": uuid.uuid4().hex[:12],
                "applied_at": now_iso(),
                "mode": "safe_manual",
                "template_id": updated["template_id"],
                "template_name": updated["template_name"],
                "previous_snapshot_created_at": str(workspace_snapshot.get("created_at") or "").strip(),
                "new_snapshot_created_at": str(current_snapshot.get("created_at") or "").strip(),
                "diff_summary": copy.deepcopy(diff.get("summary") if isinstance(diff.get("summary"), dict) else {}),
                "apply_scope": copy.deepcopy(plan.get("apply_scope") if isinstance(plan.get("apply_scope"), list) else []),
                "risk_level": str(plan.get("risk_level") or "").strip(),
            }
            updated["template_migration_history"] = [migration_record, *copy.deepcopy(history)][:12]
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
        self.save_workspaces()
        with self.lock:
            public = self.workspace_public_payload(updated)
        next_diff = workflow_template_snapshot_diff(updated.get("template_snapshot"), current_snapshot)
        return {
            "workspace_id": workspace_id,
            "workspace": public,
            "diff": next_diff,
            "applied": {
                "ok": True,
                "status": "applied",
                "mode": "safe_manual",
                "record": migration_record,
            },
        }


    def create_workspace_template_migration_draft(
        self,
        workspace_id: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested = body if isinstance(body, dict) else {}
        if not requested.get("confirm"):
            raise ValueError("template migration draft requires confirm=true")
        with self.lock:
            workspace = self.workspace_by_id(workspace_id)
            if not workspace:
                raise ValueError("workspace not found")
            current = copy.deepcopy(workspace)
            workspace_snapshot = copy.deepcopy(
                current.get("template_snapshot") if isinstance(current.get("template_snapshot"), dict) else {}
            )
            template_id = str(current.get("template_id") or workspace_snapshot.get("template_id") or "").strip()
            current_template = copy.deepcopy(self.workflow_template_by_id(template_id)) if template_id else None
            if not current_template:
                raise ValueError("current workflow template not found")
            current_snapshot = build_template_snapshot(
                current_template,
                getattr(self, "agent_definitions", workspace_default_agents()),
                getattr(self, "tool_definitions", workspace_default_tools()),
            )
            diff = workflow_template_snapshot_diff(workspace_snapshot, current_snapshot)
            if diff.get("status") == "same":
                raise ValueError("workspace template snapshot is already current")
            plan = diff.get("migration_plan") if isinstance(diff.get("migration_plan"), dict) else {}
            if not plan.get("can_create_draft"):
                raise ValueError("template migration draft is not available for this diff")

            inputs = copy.deepcopy(current.get("inputs") if isinstance(current.get("inputs"), dict) else {})
            env = current.get("env") if isinstance(current.get("env"), dict) else {}
            recipes = current.get("recipes") if isinstance(current.get("recipes"), list) else []
            recipe = recipes[0] if recipes and isinstance(recipes[0], dict) else {}
            draft_name = str(requested.get("name") or "").strip()
            if not draft_name:
                base_name = str(current.get("name") or current.get("brief") or current.get("id") or "迁移实例").strip()
                draft_name = f"{base_name[:48]} · 迁移草稿"
            draft_payload = {
                "name": draft_name,
                "status": "draft",
                "inputs": inputs,
                "goal_text": str(inputs.get("goal_text") or current.get("brief") or "").strip(),
                "workspace_dir": str(current.get("workspace_dir") or "").strip(),
                "env_name": str(env.get("name") or "").strip(),
                "env_manager": str(env.get("manager") or "").strip(),
                "python_version": str(env.get("python") or "").strip(),
                "recipe_id": str(recipe.get("id") or "default").strip() or "default",
                "recipe_name": str(recipe.get("name") or "默认运行").strip() or "默认运行",
                "setup_command": str(recipe.get("setup_command") or "").strip(),
                "run_command": str(recipe.get("run_command") or "").strip(),
                "report_command": str(recipe.get("report_command") or "").strip(),
                "schedule": str(recipe.get("schedule") or "").strip(),
                "recipe_notes": str(recipe.get("notes") or "").strip(),
                "recipe_enabled": bool(recipe.get("enabled", True)),
                "notes": str(current.get("notes") or "").strip(),
                "tags": copy.deepcopy(current.get("tags") if isinstance(current.get("tags"), list) else []),
            }
            existing_seed = copy.deepcopy(current)
            for key in ("id", "created_at", "updated_at", "runs", "chat", "execution", "template_migration_history"):
                existing_seed.pop(key, None)
            existing_seed["runs"] = []
            existing_seed["chat"] = []
            existing_seed["execution"] = {}
            draft = normalize_workspace_instance_from_template(
                draft_payload,
                template=current_template,
                agent_definitions=getattr(self, "agent_definitions", workspace_default_agents()),
                tool_definitions=getattr(self, "tool_definitions", workspace_default_tools()),
                existing=existing_seed,
            )
            record = {
                "id": uuid.uuid4().hex[:12],
                "applied_at": now_iso(),
                "mode": "structural_draft",
                "source_workspace_id": workspace_id,
                "source_workspace_name": str(current.get("name") or "").strip(),
                "template_id": str(current_template.get("id") or template_id).strip(),
                "template_name": str(current_template.get("name") or "").strip(),
                "previous_snapshot_created_at": str(workspace_snapshot.get("created_at") or "").strip(),
                "new_snapshot_created_at": str(current_snapshot.get("created_at") or "").strip(),
                "diff_summary": copy.deepcopy(diff.get("summary") if isinstance(diff.get("summary"), dict) else {}),
                "risk_level": str(plan.get("risk_level") or "").strip(),
            }
            draft["source_migration"] = {
                "source_workspace_id": workspace_id,
                "source_workspace_name": str(current.get("name") or "").strip(),
                "created_at": record["applied_at"],
                "template_id": record["template_id"],
                "template_name": record["template_name"],
            }
            draft["template_migration_history"] = [record]
            self.workspaces.insert(0, draft)
        self.save_workspaces()
        with self.lock:
            public = self.workspace_public_payload(draft)
        draft_diff = workflow_template_snapshot_diff(draft.get("template_snapshot"), current_snapshot)
        return {
            "workspace_id": workspace_id,
            "draft_workspace_id": str(draft.get("id") or "").strip(),
            "workspace": public,
            "diff": draft_diff,
            "source_diff": diff,
            "created": {
                "ok": True,
                "status": "created",
                "mode": "structural_draft",
                "record": record,
            },
        }


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
