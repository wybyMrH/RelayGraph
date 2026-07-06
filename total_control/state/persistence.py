from __future__ import annotations

from ._deps import *  # noqa: F403

class PersistenceMixin:
    def save_jobs(self) -> None:
        with self.lock:
            write_json(JOBS_PATH, self.jobs)


    def save_workspaces(self) -> None:
        with self.lock:
            write_json(WORKSPACES_PATH, self.workspaces)


    def save_provider_profiles(self) -> None:
        with self.lock:
            # Keep plaintext in memory (LLMClient needs it); write an encrypted
            # copy to disk so provider_profiles.json never holds raw keys.
            encrypted: list[Any] = []
            for profile in self.provider_profiles:
                if isinstance(profile, dict):
                    sealed = dict(profile)
                    sealed["api_key"] = encrypt_secret(str(sealed.get("api_key") or ""))
                    encrypted.append(sealed)
                else:
                    encrypted.append(profile)
            write_json(PROVIDER_PROFILES_PATH, encrypted)


    def save_workflow_templates(self) -> None:
        with self.lock:
            write_json(WORKFLOW_TEMPLATES_PATH, self.workflow_templates)


    def save_agent_definitions(self) -> None:
        with self.lock:
            tool_ids = [str(item.get("id") or "").strip() for item in self.tool_definitions]
            seen: set[str] = set()
            deduped: list[dict[str, Any]] = []
            for index, item in enumerate(self.agent_definitions):
                if not isinstance(item, dict):
                    continue
                agent = normalize_global_agent_definition(
                    item,
                    index=index,
                    existing=item,
                    tool_ids=tool_ids,
                    touch_updated_at=False,
                )
                agent_id = str(agent.get("id") or "").strip()
                if agent_id and agent_id in seen:
                    continue
                if agent_id:
                    seen.add(agent_id)
                deduped.append(agent)
            self.agent_definitions = deduped
            write_json(AGENT_DEFINITIONS_PATH, self.agent_definitions)


    def save_tool_definitions(self) -> None:
        with self.lock:
            write_json(TOOL_DEFINITIONS_PATH, self.tool_definitions)
