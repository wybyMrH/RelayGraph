(function () {
  "use strict";

  function fallbackMakeClientId(prefix = "item") {
    return `${prefix}-${Date.now()}`;
  }

  function fallbackDeepClone(value, fallback) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return fallback;
    }
  }

  function normalizeWorkspaceContextReflection(reflection = null, deps = {}) {
    const makeClientId = typeof deps.makeClientId === "function" ? deps.makeClientId : fallbackMakeClientId;
    if (!reflection || typeof reflection !== "object") return null;
    const summary = String(reflection.summary || reflection.text || "").trim();
    if (!summary) return null;
    const status = ["suggested", "accepted", "dismissed"].includes(String(reflection.status || ""))
      ? String(reflection.status)
      : "suggested";
    const source = reflection.source && typeof reflection.source === "object" ? reflection.source : {};
    const confidence = Number(reflection.confidence);
    return {
      id: String(reflection.id || makeClientId("ctxref")),
      summary,
      status,
      confidence: Number.isFinite(confidence) ? Math.max(0, Math.min(1, confidence)) : 0,
      source: {
        type: String(source.type || "chat"),
        message_id: String(source.message_id || ""),
        user_message_id: String(source.user_message_id || ""),
        agent_execution_id: String(source.agent_execution_id || ""),
      },
      created_at: String(reflection.created_at || ""),
      accepted_at: String(reflection.accepted_at || ""),
      accepted_context_block: String(reflection.accepted_context_block || ""),
      dismissed_at: String(reflection.dismissed_at || ""),
      dismissed_reason: String(reflection.dismissed_reason || ""),
    };
  }

  function normalizeWorkspaceChatMessage(message = {}, index = 0, deps = {}) {
    const makeClientId = typeof deps.makeClientId === "function" ? deps.makeClientId : fallbackMakeClientId;
    const deepClone = typeof deps.deepClone === "function" ? deps.deepClone : fallbackDeepClone;
    const normalizeContextReflection = typeof deps.normalizeWorkspaceContextReflection === "function"
      ? deps.normalizeWorkspaceContextReflection
      : (reflection) => normalizeWorkspaceContextReflection(reflection, deps);
    const role = ["user", "assistant", "system"].includes(String(message.role || ""))
      ? String(message.role)
      : "user";
    const status = ["pending", "streaming", "completed", "failed"].includes(String(message.status || ""))
      ? String(message.status)
      : "completed";
    return {
      id: String(message.id || makeClientId(`chat-${index}`)),
      role,
      text: String(message.text || ""),
      status,
      error: String(message.error || ""),
      agent_id: String(message.agent_id || ""),
      agent_name: String(message.agent_name || ""),
      agent_execution: message.agent_execution && typeof message.agent_execution === "object" ? deepClone(message.agent_execution, {}) : {},
      context_reflection: normalizeContextReflection(message.context_reflection),
      created_at: String(message.created_at || ""),
      updated_at: String(message.updated_at || message.created_at || ""),
    };
  }

  function workspaceChatStatusText(status = "") {
    const value = String(status || "").trim();
    if (["pending", "streaming"].includes(value)) return "生成中";
    if (value === "failed") return "失败";
    return "";
  }

  window.WorkspaceChatNormalizers = {
    normalizeWorkspaceChatMessage,
    normalizeWorkspaceContextReflection,
    workspaceChatStatusText,
  };
})();
