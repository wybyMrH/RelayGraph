from __future__ import annotations

from ._deps import *  # noqa: F403

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
            self.agent_definitions[index] = updated
            if updated["id"] != previous_id:
                for template in self.workflow_templates:
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
                # Mask API key for security
                api_key = str(public_profile.get("api_key") or "")
                if api_key:
                    public_profile["api_key_masked"] = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    del public_profile["api_key"]
                items.append(public_profile)
        return {"provider_profiles": items}


    def create_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new provider profile."""
        profile_id = str(payload.get("id") or uuid.uuid4().hex[:8]).strip()
        name = str(payload.get("name") or "").strip()
        provider = str(payload.get("provider") or "openai").strip()
        base_url = str(payload.get("base_url") or "").strip()
        api_key = str(payload.get("api_key") or "").strip()
        models = payload.get("models") if isinstance(payload.get("models"), list) else []
        is_default = bool(payload.get("is_default"))

        if not name:
            name = f"{provider.title()} Profile"

        profile: dict[str, Any] = {
            "id": profile_id,
            "name": name,
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "models": models,
            "is_default": is_default,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

        # If this is default, unset other defaults
        if is_default:
            for p in self.provider_profiles:
                p["is_default"] = False

        with self.lock:
            self.provider_profiles.append(profile)
        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        return result


    def update_provider_profile(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            profile = self.provider_profile_by_id(profile_id)
            if not profile:
                raise ValueError("provider profile not found")

            # Update fields
            if "name" in payload:
                profile["name"] = str(payload["name"] or "").strip()
            if "provider" in payload:
                profile["provider"] = str(payload["provider"] or "openai").strip()
            if "base_url" in payload:
                profile["base_url"] = str(payload["base_url"] or "").strip()
            if "api_key" in payload and payload["api_key"]:
                profile["api_key"] = str(payload["api_key"] or "").strip()
            if "models" in payload:
                profile["models"] = payload["models"] if isinstance(payload["models"], list) else []
            if "is_default" in payload:
                is_default = bool(payload["is_default"])
                if is_default:
                    for p in self.provider_profiles:
                        p["is_default"] = False
                profile["is_default"] = is_default

            profile["updated_at"] = now_iso()

        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        return result


    def delete_provider_profile(self, profile_id: str) -> None:
        """Delete a provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            index = next((idx for idx, item in enumerate(self.provider_profiles) if item.get("id") == profile_id), -1)
            if index < 0:
                raise ValueError("provider profile not found")
            del self.provider_profiles[index]
        self.save_provider_profiles()
