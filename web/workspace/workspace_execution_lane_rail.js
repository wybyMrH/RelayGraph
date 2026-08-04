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

  function contractFromWorkspace(workspace = {}) {
    return workspace?.automation?.orchestration_contract && typeof workspace.automation.orchestration_contract === "object"
      ? workspace.automation.orchestration_contract
      : null;
  }

  function laneNodeMarkup(node = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    const nodeId = String(node.id || "").trim();
    const active = nodeId && nodeId === selectedNodeId ? " active" : "";
    const status = String(node.status || "draft").trim() || "draft";
    const gapCount = Number(node.input_gap_count || (Array.isArray(node.gaps) ? node.gaps.length : 0) || 0);
    return `
      <button
        class="workspace-execution-lane-node status-${escapeFor(deps, status)}${active}${gapCount ? " has-gap" : ""}"
        type="button"
        data-action="select-flow-node"
        data-node-id="${escapeFor(deps, nodeId)}"
        title="${escapeFor(deps, `${node.title || node.kind || "节点"} · ${gapCount ? `${gapCount} 个缺口` : node.output_key || "闭环"}`)}"
      >
        <span>${escapeFor(deps, String(node.index || ""))}</span>
      </button>
    `;
  }

  function laneMarkup(lane = {}, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const nodeIds = options.nodeIds instanceof Set ? options.nodeIds : new Set();
    const laneNodes = (Array.isArray(lane.nodes) ? lane.nodes : []).filter((node) => {
      const nodeId = String(node?.id || "").trim();
      return nodeId && (!nodeIds.size || nodeIds.has(nodeId));
    });
    const gaps = Array.isArray(lane.gaps) ? lane.gaps : [];
    const blockedCount = Number(lane.blocked_count || laneNodes.filter((node) => ["blocked", "failed"].includes(String(node?.status || ""))).length || 0);
    const readyCount = Number(lane.ready_count || laneNodes.filter((node) => ["ready", "done"].includes(String(node?.status || ""))).length || 0);
    const label = String(lane.label || lane.id || "阶段").trim();
    return `
      <section class="workspace-execution-lane status-${escapeFor(deps, lane.status || "draft")}" title="${escapeFor(deps, lane.summary || label)}">
        <div class="workspace-execution-lane-head">
          <span>${escapeFor(deps, label)}</span>
          <strong>${escapeFor(deps, `${readyCount}/${laneNodes.length || Number(lane.node_count || 0)} 闭环`)}</strong>
          <em>${escapeFor(deps, blockedCount ? `${blockedCount} 阻塞` : gaps.length ? `${gaps.length} 缺口` : "可推进")}</em>
        </div>
        <div class="workspace-execution-lane-nodes">
          ${laneNodes.slice(0, 8).map((node) => laneNodeMarkup(node, options)).join("") || '<span class="workspace-execution-lane-empty">等待节点</span>'}
        </div>
      </section>
    `;
  }

  function markup(options = {}) {
    if (options.preview) return "";
    const workspace = options.workspace && typeof options.workspace === "object" ? options.workspace : null;
    if (!workspace?.id) return "";
    const contract = options.contract && typeof options.contract === "object"
      ? options.contract
      : contractFromWorkspace(workspace);
    const lanes = Array.isArray(contract?.lanes) ? contract.lanes.filter((lane) => lane && typeof lane === "object") : [];
    if (!lanes.length) return "";
    const deps = { escapeHtml: options.escapeHtml };
    const nodeIds = new Set((Array.isArray(options.nodes) ? options.nodes : [])
      .map((node) => String(node?.id || "").trim())
      .filter(Boolean));
    return `
      <div class="workspace-execution-lane-rail status-${escapeFor(deps, contract.status || "draft")}" aria-label="编排阶段泳道">
        <div class="workspace-execution-lane-rail-head">
          <span>阶段泳道</span>
          <strong>${escapeFor(deps, contract.summary || `${lanes.length} 个阶段`)}</strong>
        </div>
        <div class="workspace-execution-lane-strip">
          ${lanes.map((lane) => laneMarkup(lane, { ...options, nodeIds })).join("")}
        </div>
      </div>
    `;
  }

  window.WorkspaceExecutionLaneRail = {
    markup,
  };
})();
