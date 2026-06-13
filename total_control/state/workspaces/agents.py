"""Workspace state — agents operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class AgentsMixin:
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
    ) -> dict[str, Any]:
        workspace_id = str(workspace.get("id") or "").strip()
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
        if not profile or not profile.get("api_key"):
            return {
                "success": False,
                "error": "Provider profile not found or API key not configured",
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
        )
        agent_config = dict(agent)
        if max_iterations is not None:
            agent_config = {**agent_config, "max_iterations": max_iterations}
        executor = AgentExecutor(
            agent=agent_config,
            llm_client=llm_client,
            tools=allowed_tools,
            tool_executor=tool_executor,
        )
        node_kind = str(requested_node_kind or (node or {}).get("kind") or "").strip()
        handler = (node or {}).get("handler") if isinstance((node or {}).get("handler"), dict) else {}
        effective_output_key = str(output_key or handler.get("output_key") or (node or {}).get("output_key") or "").strip()
        effective_output_format = str(
            output_format or handler.get("output_format") or (node or {}).get("output_format") or ""
        ).strip()
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
        result = execution_result.to_dict()
        result["id"] = make_agent_execution_id()
        if execution_result.success and isinstance(node, dict):
            if effective_output_key and not collect_agent_step_output(workspace, node, output_key=effective_output_key)[1]:
                apply_final_answer_output(
                    workspace,
                    node,
                    output_key=effective_output_key,
                    final_answer=execution_result.final_answer,
                    output_format=effective_output_format,
                )
            artifacts, output_value = collect_agent_step_output(workspace, node, output_key=effective_output_key)
            result["artifacts"] = artifacts
            if output_value:
                result["output_value"] = output_value
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

        def debug_runner(_workspace_id: str, _agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
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
            )
            return {"execution": execution}

        step_result = run_agent_node(
            workspace,
            node,
            context,
            debug_runner=debug_runner,
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
