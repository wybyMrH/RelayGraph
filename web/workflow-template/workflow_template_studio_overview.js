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

  function manageOverviewCardsMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const cards = Array.isArray(options.cards) ? options.cards : [];
    const activeTab = String(options.activeTab || "").trim();
    return cards.map((card) => `
      <button class="workspace-manage-overview-card status-${escapeFor(deps, card.state || "draft")}${card.tab === activeTab ? " active" : ""}" type="button" data-action="switch-workspace-manage-tab" data-tab="${escapeFor(deps, card.tab)}" title="切换到${escapeFor(deps, card.label)}配置页：${escapeFor(deps, card.detail)}">
        <span class="workspace-cockpit-label">${escapeFor(deps, card.label)}</span>
        <strong>${escapeFor(deps, card.title)}</strong>
        <p title="${escapeFor(deps, card.detail)}">${escapeFor(deps, card.detail)}</p>
        <em>${escapeFor(deps, card.next)}</em>
      </button>
    `).join("");
  }

  function manageFocusMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const focus = options.focus && typeof options.focus === "object" ? options.focus : {};
    return `
      <strong>${escapeFor(deps, focus.title)}</strong>
      <span>${escapeFor(deps, focus.detail)}</span>
      <em>${escapeFor(deps, focus.action)}</em>
    `;
  }

  function studioCardsMarkup(options = {}) {
    const deps = { escapeHtml: options.escapeHtml };
    const cards = Array.isArray(options.cards) ? options.cards : [];
    return cards.map((card) => `
    <article class="workspace-template-studio-card status-${escapeFor(deps, card.state || "draft")}">
      <span class="workspace-cockpit-label">${escapeFor(deps, card.label)}</span>
      <strong>${escapeFor(deps, card.title)}</strong>
      <p title="${escapeFor(deps, card.detail)}">${escapeFor(deps, card.detail)}</p>
    </article>
  `).join("");
  }

  window.WorkflowTemplateStudioOverview = {
    manageFocusMarkup,
    manageOverviewCardsMarkup,
    studioCardsMarkup,
  };
})();
