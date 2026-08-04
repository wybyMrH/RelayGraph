(function () {
  "use strict";

  function cloneValue(value) {
    if (Array.isArray(value)) return value.map((item) => cloneValue(item));
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]));
    }
    return value;
  }

  function repairActions(response = {}, options = {}) {
    const limit = Number.isFinite(options.limit) ? Math.max(0, Number(options.limit)) : Infinity;
    const preview = response?.preview && typeof response.preview === "object" ? response.preview : {};
    const nodes = Array.isArray(preview.nodes) ? preview.nodes : [];
    const actions = [];
    nodes.forEach((node) => {
      const nodeActions = Array.isArray(node.repair_actions) ? node.repair_actions : [];
      nodeActions.forEach((action) => {
        if (!action || typeof action !== "object") return;
        const id = String(action.id || "").trim();
        if (!id) return;
        actions.push({
          ...action,
          node_id: String(action.node_id || node.id || "").trim(),
          node_title: String(node.title || node.kind || node.id || "").trim(),
          node_index: Number(node.index || 0),
        });
      });
    });
    return limit === Infinity ? actions : actions.slice(0, limit);
  }

  function repairActionById(response = {}, repairId = "", nodeId = "") {
    const id = String(repairId || "").trim();
    const targetNodeId = String(nodeId || "").trim();
    if (!id) return null;
    return repairActions(response, { limit: Infinity })
      .find((action) => action.id === id && (!targetNodeId || action.node_id === targetNodeId)) || null;
  }

  function repairPatches(action = {}) {
    if (Array.isArray(action.patches) && action.patches.length) return action.patches;
    return action.patch && typeof action.patch === "object" ? [action.patch] : [];
  }

  function applyRepairPatchToNodes(nextNodes = [], action = {}, patch = {}) {
    const path = Array.isArray(patch.path) ? patch.path : [];
    if (path[0] !== "nodes") return { applied: false, selectedNodeId: "" };
    let index = Number(path[1]);
    const nodeId = String(action.node_id || "").trim();
    const idIndex = nodeId ? nextNodes.findIndex((node) => String(node.id || "") === nodeId) : -1;
    if (idIndex >= 0) index = idIndex;
    if (!Number.isInteger(index) || index < 0 || index >= nextNodes.length) {
      return { applied: false, selectedNodeId: "" };
    }
    const value = patch.value == null ? "" : String(patch.value);
    const field = String(path[2] || "").trim();
    const target = nextNodes[index];
    if (!target || typeof target !== "object") return { applied: false, selectedNodeId: "" };
    if (field === "input_mapping" && path.length === 4) {
      const inputName = String(path[3] || "").trim();
      if (!inputName) return { applied: false, selectedNodeId: "" };
      target.input_mapping = {
        ...(target.input_mapping && typeof target.input_mapping === "object" ? target.input_mapping : {}),
        [inputName]: value,
      };
    } else if (field === "output_key" && path.length === 3) {
      if (!value.trim()) return { applied: false, selectedNodeId: "" };
      target.output_key = value.trim();
      if (target.handler && typeof target.handler === "object" && String(target.handler.output_key || "").trim()) {
        target.handler = { ...target.handler, output_key: value.trim() };
      }
    } else if (field === "handler" && path.length === 4 && String(path[3] || "") === "output_key") {
      if (!value.trim()) return { applied: false, selectedNodeId: "" };
      target.handler = {
        ...(target.handler && typeof target.handler === "object" ? target.handler : {}),
        output_key: value.trim(),
      };
    } else {
      return { applied: false, selectedNodeId: "" };
    }
    return { applied: true, selectedNodeId: String(target.id || "").trim() };
  }

  function applyRepairActionToNodes(nodes = [], action = {}) {
    const nextNodes = (Array.isArray(nodes) ? nodes : []).map((node) => cloneValue(node));
    let applied = 0;
    let selectedNodeId = "";
    repairPatches(action).forEach((patch) => {
      const result = applyRepairPatchToNodes(nextNodes, action, patch);
      if (!result.applied) return;
      applied += 1;
      if (result.selectedNodeId) selectedNodeId = result.selectedNodeId;
    });
    return {
      applied,
      nodes: nextNodes,
      ok: applied > 0,
      selectedNodeId,
    };
  }

  window.WorkflowTemplateRepair = {
    applyRepairActionToNodes,
    applyRepairPatchToNodes,
    repairActionById,
    repairActions,
    repairPatches,
  };
})();
