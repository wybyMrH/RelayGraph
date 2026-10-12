# 第二部分：现状、问题与逐文件审查

审查日期：2026-10-13。目标基线为[第一部分](project-spec.md)，解决顺序为[第三部分](next-stage-plan.md)。本文随代码变化更新，不能作为永久完成证明。

## 1. 范围、证据等级与结论

当前正式代码台账覆盖 288 个文件：168 个后端 Python、118 个前端 JavaScript、HTML/CSS 各 1 个；配置/公开数据/本地验证入口另列。用户已在 42960ac 删除远端 24 个历史测试文件并忽略 tests/，旧本地 smoke 也已清理，本文不再把它们列为现存文件。不读取真实 Provider 密钥，不把运行数据、缓存或第三方包计入正式代码。

N00C/N00D 已完成文档收敛、重复代码清理和原有业务改动整合；N01 随后完成本机执行引擎选型；N02 已把完整计划、attempt 和提交记录接入现有工作流入口。样机/验证只留本地 dev_work/。LangGraph 已在 N03B2b 接入单 Job，N03B2c1 接入一个 Job → 无工具报告 Agent；G01 的更长混合链、G02 子任务续跑和 G09 剩余恢复边界仍开放，G03 的新工作流失败覆盖路径已退出。N03J0/N03A0/N03A 分别收紧 Job 启动状态、保留明确执行方式、接入浏览器稳定提交身份；这些小片不等于 Job → Agent 已正确等待。N03B1 已完成实际计划/前缀门禁；默认自动回填路径的过程复验另发现 G23；N03J1a 已阻止 cwd/环境前置失败后的命令，N03J1b 已退出未配环境就回填 rg-* 名的路径。两节点 shell CPU 链是旧路径的历史验收；当前新计划仅接受单 Job 或 Job → 无工具 eval.report Agent，其他多节点计划明确拒绝。

N03B2a 已补齐唯一运行依赖清单和 Python 3.12/3.13 隔离启动验证（G08），承接 N00A 的部署基线职责；只增加依赖声明与文档，不改变上述生产等待缺口。源码仍为 288 个文件，公开配置/数据/依赖与验证入口现为 9 项；N03B2b 随后完成单 Job 持久受理/等待，旧同步推进已删除；N03B2c1 已交付本次结果交接；按最新用户要求先补 N13A/N13B1 独立前端阶段，再做 N07A 报告正文落盘与验证，仍不接 Agent 工具/子任务。

逐文件审查通过源码文本、Python AST、函数/调用职责、导入、状态/副作用分支和前端公开接口进行静态核对；关键路径另外做内存/临时目录复现。**静态覆盖全部文件不等于逐分支动态验证，不等于读完十万行后保证没有遗漏。** 每个文件在后面的台账单列；未发现独立问题的文件不会被硬凑成缺陷。

证据等级：E1=审查时已运行/隔离复现（历史复现不代表本轮重跑）；E2=具体源码路径确认；E3=设计风险，需后续实验；E4=需求能力尚未完成。类别为能力缺口、冗余/职责重叠、伪成功或语义误导、可靠性/安全风险。一个问题可以有多个类别。

已有成果：监控、tmux Job、资源等待、rsync、浏览器终端、工作区与配置中心、受控 runtime 工具、输出校验、SSE、执行包、run/日志保留、模板诊断与迁移都有真实代码，历史曾有相应用例。最大问题是“这些组件各自可用”尚未充分等于“异步工作流完整且可恢复”。

优先级：P1=可导致错误执行、漏执行、证据丢失或控制失效；P2=正常操作受阻、结果误导、重要设计缺口；P3=后续体验/维护改进。未发现需紧急停用全项目的 P0 证据。

## 2. 问题登记与解决方向

<a id="g01"></a>
### G01 · P1 · Job → Agent 无完成屏障

- 对齐 R06/R09，类别：能力缺口、执行风险，证据 E1。
- 原 workflow_runner.py.run_workflow_sequence 提交 Job 后继续遍历，后续 Agent 没有等待 previous_job_id；本次输出也没有进入 previous_step_output。N03B2b 已删除该同步推进路径；N03B2c1 在同一图接入一个 Job → 无工具报告 Agent。
- 复现 run.command → eval.report(Agent)：Job 返回 queued 时报告 Agent 已被调用，previous_output=None。输入门禁可能改为阻塞，但仍不是等待后续跑。
- N03B2c1 已实测 Job 成功后才调用一个无工具 eval.report Agent；失败/停止跳过 Agent。本次 output_value 绑定 run/step/attempt/Job，带最多 8192 字节日志及截断证据；原引用内核解析 $prev/$context，不合入工作区历史 outputs。该最小链的屏障/结果交接已完成；Agent 带工具、更长链和子任务仍不支持，G01 不整体关闭。
- 方案：协调器持久记录 waiting_on，在任务成功且本次输出可用后推进；失败/停止传播。不要往 HTTP 请求里加轮询 sleep。验收 Job → Agent、Job → Agent → Job，确认报告读取本次结果。

<a id="g02"></a>
### G02 · P1 · 子任务后续跑缺失，完整工作流可被算成部分完成

- 对齐 R06，类别：能力缺口、伪完成，证据 E1/E2。
- 原 workflow_runner.py.run_workflow_sequence 遇到 pending_agent_runtime 后直接 break，没有后续游标。N03B2b 已删除旧推进器，但 Agent 子任务续跑仍未实现。N02 前 run_records 只以已有 steps 计算终态与分母；完整计划投影不能单独证明续跑。
- 两个 Agent 的复现只留下第一个 step；子任务结束后按现有计算得到 done、1/1、100%，第二个 Agent 未运行。历史用例只证明阻止提前执行，未证明完成后的恢复。
- N02 已持久化完整计划，未执行步骤仍为 pending，进度分母不再缩小；子任务生产续跑仍待 N04，历史 JSON 没有凭空补出计划。
- 方案：先冻结完整计划，再为每个节点记录等待/尝试；完成事件恢复推进。分别处理子 Job 与子 run，重复通知不重复启动，服务重启能恢复。

<a id="g03"></a>
### G03 · P1 · 提交异常替换已记录步骤（N02 新工作流已修复）

- 对齐 R06/R07/R11，类别：证据丢失风险，证据 E1/E2。
- 原 workflow.py 的异常分支用 steps=[failed_step] 替换整个步骤表；该分支已删除。新运行在副作用前保存完整计划，当前失败写进对应 attempt 和 submission_error，保留既有 Job 引用、其他 attempt 和未提交步骤。
- 解决路径已接入现有 run/update/query 入口；中断后能从领域账本重建 JSON 投影，不靠测试补记录。原历史记录若已被旧代码覆盖，无法自动恢复，不能补造证据。
- 下一步只复用 N02 的记录接口，N03 不再维护一份独立失败步骤表；Job 等待/续跑仍在 G01/G02。

<a id="g04"></a>
### G04 · P1 · deadline/cancel 在最后一次调用后可失效

- 对齐 R09，类别：控制风险，证据 E1。
- agent_executor.py:303–407 只在循环开头检查；Provider 返回后可直接 success 或继续工具副作用。llm_client 使用独立网络超时，未消费 Agent 剩余预算。
- 复现总预算 10ms，假 Provider 30ms 后返回并设置取消信号，结果 success=True、timed_out=False、cancelled=False。
- N03B2c1 仅对单次无工具报告启用单调时钟和调用后检查，并禁用 stream 失败后的第二次 fallback；真实延迟响应及取消 HTTP 验收通过，取消请求时仍显示 running，返回后才记失败/停止。网络调用不能立即中断，通用多轮 Agent 及网络剩余预算未解决，G04 保持开放。
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
- N03B2c1 报告回答不走 apply_final_answer_output/artifact.write/report.write；≤4000 字回答保存为 attempt 的 inline-answer 证据，无 artifact、file_verified=false，交付闭包 report.incomplete=true/status=warning。超过 4000 字显式失败，不把截断摘要当正文；JSON 无法解析也失败。没有落盘报告，通用旧声明路径仍存在，G06 未关闭。后续 N07A 只保存并验证这条链的本地正文；当前先补前端欠账，顺序见第三部分 2.14。
- 本次实际网页点击确认：记录页可看步骤、打开 Job 日志并下载结构化导出；workspaceRunStepItemMarkup 不提供当前 output_value.content 的独立正文阅读入口。演示材料另存正文仅作证据，不算产品报告文件交付；N07A 需落实正文读取与实物验证。
- 方案：ArtifactStore 保存正文或受控文件，返回可验证引用；区分 declared/written/verified；正文超过限额显式拒绝或另存。执行结束和交付完整度独立展示。

<a id="g07"></a>
### G07 · P2 · 失效挂载点导致文件浏览整体失败

- 对齐 R04/R08，类别：可靠性风险，证据 E1。
- utils.py:179–205 在 /mnt 枚举时 child.is_dir() 未隔离 OSError；本机 /mnt/g 的 Errno 19 使安全测试失败。
- 方案：逐根目录/条目容错，区分 unavailable 与不存在；测试模拟坏挂载，保证其他路径可浏览。复用同一根目录发现逻辑，不在前端绕过失败。

<a id="g08"></a>
### G08 · P2 · 运行依赖缺声明（N03B2a 已补齐部署基线）

- 对齐 R14，类别：部署缺口，证据 E1/E2。
- 原 secrets_crypto.py 顶层导入 cryptography，隔离第三方 site-packages 后启动失败；缺少公开依赖声明。N03B2a 已新增唯一 requirements.txt，固定 cryptography 49.0.0、LangGraph 1.2.7、langgraph-checkpoint-sqlite 3.1.1，README 退出单独手装 cryptography 的入口。
- 两个不共享系统 site-packages 的新 venv（Linux/WSL、Python 3.12.3/3.13.5）均从公开清单安装、pip check、Fernet 内存 round-trip、正式服务 import 和真实 HTTP 启动通过；SQLite saver 分别在三个进程中完成暂停落盘、恢复、再次读取。依赖声明/上述环境启动缺口已关闭，不能推导生产等待恢复已实现。
- 过程边界：3.12 系统缺 ensurepip，先在隔离环境补 pip；本地验证脚本首次 import 因脚本目录不同失败，修正为仓库执行上下文，正式服务始终用仓库根目录的原启动命令。解析出 44 个运行包，直接版本固定但间接依赖未锁定；LangSmith 无标志/上下文时 tracing 默认关闭，继承环境可启用，本轮显式关闭。
- Python 3.11、其他系统/架构、离线安装和系统工具缺失诊断未验证。pytest/Playwright 不进入运行清单，LiteLLM 采用时再补实际依赖；不新增第二份安装体系。许可、过程与下一片见第三部分 2.10。

<a id="g09"></a>
### G09 · P1 · 缺少可靠执行检查点与提交一致性

- 对齐 R06/R11/R13，类别：恢复能力缺口、持久化风险，证据 E2/E3。
- persistence.py 保存 jobs/workspaces 等独立 JSON；utils.write_json 可原子替换单文件，但不能对多文件与 tmux 副作用提供事务。read_json 在 JSON 损坏时返回默认值，可能把损坏误当首次初始化。agent_runtime.py 取消注册仅在内存。
- N02 的真实 workflow 入口已接 RunStore/提交适配器，先存意图、排队回执再公开。N03B2b 已接入单 Job 的 LangGraph interrupt/恢复，复用 run 锁和原 create_job；图检查点绑定 run_id/plan_hash，attempt 记录核对事实，查询不自行判完成。检查点只读检查通过才交给 saver 写入；损坏保留并 blocked。没有回执的提交保持 reconciling，不自动重提；丢失检查点只对这一片冻结单 Job 计划通过稳定回执核对恢复，不套用到旧 Agent。N03B2c1 延续 B2b engine/submit-observe-wait 节点，实际旧版等待检查点可恢复；新报告先在 attempts 表 CAS claim，持久 execution_id，未知调用 blocked、不自动重放，已记录结果复用。真实硬退出覆盖 claim/response/result/pending-writes 窗口及缺检查点恢复；next 为空但 tasks 有 pending writes 时继续结算，不能误判结束。取消传播、多实例队列及启动未知窗口仍开放。
- 普通 create_job 仍非通用幂等 API，不能绕过适配器。现有 Provider 密钥与主密钥仍在 data/，兼容迁移归 N00E。
- N02 新增存储 schema/hash 校验、损坏记录明确报错、单机 run 文件锁；当前只支持一个服务负责 JSON Job 队列。新账本 run/Job 回执暂受保护，不被 JSON 条数裁剪；事务归档与孤立账本处理待 N14。
- N03 真实过程复验发现 start_job 可让旧调度快照再次启动已 running/终态 Job：一份 compute 回执对应 count=2。N03J0 仅收紧启动状态门禁；30 秒启动占用及跨进程未知窗口仍待处理，不能用提交去重证明进程一定只启动一次。
- N03A 已验收：两个直接运行入口共用浏览器提交身份，稳定键延续 N02，刷新/未知失败不自动生成新键。真实联调及限制见第三部分 2.6；不关闭 G01 等待恢复。
- 方案：N03 落实已选的单一推进权威，复用已有计划/attempt/幂等键与核对适配器。配置目录仍可 JSON。坏文件隔离与版本迁移另设小切片，不能一次迁移全部历史。

<a id="g10"></a>
### G10 · P2 · 同一输入引用和默认目录多处维护

- 对齐 R02/R05/R09/R14，类别：冗余、语义漂移，证据 E2。
- 原 orchestration/input_mapping.py 的 context_ref_value 与 automation/contracts_pkg/context.py 的 workspace_context_ref_value 归一化 AST 相同；N00C 已合并到 context_refs.py，原导入名保留，135 组取值输入前后等价。仅完成底层字典/列表取值去重，运行/静态引用规则仍分别维护；前端 node_catalog/defaults/catalog_data 的目录副本也仍存在，G10 未关闭。
- N03A0 过程发现：finalize_agent_executable_nodes 原来把明确 system/human 的可 Agent 节点改成默认 Agent，自动回填后 CPU Job 被无关 Provider 阻断。修复只保留明确 mode/agent_id，原缺绑定的 Agent 仍补推荐；不创建第二套默认组件。已被旧逻辑覆盖的历史执行者不凭空还原。
- 本次可视化复验新增 E1/E2：独立 Agent 若使用内置 reporter 角色，即使显式 tools=[]，backfill_default_agent_tools 仍按角色补回工具，默认 auto_apply 后被 B2c1 无工具门禁拒绝（HTTP 409）。使用独立自定义角色可经原门禁运行；这属于默认配置覆盖显式权限意图，未修复，不能称内置报告角色开箱即用。后续需区分未配置与明确空列表，并验证历史默认配置的兼容。
- 方案：统一纯引用解析器，静态校验与运行时校验共享规则但传入不同上下文；由后端提供版本化目录，前端只留必要无服务草稿默认。先锁定空值、前向引用、历史输出与 $prev 语义，再替换调用者；不把不同职责的校验一律合并。

<a id="g11"></a>
### G11 · P2 · 工具注册、建议、读取与真实执行混在一个实现标签下

- 对齐 R03，类别：能力缺口、语义误导，证据 E2。
- repo.search 汇集 query/roots/hints，未实际搜索仓库；log.read 返回最新日志入口而非正文；notify.user 返回载荷，schedule.plan 是 dry_run。gpu.allocate 的实际 callback 返回 plan_only=True、persisted=False，并不写绑定；旧本地文档“已绑定”不准确。
- N02 发现完整 CPU 工作流被固定 Starter Chain 要求加入 dataset.find/env.infer/gpu.allocate；N03B1 已退出这条固定必需路径，正常两节点 shell CPU 链无需这些节点或 Provider。实际声明的数据依赖仍校验，命令、显式主机和引用错误仍拒绝；工具建议/真实执行标签问题保持开放。
- AgentExecutor 缺少 tool_executor 时返回 [Simulated]，若当生产路径使用可能让模型把模拟当真实。自定义工具 CRUD 也不等于自动产生适配器。
- 方案：能力目录明确执行级别与真实 adapter_id；无适配器只能配置/诊断，不能进入可执行包。建议型工具保留并如实命名，不必为每个名字补大型实现；验证调用方确实需要正文/通知后再开发。

<a id="g12"></a>
### G12 · P1 · Agent 文件发现工具缺统一远程读取语义

- 对齐 R04/R10，类别：能力缺口、错误证据风险，证据 E2。
- tools/workspace_executor_pkg/read_tools.py、helpers.py、discovery.py 用本机 pathlib 扫描/读取；浏览器文件工具已有 SSH 路径，二者不是同一适配入口。远程工作区可能读不到文件或读到本机同名目录。
- Job 形式的 dataset.find 还会把固定默认根加入扫描，即使已经明确本次数据目录；这是多余环境依赖，N03 最小链不应靠执行无关扫描取得就绪，范围收敛随 N08 核对。
- _read_text_file 先 read_text 整个文件再截取，响应限额并非 I/O/内存限额。
- 方案：HostFileAdapter 统一本地/SSH stat/list/read/probe；强制 host_id；有界读取、禁止敏感路径，失败返回 unavailable/permission 而非伪造 missing。复用已有远程探针，不复制一套 shell 脚本。

<a id="g13"></a>
### G13 · P1 · GPU 选择缺本服务内的原子预留

- 对齐 R01/R07，类别：资源竞争风险，证据 E2/E3。
- jobs_pkg/execution.py.find_gpu 只读最近 statuses；scheduler.py 一轮遍历多个 queued Job，启动一个任务后没有在选择器中扣除预留。启动幂等测试只保护同一个 Job，不保护多个 Job 选择同一 GPU。
- N02 修复本地 CPU 提交的目标不一致：执行包/来源记录统一 gpu_index=none，避免 gpu_policy=cpu 时因包为 auto、任务为 none 被门禁拒绝；没有修改 GPU 选择、占用或预留语义。
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
- N03B1 按实际计划编译门禁和包，保留 warning 并允许提交；静态引用错误复用 workflow_contract。N03J1a 已挡住实际激活失败后的命令，N03J1b 已退出无配置环境名回填；发现/预检投影仍可能建议无关数据/环境，未把所有视图统一为 ReadinessResult。
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

- 对齐全部需求，类别：验证缺口、历史维护冗余，证据 E1/E2。
- 历史阶段测试和本地 smoke 已由用户清理；源码中的 G01–G06 关键交接缺口仍在。N01 有隔离引擎样机验证，但正式工作流尚未接入，不能作为生产生命周期已验收的证明。后续按切片生成本地验证，不能用没有脚本代替通过。
- 方案：按行为迁移测试所有权，复用隔离 fixtures；重复测试只有在证明同一输入/行为/失败模式已被覆盖后删除。helper 装配测试可精简，但路径、脱敏、幂等、保留、退出码与执行转移必须保留。正式文档收敛为三部分，旧本地计划退出规则来源；被用户清理的脚本需要时从 Git 历史读取有效断言，不恢复无用阶段组织。

<a id="g23"></a>
### G23 · P1 · 启动前置事实与环境默认混淆（新运行两项已修复，旧配置/退出覆盖限制保留）

- 对齐 R07/R13，类别：错误执行、伪成功，证据 E1/E2。
- N03B1 补充真实 HTTP/tmux 复验：未配置 env 的两节点 CPU 链在 auto_apply=true 后生成 rg-* 环境名；两份日志均有 EnvironmentNameNotFound，计算和报告仍运行，Job/run 显示 done。功能产物虽存在，过程验收明确失败，不能计作默认路径完整通过。
- 原 infra/shell_pkg/jobs.py.build_job_script 只设置 pipefail；cd 与 conda_bootstrap 的失败不阻止命令。N03J1a 在相同唯一入口检查前置状态，失败记录 prerequisite_failed 阶段及原非零 exit_code，原 monitor 得到 failed；真实缺 cwd/命名环境/路径环境三项均验证 payload=0。正常系统 Python 与已有 venv 保留。
- 用户命令若直接执行 shell exit，会绕过既有尾部标记；本轮初始测试 exit 0 仍由 monitor 记为缺标记失败，不能算成功。这是退出标记覆盖限制，未在前置屏障切片扩成 trap/任意 shell 退出重构。
- N03J1a 的 6 项真实 HTTP/tmux + 7 项 shell 契约已完成；N03J1b 再退出默认生成环境名的分支。真实 Chromium 默认运行按钮 → 两节点 shell CPU Job → 实物报告 → 服务重启/原键核对通过，未配数据、环境安装或 Provider；5 项默认配置契约及明确存在/不存在环境的真实入口也通过。
- 新运行的前置失败/默认回填路径已修复；历史 rg-* 名无来源不能自动判为错误并清除，需用户通过正常实例编辑入口明确修改环境。shell 提前 exit 标记限制保留；不把两项小片写成 Job 全生命周期已无缺口。

<a id="g24"></a>
### G24 · P2 · 网页实时更新重复保留同一步骤占位

- 对齐 R06/R12，类别：状态呈现错误，证据 E1/E2。
- 本次 Chromium 实际点击运行 Job→报告链，后台始终两步、计算实物计数 1；页面从未绑定任务到 Job/Agent ID 的过程中，compute/report 各保留一份 pending 占位。正常结束时实时 DOM 有 4 行，既显示已完成又显示未运行；重新打开页面的完整快照恢复两行。
- workspace_run_state_merge.js 的 stepMergeKey 优先 job_id/agent_execution_id，再退回 node_id+index；身份随绑定变化，mergeSteps 又追加旧 key，导致占位未退出。此前仅检查页面内存中的 run 终态或进度，没有断言实际 DOM 行数，未覆盖这个缺陷。
- 方案：单独交付稳定 step/attempt 身份的合并修复，保留历史记录和实时事件边界；对待执行→绑定任务→终态、Agent 绑定及旧记录做真实浏览器验证。不能用强制刷新、隐藏重复行或删除测试来代替修复。归 N13A 首片处理；这是 N03B2c1 后补做的独立前端阶段，验收后再迁移运行阅读视图（N13B1），不与报告落盘混做。

<a id="g25"></a>
### G25 · P2 · 成功 Agent 的完成说明被写成错误

- 对齐 R09/R12，类别：错误字段语义与页面误导，证据 E1/E2。
- 本次成功报告的服务响应同时含 status=done 与 error="agent node executed"；页面将这句成功说明显示为红色错误。报告正文/真实计算结果有效，不能把这个红字解释为模型失败，也不能宣称展示完全正确。
- node_runner.py 成功 StepResult.detail 为完成说明；run_steps.py.workspace_run_step_from_agent 无条件把 reason/detail 写入 error。需在独立 API/投影契约小片区分成功说明与失败原因，验证失败、取消、超时和历史记录读取；不靠前端隐藏 error 掩盖源字段错误。本轮仅登记，不混入报告文件落盘。

<a id="g26"></a>
### G26 · P2 · 配置与运行界面混杂，多层容器挤压主要内容

- 对齐规格§3/C13/R12，类别：功能入口错位、布局与可用性缺口。证据分开记：上轮真实浏览器“打开日志”截图的拥挤/空白是 E1；本轮 HTML/调用/样式检查是 E2；其他视口表现尚未动态验收。不是已经修复或完成全站视觉检查。
- 用户指出本地展示的 success-log.png 中“实例快照配置”层层嵌套、条目被挤压并有空白。web/index.html 的 workspaceProjectConfigDrawer 把实例编辑、多个子折叠区和 workspaceRunDetails 包在一起；配置区还有全局运行概览。查看日志/结果要穿过配置入口，页面职责与规格§3不一致。
- web/core/app.js 还按概览面板可见性调度刷新（executionOverviewPanelVisible/schedule 相关调用），并装配实例抽屉/运行区；web/styles/styles.css 叠加 drawer、sticky/高度等规则。结构和样式共同参与，不能只加一条 CSS 覆盖或把 DOM 隐藏算完成。配置概览的 renderer/actions 是仍有消费者的迁移对象，不能因文件名含 config_center 就直接删掉。
- 方案分片：N13A 先保证步骤事实没有重复；N13B1 只把当前实例的运行列表/详情/日志/导出移到驾驶舱的独立运行阅读区，配置保留编辑和版本信息；N13B2 再移全局运行概览，N13B3 单独精简实例编辑层级。每片先做信息/交互草图，使用已评估设计 skill，真实浏览器核对入口、宽度/滚动、长文本、空/失败状态及选择保持。不是一次重写整个前端，也不更换静态脚本技术栈。
- 消融要求：列出每个旧入口、事件绑定和刷新调用；相同 run 固定输入下比较状态、行数、按钮副作用次数和导出引用，验证新入口后删除对应旧展示。配置诊断保留；运行状态不复制到配置中。G15 的组合根/样式债务与本条相关，但不能借布局片顺手抽取全站控制器。

## 3. 验证边界与阶段状态

历史审查对 G01/G02/G04/G05/G06 做过隔离复现，G03 为源码确认；G07 的失效挂载问题仍未修复。旧测试被移出远端不改变这些问题的状态。本地原始调查结果与旧 smoke 已清理，不把历史运行声明当成本轮完成证明。

N01 的场景检查、依赖锁文件、硬退出恢复记录和本地 CPU 实物演示保存在 dev_work/n01/，不上传脚本或执行结果。正式决策、接口草案和旧路径去向见第三部分 2.4。该样机不访问现有 data/、真实密钥、SSH、GPU 或联网 Provider；不证明生产 runner 已具备等待/恢复，也不证明真实模型请求可 exactly-once。

### N00C：本次有证据的清理

| 清理对象 | 删除/收敛依据 | 保留行为与后续边界 |
| --- | --- | --- |
| 七份旧正式文档 | 信息已归入三部分、README、AGENTS；映射见文档索引 | Git 保留历史，不留重复规则源 |
| workspace/automation.py | 与 automation/ 同名，Python 正常导入选择包；无文件路径加载者 | 保留包的全部公开导出和调用路径 |
| LLMClient.simple_chat | 全仓代码、测试、smoke、文档只有定义；是 chat 的未使用包装 | Agent/Provider 继续调用 chat/chat_stream，不改变协议 |
| TerminalsMixin.terminal_list | 全仓只有定义；HTTP 路由没有会话列表入口 | 保留现有会话打开、读写、信号和关闭 |
| 两份 context_ref_value | 函数 AST 一致，字典/列表/缺失/空路径等 135 组输入结果和对象引用等价 | 唯一实现放 context_refs.py；旧导入名是别名，静态/运行时规则不在此轮改写 |
| CSS 和其他门面 | 尚无等价替代或无消费者的充分证据 | 保留；不按同名/短文件直接删除 |

本切片只清理无消费者或完全相同的实现，不代表完成 G10/G16，也不提前实施 N01–N17。N00C 当时未删除失败测试或改变断言；后续用户清理测试不构成 G07 已修复的证据。

### N00D：原有任务、传输与输出改动整合

本次按用户要求整合已有业务改动，不扩展下一阶段的工作流功能：

| 对应需求 | 当前变更 | 边界与保留决定 |
| --- | --- | --- |
| R07 · 进程停止 | 正常权限优先发信号，失败后使用 sudo -n；用 ps 状态核对存活，不把 sudo 无权限误判为已退出 | 保留原有非本人/归属未知进程确认入口；sudo 不等待密码；进程仍存活就报失败 |
| R08 · SSH 文件传输 | rsync 的 SSH 参数包含 ServerConfig.port | 复用原 SSH config/密码参数；没有另建传输协议或队列 |
| R07/R12 · tmux 输出 | 默认宽度改为 160 列，显示快照去掉尾部空行/空白 | 保留内部换行/缩进；这是显示快照，原日志文件不改写 |
| R11 · 失败证据 | 非零退出码或缺少退出标记时保存最多 65536 字符的失败日志尾部 | 复用现有快照 schema；短日志不虚报字符截断，行窗口与字符上限分开标记；不是完整归档 |
| R12 · 错误呈现与布局 | transfer 的错误优先于缓存进度提示；缩小输出区和标签宽度并更新 CSS 缓存版本 | 保留进度条；错误文字继续 HTML 转义；不重构前端控制器 |

本轮验证脚本、截图、命令输出与结果说明只保存在本地 dev_work/，不纳入远端。实际验证状态在交接时报告；未用本轮整合来关闭 G01–G22 中尚未解决的功能缺口。真实 SSH 主机和跨用户 sudo 权限需在对应环境验收，受控替身不代表远程通过。

### N02：完整计划、attempt 与提交证据

正式行为与请求/查询契约见第三部分 2.5。新工作流的执行证据以 SQLite 为准，JSON runs 是兼容投影/事件缓存；历史 JSON 保持读取，不承担新 run 的计划或恢复游标。N02 当时保留原顺序 runner；N03B2b 已替换为单一图推进器。

删除了两条“单条失败覆盖整个 run”的路径，合并提交与启动核对的 Job 身份检查，去掉相同结果反复写库和同一调用内的重复投影读取；N02 当时保留旧 runner 与历史读取；N03B2b 已删除无剩余调用者的旧 runner，历史记录仍只查询/核对。

正常验收走真实 HTTP、门禁、调度器与 tmux；重复请求需要显式稳定 request_id，N02 当时客户端未携带该键，现已由 N03A 接入两个直接运行入口，其余操作仍按第三部分 2.6 的边界处理。故障注入只用于异常/硬退出边界，正常路径不修改终态、不关闭门禁。测试脚本、真实执行结果、超时排查与消融记录均在本地 dev_work/n02/，不提交远端。

N02 不证明 Job → Agent 已正确等待，不证明 Agent 子任务自动续跑，也不证明任意外部副作用 exactly-once。默认完整链的冗余节点、非必要目录扫描和单机保留策略仍如实登记，不能拿完整链成功掩盖最小入口缺口。

### N03B1：实际计划门禁（已完成）

提交检查和执行包使用实际可执行节点/所选前缀。固定 Starter Chain 必需项、system/human 的无关 Agent 要求、无条件数据根要求已退出；保留声明的数据需求，推断出的无关目录不能替代它。包脚本只保留当前节点的命令预览并按计划排序，warning 不再等于不可执行。Job 的命令/主机 payload 和真实 Agent 的绑定/路由仍逐节点检查。请求显式 executor_mode=job 时仅改变本次计划投影，不改实例的 Agent 绑定；另一个真实 HTTP 检查已验证该兼容行为。

显式非法引用与 Agent 必需输入缺失由已有 workflow_contract 校验进入门禁和包缺项；未消费的自动 shell 映射只作预览警告，shell 的输入仍以实际命令配置为准。保留既有 schema 和历史查询；旧 allow_incomplete_execution_package 不再绕过硬错误，重复请求仍先核对冻结 run。这里未统一所有引用解析，也不证明 Job → Agent 屏障。

实际通过 20 项真实 HTTP/tmux 场景和 11 项静态/配置契约：两节点 CPU 计算与 shell 报告、重复/重启请求、前缀隔离、缺命令、未知主机、非法引用、缺 Agent/路由、缺声明数据及兼容参数硬门禁；完整旧链仍可提交。正常最小链用 auto_apply=false，只有隔离本地主机、已有 python3/tmux，没有造数据目录/Provider/环境安装或手填记录。完整旧链的现有 venv 和数据目录属于该旧链显式配置；不是最小链依赖。根 pytest 因无远端测试返回退出码 5，不记通过；实际本地 11 项 pytest 返回 0。

auto_apply=true 的独立真实复验产物成功，但环境激活失败被吞，过程复验退出码 1（G23）。不把它归为正常路径通过，也不把无浏览器/SSH/GPU/真实模型验证写成通过。测试脚本/结果、日志、配置和调查保存在忽略的本地目录；当时唯一下一片为 N03J1a；现已完成，见下文。

### N03J1a：Job 启动前置失败屏障（已完成）

本片只改 infra/shell_pkg/jobs.py，保留单一 Job 服务、启动路径和退出标记消费者。生成 shell 内共用一个结束函数，正常命令和前置失败都写同样结束时间/exit_code；cd 与激活失败再写明确阶段，停止 payload。没有改 Agent、自动回填或调度状态机，也不增加 Job monitor 猜日志规则。

6 项真实 HTTP → 队列 → tmux → 原 monitor 场景通过：系统 Python/已有 venv 正常，各副作用 1；缺 cwd/缺命名环境/缺路径环境均 failed，副作用 0，标记非零；用户 Python 进程退出 7 被正确记录且 Job failed。7 项本地生成脚本契约验证原退出码、引号/空格、激活变量作用域、激活失败和命令自处理失败等语义；激活文件 fixture 仅用于 shell 作用域/错误测试，不冒充 Conda 环境。根 pytest 无用例退出 5，不计通过。

初始测试 payload 显式 shell exit 0 跳过原尾部标记，Job 被报为缺标记失败；原证据保留，本片不宣称解决任意 shell 提前退出。正常/非零退出验证改用实际 Python 子进程退出码，既覆盖目标也不删除前置失败断言。SSH 分支共享脚本入口但真实 SSH 未验证。config 中隔离本机配置、脚本、日志及实物只留本地，第一部分保持稳定。

J1a 完成时下一片为 N03J1b；现已按独立小片完成默认路径，见下文。

### N03J1b：可选环境默认（已完成）

只改 cockpit/payload.py 的现有回填入口：删除无配置时生成 rg-* 环境名并写回 workspace/env_name 的分支。没有选环境就使用主机已有 shell 环境；显式工作区/节点环境继续传播，force 默认回填也不替换工作区明确环境名。不新造环境命名/管理组件，不修改历史 run 和未知来源的旧环境配置。

实际浏览器正常可见运行按钮使用 auto_apply=true、apply_evidence=true、默认 auto：两节点 shell CPU 链通过，计算实物次数 1、报告平方值 49、无页面错误/激活失败。刷新后的服务重启原请求核对同一 run，不重新执行。正常路径只有 python3/tmux 和隔离 config 主机配置，没有临时建数据根、manifest、venv 或 Provider。另一次真实 HTTP 默认链通过；明确存在 venv 保留且 done/计数 1，明确不存在环境保留且 failed/计数 0。

5 项本地配置契约通过，覆盖不生成名、重复应用稳定、明确环境在 force 时保留、旧 rg-* 不猜测删除、节点专有环境保留。compileall、链接/台账/敏感模式/diff 检查通过；根 pytest 无用例退出 5，未记通过。仍未验证 SSH/GPU/真实模型或 Job → Agent；旧配置修正必须显式。测试、截图、配置和原始证据仅在本地。

J1b 交付时下一片是 B2a；B2a/B2b 现已分别完成（第三部分 2.10/2.11）。历史两节点验收不代表当前新多节点计划可运行；B2c 将单独恢复 Job → Agent，不能一次接完整 B2。

### N03B2b：单 Job 持久受理与等待（已完成）

以下记录 B2b 当时的交付边界；B2c1 当前能力见下一节。

以下记录 B2b 当时的交付边界；B2c1 当前能力见下一节。

以下记录 B2b 当时的交付边界；B2c1 当前能力见下一节。

以下记录 B2b 当时的交付边界；B2c1 当前能力见下一节。

POST /run 先保存完整单 Job 计划及冻结 payload，再返回可查询 run；jobs 可以暂为空。原 scheduler 唯一唤醒 LangGraph 的 submit → observe → interrupt/wait 图，仍通过 N02 适配器提交原 Job 队列。终态由真实 Job 事实写入 attempt，查询/JSON/SSE 不越过协调器判完成。图检查点绑定 run_id/plan_hash，数据库在领域账本旁；没有新配置源或第二个 Job 生命周期。自动推进入口还检查已受理但无 Job 的新 run，返回 watch/active_run_ids；真实默认 2 秒调度窗口下 /run 后立即 /advance 只有原计划的一个 Job，没有新增发现任务或暂停调度器。驾驶舱通用建议仍有 G17 的投影收敛工作，不在本片重做。

旧 workflow_runner.py、唯一调用者的回调装配和同步 for 路径、闲置失败回调及聚合导入已删除。新多节点/Agent 工作流返回明确不支持，单 Job 前缀仍过原硬门禁；这是过渡能力边界，不把 G01/G02 关闭。旧 14f87a3 实际 HTTP 生成的 legacy run 在新服务仍查询/核对原 Job、执行计数 1，engine 不改写，也未创建新图；不自动重放未提交旧节点或 Agent。

8 项核心真实 HTTP/tmux 场景、另一次真实受理窗口消费者检查、5 项实际故障/重启、真实 Chromium 可见按钮及 12 项本地契约通过。覆盖正常默认 auto_apply/auto、非零退出、停止、等待重启、12 次重发、6 次并发首次请求、终态重复唤醒、计划受理/回执窗口硬退出、缺失与损坏检查点。无回执未知提交保持 blocked/reconciling，副作用 0；其他正常/恢复 Job 副作用均 1。损坏文件只读检查后保持原字节，协调器 blocked，原外部 Job 仍可 done；不是假装已取消。

过程发现保留：首次本地断言把 running 误认为命令已写文件，改为等待真实实物；系统测试解释器缺 SQLite saver，另建公开依赖+pytest 的开发 venv；损坏注入首次被 SQLite 遗留 WAL 影响原文件，因此新增 saver 写入前只读检查，再复验通过。正常路径没有替身、force、手填终态或补记录；故障 wrapper 仅在隔离状态里硬退出/损坏文件，恢复均用原服务命令。根 pytest 无用例退出 5，不算通过；compileall/相关 JS 语法通过。

仍未实现 Job 输出进入 Agent、子任务续跑、Agent 预算/取消、报告正文；没有真实 SSH/GPU/模型验收。检查点缺失恢复仅适用于本片冻结单 Job；B2c 不能照搬为 Agent 从头重放。单机一个服务、启动未知窗口和保留/检查点增长边界仍见 G09/N14；全库损坏会阻塞使用该库的图，不影响独立 Job 服务核对。脚本、截图、结果、旧版隔离 checkout、配置和数据库均只存本地。

### N03B2c1：一个 Job → 无工具报告 Agent（已完成）

只扩展原协调器，新增 engine `langgraph-job-report/n03b2c1`；单 Job 仍使用 `langgraph-job/n03b2b`。冻结完整两步计划、所选节点/实例/Agent 和非密钥 Provider 路由 hash；等待期间修改实例不会改本次执行，也不会被冻结副本写回覆盖。Provider 模型/endpoint 改变则拒绝执行，凭据不复制到计划。旧 B2b 检查点沿原节点恢复，没有新建第二推进器或自动重放旧 Agent。

Job 成功后，当前 attempt 保存 output_value：run_id/node_id/attempt_id/job_id/host_id、受限日志、文件大小/偏移/省略字节及截断标记、当前 Job 的 artifact_manifest 声明（不声称验证其中实物）。原引用解析器消费这些输入；报告只允许 tools=[]，一次模型请求，无 stream→普通请求 fallback，无工具/子任务。引用缺失/日志不可用不改用同名历史输出。失败/停止前置使报告 skipped，模型请求 0。

Agent claim 在模型调用前事务落盘；服务重启时有 claim 无结果变成 unknown/blocked；已有结果直接复用。图结果未落盘前断电仍保留 attempt 证据；检查点缺失按 Job 回执和 Agent claim 核对，不能当作从头自动调用模型的许可。单个后台图唤醒线程串行处理工作流，原 scheduler 继续监控 Job；慢 Provider 不占住 Job 监控循环，其他工作流图仍可能等待这个串行线程。服务退出不会保证撤回已发出的网络请求。

实际通过：5 项真实 HTTP/tmux/受控 Provider 主链；7 项历史输出、冻结实例、路由变更、503/无 fallback、长回答、JSON、截断/脱敏边界；4 项真实硬退出窗口及两次缺检查点核对；4 项不关硬门禁的拒绝场景；2 项真实延迟/取消；1 项慢报告期间独立真实 Job 继续监控；实际 898ef12 创建的 B2b 等待检查点升级恢复；Chromium 可见默认按钮可启动，页面收到 running→done、2/2 快照，报告交付仍 incomplete（未逐项断言状态 DOM 文案）；8 项单 Job HTTP 回归和 17 项本地契约；受控 Provider 返回工具 JSON 时明确失败，工具轨迹/子 Job 均为 0，公开记录不含合成敏感参数。受控 Provider 仅证明编排，不证明真实模型质量/供应商可用。

过程审查发现并修正：pending writes 不能当图结束；模型等待不能占用监控线程；独立监督发现无工具报告仍可能生成意外工具 JSON 的参数轨迹，现已在生成工具步骤、事件和副作用前拒绝，并复验公开记录不含原始参数。测试辅助错误也保留：失败状态先可见但报告 skipped 尚未提交，检查器改为等待完整计划的步骤状态；兼容脚本批量换目录误换 engine 字符串，修正本地断言；独立 Job 验证误把 gpu_policy 当直接 API 的 CPU 选择参数，使用原 gpu_index=none 后正常通过，没有关闭资源门禁。报告输入 artifact_manifest 来自本次 Job 的声明字段，不为通过测试塞一份无关历史 manifest。

compileall 通过；根 pytest 无用例退出 5，不计通过；新增/改动源码、API 字段与台账/文档范围复核见本地交接。没有改前端脚本/加载顺序，浏览器仍单独实测。只保存 inline 回答证据，不落盘报告文件；一般 Agent deadline/网络预算、子任务、长报告、SSH/GPU/传输及真实模型未完成或未验证。规格不变，测试/配置/日志/结果/截图/旧版 checkout 全部本地忽略。当时下一片为 N07A；最新顺序见第三部分 2.14。

### 本轮可视化成果复验（源码 2a2edb3，未开发新功能）

按用户要求，将 N00C 至 N03B2c1 的 13 个切片整理成白话成果说明，历史证据与本轮点击复验分开。展示页、原始截图/录像、结构化导出、计算文件及正文证据只在本机 `dev_work/artifacts/stage-showcase/`，测试脚本在 `dev_work/smokes/`，不进入远端；本机运行配置放隔离的 `config/stage-showcase-local/`。正式三部分与稳定规格的职责不变。

真实 Chromium 经可见工作台/实例/工作流/运行/记录按钮操作，不调用隐藏页面 callback、不强制显示、不手填终态。正常链计算 1 到 10 平方和 385，Job 和本机演示报告接口各执行一次；故意退出 7 的 Job 失败、报告 skipped、接口调用 0；运行期间真实重启控制服务、刷新页面后沿原 run/Job 完成，计算仍为一次。三例均点击实际“导出”按钮下载 JSON，点击“打开日志”读取当前任务。报告由本机接口从本次日志生成，只证明交接，未验证真实供应商/模型质量。测试生成的正文展示文件不算产品 N07A 已交付。

实际过程暴露 G10 的内置角色自动补工具、G24 的实时重复步骤及 G25 的成功说明写入 error；完成后的 DOM 也有旧 pending 行，不冒记页面完全正确。重新打开页面只用于展示持久事实，并另留实时重复行截图。记录页正文入口缺口仍归 G06。准备时曾用错误的 HTML open 空属性判断导致自动化点到折叠控件、演示接口直接解析序列化日志失败、继承代理未直连本机；修正本地脚本/隔离配置后复验，不修改业务代码或测试终态。先使用 config 根目录会合并同目录用户主机配置，随后将演示配置移入独立子目录、重建隔离状态，展示只含本机主机，不分享个人配置。

### D-UI-01：前后端交付与页面职责补充（文档切片）

本轮只更新规则、规格边界文义、G26 与后续顺序；没有改业务代码，也没有新增 UI 功能或关闭 G24/G25/G26。前端设计指导采用已核对来源/许可的 frontend-design，具体范围与退出成本见第三部分 2.14。原阶段展示归档为本地静态材料，保留源码 2a2edb3 的截图、导出、命名录像和失败证据，不拿归档内容声称当前功能已修复。只清理确证无引用的重复录像，不清空历史回归、用户配置或运行证据。

## 4. 逐文件台账的读法

下面每行对应一个实际文件，列出需求、职责与输入处理输出、检查结论和解决路径。`保留`表示本轮未发现该文件的独立缺陷，不保证所有分支正确；`关联`表示参与某个问题的修补或验收，不表示文件自身一定有 bug。同一问题的详细方案只在 G 登记维护，避免在几百行表格重复且漂移。

证据栏采用源码中的具体符号和行号；对纯数据、CSS/HTML、转导出入口检查对应边界。文件的责任不由行数决定，框架替换也不能跳过这些接口与测试。

<!-- FILE_AUDIT_START -->

### total_control

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/__init__.py) · 5 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [agent_executor.py](../total_control/agent_executor.py) · 511 | R03/R09；Agent 输入/模型/工具/预算 → ReAct 循环与结果封装 → AgentExecution | N03B2c1 的 single_call 模式只调用一次、无失败 fallback，工具 JSON 在生成轨迹/副作用前拒绝，单调预算与返回后 cancel/deadline 检查；普通多轮路径保持，G04/G21 未关闭。 | `_tool_side_effect:31`；`_metadata_value:39` |
| [agent_runtime.py](../total_control/agent_runtime.py) · 49 | R09；execution_id/取消请求 → 进程内注册与信号 → active/cancel 检查 | 问题/修补关联 [G04](#g04)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `register_agent_cancel:20`；`cancel_agent_run:30` |
| [compat.py](../total_control/compat.py) · 21 | R14；公开门面名/默认实现 → 查询 override → 兼容调用入口 | 问题/修补关联 [G16](#g16)；按登记方案处理，不另建平行服务。 | `public_api_override:7`；`public_api_value:17` |
| [config.py](../total_control/config.py) · 332 | R01/R13；config/ TOML/SSH 配置 → 合并主机与本机路径参数 → AppConfig/ServerConfig | N02 新增 execution_db_path，以配置目录解析相对路径；默认沿 DATA_DIR，真实密钥布局不迁移；其余关联 [G19](#g19)。 | `ServerConfig:18`；`AppConfig:40`；`load_secrets:49` |
| [constants.py](../total_control/constants.py) · 2 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context_refs.py](../total_control/context_refs.py) · 18 | R05/R09；数据和点分路径 → 字典键/列表下标查找 → 原值或 None | N00C 唯一纯取值内核；执行映射与上下文投影均已接入；不承担引用前缀或就绪规则。 | `context_ref_value:8` |
| [events.py](../total_control/events.py) · 207 | R12；业务事件/游标 → 有界队列、gap 与 SSE 编码 → 实时通知 | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `EventBroker:12`；`sse_encode:135` |
| [handler.py](../total_control/handler.py) · 180 | R12/R13；HTTP/静态请求 → 路由与领域错误封装 → JSON/文件响应 | N02 将 RunStoreError 明确返回 503，坏库不伪装为空或 workspace 不存在；原边界仍关联 [G19](#g19)。 | `Handler:23`；`run:152`；`main:170` |
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
| [paths.py](../total_control/constants_pkg/paths.py) · 59 | R02/R03/R05；环境变量/项目根 → 定义配置、数据、日志位置 → 路径常量 | N00D 将 tmux 默认宽度设为 160；路径与运行数据规则保持，关联 [G08](#g08)。 | 文件整体/公开入口 |
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
| [post_routes.py](../total_control/http_api/post_routes.py) · 416 | R06/R12；POST 命令 → 现有状态服务/公开封装 → 启动/配置响应 | N02 工作流 request_id/提交冲突返回 409；其余路由不批量改写，关联 [G19](#g19)。 | `_public_job_response:14`；`handle_post:30` |
| [put_routes.py](../total_control/http_api/put_routes.py) · 44 | R12；资源更新请求 → 匹配资源与调用更新 → 更新响应 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `handle_put:9` |

### total_control/infra

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/infra/__init__.py) · 5 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [checks.py](../total_control/infra/checks.py) · 218 | R01/R07；主机/检查或停止请求 → 连接、能力、进程所有者检查 → 诊断或停止结果 | N00D 修正停止权限：正常信号优先，sudo -n 回退，ps 判存活；保留实时归属确认入口。 | `run_server_checks:21`；`build_process_stop_script:90` |
| [shell.py](../total_control/infra/shell.py) · 2 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [web_terminal.py](../total_control/infra/web_terminal.py) · 160 | R07；主机/输入/信号 → PTY 启动与读写 → 终端缓冲和状态 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `set_terminal_winsize:19`；`WebTerminal:26` |

### total_control/infra/shell_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/infra/shell_pkg/__init__.py) · 159 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [command.py](../total_control/infra/shell_pkg/command.py) · 94 | R01/R07；命令/超时/密码模式 → subprocess 或 PTY 执行 → CompletedProcess | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_run_command_impl:23`；`run_command:32` |
| [gpu.py](../total_control/infra/shell_pkg/gpu.py) · 327 | R01/R07；主机列表/探测配置 → nvidia-smi 与连接采集 → GPU 状态快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `gpu_activity_state:28`；`_collect_server_impl:51` |
| [host.py](../total_control/infra/shell_pkg/host.py) · 486 | R01/R07；系统文件/远程探针 → CPU/内存/磁盘/网络解析 → 主机资源 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `parse_csv_lines:24`；`parse_meminfo:32` |
| [jobs.py](../total_control/infra/shell_pkg/jobs.py) · 193 | R07/R13；任务 cwd/环境/命令 → 前置屏障、共用退出标记 → 唯一 shell Job 脚本 | N03J1a 的 6 项真实入口 + 7 项 shell 契约通过；前置失败不运行 payload，原 monitor 判 failed。环境默认/提前 shell exit 限制仍见 [G23](#g23)。 | `conda_bootstrap:90`；`build_job_script:128` |
| [probe.py](../total_control/infra/shell_pkg/probe.py) · 44 | R01/R07；主机检查项 → 生成/判定远程探针 → 能力检查结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `remote_check_script:23`；`server_check_ok:27` |
| [process.py](../total_control/infra/shell_pkg/process.py) · 61 | R01/R07；PID/ps 输出 → 本地或远程查进程 → 进程元信息 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `ps_lookup_local:22`；`ps_lookup_remote:28` |
| [ssh.py](../total_control/infra/shell_pkg/ssh.py) · 109 | R01/R07；ServerConfig/命令 → SSH 参数与连通性检查 → 远程命令结果 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_ssh_command_impl:22`；`ssh_command:29` |
| [tmux.py](../total_control/infra/shell_pkg/tmux.py) · 68 | R01/R07；会话/尺寸/任务 id → tmux 参数与日志命名 → 会话操作参数 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `tmux_new_session_args:21`；`tmux_resize_commands:35` |
| [transfer.py](../total_control/infra/shell_pkg/transfer.py) · 489 | R08；源/目标/过滤/冲突策略 → rsync、安全与冲突探测 → 传输命令/检查结果 | N00D 在 rsync SSH shell 中携带配置端口；复用原参数与路径安全规则，工作流交接仍关联 [G14](#g14)。 | `rsync_endpoint_prefix:53`；`server_matches_rsync_prefix:65` |

### total_control/orchestration

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/orchestration/__init__.py) · 20 | R06/R09；节点执行/输入类型 → 公开导出 → 单节点兼容入口 | N03B2b 退出 WorkflowRunner 等同步推进导出；保留已有节点执行消费者。 | 文件整体/公开入口 |
| [input_mapping.py](../total_control/orchestration/input_mapping.py) · 296 | R05/R09；引用/上下文/模型输出 → 解析映射与 JSON 输出校验 → 输入值/输出证据 | N00C 改为导入唯一取值内核；前缀/缺失/历史输出规则仍关联 [G10](#g10)，未整体统一。 | `_is_mapping_ref:11`；`resolve_input_mapping_ref:16` |
| [node_runner.py](../total_control/orchestration/node_runner.py) · 212 | R06/R09；节点/执行上下文 → 选择 Agent/Job、Agent 失败校验 → StepResult | 共用原 Agent 执行入口/映射和失败规则；N03B2c1 传递 output_value 到持久 step，不自建模型或推进循环。G02/G04 仍开放。 | `_node_handler_mode:51`；`_node_agent_id:56` |
| [run_store.py](../total_control/orchestration/run_store.py) · 305 | R06/R11/R13；完整计划/attempt/提交意图 → SQLite 事务、hash 与单机互斥 → 可核对证据 | N03B2c1 在原 attempts 表增加 Agent 原子 claim，无第二提交表/schema 迁移；execution_id/未知窗口可核对，终态仍不可覆盖。G09 启动/保留风险未关闭。 | `canonical_json:19`；`content_hash:23`；`RunConflictError:27` |
| [types.py](../total_control/orchestration/types.py) · 89 | R06/R09/R11；计划/结果/上下文 → RunPlan/StepResult/ExecutionRunContext → 类型化边界 | N02 RunPlan 仍经领域库冻结；N03B2c1 StepResult 追加可选 output_value，承载本次报告证据，不把回答当实物。 | `RunPlan:8`；`StepResult:22`；`ExecutionRunContext:73` |
| [job_coordinator.py](../total_control/orchestration/job_coordinator.py) · 126 | R06/R11/R13；run/冻结计划、Job 回调 → 持久图/暂停、去重唤醒与身份检查 → attempt 事实及检查点 | N03B2c1 在唯一图加报告节点，保留 B2b 节点/engine；pending writes 有任务但 next 为空仍结算。Job/Agent 副作用由领域适配器核对，其他链不支持。 | `JobCoordinator`；`advance`；`_validate_checkpoint` |
| [workspace_mutations.py](../total_control/orchestration/workspace_mutations.py) · 143 | R02/R10；节点/配置或 artifact 内容 → 修改工作区内存快照 → 配置/产物元数据 | 问题/修补关联 [G06](#g06)；按登记方案处理，不另建平行服务。 | `find_workspace_node:29`；`apply_workflow_edit:45` |

### total_control/state

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/__init__.py) · 20 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | `TotalControlState:16` |
| [_deps.py](../total_control/state/_deps.py) · 40 | R14；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [base.py](../total_control/state/base.py) · 230 | R06/R13/R14；配置/持久数据 → 账本/回执核对、唯一图适配及后台启动 → 单机状态 | N03B2c1 组合同一个 JobCoordinator/报告回调与单个串行后台唤醒线程；监控线程不等待模型，legacy 不重放。G09/G21 剩余风险保持。 | `_dedupe_provider_profiles:8`；`_agent_definitions_need_writeback:44`；`BaseMixin:60` |
| [files.py](../total_control/state/files.py) · 741 | R04/R11；浏览/清理请求 → 文件与保留引用管理 → 文件/存储响应 | N02 暂保护账本 run 和回执，防止 JSON 裁剪后重新出现或失去幂等依据；事务归档待 N14。其他关联 [G07](#g07)、[G09](#g09)、[G20](#g20)。 | `_runtime_state_run_job_ids:18`；`_runtime_state_workspace_run_closure:22`；`FilesMixin:47` |
| [jobs.py](../total_control/state/jobs.py) · 4 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [monitoring.py](../total_control/state/monitoring.py) · 114 | R01/R12；探针/查询 → 刷新完整计划投影、组合工作区状态 → status/cockpit | N02 读取领域账本和 Job 事实形成只读投影，不执行恢复副作用；派生冗余仍关联 [G17](#g17)。 | `MonitoringMixin:5` |
| [persistence.py](../total_control/state/persistence.py) · 63 | R11/R13；内存 jobs/workspaces/registries → JSON 保存与密钥加密 → 本地状态文件 | 问题/修补关联 [G09](#g09)；按登记方案处理，不另建平行服务。 | `PersistenceMixin:5`；`save_jobs:6` |
| [registry.py](../total_control/state/registry.py) · 606 | R03/R05；能力/模板/Profile 请求 → CRUD 与诊断组合 → 公开 registry payload | 问题/修补关联 [G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `RegistryMixin:30`；`tool_definition_by_id:31` |
| [scheduler.py](../total_control/state/scheduler.py) · 370 | R01/R06/R07；资源/Job 队列及计划 → 原 monitor 核对后唯一唤醒图 → Job/run 更新 | N03B2b 增加唯一调度唤醒；不把 HTTP/query/SSE 变成推进器。保留原生命周期与日志；GPU 原子预留仍见 G13。 | `SchedulerMixin:8` |
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
| [crud.py](../total_control/state/jobs_pkg/crud.py) · 205 | R07/R11；Job 创建/重试/复制/删除 → 唯一队列生命周期 → Job/关联 run | N02 排队 Job 在锁内写盘后才公开，失败撤销内存条目；克隆清除旧提交身份。普通 create_job 不提供通用去重；关联 [G09](#g09)。 | `CrudJobsMixin:8` |
| [execution.py](../total_control/state/jobs_pkg/execution.py) · 747 | R07；Job/资源/日志请求 → GPU 选择、tmux 启停、尾部读取 → 状态与日志 | N03J0 收紧 queued/starting 启动门禁，退出 running 会话消失就重启路径；完成核对仍归 monitor_jobs。其余资源/日志/控制缺口关联 [G09](#g09)、[G13](#g13)。 | `_read_text_file_tail:10`；`_read_text_file_chunk:36` |
| [paths.py](../total_control/state/jobs_pkg/paths.py) · 25 | R07；任务/服务器路径 → 展开远程目录变量 → 实际任务路径 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `PathsJobsMixin:8`；`_format_remote_path:9` |
| [presets.py](../total_control/state/jobs_pkg/presets.py) · 70 | R07；研究 preset 请求 → 专用计划与 Job 创建 → 实验任务列表 | 问题/修补关联 [G18](#g18)；按登记方案处理，不另建平行服务。 | `PresetsJobsMixin:8`；`preset_command:9` |
| [queue.py](../total_control/state/jobs_pkg/queue.py) · 48 | R07；Job id/移动方向 → 调整排队序号 → 队列位置 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `QueueJobsMixin:8`；`reorder_job:9` |
| [task_plans.py](../total_control/state/jobs_pkg/task_plans.py) · 237 | R07；模板/参数矩阵 → 展开、预览、排队 → 通用批量 Job | 问题/修补关联 [G18](#g18)、[G19](#g19)；按登记方案处理，不另建平行服务。 | `TaskPlansJobsMixin:8`；`task_plan_items:9` |

### total_control/state/registry_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/registry_pkg/__init__.py) · 1 | R03/R05/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [execution_overview.py](../total_control/state/registry_pkg/execution_overview.py) · 325 | R03/R05/R11；全局 run/Job/筛选 → 引用匹配与分页投影 → 只读执行概览 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `execution_overview_status_group:10`；`execution_overview_search_text:19` |
| [provider_profiles.py](../total_control/state/registry_pkg/provider_profiles.py) · 200 | R03/R05/R11；Profile/目录/保存版本 → 合并、健康与脱敏 → 有效/公开 Profile | N03B2c1 用非密钥路由 hash 检测 endpoint/model 变化，密钥/密钥指纹均不复制到计划；协议/私密存储仍按 G21/G09 后续处理。 | `normalized_provider_base_url:11`；`provider_catalog_public_payload:15` |
| [provider_route_health.py](../total_control/state/registry_pkg/provider_route_health.py) · 162 | R03/R05/R11；工作区/Agent/Profile → 检查路由缺口 → 诊断问题列表 | 问题/修补关联 [G21](#g21)；按登记方案处理，不另建平行服务。 | `build_provider_route_health:8`；`add_issue:35` |
| [tool_definitions.py](../total_control/state/registry_pkg/tool_definitions.py) · 22 | R03/R05/R11；工具引用变化 → 重写 Agent allowlist → 更新后的定义 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `rewrite_agent_tool_reference:8` |
| [tool_testing.py](../total_control/state/registry_pkg/tool_testing.py) · 73 | R03/R05/R11；工具/安全测试参数 → 判定副作用并受限执行 → safe-test 结果 | 问题/修补关联 [G11](#g11)；按登记方案处理，不另建平行服务。 | `run_tool_definition_safe_test:12` |
| [workflow_templates.py](../total_control/state/registry_pkg/workflow_templates.py) · 498 | R03/R05/R11；模板节点/能力目录 → I/O、绑定、拓扑校验 → validation/preview | 问题/修补关联 [G10](#g10)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `rewrite_workflow_template_agent_reference:20`；`build_workflow_template_validation_payload:60` |

### total_control/state/workspaces

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/workspaces/__init__.py) · 20 | R05/R06/R09；领域 mixin → 装配 WorkflowRecordsMixin → 工作区服务入口 | N02 接入记录/适配边界；仍只有原 workflow runner，不按短文件删除。 | `WorkspacesMixin:17` |
| [_deps.py](../total_control/state/workspaces/_deps.py) · 52 | R05/R06/R09；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [agent_runtime_control.py](../total_control/state/workspaces/agent_runtime_control.py) · 138 | R05/R06/R09；工具 GPU/Job 控制请求 → 候选建议或当前工作区任务控制 → planned/stopped/reordered | 问题/修补关联 [G11](#g11)、[G13](#g13)；按登记方案处理，不另建平行服务。 | `bind_workspace_tool_gpu_allocation:8`；`control_workspace_tool_job:51` |
| [agent_runtime_inputs.py](../total_control/state/workspaces/agent_runtime_inputs.py) · 100 | R05/R06/R09；映射/节点位置/历史输出 → 检查运行时引用 → refs/blockers | 问题/修补关联 [G10](#g10)、[G01](#g01)；按登记方案处理，不另建平行服务。 | `_agent_node_runtime_input_refs:10` |
| [agent_runtime_observation.py](../total_control/state/workspaces/agent_runtime_observation.py) · 156 | R05/R06/R09；子 Job/run id/观察限额 → 等待与读取受限快照 → runtime observation | 问题/修补关联 [G02](#g02)、[G04](#g04)；按登记方案处理，不另建平行服务。 | `workspace_tool_observe_options:9`；`workspace_tool_job_snapshot:35` |
| [agent_runtime_safety.py](../total_control/state/workspaces/agent_runtime_safety.py) · 327 | R05/R06/R09；命令/观测文本 → 允许诊断边界与密钥脱敏 → 拒绝原因/安全文本 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `redact_runtime_observation_text:18`；`workspace_tool_command_block_reason:29` |
| [agents.py](../total_control/state/workspaces/agents.py) · 887 | R05/R06/R09；Agent 节点/工具参数 → 有效配置、runtime Job、输出持久化 → execution/节点结果 | N03B2c1 共用现有映射/AgentExecutor，冻结工作区不合历史 outputs/不写回实例，报告不调用声明型 artifact 写入；返回有界 inline 证据。debug 旧路径保留，G04/G06 未关闭。 | `AgentsMixin:33`；`cancel_agent_execution:34` |
| [automation.py](../total_control/state/workspaces/automation.py) · 138 | R06/R12；用户推进请求/权威 run 与 Job 投影 → 活跃运行保护、发现/受理命令 → watch/blocked/run 反馈 | 受理窗口 watch 保护同时涵盖 B2b/B2c1；当前运行未完成或未知时不另开发现任务。不是图推进入口，G17 建议投影仍开放。 | `AutomationMixin:8`；`advance_workspace_automation:9` |
| [chat.py](../total_control/state/workspaces/chat.py) · 902 | R09/R12；聊天/反思/流请求 → 路由、Agent、消息更新 → 聊天与事件 | 问题/修补关联 [G05](#g05)、[G04](#g04)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `ChatMixin:7`；`_chat_agent_execution_trace:33` |
| [crud.py](../total_control/state/workspaces/crud.py) · 365 | R02；工作区与迁移请求 → 创建/更新/模板差异与草稿 → 工作区快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `CrudMixin:7`；`workspace_by_id:8` |
| [debug.py](../total_control/state/workspaces/debug.py) · 181 | R05/R06/R09；Agent 定义/样例 → 组装调试上下文与有效配置 → debug/execution | 问题/修补关联 [G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `DebugMixin:7`；`debug_agent_definition:8` |
| [defaults.py](../total_control/state/workspaces/defaults.py) · 62 | R05/R06/R09；工作区/应用建议请求 → 有来源的默认与发现回填 → 配置快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `DefaultsMixin:7`；`apply_workspace_automation_defaults:8` |
| [discovery.py](../total_control/state/workspaces/discovery.py) · 162 | R05/R06/R09；工作区/发现节点 → 创建受控发现 Job 链 → 发现任务/run | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `DiscoveryMixin:7`；`run_workspace_discovery:8` |
| [nodes.py](../total_control/state/workspaces/nodes.py) · 461 | R05/R06/R09；节点/前置 Job/自动化状态 → 编译命令与依赖 → 节点 Job payload | 问题/修补关联 [G01](#g01)、[G14](#g14)；按登记方案处理，不另建平行服务。 | `NodesMixin:7`；`workspace_node_job_payload:8` |
| [runs.py](../total_control/state/workspaces/runs.py) · 650 | R05/R06/R11；steps/事件/查询 → 新账本投影与历史 JSON 兼容 → run/SSE | N02 新工作流先写所属 attempt，再复用既有事件/响应；不以局部步骤替换完整计划。历史 JSON 分支保留，关联 [G02](#g02)、[G03](#g03)、[G09](#g09)。 | `_workspace_public_payload_with_full_runs:8`；`RunsMixin:18` |
| [workflow.py](../total_control/state/workspaces/workflow.py) · 432 | R05/R06/R09；启动/重发/实际前缀 → 类型边界、原门禁及冻结计划受理 → run/暂可为空的 jobs | N03B2c1 仅支持单 Job 或 Job→无工具 eval.report Agent；原命令/主机/引用门禁保留，冻结路由 hash；其他计划明确拒绝，无同步 runner 回退。 | `_workspace_agent_execution_checks`；`WorkflowMixin.run_workspace_workflow` |
| [workflow_records.py](../total_control/state/workspaces/workflow_records.py) · 387 | R06/R11/R13；计划/Job 回执/图回调 → 冻结 payload、幂等提交核对/attempt 观察 → 领域证据和公开投影 | N03B2c1 冻结两步计划、捕获本次有界输出、复用原解析/Agent 执行；先 claim 后调用，未知阻塞、已记结果复用。单后台图唤醒线程，Job 服务/提交账本保持唯一。 | `WorkflowRecordsMixin:21` |

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
| [advance.py](../total_control/workspace/automation/advance.py) · 593 | R05/R06；实际节点/派生状态 → 门禁与包组合 → 自动化投影 | N03B1 不再强制六类 Starter 节点，system/human 不要求 Agent；固定发现建议仍待 [G17](#g17)，默认环境问题见 [G23](#g23)。 | `derive_workspace_automation_state` |
| [bundle.py](../total_control/workspace/automation/bundle.py) · 647 | R05/R06；命令/目标/证据 → 生成脚本、标识、包门禁 → ExecutionPackage | 问题/修补关联 [G10](#g10)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `make_execution_package_id:11`；`make_stable_execution_package_id:16` |
| [contracts.py](../total_control/workspace/automation/contracts.py) · 2 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [core.py](../total_control/workspace/automation/core.py) · 61 | R05/R06；检查字段/状态 → 统一基础检查项 → 带优先级 readiness item | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_execution_node_by_kind:6`；`workspace_automation_check:15` |
| [deployment.py](../total_control/workspace/automation/deployment.py) · 226 | R05/R06；实例命令/服务参数 → 推断端口、健康检查与停止命令 → 部署交付建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_delivery_contract:7`；`workspace_deployment_health_path:76` |
| [evidence.py](../total_control/workspace/automation/evidence.py) · 206 | R05/R06；执行/发现状态 → 收集来源与分组 → evidence 清单 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_evidence_item:6`；`workspace_add_evidence_item:22` |
| [helpers.py](../total_control/workspace/automation/helpers.py) · 21 | R05/R06；列表/限额 → 压缩显示条目 → 紧凑列表 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `compact_contract_items:10` |
| [preflight.py](../total_control/workspace/automation/preflight.py) · 593 | R05/R06；工作区/资源/执行 → 汇总预检与资源编排 → 缺口和建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_execution_readiness_step:7`；`workspace_resource_item:36` |
| [report.py](../total_control/workspace/automation/report.py) · 458 | R05/R06；自动化各投影 → 汇总高亮/门禁/行动 → 操作报告 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_report_highlight:9`；`workspace_report_next_action:17` |
| [reproduction.py](../total_control/workspace/automation/reproduction.py) · 791 | R05/R06；计划/声明数据/静态输入 → 范围内脚本与包缺项 → execution bundle | N03B1 仅有消费者的命令预览进入包；warning 可提交，声明数据与输入硬错误保留；未统一多同-kind/远程读取，关联 [G10](#g10)、[G12](#g12)、[G17](#g17)。 | `derive_workspace_reproduction_manifest` |
| [run_plan.py](../total_control/workspace/automation/run_plan.py) · 195 | R05/R06；节点执行方式/配置 → 阶段和命令摘要 → run plan | N03B1 复用 executor resolver，Agent 报告不强求 shell report_command；实际路由/输入仍由提交门禁校验。 | `workspace_node_command_summary_for_plan`；`derive_workspace_run_plan` |
| [topology.py](../total_control/workspace/automation/topology.py) · 391 | R03/R05/R06；节点执行方式/Agent/工具 → 有效绑定和路由缺口 → topology | N03B1 仅 Agent 模式进入 Agent 绑定/路由缺口；system/human 不借虚拟绑定过门禁，其余投影收敛待 [G17](#g17)。 | `derive_workspace_agent_topology` |

### total_control/workspace/automation/contracts_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/automation/contracts_pkg/__init__.py) · 60 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context.py](../total_control/workspace/automation/contracts_pkg/context.py) · 351 | R05/R06；节点/输出/映射 → 解析并汇总上下文契约 → 输入/输出状态 | N00C 通过别名复用 context_refs；展示就绪语义仍由本文件处理，关联 [G10](#g10)。 | `workspace_node_workflow_contract_metadata:16`；`workspace_context_value_present:84` |
| [io.py](../total_control/workspace/automation/contracts_pkg/io.py) · 226 | R05/R06；节点类型/映射 → I/O 默认和引用静态校验 → refs/gaps | 问题/修补关联 [G10](#g10)；按登记方案处理，不另建平行服务。 | `workspace_io_contract_for_kind:12`；`workspace_node_config_signal:24` |
| [orchestration.py](../total_control/workspace/automation/contracts_pkg/orchestration.py) · 225 | R05/R06；节点契约/拓扑缺口 → 按阶段分车道 → 编排展示契约 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_orchestration_gap_matches_node:12`；`workspace_orchestration_status:29` |
| [workflow.py](../total_control/workspace/automation/contracts_pkg/workflow.py) · 229 | R05/R06；实际节点/映射/执行方式 → 复用静态引用校验 → workflow contract | N03B1 保留显式非法引用；Agent 要求声明输入完整，shell 默认映射是未消费预览，不能误当必需 Agent 输入。静态/运行时规则统一仍待 [G10](#g10)。 | `derive_workspace_workflow_contract` |

### total_control/workspace/cockpit

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/cockpit/__init__.py) · 135 | R02/R04/R05；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [_deps.py](../total_control/workspace/cockpit/_deps.py) · 16 | R02/R04/R05；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [commands.py](../total_control/workspace/cockpit/commands.py) · 56 | R02/R04/R05；仓库/配置/资源 → 规则推断 setup/run/GPU → 命令与候选建议 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `infer_workspace_setup_command:7`；`infer_workspace_run_command:20` |
| [discovery.py](../total_control/workspace/cockpit/discovery.py) · 386 | R02/R04/R05；输入路径/数据线索 → 目录推断与根验证 → discovery plan/bundle | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `workspace_path_like_values:10`；`workspace_project_path_score:34` |
| [evidence.py](../total_control/workspace/cockpit/evidence.py) · 417 | R02/R04/R05；发现结果/现有字段 → 生成并应用有来源回填 → backfill plan/实例 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `apply_workspace_evidence_config_value:15`；`merge_workspace_evidence_config_values:29` |
| [fsm.py](../total_control/workspace/cockpit/fsm.py) · 614 | R05/R06；检查与静态契约/包 → 共用阻塞投影 → cockpit/提交门禁 | N03B1 复用 workflow_contract 缺项，包错误优先显示真正计划阻塞；保留公共响应与旧建议投影，不另造解析器。关联 [G17](#g17)。 | `workspace_workflow_blocking_checks`；`workspace_execution_package_blocking_checks` |
| [helpers.py](../total_control/workspace/cockpit/helpers.py) · 75 | R02/R04/R05；工作区/Job/字段 → 通用选择与参数解析 → 基础派生值 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_jobs_for_workspace:7`；`workspace_node_config_ready_status:19` |
| [payload.py](../total_control/workspace/cockpit/payload.py) · 333 | R02/R05/R07；实例输入/显式环境 → 现有默认回填与运行投影 → workspace | N03J1b 退出 rg-* 默认执行名；5 项契约、真实默认 HTTP/浏览器、显式环境正常/失败通过。旧无来源配置不猜测清除；其他就绪展示仍见 [G17](#g17)。 | `apply_workspace_automation_defaults_to_payload:19` |
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
| [run_delivery.py](../total_control/workspace/execution/run_delivery.py) · 185 | R06/R10/R11；包预期/step artifact → 路径匹配与完成度派生 → delivery closure | N03B2c1 inline-answer 无文件时 report.incomplete=true/既有 warning，不能因执行 done/指标就宣称报告交付。其他旧声明型判定仍是 G06，N07A 接本地正文验证。 | `_workspace_delivery_path_candidates:9`；`workspace_execution_run_delivery_closure:43` |
| [run_events.py](../total_control/workspace/execution/run_events.py) · 324 | R06/R10/R11；事件/流摘要 → 裁剪、脱敏、计数 → run event/delta_evidence | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `_compact_run_event_text:8`；`_compact_run_event_payload:15` |
| [run_export.py](../total_control/workspace/execution/run_export.py) · 341 | R06/R10/R11；run/关联任务 → 有界日志、artifact、manifest 组合 → JSON 导出 | 问题/修补关联 [G06](#g06)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_run_export_manifest:18`；`workspace_run_export_readme:147` |
| [run_records.py](../total_control/workspace/execution/run_records.py) · 248 | R06/R10/R11；完整 steps/历史 run → 状态/进度/规范化 → 兼容 run 记录 | N02 保留计划/attempt/意图字段，skipped 终结但未执行步骤仍计分母；简化相同分支，暂保护账本记录不被条数截断。关联 [G02](#g02)、[G09](#g09)。 | `make_workspace_execution_run_id:12`；`make_agent_execution_id:16`；`derive_workspace_execution_run_status:20` |
| [run_refresh.py](../total_control/workspace/execution/run_refresh.py) · 284 | R06/R10/R11；计划/attempt 与旧 Job/子 run → 按 engine 区分只读投影 → 当前 run | B2b/B2c1 图记录只读持久 attempt；查询/SSE 不独立推进 Job 或 Agent。legacy 只读兼容分支保留，G02 未关闭。 | `_workspace_child_run_status:22`；`_workspace_child_run_error:29`；`_workspace_agent_child_runtime_status:44` |
| [run_refs.py](../total_control/workspace/execution/run_refs.py) · 194 | R06/R10/R11；run/step 引用 → 去重、闭包与归属过滤 → 关联 Job/子 run | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_unique_run_ref_list:11`；`workspace_run_step_job_ids:20` |
| [run_replay.py](../total_control/workspace/execution/run_replay.py) · 169 | R06/R10/R11；run/关联 Job → 组装历史时间线 → 摘要回放 | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_execution_run_timeline:19`；`workspace_execution_run_replay_run_summary:63` |
| [run_state.py](../total_control/workspace/execution/run_state.py) · 103 | R06/R10/R11；节点/Job → 按最近 Job 派生节点执行状态 → 执行面板状态 | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `derive_workspace_execution_state:10` |
| [run_steps.py](../total_control/workspace/execution/run_steps.py) · 359 | R06/R10/R11；Job/Agent/计划结果 → 状态、资源、引用规范化 → 持久/公开 step | N03B2c1 保留可选 output_value 到公开 step/回放；Job 当前输出和报告正文证据均绑定具体 attempt；原资源/引用字段保持。G25：成功 detail 无条件写入 error，显示红字误报，待独立契约修复。 | `workspace_run_step_status_from_job:18`；`_normalize_agent_meta:33`；`normalize_workspace_run_step_resources:45` |
| [runs.py](../total_control/workspace/execution/runs.py) · 77 | R06/R10/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [trace.py](../total_control/workspace/execution/trace.py) · 246 | R06/R10/R11；节点/绑定 Job → 汇总产物、资源与轨迹 → 节点 trace | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_node_artifacts:20`；`workspace_node_resources:97` |

### total_control/workspace/schema

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/schema/__init__.py) · 139 | R02/R03/R05；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [agents_tools.py](../total_control/workspace/schema/agents_tools.py) · 438 | R02/R03/R05；Agent/工具草稿/默认 → 规范与 backfill → 有效能力定义 | G10 本轮复现：内置角色 backfill 覆盖明确空工具列表；独立自定义角色可运行，默认权限意图仍待修复。工具能力标签仍归 G11。 | `_tool_side_effect_value:14`；`workspace_default_agents:20` |
| [chat.py](../total_control/workspace/schema/chat.py) · 461 | R02/R03/R05；消息/反思/工作区 → 规范、规则回复与 debug → chat/debug payload | 问题/修补关联 [G05](#g05)、[G11](#g11)；按登记方案处理，不另建平行服务。 | `normalize_workspace_context_reflection:15`；`normalize_workspace_chat_message:54` |
| [nodes.py](../total_control/workspace/schema/nodes.py) · 698 | R02/R03/R05；源类型/节点草稿/recipe → 默认、绑定、连线规范 → 顺序工作区节点 | N03A0 保留明确 system/human 与已绑定 Agent 的执行者；缺指定/缺 Agent 继续由唯一 finalizer 补默认，输出键/输入映射沿原逻辑。关联 [G10](#g10)、[G11](#g11)、[G14](#g14)。 | `workspace_node_definition:22`；`workspace_node_kinds_for_source:31` |
| [recipe.py](../total_control/workspace/schema/recipe.py) · 201 | R02/R03/R05；启动/模型/环境输入 → 字段规范与源类型推断 → recipe/model/inputs | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `normalize_workspace_recipe:13`；`clean_workspace_config_default:32` |
| [templates.py](../total_control/workspace/schema/templates.py) · 1372 | R02/R03/R05；模板/实例快照 → 版本、拓扑、差异与迁移计划 → template/snapshot/diff | N03A0 模板补齐保留明确 system/human，即使没有 agent_id；新默认链仍提供推荐 Agent。其余迁移/快照关联 [G10](#g10)、[G16](#g16)。 | `workflow_template_sort_key:39`；`normalize_workflow_template_version_history:46` |

### web

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [index.html](../web/index.html) · 1895 | R12/R14；浏览器加载 → UI 壳与脚本顺序 → 产品入口 | G26：实例配置抽屉嵌套运行详情/多层折叠；按 N13B1 迁移运行阅读区，加载顺序仍需保护。 | 文件整体/公开入口 |

### web/config-center

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [config_center_agent_actions.js](../web/config-center/config_center_agent_actions.js) · 126 | R03/R12；用户事件/注入依赖 → Agent 定义动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_agent_health.js](../web/config-center/config_center_agent_health.js) · 112 | R03/R12；页面数据/注入依赖 → Agent 能力健康 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`textList:21` |
| [config_center_agent_renderer.js](../web/config-center/config_center_agent_renderer.js) · 196 | R03/R12；状态/注入 renderer → Agent 定义组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_ai_renderer.js](../web/config-center/config_center_ai_renderer.js) · 201 | R03/R12；状态/注入 renderer → AI 配置组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_diagnostics.js](../web/config-center/config_center_diagnostics.js) · 128 | R03/R12；页面数据/注入依赖 → 链诊断 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`defaultToolTestArguments:21` |
| [config_center_execution_overview_actions.js](../web/config-center/config_center_execution_overview_actions.js) · 60 | R03/R12；用户事件/注入依赖 → 全局运行概览动作路由 → 回调/API 请求 | G26：配置中心的真实运行概览仍有消费者，N13B2 迁移时核对事件/刷新后退出旧展示；本轮保留。 | `element:8`；`eventTarget:12` |
| [config_center_execution_overview_renderer.js](../web/config-center/config_center_execution_overview_renderer.js) · 145 | R03/R12；状态/注入 renderer → 全局运行概览组合 → DOM 更新 | G26：配置中心的真实运行概览仍有消费者，N13B2 迁移时核对事件/刷新后退出旧展示；本轮保留。 | `element:8`；`listFor:12` |
| [config_center_provider_actions.js](../web/config-center/config_center_provider_actions.js) · 119 | R03/R12；用户事件/注入依赖 → Provider 配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_provider_profiles.js](../web/config-center/config_center_provider_profiles.js) · 239 | R03/R12；页面数据/注入依赖 → Provider 目录和选项 → 派生状态/界面结果 | 契约/维护关联 [G21](#g21)；消费后端结果，随所属切片收敛。 | `escapeFor:13`；`vendorDefaultBaseUrl:47` |
| [config_center_tool_actions.js](../web/config-center/config_center_tool_actions.js) · 109 | R03/R12；用户事件/注入依赖 → 工具配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_tool_renderer.js](../web/config-center/config_center_tool_renderer.js) · 164 | R03/R12；状态/注入 renderer → 工具配置组合 → DOM 更新 | 契约/维护关联 [G11](#g11)；消费后端结果，随所属切片收敛。 | `element:8`；`listFor:12` |

### web/core

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [app.js](../web/core/app.js) · 26575 | R12；注入存储/HTTP/client ID → 装配共用工作流提交组件 → 原动作控制器 | N03A 提交装配保留；G26 的运行概览刷新/实例与运行切换须随单一视图迁移核对。组合根仍见 [G15](#g15)。 | `workspaceAutomationActionDeps:25360` |
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
| [styles.css](../web/styles/styles.css) · 23037 | R12/R14；界面类名/视口 → 层叠与响应式布局 → 视觉样式 | G26：抽屉/高度/滚动布局参与拥挤，按单一阅读视图核对实际布局；样式叠加仍见 [G15](#g15)，不凭重复 selector 删除。 | 文件整体/公开入口 |

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
| [workspace_automation_actions.js](../web/workspace/workspace_automation_actions.js) · 898 | R06/R11/R12；两个直接动作 → 共用稳定身份、受理反馈/忙碌控制 → HTTP/run/日志 | N03B2b 同步文案为计划节点数/已关联 Job 数，允许受理时 jobs 为空；真实浏览器 running→done 通过。单节点/发现仍原入口，G17 不关闭。 | `workflowErrorMessage:212`；`runWorkspaceToNode:312`；`runWorkspaceWorkflow:375` |
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
| [workspace_run_detail_actions.js](../web/workspace/workspace_run_detail_actions.js) · 305 | R02/R06/R09/R12；用户事件/注入依赖 → 详情、回放、比较、导出动作动作路由 → 回调/API 请求 | G26/N13B1：运行详情/日志/导出动作随阅读视图迁移，保持当前 run 引用；报告/导出仍见 G06/G20。 | `appState:8`；`selectedWorkspace:13` |
| [workspace_run_filter.js](../web/workspace/workspace_run_filter.js) · 195 | R02/R06/R09/R12；页面数据/注入依赖 → 运行筛选条件 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:22`；`normalizeFilters:26` |
| [workspace_run_replay.js](../web/workspace/workspace_run_replay.js) · 220 | R02/R06/R09/R12；页面数据/注入依赖 → 摘要回放展示 → 派生状态/界面结果 | 契约/维护关联 [G20](#g20)；消费后端结果，随所属切片收敛。 | `escapeFor:13`；`compactFor:17` |
| [workspace_run_state_merge.js](../web/workspace/workspace_run_state_merge.js) · 347 | R02/R06/R09/R12；页面数据/注入依赖 → HTTP/SSE run/step 版本合并 → 派生状态/界面结果 | G24 已在真实 DOM 复现：绑定 Job/Agent 前后 merge key 变化，旧 pending 占位被追加；应按稳定 step/attempt 身份合并。G02/G20 历史兼容仍保留。 | `defaultTimestampMs:17`；`timestampMs:22` |
| [workspace_run_summary.js](../web/workspace/workspace_run_summary.js) · 260 | R02/R06/R09/R12；页面数据/注入依赖 → 运行进度/交付摘要 → 派生状态/界面结果 | 契约/维护关联 [G02](#g02)、[G06](#g06)；消费后端结果，随所属切片收敛。 | `escapeFor:17`；`statusFor:21` |
| [workspace_shell_actions.js](../web/workspace/workspace_shell_actions.js) · 46 | R02/R06/R09/R12；用户事件/注入依赖 → 工作区视图/页签交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_template_diff.js](../web/workspace/workspace_template_diff.js) · 282 | R02/R06/R09/R12；页面数据/注入依赖 → 模板/实例差异 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`diffStatusLabel:17` |
| [workspace_template_migration_actions.js](../web/workspace/workspace_template_migration_actions.js) · 174 | R02/R06/R09/R12；用户事件/注入依赖 → 模板迁移动作动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `selectedWorkspace:8`；`cachedDiff:12` |
| [workspace_tool_catalog.js](../web/workspace/workspace_tool_catalog.js) · 93 | R02/R06/R09/R12；页面数据/注入依赖 → 实例工具分类/健康/副作用显示 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceToolById:22`；`workspaceToolLabel:26` |
| [workspace_workflow_submission.js](../web/workspace/workspace_workflow_submission.js) · 89 | R06/R11/R12；工作区/固定范围参数、存储/HTTP/client ID → 提交前持久身份/确认/重发 → 本次 run 或待核对错误 | N03A 新增唯一浏览器直接运行提交组件；sessionStorage 同标签页刷新恢复，未知错误不换键、损坏/不可用不发请求。不推进流程、不猜终态；作用边界见第三部分 2.6。 | `validArguments:6`；`sameArguments:13`；`submit:18` |

### 本地验证与历史文件

用户清理后，tests/ 与旧 dev_work/smokes/ 不再有现存脚本，历史文件可从 Git 读取。N01 新样机集中在本地 dev_work/n01/：common.py 管理配置与模拟外部任务，engines.py 包含 LangGraph/SQLite 对照，cli.py 提供跨进程本地演示，verify.py 验证故障与恢复；这些均不进入正式源码或远端。第三方环境、锁文件、数据库、输出文件同样只保留本地。N02 的存储契约检查、真实服务/HTTP 验证和崩溃注入位于本地 dev_work/n02/，隔离配置位于忽略的 config/n02-local/；它们也不进入正式源码或远端，过程限制见第三部分 2.5。

### 配置、公开样例与测试入口

| 文件 | 检查结论与解决方向 |
| --- | --- |
| [config/servers.toml](../config/servers.toml) | R01/R13；保留本地默认与 SSH 发现，属于非私密启动样例，不混入个人主机。 |
| [config/user_servers.example.toml](../config/user_servers.example.toml) | R01/R13；保留覆盖模板；后续输入校验统一，实际用户覆盖仍忽略。 |
| [config/secrets.example.toml](../config/secrets.example.toml) | R13；保留 SSH 密码格式示例；不等于推荐明文密码，真实 secrets 不入库。 |
| [data/agent_definitions.json](../data/agent_definitions.json) | R03；保留公开 Agent 目录；与真实 adapter/Provider 绑定校验，关联 G10/G11。 |
| [data/tool_definitions.json](../data/tool_definitions.json) | R03；保留工具 schema；明确建议/真实读取/异步执行级别，关联 G11。 |
| [data/workflow_templates.json](../data/workflow_templates.json) | R02/R05；保留起始链；顺序执行与拓扑预览分开，新增 Transfer 后版本化。 |
| [config/workflow-poc.example.toml](../config/workflow-poc.example.toml) | R06/R13/R14；N01 无密钥配置模板，定义引擎、隔离状态目录和 worker 延迟；仅本地样机读取，正式服务尚未接入。 |
| [pytest.ini](../pytest.ini) | R14；历史 testpaths=tests 与 scratch 排除；当前没有正式测试文件，后续按切片生成本地检查；无用例不算通过。 |
| [requirements.txt](../requirements.txt) | R14/G08；唯一直接运行依赖声明，固定 cryptography/LangGraph/SQLite saver；两个独立 Python 环境安装/HTTP/框架持久化通过。间接依赖仍由 pip 解析；N03B2b 已接单 Job 生产协调器，不用开发工具包扩大启动要求。 |

### 台账完整性与维护

正式代码台账包含 288 行，一文件一行；配置/公开数据/依赖与验证入口 9 行；本地样机/安装验证另说明职责，不列为生产源码。代码路径集合来自当前实际源码树，不按历史目录猜测。新增、删除或改职责时同步对应行和 G 问题状态；不把未跑过的场景写成已验收。
<!-- FILE_AUDIT_END -->
