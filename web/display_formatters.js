(function () {
  "use strict";

  function fmtMiB(value) {
    const n = Number(value || 0);
    if (n >= 1024) return `${(n / 1024).toFixed(1)} GiB`;
    return `${n} MiB`;
  }

  function formatBytes(value) {
    let n = Number(value || 0);
    if (!Number.isFinite(n) || n <= 0) return "0 B";
    const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
    let index = 0;
    while (n >= 1024 && index < units.length - 1) {
      n /= 1024;
      index += 1;
    }
    if (index === 0) return `${Math.round(n)} ${units[index]}`;
    return `${n.toFixed(n >= 10 ? 1 : 2)} ${units[index]}`;
  }

  function formatPercent(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "--";
    return `${Math.max(0, Math.min(100, n)).toFixed(n % 1 === 0 ? 0 : 1)}%`;
  }

  function compactText(value, limit = 80) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    const max = Math.max(Number(limit) || 80, 12);
    return text.length > max ? `${text.slice(0, max - 1)}...` : text;
  }

  window.DisplayFormatters = {
    compactText,
    fmtMiB,
    formatBytes,
    formatPercent,
  };
})();
