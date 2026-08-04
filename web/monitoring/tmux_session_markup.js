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

  function tmuxErrorMarkup(error = "", deps = {}) {
    return `<div class="empty error-text">${escapeFor(deps, error)}</div>`;
  }

  function tmuxEmptyMarkup() {
    return '<div class="empty">所选服务器暂无 tmux 会话。</div>';
  }

  function tmuxSessionItemMarkup(session = {}, options = {}, deps = {}) {
    const active = options.activeClass || "";
    return `
      <div class="tmux-item${active}" onclick="showTmux('${escapeFor(deps, session.name)}')">
        <span class="tmux-name">${escapeFor(deps, session.name)}</span>
        <span class="muted">${escapeFor(deps, session.windows)} 窗口 · ${session.attached ? "已连接" : "未连接"}</span>
      </div>
    `;
  }

  window.TmuxSessionMarkup = {
    tmuxEmptyMarkup,
    tmuxErrorMarkup,
    tmuxSessionItemMarkup,
  };
})();
