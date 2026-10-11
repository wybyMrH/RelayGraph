# 第二部分：现状、问题与逐文件审查

审查日期：2026-10-11。目标基线为[第一部分](project-spec.md)，解决顺序为[第三部分](next-stage-plan.md)。本文随代码变化更新，不能作为永久完成证明。

## 1. 范围、证据等级与结论

本次提交维护 309 个正式代码文件的台账：166 个后端 Python、117 个前端 JavaScript、HTML/CSS 各 1 个、24 个测试文件；另审查 1 个用户本地新增测试和 40 个本地 smoke 脚本的职责与验收价值，并核对 3 份公开 registry JSON、3 份配置和 pytest.ini。忽略运行数据、密钥、缓存、第三方/生成产物，不读取 Provider 密钥。

本次包含审查前就已存在的未提交修改：paths、checks、transfer、Job execution、scheduler、app.js、index.html、styles.css、scheduler 测试和未跟踪的 tmux/transfer 测试。没有撤销或改写这些内容，也没有将它们纳入本次清理提交。问题复现基于审查工作区；提交验证另用暂存区的隔离副本，避免用户改动掩盖清理回归。台账行号取审查时源码，未纳入的原有改动可能带来少量行号偏差。

逐文件审查通过源码文本、Python AST、函数/调用职责、导入、状态/副作用分支和前端公开接口进行静态核对；关键路径另外做内存/临时目录复现。**静态覆盖全部文件不等于逐分支动态验证，不等于读完十万行后保证没有遗漏。** 每个文件在后面的台账单列；未发现独立问题的文件不会被硬凑成缺陷。

证据等级：E1=本轮运行/隔离复现；E2=具体源码路径确认；E3=设计风险，需后续实验；E4=需求能力尚未完成。类别为能力缺口、冗余/职责重叠、伪成功或语义误导、可靠性/安全风险。一个问题可以有多个类别。

已有成果：监控、tmux Job、资源等待、rsync、浏览器终端、工作区与配置中心、受控 runtime 工具、输出校验、SSE、执行包、run/日志保留、模板诊断与迁移都有真实代码和测试。最大问题是“这些组件各自可用”尚未充分等于“异步工作流完整且可恢复”。

优先级：P1=可导致错误执行、漏执行、证据丢失或控制失效；P2=正常操作受阻、结果误导、重要设计缺口；P3=后续体验/维护改进。未发现需紧急停用全项目的 P0 证据。

## 2. 问题登记与解决方向

<a id="g01"></a>
### G01 · P1 · Job → Agent 无完成屏障

- 对齐 R06/R09，类别：能力缺口、执行风险，证据 E1。
- workflow_runner.py:89–106、147–171 提交 Job 后继续遍历，后续 Agent 没有等待 previous_job_id；Job 的本次输出也没有在此进入 previous_step_output。
- 复现 run.command → eval.report(Agent)：Job 返回 queued 时报告 Agent 已被调用，previous_output=None。输入门禁可能改为阻塞，但仍不是等待后续跑。
- 方案：协调器持久记录 waiting_on，在任务成功且本次输出可用后推进；失败/停止传播。不要往 HTTP 请求里加轮询 sleep。验收 Job → Agent、Job → Agent → Job，确认报告读取本次结果。

<a id="g02"></a>
### G02 · P1 · 子任务后续跑缺失，完整工作流可被算成部分完成

- 对齐 R06，类别：能力缺口、伪完成，证据 E1/E2。
- workflow_runner.py:93–95 遇到 pending_agent_runtime 后的 Agent 直接 break；WorkflowMixin 不消费 stopped_early，也不保存剩余节点游标。run_records.py:20–55 只以已有 steps 计算终态与分母。
- 两个 Agent 的复现只留下第一个 step；子任务结束后按现有计算得到 done、1/1、100%，第二个 Agent 未运行。现有测试只证明阻止提前执行，未证明完成后的恢复。
- 方案：先冻结完整计划，再为每个节点记录等待/尝试；完成事件恢复推进。分别处理子 Job 与子 run，重复通知不重复启动，服务重启能恢复。

<a id="g03"></a>
### G03 · P1 · 提交异常替换已记录步骤

- 对齐 R06/R07/R11，类别：证据丢失风险，证据 E2。
- workflow.py:465–484 用 steps=[failed_step] 更新失败；runs.py:269 起对非空 incoming_steps 整表替换。之前已逐步保存的 Job/Agent 记录会被覆盖。
- 方案：追加提交失败 attempt/事件，不覆盖先前步骤；保留未提交计划与已提交任务引用，明确其继续/停止策略。验收第二个任务创建失败时，第一个任务与历史仍在。不能靠异常后删除所有任务“清理现场”。

<a id="g04"></a>
### G04 · P1 · deadline/cancel 在最后一次调用后可失效

- 对齐 R09，类别：控制风险，证据 E1。
- agent_executor.py:303–407 只在循环开头检查；Provider 返回后可直接 success 或继续工具副作用。llm_client 使用独立网络超时，未消费 Agent 剩余预算。
- 复现总预算 10ms，假 Provider 30ms 后返回并设置取消信号，结果 success=True、timed_out=False、cancelled=False。
- 方案：单调 deadline，调用前后/工具前/成功前检查；重试与 fallback 共用剩余预算。区分取消请求和真正终止；已提交 Job 按策略处理，不宣称必定可立即中断网络或远程进程。

<a id="g05"></a>
### G05 · P2 · 聊天失败语义不一致，同步/流式执行存在重复编排

- 对齐 R09/R12，类别：伪成功、冗余，证据 E1/E2。
- chat.py:778–889 以失败文字正常返回，完成方法仍写 completed/error="" 并发布 chat.message.completed；隔离复现 execution.success=False 与上述状态同时出现。
- append_workspace_chat 与 _workspace_chat_reply 都包含路由选择、工具构造、Agent callbacks 等相似逻辑；其中两组事件回调的归一化 AST 完全相同。不是简单按方法同名就认定重复。
- 方案：一个聊天执行服务返回统一 ChatResult，普通/流式入口只改变传输；依据成功/失败/取消/离线规则来源组装消息。合并后删除旧编排，不保留两个带默认降级的实现。

<a id="g06"></a>
### G06 · P1 · 长报告正文丢失，交付判断不足以证明实物存在

- 对齐 R10/R11，类别：能力缺口、语义误导，证据 E1/E2。
- workspace_mutations.py:78–143 不写文件，content >4000 时仅保留 240 字符 summary；dispatcher 的 report.write 仍返回 written。4001 字符临时目录复现：无文件、无正文。
- run_delivery.py 根据 artifact 的 exists/status 等声明判断 observed；report_ready 可由报告条目存在推导，不能单独作为实际文件可取的证明。此处未做真实远程文件验收。
- 方案：ArtifactStore 保存正文或受控文件，返回可验证引用；区分 declared/written/verified；正文超过限额显式拒绝或另存。执行结束和交付完整度独立展示。

<a id="g07"></a>
### G07 · P2 · 失效挂载点导致文件浏览整体失败

- 对齐 R04/R08，类别：可靠性风险，证据 E1。
- utils.py:179–205 在 /mnt 枚举时 child.is_dir() 未隔离 OSError；本机 /mnt/g 的 Errno 19 使安全测试失败。
- 方案：逐根目录/条目容错，区分 unavailable 与不存在；测试模拟坏挂载，保证其他路径可浏览。复用同一根目录发现逻辑，不在前端绕过失败。

<a id="g08"></a>
### G08 · P2 · 运行依赖缺声明，安装文档曾与事实冲突

- 对齐 R14，类别：部署缺口，证据 E1/E2。
- secrets_crypto.py:17 顶层导入 cryptography，启动链直接依赖；隔离第三方 site-packages 后 import server 报 ModuleNotFoundError。无 requirements/pyproject 声明。
- 本轮已修正文档“纯标准库/零运行依赖”的说法；**依赖清单与干净环境安装验证仍未实现**，不能因改文档关闭问题。
- 方案：声明最小运行/测试依赖和 Python 范围，固定可重复安装方式；系统能力缺失可诊断。引入 LangGraph/LiteLLM 时统一维护依赖，不各自藏一套安装说明。

<a id="g09"></a>
### G09 · P1 · 缺少可靠执行检查点与提交一致性

- 对齐 R06/R11/R13，类别：恢复能力缺口、持久化风险，证据 E2/E3。
- persistence.py 保存 jobs/workspaces 等独立 JSON；utils.write_json 可原子替换单文件，但不能对多文件与 tmux 副作用提供事务。read_json 在 JSON 损坏时返回默认值，可能把损坏误当首次初始化。agent_runtime.py 取消注册仅在内存。
- 方案：选择单一执行状态权威（优先评估 LangGraph 持久 checkpoint + 薄领域存储），保存计划/attempt/幂等键；提交前记意图，提交后登记外部引用，重启核对。配置目录仍可 JSON。坏文件隔离与版本迁移另设小切片，不能一次迁移全部历史。

<a id="g10"></a>
### G10 · P2 · 同一输入引用和默认目录多处维护

- 对齐 R02/R05/R09/R14，类别：冗余、语义漂移，证据 E2。
- 原 orchestration/input_mapping.py 的 context_ref_value 与 automation/contracts_pkg/context.py 的 workspace_context_ref_value 归一化 AST 相同；N00C 已合并到 context_refs.py，原导入名保留，135 组取值输入前后等价。仅完成底层字典/列表取值去重，运行/静态引用规则仍分别维护；前端 node_catalog/defaults/catalog_data 的目录副本也仍存在，G10 未关闭。
- 方案：统一纯引用解析器，静态校验与运行时校验共享规则但传入不同上下文；由后端提供版本化目录，前端只留必要无服务草稿默认。先锁定空值、前向引用、历史输出与 $prev 语义，再替换调用者；不把不同职责的校验一律合并。

<a id="g11"></a>
### G11 · P2 · 工具注册、建议、读取与真实执行混在一个实现标签下

- 对齐 R03，类别：能力缺口、语义误导，证据 E2。
- repo.search 汇集 query/roots/hints，未实际搜索仓库；log.read 返回最新日志入口而非正文；notify.user 返回载荷，schedule.plan 是 dry_run。gpu.allocate 的实际 callback 返回 plan_only=True、persisted=False，并不写绑定；旧本地文档“已绑定”不准确。
- AgentExecutor 缺少 tool_executor 时返回 [Simulated]，若当生产路径使用可能让模型把模拟当真实。自定义工具 CRUD 也不等于自动产生适配器。
- 方案：能力目录明确执行级别与真实 adapter_id；无适配器只能配置/诊断，不能进入可执行包。建议型工具保留并如实命名，不必为每个名字补大型实现；验证调用方确实需要正文/通知后再开发。

<a id="g12"></a>
### G12 · P1 · Agent 文件发现工具缺统一远程读取语义

- 对齐 R04/R10，类别：能力缺口、错误证据风险，证据 E2。
- tools/workspace_executor_pkg/read_tools.py、helpers.py、discovery.py 用本机 pathlib 扫描/读取；浏览器文件工具已有 SSH 路径，二者不是同一适配入口。远程工作区可能读不到文件或读到本机同名目录。
- _read_text_file 先 read_text 整个文件再截取，响应限额并非 I/O/内存限额。
- 方案：HostFileAdapter 统一本地/SSH stat/list/read/probe；强制 host_id；有界读取、禁止敏感路径，失败返回 unavailable/permission 而非伪造 missing。复用已有远程探针，不复制一套 shell 脚本。

<a id="g13"></a>
### G13 · P1 · GPU 选择缺本服务内的原子预留

- 对齐 R01/R07，类别：资源竞争风险，证据 E2/E3。
- jobs_pkg/execution.py.find_gpu 只读最近 statuses；scheduler.py 一轮遍历多个 queued Job，启动一个任务后没有在选择器中扣除预留。启动幂等测试只保护同一个 Job，不保护多个 Job 选择同一 GPU。
- 可由源码确认竞争窗口，尚未用真实 GPU 制造 OOM；外部使用者竞争也不能靠内部锁完全解决。
- 方案：主机/GPU 范围的原子 claim 与释放、过期/重启核对、采样陈旧限制。CPU 不走 GPU claim。验收两个 Job 同时竞争一张卡，只有获准者启动，不能用固定 sleep 假装预留。

<a id="g14"></a>
### G14 · P2 · 文件传输未形成工作流与产物的统一交接

- 对齐 R08，类别：能力缺口，证据 E2/E4。
- rsync、冲突检查和 transfer UI 已实现；现有节点类型/runner 未提供完整的 Transfer → Job 依赖和传后 ArtifactRecord 语义。
- 方案：把已有传输执行映射成带 run/step/attempt 的 Job/TransferRecord，输出目标 host/path 验证引用；仅增加一个顺序节点适配，不另建传输队列。先覆盖单源本地↔远程，不一次扩成任意多端同步。

<a id="g15"></a>
### G15 · P2 · 前端组合根与样式叠加过重

- 对齐 R12/R14，类别：维护风险、重复实现候选，证据 E2/E3。
- app.js 26,570 行，styles.css 23,037 行；不少 helper 有 fallback，与 app 中默认/包装路径并存。CSS 某些 selector 出现 5–6 次，但媒体查询与有意覆盖不应直接删除。
- 方案：按职责迁移一个控制器（run/服务器/transfer 分开），装配处明确必须的 helper；通过调用覆盖与缺失 helper 实验判断 fallback 是否必要。样式按界面责任归并，视觉验证后删除已覆盖规则，不做“同 selector 自动去重”。

<a id="g16"></a>
### G16 · P2 · 包/目录门面与星号导入隐藏真实依赖

- 对齐 R14，类别：职责重叠候选，证据 E2/E3。
- constants.py、infra/shell.py、workspace/normalize.py 等仍是有调用者的兼容门面；多个 _deps.py 和 __init__.py 大量转导出。compat.py 还支持门面覆盖，部分测试依赖旧导入位置。N00C 删除了被同名 automation/ 包遮蔽的 workspace/automation.py；find_spec 确认正常导入始终选择包，仓库没有按文件路径加载它的消费者。其他门面未凭文件短而删除，G16 未关闭。
- 方案：先查实际调用与 monkeypatch，再改成显式导入/协议；有调用者的兼容入口保留，清晰标注范围；无调用者且契约验证通过才删除。不能因为只剩两行就认定是死代码。

<a id="g17"></a>
### G17 · P2 · 多层就绪、报告、调度与部署派生存在重叠

- 对齐 R05/R06/R14，类别：重复设计候选，证据 E2/E3。
- cockpit/fsm 与 automation/advance、preflight、report、reproduction、deployment 各生成状态/门禁/下一步信息。部分是不同展示投影，不应因相似字段全删；但同一失败可能在多个结构分别派生，增加契约维护成本。
- 方案：一个 ReadinessResult 和执行决策权威，其他视图只投影；对同一输入做删减前后等价比较。deployment 若不服务当前研究闭环，降为可选交付类型，不扩成通用部署平台。

<a id="g18"></a>
### G18 · P2 · 研究领域特定 preset 留在核心代码

- 对齐 R02/R14，类别：通用目标不匹配、冗余候选，证据 E2。
- preset_matrix.py 硬编码 LEVIR/CLCD/SYSU、特定模型组合与显存估计；jobs_pkg/presets.py 为它保留专门路径，同时已有通用 task_plans。
- 方案：比较 preset 与 task-plan 的等价能力；有效案例转为公开样例模板/参数矩阵，保留历史 Job 可读性。确认无人使用的专用入口才退役；不能把既有研究用户的配置直接删除。

<a id="g19"></a>
### G19 · P2 · HTTP 与参数边界不统一

- 对齐 R12/R13，类别：契约风险，证据 E2/E3。
- Handler.read_body 未限制请求体大小，也未统一校验 JSON 对象；一些路由按 startswith/endswith + split 索引提取资源，Provider 单资源已有更严格 helper。多个地方 bool("false") 会变成 True。
- 方案：公共输入验证/布尔解析/路径段匹配，统一错误 code 与对象关联；逐路由切片迁移，保持响应封装。默认本地部署不等于可以省略基本参数边界；本轮没有做公网攻击测试。

<a id="g20"></a>
### G20 · P2 · 摘要回放不等于完整离线交付，截断语义需要统一

- 对齐 R11，类别：能力缺口，证据 E2/E4。
- run_export 最多保留 12 份日志、48 个 artifact、12 个 report，日志尾 80 行/12,000 bytes；delta 为 summary-only。已有 manifest 暴露不少 limit/截断信息，这些保护应保留。
- 方案：继续保留轻量摘要导出，同时增加按需证据包；集中管理日志/child refs/产物限额，逐项标记未包含原因。先保全文和验证报告，再做离线包；不是立即保存所有 token。

<a id="g21"></a>
### G21 · P2 · Provider 协议与健康/合并逻辑自维护成本偏高

- 对齐 R03/R09/R14，类别：重复维护、适配风险，证据 E2/E3。
- llm_client.py 自维护 OpenAI/Anthropic 请求、流解析和响应；profile catalog、health、route health 与 saved-version merge/base dedupe 各有规则。当前路径可用，不能称为全部伪实现。
- 方案：先以 LiteLLM SDK 对照验证替换协议层；保留项目 Profile/密钥与路由领域模型，统一有效配置解析。重复重试和 fallback 只能有一个控制层，搜索适配器不强行塞入 LLM SDK。

<a id="g22"></a>
### G22 · P2 · 测试与历史文档按阶段堆叠，核心缺口未形成验收门禁

- 对齐全部需求，类别：验证缺口、维护冗余，证据 E1/E2。
- 现有阶段测试包含大量有效安全与契约断言；文件长或 phase 名称不是删除理由。缺 G01–G06 的关键交接/失败验证，局部成功被用来代表整链完成。40 个本地 smoke 有真实验收价值，但依赖私有环境，部分与单次 helper 抽取绑定。
- 方案：按行为迁移测试所有权，复用隔离 fixtures；重复测试只有在证明同一输入/行为/失败模式已被覆盖后删除。helper 装配测试可精简，但路径、脱敏、幂等、保留、退出码与执行转移必须保留。正式文档本轮收敛为三部分，旧本地计划退出规则来源。

## 3. 本轮验证与尚未验证的事

审查工作区基线（包含用户本地修改及新增测试）的 `python -m pytest -q`：255 passed、1 failed、80 warnings，约 52.78 秒；唯一失败是 G07 的失效挂载。Python compileall 通过；117 个 JS 全部 node --check 通过。HTML 的 117 个脚本引用均有对应文件、没有漏加载的正式 JS，组合根最后加载。语法/引用通过不证明 UI 流程正确。

N00C 的实际提交版本在隔离目录验证：`python -m compileall -q total_control` 通过；`python -m pytest -q` 为 **252 passed、1 failed（42.84 秒）**。少 3 个通过用例是因为用户新增 tmux/transfer 测试未纳入提交，没有删除测试。唯一失败仍是同一文件浏览测试在 `/mnt/g` 遇到 Errno 19；恢复清理前代码后单独执行该用例也同样失败，确认是原有 G07。取值函数 135 组前后等价对照通过，automation 的 82 个公开导出名称保持一致。此轮没有前端变更，不重跑浏览器/远程 smoke。

隔离复现涵盖 G01/G02/G04/G05/G06；G03 为源码确认。未调用真实 SSH、GPU、联网 Provider 或浏览器端到端；旧 smoke 记录只说明历史有过验证，不能当成本次通过。文档整理不重跑网络 smoke，也不因环境未配置删除它。

### N00C：本次有证据的清理

| 清理对象 | 删除/收敛依据 | 保留行为与后续边界 |
| --- | --- | --- |
| 七份旧正式文档 | 信息已归入三部分、README、AGENTS；映射见文档索引 | Git 保留历史，不留重复规则源 |
| workspace/automation.py | 与 automation/ 同名，Python 正常导入选择包；无文件路径加载者 | 保留包的全部公开导出和调用路径 |
| LLMClient.simple_chat | 全仓代码、测试、smoke、文档只有定义；是 chat 的未使用包装 | Agent/Provider 继续调用 chat/chat_stream，不改变协议 |
| TerminalsMixin.terminal_list | 全仓只有定义；HTTP 路由没有会话列表入口 | 保留现有会话打开、读写、信号和关闭 |
| 两份 context_ref_value | 函数 AST 一致，字典/列表/缺失/空路径等 135 组输入结果和对象引用等价 | 唯一实现放 context_refs.py；旧导入名是别名，静态/运行时规则不在此轮改写 |
| 正式测试、40 个本地 smoke、CSS 和其他门面 | 尚无等价替代或无消费者的充分证据 | 保留；不能把未执行的 UI/远程场景当成重复覆盖 |

本切片只清理无消费者或完全相同的实现，不代表完成 G10/G16，也不提前实施 N01–N17。未删除失败测试，未调整失败断言或跳过条件。

## 4. 逐文件台账的读法

下面每行对应一个实际文件，列出需求、职责与输入处理输出、检查结论和解决路径。`保留`表示本轮未发现该文件的独立缺陷，不保证所有分支正确；`关联`表示参与某个问题的修补或验收，不表示文件自身一定有 bug。同一问题的详细方案只在 G 登记维护，避免在几百行表格重复且漂移。

证据栏采用源码中的具体符号和行号；对纯数据、CSS/HTML、转导出入口检查对应边界。文件的责任不由行数决定，框架替换也不能跳过这些接口与测试。

<!-- FILE_AUDIT_START -->

### total_control

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/__init__.py) · 5 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [agent_executor.py](../total_control/agent_executor.py) · 480 | R03/R09；Agent 输入/模型/工具/预算 → ReAct 循环与结果封装 → AgentExecution | 问题/修补关联 [G04](#g04)、[G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `_tool_side_effect:31`；`_metadata_value:39` |
| [agent_runtime.py](../total_control/agent_runtime.py) · 49 | R09；execution_id/取消请求 → 进程内注册与信号 → active/cancel 检查 | 问题/修补关联 [G04](#g04)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `register_agent_cancel:20`；`cancel_agent_run:30` |
| [compat.py](../total_control/compat.py) · 21 | R14；公开门面名/默认实现 → 查询 override → 兼容调用入口 | 问题/修补关联 [G16](#g16)；按登记方案处理，不另建平行服务。 | `public_api_override:7`；`public_api_value:17` |
| [config.py](../total_control/config.py) · 329 | R01/R13；TOML/SSH config/本地覆盖 → 解析合并 → ServerConfig/AppConfig | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `ServerConfig:18`；`AppConfig:40` |
| [constants.py](../total_control/constants.py) · 2 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context_refs.py](../total_control/context_refs.py) · 18 | R05/R09；数据和点分路径 → 字典键/列表下标查找 → 原值或 None | N00C 唯一纯取值内核；执行映射与上下文投影均已接入；不承担引用前缀或就绪规则。 | `context_ref_value:8` |
| [events.py](../total_control/events.py) · 207 | R12；业务事件/游标 → 有界队列、gap 与 SSE 编码 → 实时通知 | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `EventBroker:12`；`sse_encode:135` |
| [handler.py](../total_control/handler.py) · 170 | R12/R13；HTTP 请求/静态路径 → 分发、JSON 与文件响应 → 浏览器接口 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `Handler:22`；`run:142` |
| [llm_client.py](../total_control/llm_client.py) · 578 | R03/R09；Profile/消息 → 供应商请求、流解析 → LLMResponse | N00C 已删除无调用者的 simple_chat 包装；协议维护与预算问题仍按 [G04](#g04)/[G21](#g21) 解决。 | `LLMResponse:17`；`ChatMessage:37` |
| [path_safety.py](../total_control/path_safety.py) · 37 | R04/R13；原始/解析路径 → 敏感目录规则 → 拒绝原因 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `sensitive_path_block_reason:19`；`sensitive_path_block_reason_for_path:30` |
| [preset_matrix.py](../total_control/preset_matrix.py) · 90 | R02/R07；数据集选项 → 硬编码实验组合排序 → preset 参数矩阵 | 问题/修补关联 [G18](#g18)；按登记方案处理，不另建平行服务。 | `PresetExperiment:12`；`dataset_rank:26` |
| [secrets_crypto.py](../total_control/secrets_crypto.py) · 68 | R13/R14；明文或密文 → Fernet/主密钥处理 → 加密存储或内存明文 | 问题/修补关联 [G08](#g08)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `_load_or_create_master_key:26`；`_fernet_instance:42` |
| [server.py](../total_control/server.py) · 35 | R14；CLI/兼容导入 → 转接 Handler 和 main → 服务入口 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | 文件整体/公开入口 |
| [terminal.py](../total_control/terminal.py) · 82 | R07/R14；server_id/终端输入 → CLI PTY/SSH 交互与本地 shell → 交互式终端退出状态 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `interactive_ssh:16`；`main:63` |
| [utils.py](../total_control/utils.py) · 1389 | R04/R11/R13；路径/文件/日志/公开对象 → 浏览、预览、存储与脱敏等混合处理 → 公共 payload | 问题/修补关联 [G07](#g07)、[G09](#g09)、[G12](#g12)、[G19](#g19)；按登记方案处理，不另建平行服务。 | `now_iso:97`；`iso_at:100` |

### total_control/constants_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/constants_pkg/__init__.py) · 10 | R02/R03/R05；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [paths.py](../total_control/constants_pkg/paths.py) · 59 | R02/R03/R05；环境变量/项目根 → 定义配置、数据、日志位置 → 路径常量 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | 文件整体/公开入口 |
| [provider_catalog.py](../total_control/constants_pkg/provider_catalog.py) · 185 | R02/R03/R05；静态厂商描述 → 按 id 查询 → Provider 预设 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `provider_catalog_by_id:183` |
| [workspace_contracts.py](../total_control/constants_pkg/workspace_contracts.py) · 444 | R02/R03/R05；节点类型 → 定义 I/O、默认绑定与能力 → 契约目录 | 问题/修补关联 [G10](#g10)、[G14](#g14)；按登记方案处理，不另建平行服务。 | 文件整体/公开入口 |
| [workspace_nodes.py](../total_control/constants_pkg/workspace_nodes.py) · 202 | R02/R03/R05；源类型/节点类型 → 节点库与流程默认 → 节点描述 | 问题/修补关联 [G10](#g10)、[G14](#g14)；按登记方案处理，不另建平行服务。 | 文件整体/公开入口 |

### total_control/http_api

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/http_api/__init__.py) · 10 | R12；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [delete_routes.py](../total_control/http_api/delete_routes.py) · 55 | R12；资源删除路径 → 匹配并调用删除 → 结果响应 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `handle_delete:9` |
| [get_routes.py](../total_control/http_api/get_routes.py) · 460 | R12；查询路径/参数 → 调用状态服务、回放/下载/SSE → 查询响应 | 问题/修补关联 [G19](#g19)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `_workspace_jobs_snapshot:14`；`_workspace_stream_snapshot_event:27` |
| [path_utils.py](../total_control/http_api/path_utils.py) · 14 | R12；API 路径/前缀 → 单资源路径段匹配 → id 或空 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `single_segment_path_id:6` |
| [post_routes.py](../total_control/http_api/post_routes.py) · 413 | R12；创建/执行请求 → 参数提取与服务调用 → 创建/命令响应 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `_public_job_response:13`；`handle_post:29` |
| [put_routes.py](../total_control/http_api/put_routes.py) · 44 | R12；资源更新请求 → 匹配资源与调用更新 → 更新响应 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `handle_put:9` |

### total_control/infra

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/infra/__init__.py) · 5 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [checks.py](../total_control/infra/checks.py) · 218 | R01/R07；主机/检查或停止请求 → 连接、能力、进程所有者检查 → 诊断或停止结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `run_server_checks:21`；`build_process_stop_script:90` |
| [shell.py](../total_control/infra/shell.py) · 2 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [web_terminal.py](../total_control/infra/web_terminal.py) · 160 | R07；主机/输入/信号 → PTY 启动与读写 → 终端缓冲和状态 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `set_terminal_winsize:19`；`WebTerminal:26` |

### total_control/infra/shell_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/infra/shell_pkg/__init__.py) · 159 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [command.py](../total_control/infra/shell_pkg/command.py) · 94 | R01/R07；命令/超时/密码模式 → subprocess 或 PTY 执行 → CompletedProcess | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_run_command_impl:23`；`run_command:32` |
| [gpu.py](../total_control/infra/shell_pkg/gpu.py) · 327 | R01/R07；主机列表/探测配置 → nvidia-smi 与连接采集 → GPU 状态快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `gpu_activity_state:28`；`_collect_server_impl:51` |
| [host.py](../total_control/infra/shell_pkg/host.py) · 486 | R01/R07；系统文件/远程探针 → CPU/内存/磁盘/网络解析 → 主机资源 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `parse_csv_lines:24`；`parse_meminfo:32` |
| [jobs.py](../total_control/infra/shell_pkg/jobs.py) · 175 | R01/R07；任务参数/环境 → 生成激活和退出标记脚本 → shell Job 脚本 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `parse_smoke_peak_mib:20`；`render_task_template:35` |
| [probe.py](../total_control/infra/shell_pkg/probe.py) · 44 | R01/R07；主机检查项 → 生成/判定远程探针 → 能力检查结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `remote_check_script:23`；`server_check_ok:27` |
| [process.py](../total_control/infra/shell_pkg/process.py) · 61 | R01/R07；PID/ps 输出 → 本地或远程查进程 → 进程元信息 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `ps_lookup_local:22`；`ps_lookup_remote:28` |
| [ssh.py](../total_control/infra/shell_pkg/ssh.py) · 109 | R01/R07；ServerConfig/命令 → SSH 参数与连通性检查 → 远程命令结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_ssh_command_impl:22`；`ssh_command:29` |
| [tmux.py](../total_control/infra/shell_pkg/tmux.py) · 68 | R01/R07；会话/尺寸/任务 id → tmux 参数与日志命名 → 会话操作参数 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `tmux_new_session_args:21`；`tmux_resize_commands:35` |
| [transfer.py](../total_control/infra/shell_pkg/transfer.py) · 489 | R08；源/目标/过滤/冲突策略 → rsync、安全与冲突探测 → 传输命令/检查结果 | 问题/修补关联 [G14](#g14)；按登记方案处理，不另建平行服务。 | `rsync_endpoint_prefix:53`；`server_matches_rsync_prefix:65` |

### total_control/orchestration

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/orchestration/__init__.py) · 25 | R06/R09；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [input_mapping.py](../total_control/orchestration/input_mapping.py) · 296 | R05/R09；引用/上下文/模型输出 → 解析映射与 JSON 输出校验 → 输入值/输出证据 | N00C 改为导入唯一取值内核；前缀/缺失/历史输出规则仍关联 [G10](#g10)，未整体统一。 | `_is_mapping_ref:11`；`resolve_input_mapping_ref:16` |
| [node_runner.py](../total_control/orchestration/node_runner.py) · 211 | R06/R09；节点/执行上下文 → 选择 Agent/Job、Agent 失败校验 → StepResult | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G04](#g04)；按登记方案处理，不另建平行服务。 | `_node_handler_mode:51`；`_node_agent_id:56` |
| [types.py](../total_control/orchestration/types.py) · 72 | R06/R09；执行字段 → 类型化封装 → StepResult/ExecutionRunContext | 问题/修补关联 [G02](#g02)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `StepResult:8`；`ExecutionRunContext:59` |
| [workflow_runner.py](../total_control/orchestration/workflow_runner.py) · 209 | R06/R09；节点序列/回调 → 混合步骤提交与局部交接 → jobs/run_steps | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `WorkflowRunResult:12`；`WorkflowRunnerCallbacks:20` |
| [workspace_mutations.py](../total_control/orchestration/workspace_mutations.py) · 143 | R02/R10；节点/配置或 artifact 内容 → 修改工作区内存快照 → 配置/产物元数据 | 问题/修补关联 [G06](#g06)；按登记方案处理，不另建平行服务。 | `find_workspace_node:29`；`apply_workflow_edit:45` |

### total_control/state

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/__init__.py) · 20 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | `TotalControlState:16` |
| [_deps.py](../total_control/state/_deps.py) · 41 | R14；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [base.py](../total_control/state/base.py) · 217 | R13/R14；配置路径/JSON → 加载目录与运行状态、启动后台循环 → 应用共享状态 | 问题/修补关联 [G09](#g09)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `_dedupe_provider_profiles:6`；`_agent_definitions_need_writeback:42` |
| [files.py](../total_control/state/files.py) · 741 | R04/R11；浏览/预览/清理请求 → 本地远程文件、缓存、保留引用管理 → 文件/存储 payload | 问题/修补关联 [G07](#g07)、[G09](#g09)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `_runtime_state_run_job_ids:18`；`_runtime_state_workspace_run_closure:22` |
| [jobs.py](../total_control/state/jobs.py) · 4 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [monitoring.py](../total_control/state/monitoring.py) · 113 | R01/R12；刷新/状态查询 → 探针、工作区公开投影 → status/cockpit payload | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `MonitoringMixin:5`；`reload_config:6` |
| [persistence.py](../total_control/state/persistence.py) · 63 | R11/R13；内存 jobs/workspaces/registries → JSON 保存与密钥加密 → 本地状态文件 | 问题/修补关联 [G09](#g09)；按登记方案处理，不另建平行服务。 | `PersistenceMixin:5`；`save_jobs:6` |
| [registry.py](../total_control/state/registry.py) · 606 | R03/R05；能力/模板/Profile 请求 → CRUD 与诊断组合 → 公开 registry payload | 问题/修补关联 [G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `RegistryMixin:30`；`tool_definition_by_id:31` |
| [scheduler.py](../total_control/state/scheduler.py) · 360 | R01/R07；资源快照/队列/日志 → 监控终态、依赖与启动 → Job 更新与事件 | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G13](#g13)；按登记方案处理，不另建平行服务。 | `SchedulerMixin:8`；`_read_local_job_log_delta:9` |
| [servers.py](../total_control/state/servers.py) · 430 | R01/R07；服务器配置/所有者停止请求 → 编辑覆盖、检查与实时核对 → 服务器/停止结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `ServersMixin:5`；`list_servers_admin:6` |
| [terminals.py](../total_control/state/terminals.py) · 65 | R07；终端 id/输入/信号 → 管理 WebTerminal → 会话状态/输出 | N00C 已删除无调用者的 terminal_list；保留 open/read/write/signal/close 会话管理。 | `TerminalsMixin:5` |

### total_control/state/files_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/files_pkg/__init__.py) · 1 | R11/R13；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [remote_runtime_logs.py](../total_control/state/files_pkg/remote_runtime_logs.py) · 20 | R11/R13；远程日志失败 → 组装统一诊断 → 错误状态 payload | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `build_remote_runtime_log_status_error_payload:6` |
| [runtime_log_snapshots.py](../total_control/state/files_pkg/runtime_log_snapshots.py) · 73 | R11/R13；有界日志尾/来源 → 规范快照字段 → 保留证据快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `build_log_tail_snapshot_payload:8`；`build_remote_log_tail_payload:43` |
| [runtime_logs.py](../total_control/state/files_pkg/runtime_logs.py) · 45 | R11/R13；日志路径统计 → 组合本地远程公开条目 → 路径状态 payload | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `build_runtime_log_path_payload:6`；`merge_runtime_log_path_payloads:20` |
| [runtime_state.py](../total_control/state/files_pkg/runtime_state.py) · 60 | R11/R13；状态计数/保留量 → 统计汇总 → runtime-state payload | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `build_runtime_state_status_payload:6` |
| [runtime_state_requests.py](../total_control/state/files_pkg/runtime_state_requests.py) · 31 | R11/R13；清理请求 → 解析保留数量/dry_run → 清理参数 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `parse_runtime_state_cleanup_request:8` |
| [runtime_storage_cleanup.py](../total_control/state/files_pkg/runtime_storage_cleanup.py) · 46 | R11/R13；策略设置 → 计算清理限额与间隔 → 有效清理策略 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `build_runtime_storage_cleanup_limits:6`；`runtime_storage_cleanup_limits_enabled:24` |
| [runtime_storage_requests.py](../total_control/state/files_pkg/runtime_storage_requests.py) · 39 | R11/R13；存储清理请求 → 解析目标/标志/指定路径 → 清理参数 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `parse_runtime_storage_cleanup_request:6` |

### total_control/state/jobs_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/jobs_pkg/__init__.py) · 15 | R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | `JobsMixin:12` |
| [_deps.py](../total_control/state/jobs_pkg/_deps.py) · 12 | R07；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [crud.py](../total_control/state/jobs_pkg/crud.py) · 198 | R07；Job 请求/重试/复制/删除 → 创建记录与保留判断 → Job/关联 run | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `CrudJobsMixin:8`；`retained_workspace_run_job_ids_for_jobs:9` |
| [execution.py](../total_control/state/jobs_pkg/execution.py) · 747 | R07；Job/资源/日志请求 → GPU 选择、tmux 启停、尾部读取 → 状态与日志 | 问题/修补关联 [G13](#g13)、[G12](#g12)；按登记方案处理，不另建平行服务。 | `_read_text_file_tail:10`；`_read_text_file_chunk:36` |
| [paths.py](../total_control/state/jobs_pkg/paths.py) · 25 | R07；任务/服务器路径 → 展开远程目录变量 → 实际任务路径 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `PathsJobsMixin:8`；`_format_remote_path:9` |
| [presets.py](../total_control/state/jobs_pkg/presets.py) · 70 | R07；研究 preset 请求 → 专用计划与 Job 创建 → 实验任务列表 | 问题/修补关联 [G18](#g18)；按登记方案处理，不另建平行服务。 | `PresetsJobsMixin:8`；`preset_command:9` |
| [queue.py](../total_control/state/jobs_pkg/queue.py) · 48 | R07；Job id/移动方向 → 调整排队序号 → 队列位置 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `QueueJobsMixin:8`；`reorder_job:9` |
| [task_plans.py](../total_control/state/jobs_pkg/task_plans.py) · 237 | R07；模板/参数矩阵 → 展开、预览、排队 → 通用批量 Job | 问题/修补关联 [G18](#g18)、[G19](#g19)；按登记方案处理，不另建平行服务。 | `TaskPlansJobsMixin:8`；`task_plan_items:9` |

### total_control/state/registry_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/registry_pkg/__init__.py) · 1 | R03/R05/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [execution_overview.py](../total_control/state/registry_pkg/execution_overview.py) · 325 | R03/R05/R11；全局 run/Job/筛选 → 引用匹配与分页投影 → 只读执行概览 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `execution_overview_status_group:10`；`execution_overview_search_text:19` |
| [provider_profiles.py](../total_control/state/registry_pkg/provider_profiles.py) · 192 | R03/R05/R11；Profile/目录/保存版本 → 合并、健康与脱敏 → 有效/公开 Profile | 问题/修补关联 [G21](#g21)；按登记方案处理，不另建平行服务。 | `normalized_provider_base_url:11`；`provider_catalog_public_payload:15` |
| [provider_route_health.py](../total_control/state/registry_pkg/provider_route_health.py) · 162 | R03/R05/R11；工作区/Agent/Profile → 检查路由缺口 → 诊断问题列表 | 问题/修补关联 [G21](#g21)；按登记方案处理，不另建平行服务。 | `build_provider_route_health:8`；`add_issue:35` |
| [tool_definitions.py](../total_control/state/registry_pkg/tool_definitions.py) · 22 | R03/R05/R11；工具引用变化 → 重写 Agent allowlist → 更新后的定义 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `rewrite_agent_tool_reference:8` |
| [tool_testing.py](../total_control/state/registry_pkg/tool_testing.py) · 73 | R03/R05/R11；工具/安全测试参数 → 判定副作用并受限执行 → safe-test 结果 | 问题/修补关联 [G11](#g11)；按登记方案处理，不另建平行服务。 | `run_tool_definition_safe_test:12` |
| [workflow_templates.py](../total_control/state/registry_pkg/workflow_templates.py) · 498 | R03/R05/R11；模板节点/能力目录 → I/O、绑定、拓扑校验 → validation/preview | 问题/修补关联 [G10](#g10)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `rewrite_workflow_template_agent_reference:20`；`build_workflow_template_validation_payload:60` |

### total_control/state/workspaces

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/workspaces/__init__.py) · 19 | R05/R06/R09；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | `WorkspacesMixin:16` |
| [_deps.py](../total_control/state/workspaces/_deps.py) · 53 | R05/R06/R09；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [agent_runtime_control.py](../total_control/state/workspaces/agent_runtime_control.py) · 138 | R05/R06/R09；工具 GPU/Job 控制请求 → 候选建议或当前工作区任务控制 → planned/stopped/reordered | 问题/修补关联 [G11](#g11)、[G13](#g13)；按登记方案处理，不另建平行服务。 | `bind_workspace_tool_gpu_allocation:8`；`control_workspace_tool_job:51` |
| [agent_runtime_inputs.py](../total_control/state/workspaces/agent_runtime_inputs.py) · 100 | R05/R06/R09；映射/节点位置/历史输出 → 检查运行时引用 → refs/blockers | 问题/修补关联 [G10](#g10)、[G01](#g01)；按登记方案处理，不另建平行服务。 | `_agent_node_runtime_input_refs:10` |
| [agent_runtime_observation.py](../total_control/state/workspaces/agent_runtime_observation.py) · 156 | R05/R06/R09；子 Job/run id/观察限额 → 等待与读取受限快照 → runtime observation | 问题/修补关联 [G02](#g02)、[G04](#g04)；按登记方案处理，不另建平行服务。 | `workspace_tool_observe_options:9`；`workspace_tool_job_snapshot:35` |
| [agent_runtime_safety.py](../total_control/state/workspaces/agent_runtime_safety.py) · 327 | R05/R06/R09；命令/观测文本 → 允许诊断边界与密钥脱敏 → 拒绝原因/安全文本 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `redact_runtime_observation_text:18`；`workspace_tool_command_block_reason:29` |
| [agents.py](../total_control/state/workspaces/agents.py) · 846 | R05/R06/R09；Agent 节点/工具参数 → 有效配置、runtime Job、输出持久化 → execution/节点结果 | 问题/修补关联 [G04](#g04)、[G09](#g09)、[G11](#g11)、[G12](#g12)；按登记方案处理，不另建平行服务。 | `AgentsMixin:33`；`cancel_agent_execution:34` |
| [automation.py](../total_control/state/workspaces/automation.py) · 132 | R05/R06/R09；工作区/推进请求 → 执行后端 next_action → 更新后的实例/任务 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `AutomationMixin:7`；`advance_workspace_automation:8` |
| [chat.py](../total_control/state/workspaces/chat.py) · 902 | R09/R12；聊天/反思/流请求 → 路由、Agent、消息更新 → 聊天与事件 | 问题/修补关联 [G05](#g05)、[G04](#g04)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `ChatMixin:7`；`_chat_agent_execution_trace:33` |
| [crud.py](../total_control/state/workspaces/crud.py) · 365 | R02；工作区与迁移请求 → 创建/更新/模板差异与草稿 → 工作区快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `CrudMixin:7`；`workspace_by_id:8` |
| [debug.py](../total_control/state/workspaces/debug.py) · 181 | R05/R06/R09；Agent 定义/样例 → 组装调试上下文与有效配置 → debug/execution | 问题/修补关联 [G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `DebugMixin:7`；`debug_agent_definition:8` |
| [defaults.py](../total_control/state/workspaces/defaults.py) · 62 | R05/R06/R09；工作区/应用建议请求 → 有来源的默认与发现回填 → 配置快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `DefaultsMixin:7`；`apply_workspace_automation_defaults:8` |
| [discovery.py](../total_control/state/workspaces/discovery.py) · 162 | R05/R06/R09；工作区/发现节点 → 创建受控发现 Job 链 → 发现任务/run | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `DiscoveryMixin:7`；`run_workspace_discovery:8` |
| [nodes.py](../total_control/state/workspaces/nodes.py) · 461 | R05/R06/R09；节点/前置 Job/自动化状态 → 编译命令与依赖 → 节点 Job payload | 问题/修补关联 [G01](#g01)、[G14](#g14)；按登记方案处理，不另建平行服务。 | `NodesMixin:7`；`workspace_node_job_payload:8` |
| [runs.py](../total_control/state/workspaces/runs.py) · 643 | R05/R06/R09；run/steps/事件/Job 更新 → 注册、替换/刷新、查询 → 持久 run 与事件 | 问题/修补关联 [G02](#g02)、[G03](#g03)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `_workspace_public_payload_with_full_runs:8`；`RunsMixin:18` |
| [workflow.py](../total_control/state/workspaces/workflow.py) · 548 | R05/R06/R09；运行请求/节点快照 → 门禁、创建 run、调用 runner → 整链提交结果 | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G03](#g03)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `_workspace_env_prepare_failure_checks:9`；`_workspace_agent_execution_checks:39` |

### total_control/tools

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/tools/__init__.py) · 19 | R03/R04/R09；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [registry.py](../total_control/tools/registry.py) · 134 | R03/R04/R09；工具 id → 副作用/适配声明 → runtime 元数据 | 问题/修补关联 [G11](#g11)；按登记方案处理，不另建平行服务。 | `ToolSideEffect:7`；`tool_side_effect:93` |
| [workspace_executor.py](../total_control/tools/workspace_executor.py) · 50 | R03/R04/R09；工作区/运行依赖 → 绑定工具上下文 → 工具执行 callable | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `create_workspace_tool_executor:15`；`executor:36` |

### total_control/tools/workspace_executor_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/tools/workspace_executor_pkg/__init__.py) · 7 | R03/R04/R09；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [artifacts.py](../total_control/tools/workspace_executor_pkg/artifacts.py) · 42 | R03/R04/R09；artifact/文件请求 → 查元数据或本地读取 → artifact 内容 | 问题/修补关联 [G06](#g06)、[G12](#g12)；按登记方案处理，不另建平行服务。 | `execute_artifact_read:8` |
| [context.py](../total_control/tools/workspace_executor_pkg/context.py) · 181 | R03/R04/R09；工作区/资源/回调 → 提供发现与 runtime 访问 → workspace tool context | 问题/修补关联 [G12](#g12)、[G11](#g11)；按登记方案处理，不另建平行服务。 | `WorkspaceToolContext:12`；`node_config:20` |
| [discovery.py](../total_control/tools/workspace_executor_pkg/discovery.py) · 158 | R03/R04/R09；数据根/目录参数 → 本地扫描与敏感路径过滤 → 发现条目 | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `execute_dataset_find:9`；`execute_dir_scan:126` |
| [dispatcher.py](../total_control/tools/workspace_executor_pkg/dispatcher.py) · 395 | R03/R04/R09；tool id/arguments → 路由真实、建议或阻塞路径 → JSON observation | 问题/修补关联 [G11](#g11)、[G06](#g06)；按登记方案处理，不另建平行服务。 | `_runtime_unavailable_payload:21`；`execute_tool:36` |
| [helpers.py](../total_control/tools/workspace_executor_pkg/helpers.py) · 154 | R03/R04/R09；路径/配置/输入 → 本地安全解析与扫描 → 基础工具结果 | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `split_values:10`；`safe_workspace_path:26` |
| [payloads.py](../total_control/tools/workspace_executor_pkg/payloads.py) · 104 | R03/R04/R09；工作区/自动化快照 → 提取执行包与 artifact → 工具 payload | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `execution_package_payload:6`；`workspace_artifacts:67` |
| [read_tools.py](../total_control/tools/workspace_executor_pkg/read_tools.py) · 276 | R03/R04/R09；workspace_dir/路径 → 本地 pathlib 读取与探测 → 文件/仓库/artifact 内容 | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `_workspace_dir:9`；`_read_text_file:20` |
| [web_search.py](../total_control/tools/workspace_executor_pkg/web_search.py) · 551 | R03/R04/R09；query/Search Profile → 供应商请求或显式种子回退 → 结果与 provenance | 问题/修补关联 [G21](#g21)；按登记方案处理，不另建平行服务。 | `workspace_seed_results:13`；`execute_web_search:24` |

### total_control/workspace

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/__init__.py) · 7 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [errors.py](../total_control/workspace/errors.py) · 20 | R05；阻塞项/工作区 → 结构化异常 → readiness error | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `WorkspaceWorkflowReadinessError:6` |
| [normalize.py](../total_control/workspace/normalize.py) · 2 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |

### total_control/workspace/automation

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/automation/__init__.py) · 202 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [_deps.py](../total_control/workspace/automation/_deps.py) · 17 | R05/R06；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [advance.py](../total_control/workspace/automation/advance.py) · 591 | R05/R06；工作区/派生状态 → FSM 与 playbook 组合 → 自动推进建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_advance_from_fsm:24`；`resolve_workspace_advance_bundle:36` |
| [bundle.py](../total_control/workspace/automation/bundle.py) · 647 | R05/R06；命令/目标/证据 → 生成脚本、标识、包门禁 → ExecutionPackage | 问题/修补关联 [G10](#g10)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `make_execution_package_id:11`；`make_stable_execution_package_id:16` |
| [contracts.py](../total_control/workspace/automation/contracts.py) · 2 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [core.py](../total_control/workspace/automation/core.py) · 61 | R05/R06；检查字段/状态 → 统一基础检查项 → 带优先级 readiness item | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_execution_node_by_kind:6`；`workspace_automation_check:15` |
| [deployment.py](../total_control/workspace/automation/deployment.py) · 226 | R05/R06；实例命令/服务参数 → 推断端口、健康检查与停止命令 → 部署交付建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_delivery_contract:7`；`workspace_deployment_health_path:76` |
| [evidence.py](../total_control/workspace/automation/evidence.py) · 206 | R05/R06；执行/发现状态 → 收集来源与分组 → evidence 清单 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_evidence_item:6`；`workspace_add_evidence_item:22` |
| [helpers.py](../total_control/workspace/automation/helpers.py) · 21 | R05/R06；列表/限额 → 压缩显示条目 → 紧凑列表 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `compact_contract_items:10` |
| [preflight.py](../total_control/workspace/automation/preflight.py) · 593 | R05/R06；工作区/资源/执行 → 汇总预检与资源编排 → 缺口和建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_execution_readiness_step:7`；`workspace_resource_item:36` |
| [report.py](../total_control/workspace/automation/report.py) · 458 | R05/R06；自动化各投影 → 汇总高亮/门禁/行动 → 操作报告 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_report_highlight:9`；`workspace_report_next_action:17` |
| [reproduction.py](../total_control/workspace/automation/reproduction.py) · 758 | R05/R06；源/环境/数据/命令/证据 → 推导复现实验清单 → reproduction manifest | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_reproduction_manifest_item:16`；`workspace_reproduction_intent:43` |
| [run_plan.py](../total_control/workspace/automation/run_plan.py) · 191 | R05/R06；节点/配置 → 顺序阶段与命令摘要 → run plan | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_run_node_phase:6`；`workspace_run_phase_label:21` |
| [topology.py](../total_control/workspace/automation/topology.py) · 391 | R05/R06；Agent/工具/Profile/节点 → 绑定与路由缺口检查 → agent topology | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_model_route_for_agent:9`；`workspace_agent_topology_gap:43` |

### total_control/workspace/automation/contracts_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/automation/contracts_pkg/__init__.py) · 60 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context.py](../total_control/workspace/automation/contracts_pkg/context.py) · 351 | R05/R06；节点/输出/映射 → 解析并汇总上下文契约 → 输入/输出状态 | N00C 通过别名复用 context_refs；展示就绪语义仍由本文件处理，关联 [G10](#g10)。 | `workspace_node_workflow_contract_metadata:16`；`workspace_context_value_present:84` |
| [io.py](../total_control/workspace/automation/contracts_pkg/io.py) · 226 | R05/R06；节点类型/映射 → I/O 默认和引用静态校验 → refs/gaps | 问题/修补关联 [G10](#g10)；按登记方案处理，不另建平行服务。 | `workspace_io_contract_for_kind:12`；`workspace_node_config_signal:24` |
| [orchestration.py](../total_control/workspace/automation/contracts_pkg/orchestration.py) · 225 | R05/R06；节点契约/拓扑缺口 → 按阶段分车道 → 编排展示契约 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_orchestration_gap_matches_node:12`；`workspace_orchestration_status:29` |
| [workflow.py](../total_control/workspace/automation/contracts_pkg/workflow.py) · 221 | R05/R06；工作区/执行状态 → 合成节点 I/O 契约 → workflow contract | 问题/修补关联 [G10](#g10)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `derive_workspace_workflow_contract:25` |

### total_control/workspace/cockpit

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/cockpit/__init__.py) · 135 | R02/R04/R05；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [_deps.py](../total_control/workspace/cockpit/_deps.py) · 16 | R02/R04/R05；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [commands.py](../total_control/workspace/cockpit/commands.py) · 56 | R02/R04/R05；仓库/配置/资源 → 规则推断 setup/run/GPU → 命令与候选建议 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `infer_workspace_setup_command:7`；`infer_workspace_run_command:20` |
| [discovery.py](../total_control/workspace/cockpit/discovery.py) · 386 | R02/R04/R05；输入路径/数据线索 → 目录推断与根验证 → discovery plan/bundle | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `workspace_path_like_values:10`；`workspace_project_path_score:34` |
| [evidence.py](../total_control/workspace/cockpit/evidence.py) · 417 | R02/R04/R05；发现结果/现有字段 → 生成并应用有来源回填 → backfill plan/实例 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `apply_workspace_evidence_config_value:15`；`merge_workspace_evidence_config_values:29` |
| [fsm.py](../total_control/workspace/cockpit/fsm.py) · 595 | R02/R04/R05；执行、包、阻塞项 → 状态机决定下一步 → cockpit/next_action | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_nodes_require_execution_package:12`；`attach_workspace_cockpit:20` |
| [helpers.py](../total_control/workspace/cockpit/helpers.py) · 75 | R02/R04/R05；工作区/Job/字段 → 通用选择与参数解析 → 基础派生值 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_jobs_for_workspace:7`；`workspace_node_config_ready_status:19` |
| [payload.py](../total_control/workspace/cockpit/payload.py) · 335 | R02/R04/R05；实例输入/Job/默认 → 规范化与运行数据投影 → 公开工作区 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `apply_workspace_automation_defaults_to_payload:19`；`apply_workspace_job_runtime:133` |
| [scheduler.py](../total_control/workspace/cockpit/scheduler.py) · 451 | R02/R04/R05；资源快照/限制/偏好 → 候选评分与绑定建议 → scheduler selection | 问题/修补关联 [G13](#g13)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_status_age_seconds:11`；`workspace_host_resource_summary_for_scheduler:18` |

### total_control/workspace/execution

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/execution/__init__.py) · 172 | R06/R10/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [_deps.py](../total_control/workspace/execution/_deps.py) · 42 | R06/R10/R11；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [agent_trace.py](../total_control/workspace/execution/agent_trace.py) · 285 | R06/R10/R11；工具参数/观测/事件 → 脱敏、摘要、有界规范 → compact trace | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `summarize_trace_text:31`；`redact_sensitive_arguments:39` |
| [jobs.py](../total_control/workspace/execution/jobs.py) · 21 | R06/R10/R11；Job 元数据 → 工作区绑定与排序 → 关联键 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_job_binding:7`；`workspace_job_sort_key:14` |
| [log_parser.py](../total_control/workspace/execution/log_parser.py) · 278 | R06/R10/R11；日志/路径标记 → 提取 artifact、资源、指标 → 结构化证据 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_log_path_artifact:8`；`workspace_manifest_setup_suggestion:19` |
| [nodes.py](../total_control/workspace/execution/nodes.py) · 30 | R06/R10/R11；节点集合/kind → 查询配置或节点 → 选中节点 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_node_config_by_kind:7`；`workspace_node_by_kind:17` |
| [paths.py](../total_control/workspace/execution/paths.py) · 217 | R06/R10/R11；路径/Job/日志快照 → 安全 probe 与有界尾部选择 → 路径/日志证据 | 问题/修补关联 [G12](#g12)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_config_values:7`；`compact_workspace_command:22` |
| [run_artifacts.py](../total_control/workspace/execution/run_artifacts.py) · 41 | R06/R10/R11；artifact 列表 → 字段规范与限制 → step artifacts | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `normalize_workspace_run_step_artifacts:9` |
| [run_compare.py](../total_control/workspace/execution/run_compare.py) · 130 | R06/R10/R11；两次 run/指标 → 语义与节点差异比较 → compare payload | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_execution_run_compare_payload:9`；`metric:19` |
| [run_delivery.py](../total_control/workspace/execution/run_delivery.py) · 177 | R06/R10/R11；包预期/step artifact → 路径匹配与完成度派生 → delivery closure | 问题/修补关联 [G06](#g06)；按登记方案处理，不另建平行服务。 | `_workspace_delivery_path_candidates:9`；`workspace_execution_run_delivery_closure:43` |
| [run_events.py](../total_control/workspace/execution/run_events.py) · 324 | R06/R10/R11；事件/流摘要 → 裁剪、脱敏、计数 → run event/delta_evidence | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `_compact_run_event_text:8`；`_compact_run_event_payload:15` |
| [run_export.py](../total_control/workspace/execution/run_export.py) · 341 | R06/R10/R11；run/关联任务 → 有界日志、artifact、manifest 组合 → JSON 导出 | 问题/修补关联 [G06](#g06)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_run_export_manifest:18`；`workspace_run_export_readme:147` |
| [run_records.py](../total_control/workspace/execution/run_records.py) · 243 | R06/R10/R11；steps/run/筛选 → 状态、进度、规范化 → run 记录 | 问题/修补关联 [G02](#g02)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `make_workspace_execution_run_id:12`；`make_agent_execution_id:16` |
| [run_refresh.py](../total_control/workspace/execution/run_refresh.py) · 266 | R06/R10/R11；run/实时 Job/子 run → 关联状态归并 → 刷新后步骤与 run | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `_workspace_child_run_status:21`；`_workspace_child_run_error:28` |
| [run_refs.py](../total_control/workspace/execution/run_refs.py) · 194 | R06/R10/R11；run/step 引用 → 去重、闭包与归属过滤 → 关联 Job/子 run | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_unique_run_ref_list:11`；`workspace_run_step_job_ids:20` |
| [run_replay.py](../total_control/workspace/execution/run_replay.py) · 169 | R06/R10/R11；run/关联 Job → 组装历史时间线 → 摘要回放 | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_execution_run_timeline:19`；`workspace_execution_run_replay_run_summary:63` |
| [run_state.py](../total_control/workspace/execution/run_state.py) · 103 | R06/R10/R11；节点/Job → 按最近 Job 派生节点执行状态 → 执行面板状态 | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `derive_workspace_execution_state:10` |
| [run_steps.py](../total_control/workspace/execution/run_steps.py) · 353 | R06/R10/R11；Job/Agent 结果 → 状态、资源、引用规范 → 持久 step | 问题/修补关联 [G02](#g02)、[G03](#g03)、[G06](#g06)；按登记方案处理，不另建平行服务。 | `workspace_run_step_status_from_job:18`；`_normalize_agent_meta:33` |
| [runs.py](../total_control/workspace/execution/runs.py) · 77 | R06/R10/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [trace.py](../total_control/workspace/execution/trace.py) · 246 | R06/R10/R11；节点/绑定 Job → 汇总产物、资源与轨迹 → 节点 trace | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_node_artifacts:20`；`workspace_node_resources:97` |

### total_control/workspace/schema

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/schema/__init__.py) · 139 | R02/R03/R05；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [agents_tools.py](../total_control/workspace/schema/agents_tools.py) · 438 | R02/R03/R05；Agent/工具草稿/默认 → 规范与 backfill → 有效能力定义 | 问题/修补关联 [G10](#g10)、[G11](#g11)；按登记方案处理，不另建平行服务。 | `_tool_side_effect_value:14`；`workspace_default_agents:20` |
| [chat.py](../total_control/workspace/schema/chat.py) · 461 | R02/R03/R05；消息/反思/工作区 → 规范、规则回复与 debug → chat/debug payload | 问题/修补关联 [G05](#g05)、[G11](#g11)；按登记方案处理，不另建平行服务。 | `normalize_workspace_context_reflection:15`；`normalize_workspace_chat_message:54` |
| [nodes.py](../total_control/workspace/schema/nodes.py) · 697 | R02/R03/R05；源类型/节点草稿/recipe → 默认、绑定、连线规范 → 顺序工作区节点 | 问题/修补关联 [G10](#g10)、[G14](#g14)；按登记方案处理，不另建平行服务。 | `workspace_node_definition:22`；`workspace_node_kinds_for_source:31` |
| [recipe.py](../total_control/workspace/schema/recipe.py) · 201 | R02/R03/R05；启动/模型/环境输入 → 字段规范与源类型推断 → recipe/model/inputs | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `normalize_workspace_recipe:13`；`clean_workspace_config_default:32` |
| [templates.py](../total_control/workspace/schema/templates.py) · 1362 | R02/R03/R05；模板/实例快照 → 版本、拓扑、差异与迁移计划 → template/snapshot/diff | 问题/修补关联 [G16](#g16)；按登记方案处理，不另建平行服务。 | `workflow_template_sort_key:39`；`normalize_workflow_template_version_history:46` |

### web

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [index.html](../web/index.html) · 1894 | R12/R14；浏览器加载 → 界面壳、DOM id 与脚本顺序 → 产品入口 | 保留壳；关联 [G15](#g15)，抽控制器同步验证引用/加载次序。 | 文件整体/公开入口 |

### web/config-center

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [config_center_agent_actions.js](../web/config-center/config_center_agent_actions.js) · 126 | R03/R12；用户事件/注入依赖 → Agent 定义动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_agent_health.js](../web/config-center/config_center_agent_health.js) · 112 | R03/R12；页面数据/注入依赖 → Agent 能力健康 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`textList:21` |
| [config_center_agent_renderer.js](../web/config-center/config_center_agent_renderer.js) · 196 | R03/R12；状态/注入 renderer → Agent 定义组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_ai_renderer.js](../web/config-center/config_center_ai_renderer.js) · 201 | R03/R12；状态/注入 renderer → AI 配置组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_diagnostics.js](../web/config-center/config_center_diagnostics.js) · 128 | R03/R12；页面数据/注入依赖 → 链诊断 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`defaultToolTestArguments:21` |
| [config_center_execution_overview_actions.js](../web/config-center/config_center_execution_overview_actions.js) · 60 | R03/R12；用户事件/注入依赖 → 全局运行概览动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_execution_overview_renderer.js](../web/config-center/config_center_execution_overview_renderer.js) · 145 | R03/R12；状态/注入 renderer → 全局运行概览组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_provider_actions.js](../web/config-center/config_center_provider_actions.js) · 119 | R03/R12；用户事件/注入依赖 → Provider 配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_provider_profiles.js](../web/config-center/config_center_provider_profiles.js) · 239 | R03/R12；页面数据/注入依赖 → Provider 目录和选项 → 派生状态/界面结果 | 契约/维护关联 [G21](#g21)；消费后端结果，随所属切片收敛。 | `escapeFor:13`；`vendorDefaultBaseUrl:47` |
| [config_center_tool_actions.js](../web/config-center/config_center_tool_actions.js) · 109 | R03/R12；用户事件/注入依赖 → 工具配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_tool_renderer.js](../web/config-center/config_center_tool_renderer.js) · 164 | R03/R12；状态/注入 renderer → 工具配置组合 → DOM 更新 | 契约/维护关联 [G11](#g11)；消费后端结果，随所属切片收敛。 | `element:8`；`listFor:12` |

### web/core

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [app.js](../web/core/app.js) · 26570 | R12；页面数据/注入依赖 → 应用组合、共享状态和跨界面编排 → 派生状态/界面结果 | 契约/维护关联 [G15](#g15)、[G10](#g10)、[G17](#g17)；消费后端结果，随所属切片收敛。 | `markWorkspaceUiInteraction:280`；`workspaceFlowCanvasControlsApi:341` |
| [app_navigation_actions.js](../web/core/app_navigation_actions.js) · 70 | R12；用户事件/注入依赖 → 顶层导航动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`query:12` |
| [app_runtime.js](../web/core/app_runtime.js) · 250 | R12；页面数据/注入依赖 → fetch、浏览器存储与表单状态 → 派生状态/界面结果 | 契约/维护关联 [G19](#g19)；消费后端结果，随所属切片收敛。 | `loadStoredValue:7`；`saveStoredValue:15` |
| [app_status_actions.js](../web/core/app_status_actions.js) · 31 | R12；用户事件/注入依赖 → 全局刷新/状态动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`call:12` |
| [display_formatters.js](../web/core/display_formatters.js) · 57 | R12；页面数据/注入依赖 → 单位/时间/摘要格式 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `fmtMiB:4`；`formatBytes:10` |
| [input_parsers.js](../web/core/input_parsers.js) · 38 | R12；页面数据/注入依赖 → 基础输入解析 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `positiveNumberOrBlank:4`；`parseLineList:9` |
| [status_labels.js](../web/core/status_labels.js) · 91 | R12；页面数据/注入依赖 → 公开状态文案 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `zhStatus:30`；`zhKind:34` |

### web/monitoring

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [job_form_actions.js](../web/monitoring/job_form_actions.js) · 21 | R01/R07/R12；用户事件/注入依赖 → 任务表单动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`bind:12` |
| [job_list_markup.js](../web/monitoring/job_list_markup.js) · 69 | R01/R07/R12；数据/格式化依赖 → 任务列表转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`jobListEmptyMarkup:17` |
| [job_state.js](../web/monitoring/job_state.js) · 144 | R01/R07/R12；页面数据/注入依赖 → 任务筛选/耗时/排队 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `parseDateMs:8`；`formatDurationMs:13` |
| [log_view_markup.js](../web/monitoring/log_view_markup.js) · 45 | R01/R07/R12；数据/格式化依赖 → 日志高亮转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeHtmlFor:17`；`escapeRegExpFor:21` |
| [monitoring_filter_actions.js](../web/monitoring/monitoring_filter_actions.js) · 84 | R01/R07/R12；用户事件/注入依赖 → 监控筛选动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`queryAll:12` |
| [monitoring_process_filters.js](../web/monitoring/monitoring_process_filters.js) · 95 | R01/R07/R12；页面数据/注入依赖 → 进程筛选/排序 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `processFilterKey:4`；`processSortValue:20` |
| [monitoring_process_stop_actions.js](../web/monitoring/monitoring_process_stop_actions.js) · 34 | R01/R07/R12；用户事件/注入依赖 → 停止进程动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`resolve:12` |
| [monitoring_process_stop_confirm.js](../web/monitoring/monitoring_process_stop_confirm.js) · 48 | R01/R07/R12；页面数据/注入依赖 → 进程所有者确认 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `processStopOwnerUnknown:4`；`processStopConfirmCopy:9` |
| [monitoring_table_markup.js](../web/monitoring/monitoring_table_markup.js) · 81 | R01/R07/R12；数据/格式化依赖 → GPU/进程表格转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`gpuRowsEmptyMarkup:17` |
| [output_tabs_markup.js](../web/monitoring/output_tabs_markup.js) · 38 | R01/R07/R12；数据/格式化依赖 → 输出页签转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`outputTabsPlaceholderMarkup:17` |
| [output_terminal_actions.js](../web/monitoring/output_terminal_actions.js) · 99 | R01/R07/R12；用户事件/注入依赖 → 日志与终端操作动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [runtime_storage_actions.js](../web/monitoring/runtime_storage_actions.js) · 227 | R01/R07/R12；用户事件/注入依赖 → 运行存储维护动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:16`；`runtimeStorageSummaryApi:20` |
| [runtime_storage_summary.js](../web/monitoring/runtime_storage_summary.js) · 101 | R01/R07/R12；页面数据/注入依赖 → 运行存储统计 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`formatBytesFor:17` |
| [server_admin_actions.js](../web/monitoring/server_admin_actions.js) · 100 | R01/R07/R12；用户事件/注入依赖 → 服务器管理动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [server_list_actions.js](../web/monitoring/server_list_actions.js) · 161 | R01/R07/R12；用户事件/注入依赖 → 服务器列表/固定/排序动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [server_list_markup.js](../web/monitoring/server_list_markup.js) · 353 | R01/R07/R12；数据/格式化依赖 → 服务器列表/固定/排序转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`serverListEmptyMarkup:17` |
| [server_selection_actions.js](../web/monitoring/server_selection_actions.js) · 35 | R01/R07/R12；用户事件/注入依赖 → 选择服务器动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventValue:12` |
| [task_plan_actions.js](../web/monitoring/task_plan_actions.js) · 34 | R01/R07/R12；用户事件/注入依赖 → 参数矩阵计划动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`call:12` |
| [terminal_activity_markup.js](../web/monitoring/terminal_activity_markup.js) · 140 | R01/R07/R12；数据/格式化依赖 → 终端活动转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`terminalActivityKindLabel:17` |
| [tmux_session_markup.js](../web/monitoring/tmux_session_markup.js) · 40 | R01/R07/R12；数据/格式化依赖 → tmux 会话转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`tmuxErrorMarkup:17` |

### web/styles

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [styles.css](../web/styles/styles.css) · 23037 | R12/R14；界面类名/视口 → 层叠与响应式布局 → 视觉样式 | 维护风险；[G15](#g15)，覆盖/媒体规则逐块验证后收敛，禁自动去重。 | 文件整体/公开入口 |

### web/transfer

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [file_picker_markup.js](../web/transfer/file_picker_markup.js) · 125 | R08/R12；数据/格式化依赖 → 文件选择列表转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`normalizeFor:17` |
| [file_picker_navigation.js](../web/transfer/file_picker_navigation.js) · 181 | R08/R12；页面数据/注入依赖 → 文件选择历史/上下级导航 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeFor:4`；`resetNavigationState:11` |
| [file_preview_markup.js](../web/transfer/file_preview_markup.js) · 159 | R08/R12；数据/格式化依赖 → 预览显示转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`pathBaseNameFor:17` |
| [file_preview_state.js](../web/transfer/file_preview_state.js) · 48 | R08/R12；页面数据/注入依赖 → 预览类型/文本格式 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `pathBaseNameFor:9`；`isLikelyTextPreviewPath:13` |
| [transfer_command_builder.js](../web/transfer/transfer_command_builder.js) · 39 | R08/R12；页面数据/注入依赖 → rsync 命令预览 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `buildTransferCommandParts:13` |
| [transfer_ignore_chips.js](../web/transfer/transfer_ignore_chips.js) · 40 | R08/R12；页面数据/注入依赖 → 传输过滤项 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`ignoreCountText:17` |
| [transfer_path_favorites_markup.js](../web/transfer/transfer_path_favorites_markup.js) · 78 | R08/R12；数据/格式化依赖 → 传输收藏转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`pathBaseNameFor:17` |
| [transfer_path_favorites_state.js](../web/transfer/transfer_path_favorites_state.js) · 89 | R08/R12；页面数据/注入依赖 → 传输收藏 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeFavoritePath:6`；`serverKey:10` |
| [transfer_path_memory_state.js](../web/transfer/transfer_path_memory_state.js) · 39 | R08/R12；页面数据/注入依赖 → 传输路径记忆 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `emptyStore:4`；`normalizeStore:8` |
| [transfer_path_utils.js](../web/transfer/transfer_path_utils.js) · 77 | R08/R12；页面数据/注入依赖 → 传输路径比较/解析 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `ensureDirectorySlash:4`；`normalizePathForCompare:10` |
| [transfer_progress_markup.js](../web/transfer/transfer_progress_markup.js) · 48 | R08/R12；数据/格式化依赖 → 传输进度转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`statusFor:17` |
| [transfer_progress_state.js](../web/transfer/transfer_progress_state.js) · 24 | R08/R12；页面数据/注入依赖 → 传输进度 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `parseTransferProgress:4`；`lastTransferLine:11` |
| [transfer_selected_sources.js](../web/transfer/transfer_selected_sources.js) · 151 | R08/R12；页面数据/注入依赖 → 多选传输源 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`element:21` |
| [transfer_surface_actions.js](../web/transfer/transfer_surface_actions.js) · 238 | R08/R12；用户事件/注入依赖 → 传输与文件选择交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [transfer_tree_markup.js](../web/transfer/transfer_tree_markup.js) · 103 | R08/R12；数据/格式化依赖 → 源/目标目录树转义与展示 → HTML 文本 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`rowPadding:17` |
| [transfer_tree_navigation.js](../web/transfer/transfer_tree_navigation.js) · 107 | R08/R12；页面数据/注入依赖 → 传输树导航 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeFor:4`；`rememberForwardStack:11` |

### web/workflow-template

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [template_review_actions.js](../web/workflow-template/template_review_actions.js) · 80 | R02/R05/R12；用户事件/注入依赖 → 模板审查/迁移入口动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workflow_template_canvas.js](../web/workflow-template/workflow_template_canvas.js) · 234 | R02/R05/R12；页面数据/注入依赖 → 顺序模板画布 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`searchToolsMarkup:21` |
| [workflow_template_canvas_actions.js](../web/workflow-template/workflow_template_canvas_actions.js) · 166 | R02/R05/R12；用户事件/注入依赖 → 顺序模板画布动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `eventTarget:8`；`selectedNodeKind:14` |
| [workflow_template_canvas_renderer.js](../web/workflow-template/workflow_template_canvas_renderer.js) · 126 | R02/R05/R12；状态/注入 renderer → 顺序模板画布组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`createElement:12` |
| [workflow_template_canvas_search.js](../web/workflow-template/workflow_template_canvas_search.js) · 145 | R02/R05/R12；页面数据/注入依赖 → 模板画布搜索 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `nodeSearchText:8`；`nodeMatchesSearch:44` |
| [workflow_template_canvas_search_actions.js](../web/workflow-template/workflow_template_canvas_search_actions.js) · 54 | R02/R05/R12；用户事件/注入依赖 → 模板画布搜索动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `nodesFor:8`；`searchApiFor:13` |
| [workflow_template_catalog.js](../web/workflow-template/workflow_template_catalog.js) · 143 | R02/R05/R12；页面数据/注入依赖 → 模板目录/节点列表 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`summaryMarkup:21` |
| [workflow_template_catalog_actions.js](../web/workflow-template/workflow_template_catalog_actions.js) · 122 | R02/R05/R12；用户事件/注入依赖 → 模板目录/节点列表动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:23`；`queryAll:27` |
| [workflow_template_catalog_renderers.js](../web/workflow-template/workflow_template_catalog_renderers.js) · 62 | R02/R05/R12；状态/注入 renderer → 模板目录/节点列表组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`catalogApiFor:12` |
| [workflow_template_draft.js](../web/workflow-template/workflow_template_draft.js) · 176 | R02/R05/R12；页面数据/注入依赖 → 模板草稿 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `defaultDraft:8`；`normalizeDraft:56` |
| [workflow_template_io_state.js](../web/workflow-template/workflow_template_io_state.js) · 70 | R02/R05/R12；页面数据/注入依赖 → 节点 I/O 完整度 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `nodeIoState:8` |
| [workflow_template_lifecycle_actions.js](../web/workflow-template/workflow_template_lifecycle_actions.js) · 136 | R02/R05/R12；用户事件/注入依赖 → 模板预览/保存/删除动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `selectedTemplateId:8`；`previewTemplateId:12` |
| [workflow_template_manage_renderer.js](../web/workflow-template/workflow_template_manage_renderer.js) · 93 | R02/R05/R12；状态/注入 renderer → 模板管理表单组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`draftFor:12` |
| [workflow_template_mapping.js](../web/workflow-template/workflow_template_mapping.js) · 652 | R02/R05/R12；页面数据/注入依赖 → 模板输入与边交接映射 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`toText:21` |
| [workflow_template_mapping_actions.js](../web/workflow-template/workflow_template_mapping_actions.js) · 77 | R02/R05/R12；用户事件/注入依赖 → 模板输入与边交接映射动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `nodesFor:8`；`selectedNodeIdFor:13` |
| [workflow_template_node_editor.js](../web/workflow-template/workflow_template_node_editor.js) · 121 | R02/R05/R12；页面数据/注入依赖 → 模板节点编辑器 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`agentOptions:21` |
| [workflow_template_node_editor_actions.js](../web/workflow-template/workflow_template_node_editor_actions.js) · 145 | R02/R05/R12；用户事件/注入依赖 → 模板节点编辑器动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `eventTarget:8`；`updateNode:14` |
| [workflow_template_node_editor_renderer.js](../web/workflow-template/workflow_template_node_editor_renderer.js) · 43 | R02/R05/R12；状态/注入 renderer → 模板节点编辑器组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`editorApiFor:12` |
| [workflow_template_node_list_actions.js](../web/workflow-template/workflow_template_node_list_actions.js) · 34 | R02/R05/R12；用户事件/注入依赖 → 模板节点选择动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`templateNodeButton:12` |
| [workflow_template_node_mutations.js](../web/workflow-template/workflow_template_node_mutations.js) · 141 | R02/R05/R12；页面数据/注入依赖 → 模板节点增删/移动/字段变更 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `draftNodes:8`；`nodeFormData:12` |
| [workflow_template_repair.js](../web/workflow-template/workflow_template_repair.js) · 111 | R02/R05/R12；页面数据/注入依赖 → 模板诊断修复 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `cloneValue:4`；`repairActions:12` |
| [workflow_template_repair_actions.js](../web/workflow-template/workflow_template_repair_actions.js) · 87 | R02/R05/R12；用户事件/注入依赖 → 模板诊断修复动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `repairApiFor:8`；`validationFor:12` |
| [workflow_template_state.js](../web/workflow-template/workflow_template_state.js) · 81 | R02/R05/R12；页面数据/注入依赖 → 模板选择/草稿状态 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `templateById:8`；`firstNodeId:13` |
| [workflow_template_studio_overview.js](../web/workflow-template/workflow_template_studio_overview.js) · 58 | R02/R05/R12；页面数据/注入依赖 → 模板工作室概览 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`manageOverviewCardsMarkup:17` |
| [workflow_template_studio_overview_renderer.js](../web/workflow-template/workflow_template_studio_overview_renderer.js) · 103 | R02/R05/R12；状态/注入 renderer → 模板工作室概览组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`overviewApiFor:12` |
| [workflow_template_topology.js](../web/workflow-template/workflow_template_topology.js) · 218 | R02/R05/R12；页面数据/注入依赖 → 模板拓扑只读预览 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `cssToken:15`；`escapeFor:20` |
| [workflow_template_validation.js](../web/workflow-template/workflow_template_validation.js) · 112 | R02/R05/R12；页面数据/注入依赖 → 模板校验结果 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`label:21` |
| [workflow_template_version_history.js](../web/workflow-template/workflow_template_version_history.js) · 119 | R02/R05/R12；页面数据/注入依赖 → 模板版本历史 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`dateFor:17` |
| [workflow_template_version_history_actions.js](../web/workflow-template/workflow_template_version_history_actions.js) · 29 | R02/R05/R12；用户事件/注入依赖 → 模板版本历史动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `currentTemplateForCopy:8`；`copyHistory:14` |

### web/workspace

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [workspace_action_surfaces.js](../web/workspace/workspace_action_surfaces.js) · 75 | R02/R06/R09/R12；页面数据/注入依赖 → 工作区动作入口 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:34`；`query:38` |
| [workspace_agent_catalog.js](../web/workspace/workspace_agent_catalog.js) · 48 | R02/R06/R09/R12；页面数据/注入依赖 → 实例 Agent 查询/显示 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceAgentById:4`；`workspaceAgentDisplayName:8` |
| [workspace_agent_stream_state.js](../web/workspace/workspace_agent_stream_state.js) · 286 | R02/R06/R09/R12；页面数据/注入依赖 → Agent 实时输出缓冲 → 派生状态/界面结果 | 契约/维护关联 [G04](#g04)、[G05](#g05)；消费后端结果，随所属切片收敛。 | `appState:8`；`selectedWorkspaceId:13` |
| [workspace_agent_tool_actions.js](../web/workspace/workspace_agent_tool_actions.js) · 166 | R02/R06/R09/R12；用户事件/注入依赖 → 实例 Agent/工具编辑交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_agent_trace.js](../web/workspace/workspace_agent_trace.js) · 218 | R02/R06/R09/R12；页面数据/注入依赖 → Agent 工具与事件轨迹 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:17`；`compactFor:21` |
| [workspace_automation_actions.js](../web/workspace/workspace_automation_actions.js) · 885 | R02/R06/R09/R12；用户事件/注入依赖 → 自动推进/运行/反馈编排动作路由 → 回调/API 请求 | 契约/维护关联 [G01](#g01)、[G02](#g02)、[G17](#g17)；消费后端结果，随所属切片收敛。 | `appState:8`；`element:15` |
| [workspace_catalog_data.js](../web/workspace/workspace_catalog_data.js) · 564 | R02/R06/R09/R12；页面数据/注入依赖 → 节点/能力静态目录 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)；消费后端结果，随所属切片收敛。 | `deepClone:538`；`clone:546` |
| [workspace_chat_actions.js](../web/workspace/workspace_chat_actions.js) · 61 | R02/R06/R09/R12；用户事件/注入依赖 → 聊天/反思动作动作路由 → 回调/API 请求 | 契约/维护关联 [G05](#g05)；消费后端结果，随所属切片收敛。 | `element:8`；`eventTarget:12` |
| [workspace_chat_normalizers.js](../web/workspace/workspace_chat_normalizers.js) · 84 | R02/R06/R09/R12；页面数据/注入依赖 → 聊天与反思字段规范 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeWorkspaceContextReflection:16`；`normalizeWorkspaceChatMessage:45` |
| [workspace_defaults.js](../web/workspace/workspace_defaults.js) · 217 | R02/R06/R09/R12；页面数据/注入依赖 → 实例默认值 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)；消费后端结果，随所属切片收敛。 | `deepCloneFor:56`；`agentCatalogFor:60` |
| [workspace_draft_normalizers.js](../web/workspace/workspace_draft_normalizers.js) · 100 | R02/R06/R09/R12；页面数据/注入依赖 → 能力草稿字段规范 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeWorkspaceToolDraft:27`；`normalizeWorkspaceAgentDraft:42` |
| [workspace_event_stream.js](../web/workspace/workspace_event_stream.js) · 391 | R02/R06/R09/R12；页面数据/注入依赖 → SSE 连接、事件应用与 gap 恢复 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `appState:33`；`uiState:38` |
| [workspace_execution_lane_rail.js](../web/workspace/workspace_execution_lane_rail.js) · 97 | R02/R06/R09/R12；页面数据/注入依赖 → 只读执行车道 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`contractFromWorkspace:17` |
| [workspace_execution_overview.js](../web/workspace/workspace_execution_overview.js) · 192 | R02/R06/R09/R12；页面数据/注入依赖 → 全局 run/Job 筛选与显示 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`statusClass:21` |
| [workspace_flow_canvas_controls.js](../web/workspace/workspace_flow_canvas_controls.js) · 178 | R02/R06/R09/R12；页面数据/注入依赖 → 执行板缩放/平移 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `configFor:16`；`boardFor:23` |
| [workspace_flow_tool_state.js](../web/workspace/workspace_flow_tool_state.js) · 76 | R02/R06/R09/R12；页面数据/注入依赖 → 节点工具健康/选择状态 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceFlowNodeToolStatuses:4`；`workspaceFlowToolStatusLabel:21` |
| [workspace_focus_navigation.js](../web/workspace/workspace_focus_navigation.js) · 441 | R02/R06/R09/R12；页面数据/注入依赖 → 工作区焦点、滚动与跨面板定位 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `elementById:4`；`flashWorkspaceFocus:9` |
| [workspace_form_actions.js](../web/workspace/workspace_form_actions.js) · 54 | R02/R06/R09/R12；用户事件/注入依赖 → 实例高级表单动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`fieldName:12` |
| [workspace_help_popover_actions.js](../web/workspace/workspace_help_popover_actions.js) · 79 | R02/R06/R09/R12；用户事件/注入依赖 → 帮助浮层动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `eventTarget:8`；`workspaceHelpTarget:14` |
| [workspace_launcher_actions.js](../web/workspace/workspace_launcher_actions.js) · 92 | R02/R06/R09/R12；用户事件/注入依赖 → 目标输入与实例创建动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:16`；`eventTarget:20` |
| [workspace_model_provider_actions.js](../web/workspace/workspace_model_provider_actions.js) · 91 | R02/R06/R09/R12；用户事件/注入依赖 → 实例模型路由交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_node_actions.js](../web/workspace/workspace_node_actions.js) · 91 | R02/R06/R09/R12；用户事件/注入依赖 → 实例节点交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_node_catalog.js](../web/workspace/workspace_node_catalog.js) · 422 | R02/R06/R09/R12；页面数据/注入依赖 → 实例节点默认/归一化/顺序链 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)、[G14](#g14)；消费后端结果，随所属切片收敛。 | `workspaceNodeMeta:48`；`workspaceNodeLabel:53` |
| [workspace_node_run_state.js](../web/workspace/workspace_node_run_state.js) · 76 | R02/R06/R09/R12；页面数据/注入依赖 → 节点执行方式和运行内容 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)；消费后端结果，随所属切片收敛。 | `workspaceNodeSupportsAgentRun:32`；`workspaceNodeSupportsJobRun:39` |
| [workspace_run_actions.js](../web/workspace/workspace_run_actions.js) · 83 | R02/R06/R09/R12；用户事件/注入依赖 → 运行列表和筛选交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_run_detail_actions.js](../web/workspace/workspace_run_detail_actions.js) · 305 | R02/R06/R09/R12；用户事件/注入依赖 → 详情、回放、比较、导出动作动作路由 → 回调/API 请求 | 契约/维护关联 [G06](#g06)、[G20](#g20)；消费后端结果，随所属切片收敛。 | `appState:8`；`selectedWorkspace:13` |
| [workspace_run_filter.js](../web/workspace/workspace_run_filter.js) · 195 | R02/R06/R09/R12；页面数据/注入依赖 → 运行筛选条件 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:22`；`normalizeFilters:26` |
| [workspace_run_replay.js](../web/workspace/workspace_run_replay.js) · 220 | R02/R06/R09/R12；页面数据/注入依赖 → 摘要回放展示 → 派生状态/界面结果 | 契约/维护关联 [G20](#g20)；消费后端结果，随所属切片收敛。 | `escapeFor:13`；`compactFor:17` |
| [workspace_run_state_merge.js](../web/workspace/workspace_run_state_merge.js) · 347 | R02/R06/R09/R12；页面数据/注入依赖 → HTTP/SSE run/step 版本合并 → 派生状态/界面结果 | 契约/维护关联 [G02](#g02)、[G20](#g20)；消费后端结果，随所属切片收敛。 | `defaultTimestampMs:17`；`timestampMs:22` |
| [workspace_run_summary.js](../web/workspace/workspace_run_summary.js) · 260 | R02/R06/R09/R12；页面数据/注入依赖 → 运行进度/交付摘要 → 派生状态/界面结果 | 契约/维护关联 [G02](#g02)、[G06](#g06)；消费后端结果，随所属切片收敛。 | `escapeFor:17`；`statusFor:21` |
| [workspace_shell_actions.js](../web/workspace/workspace_shell_actions.js) · 46 | R02/R06/R09/R12；用户事件/注入依赖 → 工作区视图/页签交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_template_diff.js](../web/workspace/workspace_template_diff.js) · 282 | R02/R06/R09/R12；页面数据/注入依赖 → 模板/实例差异 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`diffStatusLabel:17` |
| [workspace_template_migration_actions.js](../web/workspace/workspace_template_migration_actions.js) · 174 | R02/R06/R09/R12；用户事件/注入依赖 → 模板迁移动作动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `selectedWorkspace:8`；`cachedDiff:12` |
| [workspace_tool_catalog.js](../web/workspace/workspace_tool_catalog.js) · 93 | R02/R06/R09/R12；页面数据/注入依赖 → 实例工具分类/健康/副作用显示 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceToolById:22`；`workspaceToolLabel:26` |

### tests

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [test_agent_output_persistence.py](../tests/test_agent_output_persistence.py) · 44 | R09/R10；隔离 fixture/假适配器 → 3 个行为用例 → 断言公开结果与失败边界 | 保留；补长正文/attempt 输出来源，保留输出持久化断言；关联 [G06](#g06)、[G09](#g09) | `test_agent_meta_persists_and_round_trips:12`；`test_job_step_has_empty_agent_meta:36` |
| [test_agent_output_validation.py](../tests/test_agent_output_validation.py) · 198 | R09；隔离 fixture/假适配器 → 13 个行为用例 → 断言公开结果与失败边界 | 保留；保留 JSON/字段校验；补过期/取消后的成功禁止；关联 [G04](#g04)、[G10](#g10) | `_workspace:22`；`test_validate_accepts_valid_json:33` |
| [test_agent_runtime_metadata.py](../tests/test_agent_runtime_metadata.py) · 86 | R09；隔离 fixture/假适配器 → 4 个行为用例 → 断言公开结果与失败边界 | 保留；保留嵌套 runtime 元数据兼容；新协议稳定后再收敛；关联 [G02](#g02)、[G11](#g11) | `test_tool_runtime_metadata_ignores_invalid_observation_payloads:8`；`test_tool_runtime_metadata_reads_existing_top_level_fields:14` |
| [test_agent_timeout_cancel.py](../tests/test_agent_timeout_cancel.py) · 203 | R09；隔离 fixture/假适配器 → 9 个行为用例 → 断言公开结果与失败边界 | 保留；补最后调用返回后取消/超时与副作用前检查；关联 [G04](#g04) | `_FakeResp:20`；`_FakeClient:28` |
| [test_agent_trace_and_run_filter.py](../tests/test_agent_trace_and_run_filter.py) · 319 | R09/R11；隔离 fixture/假适配器 → 8 个行为用例 → 断言公开结果与失败边界 | 保留；保留 trace/完整引用筛选；与相同过滤场景对照后再合并；关联 [G20](#g20) | `test_make_and_normalize_agent_trace_events:17`；`test_tool_observation_failed_flags_runtime_terminal_failures:41` |
| [test_events.py](../tests/test_events.py) · 633 | R12；隔离 fixture/假适配器 → 18 个行为用例 → 断言公开结果与失败边界 | 保留；保留 SSE gap/回放；补重启/重复完成通知的领域恢复；关联 [G02](#g02)、[G09](#g09) | `test_broker_reports_gap_when_visible_workspace_event_was_evicted:25`；`test_broker_does_not_gap_for_only_unrelated_workspace_evictions:43` |
| [test_file_browser_path_safety.py](../tests/test_file_browser_path_safety.py) · 52 | R04/R13；隔离 fixture/假适配器 → 4 个行为用例 → 断言公开结果与失败边界 | 保留；修正宿主挂载依赖，保留敏感路径/符号链接断言；关联 [G07](#g07) | `test_local_file_browser_filters_sensitive_entries:12`；`test_local_file_browser_blocks_sensitive_file_read:28` |
| [test_handler.py](../tests/test_handler.py) · 49 | R12/R13；隔离 fixture/假适配器 → 2 个行为用例 → 断言公开结果与失败边界 | 保留；保留静态路径穿越；补请求大小/JSON 类型错误；关联 [G19](#g19) | `test_handler_serves_static_file_when_cwd_is_missing:13`；`test_handler_static_path_translation_stays_inside_web_dir:36` |
| [test_http_get_routes.py](../tests/test_http_get_routes.py) · 55 | R12；隔离 fixture/假适配器 → 1 个行为用例 → 断言公开结果与失败边界 | 保留；保留公开封装与 GET 分发；按族补参数边界；关联 [G19](#g19) | `_SpyState:8`；`_JsonHandler:17` |
| [test_job_launch_idempotence.py](../tests/test_job_launch_idempotence.py) · 37 | R07；隔离 fixture/假适配器 → 1 个行为用例 → 断言公开结果与失败边界 | 保留；保留单任务幂等；新增跨任务 GPU claim/崩溃窗口验收；关联 [G09](#g09)、[G13](#g13) | `_LaunchState:9`；`test_start_job_skips_duplicate_launch_attempt:23` |
| [test_phase3_agent_node_kinds.py](../tests/test_phase3_agent_node_kinds.py) · 105 | R06/R09；隔离 fixture/假适配器 → 7 个行为用例 → 断言公开结果与失败边界 | 保留；按执行器选择行为归档，不因阶段名删除；关联 [G01](#g01)、[G11](#g11) | `test_path_resolve_and_artifact_collect_are_agent_executable:15`；`test_agent_handler_selects_agent_executor_for_path_resolve:20` |
| [test_phase3_agent_runtime_integration.py](../tests/test_phase3_agent_runtime_integration.py) · 1119 | R03/R09；隔离 fixture/假适配器 → 16 个行为用例 → 断言公开结果与失败边界 | 保留；保留受控工具/敏感路径；补远程 host 文件与完成后恢复；关联 [G02](#g02)、[G11](#g11)、[G12](#g12) | `_isolated_runtime_paths:15`；`_isolated_state:40` |
| [test_phase4_context_reflection_dismiss.py](../tests/test_phase4_context_reflection_dismiss.py) · 254 | R09/R12；隔离 fixture/假适配器 → 4 个行为用例 → 断言公开结果与失败边界 | 保留；保留人工反思边界；补非抛异常的 Agent 失败状态；关联 [G05](#g05) | `_state:11`；`_assistant_message_with_reflection:31` |
| [test_phase5_execution_package.py](../tests/test_phase5_execution_package.py) · 1629 | R05/R06/R10；隔离 fixture/假适配器 → 42 个行为用例 → 断言公开结果与失败边界 | 保留；拆出工作流推进/执行包/交付行为；补闭环失败场景后再去重；关联 [G01](#g01)、[G02](#g02)、[G03](#g03)、[G06](#g06) | `_StubContext:34`；`_NodePayloadState:39` |
| [test_phase6_agent_capability_management.py](../tests/test_phase6_agent_capability_management.py) · 71 | R03；隔离 fixture/假适配器 → 1 个行为用例 → 断言公开结果与失败边界 | 保留；保留有效运行配置 round-trip，统一 fixtures 即可；关联 [G21](#g21) | `test_global_agent_runtime_boundaries_round_trip_and_debug:8` |
| [test_phase6_tool_provider_run_overview.py](../tests/test_phase6_tool_provider_run_overview.py) · 1128 | R03/R11；隔离 fixture/假适配器 → 13 个行为用例 → 断言公开结果与失败边界 | 保留；拆工具安全测试/路由/全局概览所有权，不删除独有安全断言；关联 [G11](#g11)、[G21](#g21) | `_state:14`；`test_tool_safe_payload_blocks_runtime_tools:46` |
| [test_phase6_workflow_template_validation.py](../tests/test_phase6_workflow_template_validation.py) · 560 | R02/R05；隔离 fixture/假适配器 → 19 个行为用例 → 断言公开结果与失败边界 | 保留；保留模板隔离、映射、迁移与拓扑校验；区别预览与执行语义；关联 [G10](#g10) | `_FakeState:24`；`_default_template:62` |
| [test_provider_catalog.py](../tests/test_provider_catalog.py) · 155 | R03；隔离 fixture/假适配器 → 9 个行为用例 → 断言公开结果与失败边界 | 保留；保留目录/无密钥/按种类默认契约，迁移 SDK 时继续运行；关联 [G21](#g21) | `_FakeState:20`；`test_catalog_lists_known_vendors:31` |
| [test_provider_key_encryption.py](../tests/test_provider_key_encryption.py) · 149 | R13；隔离 fixture/假适配器 → 10 个行为用例 → 断言公开结果与失败边界 | 保留；保留落盘密文/内存明文；补主密钥丢失的明确恢复；关联 [G08](#g08)、[G09](#g09) | `_FakeState:17`；`_isolate_crypto:23` |
| [test_provider_profile_routes.py](../tests/test_provider_profile_routes.py) · 111 | R12/R13；隔离 fixture/假适配器 → 5 个行为用例 → 断言公开结果与失败边界 | 保留；保留单资源段与脱敏契约，作为其他路由模板；关联 [G19](#g19) | `_JsonHandler:11`；`_ProviderProfileState:27` |
| [test_runtime_storage_maintenance.py](../tests/test_runtime_storage_maintenance.py) · 954 | R11/R13；隔离 fixture/假适配器 → 23 个行为用例 → 断言公开结果与失败边界 | 保留；保留递归引用/日志留存/精确清理；提取隔离 fixtures；关联 [G09](#g09)、[G20](#g20) | `_write_log:23`；`test_local_runtime_log_stats_exposes_newest_and_largest_paths:29` |
| [test_scheduler_terminal_status.py](../tests/test_scheduler_terminal_status.py) · 304 | R07/R11；隔离 fixture/假适配器 → 12 个行为用例 → 断言公开结果与失败边界 | 保留；保留退出码、停止、增量日志；新增资源占用竞争用例；关联 [G13](#g13) | `_runtime_log_path:12`；`_SchedulerState:20` |
| [test_transfer_path_safety.py](../tests/test_transfer_path_safety.py) · 140 | R08/R13；隔离 fixture/假适配器 → 6 个行为用例 → 断言公开结果与失败边界 | 保留；保留 rsync 参数/敏感路径/冲突；补 run 归属和下游依赖；关联 [G14](#g14) | `_remote:14`；`test_build_transfer_command_blocks_sensitive_sources:34` |
| [test_workflow_data_contract.py](../tests/test_workflow_data_contract.py) · 129 | R05/R09；隔离 fixture/假适配器 → 10 个行为用例 → 断言公开结果与失败边界 | 保留；保留映射缺口/前向引用；统一解析后做等价差异验证；关联 [G10](#g10) | `test_context_output_resolves_when_present:12`；`test_context_output_missing_returns_none:21` |

### 用户本地新增测试（未纳入本次提交）

`tests/test_tmux_transfer_regressions.py`：2 个测试函数（参数化后 3 个用例），覆盖 rsync 显式 SSH 端口、local/SSH tmux 尾部空行；对应用户原有修复。保留在工作区，未当成清理提交的回归证据，未删独有断言。后续提交这些修复时再纳入正式文件台账。

### 本地 smoke 脚本：40 个，逐文件保留价值判断

这些是当前工作区的本地文件，不作为正式部署依赖；未逐个运行，也未验证当前私有环境是否齐全。以下“保留/候选合并”是交接计划，不是本轮删除授权的替代证据。

| 本地文件 | 输入 → 验证输出 | 结论与下一步 |
| --- | --- | --- |
| `dev_work/smokes/phase3_agent_runtime_observe_smoke.py` | 隔离本地服务、fake Provider/Job 与浏览器 → 核心执行、事件或证据闭环 | 保留；扩为按行为命名的核心 smoke，不删除独有场景。 |
| `dev_work/smokes/phase4_chat_stream_smoke.py` | 隔离本地服务、fake Provider/Job 与浏览器 → 核心执行、事件或证据闭环 | 保留；扩为按行为命名的核心 smoke，不删除独有场景。 |
| `dev_work/smokes/phase4_job_log_delta_smoke.py` | 隔离本地服务、fake Provider/Job 与浏览器 → 核心执行、事件或证据闭环 | 保留；扩为按行为命名的核心 smoke，不删除独有场景。 |
| `dev_work/smokes/phase5_full_workflow_smoke.py` | 隔离本地服务、fake Provider/Job 与浏览器 → 核心执行、事件或证据闭环 | 保留；扩为按行为命名的核心 smoke，不删除独有场景。 |
| `dev_work/smokes/phase5_remote_full_workflow_smoke.py` | 所选 SSH 主机、隔离工作区与浏览器 → 远程执行/清理事实和归属证据 | 保留远程门禁；未配置时记 skipped，不可当通过。 |
| `dev_work/smokes/phase5_remote_mixed_agent_job_smoke.py` | 所选 SSH 主机、隔离工作区与浏览器 → 远程执行/清理事实和归属证据 | 保留远程门禁；未配置时记 skipped，不可当通过。 |
| `dev_work/smokes/phase6_7_config_center_smoke.py` | 受控页面/脚本依赖/注入事件 → 7 config center 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase6_agent_health_smoke.py` | 受控页面/脚本依赖/注入事件 → agent health 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_app_navigation_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → app navigation actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_app_status_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → app status actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_job_form_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → job form actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_monitoring_filter_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → monitoring filter actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_output_terminal_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → output terminal actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_process_stop_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → process stop actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_replay_preview_smoke.py` | 受控页面/脚本依赖/注入事件 → replay preview 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_admin_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server admin actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_list_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server list actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_list_drag_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server list drag actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_list_popover_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server list popover actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_offline_toggle_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server offline toggle actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_resource_overlay_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server resource overlay actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_server_selection_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → server selection actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_task_plan_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → task plan actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_template_canvas_search_smoke.py` | 受控页面/脚本依赖/注入事件 → template canvas search 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_template_review_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → template review actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_transfer_surface_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → transfer surface actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workflow_template_node_list_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workflow template node list actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_action_surfaces_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace action surfaces 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_agent_tool_toolbar_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace agent tool toolbar 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_chat_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace chat actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_form_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace form actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_help_popover_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace help popover actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_history_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace history actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_launcher_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace launcher actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_run_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace run actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase7_workspace_shell_actions_smoke.py` | 受控页面/脚本依赖/注入事件 → workspace shell actions 的装配/交互结果 | 候选合并到所属界面 smoke；先核对独有断言与对应正式测试，不直接删除。 |
| `dev_work/smokes/phase_runtime_maintenance_smoke.py` | 隔离本地服务、fake Provider/Job 与浏览器 → 核心执行、事件或证据闭环 | 保留；扩为按行为命名的核心 smoke，不删除独有场景。 |
| `dev_work/smokes/phase_runtime_remote_maintenance_smoke.py` | 所选 SSH 主机、隔离工作区与浏览器 → 远程执行/清理事实和归属证据 | 保留远程门禁；未配置时记 skipped，不可当通过。 |
| `dev_work/smokes/phase_search_provider_smoke.py` | 显式 Provider/Profile 或受控 endpoint → 真实模型/搜索契约、来源与错误 | 保留供应商验收；确定性 endpoint 与真实供应商分开记录。 |
| `dev_work/smokes/provider_smoke.py` | 显式 Provider/Profile 或受控 endpoint → 真实模型/搜索契约、来源与错误 | 保留供应商验收；确定性 endpoint 与真实供应商分开记录。 |

### 配置、公开样例与测试入口

| 文件 | 检查结论与解决方向 |
| --- | --- |
| [config/servers.toml](../config/servers.toml) | R01/R13；保留本地默认与 SSH 发现，属于非私密启动样例，不混入个人主机。 |
| [config/user_servers.example.toml](../config/user_servers.example.toml) | R01/R13；保留覆盖模板；后续输入校验统一，实际用户覆盖仍忽略。 |
| [config/secrets.example.toml](../config/secrets.example.toml) | R13；保留 SSH 密码格式示例；不等于推荐明文密码，真实 secrets 不入库。 |
| [data/agent_definitions.json](../data/agent_definitions.json) | R03；保留公开 Agent 目录；与真实 adapter/Provider 绑定校验，关联 G10/G11。 |
| [data/tool_definitions.json](../data/tool_definitions.json) | R03；保留工具 schema；明确建议/真实读取/异步执行级别，关联 G11。 |
| [data/workflow_templates.json](../data/workflow_templates.json) | R02/R05；保留起始链；顺序执行与拓扑预览分开，新增 Transfer 后版本化。 |
| [pytest.ini](../pytest.ini) | R14；保留 testpaths=tests 与 scratch 排除；不要把私有 smoke 混入确定性门禁。 |

### 台账完整性与维护

正式代码台账包含 309 行，一文件一行；另有用户本地新增测试 1 项、本地 smoke 40 行；配置/公开数据/测试入口 7 行。代码路径集合来自当前实际源码树，不按历史目录猜测。新增、删除或改职责时同步对应行和 G 问题状态；不把未跑过的场景写成已验收。
<!-- FILE_AUDIT_END -->
