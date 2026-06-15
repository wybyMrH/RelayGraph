from __future__ import annotations

from ._deps import *  # noqa: F403


def _dedupe_provider_profiles(profiles: list[Any]) -> tuple[list[dict[str, Any]], bool]:
    deduped: list[dict[str, Any]] = []
    index_by_id: dict[str, int] = {}
    changed = False
    for item in profiles:
        if not isinstance(item, dict):
            changed = True
            continue
        profile = copy.deepcopy(item)
        profile_id = str(profile.get("id") or "").strip()
        if not profile_id:
            deduped.append(profile)
            continue
        existing_index = index_by_id.get(profile_id)
        if existing_index is None:
            index_by_id[profile_id] = len(deduped)
            deduped.append(profile)
            continue
        changed = True
        merged = deduped[existing_index]
        for key in ("name", "provider", "base_url", "created_at", "updated_at"):
            value = str(profile.get(key) or "").strip()
            if value:
                merged[key] = value
        if isinstance(profile.get("models"), list) and profile.get("models"):
            merged["models"] = list(profile.get("models") or [])
        if "is_default" in profile:
            merged["is_default"] = bool(profile.get("is_default"))
        api_key = str(profile.get("api_key") or "").strip()
        if api_key:
            merged["api_key"] = api_key
    return deduped, changed


class BaseMixin:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.servers = self.config.servers
        self.lock = threading.RLock()
        self.event_broker = EventBroker()
        self.statuses: list[dict[str, Any]] = []
        self.last_refresh = 0.0
        self.last_refreshed_at = ""
        self.jobs: list[dict[str, Any]] = read_json(JOBS_PATH, [])
        raw_tool_definitions = read_json(TOOL_DEFINITIONS_PATH, [])
        self.tool_definitions: list[dict[str, Any]] = normalize_global_tool_definitions(raw_tool_definitions)
        self.tool_definitions, default_tools_applied = backfill_default_tool_definitions(
            self.tool_definitions,
            global_definitions=True,
        )
        raw_agent_definitions = read_json(AGENT_DEFINITIONS_PATH, [])
        self.agent_definitions: list[dict[str, Any]] = normalize_global_agent_definitions(
            raw_agent_definitions,
            tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
        )
        self.agent_definitions, default_agent_tools_applied = backfill_default_agent_tools(
            self.agent_definitions,
            tool_ids=[str(item.get("id") or "").strip() for item in self.tool_definitions],
        )
        raw_workflow_templates = read_json(WORKFLOW_TEMPLATES_PATH, [])
        if isinstance(raw_workflow_templates, list) and raw_workflow_templates:
            self.workflow_templates = [
                normalize_workflow_template(
                    item,
                    existing=item if isinstance(item, dict) else None,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
                for item in raw_workflow_templates
                if isinstance(item, dict)
            ]
        else:
            self.workflow_templates = build_default_workflow_templates(self.agent_definitions, self.tool_definitions)
        raw_workspaces = read_json(WORKSPACES_PATH, [])
        self.workspaces: list[dict[str, Any]] = raw_workspaces if isinstance(raw_workspaces, list) else []
        raw_provider_profiles = read_json(PROVIDER_PROFILES_PATH, [])
        self.provider_profiles: list[dict[str, Any]] = raw_provider_profiles if isinstance(raw_provider_profiles, list) else []
        for _profile in self.provider_profiles:
            if isinstance(_profile, dict):
                _profile["api_key"] = decrypt_secret(str(_profile.get("api_key") or ""))
        self.provider_profiles, provider_profiles_deduped = _dedupe_provider_profiles(self.provider_profiles)
        self.next_queue_rank = 1
        self.terminals: dict[str, WebTerminal] = {}
        self.terminals_lock = threading.Lock()
        self.file_preview_cache: dict[str, dict[str, Any]] = {}
        self.last_preview_cache_cleanup = 0.0
        self.stop_event = threading.Event()
        if self.bootstrap_queue_ranks():
            write_json(JOBS_PATH, self.jobs)
        if (not isinstance(raw_tool_definitions, list) or not raw_tool_definitions) or default_tools_applied:
            write_json(TOOL_DEFINITIONS_PATH, self.tool_definitions)
        if (not isinstance(raw_agent_definitions, list) or not raw_agent_definitions) or default_agent_tools_applied:
            write_json(AGENT_DEFINITIONS_PATH, self.agent_definitions)
        if not isinstance(raw_workflow_templates, list) or not raw_workflow_templates:
            write_json(WORKFLOW_TEMPLATES_PATH, self.workflow_templates)
        if provider_profiles_deduped and hasattr(self, "save_provider_profiles"):
            self.save_provider_profiles()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        FILE_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.thread.start()


    def public_config(self) -> dict[str, Any]:
        return {
            "poll_interval_seconds": self.config.poll_interval_seconds,
            "idle_min_free_mib": self.config.idle_min_free_mib,
            "idle_max_gpu_util": self.config.idle_max_gpu_util,
            "config_path": str(self.config_path),
            "server_count": len(self.servers),
        }


    def publish_event(
        self,
        event_type: str,
        *,
        workspace_id: str = "",
        payload: dict[str, Any] | None = None,
        run_id: str = "",
        job_id: str = "",
        agent_execution_id: str = "",
    ) -> dict[str, Any] | None:
        broker = getattr(self, "event_broker", None)
        if broker is None:
            return None
        return broker.publish(
            event_type,
            workspace_id=workspace_id,
            payload=payload,
            run_id=run_id,
            job_id=job_id,
            agent_execution_id=agent_execution_id,
        )


    def publish_job_event(self, job: dict[str, Any], event_type: str = "job.updated") -> None:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        workspace_id = str(metadata.get("workspace_id") or "").strip()
        if not workspace_id:
            return
        self.publish_event(
            event_type,
            workspace_id=workspace_id,
            job_id=str(job.get("id") or "").strip(),
            run_id=str(metadata.get("execution_run_id") or "").strip(),
            payload={"job": copy.deepcopy(job)},
        )


    def server_by_id(self, server_id: str) -> ServerConfig | None:
        return next((server for server in self.servers if server.id == server_id), None)


    def bootstrap_queue_ranks(self) -> bool:
        changed = False
        queued = [job for job in reversed(self.jobs) if str(job.get("status") or "") in {"queued", "blocked", "starting"}]
        for index, job in enumerate(queued, 1):
            if safe_int(job.get("queue_rank"), 0) != index:
                job["queue_rank"] = index
                changed = True
        self.next_queue_rank = len(queued) + 1
        return changed


    def reserve_queue_ranks(self, jobs: list[dict[str, Any]]) -> None:
        for job in jobs:
            job["queue_rank"] = self.next_queue_rank
            self.next_queue_rank += 1


    def queue_sort_key(self, job: dict[str, Any]) -> tuple[int, str, str]:
        return (
            safe_int(job.get("queue_rank"), 10**9),
            str(job.get("created_at") or ""),
            str(job.get("id") or ""),
        )
