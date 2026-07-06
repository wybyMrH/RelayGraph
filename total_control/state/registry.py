from __future__ import annotations

from ._deps import *  # noqa: F403
from .registry_pkg.execution_overview import (
    build_execution_overview_payload as _build_execution_overview_payload,
)
from .registry_pkg.provider_profiles import (
    provider_profile_health,
    provider_profile_key_required as _provider_profile_key_required,
    provider_profile_kind as _provider_profile_kind,
)
from .registry_pkg.provider_route_health import (
    build_provider_route_health as _build_provider_route_health,
)
from .registry_pkg.tool_testing import (
    run_tool_definition_safe_test as _run_tool_definition_safe_test,
)
from .registry_pkg.workflow_templates import (
    build_workflow_template_preview_payload as _build_workflow_template_preview_payload,
    build_workflow_template_validation_payload as _build_workflow_template_validation_payload,
)


class RegistryMixin:
    def tool_definition_by_id(self, tool_id: str) -> dict[str, Any] | None:
        return next((item for item in self.tool_definitions if str(item.get("id") or "") == str(tool_id)), None)


    def agent_definition_by_id(self, agent_id: str) -> dict[str, Any] | None:
        return next((item for item in self.agent_definitions if str(item.get("id") or "") == str(agent_id)), None)


    def workflow_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        return next((item for item in self.workflow_templates if str(item.get("id") or "") == str(template_id)), None)


    def list_tool_definitions(self) -> dict[str, Any]:
        with self.lock:
            return {"tool_definitions": copy.deepcopy(self.tool_definitions)}

    def test_tool_definition(self, tool_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a safe tool preview against a workspace snapshot.

        Configuration-center tool tests must not bypass the controlled runtime
        queue. Read-only tools can execute with the workspace executor; runtime
        and dangerous tools return a blocked/plan-only result so their payload
        shape can be inspected without causing side effects.
        """
        requested = payload if isinstance(payload, dict) else {}
        requested_tool_id = str(tool_id or requested.get("tool_id") or "").strip()
        with self.lock:
            tool = copy.deepcopy(self.tool_definition_by_id(requested_tool_id)) if requested_tool_id else None
            workspace_id = str(requested.get("workspace_id") or "").strip()
            workspace = copy.deepcopy(self.workspace_by_id(workspace_id)) if workspace_id else None
            if not workspace:
                workspace = copy.deepcopy(self.workspaces[0]) if getattr(self, "workspaces", []) else {}
            statuses = copy.deepcopy(getattr(self, "statuses", []))
            jobs = copy.deepcopy(getattr(self, "jobs", []))
            provider_profiles = copy.deepcopy(getattr(self, "provider_profiles", []))
            tool_definitions = copy.deepcopy(getattr(self, "tool_definitions", []))
        arguments = requested.get("arguments") if isinstance(requested.get("arguments"), dict) else {}
        return _run_tool_definition_safe_test(
            requested_tool_id,
            tool=tool,
            workspace=workspace,
            arguments=arguments,
            config=getattr(self, "config", None),
            statuses=statuses,
            jobs=jobs,
            provider_profiles=provider_profiles,
            tool_definitions=tool_definitions,
        )


    def list_agent_definitions(self) -> dict[str, Any]:
        with self.lock:
            return {"agent_definitions": copy.deepcopy(self.agent_definitions)}


    def list_workflow_templates(self) -> dict[str, Any]:
        with self.lock:
            items = [
                self.workflow_template_public_payload(item)
                for item in sorted(self.workflow_templates, key=workflow_template_sort_key, reverse=True)
            ]
        return {"workflow_templates": items}

    def provider_route_health(self) -> dict[str, Any]:
        with self.lock:
            profiles = copy.deepcopy(getattr(self, "provider_profiles", []))
            agents = copy.deepcopy(getattr(self, "agent_definitions", []))
            templates = copy.deepcopy(getattr(self, "workflow_templates", []))
            workspaces = copy.deepcopy(getattr(self, "workspaces", []))
        return _build_provider_route_health(profiles, agents, templates, workspaces)

    def execution_overview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        requested = payload if isinstance(payload, dict) else {}
        self.sync_workspace_execution_runs_from_jobs()
        with self.lock:
            workspaces = copy.deepcopy(getattr(self, "workspaces", []))
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        return _build_execution_overview_payload(requested, workspaces, jobs)

    def validate_workflow_template(self, payload: dict[str, Any], template_id: str = "") -> dict[str, Any]:
        body = payload if isinstance(payload, dict) else {}
        requested_id = str(template_id or body.get("template_id") or "").strip()
        with self.lock:
            current = self.workflow_template_by_id(requested_id) if requested_id else None
            if requested_id and not current:
                raise ValueError("workflow template not found")
            template = normalize_workflow_template(
                body if body else copy.deepcopy(current or {}),
                existing=current,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
            )
            public = self.workflow_template_public_payload(template)
            validation = _build_workflow_template_validation_payload(
                template,
                body,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
                provider_profiles=getattr(self, "provider_profiles", []),
            )
            preview = _build_workflow_template_preview_payload(template, validation, body)
        return {
            "workflow_template": public,
            "validation": validation,
            "preview": preview,
        }


    def create_tool_definition(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool = normalize_global_tool_definition(payload, index=len(self.tool_definitions))
        with self.lock:
            self.tool_definitions.insert(0, tool)
        self.save_tool_definitions()
        return tool


    def update_tool_definition(self, tool_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        tool_id = str(tool_id or "").strip()
        with self.lock:
            current = self.tool_definition_by_id(tool_id)
            if not current:
                raise ValueError("tool definition not found")
            updated = normalize_global_tool_definition({**current, **payload}, existing=current)
            index = next((idx for idx, item in enumerate(self.tool_definitions) if str(item.get("id") or "") == tool_id), -1)
            if index < 0:
                raise ValueError("tool definition not found")
            previous_id = str(current.get("id") or "").strip()
            self.tool_definitions[index] = updated
            if updated["id"] != previous_id:
                for agent in self.agent_definitions:
                    tools = parse_tag_list(agent.get("tools", []))
                    agent["tools"] = [updated["id"] if item == previous_id else item for item in tools]
                self.agent_definitions = normalize_global_agent_definitions(
                    self.agent_definitions,
                    existing=self.agent_definitions,
                    tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
                )
        self.save_tool_definitions()
        self.save_agent_definitions()
        return updated


    def delete_tool_definition(self, tool_id: str) -> None:
        tool_id = str(tool_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.tool_definitions) if str(item.get("id") or "") == tool_id), -1)
            if index < 0:
                raise ValueError("tool definition not found")
            del self.tool_definitions[index]
            for agent in self.agent_definitions:
                agent["tools"] = [item for item in parse_tag_list(agent.get("tools", [])) if item != tool_id]
        self.save_tool_definitions()
        self.save_agent_definitions()


    def create_agent_definition(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool_ids = [str(item.get("id") or "").strip() for item in self.tool_definitions]
        agent = normalize_global_agent_definition(payload, index=len(self.agent_definitions), tool_ids=tool_ids)
        with self.lock:
            existing_index = next(
                (idx for idx, item in enumerate(self.agent_definitions) if str(item.get("id") or "").strip() == agent["id"]),
                -1,
            )
            if existing_index >= 0:
                current = self.agent_definitions[existing_index]
                agent = normalize_global_agent_definition(
                    {**current, **payload, "id": agent["id"]},
                    index=existing_index,
                    existing=current,
                    tool_ids=tool_ids,
                )
                self.agent_definitions[existing_index] = agent
            else:
                self.agent_definitions.insert(0, agent)
        self.save_agent_definitions()
        return agent


    def update_agent_definition(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(agent_id or "").strip()
        tool_ids = [str(item.get("id") or "").strip() for item in self.tool_definitions]
        with self.lock:
            current = self.agent_definition_by_id(agent_id)
            if not current:
                raise ValueError("agent definition not found")
            updated = normalize_global_agent_definition({**current, **payload}, existing=current, tool_ids=tool_ids)
            index = next((idx for idx, item in enumerate(self.agent_definitions) if str(item.get("id") or "") == agent_id), -1)
            if index < 0:
                raise ValueError("agent definition not found")
            previous_id = str(current.get("id") or "").strip()
            duplicate_index = next(
                (
                    idx
                    for idx, item in enumerate(self.agent_definitions)
                    if idx != index and str(item.get("id") or "").strip() == updated["id"]
                ),
                -1,
            )
            if duplicate_index >= 0:
                raise ValueError("agent definition id already exists")
            else:
                self.agent_definitions[index] = updated
            if updated["id"] != previous_id:
                for template in self.workflow_templates:
                    agent_ids = [str(item or "").strip() for item in template.get("agent_ids", []) if str(item or "").strip()]
                    if previous_id in agent_ids:
                        template["agent_ids"] = [updated["id"] if item == previous_id else item for item in agent_ids]
                    nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
                        if str(handler.get("agent_id") or "").strip() != previous_id:
                            continue
                        handler["agent_id"] = updated["id"]
                        handler["name"] = updated["name"]
                        node["handler"] = handler
                    model = template.get("model") if isinstance(template.get("model"), dict) else {}
                    if str(model.get("chat_agent_id") or "").strip() == previous_id:
                        model["chat_agent_id"] = updated["id"]
                        template["model"] = model
        self.save_agent_definitions()
        self.save_workflow_templates()
        return updated


    def delete_agent_definition(self, agent_id: str) -> None:
        agent_id = str(agent_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.agent_definitions) if str(item.get("id") or "") == agent_id), -1)
            if index < 0:
                raise ValueError("agent definition not found")
            del self.agent_definitions[index]
            for template in self.workflow_templates:
                nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
                    if str(handler.get("agent_id") or "").strip() != agent_id:
                        continue
                    handler["agent_id"] = ""
                    node["handler"] = handler
                model = template.get("model") if isinstance(template.get("model"), dict) else {}
                if str(model.get("chat_agent_id") or "").strip() == agent_id:
                    model["chat_agent_id"] = ""
                    template["model"] = model
        self.save_agent_definitions()
        self.save_workflow_templates()


    def create_workflow_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = normalize_workflow_template(
            payload,
            agent_definitions=self.agent_definitions,
            tool_definitions=self.tool_definitions,
        )
        create_record = workflow_template_version_record(
            None,
            template,
            agent_definitions=self.agent_definitions,
            tool_definitions=self.tool_definitions,
            mode="create",
        )
        if create_record:
            template["version_history"] = [create_record]
        with self.lock:
            self.workflow_templates.insert(0, template)
        self.save_workflow_templates()
        return self.workflow_template_public_payload(template)


    def update_workflow_template(self, template_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        template_id = str(template_id or "").strip()
        with self.lock:
            current = self.workflow_template_by_id(template_id)
            if not current:
                raise ValueError("workflow template not found")
            merged = dict(current)
            merged.update(payload)
            updated = normalize_workflow_template(
                merged,
                existing=current,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
            )
            version_record = workflow_template_version_record(
                current,
                updated,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
                mode="update",
            )
            if version_record:
                current_history = current.get("version_history") if isinstance(current.get("version_history"), list) else []
                updated["version_history"] = normalize_workflow_template_version_history([version_record, *copy.deepcopy(current_history)])
            index = next((idx for idx, item in enumerate(self.workflow_templates) if str(item.get("id") or "") == template_id), -1)
            if index < 0:
                raise ValueError("workflow template not found")
            self.workflow_templates[index] = updated
        self.save_workflow_templates()
        return self.workflow_template_public_payload(updated)


    def delete_workflow_template(self, template_id: str) -> None:
        template_id = str(template_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workflow_templates) if str(item.get("id") or "") == template_id), -1)
            if index < 0:
                raise ValueError("workflow template not found")
            del self.workflow_templates[index]
        self.save_workflow_templates()


    def provider_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        return next((item for item in self.provider_profiles if str(item.get("id")) == str(profile_id)), None)


    def list_provider_profiles(self) -> dict[str, Any]:
        """List all provider profiles (API keys masked)."""
        with self.lock:
            items = []
            for profile in self.provider_profiles:
                public_profile = dict(profile)
                health = provider_profile_health(profile)
                # Mask API key for security
                api_key = str(public_profile.get("api_key") or "")
                if api_key:
                    public_profile["api_key_masked"] = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    del public_profile["api_key"]
                public_profile["has_api_key"] = bool(api_key) or not bool(health.get("key_required", True))
                public_profile["key_required"] = bool(health.get("key_required", True))
                public_profile["status"] = str(health.get("status") or "warning")
                public_profile["missing_fields"] = list(health.get("missing_fields") or [])
                items.append(public_profile)
        return {"provider_profiles": items}


    def list_provider_catalog(self) -> dict[str, Any]:
        """List known vendor presets so a profile can be created from a pick + key."""
        return {"provider_catalog": copy.deepcopy(PROVIDER_CATALOG)}


    def create_provider_profile_from_catalog(
        self,
        vendor_id: str,
        *,
        api_key: str = "",
        name: str = "",
        models: list[Any] | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Materialize a provider profile from a catalogue vendor + API key.

        Falls back to a non-empty sentinel key for local/no-key vendors
        (e.g. Ollama) so LLMClient's empty-key guard does not block them.
        """
        vendor = provider_catalog_by_id(vendor_id)
        if not vendor:
            raise ValueError(f"unknown provider catalog vendor: {vendor_id or '(empty)'}")
        key_required = bool(vendor.get("key_required", True))
        resolved_key = str(api_key or "").strip()
        if key_required and not resolved_key:
            raise ValueError(f"vendor {vendor_id} requires an api_key")
        if not resolved_key:
            resolved_key = "sk-no-key-required"

        profile_models = models if isinstance(models, list) else list(vendor.get("models") or [])
        profile_name = str(name or "").strip() or str(vendor.get("name") or vendor_id).strip()
        payload = {
            "id": str(uuid.uuid4().hex[:10]),
            "kind": "llm",
            "name": profile_name,
            "vendor_id": vendor_id,
            "provider": str(vendor.get("provider") or "openai").strip(),
            "base_url": str(vendor.get("base_url") or "").strip(),
            "api_key": resolved_key,
            "models": profile_models,
            "is_default": bool(is_default),
            "key_required": key_required,
        }
        return self.create_provider_profile(payload)


    def create_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new provider profile."""
        profile_id = str(payload.get("id") or uuid.uuid4().hex[:8]).strip()
        kind = _provider_profile_kind(payload)
        name = str(payload.get("name") or "").strip()
        provider = str(payload.get("provider") or payload.get("search_provider") or ("openai" if kind == "llm" else "")).strip()
        base_url = str(payload.get("base_url") or "").strip()
        api_key = str(payload.get("api_key") or "").strip()
        models = payload.get("models") if isinstance(payload.get("models"), list) else []
        is_default = bool(payload.get("is_default"))
        vendor_id = str(payload.get("vendor_id") or payload.get("vendor") or "").strip()
        key_required_source = payload if "key_required" in payload else {
            "kind": kind,
            "base_url": base_url,
            "vendor_id": vendor_id,
            "provider": provider,
        }
        key_required = _provider_profile_key_required(key_required_source)

        if not name:
            name = f"{provider.title() or kind.title()} Profile"

        with self.lock:
            existing_profiles = [
                item for item in self.provider_profiles
                if isinstance(item, dict) and str(item.get("id") or "").strip() == profile_id
            ]
            existing = existing_profiles[-1] if existing_profiles else {}
            resolved_api_key = api_key or str(existing.get("api_key") or "").strip()
            if not resolved_api_key and not key_required:
                resolved_api_key = "sk-no-key-required"
            created_at = str(existing.get("created_at") or now_iso()).strip() or now_iso()
            profile: dict[str, Any] = {
                "id": profile_id,
                "name": name,
                "kind": kind,
                "vendor_id": vendor_id,
                "provider": provider,
                "base_url": base_url,
                "api_key": resolved_api_key,
                "models": models,
                "is_default": is_default,
                "key_required": key_required,
                "created_at": created_at,
                "updated_at": now_iso(),
            }

            updated_profiles: list[dict[str, Any]] = []
            for item in self.provider_profiles:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "").strip()
                if item_id == profile_id:
                    continue
                if is_default and _provider_profile_kind(item) == kind:
                    item = dict(item)
                    item["is_default"] = False
                updated_profiles.append(item)
            updated_profiles.append(profile)
            self.provider_profiles = updated_profiles
        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        health = provider_profile_health(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        result["has_api_key"] = bool(profile.get("api_key")) or not bool(health.get("key_required", True))
        result["key_required"] = bool(health.get("key_required", True))
        result["status"] = str(health.get("status") or "warning")
        result["missing_fields"] = list(health.get("missing_fields") or [])
        return result


    def test_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ping a provider endpoint with a 1-token request to verify the link.

        Accepts either a saved ``profile_id`` or raw ``{provider, base_url,
        api_key, model}`` values so a draft can be tested before saving.
        """
        profile_id = str(payload.get("profile_id") or "").strip()
        if profile_id:
            with self.lock:
                saved = self.provider_profile_by_id(profile_id)
                profile = copy.deepcopy(saved) if saved else None
        else:
            model = str(payload.get("model") or "").strip()
            kind = _provider_profile_kind(payload)
            profile = {
                "id": "test",
                "kind": kind,
                "provider": str(payload.get("provider") or payload.get("vendor") or ("openai" if kind == "llm" else "")).strip(),
                "base_url": str(payload.get("base_url") or "").strip(),
                "api_key": str(payload.get("api_key") or "").strip(),
                "models": [model] if model else [],
                "key_required": bool(payload.get("key_required", True)),
            }
        if not profile:
            return {"success": False, "error": "provider profile not found", "model": ""}
        if _provider_profile_kind(profile) == "search":
            from ..tools.workspace_executor_pkg.context import WorkspaceToolContext
            from ..tools.workspace_executor_pkg.web_search import execute_web_search

            profile_id = str(profile.get("id") or payload.get("profile_id") or "draft-search-profile").strip()
            query = str(payload.get("query") or "RelayGraph search provider smoke").strip()
            context = WorkspaceToolContext(
                workspace={"id": "provider-search-test", "inputs": {"goal_text": query}},
                provider_profiles=[profile],
            )
            result = execute_web_search(
                context,
                {
                    "query": query,
                    "limit": max(1, min(safe_int(payload.get("limit"), 3), 5)),
                    "provider_profile_id": profile_id,
                },
            )
            provider_status = str(result.get("provider_status") or result.get("status") or "").strip()
            success = bool(result.get("provider_configured")) and provider_status not in {"", "blocked", "error", "unconfigured"}
            return {
                "success": success,
                "kind": "search",
                "provider": result.get("provider") or profile.get("provider") or "",
                "base_url": str(profile.get("base_url") or "").strip(),
                "profile_id": profile_id,
                "provider_status": provider_status,
                "status": result.get("status") or "",
                "latency_ms": result.get("latency_ms") or 0,
                "result_count": result.get("result_count") or 0,
                "result_provenance": result.get("result_provenance") or [],
                "rate_limit": result.get("rate_limit") or {},
                "error": result.get("error") or "",
            }
        client = LLMClient(profile)
        if not client.api_key:
            return {
                "success": False,
                "error": "API key not configured",
                "provider": client.provider,
                "base_url": client.base_url,
                "model": "",
            }
        model = (client.models[0] if client.models else "") or str(payload.get("model") or "").strip()
        response = client.chat(
            [ChatMessage(role="user", content="ping")],
            model=model or None,
            max_tokens=8,
            timeout=15,
        )
        # If the chat ping failed (often a bad/unknown model name), still report
        # connectivity via /models so the user can pick a valid model.
        models: list[str] = []
        models_error = ""
        if not response.success:
            listed = client.list_models()
            models = listed.get("models") or []
            models_error = listed.get("error") or ""
        return {
            "success": response.success,
            "provider": client.provider,
            "base_url": client.base_url,
            "model": response.model or model,
            "latency_ms": round(float(response.latency_ms or 0), 1),
            "total_tokens": response.total_tokens,
            "content_preview": (response.content or "")[:120],
            "error": response.error,
            "available_models": models,
            "models_error": models_error,
        }

    def list_provider_models(self, payload: dict[str, Any]) -> dict[str, Any]:
        """List available model ids from a provider endpoint (GET /models)."""
        profile_id = str(payload.get("profile_id") or "").strip()
        if profile_id:
            with self.lock:
                saved = self.provider_profile_by_id(profile_id)
                profile = copy.deepcopy(saved) if saved else None
        else:
            model = str(payload.get("model") or "").strip()
            kind = _provider_profile_kind(payload)
            profile = {
                "id": "models",
                "kind": kind,
                "provider": str(payload.get("provider") or payload.get("vendor") or ("openai" if kind == "llm" else "")).strip(),
                "base_url": str(payload.get("base_url") or "").strip(),
                "api_key": str(payload.get("api_key") or "").strip(),
                "models": [model] if model else [],
                "key_required": bool(payload.get("key_required", True)),
            }
        if not profile:
            return {"success": False, "models": [], "error": "provider profile not found"}
        if _provider_profile_kind(profile) == "search":
            return {
                "success": False,
                "models": [],
                "kind": "search",
                "provider": str(profile.get("provider") or "").strip(),
                "base_url": str(profile.get("base_url") or "").strip(),
                "error": "search provider profiles do not expose LLM models",
            }
        client = LLMClient(profile)
        if not client.api_key:
            return {"success": False, "models": [], "error": "API key not configured"}
        result = client.list_models()
        return {
            "success": bool(result.get("success")),
            "models": list(result.get("models") or []),
            "provider": client.provider,
            "base_url": client.base_url,
            "error": result.get("error") or "",
        }


    def update_provider_profile(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            profile = self.provider_profile_by_id(profile_id)
            if not profile:
                raise ValueError("provider profile not found")

            # Update fields
            if "kind" in payload or "profile_type" in payload or "type" in payload:
                profile["kind"] = _provider_profile_kind(payload)
            kind = _provider_profile_kind(profile)
            if "name" in payload:
                profile["name"] = str(payload["name"] or "").strip()
            if "vendor_id" in payload or "vendor" in payload:
                profile["vendor_id"] = str(payload.get("vendor_id") or payload.get("vendor") or "").strip()
            if "provider" in payload or "search_provider" in payload:
                profile["provider"] = str(payload.get("provider") or payload.get("search_provider") or ("openai" if kind == "llm" else "")).strip()
            if "base_url" in payload:
                profile["base_url"] = str(payload["base_url"] or "").strip()
            if "key_required" in payload:
                profile["key_required"] = bool(payload.get("key_required"))
            if "api_key" in payload and payload["api_key"]:
                profile["api_key"] = str(payload["api_key"] or "").strip()
            if "models" in payload:
                profile["models"] = payload["models"] if isinstance(payload["models"], list) else []
            if "is_default" in payload:
                is_default = bool(payload["is_default"])
                if is_default:
                    for p in self.provider_profiles:
                        if _provider_profile_kind(p) == _provider_profile_kind(profile):
                            p["is_default"] = False
                profile["is_default"] = is_default
            if not str(profile.get("api_key") or "").strip() and not _provider_profile_key_required(profile):
                profile["api_key"] = "sk-no-key-required"

            profile["updated_at"] = now_iso()

        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        health = provider_profile_health(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        result["has_api_key"] = bool(profile.get("api_key")) or not bool(health.get("key_required", True))
        result["key_required"] = bool(health.get("key_required", True))
        result["status"] = str(health.get("status") or "warning")
        result["missing_fields"] = list(health.get("missing_fields") or [])
        return result


    def delete_provider_profile(self, profile_id: str) -> None:
        """Delete a provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            original_count = len(self.provider_profiles)
            self.provider_profiles = [
                item
                for item in self.provider_profiles
                if not (isinstance(item, dict) and str(item.get("id") or "").strip() == profile_id)
            ]
            if len(self.provider_profiles) == original_count:
                raise ValueError("provider profile not found")
        self.save_provider_profiles()
