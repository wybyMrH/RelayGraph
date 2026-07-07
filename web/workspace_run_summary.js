(function () {
  "use strict";

  function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function escapeFor(deps, value) {
    return fn(deps, "escapeHtml", fallbackEscapeHtml)(value);
  }

  function statusFor(deps, value) {
    return fn(deps, "zhStatus", (status) => status)(value);
  }

  function dateFor(deps, value) {
    return fn(deps, "fmtDate", (date) => String(date || ""))(value);
  }

  function compactFor(deps, value, limit) {
    return fn(deps, "compactText", (text) => String(text || ""))(value, limit);
  }

  function kindLabel(kind = "") {
    const labels = {
      discovery: "安全发现",
      reproduction: "完整复现",
      node: "单节点",
      agent_debug: "Agent 调试",
      advance: "自动推进",
    };
    return labels[String(kind || "").trim()] || String(kind || "运行");
  }

  function progressMarkup(run, options = {}, deps = {}) {
    if (!run) return "";
    const progress = run.progress && typeof run.progress === "object" ? run.progress : {};
    const total = Number(progress.total) || (Array.isArray(run.steps) ? run.steps.length : 0);
    const done = Number(progress.done) || 0;
    const percent = Number(progress.percent) || (total ? Math.round((done / total) * 100) : 0);
    const compact = Boolean(options.compact);
    return `
    <div class="workspace-execution-run-progress status-${escapeFor(deps, run.status || "pending")}${compact ? " compact" : ""}">
      <div class="workspace-execution-run-progress-head">
        <span>${escapeFor(deps, kindLabel(run.kind))}</span>
        <strong>${escapeFor(deps, `${done}/${total} 步 · ${percent}%`)}</strong>
        <em>${escapeFor(deps, run.summary || "")}</em>
      </div>
      <div class="workspace-execution-run-progress-bar" role="progressbar" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100">
        <span style="width:${Math.max(0, Math.min(100, percent))}%"></span>
      </div>
    </div>
  `;
  }

  function eventLabel(type = "") {
    const map = {
      "run.created": "运行创建",
      "run.updated": "运行更新",
      "run.step.updated": "步骤更新",
      "job.updated": "任务更新",
      "agent.step.created": "Agent 步骤",
      "agent.tool.called": "调用工具",
      "agent.tool.result": "工具结果",
      "agent.tool.failed": "工具失败",
      "agent.completed": "Agent 完成",
      "agent.failed": "Agent 失败",
    };
    return map[String(type || "").trim()] || String(type || "事件").trim();
  }

  function eventStatus(event = {}) {
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    const step = payload.step && typeof payload.step === "object" ? payload.step : {};
    const job = payload.job && typeof payload.job === "object" ? payload.job : {};
    const run = payload.run && typeof payload.run === "object" ? payload.run : {};
    const execution = payload.execution && typeof payload.execution === "object" ? payload.execution : {};
    if (execution.error) return "failed";
    if (execution.success) return "done";
    return String(
      step.status
        || job.status
        || run.status
        || "",
    ).trim();
  }

  function eventDetail(event = {}, deps = {}) {
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    const step = payload.step && typeof payload.step === "object" ? payload.step : {};
    const job = payload.job && typeof payload.job === "object" ? payload.job : {};
    const run = payload.run && typeof payload.run === "object" ? payload.run : {};
    const execution = payload.execution && typeof payload.execution === "object" ? payload.execution : {};
    const parts = [];
    if (step.node_title || step.node_kind) {
      parts.push(`${Number(step.index || 0) + 1}. ${step.node_title || fn(deps, "workspaceCockpitStageLabel", (value) => value)(step.node_kind)}`);
    }
    if (payload.tool_id) parts.push(`工具 ${payload.tool_id}`);
    const toolSummary = String(payload.observation_summary || payload.arguments_summary || "").trim();
    if (toolSummary) parts.push(toolSummary);
    if (job.id || event.job_id) parts.push(`任务 ${job.id || event.job_id}`);
    if (execution.id || event.agent_execution_id) parts.push(`Agent ${execution.id || event.agent_execution_id}`);
    if (run.summary) parts.push(run.summary);
    const error = String(step.error || job.error || execution.error || "").trim();
    if (error) parts.push(error);
    return compactFor(deps, parts.filter(Boolean).join(" · "), 150);
  }

  function eventTimelineMarkup(run = {}, limit = 6, deps = {}) {
    const events = (Array.isArray(run.events) ? run.events : []).filter((item) => item && typeof item === "object");
    if (!events.length) return "";
    const total = events.length;
    const visible = events.slice(-Math.max(Number(limit) || 6, 1)).reverse();
    return `
    <div class="workspace-run-event-timeline" aria-label="最近执行事件">
      <div class="workspace-run-event-timeline-head">
        <strong>最近事件</strong>
        <span>${escapeFor(deps, `${total} 条`)}</span>
      </div>
      <ol>
        ${visible.map((event) => {
          const type = String(event.type || "").trim();
          const status = eventStatus(event);
          const detail = eventDetail(event, deps);
          return `
            <li class="workspace-run-event status-${escapeFor(deps, status || "info")}">
              <span>${escapeFor(deps, dateFor(deps, event.created_at || ""))}</span>
              <strong>${escapeFor(deps, eventLabel(type))}</strong>
              ${status ? `<em>${escapeFor(deps, statusFor(deps, status))}</em>` : ""}
              ${detail ? `<p title="${escapeFor(deps, detail)}">${escapeFor(deps, detail)}</p>` : ""}
            </li>
          `;
        }).join("")}
      </ol>
    </div>
  `;
  }

  function evidenceNoticeMarkup(run = {}, deps = {}) {
    const steps = Array.isArray(run.steps) ? run.steps.filter((step) => step && typeof step === "object") : [];
    if (!steps.length) return "";
    const childRefSteps = steps.filter((step) => step.child_job_ids_truncated || step.child_run_ids_truncated);
    const childJobTotal = steps.reduce((sum, step) => sum + Number(step.child_job_ref_count || 0), 0);
    const childRunTotal = steps.reduce((sum, step) => sum + Number(step.child_run_ref_count || 0), 0);
    const visibleChildJobs = steps.reduce((sum, step) => sum + (Array.isArray(step.child_job_ids) ? step.child_job_ids.length : 0), 0);
    const visibleChildRuns = steps.reduce((sum, step) => sum + (Array.isArray(step.child_run_ids) ? step.child_run_ids.length : 0), 0);
    const jobRefs = steps.reduce((sum, step) => sum + (String(step.job_id || "").trim() ? 1 : 0), 0);
    const childSummary = childRefSteps.length
      ? `子引用已截断：${visibleChildJobs + visibleChildRuns}/${childJobTotal + childRunTotal || visibleChildJobs + visibleChildRuns}`
      : "";
    const logSummary = childRefSteps.length && (jobRefs || visibleChildJobs) ? "导出日志为有界尾部" : "";
    const exportSummary = childRefSteps.length ? "导出含 manifest/readme 说明证据范围" : "";
    const parts = [childSummary, logSummary, exportSummary].filter(Boolean);
    if (!parts.length) return "";
    return `
    <div class="workspace-run-evidence-notice" title="${escapeFor(deps, parts.join(" · "))}">
      <span>证据范围</span>
      <em>${escapeFor(deps, parts.join(" · "))}</em>
    </div>
  `;
  }

  function deliveryClosureMarkup(delivery = {}, deps = {}) {
    const status = String(delivery.status || "draft");
    const observed = Number(delivery.observed_count || 0);
    const found = Number(delivery.found_count || 0);
    const metricCount = delivery.metrics && typeof delivery.metrics === "object" ? Object.keys(delivery.metrics).length : 0;
    const missing = Array.isArray(delivery.missing_expected) ? delivery.missing_expected.length : 0;
    const report = delivery.report && typeof delivery.report === "object" ? delivery.report : {};
    const reportArtifacts = Array.isArray(report.artifacts) ? report.artifacts.filter((item) => item && typeof item === "object") : [];
    const reportStatus = String(report.status || "draft");
    const text = [
      `${found}/${observed || found} 产物`,
      `${metricCount} 指标`,
      reportStatus === "ready" ? "报告就绪" : "报告待整理",
      missing ? `${missing} 预期未见` : "",
    ].filter(Boolean).join(" · ");
    const reportMarkup = reportArtifacts.length ? `
    <div class="workspace-run-report-artifacts">
      ${reportArtifacts.slice(0, 3).map((artifact) => {
        const path = String(artifact.resolved_path || artifact.path || "").trim();
        const summary = String(artifact.summary || artifact.content || "").trim();
        const title = [artifact.label || "报告", path, summary].filter(Boolean).join(" · ");
        return `
          <article title="${escapeFor(deps, title)}">
            <strong>${escapeFor(deps, artifact.label || "报告")}</strong>
            ${path ? `<span>${escapeFor(deps, path)}</span>` : ""}
            ${summary ? `<em>${escapeFor(deps, compactFor(deps, summary, 160))}</em>` : ""}
          </article>
        `;
      }).join("")}
    </div>
  ` : "";
    return `
    <div class="workspace-run-delivery-closure status-${escapeFor(deps, status)}" title="${escapeFor(deps, text)}">
      <span>交付闭环</span>
      <strong>${escapeFor(deps, fn(deps, "workspaceStatusLabel", (value) => value)(status))}</strong>
      <em>${escapeFor(deps, text || "等待产物、指标和报告")}</em>
      ${reportMarkup}
    </div>
  `;
  }

  window.WorkspaceRunSummary = {
    deliveryClosureMarkup,
    eventDetail,
    eventLabel,
    eventStatus,
    eventTimelineMarkup,
    evidenceNoticeMarkup,
    kindLabel,
    progressMarkup,
  };
})();
