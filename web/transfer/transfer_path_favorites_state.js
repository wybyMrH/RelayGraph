(function () {
  "use strict";

  const DEFAULT_LIMIT = 16;

  function normalizeFavoritePath(path) {
    return String(path || "").trim();
  }

  function serverKey(serverId) {
    return String(serverId || "local");
  }

  function normalizeFor(deps = {}, path = "") {
    const normalize = typeof deps.normalizePathForCompare === "function"
      ? deps.normalizePathForCompare
      : (value) => String(value || "").replace(/\/+$/, "");
    return normalize(path);
  }

  function labelFor(path, label = "", deps = {}) {
    const pathBaseName = typeof deps.pathBaseName === "function" ? deps.pathBaseName : (value) => String(value || "");
    return String(label || "").trim() || pathBaseName(path) || path;
  }

  function favoritesForServer(store = {}, serverId) {
    const items = store && typeof store === "object" ? store[serverKey(serverId)] : null;
    return Array.isArray(items) ? items : [];
  }

  function isFavorite(store = {}, serverId, path = "", deps = {}) {
    const normalized = normalizeFor(deps, normalizeFavoritePath(path));
    return favoritesForServer(store, serverId).some(
      (item) => normalizeFor(deps, item.path) === normalized,
    );
  }

  function addFavorite(store = {}, serverId, path = "", label = "", deps = {}) {
    const normalizedPath = normalizeFavoritePath(path);
    if (!normalizedPath) return { store, added: false };
    const key = serverKey(serverId);
    const nextStore = store && typeof store === "object" ? store : {};
    const now = typeof deps.now === "function" ? deps.now : () => Date.now();
    const limit = Math.max(1, Number(deps.limit || DEFAULT_LIMIT));
    const existing = favoritesForServer(nextStore, serverId).filter(
      (item) => normalizeFor(deps, item.path) !== normalizeFor(deps, normalizedPath),
    );
    nextStore[key] = [
      {
        path: normalizedPath,
        label: labelFor(normalizedPath, label, deps),
        savedAt: now(),
      },
      ...existing,
    ].slice(0, limit);
    return { store: nextStore, added: true };
  }

  function removeFavorite(store = {}, serverId, path = "", deps = {}) {
    const key = serverKey(serverId);
    const nextStore = store && typeof store === "object" ? store : {};
    const normalized = normalizeFor(deps, normalizeFavoritePath(path));
    const next = favoritesForServer(nextStore, serverId).filter(
      (item) => normalizeFor(deps, item.path) !== normalized,
    );
    if (next.length) nextStore[key] = next;
    else delete nextStore[key];
    return { store: nextStore };
  }

  function toggleFavorite(store = {}, serverId, path = "", label = "", deps = {}) {
    if (isFavorite(store, serverId, path, deps)) {
      const result = removeFavorite(store, serverId, path, deps);
      return { store: result.store, active: false, changed: true };
    }
    const result = addFavorite(store, serverId, path, label, deps);
    return { store: result.store, active: true, changed: Boolean(result.added) };
  }

  window.TransferPathFavoritesState = {
    addFavorite,
    favoritesForServer,
    isFavorite,
    normalizeFavoritePath,
    removeFavorite,
    serverKey,
    toggleFavorite,
  };
})();
