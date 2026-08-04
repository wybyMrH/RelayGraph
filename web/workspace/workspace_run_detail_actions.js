(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function appState(deps = {}) {
    const source = typeof deps.state === "function" ? deps.state() : deps.state;
    return source && typeof source === "object" ? source : {};
  }

  function selectedWorkspace(deps = {}) {
    return fn(deps, "selectedWorkspace", () => null)();
  }

  function encodeValue(deps = {}, value) {
    return fn(deps, "encodeURIComponent", (item) => encodeURIComponent(item))(value);
  }

  function runKindLabel(deps = {}, value) {
    return fn(deps, "workspaceRunKindLabel", (item) => String(item || ""))(value);
  }

  function statusLabel(deps = {}, value = "") {
    return fn(deps, "zhStatus", (item) => String(item || ""))(value);
  }

  function formatBytesFor(deps = {}, value = 0) {
    return fn(deps, "formatBytes", (item) => String(item || 0))(value);
  }

  async function refreshRunDetail(runId, options = {}, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    if (!workspace?.id || !id) return null;
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(
        `/api/workspaces/${encodeValue(deps, workspace.id)}/runs/${encodeValue(deps, id)}`,
      );
      const run = fn(deps, "mergeWorkspaceRunDetailPayload", () => null)(workspace.id, payload);
      if (run && options.render !== false) fn(deps, "renderWorkspaceRunSurfaces", () => {})();
      return run;
    } catch (error) {
      if (!options.quiet) fn(deps, "setWorkspaceMessage", () => {})(error.message, true);
      return null;
    }
  }

  async function openRunDetail(runId, deps = {}) {
    const run = await refreshRunDetail(runId, {}, deps);
    if (!run) return;
    const steps = Array.isArray(run.steps) ? run.steps : [];
    const jobStep = steps.find((step) => String(step?.job_id || "").trim());
    if (jobStep?.job_id) {
      await fn(deps, "showLog", async () => {})(jobStep.job_id);
      return;
    }
    fn(deps, "setWorkspaceMessage", () => {})(
      `运行详情已刷新：${runKindLabel(deps, run.kind)} · ${statusLabel(deps, run.status || "pending")}。`,
    );
  }

  async function copyRunReplay(runId, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    if (!workspace?.id || !id) {
      fn(deps, "setWorkspaceMessage", () => {})("还没有可复制的运行回放。", true);
      return;
    }
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(
        `/api/workspaces/${encodeValue(deps, workspace.id)}/runs/${encodeValue(deps, id)}/replay`,
      );
      const replay = payload.replay && typeof payload.replay === "object" ? payload.replay : payload;
      await fn(deps, "copyTextToClipboard", async () => {})(JSON.stringify(replay, null, 2));
      fn(deps, "setWorkspaceMessage", () => {})("运行回放 JSON 已复制，可用于复盘、对比或导出。");
    } catch (error) {
      fn(deps, "setWorkspaceMessage", () => {})(error.message || "复制运行回放失败。", true);
    }
  }

  async function loadRunReplay(runId, options = {}, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    const key = fn(deps, "workspaceRunReplayCacheKey", () => "")(workspace?.id || "", id);
    if (!workspace?.id || !id || !key) return null;
    const cache = fn(deps, "workspaceRunReplayCacheStore", () => ({}))();
    if (!options.force && cache[key]) return cache[key];
    const errors = fn(deps, "workspaceRunReplayErrorStore", () => ({}))();
    delete errors[key];
    appState(deps).ui.workspaceRunReplayBusyKey = key;
    if (options.render !== false) fn(deps, "renderWorkspaceRunSurfaces", () => {})();
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(
        `/api/workspaces/${encodeValue(deps, workspace.id)}/runs/${encodeValue(deps, id)}/replay`,
      );
      const replay = payload.replay && typeof payload.replay === "object" ? payload.replay : payload;
      cache[key] = replay;
      delete errors[key];
      return replay;
    } catch (error) {
      errors[key] = error.message || "读取运行回放失败。";
      fn(deps, "setWorkspaceMessage", () => {})(errors[key], true);
      return null;
    } finally {
      const state = appState(deps);
      if (state.ui.workspaceRunReplayBusyKey === key) state.ui.workspaceRunReplayBusyKey = "";
      if (options.render !== false) fn(deps, "renderWorkspaceRunSurfaces", () => {})();
    }
  }

  async function toggleRunReplay(runId, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    if (!workspace?.id || !id) {
      fn(deps, "setWorkspaceMessage", () => {})("还没有可预览的运行回放。", true);
      return;
    }
    const current = fn(deps, "workspaceRunReplayOpenRunId", () => "")(workspace.id);
    if (current === id) {
      fn(deps, "setWorkspaceRunReplayOpenRunId", () => {})("", workspace.id);
      fn(deps, "renderWorkspaceRunSurfaces", () => {})();
      return;
    }
    fn(deps, "setWorkspaceRunReplayOpenRunId", () => {})(id, workspace.id);
    fn(deps, "renderWorkspaceRunSurfaces", () => {})();
    const replay = await loadRunReplay(id, {}, deps);
    if (replay) {
      const summary = fn(deps, "workspaceRunReplayCountSummary", () => ({ stepCount: 0, eventCount: 0, linkedJobCount: 0 }))(replay);
      fn(deps, "setWorkspaceMessage", () => {})(
        `回放预览已加载：${summary.stepCount} 步 · ${summary.eventCount} 事件 · ${summary.linkedJobCount} 个关联 Job。`,
      );
    }
  }

  async function downloadRunExport(runId, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    if (!workspace?.id || !id) {
      fn(deps, "setWorkspaceMessage", () => {})("还没有可导出的运行记录。", true);
      return;
    }
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(
        `/api/workspaces/${encodeValue(deps, workspace.id)}/runs/${encodeValue(deps, id)}/export`,
      );
      const exportPayload = payload.export && typeof payload.export === "object" ? payload.export : payload;
      const safeId = fn(deps, "safeId", (value) => String(value || ""));
      const filename = String(exportPayload.filename || `relaygraph-run-${safeId(workspace.id)}-${safeId(id)}.json`);
      fn(deps, "downloadTextFile", () => {})(JSON.stringify(exportPayload, null, 2), filename, "application/json;charset=utf-8");
      const summary = exportPayload.summary && typeof exportPayload.summary === "object" ? exportPayload.summary : {};
      const manifest = exportPayload.manifest && typeof exportPayload.manifest === "object" ? exportPayload.manifest : {};
      const truncation = manifest.truncation && typeof manifest.truncation === "object" ? manifest.truncation : {};
      const logTailCount = Number(truncation.log_tails || 0);
      const omittedBytes = Number(truncation.omitted_log_bytes || 0);
      const evidenceNote = logTailCount
        ? ` · ${logTailCount} 段日志为尾部窗口${omittedBytes ? `，省略 ${formatBytesFor(deps, omittedBytes)}` : ""}`
        : "";
      fn(deps, "setWorkspaceMessage", () => {})(
        `运行导出已下载：${Number(summary.step_count || 0)} 步 · ${Number(summary.log_count || 0)} 段日志 · ${Number(summary.report_count || 0)} 份报告${evidenceNote}。`,
      );
    } catch (error) {
      fn(deps, "setWorkspaceMessage", () => {})(error.message || "下载运行导出失败。", true);
    }
  }

  function setRunCompareBase(runId, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const id = String(runId || "").trim();
    if (!workspace?.id || !id) {
      fn(deps, "setWorkspaceMessage", () => {})("还没有可作为基准的运行记录。", true);
      return;
    }
    fn(deps, "setWorkspaceRunCompareBaseId", () => {})(id, workspace.id);
    fn(deps, "renderWorkspaceRunSurfaces", () => {})();
    fn(deps, "setWorkspaceMessage", () => {})("已设置运行对比基准。再点另一条运行记录的“对比”即可复制差异 JSON。");
  }

  async function compareRunToBase(runId, deps = {}) {
    const workspace = selectedWorkspace(deps);
    const targetId = String(runId || "").trim();
    const baseId = fn(deps, "workspaceRunCompareBaseId", () => "")(workspace?.id || "");
    if (!workspace?.id || !baseId || !targetId) {
      fn(deps, "setWorkspaceMessage", () => {})("请先设置一条运行记录作为对比基准。", true);
      return;
    }
    if (baseId === targetId) {
      fn(deps, "setWorkspaceMessage", () => {})("请选择另一条运行记录进行对比。", true);
      return;
    }
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(
        `/api/workspaces/${encodeValue(deps, workspace.id)}/runs/compare?base=${encodeValue(deps, baseId)}&target=${encodeValue(deps, targetId)}`,
      );
      const compare = payload.compare && typeof payload.compare === "object" ? payload.compare : payload;
      await fn(deps, "copyTextToClipboard", async () => {})(JSON.stringify(compare, null, 2));
      const delta = compare.diff?.metric_delta || {};
      const summary = [
        `步骤 ${Number(delta.step_count || 0) >= 0 ? "+" : ""}${Number(delta.step_count || 0)}`,
        `失败 ${Number(delta.failed_step_count || 0) >= 0 ? "+" : ""}${Number(delta.failed_step_count || 0)}`,
        `产物 ${Number(delta.artifact_count || 0) >= 0 ? "+" : ""}${Number(delta.artifact_count || 0)}`,
      ].join(" · ");
      fn(deps, "setWorkspaceMessage", () => {})(`运行对比 JSON 已复制：${summary}。`);
    } catch (error) {
      fn(deps, "setWorkspaceMessage", () => {})(error.message || "运行对比失败。", true);
    }
  }

  function handleRunSurfaceClick(event, deps = {}) {
    const button = event.target.closest("[data-action]");
    if (button?.dataset.action === "reset-workspace-run-filters") {
      fn(deps, "consumeClick", () => {})(event);
      fn(deps, "resetWorkspaceRunFilters", () => {})();
      return true;
    }
    if (button?.dataset.action === "cancel-agent-step" && button.dataset.agentExecutionId) {
      fn(deps, "consumeClick", () => {})(event);
      void fn(deps, "cancelAgentExecution", async () => {})(button.dataset.agentExecutionId);
      return true;
    }
    if (button?.dataset.action === "retry-agent-step" && button.dataset.nodeId) {
      fn(deps, "consumeClick", () => {})(event);
      void fn(deps, "runWorkspaceNode", async () => {})(button.dataset.nodeId, { prefer: "agent" });
      return true;
    }
    if (button?.dataset.action === "copy-workspace-run-replay" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      void copyRunReplay(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.action === "toggle-workspace-run-replay" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      void toggleRunReplay(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.action === "download-workspace-run-export" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      void downloadRunExport(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.action === "set-workspace-run-compare-base" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      setRunCompareBase(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.action === "compare-workspace-run" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      void compareRunToBase(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.action === "open-workspace-run" && button.dataset.runId) {
      fn(deps, "consumeClick", () => {})(event);
      void openRunDetail(button.dataset.runId, deps);
      return true;
    }
    if (button?.dataset.jobId) {
      const actionEvent = fn(deps, "actionProxyEvent", (baseEvent) => baseEvent)(event, button);
      if (button.dataset.action === "open-workspace-run") {
        fn(deps, "consumeClick", () => {})(actionEvent);
        void fn(deps, "showLog", async () => {})(button.dataset.jobId);
      } else if (button.dataset.action === "stop-workspace-run") {
        void fn(deps, "stopJob", async () => {})(actionEvent, button.dataset.jobId);
      } else if (button.dataset.action === "retry-workspace-run") {
        void fn(deps, "retryJob", async () => {})(actionEvent, button.dataset.jobId);
      } else if (button.dataset.action === "copy-workspace-run") {
        void fn(deps, "copyJob", async () => {})(actionEvent, button.dataset.jobId);
      } else if (button.dataset.action === "copy-workspace-run-script") {
        fn(deps, "consumeClick", () => {})(actionEvent);
        const state = appState(deps);
        const job = (Array.isArray(state.jobs) ? state.jobs : [])
          .find((item) => String(item?.id || "") === String(button.dataset.jobId || ""));
        const bundle = fn(deps, "workspaceJobExecutionBundle", () => ({}))(job || {});
        const scriptText = String(bundle.command_script?.text || "");
        void fn(deps, "copyTextToClipboard", async () => {})(scriptText)
          .then(() => fn(deps, "setWorkspaceMessage", () => {})("运行记录里的执行包脚本已复制。"))
          .catch((error) => fn(deps, "setWorkspaceMessage", () => {})(error.message || "复制脚本失败。", true));
      }
      return true;
    }
    const item = event.target.closest(".workspace-run-item[data-job-id]");
    if (item?.dataset.jobId) {
      void fn(deps, "showLog", async () => {})(item.dataset.jobId);
      return true;
    }
    const runItem = event.target.closest(".workspace-execution-run-item[data-run-id]");
    if (runItem?.dataset.runId) {
      void openRunDetail(runItem.dataset.runId, deps);
      return true;
    }
    return false;
  }

  window.WorkspaceRunDetailActions = {
    compareRunToBase,
    copyRunReplay,
    downloadRunExport,
    handleRunSurfaceClick,
    loadRunReplay,
    openRunDetail,
    refreshRunDetail,
    setRunCompareBase,
    toggleRunReplay,
  };
})();
