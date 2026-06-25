"""Workspace state — debug operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class DebugMixin:
    def debug_agent_definition(self, agent_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        requested_agent_id = safe_id(str(agent_id or "").strip()) if str(agent_id or "").strip() else ""
        requested_payload = payload if isinstance(payload, dict) else {}
        template_id = str(requested_payload.get("template_id") or "").strip()
        input_text = str(requested_payload.get("input") or requested_payload.get("text") or "").strip()
        requested_node_kind = str(requested_payload.get("node_kind") or "").strip()
        requested_tool_ids = parse_tag_list(requested_payload.get("tool_ids", []))
        execute_llm = bool(requested_payload.get("execute_llm") or False)
        output_format = str(requested_payload.get("output_format") or "").strip().lower()
        if output_format not in {"", "text", "json"}:
            output_format = ""
        max_iterations_raw = requested_payload.get("max_iterations")
        max_iterations = safe_int(max_iterations_raw, 0) if max_iterations_raw not in (None, "") else 0
        timeout_raw = requested_payload.get("timeout_seconds")
        timeout_seconds = float(timeout_raw) if timeout_raw not in (None, "") and safe_int(timeout_raw, 0) > 0 else 0.0

        with self.lock:
            agent = self.agent_definition_by_id(requested_agent_id)
            if not agent:
                raise ValueError("agent definition not found")
            template = self.workflow_template_by_id(template_id) if template_id else None
            if template:
                preview_workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=template,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
            else:
                inputs = normalize_workspace_inputs(
                    requested_payload.get("inputs") if isinstance(requested_payload.get("inputs"), dict) else requested_payload
                )
                debug_source_type = source_type_for_chain(inputs.get("source_mode") or "idea")
                template_payload = {
                    "id": f"debug-{requested_agent_id or 'agent'}",
                    "name": str(requested_payload.get("template_name") or "Agent 调试预览").strip() or "Agent 调试预览",
                    "brief": str(requested_payload.get("brief") or inputs.get("goal_text") or f"调试 {agent.get('name') or requested_agent_id}").strip(),
                    "source_type": inputs.get("source_mode") or "idea",
                    "repo_url": parse_line_list(inputs.get("repo_urls", []))[0] if parse_line_list(inputs.get("repo_urls", [])) else "",
                    "paper_url": parse_line_list(inputs.get("paper_urls", []))[0] if parse_line_list(inputs.get("paper_urls", [])) else "",
                    "idea_text": str(inputs.get("goal_text") or requested_payload.get("brief") or "").strip(),
                    "references": parse_line_list(inputs.get("references", [])),
                    "workspace_dir": str(requested_payload.get("workspace_dir") or "").strip(),
                    "env_name": str(requested_payload.get("env_name") or "").strip(),
                    "env_manager": str(requested_payload.get("env_manager") or "conda").strip() or "conda",
                    "python_version": str(requested_payload.get("python_version") or "").strip(),
                    "model": {
                        "chat_agent_id": requested_agent_id,
                        "provider_profile_id": str(requested_payload.get("provider_profile_id") or "").strip(),
                        "routing_mode": str(requested_payload.get("routing_mode") or "agent_override").strip() or "agent_override",
                    },
                    "nodes": [
                        {
                            "id": "debug-node",
                            "kind": requested_node_kind or f"source.{debug_source_type}",
                            "title": str(requested_payload.get("node_title") or "调试节点").strip() or "调试节点",
                            "handler": {
                                "agent_id": requested_agent_id,
                                "name": str(agent.get("name") or requested_agent_id).strip(),
                            },
                            "config": {
                                "goal": str(requested_payload.get("node_goal") or inputs.get("goal_text") or "").strip(),
                            },
                        }
                    ],
                }
                debug_template = normalize_workflow_template(
                    template_payload,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )
                preview_workspace = normalize_workspace_instance_from_template(
                    requested_payload,
                    template=debug_template,
                    agent_definitions=self.agent_definitions,
                    tool_definitions=self.tool_definitions,
                )

            preview_workspace["agents"] = copy.deepcopy(self.agent_definitions)
            preview_workspace["tools"] = copy.deepcopy(self.tool_definitions)
            model = normalize_workspace_model(preview_workspace.get("model"), existing=preview_workspace.get("model"))
            if requested_payload.get("provider_profile_id"):
                model["provider_profile_id"] = str(requested_payload.get("provider_profile_id") or "").strip()
            if requested_payload.get("routing_mode"):
                model["routing_mode"] = str(requested_payload.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            if not str(model.get("chat_agent_id") or "").strip():
                model["chat_agent_id"] = requested_agent_id
            preview_workspace["model"] = model
            preview_workspace["chat"] = normalize_workspace_chat(
                requested_payload.get("chat") if "chat" in requested_payload else preview_workspace.get("chat"),
                existing=preview_workspace.get("chat"),
            )
            preview_workspace_public = self.workspace_public_payload(preview_workspace)

        debug = build_workspace_agent_debug(
            preview_workspace_public,
            agent,
            input_text=input_text,
            requested_node_kind=requested_node_kind,
            requested_tool_ids=requested_tool_ids,
        )
        result = {
            "debug": debug,
            "workspace": preview_workspace_public,
            "agent_definition": copy.deepcopy(agent),
            "effective_config": {
                "max_iterations": max_iterations or safe_int(agent.get("max_iterations"), 0),
                "timeout_seconds": timeout_seconds or float(agent.get("timeout_seconds") or 0),
                "output_format": output_format or str(agent.get("output_format") or "").strip(),
            },
        }

        if execute_llm and input_text:
            model_config = preview_workspace_public.get("model") if isinstance(preview_workspace_public.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id

            if effective_profile_id:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    tool_map = {
                        t.get("id"): t
                        for t in preview_workspace_public.get("tools", [])
                        if isinstance(t, dict) and t.get("id")
                    }
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map and (not requested_tool_ids or tid in requested_tool_ids)
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace_public,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                    )
                    executor = AgentExecutor(
                        agent={**agent, **({"max_iterations": max_iterations} if max_iterations > 0 else {})},
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                        timeout_seconds=timeout_seconds or float(agent.get("timeout_seconds") or 0) or None,
                    )
                    execution_result = executor.run(
                        input_text,
                        context={
                            "workspace_id": str(preview_workspace_public.get("id") or "").strip(),
                            "workspace_name": preview_workspace_public.get("name", ""),
                            "source_type": preview_workspace_public.get("source", {}).get("type", ""),
                            "node_kind": requested_node_kind,
                            "output_format": output_format or str(agent.get("output_format") or "").strip(),
                        },
                    )
                    result["execution"] = execution_result.to_dict()
                else:
                    result["execution"] = {
                        "success": False,
                        "error": "Provider profile not found or API key not configured",
                        "final_answer": "",
                    }
            else:
                result["execution"] = {
                    "success": False,
                    "error": "No provider profile configured for this agent/template",
                    "final_answer": "",
                }

        return result
