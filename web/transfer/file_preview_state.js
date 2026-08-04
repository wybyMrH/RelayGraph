(function () {
  "use strict";

  function fallbackPathBaseName(path) {
    const normalized = String(path || "").replace(/[\\\/]+$/, "");
    return normalized.split(/[\\\/]/).filter(Boolean).pop() || normalized || "传输";
  }

  function pathBaseNameFor(deps = {}, path = "") {
    return typeof deps.pathBaseName === "function" ? deps.pathBaseName(path) : fallbackPathBaseName(path);
  }

  function isLikelyTextPreviewPath(path, deps = {}) {
    const base = pathBaseNameFor(deps, String(path || "")).toLowerCase();
    if (!base) return false;
    if (base.startsWith(".") && base.length > 1) return true;
    if (["dockerfile", "makefile", "gemfile", "rakefile", "procfile", "license", "readme", "changelog"].includes(base)) {
      return true;
    }
    const dot = base.lastIndexOf(".");
    if (dot <= 0) return false;
    const suffix = base.slice(dot);
    const textSuffixes = new Set([
      ".bat", ".c", ".cc", ".cfg", ".conf", ".cpp", ".cs", ".css", ".csv", ".dockerfile", ".env", ".go", ".h", ".hpp",
      ".htm", ".html", ".ini", ".ipynb", ".java", ".js", ".json", ".jsonc", ".jsx", ".kt", ".less", ".log", ".lua", ".md",
      ".mjs", ".out", ".php", ".ps1", ".py", ".rb", ".rs", ".rst", ".sass", ".scala", ".scss", ".sh", ".sql", ".svg",
      ".swift", ".toml", ".ts", ".tsv", ".tsx", ".txt", ".vue", ".xml", ".yaml", ".yml", ".zsh",
    ]);
    return textSuffixes.has(suffix);
  }

  function formatPreviewText(path, text, deps = {}) {
    const base = pathBaseNameFor(deps, String(path || "")).toLowerCase();
    if (base.endsWith(".json") || base.endsWith(".jsonc")) {
      try {
        return JSON.stringify(JSON.parse(text), null, 2);
      } catch {
        return text;
      }
    }
    return text;
  }

  window.FilePreviewState = {
    formatPreviewText,
    isLikelyTextPreviewPath,
  };
})();
