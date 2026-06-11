"""Agent Executor for RelayGraph.

Implements ReAct (Reasoning + Acting) pattern for agent execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .llm_client import LLMClient, ChatMessage, LLMResponse, build_agent_system_prompt, tool_definition_for_llm
from .orchestration.workspace_mutations import apply_artifact_write, apply_workflow_edit
from .tools.registry import TOOL_SIDE_EFFECTS, ToolSideEffect, tool_side_effect


@dataclass
class AgentStep:
    """A single step in agent execution."""

    step_number: int
    thought: str = ""
    action: str = ""
    action_input: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    error: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentExecutionResult:
    """Result of an agent execution."""

    success: bool
    final_answer: str
    steps: list[AgentStep] = field(default_factory=list)
    total_tokens: int = 0
    total_steps: int = 0
    error: str = ""
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "final_answer": self.final_answer,
            "steps": [step.to_dict() for step in self.steps],
            "total_tokens": self.total_tokens,
            "total_steps": self.total_steps,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class AgentExecutor:
    """Executes agents using ReAct pattern."""

    def __init__(
        self,
        agent: dict[str, Any],
        llm_client: LLMClient,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], str] | None = None,
    ):
        """Initialize agent executor.

        Args:
            agent: Agent configuration (role, prompt, tools, etc.)
            llm_client: LLM client for making API calls
            tools: List of available tools
            tool_executor: Optional function to execute tools (tool_id, args) -> result
        """
        self.agent = agent
        self.llm_client = llm_client
        self.tools = tools
        self.tool_executor = tool_executor
        self.max_iterations = 10

    def _get_tool_by_id(self, tool_id: str) -> dict[str, Any] | None:
        """Get tool definition by ID."""
        return next((t for t in self.tools if t.get("id") == tool_id), None)

    def _parse_tool_call(self, content: str) -> tuple[str, dict[str, Any]] | None:
        """Parse tool call from LLM response.

        Supports multiple formats:
        1. JSON: {"tool": "tool_id", "arguments": {...}}
        2. Markdown code block: ```json\n{...}\n```
        3. Natural language: "I'll use the X tool with Y"
        """
        content = content.strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed["tool"], parsed.get("arguments", {})
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from code block
        json_match = re.search(r"```(?:json)?\s*\n?(.+?)\n?```", content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
                if isinstance(parsed, dict) and "tool" in parsed:
                    return parsed["tool"], parsed.get("arguments", {})
            except json.JSONDecodeError:
                pass

        # Try to find JSON-like structure anywhere in content
        json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}'
        match = re.search(json_pattern, content)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and "tool" in parsed:
                    return parsed["tool"], parsed.get("arguments", {})
            except json.JSONDecodeError:
                pass

        return None

    def _execute_tool(self, tool_id: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        tool = self._get_tool_by_id(tool_id)
        if not tool:
            return f"Error: Tool '{tool_id}' not found. Available tools: {', '.join(t.get('id', '') for t in self.tools)}"

        if self.tool_executor:
            try:
                return self.tool_executor(tool_id, arguments)
            except Exception as e:
                return f"Error executing tool '{tool_id}': {str(e)}"

        # Default: return tool info (simulated execution)
        return f"[Simulated] Tool '{tool_id}' called with arguments: {json.dumps(arguments, ensure_ascii=False)}"

    def run(self, user_input: str, context: dict[str, Any] | None = None) -> AgentExecutionResult:
        """Run the agent with the given input.

        Args:
            user_input: User's input/task
            context: Optional context (workspace info, previous outputs, etc.)

        Returns:
            AgentExecutionResult with the execution trace and result
        """
        start_time = datetime.now()
        steps: list[AgentStep] = []
        total_tokens = 0

        # Build system prompt
        system_prompt = build_agent_system_prompt(self.agent, self.tools)

        # Add context if provided
        if context:
            context_str = "\n\nContext:\n"
            for key, value in context.items():
                context_str += f"- {key}: {json.dumps(value, ensure_ascii=False, indent=2)}\n"
            system_prompt = context_str + system_prompt

        # Build conversation history
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_input),
        ]

        for iteration in range(self.max_iterations):
            # Call LLM
            response = self.llm_client.chat(messages)

            if not response.success:
                return AgentExecutionResult(
                    success=False,
                    final_answer="",
                    steps=steps,
                    total_tokens=total_tokens,
                    total_steps=len(steps),
                    error=f"LLM error: {response.error}",
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                )

            total_tokens += response.total_tokens

            # Check if we have a final answer (no tool call)
            tool_call = self._parse_tool_call(response.content)

            if not tool_call:
                # No tool call = final answer
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return AgentExecutionResult(
                    success=True,
                    final_answer=response.content,
                    steps=steps,
                    total_tokens=total_tokens,
                    total_steps=len(steps),
                    execution_time_ms=execution_time,
                )

            # Execute tool
            tool_id, arguments = tool_call

            step = AgentStep(
                step_number=len(steps) + 1,
                thought=response.content,
                action=tool_id,
                action_input=arguments,
                timestamp=datetime.now().isoformat(),
            )

            # Execute tool and get observation
            observation = self._execute_tool(tool_id, arguments)
            step.observation = observation

            steps.append(step)

            # Add to conversation history
            messages.append(ChatMessage(role="assistant", content=response.content))
            messages.append(ChatMessage(role="user", content=f"Tool result:\n{observation}"))

        # Max iterations reached
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        return AgentExecutionResult(
            success=False,
            final_answer="",
            steps=steps,
            total_tokens=total_tokens,
            total_steps=len(steps),
            error="Maximum iterations reached without a final answer",
            execution_time_ms=execution_time,
        )


def create_workspace_tool_executor(
    workspace: dict[str, Any],
    server_config: Any = None,
    *,
    statuses: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> Callable[[str, dict[str, Any]], str]:
    """Create a tool executor for workspace-related tools.

    Args:
        workspace: Current workspace
        server_config: Server configuration for remote execution
        statuses: Latest server/GPU snapshots. When present, GPU tools report real state.
        jobs: Known jobs. Used for log/artifact context without mutating queues.

    Returns:
        Function that executes tools and returns results
    """

    workspace_snapshot = workspace if isinstance(workspace, dict) else {}
    status_snapshot = [item for item in (statuses or []) if isinstance(item, dict)]
    job_snapshot = [item for item in (jobs or []) if isinstance(item, dict)]

    def node_config(kind: str) -> dict[str, Any]:
        for node in workspace_snapshot.get("nodes") if isinstance(workspace_snapshot.get("nodes"), list) else []:
            if isinstance(node, dict) and str(node.get("kind") or "").strip() == kind:
                config = node.get("config") if isinstance(node.get("config"), dict) else {}
                return config
        return {}

    def split_values(value: Any) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            raw_items = [str(item or "") for item in value]
        else:
            raw_items = str(value or "").replace(",", "\n").splitlines()
        seen: set[str] = set()
        values: list[str] = []
        for raw in raw_items:
            item = str(raw or "").strip()
            if not item or item in seen:
                continue
            seen.add(item)
            values.append(item)
        return values

    def source_payload() -> dict[str, Any]:
        source = workspace_snapshot.get("source") if isinstance(workspace_snapshot.get("source"), dict) else {}
        inputs = workspace_snapshot.get("inputs") if isinstance(workspace_snapshot.get("inputs"), dict) else {}
        return {
            "goal_text": str(inputs.get("goal_text") or workspace_snapshot.get("brief") or source.get("idea_text") or "").strip(),
            "repo_urls": split_values(inputs.get("repo_urls") or source.get("repo_url")),
            "paper_urls": split_values(inputs.get("paper_urls") or source.get("paper_url")),
            "references": split_values(inputs.get("references")),
            "context_blocks": split_values(inputs.get("context_blocks")),
            "workspace_dir": str(workspace_snapshot.get("workspace_dir") or "").strip(),
        }

    def configured_run_command() -> str:
        return str(node_config("run.command").get("run_command") or "").strip()

    def workflow_nodes() -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for index, node in enumerate(workspace_snapshot.get("nodes") if isinstance(workspace_snapshot.get("nodes"), list) else []):
            if not isinstance(node, dict):
                continue
            config = node.get("config") if isinstance(node.get("config"), dict) else {}
            handler = node.get("handler") if isinstance(node.get("handler"), dict) else {}
            nodes.append(
                {
                    "order": index + 1,
                    "id": str(node.get("id") or "").strip(),
                    "kind": str(node.get("kind") or "").strip(),
                    "title": str(node.get("title") or node.get("kind") or "").strip(),
                    "agent_id": str(handler.get("agent_id") or "").strip(),
                    "input_mapping": node.get("input_mapping") if isinstance(node.get("input_mapping"), dict) else {},
                    "output_key": str(node.get("output_key") or "").strip(),
                    "configured_fields": sorted(key for key, value in config.items() if str(value or "").strip())[:8],
                }
            )
        return nodes

    def gpu_candidates(min_free_mib: int = 0, server_id: str = "") -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for status in status_snapshot:
            sid = str(status.get("id") or "").strip()
            if server_id and sid != server_id:
                continue
            if status.get("online") is False:
                continue
            for gpu in status.get("gpus") if isinstance(status.get("gpus"), list) else []:
                if not isinstance(gpu, dict):
                    continue
                free_mib = int(float(gpu.get("memory_free_mib") or 0))
                util = int(float(gpu.get("gpu_util") or 100))
                state = str(gpu.get("state") or "").strip() or ("idle" if util <= 10 else "busy")
                candidates.append(
                    {
                        "server_id": sid,
                        "server_name": str(status.get("name") or sid).strip(),
                        "gpu_index": gpu.get("index"),
                        "name": str(gpu.get("name") or "").strip(),
                        "memory_free_mib": free_mib,
                        "memory_total_mib": int(float(gpu.get("memory_total_mib") or 0)),
                        "gpu_util": util,
                        "state": state,
                        "eligible": state == "idle" and free_mib >= min_free_mib,
                        "collected_at": str(status.get("collected_at") or "").strip(),
                    }
                )
        candidates.sort(key=lambda item: (bool(item["eligible"]), item["memory_free_mib"], -item["gpu_util"]), reverse=True)
        return candidates

    def automation_selected_gpu() -> dict[str, Any]:
        automation = workspace_snapshot.get("automation") if isinstance(workspace_snapshot.get("automation"), dict) else {}
        resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
        scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
        selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
        return selected

    def execution_package_payload() -> dict[str, Any]:
        automation = workspace_snapshot.get("automation") if isinstance(workspace_snapshot.get("automation"), dict) else {}
        manifest = automation.get("reproduction_manifest") if isinstance(automation.get("reproduction_manifest"), dict) else {}
        bundle = manifest.get("execution_bundle") if isinstance(manifest.get("execution_bundle"), dict) else {}
        package_manifest = bundle.get("package_manifest") if isinstance(bundle.get("package_manifest"), dict) else {}
        resource = automation.get("resource_orchestration") if isinstance(automation.get("resource_orchestration"), dict) else {}
        scheduler = resource.get("scheduler") if isinstance(resource.get("scheduler"), dict) else {}
        selected = scheduler.get("selected") if isinstance(scheduler.get("selected"), dict) else {}
        backfill = automation.get("evidence_backfill") if isinstance(automation.get("evidence_backfill"), dict) else {}
        backfill_items = backfill.get("items") if isinstance(backfill.get("items"), list) else []
        readiness = automation.get("execution_readiness") if isinstance(automation.get("execution_readiness"), dict) else {}
        command_script = bundle.get("command_script") if isinstance(bundle.get("command_script"), dict) else {}
        return {
            "status": str(bundle.get("status") or manifest.get("status") or "draft").strip(),
            "ready_to_execute": bool(bundle.get("ready_to_execute")),
            "next_action": bundle.get("next_action") if isinstance(bundle.get("next_action"), dict) else {},
            "target": bundle.get("target") if isinstance(bundle.get("target"), dict) else {},
            "commands": package_manifest.get("commands") if isinstance(package_manifest.get("commands"), dict) else {},
            "paths": package_manifest.get("paths") if isinstance(package_manifest.get("paths"), dict) else {},
            "dataset_discovery": package_manifest.get("dataset_discovery") if isinstance(package_manifest.get("dataset_discovery"), dict) else {},
            "scheduler": {
                "status": str(scheduler.get("status") or "").strip(),
                "mode": str(scheduler.get("mode") or "").strip(),
                "policy": str(scheduler.get("policy") or "").strip(),
                "summary": str(scheduler.get("summary") or "").strip(),
                "selected": selected,
                "candidate_count": int(scheduler.get("candidate_count") or 0),
                "ready_count": int(scheduler.get("ready_count") or 0),
            },
            "missing": bundle.get("missing") if isinstance(bundle.get("missing"), list) else [],
            "backfill": {
                "status": str(backfill.get("status") or "").strip(),
                "summary": str(backfill.get("summary") or "").strip(),
                "ready_count": int(backfill.get("ready_count") or 0),
                "items": [
                    {
                        "node_kind": str(item.get("node_kind") or "").strip(),
                        "field": str(item.get("field") or "").strip(),
                        "label": str(item.get("label") or "").strip(),
                        "value": str(item.get("value") or "").strip(),
                        "status": str(item.get("status") or "").strip(),
                    }
                    for item in backfill_items[:12]
                    if isinstance(item, dict)
                ],
            },
            "readiness": {
                "status": str(readiness.get("status") or "").strip(),
                "summary": str(readiness.get("summary") or "").strip(),
                "gate": readiness.get("gate") if isinstance(readiness.get("gate"), dict) else {},
            },
            "script": {
                "shell": str(command_script.get("shell") or "bash").strip(),
                "status": str(command_script.get("status") or "").strip(),
                "ready": bool(command_script.get("ready")),
                "summary": str(command_script.get("summary") or "").strip(),
                "text": str(command_script.get("text") or "")[:4000],
            },
        }

    def workspace_artifacts() -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for node in workspace_snapshot.get("nodes") if isinstance(workspace_snapshot.get("nodes"), list) else []:
            if not isinstance(node, dict):
                continue
            for artifact in node.get("artifacts") if isinstance(node.get("artifacts"), list) else []:
                if isinstance(artifact, dict):
                    artifacts.append(artifact)
        automation = workspace_snapshot.get("automation") if isinstance(workspace_snapshot.get("automation"), dict) else {}
        context = automation.get("execution_context") if isinstance(automation.get("execution_context"), dict) else {}
        for output in context.get("outputs") if isinstance(context.get("outputs"), list) else []:
            if isinstance(output, dict) and output.get("artifact_count"):
                artifacts.append(
                    {
                        "label": str(output.get("title") or output.get("node_kind") or "输出").strip(),
                        "path": str(output.get("key") or "").strip(),
                        "source": "context.outputs",
                    }
                )
        return artifacts

    def job_workspace_id(job: dict[str, Any]) -> str:
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        return str(metadata.get("workspace_id") or job.get("workspace_id") or "").strip()

    def executor(tool_id: str, arguments: dict[str, Any]) -> str:
        """Execute a workspace tool against the current workspace snapshot."""
        arguments = arguments if isinstance(arguments, dict) else {}

        if tool_id == "workflow.plan":
            nodes = workflow_nodes()
            return json.dumps(
                {
                    "status": "planned" if nodes else "draft",
                    "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                    "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                    "node_count": len(nodes),
                    "nodes": nodes,
                    "run_command": configured_run_command(),
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "web.search":
            source = source_payload()
            query = str(arguments.get("query") or source.get("goal_text") or "").strip()
            results = [
                {"type": "repo", "url": url, "source": "workspace.input"}
                for url in source["repo_urls"]
            ] + [
                {"type": "paper", "url": url, "source": "workspace.input"}
                for url in source["paper_urls"]
            ]
            return json.dumps(
                {
                    "status": "seeded" if results else "draft",
                    "query": query,
                    "results": results,
                    "note": "当前工具返回工作台已有搜索种子；真正联网搜索应由受控搜索工具接管。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "repo.clone":
            source = source_payload()
            repo_url = str(arguments.get("repo_url") or (source["repo_urls"][0] if source["repo_urls"] else "")).strip()
            workspace_dir = str(arguments.get("workspace_dir") or source.get("workspace_dir") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if repo_url and workspace_dir else "draft",
                    "repo_url": repo_url,
                    "workspace_dir": workspace_dir,
                    "dry_run": True,
                    "message": "已生成克隆计划，等待工作流节点提交实际任务。" if repo_url else "等待 repo_url。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "gpu.inspect":
            min_free_mib = int(float(arguments.get("min_free_mib") or 0))
            candidates = gpu_candidates(min_free_mib=min_free_mib, server_id=str(arguments.get("server_id") or "").strip())
            return json.dumps(
                {
                    "status": "inspected" if status_snapshot else "draft",
                    "server_count": len(status_snapshot),
                    "gpu_count": len(candidates),
                    "idle_count": len([item for item in candidates if item["eligible"]]),
                    "candidates": candidates[:12],
                    "selected": candidates[0] if candidates else automation_selected_gpu(),
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "gpu.allocate":
            min_free_mib = int(float(arguments.get("min_free_mib") or 0))
            if not min_free_mib:
                min_free_gib = float(arguments.get("min_free_memory_gib") or node_config("gpu.allocate").get("min_free_memory_gib") or 0)
                min_free_mib = int(min_free_gib * 1024)
            config = node_config("gpu.allocate")
            server_id = str(arguments.get("server_id") or config.get("server_id") or "").strip()
            candidates = gpu_candidates(min_free_mib=min_free_mib, server_id=server_id)
            selected = next((item for item in candidates if item["eligible"]), None)
            if not selected and not candidates:
                scheduler_selected = automation_selected_gpu()
                selected = scheduler_selected if scheduler_selected else None
            return json.dumps(
                {
                    "status": "allocated" if selected else "blocked",
                    "selected": selected,
                    "candidate_count": len(candidates),
                    "min_free_mib": min_free_mib,
                    "dry_run": True,
                    "message": "已选出候选 GPU，等待 run.command 使用。" if selected else "没有满足条件的 GPU 候选。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id in {"dataset.find", "repo.search"}:
            config = node_config("dataset.find")
            source = source_payload()
            query = str(arguments.get("query") or config.get("query") or source.get("goal_text") or "").strip()
            roots = split_values(arguments.get("data_roots") or config.get("data_roots"))
            hints = split_values(arguments.get("dataset_hints") or config.get("dataset_hints"))
            for value in source["references"]:
                if value not in roots and (value.startswith("/") or value.startswith("./") or "data" in value.lower()):
                    roots.append(value)
                elif value not in hints:
                    hints.append(value)
            return json.dumps(
                {
                    "status": "ready" if roots or hints or query else "draft",
                    "query": query,
                    "data_roots": roots,
                    "dataset_hints": hints,
                    "message": "数据线索已收集，可回填 dataset.find。" if roots or hints else "等待数据集名称、路径或参考链接。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id in {"env.inspect", "env.infer"}:
            env = workspace_snapshot.get("env") if isinstance(workspace_snapshot.get("env"), dict) else {}
            infer_config = node_config("env.infer")
            prepare_config = node_config("env.prepare")
            manifests = split_values(arguments.get("manifest_paths") or infer_config.get("manifest_paths"))
            setup_command = str(arguments.get("setup_command") or prepare_config.get("setup_command") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if manifests or setup_command else "draft",
                    "env_name": str(env.get("name") or infer_config.get("env_name") or prepare_config.get("env_name") or "").strip(),
                    "env_manager": str(env.get("manager") or prepare_config.get("env_manager") or "conda").strip(),
                    "python_version": str(env.get("python") or infer_config.get("python_version") or "").strip(),
                    "manifest_paths": manifests,
                    "setup_command": setup_command,
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "job.run":
            run_config = node_config("run.command")
            command = str(arguments.get("command") or run_config.get("run_command") or "").strip()
            return json.dumps(
                {
                    "status": "ready" if command else "draft",
                    "dry_run": True,
                    "command": command,
                    "server_id": str(arguments.get("server_id") or run_config.get("server_id") or "").strip(),
                    "gpu_index": str(arguments.get("gpu_index") or run_config.get("gpu_index") or "").strip(),
                    "message": "已生成任务提交包；由工作流运行按钮真正入队。" if command else "等待 run.command。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "execution.package":
            package = execution_package_payload()
            return json.dumps(
                {
                    "status": "ready" if package["ready_to_execute"] else package["status"] or "draft",
                    "workspace_id": str(workspace_snapshot.get("id") or "").strip(),
                    "workspace_name": str(workspace_snapshot.get("name") or "").strip(),
                    "package": package,
                    "message": "执行包已就绪，可按工作流提交。" if package["ready_to_execute"] else "执行包仍有缺口，请查看 missing/backfill/readiness。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "log.read":
            workspace_id = str(workspace_snapshot.get("id") or "").strip()
            related_jobs = [
                job for job in job_snapshot
                if job_workspace_id(job) == workspace_id
            ]
            related_jobs.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
            latest = related_jobs[0] if related_jobs else {}
            return json.dumps(
                {
                    "status": "found" if latest else "draft",
                    "job_id": str(latest.get("id") or "").strip(),
                    "job_status": str(latest.get("status") or "").strip(),
                    "log_path": str(latest.get("log_path") or "").strip(),
                    "message": "找到最近任务日志入口。" if latest else "当前工作台还没有关联任务日志。",
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "artifact.read":
            artifacts = workspace_artifacts()
            return json.dumps(
                {
                    "status": "read" if artifacts else "draft",
                    "artifacts": artifacts[:20],
                    "artifact_count": len(artifacts),
                },
                ensure_ascii=False,
                indent=2,
            )

        elif tool_id == "artifact.write":
            try:
                result = apply_artifact_write(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "").strip(),
                    label=str(arguments.get("label") or arguments.get("title") or "").strip(),
                    path=str(arguments.get("path") or arguments.get("content_path") or "").strip(),
                    content=str(arguments.get("content") or arguments.get("text") or "").strip(),
                    output_key=str(arguments.get("output_key") or "").strip(),
                    artifact_type=str(arguments.get("type") or arguments.get("artifact_type") or "note").strip(),
                )
                return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        elif tool_id == "workflow.edit":
            patch = arguments.get("config")
            if not isinstance(patch, dict):
                patch = arguments.get("patch") if isinstance(arguments.get("patch"), dict) else {}
            try:
                result = apply_workflow_edit(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "").strip(),
                    config_patch=patch,
                )
                return json.dumps({"status": "updated", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        elif tool_id == "report.write":
            try:
                result = apply_artifact_write(
                    workspace_snapshot,
                    node_id=str(arguments.get("node_id") or "").strip(),
                    node_kind=str(arguments.get("node_kind") or "eval.report").strip(),
                    label=str(arguments.get("label") or arguments.get("title") or "report").strip(),
                    path=str(arguments.get("path") or arguments.get("report_path") or "").strip(),
                    content=str(arguments.get("content") or arguments.get("text") or arguments.get("report") or "").strip(),
                    output_key=str(arguments.get("output_key") or "eval_report").strip(),
                    artifact_type="report",
                )
                return json.dumps({"status": "written", **result}, ensure_ascii=False, indent=2)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

        elif tool_id == "chat.write":
            message = arguments.get("message", "")
            return json.dumps({
                "status": "written",
                "message": message,
            }, ensure_ascii=False, indent=2)

        else:
            side_effect = tool_side_effect(tool_id)
            meta = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip(), {})
            implemented = bool(meta.get("implemented"))
            if side_effect != ToolSideEffect.READ and not implemented:
                return json.dumps(
                    {
                        "status": "simulated",
                        "tool": tool_id,
                        "side_effect": side_effect.value,
                        "arguments": arguments,
                        "message": f"Tool '{tool_id}' is not implemented yet; returning simulated payload.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            return json.dumps(
                {
                    "status": "simulated",
                    "tool": tool_id,
                    "arguments": arguments,
                    "message": f"Tool '{tool_id}' executed (simulated)",
                },
                ensure_ascii=False,
                indent=2,
            )

    return executor
