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

  function normalizeFor(deps, path) {
    if (typeof deps.normalizePathForCompare === "function") return deps.normalizePathForCompare(path);
    return String(path || "").replace(/\/+$/, "");
  }

  function filePickerRootsMarkup(roots = [], currentPath = "", favoritesSidebarHtml = "", deps = {}) {
    const list = Array.isArray(roots) ? roots : [];
    const rootButtons = list
      .map((root) => {
        const active = currentPath && normalizeFor(deps, currentPath).startsWith(normalizeFor(deps, root.path));
        return `
        <button class="root-button${active ? " active" : ""}" type="button" data-path="${escapeFor(deps, root.path)}" title="快速跳到这个常用根目录">
          <strong>${escapeFor(deps, root.label)}</strong>
          <span title="${escapeFor(deps, root.path)}">${escapeFor(deps, root.path)}</span>
        </button>
      `;
      })
      .join("");
    return `
    <div class="file-picker-sidebar-section">
      <div class="file-picker-sidebar-label">根目录</div>
      ${rootButtons || '<p class="file-picker-favorites-empty muted">暂无根目录。</p>'}
    </div>
    ${favoritesSidebarHtml || ""}
  `;
  }

  function filePickerHeaderText(payload = {}, server = null) {
    return {
      title: payload.mode === "target" ? "选择目标目录" : "选择源文件或文件夹",
      subtitle: payload.mode === "target"
        ? `正在浏览 ${server?.name || "目标服务器"}，点目录进入，或用「选择」设为路径。`
        : server && server.mode !== "local"
          ? `正在浏览 ${server.name} 的文件系统，点目录进入、点文件快览。`
          : "浏览 WSL 可访问路径，例如 /mnt/e、/mnt/f、Home 和项目目录；点目录进入、点文件快览。",
      chooseDirText: payload.mode === "target" ? "选择当前目录" : "加入当前文件夹",
    };
  }

  function filePickerEntryRowMarkup(entry = {}, options = {}, deps = {}) {
    const mode = options.mode || "source";
    const selectedClass = options.selectedClass || "";
    const previewActiveClass = options.previewActiveClass || "";
    const sourceSelectedClass = options.sourceSelectedClass || "";
    const selectedSource = options.selectedSource || null;
    const meta = options.meta || "";
    const chooseAction = selectedSource
      ? `<button class="file-action selected-source-toggle" type="button" data-action="remove-picker-source" data-source-key="${escapeFor(deps, selectedSource.key)}" title="取消加入这个待传源项">取消</button>`
      : `<button class="file-action${mode !== "target" && entry.is_dir ? " primary-soft" : ""}" type="button" data-action="choose-picker" title="${mode === "target" ? "把这个目录设为目标路径" : "把这个文件或目录加入源项"}">${mode === "target" ? "选择" : "加入"}</button>`;
    return `
      <div class="file-picker-row${selectedClass}${previewActiveClass}${sourceSelectedClass}" data-path="${escapeFor(deps, entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}">
        <div class="file-picker-row-main">
          <span class="file-kind">${entry.is_dir ? "DIR" : "FILE"}</span>
          <div class="file-picker-row-text">
            <span class="file-name" title="${escapeFor(deps, entry.path)}">${escapeFor(deps, entry.name)}</span>
            <span class="file-picker-row-meta" title="${escapeFor(deps, meta)}">${escapeFor(deps, meta)}</span>
          </div>
        </div>
        <div class="file-actions file-picker-row-actions">
          ${entry.is_dir ? "" : '<button class="file-action" type="button" data-action="preview-picker" title="把这个文件拉到本机缓存后快速预览">快览</button>'}
          ${chooseAction}
        </div>
      </div>
    `;
  }

  function filePickerEmptyListMarkup() {
    return '<div class="empty compact-empty">目录为空。</div>';
  }

  function filePickerEntriesMarkup(payload = {}, options = {}, deps = {}) {
    const entries = payload.entries || [];
    const rows = entries
      .map((entry) => {
        const selectedClass = normalizeFor(deps, entry.path) === normalizeFor(deps, payload.selectedPath || "")
          ? " selected"
          : "";
        const previewActiveClass = typeof deps.previewPathMatchesState === "function" && deps.previewPathMatchesState(entry.path, payload.serverId || "")
          ? " preview-active"
          : "";
        const selectedSource = payload.mode === "target" || typeof deps.transferSourceItemByPath !== "function"
          ? null
          : deps.transferSourceItemByPath(entry.path, entry.is_dir, payload.serverId);
        const sourceSelectedClass = selectedSource ? " transfer-source-selected" : "";
        const meta = [
          entry.is_dir ? "文件夹" : (entry.size_text || "文件"),
          typeof deps.fmtDate === "function" ? (deps.fmtDate(entry.mtime) || "") : "",
        ].filter(Boolean).join(" · ");
        return filePickerEntryRowMarkup(entry, {
          meta,
          mode: payload.mode,
          previewActiveClass,
          selectedClass,
          selectedSource,
          sourceSelectedClass,
        }, deps);
      })
      .join("");
    return rows || filePickerEmptyListMarkup();
  }

  window.FilePickerMarkup = {
    filePickerEntriesMarkup,
    filePickerEmptyListMarkup,
    filePickerEntryRowMarkup,
    filePickerHeaderText,
    filePickerRootsMarkup,
  };
})();
