from __future__ import annotations

from ._deps import *  # noqa: F403

class BaseMixin:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.servers = self.config.servers
        self.lock = threading.RLock()
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
