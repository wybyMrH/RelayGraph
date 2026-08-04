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

  function terminalActivityKindLabel(tab) {
    if (tab.type === "terminal") return "终端";
    if (tab.type === "tmux") return "tmux";
    if (tab.type === "process") return "进程";
    return "任务";
  }

  function terminalActivitySnapshotSummary(tabs = [], terminalCount = 0, options = {}, deps = {}) {
    const kindLabel = typeof deps.terminalActivityKindLabel === "function"
      ? deps.terminalActivityKindLabel
      : terminalActivityKindLabel;
    const serverById = typeof deps.serverById === "function" ? deps.serverById : () => null;
    const terminals = options.terminals || {};
    const counts = {
      job: tabs.filter((tab) => tab.type === "job").length,
      tmux: tabs.filter((tab) => tab.type === "tmux").length,
      process: tabs.filter((tab) => tab.type === "process").length,
    };
    const active = tabs.find((tab) => tab.key === options.activeOutputKey) || tabs[0] || null;
    const activeTerminal = active?.type === "terminal" ? terminals[active.terminalId] : null;
    const activeServerInfo = active?.serverId ? serverById(active.serverId) : null;
    const activeServer = activeServerInfo?.name || activeServerInfo?.id || activeTerminal?.serverName || "-";
    const activeStatus = active
      ? active.type === "terminal"
        ? activeTerminal?.alive === false ? "已退出" : "运行中"
        : "已打开"
      : "未打开";
    const contentLength = active?.content ? String(active.content).length : 0;
    return {
      activeTitle: active ? active.title || kindLabel(active) : "没有标签",
      activeMeta: active ? `${kindLabel(active)} · ${activeServer} · ${activeStatus}` : "打开任务、tmux、进程或终端后会出现在这里",
      tabsCount: String(tabs.length),
      terminalCount: String(terminalCount),
      jobCount: String(counts.job),
      tmuxProcessCount: String(counts.tmux + counts.process),
      contentLengthText: contentLength ? `${contentLength} 字符` : "-",
    };
  }

  function terminalActivityItemOptions(tab = {}, options = {}, deps = {}) {
    const kindLabel = typeof deps.terminalActivityKindLabel === "function"
      ? deps.terminalActivityKindLabel
      : terminalActivityKindLabel;
    const terminals = options.terminals || {};
    const active = tab.key === options.activeOutputKey ? " active" : "";
    const typeLabel = kindLabel(tab);
    const terminal = tab.type === "terminal" ? terminals[tab.terminalId] : null;
    const status = tab.type === "terminal"
      ? terminal?.alive === false ? "stopped" : "running"
      : "ready";
    const detail = tab.type === "terminal"
      ? `${terminal?.serverName || tab.title || "终端"} · ${terminal?.alive === false ? "已退出" : "运行中"}`
      : tab.title || "输出";
    return {
      activeClass: active,
      detail,
      status,
      typeLabel,
    };
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
    terminalActivityItemOptions,
    terminalActivityKindLabel,
    terminalActivitySnapshotSummary,
    terminalActivitySnapshotMarkup,
  };
})();
