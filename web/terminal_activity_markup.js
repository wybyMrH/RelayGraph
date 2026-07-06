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

  function terminalActivitySnapshotMarkup(summary = {}, deps = {}) {
    return `
    <div class="terminal-activity-snapshot-head">
      <span class="workspace-home-card-label">当前输出</span>
      <strong>${escapeFor(deps, summary.activeTitle)}</strong>
      <em>${escapeFor(deps, summary.activeMeta)}</em>
    </div>
    <div class="terminal-activity-stat-grid">
      <article>
        <span>标签</span>
        <strong>${escapeFor(deps, summary.tabsCount)}</strong>
      </article>
      <article>
        <span>终端</span>
        <strong>${escapeFor(deps, summary.terminalCount)}</strong>
      </article>
      <article>
        <span>任务输出</span>
        <strong>${escapeFor(deps, summary.jobCount)}</strong>
      </article>
      <article>
        <span>tmux / 进程</span>
        <strong>${escapeFor(deps, summary.tmuxProcessCount)}</strong>
      </article>
    </div>
    <div class="terminal-activity-detail">
      <span>输出长度</span>
      <strong>${escapeFor(deps, summary.contentLengthText)}</strong>
    </div>
  `;
  }

  function terminalActivityEmptyMarkup() {
    return '<div class="empty compact-empty">还没有打开输出标签。</div>';
  }

  function terminalActivityItemMarkup(tab = {}, options = {}, deps = {}) {
    const active = options.activeClass || "";
    const typeLabel = options.typeLabel || "";
    const status = options.status || "";
    const detail = options.detail || "";
    const title = tab.title || typeLabel;
    return `
        <article class="terminal-session-item${active}">
          <button type="button" data-action="activate-output-tab" data-output-key="${escapeFor(deps, tab.key)}" title="${escapeFor(deps, `打开标签：${title}`)}">
            <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, typeLabel)}</span>
            <strong>${escapeFor(deps, title)}</strong>
            <em>${escapeFor(deps, detail)}</em>
          </button>
          <button class="secondary mini danger" type="button" data-action="close-output-tab" data-output-key="${escapeFor(deps, tab.key)}" title="${escapeFor(deps, `关闭标签：${title}`)}">关闭</button>
        </article>
      `;
  }

  window.TerminalActivityMarkup = {
    terminalActivityEmptyMarkup,
    terminalActivityItemMarkup,
    terminalActivitySnapshotMarkup,
  };
})();
