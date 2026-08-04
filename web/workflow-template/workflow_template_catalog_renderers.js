(function () {
  "use strict";

  function fn(deps, name, fallback) {
    return typeof deps[name] === "function" ? deps[name] : fallback;
  }

  function element(deps, id) {
    return fn(deps, "element", () => null)(id);
  }

  function catalogApiFor(deps = {}) {
    return typeof deps.catalogApi === "function" ? deps.catalogApi() : deps.catalogApi;
  }

  function catalogDepsFor(deps = {}) {
    return typeof deps.catalogDeps === "function" ? deps.catalogDeps() : (deps.catalogDeps || {});
  }

  function renderTemplateList(deps = {}) {
    const list = element(deps, "workflowTemplateList");
    if (!list) return;
    const templates = fn(deps, "templates", () => [])();
    const selectedTemplateId = fn(deps, "selectedTemplateId", () => "")();
    list.innerHTML = catalogApiFor(deps)?.templateListMarkup?.({
      templates,
      selectedTemplateId,
      ...catalogDepsFor(deps),
    }) || '<div class="empty">还没有工作流模板。</div>';
  }

  function renderNodeKindOptions(deps = {}) {
    const select = element(deps, "workflowTemplateNodeKindSelect");
    if (!select) return;
    const current = select.value;
    const nodeTypes = fn(deps, "nodeTypes", () => ({}))();
    select.innerHTML = catalogApiFor(deps)?.nodeKindOptionsMarkup?.({
      nodeTypes,
      ...catalogDepsFor(deps),
    }) || "";
    select.value = nodeTypes[current] ? current : "custom.step";
  }

  function renderNodeList(deps = {}) {
    const list = element(deps, "workflowTemplateNodeList");
    if (!list) return;
    fn(deps, "renderNodeKindOptions", () => renderNodeKindOptions(deps))();
    const nodes = fn(deps, "nodes", () => [])();
    const selectedNodeId = fn(deps, "selectedNodeId", () => "")();
    list.innerHTML = catalogApiFor(deps)?.nodeListMarkup?.({
      nodes: Array.isArray(nodes) ? nodes : [],
      selectedNodeId,
      ...catalogDepsFor(deps),
    }) || '<div class="empty">模板里还没有节点。</div>';
  }

  window.WorkflowTemplateCatalogRenderers = {
    renderNodeKindOptions,
    renderNodeList,
    renderTemplateList,
  };
})();
