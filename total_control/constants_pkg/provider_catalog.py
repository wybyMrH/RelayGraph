"""Auto-split from constants.py — provider_catalog.

A catalogue of known LLM vendors so a profile can be created by picking a
vendor + pasting an API key, instead of typing base_url/protocol by hand.
The ``provider`` field is the wire protocol (``openai`` = OpenAI-compatible
``/chat/completions``; ``anthropic`` = ``/messages``), matching LLMClient.
Unregistered vendors are still supported via manual profile creation.
"""

from __future__ import annotations

from typing import Any

PROVIDER_CATALOG: list[dict[str, Any]] = [
    # === 国际主流提供商 ===
    {
        "id": "openai",
        "name": "OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"],
        "key_required": True,
        "website": "https://platform.openai.com",
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "key_required": True,
        "website": "https://console.anthropic.com",
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "provider": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "key_required": True,
        "website": "https://aistudio.google.com",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "provider": "openai",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
        "key_required": True,
        "website": "https://platform.deepseek.com",
    },
    {
        "id": "groq",
        "name": "Groq",
        "provider": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "key_required": True,
        "website": "https://console.groq.com",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "provider": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [],
        "key_required": True,
        "website": "https://openrouter.ai",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "provider": "openai",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-large-latest", "mistral-medium", "codestral-latest"],
        "key_required": True,
        "website": "https://console.mistral.ai",
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "provider": "openai",
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "models": ["command-r-plus", "command-r", "command-light"],
        "key_required": True,
        "website": "https://dashboard.cohere.com",
    },
    {
        "id": "together",
        "name": "Together AI",
        "provider": "openai",
        "base_url": "https://api.together.xyz/v1",
        "models": [],
        "key_required": True,
        "website": "https://api.together.xyz",
    },
    # === 中国主流提供商 ===
    {
        "id": "qwen",
        "name": "通义千问 (DashScope)",
        "provider": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-max", "qwen-turbo", "qwen-long"],
        "key_required": True,
        "website": "https://dashscope.console.aliyun.com",
    },
    {
        "id": "zhipu",
        "name": "智谱 GLM",
        "provider": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4-flash", "glm-4-air", "glm-z1-airx"],
        "key_required": True,
        "website": "https://open.bigmodel.cn",
    },
    {
        "id": "moonshot",
        "name": "月之暗面 (Kimi)",
        "provider": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-latest"],
        "key_required": True,
        "website": "https://platform.moonshot.cn",
    },
    {
        "id": "baichuan",
        "name": "百川智能",
        "provider": "openai",
        "base_url": "https://api.baichuan-ai.com/v1",
        "models": ["Baichuan4", "Baichuan3-Turbo", "Baichuan2-Turbo"],
        "key_required": True,
        "website": "https://platform.baichuan-ai.com",
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "provider": "openai",
        "base_url": "https://api.minimax.chat/v1",
        "models": ["abab6.5s-chat", "abab6.5-chat", "abab5.5-chat"],
        "key_required": True,
        "website": "https://platform.minimaxi.com",
    },
    {
        "id": "yi",
        "name": "零一万物 (Yi)",
        "provider": "openai",
        "base_url": "https://api.01.ai/v1",
        "models": ["yi-lightning", "yi-large", "yi-medium"],
        "key_required": True,
        "website": "https://platform.01.ai",
    },
    {
        "id": "siliconflow",
        "name": "硅基流动 (SiliconFlow)",
        "provider": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"],
        "key_required": True,
        "website": "https://cloud.siliconflow.cn",
    },
    # === 其他 ===
    {
        "id": "xiaomi-mimo",
        "name": "小米 MiMo",
        "provider": "openai",
        "base_url": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.5"],
        "key_required": True,
        "website": "https://api.xiaomimimo.com",
    },
    {
        "id": "ollama",
        "name": "Ollama（本地，无需 key）",
        "provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "models": [],
        "key_required": False,
        "website": "https://ollama.com",
    },
]


def provider_catalog_by_id(vendor_id: str) -> dict[str, Any] | None:
    normalized = str(vendor_id or "").strip().lower()
    return next((item for item in PROVIDER_CATALOG if str(item.get("id")) == normalized), None)
