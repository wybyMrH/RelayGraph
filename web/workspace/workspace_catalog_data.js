(function () {
  "use strict";

  const WORKSPACE_PROJECT_TABS = ["home", "project", "workflow", "chat", "agents", "tools", "model", "runs"];
  const WORKSPACE_MANAGE_TABS = ["templates", "agents", "tools", "ai", "runs", "inspect"];

  const WORKSPACE_JOB_EXECUTABLE_KINDS = new Set([
    "repo.clone",
    "path.resolve",
    "env.prepare",
    "gpu.allocate",
    "run.command",
    "artifact.collect",
  ]);

  const WORKSPACE_AGENT_EXECUTABLE_KINDS = new Set([
    "repo.inspect",
    "env.infer",
    "dataset.find",
    "eval.report",
    "research.search",
    "path.resolve",
    "artifact.collect",
  ]);

  const WORKSPACE_SHELL_DISCOVERY_KINDS = new Set([
    "repo.inspect",
    "dataset.find",
    "env.infer",
    "eval.report",
    "path.resolve",
    "artifact.collect",
  ]);

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
            { value: "", label: "未选择" },
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
            { value: "", label: "未选择" },
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
            { value: "", label: "未选择" },
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
      label: "主机执行计划",
      category: "host",
      capability: "execute",
      description: "通过受控 job 队列执行目标主机检查或命令，保留日志和停止入口。",
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
      label: "GPU 候选",
      category: "gpu",
      capability: "read",
      description: "给出 GPU 调度候选；真正占用由工作流任务处理。",
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
      label: "任务提交包",
      category: "run",
      capability: "execute",
      description: "通过受控 job 队列提交运行任务，并同步 workspace run 记录。",
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

  const CATALOG_VALUES = {
    WORKSPACE_PROJECT_TABS,
    WORKSPACE_MANAGE_TABS,
    WORKSPACE_JOB_EXECUTABLE_KINDS: Array.from(WORKSPACE_JOB_EXECUTABLE_KINDS),
    WORKSPACE_AGENT_EXECUTABLE_KINDS: Array.from(WORKSPACE_AGENT_EXECUTABLE_KINDS),
    WORKSPACE_SHELL_DISCOVERY_KINDS: Array.from(WORKSPACE_SHELL_DISCOVERY_KINDS),
    WORKSPACE_NODE_TYPES,
    WORKSPACE_TOOL_CATALOG,
    DEFAULT_WORKSPACE_AGENTS,
    SOURCE_AGENT_ROLE_IDS,
  };

  function deepClone(value, fallback) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch {
      return fallback;
    }
  }

  function clone(name, fallback) {
    if (!Object.prototype.hasOwnProperty.call(CATALOG_VALUES, name)) return fallback;
    return deepClone(CATALOG_VALUES[name], fallback);
  }

  window.WorkspaceCatalogData = {
    clone,
    catalogValue: clone,
    WORKSPACE_PROJECT_TABS: clone("WORKSPACE_PROJECT_TABS", []),
    WORKSPACE_MANAGE_TABS: clone("WORKSPACE_MANAGE_TABS", []),
    WORKSPACE_JOB_EXECUTABLE_KINDS: clone("WORKSPACE_JOB_EXECUTABLE_KINDS", []),
    WORKSPACE_AGENT_EXECUTABLE_KINDS: clone("WORKSPACE_AGENT_EXECUTABLE_KINDS", []),
    WORKSPACE_SHELL_DISCOVERY_KINDS: clone("WORKSPACE_SHELL_DISCOVERY_KINDS", []),
    WORKSPACE_NODE_TYPES: clone("WORKSPACE_NODE_TYPES", {}),
    WORKSPACE_TOOL_CATALOG: clone("WORKSPACE_TOOL_CATALOG", []),
    DEFAULT_WORKSPACE_AGENTS: clone("DEFAULT_WORKSPACE_AGENTS", []),
    SOURCE_AGENT_ROLE_IDS: clone("SOURCE_AGENT_ROLE_IDS", { repo: [], paper: [], idea: [] }),
  };
})();
