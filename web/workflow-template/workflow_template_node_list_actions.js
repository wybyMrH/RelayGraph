(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function templateNodeButton(event) {
    return event?.target?.closest?.("[data-action='select-template-node']") || null;
  }

  function handleClick(event, callbacks = {}) {
    const button = templateNodeButton(event);
    if (button?.dataset.nodeId) {
      fn(callbacks, "selectTemplateNode", () => {})(button.dataset.nodeId, event);
    }
  }

  function bind(callbacks = {}) {
    element(callbacks, "workflowTemplateNodeList")?.addEventListener("click", (event) => {
      handleClick(event, callbacks);
    });
  }

  window.WorkflowTemplateNodeListActions = {
    bind,
    handleClick,
    templateNodeButton,
  };
})();
