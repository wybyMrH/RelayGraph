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
    const key = fn(deps, "workspaceRunReplayCacheKey", () => "")(workspace.id, id);
    const cache = fn(deps, "workspaceRunReplayCacheStore", () => ({}))();
    if (key && appState(deps).ui.workspaceRunReplayBusyKey === key) return;
    if (current === id && cache[key]) {
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

  async function continuationRequest(url, options, deps) {
    // Reuse the configured local HTTP wait budget; abort is not server cancellation.
    const timeoutMs = fn(deps, "controlTimeoutMs", () => 0)();
    if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 300000) throw new Error("页面缺少有效的请求等待预算，请重新加载。");
    const controller = new AbortController();
    const deadline = Date.now() + timeoutMs;
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const payload = await fn(deps, "fetchJson", async () => ({}))(url, { ...options, signal: controller.signal });
      if (controller.signal.aborted || Date.now() >= deadline) throw new Error("请求等待已超时，执行结果需要核对。");
      return payload;
    } finally { clearTimeout(timer); }
  }

  async function controlContinuation(key, readOnly = false, deps = {}) {
    const state = appState(deps);
    const contextFor = fn(deps, "continuationContext", () => null);
    const run = (state.workspaces || []).flatMap((workspace) => workspace.runs || [])
      .find((item) => contextFor(item)?.key === key);
    const context = run && contextFor(run);
    if (!context) return;
    state.ui ||= {};
    const controls = state.ui.workspaceContinuationControls ||= {};
    if (["submitting", "checking"].includes(controls[key]?.phase)) return;
    if (!readOnly && (!context.canStop || controls[key]?.phase === "unknown")) return;
    const control = { phase: readOnly ? "checking" : "submitting", message: "正在核对后端结果，子任务按自身状态运行。", error: false };
    controls[key] = control;
    const render = () => fn(deps, "renderWorkspaceRunSurfaces", () => {})();
    const merge = (payload) => {
      if (payload.run?.id !== context.runId || payload.run?.workspace_id !== context.workspaceId) throw new Error("返回记录与原运行身份不符。");
      return fn(deps, "mergeWorkspaceRunDetailPayload", () => null)(context.workspaceId, payload);
    };
    const url = `/api/workspaces/${encodeValue(deps, context.workspaceId)}/runs/${encodeValue(deps, context.runId)}`;
    let rejected = false;
    let failure = "";
    render();
    try {
      if (!readOnly) {
        try {
          const payload = await continuationRequest(`${url}/stop-continuation`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ parent_attempt_id: context.attemptId, child_job_id: context.childJobId, child_policy: "keep_running" }),
          }, deps);
          const updated = merge(payload);
          if (contextFor(updated)?.key === key && contextFor(updated)?.stopped) {
            control.phase = "idle";
            control.message = "后续流程已停止。";
            return;
          }
          failure = "响应未能确认停止回执。";
        } catch (error) {
          rejected = Number(error.status) >= 400 && Number(error.status) < 500;
          failure = rejected ? (Number(error.status) === 409
            ? "停止未受理：运行正在推进、状态已变化，或任务引用需要核对。"
            : "停止未受理：请求未通过服务器校验，请刷新记录后核对。")
            : "停止请求的结果未确认，正在读取原运行核对。";
        }
      }
      control.phase = "checking";
      control.message = failure || "正在重新读取原运行核对停止结果。";
      render();
      try {
        const updated = merge(await continuationRequest(url, {}, deps));
        const current = contextFor(updated);
        if (current?.key === key && current.stopped) {
          control.phase = "idle";
          control.message = "已核对持久停止回执。";
          control.error = false;
        } else {
          control.phase = rejected || !current?.canStop ? "idle" : "uncertain";
          control.error = true;
          control.message = rejected ? `${failure} 已重新读取当前状态；${current?.canStop ? "当前仍在等待，可稍后重试。" : "当前已不在可停止的等待阶段。"}`
            : "尚未读到停止回执，不能确认原请求是否仍在处理。可重新核对；若仍在等待，也可按原身份再次请求停止。";
        }
      } catch (error) {
        control.phase = "unknown";
        control.error = true;
        control.message = "停止结果仍未确认，原运行暂时无法读取。请重新核对结果；不要据此认为流程已停止。";
      }
    } finally { render(); }
  }

  function handleRunSurfaceClick(event, deps = {}) {
    if (fn(deps, "handleReportClick", () => false)(event)) return true;
    const button = event.target.closest("[data-action]");
    if (["stop-run-continuation", "check-run-continuation"].includes(button?.dataset.action) && button.dataset.continuationKey) {
      fn(deps, "consumeClick", () => {})(event);
      void controlContinuation(button.dataset.continuationKey, button.dataset.action === "check-run-continuation", deps);
      return true;
    }
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
        button.closest(".workspace-job-target[data-child-job-id]")?.focus({ preventScroll: true });
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
    if (event.target.closest("button, a, input, select, textarea, summary, [contenteditable='true']")) return false;
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
    controlContinuation,
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
