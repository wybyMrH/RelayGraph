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

  window.WorkspaceAgentCatalog = {
    workspaceAgentById,
    workspaceAgentDisplayName,
    workspaceAgentToolsSummary,
  };
})();
