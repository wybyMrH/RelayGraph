from __future__ import annotations

from ._deps import *  # noqa: F403


def _normalized_provider_base_url(value: Any) -> str:
    return str(value or "").strip().rstrip("/")


def _provider_catalog_for_profile(profile: dict[str, Any]) -> dict[str, Any]:
    vendor_id = str(profile.get("vendor_id") or profile.get("catalog_id") or "").strip()
    if vendor_id:
        vendor = provider_catalog_by_id(vendor_id)
        if vendor:
            return vendor
    base_url = _normalized_provider_base_url(profile.get("base_url"))
    if base_url:
        for vendor in PROVIDER_CATALOG:
            if _normalized_provider_base_url(vendor.get("base_url")) == base_url:
                return vendor
    return {}


def _provider_profile_key_required(profile: dict[str, Any]) -> bool:
    if "key_required" in profile:
        return bool(profile.get("key_required"))
    vendor = _provider_catalog_for_profile(profile)
    if vendor:
        return bool(vendor.get("key_required", True))
    base_url = _normalized_provider_base_url(profile.get("base_url")).lower()
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return False
    return True


def _provider_profile_models(profile: dict[str, Any]) -> list[str]:
    return [
        str(item or "").strip()
        for item in (profile.get("models") if isinstance(profile.get("models"), list) else [])
        if str(item or "").strip()
    ]


def provider_profile_health(profile: dict[str, Any]) -> dict[str, Any]:
    source = profile if isinstance(profile, dict) else {}
    key_required = _provider_profile_key_required(source)
    has_api_key = bool(str(source.get("api_key") or "").strip()) or not key_required
    models = _provider_profile_models(source)
    base_url = str(source.get("base_url") or "").strip()
    missing_fields: list[str] = []
    if not base_url:
        missing_fields.append("base_url")
    if not models:
        missing_fields.append("models")
    if key_required and not str(source.get("api_key") or "").strip():
        missing_fields.append("api_key")
    ready = not missing_fields
    return {
        "status": "ready" if ready else "blocked" if "api_key" in missing_fields or "base_url" in missing_fields else "warning",
        "ready": ready,
        "key_required": key_required,
        "has_api_key": has_api_key,
        "model_count": len(models),
        "missing_fields": missing_fields,
    }


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

    def test_tool_definition(self, tool_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a safe tool preview against a workspace snapshot.

        Configuration-center tool tests must not bypass the controlled runtime
        queue. Read-only tools can execute with the workspace executor; runtime
        and dangerous tools return a blocked/plan-only result so their payload
        shape can be inspected without causing side effects.
        """
        requested = payload if isinstance(payload, dict) else {}
        requested_tool_id = str(tool_id or requested.get("tool_id") or "").strip()
        with self.lock:
            tool = copy.deepcopy(self.tool_definition_by_id(requested_tool_id)) if requested_tool_id else None
            workspace_id = str(requested.get("workspace_id") or "").strip()
            workspace = copy.deepcopy(self.workspace_by_id(workspace_id)) if workspace_id else None
            if not workspace:
                workspace = copy.deepcopy(self.workspaces[0]) if getattr(self, "workspaces", []) else {}
            statuses = copy.deepcopy(getattr(self, "statuses", []))
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        if not tool:
            raise ValueError("tool definition not found")

        side_effect = str(tool.get("side_effect") or tool_side_effect(requested_tool_id).value).strip()
        arguments = requested.get("arguments") if isinstance(requested.get("arguments"), dict) else {}
        workspace_summary = {
            "id": str(workspace.get("id") or "").strip(),
            "name": str(workspace.get("name") or workspace.get("brief") or "").strip(),
        }
        if side_effect != ToolSideEffect.READ.value:
            return {
                "tool_id": requested_tool_id,
                "status": "blocked",
                "safe": False,
                "side_effect": side_effect,
                "workspace": workspace_summary,
                "arguments": copy.deepcopy(arguments),
                "result": {
                    "status": "blocked",
                    "plan_only": True,
                    "message": "配置中心只允许安全测试 read-only 工具；runtime/config/dangerous 工具必须通过 Agent trace 或受控 workflow/job 队列验证。",
                },
            }

        executor = create_workspace_tool_executor(
            workspace,
            getattr(self, "config", None),
            statuses=statuses,
            jobs=jobs,
            runtime=None,
        )
        started = time.time()
        observation = executor(requested_tool_id, arguments)
        latency_ms = round((time.time() - started) * 1000, 1)
        parsed_result: Any
        try:
            parsed_result = json.loads(observation)
        except (TypeError, json.JSONDecodeError):
            parsed_result = {"text": str(observation or "")[:4000]}
        return {
            "tool_id": requested_tool_id,
            "status": "ok",
            "safe": True,
            "side_effect": side_effect,
            "workspace": workspace_summary,
            "arguments": copy.deepcopy(arguments),
            "latency_ms": latency_ms,
            "result": parsed_result,
        }


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

    def provider_route_health(self) -> dict[str, Any]:
        with self.lock:
            profiles = copy.deepcopy(getattr(self, "provider_profiles", []))
            agents = copy.deepcopy(getattr(self, "agent_definitions", []))
            templates = copy.deepcopy(getattr(self, "workflow_templates", []))
            workspaces = copy.deepcopy(getattr(self, "workspaces", []))
        profile_index = {
            str(profile.get("id") or "").strip(): profile
            for profile in profiles
            if isinstance(profile, dict) and str(profile.get("id") or "").strip()
        }
        profile_health = {
            profile_id: provider_profile_health(profile)
            for profile_id, profile in profile_index.items()
        }
        issues: list[dict[str, Any]] = []

        def add_issue(severity: str, code: str, message: str, **extra: Any) -> None:
            issue = {
                "severity": severity,
                "code": code,
                "message": message,
            }
            issue.update({key: value for key, value in extra.items() if value not in (None, "")})
            issues.append(issue)

        configured_profiles = sum(1 for item in profile_health.values() if item.get("ready"))
        for profile_id, profile in profile_index.items():
            health = profile_health.get(profile_id, {})
            missing_fields = health.get("missing_fields") if isinstance(health.get("missing_fields"), list) else []
            missing_severity = "warning" if configured_profiles else "blocking"
            if "api_key" in missing_fields:
                add_issue(missing_severity, "provider_missing_api_key", f"Provider Profile {profile.get('name') or profile_id} 没有 API key。", provider_profile_id=profile_id)
            if "models" in missing_fields:
                add_issue("warning", "provider_missing_model", f"Provider Profile {profile.get('name') or profile_id} 没有模型。", provider_profile_id=profile_id)
            if "base_url" in missing_fields:
                add_issue(missing_severity, "provider_missing_base_url", f"Provider Profile {profile.get('name') or profile_id} 没有 Base URL。", provider_profile_id=profile_id)

        if not profile_index:
            add_issue("blocking", "no_provider_profiles", "还没有 Provider Profile，Agent 无法真实调用模型。")

        for agent in agents:
            if not isinstance(agent, dict):
                continue
            agent_id = str(agent.get("id") or "").strip()
            if agent.get("enabled") is False:
                continue
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
            if agent_profile_id and agent_profile_id not in profile_index:
                add_issue(
                    "warning",
                    "agent_unknown_provider_profile",
                    f"Agent {agent.get('name') or agent_id} 指向不存在的 Provider Profile {agent_profile_id}。",
                    agent_id=agent_id,
                    provider_profile_id=agent_profile_id,
                )
            elif agent_profile_id and not profile_health.get(agent_profile_id, {}).get("ready"):
                add_issue(
                    "warning",
                    "agent_provider_profile_not_ready",
                    f"Agent {agent.get('name') or agent_id} 的 Provider Profile {agent_profile_id} 未就绪。",
                    agent_id=agent_id,
                    provider_profile_id=agent_profile_id,
                )

        for template in templates:
            if not isinstance(template, dict):
                continue
            template_id = str(template.get("id") or "").strip()
            model = template.get("model") if isinstance(template.get("model"), dict) else {}
            template_profile_id = str(model.get("provider_profile_id") or "").strip()
            routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
            if template_profile_id and template_profile_id not in profile_index:
                add_issue(
                    "warning",
                    "template_unknown_provider_profile",
                    f"模板 {template.get('name') or template_id} 指向不存在的 Provider Profile {template_profile_id}。",
                    template_id=template_id,
                    provider_profile_id=template_profile_id,
                )
            elif template_profile_id and not profile_health.get(template_profile_id, {}).get("ready"):
                add_issue(
                    "warning",
                    "template_provider_profile_not_ready",
                    f"模板 {template.get('name') or template_id} 的 Provider Profile {template_profile_id} 未就绪。",
                    template_id=template_id,
                    provider_profile_id=template_profile_id,
                )
            if routing_mode == "workspace_default" and not template_profile_id and not configured_profiles:
                add_issue(
                    "blocking",
                    "template_without_provider_route",
                    f"模板 {template.get('name') or template_id} 没有默认 Provider，且全局没有可用 Profile。",
                    template_id=template_id,
                )

        for workspace in workspaces:
            if not isinstance(workspace, dict):
                continue
            workspace_id = str(workspace.get("id") or "").strip()
            model = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
            workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
            if workspace_profile_id and workspace_profile_id not in profile_index:
                add_issue(
                    "warning",
                    "workspace_unknown_provider_profile",
                    f"实例 {workspace.get('name') or workspace_id} 指向不存在的 Provider Profile {workspace_profile_id}。",
                    workspace_id=workspace_id,
                    provider_profile_id=workspace_profile_id,
                )
            elif workspace_profile_id and not profile_health.get(workspace_profile_id, {}).get("ready"):
                add_issue(
                    "warning",
                    "workspace_provider_profile_not_ready",
                    f"实例 {workspace.get('name') or workspace_id} 的 Provider Profile {workspace_profile_id} 未就绪。",
                    workspace_id=workspace_id,
                    provider_profile_id=workspace_profile_id,
                )

        blocking_count = sum(1 for item in issues if item.get("severity") == "blocking")
        warning_count = sum(1 for item in issues if item.get("severity") == "warning")
        return {
            "status": "blocked" if blocking_count else "warning" if warning_count else "ready",
            "profile_count": len(profile_index),
            "configured_profile_count": configured_profiles,
            "agent_count": len([item for item in agents if isinstance(item, dict)]),
            "template_count": len([item for item in templates if isinstance(item, dict)]),
            "workspace_count": len([item for item in workspaces if isinstance(item, dict)]),
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "profiles": [
                {
                    "id": profile_id,
                    "name": str(profile_index.get(profile_id, {}).get("name") or profile_id),
                    **profile_health.get(profile_id, {}),
                }
                for profile_id in sorted(profile_index)
            ],
            "issues": issues,
        }

    def execution_overview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        requested = payload if isinstance(payload, dict) else {}
        limit = max(1, min(safe_int(requested.get("limit"), 50), 200))
        self.sync_workspace_execution_runs_from_jobs()
        with self.lock:
            workspaces = copy.deepcopy(getattr(self, "workspaces", []))
            jobs = copy.deepcopy(getattr(self, "jobs", []))
        workspace_names = {
            str(workspace.get("id") or "").strip(): str(workspace.get("name") or workspace.get("brief") or workspace.get("id") or "").strip()
            for workspace in workspaces
            if isinstance(workspace, dict) and str(workspace.get("id") or "").strip()
        }
        runs: list[dict[str, Any]] = []
        for workspace in workspaces:
            if not isinstance(workspace, dict):
                continue
            workspace_id = str(workspace.get("id") or "").strip()
            workspace_name = workspace_names.get(workspace_id, workspace_id)
            for run in workspace_execution_runs_public(workspace.get("runs"), jobs):
                if not isinstance(run, dict):
                    continue
                steps = run.get("steps") if isinstance(run.get("steps"), list) else []
                runs.append(
                    {
                        "id": str(run.get("id") or "").strip(),
                        "workspace_id": workspace_id,
                        "workspace_name": workspace_name,
                        "kind": str(run.get("kind") or "").strip(),
                        "status": str(run.get("status") or "").strip(),
                        "summary": str(run.get("summary") or "").strip(),
                        "progress": copy.deepcopy(run.get("progress") if isinstance(run.get("progress"), dict) else {}),
                        "step_count": len(steps),
                        "job_ids": [
                            str(step.get("job_id") or "").strip()
                            for step in steps
                            if isinstance(step, dict) and str(step.get("job_id") or "").strip()
                        ][:8],
                        "agent_execution_ids": [
                            str(step.get("agent_execution_id") or "").strip()
                            for step in steps
                            if isinstance(step, dict) and str(step.get("agent_execution_id") or "").strip()
                        ][:8],
                        "created_at": str(run.get("created_at") or "").strip(),
                        "updated_at": str(run.get("updated_at") or "").strip(),
                    }
                )
        runs.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)

        job_items: list[dict[str, Any]] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
            workspace_id = str(metadata.get("workspace_id") or job.get("workspace_id") or "").strip()
            job_items.append(
                {
                    "id": str(job.get("id") or "").strip(),
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_names.get(workspace_id, workspace_id or "未绑定 workspace"),
                    "status": str(job.get("status") or "").strip(),
                    "kind": str(metadata.get("node_kind") or job.get("kind") or "").strip(),
                    "server_id": str(job.get("server_id") or metadata.get("server_id") or "").strip(),
                    "summary": str(job.get("summary") or metadata.get("node_title") or "").strip(),
                    "execution_run_id": str(metadata.get("execution_run_id") or "").strip(),
                    "created_at": str(job.get("created_at") or "").strip(),
                    "updated_at": str(job.get("updated_at") or job.get("finished_at") or job.get("created_at") or "").strip(),
                }
            )
        job_items.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
        return {
            "runs": runs[:limit],
            "jobs": job_items[:limit],
            "summary": {
                "run_count": len(runs),
                "job_count": len(job_items),
                "active_run_count": sum(1 for item in runs if str(item.get("status") or "") in {"queued", "running", "pending"}),
                "active_job_count": sum(1 for item in job_items if str(item.get("status") or "") in {"queued", "blocked", "starting", "running"}),
                "failed_run_count": sum(1 for item in runs if str(item.get("status") or "") in {"failed", "blocked", "stopped"}),
                "failed_job_count": sum(1 for item in job_items if str(item.get("status") or "") in {"failed", "stopped"}),
            },
        }

    def validate_workflow_template(self, payload: dict[str, Any], template_id: str = "") -> dict[str, Any]:
        body = payload if isinstance(payload, dict) else {}
        requested_id = str(template_id or body.get("template_id") or "").strip()
        with self.lock:
            current = self.workflow_template_by_id(requested_id) if requested_id else None
            if requested_id and not current:
                raise ValueError("workflow template not found")
            template = normalize_workflow_template(
                body if body else copy.deepcopy(current or {}),
                existing=current,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
            )
            public = self.workflow_template_public_payload(template)
            validation = self._workflow_template_validation_payload(template, body)
            preview = self._workflow_template_preview_payload(template, validation)
        return {
            "workflow_template": public,
            "validation": validation,
            "preview": preview,
        }

    def _workflow_template_validation_payload(
        self,
        template: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]:
        nodes = template.get("nodes") if isinstance(template.get("nodes"), list) else []
        links = raw_payload.get("links") if isinstance(raw_payload.get("links"), list) else template.get("links")
        links = links if isinstance(links, list) else []
        model = template.get("model") if isinstance(template.get("model"), dict) else {}
        agent_index = {
            str(agent.get("id") or "").strip(): agent
            for agent in self.agent_definitions
            if isinstance(agent, dict) and str(agent.get("id") or "").strip()
        }
        tool_index = {
            str(tool.get("id") or "").strip(): tool
            for tool in self.tool_definitions
            if isinstance(tool, dict) and str(tool.get("id") or "").strip()
        }
        provider_ids = {
            str(profile.get("id") or "").strip()
            for profile in getattr(self, "provider_profiles", [])
            if isinstance(profile, dict) and str(profile.get("id") or "").strip()
        }
        raw_nodes = raw_payload.get("nodes") if isinstance(raw_payload.get("nodes"), list) else []
        raw_nodes_by_id = {
            str(item.get("id") or "").strip(): item
            for item in raw_nodes
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        issues: list[dict[str, Any]] = []
        output_key_mismatch_nodes: set[str] = set()

        def add_issue(
            severity: str,
            kind: str,
            code: str,
            message: str,
            **extra: Any,
        ) -> None:
            issue = {
                "severity": severity,
                "kind": kind,
                "code": code,
                "message": message,
            }
            issue.update({key: value for key, value in extra.items() if value not in (None, "")})
            issues.append(issue)

        if not nodes:
            add_issue("blocking", "template", "no_nodes", "模板没有节点，无法创建可执行实例。")

        node_ids: set[str] = set()
        output_keys: dict[str, dict[str, Any]] = {}
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                add_issue("blocking", "node", "invalid_node", "模板节点不是对象。", index=index)
                continue
            node_id = str(node.get("id") or "").strip()
            kind = str(node.get("kind") or "").strip()
            title = str(node.get("title") or kind or f"节点 {index + 1}").strip()
            if not node_id:
                add_issue("blocking", "node", "missing_node_id", f"{title} 缺少节点 ID。", index=index)
            elif node_id in node_ids:
                add_issue("blocking", "node", "duplicate_node_id", f"节点 ID {node_id} 重复。", node_id=node_id)
            else:
                node_ids.add(node_id)
            if kind and kind not in WORKSPACE_NODE_LIBRARY:
                add_issue("warning", "node", "custom_node_kind", f"{title} 使用自定义节点类型 {kind}。", node_id=node_id)

            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            mode = str(handler.get("mode") or "human").strip().lower() or "human"
            agent_id = str(handler.get("agent_id") or "").strip()
            if mode != "human":
                if not agent_id:
                    add_issue("blocking", "agent", "missing_agent", f"{title} 是 {mode} 节点，但没有绑定 Agent。", node_id=node_id)
                else:
                    agent = agent_index.get(agent_id)
                    if not agent:
                        add_issue("blocking", "agent", "unknown_agent", f"{title} 绑定的 Agent {agent_id} 不存在。", node_id=node_id, agent_id=agent_id)
                    elif agent.get("enabled") is False:
                        severity = "blocking" if mode == "agent" else "warning"
                        add_issue(severity, "agent", "disabled_agent", f"{title} 绑定的 Agent {agent.get('name') or agent_id} 已停用。", node_id=node_id, agent_id=agent_id)
                    elif mode == "agent":
                        for tool_id in parse_tag_list(agent.get("tools", [])):
                            tool = tool_index.get(tool_id)
                            if not tool:
                                add_issue("warning", "tool", "unknown_agent_tool", f"Agent {agent.get('name') or agent_id} 的工具 {tool_id} 不在工具注册表。", node_id=node_id, agent_id=agent_id, tool_id=tool_id)
                            elif tool.get("enabled") is False:
                                add_issue("warning", "tool", "disabled_agent_tool", f"Agent {agent.get('name') or agent_id} 的工具 {tool.get('label') or tool_id} 已停用。", node_id=node_id, agent_id=agent_id, tool_id=tool_id)

            required_tool_id = workspace_node_required_tool_id(kind)
            if required_tool_id:
                tool = tool_index.get(required_tool_id)
                if not tool:
                    add_issue("blocking", "tool", "missing_required_tool", f"{title} 需要工具 {required_tool_id}，但工具注册表里不存在。", node_id=node_id, tool_id=required_tool_id)
                elif tool.get("enabled") is False:
                    add_issue("blocking", "tool", "disabled_required_tool", f"{title} 需要的工具 {tool.get('label') or required_tool_id} 已停用。", node_id=node_id, tool_id=required_tool_id)

            raw_node = raw_nodes_by_id.get(node_id) if node_id else None
            if not raw_node and index < len(raw_nodes) and isinstance(raw_nodes[index], dict):
                raw_node = raw_nodes[index]
            raw_handler = raw_node.get("handler") if isinstance(raw_node, dict) and isinstance(raw_node.get("handler"), dict) else {}
            raw_node_output_key = str(raw_node.get("output_key") or "").strip() if isinstance(raw_node, dict) else ""
            raw_handler_output_key = str(raw_handler.get("output_key") or "").strip()
            if raw_node_output_key and raw_handler_output_key and raw_node_output_key != raw_handler_output_key:
                output_key_mismatch_nodes.add(node_id)
                add_issue(
                    "blocking",
                    "contract",
                    "output_key_mismatch",
                    f"{title} 的 node.output_key={raw_node_output_key} 与 handler.output_key={raw_handler_output_key} 不一致。",
                    node_id=node_id,
                    output_key=raw_node_output_key,
                    handler_output_key=raw_handler_output_key,
                )

            node_output_key = str(node.get("output_key") or "").strip()
            handler_output_key = str(handler.get("output_key") or "").strip()
            if node_id not in output_key_mismatch_nodes and node_output_key and handler_output_key and node_output_key != handler_output_key:
                add_issue(
                    "blocking",
                    "contract",
                    "output_key_mismatch",
                    f"{title} 的 node.output_key={node_output_key} 与 handler.output_key={handler_output_key} 不一致。",
                    node_id=node_id,
                    output_key=node_output_key,
                    handler_output_key=handler_output_key,
                )
            output_key = str(
                node_output_key
                or handler_output_key
                or workspace_io_contract_for_kind(kind, index).get("output_key")
                or ""
            ).strip()
            if output_key:
                previous = output_keys.get(output_key)
                if previous:
                    add_issue(
                        "blocking",
                        "contract",
                        "duplicate_output_key",
                        f"{title} 的 output_key {output_key} 与上游节点重复。",
                        node_id=node_id,
                        upstream_node_id=previous.get("node_id"),
                        output_key=output_key,
                    )
                else:
                    output_keys[output_key] = {"node_id": node_id, "index": index}

        seen_edges: set[tuple[str, str]] = set()
        for link in links:
            if not isinstance(link, dict):
                add_issue("blocking", "link", "invalid_link", "模板链路不是对象。")
                continue
            from_id = str(link.get("from") or "").strip()
            to_id = str(link.get("to") or "").strip()
            if not from_id or not to_id:
                add_issue("blocking", "link", "incomplete_link", "模板链路缺少 from/to。")
                continue
            if from_id not in node_ids or to_id not in node_ids:
                add_issue("blocking", "link", "dangling_link", f"链路 {from_id} -> {to_id} 指向不存在的节点。", from_node_id=from_id, to_node_id=to_id)
                continue
            edge = (from_id, to_id)
            if edge in seen_edges:
                add_issue("warning", "link", "duplicate_link", f"链路 {from_id} -> {to_id} 重复。", from_node_id=from_id, to_node_id=to_id)
            seen_edges.add(edge)

        chat_agent_id = str(model.get("chat_agent_id") or "").strip()
        if chat_agent_id and chat_agent_id not in agent_index:
            add_issue("warning", "model", "unknown_chat_agent", f"默认对话 Agent {chat_agent_id} 不存在。", agent_id=chat_agent_id)
        provider_profile_id = str(model.get("provider_profile_id") or "").strip()
        if provider_profile_id and provider_profile_id not in provider_ids:
            add_issue("warning", "model", "unknown_provider_profile", f"默认 Provider Profile {provider_profile_id} 不存在。", provider_profile_id=provider_profile_id)
        routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
        used_agent_ids = collect_template_agent_ids(nodes, model)
        for agent_id in used_agent_ids:
            agent = agent_index.get(agent_id)
            if not agent:
                continue
            agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
            if agent_profile_id and agent_profile_id not in provider_ids:
                add_issue(
                    "warning",
                    "model",
                    "unknown_agent_provider_profile",
                    f"Agent {agent.get('name') or agent_id} 指向的 Provider Profile {agent_profile_id} 不存在。",
                    agent_id=agent_id,
                    provider_profile_id=agent_profile_id,
                )
            if routing_mode == "agent_override" and not agent_profile_id:
                add_issue(
                    "warning",
                    "model",
                    "agent_override_without_profile",
                    f"Agent {agent.get('name') or agent_id} 未设置 Provider 覆盖，会回落到模板默认路由。",
                    agent_id=agent_id,
                )

        snapshot = build_template_snapshot(template, self.agent_definitions, self.tool_definitions)
        contract = derive_workspace_workflow_contract(
            {
                "nodes": copy.deepcopy(nodes),
                "links": copy.deepcopy(template.get("links") if isinstance(template.get("links"), list) else []),
                "agents": copy.deepcopy(snapshot.get("agents") if isinstance(snapshot.get("agents"), list) else []),
                "tools": copy.deepcopy(snapshot.get("tools") if isinstance(snapshot.get("tools"), list) else []),
                "model": copy.deepcopy(model),
            },
            {},
            [],
            {},
            {},
            {},
        )
        for contract_node in contract.get("nodes") if isinstance(contract.get("nodes"), list) else []:
            if not isinstance(contract_node, dict):
                continue
            for ref in contract_node.get("missing_inputs") if isinstance(contract_node.get("missing_inputs"), list) else []:
                if not isinstance(ref, dict):
                    continue
                code = str(ref.get("code") or "blocked_input_mapping").strip()
                add_issue(
                    "blocking",
                    "contract",
                    code,
                    f"{contract_node.get('title') or contract_node.get('id')} 的输入 {ref.get('name') or ''} 未能解析：{ref.get('detail') or ''}",
                    node_id=str(contract_node.get("id") or "").strip(),
                    source=str(ref.get("source") or "").strip(),
                    input_name=str(ref.get("name") or "").strip(),
                    upstream_node_id=str(ref.get("upstream_node_id") or "").strip(),
                    upstream_output_key=str(ref.get("upstream_output_key") or "").strip(),
                )

        blocking_count = sum(1 for issue in issues if issue.get("severity") == "blocking")
        warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
        status = "blocked" if blocking_count else "warning" if warning_count else "ready"
        return {
            "status": status,
            "summary": f"{len(nodes)} 个节点 · {blocking_count} 个阻塞 · {warning_count} 个警告 · {safe_int(contract.get('mapped_count'), 0)}/{safe_int(contract.get('node_count'), 0)} 节点有输入/输出契约 · {safe_int(contract.get('input_gap_count'), 0)} 输入断点",
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "issue_count": len(issues),
            "node_count": len(nodes),
            "agent_count": len(snapshot.get("agents") if isinstance(snapshot.get("agents"), list) else []),
            "tool_count": len(snapshot.get("tools") if isinstance(snapshot.get("tools"), list) else []),
            "contract": contract,
            "issues": issues,
        }

    def _workflow_template_preview_payload(
        self,
        template: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        contract_nodes = validation.get("contract", {}).get("nodes") if isinstance(validation.get("contract"), dict) else []
        contract_by_id = {
            str(item.get("id") or "").strip(): item
            for item in contract_nodes
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        issues = validation.get("issues") if isinstance(validation.get("issues"), list) else []
        output_conflicts_by_node: dict[str, list[dict[str, Any]]] = {}
        for issue in issues:
            if not isinstance(issue, dict) or str(issue.get("code") or "").strip() not in {"duplicate_output_key", "output_key_mismatch"}:
                continue
            node_id = str(issue.get("node_id") or "").strip()
            if not node_id:
                continue
            code = str(issue.get("code") or "").strip()
            output_conflicts_by_node.setdefault(node_id, []).append(
                {
                    "code": code,
                    "output_key": str(issue.get("output_key") or "").strip(),
                    "handler_output_key": str(issue.get("handler_output_key") or "").strip(),
                    "upstream_node_id": str(issue.get("upstream_node_id") or "").strip(),
                    "message": str(issue.get("message") or "").strip(),
                }
            )
        reserved_output_keys = {
            str(item.get("output_key") or "").strip()
            for item in contract_nodes
            if isinstance(item, dict) and str(item.get("output_key") or "").strip()
        }

        def unique_output_key(seed: str, index: int) -> str:
            base = safe_id(seed) or f"step_{index + 1}"
            candidate = f"{base}_{index + 1}"
            suffix = 2
            while candidate in reserved_output_keys:
                candidate = f"{base}_{index + 1}_{suffix}"
                suffix += 1
            reserved_output_keys.add(candidate)
            return candidate

        seen_outputs: dict[str, dict[str, Any]] = {}
        preview_nodes: list[dict[str, Any]] = []
        for index, node in enumerate(template.get("nodes") if isinstance(template.get("nodes"), list) else []):
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            contract = contract_by_id.get(node_id, {})
            repair_actions: list[dict[str, Any]] = []
            missing_inputs = contract.get("missing_inputs") if isinstance(contract.get("missing_inputs"), list) else []
            for ref in missing_inputs:
                if not isinstance(ref, dict):
                    continue
                input_name = str(ref.get("name") or "").strip()
                if not input_name:
                    continue
                source = str(ref.get("source") or "").strip()
                code = str(ref.get("code") or "").strip()
                upstream_output_key = str(ref.get("upstream_output_key") or "").strip()
                if upstream_output_key and upstream_output_key in seen_outputs:
                    value = f"$context.outputs.{upstream_output_key}"
                elif code == "first_node_prev_reference" or index == 0:
                    value = "$input"
                elif input_name in seen_outputs:
                    value = f"$context.outputs.{input_name}"
                elif source:
                    value = source
                else:
                    value = "$prev.output"
                repair_actions.append(
                    {
                        "id": safe_id(f"map-input-{node_id}-{input_name}") or f"map-input-{index}-{len(repair_actions)}",
                        "kind": "set_input_mapping",
                        "issue_code": code or "unmapped_required_input",
                        "severity": "blocking",
                        "node_id": node_id,
                        "label": f"映射 {input_name}",
                        "patch": {
                            "path": ["nodes", index, "input_mapping", input_name],
                            "value": value,
                        },
                        "patches": [
                            {
                                "path": ["nodes", index, "input_mapping", input_name],
                                "value": value,
                            }
                        ],
                    }
                )
            output_key = str(contract.get("output_key") or node.get("output_key") or handler.get("output_key") or "").strip()
            output_conflicts = output_conflicts_by_node.get(node_id, [])
            for conflict in output_conflicts:
                if not isinstance(conflict, dict):
                    continue
                code = str(conflict.get("code") or "").strip()
                if code == "duplicate_output_key":
                    value = unique_output_key(str(conflict.get("output_key") or output_key or "step"), index)
                    patches = [
                        {"path": ["nodes", index, "output_key"], "value": value},
                        {"path": ["nodes", index, "handler", "output_key"], "value": value},
                    ]
                    repair_actions.append(
                        {
                            "id": safe_id(f"set-output-key-{node_id}-{value}") or f"set-output-key-{index}",
                            "kind": "set_output_key",
                            "issue_code": "duplicate_output_key",
                            "severity": "blocking",
                            "node_id": node_id,
                            "label": f"改为唯一 output_key {value}",
                            "patch": patches[0],
                            "patches": patches,
                        }
                    )
                elif code == "output_key_mismatch" and output_key:
                    patches = [
                        {"path": ["nodes", index, "handler", "output_key"], "value": output_key},
                    ]
                    repair_actions.append(
                        {
                            "id": safe_id(f"sync-handler-output-key-{node_id}") or f"sync-handler-output-key-{index}",
                            "kind": "sync_output_key",
                            "issue_code": "output_key_mismatch",
                            "severity": "blocking",
                            "node_id": node_id,
                            "label": f"同步 handler output_key 为 {output_key}",
                            "patch": patches[0],
                            "patches": patches,
                        }
                    )
            preview_nodes.append(
                {
                    "id": node_id,
                    "index": index + 1,
                    "kind": str(node.get("kind") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or f"节点 {index + 1}").strip(),
                    "handler": {
                        "mode": str(handler.get("mode") or "human").strip() or "human",
                        "agent_id": str(handler.get("agent_id") or "").strip(),
                        "name": str(handler.get("name") or "").strip(),
                    },
                    "output_key": output_key,
                    "inputs": copy.deepcopy(contract.get("inputs") if isinstance(contract.get("inputs"), list) else []),
                    "required_inputs": copy.deepcopy(contract.get("required_inputs") if isinstance(contract.get("required_inputs"), list) else []),
                    "mapped_inputs": copy.deepcopy(contract.get("mapped_inputs") if isinstance(contract.get("mapped_inputs"), list) else []),
                    "input_mapping": copy.deepcopy(contract.get("input_mapping") if isinstance(contract.get("input_mapping"), dict) else {}),
                    "input_refs": copy.deepcopy(contract.get("input_refs") if isinstance(contract.get("input_refs"), list) else []),
                    "input_status": str(contract.get("input_status") or "").strip(),
                    "missing_inputs": copy.deepcopy(missing_inputs),
                    "unmapped_required_inputs": copy.deepcopy(contract.get("unmapped_required_inputs") if isinstance(contract.get("unmapped_required_inputs"), list) else []),
                    "input_gap_count": safe_int(contract.get("input_gap_count"), 0),
                    "output_conflicts": output_conflicts,
                    "repair_actions": repair_actions,
                    "tools": copy.deepcopy(contract.get("tools") if isinstance(contract.get("tools"), list) else []),
                    "model": copy.deepcopy(contract.get("model") if isinstance(contract.get("model"), dict) else {}),
                }
            )
            if output_key and output_key not in seen_outputs:
                seen_outputs[output_key] = {"node_id": node_id, "index": index}
        source = template.get("source") if isinstance(template.get("source"), dict) else {}
        model = template.get("model") if isinstance(template.get("model"), dict) else {}
        return {
            "source_type": str(source.get("type") or "").strip(),
            "template_id": str(template.get("id") or "").strip(),
            "template_name": str(template.get("name") or "").strip(),
            "status": validation.get("status"),
            "node_count": len(preview_nodes),
            "agent_ids": copy.deepcopy(template.get("agent_ids") if isinstance(template.get("agent_ids"), list) else []),
            "tool_ids": copy.deepcopy(template.get("tool_ids") if isinstance(template.get("tool_ids"), list) else []),
            "provider_profile_id": str(model.get("provider_profile_id") or "").strip(),
            "chat_agent_id": str(model.get("chat_agent_id") or "").strip(),
            "nodes": preview_nodes,
        }


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
        create_record = workflow_template_version_record(
            None,
            template,
            agent_definitions=self.agent_definitions,
            tool_definitions=self.tool_definitions,
            mode="create",
        )
        if create_record:
            template["version_history"] = [create_record]
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
            version_record = workflow_template_version_record(
                current,
                updated,
                agent_definitions=self.agent_definitions,
                tool_definitions=self.tool_definitions,
                mode="update",
            )
            if version_record:
                current_history = current.get("version_history") if isinstance(current.get("version_history"), list) else []
                updated["version_history"] = normalize_workflow_template_version_history([version_record, *copy.deepcopy(current_history)])
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
                health = provider_profile_health(profile)
                # Mask API key for security
                api_key = str(public_profile.get("api_key") or "")
                if api_key:
                    public_profile["api_key_masked"] = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    del public_profile["api_key"]
                public_profile["has_api_key"] = bool(api_key) or not bool(health.get("key_required", True))
                public_profile["key_required"] = bool(health.get("key_required", True))
                public_profile["status"] = str(health.get("status") or "warning")
                public_profile["missing_fields"] = list(health.get("missing_fields") or [])
                items.append(public_profile)
        return {"provider_profiles": items}


    def list_provider_catalog(self) -> dict[str, Any]:
        """List known vendor presets so a profile can be created from a pick + key."""
        return {"provider_catalog": copy.deepcopy(PROVIDER_CATALOG)}


    def create_provider_profile_from_catalog(
        self,
        vendor_id: str,
        *,
        api_key: str = "",
        name: str = "",
        models: list[Any] | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Materialize a provider profile from a catalogue vendor + API key.

        Falls back to a non-empty sentinel key for local/no-key vendors
        (e.g. Ollama) so LLMClient's empty-key guard does not block them.
        """
        vendor = provider_catalog_by_id(vendor_id)
        if not vendor:
            raise ValueError(f"unknown provider catalog vendor: {vendor_id or '(empty)'}")
        key_required = bool(vendor.get("key_required", True))
        resolved_key = str(api_key or "").strip()
        if key_required and not resolved_key:
            raise ValueError(f"vendor {vendor_id} requires an api_key")
        if not resolved_key:
            resolved_key = "sk-no-key-required"

        profile_models = models if isinstance(models, list) else list(vendor.get("models") or [])
        profile_name = str(name or "").strip() or str(vendor.get("name") or vendor_id).strip()
        payload = {
            "id": str(uuid.uuid4().hex[:10]),
            "name": profile_name,
            "vendor_id": vendor_id,
            "provider": str(vendor.get("provider") or "openai").strip(),
            "base_url": str(vendor.get("base_url") or "").strip(),
            "api_key": resolved_key,
            "models": profile_models,
            "is_default": bool(is_default),
            "key_required": key_required,
        }
        return self.create_provider_profile(payload)


    def create_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new provider profile."""
        profile_id = str(payload.get("id") or uuid.uuid4().hex[:8]).strip()
        name = str(payload.get("name") or "").strip()
        provider = str(payload.get("provider") or "openai").strip()
        base_url = str(payload.get("base_url") or "").strip()
        api_key = str(payload.get("api_key") or "").strip()
        models = payload.get("models") if isinstance(payload.get("models"), list) else []
        is_default = bool(payload.get("is_default"))
        vendor_id = str(payload.get("vendor_id") or payload.get("vendor") or "").strip()
        key_required_source = payload if "key_required" in payload else {"base_url": base_url, "vendor_id": vendor_id, "provider": provider}
        key_required = _provider_profile_key_required(key_required_source)

        if not name:
            name = f"{provider.title()} Profile"

        with self.lock:
            existing_profiles = [
                item for item in self.provider_profiles
                if isinstance(item, dict) and str(item.get("id") or "").strip() == profile_id
            ]
            existing = existing_profiles[-1] if existing_profiles else {}
            resolved_api_key = api_key or str(existing.get("api_key") or "").strip()
            if not resolved_api_key and not key_required:
                resolved_api_key = "sk-no-key-required"
            created_at = str(existing.get("created_at") or now_iso()).strip() or now_iso()
            profile: dict[str, Any] = {
                "id": profile_id,
                "name": name,
                "vendor_id": vendor_id,
                "provider": provider,
                "base_url": base_url,
                "api_key": resolved_api_key,
                "models": models,
                "is_default": is_default,
                "key_required": key_required,
                "created_at": created_at,
                "updated_at": now_iso(),
            }

            updated_profiles: list[dict[str, Any]] = []
            for item in self.provider_profiles:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "").strip()
                if item_id == profile_id:
                    continue
                if is_default:
                    item = dict(item)
                    item["is_default"] = False
                updated_profiles.append(item)
            updated_profiles.append(profile)
            self.provider_profiles = updated_profiles
        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        health = provider_profile_health(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        result["has_api_key"] = bool(profile.get("api_key")) or not bool(health.get("key_required", True))
        result["key_required"] = bool(health.get("key_required", True))
        result["status"] = str(health.get("status") or "warning")
        result["missing_fields"] = list(health.get("missing_fields") or [])
        return result


    def test_provider_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ping a provider endpoint with a 1-token request to verify the link.

        Accepts either a saved ``profile_id`` or raw ``{provider, base_url,
        api_key, model}`` values so a draft can be tested before saving.
        """
        profile_id = str(payload.get("profile_id") or "").strip()
        if profile_id:
            with self.lock:
                saved = self.provider_profile_by_id(profile_id)
                profile = copy.deepcopy(saved) if saved else None
        else:
            model = str(payload.get("model") or "").strip()
            profile = {
                "id": "test",
                "provider": str(payload.get("provider") or payload.get("vendor") or "openai").strip(),
                "base_url": str(payload.get("base_url") or "").strip(),
                "api_key": str(payload.get("api_key") or "").strip(),
                "models": [model] if model else [],
                "key_required": bool(payload.get("key_required", True)),
            }
        if not profile:
            return {"success": False, "error": "provider profile not found", "model": ""}
        client = LLMClient(profile)
        if not client.api_key:
            return {
                "success": False,
                "error": "API key not configured",
                "provider": client.provider,
                "base_url": client.base_url,
                "model": "",
            }
        model = (client.models[0] if client.models else "") or str(payload.get("model") or "").strip()
        response = client.chat(
            [ChatMessage(role="user", content="ping")],
            model=model or None,
            max_tokens=8,
            timeout=15,
        )
        # If the chat ping failed (often a bad/unknown model name), still report
        # connectivity via /models so the user can pick a valid model.
        models: list[str] = []
        models_error = ""
        if not response.success:
            listed = client.list_models()
            models = listed.get("models") or []
            models_error = listed.get("error") or ""
        return {
            "success": response.success,
            "provider": client.provider,
            "base_url": client.base_url,
            "model": response.model or model,
            "latency_ms": round(float(response.latency_ms or 0), 1),
            "total_tokens": response.total_tokens,
            "content_preview": (response.content or "")[:120],
            "error": response.error,
            "available_models": models,
            "models_error": models_error,
        }

    def list_provider_models(self, payload: dict[str, Any]) -> dict[str, Any]:
        """List available model ids from a provider endpoint (GET /models)."""
        profile_id = str(payload.get("profile_id") or "").strip()
        if profile_id:
            with self.lock:
                saved = self.provider_profile_by_id(profile_id)
                profile = copy.deepcopy(saved) if saved else None
        else:
            model = str(payload.get("model") or "").strip()
            profile = {
                "id": "models",
                "provider": str(payload.get("provider") or payload.get("vendor") or "openai").strip(),
                "base_url": str(payload.get("base_url") or "").strip(),
                "api_key": str(payload.get("api_key") or "").strip(),
                "models": [model] if model else [],
                "key_required": bool(payload.get("key_required", True)),
            }
        if not profile:
            return {"success": False, "models": [], "error": "provider profile not found"}
        client = LLMClient(profile)
        if not client.api_key:
            return {"success": False, "models": [], "error": "API key not configured"}
        result = client.list_models()
        return {
            "success": bool(result.get("success")),
            "models": list(result.get("models") or []),
            "provider": client.provider,
            "base_url": client.base_url,
            "error": result.get("error") or "",
        }


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
            if "vendor_id" in payload or "vendor" in payload:
                profile["vendor_id"] = str(payload.get("vendor_id") or payload.get("vendor") or "").strip()
            if "provider" in payload:
                profile["provider"] = str(payload["provider"] or "openai").strip()
            if "base_url" in payload:
                profile["base_url"] = str(payload["base_url"] or "").strip()
            if "key_required" in payload:
                profile["key_required"] = bool(payload.get("key_required"))
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
            if not str(profile.get("api_key") or "").strip() and not _provider_profile_key_required(profile):
                profile["api_key"] = "sk-no-key-required"

            profile["updated_at"] = now_iso()

        self.save_provider_profiles()

        # Return masked version
        result = dict(profile)
        health = provider_profile_health(profile)
        if result.get("api_key"):
            result["api_key_masked"] = result["api_key"][:8] + "..." + result["api_key"][-4:] if len(result["api_key"]) > 12 else "***"
            del result["api_key"]
        result["has_api_key"] = bool(profile.get("api_key")) or not bool(health.get("key_required", True))
        result["key_required"] = bool(health.get("key_required", True))
        result["status"] = str(health.get("status") or "warning")
        result["missing_fields"] = list(health.get("missing_fields") or [])
        return result


    def delete_provider_profile(self, profile_id: str) -> None:
        """Delete a provider profile."""
        profile_id = str(profile_id or "").strip()
        with self.lock:
            original_count = len(self.provider_profiles)
            self.provider_profiles = [
                item
                for item in self.provider_profiles
                if not (isinstance(item, dict) and str(item.get("id") or "").strip() == profile_id)
            ]
            if len(self.provider_profiles) == original_count:
                raise ValueError("provider profile not found")
        self.save_provider_profiles()
