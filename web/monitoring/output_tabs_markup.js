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

  function outputTabsPlaceholderMarkup() {
    return '<span class="output-tab-placeholder">选择任务、tmux、进程或打开终端。</span>';
  }

  function outputTabItemMarkup(tab = {}, options = {}, deps = {}) {
    const active = options.activeClass || "";
    const title = tab.title || "输出";
    return `
        <div class="output-tab${active}">
          <button class="output-tab-trigger" type="button" title="${escapeFor(deps, title)}" onclick="activateOutputTab('${escapeFor(deps, tab.key)}')">
            <span class="output-tab-label">${escapeFor(deps, title)}</span>
          </button>
          <button class="output-tab-close" type="button" title="关闭" onclick="closeOutputTab(event, '${escapeFor(deps, tab.key)}')">×</button>
        </div>
      `;
  }

  window.OutputTabsMarkup = {
    outputTabItemMarkup,
    outputTabsPlaceholderMarkup,
  };
})();
