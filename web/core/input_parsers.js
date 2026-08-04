(function () {
  "use strict";

  function positiveNumberOrBlank(value) {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : "";
  }

  function parseLineList(value) {
    if (Array.isArray(value)) {
      return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
    }
    return Array.from(new Set(String(value || "").split(/\r?\n+/).map((item) => item.trim()).filter(Boolean)));
  }

  function parseTagList(value) {
    if (Array.isArray(value)) {
      return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
    }
    return Array.from(new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean)));
  }

  function safeId(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "item";
  }

  window.InputParsers = {
    parseLineList,
    parseTagList,
    positiveNumberOrBlank,
    safeId,
  };
})();
