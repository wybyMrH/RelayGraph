(function () {
  "use strict";

  const WORKSPACE_STREAM_EVENT_TYPES = [
    "workspace.snapshot",
    "workspace.updated",
    "cockpit.updated",
    "run.created",
    "run.updated",
    "run.step.updated",
    "job.updated",
    "job.log.delta",
    "chat.message.created",
    "chat.message.delta",
    "chat.message.completed",
    "chat.message.failed",
    "agent.message.delta",
    "agent.step.created",
    "agent.thought.delta",
    "agent.tool.called",
    "agent.tool.result",
    "agent.tool.failed",
    "agent.answer.delta",
    "agent.completed",
    "agent.failed",
    "heartbeat",
  ];

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function appState(deps = {}) {
    const source = typeof deps.state === "function" ? deps.state() : deps.state;
    return source && typeof source === "object" ? source : {};
  }

  function uiState(deps = {}) {
    const state = appState(deps);
    if (!state.ui || typeof state.ui !== "object") state.ui = {};
    return state.ui;
  }

  function selectedWorkspaceId(deps = {}) {
    const state = appState(deps);
    const value = typeof deps.selectedWorkspaceId === "function"
      ? deps.selectedWorkspaceId()
      : deps.selectedWorkspaceId ?? state.selectedWorkspaceId;
    return String(value || "").trim();
  }

  function selectedWorkspace(deps = {}) {
    return fn(deps, "selectedWorkspace", () => null)();
  }

  function eventSourceConstructor(deps = {}) {
    if (deps.EventSource === undefined && deps.eventSourceCtor === undefined) {
      return typeof EventSource === "undefined" ? null : EventSource;
    }
    return deps.EventSource || deps.eventSourceCtor || null;
  }

  function nowMs(deps = {}) {
    return fn(deps, "nowMs", () => Date.now())();
  }

  function requestFrame(deps = {}, callback) {
    const request = deps.requestAnimationFrame || (typeof requestAnimationFrame === "function" ? requestAnimationFrame : null);
    if (typeof request === "function") return request(callback);
    return fn(deps, "setTimeout", (handler, ms) => setTimeout(handler, ms))(callback, 100);
  }

  function timerSetInterval(deps = {}, callback, ms) {
    return fn(deps, "setInterval", (handler, delay) => setInterval(handler, delay))(callback, ms);
  }

  function timerClearInterval(deps = {}, timer) {
    return fn(deps, "clearInterval", (value) => clearInterval(value))(timer);
  }

  function encodeValue(deps = {}, value) {
    return fn(deps, "encodeURIComponent", (item) => encodeURIComponent(item))(value);
  }

  function makeSearchParams(deps = {}) {
    const Params = deps.URLSearchParams || (typeof URLSearchParams === "undefined" ? null : URLSearchParams);
    return Params ? new Params() : null;
  }

  function defaultEventTypes() {
    return [...WORKSPACE_STREAM_EVENT_TYPES];
  }

  function eventTypes(deps = {}) {
    return Array.isArray(deps.eventTypes) ? deps.eventTypes : defaultEventTypes();
  }

  function renderRealtimeSurfaces(deps = {}) {
    fn(deps, "renderWorkspaces", () => {})();
    fn(deps, "renderJobs", () => {})();
    fn(deps, "renderWorkspaceHome", () => {})();
    fn(deps, "renderWorkspaceRuns", () => {})();
    fn(deps, "renderWorkspaceExecutionDetail", () => {})();
    fn(deps, "renderWorkspaceUseChat", () => {})();
    fn(deps, "renderWorkspaceChat", () => {})();
    fn(deps, "renderWorkspaceUseMonitor", () => {})(selectedWorkspace(deps));
  }

  function gapNotice(payload = {}) {
    const gap = payload.gap && typeof payload.gap === "object" ? payload.gap : {};
    const reason = String(payload.snapshot_reason || gap.reason || "event_replay_gap").trim();
    if (reason === "buffer_overflow") return "实时事件有缺口，已用最新快照补齐状态，并刷新打开的日志。";
    if (reason === "event_id_reset_or_server_restart") return "服务或事件序号已重置，已用最新快照恢复状态，并刷新打开的日志。";
    return "实时连接恢复后已补一次快照，并刷新打开的日志。";
  }

  function renderRealtimeRecovery(workspaceId, deps = {}) {
    if (workspaceId !== selectedWorkspaceId(deps)) return;
    renderRealtimeSurfaces(deps);
  }

  function flushRender(workspaceId, deps = {}) {
    const ui = uiState(deps);
    ui.workspaceStreamRenderQueued = false;
    ui.workspaceStreamRenderTimer = null;
    const id = String(workspaceId || "").trim();
    if (!id || id !== selectedWorkspaceId(deps)) return;
    renderRealtimeSurfaces(deps);
  }

  function scheduleRender(workspaceId, deps = {}) {
    const id = String(workspaceId || "").trim();
    const ui = uiState(deps);
    if (!id || id !== selectedWorkspaceId(deps)) return;
    if (ui.workspaceStreamRenderQueued) return;
    ui.workspaceStreamRenderQueued = true;
    const flush = () => flushRender(id, deps);
    ui.workspaceStreamRenderTimer = requestFrame(deps, flush);
  }

  async function recoverGap(workspaceId, payload = {}, deps = {}) {
    const id = String(workspaceId || "").trim();
    const ui = uiState(deps);
    if (!id || ui.workspaceEventRecovering) return;
    ui.workspaceEventRecovering = true;
    ui.workspaceEventGapNotice = gapNotice(payload);
    ui.workspaceEventGapAt = nowMs(deps);
    if (id === selectedWorkspaceId(deps)) {
      fn(deps, "setWorkspaceMessage", () => {})(ui.workspaceEventGapNotice, false);
      fn(deps, "renderWorkspaceRuns", () => {})();
      fn(deps, "renderWorkspaceUseMonitor", () => {})(selectedWorkspace(deps));
    }
    try {
      const statusPayload = await fn(deps, "fetchJson", async () => ({}))("/api/status");
      fn(deps, "applyStatusPayload", () => {})(statusPayload, { preserveWorkspaceUi: true });
      await fn(deps, "refreshWorkspaceCockpit", async () => null)(id, { render: false, quiet: true });
      await fn(deps, "refreshOpenJobOutputTabs", async () => null)({ useOffset: true, quiet: true, keepSearchIndex: true });
      renderRealtimeRecovery(id, deps);
    } catch (error) {
      if (id === selectedWorkspaceId(deps)) {
        const text = fn(deps, "humanizeFetchError", (err, context) => err?.message || context || String(err || ""))(error, "补偿实时事件缺口");
        fn(deps, "setWorkspaceMessage", () => {})(text, true);
      }
    } finally {
      ui.workspaceEventRecovering = false;
      if (id === selectedWorkspaceId(deps)) {
        fn(deps, "renderWorkspaceRuns", () => {})();
        fn(deps, "renderWorkspaceUseMonitor", () => {})(selectedWorkspace(deps));
      }
    }
  }

  function applyEvent(rawEvent = {}, deps = {}) {
    const event = rawEvent && typeof rawEvent === "object" ? rawEvent : {};
    const eventType = String(event.type || "").trim();
    if (eventType === "heartbeat") return;
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    const workspaceId = String(event.workspace_id || payload.workspace_id || payload.workspace?.id || "").trim();
    if (!workspaceId) return;
    fn(deps, "mergeWorkspaceExecutionResultPayload", () => {})(workspaceId, payload);
    if (eventType === "workspace.snapshot" && payload.gap) {
      void recoverGap(workspaceId, payload, deps);
    }
    if (eventType === "chat.message.delta") {
      fn(deps, "mergeWorkspaceChatDelta", () => {})(workspaceId, {
        ...payload,
        created_at: event.created_at || payload.created_at || "",
      });
    }
    if (eventType === "job.log.delta") {
      fn(deps, "mergeWorkspaceJobLogDelta", () => {})(payload);
    }
    const runEvent = fn(deps, "normalizeWorkspaceRunEventFromStream", () => null)(event, payload);
    if (runEvent) fn(deps, "mergeWorkspaceRunEventIntoState", () => {})(workspaceId, runEvent);
    if (eventType.startsWith("agent.")) {
      fn(deps, "mergeWorkspaceAgentStreamEvent", () => {})(workspaceId, event, payload);
    }
    if (
      eventType.startsWith("run.")
      || eventType === "job.updated"
      || eventType === "agent.completed"
      || eventType === "agent.failed"
    ) {
      fn(deps, "scheduleExecutionOverviewRefresh", () => {})();
    }
    if (workspaceId === selectedWorkspaceId(deps) && eventType !== "job.log.delta") {
      scheduleRender(workspaceId, deps);
    }
  }

  function handleMessage(event, deps = {}) {
    let payload = null;
    try {
      payload = JSON.parse(event.data || "{}");
    } catch (error) {
      return;
    }
    const ui = uiState(deps);
    const workspaceId = String(payload.workspace_id || ui.workspaceEventWorkspaceId || "").trim();
    const eventType = String(payload.type || event.type || "").trim();
    const eventId = Number(event.lastEventId || payload.id || 0);
    if (workspaceId && Number.isFinite(eventId)) {
      if (eventType === "workspace.snapshot" && eventId >= 0) {
        ui.workspaceEventLastIds[workspaceId] = eventId;
      } else if (eventId > 0) {
        ui.workspaceEventLastIds[workspaceId] = Math.max(
          Number(ui.workspaceEventLastIds[workspaceId] || 0),
          eventId,
        );
      }
    }
    applyEvent(payload, deps);
  }

  function close(deps = {}) {
    const ui = uiState(deps);
    if (ui.workspaceEventSource) {
      ui.workspaceEventSource.close();
    }
    ui.workspaceEventSource = null;
    ui.workspaceEventWorkspaceId = "";
    ui.workspaceEventConnected = false;
    stopFallbackPolling(deps);
  }

  function realtimeStatusText(deps = {}) {
    const ui = uiState(deps);
    if (!selectedWorkspace(deps)?.id) return "";
    if (ui.workspaceEventRecovering) return "实时补偿中";
    if (ui.workspaceEventGapAt && nowMs(deps) - Number(ui.workspaceEventGapAt || 0) < 60000) {
      return "实时已补快照";
    }
    if (ui.workspaceEventConnected) return "实时连接";
    if (!eventSourceConstructor(deps)) return "实时不可用 · 轮询中";
    if (ui.workspaceEventFallbackTimer) return "实时断开 · 窄轮询";
    return "实时连接中";
  }

  async function pollFallback(workspaceId = "", deps = {}) {
    const id = String(workspaceId || uiState(deps).workspaceEventFallbackWorkspaceId || "").trim();
    const ui = uiState(deps);
    if (!id || ui.workspaceEventFallbackBusy) return;
    ui.workspaceEventFallbackBusy = true;
    try {
      try {
        const params = makeSearchParams(deps);
        let query = "";
        if (params) {
          params.set("since", String(Math.max(0, Number(ui.workspaceEventLastIds[id] || 0))));
          params.set("limit", "200");
          query = params.toString();
        } else {
          query = `since=${encodeValue(deps, String(Math.max(0, Number(ui.workspaceEventLastIds[id] || 0))))}&limit=200`;
        }
        const replay = await fn(deps, "fetchJson", async () => ({}))(
          `/api/workspaces/${encodeValue(deps, id)}/events/replay?${query}`,
        );
        const events = Array.isArray(replay.events) ? replay.events : [];
        events.forEach((streamEvent) => {
          applyEvent(streamEvent, deps);
          const eventId = Number(streamEvent?.id || 0);
          if (Number.isFinite(eventId) && eventId > 0) {
            ui.workspaceEventLastIds[id] = Math.max(Number(ui.workspaceEventLastIds[id] || 0), eventId);
          }
        });
        const nextSinceId = Number(replay.next_since_id || 0);
        if (Number.isFinite(nextSinceId) && nextSinceId > 0) {
          ui.workspaceEventLastIds[id] = Math.max(Number(ui.workspaceEventLastIds[id] || 0), nextSinceId);
        }
      } catch (replayError) {
        const statusPayload = await fn(deps, "fetchJson", async () => ({}))("/api/status");
        fn(deps, "applyStatusPayload", () => {})(statusPayload, { preserveWorkspaceUi: true });
        const payload = await fn(deps, "fetchJson", async () => ({}))(`/api/workspaces/${encodeValue(deps, id)}/runs`);
        if (Array.isArray(payload.runs)) fn(deps, "mergeWorkspaceRunsPayload", () => {})(id, payload.runs);
        await fn(deps, "refreshWorkspaceCockpit", async () => null)(id, { render: false, quiet: true });
      }
      await fn(deps, "refreshOpenJobOutputTabs", async () => null)({ useOffset: true, quiet: true, keepSearchIndex: true });
      if (id === selectedWorkspaceId(deps)) {
        renderRealtimeSurfaces(deps);
      }
    } catch (error) {
      // SSE fallback should stay quiet; the normal refresh path still surfaces hard failures.
    } finally {
      ui.workspaceEventFallbackBusy = false;
    }
  }

  function startFallbackPolling(workspaceId = "", deps = {}) {
    const id = String(workspaceId || selectedWorkspaceId(deps)).trim();
    const ui = uiState(deps);
    if (!id) return;
    if (ui.workspaceEventFallbackTimer && ui.workspaceEventFallbackWorkspaceId === id) return;
    stopFallbackPolling(deps);
    ui.workspaceEventFallbackWorkspaceId = id;
    void pollFallback(id, deps);
    ui.workspaceEventFallbackTimer = timerSetInterval(deps, () => {
      if (ui.workspaceEventConnected || selectedWorkspaceId(deps) !== id) {
        stopFallbackPolling(deps);
        return;
      }
      void pollFallback(id, deps);
    }, Math.max(3000, Number(ui.pollIntervalMs || 5000)));
    if (id === selectedWorkspaceId(deps)) fn(deps, "renderWorkspaceRuns", () => {})();
  }

  function stopFallbackPolling(deps = {}) {
    const ui = uiState(deps);
    if (ui.workspaceEventFallbackTimer) {
      timerClearInterval(deps, ui.workspaceEventFallbackTimer);
    }
    ui.workspaceEventFallbackTimer = null;
    ui.workspaceEventFallbackWorkspaceId = "";
    ui.workspaceEventFallbackBusy = false;
    if (selectedWorkspace(deps)?.id) fn(deps, "renderWorkspaceRuns", () => {})();
  }

  function connect(workspaceId = "", deps = {}) {
    const id = String(workspaceId || selectedWorkspaceId(deps)).trim();
    const ui = uiState(deps);
    if (!id) {
      close(deps);
      return;
    }
    const EventSourceCtor = eventSourceConstructor(deps);
    if (!EventSourceCtor) {
      close(deps);
      ui.workspaceEventWorkspaceId = id;
      startFallbackPolling(id, deps);
      return;
    }
    if (ui.workspaceEventSource && ui.workspaceEventWorkspaceId === id) return;
    close(deps);
    const lastId = Number(ui.workspaceEventLastIds[id] || 0);
    const url = `/api/workspaces/${encodeValue(deps, id)}/events${lastId > 0 ? `?since=${encodeValue(deps, String(lastId))}` : ""}`;
    const source = new EventSourceCtor(url);
    ui.workspaceEventSource = source;
    ui.workspaceEventWorkspaceId = id;
    const messageHandler = (event) => handleMessage(event, deps);
    eventTypes(deps).forEach((eventType) => {
      source.addEventListener(eventType, messageHandler);
    });
    source.onmessage = messageHandler;
    source.onopen = () => {
      ui.workspaceEventConnected = true;
      stopFallbackPolling(deps);
      fn(deps, "renderWorkspaceRuns", () => {})();
    };
    source.onerror = () => {
      ui.workspaceEventConnected = false;
      startFallbackPolling(id, deps);
      fn(deps, "renderWorkspaceRuns", () => {})();
    };
  }

  window.WorkspaceEventStream = {
    applyEvent,
    close,
    connect,
    eventTypes: defaultEventTypes,
    flushRender,
    gapNotice,
    handleMessage,
    pollFallback,
    realtimeStatusText,
    recoverGap,
    renderRealtimeRecovery,
    scheduleRender,
    startFallbackPolling,
    stopFallbackPolling,
  };
})();
