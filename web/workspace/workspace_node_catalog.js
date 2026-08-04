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

  function workspaceLinksFromNodes(nodes = []) {
    return nodes.slice(0, -1).map((node, index) => ({
      id: `link-${index + 1}-${node.id}-${nodes[index + 1].id}`,
      from: node.id,
      to: nodes[index + 1].id,
    }));
  }

  function workspaceChainSourceType(sourceType) {
    return String(sourceType || "idea") === "mixed" ? "idea" : String(sourceType || "idea");
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

  function normalizeWorkspaceDraftNode(node, index = 0, formData = {}, deps = {}) {
    const defaultConfig = typeof deps.workspaceNodeDefaultConfig === "function"
      ? deps.workspaceNodeDefaultConfig
      : workspaceNodeDefaultConfig;
    const configValue = typeof deps.workspaceConfigValue === "function"
      ? deps.workspaceConfigValue
      : (_kind, _key, value) => value;
    const makeId = typeof deps.makeClientId === "function"
      ? deps.makeClientId
      : (prefix = "node") => `${prefix}-${Date.now()}`;
    const nodeLabel = typeof deps.workspaceNodeLabel === "function"
      ? deps.workspaceNodeLabel
      : (_kind) => _kind || "节点";
    const kind = String(node?.kind || "custom.step");
    const defaults = defaultConfig(kind, formData);
    const rawConfig = {
      ...defaults,
      ...(node?.config && typeof node.config === "object" ? node.config : {}),
    };
    const config = Object.fromEntries(
      Object.entries(rawConfig).map(([key, value]) => [key, configValue(kind, key, value)]),
    );
    const normalized = {
      id: String(node?.id || makeId("node")),
      kind,
      title: String(node?.title || nodeLabel(kind)),
      status: String(node?.status || "draft"),
      handler: {
        mode: String(node?.handler?.mode || "human"),
        agent_id: String(node?.handler?.agent_id || ""),
        name: String(node?.handler?.name || ""),
        handoff: String(node?.handler?.handoff || ""),
        output_key: String(node?.handler?.output_key || ""),
      },
      notes: String(node?.notes || ""),
      runtime: node?.runtime && typeof node.runtime === "object" ? {
        run_count: Number(node.runtime.run_count || 0),
        last_job_id: String(node.runtime.last_job_id || ""),
        last_job_name: String(node.runtime.last_job_name || ""),
        last_job_kind: String(node.runtime.last_job_kind || ""),
        last_job_status: String(node.runtime.last_job_status || ""),
        last_run_at: String(node.runtime.last_run_at || ""),
        last_finished_at: String(node.runtime.last_finished_at || ""),
        last_error: String(node.runtime.last_error || ""),
      } : {
        run_count: 0,
        last_job_id: "",
        last_job_name: "",
        last_job_kind: "",
        last_job_status: "",
        last_run_at: "",
        last_finished_at: "",
        last_error: "",
      },
      config,
      position: {
        x: Number(node?.position?.x ?? index * 240),
        y: Number(node?.position?.y ?? 0),
      },
    };
    const inputMapping = node?.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : {};
    if (Object.keys(inputMapping).length) {
      normalized.input_mapping = Object.entries(inputMapping).reduce((acc, [key, value]) => {
        const name = String(key || "").trim();
        if (name) acc[name] = String(value || "").trim();
        return acc;
      }, {});
    }
    const outputKey = String(node?.output_key || "").trim();
    if (outputKey) normalized.output_key = outputKey;
    return normalized;
  }

  function createWorkspaceNode(kind, overrides = {}, index = 0, formData = {}, deps = {}) {
    const deepClone = typeof deps.deepClone === "function"
      ? deps.deepClone
      : (value, fallback) => {
          try {
            return JSON.parse(JSON.stringify(value));
          } catch {
            return fallback;
          }
        };
    const normalizeNode = typeof deps.normalizeWorkspaceDraftNode === "function"
      ? deps.normalizeWorkspaceDraftNode
      : normalizeWorkspaceDraftNode;
    return normalizeNode({ kind, ...deepClone(overrides, {}) }, index, formData);
  }

  function buildWorkspaceStarterNodes(formData = {}, deps = {}) {
    const kindsForSource = typeof deps.workspaceNodeKindsForSource === "function"
      ? deps.workspaceNodeKindsForSource
      : workspaceNodeKindsForSource;
    const normalizeNode = typeof deps.normalizeWorkspaceDraftNode === "function"
      ? deps.normalizeWorkspaceDraftNode
      : normalizeWorkspaceDraftNode;
    return kindsForSource(String(formData.source_type || "repo")).map((kind, index) =>
      normalizeNode({ kind }, index, formData));
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

  function recommendedNodeAssignment(kind) {
    const mapping = {
      "source.repo": {
        mode: "human",
        role: "",
        displayName: "你",
        handoff: "确认仓库地址、目标分支、成功标准和运行约束。",
      },
      "source.paper": {
        mode: "human",
        role: "",
        displayName: "你",
        handoff: "补齐论文链接、任务目标和希望复现的指标。",
      },
      "source.idea": {
        mode: "human",
        role: "",
        displayName: "你",
        handoff: "把目标、限制条件和成功标准写清楚，再交给 Planner 和 Researcher。",
      },
      "research.search": {
        mode: "agent",
        role: "researcher",
        displayName: "Researcher",
        handoff: "输出候选仓库、关键依赖、相关文章和可信度说明。",
      },
      "repo.clone": {
        mode: "system",
        role: "repo_scout",
        displayName: "Repo Scout",
        handoff: "记录克隆目录、分支或提交，并确认代码已经落地。",
      },
      "path.resolve": {
        mode: "agent",
        role: "repo_scout",
        displayName: "Repo Scout",
        handoff: "输出工作目录、数据目录、日志目录和结果目录的候选路径。",
      },
      "repo.inspect": {
        mode: "agent",
        role: "repo_scout",
        displayName: "Repo Scout",
        handoff: "产出入口、依赖、默认命令、配置文件和结果目录。",
      },
      "dataset.find": {
        mode: "agent",
        role: "researcher",
        displayName: "Researcher",
        handoff: "输出数据集名称、来源、本地路径候选、下载方式和结构要求。",
      },
      "env.infer": {
        mode: "agent",
        role: "env_builder",
        displayName: "Env Builder",
        handoff: "输出 Python/CUDA/依赖文件判断和建议安装命令。",
      },
      "env.prepare": {
        mode: "system",
        role: "env_builder",
        displayName: "Env Builder",
        handoff: "记录环境名、安装结果、失败依赖和替代方案。",
      },
      "gpu.allocate": {
        mode: "system",
        role: "gpu_scout",
        displayName: "GPU Scout",
        handoff: "记录目标服务器、GPU 编号、空闲显存和调度约束。",
      },
      "run.command": {
        mode: "system",
        role: "runner",
        displayName: "Runner",
        handoff: "记录服务器、GPU、会话、日志路径和下一步评估入口。",
      },
      "artifact.collect": {
        mode: "agent",
        role: "evaluator",
        displayName: "Evaluator",
        handoff: "输出日志、指标、模型文件、运行命令和可复现产物路径。",
      },
      "eval.report": {
        mode: "agent",
        role: "evaluator",
        displayName: "Evaluator",
        handoff: "汇总核心指标、主要输出文件、异常和下一步建议。",
      },
      "notify.user": {
        mode: "agent",
        role: "reporter",
        displayName: "Reporter",
        handoff: "把关键结论、风险和待确认项反馈给用户。",
      },
    };
    return mapping[String(kind || "")] || {
      mode: "human",
      role: "",
      displayName: "你",
      handoff: "补充这个节点的职责、输入输出和交接要求。",
    };
  }

  window.WorkspaceNodeCatalog = {
    createWorkspaceNode,
    buildWorkspaceStarterNodes,
    normalizeWorkspaceDraftNode,
    recommendedNodeAssignment,
    workspaceChainSourceType,
    workspaceLinksFromNodes,
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
