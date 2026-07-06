(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function resolve(callbacks, confirmed) {
    fn(callbacks, "resolve", () => {})(Boolean(confirmed));
  }

  function bind(callbacks = {}) {
    element(callbacks, "processStopConfirmCloseBtn")?.addEventListener("click", () => {
      resolve(callbacks, false);
    });
    element(callbacks, "processStopConfirmCancelBtn")?.addEventListener("click", () => {
      resolve(callbacks, false);
    });
    element(callbacks, "processStopConfirmSubmitBtn")?.addEventListener("click", () => {
      resolve(callbacks, true);
    });
    element(callbacks, "processStopConfirmModal")?.addEventListener("click", (event) => {
      if (event.target?.id === "processStopConfirmModal") resolve(callbacks, false);
    });
  }

  window.MonitoringProcessStopActions = {
    bind,
  };
})();
