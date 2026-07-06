(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function consume(callbacks, event) {
    fn(callbacks, "consumeEvent", () => {})(event);
  }

  function callAsync(callbacks, name, ...args) {
    void fn(callbacks, name, async () => {})(...args);
  }

  function handleStudioOverviewClick(event, callbacks = {}) {
    const button = eventTarget(event)?.closest("[data-action]");
    if (!button) return;
    const action = button.dataset.action || "";
    if (action === "copy-template-version-history") {
      consume(callbacks, event);
      callAsync(callbacks, "copyTemplateVersionHistory", event, button);
      return;
    }
    if (action === "apply-template-repair") {
      consume(callbacks, event);
      callAsync(callbacks, "applyTemplateRepair", button.dataset.repairId || "", button.dataset.nodeId || "", event, button);
      return;
    }
    if (action === "apply-template-repair-all") {
      consume(callbacks, event);
      callAsync(callbacks, "applyAllTemplateRepairs", event, button);
    }
  }

  function handleTemplateDiffClick(event, callbacks = {}) {
    const button = eventTarget(event)?.closest("[data-action]");
    if (!button) return;
    const action = button.dataset.action || "";
    if (action === "copy-template-migration-plan") {
      consume(callbacks, event);
      callAsync(callbacks, "copyTemplateMigrationPlan", event, button);
      return;
    }
    if (action === "apply-template-migration") {
      consume(callbacks, event);
      callAsync(callbacks, "applyTemplateMigration", event, button);
      return;
    }
    if (action === "create-template-migration-draft") {
      consume(callbacks, event);
      callAsync(callbacks, "createTemplateMigrationDraft", event, button);
    }
  }

  function bind(callbacks = {}) {
    element(callbacks, "workflowTemplateStudioOverview")?.addEventListener("click", (event) => {
      handleStudioOverviewClick(event, callbacks);
    });
    element(callbacks, "workspaceManageTemplateDiff")?.addEventListener("click", (event) => {
      handleTemplateDiffClick(event, callbacks);
    });
  }

  window.TemplateReviewActions = {
    bind,
    handleStudioOverviewClick,
    handleTemplateDiffClick,
  };
})();
