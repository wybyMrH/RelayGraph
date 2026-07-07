"""Workspace state — agents operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403
from .agent_runtime_safety import (
    RUNTIME_OBSERVATION_SECRET_PATTERN,
    redact_runtime_observation_text,
    workspace_tool_command_block_reason as _runtime_command_block_reason,
    workspace_tool_host_exec_conda_block_reason as _runtime_conda_block_reason,
    workspace_tool_host_exec_diagnostic_block_reason as _runtime_diagnostic_block_reason,
    workspace_tool_host_exec_docker_block_reason as _runtime_docker_block_reason,
    workspace_tool_host_exec_git_block_reason as _runtime_git_block_reason,
    workspace_tool_host_exec_option_block_reason as _runtime_option_block_reason,
    workspace_tool_host_exec_ps_block_reason as _runtime_ps_block_reason,
    workspace_tool_host_exec_systemctl_block_reason as _runtime_systemctl_block_reason,
    workspace_tool_host_exec_top_is_bounded as _runtime_top_is_bounded,
    workspace_tool_host_exec_version_only as _runtime_version_only,
)
from .agent_runtime_observation import (
    observe_workspace_tool_job as _observe_workspace_tool_job,
    workspace_tool_job_snapshot as _workspace_tool_job_snapshot,
    workspace_tool_observe_options as _workspace_tool_observe_options,
    workspace_tool_run_snapshot as _workspace_tool_run_snapshot,
)
from .agent_runtime_control import (
    bind_workspace_tool_gpu_allocation as _bind_workspace_tool_gpu_allocation,
    control_workspace_tool_job as _control_workspace_tool_job,
)
from .agent_runtime_inputs import RUNTIME_INPUT_REF_PREFIXES, _agent_node_runtime_input_refs


class AgentsMixin:
    def cancel_agent_execution(self, execution_id: str) -> dict[str, Any]:
        """Signal a running agent execution to abort on its next iteration."""
        active = cancel_agent_run(str(execution_id or "").strip())
        return {
            "agent_execution_id": str(execution_id or "").strip(),
            "cancelled": active,
            "active": agent_run_is_active(str(execution_id or "").strip()),
        }

    def workspace_tool_runtime(self, workspace: dict[str, Any]) -> dict[str, Any]:
        return {
            "submit_job": lambda tool_id, arguments, context: self.submit_workspace_tool_job(
                workspace,
                tool_id,
                arguments,
                context,
            ),
            "bind_gpu": lambda arguments, context: self.bind_workspace_tool_gpu_allocation(
                workspace,
                arguments,
                context,
            ),
            "control_job": lambda tool_id, arguments, context: self.control_workspace_tool_job(
                workspace,
                tool_id,
                arguments,
                context,
            ),
        }


    def workspace_tool_command_block_reason(self, tool_id: str, command: str) -> str:
        return _runtime_command_block_reason(tool_id, command)


    def workspace_tool_host_exec_diagnostic_block_reason(self, command: str) -> str:
        return _runtime_diagnostic_block_reason(command)


    def workspace_tool_host_exec_ps_block_reason(self, args: list[str]) -> str:
        return _runtime_ps_block_reason(args)


    def workspace_tool_host_exec_option_block_reason(self, executable: str, args: list[str]) -> str:
        return _runtime_option_block_reason(executable, args)


    def workspace_tool_host_exec_top_is_bounded(self, args: list[str]) -> bool:
        return _runtime_top_is_bounded(args)


    def workspace_tool_host_exec_systemctl_block_reason(self, args: list[str]) -> str:
        return _runtime_systemctl_block_reason(args)


    def workspace_tool_host_exec_git_block_reason(self, args: list[str]) -> str:
        return _runtime_git_block_reason(args)


    def workspace_tool_host_exec_conda_block_reason(self, args: list[str]) -> str:
        return _runtime_conda_block_reason(args)


    def workspace_tool_host_exec_docker_block_reason(self, args: list[str]) -> str:
        return _runtime_docker_block_reason(args)


    def workspace_tool_host_exec_version_only(self, executable: str, args: list[str]) -> bool:
        return _runtime_version_only(executable, args)


    def workspace_tool_runtime_node_kind(self, tool_id: str) -> str:
        tool = str(tool_id or "").strip()
        if tool == "repo.clone":
            return "repo.clone"
        if tool in {"env.prepare", "env.create"}:
            return "env.prepare"
        return "run.command"


    def workspace_tool_env_create_command(
        self,
        args: dict[str, Any],
        config: dict[str, Any],
        workspace: dict[str, Any],
    ) -> str:
        command = str(args.get("command") or args.get("setup_command") or "").strip()
        if command:
            return command
        workspace_env = workspace.get("env") if isinstance(workspace.get("env"), dict) else {}
        env_name = str(args.get("env_name") or config.get("env_name") or workspace_env.get("name") or "").strip()
        if not env_name:
            return ""
        manager = str(args.get("env_manager") or config.get("env_manager") or workspace_env.get("manager") or "conda").strip().lower()
        python_version = str(args.get("python_version") or config.get("python_version") or workspace_env.get("python") or "").strip()
        if manager == "venv":
            workspace_dir = str(args.get("workspace_dir") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            target = env_name if env_name.startswith(("/", "~", ".")) else os.path.join(workspace_dir or ".", env_name)
            return "python3 -m venv " + shlex.quote(target)
        command_parts = ["conda", "create", "-y", "-n", shlex.quote(env_name)]
        if python_version:
            command_parts.append("python=" + shlex.quote(python_version))
        return " ".join(command_parts)


    def workspace_tool_observe_options(self, args: dict[str, Any]) -> dict[str, Any]:
        return _workspace_tool_observe_options(args)


    def workspace_tool_job_snapshot(self, job_id: str) -> dict[str, Any] | None:
        return _workspace_tool_job_snapshot(self, job_id)


    def workspace_tool_run_snapshot(self, workspace_id: str, run_id: str) -> dict[str, Any] | None:
        return _workspace_tool_run_snapshot(self, workspace_id, run_id)


    def observe_workspace_tool_job(
        self,
        *,
        workspace_id: str,
        job_id: str,
        run_id: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        return _observe_workspace_tool_job(
            self,
            workspace_id=workspace_id,
            job_id=job_id,
            run_id=run_id,
            options=options,
        )


    def submit_workspace_tool_job(
        self,
        workspace: dict[str, Any],
        tool_id: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        workspace_id = str(workspace.get("id") or "").strip()
        tool = str(tool_id or "").strip()
        args = arguments if isinstance(arguments, dict) else {}
        if not workspace_id:
            return {"status": "error", "tool": tool, "error": "workspace_id is required"}
        command = str(args.get("command") or args.get("cmd") or args.get("run_command") or args.get("setup_command") or "").strip()
        run_config = context.node_config("run.command") if context else {}
        preferred_node_kind = self.workspace_tool_runtime_node_kind(tool)
        if not command and tool == "job.run":
            command = str(run_config.get("run_command") or "").strip()
        if not command and tool == "env.prepare" and context:
            command = str(context.node_config("env.prepare").get("setup_command") or "").strip()
        if not command and tool == "env.create":
            command = self.workspace_tool_env_create_command(
                args,
                context.node_config("env.prepare") if context else {},
                workspace,
            )
        if tool == "repo.clone":
            source = context.source_payload() if context else {}
            repo_config = context.node_config("repo.clone") if context else {}
            repo_urls = source.get("repo_urls") if isinstance(source.get("repo_urls"), list) else []
            repo_url = str(args.get("repo_url") or repo_config.get("repo_url") or (repo_urls[0] if repo_urls else "")).strip()
            workspace_dir = str(args.get("workspace_dir") or args.get("cwd") or repo_config.get("workspace_dir") or source.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
            if not repo_url or not workspace_dir:
                return {
                    "status": "blocked",
                    "tool": tool,
                    "controlled": True,
                    "runtime_control": "workspace_job_queue",
                    "error": "repo_url and workspace_dir are required",
                }
        elif not command:
            return {"status": "blocked", "tool": tool, "error": "command is required"}
        block_reason = self.workspace_tool_command_block_reason(tool, command)
        if block_reason:
            return {
                "status": "blocked",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_queue",
                "command": command,
                "error": block_reason,
            }

        nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
        requested_node_id = str(args.get("node_id") or "").strip()
        node = next(
            (
                item for item in nodes
                if isinstance(item, dict)
                and requested_node_id
                and str(item.get("id") or "").strip() == requested_node_id
            ),
            None,
        )
        if node is None:
            node = next(
                (
                    item for item in nodes
                    if isinstance(item, dict) and str(item.get("kind") or "").strip() == preferred_node_kind
                ),
                None,
            )
        if node is None and preferred_node_kind != "run.command":
            node = {
                "id": safe_id(f"{preferred_node_kind}-agent-runtime"),
                "kind": preferred_node_kind,
                "title": WORKSPACE_NODE_LIBRARY.get(preferred_node_kind, {}).get("title") or "Agent 受控任务",
                "config": {},
                "handler": {"mode": "system", "name": "Agent Runtime", "output_key": "runtime_result"},
            }
        if node is None:
            node = {
                "id": safe_id(f"{tool}-agent-runtime"),
                "kind": "run.command",
                "title": "Agent 受控任务",
                "config": {},
                "handler": {"mode": "system", "name": "Agent Runtime", "output_key": "run_result"},
            }
        node_copy = copy.deepcopy(node)
        config = node_copy.get("config") if isinstance(node_copy.get("config"), dict) else {}
        config["server_id"] = str(args.get("server_id") or config.get("server_id") or run_config.get("server_id") or "auto").strip() or "auto"
        config["workspace_dir"] = str(args.get("cwd") or args.get("workspace_dir") or config.get("workspace_dir") or workspace.get("workspace_dir") or "").strip()
        if tool == "repo.clone":
            source = context.source_payload() if context else {}
            repo_config = context.node_config("repo.clone") if context else {}
            repo_urls = source.get("repo_urls") if isinstance(source.get("repo_urls"), list) else []
            config["repo_url"] = str(args.get("repo_url") or repo_config.get("repo_url") or (repo_urls[0] if repo_urls else "")).strip()
            config["repo_ref"] = str(args.get("repo_ref") or args.get("branch") or repo_config.get("repo_ref") or "").strip()
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        elif tool in {"env.prepare", "env.create"}:
            config["setup_command"] = command
            if args.get("env_name") is not None:
                config["env_name"] = str(args.get("env_name") or "").strip()
            if args.get("env_manager") is not None:
                config["env_manager"] = str(args.get("env_manager") or "").strip()
            if args.get("python_version") is not None:
                config["python_version"] = str(args.get("python_version") or "").strip()
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        else:
            config["run_command"] = command
        if tool == "host.exec":
            config["gpu_policy"] = "cpu"
            config["gpu_index"] = "none"
        elif tool not in {"repo.clone", "env.prepare", "env.create"}:
            if args.get("gpu_policy") is not None:
                config["gpu_policy"] = str(args.get("gpu_policy") or "").strip()
            elif not str(config.get("gpu_policy") or "").strip() and str(run_config.get("gpu_policy") or "").strip():
                config["gpu_policy"] = str(run_config.get("gpu_policy") or "").strip()
            if args.get("gpu_index") is not None:
                config["gpu_index"] = str(args.get("gpu_index") or "").strip()
            elif not str(config.get("gpu_index") or "").strip() and str(run_config.get("gpu_index") or "").strip():
                config["gpu_index"] = str(run_config.get("gpu_index") or "").strip()
        if args.get("env_name") is not None:
            config["env_name"] = str(args.get("env_name") or "").strip()
        if args.get("min_free_memory_gib") is not None:
            config["min_free_memory_gib"] = str(args.get("min_free_memory_gib") or "").strip()
        node_copy["config"] = config

        try:
            job_payload = self.workspace_node_job_payload(workspace, node_copy)
            job_payload["name"] = str(
                args.get("name")
                or f"{workspace.get('name') or workspace_id} · {tool}"
            )
            if command and tool != "repo.clone":
                job_payload["command"] = command
                job_payload["command_display"] = command
            if context is not None:
                job_payload["wait_for_idle"] = True
            elif "wait_for_idle" in args:
                job_payload["wait_for_idle"] = bool(args.get("wait_for_idle"))
            else:
                job_payload["wait_for_idle"] = False
            if tool == "host.exec":
                job_payload["gpu_index"] = "none"
                metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
                metadata["execution_mode"] = "cpu"
                runtime_binding = metadata.get("runtime_binding") if isinstance(metadata.get("runtime_binding"), dict) else {}
                runtime_binding["gpu_policy"] = "cpu"
                runtime_binding["gpu_index"] = "none"
                runtime_binding["execution_mode"] = "cpu"
                metadata["runtime_binding"] = runtime_binding
                job_payload["metadata"] = metadata
            observe_options = self.workspace_tool_observe_options(args)
            metadata = job_payload.get("metadata") if isinstance(job_payload.get("metadata"), dict) else {}
            metadata.update(
                {
                    "tool_id": tool,
                    "agent_runtime_tool": True,
                    "runtime_control": "workspace_job_queue",
                    "submitted_by": "agent_tool",
                }
            )
            job_payload["metadata"] = metadata
            job = self.create_job(job_payload, publish_events=False)
            run = self.register_workspace_execution_run(
                workspace_id,
                kind="node",
                trigger="agent_tool",
                summary=f"Agent 工具任务 · {tool}",
                jobs=[job],
            )
            with self.lock:
                persisted = self.workspace_by_id(workspace_id)
                if persisted and isinstance(persisted.get("runs"), list):
                    workspace["runs"] = copy.deepcopy(persisted["runs"])
            result = {
                "status": "submitted",
                "tool": tool,
                "controlled": True,
                "runtime_control": "workspace_job_queue",
                "runtime_side_effect": "workspace_job",
                "observed": False,
                "job": public_job_payload(job),
                "job_id": str(job.get("id") or "").strip(),
                "run": copy.deepcopy(run),
                "run_id": str(run.get("id") or "").strip(),
                "message": "任务已通过受控 workspace job 队列提交。",
            }
            if observe_options.get("enabled") and safe_float(observe_options.get("seconds"), 0.0) > 0:
                observation = self.observe_workspace_tool_job(
                    workspace_id=workspace_id,
                    job_id=str(job.get("id") or "").strip(),
                    run_id=str(run.get("id") or "").strip(),
                    options=observe_options,
                )
                result.update(observation)
                result["tool"] = tool
                result["controlled"] = True
                result["runtime_control"] = "workspace_job_queue"
                result["runtime_side_effect"] = "workspace_job"
                with self.lock:
                    persisted = self.workspace_by_id(workspace_id)
                    if persisted and isinstance(persisted.get("runs"), list):
                        workspace["runs"] = copy.deepcopy(persisted["runs"])
            return result
        except Exception as exc:  # noqa: BLE001 - tools report errors inside the agent loop.
            return {"status": "error", "tool": tool, "controlled": True, "error": str(exc)}


    def bind_workspace_tool_gpu_allocation(
        self,
        workspace: dict[str, Any],
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        return _bind_workspace_tool_gpu_allocation(self, workspace, arguments, context)


    def control_workspace_tool_job(
        self,
        workspace: dict[str, Any],
        tool_id: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        return _control_workspace_tool_job(self, workspace, tool_id, arguments, context)


    def _execute_agent_on_mutable_workspace(
        self,
        workspace: dict[str, Any],
        agent: dict[str, Any],
        *,
        input_text: str,
        requested_node_kind: str = "",
        execute_llm: bool = True,
        node: dict[str, Any] | None = None,
        mapped_inputs: dict[str, Any] | None = None,
        output_key: str = "",
        output_format: str = "",
        max_iterations: int | None = None,
        timeout_seconds: float | None = None,
        run_id: str = "",
    ) -> dict[str, Any]:
        workspace_id = str(workspace.get("id") or "").strip()
        execution_run_id = str(run_id or "").strip()
        tools = normalize_workspace_tools(workspace.get("tools"), existing=workspace.get("tools"))
        model_config = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
        routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
        workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
        agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
        effective_profile_id = workspace_profile_id
        if routing_mode == "agent_override" and agent_profile_id:
            effective_profile_id = agent_profile_id

        if not execute_llm or not input_text:
            return {
                "success": False,
                "error": "agent execution requires input text",
                "final_answer": "",
            }
        if not effective_profile_id:
            return {
                "success": False,
                "error": "No provider profile configured for this workspace/agent",
                "final_answer": "",
            }
        profile = self.provider_profile_by_id(effective_profile_id)
        if not profile:
            return {
                "success": False,
                "error": "Provider profile not found",
                "final_answer": "",
            }
        from ..registry_pkg.provider_profiles import provider_profile_health

        health = provider_profile_health(profile)
        if not health.get("ready"):
            missing_fields = [
                str(item or "").strip()
                for item in (health.get("missing_fields") if isinstance(health.get("missing_fields"), list) else [])
                if str(item or "").strip()
            ]
            detail = ", ".join(missing_fields) if missing_fields else "profile is not ready"
            return {
                "success": False,
                "error": f"Provider profile is not ready: {detail}",
                "final_answer": "",
            }

        tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
        allowed_tool_ids = [
            tid for tid in parse_tag_list(agent.get("tools", []))
            if tid in tool_map
        ]
        allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]
        llm_client = LLMClient(profile)
        tool_executor = create_workspace_tool_executor(
            workspace,
            statuses=copy.deepcopy(self.statuses),
            jobs=copy.deepcopy(self.jobs),
            provider_profiles=copy.deepcopy(getattr(self, "provider_profiles", [])),
            tool_definitions=copy.deepcopy(getattr(self, "tool_definitions", [])),
            runtime=self.workspace_tool_runtime(workspace),
        )
        agent_config = dict(agent)
        if max_iterations is not None:
            agent_config = {**agent_config, "max_iterations": max_iterations}
        execution_id = make_agent_execution_id()
        cancel_check = register_agent_cancel(execution_id)
        node_kind = str(requested_node_kind or (node or {}).get("kind") or "").strip()
        trace_events: list[dict[str, Any]] = []

        def on_agent_event(event_type: str, event_payload: dict[str, Any]) -> None:
            if isinstance(event_payload, dict) and event_payload:
                trace_events.append(copy.deepcopy(event_payload))
            self.publish_event(
                event_type,
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    **(event_payload if isinstance(event_payload, dict) else {}),
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                    "chat": False,
                },
            )

        def on_agent_step(step: Any) -> None:
            step_payload = step.to_dict() if hasattr(step, "to_dict") else step
            self.publish_event(
                "agent.step.created",
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    "step": copy.deepcopy(step_payload) if isinstance(step_payload, dict) else {},
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                },
            )

        def on_agent_delta(delta: str, accumulated: str) -> None:
            if not str(accumulated or "").strip():
                return
            self.publish_event(
                "agent.message.delta",
                workspace_id=workspace_id,
                run_id=execution_run_id,
                agent_execution_id=execution_id,
                payload={
                    "delta": str(delta or ""),
                    "accumulated": str(accumulated or ""),
                    "node_id": str((node or {}).get("id") or "").strip(),
                    "node_kind": node_kind,
                    "agent_id": str(agent.get("id") or "").strip(),
                    "chat": False,
                },
            )

        executor = AgentExecutor(
            agent=agent_config,
            llm_client=llm_client,
            tools=allowed_tools,
            tool_executor=tool_executor,
            step_callback=on_agent_step,
            token_callback=on_agent_delta,
            event_callback=on_agent_event,
            timeout_seconds=timeout_seconds,
            cancel_check=cancel_check,
        )
        handler = (node or {}).get("handler") if isinstance((node or {}).get("handler"), dict) else {}
        effective_output_key = str(output_key or handler.get("output_key") or (node or {}).get("output_key") or "").strip()
        effective_output_format = str(
            output_format or handler.get("output_format") or (node or {}).get("output_format") or ""
        ).strip()
        try:
            execution_result = executor.run(
                input_text,
                context={
                    "workspace_id": workspace_id,
                    "workspace_name": workspace.get("name", ""),
                    "source_type": (workspace.get("source") or {}).get("type", "") if isinstance(workspace.get("source"), dict) else "",
                    "node_kind": node_kind,
                    "output_key": effective_output_key,
                    "output_format": effective_output_format,
                    "node_goal": str((node or {}).get("title") or node_kind or "").strip(),
                    "mapped_inputs": mapped_inputs if isinstance(mapped_inputs, dict) else {},
                },
            )
        finally:
            release_agent_cancel(execution_id)
        result = execution_result.to_dict()
        result["id"] = execution_id
        result["trace_events"] = normalize_agent_trace_events(trace_events)
        validation = validate_agent_output(
            output_key=effective_output_key,
            output_format=effective_output_format,
            final_answer=execution_result.final_answer,
        )
        result["output_validation"] = validation
        if execution_result.success and isinstance(node, dict):
            if effective_output_key and not collect_agent_step_output(workspace, node, output_key=effective_output_key)[1]:
                apply_final_answer_output(
                    workspace,
                    node,
                    output_key=effective_output_key,
                    final_answer=execution_result.final_answer,
                    output_format=effective_output_format,
                    validation=validation,
                )
            artifacts, output_value = collect_agent_step_output(workspace, node, output_key=effective_output_key)
            result["artifacts"] = artifacts
            if output_value:
                result["output_value"] = output_value
        self.publish_event(
            "agent.completed" if execution_result.success else "agent.failed",
            workspace_id=workspace_id,
            run_id=execution_run_id,
            agent_execution_id=execution_id,
            payload={
                "execution": copy.deepcopy(result),
                "node_id": str((node or {}).get("id") or "").strip(),
                "node_kind": node_kind,
                "agent_id": str(agent.get("id") or "").strip(),
            },
        )
        return result


    def execute_workspace_agent_node(
        self,
        workspace_id: str,
        node: dict[str, Any],
        *,
        run_context: ExecutionRunContext | None = None,
        input_text: str = "",
    ) -> StepResult:
        workspace_id = str(workspace_id or "").strip()
        node = copy.deepcopy(node) if isinstance(node, dict) else {}
        handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
        agent_id = str(handler.get("agent_id") or "").strip()
        node_kind = str(node.get("kind") or "").strip()
        output_key = str(handler.get("output_key") or node.get("output_key") or "").strip()
        output_format = str(handler.get("output_format") or node.get("output_format") or "").strip()
        max_iterations_raw = handler.get("max_iterations")
        max_iterations = safe_int(max_iterations_raw, 0) if max_iterations_raw not in (None, "") else None
        if max_iterations is not None and max_iterations <= 0:
            max_iterations = None
        timeout_raw = handler.get("timeout_seconds")
        if timeout_raw in (None, ""):
            timeout_raw = node.get("timeout_seconds")
        timeout_seconds = float(timeout_raw) if timeout_raw not in (None, "") and safe_int(timeout_raw, 0) > 0 else None

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            workspace = copy.deepcopy(current)
            tools = normalize_workspace_tools(workspace.get("tools"), existing=workspace.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(workspace.get("agents"), existing=workspace.get("agents"), tool_ids=tool_ids)
            agent = next((item for item in agents if item["id"] == agent_id), None)
            if not agent:
                return StepResult(status="blocked", executor="agent", reason=f"agent not found: {agent_id or 'unset'}")
            if max_iterations is None:
                agent_iterations = agent.get("max_iterations")
                if agent_iterations not in (None, ""):
                    parsed = safe_int(agent_iterations, 0)
                    max_iterations = parsed if parsed > 0 else None

        context = run_context or ExecutionRunContext(workspace_id=workspace_id)
        workspace_nodes = workspace.get("nodes") if isinstance(workspace.get("nodes"), list) else []
        node_index = next(
            (index for index, item in enumerate(workspace_nodes) if isinstance(item, dict) and str(item.get("id") or "").strip() == str(node.get("id") or "").strip()),
            0,
        )
        contract = workspace_io_contract_for_kind(node_kind, node_index)
        if not output_key:
            output_key = str(contract.get("output_key") or "").strip()
        input_mapping = workspace_io_input_mapping(node, contract, node_index)
        input_data = workspace_input_data_for_context(workspace)
        automation = workspace.get("automation") if isinstance(workspace.get("automation"), dict) else {}
        execution_context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
        persisted_outputs = execution_context.get("outputs") if isinstance(execution_context.get("outputs"), dict) else {}
        context_outputs = {**copy.deepcopy(persisted_outputs), **copy.deepcopy(context.outputs)}
        node_config = node.get("config") if isinstance(node.get("config"), dict) else {}
        mapped_inputs = resolve_mapped_inputs(
            input_mapping,
            input_data=input_data,
            context_outputs=context_outputs,
            previous_output=context.previous_output,
            node_config=node_config,
        )
        input_refs, input_blockers = _agent_node_runtime_input_refs(
            workspace,
            node,
            node_index=node_index,
            input_mapping=input_mapping,
            mapped_inputs=mapped_inputs,
            context_outputs=context_outputs,
            previous_output=context.previous_output,
            enforce_previous_output=context.kind == "workflow",
        )
        if input_blockers:
            first = input_blockers[0]
            node_title = str(node.get("title") or node_kind or "Agent 节点").strip()
            detail = f"{node_title} 的输入 {first.get('name') or ''} 未就绪：{first.get('detail') or 'input_mapping blocked'}"
            return StepResult(
                status="blocked",
                executor="agent",
                output_key=output_key,
                mapped_inputs=summarize_mapped_inputs(mapped_inputs),
                detail=detail,
                reason="input_mapping_blocked",
                validation={
                    "status": "failed",
                    "code": "input_mapping_blocked",
                    "errors": [str(item.get("detail") or item.get("code") or "input_mapping blocked") for item in input_blockers],
                    "input_refs": copy.deepcopy(input_refs),
                },
            )
        if not input_text:
            goal_text = str(input_data.get("goal_text") or "").strip()
            input_text = build_agent_node_input_text(
                node_kind=node_kind,
                node_title=str(node.get("title") or node_kind or "node").strip(),
                output_key=output_key,
                mapped_inputs=mapped_inputs,
                goal_text=goal_text,
                node_config=node_config,
            )

        def agent_executor(_workspace_id: str, _agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            execution = self._execute_agent_on_mutable_workspace(
                workspace,
                agent,
                input_text=str(payload.get("input") or input_text or "").strip(),
                requested_node_kind=str(payload.get("node_kind") or node_kind or "").strip(),
                execute_llm=bool(payload.get("execute_llm", True)),
                node=node,
                mapped_inputs=payload.get("mapped_inputs") if isinstance(payload.get("mapped_inputs"), dict) else mapped_inputs,
                output_key=str(payload.get("output_key") or output_key or "").strip(),
                output_format=output_format,
                max_iterations=max_iterations,
                timeout_seconds=timeout_seconds,
                run_id=context.run_id,
            )
            return {"execution": execution}

        step_result = run_agent_node(
            workspace,
            node,
            context,
            agent_executor=agent_executor,
            mapped_inputs=mapped_inputs,
            input_text=input_text,
        )
        with self.lock:
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            existing = self.workspaces[index]
            updated = normalize_workspace_payload(workspace, existing=existing)
            self.workspaces[index] = updated
        self.save_workspaces()
        return step_result


    def debug_workspace_agent(self, workspace_id: str, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        requested_agent_id = safe_id(str(agent_id or "").strip()) if str(agent_id or "").strip() else ""
        requested_payload = payload if isinstance(payload, dict) else {}
        input_text = str(requested_payload.get("input") or requested_payload.get("text") or "").strip()
        requested_node_id = str(requested_payload.get("node_id") or "").strip()
        requested_node_kind = str(requested_payload.get("node_kind") or "").strip()
        requested_tool_ids = parse_tag_list(requested_payload.get("tool_ids", []))
        execute_llm = bool(requested_payload.get("execute_llm") or False)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            agent = next((item for item in agents if item["id"] == requested_agent_id), None)
            if not agent:
                raise ValueError("agent not found")
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat
            preview_workspace = self.workspace_public_payload(preview_workspace)
            target_node: dict[str, Any] | None = None
            workspace_nodes = preview_workspace.get("nodes") if isinstance(preview_workspace.get("nodes"), list) else []
            if requested_node_id:
                target_node = next(
                    (
                        item for item in workspace_nodes
                        if isinstance(item, dict) and str(item.get("id") or "").strip() == requested_node_id
                    ),
                    None,
                )
            elif requested_node_kind:
                target_node = next(
                    (
                        item for item in workspace_nodes
                        if isinstance(item, dict)
                        and str(item.get("kind") or "").strip() == requested_node_kind
                        and str((item.get("handler") or {}).get("agent_id") or "").strip() == requested_agent_id
                    ),
                    None,
                )

        debug = build_workspace_agent_debug(
            preview_workspace,
            agent,
            input_text=input_text,
            requested_node_kind=requested_node_kind or str((target_node or {}).get("kind") or "").strip(),
            requested_tool_ids=requested_tool_ids,
        )

        result = {"debug": debug}

        if execute_llm and input_text:
            if target_node and str((target_node.get("handler") or {}).get("mode") or "").strip().lower() == "agent":
                step_result = self.execute_workspace_agent_node(
                    workspace_id,
                    copy.deepcopy(target_node),
                    input_text=input_text,
                )
                result["step"] = step_result.as_dict()
                result["execution"] = {
                    "id": step_result.agent_execution_id,
                    "success": step_result.status in {"completed", "warning"},
                    "steps": step_result.agent_steps,
                    "artifacts": step_result.artifacts,
                    "output_value": None,
                    "error": "" if step_result.status in {"completed", "warning"} else step_result.detail,
                    "final_answer": step_result.detail if step_result.status in {"completed", "warning"} else "",
                }
                if step_result.output_key:
                    refreshed = self.workspace_by_id(workspace_id)
                    if refreshed:
                        outputs = (
                            refreshed.get("automation", {})
                            .get("execution_context", {})
                            .get("outputs", {})
                        )
                        if isinstance(outputs, dict) and step_result.output_key in outputs:
                            result["execution"]["output_value"] = outputs.get(step_result.output_key)
            else:
                execution_payload = self._execute_agent_on_mutable_workspace(
                    preview_workspace,
                    agent,
                    input_text=input_text,
                    requested_node_kind=requested_node_kind,
                    execute_llm=True,
                )
                result["execution"] = execution_payload
                if execution_payload.get("success"):
                    with self.lock:
                        index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
                        if index >= 0:
                            existing = self.workspaces[index]
                            updated = normalize_workspace_payload(preview_workspace, existing=existing)
                            self.workspaces[index] = updated
                    self.save_workspaces()

        return result
