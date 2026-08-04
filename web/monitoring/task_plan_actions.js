(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function call(callbacks, name, event) {
    fn(callbacks, name, () => {})(event);
  }

  function bind(callbacks = {}) {
    element(callbacks, "taskPlanForm")?.addEventListener("submit", (event) => {
      call(callbacks, "scheduleTaskPlan", event);
    });
    element(callbacks, "taskPlanPreviewBtn")?.addEventListener("click", (event) => {
      call(callbacks, "previewTaskPlan", event);
    });
    element(callbacks, "taskTemplateSelect")?.addEventListener("change", (event) => {
      call(callbacks, "toggleTaskTemplateFields", event);
    });
    element(callbacks, "planServerSelect")?.addEventListener("change", (event) => {
      call(callbacks, "renderTaskPlanOptions", event);
    });
  }

  window.TaskPlanActions = {
    bind,
  };
})();
