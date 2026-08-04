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

  function label(status = "") {
    const value = String(status || "").trim();
    if (value === "ready") return "通过";
    if (value === "warning") return "有警告";
    if (value === "blocked") return "阻塞";
    return "未校验";
  }

  function summary(validation = null) {
    if (!validation || typeof validation !== "object") return "等待后端校验";
    return validation.summary
      || `${Number(validation.node_count || 0)} 个节点 · ${Number(validation.blocking_count || 0)} 个阻塞 · ${Number(validation.warning_count || 0)} 个警告`;
  }

  function issueMarkup(validation = null, options = {}) {
    const deps = { escapeHtml: options.escapeHtml, statusLabel: options.statusLabel };
    const statusLabel = fn(deps, "statusLabel", (status) => status);
    const limit = Number.isFinite(options.limit) ? Math.max(0, Number(options.limit)) : 4;
    const issues = Array.isArray(validation?.issues) ? validation.issues : [];
    if (!issues.length) return '<div class="workspace-template-validation-empty">没有发现阻塞项。</div>';
    return `
    <div class="workspace-template-validation-issues">
      ${issues.slice(0, limit).map((issue) => `
        <div class="workspace-template-validation-issue severity-${escapeFor(deps, issue.severity || "warning")}">
          <span>${escapeFor(deps, statusLabel(issue.severity === "blocking" ? "blocked" : "warning"))}</span>
          <strong>${escapeFor(deps, issue.message || issue.code || "配置检查项")}</strong>
        </div>
      `).join("")}
      ${issues.length > limit ? `<div class="workspace-template-validation-more">还有 ${issues.length - limit} 个检查项，可切到链路诊断查看上下文。</div>` : ""}
    </div>
  `;
  }

  function repairMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const actions = Array.isArray(options.actions) ? options.actions : [];
    const allCount = Number(options.allCount || actions.length || 0);
    if (!actions.length) return "";
    return `
    <div class="workspace-template-validation-repairs">
      <div>
        <span>建议修复</span>
        <em>${allCount > actions.length ? `显示 ${actions.length}/${allCount}` : `${actions.length} 项`}</em>
      </div>
      <div class="workspace-template-validation-repair-actions">
        ${allCount > 1 ? '<button class="secondary mini" type="button" data-action="apply-template-repair-all" title="按当前后端预览给出的顺序应用全部可安全修复项">全部应用</button>' : ""}
        ${actions.map((action) => {
          const value = action.patch?.value == null ? "" : String(action.patch.value);
          const title = [action.node_title, action.label || action.kind || "应用修复", value].filter(Boolean).join(" · ");
          return `
            <button
              class="secondary mini"
              type="button"
              data-action="apply-template-repair"
              data-repair-id="${escapeFor(deps, action.id)}"
              data-node-id="${escapeFor(deps, action.node_id)}"
              title="${escapeFor(deps, title)}"
            >${escapeFor(deps, action.label || "应用修复")}</button>
          `;
        }).join("")}
      </div>
    </div>
  `;
  }

  function markup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml, statusLabel: options.statusLabel };
    const validation = options.validation && typeof options.validation === "object" ? options.validation : null;
    const status = String(validation?.status || "").trim() || "draft";
    const blocking = Number(validation?.blocking_count || 0);
    const warnings = Number(validation?.warning_count || 0);
    const currentSummary = summary(validation);
    return `
    <article class="workspace-template-studio-card workspace-template-validation-card status-${escapeFor(deps, status)}">
      <span class="workspace-cockpit-label">后端校验</span>
      <strong>${options.busy ? "校验中..." : label(status)}</strong>
      <p title="${escapeFor(deps, currentSummary)}">${escapeFor(deps, currentSummary)}</p>
      <em>${blocking ? `${blocking} 个阻塞会阻止保存` : warnings ? `${warnings} 个警告，可保存但建议处理` : "保存前会自动校验"}</em>
      ${issueMarkup(validation, { ...deps, limit: options.issueLimit })}
      ${repairMarkup({ ...deps, actions: options.actions, allCount: options.allCount })}
    </article>
  `;
  }

  window.WorkflowTemplateValidation = {
    issueMarkup,
    label,
    markup,
    repairMarkup,
    summary,
  };
})();
