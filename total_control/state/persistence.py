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
            write_json(AGENT_DEFINITIONS_PATH, self.agent_definitions)


    def save_tool_definitions(self) -> None:
        with self.lock:
            write_json(TOOL_DEFINITIONS_PATH, self.tool_definitions)
