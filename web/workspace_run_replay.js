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

  function escapeFor(deps, value) {
    return (typeof deps.escapeHtml === "function" ? deps.escapeHtml : fallbackEscapeHtml)(value);
  }

  function compactFor(deps, value, limit = 80) {
    if (typeof deps.compactText === "function") return deps.compactText(value, limit);
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > limit ? `${text.slice(0, Math.max(0, limit - 1))}...` : text;
  }

  function dateFor(deps, value) {
    return typeof deps.fmtDate === "function" ? deps.fmtDate(value) : String(value || "");
  }

  function statusFor(deps, value) {
    return typeof deps.zhStatus === "function" ? deps.zhStatus(value) : String(value || "");
  }

  function workspaceStatusFor(deps, value) {
    return typeof deps.workspaceStatusLabel === "function" ? deps.workspaceStatusLabel(value) : String(value || "");
  }

  function eventLabelFor(deps, type) {
    return typeof deps.workspaceRunEventLabel === "function" ? deps.workspaceRunEventLabel(type) : String(type || "事件");
  }

  function eventDetailFor(deps, event) {
    return typeof deps.workspaceRunEventDetail === "function" ? deps.workspaceRunEventDetail(event) : "";
  }

  function timeline(replay = {}) {
    const rootRun = replay.run && typeof replay.run === "object" ? replay.run : {};
    const rootRunId = String(rootRun.id || "").trim();
    const rootItems = (Array.isArray(replay.timeline) ? replay.timeline : [])
      .filter((item) => item && typeof item === "object")
      .map((item) => ({ ...item, replay_run_id: String(item.run_id || rootRunId).trim(), linked: false }));
    const linkedItems = (Array.isArray(replay.linked_runs) ? replay.linked_runs : [])
      .filter((item) => item && typeof item === "object")
      .flatMap((item) => {
        const linkedRun = item.run && typeof item.run === "object" ? item.run : {};
        const linkedRunId = String(linkedRun.id || "").trim();
        return (Array.isArray(item.timeline) ? item.timeline : [])
          .filter((step) => step && typeof step === "object")
          .map((step) => ({ ...step, replay_run_id: String(step.run_id || linkedRunId).trim(), linked: true }));
      });
    return [...rootItems, ...linkedItems];
  }

  function countSummary(replay = {}) {
    const rootRun = replay.run && typeof replay.run === "object" ? replay.run : {};
    const replayTimeline = timeline(replay);
    const linkedRuns = Array.isArray(replay.linked_runs) ? replay.linked_runs.filter((item) => item && typeof item === "object") : [];
    const linkedJobs = Array.isArray(replay.linked_jobs) ? replay.linked_jobs.filter((item) => item && typeof item === "object") : [];
    const events = Array.isArray(replay.event_timeline) ? replay.event_timeline.filter((item) => item && typeof item === "object") : [];
    const delta = replay.delta_evidence && typeof replay.delta_evidence === "object" ? replay.delta_evidence : {};
    return {
      stepCount: replayTimeline.length,
      linkedRunCount: linkedRuns.length,
      linkedJobCount: linkedJobs.length,
      eventCount: Number(rootRun.event_count || events.length || 0),
      deltaCount: Number(rootRun.delta_evidence_count || delta.total_events || 0),
    };
  }

  function stepLine(step = {}, deps = {}) {
    const title = String(step.node_title || step.node_kind || "步骤").trim();
    const bits = [
      step.linked ? `子运行 ${String(step.replay_run_id || step.run_id || "").trim()}` : "",
      String(step.executor || "").trim(),
      String(step.job_id || "").trim() ? `job ${step.job_id}` : "",
      String(step.agent_execution_id || "").trim() ? `agent ${step.agent_execution_id}` : "",
      String(step.output_key || "").trim(),
    ].filter(Boolean);
    const error = String(step.error || "").trim();
    return {
      title: `${Number(step.index || 0) + 1}. ${title}`,
      meta: compactFor(deps, bits.join(" · "), 150),
      status: String(step.status || "pending").trim(),
      error: compactFor(deps, error, 180),
    };
  }

  function previewMarkup(options = {}) {
    const deps = {
      escapeHtml: options.escapeHtml,
      fmtDate: options.fmtDate,
      zhStatus: options.zhStatus,
      workspaceStatusLabel: options.workspaceStatusLabel,
      workspaceRunEventLabel: options.workspaceRunEventLabel,
      workspaceRunEventDetail: options.workspaceRunEventDetail,
      compactText: options.compactText,
    };
    const run = options.run && typeof options.run === "object" ? options.run : {};
    const replayState = options.replayState && typeof options.replayState === "object" ? options.replayState : {};
    if (!replayState.open) return "";
    if (replayState.busy && !replayState.replay) {
      return `
        <div class="workspace-run-replay-preview loading">
          <div class="workspace-run-replay-head">
            <strong>回放预览</strong>
            <span>正在读取结构化回放...</span>
          </div>
        </div>
      `;
    }
    if (replayState.error && !replayState.replay) {
      return `
        <div class="workspace-run-replay-preview status-failed">
          <div class="workspace-run-replay-head">
            <strong>回放预览</strong>
            <span>${escapeFor(deps, replayState.error)}</span>
          </div>
        </div>
      `;
    }
    const replay = replayState.replay && typeof replayState.replay === "object" ? replayState.replay : null;
    if (!replay) {
      return `
        <div class="workspace-run-replay-preview">
          <div class="workspace-run-replay-head">
            <strong>回放预览</strong>
            <span>等待加载</span>
          </div>
        </div>
      `;
    }
    const summary = countSummary(replay);
    const rootRun = replay.run && typeof replay.run === "object" ? replay.run : {};
    const delivery = replay.delivery_closure && typeof replay.delivery_closure === "object" ? replay.delivery_closure : {};
    const closure = replay.linked_run_closure && typeof replay.linked_run_closure === "object" ? replay.linked_run_closure : {};
    const replayTimeline = timeline(replay);
    const highlightedSteps = replayTimeline.filter((step) => {
      const stepStatus = String(step.status || "").trim();
      return step.linked
        || ["failed", "blocked", "stopped"].includes(stepStatus)
        || Number(step.child_job_ref_count || 0) > 0
        || Number(step.child_run_ref_count || 0) > 0;
    });
    const visibleSteps = highlightedSteps.slice(0, 4).map((step) => stepLine(step, deps));
    const linkedJobs = (Array.isArray(replay.linked_jobs) ? replay.linked_jobs : [])
      .filter((item) => item && typeof item === "object")
      .slice(0, 4);
    const visibleEvents = (Array.isArray(replay.event_timeline) ? replay.event_timeline : [])
      .filter((item) => item && typeof item === "object")
      .slice(-3)
      .reverse();
    const deliveryStatus = String(delivery.status || "").trim();
    const packageId = String(rootRun.package_id || "").trim();
    const closureIssue = closure.truncated
      ? `子运行截断 ${Number(closure.included_count || 0)}/${Number(closure.included_count || 0) + Number(closure.pending_count || 0) + Number(closure.missing_count || 0)}`
      : "";
    return `
      <div class="workspace-run-replay-preview status-${escapeFor(deps, rootRun.status || run.status || "pending")}">
        <div class="workspace-run-replay-head">
          <div>
            <strong>回放预览</strong>
            <span>${escapeFor(deps, [replay.schema || "relaygraph.run.replay.v1", dateFor(deps, replay.exported_at || "")].filter(Boolean).join(" · "))}</span>
          </div>
          <em>${escapeFor(deps, [packageId ? `pkg ${packageId}` : "", deliveryStatus ? `交付 ${workspaceStatusFor(deps, deliveryStatus)}` : "", closureIssue].filter(Boolean).join(" · ") || "结构化执行证据")}</em>
        </div>
        <div class="workspace-run-replay-stats">
          <span><strong>${summary.stepCount}</strong>步骤</span>
          <span><strong>${summary.eventCount}</strong>事件</span>
          <span><strong>${summary.linkedJobCount}</strong>Job</span>
          <span><strong>${summary.linkedRunCount}</strong>子运行</span>
          <span><strong>${summary.deltaCount}</strong>实时增量</span>
        </div>
        ${visibleSteps.length ? `
          <ol class="workspace-run-replay-steps">
            ${visibleSteps.map((item) => `
              <li class="status-${escapeFor(deps, item.status || "pending")}">
                <strong>${escapeFor(deps, item.title)}</strong>
                ${item.status ? `<span>${escapeFor(deps, statusFor(deps, item.status))}</span>` : ""}
                ${item.meta ? `<em title="${escapeFor(deps, item.meta)}">${escapeFor(deps, item.meta)}</em>` : ""}
                ${item.error ? `<p title="${escapeFor(deps, item.error)}">${escapeFor(deps, item.error)}</p>` : ""}
              </li>
            `).join("")}
          </ol>
        ` : ""}
        ${linkedJobs.length ? `
          <div class="workspace-run-replay-events">
            ${linkedJobs.map((job) => {
              const statusText = job.status ? statusFor(deps, job.status) : "未知状态";
              const serverText = job.server_id ? ` · ${job.server_id}` : "";
              return `<span title="${escapeFor(deps, job.command || job.error || job.id || "")}">${escapeFor(deps, `Job ${job.id || "-"} · ${statusText}${serverText}`)}</span>`;
            }).join("")}
          </div>
        ` : ""}
        ${visibleEvents.length ? `
          <div class="workspace-run-replay-events">
            ${visibleEvents.map((event) => {
              const label = eventLabelFor(deps, event.type || "");
              const detail = eventDetailFor(deps, event);
              return `<span title="${escapeFor(deps, detail || label)}">${escapeFor(deps, label)}${detail ? ` · ${compactFor(deps, detail, 70)}` : ""}</span>`;
            }).join("")}
          </div>
        ` : ""}
      </div>
    `;
  }

  window.WorkspaceRunReplay = {
    countSummary,
    previewMarkup,
    stepLine,
    timeline,
  };
})();
