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
    element(callbacks, "refreshBtn")?.addEventListener("click", (event) => {
      call(callbacks, "refreshStatus", event);
    });
    element(callbacks, "refreshSelectedServerBtn")?.addEventListener("click", (event) => {
      call(callbacks, "refreshSelectedServer", event);
    });
    element(callbacks, "terminalBtn")?.addEventListener("click", (event) => {
      call(callbacks, "openTerminal", event);
    });
  }

  window.AppStatusActions = {
    bind,
  };
})();
