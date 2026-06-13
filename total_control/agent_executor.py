"""Agent Executor for RelayGraph.

Implements ReAct (Reasoning + Acting) pattern for agent execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .llm_client import (
    LLMClient,
    ChatMessage,
    LLMResponse,
    build_agent_node_system_prompt,
    build_agent_system_prompt,
    tool_definition_for_llm,
)
from .tools.registry import create_workspace_tool_executor


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
        step_callback: Callable[[AgentStep], None] | None = None,
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
        self.step_callback = step_callback
        configured = agent.get("max_iterations")
        self.max_iterations = int(configured) if configured not in (None, "") else 10

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
        node_kind = str((context or {}).get("node_kind") or "").strip()
        output_key = str((context or {}).get("output_key") or "").strip()
        output_format = str((context or {}).get("output_format") or "").strip()
        node_goal = str((context or {}).get("node_goal") or "").strip()
        if node_kind or output_key:
            system_prompt = build_agent_node_system_prompt(
                self.agent,
                self.tools,
                node_kind=node_kind,
                output_key=output_key,
                output_format=output_format,
                node_goal=node_goal,
            )
        else:
            system_prompt = build_agent_system_prompt(self.agent, self.tools)

        # Add compact runtime context if provided
        if context:
            compact_context = {
                key: value
                for key, value in context.items()
                if key not in {"node_kind", "output_key", "output_format", "node_goal"}
            }
            if compact_context:
                context_str = "\n\nRuntime context:\n"
                for key, value in compact_context.items():
                    serialized = json.dumps(value, ensure_ascii=False, indent=2)
                    if len(serialized) > 2400:
                        serialized = serialized[:2400] + "…"
                    context_str += f"- {key}: {serialized}\n"
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
            if self.step_callback:
                self.step_callback(step)

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
