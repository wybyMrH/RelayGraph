(function () {
  "use strict";

  function ensureDirectorySlash(path) {
    const text = String(path || "").trim();
    if (!text) return "";
    return text.endsWith("/") ? text : `${text}/`;
  }

  function normalizePathForCompare(path) {
    return String(path || "").replace(/\/+$/, "");
  }

  function parentDirectoryPath(path) {
    const text = String(path || "").trim().replace(/\/+$/, "");
    if (!text || text === "/") return "";
    const index = text.lastIndexOf("/");
    if (index <= 0) return "/";
    return text.slice(0, index) || "/";
  }

  function parseRsyncTargetPath(value) {
    const text = String(value || "").trim();
    const match = text.match(/^[^:]+:(\/.*)$/);
    if (match) return match[1];
    return text.startsWith("/") ? text : "";
  }

  function parseRsyncTargetPrefix(value) {
    const text = String(value || "").trim();
    const match = text.match(/^([^:]+):\/.*$/);
    return match ? match[1] : "";
  }

  function transferPathOnly(value) {
    return parseRsyncTargetPath(value) || String(value || "").trim();
  }

  function transferTargetPrefix(server) {
    if (!server || server.mode === "local") return "";
    return `${server.target || server.ssh_alias || server.host_name || server.id}:`;
  }

  function parseIgnoreText(text) {
    return Array.from(
      new Set(
        String(text || "")
          .split(/[\n,]+/)
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    );
  }

  window.TransferPathUtils = {
    ensureDirectorySlash,
    normalizePathForCompare,
    parentDirectoryPath,
    parseIgnoreText,
    parseRsyncTargetPath,
    parseRsyncTargetPrefix,
    transferPathOnly,
    transferTargetPrefix,
  };
})();
