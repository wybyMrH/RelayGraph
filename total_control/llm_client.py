"""LLM Provider Client for RelayGraph.

Supports multiple providers: OpenAI, DeepSeek, Anthropic, and OpenAI-compatible APIs.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
from datetime import datetime


@dataclass
class LLMResponse:
    """Response from an LLM API call."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    latency_ms: float = 0.0

    @property
    def success(self) -> bool:
        return not self.error


@dataclass
class ChatMessage:
    """A single chat message."""

    role: str  # system, user, assistant, tool
    content: str
    name: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str = ""


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, profile: dict[str, Any]):
        """Initialize client with a provider profile.

        Args:
            profile: Provider profile dict with keys:
                - id: Profile ID
                - provider: Provider name (openai, deepseek, anthropic, etc.)
                - base_url: API base URL
                - api_key: API key
                - models: List of available models
        """
        self.profile_id = str(profile.get("id") or "")
        self.provider = str(profile.get("provider") or "openai").lower()
        self.base_url = str(profile.get("base_url") or "").rstrip("/")
        self.api_key = str(profile.get("api_key") or "")
        self.models = profile.get("models") if isinstance(profile.get("models"), list) else []

        # Set default base URLs for known providers
        if not self.base_url:
            if self.provider == "openai":
                self.base_url = "https://api.openai.com/v1"
            elif self.provider == "deepseek":
                self.base_url = "https://api.deepseek.com/v1"
            elif self.provider == "anthropic":
                self.base_url = "https://api.anthropic.com/v1"

    def _headers(self) -> dict[str, str]:
        """Get API headers for the provider."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.provider == "anthropic":
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_request_body(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Build request body for the provider."""
        if self.provider == "anthropic":
            # Anthropic uses a different format
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                else:
                    chat_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })

            body = {
                "model": model,
                "messages": chat_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
            }
            if system_msg:
                body["system"] = system_msg
        else:
            # OpenAI-compatible format
            chat_messages = []
            for msg in messages:
                msg_dict = {"role": msg.role, "content": msg.content}
                if msg.name:
                    msg_dict["name"] = msg.name
                if msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    msg_dict["tool_call_id"] = msg.tool_call_id
                chat_messages.append(msg_dict)

            body = {
                "model": model,
                "messages": chat_messages,
            }
            if kwargs.get("max_tokens"):
                body["max_tokens"] = kwargs["max_tokens"]
            if kwargs.get("temperature") is not None:
                body["temperature"] = kwargs["temperature"]
            if kwargs.get("tools"):
                body["tools"] = kwargs["tools"]
            if kwargs.get("tool_choice"):
                body["tool_choice"] = kwargs["tool_choice"]

        return body

    def _parse_response(self, response_data: dict[str, Any], model: str, latency_ms: float) -> LLMResponse:
        """Parse API response into LLMResponse."""
        if self.provider == "anthropic":
            content = ""
            if response_data.get("content"):
                for block in response_data["content"]:
                    if block.get("type") == "text":
                        content += block.get("text", "")

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                prompt_tokens=response_data.get("usage", {}).get("input_tokens", 0),
                completion_tokens=response_data.get("usage", {}).get("output_tokens", 0),
                total_tokens=response_data.get("usage", {}).get("input_tokens", 0) + response_data.get("usage", {}).get("output_tokens", 0),
                finish_reason=response_data.get("stop_reason", ""),
                raw_response=response_data,
                latency_ms=latency_ms,
            )
        else:
            # OpenAI-compatible format
            choices = response_data.get("choices", [])
            content = ""
            tool_calls = []
            finish_reason = ""

            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "") or ""
                tool_calls = message.get("tool_calls", [])
                finish_reason = choice.get("finish_reason", "")

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                prompt_tokens=response_data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_data.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response_data.get("usage", {}).get("total_tokens", 0),
                finish_reason=finish_reason,
                raw_response=response_data,
                latency_ms=latency_ms,
            )

    def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a chat request to the LLM.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to first in profile)
            **kwargs: Additional parameters (max_tokens, temperature, tools, etc.)

        Returns:
            LLMResponse with the result
        """
        if not self.api_key:
            return LLMResponse(
                content="",
                model="",
                provider=self.provider,
                error="API key not configured",
            )

        if not model:
            model = self.models[0] if self.models else "gpt-3.5-turbo"

        url = f"{self.base_url}/chat/completions"
        if self.provider == "anthropic":
            url = f"{self.base_url}/messages"

        body = self._build_request_body(messages, model, **kwargs)
        headers = self._headers()

        start_time = datetime.now()

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60)) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            return self._parse_response(response_data, model, latency_ms)

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                error=f"HTTP {e.code}: {error_body}",
            )
        except urllib.error.URLError as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                error=f"URL Error: {e.reason}",
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider,
                error=f"Error: {str(e)}",
            )

    def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        *,
        on_delta: Callable[[str, str, dict[str, Any]], None] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a streaming chat request and return the accumulated response."""
        if not self.api_key:
            return LLMResponse(
                content="",
                model="",
                provider=self.provider,
                error="API key not configured",
            )

        if not model:
            model = self.models[0] if self.models else "gpt-3.5-turbo"

        url = f"{self.base_url}/chat/completions"
        if self.provider == "anthropic":
            url = f"{self.base_url}/messages"

        body = self._build_request_body(messages, model, **kwargs)
        body["stream"] = True
        if self.provider != "anthropic":
            body.setdefault("stream_options", {"include_usage": True})
        headers = self._headers()
        start_time = datetime.now()
        content = ""
        finish_reason = ""
        usage: dict[str, Any] = {}
        raw_events: list[dict[str, Any]] = []

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60)) as response:
                for event_data in self._iter_sse_data(response):
                    if event_data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(event_data)
                    except json.JSONDecodeError:
                        continue
                    raw_events.append(chunk)
                    if self.provider == "anthropic":
                        piece, finish, chunk_usage = self._parse_anthropic_stream_chunk(chunk)
                    else:
                        piece, finish, chunk_usage = self._parse_openai_stream_chunk(chunk)
                    if chunk_usage:
                        usage.update(chunk_usage)
                    if finish:
                        finish_reason = finish
                    if not piece:
                        continue
                    content += piece
                    if on_delta:
                        on_delta(piece, content, chunk)

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                prompt_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                total_tokens=int(
                    usage.get("total_tokens")
                    or (
                        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
                        + int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
                    )
                ),
                finish_reason=finish_reason,
                raw_response={"stream": True, "events": raw_events[-20:]},
                latency_ms=latency_ms,
            )

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                error=f"HTTP {e.code}: {error_body}",
                raw_response={"stream": True, "partial": content},
            )
        except urllib.error.URLError as e:
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                error=f"URL Error: {e.reason}",
                raw_response={"stream": True, "partial": content},
            )
        except Exception as e:
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                error=f"Error: {str(e)}",
                raw_response={"stream": True, "partial": content},
            )

    @staticmethod
    def _iter_sse_data(response: Any) -> Iterator[str]:
        data_lines: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                if data_lines:
                    yield "\n".join(data_lines)
                    data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            yield "\n".join(data_lines)

    @staticmethod
    def _parse_openai_stream_chunk(chunk: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        choices = chunk.get("choices") if isinstance(chunk.get("choices"), list) else []
        usage = chunk.get("usage") if isinstance(chunk.get("usage"), dict) else {}
        if not choices:
            return "", "", usage
        choice = choices[0] if isinstance(choices[0], dict) else {}
        delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
        piece = str(delta.get("content") or "")
        finish_reason = str(choice.get("finish_reason") or "")
        return piece, finish_reason, usage

    @staticmethod
    def _parse_anthropic_stream_chunk(chunk: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        event_type = str(chunk.get("type") or "")
        usage: dict[str, Any] = {}
        if isinstance(chunk.get("message"), dict) and isinstance(chunk["message"].get("usage"), dict):
            usage.update(chunk["message"]["usage"])
        if isinstance(chunk.get("usage"), dict):
            usage.update(chunk["usage"])
        if event_type == "content_block_delta":
            delta = chunk.get("delta") if isinstance(chunk.get("delta"), dict) else {}
            if str(delta.get("type") or "") == "text_delta":
                return str(delta.get("text") or ""), "", usage
        if event_type == "message_delta":
            delta = chunk.get("delta") if isinstance(chunk.get("delta"), dict) else {}
            return "", str(delta.get("stop_reason") or ""), usage
        return "", "", usage

    def simple_chat(self, system_prompt: str, user_message: str, model: str | None = None, **kwargs) -> LLMResponse:
        """Simple chat with system and user message.

        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            LLMResponse with the result
        """
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        return self.chat(messages, model, **kwargs)


def tool_definition_for_llm(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a tool definition to LLM function calling format.

    Args:
        tool: Tool definition with id, label, description, etc.

    Returns:
        OpenAI-compatible function definition
    """
    return {
        "type": "function",
        "function": {
            "name": str(tool.get("id") or "unknown"),
            "description": str(tool.get("description") or ""),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }


def build_agent_node_system_prompt(
    agent: dict[str, Any],
    tools: list[dict[str, Any]],
    *,
    node_kind: str = "",
    output_key: str = "",
    output_format: str = "",
    node_goal: str = "",
) -> str:
    """Build a node-scoped system prompt without dumping full repository trees."""
    base = build_agent_system_prompt(agent, tools)
    sections: list[str] = [base.rstrip()]
    kind = str(node_kind or "").strip()
    if kind:
        sections.append(f"\nCurrent workflow node kind: {kind}")
    goal = str(node_goal or "").strip()
    if goal:
        sections.append(f"Node goal: {goal}")
    key = str(output_key or "").strip()
    if key:
        sections.append(f"Required output_key: {key}")
    fmt = str(output_format or "").strip()
    if fmt:
        sections.append(f"Expected output_format: {fmt}")
    sections.append(
        "\nRespond using Thought / Action / Action Input / Final Answer when helpful. "
        "Prefer artifact.write or workflow.edit to persist structured outputs."
    )
    return "\n".join(sections)


def build_agent_system_prompt(agent: dict[str, Any], tools: list[dict[str, Any]]) -> str:
    """Build system prompt for an agent with tool descriptions.

    Args:
        agent: Agent definition with role, prompt, etc.
        tools: List of available tools

    Returns:
        System prompt string
    """
    role = str(agent.get("role") or agent.get("id") or "assistant")
    base_prompt = str(agent.get("prompt") or "You are a helpful assistant.")

    tool_descriptions = []
    for tool in tools:
        tool_id = str(tool.get("id") or "")
        tool_label = str(tool.get("label") or tool_id)
        tool_desc = str(tool.get("description") or "")
        tool_descriptions.append(f"- {tool_id}: {tool_label}. {tool_desc}")

    if tool_descriptions:
        tools_section = "\n\nAvailable tools:\n" + "\n".join(tool_descriptions)
        tools_section += "\n\nTo use a tool, respond with JSON in this format:\n{\"tool\": \"tool_id\", \"arguments\": {...}}"
    else:
        tools_section = ""

    return f"""You are the {role} agent.

{base_prompt}
{tools_section}

Remember:
1. Think step by step before acting
2. Use tools when needed to accomplish tasks
3. Provide clear, helpful responses
4. If you cannot complete a task, explain why
"""
