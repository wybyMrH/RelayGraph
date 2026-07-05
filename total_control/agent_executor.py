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
from .tools.registry import TOOL_SIDE_EFFECTS, ToolSideEffect, create_workspace_tool_executor
from .workspace.execution.agent_trace import (
    compact_tool_arguments,
    compact_tool_observation,
    make_agent_trace_event,
    tool_observation_failed,
)


def _tool_side_effect(tool_id: str) -> str:
    entry = TOOL_SIDE_EFFECTS.get(str(tool_id or "").strip())
    if not entry:
        return ""
    side = entry.get("side_effect")
    return side.value if isinstance(side, ToolSideEffect) else str(side or "")


def _tool_runtime_metadata(observation: str) -> dict[str, str]:
    try:
        payload = json.loads(str(observation or "").strip() or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for source_key, target_key in (
        ("job_id", "job_id"),
        ("run_id", "run_id"),
        ("runtime_control", "runtime_control"),
        ("runtime_side_effect", "runtime_side_effect"),
        ("status", "runtime_status"),
    ):
        value = str(payload.get(source_key) or "").strip()
        if value:
            result[target_key] = value
    return result


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
    side_effect: str = ""
    controlled: bool = False
    job_id: str = ""
    run_id: str = ""
    runtime_control: str = ""
    runtime_side_effect: str = ""
    runtime_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "error": self.error,
            "timestamp": self.timestamp,
            "side_effect": self.side_effect,
            "controlled": self.controlled,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "runtime_control": self.runtime_control,
            "runtime_side_effect": self.runtime_side_effect,
            "runtime_status": self.runtime_status,
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
    max_iterations: int = 0
    timeout_seconds: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "final_answer": self.final_answer,
            "steps": [step.to_dict() for step in self.steps],
            "total_tokens": self.total_tokens,
            "total_steps": self.total_steps,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "timed_out": self.timed_out,
            "cancelled": self.cancelled,
            "model": self.model,
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
        token_callback: Callable[[str, str], None] | None = None,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
        timeout_seconds: float | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ):
        """Initialize agent executor.

        Args:
            agent: Agent configuration (role, prompt, tools, etc.)
            llm_client: LLM client for making API calls
            tools: List of available tools
            tool_executor: Optional function to execute tools (tool_id, args) -> result
            step_callback: Optional step notification callback
            token_callback: Optional streaming token callback
            event_callback: Optional fine-grained trace event callback (event_type, payload)
            timeout_seconds: Optional wall-clock budget across the whole loop.
            cancel_check: Optional callable returning True when the run should abort.
        """
        self.agent = agent
        self.llm_client = llm_client
        self.tools = tools
        self.tool_executor = tool_executor
        self.step_callback = step_callback
        self.token_callback = token_callback
        self.event_callback = event_callback
        configured = agent.get("max_iterations")
        self.max_iterations = int(configured) if configured not in (None, "") else 10
        self.timeout_seconds = float(timeout_seconds) if timeout_seconds not in (None, "") else None
        self.cancel_check = cancel_check

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

    def _emit_trace_event(self, event_type: str, **fields: Any) -> None:
        # 发布细粒度 trace 事件
        if not self.event_callback:
            return
        payload = make_agent_trace_event(event_type, **fields)
        if payload:
            self.event_callback(event_type, payload)

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
        last_model = ""

        for iteration in range(self.max_iterations):
            # Cancel/timeout checks happen between iterations, so a long single
            # provider/tool call is not interrupted mid-flight but the loop yields
            # control before the next step.
            if self.cancel_check and self.cancel_check():
                return AgentExecutionResult(
                    success=False,
                    final_answer="",
                    steps=steps,
                    total_tokens=total_tokens,
                    total_steps=len(steps),
                    error="agent cancelled",
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    max_iterations=self.max_iterations,
                    timeout_seconds=self.timeout_seconds or 0.0,
                    cancelled=True,
                    model=last_model,
                )
            if self.timeout_seconds is not None and (datetime.now() - start_time).total_seconds() > self.timeout_seconds:
                return AgentExecutionResult(
                    success=False,
                    final_answer="",
                    steps=steps,
                    total_tokens=total_tokens,
                    total_steps=len(steps),
                    error=f"agent timeout after {self.timeout_seconds}s",
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    max_iterations=self.max_iterations,
                    timeout_seconds=self.timeout_seconds,
                    timed_out=True,
                    model=last_model,
                )
            # Call LLM
            if self.token_callback or self.event_callback:
                stream_state = {"mode": "undecided"}

                def on_stream_delta(delta: str, accumulated: str, _raw: dict[str, Any]) -> None:
                    text = str(accumulated or "")
                    mode = stream_state["mode"]
                    if mode == "blocked":
                        return
                    if mode == "undecided":
                        stripped = text.lstrip()
                        if not stripped:
                            return
                        if stripped.startswith("{") or stripped.startswith("```"):
                            stream_state["mode"] = "blocked"
                            return
                        stream_state["mode"] = "emit"
                    if self.token_callback:
                        self.token_callback(delta, accumulated)
                    self._emit_trace_event(
                        "agent.thought.delta",
                        step_number=len(steps) + 1,
                        delta=str(delta or ""),
                        accumulated=text,
                    )

                response = self.llm_client.chat_stream(messages, on_delta=on_stream_delta)
                if not response.success and not response.content:
                    response = self.llm_client.chat(messages)
            else:
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
                    max_iterations=self.max_iterations,
                    timeout_seconds=self.timeout_seconds or 0.0,
                    model=last_model,
                )

            total_tokens += response.total_tokens
            if getattr(response, "model", ""):
                last_model = response.model

            # Check if we have a final answer (no tool call)
            tool_call = self._parse_tool_call(response.content)

            if not tool_call:
                # No tool call = final answer
                final_answer = str(response.content or "")
                if final_answer.strip():
                    self._emit_trace_event(
                        "agent.answer.delta",
                        step_number=len(steps) + 1,
                        accumulated=final_answer,
                    )
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return AgentExecutionResult(
                    success=True,
                    final_answer=final_answer,
                    steps=steps,
                    total_tokens=total_tokens,
                    total_steps=len(steps),
                    execution_time_ms=execution_time,
                    max_iterations=self.max_iterations,
                    timeout_seconds=self.timeout_seconds or 0.0,
                    model=last_model,
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

            # Record the tool's permission policy on the step so the run trace
            # shows the tier (read / mutate_config / mutate_runtime / dangerous)
            # and whether runtime tools were controlled via the job queue.
            step.side_effect = _tool_side_effect(tool_id)
            step.controlled = step.side_effect == ToolSideEffect.MUTATE_RUNTIME.value

            self._emit_trace_event(
                "agent.tool.called",
                step_number=step.step_number,
                tool_id=tool_id,
                arguments_summary=compact_tool_arguments(arguments),
                side_effect=step.side_effect,
                controlled=step.controlled,
            )

            # Execute tool and get observation
            observation = self._execute_tool(tool_id, arguments)
            step.observation = observation
            runtime_metadata = _tool_runtime_metadata(observation)
            step.job_id = runtime_metadata.get("job_id", "")
            step.run_id = runtime_metadata.get("run_id", "")
            step.runtime_control = runtime_metadata.get("runtime_control", "")
            step.runtime_side_effect = runtime_metadata.get("runtime_side_effect", "")
            step.runtime_status = runtime_metadata.get("runtime_status", "")
            tool_failed = tool_observation_failed(observation)
            self._emit_trace_event(
                "agent.tool.failed" if tool_failed else "agent.tool.result",
                step_number=step.step_number,
                tool_id=tool_id,
                observation_summary=compact_tool_observation(observation),
                status="failed" if tool_failed else "ok",
                job_id=step.job_id,
                run_id=step.run_id,
                runtime_control=step.runtime_control,
                runtime_side_effect=step.runtime_side_effect,
                runtime_status=step.runtime_status,
            )

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
            max_iterations=self.max_iterations,
            timeout_seconds=self.timeout_seconds or 0.0,
            model=last_model,
        )
