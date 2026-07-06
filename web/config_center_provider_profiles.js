(function () {
  "use strict";

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeFor(options, value) {
    return (typeof options.escapeHtml === "function" ? options.escapeHtml : fallbackEscapeHtml)(value);
  }

  const providerVendorOptions = [
    { value: "openai", label: "OpenAI", base_url: "https://api.openai.com/v1" },
    { value: "anthropic", label: "Anthropic (Claude)", base_url: "https://api.anthropic.com/v1" },
    { value: "google", label: "Google Gemini", base_url: "https://generativelanguage.googleapis.com/v1beta/openai" },
    { value: "deepseek", label: "DeepSeek", base_url: "https://api.deepseek.com" },
    { value: "groq", label: "Groq", base_url: "https://api.groq.com/openai/v1" },
    { value: "openrouter", label: "OpenRouter", base_url: "https://openrouter.ai/api/v1" },
    { value: "mistral", label: "Mistral AI", base_url: "https://api.mistral.ai/v1" },
    { value: "cohere", label: "Cohere", base_url: "https://api.cohere.ai/compatibility/v1" },
    { value: "together", label: "Together AI", base_url: "https://api.together.xyz/v1" },
    { value: "qwen", label: "Qwen (通义千问)", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
    { value: "zhipu", label: "Zhipu (智谱GLM)", base_url: "https://open.bigmodel.cn/api/paas/v4" },
    { value: "moonshot", label: "Moonshot (Kimi)", base_url: "https://api.moonshot.cn/v1" },
    { value: "baichuan", label: "Baichuan (百川)", base_url: "https://api.baichuan-ai.com/v1" },
    { value: "minimax", label: "MiniMax", base_url: "https://api.minimax.chat/v1" },
    { value: "yi", label: "Yi (零一万物)", base_url: "https://api.01.ai/v1" },
    { value: "siliconflow", label: "SiliconFlow (硅基流动)", base_url: "https://api.siliconflow.cn/v1" },
    { value: "xiaomi-mimo", label: "MiMo (小米)", base_url: "https://api.xiaomimimo.com/v1" },
    { value: "ollama", label: "Ollama (本地)", base_url: "http://localhost:11434/v1", key_required: false },
    { value: "custom", label: "Custom (自定义)", base_url: "" },
  ];

  const searchProviderOptions = [
    { value: "", label: "未选择", base_url: "", key_required: true, endpoint_required: false },
    { value: "firecrawl", label: "Firecrawl", base_url: "https://api.firecrawl.dev", key_required: true, endpoint_required: false },
    { value: "serper", label: "Serper", base_url: "https://google.serper.dev/search", key_required: true, endpoint_required: false },
    { value: "duckduckgo", label: "DuckDuckGo", base_url: "", key_required: false, endpoint_required: false },
    { value: "endpoint", label: "HTTP Endpoint", base_url: "", key_required: false, endpoint_required: true },
  ];

  function vendorDefaultBaseUrl(vendor = "") {
    const entry = providerVendorOptions.find((item) => item.value === String(vendor || "").trim());
    return entry?.base_url || "";
  }

  function searchProviderOption(provider = "") {
    return searchProviderOptions.find((item) => item.value === String(provider || "").trim()) || searchProviderOptions[0];
  }

  function searchProviderOptionsMarkup(selectedValue = "", options = {}) {
    const selected = String(selectedValue || "").trim();
    return searchProviderOptions.map((option) => (
      `<option value="${escapeFor(options, option.value)}" ${option.value === selected ? "selected" : ""}>${escapeFor(options, option.label)}</option>`
    )).join("");
  }

  function providerVendorRequiresApiKey(vendor = "") {
    const entry = providerVendorOptions.find((item) => item.value === String(vendor || "").trim());
    return entry?.key_required !== false;
  }

  function baseUrlIsVendorDefault(url = "") {
    const value = String(url || "").trim();
    if (!value) return true;
    return providerVendorOptions.some((item) => item.base_url && item.base_url === value);
  }

  function providerProfileKind(profile = {}) {
    const value = String(profile?.kind || profile?.profile_type || "").trim().toLowerCase();
    return value === "search" || value === "web_search" || value === "web-search" ? "search" : "llm";
  }

  function providerProfileRequiresApiKey(profile = {}) {
    if (profile && profile.key_required === false) return false;
    if (providerProfileKind(profile) === "search") {
      return searchProviderOption(profile.vendor).key_required !== false;
    }
    const vendor = String(profile?.vendor || "").trim();
    const option = providerVendorOptions.find((item) => item.value === vendor);
    if (option && option.key_required === false) return false;
    const baseUrl = String(profile?.base_url || "").trim().toLowerCase();
    return !(baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1"));
  }

  function providerProfileIsValid(profile = {}) {
    if (providerProfileKind(profile) === "search") {
      const provider = String(profile.vendor || "").trim();
      const option = searchProviderOption(provider);
      return Boolean(
        profile
        && String(profile.label || "").trim()
        && provider
        && (!option.endpoint_required || String(profile.base_url || "").trim())
        && (!providerProfileRequiresApiKey(profile) || String(profile.api_key || "").trim() || profile.has_api_key),
      );
    }
    const keyRequired = providerProfileRequiresApiKey(profile);
    return Boolean(
      profile
      && String(profile.label || "").trim()
      && String(profile.vendor || "").trim()
      && String(profile.base_url || "").trim()
      && String(profile.model || "").trim()
      && (!keyRequired || String(profile.api_key || "").trim() || profile.has_api_key),
    );
  }

  function providerVendorOptionsMarkup(selectedValue = "", options = {}) {
    const selected = String(selectedValue || "").trim();
    return [
      `<option value="" ${selected ? "" : "selected"}>未选择</option>`,
      ...providerVendorOptions.map((option) => (
        `<option value="${escapeFor(options, option.value)}" ${option.value === selected ? "selected" : ""}>${escapeFor(options, option.label)}</option>`
      )),
    ].join("");
  }

  window.ConfigCenterProviderProfiles = {
    baseUrlIsVendorDefault,
    providerProfileIsValid,
    providerProfileKind,
    providerProfileRequiresApiKey,
    providerVendorOptions,
    providerVendorOptionsMarkup,
    providerVendorRequiresApiKey,
    searchProviderOption,
    searchProviderOptions,
    searchProviderOptionsMarkup,
    vendorDefaultBaseUrl,
  };
})();
