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

  function stripAnsi(value) {
    return String(value || "")
      .replace(/\uFFFD\[[0-?]*[ -/]*[@-~]/g, "")
      .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
      .replace(/\x1b\][^\x07]*(?:\x07|\x1b\\)/g, "")
      .replace(/\x1b[()#%*+\-.\/][0-9A-Za-z]/g, "")
      .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "");
  }

  function fmtDate(value) {
    if (!value) return "";
    return String(value).replace("T", " ").slice(0, 16);
  }

  window.DisplayFormatters = {
    compactText,
    fmtDate,
    fmtMiB,
    formatBytes,
    formatPercent,
    stripAnsi,
  };
})();
