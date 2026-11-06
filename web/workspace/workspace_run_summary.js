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

  function mappedInputsCompactLine(mappedInputs = [], limit = 3) {
    const items = (Array.isArray(mappedInputs) ? mappedInputs : []).filter((item) => item && typeof item === "object");
    if (!items.length) return "";
    return items.slice(0, limit).map((item) => {
      const name = String(item.name || "input").trim();
      const preview = String(item.preview || "—").trim();
      const missing = String(item.present || "") === "false";
      return `${name}: ${preview}${missing ? " (缺)" : ""}`;
    }).join(" · ");
  }

  function agentRunCompactMarkup(bundle, deps = {}) {
    const step = bundle?.step;
    if (!step || String(step.executor || "") !== "agent") return "";
    const mappedLine = mappedInputsCompactLine(step.mapped_inputs || []);
    const outputKey = String(step.output_key || "").trim();
    const artifactCount = Number(step.artifact_count) || 0;
    const childJobIds = (Array.isArray(step.child_job_ids) ? step.child_job_ids : [])
      .map((item) => String(item || "").trim())
      .filter(Boolean);
    const childRunIds = (Array.isArray(step.child_run_ids) ? step.child_run_ids : [])
      .map((item) => String(item || "").trim())
      .filter(Boolean);
    const runtimeStatus = String(step.runtime_status || "").trim();
    const parts = [];
    if (mappedLine) parts.push(`解析输入 ${mappedLine}`);
    if (outputKey) parts.push(`写出 ${outputKey}${artifactCount ? ` (${artifactCount} 产物)` : ""}`);
    if (childJobIds.length) parts.push(`子任务 ${childJobIds[0].slice(0, 8)}${childJobIds.length > 1 ? ` +${childJobIds.length - 1}` : ""}`);
    if (childRunIds.length) parts.push(`子运行 ${childRunIds[0].slice(0, 8)}${childRunIds.length > 1 ? ` +${childRunIds.length - 1}` : ""}`);
    if (runtimeStatus) parts.push(`runtime ${statusFor(deps, runtimeStatus)}`);
    if (!parts.length) return "";
    const text = parts.join(" · ");
    return `<p class="workspace-agent-run-compact muted" title="${escapeFor(deps, text)}">${escapeFor(deps, text)}</p>`;
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
    const managedReports = reportArtifacts.filter((artifact) => artifact.report_id);
    const reportLabel = managedReports.length
      ? (managedReports.every((artifact) => artifact.file_verified) && !report.incomplete ? "报告文件已核对" : "报告交付不完整")
      : reportStatus === "ready" ? "报告就绪" : "报告待整理";
    const legacyReports = reportArtifacts.filter((artifact) => !artifact.report_id);
    const text = [
      `${found}/${observed || found} 产物`,
      `${metricCount} 指标`,
      reportLabel,
      missing ? `${missing} 预期未见` : "",
    ].filter(Boolean).join(" · ");
    const reportMarkup = legacyReports.length ? `
    <div class="workspace-run-report-artifacts">
      ${legacyReports.slice(0, 3).map((artifact) => {
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

  function childSubmissionPresentation(step = {}, run = {}, deps = {}) {
    // Wording only: the backend owns liveness, receipts and progression.
    const parent = run.execution_plan?.steps?.[0];
    if (run.execution_plan?.engine_version !== "langgraph-agent-child-job/n04"
        || !run.id || step.index !== 0 || step.executor !== "agent"
        || parent?.index !== 0 || parent.executor !== "agent" || !parent.step_id
        || (step.step_id || step.node_id) !== parent.step_id
        || (step.node_id && step.node_id !== parent.step_id)) return null;
    const ids = [step.job_id, ...(Array.isArray(step.child_job_ids) ? step.child_job_ids : [])].filter(Boolean);
    let label, description, kind;
    if (step.status === "running" && step.runtime_status === "submitting" && !ids.length) {
      label = "提交中";
      description = "正在提交本次子任务，尚未取得任务回执。提交成功后仍需等待任务执行完成。";
      kind = "submitting";
    } else if (step.status === "waiting" && step.runtime_status === "waiting_child" && ids.length) {
      label = "等待子任务";
      description = "已取得子任务回执，正在等待任务结果与后续交接；提交成功不代表执行完成。";
      kind = "waiting";
    } else if (step.status === "blocked" && step.runtime_status === "reconciling") {
      label = "提交结果需核对";
      description = "暂时无法确认本次子任务的提交结果。系统不会自动重新提交；请核对任务记录、后续步骤与下方错误。";
      kind = "unknown";
    } else return null;
    return { label, markup: `<p class="workspace-child-submission is-${kind}">${escapeFor(deps, description)}</p>` };
  }

  function continuationContext(run = {}) {
    if (run.execution_plan?.engine_version !== "langgraph-agent-child-job/n04" || !run.id || !run.workspace_id) return null;
    const parent = (Array.isArray(run.steps) ? run.steps : []).find((step) => Number(step.index) === 0);
    if (!parent || !parent.attempt_id || !/^a[1-9]\d*$/.test(parent.attempt_id)) return null;
    const stepId = parent.step_id || parent.node_id;
    if (!stepId || (parent.step_id && parent.node_id && parent.step_id !== parent.node_id)) return null;
    const ids = [...new Set([parent.job_id, ...(Array.isArray(parent.child_job_ids) ? parent.child_job_ids : [])].filter(Boolean))];
    if (ids.length !== 1) return null;
    const marker = run.continuation_stop || {};
    const stopped = parent.status === "stopped" && marker.status === "stopped"
      && marker.run_id === run.id && marker.step_id === stepId && marker.attempt_id === parent.attempt_id
      && marker.child_job_id === ids[0] && marker.child_policy === "keep_running" && Boolean(marker.stopped_at);
    const canStop = !Object.keys(marker).length && run.status === "waiting" && parent.status === "waiting"
      && parent.runtime_status === "waiting_child" && Array.isArray(run.attempts) && run.attempts.length === 1
      && run.attempts[0].step_id === stepId && run.attempts[0].attempt_id === parent.attempt_id;
    return { workspaceId: run.workspace_id, runId: run.id, stepId, attemptId: parent.attempt_id,
      childJobId: ids[0], key: JSON.stringify([run.workspace_id, run.id, stepId, parent.attempt_id, ids[0]]),
      stopped, canStop, unconfirmedMarker: Boolean(Object.keys(marker).length) && !stopped };
  }

  function continuationControlMarkup(run = {}, deps = {}, control = {}) {
    const context = continuationContext(run);
    if (!context || (!context.canStop && !context.stopped && !context.unconfirmedMarker && !control.message)) return "";
    const busy = ["submitting", "checking"].includes(control.phase);
    const uncertain = ["unknown", "uncertain"].includes(control.phase);
    const attrs = `data-continuation-key="${escapeFor(deps, context.key)}"`;
    const description = context.stopped ? "本次后续 Agent 不会再启动。子任务没有随之停止，其状态在下方独立更新。"
      : context.unconfirmedMarker ? "停止记录与本次运行身份不一致，请重新核对，暂不提供停止操作。"
      : !context.canStop ? "当前记录已不在可停止的等待阶段；请按下方步骤状态核对进度。"
      : "停止后，后续 Agent 不再启动；已提交的子任务继续运行。需要结束子任务时，请单独停止子任务。";
    return `<section class="workspace-continuation-control" ${attrs} tabindex="-1" aria-label="后续流程控制">
      <strong>${context.stopped ? "后续流程已停止" : "后续流程"}</strong>
      <p>${escapeFor(deps, description)}</p>
      ${!context.stopped && control.message ? `<p class="workspace-continuation-feedback ${control.error ? "is-error" : "muted"}" role="status">${escapeFor(deps, control.message)}</p>` : ""}
      ${!context.stopped && !context.unconfirmedMarker && (context.canStop || uncertain) ? `<div class="workspace-execution-run-step-actions">
        ${context.canStop && control.phase !== "unknown" ? `<button type="button" class="secondary mini danger" data-action="stop-run-continuation" ${attrs}${busy ? " disabled" : ""}>${busy ? "正在核对停止结果…" : control.phase === "uncertain" ? "按原身份再次请求停止" : "停止后续流程"}</button>` : ""}
        ${uncertain ? `<button type="button" class="secondary mini" data-action="check-run-continuation" ${attrs}>重新核对结果</button>` : ""}
      </div>` : ""}
    </section>`;
  }

  function actualJobTargetMarkup(job, deps = {}, options = {}) {
    if (!job) return '<p class="workspace-job-target-missing muted">未取得本次子任务记录，无法确认状态与目标；请刷新后核对。</p>';
    const index = String(job.gpu_index ?? "").trim();
    const cpu = ["none", "cpu", "no_gpu"].includes(index.toLowerCase());
    const jobStatus = String(job.status || "unknown");
    const labels = { queued: "排队中", starting: "正在启动", running: "运行中", done: "已完成", failed: "失败", stopped: "已停止", blocked: "需核对" };
    const parentFailed = ["failed", "blocked", "stopped"].includes(options.parentStatus);
    const parentNotice = options.parentStatus === "stopped"
      ? "父步骤已停止；此任务不会因此自动停止或重新提交。"
      : "父步骤的错误会保留；此任务不会因此自动停止或重新提交。";
    const fields = [
      ["主机", job.server_id || "尚未分配"],
      ["计算方式", cpu ? "CPU" : index === "auto" ? "GPU 待分配" : index ? `GPU ${index}` : "尚未取得"],
      ["工作目录", job.cwd || "主机默认目录"],
      ["环境", job.env_name || "主机现有环境（未激活指定环境）"],
    ];
    return `<section class="workspace-job-target" data-child-job-id="${escapeFor(deps, job.id || "")}" tabindex="-1" aria-label="本次任务目标">
      <div class="workspace-job-target-head"><strong>已提交的子任务</strong><span class="state ${escapeFor(deps, jobStatus)}">${escapeFor(deps, labels[jobStatus] || "状态未知")}</span></div>
      ${parentFailed ? `<p>${parentNotice}</p>` : ""}
      <p class="muted">实际执行目标来自本次任务记录。</p>
      ${options.allowChildStop && job.id === options.childJobId && ["queued", "blocked", "starting", "running"].includes(jobStatus) ? `<button type="button" class="secondary mini danger" data-action="stop-workspace-run" data-job-id="${escapeFor(deps, job.id)}">单独停止子任务</button>` : ""}
      <dl>${fields.map(([label, value]) => `<div><dt>${escapeFor(deps, label)}</dt><dd>${escapeFor(deps, value)}</dd></div>`).join("")}</dl>
    </section>`;
  }

  function jobLogHandoffMarkup(step = {}, run = {}, deps = {}, options = {}) {
    const output = step.output_value && typeof step.output_value === "object" ? step.output_value : {};
    const evidence = output.log_evidence && typeof output.log_evidence === "object" ? output.log_evidence : {};
    const notice = (text) => `<section class="workspace-job-handoff"><strong>本次日志交接</strong><p>${escapeFor(deps, text)}</p></section>`;
    if (!evidence.schema) {
      return step.status === "done" ? notice("此记录未登记日志交接完整性，请通过原任务日志核对；不能据此确认后续分析收到的文本。") : "";
    }
    const jobIds = [step.job_id, ...(Array.isArray(step.child_job_ids) ? step.child_job_ids : [])].filter(Boolean);
    const identityMatches = run.id && (step.step_id || step.node_id) && step.attempt_id && output.host_id
      && output.run_id === run.id && output.node_id === (step.step_id || step.node_id)
      && output.attempt_id === step.attempt_id && jobIds.includes(output.job_id) && output.status === "done";
    if (evidence.schema !== "job-log-handoff/v1" || !identityMatches) {
      return notice("交接记录的版本或运行身份无法确认，暂不展示为本次日志；请核对原任务记录。");
    }
    const count = (key) => Number.isSafeInteger(evidence[key]) && evidence[key] >= 0;
    const fullRange = ["offset", "next_offset", "file_size", "byte_count", "skipped_bytes"].every(count)
      && evidence.offset === 0 && evidence.skipped_bytes === 0
      && evidence.next_offset === evidence.file_size && evidence.byte_count === evidence.file_size;
    const complete = evidence.state === "complete" && evidence.complete === true && evidence.exists === true
      && fullRange && output.log_truncated === false && !evidence.delivery_limited
      && !evidence.text_replacement_characters && !evidence.error && typeof output.log === "string";
    const state = complete ? "complete" : evidence.state === "complete" || evidence.complete === true ? "unknown" : String(evidence.state || "unknown");
    const descriptions = {
      complete: ["完整日志", "本次读取覆盖完整日志。"],
      partial: ["部分日志", "本次只交接部分日志，不能当作完整输出。"],
      missing: ["日志缺失", "交接时没有取得日志文件，后续分析缺少这份日志。"],
      error: ["读取失败", "交接时未能完整读取日志，不能据此确认完整输出。"],
      unknown: ["需核对", "交接完整性信息不足或不一致，请核对原任务记录。"],
    };
    const [label, description] = descriptions[state] || descriptions.unknown;
    const range = ["offset", "next_offset", "file_size"].every(count)
      ? `原日志 ${evidence.file_size} 字节，本次读取范围 ${evidence.offset}–${evidence.next_offset}。` : "原日志读取范围未登记。";
    const delivery = count("delivered_byte_count") ? `交接文本 ${evidence.delivered_byte_count} 字节。` : "交接文本字节数未登记。";
    const flags = [evidence.redacted ? "文本已脱敏。" : "", evidence.delivery_limited ? "交接文本因大小限制再次裁短。" : "",
      evidence.text_replacement_characters ? "含无法还原的字符。" : ""].join("");
    const key = `${run.id}:${step.step_id || step.node_id}:${step.attempt_id}:${output.job_id}:job-log`;
    const hasText = ["complete", "partial", "error"].includes(state) && typeof output.log === "string" && output.log.length > 0;
    return `<section class="workspace-job-handoff" aria-label="本次日志交接">
      <div class="workspace-job-target-head"><strong>本次日志交接</strong><span class="state ${complete ? "done" : "blocked"}">${escapeFor(deps, label)}</span></div>
      <p>${escapeFor(deps, description)} 此处是保存给后续分析的证据，不表示后续步骤已经执行。</p>
      <p class="muted">${escapeFor(deps, `${range} ${delivery} ${flags}`)}</p>
      <p class="muted">主机 ${escapeFor(deps, output.host_id)}；“打开日志”查看原任务日志，可能与这份冻结文本不同。</p>
      ${hasText ? `<details class="workspace-run-reader-evidence" data-reader-detail="${escapeFor(deps, key)}"${options.openDetails?.has(key) ? " open" : ""}>
        <summary>查看本次交接文本</summary><pre tabindex="0" class="workspace-job-handoff-text" aria-label="本次交接文本">${escapeFor(deps, output.log)}</pre>
      </details>` : complete ? "<p>日志文件存在，本次完整日志为空。</p>" : "<p>没有可展示的交接文本。</p>"}
    </section>`;
  }

  window.WorkspaceRunSummary = {
    actualJobTargetMarkup,
    childSubmissionPresentation,
    continuationContext,
    continuationControlMarkup,
    jobLogHandoffMarkup,
    agentRunCompactMarkup,
    deliveryClosureMarkup,
    eventDetail,
    eventLabel,
    eventStatus,
    eventTimelineMarkup,
    evidenceNoticeMarkup,
    kindLabel,
    mappedInputsCompactLine,
    progressMarkup,
  };
})();
