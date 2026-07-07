(function () {
  "use strict";

  const REPO_SOURCE_KINDS = [
    "source.repo",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  const PAPER_SOURCE_KINDS = [
    "source.paper",
    "research.search",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  const IDEA_SOURCE_KINDS = [
    "source.idea",
    "research.search",
    "repo.clone",
    "path.resolve",
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
    "eval.report",
  ];

  function workspaceNodeMeta(nodeTypes = {}, kind = "") {
    const map = nodeTypes && typeof nodeTypes === "object" ? nodeTypes : {};
    return map[kind] || map["custom.step"];
  }

  function workspaceNodeLabel(nodeTypes = {}, kind = "") {
    const meta = workspaceNodeMeta(nodeTypes, kind) || {};
    return meta.label || kind || "节点";
  }

  function workspaceNodeKindsForSource(sourceType) {
    if (sourceType === "repo") return [...REPO_SOURCE_KINDS];
    if (sourceType === "paper") return [...PAPER_SOURCE_KINDS];
    return [...IDEA_SOURCE_KINDS];
  }

  function workspaceNodeDefaultConfig(kind, formData = {}) {
    const base = {};
    const type = String(formData.source_type || "repo");
    if (kind === "source.repo") {
      base.repo_url = String(formData.repo_url || "");
      base.repo_ref = String(formData.repo_ref || "");
    } else if (kind === "source.paper") {
      base.paper_url = String(formData.paper_url || "");
    } else if (kind === "source.idea") {
      base.idea_text = String(formData.idea_text || formData.brief || "");
    } else if (kind === "research.search") {
      base.query = "";
      base.goal = "";
    } else if (kind === "repo.clone") {
      base.repo_url = String(formData.repo_url || "");
      base.repo_ref = String(formData.repo_ref || "");
      base.workspace_dir = String(formData.workspace_dir || "");
    } else if (kind === "path.resolve") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.data_roots = "";
      base.output_roots = "";
    } else if (kind === "repo.inspect") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.focus_paths = "";
      base.questions = "";
    } else if (kind === "dataset.find") {
      base.query = "";
      base.dataset_hints = String(formData.references || "");
      base.data_roots = "";
      base.expected_layout = "";
    } else if (kind === "env.infer") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.manifest_paths = "";
      base.env_name = String(formData.env_name || "");
      base.python_version = String(formData.python_version || "");
    } else if (kind === "env.prepare") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.env_name = String(formData.env_name || "");
      base.env_manager = String(formData.env_manager || "");
      base.python_version = String(formData.python_version || "");
      base.setup_command = String(formData.setup_command || "");
    } else if (kind === "gpu.allocate") {
      base.server_id = "";
      base.gpu_policy = "";
      base.min_free_memory_gib = "";
      base.notes = "";
    } else if (kind === "run.command") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.env_name = String(formData.env_name || "");
      base.server_id = "";
      base.gpu_policy = "";
      base.run_command = String(formData.run_command || "");
      base.schedule = String(formData.schedule || "");
    } else if (kind === "artifact.collect") {
      base.workspace_dir = String(formData.workspace_dir || "");
      base.artifact_paths = "";
      base.metric_paths = "";
      base.notes = String(formData.notes || "");
    } else if (kind === "eval.report") {
      base.report_command = String(formData.report_command || "");
      base.metric_paths = "";
      base.notes = String(formData.notes || "");
    } else if (kind === "notify.user") {
      base.channel = "ui";
      base.message = "";
    } else {
      base.goal = "";
      base.command = "";
      base.output_expectation = "";
    }
    return base;
  }

  function workspaceRecipeCommandValueFromNodes(nodes = [], key = "") {
    const items = Array.isArray(nodes) ? nodes : [];
    const findConfig = (kind) => {
      const node = items.find((item) => item?.kind === kind);
      return node?.config && typeof node.config === "object" ? node.config : {};
    };
    if (key === "setup_command") return String(findConfig("env.prepare").setup_command || "");
    if (key === "run_command") return String(findConfig("run.command").run_command || "");
    if (key === "schedule") return String(findConfig("run.command").schedule || "");
    if (key === "report_command") return String(findConfig("eval.report").report_command || "");
    return "";
  }

  function workspaceRecipeCommandValues(nodes = []) {
    return {
      setup_command: workspaceRecipeCommandValueFromNodes(nodes, "setup_command"),
      run_command: workspaceRecipeCommandValueFromNodes(nodes, "run_command"),
      report_command: workspaceRecipeCommandValueFromNodes(nodes, "report_command"),
      schedule: workspaceRecipeCommandValueFromNodes(nodes, "schedule"),
    };
  }

  function workspaceNodeSummary(node) {
    if (!node) return "";
    const config = node.config || {};
    if (node.kind === "source.repo") return config.repo_url || "未填写仓库地址";
    if (node.kind === "source.paper") return config.paper_url || "未填写论文链接";
    if (node.kind === "source.idea") return config.idea_text || "未填写想法";
    if (node.kind === "research.search") return config.query || config.goal || "待定义检索范围";
    if (node.kind === "repo.clone") return config.workspace_dir || config.repo_ref || "待定义克隆位置";
    if (node.kind === "path.resolve") return config.workspace_dir || config.data_roots || "待解析工作与数据路径";
    if (node.kind === "repo.inspect") return config.questions || config.focus_paths || "待定义检查目标";
    if (node.kind === "dataset.find") return config.query || config.dataset_hints || "待发现数据集";
    if (node.kind === "env.infer") return config.manifest_paths || config.python_version || "待推断环境";
    if (node.kind === "env.prepare") return config.setup_command || config.env_name || "待定义环境";
    if (node.kind === "gpu.allocate") return config.gpu_policy || config.server_id || "待分配 GPU";
    if (node.kind === "run.command") return config.run_command || "待定义运行命令";
    if (node.kind === "artifact.collect") return config.artifact_paths || config.metric_paths || "待收集产物";
    if (node.kind === "eval.report") return config.report_command || config.metric_paths || "待定义汇总动作";
    if (node.kind === "notify.user") return config.message || config.channel || "待定义通知内容";
    return config.goal || config.command || config.output_expectation || "待补充节点内容";
  }

  function workspaceNodeRuntimeSummary(node, deps = {}) {
    const zhStatus = typeof deps.zhStatus === "function" ? deps.zhStatus : (status) => status;
    const runtime = node?.runtime || {};
    const runCount = Number(runtime.run_count || 0);
    const status = String(runtime.last_job_status || "").trim();
    if (!runCount && !status && !runtime.last_error) return "";
    const parts = [];
    if (runCount) parts.push(`已运行 ${runCount} 次`);
    if (status) parts.push(`最近 ${zhStatus(status)}`);
    if (runtime.last_error) parts.push(`错误 ${String(runtime.last_error).slice(0, 36)}`);
    return parts.join(" · ");
  }

  window.WorkspaceNodeCatalog = {
    workspaceNodeDefaultConfig,
    workspaceRecipeCommandValueFromNodes,
    workspaceRecipeCommandValues,
    workspaceNodeKindsForSource,
    workspaceNodeLabel,
    workspaceNodeMeta,
    workspaceNodeRuntimeSummary,
    workspaceNodeSummary,
  };
})();
