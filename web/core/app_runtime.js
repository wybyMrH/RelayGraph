(function () {
  "use strict";

  const JOB_FORM_PERSIST_SKIP = new Set(["workspace_id", "workspace_node_id", "workspace_node_title"]);
  const TRANSFER_FORM_PERSIST_SKIP = new Set(["source", "target"]);

  function loadStoredValue(key, fallback = "") {
    try {
      return localStorage.getItem(key) ?? fallback;
    } catch {
      return fallback;
    }
  }

  function saveStoredValue(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  }

  function removeStoredValue(key) {
    try {
      localStorage.removeItem(key);
    } catch {}
  }

  function loadStoredJson(key, fallback = {}) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return fallback;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : fallback;
    } catch {
      return fallback;
    }
  }

  function saveStoredJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {}
  }

  function loadStoredArray(key) {
    const value = loadStoredJson(key, []);
    return Array.isArray(value) ? value : [];
  }

  function humanizeFetchError(error, context = "") {
    const raw = String(error?.message || error || "未知错误");
    if (raw === "Failed to fetch") {
      return context
        ? `${context}失败：无法连接后端，请确认 Total Control 服务仍在运行。`
        : "无法连接后端，请确认 Total Control 服务仍在运行。";
    }
    if (raw === "not found") {
      return context
        ? `${context}失败：接口不存在，请重启 Total Control 以加载最新后端。`
        : "接口不存在，请重启 Total Control 以加载最新后端。";
    }
    return raw;
  }

  async function fetchJson(url, options) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (error) {
      const enhanced = new Error(humanizeFetchError(error, `请求 ${url}`));
      enhanced.cause = error;
      throw enhanced;
    }
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await response.text();
      throw new Error(
        `请求 ${url} 返回非 JSON（HTTP ${response.status}）。可能后端版本旧或路径不存在。响应起始: ${text.slice(0, 80)}`,
      );
    }
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.error || response.statusText);
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function storageKeysFor(deps = {}) {
    return deps.storageKeys && typeof deps.storageKeys === "object" ? deps.storageKeys : {};
  }

  function elementFor(deps = {}, id = "") {
    const lookup = typeof deps.element === "function" ? deps.element : (value) => document.getElementById(value);
    return lookup(id);
  }

  function formStorageKey(formId, deps = {}) {
    const keys = storageKeysFor(deps);
    if (formId === "workspaceForm") return keys.workspaceForm || "";
    if (formId === "jobForm") return keys.jobForm || "";
    if (formId === "taskPlanForm") return keys.taskPlanForm || "";
    if (formId === "transferForm") return keys.transferForm || "";
    return "";
  }

  function storedFormState(formId, deps = {}) {
    const key = formStorageKey(formId, deps);
    return key ? loadStoredJson(key, {}) : {};
  }

  function formPersistSkipNames(formId) {
    if (formId === "jobForm") return JOB_FORM_PERSIST_SKIP;
    if (formId === "transferForm") return TRANSFER_FORM_PERSIST_SKIP;
    return null;
  }

  function captureFormState(form, options = {}) {
    const skipNames = options.skipNames || null;
    const data = {};
    form.querySelectorAll("[name]").forEach((field) => {
      if (!field.name) return;
      if (skipNames?.has(field.name)) return;
      if (field.type === "checkbox") data[field.name] = Boolean(field.checked);
      else data[field.name] = field.value;
    });
    return data;
  }

  function persistFormState(formId, deps = {}) {
    const form = elementFor(deps, formId);
    const key = formStorageKey(formId, deps);
    if (!form || !key) return;
    const skipNames = formPersistSkipNames(formId);
    saveStoredJson(key, captureFormState(form, { skipNames }));
  }

  function restoreFormState(formId, deps = {}) {
    const form = elementFor(deps, formId);
    const data = storedFormState(formId, deps);
    const skipNames = formPersistSkipNames(formId);
    if (!form || !data || typeof data !== "object") return;
    form.querySelectorAll("[name]").forEach((field) => {
      if (skipNames?.has(field.name)) return;
      if (!(field.name in data)) return;
      if (field.type === "checkbox") field.checked = Boolean(data[field.name]);
      else field.value = data[field.name];
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function deepClone(value, fallback) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return fallback;
    }
  }

  function makeClientId(prefix = "node") {
    if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  function inputSignature(el) {
    const data = el.dataset
      ? Object.keys(el.dataset).sort().map((k) => `${k}=${el.dataset[k]}`).join("|")
      : "";
    return `${el.tagName}|${el.type || ""}|${el.name || ""}|${data}`;
  }

  function findInputBySignature(sig) {
    let match = null;
    for (const el of document.querySelectorAll("input, textarea, select")) {
      if (inputSignature(el) === sig) {
        if (match) return null;
        match = el;
      }
    }
    return match;
  }

  function captureActiveInput() {
    const active = document.activeElement;
    if (!active || !/^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return null;
    let start = null;
    let end = null;
    try {
      start = active.selectionStart;
      end = active.selectionEnd;
    } catch (_) {
      start = end = null;
    }
    return { sig: inputSignature(active), start, end };
  }

  function restoreActiveInput(captured) {
    if (!captured) return;
    const match = findInputBySignature(captured.sig);
    if (!match) return;
    match.focus();
    if (captured.start !== null) {
      try {
        match.setSelectionRange(captured.start, captured.end);
      } catch (_) {
        /* not all elements support selection */
      }
    }
  }

  function preserveActiveInput(renderFn) {
    const captured = captureActiveInput();
    renderFn();
    restoreActiveInput(captured);
  }

  window.AppRuntime = {
    captureActiveInput,
    captureFormState,
    deepClone,
    escapeHtml,
    fetchJson,
    findInputBySignature,
    formPersistSkipNames,
    formStorageKey,
    humanizeFetchError,
    inputSignature,
    loadStoredArray,
    loadStoredJson,
    loadStoredValue,
    makeClientId,
    persistFormState,
    preserveActiveInput,
    removeStoredValue,
    restoreActiveInput,
    restoreFormState,
    saveStoredJson,
    saveStoredValue,
    storedFormState,
  };
})();
