(function () {
  "use strict";

  const WORKSPACE_RUN_TIMELINE_EVENT_TYPES = [
    "run.created",
    "run.updated",
    "run.step.updated",
    "job.updated",
    "agent.step.created",
    "agent.tool.called",
    "agent.tool.result",
    "agent.tool.failed",
    "agent.completed",
    "agent.failed",
  ];

  function defaultTimestampMs(value) {
    const ms = Date.parse(String(value || ""));
    return Number.isFinite(ms) ? ms : 0;
  }

  function timestampMs(options = {}) {
    return typeof options.timestampMs === "function" ? options.timestampMs : defaultTimestampMs;
  }

  function defaultTimelineEventTypes() {
    return new Set(WORKSPACE_RUN_TIMELINE_EVENT_TYPES);
  }

  function runTimelineEventTypes(options = {}) {
    const source = options.timelineEventTypes;
    if (source instanceof Set) return source;
    if (Array.isArray(source)) return new Set(source.map((item) => String(item || "").trim()).filter(Boolean));
    return defaultTimelineEventTypes();
  }

  function eventKey(event = {}) {
    const sseId = Number(event.sse_id || event.id || 0);
    if (Number.isFinite(sseId) && sseId > 0) return `sse:${sseId}`;
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    const step = payload.step && typeof payload.step === "object" ? payload.step : {};
    const job = payload.job && typeof payload.job === "object" ? payload.job : {};
    const execution = payload.execution && typeof payload.execution === "object" ? payload.execution : {};
    return [
      event.type || "",
      event.run_id || "",
      event.job_id || "",
      event.agent_execution_id || execution.id || "",
      step.index ?? "",
      step.status || "",
      job.status || "",
      event.created_at || "",
    ].join("|");
  }

  function mergeEvents(existing = [], incoming = []) {
    const merged = [];
    const byKey = new Map();
    const append = (item) => {
      const event = item && typeof item === "object" ? item : null;
      if (!event?.type || !event?.run_id) return;
      const key = eventKey(event);
      const previousIndex = byKey.get(key);
      if (previousIndex !== undefined) {
        merged.splice(previousIndex, 1, { ...merged[previousIndex], ...event });
        return;
      }
      byKey.set(key, merged.length);
      merged.push(event);
    };
    (Array.isArray(existing) ? existing : []).forEach(append);
    (Array.isArray(incoming) ? incoming : []).forEach(append);
    return merged
      .sort((a, b) => {
        const leftId = Number(a.sse_id || a.id || 0);
        const rightId = Number(b.sse_id || b.id || 0);
        if (leftId && rightId && leftId !== rightId) return leftId - rightId;
        return String(a.created_at || "").localeCompare(String(b.created_at || ""));
      })
      .slice(-80);
  }

  function runStatus(run = {}) {
    return String(run?.status || "").trim();
  }

  function runIsTerminal(run = {}) {
    return ["done", "failed", "stopped"].includes(runStatus(run));
  }

  function runTimestampMs(run = {}, options = {}) {
    return timestampMs(options)(run?.updated_at || run?.finished_at || run?.completed_at || run?.created_at);
  }

  function shouldKeepExistingRun(existing = {}, incoming = {}, options = {}) {
    const existingStatus = runStatus(existing);
    const incomingStatus = runStatus(incoming);
    if (!existingStatus || !incomingStatus) return false;
    const existingTerminal = runIsTerminal(existing);
    const incomingTerminal = runIsTerminal(incoming);
    if (existingTerminal && !incomingTerminal) return true;
    const existingTime = runTimestampMs(existing, options);
    const incomingTime = runTimestampMs(incoming, options);
    if (existingTime && incomingTime && existingTime > incomingTime) return true;
    if (existingTerminal && incomingTerminal && existingTime && incomingTime && existingTime > incomingTime) return true;
    return false;
  }

  function stepMergeKey(step = {}, index = 0) {
    const source = step && typeof step === "object" ? step : {};
    const jobId = String(source.job_id || "").trim();
    if (jobId) return `job:${jobId}`;
    const agentExecutionId = String(source.agent_execution_id || "").trim();
    if (agentExecutionId) return `agent:${agentExecutionId}`;
    const nodeId = String(source.node_id || "").trim();
    if (nodeId) return `node:${nodeId}:${String(source.index ?? index)}`;
    return `index:${String(source.index ?? index)}`;
  }

  function mergeSteps(existingSteps = [], incomingSteps = []) {
    const existingItems = Array.isArray(existingSteps) ? existingSteps : [];
    const incomingItems = Array.isArray(incomingSteps) ? incomingSteps : [];
    if (!incomingItems.length) return existingItems.slice();
    const existingByKey = new Map(
      existingItems.map((step, index) => [stepMergeKey(step, index), step]),
    );
    const seen = new Set();
    const merged = incomingItems.map((step, index) => {
      const key = stepMergeKey(step, index);
      seen.add(key);
      const previous = existingByKey.get(key);
      return previous && typeof previous === "object" ? { ...previous, ...step } : step;
    });
    existingItems.forEach((step, index) => {
      const key = stepMergeKey(step, index);
      if (!seen.has(key)) merged.push(step);
    });
    return merged.sort((a, b) => Number(a?.index ?? 0) - Number(b?.index ?? 0));
  }

  function mergeRunSnapshot(existing = {}, incoming = {}, options = {}) {
    const previous = existing && typeof existing === "object" ? existing : {};
    const next = incoming && typeof incoming === "object" ? incoming : {};
    const keepExisting = shouldKeepExistingRun(previous, next, options);
    const selected = keepExisting ? previous : next;
    const steps = keepExisting
      ? (Array.isArray(previous.steps) ? previous.steps : [])
      : mergeSteps(previous.steps || [], next.steps || []);
    const base = keepExisting ? selected : { ...previous, ...selected };
    return {
      ...base,
      steps,
      events: mergeEvents(previous.events || [], next.events || []),
    };
  }

  function mergeRunListSnapshots(existingRuns = [], incomingRuns = [], options = {}) {
    const existingItems = Array.isArray(existingRuns) ? existingRuns : [];
    const incomingItems = Array.isArray(incomingRuns) ? incomingRuns : [];
    const existingById = new Map(
      existingItems
        .map((run) => [String(run?.id || "").trim(), run])
        .filter(([id]) => id),
    );
    const seen = new Set();
    const merged = incomingItems.map((run) => {
      const runId = String(run?.id || "").trim();
      if (!runId) return run;
      seen.add(runId);
      return mergeRunSnapshot(existingById.get(runId) || {}, run, options);
    });
    existingItems.forEach((run) => {
      const runId = String(run?.id || "").trim();
      if (runId && !seen.has(runId)) merged.push(run);
    });
    return merged.slice(0, 60);
  }

  function collectRunEvents(workspaces = []) {
    const eventsByRun = new Map();
    (Array.isArray(workspaces) ? workspaces : []).forEach((workspace) => {
      (Array.isArray(workspace?.runs) ? workspace.runs : []).forEach((run) => {
        const runId = String(run?.id || "").trim();
        if (!runId) return;
        const events = Array.isArray(run.events) ? run.events : [];
        if (events.length) eventsByRun.set(runId, mergeEvents(eventsByRun.get(runId) || [], events));
      });
    });
    return eventsByRun;
  }

  function mergeWorkspaceSnapshotRunEvents(workspace = {}, eventsByRun = new Map()) {
    if (!workspace || typeof workspace !== "object") return workspace;
    const runs = Array.isArray(workspace.runs) ? workspace.runs : [];
    if (!runs.length) return workspace;
    return {
      ...workspace,
      runs: runs.map((run) => {
        const runId = String(run?.id || "").trim();
        if (!runId) return run;
        const localEvents = eventsByRun.get(runId) || [];
        if (!localEvents.length) return run;
        return {
          ...run,
          events: mergeEvents(localEvents, run.events || []),
        };
      }),
    };
  }

  function mergeWorkspaceSnapshotRunState(workspace = {}, previousWorkspace = null, options = {}) {
    const previousEvents = previousWorkspace ? collectRunEvents([previousWorkspace]) : new Map();
    const nextWorkspace = mergeWorkspaceSnapshotRunEvents(workspace, previousEvents);
    if (!previousWorkspace || !Array.isArray(nextWorkspace?.runs)) return nextWorkspace;
    return {
      ...nextWorkspace,
      runs: mergeRunListSnapshots(previousWorkspace.runs || [], nextWorkspace.runs || [], options),
    };
  }

  function compactStreamEventPayload(payload = {}) {
    const source = payload && typeof payload === "object" ? payload : {};
    const compact = {};
    [
      "node_id",
      "node_kind",
      "agent_id",
      "chat",
      "tool_id",
      "step_number",
      "arguments_summary",
      "observation_summary",
      "runtime_control",
      "runtime_status",
      "runtime_side_effect",
    ].forEach((key) => {
      if (source[key] !== undefined) compact[key] = source[key];
    });
    const run = source.run && typeof source.run === "object" ? source.run : {};
    if (run.id) {
      compact.run = {
        id: String(run.id || "").trim(),
        kind: String(run.kind || "").trim(),
        status: String(run.status || "").trim(),
        summary: String(run.summary || "").trim(),
        progress: run.progress && typeof run.progress === "object" ? run.progress : {},
        updated_at: String(run.updated_at || "").trim(),
      };
    }
    const step = source.step && typeof source.step === "object" ? source.step : {};
    if (step.node_id || step.node_kind || step.job_id || step.agent_execution_id) {
      compact.step = {
        index: Number(step.index || 0),
        node_id: String(step.node_id || "").trim(),
        node_kind: String(step.node_kind || "").trim(),
        node_title: String(step.node_title || "").trim(),
        executor: String(step.executor || "").trim(),
        status: String(step.status || "").trim(),
        job_id: String(step.job_id || "").trim(),
        child_job_ids: (Array.isArray(step.child_job_ids) ? step.child_job_ids : [])
          .map((item) => String(item || "").trim())
          .filter(Boolean),
        child_run_ids: (Array.isArray(step.child_run_ids) ? step.child_run_ids : [])
          .map((item) => String(item || "").trim())
          .filter(Boolean),
        runtime_control: String(step.runtime_control || "").trim(),
        runtime_status: String(step.runtime_status || "").trim(),
        runtime_side_effect: String(step.runtime_side_effect || "").trim(),
        agent_execution_id: String(step.agent_execution_id || "").trim(),
        error: String(step.error || "").trim(),
      };
    }
    const job = source.job && typeof source.job === "object" ? source.job : {};
    if (job.id) {
      compact.job = {
        id: String(job.id || "").trim(),
        status: String(job.status || "").trim(),
        server_id: String(job.server_id || "").trim(),
        queue_rank: Number(job.queue_rank || 0),
        started_at: String(job.started_at || "").trim(),
        finished_at: String(job.finished_at || "").trim(),
        error: String(job.error || "").trim(),
      };
    }
    const execution = source.execution && typeof source.execution === "object" ? source.execution : {};
    if (execution.id) {
      compact.execution = {
        id: String(execution.id || "").trim(),
        success: Boolean(execution.success),
        model: String(execution.model || "").trim(),
        total_tokens: Number(execution.total_tokens || 0),
        total_steps: Number(execution.total_steps || 0),
        error: String(execution.error || "").trim(),
      };
    }
    return compact;
  }

  function normalizeRunEventFromStream(event = {}, payload = {}, options = {}) {
    const eventType = String(event.type || "").trim();
    if (!runTimelineEventTypes(options).has(eventType)) return null;
    const source = payload && typeof payload === "object" ? payload : {};
    const run = source.run && typeof source.run === "object" ? source.run : {};
    const step = source.step && typeof source.step === "object" ? source.step : {};
    const job = source.job && typeof source.job === "object" ? source.job : {};
    const metadata = job.metadata && typeof job.metadata === "object" ? job.metadata : {};
    const execution = source.execution && typeof source.execution === "object" ? source.execution : {};
    const runId = String(event.run_id || source.run_id || run.id || metadata.execution_run_id || "").trim();
    const workspaceId = String(event.workspace_id || source.workspace_id || run.workspace_id || metadata.workspace_id || "").trim();
    if (!workspaceId || !runId) return null;
    return {
      sse_id: Number(event.id || event.sse_id || 0),
      type: eventType,
      workspace_id: workspaceId,
      run_id: runId,
      job_id: String(event.job_id || source.job_id || job.id || step.job_id || "").trim(),
      agent_execution_id: String(
        event.agent_execution_id
        || source.agent_execution_id
        || execution.id
        || step.agent_execution_id
        || "",
      ).trim(),
      created_at: String(event.created_at || source.created_at || new Date().toISOString()).trim(),
      payload: compactStreamEventPayload(source),
    };
  }

  window.WorkspaceRunStateMerge = {
    collectRunEvents,
    compactStreamEventPayload,
    eventKey,
    mergeEvents,
    mergeRunListSnapshots,
    mergeRunSnapshot,
    mergeSteps,
    mergeWorkspaceSnapshotRunEvents,
    mergeWorkspaceSnapshotRunState,
    normalizeRunEventFromStream,
    runIsTerminal,
    runStatus,
    runTimestampMs,
    shouldKeepExistingRun,
    stepMergeKey,
    timelineEventTypes: defaultTimelineEventTypes,
  };
})();
