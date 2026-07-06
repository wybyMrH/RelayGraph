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

  function ignoreCountText(ignores = []) {
    return `${Array.isArray(ignores) ? ignores.length : 0} 项`;
  }

  function ignoreChipsMarkup(ignores = [], deps = {}) {
    const list = Array.isArray(ignores) ? ignores : [];
    if (!list.length) {
      return '<span class="muted">可以从左侧文件树点“忽略”加入。</span>';
    }
    return list
      .map((item) => `
      <span class="ignore-chip" title="${escapeFor(deps, item)}">
        <span>${escapeFor(deps, item)}</span>
        <button class="chip-remove" type="button" data-ignore="${escapeFor(deps, item)}" title="移除这条忽略规则">×</button>
      </span>
    `)
      .join("");
  }

  window.TransferIgnoreChips = {
    ignoreChipsMarkup,
    ignoreCountText,
  };
})();
