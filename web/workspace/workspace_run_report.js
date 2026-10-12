(function () {
  "use strict";

  const reportStep = (run) => (run?.steps || []).find((step) => step.node_kind === "eval.report");
  const fileFor = (step) => step?.output_value?.report_file || null;
  const signature = (step) => JSON.stringify([step?.step_id, step?.attempt_id, step?.status, fileFor(step)]);
  const current = (view, deps) => Boolean(view) && deps.ui.workspaceMode === "runs" && deps.ui.workspaceRunReport === view
    && deps.selectedWorkspace()?.id === view.workspaceId
    && deps.ui.workspaceRunReportSelections?.[view.workspaceId] === view.runId;

  function statusInfo(step, report = fileFor(step)) {
    if (report?.file_verified) return { label: "文件已核对", tone: "ready", detail: "正文来自这次运行的报告文件。" };
    const reason = report?.reason || "";
    const reasons = {
      report_file_missing: "报告文件已丢失；原执行证据仍保留。",
      report_file_hash_or_size_mismatch: "报告文件与这次回答不一致，核对未通过。",
      report_file_unreadable: "报告文件无法读取，请检查本机文件权限。",
      report_directory_unavailable: "报告存储目录不可用。",
      report_file_publish_failed: "报告文件写入失败，请检查目录权限或文件系统。",
      report_not_regular_file: "报告位置被其他文件类型占用，无法核对。",
      report_sensitive_path_blocked: "报告目录不允许写入，请检查本机配置。",
      report_directory_invalid_or_symlink: "报告目录无效或包含符号链接。",
      report_receipt_identity_mismatch: "报告文件记录与本次执行不一致。",
      report_file_changed_during_read: "读取时文件发生变化，请重新核对。",
    };
    if (reasons[reason]) return { label: "交付不完整", tone: "warning", detail: reasons[reason] };
    if (["pending", "queued", "running", "waiting", "blocked"].includes(step?.status) || reason === "report_file_pending") {
      return { label: "等待报告交付", tone: "waiting", detail: "报告尚未生成或文件正在交付，可稍后重新核对。" };
    }
    if (step?.status === "skipped") return { label: "未生成报告", tone: "warning", detail: "报告步骤未执行，请返回运行记录查看前置任务。" };
    if (["failed", "stopped"].includes(step?.status)) return { label: "未生成报告", tone: "warning", detail: "报告步骤未成功完成，请返回运行记录查看原因。" };
    if (report) return { label: "交付不完整", tone: "warning", detail: "尚无通过核对的报告文件，原回答只能作为执行证据。" };
    return { label: "没有报告文件", tone: "warning", detail: "这条记录没有可读取的报告文件；历史记录不会自动补文件。" };
  }

  function entryMarkup(step, run, deps) {
    if (step.node_kind !== "eval.report") return "";
    const info = statusInfo(step);
    const e = deps.escapeHtml;
    return `<div class="workspace-report-entry"><span class="workspace-report-status status-${info.tone}">${e(info.label)}</span>
      <button class="secondary mini" type="button" data-action="open-workspace-report" data-run-id="${e(run.id)}">${fileFor(step)?.file_verified ? "阅读报告" : "查看报告状态"}</button></div>`;
  }

  function persist(deps) {
    deps.saveSelections(deps.ui.workspaceRunReportSelections);
  }

  function open(runId, deps) {
    const workspace = deps.selectedWorkspace();
    if (!workspace?.id || !runId) return;
    deps.ui.workspaceRunReportSelections ||= {};
    deps.ui.workspaceRunReportSelections[workspace.id] = runId;
    deps.ui.workspaceRunReport = null;
    deps.clearMessage();
    persist(deps);
    deps.render();
    deps.element("workspaceReportTitle")?.focus();
    deps.element("workspaceRunReportPanel")?.scrollIntoView({ block: "start" });
  }

  function close(deps) {
    const workspaceId = deps.selectedWorkspace()?.id;
    const runId = deps.ui.workspaceRunReportSelections?.[workspaceId];
    delete deps.ui.workspaceRunReportSelections?.[workspaceId];
    deps.ui.workspaceRunReport = null;
    persist(deps);
    deps.render();
    const buttons = deps.element("workspaceRunList")?.querySelectorAll("[data-action='open-workspace-report']") || [];
    Array.from(buttons).find((button) => button.dataset.runId === runId)?.focus();
  }

  async function load(view, deps) {
    if (!current(view, deps)) return;
    const request = ++view.request;
    view.phase = "loading";
    view.report = null;
    view.error = "";
    deps.render();
    try {
      const enc = encodeURIComponent;
      const payload = await deps.fetchJson(`/api/workspaces/${enc(view.workspaceId)}/runs/${enc(view.runId)}/report`);
      if (!current(view, deps) || view.request !== request) return;
      const report = payload.report;
      if (payload.workspace_id !== view.workspaceId || payload.run_id !== view.runId || !report || typeof report !== "object"
        || (report.file_verified && (typeof report.content !== "string" || report.run_id !== view.runId
          || (view.step?.step_id && report.step_id !== view.step.step_id)
          || (view.step?.attempt_id && report.attempt_id !== view.step.attempt_id)))) {
        throw new Error("报告响应与所选执行不一致，请重新核对。");
      }
      view.report = { ...report, content: report.file_verified ? report.content : null };
      view.phase = "loaded";
    } catch (error) {
      if (!current(view, deps) || view.request !== request) return;
      view.report = null;
      view.error = String(error.message || "读取报告失败，请重新核对。");
      view.phase = "error";
    }
    if (current(view, deps) && view.request === request) deps.render();
  }

  function panelMarkup(view, workspace, deps, detailsOpen) {
    const e = deps.escapeHtml;
    const info = statusInfo(view.step, view.report || fileFor(view.step));
    const report = view.report;
    const busy = view.phase === "loading";
    const content = view.phase === "loaded" && report?.file_verified ? report.content : null;
    const title = view.step?.node_title || "运行报告";
    return `<div class="workspace-report-toolbar">
      <button class="secondary" type="button" data-action="close-workspace-report">返回运行记录</button>
      <div><button class="secondary" type="button" data-action="refresh-workspace-report"${busy ? " disabled" : ""}>${busy ? "正在核对…" : "重新核对"}</button>
      <button class="secondary" type="button" data-action="download-workspace-run-export" data-run-id="${e(view.runId)}">导出</button></div>
    </div>
    <header class="workspace-report-heading"><h3 id="workspaceReportTitle" tabindex="-1">${e(title)}</h3>
      <p>${e(workspace.name || workspace.id)} · ${e(deps.fmtDate(view.run?.created_at || "") || "执行记录")}</p></header>
    <div class="workspace-report-notice" role="status" aria-live="polite">
      <span>执行：${e(deps.zhStatus(view.run?.status || "pending"))}</span>
      <strong class="workspace-report-status status-${busy ? "waiting" : view.error ? "warning" : info.tone}">${e(busy ? "正在读取并核对文件" : view.error ? "读取失败，尚未核对" : info.label)}</strong>
      <p>${e(busy ? "正在从服务读取这次报告。" : view.error ? view.error : info.detail)}</p>
    </div>
    ${content !== null ? `<div class="workspace-report-body" role="region" aria-label="本次报告正文">${e(content)}</div>` : ""}
    <details class="workspace-report-evidence"${detailsOpen ? " open" : ""}><summary>文件核对信息</summary>
      <dl><dt>运行</dt><dd>${e(view.runId)}</dd><dt>步骤 / 尝试</dt><dd>${e(report?.step_id || view.step?.step_id || "未记录")} / ${e(report?.attempt_id || view.step?.attempt_id || "未记录")}</dd>
      ${report?.report_id ? `<dt>文件引用</dt><dd>${e(report.path || report.report_id)}</dd>` : ""}
      ${report?.sha256 ? `<dt>内容摘要</dt><dd>${e(report.sha256)}</dd><dt>文件大小</dt><dd>${e(deps.formatBytes(report.size_bytes))}（${e(report.size_bytes)} 字节）</dd>` : ""}
      ${report?.verified_at ? `<dt>曾通过核对</dt><dd>${e(deps.fmtDate(report.verified_at))}</dd>` : ""}
      ${report?.reason ? `<dt>原因编号</dt><dd>${e(report.reason)}</dd>` : ""}</dl>
    </details>`;
  }

  function sync(workspace, runs, deps) {
    const panel = deps.element("workspaceRunReportPanel");
    if (!panel) return;
    const runId = deps.ui.workspaceRunReportSelections?.[workspace?.id];
    const active = Boolean(workspace?.id && runId && deps.ui.workspaceMode === "runs");
    panel.hidden = !active;
    for (const id of ["workspaceRunMeta", "workspaceRunSummary", "workspaceRunList"]) {
      const element = deps.element(id);
      if (element) element.hidden = active;
    }
    if (!active) { deps.ui.workspaceRunReport = null; panel.replaceChildren(); return; }
    const run = runs.find((item) => item.id === runId);
    const step = reportStep(run);
    const sig = signature(step);
    let view = deps.ui.workspaceRunReport;
    if (!view || view.workspaceId !== workspace.id || view.runId !== runId) {
      view = { workspaceId: workspace.id, runId, run, step, signature: sig, phase: "loading", report: null, request: 0, error: "" };
      deps.ui.workspaceRunReport = view;
      Promise.resolve().then(() => load(view, deps));
    } else if (view.signature !== sig) {
      view.request += 1; // Invalidate any response from an earlier attempt/file snapshot.
      view.signature = sig;
      view.report = null;
      view.error = "";
      view.phase = "loaded";
      if (fileFor(step)?.file_verified) {
        view.phase = "loading";
        Promise.resolve().then(() => load(view, deps));
      }
    }
    view.run = run;
    view.step = step;
    const detailsOpen = Boolean(panel.querySelector("details[open]"));
    const markup = panelMarkup(view, workspace, deps, false);
    if (view.markup !== markup) {
      const active = panel.contains(document.activeElement) ? document.activeElement : null;
      const focused = active?.dataset.action;
      const focusedId = active?.id;
      const focusedSummary = active?.tagName === "SUMMARY";
      panel.innerHTML = panelMarkup(view, workspace, deps, detailsOpen);
      view.markup = markup;
      if (focused) panel.querySelector(`[data-action='${focused}']`)?.focus({ preventScroll: true });
      else if (focusedId) deps.element(focusedId)?.focus({ preventScroll: true });
      else if (focusedSummary) panel.querySelector("summary")?.focus({ preventScroll: true });
    }
  }

  function handleClick(event, deps) {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (!["open-workspace-report", "close-workspace-report", "refresh-workspace-report"].includes(action)) return false;
    deps.consumeClick(event);
    if (action === "open-workspace-report") open(event.target.closest("[data-run-id]").dataset.runId, deps);
    else if (action === "close-workspace-report") close(deps);
    else if (deps.ui.workspaceRunReport?.phase !== "loading") void load(deps.ui.workspaceRunReport, deps);
    return true;
  }

  window.WorkspaceRunReport = { entryMarkup, handleClick, open, close, sync, statusInfo };
})();
