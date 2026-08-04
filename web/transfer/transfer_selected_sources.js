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

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function transferState(deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : {};
    if (!state.transfer || typeof state.transfer !== "object") state.transfer = {};
    if (!Array.isArray(state.transfer.sources)) state.transfer.sources = [];
    return state.transfer;
  }

  function sourceKey(serverId, path, isDir = false, deps = {}) {
    const normalize = fn(deps, "normalizePathForCompare", (value) => String(value || "").trim().replace(/\/+$/, "").toLowerCase());
    return `${serverId || "local"}|${normalize(path)}|${isDir ? "dir" : "file"}`;
  }

  function selectedSourceKey(path, isDir = false, serverId, deps = {}) {
    const transferPathOnly = fn(deps, "transferPathOnly", (value) => String(value || "").trim());
    const sourceServerId = fn(deps, "transferSourceServerId", () => "local");
    const effectiveServerId = serverId === undefined ? sourceServerId() : serverId;
    return sourceKey(effectiveServerId || "local", transferPathOnly(path), isDir, deps);
  }

  function sourceItemByPath(path, isDir = false, serverId, deps = {}) {
    const transfer = transferState(deps);
    const key = selectedSourceKey(path, isDir, serverId, deps);
    return transfer.sources.find((item) => item.key === key) || null;
  }

  function addSource(path, isDir = false, options = {}, deps = {}) {
    const transfer = transferState(deps);
    const transferPathOnly = fn(deps, "transferPathOnly", (value) => String(value || "").trim());
    const sourcePath = transferPathOnly(path);
    if (!sourcePath) return;
    const sourceServerId = fn(deps, "transferSourceServerId", () => "local");
    const serverById = fn(deps, "serverById", () => null);
    const server = options.server || serverById(sourceServerId());
    const serverId = server?.id || sourceServerId() || "local";
    const key = sourceKey(serverId, sourcePath, isDir, deps);
    if (!transfer.sources.some((item) => item.key === key)) {
      const rsyncValue = fn(deps, "rsyncTransferSourceValue", ({ path: value }) => value);
      transfer.sources.push({
        key,
        serverId,
        serverName: server?.name || serverId,
        path: sourcePath,
        isDir,
        value: rsyncValue({ path: sourcePath, isDir, serverId }),
      });
    }
    fn(deps, "renderSelectedSources", () => {})();
    fn(deps, "renderTransferTree", () => {})();
    const message = element(deps, "transferMessage");
    if (message && options.silent !== true) {
      message.textContent = `已加入待传源项：${fn(deps, "pathBaseName", (value) => value)(sourcePath)}`;
      message.classList.remove("error");
    }
  }

  function removeSource(key, deps = {}) {
    const transfer = transferState(deps);
    transfer.sources = transfer.sources.filter((item) => item.key !== key);
    fn(deps, "renderSelectedSources", () => {})();
    fn(deps, "renderTransferTree", () => {})();
  }

  function clearSources(deps = {}) {
    const transfer = transferState(deps);
    transfer.sources = [];
    fn(deps, "renderSelectedSources", () => {})();
    fn(deps, "renderTransferTree", () => {})();
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
    addSource,
    clearSources,
    removeSource,
    selectedSourceKey,
    selectedSourceCountText,
    selectedSourceListMarkup,
    sourceItemByPath,
    sourceKey,
    transferPaneEmptyMarkup,
    transferPaneLoadingMarkup,
  };
})();
