(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function eventValue(event) {
    return event?.target?.value || "";
  }

  function call(callbacks, name, value, event) {
    fn(callbacks, name, () => {})(value, event);
  }

  function bind(callbacks = {}) {
    element(callbacks, "terminalServerSelect")?.addEventListener("change", (event) => {
      call(callbacks, "selectTerminalServer", eventValue(event), event);
    });
    element(callbacks, "serverSelect")?.addEventListener("change", (event) => {
      call(callbacks, "selectMainServer", eventValue(event), event);
    });
    element(callbacks, "gpuSelect")?.addEventListener("change", (event) => {
      call(callbacks, "selectGpu", eventValue(event), event);
    });
  }

  window.ServerSelectionActions = {
    bind,
  };
})();
