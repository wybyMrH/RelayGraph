"""Workspace state — chat operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class ChatMixin:
    def append_workspace_chat(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("text is required")
        role = str(payload.get("role") or "user").strip().lower()
        if role not in {"user", "assistant", "system"}:
            role = "user"
        requested_agent_id = safe_id(str(payload.get("agent_id") or "").strip()) if str(payload.get("agent_id") or "").strip() else ""
        use_llm = bool(payload.get("use_llm") or False)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            agent_id = requested_agent_id if any(agent["id"] == requested_agent_id for agent in agents) else ""
            if agent_id:
                model["chat_agent_id"] = agent_id
            agent_name = workspace_agent_name({"agents": agents}, agent_id)
            user_message = make_workspace_chat_message(role, text, agent_id=agent_id, agent_name=agent_name)
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat + [user_message]
            preview_workspace_public = self.workspace_public_payload(preview_workspace)

        # Generate reply - either from LLM or from placeholder
        reply_text = ""
        execution_info = None

        if use_llm and agent_id:
            # Try to use actual LLM
            model_config = preview_workspace.get("model") if isinstance(preview_workspace.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()

            agent = next((item for item in agents if item["id"] == agent_id), None)
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip() if agent else ""
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id

            if effective_profile_id and agent:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    # Get allowed tools
                    tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]

                    # Create and execute agent
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                    )
                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                    )

                    # Build context from chat history
                    chat_context = []
                    for msg in chat[-10:]:  # Last 10 messages as context
                        msg_role = str(msg.get("role") or "user")
                        msg_text = str(msg.get("text") or "")
                        if msg_text:
                            chat_context.append(f"{msg_role}: {msg_text}")

                    execution_result = executor.run(text, context={
                        "workspace_id": workspace_id,
                        "workspace_name": preview_workspace.get("name", ""),
                        "chat_history": chat_context,
                    })

                    if execution_result.success:
                        reply_text = execution_result.final_answer
                    else:
                        reply_text = f"[Agent execution failed: {execution_result.error}]"

                    execution_info = execution_result.to_dict()

        # If no LLM used or failed, use placeholder reply
        if not reply_text:
            reply_text = build_workspace_chat_reply(preview_workspace, text, agent_id=agent_id)

        assistant_message = make_workspace_chat_message("assistant", reply_text, agent_id=agent_id, agent_name=agent_name)

        with self.lock:
            merged = copy.deepcopy(current)
            merged["agents"] = agents
            merged["tools"] = tools
            merged["model"] = model
            merged["chat"] = chat + [user_message, assistant_message]
            updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
            result_workspace = self.workspace_public_payload(updated)

        self.save_workspaces()

        result = {
            "workspace": result_workspace,
            "messages": [user_message, assistant_message],
        }
        if execution_info:
            result["execution"] = execution_info

        return result
