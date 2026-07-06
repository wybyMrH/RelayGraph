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

  function rowPadding(level) {
    return 6 + Number(level || 0) * 18;
  }

  function sourceTreeNodeRowMarkup(entry = {}, options = {}, deps = {}) {
    const level = Number(options.level || 0);
    const icon = options.icon || "·";
    const previewingClass = options.previewingClass || "";
    const selectedClass = options.selectedClass || "";
    const selectedSource = options.selectedSource || null;
    const sourceAction = selectedSource
      ? `<button class="file-action selected-source-toggle" type="button" data-action="remove-transfer-source" data-source-key="${escapeFor(deps, selectedSource.key)}" title="取消加入这个待传源项">取消</button>`
      : `<button class="file-action primary-soft" type="button" data-action="add-transfer-source" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="把这个文件或目录加入待传源项">加入</button>`;
    return `
    <div class="file-tree-row${level === 0 ? " root-row" : ""}${previewingClass}${selectedClass}" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" style="padding-left:${rowPadding(level)}px">
      <button class="file-toggle" type="button" data-action="toggle-transfer-node" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="${entry.is_dir ? "展开或收起这个目录" : "文件项不可展开"}">${escapeFor(deps, icon)}</button>
      <div class="file-tree-main">
        <span class="file-name" title="${escapeFor(deps, entry.path)}">${entry.is_dir ? "[DIR]" : "[FILE]"} ${escapeFor(deps, entry.name)}</span>
        ${entry.size_text ? `<span class="file-meta">${escapeFor(deps, entry.size_text)}</span>` : ""}
      </div>
      <span class="file-actions">
        ${entry.is_dir ? "" : `<button class="file-action" type="button" data-action="preview-transfer-node" data-path="${escapeFor(deps, entry.path)}" title="把这个文件拉到本机缓存后快速预览">快览</button>`}
        ${sourceAction}
        <button class="file-action" type="button" data-action="ignore-transfer-node" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="把这个路径加入 rsync 忽略规则">忽略</button>
      </span>
    </div>
  `;
  }

  function targetTreeNodeRowMarkup(entry = {}, options = {}, deps = {}) {
    const level = Number(options.level || 0);
    const icon = options.icon || "·";
    const selectedClass = options.selectedClass || "";
    return `
    <div class="file-tree-row${level === 0 ? " root-row" : ""}${selectedClass}" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" style="padding-left:${rowPadding(level)}px">
      <button class="file-toggle" type="button" data-action="toggle-target-node" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="展开或收起这个目标目录">${escapeFor(deps, icon)}</button>
      <div class="file-tree-main">
        <span class="file-name" title="${escapeFor(deps, entry.path)}">[DIR] ${escapeFor(deps, entry.name || entry.path)}</span>
      </div>
    </div>
  `;
  }

  window.TransferTreeMarkup = {
    sourceTreeNodeRowMarkup,
    targetTreeNodeRowMarkup,
  };
})();
