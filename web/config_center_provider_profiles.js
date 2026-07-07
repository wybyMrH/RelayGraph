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

  function normalizeProviderProfile(profile = {}, index = 0, deps = {}) {
    void index;
    const makeClientId = typeof deps.makeClientId === "function"
      ? deps.makeClientId
      : () => `provider-${Date.now().toString(36)}`;
    const getProfileKind = typeof deps.providerProfileKind === "function"
      ? deps.providerProfileKind
      : providerProfileKind;
    const requiresApiKey = typeof deps.providerProfileRequiresApiKey === "function"
      ? deps.providerProfileRequiresApiKey
      : providerProfileRequiresApiKey;
    // Required fields stay empty when absent so the UI can mark them as waiting
    // for user input instead of silently inventing Provider defaults.
    return {
      id: String(profile.id || makeClientId("provider")),
      kind: getProfileKind(profile),
      label: String(profile.label || "").trim(),
      vendor: String(profile.vendor || profile.provider || "").trim(),
      base_url: String(profile.base_url || "").trim(),
      model: String(profile.model || (Array.isArray(profile.models) ? profile.models[0] || "" : "")).trim(),
      api_key: String(profile.api_key || ""),
      api_key_masked: String(profile.api_key_masked || ""),
      has_api_key: Boolean(profile.has_api_key || profile.api_key || profile.api_key_masked),
      key_required: profile.key_required === false ? false : requiresApiKey(profile),
      status: String(profile.status || "").trim(),
      missing_fields: Array.isArray(profile.missing_fields) ? profile.missing_fields.map((item) => String(item || "").trim()).filter(Boolean) : [],
      is_default: Boolean(profile.is_default),
      is_new: Boolean(profile.is_new),
    };
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

  function configuredProviderProfiles(list = []) {
    return (Array.isArray(list) ? list : []).filter((profile) => providerProfileKind(profile) === "llm" && providerProfileIsValid(profile));
  }

  function searchProviderProfiles(list = []) {
    return (Array.isArray(list) ? list : []).filter((profile) => providerProfileKind(profile) === "search");
  }

  function configuredSearchProviderProfiles(list = []) {
    return searchProviderProfiles(list).filter((profile) => providerProfileIsValid(profile));
  }

  function selectedSearchProviderProfileId(list = [], draftProfileId = "") {
    const profiles = searchProviderProfiles(list);
    const draftId = String(draftProfileId || "").trim();
    if (draftId && profiles.some((profile) => profile.id === draftId)) return draftId;
    const defaultProfile = profiles.find((profile) => profile.is_default) || profiles[0];
    return defaultProfile?.id || "";
  }

  function providerRouteHealthStatus(health = {}, providerProfiles = []) {
    const source = health && typeof health === "object"
      ? health
      : { status: "draft", issues: [], blocking_count: 0, warning_count: 0, configured_profile_count: 0, profile_count: 0 };
    const configuredCount = Number(source.configured_profile_count || configuredProviderProfiles(providerProfiles).length || 0);
    const blockingCount = configuredCount ? 0 : Number(source.blocking_count || 0);
    return {
      ...source,
      effective_status: blockingCount ? "blocked" : configuredCount ? "ready" : source.status || "draft",
      effective_blocking_count: blockingCount,
    };
  }

  function providerHealthIssueLabel(issue = {}) {
    const prefix = issue.severity === "blocking" ? "阻塞" : issue.severity === "warning" ? "警告" : "提示";
    return `${prefix} · ${issue.message || issue.code || "Provider 路由待检查"}`;
  }

  function maskSecret(value) {
    const text = String(value || "");
    if (!text) return "未填写";
    if (text.length <= 8) return `${text.slice(0, 2)}***${text.slice(-1)}`;
    return `${text.slice(0, 4)}...${text.slice(-4)}`;
  }

  function providerProfileSecretLabel(profile = {}) {
    if (profile.api_key) return maskSecret(profile.api_key);
    if (profile.api_key_masked) return `已保存 ${profile.api_key_masked}`;
    return profile.has_api_key ? "已保存 API key" : "未填写";
  }

  function providerProfileLabel(profile) {
    if (!profile) return "未选择";
    if (providerProfileKind(profile) === "search") {
      const provider = searchProviderOption(profile.vendor).label || profile.vendor || "Search";
      return `${profile.label || profile.id} · Search · ${provider}`;
    }
    const vendor = providerVendorOptions.find((item) => item.value === profile.vendor)?.label || profile.vendor || "Custom";
    const model = String(profile.model || "").trim();
    return model ? `${profile.label} · ${vendor} · ${model}` : `${profile.label} · ${vendor}`;
  }

  window.ConfigCenterProviderProfiles = {
    baseUrlIsVendorDefault,
    configuredProviderProfiles,
    configuredSearchProviderProfiles,
    normalizeProviderProfile,
    providerProfileIsValid,
    providerProfileKind,
    providerProfileLabel,
    providerProfileRequiresApiKey,
    providerProfileSecretLabel,
    providerHealthIssueLabel,
    providerRouteHealthStatus,
    providerVendorOptions,
    providerVendorOptionsMarkup,
    providerVendorRequiresApiKey,
    searchProviderOption,
    searchProviderOptions,
    searchProviderOptionsMarkup,
    searchProviderProfiles,
    selectedSearchProviderProfileId,
    vendorDefaultBaseUrl,
  };
})();
