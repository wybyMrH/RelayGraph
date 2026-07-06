from __future__ import annotations

from pathlib import Path
from types import MethodType
import time

from total_control.llm_client import LLMResponse
from total_control.state import TotalControlState


def _state(monkeypatch, tmp_path) -> TotalControlState:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    paths = {
        "JOBS_PATH": runtime_dir / "jobs.json",
        "WORKSPACES_PATH": runtime_dir / "workspaces.json",
        "PROVIDER_PROFILES_PATH": runtime_dir / "provider_profiles.json",
        "TOOL_DEFINITIONS_PATH": runtime_dir / "tool_definitions.json",
        "AGENT_DEFINITIONS_PATH": runtime_dir / "agent_definitions.json",
        "WORKFLOW_TEMPLATES_PATH": runtime_dir / "workflow_templates.json",
    }
    for path in paths.values():
        path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("total_control.secrets_crypto.MASTER_KEY_PATH", runtime_dir / ".master_key")
    for module in ("total_control.state.base", "total_control.state.persistence"):
        for name, path in paths.items():
            monkeypatch.setattr(f"{module}.{name}", path)
    return TotalControlState(Path("config/servers.toml"))


def _assistant_message_with_reflection(workspace: dict) -> dict:
    for message in reversed(workspace.get("chat") or []):
        reflection = message.get("context_reflection") if isinstance(message, dict) else {}
        if isinstance(reflection, dict) and reflection.get("summary"):
            return message
    raise AssertionError("expected a context reflection")


def test_dismiss_context_reflection_does_not_write_context_blocks(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Reflection Test", "brief": "Keep cockpit focused", "source_type": "idea"})

        first = state.append_workspace_chat(
            workspace["id"],
            {"text": "驾驶舱必须只负责状态校验和执行可视化，不要放配置表单。"},
        )["workspace"]
        first_message = _assistant_message_with_reflection(first)

        dismissed = state.dismiss_workspace_context_reflection(workspace["id"], first_message["id"])["workspace"]
        dismissed_message = _assistant_message_with_reflection(dismissed)
        assert dismissed_message["context_reflection"]["status"] == "dismissed"
        assert dismissed_message["context_reflection"]["dismissed_at"]
        assert dismissed["inputs"]["context_blocks"] == []

        second = state.append_workspace_chat(
            workspace["id"],
            {"text": "后续必须保持驾驶舱简洁，配置继续留在配置中心。"},
        )["workspace"]
        second_message = _assistant_message_with_reflection(second)
        accepted = state.accept_workspace_context_reflection(workspace["id"], second_message["id"])["workspace"]

        assert accepted["inputs"]["context_blocks"] == [second_message["context_reflection"]["summary"]]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_chat_stream_completion_event_after_workspace_state_update(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Stream Test", "brief": "Stream reply", "source_type": "idea"})
        events = []
        original_publish = state.publish_event

        def fake_reply(self, workspace_id, text, agent_id, *, use_llm, delta_callback=None):
            if delta_callback:
                delta_callback("流", "流")
                delta_callback("式", "流式")
            return "流式完成", None, "Stream Agent"

        def capture_event(event_type, **kwargs):
            payload = kwargs.get("payload") if isinstance(kwargs.get("payload"), dict) else {}
            if event_type == "chat.message.delta":
                message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
                events.append((event_type, message.get("status"), message.get("text")))
            if event_type == "chat.message.completed":
                message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
                live = state.workspace_by_id(workspace["id"]) or {}
                live_message = next(
                    (
                        item for item in live.get("chat", [])
                        if isinstance(item, dict) and item.get("id") == message.get("id")
                    ),
                    {},
                )
                events.append((event_type, live_message.get("status"), live_message.get("text")))
            return original_publish(event_type, **kwargs)

        state._workspace_chat_reply = MethodType(fake_reply, state)
        state.publish_event = capture_event

        result = state.append_workspace_chat(
            workspace["id"],
            {"text": "请流式回复", "stream": True, "use_llm": False},
        )
        assistant_id = result["messages"][1]["id"]

        deadline = time.time() + 3
        while time.time() < deadline and not any(event[0] == "chat.message.completed" for event in events):
            time.sleep(0.02)

        assert ("chat.message.delta", "streaming", "流") in events
        assert ("chat.message.delta", "streaming", "流式") in events
        assert ("chat.message.completed", "completed", "流式完成") in events
        persisted = state.workspace_by_id(workspace["id"])
        assistant = next(item for item in persisted["chat"] if item["id"] == assistant_id)
        assert assistant["status"] == "completed"
        assert assistant["text"] == "流式完成"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_chat_stream_background_failure_persists_failed_message(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace({"name": "Stream Failure", "brief": "Stream failure", "source_type": "idea"})
        events = []
        original_publish = state.publish_event

        def fake_reply(self, workspace_id, text, agent_id, *, use_llm, delta_callback=None):
            if delta_callback:
                delta_callback("半", "半")
            raise RuntimeError("stream exploded")

        def capture_event(event_type, **kwargs):
            payload = kwargs.get("payload") if isinstance(kwargs.get("payload"), dict) else {}
            if event_type in {"chat.message.delta", "chat.message.failed"}:
                message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
                events.append((event_type, message.get("status"), message.get("text"), message.get("error")))
            return original_publish(event_type, **kwargs)

        state._workspace_chat_reply = MethodType(fake_reply, state)
        state.publish_event = capture_event

        result = state.append_workspace_chat(
            workspace["id"],
            {"text": "请流式回复", "stream": True, "use_llm": False},
        )
        assistant_id = result["messages"][1]["id"]

        deadline = time.time() + 3
        while time.time() < deadline and not any(event[0] == "chat.message.failed" for event in events):
            time.sleep(0.02)

        assert ("chat.message.delta", "streaming", "半", "") in events
        failed_events = [event for event in events if event[0] == "chat.message.failed"]
        assert failed_events
        assert failed_events[-1][1] == "failed"
        assert "stream exploded" in failed_events[-1][3]
        persisted = state.workspace_by_id(workspace["id"])
        assistant = next(item for item in persisted["chat"] if item["id"] == assistant_id)
        assert assistant["status"] == "failed"
        assert "stream exploded" in assistant["error"]
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)


def test_chat_stream_llm_token_delta_uses_ready_no_key_provider(monkeypatch, tmp_path):
    state = _state(monkeypatch, tmp_path)
    try:
        workspace = state.create_workspace(
            {
                "name": "LLM Stream Test",
                "brief": "Stream from fake local provider",
                "source_type": "idea",
                "model": {"provider_profile_id": "local-llm", "routing_mode": "workspace_default"},
                "agents": [
                    {
                        "id": "planner",
                        "name": "Planner",
                        "role": "planner",
                        "tools": [],
                    }
                ],
            }
        )
        state.provider_profiles = [
            {
                "id": "local-llm",
                "name": "Local LLM",
                "provider": "openai",
                "base_url": "http://127.0.0.1:11434/v1",
                "models": ["local-test-model"],
                "key_required": False,
            }
        ]
        events = []
        original_publish = state.publish_event

        def fake_chat_stream(self, messages, model=None, on_delta=None, **kwargs):
            del messages, kwargs
            accumulated = ""
            for piece in ("真", "机", "流"):
                accumulated += piece
                if on_delta:
                    on_delta(piece, accumulated, {"choices": [{"delta": {"content": piece}}]})
            return LLMResponse(
                content=accumulated,
                model=model or "local-test-model",
                provider=self.provider,
                total_tokens=9,
            )

        def capture_event(event_type, **kwargs):
            payload = kwargs.get("payload") if isinstance(kwargs.get("payload"), dict) else {}
            if event_type in {"chat.message.delta", "chat.message.completed"}:
                message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
                events.append(
                    (
                        event_type,
                        payload.get("message_id") or message.get("id"),
                        payload.get("accumulated") or message.get("text"),
                        message.get("status"),
                    )
                )
            return original_publish(event_type, **kwargs)

        monkeypatch.setattr("total_control.llm_client.LLMClient.chat_stream", fake_chat_stream)
        monkeypatch.setattr(state, "publish_event", capture_event)

        result = state.append_workspace_chat(
            workspace["id"],
            {"text": "请流式回复", "agent_id": "planner", "stream": True, "use_llm": True},
        )
        assistant_id = result["messages"][1]["id"]
        deadline = time.time() + 3
        while time.time() < deadline and not any(event[0] == "chat.message.completed" for event in events):
            time.sleep(0.02)

        assert ("chat.message.delta", assistant_id, "真", "streaming") in events
        assert ("chat.message.delta", assistant_id, "真机", "streaming") in events
        assert ("chat.message.delta", assistant_id, "真机流", "streaming") in events
        assert ("chat.message.completed", assistant_id, "真机流", "completed") in events
        persisted = state.workspace_by_id(workspace["id"])
        assistant = next(item for item in persisted["chat"] if item["id"] == assistant_id)
        assert assistant["status"] == "completed"
        assert assistant["text"] == "真机流"
        assert assistant["agent_execution"]["provider_profile_id"] == "local-llm"
    finally:
        state.stop_event.set()
        state.thread.join(timeout=1)
