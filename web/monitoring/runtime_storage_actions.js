(function () {
  "use strict";

  const CONTROL_IDS = [
    "runtimeStorageSaveBtn",
    "runtimeStorageCleanupBtn",
    "runtimeStoragePurgeBtn",
    "runtimeStateCleanupBtn",
    "runtimeStorageResetBtn",
  ];

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function runtimeStorageSummaryApi() {
    return window.RuntimeStorageSummary && typeof window.RuntimeStorageSummary === "object"
      ? window.RuntimeStorageSummary
      : null;
  }

  function setMessage(message, text = "", isError = false) {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("error", Boolean(isError));
  }

  function settingsInputPayload(deps = {}) {
    const previewAgeInput = element(deps, "runtimePreviewMaxAgeHours");
    const previewSizeInput = element(deps, "runtimePreviewMaxSizeMib");
    const logAgeInput = element(deps, "runtimeLogMaxAgeHours");
    const logFileInput = element(deps, "runtimeLogMaxFileMib");
    const logSizeInput = element(deps, "runtimeLogMaxSizeMib");
    const intervalInput = element(deps, "runtimeAutoIntervalMinutes");
    const remoteInput = element(deps, "runtimeRemoteCleanupEnabled");
    return {
      preview_max_age_hours: Number(previewAgeInput?.value || 0),
      preview_max_size_mib: Number(previewSizeInput?.value || 0),
      log_max_age_hours: Number(logAgeInput?.value || 0),
      log_max_file_mib: Number(logFileInput?.value || 0),
      log_max_size_mib: Number(logSizeInput?.value || 0),
      auto_cleanup_interval_minutes: Number(intervalInput?.value || 60),
      remote_log_cleanup_enabled: Boolean(remoteInput?.checked),
    };
  }

  function setControlsBusy(busy, deps = {}) {
    const state = deps.state && typeof deps.state === "object" ? deps.state : null;
    if (state?.ui) state.ui.runtimeStorageBusy = Boolean(busy);
    CONTROL_IDS.forEach((id) => {
      const button = element(deps, id);
      if (button) button.disabled = Boolean(busy);
    });
  }

  function isBusy(deps = {}) {
    return Boolean(deps.state?.ui?.runtimeStorageBusy);
  }

  function errorText(deps = {}, error, context = "") {
    return fn(deps, "humanizeFetchError", (value) => String(value?.message || value || "未知错误"))(error, context);
  }

  async function loadPanel(deps = {}) {
    const message = element(deps, "runtimeStorageMessage");
    try {
      const fetchJson = fn(deps, "fetchJson", async () => ({}));
      const [payload, runtimeState] = await Promise.all([
        fetchJson("/api/admin/runtime-storage"),
        fetchJson("/api/admin/runtime-state"),
      ]);
      fn(deps, "renderRuntimeStoragePanel", () => {})(payload);
      fn(deps, "renderRuntimeStatePanel", () => {})(runtimeState);
      setMessage(message, "");
    } catch (error) {
      setMessage(message, errorText(deps, error, "读取运行数据"), true);
    }
  }

  async function saveSettings(deps = {}) {
    if (isBusy(deps)) return;
    const message = element(deps, "runtimeStorageMessage");
    setMessage(message, "正在保存...");
    setControlsBusy(true, deps);
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))("/api/admin/runtime-storage/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsInputPayload(deps)),
      });
      fn(deps, "renderRuntimeStoragePanel", () => {})(payload);
      setMessage(message, "自动清理设置已保存。");
    } catch (error) {
      setMessage(message, errorText(deps, error, "保存设置"), true);
    } finally {
      setControlsBusy(false, deps);
    }
  }

  async function cleanupRuntimeState(deps = {}) {
    if (isBusy(deps)) return;
    const message = element(deps, "runtimeStorageMessage");
    const confirmAction = fn(deps, "confirm", () => true);
    if (!confirmAction("确定清理已完成/失败/停止的任务记录，并把每个项目的旧运行记录裁剪到最近 20 条吗？这不会删除运行日志、缓存、项目配置、聊天或密钥。")) return;
    setMessage(message, "正在清理运行记录...");
    setControlsBusy(true, deps);
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))("/api/admin/runtime-state/cleanup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clear_completed_jobs: true,
          prune_workspace_runs: true,
          max_runs_per_workspace: 20,
        }),
      });
      fn(deps, "renderRuntimeStatePanel", () => {})(payload.status || {});
      setMessage(
        message,
        `已清理运行记录：任务 ${Number(payload.removed_jobs || 0)} 条，项目 run ${Number(payload.removed_runs || 0)} 条，事件 ${Number(payload.removed_events || 0)} 条。日志文件没有删除。`,
      );
      await fn(deps, "loadStatus", async () => {})(true);
    } catch (error) {
      setMessage(message, errorText(deps, error, "清理运行记录"), true);
    } finally {
      setControlsBusy(false, deps);
    }
  }

  async function cleanupStorage(removeAll = false, deps = {}) {
    if (isBusy(deps)) return;
    const message = element(deps, "runtimeStorageMessage");
    const remoteInput = element(deps, "runtimeRemoteCleanupEnabled");
    const includeRemote = remoteInput?.checked !== false;
    const remoteText = includeRemote ? "、远程 $HOME/.total_control/logs" : "";
    const actionText = removeAll ? "清空" : "按当前阈值清理";
    const safetyText = removeAll
      ? "会删除范围内已有日志和预览缓存，但会保留正在运行任务和保留运行证据引用的日志。"
      : "会保留未超过当前时间/大小阈值的数据，以及正在运行任务和保留运行证据引用的日志。";
    const confirmAction = fn(deps, "confirm", () => true);
    if (!confirmAction(`确定${actionText} RelayGraph 的运行日志和预览缓存吗？范围仅限本机 data/logs${remoteText} 与 /tmp/total-control-file-preview；${safetyText}`)) return;
    setMessage(message, removeAll ? "正在清空..." : "正在按策略清理...");
    setControlsBusy(true, deps);
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))("/api/admin/runtime-storage/cleanup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...settingsInputPayload(deps),
          include_preview: true,
          include_logs: true,
          include_remote: includeRemote,
          remove_all: Boolean(removeAll),
        }),
      });
      fn(deps, "renderRuntimeStoragePanel", () => {})(payload.status || {});
      const api = runtimeStorageSummaryApi();
      const text = typeof api?.runtimeStorageCleanupMessage === "function"
        ? api.runtimeStorageCleanupMessage(payload, removeAll, { formatBytes: deps.formatBytes })
        : `${removeAll ? "已清空" : "已按策略清理"}。`;
      setMessage(message, text);
    } catch (error) {
      setMessage(message, errorText(deps, error, "清理运行数据"), true);
    } finally {
      setControlsBusy(false, deps);
    }
  }

  async function resetSettings(deps = {}) {
    if (isBusy(deps)) return;
    const message = element(deps, "runtimeStorageMessage");
    const confirmAction = fn(deps, "confirm", () => true);
    if (!confirmAction("确定恢复默认自动清理策略吗？这不会删除已有日志或缓存。")) return;
    setMessage(message, "正在重置...");
    setControlsBusy(true, deps);
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))("/api/admin/runtime-storage/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      fn(deps, "renderRuntimeStoragePanel", () => {})(payload);
      setMessage(message, "已恢复默认清理策略。");
    } catch (error) {
      setMessage(message, errorText(deps, error, "重置清理策略"), true);
    } finally {
      setControlsBusy(false, deps);
    }
  }

  function callAsync(deps, name, ...args) {
    void fn(deps, name, async () => {})(...args);
  }

  function bind(deps = {}) {
    element(deps, "runtimeStorageSaveBtn")?.addEventListener("click", () => {
      callAsync(deps, "saveRuntimeStorageSettings");
    });
    element(deps, "runtimeStorageCleanupBtn")?.addEventListener("click", () => {
      callAsync(deps, "cleanupRuntimeStorage", false);
    });
    element(deps, "runtimeStoragePurgeBtn")?.addEventListener("click", () => {
      callAsync(deps, "cleanupRuntimeStorage", true);
    });
    element(deps, "runtimeStateCleanupBtn")?.addEventListener("click", () => {
      callAsync(deps, "cleanupRuntimeState");
    });
    element(deps, "runtimeStorageResetBtn")?.addEventListener("click", () => {
      callAsync(deps, "resetRuntimeStorageSettings");
    });
  }

  window.RuntimeStorageActions = {
    bind,
    cleanupRuntimeState,
    cleanupStorage,
    loadPanel,
    resetSettings,
    saveSettings,
    setControlsBusy,
    settingsInputPayload,
  };
})();
