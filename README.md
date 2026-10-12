# RelayGraph

RelayGraph 是一个本地研究与运维工作台，把 GPU 监控、远程任务、文件传输和 Agent 工作流串成可执行、可追溯的研究流程。

已有能力包括本地/SSH 机器监控、tmux 任务与空闲 GPU 队列、rsync 传输、浏览器终端、工作区、模板与能力配置、Agent 执行、SSE 反馈、运行摘要回放和导出。异步工作流的等待/恢复与交付验证仍有已登记缺口；当前状态见[代码审查](docs/current-audit.md)，不要把模块存在当成整个闭环已验收。

后端是 Python，HTTP 服务使用标准库；前端是静态 HTML/CSS/JavaScript，没有 Node 构建步骤。密钥加密依赖 cryptography，工作流推进使用 LangGraph core + SQLite。当前新工作流只接入单 Job 的持久受理、等待和重启核对，Job → Agent 仍待下一片；LiteLLM 仍为待验证候选。

## 本地启动

适用环境为 Linux/WSL，Python 目标为 3.11+。当前已在独立 Python 3.12.3、3.13.5 环境完成安装、依赖检查、正式 HTTP 启动和 SQLite 检查点跨进程读写；3.11 尚未运行验证。

在仓库根目录创建并激活隔离环境，再安装唯一运行依赖清单（下面的环境放在仓库外）：

```bash
python3 -m venv ../relaygraph-venv
source ../relaygraph-venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m total_control.server --host 127.0.0.1 --port 8765
```

Debian/Ubuntu 如果提示缺少 ensurepip，需要先安装与 Python 版本匹配的 venv 系统包（例如 python3-venv 或 python3.12-venv）。本轮 3.12 遇到该问题，先在隔离环境补齐 pip 后才完成安装，未把环境准备算成产品恢复能力。无对应平台 wheel 时，依赖的源码安装可能还需要编译工具；当前没有验证离线安装。

[requirements.txt](requirements.txt) 固定一起验证过的三个直接依赖版本：cryptography 49.0.0、LangGraph 1.2.7、SQLite saver 3.1.1。间接依赖由 pip 解析，这不是全依赖锁文件。N03B2a 解析出 44 个运行包；LangGraph 带入 LangChain core、LangSmith 等依赖。项目没有启用外部 tracing，但上游可受 LANGSMITH_/LANGCHAIN_ 环境变量或 tracing 上下文影响；验证显式关闭 tracing。pytest、Playwright、PyTorch 和 LiteLLM 均不属于当前运行清单，开发时按切片另行准备。

浏览器打开 `http://127.0.0.1:8765`。系统工具按功能准备：本地任务需要 tmux；远程连接需要 ssh，任务目标主机需要 tmux；传输需要相应端的 rsync；GPU 监控需要目标主机的 nvidia-smi。CPU 路径不要求 GPU 工具。默认监听本机，现有接口可执行命令，不应直接开放为公共服务。

## 配置与数据

默认配置是 `config/servers.toml`，包含本地服务器和 SSH config 发现。个人主机、别名和路径放忽略的覆盖文件：

```bash
cp config/user_servers.example.toml config/user_servers.toml
```

config/ 默认只跟踪公开默认和 *.example.toml 模板，本机配置与凭据文件均忽略。N01 样机使用 config/workflow-poc.example.toml 对应的 workflow-poc.local.toml，无需 API key。

优先使用 SSH key。确需密码时按 `config/secrets.example.toml` 创建本地 `config/secrets.toml`，不提交或分享真实文件。

公开起始目录是 `data/agent_definitions.json`、`data/tool_definitions.json`、`data/workflow_templates.json`。运行 Job、工作区、Provider Profile、日志与主密钥属于本地数据并被 Git 忽略。Provider key 加密落盘，主密钥位于 `data/.master_key`；运行数据不能随公共归档发布。执行账本默认使用 data/execution.sqlite3；可在 config/ 主机配置文件的 [app] 设置 execution_db_path（相对路径从该配置所在目录计算），数据库和锁文件不提交。上述 Provider 私密配置与主密钥仍是现有 data/ 布局，统一归入 config/ 的兼容迁移安排在 N00E；本轮没有搬动或读取真实密钥。

## 开发与文档

完整文档入口为 [docs/README.md](docs/README.md)，由三个部分组成：

1. [稳定的项目目标、需求与组件契约](docs/project-spec.md)。
2. [当前问题与逐文件审查](docs/current-audit.md)。
3. [下一阶段计划、技术复用与消融验证](docs/next-stage-plan.md)。

开发规则见 [AGENTS.md](AGENTS.md)。N02/N03A 已接完整计划和稳定提交身份，N03B1/J1a/J1b 修正实际计划门禁及可选环境，B2a 补齐依赖。N03B2b 已接入单 Job 的 LangGraph 持久等待；旧同步推进器已删除。新工作流 POST 保存计划后返回，jobs 可以暂为空，调度器随后提交和核对；重复请求保留同一个 run/Job。当前多节点和 Agent 工作流会明确拒绝，可先选择只含一个 Job 的前缀；之前两节点 shell 链是旧路径的历史验收，当前不会回退运行。旧 N02 记录仍能查询/核对，未提交的旧节点不自动重放。

检查点位于领域账本旁的 `<账本文件主名>-checkpoints.sqlite3`，沿用 config/ 中的 execution_db_path 确定目录，不新增配置源。损坏检查点会阻塞协调器并保留文件；已提交外部任务仍由原 Job 服务管理。单 Job 检查点丢失时可用冻结计划和稳定回执重新核对；无回执的未知提交不盲目重提，也不宣称任意外部进程 exactly-once。唯一下一片是 N03B2c：Job 成功后让一个 Agent 消费本次结果。Agent 控制、报告正文、远程文件、GPU 占用和传输继续分片推进。

用户已清理并忽略 tests/；后续按功能切片生成本地验证，不上传脚本、执行结果或产物。dev_work/ 保存忽略的调查、PoC、浏览器/远程/Provider 验证。当前 N01 本地样机的运行方式见第三部分 2.4；正式应用仍按上面的启动命令运行。

代码按 total_control/、web/ 分层，前端通过 window.X 与静态脚本装配。

## License

MIT，见 [LICENSE](LICENSE)。引入的第三方代码和技能按其对应版本/目录的许可另行核对。
