(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function appState(deps = {}) {
    const source = typeof deps.state === "function" ? deps.state() : deps.state;
    return source && typeof source === "object" ? source : {};
  }

  function selectedWorkspaceId(deps = {}) {
    const value = typeof deps.selectedWorkspaceId === "function"
      ? deps.selectedWorkspaceId()
      : deps.selectedWorkspaceId;
    return String(value || "").trim();
  }

  function nowIso(deps = {}) {
    return fn(deps, "nowIso", () => new Date().toISOString())();
  }

  function normalizeTraceEvent(deps = {}, eventType = "", payload = {}) {
    return fn(deps, "normalizeAgentTraceEventFromPayload", () => null)(eventType, payload);
  }

  function mergeTraceEvents(deps = {}, existing = [], incoming = []) {
    return fn(deps, "mergeAgentTraceEvents", () => [])(existing, incoming);
  }

  function runIsTerminal(deps = {}, run = {}) {
    return fn(deps, "workspaceRunIsTerminal", () => false)(run);
  }

  function stageLabel(deps = {}, kind = "") {
    return fn(deps, "workspaceCockpitStageLabel", (value) => value)(kind);
  }

  function eventStore(workspaceId, deps = {}) {
    const id = String(workspaceId || "").trim();
    if (!id) return [];
    const state = appState(deps);
    if (!state.ui || typeof state.ui !== "object") state.ui = {};
    if (!state.ui.workspaceAgentEvents || typeof state.ui.workspaceAgentEvents !== "object") {
      state.ui.workspaceAgentEvents = {};
    }
    if (!Array.isArray(state.ui.workspaceAgentEvents[id])) {
      state.ui.workspaceAgentEvents[id] = [];
    }
    return state.ui.workspaceAgentEvents[id];
  }

  function streamRecordId(event = {}, payload = {}, execution = {}, step = {}) {
    const executionId = String(event.agent_execution_id || execution.id || payload.agent_execution_id || "").trim();
    if (executionId) return executionId;
    const eventType = String(event.type || "").trim();
    const runId = String(event.run_id || payload.run_id || execution.run_id || "").trim();
    const nodeId = String(payload.node_id || execution.node_id || step.node_id || "").trim();
    const agentId = String(payload.agent_id || execution.agent_id || "").trim();
    const chatScope = payload.chat ? "chat" : "node";
    if (runId || nodeId || agentId) {
      return [
        "agent-fallback",
        chatScope,
        runId || "no-run",
        nodeId || "no-node",
        agentId || "no-agent",
      ].join(":");
    }
    const sseId = Number(event.id || event.sse_id || 0);
    if (Number.isFinite(sseId) && sseId > 0) return `agent-fallback:sse:${sseId}`;
    return `agent-fallback:${eventType || "event"}:${String(event.created_at || "").trim() || "unknown"}`;
  }

  function mergeStreamEvent(workspaceId, event = {}, payload = {}, deps = {}) {
    const id = String(workspaceId || "").trim();
    const eventType = String(event.type || "").trim();
    if (!id || !eventType.startsWith("agent.")) return null;
    const execution = payload.execution && typeof payload.execution === "object" ? payload.execution : {};
    const step = payload.step && typeof payload.step === "object" ? payload.step : null;
    const recordId = streamRecordId(event, payload, execution, step || {});
    const store = eventStore(id, deps);
    const existingIndex = store.findIndex((item) => String(item?.id || "") === recordId);
    const previous = existingIndex >= 0 ? store[existingIndex] : {};
    const steps = Array.isArray(previous.steps) ? previous.steps.slice() : [];
    const upsertStep = (nextStep) => {
      if (!nextStep || typeof nextStep !== "object") return;
      const stepNumber = String(nextStep.step_number || nextStep.index || "").trim();
      const stepIndex = steps.findIndex((item) => (
        stepNumber && String(item?.step_number || item?.index || "").trim() === stepNumber
      ) || (
        String(item?.timestamp || "") && String(item.timestamp || "") === String(nextStep.timestamp || "")
      ));
      if (stepIndex >= 0) steps.splice(stepIndex, 1, { ...steps[stepIndex], ...nextStep });
      else steps.push(nextStep);
    };
    if (Array.isArray(execution.steps)) {
      execution.steps.forEach((item) => upsertStep(item));
    }
    if (step) upsertStep(step);
    const traceEvent = normalizeTraceEvent(deps, eventType, payload);
    const traceEvents = mergeTraceEvents(
      deps,
      previous.trace_events || [],
      traceEvent ? [traceEvent] : [],
    );
    if (Array.isArray(execution.trace_events)) {
      traceEvents.push(...execution.trace_events.filter((item) => item && typeof item === "object"));
    }
    const normalizedTraceEvents = mergeTraceEvents(deps, [], traceEvents);
    const partialAnswer = eventType === "agent.message.delta" || eventType === "agent.answer.delta"
      ? String(payload.accumulated || payload.text || "").trim()
      : String(previous.partial_answer || "").trim();
    const status = eventType === "agent.failed"
      ? "failed"
      : eventType === "agent.completed"
        ? "completed"
        : previous.status || "running";
    const record = {
      ...previous,
      id: recordId,
      run_id: String(event.run_id || payload.run_id || execution.run_id || previous.run_id || "").trim(),
      agent_id: String(payload.agent_id || execution.agent_id || previous.agent_id || "").trim(),
      node_id: String(payload.node_id || previous.node_id || "").trim(),
      node_kind: String(payload.node_kind || previous.node_kind || "").trim(),
      chat: Boolean(payload.chat || previous.chat),
      status,
      final_answer: String(execution.final_answer || previous.final_answer || "").trim(),
      partial_answer: eventType === "agent.completed" ? "" : partialAnswer,
      error: String(execution.error || previous.error || "").trim(),
      total_steps: Number(execution.total_steps ?? previous.total_steps ?? steps.length) || steps.length,
      steps: steps.slice(-24),
      trace_events: normalizedTraceEvents,
      updated_at: String(event.created_at || nowIso(deps)),
    };
    if (existingIndex >= 0) store.splice(existingIndex, 1, record);
    else store.push(record);
    store.sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
    const state = appState(deps);
    if (!state.ui || typeof state.ui !== "object") state.ui = {};
    if (!state.ui.workspaceAgentEvents || typeof state.ui.workspaceAgentEvents !== "object") {
      state.ui.workspaceAgentEvents = {};
    }
    state.ui.workspaceAgentEvents[id] = store.slice(0, 20);
    return record;
  }

  function streamRecords(workspaceId, agentId = "", deps = {}) {
    const targetAgentId = String(agentId || "").trim();
    return eventStore(workspaceId, deps).slice()
      .filter((item) => !targetAgentId || String(item?.agent_id || "").trim() === targetAgentId)
      .slice(0, 6);
  }

  function liveChatRecord(workspaceId, agentId = "", deps = {}) {
    const targetAgentId = String(agentId || "").trim();
    return eventStore(workspaceId, deps).slice()
      .filter((item) => {
        if (!item || !item.chat || !String(item.partial_answer || "").trim()) return false;
        if (!targetAgentId) return true;
        return String(item.agent_id || "").trim() === targetAgentId;
      })
      .sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")))[0] || null;
  }

  function liveAgentStatus(record = {}) {
    const status = String(record?.status || "").trim();
    if (status === "completed") return "done";
    return status || "running";
  }

  function liveAgentRecordIsActive(record = {}) {
    return ["running", "queued", "starting", "pending"].includes(liveAgentStatus(record));
  }

  function liveAgentRecordFresh(record = {}, maxAgeMs = 30 * 60 * 1000) {
    if (liveAgentRecordIsActive(record)) return true;
    const updatedMs = Date.parse(String(record?.updated_at || ""));
    return Number.isFinite(updatedMs) && Date.now() - updatedMs <= maxAgeMs;
  }

  function liveAgentRecordsForRun(run = {}, workspaceId = "", deps = {}) {
    const runId = String(run?.id || "").trim();
    const steps = Array.isArray(run?.steps) ? run.steps : [];
    const nodeIds = new Set(
      steps
        .map((step) => String(step?.node_id || "").trim())
        .filter(Boolean),
    );
    return eventStore(workspaceId, deps).slice()
      .filter((record) => {
        if (!record || record.chat) return false;
        const recordRunId = String(record.run_id || "").trim();
        const recordNodeId = String(record.node_id || "").trim();
        if (runId && recordRunId === runId) return true;
        if (!recordRunId && !runIsTerminal(deps, run) && recordNodeId && nodeIds.has(recordNodeId)) {
          return liveAgentRecordFresh(record);
        }
        return false;
      })
      .sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  }

  function liveAgentRecordForStep(step = {}, run = {}, workspaceId = "", deps = {}) {
    const agentExecutionId = String(step?.agent_execution_id || "").trim();
    const nodeId = String(step?.node_id || "").trim();
    const runId = String(run?.id || "").trim();
    const records = liveAgentRecordsForRun(run, workspaceId, deps);
    return records.find((record) => (
      agentExecutionId && String(record.id || "") === agentExecutionId
    )) || records.find((record) => (
      nodeId
      && String(record.node_id || "").trim() === nodeId
      && (!String(record.run_id || "").trim() || String(record.run_id || "").trim() === runId)
    )) || null;
  }

  function liveAgentSyntheticStepsForRun(run = {}, steps = [], deps = {}) {
    const existingAgentIds = new Set(
      (Array.isArray(steps) ? steps : [])
        .map((step) => String(step?.agent_execution_id || "").trim())
        .filter(Boolean),
    );
    const existingNodeIds = new Set(
      (Array.isArray(steps) ? steps : [])
        .filter((step) => String(step?.executor || "") === "agent")
        .map((step) => String(step?.node_id || "").trim())
        .filter(Boolean),
    );
    return liveAgentRecordsForRun(run, selectedWorkspaceId(deps), deps)
      .filter((record) => {
        const recordId = String(record.id || "").trim();
        const nodeId = String(record.node_id || "").trim();
        if (recordId && existingAgentIds.has(recordId)) return false;
        if (nodeId && existingNodeIds.has(nodeId)) return false;
        return liveAgentRecordIsActive(record);
      })
      .slice(0, 2)
      .map((record, offset) => ({
        index: (Array.isArray(steps) ? steps.length : 0) + offset,
        node_id: String(record.node_id || "").trim(),
        node_kind: String(record.node_kind || "agent.node").trim(),
        node_title: record.node_kind ? stageLabel(deps, record.node_kind) : "Agent 运行中",
        executor: "agent",
        status: liveAgentStatus(record),
        agent_execution_id: String(record.id || "").trim(),
        agent_steps: Array.isArray(record.steps) ? record.steps : [],
        trace_events: Array.isArray(record.trace_events) ? record.trace_events : [],
        error: String(record.error || "").trim(),
        _live_agent_synthetic: true,
      }));
  }

  function streamingChatDisplay(message = {}, workspaceId = "", agentId = "", deps = {}) {
    const status = String(message.status || "").trim();
    const text = String(message.text || "").trim();
    if (message.role === "assistant" && status === "streaming" && text && text !== "正在回复...") {
      return { text: message.error || text, live: true };
    }
    const canUseLive = message.role === "assistant"
      && ["pending", "streaming"].includes(status)
      && (!text || text === "正在回复...");
    if (!canUseLive) return { text: message.error || message.text || "", live: false };
    const live = liveChatRecord(workspaceId, String(message.agent_id || agentId || "").trim(), deps);
    const partial = String(live?.partial_answer || "").trim();
    return partial
      ? { text: partial, live: true }
      : { text: message.error || message.text || "", live: false };
  }

  window.WorkspaceAgentStreamState = {
    eventStore,
    liveAgentRecordForStep,
    liveAgentRecordFresh,
    liveAgentRecordIsActive,
    liveAgentRecordsForRun,
    liveAgentStatus,
    liveAgentSyntheticStepsForRun,
    liveChatRecord,
    mergeStreamEvent,
    streamRecordId,
    streamRecords,
    streamingChatDisplay,
  };
})();
