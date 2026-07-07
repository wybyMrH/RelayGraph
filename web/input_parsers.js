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

  window.InputParsers = {
    parseLineList,
    parseTagList,
    positiveNumberOrBlank,
  };
})();
