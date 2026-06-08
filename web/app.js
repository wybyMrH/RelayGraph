const state = {
  servers: [],
  jobs: [],
  workspaces: [],
  workflowTemplates: [],
  agentDefinitions: [],
  toolDefinitions: [],
  selectedWorkspaceId: "",
  selectedWorkflowTemplateId: "",
  selectedGlobalAgentId: "",
  selectedGlobalToolId: "",
  workspaceNodesDraft: [],
  workspaceAgentsDraft: [],
  workspaceToolsDraft: [],
  workspaceModelDraft: {},
  workflowTemplateDraft: {},
  agentDefinitionDraft: {},
  toolDefinitionDraft: {},
  providerProfiles: [],
  selectedWorkspaceNodeId: "",
  selectedTemplateNodeId: "",
  selectedWorkspaceAgentId: "",
  selectedWorkspaceToolId: "",
  selectedWorkspaceExecutionNodeId: "",
  selectedProviderProfileId: "",
  selectedServer: null,
  selectedGpu: "auto",
  selectedJob: null,
  selectedTmux: null,
  tmuxSessions: [],
  tmuxError: "",
  outputTabs: [],
  activeOutputKey: null,
  activeOutput: null,
  outputBusy: false,
  pollTimer: null,
  logPollTimer: null,
  terminal: {
    id: null,
    cursor: 0,
    alive: false,
    serverId: null,
    serverName: "",
    text: "",
    pollTimer: null,
  },
  terminals: {},
  processFilters: {
    query: "",
    server: "",
    user: "",
    gpu: "",
    sort: "server",
    dir: "asc",
  },
  jobFilters: {
    query: "",
    status: "",
    server: "",
    kind: "",
    sort: "created_desc",
  },
  transfer: {
    source: null,
    sources: [],
    target: null,
    tree: {},
    targetTree: {},
    ignores: [],
    logs: {},
  },
  filePicker: {
    roots: [],
    path: "",
    parent: "",
    entries: [],
    selected: null,
    mode: "source",
    serverId: "",
    dirsOnly: false,
    requestId: 0,
  },
  filePreview: {
    serverId: "",
    path: "",
    text: "",
    encoding: "",
    truncated: false,
    error: "",
    loading: false,
  },
  logSearch: {
    query: "",
    activeIndex: -1,
  },
  serverDnd: {
    draggingId: "",
    overId: "",
    position: "",
  },
  workspaceChatBusy: false,
  workspaceAgentDebug: {
    workspaceId: "",
    agentId: "",
    input: "",
    result: null,
    busy: false,
    error: "",
  },
  manageAgentDebug: {
    agentId: "",
    templateId: "",
    input: "",
    result: null,
    busy: false,
    error: "",
  },
  ui: {
    productTab: "console",
    execTab: "job",
    activityTab: "tasks",
    workspaceTab: "home",
    workspaceMode: "use",
    workspaceManageTab: "templates",
    serverSort: "default",
    pollIntervalMs: 5000,
    formsRestored: false,
    adminChecks: {},
    adminCheckBusy: {},
    serverOrder: [],
    serverPins: [],
    serverHistory: {},
    serverRefreshBusy: {},
    serverRefreshSeq: {},
    workspaceAutomationBusyAction: "",
    workspaceResourceRefreshBusy: false,
    workspaceResourceServerId: "",
    workspaceUiRevision: 0,
    offlineServersOpen: true,
    workspaceToolSearch: "",
    statusRequestSeq: 0,
    statusBusyCount: 0,
    statusManualBusyCount: 0,
    statusBusyVisibleUntil: 0,
    statusBusyTimer: null,
    workflowTemplateDirty: false,
    agentDefinitionDirty: false,
    toolDefinitionDirty: false,
    providerProfileDirty: false,
  },
};

let activeServerResourceAnchor = null;
let serverResourceHideTimer = null;

const $ = (id) => document.getElementById(id);

function markWorkspaceUiInteraction() {
  state.ui.workspaceUiRevision = Number(state.ui.workspaceUiRevision || 0) + 1;
}

const STORAGE_KEYS = {
  selectedServer: "tc-selected-server",
  selectedWorkspace: "tc-selected-workspace",
  selectedWorkflowTemplate: "tc-selected-workflow-template",
  selectedGlobalAgent: "tc-selected-global-agent",
  selectedGlobalTool: "tc-selected-global-tool",
  productTab: "tc-product-tab",
  execTab: "tc-exec-tab",
  activityTab: "tc-activity-tab",
  workspaceTab: "tc-workspace-tab",
  workspaceMode: "tc-workspace-mode",
  workspaceManageTab: "tc-workspace-manage-tab",
  serverSort: "tc-server-sort",
  serverOrder: "tc-server-order",
  serverPins: "tc-server-pins",
  outputSearch: "tc-output-search",
  providerProfiles: "tc-provider-profiles",
  selectedProviderProfile: "tc-selected-provider-profile",
  selectedWorkspaceAgent: "tc-selected-workspace-agent",
  workspaceLauncherDraft: "tc-workspace-launcher-draft",
  workspaceExecutionNodeSelections: "tc-workspace-execution-node-selections",
  workspaceForm: "tc-workspace-form",
  workspaceNodes: "tc-workspace-nodes",
  workspaceAgents: "tc-workspace-agents",
  workspaceTools: "tc-workspace-tools",
  workspaceModel: "tc-workspace-model",
  jobForm: "tc-job-form",
  taskPlanForm: "tc-task-plan-form",
  transferForm: "tc-transfer-form",
  selectedWorkspaceTool: "tc-selected-workspace-tool",
  workspaceResourceServer: "tc-workspace-resource-server",
};

const WORKSPACE_NODE_TYPES = {
  "source.repo": {
    label: "仓库输入",
    description: "定义主仓库来源",
    configFields: [
      { key: "repo_url", label: "仓库地址", type: "text", placeholder: "https://github.com/org/project.git" },
      { key: "repo_ref", label: "分支 / 提交", type: "text", placeholder: "main / v1.0 / sha" },
    ],
  },
  "source.paper": {
    label: "论文输入",
    description: "定义主论文来源",
    configFields: [
      { key: "paper_url", label: "论文链接", type: "text", placeholder: "https://arxiv.org/abs/xxxx.xxxxx" },
    ],
  },
  "source.idea": {
    label: "想法输入",
    description: "记录目标和背景",
    configFields: [
      { key: "idea_text", label: "想法 / 目标", type: "textarea", rows: 4, placeholder: "想做什么，为什么做，成功标准是什么" },
    ],
  },
  "research.search": {
    label: "检索资料",
    description: "整理参考资料与候选方案",
    configFields: [
      { key: "query", label: "检索关键词", type: "textarea", rows: 3, placeholder: "论文名、任务关键词、关键技术词" },
      { key: "goal", label: "检索目标", type: "text", placeholder: "例如找官方 repo、依赖和运行方式" },
    ],
  },
  "repo.clone": {
    label: "克隆仓库",
    description: "把代码拉到工作目录",
    configFields: [
      { key: "repo_url", label: "仓库地址", type: "text", placeholder: "https://github.com/org/project.git" },
      { key: "repo_ref", label: "分支 / 提交", type: "text", placeholder: "main / v1.0 / sha" },
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
    ],
  },
  "path.resolve": {
    label: "解析路径",
    description: "确认代码、数据、输出和日志路径",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "data_roots", label: "数据根目录", type: "textarea", rows: 3, placeholder: "/mnt/e/datasets\n/mnt/f/datasets" },
      { key: "output_roots", label: "输出根目录", type: "textarea", rows: 3, placeholder: "runs\noutputs\ncheckpoints" },
    ],
  },
  "repo.inspect": {
    label: "检查仓库",
    description: "找入口、依赖、配置和结果目录",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "focus_paths", label: "重点路径", type: "text", placeholder: "src, configs, scripts" },
      { key: "questions", label: "检查问题", type: "textarea", rows: 3, placeholder: "入口、依赖、默认参数、结果文件在哪里" },
    ],
  },
  "dataset.find": {
    label: "发现数据集",
    description: "从线索、论文和本地数据盘定位数据集",
    configFields: [
      { key: "query", label: "数据集关键词", type: "textarea", rows: 3, placeholder: "数据集名、任务名、论文名或 benchmark" },
      { key: "dataset_hints", label: "路径 / 链接线索", type: "textarea", rows: 3, placeholder: "每行一个本地路径、数据集名或下载链接" },
      { key: "data_roots", label: "搜索根目录", type: "textarea", rows: 3, placeholder: "/mnt/e/datasets\n/mnt/f/datasets" },
      { key: "expected_layout", label: "期望结构", type: "text", placeholder: "例如 images/, annotations/, train/val split" },
    ],
  },
  "env.infer": {
    label: "推断环境",
    description: "从仓库文件和运行脚本推断环境需求",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "manifest_paths", label: "依赖文件", type: "text", placeholder: "requirements.txt, pyproject.toml, environment.yml" },
      { key: "env_name", label: "环境名", type: "text", placeholder: "agent-workspace" },
      { key: "python_version", label: "Python 版本", type: "text", placeholder: "3.11" },
    ],
  },
  "env.prepare": {
    label: "准备环境",
    description: "配置 conda / venv / 自定义环境",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "env_name", label: "环境名", type: "text", placeholder: "agent-workspace" },
      {
        key: "env_manager",
        label: "环境管理",
        type: "select",
        options: [
          { value: "conda", label: "conda" },
          { value: "venv", label: "venv" },
          { value: "custom", label: "custom" },
        ],
      },
      { key: "python_version", label: "Python 版本", type: "text", placeholder: "3.11" },
      { key: "setup_command", label: "Setup 命令", type: "textarea", rows: 3, placeholder: "pip install -r requirements.txt" },
    ],
  },
  "gpu.allocate": {
    label: "分配 GPU",
    description: "根据空闲显存和策略选择运行资源",
    configFields: [
      { key: "server_id", label: "目标服务器提示", type: "text", placeholder: "auto / gpu-01" },
      {
        key: "gpu_policy",
        label: "GPU 策略",
        type: "select",
        options: [
          { value: "auto", label: "自动选择" },
          { value: "manual", label: "手动指定" },
          { value: "cpu", label: "仅 CPU" },
        ],
      },
      { key: "min_free_memory_gib", label: "最低空闲显存 GiB", type: "text", placeholder: "16" },
      { key: "notes", label: "调度备注", type: "textarea", rows: 3, placeholder: "例如优先 3090 / 避开正在占用的机器" },
    ],
  },
  "run.command": {
    label: "运行任务",
    description: "生成可执行任务",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "env_name", label: "环境名", type: "text", placeholder: "agent-workspace" },
      { key: "server_id", label: "目标服务器提示", type: "text", placeholder: "例如 gpu-01 / auto" },
      {
        key: "gpu_policy",
        label: "GPU 策略",
        type: "select",
        options: [
          { value: "auto", label: "自动选择" },
          { value: "manual", label: "手动指定" },
          { value: "cpu", label: "仅 CPU" },
        ],
      },
      { key: "run_command", label: "Run 命令", type: "textarea", rows: 4, placeholder: "python train.py --config configs/base.yaml" },
      { key: "schedule", label: "定时 / 批量计划", type: "text", placeholder: "每天 02:00 / sweep:v1" },
    ],
  },
  "artifact.collect": {
    label: "收集产物",
    description: "汇总日志、指标、模型文件和输出路径",
    configFields: [
      { key: "workspace_dir", label: "工作目录", type: "text", placeholder: "/path/to/workspace" },
      { key: "artifact_paths", label: "产物路径", type: "textarea", rows: 3, placeholder: "runs\noutputs\ncheckpoints\nlogs" },
      { key: "metric_paths", label: "指标路径", type: "text", placeholder: "runs/latest/metrics.json" },
      { key: "notes", label: "收集要求", type: "textarea", rows: 3, placeholder: "需要保留哪些指标、日志和复跑命令" },
    ],
  },
  "eval.report": {
    label: "结果整理",
    description: "汇总指标与产出",
    configFields: [
      { key: "report_command", label: "Report 命令", type: "text", placeholder: "python eval.py --latest" },
      { key: "metric_paths", label: "指标文件路径", type: "text", placeholder: "runs/latest/metrics.json" },
      { key: "notes", label: "结果要求", type: "textarea", rows: 3, placeholder: "记录需要重点看的指标和对比基线" },
    ],
  },
  "notify.user": {
    label: "通知用户",
    description: "把结果推回给人",
    configFields: [
      {
        key: "channel",
        label: "通知渠道",
        type: "select",
        options: [
          { value: "ui", label: "界面消息" },
          { value: "log", label: "日志" },
          { value: "email", label: "邮件（占位）" },
        ],
      },
      { key: "message", label: "消息模板", type: "textarea", rows: 3, placeholder: "结果完成后需要告知什么" },
    ],
  },
  "custom.step": {
    label: "自定义步骤",
    description: "留给人工或 agent 的自由节点",
    configFields: [
      { key: "goal", label: "目标", type: "text", placeholder: "这个节点要完成什么" },
      { key: "command", label: "可选命令", type: "textarea", rows: 3, placeholder: "留空表示纯人工 / 纯分析节点" },
      { key: "output_expectation", label: "输出预期", type: "text", placeholder: "需要交付的结果或文档" },
    ],
  },
};

const WORKSPACE_TOOL_CATALOG = [
  {
    id: "workflow.plan",
    label: "工作流规划",
    category: "workflow",
    capability: "write",
    description: "拆分目标、编排节点、写交接说明。",
  },
  {
    id: "workflow.edit",
    label: "工作流编辑",
    category: "workflow",
    capability: "control",
    description: "新增、移动、删除或重排节点。",
  },
  {
    id: "web.search",
    label: "网络检索",
    category: "research",
    capability: "read",
    description: "搜索论文、repo、issue、文档和公开说明。",
  },
  {
    id: "repo.search",
    label: "仓库搜寻",
    category: "research",
    capability: "read",
    description: "围绕关键字找候选仓库和镜像。",
  },
  {
    id: "repo.clone",
    label: "仓库克隆",
    category: "repo",
    capability: "execute",
    description: "把仓库拉到工作目录。",
  },
  {
    id: "repo.read",
    label: "仓库阅读",
    category: "repo",
    capability: "read",
    description: "读取源码、README、配置和入口说明。",
  },
  {
    id: "repo.inspect",
    label: "仓库检查",
    category: "repo",
    capability: "read",
    description: "扫描依赖、入口、默认参数和输出目录。",
  },
  {
    id: "path.resolve",
    label: "路径解析",
    category: "path",
    capability: "read",
    description: "确认工作目录、数据目录、日志目录和输出路径。",
  },
  {
    id: "dataset.find",
    label: "数据集发现",
    category: "data",
    capability: "read",
    description: "从论文、README、线索和本地数据盘定位数据集。",
  },
  {
    id: "file.browse",
    label: "文件浏览",
    category: "file",
    capability: "read",
    description: "浏览本地或远端目录树。",
  },
  {
    id: "file.read",
    label: "文件预览",
    category: "file",
    capability: "read",
    description: "读取日志、配置和脚本片段。",
  },
  {
    id: "dir.scan",
    label: "目录扫描",
    category: "host",
    capability: "read",
    description: "查看可用工作目录和挂载盘。",
  },
  {
    id: "host.exec",
    label: "主机执行",
    category: "host",
    capability: "execute",
    description: "在目标主机上跑检查、命令和维护脚本。",
  },
  {
    id: "gpu.inspect",
    label: "GPU 探测",
    category: "gpu",
    capability: "read",
    description: "查询可用显卡、利用率、显存和温度。",
  },
  {
    id: "gpu.allocate",
    label: "GPU 选择",
    category: "gpu",
    capability: "control",
    description: "为任务挑选空闲或最合适的显卡。",
  },
  {
    id: "env.inspect",
    label: "环境检查",
    category: "env",
    capability: "read",
    description: "检查 conda、python3、tmux、rsync 等依赖。",
  },
  {
    id: "env.infer",
    label: "环境推断",
    category: "env",
    capability: "read",
    description: "从依赖文件、README 和运行脚本推断安装步骤。",
  },
  {
    id: "env.prepare",
    label: "环境准备",
    category: "env",
    capability: "execute",
    description: "创建或激活 conda / venv 并安装依赖。",
  },
  {
    id: "env.create",
    label: "环境创建",
    category: "env",
    capability: "execute",
    description: "初始化新的 Python 环境与基础依赖。",
  },
  {
    id: "job.run",
    label: "任务提交",
    category: "run",
    capability: "execute",
    description: "把命令提交到任务中心并落到 tmux。",
  },
  {
    id: "job.stop",
    label: "任务停止",
    category: "run",
    capability: "control",
    description: "停止正在运行的任务或进程。",
  },
  {
    id: "job.reorder",
    label: "队列重排",
    category: "run",
    capability: "control",
    description: "调整等待中任务的优先顺序。",
  },
  {
    id: "log.read",
    label: "日志读取",
    category: "log",
    capability: "read",
    description: "读取任务日志、输出和 tmux 片段。",
  },
  {
    id: "artifact.read",
    label: "产物读取",
    category: "artifact",
    capability: "read",
    description: "查看项目产物、指标和中间结果。",
  },
  {
    id: "artifact.collect",
    label: "产物收集",
    category: "artifact",
    capability: "read",
    description: "收集日志、指标、模型文件和复跑命令。",
  },
  {
    id: "artifact.write",
    label: "产物写入",
    category: "artifact",
    capability: "write",
    description: "写入整理后的结论、摘要和检查点。",
  },
  {
    id: "report.write",
    label: "结果报告",
    category: "artifact",
    capability: "write",
    description: "输出评估报告、对比摘要和下一步建议。",
  },
  {
    id: "notify.user",
    label: "用户通知",
    category: "notify",
    capability: "write",
    description: "把关键结论、失败原因或待确认项推回给用户。",
  },
  {
    id: "chat.write",
    label: "项目对话",
    category: "chat",
    capability: "write",
    description: "把自然语言输入写入项目上下文与对话历史。",
  },
  {
    id: "schedule.plan",
    label: "调度规划",
    category: "workflow",
    capability: "write",
    description: "记录定时运行、批量 sweep 和重复执行计划。",
  },
];

const DEFAULT_WORKSPACE_AGENTS = [
  {
    id: "planner",
    name: "Planner",
    role: "planner",
    prompt: "把用户目标整理成可执行节点和审批点。",
    tools: ["workflow.edit", "workflow.plan", "artifact.write", "chat.write"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "researcher",
    name: "Researcher",
    role: "researcher",
    prompt: "检索论文、repo、issue、文档和候选方案。",
    tools: ["web.search", "repo.search", "dataset.find", "artifact.read", "artifact.write"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "repo-scout",
    name: "Repo Scout",
    role: "repo_scout",
    prompt: "理解仓库结构、依赖、入口和运行方式。",
    tools: ["repo.clone", "repo.read", "repo.inspect", "path.resolve", "file.read"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "gpu-scout",
    name: "GPU Scout",
    role: "gpu_scout",
    prompt: "找可用显卡、判断忙碌程度并给出可运行的主机。",
    tools: ["gpu.inspect", "gpu.allocate", "host.exec", "dir.scan"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "env-builder",
    name: "Env Builder",
    role: "env_builder",
    prompt: "准备环境、检查依赖并整理安装步骤。",
    tools: ["env.inspect", "env.infer", "env.prepare", "env.create", "host.exec"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "runner",
    name: "Runner",
    role: "runner",
    prompt: "把运行配方转换为实际任务并跟踪输出。",
    tools: ["job.run", "job.stop", "job.reorder", "gpu.allocate", "log.read"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "evaluator",
    name: "Evaluator",
    role: "evaluator",
    prompt: "解析结果、指标、产出文件和回归结论。",
    tools: ["artifact.collect", "artifact.read", "log.read", "report.write", "notify.user"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "watcher",
    name: "Watcher",
    role: "watcher",
    prompt: "监控运行异常、卡住的任务和日志里的错误信号。",
    tools: ["log.read", "job.stop", "notify.user", "artifact.write"],
    provider_profile_id: "",
    enabled: true,
  },
  {
    id: "reporter",
    name: "Reporter",
    role: "reporter",
    prompt: "把过程、结果和下一步建议整理成可分享的总结。",
    tools: ["artifact.read", "artifact.write", "report.write", "chat.write"],
    provider_profile_id: "",
    enabled: true,
  },
];

const SOURCE_AGENT_ROLE_IDS = {
  repo: ["planner", "repo_scout", "gpu_scout", "env_builder", "runner", "evaluator", "watcher"],
  paper: ["planner", "researcher", "repo_scout", "gpu_scout", "env_builder", "runner", "evaluator", "reporter"],
  idea: ["planner", "researcher", "repo_scout", "gpu_scout", "env_builder", "runner", "evaluator", "reporter"],
};

const PROVIDER_VENDOR_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "qwen", label: "Qwen" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "custom", label: "Custom" },
];

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

async function fetchJson(url, options) {
  const response = await fetch(url, options);
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

function consumeClick(event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();
}

function actionProxyEvent(baseEvent, currentTarget) {
  return {
    preventDefault: () => baseEvent?.preventDefault?.(),
    stopPropagation: () => baseEvent?.stopPropagation?.(),
    currentTarget,
  };
}

function scheduleRefreshButtonStateUpdate(delayMs) {
  if (state.ui.statusBusyTimer) clearTimeout(state.ui.statusBusyTimer);
  if (delayMs <= 0) {
    state.ui.statusBusyTimer = null;
    updateRefreshButtonState();
    return;
  }
  state.ui.statusBusyTimer = setTimeout(() => {
    state.ui.statusBusyTimer = null;
    updateRefreshButtonState();
  }, delayMs);
}

function updateRefreshButtonState() {
  const button = $("refreshBtn");
  if (!button) return;
  const now = Date.now();
  const busy = state.ui.statusBusyCount > 0 || now < (state.ui.statusBusyVisibleUntil || 0);
  button.classList.toggle("busy", busy);
  button.setAttribute("aria-busy", busy ? "true" : "false");
  button.disabled = state.ui.statusBusyCount > 0;
  button.title = busy ? "正在刷新" : "刷新";
  if (busy && state.ui.statusBusyCount === 0 && state.ui.statusBusyVisibleUntil > now) {
    scheduleRefreshButtonStateUpdate(state.ui.statusBusyVisibleUntil - now);
  } else if (!busy && state.ui.statusBusyVisibleUntil && now >= state.ui.statusBusyVisibleUntil) {
    state.ui.statusBusyVisibleUntil = 0;
  }
}

function setLogPaneOpen(open) {
  const pane = $("logPane");
  if (!pane) return;
  pane.hidden = !open;
  document.body.classList.toggle("has-log-pane", open);
}

function storedFormState(formId) {
  if (formId === "workspaceForm") return loadStoredJson(STORAGE_KEYS.workspaceForm, {});
  if (formId === "jobForm") return loadStoredJson(STORAGE_KEYS.jobForm, {});
  if (formId === "taskPlanForm") return loadStoredJson(STORAGE_KEYS.taskPlanForm, {});
  if (formId === "transferForm") return loadStoredJson(STORAGE_KEYS.transferForm, {});
  return {};
}

function formStorageKey(formId) {
  if (formId === "workspaceForm") return STORAGE_KEYS.workspaceForm;
  if (formId === "jobForm") return STORAGE_KEYS.jobForm;
  if (formId === "taskPlanForm") return STORAGE_KEYS.taskPlanForm;
  if (formId === "transferForm") return STORAGE_KEYS.transferForm;
  return "";
}

function captureFormState(form) {
  const data = {};
  form.querySelectorAll("[name]").forEach((field) => {
    if (!field.name) return;
    if (field.type === "checkbox") data[field.name] = Boolean(field.checked);
    else data[field.name] = field.value;
  });
  return data;
}

function persistFormState(formId) {
  const form = $(formId);
  const key = formStorageKey(formId);
  if (!form || !key) return;
  saveStoredJson(key, captureFormState(form));
}

function restoreFormState(formId) {
  const form = $(formId);
  const data = storedFormState(formId);
  if (!form || !data || typeof data !== "object") return;
  form.querySelectorAll("[name]").forEach((field) => {
    if (!(field.name in data)) return;
    if (field.type === "checkbox") field.checked = Boolean(data[field.name]);
    else field.value = data[field.name];
  });
}

const statusText = {
  draft: "草稿",
  ready: "已就绪",
  preview: "预览",
  pending: "未运行",
  idle: "空闲",
  busy: "忙碌",
  blocked: "等待 Profile",
  queued: "等待中",
  starting: "启动中",
  running: "运行中",
  done: "已完成",
  failed: "失败",
  stopped: "已停止",
  offline: "离线",
};

const kindText = {
  command: "单命令",
  "batch-item": "批量",
  "profiled-batch-item": "批量",
  profile: "Profile",
  transfer: "文件传输",
};

function zhStatus(value) {
  return statusText[value] || value || "-";
}

function zhKind(value) {
  return kindText[value] || value || "任务";
}

function fmtMiB(value) {
  const n = Number(value || 0);
  if (n >= 1024) return `${(n / 1024).toFixed(1)} GiB`;
  return `${n} MiB`;
}

function formatBytes(value) {
  let n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
  let index = 0;
  while (n >= 1024 && index < units.length - 1) {
    n /= 1024;
    index += 1;
  }
  if (index === 0) return `${Math.round(n)} ${units[index]}`;
  return `${n.toFixed(n >= 10 ? 1 : 2)} ${units[index]}`;
}

function formatPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return `${Math.max(0, Math.min(100, n)).toFixed(n % 1 === 0 ? 0 : 1)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function stripAnsi(value) {
  return String(value || "")
    .replace(/\uFFFD\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
    .replace(/\x1b\][^\x07]*(?:\x07|\x1b\\)/g, "")
    .replace(/\x1b[()#%*+\-.\/][0-9A-Za-z]/g, "")
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "");
}

function fmtDate(value) {
  if (!value) return "";
  return String(value).replace("T", " ").slice(0, 16);
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

function parseLineList(value) {
  if (Array.isArray(value)) {
    return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
  }
  return Array.from(new Set(String(value || "").split(/\r?\n+/).map((item) => item.trim()).filter(Boolean)));
}

function parseTagList(value) {
  if (Array.isArray(value)) {
    return Array.from(new Set(value.map((item) => String(item || "").trim()).filter(Boolean)));
  }
  return Array.from(new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean)));
}

function safeId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "item";
}

function currentWorkspaceSourceType() {
  return String(workspaceFormPayload().source_type || selectedWorkspace()?.source?.type || "repo");
}

function recommendedAgentTemplateByRole(role) {
  return DEFAULT_WORKSPACE_AGENTS.find((agent) => agent.role === role || agent.id === role) || null;
}

function recommendedAgentRoleIds(sourceType = currentWorkspaceSourceType()) {
  const fallback = SOURCE_AGENT_ROLE_IDS.repo;
  return SOURCE_AGENT_ROLE_IDS[String(sourceType || "repo")] || fallback;
}

function recommendedAgentTemplatesForSource(sourceType = currentWorkspaceSourceType()) {
  return recommendedAgentRoleIds(sourceType)
    .map((role) => deepClone(recommendedAgentTemplateByRole(role), null))
    .filter(Boolean);
}

function workspaceAgentLibraryTemplates(sourceType = currentWorkspaceSourceType()) {
  const primary = recommendedAgentTemplatesForSource(sourceType);
  const seen = new Set(primary.map((agent) => agent.role));
  DEFAULT_WORKSPACE_AGENTS.forEach((agent) => {
    if (seen.has(agent.role)) return;
    primary.push(deepClone(agent, null));
  });
  return primary;
}

function defaultWorkspaceTools() {
  return deepClone(WORKSPACE_TOOL_CATALOG, []);
}

function defaultWorkspaceAgents(sourceType = currentWorkspaceSourceType()) {
  return recommendedAgentTemplatesForSource(sourceType);
}

function defaultWorkspaceModel() {
  return {
    provider_profile_id: "",
    routing_mode: "workspace_default",
    chat_agent_id: "",
    notes: "",
  };
}

function defaultWorkspaceNodes(sourceType = "repo") {
  const nodeTemplates = {
    repo: [
      { kind: "source.repo", title: "仓库输入" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
    paper: [
      { kind: "source.paper", title: "论文输入" },
      { kind: "research.search", title: "检索资料" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
    idea: [
      { kind: "source.idea", title: "想法输入" },
      { kind: "research.search", title: "检索资料" },
      { kind: "repo.clone", title: "克隆仓库" },
      { kind: "path.resolve", title: "解析路径" },
      { kind: "repo.inspect", title: "检查仓库" },
      { kind: "dataset.find", title: "发现数据集" },
      { kind: "env.infer", title: "推断环境" },
      { kind: "env.prepare", title: "准备环境" },
      { kind: "gpu.allocate", title: "分配 GPU" },
      { kind: "run.command", title: "运行任务" },
      { kind: "artifact.collect", title: "收集产物" },
      { kind: "eval.report", title: "结果整理" },
    ],
  };

  return (nodeTemplates[sourceType] || nodeTemplates.repo).map((template, index) => ({
    id: makeClientId("node"),
    kind: template.kind,
    title: template.title,
    order: index,
    config: workspaceNodeDefaultConfig(template.kind),
    handler: { mode: "agent" },
    runtime: {},
  }));
}

function defaultWorkspaceForm(sourceType = "repo") {
  const baseDefaults = {
    name: "",
    brief: "",
    tags: [],
    status: "draft",
    env_name: "agent-workspace",
    env_manager: "conda",
    python_version: "3.11",
    setup_command: "pip install -r requirements.txt",
    run_command: "",
    report_command: "",
    schedule: "",
  };

  const sourceDefaults = {
    repo: {
      source_type: "repo",
      repo_url: "",
      repo_ref: "main",
      workspace_dir: "",
    },
    paper: {
      source_type: "paper",
      paper_url: "",
      workspace_dir: "",
    },
    idea: {
      source_type: "idea",
      idea_text: "",
      workspace_dir: "",
    },
  };

  return {
    ...baseDefaults,
    ...(sourceDefaults[sourceType] || sourceDefaults.repo),
    nodes: defaultWorkspaceNodes(sourceType),
    agents: defaultWorkspaceAgents(sourceType),
    tools: defaultWorkspaceTools(),
    model: defaultWorkspaceModel(),
  };
}

function workspaceToolById(toolId, list = state.workspaceToolsDraft) {
  return list.find((item) => item.id === toolId) || null;
}

function workspaceToolLabel(toolId, list = state.workspaceToolsDraft) {
  return workspaceToolById(toolId, list)?.label || toolId || "未命名工具";
}

function workspaceToolCategoryLabel(category) {
  const labels = {
    workflow: "工作流",
    research: "检索",
    data: "数据",
    repo: "仓库",
    path: "路径",
    file: "文件",
    host: "主机",
    gpu: "GPU",
    env: "环境",
    run: "运行",
    log: "日志",
    artifact: "产物",
    notify: "通知",
    chat: "对话",
    general: "通用",
  };
  return labels[String(category || "general")] || String(category || "通用");
}

function workspaceToolsByCategory(tools = state.workspaceToolsDraft) {
  const buckets = new Map();
  tools.forEach((tool) => {
    const key = String(tool.category || "general");
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(tool);
  });
  return Array.from(buckets.entries()).map(([category, items]) => ({
    category,
    label: workspaceToolCategoryLabel(category),
    items,
  }));
}

function workspaceToolSummary(tool) {
  if (!tool) return "";
  const parts = [
    workspaceToolCategoryLabel(tool.category || "general"),
    tool.capability || "read",
  ];
  if (tool.description) parts.push(tool.description);
  return parts.join(" · ");
}

function normalizeWorkspaceToolDraft(tool = {}, index = 0) {
  const fallbackId = safeId(tool.label || tool.id || `tool-${index + 1}`);
  return {
    id: String(tool.id || fallbackId),
    label: String(tool.label || tool.display_name || `Tool ${index + 1}`),
    category: String(tool.category || "general"),
    capability: String(tool.capability || "read"),
    description: String(tool.description || ""),
    enabled: tool.enabled !== false,
    notes: String(tool.notes || ""),
  };
}

function normalizeWorkspaceAgentDraft(agent = {}, index = 0, toolIds = []) {
  const roleSeed = String(agent.role || agent.name || `agent-${index + 1}`).trim() || `agent-${index + 1}`;
  const tools = Array.isArray(agent.tools) ? agent.tools.map((item) => String(item || "").trim()).filter(Boolean) : parseTagList(agent.tools || "");
  const allowedTools = new Set(toolIds.map((item) => String(item || "").trim()).filter(Boolean));
  const filteredTools = allowedTools.size ? tools.filter((tool) => allowedTools.has(tool)) : tools;
  return {
    id: String(agent.id || safeId(roleSeed)),
    name: String(agent.name || `Agent ${index + 1}`),
    role: String(agent.role || safeId(roleSeed)),
    prompt: String(agent.prompt || ""),
    tools: filteredTools,
    provider_profile_id: String(agent.provider_profile_id || ""),
    enabled: agent.enabled !== false,
  };
}

function syncWorkspaceNodeHandlerNamesFromAgents(agentList = state.workspaceAgentsDraft) {
  state.workspaceNodesDraft = state.workspaceNodesDraft.map((node) => {
    const linked = agentList.find((agent) => agent.id === node.handler?.agent_id);
    if (!linked) return node;
    return {
      ...node,
      handler: {
        ...(node.handler || {}),
        name: linked.name,
      },
    };
  });
  persistWorkspaceNodesDraft();
}

function recommendedRoleIdsForCurrentStarter() {
  const ids = new Set();
  state.workspaceNodesDraft.forEach((node) => {
    const suggestion = recommendedNodeAssignment(node.kind);
    if (suggestion.role) ids.add(suggestion.role);
  });
  return ids;
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

function recommendedToolMissingCount() {
  const existing = new Set(state.workspaceToolsDraft.map((tool) => tool.id));
  return WORKSPACE_TOOL_CATALOG.filter((tool) => !existing.has(tool.id)).length;
}

function mergeRecommendedWorkspaceTools(options = {}) {
  const existing = new Set(state.workspaceToolsDraft.map((tool) => tool.id));
  const missing = WORKSPACE_TOOL_CATALOG
    .filter((tool) => !existing.has(tool.id))
    .map((tool) => deepClone(tool, tool));
  if (!missing.length) {
    if (!options.silent) setWorkspaceMessage("推荐工具已经齐了。");
    return 0;
  }
  setWorkspaceToolsDraft([...state.workspaceToolsDraft, ...missing], {
    render: options.render !== false,
    selectedToolId: state.selectedWorkspaceToolId,
  });
  if (!options.silent) setWorkspaceMessage(`已补齐 ${missing.length} 个推荐工具。`);
  return missing.length;
}

function sortWorkspaceAgentsByRecommendation(list, sourceType = currentWorkspaceSourceType()) {
  const order = workspaceAgentLibraryTemplates(sourceType).map((agent) => agent.role);
  const rank = new Map(order.map((role, index) => [role, index]));
  return list.slice().sort((left, right) => {
    const leftRank = rank.has(left.role) ? rank.get(left.role) : Number.MAX_SAFE_INTEGER;
    const rightRank = rank.has(right.role) ? rank.get(right.role) : Number.MAX_SAFE_INTEGER;
    if (leftRank !== rightRank) return leftRank - rightRank;
    return String(left.name || left.role).localeCompare(String(right.name || right.role), "zh-Hans-CN", {
      numeric: true,
      sensitivity: "base",
    });
  });
}

function applyAgentTemplate(role, options = {}) {
  mergeRecommendedWorkspaceTools({ render: false, silent: true });
  const template = recommendedAgentTemplateByRole(role);
  if (!template) return null;
  const toolIds = state.workspaceToolsDraft.map((item) => item.id);
  const index = state.workspaceAgentsDraft.findIndex((agent) => agent.role === template.role || agent.id === template.id);
  const list = state.workspaceAgentsDraft.slice();
  let nextAgent = null;
  if (index >= 0) {
    const current = list[index];
    const mergedTools = Array.from(new Set([...(current.tools || []), ...(template.tools || [])]));
    nextAgent = normalizeWorkspaceAgentDraft({
      ...current,
      name: current.name || template.name,
      role: template.role,
      prompt: template.prompt,
      tools: mergedTools,
    }, index, toolIds);
    list.splice(index, 1, nextAgent);
  } else {
    nextAgent = normalizeWorkspaceAgentDraft(template, list.length, toolIds);
    list.push(nextAgent);
  }
  const sorted = sortWorkspaceAgentsByRecommendation(list);
  setWorkspaceAgentsDraft(sorted, {
    render: options.render !== false,
    selectedAgentId: nextAgent.id,
  });
  syncWorkspaceNodeHandlerNamesFromAgents(sorted);
  if (!options.silent) {
    setWorkspaceMessage(index >= 0 ? `已同步 ${nextAgent.name} 模板。` : `已加入 ${nextAgent.name}。`);
  }
  return nextAgent;
}

function mergeRecommendedWorkspaceAgents(options = {}) {
  const sourceType = currentWorkspaceSourceType();
  const templates = recommendedAgentTemplatesForSource(sourceType);
  let added = 0;
  let updated = 0;
  templates.forEach((template) => {
    const existing = state.workspaceAgentsDraft.find((agent) => agent.role === template.role || agent.id === template.id);
    const before = existing ? JSON.stringify(existing) : "";
    const result = applyAgentTemplate(template.role, { render: false, silent: true });
    if (!existing && result) added += 1;
    else if (existing && result && JSON.stringify(result) !== before) updated += 1;
  });
  renderWorkspacePanels();
  if (!options.silent) {
    if (!added && !updated) setWorkspaceMessage("推荐角色已经是最新状态。");
    else setWorkspaceMessage(`已补齐/同步 ${added + updated} 个推荐角色。`);
  }
  return { added, updated };
}

function applyRecommendedNodeAssignments() {
  mergeRecommendedWorkspaceAgents({ silent: true });
  const agentsByRole = new Map(state.workspaceAgentsDraft.map((agent) => [agent.role, agent]));
  let changedCount = 0;
  state.workspaceNodesDraft = state.workspaceNodesDraft.map((node) => {
    const suggestion = recommendedNodeAssignment(node.kind);
    const linkedAgent = suggestion.role ? agentsByRole.get(suggestion.role) : null;
    const nextHandler = {
      ...(node.handler || {}),
      mode: suggestion.mode,
      agent_id: linkedAgent?.id || "",
      name: linkedAgent?.name || suggestion.displayName,
      handoff: suggestion.handoff,
    };
    if (
      nextHandler.mode === node.handler?.mode &&
      nextHandler.agent_id === node.handler?.agent_id &&
      nextHandler.name === node.handler?.name &&
      nextHandler.handoff === node.handler?.handoff
    ) {
      return node;
    }
    changedCount += 1;
    return { ...node, handler: nextHandler };
  });
  persistWorkspaceNodesDraft();
  renderWorkspacePanels();
  setWorkspaceMessage(changedCount ? `已按推荐角色刷新 ${changedCount} 个节点分工。` : "当前节点分工已经符合推荐模板。");
}

function normalizeWorkspaceModelDraft(model = {}) {
  const routingMode = ["workspace_default", "agent_override"].includes(String(model.routing_mode || ""))
    ? String(model.routing_mode)
    : "workspace_default";
  return {
    provider_profile_id: String(model.provider_profile_id || ""),
    routing_mode: routingMode,
    chat_agent_id: String(model.chat_agent_id || ""),
    notes: String(model.notes || ""),
  };
}

function normalizeWorkspaceChatMessage(message = {}, index = 0) {
  const role = ["user", "assistant", "system"].includes(String(message.role || ""))
    ? String(message.role)
    : "user";
  return {
    id: String(message.id || makeClientId(`chat-${index}`)),
    role,
    text: String(message.text || ""),
    agent_id: String(message.agent_id || ""),
    agent_name: String(message.agent_name || ""),
    created_at: String(message.created_at || ""),
  };
}

function normalizeProviderProfile(profile = {}, index = 0) {
  const label = String(profile.label || "").trim() || `Profile ${index + 1}`;
  return {
    id: String(profile.id || makeClientId("provider")),
    label,
    vendor: String(profile.vendor || "openai"),
    base_url: String(profile.base_url || ""),
    model: String(profile.model || ""),
    api_key: String(profile.api_key || ""),
    is_default: Boolean(profile.is_default),
    is_new: Boolean(profile.is_new),
  };
}

function normalizeWorkspaceToolsDraft(tools = []) {
  const list = (Array.isArray(tools) ? tools : [])
    .map((item, index) => normalizeWorkspaceToolDraft(item, index))
    .filter(Boolean);
  return list.length ? list : defaultWorkspaceTools();
}

function setWorkspaceToolsDraft(tools = [], options = {}) {
  const list = normalizeWorkspaceToolsDraft(tools);
  state.workspaceToolsDraft = list;
  const selectedId = String(options.selectedToolId || state.selectedWorkspaceToolId || "").trim();
  state.selectedWorkspaceToolId = state.workspaceToolsDraft.some((item) => item.id === selectedId)
    ? selectedId
    : state.workspaceToolsDraft[0]?.id || "";
  if (options.render !== false) {
    renderWorkspaceTools();
    renderWorkspaceAgents();
  }
  saveStoredJson(STORAGE_KEYS.workspaceTools, state.workspaceToolsDraft);
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceTool, state.selectedWorkspaceToolId);
}

function selectedWorkspaceTool() {
  return workspaceToolById(state.selectedWorkspaceToolId, state.workspaceToolsDraft) || state.workspaceToolsDraft[0] || null;
}

function persistWorkspaceAgentDrafts() {
  saveStoredJson(STORAGE_KEYS.workspaceAgents, state.workspaceAgentsDraft);
}

function persistWorkspaceModelDraft() {
  saveStoredJson(STORAGE_KEYS.workspaceModel, state.workspaceModelDraft);
}

function persistWorkspaceToolDrafts() {
  saveStoredJson(STORAGE_KEYS.workspaceTools, state.workspaceToolsDraft);
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceTool, state.selectedWorkspaceToolId);
}

function workspaceAgentToolsSummary(agent, list = state.workspaceToolsDraft) {
  const tools = Array.isArray(agent?.tools) ? agent.tools : [];
  if (!tools.length) return "未配置工具";
  return tools.map((toolId) => workspaceToolLabel(toolId, list)).join(" · ");
}

function selectWorkspaceTool(toolId) {
  if (!workspaceToolById(toolId)) return;
  const changed = state.selectedWorkspaceToolId !== toolId;
  state.selectedWorkspaceToolId = toolId;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceTool, toolId);
  renderWorkspaceTools();
}

function updateSelectedWorkspaceTool(updater) {
  const index = state.workspaceToolsDraft.findIndex((item) => item.id === state.selectedWorkspaceToolId);
  if (index < 0) return;
  const current = state.workspaceToolsDraft[index];
  const previousId = current.id;
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  const normalized = normalizeWorkspaceToolDraft(next, index);
  state.workspaceToolsDraft.splice(index, 1, normalized);
  state.selectedWorkspaceToolId = normalized.id;
  persistWorkspaceToolDrafts();
  state.workspaceAgentsDraft = state.workspaceAgentsDraft.map((agent) => ({
    ...agent,
    tools: (agent.tools || [])
      .map((toolId) => (toolId === previousId ? normalized.id : toolId))
      .filter((toolId) => workspaceToolById(toolId, state.workspaceToolsDraft) || toolId === normalized.id),
  }));
  persistWorkspaceAgentDrafts();
  renderWorkspaceTools();
  renderWorkspaceAgents();
}

function addWorkspaceTool() {
  const tool = normalizeWorkspaceToolDraft({
    id: makeClientId("tool"),
    label: `Tool ${state.workspaceToolsDraft.length + 1}`,
    category: "custom",
    capability: "read",
    description: "",
    enabled: true,
    notes: "",
  }, state.workspaceToolsDraft.length);
  state.workspaceToolsDraft.push(tool);
  state.selectedWorkspaceToolId = tool.id;
  persistWorkspaceToolDrafts();
  renderWorkspaceTools();
}

function removeWorkspaceTool(toolId) {
  if (state.workspaceToolsDraft.length <= 1) {
    setWorkspaceMessage("至少保留一个工具。", true);
    return;
  }
  state.workspaceToolsDraft = state.workspaceToolsDraft.filter((item) => item.id !== toolId);
  state.workspaceAgentsDraft = state.workspaceAgentsDraft.map((agent) => ({
    ...agent,
    tools: (agent.tools || []).filter((item) => item !== toolId),
  }));
  state.selectedWorkspaceToolId = state.workspaceToolsDraft[0]?.id || "";
  persistWorkspaceToolDrafts();
  persistWorkspaceAgentDrafts();
  renderWorkspaceTools();
  renderWorkspaceAgents();
}

function maskSecret(value) {
  const text = String(value || "");
  if (!text) return "未填写";
  if (text.length <= 8) return `${text.slice(0, 2)}***${text.slice(-1)}`;
  return `${text.slice(0, 4)}...${text.slice(-4)}`;
}

function providerProfileById(profileId, list = state.providerProfiles) {
  return list.find((item) => item.id === profileId) || null;
}

function providerProfileLabel(profile) {
  if (!profile) return "未选择";
  const vendor = PROVIDER_VENDOR_OPTIONS.find((item) => item.value === profile.vendor)?.label || profile.vendor || "Custom";
  const model = String(profile.model || "").trim();
  return model ? `${profile.label} · ${vendor} · ${model}` : `${profile.label} · ${vendor}`;
}

function workspaceAgentById(agentId, list = state.workspaceAgentsDraft) {
  return list.find((item) => item.id === agentId) || null;
}

function workspaceAgentDisplayName(handler = {}) {
  const linked = workspaceAgentById(String(handler.agent_id || ""));
  return linked?.name || handler.name || "未指派";
}

function setWorkspaceAgentsDraft(agents = [], options = {}) {
  const toolIds = state.workspaceToolsDraft.map((item) => item.id);
  const list = (Array.isArray(agents) ? agents : [])
    .map((item, index) => normalizeWorkspaceAgentDraft(item, index, toolIds))
    .filter(Boolean);
  state.workspaceAgentsDraft = list.length ? list : defaultWorkspaceAgents();
  const selectedId = String(options.selectedAgentId || state.selectedWorkspaceAgentId || "").trim();
  state.selectedWorkspaceAgentId = state.workspaceAgentsDraft.some((item) => item.id === selectedId)
    ? selectedId
    : state.workspaceAgentsDraft[0]?.id || "";
  persistWorkspaceAgentDrafts();
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceAgent, state.selectedWorkspaceAgentId);
  if (options.render !== false) {
    renderWorkspaceAgentControls();
    renderWorkspaceAgents();
  }
}

function setWorkspaceModelDraft(model = {}, options = {}) {
  state.workspaceModelDraft = normalizeWorkspaceModelDraft(model);
  if (!workspaceAgentById(state.workspaceModelDraft.chat_agent_id, state.workspaceAgentsDraft)) {
    state.workspaceModelDraft.chat_agent_id = state.workspaceAgentsDraft[0]?.id || "";
  }
  persistWorkspaceModelDraft();
  if (options.render !== false) {
    renderWorkspaceAgentControls();
    renderWorkspaceModel();
  }
}

function setProviderProfiles(profiles = [], options = {}) {
  const list = (Array.isArray(profiles) ? profiles : [])
    .map((item, index) => normalizeProviderProfile(item, index))
    .filter(Boolean);
  state.providerProfiles = list;
  const selectedId = String(options.selectedProfileId || state.selectedProviderProfileId || "").trim();
  state.selectedProviderProfileId = state.providerProfiles.some((item) => item.id === selectedId)
    ? selectedId
    : state.providerProfiles[0]?.id || "";
  // Don't save to localStorage anymore - use API instead
  if (options.render !== false) renderWorkspaceModel();
  if (options.render !== false) renderWorkspaceWorkbench();
}

async function loadProviderProfiles(options = {}) {
  const renderProfiles = options.render !== false;
  try {
    const payload = await fetchJson("/api/provider-profiles");
    const profiles = payload.provider_profiles || [];
    // Transform backend format to frontend format
    const transformed = profiles.map((p) => ({
      id: p.id,
      label: p.name || p.id,
      vendor: p.provider || "openai",
      base_url: p.base_url || "",
      model: (p.models || [])[0] || "",
      api_key: p.api_key_masked || "",
      has_api_key: !!(p.api_key_masked || p.api_key),
      is_default: p.is_default || false,
    }));
    setProviderProfiles(transformed, { render: renderProfiles });
    return transformed;
  } catch (error) {
    console.error("Failed to load provider profiles:", error);
    // Fall back to localStorage on error
    setProviderProfiles(loadStoredArray(STORAGE_KEYS.providerProfiles), { render: renderProfiles });
    return state.providerProfiles;
  }
}

async function saveProviderProfile(profile, options = {}) {
  const payload = {
    id: profile.id,
    name: profile.label || profile.id,
    provider: profile.vendor || "openai",
    base_url: profile.base_url || "",
    api_key: profile.api_key || "",
    models: profile.model ? [profile.model] : [],
    is_default: profile.is_default || false,
  };

  const existing = !options.forceCreate && state.providerProfiles.some((p) => p.id === profile.id && !p.is_new);
  const url = existing ? `/api/provider-profiles/${profile.id}` : "/api/provider-profiles";
  const method = existing ? "PUT" : "POST";

  const response = await fetchJson(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  await loadProviderProfiles();
  return response.provider_profile;
}

async function deleteProviderProfile(profileId) {
  await fetchJson(`/api/provider-profiles/${profileId}`, { method: "DELETE" });
  await loadProviderProfiles();
}

function workspaceNodeMeta(kind) {
  return WORKSPACE_NODE_TYPES[kind] || WORKSPACE_NODE_TYPES["custom.step"];
}

function workspaceNodeLabel(kind) {
  return workspaceNodeMeta(kind).label || kind || "节点";
}

function workspaceNodeKindsForSource(sourceType) {
  if (sourceType === "repo") return [
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
  if (sourceType === "paper") return [
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
  return [
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
}

function workspaceSearchSeed(formData = {}) {
  const idea = String(formData.idea_text || formData.brief || "").trim().split("\n")[0] || "";
  return String(formData.paper_url || "").trim() || idea || String(formData.repo_url || "").trim();
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
    base.query = workspaceSearchSeed(formData);
    base.goal = "检索相关代码仓库、依赖和运行方式";
  } else if (kind === "repo.clone") {
    base.repo_url = String(formData.repo_url || "");
    base.repo_ref = String(formData.repo_ref || "");
    base.workspace_dir = String(formData.workspace_dir || "");
  } else if (kind === "path.resolve") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.data_roots = "";
    base.output_roots = "runs\noutputs\ncheckpoints\nlogs";
  } else if (kind === "repo.inspect") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.focus_paths = "";
    base.questions = "入口、依赖、默认配置、结果目录";
  } else if (kind === "dataset.find") {
    base.query = workspaceSearchSeed(formData);
    base.dataset_hints = String(formData.references || "");
    base.data_roots = "";
    base.expected_layout = "";
  } else if (kind === "env.infer") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.manifest_paths = "requirements.txt, pyproject.toml, environment.yml, setup.py";
    base.env_name = String(formData.env_name || "");
    base.python_version = String(formData.python_version || "");
  } else if (kind === "env.prepare") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.env_name = String(formData.env_name || "");
    base.env_manager = String(formData.env_manager || "conda");
    base.python_version = String(formData.python_version || "");
    base.setup_command = String(formData.setup_command || "");
  } else if (kind === "gpu.allocate") {
    base.server_id = "";
    base.gpu_policy = "auto";
    base.min_free_memory_gib = "";
    base.notes = "";
  } else if (kind === "run.command") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.env_name = String(formData.env_name || "");
    base.server_id = "";
    base.gpu_policy = "auto";
    base.run_command = String(formData.run_command || "");
    base.schedule = String(formData.schedule || "");
  } else if (kind === "artifact.collect") {
    base.workspace_dir = String(formData.workspace_dir || "");
    base.artifact_paths = "runs\noutputs\ncheckpoints\nlogs";
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

function createWorkspaceNode(kind, overrides = {}, index = 0, formData = {}) {
  return normalizeWorkspaceDraftNode({ kind, ...deepClone(overrides, {}) }, index, formData);
}

function normalizeWorkspaceDraftNode(node, index = 0, formData = {}) {
  const kind = String(node?.kind || "custom.step");
  const defaults = workspaceNodeDefaultConfig(kind, formData);
  const config = {
    ...defaults,
    ...(node?.config && typeof node.config === "object" ? node.config : {}),
  };
  return {
    id: String(node?.id || makeClientId("node")),
    kind,
    title: String(node?.title || workspaceNodeLabel(kind)),
    status: String(node?.status || "draft"),
    handler: {
      mode: String(node?.handler?.mode || "human"),
      agent_id: String(node?.handler?.agent_id || ""),
      name: String(node?.handler?.name || ""),
      handoff: String(node?.handler?.handoff || ""),
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
}

function buildWorkspaceStarterNodes(formData = {}) {
  return workspaceNodeKindsForSource(String(formData.source_type || "repo")).map((kind, index) =>
    normalizeWorkspaceDraftNode({ kind }, index, formData));
}

function workspaceLinksFromNodes(nodes = state.workspaceNodesDraft) {
  return nodes.slice(0, -1).map((node, index) => ({
    id: `link-${index + 1}-${node.id}-${nodes[index + 1].id}`,
    from: node.id,
    to: nodes[index + 1].id,
  }));
}

function selectedWorkspaceNode() {
  return state.workspaceNodesDraft.find((item) => item.id === state.selectedWorkspaceNodeId) || state.workspaceNodesDraft[0] || null;
}

function workspaceRunNode(nodes = state.workspaceNodesDraft) {
  const selected = selectedWorkspaceNode();
  if (selected?.kind === "run.command") return selected;
  return nodes.find((item) => item.kind === "run.command") || null;
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

function workspaceNodeRuntimeSummary(node) {
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

function persistWorkspaceNodesDraft() {
  saveStoredJson(STORAGE_KEYS.workspaceNodes, state.workspaceNodesDraft);
}

function workspaceChainSourceType(sourceType) {
  return String(sourceType || "idea") === "mixed" ? "idea" : String(sourceType || "idea");
}

function defaultWorkflowTemplateDraft(sourceType = "repo") {
  const chainSourceType = workspaceChainSourceType(sourceType);
  const defaults = defaultWorkspaceForm(chainSourceType);
  const recipe = {
    enabled: true,
    setup_command: defaults.setup_command || "",
    run_command: defaults.run_command || "",
    report_command: defaults.report_command || "",
    schedule: defaults.schedule || "",
  };
  return {
    id: "",
    name: sourceType === "paper"
      ? "Paper 复现默认流"
      : sourceType === "idea" || sourceType === "mixed"
        ? "Idea 探索默认流"
        : "Repo 复现默认流",
    description: "",
    status: "ready",
    brief: "",
    source: {
      type: sourceType,
      repo_url: "",
      repo_ref: sourceType === "repo" ? "main" : "",
      paper_url: "",
      idea_text: "",
    },
    workspace_dir: "",
    env: {
      name: defaults.env_name || "agent-workspace",
      manager: defaults.env_manager || "conda",
      python: defaults.python_version || "3.11",
    },
    recipes: [recipe],
    model: defaultWorkspaceModel(),
    nodes: defaults.nodes || [],
    links: workspaceLinksFromNodes(defaults.nodes || []),
    tags: [],
    notes: "",
    created_at: "",
    updated_at: "",
  };
}

function normalizeWorkflowTemplateDraft(template = {}) {
  const source = template.source && typeof template.source === "object" ? template.source : {};
  const env = template.env && typeof template.env === "object" ? template.env : {};
  const recipes = Array.isArray(template.recipes) ? template.recipes : [];
  const recipe = recipes.find((item) => item && item.enabled !== false) || recipes[0] || {};
  const sourceType = String(source.type || template.source_type || "repo");
  const chainSourceType = workspaceChainSourceType(sourceType);
  const base = defaultWorkflowTemplateDraft(sourceType);
  const nodes = (Array.isArray(template.nodes) && template.nodes.length
    ? template.nodes
    : buildWorkspaceStarterNodes({ source_type: chainSourceType }))
    .map((node, index) => normalizeWorkspaceDraftNode(node, index, {
      source_type: chainSourceType,
      repo_url: source.repo_url || "",
      repo_ref: source.repo_ref || "",
      paper_url: source.paper_url || "",
      idea_text: source.idea_text || template.brief || "",
      workspace_dir: template.workspace_dir || "",
      env_name: env.name || "",
      env_manager: env.manager || "conda",
      python_version: env.python || "",
      setup_command: recipe.setup_command || "",
      run_command: recipe.run_command || "",
      report_command: recipe.report_command || "",
      schedule: recipe.schedule || "",
      notes: template.notes || "",
    }));
  return {
    ...base,
    id: String(template.id || ""),
    name: String(template.name || base.name),
    description: String(template.description || ""),
    status: String(template.status || base.status),
    brief: String(template.brief || ""),
    source: {
      type: sourceType,
      repo_url: String(source.repo_url || ""),
      repo_ref: String(source.repo_ref || ""),
      paper_url: String(source.paper_url || ""),
      idea_text: String(source.idea_text || ""),
    },
    workspace_dir: String(template.workspace_dir || ""),
    env: {
      name: String(env.name || base.env.name || ""),
      manager: String(env.manager || base.env.manager || "conda"),
      python: String(env.python || base.env.python || ""),
    },
    recipes: [{
      enabled: recipe.enabled !== false,
      setup_command: String(recipe.setup_command || ""),
      run_command: String(recipe.run_command || ""),
      report_command: String(recipe.report_command || ""),
      schedule: String(recipe.schedule || ""),
    }],
    model: normalizeWorkspaceModelDraft(template.model || base.model),
    nodes,
    links: workspaceLinksFromNodes(nodes),
    tags: parseTagList(template.tags || []),
    notes: String(template.notes || ""),
    created_at: String(template.created_at || ""),
    updated_at: String(template.updated_at || ""),
  };
}

function normalizeGlobalAgentDefinitionDraft(agent = {}, index = 0) {
  const base = normalizeWorkspaceAgentDraft(agent, index, state.toolDefinitions.map((item) => item.id));
  return {
    ...base,
    description: String(agent.description || ""),
    created_at: String(agent.created_at || ""),
    updated_at: String(agent.updated_at || ""),
  };
}

function normalizeGlobalToolDefinitionDraft(tool = {}, index = 0) {
  const base = normalizeWorkspaceToolDraft(tool, index);
  return {
    ...base,
    created_at: String(tool.created_at || ""),
    updated_at: String(tool.updated_at || ""),
  };
}

function workflowTemplatePayloadForSave() {
  const draft = normalizeWorkflowTemplateDraft(state.workflowTemplateDraft || {});
  const recipe = Array.isArray(draft.recipes) ? draft.recipes[0] || {} : {};
  return {
    id: draft.id || undefined,
    name: draft.name,
    description: draft.description,
    status: draft.status,
    brief: draft.brief,
    source_type: draft.source?.type || "repo",
    repo_url: draft.source?.repo_url || "",
    repo_ref: draft.source?.repo_ref || "",
    paper_url: draft.source?.paper_url || "",
    idea_text: draft.source?.idea_text || "",
    workspace_dir: draft.workspace_dir || "",
    env_name: draft.env?.name || "",
    env_manager: draft.env?.manager || "conda",
    python_version: draft.env?.python || "",
    setup_command: recipe.setup_command || "",
    run_command: recipe.run_command || "",
    report_command: recipe.report_command || "",
    schedule: recipe.schedule || "",
    model: deepClone(draft.model || {}, {}),
    nodes: deepClone(draft.nodes || [], []),
    links: workspaceLinksFromNodes(draft.nodes || []),
    tags: deepClone(draft.tags || [], []),
    notes: draft.notes || "",
  };
}

function setWorkspaceUseMessage(text = "", isError = false) {
  const box = $("workspaceUseMessage");
  if (!box) return;
  box.textContent = text;
  box.classList.toggle("error", Boolean(isError));
}

function setWorkspaceManageMessage(text = "", isError = false) {
  const box = $("workspaceManageMessage");
  if (!box) return;
  box.textContent = text;
  box.classList.toggle("error", Boolean(isError));
}

function selectWorkflowTemplate(templateId, options = {}) {
  const template = workflowTemplateById(templateId);
  if (!template) return;
  const changed = state.selectedWorkflowTemplateId !== template.id;
  state.selectedWorkflowTemplateId = template.id;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, template.id);
  state.workflowTemplateDraft = normalizeWorkflowTemplateDraft(template);
  state.selectedTemplateNodeId = String(options.selectedNodeId || state.workflowTemplateDraft.nodes?.[0]?.id || "").trim();
  state.ui.workflowTemplateDirty = false;
  renderWorkspaceWorkbench();
}

function selectedWorkflowTemplateNode() {
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes : [];
  return nodes.find((item) => item.id === state.selectedTemplateNodeId) || nodes[0] || null;
}

function updateWorkflowTemplateDraft(updater) {
  const current = normalizeWorkflowTemplateDraft(state.workflowTemplateDraft || {});
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  const normalized = normalizeWorkflowTemplateDraft(next);
  state.workflowTemplateDraft = normalized;
  state.ui.workflowTemplateDirty = true;
  if (!normalized.nodes.some((node) => node.id === state.selectedTemplateNodeId)) {
    state.selectedTemplateNodeId = normalized.nodes[0]?.id || "";
  }
  renderWorkspaceWorkbench();
}

function updateSelectedWorkflowTemplateNode(updater) {
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes.slice() : [];
  const index = nodes.findIndex((item) => item.id === state.selectedTemplateNodeId);
  if (index < 0) return;
  const current = nodes[index];
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  nodes.splice(index, 1, normalizeWorkspaceDraftNode(next, index, {
    source_type: workspaceChainSourceType(state.workflowTemplateDraft?.source?.type || "repo"),
    repo_url: state.workflowTemplateDraft?.source?.repo_url || "",
    repo_ref: state.workflowTemplateDraft?.source?.repo_ref || "",
    paper_url: state.workflowTemplateDraft?.source?.paper_url || "",
    idea_text: state.workflowTemplateDraft?.source?.idea_text || state.workflowTemplateDraft?.brief || "",
    workspace_dir: state.workflowTemplateDraft?.workspace_dir || "",
    env_name: state.workflowTemplateDraft?.env?.name || "",
    env_manager: state.workflowTemplateDraft?.env?.manager || "conda",
    python_version: state.workflowTemplateDraft?.env?.python || "",
  }));
  updateWorkflowTemplateDraft((draft) => ({ ...draft, nodes }));
}

function insertWorkflowTemplateNode(kind) {
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes.slice() : [];
  const currentIndex = nodes.findIndex((node) => node.id === state.selectedTemplateNodeId);
  const insertIndex = currentIndex >= 0 ? currentIndex + 1 : nodes.length;
  const node = createWorkspaceNode(
    String(kind || "custom.step"),
    {},
    insertIndex,
    {
      source_type: workspaceChainSourceType(state.workflowTemplateDraft?.source?.type || "repo"),
      repo_url: state.workflowTemplateDraft?.source?.repo_url || "",
      repo_ref: state.workflowTemplateDraft?.source?.repo_ref || "",
      paper_url: state.workflowTemplateDraft?.source?.paper_url || "",
      idea_text: state.workflowTemplateDraft?.source?.idea_text || state.workflowTemplateDraft?.brief || "",
      workspace_dir: state.workflowTemplateDraft?.workspace_dir || "",
      env_name: state.workflowTemplateDraft?.env?.name || "",
      env_manager: state.workflowTemplateDraft?.env?.manager || "conda",
      python_version: state.workflowTemplateDraft?.env?.python || "",
    },
  );
  nodes.splice(insertIndex, 0, node);
  state.selectedTemplateNodeId = node.id;
  updateWorkflowTemplateDraft((draft) => ({ ...draft, nodes }));
}

function moveWorkflowTemplateNode(direction) {
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes.slice() : [];
  const index = nodes.findIndex((item) => item.id === state.selectedTemplateNodeId);
  if (index < 0) return;
  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= nodes.length) return;
  const [node] = nodes.splice(index, 1);
  nodes.splice(targetIndex, 0, node);
  updateWorkflowTemplateDraft((draft) => ({ ...draft, nodes }));
}

function removeWorkflowTemplateNode() {
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes.slice() : [];
  if (nodes.length <= 1) {
    setWorkspaceManageMessage("至少保留一个节点。", true);
    return;
  }
  const index = nodes.findIndex((item) => item.id === state.selectedTemplateNodeId);
  if (index < 0) return;
  nodes.splice(index, 1);
  state.selectedTemplateNodeId = nodes[Math.max(0, index - 1)]?.id || nodes[0]?.id || "";
  updateWorkflowTemplateDraft((draft) => ({ ...draft, nodes }));
}

function rebuildWorkflowTemplateNodes() {
  const sourceType = workspaceChainSourceType(state.workflowTemplateDraft?.source?.type || "repo");
  const nodes = buildWorkspaceStarterNodes({
    source_type: sourceType,
    repo_url: state.workflowTemplateDraft?.source?.repo_url || "",
    repo_ref: state.workflowTemplateDraft?.source?.repo_ref || "",
    paper_url: state.workflowTemplateDraft?.source?.paper_url || "",
    idea_text: state.workflowTemplateDraft?.source?.idea_text || state.workflowTemplateDraft?.brief || "",
    workspace_dir: state.workflowTemplateDraft?.workspace_dir || "",
    env_name: state.workflowTemplateDraft?.env?.name || "",
    env_manager: state.workflowTemplateDraft?.env?.manager || "conda",
    python_version: state.workflowTemplateDraft?.env?.python || "",
  });
  state.selectedTemplateNodeId = nodes[0]?.id || "";
  updateWorkflowTemplateDraft((draft) => ({ ...draft, nodes }));
}

function selectedWorkspaceExecutionNode() {
  const workspace = selectedWorkspace();
  const nodes = Array.isArray(workspace?.execution?.nodes) && workspace.execution.nodes.length
    ? workspace.execution.nodes
    : Array.isArray(workspace?.nodes)
      ? workspace.nodes.map((node) => ({
          id: node.id,
          kind: node.kind,
          title: node.title || workspaceNodeLabel(node.kind),
          status: node.status || "pending",
          agent_id: node.handler?.agent_id || "",
          agent_name: node.handler?.name || "",
          error: node.runtime?.last_error || "",
          job_id: node.runtime?.last_job_id || "",
          job_status: node.runtime?.last_job_status || "",
          run_count: node.runtime?.run_count || 0,
          trace: Array.isArray(node.runtime?.trace) ? node.runtime.trace : [],
          artifacts: Array.isArray(node.runtime?.artifacts) ? node.runtime.artifacts : [],
          resources: node.runtime?.resources || {},
        }))
      : [];
  const selectedId = String(state.selectedWorkspaceExecutionNodeId || workspace?.execution?.current_node_id || "").trim();
  return nodes.find((item) => item.id === selectedId) || nodes[0] || null;
}

function templatePreviewExecutionNodes(template = selectedWorkflowTemplate()) {
  const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
  return nodes.map((node) => ({
    id: node.id,
    kind: node.kind,
    title: node.title || workspaceNodeLabel(node.kind),
    status: "preview",
    agent_id: node.handler?.agent_id || "",
    agent_name: node.handler?.name || "",
    error: "",
    job_id: "",
    job_status: "",
  }));
}

function selectedExecutionPreviewNode() {
  const nodes = templatePreviewExecutionNodes(selectedWorkflowTemplate());
  const selectedId = String(state.selectedWorkspaceExecutionNodeId || "").trim();
  return nodes.find((item) => item.id === selectedId) || nodes[0] || null;
}

function workspaceExecutionSelectionKey(workspace = selectedWorkspace(), template = selectedWorkflowTemplate()) {
  if (workspace?.id) return `workspace:${workspace.id}`;
  if (template?.id) return `template:${template.id}`;
  return "";
}

function savedWorkspaceExecutionNodeId(key = workspaceExecutionSelectionKey()) {
  if (!key) return "";
  const selections = loadStoredJson(STORAGE_KEYS.workspaceExecutionNodeSelections, {});
  return String(selections?.[key] || "").trim();
}

function saveWorkspaceExecutionNodeSelection(nodeId, key = workspaceExecutionSelectionKey()) {
  if (!key) return;
  const selections = loadStoredJson(STORAGE_KEYS.workspaceExecutionNodeSelections, {});
  selections[key] = String(nodeId || "").trim();
  saveStoredJson(STORAGE_KEYS.workspaceExecutionNodeSelections, selections);
}

function selectWorkspaceExecutionNode(nodeId) {
  const next = String(nodeId || "").trim();
  const changed = state.selectedWorkspaceExecutionNodeId !== next;
  state.selectedWorkspaceExecutionNodeId = next;
  if (changed) markWorkspaceUiInteraction();
  saveWorkspaceExecutionNodeSelection(state.selectedWorkspaceExecutionNodeId);
  renderWorkspaceWorkbench();
}

function workspaceExecutionPhaseGroups(nodes = []) {
  const phaseOrder = ["输入", "发现", "环境", "调度", "回收", "其他"];
  const groups = [];
  const byPhase = {};
  nodes.forEach((node, index) => {
    const phase = workspaceStarterNodePhase(node.kind || "");
    if (!byPhase[phase]) {
      byPhase[phase] = {
        phase,
        order: phaseOrder.includes(phase) ? phaseOrder.indexOf(phase) : phaseOrder.length,
        nodes: [],
      };
      groups.push(byPhase[phase]);
    }
    byPhase[phase].nodes.push({ node, index });
  });
  return groups.sort((left, right) => left.order - right.order);
}

function workspaceExecutionNodePosition(nodes = [], node = null) {
  const list = Array.isArray(nodes) ? nodes : [];
  const index = list.findIndex((item) => item?.id === node?.id);
  const phase = workspaceStarterNodePhase(node?.kind || "");
  const phaseNodes = list.filter((item) => workspaceStarterNodePhase(item?.kind || "") === phase);
  const phaseIndex = phaseNodes.findIndex((item) => item?.id === node?.id);
  return {
    phase,
    index,
    total: list.length,
    phaseIndex,
    phaseTotal: phaseNodes.length,
    label: index >= 0
      ? `${phase} · ${index + 1}/${list.length}`
      : phase,
    detail: phaseIndex >= 0
      ? `阶段内 ${phaseIndex + 1}/${phaseNodes.length}`
      : "未定位",
  };
}

function workspaceNodeAgentContractMarkup(node = null, sourceNode = null, context = {}) {
  const workspace = context.workspace || selectedWorkspace();
  const template = context.template || selectedWorkflowTemplate();
  const model = workspace?.model || template?.model || {};
  const workspaceAgents = Array.isArray(workspace?.agents) ? workspace.agents : [];
  const workspaceTools = Array.isArray(workspace?.tools) ? workspace.tools : [];
  const handler = sourceNode?.handler && typeof sourceNode.handler === "object" ? sourceNode.handler : {};
  const agentId = String(handler.agent_id || node?.agent_id || "").trim();
  const mode = String(handler.mode || (agentId ? "agent" : "human"));
  const agent = workspaceAgentById(agentId, workspaceAgents) || globalAgentById(agentId) || {};
  const agentName = agent.name || handler.name || node?.agent_name || (mode === "human" ? "你" : "未指派 Agent");
  const role = agent.role || mode || "agent";
  const toolIds = Array.isArray(agent.tools) ? agent.tools : parseTagList(agent.tools || "");
  const tools = toolIds
    .map((toolId) => workspaceToolById(toolId, workspaceTools) || globalToolById(toolId) || { id: toolId, label: toolId, category: "tool" })
    .filter(Boolean);
  const providerId = String(agent.provider_profile_id || model.provider_profile_id || "").trim();
  const profile = providerProfileById(providerId);
  const chatAgent = workspaceAgentById(model.chat_agent_id || "", workspaceAgents) || globalAgentById(model.chat_agent_id || "");
  const routingMode = agent.provider_profile_id ? "agent_override" : model.routing_mode || "workspace_default";
  const handoff = String(handler.handoff || agent.description || sourceNode?.notes || "").trim();
  return `
    <div class="workspace-node-contract">
      <article class="workspace-node-contract-card">
        <span>Agent</span>
        <strong title="${escapeHtml(agentName)}">${escapeHtml(agentName)}</strong>
        <em>${escapeHtml(role)} · ${escapeHtml(mode)}</em>
      </article>
      <article class="workspace-node-contract-card">
        <span>Tool allowlist</span>
        <strong>${escapeHtml(tools.length ? `${tools.length} 个工具` : "未配置工具")}</strong>
        <em title="${escapeHtml(tools.map((tool) => tool.label || tool.id).join(" / ") || "等待工具配置")}">${escapeHtml(tools.map((tool) => tool.label || tool.id).slice(0, 4).join(" / ") || "等待工具配置")}</em>
      </article>
      <article class="workspace-node-contract-card">
        <span>AI 路由</span>
        <strong title="${escapeHtml(profile ? providerProfileLabel(profile) : "继承默认")}">${escapeHtml(profile ? providerProfileLabel(profile) : "继承默认")}</strong>
        <em>${escapeHtml(routingMode)}${chatAgent?.name ? ` · ${escapeHtml(chatAgent.name)}` : ""}</em>
      </article>
      <article class="workspace-node-contract-card wide">
        <span>交接</span>
        <strong title="${escapeHtml(handoff || "等待交接说明")}">${escapeHtml(handoff || "等待交接说明")}</strong>
        <em>${escapeHtml(sourceNode?.kind || node?.kind || "未选择节点")}</em>
      </article>
    </div>
  `;
}

function workspaceNodeAutomationScopeMarkup(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  if (!workspace?.id || !kind) return '<div class="empty">创建实例后会显示当前节点的门禁、证据和调度态势。</div>';
  const automation = workspace.automation && typeof workspace.automation === "object" ? workspace.automation : {};
  const checks = Array.isArray(automation.checks) ? automation.checks : [];
  const readiness = automation.execution_readiness && typeof automation.execution_readiness === "object" ? automation.execution_readiness : {};
  const runPlan = automation.run_plan && typeof automation.run_plan === "object" ? automation.run_plan : {};
  const resource = automation.resource_orchestration && typeof automation.resource_orchestration === "object" ? automation.resource_orchestration : {};
  const backfill = automation.evidence_backfill && typeof automation.evidence_backfill === "object" ? automation.evidence_backfill : {};
  const matchingCheck = checks.find((item) => String(item?.node_kind || "").trim() === kind) || null;
  const blockers = [
    ...(Array.isArray(readiness.blockers) ? readiness.blockers : []),
    ...(Array.isArray(runPlan.blocking) ? runPlan.blocking : []),
  ].filter((item) => String(item?.node_kind || "").trim() === kind);
  const warnings = [
    ...(Array.isArray(readiness.warnings) ? readiness.warnings : []),
    ...(Array.isArray(runPlan.warnings) ? runPlan.warnings : []),
  ].filter((item) => String(item?.node_kind || "").trim() === kind);
  const evidenceItems = [];
  (Array.isArray(automation.evidence) ? automation.evidence : []).forEach((group) => {
    (Array.isArray(group?.items) ? group.items : []).forEach((item) => {
      if (String(item?.node_kind || "").trim() !== kind) return;
      evidenceItems.push({
        group: String(group.label || group.id || "证据"),
        label: String(item.label || item.source || item.node_kind || "发现"),
        value: String(item.value || ""),
        status: String(item.status || "ready"),
      });
    });
  });
  const resourceItems = (Array.isArray(resource.items) ? resource.items : [])
    .filter((item) => String(item?.node_kind || "").trim() === kind);
  const backfillItems = (Array.isArray(backfill.items) ? backfill.items : [])
    .filter((item) => String(item?.node_kind || "").trim() === kind);
  const gateStatus = blockers.length
    ? "blocked"
    : matchingCheck?.status || (warnings.length ? "warning" : "ready");
  const gateTitle = blockers[0]?.title || matchingCheck?.title || (warnings[0]?.title) || workspaceStatusLabel(gateStatus);
  const gateDetail = blockers[0]?.detail || matchingCheck?.detail || warnings[0]?.detail || matchingCheck?.action || "当前节点没有硬阻塞。";
  const evidencePreview = evidenceItems.slice(0, 2).map((item) => `${item.group}:${item.label}`).join(" / ");
  const resourcePrimary = resourceItems[0] || null;
  const backfillPrimary = backfillItems[0] || null;
  const cards = [
    {
      label: "节点门禁",
      status: gateStatus,
      title: gateTitle,
      detail: gateDetail,
    },
    {
      label: "发现证据",
      status: evidenceItems.length ? "ready" : "draft",
      title: evidenceItems.length ? `${evidenceItems.length} 条证据` : "等待发现",
      detail: evidencePreview || "自动发现运行后会把路径、数据、环境、GPU 或产物证据挂到这里。",
    },
    {
      label: "调度项",
      status: resourcePrimary?.status || "draft",
      title: resourcePrimary?.title || resourcePrimary?.value || "等待调度",
      detail: resourcePrimary?.detail || resourcePrimary?.action || "资源矩阵会按节点收口服务器、路径、环境、GPU 或运行入口。",
    },
    {
      label: "回填建议",
      status: backfillPrimary?.status || (backfillItems.length ? "warning" : "draft"),
      title: backfillItems.length ? `${backfillItems.length} 项可回填` : "等待证据",
      detail: backfillPrimary?.action || backfillPrimary?.candidate || "发现证据可用于补齐节点配置字段。",
    },
  ];
  return `
    <div class="workspace-node-scope">
      ${cards.map((item) => `
        <article class="workspace-node-scope-card status-${escapeHtml(item.status || "draft")}">
          <span>${escapeHtml(item.label)}</span>
          <strong title="${escapeHtml(item.title || "")}">${escapeHtml(item.title || "等待")}</strong>
          <em title="${escapeHtml(item.detail || "")}">${escapeHtml(item.detail || "")}</em>
        </article>
      `).join("")}
    </div>
  `;
}

function workspaceNodeNextActionMarkup(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  if (!workspace?.id || !kind) return '<div class="empty">创建实例后会显示当前节点下一步。</div>';
  const automation = workspace.automation && typeof workspace.automation === "object" ? workspace.automation : {};
  const readiness = automation.execution_readiness && typeof automation.execution_readiness === "object" ? automation.execution_readiness : {};
  const runPlan = automation.run_plan && typeof automation.run_plan === "object" ? automation.run_plan : {};
  const backfill = automation.evidence_backfill && typeof automation.evidence_backfill === "object" ? automation.evidence_backfill : {};
  const status = String(node?.status || sourceNode?.status || "").trim();
  const jobId = String(node?.job_id || node?.runtime?.last_job_id || "").trim();
  const activeStatuses = new Set(["queued", "starting", "running"]);
  const failedStatuses = new Set(["failed", "stopped"]);
  const discoveryKinds = new Set(["repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate", "artifact.collect"]);
  const blockers = [
    ...(Array.isArray(readiness.blockers) ? readiness.blockers : []),
    ...(Array.isArray(runPlan.blocking) ? runPlan.blocking : []),
  ].filter((item) => String(item?.node_kind || "").trim() === kind);
  const warnings = [
    ...(Array.isArray(readiness.warnings) ? readiness.warnings : []),
    ...(Array.isArray(runPlan.warnings) ? runPlan.warnings : []),
  ].filter((item) => String(item?.node_kind || "").trim() === kind);
  const backfillItems = (Array.isArray(backfill.items) ? backfill.items : [])
    .filter((item) => String(item?.node_kind || "").trim() === kind && ["ready", "warning", "draft"].includes(String(item?.status || "draft")));
  const baseSecondary = jobId
    ? { label: "打开输出", action: "open-selected-node-log", jobId, title: "打开当前节点最近一次绑定任务的日志输出" }
    : { label: "填入执行面板", action: "fill-job-from-selected-workspace", title: "把当前节点配置带到通用执行面板手动调整" };
  let title = "交给自动推进";
  let detail = "系统会按发现、回填、门禁、完整运行和报告回收顺序决定下一步。";
  let stateName = "ready";
  let primary = { label: "自动推进", action: "advance-workspace-automation", title: "根据当前门禁自动决定下一步" };
  let secondary = baseSecondary;
  if (activeStatuses.has(status)) {
    title = "正在执行，先观察输出";
    detail = jobId ? `当前节点绑定任务 ${jobId}，优先看日志和资源占用。` : "当前节点已进入队列或运行态，等待任务输出。";
    stateName = "running";
    primary = jobId
      ? { label: "打开输出", action: "open-selected-node-log", jobId, title: "打开当前节点输出日志" }
      : { label: "自动推进", action: "advance-workspace-automation", title: "刷新并判断当前运行态" };
    secondary = { label: "自动推进", action: "advance-workspace-automation", title: "已有运行任务时自动推进会进入观察态" };
  } else if (failedStatuses.has(status) || node?.error) {
    title = "先复查失败输出";
    detail = node?.error || "当前节点失败或停止，先看日志、修配置，再继续自动推进。";
    stateName = "failed";
    primary = jobId
      ? { label: "打开输出", action: "open-selected-node-log", jobId, title: "打开失败节点最近输出" }
      : { label: "自动推进", action: "advance-workspace-automation", title: "让系统复查失败态" };
    secondary = { label: "自动推进", action: "advance-workspace-automation", title: "复查失败后继续推进" };
  } else if (blockers.length) {
    title = blockers[0]?.title || "处理节点阻塞";
    detail = blockers[0]?.detail || blockers[0]?.action || "当前节点存在完整运行前必须处理的阻塞项。";
    stateName = "blocked";
    primary = { label: "自动发现", action: "run-workspace-discovery", title: "先补路径、数据、环境、GPU 和产物证据" };
    secondary = { label: "回填证据", action: "apply-workspace-automation", title: "把已有建议和发现证据回填到节点配置" };
  } else if (backfillItems.length) {
    title = "先回填发现证据";
    detail = backfillItems[0]?.action || backfillItems[0]?.candidate || `${backfillItems.length} 项发现证据可用于补齐当前节点配置。`;
    stateName = "warning";
    primary = { label: "回填证据", action: "apply-workspace-automation", title: "把发现证据回填到节点配置" };
    secondary = { label: "自动推进", action: "advance-workspace-automation", title: "回填后继续自动推进" };
  } else if (discoveryKinds.has(kind) && !jobId && !["done", "ready"].includes(status)) {
    title = "先跑安全发现";
    detail = "当前节点属于安全发现链，适合先收集源码、路径、数据、环境、GPU 或产物证据。";
    stateName = "ready";
    primary = { label: "自动发现", action: "run-workspace-discovery", title: "提交安全发现链" };
    secondary = { label: "运行当前节点", action: "run-selected-node", nodeId: node?.id || sourceNode?.id || "", title: "只运行当前节点做单点调试" };
  } else if (kind === "run.command") {
    title = warnings.length ? "确认提示后运行" : "可以单点运行";
    detail = warnings[0]?.detail || warnings[0]?.action || "当前运行节点可单独提交；完整工作流仍会受门禁保护。";
    stateName = warnings.length ? "warning" : "ready";
    primary = { label: "运行当前节点", action: "run-selected-node", nodeId: node?.id || sourceNode?.id || "", title: "只提交当前运行节点" };
    secondary = { label: "运行工作流", action: "run-selected-workspace", title: "门禁通过后提交完整工作流" };
  }
  const buttonMarkup = (button, tone = "secondary") => {
    if (!button?.action) return "";
    const nodeAttr = button.nodeId ? ` data-node-id="${escapeHtml(button.nodeId)}"` : "";
    const jobAttr = button.jobId ? ` data-job-id="${escapeHtml(button.jobId)}"` : "";
    return `<button class="${tone} mini" type="button" data-action="${escapeHtml(button.action)}"${nodeAttr}${jobAttr} title="${escapeHtml(button.title || button.label || "执行操作")}">${escapeHtml(button.label || "操作")}</button>`;
  };
  return `
    <div class="workspace-node-next-action status-${escapeHtml(stateName)}">
      <div>
        <span>节点下一步</span>
        <strong>${escapeHtml(title)}</strong>
        <em>${escapeHtml(detail)}</em>
      </div>
      <div class="workspace-node-next-actions">
        ${buttonMarkup(primary, "primary")}
        ${buttonMarkup(secondary)}
      </div>
    </div>
  `;
}

function workspaceNodeExecutionPlanItems(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  if (!workspace?.id || !kind) return [];
  const nodeId = String(node?.id || sourceNode?.id || "").trim();
  const io = workspaceNodeIoContractState(node, sourceNode, { workspace });
  const automation = workspace.automation && typeof workspace.automation === "object" ? workspace.automation : {};
  const runPlan = automation.run_plan && typeof automation.run_plan === "object" ? automation.run_plan : {};
  const runNodes = Array.isArray(runPlan.nodes) ? runPlan.nodes : [];
  const planNode = runNodes.find((item) => String(item?.id || item?.node_id || "").trim() === nodeId)
    || runNodes.find((item) => String(item?.kind || item?.node_kind || "").trim() === kind)
    || {};
  const manifest = automation.reproduction_manifest && typeof automation.reproduction_manifest === "object" ? automation.reproduction_manifest : {};
  const manifestItems = Array.isArray(manifest.items) ? manifest.items : [];
  const manifestItem = manifestItems.find((item) => String(item?.node_id || "").trim() === nodeId)
    || manifestItems.find((item) => String(item?.node_kind || "").trim() === kind)
    || {};
  const resource = automation.resource_orchestration && typeof automation.resource_orchestration === "object" ? automation.resource_orchestration : {};
  const resourceItems = Array.isArray(resource.items) ? resource.items : [];
  const resourceItem = resourceItems.find((item) => String(item?.node_kind || "").trim() === kind) || {};
  const evidenceItems = [];
  (Array.isArray(automation.evidence) ? automation.evidence : []).forEach((group) => {
    (Array.isArray(group?.items) ? group.items : []).forEach((item) => {
      if (String(item?.node_kind || "").trim() !== kind) return;
      evidenceItems.push({
        label: String(item.label || item.source || group.label || "证据"),
        value: String(item.value || ""),
      });
    });
  });
  const inputMapping = io.inputMapping && typeof io.inputMapping === "object" ? io.inputMapping : {};
  const inputLabels = Object.entries(inputMapping)
    .slice(0, 4)
    .map(([name, source]) => `${name} ← ${source}`);
  const outputKey = String(io.outputKey || io.output || planNode.output_key || "").trim();
  const handoff = String(io.handoff || planNode.handoff || sourceNode?.handler?.handoff || manifestItem.action || "").trim();
  const agentName = String(io.agent?.name || planNode.agent_name || node?.agent_name || "未指派 Agent").trim();
  const toolNames = Array.isArray(io.tools) ? io.tools.map((tool) => tool.label || tool.id || tool).filter(Boolean) : [];
  const modelText = String(io.model?.effective_profile_id || io.model?.workspace_profile_id || io.model?.agent_profile_id || "").trim();
  return [
    {
      id: "inputs",
      label: "输入来源",
      status: inputLabels.length ? "ready" : "draft",
      title: inputLabels.length ? `${inputLabels.length} 个 input_mapping` : "等待输入映射",
      detail: inputLabels.join(" / ") || "会从任务 input、上一节点输出或 context.outputs 读取。",
    },
    {
      id: "action",
      label: "执行动作",
      status: planNode.status || node?.status || sourceNode?.status || "draft",
      title: planNode.title || sourceNode?.title || node?.title || workspaceNodeLabel(kind),
      detail: [
        planNode.phase_label || workspaceStarterNodePhase(kind),
        agentName,
        toolNames.length ? toolNames.slice(0, 3).join(" / ") : "",
        modelText,
      ].filter(Boolean).join(" · ") || "等待 Agent、Tool 和模型路由。",
    },
    {
      id: "outputs",
      label: "输出交接",
      status: outputKey ? "ready" : "draft",
      title: outputKey || "等待 output_key",
      detail: handoff || `输出会写入 ${io.context?.outputs_key || "$context.outputs"}，供下游节点读取。`,
    },
    {
      id: "evidence",
      label: "验收证据",
      status: manifestItem.status || resourceItem.status || (evidenceItems.length ? "ready" : "draft"),
      title: manifestItem.title || resourceItem.title || (evidenceItems.length ? `${evidenceItems.length} 条证据` : "等待证据"),
      detail: manifestItem.detail || resourceItem.detail || evidenceItems.slice(0, 3).map((item) => `${item.label}:${item.value}`).join(" / ") || "运行或发现完成后会回收证据、产物或指标。",
    },
  ];
}

function workspaceNodeExecutionPlanActions(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  const nodeId = String(node?.id || sourceNode?.id || "").trim();
  const discoveryKinds = new Set(["repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate", "artifact.collect"]);
  const actions = [];
  if (discoveryKinds.has(kind)) {
    actions.push({ label: "自动发现", action: "run-workspace-discovery", title: "提交安全发现链，补齐路径、数据、环境、GPU 和产物证据" });
  }
  if (nodeId && kind !== "source.repo" && kind !== "source.paper" && kind !== "source.idea") {
    actions.push({ label: "运行节点", action: "run-selected-node", nodeId, title: "只运行当前节点，用于单点调试或补证据" });
  }
  actions.push({ label: "回填证据", action: "apply-workspace-automation", title: "把发现证据回填到节点配置" });
  actions.push({ label: "自动推进", action: "advance-workspace-automation", title: "根据当前门禁自动决定下一步" });
  if (kind === "run.command") {
    actions.unshift({ label: "运行工作流", action: "run-selected-workspace", title: "门禁通过后提交完整工作流" });
  }
  return actions.slice(0, 4);
}

function workspaceNodeExecutionPlanButton(action = {}, tone = "secondary") {
  if (!action?.action) return "";
  const nodeAttr = action.nodeId ? ` data-node-id="${escapeHtml(action.nodeId)}"` : "";
  const help = workspaceAutomationActionHelp(action.action, action.title || action.label || "执行节点计划动作");
  return `<button class="${tone} mini" type="button" data-action="${escapeHtml(action.action)}"${nodeAttr} title="${escapeHtml(help)}">${escapeHtml(action.label || "操作")}</button>`;
}

function workspaceNodeExecutionPlanMarkup(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const items = workspaceNodeExecutionPlanItems(workspace, node, sourceNode);
  if (!items.length) return '<div class="empty">创建实例后会显示当前节点执行计划。</div>';
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  const actions = workspaceNodeExecutionPlanActions(workspace, node, sourceNode);
  const ready = items.filter((item) => ["ready", "done"].includes(String(item.status || ""))).length;
  const blocked = items.filter((item) => ["blocked", "failed"].includes(String(item.status || ""))).length;
  return `
    <div class="workspace-node-execution-plan status-${escapeHtml(blocked ? "blocked" : ready === items.length ? "ready" : "warning")}">
      <div class="workspace-node-execution-plan-head">
        <div>
          <span>当前节点执行计划</span>
          <strong>${escapeHtml(`${ready}/${items.length} 项就绪 · ${workspaceCockpitStageLabel(kind)}`)}</strong>
        </div>
        <small>${escapeHtml(kind || "未选择节点")}</small>
      </div>
      <div class="workspace-node-execution-plan-grid">
        ${items.map((item, index) => `
          <article class="workspace-node-execution-plan-item status-${escapeHtml(item.status || "draft")}">
            <span>${escapeHtml(`${index + 1}. ${item.label}`)}</span>
            <strong title="${escapeHtml(item.title || "")}">${escapeHtml(item.title || "等待")}</strong>
            <em title="${escapeHtml(item.detail || "")}">${escapeHtml(item.detail || "")}</em>
          </article>
        `).join("")}
      </div>
      <div class="workspace-node-execution-plan-actions">
        ${actions.map((action, index) => workspaceNodeExecutionPlanButton(action, index === 0 ? "primary" : "secondary")).join("")}
      </div>
    </div>
  `;
}

function workspaceExecutionCardMarkup(node, index, options = {}) {
  const active = node.id === state.selectedWorkspaceExecutionNodeId ? " active" : "";
  const status = String(node.status || (options.preview ? "preview" : "pending"));
  const handlerName = node.agent_name || globalAgentById(node.agent_id)?.name || "未指派";
  const note = options.note || "";
  const artifacts = options.preview ? [] : workspaceRuntimeArtifacts(node);
  const resources = options.preview ? {} : workspaceRuntimeResources(node);
  const resourceSummary = options.preview
    ? ""
    : `${resources.execution_mode || "cpu"} · ${resources.server_id || "auto"} · GPU ${resources.gpu_index || resources.gpu_policy || "auto"}`;
  return `
    <button class="workspace-execution-card${active} status-${escapeHtml(status)}" type="button" data-action="select-execution-node" data-node-id="${escapeHtml(node.id)}" title="${escapeHtml(options.preview ? "选择这个模板预览节点，查看实例创建后的计划位置" : "选择这个执行节点，查看门禁、资源、任务和产物详情")}">
      <div class="workspace-execution-card-head">
        <span class="workspace-execution-order">${index + 1}</span>
        <strong>${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</strong>
        <span class="state ${escapeHtml(status)}">${escapeHtml(workspaceStatusLabel(status))}</span>
      </div>
      <div class="workspace-execution-card-meta">${escapeHtml(workspaceNodeLabel(node.kind))} · ${escapeHtml(handlerName)}</div>
      ${options.preview
        ? `<div class="workspace-execution-card-meta">${escapeHtml(note)}</div>`
        : `
          <div class="workspace-execution-card-meta">${escapeHtml(resourceSummary)} · ${artifacts.length} 个路径快照</div>
          <div class="workspace-execution-card-meta">${node.job_id ? `最近任务 ${escapeHtml(node.job_id)}` : "还没有任务记录"}</div>
        `}
      ${node.error ? `<div class="workspace-execution-card-error">${escapeHtml(node.error)}</div>` : ""}
    </button>
  `;
}

function workspaceExecutionPhaseStatus(group = {}) {
  const statuses = (group.nodes || []).map(({ node }) => String(node?.status || "pending"));
  if (statuses.some((status) => ["failed", "stopped"].includes(status))) return "failed";
  if (statuses.some((status) => ["running", "starting", "queued"].includes(status))) return "running";
  if (statuses.some((status) => ["blocked"].includes(status))) return "blocked";
  if (statuses.length && statuses.every((status) => ["done"].includes(status))) return "done";
  if (statuses.some((status) => ["preview"].includes(status))) return "preview";
  return "pending";
}

function workspaceExecutionPhaseProgressMarkup(groups = []) {
  if (!groups.length) return "";
  return `
    <div class="workspace-execution-phase-progress">
      ${groups.map((group) => {
        const status = workspaceExecutionPhaseStatus(group);
        const doneCount = group.nodes.filter(({ node }) => String(node?.status || "") === "done").length;
        const runningCount = group.nodes.filter(({ node }) => ["running", "starting", "queued"].includes(String(node?.status || ""))).length;
        const blockedCount = group.nodes.filter(({ node }) => ["blocked", "failed", "stopped"].includes(String(node?.status || ""))).length;
        const detail = status === "preview"
          ? "模板预览"
          : `${doneCount} 完成 · ${runningCount} 活跃 · ${blockedCount} 阻塞`;
        return `
          <article class="workspace-execution-phase-chip status-${escapeHtml(status)}">
            <span>${escapeHtml(group.phase)}</span>
            <strong>${escapeHtml(String(group.nodes.length))}</strong>
            <em>${escapeHtml(detail)}</em>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function workspaceExecutionChainMarkup(nodes = [], options = {}) {
  const groups = workspaceExecutionPhaseGroups(nodes);
  if (!groups.length) return '<div class="empty">还没有可展示的执行节点。</div>';
  return `
    ${workspaceExecutionPhaseProgressMarkup(groups)}
    ${groups.map((group) => `
      <section class="workspace-execution-phase">
        <div class="workspace-execution-phase-head">
          <strong>${escapeHtml(group.phase)}</strong>
          <span>${escapeHtml(String(group.nodes.length))} 节点</span>
        </div>
        <div class="workspace-execution-phase-nodes">
          ${group.nodes.map(({ node, index }) => {
            const note = options.preview
              ? index === 0
                ? "创建实例后会从这里开始生成真实运行状态"
                : "等待上游节点交接后进入真实执行"
              : "";
            return workspaceExecutionCardMarkup(node, index, { ...options, note });
          }).join("")}
        </div>
      </section>
    `).join("")}
  `;
}

function workspaceUseInputsPayload() {
  return {
    goal_text: String($("workspaceTaskGoalInput")?.value || "").trim(),
    repo_urls: parseLineList($("workspaceTaskRepoInput")?.value || ""),
    paper_urls: parseLineList($("workspaceTaskPaperInput")?.value || ""),
    references: parseLineList($("workspaceTaskReferenceInput")?.value || ""),
    context_blocks: parseLineList($("workspaceTaskContextInput")?.value || ""),
  };
}

function setWorkspaceLauncherInputs(inputs = {}) {
  if ($("workspaceTaskGoalInput")) $("workspaceTaskGoalInput").value = String(inputs.goal_text || "");
  if ($("workspaceTaskRepoInput")) $("workspaceTaskRepoInput").value = Array.isArray(inputs.repo_urls) ? inputs.repo_urls.join("\n") : "";
  if ($("workspaceTaskPaperInput")) $("workspaceTaskPaperInput").value = Array.isArray(inputs.paper_urls) ? inputs.paper_urls.join("\n") : "";
  if ($("workspaceTaskReferenceInput")) $("workspaceTaskReferenceInput").value = Array.isArray(inputs.references) ? inputs.references.join("\n") : "";
  if ($("workspaceTaskContextInput")) $("workspaceTaskContextInput").value = Array.isArray(inputs.context_blocks) ? inputs.context_blocks.join("\n") : "";
}

function saveWorkspaceLauncherDraft() {
  saveStoredJson(STORAGE_KEYS.workspaceLauncherDraft, workspaceUseInputsPayload());
}

function restoreWorkspaceLauncherDraft() {
  if (state.selectedWorkspaceId) return;
  const draft = loadStoredJson(STORAGE_KEYS.workspaceLauncherDraft, {});
  if (!draft || typeof draft !== "object") return;
  setWorkspaceLauncherInputs(draft);
}

function workspaceUseSourceMode(inputs = workspaceUseInputsPayload()) {
  const hasRepo = Array.isArray(inputs.repo_urls) && inputs.repo_urls.length > 0;
  const hasPaper = Array.isArray(inputs.paper_urls) && inputs.paper_urls.length > 0;
  const hasGoal = Boolean(String(inputs.goal_text || "").trim());
  if ((hasRepo && hasPaper) || (hasRepo && hasGoal) || (hasPaper && hasGoal)) return "mixed";
  if (hasRepo) return "repo";
  if (hasPaper) return "paper";
  return "idea";
}

function workspaceUseInputSummary(inputs = workspaceUseInputsPayload()) {
  const parts = [];
  const goal = String(inputs.goal_text || "").trim();
  if (goal) parts.push(goal.split(/\r?\n/)[0].slice(0, 90));
  if (inputs.repo_urls?.length) parts.push(`${inputs.repo_urls.length} repo`);
  if (inputs.paper_urls?.length) parts.push(`${inputs.paper_urls.length} paper`);
  if (inputs.references?.length) parts.push(`${inputs.references.length} path/ref`);
  if (inputs.context_blocks?.length) parts.push(`${inputs.context_blocks.length} constraints`);
  return parts.join(" · ") || "先写目标、repo、论文或数据路径线索";
}

function workspaceUseNextAction(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), workspace = selectedWorkspace()) {
  const hasInput = Boolean(
    inputs.goal_text
    || inputs.repo_urls?.length
    || inputs.paper_urls?.length
    || inputs.references?.length
    || inputs.context_blocks?.length
  );
  if (!hasInput) {
    return {
      title: "补齐复现目标",
      detail: "先写目标或贴 repo / 论文 / 数据集路径，系统才能生成实例快照。",
      state: "draft",
    };
  }
  if (!template) {
    return {
      title: "选择 Starter Chain",
      detail: "需要先选一条 repo / paper / idea 初始链路。",
      state: "blocked",
    };
  }
  if (!workspace) {
    return {
      title: "创建并自动发现",
      detail: "输入已经准备好，下一步复制模板并先探测路径、数据、环境和 GPU。",
      state: "ready",
    };
  }
  const jobs = workspaceJobs();
  const activeJobs = jobs.filter((job) => isJobActive(job)).length;
  const failedJobs = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  if (failedJobs) {
    return {
      title: "先处理失败节点",
      detail: `${failedJobs} 个任务失败或停止，先看日志和节点配置。`,
      state: "failed",
    };
  }
  if (activeJobs) {
    return {
      title: "跟踪运行输出",
      detail: `${activeJobs} 个节点正在排队或运行，优先看日志和资源占用。`,
      state: "running",
    };
  }
  if (!jobs.length) {
    return {
      title: "运行 starter chain",
      detail: "实例已经创建，可以先跑确定性节点把日志接回来。",
      state: "ready",
    };
  }
  return {
    title: "整理产物报告",
    detail: "已有运行记录，下一步汇总指标、路径、错误和复跑命令。",
    state: "done",
  };
}

function workspaceUseResourceSummary() {
  const connected = connectedServers().length;
  const online = onlineServers().length;
  const total = state.servers.length;
  const idle = idleGpuCount();
  const gpus = allGpus();
  const idleGpus = gpus.filter((item) => item.gpu?.state === "idle");
  const bestGpu = (idleGpus.length ? idleGpus : gpus)
    .slice()
    .sort((left, right) => Number(right.gpu?.memory_free_mib || 0) - Number(left.gpu?.memory_free_mib || 0))[0];
  const bestText = bestGpu
    ? `${bestGpu.server.name || bestGpu.server.id} / GPU ${bestGpu.gpu.index} / ${fmtMiB(bestGpu.gpu.memory_free_mib)} free`
    : "没有可用 GPU 快照";
  return {
    title: `${connected}/${total} 已连接`,
    detail: `${online} 监控正常 · ${idle} 张空闲 GPU · ${bestText}`,
    state: connected ? (online < connected ? "blocked" : "ready") : "failed",
  };
}

function workspaceAutomationSummary(workspace = selectedWorkspace()) {
  const automation = workspace?.automation && typeof workspace.automation === "object" ? workspace.automation : null;
  if (!automation) return null;
  const checks = Array.isArray(automation.checks) ? automation.checks : [];
  const missing = Array.isArray(automation.missing) ? automation.missing : checks.filter((item) => ["blocked", "warning", "draft"].includes(String(item.status || "")));
  const next = automation.next_action && typeof automation.next_action === "object"
    ? automation.next_action
    : missing[0] || checks[0] || null;
  const advance = automation.advance && typeof automation.advance === "object" ? automation.advance : null;
  const agentTopology = automation.agent_topology && typeof automation.agent_topology === "object" ? automation.agent_topology : null;
  const resourcePlan = automation.resource_orchestration && typeof automation.resource_orchestration === "object" ? automation.resource_orchestration : null;
  const executionReadiness = automation.execution_readiness && typeof automation.execution_readiness === "object" ? automation.execution_readiness : null;
  return {
    status: automation.status || "warning",
    score: Number(automation.score || 0),
    checks,
    missing,
    next,
    advance,
    agentTopology,
    resourcePlan,
    executionReadiness,
    summary: automation.summary || `${checks.length - missing.length} 项就绪 · ${missing.length} 项待处理`,
  };
}

function workspaceAutomationCheckMarkup(workspace = selectedWorkspace(), { limit = 8 } = {}) {
  const automation = workspaceAutomationSummary(workspace);
  if (!automation || !automation.checks.length) return '<div class="empty">还没有自动化体检结果。</div>';
  const checks = automation.checks.slice(0, limit);
  return `
    <div class="workspace-automation-check-list">
      ${checks.map((check) => {
        const status = String(check.status || "warning");
        return `
          <article class="workspace-automation-check status-${escapeHtml(status)}">
            <div>
              <span>${escapeHtml(check.label || check.id || "检查项")}</span>
              <strong>${escapeHtml(check.title || workspaceStatusLabel(status))}</strong>
              <em>${escapeHtml(check.detail || "")}</em>
            </div>
            <small>${escapeHtml(check.action || workspaceStatusLabel(status))}</small>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function workspaceAutomationAdvanceMarkup(workspace = selectedWorkspace()) {
  const advance = workspaceAutomationSummary(workspace)?.advance;
  if (!advance) return '<div class="empty">还没有自动推进建议。</div>';
  return `
    <div class="workspace-advance-card status-${escapeHtml(advance.status || "ready")}">
      <div>
        <strong>${escapeHtml(advance.title || "自动推进")}</strong>
        <p>${escapeHtml(advance.reason || "系统已判断下一步。")}</p>
      </div>
      <small>${escapeHtml(advance.next_action || "点击自动推进继续。")}</small>
    </div>
  `;
}

function workspaceAutomationExecutionReadinessMarkup(workspace = selectedWorkspace(), { limit = 6 } = {}) {
  const readiness = workspaceAutomationSummary(workspace)?.executionReadiness;
  if (!readiness) return '<div class="empty">还没有执行准备清单。</div>';
  const steps = Array.isArray(readiness.steps) ? readiness.steps.slice(0, limit) : [];
  const gate = readiness.gate && typeof readiness.gate === "object" ? readiness.gate : {};
  const jobState = readiness.job_state && typeof readiness.job_state === "object" ? readiness.job_state : {};
  const forceRun = readiness.force_run && typeof readiness.force_run === "object" ? readiness.force_run : {};
  const next = readiness.next_action && typeof readiness.next_action === "object" ? readiness.next_action : {};
  return `
    <div class="workspace-readiness status-${escapeHtml(readiness.status || "draft")}">
      <div class="workspace-readiness-head">
        <div>
          <span>执行准备</span>
          <strong>${escapeHtml(readiness.summary || "等待准备清单")}</strong>
        </div>
        <small>${escapeHtml(next.title || gate.title || "等待自动推进判断")}</small>
      </div>
      <div class="workspace-readiness-metrics">
        <article>
          <span>发现记录</span>
          <strong>${escapeHtml(String(jobState.discovery_run_count || 0))}</strong>
        </article>
        <article>
          <span>完整节点</span>
          <strong>${escapeHtml(String(jobState.full_run_node_count || 0))}</strong>
        </article>
        <article>
          <span>活跃任务</span>
          <strong>${escapeHtml(String(jobState.active_count || 0))}</strong>
        </article>
        <article>
          <span>失败任务</span>
          <strong>${escapeHtml(String(jobState.failed_count || 0))}</strong>
        </article>
      </div>
      ${workspaceAutomationStateMachineMarkup(workspace)}
      <div class="workspace-readiness-gate status-${escapeHtml(gate.status || "draft")}">
        <div>
          <span>运行门禁</span>
          <strong>${escapeHtml(gate.title || workspaceStatusLabel(gate.status || "draft"))}</strong>
          <em>${escapeHtml(gate.detail || "")}</em>
        </div>
        <small>${escapeHtml(gate.action || "")}</small>
      </div>
      <div class="workspace-readiness-steps">
        ${steps.map((step, index) => `
          <article class="workspace-readiness-step status-${escapeHtml(step.status || "draft")}">
            <span>${escapeHtml(String(index + 1))}</span>
            <div>
              <strong>${escapeHtml(step.label || step.id || "准备项")}</strong>
              <em>${escapeHtml(step.title || workspaceStatusLabel(step.status || "draft"))}</em>
              <small>${escapeHtml(step.detail || step.action || "")}</small>
            </div>
          </article>
        `).join("") || '<div class="empty">还没有准备步骤。</div>'}
      </div>
      <div class="workspace-readiness-force status-${escapeHtml(forceRun.status || "draft")}">
        <strong>${escapeHtml(forceRun.title || "强制运行风险")}</strong>
        <span>${escapeHtml(forceRun.detail || "等待节点校验结果")}</span>
        <em>${escapeHtml(forceRun.action || "")}</em>
      </div>
    </div>
  `;
}

function workspaceStateMachineCurrentStepId(readiness = {}) {
  const steps = Array.isArray(readiness.steps) ? readiness.steps : [];
  const next = readiness.next_action && typeof readiness.next_action === "object" ? readiness.next_action : {};
  const action = String(next.action || "").trim();
  if (action === "discover") return "safe_discovery";
  if (action === "run") return "full_run";
  if (action === "watch") {
    return steps.find((step) => ["running", "queued"].includes(String(step.status || "")))?.id || "full_run";
  }
  if (action === "review_failed") return "full_run";
  if (action === "blocked") {
    return steps.find((step) => ["blocked", "failed"].includes(String(step.status || "")))?.id || "hard_gate";
  }
  return steps.find((step) => !["done"].includes(String(step.status || "")))?.id || steps[steps.length - 1]?.id || "";
}

function workspaceStateMachineActionForStep(step = {}, readiness = {}) {
  const id = String(step.id || "").trim();
  const status = String(step.status || "draft");
  const jobState = readiness.job_state && typeof readiness.job_state === "object" ? readiness.job_state : {};
  const hasLastJob = Boolean(String(jobState.last_job_id || "").trim());
  if (["running", "queued"].includes(status) && hasLastJob) {
    return { label: "打开输出", action: "open-last-workspace-log", title: "打开当前实例最近绑定任务的日志输出" };
  }
  if (["failed", "stopped"].includes(status) && hasLastJob) {
    return { label: "看日志", action: "open-last-workspace-log", title: "先打开失败任务日志，再修正配置继续推进" };
  }
  if (id === "safe_discovery") {
    return status === "done"
      ? { label: "继续推进", action: "advance-workspace-automation", title: "发现链已有记录，继续判断是否回填证据或完整运行" }
      : { label: "自动发现", action: "run-workspace-discovery", title: "只运行安全发现链，收集源码、路径、数据、环境、GPU 和产物证据" };
  }
  if (id === "defaults_evidence") {
    return ["ready", "warning"].includes(status)
      ? { label: "回填证据", action: "apply-workspace-automation", title: "把发现证据写入路径、数据、环境、GPU、产物等节点配置" }
      : { label: "自动发现", action: "run-workspace-discovery", title: "先提交安全发现，再回填证据" };
  }
  if (id === "resource_binding") {
    return ["blocked", "warning", "draft"].includes(status)
      ? { label: "刷新资源", action: "refresh-workspace-resources", title: "刷新全部服务器、GPU、任务和资源快照；不会重置工作台" }
      : { label: "继续推进", action: "advance-workspace-automation", title: "资源调度已具备，继续判断门禁和完整运行" };
  }
  if (id === "hard_gate") {
    return ["blocked", "failed"].includes(status)
      ? { label: "配置中心", action: "switch-workspace-manage", title: "去配置中心补齐 Starter Chain、Agent、工具或运行命令" }
      : { label: "自动推进", action: "advance-workspace-automation", title: "门禁通过后继续发现、回填或完整运行" };
  }
  if (id === "full_run") {
    return status === "ready"
      ? { label: "运行工作流", action: "run-selected-workspace", title: "提交完整执行链；门禁失败时不会创建半截队列" }
      : { label: "自动推进", action: "advance-workspace-automation", title: "让系统按当前状态决定是否发现、回填、观察或运行" };
  }
  if (id === "collect_report") {
    return ["ready", "done", "warning"].includes(status)
      ? { label: "继续推进", action: "advance-workspace-automation", title: "继续收集产物、指标并整理复现/部署报告" }
      : { label: "运行工作流", action: "run-selected-workspace", title: "完整运行完成后再收集产物和指标" };
  }
  return { label: "自动推进", action: "advance-workspace-automation", title: "根据当前门禁自动决定下一步" };
}

function workspaceStateMachineActionButton(action = {}, current = false) {
  if (!action?.action) return "";
  const busy = Boolean(state.ui.workspaceAutomationBusyAction) && !WORKSPACE_NON_BLOCKING_ACTIONS.has(action.action);
  const label = busy && state.ui.workspaceAutomationBusyAction === action.action ? "处理中..." : action.label || "操作";
  const help = workspaceAutomationActionHelp(action.action, action.title || label);
  return `
    <button class="${current ? "primary" : "secondary"} mini" type="button" data-action="${escapeHtml(action.action)}" title="${escapeHtml(help)}" ${busy ? "disabled" : ""}>
      ${escapeHtml(label)}
    </button>
  `;
}

function workspaceAutomationStateMachineMarkup(workspace = selectedWorkspace()) {
  const readiness = workspaceAutomationSummary(workspace)?.executionReadiness;
  if (!workspace?.id || !readiness) return "";
  const steps = Array.isArray(readiness.steps) ? readiness.steps : [];
  if (!steps.length) return "";
  const next = readiness.next_action && typeof readiness.next_action === "object" ? readiness.next_action : {};
  const gate = readiness.gate && typeof readiness.gate === "object" ? readiness.gate : {};
  const jobState = readiness.job_state && typeof readiness.job_state === "object" ? readiness.job_state : {};
  const currentStepId = workspaceStateMachineCurrentStepId(readiness);
  const activeCount = Number(jobState.active_count || 0);
  const failedCount = Number(jobState.failed_count || 0);
  const doneCount = steps.filter((step) => String(step.status || "") === "done").length;
  return `
    <div class="workspace-state-machine status-${escapeHtml(readiness.status || "draft")}">
      <div class="workspace-state-machine-head">
        <div>
          <span>自动化状态机</span>
          <strong>${escapeHtml(next.title || gate.title || "等待下一步判断")}</strong>
          <em>${escapeHtml(next.reason || next.next_action || gate.detail || "按发现、回填、调度、门禁、完整运行、产物回收推进。")}</em>
        </div>
        <small>${escapeHtml(`${doneCount}/${steps.length} 完成 · ${activeCount} 活跃 · ${failedCount} 失败`)}</small>
      </div>
      <div class="workspace-state-machine-rail">
        ${steps.map((step, index) => {
          const id = String(step.id || `step-${index}`);
          const current = id === currentStepId;
          const action = workspaceStateMachineActionForStep(step, readiness);
          return `
            <article class="workspace-state-step status-${escapeHtml(step.status || "draft")}${current ? " current" : ""}">
              <div class="workspace-state-step-index">
                <span>${escapeHtml(String(index + 1))}</span>
                ${index < steps.length - 1 ? "<i></i>" : ""}
              </div>
              <div class="workspace-state-step-body">
                <span>${escapeHtml(step.label || id)}</span>
                <strong title="${escapeHtml(step.title || "")}">${escapeHtml(step.title || workspaceStatusLabel(step.status || "draft"))}</strong>
                <em title="${escapeHtml(step.detail || step.action || "")}">${escapeHtml(step.detail || step.action || "")}</em>
                <div class="workspace-state-step-actions">
                  ${workspaceStateMachineActionButton(action, current)}
                </div>
              </div>
            </article>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function workspaceIssueTitle(item = {}) {
  return String(item.label || item.title || item.node_kind || item.id || item.type || "检查项").trim();
}

function workspaceIssueDetail(item = {}) {
  return String(item.detail || item.action || item.summary || item.value || "").trim();
}

function workspaceIssueMeta(item = {}) {
  const parts = [
    String(item.node_title || item.node_kind || "").trim(),
    String(item.field || "").trim(),
  ].filter(Boolean);
  return parts.join(" · ");
}

function workspaceIssueFixAction(item = {}) {
  return String(item.fix_action || item.action || "定位节点后补齐配置。").trim();
}

function workspaceCockpitIssueMarkup(item = {}, fallbackStatus = "warning") {
  const status = String(item.status || fallbackStatus || "warning");
  const nodeId = String(item.node_id || "").trim();
  const title = workspaceIssueTitle(item);
  const detail = workspaceIssueDetail(item) || "等待处理";
  const meta = workspaceIssueMeta(item);
  const fixAction = workspaceIssueFixAction(item);
  const tag = nodeId ? "button" : "article";
  const attrs = nodeId
    ? `type="button" data-action="select-execution-node" data-node-id="${escapeHtml(nodeId)}" title="${escapeHtml(`定位到节点：${meta || title}`)}"`
    : "";
  return `
    <${tag} class="workspace-cockpit-issue status-${escapeHtml(status)}" ${attrs}>
      <strong>${escapeHtml(title)}</strong>
      ${meta ? `<small>${escapeHtml(meta)}</small>` : ""}
      <span>${escapeHtml(detail)}</span>
      <em>${escapeHtml(fixAction)}</em>
    </${tag}>
  `;
}

function workspaceEvidenceSummaryItems(workspace = selectedWorkspace()) {
  const evidence = Array.isArray(workspace?.automation?.evidence) ? workspace.automation.evidence : [];
  return evidence.map((group) => ({
    id: String(group.id || group.label || "evidence"),
    label: String(group.label || group.id || "证据"),
    count: Number(group.count || 0),
    detail: String(group.detail || "等待自动发现"),
    status: String(group.status || (Number(group.count || 0) ? "ready" : "draft")),
  }));
}

function workspaceEvidenceGroupsByKind(workspace = selectedWorkspace()) {
  const evidence = Array.isArray(workspace?.automation?.evidence) ? workspace.automation.evidence : [];
  const index = {};
  evidence.forEach((group) => {
    const items = Array.isArray(group.items) ? group.items : [];
    items.forEach((item) => {
      const kind = String(item?.node_kind || "").trim();
      if (!kind) return;
      if (!index[kind]) index[kind] = [];
      index[kind].push({
        group: String(group.label || group.id || "证据"),
        label: String(item.label || item.source || "发现"),
        value: String(item.value || ""),
        status: String(item.status || "found"),
      });
    });
  });
  return index;
}

function workspaceCockpitStageLabel(kind = "") {
  const normalized = String(kind || "").trim();
  const labels = {
    "repo.clone": "拉取",
    "path.resolve": "路径",
    "repo.inspect": "仓库",
    "dataset.find": "数据",
    "env.infer": "环境",
    "env.prepare": "安装",
    "gpu.allocate": "GPU",
    "run.command": "运行",
    "artifact.collect": "产物",
    "eval.report": "报告",
  };
  return labels[normalized] || workspaceNodeLabel(normalized);
}

function workspaceLaunchIntentItems(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), resources = null) {
  const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
  const hasKind = (kinds = []) => nodes.some((node) => kinds.includes(String(node?.kind || "")));
  const sourceMode = workspaceUseSourceMode(inputs);
  const hasGoal = Boolean(String(inputs.goal_text || "").trim());
  const hasRepo = Array.isArray(inputs.repo_urls) && inputs.repo_urls.length > 0;
  const hasPaper = Array.isArray(inputs.paper_urls) && inputs.paper_urls.length > 0;
  const hasReference = Array.isArray(inputs.references) && inputs.references.length > 0;
  const hasContext = Array.isArray(inputs.context_blocks) && inputs.context_blocks.length > 0;
  const hasInput = hasGoal || hasRepo || hasPaper || hasReference || hasContext;
  const resourceState = resources?.state || "draft";
  return [
    {
      label: "来源",
      value: hasInput ? workspaceSourceTypeLabel(sourceMode) : "等待输入",
      detail: hasRepo ? `${inputs.repo_urls.length} 个候选仓库` : hasPaper ? `${inputs.paper_urls.length} 条论文/资料` : hasGoal ? "从目标描述启动" : "目标、repo 或论文至少填一项",
      status: hasInput ? "ready" : "draft",
    },
    {
      label: "数据",
      value: hasReference ? `${inputs.references.length} 条线索` : hasKind(["dataset.find"]) ? "自动发现" : "未编排",
      detail: hasReference ? "会作为数据集、路径或参考线索进入发现链" : "dataset.find 节点会尝试从 README、论文和本地路径补证据",
      status: hasReference || hasKind(["dataset.find"]) ? "ready" : "warning",
    },
    {
      label: "环境",
      value: hasKind(["env.infer", "env.prepare"]) ? "推断/准备" : "未编排",
      detail: hasKind(["env.infer"]) ? "会从依赖文件、README 和脚本推断 Python/CUDA/安装命令" : "需要 env.infer 或 env.prepare 节点承接环境准备",
      status: hasKind(["env.infer", "env.prepare"]) ? "ready" : "warning",
    },
    {
      label: "GPU",
      value: resources?.title || "等待快照",
      detail: resources?.detail || "刷新服务器后生成候选服务器和空闲 GPU",
      status: resourceState,
    },
    {
      label: "运行",
      value: hasKind(["run.command"]) ? "门禁后执行" : "未编排",
      detail: hasKind(["run.command"]) ? "完整运行会在路径、数据、环境和 GPU 门禁通过后提交" : "需要 run.command 节点承接真实运行",
      status: hasKind(["run.command"]) ? "ready" : "blocked",
    },
    {
      label: "产物",
      value: hasKind(["artifact.collect", "eval.report"]) ? "收集/报告" : "未编排",
      detail: hasKind(["artifact.collect"]) ? "会回收日志、指标、模型文件、输出路径和复跑命令" : "需要 artifact.collect 或 eval.report 节点承接结果整理",
      status: hasKind(["artifact.collect", "eval.report"]) ? "ready" : "warning",
    },
  ];
}

function workspaceCockpitNodeRadarItems(workspace = selectedWorkspace()) {
  if (!workspace?.id) return [];
  const executionNodes = Array.isArray(workspace?.execution?.nodes) ? workspace.execution.nodes : [];
  const sourceNodes = executionNodes.length ? executionNodes : (Array.isArray(workspace.nodes) ? workspace.nodes : []);
  const resourceItems = workspace?.automation?.resource_orchestration?.items;
  const resourceIndex = {};
  if (Array.isArray(resourceItems)) {
    resourceItems.forEach((item) => {
      const kind = String(item?.node_kind || "").trim();
      if (kind && !resourceIndex[kind]) resourceIndex[kind] = item;
    });
  }
  const evidenceIndex = workspaceEvidenceGroupsByKind(workspace);
  const priority = [
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
  const seen = new Set();
  const orderedNodes = [
    ...priority
      .map((kind) => sourceNodes.find((node) => String(node?.kind || "") === kind))
      .filter(Boolean),
    ...sourceNodes.filter((node) => !priority.includes(String(node?.kind || ""))),
  ].filter((node) => {
    const id = String(node?.id || node?.kind || "");
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
  return orderedNodes.slice(0, 10).map((node, index) => {
    const kind = String(node.kind || "");
    const resource = resourceIndex[kind] || {};
    const evidenceItems = evidenceIndex[kind] || [];
    const handler = node.handler && typeof node.handler === "object" ? node.handler : {};
    const status = String(resource.status || node.status || "draft");
    const detail = String(resource.detail || node.error || node.summary || handler.handoff || "");
    const action = String(resource.action || handler.handoff || "等待自动推进判断下一步。");
    const value = String(resource.value || node.job_id || node.job_status || "");
    return {
      index: index + 1,
      id: String(node.id || kind || `node-${index}`),
      kind,
      label: workspaceCockpitStageLabel(kind),
      title: String(node.title || resource.label || workspaceNodeLabel(kind)),
      status,
      agent: String(node.agent_name || handler.name || globalAgentById(node.agent_id || handler.agent_id || "")?.name || "未指派"),
      phase: String(resource.phase || ""),
      detail,
      action,
      value,
      evidenceCount: Math.max(Number(resource.evidence_count || 0), evidenceItems.length),
      evidenceItems,
    };
  });
}

function workspaceCockpitNodeRadarMarkup(workspace = selectedWorkspace()) {
  const items = workspaceCockpitNodeRadarItems(workspace);
  if (!workspace?.id || !items.length) return "";
  const readyCount = items.filter((item) => ["ready", "done"].includes(item.status)).length;
  const blockedCount = items.filter((item) => ["blocked", "failed"].includes(item.status)).length;
  const warningCount = items.filter((item) => ["warning", "draft"].includes(item.status)).length;
  return `
    <div class="workspace-cockpit-radar">
      <div class="workspace-cockpit-radar-head">
        <div>
          <span>自动化链路雷达</span>
          <strong>${escapeHtml(`${readyCount}/${items.length} 节点就绪 · ${blockedCount} 阻塞 · ${warningCount} 待补`)}</strong>
        </div>
        <small>证据、调度、Agent 和下一步动作按节点收口</small>
      </div>
      <div class="workspace-cockpit-radar-grid">
        ${items.map((item) => {
          const evidencePreview = item.evidenceItems.slice(0, 2).map((evidence) => `${evidence.group}:${evidence.label}`).join(" / ");
          const title = `${item.title} · ${item.agent} · ${item.action}`;
          return `
            <button class="workspace-cockpit-radar-node status-${escapeHtml(item.status)}" type="button" data-action="select-execution-node" data-node-id="${escapeHtml(item.id)}" title="${escapeHtml(title)}">
              <span>${escapeHtml(String(item.index))}</span>
              <div>
                <strong>${escapeHtml(item.label)}</strong>
                <em>${escapeHtml(item.agent)}</em>
              </div>
              <small>${escapeHtml(item.evidenceCount ? `${item.evidenceCount} 条证据` : (item.value || "等待证据"))}</small>
              <p>${escapeHtml(evidencePreview || item.detail || item.action)}</p>
            </button>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

const WORKSPACE_NODE_IO_CONTRACTS = {
  "source.repo": {
    inputs: ["目标", "仓库 URL", "分支 / 提交"],
    output: "source_repo",
    evidence: "仓库来源、版本和启动目标",
  },
  "source.paper": {
    inputs: ["目标", "论文 / 资料", "参考线索"],
    output: "paper_context",
    evidence: "论文、任务和候选实现线索",
  },
  "source.idea": {
    inputs: ["目标描述", "约束", "成功标准"],
    output: "idea_brief",
    evidence: "需求、约束和验收标准",
  },
  "research.search": {
    inputs: ["source_context", "论文 / 资料", "参考线索"],
    output: "research_brief",
    evidence: "候选 repo、issue、论文和资料结论",
  },
  "repo.clone": {
    inputs: ["source_repo", "repo_url", "repo_ref"],
    output: "repo_checkout",
    evidence: "本地仓库路径、分支和提交",
  },
  "path.resolve": {
    inputs: ["repo_checkout", "工作目录", "数据 / 输出线索"],
    output: "path_map",
    evidence: "工作目录、数据目录、输出目录和日志目录",
  },
  "repo.inspect": {
    inputs: ["repo_checkout", "path_map"],
    output: "repo_profile",
    evidence: "入口脚本、依赖文件、默认参数和结果目录",
  },
  "dataset.find": {
    inputs: ["paper_context", "repo_profile", "数据集 / 路径线索"],
    output: "dataset_profile",
    evidence: "数据集名称、本地路径候选和结构要求",
  },
  "env.infer": {
    inputs: ["repo_profile", "path_map"],
    output: "env_requirements",
    evidence: "Python/CUDA/依赖文件和安装建议",
  },
  "env.prepare": {
    inputs: ["env_requirements", "setup_command"],
    output: "env_ready",
    evidence: "环境名、安装命令、依赖检查结果",
  },
  "gpu.allocate": {
    inputs: ["env_ready", "run_profile", "GPU 快照"],
    output: "gpu_allocation",
    evidence: "目标服务器、GPU 编号、显存和调度策略",
  },
  "run.command": {
    inputs: ["repo_profile", "dataset_profile", "env_ready", "gpu_allocation"],
    output: "run_result",
    evidence: "任务 ID、命令、日志、退出状态和运行路径",
  },
  "artifact.collect": {
    inputs: ["run_result", "path_map"],
    output: "artifact_manifest",
    evidence: "日志、指标、模型文件和复跑命令",
  },
  "eval.report": {
    inputs: ["artifact_manifest", "run_result"],
    output: "evaluation_report",
    evidence: "指标、结论、失败原因和下一步建议",
  },
};

function workspaceNodeIoContract(kind = "", index = 0) {
  const normalized = String(kind || "").trim();
  return WORKSPACE_NODE_IO_CONTRACTS[normalized] || {
    inputs: index ? ["上一节点输出", "节点配置"] : ["启动输入", "节点配置"],
    output: normalized ? normalized.replace(/[^a-zA-Z0-9]+/g, "_").replace(/^_+|_+$/g, "") || `step_${index + 1}` : `step_${index + 1}`,
    evidence: "节点配置、运行结果和交接备注",
  };
}

function workspaceNodeIoFallbackMapping(inputs = [], index = 0) {
  const mapping = {};
  (Array.isArray(inputs) ? inputs : []).slice(0, 6).forEach((raw) => {
    const label = String(raw || "").trim();
    if (!label) return;
    if (index === 0) {
      mapping[label] = "$input";
    } else if (label === "上一节点输出" || label === "source_context") {
      mapping[label] = "$prev.output";
    } else if (label.endsWith("_context") || label.endsWith("_profile") || label.endsWith("_ready") || label.endsWith("_allocation")) {
      mapping[label] = `$context.outputs.${label}`;
    } else {
      const slug = label.toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
      mapping[label] = `$input.${slug || label}`;
    }
  });
  return mapping;
}

function workspaceNodeWorkflowContractNode(workspace = selectedWorkspace(), node = null, sourceNode = null) {
  const runtimeContract = node?.workflow_contract_node && typeof node.workflow_contract_node === "object"
    ? node.workflow_contract_node
    : null;
  if (runtimeContract && Object.keys(runtimeContract).length) return runtimeContract;
  const nodeId = String(node?.id || sourceNode?.id || "").trim();
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  const contract = workspace?.automation?.workflow_contract && typeof workspace.automation.workflow_contract === "object"
    ? workspace.automation.workflow_contract
    : null;
  const nodes = Array.isArray(contract?.nodes) ? contract.nodes : [];
  return nodes.find((item) => String(item?.id || item?.node_id || "").trim() === nodeId)
    || nodes.find((item) => kind && String(item?.kind || item?.node_kind || "").trim() === kind)
    || null;
}

function workspaceNodeIoContractState(node = null, sourceNode = null, context = {}) {
  const workspace = context.workspace || selectedWorkspace();
  const template = context.template || selectedWorkflowTemplate();
  const sourceNodes = Array.isArray(workspace?.nodes) && workspace.nodes.length
    ? workspace.nodes
    : Array.isArray(template?.nodes)
      ? template.nodes
      : [];
  const nodeId = String(node?.id || sourceNode?.id || "").trim();
  const kind = String(sourceNode?.kind || node?.kind || "").trim();
  const index = Math.max(0, sourceNodes.findIndex((item) => String(item?.id || "").trim() === nodeId));
  const fallback = workspaceNodeIoContract(kind, index);
  const contractNode = workspaceNodeWorkflowContractNode(workspace, node, sourceNode);
  const rawMapping = contractNode?.input_mapping && typeof contractNode.input_mapping === "object"
    ? contractNode.input_mapping
    : sourceNode?.input_mapping && typeof sourceNode.input_mapping === "object"
      ? sourceNode.input_mapping
      : node?.input_mapping && typeof node.input_mapping === "object"
        ? node.input_mapping
        : {};
  const fallbackInputs = Array.isArray(fallback.inputs) ? fallback.inputs : [];
  const inputs = Array.isArray(contractNode?.inputs) && contractNode.inputs.length
    ? contractNode.inputs.map((item) => String(item || "").trim()).filter(Boolean)
    : Object.keys(rawMapping).length
      ? Object.keys(rawMapping)
      : fallbackInputs;
  const inputMapping = Object.keys(rawMapping).length
    ? Object.entries(rawMapping).reduce((acc, [key, value]) => {
      const name = String(key || "").trim();
      if (name) acc[name] = String(value || "").trim();
      return acc;
    }, {})
    : workspaceNodeIoFallbackMapping(inputs, index);
  const contextPayload = contractNode?.context && typeof contractNode.context === "object"
    ? contractNode.context
    : workspace?.automation?.workflow_contract?.context && typeof workspace.automation.workflow_contract.context === "object"
      ? workspace.automation.workflow_contract.context
      : {
        input_key: "$input",
        outputs_key: "$context.outputs",
        previous_key: "$prev.output",
      };
  const handler = sourceNode?.handler && typeof sourceNode.handler === "object" ? sourceNode.handler : {};
  const agentPayload = contractNode?.agent && typeof contractNode.agent === "object" ? contractNode.agent : {};
  const agentId = String(agentPayload.id || handler.agent_id || node?.agent_id || "").trim();
  const workspaceAgents = Array.isArray(workspace?.agents) ? workspace.agents : [];
  const agent = workspaceAgentById(agentId, workspaceAgents) || globalAgentById(agentId) || {};
  const toolsPayload = Array.isArray(contractNode?.tools) ? contractNode.tools : [];
  const fallbackToolIds = Array.isArray(agent.tools) ? agent.tools : parseTagList(agent.tools || "");
  const workspaceTools = Array.isArray(workspace?.tools) ? workspace.tools : [];
  const tools = (toolsPayload.length ? toolsPayload : fallbackToolIds)
    .map((tool) => {
      const toolId = String(tool?.id || tool || "").trim();
      const resolved = workspaceToolById(toolId, workspaceTools) || globalToolById(toolId) || {};
      return {
        id: toolId,
        label: String(tool?.label || resolved.label || toolId || "").trim(),
        enabled: tool?.enabled !== false && resolved.enabled !== false,
      };
    })
    .filter((tool) => tool.id || tool.label);
  const modelPayload = contractNode?.model && typeof contractNode.model === "object" ? contractNode.model : {};
  const profileId = String(
    modelPayload.effective_profile_id
    || modelPayload.workspace_profile_id
    || modelPayload.agent_profile_id
    || agent.provider_profile_id
    || workspace?.model?.provider_profile_id
    || template?.model?.provider_profile_id
    || "",
  ).trim();
  const profile = providerProfileById(profileId);
  const modelLabel = modelPayload.label
    ? `${modelPayload.label}${profile ? ` · ${providerProfileLabel(profile)}` : ""}`
    : profile
      ? providerProfileLabel(profile)
      : "继承默认路由";
  const nextTitle = String(contractNode?.next_node_title || "最终报告").trim();
  const handoff = String(
    contractNode?.handoff
    || handler.handoff
    || (nextTitle ? `交给 ${nextTitle}` : "交给报告/归档"),
  ).trim();
  return {
    kind,
    index,
    title: String(sourceNode?.title || node?.title || workspaceNodeLabel(kind) || "未选择节点"),
    inputMapping,
    inputs,
    outputKey: String(contractNode?.output_key || sourceNode?.output_key || node?.output_key || fallback.output || fallback.output_key || `step_${index + 1}`).trim(),
    context: contextPayload,
    handoff,
    nextTitle,
    agentName: String(agentPayload.name || handler.name || node?.agent_name || agent.name || "未指派 Agent").trim(),
    tools,
    modelLabel,
    route: String(modelPayload.source || modelPayload.routing_mode || "workspace_default").trim(),
  };
}

function workspaceNodeIoContractMarkup(node = null, sourceNode = null, context = {}) {
  const contract = workspaceNodeIoContractState(node, sourceNode, context);
  const mappingEntries = Object.entries(contract.inputMapping || {}).slice(0, 8);
  const contextEntries = Object.entries(contract.context || {}).filter(([key]) => String(key || "").trim());
  const toolLabels = contract.tools.map((tool) => tool.label || tool.id).filter(Boolean);
  return `
    <div class="workspace-node-io-contract">
      <div class="workspace-node-io-summary">
        <article>
          <span>输入映射</span>
          <strong>${escapeHtml(`${mappingEntries.length} 项`)}</strong>
          <em title="input_mapping 决定本节点从启动输入、上游输出或上下文读取哪些字段">input_mapping</em>
        </article>
        <article>
          <span>输出键</span>
          <strong title="${escapeHtml(contract.outputKey)}">${escapeHtml(contract.outputKey || "等待 output_key")}</strong>
          <em title="output_key 会写入 $context.outputs，供下游节点引用">output_key</em>
        </article>
        <article>
          <span>交接对象</span>
          <strong title="${escapeHtml(contract.handoff)}">${escapeHtml(contract.nextTitle || "最终报告")}</strong>
          <em title="${escapeHtml(contract.handoff)}">${escapeHtml(contract.handoff || "等待交接")}</em>
        </article>
      </div>
      <div class="workspace-node-io-map">
        <div class="workspace-node-io-column">
          <span>输入来源</span>
          ${mappingEntries.length ? mappingEntries.map(([key, value]) => `
            <div class="workspace-node-io-row" title="${escapeHtml(`${key}: ${value}`)}">
              <strong>${escapeHtml(key)}</strong>
              <em>${escapeHtml(value || "等待来源")}</em>
            </div>
          `).join("") : '<div class="empty">还没有 input_mapping。</div>'}
        </div>
        <div class="workspace-node-io-arrow" aria-hidden="true">→</div>
        <div class="workspace-node-io-column output">
          <span>写入上下文</span>
          <div class="workspace-node-io-row">
            <strong>${escapeHtml(contract.outputKey || "step_output")}</strong>
            <em>${escapeHtml(`$context.outputs.${contract.outputKey || "step_output"}`)}</em>
          </div>
          <div class="workspace-node-io-row muted">
            <strong>${escapeHtml(contract.title)}</strong>
            <em>${escapeHtml(contract.kind || "custom.step")}</em>
          </div>
        </div>
      </div>
      <div class="workspace-node-io-runtime">
        ${contextEntries.map(([key, value]) => `
          <span title="${escapeHtml(`${key}: ${value}`)}">${escapeHtml(`${key}: ${value}`)}</span>
        `).join("")}
        <span title="${escapeHtml(contract.agentName)}">Agent: ${escapeHtml(contract.agentName)}</span>
        <span title="${escapeHtml(toolLabels.join(" / ") || "等待工具")}">Tools: ${escapeHtml(toolLabels.slice(0, 4).join(" / ") || "待定")}</span>
        <span title="${escapeHtml(`${contract.route} · ${contract.modelLabel}`)}">Model: ${escapeHtml(contract.modelLabel)}</span>
      </div>
    </div>
  `;
}

function workspaceNodeConfigSignal(node = {}) {
  const config = node.config && typeof node.config === "object" ? node.config : {};
  const values = [
    config.repo_url,
    config.workspace_dir,
    config.data_roots,
    config.dataset_hints,
    config.setup_command,
    config.run_command,
    config.server_id,
    config.artifact_paths,
    config.metric_paths,
  ].map((item) => String(item || "").trim()).filter(Boolean);
  return values[0] || "";
}

function workspaceHandoffEvidenceLabel(evidenceItems = [], resource = {}, node = {}) {
  if (evidenceItems.length) {
    const first = evidenceItems[0];
    const label = [first.group, first.label].filter(Boolean).join(" · ");
    return evidenceItems.length > 1 ? `${label} +${evidenceItems.length - 1}` : label;
  }
  const value = String(resource.value || resource.detail || "").trim();
  if (value) return value;
  const job = String(node.job_status || node.status || "").trim();
  if (job) return workspaceStatusLabel(job);
  return "";
}

function workspaceCockpitHandoffItems(workspace = selectedWorkspace()) {
  if (!workspace?.id) return [];
  const backendContract = workspace?.automation?.workflow_contract && typeof workspace.automation.workflow_contract === "object"
    ? workspace.automation.workflow_contract
    : null;
  const backendNodes = Array.isArray(backendContract?.nodes) ? backendContract.nodes : [];
  if (backendNodes.length) {
    return backendNodes.slice(0, 12).map((item, index) => {
      const agent = item.agent && typeof item.agent === "object" ? item.agent : {};
      const model = item.model && typeof item.model === "object" ? item.model : {};
      const inputMapping = item.input_mapping && typeof item.input_mapping === "object" ? item.input_mapping : {};
      const inputs = Array.isArray(item.inputs) && item.inputs.length
        ? item.inputs
        : Object.keys(inputMapping);
      return {
        id: String(item.id || item.kind || `node-${index}`),
        index: Number(item.index || index + 1),
        kind: String(item.kind || ""),
        title: String(item.title || workspaceNodeLabel(item.kind || "")),
        status: String(item.status || "draft"),
        phase: String(item.phase_label || workspaceStarterNodePhase(item.kind || "")),
        inputs: inputs.slice(0, 4).map((value) => String(value || "").trim()).filter(Boolean),
        outputKey: String(item.output_key || `step_${index + 1}`),
        evidence: String(item.evidence || "等待证据"),
        configSignal: String(item.config_signal || ""),
        handoff: String(item.handoff || (item.next_node_title ? `交给 ${item.next_node_title}` : "交给报告/归档")),
        next: String(item.next_node_title || "最终报告"),
        agent: String(agent.name || agent.id || "未指派 Agent"),
        tools: (Array.isArray(item.tools) ? item.tools : [])
          .map((tool) => String(tool?.label || tool?.id || tool || "").trim())
          .filter(Boolean)
          .slice(0, 3),
        model: String(model.effective_profile_id || model.workspace_profile_id || model.agent_profile_id || ""),
        evidenceCount: Number(item.evidence_count || 0),
      };
    });
  }
  const executionNodes = Array.isArray(workspace?.execution?.nodes) ? workspace.execution.nodes : [];
  const sourceNodes = executionNodes.length ? executionNodes : (Array.isArray(workspace.nodes) ? workspace.nodes : []);
  if (!sourceNodes.length) return [];
  const resourceItems = workspace?.automation?.resource_orchestration?.items;
  const resourceIndex = {};
  if (Array.isArray(resourceItems)) {
    resourceItems.forEach((item) => {
      const kind = String(item?.node_kind || "").trim();
      if (kind && !resourceIndex[kind]) resourceIndex[kind] = item;
    });
  }
  const evidenceIndex = workspaceEvidenceGroupsByKind(workspace);
  return sourceNodes.slice(0, 12).map((node, index) => {
    const kind = String(node.kind || "");
    const contract = workspaceNodeIoContract(kind, index);
    const resource = resourceIndex[kind] || {};
    const evidenceItems = evidenceIndex[kind] || [];
    const handler = node.handler && typeof node.handler === "object" ? node.handler : {};
    const agentId = String(node.agent_id || handler.agent_id || "").trim();
    const agent = workspaceAgentById(agentId) || globalAgentById(agentId) || {};
    const tools = Array.isArray(agent.tools) && agent.tools.length
      ? agent.tools
      : Array.isArray(handler.tools)
        ? handler.tools
        : [];
    const status = String(resource.status || node.status || "draft");
    const nextNode = sourceNodes[index + 1] || null;
    const outputKey = String(node.output_key || contract.output || `step_${index + 1}`);
    const inputMapping = node.input_mapping && typeof node.input_mapping === "object" ? node.input_mapping : null;
    const inputLabels = Array.isArray(inputMapping) && inputMapping.length
      ? inputMapping
      : inputMapping && !Array.isArray(inputMapping) && Object.keys(inputMapping).length
        ? Object.entries(inputMapping).map(([key, value]) => `${key}: ${String(value || "")}`)
        : Array.isArray(contract.inputs)
          ? contract.inputs
          : [];
    return {
      id: String(node.id || kind || `node-${index}`),
      index: index + 1,
      kind,
      title: String(node.title || workspaceNodeLabel(kind)),
      status,
      phase: workspaceStarterNodePhase(kind),
      inputs: inputLabels.slice(0, 4).map((item) => String(item || "").trim()).filter(Boolean),
      outputKey,
      evidence: workspaceHandoffEvidenceLabel(evidenceItems, resource, node) || contract.evidence || "等待证据",
      configSignal: workspaceNodeConfigSignal(node),
      handoff: String(handler.handoff || resource.action || (nextNode ? `交给 ${nextNode.title || workspaceNodeLabel(nextNode.kind)}` : "交给报告/归档") || ""),
      next: nextNode ? String(nextNode.title || workspaceNodeLabel(nextNode.kind)) : "最终报告",
      agent: String(node.agent_name || handler.name || agent.name || agent.display_name || "未指派 Agent"),
      tools: tools.map((tool) => String(tool?.label || tool?.id || tool || "").trim()).filter(Boolean).slice(0, 3),
      model: String(handler.provider_profile_id || agent.provider_profile_id || workspace.model?.provider_profile_id || ""),
      evidenceCount: evidenceItems.length,
    };
  });
}

function workspaceCockpitHandoffMapMarkup(workspace = selectedWorkspace()) {
  const items = workspaceCockpitHandoffItems(workspace);
  if (!workspace?.id || !items.length) return "";
  const mapped = items.filter((item) => item.inputs.length && item.outputKey).length;
  const ready = items.filter((item) => ["ready", "done"].includes(item.status)).length;
  const blocked = items.filter((item) => ["blocked", "failed"].includes(item.status)).length;
  return `
    <div class="workspace-cockpit-handoff-map">
      <div class="workspace-cockpit-handoff-head">
        <div>
          <span>节点 I/O 交接图</span>
          <strong>${escapeHtml(`${mapped}/${items.length} 节点有输入/输出契约 · ${ready} 就绪 · ${blocked} 阻塞`)}</strong>
        </div>
        <small title="参考工作流 input_mapping / output_key / context 的结构，把复现部署链上的输入、证据、输出和下游交接显式化">input_mapping / output_key / context</small>
      </div>
      <div class="workspace-cockpit-handoff-rail">
        ${items.map((item) => `
          <button class="workspace-cockpit-handoff-node status-${escapeHtml(item.status)}" type="button" data-action="select-execution-node" data-node-id="${escapeHtml(item.id)}" title="${escapeHtml(`${item.title} · 输出 ${item.outputKey} · ${item.handoff}`)}">
            <div class="workspace-cockpit-handoff-order">
              <span>${escapeHtml(String(item.index))}</span>
              <em>${escapeHtml(item.phase)}</em>
            </div>
            <div class="workspace-cockpit-handoff-body">
              <div class="workspace-cockpit-handoff-title">
                <strong>${escapeHtml(item.title)}</strong>
                <small>${escapeHtml(item.agent)}</small>
              </div>
              <div class="workspace-cockpit-handoff-io">
                <article>
                  <span>输入</span>
                  <strong title="${escapeHtml(item.inputs.join(" / "))}">${escapeHtml(item.inputs.join(" / ") || "等待输入映射")}</strong>
                </article>
                <article>
                  <span>输出键</span>
                  <strong title="${escapeHtml(item.outputKey)}">${escapeHtml(item.outputKey)}</strong>
                </article>
                <article>
                  <span>证据 / 配置</span>
                  <strong title="${escapeHtml(item.configSignal || item.evidence)}">${escapeHtml(item.configSignal || item.evidence)}</strong>
                </article>
              </div>
              <div class="workspace-cockpit-handoff-meta">
                <span title="${escapeHtml(item.tools.join(" / ") || "等待工具")}">${escapeHtml(item.tools.length ? item.tools.join(" / ") : "工具待定")}</span>
                <span title="${escapeHtml(item.model || "继承项目默认 AI 路由")}">${escapeHtml(item.model || "默认路由")}</span>
                <span title="${escapeHtml(item.handoff)}">→ ${escapeHtml(item.next)}</span>
              </div>
            </div>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function workspaceExecutionContextBusMarkup(workspace = selectedWorkspace(), { limit = 6, compact = false } = {}) {
  const context = workspace?.automation?.execution_context && typeof workspace.automation.execution_context === "object"
    ? workspace.automation.execution_context
    : null;
  if (!workspace?.id || !context) return compact ? "" : '<div class="empty">还没有执行上下文总线。</div>';
  const input = context.input_data && typeof context.input_data === "object" ? context.input_data : {};
  const outputs = Array.isArray(context.outputs) ? context.outputs : [];
  const steps = Array.isArray(context.step_results) ? context.step_results : [];
  const totals = context.totals && typeof context.totals === "object" ? context.totals : {};
  const contextKeys = context.context && typeof context.context === "object" ? context.context : {};
  const visibleSteps = steps.slice(0, compact ? Math.min(limit, 5) : limit);
  const inputFacts = [
    `${Number(input.repo_count || 0)} repo`,
    `${Number(input.paper_count || 0)} paper`,
    `${Number(input.reference_count || 0)} 参考/路径`,
    `${Number(input.context_count || 0)} 上下文`,
  ];
  return `
    <div class="workspace-context-bus status-${escapeHtml(context.status || "draft")}">
      <div class="workspace-context-bus-head">
        <div>
          <span>执行上下文总线</span>
          <strong>${escapeHtml(context.summary || "等待上下文生成")}</strong>
        </div>
        <small title="参考 FoodMemo 工作流的 input_data / context.outputs / step_results 结构，把自动推进中的输入、输出和步骤结果显式化">${escapeHtml(`${contextKeys.input_key || "$input"} → ${contextKeys.outputs_key || "$context.outputs"}`)}</small>
      </div>
      <div class="workspace-context-bus-metrics">
        <article class="status-${escapeHtml(input.goal_present ? "ready" : "draft")}">
          <span>input_data</span>
          <strong>${escapeHtml(input.source_mode || "idea")}</strong>
          <em>${escapeHtml(inputFacts.join(" · "))}</em>
        </article>
        <article class="status-${escapeHtml(Number(totals.produced_output_count || 0) ? "ready" : "draft")}">
          <span>context.outputs</span>
          <strong>${escapeHtml(`${Number(totals.produced_output_count || 0)}/${Number(totals.output_count || outputs.length || 0)}`)}</strong>
          <em>已产生输出键</em>
        </article>
        <article class="status-${escapeHtml(Number(totals.running_count || 0) ? "running" : Number(totals.failed_count || 0) ? "failed" : "ready")}">
          <span>step_results</span>
          <strong>${escapeHtml(`${Number(totals.running_count || 0)} 运行 · ${Number(totals.failed_count || 0)} 失败`)}</strong>
          <em>${escapeHtml(`${Number(totals.step_count || steps.length || 0)} 步 · ${Number(totals.blocked_input_count || 0)} 输入阻塞`)}</em>
        </article>
      </div>
      <div class="workspace-context-output-rail">
        ${outputs.slice(0, compact ? 8 : 12).map((item) => `
          <button class="workspace-context-output status-${escapeHtml(item.status || "draft")}" type="button" data-action="select-execution-node" data-node-id="${escapeHtml(item.node_id || "")}" title="${escapeHtml(`${item.key || "output"} · ${item.title || item.node_kind || ""} · ${item.handoff || ""}`)}">
            <span>${escapeHtml(item.key || "output")}</span>
            <strong>${escapeHtml(item.produced ? "已写入" : workspaceStatusLabel(item.status || "draft"))}</strong>
            <em>${escapeHtml(item.next_node_title || "最终报告")}</em>
          </button>
        `).join("") || '<div class="empty">还没有 output_key。</div>'}
      </div>
      ${compact ? "" : `
        <div class="workspace-context-step-list">
          ${visibleSteps.map((step) => {
            const agent = step.agent && typeof step.agent === "object" ? step.agent : {};
            const inputs = Array.isArray(step.resolved_inputs) ? step.resolved_inputs : [];
            const tools = Array.isArray(step.tools) ? step.tools : [];
            const model = step.model && typeof step.model === "object" ? step.model : {};
            return `
              <article class="workspace-context-step status-${escapeHtml(step.status || step.output_status || "draft")}">
                <div class="workspace-context-step-main">
                  <span>${escapeHtml(`${step.step_order || ""}. ${workspaceCockpitStageLabel(step.node_kind || "")}`)}</span>
                  <strong>${escapeHtml(step.title || step.node_kind || "步骤")}</strong>
                  <em title="${escapeHtml(inputs.map((item) => `${item.name}:${item.source}`).join(" / "))}">${escapeHtml(inputs.slice(0, 3).map((item) => `${item.name} ← ${item.source}`).join(" / ") || "等待 input_mapping")}</em>
                </div>
                <div class="workspace-context-step-side">
                  <span title="${escapeHtml(agent.name || agent.id || "未指派 Agent")}">${escapeHtml(agent.name || agent.id || "未指派 Agent")}</span>
                  <em title="${escapeHtml(tools.map((tool) => tool.label || tool.id || tool).join(" / ") || "等待工具")}">${escapeHtml(tools.map((tool) => tool.label || tool.id || tool).slice(0, 3).join(" / ") || "工具待定")}</em>
                  <small title="${escapeHtml(model.effective_profile_id || model.workspace_profile_id || "继承默认路由")}">${escapeHtml(`${step.output_key || "output"} · ${step.input_status || "draft"}`)}</small>
                </div>
              </article>
            `;
          }).join("") || '<div class="empty">还没有 step_results。</div>'}
        </div>
      `}
    </div>
  `;
}

function workspaceManifestItemAction(item = {}, manifest = {}) {
  const id = String(item.id || "").trim();
  const status = String(item.status || "draft");
  const nodeId = String(item.node_id || "").trim();
  const ready = ["ready", "done"].includes(status);
  if (id === "gpu") {
    return {
      label: "刷新资源",
      action: "refresh-workspace-resources",
      title: "刷新服务器、GPU、任务和资源快照，然后重新计算清单状态",
    };
  }
  if (id === "run") {
    return ready
      ? {
          label: "运行工作流",
          action: "run-selected-workspace",
          title: "门禁通过后提交完整工作流",
        }
      : {
          label: "自动推进",
          action: "advance-workspace-automation",
          title: "根据当前门禁自动决定发现、回填或完整运行",
        };
  }
  if (["checkout", "dataset", "environment", "artifacts"].includes(id) && !ready) {
    return {
      label: "自动发现",
      action: "run-workspace-discovery",
      title: "提交安全发现链，补齐路径、数据、环境、GPU 和产物证据",
    };
  }
  if (id === "report" && ready && nodeId) {
    return {
      label: "运行报告",
      action: "run-selected-node",
      nodeId,
      title: "只运行报告节点，整理指标、产物和复跑建议",
    };
  }
  if (ready && nodeId && id !== "source") {
    return {
      label: "运行节点",
      action: "run-selected-node",
      nodeId,
      title: "只运行当前清单项对应节点，用于单点调试",
    };
  }
  if (manifest?.ready_to_run) {
    return {
      label: "运行工作流",
      action: "run-selected-workspace",
      title: "清单已就绪，提交完整工作流",
    };
  }
  return {
    label: "自动推进",
    action: "advance-workspace-automation",
    title: "让系统按当前清单和门禁决定下一步",
  };
}

function workspaceManifestActionButton(action = {}, tone = "secondary") {
  if (!action?.action) return "";
  const nodeId = action.nodeId || action.node_id || "";
  const serverId = action.serverId || action.server_id || "";
  const nodeAttr = nodeId ? ` data-node-id="${escapeHtml(nodeId)}"` : "";
  const serverAttr = serverId ? ` data-server-id="${escapeHtml(serverId)}"` : "";
  const help = workspaceAutomationActionHelp(action.action, action.title || action.label || "执行清单动作");
  return `
    <button class="${tone} mini" type="button" data-action="${escapeHtml(action.action)}"${nodeAttr}${serverAttr} title="${escapeHtml(help)}">
      ${escapeHtml(action.label || "执行")}
    </button>
  `;
}

function workspaceManifestNextAction(manifest = {}) {
  const next = manifest.next_action && typeof manifest.next_action === "object" ? manifest.next_action : {};
  const item = Array.isArray(manifest.items)
    ? manifest.items.find((candidate) => String(candidate?.id || "") === String(next.id || ""))
    : null;
  return workspaceManifestItemAction(item || next, manifest);
}

function workspaceExecutionBundleMarkup(manifest = {}, { compact = false } = {}) {
  const bundle = manifest.execution_bundle && typeof manifest.execution_bundle === "object" ? manifest.execution_bundle : null;
  if (!bundle) return "";
  const target = bundle.target && typeof bundle.target === "object" ? bundle.target : {};
  const steps = Array.isArray(bundle.steps) ? bundle.steps : [];
  const missing = Array.isArray(bundle.missing) ? bundle.missing : [];
  const nextAction = bundle.next_action && typeof bundle.next_action === "object" ? bundle.next_action : {};
  const visibleSteps = compact ? steps.slice(0, 4) : steps;
  const targetItems = [
    { label: "server", value: target.server_id || "auto" },
    { label: "gpu", value: `${target.gpu_index || "auto"} · ${target.gpu_policy || "auto"}` },
    { label: "cwd", value: target.workspace_dir || "等待路径" },
    { label: "env", value: target.env_name || target.env_manager || "待定" },
  ];
  return `
    <div class="workspace-execution-bundle status-${escapeHtml(bundle.status || "draft")}">
      <div class="workspace-execution-bundle-head">
        <div>
          <span>执行包</span>
          <strong>${escapeHtml(bundle.ready_to_execute ? "可提交执行" : missing.length ? `${missing.length} 项待补齐` : "等待运行预案")}</strong>
        </div>
        <div class="workspace-execution-bundle-actions">
          <small>${escapeHtml(nextAction.title || target.label || "自动复现/部署")}</small>
          ${workspaceManifestActionButton(nextAction, bundle.ready_to_execute ? "primary" : "secondary")}
        </div>
      </div>
      <div class="workspace-execution-bundle-target">
        ${targetItems.map((item) => `
          <span title="${escapeHtml(item.value)}">${escapeHtml(`${item.label}: ${item.value}`)}</span>
        `).join("")}
      </div>
      <div class="workspace-execution-bundle-steps">
        ${visibleSteps.map((step) => {
          const nodeId = String(step.node_id || "").trim();
          const tag = nodeId ? "button" : "article";
          const attrs = nodeId ? `type="button" data-action="select-execution-node" data-node-id="${escapeHtml(nodeId)}"` : "";
          const envText = step.env && typeof step.env === "object"
            ? Object.entries(step.env).map(([key, value]) => `${key}=${value}`).join(" ")
            : "";
          return `
            <${tag} class="workspace-execution-bundle-step status-${escapeHtml(step.status || "draft")}" ${attrs} title="${escapeHtml(step.command || step.detail || "")}">
              <span>${escapeHtml(step.label || step.id || "步骤")}</span>
              <strong>${escapeHtml(step.command || workspaceStatusLabel(step.status || "draft"))}</strong>
              ${compact ? "" : `<em>${escapeHtml([step.cwd, envText].filter(Boolean).join(" · ") || step.detail || "")}</em>`}
            </${tag}>
          `;
        }).join("") || '<div class="empty">执行包还没有步骤。</div>'}
      </div>
      ${compact || !missing.length ? "" : `
        <div class="workspace-execution-bundle-missing">
          ${missing.slice(0, 5).map((item) => `
            <span class="status-${escapeHtml(item.status || "warning")}" title="${escapeHtml(item.action || "")}">${escapeHtml(`${item.label || item.field}: ${item.action || "待补齐"}`)}</span>
          `).join("")}
        </div>
      `}
    </div>
  `;
}

function workspaceReproductionManifestMarkup(workspace = selectedWorkspace(), { limit = 8, compact = false } = {}) {
  const manifest = workspace?.automation?.reproduction_manifest && typeof workspace.automation.reproduction_manifest === "object"
    ? workspace.automation.reproduction_manifest
    : null;
  if (!workspace?.id || !manifest) return compact ? "" : '<div class="empty">还没有复现/部署清单。</div>';
  const items = Array.isArray(manifest.items) ? manifest.items.slice(0, limit) : [];
  const next = manifest.next_action && typeof manifest.next_action === "object" ? manifest.next_action : {};
  const commands = manifest.commands && typeof manifest.commands === "object" ? manifest.commands : {};
  const intent = manifest.intent && typeof manifest.intent === "object" ? manifest.intent : {};
  const commandItems = [
    { label: "setup", value: commands.setup_command },
    { label: "run", value: commands.run_command },
    { label: "report", value: commands.report_command },
  ].filter((item) => String(item.value || "").trim());
  return `
    <div class="workspace-manifest status-${escapeHtml(manifest.status || "draft")}">
      <div class="workspace-manifest-head">
        <div>
          <span>复现/部署清单</span>
          <strong>${escapeHtml(manifest.summary || "等待清单生成")}</strong>
        </div>
        <div class="workspace-manifest-head-actions">
          <small title="${escapeHtml(next.action || next.detail || "下一步")}">${escapeHtml(next.title || intent.label || "等待下一步")}</small>
          ${workspaceManifestActionButton(workspaceManifestNextAction(manifest), "primary")}
        </div>
      </div>
      <div class="workspace-manifest-items">
        ${items.map((item) => {
          const nodeId = String(item.node_id || "").trim();
          const action = workspaceManifestItemAction(item, manifest);
          return `
            <article class="workspace-manifest-item status-${escapeHtml(item.status || "draft")}" title="${escapeHtml(item.action || item.detail || "")}">
              <span>${escapeHtml(item.label || item.id || "清单项")}</span>
              <strong>${escapeHtml(item.title || workspaceStatusLabel(item.status || "draft"))}</strong>
              <em title="${escapeHtml(item.value || item.detail || "")}">${escapeHtml(item.value || item.detail || "等待")}</em>
              ${compact ? "" : `<small>${escapeHtml(item.detail || item.action || "")}</small>`}
              ${compact ? "" : `
                <div class="workspace-manifest-item-actions">
                  ${nodeId ? workspaceManifestActionButton({ label: "定位节点", action: "select-execution-node", nodeId, title: `点击定位执行节点：${item.label || item.id || ""}` }) : ""}
                  ${workspaceManifestActionButton(action)}
                </div>
              `}
            </article>
          `;
        }).join("") || '<div class="empty">还没有清单项。</div>'}
      </div>
      ${workspaceExecutionBundleMarkup(manifest, { compact })}
      ${compact || !commandItems.length ? "" : `
        <div class="workspace-manifest-commands">
          ${commandItems.map((item) => `
            <span title="${escapeHtml(item.value)}">${escapeHtml(`${item.label}: ${item.value}`)}</span>
          `).join("")}
        </div>
      `}
      ${compact ? "" : `
        <div class="workspace-manifest-next status-${escapeHtml(next.status || manifest.status || "draft")}">
          <strong>${escapeHtml(next.title || "等待下一步")}</strong>
          <span>${escapeHtml(next.detail || "")}</span>
          <em>${escapeHtml(next.action || "")}</em>
        </div>
      `}
    </div>
  `;
}

function workspaceEvidenceBackfillMarkup(workspace = selectedWorkspace(), { limit = 6, compact = false } = {}) {
  const plan = workspace?.automation?.evidence_backfill && typeof workspace.automation.evidence_backfill === "object"
    ? workspace.automation.evidence_backfill
    : null;
  if (!plan) return compact ? "" : '<div class="empty">还没有证据回填计划。</div>';
  const items = Array.isArray(plan.items) ? plan.items : [];
  const visible = items
    .filter((item) => compact ? ["ready", "warning", "blocked"].includes(String(item.status || "")) : true)
    .slice(0, limit);
  if (!visible.length && compact) return "";
  return `
    <div class="workspace-backfill-plan status-${escapeHtml(plan.status || "draft")}">
      <div class="workspace-backfill-head">
        <div>
          <span>证据回填解释</span>
          <strong>${escapeHtml(plan.summary || "等待发现证据")}</strong>
        </div>
        <small>${escapeHtml(plan.next_action?.action || "显示证据会进入哪个节点字段")}</small>
      </div>
      <div class="workspace-backfill-list">
        ${visible.map((item) => {
          const mode = item.mode === "replace" ? "写入/替换" : "追加";
          const current = String(item.current || "").trim();
          const value = String(item.value || "").trim();
          const detail = current
            ? `当前: ${current}`
            : value
              ? `候选: ${value}`
              : item.action || "等待证据";
          return `
            <article class="workspace-backfill-item status-${escapeHtml(item.status || "draft")}">
              <div>
                <span>${escapeHtml(workspaceCockpitStageLabel(item.node_kind || ""))} · ${escapeHtml(item.field || "")}</span>
                <strong>${escapeHtml(item.label || item.field || "回填项")}</strong>
                <em title="${escapeHtml(detail)}">${escapeHtml(detail)}</em>
              </div>
              <small title="${escapeHtml(item.action || "")}">${escapeHtml(`${mode} · ${workspaceStatusLabel(item.status || "draft")}`)}</small>
            </article>
          `;
        }).join("") || '<div class="empty">还没有可展示的回填项。</div>'}
      </div>
    </div>
  `;
}

function workspaceCockpitActionButton(button = {}) {
  const tone = button.tone === "primary" ? "primary" : "secondary";
  const nonBlocking = WORKSPACE_NON_BLOCKING_ACTIONS.has(button.action);
  const busy = Boolean(state.ui.workspaceAutomationBusyAction) && !nonBlocking;
  const currentBusy = busy && state.ui.workspaceAutomationBusyAction === button.action;
  const help = workspaceAutomationActionHelp(button.action, button.title || button.detail || button.label || "执行操作");
  return `
    <button
      class="${tone} mini"
      type="button"
      data-action="${escapeHtml(button.action || "")}"
      title="${escapeHtml(help)}"
      aria-label="${escapeHtml(`${button.label || "操作"}：${help}`)}"
      data-workspace-help="${escapeHtml(help)}"
      ${busy ? "disabled" : ""}
    >${escapeHtml(currentBusy ? "处理中..." : button.label || "操作")}</button>
  `;
}

function workspaceStarterNodePhase(kind = "") {
  const normalized = String(kind || "").trim();
  if (["source.repo", "source.paper", "source.idea", "research.search"].includes(normalized)) return "输入";
  if (["repo.clone", "path.resolve", "repo.inspect", "dataset.find"].includes(normalized)) return "发现";
  if (["env.infer", "env.prepare"].includes(normalized)) return "环境";
  if (["gpu.allocate", "run.command"].includes(normalized)) return "调度";
  if (["artifact.collect", "eval.report"].includes(normalized)) return "回收";
  return "其他";
}

function workspaceStarterDecision(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), resources = null) {
  const hasInput = Boolean(
    String(inputs.goal_text || "").trim()
    || (Array.isArray(inputs.repo_urls) && inputs.repo_urls.length)
    || (Array.isArray(inputs.paper_urls) && inputs.paper_urls.length)
    || (Array.isArray(inputs.references) && inputs.references.length)
    || (Array.isArray(inputs.context_blocks) && inputs.context_blocks.length)
  );
  const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
  const automatedNodes = nodes.filter((node) => String(node?.handler?.mode || "human") !== "human");
  const assignedNodes = automatedNodes.filter((node) => String(node?.handler?.agent_id || "").trim()).length;
  const templateReady = Boolean(nodes.length && assignedNodes === automatedNodes.length);
  const safeDiscoveryKinds = ["repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate", "artifact.collect"];
  const safeCount = nodes.filter((node) => safeDiscoveryKinds.includes(String(node?.kind || ""))).length;
  const hasRunNode = nodes.some((node) => String(node?.kind || "") === "run.command");
  const resourceState = String(resources?.state || "draft");
  if (!hasInput) {
    return {
      status: "draft",
      title: "先补目标输入",
      detail: "目标、repo、论文、数据路径或成功标准至少需要一类线索。",
      primary: null,
      secondary: { label: "配置中心", action: "switch-workspace-manage", title: "查看 Starter Chain、Agent、工具和 AI 配置" },
    };
  }
  if (!nodes.length) {
    return {
      status: "blocked",
      title: "先选择 Starter Chain",
      detail: "没有链路模板时无法生成实例快照。",
      primary: { label: "配置中心", action: "switch-workspace-manage", title: "创建或选择 Starter Chain 模板" },
      secondary: null,
    };
  }
  if (!templateReady) {
    return {
      status: "warning",
      title: "补齐自动节点接管",
      detail: `${assignedNodes}/${automatedNodes.length || 0} 个自动节点已绑定 Agent，建议先补齐交接人和工具边界。`,
      primary: { label: "配置中心", action: "switch-workspace-manage", title: "补齐节点 Agent、工具 allowlist 和模型路由" },
      secondary: { label: "创建任务", action: "create-workspace", title: "先创建实例快照，稍后再补自动化配置" },
    };
  }
  if (!safeCount) {
    return {
      status: "blocked",
      title: "缺少安全发现链",
      detail: "至少需要 repo/path/dataset/env/gpu/artifact 中的一段发现节点，自动推进才有证据来源。",
      primary: { label: "配置中心", action: "switch-workspace-manage", title: "补齐安全发现链节点" },
      secondary: { label: "创建任务", action: "create-workspace", title: "只创建实例，不提交自动发现" },
    };
  }
  if (["failed", "blocked"].includes(resourceState)) {
    return {
      status: "warning",
      title: "资源快照需要确认",
      detail: resources?.detail || "服务器/GPU 快照不可用时，创建后仍可发现代码和路径，但调度判断会偏弱。",
      primary: { label: "刷新资源", action: "refresh-workspace-resources", title: "刷新服务器、GPU、任务和资源快照" },
      secondary: { label: "创建并自动发现", action: "create-workspace-discover", title: "先创建实例并只跑安全发现链" },
    };
  }
  return {
    status: "ready",
    title: "推荐创建并自动推进",
    detail: `会先跑 ${safeCount} 个安全发现节点${hasRunNode ? "，门禁通过后再完整运行" : "，后续需要补 run.command 才能完整运行"}。`,
    primary: { label: "创建并自动推进", action: "create-workspace-run", title: "创建实例后交给自动推进；首次通常先跑安全发现" },
    secondary: { label: "创建并自动发现", action: "create-workspace-discover", title: "只提交安全发现链，先收集路径、数据、环境、GPU 和产物证据" },
  };
}

function workspaceStarterDecisionMarkup(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), resources = null) {
  const decision = workspaceStarterDecision(inputs, template, resources);
  const buttonMarkup = (button, tone = "secondary") => {
    if (!button?.action) return "";
    const help = workspaceAutomationActionHelp(button.action, button.title || button.label || "执行操作");
    return `<button class="${tone} mini" type="button" data-action="${escapeHtml(button.action)}" title="${escapeHtml(help)}">${escapeHtml(button.label || "操作")}</button>`;
  };
  return `
    <div class="workspace-launch-decision status-${escapeHtml(decision.status || "draft")}">
      <div>
        <span>启动决策</span>
        <strong>${escapeHtml(decision.title)}</strong>
        <em>${escapeHtml(decision.detail)}</em>
      </div>
      <div class="workspace-launch-decision-actions">
        ${buttonMarkup(decision.primary, "primary")}
        ${buttonMarkup(decision.secondary)}
      </div>
    </div>
  `;
}

function workspaceLauncherPreviewMarkup(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), resources = null) {
  const sourceMode = workspaceUseSourceMode(inputs);
  const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
  const automatedNodes = nodes.filter((node) => String(node?.handler?.mode || "human") !== "human");
  const assignedNodes = automatedNodes.filter((node) => String(node?.handler?.agent_id || "").trim()).length;
  const safeDiscoveryKinds = ["repo.clone", "path.resolve", "repo.inspect", "dataset.find", "env.infer", "gpu.allocate", "artifact.collect"];
  const safeNodes = nodes.filter((node) => safeDiscoveryKinds.includes(String(node?.kind || "")));
  const previewNodes = nodes.slice(0, 8);
  const sourceLabels = {
    repo: "仓库复现",
    paper: "论文复现",
    idea: "目标探索",
    mixed: "混合线索",
  };
  const inputFacts = [
    `${inputs.repo_urls?.length || 0} repo`,
    `${inputs.paper_urls?.length || 0} paper`,
    `${inputs.references?.length || 0} 路径/参考`,
    `${inputs.context_blocks?.length || 0} 约束`,
  ];
  return `
    <div class="workspace-launch-preview">
      <div class="workspace-launch-preview-head">
        <div>
          <span>启动包预览</span>
          <strong>${escapeHtml(sourceLabels[sourceMode] || sourceMode)} · ${escapeHtml(template?.name || "未选择 Starter Chain")}</strong>
        </div>
        <small>${escapeHtml(inputFacts.join(" · "))}</small>
      </div>
      <div class="workspace-launch-metrics">
        <article>
          <span>实例快照</span>
          <strong>${escapeHtml(nodes.length ? `${nodes.length} 节点` : "等待模板")}</strong>
          <em>${escapeHtml(`${assignedNodes}/${automatedNodes.length || 0} 自动节点已绑定 Agent`)}</em>
        </article>
        <article>
          <span>首轮安全发现</span>
          <strong>${escapeHtml(safeNodes.length ? `${safeNodes.length} 节点` : "等待链路")}</strong>
          <em>只收集路径、数据、环境、GPU、产物证据</em>
        </article>
        <article>
          <span>资源快照</span>
          <strong>${escapeHtml(resources?.title || "等待资源")}</strong>
          <em>${escapeHtml(resources?.detail || "刷新服务器后生成调度候选")}</em>
        </article>
      </div>
      ${workspaceStarterDecisionMarkup(inputs, template, resources)}
      <div class="workspace-launch-intent-chain">
        ${workspaceLaunchIntentItems(inputs, template, resources).map((item) => `
          <article class="workspace-launch-intent status-${escapeHtml(item.status)}" title="${escapeHtml(item.detail)}">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(item.value)}</strong>
            <em>${escapeHtml(item.detail)}</em>
          </article>
        `).join("")}
      </div>
      <div class="workspace-launch-node-strip">
        ${previewNodes.map((node, index) => {
          const handler = node.handler && typeof node.handler === "object" ? node.handler : {};
          const handlerName = handler.name || globalAgentById(handler.agent_id || "")?.name || (handler.mode === "human" ? "你" : "未指派");
          const status = String(handler.mode || "human") !== "human" && !String(handler.agent_id || "").trim() ? "blocked" : "ready";
          return `
            <article class="workspace-launch-node status-${escapeHtml(status)}">
              <span>${escapeHtml(`${index + 1}. ${workspaceStarterNodePhase(node.kind)}`)}</span>
              <strong>${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</strong>
              <em>${escapeHtml(handlerName)}</em>
            </article>
          `;
        }).join("") || '<div class="empty">选择 Starter Chain 后预览节点。</div>'}
      </div>
    </div>
  `;
}

function workspaceResourceSnapshotMeta(candidates = {}) {
  const recommendedServerId = String(candidates.recommended_server_id || "").trim();
  const recommended = recommendedServerId
    ? state.servers.find((server) => String(server?.id || "") === recommendedServerId)
    : null;
  const snapshots = state.servers
    .map((server) => ({
      server,
      ms: statusTimestampMs(server?.collected_at),
      collectedAt: String(server?.collected_at || ""),
    }))
    .filter((item) => item.ms > 0)
    .sort((left, right) => right.ms - left.ms);
  const selected = recommended && statusTimestampMs(recommended.collected_at)
    ? {
        server: recommended,
        ms: statusTimestampMs(recommended.collected_at),
        collectedAt: String(recommended.collected_at || ""),
      }
    : snapshots[0] || null;
  const recommendedBusy = Boolean(recommendedServerId && state.ui.serverRefreshBusy[recommendedServerId]);
  const globalBusy = Boolean(state.ui.workspaceResourceRefreshBusy);
  if (globalBusy || recommendedBusy) {
    return {
      status: "running",
      title: globalBusy ? "全局刷新中" : "单机刷新中",
      detail: recommendedBusy ? `${recommendedServerId} 正在刷新 GPU 快照` : "正在刷新服务器、GPU、任务和资源快照",
    };
  }
  if (!selected) {
    return {
      status: "draft",
      title: "等待快照",
      detail: "点击刷新资源后生成服务器/GPU 采集时间",
    };
  }
  const ageSeconds = Math.max(Math.round((Date.now() - selected.ms) / 1000), 0);
  const staleThreshold = Math.max(60, Math.round(Number(state.ui.pollIntervalMs || 5000) / 1000) * 3);
  const serverName = selected.server?.name || selected.server?.id || "服务器";
  return {
    status: ageSeconds > staleThreshold ? "warning" : "ready",
    title: fmtDate(selected.collectedAt) || "刚更新",
    detail: `${serverName} · ${ageSeconds} 秒前${ageSeconds > staleThreshold ? " · 可能过期" : ""}`,
  };
}

function workspaceResourceServerOptions(candidates = {}) {
  const recommendedServerId = String(candidates.recommended_server_id || "").trim();
  const servers = state.servers.slice();
  if (recommendedServerId) {
    servers.sort((left, right) => {
      if (String(left?.id || "") === recommendedServerId) return -1;
      if (String(right?.id || "") === recommendedServerId) return 1;
      return String(left?.name || left?.id || "").localeCompare(String(right?.name || right?.id || ""));
    });
  }
  return servers;
}

function workspaceSelectedResourceServerId(candidates = {}) {
  const servers = workspaceResourceServerOptions(candidates);
  const known = new Set(servers.map((server) => String(server?.id || "")).filter(Boolean));
  const candidatesInOrder = [
    state.ui.workspaceResourceServerId,
    candidates.recommended_server_id,
    state.selectedServer,
    servers[0]?.id,
  ].map((value) => String(value || "").trim());
  return candidatesInOrder.find((value) => value && known.has(value)) || "";
}

function workspaceCockpitResourceMatrixMarkup(workspace = selectedWorkspace(), { limit = 6 } = {}) {
  const resource = workspace?.automation?.resource_orchestration && typeof workspace.automation.resource_orchestration === "object"
    ? workspace.automation.resource_orchestration
    : null;
  if (!workspace?.id || !resource) return "";
  const items = Array.isArray(resource.items) ? resource.items.slice(0, limit) : [];
  const candidates = resource.resource_candidates && typeof resource.resource_candidates === "object" ? resource.resource_candidates : {};
  const next = resource.next_action && typeof resource.next_action === "object" ? resource.next_action : {};
  const recommendedServerId = String(candidates.recommended_server_id || "").trim();
  const recommendedServerBusy = Boolean(recommendedServerId && state.ui.serverRefreshBusy[recommendedServerId]);
  const serverOptions = workspaceResourceServerOptions(candidates);
  const selectedResourceServerId = workspaceSelectedResourceServerId(candidates);
  const selectedResourceServerBusy = Boolean(selectedResourceServerId && state.ui.serverRefreshBusy[selectedResourceServerId]);
  const resourceRefreshBusy = Boolean(state.ui.workspaceResourceRefreshBusy);
  const snapshot = workspaceResourceSnapshotMeta(candidates);
  const globalRefreshHelp = "刷新全部服务器、GPU、任务和工作台资源快照；异步返回后保留当前工作台选项卡和草稿。";
  const pickerHelp = "选择要单独刷新 GPU 快照的服务器；只更新这台服务器，不会重置工作台选项卡。";
  const selectedRefreshHelp = "只刷新下拉选择的单台服务器 GPU、显存、进程和连接状态；不会重置工作台。";
  const recommendedRefreshHelp = recommendedServerId
    ? `只刷新推荐服务器 ${recommendedServerId} 的 GPU、显存、进程和连接状态；不会重置工作台。`
    : "";
  return `
    <div class="workspace-cockpit-resource-matrix status-${escapeHtml(resource.status || "draft")}">
      <div class="workspace-cockpit-resource-head">
        <div>
          <span>资源 / 数据 / 环境 / GPU 调度矩阵</span>
          <strong>${escapeHtml(resource.summary || "等待调度分析")}</strong>
        </div>
        <div class="workspace-cockpit-resource-actions">
          <small>${escapeHtml(next.action || "路径、数据、环境、GPU、运行入口和产物在这里收口")}</small>
          <div>
            <button class="secondary mini" type="button" data-action="refresh-workspace-resources" title="${escapeHtml(globalRefreshHelp)}" aria-label="${escapeHtml(`刷新资源：${globalRefreshHelp}`)}" data-workspace-help="${escapeHtml(globalRefreshHelp)}" ${resourceRefreshBusy ? "disabled" : ""}>${resourceRefreshBusy ? "刷新中..." : "刷新资源"}</button>
            <label class="workspace-resource-server-picker" title="${escapeHtml(pickerHelp)}" aria-label="${escapeHtml(pickerHelp)}" data-workspace-help="${escapeHtml(pickerHelp)}">
              <span>单机</span>
              <select data-role="workspace-resource-server-select" title="${escapeHtml(pickerHelp)}" ${serverOptions.length ? "" : "disabled"}>
                ${serverOptions.map((server) => `<option value="${escapeHtml(server.id)}" ${server.id === selectedResourceServerId ? "selected" : ""}>${escapeHtml(server.name || server.id)}</option>`).join("")}
              </select>
            </label>
            <button class="secondary mini" type="button" data-action="refresh-workspace-resource-selected-server" title="${escapeHtml(selectedRefreshHelp)}" aria-label="${escapeHtml(`刷新单机：${selectedRefreshHelp}`)}" data-workspace-help="${escapeHtml(selectedRefreshHelp)}" ${!selectedResourceServerId || selectedResourceServerBusy ? "disabled" : ""}>${selectedResourceServerBusy ? "单机刷新中..." : "刷新单机"}</button>
            ${recommendedServerId ? `<button class="secondary mini" type="button" data-action="refresh-workspace-resource-server" data-server-id="${escapeHtml(recommendedServerId)}" title="${escapeHtml(recommendedRefreshHelp)}" aria-label="${escapeHtml(`刷新推荐服务器：${recommendedRefreshHelp}`)}" data-workspace-help="${escapeHtml(recommendedRefreshHelp)}" ${recommendedServerBusy ? "disabled" : ""}>${recommendedServerBusy ? "单机刷新中..." : "刷新推荐服务器"}</button>` : ""}
          </div>
        </div>
      </div>
      <div class="workspace-cockpit-resource-candidates">
        <article>
          <span>在线服务器</span>
          <strong>${escapeHtml(String(candidates.online_server_count || 0))}</strong>
        </article>
        <article>
          <span>空闲 GPU</span>
          <strong>${escapeHtml(`${Number(candidates.idle_gpu_count || 0)}/${Number(candidates.gpu_count || 0)}`)}</strong>
        </article>
        <article>
          <span>推荐资源</span>
          <strong>${escapeHtml(candidates.recommended_server_id ? `${candidates.recommended_server_id} · GPU ${candidates.recommended_gpu_index || "auto"}` : "等待快照")}</strong>
        </article>
        <article class="status-${escapeHtml(snapshot.status)}">
          <span>快照状态</span>
          <strong>${escapeHtml(snapshot.title)}</strong>
          <em title="${escapeHtml(snapshot.detail)}">${escapeHtml(snapshot.detail)}</em>
        </article>
      </div>
      <div class="workspace-cockpit-resource-items">
        ${items.map((item) => `
          <article class="workspace-cockpit-resource-item status-${escapeHtml(item.status || "draft")}">
            <span>${escapeHtml(item.label || item.id || "调度项")}</span>
            <strong>${escapeHtml(item.title || workspaceStatusLabel(item.status || "draft"))}</strong>
            <em title="${escapeHtml(item.value || item.detail || "")}">${escapeHtml(item.value || item.detail || "等待")}</em>
            <small title="${escapeHtml(item.action || "")}">${escapeHtml(item.action || item.detail || "")}</small>
          </article>
        `).join("") || '<div class="empty">还没有调度条目。</div>'}
      </div>
    </div>
  `;
}

function workspaceCockpitOperationsMarkup(workspace = selectedWorkspace(), inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), next = null, resources = null) {
  const automation = workspaceAutomationSummary(workspace);
  if (!workspace?.id) {
    const hasInput = Boolean(
      String(inputs.goal_text || "").trim()
      || (Array.isArray(inputs.repo_urls) && inputs.repo_urls.length)
      || (Array.isArray(inputs.paper_urls) && inputs.paper_urls.length)
      || (Array.isArray(inputs.references) && inputs.references.length)
      || (Array.isArray(inputs.context_blocks) && inputs.context_blocks.length)
    );
    const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
    const automatedNodes = nodes.filter((node) => String(node?.handler?.mode || "human") !== "human");
    const assignedNodes = automatedNodes.filter((node) => String(node?.handler?.agent_id || "").trim()).length;
    const templateReady = Boolean(nodes.length && assignedNodes === automatedNodes.length);
    const actions = [
      { label: "创建并自动推进", action: "create-workspace-run", tone: "primary", title: "创建实例后交给自动推进；首次通常先跑安全发现" },
      { label: "创建并自动发现", action: "create-workspace-discover", title: "创建实例后只提交安全发现链，先收集路径、数据、环境、GPU 和产物证据" },
      { label: "配置中心", action: "switch-workspace-manage", title: "维护 Starter Chain、Agent、工具和 AI 路由" },
    ];
    const checks = [
      { label: "目标输入", value: hasInput ? workspaceUseInputSummary(inputs) : "等待目标、repo、论文、数据或约束", status: hasInput ? "ready" : "draft" },
      { label: "模板链路", value: nodes.length ? `${nodes.length} 节点 · ${assignedNodes}/${automatedNodes.length || 0} 自动节点已绑定 Agent` : "未选择模板", status: templateReady ? "ready" : "warning" },
      { label: "资源快照", value: resources?.detail || "等待服务器/GPU 快照", status: resources?.state || "draft" },
    ];
    return `
      <div class="workspace-cockpit-action-rail status-${escapeHtml(hasInput && templateReady ? "ready" : "draft")}">
        <div class="workspace-cockpit-action-main">
          <span>启动动作</span>
          <strong>${escapeHtml(next?.title || "准备创建自动化实例")}</strong>
          <p>${escapeHtml(next?.detail || "输入目标后创建实例，系统会先跑安全发现，再根据门禁决定是否完整运行。")}</p>
        </div>
        <div class="workspace-cockpit-action-buttons">
          ${actions.map(workspaceCockpitActionButton).join("")}
        </div>
        <div class="workspace-cockpit-mini-grid">
          ${checks.map((item) => `
            <article class="workspace-cockpit-mini-card status-${escapeHtml(item.status)}">
              <span>${escapeHtml(item.label)}</span>
              <strong title="${escapeHtml(item.value)}">${escapeHtml(item.value)}</strong>
            </article>
          `).join("")}
        </div>
        ${workspaceLauncherPreviewMarkup(inputs, template, resources)}
      </div>
    `;
  }

  const readiness = automation?.executionReadiness || {};
  const gate = readiness.gate && typeof readiness.gate === "object" ? readiness.gate : {};
  const nextAction = readiness.next_action && typeof readiness.next_action === "object"
    ? readiness.next_action
    : automation?.advance || {};
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  const warnings = Array.isArray(readiness.warnings) ? readiness.warnings : [];
  const evidenceItems = workspaceEvidenceSummaryItems(workspace);
  const evidenceTotal = evidenceItems.reduce((sum, item) => sum + Number(item.count || 0), 0);
  const jobState = readiness.job_state && typeof readiness.job_state === "object" ? readiness.job_state : {};
  const lastJobId = String(jobState.last_job_id || "").trim();
  const actions = [
    { label: "自动推进", action: "advance-workspace-automation", tone: "primary", title: "根据当前门禁自动决定发现、观察、复查失败、回填或完整运行" },
    { label: "自动发现", action: "run-workspace-discovery", title: "只运行安全发现链，收集源码、路径、数据、环境、GPU 和产物证据" },
    { label: "回填证据", action: "apply-workspace-automation", title: "把建议和发现证据回填到节点配置" },
    { label: "运行工作流", action: "run-selected-workspace", title: "门禁通过后提交完整工作流；门禁失败时不会创建半截队列" },
  ];
  if (lastJobId) {
    actions.push({ label: "打开最近输出", action: "open-last-workspace-log", title: "打开当前实例最近绑定任务的日志输出" });
  }
  const issueItems = blockers.length ? blockers : warnings;
  const issueLabel = blockers.length ? "阻塞项" : warnings.length ? "提示项" : "没有阻塞";
  return `
    <div class="workspace-cockpit-action-rail status-${escapeHtml(readiness.status || automation?.status || "draft")}">
      <div class="workspace-cockpit-action-main">
        <span>${escapeHtml(issueLabel)}</span>
        <strong>${escapeHtml(nextAction.title || gate.title || "等待自动推进判断")}</strong>
        <p>${escapeHtml(nextAction.reason || nextAction.next_action || gate.detail || "系统会按发现、回填、门禁、完整运行和报告回收顺序推进。")}</p>
      </div>
      <div class="workspace-cockpit-action-buttons">
        ${actions.map(workspaceCockpitActionButton).join("")}
      </div>
      <div class="workspace-cockpit-mini-grid">
        <article class="workspace-cockpit-mini-card status-${escapeHtml(gate.status || "draft")}">
          <span>运行门禁</span>
          <strong title="${escapeHtml(gate.detail || "")}">${escapeHtml(gate.title || workspaceStatusLabel(gate.status || "draft"))}</strong>
        </article>
        <article class="workspace-cockpit-mini-card status-${escapeHtml(evidenceTotal ? "ready" : "draft")}">
          <span>发现证据</span>
          <strong>${escapeHtml(`${evidenceTotal} 条`)}</strong>
        </article>
        <article class="workspace-cockpit-mini-card status-${escapeHtml(jobState.active_count ? "running" : jobState.failed_count ? "failed" : "ready")}">
          <span>任务状态</span>
          <strong>${escapeHtml(`${Number(jobState.active_count || 0)} 活跃 · ${Number(jobState.failed_count || 0)} 失败`)}</strong>
        </article>
      </div>
      <div class="workspace-cockpit-evidence-strip">
        ${evidenceItems.map((item) => `
          <span class="status-${escapeHtml(item.status)}" title="${escapeHtml(item.detail)}">${escapeHtml(item.label)} ${escapeHtml(String(item.count || 0))}</span>
        `).join("") || '<span class="status-draft">等待发现证据</span>'}
      </div>
      ${issueItems.length ? `
        <div class="workspace-cockpit-issue-list">
          ${issueItems.slice(0, 4).map((item) => workspaceCockpitIssueMarkup(item, blockers.length ? "blocked" : "warning")).join("")}
        </div>
      ` : ""}
      ${workspaceCockpitNodeRadarMarkup(workspace)}
      ${workspaceCockpitHandoffMapMarkup(workspace)}
      ${workspaceReproductionManifestMarkup(workspace, { compact: true, limit: 8 })}
      ${workspaceExecutionContextBusMarkup(workspace, { compact: true, limit: 5 })}
      ${workspaceCockpitTopologyMarkup(workspace)}
      ${workspaceCockpitResourceMatrixMarkup(workspace)}
      ${workspaceEvidenceBackfillMarkup(workspace, { compact: true, limit: 6 })}
    </div>
  `;
}

function workspaceCockpitStarterReadinessMarkup(inputs = workspaceUseInputsPayload(), template = selectedWorkflowTemplate(), next = null, resources = null) {
  const hasInput = Boolean(
    String(inputs.goal_text || "").trim()
    || (Array.isArray(inputs.repo_urls) && inputs.repo_urls.length)
    || (Array.isArray(inputs.paper_urls) && inputs.paper_urls.length)
    || (Array.isArray(inputs.references) && inputs.references.length)
    || (Array.isArray(inputs.context_blocks) && inputs.context_blocks.length)
  );
  const nodes = Array.isArray(template?.nodes) ? template.nodes : [];
  const automatedNodes = nodes.filter((node) => String(node?.handler?.mode || "human") !== "human");
  const assignedNodes = automatedNodes.filter((node) => String(node?.handler?.agent_id || "").trim()).length;
  const templateReady = Boolean(nodes.length && assignedNodes === automatedNodes.length);
  const resourceState = resources?.state || "draft";
  const createReady = hasInput && templateReady;
  const status = createReady
    ? resourceState === "blocked" || resourceState === "failed"
      ? "warning"
      : "ready"
    : hasInput || nodes.length
      ? "warning"
      : "draft";
  const steps = [
    {
      id: "starter_input",
      label: "目标输入",
      status: hasInput ? "ready" : "draft",
      title: hasInput ? "输入已可建档" : "等待目标线索",
      detail: workspaceUseInputSummary(inputs),
      action: "填写目标、仓库、论文、数据路径或成功标准。",
    },
    {
      id: "starter_chain",
      label: "Starter Chain",
      status: templateReady ? "ready" : nodes.length ? "blocked" : "draft",
      title: nodes.length ? `${nodes.length} 个节点` : "未选择链路模板",
      detail: `${assignedNodes}/${automatedNodes.length || 0} 个自动节点已绑定 Agent`,
      action: "在配置中心补齐节点、Agent、工具和模型路由。",
    },
    {
      id: "resource_snapshot",
      label: "资源快照",
      status: resourceState,
      title: resources?.title || "等待资源快照",
      detail: resources?.detail || "创建实例后会结合 GPU、路径和任务配置调度。",
      action: "先确认服务器监控和 GPU 状态可用。",
    },
    {
      id: "create_instance",
      label: "创建实例",
      status: createReady ? "ready" : "draft",
      title: createReady ? "可以创建任务实例" : "创建前信息不足",
      detail: template?.name || "选择模板后会复制成独立实例快照。",
      action: createReady ? "点击创建并自动发现，先跑安全发现链。" : "补齐输入和模板链路后再创建实例。",
    },
    {
      id: "safe_discovery",
      label: "安全发现",
      status: "draft",
      title: "创建后提交发现链",
      detail: "repo.clone、path.resolve、repo.inspect、dataset.find、env.infer、gpu.allocate、artifact.collect。",
      action: "发现链只收集证据，不直接提交完整训练/部署命令。",
    },
  ];
  const readyCount = steps.filter((step) => ["ready", "done"].includes(String(step.status || ""))).length;
  const blockerCount = steps.filter((step) => ["blocked", "failed"].includes(String(step.status || ""))).length;
  return `
    <div class="workspace-readiness status-${escapeHtml(status)}">
      <div class="workspace-readiness-head">
        <div>
          <span>启动器预检</span>
          <strong>${escapeHtml(`${readyCount}/${steps.length} 项准备完成 · ${blockerCount} 阻塞`)}</strong>
        </div>
        <small>${escapeHtml(next?.title || "等待创建实例")}</small>
      </div>
      <div class="workspace-readiness-gate status-${escapeHtml(createReady ? "ready" : blockerCount ? "blocked" : "draft")}">
        <div>
          <span>创建门禁</span>
          <strong>${escapeHtml(createReady ? "可以创建自动化实例" : "还不能稳定启动")}</strong>
          <em>${escapeHtml(createReady ? "目标输入和 Starter Chain 已具备，创建后可先跑安全发现。" : "先补目标输入、节点链和 Agent 归属。")}</em>
        </div>
        <small>${escapeHtml(createReady ? "推荐使用“创建并自动推进”；首次会先跑安全发现。" : "输入越明确，后面的路径/数据/环境推断越稳。")}</small>
      </div>
      <div class="workspace-readiness-steps">
        ${steps.map((step, index) => `
          <article class="workspace-readiness-step status-${escapeHtml(step.status || "draft")}">
            <span>${escapeHtml(String(index + 1))}</span>
            <div>
              <strong>${escapeHtml(step.label)}</strong>
              <em>${escapeHtml(step.title)}</em>
              <small>${escapeHtml(step.detail || step.action || "")}</small>
            </div>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function workspaceAutomationEvidenceMarkup(workspace = selectedWorkspace()) {
  const evidence = Array.isArray(workspace?.automation?.evidence) ? workspace.automation.evidence : [];
  if (!evidence.length) return '<div class="empty">还没有自动发现证据。</div>';
  return `
    <div class="workspace-evidence-grid">
      ${evidence.map((group) => {
        const items = Array.isArray(group.items) ? group.items.slice(0, 3) : [];
        const count = Number(group.count || items.length || 0);
        const status = count ? "ready" : "draft";
        return `
          <article class="workspace-evidence-card status-${escapeHtml(status)}">
            <div class="workspace-evidence-card-head">
              <span>${escapeHtml(group.label || group.id || "证据")}</span>
              <strong>${escapeHtml(String(count))}</strong>
            </div>
            ${items.length ? `
              <div class="workspace-evidence-items">
                ${items.map((item) => `
                  <div class="workspace-evidence-item">
                    <span>${escapeHtml(item.label || item.node_kind || "发现")}</span>
                    <strong>${escapeHtml(item.value || "")}</strong>
                  </div>
                `).join("")}
              </div>
            ` : `<p>${escapeHtml(group.detail || "等待自动发现")}</p>`}
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function workspaceAutomationResourceMarkup(workspace = selectedWorkspace(), { limit = 6 } = {}) {
  const resource = workspace?.automation?.resource_orchestration && typeof workspace.automation.resource_orchestration === "object"
    ? workspace.automation.resource_orchestration
    : null;
  if (!resource) return '<div class="empty">还没有资源调度总览。</div>';
  const items = Array.isArray(resource.items) ? resource.items.slice(0, limit) : [];
  const candidates = resource.resource_candidates && typeof resource.resource_candidates === "object" ? resource.resource_candidates : {};
  const next = resource.next_action && typeof resource.next_action === "object" ? resource.next_action : null;
  return `
    <div class="workspace-resource-plan status-${escapeHtml(resource.status || "draft")}">
      <div class="workspace-resource-head">
        <strong>${escapeHtml(resource.summary || "等待资源调度")}</strong>
        <span>${escapeHtml(next?.action || "路径、数据、环境、GPU、运行入口和产物会在这里收口。")}</span>
      </div>
      <div class="workspace-resource-candidates">
        <article>
          <span>在线服务器</span>
          <strong>${escapeHtml(String(candidates.online_server_count || 0))}</strong>
        </article>
        <article>
          <span>空闲 GPU</span>
          <strong>${escapeHtml(`${Number(candidates.idle_gpu_count || 0)}/${Number(candidates.gpu_count || 0)}`)}</strong>
        </article>
        <article>
          <span>推荐资源</span>
          <strong>${escapeHtml(candidates.recommended_server_id ? `${candidates.recommended_server_id} · GPU ${candidates.recommended_gpu_index || "auto"}` : "等待快照")}</strong>
        </article>
      </div>
      <div class="workspace-resource-list">
        ${items.map((item) => `
          <article class="workspace-resource-item status-${escapeHtml(item.status || "warning")}">
            <div>
              <span>${escapeHtml(item.label || item.id || "资源")}</span>
              <strong>${escapeHtml(item.title || workspaceStatusLabel(item.status || "warning"))}</strong>
              <em title="${escapeHtml(item.value || "")}">${escapeHtml(item.value || "等待")}</em>
            </div>
            <small>${escapeHtml(item.detail || item.action || "")}</small>
          </article>
        `).join("") || '<div class="empty">还没有资源条目。</div>'}
      </div>
    </div>
  `;
}

function workspaceAutomationRunPlanMarkup(workspace = selectedWorkspace()) {
  const plan = workspace?.automation?.run_plan && typeof workspace.automation.run_plan === "object"
    ? workspace.automation.run_plan
    : null;
  if (!plan) return '<div class="empty">还没有完整运行预案。</div>';
  const phases = Array.isArray(plan.phases) ? plan.phases : [];
  const nodes = Array.isArray(plan.nodes) ? plan.nodes.slice(0, 8) : [];
  const blocking = Array.isArray(plan.blocking) ? plan.blocking : [];
  const warnings = Array.isArray(plan.warnings) ? plan.warnings : [];
  return `
    <div class="workspace-run-plan">
      <div class="workspace-run-plan-summary status-${escapeHtml(plan.status || "draft")}">
        <strong>${escapeHtml(plan.summary || "等待生成运行预案")}</strong>
        <span>${escapeHtml(blocking.length ? "完整运行前需要处理阻塞项" : "完整运行预案已就绪")}</span>
      </div>
      ${phases.length ? `
        <div class="workspace-run-plan-phases">
          ${phases.map((phase) => `
            <span>${escapeHtml(phase.label || phase.id)} · ${escapeHtml(String(phase.count || 0))}</span>
          `).join("")}
        </div>
      ` : ""}
      ${blocking.length ? `
        <div class="workspace-run-plan-blockers">
          ${blocking.slice(0, 4).map((item) => `
            <article>
              <strong>${escapeHtml(item.label || item.title || item.node_kind || "阻塞项")}</strong>
              <span>${escapeHtml(item.detail || item.action || "")}</span>
            </article>
          `).join("")}
        </div>
      ` : ""}
      ${warnings.length ? `
        <div class="workspace-run-plan-warnings">
          ${warnings.slice(0, 4).map((item) => `
            <article>
              <strong>${escapeHtml(item.label || item.title || item.node_kind || "提示项")}</strong>
              <span>${escapeHtml(item.detail || item.action || "")}</span>
            </article>
          `).join("")}
        </div>
      ` : ""}
      ${nodes.length ? `
        <div class="workspace-run-plan-node-list">
          ${nodes.map((item) => `
            <article class="workspace-run-plan-node status-${escapeHtml(item.status || "warning")}">
              <span>${escapeHtml(String(item.index || ""))}</span>
              <div>
                <strong>${escapeHtml(item.title || item.kind || "节点")}</strong>
                <em>${escapeHtml(item.phase_label || item.phase || "阶段")} · ${escapeHtml(item.agent_name || item.agent_id || "未指派 Agent")}</em>
                <p>${escapeHtml(item.summary || "")}</p>
              </div>
            </article>
          `).join("")}
        </div>
      ` : '<div class="empty">还没有可执行节点。</div>'}
    </div>
  `;
}

function workspaceTopologyLayerValue(layer = {}) {
  const label = String(layer.label || "").toLowerCase();
  if (label === "agent") return `${Number(layer.assigned_count || 0)}/${Number(layer.enabled_count || 0)}`;
  if (label === "tool") return `${Number(layer.required_count || 0)}/${Number(layer.enabled_count || 0)}`;
  if (label === "ai") return layer.effective_profile_count ? `${Number(layer.effective_profile_count || 0)} profile` : "未配置";
  return String(layer.value || layer.status || "draft");
}

function workspaceTopologyLayerDetail(layer = {}) {
  const label = String(layer.label || "").toLowerCase();
  if (label === "agent") return `${Number(layer.missing_count || 0)} 个节点缺 Agent`;
  if (label === "tool") return `${Number(layer.gap_count || 0)} 个工具缺口`;
  if (label === "ai") return `${layer.routing_mode || "workspace_default"} · ${layer.workspace_profile_id || "无默认 Profile"}`;
  return String(layer.detail || layer.status || "");
}

function workspaceCockpitTopologyMarkup(workspace = selectedWorkspace(), { limit = 4 } = {}) {
  const topology = workspace?.automation?.agent_topology && typeof workspace.automation.agent_topology === "object"
    ? workspace.automation.agent_topology
    : null;
  if (!workspace?.id || !topology) return "";
  const layers = topology.layers && typeof topology.layers === "object" ? topology.layers : {};
  const layerItems = ["agent", "tool", "ai"].map((key) => layers[key]).filter(Boolean);
  const stages = Array.isArray(topology.stages) ? topology.stages.slice(0, limit) : [];
  const gaps = Array.isArray(topology.gaps) ? topology.gaps : [];
  return `
    <div class="workspace-cockpit-topology status-${escapeHtml(topology.status || "draft")}">
      <div class="workspace-cockpit-topology-head">
        <div>
          <span>Agent / Tool / AI 分层编排</span>
          <strong>${escapeHtml(topology.summary || "等待拓扑分析")}</strong>
        </div>
        <small>${escapeHtml(gaps.length ? `${gaps.length} 个缺口需要处理` : "角色、工具和模型路由已形成闭环")}</small>
      </div>
      <div class="workspace-cockpit-topology-layers">
        ${layerItems.map((layer) => `
          <article class="workspace-cockpit-topology-layer status-${escapeHtml(layer.status || "draft")}">
            <span>${escapeHtml(layer.label || "Layer")}</span>
            <strong>${escapeHtml(workspaceTopologyLayerValue(layer))}</strong>
            <em>${escapeHtml(workspaceTopologyLayerDetail(layer))}</em>
          </article>
        `).join("")}
      </div>
      <div class="workspace-cockpit-topology-stages">
        ${stages.map((stage) => {
          const agents = Array.isArray(stage.agents) ? stage.agents : [];
          const tools = Array.isArray(stage.tools) ? stage.tools : [];
          const profiles = Array.isArray(stage.model_profiles) ? stage.model_profiles : [];
          const stageGaps = Array.isArray(stage.gaps) ? stage.gaps : [];
          const agentNames = agents.map((agent) => agent.name || agent.id).filter(Boolean).join(" / ");
          const toolNames = tools.map((tool) => tool.label || tool.id).filter(Boolean).slice(0, 3).join(" / ");
          return `
            <article class="workspace-cockpit-topology-stage status-${escapeHtml(stage.status || "draft")}">
              <div>
                <span>${escapeHtml(stage.label || stage.id || "阶段")}</span>
                <strong>${escapeHtml(agentNames || "未指派 Agent")}</strong>
                <em>${escapeHtml(`${Number(stage.node_count || 0)} 节点 · ${Number(stage.assigned_node_count || 0)} 已绑定`)}</em>
              </div>
              <small title="${escapeHtml(toolNames || "无关键工具")}">${escapeHtml(toolNames || "无关键工具")}</small>
              <small title="${escapeHtml(profiles.join(" / ") || "AI profile 未配置")}">${escapeHtml(profiles.length ? profiles.join(" / ") : "AI profile 未配置")}</small>
              ${stageGaps.length ? `<p>${escapeHtml(stageGaps[0].title || stageGaps[0].type || "有缺口")}</p>` : ""}
            </article>
          `;
        }).join("") || '<div class="empty">还没有阶段拓扑。</div>'}
      </div>
    </div>
  `;
}

function workspaceAutomationAgentTopologyMarkup(workspace = selectedWorkspace(), { limit = 6 } = {}) {
  const topology = workspace?.automation?.agent_topology && typeof workspace.automation.agent_topology === "object"
    ? workspace.automation.agent_topology
    : null;
  if (!topology) return '<div class="empty">还没有 Agent / Tool / AI 拓扑。</div>';
  const layers = topology.layers && typeof topology.layers === "object" ? topology.layers : {};
  const layerItems = ["agent", "tool", "ai"].map((key) => layers[key]).filter(Boolean);
  const stages = Array.isArray(topology.stages) ? topology.stages.slice(0, limit) : [];
  const gaps = Array.isArray(topology.gaps) ? topology.gaps.slice(0, 4) : [];
  return `
    <div class="workspace-topology status-${escapeHtml(topology.status || "draft")}">
      <div class="workspace-topology-head">
        <strong>${escapeHtml(topology.summary || "等待拓扑分析")}</strong>
        <span>${escapeHtml(gaps.length ? "先处理阻塞和模型/工具缺口" : "节点、角色和关键工具已形成闭环")}</span>
      </div>
      ${layerItems.length ? `
        <div class="workspace-topology-layers">
          ${layerItems.map((layer) => `
            <article class="workspace-topology-layer status-${escapeHtml(layer.status || "draft")}">
              <span>${escapeHtml(layer.label || "Layer")}</span>
              <strong>${escapeHtml(workspaceTopologyLayerValue(layer))}</strong>
              <em>${escapeHtml(
                layer.label === "AI"
                  ? `${layer.routing_mode || "workspace_default"} · ${layer.workspace_profile_id || "无默认 Profile"}`
                  : layer.label === "Tool"
                    ? `${Number(layer.gap_count || 0)} 个工具缺口`
                    : `${Number(layer.missing_count || 0)} 个节点缺 Agent`
              )}</em>
            </article>
          `).join("")}
        </div>
      ` : ""}
      ${gaps.length ? `
        <div class="workspace-topology-gaps">
          ${gaps.map((gap) => `
            <article class="workspace-topology-gap status-${escapeHtml(gap.status || "warning")}">
              <strong>${escapeHtml(gap.title || gap.type || "缺口")}</strong>
              <span>${escapeHtml(gap.detail || gap.action || "")}</span>
              ${gap.action ? `<em>${escapeHtml(gap.action)}</em>` : ""}
            </article>
          `).join("")}
        </div>
      ` : ""}
      <div class="workspace-topology-stage-list">
        ${stages.map((stage) => {
          const agents = Array.isArray(stage.agents) ? stage.agents : [];
          const tools = Array.isArray(stage.tools) ? stage.tools : [];
          const profiles = Array.isArray(stage.model_profiles) ? stage.model_profiles : [];
          const stageGaps = Array.isArray(stage.gaps) ? stage.gaps : [];
          return `
            <article class="workspace-topology-stage status-${escapeHtml(stage.status || "draft")}">
              <div class="workspace-topology-stage-main">
                <span>${escapeHtml(stage.label || stage.id || "阶段")}</span>
                <strong>${escapeHtml(agents.map((agent) => agent.name || agent.id).join(" / ") || "未指派 Agent")}</strong>
                <em>${escapeHtml(`${Number(stage.node_count || 0)} 节点 · ${Number(stage.assigned_node_count || 0)} 已绑定`)}</em>
              </div>
              <div class="workspace-topology-stage-side">
                <span>${escapeHtml(tools.map((tool) => tool.label || tool.id).slice(0, 3).join(" / ") || "无关键工具")}</span>
                <em>${escapeHtml(profiles.length ? profiles.join(" / ") : "AI profile 未配置")}</em>
                ${stageGaps.length ? `<small>${escapeHtml(stageGaps[0].title || stageGaps[0].type || "有缺口")}</small>` : ""}
              </div>
            </article>
          `;
        }).join("") || '<div class="empty">还没有可执行阶段。</div>'}
      </div>
    </div>
  `;
}

function workspaceAutomationReportMarkup(workspace = selectedWorkspace()) {
  const report = workspace?.automation?.report && typeof workspace.automation.report === "object"
    ? workspace.automation.report
    : null;
  if (!report) return '<div class="empty">还没有报告草稿。</div>';
  const highlights = Array.isArray(report.highlights) ? report.highlights : [];
  const actions = Array.isArray(report.next_actions) ? report.next_actions : [];
  return `
    <div class="workspace-report-draft status-${escapeHtml(report.status || "draft")}">
      <div class="workspace-report-draft-head">
        <span>${escapeHtml(report.title || "复现/部署报告草稿")}</span>
        <strong>${escapeHtml(report.headline || "等待证据")}</strong>
        <em>${escapeHtml(report.summary || "")}</em>
      </div>
      ${highlights.length ? `
        <div class="workspace-report-highlight-grid">
          ${highlights.slice(0, 5).map((item) => `
            <article class="workspace-report-highlight status-${escapeHtml(item.status || "draft")}">
              <span>${escapeHtml(item.label || "摘要")}</span>
              <strong>${escapeHtml(item.value || "")}</strong>
              <em>${escapeHtml(item.detail || "")}</em>
            </article>
          `).join("")}
        </div>
      ` : ""}
      ${actions.length ? `
        <div class="workspace-report-next-list">
          ${actions.slice(0, 4).map((item) => `
            <article class="workspace-report-next status-${escapeHtml(item.status || "ready")}">
              <strong>${escapeHtml(item.label || "下一步")}</strong>
              <span>${escapeHtml(item.detail || "")}</span>
              <em>${escapeHtml(item.action || "")}</em>
            </article>
          `).join("")}
        </div>
      ` : ""}
    </div>
  `;
}

function renderWorkspaceCockpitOverview() {
  const root = $("workspaceCockpitCards");
  const readinessRoot = $("workspaceCockpitReadiness");
  const operationsRoot = $("workspaceCockpitOperations");
  if (!root) return;
  const inputs = workspaceUseInputsPayload();
  const template = selectedWorkflowTemplate();
  const workspace = selectedWorkspace();
  const automation = workspaceAutomationSummary(workspace);
  const next = workspaceUseNextAction(inputs, template, workspace);
  const resources = workspaceUseResourceSummary();
  const jobs = workspace ? workspaceJobs() : [];
  const activeJobs = jobs.filter((job) => isJobActive(job)).length;
  const doneJobs = jobs.filter((job) => String(job.status || "") === "done").length;
  const failedJobs = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  const templateNodes = Array.isArray(template?.nodes) ? template.nodes.length : template?.node_count || 0;
  const topology = automation?.agentTopology || null;
  const resourcePlan = automation?.resourcePlan || null;
  const cards = automation ? [
    {
      label: "自动化体检",
      title: `${automation.score}% ready`,
      detail: automation.summary,
      state: automation.status,
    },
    {
      label: "自动推进",
      title: automation.advance?.title || automation.next?.title || next.title,
      detail: automation.advance?.reason || automation.next?.action || next.detail,
      state: automation.advance?.status || automation.next?.status || next.state,
    },
    {
      label: "资源调度",
      title: resourcePlan ? resourcePlan.summary.split(" · ")[0] : resources.title,
      detail: resourcePlan?.next_action?.action || resourcePlan?.summary || resources.detail,
      state: resourcePlan?.status || resources.state,
    },
    {
      label: "Agent / Tool / AI",
      title: topology ? `${topology.agent_count || 0}A · ${topology.required_tool_count || 0}T · ${topology.layers?.ai?.effective_profile_count || 0}P` : `${state.workspaceAgentsDraft.length}A · ${state.workspaceToolsDraft.length}T`,
      detail: topology?.summary || "等待实例拓扑",
      state: topology?.status || automation.status,
    },
    {
      label: "执行闭环",
      title: `${jobs.length} 个任务`,
      detail: `${activeJobs} 活跃 · ${doneJobs} 完成 · ${failedJobs} 异常`,
      state: failedJobs ? "failed" : activeJobs ? "running" : automation.status,
    },
  ] : [
    {
      label: "目标输入",
      title: workspaceSourceTypeLabel(workspaceUseSourceMode(inputs)),
      detail: workspaceUseInputSummary(inputs),
      state: inputs.goal_text || inputs.repo_urls?.length || inputs.paper_urls?.length ? "ready" : "draft",
    },
    {
      label: "下一步",
      title: next.title,
      detail: next.detail,
      state: next.state,
    },
    {
      label: "资源调度",
      title: resources.title,
      detail: resources.detail,
      state: resources.state,
    },
    {
      label: "执行闭环",
      title: workspace ? `${jobs.length} 个任务` : `${templateNodes} 个模板节点`,
      detail: workspace
        ? `${activeJobs} 活跃 · ${doneJobs} 完成 · ${failedJobs} 异常`
        : `${template?.agent_count || template?.agent_ids?.length || 0} Agent · ${template?.tool_count || template?.tool_ids?.length || 0} 工具 · 等待创建实例`,
      state: failedJobs ? "failed" : activeJobs ? "running" : workspace ? "ready" : "draft",
    },
  ];
  root.innerHTML = cards.map((card) => `
    <article class="workspace-cockpit-card status-${escapeHtml(card.state || "draft")}">
      <span class="workspace-cockpit-label">${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(card.title)}</strong>
      <p title="${escapeHtml(card.detail)}">${escapeHtml(card.detail)}</p>
    </article>
  `).join("");
  if (readinessRoot) {
    readinessRoot.innerHTML = automation
      ? workspaceAutomationExecutionReadinessMarkup(workspace, { limit: 6 })
      : workspaceCockpitStarterReadinessMarkup(inputs, template, next, resources);
  }
  if (operationsRoot) {
    operationsRoot.innerHTML = workspaceCockpitOperationsMarkup(workspace, inputs, template, next, resources);
  }
}

function workspaceManageTemplateStats() {
  const templates = Array.isArray(state.workflowTemplates) ? state.workflowTemplates : [];
  const draft = state.workflowTemplateDraft && Object.keys(state.workflowTemplateDraft).length
    ? normalizeWorkflowTemplateDraft(state.workflowTemplateDraft)
    : selectedWorkflowTemplate()
      ? normalizeWorkflowTemplateDraft(selectedWorkflowTemplate())
      : null;
  const ready = templates.filter((template) => String(template.status || "ready") === "ready").length;
  const nodeCount = templates.reduce((sum, template) => sum + (Array.isArray(template.nodes) ? template.nodes.length : Number(template.node_count || 0)), 0);
  const missingHandlers = templates.reduce((sum, template) => {
    const nodes = Array.isArray(template.nodes) ? template.nodes : [];
    return sum + nodes.filter((node) => {
      const mode = String(node.handler?.mode || "human");
      return mode !== "human" && !String(node.handler?.agent_id || "").trim();
    }).length;
  }, 0);
  return { templates, draft, ready, nodeCount, missingHandlers };
}

function workspaceManageOverviewCards() {
  const { templates, draft, ready, nodeCount, missingHandlers } = workspaceManageTemplateStats();
  const agents = Array.isArray(state.agentDefinitions) ? state.agentDefinitions : [];
  const tools = Array.isArray(state.toolDefinitions) ? state.toolDefinitions : [];
  const profiles = Array.isArray(state.providerProfiles) ? state.providerProfiles : [];
  const enabledAgents = agents.filter((agent) => agent.enabled !== false);
  const enabledTools = tools.filter((tool) => tool.enabled !== false);
  const toolCategories = new Set(enabledTools.map((tool) => String(tool.category || "general")));
  const agentsWithTools = enabledAgents.filter((agent) => Array.isArray(agent.tools) && agent.tools.length);
  const selectedProfile = selectedProviderProfile();
  const templateProfile = providerProfileById(draft?.model?.provider_profile_id || "");
  const configuredProfiles = profiles.filter((profile) => String(profile.model || "").trim() && (profile.api_key || profile.base_url || profile.vendor));
  return [
    {
      tab: "templates",
      label: "Starter Chain",
      title: `${templates.length} 条模板`,
      detail: `${ready} ready · ${nodeCount} 个节点 · ${draft?.name || "未选择模板"}`,
      next: missingHandlers ? `${missingHandlers} 个节点缺 Agent 归属` : "节点链已具备交接关系",
      state: templates.length && !missingHandlers ? "ready" : templates.length ? "blocked" : "draft",
    },
    {
      tab: "agents",
      label: "Agent 角色库",
      title: `${enabledAgents.length}/${agents.length} 启用`,
      detail: `${agentsWithTools.length} 个 Agent 已绑定工具 · 当前 ${selectedGlobalAgent()?.name || "未选择"}`,
      next: agents.length ? "把规划、仓库、环境、运行、报告职责挂到节点上" : "先建立规划和执行 Agent",
      state: enabledAgents.length ? "ready" : "draft",
    },
    {
      tab: "tools",
      label: "工具注册表",
      title: `${enabledTools.length}/${tools.length} 可用`,
      detail: `${toolCategories.size || 0} 个类别 · 当前 ${selectedGlobalTool()?.label || "未选择"}`,
      next: tools.length ? "补齐数据集、路径解析、环境推断、GPU 调度和产物收集工具" : "先注册自动化执行工具",
      state: enabledTools.length ? "ready" : "draft",
    },
    {
      tab: "ai",
      label: "AI 路由",
      title: `${profiles.length} 个 Profile`,
      detail: `${configuredProfiles.length} 个已填模型 · 当前 ${selectedProfile ? providerProfileLabel(selectedProfile) : "未选择"}`,
      next: templateProfile ? `模板默认 ${providerProfileLabel(templateProfile)}` : "给当前模板指定默认 Profile 和聊天 Agent",
      state: profiles.length && templateProfile ? "ready" : profiles.length ? "blocked" : "draft",
    },
  ];
}

function workspaceManageFocusSummary(tab = state.ui.workspaceManageTab || "templates") {
  const { draft, missingHandlers } = workspaceManageTemplateStats();
  if (tab === "agents") {
    const enabled = state.agentDefinitions.filter((agent) => agent.enabled !== false).length;
    return {
      title: "Agent 层负责把节点变成可执行职责",
      detail: `${enabled} 个 Agent 启用。每个节点应该能明确归属到规划、检索、仓库检查、环境准备、运行调度或报告 Agent。`,
      action: "缺口通常不是名字不够多，而是工具 allowlist 和交接说明不够清楚。",
    };
  }
  if (tab === "tools") {
    const categories = Array.from(new Set(state.toolDefinitions.map((tool) => workspaceToolCategoryLabel(tool.category || "general"))));
    return {
      title: "Tool 层负责真实世界动作边界",
      detail: categories.length ? `当前覆盖 ${categories.join("、")}。` : "还没有工具类别。",
      action: "后续自动复现需要重点补 dataset.find、path.resolve、env.infer、gpu.allocate、artifact.collect。",
    };
  }
  if (tab === "ai") {
    const profile = selectedProviderProfile();
    return {
      title: "AI 层负责模型接入和模板默认路由",
      detail: profile ? `当前 Profile：${providerProfileLabel(profile)}。` : "还没有可用 Profile。",
      action: "模板默认路由决定实例创建后的聊天 Agent、节点 Agent 是否能覆盖模型。",
    };
  }
  return {
    title: "Template 层负责把复现流程固定成 Starter Chain",
    detail: draft ? `${draft.name || "未命名模板"} · ${workspaceSourceTypeLabel(draft.source?.type || "idea")} · ${draft.nodes.length} 个节点。` : "还没有选中的模板。",
    action: missingHandlers ? `${missingHandlers} 个节点还没有绑定 Agent，运行前需要补齐。` : "现在可以优先编辑节点链和默认输入，再保存成可复制快照。",
  };
}

function renderWorkspaceManageOverview() {
  const cardsRoot = $("workspaceManageOverviewCards");
  if (cardsRoot) {
    const activeTab = state.ui.workspaceManageTab || "templates";
    cardsRoot.innerHTML = workspaceManageOverviewCards().map((card) => `
      <button class="workspace-manage-overview-card status-${escapeHtml(card.state || "draft")}${card.tab === activeTab ? " active" : ""}" type="button" data-action="switch-workspace-manage-tab" data-tab="${escapeHtml(card.tab)}" title="切换到${escapeHtml(card.label)}配置页：${escapeHtml(card.detail)}">
        <span class="workspace-cockpit-label">${escapeHtml(card.label)}</span>
        <strong>${escapeHtml(card.title)}</strong>
        <p title="${escapeHtml(card.detail)}">${escapeHtml(card.detail)}</p>
        <em>${escapeHtml(card.next)}</em>
      </button>
    `).join("");
  }
  const focusRoot = $("workspaceManageFocusSummary");
  if (focusRoot) {
    const focus = workspaceManageFocusSummary(state.ui.workspaceManageTab || "templates");
    focusRoot.innerHTML = `
      <strong>${escapeHtml(focus.title)}</strong>
      <span>${escapeHtml(focus.detail)}</span>
      <em>${escapeHtml(focus.action)}</em>
    `;
  }
}

function renderWorkflowTemplateStudioOverview() {
  const root = $("workflowTemplateStudioOverview");
  if (!root) return;
  const draft = state.workflowTemplateDraft && Object.keys(state.workflowTemplateDraft).length
    ? normalizeWorkflowTemplateDraft(state.workflowTemplateDraft)
    : selectedWorkflowTemplate()
      ? normalizeWorkflowTemplateDraft(selectedWorkflowTemplate())
      : defaultWorkflowTemplateDraft("repo");
  const nodes = Array.isArray(draft.nodes) ? draft.nodes : [];
  const automatedNodes = nodes.filter((node) => String(node.handler?.mode || "human") !== "human");
  const assignedNodes = automatedNodes.filter((node) => String(node.handler?.agent_id || "").trim()).length;
  const profile = providerProfileById(draft.model?.provider_profile_id || "");
  const chatAgent = globalAgentById(draft.model?.chat_agent_id || "");
  const sourceBits = [
    draft.source?.repo_url ? "repo" : "",
    draft.source?.paper_url ? "paper" : "",
    draft.source?.idea_text ? "idea" : "",
    draft.workspace_dir ? "workdir" : "",
  ].filter(Boolean);
  const envBits = [
    draft.env?.manager || "",
    draft.env?.name || "",
    draft.env?.python ? `Python ${draft.env.python}` : "",
  ].filter(Boolean);
  const cards = [
    {
      label: "入口类型",
      title: workspaceSourceTypeLabel(draft.source?.type || "idea"),
      detail: sourceBits.length ? sourceBits.join(" · ") : "等待实例输入覆盖默认来源",
      state: sourceBits.length || draft.source?.type === "idea" ? "ready" : "draft",
    },
    {
      label: "节点链",
      title: `${nodes.length} 个节点`,
      detail: `${assignedNodes}/${automatedNodes.length || 0} 自动节点已绑定 Agent · ${nodes[0]?.title || workspaceNodeLabel(nodes[0]?.kind) || "未设置起点"}`,
      state: nodes.length && assignedNodes === automatedNodes.length ? "ready" : nodes.length ? "blocked" : "draft",
    },
    {
      label: "默认环境",
      title: draft.workspace_dir || draft.env?.name || "实例创建时推断",
      detail: envBits.join(" · ") || "后续由 env.infer / path.resolve 补齐",
      state: draft.workspace_dir || draft.env?.name ? "ready" : "draft",
    },
    {
      label: "AI 路由",
      title: profile ? providerProfileLabel(profile) : draft.model?.routing_mode || "workspace_default",
      detail: chatAgent ? `聊天 Agent ${chatAgent.name || chatAgent.id}` : "未设置默认聊天 Agent",
      state: profile ? "ready" : "blocked",
    },
  ];
  root.innerHTML = cards.map((card) => `
    <article class="workspace-template-studio-card status-${escapeHtml(card.state || "draft")}">
      <span class="workspace-cockpit-label">${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(card.title)}</strong>
      <p title="${escapeHtml(card.detail)}">${escapeHtml(card.detail)}</p>
    </article>
  `).join("");
}

function hydrateWorkspaceUseInputsFromWorkspace(workspace) {
  const inputs = workspace?.inputs || {};
  if ($("workspaceTaskGoalInput")) $("workspaceTaskGoalInput").value = inputs.goal_text || workspace?.brief || "";
  if ($("workspaceTaskRepoInput")) $("workspaceTaskRepoInput").value = Array.isArray(inputs.repo_urls) ? inputs.repo_urls.join("\n") : "";
  if ($("workspaceTaskPaperInput")) $("workspaceTaskPaperInput").value = Array.isArray(inputs.paper_urls) ? inputs.paper_urls.join("\n") : "";
  if ($("workspaceTaskReferenceInput")) $("workspaceTaskReferenceInput").value = Array.isArray(inputs.references) ? inputs.references.join("\n") : Array.isArray(workspace?.references) ? workspace.references.join("\n") : "";
  if ($("workspaceTaskContextInput")) $("workspaceTaskContextInput").value = Array.isArray(inputs.context_blocks) ? inputs.context_blocks.join("\n") : "";
}

function ensureDirectorySlash(path) {
  const text = String(path || "").trim();
  if (!text) return "";
  return text.endsWith("/") ? text : `${text}/`;
}

function normalizePathForCompare(path) {
  return String(path || "").replace(/\/+$/, "");
}

function transferPathOnly(value) {
  return parseRsyncTargetPath(value) || String(value || "").trim();
}

function transferSourceValue() {
  return transferPathOnly($("transferSourceInput")?.value || "");
}

function transferTargetValue() {
  return transferPathOnly($("transferTargetInput")?.value || "");
}

function normalizeTransferPathInput(inputEl, selectEl) {
  if (!inputEl) return;
  const raw = String(inputEl.value || "").trim();
  const prefix = parseRsyncTargetPrefix(raw);
  if (!prefix) {
    inputEl.value = transferPathOnly(raw);
    return;
  }
  const server = visibleServers().find((item) => transferTargetMatchesServer(prefix, item));
  if (server && selectEl && Array.from(selectEl.options).some((option) => option.value === server.id)) {
    selectEl.value = server.id;
  }
  inputEl.value = parseRsyncTargetPath(raw) || transferPathOnly(raw);
}

function transferSourceServerId() {
  return $("transferSourceServerSelect")?.value || state.selectedServer || "";
}

function transferTargetServerId() {
  return $("transferTargetServerSelect")?.value || state.selectedServer || "";
}

function parseRsyncTargetPath(value) {
  const text = String(value || "").trim();
  const match = text.match(/^[^:]+:(\/.*)$/);
  if (match) return match[1];
  return text.startsWith("/") ? text : "";
}

function parseRsyncTargetPrefix(value) {
  const text = String(value || "").trim();
  const match = text.match(/^([^:]+):\/.*$/);
  return match ? match[1] : "";
}

function transferTargetPrefix(server) {
  if (!server || server.mode === "local") return "";
  return `${server.target || server.ssh_alias || server.host_name || server.id}:`;
}

function formatTransferTarget(path, server = serverById(transferTargetServerId())) {
  const directory = ensureDirectorySlash(path || "");
  return `${transferTargetPrefix(server)}${directory}`;
}

function formatTransferSource(path, server = serverById(transferSourceServerId()), isDir = false) {
  const value = String(path || "");
  const sourcePath = value && isDir ? ensureDirectorySlash(value) : value;
  return `${transferTargetPrefix(server)}${sourcePath}`;
}

function parseIgnoreText(text) {
  return Array.from(
    new Set(
      String(text || "")
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );
}

function transferRelativePath(path, isDir = false) {
  const parsedSource = parseRsyncTargetPath(transferSourceValue());
  const source = normalizePathForCompare(parsedSource || transferSourceValue());
  const target = normalizePathForCompare(path);
  let relative = target;
  if (source && (target === source || target.startsWith(`${source}/`))) {
    relative = target.slice(source.length).replace(/^\/+/, "");
  }
  if (!relative) relative = pathBaseName(target);
  if (isDir && relative && !relative.endsWith("/")) relative += "/";
  return relative;
}

async function browseFiles(path = "", maxEntries = 300, options = {}) {
  const params = new URLSearchParams();
  if (path) params.set("path", path);
  params.set("max", String(maxEntries));
  if (options.serverId) params.set("server_id", options.serverId);
  if (options.dirsOnly) params.set("dirs_only", "1");
  return fetchJson(`/api/files/browse?${params.toString()}`);
}

async function readFileText(path = "", limitBytes = 131072, options = {}) {
  const params = new URLSearchParams();
  if (path) params.set("path", path);
  params.set("limit", String(limitBytes));
  if (options.serverId) params.set("server_id", options.serverId);
  return fetchJson(`/api/files/read?${params.toString()}`);
}

function parseDateMs(value) {
  const ms = Date.parse(value || "");
  return Number.isFinite(ms) ? ms : 0;
}

function formatDurationMs(value) {
  const totalSeconds = Math.max(0, Math.round(Number(value || 0) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function jobDurationMs(job) {
  const start = parseDateMs(job.started_at || job.created_at);
  const end = parseDateMs(job.finished_at) || Date.now();
  if (!start || end < start) return 0;
  return end - start;
}

function isWaitingJob(job) {
  return ["queued", "blocked"].includes(String(job?.status || ""));
}

function jobKindGroup(job) {
  const kind = String(job?.kind || "");
  if (kind === "transfer") return "transfer";
  if (kind === "profile") return "profile";
  if (kind.includes("batch")) return "batch";
  return "command";
}

function jobQueueRank(job) {
  const rank = Number(job?.queue_rank || 0);
  return Number.isFinite(rank) && rank > 0 ? rank : Number.MAX_SAFE_INTEGER;
}

function serverBusyGpuCount(server) {
  return (server.gpus || []).filter((gpu) => gpu.state === "busy").length;
}

function serverIdleGpuCount(server) {
  return Math.max((server.gpus || []).length - serverBusyGpuCount(server), 0);
}

function serverHostResources(server) {
  const resources = server?.host_resources;
  return resources && typeof resources === "object" ? resources : {};
}

function serverHostResourceSummary(server) {
  const resources = serverHostResources(server);
  if (!Object.keys(resources).length) {
    return {
      badge: "主机待采集",
      title: "等待主机 CPU、内存、磁盘和网络资源快照",
      state: "muted",
    };
  }
  if (resources.ok === false) {
    return {
      badge: "主机异常",
      title: resources.error || "主机资源采集失败",
      state: "warning",
    };
  }
  const cpu = resources.cpu || {};
  const memory = resources.memory || {};
  const cpuText = formatPercent(cpu.util_percent);
  const memText = formatPercent(memory.used_percent);
  return {
    badge: `主机 ${cpuText}/${memText}`,
    title: `CPU ${cpuText} · 内存 ${memText} · 悬停查看磁盘和网络`,
    state: "ok",
  };
}

function serverHostResourceMetric(label, value, detail = "") {
  return `
    <div class="server-resource-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      ${detail ? `<em>${escapeHtml(detail)}</em>` : ""}
    </div>
  `;
}

function serverHostResourceDiskRows(disks = []) {
  if (!Array.isArray(disks) || !disks.length) {
    return '<div class="server-resource-empty">未采集到磁盘挂载点</div>';
  }
  return disks.slice(0, 5).map((disk) => `
    <div class="server-resource-row">
      <span title="${escapeHtml(`${disk.device || ""} ${disk.fs_type || ""}`.trim())}">${escapeHtml(disk.mount || "-")}</span>
      <strong>${escapeHtml(formatPercent(disk.used_percent))}</strong>
      <em>${escapeHtml(formatBytes(disk.used_bytes))} / ${escapeHtml(formatBytes(disk.total_bytes))}</em>
    </div>
  `).join("");
}

function serverHostResourceNetworkRows(network = {}) {
  const interfaces = Array.isArray(network.interfaces) ? network.interfaces : [];
  if (!interfaces.length) {
    return `
      <div class="server-resource-row">
        <span>累计流量</span>
        <strong>RX ${escapeHtml(formatBytes(network.rx_bytes))}</strong>
        <em>TX ${escapeHtml(formatBytes(network.tx_bytes))}</em>
      </div>
    `;
  }
  return interfaces.slice(0, 4).map((iface) => `
    <div class="server-resource-row">
      <span>${escapeHtml(iface.name || "-")}</span>
      <strong>RX ${escapeHtml(formatBytes(iface.rx_bytes))}</strong>
      <em>TX ${escapeHtml(formatBytes(iface.tx_bytes))}</em>
    </div>
  `).join("");
}

function serverHostResourcePopoverMarkup(server) {
  const resources = serverHostResources(server);
  const collectedAt = resources.collected_at ? `采集 ${resources.collected_at}` : "等待采集";
  if (!Object.keys(resources).length || resources.ok === false) {
    return `
      <div class="server-resource-popover" role="tooltip">
        <div class="server-resource-popover-head">
          <strong>主机资源</strong>
          <span>${escapeHtml(collectedAt)}</span>
        </div>
        <div class="server-resource-empty">${escapeHtml(resources.error || "还没有 CPU、内存、磁盘和网络快照。")}</div>
      </div>
    `;
  }
  const cpu = resources.cpu || {};
  const memory = resources.memory || {};
  const swap = resources.swap || {};
  const network = resources.network || {};
  const disks = Array.isArray(resources.disks) ? resources.disks : [];
  const primaryDisk = disks[0] || {};
  return `
    <div class="server-resource-popover" role="tooltip">
      <div class="server-resource-popover-head">
        <strong>主机资源</strong>
        <span>${escapeHtml(collectedAt)}</span>
      </div>
      <div class="server-resource-grid">
        ${serverHostResourceMetric("CPU", formatPercent(cpu.util_percent), `${cpu.cores || "-"} 核 · load ${cpu.load1 ?? "-"}/${cpu.load5 ?? "-"}/${cpu.load15 ?? "-"}`)}
        ${serverHostResourceMetric("内存", formatPercent(memory.used_percent), `${formatBytes(memory.used_bytes)} / ${formatBytes(memory.total_bytes)}`)}
        ${serverHostResourceMetric("Swap", formatPercent(swap.used_percent), `${formatBytes(swap.used_bytes)} / ${formatBytes(swap.total_bytes)}`)}
        ${serverHostResourceMetric("主磁盘", formatPercent(primaryDisk.used_percent), `${primaryDisk.mount || "-"} · ${formatBytes(primaryDisk.free_bytes)} 空闲`)}
      </div>
      <div class="server-resource-section">
        <div class="server-resource-section-title">磁盘 / inode</div>
        ${serverHostResourceDiskRows(disks)}
      </div>
      <div class="server-resource-section">
        <div class="server-resource-section-title">网络接口</div>
        ${serverHostResourceNetworkRows(network)}
      </div>
    </div>
  `;
}

function serverResourceOverlayNode() {
  let node = $("serverResourceOverlay");
  if (!node) {
    node = document.createElement("div");
    node.id = "serverResourceOverlay";
    node.className = "server-resource-overlay";
    node.hidden = true;
    node.addEventListener("mouseenter", clearServerResourceHideTimer);
    node.addEventListener("mouseleave", () => scheduleHideServerResourcePopover());
    document.body.appendChild(node);
  }
  return node;
}

function clearServerResourceHideTimer() {
  if (serverResourceHideTimer) {
    clearTimeout(serverResourceHideTimer);
    serverResourceHideTimer = null;
  }
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function positionServerResourcePopover(anchor = activeServerResourceAnchor) {
  const overlay = $("serverResourceOverlay");
  if (!overlay || overlay.hidden || !anchor?.isConnected) return;
  const list = $("serverList");
  const anchorRect = anchor.getBoundingClientRect();
  if (list) {
    const listRect = list.getBoundingClientRect();
    if (anchorRect.bottom < listRect.top || anchorRect.top > listRect.bottom) {
      hideServerResourcePopover();
      return;
    }
  }
  const margin = 12;
  const gap = 10;
  const width = Math.min(380, Math.max(280, window.innerWidth - margin * 2));
  overlay.style.width = `${width}px`;
  overlay.style.maxHeight = `${Math.max(220, window.innerHeight - margin * 2)}px`;
  const preferRight = anchorRect.right + gap + width <= window.innerWidth - margin;
  const preferLeft = anchorRect.left - gap - width >= margin;
  let left = preferRight
    ? anchorRect.right + gap
    : preferLeft
      ? anchorRect.left - gap - width
      : clampNumber(anchorRect.left, margin, window.innerWidth - width - margin);
  const height = Math.min(overlay.offsetHeight || 420, window.innerHeight - margin * 2);
  let top = clampNumber(anchorRect.top, margin, window.innerHeight - height - margin);
  if (!preferRight && !preferLeft && anchorRect.bottom + gap + height <= window.innerHeight - margin) {
    top = anchorRect.bottom + gap;
  }
  left = clampNumber(left, margin, window.innerWidth - width - margin);
  overlay.style.left = `${Math.round(left)}px`;
  overlay.style.top = `${Math.round(top)}px`;
}

function showServerResourcePopover(serverId, anchor) {
  const id = String(serverId || "").trim();
  const server = serverById(id);
  if (!server || !anchor) return;
  clearServerResourceHideTimer();
  activeServerResourceAnchor = anchor;
  const overlay = serverResourceOverlayNode();
  overlay.dataset.serverId = id;
  overlay.innerHTML = serverHostResourcePopoverMarkup(server);
  overlay.hidden = false;
  requestAnimationFrame(() => {
    overlay.classList.add("visible");
    positionServerResourcePopover(anchor);
  });
}

function hideServerResourcePopover() {
  clearServerResourceHideTimer();
  activeServerResourceAnchor = null;
  const overlay = $("serverResourceOverlay");
  if (!overlay) return;
  overlay.classList.remove("visible");
  overlay.hidden = true;
  overlay.innerHTML = "";
  overlay.dataset.serverId = "";
}

function scheduleHideServerResourcePopover(delay = 120) {
  clearServerResourceHideTimer();
  serverResourceHideTimer = setTimeout(() => hideServerResourcePopover(), delay);
}

function serverAlertCount() {
  return state.servers.filter((server) => {
    const history = state.ui.serverHistory[server.id] || [];
    return history.some((item) => !item.online || item.error);
  }).length;
}

function allGpus() {
  return onlineServers().flatMap((server) =>
    (server.gpus || []).map((gpu) => ({ server, gpu })),
  );
}

function allProcesses() {
  return onlineServers().flatMap((server) =>
    (server.processes || []).map((process) => ({ server, process })),
  );
}

function processFilterKey(item) {
  const serverName = item.server?.name || "";
  const process = item.process || {};
  return [
    serverName,
    item.server?.id || "",
    process.gpu_index ?? "",
    process.pid ?? "",
    process.user || "",
    process.used_memory_mib ?? "",
    process.command || process.process_name || "",
  ]
    .join(" ")
    .toLowerCase();
}

function processSortValue(item, key) {
  const process = item.process || {};
  if (key === "server") return item.server?.name || item.server?.id || "";
  if (key === "gpu") return Number(process.gpu_index ?? -1);
  if (key === "pid") return Number(process.pid ?? 0);
  if (key === "user") return process.user || "";
  if (key === "vram") return Number(process.used_memory_mib || 0);
  if (key === "command") return process.command || process.process_name || "";
  return "";
}

function filteredProcesses(items) {
  const query = state.processFilters.query.trim().toLowerCase();
  const selectedServerId = state.processFilters.server;
  const user = state.processFilters.user;
  const gpu = state.processFilters.gpu;
  const filtered = items.filter((item) => {
    const process = item.process || {};
    if (query && !processFilterKey(item).includes(query)) return false;
    if (selectedServerId && String(item.server?.id || "") !== selectedServerId) return false;
    if (user && String(process.user || "") !== user) return false;
    if (gpu && String(process.gpu_index ?? "") !== gpu) return false;
    return true;
  });
  const sortKey = state.processFilters.sort || "server";
  const direction = state.processFilters.dir === "desc" ? -1 : 1;
  filtered.sort((a, b) => {
    const left = processSortValue(a, sortKey);
    const right = processSortValue(b, sortKey);
    if (typeof left === "number" && typeof right === "number") {
      return (left - right) * direction;
    }
    return String(left).localeCompare(String(right), "zh-Hans-CN", {
      numeric: true,
      sensitivity: "base",
    }) * direction;
  });
  return filtered;
}

function renderProcessFilters(items) {
  const serverSelect = $("processServerFilter");
  const userSelect = $("processUserFilter");
  const gpuSelect = $("processGpuFilter");
  if (!serverSelect || !userSelect || !gpuSelect) return;
  const serverPool = onlineServers().length
    ? onlineServers()
    : Array.from(new Map(items.map(({ server }) => [server.id, server])).values());
  const servers = serverPool
    .slice()
    .sort((a, b) => String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-Hans-CN", { numeric: true }));
  const users = Array.from(new Set(items.map(({ process }) => process.user).filter(Boolean)))
    .sort((a, b) => String(a).localeCompare(String(b), "zh-Hans-CN", { numeric: true }));
  const gpus = Array.from(new Set(items.map(({ process }) => String(process.gpu_index ?? "")).filter(Boolean)))
    .sort((a, b) => Number(a) - Number(b));
  const currentServer = state.processFilters.server;
  const currentUser = state.processFilters.user;
  const currentGpu = state.processFilters.gpu;
  serverSelect.innerHTML = '<option value="">全部服务器</option>' +
    servers.map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(server.name || server.id)}</option>`).join("");
  userSelect.innerHTML = '<option value="">全部用户</option>' +
    users.map((user) => `<option value="${escapeHtml(user)}">${escapeHtml(user)}</option>`).join("");
  gpuSelect.innerHTML = '<option value="">全部 GPU</option>' +
    gpus.map((gpu) => `<option value="${escapeHtml(gpu)}">GPU ${escapeHtml(gpu)}</option>`).join("");
  serverSelect.value = servers.some((server) => server.id === currentServer) ? currentServer : "";
  userSelect.value = users.includes(currentUser) ? currentUser : "";
  gpuSelect.value = gpus.includes(currentGpu) ? currentGpu : "";
  state.processFilters.server = serverSelect.value;
  state.processFilters.user = userSelect.value;
  state.processFilters.gpu = gpuSelect.value;
}

function renderProcessSortIndicators() {
  document.querySelectorAll("#processTable th[data-sort]").forEach((th) => {
    const indicator = th.querySelector(".sort-indicator");
    if (!indicator) return;
    if (th.dataset.sort === state.processFilters.sort) {
      indicator.textContent = state.processFilters.dir === "desc" ? "▼" : "▲";
    } else {
      indicator.textContent = "";
    }
  });
}

function onlineServers() {
  return state.servers.filter((server) => server.online);
}

function serverIsReachable(server) {
  if (!server) return false;
  if (typeof server.reachable === "boolean") return server.reachable;
  return Boolean(server.online);
}

function serverHasMonitorIssue(server) {
  return Boolean(server) && !server.online && serverIsReachable(server);
}

function connectedServers() {
  return state.servers.filter((server) => serverIsReachable(server));
}

function offlineServers() {
  return state.servers.filter((server) => !serverIsReachable(server));
}

function visibleServers() {
  return state.servers;
}

function sortedVisibleServers() {
  return sortedServersForDisplay(visibleServers());
}

function serverOptionLabel(server) {
  const parts = [server.name || server.id || "未命名服务器"];
  const tags = [server.online ? "在线" : serverIsReachable(server) ? "已连接" : "离线"];
  if (serverHasMonitorIssue(server)) tags.push("GPU 异常");
  const gpuCount = (server.gpus || []).length;
  const busyCount = serverBusyGpuCount(server);
  const processCount = (server.processes || []).length;
  if (gpuCount) tags.push(`${busyCount}/${gpuCount} GPU 忙`);
  if (processCount) tags.push(`${processCount} 进程`);
  return `${parts.join("")} · ${tags.join(" · ")}`;
}

function serverOptionShortLabel(server) {
  const name = server.name || server.id || "未命名服务器";
  if (server.online) return `${name} · 在线`;
  if (serverIsReachable(server)) {
    return serverHasMonitorIssue(server) ? `${name} · 已连接 · GPU 异常` : `${name} · 已连接`;
  }
  return `${name} · 离线`;
}

function serverById(serverId) {
  return state.servers.find((server) => server.id === serverId) || null;
}

function workspaceById(workspaceId) {
  return state.workspaces.find((item) => item.id === workspaceId) || null;
}

function selectedWorkspace() {
  const workspaceId = String($("workspaceIdInput")?.value || state.selectedWorkspaceId || "").trim();
  return workspaceId ? workspaceById(workspaceId) : null;
}

function workflowTemplateById(templateId) {
  return state.workflowTemplates.find((item) => item.id === templateId) || null;
}

function selectedWorkflowTemplate() {
  return workflowTemplateById(state.selectedWorkflowTemplateId) || null;
}

function globalAgentById(agentId) {
  return state.agentDefinitions.find((item) => item.id === agentId) || null;
}

function selectedGlobalAgent() {
  return globalAgentById(state.selectedGlobalAgentId) || null;
}

function globalToolById(toolId) {
  return state.toolDefinitions.find((item) => item.id === toolId) || null;
}

function selectedGlobalTool() {
  return globalToolById(state.selectedGlobalToolId) || null;
}

function workspaceRecipe(workspace) {
  const recipes = Array.isArray(workspace?.recipes) ? workspace.recipes : [];
  return recipes.find((item) => item && item.enabled !== false) || recipes[0] || null;
}

function workspaceSourceSummary(workspace) {
  const source = workspace?.source || {};
  if (workspace?.brief && source.type === "idea") return workspace.brief;
  if (source.type === "repo") return source.repo_url || "未填写仓库地址";
  if (source.type === "paper") return source.paper_url || "未填写论文链接";
  return source.idea_text || workspace?.brief || "未填写想法";
}

function workspaceDraftSourceSummary(formData = workspaceFormPayload(), workspace = selectedWorkspace()) {
  const sourceType = String(formData.source_type || workspace?.source?.type || "idea");
  if (sourceType === "repo") return String(formData.repo_url || workspace?.source?.repo_url || "").trim() || "未填写仓库地址";
  if (sourceType === "paper") return String(formData.paper_url || workspace?.source?.paper_url || "").trim() || "未填写论文链接";
  return String(formData.idea_text || formData.brief || workspace?.source?.idea_text || workspace?.brief || "").trim() || "未填写想法";
}

function workspaceStatusLabel(value) {
  const text = String(value || "");
  if (text === "blocked") return "阻塞";
  return zhStatus(text);
}

function workspaceJobs() {
  const workspaceId = String(state.selectedWorkspaceId || selectedWorkspace()?.id || "").trim();
  if (!workspaceId) return [];
  return state.jobs.filter((job) => String(job?.metadata?.workspace_id || "").trim() === workspaceId);
}

function workspaceRuntimeTrace(node = {}) {
  return Array.isArray(node?.trace)
    ? node.trace
    : Array.isArray(node?.runtime?.trace)
      ? node.runtime.trace
      : [];
}

function workspaceRuntimeArtifacts(node = {}) {
  return Array.isArray(node?.artifacts)
    ? node.artifacts
    : Array.isArray(node?.runtime?.artifacts)
      ? node.runtime.artifacts
      : [];
}

function workspaceRuntimeResources(node = {}) {
  if (node?.resources && typeof node.resources === "object") return node.resources;
  if (node?.runtime?.resources && typeof node.runtime.resources === "object") return node.runtime.resources;
  return {};
}

function workspaceArtifactStatusLabel(status) {
  const value = String(status || "").trim();
  if (value === "found") return "已找到";
  if (value === "expected") return "待生成";
  if (value === "missing") return "缺失";
  if (value === "unreadable") return "不可读";
  if (value === "planned") return "计划中";
  return value || "未知";
}

function workspaceTraceStatusLabel(status) {
  const value = String(status || "").trim();
  if (value === "planned") return "已编排";
  if (value === "queued") return "排队";
  if (value === "blocked") return "等待";
  if (value === "running") return "运行";
  if (value === "done") return "完成";
  if (value === "failed") return "失败";
  if (value === "stopped") return "停止";
  return workspaceStatusLabel(value || "pending");
}

function workspaceDetailResourceMarkup(resources = {}) {
  const items = [
    ["Server", resources.server_id || resources.requested_server_id || "auto"],
    ["GPU", resources.gpu_index || resources.gpu_policy || "auto"],
    ["模式", resources.execution_mode || "cpu"],
    ["环境", resources.env_name || "未设置"],
    ["目录", resources.cwd || "未设置"],
    ["依赖", Array.isArray(resources.depends_on) && resources.depends_on.length ? resources.depends_on.join(", ") : "无"],
  ];
  return `
    <div class="workspace-detail-resource-grid">
      ${items.map(([label, value]) => `
        <article class="workspace-detail-resource">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(String(value || "未设置"))}</strong>
        </article>
      `).join("")}
    </div>
  `;
}

function workspaceDetailTraceMarkup(trace = []) {
  if (!trace.length) return '<div class="empty">还没有节点 trace。</div>';
  return `
    <div class="workspace-detail-timeline">
      ${trace.map((item) => {
        const status = String(item.status || "pending").trim();
        return `
          <article class="workspace-detail-trace status-${escapeHtml(status)}">
            <span>${escapeHtml(workspaceTraceStatusLabel(status))}</span>
            <strong>${escapeHtml(item.label || "状态更新")}</strong>
            <em>${escapeHtml(item.detail || "")}</em>
            <small>${escapeHtml(fmtDate(item.at || ""))}</small>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function workspaceDetailArtifactsMarkup(artifacts = []) {
  if (!artifacts.length) return '<div class="empty">还没有产物或路径快照。</div>';
  return `
    <div class="workspace-detail-artifact-list">
      ${artifacts.slice(0, 18).map((artifact) => {
        const status = String(artifact.status || "").trim();
        const path = artifact.resolved_path || artifact.path || "";
        return `
          <article class="workspace-detail-artifact status-${escapeHtml(status || "planned")}">
            <div>
              <strong>${escapeHtml(artifact.label || artifact.source || "产物")}</strong>
              <span>${escapeHtml(path || "未设置路径")}</span>
            </div>
            <em>${escapeHtml(workspaceArtifactStatusLabel(status))}</em>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function clearWorkspaceMessage() {
  const message = $("workspaceMessage");
  if (!message) return;
  message.textContent = "";
  message.classList.remove("error");
}

function setWorkspaceFormValues(data = {}) {
  const form = $("workspaceForm");
  if (!form) return;
  form.querySelectorAll("[name]").forEach((field) => {
    if (!(field.name in data)) return;
    field.value = data[field.name] ?? "";
  });
  toggleWorkspaceSourceFields();
}

function workspaceFormPayload() {
  const form = $("workspaceForm");
  if (!form) return {};
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.workspace_id = String(payload.workspace_id || "").trim();
  return payload;
}

function selectedWorkspaceAgent() {
  return workspaceAgentById(state.selectedWorkspaceAgentId, state.workspaceAgentsDraft) || state.workspaceAgentsDraft[0] || null;
}

function selectedProviderProfile() {
  return providerProfileById(state.selectedProviderProfileId, state.providerProfiles) || state.providerProfiles[0] || null;
}

function workspaceSourceTypeLabel(value) {
  if (value === "repo") return "仓库";
  if (value === "paper") return "论文";
  if (value === "mixed") return "混合";
  return "通用目标";
}

function workspaceHeaderMeta() {
  const formData = workspaceFormPayload();
  const parts = [
    workspaceSourceTypeLabel(String(formData.source_type || "idea")),
    `${state.workspaceNodesDraft.length} 个节点`,
    `${state.workspaceAgentsDraft.length} 个 agent`,
    `${state.workspaceToolsDraft.length} 个工具`,
  ];
  if (formData.workspace_dir) parts.push(String(formData.workspace_dir));
  const profile = providerProfileById(state.workspaceModelDraft.provider_profile_id);
  if (profile) parts.push(providerProfileLabel(profile));
  return parts.join(" · ");
}

function workspaceModuleCardsConfig() {
  const workspace = selectedWorkspace();
  const formData = workspaceFormPayload();
  const jobs = workspaceJobs();
  const activeJobs = jobs.filter((job) => isJobActive(job)).length;
  const failedJobs = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  const messages = Array.isArray(workspace?.chat) ? workspace.chat.length : 0;
  const enabledAgents = state.workspaceAgentsDraft.filter((agent) => agent.enabled !== false).length;
  const enabledTools = state.workspaceToolsDraft.filter((tool) => tool.enabled !== false).length;
  const toolCategories = new Set(state.workspaceToolsDraft.map((tool) => String(tool.category || "general"))).size;
  const profile = providerProfileById(state.workspaceModelDraft.provider_profile_id);
  const chatAgent = workspaceAgentById(state.workspaceModelDraft.chat_agent_id)?.name || "项目默认 Agent";
  const sourceSummary = workspaceDraftSourceSummary(formData, workspace);
  const referenceCount = parseLineList(formData.references || "").length || (Array.isArray(workspace?.references) ? workspace.references.length : 0);
  const workspaceDir = String(formData.workspace_dir || workspace?.workspace_dir || "").trim() || "未设工作目录";
  const envName = String(formData.env_name || workspace?.env?.name || "").trim() || "未设环境";
  const statusValue = String(formData.status || workspace?.status || "draft");
  return [
    {
      id: "home",
      title: "概览",
      meta: `${workspaceSourceTypeLabel(String(formData.source_type || workspace?.source?.type || "idea"))} · ${workspaceStatusLabel(statusValue)}`,
      detail: String(formData.brief || sourceSummary || "先从这里确认目标、编排规模和最近运行。").trim() || "先从这里确认目标、编排规模和最近运行。",
    },
    {
      id: "project",
      title: "项目设置",
      meta: `${referenceCount} 条参考 · ${workspaceDir}`,
      detail: `${envName}${formData.schedule ? ` · ${String(formData.schedule).trim()}` : ""}`,
    },
    {
      id: "workflow",
      title: "工作流",
      meta: `${state.workspaceNodesDraft.length} 个节点`,
      detail: workspaceNodeRuntimeSummary(workspaceRunNode(state.workspaceNodesDraft)) || "把 repo、环境、运行和评估拆成可见节点。",
    },
    {
      id: "chat",
      title: "对话",
      meta: `${messages} 条消息`,
      detail: `当前路由 ${chatAgent}`,
    },
    {
      id: "agents",
      title: "Agent 管理",
      meta: `${state.workspaceAgentsDraft.length} 个 agent · ${enabledAgents} 启用`,
      detail: "角色、提示词、模型覆盖和工具边界。",
    },
    {
      id: "tools",
      title: "工具注册",
      meta: `${state.workspaceToolsDraft.length} 个工具 · ${toolCategories} 类`,
      detail: `${enabledTools} 个已启用工具可分配给不同 agent。`,
    },
    {
      id: "model",
      title: "AI 配置",
      meta: `${state.providerProfiles.length} 个 profile`,
      detail: profile ? `${providerProfileLabel(profile)} · ${state.workspaceModelDraft.routing_mode === "agent_override" ? "允许 agent 覆盖" : "项目统一默认"}` : "先配置 provider、model 和路由策略。",
    },
    {
      id: "runs",
      title: "运行记录",
      meta: `${jobs.length} 个任务 · ${activeJobs} 活跃`,
      detail: failedJobs ? `${failedJobs} 个失败或停止，适合先看这里。` : "查看当前项目绑定的节点任务和输出。",
    },
  ];
}

function renderWorkspaceHeader() {
  const formData = workspaceFormPayload();
  const title = String(formData.name || selectedWorkspace()?.name || "").trim() || "新工作区";
  const meta = workspaceHeaderMeta();
  if ($("workspaceTitleDisplay")) $("workspaceTitleDisplay").textContent = title;
  if ($("workspaceSummaryMeta")) $("workspaceSummaryMeta").textContent = meta;
}

function renderWorkspaceModuleCards() {
  const root = $("workspaceModuleCards");
  if (!root) return;
  root.innerHTML = workspaceModuleCardsConfig().map((item) => {
    const active = item.id === state.ui.workspaceTab ? " active" : "";
    return `
      <button class="workspace-module-card${active}" type="button" data-tab="${escapeHtml(item.id)}" title="切换到${escapeHtml(item.title)}模块：${escapeHtml(item.detail)}">
        <div class="workspace-module-card-head">
          <strong>${escapeHtml(item.title)}</strong>
          <span class="workspace-module-card-meta">${escapeHtml(item.meta)}</span>
        </div>
        <div class="workspace-module-card-detail" title="${escapeHtml(item.detail)}">${escapeHtml(item.detail)}</div>
      </button>
    `;
  }).join("");
}

function defaultWorkspaceAgentDebugInput(agent = selectedWorkspaceAgent()) {
  const workspace = selectedWorkspace();
  const formData = workspaceFormPayload();
  const node = selectedWorkspaceNode();
  return [
    `项目：${String(formData.name || workspace?.name || "未命名项目").trim() || "未命名项目"}`,
    `目标：${String(formData.brief || workspaceDraftSourceSummary(formData, workspace) || "待补项目目标").trim() || "待补项目目标"}`,
    node ? `当前节点：${node.title || workspaceNodeLabel(node.kind)} (${node.kind})` : "",
    agent ? `请说明 ${agent.name || agent.id} 接下来应该如何处理，优先使用哪些工具。` : "请说明当前 Agent 应该如何处理这项任务。",
  ].filter(Boolean).join("\n");
}

function ensureWorkspaceAgentDebugState(agent = selectedWorkspaceAgent()) {
  const workspaceId = String(selectedWorkspace()?.id || "draft").trim();
  const agentId = String(agent?.id || "").trim();
  if (!agentId) {
    state.workspaceAgentDebug = {
      workspaceId: "",
      agentId: "",
      input: "",
      result: null,
      busy: false,
      error: "",
    };
    return;
  }
  if (state.workspaceAgentDebug.workspaceId === workspaceId && state.workspaceAgentDebug.agentId === agentId) return;
  state.workspaceAgentDebug = {
    workspaceId,
    agentId,
    input: defaultWorkspaceAgentDebugInput(agent),
    result: null,
    busy: false,
    error: "",
  };
}

function workspaceAgentDebugResultMarkup(result) {
  if (!result) return "";
  const focusNode = result.focus_node || {};
  const model = result.model || {};
  const context = result.context || {};
  const allowedTools = Array.isArray(result.allowed_tools) ? result.allowed_tools : [];
  const assignedNodes = Array.isArray(result.assigned_nodes) ? result.assigned_nodes : [];
  const plan = Array.isArray(result.plan) ? result.plan : [];
  const nextActions = Array.isArray(result.next_actions) ? result.next_actions : [];
  const warnings = Array.isArray(result.warnings) ? result.warnings : [];
  return `
    <div class="workspace-agent-debug-result">
      <div class="workspace-agent-debug-summary">
        <article class="workspace-agent-debug-card">
          <span>聚焦节点</span>
          <strong>${escapeHtml(focusNode.title || "未命中")}</strong>
          <em>${escapeHtml(focusNode.kind || "未指定")}${focusNode.status ? ` · ${escapeHtml(workspaceStatusLabel(focusNode.status))}` : ""}</em>
        </article>
        <article class="workspace-agent-debug-card">
          <span>有效模型路由</span>
          <strong>${escapeHtml(model.effective_profile_id || "未配置")}</strong>
          <em>${escapeHtml(model.source || "unconfigured")} · ${escapeHtml(model.routing_mode || "workspace_default")}</em>
        </article>
        <article class="workspace-agent-debug-card">
          <span>可用工具</span>
          <strong>${allowedTools.length}</strong>
          <em>${escapeHtml(allowedTools.slice(0, 3).map((tool) => tool.label || tool.id).join(" / ") || "没有可用工具")}</em>
        </article>
        <article class="workspace-agent-debug-card">
          <span>上下文</span>
          <strong>${escapeHtml(workspaceSourceTypeLabel(context.source_type || "idea"))}</strong>
          <em>${escapeHtml(context.workspace_dir || context.source_summary || "未补目录或来源")}</em>
        </article>
      </div>
      <div class="workspace-agent-debug-blocks">
        <section class="workspace-agent-debug-block">
          <div class="subsection-head">
            <strong>Prompt 预演</strong>
            <span class="muted">${escapeHtml(result.generated_at || "")}</span>
          </div>
          <pre class="workspace-agent-debug-pre">${escapeHtml(result.prompt_preview || "还没有可展示的 prompt。")}</pre>
        </section>
        <section class="workspace-agent-debug-block">
          <div class="subsection-head">
            <strong>执行思路</strong>
            <span class="muted">确定性预演，不调用外部模型</span>
          </div>
          <ol class="workspace-agent-debug-list">
            ${plan.map((step) => `<li>${escapeHtml(step)}</li>`).join("") || "<li>当前还没有推导出明确步骤。</li>"}
          </ol>
        </section>
        <section class="workspace-agent-debug-block">
          <div class="subsection-head">
            <strong>建议下一步</strong>
            <span class="muted">${assignedNodes.length} 个已绑定节点</span>
          </div>
          <ul class="workspace-agent-debug-list bullet">
            ${nextActions.map((step) => `<li>${escapeHtml(step)}</li>`).join("") || "<li>当前没有额外建议。</li>"}
          </ul>
          ${assignedNodes.length ? `
            <div class="workspace-agent-debug-chip-row">
              ${assignedNodes.map((node) => `<span class="workspace-agent-debug-chip">${escapeHtml(node.title || node.kind)} · ${escapeHtml(workspaceStatusLabel(node.status || "draft"))}</span>`).join("")}
            </div>
          ` : ""}
        </section>
        <section class="workspace-agent-debug-block">
          <div class="subsection-head">
            <strong>可用工具</strong>
            <span class="muted">${allowedTools.length} 个</span>
          </div>
          <div class="workspace-agent-debug-tool-list">
            ${allowedTools.map((tool) => `
              <article class="workspace-agent-debug-tool">
                <strong>${escapeHtml(tool.label || tool.id)}</strong>
                <span>${escapeHtml(tool.id || "")}</span>
                <em>${escapeHtml(workspaceToolCategoryLabel(tool.category || "general"))} · ${escapeHtml(tool.capability || "read")}</em>
              </article>
            `).join("") || '<div class="empty">这个 agent 还没有允许的工具。</div>'}
          </div>
          ${warnings.length ? `
            <div class="workspace-agent-debug-warning-list">
              ${warnings.map((item) => `<div class="workspace-agent-debug-warning">${escapeHtml(item)}</div>`).join("")}
            </div>
          ` : ""}
        </section>
      </div>
    </div>
  `;
}

function workspaceHomeRecommendations() {
  const workspace = selectedWorkspace();
  const formData = workspaceFormPayload();
  const jobs = workspaceJobs();
  const failedJobs = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  const activeJobs = jobs.filter((job) => isJobActive(job)).length;
  const sourceType = String(formData.source_type || workspace?.source?.type || "idea");
  const sourceSummary = workspaceDraftSourceSummary(formData, workspace);
  const runNode = workspaceRunNode(state.workspaceNodesDraft);
  const runCommand = String(runNode?.config?.run_command || formData.run_command || "").trim();
  const automation = workspaceAutomationSummary(workspace);
  const advance = automation?.advance || null;
  const items = [];
  if (workspace?.id && advance) {
    items.push({
      title: advance.title || "自动推进",
      detail: `${advance.reason || "系统已判断下一步。"}${advance.next_action ? ` 下一步：${advance.next_action}` : ""}`,
      buttons: [
        { label: "自动推进", action: "advanceWorkspaceAutomation()", tone: "primary" },
        { label: "看执行链", action: "switchWorkspaceTab('home')", tone: "secondary" },
      ],
    });
  }
  if (!workspace?.id) {
    items.push({
      title: "先保存项目壳",
      detail: "把目标、目录和节点草稿先保存成项目，后续对话、运行和日志才会统一挂接。",
      buttons: [{ label: "打开项目设置", action: "switchWorkspaceTab('project')", tone: "primary" }],
    });
  }
  if (!String(sourceSummary).trim() || sourceSummary.startsWith("未填写")) {
    items.push({
      title: "补齐输入来源",
      detail: sourceType === "repo"
        ? "先补 repo 地址或分支，starter chain 才能更像真实执行链。"
        : sourceType === "paper"
          ? "先补论文链接，后续检索和复现链会更稳定。"
          : "先写清目标和约束，Planner / Researcher 才有明确上下文。",
      buttons: [{ label: "去项目设置", action: "switchWorkspaceTab('project')", tone: "primary" }],
    });
  }
  if (!runCommand) {
    items.push({
      title: "明确运行入口",
      detail: "当前还没看到清晰的运行命令，先把运行节点补完整，后面才适合提交任务或批量调度。",
      buttons: [{ label: "去工作流", action: "switchWorkspaceTab('workflow')", tone: "primary" }],
    });
  }
  if (!state.providerProfiles.length) {
    items.push({
      title: "补一个 AI Profile",
      detail: "对话、Agent 调试和后续多模型路由都依赖本地 Provider Profile。",
      buttons: [{ label: "去 AI 配置", action: "switchWorkspaceTab('model')", tone: "primary" }],
    });
  }
  if (failedJobs) {
    items.push({
      title: "先处理失败任务",
      detail: `${failedJobs} 个任务失败或已停止。先回看输出和错误，再决定是否重试或改节点配置。`,
      buttons: [{ label: "查看运行记录", action: "switchWorkspaceTab('runs')", tone: "primary" }],
    });
  }
  if (!jobs.length && workspace?.id) {
    items.push({
      title: "先跑自动发现链",
      detail: "先让系统探测路径、数据集、环境清单、GPU 和产物入口，把证据接回节点详情，再决定是否完整运行。",
      buttons: [
        { label: "自动推进", action: "advanceWorkspaceAutomation()", tone: "primary" },
        { label: "自动发现", action: "runWorkspaceDiscovery()", tone: "secondary" },
      ],
    });
  }
  if (!jobs.length && workspace?.id && runCommand) {
    items.push({
      title: "跑一轮 starter chain",
      detail: "项目已经有保存记录，也看到了运行入口，现在最值得做的是跑一轮，把真实输出接回工作流。",
      buttons: [
        { label: "自动推进", action: "advanceWorkspaceAutomation()", tone: "primary" },
        { label: "检查节点链", action: "switchWorkspaceTab('workflow')", tone: "secondary" },
      ],
    });
  }
  if (activeJobs) {
    items.push({
      title: "盯住当前活跃任务",
      detail: `${activeJobs} 个任务正在等待、启动或运行。先看运行记录和输出，不急着继续堆配置。`,
      buttons: [
        { label: "查看运行记录", action: "switchWorkspaceTab('runs')", tone: "primary" },
        { label: "打开对话", action: "switchWorkspaceTab('chat')", tone: "secondary" },
      ],
    });
  }
  if (!items.length) {
    items.push({
      title: "继续推进工作链",
      detail: "当前项目已经有基本结构，可以在对话里补更多上下文，或者继续细化 Agent 与工具边界。",
      buttons: [
        { label: "自动推进", action: "advanceWorkspaceAutomation()", tone: "primary" },
        { label: "管理 Agent", action: "switchWorkspaceTab('agents')", tone: "secondary" },
      ],
    });
  }
  return items.slice(0, 3);
}

function renderWorkspaceHome() {
  const workspace = selectedWorkspace();
  const formData = workspaceFormPayload();
  const summary = $("workspaceHomeSummary");
  const actions = $("workspaceHomeActions");
  const brief = $("workspaceHomeBrief");
  const flow = $("workspaceHomeFlow");
  const readiness = $("workspaceHomeReadiness");
  const resourcesPanel = $("workspaceHomeResources");
  const topology = $("workspaceHomeTopology");
  const runs = $("workspaceHomeRuns");
  const quick = $("workspaceHomeQuickLinks");
  if (!summary || !actions || !brief || !flow || !readiness || !resourcesPanel || !topology || !runs || !quick) return;
  const jobs = workspaceJobs();
  const activeJobs = jobs.filter((job) => isJobActive(job)).length;
  const doneJobs = jobs.filter((job) => String(job.status || "") === "done").length;
  const failedJobs = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  const referenceCount = parseLineList(formData.references || "").length || (Array.isArray(workspace?.references) ? workspace.references.length : 0);
  const sourceType = String(formData.source_type || workspace?.source?.type || "idea");
  const sourceSummary = workspaceDraftSourceSummary(formData, workspace);
  const statusValue = String(formData.status || workspace?.status || "draft");
  const profile = providerProfileById(state.workspaceModelDraft.provider_profile_id);
  const chatAgent = workspaceAgentById(state.workspaceModelDraft.chat_agent_id)?.name || "项目默认 Agent";
  const enabledAgents = state.workspaceAgentsDraft.filter((agent) => agent.enabled !== false).length;
  const enabledTools = state.workspaceToolsDraft.filter((tool) => tool.enabled !== false).length;
  const quickLinks = [
    { title: "项目设置", meta: "目标、来源、目录和环境", action: "switchWorkspaceTab('project')" },
    { title: "工作流", meta: "节点链、交接和运行入口", action: "switchWorkspaceTab('workflow')" },
    { title: "对话", meta: "把自然语言上下文沉淀进项目", action: "switchWorkspaceTab('chat')" },
    { title: "Agent 管理", meta: "角色、提示词和模型覆盖", action: "switchWorkspaceTab('agents')" },
    { title: "工具注册", meta: "工具边界和 allowlist", action: "switchWorkspaceTab('tools')" },
    { title: "AI 配置", meta: "Provider Profile 和路由", action: "switchWorkspaceTab('model')" },
    { title: "运行记录", meta: "输出、失败、重试和追踪", action: "switchWorkspaceTab('runs')" },
    { title: "执行面板", meta: "单命令、批量和传输", action: "switchProductTab('exec'); switchExecTab('job')" },
  ];
  summary.innerHTML = `
    <article class="workspace-home-card">
      <span class="workspace-home-card-label">项目状态</span>
      <strong>${escapeHtml(workspaceStatusLabel(statusValue))}</strong>
      <span class="workspace-home-card-meta">${workspace?.id ? `已保存为 ${escapeHtml(workspace.id)}` : "当前还是未保存草稿"}</span>
    </article>
    <article class="workspace-home-card">
      <span class="workspace-home-card-label">输入来源</span>
      <strong>${escapeHtml(workspaceSourceTypeLabel(sourceType))}</strong>
      <span class="workspace-home-card-meta" title="${escapeHtml(sourceSummary)}">${escapeHtml(sourceSummary)}</span>
    </article>
    <article class="workspace-home-card">
      <span class="workspace-home-card-label">编排规模</span>
      <strong>${state.workspaceNodesDraft.length} / ${enabledAgents} / ${enabledTools}</strong>
      <span class="workspace-home-card-meta">节点 / 启用 Agent / 启用工具</span>
    </article>
    <article class="workspace-home-card">
      <span class="workspace-home-card-label">运行情况</span>
      <strong>${jobs.length}</strong>
      <span class="workspace-home-card-meta">${activeJobs} 活跃 · ${doneJobs} 完成 · ${failedJobs} 异常</span>
    </article>
  `;
  actions.innerHTML = workspaceHomeRecommendations().map((item) => `
    <article class="workspace-home-action-card">
      <div class="workspace-home-action-head">
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <p class="workspace-home-action-detail">${escapeHtml(item.detail)}</p>
        </div>
        <div class="workspace-home-action-buttons">
          ${(item.buttons || []).map((button) => `
            <button class="${button.tone === "primary" ? "primary" : "secondary"} mini" type="button" onclick="${escapeHtml(button.action)}" title="${escapeHtml(item.detail || button.label || "执行建议动作")}">
              ${escapeHtml(button.label)}
            </button>
          `).join("")}
        </div>
      </div>
    </article>
  `).join("");
  brief.innerHTML = `
    <div class="workspace-home-brief-main">${escapeHtml(String(formData.brief || workspace?.brief || "还没有项目简报。先写目标、成功标准和限制条件。").trim() || "还没有项目简报。先写目标、成功标准和限制条件。")}</div>
    <div class="workspace-home-keyfacts">
      <article class="workspace-home-fact">
        <span>工作目录</span>
        <strong>${escapeHtml(String(formData.workspace_dir || workspace?.workspace_dir || "").trim() || "未设置")}</strong>
        <em>节点默认会继承这里</em>
      </article>
      <article class="workspace-home-fact">
        <span>运行环境</span>
        <strong>${escapeHtml(String(formData.env_name || workspace?.env?.name || "").trim() || "未设置")}</strong>
        <em>${escapeHtml(String(formData.env_manager || workspace?.env?.manager || "conda"))}</em>
      </article>
      <article class="workspace-home-fact">
        <span>参考资料</span>
        <strong>${referenceCount}</strong>
        <em>条 URL / 路径 / 备注</em>
      </article>
      <article class="workspace-home-fact">
        <span>模型路由</span>
        <strong>${escapeHtml(profile ? providerProfileLabel(profile) : "未配置 profile")}</strong>
        <em>聊天默认 ${escapeHtml(chatAgent)}</em>
      </article>
    </div>
  `;
  if (!state.workspaceNodesDraft.length) {
    flow.innerHTML = '<div class="empty">还没有节点。先在项目设置里补输入来源，或去工作流重建 starter chain。</div>';
  } else {
    flow.innerHTML = `
      <div class="workspace-home-flow-list">
        ${state.workspaceNodesDraft.slice(0, 8).map((node, index) => `
          <button class="workspace-home-node" type="button" onclick="switchWorkspaceTab('workflow'); selectWorkspaceNode('${escapeHtml(node.id)}')" title="打开工作流配置并选中这个节点">
            <div class="workspace-home-node-head">
              <strong>${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</strong>
              <span class="server-badge subtle">${index + 1}</span>
            </div>
            <div class="workspace-home-node-meta">${escapeHtml(workspaceNodeLabel(node.kind))} · ${escapeHtml(node.handler?.agent_id || node.handler?.name || node.handler?.mode || "未指定执行者")}</div>
            <div class="workspace-home-node-detail" title="${escapeHtml(workspaceNodeSummary(node))}">${escapeHtml(workspaceNodeSummary(node))}</div>
          </button>
        `).join("")}
      </div>
      ${state.workspaceNodesDraft.length > 8 ? `<div class="workspace-home-note">还有 ${escapeHtml(String(state.workspaceNodesDraft.length - 8))} 个节点，进入工作流页查看完整链路。</div>` : ""}
    `;
  }
  readiness.innerHTML = workspaceAutomationExecutionReadinessMarkup(workspace, { limit: 6 });
  resourcesPanel.innerHTML = workspaceAutomationResourceMarkup(workspace, { limit: 6 });
  topology.innerHTML = workspaceAutomationAgentTopologyMarkup(workspace, { limit: 6 });
  if (!jobs.length) {
    runs.innerHTML = '<div class="empty">当前项目还没有运行记录。等工作流或运行节点真正提交后，这里会先显示最近结果。</div>';
  } else {
    runs.innerHTML = jobs.slice(0, 3).map((job) => {
      const nodeTitle = String(job.metadata?.node_title || job.metadata?.node_kind || job.kind || "任务");
      const server = serverById(job.server_id);
      const serverText = server?.name || job.server_id || "未分配服务器";
      const createdText = fmtDate(job.started_at || job.created_at || "") || "等待开始";
      return `
        <button class="workspace-run-item" type="button" onclick="showLog('${escapeHtml(job.id)}')" title="打开这条任务的最近输出日志">
          <div class="workspace-run-item-head">
            <div>
              <strong>${escapeHtml(job.name || job.id)}</strong>
              <div class="workspace-run-item-meta">${escapeHtml(nodeTitle)} · ${escapeHtml(serverText)}</div>
            </div>
            <span class="state ${escapeHtml(job.status || "queued")}">${escapeHtml(zhStatus(job.status || "queued"))}</span>
          </div>
          <div class="workspace-run-item-grid">
            <span>开始 ${escapeHtml(createdText)}</span>
            <span>时长 ${escapeHtml(formatDurationMs(jobDurationMs(job)))}</span>
            <span>ID ${escapeHtml(job.id)}</span>
            <span>${escapeHtml(job.kind || "command")}</span>
          </div>
        </button>
      `;
    }).join("");
  }
  quick.innerHTML = quickLinks.map((item) => `
    <button class="workspace-home-quick-card" type="button" onclick="${escapeHtml(item.action)}" title="${escapeHtml(item.meta)}">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.meta)}</span>
    </button>
  `).join("");
}

function setSelectOptions(select, options, selectedValue, emptyLabel = "") {
  if (!select) return;
  const items = emptyLabel ? [{ value: "", label: emptyLabel }, ...options] : options;
  select.innerHTML = items
    .map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`)
    .join("");
  select.value = items.some((item) => item.value === selectedValue) ? selectedValue : items[0]?.value || "";
}

function renderWorkspaceAgentControls() {
  const agentOptions = state.workspaceAgentsDraft.map((agent) => ({
    value: agent.id,
    label: `${agent.name}${agent.enabled === false ? "（停用）" : ""}`,
  }));
  setSelectOptions($("workspaceChatAgentSelect"), agentOptions, state.workspaceModelDraft.chat_agent_id, "项目默认 Agent");
  setSelectOptions($("workspaceModelChatAgentSelect"), agentOptions, state.workspaceModelDraft.chat_agent_id, "项目默认 Agent");
  const modelOptions = state.providerProfiles.map((profile) => ({
    value: profile.id,
    label: providerProfileLabel(profile),
  }));
  setSelectOptions($("workspaceModelProfileSelect"), modelOptions, state.workspaceModelDraft.provider_profile_id, "不指定 profile");
}

function switchWorkspaceTab(tab, options = {}) {
  // Simplified to 4 tabs: home, config, agents, runs
  const validTabs = ["home", "config", "agents", "runs"];
  // Map old tab names to new ones for backward compatibility
  const tabMap = {
    "project": "config",
    "workflow": "config",
    "model": "config",
    "chat": "runs",
    "tools": "agents",
  };
  const next = validTabs.includes(tab) ? tab : (tabMap[tab] || "home");
  const changed = state.ui.workspaceTab !== next;
  state.ui.workspaceTab = next;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();

  // Show/hide panels based on new structure
  const homePanel = $("workspaceHomePanel");
  const projectPanel = $("workspaceProjectPanel");
  const workflowPanel = $("workspaceWorkflowPanel");
  const chatPanel = $("workspaceChatPanel");
  const agentsPanel = $("workspaceAgentsPanel");
  const toolsPanel = $("workspaceToolsPanel");
  const modelPanel = $("workspaceModelPanel");
  const runsPanel = $("workspaceRunsPanel");

  // Home panel
  if (homePanel) homePanel.hidden = next !== "home";

  // Config panel (combine project, workflow, model)
  if (projectPanel) projectPanel.hidden = next !== "config";
  if (workflowPanel) workflowPanel.hidden = next !== "config";
  if (modelPanel) modelPanel.hidden = next !== "config";

  // Agents panel (combine agents, tools)
  if (agentsPanel) agentsPanel.hidden = next !== "agents";
  if (toolsPanel) toolsPanel.hidden = next !== "agents";

  // Runs panel (combine runs, chat)
  if (runsPanel) runsPanel.hidden = next !== "runs";
  if (chatPanel) chatPanel.hidden = next !== "runs";

  setActiveTab("workspaceTabs", next);
  setActiveTab("workspaceModuleCards", next);
  if (options.persist !== false) saveStoredValue(STORAGE_KEYS.workspaceTab, next);
}

function renderWorkspaceChat() {
  const list = $("workspaceChatList");
  const hint = $("workspaceChatHint");
  if (!list) return;
  const workspace = selectedWorkspace();
  const messages = Array.isArray(workspace?.chat) ? workspace.chat.map((item, index) => normalizeWorkspaceChatMessage(item, index)) : [];
  if (!workspace?.id) {
    list.innerHTML = '<div class="empty">先保存一个项目，再把聊天记录挂到项目上下文里。</div>';
    if (hint) hint.textContent = "未保存项目";
    return;
  }
  if (!messages.length) {
    list.innerHTML = '<div class="empty">还没有对话。可以直接补需求、问下一步，或者指定某个 agent 接手。</div>';
  } else {
    list.innerHTML = messages.map((message) => {
      const agentText = message.agent_name || workspaceAgentById(message.agent_id)?.name || "";
      const title = message.role === "assistant"
        ? `Assistant${agentText ? ` · ${agentText}` : ""}`
        : message.role === "system"
          ? "System"
          : `你${agentText ? ` · 指派 ${agentText}` : ""}`;
      return `
        <article class="workspace-chat-item ${escapeHtml(message.role)}">
          <div class="workspace-chat-head">
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(fmtDate(message.created_at) || message.created_at || "")}</span>
          </div>
          <p class="workspace-chat-text">${escapeHtml(message.text)}</p>
        </article>
      `;
    }).join("");
  }
  if (hint) {
    const agentName = workspaceAgentById(state.workspaceModelDraft.chat_agent_id)?.name || "项目默认 Agent";
    hint.textContent = state.workspaceChatBusy ? "发送中..." : `当前对话路由：${agentName}`;
  }
}

function renderWorkspaceAgentPresets() {
  const root = $("workspaceAgentPresetList");
  if (!root) return;
  const starterRoles = recommendedRoleIdsForCurrentStarter();
  const existingRoles = new Set(state.workspaceAgentsDraft.map((agent) => agent.role));
  const cards = workspaceAgentLibraryTemplates(currentWorkspaceSourceType());
  root.innerHTML = cards.map((agent) => {
    const inStarter = starterRoles.has(agent.role);
    const exists = existingRoles.has(agent.role);
    const tools = (agent.tools || []).slice(0, 4)
      .map((toolId) => `<span class="server-badge subtle">${escapeHtml(workspaceToolLabel(toolId, WORKSPACE_TOOL_CATALOG))}</span>`)
      .join("");
    return `
      <article class="workspace-role-card">
        <div class="workspace-role-card-head">
          <div>
            <strong>${escapeHtml(agent.name)}</strong>
            <div class="workspace-role-card-meta">${escapeHtml(agent.role)} · ${inStarter ? "starter chain 推荐" : "扩展角色"}</div>
          </div>
          <button class="secondary mini" type="button" data-action="apply-agent-template" data-role="${escapeHtml(agent.role)}" title="${exists ? "用推荐模板同步这个 Agent 的提示词、工具和模型配置" : "把这个推荐角色加入当前项目 Agent 列表"}">
            ${exists ? "同步模板" : "加入角色"}
          </button>
        </div>
        <p class="workspace-role-card-prompt">${escapeHtml(agent.prompt)}</p>
        <div class="workspace-role-card-tools">${tools || '<span class="muted">无预设工具</span>'}</div>
      </article>
    `;
  }).join("");
}

function renderWorkspaceAgents() {
  const list = $("workspaceAgentList");
  const editor = $("workspaceAgentEditor");
  const count = $("workspaceAgentCount");
  if (count) count.textContent = `${state.workspaceAgentsDraft.length} 个 agent`;
  renderWorkspaceAgentPresets();
  if (list) {
    if (!state.workspaceAgentsDraft.length) {
      list.innerHTML = '<div class="empty">还没有 agent。</div>';
    } else {
      list.innerHTML = `
        <div class="workspace-agent-stack">
          ${state.workspaceAgentsDraft.map((agent) => {
            const active = agent.id === state.selectedWorkspaceAgentId ? " active" : "";
            const tools = agent.tools.slice(0, 4).map((tool) => `<span class="server-badge subtle">${escapeHtml(workspaceToolLabel(tool))}</span>`).join("");
            const profile = providerProfileById(agent.provider_profile_id);
            return `
              <button class="workspace-agent-card${active}" type="button" data-action="select-workspace-agent" data-agent-id="${escapeHtml(agent.id)}" title="选择这个 Agent，编辑角色、提示词、工具和模型覆盖">
                <div class="workspace-agent-head">
                  <strong>${escapeHtml(agent.name)}</strong>
                  <span class="state ${agent.enabled === false ? "blocked" : "idle"}">${agent.enabled === false ? "停用" : "启用"}</span>
                </div>
                <div class="workspace-agent-meta">${escapeHtml(agent.role || "未设角色")}</div>
                <div class="workspace-agent-meta">${escapeHtml(profile ? providerProfileLabel(profile) : "继承项目默认模型")}</div>
                <div class="workspace-agent-tools">${tools || '<span class="muted">还没配工具</span>'}</div>
              </button>
            `;
          }).join("")}
        </div>
      `;
    }
  }
  if (!editor) return;
  const agent = selectedWorkspaceAgent();
  if (!agent) {
    editor.innerHTML = '<div class="empty">选择一个 agent 后，在这里编辑提示词、工具和模型覆盖。</div>';
    return;
  }
  ensureWorkspaceAgentDebugState(agent);
  const debugState = state.workspaceAgentDebug;
  const profileOptions = [
    { value: "", label: "继承项目默认模型" },
    ...state.providerProfiles.map((profile) => ({
      value: profile.id,
      label: providerProfileLabel(profile),
    })),
  ];
  editor.innerHTML = `
    <div class="workspace-node-editor-card">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(agent.name)}</h4>
          <p class="muted">这个 agent 会被节点、聊天和后续自动路由引用。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="run-workspace-agent-debug" data-agent-id="${escapeHtml(agent.id)}" title="用当前调试输入运行这个 Agent 的调试流程，不提交任务队列">
            ${debugState.busy ? "调试中..." : "调试 Agent"}
          </button>
          <button class="secondary mini danger" type="button" data-action="remove-workspace-agent" data-agent-id="${escapeHtml(agent.id)}" title="从当前项目实例移除这个 Agent，并清理节点上的引用">删除 Agent</button>
        </div>
      </div>
      <div class="workspace-agent-editor-grid">
        <label>
          名称
          <input data-agent-field="name" value="${escapeHtml(agent.name)}" placeholder="Planner / Researcher / Repo Scout / GPU Scout" />
        </label>
        <label>
          角色
          <input data-agent-field="role" value="${escapeHtml(agent.role)}" placeholder="planner / researcher / runner" />
        </label>
        <label>
          模型覆盖
          <select data-agent-field="provider_profile_id">
            ${profileOptions.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === agent.provider_profile_id ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        </label>
        <label class="check">
          <input data-agent-checkbox="enabled" type="checkbox" ${agent.enabled === false ? "" : "checked"} />
          启用这个 agent
        </label>
      </div>
        <label>
          提示词
          <textarea data-agent-field="prompt" rows="5" placeholder="这个 agent 应该如何理解任务、产出什么">${escapeHtml(agent.prompt)}</textarea>
        </label>
        <label>
          可用工具
          <textarea data-agent-field="tools" rows="4" placeholder="用逗号分隔，例如 web.search, artifact.write, job.run">${escapeHtml(agent.tools.join(", "))}</textarea>
        </label>
        <div class="workspace-agent-toolbox">
          <div class="subsection-head">
            <strong>工具库</strong>
            <span class="muted">勾选会同步到上方工具列表。</span>
          </div>
          <div class="workspace-agent-tool-groups">
            ${workspaceToolsByCategory(state.workspaceToolsDraft)
              .map(({ category, label, items }) => `
                <details class="workspace-tool-group" open>
                  <summary>
                    <span>${escapeHtml(label)}</span>
                    <strong>${items.length}</strong>
                  </summary>
                  <div class="workspace-tool-checklist">
                    ${items.map((tool) => `
                      <label class="workspace-tool-check">
                        <input
                          type="checkbox"
                          data-agent-tool-toggle="1"
                          data-tool-id="${escapeHtml(tool.id)}"
                          ${agent.tools.includes(tool.id) ? "checked" : ""}
                        />
                        <span>
                          <strong>${escapeHtml(tool.label)}</strong>
                          <em>${escapeHtml(tool.description || tool.id)}</em>
                        </span>
                      </label>
                    `).join("")}
                  </div>
                </details>
              `).join("")}
          </div>
        </div>
        <div class="workspace-agent-debug-panel">
          <div class="subsection-head">
            <strong>Agent 调试</strong>
            <span class="muted">先看 prompt、工具边界和计划草稿，再接真实模型。</span>
          </div>
          <div class="workspace-agent-debug-toolbar">
            <button class="secondary mini" type="button" data-action="prefill-workspace-agent-debug" title="用当前项目、目标和选中节点生成一段调试输入">填入当前项目上下文</button>
            <button class="primary mini" type="button" data-action="run-workspace-agent-debug" data-agent-id="${escapeHtml(agent.id)}" title="运行 Agent 调试，查看计划草稿、工具边界和下一步建议">
              ${debugState.busy ? "调试中..." : "运行调试"}
            </button>
          </div>
          <label>
            调试输入
            <textarea data-agent-debug-input="1" rows="5" placeholder="例如：先判断这个仓库应该怎么拆节点、需要哪些工具、下一步先做什么">${escapeHtml(debugState.input || "")}</textarea>
          </label>
          ${debugState.error ? `<p class="form-message error">${escapeHtml(debugState.error)}</p>` : ""}
          ${debugState.result ? workspaceAgentDebugResultMarkup(debugState.result) : '<div class="empty">输入一段任务描述后运行调试，这里会展示当前 Agent 的上下文、工具、计划和下一步建议。</div>'}
        </div>
      </div>
  `;
}

function renderWorkspaceToolCatalogSummary() {
  const root = $("workspaceToolCatalogSummary");
  if (!root) return;
  const missingCount = recommendedToolMissingCount();
  const catalogGroups = workspaceToolsByCategory(WORKSPACE_TOOL_CATALOG);
  const currentGroups = workspaceToolsByCategory(state.workspaceToolsDraft);
  const matchedCount = WORKSPACE_TOOL_CATALOG.length - missingCount;
  root.innerHTML = `
    <article class="workspace-tool-summary-card">
      <span class="workspace-tool-summary-label">推荐工具库</span>
      <strong>${matchedCount} / ${WORKSPACE_TOOL_CATALOG.length}</strong>
      <span class="workspace-tool-summary-meta">${missingCount ? `还缺 ${missingCount} 个系统工具` : "系统工具已经完整"}</span>
    </article>
    <article class="workspace-tool-summary-card">
      <span class="workspace-tool-summary-label">当前工具</span>
      <strong>${state.workspaceToolsDraft.length}</strong>
      <span class="workspace-tool-summary-meta">${currentGroups.length} / ${catalogGroups.length} 个类别已经可分配给 Agent</span>
    </article>
    <article class="workspace-tool-summary-chip-row">
      ${catalogGroups.map((group) => {
        const current = currentGroups.find((item) => item.category === group.category);
        return `<span class="workspace-tool-summary-chip">${escapeHtml(group.label)} ${current?.items.length || 0}/${group.items.length}</span>`;
      }).join("")}
    </article>
  `;
}

function renderWorkspaceTools() {
  const list = $("workspaceToolList");
  const editor = $("workspaceToolEditor");
  const count = $("workspaceToolCount");
  if (count) count.textContent = `${state.workspaceToolsDraft.length} 个工具`;
  renderWorkspaceToolCatalogSummary();
  if (list) {
    if (!state.workspaceToolsDraft.length) {
      list.innerHTML = '<div class="empty">还没有工具。</div>';
    } else {
      list.innerHTML = `
        <div class="workspace-tool-stack">
          ${state.workspaceToolsDraft.map((tool) => {
            const active = tool.id === state.selectedWorkspaceToolId ? " active" : "";
            const enabled = tool.enabled === false ? "blocked" : "idle";
            return `
              <button class="workspace-tool-card${active}" type="button" data-action="select-workspace-tool" data-tool-id="${escapeHtml(tool.id)}" title="选择这个工具，编辑类别、能力边界和描述">
                <div class="workspace-tool-head">
                  <strong>${escapeHtml(tool.label)}</strong>
                  <span class="state ${enabled}">${tool.enabled === false ? "停用" : "启用"}</span>
                </div>
                <div class="workspace-tool-meta">${escapeHtml(tool.id)}</div>
                <div class="workspace-tool-meta">${escapeHtml(workspaceToolCategoryLabel(tool.category))} · ${escapeHtml(tool.capability || "read")}</div>
                <div class="workspace-tool-desc">${escapeHtml(tool.description || "未填写描述")}</div>
              </button>
            `;
          }).join("")}
        </div>
      `;
    }
  }
  if (!editor) return;
  const tool = selectedWorkspaceTool();
  if (!tool) {
    editor.innerHTML = '<div class="empty">选择一个工具后，在这里编辑标签、类别和描述。</div>';
    return;
  }
  const categoryOptions = [
    { value: "workflow", label: "workflow / 工作流" },
    { value: "research", label: "research / 检索" },
    { value: "repo", label: "repo / 仓库" },
    { value: "file", label: "file / 文件" },
    { value: "host", label: "host / 主机" },
    { value: "gpu", label: "gpu / GPU" },
    { value: "env", label: "env / 环境" },
    { value: "run", label: "run / 运行" },
    { value: "log", label: "log / 日志" },
    { value: "artifact", label: "artifact / 产物" },
    { value: "notify", label: "notify / 通知" },
    { value: "chat", label: "chat / 对话" },
    { value: "general", label: "general / 通用" },
    { value: "custom", label: "custom / 自定义" },
  ];
  const capabilityOptions = [
    { value: "read", label: "read / 读取" },
    { value: "write", label: "write / 写入" },
    { value: "execute", label: "execute / 执行" },
    { value: "control", label: "control / 控制" },
    { value: "observe", label: "observe / 观察" },
  ];
  editor.innerHTML = `
    <div class="workspace-node-editor-card">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(tool.label)}</h4>
          <p class="muted">工具 registry 会被 agent 复用，决定可调用能力的边界。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="add-workspace-tool" title="在当前项目实例里新增一条工具定义">新增工具</button>
          <button class="secondary mini danger" type="button" data-action="remove-workspace-tool" data-tool-id="${escapeHtml(tool.id)}" title="从当前项目实例移除这个工具，并从 Agent allowlist 中清理引用">删除工具</button>
        </div>
      </div>
      <div class="workspace-tool-editor-grid">
        <label>
          工具 ID
          <input data-tool-field="id" value="${escapeHtml(tool.id)}" placeholder="workflow.plan" />
        </label>
        <label>
          显示名
          <input data-tool-field="label" value="${escapeHtml(tool.label)}" placeholder="工作流规划" />
        </label>
        <label>
          类别
          <select data-tool-field="category">
            ${categoryOptions.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === tool.category ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        </label>
        <label>
          能力
          <select data-tool-field="capability">
            ${capabilityOptions.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === tool.capability ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        </label>
      </div>
      <label>
        描述
        <textarea data-tool-field="description" rows="4" placeholder="这个工具适合做什么">${escapeHtml(tool.description || "")}</textarea>
      </label>
      <label>
        备注
        <textarea data-tool-field="notes" rows="3" placeholder="可以写调用约束、审批点或实现提示">${escapeHtml(tool.notes || "")}</textarea>
      </label>
      <label class="check">
        <input data-tool-checkbox="enabled" type="checkbox" ${tool.enabled === false ? "" : "checked"} />
        启用这个工具
      </label>
      <div class="workspace-tool-summary">${escapeHtml(workspaceToolSummary(tool))}</div>
    </div>
  `;
}

function renderWorkspaceModel() {
  renderWorkspaceAgentControls();
  const profileCount = $("workspaceProviderCount");
  if (profileCount) profileCount.textContent = `${state.providerProfiles.length} 个 profile`;
  const profileList = $("providerProfileList");
  if (profileList) {
    if (!state.providerProfiles.length) {
      profileList.innerHTML = '<div class="empty">还没有本地模型 profile。先加一个厂商 / base URL / model / API key 组合。</div>';
    } else {
      profileList.innerHTML = `
        <div class="workspace-provider-stack">
          ${state.providerProfiles.map((profile) => {
            const active = profile.id === state.selectedProviderProfileId ? " active" : "";
            return `
              <button class="workspace-provider-card${active}" type="button" data-action="select-provider-profile" data-profile-id="${escapeHtml(profile.id)}" title="选择这个 Provider Profile，编辑模型、Base URL 和 API key">
                <div class="workspace-provider-head">
                  <strong>${escapeHtml(profile.label)}</strong>
                  <span class="server-badge subtle">${escapeHtml(PROVIDER_VENDOR_OPTIONS.find((item) => item.value === profile.vendor)?.label || profile.vendor)}</span>
                </div>
                <div class="workspace-provider-meta">${escapeHtml(profile.model || "未设置模型")}</div>
                <div class="workspace-provider-meta">${escapeHtml(profile.base_url || "默认 base URL")}</div>
                <div class="workspace-provider-secret">${escapeHtml(maskSecret(profile.api_key))}</div>
              </button>
            `;
          }).join("")}
        </div>
      `;
    }
  }
  const editor = $("providerProfileEditor");
  if (editor) {
    const profile = selectedProviderProfile();
    if (!profile) {
      editor.innerHTML = '<div class="empty">选择一个 profile 后，在这里编辑本地 API 配置。</div>';
    } else {
      editor.innerHTML = `
        <div class="workspace-node-editor-card">
          <div class="workspace-node-editor-head">
            <div>
              <h4>${escapeHtml(profile.label)}</h4>
              <p class="muted">API key 只保存在当前浏览器 localStorage，不会写入项目。</p>
            </div>
            <div class="workspace-node-editor-actions">
              <button class="secondary mini danger" type="button" data-action="remove-provider-profile" data-profile-id="${escapeHtml(profile.id)}" title="删除这个本地 Provider Profile，并清理当前项目中的引用">删除 Profile</button>
            </div>
          </div>
          <div class="workspace-provider-editor-grid">
            <label>
              显示名
              <input data-provider-field="label" value="${escapeHtml(profile.label)}" placeholder="OpenAI Main / DeepSeek Lab" />
            </label>
            <label>
              厂商
              <select data-provider-field="vendor">
                ${PROVIDER_VENDOR_OPTIONS.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === profile.vendor ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
              </select>
            </label>
            <label>
              Base URL
              <input data-provider-field="base_url" value="${escapeHtml(profile.base_url)}" placeholder="https://api.openai.com/v1" />
            </label>
            <label>
              Model
              <input data-provider-field="model" value="${escapeHtml(profile.model)}" placeholder="gpt-4.1 / claude / deepseek-chat" />
            </label>
          </div>
          <label>
            API Key
            <input data-provider-field="api_key" value="${escapeHtml(profile.api_key)}" placeholder="sk-..." />
          </label>
        </div>
      `;
    }
  }
  if ($("workspaceModelRoutingSelect")) $("workspaceModelRoutingSelect").value = state.workspaceModelDraft.routing_mode || "workspace_default";
  if ($("workspaceModelNotes")) $("workspaceModelNotes").value = state.workspaceModelDraft.notes || "";
  if ($("workspaceModelProfileSelect")) $("workspaceModelProfileSelect").value = state.workspaceModelDraft.provider_profile_id || "";
  if ($("workspaceModelChatAgentSelect")) $("workspaceModelChatAgentSelect").value = state.workspaceModelDraft.chat_agent_id || "";
}

function renderWorkspaceRuns() {
  const workspace = selectedWorkspace();
  const meta = $("workspaceRunMeta");
  const summary = $("workspaceRunSummary");
  const list = $("workspaceRunList");
  if (!meta || !summary || !list) return;
  if (!workspace?.id) {
    meta.textContent = "未保存项目";
    summary.innerHTML = "";
    list.innerHTML = '<div class="empty">先保存项目，后续节点任务和执行日志才会绑定到这里。</div>';
    return;
  }
  const jobs = workspaceJobs();
  const activeCount = jobs.filter((job) => isJobActive(job)).length;
  const doneCount = jobs.filter((job) => String(job.status || "") === "done").length;
  const failedCount = jobs.filter((job) => ["failed", "stopped"].includes(String(job.status || ""))).length;
  const latest = jobs[0] || null;
  meta.textContent = `${jobs.length} 个任务`;
  summary.innerHTML = `
    <article class="workspace-run-summary-card">
      <span class="workspace-run-summary-label">总任务</span>
      <strong>${jobs.length}</strong>
      <span class="workspace-run-summary-meta">当前项目已绑定的节点执行</span>
    </article>
    <article class="workspace-run-summary-card">
      <span class="workspace-run-summary-label">活跃中</span>
      <strong>${activeCount}</strong>
      <span class="workspace-run-summary-meta">等待、启动中、运行中</span>
    </article>
    <article class="workspace-run-summary-card">
      <span class="workspace-run-summary-label">已完成</span>
      <strong>${doneCount}</strong>
      <span class="workspace-run-summary-meta">最近跑完的节点任务</span>
    </article>
    <article class="workspace-run-summary-card">
      <span class="workspace-run-summary-label">异常</span>
      <strong>${failedCount}</strong>
      <span class="workspace-run-summary-meta">${latest ? `最近一次 ${fmtDate(latest.created_at || latest.started_at || "")}` : "还没有执行记录"}</span>
    </article>
  `;
  if (!jobs.length) {
    list.innerHTML = '<div class="empty">当前项目还没有绑定任务。可以从工作流运行节点，或者把运行节点填入执行面板后提交。</div>';
    return;
  }
  list.innerHTML = jobs.slice(0, 24).map((job) => {
    const nodeTitle = String(job.metadata?.node_title || job.metadata?.node_kind || job.kind || "任务");
    const server = serverById(job.server_id);
    const serverText = server?.name || job.server_id || "未分配服务器";
    const durationText = formatDurationMs(jobDurationMs(job));
    const canStop = ["queued", "blocked", "starting", "running"].includes(String(job.status || ""));
    const createdText = fmtDate(job.started_at || job.created_at || "") || "等待开始";
    const errorText = String(job.error || "").trim();
    const commandText = String(job.command_display || job.command || "").trim();
    return `
      <article class="workspace-run-item" role="button" tabindex="0" data-job-id="${escapeHtml(job.id)}">
        <div class="workspace-run-item-head">
          <div>
            <strong>${escapeHtml(job.name || job.id)}</strong>
            <div class="workspace-run-item-meta">${escapeHtml(nodeTitle)} · ${escapeHtml(serverText)}${job.gpu_index === "auto" || job.gpu_index === "" || job.gpu_index === undefined ? "" : ` · GPU ${escapeHtml(String(job.gpu_index))}`}</div>
          </div>
          <span class="state ${escapeHtml(job.status || "queued")}">${escapeHtml(zhStatus(job.status || "queued"))}</span>
        </div>
        <div class="workspace-run-item-grid">
          <span>开始 ${escapeHtml(createdText)}</span>
          <span>时长 ${escapeHtml(durationText)}</span>
          <span>ID ${escapeHtml(job.id)}</span>
          <span>${escapeHtml(job.kind || "command")}</span>
        </div>
        ${commandText ? `<div class="workspace-run-item-command" title="${escapeHtml(commandText)}">${escapeHtml(commandText)}</div>` : ""}
        ${errorText ? `<div class="workspace-run-item-error" title="${escapeHtml(errorText)}">${escapeHtml(errorText)}</div>` : ""}
        <div class="workspace-run-item-actions">
          <button class="secondary mini" type="button" data-action="open-workspace-run" data-job-id="${escapeHtml(job.id)}" title="打开这条运行记录的输出日志">打开输出</button>
          ${canStop ? `<button class="secondary mini danger" type="button" data-action="stop-workspace-run" data-job-id="${escapeHtml(job.id)}" title="停止这条任务；不会删除运行记录">停止</button>` : ""}
          ${!canStop ? `<button class="secondary mini" type="button" data-action="retry-workspace-run" data-job-id="${escapeHtml(job.id)}" title="复制这条任务配置并重新加入队列">重试</button>` : ""}
          <button class="secondary mini" type="button" data-action="copy-workspace-run" data-job-id="${escapeHtml(job.id)}" title="把这条任务复制成新的待运行任务">复制</button>
        </div>
      </article>
    `;
  }).join("");
}

function renderWorkspacePanels() {
  renderWorkspaceHeader();
  renderWorkspaceModuleCards();
  renderWorkspaceHome();
  renderWorkspaceNodeBuilder();
  renderWorkspaceAgents();
  renderWorkspaceTools();
  renderWorkspaceModel();
  renderWorkspaceChat();
  renderWorkspaceRuns();
  switchWorkspaceTab(state.ui.workspaceTab, { persist: false });
}

function renderWorkspaceNodeBuilder() {
  renderWorkspaceNodeList();
  renderWorkspaceNodeEditor();
}

function setWorkspaceNodesDraft(nodes, options = {}) {
  const formData = options.formData || workspaceFormPayload();
  const list = (Array.isArray(nodes) ? nodes : [])
    .map((node, index) => normalizeWorkspaceDraftNode(node, index, formData))
    .filter(Boolean);
  state.workspaceNodesDraft = list.length ? list : buildWorkspaceStarterNodes(formData);
  const selectedId = String(options.selectedNodeId || state.selectedWorkspaceNodeId || "").trim();
  state.selectedWorkspaceNodeId = state.workspaceNodesDraft.some((node) => node.id === selectedId)
    ? selectedId
    : state.workspaceNodesDraft[0]?.id || "";
  persistWorkspaceNodesDraft();
  if (options.render !== false) renderWorkspacePanels();
}

function selectWorkspaceNode(nodeId, options = {}) {
  const next = state.workspaceNodesDraft.find((node) => node.id === nodeId);
  if (!next) return;
  const changed = state.selectedWorkspaceNodeId !== next.id;
  state.selectedWorkspaceNodeId = next.id;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();
  if (options.syncForm) syncWorkspaceFormFromNode(next);
  if (options.render !== false) renderWorkspacePanels();
}

function syncWorkspaceFormFromNode(node) {
  const form = $("workspaceForm");
  if (!form || !node) return;
  const config = node.config || {};
  const setValue = (name, value) => {
    const field = form.elements.namedItem(name);
    if (!field) return;
    field.value = value ?? "";
  };
  if (node.kind === "source.repo") {
    setValue("source_type", "repo");
    setValue("repo_url", config.repo_url || "");
    setValue("repo_ref", config.repo_ref || "");
  } else if (node.kind === "source.paper") {
    setValue("source_type", "paper");
    setValue("paper_url", config.paper_url || "");
  } else if (node.kind === "source.idea") {
    setValue("source_type", "idea");
    setValue("idea_text", config.idea_text || "");
  } else if (["repo.clone", "path.resolve", "repo.inspect", "dataset.find", "artifact.collect"].includes(node.kind)) {
    if (config.workspace_dir) setValue("workspace_dir", config.workspace_dir);
    if (config.repo_url) setValue("repo_url", config.repo_url);
    if (config.repo_ref) setValue("repo_ref", config.repo_ref);
  } else if (node.kind === "env.infer") {
    setValue("workspace_dir", config.workspace_dir || "");
    setValue("env_name", config.env_name || "");
    setValue("python_version", config.python_version || "");
  } else if (node.kind === "env.prepare") {
    setValue("workspace_dir", config.workspace_dir || "");
    setValue("env_name", config.env_name || "");
    setValue("env_manager", config.env_manager || "conda");
    setValue("python_version", config.python_version || "");
    setValue("setup_command", config.setup_command || "");
  } else if (node.kind === "run.command") {
    if (config.workspace_dir) setValue("workspace_dir", config.workspace_dir);
    if (config.env_name) setValue("env_name", config.env_name);
    setValue("run_command", config.run_command || "");
    setValue("schedule", config.schedule || "");
  } else if (node.kind === "eval.report") {
    setValue("report_command", config.report_command || "");
  }
  toggleWorkspaceSourceFields();
  persistFormState("workspaceForm");
}

function syncWorkspaceNodesFromForm() {
  const formData = workspaceFormPayload();
  const sourceNode = state.workspaceNodesDraft.find((node) => node.kind.startsWith("source."));
  const cloneNode = state.workspaceNodesDraft.find((node) => node.kind === "repo.clone");
  const pathNode = state.workspaceNodesDraft.find((node) => node.kind === "path.resolve");
  const inspectNode = state.workspaceNodesDraft.find((node) => node.kind === "repo.inspect");
  const datasetNode = state.workspaceNodesDraft.find((node) => node.kind === "dataset.find");
  const searchNode = state.workspaceNodesDraft.find((node) => node.kind === "research.search");
  const envInferNode = state.workspaceNodesDraft.find((node) => node.kind === "env.infer");
  const envNode = state.workspaceNodesDraft.find((node) => node.kind === "env.prepare");
  const gpuNode = state.workspaceNodesDraft.find((node) => node.kind === "gpu.allocate");
  const runNode = workspaceRunNode(state.workspaceNodesDraft);
  const artifactNode = state.workspaceNodesDraft.find((node) => node.kind === "artifact.collect");
  const evalNode = state.workspaceNodesDraft.find((node) => node.kind === "eval.report");
  const nextNodes = state.workspaceNodesDraft.map((node, index) => {
    const copy = normalizeWorkspaceDraftNode(node, index, formData);
    if (!copy) return null;
    if (sourceNode && copy.id === sourceNode.id) {
      if (copy.kind === "source.repo") {
        copy.config.repo_url = String(formData.repo_url || "");
        copy.config.repo_ref = String(formData.repo_ref || "");
      } else if (copy.kind === "source.paper") {
        copy.config.paper_url = String(formData.paper_url || "");
      } else if (copy.kind === "source.idea") {
        copy.config.idea_text = String(formData.idea_text || formData.brief || "");
      }
    }
    if (searchNode && copy.id === searchNode.id) {
      copy.config.repo_url = String(formData.repo_url || "");
      copy.config.paper_url = String(formData.paper_url || "");
      copy.config.source_type = String(formData.source_type || "repo");
      if (!String(copy.config.query || "").trim()) copy.config.query = workspaceSearchSeed(formData);
    }
    if (cloneNode && copy.id === cloneNode.id) {
      copy.config.repo_url = String(formData.repo_url || "");
      copy.config.repo_ref = String(formData.repo_ref || "");
      copy.config.workspace_dir = String(formData.workspace_dir || "");
    }
    if (pathNode && copy.id === pathNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
    }
    if (inspectNode && copy.id === inspectNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
    }
    if (datasetNode && copy.id === datasetNode.id) {
      if (!String(copy.config.query || "").trim()) copy.config.query = workspaceSearchSeed(formData);
      copy.config.dataset_hints = String(formData.references || copy.config.dataset_hints || "");
    }
    if (envInferNode && copy.id === envInferNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
      copy.config.env_name = String(formData.env_name || "");
      copy.config.python_version = String(formData.python_version || "");
    }
    if (envNode && copy.id === envNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
      copy.config.env_name = String(formData.env_name || "");
      copy.config.env_manager = String(formData.env_manager || "conda");
      copy.config.python_version = String(formData.python_version || "");
      copy.config.setup_command = String(formData.setup_command || "");
    }
    if (gpuNode && copy.id === gpuNode.id) {
      copy.config.gpu_policy = String(copy.config.gpu_policy || "auto");
    }
    if (runNode && copy.id === runNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
      copy.config.env_name = String(formData.env_name || "");
      copy.config.run_command = String(formData.run_command || "");
      copy.config.schedule = String(formData.schedule || "");
    }
    if (artifactNode && copy.id === artifactNode.id) {
      copy.config.workspace_dir = String(formData.workspace_dir || "");
      copy.config.notes = String(formData.notes || copy.config.notes || "");
    }
    if (evalNode && copy.id === evalNode.id) {
      copy.config.report_command = String(formData.report_command || "");
    }
    return copy;
  }).filter(Boolean);
  state.workspaceNodesDraft = nextNodes;
  persistWorkspaceNodesDraft();
  return nextNodes;
}

function replacePrimarySourceNodeKind(sourceType) {
  const targetKind = `source.${sourceType}`;
  const currentIndex = state.workspaceNodesDraft.findIndex((node) => node.kind.startsWith("source."));
  const formData = workspaceFormPayload();
  if (currentIndex < 0) {
    const nextNodes = [createWorkspaceNode(targetKind, {}, 0, formData), ...state.workspaceNodesDraft];
    setWorkspaceNodesDraft(nextNodes, { selectedNodeId: nextNodes[0].id, formData });
    return;
  }
  const current = state.workspaceNodesDraft[currentIndex];
  const replacement = createWorkspaceNode(targetKind, current, currentIndex, formData);
  state.workspaceNodesDraft.splice(currentIndex, 1, replacement);
  state.selectedWorkspaceNodeId = replacement.id;
  persistWorkspaceNodesDraft();
  renderWorkspacePanels();
}

function clearWorkspaceForm() {
  // Use new defaultWorkspaceForm for smart defaults
  const defaults = defaultWorkspaceForm("repo");
  defaults.workspace_id = "";
  defaults.references = "";

  setWorkspaceFormValues(defaults);
  state.selectedWorkspaceId = "";
  state.selectedWorkspaceNodeId = "";
  saveStoredValue(STORAGE_KEYS.selectedWorkspace, "");
  persistFormState("workspaceForm");
  clearJobSourceBinding();
  setWorkspaceToolsDraft(defaults.tools || defaultWorkspaceTools(), { render: false });
  setWorkspaceAgentsDraft(defaults.agents || defaultWorkspaceAgents(), { render: false });
  setWorkspaceModelDraft(defaults.model || defaultWorkspaceModel(), { render: false });
  setWorkspaceNodesDraft(defaults.nodes || buildWorkspaceStarterNodes(defaults), { formData: defaults });
  clearWorkspaceMessage();
  renderWorkspaces();
  renderWorkspacePanels();
  switchProductTab("workspace");
  switchWorkspaceTab("home");
}

function workspacePayloadForSave() {
  const payload = workspaceFormPayload();
  const nodes = syncWorkspaceNodesFromForm();
  payload.nodes = deepClone(nodes, []);
  payload.links = workspaceLinksFromNodes(nodes);
  payload.references = parseLineList(payload.references || "");
  payload.agents = deepClone(state.workspaceAgentsDraft, []);
  payload.model = deepClone(state.workspaceModelDraft, {});
  payload.chat = deepClone(selectedWorkspace()?.chat || [], []);
  return payload;
}

function selectWorkspace(workspaceId, options = {}) {
  const workspace = workspaceById(workspaceId);
  if (!workspace) return;
  const changed = state.selectedWorkspaceId !== workspace.id;
  state.selectedWorkspaceId = workspace.id;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();
  const executionNodes = Array.isArray(workspace.execution?.nodes) && workspace.execution.nodes.length ? workspace.execution.nodes : (workspace.nodes || []);
  const executionNodeIds = new Set(executionNodes.map((node) => String(node?.id || "")).filter(Boolean));
  const validExecutionNodeId = (nodeId) => {
    const value = String(nodeId || "").trim();
    return value && executionNodeIds.has(value) ? value : "";
  };
  const requestedExecutionNodeId = validExecutionNodeId(options.selectedExecutionNodeId || options.selectedNodeId);
  const savedNodeId = savedWorkspaceExecutionNodeId(workspaceExecutionSelectionKey(workspace));
  state.selectedWorkspaceExecutionNodeId = requestedExecutionNodeId
    || validExecutionNodeId(savedNodeId)
    || validExecutionNodeId(workspace.execution?.current_node_id)
    || validExecutionNodeId(workspace.nodes?.[0]?.id)
    || "";
  saveWorkspaceExecutionNodeSelection(state.selectedWorkspaceExecutionNodeId, workspaceExecutionSelectionKey(workspace));
  saveStoredValue(STORAGE_KEYS.selectedWorkspace, workspace.id);
  hydrateWorkspaceUseInputsFromWorkspace(workspace);
  const recipe = workspaceRecipe(workspace) || {};
  setWorkspaceFormValues({
    workspace_id: workspace.id,
    name: workspace.name || "",
    source_type: workspace.source?.type || "repo",
    brief: workspace.brief || "",
    references: Array.isArray(workspace.references) ? workspace.references.join("\n") : "",
    repo_url: workspace.source?.repo_url || "",
    repo_ref: workspace.source?.repo_ref || "",
    paper_url: workspace.source?.paper_url || "",
    idea_text: workspace.source?.idea_text || "",
    workspace_dir: workspace.workspace_dir || "",
    env_name: workspace.env?.name || "",
    env_manager: workspace.env?.manager || "conda",
    python_version: workspace.env?.python || "",
    setup_command: recipe.setup_command || "",
    run_command: recipe.run_command || "",
    report_command: recipe.report_command || "",
    schedule: recipe.schedule || "",
    tags: (workspace.tags || []).join(","),
    status: workspace.status || "draft",
    notes: workspace.notes || "",
  });
  if (options.persist !== false) persistFormState("workspaceForm");
  setWorkspaceToolsDraft(workspace.tools || [], {
    render: false,
    selectedToolId: options.selectedToolId || workspace.tools?.[0]?.id || "",
  });
  setWorkspaceAgentsDraft(workspace.agents || [], {
    render: false,
    selectedAgentId: options.selectedAgentId || workspace.agents?.[0]?.id || "",
  });
  setWorkspaceModelDraft(workspace.model || {}, { render: false });
  setWorkspaceNodesDraft(workspace.nodes || [], {
    selectedNodeId: options.selectedNodeId || workspace.nodes?.[0]?.id || "",
    formData: workspaceFormPayload(),
    render: false,
  });
  clearWorkspaceMessage();
  renderWorkspaces();
  renderWorkspacePanels();
  renderWorkspaceWorkbench();
  switchProductTab("workspace");
}

function rebuildWorkspaceStarterChain() {
  const formData = workspaceFormPayload();
  const nextNodes = buildWorkspaceStarterNodes(formData);
  setWorkspaceNodesDraft(nextNodes, { selectedNodeId: nextNodes[0]?.id || "", formData });
  const message = $("workspaceMessage");
  if (message) {
    message.textContent = "已按当前工作区信息重建 starter chain。";
    message.classList.remove("error");
  }
}

function insertWorkspaceNode(kind) {
  const selectedId = state.selectedWorkspaceNodeId;
  const currentIndex = state.workspaceNodesDraft.findIndex((node) => node.id === selectedId);
  const insertIndex = currentIndex >= 0 ? currentIndex + 1 : state.workspaceNodesDraft.length;
  const formData = workspaceFormPayload();
  const nextNodes = state.workspaceNodesDraft.slice();
  const node = createWorkspaceNode(String(kind || "custom.step"), {}, insertIndex, formData);
  nextNodes.splice(insertIndex, 0, node);
  setWorkspaceNodesDraft(nextNodes, { selectedNodeId: node.id, formData });
}

function moveWorkspaceNode(nodeId, direction) {
  const index = state.workspaceNodesDraft.findIndex((node) => node.id === nodeId);
  if (index < 0) return;
  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= state.workspaceNodesDraft.length) return;
  const nextNodes = state.workspaceNodesDraft.slice();
  const [node] = nextNodes.splice(index, 1);
  nextNodes.splice(targetIndex, 0, node);
  setWorkspaceNodesDraft(nextNodes, { selectedNodeId: node.id, formData: workspaceFormPayload() });
}

function removeWorkspaceNode(nodeId) {
  if (state.workspaceNodesDraft.length <= 1) {
    const message = $("workspaceMessage");
    if (message) {
      message.textContent = "至少保留一个节点。";
      message.classList.add("error");
    }
    return;
  }
  const nextNodes = state.workspaceNodesDraft.filter((node) => node.id !== nodeId);
  const fallback = nextNodes[Math.max(0, nextNodes.findIndex((node) => node.id === state.selectedWorkspaceNodeId))] || nextNodes[0];
  setWorkspaceNodesDraft(nextNodes, { selectedNodeId: fallback?.id || "", formData: workspaceFormPayload() });
}

function updateSelectedWorkspaceNode(updater) {
  const index = state.workspaceNodesDraft.findIndex((node) => node.id === state.selectedWorkspaceNodeId);
  if (index < 0) return;
  const current = state.workspaceNodesDraft[index];
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  state.workspaceNodesDraft.splice(index, 1, next);
  persistWorkspaceNodesDraft();
  renderWorkspacePanels();
}

function toggleWorkspaceSourceFields() {
  const type = $("workspaceSourceType")?.value || "repo";
  const repoUrl = $("workspaceRepoUrl")?.closest("label");
  const repoRef = $("workspaceRepoRef")?.closest("label");
  const paperUrl = $("workspacePaperUrl")?.closest("label");
  const idea = $("workspaceIdeaText")?.closest("label");
  if (repoUrl) repoUrl.hidden = type === "idea";
  if (repoRef) repoRef.hidden = type !== "repo";
  if (paperUrl) paperUrl.hidden = type === "repo";
  if (idea) idea.hidden = type === "repo";
}

function clearTerminalMessage() {
  const message = $("terminalMessage");
  message.textContent = "";
  message.title = "";
  message.classList.remove("error");
}

function selectServer(id) {
  state.selectedServer = id;
  state.selectedGpu = "auto";
  saveStoredValue(STORAGE_KEYS.selectedServer, id);
  clearTerminalMessage();
  render();
  loadTmuxSessions();
}

function selectGpu(serverId, gpuIndex) {
  state.selectedServer = serverId;
  state.selectedGpu = String(gpuIndex);
  saveStoredValue(STORAGE_KEYS.selectedServer, serverId);
  clearTerminalMessage();
  render();
  loadTmuxSessions();
  scrollGpuSelectionIntoView();
}

function selectedServer() {
  const servers = sortedVisibleServers();
  return servers.find((server) => server.id === state.selectedServer) || servers[0];
}

function selectedServerFromForm() {
  const selectedId = $("serverSelect")?.value || state.selectedServer;
  const server =
    sortedVisibleServers().find((item) => item.id === selectedId) ||
    serverById(selectedId) ||
    selectedServer();
  if (server) state.selectedServer = server.id;
  return server;
}

function selectedTerminalServerFromForm() {
  const selectedId = $("terminalServerSelect")?.value || state.selectedServer;
  return serverById(selectedId) || selectedServer();
}

function isJobActive(job) {
  return ["running", "queued", "starting", "blocked"].includes(String(job?.status || ""));
}

function runningJobCount() {
  return state.jobs.filter((job) => ["running", "starting", "blocked"].includes(job.status)).length;
}

function transferJobCount() {
  return state.jobs.filter((job) => job.kind === "transfer" && isJobActive(job)).length;
}

function idleGpuCount() {
  return allGpus().filter(({ gpu }) => gpu.state === "idle").length;
}

function setActiveTab(containerId, tab) {
  const root = $(containerId);
  if (!root) return;
  root.querySelectorAll("[data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });
}

function switchExecTab(tab, options = {}) {
  const next = ["job", "plan", "transfer"].includes(tab) ? tab : "job";
  const changed = state.ui.execTab !== next;
  state.ui.execTab = next;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();
  $("execJobPanel").hidden = next !== "job";
  $("execPlanPanel").hidden = next !== "plan";
  $("execTransferPanel").hidden = next !== "transfer";
  setActiveTab("execTabs", next);
  if (options.persist !== false) saveStoredValue(STORAGE_KEYS.execTab, next);
}

function switchActivityTab(tab, options = {}) {
  const next = ["tasks", "tmux", "output", "terminal"].includes(tab) ? tab : "tasks";
  const changed = state.ui.activityTab !== next;
  state.ui.activityTab = next;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();
  $("activityTasksPanel").hidden = next !== "tasks";
  $("activityTmuxPanel").hidden = next !== "tmux";
  $("activityConsolePanel").hidden = !["output", "terminal"].includes(next);
  $("terminalLauncher").hidden = next !== "terminal";
  if (options.revealOutput && ["output", "terminal"].includes(next) && (state.outputTabs.length || state.activeOutput)) {
    showLogPane();
  }
  setActiveTab("activityTabs", next);
  if (options.persist !== false) saveStoredValue(STORAGE_KEYS.activityTab, next);
}

function switchProductTab(tab, options = {}) {
  // Support 4 views: console, workspace, exec, activity
  const next = ["console", "workspace", "exec", "activity"].includes(tab) ? tab : "console";
  const changed = state.ui.productTab !== next;
  state.ui.productTab = next;
  if (changed && options.persist !== false) markWorkspaceUiInteraction();

  // Hide all panels first
  const overviewPanel = $("consoleOverviewPanel");
  const monitorPanel = $("consoleMonitorPanel");
  const workspacePanel = $("workspaceHubPanel");
  const execPanel = $("consoleExecPanel");
  const activityPanel = $("consoleActivityPanel");

  if (overviewPanel) overviewPanel.hidden = next !== "console";
  if (monitorPanel) monitorPanel.hidden = next !== "console";
  if (workspacePanel) workspacePanel.hidden = next !== "workspace";
  if (execPanel) execPanel.hidden = next !== "exec";
  if (activityPanel) activityPanel.hidden = next !== "activity";

  // Update navigation buttons in sidebar
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === next);
  });

  if (options.persist !== false) saveStoredValue(STORAGE_KEYS.productTab, next);
}

function renderOverview() {
  $("summaryOnlineServers").textContent = `${connectedServers().length} / ${state.servers.length}`;
  $("summaryIdleGpus").textContent = String(idleGpuCount());
  $("summaryRunningJobs").textContent = String(runningJobCount());
  $("summaryTransferJobs").textContent = String(transferJobCount());
  $("summaryAlertServers").textContent = String(serverAlertCount());
}

function showLogPane() {
  setLogPaneOpen(true);
  setTerminalControlsVisible(state.activeOutput?.type === "terminal");
}

function collapseLogPane() {
  setLogPaneOpen(false);
  setTerminalControlsVisible(false);
}

function showTerminalOutput() {
  const tab = upsertOutputTab({
    type: "terminal",
    terminalId: state.terminal.id,
    title: `终端 · ${state.terminal.serverName || state.terminal.serverId || ""}`,
    content: state.terminal.text || "",
  });
  activateOutputTab(tab.key);
}

function escapeRegExp(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function updateLogSearchControls() {
  const input = $("logSearchInput");
  const count = $("logSearchCount");
  const prev = $("logSearchPrevBtn");
  const next = $("logSearchNextBtn");
  if (input && input.value !== state.logSearch.query) input.value = state.logSearch.query;
  const hits = document.querySelectorAll("#logView .log-hit");
  const total = hits.length;
  const active = total ? Math.max(0, Math.min(state.logSearch.activeIndex, total - 1)) + 1 : 0;
  if (count) count.textContent = `${active} / ${total}`;
  if (prev) prev.disabled = total === 0;
  if (next) next.disabled = total === 0;
}

function focusLogSearchHit(index, options = {}) {
  const hits = Array.from(document.querySelectorAll("#logView .log-hit"));
  if (!hits.length) {
    state.logSearch.activeIndex = -1;
    updateLogSearchControls();
    return;
  }
  const nextIndex = ((index % hits.length) + hits.length) % hits.length;
  state.logSearch.activeIndex = nextIndex;
  hits.forEach((hit, hitIndex) => {
    hit.classList.toggle("active", hitIndex === nextIndex);
  });
  if (options.scroll !== false) {
    hits[nextIndex].scrollIntoView({ block: "center", inline: "nearest" });
  }
  updateLogSearchControls();
}

function setLogText(text, options = {}) {
  const view = $("logView");
  const follow = $("logFollow")?.checked ?? true;
  const wasNearBottom = view.scrollHeight - view.scrollTop - view.clientHeight < 80;
  const source = text || "";
  const query = state.logSearch.query.trim();
  if (!query) {
    state.logSearch.activeIndex = -1;
    view.textContent = source;
  } else {
    const regex = new RegExp(escapeRegExp(query), "gi");
    let html = "";
    let lastIndex = 0;
    let matches = 0;
    for (const match of source.matchAll(regex)) {
      const start = match.index ?? 0;
      const end = start + match[0].length;
      html += escapeHtml(source.slice(lastIndex, start));
      html += `<mark class="log-hit" data-hit-index="${matches}">${escapeHtml(match[0])}</mark>`;
      lastIndex = end;
      matches += 1;
    }
    html += escapeHtml(source.slice(lastIndex));
    view.innerHTML = html;
    if (!matches) {
      state.logSearch.activeIndex = -1;
    } else if (options.keepSearchIndex !== true || state.logSearch.activeIndex < 0 || state.logSearch.activeIndex >= matches) {
      state.logSearch.activeIndex = 0;
    }
    focusLogSearchHit(state.logSearch.activeIndex, { scroll: Boolean(options.focusMatch) });
  }
  if (options.resetX) view.scrollLeft = 0;
  updateLogSearchControls();
  if (options.noAutoScroll) return;
  if (follow || wasNearBottom || options.forceBottom) {
    requestAnimationFrame(() => {
      view.scrollTop = view.scrollHeight;
    });
  }
}

function setLogTitle(text) {
  $("logTitle").textContent = text || "输出";
}

function setLogSearchQuery(query, options = {}) {
  state.logSearch.query = String(query || "");
  saveStoredValue(STORAGE_KEYS.outputSearch, state.logSearch.query);
  if (!options.keepIndex) state.logSearch.activeIndex = -1;
  const content = state.activeOutput?.content || $("logView")?.textContent || "";
  setLogText(content, {
    noAutoScroll: true,
    keepSearchIndex: options.keepIndex === true,
    focusMatch: options.focusMatch === true,
  });
}

function moveLogSearch(step) {
  const hits = document.querySelectorAll("#logView .log-hit");
  if (!hits.length) return;
  const base = state.logSearch.activeIndex < 0 ? 0 : state.logSearch.activeIndex;
  focusLogSearchHit(base + step);
}

function downloadActiveOutput() {
  const text = state.activeOutput?.content || $("logView")?.textContent || "";
  const title = (state.activeOutput?.title || "output").replace(/[^\w.-]+/g, "_");
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${title || "output"}.log`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function outputTabKey(tab) {
  if (tab.key) return tab.key;
  if (tab.type === "job") return `job:${tab.jobId}`;
  if (tab.type === "tmux") return `tmux:${tab.serverId}:${tab.sessionName}`;
  if (tab.type === "process") return `process:${tab.serverId}:${tab.pid}`;
  if (tab.type === "terminal") return `terminal:${tab.terminalId}`;
  return `tab:${Date.now()}`;
}

function upsertOutputTab(tab) {
  const key = outputTabKey(tab);
  const existing = state.outputTabs.find((item) => item.key === key);
  if (existing) {
    Object.assign(existing, tab, { key });
    return existing;
  }
  const next = { ...tab, key, content: tab.content || "" };
  state.outputTabs.push(next);
  return next;
}

function renderOutputTabs() {
  const tabs = $("outputTabs");
  if (!tabs) return;
  if (!state.outputTabs.length) {
    tabs.innerHTML = '<span class="output-tab-placeholder">选择任务、tmux、进程或打开终端。</span>';
    return;
  }
  tabs.innerHTML = state.outputTabs
    .map((tab) => {
      const active = tab.key === state.activeOutputKey ? " active" : "";
      return `
        <div class="output-tab${active}">
          <button class="output-tab-trigger" type="button" title="${escapeHtml(tab.title || "输出")}" onclick="activateOutputTab('${escapeHtml(tab.key)}')">
            <span class="output-tab-label">${escapeHtml(tab.title || "输出")}</span>
          </button>
          <button class="output-tab-close" type="button" title="关闭" onclick="closeOutputTab(event, '${escapeHtml(tab.key)}')">×</button>
        </div>
      `;
    })
    .join("");
}

function setTerminalControlsVisible(visible) {
  document.querySelectorAll(".terminal-only").forEach((item) => {
    item.hidden = !visible;
  });
  $("terminalInputForm").hidden = !visible;
}

function activateOutputTab(key) {
  const tab = state.outputTabs.find((item) => item.key === key);
  if (!tab) return;
  state.activeOutputKey = key;
  state.activeOutput = tab;
  state.selectedJob = tab.type === "job" ? tab.jobId : null;
  state.selectedTmux = tab.type === "tmux" ? tab.sessionName : null;
  if (tab.serverId) state.selectedServer = tab.serverId;
  if (tab.type === "terminal") {
    state.terminal = state.terminals[tab.terminalId] || state.terminal;
  }
  renderJobs();
  renderTmuxSessions();
  renderOutputTabs();
  setLogTitle(tab.title || "输出");
  setLogText(tab.content || "", { resetX: true, forceBottom: tab.type === "terminal" });
  showLogPane();
  if (tab.type === "terminal") {
    startTerminalPoller();
    void pollTerminalOutput();
    $("terminalInput").focus();
  } else if (tab.type === "job" || tab.type === "tmux") {
    void refreshActiveOutput({ forceBottom: true, resetX: true });
  }
}

function closeOutputTab(event, key) {
  consumeClick(event);
  const index = state.outputTabs.findIndex((item) => item.key === key);
  if (index < 0) return;
  const [tab] = state.outputTabs.splice(index, 1);
  if (tab.type === "terminal" && state.terminals[tab.terminalId]) {
    if (state.terminal.id === tab.terminalId) {
      void closeCurrentTerminal({ silent: true });
    } else {
      void fetchJson(`/api/terminal/sessions/${encodeURIComponent(tab.terminalId)}`, {
        method: "DELETE",
      }).catch(() => {});
      delete state.terminals[tab.terminalId];
    }
  }
  if (state.activeOutputKey === key) {
    const next = state.outputTabs[Math.max(index - 1, 0)] || state.outputTabs[0];
    if (next) {
      activateOutputTab(next.key);
    } else {
      clearActiveOutput();
    }
  }
  renderOutputTabs();
}

function clearActiveOutput() {
  state.activeOutput = null;
  state.activeOutputKey = null;
  state.selectedJob = null;
  state.selectedTmux = null;
  renderJobs();
  renderTmuxSessions();
  renderOutputTabs();
  setLogTitle("输出");
  setLogText("选择一个任务、进程或 tmux 会话查看输出。", { resetX: true });
  setLogPaneOpen(false);
  setTerminalControlsVisible(false);
}

function scrollGpuSelectionIntoView() {
  requestAnimationFrame(() => {
    const row = document.querySelector("#gpuRows tr.selected");
    row?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function syncServerOrderingState() {
  const ids = state.servers.map((server) => server.id);
  state.ui.serverPins = state.ui.serverPins.filter((id) => ids.includes(id));
  state.ui.serverOrder = [
    ...state.ui.serverOrder.filter((id) => ids.includes(id)),
    ...ids.filter((id) => !state.ui.serverOrder.includes(id)),
  ];
}

function updateServerHistory(servers = state.servers) {
  const next = { ...state.ui.serverHistory };
  servers.forEach((server) => {
    const history = Array.isArray(next[server.id]) ? next[server.id].slice(-7) : [];
    history.push({
      online: Boolean(server.online),
      error: Boolean(server.error),
      busy: serverBusyGpuCount(server),
      processes: (server.processes || []).length,
    });
    next[server.id] = history.slice(-8);
  });
  Object.keys(next).forEach((id) => {
    if (!servers.some((server) => server.id === id)) delete next[id];
  });
  state.ui.serverHistory = next;
}

function serverOriginalIndex(server) {
  return state.servers.findIndex((item) => item.id === server.id);
}

function serverManualIndex(server) {
  const index = state.ui.serverOrder.indexOf(server.id);
  return index >= 0 ? index : state.ui.serverOrder.length + Math.max(serverOriginalIndex(server), 0);
}

function serverPinned(serverId) {
  return state.ui.serverPins.includes(serverId);
}

function serverSortScore(server, mode) {
  if (mode === "idle") {
    return [serverIdleGpuCount(server), (server.gpus || []).length, -((server.processes || []).length)];
  }
  if (mode === "alerts") {
    return [
      server.online ? 0 : 3,
      server.error ? 2 : 0,
      serverBusyGpuCount(server),
      (server.processes || []).length,
      (server.gpus || []).length,
    ];
  }
  if (mode === "gpus") {
    return [(server.gpus || []).length, serverIdleGpuCount(server)];
  }
  if (mode === "processes") {
    return [((server.processes || []).length), (server.gpus || []).length];
  }
  return [];
}

function compareServerArrays(left, right) {
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    const delta = Number(right[index] || 0) - Number(left[index] || 0);
    if (delta !== 0) return delta;
  }
  return 0;
}

function sortedServersForDisplay(servers) {
  syncServerOrderingState();
  const mode = state.ui.serverSort || "default";
  const items = servers.slice();
  items.sort((a, b) => {
    const pinCompare = Number(serverPinned(b.id)) - Number(serverPinned(a.id));
    if (pinCompare !== 0) return pinCompare;
    if (mode === "manual") {
      return serverManualIndex(a) - serverManualIndex(b);
    }
    if (mode === "default") {
      return serverOriginalIndex(a) - serverOriginalIndex(b);
    }
    if (mode === "name") {
      return String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-Hans-CN", {
        numeric: true,
        sensitivity: "base",
      });
    }
    const scoreCompare = compareServerArrays(serverSortScore(a, mode), serverSortScore(b, mode));
    if (scoreCompare !== 0) return scoreCompare;
    const nameCompare = String(a.name || a.id).localeCompare(String(b.name || b.id), "zh-Hans-CN", {
      numeric: true,
      sensitivity: "base",
    });
    if (nameCompare !== 0) return nameCompare;
    return serverOriginalIndex(a) - serverOriginalIndex(b);
  });
  return items;
}

function renderServerSortControl() {
  const select = $("serverSortSelect");
  if (!select) return;
  select.value = Array.from(select.options).some((option) => option.value === state.ui.serverSort)
    ? state.ui.serverSort
    : "default";
}

function persistServerUiState() {
  saveStoredJson(STORAGE_KEYS.serverOrder, state.ui.serverOrder);
  saveStoredJson(STORAGE_KEYS.serverPins, state.ui.serverPins);
}

function toggleServerPin(serverId) {
  syncServerOrderingState();
  if (serverPinned(serverId)) {
    state.ui.serverPins = state.ui.serverPins.filter((id) => id !== serverId);
  } else {
    state.ui.serverPins = [serverId, ...state.ui.serverPins.filter((id) => id !== serverId)];
    if (!state.ui.serverOrder.includes(serverId)) {
      state.ui.serverOrder = [serverId, ...state.ui.serverOrder];
    }
  }
  persistServerUiState();
  renderServers();
}

function moveServerInManualOrder(draggingId, targetId, position = "after") {
  if (!draggingId || !targetId || draggingId === targetId) return;
  syncServerOrderingState();
  if (serverPinned(draggingId) !== serverPinned(targetId)) return;
  const next = state.ui.serverOrder.filter((id) => id !== draggingId);
  const targetIndex = next.indexOf(targetId);
  if (targetIndex < 0) return;
  const insertIndex = position === "before" ? targetIndex : targetIndex + 1;
  next.splice(insertIndex, 0, draggingId);
  state.ui.serverOrder = next;
  persistServerUiState();
}

function renderServers() {
  const list = $("serverList");
  hideServerResourcePopover();
  if (!state.servers.length) {
    list.innerHTML = '<div class="empty">暂无服务器配置。</div>';
    return;
  }
  list.classList.toggle("manual", (state.ui.serverSort || "default") === "manual");
  list.classList.add("folded");
  const items = sortedServersForDisplay(state.servers);
  const onlineItems = items.filter((server) => serverIsReachable(server));
  const offlineItems = items.filter((server) => !serverIsReachable(server));
  const manual = (state.ui.serverSort || "default") === "manual";
  const selectedOffline = offlineItems.some((server) => server.id === state.selectedServer);
  const renderSeries = (series, maxValue, variant = "") => `
    <div class="server-sparkline${variant ? ` ${variant}` : ""}">
      ${(series.length ? series : [0]).map((value) => {
        const ratio = maxValue > 0 ? value / maxValue : 0;
        const height = Math.max(3, Math.round(ratio * 100));
        return `<span style="height:${height}%"></span>`;
      }).join("")}
    </div>
  `;
  const renderCard = (server, index, compact = false) => {
    const gpuCount = (server.gpus || []).length;
    const busyGpuCount = serverBusyGpuCount(server);
    const idleCount = serverIdleGpuCount(server);
    const processCount = (server.processes || []).length;
    const active = server.id === state.selectedServer ? " active" : "";
    const reachable = serverIsReachable(server);
    const monitorBlocked = serverHasMonitorIssue(server);
    const dotState = server.online ? " online" : reachable ? " warning" : "";
    const target = server.target || server.mode;
    const errorText = server.error || "";
    const history = state.ui.serverHistory[server.id] || [];
    const busySeries = history.map((item) => item.busy);
    const processSeries = history.map((item) => item.processes);
    const busyMax = Math.max(1, ...busySeries, gpuCount);
    const processMax = Math.max(1, ...processSeries, processCount);
    const rankText = serverPinned(server.id) ? "置顶" : `#${index + 1}`;
    const connectivityText = server.mode === "local" ? "本机可用" : "SSH 已连接";
    const refreshing = Boolean(state.ui.serverRefreshBusy[server.id]);
    const hostSummary = serverHostResourceSummary(server);
    const hostBadgeClass = hostSummary.state === "warning" ? " warning" : hostSummary.state === "muted" ? " subtle" : " host";
    const hostBadge = `<span class="server-badge${hostBadgeClass}" title="${escapeHtml(hostSummary.title)}">${escapeHtml(hostSummary.badge)}</span>`;
    const health = compact
      ? `
          <div class="server-health">
            <span class="server-badge danger">连接失败</span>
            ${hostBadge}
            ${errorText ? `<span class="server-badge danger" title="${escapeHtml(errorText)}">异常</span>` : ""}
          </div>
          ${errorText ? `<div class="server-error" title="${escapeHtml(errorText)}">${escapeHtml(errorText)}</div>` : ""}
        `
      : monitorBlocked
        ? `
          <div class="server-health">
            <span class="server-badge warning">${connectivityText}</span>
            <span class="server-badge danger" title="GPU / CUDA 监控采集失败">GPU / CUDA 异常</span>
            ${hostBadge}
          </div>
          <div class="server-error" title="${escapeHtml(errorText || "GPU 监控未上线")}">${escapeHtml(errorText || "GPU 监控未上线")}</div>
        `
      : `
          <div class="server-health">
            <span class="server-badge" title="${idleCount} 空闲 / ${gpuCount} GPU">${idleCount}闲/${gpuCount}卡</span>
            <span class="server-badge subtle" title="${busyGpuCount} 张 GPU 忙碌">${busyGpuCount}忙</span>
            <span class="server-badge subtle" title="${processCount} 个进程">${processCount}进程</span>
            ${hostBadge}
            ${errorText ? `<span class="server-badge danger" title="${escapeHtml(errorText)}">${escapeHtml(errorText)}</span>` : ""}
          </div>
          <div class="server-trends">
            <div class="server-trend">
              <span>忙碌 GPU</span>
              ${renderSeries(busySeries, busyMax)}
              <strong>${busyGpuCount}</strong>
            </div>
            <div class="server-trend">
              <span>进程数</span>
              ${renderSeries(processSeries, processMax, "process")}
              <strong>${processCount}</strong>
            </div>
          </div>
        `;
    return `
      <div
        class="server-item${active}${manual ? " manual" : ""}${compact ? " compact" : ""}${monitorBlocked ? " degraded" : ""}"
        data-id="${escapeHtml(server.id)}"
        draggable="${manual ? "true" : "false"}"
      >
        <div class="server-item-head">
          <div class="server-name">
            <span title="${escapeHtml(server.name)}">${escapeHtml(server.name)}</span>
            <span class="dot${dotState}"></span>
          </div>
          <div class="server-item-actions">
            <button
              class="server-refresh${refreshing ? " busy" : ""}"
              type="button"
              title="只刷新这台服务器的 GPU、显存、进程和连接状态；不会重画工作台"
              data-action="refresh-server"
              data-id="${escapeHtml(server.id)}"
              ${refreshing ? "disabled" : ""}
            >${refreshing ? "…" : "↻"}</button>
            <button
              class="server-pin${serverPinned(server.id) ? " active" : ""}"
              type="button"
              title="${serverPinned(server.id) ? "取消置顶" : "置顶"}"
              data-action="pin-server"
              data-id="${escapeHtml(server.id)}"
            >★</button>
            <button class="server-drag" type="button" title="拖拽排序" tabindex="-1">⋮⋮</button>
          </div>
        </div>
        <div class="server-meta-row">
          <div class="server-meta" title="${escapeHtml(target)}">${escapeHtml(target)}</div>
          <span class="server-rank">${rankText}</span>
        </div>
        ${health}
      </div>
    `;
  };
  const onlineHtml = onlineItems.length
    ? onlineItems.map((server, index) => renderCard(server, index)).join("")
    : '<div class="empty">暂无已连接服务器。</div>';
  const offlineHtml = offlineItems.length
    ? `
        <details
          id="offlineServerGroup"
          class="offline-group"
          ${state.ui.offlineServersOpen || selectedOffline ? "open" : ""}
        >
          <summary>
            <span>连接失败</span>
            <strong>${offlineItems.length}</strong>
          </summary>
          <div class="offline-list">
            ${offlineItems.map((server, index) => renderCard(server, onlineItems.length + index, true)).join("")}
          </div>
        </details>
      `
    : "";
  renderServerSortControl();
  list.innerHTML = `${onlineHtml}${offlineHtml}`;
  $("offlineServerGroup")?.addEventListener("toggle", (event) => {
    state.ui.offlineServersOpen = event.currentTarget.open;
  });
}

function renderGpuRows() {
  const rows = $("gpuRows");
  const items = allGpus();
  $("gpuCount").textContent = `${items.length} 张卡`;
  if (!items.length) {
    rows.innerHTML = '<tr><td colspan="6" class="empty">暂无 GPU 数据。</td></tr>';
    return;
  }
  rows.innerHTML = items
    .map(({ server, gpu }) => {
      const pct = gpu.memory_total_mib
        ? Math.min(100, Math.round((gpu.memory_used_mib / gpu.memory_total_mib) * 100))
        : 0;
      const util = Number(gpu.gpu_util ?? 0);
      const utilTitle = util === 0 && pct >= 8
        ? "算力利用率为 0%，但显存已被占用"
        : "GPU 算力利用率";
      const stateTitle = gpu.state === "busy" && util === 0 && pct >= 8
        ? "显存占用"
        : zhStatus(gpu.state);
      const selected =
        server.id === state.selectedServer && String(gpu.index) === String(state.selectedGpu)
          ? " selected"
          : "";
      const serverSelected = server.id === state.selectedServer ? " server-selected" : "";
      const busy = gpu.state === "busy" ? " busy" : "";
      return `
        <tr class="gpu-row${serverSelected}${selected}" data-server-id="${escapeHtml(server.id)}" data-gpu-index="${escapeHtml(gpu.index)}" onclick="selectGpu('${escapeHtml(server.id)}', '${escapeHtml(gpu.index)}')">
          <td>${escapeHtml(server.name)}</td>
          <td><div class="gpu-name" title="${escapeHtml(gpu.name)}">#${gpu.index} ${escapeHtml(gpu.name)}</div></td>
          <td class="mem-cell">
            <div class="bar"><div class="bar-fill${busy}" style="width:${pct}%"></div></div>
            <span class="muted">${fmtMiB(gpu.memory_used_mib)} / ${fmtMiB(gpu.memory_total_mib)}</span>
          </td>
          <td title="${escapeHtml(utilTitle)}">${util}%</td>
          <td>${gpu.temperature ?? 0}°C</td>
          <td><span class="state ${escapeHtml(gpu.state)}" title="${escapeHtml(stateTitle)}">${escapeHtml(stateTitle)}</span></td>
        </tr>
      `;
    })
    .join("");
}

function renderProcesses() {
  const rows = $("processRows");
  const allItems = allProcesses();
  renderProcessFilters(allItems);
  renderProcessSortIndicators();
  const items = filteredProcesses(allItems);
  $("processCount").textContent = items.length === allItems.length
    ? `${allItems.length} 个运行中`
    : `${items.length}/${allItems.length} 个运行中`;
  if (!allItems.length) {
    rows.innerHTML = '<tr><td colspan="7" class="empty">当前在线服务器未报告 CUDA 计算进程。</td></tr>';
    return;
  }
  if (!items.length) {
    rows.innerHTML = '<tr><td colspan="7" class="empty">没有匹配的进程。</td></tr>';
    return;
  }
  rows.innerHTML = items
    .map(({ server, process }) => `
      <tr class="process-row" onclick="showProcessCommand('${escapeHtml(server.id)}', '${escapeHtml(process.pid)}')">
        <td class="process-action-cell">
          <button class="stop-button compact" type="button" onclick="stopProcess(event, '${escapeHtml(server.id)}', '${escapeHtml(process.pid)}')" title="向这个 CUDA 进程发送停止信号">关闭</button>
        </td>
        <td>${escapeHtml(server.name)}</td>
        <td>${escapeHtml(process.gpu_index ?? "-")}</td>
        <td>${escapeHtml(process.pid)}</td>
        <td>${escapeHtml(process.user || "-")}</td>
        <td>${fmtMiB(process.used_memory_mib)}</td>
        <td><div class="cmd" title="${escapeHtml(process.command || process.process_name)}">${escapeHtml(process.command || process.process_name)}</div></td>
      </tr>
    `)
    .join("");
}

function showProcessCommand(serverId, pid) {
  const server = serverById(serverId);
  const process = (server?.processes || []).find((item) => String(item.pid) === String(pid));
  if (!server || !process) return;
  const command = process.command || process.process_name || "";
  const content = [
      `服务器: ${server.name} (${server.target || server.id})`,
      `GPU: ${process.gpu_index ?? "-"}`,
      `PID: ${process.pid}`,
      `用户: ${process.user || "-"}`,
      `显存: ${fmtMiB(process.used_memory_mib)}`,
      "",
      "完整命令:",
      command || "-",
    ].join("\n");
  const tab = upsertOutputTab({
    type: "process",
    serverId,
    pid: String(pid),
    title: `进程 · ${server.name} · ${pid}`,
    content,
  });
  activateOutputTab(tab.key);
}

async function stopProcess(event, serverId, pid) {
  consumeClick(event);
  const button = event.currentTarget;
  if (button) {
    button.disabled = true;
    button.textContent = "关闭中";
  }
  try {
    const payload = await fetchJson(
      `/api/servers/${encodeURIComponent(serverId)}/processes/${encodeURIComponent(pid)}/stop`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
    );
    const server = serverById(serverId);
    const content = [
      `服务器: ${server?.name || serverId}`,
      `PID: ${pid}`,
      "",
      "关闭结果:",
      payload.detail || "已发送停止信号。",
    ].join("\n");
    const tab = upsertOutputTab({
      type: "process",
      serverId,
      pid: String(pid),
      title: `进程 · ${server?.name || serverId} · ${pid}`,
      content,
    });
    activateOutputTab(tab.key);
    await loadStatus(true);
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = "关闭";
    }
    showActionError(error);
  }
}

function renderFormOptions() {
  const serverSelect = $("serverSelect");
  const gpuSelect = $("gpuSelect");
  const selectable = sortedVisibleServers();
  if (!state.selectedServer && selectable.length) {
    state.selectedServer = selectable[0].id;
  }
  const current = selectedServer();
  serverSelect.innerHTML = selectable
    .map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(serverOptionLabel(server))}</option>`)
    .join("");
  if (current) serverSelect.value = current.id;

  const gpus = current?.gpus || [];
  gpuSelect.innerHTML = '<option value="auto">自动选择空闲 GPU</option>' +
    gpus
      .map((gpu) => {
        const label = `GPU ${gpu.index} · 空闲 ${fmtMiB(gpu.memory_free_mib)} · ${gpu.gpu_util}%`;
        return `<option value="${escapeHtml(gpu.index)}">${escapeHtml(label)}</option>`;
      })
      .join("");
  gpuSelect.value = Array.from(gpuSelect.options).some((option) => option.value === String(state.selectedGpu))
    ? String(state.selectedGpu)
    : "auto";
}

function renderTaskPlanOptions() {
  const serverSelect = $("planServerSelect");
  const gpuSelect = $("planGpuSelect");
  if (!serverSelect || !gpuSelect) return;
  const online = sortedServersForDisplay(onlineServers());
  const selectedValue = serverSelect.value || "auto";
  serverSelect.innerHTML = '<option value="auto">自动分配到所有在线服务器</option>' +
    online
      .map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(server.name)}</option>`)
      .join("");
  serverSelect.value = Array.from(serverSelect.options).some((option) => option.value === selectedValue)
    ? selectedValue
    : "auto";

  if (serverSelect.value === "auto") {
    gpuSelect.innerHTML = '<option value="auto">自动选择最大空闲显存 GPU</option>';
    gpuSelect.value = "auto";
    return;
  }

  const server = serverById(serverSelect.value);
  const oldGpu = gpuSelect.value || "auto";
  gpuSelect.innerHTML = '<option value="auto">自动选择空闲 GPU</option>' +
    (server?.gpus || [])
      .map((gpu) => {
        const label = `GPU ${gpu.index} · 空闲 ${fmtMiB(gpu.memory_free_mib)} · ${gpu.gpu_util}%`;
        return `<option value="${escapeHtml(gpu.index)}">${escapeHtml(label)}</option>`;
      })
      .join("");
  gpuSelect.value = Array.from(gpuSelect.options).some((option) => option.value === oldGpu)
    ? oldGpu
    : "auto";
}

function renderTerminalOptions() {
  const terminalSelect = $("terminalServerSelect");
  if (!terminalSelect) return;
  const selectable = sortedVisibleServers();
  const currentValue = terminalSelect.value || state.selectedServer;
  terminalSelect.innerHTML = selectable
    .map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(serverOptionLabel(server))}</option>`)
    .join("");
  terminalSelect.value = Array.from(terminalSelect.options).some((option) => option.value === currentValue)
    ? currentValue
    : selectable[0]?.id || "";
}

function renderTransferTargetOptions() {
  const select = $("transferTargetServerSelect");
  if (!select) return;
  const selectable = sortedVisibleServers();
  const currentValue = select.value || state.selectedServer || selectable[0]?.id || "";
  select.innerHTML = selectable
    .map((server) => `<option value="${escapeHtml(server.id)}" title="${escapeHtml(serverOptionLabel(server))}">${escapeHtml(serverOptionShortLabel(server))}</option>`)
    .join("");
  select.value = Array.from(select.options).some((option) => option.value === currentValue)
    ? currentValue
    : selectable[0]?.id || "";
}

function renderTransferSourceOptions() {
  const select = $("transferSourceServerSelect");
  if (!select) return;
  const selectable = sortedVisibleServers();
  const currentValue = select.value || selectable[0]?.id || "";
  select.innerHTML = selectable
    .map((server) => `<option value="${escapeHtml(server.id)}" title="${escapeHtml(serverOptionLabel(server))}">${escapeHtml(serverOptionShortLabel(server))}</option>`)
    .join("");
  select.value = Array.from(select.options).some((option) => option.value === currentValue)
    ? currentValue
    : selectable[0]?.id || "";
}

function syncTransferTargetServerFromInput() {
  normalizeTransferPathInput($("transferTargetInput"), $("transferTargetServerSelect"));
}

function syncTransferSourceServerFromInput() {
  normalizeTransferPathInput($("transferSourceInput"), $("transferSourceServerSelect"));
}

function transferTargetMatchesServer(prefix, server) {
  const text = String(prefix || "");
  const host = text.includes("@") ? text.split("@").pop() : text;
  return [server.target, server.id, server.name]
    .filter(Boolean)
    .some((value) => {
      const candidate = String(value);
      return candidate === text || candidate === host || candidate.endsWith(`@${host}`);
    });
}

function renderIgnoreChips() {
  const box = $("ignoreChips");
  const count = $("ignoreCount");
  if (!box || !count) return;
  count.textContent = `${state.transfer.ignores.length} 项`;
  if (!state.transfer.ignores.length) {
    box.innerHTML = '<span class="muted">可以从左侧文件树点“忽略”加入。</span>';
    return;
  }
  box.innerHTML = state.transfer.ignores
    .map((item) => `
      <span class="ignore-chip" title="${escapeHtml(item)}">
        <span>${escapeHtml(item)}</span>
        <button class="chip-remove" type="button" data-ignore="${escapeHtml(item)}" title="移除这条忽略规则">×</button>
      </span>
    `)
    .join("");
}

function syncIgnoreInputFromState() {
  const input = $("transferExcludeInput");
  if (input) input.value = state.transfer.ignores.join(",");
  renderIgnoreChips();
}

function syncIgnoreStateFromInput() {
  state.transfer.ignores = parseIgnoreText($("transferExcludeInput")?.value || "");
  renderIgnoreChips();
}

function addTransferIgnore(path, isDir = false) {
  const pattern = transferRelativePath(path, isDir);
  if (!pattern) return;
  if (!state.transfer.ignores.includes(pattern)) {
    state.transfer.ignores.push(pattern);
  }
  syncIgnoreInputFromState();
}

function removeTransferIgnore(pattern) {
  state.transfer.ignores = state.transfer.ignores.filter((item) => item !== pattern);
  syncIgnoreInputFromState();
}

function transferSourceKey(serverId, path, isDir = false) {
  return `${serverId || "local"}|${normalizePathForCompare(path)}|${isDir ? "dir" : "file"}`;
}

function addTransferSource(path, isDir = false, options = {}) {
  const sourcePath = transferPathOnly(path);
  if (!sourcePath) return;
  const server = options.server || serverById(transferSourceServerId());
  const serverId = server?.id || transferSourceServerId() || "local";
  const key = transferSourceKey(serverId, sourcePath, isDir);
  const value = formatTransferSource(sourcePath, server, isDir);
  if (!state.transfer.sources.some((item) => item.key === key)) {
    state.transfer.sources.push({
      key,
      serverId,
      serverName: server?.name || serverId,
      path: sourcePath,
      isDir,
      value,
    });
  }
  renderSelectedSources();
  const message = $("transferMessage");
  if (message && options.silent !== true) {
    message.textContent = `已加入待传源项：${pathBaseName(sourcePath)}`;
    message.classList.remove("error");
  }
}

function removeTransferSource(key) {
  state.transfer.sources = state.transfer.sources.filter((item) => item.key !== key);
  renderSelectedSources();
}

function clearTransferSources() {
  state.transfer.sources = [];
  renderSelectedSources();
}

function renderSelectedSources() {
  const list = $("selectedSourceList");
  const count = $("selectedSourceCount");
  if (!list || !count) return;
  count.textContent = `${state.transfer.sources.length} 项`;
  if (!state.transfer.sources.length) {
    list.innerHTML = '<div class="empty compact-empty">可以从文件树或弹窗里把多个文件、文件夹加入这里。</div>';
    return;
  }
  const rows = state.transfer.sources
    .map((item) => `
      <div class="selected-source-item" title="${escapeHtml(item.value)}">
        <span>
          <strong>${item.isDir ? "目录" : "文件"}</strong>
          ${escapeHtml(item.serverName || item.serverId || "本机")} · ${escapeHtml(item.value)}
        </span>
        <button class="chip-remove" type="button" data-source-key="${escapeHtml(item.key)}" title="从待传源项中移除这一项">×</button>
      </div>
    `)
    .join("");
  list.innerHTML = `
    <div class="selected-source-toolbar">
      <span class="muted">提交时会依次传输这些源项。</span>
      <button class="secondary mini" type="button" data-action="clear-transfer-sources" title="清空当前所有待传源项">清空</button>
    </div>
    ${rows}
  `;
}

function renderTransferTreeNode(entry, level = 0) {
  const node = state.transfer.tree[entry.path];
  const open = Boolean(node?.open);
  const children = node?.entries || [];
  const icon = entry.is_dir ? (open ? "▾" : "▸") : "·";
  const row = `
    <div class="file-tree-row${level === 0 ? " root-row" : ""}" style="padding-left:${6 + level * 18}px">
      <button class="file-toggle" type="button" data-action="toggle-transfer-node" data-path="${escapeHtml(entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="${entry.is_dir ? "展开或收起这个目录" : "文件项不可展开"}">${icon}</button>
      <span class="file-name" title="${escapeHtml(entry.path)}">${entry.is_dir ? "[DIR]" : "[FILE]"} ${escapeHtml(entry.name)}</span>
      <span class="file-meta">${escapeHtml(entry.size_text || "")}</span>
      <span class="file-actions">
        <button class="file-action primary-soft" type="button" data-action="add-transfer-source" data-path="${escapeHtml(entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="把这个文件或目录加入待传源项">加入</button>
        <button class="file-action" type="button" data-action="ignore-transfer-node" data-path="${escapeHtml(entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="把这个路径加入 rsync 忽略规则">忽略</button>
      </span>
    </div>
  `;
  if (!entry.is_dir || !open) return row;
  const childRows = children
    .map((child) => renderTransferTreeNode(child, level + 1))
    .join("");
  return row + childRows;
}

function renderTransferTree() {
  const box = $("transferTree");
  const meta = $("transferTreeMeta");
  if (!box || !meta) return;
  const source = state.transfer.source;
  if (!source) {
    meta.textContent = "选择源路径后显示文件树";
    box.innerHTML = '<div class="empty compact-empty">还没有选择源路径。</div>';
    return;
  }
  const prefix = source.serverName ? `${source.serverName} · ` : "";
  meta.textContent = prefix + (source.is_dir ? "文件夹，可展开查看并忽略子项" : "单个文件");
  box.innerHTML = renderTransferTreeNode(source, 0);
}

function renderTargetTreeNode(entry, level = 0) {
  const node = state.transfer.targetTree[entry.path];
  const open = Boolean(node?.open);
  const children = node?.entries || [];
  const icon = entry.is_dir ? (open ? "▾" : "▸") : "·";
  const selected = normalizePathForCompare(entry.path) === normalizePathForCompare(state.transfer.target?.path || "")
    ? " selected"
    : "";
  const row = `
    <div class="file-tree-row${level === 0 ? " root-row" : ""}${selected}" style="padding-left:${6 + level * 18}px">
      <button class="file-toggle" type="button" data-action="toggle-target-node" data-path="${escapeHtml(entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}" title="展开或收起这个目标目录">${icon}</button>
      <span class="file-name" title="${escapeHtml(entry.path)}">[DIR] ${escapeHtml(entry.name || entry.path)}</span>
      <button class="file-action" type="button" data-action="choose-target-node" data-path="${escapeHtml(entry.path)}" title="把这个目录设为传输目标路径">选择</button>
    </div>
  `;
  if (!entry.is_dir || !open) return row;
  return row + children.map((child) => renderTargetTreeNode(child, level + 1)).join("");
}

function renderTargetTree() {
  const box = $("targetTree");
  const meta = $("targetTreeMeta");
  if (!box || !meta) return;
  const target = state.transfer.target;
  if (!target) {
    meta.textContent = "选择服务器后浏览目标目录";
    box.innerHTML = '<div class="empty compact-empty">还没有选择目标目录。</div>';
    return;
  }
  meta.textContent = target.serverName ? `${target.serverName} · 点击目录可选择` : "点击目录可选择";
  box.innerHTML = renderTargetTreeNode(target, 0);
}

function transferTargetBrowsePath() {
  const raw = transferTargetValue();
  if (raw) return raw;
  const server = serverById(transferTargetServerId());
  if (server?.mode === "local") return "/mnt";
  return "/";
}

function transferSourceBrowsePath() {
  const raw = transferSourceValue();
  if (raw) return raw;
  const server = serverById(transferSourceServerId());
  if (server?.mode === "local") return "/mnt";
  return "/";
}

async function loadTransferSourceTree(path = transferSourceBrowsePath()) {
  const box = $("transferTree");
  const meta = $("transferTreeMeta");
  const message = $("transferMessage");
  const serverId = transferSourceServerId();
  const server = serverById(serverId);
  const target = String(parseRsyncTargetPath(path) || path || "").trim();
  if (!target) {
    state.transfer.source = null;
    state.transfer.tree = {};
    renderTransferTree();
    return;
  }
  if (box) box.innerHTML = '<div class="empty compact-empty">正在读取目录...</div>';
  if (meta) meta.textContent = "加载中";
  if (message) {
    message.textContent = "";
    message.classList.remove("error");
  }
  try {
    const payload = await browseFiles(target, 300, { serverId });
    state.transfer.source = { ...(payload.selected || {}), serverName: server?.name || "" };
    state.transfer.tree = {};
    if (payload.selected?.is_dir) {
      state.transfer.tree[payload.selected.path] = {
        open: true,
        entries: payload.entries || [],
      };
      $("transferSourceInput").value = ensureDirectorySlash(payload.selected.path);
    } else if (payload.selected) {
      $("transferSourceInput").value = payload.selected.path;
    }
    renderTransferTree();
  } catch (error) {
    state.transfer.source = null;
    state.transfer.tree = {};
    renderTransferTree();
    if (message) {
      message.textContent = error.message;
      message.classList.add("error");
    }
  }
}

async function loadTransferTargetTree(path = transferTargetBrowsePath()) {
  const box = $("targetTree");
  const meta = $("targetTreeMeta");
  const message = $("transferMessage");
  const serverId = transferTargetServerId();
  const server = serverById(serverId);
  if (box) box.innerHTML = '<div class="empty compact-empty">正在读取目标目录...</div>';
  if (meta) meta.textContent = "加载中";
  if (message) {
    message.textContent = "";
    message.classList.remove("error");
  }
  try {
    const payload = await browseFiles(path || "", 300, { serverId, dirsOnly: true });
    const selected = { ...(payload.selected || {}), serverName: server?.name || "" };
    state.transfer.target = selected;
    state.transfer.targetTree = {};
    if (selected?.is_dir) {
      state.transfer.targetTree[selected.path] = {
        open: true,
        entries: payload.entries || [],
      };
      $("transferTargetInput").value = ensureDirectorySlash(selected.path);
    }
    renderTargetTree();
  } catch (error) {
    state.transfer.target = null;
    state.transfer.targetTree = {};
    renderTargetTree();
    if (message) {
      message.textContent = error.message;
      message.classList.add("error");
    }
  }
}

async function toggleTransferNode(path, isDir) {
  if (!isDir) return;
  const existing = state.transfer.tree[path];
  if (existing) {
    existing.open = !existing.open;
    renderTransferTree();
    return;
  }
  state.transfer.tree[path] = { open: true, entries: [] };
  renderTransferTree();
  try {
    const payload = await browseFiles(path, 300, { serverId: transferSourceServerId() });
    state.transfer.tree[path] = {
      open: true,
      entries: payload.entries || [],
    };
  } catch (error) {
    state.transfer.tree[path] = {
      open: true,
      entries: [{ name: error.message, path, is_dir: false, size_text: "", mtime: "" }],
    };
  }
  renderTransferTree();
}

async function toggleTransferTargetNode(path, isDir) {
  if (!isDir) return;
  const existing = state.transfer.targetTree[path];
  if (existing) {
    existing.open = !existing.open;
    renderTargetTree();
    return;
  }
  state.transfer.targetTree[path] = { open: true, entries: [] };
  renderTargetTree();
  try {
    const payload = await browseFiles(path, 300, {
      serverId: transferTargetServerId(),
      dirsOnly: true,
    });
    state.transfer.targetTree[path] = {
      open: true,
      entries: payload.entries || [],
    };
  } catch (error) {
    state.transfer.targetTree[path] = {
      open: true,
      entries: [{ name: error.message, path, is_dir: true, size_text: "", mtime: "" }],
    };
  }
  renderTargetTree();
}

function chooseTransferTargetDirectory(path) {
  const server = serverById(transferTargetServerId());
  $("transferTargetInput").value = ensureDirectorySlash(path);
  state.transfer.target = {
    name: pathBaseName(path),
    path,
    is_dir: true,
    serverName: server?.name || "",
  };
  renderTargetTree();
}

function parseTransferProgress(job, log) {
  if (job.status === "done") return 100;
  const matches = Array.from(String(log || "").matchAll(/(?:^|\s)(\d{1,3})%\s/g));
  const last = matches.length ? Number(matches[matches.length - 1][1]) : 0;
  return Math.max(0, Math.min(100, Number.isFinite(last) ? last : 0));
}

function lastTransferLine(log) {
  const lines = String(log || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("[total-control] command:"));
  return lines.slice(-1)[0] || "等待输出...";
}

function renderTransferProgress() {
  const list = $("transferProgressList");
  if (!list) return;
  const jobs = state.jobs.filter((job) => job.kind === "transfer").slice(0, 20);
  if (!jobs.length) {
    list.innerHTML = '<div class="empty compact-empty">暂无文件传输任务。</div>';
    return;
  }
  list.innerHTML = jobs
    .map((job) => {
      const cached = state.transfer.logs[job.id] || {};
      const pct = cached.progress ?? (job.status === "done" ? 100 : 0);
      const line = cached.line || (job.status === "running" ? "正在读取 rsync 输出..." : job.error || job.created_at);
      const canStop = ["running", "queued", "starting", "blocked"].includes(job.status);
      return `
        <div class="transfer-progress-item" onclick="showLog('${escapeHtml(job.id)}')">
          <div class="transfer-progress-head">
            <span class="transfer-progress-name" title="${escapeHtml(job.name)}">${escapeHtml(job.name)}</span>
            <span class="transfer-progress-actions">
              <span class="state ${escapeHtml(job.status)}">${escapeHtml(zhStatus(job.status))} · ${pct}%</span>
              ${canStop ? `<button class="stop-button compact" type="button" onclick="stopJob(event, '${escapeHtml(job.id)}')" title="取消这条文件传输任务">取消</button>` : ""}
            </span>
          </div>
          <div class="bar"><div class="bar-fill${job.status === "running" ? " busy" : ""}" style="width:${pct}%"></div></div>
          <div class="transfer-progress-line" title="${escapeHtml(line)}">${escapeHtml(line)}</div>
        </div>
      `;
    })
    .join("");
}

async function updateTransferProgress() {
  const jobs = state.jobs.filter((job) => job.kind === "transfer").slice(0, 20);
  if (!jobs.length) {
    renderTransferProgress();
    renderJobs();
    return;
  }
  await Promise.all(
    jobs.map(async (job) => {
      if (job.status === "done" && state.transfer.logs[job.id]) return;
      try {
        const payload = await fetchJson(`/api/jobs/${encodeURIComponent(job.id)}/log`);
        const log = payload.log || "";
        state.transfer.logs[job.id] = {
          progress: parseTransferProgress(job, log),
          line: lastTransferLine(log),
        };
      } catch (error) {
        state.transfer.logs[job.id] = {
          progress: 0,
          line: error.message,
        };
      }
    }),
  );
  renderTransferProgress();
  renderJobs();
}

function clearFilePreview(message = "选择文件查看预览。") {
  state.filePreview = {
    serverId: state.filePicker.serverId || "",
    path: "",
    text: "",
    encoding: "",
    truncated: false,
    error: "",
    loading: false,
  };
  renderFilePreview(message);
}

function renderFilePreview(emptyMessage = "选择文件查看预览。") {
  const box = $("filePreview");
  const title = $("filePreviewTitle");
  const meta = $("filePreviewMeta");
  if (!box || !title || !meta) return;
  const server = serverById(state.filePreview.serverId || state.filePicker.serverId || "");
  if (state.filePreview.loading) {
    title.textContent = "文本预览";
    meta.textContent = "读取中";
    box.textContent = "正在读取文件内容...";
    return;
  }
  if (state.filePreview.error) {
    title.textContent = "文本预览";
    meta.textContent = "不可预览";
    box.textContent = state.filePreview.error;
    return;
  }
  if (!state.filePreview.path) {
    title.textContent = "文本预览";
    meta.textContent = "选择文件后预览";
    box.textContent = emptyMessage;
    return;
  }
  title.textContent = pathBaseName(state.filePreview.path);
  meta.textContent = [
    server?.name || (state.filePreview.serverId ? state.filePreview.serverId : "本机"),
    state.filePreview.encoding || "utf-8",
    state.filePreview.truncated ? "已截断" : "",
  ].filter(Boolean).join(" · ");
  box.textContent = state.filePreview.text || "文件为空。";
}

async function previewFileInPicker(path) {
  state.filePreview = {
    serverId: state.filePicker.serverId || "",
    path,
    text: "",
    encoding: "",
    truncated: false,
    error: "",
    loading: true,
  };
  renderFilePreview();
  try {
    const payload = await readFileText(path, 131072, { serverId: state.filePicker.serverId || "" });
    state.filePreview = {
      serverId: payload.server_id || state.filePicker.serverId || "",
      path: payload.path || path,
      text: payload.text || "",
      encoding: payload.encoding || "utf-8",
      truncated: Boolean(payload.truncated),
      error: "",
      loading: false,
    };
  } catch (error) {
    state.filePreview = {
      serverId: state.filePicker.serverId || "",
      path,
      text: "",
      encoding: "",
      truncated: false,
      error: error.message,
      loading: false,
    };
  }
  renderFilePreview();
  renderFilePicker(state.filePicker);
}

function renderFilePicker(payload = state.filePicker) {
  const roots = $("filePickerRoots");
  const list = $("filePickerList");
  const input = $("filePickerPathInput");
  const message = $("filePickerMessage");
  if (!roots || !list || !input) return;
  const title = $("filePickerTitle");
  const subtitle = $("filePickerSubtitle");
  const chooseDir = $("filePickerChooseDirBtn");
  const server = payload.serverId ? serverById(payload.serverId) : null;
  if (title) title.textContent = payload.mode === "target" ? "选择目标目录" : "选择源文件或文件夹";
  if (subtitle) {
    subtitle.textContent = payload.mode === "target"
      ? `正在浏览 ${server?.name || "目标服务器"}，只显示目录。`
      : server && server.mode !== "local"
        ? `正在浏览 ${server.name} 的文件系统。`
        : "浏览 WSL 可访问路径，例如 /mnt/e、/mnt/f、Home 和项目目录。";
  }
  if (chooseDir) chooseDir.textContent = payload.mode === "target" ? "选择当前目录" : "加入当前文件夹";
  input.value = payload.path || "";
  roots.innerHTML = (payload.roots || [])
    .map((root) => {
      const active = payload.path && normalizePathForCompare(payload.path).startsWith(normalizePathForCompare(root.path));
      return `
        <button class="root-button${active ? " active" : ""}" type="button" data-path="${escapeHtml(root.path)}" title="快速跳到这个常用根目录">
          <strong>${escapeHtml(root.label)}</strong>
          <span title="${escapeHtml(root.path)}">${escapeHtml(root.path)}</span>
        </button>
      `;
    })
    .join("");
  const rows = (payload.entries || [])
    .map((entry) => {
      const active = normalizePathForCompare(state.filePreview.path) === normalizePathForCompare(entry.path) ? " active" : "";
      const meta = [
        entry.is_dir ? "文件夹" : (entry.size_text || "文件"),
        fmtDate(entry.mtime) || "",
      ].filter(Boolean).join(" · ");
      return `
      <div class="file-picker-row${active}" data-path="${escapeHtml(entry.path)}" data-dir="${entry.is_dir ? "1" : "0"}">
        <div class="file-picker-row-main">
          <span class="file-kind">${entry.is_dir ? "DIR" : "FILE"}</span>
          <div class="file-picker-row-text">
            <span class="file-name" title="${escapeHtml(entry.path)}">${escapeHtml(entry.name)}</span>
            <span class="file-picker-row-meta" title="${escapeHtml(meta)}">${escapeHtml(meta)}</span>
          </div>
        </div>
        <div class="file-actions file-picker-row-actions">
          ${entry.is_dir ? '<button class="file-action" type="button" data-action="open-picker" title="进入这个目录继续浏览">打开</button>' : '<button class="file-action" type="button" data-action="preview-picker" title="读取这个文件的文本预览">预览</button>'}
          <button class="file-action${payload.mode !== "target" && entry.is_dir ? " primary-soft" : ""}" type="button" data-action="choose-picker" title="${payload.mode === "target" ? "把这个目录设为目标路径" : "把这个文件或目录加入源项"}">${payload.mode === "target" ? "选择" : "加入"}</button>
        </div>
      </div>
    `;
    })
    .join("");
  list.innerHTML = rows || '<div class="empty compact-empty">目录为空。</div>';
  if (message) {
    message.textContent = payload.truncated ? "目录项较多，仅显示前一部分。" : "";
    message.classList.remove("error");
  }
}

async function loadFilePicker(path = "") {
  const requestId = (state.filePicker.requestId || 0) + 1;
  state.filePicker.requestId = requestId;
  const mode = state.filePicker.mode || "source";
  const serverId = state.filePicker.serverId || "";
  const dirsOnly = Boolean(state.filePicker.dirsOnly);
  const list = $("filePickerList");
  const message = $("filePickerMessage");
  if (list) list.innerHTML = '<div class="empty compact-empty">正在读取目录...</div>';
  renderFilePreview();
  if (message) {
    message.textContent = "";
    message.classList.remove("error");
  }
  try {
    const payload = await browseFiles(path, 500, { serverId, dirsOnly });
    if (requestId !== state.filePicker.requestId) return;
    state.filePicker = {
      roots: payload.roots || [],
      path: payload.path || "",
      parent: payload.parent || "",
      entries: payload.entries || [],
      selected: payload.selected || null,
      truncated: payload.truncated,
      mode,
      serverId,
      dirsOnly,
      requestId,
    };
    renderFilePicker(state.filePicker);
  } catch (error) {
    if (requestId !== state.filePicker.requestId) return;
    if (message) {
      message.textContent = error.message;
      message.classList.add("error");
    }
  }
}

async function openFilePicker(mode = "source") {
  state.filePicker.mode = mode;
  state.filePicker.serverId = mode === "target" ? transferTargetServerId() : transferSourceServerId();
  state.filePicker.dirsOnly = mode === "target";
  clearFilePreview();
  $("filePickerModal").hidden = false;
  const initialPath = mode === "target"
    ? transferTargetBrowsePath()
    : transferSourceBrowsePath();
  await loadFilePicker(initialPath);
}

function closeFilePicker() {
  $("filePickerModal").hidden = true;
  $("filePickerMessage").textContent = "";
  $("filePickerMessage").classList.remove("error");
}

async function chooseFilePickerPath(path, isDir) {
  if (state.filePicker.mode === "target") {
    chooseTransferTargetDirectory(path);
    closeFilePicker();
    await loadTransferTargetTree(path);
    return;
  }
  const sourcePath = transferPathOnly(path);
  $("transferSourceInput").value = isDir ? ensureDirectorySlash(sourcePath) : sourcePath;
  addTransferSource(sourcePath, isDir, { server: serverById(transferSourceServerId()), silent: true });
  const message = $("filePickerMessage");
  if (message) {
    message.textContent = `已加入待传源项：${pathBaseName(sourcePath)}`;
    message.classList.remove("error");
  }
  await loadTransferSourceTree(sourcePath);
}

function jobSearchKey(job) {
  return [
    job.id,
    job.name,
    job.kind,
    job.command_display || job.command,
    job.error,
    job.server_id,
    job.requested_server_id,
  ]
    .join(" ")
    .toLowerCase();
}

function jobMatchesKindFilter(job, value) {
  if (!value) return true;
  return jobKindGroup(job) === value;
}

function jobMatchesStatusFilter(job, value) {
  if (!value) return true;
  const status = String(job.status || "");
  if (value === "running") return ["running", "starting"].includes(status);
  if (value === "waiting") return ["queued", "blocked"].includes(status);
  if (value === "done") return status === "done";
  if (value === "failed") return ["failed", "stopped"].includes(status);
  if (value === "transfer") return job.kind === "transfer";
  return status === value;
}

function waitingQueuePositions() {
  return new Map(
    state.jobs
      .filter((job) => isWaitingJob(job))
      .slice()
      .sort((left, right) => jobQueueRank(left) - jobQueueRank(right))
      .map((job, index) => [job.id, index + 1]),
  );
}

function filteredJobs() {
  const query = state.jobFilters.query.trim().toLowerCase();
  const serverId = state.jobFilters.server;
  const status = state.jobFilters.status;
  const kind = state.jobFilters.kind;
  const sort = state.jobFilters.sort || "created_desc";
  const items = state.jobs
    .filter((job) => {
      if (query && !jobSearchKey(job).includes(query)) return false;
      if (serverId && String(job.server_id || "") !== serverId && String(job.requested_server_id || "") !== serverId) return false;
      if (!jobMatchesStatusFilter(job, status)) return false;
      if (!jobMatchesKindFilter(job, kind)) return false;
      return true;
    });
  items.sort((left, right) => {
    if (sort === "queue") {
      const leftWaiting = isWaitingJob(left);
      const rightWaiting = isWaitingJob(right);
      if (leftWaiting && rightWaiting) return jobQueueRank(left) - jobQueueRank(right);
      if (leftWaiting || rightWaiting) return leftWaiting ? -1 : 1;
    }
    if (sort === "duration_desc") {
      const delta = jobDurationMs(right) - jobDurationMs(left);
      if (delta !== 0) return delta;
    }
    const leftCreated = parseDateMs(left.created_at);
    const rightCreated = parseDateMs(right.created_at);
    if (sort === "created_asc") return leftCreated - rightCreated;
    return rightCreated - leftCreated;
  });
  return items.slice(0, 100);
}

function renderJobFilters() {
  const serverSelect = $("jobServerFilter");
  const statusSelect = $("jobStatusFilter");
  const kindSelect = $("jobTypeFilter");
  const sortSelect = $("jobSortSelect");
  const searchInput = $("jobSearch");
  if (!serverSelect || !statusSelect || !kindSelect || !sortSelect || !searchInput) return;
  const servers = Array.from(
    new Map(
      state.jobs
        .map((job) => {
          const serverId = String(job.server_id || job.requested_server_id || "");
          const server = serverById(serverId);
          return serverId ? [serverId, { id: serverId, name: server?.name || serverId }] : null;
        })
        .filter(Boolean),
    ).values(),
  ).sort((a, b) => String(a.name).localeCompare(String(b.name), "zh-Hans-CN", { numeric: true }));
  serverSelect.innerHTML = '<option value="">全部服务器</option>' +
    servers.map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(server.name)}</option>`).join("");
  serverSelect.value = servers.some((server) => server.id === state.jobFilters.server) ? state.jobFilters.server : "";
  statusSelect.value = state.jobFilters.status || "";
  kindSelect.value = state.jobFilters.kind || "";
  sortSelect.value = state.jobFilters.sort || "created_desc";
  searchInput.value = state.jobFilters.query || "";
  state.jobFilters.server = serverSelect.value;
  state.jobFilters.kind = kindSelect.value;
  state.jobFilters.sort = sortSelect.value;
}

function loadJobIntoExecution(event, jobId) {
  consumeClick(event);
  const job = state.jobs.find((item) => item.id === jobId);
  if (!job) return;
  if (job.kind === "transfer") {
    const spec = job.metadata?.transfer_spec || {};
    const sourceItems = Array.isArray(spec.sources) ? spec.sources : [];
    state.transfer.sources = sourceItems
      .map((item) => {
        const serverId = item.server_id || "local";
        const server = serverById(serverId);
        const path = item.path || parseRsyncTargetPath(item.value || "") || item.value || "";
        const isDir = Boolean(item.is_dir) || String(item.value || "").trim().endsWith("/");
        return {
          key: transferSourceKey(serverId, path, isDir),
          serverId,
          serverName: server?.name || serverId,
          path,
          isDir,
          value: item.value || formatTransferSource(path, server, isDir),
        };
      })
      .filter((item) => item.path || item.value);
    state.transfer.ignores = Array.isArray(spec.excludes) ? spec.excludes.slice() : [];
    state.transfer.source = null;
    state.transfer.tree = {};
    state.transfer.target = null;
    state.transfer.targetTree = {};
    const sourceServerId = state.transfer.sources[0]?.serverId || "";
    if ($("transferSourceServerSelect") && sourceServerId) $("transferSourceServerSelect").value = sourceServerId;
    if ($("transferSourceInput")) {
      $("transferSourceInput").value = transferPathOnly(state.transfer.sources[0]?.path || state.transfer.sources[0]?.value || "");
    }
    if ($("transferTargetInput")) {
      $("transferTargetInput").value = transferPathOnly(spec.target || "");
    }
    if ($("transferTargetServerSelect") && spec.target_server_id) $("transferTargetServerSelect").value = spec.target_server_id;
    const form = $("transferForm");
    if (form) {
      form.elements.checksum.checked = Boolean(spec.options?.checksum);
      form.elements.size_only.checked = Boolean(spec.options?.size_only ?? true);
      form.elements.resume_partial.checked = Boolean(spec.options?.resume_partial ?? true);
    }
    syncIgnoreInputFromState();
    renderSelectedSources();
    renderTransferSourceOptions();
    renderTransferTargetOptions();
    renderTransferTree();
    renderTargetTree();
    switchProductTab("exec");
    switchExecTab("transfer");
    persistFormState("transferForm");
    $("transferMessage").textContent = `已载入 ${job.id}`;
    $("transferMessage").classList.remove("error");
    return;
  }
  const form = $("jobForm");
  if (!form) return;
  state.selectedServer = String(job.requested_server_id || job.server_id || state.selectedServer || "");
  state.selectedGpu = String(job.requested_gpu_index ?? job.gpu_index ?? "auto");
  saveStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer);
  renderFormOptions();
  $("serverSelect").value = $("serverSelect").querySelector(`option[value="${CSS.escape(state.selectedServer)}"]`)
    ? state.selectedServer
    : $("serverSelect").value;
  renderFormOptions();
  $("gpuSelect").value = Array.from($("gpuSelect").options).some((option) => option.value === String(state.selectedGpu))
    ? String(state.selectedGpu)
    : "auto";
  form.elements.command.value = job.command_display || job.command || "";
  form.elements.cwd.value = job.cwd || "";
  form.elements.env_name.value = job.env_name || "";
  form.elements.min_free_mib.value = job.min_free_mib ?? 0;
  form.elements.max_gpu_util.value = job.max_gpu_util ?? 10;
  form.elements.wait_for_idle.checked = Boolean(job.wait_for_idle);
  switchProductTab("exec");
  switchExecTab("job");
  persistFormState("jobForm");
  $("formMessage").textContent = `已载入 ${job.id}`;
  $("formMessage").classList.remove("error");
}

async function reorderQueuedJob(event, jobId, direction) {
  consumeClick(event);
  const button = event.currentTarget;
  if (button) button.disabled = true;
  try {
    await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    });
    await loadStatus(true);
  } catch (error) {
    showActionError(error);
  }
}

function renderWorkspaceNodeKindOptions() {
  const select = $("workspaceNodeKindSelect");
  if (!select) return;
  const current = select.value;
  select.innerHTML = Object.entries(WORKSPACE_NODE_TYPES)
    .map(([kind, meta]) => `<option value="${escapeHtml(kind)}">${escapeHtml(meta.label || kind)}</option>`)
    .join("");
  select.value = WORKSPACE_NODE_TYPES[current] ? current : "custom.step";
}

function renderWorkspaceNodeList() {
  const list = $("workspaceNodeList");
  const count = $("workspaceNodeCount");
  const meta = $("workspaceNodeMeta");
  if (!list) return;
  renderWorkspaceNodeKindOptions();
  const nodes = state.workspaceNodesDraft || [];
  if (count) count.textContent = `${nodes.length} 个节点`;
  if (meta) {
    const links = workspaceLinksFromNodes(nodes);
    meta.textContent = links.length
      ? `按顺序 handoff，共 ${links.length} 段`
      : "节点可新增、重排、删改";
  }
  if (!nodes.length) {
    list.innerHTML = '<div class="empty">还没有节点。先新增一个输入节点。</div>';
    return;
  }
  list.innerHTML = nodes.map((node, index) => {
    const active = node.id === state.selectedTemplateNodeId ? " active" : "";
    const handler = node.handler || {};
    const next = nodes[index + 1];
    const handoff = handler.handoff
      ? `<div class="workspace-node-link-note">${escapeHtml(handler.handoff)}</div>`
      : "";
    const runtime = workspaceNodeRuntimeSummary(node);
    return `
      <div class="workspace-node-stack">
        <div class="workspace-node-card${active}">
          <button class="workspace-node-main" type="button" data-action="select-workspace-node" data-node-id="${escapeHtml(node.id)}" title="选择这个实例节点，在右侧编辑配置、执行者和资源策略">
            <div class="workspace-node-head">
              <span class="workspace-node-title">${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</span>
              <span class="server-badge subtle">${escapeHtml(workspaceNodeLabel(node.kind))}</span>
            </div>
            <div class="workspace-node-meta">
              <span class="state ${escapeHtml(node.status || "draft")}">${escapeHtml(workspaceStatusLabel(node.status || "draft"))}</span>
              <span>${escapeHtml((handler.mode || "human") === "agent" ? "Agent" : (handler.mode || "human") === "system" ? "系统" : "人工")}</span>
              <span>${escapeHtml(workspaceAgentDisplayName(handler))}</span>
            </div>
            <div class="workspace-node-summary" title="${escapeHtml(workspaceNodeSummary(node))}">${escapeHtml(workspaceNodeSummary(node))}</div>
            ${runtime ? `<div class="workspace-node-runtime">${escapeHtml(runtime)}</div>` : ""}
          </button>
          <div class="workspace-node-actions">
            <button class="secondary mini" type="button" data-action="move-workspace-node" data-node-id="${escapeHtml(node.id)}" data-direction="up" title="把这个节点向前移动一位" ${index === 0 ? "disabled" : ""}>上移</button>
            <button class="secondary mini" type="button" data-action="move-workspace-node" data-node-id="${escapeHtml(node.id)}" data-direction="down" title="把这个节点向后移动一位" ${index === nodes.length - 1 ? "disabled" : ""}>下移</button>
            ${node.kind === "run.command" ? `<button class="secondary mini" type="button" data-action="run-workspace-node" data-node-id="${escapeHtml(node.id)}" title="只提交这个运行节点，用于单点调试；不会跑完整链路">运行节点</button>` : ""}
            ${node.kind === "run.command" ? `<button class="secondary mini" type="button" data-action="fill-job-from-node" data-node-id="${escapeHtml(node.id)}" title="把这个节点的命令、目录、环境和 GPU 策略填入通用执行面板">填入执行</button>` : ""}
            <button class="secondary mini danger" type="button" data-action="remove-workspace-node" data-node-id="${escapeHtml(node.id)}" title="从当前实例节点链中删除这个节点">删除</button>
          </div>
        </div>
        ${next ? `
          <div class="workspace-node-link-row">
            <span class="workspace-node-link-arrow">↓</span>
            <div>
              <div class="workspace-node-link-title">交接至 ${escapeHtml(next.title || workspaceNodeLabel(next.kind))}</div>
              ${handoff}
            </div>
          </div>
        ` : ""}
      </div>
    `;
  }).join("");
}

function renderWorkspaceNodeField(field, value) {
  const fieldId = `node-field-${field.key}`;
  if (field.type === "textarea") {
    return `
      <label>
        ${escapeHtml(field.label)}
        <textarea id="${escapeHtml(fieldId)}" data-config-key="${escapeHtml(field.key)}" rows="${escapeHtml(String(field.rows || 3))}" placeholder="${escapeHtml(field.placeholder || "")}">${escapeHtml(value || "")}</textarea>
      </label>
    `;
  }
  if (field.type === "select") {
    const options = (field.options || [])
      .map((option) => `<option value="${escapeHtml(option.value)}" ${String(option.value) === String(value || "") ? "selected" : ""}>${escapeHtml(option.label)}</option>`)
      .join("");
    return `
      <label>
        ${escapeHtml(field.label)}
        <select id="${escapeHtml(fieldId)}" data-config-key="${escapeHtml(field.key)}">${options}</select>
      </label>
    `;
  }
  return `
    <label>
      ${escapeHtml(field.label)}
      <input id="${escapeHtml(fieldId)}" data-config-key="${escapeHtml(field.key)}" value="${escapeHtml(value || "")}" placeholder="${escapeHtml(field.placeholder || "")}" />
    </label>
  `;
}

function renderWorkspaceNodeEditor() {
  const box = $("workspaceNodeEditor");
  if (!box) return;
  const node = selectedWorkspaceNode();
  if (!node) {
    box.innerHTML = '<div class="empty">选择一个节点后，在这里编辑执行者、交接说明和节点配置。</div>';
    return;
  }
  const meta = workspaceNodeMeta(node.kind);
  const agentOptions = [
    { value: "", label: "选择已定义 Agent" },
    ...state.workspaceAgentsDraft.map((agent) => ({
      value: agent.id,
      label: `${agent.name} · ${agent.role}`,
    })),
  ];
  const configFields = (meta.configFields || [])
    .map((field) => renderWorkspaceNodeField(field, node.config?.[field.key]))
    .join("");
  box.innerHTML = `
    <div class="workspace-node-editor-card">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</h4>
          <p class="muted">${escapeHtml(meta.description || "编辑这个节点的配置和交接信息。")}</p>
        </div>
        <span class="server-badge">${escapeHtml(workspaceNodeLabel(node.kind))}</span>
      </div>
      <div class="workspace-node-editor-grid">
        <label>
          节点标题
          <input data-node-field="title" value="${escapeHtml(node.title || "")}" placeholder="${escapeHtml(workspaceNodeLabel(node.kind))}" />
        </label>
        <label>
          节点状态
          <select data-node-field="status">
            ${["draft", "ready", "running", "blocked", "done"].map((status) => `<option value="${status}" ${status === node.status ? "selected" : ""}>${escapeHtml(workspaceStatusLabel(status))}</option>`).join("")}
          </select>
        </label>
        <label>
          执行者类型
          <select data-handler-field="mode">
            <option value="human" ${node.handler?.mode === "human" ? "selected" : ""}>人工</option>
            <option value="agent" ${node.handler?.mode === "agent" ? "selected" : ""}>Agent</option>
            <option value="system" ${node.handler?.mode === "system" ? "selected" : ""}>系统</option>
          </select>
        </label>
        <label>
          执行者标记
          <input data-handler-field="name" value="${escapeHtml(node.handler?.name || "")}" placeholder="例如 你 / Planner / Repo Scout / GPU Scout" />
        </label>
        <label>
          绑定 Agent
          <select data-handler-field="agent_id">
            ${agentOptions.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === String(node.handler?.agent_id || "") ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        </label>
      </div>
      <label>
        交接说明
        <textarea data-handler-field="handoff" rows="3" placeholder="这个节点完成后，下一节点应该拿到什么信息">${escapeHtml(node.handler?.handoff || "")}</textarea>
      </label>
      <label>
        节点备注
        <textarea data-node-field="notes" rows="3" placeholder="写补充约束、风险或检查点">${escapeHtml(node.notes || "")}</textarea>
      </label>
      ${workspaceNodeRuntimeSummary(node) ? `<div class="workspace-node-runtime">${escapeHtml(workspaceNodeRuntimeSummary(node))}</div>` : ""}
      <div class="workspace-node-config-grid">${configFields || '<div class="empty">这个节点暂时没有额外配置字段。</div>'}</div>
      <div class="workspace-node-editor-actions">
        <button class="secondary" type="button" data-action="sync-form-from-node" title="把当前节点的关键配置同步回项目概览表单">同步到概览</button>
        ${node.kind === "run.command" ? `<button class="secondary" type="button" data-action="run-workspace-node" data-node-id="${escapeHtml(node.id)}" title="只提交当前运行节点，用于单点调试；不会运行整条链">运行节点</button>` : ""}
        ${node.kind === "run.command" ? `<button class="secondary" type="button" data-action="fill-job-from-node" data-node-id="${escapeHtml(node.id)}" title="把当前运行节点的命令、目录、环境和 GPU 策略填入通用执行面板">填入执行面板</button>` : ""}
      </div>
    </div>
  `;
}

function workspaceItemCockpitSummary(workspace = {}) {
  const automation = workspaceAutomationSummary(workspace);
  const execution = workspace.execution && typeof workspace.execution === "object" ? workspace.execution : {};
  const executionNodes = Array.isArray(execution.nodes) ? execution.nodes : [];
  const currentNode = executionNodes.find((node) => node.id === execution.current_node_id) || executionNodes[0] || null;
  const counts = execution.counts && typeof execution.counts === "object" ? execution.counts : {};
  const activeCount = Number(counts.running || 0) + Number(counts.queued || 0) + Number(counts.starting || 0);
  const failedCount = Number(counts.failed || 0) + Number(counts.stopped || 0);
  const evidenceTotal = Array.isArray(workspace?.automation?.evidence)
    ? workspace.automation.evidence.reduce((sum, item) => sum + Number(item?.count || 0), 0)
    : 0;
  const next = automation?.advance || automation?.next || {};
  const readiness = automation?.executionReadiness || {};
  const gate = readiness.gate && typeof readiness.gate === "object" ? readiness.gate : {};
  return [
    {
      label: "自动化",
      status: automation?.status || workspace.status || "draft",
      value: automation ? `${automation.score}%` : workspaceStatusLabel(workspace.status || "draft"),
      detail: automation?.summary || "等待体检",
    },
    {
      label: "当前节点",
      status: currentNode?.status || workspace.status || "draft",
      value: currentNode?.title || currentNode?.kind || "未开始",
      detail: activeCount ? `${activeCount} 活跃` : failedCount ? `${failedCount} 失败` : `${Number(counts.done || 0)} 完成`,
    },
    {
      label: "下一步",
      status: next.status || gate.status || automation?.status || "draft",
      value: next.title || gate.title || "等待判断",
      detail: next.next_action || next.reason || gate.detail || `${evidenceTotal} 条证据`,
    },
  ];
}

function renderWorkspaces() {
  const list = $("workspaceList");
  const historyList = $("workspaceHistoryList");
  const count = $("workspaceCount");
  const targets = [list, historyList].filter(Boolean);
  if (!targets.length || !count) return;
  const items = state.workspaces.slice();
  count.textContent = `${items.length} 个实例`;
  if (!items.length) {
    targets.forEach((target) => {
      target.innerHTML = '<div class="empty">还没有任务实例。先输入目标并基于模板创建一条实例快照。</div>';
    });
    return;
  }
  const markup = items.map((workspace) => {
    const active = workspace.id === state.selectedWorkspaceId ? " active" : "";
    const recipe = workspaceRecipe(workspace) || {};
    const flow = (workspace.nodes || []).map((node) => node.title || node.kind).join(" -> ");
    const brief = String(workspace.brief || "").trim();
    const tags = (workspace.tags || []).slice(0, 4)
      .map((tag) => `<span class="server-badge subtle">${escapeHtml(tag)}</span>`)
      .join("");
    const execution = workspace.execution || {};
    const currentNode = Array.isArray(execution.nodes)
      ? execution.nodes.find((node) => node.id === execution.current_node_id) || execution.nodes[0] || null
      : null;
    const cockpitItems = workspaceItemCockpitSummary(workspace);
    const stateLine = currentNode
      ? `${currentNode.title || currentNode.kind} · ${workspaceStatusLabel(currentNode.status || "pending")}`
      : `节点 ${escapeHtml(String((workspace.nodes || []).length))}`;
    return `
      <div class="workspace-item-wrapper${active}">
        <button class="workspace-item${active}" type="button" data-action="select-workspace" data-workspace-id="${escapeHtml(workspace.id)}" title="选择这个任务实例，查看驾驶舱、执行链和运行记录">
          <div class="workspace-item-head">
            <strong>${escapeHtml(workspace.name || workspace.id)}</strong>
            <span class="state ${escapeHtml(workspace.status || "draft")}">${escapeHtml(workspaceStatusLabel(workspace.status || "draft"))}</span>
          </div>
          <div class="workspace-item-meta">${escapeHtml(workspace.template_name || "自定义实例")} · ${escapeHtml(workspaceSourceSummary(workspace))}</div>
          <div class="workspace-item-meta">${escapeHtml(stateLine)} · Agent ${escapeHtml(String((workspace.agents || []).length || 0))} · ${escapeHtml(workspace.workspace_dir || "-")}</div>
          <div class="workspace-item-cockpit">
            ${cockpitItems.map((item) => `
              <span class="workspace-item-cockpit-chip status-${escapeHtml(item.status || "draft")}" title="${escapeHtml(item.detail || "")}">
                <em>${escapeHtml(item.label)}</em>
                <strong>${escapeHtml(item.value)}</strong>
              </span>
            `).join("")}
          </div>
          ${brief ? `<div class="workspace-item-flow" title="${escapeHtml(brief)}">${escapeHtml(brief)}</div>` : ""}
          ${recipe.run_command ? `<div class="workspace-item-command" title="${escapeHtml(recipe.run_command)}">${escapeHtml(recipe.run_command)}</div>` : ""}
          <div class="workspace-item-flow" title="${escapeHtml(flow)}">${escapeHtml(flow)}</div>
          ${tags ? `<div class="workspace-item-tags">${tags}</div>` : ""}
        </button>
        <button class="icon-button mini danger" type="button" data-action="delete-workspace" data-workspace-id="${escapeHtml(workspace.id)}" title="删除项目">×</button>
      </div>
    `;
  }).join("");
  targets.forEach((target) => {
    target.innerHTML = markup;
  });
}

function switchWorkspaceMode(mode) {
  const next = ["use", "manage"].includes(String(mode || "")) ? String(mode) : "use";
  const changed = state.ui.workspaceMode !== next;
  state.ui.workspaceMode = next;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.workspaceMode, next);
  renderWorkspaceWorkbench();
}

function switchWorkspaceManageTab(tab) {
  const next = ["templates", "agents", "tools", "ai"].includes(String(tab || "")) ? String(tab) : "templates";
  const changed = state.ui.workspaceManageTab !== next;
  state.ui.workspaceManageTab = next;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.workspaceManageTab, next);
  renderWorkspaceWorkbench();
}

function workflowTemplateSummaryMarkup(template) {
  if (!template) return '<div class="empty">还没有模板。先在管理模式创建一条默认流。</div>';
  const nodes = Array.isArray(template.nodes) ? template.nodes : [];
  const chain = nodes
    .map((node) => {
      const handler = node.handler || {};
      const owner = handler.name || globalAgentById(handler.agent_id)?.name || "";
      return owner ? `${node.title || workspaceNodeLabel(node.kind)} · ${owner}` : node.title || workspaceNodeLabel(node.kind);
    })
    .slice(0, 6);
  const model = template.model || {};
  const profile = providerProfileById(model.provider_profile_id);
  return `
    <div class="workspace-template-summary-card">
      <div class="workspace-template-summary-line">
        <strong>${escapeHtml(template.name || template.id)}</strong>
        <span class="server-badge subtle">${escapeHtml(template.source?.type || "repo")}</span>
      </div>
      <div class="workspace-template-summary-text">${escapeHtml(template.description || template.brief || "这条模板会被复制成实例快照，再进入执行链。")}</div>
      <div class="workspace-template-summary-meta">
        <span>${nodes.length} 个节点</span>
        <span>${template.agent_count || template.agent_ids?.length || 0} 个 Agent</span>
        <span>${template.tool_count || template.tool_ids?.length || 0} 个工具</span>
        <span>${escapeHtml(profile ? providerProfileLabel(profile) : model.routing_mode || "workspace_default")}</span>
      </div>
      <div class="workspace-template-summary-chain">
        ${chain.map((item) => `<span class="workspace-template-chip">${escapeHtml(item)}</span>`).join("") || '<span class="workspace-template-chip">空模板</span>'}
      </div>
    </div>
  `;
}

function renderWorkspaceUseMode() {
  const templateSelect = $("workspaceTemplateSelect");
  const templateSummary = $("workspaceTemplateSummary");
  if (templateSelect) {
    if (!state.workflowTemplates.length) {
      templateSelect.innerHTML = '<option value="">暂无模板</option>';
      templateSelect.disabled = true;
    } else {
      if (!selectedWorkflowTemplate()) {
        state.selectedWorkflowTemplateId = state.workflowTemplates[0].id;
        saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, state.selectedWorkflowTemplateId);
      }
      templateSelect.disabled = false;
      templateSelect.innerHTML = state.workflowTemplates
        .map((template) => `<option value="${escapeHtml(template.id)}">${escapeHtml(template.name || template.id)}</option>`)
        .join("");
      templateSelect.value = state.selectedWorkflowTemplateId || state.workflowTemplates[0]?.id || "";
    }
  }
  if (templateSummary) templateSummary.innerHTML = workflowTemplateSummaryMarkup(selectedWorkflowTemplate());
  renderWorkspaceCockpitOverview();
  renderWorkspaceExecutionBoard();
  renderWorkspaceExecutionDetail();
  renderWorkspaceUseChat();
}

function renderWorkspaceExecutionBoard() {
  const workspace = selectedWorkspace();
  const box = $("workspaceExecutionBoard");
  const meta = $("workspaceExecutionMeta");
  if (!box) return;
  if (!workspace) {
    const template = selectedWorkflowTemplate();
    const previewNodes = templatePreviewExecutionNodes(template);
    if (!template || !previewNodes.length) {
      if (meta) meta.textContent = "先创建或选择一个任务实例。";
      box.innerHTML = '<div class="empty">工作流实例会在这里展开成按顺序排列的节点执行看板。</div>';
      return;
    }
    if (meta) meta.textContent = `模板预览 · ${template.name || template.id} · ${previewNodes.length} 个节点`;
    if (!state.selectedWorkspaceExecutionNodeId || !previewNodes.some((node) => node.id === state.selectedWorkspaceExecutionNodeId)) {
      const savedNodeId = savedWorkspaceExecutionNodeId(workspaceExecutionSelectionKey(null, template));
      state.selectedWorkspaceExecutionNodeId = previewNodes.some((node) => node.id === savedNodeId)
        ? savedNodeId
        : previewNodes[0]?.id || "";
    }
    const agentCount = template.agent_count || template.agent_ids?.length || 0;
    const toolCount = template.tool_count || template.tool_ids?.length || 0;
    box.innerHTML = `
      <article class="workspace-empty-state">
        <div class="workspace-empty-state-copy">
          <strong>${escapeHtml(template.name || template.id)}</strong>
          <p>${escapeHtml(template.description || template.brief || "当前展示的是模板顺序预览。输入任务并创建实例后，才会生成真实状态、日志和对话。")}</p>
        </div>
        <div class="workspace-empty-chip-row">
          <span class="workspace-empty-chip">${escapeHtml(template.source?.type || "idea")}</span>
          <span class="workspace-empty-chip">${previewNodes.length} 个节点</span>
          <span class="workspace-empty-chip">${agentCount} 个 Agent</span>
          <span class="workspace-empty-chip">${toolCount} 个工具</span>
        </div>
      </article>
      ${workspaceExecutionChainMarkup(previewNodes, { preview: true })}
    `;
    return;
  }
  const execution = workspace.execution || {};
  const nodes = Array.isArray(execution.nodes) && execution.nodes.length
    ? execution.nodes
    : (workspace.nodes || []).map((node) => ({
        id: node.id,
        kind: node.kind,
        title: node.title || workspaceNodeLabel(node.kind),
        status: "pending",
        agent_id: node.handler?.agent_id || "",
        agent_name: node.handler?.name || "",
        error: "",
        job_id: "",
        job_status: "",
      }));
  const counts = execution.counts || {};
  if (meta) {
    meta.textContent = `当前节点 ${execution.current_node_id || "未开始"} · 待执行 ${counts.pending || 0} · 排队 ${counts.queued || 0} · 运行 ${counts.running || 0} · 完成 ${counts.done || 0} · 失败 ${counts.failed || 0}`;
  }
  if (!state.selectedWorkspaceExecutionNodeId || !nodes.some((node) => node.id === state.selectedWorkspaceExecutionNodeId)) {
    const savedNodeId = savedWorkspaceExecutionNodeId(workspaceExecutionSelectionKey(workspace));
    state.selectedWorkspaceExecutionNodeId = nodes.some((node) => node.id === savedNodeId)
      ? savedNodeId
      : execution.current_node_id || nodes[0]?.id || "";
  }
  box.innerHTML = workspaceExecutionChainMarkup(nodes);
}

function renderWorkspaceExecutionDetail() {
  const box = $("workspaceExecutionDetail");
  const meta = $("workspaceSelectedInstanceMeta");
  const workspace = selectedWorkspace();
  if (!box) return;
  if (!workspace) {
    const template = selectedWorkflowTemplate();
    const node = selectedExecutionPreviewNode();
    if (!template) {
      if (meta) meta.textContent = "选择实例后显示";
      box.innerHTML = '<div class="empty">右侧会显示当前节点、最近运行、错误和输出入口。</div>';
      return;
    }
    const sourceSummary = workspaceSourceSummary(template);
    const handlerName = node?.agent_name || globalAgentById(node?.agent_id || "")?.name || "未指派 Agent";
    const profile = providerProfileById(template.model?.provider_profile_id || "");
    const sourceNode = (template.nodes || []).find((item) => item.id === node?.id) || null;
    const nodeConfig = sourceNode?.config || {};
    const nodePosition = workspaceExecutionNodePosition(templatePreviewExecutionNodes(template), node);
    if (meta) meta.textContent = "模板预览 · 创建实例后会变成运行快照";
    box.innerHTML = `
      <div class="workspace-detail-hero preview">
        <div class="workspace-detail-hero-copy">
          <span>当前模板</span>
          <strong>${escapeHtml(template.name || template.id)}</strong>
          <em>${escapeHtml(sourceSummary)}</em>
        </div>
        <div class="workspace-detail-hero-side">
          <span class="state preview">${escapeHtml(workspaceStatusLabel("preview"))}</span>
          <small>未创建实例</small>
        </div>
      </div>
      <div class="workspace-detail-facts">
        <article class="workspace-detail-fact">
          <span>默认来源</span>
          <strong>${escapeHtml(template.source?.type || "idea")}</strong>
          <em>${escapeHtml((template.nodes || []).length)} 个节点</em>
        </article>
        <article class="workspace-detail-fact">
          <span>预览节点</span>
          <strong>${escapeHtml(node?.title || "未选择")}</strong>
          <em>${escapeHtml(handlerName)}</em>
        </article>
        <article class="workspace-detail-fact">
          <span>链路位置</span>
          <strong>${escapeHtml(nodePosition.label)}</strong>
          <em>${escapeHtml(nodePosition.detail)}</em>
        </article>
        <article class="workspace-detail-fact">
          <span>默认路由</span>
          <strong>${escapeHtml(profile ? providerProfileLabel(profile) : template.model?.routing_mode || "workspace_default")}</strong>
          <em>${escapeHtml(globalAgentById(template.model?.chat_agent_id || "")?.name || template.model?.chat_agent_id || "未设置聊天 Agent")}</em>
        </article>
      </div>
      <div class="workspace-detail-block">
        <div class="subsection-head">
          <strong>节点接管</strong>
          <span class="muted">Agent / Tool / AI</span>
        </div>
        ${workspaceNodeAgentContractMarkup(node, sourceNode, { template })}
      </div>
      <div class="workspace-detail-block">
        <div class="subsection-head">
          <strong>I/O 契约</strong>
          <span class="muted">input_mapping / output_key / context</span>
        </div>
        ${workspaceNodeIoContractMarkup(node, sourceNode, { template })}
      </div>
      <div class="workspace-detail-block">
        <div class="subsection-head">
          <strong>预览节点详情</strong>
          <span class="muted">${escapeHtml(node?.kind || "未选择")}</span>
        </div>
        <pre class="workspace-detail-pre">${escapeHtml(JSON.stringify(nodeConfig, null, 2) || "{}")}</pre>
      </div>
      <div class="workspace-detail-block">
        <div class="subsection-head">
          <strong>创建实例后会带上</strong>
          <span class="muted">运行快照</span>
        </div>
        <div class="workspace-detail-mini-list">
          <div class="workspace-detail-mini-item">模板节点、Agent 和工具会复制成独立快照</div>
          <div class="workspace-detail-mini-item">任务输入会归档到 inputs，并自动推导 repo / paper / idea / mixed</div>
          <div class="workspace-detail-mini-item">节点会显示排队、运行、完成、失败和最近日志</div>
          <div class="workspace-detail-mini-item">右侧实例对话和历史运行会持续绑定到这份快照</div>
        </div>
      </div>
    `;
    return;
  }
  const node = selectedWorkspaceExecutionNode();
  const jobs = workspaceJobs();
  const recent = jobs.slice(0, 5);
  const execution = workspace.execution || {};
  const currentAgent = globalAgentById(execution.current_agent_id || "") || (workspace.agents || []).find((item) => item.id === execution.current_agent_id) || null;
  const counts = execution.counts || {};
  const inputs = workspace.inputs || {};
  const repoCount = Array.isArray(inputs.repo_urls) ? inputs.repo_urls.length : 0;
  const paperCount = Array.isArray(inputs.paper_urls) ? inputs.paper_urls.length : 0;
  const referenceCount = Array.isArray(inputs.references) ? inputs.references.length : Array.isArray(workspace.references) ? workspace.references.length : 0;
  const contextCount = Array.isArray(inputs.context_blocks) ? inputs.context_blocks.length : 0;
  const totalNodes = Array.isArray(workspace.nodes) ? workspace.nodes.length : 0;
  const selectedStatus = node?.status || execution.last_job_status || workspace.status || "ready";
  if (meta) {
    meta.textContent = `${workspace.template_name || "实例"} · ${workspace.status || "ready"} · ${workspace.workspace_dir || "未设工作目录"}`;
  }
  const sourceNode = (workspace.nodes || []).find((item) => item.id === node?.id) || null;
  const nodeConfig = sourceNode?.config || {};
  const nodeTrace = workspaceRuntimeTrace(node);
  const nodeArtifacts = workspaceRuntimeArtifacts(node);
  const nodeResources = workspaceRuntimeResources(node);
  const executionNodesForPosition = Array.isArray(execution.nodes) && execution.nodes.length ? execution.nodes : (workspace.nodes || []);
  const nodePosition = workspaceExecutionNodePosition(executionNodesForPosition, node);
  box.innerHTML = `
    <div class="workspace-detail-hero">
      <div class="workspace-detail-hero-copy">
        <span>实例快照</span>
        <strong>${escapeHtml(workspace.template_name || workspace.name || "任务实例")}</strong>
        <em>${escapeHtml(workspaceSourceSummary(workspace))}</em>
      </div>
      <div class="workspace-detail-hero-side">
        <span class="state ${escapeHtml(selectedStatus)}">${escapeHtml(workspaceStatusLabel(selectedStatus))}</span>
        <small>${escapeHtml(workspace.workspace_dir || "未设工作目录")}</small>
      </div>
    </div>
    <div class="workspace-detail-summary">
      <article class="workspace-detail-card">
        <span>模板快照</span>
        <strong>${escapeHtml(workspace.template_name || "未关联模板")}</strong>
        <em>${escapeHtml(workspaceSourceSummary(workspace))}</em>
      </article>
      <article class="workspace-detail-card">
        <span>当前节点</span>
        <strong>${escapeHtml(node?.title || "未开始")}</strong>
        <em>${escapeHtml(node?.agent_name || currentAgent?.name || "未分配 Agent")}</em>
      </article>
      <article class="workspace-detail-card">
        <span>链路位置</span>
        <strong>${escapeHtml(nodePosition.label)}</strong>
        <em>${escapeHtml(nodePosition.detail)}</em>
      </article>
      <article class="workspace-detail-card">
        <span>最近状态</span>
        <strong>${escapeHtml(workspaceStatusLabel(node?.status || execution.last_job_status || "ready"))}</strong>
        <em>${escapeHtml(execution.latest_error || "没有最近错误")}</em>
      </article>
      <article class="workspace-detail-card">
        <span>执行概况</span>
        <strong>${escapeHtml(`${counts.done || 0}/${totalNodes || 0}`)}</strong>
        <em>${escapeHtml(`排队 ${counts.queued || 0} · 运行 ${counts.running || 0} · 失败 ${counts.failed || 0}`)}</em>
      </article>
    </div>
    <div class="workspace-detail-facts">
      <article class="workspace-detail-fact">
        <span>任务输入</span>
        <strong>${escapeHtml(`${repoCount} repo · ${paperCount} paper`)}</strong>
        <em>${escapeHtml(`${referenceCount} 条参考 · ${contextCount} 条上下文`)}</em>
      </article>
      <article class="workspace-detail-fact">
        <span>当前 Agent</span>
        <strong>${escapeHtml(node?.agent_name || currentAgent?.name || "未分配 Agent")}</strong>
        <em>${escapeHtml(currentAgent?.role || node?.kind || "等待开始")}</em>
      </article>
      <article class="workspace-detail-fact">
        <span>最近任务</span>
        <strong>${escapeHtml(execution.last_job_id || "还没有")}</strong>
        <em>${escapeHtml(execution.latest_error || "没有最近错误")}</em>
      </article>
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>节点接管</strong>
        <span class="muted">Agent / Tool / AI</span>
      </div>
      ${workspaceNodeAgentContractMarkup(node, sourceNode, { workspace })}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>I/O 契约</strong>
        <span class="muted">workflow_contract_node</span>
      </div>
      ${workspaceNodeIoContractMarkup(node, sourceNode, { workspace })}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>执行上下文</strong>
        <span class="muted">input_data / context.outputs / step_results</span>
      </div>
      ${workspaceExecutionContextBusMarkup(workspace, { limit: 10 })}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>复现/部署清单</strong>
        <span class="muted">source / data / env / gpu / run / artifact</span>
      </div>
      ${workspaceReproductionManifestMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>节点态势</strong>
        <span class="muted">${escapeHtml(node?.kind || "未开始")}</span>
      </div>
      ${workspaceNodeAutomationScopeMarkup(workspace, node, sourceNode)}
    </div>
    ${workspaceNodeExecutionPlanMarkup(workspace, node, sourceNode)}
    ${workspaceNodeNextActionMarkup(workspace, node, sourceNode)}
    <div class="workspace-detail-actions">
      <button class="primary" type="button" data-action="advance-workspace-automation" title="让系统根据当前门禁状态自动决定：发现、观察、复查失败、回填后完整运行">自动推进</button>
      <button class="secondary" type="button" data-action="apply-workspace-automation" title="把默认建议和发现证据回填到节点配置，例如路径、环境命令、GPU 策略和产物路径">回填建议/发现</button>
      <button class="secondary" type="button" data-action="run-workspace-discovery" title="提交安全发现链，只收集源码、路径、数据、环境、GPU 和产物入口证据">自动发现</button>
      <button class="secondary" type="button" data-action="run-selected-workspace" title="在门禁通过后提交完整工作流；门禁不通过时不会创建半截队列">运行工作流</button>
      ${node?.id ? `<button class="secondary" type="button" data-action="run-selected-node" data-node-id="${escapeHtml(node.id)}" title="只运行当前选中的节点，用于单点调试或补证据">运行当前节点</button>` : ""}
      ${node?.job_id ? `<button class="secondary" type="button" data-action="open-selected-node-log" data-job-id="${escapeHtml(node.job_id)}" title="打开当前节点最近一次绑定任务的日志输出">打开最近输出</button>` : ""}
      ${workspace.id ? `<button class="secondary" type="button" data-action="fill-job-from-selected-workspace" title="把当前工作区和运行节点填入通用执行面板，便于手动调整命令后提交">填入执行面板</button>` : ""}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>执行准备清单</strong>
        <span class="muted">${escapeHtml(workspace.automation?.execution_readiness?.summary || "等待准备")}</span>
      </div>
      ${workspaceAutomationExecutionReadinessMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>自动推进建议</strong>
        <span class="muted">${escapeHtml(workspace.automation?.advance?.next_action || "等待判断")}</span>
      </div>
      ${workspaceAutomationAdvanceMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>自动化体检</strong>
        <span class="muted">${escapeHtml(workspace.automation?.summary || "等待检查")}</span>
      </div>
      ${workspaceAutomationCheckMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>发现证据</strong>
        <span class="muted">路径、数据、环境、GPU、产物、指标</span>
      </div>
      ${workspaceAutomationEvidenceMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>证据回填解释</strong>
        <span class="muted">${escapeHtml(workspace.automation?.evidence_backfill?.summary || "等待发现证据")}</span>
      </div>
      ${workspaceEvidenceBackfillMarkup(workspace, { limit: 12 })}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>资源/数据/环境/GPU 调度</strong>
        <span class="muted">${escapeHtml(workspace.automation?.resource_orchestration?.summary || "等待调度")}</span>
      </div>
      ${workspaceAutomationResourceMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>报告草稿</strong>
        <span class="muted">${escapeHtml(workspace.automation?.report?.headline || "等待证据")}</span>
      </div>
      ${workspaceAutomationReportMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>运行预案</strong>
        <span class="muted">${escapeHtml(workspace.automation?.run_plan?.summary || "等待生成")}</span>
      </div>
      ${workspaceAutomationRunPlanMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>Agent / Tool / AI 分层</strong>
        <span class="muted">${escapeHtml(workspace.automation?.agent_topology?.summary || "等待拓扑")}</span>
      </div>
      ${workspaceAutomationAgentTopologyMarkup(workspace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>资源计划</strong>
        <span class="muted">${escapeHtml(node?.kind || "未开始")}</span>
      </div>
      ${workspaceDetailResourceMarkup(nodeResources)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>节点 Trace</strong>
        <span class="muted">${nodeTrace.length} 条</span>
      </div>
      ${workspaceDetailTraceMarkup(nodeTrace)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>产物与路径</strong>
        <span class="muted">${nodeArtifacts.length} 项</span>
      </div>
      ${workspaceDetailArtifactsMarkup(nodeArtifacts)}
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>节点配置</strong>
        <span class="muted">${escapeHtml(node?.kind || "未开始")}</span>
      </div>
      <pre class="workspace-detail-pre">${escapeHtml(JSON.stringify(nodeConfig, null, 2) || "{}")}</pre>
    </div>
    <div class="workspace-detail-block">
      <div class="subsection-head">
        <strong>最近运行</strong>
        <span class="muted">${recent.length} 条</span>
      </div>
      ${recent.length ? `
        <div class="workspace-detail-run-list">
          ${recent.map((job) => `
            <button class="workspace-detail-run" type="button" data-action="open-workspace-run" data-job-id="${escapeHtml(job.id)}" title="打开这条节点运行记录的输出日志">
              <strong>${escapeHtml(job.name || job.id)}</strong>
              <span>${escapeHtml(zhStatus(job.status || "queued"))}</span>
              <em>${escapeHtml(job.metadata?.node_title || job.kind || "任务")} · ${escapeHtml(fmtDate(job.started_at || job.created_at || ""))}</em>
            </button>
          `).join("")}
        </div>
      ` : '<div class="empty">还没有运行记录。</div>'}
    </div>
  `;
}

function renderWorkspaceUseChat() {
  const workspace = selectedWorkspace();
  const list = $("workspaceUseChatList");
  const select = $("workspaceUseChatAgentSelect");
  const hint = $("workspaceUseChatHint");
  if (select) {
    const agents = Array.isArray(workspace?.agents) ? workspace.agents : [];
    select.innerHTML = agents.length
      ? agents.map((agent) => `<option value="${escapeHtml(agent.id)}">${escapeHtml(agent.name || agent.id)}</option>`).join("")
      : '<option value="">暂无 Agent</option>';
    const defaultAgentId = workspace?.model?.chat_agent_id || agents[0]?.id || "";
    select.value = agents.some((agent) => agent.id === defaultAgentId) ? defaultAgentId : agents[0]?.id || "";
    select.disabled = !agents.length;
  }
  if (hint) hint.textContent = workspace?.template_name ? `实例来自 ${workspace.template_name}` : "";
  if (!list) return;
  if (!workspace) {
    list.innerHTML = '<div class="empty">选择实例后，在这里继续对话。</div>';
    return;
  }
  const chat = Array.isArray(workspace.chat) ? workspace.chat : [];
  if (!chat.length) {
    list.innerHTML = '<div class="empty">当前实例还没有消息。</div>';
    return;
  }
  list.innerHTML = chat.slice(-24).map((message) => `
    <article class="workspace-chat-message ${escapeHtml(message.role || "user")}">
      <div class="workspace-chat-message-head">
        <strong>${escapeHtml(message.agent_name || message.role || "user")}</strong>
        <span>${escapeHtml(fmtDate(message.created_at || ""))}</span>
      </div>
      <div class="workspace-chat-message-body">${escapeHtml(message.text || "")}</div>
    </article>
  `).join("");
}

function renderWorkspaceModeSwitch() {
  const mode = state.ui.workspaceMode || "use";
  $("workspaceUseModePanel")?.toggleAttribute("hidden", mode !== "use");
  $("workspaceManageModePanel")?.toggleAttribute("hidden", mode !== "manage");
  document.querySelectorAll("#workspaceModeSwitch [data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  document.querySelectorAll("#workspaceManageTabs [data-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.ui.workspaceManageTab);
  });
  ["templates", "agents", "tools", "ai"].forEach((tab) => {
    $(`workspaceManage${tab.charAt(0).toUpperCase() + tab.slice(1)}Panel`)?.toggleAttribute("hidden", state.ui.workspaceManageTab !== tab);
  });
}

function renderManageTemplateList() {
  const list = $("workflowTemplateList");
  if (!list) return;
  if (!state.workflowTemplates.length) {
    list.innerHTML = '<div class="empty">还没有工作流模板。</div>';
    return;
  }
  list.innerHTML = state.workflowTemplates.map((template) => {
    const active = template.id === state.selectedWorkflowTemplateId ? " active" : "";
    const nodeCount = Array.isArray(template.nodes) ? template.nodes.length : template.node_count || 0;
    return `
      <button class="workspace-template-item${active}" type="button" data-action="select-workflow-template" data-template-id="${escapeHtml(template.id)}" title="选择这个 Starter Chain 模板并编辑默认节点链">
        <div class="workspace-template-item-head">
          <strong>${escapeHtml(template.name || template.id)}</strong>
          <span class="state ${escapeHtml(template.status || "ready")}">${escapeHtml(workspaceStatusLabel(template.status || "ready"))}</span>
        </div>
        <div class="workspace-template-item-meta">${escapeHtml(template.source?.type || "repo")} · ${nodeCount} 个节点</div>
        <div class="workspace-template-item-desc">${escapeHtml(template.description || template.brief || "未填写模板描述")}</div>
      </button>
    `;
  }).join("");
}

function renderWorkflowTemplateNodeKindOptions() {
  const select = $("workflowTemplateNodeKindSelect");
  if (!select) return;
  const current = select.value;
  select.innerHTML = Object.entries(WORKSPACE_NODE_TYPES)
    .map(([kind, meta]) => `<option value="${escapeHtml(kind)}">${escapeHtml(meta.label || kind)}</option>`)
    .join("");
  select.value = WORKSPACE_NODE_TYPES[current] ? current : "custom.step";
}

function renderWorkflowTemplateNodeList() {
  const list = $("workflowTemplateNodeList");
  if (!list) return;
  renderWorkflowTemplateNodeKindOptions();
  const nodes = Array.isArray(state.workflowTemplateDraft?.nodes) ? state.workflowTemplateDraft.nodes : [];
  if (!nodes.length) {
    list.innerHTML = '<div class="empty">模板里还没有节点。</div>';
    return;
  }
  list.innerHTML = nodes.map((node, index) => {
    const active = node.id === state.selectedTemplateNodeId ? " active" : "";
    const handler = node.handler || {};
    const agent = globalAgentById(handler.agent_id || "");
    return `
      <div class="workspace-node-stack">
        <button class="workspace-node-card${active}" type="button" data-action="select-template-node" data-node-id="${escapeHtml(node.id)}" title="选择这个模板节点，编辑默认配置和绑定 Agent">
          <div class="workspace-node-head">
            <span class="workspace-node-title">${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</span>
            <span class="server-badge subtle">${index + 1}</span>
          </div>
          <div class="workspace-node-meta">
            <span class="state ${escapeHtml(node.status || "ready")}">${escapeHtml(workspaceStatusLabel(node.status || "ready"))}</span>
            <span>${escapeHtml(workspaceNodeLabel(node.kind))}</span>
            <span>${escapeHtml(handler.name || agent?.name || "未指派")}</span>
          </div>
          <div class="workspace-node-summary">${escapeHtml(workspaceNodeSummary(node))}</div>
        </button>
        ${index < nodes.length - 1 ? '<div class="workspace-node-link-row"><span class="workspace-node-link-arrow">↓</span><div><div class="workspace-node-link-title">顺序交接</div></div></div>' : ""}
      </div>
    `;
  }).join("");
}

function renderWorkflowTemplateNodeEditor() {
  const box = $("workflowTemplateNodeEditor");
  if (!box) return;
  const node = selectedWorkflowTemplateNode();
  if (!node) {
    box.innerHTML = '<div class="empty">选择一个节点后，在这里编辑配置。</div>';
    return;
  }
  const meta = workspaceNodeMeta(node.kind);
  const agentOptions = [
    { value: "", label: "选择全局 Agent" },
    ...state.agentDefinitions.map((agent) => ({
      value: agent.id,
      label: `${agent.name || agent.id} · ${agent.role || agent.id}`,
    })),
  ];
  const configFields = (meta.configFields || [])
    .map((field) => renderWorkspaceNodeField(field, node.config?.[field.key]))
    .join("");
  box.innerHTML = `
    <div class="workspace-node-editor-card">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(node.title || workspaceNodeLabel(node.kind))}</h4>
          <p class="muted">${escapeHtml(meta.description || "编辑模板节点")}</p>
        </div>
        <span class="server-badge">${escapeHtml(workspaceNodeLabel(node.kind))}</span>
      </div>
      <div class="workspace-node-editor-grid">
        <label>
          节点标题
          <input data-manage-node-field="title" value="${escapeHtml(node.title || "")}" placeholder="${escapeHtml(workspaceNodeLabel(node.kind))}" />
        </label>
        <label>
          节点状态
          <select data-manage-node-field="status">
            ${["ready", "draft", "blocked", "running", "done"].map((status) => `<option value="${status}" ${status === node.status ? "selected" : ""}>${escapeHtml(workspaceStatusLabel(status))}</option>`).join("")}
          </select>
        </label>
        <label>
          执行者类型
          <select data-manage-handler-field="mode">
            <option value="human" ${node.handler?.mode === "human" ? "selected" : ""}>人工</option>
            <option value="agent" ${node.handler?.mode === "agent" ? "selected" : ""}>Agent</option>
            <option value="system" ${node.handler?.mode === "system" ? "selected" : ""}>系统</option>
          </select>
        </label>
        <label>
          归属 Agent
          <select data-manage-handler-field="agent_id">
            ${agentOptions.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === node.handler?.agent_id ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        </label>
      </div>
      <label>
        显示名 / 责任人
        <input data-manage-handler-field="name" value="${escapeHtml(node.handler?.name || "")}" placeholder="例如 Repo Scout" />
      </label>
      <label>
        交接说明
        <textarea data-manage-handler-field="handoff" rows="3" placeholder="这个节点结束后，下一步应该拿着什么继续执行">${escapeHtml(node.handler?.handoff || "")}</textarea>
      </label>
      <div class="workspace-node-editor-grid">
        ${configFields || '<div class="empty">这个节点当前没有额外配置字段。</div>'}
      </div>
      <label>
        节点备注
        <textarea data-manage-node-field="notes" rows="3" placeholder="可以写人工检查点、边界或特别说明">${escapeHtml(node.notes || "")}</textarea>
      </label>
    </div>
  `;
}

function renderManageTemplateModule() {
  const draft = state.workflowTemplateDraft && Object.keys(state.workflowTemplateDraft).length
    ? normalizeWorkflowTemplateDraft(state.workflowTemplateDraft)
    : selectedWorkflowTemplate()
      ? normalizeWorkflowTemplateDraft(selectedWorkflowTemplate())
      : defaultWorkflowTemplateDraft("repo");
  state.workflowTemplateDraft = draft;
  if (!state.selectedTemplateNodeId || !draft.nodes.some((node) => node.id === state.selectedTemplateNodeId)) {
    state.selectedTemplateNodeId = draft.nodes[0]?.id || "";
  }
  if ($("workflowTemplateTitle")) $("workflowTemplateTitle").textContent = draft.name || "工作流模板";
  if ($("workflowTemplateMeta")) $("workflowTemplateMeta").textContent = `${draft.source?.type || "repo"} · ${draft.nodes.length} 个节点 · ${draft.tags.length} 个标签`;
  if ($("templateNameInput")) $("templateNameInput").value = draft.name || "";
  if ($("templateSourceTypeSelect")) $("templateSourceTypeSelect").value = draft.source?.type || "repo";
  if ($("templateStatusSelect")) $("templateStatusSelect").value = draft.status || "ready";
  if ($("templateTagsInput")) $("templateTagsInput").value = (draft.tags || []).join(",");
  if ($("templateDescriptionInput")) $("templateDescriptionInput").value = draft.description || "";
  if ($("templateBriefInput")) $("templateBriefInput").value = draft.brief || "";
  if ($("templateRepoUrlInput")) $("templateRepoUrlInput").value = draft.source?.repo_url || "";
  if ($("templateRepoRefInput")) $("templateRepoRefInput").value = draft.source?.repo_ref || "";
  if ($("templatePaperUrlInput")) $("templatePaperUrlInput").value = draft.source?.paper_url || "";
  if ($("templateWorkspaceDirInput")) $("templateWorkspaceDirInput").value = draft.workspace_dir || "";
  if ($("templateIdeaInput")) $("templateIdeaInput").value = draft.source?.idea_text || "";
  if ($("templateEnvNameInput")) $("templateEnvNameInput").value = draft.env?.name || "";
  if ($("templateEnvManagerSelect")) $("templateEnvManagerSelect").value = draft.env?.manager || "conda";
  if ($("templatePythonVersionInput")) $("templatePythonVersionInput").value = draft.env?.python || "";
  if ($("templateProviderProfileSelect")) {
    $("templateProviderProfileSelect").innerHTML = `<option value="">未选择</option>${state.providerProfiles.map((profile) => `<option value="${escapeHtml(profile.id)}">${escapeHtml(providerProfileLabel(profile))}</option>`).join("")}`;
    $("templateProviderProfileSelect").value = draft.model?.provider_profile_id || "";
  }
  if ($("templateRoutingModeSelect")) $("templateRoutingModeSelect").value = draft.model?.routing_mode || "workspace_default";
  if ($("templateChatAgentSelect")) {
    $("templateChatAgentSelect").innerHTML = `<option value="">未选择</option>${state.agentDefinitions.map((agent) => `<option value="${escapeHtml(agent.id)}">${escapeHtml(agent.name || agent.id)}</option>`).join("")}`;
    $("templateChatAgentSelect").value = draft.model?.chat_agent_id || "";
  }
  renderWorkflowTemplateStudioOverview();
  renderManageTemplateList();
  renderWorkflowTemplateNodeList();
  renderWorkflowTemplateNodeEditor();
}

function selectGlobalAgent(agentId) {
  const agent = globalAgentById(agentId);
  if (!agent) return;
  const changed = state.selectedGlobalAgentId !== agent.id;
  state.selectedGlobalAgentId = agent.id;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedGlobalAgent, agent.id);
  state.agentDefinitionDraft = normalizeGlobalAgentDefinitionDraft(agent);
  state.manageAgentDebug = {
    agentId: agent.id,
    templateId: state.selectedWorkflowTemplateId || state.workflowTemplates[0]?.id || "",
    input: "",
    result: null,
    busy: false,
    error: "",
  };
  state.ui.agentDefinitionDirty = false;
  renderWorkspaceWorkbench();
}

function selectGlobalTool(toolId) {
  const tool = globalToolById(toolId);
  if (!tool) return;
  const changed = state.selectedGlobalToolId !== tool.id;
  state.selectedGlobalToolId = tool.id;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedGlobalTool, tool.id);
  state.toolDefinitionDraft = normalizeGlobalToolDefinitionDraft(tool);
  state.ui.toolDefinitionDirty = false;
  renderWorkspaceWorkbench();
}

function renderManageAgentModule() {
  const list = $("manageAgentList");
  const editor = $("manageAgentEditor");
  if (!selectedGlobalAgent() && state.agentDefinitions.length) {
    state.selectedGlobalAgentId = state.agentDefinitions[0].id;
    saveStoredValue(STORAGE_KEYS.selectedGlobalAgent, state.selectedGlobalAgentId);
  }
  if (!state.agentDefinitionDraft.id && selectedGlobalAgent()) {
    state.agentDefinitionDraft = normalizeGlobalAgentDefinitionDraft(selectedGlobalAgent());
  }
  if (list) {
    list.innerHTML = state.agentDefinitions.length
      ? state.agentDefinitions.map((agent) => {
          const active = agent.id === state.selectedGlobalAgentId ? " active" : "";
          return `
            <button class="workspace-template-item${active}" type="button" data-action="select-global-agent" data-agent-id="${escapeHtml(agent.id)}" title="选择这个全局 Agent 定义，编辑后会影响引用它的新模板快照">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(agent.name || agent.id)}</strong>
                <span class="state ${agent.enabled === false ? "blocked" : "ready"}">${agent.enabled === false ? "停用" : "启用"}</span>
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(agent.role || agent.id)} · ${escapeHtml((agent.tools || []).length)} 个工具</div>
              <div class="workspace-template-item-desc">${escapeHtml(agent.description || agent.prompt || "未填写描述")}</div>
            </button>
          `;
        }).join("")
      : '<div class="empty">还没有全局 Agent。</div>';
  }
  if (!editor) return;
  const agent = state.agentDefinitionDraft && Object.keys(state.agentDefinitionDraft).length
    ? normalizeGlobalAgentDefinitionDraft(state.agentDefinitionDraft)
    : null;
  if (!agent) {
    editor.innerHTML = '<div class="empty">选择一个 Agent 后在这里编辑。</div>';
    return;
  }
  editor.innerHTML = `
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(agent.name || agent.id)}</h4>
          <p class="muted">全局角色库。模板节点通过 handler.agent_id 引用这里的定义。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-global-agent" title="保存当前全局 Agent 定义，供模板节点引用">保存 Agent</button>
          <button class="secondary mini danger" type="button" data-action="delete-global-agent" title="删除当前全局 Agent 定义；已创建实例的快照不会被直接删除">删除 Agent</button>
        </div>
      </div>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>基础信息</strong>
          <span class="muted">ID、显示名、角色和 Provider 覆盖。</span>
        </div>
        <div class="workspace-agent-editor-grid">
          <label>
            Agent ID
            <input data-manage-agent-field="id" value="${escapeHtml(agent.id || "")}" placeholder="planner" />
          </label>
          <label>
            显示名
            <input data-manage-agent-field="name" value="${escapeHtml(agent.name || "")}" placeholder="Planner" />
          </label>
          <label>
            角色
            <input data-manage-agent-field="role" value="${escapeHtml(agent.role || "")}" placeholder="planner" />
          </label>
          <label>
            Provider Profile 覆盖
            <select data-manage-agent-field="provider_profile_id">
              <option value="">未覆盖</option>
              ${state.providerProfiles.map((profile) => `<option value="${escapeHtml(profile.id)}" ${profile.id === agent.provider_profile_id ? "selected" : ""}>${escapeHtml(providerProfileLabel(profile))}</option>`).join("")}
            </select>
          </label>
        </div>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>能力边界</strong>
          <span class="muted">说明用途，并明确允许调用哪些工具。</span>
        </div>
        <label>
          描述
          <textarea data-manage-agent-field="description" rows="2" placeholder="这个 Agent 在全局库中的职责">${escapeHtml(agent.description || "")}</textarea>
        </label>
        <label>
          工具 allowlist
          <textarea data-manage-agent-field="tools" rows="2" placeholder="逗号分隔 tool id">${escapeHtml((agent.tools || []).join(", "))}</textarea>
        </label>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>系统提示词</strong>
          <span class="muted">保留完整 Prompt，但控制高度和节奏。</span>
        </div>
        <label>
          Prompt
          <textarea data-manage-agent-field="prompt" rows="7" placeholder="给这个 Agent 的系统提示词">${escapeHtml(agent.prompt || "")}</textarea>
        </label>
        <label class="check">
          <input data-manage-agent-checkbox="enabled" type="checkbox" ${agent.enabled === false ? "" : "checked"} />
          启用这个 Agent
        </label>
      </section>
    </div>
    <div class="workspace-agent-debug-panel">
      <div class="workspace-agent-debug-toolbar">
        <strong>Agent 调试</strong>
        <button class="primary mini" type="button" data-action="run-global-agent-debug" title="用当前模板上下文和输入调试这个全局 Agent，不提交任务队列">${state.manageAgentDebug.busy ? "调试中..." : "运行调试"}</button>
      </div>
      <label>
        模板上下文
        <select id="manageAgentDebugTemplateSelect">
          <option value="">无模板上下文</option>
          ${state.workflowTemplates.map((template) => `<option value="${escapeHtml(template.id)}" ${template.id === (state.manageAgentDebug.templateId || state.selectedWorkflowTemplateId) ? "selected" : ""}>${escapeHtml(template.name || template.id)}</option>`).join("")}
        </select>
      </label>
      <label>
        调试输入
        <textarea id="manageAgentDebugInput" rows="4" placeholder="例如：请判断这个 repo 复现任务下一步应该怎么拆解和使用哪些工具">${escapeHtml(state.manageAgentDebug.input || "")}</textarea>
      </label>
      ${state.manageAgentDebug.error ? `<p class="form-message error">${escapeHtml(state.manageAgentDebug.error)}</p>` : ""}
      ${state.manageAgentDebug.result?.debug
        ? workspaceAgentDebugResultMarkup(state.manageAgentDebug.result.debug)
        : '<div class="empty">输入一段任务描述后，调试结果会显示在这里。</div>'}
      ${state.manageAgentDebug.result?.execution ? `
        <div class="workspace-detail-block">
          <div class="subsection-head"><strong>执行结果</strong><span class="muted">${escapeHtml(state.manageAgentDebug.result.execution.success ? "success" : "failed")}</span></div>
          <pre class="workspace-detail-pre">${escapeHtml(JSON.stringify(state.manageAgentDebug.result.execution, null, 2))}</pre>
        </div>
      ` : ""}
    </div>
  `;
}

function renderManageToolModule() {
  const list = $("manageToolList");
  const editor = $("manageToolEditor");
  if (!selectedGlobalTool() && state.toolDefinitions.length) {
    state.selectedGlobalToolId = state.toolDefinitions[0].id;
    saveStoredValue(STORAGE_KEYS.selectedGlobalTool, state.selectedGlobalToolId);
  }
  if (!state.toolDefinitionDraft.id && selectedGlobalTool()) {
    state.toolDefinitionDraft = normalizeGlobalToolDefinitionDraft(selectedGlobalTool());
  }
  if (list) {
    list.innerHTML = state.toolDefinitions.length
      ? state.toolDefinitions.map((tool) => {
          const active = tool.id === state.selectedGlobalToolId ? " active" : "";
          return `
            <button class="workspace-template-item${active}" type="button" data-action="select-global-tool" data-tool-id="${escapeHtml(tool.id)}" title="选择这个全局工具定义，编辑工具类别和能力边界">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(tool.label || tool.id)}</strong>
                <span class="state ${tool.enabled === false ? "blocked" : "ready"}">${tool.enabled === false ? "停用" : "启用"}</span>
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(workspaceToolCategoryLabel(tool.category || "general"))} · ${escapeHtml(tool.capability || "read")}</div>
              <div class="workspace-template-item-desc">${escapeHtml(tool.description || "未填写描述")}</div>
            </button>
          `;
        }).join("")
      : '<div class="empty">还没有全局工具。</div>';
  }
  if (!editor) return;
  const tool = state.toolDefinitionDraft && Object.keys(state.toolDefinitionDraft).length
    ? normalizeGlobalToolDefinitionDraft(state.toolDefinitionDraft)
    : null;
  if (!tool) {
    editor.innerHTML = '<div class="empty">选择一个工具后在这里编辑。</div>';
    return;
  }
  editor.innerHTML = `
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(tool.label || tool.id)}</h4>
          <p class="muted">工具边界是全局注册表，Agent 只通过 allowlist 引用。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-global-tool" title="保存当前全局工具定义，供 Agent allowlist 引用">保存工具</button>
          <button class="secondary mini danger" type="button" data-action="delete-global-tool" title="删除当前全局工具定义；已创建实例的工具快照不会被直接删除">删除工具</button>
        </div>
      </div>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>基础信息</strong>
          <span class="muted">ID、显示名、类别和能力边界。</span>
        </div>
        <div class="workspace-tool-editor-grid">
          <label>
            Tool ID
            <input data-manage-tool-field="id" value="${escapeHtml(tool.id || "")}" placeholder="repo.inspect" />
          </label>
          <label>
            显示名
            <input data-manage-tool-field="label" value="${escapeHtml(tool.label || "")}" placeholder="Repo Inspect" />
          </label>
          <label>
            类别
            <input data-manage-tool-field="category" value="${escapeHtml(tool.category || "general")}" placeholder="repo / workflow / env" />
          </label>
          <label>
            能力
            <input data-manage-tool-field="capability" value="${escapeHtml(tool.capability || "read")}" placeholder="read / write / execute" />
          </label>
        </div>
      </section>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>说明与约束</strong>
          <span class="muted">写清楚它擅长什么，以及不该跨过的边界。</span>
        </div>
        <label>
          描述
          <textarea data-manage-tool-field="description" rows="2" placeholder="这个工具擅长做什么">${escapeHtml(tool.description || "")}</textarea>
        </label>
        <label>
          备注
          <textarea data-manage-tool-field="notes" rows="2" placeholder="边界、审批点或使用说明">${escapeHtml(tool.notes || "")}</textarea>
        </label>
        <label class="check">
          <input data-manage-tool-checkbox="enabled" type="checkbox" ${tool.enabled === false ? "" : "checked"} />
          启用这个工具
        </label>
      </section>
    </div>
  `;
}

function renderManageAiModule() {
  const list = $("manageProviderProfileList");
  const editor = $("manageAiEditor");
  if (list) {
    list.innerHTML = state.providerProfiles.length
      ? state.providerProfiles.map((profile) => {
          const active = profile.id === state.selectedProviderProfileId ? " active" : "";
          return `
            <button class="workspace-template-item${active}" type="button" data-action="select-provider-profile" data-profile-id="${escapeHtml(profile.id)}" title="选择这个 Provider Profile，编辑模型接入和默认路由">
              <div class="workspace-template-item-head">
                <strong>${escapeHtml(profile.label || profile.id)}</strong>
                <span class="server-badge subtle">${escapeHtml(profile.vendor || "custom")}</span>
              </div>
              <div class="workspace-template-item-meta">${escapeHtml(profile.model || "未填 model")}</div>
              <div class="workspace-template-item-desc">${escapeHtml(profile.base_url || "默认 base URL")}</div>
            </button>
          `;
        }).join("")
      : '<div class="empty">还没有 Provider Profile。</div>';
  }
  if (!editor) return;
  const profile = selectedProviderProfile();
  const draft = normalizeWorkflowTemplateDraft(state.workflowTemplateDraft || selectedWorkflowTemplate() || defaultWorkflowTemplateDraft("repo"));
  editor.innerHTML = `
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>${escapeHtml(profile?.label || "Provider Profile")}</h4>
          <p class="muted">这里管理全局模型接入信息，以及当前模板的默认路由。</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-provider-profile" title="保存当前 Provider Profile 接入配置">保存 Profile</button>
          ${profile ? '<button class="secondary mini danger" type="button" data-action="delete-provider-profile-manage" title="删除当前 Provider Profile，并清理相关路由引用">删除 Profile</button>' : ""}
        </div>
      </div>
      ${profile ? `
        <section class="workspace-manage-group">
          <div class="workspace-manage-group-head">
            <strong>接入信息</strong>
            <span class="muted">控制厂商、模型与自定义 Base URL。</span>
          </div>
          <div class="workspace-provider-editor-grid">
            <label>
              显示名
              <input data-manage-provider-field="label" value="${escapeHtml(profile.label || "")}" />
            </label>
            <label>
              厂商
              <input data-manage-provider-field="vendor" value="${escapeHtml(profile.vendor || "openai")}" />
            </label>
            <label>
              Base URL
              <input data-manage-provider-field="base_url" value="${escapeHtml(profile.base_url || "")}" />
            </label>
            <label>
              Model
              <input data-manage-provider-field="model" value="${escapeHtml(profile.model || "")}" />
            </label>
          </div>
          <label>
            API Key
            <input data-manage-provider-field="api_key" value="${escapeHtml(profile.api_key || "")}" placeholder="sk-..." />
          </label>
        </section>
      ` : '<div class="empty">先新增一个 Provider Profile。</div>'}
    </div>
    <div class="workspace-node-editor-card workspace-manage-editor-stack">
      <div class="workspace-node-editor-head">
        <div>
          <h4>当前模板默认路由</h4>
          <p class="muted">正在编辑：${escapeHtml(draft.name || "未命名模板")}</p>
        </div>
        <div class="workspace-node-editor-actions">
          <button class="secondary mini" type="button" data-action="save-template-routing" title="把当前 Provider、路由模式和聊天 Agent 保存到模板默认配置">保存模板 AI 路由</button>
        </div>
      </div>
      <section class="workspace-manage-group">
        <div class="workspace-manage-group-head">
          <strong>模板默认路由</strong>
          <span class="muted">这里决定实例默认用哪个 Profile、路由模式和聊天 Agent。</span>
        </div>
        <div class="workspace-provider-editor-grid">
          <label>
            默认 Profile
            <select id="manageAiTemplateProfileSelect">
              <option value="">未选择</option>
              ${state.providerProfiles.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === draft.model?.provider_profile_id ? "selected" : ""}>${escapeHtml(providerProfileLabel(item))}</option>`).join("")}
            </select>
          </label>
          <label>
            路由模式
            <select id="manageAiTemplateRoutingSelect">
              <option value="workspace_default" ${draft.model?.routing_mode === "workspace_default" ? "selected" : ""}>workspace_default</option>
              <option value="agent_override" ${draft.model?.routing_mode === "agent_override" ? "selected" : ""}>agent_override</option>
            </select>
          </label>
          <label>
            默认聊天 Agent
            <select id="manageAiTemplateChatAgentSelect">
              <option value="">未选择</option>
              ${state.agentDefinitions.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === draft.model?.chat_agent_id ? "selected" : ""}>${escapeHtml(item.name || item.id)}</option>`).join("")}
            </select>
          </label>
        </div>
      </section>
    </div>
  `;
}

function renderWorkspaceWorkbench() {
  renderWorkspaceModeSwitch();
  renderWorkspaceUseMode();
  renderManageTemplateModule();
  renderManageAgentModule();
  renderManageToolModule();
  renderManageAiModule();
  renderWorkspaceManageOverview();
}

async function deleteWorkspace(workspaceId) {
  if (!workspaceId) return;
  const workspace = state.workspaces.find((item) => item.id === workspaceId);
  if (!workspace) return;
  const name = workspace.name || workspaceId;
  if (!confirm(`确定要删除任务实例 "${name}" 吗？此操作不可撤销。`)) return;

  try {
    await fetchJson(`/api/workspaces/${workspaceId}`, { method: "DELETE" });
    state.workspaces = state.workspaces.filter((item) => item.id !== workspaceId);
    if (state.selectedWorkspaceId === workspaceId) {
      state.selectedWorkspaceId = state.workspaces[0]?.id || "";
      saveStoredValue(STORAGE_KEYS.selectedWorkspace, state.selectedWorkspaceId);
      if (state.selectedWorkspaceId) {
        selectWorkspace(state.selectedWorkspaceId, { persist: false });
      } else {
        resetWorkspaceForm();
      }
    }
    renderWorkspaces();
    renderWorkspaceWorkbench();
    setWorkspaceMessage(`实例 "${name}" 已删除`);
  } catch (err) {
    console.error("Failed to delete workspace:", err);
    setWorkspaceMessage("删除实例失败: " + err.message, true);
  }
}

async function createWorkspaceTask(mode = "create") {
  const actionMode = mode === true ? "run" : mode === false ? "create" : String(mode || "create");
  const busyAction = actionMode === "run"
    ? "create-workspace-run"
    : actionMode === "discover"
      ? "create-workspace-discover"
      : "create-workspace";
  const templateId = String($("workspaceTemplateSelect")?.value || state.selectedWorkflowTemplateId || "").trim();
  const inputs = workspaceUseInputsPayload();
  const hasInput = Boolean(inputs.goal_text || inputs.repo_urls.length || inputs.paper_urls.length || inputs.references.length || inputs.context_blocks.length);
  if (!templateId) {
    setWorkspaceUseMessage("先选择一个工作流模板。", true);
    return;
  }
  if (!hasInput) {
    setWorkspaceUseMessage("先写点任务目标、repo、论文或上下文。", true);
    return;
  }
  const busyText = actionMode === "run"
    ? "正在创建实例并自动推进..."
    : actionMode === "discover"
      ? "正在创建实例并提交自动发现..."
      : "正在创建实例...";
  if (!beginWorkspaceAutomationAction(busyAction, { useMessage: true })) return;
  setWorkspaceUseMessage(busyText);
  try {
    const created = await fetchJson("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        inputs,
      }),
    });
    const workspace = created.workspace;
    if (workspace) {
      upsertWorkspaceInState(workspace);
      state.selectedWorkspaceId = workspace.id;
      saveStoredValue(STORAGE_KEYS.selectedWorkspace, workspace.id);
      hydrateWorkspaceUseInputsFromWorkspace(workspace);
      selectWorkspace(workspace.id, { persist: false });
    }
    if (actionMode === "discover" && workspace?.id) {
      const result = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/discovery/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apply_defaults: true, include_source: true }),
      });
      if (result.workspace) {
        upsertWorkspaceInState(result.workspace);
        selectWorkspace(result.workspace.id, { persist: false });
      }
      const createdJobs = Array.isArray(result.jobs) ? result.jobs.length : 0;
      const applied = Array.isArray(result.applied) ? result.applied.length : 0;
      const skipped = Array.isArray(result.skipped) ? result.skipped.length : 0;
      setWorkspaceUseMessage(`实例已创建并提交源码/发现链：${createdJobs} 个节点 · 应用 ${applied} 项建议${skipped ? ` · 跳过 ${skipped} 项` : ""}。`);
      await loadStatus(true, { renderWorkspace: true });
      if (result.jobs?.[0]?.id) await showLog(result.jobs[0].id);
      return;
    }
    if (actionMode === "run" && workspace?.id) {
      const result = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/advance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_run: false }),
      });
      if (result.workspace) {
        upsertWorkspaceInState(result.workspace);
        selectWorkspace(result.workspace.id, { persist: false });
      }
      setWorkspaceUseMessage(`实例已创建。${workspaceAdvanceMessage(result)}`);
      await loadStatus(true, { renderWorkspace: true });
      if (result.jobs?.[0]?.id) await showLog(result.jobs[0].id);
      return;
    }
    setWorkspaceUseMessage("实例已创建。");
    await loadStatus(true, { renderWorkspace: true });
  } catch (error) {
    if (error?.payload?.workspace) {
      upsertWorkspaceInState(error.payload.workspace);
      selectWorkspace(error.payload.workspace.id, { persist: false });
    }
    setWorkspaceUseMessage(`实例创建/推进未完成：${workspaceWorkflowErrorMessage(error)}`, true);
  } finally {
    endWorkspaceAutomationAction(busyAction);
  }
}

async function submitWorkspaceUseChat() {
  const workspace = selectedWorkspace();
  const input = $("workspaceUseChatInput");
  if (!workspace?.id) {
    setWorkspaceUseMessage("先选择一个实例再发消息。", true);
    return;
  }
  const text = String(input?.value || "").trim();
  if (!text) return;
  try {
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        agent_id: $("workspaceUseChatAgentSelect")?.value || workspace.model?.chat_agent_id || "",
      }),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: false,
        selectedExecutionNodeId: state.selectedWorkspaceExecutionNodeId,
      });
    }
    if (input) input.value = "";
  } catch (error) {
    setWorkspaceUseMessage(error.message, true);
  }
}

function newWorkflowTemplateDraft(sourceType = "repo") {
  state.selectedWorkflowTemplateId = "";
  saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, "");
  state.workflowTemplateDraft = normalizeWorkflowTemplateDraft(defaultWorkflowTemplateDraft(sourceType));
  state.selectedTemplateNodeId = state.workflowTemplateDraft.nodes[0]?.id || "";
  state.ui.workflowTemplateDirty = true;
  renderWorkspaceWorkbench();
}

async function saveWorkflowTemplate() {
  const payload = workflowTemplatePayloadForSave();
  setWorkspaceManageMessage(state.selectedWorkflowTemplateId ? "正在保存模板..." : "正在创建模板...");
  try {
    const response = await fetchJson(
      state.selectedWorkflowTemplateId
        ? `/api/workflow-templates/${encodeURIComponent(state.selectedWorkflowTemplateId)}`
        : "/api/workflow-templates",
      {
        method: state.selectedWorkflowTemplateId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const saved = response.workflow_template;
    await loadStatus(true, { renderWorkspace: true });
    if (saved?.id) selectWorkflowTemplate(saved.id);
    setWorkspaceManageMessage("模板已保存。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function deleteSelectedWorkflowTemplate() {
  if (!state.selectedWorkflowTemplateId) {
    newWorkflowTemplateDraft("repo");
    return;
  }
  const template = selectedWorkflowTemplate();
  if (template && !confirm(`确定删除模板 "${template.name || template.id}" 吗？`)) return;
  try {
    await fetchJson(`/api/workflow-templates/${encodeURIComponent(state.selectedWorkflowTemplateId)}`, {
      method: "DELETE",
    });
    await loadStatus(true, { renderWorkspace: true });
    if (state.workflowTemplates[0]) selectWorkflowTemplate(state.workflowTemplates[0].id);
    else newWorkflowTemplateDraft("repo");
    setWorkspaceManageMessage("模板已删除。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

function updateAgentDefinitionDraft(patch) {
  const current = state.agentDefinitionDraft && Object.keys(state.agentDefinitionDraft).length
    ? state.agentDefinitionDraft
    : normalizeGlobalAgentDefinitionDraft(selectedGlobalAgent() || {}, 0);
  state.agentDefinitionDraft = normalizeGlobalAgentDefinitionDraft({ ...current, ...patch }, 0);
  state.ui.agentDefinitionDirty = true;
  renderWorkspaceWorkbench();
}

function newGlobalAgentDraft() {
  state.selectedGlobalAgentId = "";
  saveStoredValue(STORAGE_KEYS.selectedGlobalAgent, "");
  state.agentDefinitionDraft = normalizeGlobalAgentDefinitionDraft({
    id: "",
    name: "New Agent",
    role: "new_agent",
    description: "",
    prompt: "",
    tools: [],
    provider_profile_id: "",
    enabled: true,
  });
  state.manageAgentDebug = {
    agentId: "",
    templateId: state.selectedWorkflowTemplateId || "",
    input: "",
    result: null,
    busy: false,
    error: "",
  };
  state.ui.agentDefinitionDirty = true;
  renderWorkspaceWorkbench();
}

async function saveGlobalAgentDefinition() {
  const agent = normalizeGlobalAgentDefinitionDraft(state.agentDefinitionDraft || {}, 0);
  const payload = {
    id: agent.id || undefined,
    name: agent.name,
    role: agent.role,
    description: agent.description,
    prompt: agent.prompt,
    tools: parseTagList(agent.tools || []),
    provider_profile_id: agent.provider_profile_id || "",
    enabled: agent.enabled !== false,
  };
  try {
    const response = await fetchJson(
      state.selectedGlobalAgentId
        ? `/api/agent-definitions/${encodeURIComponent(state.selectedGlobalAgentId)}`
        : "/api/agent-definitions",
      {
        method: state.selectedGlobalAgentId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    await loadStatus(true, { renderWorkspace: true });
    const saved = response.agent_definition;
    if (saved?.id) selectGlobalAgent(saved.id);
    setWorkspaceManageMessage("Agent 已保存。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function deleteGlobalAgentDefinition() {
  if (!state.selectedGlobalAgentId) {
    newGlobalAgentDraft();
    return;
  }
  const agent = selectedGlobalAgent();
  if (agent && !confirm(`确定删除 Agent "${agent.name || agent.id}" 吗？`)) return;
  try {
    await fetchJson(`/api/agent-definitions/${encodeURIComponent(state.selectedGlobalAgentId)}`, { method: "DELETE" });
    await loadStatus(true, { renderWorkspace: true });
    if (state.agentDefinitions[0]) selectGlobalAgent(state.agentDefinitions[0].id);
    else newGlobalAgentDraft();
    setWorkspaceManageMessage("Agent 已删除。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function runGlobalAgentDebug() {
  const agentId = state.selectedGlobalAgentId || state.agentDefinitionDraft.id || "";
  if (!agentId) {
    setWorkspaceManageMessage("先保存或选择一个 Agent。", true);
    return;
  }
  state.manageAgentDebug.busy = true;
  state.manageAgentDebug.error = "";
  state.manageAgentDebug.result = null;
  renderWorkspaceWorkbench();
  try {
    const payload = await fetchJson(`/api/agent-definitions/${encodeURIComponent(agentId)}/debug`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: state.manageAgentDebug.templateId || "",
        input: state.manageAgentDebug.input || "",
        node_kind: selectedWorkflowTemplateNode()?.kind || "",
      }),
    });
    state.manageAgentDebug.result = payload;
  } catch (error) {
    state.manageAgentDebug.error = error.message;
  } finally {
    state.manageAgentDebug.busy = false;
    renderWorkspaceWorkbench();
  }
}

function updateToolDefinitionDraft(patch) {
  const current = state.toolDefinitionDraft && Object.keys(state.toolDefinitionDraft).length
    ? state.toolDefinitionDraft
    : normalizeGlobalToolDefinitionDraft(selectedGlobalTool() || {}, 0);
  state.toolDefinitionDraft = normalizeGlobalToolDefinitionDraft({ ...current, ...patch }, 0);
  state.ui.toolDefinitionDirty = true;
  renderWorkspaceWorkbench();
}

function newGlobalToolDraft() {
  state.selectedGlobalToolId = "";
  saveStoredValue(STORAGE_KEYS.selectedGlobalTool, "");
  state.toolDefinitionDraft = normalizeGlobalToolDefinitionDraft({
    id: "",
    label: "New Tool",
    category: "custom",
    capability: "read",
    description: "",
    enabled: true,
    notes: "",
  });
  state.ui.toolDefinitionDirty = true;
  renderWorkspaceWorkbench();
}

async function saveGlobalToolDefinition() {
  const tool = normalizeGlobalToolDefinitionDraft(state.toolDefinitionDraft || {}, 0);
  const payload = {
    id: tool.id || undefined,
    label: tool.label,
    category: tool.category,
    capability: tool.capability,
    description: tool.description,
    enabled: tool.enabled !== false,
    notes: tool.notes || "",
  };
  try {
    const response = await fetchJson(
      state.selectedGlobalToolId
        ? `/api/tool-definitions/${encodeURIComponent(state.selectedGlobalToolId)}`
        : "/api/tool-definitions",
      {
        method: state.selectedGlobalToolId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    await loadStatus(true, { renderWorkspace: true });
    const saved = response.tool_definition;
    if (saved?.id) selectGlobalTool(saved.id);
    setWorkspaceManageMessage("工具已保存。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function deleteGlobalToolDefinition() {
  if (!state.selectedGlobalToolId) {
    newGlobalToolDraft();
    return;
  }
  const tool = selectedGlobalTool();
  if (tool && !confirm(`确定删除工具 "${tool.label || tool.id}" 吗？`)) return;
  try {
    await fetchJson(`/api/tool-definitions/${encodeURIComponent(state.selectedGlobalToolId)}`, { method: "DELETE" });
    await loadStatus(true, { renderWorkspace: true });
    if (state.toolDefinitions[0]) selectGlobalTool(state.toolDefinitions[0].id);
    else newGlobalToolDraft();
    setWorkspaceManageMessage("工具已删除。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function saveManageProviderProfile() {
  const profile = selectedProviderProfile();
  if (!profile) {
    setWorkspaceManageMessage("先新增或选择一个 Provider Profile。", true);
    return;
  }
  try {
    await saveProviderProfile(profile, { forceCreate: Boolean(profile.is_new) });
    setWorkspaceManageMessage("Provider Profile 已保存。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

async function deleteManageProviderProfile() {
  const profile = selectedProviderProfile();
  if (!profile) return;
  if (!confirm(`确定删除 Profile "${profile.label || profile.id}" 吗？`)) return;
  try {
    await deleteProviderProfile(profile.id);
    setWorkspaceManageMessage("Provider Profile 已删除。");
  } catch (error) {
    setWorkspaceManageMessage(error.message, true);
  }
}

function addManageProviderProfile() {
  const profile = normalizeProviderProfile({
    id: makeClientId("provider"),
    label: `Profile ${state.providerProfiles.length + 1}`,
    vendor: "openai",
    base_url: "",
    model: "",
    api_key: "",
    is_new: true,
  }, state.providerProfiles.length);
  profile.is_new = true;
  state.providerProfiles.unshift(profile);
  state.selectedProviderProfileId = profile.id;
  saveStoredValue(STORAGE_KEYS.selectedProviderProfile, profile.id);
  renderWorkspaceWorkbench();
}

function upsertWorkspaceInState(workspace) {
  const index = state.workspaces.findIndex((item) => item.id === workspace.id);
  if (index >= 0) state.workspaces.splice(index, 1, workspace);
  else state.workspaces.unshift(workspace);
}

function resetWorkspaceAgentDebug(agent = selectedWorkspaceAgent(), options = {}) {
  const workspaceId = String(selectedWorkspace()?.id || "draft").trim();
  const agentId = String(agent?.id || "").trim();
  state.workspaceAgentDebug = {
    workspaceId,
    agentId,
    input: options.keepInput ? state.workspaceAgentDebug.input : defaultWorkspaceAgentDebugInput(agent),
    result: options.keepResult ? state.workspaceAgentDebug.result : null,
    busy: false,
    error: "",
  };
}

function selectWorkspaceAgent(agentId) {
  if (!workspaceAgentById(agentId, state.workspaceAgentsDraft)) return;
  const changed = state.selectedWorkspaceAgentId !== agentId;
  state.selectedWorkspaceAgentId = agentId;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceAgent, agentId);
  renderWorkspacePanels();
}

function updateSelectedWorkspaceAgent(updater) {
  const index = state.workspaceAgentsDraft.findIndex((item) => item.id === state.selectedWorkspaceAgentId);
  if (index < 0) return;
  const current = state.workspaceAgentsDraft[index];
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  next.tools = Array.isArray(next.tools) ? next.tools : parseTagList(next.tools || "");
  const normalized = normalizeWorkspaceAgentDraft(next, index);
  state.workspaceAgentsDraft.splice(index, 1, normalized);
  state.workspaceNodesDraft = state.workspaceNodesDraft.map((node) => (
    node.handler?.agent_id === normalized.id
      ? { ...node, handler: { ...(node.handler || {}), name: normalized.name } }
      : node
  ));
  persistWorkspaceNodesDraft();
  if (state.workspaceAgentDebug.agentId === normalized.id) {
    state.workspaceAgentDebug.result = null;
    state.workspaceAgentDebug.error = "";
  }
  renderWorkspacePanels();
}

function addWorkspaceAgent() {
  const agent = normalizeWorkspaceAgentDraft({
    id: makeClientId("agent"),
    name: `Agent ${state.workspaceAgentsDraft.length + 1}`,
    role: `agent_${state.workspaceAgentsDraft.length + 1}`,
    prompt: "",
    tools: [],
    provider_profile_id: "",
    enabled: true,
  }, state.workspaceAgentsDraft.length);
  state.workspaceAgentsDraft.push(agent);
  state.selectedWorkspaceAgentId = agent.id;
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceAgent, agent.id);
  if (!state.workspaceModelDraft.chat_agent_id) state.workspaceModelDraft.chat_agent_id = agent.id;
  renderWorkspacePanels();
}

function removeWorkspaceAgent(agentId) {
  if (state.workspaceAgentsDraft.length <= 1) {
    setWorkspaceMessage("至少保留一个 agent。", true);
    return;
  }
  state.workspaceAgentsDraft = state.workspaceAgentsDraft.filter((item) => item.id !== agentId);
  state.workspaceNodesDraft = state.workspaceNodesDraft.map((node) => {
    if (node.handler?.agent_id !== agentId) return node;
    return {
      ...node,
      handler: { ...(node.handler || {}), agent_id: "", name: "" },
    };
  });
  if (state.workspaceModelDraft.chat_agent_id === agentId) {
    state.workspaceModelDraft.chat_agent_id = state.workspaceAgentsDraft[0]?.id || "";
  }
  state.selectedWorkspaceAgentId = state.workspaceAgentsDraft[0]?.id || "";
  saveStoredValue(STORAGE_KEYS.selectedWorkspaceAgent, state.selectedWorkspaceAgentId);
  persistWorkspaceNodesDraft();
  renderWorkspacePanels();
}

function prefillWorkspaceAgentDebug() {
  const agent = selectedWorkspaceAgent();
  if (!agent) return;
  state.workspaceAgentDebug.input = defaultWorkspaceAgentDebugInput(agent);
  state.workspaceAgentDebug.error = "";
  state.workspaceAgentDebug.result = null;
  renderWorkspacePanels();
}

async function debugWorkspaceAgent(agentId = state.selectedWorkspaceAgentId) {
  const workspace = selectedWorkspace();
  const agent = workspaceAgentById(agentId, state.workspaceAgentsDraft);
  if (!workspace?.id) {
    setWorkspaceMessage("先保存项目，再调试 Agent。", true);
    switchWorkspaceTab("project");
    return;
  }
  if (!agent) return;
  ensureWorkspaceAgentDebugState(agent);
  state.workspaceAgentDebug.busy = true;
  state.workspaceAgentDebug.error = "";
  state.workspaceAgentDebug.result = null;
  renderWorkspacePanels();
  try {
    const payload = await fetchJson(
      `/api/workspaces/${encodeURIComponent(workspace.id)}/agents/${encodeURIComponent(agent.id)}/debug`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: state.workspaceAgentDebug.input || "",
          node_kind: selectedWorkspaceNode()?.kind || "",
        }),
      },
    );
    state.workspaceAgentDebug.result = payload.debug || null;
  } catch (error) {
    state.workspaceAgentDebug.error = error.message;
  } finally {
    state.workspaceAgentDebug.busy = false;
    renderWorkspacePanels();
  }
}

function updateWorkspaceModelDraft(patch = {}) {
  state.workspaceModelDraft = normalizeWorkspaceModelDraft({ ...state.workspaceModelDraft, ...patch });
  if (!workspaceAgentById(state.workspaceModelDraft.chat_agent_id, state.workspaceAgentsDraft)) {
    state.workspaceModelDraft.chat_agent_id = state.workspaceAgentsDraft[0]?.id || "";
  }
  renderWorkspacePanels();
}

function selectProviderProfile(profileId) {
  if (!providerProfileById(profileId, state.providerProfiles)) return;
  const changed = state.selectedProviderProfileId !== profileId;
  state.selectedProviderProfileId = profileId;
  if (changed) markWorkspaceUiInteraction();
  saveStoredValue(STORAGE_KEYS.selectedProviderProfile, profileId);
  renderWorkspaceModel();
  renderWorkspaceWorkbench();
}

function updateSelectedProviderProfile(updater) {
  const index = state.providerProfiles.findIndex((item) => item.id === state.selectedProviderProfileId);
  if (index < 0) return;
  const current = state.providerProfiles[index];
  const next = typeof updater === "function" ? updater(deepClone(current, current)) : { ...current, ...updater };
  state.providerProfiles.splice(index, 1, normalizeProviderProfile(next, index));
  renderWorkspaceModel();
  renderWorkspaceWorkbench();
  // Debounce save to API
  clearTimeout(state._providerProfileSaveTimeout);
  state._providerProfileSaveTimeout = setTimeout(() => {
    saveProviderProfile(next).catch((err) => {
      console.error("Failed to save provider profile:", err);
    });
  }, 500);
}

function addProviderProfile() {
  const profile = normalizeProviderProfile({
    id: makeClientId("provider"),
    label: `Profile ${state.providerProfiles.length + 1}`,
    vendor: "openai",
    base_url: "",
    model: "",
    api_key: "",
    is_new: true,
  }, state.providerProfiles.length);
  state.providerProfiles.push(profile);
  state.selectedProviderProfileId = profile.id;
  saveStoredValue(STORAGE_KEYS.selectedProviderProfile, profile.id);
  // Create in backend
  saveProviderProfile(profile, { forceCreate: true }).catch((err) => {
    console.error("Failed to save provider profile:", err);
    setWorkspaceMessage("保存 Provider Profile 失败: " + err.message, true);
  });
  renderWorkspaceModel();
}

async function removeProviderProfile(profileId) {
  try {
    await deleteProviderProfile(profileId);
    if (state.workspaceModelDraft.provider_profile_id === profileId) {
      state.workspaceModelDraft.provider_profile_id = "";
    }
    state.workspaceAgentsDraft = state.workspaceAgentsDraft.map((agent) => (
      agent.provider_profile_id === profileId ? { ...agent, provider_profile_id: "" } : agent
    ));
    state.selectedProviderProfileId = state.providerProfiles[0]?.id || "";
    saveStoredValue(STORAGE_KEYS.selectedProviderProfile, state.selectedProviderProfileId);
    renderWorkspacePanels();
  } catch (err) {
    console.error("Failed to delete provider profile:", err);
    setWorkspaceMessage("删除 Provider Profile 失败: " + err.message, true);
  }
}

function setWorkspaceMessage(text, isError = false) {
  const message = $("workspaceMessage");
  if (!message) return;
  message.textContent = text || "";
  message.classList.toggle("error", Boolean(isError));
}

const WORKSPACE_AUTOMATION_ACTION_LABELS = {
  "create-workspace": "创建任务",
  "create-workspace-discover": "创建并自动发现",
  "create-workspace-run": "创建并自动推进",
  "run-workspace-node": "运行节点",
  "run-selected-node": "运行当前节点",
  "run-selected-workspace": "运行工作流",
  "advance-workspace-automation": "自动推进",
  "run-workspace-discovery": "自动发现",
  "apply-workspace-automation": "回填证据",
  "refresh-workspace-resources": "刷新资源",
  "refresh-workspace-resource-server": "刷新推荐服务器",
  "refresh-workspace-resource-selected-server": "刷新单机",
};

const WORKSPACE_NON_BLOCKING_ACTIONS = new Set([
  "refresh-workspace-resources",
  "refresh-workspace-resource-server",
  "refresh-workspace-resource-selected-server",
]);

function workspaceAutomationActionLabel(action) {
  return WORKSPACE_AUTOMATION_ACTION_LABELS[action] || "工作台操作";
}

const WORKSPACE_AUTOMATION_ACTION_HELP = {
  "create-workspace": "只创建任务实例快照，不提交自动发现或运行队列。",
  "create-workspace-discover": "创建实例后只提交安全发现链，先收集源码、路径、数据、环境、GPU 和产物证据。",
  "create-workspace-run": "创建实例后交给自动推进；首次通常先跑安全发现，门禁通过后再完整运行。",
  "run-workspace-node": "只提交当前节点，用于单点调试；不会运行整条链。",
  "run-selected-node": "只提交当前节点，用于单点调试；不会运行整条链。",
  "run-selected-workspace": "门禁通过后提交完整工作流；门禁失败时不会创建半截队列。",
  "advance-workspace-automation": "根据当前门禁自动决定发现、观察、复查失败、回填或完整运行。",
  "run-workspace-discovery": "只运行安全发现链，收集源码、路径、数据、环境、GPU 和产物证据。",
  "apply-workspace-automation": "把建议和发现证据回填到节点配置，后续运行会使用这些路径、环境和资源线索。",
  "refresh-workspace-resources": "刷新全部服务器、GPU、任务和工作台资源快照；异步返回后保留当前工作台选项卡和草稿。",
  "refresh-workspace-resource-server": "只刷新指定服务器的 GPU、显存、进程和连接状态；不会重置工作台。",
  "refresh-workspace-resource-selected-server": "只刷新下拉选择的单台服务器 GPU、显存、进程和连接状态；不会重置工作台。",
};

function workspaceAutomationActionHelp(action, fallback = "") {
  return WORKSPACE_AUTOMATION_ACTION_HELP[action] || fallback || workspaceAutomationActionLabel(action);
}

function updateWorkspaceAutomationBusyControls() {
  const busyAction = String(state.ui.workspaceAutomationBusyAction || "");
  const busy = Boolean(busyAction);
  document.querySelectorAll("[data-action]").forEach((button) => {
    const action = button.dataset?.action || "";
    if (!WORKSPACE_AUTOMATION_ACTION_LABELS[action]) return;
    if (WORKSPACE_NON_BLOCKING_ACTIONS.has(action)) return;
    button.disabled = busy;
  });
  [
    ["workspaceCreateTaskBtn", "create-workspace"],
    ["workspaceCreateDiscoverTaskBtn", "create-workspace-discover"],
    ["workspaceCreateRunTaskBtn", "create-workspace-run"],
    ["workspaceRunFlowBtn", "run-selected-workspace"],
  ].forEach(([id, action]) => {
    const button = $(id);
    if (!button) return;
    button.disabled = busy;
    button.dataset.busyAction = busyAction === action ? "1" : "";
  });
}

function beginWorkspaceAutomationAction(action, options = {}) {
  const busyAction = String(state.ui.workspaceAutomationBusyAction || "");
  if (busyAction) {
    const message = `${workspaceAutomationActionLabel(busyAction)}正在处理中，稍等一下再操作。`;
    if (options.useMessage) setWorkspaceUseMessage(message, true);
    else setWorkspaceMessage(message, true);
    return false;
  }
  state.ui.workspaceAutomationBusyAction = String(action || "workspace-action");
  updateWorkspaceAutomationBusyControls();
  renderWorkspaceCockpitOverview();
  renderWorkspaceExecutionDetail();
  return true;
}

function endWorkspaceAutomationAction(action) {
  const current = String(state.ui.workspaceAutomationBusyAction || "");
  if (current && current !== String(action || "")) return;
  state.ui.workspaceAutomationBusyAction = "";
  updateWorkspaceAutomationBusyControls();
  renderWorkspaceCockpitOverview();
  renderWorkspaceExecutionDetail();
}

function workspaceWorkflowErrorMessage(error) {
  const blocked = Array.isArray(error?.payload?.blocked_checks) ? error.payload.blocked_checks : [];
  if (!blocked.length) return error?.message || "工作流提交失败";
  const applied = Array.isArray(error?.payload?.applied) ? error.payload.applied.length : 0;
  const prefix = applied ? `已先回填 ${applied} 项建议/发现，但` : "";
  const labels = blocked
    .map((item) => item.label || item.title || item.node_kind || item.id)
    .filter(Boolean)
    .slice(0, 5)
    .join("、");
  return `${prefix}完整运行前检查未通过：${labels}。先点“自动发现”或补齐阻塞项，再提交完整工作流。`;
}

async function runWorkspaceNode(nodeId) {
  const workspace = selectedWorkspace();
  const node = state.workspaceNodesDraft.find((item) => item.id === nodeId);
  if (!workspace?.id || !node) {
    setWorkspaceMessage("先保存项目，再运行节点。", true);
    return;
  }
  if (!beginWorkspaceAutomationAction("run-selected-node")) return;
  setWorkspaceMessage(`正在提交节点“${node.title || workspaceNodeLabel(node.kind)}”...`);
  try {
    const payload = await fetchJson(
      `/api/workspaces/${encodeURIComponent(workspace.id)}/nodes/${encodeURIComponent(node.id)}/run`,
      { method: "POST" },
    );
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: node.id,
        selectedExecutionNodeId: node.id,
        selectedAgentId: state.selectedWorkspaceAgentId,
      });
    }
    setWorkspaceMessage(`节点“${node.title || workspaceNodeLabel(node.kind)}”已加入执行队列。`);
    if (payload.job?.id) {
      await loadStatus(true, { renderWorkspace: true });
      await showLog(payload.job.id);
    }
  } catch (error) {
    setWorkspaceMessage(workspaceWorkflowErrorMessage(error), true);
  } finally {
    endWorkspaceAutomationAction("run-selected-node");
  }
}

async function runWorkspaceWorkflow() {
  const workspace = selectedWorkspace();
  if (!workspace?.id) {
    setWorkspaceMessage("先保存项目，再运行工作流。", true);
    return;
  }
  const selectedExecutionNodeId = state.selectedWorkspaceExecutionNodeId;
  if (!beginWorkspaceAutomationAction("run-selected-workspace")) return;
  setWorkspaceMessage("正在整理建议/发现并提交整条工作流...");
  try {
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_apply: true, apply_evidence: true }),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    const created = Array.isArray(payload.jobs) ? payload.jobs.length : 0;
    const applied = Array.isArray(payload.applied) ? payload.applied.length : 0;
    setWorkspaceMessage(`已提交工作流，创建 ${created} 个执行节点${applied ? ` · 先回填 ${applied} 项` : ""}。`);
    if (payload.jobs?.[0]?.id) {
      await loadStatus(true, { renderWorkspace: true });
      await showLog(payload.jobs[0].id);
    }
  } catch (error) {
    if (error?.payload?.workspace) {
      upsertWorkspaceInState(error.payload.workspace);
      selectWorkspace(error.payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    setWorkspaceMessage(workspaceWorkflowErrorMessage(error), true);
  } finally {
    endWorkspaceAutomationAction("run-selected-workspace");
  }
}

function workspaceAdvanceMessage(payload) {
  const action = String(payload?.action || "").trim();
  const jobs = Array.isArray(payload?.jobs) ? payload.jobs : [];
  const applied = Array.isArray(payload?.applied) ? payload.applied.length : 0;
  const evidenceApplied = Array.isArray(payload?.evidence_applied) ? payload.evidence_applied.length : 0;
  const decision = payload?.decision && typeof payload.decision === "object" ? payload.decision : null;
  const suffix = decision?.reason
    ? ` 原因：${decision.reason}${decision.next_action ? ` 下一步：${decision.next_action}` : ""}`
    : "";
  if (action === "discover") {
    return `自动推进已提交发现链：${jobs.length} 个节点${applied ? ` · 先应用 ${applied} 项建议` : ""}。${suffix}`;
  }
  if (action === "run") {
    return `自动推进已提交完整工作流：${jobs.length} 个节点${applied ? ` · 先回填 ${applied} 项` : ""}${evidenceApplied ? ` · ${evidenceApplied} 项来自发现证据` : ""}。${suffix}`;
  }
  if (action === "watch") {
    const active = Array.isArray(payload?.active_job_ids) ? payload.active_job_ids.length : 0;
    return `自动推进暂停：已有 ${active} 个任务在队列或运行中，先观察当前执行。${suffix}`;
  }
  if (action === "review_failed") {
    const failed = Array.isArray(payload?.failed_job_ids) ? payload.failed_job_ids.length : 0;
    return `自动推进暂停：存在 ${failed} 个失败或停止任务，先查看输出再继续。${suffix}`;
  }
  if (action === "blocked") {
    const blocked = Array.isArray(payload?.blocked_checks) ? payload.blocked_checks : [];
    const labels = blocked.map((item) => item.label || item.title || item.node_kind || item.id).filter(Boolean).slice(0, 5).join("、");
    return `${payload?.message || "自动推进遇到阻塞"}${labels ? `：${labels}` : ""}${suffix}`;
  }
  return `${payload?.message || "自动推进已完成。"}${suffix}`;
}

async function advanceWorkspaceAutomation() {
  const workspace = selectedWorkspace();
  if (!workspace?.id) {
    setWorkspaceMessage("先创建任务实例，再自动推进。", true);
    return;
  }
  const selectedExecutionNodeId = state.selectedWorkspaceExecutionNodeId;
  if (!beginWorkspaceAutomationAction("advance-workspace-automation")) return;
  setWorkspaceMessage("正在判断下一步并自动推进...");
  try {
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/advance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    setWorkspaceMessage(workspaceAdvanceMessage(payload), payload.action === "blocked" || payload.action === "review_failed");
    const firstJobId = payload.jobs?.[0]?.id || payload.active_job_ids?.[0] || payload.failed_job_ids?.[0] || "";
    await loadStatus(true, { renderWorkspace: true });
    if (firstJobId) await showLog(firstJobId);
  } catch (error) {
    if (error?.payload?.workspace) {
      upsertWorkspaceInState(error.payload.workspace);
      selectWorkspace(error.payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    setWorkspaceMessage(workspaceWorkflowErrorMessage(error), true);
  } finally {
    endWorkspaceAutomationAction("advance-workspace-automation");
  }
}

async function runWorkspaceDiscovery() {
  const workspace = selectedWorkspace();
  if (!workspace?.id) {
    setWorkspaceMessage("先创建任务实例，再运行自动发现。", true);
    return;
  }
  const selectedExecutionNodeId = state.selectedWorkspaceExecutionNodeId;
  if (!beginWorkspaceAutomationAction("run-workspace-discovery")) return;
  setWorkspaceMessage("正在准备源码、应用建议并提交发现链...");
  try {
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/discovery/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apply_defaults: true, include_source: true }),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    const created = Array.isArray(payload.jobs) ? payload.jobs.length : 0;
    const applied = Array.isArray(payload.applied) ? payload.applied.length : 0;
    const skipped = Array.isArray(payload.skipped) ? payload.skipped.length : 0;
    setWorkspaceMessage(`已提交源码/发现链：${created} 个节点 · 应用 ${applied} 项建议${skipped ? ` · 跳过 ${skipped} 项` : ""}。`);
    if (payload.jobs?.[0]?.id) {
      await loadStatus(true, { renderWorkspace: true });
      await showLog(payload.jobs[0].id);
    }
  } catch (error) {
    setWorkspaceMessage(error.message, true);
  } finally {
    endWorkspaceAutomationAction("run-workspace-discovery");
  }
}

async function applyWorkspaceAutomationDefaults() {
  const workspace = selectedWorkspace();
  if (!workspace?.id) {
    setWorkspaceMessage("先创建任务实例，再回填建议和发现结果。", true);
    return;
  }
  const selectedExecutionNodeId = state.selectedWorkspaceExecutionNodeId;
  if (!beginWorkspaceAutomationAction("apply-workspace-automation")) return;
  setWorkspaceMessage("正在回填自动化建议和发现证据...");
  try {
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/automation/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apply_evidence: true }),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
        selectedToolId: state.selectedWorkspaceToolId,
      });
    }
    const applied = Array.isArray(payload.applied) ? payload.applied : [];
    const evidenceApplied = Array.isArray(payload.evidence_applied) ? payload.evidence_applied.length : 0;
    setWorkspaceMessage(applied.length ? `已回填 ${applied.length} 项建议/发现${evidenceApplied ? `，其中 ${evidenceApplied} 项来自发现证据` : ""}。` : "没有新的建议或发现结果需要回填。");
  } catch (error) {
    setWorkspaceMessage(error.message, true);
  } finally {
    endWorkspaceAutomationAction("apply-workspace-automation");
  }
}

function renderJobSourceHint() {
  const hint = $("jobSourceHint");
  if (!hint) return;
  const workspaceId = $("jobWorkspaceIdInput")?.value || "";
  const workspaceName = workspaceById(workspaceId)?.name || "";
  const nodeTitle = $("jobWorkspaceNodeTitleInput")?.value || "";
  if (!workspaceName || !nodeTitle) {
    hint.textContent = "";
    return;
  }
  hint.textContent = `来源：${workspaceName} / ${nodeTitle}`;
}

function bindJobToWorkspaceNode(node) {
  if (!node) return;
  if ($("jobWorkspaceIdInput")) $("jobWorkspaceIdInput").value = state.selectedWorkspaceId || "";
  if ($("jobWorkspaceNodeIdInput")) $("jobWorkspaceNodeIdInput").value = node.id || "";
  if ($("jobWorkspaceNodeTitleInput")) $("jobWorkspaceNodeTitleInput").value = node.title || workspaceNodeLabel(node.kind);
  renderJobSourceHint();
}

function clearJobSourceBinding() {
  if ($("jobWorkspaceIdInput")) $("jobWorkspaceIdInput").value = "";
  if ($("jobWorkspaceNodeIdInput")) $("jobWorkspaceNodeIdInput").value = "";
  if ($("jobWorkspaceNodeTitleInput")) $("jobWorkspaceNodeTitleInput").value = "";
  renderJobSourceHint();
}

async function submitWorkspaceChat() {
  const input = $("workspaceChatInput");
  const workspace = selectedWorkspace();
  if (!workspace?.id) {
    setWorkspaceMessage("先保存项目，再发送项目对话。", true);
    switchWorkspaceTab("project");
    return;
  }
  const text = String(input?.value || "").trim();
  if (!text) return;
  state.workspaceChatBusy = true;
  renderWorkspaceChat();
  try {
    const agentId = $("workspaceChatAgentSelect")?.value || state.workspaceModelDraft.chat_agent_id || "";
    const payload = await fetchJson(`/api/workspaces/${encodeURIComponent(workspace.id)}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, agent_id: agentId }),
    });
    if (payload.workspace) {
      upsertWorkspaceInState(payload.workspace);
      selectWorkspace(payload.workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId: state.selectedWorkspaceExecutionNodeId,
        selectedAgentId: state.selectedWorkspaceAgentId,
      });
    }
    if (input) input.value = "";
  } catch (error) {
    setWorkspaceMessage(error.message, true);
  } finally {
    state.workspaceChatBusy = false;
    renderWorkspaceChat();
  }
}

function renderJobs() {
  const list = $("jobList");
  const items = filteredJobs();
  const queuePositions = waitingQueuePositions();
  $("jobCount").textContent = items.length === state.jobs.length
    ? `最近 ${Math.min(state.jobs.length, 100)} 个任务`
    : `筛选后 ${items.length} / ${Math.min(state.jobs.length, 100)} 个任务`;
  if (!state.jobs.length) {
    list.innerHTML = '<div class="empty">暂无任务。</div>';
    return;
  }
  if (!items.length) {
    list.innerHTML = '<div class="empty">没有匹配的任务。</div>';
    return;
  }
  list.innerHTML = items
    .map((job) => {
      const active = job.id === state.selectedJob ? " active" : "";
      const canStop = isJobActive(job);
      const canDelete = !canStop && ["done", "failed", "stopped"].includes(job.status);
      const canRetry = !canStop;
      const canReorder = isWaitingJob(job);
      const requestedServer = serverById(job.server_id || job.requested_server_id || "");
      const gpu = job.gpu_index === "auto"
        ? "auto"
        : job.gpu_index === "none"
          ? "无 GPU"
          : `GPU ${job.gpu_index}`;
      const durationText = formatDurationMs(jobDurationMs(job));
      const queueText = queuePositions.get(job.id) ? `队列 #${queuePositions.get(job.id)}` : "";
      const statusTextLine = job.kind === "transfer" && state.transfer.logs[job.id]
        ? `${zhStatus(job.status)} · ${state.transfer.logs[job.id].progress ?? 0}% · ${state.transfer.logs[job.id].line}`
        : job.error || job.created_at;
      const meta = job.metadata || {};
      const template = meta.template ? ` · ${escapeHtml(meta.template)}` : "";
      const commandText = escapeHtml(job.command_display || job.command || "");
      const progress = job.kind === "transfer"
        ? `
          <div class="job-progress">
            <div class="bar"><div class="bar-fill${job.status === "running" ? " busy" : ""}" style="width:${state.transfer.logs[job.id]?.progress ?? 0}%"></div></div>
          </div>
        `
        : "";
      return `
        <div class="job-item${active}" onclick="showLog('${escapeHtml(job.id)}')">
          <div>
            <div class="job-title" title="${escapeHtml(job.name)}">${escapeHtml(job.name)}</div>
            <div class="job-line">
              <span class="state ${escapeHtml(job.status)}">${escapeHtml(zhStatus(job.status))}</span>
              <span>${escapeHtml(zhKind(job.kind))}${template}</span>
              <span>${escapeHtml(requestedServer?.name || job.server_id || job.requested_server_id || "-")}</span>
              <span>${escapeHtml(gpu)}</span>
              <span>${escapeHtml(durationText)}</span>
              ${queueText ? `<span>${escapeHtml(queueText)}</span>` : ""}
              <span class="${job.error ? "job-error" : ""}">${escapeHtml(statusTextLine)}</span>
            </div>
            <div class="job-command" title="${commandText}">${commandText}</div>
            ${progress}
          </div>
          <div class="job-actions">
            ${canStop ? `<button class="stop-button" type="button" onclick="stopJob(event, '${escapeHtml(job.id)}')" title="停止这条任务；不会删除任务记录">停止</button>` : ""}
            ${canRetry ? `<button class="secondary mini" type="button" onclick="retryJob(event, '${escapeHtml(job.id)}')" title="复制原任务配置并重新加入队列">重试</button>` : ""}
            ${canDelete ? `<button class="secondary mini" type="button" onclick="deleteJob(event, '${escapeHtml(job.id)}')" title="删除这条已完成或已停止的任务记录">删除</button>` : ""}
            ${canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeHtml(job.id)}', 'top')" title="把这条排队任务移动到队列最前">置顶</button>` : ""}
            ${canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeHtml(job.id)}', 'up')" title="把这条排队任务向前移动一位">上移</button>` : ""}
            ${canReorder ? `<button class="secondary mini" type="button" onclick="reorderQueuedJob(event, '${escapeHtml(job.id)}', 'down')" title="把这条排队任务向后移动一位">下移</button>` : ""}
            <button class="secondary mini" type="button" onclick="loadJobIntoExecution(event, '${escapeHtml(job.id)}')" title="把这条任务的命令、服务器、GPU 和目录填回执行面板">填回执行</button>
            <button class="secondary mini" type="button" onclick="copyJob(event, '${escapeHtml(job.id)}')" title="把这条任务复制成新的待运行任务">复制入队</button>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderTmuxSessions() {
  const list = $("tmuxList");
  $("tmuxCount").textContent = `${state.tmuxSessions.length} 个会话`;
  if (state.tmuxError) {
    list.innerHTML = `<div class="empty error-text">${escapeHtml(state.tmuxError)}</div>`;
    return;
  }
  if (!state.tmuxSessions.length) {
    list.innerHTML = '<div class="empty">所选服务器暂无 tmux 会话。</div>';
    return;
  }
  list.innerHTML = state.tmuxSessions
    .map((session) => {
      const active = session.name === state.selectedTmux ? " active" : "";
      return `
      <div class="tmux-item${active}" onclick="showTmux('${escapeHtml(session.name)}')">
        <span class="tmux-name">${escapeHtml(session.name)}</span>
        <span class="muted">${session.windows} 窗口 · ${session.attached ? "已连接" : "未连接"}</span>
      </div>
    `;
    })
    .join("");
}

function renderHeader(payload) {
  const connected = connectedServers().length;
  const online = onlineServers().length;
  const total = state.servers.length;
  const refreshedAt = payload.refreshed_at ? fmtDate(payload.refreshed_at) : "等待首次刷新";
  $("refreshMeta").textContent = `${payload.status_age_seconds ?? 0} 秒前更新 · ${refreshedAt} · 已配置 ${total} 台`;
  const pill = $("healthPill");
  pill.textContent = online === connected
    ? `${connected}/${total} 在线`
    : `${connected}/${total} 已连接 · ${online} 监控正常`;
  pill.classList.toggle("bad", connected === 0);
  pill.classList.toggle("warn", connected > 0 && online < connected);
}

function render(payload = {}, options = {}) {
  const renderWorkspace = options.workspace !== false;
  renderHeader(payload);
  renderOverview();
  renderServers();
  renderGpuRows();
  renderProcesses();
  if (renderWorkspace) {
    renderWorkspaces();
    renderWorkspacePanels();
    renderWorkspaceWorkbench();
  }
  renderFormOptions();
  renderTaskPlanOptions();
  renderTerminalOptions();
  renderTransferSourceOptions();
  renderTransferTargetOptions();
  renderSelectedSources();
  renderJobFilters();
  renderJobs();
  renderTransferProgress();
  renderTmuxSessions();
  renderOutputTabs();
  renderFilePreview();
  renderJobSourceHint();
  updateSelectedServerRefreshButton();
  updateWorkspaceAutomationBusyControls();
  updateLogSearchControls();
  switchProductTab(state.ui.productTab, { persist: false });
  switchExecTab(state.ui.execTab, { persist: false });
  switchActivityTab(state.ui.activityTab, { persist: false });
}

function updatePollTimer(seconds) {
  const ms = Math.max(2000, Number(seconds || 5) * 1000);
  if (state.ui.pollIntervalMs === ms && state.pollTimer) return;
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.ui.pollIntervalMs = ms;
  state.pollTimer = setInterval(() => loadStatus(false), ms);
}

function restoreStoredUiState() {
  state.selectedServer = loadStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer || "");
  state.selectedWorkspaceId = loadStoredValue(STORAGE_KEYS.selectedWorkspace, state.selectedWorkspaceId || "");
  state.selectedWorkflowTemplateId = loadStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, state.selectedWorkflowTemplateId || "");
  state.selectedGlobalAgentId = loadStoredValue(STORAGE_KEYS.selectedGlobalAgent, state.selectedGlobalAgentId || "");
  state.selectedGlobalToolId = loadStoredValue(STORAGE_KEYS.selectedGlobalTool, state.selectedGlobalToolId || "");
  state.ui.productTab = loadStoredValue(STORAGE_KEYS.productTab, state.ui.productTab || "console");
  state.ui.execTab = loadStoredValue(STORAGE_KEYS.execTab, state.ui.execTab || "job");
  state.ui.activityTab = loadStoredValue(STORAGE_KEYS.activityTab, state.ui.activityTab || "tasks");
  state.ui.workspaceTab = loadStoredValue(STORAGE_KEYS.workspaceTab, state.ui.workspaceTab || "home");
  state.ui.workspaceMode = loadStoredValue(STORAGE_KEYS.workspaceMode, state.ui.workspaceMode || "use");
  state.ui.workspaceManageTab = loadStoredValue(STORAGE_KEYS.workspaceManageTab, state.ui.workspaceManageTab || "templates");
  state.ui.serverSort = loadStoredValue(STORAGE_KEYS.serverSort, state.ui.serverSort || "default");
  state.ui.serverOrder = loadStoredArray(STORAGE_KEYS.serverOrder);
  state.ui.serverPins = loadStoredArray(STORAGE_KEYS.serverPins);
  state.logSearch.query = loadStoredValue(STORAGE_KEYS.outputSearch, state.logSearch.query || "");
  state.selectedProviderProfileId = loadStoredValue(STORAGE_KEYS.selectedProviderProfile, state.selectedProviderProfileId || "");
  state.selectedWorkspaceAgentId = loadStoredValue(STORAGE_KEYS.selectedWorkspaceAgent, state.selectedWorkspaceAgentId || "");
  state.selectedWorkspaceToolId = loadStoredValue(STORAGE_KEYS.selectedWorkspaceTool, state.selectedWorkspaceToolId || "");
  state.ui.workspaceResourceServerId = loadStoredValue(STORAGE_KEYS.workspaceResourceServer, state.ui.workspaceResourceServerId || "");
  // Provider profiles will be loaded from API in loadStatus
  setProviderProfiles([], { render: false });
}

function restorePersistedForms() {
  restoreFormState("workspaceForm");
  restoreFormState("jobForm");
  restoreFormState("taskPlanForm");
  restoreFormState("transferForm");
  restoreWorkspaceLauncherDraft();
  const storedNodes = loadStoredJson(STORAGE_KEYS.workspaceNodes, []);
  setWorkspaceToolsDraft(loadStoredArray(STORAGE_KEYS.workspaceTools), { render: false });
  setWorkspaceAgentsDraft(defaultWorkspaceAgents(), { render: false });
  setWorkspaceModelDraft(defaultWorkspaceModel(), { render: false });
  if (!state.selectedWorkspaceId) {
    setWorkspaceNodesDraft(
      Array.isArray(storedNodes) && storedNodes.length ? storedNodes : buildWorkspaceStarterNodes(workspaceFormPayload()),
      { formData: workspaceFormPayload() },
    );
  } else {
    renderWorkspacePanels();
  }
  toggleWorkspaceSourceFields();
  syncIgnoreStateFromInput();
  toggleTaskTemplateFields();
  state.ui.formsRestored = true;
}

function captureWorkspaceUiSnapshot() {
  return {
    workspaceUiRevision: Number(state.ui.workspaceUiRevision || 0),
    productTab: state.ui.productTab,
    workspaceTab: state.ui.workspaceTab,
    workspaceMode: state.ui.workspaceMode,
    workspaceManageTab: state.ui.workspaceManageTab,
    selectedWorkspaceId: state.selectedWorkspaceId,
    selectedWorkspaceNodeId: state.selectedWorkspaceNodeId,
    selectedWorkspaceExecutionNodeId: state.selectedWorkspaceExecutionNodeId,
    selectedWorkflowTemplateId: state.selectedWorkflowTemplateId,
    selectedTemplateNodeId: state.selectedTemplateNodeId,
    selectedGlobalAgentId: state.selectedGlobalAgentId,
    selectedGlobalToolId: state.selectedGlobalToolId,
    selectedProviderProfileId: state.selectedProviderProfileId,
    selectedWorkspaceAgentId: state.selectedWorkspaceAgentId,
    selectedWorkspaceToolId: state.selectedWorkspaceToolId,
    workspaceResourceServerId: state.ui.workspaceResourceServerId,
    workflowTemplateDirty: state.ui.workflowTemplateDirty,
    agentDefinitionDirty: state.ui.agentDefinitionDirty,
    toolDefinitionDirty: state.ui.toolDefinitionDirty,
    providerProfileDirty: state.ui.providerProfileDirty,
  };
}

function restoreWorkspaceUiSnapshot(snapshot = {}, options = {}) {
  if (!snapshot || typeof snapshot !== "object") return;
  const force = Boolean(options.force && Number(snapshot.workspaceUiRevision || 0) === Number(state.ui.workspaceUiRevision || 0));
  if ((force || !["console", "workspace", "exec", "activity"].includes(state.ui.productTab)) && ["console", "workspace", "exec", "activity"].includes(snapshot.productTab)) {
    state.ui.productTab = snapshot.productTab;
  }
  if ((force || !["home", "config", "agents", "runs"].includes(state.ui.workspaceTab)) && ["home", "config", "agents", "runs"].includes(snapshot.workspaceTab)) {
    state.ui.workspaceTab = snapshot.workspaceTab;
  }
  if ((force || !["use", "manage"].includes(state.ui.workspaceMode)) && ["use", "manage"].includes(snapshot.workspaceMode)) {
    state.ui.workspaceMode = snapshot.workspaceMode;
  }
  if ((force || !["templates", "agents", "tools", "ai"].includes(state.ui.workspaceManageTab)) && ["templates", "agents", "tools", "ai"].includes(snapshot.workspaceManageTab)) {
    state.ui.workspaceManageTab = snapshot.workspaceManageTab;
  }

  const workspaceId = String(snapshot.selectedWorkspaceId || "").trim();
  const currentWorkspaceValid = state.selectedWorkspaceId && state.workspaces.some((item) => String(item?.id || "") === state.selectedWorkspaceId);
  if ((force || !currentWorkspaceValid) && workspaceId && state.workspaces.some((item) => String(item?.id || "") === workspaceId)) {
    state.selectedWorkspaceId = workspaceId;
  } else if (!currentWorkspaceValid && state.selectedWorkspaceId) {
    state.selectedWorkspaceId = state.workspaces[0]?.id || "";
  }

  const templateId = String(snapshot.selectedWorkflowTemplateId || "").trim();
  const currentTemplateValid = state.selectedWorkflowTemplateId && state.workflowTemplates.some((item) => String(item?.id || "") === state.selectedWorkflowTemplateId);
  if ((force || !currentTemplateValid) && templateId && state.workflowTemplates.some((item) => String(item?.id || "") === templateId)) {
    state.selectedWorkflowTemplateId = templateId;
  }
  const globalAgentId = String(snapshot.selectedGlobalAgentId || "").trim();
  const currentGlobalAgentValid = state.selectedGlobalAgentId && state.agentDefinitions.some((item) => String(item?.id || "") === state.selectedGlobalAgentId);
  if ((force || !currentGlobalAgentValid) && globalAgentId && state.agentDefinitions.some((item) => String(item?.id || "") === globalAgentId)) {
    state.selectedGlobalAgentId = globalAgentId;
  }
  const globalToolId = String(snapshot.selectedGlobalToolId || "").trim();
  const currentGlobalToolValid = state.selectedGlobalToolId && state.toolDefinitions.some((item) => String(item?.id || "") === state.selectedGlobalToolId);
  if ((force || !currentGlobalToolValid) && globalToolId && state.toolDefinitions.some((item) => String(item?.id || "") === globalToolId)) {
    state.selectedGlobalToolId = globalToolId;
  }

  const workspace = selectedWorkspace();
  const executionNodes = Array.isArray(workspace?.execution?.nodes) && workspace.execution.nodes.length
    ? workspace.execution.nodes
    : Array.isArray(workspace?.nodes)
      ? workspace.nodes
      : [];
  const executionNodeId = String(snapshot.selectedWorkspaceExecutionNodeId || "").trim();
  const currentExecutionNodeValid = state.selectedWorkspaceExecutionNodeId && executionNodes.some((node) => String(node?.id || "") === state.selectedWorkspaceExecutionNodeId);
  if ((force || !currentExecutionNodeValid) && executionNodeId && executionNodes.some((node) => String(node?.id || "") === executionNodeId)) {
    state.selectedWorkspaceExecutionNodeId = executionNodeId;
  }

  const workspaceNodeId = String(snapshot.selectedWorkspaceNodeId || "").trim();
  const currentWorkspaceNodeValid = state.selectedWorkspaceNodeId && state.workspaceNodesDraft.some((node) => String(node?.id || "") === state.selectedWorkspaceNodeId);
  if ((force || !currentWorkspaceNodeValid) && workspaceNodeId && state.workspaceNodesDraft.some((node) => String(node?.id || "") === workspaceNodeId)) {
    state.selectedWorkspaceNodeId = workspaceNodeId;
  }
  const templateNodeId = String(snapshot.selectedTemplateNodeId || "").trim();
  const currentTemplateNodeValid = state.selectedTemplateNodeId && Array.isArray(state.workflowTemplateDraft?.nodes) && state.workflowTemplateDraft.nodes.some((node) => String(node?.id || "") === state.selectedTemplateNodeId);
  if ((force || !currentTemplateNodeValid) && templateNodeId && Array.isArray(state.workflowTemplateDraft?.nodes) && state.workflowTemplateDraft.nodes.some((node) => String(node?.id || "") === templateNodeId)) {
    state.selectedTemplateNodeId = templateNodeId;
  }

  const providerProfileId = String(snapshot.selectedProviderProfileId || "").trim();
  if ((force || !state.selectedProviderProfileId) && providerProfileId) state.selectedProviderProfileId = providerProfileId;
  const workspaceAgentId = String(snapshot.selectedWorkspaceAgentId || "").trim();
  const currentWorkspaceAgentValid = state.selectedWorkspaceAgentId && state.workspaceAgentsDraft.some((item) => String(item?.id || "") === state.selectedWorkspaceAgentId);
  if ((force || !currentWorkspaceAgentValid) && workspaceAgentId && state.workspaceAgentsDraft.some((item) => String(item?.id || "") === workspaceAgentId)) {
    state.selectedWorkspaceAgentId = workspaceAgentId;
  }
  const workspaceToolId = String(snapshot.selectedWorkspaceToolId || "").trim();
  const currentWorkspaceToolValid = state.selectedWorkspaceToolId && state.workspaceToolsDraft.some((item) => String(item?.id || "") === state.selectedWorkspaceToolId);
  if ((force || !currentWorkspaceToolValid) && workspaceToolId && state.workspaceToolsDraft.some((item) => String(item?.id || "") === workspaceToolId)) {
    state.selectedWorkspaceToolId = workspaceToolId;
  }

  const resourceServerId = String(snapshot.workspaceResourceServerId || "").trim();
  const currentResourceServerValid = state.ui.workspaceResourceServerId && state.servers.some((server) => String(server?.id || "") === state.ui.workspaceResourceServerId);
  if ((force || !currentResourceServerValid) && resourceServerId && state.servers.some((server) => String(server?.id || "") === resourceServerId)) {
    state.ui.workspaceResourceServerId = resourceServerId;
  }

  state.ui.workflowTemplateDirty = Boolean(state.ui.workflowTemplateDirty || snapshot.workflowTemplateDirty);
  state.ui.agentDefinitionDirty = Boolean(state.ui.agentDefinitionDirty || snapshot.agentDefinitionDirty);
  state.ui.toolDefinitionDirty = Boolean(state.ui.toolDefinitionDirty || snapshot.toolDefinitionDirty);
  state.ui.providerProfileDirty = Boolean(state.ui.providerProfileDirty || snapshot.providerProfileDirty);
}

function applyStatusPayload(payload = {}, options = {}) {
  const preserveWorkspaceUi = Boolean(options.preserveWorkspaceUi);
  state.servers = payload.servers || [];
  state.jobs = payload.jobs || [];
  state.workspaces = payload.workspaces || [];
  state.workflowTemplates = payload.workflow_templates || [];
  state.agentDefinitions = payload.agent_definitions || [];
  state.toolDefinitions = payload.tool_definitions || [];
  if (!preserveWorkspaceUi) {
    if (state.selectedWorkspaceId && !state.workspaces.some((item) => item.id === state.selectedWorkspaceId)) {
      state.selectedWorkspaceId = "";
      saveStoredValue(STORAGE_KEYS.selectedWorkspace, "");
    }
    if (state.selectedWorkflowTemplateId && !state.workflowTemplates.some((item) => item.id === state.selectedWorkflowTemplateId)) {
      state.selectedWorkflowTemplateId = "";
      saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, "");
      state.ui.workflowTemplateDirty = false;
    }
    if (state.selectedGlobalAgentId && !state.agentDefinitions.some((item) => item.id === state.selectedGlobalAgentId)) {
      state.selectedGlobalAgentId = "";
      saveStoredValue(STORAGE_KEYS.selectedGlobalAgent, "");
      state.ui.agentDefinitionDirty = false;
    }
    if (state.selectedGlobalToolId && !state.toolDefinitions.some((item) => item.id === state.selectedGlobalToolId)) {
      state.selectedGlobalToolId = "";
      saveStoredValue(STORAGE_KEYS.selectedGlobalTool, "");
      state.ui.toolDefinitionDirty = false;
    }
  }
  syncServerOrderingState();
  updateServerHistory(state.servers);
  updatePollTimer(payload.config?.poll_interval_seconds);
  const allServers = payload.servers || [];
  const knownServerIds = new Set(allServers.map((server) => server.id));
  if (!state.selectedServer || !knownServerIds.has(state.selectedServer)) {
    const preferred = allServers.find((server) => server.online)
      || allServers.find((server) => serverIsReachable(server))
      || allServers[0]
      || null;
    state.selectedServer = preferred?.id || null;
    state.selectedGpu = "auto";
  }
  if (!preserveWorkspaceUi) {
    if (!state.selectedWorkspaceId && state.workspaces.length) {
      state.selectedWorkspaceId = state.workspaces[0].id;
      saveStoredValue(STORAGE_KEYS.selectedWorkspace, state.selectedWorkspaceId);
    }
    if (!state.selectedWorkflowTemplateId && state.workflowTemplates.length) {
      state.selectedWorkflowTemplateId = state.workflowTemplates[0].id;
      saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, state.selectedWorkflowTemplateId);
    }
    if (!state.selectedGlobalAgentId && state.agentDefinitions.length) {
      state.selectedGlobalAgentId = state.agentDefinitions[0].id;
      saveStoredValue(STORAGE_KEYS.selectedGlobalAgent, state.selectedGlobalAgentId);
    }
    if (!state.selectedGlobalToolId && state.toolDefinitions.length) {
      state.selectedGlobalToolId = state.toolDefinitions[0].id;
      saveStoredValue(STORAGE_KEYS.selectedGlobalTool, state.selectedGlobalToolId);
    }
  }
  if (state.selectedServer) saveStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer);
}

function statusTimestampMs(value) {
  const ms = Date.parse(String(value || ""));
  return Number.isFinite(ms) ? ms : 0;
}

function applyServerRefreshPayload(payload = {}, serverId = "") {
  const id = String(serverId || "").trim();
  const refreshedServer = payload.server
    || (Array.isArray(payload.servers) ? payload.servers.find((server) => String(server?.id || "") === id) : null);
  if (!refreshedServer?.id) {
    applyStatusPayload(payload, { preserveWorkspaceUi: true });
    return;
  }

  const nextId = String(refreshedServer.id || "");
  const existingIndex = state.servers.findIndex((server) => String(server?.id || "") === nextId);
  const existing = existingIndex >= 0 ? state.servers[existingIndex] : null;
  const existingCollectedAt = statusTimestampMs(existing?.collected_at);
  const nextCollectedAt = statusTimestampMs(refreshedServer.collected_at);
  const shouldReplace = existingIndex < 0
    || !existingCollectedAt
    || !nextCollectedAt
    || nextCollectedAt >= existingCollectedAt;

  if (shouldReplace) {
    if (existingIndex >= 0) {
      state.servers = state.servers.map((server, index) => (index === existingIndex ? refreshedServer : server));
    } else {
      state.servers = [...state.servers, refreshedServer];
    }
    syncServerOrderingState();
    updateServerHistory(state.servers);
  }
  if (Array.isArray(payload.jobs)) state.jobs = payload.jobs;
  if (Array.isArray(payload.workspaces)) state.workspaces = payload.workspaces;
  if (Array.isArray(payload.workflow_templates)) state.workflowTemplates = payload.workflow_templates;
  if (Array.isArray(payload.agent_definitions)) state.agentDefinitions = payload.agent_definitions;
  if (Array.isArray(payload.tool_definitions)) state.toolDefinitions = payload.tool_definitions;
  updatePollTimer(payload.config?.poll_interval_seconds);
  const knownServerIds = new Set(state.servers.map((server) => server.id));
  if (!state.selectedServer || !knownServerIds.has(state.selectedServer)) {
    state.selectedServer = knownServerIds.has(nextId) ? nextId : (state.servers[0]?.id || null);
    state.selectedGpu = "auto";
  }
  if (state.selectedServer) saveStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer);
}

async function loadStatus(force = false, options = {}) {
  const endpoint = force ? "/api/refresh" : "/api/status";
  const renderWorkspace = options.renderWorkspace ?? !state.ui.formsRestored;
  const workspaceSnapshot = renderWorkspace ? null : captureWorkspaceUiSnapshot();
  const requestId = state.ui.statusRequestSeq + 1;
  state.ui.statusRequestSeq = requestId;
  state.ui.statusBusyCount += 1;
  if (force) {
    state.ui.statusManualBusyCount += 1;
    state.ui.statusBusyVisibleUntil = Math.max(state.ui.statusBusyVisibleUntil || 0, Date.now() + 450);
  }
  updateRefreshButtonState();
  try {
    const payload = await fetchJson(endpoint);
    if (requestId !== state.ui.statusRequestSeq) return;
    applyStatusPayload(payload, { preserveWorkspaceUi: !renderWorkspace });
    if (workspaceSnapshot) restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true });
    // Provider/Profile data belongs to the workbench editor; monitor-only refresh should not disturb drafts.
    if (renderWorkspace) await loadProviderProfiles({ render: true });
    if (requestId !== state.ui.statusRequestSeq) return;
    render(payload, { workspace: renderWorkspace });
    if (!state.ui.formsRestored) {
      restorePersistedForms();
      render(payload, { workspace: true });
    }
    if (renderWorkspace) {
      if (!state.ui.workflowTemplateDirty && state.selectedWorkflowTemplateId) {
        const activeTemplate = workflowTemplateById(state.selectedWorkflowTemplateId);
        if (activeTemplate) {
          state.workflowTemplateDraft = normalizeWorkflowTemplateDraft(activeTemplate);
          if (!state.selectedTemplateNodeId || !state.workflowTemplateDraft.nodes.some((node) => node.id === state.selectedTemplateNodeId)) {
            state.selectedTemplateNodeId = state.workflowTemplateDraft.nodes[0]?.id || "";
          }
        }
      }
      if (!state.ui.agentDefinitionDirty && state.selectedGlobalAgentId) {
        const activeAgent = globalAgentById(state.selectedGlobalAgentId);
        if (activeAgent) state.agentDefinitionDraft = normalizeGlobalAgentDefinitionDraft(activeAgent);
      }
      if (!state.ui.toolDefinitionDirty && state.selectedGlobalToolId) {
        const activeTool = globalToolById(state.selectedGlobalToolId);
        if (activeTool) state.toolDefinitionDraft = normalizeGlobalToolDefinitionDraft(activeTool);
      }
      if (state.selectedWorkspaceId && ($("workspaceIdInput")?.value !== state.selectedWorkspaceId || !state.workspaceNodesDraft.length)) {
        selectWorkspace(state.selectedWorkspaceId, { persist: false });
      }
      renderWorkspaceWorkbench();
    } else if (state.ui.productTab === "workspace") {
      renderWorkspaceResourceSurfaces();
    }
    void updateTransferProgress();
    await loadTmuxSessions();
  } catch (error) {
    if (requestId !== state.ui.statusRequestSeq) return;
    $("healthPill").textContent = "api error";
    $("healthPill").classList.add("bad");
    $("refreshMeta").textContent = error.message;
  } finally {
    state.ui.statusBusyCount = Math.max(0, state.ui.statusBusyCount - 1);
    if (force) state.ui.statusManualBusyCount = Math.max(0, state.ui.statusManualBusyCount - 1);
    if (state.ui.statusBusyCount === 0) {
      const remaining = Math.max((state.ui.statusBusyVisibleUntil || 0) - Date.now(), 0);
      scheduleRefreshButtonStateUpdate(remaining);
    }
    updateRefreshButtonState();
  }
}

function updateSelectedServerRefreshButton() {
  const button = $("refreshSelectedServerBtn");
  if (!button) return;
  const busy = Boolean(state.selectedServer && state.ui.serverRefreshBusy[state.selectedServer]);
  button.disabled = !state.selectedServer || busy;
  button.textContent = busy ? "刷新中" : "刷新选中服务器";
}

async function loadTmuxSessions() {
  if (!state.selectedServer) return;
  try {
    const payload = await fetchJson(`/api/servers/${encodeURIComponent(state.selectedServer)}/tmux`);
    state.tmuxSessions = payload.sessions || [];
    state.tmuxError = "";
  } catch (error) {
    state.tmuxSessions = [];
    state.tmuxError = error.message;
  }
  renderTmuxSessions();
}

async function refreshServerStatus(serverId) {
  const id = String(serverId || "").trim();
  if (!id || state.ui.serverRefreshBusy[id]) return;
  const workspaceSnapshot = captureWorkspaceUiSnapshot();
  const requestId = Number(state.ui.serverRefreshSeq[id] || 0) + 1;
  state.ui.serverRefreshSeq[id] = requestId;
  state.ui.serverRefreshBusy[id] = true;
  renderServers();
  updateSelectedServerRefreshButton();
  try {
    const payload = await fetchJson(`/api/servers/${encodeURIComponent(id)}/refresh`);
    if (state.ui.serverRefreshSeq[id] !== requestId) return;
    applyServerRefreshPayload(payload, id);
    restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true });
    render(payload, { workspace: false });
    if (state.ui.productTab === "workspace") renderWorkspaceResourceSurfaces();
    await loadTmuxSessions();
    return payload;
  } catch (error) {
    $("refreshMeta").textContent = `单机刷新失败：${error.message}`;
  } finally {
    if (state.ui.serverRefreshSeq[id] === requestId) {
      delete state.ui.serverRefreshBusy[id];
      delete state.ui.serverRefreshSeq[id];
      renderServers();
      updateSelectedServerRefreshButton();
    }
  }
}

function renderWorkspaceResourceSurfaces() {
  renderWorkspaceCockpitOverview();
  renderWorkspaceExecutionBoard();
  renderWorkspaceExecutionDetail();
  updateWorkspaceAutomationBusyControls();
}

async function refreshWorkspaceResourceSnapshot(serverId = "") {
  const id = String(serverId || "").trim();
  if (id) {
    await refreshServerStatus(id);
    renderWorkspaceResourceSurfaces();
    return;
  }
  if (state.ui.workspaceResourceRefreshBusy) return;
  const workspaceSnapshot = captureWorkspaceUiSnapshot();
  state.ui.workspaceResourceRefreshBusy = true;
  renderWorkspaceCockpitOverview();
  try {
    const payload = await fetchJson("/api/refresh");
    applyStatusPayload(payload, { preserveWorkspaceUi: true });
    restoreWorkspaceUiSnapshot(workspaceSnapshot, { force: true });
    render(payload, { workspace: false });
    renderWorkspaceResourceSurfaces();
    void updateTransferProgress();
    await loadTmuxSessions();
  } catch (error) {
    $("refreshMeta").textContent = `资源刷新失败：${error.message}`;
  } finally {
    state.ui.workspaceResourceRefreshBusy = false;
    renderWorkspaceCockpitOverview();
  }
}

async function submitJob(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = $("formMessage");
  const data = Object.fromEntries(new FormData(form).entries());
  data.wait_for_idle = form.wait_for_idle.checked;
  data.min_free_mib = Number(data.min_free_mib || 0);
  data.max_gpu_util = Number(data.max_gpu_util || 0);
  const metadata = {};
  if (String(data.workspace_id || "").trim()) metadata.workspace_id = String(data.workspace_id || "").trim();
  if (String(data.workspace_node_id || "").trim()) metadata.node_id = String(data.workspace_node_id || "").trim();
  if (String(data.workspace_node_title || "").trim()) metadata.node_title = String(data.workspace_node_title || "").trim();
  if (Object.keys(metadata).length) data.metadata = metadata;
  message.textContent = "正在提交...";
  message.classList.remove("error");
  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || response.statusText);
    state.selectedJob = payload.job.id;
    message.textContent = `任务${zhStatus(payload.job.status)}：${payload.job.id}`;
    persistFormState("jobForm");
    await loadStatus(true);
    await showLog(payload.job.id);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

function shellQuote(value) {
  const text = String(value ?? "");
  return `'${text.replaceAll("'", "'\\''")}'`;
}

function pathBaseName(path) {
  const normalized = String(path || "").replace(/[\\\/]+$/, "");
  return normalized.split(/[\\\/]/).filter(Boolean).pop() || normalized || "传输";
}

function normalizeTransferEndpoint(value, serverId) {
  const text = String(value || "").trim();
  if (!text || parseRsyncTargetPrefix(text)) return text;
  const server = serverById(serverId);
  if (!server || server.mode === "local") return text;
  return `${transferTargetPrefix(server)}${text}`;
}

async function submitTransfer(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = $("transferMessage");
  syncIgnoreStateFromInput();
  const data = Object.fromEntries(new FormData(form).entries());
  const sourceItems = state.transfer.sources.length
    ? state.transfer.sources
        .map((item) => ({
          value: item.value,
          server_id: item.serverId,
          path: item.path,
          is_dir: item.isDir,
        }))
        .filter((item) => item.value)
    : [{
        value: normalizeTransferEndpoint(data.source, transferSourceServerId()),
        server_id: transferSourceServerId(),
        path: parseRsyncTargetPath(data.source) || String(data.source || "").trim(),
        is_dir: String(data.source || "").trim().endsWith("/"),
      }].filter((item) => item.value);
  const sources = sourceItems.map((item) => item.value);
  const target = normalizeTransferEndpoint(data.target, transferTargetServerId());
  const excludes = state.transfer.ignores.length
    ? state.transfer.ignores
    : parseIgnoreText(data.exclude || "");
  if (!sources.length || !target) {
    message.textContent = "至少要加入一个源路径，并填写目标路径。";
    message.classList.add("error");
    return;
  }
  if (parseRsyncTargetPrefix(target) && sources.some((source) => parseRsyncTargetPrefix(source))) {
    message.textContent = "当前传输任务从本机启动 rsync，暂不支持远程服务器到远程服务器。请让源或目标至少一个是本机。";
    message.classList.add("error");
    return;
  }
  const baseParts = ["rsync", "-avPh", "--info=progress2"];
  if (form.checksum?.checked) {
    baseParts.push("--checksum");
  } else if (form.size_only?.checked) {
    baseParts.push("--size-only");
  }
  if (form.resume_partial?.checked) baseParts.push("--partial", "--append-verify");
  excludes.forEach((item) => {
    baseParts.push("--exclude", shellQuote(item));
  });
  const commandForSource = (source) => [...baseParts, shellQuote(source), shellQuote(target)].join(" ");
  const command = sources.length === 1
    ? commandForSource(sources[0])
    : ["set -e", ...sources.map((source) => commandForSource(source))].join("\n");
  const localServer = state.servers.find((server) => server.mode === "local") || serverById("local");
  if (!localServer) {
    message.textContent = "没有找到本机服务器配置，无法从本机启动 rsync。";
    message.classList.add("error");
    return;
  }
  message.textContent = "正在加入文件传输任务...";
  message.classList.remove("error");
  try {
    const payload = await fetchJson("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: sources.length === 1 ? `文件传输 ${pathBaseName(sources[0])}` : `文件传输 ${sources.length} 项`,
        server_id: localServer.id,
        gpu_index: "none",
        wait_for_idle: false,
        kind: "transfer",
        command,
        command_display: command,
        metadata: {
          transfer_spec: {
            sources: sourceItems,
            target,
            target_server_id: transferTargetServerId(),
            excludes,
            options: {
              checksum: Boolean(form.checksum?.checked),
              size_only: Boolean(form.size_only?.checked),
              resume_partial: Boolean(form.resume_partial?.checked),
            },
          },
        },
        cwd: "",
        env_name: "",
        min_free_mib: 0,
        max_gpu_util: 100,
      }),
    });
    message.textContent = `已加入任务中心：${payload.job.id}`;
    persistFormState("transferForm");
    await loadStatus(true);
    await updateTransferProgress();
    await showLog(payload.job.id);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function showLog(jobId) {
  const job = state.jobs.find((item) => item.id === jobId);
  const tab = upsertOutputTab({
    type: "job",
    jobId,
    title: `任务 · ${job?.name || jobId}`,
    content: "正在读取日志...",
  });
  activateOutputTab(tab.key);
}

async function showTmux(sessionName) {
  if (!state.selectedServer) return;
  const server = serverById(state.selectedServer);
  const tab = upsertOutputTab({
    type: "tmux",
    serverId: state.selectedServer,
    sessionName,
    title: `tmux · ${server?.name || state.selectedServer} · ${sessionName}`,
    content: `正在抓取 tmux 会话 ${sessionName} ...`,
  });
  activateOutputTab(tab.key);
}

async function refreshActiveOutput(options = {}) {
  if (!state.activeOutput || state.outputBusy) return;
  if (state.activeOutput.type === "process" || state.activeOutput.type === "terminal") return;
  state.outputBusy = true;
  try {
    if (state.activeOutput.type === "job") {
      const jobId = state.activeOutput.jobId;
      const payload = await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}/log`);
      setLogTitle(`任务日志 · ${jobId}`);
      state.activeOutput.content = payload.log || "日志为空。";
      setLogText(state.activeOutput.content, options);
      return;
    }
    if (state.activeOutput.type === "tmux") {
      const { serverId, sessionName } = state.activeOutput;
      const server = serverById(serverId);
      const payload = await fetchJson(
        `/api/servers/${encodeURIComponent(serverId)}/tmux/${encodeURIComponent(sessionName)}/capture?lines=50000`,
      );
      setLogTitle(`tmux · ${server?.name || serverId} · ${sessionName}`);
      state.activeOutput.content = payload.log || "（会话当前没有可见输出）";
      setLogText(state.activeOutput.content, options);
    }
  } catch (error) {
    setLogText(error.message, options);
  } finally {
    state.outputBusy = false;
  }
}

function startLogPoller() {
  if (state.logPollTimer) return;
  state.logPollTimer = setInterval(() => {
    if (!$("logAutoRefresh")?.checked) return;
    if ($("logPane")?.hidden) return;
    void refreshActiveOutput();
  }, 3000);
}

function showActionError(error) {
  setLogTitle("操作失败");
  setLogText(error?.message || String(error || "操作失败"), { resetX: true, forceBottom: true });
  setLogPaneOpen(true);
  setTerminalControlsVisible(false);
}

async function stopJob(event, jobId) {
  consumeClick(event);
  const button = event.currentTarget;
  if (button) {
    button.disabled = true;
    button.textContent = "取消中";
  }
  try {
    await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}/stop`, { method: "POST" });
  } catch (error) {
    showActionError(error);
  } finally {
    await loadStatus(true);
    await updateTransferProgress();
  }
}

async function retryJob(event, jobId) {
  consumeClick(event);
  const button = event.currentTarget;
  if (button) {
    button.disabled = true;
    button.textContent = "重试中";
  }
  try {
    const payload = await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
    await loadStatus(true);
    if (payload.job?.id) await showLog(payload.job.id);
  } catch (error) {
    showActionError(error);
  } finally {
    await updateTransferProgress();
  }
}

async function deleteJob(event, jobId) {
  consumeClick(event);
  if (!confirm("确定要删除这个任务吗？")) return;
  const button = event.currentTarget;
  if (button) {
    button.disabled = true;
    button.textContent = "删除中";
  }
  try {
    await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
    state.jobs = state.jobs.filter((j) => j.id !== jobId);
    renderJobs();
  } catch (error) {
    showActionError(error);
  }
}

async function clearCompletedJobs(event) {
  consumeClick(event);
  const completedCount = state.jobs.filter((j) => ["done", "failed", "stopped"].includes(j.status)).length;
  if (completedCount === 0) {
    alert("没有已完成的任务可清理");
    return;
  }
  if (!confirm(`确定要清理 ${completedCount} 个已完成的任务吗？`)) return;
  try {
    const payload = await fetchJson("/api/jobs/clear-completed", { method: "DELETE" });
    state.jobs = state.jobs.filter((j) => !["done", "failed", "stopped"].includes(j.status));
    renderJobs();
    alert(`已清理 ${payload.deleted} 个任务`);
  } catch (error) {
    showActionError(error);
  }
}

async function copyJob(event, jobId) {
  consumeClick(event);
  const button = event.currentTarget;
  if (button) {
    button.disabled = true;
    button.textContent = "复制中";
  }
  try {
    const payload = await fetchJson(`/api/jobs/${encodeURIComponent(jobId)}/copy`, { method: "POST" });
    await loadStatus(true);
    if (payload.job?.id) await showLog(payload.job.id);
  } catch (error) {
    showActionError(error);
  } finally {
    await updateTransferProgress();
  }
}

async function submitWorkspace(event) {
  event.preventDefault();
  const message = $("workspaceMessage");
  const payload = workspacePayloadForSave();
  message.textContent = payload.workspace_id ? "正在更新工作区..." : "正在保存工作区...";
  message.classList.remove("error");
  try {
    const endpoint = payload.workspace_id
      ? `/api/workspaces/${encodeURIComponent(payload.workspace_id)}`
      : "/api/workspaces";
    const response = await fetchJson(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    persistFormState("workspaceForm");
    await loadStatus(true, { renderWorkspace: true });
    const workspace = response.workspace || workspaceById(payload.workspace_id) || selectedWorkspace();
    if (workspace?.id) {
      selectWorkspace(workspace.id, {
        persist: true,
        selectedNodeId: state.selectedWorkspaceNodeId,
        selectedExecutionNodeId: state.selectedWorkspaceExecutionNodeId,
      });
    }
    message.textContent = payload.workspace_id ? "工作区已更新。" : "工作区已保存。";
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

function fillJobFormFromNode(node) {
  const form = $("jobForm");
  const message = $("workspaceMessage");
  if (!form || !node || node.kind !== "run.command") {
    if (message) {
      message.textContent = "先选择一个运行节点。";
      message.classList.add("error");
    }
    return;
  }
  const config = node.config || {};
  if (form.elements.cwd) form.elements.cwd.value = config.workspace_dir || $("workspaceDir")?.value || "";
  if (form.elements.env_name) form.elements.env_name.value = config.env_name || $("workspaceEnvName")?.value || "";
  if (form.elements.command) form.elements.command.value = config.run_command || "";
  if (config.server_id && form.elements.server_id) {
    const options = Array.from(form.elements.server_id.options || []);
    if (options.some((option) => option.value === config.server_id)) {
      form.elements.server_id.value = config.server_id;
      state.selectedServer = config.server_id;
      renderFormOptions();
    }
  }
  bindJobToWorkspaceNode(node);
  persistFormState("jobForm");
  switchProductTab("exec");
  switchExecTab("job");
  if (message) {
    message.textContent = `已把节点“${node.title || workspaceNodeLabel(node.kind)}”填入执行面板。`;
    message.classList.remove("error");
  }
}

function fillJobFormFromWorkspace() {
  const node = workspaceRunNode();
  const message = $("workspaceMessage");
  if (!node) {
    message.textContent = "先选择一个带运行命令的工作区。";
    message.classList.add("error");
    return;
  }
  fillJobFormFromNode(node);
}

function taskPlanPayload(dryRun = false) {
  const form = $("taskPlanForm");
  const data = Object.fromEntries(new FormData(form).entries());
  data.limit = Number(data.limit || 0);
  data.max_gpu_util = Number(data.max_gpu_util || 0);
  data.max_memory_mib = Number(data.max_memory_mib || 0);
  data.profile_safety = Number(data.profile_safety || 1.2);
  data.profile_first = form.profile_first.checked;
  data.dry_run = dryRun;
  if (data.server_id === "auto") {
    data.candidate_server_ids = onlineServers().map((server) => server.id);
  }
  return data;
}

function renderTaskPlanPreview(payload) {
  const box = $("taskPlanPreview");
  const items = payload.items || [];
  if (!items.length) {
    box.textContent = "没有可调度的任务。";
    return;
  }
  const thresholds = items.map((item) => Number(item.min_free_mib || item.estimated_mib || 0)).filter((value) => value > 0);
  const minThreshold = thresholds.length ? Math.min(...thresholds) : 0;
  const maxThreshold = thresholds.length ? Math.max(...thresholds) : 0;
  const previewLimit = 24;
  const rows = items.slice(0, previewLimit).map((item, index) => {
    const meta = item.metadata || {};
    const desc = meta.template === "preset"
      ? `${meta.dataset} · ${meta.arch} · ${meta.ablation} · ${meta.dino}`
      : JSON.stringify(meta.params || {});
    return `
      <tr>
        <td>${index + 1}</td>
        <td title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</td>
        <td title="${escapeHtml(desc)}">${escapeHtml(desc)}</td>
        <td>${fmtMiB(item.min_free_mib || item.estimated_mib)}</td>
        <td title="${escapeHtml(item.command)}"><div class="cmd">${escapeHtml(item.command)}</div></td>
      </tr>
    `;
  }).join("");
  const extra = items.length > previewLimit ? `<p class="muted">仅显示前 ${previewLimit} 个，共 ${items.length} 个。</p>` : "";
  const profileText = payload.profile_first ? "会先运行 profile/smoke，再释放训练任务。" : "直接按显存阈值排队。";
  const thresholdText = thresholds.length
    ? `显存阈值范围 ${fmtMiB(minThreshold)} - ${fmtMiB(maxThreshold)}。`
    : "未设置额外显存阈值。";
  box.innerHTML = `
    <div class="plan-summary">将提交 ${items.length} 个任务，${profileText} ${thresholdText}</div>
    <div class="table-wrap mini-table">
      <table>
        <thead>
          <tr><th>#</th><th>任务</th><th>参数</th><th>阈值</th><th>命令</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    ${extra}
  `;
}

async function previewTaskPlan() {
  const message = $("taskPlanMessage");
  message.textContent = "正在生成预览...";
  message.classList.remove("error");
  try {
    const payload = await fetchJson("/api/task-plans/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskPlanPayload(true)),
    });
    renderTaskPlanPreview(payload);
    message.textContent = `预览完成：${payload.count} 个任务。`;
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function scheduleTaskPlan(event) {
  event.preventDefault();
  const message = $("taskPlanMessage");
  message.textContent = "正在加入任务中心...";
  message.classList.remove("error");
  try {
    const payload = await fetchJson("/api/task-plans/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskPlanPayload(false)),
    });
    message.textContent = `已加入 ${payload.batch_jobs} 个任务` +
      (payload.profile_jobs ? `，另有 ${payload.profile_jobs} 个 profile/smoke 任务。` : "。");
    persistFormState("taskPlanForm");
    await loadStatus(true);
    const firstJob = (payload.jobs || [])[0];
    if (firstJob) await showLog(firstJob.id);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

function toggleTaskTemplateFields() {
  const template = $("taskTemplateSelect")?.value || "preset";
  $("presetTemplateFields").hidden = template !== "preset";
  $("customTemplateFields").hidden = template !== "custom";
  $("taskPlanPreview").textContent = "选择模板后点击预览。";
  $("taskPlanMessage").textContent = "";
  $("taskPlanMessage").classList.remove("error");
}

async function openTerminal() {
  const server = selectedTerminalServerFromForm();
  const message = $("terminalMessage");
  if (!server) {
    message.textContent = "没有可打开的服务器。";
    message.classList.add("error");
    return;
  }
  if (!serverIsReachable(server)) {
    message.textContent = "所选服务器当前未连接，先检查密码、网络或 SSH 配置。";
    message.classList.add("error");
    return;
  }
  message.textContent = "正在页面打开终端...";
  message.title = "";
  message.classList.remove("error");
  try {
    const payload = await fetchJson("/api/terminal/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ server_id: server.id }),
    });
    const terminal = {
      id: payload.id,
      cursor: payload.cursor || 0,
      alive: payload.alive,
      serverId: payload.server_id,
      serverName: payload.server_name || server.name,
      text: stripAnsi(payload.output || ""),
      pollTimer: state.terminal.pollTimer,
    };
    state.terminals[terminal.id] = terminal;
    state.terminal = terminal;
    state.selectedServer = server.id;
    saveStoredValue(STORAGE_KEYS.selectedServer, server.id);
    showTerminalOutput();
    switchActivityTab("terminal");
    startTerminalPoller();
    $("terminalInput").focus();
    message.textContent = `已在页面打开：${state.terminal.serverName}`;
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

function scrollTerminalBottom() {
  requestAnimationFrame(() => {
    const output = $("logView");
    output.scrollTop = output.scrollHeight;
  });
}

function appendTerminalOutput(text) {
  if (!text) return;
  const clean = stripAnsi(text);
  state.terminal.text += clean;
  if (state.terminal.text.length > 1_000_000) {
    state.terminal.text = state.terminal.text.slice(-900_000);
  }
  const tab = state.outputTabs.find((item) => item.type === "terminal" && item.terminalId === state.terminal.id);
  if (tab) tab.content = state.terminal.text;
  if (state.activeOutput?.type !== "terminal" || state.activeOutput.terminalId !== state.terminal.id) return;
  const output = $("logView");
  const wasNearBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 80;
  setLogText(state.terminal.text, {
    forceBottom: wasNearBottom || $("logFollow")?.checked,
  });
}

async function pollTerminalOutput() {
  if (!state.terminal.id) return;
  try {
    const payload = await fetchJson(
      `/api/terminal/sessions/${encodeURIComponent(state.terminal.id)}/output?cursor=${encodeURIComponent(state.terminal.cursor)}`,
    );
    state.terminal.cursor = payload.cursor || state.terminal.cursor;
    state.terminal.alive = payload.alive;
    appendTerminalOutput(payload.output || "");
    if (!payload.alive) {
      $("terminalMessage").textContent = "页面终端已退出。";
    }
  } catch (error) {
    appendTerminalOutput(`\n[RelayGraph] ${error.message}\n`);
    state.terminal.alive = false;
  }
}

function startTerminalPoller() {
  if (state.terminal.pollTimer) return;
  state.terminal.pollTimer = setInterval(() => {
    if (
      state.terminal.id &&
      state.terminal.alive &&
      state.activeOutput?.type === "terminal" &&
      state.activeOutput.terminalId === state.terminal.id
    ) {
      void pollTerminalOutput();
    }
  }, 1000);
}

async function sendTerminalInput(data) {
  if (!state.terminal.id || !state.terminal.alive) {
    appendTerminalOutput("\n[RelayGraph] 终端没有运行。\n");
    return;
  }
  await fetchJson(`/api/terminal/sessions/${encodeURIComponent(state.terminal.id)}/input`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data }),
  });
}

async function sendTerminalSignal(signalValue = 2) {
  if (!state.terminal.id || !state.terminal.alive) {
    appendTerminalOutput("\n[RelayGraph] 终端没有运行。\n");
    return;
  }
  await fetchJson(`/api/terminal/sessions/${encodeURIComponent(state.terminal.id)}/signal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ signal: signalValue }),
  });
}

async function submitTerminalInput(event) {
  event.preventDefault();
  const input = $("terminalInput");
  const value = input.value;
  if (!value) return;
  input.value = "";
  await sendTerminalInput(`${value}\n`);
}

async function closeCurrentTerminal(options = {}) {
  const terminalId = state.terminal.id;
  if (!terminalId) return;
  try {
    await fetchJson(`/api/terminal/sessions/${encodeURIComponent(terminalId)}`, {
      method: "DELETE",
    });
  } catch (error) {
    if (!options.silent) appendTerminalOutput(`\n[RelayGraph] ${error.message}\n`);
  }
  state.terminal.id = null;
  state.terminal.cursor = 0;
  state.terminal.alive = false;
  state.terminal.serverId = null;
  state.terminal.serverName = "";
  state.terminal.text = "";
  delete state.terminals[terminalId];
  const tabIndex = state.outputTabs.findIndex((item) => item.type === "terminal" && item.terminalId === terminalId);
  if (tabIndex >= 0) state.outputTabs.splice(tabIndex, 1);
  if (!options.silent) {
    $("terminalMessage").textContent = "页面终端已关闭。";
    const next = state.outputTabs[tabIndex] || state.outputTabs[tabIndex - 1] || state.outputTabs[0];
    if (next) activateOutputTab(next.key);
    else clearActiveOutput();
  } else {
    renderOutputTabs();
  }
}

const PROCESS_COLUMN_MIN = {
  server: 76,
  gpu: 52,
  pid: 72,
  user: 84,
  vram: 78,
  command: 220,
  actions: 80,
};

const PROCESS_COLUMN_MAX_NARROW = {
  server: 120,
  gpu: 68,
  pid: 96,
  user: 108,
  vram: 98,
  command: 360,
  actions: 96,
};

function processColumnMaxWidth(colName) {
  if (window.innerWidth >= 1500) return Number.POSITIVE_INFINITY;
  return PROCESS_COLUMN_MAX_NARROW[colName] || Number.POSITIVE_INFINITY;
}

function clampProcessColumnWidth(colName, width) {
  const minWidth = PROCESS_COLUMN_MIN[colName] || 64;
  const maxWidth = processColumnMaxWidth(colName);
  return Math.max(minWidth, Math.min(Number(width || minWidth), maxWidth));
}

function updateProcessTableWidth() {
  const table = $("processTable");
  if (!table) return;
  const total = Array.from(table.querySelectorAll("col[data-col]")).reduce((sum, col) => {
    return sum + Number.parseInt(col.style.width || "0", 10);
  }, 0);
  if (total > 0) table.style.minWidth = `${total}px`;
}

function loadProcessColumnWidths() {
  const table = $("processTable");
  if (!table) return;
  table.querySelectorAll("col[data-col]").forEach((col) => {
    const key = `tc-process-col-${col.dataset.col}`;
    const saved = Number.parseInt(localStorage.getItem(key) || "", 10);
    const fallback = Number.parseInt(col.style.width || "0", 10);
    const next = Number.isFinite(saved) && saved > 40 ? saved : fallback;
    col.style.width = `${clampProcessColumnWidth(col.dataset.col || "", next)}px`;
  });
  updateProcessTableWidth();
}

function enforceProcessColumnWidthConstraints() {
  const table = $("processTable");
  if (!table) return;
  table.querySelectorAll("col[data-col]").forEach((col) => {
    const current = Number.parseInt(col.style.width || "0", 10);
    const next = clampProcessColumnWidth(col.dataset.col || "", current);
    if (next !== current) {
      col.style.width = `${next}px`;
      localStorage.setItem(`tc-process-col-${col.dataset.col}`, String(next));
    }
  });
  updateProcessTableWidth();
}

function bindProcessColumnResize() {
  const table = $("processTable");
  if (!table) return;
  table.querySelectorAll("th[data-col] .col-resizer").forEach((handle) => {
    handle.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const th = event.currentTarget.closest("th[data-col]");
      const colName = th.dataset.col;
      const col = table.querySelector(`col[data-col="${CSS.escape(colName)}"]`);
      if (!col) return;
      const startX = event.clientX;
      const startWidth = Number.parseInt(col.style.width || `${th.offsetWidth}`, 10);
      handle.classList.add("dragging");
      const onMove = (moveEvent) => {
        const width = clampProcessColumnWidth(colName, startWidth + moveEvent.clientX - startX);
        col.style.width = `${width}px`;
        localStorage.setItem(`tc-process-col-${colName}`, String(width));
        updateProcessTableWidth();
      };
      const onUp = () => {
        handle.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  });
}

function handleWorkspaceAutomationAction(button) {
  if (!button?.dataset?.action) return false;
  const action = button.dataset.action;
  if (action === "select-execution-node" && button.dataset.nodeId) {
    selectWorkspaceExecutionNode(button.dataset.nodeId);
    return true;
  }
  if (action === "create-workspace") {
    void createWorkspaceTask("create");
    return true;
  }
  if (action === "create-workspace-discover") {
    void createWorkspaceTask("discover");
    return true;
  }
  if (action === "create-workspace-run") {
    void createWorkspaceTask("run");
    return true;
  }
  if (action === "switch-workspace-manage") {
    switchWorkspaceMode("manage");
    return true;
  }
  if (action === "advance-workspace-automation") {
    void advanceWorkspaceAutomation();
    return true;
  }
  if (action === "apply-workspace-automation") {
    void applyWorkspaceAutomationDefaults();
    return true;
  }
  if (action === "run-workspace-discovery") {
    void runWorkspaceDiscovery();
    return true;
  }
  if (action === "run-selected-workspace") {
    void runWorkspaceWorkflow();
    return true;
  }
  if (action === "run-selected-node" && button.dataset.nodeId) {
    void runWorkspaceNode(button.dataset.nodeId);
    return true;
  }
  if (action === "open-selected-node-log" && button.dataset.jobId) {
    void showLog(button.dataset.jobId);
    return true;
  }
  if (action === "open-last-workspace-log") {
    const workspace = selectedWorkspace();
    const jobId = String(workspace?.execution?.last_job_id || "").trim();
    if (jobId) void showLog(jobId);
    else setWorkspaceUseMessage("当前实例还没有最近任务输出。", true);
    return true;
  }
  if (action === "fill-job-from-selected-workspace") {
    fillJobFormFromWorkspace();
    return true;
  }
  if (action === "refresh-workspace-resources") {
    void refreshWorkspaceResourceSnapshot("");
    return true;
  }
  if (action === "refresh-workspace-resource-server") {
    void refreshWorkspaceResourceSnapshot(button.dataset.serverId || "");
    return true;
  }
  if (action === "refresh-workspace-resource-selected-server") {
    const picker = button
      .closest(".workspace-cockpit-resource-actions")
      ?.querySelector("[data-role='workspace-resource-server-select']");
    void refreshWorkspaceResourceSnapshot(picker?.value || state.ui.workspaceResourceServerId || "");
    return true;
  }
  return false;
}

function bindEvents() {
  $("serverSortSelect")?.addEventListener("change", (event) => {
    state.ui.serverSort = event.target.value || "default";
    saveStoredValue(STORAGE_KEYS.serverSort, state.ui.serverSort);
    renderServers();
  });
  $("serverList")?.addEventListener("click", (event) => {
    const refreshButton = event.target.closest("[data-action='refresh-server']");
    if (refreshButton?.dataset.id) {
      event.stopPropagation();
      void refreshServerStatus(refreshButton.dataset.id);
      return;
    }
    const pinButton = event.target.closest("[data-action='pin-server']");
    if (pinButton?.dataset.id) {
      event.stopPropagation();
      toggleServerPin(pinButton.dataset.id);
      return;
    }
    const item = event.target.closest(".server-item[data-id]");
    if (item?.dataset.id) selectServer(item.dataset.id);
  });
  $("serverList")?.addEventListener("pointerover", (event) => {
    const item = event.target.closest(".server-item[data-id]");
    if (!item?.dataset.id || !$("serverList")?.contains(item)) return;
    if (event.relatedTarget && item.contains(event.relatedTarget)) return;
    showServerResourcePopover(item.dataset.id, item);
  });
  $("serverList")?.addEventListener("pointerout", (event) => {
    const item = event.target.closest(".server-item[data-id]");
    if (!item?.dataset.id) return;
    const overlay = $("serverResourceOverlay");
    if (event.relatedTarget && (item.contains(event.relatedTarget) || overlay?.contains(event.relatedTarget))) return;
    scheduleHideServerResourcePopover();
  });
  $("serverList")?.addEventListener("focusin", (event) => {
    const item = event.target.closest(".server-item[data-id]");
    if (item?.dataset.id) showServerResourcePopover(item.dataset.id, item);
  });
  $("serverList")?.addEventListener("focusout", (event) => {
    const item = event.target.closest(".server-item[data-id]");
    const overlay = $("serverResourceOverlay");
    if (event.relatedTarget && (item?.contains(event.relatedTarget) || overlay?.contains(event.relatedTarget))) return;
    scheduleHideServerResourcePopover();
  });
  $("serverList")?.addEventListener("scroll", () => positionServerResourcePopover(), { passive: true });
  window.addEventListener("resize", () => positionServerResourcePopover());
  window.addEventListener("scroll", () => positionServerResourcePopover(), true);
  $("serverList")?.addEventListener("dragstart", (event) => {
    if ((state.ui.serverSort || "default") !== "manual") {
      event.preventDefault();
      return;
    }
    const item = event.target.closest(".server-item[data-id]");
    if (!item?.dataset.id) return;
    state.serverDnd.draggingId = item.dataset.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", item.dataset.id);
    item.classList.add("dragging");
  });
  $("serverList")?.addEventListener("dragover", (event) => {
    if ((state.ui.serverSort || "default") !== "manual" || !state.serverDnd.draggingId) return;
    const item = event.target.closest(".server-item[data-id]");
    if (!item?.dataset.id || item.dataset.id === state.serverDnd.draggingId) return;
    event.preventDefault();
    const rect = item.getBoundingClientRect();
    const position = event.clientY < rect.top + rect.height / 2 ? "before" : "after";
    state.serverDnd.overId = item.dataset.id;
    state.serverDnd.position = position;
    document.querySelectorAll("#serverList .server-item").forEach((node) => {
      node.classList.remove("drop-before", "drop-after");
    });
    item.classList.add(position === "before" ? "drop-before" : "drop-after");
  });
  $("serverList")?.addEventListener("drop", (event) => {
    if ((state.ui.serverSort || "default") !== "manual") return;
    const item = event.target.closest(".server-item[data-id]");
    if (!item?.dataset.id || !state.serverDnd.draggingId) return;
    event.preventDefault();
    moveServerInManualOrder(state.serverDnd.draggingId, item.dataset.id, state.serverDnd.position || "after");
    state.serverDnd.draggingId = "";
    state.serverDnd.overId = "";
    state.serverDnd.position = "";
    renderServers();
  });
  $("serverList")?.addEventListener("dragend", () => {
    state.serverDnd.draggingId = "";
    state.serverDnd.overId = "";
    state.serverDnd.position = "";
    document.querySelectorAll("#serverList .server-item").forEach((node) => {
      node.classList.remove("dragging", "drop-before", "drop-after");
    });
  });
  $("execTabs")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) switchExecTab(button.dataset.tab);
  });
  $("mainNav")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (button) switchProductTab(button.dataset.view);
  });
  $("workspaceTabs")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) switchWorkspaceTab(button.dataset.tab);
  });
  $("workspaceModuleCards")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) switchWorkspaceTab(button.dataset.tab);
  });
  $("workspaceModeSwitch")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-mode]");
    if (button) switchWorkspaceMode(button.dataset.mode);
  });
  $("workspaceManageTabs")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) switchWorkspaceManageTab(button.dataset.tab);
  });
  $("workspaceManageOverviewCards")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='switch-workspace-manage-tab']");
    if (button?.dataset.tab) switchWorkspaceManageTab(button.dataset.tab);
  });
  $("workspaceTemplateSelect")?.addEventListener("change", (event) => {
    state.selectedWorkflowTemplateId = event.target.value || "";
    saveStoredValue(STORAGE_KEYS.selectedWorkflowTemplate, state.selectedWorkflowTemplateId);
    renderWorkspaceWorkbench();
  });
  [
    "workspaceTaskGoalInput",
    "workspaceTaskRepoInput",
    "workspaceTaskPaperInput",
    "workspaceTaskReferenceInput",
    "workspaceTaskContextInput",
  ].forEach((id) => {
    $(id)?.addEventListener("input", () => {
      saveWorkspaceLauncherDraft();
      renderWorkspaceCockpitOverview();
    });
  });
  $("workspaceCreateTaskBtn")?.addEventListener("click", () => {
    void createWorkspaceTask("create");
  });
  $("workspaceCreateDiscoverTaskBtn")?.addEventListener("click", () => {
    void createWorkspaceTask("discover");
  });
  $("workspaceCreateRunTaskBtn")?.addEventListener("click", () => {
    void createWorkspaceTask("run");
  });
  $("workspaceUseChatSendBtn")?.addEventListener("click", () => {
    void submitWorkspaceUseChat();
  });
  $("workspaceUseChatInput")?.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void submitWorkspaceUseChat();
    }
  });
  $("activityTabs")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) switchActivityTab(button.dataset.tab, { revealOutput: true });
  });
  $("refreshBtn").addEventListener("click", () => loadStatus(true));
  $("refreshSelectedServerBtn")?.addEventListener("click", () => {
    if (!state.selectedServer) {
      $("refreshMeta").textContent = "先选择一台服务器，再刷新单机状态。";
      return;
    }
    void refreshServerStatus(state.selectedServer);
  });
  $("terminalBtn").addEventListener("click", openTerminal);
  $("workspaceForm")?.addEventListener("submit", submitWorkspace);
  $("workspaceForm")?.addEventListener("input", (event) => {
    const field = event.target.name;
    if (!field) return;
    if (field === "source_type") return;
    const syncNodeFields = [
      "brief",
      "repo_url",
      "repo_ref",
      "paper_url",
      "idea_text",
      "workspace_dir",
      "env_name",
      "env_manager",
      "python_version",
      "setup_command",
      "run_command",
      "report_command",
      "schedule",
    ];
    const renderOnlyFields = ["name", "references", "tags", "status", "notes"];
    if (syncNodeFields.includes(field)) {
      syncWorkspaceNodesFromForm();
      renderWorkspacePanels();
      return;
    }
    if (renderOnlyFields.includes(field)) {
      renderWorkspacePanels();
      return;
    }
    renderWorkspaceHeader();
  });
  $("workspaceSourceType")?.addEventListener("change", () => {
    toggleWorkspaceSourceFields();
    replacePrimarySourceNodeKind($("workspaceSourceType")?.value || "repo");
    persistFormState("workspaceForm");
  });
  $("workspaceResetBtn")?.addEventListener("click", clearWorkspaceForm);
  $("workspaceRunFlowBtn")?.addEventListener("click", () => {
    void runWorkspaceWorkflow();
  });
  $("workspaceFillJobBtn")?.addEventListener("click", fillJobFormFromWorkspace);
  $("workspaceChatSendBtn")?.addEventListener("click", () => {
    void submitWorkspaceChat();
  });
  $("workspaceChatInput")?.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void submitWorkspaceChat();
    }
  });
  $("workspaceChatAgentSelect")?.addEventListener("change", (event) => {
    updateWorkspaceModelDraft({ chat_agent_id: event.target.value || "" });
  });
  $("workspaceFillRolesBtn")?.addEventListener("click", () => {
    mergeRecommendedWorkspaceAgents();
  });
  $("workspaceRestoreToolsBtn")?.addEventListener("click", () => {
    mergeRecommendedWorkspaceTools();
  });
  $("workspaceAssignRolesBtn")?.addEventListener("click", () => {
    applyRecommendedNodeAssignments();
  });
  $("workspaceAddAgentBtn")?.addEventListener("click", addWorkspaceAgent);
  $("workspaceAddToolBtn")?.addEventListener("click", addWorkspaceTool);
  $("workspaceModelProfileSelect")?.addEventListener("change", (event) => {
    updateWorkspaceModelDraft({ provider_profile_id: event.target.value || "" });
  });
  $("workspaceModelRoutingSelect")?.addEventListener("change", (event) => {
    updateWorkspaceModelDraft({ routing_mode: event.target.value || "workspace_default" });
  });
  $("workspaceModelChatAgentSelect")?.addEventListener("change", (event) => {
    updateWorkspaceModelDraft({ chat_agent_id: event.target.value || "" });
  });
  $("workspaceModelNotes")?.addEventListener("input", (event) => {
    updateWorkspaceModelDraft({ notes: event.target.value || "" });
  });
  $("workspaceExecutionBoard")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-execution-node']");
    if (button?.dataset.nodeId) selectWorkspaceExecutionNode(button.dataset.nodeId);
  });
  $("workspaceExecutionDetail")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (button) handleWorkspaceAutomationAction(button);
  });
  $("workspaceCockpitOperations")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (button) handleWorkspaceAutomationAction(button);
  });
  $("workspaceCockpitReadiness")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (button) handleWorkspaceAutomationAction(button);
  });
  $("workspaceCockpitOperations")?.addEventListener("change", (event) => {
    const picker = event.target.closest("[data-role='workspace-resource-server-select']");
    if (!picker) return;
    const next = picker.value || "";
    if (state.ui.workspaceResourceServerId !== next) markWorkspaceUiInteraction();
    state.ui.workspaceResourceServerId = next;
    saveStoredValue(STORAGE_KEYS.workspaceResourceServer, state.ui.workspaceResourceServerId);
    renderWorkspaceCockpitOverview();
  });
  $("workspaceHistoryList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='delete-workspace']");
    if (button?.dataset.workspaceId) {
      event.stopPropagation();
      void deleteWorkspace(button.dataset.workspaceId);
      return;
    }
    const item = event.target.closest("[data-action='select-workspace']");
    if (item?.dataset.workspaceId) selectWorkspace(item.dataset.workspaceId);
  });
  $("workflowTemplateList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-workflow-template']");
    if (button?.dataset.templateId) selectWorkflowTemplate(button.dataset.templateId);
  });
  $("workspaceNewTemplateBtn")?.addEventListener("click", () => newWorkflowTemplateDraft("repo"));
  $("workspaceDeleteTemplateBtn")?.addEventListener("click", () => {
    void deleteSelectedWorkflowTemplate();
  });
  $("workspaceSaveTemplateBtn")?.addEventListener("click", () => {
    void saveWorkflowTemplate();
  });
  document.querySelectorAll(".workspace-template-seeds [data-seed]").forEach((button) => {
    button.addEventListener("click", () => newWorkflowTemplateDraft(button.dataset.seed || "repo"));
  });
  [
    ["templateNameInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, name: value }))],
    ["templateStatusSelect", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, status: value || "ready" }))],
    ["templateTagsInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, tags: parseTagList(value || "") }))],
    ["templateDescriptionInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, description: value || "" }))],
    ["templateBriefInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, brief: value || "" }))],
    ["templateRepoUrlInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, source: { ...(draft.source || {}), repo_url: value || "" } }))],
    ["templateRepoRefInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, source: { ...(draft.source || {}), repo_ref: value || "" } }))],
    ["templatePaperUrlInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, source: { ...(draft.source || {}), paper_url: value || "" } }))],
    ["templateWorkspaceDirInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, workspace_dir: value || "" }))],
    ["templateIdeaInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, source: { ...(draft.source || {}), idea_text: value || "" } }))],
    ["templateEnvNameInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, env: { ...(draft.env || {}), name: value || "" } }))],
    ["templatePythonVersionInput", (value) => updateWorkflowTemplateDraft((draft) => ({ ...draft, env: { ...(draft.env || {}), python: value || "" } }))],
  ].forEach(([id, handler]) => {
    $(id)?.addEventListener("input", (event) => handler(event.target.value || ""));
  });
  $("templateSourceTypeSelect")?.addEventListener("change", (event) => {
    const sourceType = event.target.value || "repo";
    updateWorkflowTemplateDraft((draft) => ({
      ...draft,
      source: { ...(draft.source || {}), type: sourceType },
      nodes: buildWorkspaceStarterNodes({
        source_type: workspaceChainSourceType(sourceType),
        repo_url: draft.source?.repo_url || "",
        repo_ref: draft.source?.repo_ref || "",
        paper_url: draft.source?.paper_url || "",
        idea_text: draft.source?.idea_text || draft.brief || "",
        workspace_dir: draft.workspace_dir || "",
        env_name: draft.env?.name || "",
        env_manager: draft.env?.manager || "conda",
        python_version: draft.env?.python || "",
      }),
    }));
  });
  $("templateEnvManagerSelect")?.addEventListener("change", (event) => {
    updateWorkflowTemplateDraft((draft) => ({ ...draft, env: { ...(draft.env || {}), manager: event.target.value || "conda" } }));
  });
  $("templateProviderProfileSelect")?.addEventListener("change", (event) => {
    updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), provider_profile_id: event.target.value || "" } }));
  });
  $("templateRoutingModeSelect")?.addEventListener("change", (event) => {
    updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), routing_mode: event.target.value || "workspace_default" } }));
  });
  $("templateChatAgentSelect")?.addEventListener("change", (event) => {
    updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), chat_agent_id: event.target.value || "" } }));
  });
  $("workflowTemplateAddNodeBtn")?.addEventListener("click", () => insertWorkflowTemplateNode($("workflowTemplateNodeKindSelect")?.value || "custom.step"));
  $("workflowTemplateMoveUpBtn")?.addEventListener("click", () => moveWorkflowTemplateNode("up"));
  $("workflowTemplateMoveDownBtn")?.addEventListener("click", () => moveWorkflowTemplateNode("down"));
  $("workflowTemplateDeleteNodeBtn")?.addEventListener("click", removeWorkflowTemplateNode);
  $("workflowTemplateRebuildBtn")?.addEventListener("click", rebuildWorkflowTemplateNodes);
  $("workflowTemplateNodeList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-template-node']");
    if (button?.dataset.nodeId) {
      state.selectedTemplateNodeId = button.dataset.nodeId;
      renderWorkspaceWorkbench();
    }
  });
  const handleTemplateNodeField = (event) => {
    const target = event.target;
    if (target.matches("[data-manage-node-field]")) {
      const key = target.dataset.manageNodeField;
      updateSelectedWorkflowTemplateNode((node) => ({ ...node, [key]: target.value }));
      return;
    }
    if (target.matches("[data-manage-handler-field]")) {
      const key = target.dataset.manageHandlerField;
      if (key === "agent_id") {
        const agent = globalAgentById(target.value || "");
        updateSelectedWorkflowTemplateNode((node) => ({
          ...node,
          handler: { ...(node.handler || {}), agent_id: target.value || "", name: agent?.name || node.handler?.name || "" },
        }));
        return;
      }
      updateSelectedWorkflowTemplateNode((node) => ({
        ...node,
        handler: { ...(node.handler || {}), [key]: target.value || "" },
      }));
      return;
    }
    if (target.matches("[data-config-key]")) {
      const key = target.dataset.configKey;
      updateSelectedWorkflowTemplateNode((node) => ({
        ...node,
        config: { ...(node.config || {}), [key]: target.value || "" },
      }));
    }
  };
  $("workflowTemplateNodeEditor")?.addEventListener("input", handleTemplateNodeField);
  $("workflowTemplateNodeEditor")?.addEventListener("change", handleTemplateNodeField);
  $("workspaceNewAgentBtn")?.addEventListener("click", newGlobalAgentDraft);
  $("manageAgentList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-global-agent']");
    if (button?.dataset.agentId) selectGlobalAgent(button.dataset.agentId);
  });
  $("manageAgentEditor")?.addEventListener("input", (event) => {
    const target = event.target;
    if (target.matches("[data-manage-agent-field]")) {
      const key = target.dataset.manageAgentField;
      updateAgentDefinitionDraft({ [key]: key === "tools" ? parseTagList(target.value || "") : target.value || "" });
      return;
    }
    if (target.id === "manageAgentDebugInput") {
      state.manageAgentDebug.input = target.value || "";
    }
  });
  $("manageAgentEditor")?.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-manage-agent-checkbox]")) {
      updateAgentDefinitionDraft({ [target.dataset.manageAgentCheckbox]: Boolean(target.checked) });
      return;
    }
    if (target.id === "manageAgentDebugTemplateSelect") {
      state.manageAgentDebug.templateId = target.value || "";
      return;
    }
    if (target.matches("[data-manage-agent-field]")) {
      const key = target.dataset.manageAgentField;
      updateAgentDefinitionDraft({ [key]: key === "tools" ? parseTagList(target.value || "") : target.value || "" });
    }
  });
  $("manageAgentEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-global-agent") {
      void saveGlobalAgentDefinition();
    } else if (button.dataset.action === "delete-global-agent") {
      void deleteGlobalAgentDefinition();
    } else if (button.dataset.action === "run-global-agent-debug") {
      void runGlobalAgentDebug();
    }
  });
  $("workspaceNewToolBtn")?.addEventListener("click", newGlobalToolDraft);
  $("manageToolList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-global-tool']");
    if (button?.dataset.toolId) selectGlobalTool(button.dataset.toolId);
  });
  $("manageToolEditor")?.addEventListener("input", (event) => {
    const target = event.target;
    if (target.matches("[data-manage-tool-field]")) {
      updateToolDefinitionDraft({ [target.dataset.manageToolField]: target.value || "" });
    }
  });
  $("manageToolEditor")?.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-manage-tool-checkbox]")) {
      updateToolDefinitionDraft({ [target.dataset.manageToolCheckbox]: Boolean(target.checked) });
      return;
    }
    if (target.matches("[data-manage-tool-field]")) {
      updateToolDefinitionDraft({ [target.dataset.manageToolField]: target.value || "" });
    }
  });
  $("manageToolEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-global-tool") {
      void saveGlobalToolDefinition();
    } else if (button.dataset.action === "delete-global-tool") {
      void deleteGlobalToolDefinition();
    }
  });
  $("workspaceManageAddProviderBtn")?.addEventListener("click", addManageProviderProfile);
  $("manageProviderProfileList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-provider-profile']");
    if (button?.dataset.profileId) selectProviderProfile(button.dataset.profileId);
  });
  $("manageAiEditor")?.addEventListener("input", (event) => {
    const target = event.target;
    if (target.matches("[data-manage-provider-field]")) {
      updateSelectedProviderProfile((profile) => ({
        ...profile,
        [target.dataset.manageProviderField]: target.value || "",
      }));
    }
  });
  $("manageAiEditor")?.addEventListener("change", (event) => {
    const target = event.target;
    if (target.id === "manageAiTemplateProfileSelect") {
      updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), provider_profile_id: target.value || "" } }));
      return;
    }
    if (target.id === "manageAiTemplateRoutingSelect") {
      updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), routing_mode: target.value || "workspace_default" } }));
      return;
    }
    if (target.id === "manageAiTemplateChatAgentSelect") {
      updateWorkflowTemplateDraft((draft) => ({ ...draft, model: { ...(draft.model || {}), chat_agent_id: target.value || "" } }));
      return;
    }
    if (target.matches("[data-manage-provider-field]")) {
      updateSelectedProviderProfile((profile) => ({
        ...profile,
        [target.dataset.manageProviderField]: target.value || "",
      }));
    }
  });
  $("manageAiEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "save-provider-profile") {
      void saveManageProviderProfile();
    } else if (button.dataset.action === "delete-provider-profile-manage") {
      void deleteManageProviderProfile();
    } else if (button.dataset.action === "save-template-routing") {
      void saveWorkflowTemplate();
    }
  });
  $("workspaceAddProviderBtn")?.addEventListener("click", addProviderProfile);
  $("workspaceAddNodeBtn")?.addEventListener("click", () => insertWorkspaceNode($("workspaceNodeKindSelect")?.value || "custom.step"));
  $("workspaceRebuildGraphBtn")?.addEventListener("click", rebuildWorkspaceStarterChain);
  $("workspaceNodeList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const nodeId = button.dataset.nodeId || "";
    if (button.dataset.action === "select-workspace-node") {
      selectWorkspaceNode(nodeId);
    } else if (button.dataset.action === "move-workspace-node") {
      moveWorkspaceNode(nodeId, button.dataset.direction || "down");
    } else if (button.dataset.action === "remove-workspace-node") {
      removeWorkspaceNode(nodeId);
    } else if (button.dataset.action === "run-workspace-node") {
      void runWorkspaceNode(nodeId);
    } else if (button.dataset.action === "fill-job-from-node") {
      fillJobFormFromNode(state.workspaceNodesDraft.find((node) => node.id === nodeId));
    }
  });
  $("workspaceNodeEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "sync-form-from-node") {
      syncWorkspaceFormFromNode(selectedWorkspaceNode());
    } else if (button.dataset.action === "run-workspace-node") {
      void runWorkspaceNode(button.dataset.nodeId || "");
    } else if (button.dataset.action === "fill-job-from-node") {
      fillJobFormFromNode(state.workspaceNodesDraft.find((node) => node.id === button.dataset.nodeId));
    }
  });
  $("workspaceAgentList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-workspace-agent']");
    if (button?.dataset.agentId) selectWorkspaceAgent(button.dataset.agentId);
  });
  $("workspaceAgentPresetList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='apply-agent-template']");
    if (button?.dataset.role) applyAgentTemplate(button.dataset.role);
  });
  $("workspaceAgentEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "remove-workspace-agent" && button.dataset.agentId) {
      removeWorkspaceAgent(button.dataset.agentId);
      return;
    }
    if (button.dataset.action === "prefill-workspace-agent-debug") {
      prefillWorkspaceAgentDebug();
      return;
    }
    if (button.dataset.action === "run-workspace-agent-debug" && button.dataset.agentId) {
      void debugWorkspaceAgent(button.dataset.agentId);
    }
  });
  $("workspaceToolList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-workspace-tool']");
    if (button?.dataset.toolId) selectWorkspaceTool(button.dataset.toolId);
  });
  $("workspaceToolEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    if (button.dataset.action === "add-workspace-tool") {
      addWorkspaceTool();
      return;
    }
    if (button.dataset.action === "remove-workspace-tool" && button.dataset.toolId) {
      removeWorkspaceTool(button.dataset.toolId);
    }
  });
  const handleWorkspaceAgentField = (event) => {
    const target = event.target;
    if (target.matches("[data-agent-field]")) {
      const key = target.dataset.agentField;
      updateSelectedWorkspaceAgent((agent) => ({
        ...agent,
        [key]: key === "tools" ? parseTagList(target.value) : target.value,
      }));
      return;
    }
    if (target.matches("[data-agent-debug-input]")) {
      state.workspaceAgentDebug.input = target.value;
      state.workspaceAgentDebug.error = "";
      return;
    }
    if (target.matches("[data-agent-checkbox]")) {
      const key = target.dataset.agentCheckbox;
      updateSelectedWorkspaceAgent((agent) => ({
        ...agent,
        [key]: Boolean(target.checked),
      }));
    }
  };
  $("workspaceAgentEditor")?.addEventListener("input", handleWorkspaceAgentField);
  $("workspaceAgentEditor")?.addEventListener("change", handleWorkspaceAgentField);
  const handleWorkspaceToolField = (event) => {
    const target = event.target;
    if (target.matches("[data-tool-field]")) {
      const key = target.dataset.toolField;
      updateSelectedWorkspaceTool((tool) => ({
        ...tool,
        [key]: target.value,
      }));
      return;
    }
    if (target.matches("[data-tool-checkbox]")) {
      const key = target.dataset.toolCheckbox;
      updateSelectedWorkspaceTool((tool) => ({
        ...tool,
        [key]: Boolean(target.checked),
      }));
    }
  };
  $("workspaceToolEditor")?.addEventListener("input", handleWorkspaceToolField);
  $("workspaceToolEditor")?.addEventListener("change", handleWorkspaceToolField);
  $("workspaceList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='delete-workspace']");
    if (button?.dataset.workspaceId) {
      event.stopPropagation();
      void deleteWorkspace(button.dataset.workspaceId);
      return;
    }
    const item = event.target.closest("[data-action='select-workspace']");
    if (item?.dataset.workspaceId) {
      selectWorkspace(item.dataset.workspaceId);
    }
  });
  $("workspaceRunList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (button?.dataset.jobId) {
      const actionEvent = actionProxyEvent(event, button);
      if (button.dataset.action === "open-workspace-run") {
        consumeClick(actionEvent);
        void showLog(button.dataset.jobId);
      } else if (button.dataset.action === "stop-workspace-run") {
        void stopJob(actionEvent, button.dataset.jobId);
      } else if (button.dataset.action === "retry-workspace-run") {
        void retryJob(actionEvent, button.dataset.jobId);
      } else if (button.dataset.action === "copy-workspace-run") {
        void copyJob(actionEvent, button.dataset.jobId);
      }
      return;
    }
    const item = event.target.closest(".workspace-run-item[data-job-id]");
    if (item?.dataset.jobId) void showLog(item.dataset.jobId);
  });
  $("workspaceRunList")?.addEventListener("keydown", (event) => {
    if (!["Enter", " "].includes(event.key)) return;
    const item = event.target.closest(".workspace-run-item[data-job-id]");
    if (!item?.dataset.jobId) return;
    consumeClick(event);
    void showLog(item.dataset.jobId);
  });
  $("providerProfileList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='select-provider-profile']");
    if (button?.dataset.profileId) selectProviderProfile(button.dataset.profileId);
  });
  $("providerProfileEditor")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='remove-provider-profile']");
    if (button?.dataset.profileId) removeProviderProfile(button.dataset.profileId);
  });
  const handleProviderField = (event) => {
    const target = event.target;
    if (!target.matches("[data-provider-field]")) return;
    const key = target.dataset.providerField;
    updateSelectedProviderProfile((profile) => ({
      ...profile,
      [key]: target.value,
    }));
  };
  $("providerProfileEditor")?.addEventListener("input", handleProviderField);
  $("providerProfileEditor")?.addEventListener("change", handleProviderField);
  const handleNodeEditorField = (event) => {
    const target = event.target;
    if (target.matches("[data-node-field]")) {
      const key = target.dataset.nodeField;
      updateSelectedWorkspaceNode((node) => ({ ...node, [key]: target.value }));
      return;
    }
    if (target.matches("[data-handler-field]")) {
      const key = target.dataset.handlerField;
      if (key === "agent_id") {
        const linkedAgent = workspaceAgentById(target.value);
        updateSelectedWorkspaceNode((node) => ({
          ...node,
          handler: {
            ...(node.handler || {}),
            agent_id: target.value,
            name: linkedAgent?.name || node.handler?.name || "",
          },
        }));
        return;
      }
      updateSelectedWorkspaceNode((node) => ({
        ...node,
        handler: { ...(node.handler || {}), [key]: target.value },
      }));
      return;
    }
    if (target.matches("[data-config-key]")) {
      const key = target.dataset.configKey;
      updateSelectedWorkspaceNode((node) => ({
        ...node,
        config: { ...(node.config || {}), [key]: target.value },
      }));
      syncWorkspaceFormFromNode(selectedWorkspaceNode());
      return;
    }
  };
  $("workspaceNodeEditor")?.addEventListener("input", handleNodeEditorField);
  $("workspaceNodeEditor")?.addEventListener("change", handleNodeEditorField);
  $("jobForm").addEventListener("submit", submitJob);
  $("transferForm")?.addEventListener("submit", submitTransfer);
  $("sourceBrowseBtn")?.addEventListener("click", () => openFilePicker("source"));
  $("sourceInspectBtn")?.addEventListener("click", () => loadTransferSourceTree());
  $("transferSourceInput")?.addEventListener("blur", syncTransferSourceServerFromInput);
  $("transferSourceServerSelect")?.addEventListener("change", () => {
    const input = $("transferSourceInput");
    if (input) input.value = transferPathOnly(input.value);
    state.transfer.source = null;
    state.transfer.tree = {};
    renderTransferTree();
  });
  $("targetBrowseBtn")?.addEventListener("click", () => openFilePicker("target"));
  $("targetInspectBtn")?.addEventListener("click", () => loadTransferTargetTree());
  $("transferTargetInput")?.addEventListener("blur", syncTransferTargetServerFromInput);
  $("transferTargetServerSelect")?.addEventListener("change", () => {
    const input = $("transferTargetInput");
    if (input) input.value = transferPathOnly(input.value);
    state.transfer.target = null;
    state.transfer.targetTree = {};
    renderTargetTree();
  });
  $("transferExcludeInput")?.addEventListener("change", syncIgnoreStateFromInput);
  $("ignoreChips")?.addEventListener("click", (event) => {
    const button = event.target.closest(".chip-remove");
    if (!button) return;
    removeTransferIgnore(button.dataset.ignore || "");
  });
  $("selectedSourceList")?.addEventListener("click", (event) => {
    const clearButton = event.target.closest("[data-action='clear-transfer-sources']");
    if (clearButton) {
      clearTransferSources();
      return;
    }
    const removeButton = event.target.closest("[data-source-key]");
    if (!removeButton) return;
    removeTransferSource(removeButton.dataset.sourceKey || "");
  });
  $("transferTree")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const path = button.dataset.path || "";
    const isDir = button.dataset.dir === "1";
    if (button.dataset.action === "toggle-transfer-node") {
      void toggleTransferNode(path, isDir);
    } else if (button.dataset.action === "add-transfer-source") {
      addTransferSource(path, isDir);
    } else if (button.dataset.action === "ignore-transfer-node") {
      addTransferIgnore(path, isDir);
    }
  });
  $("targetTree")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const path = button.dataset.path || "";
    const isDir = button.dataset.dir === "1";
    if (button.dataset.action === "toggle-target-node") {
      void toggleTransferTargetNode(path, isDir);
    } else if (button.dataset.action === "choose-target-node") {
      chooseTransferTargetDirectory(path);
    }
  });
  $("closeFilePickerBtn")?.addEventListener("click", closeFilePicker);
  $("filePickerModal")?.addEventListener("click", (event) => {
    if (event.target.id === "filePickerModal") closeFilePicker();
  });
  $("filePickerOpenBtn")?.addEventListener("click", () => loadFilePicker($("filePickerPathInput").value));
  $("filePickerPathInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void loadFilePicker(event.currentTarget.value);
    }
  });
  $("filePickerPathInput")?.addEventListener("input", () => {
    state.filePicker.requestId = (state.filePicker.requestId || 0) + 1;
  });
  $("filePickerUpBtn")?.addEventListener("click", () => {
    if (state.filePicker.parent) void loadFilePicker(state.filePicker.parent);
  });
  $("filePickerChooseDirBtn")?.addEventListener("click", () => {
    if (state.filePicker.path) void chooseFilePickerPath(state.filePicker.path, true);
  });
  $("filePickerRoots")?.addEventListener("click", (event) => {
    const button = event.target.closest(".root-button");
    if (button?.dataset.path) void loadFilePicker(button.dataset.path);
  });
  $("filePickerList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const row = button.closest(".file-picker-row");
    if (!row) return;
    const path = row.dataset.path || "";
    const isDir = row.dataset.dir === "1";
    if (button.dataset.action === "open-picker") {
      void loadFilePicker(path);
    } else if (button.dataset.action === "preview-picker") {
      void previewFileInPicker(path);
    } else if (button.dataset.action === "choose-picker") {
      void chooseFilePickerPath(path, isDir);
    }
  });
  $("taskPlanForm")?.addEventListener("submit", scheduleTaskPlan);
  $("taskPlanPreviewBtn")?.addEventListener("click", previewTaskPlan);
  $("taskTemplateSelect")?.addEventListener("change", toggleTaskTemplateFields);
  $("planServerSelect")?.addEventListener("change", renderTaskPlanOptions);
  $("terminalServerSelect")?.addEventListener("change", (event) => {
    state.selectedServer = event.target.value;
    saveStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer);
    state.selectedGpu = "auto";
    render();
    loadTmuxSessions();
  });
  $("serverSelect").addEventListener("change", (event) => {
    state.selectedServer = event.target.value;
    saveStoredValue(STORAGE_KEYS.selectedServer, state.selectedServer);
    state.selectedGpu = "auto";
    clearTerminalMessage();
    render();
    loadTmuxSessions();
  });
  $("gpuSelect").addEventListener("change", (event) => {
    state.selectedGpu = event.target.value;
    renderGpuRows();
    if (state.selectedGpu !== "auto") scrollGpuSelectionIntoView();
  });
  $("logRefreshBtn")?.addEventListener("click", () => refreshActiveOutput({ forceBottom: true }));
  $("logSearchInput")?.addEventListener("input", (event) => {
    setLogSearchQuery(event.target.value, { focusMatch: Boolean(event.target.value) });
  });
  $("logSearchPrevBtn")?.addEventListener("click", () => moveLogSearch(-1));
  $("logSearchNextBtn")?.addEventListener("click", () => moveLogSearch(1));
  $("logDownloadBtn")?.addEventListener("click", downloadActiveOutput);
  $("logClearBtn")?.addEventListener("click", collapseLogPane);
  $("terminalInputForm").addEventListener("submit", submitTerminalInput);
  $("terminalCtrlCBtn").addEventListener("click", () => sendTerminalSignal(2));
  $("terminalCloseBtn").addEventListener("click", () => closeCurrentTerminal());
  $("processSearch")?.addEventListener("input", (event) => {
    state.processFilters.query = event.target.value;
    renderProcesses();
  });
  $("processServerFilter")?.addEventListener("change", (event) => {
    state.processFilters.server = event.target.value;
    renderProcesses();
  });
  $("processUserFilter")?.addEventListener("change", (event) => {
    state.processFilters.user = event.target.value;
    renderProcesses();
  });
  $("processGpuFilter")?.addEventListener("change", (event) => {
    state.processFilters.gpu = event.target.value;
    renderProcesses();
  });
  $("jobSearch")?.addEventListener("input", (event) => {
    state.jobFilters.query = event.target.value;
    renderJobs();
  });
  $("jobStatusFilter")?.addEventListener("change", (event) => {
    state.jobFilters.status = event.target.value;
    renderJobs();
  });
  $("jobTypeFilter")?.addEventListener("change", (event) => {
    state.jobFilters.kind = event.target.value;
    renderJobs();
  });
  $("jobServerFilter")?.addEventListener("change", (event) => {
    state.jobFilters.server = event.target.value;
    renderJobs();
  });
  $("jobSortSelect")?.addEventListener("change", (event) => {
    state.jobFilters.sort = event.target.value;
    renderJobs();
  });
  document.querySelectorAll("#processTable th[data-sort]").forEach((th) => {
    th.addEventListener("click", (event) => {
      if (event.target.closest(".col-resizer")) return;
      const key = th.dataset.sort;
      if (state.processFilters.sort === key) {
        state.processFilters.dir = state.processFilters.dir === "asc" ? "desc" : "asc";
      } else {
        state.processFilters.sort = key;
        state.processFilters.dir = ["pid", "vram", "gpu"].includes(key) ? "desc" : "asc";
      }
      renderProcesses();
    });
  });
  $("manageServersBtn").addEventListener("click", openServerModal);
  $("closeModalBtn").addEventListener("click", closeServerModal);
  $("serverModal").addEventListener("click", (event) => {
    if (event.target.id === "serverModal") closeServerModal();
  });
  $("addServerForm").addEventListener("submit", addServer);
  const cancelEditBtn = $("addServerForm").querySelector(".cancel-edit-btn");
  if (cancelEditBtn) cancelEditBtn.addEventListener("click", cancelEdit);
  if ($("processTable")) {
    loadProcessColumnWidths();
    bindProcessColumnResize();
    window.addEventListener("resize", enforceProcessColumnWidthConstraints);
  }
  ["workspaceForm", "jobForm", "taskPlanForm", "transferForm"].forEach((formId) => {
    const form = $(formId);
    form?.addEventListener("input", () => persistFormState(formId));
    form?.addEventListener("change", () => persistFormState(formId));
  });
  renderIgnoreChips();
  renderTargetTree();
  renderTransferProgress();
  toggleWorkspaceSourceFields();
  toggleTaskTemplateFields();
}

let editingServerId = null; // null = add mode, string = edit mode

async function openServerModal() {
  $("serverModal").hidden = false;
  await loadAdminServers();
}

function closeServerModal() {
  $("serverModal").hidden = true;
  $("adminServerMessage").textContent = "";
  $("adminServerMessage").classList.remove("error");
  $("addServerMessage").textContent = "";
  $("addServerMessage").classList.remove("error");
  cancelEdit();
}

function cancelEdit() {
  editingServerId = null;
  const form = $("addServerForm");
  form.reset();
  form.querySelector("button[type=submit]").textContent = "添加";
  const cancelBtn = form.querySelector(".cancel-edit-btn");
  if (cancelBtn) cancelBtn.hidden = true;
  $("addServerMessage").textContent = "";
}

function editServer(serverId) {
  const server = (state.ui.adminServers || []).find((s) => s.id === serverId);
  if (!server) return;
  const form = $("addServerForm");
  form.elements.name.value = server.name || "";
  form.elements.host_name.value = server.host_name || "";
  form.elements.ssh_alias.value = server.ssh_alias || "";
  form.elements.user.value = server.user || "";
  form.elements.port.value = server.port || "";
  form.elements.password.value = "";
  editingServerId = serverId;
  form.querySelector("button[type=submit]").textContent = "保存修改";
  const cancelBtn = form.querySelector(".cancel-edit-btn");
  if (cancelBtn) cancelBtn.hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function renderServerCheckResult(result) {
  if (!result?.checks?.length) return "";
  const rows = result.checks
    .map((item) => `
      <div class="check-row">
        <strong>${escapeHtml(item.label)}</strong>
        <span class="state ${item.ok ? "idle" : "failed"}">${item.ok ? "通过" : "失败"}</span>
        <span class="muted" title="${escapeHtml(item.detail || "")}">${escapeHtml(item.detail || "-")}</span>
      </div>
    `)
    .join("");
  return `
    <div class="check-result">
      <div class="check-grid">${rows}</div>
    </div>
  `;
}

async function loadAdminServers() {
  const list = $("adminServerList");
  const hidden = $("hiddenList");
  list.innerHTML = '<div class="empty">加载中...</div>';
  hidden.innerHTML = "";
  $("adminServerMessage").textContent = "";
  $("adminServerMessage").classList.remove("error");
  try {
    const payload = await fetchJson("/api/admin/servers");
    state.ui.adminServers = payload.servers || [];
    const discoveryPath = payload.discovery_config_path || "~/.ssh/config";
    const discoveryInfo = $("discoveryInfo");
    if (discoveryInfo) {
      discoveryInfo.textContent = `自动发现来自: ${discoveryPath} ｜ 连接使用系统默认 SSH 配置（~/.ssh/config）`;
    }
    list.innerHTML = state.ui.adminServers
      .map((server) => {
        const target = server.host_name
          ? `${server.user ? server.user + "@" : ""}${server.host_name}`
          : server.ssh_alias || server.id;
        const removeLabel = server.is_user ? "删除" : "隐藏";
        const editBtn = `<button class="secondary server-edit" data-id="${escapeHtml(server.id)}" type="button" title="把这台服务器配置载入下方表单进行编辑">编辑</button>`;
        const sourceLabel = server.is_user ? "user_servers.toml" : escapeHtml(server.source || "SSH config");
        const checkResult = state.ui.adminChecks[server.id];
        const checking = Boolean(state.ui.adminCheckBusy[server.id]);
        return `
          <div class="admin-row">
            <div class="admin-info">
              <div class="admin-name">${escapeHtml(server.name)} <span class="muted">(${escapeHtml(server.mode)}${server.is_user ? " · 自定义" : ""})</span></div>
              <div class="muted">${escapeHtml(target)}</div>
              <div class="muted" style="font-size:11px">来源: ${sourceLabel}</div>
              ${renderServerCheckResult(checkResult)}
            </div>
            <div class="admin-actions">
              <input class="alias-input" data-id="${escapeHtml(server.id)}" value="${escapeHtml(server.name)}" />
              <button class="secondary alias-save" data-id="${escapeHtml(server.id)}" type="button" title="保存这台服务器的显示名称">保存名称</button>
              ${editBtn}
              <button class="secondary server-check" data-id="${escapeHtml(server.id)}" type="button" title="检查 SSH、GPU 监控、tmux 和基础命令是否可用">${checking ? "检查中..." : "检查连接"}</button>
              <button class="secondary alias-remove" data-id="${escapeHtml(server.id)}" type="button" title="${server.is_user ? "删除这条自定义服务器配置" : "隐藏这条从 SSH config 自动发现的服务器"}">${removeLabel}</button>
            </div>
          </div>
        `;
      })
      .join("");
    list.querySelectorAll(".alias-save").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const input = list.querySelector(`.alias-input[data-id="${CSS.escape(id)}"]`);
        await saveAlias(id, input.value);
      });
    });
    list.querySelectorAll(".alias-remove").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("确认从列表移除该服务器？")) return;
        await removeServer(btn.dataset.id);
      });
    });
    list.querySelectorAll(".server-check").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await checkServerConnection(btn.dataset.id);
      });
    });
    list.querySelectorAll(".server-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        editServer(btn.dataset.id);
      });
    });

    const aliases = payload.aliases || {};
    const disabled = payload.disabled_discovery || [];
    if (disabled.length) {
      hidden.innerHTML = `
        <h4>已隐藏的发现项</h4>
        <div class="admin-list">
          ${disabled
            .map(
              (alias) => `
            <div class="admin-row">
              <div class="admin-info">
                <div class="admin-name">${escapeHtml(alias)}</div>
              </div>
              <div class="admin-actions">
                <button class="secondary restore-btn" data-alias="${escapeHtml(alias)}" type="button" title="恢复这条从 SSH config 自动发现的服务器">恢复</button>
              </div>
            </div>
          `,
            )
            .join("")}
        </div>
      `;
      hidden.querySelectorAll(".restore-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await restoreDiscovery(btn.dataset.alias);
        });
      });
    }
    void aliases;
  } catch (error) {
    list.innerHTML = `<div class="empty error-text">${escapeHtml(error.message)}</div>`;
  }
}

async function saveAlias(serverId, alias) {
  const message = $("adminServerMessage");
  message.textContent = "正在保存名称...";
  message.classList.remove("error");
  try {
    await fetchJson(
      `/api/admin/servers/${encodeURIComponent(serverId)}/alias`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alias }),
      },
    );
    await loadAdminServers();
    await loadStatus(true);
    message.textContent = "名称已保存。";
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function removeServer(serverId) {
  const message = $("adminServerMessage");
  message.textContent = "正在处理...";
  message.classList.remove("error");
  try {
    await fetchJson(`/api/admin/servers/${encodeURIComponent(serverId)}`, {
      method: "DELETE",
    });
    await loadAdminServers();
    await loadStatus(true);
    message.textContent = "已更新服务器列表。";
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function restoreDiscovery(alias) {
  const message = $("adminServerMessage");
  message.textContent = "正在恢复...";
  message.classList.remove("error");
  try {
    await fetchJson(`/api/admin/discovery/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alias }),
    });
    await loadAdminServers();
    await loadStatus(true);
    message.textContent = "已恢复。";
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function checkServerConnection(serverId) {
  const message = $("adminServerMessage");
  state.ui.adminCheckBusy[serverId] = true;
  message.textContent = "正在检查连接...";
  message.classList.remove("error");
  try {
    const payload = await fetchJson(`/api/admin/servers/${encodeURIComponent(serverId)}/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    state.ui.adminChecks[serverId] = payload;
    message.textContent = payload.ok ? "检查完成。" : "检查完成，存在缺失项。";
    await loadStatus(true);
    renderServers();
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  } finally {
    delete state.ui.adminCheckBusy[serverId];
    await loadAdminServers();
  }
}

async function addServer(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = $("addServerMessage");
  const data = Object.fromEntries(new FormData(form).entries());
  data.mode = "ssh";
  message.textContent = "正在保存...";
  message.classList.remove("error");
  try {
    let payload;
    if (editingServerId) {
      payload = await fetchJson(
        `/api/admin/servers/${encodeURIComponent(editingServerId)}/edit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      );
      message.textContent = `已更新：${payload.server.name}`;
    } else {
      payload = await fetchJson("/api/admin/servers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      message.textContent = `已添加：${payload.server.name}`;
    }
    cancelEdit();
    await loadAdminServers();
    await loadStatus(true);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

window.selectServer = selectServer;
window.selectWorkspace = selectWorkspace;
window.selectGpu = selectGpu;
window.showLog = showLog;
window.showTmux = showTmux;
window.showProcessCommand = showProcessCommand;
window.stopProcess = stopProcess;
window.stopJob = stopJob;
window.retryJob = retryJob;
window.copyJob = copyJob;
window.loadJobIntoExecution = loadJobIntoExecution;
window.reorderQueuedJob = reorderQueuedJob;
window.openTerminal = openTerminal;
window.activateOutputTab = activateOutputTab;
window.closeOutputTab = closeOutputTab;
window.advanceWorkspaceAutomation = advanceWorkspaceAutomation;

restoreStoredUiState();
bindEvents();
loadStatus(true);
startLogPoller();
