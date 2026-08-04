(function () {
  "use strict";

  function workspaceAgentById(agentId, list) {
    return list.find((item) => item.id === agentId) || null;
  }

  function workspaceAgentDisplayName(handler = {}, deps = {}) {
    const findAgent = typeof deps.workspaceAgentById === "function"
      ? deps.workspaceAgentById
      : () => null;
    const linked = findAgent(String(handler.agent_id || ""));
    return linked?.name || handler.name || "未指派";
  }

  function workspaceAgentToolsSummary(agent, list, deps = {}) {
    const toolLabel = typeof deps.workspaceToolLabel === "function"
      ? deps.workspaceToolLabel
      : (toolId) => toolId || "未命名工具";
    const tools = Array.isArray(agent?.tools) ? agent.tools : [];
    if (!tools.length) return "未配置工具";
    return tools.map((toolId) => toolLabel(toolId, list)).join(" · ");
  }

  function sortWorkspaceAgentsByRecommendation(list, sourceType, deps = {}) {
    const agentLibraryTemplates = typeof deps.workspaceAgentLibraryTemplates === "function"
      ? deps.workspaceAgentLibraryTemplates
      : () => [];
    const order = agentLibraryTemplates(sourceType).map((agent) => agent.role);
    const rank = new Map(order.map((role, index) => [role, index]));
    return list.slice().sort((left, right) => {
      const leftRank = rank.has(left.role) ? rank.get(left.role) : Number.MAX_SAFE_INTEGER;
      const rightRank = rank.has(right.role) ? rank.get(right.role) : Number.MAX_SAFE_INTEGER;
      if (leftRank !== rightRank) return leftRank - rightRank;
      return String(left.name || left.role).localeCompare(String(right.name || right.role), "zh-Hans-CN", {
        numeric: true,
        sensitivity: "base",
      });
    });
  }

  window.WorkspaceAgentCatalog = {
    sortWorkspaceAgentsByRecommendation,
    workspaceAgentById,
    workspaceAgentDisplayName,
    workspaceAgentToolsSummary,
  };
})();
