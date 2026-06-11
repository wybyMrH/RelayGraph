from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"


class WorkbenchCockpitSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        cls.app = (WEB_DIR / "app.js").read_text(encoding="utf-8")
        cls.css = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    def test_cockpit_home_has_required_mount_points(self) -> None:
        required_ids = [
            "workspaceManageInspectSummary",
            "workspaceManageInspectChain",
            "workspaceManageInspectHandoff",
            "workspaceManageInspectGaps",
            "workspaceManageInspectReadiness",
            "workspaceLauncherPlan",
            "workspaceExecutionBoard",
            "workspaceExecutionDetail",
            "workspaceProjectModulesPanel",
            "workspaceHomeDecision",
            "workspaceHomeCockpit",
            "workspaceHomePreflight",
            "workspaceHomeContext",
            "workspaceProjectQueue",
            "workspaceWorkflowSummary",
            "workspaceAgentCoverageSummary",
            "workspaceAgentAdvancedDetails",
            "workspaceToolCatalogSummary",
            "workspaceToolAdvancedDetails",
            "workspaceModelRoutingSummary",
            "workspaceModelAdvancedDetails",
            "workspaceProjectPanel",
            "workspaceWorkflowPanel",
            "workspaceChatPanel",
            "workspaceToolsPanel",
            "workspaceModelPanel",
            "workspaceRunsPanel",
            "outputTabsActions",
            "outputCloseActiveBtn",
            "outputCloseAllBtn",
            "terminalSessionList",
            "terminalSessionMeta",
            "terminalActivitySnapshot",
            "topbarTitle",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_log_output_wraps_long_lines(self) -> None:
        self.assertIn(".log-view", self.css)
        self.assertIn(".terminal-output", self.css)
        self.assertIn("white-space: pre-wrap;", self.css)
        self.assertIn("overflow-wrap: anywhere;", self.css)
        self.assertIn("word-break: break-word;", self.css)
        self.assertIn("--output-tabs-height: 42px;", self.css)
        self.assertIn("flex: 0 0 var(--output-tabs-height);", self.css)
        self.assertIn("top: var(--output-tabs-height);", self.css)
        self.assertIn("flex-wrap: nowrap;", self.css)
        self.assertIn("scrollbar-gutter: stable both-edges;", self.css)

    def test_file_picker_supports_quick_preview_cache_actions(self) -> None:
        self.assertIn('id="filePreviewOpenBtn"', self.html)
        self.assertIn('id="filePreviewDownloadBtn"', self.html)
        self.assertIn('id="sourcePreviewBtn"', self.html)
        self.assertIn('id="transferPreviewOpenBtn"', self.html)
        self.assertIn('id="transferPreviewDownloadBtn"', self.html)
        self.assertIn('id="transferPreviewSurface"', self.html)
        self.assertIn("function filePreviewKindLabel", self.app)
        self.assertIn("function fetchFilePreviewAsset", self.app)
        self.assertIn("function previewTransferSourceInput", self.app)
        self.assertIn("function previewFileInTransfer", self.app)
        self.assertIn("sourcePreviewBtn", self.app)
        self.assertIn("data-action=\"preview-transfer-node\"", self.app)
        self.assertIn("data-action=\"preview-selected-source\"", self.app)
        self.assertIn("在源路径填单个文件后点“预览”", self.app)
        self.assertIn("triggerBrowserDownload(state.filePreview.downloadUrl", self.app)
        self.assertIn("从左侧文件树点“快览”", self.app)
        self.assertIn(".file-preview-surface", self.css)
        self.assertIn(".file-preview-surface.empty-state", self.css)
        self.assertIn('box.classList.toggle("empty-state", isEmpty);', self.app)
        self.assertIn(".transfer-side-stack", self.css)
        self.assertIn(".source-path-input-action", self.css)
        self.assertIn(".transfer-preview-box", self.css)
        self.assertIn(".transfer-preview-surface", self.css)
        self.assertIn(".file-preview-summary", self.css)
        self.assertIn(".file-preview-embed", self.css)

    def test_gpu_click_focuses_matching_process_rows(self) -> None:
        self.assertIn("processFocus", self.app)
        self.assertIn("function setProcessFocusForGpu", self.app)
        self.assertIn("function processMatchesGpuFocus", self.app)
        self.assertIn("function scrollFocusedProcessIntoView", self.app)
        self.assertIn("setProcessFocusForGpu(serverId, gpuIndex);", self.app)
        self.assertIn('data-server-id="${escapeHtml(server.id)}"', self.app)
        self.assertIn('data-gpu-index="${escapeHtml(process.gpu_index ?? "")}"', self.app)
        self.assertIn('class="process-row${focusClass}"', self.app)
        self.assertIn(".process-row.process-focus td", self.css)
        self.assertIn(".process-command-cell", self.css)
        self.assertIn("max-width: 100%;", self.css)
        self.assertNotIn("overflow: visible;\n  text-overflow: clip;", self.css)

    def test_output_tabs_have_bulk_close_and_terminal_activity_list(self) -> None:
        self.assertIn("function closeActiveOutputTab", self.app)
        self.assertIn("function closeAllOutputTabs", self.app)
        self.assertIn("function renderTerminalActivity", self.app)
        self.assertIn("function renderTerminalActivitySnapshot", self.app)
        self.assertIn("outputCloseActiveBtn", self.app)
        self.assertIn("outputCloseAllBtn", self.app)
        self.assertIn("terminalSessionList", self.app)
        self.assertIn("terminalActivitySnapshot", self.app)
        self.assertIn("data-action=\"activate-output-tab\"", self.app)
        self.assertIn("data-action=\"close-output-tab\"", self.app)
        self.assertIn(".output-tabs-actions", self.css)
        self.assertIn(".terminal-workbench", self.css)
        self.assertIn(".terminal-activity-snapshot", self.css)
        self.assertIn(".terminal-session-panel", self.css)
        self.assertIn(".terminal-session-list", self.css)
        self.assertIn(".terminal-session-item", self.css)
        self.assertIn("overflow-x: auto;", self.css)
        self.assertIn(".terminal-session-list::-webkit-scrollbar", self.css)
        self.assertIn("grid-template-rows: auto minmax(0, 1fr);", self.css)
        self.assertIn("overflow: auto;\n  padding-right: 2px;\n  scrollbar-gutter: stable;", self.css)

    def test_main_workspace_has_wheel_fallback(self) -> None:
        self.assertIn("function handleMainWheelFallback", self.app)
        self.assertIn("function closestScrollableElement", self.app)
        self.assertIn("function scrollableAncestors", self.app)
        self.assertIn("function routeWheelToElement", self.app)
        self.assertIn("function scrollElementWithinContainer", self.app)
        self.assertIn("function workspaceNearestScrollContainer", self.app)
        self.assertIn("function revealWorkspaceElement", self.app)
        self.assertIn("function elementVisibleInViewport", self.app)
        self.assertIn("function staticWheelScrollTarget", self.app)
        self.assertIn("function visibleScrollTargetWithin", self.app)
        self.assertIn("function targetShouldForceRoutedWheel", self.app)
        self.assertIn("function workspaceHeaderWheelTarget", self.app)
        self.assertIn("function handleLogPaneWheel", self.app)
        self.assertIn("focus-workspace-goal", self.app)
        self.assertIn("MAIN_WHEEL_FALLBACK_EXCLUDE_SELECTOR", self.app)
        self.assertIn("FORCE_ROUTED_WHEEL_SELECTOR", self.app)
        self.assertIn('document.addEventListener("wheel", handleMainWheelFallback, { passive: false });', self.app)
        self.assertIn('$("logPane")?.addEventListener("wheel", handleLogPaneWheel, { passive: false });', self.app)
        self.assertIn("const staticTarget = staticWheelScrollTarget(target, workspacePanel);", self.app)
        self.assertIn("const nearestScrollable = closestScrollableElement(target, workspacePanel);", self.app)
        self.assertIn("const nearestAtBoundary = nearestScrollable", self.app)
        self.assertIn("routeWheelToElement(event, scrollTarget);", self.app)
        self.assertIn("async function bootstrapStatus", self.app)
        self.assertIn("await loadStatus(false);", self.app)
        self.assertIn("void loadStatus(true, { renderWorkspace: false });", self.app)
        self.assertIn("void bootstrapStatus();", self.app)
        self.assertIn("#workspaceHubPanel, #consoleActivityPanel, #consoleExecPanel, #consoleMonitorPanel", self.app)
        self.assertIn('workspacePanel.id === "consoleActivityPanel"', self.app)
        self.assertIn('workspacePanel.id === "consoleMonitorPanel"', self.app)
        self.assertIn('const tableWrap = target.closest(".table-wrap");', self.app)
        self.assertIn("return tableWrap;", self.app)
        self.assertIn('workspacePanel.id === "workspaceHubPanel"', self.app)
        self.assertIn("#workspaceModeSwitch, #workspaceManageTabs, #workspaceTabs, .workspace-project-drawer-summary", self.app)
        self.assertIn('target.closest(".workspace-use-board > .subsection-head")', self.app)
        self.assertIn('visibleScrollTarget("#workspaceExecutionBoard")', self.app)
        self.assertIn('target.closest(".panel-head-tabs")', self.app)
        self.assertIn('workspacePanel.id === "consoleExecPanel"', self.app)
        self.assertIn('target.closest("#workspaceHubPanel > .panel-head")', self.app)
        self.assertIn("event.deltaMode === WheelEvent.DOM_DELTA_LINE", self.app)
        self.assertIn("elementVisibleInViewport(panelTableWrap, 40)", self.app)
        self.assertIn('return $("execJobPanel");', self.app)
        self.assertIn('return $("execPlanPanel");', self.app)
        self.assertIn('return $("execTransferPanel");', self.app)
        self.assertIn('return $("jobList");', self.app)
        self.assertIn('return $("tmuxList");', self.app)
        self.assertIn('return $("terminalSessionList");', self.app)
        self.assertIn('target.closest("#terminalActivitySnapshot")', self.app)
        exclusion_start = self.app.index("const MAIN_WHEEL_FALLBACK_EXCLUDE_SELECTOR")
        exclusion_end = self.app.index("].join", exclusion_start)
        exclusion_block = self.app[exclusion_start:exclusion_end]
        self.assertNotIn("#logPane", exclusion_block)
        self.assertNotIn(".server-list", exclusion_block)
        self.assertNotIn(".job-list", exclusion_block)
        self.assertNotIn(".tmux-list", exclusion_block)
        self.assertNotIn(".table-wrap", exclusion_block)

    def test_workspace_contract_input_gaps_are_visible(self) -> None:
        self.assertIn("input_refs", self.app)
        self.assertIn("missing_inputs", self.app)
        self.assertIn("input_gap_count", self.app)
        self.assertIn("input_status", self.app)
        self.assertIn("function workspaceInputStatusLabel", self.app)
        self.assertIn("function workspaceInputRefDetail", self.app)
        self.assertIn("function workspaceInputMappingToText", self.app)
        self.assertIn("function workspaceInputMappingFromText", self.app)
        self.assertIn("function normalizeWorkspaceDraftNode", self.app)
        self.assertIn("function normalizeWorkflowTemplateDraft", self.app)
        self.assertIn("function workflowTemplatePayloadForSave", self.app)
        self.assertIn("function workspaceLauncherInputsFromWorkspace", self.app)
        self.assertIn("repo_urls: listOrFallback(inputs.repo_urls, source.repo_url),", self.app)
        self.assertIn("paper_urls: listOrFallback(inputs.paper_urls, source.paper_url),", self.app)
        self.assertIn("setWorkspaceLauncherInputs(workspaceLauncherInputsFromWorkspace(workspace));", self.app)
        self.assertIn("normalized.input_mapping", self.app)
        self.assertIn("normalized.output_key", self.app)
        self.assertIn("nodes: deepClone(draft.nodes || [], []),", self.app)
        self.assertIn("输入断点", self.app)
        self.assertIn("workspace-node-io-gaps", self.app)
        self.assertIn("workspace-cockpit-handoff-gap", self.app)
        self.assertIn("workspace-orchestration-input-gap", self.app)
        self.assertIn("workspace-context-input-gap", self.app)
        self.assertIn("workspace-node-io-edit-grid", self.app)
        self.assertIn("data-node-input-mapping", self.app)
        self.assertIn("data-manage-input-mapping", self.app)
        self.assertIn('action: "open-workspace-node"', self.app)
        self.assertIn('label: "编辑映射"', self.app)
        self.assertIn("upstream_output_key", self.app)
        self.assertIn("resolved_inputs", self.app)
        self.assertIn(".workspace-node-io-gaps", self.css)
        self.assertIn(".workspace-cockpit-handoff-gap", self.css)
        self.assertIn(".workspace-orchestration-input-gap", self.css)
        self.assertIn(".workspace-context-input-gap", self.css)
        self.assertIn(".workspace-node-io-edit-grid", self.css)

    def test_workspace_save_preserves_node_command_fallbacks(self) -> None:
        self.assertIn("function workspaceRecipeCommandValueFromNodes", self.app)
        self.assertIn("function workspaceRecipeCommandValues", self.app)
        self.assertIn('if (key === "setup_command") return String(findConfig("env.prepare").setup_command || "");', self.app)
        self.assertIn('if (key === "run_command") return String(findConfig("run.command").run_command || "");', self.app)
        self.assertIn('if (key === "schedule") return String(findConfig("run.command").schedule || "");', self.app)
        self.assertIn('if (key === "report_command") return String(findConfig("eval.report").report_command || "");', self.app)
        self.assertIn("const nodeRecipeCommands = workspaceRecipeCommandValues(nodes);", self.app)
        self.assertIn("payload[key] = value;", self.app)
        self.assertIn("recipe.setup_command || nodeRecipeCommands.setup_command || \"\"", self.app)
        self.assertIn("recipe.run_command || nodeRecipeCommands.run_command || \"\"", self.app)
        self.assertIn("recipe.report_command || nodeRecipeCommands.report_command || \"\"", self.app)
        self.assertIn("recipe.schedule || nodeRecipeCommands.schedule || \"\"", self.app)
        self.assertIn("if (setupCommand.trim()) copy.config.setup_command = setupCommand;", self.app)
        self.assertIn("if (runCommand.trim()) copy.config.run_command = runCommand;", self.app)
        self.assertIn("if (schedule.trim()) copy.config.schedule = schedule;", self.app)
        self.assertIn("if (reportCommand.trim()) copy.config.report_command = reportCommand;", self.app)
        self.assertNotIn('copy.config.setup_command = String(formData.setup_command || "");', self.app)
        self.assertNotIn('copy.config.run_command = String(formData.run_command || "");', self.app)
        self.assertNotIn('copy.config.schedule = String(formData.schedule || "");', self.app)
        self.assertNotIn('copy.config.report_command = String(formData.report_command || "");', self.app)

    def test_monitor_tables_have_real_sticky_headers(self) -> None:
        self.assertIn("border-collapse: separate;", self.css)
        self.assertIn("border-spacing: 0;", self.css)
        self.assertIn(".table-wrap thead", self.css)
        self.assertIn(".table-wrap thead th", self.css)
        self.assertIn("z-index: 9;", self.css)
        self.assertIn(".process-table th:first-child", self.css)
        self.assertIn("z-index: 30;", self.css)
        self.assertIn(".gpu-panel table {\n  table-layout: fixed;", self.css)
        self.assertIn("grid-template-columns: minmax(600px, 1.04fr) minmax(520px, 0.96fr);", self.css)
        self.assertIn(".gpu-panel :is(th, td):nth-child(1) {\n  width: 96px;", self.css)
        self.assertIn("overscroll-behavior: contain;", self.css)
        self.assertIn(".activity-panel > .panel-head-tabs", self.css)
        self.assertIn(".activity-panel .subhead", self.css)
        self.assertIn(".table-wrap::-webkit-scrollbar", self.css)
        self.assertIn("function restoreScrollTop", self.app)
        self.assertIn("function tableScrollContainerForRows", self.app)
        self.assertIn("restoreScrollTop(scrollContainer, previousScrollTop);", self.app)
        self.assertIn('const tableWrap = target.closest(".table-wrap");', self.app)
        self.assertIn(".table-wrap thead tr", self.css)
        self.assertIn("z-index: 11;", self.css)
        self.assertIn('requestAnimationFrame(() => enforceProcessColumnWidthConstraints());', self.app)

    def test_top_level_pages_fill_viewport_height(self) -> None:
        self.assertIn("--monitor-panel-height: clamp(520px, calc(100dvh - 288px), 980px);", self.css)
        self.assertIn("--workspace-execution-board-height: clamp(380px, calc(100dvh - 320px - var(--active-log-pane-offset)), 680px);", self.css)
        self.assertIn("height: var(--workspace-execution-board-height);", self.css)
        self.assertIn("--workspace-mode-tabs-height: 56px;", self.css)
        self.assertIn("height: 100dvh;", self.css)
        self.assertIn("overflow: hidden;", self.css)
        self.assertIn("flex: 1 1 auto;", self.css)
        self.assertIn("flex: 1 0 var(--monitor-panel-height);", self.css)
        self.assertIn("grid-auto-rows: minmax(0, 1fr);", self.css)
        self.assertIn("grid-template-rows: minmax(0, 0.92fr) minmax(0, 1.08fr);", self.css)
        self.assertNotIn("grid-template-rows: none;", self.css)
        self.assertIn(".grid.two.monitor-grid", self.css)
        self.assertIn(".monitor-grid > .panel", self.css)
        self.assertIn("height: 100%;", self.css)
        self.assertIn("html,\nbody {\n  height: 100%;\n}", self.css)
        self.assertIn('id="mainContentArea" class="main-content-area"', self.html)
        self.assertIn("display: flex;\n  flex-direction: column;", self.css)
        self.assertIn("scrollbar-gutter: stable;", self.css)
        self.assertIn('class="workspace-scroll-shell"', self.html)
        self.assertIn(".workspace-scroll-shell", self.css)
        self.assertIn("height: 100%;\n  max-height: 100%;\n  min-height: 0;\n  overflow-x: hidden;\n  overflow-y: auto;", self.css)
        self.assertIn("scroll-padding-top: calc(var(--workspace-mode-tabs-height) + 12px);", self.css)
        self.assertIn("scroll-margin-top: calc(var(--workspace-mode-tabs-height) + 12px);", self.css)
        self.assertIn("function cssPixelValue", self.app)
        self.assertIn("const paddingTop = cssPixelValue(containerStyle?.scrollPaddingTop);", self.app)
        self.assertIn("const paddingBottom = cssPixelValue(containerStyle?.scrollPaddingBottom);", self.app)
        self.assertIn("height: var(--workspace-execution-board-height);", self.css)
        self.assertIn(".workspace-execution-phase-progress", self.css)
        self.assertIn(".workspace-execution-chain-header", self.css)
        self.assertIn("position: sticky;\n  top: 0;\n  z-index: 8;", self.css)
        self.assertIn("grid-template-rows: auto minmax(0, 1fr);", self.css)
        self.assertIn('id="workspaceModeSwitch" class="segmented-tabs workspace-mode-switch"', self.html)
        self.assertIn('id="workspaceProjectConfigDrawer" class="workspace-project-drawer"', self.html)
        self.assertIn(".workspace-project-drawer[hidden]", self.css)
        self.assertIn("top: var(--workspace-mode-tabs-height);", self.css)
        self.assertIn("--workspace-project-drawer-summary-height: 64px;", self.css)
        self.assertIn(".workspace-project-modules > .workspace-tabs", self.css)
        self.assertIn("top: calc(var(--workspace-mode-tabs-height) + var(--workspace-project-drawer-summary-height));", self.css)
        drawer_start = self.css.index(".workspace-project-drawer {")
        drawer_end = self.css.index(".workspace-project-drawer[hidden]", drawer_start)
        drawer_block = self.css[drawer_start:drawer_end]
        self.assertIn("overflow: visible;", drawer_block)
        self.assertIn("position: sticky;\n  top: var(--workspace-mode-tabs-height);", self.css)
        modules_start = self.html.index('id="workspaceProjectModulesPanel"')
        tabs_index = self.html.index('id="workspaceTabs"', modules_start)
        editor_index = self.html.index('<section class="workspace-editor">', modules_start)
        self.assertLess(tabs_index, editor_index)
        self.assertIn("@media (min-width: 721px) and (max-width: 1080px)", self.css)
        self.assertIn("--sidebar-width: 240px;", self.css)
        self.assertIn("grid-template-columns: repeat(5, minmax(0, 1fr));", self.css)
        self.assertIn("@media (min-width: 1180px) and (max-width: 1359px)", self.css)
        self.assertIn("@media (max-width: 1179px)", self.css)
        self.assertIn(".workspace-panel > .tab-panel {\n  min-height: 0;\n  overflow: auto;", self.css)
        self.assertIn("position: sticky;\n  top: 0;", self.css)
        self.assertIn(".workspace-use-board > .subsection-head", self.css)
        self.assertIn(".workspace-use-detail > .subsection-head", self.css)
        self.assertIn(".workspace-use-history > .subsection-head", self.css)
        self.assertIn("top: var(--workspace-mode-tabs-height);", self.css)
        self.assertIn("overflow-anchor: none;", self.css)
        self.assertIn("display: none !important;", self.css)
        self.assertIn(".activity-panel .job-list,\n.activity-panel .tmux-list", self.css)
        self.assertIn("#activityTasksPanel {\n  display: grid;\n  grid-template-rows: auto minmax(0, 1fr);\n  min-height: 0;\n  overflow: hidden;", self.css)
        self.assertIn(".main {\n  padding: var(--main-padding) var(--main-padding) 0;", self.css)
        self.assertIn("body.has-log-pane .main {\n  padding-bottom: 0;\n}", self.css)
        self.assertIn("body.has-log-pane .main-content-area", self.css)
        self.assertIn("padding-bottom: 0;", self.css)
        self.assertIn(".main-content-area::after", self.css)
        self.assertIn(".bottom-pane", self.css)
        self.assertIn("body.has-log-pane {\n  --monitor-panel-height: clamp(300px, calc(100dvh - 288px - var(--active-log-pane-offset)), 640px);", self.css)
        self.assertIn("position: relative;\n  inset: auto;", self.css)
        self.assertIn("flex: 0 0 clamp(260px, 36vh, var(--log-pane-height));", self.css)
        self.assertIn("height: clamp(260px, 36vh, var(--log-pane-height));", self.css)
        self.assertIn("Math.max(0, rect.height) + 12", self.app)
        self.assertNotIn(
            "padding-bottom: max(calc(var(--main-padding) + var(--log-pane-height) + 16px), var(--active-log-pane-offset));",
            self.css,
        )

    def test_cockpit_renderers_are_wired_into_home(self) -> None:
        required_functions = [
            "workspaceLauncherPreviewMarkup",
            "workspaceStarterDecisionMarkup",
            "workspaceLaunchIntentItems",
            "workspaceLaunchModeItems",
            "workspaceLaunchModeImpactMarkup",
            "workspaceLauncherContractItems",
            "workspaceLauncherContractMatrixMarkup",
            "workspaceLauncherPlanMarkup",
            "saveWorkspaceLauncherDraft",
            "restoreWorkspaceLauncherDraft",
            "workspaceCockpitNodeRadarMarkup",
            "workspaceCockpitHandoffMapMarkup",
            "workspaceCockpitHandoffItems",
            "workspaceNodeIoContract",
            "workspaceNodeIoFallbackMapping",
            "workspaceNodeWorkflowContractNode",
            "workspaceNodeIoContractState",
            "workspaceNodeIoContractMarkup",
            "workspaceExecutionContextBusMarkup",
            "workspaceManifestItemAction",
            "workspaceManifestActionButton",
            "workspaceManifestNextAction",
            "workspaceExecutionBundlePackage",
            "workspaceExecutionBundlePackageText",
            "workspaceExecutionBundleScriptText",
            "workspaceDatasetDiscoveryPlanMarkup",
            "workspaceDeploymentPlanMarkup",
            "workspaceExecutionBundleMarkup",
            "workspaceDeliveryContractMarkup",
            "workspaceReproductionManifestMarkup",
            "copyTextToClipboard",
            "workspaceOrchestrationContractMarkup",
            "workspaceCockpitTopologyMarkup",
            "workspaceCockpitResourceMatrixMarkup",
            "workspaceEvidenceBackfillMarkup",
            "workspaceExecutionChainMarkup",
            "workspaceExecutionChainSourceNodes",
            "workspaceExecutionChainNodeFacts",
            "workspaceExecutionChainOverviewItems",
            "workspaceExecutionChainOverviewMarkup",
            "workspaceExecutionChainHeaderMarkup",
            "workspaceExecutionChainStructureMarkup",
            "workspaceHomeExecutionRoadmapStageDefinitions",
            "workspaceHomeExecutionRoadmapStageItems",
            "workspaceHomeExecutionRoadmapMarkup",
            "workspaceResponsibilityResourceKey",
            "workspaceNodeResourceItem",
            "workspaceNodeReadinessBlockers",
            "workspaceHomeResponsibilityMatrixItems",
            "workspaceHomeResponsibilityMatrixMarkup",
            "workspaceAgentLayerBusItems",
            "workspaceAgentLayerBusMarkup",
            "workspaceCapabilityBaselineMarkup",
            "workspaceHomeLayerSummaryMarkup",
            "workspaceHomeLayeringMarkup",
            "workspaceHomeContextMarkup",
            "workspaceJobGpuLabel",
            "workspaceHomeRunDetailItemMarkup",
            "workspaceHomeRunsMarkup",
            "workspaceRuntimeBlueprintItems",
            "workspaceRuntimeBlueprintMarkup",
            "workspaceReproductionPipelineItems",
            "workspaceReproductionPipelineMarkup",
            "workspaceAutomationGapQueueItems",
            "workspaceAutomationGapQueueMarkup",
            "workspaceExecutionPhaseProgressMarkup",
            "workspaceExecutionNodePosition",
            "workspaceExecutionNodeGate",
            "workspaceNodeAutomationItemsByKind",
            "workspaceNodeAgentContractMarkup",
            "workspaceNodeAutomationScopeMarkup",
            "workspaceNodeNextActionMarkup",
            "workspaceNodeExecutionPlanItems",
            "workspaceNodeExecutionPlanActions",
            "workspaceNodeExecutionPlanButton",
            "workspaceNodeExecutionPlanMarkup",
            "workspaceStateMachineCurrentStepId",
            "workspaceStateMachineActionForStep",
            "workspaceStateMachineActionButton",
            "workspaceAutomationStateMachineMarkup",
            "workspaceAutomationPlaybookMarkup",
            "workspaceIssueMeta",
            "workspaceIssueFixAction",
            "workspaceCockpitIssueMarkup",
            "refreshWorkspaceResourceSnapshot",
            "workspaceResourceServerOptions",
            "workspaceSelectedResourceServerId",
            "workspaceSchedulerDecisionMarkup",
            "workspaceFirstNodeByKinds",
            "workspaceSchedulingFocusAttrs",
            "selectWorkspaceSchedulerCandidate",
            "workspaceSchedulingClosureItems",
            "workspaceSchedulingClosureMarkup",
            "workspaceSchedulingTemplateItems",
            "workspaceSchedulingStatus",
            "workspaceJobExecutionBundle",
            "workspaceJobExecutionBundleMarkup",
            "workspaceNodeExecutionBundle",
            "workspaceNodeExecutionBundleMarkup",
            "serverHostResourceSummary",
            "serverHostResourcePopoverMarkup",
            "serverResourceOverlayNode",
            "workspaceFloatingViewportBounds",
            "flashWorkspaceFocus",
            "revealWorkspacePanelTarget",
            "revealWorkspaceExecutionNode",
            "focusWorkspaceExecutionNode",
            "syncLogPaneMetrics",
            "positionServerResourcePopover",
            "showServerResourcePopover",
            "workspaceHelpOverlayNode",
            "positionWorkspaceHelpPopover",
            "showWorkspaceHelpPopover",
            "captureWorkspaceUiSnapshot",
            "restoreWorkspaceUiSnapshot",
            "workspaceResourceSnapshotMeta",
            "workspaceItemCockpitSummary",
            "workspaceProjectQueueMarkup",
            "workspaceWorkflowSummaryMarkup",
            "renderWorkspaceWorkflowSummary",
            "workspaceAgentCoverageSummaryMarkup",
            "workspaceModelRoutingSummaryMarkup",
            "workspaceHomeCockpitMarkup",
            "workspaceExecutionPackageSummaryMarkup",
            "workspaceLauncherPrecreateContractItems",
            "workspaceLauncherPrecreateContractMarkup",
            "workspaceLauncherDetailsMarkup",
            "workspaceHomeResourceSummaryMarkup",
            "workspaceHomeResourceSchedulingMarkup",
            "workspaceAutomationDecisionModel",
            "workspaceAutomationDecisionMarkup",
            "workspaceCommandCenterModel",
            "workspaceCockpitNextAction",
            "workspaceCockpitChainMarkup",
            "workspaceNextActionUiButton",
            "workspaceCommandCenterModelFromCockpit",
            "openWorkspaceChainInspect",
            "focusWorkspaceCockpitFromNextAction",
            "workspaceCommandCenterGoalItems",
            "workspaceCommandCenterBlockerSummary",
            "workspaceCommandCenterMainlineItems",
            "workspaceCommandCenterMainlineMarkup",
            "workspaceCommandCenterContractMarkup",
            "workspaceManageAction",
            "workspaceAutomationClosureItems",
            "workspaceCommandCenterClosureMarkup",
            "workspaceCommandCenterMarkup",
            "workspaceDetailClosureItems",
            "workspaceDetailClosureMarkup",
            "workspaceHomePreflightMarkup",
            "workspaceHomePreflightActionMarkup",
            "workspaceHomeActionButtonMarkup",
            "workspaceHomeCurrentPlaybookItem",
            "workspaceAgentExecutionTraceMarkup",
            "workspaceHandoffInputSummary",
            "beginWorkspaceAutomationAction",
            "endWorkspaceAutomationAction",
            "runWorkspaceToNode",
            "renderWorkspaceCockpitOverview",
            "renderWorkspaceChainInspectPanel",
            "renderWorkspaceUseLauncherSurfaces",
            "renderWorkspaceUseMonitor",
            "workspaceUseMonitorMarkup",
            "workspaceUseDetailCompactMarkup",
            "renderWorkspaceLauncherPlan",
            "workspaceLaunchCompactStepLabel",
        ]

        for function_name in required_functions:
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.app)

        inspect_index = self.app.index("function renderWorkspaceChainInspectPanel")
        cockpit_index = self.app.index("function workspaceCockpitChainMarkup")
        self.assertGreater(inspect_index, cockpit_index)
        launcher_plan_index = self.app.index("function renderWorkspaceLauncherPlan")
        cockpit_overview_index = self.app.index("function renderWorkspaceCockpitOverview")
        self.assertLess(launcher_plan_index, cockpit_overview_index)
        self.assertIn('class="workspace-use-cockpit-shell"', self.html)
        self.assertIn('class="workspace-use-launcher-panel"', self.html)
        self.assertIn('class="workspace-use-status-panel"', self.html)
        self.assertIn('id="workspaceUseMonitor" class="workspace-use-monitor-shell"', self.html)
        self.assertIn('id="workspaceLauncherPlan" class="workspace-launcher-plan"', self.html)
        self.assertIn('id="workspaceCapabilityBaseline" class="workspace-capability-baseline"', self.html)
        self.assertIn('class="workspace-use-support-band workspace-home-collapse workspace-use-support-collapse"', self.html)
        self.assertIn("renderWorkspaceUseMonitor(", self.app)
        self.assertIn("root.innerHTML = workspaceUseMonitorMarkup", self.app)
        self.assertIn("capabilityBaseline.innerHTML = baselineMarkup", self.app)
        self.assertIn("renderWorkspaceLauncherPlan(inputs, template, resources);", self.app)
        self.assertIn('"workspaceUseMonitor"', self.app)
        self.assertIn('"workspaceLauncherPlan"', self.app)
        self.assertIn('"workspaceCapabilityBaseline"', self.app)
        self.assertIn(".workspace-use-cockpit-shell {\n  display: grid;", self.css)
        self.assertIn("gap: 16px 18px;", self.css)
        self.assertIn(".workspace-use-status-panel .workspace-launcher-plan-shell {\n  grid-template-columns: 1fr;", self.css)
        self.assertIn(".workspace-use-status-panel .workspace-home-decision,\n.workspace-use-status-panel .workspace-launcher-plan {\n  display: none;", self.css)
        self.assertIn(".workspace-use-monitor {", self.css)
        self.assertIn("workspace-execution-board-compact", self.html)
        self.assertIn("compact: true", self.app)
        self.assertIn("workspaceExecutionCanvasMarkup", self.app)
        self.assertIn("focusWorkspaceFlowCanvasNode", self.app)
        self.assertIn("workspace-flow-zoom-fit", self.app)
        self.assertIn("workspace-execution-flow-viewport", self.app)
        self.assertIn("workspace-flow-node", self.app)
        self.assertIn("workspace-flow-track", self.app)
        self.assertIn("workspaceExecutionToolsColumn", self.app)
        self.assertIn("workspace-execution-inspector", self.html)
        self.assertIn("workspaceAgentOutputPanel", self.html)
        self.assertIn("select-flow-tool", self.app)
        self.assertIn("refreshWorkspaceExecutionFlowCanvas", self.app)
        self.assertIn("bindWorkspaceExecutionFlowCanvas", self.app)
        self.assertIn("toggleCockpitMonitorMode(true)", self.app)
        self.assertIn('id="workspaceCockpitMonitorToggle"', self.html)
        self.assertIn('data-action="toggle-cockpit-monitor-mode"', self.html)
        self.assertIn('id="transferConflictModal"', self.html)
        self.assertIn(".workspace-execution-flow-viewport {", self.css)
        self.assertIn(".workspace-flow-track {", self.css)
        self.assertIn(".workspace-execution-inspector-grid {", self.css)
        self.assertIn(".workspace-execution-tools-list {", self.css)
        self.assertIn(".workspace-flow-node {", self.css)
        self.assertIn("@media (max-width: 1179px) {\n  .workspace-use-cockpit-shell {\n    grid-template-columns: 1fr;", self.css)
        self.assertIn("@media (max-width: 720px) {\n  .workspace-use-input-grid,\n  .workspace-use-launcher-panel .workspace-use-template-grid {\n    grid-template-columns: 1fr;", self.css)
        self.assertEqual(self.html.count('id="workspaceCreateRunTaskBtn"'), 1)
        self.assertIn('workspace-execution-inspector-chat', self.html)
        self.assertIn('class="workspace-use-drawer workspace-use-history workspace-use-history-standalone"', self.html)
        self.assertIn(".workspace-use-drawer > summary", self.css)
        self.assertIn(".workspace-cockpit-band {\n  display: none;", self.css)
        self.assertIn('data-tab="inspect"', self.html)
        self.assertIn('id="workspaceManageInspectPanel"', self.html)
        self.assertIn("完整链路检查", self.html)
        self.assertIn('id="workspaceTaskGoalInput" rows="3"', self.html)
        self.assertIn("@media (min-width: 1081px) and (max-width: 1359px) {", self.css)
        self.assertIn("@media (max-width: 1359px) {\n  .workspace-execution-board {\n    grid-template-columns: 1fr;", self.css)
        self.assertIn("const showDetails = !monitorMode && options.showDetails === true;", self.app)
        self.assertIn("showDetails && details", self.app)
        self.assertIn("const showBlockers = !monitorMode && blockers.length && (workspace?.id || options.showBlockers === true);", self.app)
        self.assertIn("showBlockers ? `", self.app)
        self.assertIn("height: 118px;", self.css)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));", self.css)
        self.assertIn(".workspace-capability-baseline-card", self.css)
        self.assertIn(".workspace-capability-baseline-facts", self.css)
        self.assertIn(".workspace-command-center-facts {\n  display: grid;", self.css)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", self.css)
        self.assertIn("@media (max-width: 1080px) {\n  .workspace-use-grid {\n    grid-template-columns: 1fr;", self.css)
        self.assertIn(".form-message:empty", self.css)
        self.assertIn('String(text || "") === "not found"', self.app)
        self.assertIn("workspaceLauncherPreviewMarkup(inputs, template, resources, { includeDecision: false })", self.app)
        self.assertIn("workspaceLauncherPrecreateContractMarkup(inputs, template, resources", self.app)
        self.assertIn("workspaceLauncherPrecreateContractMarkup(inputs, template, resources, { compact: options.compact })", self.app)
        self.assertIn("workspaceLaunchModeImpactMarkup(inputs, template, resources)", self.app)
        self.assertIn("workspaceLauncherContractMatrixMarkup(template)", self.app)
        self.assertIn("workspaceExecutionNodeSummaryMarkup", self.app)
        self.assertIn("workspace-execution-inspector-node", self.html)
        self.assertIn("输入/数据", self.app)
        self.assertIn("Agent/Tool/AI", self.app)
        self.assertIn("scheduler_binding", self.app)
        self.assertIn("scheduler_reasons", self.app)
        self.assertIn("选择原因", self.app)
        self.assertIn(".workspace-detail-closure", self.css)
        self.assertIn(".workspace-detail-closure-card", self.css)
        self.assertIn("启动闭环", self.app)
        self.assertIn('"Starter Chain": "链路"', self.app)
        self.assertIn("创建前启动契约", self.app)
        self.assertIn("输入 → 链路 → 发现 → 资源/GPU → 执行包", self.app)
        self.assertIn("执行包会汇总 cwd、环境、GPU、运行入口", self.app)
        self.assertIn("data-workspace-help", self.app)
        self.assertIn("workspaceExecutionNodeGate(workspace, node, sourceNode, options)", self.app)
        self.assertIn('class="workspace-execution-card-gate status-${escapeHtml(gate.status || "draft")}"', self.app)
        self.assertIn("可安全发现", self.app)
        self.assertIn("等待 GPU/主机", self.app)
        self.assertIn(".workspace-execution-card-gate", self.css)
        self.assertIn(".workspace-execution-card-gate.status-blocked", self.css)
        self.assertIn('class="workspace-launch-contract-node status-${escapeHtml(item.status)}${selectedNodeId === item.id ? " active" : ""}"', self.app)
        self.assertIn('data-action="select-execution-node"', self.app)
        self.assertIn('data-node-id="${escapeHtml(item.id)}"', self.app)
        self.assertIn('data-target-id="workspaceExecutionBoard"', self.app)
        self.assertIn('aria-label="${escapeHtml(`定位节点 ${item.index}：${item.title}`)}"', self.app)
        self.assertIn("#workspaceLauncherPlan [data-action=\"select-execution-node\"]", self.app)
        self.assertIn("function workspaceDetailActionsMarkup", self.app)
        self.assertIn("workspaceUseDetailCompactMarkup", self.app)
        self.assertIn(".workspace-detail-drawer > summary", self.css)
        self.assertIn("自动化驾驶舱", self.html)
        self.assertIn("项目配置 / 高级编辑", self.html)
        self.assertIn("workspaceProjectConfigOpen", self.app)
        self.assertIn("syncWorkspaceProjectConfigDrawer", self.app)
        self.assertIn('id="workspaceProjectModulesPanel" class="workspace-grid workspace-project-modules"', self.html)
        self.assertNotIn("workspace-legacy-grid", self.html)
        self.assertNotIn(".workspace-legacy-grid", self.css)
        self.assertIn('$("workspaceProjectModulesPanel")?.toggleAttribute("hidden", mode !== "use");', self.app)
        self.assertIn('$("workspaceProjectConfigDrawer")?.addEventListener("toggle"', self.app)
        self.assertEqual(self.html.count('id="workspaceHistoryMeta"'), 1)
        self.assertEqual(self.html.count('id="workspaceProjectListMeta"'), 1)
        self.assertEqual(self.html.count('id="workspaceMeta"'), 0)
        self.assertIn('id="workspaceManageInspectPanel"', self.html)
        self.assertIn("完整链路检查", self.html)
        self.assertIn("renderWorkspaceChainInspectPanel()", self.app)
        self.assertIn("renderWorkspaceUseLauncherSurfaces();", self.app)
        self.assertIn("open-workspace-chain-inspect", self.app)
        self.assertIn("function openWorkspaceChainInspect", self.app)

    def test_cockpit_sections_have_styles(self) -> None:
        required_classes = [
            ".workspace-launch-preview",
            ".workspace-use-launcher-grid",
            ".workspace-launcher-plan",
            ".workspace-launcher-plan-shell",
            ".workspace-launcher-details",
            ".workspace-launcher-details-shell",
            ".workspace-launch-start-summary",
            ".workspace-launch-start-spine",
            ".workspace-launch-start-step",
            ".workspace-launch-start-focus",
            ".workspace-chain-structure",
            ".workspace-cockpit-blueprint",
            ".workspace-repro-pipeline-board",
            ".workspace-repro-pipeline-rail",
            ".workspace-repro-pipeline-stage",
            ".workspace-repro-pipeline-actions",
            ".workspace-cockpit-handoff",
            ".workspace-runtime-blueprint",
            ".workspace-runtime-blueprint-grid",
            ".workspace-runtime-blueprint-card",
            ".workspace-cockpit-chain",
            ".workspace-chain-structure-phases",
            ".workspace-chain-structure-node",
            ".workspace-launch-decision",
            ".workspace-launch-intent-chain",
            ".workspace-launch-precreate-contract",
            ".workspace-launch-precreate-head",
            ".workspace-launch-precreate-flow",
            ".workspace-launch-precreate-step",
            ".workspace-launch-mode-panel",
            ".workspace-launch-mode-grid",
            ".workspace-launch-mode-card",
            ".workspace-launch-contract-matrix",
            ".workspace-launch-contract-grid",
            ".workspace-launch-contract-node",
            ".workspace-launch-contract-node:hover",
            ".workspace-launch-contract-node:focus-visible",
            ".workspace-launch-contract-node.active",
            ".workspace-cockpit-radar",
            ".workspace-cockpit-handoff-map",
            ".workspace-cockpit-handoff-node",
            ".workspace-cockpit-handoff-io",
            ".workspace-cockpit-topology",
            ".workspace-orchestration-contract",
            ".workspace-orchestration-lanes",
            ".workspace-orchestration-lane",
            ".workspace-orchestration-node",
            ".workspace-cockpit-resource-matrix",
            ".workspace-scheduler-decision",
            ".workspace-scheduler-candidates",
            ".workspace-scheduler-candidate",
            ".workspace-scheduler-candidate:hover",
            ".workspace-scheduler-candidate:focus-within",
            ".workspace-scheduler-candidate-main:focus-visible",
            ".workspace-scheduler-candidate.active",
            ".workspace-playbook",
            ".workspace-home-decision",
            ".workspace-command-center",
            ".workspace-command-center-main",
            ".workspace-command-center-stage",
            ".workspace-command-center-actions",
            ".workspace-command-center-closure",
            ".workspace-command-center-closure-item",
            ".workspace-command-center-details",
            ".workspace-command-center-goal-grid",
            ".workspace-home-collapse",
            ".workspace-home-collapse-body",
            ".workspace-automation-decision",
            ".workspace-automation-decision-grid",
            ".workspace-automation-decision-fact",
            ".workspace-automation-decision-blockers",
            ".workspace-playbook-steps",
            ".workspace-playbook-step",
            ".workspace-home-cockpit",
            ".workspace-home-cockpit-card",
            ".workspace-home-cockpit-card-actions",
            ".workspace-home-roadmap",
            ".workspace-home-roadmap-head",
            ".workspace-home-roadmap-rail",
            ".workspace-home-roadmap-spine",
            ".workspace-home-roadmap-step",
            ".workspace-home-roadmap-focus",
            ".workspace-home-roadmap-detail-grid",
            ".workspace-home-roadmap-stage",
            ".workspace-home-roadmap-node",
            ".workspace-home-roadmap-actions",
            ".workspace-home-resource-scheduling",
            ".workspace-home-resource-summary",
            ".workspace-home-resource-spine",
            ".workspace-home-resource-step",
            ".workspace-home-resource-focus",
            ".workspace-home-resource-details",
            ".workspace-home-resource-empty",
            ".workspace-home-layering",
            ".workspace-home-layer-summary",
            ".workspace-home-layer-spine",
            ".workspace-home-layer-step",
            ".workspace-home-layer-focus",
            ".workspace-home-layer-details",
            ".workspace-home-run-summary",
            ".workspace-home-run-spine",
            ".workspace-home-run-step",
            ".workspace-home-run-focus",
            ".workspace-home-run-details",
            ".workspace-home-run-detail-list",
            ".workspace-home-context",
            ".workspace-home-context-summary",
            ".workspace-home-context-grid",
            ".workspace-home-context-item",
            ".workspace-home-context-focus",
            ".workspace-home-context-details",
            ".workspace-project-queue",
            ".workspace-project-queue-summary",
            ".workspace-project-queue-grid",
            ".workspace-project-queue-chip",
            ".workspace-project-queue-focus",
            ".workspace-project-list-details",
            ".workspace-workflow-summary",
            ".workspace-workflow-brief",
            ".workspace-workflow-phase-spine",
            ".workspace-workflow-phase-step",
            ".workspace-workflow-focus",
            ".workspace-agent-coverage-summary",
            ".workspace-agent-coverage-card",
            ".workspace-agent-coverage-grid",
            ".workspace-agent-coverage-chip",
            ".workspace-agent-coverage-focus",
            ".workspace-panel-details",
            ".workspace-panel-details-body",
            ".workspace-tool-summary-overview",
            ".workspace-tool-summary-head",
            ".workspace-tool-summary-grid",
            ".workspace-tool-summary-actions",
            ".workspace-model-routing-summary",
            ".workspace-model-routing-card",
            ".workspace-model-routing-head",
            ".workspace-model-routing-grid",
            ".workspace-model-routing-chip",
            ".workspace-model-routing-focus",
            ".workspace-home-preflight",
            ".workspace-preflight",
            ".workspace-preflight-head",
            ".workspace-preflight-grid",
            ".workspace-preflight-item",
            ".workspace-preflight-tags",
            ".workspace-preflight-item-actions",
            ".workspace-agent-execution-trace",
            ".workspace-agent-execution-summary",
            ".workspace-agent-execution-step",
            ".workspace-detail-closure",
            ".workspace-detail-closure-card",
            ".workspace-cockpit-resource-actions",
            ".workspace-resource-server-picker",
            ".workspace-run-package",
            ".workspace-node-execution-bundle",
            ".workspace-node-execution-bundle-grid",
            "body.has-log-pane .workspace-use-detail > .workspace-execution-detail",
            ".server-resource-overlay",
            ".server-resource-popover",
            ".server-resource-grid",
            ".server-resource-row",
            ".workspace-help-overlay",
            ".workspace-backfill-plan",
            ".workspace-execution-chain-header",
            ".workspace-execution-overview",
            ".workspace-execution-overview-item",
            ".workspace-execution-phase",
            ".workspace-execution-phase-progress",
            ".workspace-node-contract",
            ".workspace-node-io-contract",
            ".workspace-node-io-summary",
            ".workspace-node-io-map",
            ".workspace-node-io-runtime",
            ".workspace-context-bus",
            ".workspace-context-bus-metrics",
            ".workspace-context-output-rail",
            ".workspace-context-step-list",
            ".workspace-manifest",
            ".workspace-manifest-head-actions",
            ".workspace-manifest-items",
            ".workspace-manifest-item-actions",
            ".workspace-manifest-commands",
            ".workspace-delivery-contract",
            ".workspace-delivery-contract-head",
            ".workspace-delivery-contract-grid",
            ".workspace-deployment-plan",
            ".workspace-deployment-plan-head",
            ".workspace-deployment-plan-facts",
            ".workspace-deployment-plan-commands",
            ".workspace-deployment-plan-missing",
            ".workspace-dataset-discovery",
            ".workspace-dataset-discovery-head",
            ".workspace-dataset-discovery-metrics",
            ".workspace-dataset-discovery-grid",
            ".workspace-execution-package-summary",
            ".workspace-execution-package-head",
            ".workspace-execution-package-actions",
            ".workspace-execution-package-facts",
            ".workspace-execution-package-flow",
            ".workspace-execution-package-step",
            ".workspace-execution-package-missing",
            ".workspace-execution-bundle",
            ".workspace-execution-bundle-actions",
            ".workspace-execution-bundle-target",
            ".workspace-execution-bundle-steps",
            ".workspace-execution-bundle-step",
            ".workspace-execution-bundle-script",
            ".workspace-execution-bundle-script-head",
            ".workspace-execution-bundle-missing-item",
            ".workspace-node-scope",
            ".workspace-node-next-action",
            ".workspace-node-execution-plan",
            ".workspace-node-execution-plan-grid",
            ".workspace-state-machine",
            ".workspace-state-machine-rail",
            ".workspace-state-step",
            ".workspace-item-cockpit",
        ]

        for class_name in required_classes:
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.css)

        self.assertIn("--active-log-pane-offset", self.css)
        self.assertIn("scroll-padding-bottom: 18px;", self.css)

    def test_cockpit_actions_explain_refresh_and_templates(self) -> None:
        self.assertIn("只刷新当前选中服务器的 GPU、显存、进程和连接状态", self.html)
        self.assertIn("不会重置工作台正在编辑的选项卡", self.html)
        self.assertIn("链路模板", self.html)
        self.assertIn("只刷新推荐服务器", self.app)
        self.assertIn("只刷新下拉选择的单台服务器", self.app)
        self.assertIn("不会重置工作台", self.app)
        self.assertIn("复制结构化执行包 JSON", self.app)
        self.assertIn("结构化执行包 JSON 已复制", self.app)
        self.assertIn("data-workspace-help", self.app)
        self.assertIn("aria-label", self.app)
        self.assertIn("workspaceHelpOverlayNode", self.app)
        self.assertIn(".workspace-help-overlay", self.css)
        self.assertIn("max-height: min(180px, calc(100dvh - 24px));", self.css)
        self.assertIn("overscroll-behavior: contain;", self.css)
        self.assertIn("grid-auto-flow: column;", self.css)
        self.assertIn("grid-auto-columns: minmax(260px, 340px);", self.css)
        self.assertIn("function workspaceFloatingViewportBounds", self.app)
        self.assertIn("const visualViewport = window.visualViewport;", self.app)
        self.assertIn("const availableHeight = Math.max(48, bounds.height);", self.app)
        self.assertIn("const availableWidth = Math.max(180, bounds.width);", self.app)
        self.assertIn("paneOverlapsViewport", self.app)
        self.assertIn("paneTop - margin", self.app)
        self.assertIn("anchorRect.bottom < bounds.top - margin || anchorRect.top > bounds.bottom + margin", self.app)
        self.assertIn('WORKSPACE_NON_BLOCKING_ACTIONS.has(action)', self.app)
        self.assertIn("captureWorkspaceUiSnapshot()", self.app)
        self.assertIn("restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true })", self.app)
        self.assertIn("Number(snapshot.workspaceUiRevision || 0) === Number(state.ui.workspaceUiRevision || 0)", self.app)
        self.assertIn("PRODUCT_HEADER_TITLES", self.app)
        self.assertIn("function updateProductHeaderTitle", self.app)
        self.assertIn("工作台驾驶舱", self.app)
        self.assertIn("/styles.css?v=20260611cockpit11", self.html)
        self.assertIn("/app.js?v=20260611cockpit11", self.html)
        self.assertIn(".workspace-home-decision .workspace-command-center-facts", self.css)
        self.assertIn(".workspace-command-center-contract", self.css)
        self.assertIn(".workspace-use-intake .workspace-use-template-band", self.css)
        self.assertIn('const tabAttr = button.tab ? ` data-tab="${escapeHtml(button.tab)}"` : "";', self.app)
        self.assertIn('data-tab="${escapeHtml(action.tab)}"', self.app)
        self.assertIn("WORKSPACE_MANAGE_TABS.includes(String(button.dataset.tab || \"\"))", self.app)
        self.assertIn("workspaceCommandCenterClosureMarkup(workspace, options)", self.app)
        self.assertIn("发现证据", self.app)
        self.assertIn("字段回填", self.app)
        self.assertIn("资源调度", self.app)
        self.assertIn("执行包", self.app)
        self.assertIn('action: "run-workspace-discovery"', self.app)
        self.assertIn('action: "apply-workspace-automation"', self.app)
        self.assertIn('action: "refresh-workspace-resources"', self.app)
        self.assertIn('action: bundle.ready_to_execute ? "run-selected-workspace"', self.app)
        self.assertIn("workspaceExecutionChainHeaderMarkup(nodes, groups", self.app)
        self.assertIn("当前焦点", self.app)
        self.assertIn("下一节点", self.app)
        self.assertIn("门禁/卡点", self.app)
        self.assertIn("链路完整度", self.app)
        self.assertIn(".workspace-execution-chain-header", self.css)
        self.assertIn(".workspace-execution-overview-item", self.css)
        self.assertIn(".workspace-empty-state-compact", self.css)


if __name__ == "__main__":
    unittest.main()
