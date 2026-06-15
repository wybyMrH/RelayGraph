#!/usr/bin/env python3
"""Phase 3 #1 — real provider smoke.

Exercises the real LLM API path (LLMClient non-stream + stream, and an
AgentExecutor tool-call → final-answer loop) against a configured provider
profile. Never requires a committed key: it reads from the local profile
store or environment, and skips (exit 0) when nothing is configured so it is
safe to run in CI.

Pick a profile by, in priority order:

  1. ``--profile-id <id>``         read from data/provider_profiles.json
  2. ``--vendor <id>`` + key       build an ad-hoc profile from the catalogue
                                   (``--api-key`` or ``TC_SMOKE_API_KEY``)
  3. environment fallback          ``TC_SMOKE_VENDOR`` / ``TC_SMOKE_API_KEY``
                                   / ``TC_SMOKE_BASE_URL`` / ``TC_SMOKE_MODEL``

Examples::

    python temp/provider_smoke.py --vendor deepseek --api-key sk-...
    python temp/provider_smoke.py --profile-id <id-from-config-center>
    TC_SMOKE_VENDOR=ollama python temp/provider_smoke.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from total_control.constants_pkg.paths import PROVIDER_PROFILES_PATH  # noqa: E402
from total_control.constants_pkg.provider_catalog import provider_catalog_by_id  # noqa: E402
from total_control.llm_client import ChatMessage, LLMClient  # noqa: E402
from total_control.secrets_crypto import decrypt_secret  # noqa: E402
from total_control.agent_executor import AgentExecutor  # noqa: E402


def _merge_saved_profile_versions(profiles: list[dict[str, Any]], profile_id: str) -> dict[str, Any] | None:
    merged: dict[str, Any] | None = None
    for item in profiles:
        if not isinstance(item, dict) or item.get("id") != profile_id:
            continue
        current = dict(item)
        current["api_key"] = decrypt_secret(str(current.get("api_key") or ""))
        if merged is None:
            merged = current
            continue
        for key in ("name", "provider", "base_url", "created_at", "updated_at"):
            value = str(current.get(key) or "").strip()
            if value:
                merged[key] = value
        if isinstance(current.get("models"), list) and current.get("models"):
            merged["models"] = list(current["models"])
        if "is_default" in current:
            merged["is_default"] = bool(current.get("is_default"))
        if str(current.get("api_key") or "").strip():
            merged["api_key"] = str(current.get("api_key") or "").strip()
    return merged


def _read_profile(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.profile_id:
        profiles = []
        if PROVIDER_PROFILES_PATH.exists():
            try:
                profiles = json.loads(PROVIDER_PROFILES_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                profiles = []
        match = _merge_saved_profile_versions(profiles, args.profile_id)
        if not match:
            print(f"[skip] profile id '{args.profile_id}' not found in {PROVIDER_PROFILES_PATH}")
        return match

    vendor_id = (args.vendor or os.environ.get("TC_SMOKE_VENDOR") or "").strip().lower()
    api_key = (args.api_key or os.environ.get("TC_SMOKE_API_KEY") or "").strip()
    base_url = (args.base_url or os.environ.get("TC_SMOKE_BASE_URL") or "").strip()
    model = (args.model or os.environ.get("TC_SMOKE_MODEL") or "").strip()

    if not vendor_id and not base_url:
        return None  # nothing configured → skip

    provider = "openai"
    models = []
    if vendor_id:
        vendor = provider_catalog_by_id(vendor_id)
        if not vendor:
            print(f"[skip] unknown vendor '{vendor_id}'")
            return None
        provider = vendor.get("provider") or "openai"
        base_url = base_url or vendor.get("base_url") or ""
        models = list(vendor.get("models") or [])
        if not api_key and vendor.get("key_required", True):
            print(f"[skip] vendor '{vendor_id}' needs --api-key / TC_SMOKE_API_KEY")
            return None
        if not vendor.get("key_required", True) and not api_key:
            api_key = "sk-no-key-required"
    if model:
        models = [model] if not models else [model] + [m for m in models if m != model]
    return {
        "id": "smoke",
        "name": f"smoke:{vendor_id or 'custom'}",
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "models": models,
    }


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def run(profile: dict[str, Any]) -> int:
    client = LLMClient(profile)
    model = profile.get("models") or [""]
    model_name = model[0] if isinstance(model, list) and model else ""
    print(f"\nprovider={client.provider} base_url={client.base_url} model={model_name or '(default)'}")
    if not client.api_key:
        return _check("api key present", False, "LLMClient has no api_key")

    results: list[bool] = []
    deltas_seen = 0

    # 1) non-stream chat
    resp = client.chat(
        [ChatMessage(role="user", content="Reply with exactly: PONG. Do not include any reasoning.")],
        max_tokens=256,
    )
    results.append(
        _check(
            "non-stream chat",
            resp.success and bool(resp.content),
            (f"tokens={resp.total_tokens}" if resp.success else resp.error),
        )
    )

    # 2) streaming chat
    def on_delta(delta: str, accumulated: str, _raw: dict[str, Any]) -> None:
        nonlocal deltas_seen
        if delta:
            deltas_seen += 1

    sresp = client.chat_stream(
        [ChatMessage(role="user", content="Count from 1 to 3. Output only the final answer, with no reasoning.")],
        on_delta=on_delta,
        max_tokens=256,
    )
    results.append(
        _check(
            "stream chat",
            sresp.success and bool(sresp.content) and deltas_seen > 0,
            (f"deltas={deltas_seen}" if sresp.success else sresp.error),
        )
    )

    # 3) agent tool-call → final answer (read-only echo tool)
    def tool_executor(tool_id: str, arguments: dict[str, Any]) -> str:
        return f"{tool_id} observed: {json.dumps(arguments, ensure_ascii=False)}"

    tools = [{"id": "probe.read", "description": "Return the observed value for a key.", "schema": {"key": "str"}}]
    agent = {
        "id": "smoke-agent",
        "name": "Smoke",
        "role": "tester",
        "prompt": "Use the probe.read tool to observe key 'alpha', then report the observed value.",
        "tools": ["probe.read"],
        "max_iterations": 3,
    }
    executor = AgentExecutor(
        agent=agent,
        llm_client=client,
        tools=tools,
        tool_executor=tool_executor,
    )
    result = executor.run("Observe key 'alpha' via probe.read and tell me what you observed.")
    tool_calls = sum(1 for step in result.steps if str(step.action or "").strip())
    # Some providers answer directly without a tool call; either is acceptable as
    # long as the loop completed with a final answer.
    results.append(
        _check(
            "agent loop final answer",
            result.success and bool(result.final_answer),
            f"steps={result.total_steps} tool_calls={tool_calls} tokens={result.total_tokens}",
        )
    )
    if tool_calls:
        _check("agent invoked a tool", True, f"{tool_calls} call(s)")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Real provider smoke for RelayGraph")
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--vendor", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--model", default="")
    args = parser.parse_args()

    profile = _read_profile(args)
    if not profile:
        print("[skip] no provider configured — set --vendor/--api-key or --profile-id")
        print("        (safe no-op; no committed keys required)")
        return 0
    return run(profile)


if __name__ == "__main__":
    raise SystemExit(main())
