(function () {
  "use strict";

  function processFilterKey(item = {}) {
    const serverName = item.server?.name || "";
    const process = item.process || {};
    return [
      serverName,
      item.server?.id || "",
      process.gpu_index ?? "",
      process.pid ?? "",
      process.user || "",
      process.used_memory_mib ?? "",
      process.command || process.process_name || "",
    ]
      .join(" ")
      .toLowerCase();
  }

  function processSortValue(item = {}, key = "") {
    const process = item.process || {};
    if (key === "server") return item.server?.name || item.server?.id || "";
    if (key === "gpu") return Number(process.gpu_index ?? -1);
    if (key === "pid") return Number(process.pid ?? 0);
    if (key === "user") return process.user || "";
    if (key === "vram") return Number(process.used_memory_mib || 0);
    if (key === "command") return process.command || process.process_name || "";
    return "";
  }

  function normalizedFilters(filters = {}) {
    return {
      query: String(filters.query || "").trim().toLowerCase(),
      server: String(filters.server || ""),
      user: String(filters.user || ""),
      gpu: String(filters.gpu || ""),
      sort: String(filters.sort || "server"),
      dir: String(filters.dir || ""),
    };
  }

  function filteredProcesses(items = [], filters = {}) {
    const source = Array.isArray(items) ? items : [];
    const active = normalizedFilters(filters);
    const filtered = source.filter((item) => {
      const process = item.process || {};
      if (active.query && !processFilterKey(item).includes(active.query)) return false;
      if (active.server && String(item.server?.id || "") !== active.server) return false;
      if (active.user && String(process.user || "") !== active.user) return false;
      if (active.gpu && String(process.gpu_index ?? "") !== active.gpu) return false;
      return true;
    });
    const direction = active.dir === "desc" ? -1 : 1;
    filtered.sort((a, b) => {
      const left = processSortValue(a, active.sort);
      const right = processSortValue(b, active.sort);
      if (typeof left === "number" && typeof right === "number") {
        return (left - right) * direction;
      }
      return String(left).localeCompare(String(right), "zh-Hans-CN", {
        numeric: true,
        sensitivity: "base",
      }) * direction;
    });
    return filtered;
  }

  function processMatchesGpuFocus(server = {}, process = {}, focus = {}) {
    if (!focus.serverId || focus.gpuIndex === "") return false;
    return String(server?.id || "") === String(focus.serverId) &&
      String(process?.gpu_index ?? "") === String(focus.gpuIndex);
  }

  window.MonitoringProcessFilters = {
    filteredProcesses,
    normalizedFilters,
    processFilterKey,
    processMatchesGpuFocus,
    processSortValue,
  };
})();
