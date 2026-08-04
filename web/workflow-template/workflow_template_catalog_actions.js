(function () {
  "use strict";

  const TEXT_INPUT_BINDINGS = [
    "templateNameInput",
    "templateStatusSelect",
    "templateTagsInput",
    "templateDescriptionInput",
    "templateBriefInput",
    "templateRepoUrlInput",
    "templateRepoRefInput",
    "templatePaperUrlInput",
    "templateWorkspaceDirInput",
    "templateIdeaInput",
    "templateEnvNameInput",
    "templatePythonVersionInput",
  ];

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function queryAll(callbacks, selector) {
    const result = fn(callbacks, "queryAll", () => [])(selector);
    return Array.from(result || []);
  }

  function bindTemplateList(callbacks = {}) {
    element(callbacks, "workflowTemplateList")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action='select-workflow-template']");
      if (button?.dataset.templateId) fn(callbacks, "selectTemplate", () => {})(button.dataset.templateId);
    });
  }

  function bindTemplateButtons(callbacks = {}) {
    element(callbacks, "workspaceNewTemplateBtn")?.addEventListener("click", () => {
      fn(callbacks, "newTemplate", () => {})("repo");
    });
    element(callbacks, "workspaceDeleteTemplateBtn")?.addEventListener("click", () => {
      void fn(callbacks, "deleteTemplate", async () => {})();
    });
    element(callbacks, "workspaceSaveTemplateBtn")?.addEventListener("click", () => {
      void fn(callbacks, "saveTemplate", async () => {})();
    });
    element(callbacks, "workspacePreviewTemplateBtn")?.addEventListener("click", async () => {
      fn(callbacks, "setMessage", () => {})("正在校验模板...");
      try {
        const result = await fn(callbacks, "previewTemplate", async () => null)();
        const validation = result?.validation;
        const summary = fn(callbacks, "validationSummary", () => "等待后端校验")(validation);
        fn(callbacks, "setMessage", () => {})(`模板校验：${summary}`, validation?.status === "blocked");
      } catch (error) {
        fn(callbacks, "setMessage", () => {})(error.message || "模板校验失败。", true);
      }
    });
    queryAll(callbacks, ".workspace-template-seeds [data-seed]").forEach((button) => {
      button.addEventListener("click", () => {
        fn(callbacks, "newTemplate", () => {})(button.dataset.seed || "repo");
      });
    });
  }

  function bindTemplateInputs(callbacks = {}) {
    TEXT_INPUT_BINDINGS.forEach((id) => {
      element(callbacks, id)?.addEventListener("input", (event) => {
        fn(callbacks, "updateTextField", () => {})(id, event.target.value || "");
      });
    });
    element(callbacks, "templateSourceTypeSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "updateSourceType", () => {})(event.target.value || "repo");
    });
    element(callbacks, "templateEnvManagerSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "updateEnvManager", () => {})(event.target.value || "");
    });
    element(callbacks, "templateProviderProfileSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "updateProviderProfile", () => {})(event.target.value || "");
    });
    element(callbacks, "templateRoutingModeSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "updateRoutingMode", () => {})(event.target.value || "workspace_default");
    });
    element(callbacks, "templateChatAgentSelect")?.addEventListener("change", (event) => {
      fn(callbacks, "updateChatAgent", () => {})(event.target.value || "");
    });
  }

  function bindNodeToolbar(callbacks = {}) {
    element(callbacks, "workflowTemplateAddNodeBtn")?.addEventListener("click", () => {
      fn(callbacks, "insertNode", () => {})(fn(callbacks, "selectedNodeKind", () => "custom.step")() || "custom.step");
    });
    element(callbacks, "workflowTemplateMoveUpBtn")?.addEventListener("click", () => {
      fn(callbacks, "moveNode", () => {})("up");
    });
    element(callbacks, "workflowTemplateMoveDownBtn")?.addEventListener("click", () => {
      fn(callbacks, "moveNode", () => {})("down");
    });
    element(callbacks, "workflowTemplateDeleteNodeBtn")?.addEventListener("click", () => {
      fn(callbacks, "removeNode", () => {})();
    });
    element(callbacks, "workflowTemplateRebuildBtn")?.addEventListener("click", () => {
      fn(callbacks, "rebuildNodes", () => {})();
    });
  }

  function bind(callbacks = {}) {
    bindTemplateList(callbacks);
    bindTemplateButtons(callbacks);
    bindTemplateInputs(callbacks);
    bindNodeToolbar(callbacks);
  }

  window.WorkflowTemplateCatalogActions = {
    bind,
    bindNodeToolbar,
    bindTemplateButtons,
    bindTemplateInputs,
    bindTemplateList,
  };
})();
