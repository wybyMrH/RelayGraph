(function () {
  "use strict";

  function fn(callbacks, name, fallback) {
    return typeof callbacks[name] === "function" ? callbacks[name] : fallback;
  }

  function element(callbacks, id) {
    return fn(callbacks, "element", () => null)(id);
  }

  function queryAll(callbacks, selector) {
    return Array.from(fn(callbacks, "queryAll", (value) => document.querySelectorAll(value))(selector) || []);
  }

  function eventTarget(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") return target;
    return target?.parentElement && typeof target.parentElement.closest === "function" ? target.parentElement : null;
  }

  function valueFrom(event) {
    return eventTarget(event)?.value || "";
  }

  function bindProcessFilters(callbacks = {}) {
    const setProcessFilter = fn(callbacks, "setProcessFilter", () => {});
    element(callbacks, "processSearch")?.addEventListener("input", (event) => {
      setProcessFilter("query", valueFrom(event));
    });
    element(callbacks, "processServerFilter")?.addEventListener("change", (event) => {
      setProcessFilter("server", valueFrom(event));
    });
    element(callbacks, "processUserFilter")?.addEventListener("change", (event) => {
      setProcessFilter("user", valueFrom(event));
    });
    element(callbacks, "processGpuFilter")?.addEventListener("change", (event) => {
      setProcessFilter("gpu", valueFrom(event));
    });
  }

  function bindJobFilters(callbacks = {}) {
    const setJobFilter = fn(callbacks, "setJobFilter", () => {});
    element(callbacks, "jobSearch")?.addEventListener("input", (event) => {
      setJobFilter("query", valueFrom(event));
    });
    element(callbacks, "jobStatusFilter")?.addEventListener("change", (event) => {
      setJobFilter("status", valueFrom(event));
    });
    element(callbacks, "jobTypeFilter")?.addEventListener("change", (event) => {
      setJobFilter("kind", valueFrom(event));
    });
    element(callbacks, "jobServerFilter")?.addEventListener("change", (event) => {
      setJobFilter("server", valueFrom(event));
    });
    element(callbacks, "jobSortSelect")?.addEventListener("change", (event) => {
      setJobFilter("sort", valueFrom(event));
    });
  }

  function bindProcessTableSort(callbacks = {}) {
    const sortProcessTable = fn(callbacks, "sortProcessTable", () => {});
    queryAll(callbacks, "#processTable th[data-sort]").forEach((th) => {
      th.addEventListener("click", (event) => {
        if (eventTarget(event)?.closest(".col-resizer")) return;
        const key = th.dataset.sort || "";
        if (key) sortProcessTable(key);
      });
    });
  }

  function bind(callbacks = {}) {
    bindProcessFilters(callbacks);
    bindJobFilters(callbacks);
    bindProcessTableSort(callbacks);
  }

  window.MonitoringFilterActions = {
    bind,
    bindJobFilters,
    bindProcessFilters,
    bindProcessTableSort,
  };
})();
