(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function repairApiFor(deps = {}) {
    return typeof deps.repairApi === "function" ? deps.repairApi() : deps.repairApi;
  }

  function validationFor(deps = {}) {
    return typeof deps.validation === "function" ? deps.validation() : deps.validation;
  }

  function repairActionById(deps = {}, repairId = "", nodeId = "") {
    return repairApiFor(deps)?.repairActionById?.(validationFor(deps), repairId, nodeId) || null;
  }

  function applyRepairPatch(deps = {}, action = {}) {
    const currentNodes = fn(deps, "nodes", () => [])();
    const result = repairApiFor(deps)?.applyRepairActionToNodes?.(Array.isArray(currentNodes) ? currentNodes : [], action);
    if (!result?.ok) return false;
    if (result.selectedNodeId) fn(deps, "setSelectedNodeId", () => {})(result.selectedNodeId);
    fn(deps, "updateDraft", () => {})((draft) => ({ ...draft, nodes: result.nodes }));
    return true;
  }

  async function applyRepairAction(deps = {}, repairId = "", nodeId = "") {
    const setMessage = fn(deps, "setMessage", () => {});
    const action = repairActionById(deps, repairId, nodeId);
    if (!action) {
      setMessage("修复动作已过期，请重新校验模板。", true);
      return null;
    }
    if (!applyRepairPatch(deps, action)) {
      setMessage("这个修复动作无法安全应用到当前草稿。", true);
      return null;
    }
    try {
      const response = await fn(deps, "previewTemplate", async () => null)({ render: true });
      const validationSummary = fn(deps, "validationSummary", () => "等待后端校验");
      setMessage(`已应用：${action.label || action.kind || "修复动作"}。${validationSummary(response?.validation)}`, response?.validation?.status === "blocked");
      return response;
    } catch (error) {
      setMessage(error.message || "修复已应用，但重新校验失败。", true);
      return null;
    }
  }

  async function applyAllRepairActions(deps = {}) {
    const setMessage = fn(deps, "setMessage", () => {});
    const repairActions = fn(deps, "repairActions", () => []);
    const actions = repairActions(validationFor(deps), { limit: Infinity });
    if (!actions.length) {
      setMessage("当前校验结果没有可应用的修复动作。", true);
      return null;
    }
    let applied = 0;
    let firstNodeId = "";
    actions.forEach((action) => {
      if (!firstNodeId) firstNodeId = String(action.node_id || "").trim();
      if (applyRepairPatch(deps, action)) applied += 1;
    });
    if (!applied) {
      setMessage("没有修复动作能安全应用到当前草稿。", true);
      return null;
    }
    if (firstNodeId) fn(deps, "setSelectedNodeId", () => {})(firstNodeId);
    try {
      const response = await fn(deps, "previewTemplate", async () => null)({ render: true });
      const validationSummary = fn(deps, "validationSummary", () => "等待后端校验");
      setMessage(`已应用 ${applied} 项修复。${validationSummary(response?.validation)}`, response?.validation?.status === "blocked");
      return response;
    } catch (error) {
      setMessage(error.message || "修复已应用，但重新校验失败。", true);
      return null;
    }
  }

  window.WorkflowTemplateRepairActions = {
    applyAllRepairActions,
    applyRepairAction,
    applyRepairPatch,
    repairActionById,
  };
})();
