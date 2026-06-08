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
        json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+ "[^{}]*\}'
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
) -> Callable[[str, dict[str, Any]], str]:
    """Create a tool executor for workspace-related tools.

    Args:
        workspace: Current workspace
        server_config: Server configuration for remote execution

    Returns:
        Function that executes tools and returns results
    """

    def executor(tool_id: str, arguments: dict[str, Any]) -> str:
        """Execute a tool in the workspace context."""
        # For now, return simulated results
        # Real implementation would call actual functions

        if tool_id == "workflow.plan":
            return json.dumps({
                "status": "planned",
                "nodes": [
                    {"kind": "repo.clone", "title": "Clone repository"},
                    {"kind": "env.prepare", "title": "Setup environment"},
                    {"kind": "run.command", "title": "Run training"},
                ],
            }, ensure_ascii=False, indent=2)

        elif tool_id == "web.search":
            query = arguments.get("query", "")
            return json.dumps({
                "status": "searched",
                "query": query,
                "results": [
                    {"title": "Result 1", "url": "https://example.com/1"},
                    {"title": "Result 2", "url": "https://example.com/2"},
                ],
            }, ensure_ascii=False, indent=2)

        elif tool_id == "repo.clone":
            repo_url = arguments.get("repo_url", "")
            return json.dumps({
                "status": "cloned",
                "repo_url": repo_url,
                "message": f"Repository {repo_url} cloned successfully",
            }, ensure_ascii=False, indent=2)

        elif tool_id == "gpu.inspect":
            return json.dumps({
                "status": "inspected",
                "gpus": [
                    {"id": 0, "name": "RTX 3090", "memory_free": 20000, "utilization": 10},
                    {"id": 1, "name": "RTX 3090", "memory_free": 15000, "utilization": 30},
                ],
            }, ensure_ascii=False, indent=2)

        elif tool_id == "env.inspect":
            return json.dumps({
                "status": "inspected",
                "conda_envs": ["base", "py310", "ml-env"],
                "python_version": "3.10.12",
            }, ensure_ascii=False, indent=2)

        elif tool_id == "job.run":
            command = arguments.get("command", "")
            return json.dumps({
                "status": "submitted",
                "job_id": "job_123",
                "command": command,
                "message": f"Job submitted: {command}",
            }, ensure_ascii=False, indent=2)

        elif tool_id == "log.read":
            return "Log output:\n[INFO] Starting...\n[INFO] Processing...\n[INFO] Done."

        elif tool_id == "artifact.read":
            return json.dumps({
                "status": "read",
                "artifacts": workspace.get("artifacts", []),
            }, ensure_ascii=False, indent=2)

        elif tool_id == "chat.write":
            message = arguments.get("message", "")
            return json.dumps({
                "status": "written",
                "message": message,
            }, ensure_ascii=False, indent=2)

        else:
            return json.dumps({
                "status": "simulated",
                "tool": tool_id,
                "arguments": arguments,
                "message": f"Tool '{tool_id}' executed (simulated)",
            }, ensure_ascii=False, indent=2)

    return executor
