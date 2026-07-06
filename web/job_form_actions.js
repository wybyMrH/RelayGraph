(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function bind(callbacks = {}) {
    element(callbacks, "jobForm")?.addEventListener("submit", (event) => {
      void fn(callbacks, "submitJob", async () => {})(event);
    });
  }

  window.JobFormActions = {
    bind,
  };
})();
