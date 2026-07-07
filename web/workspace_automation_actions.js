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
    handleAutomationAction,
  };
})();
