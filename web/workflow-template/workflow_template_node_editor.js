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

  function agentOptions(agentDefinitions = []) {
    return [
      { value: "", label: "选择全局 Agent" },
      ...(Array.isArray(agentDefinitions) ? agentDefinitions : []).map((agent) => ({
        value: String(agent.id || ""),
        label: `${agent.name || agent.id} · ${agent.role || agent.id}`,
      })),
    ];
  }

  function editorMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      nodeLabel: options.nodeLabel,
      nodeMeta: options.nodeMeta,
      renderNodeField: options.renderNodeField,
      statusLabel: options.statusLabel,
      inputMappingEditorMarkup: options.inputMappingEditorMarkup,
    };
    const node = options.node && typeof options.node === "object" ? options.node : {};
    const nodeLabel = fn(deps, "nodeLabel", (kind) => kind);
    const nodeMeta = fn(deps, "nodeMeta", () => ({}));
    const renderNodeField = fn(deps, "renderNodeField", () => "");
    const statusLabel = fn(deps, "statusLabel", (status) => status);
    const inputMappingEditorMarkup = fn(deps, "inputMappingEditorMarkup", () => "");
    const meta = nodeMeta(node.kind) || {};
    const nodeIndex = Math.max(0, Number(options.nodeIndex || 0));
    const configFields = (Array.isArray(meta.configFields) ? meta.configFields : [])
      .map((field) => renderNodeField(field, node.config?.[field.key], node.kind))
      .join("");
    const statusOptions = ["ready", "draft", "blocked", "running", "done"]
      .map((status) => `<option value="${escapeFor(deps, status)}" ${status === node.status ? "selected" : ""}>${escapeFor(deps, statusLabel(status))}</option>`)
      .join("");
    const agents = agentOptions(options.agentDefinitions);
    const selectedAgentId = String(node.handler?.agent_id || "");
    return `
    <div class="workspace-node-editor-card">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeFor(deps, node.title || nodeLabel(node.kind))}</h4>
          <p class="muted">${escapeFor(deps, meta.description || "编辑模板节点")}</p>
        </div>
        <span class="server-badge">${escapeFor(deps, nodeLabel(node.kind))}</span>
      </div>
      <div class="workspace-node-editor-grid">
        <label>
          节点标题
          <input data-manage-node-field="title" value="${escapeFor(deps, node.title || "")}" placeholder="${escapeFor(deps, nodeLabel(node.kind))}" />
        </label>
        <label>
          节点状态
          <select data-manage-node-field="status">
            ${statusOptions}
          </select>
        </label>
        <label>
          执行者类型
          <select data-manage-handler-field="mode">
            <option value="human" ${node.handler?.mode === "human" ? "selected" : ""}>人工</option>
            <option value="agent" ${node.handler?.mode === "agent" ? "selected" : ""}>Agent</option>
            <option value="system" ${node.handler?.mode === "system" ? "selected" : ""}>系统</option>
          </select>
        </label>
        <label>
          归属 Agent
          <select data-manage-handler-field="agent_id">
            ${agents.map((option) => `<option value="${escapeFor(deps, option.value)}" ${option.value === selectedAgentId ? "selected" : ""}>${escapeFor(deps, option.label)}</option>`).join("")}
          </select>
        </label>
      </div>
      <label>
        显示名 / 责任人
        <input data-manage-handler-field="name" value="${escapeFor(deps, node.handler?.name || "")}" placeholder="例如 Repo Scout" />
      </label>
      <label>
        交接说明
        <textarea data-manage-handler-field="handoff" rows="3" placeholder="这个节点结束后，下一步应该拿着什么继续执行">${escapeFor(deps, node.handler?.handoff || "")}</textarea>
      </label>
      <div class="workspace-node-editor-grid">
        ${configFields || '<div class="empty">这个节点当前没有额外配置字段。</div>'}
      </div>
      <div class="workspace-node-io-edit-grid">
        <label>
          output_key
          <input data-manage-node-field="output_key" value="${escapeFor(deps, node.output_key || "")}" placeholder="${escapeFor(deps, options.outputPlaceholder || "step_output")}" />
        </label>
        ${inputMappingEditorMarkup(node, nodeIndex)}
      </div>
      <label>
        节点备注
        <textarea data-manage-node-field="notes" rows="3" placeholder="可以写人工检查点、边界或特别说明">${escapeFor(deps, node.notes || "")}</textarea>
      </label>
    </div>
  `;
  }

  window.WorkflowTemplateNodeEditor = {
    agentOptions,
    editorMarkup,
  };
})();
