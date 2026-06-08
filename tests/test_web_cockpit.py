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
            "workspaceCockpitCards",
            "workspaceCockpitReadiness",
            "workspaceCockpitOperations",
            "workspaceExecutionBoard",
            "workspaceExecutionDetail",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_cockpit_renderers_are_wired_into_home(self) -> None:
        required_functions = [
            "workspaceLauncherPreviewMarkup",
            "workspaceStarterDecisionMarkup",
            "workspaceLaunchIntentItems",
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
            "workspaceExecutionBundleMarkup",
            "workspaceReproductionManifestMarkup",
            "workspaceCockpitTopologyMarkup",
            "workspaceCockpitResourceMatrixMarkup",
            "workspaceEvidenceBackfillMarkup",
            "workspaceExecutionChainMarkup",
            "workspaceExecutionPhaseProgressMarkup",
            "workspaceExecutionNodePosition",
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
            "workspaceIssueMeta",
            "workspaceIssueFixAction",
            "workspaceCockpitIssueMarkup",
            "refreshWorkspaceResourceSnapshot",
            "workspaceResourceServerOptions",
            "workspaceSelectedResourceServerId",
            "serverHostResourceSummary",
            "serverHostResourcePopoverMarkup",
            "serverResourceOverlayNode",
            "positionServerResourcePopover",
            "showServerResourcePopover",
            "captureWorkspaceUiSnapshot",
            "restoreWorkspaceUiSnapshot",
            "workspaceResourceSnapshotMeta",
            "workspaceItemCockpitSummary",
            "beginWorkspaceAutomationAction",
            "endWorkspaceAutomationAction",
            "renderWorkspaceCockpitOverview",
        ]

        for function_name in required_functions:
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.app)

        operations_index = self.app.index("operationsRoot.innerHTML = workspaceCockpitOperationsMarkup")
        cockpit_index = self.app.index("function workspaceCockpitOperationsMarkup")
        self.assertGreater(operations_index, cockpit_index)
        self.assertIn("workspaceLauncherPreviewMarkup(inputs, template, resources)", self.app)
        self.assertIn("workspaceStarterDecisionMarkup(inputs, template, resources)", self.app)
        self.assertIn("workspaceLaunchIntentItems(inputs, template, resources)", self.app)
        self.assertIn('workspaceLauncherDraft: "tc-workspace-launcher-draft"', self.app)
        self.assertIn("workspaceCockpitNodeRadarMarkup(workspace)", self.app)
        self.assertIn("workspaceCockpitHandoffMapMarkup(workspace)", self.app)
        self.assertIn("automation?.workflow_contract", self.app)
        self.assertIn("节点 I/O 交接图", self.app)
        self.assertIn("input_mapping / output_key / context", self.app)
        self.assertIn("workflow_contract_node", self.app)
        self.assertIn("I/O 契约", self.app)
        self.assertIn("workspaceNodeIoContractMarkup(node, sourceNode", self.app)
        self.assertIn("当前节点执行计划", self.app)
        self.assertIn("workspaceNodeExecutionPlanMarkup(workspace, node, sourceNode)", self.app)
        self.assertIn("执行上下文总线", self.app)
        self.assertIn("input_data / context.outputs / step_results", self.app)
        self.assertIn("workspaceExecutionContextBusMarkup(workspace", self.app)
        self.assertIn("复现/部署清单", self.app)
        self.assertIn("执行包", self.app)
        self.assertIn("workspaceExecutionBundleMarkup(manifest", self.app)
        self.assertIn("bundle.next_action", self.app)
        self.assertIn("action.nodeId || action.node_id", self.app)
        self.assertIn("workspaceReproductionManifestMarkup(workspace", self.app)
        self.assertIn("source / data / env / gpu / run / artifact", self.app)
        self.assertIn('data-action="select-execution-node"', self.app)
        self.assertIn('data-node-id="${escapeHtml(action.nodeId)}"', self.app)
        self.assertIn("点击定位执行节点", self.app)
        self.assertIn('data-action="${escapeHtml(action.action)}"', self.app)
        self.assertIn("workspaceManifestNextAction(manifest)", self.app)
        self.assertIn('"run-workspace-discovery"', self.app)
        self.assertIn('"run-selected-workspace"', self.app)
        self.assertIn("workspaceCockpitTopologyMarkup(workspace)", self.app)
        self.assertIn("workspaceCockpitResourceMatrixMarkup(workspace)", self.app)
        self.assertIn("workspaceAutomationStateMachineMarkup(workspace)", self.app)
        self.assertIn("自动化状态机", self.app)
        self.assertIn("workspaceCockpitIssueMarkup(item", self.app)
        self.assertIn('data-action="select-execution-node"', self.app)
        self.assertIn('data-node-id="${escapeHtml(nodeId)}"', self.app)
        self.assertIn('$("workspaceCockpitReadiness")?.addEventListener("click"', self.app)
        self.assertIn('data-action="refresh-workspace-resources"', self.app)
        self.assertIn('data-action="refresh-workspace-resource-server"', self.app)
        self.assertIn('data-action="refresh-workspace-resource-selected-server"', self.app)
        self.assertIn('data-role="workspace-resource-server-select"', self.app)
        self.assertIn("快照状态", self.app)
        self.assertIn("workspaceEvidenceBackfillMarkup(workspace", self.app)
        self.assertIn("workspaceAutomationBusyAction", self.app)
        self.assertIn("WORKSPACE_NON_BLOCKING_ACTIONS", self.app)
        self.assertIn("workspaceUiRevision", self.app)
        self.assertIn("markWorkspaceUiInteraction", self.app)
        self.assertIn("restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true })", self.app)
        self.assertIn('workspaceExecutionNodeSelections: "tc-workspace-execution-node-selections"', self.app)
        self.assertIn("box.innerHTML = workspaceExecutionChainMarkup(nodes)", self.app)
        self.assertIn("options.selectedExecutionNodeId || options.selectedNodeId", self.app)
        self.assertIn("saveWorkspaceExecutionNodeSelection(state.selectedWorkspaceExecutionNodeId", self.app)
        self.assertIn('} else if (state.ui.productTab === "workspace")', self.app)
        self.assertIn("renderWorkspaceResourceSurfaces();", self.app)
        self.assertIn("host_resources", self.app)
        self.assertIn("server-resource-popover", self.app)
        self.assertIn("serverResourceOverlay", self.app)
        self.assertIn("主机资源", self.app)

    def test_cockpit_sections_have_styles(self) -> None:
        required_classes = [
            ".workspace-launch-preview",
            ".workspace-launch-decision",
            ".workspace-launch-intent-chain",
            ".workspace-cockpit-radar",
            ".workspace-cockpit-handoff-map",
            ".workspace-cockpit-handoff-node",
            ".workspace-cockpit-handoff-io",
            ".workspace-cockpit-topology",
            ".workspace-cockpit-resource-matrix",
            ".workspace-cockpit-resource-actions",
            ".workspace-resource-server-picker",
            ".server-resource-overlay",
            ".server-resource-popover",
            ".server-resource-grid",
            ".server-resource-row",
            ".workspace-backfill-plan",
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
            ".workspace-execution-bundle",
            ".workspace-execution-bundle-actions",
            ".workspace-execution-bundle-target",
            ".workspace-execution-bundle-steps",
            ".workspace-execution-bundle-step",
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

    def test_cockpit_actions_explain_refresh_and_templates(self) -> None:
        self.assertIn("只刷新当前选中服务器的 GPU、显存、进程和连接状态", self.html)
        self.assertIn("不会重置工作台正在编辑的选项卡", self.html)
        self.assertIn("选择这次自动化实例要复制的 Starter Chain", self.html)
        self.assertIn("只刷新推荐服务器", self.app)
        self.assertIn("只刷新下拉选择的单台服务器", self.app)
        self.assertIn("不会重置工作台", self.app)
        self.assertIn("data-workspace-help", self.app)
        self.assertIn("aria-label", self.app)
        self.assertIn("[data-workspace-help]::after", self.css)
        self.assertIn('WORKSPACE_NON_BLOCKING_ACTIONS.has(action)', self.app)
        self.assertIn("captureWorkspaceUiSnapshot()", self.app)
        self.assertIn("restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true })", self.app)
        self.assertIn("Number(snapshot.workspaceUiRevision || 0) === Number(state.ui.workspaceUiRevision || 0)", self.app)


if __name__ == "__main__":
    unittest.main()
