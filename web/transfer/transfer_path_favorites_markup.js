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

  function pathBaseNameFor(deps, path) {
    if (typeof deps.pathBaseName === "function") return deps.pathBaseName(path);
    return String(path || "").replace(/\/+$/, "").split("/").pop() || String(path || "");
  }

  function normalizeFor(deps, path) {
    if (typeof deps.normalizePathForCompare === "function") return deps.normalizePathForCompare(path);
    return String(path || "").replace(/\/+$/, "");
  }

  function favoriteLabel(item = {}, deps = {}) {
    return item.label || pathBaseNameFor(deps, item.path);
  }

  function transferPathFavoritesListMarkup(mode = "source", favorites = [], deps = {}) {
    const list = Array.isArray(favorites) ? favorites : [];
    return `
    <div class="transfer-path-favorites-list">
      ${list.map((item) => `
        <span class="transfer-path-favorite-item">
          <button class="transfer-path-favorite-btn" type="button" data-action="open-transfer-favorite" data-mode="${escapeFor(deps, mode)}" data-path="${escapeFor(deps, item.path)}" title="${escapeFor(deps, item.path)}">${escapeFor(deps, favoriteLabel(item, deps))}</button>
          <button class="transfer-path-favorite-remove" type="button" data-action="remove-transfer-favorite" data-mode="${escapeFor(deps, mode)}" data-path="${escapeFor(deps, item.path)}" title="从收藏中移除">×</button>
        </span>
      `).join("")}
    </div>
  `;
  }

  function filePickerFavoritesSidebarMarkup(favorites = [], currentPath = "", deps = {}) {
    const list = Array.isArray(favorites) ? favorites : [];
    if (!list.length) {
      return `
      <div class="file-picker-sidebar-section">
        <div class="file-picker-sidebar-label">收藏路径 <span class="muted">本机</span></div>
        <p class="file-picker-favorites-empty muted">当前主机还没有收藏，浏览到目录后点「收藏」。</p>
      </div>
    `;
    }
    return `
    <div class="file-picker-sidebar-section">
      <div class="file-picker-sidebar-label">收藏路径 <span class="muted">本机</span></div>
      ${list.map((item) => {
        const active = currentPath && normalizeFor(deps, currentPath) === normalizeFor(deps, item.path);
        return `
          <div class="favorite-path-row">
            <button class="root-button favorite-path-button${active ? " active" : ""}" type="button" data-action="open-favorite-path" data-path="${escapeFor(deps, item.path)}" title="${escapeFor(deps, item.path)}">
              <strong>${escapeFor(deps, favoriteLabel(item, deps))}</strong>
              <span>${escapeFor(deps, item.path)}</span>
            </button>
            <button class="favorite-path-remove" type="button" data-action="remove-favorite-path" data-path="${escapeFor(deps, item.path)}" title="移除收藏">×</button>
          </div>
        `;
      }).join("")}
    </div>
  `;
  }

  window.TransferPathFavoritesMarkup = {
    filePickerFavoritesSidebarMarkup,
    transferPathFavoritesListMarkup,
  };
})();
