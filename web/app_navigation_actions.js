(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function query(callbacks, selector) {
    return fn(callbacks, "query", (value) => document.querySelector(value))(selector);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function call(callbacks, name, ...args) {
    fn(callbacks, name, () => {})(...args);
  }

  function bindClosest(callbacks, root, selector, callbackName, valueFor) {
    root?.addEventListener("click", (event) => {
      const button = eventTarget(event)?.closest(selector);
      if (button) call(callbacks, callbackName, valueFor(button));
    });
  }

  function bindOverviewCards(callbacks = {}) {
    element(callbacks, "workspaceManageOverviewCards")?.addEventListener("click", (event) => {
      const button = eventTarget(event)?.closest("[data-action='switch-workspace-manage-tab']");
      if (button?.dataset.tab) call(callbacks, "switchWorkspaceManageTab", button.dataset.tab);
    });
  }

  function bind(callbacks = {}) {
    bindClosest(callbacks, element(callbacks, "execTabs"), "[data-tab]", "switchExecTab", (button) => button.dataset.tab);
    bindClosest(callbacks, element(callbacks, "mainNav"), "[data-view]", "switchProductTab", (button) => button.dataset.view);
    bindClosest(callbacks, element(callbacks, "workspaceTabs"), "[data-tab]", "switchWorkspaceTab", (button) => button.dataset.tab);
    bindClosest(
      callbacks,
      element(callbacks, "workspaceModuleCards"),
      "[data-workspace-tab]",
      "switchWorkspaceTab",
      (button) => button.getAttribute("data-workspace-tab"),
    );
    bindClosest(callbacks, element(callbacks, "workspaceModeSwitch"), "[data-mode]", "switchWorkspaceMode", (button) => button.dataset.mode);
    bindClosest(callbacks, element(callbacks, "workspaceManageTabs"), "[data-tab]", "switchWorkspaceManageTab", (button) => button.dataset.tab);
    bindClosest(
      callbacks,
      query(callbacks, ".workspace-manage-tabs-secondary"),
      "[data-tab]",
      "switchWorkspaceManageTab",
      (button) => button.dataset.tab,
    );
    bindOverviewCards(callbacks);
    bindClosest(callbacks, element(callbacks, "activityTabs"), "[data-tab]", "switchActivityTab", (button) => button.dataset.tab);
  }

  window.AppNavigationActions = {
    bind,
    bindClosest,
    bindOverviewCards,
    eventTarget,
  };
})();
