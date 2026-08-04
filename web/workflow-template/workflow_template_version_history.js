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

  function dateFor(deps, value) {
    return typeof deps.fmtDate === "function" ? deps.fmtDate(value) : String(value || "");
  }

  function modeLabel(mode = "") {
    const value = String(mode || "").trim();
    if (value === "create") return "创建";
    if (value === "update") return "更新";
    return "记录";
  }

  function summary(record = {}) {
    const data = record.summary && typeof record.summary === "object" ? record.summary : {};
    const bits = [
      Number(data.changed_count || 0) ? `${Number(data.changed_count || 0)} 处变化` : "",
      Number(data.added_node_count || 0) ? `+${Number(data.added_node_count || 0)} 节点` : "",
      Number(data.removed_node_count || 0) ? `-${Number(data.removed_node_count || 0)} 节点` : "",
      Number(data.changed_node_count || 0) ? `${Number(data.changed_node_count || 0)} 节点改动` : "",
      Number(data.added_link_count || 0) ? `+${Number(data.added_link_count || 0)} 连接` : "",
      Number(data.removed_link_count || 0) ? `-${Number(data.removed_link_count || 0)} 连接` : "",
      data.link_topology_changed ? "拓扑变化" : data.link_order_changed ? "顺序变化" : "",
    ].filter(Boolean);
    const fields = Array.isArray(record.changed_fields) ? record.changed_fields.filter(Boolean).slice(0, 3) : [];
    if (fields.length) bits.push(`字段 ${fields.join(", ")}`);
    return bits.join(" · ") || "无结构变化";
  }

  function historyMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml, fmtDate: options.fmtDate };
    const template = options.template && typeof options.template === "object" ? options.template : {};
    const history = Array.isArray(template.version_history) ? template.version_history : [];
    if (!history.length) {
      return `
        <div class="workspace-template-version-history empty-state">
          <span class="workspace-cockpit-label">版本历史</span>
          <strong>暂无历史记录</strong>
          <p>保存模板后会记录轻量变更摘要，便于后续迁移审计。</p>
        </div>
      `;
    }
    return `
      <div class="workspace-template-version-history">
        <div class="workspace-template-version-head">
          <span class="workspace-cockpit-label">版本历史</span>
          <div>
            <strong>${history.length} 条记录</strong>
            <button class="secondary mini" type="button" data-action="copy-template-version-history" title="复制当前模板版本历史摘要 JSON，便于迁移审计和排错">复制历史</button>
          </div>
        </div>
        <div class="workspace-template-version-list">
          ${history.slice(0, 4).map((record) => `
            <article class="workspace-template-version-item" title="${escapeFor(deps, summary(record))}">
              <div>
                <strong>${escapeFor(deps, modeLabel(record.mode))}</strong>
                <span>${escapeFor(deps, dateFor(deps, record.recorded_at || record.to_updated_at || "") || record.recorded_at || "")}</span>
              </div>
              <p>${escapeFor(deps, summary(record))}</p>
            </article>
          `).join("")}
        </div>
      </div>
    `;
  }

  function auditPayload(options = {}) {
    const template = options.template && typeof options.template === "object" ? options.template : {};
    const history = Array.isArray(template.version_history) ? template.version_history : [];
    return {
      schema: "relaygraph.workflow_template.version_history.copy.v1",
      copied_at: new Date().toISOString(),
      template_id: template.id || options.selectedTemplateId || "",
      template_name: template.name || "",
      dirty: Boolean(options.dirty),
      source_type: template.source?.type || "repo",
      node_count: Array.isArray(template.nodes) ? template.nodes.length : 0,
      link_count: Array.isArray(template.links) ? template.links.length : 0,
      updated_at: template.updated_at || "",
      history_count: history.length,
      history: history.map((record) => ({
        id: record.id || "",
        mode: record.mode || "update",
        recorded_at: record.recorded_at || "",
        from_updated_at: record.from_updated_at || "",
        to_updated_at: record.to_updated_at || "",
        from_node_count: Number(record.from_node_count || 0),
        to_node_count: Number(record.to_node_count || 0),
        summary: record.summary && typeof record.summary === "object" ? { ...record.summary } : {},
        changed_fields: Array.isArray(record.changed_fields) ? record.changed_fields.slice(0, 12) : [],
        added_nodes: Array.isArray(record.added_nodes) ? record.added_nodes.slice(0, 8) : [],
        removed_nodes: Array.isArray(record.removed_nodes) ? record.removed_nodes.slice(0, 8) : [],
        changed_nodes: Array.isArray(record.changed_nodes) ? record.changed_nodes.slice(0, 8) : [],
        warnings: Array.isArray(record.warnings) ? record.warnings.slice(0, 12) : [],
      })),
    };
  }

  window.WorkflowTemplateVersionHistory = {
    auditPayload,
    historyMarkup,
    modeLabel,
    summary,
  };
})();
