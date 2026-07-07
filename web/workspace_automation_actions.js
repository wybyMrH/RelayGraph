(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function appState(deps = {}) {
    const source = typeof deps.state === "function" ? deps.state() : deps.state;
    if (!source || typeof source !== "object") return { ui: {} };
    if (!source.ui || typeof source.ui !== "object") source.ui = {};
    return source;
  }

  function element(deps = {}, id) {
    return fn(deps, "element", () => null)(id);
  }

  function storageKeys(deps = {}) {
    return deps.STORAGE_KEYS && typeof deps.STORAGE_KEYS === "object" ? deps.STORAGE_KEYS : {};
  }

  function workspaceManageTabs(deps = {}) {
    return Array.isArray(deps.WORKSPACE_MANAGE_TABS) ? deps.WORKSPACE_MANAGE_TABS : [];
  }

  function workspaceFlowCanvas(deps = {}) {
    return deps.WORKSPACE_FLOW_CANVAS && typeof deps.WORKSPACE_FLOW_CANVAS === "object"
      ? deps.WORKSPACE_FLOW_CANVAS
      : { zoomStep: 0 };
  }

  function selectedWorkspace(deps = {}) {
    return fn(deps, "selectedWorkspace", () => null)();
  }

  const ACTION_LABELS = {
    "focus-scheduling-stage": "定位闭环阶段",
    "select-execution-node": "定位执行节点",
    "select-workspace-node": "编辑工作流节点",
    "select-workspace-agent": "编辑 Agent",
    "focus-workspace-goal": "填写目标",
    "focus-workspace-node-kind": "聚焦节点类型",
    "focus-workspace-backfill-target": "定位回填字段",
    "create-workspace": "仅建实例",
    "create-workspace-discover": "建实例 + 发现",
    "create-workspace-run": "建实例 + 推进",
    "test-workspace-chain": "启动检查",
    "run-workspace-node": "运行节点",
    "run-workspace-node-agent": "Agent 运行",
    "run-workspace-node-job": "Job 运行",
    "run-selected-node": "运行当前节点",
    "run-workspace-to-selected-node": "运行到当前节点",
    "run-selected-workspace": "运行工作流",
    "open-workspace-run": "打开运行输出",
    "apply-recommended-workspace-roles": "应用推荐分工",
    "merge-recommended-workspace-agents": "补齐推荐角色",
    "add-workspace-agent": "新增 Agent",
    "merge-recommended-workspace-tools": "补齐推荐工具",
    "add-workspace-tool": "新增工具",
    "add-provider-profile": "新增 Profile",
    "open-workspace-details": "打开高级配置",
    "submit-workspace-form": "保存项目",
    "advance-workspace-automation": "自动推进",
    "run-workspace-discovery": "自动发现",
    "apply-workspace-automation": "回填证据",
    "apply-workspace-backfill-item": "应用单项回填",
    "apply-workspace-scheduler-candidate": "应用调度候选",
    "refresh-workspace-resources": "刷新资源",
    "refresh-workspace-resource-server": "刷新推荐服务器",
    "refresh-workspace-resource-selected-server": "刷新单机",
    "copy-execution-bundle-script": "复制执行脚本",
    "copy-execution-bundle-json": "复制执行包 JSON",
    "copy-node-execution-bundle-script": "复制节点脚本",
  };

  const NON_BLOCKING_ACTIONS = new Set([
    "focus-scheduling-stage",
    "select-execution-node",
    "select-workspace-node",
    "select-workspace-agent",
    "focus-workspace-goal",
    "open-workspace-details",
    "focus-workspace-node-kind",
    "focus-workspace-backfill-target",
    "open-workspace-run",
    "refresh-workspace-resources",
    "refresh-workspace-resource-server",
    "refresh-workspace-resource-selected-server",
    "test-workspace-chain",
    "copy-execution-bundle-script",
    "copy-execution-bundle-json",
    "copy-node-execution-bundle-script",
  ]);

  const ACTION_HELP = {
    "focus-scheduling-stage": "定位到这个闭环阶段对应的执行节点、资源矩阵或执行详情，并短暂高亮相关区域。",
    "select-execution-node": "定位到这个执行节点，并在右侧查看门禁、资源、任务、产物和执行包详情。",
    "select-workspace-node": "定位到这个工作流节点，并在右侧编辑执行者、交接、输入输出和资源策略。",
    "select-workspace-agent": "定位到这个 Agent，并编辑角色、提示词、工具和模型覆盖。",
    "focus-workspace-goal": "把焦点放到复现/部署目标输入框；先写清目标，系统再自动整理 repo、论文、数据路径、环境和 GPU 调度线索。",
    "focus-workspace-node-kind": "把焦点放到节点类型选择器，准备插入新的工作流节点。",
    "focus-workspace-backfill-target": "定位到证据或回填建议对应的执行节点，并在右侧查看字段、门禁、资源和上下文。",
    "create-workspace": "只建实例快照，不提交发现链或运行队列。",
    "create-workspace-discover": "建实例后只跑安全发现链，先收集源码、路径、数据、环境、GPU 和产物证据。",
    "create-workspace-run": "建实例后交给自动推进；首次通常先跑安全发现，门禁通过后再完整运行。",
    "test-workspace-chain": "启动前检查当前输入、链路模板、发现链、资源和执行包是否就绪，不创建实例。",
    "run-workspace-node": "按自动策略提交当前节点（Agent 优先，失败则回退 Job）。",
    "run-workspace-node-agent": "由绑定的 Agent 执行当前节点，可调用 workflow.edit / artifact.write 写回配置。",
    "run-workspace-node-job": "把当前节点作为 shell Job 提交到队列，适合发现链与 run.command。",
    "run-selected-node": "只提交当前节点，用于单点调试；不会运行整条链。",
    "run-workspace-to-selected-node": "从起点运行到当前选中节点，用于验证前置 source/data/env/GPU 链路；不会提交后续节点。",
    "run-selected-workspace": "门禁通过后提交完整工作流；门禁失败时不会创建半截队列。",
    "open-workspace-run": "打开这条运行记录的输出日志，用于确认当前卡在命令、环境、路径、数据还是 GPU 调度。",
    "apply-recommended-workspace-roles": "根据节点类型批量填充推荐 Agent 分工，降低逐个配置节点的成本。",
    "merge-recommended-workspace-agents": "按复现/部署链路补齐默认 Agent 角色，不覆盖已有自定义 Agent。",
    "add-workspace-agent": "在当前项目实例内新增一个 Agent 草稿。",
    "merge-recommended-workspace-tools": "补齐复现/部署常用工具定义，不移除已有工具。",
    "add-workspace-tool": "在当前项目实例内新增一个工具草稿。",
    "add-provider-profile": "新增一个当前浏览器可用的 Provider Profile，并展开 AI 高级配置。",
    "open-workspace-details": "展开当前模块的高级配置抽屉，查看列表、编辑器和低层参数。",
    "submit-workspace-form": "保存当前项目实例、节点链、Agent、工具和 AI 路由草稿。",
    "advance-workspace-automation": "根据当前门禁自动决定发现、观察、复查失败、回填或完整运行。",
    "run-workspace-discovery": "只运行安全发现链，收集源码、路径、数据、环境、GPU 和产物证据。",
    "apply-workspace-automation": "把建议和发现证据回填到节点配置，后续运行会使用这些路径、环境和资源线索。",
    "apply-workspace-backfill-item": "只把当前这一条证据回填到对应节点字段，不触发全局默认值或其他证据回填。",
    "apply-workspace-scheduler-candidate": "把当前候选服务器/GPU 写入 gpu.allocate 和 run.command，后续执行包会使用这个调度目标。",
    "refresh-workspace-resources": "刷新全部服务器、GPU、任务和工作台资源快照；异步返回后保留当前工作台选项卡和草稿。",
    "refresh-workspace-resource-server": "只刷新指定服务器的 GPU、显存、进程和连接状态；不会重置工作台。",
    "refresh-workspace-resource-selected-server": "只刷新下拉选择的单台服务器 GPU、显存、进程和连接状态；不会重置工作台。",
    "copy-execution-bundle-script": "复制当前执行包脚本，便于在 tmux、SSH 或任务队列中复核执行。",
    "copy-execution-bundle-json": "复制结构化执行包 JSON，包含目标、清单、调度、步骤和复现脚本，便于外部队列、审计或跨机器复跑。",
    "copy-node-execution-bundle-script": "复制当前节点归档的执行包脚本，便于复查这次运行按什么脚本提交。",
  };

  function hasAction(action) {
    return Object.prototype.hasOwnProperty.call(ACTION_LABELS, String(action || ""));
  }

  function actionLabel(action) {
    return ACTION_LABELS[String(action || "")] || "工作台操作";
  }

  function actionHelp(action, fallback = "") {
    return ACTION_HELP[String(action || "")] || fallback || actionLabel(action);
  }

  function isNonBlockingAction(action) {
    return NON_BLOCKING_ACTIONS.has(String(action || ""));
  }

  const BUSY_CONTROL_ACTIONS = [
    ["workspaceCreateTaskBtn", "create-workspace"],
    ["workspaceCreateDiscoverTaskBtn", "create-workspace-discover"],
    ["workspaceCreateRunTaskBtn", "create-workspace-run"],
    ["workspaceTestChainBtn", "test-workspace-chain"],
    ["workspaceRunFlowBtn", "run-selected-workspace"],
  ];

  function actionButtons(deps = {}) {
    return fn(deps, "actionButtons", () => document.querySelectorAll("[data-action]"))();
  }

  function updateBusyControls(deps = {}) {
    const state = appState(deps);
    const busyAction = String(state.ui.workspaceAutomationBusyAction || "");
    const busy = Boolean(busyAction);
    actionButtons(deps).forEach((button) => {
      const action = button.dataset?.action || "";
      if (!hasAction(action)) return;
      if (isNonBlockingAction(action)) return;
      button.disabled = busy;
    });
    BUSY_CONTROL_ACTIONS.forEach(([id, action]) => {
      const button = element(deps, id);
      if (!button) return;
      button.disabled = busy;
      button.dataset.busyAction = busyAction === action ? "1" : "";
    });
  }

  function beginAutomationAction(action, options = {}, deps = {}) {
    const state = appState(deps);
    const busyAction = String(state.ui.workspaceAutomationBusyAction || "");
    if (busyAction) {
      const message = `${actionLabel(busyAction)}正在处理中，稍等一下再操作。`;
      if (options.useMessage) fn(deps, "setWorkspaceUseMessage", () => {})(message, true);
      else fn(deps, "setWorkspaceMessage", () => {})(message, true);
      return false;
    }
    state.ui.workspaceAutomationBusyAction = String(action || "workspace-action");
    updateBusyControls(deps);
    fn(deps, "renderWorkspaceCockpitOverview", () => {})();
    fn(deps, "renderWorkspaceExecutionDetail", () => {})();
    return true;
  }

  function endAutomationAction(action, deps = {}) {
    const state = appState(deps);
    const current = String(state.ui.workspaceAutomationBusyAction || "");
    if (current && current !== String(action || "")) return;
    state.ui.workspaceAutomationBusyAction = "";
    updateBusyControls(deps);
    fn(deps, "renderWorkspaceCockpitOverview", () => {})();
    fn(deps, "renderWorkspaceExecutionDetail", () => {})();
  }

  function workflowErrorMessage(error) {
    const blocked = Array.isArray(error?.payload?.blocked_checks) ? error.payload.blocked_checks : [];
    if (!blocked.length) return error?.message || "工作流提交失败";
    const applied = Array.isArray(error?.payload?.applied) ? error.payload.applied.length : 0;
    const prefix = applied ? `已先回填 ${applied} 项建议/发现，但` : "";
    const labels = blocked
      .map((item) => item.label || item.title || item.node_kind || item.id)
      .filter(Boolean)
      .slice(0, 5)
      .join("、");
    return `${prefix}完整运行前检查未通过：${labels}。先点“自动发现”或补齐阻塞项，再提交完整工作流。`;
  }

  function advanceMessage(payload) {
    const action = String(payload?.action || "").trim();
    const jobs = Array.isArray(payload?.jobs) ? payload.jobs : [];
    const applied = Array.isArray(payload?.applied) ? payload.applied.length : 0;
    const evidenceApplied = Array.isArray(payload?.evidence_applied) ? payload.evidence_applied.length : 0;
    const decision = payload?.decision && typeof payload.decision === "object" ? payload.decision : null;
    const suffix = decision?.reason
      ? ` 原因：${decision.reason}${decision.next_action ? ` 下一步：${decision.next_action}` : ""}`
      : "";
    if (action === "discover") {
      return `自动推进已提交发现链：${jobs.length} 个节点${applied ? ` · 先应用 ${applied} 项建议` : ""}。${suffix}`;
    }
    if (action === "run") {
      return `自动推进已提交完整工作流：${jobs.length} 个节点${applied ? ` · 先回填 ${applied} 项` : ""}${evidenceApplied ? ` · ${evidenceApplied} 项来自发现证据` : ""}。${suffix}`;
    }
    if (action === "watch") {
      const active = Array.isArray(payload?.active_job_ids) ? payload.active_job_ids.length : 0;
      return `自动推进暂停：已有 ${active} 个任务在队列或运行中，先观察当前执行。${suffix}`;
    }
    if (action === "review_failed") {
      const failed = Array.isArray(payload?.failed_job_ids) ? payload.failed_job_ids.length : 0;
      return `自动推进暂停：存在 ${failed} 个失败或停止任务，先查看输出再继续。${suffix}`;
    }
    if (action === "blocked") {
      const blocked = Array.isArray(payload?.blocked_checks) ? payload.blocked_checks : [];
      const labels = blocked.map((item) => item.label || item.title || item.node_kind || item.id).filter(Boolean).slice(0, 5).join("、");
      return `${payload?.message || "自动推进遇到阻塞"}${labels ? `：${labels}` : ""}${suffix}`;
    }
    return `${payload?.message || "自动推进已完成。"}${suffix}`;
  }

  function handleAutomationAction(button, deps = {}) {
    if (!button?.dataset?.action) return false;
    const action = button.dataset.action;
    const state = appState(deps);
    const keys = storageKeys(deps);
    if (action === "focus-scheduling-stage") {
      const nodeId = String(button.dataset.nodeId || "").trim();
      const targetId = button.dataset.targetId || "workspaceExecutionBoard";
      const tab = button.dataset.tab || "home";
      if (nodeId) {
        fn(deps, "focusWorkspaceExecutionNode", () => {})(nodeId, { targetId, tab });
      } else {
        fn(deps, "switchWorkspaceTab", () => {})(tab, { reveal: false });
        fn(deps, "revealWorkspacePanelTarget", () => {})(targetId, { block: "center" });
      }
      return true;
    }
    if (action === "select-workspace-scheduler-candidate") {
      fn(deps, "selectWorkspaceSchedulerCandidate", () => {})(button);
      return true;
    }
    if (action === "apply-workspace-scheduler-candidate") {
      void fn(deps, "applyWorkspaceSchedulerCandidate", async () => {})(button);
      return true;
    }
    if (action === "select-execution-node" && button.dataset.nodeId) {
      fn(deps, "focusWorkspaceExecutionNode", () => {})(button.dataset.nodeId, {
        targetId: button.dataset.targetId || "workspaceExecutionBoard",
        tab: button.dataset.tab || "home",
      });
      return true;
    }
    if (action === "open-workspace-node" && button.dataset.nodeId) {
      fn(deps, "switchWorkspaceTab", () => {})("workflow");
      fn(deps, "selectWorkspaceNode", () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "select-workspace-node" && button.dataset.nodeId) {
      fn(deps, "switchWorkspaceTab", () => {})("workflow");
      fn(deps, "selectWorkspaceNode", () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "select-workspace-agent" && button.dataset.agentId) {
      fn(deps, "switchWorkspaceTab", () => {})("agents");
      fn(deps, "selectWorkspaceAgent", () => {})(button.dataset.agentId);
      return true;
    }
    if (action === "focus-workspace-goal") {
      fn(deps, "switchWorkspaceMode", () => {})("use");
      const input = element(deps, "workspaceTaskGoalInput");
      input?.focus();
      input?.scrollIntoView({ block: "center", behavior: "smooth" });
      return true;
    }
    if (action === "focus-workspace-node-kind") {
      fn(deps, "switchWorkspaceTab", () => {})("workflow");
      element(deps, "workspaceNodeKindSelect")?.focus();
      return true;
    }
    if (action === "focus-workspace-backfill-target") {
      fn(deps, "focusWorkspaceBackfillTarget", () => {})(button);
      return true;
    }
    if (action === "apply-recommended-workspace-roles") {
      fn(deps, "applyRecommendedNodeAssignments", () => {})();
      return true;
    }
    if (action === "merge-recommended-workspace-agents") {
      fn(deps, "mergeRecommendedWorkspaceAgents", () => {})();
      return true;
    }
    if (action === "add-workspace-agent") {
      fn(deps, "addWorkspaceAgent", () => {})();
      return true;
    }
    if (action === "merge-recommended-workspace-tools") {
      fn(deps, "mergeRecommendedWorkspaceTools", () => {})();
      return true;
    }
    if (action === "add-workspace-tool") {
      fn(deps, "openWorkspaceConfigDetail", () => {})("workspaceToolAdvancedDetails", { tab: "tools" });
      fn(deps, "addWorkspaceTool", () => {})();
      return true;
    }
    if (action === "add-provider-profile") {
      fn(deps, "openWorkspaceConfigDetail", () => {})("workspaceModelAdvancedDetails", { tab: "model" });
      fn(deps, "addProviderProfile", () => {})();
      return true;
    }
    if (action === "open-workspace-details") {
      const targetId = String(button.dataset.targetId || "").trim();
      fn(deps, "openWorkspaceConfigDetail", () => {})(targetId || button.closest("details")?.id || "", { tab: button.dataset.tab || "" });
      return true;
    }
    if (action === "submit-workspace-form") {
      element(deps, "workspaceForm")?.requestSubmit();
      return true;
    }
    if (action === "create-workspace") {
      void fn(deps, "createWorkspaceTask", async () => {})("create");
      return true;
    }
    if (action === "create-workspace-discover") {
      void fn(deps, "createWorkspaceTask", async () => {})("discover");
      return true;
    }
    if (action === "create-workspace-run") {
      void fn(deps, "createWorkspaceTask", async () => {})("run");
      return true;
    }
    if (action === "switch-workspace-manage") {
      const nextTab = workspaceManageTabs(deps).includes(String(button.dataset.tab || "")) ? String(button.dataset.tab) : "";
      if (nextTab && state.ui.workspaceManageTab !== nextTab) {
        state.ui.workspaceManageTab = nextTab;
        fn(deps, "markWorkspaceUiInteraction", () => {})();
        fn(deps, "saveStoredValue", () => {})(keys.workspaceManageTab, nextTab);
      }
      fn(deps, "switchWorkspaceMode", () => {})("manage");
      return true;
    }
    if (action === "open-workspace-chain-inspect") {
      fn(deps, "openWorkspaceChainInspect", () => {})();
      return true;
    }
    if (action === "open-workflow-template-studio") {
      fn(deps, "openWorkflowTemplateStudio", () => {})();
      return true;
    }
    if (action === "switch-workspace-tab") {
      const nextTab = button.dataset.tab || "home";
      if (button.dataset.mode) fn(deps, "switchWorkspaceMode", () => {})(button.dataset.mode);
      else fn(deps, "switchWorkspaceMode", () => {})("use");
      fn(deps, "switchWorkspaceTab", () => {})(nextTab);
      return true;
    }
    if (action === "select-flow-node" && button.dataset.nodeId) {
      fn(deps, "focusWorkspaceFlowCanvasNode", () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "select-flow-tool" && button.dataset.nodeId) {
      fn(deps, "selectWorkspaceFlowTool", () => {})(button.dataset.nodeId, button.dataset.toolId || "");
      return true;
    }
    if (action === "workspace-flow-zoom-in") {
      fn(deps, "setWorkspaceFlowZoom", () => {})(
        fn(deps, "workspaceFlowZoomLevel", () => 0)() + workspaceFlowCanvas(deps).zoomStep,
      );
      return true;
    }
    if (action === "workspace-flow-zoom-out") {
      fn(deps, "setWorkspaceFlowZoom", () => {})(
        fn(deps, "workspaceFlowZoomLevel", () => 0)() - workspaceFlowCanvas(deps).zoomStep,
      );
      return true;
    }
    if (action === "workspace-flow-zoom-fit") {
      fn(deps, "resetWorkspaceFlowCanvasView", () => {})({ center: true });
      return true;
    }
    if (action === "test-workspace-chain") {
      fn(deps, "testWorkspaceStarterChain", () => {})();
      return true;
    }
    if (action === "toggle-cockpit-monitor-mode") {
      fn(deps, "toggleCockpitMonitorMode", () => {})();
      fn(deps, "renderWorkspaceWorkbench", () => {})();
      return true;
    }
    if (action === "switch-workspace-mode") {
      fn(deps, "switchWorkspaceMode", () => {})(button.dataset.mode || "use");
      return true;
    }
    if (action === "focus-workspace-execution-board") {
      const workspace = selectedWorkspace(deps);
      const nodeId = String(
        button.dataset.nodeId || fn(deps, "workspaceCockpitNextAction", () => null)(workspace)?.focus_node_id || "",
      ).trim();
      fn(deps, "switchWorkspaceMode", () => {})("use");
      fn(deps, "switchWorkspaceTab", () => {})("home", { reveal: false });
      fn(deps, "revealWorkspacePanelTarget", () => {})("workspaceExecutionBoard", { block: "start" });
      if (nodeId) {
        state.selectedWorkspaceExecutionNodeId = nodeId;
        fn(deps, "saveStoredValue", () => {})(keys.selectedWorkspaceExecutionNode, nodeId);
        fn(deps, "focusWorkspaceExecutionNode", () => {})(nodeId, { targetId: "workspaceExecutionDetail", tab: "home", block: "center" });
        fn(deps, "renderWorkspaceExecutionDetail", () => {})();
      }
      return true;
    }
    if (action === "advance-workspace-automation") {
      void fn(deps, "advanceWorkspaceAutomation", async () => {})();
      return true;
    }
    if (action === "apply-workspace-automation") {
      void fn(deps, "applyWorkspaceAutomationDefaults", async () => {})();
      return true;
    }
    if (action === "apply-workspace-backfill-item") {
      void fn(deps, "applyWorkspaceBackfillItem", async () => {})(button);
      return true;
    }
    if (action === "run-workspace-discovery") {
      void fn(deps, "runWorkspaceDiscovery", async () => {})();
      return true;
    }
    if (action === "run-selected-workspace") {
      if (!fn(deps, "workspaceExecutionBundleReady", () => true)(selectedWorkspace(deps))) {
        fn(deps, "setWorkspaceMessage", () => {})("执行包未就绪，先自动推进补齐门禁。");
        void fn(deps, "advanceWorkspaceAutomation", async () => {})();
        return true;
      }
      void fn(deps, "runWorkspaceWorkflow", async () => {})();
      return true;
    }
    if (action === "run-workspace-to-selected-node" && button.dataset.nodeId) {
      void fn(deps, "runWorkspaceToNode", async () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "run-workspace-node-agent" && button.dataset.nodeId) {
      void fn(deps, "runWorkspaceNode", async () => {})(button.dataset.nodeId, { prefer: "agent" });
      return true;
    }
    if (action === "run-workspace-node-job" && button.dataset.nodeId) {
      void fn(deps, "runWorkspaceNode", async () => {})(button.dataset.nodeId, { prefer: "job" });
      return true;
    }
    if (action === "run-workspace-node" && button.dataset.nodeId) {
      void fn(deps, "runWorkspaceNode", async () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "run-selected-node" && button.dataset.nodeId) {
      void fn(deps, "runWorkspaceNode", async () => {})(button.dataset.nodeId);
      return true;
    }
    if (action === "open-selected-node-log" && button.dataset.jobId) {
      void fn(deps, "showLog", async () => {})(button.dataset.jobId);
      return true;
    }
    if (action === "open-workspace-run" && button.dataset.jobId) {
      void fn(deps, "showLog", async () => {})(button.dataset.jobId);
      return true;
    }
    if (action === "open-workspace-run" && button.dataset.runId) {
      void fn(deps, "openWorkspaceRunDetail", async () => {})(button.dataset.runId);
      return true;
    }
    if (action === "open-last-workspace-log") {
      const workspace = selectedWorkspace(deps);
      const jobId = String(button.dataset.jobId || workspace?.execution?.last_job_id || "").trim();
      if (jobId) void fn(deps, "showLog", async () => {})(jobId);
      else fn(deps, "setWorkspaceUseMessage", () => {})("当前实例还没有最近任务输出。", true);
      return true;
    }
    if (action === "accept-chat-context-reflection" && button.dataset.messageId) {
      void fn(deps, "acceptWorkspaceChatContextReflection", async () => {})(button);
      return true;
    }
    if (action === "dismiss-chat-context-reflection" && button.dataset.messageId) {
      void fn(deps, "dismissWorkspaceChatContextReflection", async () => {})(button);
      return true;
    }
    if (action === "fill-job-from-selected-workspace") {
      fn(deps, "fillJobFormFromWorkspace", () => {})();
      return true;
    }
    if (action === "refresh-workspace-resources") {
      void fn(deps, "refreshWorkspaceResourceSnapshot", async () => {})("");
      return true;
    }
    if (action === "refresh-workspace-resource-server") {
      void fn(deps, "refreshWorkspaceResourceSnapshot", async () => {})(button.dataset.serverId || "");
      return true;
    }
    if (action === "refresh-workspace-resource-selected-server") {
      const picker = button
        .closest(".workspace-cockpit-resource-actions")
        ?.querySelector("[data-role='workspace-resource-server-select']");
      void fn(deps, "refreshWorkspaceResourceSnapshot", async () => {})(picker?.value || state.ui.workspaceResourceServerId || "");
      return true;
    }
    if (action === "copy-execution-bundle-script") {
      const scriptText = button
        .closest(".workspace-execution-bundle")
        ?.querySelector("[data-role='workspace-execution-bundle-script-text']")
        ?.textContent || fn(deps, "workspaceExecutionBundleScriptText", () => "")(selectedWorkspace(deps));
      void fn(deps, "copyTextToClipboard", async () => {})(scriptText)
        .then(() => fn(deps, "setWorkspaceMessage", () => {})("执行包脚本已复制。"))
        .catch((error) => fn(deps, "setWorkspaceMessage", () => {})(error.message || "复制脚本失败。", true));
      return true;
    }
    if (action === "copy-execution-bundle-json") {
      const workspace = selectedWorkspace(deps);
      const manifest = workspace?.automation?.reproduction_manifest && typeof workspace.automation.reproduction_manifest === "object"
        ? workspace.automation.reproduction_manifest
        : {};
      const packageText = fn(deps, "workspaceExecutionBundlePackageText", () => "")(workspace, manifest);
      if (!packageText) {
        fn(deps, "setWorkspaceMessage", () => {})("还没有可复制的执行包 JSON。", true);
        return true;
      }
      void fn(deps, "copyTextToClipboard", async () => {})(packageText)
        .then(() => fn(deps, "setWorkspaceMessage", () => {})("结构化执行包 JSON 已复制。"))
        .catch((error) => fn(deps, "setWorkspaceMessage", () => {})(error.message || "复制执行包 JSON 失败。", true));
      return true;
    }
    if (action === "copy-node-execution-bundle-script") {
      const scriptText = button
        .closest(".workspace-node-execution-bundle")
        ?.querySelector("[data-role='workspace-node-execution-bundle-script']")
        ?.textContent || "";
      void fn(deps, "copyTextToClipboard", async () => {})(scriptText)
        .then(() => fn(deps, "setWorkspaceMessage", () => {})("当前节点归档脚本已复制。"))
        .catch((error) => fn(deps, "setWorkspaceMessage", () => {})(error.message || "复制脚本失败。", true));
      return true;
    }
    return false;
  }

  window.WorkspaceAutomationActions = {
    advanceMessage,
    actionHelp,
    actionLabel,
    beginAutomationAction,
    endAutomationAction,
    handleAutomationAction,
    hasAction,
    isNonBlockingAction,
    updateBusyControls,
    workflowErrorMessage,
  };
})();
