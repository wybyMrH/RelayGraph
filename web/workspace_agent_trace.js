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

  function compactFor(deps, value, limit) {
    return fn(deps, "compactText", (text, max) => {
      const clean = String(text || "").replace(/\s+/g, " ").trim();
      return clean.length > max ? `${clean.slice(0, Math.max(0, max - 1))}…` : clean;
    })(value, limit);
  }

  function statusFor(deps, value) {
    return fn(deps, "zhStatus", (status) => status)(value);
  }

  function eventLabel(eventType = "") {
    const map = {
      "agent.thought.delta": "推理",
      "agent.tool.called": "调用工具",
      "agent.tool.result": "工具结果",
      "agent.tool.failed": "工具失败",
      "agent.answer.delta": "回答",
      "agent.message.delta": "输出",
      "agent.step.created": "步骤",
    };
    return map[String(eventType || "").trim()] || "事件";
  }

  function normalizeEventFromPayload(eventType = "", payload = {}) {
    const source = payload && typeof payload === "object" ? payload : {};
    const type = String(source.type || eventType || "").trim();
    if (!type.startsWith("agent.")) return null;
    const event = {
      type,
      at: String(source.at || "").trim(),
      step_number: source.step_number,
      tool_id: String(source.tool_id || "").trim(),
      arguments_summary: String(source.arguments_summary || "").trim(),
      observation_summary: String(source.observation_summary || "").trim(),
      delta: String(source.delta || "").trim(),
      accumulated: String(source.accumulated || "").trim(),
      status: String(source.status || "").trim(),
      side_effect: String(source.side_effect || "").trim(),
      error: String(source.error || "").trim(),
      job_id: String(source.job_id || "").trim(),
      run_id: String(source.run_id || "").trim(),
      runtime_control: String(source.runtime_control || "").trim(),
      runtime_side_effect: String(source.runtime_side_effect || "").trim(),
      runtime_status: String(source.runtime_status || "").trim(),
    };
    if (source.controlled !== undefined) event.controlled = Boolean(source.controlled);
    return event;
  }

  function mergeEvents(existing = [], incoming = []) {
    const merged = (Array.isArray(existing) ? existing : []).slice();
    const append = (candidate) => {
      const event = candidate && typeof candidate === "object" ? candidate : null;
      if (!event?.type) return;
      const key = [
        event.type,
        event.step_number ?? "",
        event.tool_id || "",
        event.at || "",
        event.accumulated || event.observation_summary || event.arguments_summary || "",
      ].join("|");
      const index = merged.findIndex((item) => {
        const itemKey = [
          item?.type || "",
          item?.step_number ?? "",
          item?.tool_id || "",
          item?.at || "",
          item?.accumulated || item?.observation_summary || item?.arguments_summary || "",
        ].join("|");
        return itemKey === key;
      });
      if (index >= 0) merged.splice(index, 1, { ...merged[index], ...event });
      else merged.push(event);
    };
    (Array.isArray(incoming) ? incoming : []).forEach((item) => append(item));
    return merged.slice(-48);
  }

  function eventDetail(event = {}, deps = {}) {
    const type = String(event.type || "").trim();
    if (type === "agent.tool.called") {
      return String(event.arguments_summary || event.tool_id || "").trim();
    }
    if (type === "agent.tool.result" || type === "agent.tool.failed") {
      const runtimeParts = [
        event.job_id ? `任务 ${String(event.job_id).slice(0, 8)}` : "",
        event.run_id ? `运行 ${String(event.run_id).slice(0, 8)}` : "",
        event.runtime_status ? statusFor(deps, event.runtime_status) : "",
        event.runtime_control || "",
      ].filter(Boolean);
      const detail = String(event.observation_summary || event.error || "").trim();
      return [runtimeParts.join(" · "), detail].filter(Boolean).join(" · ");
    }
    if (type === "agent.answer.delta" || type === "agent.thought.delta" || type === "agent.message.delta") {
      return String(event.accumulated || event.delta || "").trim();
    }
    return String(event.error || event.observation_summary || event.arguments_summary || "").trim();
  }

  function fineTraceMarkup(traceEvents = [], options = {}, deps = {}) {
    const events = (Array.isArray(traceEvents) ? traceEvents : []).filter((item) => item && typeof item === "object");
    if (!events.length) return "";
    const limit = Number(options.limit) || 8;
    const compact = Boolean(options.compact);
    const items = events.slice(-limit).map((event) => {
      const type = String(event.type || "").trim();
      const label = eventLabel(type);
      const detail = compactFor(deps, eventDetail(event, deps), compact ? 72 : 160);
      const status = type === "agent.tool.failed" ? "failed" : type === "agent.tool.result" ? "ok" : "info";
      const badge = event.side_effect ? fn(deps, "workspaceToolPolicyBadge", () => "")(event.side_effect, event.controlled) : "";
      const toolId = String(event.tool_id || "").trim();
      const title = [label, toolId, detail].filter(Boolean).join(" · ");
      return `
      <li class="workspace-agent-fine-trace-item status-${escapeFor(deps, status)}" title="${escapeFor(deps, title)}">
        <span class="workspace-agent-fine-trace-type">${escapeFor(deps, label)}</span>
        ${toolId ? `<strong>${escapeFor(deps, toolId)}</strong>` : ""}
        ${badge}
        ${detail ? `<em>${escapeFor(deps, detail)}</em>` : ""}
      </li>
    `;
    }).join("");
    const more = events.length > limit ? `<li class="muted"><em>还有 ${events.length - limit} 条 trace</em></li>` : "";
    return `<ol class="workspace-agent-fine-trace${compact ? " compact" : ""}">${items}${more}</ol>`;
  }

  function stepTraceMarkup(agentSteps = [], options = {}, deps = {}) {
    const steps = (Array.isArray(agentSteps) ? agentSteps : []).filter((item) => item && typeof item === "object");
    if (!steps.length) return "";
    const limit = Number(options.limit) || 4;
    const compact = Boolean(options.compact);
    const items = steps.slice(0, limit).map((item) => {
      const action = String(item.action || "").trim();
      const thought = compactFor(deps, String(item.thought || "").trim(), compact ? 48 : 120);
      const runtimeParts = [
        item.job_id ? `任务 ${String(item.job_id).slice(0, 8)}` : "",
        item.run_id ? `运行 ${String(item.run_id).slice(0, 8)}` : "",
        item.runtime_status ? statusFor(deps, item.runtime_status) : "",
        item.runtime_control || "",
      ].filter(Boolean);
      const observationText = [
        runtimeParts.join(" · "),
        String(item.observation || item.observation_summary || item.error || "").trim(),
      ].filter(Boolean).join(" · ");
      const observation = compactFor(deps, observationText, compact ? 56 : 140);
      const label = action || thought || "推理步";
      const detail = action ? observation : thought;
      const badge = action ? fn(deps, "workspaceToolPolicyBadge", () => "")(item.side_effect, item.controlled) : "";
      return `<li title="${escapeFor(deps, `${label}${detail ? ` · ${detail}` : ""}`)}"><strong>${escapeFor(deps, label)}</strong>${badge}${detail ? `<em>${escapeFor(deps, detail)}</em>` : ""}</li>`;
    }).join("");
    const more = steps.length > limit ? `<li class="muted"><em>还有 ${steps.length - limit} 步</em></li>` : "";
    return `<ol class="workspace-agent-step-trace${compact ? " compact" : ""}">${items}${more}</ol>`;
  }

  function streamTraceMarkup(records = [], deps = {}) {
    const items = (Array.isArray(records) ? records : []).filter((item) => item && typeof item === "object");
    if (!items.length) return "";
    return `
    <div class="workspace-agent-live-trace">
      ${items.slice(0, 2).map((record) => {
        const steps = Array.isArray(record.steps) ? record.steps : [];
        const recentSteps = steps.slice(-3);
        const status = String(record.status || "running").trim();
        const summary = String(record.error || record.final_answer || record.partial_answer || "").trim();
        const stepCount = Number(record.total_steps) || steps.length;
        const title = record.chat ? "对话执行" : record.node_kind ? fn(deps, "workspaceCockpitStageLabel", (value) => value)(record.node_kind) : "Agent 执行";
        const meta = [
          statusFor(deps, status),
          stepCount ? `${stepCount} step` : "",
          fn(deps, "fmtDate", (value) => String(value || ""))(record.updated_at || ""),
        ].filter(Boolean).join(" · ");
        return `
          <div class="workspace-agent-live-trace-item status-${escapeFor(deps, status)}">
            <div class="workspace-agent-live-trace-head">
              <strong>${escapeFor(deps, title)}</strong>
              <span class="state ${escapeFor(deps, status)}">${escapeFor(deps, statusFor(deps, status))}</span>
            </div>
        ${meta ? `<em>${escapeFor(deps, meta)}</em>` : ""}
        ${fineTraceMarkup(record.trace_events || [], { compact: true, limit: 6 }, deps)}
        ${!Array.isArray(record.trace_events) || !record.trace_events.length ? stepTraceMarkup(recentSteps, { compact: true, limit: 3 }, deps) : ""}
        ${summary ? `<p title="${escapeFor(deps, summary)}">${escapeFor(deps, compactFor(deps, summary, 120))}</p>` : ""}
          </div>
        `;
      }).join("")}
    </div>
  `;
  }

  window.WorkspaceAgentTrace = {
    eventDetail,
    eventLabel,
    fineTraceMarkup,
    mergeEvents,
    normalizeEventFromPayload,
    stepTraceMarkup,
    streamTraceMarkup,
  };
})();
