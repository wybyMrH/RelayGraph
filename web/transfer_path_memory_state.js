(function () {
  "use strict";

  function emptyStore() {
    return { source: {}, target: {} };
  }

  function normalizeStore(stored = {}) {
    return {
      source: stored?.source && typeof stored.source === "object" ? stored.source : {},
      target: stored?.target && typeof stored.target === "object" ? stored.target : {},
    };
  }

  function bucketName(mode = "") {
    return mode === "target" ? "target" : "source";
  }

  function rememberPath(store, mode = "source", serverId = "", path = "") {
    const nextStore = store || emptyStore();
    if (!serverId) return { store: nextStore, changed: false };
    nextStore[bucketName(mode)][serverId] = path;
    return { store: nextStore, changed: true };
  }

  function resolvePath(store, mode = "source", serverId = "", defaultPathForServer = () => "") {
    const nextStore = store || emptyStore();
    const bucket = nextStore[mode] || {};
    if (Object.prototype.hasOwnProperty.call(bucket, serverId)) return { store: nextStore, path: bucket[serverId] };
    return { store: nextStore, path: defaultPathForServer(serverId) };
  }

  window.TransferPathMemoryState = {
    emptyStore,
    normalizeStore,
    rememberPath,
    resolvePath,
  };
})();
