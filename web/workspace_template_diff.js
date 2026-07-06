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

  function diffStatusLabel(status = "") {
    const value = String(status || "").trim();
    if (value === "same") return "快照一致";
    if (value === "changed") return "模板已变化";
    if (value === "missing_template") return "模板已删除";
    if (value === "missing_snapshot") return "缺少快照";
    return "等待检查";
  }

  function diffStatusClass(status = "") {
    const value = String(status || "").trim();
    if (value === "same") return "ready";
    if (value === "changed") return "warning";
    if (value === "missing_template" || value === "missing_snapshot") return "blocked";
    return "draft";
  }

  function migrationStatusLabel(status = "") {
    const value = String(status || "").trim();
    if (value === "ready") return "无需迁移";
    if (value === "review") return "可复核同步";
    if (value === "manual_review") return "需人工复核";
    if (value === "blocked") return "迁移阻塞";
    return "等待计划";
  }

  function migrationStrategyLabel(strategy = "") {
    const value = String(strategy || "").trim();
    if (value === "no_action") return "保持当前实例";
    if (value === "sync_safe_fields") return "同步安全字段";
    if (value === "sync_draft_then_validate") return "草稿同步后校验";
    if (value === "create_new_workspace") return "建议新建实例";
    if (value === "manual_rebuild") return "手动重建";
    return "逐项检查";
  }

  function migrationStatusClass(status = "") {
    const value = String(status || "").trim();
    if (value === "ready") return "ready";
    if (value === "blocked") return "blocked";
    if (value === "manual_review" || value === "review") return "warning";
    return "draft";
  }

  function structureStatusLabel(status = "") {
    const value = String(status || "").trim();
    if (value === "added") return "新增";
    if (value === "removed") return "移除";
    if (value === "changed") return "变更";
    if (value === "same") return "一致";
    return "未知";
  }

  function structureNodeMarkup(node = {}, deps = {}) {
    const status = String(node.status || "same").trim() || "same";
    const meta = [
      node.kind || "",
      node.handler_agent_id ? `Agent ${node.handler_agent_id}` : node.handler_tool_id ? `Tool ${node.handler_tool_id}` : node.handler_mode || "",
      node.output_key ? `out:${node.output_key}` : "",
      node.handler_output_key && node.handler_output_key !== node.output_key ? `handler_out:${node.handler_output_key}` : "",
      node.has_input_mapping ? "mapped" : "",
    ].filter(Boolean).join(" · ");
    return `
      <span class="workspace-template-structure-node status-${escapeFor(deps, status)}" title="${escapeFor(deps, `${node.title || node.kind || node.id || "节点"} · ${meta || structureStatusLabel(status)}`)}">
        <strong>${escapeFor(deps, node.title || node.kind || node.id || "节点")}</strong>
        <em>${escapeFor(deps, structureStatusLabel(status))}</em>
      </span>
    `;
  }

  function structurePreviewMarkup(preview = null, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    if (!preview || typeof preview !== "object") return "";
    const previous = Array.isArray(preview.previous_nodes) ? preview.previous_nodes : [];
    const current = Array.isArray(preview.current_nodes) ? preview.current_nodes : [];
    if (!previous.length && !current.length) return "";
    const visibleLimit = 18;
    const previewTruncated =
      Boolean(preview.truncated) ||
      Number(preview.previous_count || previous.length) > visibleLimit ||
      Number(preview.current_count || current.length) > visibleLimit;
    const row = (label, nodes, count) => `
      <div class="workspace-template-structure-row">
        <span>${escapeFor(deps, label)} · ${Number(count || nodes.length)} 节点</span>
        <div class="workspace-template-structure-track">
          ${nodes.slice(0, visibleLimit).map((node) => structureNodeMarkup(node, deps)).join("")}
          ${Number(count || nodes.length) > visibleLimit ? '<span class="workspace-template-structure-more">...</span>' : ""}
        </div>
      </div>
    `;
    return `
      <div class="workspace-template-structure-preview">
        ${row("实例快照", previous, preview.previous_count)}
        ${row("当前模板", current, preview.current_count)}
        ${previewTruncated ? '<p class="workspace-chain-inspect-summary-note">链路较长，仅显示前 18 个节点；复制迁移计划可查看完整摘要。</p>' : ""}
      </div>
    `;
  }

  function linkStatusLabel(status = "") {
    const value = String(status || "").trim();
    if (value === "added") return "新增";
    if (value === "removed") return "移除";
    if (value === "same") return "一致";
    return "未知";
  }

  function linkItemMarkup(link = {}, deps = {}) {
    const status = String(link.status || "same").trim() || "same";
    const label = link.label || `${link.from_label || link.from || "上游"} -> ${link.to_label || link.to || "下游"}`;
    return `
      <span class="workspace-template-link-edge status-${escapeFor(deps, status)}" title="${escapeFor(deps, `${label} · ${linkStatusLabel(status)}`)}">
        <strong>${escapeFor(deps, link.from_label || link.from || "上游")}</strong>
        <em>-></em>
        <strong>${escapeFor(deps, link.to_label || link.to || "下游")}</strong>
        <small>${escapeFor(deps, linkStatusLabel(status))}</small>
      </span>
    `;
  }

  function linkPreviewMarkup(preview = null, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    if (!preview || typeof preview !== "object") return "";
    const previous = Array.isArray(preview.previous_links) ? preview.previous_links : [];
    const current = Array.isArray(preview.current_links) ? preview.current_links : [];
    if (!previous.length && !current.length) return "";
    const visibleLimit = 16;
    const previewTruncated =
      Boolean(preview.truncated) ||
      Number(preview.previous_count || previous.length) > visibleLimit ||
      Number(preview.current_count || current.length) > visibleLimit;
    const badges = [
      preview.topology_changed ? "拓扑变化" : "",
      preview.order_changed ? "顺序变化" : "",
      preview.metadata_changed ? "连接元数据变化" : "",
    ].filter(Boolean);
    const row = (label, links, count) => `
      <div class="workspace-template-link-row">
        <span>${escapeFor(deps, label)} · ${Number(count || links.length)} 连接</span>
        <div class="workspace-template-link-track">
          ${links.slice(0, visibleLimit).map((link) => linkItemMarkup(link, deps)).join("")}
          ${Number(count || links.length) > visibleLimit ? '<span class="workspace-template-link-more">...</span>' : ""}
        </div>
      </div>
    `;
    return `
      <div class="workspace-template-link-preview">
        <div class="workspace-template-link-head">
          <span class="workspace-cockpit-label">连接拓扑</span>
          <div>${badges.length ? badges.map((item) => `<strong>${escapeFor(deps, item)}</strong>`).join("") : "<strong>连接一致</strong>"}</div>
        </div>
        ${row("旧连接", previous, preview.previous_count)}
        ${row("当前连接", current, preview.current_count)}
        ${previewTruncated ? '<p class="workspace-chain-inspect-summary-note">连接较多，仅显示前 16 条；复制迁移计划可查看完整摘要。</p>' : ""}
      </div>
    `;
  }

  function migrationPlanMarkup(plan = null, options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    if (!plan || typeof plan !== "object") return "";
    const status = String(plan.status || "draft");
    const strategy = String(plan.strategy || "");
    const statusClass = migrationStatusClass(status);
    const steps = Array.isArray(plan.steps) ? plan.steps : [];
    const canApply = Boolean(plan.can_manual_apply);
    const canCreateDraft = Boolean(plan.can_create_draft) && !canApply;
    return `
      <div class="workspace-template-diff-plan status-${escapeFor(deps, statusClass)}">
        <div>
          <span class="workspace-cockpit-label">迁移计划</span>
          <strong>${escapeFor(deps, migrationStatusLabel(status))} · ${escapeFor(deps, migrationStrategyLabel(strategy))}</strong>
          <em title="${escapeFor(deps, plan.recommended_action || "")}">${escapeFor(deps, plan.recommended_action || "复制计划后按步骤复核。")}</em>
        </div>
        <div class="workspace-template-diff-plan-actions">
          <button class="secondary mini" type="button" data-action="copy-template-migration-plan" title="复制模板差异迁移计划 JSON，供迁移前审计和复核">复制计划</button>
          <button class="secondary mini" type="button" data-action="apply-template-migration" title="${escapeFor(deps, canApply ? "手动应用当前模板的安全字段，并记录迁移历史" : "此差异包含结构性变化，建议新建实例或人工重建")}" ${canApply ? "" : "disabled"}>应用安全迁移</button>
          ${canCreateDraft ? `<button class="secondary mini" type="button" data-action="create-template-migration-draft" title="从当前实例输入和当前模板创建一个新草稿，旧实例和运行历史保持不变">新建迁移草稿</button>` : ""}
        </div>
      </div>
      ${steps.length ? `
        <div class="workspace-template-diff-steps">
          ${steps.slice(0, 4).map((step) => `
            <span title="${escapeFor(deps, step.detail || step.label || "")}">${escapeFor(deps, step.label || step.id || "复核步骤")}</span>
          `).join("")}
        </div>
      ` : ""}
    `;
  }

  function diffMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const workspace = options.workspace && typeof options.workspace === "object" ? options.workspace : null;
    if (!workspace?.id) {
      return '<div class="empty">选择一个实例后显示它与当前模板的快照差异。</div>';
    }
    const cached = options.cached && typeof options.cached === "object" ? options.cached : {};
    if (cached.busy && cached.workspaceId === workspace.id) {
      return '<div class="empty">正在检查模板快照差异...</div>';
    }
    if (cached.error && cached.workspaceId === workspace.id) {
      return `<div class="empty error">模板差异检查失败：${escapeFor(deps, cached.error)}</div>`;
    }
    const payload = cached.workspaceId === workspace.id && cached.payload ? cached.payload : null;
    const diff = payload?.diff && typeof payload.diff === "object" ? payload.diff : null;
    if (!diff) {
      return '<div class="empty">尚未加载模板快照差异。</div>';
    }
    const status = String(diff.status || "draft");
    const summary = diff.summary && typeof diff.summary === "object" ? diff.summary : {};
    const details = diff.diff && typeof diff.diff === "object" ? diff.diff : {};
    const migrationPlan = diff.migration_plan && typeof diff.migration_plan === "object" ? diff.migration_plan : null;
    const structurePreview = diff.structure_preview && typeof diff.structure_preview === "object" ? diff.structure_preview : null;
    const linkPreview = diff.link_preview && typeof diff.link_preview === "object" ? diff.link_preview : null;
    const changedNodes = Array.isArray(details.changed_nodes) ? details.changed_nodes : [];
    const addedNodes = Array.isArray(details.added_nodes) ? details.added_nodes : [];
    const removedNodes = Array.isArray(details.removed_nodes) ? details.removed_nodes : [];
    const changedFields = Array.isArray(details.changed_fields) ? details.changed_fields : [];
    const changedItems = [
      ...addedNodes.slice(0, 3).map((item) => `新增 ${item.title || item.kind || item.id}`),
      ...removedNodes.slice(0, 3).map((item) => `移除 ${item.title || item.kind || item.id}`),
      ...changedNodes.slice(0, 3).map((item) => `变更 ${item.title || item.kind || item.id}`),
      ...changedFields.slice(0, 4).map((item) => `字段 ${item}`),
    ];
    const statusClass = diffStatusClass(status);
    return `
      <div class="workspace-template-diff-summary status-${escapeFor(deps, statusClass)}">
        <div>
          <span class="workspace-cockpit-label">模板快照</span>
          <strong>${escapeFor(deps, diffStatusLabel(status))}</strong>
          <em>${escapeFor(deps, payload.template_name || diff.workspace_snapshot?.template_name || workspace.template_name || "自定义实例")}</em>
        </div>
        <div class="workspace-template-diff-metrics">
          <span>${Number(summary.changed_count || 0)} 处变化</span>
          <span>${Number(summary.added_node_count || 0)} 新增</span>
          <span>${Number(summary.removed_node_count || 0)} 移除</span>
          <span>${Number(summary.changed_node_count || 0)} 节点变更</span>
        </div>
      </div>
      ${changedItems.length ? `
        <div class="workspace-template-diff-list">
          ${changedItems.map((item) => `<span>${escapeFor(deps, item)}</span>`).join("")}
        </div>
      ` : '<p class="workspace-chain-inspect-summary-note">当前实例仍保持创建时的独立快照；模板变化不会自动改写它。</p>'}
      ${structurePreviewMarkup(structurePreview, deps)}
      ${linkPreviewMarkup(linkPreview, deps)}
      ${migrationPlanMarkup(migrationPlan, deps)}
    `;
  }

  window.WorkspaceTemplateDiff = {
    diffMarkup,
    diffStatusClass,
    diffStatusLabel,
    linkPreviewMarkup,
    migrationPlanMarkup,
    migrationStatusClass,
    migrationStatusLabel,
    migrationStrategyLabel,
    structurePreviewMarkup,
  };
})();
