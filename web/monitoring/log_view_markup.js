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

  function fallbackEscapeRegExp(value) {
    return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function escapeHtmlFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function escapeRegExpFor(deps, value) {
    return (typeof deps.escapeRegExp === "function" ? deps.escapeRegExp : fallbackEscapeRegExp)(value);
  }

  function buildLogHighlightMarkup(source = "", query = "", deps = {}) {
    const regex = new RegExp(escapeRegExpFor(deps, query), "gi");
    let html = "";
    let lastIndex = 0;
    let matches = 0;
    for (const match of String(source).matchAll(regex)) {
      const start = match.index ?? 0;
      const end = start + match[0].length;
      html += escapeHtmlFor(deps, String(source).slice(lastIndex, start));
      html += `<mark class="log-hit" data-hit-index="${matches}">${escapeHtmlFor(deps, match[0])}</mark>`;
      lastIndex = end;
      matches += 1;
    }
    html += escapeHtmlFor(deps, String(source).slice(lastIndex));
    return { html, matches };
  }

  window.LogViewMarkup = {
    buildLogHighlightMarkup,
  };
})();
