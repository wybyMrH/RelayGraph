(function () {
  "use strict";

  function fallbackSafeId(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "item";
  }

  function fallbackParseTagList(value) {
    if (Array.isArray(value)) {
      return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
    }
    return Array.from(new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean)));
  }

  function fallbackPositiveNumberOrBlank(value) {
    const text = String(value ?? "").trim();
    if (!text) return "";
    const number = Number(text);
    return Number.isFinite(number) && number > 0 ? String(number) : "";
  }

  function normalizeWorkspaceToolDraft(tool = {}, index = 0, deps = {}) {
    const safeId = typeof deps.safeId === "function" ? deps.safeId : fallbackSafeId;
    const fallbackId = safeId(tool.label || tool.id || `tool-${index + 1}`);
    return {
      id: String(tool.id || fallbackId),
      label: String(tool.label || tool.display_name || `Tool ${index + 1}`),
      category: String(tool.category || "general"),
      capability: String(tool.capability || "read"),
      provider_profile_id: String(tool.provider_profile_id || ""),
      description: String(tool.description || ""),
      enabled: tool.enabled !== false,
      notes: String(tool.notes || ""),
    };
  }

  function normalizeWorkspaceAgentDraft(agent = {}, index = 0, toolIds = [], deps = {}) {
    const safeId = typeof deps.safeId === "function" ? deps.safeId : fallbackSafeId;
    const parseTagList = typeof deps.parseTagList === "function" ? deps.parseTagList : fallbackParseTagList;
    const positiveNumberOrBlank = typeof deps.positiveNumberOrBlank === "function"
      ? deps.positiveNumberOrBlank
      : fallbackPositiveNumberOrBlank;
    const roleSeed = String(agent.role || agent.name || `agent-${index + 1}`).trim() || `agent-${index + 1}`;
    const tools = Array.isArray(agent.tools) ? agent.tools.map((item) => String(item || "").trim()).filter(Boolean) : parseTagList(agent.tools || "");
    const allowedTools = new Set(toolIds.map((item) => String(item || "").trim()).filter(Boolean));
    const filteredTools = allowedTools.size ? tools.filter((tool) => allowedTools.has(tool)) : tools;
    const outputFormat = ["", "text", "json"].includes(String(agent.output_format || ""))
      ? String(agent.output_format || "")
      : "";
    return {
      id: String(agent.id || safeId(roleSeed)),
      name: String(agent.name || `Agent ${index + 1}`),
      role: String(agent.role || safeId(roleSeed)),
      prompt: String(agent.prompt || ""),
      tools: filteredTools,
      provider_profile_id: String(agent.provider_profile_id || ""),
      max_iterations: positiveNumberOrBlank(agent.max_iterations),
      timeout_seconds: positiveNumberOrBlank(agent.timeout_seconds),
      output_format: outputFormat,
      enabled: agent.enabled !== false,
    };
  }

  function normalizeWorkspaceModelDraft(model = {}) {
    const routingMode = ["workspace_default", "agent_override"].includes(String(model.routing_mode || ""))
      ? String(model.routing_mode)
      : "workspace_default";
    return {
      provider_profile_id: String(model.provider_profile_id || ""),
      routing_mode: routingMode,
      chat_agent_id: String(model.chat_agent_id || ""),
      notes: String(model.notes || ""),
    };
  }

  function normalizeWorkspaceToolsDraft(tools = [], deps = {}) {
    const normalizeToolDraft = typeof deps.normalizeWorkspaceToolDraft === "function"
      ? deps.normalizeWorkspaceToolDraft
      : normalizeWorkspaceToolDraft;
    const defaultTools = typeof deps.defaultWorkspaceTools === "function"
      ? deps.defaultWorkspaceTools
      : () => [];
    const list = (Array.isArray(tools) ? tools : [])
      .map((item, index) => normalizeToolDraft(item, index))
      .filter(Boolean);
    return list.length ? list : defaultTools();
  }

  window.WorkspaceDraftNormalizers = {
    normalizeWorkspaceAgentDraft,
    normalizeWorkspaceModelDraft,
    normalizeWorkspaceToolDraft,
    normalizeWorkspaceToolsDraft,
  };
})();
