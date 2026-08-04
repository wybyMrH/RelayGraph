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

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function textList(value) {
    if (Array.isArray(value)) {
      return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
    }
    return Array.from(new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean)));
  }

  function agentToolIds(agent = {}, options = {}) {
    const explicit = options.rawToolIds;
    if (explicit !== undefined) return textList(explicit);
    return textList(agent.tools || []);
  }

  function itemLabel(item, fallback = "") {
    return item?.label || item?.name || item?.id || fallback;
  }

  function agentHealth(agent = {}, options = {}) {
    const deps = {
      providerProfileKind: options.providerProfileKind,
      providerProfileIsValid: options.providerProfileIsValid,
    };
    const providerProfileKind = fn(deps, "providerProfileKind", () => "llm");
    const providerProfileIsValid = fn(deps, "providerProfileIsValid", (profile) => Boolean(profile));
    const toolDefinitions = Array.isArray(options.toolDefinitions) ? options.toolDefinitions : [];
    const providerProfiles = Array.isArray(options.providerProfiles) ? options.providerProfiles : [];
    const toolIndex = new Map(toolDefinitions.map((tool) => [String(tool?.id || "").trim(), tool]).filter(([id]) => id));
    const profileIndex = new Map(providerProfiles.map((profile) => [String(profile?.id || "").trim(), profile]).filter(([id]) => id));
    const issues = [];

    agentToolIds(agent, options).forEach((toolId) => {
      const tool = toolIndex.get(toolId);
      if (!tool) {
        issues.push({ severity: "warning", code: "missing_tool", message: `缺少工具：${toolId}` });
      } else if (tool.enabled === false) {
        issues.push({ severity: "warning", code: "disabled_tool", message: `工具已停用：${itemLabel(tool, toolId)}` });
      }
    });

    const profileId = String(agent.provider_profile_id || "").trim();
    if (profileId) {
      const profile = profileIndex.get(profileId);
      if (!profile) {
        issues.push({ severity: "warning", code: "missing_provider_profile", message: `Provider Profile 不可用：${profileId}` });
      } else if (providerProfileKind(profile) !== "llm") {
        issues.push({ severity: "warning", code: "non_llm_provider_profile", message: `Provider Profile 不可用：${itemLabel(profile, profileId)}` });
      } else if (!providerProfileIsValid(profile)) {
        issues.push({ severity: "warning", code: "invalid_provider_profile", message: `Provider Profile 不可用：${itemLabel(profile, profileId)}` });
      }
    } else {
      const usableDefault = providerProfiles.some((profile) => (
        providerProfileKind(profile) === "llm" && providerProfileIsValid(profile)
      ));
      if (!usableDefault) {
        issues.push({ severity: "warning", code: "missing_default_llm_route", message: "未找到可用默认 LLM 路由" });
      }
    }

    const enabled = agent.enabled !== false;
    const status = !enabled ? "blocked" : issues.length ? "warning" : "ready";
    return {
      status,
      label: !enabled ? "停用" : issues.length ? `${issues.length} 提示` : "就绪",
      issues,
    };
  }

  function agentHealthBadgeMarkup(health = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const status = String(health.status || "ready");
    const styleStatus = status === "warning" ? "blocked" : status;
    const label = String(health.label || (status === "ready" ? "就绪" : "提示"));
    return `<span class="state ${escapeFor(deps, styleStatus)}">${escapeFor(deps, label)}</span>`;
  }

  function agentHealthWarningMarkup(health = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const issues = Array.isArray(health.issues) ? health.issues : [];
    if (!issues.length) return "";
    return `
      <div class="workspace-agent-debug-warning-list">
        ${issues.slice(0, 5).map((issue) => `<div class="workspace-agent-debug-warning">${escapeFor(deps, issue.message || issue.code || "Agent 能力配置需要检查")}</div>`).join("")}
      </div>
    `;
  }

  window.ConfigCenterAgentHealth = {
    agentHealth,
    agentHealthBadgeMarkup,
    agentHealthWarningMarkup,
  };
})();
