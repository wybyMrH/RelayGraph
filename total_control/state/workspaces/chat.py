"""Workspace state — chat operations."""

from __future__ import annotations

from ._deps import *  # noqa: F403

class ChatMixin:
    CONTEXT_REFLECTION_TRIGGERS = (
        "必须",
        "不要",
        "不能",
        "只负责",
        "保持",
        "注意",
        "边界",
        "约束",
        "后续",
        "以后",
        "真机",
        "简洁",
        "冗余",
        "配置",
        "驾驶舱",
        "must",
        "should",
        "only",
        "keep",
        "avoid",
        "do not",
        "don't",
    )

    def _chat_agent_execution_trace(
        self,
        execution_id: str,
        execution_info: dict[str, Any],
        *,
        provider_profile_id: str = "",
        success: bool = False,
    ) -> dict[str, Any]:
        # 构造可回放的对话 Agent trace
        return build_agent_execution_trace(
            execution_id,
            model=str(execution_info.get("model") or ""),
            provider_profile_id=provider_profile_id,
            total_tokens=int(execution_info.get("total_tokens") or 0),
            total_steps=int(execution_info.get("total_steps") or 0),
            success=success,
            error=str(execution_info.get("error") or ""),
            trace_events=execution_info.get("trace_events") if isinstance(execution_info.get("trace_events"), list) else [],
            agent_steps=execution_info.get("steps") if isinstance(execution_info.get("steps"), list) else [],
        )

    def _workspace_chat_context_reflection(
        self,
        workspace: dict[str, Any],
        user_text: str,
        assistant_text: str,
        *,
        assistant_message_id: str,
        user_message_id: str = "",
        agent_execution_id: str = "",
    ) -> dict[str, Any]:
        del assistant_text
        inputs = workspace.get("inputs") if isinstance(workspace.get("inputs"), dict) else {}
        existing_blocks = {
            str(item or "").strip()
            for item in (inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])
            if str(item or "").strip()
        }
        candidates: list[str] = []
        for raw in re.split(r"[\r\n]+|(?<=[。！？!?；;])\s*", str(user_text or "")):
            line = re.sub(r"^[\s\-*•·0-9.、]+", "", str(raw or "").strip())
            if len(line) < 8:
                continue
            lower = line.lower()
            if not any(trigger in lower or trigger in line for trigger in self.CONTEXT_REFLECTION_TRIGGERS):
                continue
            if line in existing_blocks:
                continue
            candidates.append(compact_workspace_command(line, limit=180))
            if len(candidates) >= 3:
                break
        if not candidates:
            return {}
        summary = "；".join(candidates)
        if summary in existing_blocks:
            return {}
        high_confidence_markers = {"必须", "不要", "不能", "只负责", "must", "only", "do not", "don't"}
        confidence = 0.82 if any(marker in summary.lower() or marker in summary for marker in high_confidence_markers) else 0.68
        return normalize_workspace_context_reflection(
            {
                "summary": summary,
                "status": "suggested",
                "confidence": confidence,
                "source": {
                    "type": "chat",
                    "message_id": assistant_message_id,
                    "user_message_id": user_message_id,
                    "agent_execution_id": agent_execution_id,
                },
                "created_at": now_iso(),
            }
        )

    def accept_workspace_context_reflection(
        self,
        workspace_id: str,
        message_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace_id = str(workspace_id or "").strip()
        message_id = str(message_id or "").strip()
        requested = payload if isinstance(payload, dict) else {}
        if not workspace_id or not message_id:
            raise ValueError("workspace_id and message_id are required")
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            target_index = next((idx for idx, item in enumerate(chat) if str(item.get("id") or "") == message_id), -1)
            if target_index < 0:
                raise ValueError("chat message not found")
            target = chat[target_index]
            reflection = normalize_workspace_context_reflection(target.get("context_reflection"))
            summary = str(requested.get("summary") or reflection.get("summary") or "").strip()
            if not summary:
                raise ValueError("context reflection not found")
            inputs = normalize_workspace_inputs(current.get("inputs"), existing=current.get("inputs"))
            context_blocks = [
                str(item or "").strip()
                for item in (inputs.get("context_blocks") if isinstance(inputs.get("context_blocks"), list) else [])
                if str(item or "").strip()
            ]
            if summary not in context_blocks:
                context_blocks.append(summary)
            inputs["context_blocks"] = context_blocks
            accepted_reflection = normalize_workspace_context_reflection(
                {
                    **reflection,
                    "summary": summary,
                    "status": "accepted",
                    "accepted_at": now_iso(),
                    "accepted_context_block": summary,
                },
                existing=reflection,
            )
            updated_message = normalize_workspace_chat_message(
                {
                    **target,
                    "context_reflection": accepted_reflection,
                    "updated_at": now_iso(),
                },
                existing=target,
            )
            chat[target_index] = updated_message
            merged = copy.deepcopy(current)
            merged["inputs"] = inputs
            merged["chat"] = chat
            updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                raise ValueError("workspace not found")
            self.workspaces[index] = updated
            result_workspace = self.workspace_public_payload(updated)

        self.save_workspaces()
        self.publish_event(
            "workspace.updated",
            workspace_id=workspace_id,
            payload={
                "workspace": copy.deepcopy(result_workspace),
                "message": copy.deepcopy(updated_message),
                "context_reflection": copy.deepcopy(accepted_reflection),
            },
        )
        return {
            "workspace": result_workspace,
            "message": updated_message,
            "context_reflection": accepted_reflection,
            "context_block": summary,
        }

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
        if bool(payload.get("stream") or False):
            return self.append_workspace_chat_stream(
                workspace_id,
                {
                    **payload,
                    "text": text,
                    "role": role,
                    "agent_id": requested_agent_id,
                    "use_llm": use_llm,
                },
            )

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
        effective_profile_id = ""

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
                        runtime=self.workspace_tool_runtime(preview_workspace),
                    )
                    execution_id = make_agent_execution_id()
                    cancel_check = register_agent_cancel(execution_id)
                    chat_timeout_raw = agent.get("timeout_seconds")
                    chat_timeout = float(chat_timeout_raw) if chat_timeout_raw not in (None, "") and safe_int(chat_timeout_raw, 0) > 0 else None
                    trace_events: list[dict[str, Any]] = []

                    def on_agent_event(event_type: str, event_payload: dict[str, Any]) -> None:
                        if isinstance(event_payload, dict) and event_payload:
                            trace_events.append(copy.deepcopy(event_payload))
                        self.publish_event(
                            event_type,
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                **(event_payload if isinstance(event_payload, dict) else {}),
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    def on_agent_step(step: Any) -> None:
                        step_payload = step.to_dict() if hasattr(step, "to_dict") else step
                        self.publish_event(
                            "agent.step.created",
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                "step": copy.deepcopy(step_payload) if isinstance(step_payload, dict) else {},
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    def on_agent_delta(delta: str, accumulated: str) -> None:
                        if not str(accumulated or "").strip():
                            return
                        self.publish_event(
                            "agent.message.delta",
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                "delta": str(delta or ""),
                                "accumulated": str(accumulated or ""),
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                        step_callback=on_agent_step,
                        token_callback=on_agent_delta,
                        event_callback=on_agent_event,
                        timeout_seconds=chat_timeout,
                        cancel_check=cancel_check,
                    )

                    # Build context from chat history
                    chat_context = []
                    for msg in chat[-10:]:  # Last 10 messages as context
                        msg_role = str(msg.get("role") or "user")
                        msg_text = str(msg.get("text") or "")
                        if msg_text:
                            chat_context.append(f"{msg_role}: {msg_text}")

                    try:
                        execution_result = executor.run(text, context={
                            "workspace_id": workspace_id,
                            "workspace_name": preview_workspace.get("name", ""),
                            "chat_history": chat_context,
                        })
                    finally:
                        release_agent_cancel(execution_id)

                    if execution_result.success:
                        reply_text = execution_result.final_answer
                    else:
                        reply_text = f"[Agent execution failed: {execution_result.error}]"

                    execution_info = execution_result.to_dict()
                    execution_info["id"] = execution_id
                    execution_info["trace_events"] = normalize_agent_trace_events(trace_events)
                    self.publish_event(
                        "agent.completed" if execution_result.success else "agent.failed",
                        workspace_id=workspace_id,
                        agent_execution_id=execution_id,
                        payload={
                            "execution": copy.deepcopy(execution_info),
                            "agent_id": str(agent.get("id") or "").strip(),
                            "chat": True,
                        },
                    )

        # If no LLM used or failed, use placeholder reply
        if not reply_text:
            reply_text = build_workspace_chat_reply(preview_workspace, text, agent_id=agent_id)

        assistant_message = make_workspace_chat_message("assistant", reply_text, agent_id=agent_id, agent_name=agent_name)
        if execution_info:
            assistant_message = normalize_workspace_chat_message(
                {
                    **assistant_message,
                    "agent_execution": self._chat_agent_execution_trace(
                        str(execution_info.get("id") or ""),
                        execution_info,
                        provider_profile_id=effective_profile_id if use_llm and agent_id else "",
                        success=bool(execution_info.get("success")),
                    ),
                },
                existing=assistant_message,
            )
        reflection = self._workspace_chat_context_reflection(
            preview_workspace,
            text,
            reply_text,
            assistant_message_id=str(assistant_message.get("id") or ""),
            user_message_id=str(user_message.get("id") or ""),
            agent_execution_id=str((execution_info or {}).get("id") or ""),
        )
        if reflection:
            assistant_message = normalize_workspace_chat_message(
                {
                    **assistant_message,
                    "context_reflection": reflection,
                },
                existing=assistant_message,
            )

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
        self.publish_event(
            "chat.message.created",
            workspace_id=workspace_id,
            payload={"message": copy.deepcopy(user_message), "workspace": copy.deepcopy(result_workspace)},
        )
        self.publish_event(
            "chat.message.completed",
            workspace_id=workspace_id,
            agent_execution_id=str((execution_info or {}).get("id") or ""),
            payload={"message": copy.deepcopy(assistant_message), "workspace": copy.deepcopy(result_workspace)},
        )

        result = {
            "workspace": result_workspace,
            "messages": [user_message, assistant_message],
        }
        if execution_info:
            result["execution"] = execution_info

        return result


    def append_workspace_chat_stream(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
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
            assistant_message = make_workspace_chat_message(
                "assistant",
                "正在回复...",
                agent_id=agent_id,
                agent_name=agent_name,
                status="pending",
            )
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
        self.publish_event(
            "chat.message.created",
            workspace_id=workspace_id,
            payload={"message": copy.deepcopy(user_message), "workspace": copy.deepcopy(result_workspace)},
        )
        self.publish_event(
            "chat.message.created",
            workspace_id=workspace_id,
            payload={"message": copy.deepcopy(assistant_message), "workspace": copy.deepcopy(result_workspace)},
        )

        thread = threading.Thread(
            target=self._complete_workspace_chat_stream,
            args=(workspace_id, str(assistant_message.get("id") or ""), str(user_message.get("id") or ""), text, agent_id, use_llm),
            daemon=True,
        )
        thread.start()

        return {
            "workspace": result_workspace,
            "messages": [user_message, assistant_message],
            "stream": True,
        }


    def publish_workspace_chat_delta(
        self,
        workspace_id: str,
        assistant_message_id: str,
        *,
        delta: str,
        accumulated: str,
    ) -> None:
        workspace_id = str(workspace_id or "").strip()
        assistant_message_id = str(assistant_message_id or "").strip()
        if not workspace_id or not assistant_message_id:
            return
        accumulated = str(accumulated or "")
        if not accumulated:
            return
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                return
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            updated_chat: list[dict[str, Any]] = []
            updated_message: dict[str, Any] | None = None
            for message in chat:
                if str(message.get("id") or "") == assistant_message_id:
                    next_message = {
                        **message,
                        "text": accumulated,
                        "status": "streaming",
                        "updated_at": now_iso(),
                    }
                    updated_message = normalize_workspace_chat_message(next_message, existing=message)
                    updated_chat.append(updated_message)
                else:
                    updated_chat.append(message)
            if updated_message is None:
                return
            merged = copy.deepcopy(current)
            merged["chat"] = updated_chat
            updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                return
            self.workspaces[index] = updated

        self.publish_event(
            "chat.message.delta",
            workspace_id=workspace_id,
            payload={
                "message": copy.deepcopy(updated_message),
                "delta": str(delta or ""),
            },
        )


    def _workspace_chat_reply(
        self,
        workspace_id: str,
        text: str,
        agent_id: str,
        *,
        use_llm: bool,
        delta_callback: Callable[[str, str], None] | None = None,
    ) -> tuple[str, dict[str, Any] | None, str]:
        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                raise ValueError("workspace not found")
            tools = normalize_workspace_tools(current.get("tools"), existing=current.get("tools"))
            tool_ids = [str(item.get("id") or "").strip() for item in tools if isinstance(item, dict) and str(item.get("id") or "").strip()]
            agents = normalize_workspace_agents(current.get("agents"), existing=current.get("agents"), tool_ids=tool_ids)
            model = normalize_workspace_model(current.get("model"), existing=current.get("model"))
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            selected_agent_id = agent_id if any(agent["id"] == agent_id for agent in agents) else ""
            agent_name = workspace_agent_name({"agents": agents}, selected_agent_id)
            preview_workspace = copy.deepcopy(current)
            preview_workspace["agents"] = agents
            preview_workspace["tools"] = tools
            preview_workspace["model"] = model
            preview_workspace["chat"] = chat
            preview_workspace_public = self.workspace_public_payload(preview_workspace)

        reply_text = ""
        execution_info: dict[str, Any] | None = None
        if use_llm and selected_agent_id:
            model_config = preview_workspace.get("model") if isinstance(preview_workspace.get("model"), dict) else {}
            routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
            agent = next((item for item in agents if item["id"] == selected_agent_id), None)
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip() if agent else ""
            effective_profile_id = workspace_profile_id
            if routing_mode == "agent_override" and agent_profile_id:
                effective_profile_id = agent_profile_id
            if effective_profile_id and agent:
                profile = self.provider_profile_by_id(effective_profile_id)
                if profile and profile.get("api_key"):
                    tool_map = {t.get("id"): t for t in tools if isinstance(t, dict) and t.get("id")}
                    allowed_tool_ids = [
                        tid for tid in parse_tag_list(agent.get("tools", []))
                        if tid in tool_map
                    ]
                    allowed_tools = [tool_map[tid] for tid in allowed_tool_ids]
                    llm_client = LLMClient(profile)
                    tool_executor = create_workspace_tool_executor(
                        preview_workspace,
                        statuses=copy.deepcopy(self.statuses),
                        jobs=copy.deepcopy(self.jobs),
                        runtime=self.workspace_tool_runtime(preview_workspace),
                    )
                    execution_id = make_agent_execution_id()
                    cancel_check = register_agent_cancel(execution_id)
                    chat_timeout_raw = agent.get("timeout_seconds")
                    chat_timeout = float(chat_timeout_raw) if chat_timeout_raw not in (None, "") and safe_int(chat_timeout_raw, 0) > 0 else None
                    trace_events: list[dict[str, Any]] = []

                    def on_agent_event(event_type: str, event_payload: dict[str, Any]) -> None:
                        if isinstance(event_payload, dict) and event_payload:
                            trace_events.append(copy.deepcopy(event_payload))
                        self.publish_event(
                            event_type,
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                **(event_payload if isinstance(event_payload, dict) else {}),
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    def on_agent_step(step: Any) -> None:
                        step_payload = step.to_dict() if hasattr(step, "to_dict") else step
                        self.publish_event(
                            "agent.step.created",
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                "step": copy.deepcopy(step_payload) if isinstance(step_payload, dict) else {},
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    def on_agent_delta(delta: str, accumulated: str) -> None:
                        if delta_callback:
                            delta_callback(delta, accumulated)
                        if not str(accumulated or "").strip():
                            return
                        self.publish_event(
                            "agent.message.delta",
                            workspace_id=workspace_id,
                            agent_execution_id=execution_id,
                            payload={
                                "delta": str(delta or ""),
                                "accumulated": str(accumulated or ""),
                                "agent_id": str(agent.get("id") or "").strip(),
                                "chat": True,
                            },
                        )

                    executor = AgentExecutor(
                        agent=agent,
                        llm_client=llm_client,
                        tools=allowed_tools,
                        tool_executor=tool_executor,
                        step_callback=on_agent_step,
                        token_callback=on_agent_delta,
                        event_callback=on_agent_event,
                        timeout_seconds=chat_timeout,
                        cancel_check=cancel_check,
                    )
                    chat_context = []
                    for msg in chat[-10:]:
                        msg_role = str(msg.get("role") or "user")
                        msg_text = str(msg.get("text") or "")
                        if msg_text:
                            chat_context.append(f"{msg_role}: {msg_text}")
                    try:
                        execution_result = executor.run(
                            text,
                            context={
                                "workspace_id": workspace_id,
                                "workspace_name": preview_workspace.get("name", ""),
                                "chat_history": chat_context,
                            },
                        )
                    finally:
                        release_agent_cancel(execution_id)
                    execution_info = execution_result.to_dict()
                    execution_info["id"] = execution_id
                    execution_info["trace_events"] = normalize_agent_trace_events(trace_events)
                    self.publish_event(
                        "agent.completed" if execution_result.success else "agent.failed",
                        workspace_id=workspace_id,
                        agent_execution_id=execution_id,
                        payload={
                            "execution": copy.deepcopy(execution_info),
                            "agent_id": str(agent.get("id") or "").strip(),
                            "chat": True,
                        },
                    )
                    if execution_result.success:
                        reply_text = execution_result.final_answer
                    else:
                        reply_text = f"[Agent execution failed: {execution_result.error}]"
        if not reply_text:
            reply_text = build_workspace_chat_reply(preview_workspace_public, text, agent_id=selected_agent_id)
        return reply_text, execution_info, agent_name


    def _complete_workspace_chat_stream(
        self,
        workspace_id: str,
        assistant_message_id: str,
        user_message_id: str,
        text: str,
        agent_id: str,
        use_llm: bool,
    ) -> None:
        status = "completed"
        error = ""
        execution_info: dict[str, Any] | None = None
        try:
            def on_reply_delta(delta: str, accumulated: str) -> None:
                self.publish_workspace_chat_delta(
                    workspace_id,
                    assistant_message_id,
                    delta=delta,
                    accumulated=accumulated,
                )

            reply_text, execution_info, agent_name = self._workspace_chat_reply(
                workspace_id,
                text,
                agent_id,
                use_llm=use_llm,
                delta_callback=on_reply_delta,
            )
        except Exception as exc:  # noqa: BLE001 - background chat must report failure via event.
            status = "failed"
            error = str(exc)
            reply_text = f"[Agent execution failed: {error}]"
            agent_name = workspace_agent_name(self.workspace_by_id(workspace_id) or {}, agent_id)

        with self.lock:
            current = self.workspace_by_id(workspace_id)
            if not current:
                return
            chat = normalize_workspace_chat(current.get("chat"), existing=current.get("chat"))
            updated_chat: list[dict[str, Any]] = []
            updated_message: dict[str, Any] | None = None
            for message in chat:
                if str(message.get("id") or "") == assistant_message_id:
                    next_message = {
                        **message,
                        "text": reply_text,
                        "status": status,
                        "error": error,
                        "agent_name": message.get("agent_name") or agent_name,
                        "updated_at": now_iso(),
                    }
                    if execution_info:
                        model_config = current.get("model") if isinstance(current.get("model"), dict) else {}
                        routing_mode = str(model_config.get("routing_mode") or "workspace_default").strip() or "workspace_default"
                        workspace_profile_id = str(model_config.get("provider_profile_id") or "").strip()
                        agent = workspace_agent_by_id(current, agent_id)
                        agent_profile_id = str(agent.get("provider_profile_id") or "").strip() if agent else ""
                        effective_profile_id = workspace_profile_id
                        if routing_mode == "agent_override" and agent_profile_id:
                            effective_profile_id = agent_profile_id
                        next_message["agent_execution"] = self._chat_agent_execution_trace(
                            str(execution_info.get("id") or ""),
                            execution_info,
                            provider_profile_id=effective_profile_id if use_llm and agent_id else "",
                            success=bool(execution_info.get("success")),
                        )
                    if status == "completed":
                        reflection = self._workspace_chat_context_reflection(
                            current,
                            text,
                            reply_text,
                            assistant_message_id=assistant_message_id,
                            user_message_id=user_message_id,
                            agent_execution_id=str((execution_info or {}).get("id") or ""),
                        )
                        if reflection:
                            next_message["context_reflection"] = reflection
                    updated_message = normalize_workspace_chat_message(next_message, existing=message)
                    updated_chat.append(updated_message)
                else:
                    updated_chat.append(message)
            if updated_message is None:
                updated_message = make_workspace_chat_message(
                    "assistant",
                    reply_text,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    status=status,
                    error=error,
                )
                updated_chat.append(updated_message)
            merged = copy.deepcopy(current)
            merged["chat"] = updated_chat
            updated = normalize_workspace_payload(merged, existing=current)
            index = next((idx for idx, item in enumerate(self.workspaces) if item.get("id") == workspace_id), -1)
            if index < 0:
                return
            result_workspace = self.workspace_public_payload(updated)
            event_type = "chat.message.failed" if status == "failed" else "chat.message.completed"
            event_payload = {
                "message": copy.deepcopy(updated_message),
                "workspace": copy.deepcopy(result_workspace),
                "execution": copy.deepcopy(execution_info) if execution_info else None,
            }
            self.publish_event(
                event_type,
                workspace_id=workspace_id,
                agent_execution_id=str((execution_info or {}).get("id") or ""),
                payload=event_payload,
            )
            self.workspaces[index] = updated

        self.save_workspaces()
