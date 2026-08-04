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

  function summaryMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      agentById: options.agentById,
      nodeLabel: options.nodeLabel,
      providerProfileById: options.providerProfileById,
      providerProfileLabel: options.providerProfileLabel,
    };
    const template = options.template && typeof options.template === "object" ? options.template : null;
    if (!template) return '<div class="empty">还没有模板。先在管理模式创建一条默认流。</div>';
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const agentById = fn(deps, "agentById", () => null);
    const providerProfileById = fn(deps, "providerProfileById", () => null);
    const providerProfileLabel = fn(deps, "providerProfileLabel", (profile) => profile?.name || profile?.id || "");
    const nodes = Array.isArray(template.nodes) ? template.nodes : [];
    const chain = nodes
      .map((node) => {
        const handler = node.handler || {};
        const owner = handler.name || agentById(handler.agent_id)?.name || "";
        return owner ? `${node.title || nodeLabel(node.kind)} · ${owner}` : node.title || nodeLabel(node.kind);
      })
      .slice(0, 6);
    const model = template.model || {};
    const profile = providerProfileById(model.provider_profile_id);
    return `
    <div class="workspace-template-summary-card">
      <div class="workspace-template-summary-line">
        <strong>${escapeFor(deps, template.name || template.id)}</strong>
        <span class="server-badge subtle">${escapeFor(deps, template.source?.type || "repo")}</span>
      </div>
      <div class="workspace-template-summary-text">${escapeFor(deps, template.description || template.brief || "这条模板会被复制成实例快照，再进入执行链。")}</div>
      <div class="workspace-template-summary-meta">
        <span>${nodes.length} 个节点</span>
        <span>${template.agent_count || template.agent_ids?.length || 0} 个 Agent</span>
        <span>${template.tool_count || template.tool_ids?.length || 0} 个工具</span>
        <span>${escapeFor(deps, profile ? providerProfileLabel(profile) : model.routing_mode || "workspace_default")}</span>
      </div>
      <div class="workspace-template-summary-chain">
        ${chain.map((item) => `<span class="workspace-template-chip">${escapeFor(deps, item)}</span>`).join("") || '<span class="workspace-template-chip">空模板</span>'}
      </div>
    </div>
  `;
  }

  function templateListMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml, statusLabel: options.statusLabel };
    const templates = Array.isArray(options.templates) ? options.templates : [];
    const selectedTemplateId = String(options.selectedTemplateId || "").trim();
    const statusLabel = fn(deps, "statusLabel", (status) => status);
    if (!templates.length) return '<div class="empty">还没有工作流模板。</div>';
    return templates.map((template) => {
      const active = template.id === selectedTemplateId ? " active" : "";
      const nodeCount = Array.isArray(template.nodes) ? template.nodes.length : template.node_count || 0;
      const versionCount = Array.isArray(template.version_history) ? template.version_history.length : 0;
      const status = template.status || "ready";
      return `
      <button class="workspace-template-item${active}" type="button" data-action="select-workflow-template" data-template-id="${escapeFor(deps, template.id)}" title="选择这个 Starter Chain 模板并编辑默认节点链">
        <div class="workspace-template-item-head">
          <strong>${escapeFor(deps, template.name || template.id)}</strong>
          <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, statusLabel(status))}</span>
        </div>
        <div class="workspace-template-item-meta">${escapeFor(deps, template.source?.type || "repo")} · ${nodeCount} 个节点${versionCount ? ` · ${versionCount} 条版本` : ""}</div>
        <div class="workspace-template-item-desc">${escapeFor(deps, template.description || template.brief || "未填写模板描述")}</div>
      </button>
    `;
    }).join("");
  }

  function nodeKindOptionsMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const nodeTypes = options.nodeTypes && typeof options.nodeTypes === "object" ? options.nodeTypes : {};
    return Object.entries(nodeTypes)
      .map(([kind, meta]) => `<option value="${escapeFor(deps, kind)}">${escapeFor(deps, meta.label || kind)}</option>`)
      .join("");
  }

  function nodeListMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      agentById: options.agentById,
      nodeLabel: options.nodeLabel,
      nodeSummary: options.nodeSummary,
      statusLabel: options.statusLabel,
    };
    const nodes = Array.isArray(options.nodes) ? options.nodes : [];
    const selectedNodeId = String(options.selectedNodeId || "").trim();
    if (!nodes.length) return '<div class="empty">模板里还没有节点。</div>';
    const agentById = fn(deps, "agentById", () => null);
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const nodeSummary = fn(deps, "nodeSummary", () => "");
    const statusLabel = fn(deps, "statusLabel", (status) => status);
    return nodes.map((node, index) => {
      const active = node.id === selectedNodeId ? " active" : "";
      const handler = node.handler || {};
      const agent = agentById(handler.agent_id || "");
      const status = node.status || "ready";
      return `
      <div class="workspace-node-stack">
        <button class="workspace-node-card${active}" type="button" data-action="select-template-node" data-node-id="${escapeFor(deps, node.id)}" title="选择这个模板节点，编辑默认配置和绑定 Agent">
          <div class="workspace-node-head">
            <span class="workspace-node-title">${escapeFor(deps, node.title || nodeLabel(node.kind))}</span>
            <span class="server-badge subtle">${index + 1}</span>
          </div>
          <div class="workspace-node-meta">
            <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, statusLabel(status))}</span>
            <span>${escapeFor(deps, nodeLabel(node.kind))}</span>
            <span>${escapeFor(deps, handler.name || agent?.name || "未指派")}</span>
          </div>
          <div class="workspace-node-summary">${escapeFor(deps, nodeSummary(node))}</div>
        </button>
        ${index < nodes.length - 1 ? '<div class="workspace-node-link-row"><span class="workspace-node-link-arrow">↓</span><div><div class="workspace-node-link-title">顺序交接</div></div></div>' : ""}
      </div>
    `;
    }).join("");
  }

  window.WorkflowTemplateCatalog = {
    nodeKindOptionsMarkup,
    nodeListMarkup,
    summaryMarkup,
    templateListMarkup,
  };
})();
