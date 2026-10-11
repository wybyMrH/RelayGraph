# 第三部分：下一阶段计划、技术复用与消融验证

计划日期：2026-10-12。需求来自[第一部分](project-spec.md)，问题编号来自[第二部分](current-audit.md)。已完成文档收敛、N00C 清理、N00D 原有改动整合、N01 本地选型验证与 N02 完整计划/提交记录；其余切片仍待实施，不能把“写入计划”标成已完成。

## 1. 下一阶段的目标与执行方式

下一阶段只围绕一件事：**让顺序 Agent + Job 链真正等待、恢复、准确结束，并留下可取的报告。** 先保证本地 CPU 最小链，再接同样契约的 SSH、GPU 和 Transfer。这样可以把调度错误与机器/供应商问题分开。

不做“整仓重构再补功能”，也不把 22 个问题塞进一个 PR。每次选择下表一个切片，交付一个可观察行为与对应删除/保留判断；不得顺手加入后续切片。对规模较大的切片，再按列出的子边界拆开。

N00C/N00D 已完成清理和原有改动整合；**N01 已完成本机验证并选定 LangGraph core + SQLite checkpointer**，结论与接入边界见 2.4。N02 已接入现有工作流入口，下一轮只执行 **N03：本地 Job → Agent 等待与恢复**。N00A 依赖声明、N00B 文件浏览容错可以独立交付；现有 G07 没有因测试被移出远端而消失，不混进工作流迁移。测试脚本和执行结果按用户要求只保存在本地。

核心推进在 N02–N04；N05–N07 补控制与交付；N08–N10 扩到目标机器、GPU 与传输。每一步都沿用同一计划/attempt/外部任务接口，不另造并行路径。

## 2. 技术复用评估

### 2.1 已查阅的开源与官方资料

检索日期：2026-10-11，使用 Firecrawl 查询 GitHub 与官方文档。资料说明上游能力，不构成本仓库集成成功证明。最初审查只评估候选；随后 N01 在隔离虚拟环境安装并验证 LangGraph 与 SQLite checkpointer，正式应用尚未引入这些依赖。LiteLLM 仍未做 PoC。正式采用时锁定实际版本、对应许可与兼容 Python 范围；不以仓库星数代替验证。

| 候选 | 能解决什么 | 不能替项目解决什么 | 本阶段判断 |
| --- | --- | --- | --- |
| [LangGraph](https://github.com/langchain-ai/langgraph) core + 持久 checkpointer | 图状态、等待/恢复、检查点、节点失败处理 | SSH/tmux Job 的事实核对、GPU 预留、外部副作用幂等、artifact 实物校验 | N01 已完成本地评估，选为下一阶段唯一推进器；领域账本已在 N02 接入，LangGraph 推进在 N03 接入 |
| [LiteLLM](https://github.com/BerriAI/litellm) Python SDK | 多供应商消息/响应规范、流式调用、受限重试/fallback | 项目 Profile 与密钥生命周期、工具权限、Agent 总预算、工作流状态 | N12 验证后替换 llm_client 协议层；先 SDK，不上完整 Proxy 平台 |
| SQLite / Python sqlite3 | 本地事务、计划/attempt/外部引用、查询、迁移 | 外部进程与数据库之间的天然 exactly-once | 执行状态的轻量持久方案；配合幂等键/核对，不把所有 JSON 一次改成库 |
| 现有 SSH、tmux、rsync、nvidia-smi | 远程连接、长任务、同步、GPU 采样 | 工作流生命周期与统一证据 | 继续复用；统一适配器和结果，不重写工具协议 |
| TypedDict/dataclass；必要时 Pydantic | 领域结构与输入验证 | 业务完成语义、跨步骤正确性 | 先扩已有类型；若引入框架已有该依赖，再评估用在 API 边界，不为每个 dict 全面建模 |
| pytest + 浏览器自动化 | 领域回归、模拟故障、实际 UI 流程 | 证明未实际运行的 SSH/Provider | 继续用 pytest 做按切片生成的本地检查；浏览器 smoke 按核心场景组织，开发依赖与运行依赖分开 |
| [OpenAI skills catalog](https://github.com/openai/skills) | 复用开发流程、资料查询、浏览器等可选技能 | 应用里的工具适配器或产品权限 | 先选具体任务所需 skill，检查其 SKILL.md 与逐技能许可，再安装；不是默认装整套 |

LangGraph [持久化文档](https://docs.langchain.com/oss/python/langgraph/persistence)明确区分 checkpointer 与长期 store；内存 saver 不提供跨进程恢复，SQLite 等持久 saver 的具体包/API 要在 PoC 核实。[故障容错文档](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)包含 retry、timeout、error handler，也有版本前提（所查文档对节点 timeout/error handler 要求 >=1.2）。不能只复制示例后承诺旧版具备同样能力。

LiteLLM [可靠调用文档](https://docs.litellm.ai/docs/completion/reliable_completions)说明 SDK 重试和 fallback；所查 SDK fallback 不自动为所有尝试提供总时间预算。因此 Agent deadline 必须留在领域层，所有网络尝试消费同一预算。[一个上游 Proxy Retry-After 问题](https://github.com/BerriAI/litellm/issues/21553)只能说明某个版本/部署曾有兼容问题，不能外推为所有版本都坏；应转成候选版本的 429 测试。

OpenAI skills 目录的许可按具体 skill 的 LICENSE.txt 检查；本轮只评估技能复用方向，没有授权自动安装或让应用执行技能脚本。当前已安装技能也先检查适用范围，避免为了流程再新增一个任务管理框架。

### 2.2 暂不引入的体系

Temporal、Celery/Redis、Ray、完整 LiteLLM Proxy、Kubernetes、多租户身份/计费系统不进入当前计划：现有目标是单机控制少量 SSH 主机，暂没有需要这些基础设施的证据。未来若出现多控制节点、严格跨服务调度或统一团队网关，再单独评估。这些候选本轮没有深入版本/许可审查。

可视编辑先维持顺序链；不因画布难维护直接改 React/React Flow 或扩成自由 DAG。只有执行语义稳定、明确需要分支/汇合和稳定布局后，再评估成熟画布组件及其前端迁移成本。

### 2.3 两项选型的通过条件

**LangGraph PoC 的验收范围**使用 fake Job registry 与小型持久存储，验证 submit → wait → external completion → resume → report；等待期间退出/重启；重复完成通知；提交后保存前崩溃的核对；前置失败阻止下游。关键指标是外部 Job 启动次数、已恢复步骤、状态/证据一致性，而不是代码能 import。

必须明确 LangGraph thread/checkpoint 与项目 run/attempt 的映射；UI run 是可查询领域投影，不能另有一套自行推进的 FSM。框架重放可能再次进入节点，外部提交放在幂等适配器后。项目仍保留一套 Job 队列，LangGraph 不负责直接执行 shell。

对照方案是单一 SQLite 状态机，采用同一测试场景、相同契约。**不要为了对照写完整第二个产品实现**：最小验证即可。如果 LangGraph 能清晰替代 workflow_runner 的推进/恢复，且依赖和调试成本可接受，采用它；否则记录未通过的具体证据和保留轻量方案的原因。决策只保留一个生产路径。

**LiteLLM PoC** 使用受控 OpenAI-compatible endpoint，加上可用时的真实 Profile，核对普通/流式、无密钥本地模型、Anthropic 格式、工具参数、结构化输出、usage、429/5xx、部分流失败、deadline、取消与脱敏。真实供应商缺配置时对应格子是未验证，不准拿 fake endpoint 全绿代替。

替换后 LLMClient 可以暂做薄兼容门面，但旧请求/解析实现必须退出主路径。禁止在 Agent、SDK 和 HTTP adapter 三层同时重试。自动跨供应商 fallback 默认关闭，启用时明确目标、数据边界和预算。

### 2.4 N01 决策：LangGraph core + 本地 SQLite 持久检查点

**决定**：后续工作流推进采用 LangGraph core；本机使用 SqliteSaver。保留项目现有 Job 生命周期与队列，通过幂等适配器连接协调器。N01 样机不被正式服务导入，没有改变公开 API、前端、生产任务启动或现有 Provider 密钥存储。

对照的轻量 SQLite 状态机也能完成本轮最小链。LangGraph 并没有让两节点样机代码更少，且增加了 SDK、序列化、Pydantic 等间接依赖。采用它的依据是第一部分已明确需要多步骤/Agent 子任务等待、节点失败恢复和可追溯推进，原生节点检查点与 interrupt/resume 可以复用，避免在领域代码再长期维护通用恢复游标。SQLite 对照只留在本地作为取舍依据，不做第二条生产路径，也不据此宣称轻量方案无法实现这些能力。

**实际核对的组件**：LangGraph 1.2.7、langgraph-checkpoint-sqlite 3.1.1、langgraph-checkpoint 4.2.0，使用同步 invoke 与 durability="sync"；本机 Python 3.13.5、SQLite 3.45.3。前三项发行元数据的许可为 MIT、Python 要求 >=3.10；项目仍以 3.11+ 为目标，3.11/3.12 尚未做本轮运行验证。SQLite saver 还引入 sqlite-vec 等间接依赖，具体版本清单和许可元数据保存在本地锁文件；正式应用依赖归 N00A 统一声明，不能用 PoC 环境代替部署清单。

本地样机已运行一个固定 CPU 命令写 result.json，再由确定性 Agent 替身读取当前任务结果生成 Fixture 汇总；不使用 GPU、SSH、模型密钥或外部 tracing。任务服务和工作流使用不同 SQLite 文件，工作流动作可跨新进程继续。验证涵盖等待/恢复、通知重复或丢失、提交/汇总后的硬退出、任务失败/停止、身份冲突、旧输出拒绝与损坏检查点。原始执行结果、脚本与截图不进入远端；可复现实验保存在本地 dev_work/n01/。

**需要保留的事实边界**：

- SqliteSaver 保存的是图状态和节点恢复位置，不是 SSH/tmux 的执行事实。暂停节点恢复时会从节点开头重新进入，暂停前不得藏不可重放副作用。
- fake registry 的唯一键与事务才提供样机的提交去重。N02 已在现有 Job 队列外加持久提交意图/键和核对适配器，普通 create_job 仍创建新 ID；N03 必须经该适配器提交，不能直接把 create_job 塞进可重放节点。
- 同一 run 的 resume 必须串行化。N02 采用单机操作系统文件锁，进程死亡释放，不依赖长调用期间可能过期的租约；N03 必须沿用锁。当前 JSON Job 队列仍只支持一个服务进程，不能外推为多实例服务已经安全。
- 节点检查点与外部提交之间没有共享事务。先保存提交意图，再提交/核对；事实不明时停在 reconciling，禁止盲目重试。
- 样机的 Agent 是可幂等缓存的确定性替身，不证明真实模型请求只调用一次，也不替代 N05 总预算、N07 正文保存和交付校验。
- 本地 CPU worker 是串行验证工具，不是生产守护器；worker 本身崩溃后需核对 running 任务，不能凭工作流恢复再次启动它。

**配置与运行方式**：可分享的参数模板为 config/workflow-poc.example.toml，本机修改放 config/workflow-poc.local.toml。只接受 engine、state_dir、worker_delay_seconds；状态目录限制在 dev_work/n01/，不读个人 data/。本轮没有需要填写的 API key。config/ 默认忽略本地配置与凭据，只允许公开模板和 servers.toml 入库。现有 data/ 中的加密 Provider key 与主密钥尚未迁移；统一到 config/ 的兼容迁移列为 N00E，不能在这里宣称已经完成。

本机使用命令如下（脚本和锁文件为本地交付，不随 Git 分发）：

```bash
# 本地环境已准备好；重新创建时使用本地 requirements.lock.txt 安装。
dev_work/n01/.venv/bin/python dev_work/n01/cli.py demo
# 分步动作：start → work → resume → inspect；均可在新进程执行。
dev_work/n01/.venv/bin/python dev_work/n01/cli.py --run manual start
```

本地锁文件目前针对本机 Linux/WSL + Python 3.13；正式采用时补齐受支持环境验证。demo 默认每次生成新的 run_id，实际执行新的 CPU 任务；分步恢复使用原来的 run_id，不能改变原始计划或输入。PoC 的 summary 是流程验证产物，正式工作台的报告正文仍由 N07 交付。

**领域接口与责任**（N02 已落地计划/attempt/意图；Coordinator 与检查点接入待 N03）：

| 契约 | 输入/保存内容 | 输出与限制 |
| --- | --- | --- |
| RunPlan | run_id、workspace_id、package/version、不可变计划及 hash、全部 step_id、engine_version | 首个副作用前计划可查；进度分母始终为完整计划 |
| StepAttempt | run_id、step_id、attempt_id、输入来源、状态、错误、输出引用 | 重试追加 attempt，不覆盖旧记录；输出绑定本次 attempt |
| SubmissionIntent | 稳定 submit_key、payload_hash、目标主机/执行方式、attempt_id | 先持久记录意图；相同键不同载荷是冲突，不能静默复用 |
| JobAdapter | submit(intent)、lookup(submit_key)、observe(job_ref) | 返回外部引用或需核对状态；queued/running 不产生完成输出 |
| Coordinator | start(run_id)、resume(run_id, wakeup_hint)、读取权威 checkpoint | thread_id 对应 run_id；checkpoint_id 仅是内部恢复版本，不拿来当新的任务幂等键 |
| RunProjection | 完整计划/attempt 账本、checkpoint、已核对外部事实 | 对外 run/step/revision；只读投影，不自行推进或启动任务 |

LangGraph checkpoint 是推进位置的权威；领域 SQLite 记录计划、attempt、提交意图、外部引用与证据；二者按职责分工，JSON/UI/SSE 不再各自推进。完成通知只唤醒协调器，结果仍由 JobAdapter 核对。持久副作用键至少包含 run_id/step_id/attempt_id/operation，重放复用本次键，显式重试才产生新 attempt。

**旧代码去向**：

| 旧入口/职责 | 决定与退出条件 |
| --- | --- |
| orchestration/workflow_runner.py 的同步 for 循环与 pending_agent_runtime | 生产接入前暂保留；N03 切换顺序执行主入口时退出对应推进路径，不能和新引擎推进同一个 run |
| state/workspaces/workflow.py | 保留 HTTP/状态服务入口、门禁、执行包快照；逐步转为提交完整计划与唤醒协调器 |
| state/jobs_pkg 与 scheduler.py | 保留唯一 Job 生命周期/资源队列；增加稳定提交键核对接口，完成事实交给协调器消费 |
| cockpit/fsm.py 与 automation/advance.py | 保留操作建议/就绪投影；不能因 UI 按钮或 next_action 独立推进已经托管的 run |
| state/workspaces/runs.py 与 execution/run_* | 保留查询、兼容响应和证据展示边界；运行事实改读权威账本，历史 JSON 兼容读取不充当新游标 |
| 本地 SQLite 对照状态机 | 只保留实验依据；不进入 total_control/ 或生产依赖 |

N02 已落实完整计划、attempt/提交账本和领域存储接口，公开响应保持原字段并追加证据；N03 接入等待/恢复主路径并退出旧推进职责。任何阶段都不允许同一个 run 被两套推进器同时驱动。N01 选型完成不等于 G01/G02/G09 已修复。

### 2.5 N02：完整计划和提交记录已接入

本切片解决的是“执行前把要做的事记全，提交出了问题也不丢现场”。它覆盖 POST /api/workspaces/{id}/run 的新工作流；普通单 Job、单节点入口、Agent 工具子任务和历史 run 仍沿原有生命周期，不宣称全部迁库。生产代码仍只有现有顺序 runner；本轮没有引入 LangGraph 运行依赖，图的推进/等待接入留到 N03。

**实际数据流**：

1. 现有就绪检查通过后，保存完整 RunPlan：所有 step_id、顺序、执行方式、节点/工作区/执行包快照、schema_version、engine_version 和 plan_hash。新记录为 legacy-sequence/n02，表示当前仍由旧顺序 runner 提交。
2. 尚未执行的步骤显示 pending，显式跳过显示 skipped。开始节点时追加 StepAttempt，记录计划 hash、输入映射和前一个计划节点引用；不能把前一次 run 的结果当成本次已产出。实际输入值与输出引用的串联仍由 N03/N04 完成。
3. Job 进入队列前保存 SubmissionIntent，键由 run/step/attempt/job 构成。相同键不同载荷报冲突；状态经过 prepared → submitting → submitted，结果不明进入 reconciling，并保留外部引用。
4. 继续调用原 create_job。队列锁内先保存 jobs.json，再让调度器看到 Job；写盘失败就移除尚未公开的内存条目。适配器只接受排队提交，不允许在持久回执前立即启动 tmux。
5. 成功后绑定 Job ID。重启或重复请求只根据稳定提交键查询已有回执，并检查工作区、run、step、attempt 和载荷 hash；能查到就补齐引用，查不到就保留待核对，禁止自动创建第二个 Job。没有假设 SQLite 与 jobs.json/tmux 共享事务。
6. 每步结果写自己的 attempt，异常写当前失败与 run 错误，不用单条失败记录覆盖之前的步骤。查询从完整计划、attempt/意图和现有 Job 事实形成投影，分母不再随着已提交步骤缩小。

账本使用 Python 自带 sqlite3，默认 data/execution.sqlite3，schema 为 1；可在 config/ 的主机配置文件 [app] 设置 execution_db_path，相对路径以该配置文件所在目录为基准，修改该路径需要重启服务，普通主机配置 reload 不迁移账本。数据库、sidecar、锁文件均为本机运行数据。无新增模型密钥、GPU 或 SSH 要求，真实 Provider 与主密钥仍按 N00E 单独迁移。

**请求与查询契约**：启动请求可携带 request_id（1–128 位字母、数字、下划线、点、冒号或短横线）。同一工作区、同一 request_id 与相同请求参数返回原 run 的当前状态，不重新执行，也不会因工作区后来修改而改写冻结计划；同一键换参数返回 HTTP 409。不提供 request_id 则是一次新运行，不能承诺自动识别两次点击属于同一个意图。当前浏览器尚未持久保存该键，N03 接入口时补齐客户端的重发语义，避免只在测试里具备请求身份。

原有 workspace/jobs/run/run_id/execution_package 等响应字段保留；run 追加 execution_plan、plan_hash、attempts、submissions、submission_error，step 追加 step_id、attempt_id、submission_state。attempt.status 是结合当前 Job 的投影，recorded_status 是账本最后一次记录的观察；Job 终态仍以 Job 服务为事实。坏库、未知 schema、损坏计划或载荷 hash 返回明确错误；运行中的 HTTP 请求返回 503，不重建空库，不伪装为 workspace 不存在。历史 JSON run 沿原读取规则，不补造当年的计划或 attempt。

**保留和退出边界**：

- 新 run 的计划/attempt/提交证据以 SQLite 为准；JSON runs 保留兼容投影与已有事件，既不单独推进，也不覆盖领域记录。相同结果不反复写库，同一提交回执的查验共用一个函数；没有复制 Job 生命周期或引入第二套轻量状态机。
- 暂时保护账本 run 及其 Job 回执，JSON 的默认条数截断和手工裁剪不能无声丢掉它们。N14 要做有 tombstone/回执保留的事务归档；当前不是可无限增长的最终保留方案。已删除工作区的孤立账本也归该保留切片核对。
- 单机锁是推进互斥基础，不是分布式锁；本轮验证 Linux/WSL，Windows 分支未验证。一个服务负责 JSON Job 队列，不支持多个服务共享数据目录同时调度。
- 存储接口支持追加 retry attempt，但当前没有新增工作流重试按钮/API。失败请求再次使用相同 request_id 仍返回失败现场；N03/N04 定义恢复和重试，不能靠删记录或换幂等键把重放伪装成恢复。
- N02 的中断 run 可以查询/核对，但不会自行续交后续节点。N03 必须明确旧 engine_version 的兼容策略；旧 Agent 副作用不明时不能自动套上图从头重放。N02 完成不等于 G01/G02/G09 全部关闭。

**过程检查带来的下一步约束**：完整 CPU 工作流目前仍被固定 Starter Chain 约束，要求配置 dataset.find/env.infer/gpu.allocate；dataset.find 还附带探测默认数据根。这些额外节点与扫描是现有产品限制，不能作为“最小 Job → Agent 链已经可用”的证明。N03 必须按实际选中的计划和依赖校验；CPU 链无需伪造 GPU 分配或无关数据步骤。N02 只修复了本轮确实阻断 CPU 提交的执行包 GPU=auto / 实际任务 GPU=none 不一致，未扩大到 GPU 预留体系。

本轮正常验收走真实 HTTP 服务、现有门禁、调度器和本机 tmux，明确选择 job 执行模式和已有真实 Python 环境；不使用 force/allow_incomplete_execution_package，不手填任务终态。异常/崩溃注入另在隔离进程验证。原始脚本、超时调查、命令输出和结果只留 dev_work/n02/；不把特殊辅助或曾经失败的尝试藏在最终通过声明后面。

## 3. 按功能划分的实施切片

表中“依赖”是功能依赖；N00A/N00B 可以独立进行，不代表需要和其他切片同一提交。P1 工作优先于体验优化。

| 切片 | 单次目标 | 问题/需求 | 依赖 | 验收产物 |
| --- | --- | --- | --- | --- |
| N00C · 清理基线（已完成） | 收敛文档，移除遮蔽文件/无消费者方法/相同取值副本 | G10/G16/G22；R05/R09/R14 | 已完成本切片的调用核对与消融验证 | 三部分与 AGENTS；取值等价对照；隔离提交验证，详见第二部分；未关闭原功能缺口 |
| N00D · 原有改动整合（已完成） | 整合任务停止、失败日志、SSH 端口和输出呈现修复 | R07/R08/R11/R12 | 用户授权整合已有改动 | 修正权限/截断边界，复用原组件；测试脚本和执行结果仅本地保存 |
| N00A · 部署基线 | 最小依赖声明与干净环境启动 | G08；R14 | 无 | 安装清单、启动验证，文档与真实依赖一致 |
| N00E · 凭据配置归位 | 把 Provider 私密配置与主密钥归入 config，并兼容旧数据 | G09；R13 | 独立迁移，不阻塞无密钥 PoC | 不丢现有密钥；路径/加密与历史兼容明确；仅模板入库 |
| N00B · 浏览根容错 | 一块坏盘不阻断其他目录 | G07；R04 | 无 | 模拟 stat/iterdir 失败测试与正常浏览 |
| N01 · 推进器选型（已完成） | LangGraph core + SQLite 持久检查点；明确领域接口和替换边界 | G01/G02/G09；R06 | 本地评估已完成 | 决策见 2.4；样机与结果仅本地，生产缺口仍开放 |
| N02 · 完整计划与提交记录（已完成） | 运行开始前留计划，中途异常不丢历史 | G03/G09；R06/R11 | N01 | 已接入现有工作流入口；契约与限制见 2.5；等待恢复仍待 N03 |
| N03 · Job → Agent | 本地 CPU Job 成功后才运行报告 Agent | G01；R06/R09 | N02 | 等待/失败/重启/重复通知测试，一条真实本地链 |
| N04 · Agent 子任务续跑 | 子任务完成后恢复后续 Agent | G02；R06 | N03 | child Job 后续跑、正确分母、幂等与恢复 |
| N05 · Agent 预算与取消 | 超时/取消后无新副作用、无假成功 | G04；R09 | N02 | 单调 deadline、剩余预算与明确取消结果 |
| N06 · 聊天统一结果 | 普通/流式入口共用执行结果与编排 | G05；R09/R12 | N05 | 失败/取消/离线来源正确，删除重复编排 |
| N07 · 报告正文与验证 | 完整保存本地报告并区分交付状态 | G06；R10 | N02 | >4000 字正文可读，缺失文件不呈现已交付 |
| N08 · 主机文件适配 | Agent 在明确目标主机读文件 | G12；R04 | N07 的 artifact 引用契约 | local/SSH 同名路径隔离、有界读取与失败分类 |
| N09 · GPU 原子占用 | 多个 Job 不抢同一内部预留 | G13；R01/R07 | N02 | claim/release/recovery、CPU 旁路与竞争测试 |
| N10 · 传输交接 | 已有 rsync 作为顺序工作流前置 | G14；R08 | N03/N08 | 单源传输 → 目标验证 → Job，带归属与失败传播 |
| N11 · 引用规则收敛 | 在 N00C 共用取值基础上统一静态/运行时引用规则 | G10；R05/R09 | N03/N04 | 等价输入矩阵通过，删除重复解析函数 |
| N11B · 工具能力如实标注 | 建议、读取、提交与模拟在目录和执行包中明确区分 | G11；R03 | N02 的执行方式契约 | 无适配器不进入可执行包，GPU 建议不显示为已绑定 |
| N12 · Provider SDK | 用已验证 SDK 替代自维护协议层 | G21；R03/R09 | N05/N06 | LiteLLM 对照结果与统一 adapter，旧协议实现退出 |
| N13 · 一个 UI 控制器 | 先提取 run 控制器，不混改服务器/transfer | G15/G17；R12 | 核心 API/revision 稳定 | app.js 薄装配、同一状态权威与浏览器行为等价 |
| N14 · 摘要/离线证据 | 在摘要导出之外提供按需实物证据包 | G20；R11 | N07/N08 | manifest 完整性、缺失标记、保留与导出冲突验证 |
| N15 · 专用 preset 消融 | 用通用任务计划保留有效研究样例 | G18；R02/R14 | task-plan 行为对照 | 等价 Job 计划或保留差异理由；再退役无用入口 |
| N16 · API 边界 | 逐路由族统一输入与错误封装 | G19；R12 | 相关契约已测试 | 一次只迁移一个族，旧前端兼容，大小/类型/布尔正确 |
| N17 · 配置恢复 | 识别损坏 JSON/丢失主密钥，防止默认空值覆盖 | G09；R13 | N00A | 保留坏文件、明确错误与恢复动作；先一个存储族，不全量迁库 |

N16 可在所改路由上提前实施必要的输入修正，但不允许顺带重写整个 HTTP 服务。N00C 仅是本次已授权、已核对的删除基线；剩余 G16 门面、G17 派生投影、G22 测试归属仍随对应功能切片完成，不扩成无边界的全仓重构。

N11B 只修正能力目录与消费者的真实语义，不要求把每个建议型工具都补成复杂执行器；必要的标签修正可在受影响的前序切片中先完成。N17 遇到阻断启动的数据损坏时优先处理，普通情况下在执行状态存储稳定后再按族收敛。

## 4. 近期切片的具体交接要求

### N01：唯一推进器的最小验证（已完成，决策见 2.4）

本切片范围只允许新增本地 PoC、对照记录和选型结论；不修改公开 API、业务 Job 启动方式、模板编辑或前端。用同一组执行契约记录两方案结果，测重启前后 Job 启动计数。第三方包的额外依赖、持久 saver、许可、最低版本、升级方式和调试入口一并记录。

完成条件是一个明确采用/暂缓决定、领域接口草案、旧 runner/FSM 的职责去向和 N02 范围。失败也可以是有效结论，但必须指出具体阻碍，不以“不想引入依赖”代替比较。没有结论就不开始长期维护另一个 runner。

### N02：运行计划和提交证据（已完成，见 2.5）

沿 2.4 的 RunPlan/StepAttempt/SubmissionIntent 契约，围绕 run 的创建/提交生命周期修改 orchestration/types、workflow 状态服务和执行存储适配。先让整条计划可查，StepAttempt 可追加，任务提交有幂等键与意图记录；提交失败保留已产生步骤。历史 JSON 只提供兼容读取/一次性导入边界，不重写模板和 Provider 存储。

测试重点：空计划拒绝；完整计划先于副作用；第二步失败后第一步还在；进度分母不缩小；重发启动命令不重复建 Job；坏记录明确报错不覆盖为空。这个切片不实现所有等待类型，只给 N03/N04 稳定接口。已建立单机 run 锁、计划 hash 冲突和提交意图/外部引用核对约束；N03 复用这些接口，不能另造第二个提交账本。

### N03：本地 Job 完成后的 Agent

只处理一个 Job → 一个 Agent 的链。首先去掉固定 Starter Chain 对该最小链的无关要求，按实际计划/依赖校验；不通过 force 或伪造 GPU 节点验收。协调器收到成功事实后读取当前 attempt 的输出并推进；queued/running 保持 waiting；failed/stopped 阻止下游。以一个本地 CPU 命令写结果，再由 fake Provider 汇总，避免 GPU 和网络混淆。

复用 N02 的账本/提交适配器/run 锁，接入 LangGraph 后退出新 run 的同步 for 推进职责；明确 N02 历史/中断 run 的兼容，不自动重放旧 Agent。客户端启动/重发要携带稳定 request_id。测试必须包含等待期间重启、重复完成、事件丢失后快照恢复、同名旧输出拒绝和不关闭门禁的两节点入口。停止条件：这条链正常和故障路径均可解释；不趁机做 DAG、批量 Agent、自动研究循环或 UI 重画。

### N04：子任务恢复

复用 N03 的等待引用，不为 Agent child Job 再写一套 polling loop。持久记录子引用及后续游标；子任务失败/停止反馈到父 attempt。先实现 child Job，再把同样契约推广到 child run，后者可另一个小提交。

完成条件：父 Agent → child Job → 后续 Agent 全链只执行一次，100% 只在全部必需计划步骤终结后出现；取消父/子关系明确；服务重启不丢后续计划。

### N05–N07：控制和交付分别交付

N05 只改生命周期预算/取消及网络预算接口；不同时替换供应商。N06 在 N05 结果类型稳定后统一聊天编排，并移除同步/流式重复逻辑。N07 只实现本地正文存储和验证；先通过 4001 字符、空报告、无权限、已有路径冲突与缺失引用，不同时开发完整归档下载。

这三个切片各自有独立测试和回退边界。它们最终共同证明“任务结束”与“研究交付完成”的差别，但不需要一次合并。

## 5. 每轮实现后的消融与去重

“消融”在这里是有证据地拿掉一条旧路径，看看核心行为是否还成立，不是凭直觉删文件。

每个切片输出一张短记录：

| 项目 | 必须写清 |
| --- | --- |
| 被替代职责 | 具体旧函数/入口及调用者，替代它的新唯一实现 |
| 固定输入与故障 | 哪些正常/失败场景在删减前后保持一致 |
| 差异 | 状态、输出、事件、Job 启动次数、证据或 UI 行为哪里变了 |
| 删除决定 | 删除/保留/延期；保留要给调用者和退出条件 |
| 验证 | 实际执行命令与结果；未跑原因，不能把 skipped 写 pass |

N00C 已消除相同的 context_ref 取值函数；尚未统一引用规则。剩余候选：引用前缀/缺失语义；chat 两条执行编排；无调用者 fallback；Provider 自维护协议；preset 专用分支；重复有效配置解析。不是所有 fallback 都冗余：服务未加载与离线草稿仍可能需要回退。不能把不同 UI 投影、媒体查询或 compatibility alias 当成重复业务逻辑。

公共组件只提取已明确重复、语义相同的部分。至少列出当前消费者；抽出来后原消费者必须接入，旧代码退出。不要新增一个 util 后继续保留各处复制逻辑，也不要因为将来“可能复用”就提前造通用引擎。

## 6. 测试和旧资料的收敛方案

用户在 42960ac 清理提交中删除了远端 24 个历史测试文件，并将 tests/ 忽略；旧本地 smoke 也已清理。后续按功能实际生成需要的本地验证，脚本与执行结果不提交，不把“没有测试文件”写成回归通过。需要查旧安全断言时可从 Git 历史读取，不能把原有失败用例的删除当成问题解决。

确定性检查按 workflow-lifecycle、agent-lifecycle、provider-routing、artifact-delivery 等行为组织，共用隔离数据/假主机/受控 Provider。真实浏览器、SSH、GPU 和模型只在对应切片验证；未配置记未验证。N01 的样机和场景检查保存在本地 dev_work/n01/，不恢复一套固定 Phase 脚本到远端。

旧正式文档的目标/功能/架构/开发/阶段/测试/路线信息已经归入三份主文档和 AGENTS.md。旧“Phase 完成”、历史 agent id、旧 web/app.js 命令等不再作为当前规则。原提交历史可由 Git 找回；本地旧计划的有效需求已提取后删除，复现报告作为本地证据保留但不参与规则优先级。

## 7. 一个切片的完成门槛

1. 对应需求与 G 问题明确，变更只涉及一个可验收行为。
2. 正常、等待、失败、取消/重启等相关边界经过实际验证；不要求无关的大规模测试。
3. API/SSE/历史数据适配可解释，已提交副作用不会因重试或事件重放而重复。
4. 新实现成为该职责的唯一权威，消融决定与旧路径去向已记录。
5. 第二部分对应文件/问题状态更新；第三部分只勾选真正通过的验收项，第一部分不跟着实现细节反复改写。

到 N04 后先验收本地混合链；到 N07 后验收正文交付；到 N10 后验收 SSH/GPU/传输全链。只有真实机器可用时才运行对应 smoke，并保留主机绑定、run/package、事件、产物与导出证据。下一阶段完成这些闭环后，再决定是否值得开展 DAG 编辑和更大型多工作区能力。
