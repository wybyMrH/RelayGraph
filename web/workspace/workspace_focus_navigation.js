(function () {
  "use strict";

  function elementById(deps = {}, id = "") {
    const lookup = typeof deps.element === "function" ? deps.element : (value) => document.getElementById(value);
    return lookup(id);
  }

  function flashWorkspaceFocus(element) {
    if (!element) return;
    element.classList.remove("workspace-focus-pulse");
    void element.offsetWidth;
    element.classList.add("workspace-focus-pulse");
    window.setTimeout(() => element.classList.remove("workspace-focus-pulse"), 1400);
  }

  function clampScrollTop(element, value) {
    if (!element) return 0;
    const maxScrollTop = Math.max(0, element.scrollHeight - element.clientHeight);
    return Math.min(Math.max(0, value), maxScrollTop);
  }

  function cssPixelValue(value) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function scrollElementWithinContainer(element, container, options = {}) {
    if (!element || !container || !container.contains(element)) return false;
    const elementRect = element.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const containerStyle = window.getComputedStyle?.(container);
    const paddingTop = cssPixelValue(containerStyle?.scrollPaddingTop);
    const paddingBottom = cssPixelValue(containerStyle?.scrollPaddingBottom);
    const block = options.block || "center";
    const topDelta = elementRect.top - containerRect.top - paddingTop;
    const bottomDelta = elementRect.bottom - (containerRect.bottom - paddingBottom);
    let nextTop = container.scrollTop;
    if (block === "nearest") {
      if (topDelta < 0) nextTop += topDelta;
      else if (bottomDelta > 0) nextTop += bottomDelta;
      else return true;
    } else if (block === "start") {
      nextTop += topDelta;
    } else if (block === "end") {
      nextTop += bottomDelta;
    } else {
      nextTop += topDelta - Math.max(0, (container.clientHeight - elementRect.height) / 2);
    }
    container.scrollTop = clampScrollTop(container, nextTop);
    return true;
  }

  function workspaceNearestScrollContainer(element) {
    if (!element) return null;
    const scoped = element.closest?.([
      "#workspaceExecutionBoard",
      "#workspaceExecutionDetail",
      "#workspaceHistoryList",
      "#workspaceUseChatList",
      "#workspaceChatList",
      "#workspaceNodeList",
      "#workspaceNodeEditor",
      "#workflowTemplateCanvas",
      "#workflowTemplateNodeEditor",
      "#workflowTemplateList",
      "#manageAgentList",
      "#manageToolList",
      "#manageProviderProfileList",
      "#providerProfileList",
      "#providerProfileEditor",
      "#workspaceRunList",
    ].join(", "));
    if (scoped && isScrollableElement(scoped)) return scoped;
    const shell = document.querySelector(".workspace-scroll-shell");
    return shell && shell.contains(element) ? shell : null;
  }

  function revealWorkspaceElement(element, options = {}) {
    if (!element) return false;
    const container = workspaceNearestScrollContainer(element);
    if (container && scrollElementWithinContainer(element, container, options)) return true;
    element.scrollIntoView({ behavior: options.behavior || "smooth", block: options.block || "center" });
    return true;
  }

  function revealWorkspacePanelTarget(targetId = "", options = {}, deps = {}) {
    const id = String(targetId || "").trim();
    requestAnimationFrame(() => {
      const target = id ? elementById(deps, id) : null;
      const fallback = elementById(deps, "workspaceExecutionBoard") || elementById(deps, "workspaceHomePanel") || elementById(deps, "workspaceProjectModulesPanel");
      const element = target || fallback;
      if (!element) return;
      revealWorkspaceElement(element, options);
      flashWorkspaceFocus(element);
    });
  }

  function revealWorkspaceExecutionNode(nodeId, options = {}, deps = {}) {
    const id = String(nodeId || "").trim();
    requestAnimationFrame(() => {
      const escaped = window.CSS?.escape ? CSS.escape(id) : id.replace(/(["\\])/g, "\\$1");
      const panelTarget = options.targetId ? elementById(deps, options.targetId) : null;
        const nodeCard = id
          ? document.querySelector(`#workspaceExecutionBoard [data-action="select-execution-node"][data-node-id="${escaped}"]`)
            || document.querySelector(`#workspaceLauncherPlan [data-action="select-execution-node"][data-node-id="${escaped}"]`)
            || document.querySelector(`#workspaceLauncherDetails [data-action="select-execution-node"][data-node-id="${escaped}"]`)
            || document.querySelector(`#workspaceManageInspectChain [data-action="select-execution-node"][data-node-id="${escaped}"]`)
            || document.querySelector(`#workspaceManageInspectChain [data-action="select-execution-node"][data-node-id="${escaped}"]`)
        : null;
      const target = nodeCard || panelTarget || elementById(deps, "workspaceExecutionBoard");
      if (panelTarget) revealWorkspaceElement(panelTarget, options);
      if (target) {
        revealWorkspaceElement(target, options);
        flashWorkspaceFocus(target);
      }
      if (panelTarget && panelTarget !== target) flashWorkspaceFocus(panelTarget);
      flashWorkspaceFocus(elementById(deps, "workspaceExecutionDetail"));
    });
  }

  function revealWorkflowTemplateSelection(nodeId = "", options = {}, deps = {}) {
    const id = String(nodeId || "").trim();
    if (!id) return;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const escaped = window.CSS?.escape ? CSS.escape(id) : id.replace(/(["\\])/g, "\\$1");
      const canvas = elementById(deps, "workflowTemplateCanvas");
      const viewport = canvas?.querySelector(".workflow-template-flow-viewport");
      const node = canvas?.querySelector(`.workflow-template-flow-node[data-node-id="${escaped}"]`);
      if (viewport && node) {
        const nodeRect = node.getBoundingClientRect();
        const viewportRect = viewport.getBoundingClientRect();
        const padding = 18;
        let nextLeft = viewport.scrollLeft;
        if (nodeRect.left < viewportRect.left + padding) {
          nextLeft += nodeRect.left - viewportRect.left - padding;
        } else if (nodeRect.right > viewportRect.right - padding) {
          nextLeft += nodeRect.right - viewportRect.right + padding;
        }
        if (Math.abs(nextLeft - viewport.scrollLeft) > 1) {
          viewport.scrollTo({ left: Math.max(0, nextLeft), behavior: options.behavior || "smooth" });
        }
        flashWorkspaceFocus(node);
      }
      const editor = options.editor === false ? null : elementById(deps, "workflowTemplateNodeEditor");
      if (editor) revealWorkspaceElement(editor, { ...options, block: options.block || "nearest" });
    }));
  }

  function isScrollableElement(element, axis = "y") {
    if (!element || element === document.body || element === document.documentElement) return false;
    const style = window.getComputedStyle(element);
    if (axis === "x") {
      return /(auto|scroll|overlay)/.test(style.overflowX) && element.scrollWidth > element.clientWidth + 1;
    }
    return /(auto|scroll|overlay)/.test(style.overflowY) && element.scrollHeight > element.clientHeight + 1;
  }

  function canScrollElement(element, delta, axis = "y") {
    if (!isScrollableElement(element, axis)) return false;
    if (axis === "x") {
      if (delta > 0) return element.scrollLeft + element.clientWidth < element.scrollWidth - 1;
      if (delta < 0) return element.scrollLeft > 0;
      return false;
    }
    if (delta > 0) return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
    if (delta < 0) return element.scrollTop > 0;
    return false;
  }

  function elementVisibleInViewport(element, minimum = 24) {
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    const width = window.innerWidth || document.documentElement.clientWidth || 0;
    const height = window.innerHeight || document.documentElement.clientHeight || 0;
    const visibleX = Math.min(rect.right, width) - Math.max(rect.left, 0);
    const visibleY = Math.min(rect.bottom, height) - Math.max(rect.top, 0);
    return visibleX > 0 && visibleY >= minimum;
  }

  function wheelDeltaForAxis(event, axis = "y") {
    const primary = axis === "x" ? event.deltaX : event.deltaY;
    if (primary) return primary;
    return axis === "x" && Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
  }

  function routeWheelToElement(event, element, axis = "y") {
    const delta = wheelDeltaForAxis(event, axis);
    if (!element || !canScrollElement(element, delta, axis)) return false;
    const previousScroll = axis === "x" ? element.scrollLeft : element.scrollTop;
    const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE
      ? 16
      : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
        ? Math.max(1, element.clientHeight)
        : 1;
    if (axis === "x") element.scrollLeft += delta * unit;
    else element.scrollTop += delta * unit;
    if ((axis === "x" ? element.scrollLeft : element.scrollTop) === previousScroll) return false;
    event.preventDefault();
    return true;
  }

  function closestScrollableElement(start, boundary = null, axis = "y") {
    let node = start instanceof Element ? start : start?.parentElement;
    while (node && node !== document.body && node !== document.documentElement) {
      if (isScrollableElement(node, axis)) return node;
      if (boundary && node === boundary) break;
      node = node.parentElement;
    }
    return null;
  }

  function scrollableAncestors(start, boundary = null, axis = "y") {
    const items = [];
    let node = start instanceof Element ? start : start?.parentElement;
    while (node && node !== document.body && node !== document.documentElement) {
      if (isScrollableElement(node, axis)) items.push(node);
      if (boundary && node === boundary) break;
      node = node.parentElement;
    }
    return items;
  }

  const MAIN_WHEEL_FALLBACK_EXCLUDE_SELECTOR = [
    ".modal",
    ".server-resource-popover",
    ".workspace-help-popover",
  ].join(", ");

  const FORCE_ROUTED_WHEEL_SELECTOR = [
    ".panel-head",
    ".panel-head-tabs",
    ".subhead",
    ".subsection-head",
    ".workspace-mode-switch",
    ".workspace-tabs",
    ".workspace-project-drawer-summary",
    ".workspace-manage-toolbar",
    ".workspace-template-list-panel",
    ".workspace-template-seeds",
    ".workspace-node-toolbar",
    ".workspace-agent-toolbar",
    ".workspace-provider-toolbar",
    ".workspace-side > .subsection-head",
    ".workspace-chat-toolbar",
    ".job-tools",
    ".process-tools",
  ].join(", ");

  function targetShouldForceRoutedWheel(target) {
    return Boolean(target?.closest?.(FORCE_ROUTED_WHEEL_SELECTOR));
  }

  function visibleScrollTarget(...selectors) {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (!element || element.hidden || element.closest("[hidden]")) continue;
      if (isScrollableElement(element)) return element;
    }
    return null;
  }

  function visibleScrollTargetWithin(root, ...selectors) {
    if (!root) return null;
    for (const selector of selectors) {
      const element = root.querySelector(selector);
      if (!element || element.hidden || element.closest("[hidden]")) continue;
      if (isScrollableElement(element)) return element;
    }
    return null;
  }

  function workspaceHeaderWheelTarget(target, deps = {}) {
    if (!target) return null;
    if (target.closest("#workspaceHubPanel > .panel-head")) {
      return document.querySelector(".workspace-scroll-shell");
    }
    if (target.closest("#workspaceModeSwitch, #workspaceManageTabs, #workspaceTabs, .workspace-project-drawer-summary")) {
      return document.querySelector(".workspace-scroll-shell");
    }
    if (target.closest(".workspace-execution-workspace-head")) {
      return visibleScrollTarget("#workspaceExecutionBoard") || document.querySelector(".workspace-scroll-shell");
    }
    if (target.closest(".workspace-use-detail > .subsection-head")) {
      return visibleScrollTarget("#workspaceExecutionDetail");
    }
    if (target.closest(".workspace-use-history > .subsection-head")) {
      return visibleScrollTarget("#workspaceHistoryList");
    }
    if (target.closest(".workspace-use-chat .workspace-chat-toolbar")) {
      return visibleScrollTarget("#workspaceUseChatList");
    }
    if (target.closest("#workspaceChatPanel .workspace-chat-toolbar")) {
      return visibleScrollTarget("#workspaceChatList");
    }
    if (target.closest("#workspaceWorkflowPanel .subsection-head, #workspaceWorkflowPanel .workspace-node-toolbar")) {
      return visibleScrollTarget("#workspaceNodeList", "#workspaceNodeEditor");
    }
    if (target.closest("#workspaceAgentsPanel .workspace-agent-toolbar")) {
      return visibleScrollTarget("#workspaceAgentList", "#workspaceAgentEditor");
    }
    if (target.closest("#workspaceToolsPanel .workspace-agent-toolbar")) {
      return visibleScrollTarget("#workspaceToolList", "#workspaceToolEditor");
    }
    if (target.closest("#workspaceModelPanel .subsection-head, #workspaceModelPanel .workspace-provider-toolbar")) {
      return visibleScrollTarget("#providerProfileList", "#providerProfileEditor");
    }
    if (target.closest("#workspaceRunsPanel .workspace-agent-toolbar")) {
      return visibleScrollTarget("#workspaceRunList");
    }
    if (target.closest(".workspace-side > .subsection-head")) {
      return visibleScrollTarget("#workspaceList") || document.querySelector(".workspace-scroll-shell");
    }
    const templateListPanel = target.closest(".workspace-template-list-panel");
    if (templateListPanel && target.closest(".workspace-manage-toolbar, .workspace-template-seeds")) {
      return visibleScrollTargetWithin(templateListPanel, ".workspace-template-list");
    }
    if (templateListPanel && !target.closest(".workspace-template-list")) {
      return visibleScrollTargetWithin(templateListPanel, ".workspace-template-list");
    }
    if (target.closest(".workspace-template-studio > .workspace-manage-toolbar")) {
      return document.querySelector(".workspace-scroll-shell");
    }
    return null;
  }

  function staticWheelScrollTarget(target, workspacePanel, deps = {}) {
    if (!target || !workspacePanel) return null;
    const tableWrap = target.closest(".table-wrap");
    if (tableWrap) {
      return tableWrap;
    }
    if (workspacePanel.id === "consoleActivityPanel" && target.closest(".panel-head-tabs")) {
      if (!elementById(deps, "activityTasksPanel")?.hidden) return elementById(deps, "jobList");
      if (!elementById(deps, "activityTmuxPanel")?.hidden) return elementById(deps, "tmuxList");
      if (!elementById(deps, "activityConsolePanel")?.hidden) return elementById(deps, "terminalSessionList");
    }
    if (workspacePanel.id === "consoleMonitorPanel") {
      const panel = target.closest(".gpu-panel, .process-panel");
      if (panel) {
        const panelTableWrap = panel.querySelector(".table-wrap");
        return elementVisibleInViewport(panelTableWrap, 40) ? panelTableWrap : null;
      }
      return visibleScrollTargetWithin(workspacePanel, ".gpu-panel .table-wrap", ".process-panel .table-wrap");
    }
    if (workspacePanel.id === "workspaceHubPanel") {
      return workspaceHeaderWheelTarget(target, deps);
    }
    if (workspacePanel.id === "consoleExecPanel" && target.closest(".panel-head-tabs")) {
      if (!elementById(deps, "execJobPanel")?.hidden) return elementById(deps, "execJobPanel");
      if (!elementById(deps, "execPlanPanel")?.hidden) return elementById(deps, "execPlanPanel");
      if (!elementById(deps, "execTransferPanel")?.hidden) return elementById(deps, "execTransferPanel");
    }
    const taskPanel = target.closest("#activityTasksPanel");
    if (taskPanel && !target.closest("#jobList")) return elementById(deps, "jobList");
    if (target.closest("#jobList")) return elementById(deps, "jobList");
    const tmuxPanel = target.closest("#activityTmuxPanel");
    if (tmuxPanel && !target.closest("#tmuxList")) return elementById(deps, "tmuxList");
    if (target.closest("#tmuxList")) return elementById(deps, "tmuxList");
    const outputPanel = target.closest("#activityConsolePanel");
    if (outputPanel) {
      if (target.closest("#terminalActivitySnapshot")) return elementById(deps, "terminalActivitySnapshot");
      if (target.closest("#terminalSessionList")) return elementById(deps, "terminalSessionList");
      return elementById(deps, "terminalSessionList");
    }
    return null;
  }

  function handleMainWheelFallback(event, deps = {}) {
    if (event.defaultPrevented || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    if (!target) return;
    if (target.closest(MAIN_WHEEL_FALLBACK_EXCLUDE_SELECTOR)) return;
    const mainArea = elementById(deps, "mainContentArea") || document.querySelector(".main-content-area");
    const workspacePanel = target.closest("#workspaceHubPanel, #consoleActivityPanel, #consoleExecPanel, #consoleMonitorPanel");
    if (!mainArea || !workspacePanel) return;
    const forceRoute = targetShouldForceRoutedWheel(target);
    const staticTarget = staticWheelScrollTarget(target, workspacePanel, deps);
    if (forceRoute && routeWheelToElement(event, staticTarget)) return;
    const nearestScrollable = closestScrollableElement(target, workspacePanel);
    const scrollTarget = scrollableAncestors(target, workspacePanel)
      .find((element) => canScrollElement(element, event.deltaY));
    const targetIsFormControl = target.matches("textarea, input, select");
    if (scrollTarget) {
      if (!forceRoute) {
        const nearestAtBoundary = nearestScrollable
          && nearestScrollable !== scrollTarget
          && !canScrollElement(nearestScrollable, event.deltaY);
        if (nearestAtBoundary) routeWheelToElement(event, scrollTarget);
        return;
      }
      if (targetIsFormControl && scrollTarget === target) return;
      routeWheelToElement(event, staticTarget || scrollTarget);
      return;
    }
    if (routeWheelToElement(event, staticTarget)) return;
    const fallback = canScrollElement(workspacePanel, event.deltaY)
      ? workspacePanel
      : canScrollElement(mainArea, event.deltaY)
        ? mainArea
        : null;
    routeWheelToElement(event, fallback);
  }

  function handleLogPaneWheel(event, deps = {}) {
    if (event.defaultPrevented || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    const pane = elementById(deps, "logPane");
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    if (!pane || pane.hidden || !target || !pane.contains(target)) return;
    if (target.matches("textarea, select") || target.closest("#logView")) return;
    const nativeScroller = scrollableAncestors(target, pane)
      .find((element) => canScrollElement(element, event.deltaY));
    if (nativeScroller) return;
    routeWheelToElement(event, elementById(deps, "logView"));
  }

  window.WorkspaceFocusNavigation = {
    canScrollElement,
    clampScrollTop,
    closestScrollableElement,
    cssPixelValue,
    elementVisibleInViewport,
    flashWorkspaceFocus,
    handleLogPaneWheel,
    handleMainWheelFallback,
    isScrollableElement,
    revealWorkflowTemplateSelection,
    revealWorkspaceElement,
    revealWorkspaceExecutionNode,
    revealWorkspacePanelTarget,
    routeWheelToElement,
    scrollElementWithinContainer,
    scrollableAncestors,
    staticWheelScrollTarget,
    targetShouldForceRoutedWheel,
    visibleScrollTarget,
    visibleScrollTargetWithin,
    wheelDeltaForAxis,
    workspaceHeaderWheelTarget,
    workspaceNearestScrollContainer,
  };
})();
