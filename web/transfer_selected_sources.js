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

  function transferPaneEmptyMarkup(title, hint = "", options = {}, deps = {}) {
    const compactClass = options.compact ? " transfer-pane-empty-compact" : "";
    const icon = options.icon || "·";
    const hintHtml = hint ? `<p>${escapeFor(deps, hint)}</p>` : "";
    return `<div class="empty transfer-pane-empty${compactClass}"><span class="transfer-pane-empty-icon" aria-hidden="true">${escapeFor(deps, icon)}</span><strong>${escapeFor(deps, title)}</strong>${hintHtml}</div>`;
  }

  function transferPaneLoadingMarkup(text, deps = {}) {
    return `<div class="empty transfer-pane-empty transfer-pane-loading"><span>${escapeFor(deps, text)}</span></div>`;
  }

  function selectedSourceCountText(sources = []) {
    return `${Array.isArray(sources) ? sources.length : 0} 项`;
  }

  function selectedSourceRowMarkup(item = {}, deps = {}) {
    return `
      <div class="selected-source-item" title="${escapeFor(deps, item.value)}">
        <span>
          <strong>${item.isDir ? "目录" : "文件"}</strong>
          ${escapeFor(deps, item.serverName || item.serverId || "本机")} · ${escapeFor(deps, item.value)}
        </span>
        <div class="selected-source-actions file-actions">
          ${item.isDir ? "" : `<button class="file-action" type="button" data-action="preview-selected-source" data-source-key="${escapeFor(deps, item.key)}" title="快速预览这个待传文件">快览</button>`}
          <button class="chip-remove" type="button" data-source-key="${escapeFor(deps, item.key)}" title="从待传源项中移除这一项">×</button>
        </div>
      </div>
    `;
  }

  function selectedSourceListMarkup(sources = [], deps = {}) {
    const list = Array.isArray(sources) ? sources : [];
    if (!list.length) {
      return transferPaneEmptyMarkup("还没有待传源项", "从文件树或弹窗把多个文件、文件夹加入这里。", { compact: true, icon: "+" }, deps);
    }
    const rows = list.map((item) => selectedSourceRowMarkup(item, deps)).join("");
    return `
    <div class="selected-source-toolbar">
      <span class="muted">提交时会依次传输这些源项。</span>
      <button class="secondary mini" type="button" data-action="clear-transfer-sources" title="清空当前所有待传源项">清空待传</button>
    </div>
    ${rows}
  `;
  }

  window.TransferSelectedSources = {
    selectedSourceCountText,
    selectedSourceListMarkup,
    transferPaneEmptyMarkup,
    transferPaneLoadingMarkup,
  };
})();
