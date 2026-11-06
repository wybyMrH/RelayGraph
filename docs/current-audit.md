# 第二部分：现状、问题与逐文件审查

审查日期：2026-11-06。目标基线为[第一部分](project-spec.md)，解决顺序为[第三部分](next-stage-plan.md)。本文随代码变化更新，不能作为永久完成证明。

## 1. 范围、证据等级与结论

当前执行指针：N04-M2a 已限定接通 Agent 剩余预算到既有模型请求，首次静默等待由2.64秒降到约1秒（预算1秒），后续/fallback共享余量。唯一下一片 N04-M2a-UI：真实页面核对模型尚未返回时的超时失败、已有child独立状态与刷新。持续滴流仍能超过总预算，G04未关闭；G36/G33/精确重复通知及follow异常恢复仍开放，N04未完成。

当前正式代码台账覆盖 292 个文件：169 个后端 Python、121 个前端 JavaScript、HTML/CSS 各 1 个；配置/公开数据/本地验证入口另列。用户已在 42960ac 删除远端 24 个历史测试文件并忽略 tests/，旧本地 smoke 也已清理，本文不再把它们列为现存文件。不读取真实 Provider 密钥，不把运行数据、缓存或第三方包计入正式代码。

N00C/N00D 已完成文档收敛、重复代码清理和原有业务改动整合；N01 随后完成本机执行引擎选型；N02 已把完整计划、attempt 和提交记录接入现有工作流入口。样机/验证只留本地 dev_work/。LangGraph 已在 N03B2b 接入单 Job，N03B2c1 接入一个 Job → 无工具报告 Agent；G01 的更长混合链、G02 子任务续跑和 G09 剩余恢复边界仍开放，G03 的新工作流失败覆盖路径已退出。N03J0/N03A0/N03A 分别收紧 Job 启动状态、保留明确执行方式、接入浏览器稳定提交身份；这些小片不等于 Job → Agent 已正确等待。N03B1 已完成实际计划/前缀门禁；默认自动回填路径的过程复验另发现 G23；N03J1a 已阻止 cwd/环境前置失败后的命令，N03J1b 已退出未配环境就回填 rg-* 名的路径。两节点 shell CPU 链是旧路径的历史验收；当前新计划仅接受单 Job 或 Job → 无工具 eval.report Agent，其他多节点计划明确拒绝。

N03B2a 已补齐唯一运行依赖清单和 Python 3.12/3.13 隔离启动验证（G08），承接 N00A 的部署基线职责；只增加依赖声明与文档，不改变上述生产等待缺口。源码现为 292 个文件，公开配置/数据/依赖与验证入口现为 9 项；N03B2b 随后完成单 Job 持久受理/等待，旧同步推进已删除；N03B2c1 已交付本次结果交接；按最新用户要求 N13A 已修复实时步骤重复，N13B1 已验收独立运行阅读区；N07A 已交付本次本地报告正文落盘与验证；N07A-UI 已交付独立报告阅读与状态；N16A 已交付成功说明/错误字段契约修正；N16A-UI 已交付执行说明、错误和历史来源；N13B2 已交付全局运行概览归位与精确运行入口；N13B3a已交付独立实例编辑及权威保存回执交接；N13B3b1已接通工具业务字段正式保存；完整配置往返仍有G27缺口，N13B3b1-UI工具配置说明与反馈已限定验收，N13B3b2a工具既有元数据保真已限定验收，N13C1周期状态请求去重已限定验收（第三部分2.26）；N13C2状态加载网络预算已限定验收（第三部分2.27），N13C2-UI超时与重试呈现已限定验收（第三部分2.28），N03B2c2a默认授权后端已限定验收（第三部分2.29），N03B2c2a-UI 已交付完整启动入口与授权说明（第三部分2.30），N03B2c2b 已修正 G11 报告 Agent 工具误报；N13B3b2b-Agent 已限定验收（第三部分2.31），N13B3b2c-Model 后端片已验收，N03B2c2c-UI 已完成 ready 隔离实例真实网页启动闭环（第三部分2.34），当前唯一下一片以本文顶部执行指针为准。

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
- N04-A 已提交一个独立 `langgraph-agent-child-job/n04` engine：完整两 Agent 计划保留，父 attempt 通过 `child-job` submission 记录稳定 key/hash、parent run/step/attempt 与 child Job metadata；child 未完成时公开步骤为 `waiting` 且 `runtime_status=waiting_child`，后续 Agent 保持 pending，分母仍为完整计划。child 完成观察仍先保持父 attempt waiting，由 `child_status=done` 路由恢复；后续 Agent 结算后把父 attempt 写成 done；这表示 child 已完成，后续 Agent 若失败，整条 run 仍不能算成功，失败分支尚未真实验收。失败/停止/收据未知则进入失败或 blocked，不重提。重复观察相同值直接 no-op。
- N04-B 旧 SQLite 可确认一个 child submission 及 parent/follow 各一个 done attempt；旧 HTTP 日志可确认完成后重发和完成后服务重启使用原 run。但验证脚本硬编码 Provider 调用数/副作用次数，child 用覆盖写入，Job 实际使用 GPU 0，不能证明 CPU、只执行一次或等待中恢复，也不能把首次失败确定归因于端口。2026-11-02 以显式本机/cwd/CPU/none 参数、追加计数和原门禁重跑，工具成功提交 child，但持久 Job 变成 GPU 0；当时因 G31 停止验收，没有手填终态或改条件让其通过。N04-D 随后通过成功/失败/停止、重复调度与等待中重启的 HTTP 补充证据；浏览器、正文交接、取消关系与其他未知窗口仍未验收，N04-B 不整体关闭。
- N04-G后端已补本次child日志交接：只有done后经原Job adapter读取最多8192字节，复用既有脱敏，并带host_id及job-log-handoff/v1证据；完整空日志、截断、缺失、读失败或范围不足分开，UTF8替换字符保守标不完整。对同run/parent/attempt/Job/host/done+schema冻结首次证据，缺失/失败也冻结，不自动重读或重跑模型。follow显式保留映射内容，UTF8序列化映射超过65536字节则blocked；其他Agent仍用原预览压缩。这是映射上限，不是整个模型prompt上限。
- 真实HTTP/scheduler/tmux普通/大日志/失败/停止四链均在等待中重启并同键重发，Job及追加各一次；普通和大日志follow实际请求分别保留2348/8192字节日志，尾部运行时随机标记在400字之后，实际映射与持久output相等。大日志明确partial、跳过5360字节；失败/停止不调用follow。另通过正式API增加重复输入映射使其超限，follow为blocked且模型维持父的两次调用，无静默裁短。54项本地契约/回归通过；正常链不关门禁、不补终态，Provider受控且回复不作为读过日志的证明。N04-G-UI随后通过真实网页普通/超长两链，展示冻结交接的完整性及正文，页面文本与实际follow输入一致；父子取消等仍未交付。
- 方案：先冻结完整计划，再为每个节点记录等待/尝试；完成事件恢复推进。分别处理子 Job 与子 run，重复通知不重复启动，服务重启能恢复。N04 只覆盖 child Job 和受控 Agent handoff，child run 另切片。

N04-G-UI（2026-11-06）补充证据：真实Chromium可见网页启动普通/超长CPU child两链，经受控SSE Provider、真实HTTP/scheduler/tmux完成；每链3次模型请求、1个child/1次追加、parent/follow各1attempt，完整计划2步。普通2248字节完整；超长原14858字节、读取6666–14858、交接8192字节且明确部分。页面展开文本逐值等于实际follow请求映射和持久output，随机END在400字之后，不以受控回复证明模型理解。每链等待中重启、完成后重启/刷新同run/证据，1440×900和768×900、键盘Enter展开、summary/pre焦点和pre滚动跨2400ms实时更新、点击原Job日志核对随机END，无pageerror。截图已人工核看，证据仅本地dev_work/artifacts/n04gui-20261106-175225/。

纯JS覆盖身份/schema不符拒绝正文、矛盾完整性不标绿、完整空文件、旧无登记、partial/missing/error、转义及按attempt/Job展开键；F-UI回归、两个JS语法、121脚本引用/加载顺序与diff检查通过。独立布局夹具在1440/768/390覆盖长主机/长正文、缺失/读错/旧/空完整，不算实际磁盘故障或完整手机导航；证据dev_work/artifacts/n04gui-layout-20261106-175201/。首轮浏览器脚本错按不存在的文本标题解析模型输入，改为既有JSON封装后完整重跑，未改产品迎合断言。旧“打开日志”仍读当前原任务日志，与冻结交接不同，保留；没有第二状态合并器、轮询器或日志存储。后端/API/配置/稳定规格不改；历史回放点击、真实供应商/SSH/GPU及Python3.10完整运行本片未验证。测试和结果不提交。


N04-H（2026-11-06）补充：新增精确运行入口POST `/api/workspaces/{workspace_id}/runs/{run_id}/stop-continuation`，必须传parent_attempt_id、child_job_id、child_policy=keep_running。只受理N04唯一父waiting_child/确认child收据且无follow attempt的窗口；子任务刚done但follow未开始可受理，验证快照已failed/stopped/未知则拒绝，不能替代观察既有因果。run_lock与协调器互斥，忙或已开始follow返回409。事务再核plan/hash/engine、父状态、唯一submitted intent及无其他attempt，原子写父stopped+record.continuation_stop，保留原trace/输出/完整计划/receipt；不创建假follow attempt或把pending改done。该stopped仅说明后续流程已禁止，不声称子任务停止。Job状态读取与SQLite写入不是跨存储原子，随后发生的child失败/停止仍保留独立事实。

同身份请求返回原停止时间/回执，child后来变化或缺失不影响已接受停止的精确重放；新attempt、Agent claim和submission准备受持久marker保护；唯一图推进器在run_lock内见marker后no-op，不恢复旧checkpoint去调用follow。直接resume也由父stopped早退；原terminal attempt的同输入读取保留，停止后重新开始/重试不在本片。公开run增加continuation_stop，旧记录为空；原父stopped/child独立与follow前置未成功显示兼容，H-UI另做可见动作。旧Agent cancel只控制活动调用，Job stop只控制child，都有不同真实调用者，保留；不增取消线程/第二推进器/轮询器。

实际证据：73项本地契约（H19+D/E/F/G54）通过，包括两个RunStore句柄并发stop/begin只一个成功、写record故障回滚父attempt、commit后投影失败重发原receipt、缺/未知/冲突/已claim拒绝、terminal旧入口不重启和图no-op。真实HTTP/scheduler/tmux三条CPU链：停止后child自然done；停止后child经原Job stop变stopped；不停止对照中follow已进入Provider时停止返回409，之后正常done，终态再次停止仍409。两停止链waiting中及child终态后重启、原run请求重发和多轮调度仍同run/1Job/1追加，父stopped、follow pending/零attempt，模型只有父的2次请求；正常链3次/2attempt。每链先验证旧Agent cancel已inactive返回404，未当作流程停止；额外进程实际持flock时新入口409，释放后正常受理。完整计划分母2，停止链进度0而非100。Provider是受控SSE，不代表真实供应商/模型分析。证据仅dev_work/artifacts/n04h-20261106-180914/，脚本仅dev_work/smokes/n04h_http.py、test_n04h_stop.py、n04h_consumer.cjs。

compileall、原前端merge兼容stop字段/拒绝旧waiting回退与F-UI契约、diff通过；根pytest无用例退出5不记通过。首次smoke以文件路径调用导致仓库导入路径错误，改用模块入口；随后读尚未产生的jobs.json、故障夹具未等待scheduler释放flock分别失败，只修观察脚本为正式GET /api/jobs和有限重试获取注入锁后完整重跑，未修改产品门禁/记录。缺失、SQLite故障、两句柄竞争和child刚done窗口属契约夹具；实际HTTP未伪造这些状态。尚未浏览器点击新动作，未覆盖活动父Agent/已claim follow强停、网络中断取消、多child、SSH/GPU或Python3.10部署。稳定规格不变。

N04-H-UI（2026-11-06）限定验收：运行记录父步骤提供“停止后续流程”，明确“子任务继续运行”；按workspace/run/step/attempt/child完整身份发keep_running，只有匹配持久回执才显示已停止。收到409先读原run、说明未受理；响应未知先GET核对，GET失败只提供只读核对，GET仍waiting也不声称请求未执行，只允许用户显式按原身份再次请求。各POST/GET分别复用config注入的HTTP等待预算，不是整个动作总deadline，客户端abort不等于服务端取消。临时反馈仅内存，刷新后重新按持久run判断；切换实例不改变原请求目标。确认父停止后，实际Job区可用原stopJob精确停止child；父控制区与子任务区在实时重建时保留当前键盘焦点，不异步抢焦点。

最终真实Chromium五链通过，证据仅 `dev_work/artifacts/n04hui-20261106-184153/`：正常停止后child自然done；停止后单独停止child；POST未送达且首次GET失败，显示未知→只读核对→显式重试；服务端已commit但浏览器响应丢失，读原run确认且无重复POST；实际flock busy409后，再将真实点击延迟到follow Provider请求开始，第二次409且最终正常done。前四链各1child/1次追加、父1attempt、follow pending/零attempt、2次父模型请求，分母2；对照链2attempt/3次模型请求、完整2步done。前四链等待中及child终态后真实重启/刷新，同run/回执/选择保持；1440×900与768×900、空记录、键盘Enter和2200ms实时更新焦点通过，无pageerror。最终普通点击均无额外busy重试；未送达链2次浏览器POST仅第二次到服务端；竞争链2次POST均409。Provider为受控SSE，只证明控制链，不证明真实模型理解。

H/F/G本地JS契约、3个JS语法、121脚本路径和helper先于app装配通过。独立布局夹具 `dev_work/artifacts/n04hui-layout-20261106-183450/` 在1440/768/390覆盖加载、未知、超长错误/主机/cwd及转义，无横溢；不代表完整手机导航或真实磁盘故障。较早182546全轮属于旧文案/焦点版本，不替代最终代码；183051初次加载与183408第四链刷新失败保留在G33，未因最终通过宣称修复。183958普通停止遇真实409，脚本错误假定首点成功；仅改本地脚本为验证拒绝后有限显式点击重试并记录次数，没有改门禁/实时/终态。截图中既有启动提示浮层残留另待复核。保留原活动Agent cancel、原Job stop及实际故障Notes；仅退出匹配回执下同义英文停止说明，没有第二推进器/状态合并器/轮询器。后端/API/配置/稳定规格不变；Python3.10完整后端、真实Provider、SSH/GPU、多child和活动Agent强停未验收。脚本、配置、结果与截图不提交。


### N04-K2 · 回放加载的键盘焦点（限定验收）

对齐R12/规格§3、G26。原`workspaceExecutionRunItemMarkup`加载时把回放按钮设为原生disabled；原reader按run/node/dataset找到替换按钮后无法focus，下一次捕获已是BODY。现只将busy属性换成`aria-disabled=true/aria-busy=true`，完成后属性移除，文字仍为“加载中”。同key重复操作由原`toggleRunReplay`在await前拦截；不新增请求器、焦点缓存、异步恢复或CSS规则。现有同步恢复的消费者仍保留，未删日志/H/正文规则。

真实Chromium基线`dev_work/artifacts/n04k2-baseline-20261106-202026/`：延迟原replay GET，加载即BODY，周期更新及真实成功响应后仍BODY。修复轮`n04k2-fixed-20261106-202231/`复制历史隔离blocked数据，正常HTTP服务/页面进入运行记录，以真实Enter打开/收起、缓存重开；加载中Enter/Space/坐标鼠标点击合计仍一个GET，2400ms周期更新后仍同run按钮。注入一次503长错误后可原按钮重试；Tab离开后真实响应不抢回；切空/长名实例后选择与select焦点保持，刷新返回正常。原attempt/submission逐值不变，0Job，无Provider调用。1440×900与768×900截图已核看；长错误截图只覆盖可见首部，未重新验收全文末端与手机导航。

第二轮`n04k2-terminal-20261106-202432/`复制本轮真实CPU日志回归产生的已完成数据，再跑上述检查，切到另一实例的真实run按钮后，旧响应不抢焦点；回放按钮成功后ARIA已移除。复制数据/真实GET只证明本片阅读交互，不能冒充重新执行这些历史任务。另实际重跑`n04k1-logs-20261106-202152/`普通/超长日志两链，各1追加/3受控模型请求/2attempt、真实映射/日志正文与焦点保持通过；`n04k2-stop-20261106-202239/`原H停止后续、单独停止child及原控制焦点通过。受控Provider不证明真实模型理解。

过程失败保留：202043首轮用Playwright locator.click时被ARIA enabled检查拦住；后改真实坐标mouse.click验证产品门禁，没有force/去ARIA/关实时。202141初始化超时列G33；H首次并行回归撞日志回归端口，未启动，后仅本地脚本换独立端口重跑。J1UI/H/G/K1既有契约、121脚本装配与node语法通过；纯前端未重跑无关Python。跨run并发busyKey、切实例后的迟到全局提示继续开放。代码与缓存/本台账/计划共4文件提交，测试/配置/结果/截图仅本地。下一片只做N04完整需求总核，不以本片宣称N04已完成。



<a id="g37"></a>
### G37 · P1 · 网页取消的编码执行ID未解码（N04-M1a后端限定修复）

对齐R09/R12，类别：HTTP与真实前端消费者契约缺口。M1此前直HTTP请求使用原始冒号ID，不能证明网页入口。M1-UI真实Chromium基线 `dev_work/artifacts/n04m1ui-baseline-20261106-210007/`：原网页可见取消Agent按钮Enter，实际POST路径execution ID内冒号按encodeURIComponent成为`%3A`，旧post_routes直接split原文，取消注册表不匹配，返回404，页面真实消息Not Found。不能把这个失败归咎于Provider或用直HTTP取消替代产品点击。

N04-M1a只改post_routes：去掉固定/cancel后缀后复用已有single_segment_path_id，单次解码并拒绝空ID/原始或编码多段（400），不新增解析器、不二次解码；域服务/注册项和旧原始冒号ID入口保留，inactive仍404。现有前端encodeURIComponent和fetchJson错误消费者不变，不在浏览器写绕过编码的补丁。HTTP默认错误封装沿用既有error字段。

修复后同原页面 `n04m1ui-baseline-20261106-210325/`（本地脚本仍名baseline，但此轮代码已含M1a）真实Enter触发encoded POST，server.log记录200；信号已发后Provider仍等待，step仍running、完整分母2/follow pending；释放真实HTTP模型响应后页面沿周期更新为stopped，1实际模型请求/0Job/0追加/父1attempt，follow未开始。重发原run、服务重启和页面reload仍同run/attempt，1440×900和768×900步骤截图已核看；没有手填终态/关闭门禁/伪造模型成功。Provider延迟仅固定测试窗口，不是产品暂停能力。

9项路径契约使用实际取消注册表检查raw/%3A/小写编码同项取消、双重编码只解一次不误命中、其他ID不影响原项、空/原始/编码slash拒绝且不调用服务、inactive404；连同24项M1控制契约共33通过。compileall通过；根pytest无用例退出5不计通过。首次205922本地监听误比未编码URL而超时，只修观察脚本unquote后210007复现真实404；两轮失败/截图/网络保留，未改产品以通过错误断言。

M1a当时只完成取消URI契约，不算M1-UI完成。当时成功点击同时实测取消后额外Provider读取1次、cockpit2次（待消融），终态移除取消按钮后焦点BODY；当时列下一片，不能因为200就把整个键盘/刷新流程记通过。迟到提示/切实例、child已提交、follow取消/超时的浏览器完整分支当时仍待M1-UI，现限定结果见G26记录。前端没有改动，故不为本片重跑无关JS全套；原用户child-count不动，配置/探针/结果仅本地。

<a id="g36"></a>
### G36 · P1 · 已完成child在回放关联记录仍显示等待（当前HTTP复现）

对齐R11/R12，类别：重复记录投影不一致，E1+E2。K2终态截图已出现实际child“已完成”、回放关联项“等待中”。总核以`dev_work/artifacts/n04-completion-probe-20261106-203151/`复制本轮两条真实已完成CPU链的隔离数据，正常服务入口启动，真实GET父run/replay/jobs，未提交任何任务或调用Provider：两父run均done、parent/follow均done，linked_jobs中同Job均done，而linked_runs的同job.run-agent-runtime项仍queued。不是浏览器自己猜状态或旧截图单独构成的结论。

静态原因：`total_control/state/workspaces/runs.py::_workspace_public_payload_with_full_runs`先得到实时公开投影，随后以raw runs归一化覆盖`public_workspace.runs`；replay/export/比较调用它，关联timeline沿原始queued值输出。独立agent-tool run保留了早期提交状态，Job metadata已归父run；不能让另一个推进器或前端按最新Job强行补终态。方案：独立小片核完整读取投影与所有调用者，在保留全量/关联闭包/脱敏/历史边界的同时复用唯一事实刷新；不重写原始attempt，不顺手删除有消费者的兼容独立run。后端完成后单独前端点击回放/导出验收。当前先处理副作用控制G04，G36不与其混改。

### N04完整需求总核（2026-11-06，77bbcbd审计快照，未达到完成条件）

本次以`77bbcbd`当前代码为基线，重新核对原目标、R06/R07/R09/R11/R12与原N04-A/B计划；没有修改业务/稳定规格，也没有从历史标题继承“通过”。本地只读证据交叉检查逐值核两Agent计划、parent/follow:a1、稳定child-job key、SQLite/Job CPU身份、follow实际映射与既有失败/未知事实；9组检查中7组支持相应有限结论、2组当前反证，不能把检查脚本退出0说成产品全部通过。详细核验表与原始探针仅本地`dev_work/reports/n04-completion-audit.md`、`n04-completion-evidence.json`。

| 原要求/边界 | 当前核到的事实 | 判定与仍缺的证据 |
| --- | --- | --- |
| CPU父Agent→受控child Job→后续Agent | K1自然链200628、最新日志回归202152各1真实CPU Job/1追加/3受控模型请求，父follow各a1；实际follow输入逐值等于持久父输出，含本次run/step/attempt/Job/host/done及随机日志尾 | 支持此最小链；不证明真实模型理解，也不外推独立child Agent run |
| 首副作用前保存完整计划、等待不偷跑 | workflow.py先register_planned_workflow_run再返回，scheduler唯一唤醒；自然观测waiting时follow pending/分母2，终态才2/2 | 支持；单图/账本/Job服务各职责保留，无新推进器 |
| attempt/幂等/重复HTTP与恢复 | 最新SQLite两attempt各no1、唯一run/parent/a1/child-job key；等待/终态后重启同request返回原run，追加/调用不增 | 支持已验收窗口；不宣称任意副作用exactly-once |
| 重复完成通知 | 原scheduler每轮观察Job事实，事件publish本身不推进；旧检查终态后等待4秒/重发无新增副作用 | 仅支持重复终态观察机会/同键重放；未记录精确wake次数或重复通知消费，专门真实通知/重连回放证据仍缺，不虚构completion API |
| child失败/停止不调用follow | G真实四链173528保存失败/停止observations，follow pending/零attempt；H真实三链及K2 H回归显式keep_running、独立child停止 | 支持这些分支；follow自身失败/活动调用中断及deadline须补，不拿child失败替代 |
| 取消/截止时间门禁 | 当前取消探针203416：请求已受理后仍新建并运行child；父follow普通路径缺调用后检查 | **反证，G04优先阻碍**；单调用报告路径/H等待后停止不能抵消 |
| 提交未知与收据恢复 | J1 faults193412创建前/创建后SIGKILL，前者blocked且0Job，后者核真实receipt恢复同Job/follow；未补记录 | 支持这两个故障窗口；Provider在途/已claim follow中断为保守unknown边界，尚非所有异常的真实验收 |
| 执行目标与冲突 | D/E/F实际CPU/目录/环境与同key不同目标拒绝、旧回执保留；G31/G32各有限交付 | 支持对应范围；旧独立工具run有真实调用者，不能凭重复删掉 |
| 正文与证据完整性 | G及最新日志回归完整/partial正文、截断范围和实际follow输入一致，页面可读，旧日志入口仍供当前日志读取 | 支持有界日志交接；长报告/任意产物在本目标排除范围，不据此关G06 |
| 页面启动、实时、重启及回放 | K1修快照漏重绘、K2修焦点；但G33初始化仍偶发失败，G36回放child与实际Job矛盾 | **整体未通过**；后轮成功不能抹去初次加载失败，回放不能看似完成即验收 |
| 配置/隐私/交付规则 | 运行配置与本地探针留config忽略目录；本轮仅二三文档提交，原用户child-count.txt不动 | 本轮范围支持；3.10适配/真实供应商/SSH/GPU/Transfer均未验证或排除，不混入此审计 |

该次审计之后开N04-M1模型返回后控制门禁（现后端有限结果见G04，当前下一片见文首）。其后按更新证据分别处理必需前端验收、G36读取投影、G33诊断及精确通知/异常恢复证据，不能一次批量实现。G26迟到回放提示与跨run busyKey另记录，影响选择归属但不冒充本次执行结果；仍需按目标影响复核。N04保持未完成，第一部分不变。

<a id="g33"></a>
### G33 · P2 · N04 网页初次加载/重启刷新偶发未装配（I1未复现，原因仍未定）

- 对齐 R12/R14，类别：正常入口可靠性待调查；E1 仅指观察到的现象，不是已确认代码根因。
- K2复验再次观察：`dev_work/artifacts/n04k2-fixed-20261106-202141/` 初次导航30秒仍“尚无监控快照”，测试退出，未自动刷新掩盖；该轮只有服务日志及终端断言，未保存完整浏览器网络/截图，不能确认根因。独立后轮正常不等于修复。
- H-UI 本地复验 `dev_work/artifacts/n04hui-20261106-183051/` 首次进入页面后30秒仍“尚无监控快照”；`183408/` 的前三链通过，但第四链在child终态后重启/刷新，25秒实例select仍为空。服务就绪GET已200，日志中该次未看到浏览器bootstrap API请求；此前未完整记录静态资源/浏览器请求，不能从“未见请求”推断具体层出错。
- 对183051同隔离配置只读重开后正常，无pageerror；这仅是复查结果，不代表根因已定位或产品已修复。183958增加网络记录后另遇普通停止点击409，属于真实scheduler锁冲突，不能与加载现象混为一谈；脚本原本假定首点成功的断言已更正为核拒绝后显式重试，产品未改。
- I1已查明观察盲点：`handler.py._suppress_access_log` 默认隐藏状态GET和静态资源日志，故历史“未见请求”不能推出未发请求。`app.js` 末尾依次恢复UI、绑定事件、启动bootstrap；脚本加载失败或前置同步异常均可能阻止首请求，但本次未证明历史属于哪一种，不据此改加载器。
- 截图另观察到既有启动按钮提示浮层残留；只记录为待复核展示问题，未证明与加载现象同源，不混入停止功能修复。

N04-I1（2026-11-06）有限诊断结果：复制183408失败轮已终态的隔离数据到新config/data，以真实服务和Chromium检查原30秒快照/25秒实例阈值，不提交任务、不用刷新重试掩盖单次失败。第一组 `dev_work/artifacts/n04i1-20261106-185012/` 开既有verbose日志，首次+9次同context重启、4次fresh context均正常；该组逐事件同步重写network JSON，观察耗时1.209→11.336秒，存在采集扰动，不能当产品性能基准。第二组 `dev_work/artifacts/n04i1-route-20261106-185226/` 保持默认日志、内存采集后每次导航集中保存，启用此前smoke使用的停止路由拦截但未触发它；首次+7次同context重启、4次fresh context均正常，0.733–1.329秒。通过真实页面切换运行记录/实例后，同context重启保持选择。两组无pageerror，只有终态的4个原Job且ID不变；只读SQLite核对原数据与三份复制的runs/attempts/submissions均4/4/4，无新增执行记录。未重验运行中N04或重启未知窗口。

独立故障注入 `dev_work/artifacts/n04i1-injected-20261106-185334/` 只在浏览器阻断app.js资源：按原30秒阈值真实超时，记录net::ERR_FAILED、无首API、selectWorkspace未定义、其他helper已加载、快照为空和select零项；截图/DOM/请求均保存。这个**预期失败仅验证诊断记录有效**，与历史外观相似不等于历史根因。26个正常样本也不等于G33已修复。后续C1保留低干扰请求/完成/失败、console/pageerror和失败DOM/截图，若自然复现即暂停该次通过判定，不自动reload。I1只提交二/三文档；无业务、框架、缓存策略或阈值修改，无旧产品入口可删。既有提示浮层未在本片修复，G33继续开放。

<a id="g30"></a>
### G30 · P1 · Provider 工具调用契约覆盖不足

- 对齐 R06/R09，类别：能力缺口、伪完成风险，证据 E2/E4；旧 N04-B 失败不足以确定产品解析缺陷或端口根因。
- 本地受控 OpenAI-compatible SSE文本可触发工具步骤；C1现已补齐明确application/json的文本响应，原生tool_calls仍未支持且在该JSON分支明确拒绝。SSE原生tool_calls/分片参数、其他媒体类型与真实供应商差异仍未系统验证，G30不整体关闭。不能用固定Provider回答宣称实际读取结果。
- 方案：N04-C 单独核对 LLMClient/AgentExecutor 的输入、工具步骤、错误与副作用次数，再决定是否采用 LiteLLM 薄适配；不新增双协议主路径。

N04-C1（2026-11-06）：真实HTTP复现 `dev_work/artifacts/n04c1-probe-20261106-185937/` 显示N04因事件回调总走chat_stream，Provider对stream:true返回标准JSON时，旧SSE迭代器忽略正文却空success，父done/无child、整run blocked，实际模型请求1次。没有关闭回调或改用测试专用调用入口来绕开。现仅在OpenAI-compatible、Content-Type为application/json（允许大小写/charset）时消费同一响应，校验非空文本envelope/usage，复用原_parse_response；整体正文回调一次，不伪造分片，内部raw保留requested_stream与实际格式。空/错误结构、非法UTF8、混合error、非文本content、native tool_calls/legacy function_call及相应finish_reason明确protocol_error；Agent仅对此终止协议错误禁止旧chat fallback，不新增请求层。收到正文后回调失败仍保留已接收content，不能再次请求。其他网络/HTTP fallback、全局success、普通chat与原SSE处理不改，通用预算仍G04。

最终 `dev_work/artifacts/n04c1-20261106-191342/` 真实网页启动四条隔离CPU链：SSE/JSON各3次实际模型请求（均stream:true）、1child/1次追加、父/follow各1attempt、完整2步done。child running等待期间服务重启与同键重放，终态后再重启/重放仍同run/attempt；follow实际映射逐值等于本次持久parent output，保留620字之后的运行时随机END及run/parent/a1/Job/host/done身份。非法空choices与native+content混合链各仅1请求、0Job/0追加、父failed/follow pending；浏览器原错误/状态消费者正确显示，无pageerror。1440/768截图仅这次原页面回归，不冒称完整移动导航/键盘重验。Provider受控，不证明真实模型理解。

两正常链均记录一次活动submitting被公开投影blocked（G34），原65秒期限内只观察既有提交自然结算，不触发恢复/重提。逐快照复核唯一child-job、精确parent/a1/attempt_no1、external_ref/error空、recorded_status running及claim、无child_submission_error/submission_error；不豁免真正reconciling，不以重启后旧claim当活跃。190710 JSON与190902 SSE轮曾因脚本把所有blocked立即当终态而提前停止，保留失败；190542首轮漏选实例无启动按钮，改为原下拉真实选择；后只修观察脚本，不改产品门禁/终态。正常链仍有G34过程呈现问题，不能写成全程无阻塞。后补静态回看首次scroll_into_view等待稳定时遇实时DOM替换，只改本地滚动操作；不关闭实时或改变DOM业务内容。

27项本地真实HTTP client/Agent契约与D/E/F/G/H的73项回归通过，compileall通过；根pytest无用例退出5不计通过。只改llm_client.py、agent_executor.py和二/三文档；公开REST/SSE字段、状态枚举与动作不变，免新UI实现片，已真实回归既有浏览器消费者。原chat仍有无回调/debug消费者，保留；复用原JSON parser、urllib和队列，无新依赖、第二Provider/推进器。无Content-Type/text/plain JSON、Anthropic JSON、原SSE非法/空响应、一般网络fallback和原生工具执行仍未交付；Python3.10完整后端、真实供应商/SSH/GPU未验收。测试、结果、配置仅本地。

<a id="g34"></a>
### G34 · P2 · 活动child提交被投影成需要核对

- 对齐R06/R12，类别：过程状态误导；E1真实浏览器/HTTP快照，E2源码。`state/workspaces/workflow_records.py.project_workflow_run` 对submitting与reconciling一律投影blocked及“Job submission requires reconciliation”，即使本进程父Agent正在原提交中、attempt recorded_status仍running且无错误。
- C1最终SSE/JSON各采到一次该窗口，随后沿原提交正常完成，未人工补记录/改状态。原blocked保护不能整体删除：服务崩溃后的同一submitting/旧claim确实可能未知，不能把它显示为正在执行或自动重提。
- N04-J1后端限定修复：复用现有进程内`agent_run_is_active`，仅在N04引擎、唯一父attempt/child-job intent、精确run/step/attempt/execution_id/submit_key、running+claimed、无错误/停止/外部回执且intent仍submitting时，公开running/runtime_status=submitting。共用一个严格predicate供投影和原收据核对入口使用；核对先找真实Job，找到仍按原身份/摘要绑定，未找到且原提交仍活动才保留submitting。没有新增注册器、存储、推进器或重试；RunStore读取仍先校验计划/载荷摘要。缺活动标志、重启旧claim、真正reconciling、其他engine、多attempt/intent或身份不符不豁免。
- 活性是瞬时提示，不是持久事实或重放许可。检查后活动标志刚释放可能延后一轮未知核对，下次读取仍保守；不声称活性检查与跨存储提交原子。最小消费者只增加“提交中”标签及缓存版本，J1-UI随后限定交付共享说明，自动更新仍有G35缺口，见下文。

N04-J1证据（2026-11-06）：`dev_work/artifacts/n04j1-natural-20261106-193117/`真实Chromium点击启动，经受控JSON Provider和原HTTP/scheduler/tmux运行本机CPU链。100次HTTP观测自然捕获1次submitting、0次blocked；1个child/1次实际追加、3次Provider请求、父/follow各1attempt、完整计划2步。child运行中重启并同键重放，完成后再重启/重放仍同run/Job/attempt；follow实际映射等于本次持久父输出，含620字之后的运行时随机END。20ms采样仅捕获短窗口，不是性能结论。1440/768截图与无pageerror是既有消费者回归，不代替J1-UI、完整移动导航/键盘验收；本轮未自然复现G33，不能关闭。

故障对照`dev_work/artifacts/n04j1-faults-20261106-193412/`：本地wrapper仅暂停真实create_job前，或允许真实Job写入后拦住匹配的bind_submission；不直接写状态、不关门禁、不补终态。提交前3次GET/同键POST保持原活动提交，0Job/1次Provider；SIGKILL后用正常服务入口重启，8次观察仍blocked/reconciling、0Job、1次Provider、follow pending，不盲目重提。提交后先只读SQLite与真实jobs记录确认submitting/空ref但已有1Job，再SIGKILL；正常入口按原metadata/key/hash绑定同一Job并恢复到两步done，1次实际追加。该链共2次Provider请求：父第一次工具调用后被中断，第二次是follow，未发生父第二次模型调用；实际follow输入与恢复后持久父输出相等。尚未返回的完整父模型trace不能凭空恢复，wrapper也不是产品暂停/恢复功能。首轮193228故障脚本误把POST重放之前的旧GET当重放结果，保留失败；后改为绑定屏障固定真实故障点，只修本地观察条件。

24项J1契约与D/E/F/G/H合计97项通过，覆盖真实SQLite/活动注册、释放、独立进程不继承活动、身份/错误/多intent/其他engine及摘要损坏拒绝；这些受控夹具不冒充真实恢复。compileall、相关JS语法、原merge在running/submitting与blocked/reconciling间转换、121脚本存在/加载顺序通过；根pytest无用例退出5不计通过。受控Provider只证明流程，不证明真实模型理解；Python3.10完整后端、真实供应商/SSH/GPU未验收。代码、公开标签及二/三文档提交，测试/结果/配置仅本地。

N04-J1-UI（2026-11-06）限定交付：当前步骤和同run非linked回放使用同一纯展示helper，核N04引擎/计划首Agent/step身份，分别显示“提交中”“等待子任务”“提交结果需核对”。回放只用自己的timeline状态，不拿当前状态补猜旧快照；缺字段/其他engine仍原展示。替换原等待说明与重复runtime标签，错误、历史notes和H停止资格不改，无新合并器/轮询/恢复按钮。只有真实引用才显示Job目标/日志；未知不暗示Job未创建，也不推断后续Agent从未执行（本片提交前收紧文案并重跑故障/布局）。沿现有字体/配色/主滚动区，回放说明自然换行并覆盖旧p单行红字规则；无新卡片/折叠/字体/依赖。采用本地frontend-design（无版本声明，Apache-2.0；开片存内容摘要和来源），只取事实文案/层级/截图复核，不取营销hero/装饰动效。

自然浏览器`dev_work/artifacts/n04j1ui-natural-20261106-194651/`：可见按钮启动→原CPU/tmux→等待→done，1child/1追加、3受控JSON Provider请求、父/follow各1attempt、完整2步。等待文字与原H资格可见，键盘Enter打开真实Job日志读到START；等待中及终态后重启/同键重放不重复，follow实际输入等于持久父输出，含620字后随机END，1440/768截图，无pageerror。首轮194544日志选择器同时匹配子运行按钮而失败，修为带data-job-id的原日志入口，未改产品；自然短submitting仅HTTP捕获，不声称网页实时渲染该瞬间。

故障浏览器`dev_work/artifacts/n04j1ui-faults-20261106-195758/`：真实创建前暂停原提交，点击原运行详情/真实GET后，列表与Enter加载的回放显示提交中，无Job详情/日志/后续停止按钮；SIGKILL后正常服务入口重启并刷新，显示提交结果需核对及原错误，0Job/1Provider/父1attempt/follow pending，原键重放不重提。1440/768截图已核看。暂停wrapper仅固定窗口，不能冒充自然路径或产品恢复能力。**自动呈现未通过**：194633/194811轮活动HTTP已submitting，页面仍未运行；最终轮初看运行中，点击原详情才更新（G35）。回放Enter能加载，但2400ms后焦点落BODY，提交/未知均如此；G26焦点保持未通过，不计键盘全验收。194811轮因此断言失败保留，最终只记录真实焦点，未改产品或关实时。

H回归`dev_work/artifacts/n04j1ui-stop-20261106-194813/`：真实网页等待后停止后续、再单独停止child，刷新/重启保留回执与child独立状态；1Job/1追加、2父模型请求、follow零attempt，分母2。空记录、1440/768、停止按钮Enter及2200ms焦点通过，仅H动作焦点通过，不替代回放焦点。独立布局`dev_work/artifacts/n04j1ui-layout-20261106-195759/`在1440/768/390覆盖长名称/错误/路径、提交/等待/未知、回放无数据/加载、缺Job与Job失败，说明不截断且无横溢；不是实际磁盘故障/全手机导航。首轮布局脚本漏传notes必需escape依赖，只修本地夹具后通过。

共享文案/回放身份/旧快照/无新增动作/转义/121脚本装配、F/G/H契约和3个JS语法通过；纯前端未重跑无关Python。消融只替换重复等待/runtime，原错误证据、独立child run/日志、H动作均有调用者保留。测试/截图/配置/结果只本地。G34仅状态说明有限交付，G35/G26/G33仍开放；受控Provider不证明模型理解，Python3.10完整后端、真实供应商/SSH/GPU未验证。

<a id="g35"></a>
### G35 · P2 · 活动提交的后端快照与页面当前说明未同步

- 对齐R12/C13，类别：过程显示滞后，E1故障浏览器真实HTTP/截图。创建前暂停时精确GET run为running/submitting，但194811页面仍“未运行”；195758初看“运行中”，实际status响应后来也带running/submitting，点击原运行详情GET后才显示“提交中”。不能断言所有自然路径滞后，也不能断言只缺后端事件。
- 证据：J1-UI最终faults的network.json、before-detail-click.json/png，前轮failure.html/png与精确活动快照。正常无注入链自动进入waiting/done，但没有证明短submitting在页面自动出现。Job幂等/未知门禁未放宽，未写UI状态掩盖。
- N04-K1已定位并限定修复：原loadStatus周期renderWorkspace=false虽调用applyStatusPayload，却只绘resource-only，未绘实例运行阅读器；真实status重放原merger未丢身份/runtime/分母，新浏览器只读state与DOM基线直接确认。仅在当前workspace/runs/instance接原renderWorkspaceRuns，退出该分支重复report.sync（原reader已sync），并在响应返回、预算/请求世代检查后重取阅读位置。配置草稿、all概览、单主机资源刷新、后端/状态含义不变，无新增请求/轮询/合并器。

K1实际证据：基线`dev_work/artifacts/n04k1-baseline-20261106-200355/`同run连续8次浏览器内存running/submitting，DOM仍未运行，原失败保留。最终`dev_work/artifacts/n04k1-fixed-20261106-201123/`真实创建前暂停固定窗口，8次页面与内存均提交中；无额外详情点击/手动刷新，产品启动后的原自动详情读取保留。筛选、输入过程展开、未保存实例名称草稿及切换返回保持。延迟真实status响应期间滚轮0→250，返回仍250；SIGKILL正常重启/刷新后未知0Job/1Provider/父1attempt/follow pending，原键不重提。1440/768截图已核看。暂停/网络延迟是披露的故障注入，不冒充自然链或产品暂停能力。

自然`n04k1-natural-20261106-200628/`1Job/1追加/3请求/2attempt/完整2步，等待中及终态后重启同键不重复，Enter打开原Job日志，follow实际输入等于本次父输出含620字后随机END。H回归`n04k1-stop-20261106-200629/`停止后续再停止child、1追加/2父请求/follow零attempt，刷新重启与原动作焦点保持。普通/超长日志`n04k1-logs-20261106-200945/`两链各1追加/3请求/2attempt、完整/partial正文等于实际follow输入；重启/刷新、Enter展开、正文焦点与局部滚动跨2400ms周期更新、原Job日志均通过，无pageerror。上述目录均在本地dev_work/artifacts/，受控Provider只验证流程。

K1合同核当前instance门禁/在途导航/返回前滚动、旧请求/超时/错误拒绝、不重拉Provider/cockpit；既有22项加载预算/世代、J1UI/G/H合同、JS语法/121装配通过。首轮本地harness漏传原生AbortController，只修测试上下文后通过。纯前端接线，未重跑无关Python；真实文件报告正文未单独复验，不能把现有report.sync委托/阅读滚动合同当完整报告交付验收。回放Enter仍失焦（G26），全局历史实时、G33初始化、真实供应商/SSH/GPU/Python3.10完整后端未验收。唯一下一片K2只修回放焦点，脚本/结果/截图/config不提交。

<a id="g31"></a>
### G31 · P1 · child Job 显式 CPU 目标被执行包默认覆盖（N04-D 后端及 N04-D-UI 已限定验收）

- 对齐 R06/R07/R09，类别：错误执行目标风险，证据 E1（2026-11-02 真实 HTTP 重跑）。
- 父 Agent 的 `job.run` 工具已明确传 `server_id=local`、隔离 cwd、`gpu_policy=cpu` 和 `gpu_index=none`；持久 Job 的 resource_plan 仍记 CPU/none，但顶层与 runtime_binding 变成 GPU 0/auto。`workspace_node_job_payload` 采用 `workspace_execution_package_runtime_binding` 后覆盖了工具的明确设置。不能依赖本机恰有 GPU 使 CPU 验收通过。
- N04-D 已修复受控 run.command child：Agent 工具只传显式参数给原 payload/binding 入口，统一生成实际 server/cwd/env/GPU/阈值并更新 runtime_binding/resource_plan；包与 scheduler 保留为默认来源快照，`source=agent.tool.arguments`、`overridden_fields` 标明覆盖字段。普通工作流不传此参数，九组默认解析对照修改前一致。
- GPU policy/index 视作成对选择：只显式 CPU policy 得 none，只显式索引 0 保留 0 并使用 auto policy；非 CPU policy 单独指定则 index=auto，不继承旧 CPU。显式矛盾对拒绝；env 空串可清空，主机/cwd 空串拒绝，显存阈值 0 保留。未知主机仍经原入口拒绝。
- 2026-11-05 三条真实 HTTP→受控 SSE Provider→scheduler/tmux CPU 链通过 done/failed/stopped：waiting 中重启并同键重发后沿同一 Job；追加标记各一条；成功 parent/follow 各一 attempt、模型请求 3 次（父工具前后两次），失败/停止只有父 attempt、模型请求 2 次。额外成功链实际使用独立 child cwd 和已有 venv，日志 sys.prefix 证明激活，follow 请求 mapped_inputs 精确对应本次 parent/a1/run/Job/done。没有关门禁、手写终态或补记录。
- 17 项本地契约通过，包括 GPU 0、CPU/none、空环境、阈值 0、未知主机/空目标/矛盾参数拒绝、adapter 参数接线和普通解析前后对照。未知/其他主机仅静态夹具，未做 SSH/GPU 实际执行；后端片当时未验收浏览器，后续 D-UI 见下条。独立无 context 工具的旧 wait_for_idle 展示差异仍未解决，不能宣称所有字段/所有工具一致。
- 消融：run.command 的 host.exec 不再事后再改 GPU，复用同一 binding；显式 node_id 可选非 command 节点的 CPU 兼容分支保留，待这类调用者迁移并验证后退出。不扩 repo.clone/env.prepare，不改推进器/hash/旧 run。
- N04-D-UI 已用独立前端片验收：run 步骤按 job_id/child_job_ids 集合精确读取实际 Job，缺失不回退包默认或历史任务；明确列 CPU/主机/cwd/env，N04 的状态使用持久 step，等待/未执行有文字，成功后不沿用旧实时运行文案。同 Job 日志和重复 ID 展示合并，仍保留独立 child run 入口。浏览器可见启动→等待→成功/失败/停止、真实日志、刷新实例保留、1440/768 视口及焦点通过。独立长路径/缺 Job/GPU 0 布局夹具不冒充任务结果；实际测的是受控 Provider，不代表真实供应商。
- 页面刷新曾使日志按钮失焦：仅在原运行记录重建时按所属 run/node 和完整按钮 dataset 恢复焦点，保留原 summary 恢复，不保存 DOM、不加状态合并器。一般全局运行摘要可能仍显示实例运行中（子运行兼容记录等聚合），本片不修改全局聚合；步骤以本次持久事实展示。
- N04-E 已修复上述 hash 风险：新 payload 的 identity_version=2，覆盖最终 Job 命令、请求主机、cwd/env/GPU、策略、排队/依赖与资源阈值；阈值缺省先按本机 config 固定后，同一 payload 交给 create_job。同键不同输入仍由原 RunStore 拒绝；名称/时间/动态调度结果不入身份。没有迁移数据库或重写旧 hash。旧无版本工具重入明确要求核对，原读取/恢复仍按旧回执；不能证明旧目标相同，所以不自动重提。32 项本地契约（本片15项及 D 回归17项）通过，真实 HTTP 两次相同工具只建一 Job，换 cwd 的第二次调用返回冲突且无新 Job，均在等待中重启后保留原任务和一次追加。历史格式夹具重启复用原 Job，丢失回执故障进入 blocked/reconciling 而不重提；夹具制作过程明确见第三部分，不冒充自然产生的旧部署记录。首次契约检查另发现原异常分支漏导入 RunConflictError，已补显式导入。父流程仍可在工具冲突后 done，单列 G32，不关闭 N04 整体。

<a id="g32"></a>
### G32 · P1 · child 工具提交冲突未阻止父流程成功（N04-F 后端与 F-UI 已限定验收）

- 对齐 R06/R09，类别：错误传播缺口、伪成功风险，证据 E1（N04-E 真实 HTTP/scheduler/tmux，受控 SSE Provider）。
- 同一父 attempt 先成功提交 child，再以相同命令/不同 cwd 调用：第二次工具明确返回 `submission key reused with a different payload`，Job 数仍为 1，实际追加一次。但受控模型随后返回普通文本，父步骤仍等待首个 child，首个成功后 follow 被调用，整条 run 可为 done。冲突没有执行第二个目标，但运行终态不能证明全部工具成功。
- 静态路径：Agent 工具错误作为观察传回模型；`submit_coordinated_agent` 发现 child_job_ids 后把 recorded 改为 waiting 并清 error，后续恢复会把父步骤写 done。尚未判定每类错误在哪层应成为权威失败，不能只改一处状态或把错误藏在成功文本。
- N04-F 后端已修复这一受控边界：N04 parent 提交封装先保存首个 `child_submission_error`，RunStore 原子保留并禁止结果丢弃/成功覆盖；标记写入时保持活动 attempt，以便正常返回时保存原有 steps/trace。领域服务唯一结算函数在开始快路、结束、观察和恢复前使用该标记；从 submission 回执保留已有 child 引用，父失败不再按 child done 路由到 follow。已知目标冲突 failed，旧身份/未知或缺失回执 blocked；不自动停止已有 Job。后续同 attempt 的 child 提交拒绝，模型成功文本不产生成功事件或写入最终输出。
- 实际验证：新增8项本地契约及32项D/E回归通过，含首错保留、禁止成功覆盖、恢复/空 child 图、未知 blocked 重复观察不改证据、错误存储失败后的当前进程保护、真实create_job已入队但bind故障时按唯一metadata恢复引用。后者只读找回引用，不bind、不把blocked改成功。真实 HTTP/tmux 四条链：正常相同调用 done/4次模型请求/1次实际追加；先成功再换 cwd 为 failed/3次/1次追加；未知主机导致无 child 为 failed/2次/0追加；在第三次模型请求尚未返回时终止服务，DB已保存错误但 attempt仍running，重启后 failed/请求仍3次/1次追加。三条错误链 follow均pending、只有父attempt；等已有child真实done和重复调度后父错误仍保留。未手填终态、未关门禁、未补记录；模型为受控SSE，不能代表真实供应商。
- 限制：崩溃链保存的是错误事实、claim及child submission引用，尚未返回的完整模型steps/trace不能凭空恢复；磁盘持续不可写时只证明当前进程阻止再提交，不能承诺错误已持久并能跨重启恢复。工具注册器在进入受控提交封装前的其他错误、通用Agent预算/取消、父子取消关系不在本片。原旧child回执恢复路径保留。唯一下一片 N04-F-UI，核对失败父步骤与仍运行child的独立事实、错误/日志/刷新/重启和桌面窄窗；后端通过不等于界面交付。
- N04-F-UI随后完成独立界面验收：首步父失败/需核对与child状态分开；父错误前置、只展示一次，follow前置未成功说明来自本次run。按准确Job ID显示排队/运行/完成/失败/停止/未知文字，缺记录明确无法确认，不用包或历史任务补值。N04独立节点“重试Agent”入口隐藏，因其不是原run恢复；其他engine及原handler仍有调用者，保留。真实浏览器可见按钮启动正常相同调用与换cwd冲突两链：child running→done过程中父失败保持，follow始终pending，1440/768视口、键盘Enter打开真实日志、焦点跨更新、刷新/服务重启保留实例/run/错误通过；无pageerror。独立390/768/1440长错误/长路径/缺Job/blocked/stopped布局夹具不算真实任务。证据及未验证边界见第三部分。

<a id="g03"></a>
### G03 · P1 · 提交异常替换已记录步骤（N02 新工作流已修复）

- 对齐 R06/R07/R11，类别：证据丢失风险，证据 E1/E2。
- 原 workflow.py 的异常分支用 steps=[failed_step] 替换整个步骤表；该分支已删除。新运行在副作用前保存完整计划，当前失败写进对应 attempt 和 submission_error，保留既有 Job 引用、其他 attempt 和未提交步骤。
- 解决路径已接入现有 run/update/query 入口；中断后能从领域账本重建 JSON 投影，不靠测试补记录。原历史记录若已被旧代码覆盖，无法自动恢复，不能补造证据。
- 下一步只复用 N02 的记录接口，N03 不再维护一份独立失败步骤表；Job 等待/续跑仍在 G01/G02。

<a id="g04"></a>
### G04 · P1 · deadline/cancel 与网络预算未完整贯通（M1/M2a部分修复）

- 对齐 R09，类别：控制风险，证据 E1。
- 原 agent_executor.py:303–407 只在循环开头检查；Provider 返回后可直接 success 或继续工具副作用。llm_client 使用独立网络超时，未消费 Agent 剩余预算。
- 复现总预算 10ms，假 Provider 30ms 后返回并设置取消信号，结果 success=True、timed_out=False、cancelled=False。
- N03B2c1 仅对单次无工具报告启用单调时钟和调用后检查，并禁用 stream 失败后的第二次 fallback；真实延迟响应及取消 HTTP 验收通过，取消请求时仍显示 running，返回后才记失败/停止。网络调用不能立即中断，通用多轮 Agent 及网络剩余预算未解决，G04 保持开放。N04-H随后仅交付父Agent已返回且等待child窗口的持久停止后续意图，明确keep_running，H-UI随后交付可见动作与独立child控制；不是活动调用/网络或child停止传播的完整取消实现。
- **M1修复前的N04总核E1**：`dev_work/artifacts/n04-completion-cancel-20261106-203416/` 经正式工作区/原门禁启动CPU链，受控Provider先接请求并等待；正式Agent取消接口返回cancelled=true时真实GET仍0Job，然后才释放Provider返回合法job.run指令。最终父stopped、follow pending，但新增1个真实tmux Job且追加启动标记1次，模型请求1次。时间顺序记录为provider_enter→cancel_accepted→provider_return；未补终态/绕过门禁。取消后副作用确实发生，故不能以最终stopped验收通过。
- M1前核实N04父/follow未传report_only，均使用AgentExecutor普通多轮路径；当时调用后复核仍限single_call，stream失败fallback也未先复核。G04直接影响N04；M1仅修下述执行控制点，不关闭网络剩余预算和在途强停边界。
- **N04-M1后端限定验收**：`AgentExecutor.run`单一control_result复用原cancel_check与执行开始时的monotonic起点，循环前/stream返回后且fallback前/最终Provider返回后/tool.called回调前后/answer.delta回调前后/工具结果及step_callback落账后复核。预算到点即拒绝下一效果或成功，循环与fallback不重置；已收响应的model/token先登记，已经执行的工具observation与Job/run引用保留。旧循环前和single_call重复控制结果构造退出，single_call仍一调用/拒工具/不fallback；没有新增注册器、取消线程或传输协议。
- 当前真实HTTP `dev_work/artifacts/n04m1-http-20261106-204548/` 七分支：首次返回前cancel工具/最终答案、1秒预算的迟到工具/答案、取消后503不fallback均1模型请求/0Job/0追加，父分别stopped/failed、follow pending且零attempt；已有child后第二调用cancel保留1Job/1追加/父attempt、follow零attempt；follow第三调用cancel保留1Job/1追加/2attempt，follow stopped而非成功。取消信号送达后Provider仍等待时未预写stopped；释放后才持久终态。七条均经服务重启和原request重放，attempt/Job不增加；原门禁、真实HTTP/scheduler/tmux，Provider等待是可控故障窗口，不是产品暂停/网络强停能力。
- 正常回归 `dev_work/artifacts/n04k1-natural-20261106-204617/` 经真实网页启动JSON受控模型CPU链，3实际请求/1Job/1追加/父follow各a1、完整分母2，实际follow映射=持久本次父输出含620字后随机END；等待中与完成后重启/同键重放不重复。普通报告single_call/回调中取消/工具已执行后取消/跨迭代与fallback总预算等24项本地控制检查、C1/F/G/H/J1相关92项通过，compileall通过；根pytest无测试退出5不计通过。测试/结果/config仅本地。无公开字段/schema变更，原stopped/failed/cancelled/timed_out消费者接线保留；真实取消浏览器入口与反馈另M1-UI，当前不称UI交付。
- M1-UI真实网页入口随后发现G37编码ID取消404，M1a先独立修复；现M1-UI原网页Enter验收父/已有child/follow取消及超时，信号已受理时仍running，后端结算后才显示stopped/failed。原消息明确子任务需单独停止；已有child仍运行且原日志可打开，follow取消不改父done。不沿用M1直HTTP替代网页证据；详见下述M1-UI记录。
- M1当时剩余：LLMClient网络timeout尚未取Agent剩余预算；M2a仅接通以下空闲等待预算。持续响应读取仍不能按总墙钟期限中止；检查点与下一行外部调用不是跨系统原子操作，不承诺任意时刻的强停。回放G36/入口G33/精确重复通知未随本片修复。第一部分稳定，M1/M2a均只改AgentExecutor与二三文档。
- **N04-M2a后端限定验收**：run局部model_request_options按原monotonic起点计算min(既有60秒上限,剩余预算)，loop首次/后续及stream失败fallback均重新计算，再经原control_result拒绝耗尽；无预算返回空参数，旧行为不变。只给现有chat/chat_stream传timeout，LLMClient既有body白名单不透传；不改client协议/HTTP schema或新增网络库/线程/重试。
- 真实正式HTTP/scheduler/tmux基线 `dev_work/artifacts/n04m2a-baseline-20261106-213202/`：预算1秒，静默Provider2.6秒才响应，父失败时执行2639.1ms/1请求/0Job。修后同输入 `n04m2a-fixed-20261106-213232/first/` 为1017.0ms/1请求/0Job。`n04m2a-cases:afterchild:fallback:natural-20261106-213439/`：先前模型消费0.4秒并提交child后，第二请求静默，父1001.1ms失败，保留1Job/1实际追加及收据，follow pending；stream在0.4秒返回503再fallback静默，1001.4ms失败，仅2请求/0Job；自然CPU链3请求/1Job/1追加、父follow各1attempt、完整2步100%。各条原键重发/终态后服务重启attempt/Job不增加，正常门禁不关闭、不补终态。child即使父失败仍经原队列自然完成，未伪称父超时会停止child。
- 真实client/Agent检查覆盖无回调chat与有回调stream静默、stream503后fallback余量、无预算原60秒、实际请求正文无timeout/deadline。确定性契约覆盖耗尽不请求、长预算仍沿60秒上限、后续工具/模型消费与fallback余量、已有收据保留；与M1/C1共62项通过，compileall通过；根pytest无测试退出5不计通过。直接HTTP客户端证据与滴流测量留本地 `dev_work/artifacts/n04m2a-client-*`，不是供应商验收。新增测试/结果/config不提交。
- **仍有真实反证**：预算0.3秒、SSE每0.12秒返回一段，实际约0.84秒后原guard才判timed_out，未成功也未产生工具，但没有在总deadline中止读取。urllib timeout约束空闲等待，不是总墙钟期限；DNS/TLS/多地址、慢速JSON/错误body、取消立即中断未交付。G04保持开放，后续M2b应单独处理读取总期限，不以丢弃后台线程冒充停止。M2a状态类型未变，但失败时间改变，独立M2a-UI尚待真实网页验收。
- 过程复核：首次afterchild脚本在父failed时立即要求starts=1，磁盘Job实际queued/CPU，观察条件错误；失败记录与原数据保留，仅改本地观察为等待Job经原调度自然终态后再计数，最终1追加。没有改产品调度/超时/门禁来迎合测试。旧60秒独立等待仅在有Agent预算时被替代；无预算/debug调用、原stream与chat消费者、独立Job生命周期全部保留，无第二推进器。
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
- N03B2c1 原有 ≤4000 字 inline-answer 仍作为不可覆盖的 attempt 执行证据。**N07A 已部分修复**：新 run 冻结受控本机报告目录，成功回答持久后登记 prepared 回执，再非覆盖发布文件并核对 UTF-8 字节/sha256；验证成功才令当前文件交付完整。文件交付失败不把已完成 Agent 改成失败，不丢原回答，也不再次调用模型。
- 新增 GET `/api/workspaces/{workspace_id}/runs/{run_id}/report`，只读取该 run/attempt 的文件，返回正文、身份、摘要/字节数、验证状态与原因，不接收任意路径、不泄露物理目录。run/list/replay/export 复用同一验证投影；文件后来缺失/损坏时立即 incomplete、正文为 null，不回退 inline 冒充文件，历史 verified 回执不被改写。
- 真实 HTTP/tmux→受控 Provider 链及可见导出通过；写前/写后硬退出均从已持久回答恢复，计算/模型各一次，发布后已有正确文件不重写。冲突与只读目录写入失败保留证据；空、4001 字、无效 JSON 拒绝，4000 中文字符/12000 字节通过。故障注入只在本地 wrapper；未验证真实 AI/远程/断电持久性。
- G06 **仍开放**：旧 dispatcher 的声明型 report.write/artifact.write 有调用者，长报告未支持；旧 run 未冻结目录不自动补文件，failed 交付不自动修复。N07A-UI 已补齐可见报告入口、独立正文区和交付状态；正文仅从当前已验证GET读取，失败/缺失清正文，回到列表保持实例/run/筛选。旧inline仅作执行证据，不作为文件回退。
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
- 历史可视化及本片修复前真实 API 复现 E1：内置 reporter 即使显式 tools=[] 或删减名单，后置 backfill_default_agent_tools 仍补回五项/剩余授权；默认 auto_apply 后无工具报告链 HTTP409，未产生 Job。专用 global 定义同状态重启也扩大授权。此前用自定义角色运行只能证明绕开该默认冲突，不能证明内置角色可用。
- **N03B2c2a 后端已限定验收**：唯一 normalize_workspace_agent 按本次显式 tools→同ID已有 tools→缺字段推荐处理，空列表/None/空串均不补权。缺字段以既有内置ID preset优先，未命中才用role；只补工具，不改自定义prompt等字段。矛盾ID/role不再联合两套推荐，是有意收敛，不宣称所有旧输入逐值等价。保留既有无效工具过滤/门禁语义；已有正规化名单、历史run/snapshot不猜来源、不批量迁移或恢复曾被加回的权限。
- 删除后置 backfill_default_agent_tools、schema导出及仅有的启动/cockpit payload调用；启动退出该补权引起的写回，payload退出整段无消费的Agent再规范化，原metadata保留。工具定义目录补全、首次初始化及原清理写回保留。29项本地合同、6组真实API、一次正常默认auto_apply的CPU Job→内置reporter tools=[]报告链、网页读取/导出及重复/重启通过；详第三部分2.29。无Agent工具执行扩展，G10引用/前端目录重复仍开放。
- **已交付界面，闭环待复验（历史交接）**：N03B2c2a-UI 已增加完整运行按钮和授权说明（第三部分2.30）；旧 topology 对无工具报告 Agent 的误报由 N03B2c2b 修正，详见 G11。N03B2c2c-UI 后续仍需用 ready 隔离实例真实点击提交并进入本次 run 阅读；当前先处理 N13B3b2c-UI，不把旧 HTTP 成功或先前409写成网页闭环通过。
- 方案：统一纯引用解析器，静态校验与运行时校验共享规则但传入不同上下文；由后端提供版本化目录，前端只留必要无服务草稿默认。先锁定空值、前向引用、历史输出与 $prev 语义，再替换调用者；不把不同职责的校验一律合并。

<a id="g11"></a>
### G11 · P2 · 工具注册、建议、读取与真实执行混在一个实现标签下

- 对齐 R03，类别：能力缺口、语义误导，证据 E2。
- repo.search 汇集 query/roots/hints，未实际搜索仓库；log.read 返回最新日志入口而非正文；notify.user 返回载荷，schedule.plan 是 dry_run。gpu.allocate 的实际 callback 返回 plan_only=True、persisted=False，并不写绑定；旧本地文档“已绑定”不准确。
- N02 发现完整 CPU 工作流被固定 Starter Chain 要求加入 dataset.find/env.infer/gpu.allocate；N03B1 已退出这条固定必需路径，正常两节点 shell CPU 链无需这些节点或 Provider。实际声明的数据依赖仍校验，命令、显式主机和引用错误仍拒绝；工具建议/真实执行标签问题保持开放。
- AgentExecutor 缺少 tool_executor 时返回 [Simulated]，若当生产路径使用可能让模型把模拟当真实。自定义工具 CRUD 也不等于自动产生适配器。
- N13B3b1新增E2：agents.py构造allowed_tools只按ID交集，AgentExecutor保存/查找工具也未过滤enabled；本片只证明开关字段持久化，不能把“停用”当可靠执行隔离。WorkspaceToolContext.tool_definition_by_id先全局再实例，实例Search Provider覆盖是否作用未动态验证；先明确有效配置优先级，再单片收敛执行入口，不再加一套目录。
- N13B3b1-UI已退出按推荐/启用数量推算ready的工具摘要，明确新增定义不生成动作、停用未构成执行隔离、运行自动补配置可能补回工具/授权。仅修展示语义，不关闭以上执行风险；真实浏览器/限制见第三部分2.24。
- N03B2c2a真实页面新增E1/E2：同一内置reporter tools=[]实例执行包ready_to_execute=true、missing=[]，正常run门禁可通过，但旧topology仍报required_tool_unbound缺report.write。推荐工具与本片单次无工具报告能力混淆，尚未修复；UI不得隐藏该错误冒充诊断准确，诊断语义若需后端改动另开小片。工具enabled隔离与全局/实例有效配置优先级仍开放。
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
- app.js 26,280 行，styles.css 22,851 行；不少 helper 有 fallback，与 app 中默认/包装路径并存。CSS 某些 selector 出现 5–6 次，但媒体查询与有意覆盖不应直接删除。
- N13B3a退出旧实例抽屉状态/事件、重复模块卡导航/renderer、home运行副本DOM/renderer/SSE刷新与侧队列投影。保存复用既有upsertWorkspaceInState和run merger，不新增目录/保存器。旧home纯markup候选与form_actions/run_actions内无DOM的optional兼容绑定暂保留；须按消费者核查另片退出，不因此宣称app/CSS已整体去重。
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
### G24 · P2 · 网页实时更新重复保留同一步骤占位（N13A 已修复）

- 对齐 R06/R12，类别：状态呈现错误，证据 E1/E2。
- 本次 Chromium 实际点击运行 Job→报告链，后台始终两步、计算实物计数 1；页面从未绑定任务到 Job/Agent ID 的过程中，compute/report 各保留一份 pending 占位。正常结束时实时 DOM 有 4 行，既显示已完成又显示未运行；重新打开页面的完整快照恢复两行。
- workspace_run_state_merge.js 的 stepMergeKey 优先 job_id/agent_execution_id，再退回 node_id+index；身份随绑定变化，mergeSteps 又追加旧 key，导致占位未退出。此前仅检查页面内存中的 run 终态或进度，没有断言实际 DOM 行数，未覆盖这个缺陷。
- 方案：单独交付稳定 step/attempt 身份的合并修复，保留历史记录和实时事件边界；对待执行→绑定任务→终态、Agent 绑定及旧记录做真实浏览器验证。不能用强制刷新、隐藏重复行或删除测试来代替修复。N13A 已作为 N03B2c1 后的独立前端小片验收；新隔离实例正常/失败/重启的实时 DOM 均为两行。当时交接 N13B1；现其验收见 G26，当前下一片 N03B2c2a-UI（授权后端验收见第三部分2.29）。

- N13A 实现：step_id 优先、node_id/index 兼容；绑定的 Job/Agent ID 不再改变计划步骤身份。单步 SSE 保留可选 step_id/attempt_id，未更新的另一计划步骤继续保留；新 attempt 不继承旧任务/输出/错误。已知节点冲突不合并；缺 attempt 的历史事件不能把已知 attempt 改绑到另一任务。没有新增通用版本协议，迟到完整 run 快照仍沿既有时间/终态保护。
- app.js 的步骤 key/合并 fallback 已退出，原消费入口只委托唯一 helper；其他尚有消费者的投影 fallback 保留待 N13 后续收敛。历史真实旧 run 只读合并检查通过，未在本片重新执行旧任务。G25/G26 与无版本事件的一般排序不因本片关闭。

<a id="g25"></a>
### G25 · P2 · 成功 Agent 的完成说明被写成错误（后端与独立 UI 已修复）

- 对齐 R09/R12，类别：错误字段语义与页面误导，证据 E1/E2。
- 原复现：成功报告同时含 status=done 与 error="agent node executed"，页面将完成说明显示成红字。N16A 新正常链公开 step 已为 detail="agent node executed"、error=""，真实失败原因仍显示；不能把原红字解释为模型失败，也不把字段修复算作独立前端阶段完成。
- N16A 在唯一 run_steps 构造/归一化层保留 detail，将明确 error/reason 和非成功/负向信号的原因留在 error；不改执行终态。仅旧 agent/done、没有 detail 的精确自动说明且无负向信号时兼容提升；recorded_error 保留原值，SQLite attempts.result 与历史 events 不改写。取消/超时/校验错误/未知调用/工具失败不清洗，其他旧错误原样。run/list、事件压缩、回放/导出和 JS 消费字段同步，无第二清洗器或 CSS 隐藏。34 本地契约、三条真实按钮流程及真实历史账本不变检查见下文；N16A-UI 已独立验收说明、错误和历史来源，见下文；其他错误契约不因本片扩大。

- **N16A-UI 已验收**：列表与回放使用同一无状态说明组件，精确自动说明译为普通中文；非空error始终显示，即使status=done。同文detail/error仅留错误一次；recorded_error按需查看、安全转义，原文不当当前错误。回放不再裁180字；历史说明正文覆盖旧回放p红色/单行规则，四视口真实滚动可到末端。展开键区分列表/回放、run/step及可用attempt；回放API无step_id/attempt_id时按已有run/node/index退回，不增加后端字段。仅该历史summary焦点在列表重绘时保持，未改全站焦点系统。
- 本地11项JS契约、10项浏览器主检查与8项两区域滚动补验通过；正常/exit7/坏JSON/历史run经可见入口、回放、导出、刷新核对，串行只读检查原attempt/Provider计数不变。长文是明确DOM布局注入，包含真实LF；不是运行产物。唯一新链由可见按钮与默认门禁启动，Job1/受控Provider1，自动完成、重连后终态正确；首次20s仍pending导致观察超时，约55s后才受理Job，未捕获连续终态SSE，不能写成完整实时过程通过。原始失败与修正仅留本地。

<a id="g26"></a>
### G26 · P2 · 配置与运行界面混杂，多层容器挤压主要内容（部分修复）

- J1-UI新增E1：回放Enter加载后焦点落BODY；N04-K2已定位为busy原生disabled阻止既有reader同步恢复，现仅该焦点职责限定修复，详见N04-K2记录。G26其他范围不关闭。
- K2新增E1：回放请求期间切到空实例，旧响应不抢焦点/实例，但全局消息仍显示旧实例“回放预览已加载”。`loadRunReplay/toggleRunReplay` 的提示未按当前选择隔离；后续单独处理迟到提示归属，不混入本片。E2风险：单全局busyKey可被另一run请求覆盖，本片只验证同key重复拦截及切run不抢焦点，不宣称跨run并发去重。
- 对齐规格§3/C13/R12，类别：功能入口错位、布局与可用性缺口。原阶段截图的拥挤/空白与 N13B1 的真实浏览器点击是 E1，HTML/事件/样式检查是 E2；当前实例与全局运行阅读区已分别验收，不宣称全站完成。
- **N03B2c2a发现的完整启动入口缺口已由 N03B2c2a-UI 修复**（第三部分2.30）；随后真实旧实例点击揭示 G11 的 `required_tool_unbound/report.write` 误报，已由 N03B2c2b 修正。N03B2c2c-UI 是后续历史候选；先准备 execution bundle ready、`tools=[]` 的隔离实例，再经可见入口验收提交到本次 run 阅读。旧 markup 无消费者问题已核对，不再另造提交器。
- **N13B1 已验收**：当前实例的运行列表、步骤详情、日志、回放、比较与导出从配置表单/抽屉移至顶层“运行记录”。驾驶舱同级入口直接到达，可选择实例、去编辑、返回；配置的旧记录页签/模块卡片与包住全部记录的 workspaceRunDetails 已退出，旧动作跳到同一个阅读区。复用唯一 run renderer/merger、现有日志与订阅，没有第二套推进器或轮询。无消费者的旧运行工具栏滚轮分支、workspace-runs-panel 单个选择器与卡片统计变量同步退出。
- 原四张统计卡、最新任务/命令块改成文字摘要，计划步骤在主阅读顺序，次要输入过程、交付和事件按需展开。限定阅读区的样式修正了旧 grid 规则把按钮竖排造成的空白。原生 summary/按钮的点击和键盘不再误激活整行日志，展开状态在重绘中保留。
- 本次基线复现刷新清除已选实例；现改为恢复并核对实例 ID，过期 ID 回到明确空状态。比较基准和回放选择只保存 ID，不保存日志/正文；刷新后的“加载回放”一次沿既有 API 获取正文。旧 runs 页签迁移落盘为规范值，避免以后每次刷新强制返回记录页。
- **仍待处理**：实例高级编辑的页面归位已由 N13B3a 验收，工具保存缺口已由 N13B3b1 限定验收，工具配置说明与反馈已由 N13B3b1-UI 限定验收，工具与 Agent 来源元数据已由 N13B3b2a/b 验收（G27）；N13B3b2c-Model 后端空值契约和 N13B3b2c-UI 空/有效/无效引用呈现已限定验收。N13C1/N13C2/N13C2-UI、N03B2c2a-UI 与 N03B2c2c-UI 已分别限定验收，N03B2c2b 修正 G11。全局概览已由 N13B2 从配置中心退出，见下文。390px 下阅读区不横向溢出，但全站侧栏占首屏较多，属于后续导航布局验收，未在本片重做。G15 组合根/样式债继续开放；G25 源字段已由N16A修复，独立说明界面已由N16A-UI验收；G06 当前报告文件已由N07A补齐，独立阅读界面已由N07A-UI补齐，长报告仍待后片。
- 新隔离实例的成功/退出7/真实服务重启/同实例第二次运行经过实际按钮、默认门禁、HTTP/tmux；实时两行，Job 启动增量各1，受控报告接口调用增量1/0/1/1。14项页面导航检查和5项边界检查通过；1440×900、1280×720、768×1024、390×844 阅读/返回与宽度核对，实际长名称、63583字符进程日志和显式注入的长HTTP错误有本地截图。受控 Provider 非真实模型，故障注入不算真实后端故障恢复。
- N16A联调单次观察：页面初始化期间的早期工作台选择之后，运行入口变隐藏，可能被持久UI恢复覆盖；自动化改等可见“已配置”后正常点击通过。N16A-UI分别延迟初始status和第二次bootstrap refresh的真实响应再点击，均未复现；保留原单次观察为待定位风险，不宣称已修。后续若再次出现先固定请求/恢复时序，再独立切片，不混入说明呈现。
- N13B3a复验出现初始化持续“等待数据”（E1）；当时/API status直连HTTP200约5.9秒、5.23MB，loadStatus请求序号只收最新、周期请求可连续作废慢响应（E2机制，尚未隔离到完整因果）。清掉6个本轮重复无run测试实例后约3.84MB/3.40秒，独立旧格式迁移及reload通过；未暂停poll、未调低门禁。目录变小是环境清理，不是产品性能/饥饿修复，较大目录与多窗口仍待独立切片。
- N13B2 已把全局概览 renderer/actions 迁至 workspace，删除配置目录旧文件、app中的重复fallback/无调用者包装、旧配置卡片/引导/页签。保留仍有消费者的其他配置渲染和全站旧样式，不凭相同selector删除。N07A/N07A-UI 已分别完成本地文件与独立阅读；实例编辑归位另由N13B3a验收，不把三个页面职责同时重构。

- **N13B2 已验收（R12）**：运行记录增加“当前实例 / 全部实例”，跨实例列表可筛选并精确定位run，Job直读本条日志；精确选择只保存ID，run detail仍经原merger。缺失/不匹配响应显示错误和重试，不回退最新；切换实例/新选择后的旧响应不能抢回选择，放弃读取后返回可重读。异步GET成功/失败后交接键盘焦点，加载期间用户移动焦点则不抢回。概览用请求序号与筛选快照拒绝迟到响应（该API没有revision）；进入/手动刷新及原已选实例SSE debounce共用唯一请求，无新增轮询/全局订阅，其他实例变化需手动刷新。仅原报告API核对文件，无正文持久缓存。
- N13B2实际只读浏览24run/24Job，跨实例、回放/导出/报告返回与reload、失败重试、A→B请求逆序、离开重入、键盘焦点/同DOM节点刷新、配置无概览请求通过，账本attempt和Provider调用未变。孤立/删除实例Job仅注入概览归属，日志来自真实Job；>12项仅注入13个较新快照条目，精确读取真实run，非执行13条任务。四视口长名称和长HTTP错误经真实wheel及祖先clip交集核对末端可见；当前阅读区四视口另验。脚本/结果仅本地，边界及过程见第三部分2.21。


- **N13B3a 页面归位与保存回执交接已验收（R02/R12）**：顶层“实例编辑”与全局配置分开，唯一实例表单保留项目/工作流/Agent/工具/AI五个子编辑器，退出外层details抽屉、重复导航、运行概览和侧队列。显示真实实例ID、模板来源及快照建立时间，明确当前没有配置revision；保存影响后续运行，不改写原run。返回同实例保留原run/报告选择并重新GET正文，新建/换实例返回驾驶舱，不把旧run绑定新实例。
- 验收发现原保存POST已成功但选择/表单ID仍空（E1）：保存等待全局refresh，被周期status序号抢先后select未找到新实例，却显示成功。现直接验证POST回执身份、复用唯一目录upsert，失效保存前的在途monitor，再交接选择/成功反馈；不再把整机监控当保存屏障。保存A期间切B不重灌B草稿或显示B已保存。工具payload随后已由N13B3b1接通；同实例多次POST逆序、在途继续输入与刷新草稿仍未修复，见G27。
- 真实浏览器检查原报告→编辑→返回/reload、全局配置/驾驶舱入口、新建正常保存、POST失败后正常重试。模板来源与非空snapshot通过真实隔离模板实例保存/reload核对；另对已有历史run/attempt只读核对不变，两组证据分离，未动态验证“同一被保存实例既有历史”。完整Agent/tools/model不变检查实际失败，未改为全通过；差异见G27。本地证据dev_work/artifacts/n13b3a/，过程和布局边界见第三部分2.22。

- **N13B3b1-UI限定验收**：工具域由三处新增、重复统计/类别卡、details内双限高滚动改为唯一新增/补推荐入口、稳定原生选择框和唯一编辑器。原生键盘选择不重建select，保存后保留有效当前项；新增/删除焦点实际可见。四视口1440×900、1280×720、768×1024、390×844经真实wheel及祖先裁剪交集检查，长标题/错误末端可达，无工具域横溢/内层限高；textarea保留原生编辑滚动。空草稿只注入验证布局，没有宣称后端支持删除最后工具。Agent/AI域原details保留。正常增改删/原POST503重试/reload及run/attempt/Job/Provider/snapshot不变通过；8组浏览器与6组布局检查，失败日志和明确替身边界见2.24。本片不修G26初始化或手机全站侧栏。

- **N13C1周期请求去重已限定验收（R12/R14）**：真实status先返回并启动原2秒timer，Provider查询仅延迟原响应7秒；修前11.716秒Provider已释放，后续多个status也返回，到约20秒仍“等待数据”、seq9/busy5。首次status本身慢时timer尚未启动，不能混为同一初次饥饿，也不能把受控机制说成历史60秒事故唯一成因。现唯一周期回调仅在既有statusBusyCount为0时发起loadStatus，忙时沿用在途请求；正常完成后下一tick继续。原两道seq准入、保存回执屏障、显式刷新与run合并器不改，无新轮询/队列/缓存/依赖。
- 原服务/23实例/2秒配置不变：正常空storage进入、未保存工具输入与选择保持、reload、7秒Provider横跨至少3个真实tick、两次后续5秒status及7秒tmux尾部、503可见错误/原按钮重试/续poll、双空storage窗口均通过。只读MutationObserver另证两次慢status实际更新header（seq3/4），不拿返回/idle代替渲染。真实原表单POST证明两道保存屏障；Provider屏障与初始逆序使用显式原函数触发时序，只算受控兼容契约。历史done run/SSE实际读取及浏览器内旧事件注入后仍done/两步；现有run没有公开数字revision，本片没有补版本协议或持久终态。
- 7项Node时序契约、120JS语法/HTML装配/386ID通过，原24run/48attempt/24Job、模板snapshot、Provider调用保持。本片只改app周期回调、HTML缓存query及二/三文档4路径。观察器关闭时route异常、两轮观察窗未等到响应、误用不存在selector/全列表计数的失败保留，修本地观察后验收，未调门禁/停poll/清原实例/补记录。脚本与原始证据仅本地dev_work/artifacts/n13c1/；内部调度没有新增页面字段/动作/导航，记录独立UI设计片豁免但实际浏览器回归完成。
- **N13C1时记录的静态风险**：原fetchJson无deadline，busy包含Provider/cockpit/tmux，挂起可能持续阻止周期请求且按钮本就禁用；现指定loadStatus链由N13C2补齐预算，见下文/第三部分2.27。其他独立调用未自动获得此预算，不能把单链修复当全站网络已受控。Provider普通错误的回退、初始化前早期交互、SSE/单机刷新旁路、后端性能与配置竞争仍开放。


- **N13C2指定状态链预算已限定验收（R12/R13/R14）**：config/选用TOML的app.status_load_timeout_seconds默认30，严格整数1–300；Handler在首页/直接index与HEAD送安全数值meta、no-store，首次status还没返回即有预算。每次loadStatus只创建一个原生AbortController/单调绝对deadline，贯穿status/refresh→必要Provider/cockpit→tmux与JSON正文；同signal传原fetchJson主实现/兼容fallback。子读取开始、结果入状态、catch回退前检查同一deadline，不把超时吞成缓存成功。finally清timer/计数，既有seq/保存屏障保留，尾部再核seq才可返回true；bootstrap仅完整成功后后台force，失败不再无条件跳过Provider/再等一次满预算。
- 实际本机config15（忽略文件中的明确测试参数，不改原2秒poll/23实例）下，四阶段持有原响应均原生net::ERR_ABORTED、可见超时/同seq busy0，原按钮在旧响应仍未释放前可正常重试。真实HTTP代理只传200/原正文前16字节后保持连接，约15秒浏览器取消且代理收到EOF，证明正文读取也受控；代理不是产品恢复服务。4/4/6秒分段有限延迟在15.355秒总截止取消tmux，没有逐层重置；7秒Provider慢响应仍正常。正常无route、双空storage、未保存选择/输入、原POST保存压过旧monitor、名称还原/reload、历史done两步/内存旧事件兼容通过。
- 18项本地Python配置/HTTP契约、12项Node原函数预算/取消/成功语义与两个原客户端合同、7组浏览器加4组预算/保存/历史、1项真实正文等待通过；compileall与120JS/386ID/HTML装配通过，根pytest无用例退出5不算通过。原24run/48attempt/24Job/snapshot/Provider不变。测试/本机配置/失败日志/截图只留dev_work/artifacts/n13c2/；一次同状态重启仅加载后端代码，不作运行恢复证据。首轮tmux“此刻busy必须0”断言与下一合法poll竞争失败保留，按同seq timeout观察busy0及更高seq的新请求复验，不停poll或修改计数。
- **剩余边界**：取消的是浏览器等待，不撤销已开始的服务端GET/任何任务；同步JS不可抢占，只在后续check拒绝越预算成功。非预算独立读/SSE仍原行为。尾部seq检查只阻止旧加载继续render/返回成功/触发后台force，cockpit/tmux既有helper仍可能先写投影，未补全子读取世代/选机快照；一般revision/配置竞争未修。超时目前沿原错误区最小显示，当时交接N13C2-UI，现其独立界面验收见下文/第三部分2.28；N13C2本身不作UI已交付的证明。G26继续部分修复。


- **N13C2-UI读取反馈已限定验收（R12/规格§3）**：沿已评估frontend-design，页头保留快照时间和主机连接信息，原刷新按钮有“刷新状态/读取中/重试刷新”文字；主滚动区只有一条读取说明及必要的完整错误，不套卡片/抽屉或局部滚动。新status_load_feedback.js只接显式投影/DOM，无网络、定时器、全局业务状态或DOM缓存。loadStatus按真实结果/timeout code/seq接UI，自动重试保留上次原错误直到当前整链成功，保存作废只解释被替代，不冒称成功；错误不再把主机标为api error。首次无快照显示“主机状态待读取”，不把读取超时当主机离线或任务停止。
- 旧450ms视觉余留与专用timer、仅增减无消费者的statusManualBusyCount退出，按钮disabled/aria-busy只由实际busy决定。force包含自动请求，不能当用户操作；原按钮/初入显式feedbackSource决定读取开始及普通成功的必要朗读，失败与恢复另行通知，正常poll安静。正常loading/ready说明一致，避免2秒poll造成固有高度变化。真实键盘发现native disabled丢焦点，现仅在本次开始时原按钮确有焦点才获归还资格，用户Tab/点击/移开即撤销；finally先清监听，当前seq/idle/按钮可用/文档聚焦可见且仍BODY才preventScroll归还。自动poll只归还它禁用前已有的焦点，不抢其他控件或窗口。
- 实际通过：22项本地Node原函数/原客户端预算兼容及投影/seq/朗读/焦点监听异常清理；9组真实浏览器正常、7秒有限慢、首读/手动tmux挂起15秒native取消/原Tab+Enter重试、原poll保留错误、双窗口、草稿/历史；5组布局包括1440×900、1280×720、768×1024、390×844的正常/长HTTP错误真实wheel至末端、literal markup不执行/键盘重试，以及真实已有4000字报告在390下scroll1164→1164经3次原2秒poll。另5种焦点结束/移开和3组持续poll焦点检查，CDP只读listener数量回基线。121JS/392ID/HTML装配、292源码台账/27问题/正式链接与六路径安全范围检查通过；本地静态成果页14个证据链接经真实浏览器逐个点击HTTP200。原23实例/24run/48attempt/24Job/snapshot/Provider不变，无新任务/模型调用；config15/2秒poll不改，测试脚本/原始失败/截图只留本地dev_work/artifacts/n13c2ui/。
- 过程与边界：首次初读poll变量实际默认5000（尚未拿配置/启动timer），测试误断0失败保留；tmux短timeout被下一合法poll切换，改同seq只读observer核timeout/busy0，不暂停poll/延长状态。早期scroll0只能证明零位置，后用真实长报告非零1164补足；键盘实际掉焦点后才补接线，不在测试中人工focus恢复。pointer-away脚本误用不存在sortSelect已改实际serverSortSelect，旧失败保留。另有一次新窗口“state is not defined”，原轮未留充分脚本网络信息，原因未定位；后续窗口记录121脚本HTTP200/无pageerror，不将未复现称为已修。纯前端未重跑无关Python/pytest。非预算读取、子读取世代/选机快照、性能、一般配置并发、早期交互和全站侧栏仍开放；当前下一片以文档顶部执行指针为准，G26不关闭。

### N04-M1-UI 取消页面限定验收（G04/G26/G37，2026-11-06）

只改 app.js/index.html：取消消息明确“信号已发、以步骤状态确认、已提交子任务需单独停止”。原取消入口的全量 loadStatus、直接 cockpit 刷新和额外 render 退出，改为唯一 monitor-only loadStatus，由既有 K1 reader 接受快照后重绘。保留原编码请求、持久状态、报告同步与 Job 日志；没有客户端终态、新轮询或第二合并器。迟到取消成功/失败只对原选中实例提示；切走不强绘新页。终态移除取消按钮时，仅原焦点仍在该动作且同 run/node/execution_id 持久 done/failed/stopped，转同 run 回放按钮；用户主动离开不抢回。

最终源码真实 Chromium 九分支：parent/child/follow/timeout 在 `dev_work/artifacts/n04m1ui-final-20261106-211912/`；switch/error/away/draft/switcherror 在 `dev_work/artifacts/n04m1ui-cases:switch:error:away:draft:switcherror-20261106-212048/`。每条从原页面启动 CPU 计划，原 Enter 取消（timeout 自然到期），受控 HTTP Provider 延迟返回固定观察窗口；没有补终态/关门禁。返回前步骤仍 running；返回后父或 follow 才 stopped，timeout 为 failed，完整分母2且非100%。父取消/超时零Job，已有child保留1真实运行Job及日志，follow取消父done；每条正式同键重放、服务重启/reload不增attempt。已有child验收后经真实停止接口清理，不冒充父取消传播。

parent/child/follow/error 的原取消焦点到同run回放按钮，跨2400ms周期更新保持；Tab离开、切空长名称实例及迟到503不抢焦点/串提示；在途取消响应期间进入实例编辑、输入未保存名称，响应后名称及输入焦点保持。1440×900、768×900步骤截图已核看，无pageerror；空实例/长名称和长错误仅本片入口覆盖，不代表全手机导航通过。取消本身额外Provider/cockpit读取从基线1/2降为0/0；switch/switcherror各2个cockpit是切出/切回导航读取，draft为0，不能算作取消冗余。补充 `dev_work/artifacts/n04m1ui-cases:error-20261106-212247/` 实际滚到消息首尾，长错误自然换行且末端可见；768信号说明截图已核看。页面消息位于列表上方，滚到步骤时可能不在视口，后续可另片迁到动作邻近反馈。草稿截图还确认现有setWorkspaceMessage会把同实例取消说明写入实例编辑的公共消息区；运行反馈与配置提示尚未完全分离，仍归G26后续。本片不称提示全程可见或全站布局完成。

本地纯JS覆盖原编码路径、同实例成功/失败归属、monitor-only请求、quiet/空ID、终态身份不符/仍在途不fallback、主动离开不抢焦点；J1UI/H/G/K1契约、121脚本装配和app语法通过。K2真实回放回归 `dev_work/artifacts/n04k2-terminal-20261106-212122/` 的busy/成功/失败/重试/Tab/切实例与run焦点通过，仅复制历史数据阅读，不是新执行链。纯前端未重跑无关Python。第一次最终全分支进程在switch中退出143且已无存活句柄，只计已落盘的四分支；剩余五分支独立重跑通过，未把中断当pass。先前六分支记录211319仅作补充，不替代最终代码断言。

调用者消融：真实入口是 workspaceRunList → 原detail_actions → cancelAgentExecution；workspaceHomeRunsMarkup无调用且index无对应DOM，不保留假想兼容刷新，本片也不越界删除死markup。旧消息容器、其他动作的刷新、Job独立停止/日志保留。Provider为受控接口，延迟/一次浏览器503仅为故障窗口，不证明真实供应商理解、网络强停或产品暂停恢复。脚本/配置/结果仅本地；第一部分不变，G04网络预算/G36/G33/精确通知仍待后续。

<a id="g27"></a>
### G27 · P2 · 实例草稿、配置完整往返和保存竞争仍有缺口（部分修复）

- 对齐R02/R03/R12/R13，类别：配置丢失/来源变更风险、能力缺口；不是页面归位已完成的证明。
- **E1，草稿仍未修复**：已有实例修改name后同实例切页往返保留，reload重新选择后未保存name丢失。工具编辑原漏tools（E2）已通过真实新增→POST成功→GET丢失复现（E1）；N13B3b1现将当前tools draft接入唯一整实例payload，限定正式保存验收见下文。不把目录注册当执行能力。
- **E1，部分修复**：通过正式API创建有非空template_snapshot的隔离实例，仅改name/references后真实POST：snapshot本体保留，但6个Agent的created_at/updated_at/description丢失，27个工具的created_at/updated_at丢失，model.chat_agent_id从空变researcher。节点dataset_hints随references同步是既有显式规则，不混称无关损失。原完整域不变断言失败记录保留；N13B3b2a已修工具已有来源时间，N13B3b2b-Agent 已修同ID Agent 来源元数据。
- **E1，N13B3b2c-Model 后端契约已验收**：隔离服务正式 API 确认缺少 `chat_agent_id` 时保留 existing，显式空/空白清空，合法与未知但语法合法 ID 沿既有 `safe_id` 规则保留，其他 model 字段不变。首次夹具把模板入口忽略的顶层 `model` override 当成已创建基线，断言失败并留下隔离实例；随后按精确 ID 在隔离服务正式 DELETE，并 GET 确认不存在。监督代理只读复核 API 契约；`python3 -m compileall -q total_control`、`git diff --check` 通过。pytest 无用例，未记通过；脚本/证据仅本地 dev_work/。
- **E2，N13B3b2c-UI 已限定验收**：实例编辑的模型选择不再因初始化、更新或新增 Agent 自动选首个 Agent；未设置显示“未指定”，有效引用显示名称，未知但语法合法 ID 在模型选择和隐藏的兼容投影中显示“当前引用不可用”，并保留原值直到用户显式选择或清空。删除当前 Agent 后引用明确清空并提示。真实浏览器在隔离 `TOTAL_CONTROL_DATA_DIR` 服务中验证未知双选择器、空值 POST→GET→reload、键盘选择/清空与焦点、有效选择同步、新增不接管、删除清空、正常保存 reload、单次 POST503 后原表单重试、1440×900/390×844 几何可见性；9项检查通过、无 pageerror。执行脚本与截图只在本地 `dev_work/artifacts/n13b3b2c-ui/`，未调用 Provider/SSH/GPU。运行驾驶舱的 `workspaceUseChatAgentSelect` 仍是本次运行的临时 Agent 选择，不绑定实例 `model.chat_agent_id`；编辑器旧 `workspaceChatPanel/#workspaceChatAgentSelect` 当前没有可见 tab 入口，记录为后续消融候选，不把死入口当作第二配置消费者。
- **E1，本片已修复最小回执交接**：新建POST201后显示“已保存”而form ID/选择空。N13B3a去掉非必需全局refresh等待，直接采用本次权威回执；更新回执缺ID/错ID拒绝，不fallback到当前实例冒充成功。旧monitor响应与跨实例晚到保存分别通过真实延迟响应验收。原失败保留，不用手工reload/重选补成功。
- **E2/E3，未修复**：同一实例多次保存逆序、保存途中继续输入、两次未绑定空草稿共享空ID，仍可能覆盖新意图；当前只保护跨实例选择。接口无配置revision/乐观锁（E4），快照created_at或updated_at不能当配置版本。Provider内层编辑仍有真实消费者，“只写localStorage”文案与服务端持久化不符（E2），本片不搬密钥。
- **N13B3b1已限定验收（R02/R03/R12）**：唯一payload增加tools深拷贝，沿原POST/normalize/回执，无新API/目录/保存器。一个非空模板snapshot隔离实例经可见增改启停、重命名被researcher引用的repo.search、删除被repo-scout/env-builder引用的file.read；六次真实保存及API/普通reload/串行全新空storage上下文核对业务字段、ID和精准allowlist，snapshot不变。新custom/改名ID的implemented=false，未伪造适配器。只读盘中配置对齐，原run/attempt、Job和Provider调用不变。POST503注入后服务端不写、原入口重试成功。
- 过程边界：首轮双context时新页60秒持续等待（G26），失败保留；后轮关闭原context再开单窗口空context通过，不宣称多窗口初始化已修。复验仅经正式POST恢复本轮无run实例的tools/agents/model配置，无终态或执行证据补写。基线首次保存已正规化，元数据首存缺失仍以上述原证据为准；有效非空唯一ID之外、最后一工具限制/非法ID冲突均未修。证据仅本地dev_work/artifacts/n13b3b1/；实际10项与限制见第三部分2.23。
- N13B3b1-UI真实新增保存发现工具选择跳回首项（E1），现同实例原回执分支传已有selectedToolId、由原draft设置器校验有效ID；正常保存后无需脚本重选。新增/删除焦点复用原滚动内核，四视口可见。并未解决同实例在途输入/逆序响应。首轮失败及正常删除临时定义证据均保留。
- **N13B3b2a工具限定保真已验收（R02/R03/R12）**：真实新模板首次可见name/references保存复现27工具来源时间全丢；工具normalizer现仅保留同ID existing中的非空字符串created_at/updated_at，不从请求导入、不生成/触碰时间。新ID/改ID不继承别ID时间，global wrapper仍拥有全局更新时间。全新模板首次无关保存27工具记录全等；工具编辑/增改ID/删/503重试、reload/新空storage/重启再保存、API与盘核对通过。原allowlist仅显式ID改删精准变化，snapshot及原run/attempt/Job/Provider不变。来源时间不是实例编辑时间/revision，已丢字段不回填。Agent/model首存差异仍实际存在。9组浏览器、真实POST伪造时间/未知字段检查、8局部契约通过；compileall通过，根pytest无测试退出5不算通过。本地证据dev_work/artifacts/n13b3b2a/，详见第三部分2.25。
- **N13B3b2a工具限定保真已验收（R02/R03/R12）**：真实新模板首次可见name/references保存复现27工具来源时间全丢；工具normalizer现仅保留同ID existing中的非空字符串created_at/updated_at，不从请求导入、不生成/触碰时间。新ID/改ID不继承别ID时间，global wrapper仍拥有全局更新时间。全新模板首次无关保存27工具记录全等；工具编辑/增改ID/删/503重试、reload/新空storage/重启再保存、API与盘核对通过。原allowlist仅显式ID改删精准变化，snapshot及原run/attempt/Job/Provider不变。来源时间不是实例编辑时间/revision，已丢字段不回填。Agent/model首存差异仍实际存在。9组浏览器、真实POST伪造时间/未知字段检查、8局部契约通过；compileall通过，根pytest无测试退出5不算通过。本地证据dev_work/artifacts/n13b3b2a/，详见第三部分2.25。

- **N13B3b2b-Agent 已限定验收（R02/R03/R12）**：`normalize_workspace_agent` 仅从同 ID existing 保留 `description`（包括空字符串字段）、`created_at`、`updated_at`；客户端不能覆写，新 ID/改 ID不继承。以隔离默认模板创建的6 Agent（描述均为空字符串且字段存在）经真实编辑页只改name/references并正式POST，GET/reload与实际workspaces.json均保留三项来源元数据；请求本身不含这些元数据。另在正式API路径检查同ID伪造、新Agent伪造与改ID不继承，原表单一次POST 503后重试成功，失败时后端原值不变。template_snapshot与allowlist始终不变；隔离起始无run/attempt/Job，结束仍为空；Provider文件原本不存在且未调用。浏览器无pageerror。全流程共6组检查，脚本仅在 `dev_work/smokes/n13b3b2b_agent.py`，前后证据仅在 `dev_work/artifacts/n13b3b2b-agent/`。用已安装依赖的Python 3.13 venv compileall通过；仓库pytest无测试并退出5，不计通过。模型空引用、已有运行证据下的保存、真实Provider/SSH/GPU及N03网页闭环未测，分别留待后续。
- **N13B3b2c-Model 后端片已验收（R02/R12）**：`normalize_workspace_model` 以字段是否存在区分缺失与显式空值；未传 `chat_agent_id` 沿用 existing，显式空或空白清空，非空值照旧 `safe_id` 规范化且不在此层检查 Agent 是否存在。隔离正式 API 验证后其他模型字段不变，测试遗留实例已正式删除。未增加 helper、API、依赖或状态；历史开片时的前端自动首选、Agent 增删联动及无效引用呈现已由 N13B3b2c-UI 处理。此片未动态覆盖已有 run/attempt/Job/Provider 的非空实例，也未测试真实 Provider/SSH/GPU。
- 方案与顺序：工具说明与限定保真已分别验收（2.24/2.25）；N13C2状态加载网络预算已限定验收（第三部分2.27），N13C2-UI已限定验收（第三部分2.28），此前计划的N03B2c2a-UI已完成（第三部分2.30），G11随后由N03B2c2b修正；当前下一片以文档顶部执行指针为准（G10；G26有限慢响应去重已验收见第三部分2.26）。Agent/model、草稿、同实例竞争、配置revision和Provider归属另立边界。不要为这些问题加第二套实例状态、保存器或三层重试。

### N03B2c2a-UI：显式授权说明与完整启动入口（本片已实现，边界验收）

- 对齐 R03/R06/R12、规格§3，关联 G10/G11/G26。后端 execution bundle 的 `ready_to_execute`/`missing` 是入口事实：ready 才显示“运行工作流”，缺项显示后端返回原因并提供自动推进/配置中心；在途 run 显示“打开当前运行”，不重复提交。
- 驾驶舱的完整入口复用原 `run-selected-workspace`、`WorkspaceWorkflowSubmission` 的 request_id/sessionStorage 幂等和后端门禁；提交成功后通过既有 `openWorkspaceFromExecutionOverview(workspace_id,{runId})` 进入运行记录，不再把首个 Job 日志冒充完整工作流阅读区。`open-workspace-run-reader` 只是既有导航动作，不是第二状态机。
- 授权说明只陈述稳定规则：实例明确拥有 `tools` 字段（包括空列表）按原授权保留；只有缺少字段时才采用有来源的推荐。页面不从当前已规范化 payload 反推某个实例的历史来源，不动态声称“此实例来自推荐”。运行记录不嵌入配置抽屉。
- 消融决定：删除 `workspace_form_actions.js` 对不存在的 `#workspaceRunFlowBtn` 监听，并移除 automation busy 列表中的同一死 ID；保留既有节点级运行按钮、旧拓扑诊断和所有真实消费者。启动入口只有 `workspaceLaunchClosure` 一处，事件仍由既有 action surface 委托处理。
- 真实浏览器：1440×900 和 390×844 均看到完整入口及授权说明；键盘聚焦“查看最近运行”后点击，实际切到 runs 并定位 `20261014-160812-34545369`，无 pageerror。点击“运行工作流”也实际发出 `POST /api/workspaces/20261014-141005-1c574764/run`，服务按旧发现门禁返回 409，未伪造成功；该实例的 `cockpit.next_action` 仍报 `required_tool_unbound/report.write`，属于 G11 未修语义。由于本机没有一个同时满足 ready、无旧发现门禁且无历史运行的隔离实例，本片未把完整网页提交→Job→Agent等待→报告的成功链记为通过；后端成功链证据仍以 2.29 为准。
- 过程检查：Node 通过 `/home/hzj/.nvm/versions/node/v24.13.0/bin/node --check` 检查 4 个改动 JS；`git diff --check` 通过；系统默认 `node`、`python` 不在 PATH，Python compileall 改动未运行，不能记通过。浏览器失败 selector/隐藏面板/409 记录均保留在本地 `dev_work/artifacts/n03b2c2a-ui/`，测试脚本、截图和结果不提交。

### G11 / N03B2c2b：报告 Agent 直出与 Job 工具写入边界（后端已修，待前端闭环复验）

- 对齐 R03/R05/R06。问题是 `workspace_node_required_tool_id(kind)` 同时承担“按节点种类推荐工具”和“按执行方式判断硬门禁”两个语义，导致已经支持的 `eval.report` + `handler.mode=agent` + `tools=[]` 被错误生成 `required_tool_unbound(report.write)`。
- helper 现在接收可选 `executor_mode`：报告 Agent 直出不声明静态 `report.write`，仍要求模型路由、输入映射、报告输出和现有 `report_only/single_call` 执行约束；`eval.report` 的 Job/shell 路径仍保留 `report.write`/`report_command` 门禁。其他节点工具要求未改变。
- topology 同步跳过报告 Agent 空工具列表的“Agent 没有可用工具”警告；这是该最小链的显式能力边界，不是把空 allowlist 泛化为所有 Agent 可执行。模板验证、workflow contract/context metadata 和节点所需工具定义回填也按实际 executor mode 使用同一 helper。既有 Agent preset 仍可补齐工具定义目录，但不改变 `agent.tools` 授权列表。
- 确定性检查已通过：mode-aware helper（Agent 空、Job 保留、其他节点保留）、Agent topology 为 ready 且无 `required_tool_unbound/agent_without_tools`、Job topology 仍登记一个 `report.write` requirement；`dev_work/n03b2b/venv-test` 的 `compileall` 和契约脚本通过，`git diff --check` 通过。xng/zuoye 默认环境缺 `langgraph`，直接从完整包导入无法运行，未把它记为通过。
- 消融决定：不新增第二个工具映射表、不把 Agent 直出改成工具调用、不删除既有 Job 报告命令；唯一模式判断复用 `resolve_node_executor_mode`。旧实例的真实 POST 409 和前端响应记录保留，下一片只复验 ready 隔离实例的网页提交闭环。

## 3. 验证边界与阶段状态

N13B1 本次独立前端片的证据在本地 dev_work/artifacts/n13b1/：四条实际运行、回放/比较/导出/日志引用、导航及长内容验证。正常链没有 force、手填终态或人工补报告；模型接口是明确标注的本机替身，只验证数据衔接。正常报告文件仍 incomplete，不能把脚本另存正文当产品交付。两次导航脚本的 selector/文案断言错误保留原失败记录，修正断言后实际复跑；监督发现的真实事件拦截和恢复缺口均修复后重新验证。4个相关JS语法、118脚本引用/顺序/ID唯一与 compileall 通过；根 pytest 无测试退出5，未记通过。其他历史能力的验证边界不扩大。

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

### N13A：实时步骤身份（独立前端小片，已验收）

只改步骤合并 helper、app 的该职责委托与 HTML 缓存引用。旧版本相同输入会保留 4 行，当前 20 项 Node 契约保持 2 行，并覆盖部分更新/已知身份冲突/新 attempt 隔离/旧记录字段/迟到完整快照；另读取 14f87a3 当时经真实 HTTP 产生的一份历史 run，只读合并后步骤/证据不变，没有重放旧任务。

新的本地 Chromium 默认可见按钮实测正常、失败、服务重启三例：最终步骤 done/done、failed/skipped、done/done；实时 DOM 均两行，MutationObserver 留存的各场景观测只出现两行；真实计算均一次，受控报告接口请求 1/0/1，pageerror 为零。正常/失败不刷新消重复，重启例仅在实际重启后刷新重连原 run/Job。Provider 是隔离本机确定性替身，不证明真实模型能力；工作区/Provider 通过正常 API 准备，配置在 config/n13a-local，未改门禁/手填终态或补记录。首次三例通过后，监督补查身份冲突边界，增补保护与契约，再用新隔离实例完整重跑；两轮证据均留本地，原静态成果归档不覆盖。

相关 JS node --check、118 个脚本引用/存在性/顺序、compileall 通过；根 pytest 无用例退出 5，不算通过。测试/截图/录像/结果在本地 dev_work/artifacts/n13a 与 smokes，不入 Git。该 N13A 片没有改布局、G25 红字或报告文件交付；第一部分稳定。当时交接 N13B1，现该片已验收，见 G26。

### N07A：当前本地报告文件（后端小片，已验收）

本片只接新 B2c1 run 的非空、验证通过、≤4000 字符回答。RunPlan 在副作用前冻结 config 的 report_output_dir，默认执行账本旁 reports/；相对路径从配置文件目录解析。既有 SQLite record_json 保存按 step/attempt 绑定的 prepared→verified/failed 回执，无新表/第二状态库。原 Agent 终态与回答保持不可覆盖；文件交付是单独事实。

一个 stdlib 文件适配器负责非覆盖发布、受控读取与实物核验；拒绝敏感路径、符号链接、目录/FIFO及不匹配大小/摘要，先校验大小再有界读取。临时文件 fsync 后硬链接发布，不支持该文件系统操作时明确失败；已存在相同正文可采用，不同正文不覆盖。当前投影每次核验实物，读取不会偷偷补文件。output.report_file 仅元数据，artifact 放当前已验证正文，新增受控 GET/report 从同一投影取正文；沿用已有导出，无额外正文缓存。

实际验收：18 项本地契约；4 条真实 Chromium 可见运行/日志/导出路径（正常、退出7、等待重启、同实例再运行），实时均两步，Job 增量各1、受控报告调用1/0/1/1；8项恢复/失败检查，包括原 POST 重发、各读取投影检测篡改/删除、写前/写后真实进程硬退出恢复、冲突、只读目录及冻结目录。另4类真实HTTP内容检查确认4001字/空/无效JSON失败且无文件、4000中文字符12000bytes成功，任意path参数不起作用、跨workspace返回404。最终重启隔离服务加载最新源码，浏览器再次实际点击导出并打开GET/report，正文、摘要、字节数与身份一致。

过程限制：正常路径保留默认门禁/auto_apply，无 force、人工补终态/回执。受控本机模型接口只证明执行交接；硬退出由本地 wrapper 注入，无生产测试开关。最初两个契约失败分别是测试复用了同一attempt写不同内容（修正隔离身份）和循环链接错误分类（产品收紧分类）；不以删用例通过。发布后清理临时文件失败不掩盖已验证交付。历史计划无目录不迁移；failed交付不自动重试；失物不自动重建。原声明工具由 dispatcher/debug 消费，保留至后续迁移/对照，不宣称 G06 全部关闭。

compileall 通过；根pytest无用例退出5，不计通过。本片不改前端、图推进器、Job入口或Provider协议。长报告/工具/子任务、真实AI/SSH/GPU、一般交付修复与各文件系统断电保证均排除。测试/配置/结果/静态展示只留本地 dev_work/artifacts/n07a/；原展示归档保留。第一部分稳定不改；当时下一片N07A-UI，现已验收如下。

### N07A-UI：本次报告的独立阅读区（已验收）

对应G06/R10/R12。运行记录的报告步骤提供“阅读报告 / 查看报告状态”，打开后正文区与列表互为独立子视图，不再套入配置或步骤折叠。顶部返回/重新核对/原导出，执行状态与文件交付状态分开，一层可选文件身份/摘要/大小证据。frontend-design继续指导任务布局，沿用本机字体/颜色，无新前端框架、外部字体或装饰卡片。

单一workspace_run_report控制器显式接收UI/选择/API/DOM依赖；只有workspace→run选择ID落浏览器存储，正文短期留内存。请求按workspace/run/attempt及请求身份核对，切换/关闭/离开模式后丢弃迟到响应；新失效快照清正文。相同快照不重建正文DOM，原生证据展开保持；加载失败清旧正文，不以inline回退。受管report_id在旧交付摘要中不再重复正文，legacy无report_id展示因仍有消费者而保留。

实际验收：4条真实浏览器可见运行链（正常、计算退出7、运行时重启、同实例再运行），Job本次增量各1、受控报告接口1/0/1/1，阅读/返回/重新核对/原导出均实际点击；另1条真实“打开等待报告→服务重启及页面刷新→自动显示已核对正文”链，重发原POST同run，计算/接口各1、正文textContent与API精确一致。11项隔离组件契约覆盖首换行/空白/转义、同attempt与新attempt失效、迟到/离开、身份不符、无文件状态及选择只存ID；它们不冒充产品任务验收。

15项浏览器边界覆盖真实损坏/缺失/冲突/只读目录无正文、键盘焦点和同快照DOM、刷新保留选择、跨配置返回、断网清正文/重试、注入长HTTP错误、迟到真实A响应不能覆盖B、实物删除后可见刷新清正文，以及4000中文字在1440×900、1280×720、768×1024、390×844的布局。真实N13B1历史run在当前服务重启后仍不补文件/不重放，实物计数和接口记录不变。119脚本引用唯一/顺序、396静态ID和4个相关JS语法通过；compileall通过，根pytest无用例退出5，不计通过。第一部分不变。

过程发现与修正：首轮旧display覆盖hidden让列表仍可见，已用reader直系hidden限定修复；loadStatus原resource-only分支拿到新workspaces但未重画报告，已接同一sync，实际可见刷新后清正文复验通过，未加轮询。首轮失败场景脚本强求观察5秒running而漏看，核对真实退出7/报告skipped后修观察条件，原失败证据保留说明，不延长命令/改终态；历史脚本误用全局selector撞隐藏摘要，改为作用域选择。文件变化本身不新增SSE事件/文件watch，接收新快照或点击重新核对后以实物为准；首次只等待无事件的删除观察未通过，不冒记通过。正文精确保留、焦点恢复和native toggle后的首次相同快照不重建由实际检查确认。

补验390×844真实滚轮到4000字正文中段、末端和文件证据，以及长HTTP错误中段/末端均通过。原长元素截图受祖先裁剪，改用实际视口截图；真实滚动还发现loadStatus请求前的旧scroll快照覆盖在途阅读位置，现仅当前报告/工作台resource-only响应后重取位置、沿用原同步恢复，延迟真实刷新响应期间wheel前后位置保持验收通过。阅读区无横向溢出且正文无局部高度/滚动限制；全站侧栏仍占首屏较多，继续G26后续，不在本片改导航。真实AI/SSH/GPU、长报告、一般交付修复仍未实现或未验证。脚本/配置/结果/截图/静态成果页仅本地dev_work/artifacts/n07aui/，旧归档保留。G06仅当前报告读取界面补齐；本片当时保留G25源红字，现N16A后端修复见下文，当时交接N16A-UI，现已验收见G25/第三部分2.20，当前唯一下一片 **N03B2c2a-UI**（授权后端见第三部分2.29）。

### N16A：成功说明和错误各自归位（后端/契约已验收）

对应G25/R09/R12。原来“Agent 已执行”这句说明被放进 error，成功任务也显示红字。现在公开 step 的 detail 保存执行说明，error 保存明确错误/阻塞/停止原因；明确给出的 error/reason 不因 done 清空。失败、取消、超时、验证错误、工具错误和未知副作用信号保守保留，不改变任何执行状态、重试或调用预算。

历史兼容限定为 agent/done、没有显式 detail、error 精确为 agent node executed 且无负向信号；只在读取投影中移到 detail，并用 recorded_error 留下原值。其它旧错误不动。重复同一快照及带已有投影归一化稳定；新 attempt 不继承旧说明/来源。SQLite 原 attempts.result、历史事件证据不改写、不重调模型；legacy JSON 的规范化表示保留原值字段，不再以原 error 当当前失败。新增字段为兼容增加，旧消费者可继续读取 error；完整原始尝试仍可从 run.attempts 查证。

保留单一构造/归一化入口；run_events 的裁剪摘要、run_records 的变化检测、run_replay 的显式 timeline 和 JS 事件压缩同步两个字段，导出复用既有 replay 无新副本。仅 index cache 更新，不做 UI 排版或新增说明展示；当前 error 控件自然不再显示那条错误说明，该后端片当时未做独立前端验收；现N16A-UI已验收，见G25/第三部分2.20。

实际通过：34项本地Python契约覆盖成功/警告、明确错误/原因、失败/取消/超时、校验/未知调用/工具信号、历史精确兼容/非匹配/重复原快照/新attempt、事件/回放/导出、账本原值不变；18项既有报告契约复验、4项隔离JS字段/新attempt契约通过。三条新真实Chromium按钮链：正常计算→受控Provider、计算退出7→报告skipped且不调用Provider、受控Provider返回坏JSON→Agent失败并保留解析错误。每条Job增量1，Provider增量1/0/1；默认auto_apply/门禁、无force/手填终态。run/list/replay、可见按钮导出、真实SSE run.updated全量steps与JS合并一致；原POST重发同run，实际服务重启后原attempt结果和副作用次数不变。另读真实旧N07A-UI成功run：顶层说明正确、recorded_error可解释，原SQLite结果/Job次数/Provider记录不变。compileall、相关JS语法与119脚本/396静态ID检查通过；根pytest无用例退出5，不算通过。

过程记录：首次观察器错求本链未产生的run.step.updated，实测为run.updated带全量steps；改观察真实事件，不增产品事件。step事件的两个压缩字段属于局部契约，未冒称真实发出。坏JSON首次脚本误求validation.status=failed；既有格式校验返回warning+解析errors，Agent会拒绝并产生failed step；核对真实错误后按failed step+非空解析errors验收，不改变校验器/终态。原失败记录及首次实际拒绝run均保留本地；另一次新页面初始化前点击被表单恢复切回，脚本改等可见“已配置”后正常点击，未脚本设置状态；疑似初始化恢复覆盖的早期交互竞争留G26独立复现/修复，没有补记录或重放来覆盖原证据。

证据只在dev_work/artifacts/n16a/；测试、受控接口、截图和本机配置不提交。受控Provider证明流程，不证明真实AI；取消/超时仅字段契约覆盖，未冒称实际外部取消完整实现。执行、预算、子任务、长报告、一般恢复均排除。第一部分稳定；当时交接N16A-UI，现已独立验收见G25/第三部分2.20；当前唯一下一片 **N03B2c2a-UI**，只补显式授权说明与完整启动入口（后端见第三部分2.29）。

## 4. 逐文件台账的读法

下面每行对应一个实际文件，列出需求、职责与输入处理输出、检查结论和解决路径。`保留`表示本轮未发现该文件的独立缺陷，不保证所有分支正确；`关联`表示参与某个问题的修补或验收，不表示文件自身一定有 bug。同一问题的详细方案只在 G 登记维护，避免在几百行表格重复且漂移。

证据栏采用源码中的具体符号和行号；对纯数据、CSS/HTML、转导出入口检查对应边界。文件的责任不由行数决定，框架替换也不能跳过这些接口与测试。

<!-- FILE_AUDIT_START -->

### total_control

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/__init__.py) · 5 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [agent_executor.py](../total_control/agent_executor.py) · 513 | R03/R09；Agent 输入/模型/工具/预算 → ReAct 循环与结果封装 → AgentExecution | N03B2c1 的 single_call 模式只调用一次、无失败 fallback，工具 JSON 在生成轨迹/副作用前拒绝，单调预算与返回后 cancel/deadline 检查；C1仅对明确protocol_error禁止非single_call再次chat fallback，非法JSON不能空success洗白；M1将普通/single_call的取消/截止构造收敛到原run局部guard，模型/fallback/工具/成功边界复核并保留已收usage/既有工具证据；单调总预算不重置；M2a把min(60,剩余)传入三处原模型调用，每次/fallback重新计算再guard，无预算不传；socket空闲等待接通但持续读取总期限G04与G21未关闭；构造/查ID未滤enabled为G11 E2风险。 | `_tool_side_effect:31`；`_metadata_value:39` |
| [agent_runtime.py](../total_control/agent_runtime.py) · 49 | R09；execution_id/取消请求 → 进程内注册与信号 → active/cancel 检查 | 问题/修补关联 [G04](#g04)、[G09](#g09)；按登记方案处理，不另建平行服务。 | `register_agent_cancel:20`；`cancel_agent_run:30` |
| [compat.py](../total_control/compat.py) · 21 | R14；公开门面名/默认实现 → 查询 override → 兼容调用入口 | 问题/修补关联 [G16](#g16)；按登记方案处理，不另建平行服务。 | `public_api_override:7`；`public_api_value:17` |
| [config.py](../total_control/config.py) · 340 | R01/R12/R13/R14；config/ TOML → 校验主机/路径及状态加载秒数 → AppConfig | N13C2增加status_load_timeout_seconds默认30、严格int 1–300（拒bool/float/string/非有限值）；首页先送预算。N07A目录/SSH兼容保留，无秘密透出。 | AppConfig/load_config |
| [constants.py](../total_control/constants.py) · 2 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context_refs.py](../total_control/context_refs.py) · 18 | R05/R09；数据和点分路径 → 字典键/列表下标查找 → 原值或 None | N00C 唯一纯取值内核；执行映射与上下文投影均已接入；不承担引用前缀或就绪规则。 | `context_ref_value:8` |
| [events.py](../total_control/events.py) · 207 | R12；业务事件/游标 → 有界队列、gap 与 SSE 编码 → 实时通知 | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `EventBroker:12`；`sse_encode:135` |
| [handler.py](../total_control/handler.py) · 197 | R12/R13/R14；HTTP/首页 → 路由/安全数值meta → JSON/文件/配置化HTML | N13C2仅/与/index.html由send_head替数值占位、no-store；GET/HEAD长度相同，其他静态保持。首次status前有预算，不新增配置API；原RunStoreError503/G19边界保留；I1静态核实默认抑制状态/静态GET日志，既有verbose仅用于诊断，历史无日志不代表无请求，未改本文件。 | Handler.send_head/do_GET |
| [llm_client.py](../total_control/llm_client.py) · 621 | R03/R09；Profile/消息 → 供应商请求、流解析 → LLMResponse | N00C 已删除无调用者的 simple_chat 包装；C1仅chat_stream明确JSON文本响应校验并复用_parse_response、同响应一次消费/整体回调、记录实际格式；非法/native结构protocol_error阻止Agent回退洗白，SSE/JSON真实链及失败门禁通过；其他协议维护与预算问题仍按 [G04](#g04)/[G21](#g21) 解决。 | `LLMResponse:17`；`ChatMessage:37` |
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
| [get_routes.py](../total_control/http_api/get_routes.py) · 470 | R12；查询路径/参数 → 调用状态服务、回放/下载/SSE → 查询响应 | N07A 增量 GET runs/{id}/report，按workspace/run取绑定文件投影、缺失明确不完整，不接受任意path；原回放/导出保留。G19/G20其余边界未关闭。 | `_workspace_jobs_snapshot:14`；`_workspace_stream_snapshot_event:27` |
| [path_utils.py](../total_control/http_api/path_utils.py) · 14 | R12；API 路径/前缀 → 单资源路径段匹配 → id 或空 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `single_segment_path_id:6` |
| [post_routes.py](../total_control/http_api/post_routes.py) · 434 | R06/R12；POST 命令 → 现有状态服务/公开封装 → 启动/配置响应 | N02 工作流 request_id/提交冲突返回 409；N04-H新增精确stop-continuation路径与body边界，参数400/身份或busy409，领域受理交service；M1a取消execution ID复用single_segment_path_id单次解码，非法单段400、inactive404；原encoded消费者不改。其余路由不批量改写，关联 [G19](#g19)。 | `_public_job_response:14`；`handle_post:30` |
| [put_routes.py](../total_control/http_api/put_routes.py) · 44 | R12；资源更新请求 → 匹配资源与调用更新 → 更新响应 | 问题/修补关联 [G19](#g19)；按登记方案处理，不另建平行服务。 | `handle_put:9` |

### total_control/infra

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/infra/__init__.py) · 5 | R01/R07；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [checks.py](../total_control/infra/checks.py) · 218 | R01/R07；主机/检查或停止请求 → 连接、能力、进程所有者检查 → 诊断或停止结果 | N00D 修正停止权限：正常信号优先，sudo -n 回退，ps 判存活；保留实时归属确认入口。 | `run_server_checks:21`；`build_process_stop_script:90` |
| [report_files.py](../total_control/infra/report_files.py) · 126 | R10/R11/R13；已验证回答/受控目录/身份 → 非覆盖发布、摘要核验与有界读取 → 当前文件交付视图 | N07A唯一受管报告文件内核；18项契约及真实崩溃/缺失/冲突通过。仅本地≤4000字符，硬链接不支持明确失败；不拥有工作流状态、不自动修复，G06余项保留。 | `report_file_descriptor`；`publish_report_file`；`read_report_file`；`report_file_view` |
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
| [input_mapping.py](../total_control/orchestration/input_mapping.py) · 302 | R05/R09；引用/上下文/模型输出 → 解析映射与 JSON 输出校验 → 输入值/输出证据 | N00C导入唯一取值内核；N04-G增加显式preserve_mapped_inputs，仅N04 follow开启，映射序列化上限65536字节、超限拒绝且默认预览不变；日志作为证据而非指令。前缀/缺失/历史规则仍关联[G10](#g10)，未整体统一。 | `_is_mapping_ref:11`；`resolve_input_mapping_ref:16` |
| [node_runner.py](../total_control/orchestration/node_runner.py) · 212 | R06/R09；节点/执行上下文 → 选择 Agent/Job、Agent 失败校验 → StepResult | 共用原 Agent 执行入口/映射和失败规则；N03B2c1 传递 output_value 到持久 step，不自建模型或推进循环。G02/G04 仍开放。 | `_node_handler_mode:51`；`_node_agent_id:56` |
| [run_store.py](../total_control/orchestration/run_store.py) · 452 | R06/R11/R13；完整计划/attempt/提交意图 → SQLite 事务、hash 与单机互斥 → 可核对证据 | N04 增加 `operation` 与 `child-job` 稳定提交键，schema 由1迁移到2；父 attempt/child 收据仍复用同一 submissions 表。RunStore 隔离检查通过，LangGraph 链尚未验收。N07A 文件回执与 Agent claim 保留；N04-F在原attempt JSON中原子保存首个child提交错误，record_result禁止丢弃或成功覆盖，不加表/迁移/推进逻辑。N04-H同事务核waiting/唯一submitted child/无follow，原子父stopped+停止receipt；begin/claim/prepare防新执行，既有terminal读取保留，schema仍2。 | `canonical_json:19`；`content_hash:23`；`RunConflictError:27` |
| [types.py](../total_control/orchestration/types.py) · 90 | R06/R09/R11；计划/结果/上下文 → RunPlan/StepResult/ExecutionRunContext → 类型化边界 | N07A RunPlan追加可选report_output_root，副作用前冻结；旧计划缺字段不自动补文件。StepResult原inline执行证据与交付事实分开。 | `RunPlan:8`；`StepResult:22`；`ExecutionRunContext:73` |
| [job_coordinator.py](../total_control/orchestration/job_coordinator.py) · 175 | R06/R11/R13；run/冻结计划、Job 回调 → 持久图/暂停、去重唤醒与身份检查 → attempt 事实及检查点 | N04等待/恢复的后续真实HTTP证据见G02；总验收未完，不沿用早期callback完成声明。N04-H在run_lock内读停止receipt后no-op，旧检查点不越过停止；其他engine不变。 | `JobCoordinator`；`advance`；`_validate_checkpoint` |
| [workspace_mutations.py](../total_control/orchestration/workspace_mutations.py) · 143 | R02/R10；节点/配置或 artifact 内容 → 修改工作区内存快照 → 配置/产物元数据 | 问题/修补关联 [G06](#g06)；按登记方案处理，不另建平行服务。 | `find_workspace_node:29`；`apply_workflow_edit:45` |

### total_control/state

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/__init__.py) · 20 | R14；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | `TotalControlState:16` |
| [_deps.py](../total_control/state/_deps.py) · 40 | R14；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [base.py](../total_control/state/base.py) · 226 | R03/R06/R13/R14；配置/持久数据 → 唯一规范化、账本核对及后台启动 → 单机状态 | N03B2c2a退出后置补权及其启动写回；空/子集重启保持，旧缺字段由normalizer解释，不强制迁移原盘。首次初始化/清理写回保留；G09/G21余项开放。 | `_dedupe_provider_profiles:8`；`_agent_definitions_need_writeback:44`；`BaseMixin:60` |
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
| [workflow_templates.py](../total_control/state/registry_pkg/workflow_templates.py) · 500 | R03/R05/R11；模板节点/能力目录 → I/O、绑定、拓扑校验 → validation/preview | N03B2c2b 模板校验按 node executor mode 判断静态必需工具：Agent 报告无 report.write 要求，Job 报告仍有；G10/G17 其他问题按登记方案处理。 | `rewrite_workflow_template_agent_reference:20`；`build_workflow_template_validation_payload:60` |

### total_control/state/workspaces

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/state/workspaces/__init__.py) · 20 | R05/R06/R09；领域 mixin → 装配 WorkflowRecordsMixin → 工作区服务入口 | N02 接入记录/适配边界；仍只有原 workflow runner，不按短文件删除。 | `WorkspacesMixin:17` |
| [_deps.py](../total_control/state/workspaces/_deps.py) · 52 | R05/R06/R09；上层模块/公共符号 → 星号聚合依赖 → 子包可见依赖 | 结构风险；改显式依赖前先锁定 monkeypatch 与兼容调用。 | 文件整体/公开入口 |
| [agent_runtime_control.py](../total_control/state/workspaces/agent_runtime_control.py) · 138 | R05/R06/R09；工具 GPU/Job 控制请求 → 候选建议或当前工作区任务控制 → planned/stopped/reordered | 问题/修补关联 [G11](#g11)、[G13](#g13)；按登记方案处理，不另建平行服务。 | `bind_workspace_tool_gpu_allocation:8`；`control_workspace_tool_job:51` |
| [agent_runtime_inputs.py](../total_control/state/workspaces/agent_runtime_inputs.py) · 100 | R05/R06/R09；映射/节点位置/历史输出 → 检查运行时引用 → refs/blockers | 问题/修补关联 [G10](#g10)、[G01](#g01)；按登记方案处理，不另建平行服务。 | `_agent_node_runtime_input_refs:10` |
| [agent_runtime_observation.py](../total_control/state/workspaces/agent_runtime_observation.py) · 156 | R05/R06/R09；子 Job/run id/观察限额 → 等待与读取受限快照 → runtime observation | 问题/修补关联 [G02](#g02)、[G04](#g04)；按登记方案处理，不另建平行服务。 | `workspace_tool_observe_options:9`；`workspace_tool_job_snapshot:35` |
| [agent_runtime_safety.py](../total_control/state/workspaces/agent_runtime_safety.py) · 327 | R05/R06/R09；命令/观测文本 → 允许诊断边界与密钥脱敏 → 拒绝原因/安全文本 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `redact_runtime_observation_text:18`；`workspace_tool_command_block_reason:29` |
| [agents.py](../total_control/state/workspaces/agents.py) · 1010 | R05/R06/R09；Agent 节点/工具参数 → 有效配置、runtime Job、输出持久化 → execution/节点结果 | N04 在父 attempt 上下文中为受控 `job.run/host.exec` 工具建立 child submission metadata，N04-D 只把 command 工具显式目标传给唯一 binding，HTTP CPU/cwd/环境验证通过；非command host.exec 与独立 agent-tool run 兼容入口保留。N04-E 冻结 v2 完整执行身份与资源缺省，同键目标变化拒绝；旧回执不改写、重入需核对，原恢复保留。N04-F增加限定N04父上下文的首错持久/本进程保护，失败不再发成功事件或应用最终文本输出；G32后端与F-UI已限定验收；N04-G接follow证据保留及显式超限blocked。G02/G30与取消等边界仍开放，日志证据UI待G-UI。 | `AgentsMixin:33`；`cancel_agent_execution:34` |
| [automation.py](../total_control/state/workspaces/automation.py) · 138 | R06/R12；用户推进请求/权威 run 与 Job 投影 → 活跃运行保护、发现/受理命令 → watch/blocked/run 反馈 | 受理窗口 watch 保护同时涵盖 B2b/B2c1；当前运行未完成或未知时不另开发现任务。不是图推进入口，G17 建议投影仍开放。 | `AutomationMixin:8`；`advance_workspace_automation:9` |
| [chat.py](../total_control/state/workspaces/chat.py) · 902 | R09/R12；聊天/反思/流请求 → 路由、Agent、消息更新 → 聊天与事件 | 问题/修补关联 [G05](#g05)、[G04](#g04)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `ChatMixin:7`；`_chat_agent_execution_trace:33` |
| [crud.py](../total_control/state/workspaces/crud.py) · 365 | R02；工作区与迁移请求 → 创建/更新/模板差异与草稿 → 工作区快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `CrudMixin:7`；`workspace_by_id:8` |
| [debug.py](../total_control/state/workspaces/debug.py) · 181 | R05/R06/R09；Agent 定义/样例 → 组装调试上下文与有效配置 → debug/execution | 问题/修补关联 [G11](#g11)、[G21](#g21)；按登记方案处理，不另建平行服务。 | `DebugMixin:7`；`debug_agent_definition:8` |
| [defaults.py](../total_control/state/workspaces/defaults.py) · 62 | R05/R06/R09；工作区/应用建议请求 → 有来源的默认与发现回填 → 配置快照 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `DefaultsMixin:7`；`apply_workspace_automation_defaults:8` |
| [discovery.py](../total_control/state/workspaces/discovery.py) · 162 | R05/R06/R09；工作区/发现节点 → 创建受控发现 Job 链 → 发现任务/run | 问题/修补关联 [G12](#g12)；按登记方案处理，不另建平行服务。 | `DiscoveryMixin:7`；`run_workspace_discovery:8` |
| [nodes.py](../total_control/state/workspaces/nodes.py) · 471 | R05/R06/R09；节点/前置 Job/自动化状态 → 编译命令与依赖 → 节点 Job payload | 问题/修补关联 [G01](#g01)、[G14](#g14)、[G31](#g31)；N04-D 接显式目标并同步 payload/runtime_binding/resource_plan；普通默认解析对照不变。 | `NodesMixin:7`；`workspace_node_job_payload:8` |
| [runs.py](../total_control/state/workspaces/runs.py) · 665 | R05/R06/R11；steps/事件/查询 → 新账本投影与历史 JSON 兼容 → run/SSE | N07A 新增get_workspace_execution_report，复用原run投影取当前已验证artifact正文，失败/历史返回null与原因，不回退inline。旧JSON兼容及G02/G03/G09边界保留。 | `_workspace_public_payload_with_full_runs:8`；`RunsMixin:18` |
| [workflow.py](../total_control/state/workspaces/workflow.py) · 432 | R05/R06/R09；启动/重发/实际前缀 → 类型边界、原门禁及冻结计划受理 → run/暂可为空的 jobs | N04 两 Agent handoff 计划可经真实 HTTP 受理；旧单 Job/Job→报告入口不变。N04-D 已限定验证 CPU 目标保真和等待中恢复；正文/UI/其他恢复窗口仍待 G02 后续片。 | `_workspace_agent_execution_checks`；`WorkflowMixin.run_workspace_workflow` |
| [workflow_records.py](../total_control/state/workspaces/workflow_records.py) · 779 | R06/R11/R13；计划/Job 回执/图回调 → 冻结 payload、幂等提交核对/attempt 观察 → 领域证据和公开投影 | N04-A 已接父 Agent claim、child receipt 核对、waiting_child 投影及 follow resume；隔离 callback 验证重复 wake。N04-F唯一错误结算函数接入start/final/observe/resume，保留已提交child回执但不让其完成覆盖父失败；HTTP四链及模型返回前重启通过。N04-G抽N03/N04共用有界脱敏日志helper，done首次证据按完整身份冻结；实际follow请求及超限HTTP通过。N04-H新增stop service，run_lock先于短self.lock核精确child、显式keep_running，store原子受理后复用原投影/事件；三HTTP链及H-UI已限定通过；J1复用进程活动标志及精确身份的共用predicate，活动原提交投running/submitting且不被核对入口提前改未知；真实Job优先核对，重启/未知保护保留。自然网页及提交前后SIGKILL对照通过，UI独立待验收。N04全验收仍未完成，见G02/G04/G30/G31/G32/G34。 | `WorkflowRecordsMixin:21` |

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
| [context.py](../total_control/tools/workspace_executor_pkg/context.py) · 181 | R03/R04/R09；工作区/资源/回调 → 提供发现与 runtime 访问 → workspace tool context | 问题/修补关联 [G12](#g12)、[G11](#g11)；按登记方案处理；N13B3b1静态确认工具定义全局优先，实例Search Provider覆盖未动态验证（G11）。 | `WorkspaceToolContext:12`；`node_config:20` |
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
| [bundle.py](../total_control/workspace/automation/bundle.py) · 682 | R05/R06；命令/目标/证据 → 生成脚本、标识、包门禁 → ExecutionPackage | 问题/修补关联 [G10](#g10)、[G17](#g17)、[G31](#g31)；N04-D 在既有 runtime binding 统一 command 显式目标/GPU成对选择，保留包默认快照及覆盖来源。 | `make_execution_package_id:11`；`make_stable_execution_package_id:16` |
| [contracts.py](../total_control/workspace/automation/contracts.py) · 2 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [core.py](../total_control/workspace/automation/core.py) · 61 | R05/R06；检查字段/状态 → 统一基础检查项 → 带优先级 readiness item | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_execution_node_by_kind:6`；`workspace_automation_check:15` |
| [deployment.py](../total_control/workspace/automation/deployment.py) · 226 | R05/R06；实例命令/服务参数 → 推断端口、健康检查与停止命令 → 部署交付建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_delivery_contract:7`；`workspace_deployment_health_path:76` |
| [evidence.py](../total_control/workspace/automation/evidence.py) · 206 | R05/R06；执行/发现状态 → 收集来源与分组 → evidence 清单 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_evidence_item:6`；`workspace_add_evidence_item:22` |
| [helpers.py](../total_control/workspace/automation/helpers.py) · 21 | R05/R06；列表/限额 → 压缩显示条目 → 紧凑列表 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `compact_contract_items:10` |
| [preflight.py](../total_control/workspace/automation/preflight.py) · 593 | R05/R06；工作区/资源/执行 → 汇总预检与资源编排 → 缺口和建议 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_execution_readiness_step:7`；`workspace_resource_item:36` |
| [report.py](../total_control/workspace/automation/report.py) · 458 | R05/R06；自动化各投影 → 汇总高亮/门禁/行动 → 操作报告 | 问题/修补关联 [G17](#g17)；按登记方案处理，不另建平行服务。 | `workspace_report_highlight:9`；`workspace_report_next_action:17` |
| [reproduction.py](../total_control/workspace/automation/reproduction.py) · 791 | R05/R06；计划/声明数据/静态输入 → 范围内脚本与包缺项 → execution bundle | N03B1 仅有消费者的命令预览进入包；warning 可提交，声明数据与输入硬错误保留；未统一多同-kind/远程读取，关联 [G10](#g10)、[G12](#g12)、[G17](#g17)。 | `derive_workspace_reproduction_manifest` |
| [run_plan.py](../total_control/workspace/automation/run_plan.py) · 198 | R05/R06；节点执行方式/配置 → 阶段和命令摘要 → run plan | N03B2c2b 使 `workspace_node_required_tool_id` 接收 executor mode：eval.report Agent 无静态 report.write 要求，Job 保留；N03B1 的 Agent 报告不强求 shell report_command 仍保留。 | `workspace_node_required_tool_id`；`workspace_node_command_summary_for_plan` |
| [topology.py](../total_control/workspace/automation/topology.py) · 393 | R03/R05/R06；节点执行方式/Agent/工具 → 有效绑定和路由缺口 → topology | N03B2c2b 的 eval.report Agent 可显式 tools=[] 且不报 required_tool_unbound/agent_without_tools；Job 的 report.write 门禁保留；system/human 原边界保留，其他投影收敛待 [G17](#g17)。 | `derive_workspace_agent_topology` |

### total_control/workspace/automation/contracts_pkg

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/automation/contracts_pkg/__init__.py) · 60 | R05/R06；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [context.py](../total_control/workspace/automation/contracts_pkg/context.py) · 353 | R05/R06；节点/输出/映射 → 解析并汇总上下文契约 → 输入/输出状态 | N00C 通过别名复用 context_refs；N03B2c2b metadata 按 executor mode 投影必需工具，report Agent 不注入 report.write；其余展示就绪语义与 G10 引用规则仍开放。 | `workspace_node_workflow_contract_metadata:16`；`workspace_context_value_present:84` |
| [io.py](../total_control/workspace/automation/contracts_pkg/io.py) · 226 | R05/R06；节点类型/映射 → I/O 默认和引用静态校验 → refs/gaps | 问题/修补关联 [G10](#g10)；按登记方案处理，不另建平行服务。 | `workspace_io_contract_for_kind:12`；`workspace_node_config_signal:24` |
| [orchestration.py](../total_control/workspace/automation/contracts_pkg/orchestration.py) · 225 | R05/R06；节点契约/拓扑缺口 → 按阶段分车道 → 编排展示契约 | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_orchestration_gap_matches_node:12`；`workspace_orchestration_status:29` |
| [workflow.py](../total_control/workspace/automation/contracts_pkg/workflow.py) · 229 | R05/R06；实际节点/映射/执行方式 → 复用静态引用校验 → workflow contract | N03B2c2b 按 `resolve_node_executor_mode` 生成工具投影，Agent 报告不注入 report.write、Job 要求保留；N03B1 显式非法引用与输入契约规则不变。静态/运行时引用规则统一仍待 [G10](#g10)。 | `derive_workspace_workflow_contract` |

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
| [payload.py](../total_control/workspace/cockpit/payload.py) · 320 | R02/R03/R05/R07；实例字段/显式授权 → 默认目录/运行投影 → workspace | N03B2c2a退出整段Agent再规范化/补权，原Agent字段保真；工具定义补全与N03J1b显式环境规则保留。正常/force/auto_apply不扩大授权，G17余项开放。 | `apply_workspace_automation_defaults_to_payload:19` |
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
| [run_artifacts.py](../total_control/workspace/execution/run_artifacts.py) · 48 | R06/R10/R11；artifact 列表 → 字段规范与限制 → step artifacts | N07A 归一化保留报告run/step/attempt/host/hash/size/verified等元数据和精确空白正文；无新存储。旧artifact兼容保留，G06余项开放。 | `normalize_workspace_run_step_artifacts:9` |
| [run_compare.py](../total_control/workspace/execution/run_compare.py) · 130 | R06/R10/R11；两次 run/指标 → 语义与节点差异比较 → compare payload | 问题/修补关联 [G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_execution_run_compare_payload:9`；`metric:19` |
| [run_delivery.py](../total_control/workspace/execution/run_delivery.py) · 187 | R06/R10/R11；包预期/step artifact → 路径匹配与完成度派生 → delivery closure | N07A 当前受管报告交付来自实物投影；缺失/损坏/写失败保持incomplete及具体原因，不改变Agent执行终态。旧声明型判断仍属G06。 | `_workspace_delivery_path_candidates:9`；`workspace_execution_run_delivery_closure:43` |
| [run_events.py](../total_control/workspace/execution/run_events.py) · 326 | R06/R10/R11；事件/流摘要 → 裁剪、脱敏、计数 → run event/delta_evidence | N16A同步step事件摘要detail/recorded_error，沿用原裁剪规则；旧事件保留原error。G20其它事件/保留边界不变。 | `_compact_run_event_text:8`；`_compact_run_event_payload:15` |
| [run_export.py](../total_control/workspace/execution/run_export.py) · 341 | R06/R10/R11；run/关联任务 → 有界日志、artifact、manifest 组合 → JSON 导出 | 问题/修补关联 [G06](#g06)、[G20](#g20)；按登记方案处理，不另建平行服务。 | `workspace_run_export_manifest:18`；`workspace_run_export_readme:147` |
| [run_records.py](../total_control/workspace/execution/run_records.py) · 255 | R06/R10/R11；完整 steps/历史 run → 状态/进度/规范化 → 兼容 run 记录 | N04 保留 waiting child 的运行/进度投影字段，完整计划分母不缩小；真实 UI/服务投影待验收。N16A detail/recorded_error 与 N02 边界保持。N04-H公开normalizer增continuation_stop，旧记录空值、停止回执在刷新/HTTP重启中保留。 | `make_workspace_execution_run_id:12`；`make_agent_execution_id:16`；`derive_workspace_execution_run_status:20` |
| [run_refresh.py](../total_control/workspace/execution/run_refresh.py) · 284 | R06/R10/R11；计划/attempt 与旧 Job/子 run → 按 engine 区分只读投影 → 当前 run | N04 仅把 authoritative child Job 事实投影为 waiting_child/done/failed；查询/SSE 不独立推进。旧 child run 兼容分支保留待后续切片。 | `_workspace_child_run_status:22`；`_workspace_child_run_error:29`；`_workspace_agent_child_runtime_status:44` |
| [run_refs.py](../total_control/workspace/execution/run_refs.py) · 194 | R06/R10/R11；run/step 引用 → 去重、闭包与归属过滤 → 关联 Job/子 run | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `_unique_run_ref_list:11`；`workspace_run_step_job_ids:20` |
| [run_replay.py](../total_control/workspace/execution/run_replay.py) · 171 | R06/R10/R11；run/关联 Job → 组装历史时间线 → 摘要回放 | N16A显式timeline保留detail/recorded_error，回放与export复用同一投影；历史来源可追查。没有新回放状态机，G20余项保持。 | `workspace_execution_run_timeline:19`；`workspace_execution_run_replay_run_summary:63` |
| [run_state.py](../total_control/workspace/execution/run_state.py) · 103 | R06/R10/R11；节点/Job → 按最近 Job 派生节点执行状态 → 执行面板状态 | 问题/修补关联 [G01](#g01)、[G02](#g02)、[G17](#g17)；按登记方案处理，不另建平行服务。 | `derive_workspace_execution_state:10` |
| [run_steps.py](../total_control/workspace/execution/run_steps.py) · 394 | R06/R10/R11；Job/Agent/计划结果 → 状态、资源、引用规范化 → 持久/公开 step | N16A/G25唯一构造与归一化保留detail/真实error；legacy精确提升保留recorded_error、原attempt不改。负向信号不清洗，重复原快照/新attempt隔离通过。 | `workspace_run_step_status_from_job:18`；`_normalize_agent_meta:33`；`normalize_workspace_run_step_resources:45` |
| [runs.py](../total_control/workspace/execution/runs.py) · 77 | R06/R10/R11；包内实现 → 组合或转导出 → 公开兼容入口 | 兼容/包边界；保留已知调用，不按短文件数量删除。 | 文件整体/公开入口 |
| [trace.py](../total_control/workspace/execution/trace.py) · 246 | R06/R10/R11；节点/绑定 Job → 汇总产物、资源与轨迹 → 节点 trace | 保留；接口/副作用静态检查未发现独立缺陷，修改调用契约时补对应回归。 | `workspace_node_artifacts:20`；`workspace_node_resources:97` |

### total_control/workspace/schema

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [__init__.py](../total_control/workspace/schema/__init__.py) · 137 | R02/R03/R05；包内实现 → 显式转导出 → 公开兼容入口 | N03B2c2a移除无其他消费者的backfill_default_agent_tools导出，已有规范化/工具定义入口保留；不按短文件数量删除。 | 文件整体/公开入口 |
| [agents_tools.py](../total_control/workspace/schema/agents_tools.py) · 418 | R02/R03/R05；当前/同ID字段与目录 → 规范化与缺字段推荐 → 有效Agent/工具 | N03B2c2a 唯一授权入口尊重显式空/子集，删除后置 allowlist 补权；N03B2c2b 默认工具需求按 executor mode 区分。N13B3b2b-Agent 保留同ID existing 的只读 description/timestamps，拒绝客户端伪造和跨ID继承；不触碰业务字段/allowlist。G10/G11/G27 的其他边界开放。 | `normalize_workspace_agent:119`；`normalize_workspace_agents:186` |
| [chat.py](../total_control/workspace/schema/chat.py) · 461 | R02/R03/R05；消息/反思/工作区 → 规范、规则回复与 debug → chat/debug payload | 问题/修补关联 [G05](#g05)、[G11](#g11)；按登记方案处理，不另建平行服务。 | `normalize_workspace_context_reflection:15`；`normalize_workspace_chat_message:54` |
| [nodes.py](../total_control/workspace/schema/nodes.py) · 698 | R02/R03/R05；源类型/节点草稿/recipe → 默认、绑定、连线规范 → 顺序工作区节点 | N03A0 保留明确 system/human 与已绑定 Agent 的执行者；缺指定/缺 Agent 继续由唯一 finalizer 补默认，输出键/输入映射沿原逻辑。关联 [G10](#g10)、[G11](#g11)、[G14](#g14)。 | `workspace_node_definition:22`；`workspace_node_kinds_for_source:31` |
| [recipe.py](../total_control/workspace/schema/recipe.py) · 201 | R02/R03/R05；启动/模型/环境输入 → 字段规范与源类型推断 → recipe/model/inputs | N13B3b2c-Model 后端片：`normalize_workspace_model` 对 `chat_agent_id` 区分缺字段（保留 existing）和显式空值（清空）；非空值保持既有 `safe_id` 规则，未知引用不在 schema 层自动重选。未增加抽象或第二保存路径；UI已在N13B3b2c-UI独立处理，不在此层显示或自动修复引用。 | `normalize_workspace_model:84`；`clean_workspace_config_default:32` |
| [templates.py](../total_control/workspace/schema/templates.py) · 1372 | R02/R03/R05；模板/实例快照 → 版本、拓扑、差异与迁移计划 → template/snapshot/diff | N03A0 模板补齐保留明确 system/human，即使没有 agent_id；新默认链仍提供推荐 Agent。其余迁移/快照关联 [G10](#g10)、[G16](#g16)。 | `workflow_template_sort_key:39`；`normalize_workflow_template_version_history:46` |

### web

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [index.html](../web/index.html) · 1762 | R02/R03/R12/R14；安全预算meta/唯一装配 → 按职责页面与读取反馈 | N13C2-UI原按钮文字化、主滚动区单反馈/独立polite区域；N13B3b2c-UI为两个实例模型 Agent 选择器增加明确标签/状态文本；N04-D-UI、F-UI、G-UI及H-UI更新现有summary/actions/app/CSS缓存标识，helper在app前；J1只更新status_labels缓存标识；121脚本引用与顺序已核对。无新网络/状态页。 J1-UI同步summary/replay/app/styles缓存版本，无新入口。 K1/K2及M1-UI各只更新app缓存版本。 | refreshBtn/statusLoadFeedback/statusAnnouncement/workspaceModelChatAgentSelect |

### web/config-center

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [config_center_agent_actions.js](../web/config-center/config_center_agent_actions.js) · 126 | R03/R12；用户事件/注入依赖 → Agent 定义动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_agent_health.js](../web/config-center/config_center_agent_health.js) · 112 | R03/R12；页面数据/注入依赖 → Agent 能力健康 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`textList:21` |
| [config_center_agent_renderer.js](../web/config-center/config_center_agent_renderer.js) · 196 | R03/R12；状态/注入 renderer → Agent 定义组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_ai_renderer.js](../web/config-center/config_center_ai_renderer.js) · 201 | R03/R12；状态/注入 renderer → AI 配置组合 → DOM 更新 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`listFor:12` |
| [config_center_diagnostics.js](../web/config-center/config_center_diagnostics.js) · 128 | R03/R12；页面数据/注入依赖 → 链诊断 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`defaultToolTestArguments:21` |
| [config_center_provider_actions.js](../web/config-center/config_center_provider_actions.js) · 119 | R03/R12；用户事件/注入依赖 → Provider 配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_provider_profiles.js](../web/config-center/config_center_provider_profiles.js) · 239 | R03/R12；页面数据/注入依赖 → Provider 目录和选项 → 派生状态/界面结果 | 契约/维护关联 [G21](#g21)；消费后端结果，随所属切片收敛。 | `escapeFor:13`；`vendorDefaultBaseUrl:47` |
| [config_center_tool_actions.js](../web/config-center/config_center_tool_actions.js) · 109 | R03/R12；用户事件/注入依赖 → 工具配置动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [config_center_tool_renderer.js](../web/config-center/config_center_tool_renderer.js) · 164 | R03/R12；状态/注入 renderer → 工具配置组合 → DOM 更新 | 契约/维护关联 [G11](#g11)；消费后端结果，随所属切片收敛。 | `element:8`；`listFor:12` |

### web/core

| 文件（行数） | 对应需求与职责：输入 → 处理 → 输出 | 检查结论与解决路径 | 源码依据 |
| --- | --- | --- | --- |
| [app.js](../web/core/app.js) · 26529 | R02/R03/R06/R12/R14；真实加载结果/执行包/run身份 → 启动闭环与运行阅读导航 → 驾驶舱/运行记录 DOM | N03B2c2a-UI 新增 `renderWorkspaceLaunchClosure` 的 ready/missing/在途投影，`workspaceHomeActionButtonMarkup` 传递 run_id，`workspaceAutomationActionDeps` 复用 `openWorkspaceFromExecutionOverview`；N13B3b2c-UI 让实例模型 Agent 选择保留空/未知值，新增/删除不隐式接管，状态投影共用原 draft；N04-D-UI 接实际目标纯markup、持久N04状态/等待说明、精确日志去重与重建时按钮焦点恢复；N04-F-UI首步错误前置、child状态独立、follow未执行解释、N04独立重试隐藏；G-UI仅父步骤接冻结日志helper，按run/step/attempt/Job保留展开、正文滚动与焦点；H-UI只接父后续控制与已停止回执后的独立child停止，按完整身份恢复控制区/目标区焦点；只隐藏匹配停止回执的同义英文说明，其他Notes保留；配置/运行仍分区。G11旧诊断不隐藏。 J1-UI接共享提交说明与同run回放注入，替换重复等待/runtime；活动自动呈现G35和回放焦点G26未通过。 K1只补周期快照到当前instance reader重绘，复用原报告sync并保留响应前阅读位置；G35限定修复；K2回放busy改ARIA保持可聚焦，沿用原同步恢复/同key门禁，无异步焦点缓存。 M1-UI取消仅请求原monitor快照，迟到成功/失败检查原实例，持久同run/node/execution终态才将消失的cancel焦点交给同run回放；无新状态/轮询。 | renderWorkspaceLaunchClosure/workspaceHomeActionMarkup/workspaceModelChatAgentSelection |
| [app_navigation_actions.js](../web/core/app_navigation_actions.js) · 63 | R12；用户事件/注入依赖 → 顶层导航动作 → 唯一回调 | N13B3a删除已退出moduleCards的委托绑定；其他导航保持，实际独立编辑入口由shell actions绑定。 | bind |
| [app_runtime.js](../web/core/app_runtime.js) · 250 | R12；页面数据/注入依赖 → fetch/浏览器存储 → 页面结果 | 原通用fetchJson不自带deadline；N13C2外层标准signal透传/正文取消合同通过，本文件不改，不冒称其他调用都获预算。存储仍[G19](#g19)。 | fetchJson/loadStoredValue/saveStoredValue |
| [app_status_actions.js](../web/core/app_status_actions.js) · 31 | R12；用户事件/注入依赖 → 全局刷新/状态动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`call:12` |
| [status_load_feedback.js](../web/core/status_load_feedback.js) · 59 | R12/规格§3；显式读取投影/busy/DOM → 安全文字与按钮反馈 → 加载/失败/超时/完成/替代展示 | N13C2-UI新无状态renderer，textContent保留完整错误；无网络/计时器/缓存/领域判断。app唯一实际消费者，原混合写入退出；合同/四视口/键盘验证通过。 | AppStatusFeedback.describe/render |
| [display_formatters.js](../web/core/display_formatters.js) · 57 | R12；页面数据/注入依赖 → 单位/时间/摘要格式 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `fmtMiB:4`；`formatBytes:10` |
| [input_parsers.js](../web/core/input_parsers.js) · 38 | R12；页面数据/注入依赖 → 基础输入解析 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `positiveNumberOrBlank:4`；`parseLineList:9` |
| [status_labels.js](../web/core/status_labels.js) · 92 | R12；页面数据/注入依赖 → 公开状态文案 → 派生状态/界面结果 | J1仅增加submitting“提交中”文案；原merge转换与脚本装配契约通过，完整J1-UI待独立验收。保留公共标签，不新建状态合并器。 | `zhStatus:30`；`zhKind:34` |

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
| [styles.css](../web/styles/styles.css) · 23057 | R12/规格§3；执行包状态/授权说明 → 入口状态色、自然换行、窄屏动作换行 → 启动闭环可读布局 | N03B2c2a-UI 只补完整运行入口、缺项列表和授权说明响应式样式；N13B3b2c-UI补充空/有效/无效模型聊天 Agent 状态文字样式；letter-spacing保持0，无固定局部滚动、动画或外部字体。N04-D-UI 目标dl自然换行、窄窗无固定高；F-UI仅补标题与状态flex换行；G-UI新增交接摘要自然换行与唯一正文局部滚动/键盘焦点样式；H-UI补后续控制自然流、错误反馈和控制/子任务区焦点轮廓，不加嵌套折叠/固定高；旧共享样式仍有消费者，G15旧样式债保留。 J1-UI补说明边线/自然换行，覆盖旧回放p裁剪红字，无新滚动容器。 | workspace-launch-runtime-entry/workspace-model-chat-agent-status |

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
| [workspace_action_surfaces.js](../web/workspace/workspace_action_surfaces.js) · 64 | R12；用户动作/依赖 → 单一事件委托 → 业务回调 | N03B2c2a-UI 将实际渲染的 `workspaceLaunchClosure` 纳入既有委托；不新增第二事件系统。旧 workflow/agents/tools/model/inspect 消费者保留。 | WORKSPACE_ACTION_SURFACE_IDS/bind |
| [workspace_agent_catalog.js](../web/workspace/workspace_agent_catalog.js) · 48 | R02/R06/R09/R12；页面数据/注入依赖 → 实例 Agent 查询/显示 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceAgentById:4`；`workspaceAgentDisplayName:8` |
| [workspace_agent_stream_state.js](../web/workspace/workspace_agent_stream_state.js) · 286 | R02/R06/R09/R12；页面数据/注入依赖 → Agent 实时输出缓冲 → 派生状态/界面结果 | 契约/维护关联 [G04](#g04)、[G05](#g05)；消费后端结果，随所属切片收敛。 | `appState:8`；`selectedWorkspaceId:13` |
| [workspace_agent_tool_actions.js](../web/workspace/workspace_agent_tool_actions.js) · 165 | R03/R12；原生select change/原编辑事件 → 注入原回调 → 选择与字段编辑 | N13B3b1-UI从卡click改稳定select change；toolbar增补/编辑器/Agent回调沿原绑定。键盘/正常保存与本地回调契约通过，不新建状态。 | bindToolList/bindToolEditor/bindToolbars |
| [workspace_agent_trace.js](../web/workspace/workspace_agent_trace.js) · 218 | R02/R06/R09/R12；页面数据/注入依赖 → Agent 工具与事件轨迹 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:17`；`compactFor:21` |
| [workspace_automation_actions.js](../web/workspace/workspace_automation_actions.js) · 904 | R06/R11/R12；用户点击/稳定 request_id → 唯一工作流提交与运行阅读导航 → HTTP/run/运行记录 | N03B2c2a-UI `runWorkspaceWorkflow` 成功后刷新状态并调用既有运行阅读导航；新增 `open-workspace-run-reader` 只切换既有 run reader；移除无 DOM 的 `workspaceRunFlowBtn` busy 引用。单节点/发现仍原入口，G17 不关闭。 | `runWorkspaceWorkflow:377`；`handleAutomationAction:500`；`openWorkspaceRunReader` |
| [workspace_catalog_data.js](../web/workspace/workspace_catalog_data.js) · 564 | R02/R06/R12；静态能力目录 → 配置tab枚举 → 装配数据 | N13B2从WORKSPACE_MANAGE_TABS退出runs；旧存储值在app一次迁移到运行记录/all。其他节点/工具目录保留。 | WORKSPACE_MANAGE_TABS |
| [workspace_chat_actions.js](../web/workspace/workspace_chat_actions.js) · 61 | R02/R06/R09/R12；用户事件/注入依赖 → 聊天/反思动作动作路由 → 回调/API 请求 | 契约/维护关联 [G05](#g05)；消费后端结果，随所属切片收敛。 | `element:8`；`eventTarget:12` |
| [workspace_chat_normalizers.js](../web/workspace/workspace_chat_normalizers.js) · 84 | R02/R06/R09/R12；页面数据/注入依赖 → 聊天与反思字段规范 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeWorkspaceContextReflection:16`；`normalizeWorkspaceChatMessage:45` |
| [workspace_defaults.js](../web/workspace/workspace_defaults.js) · 217 | R02/R06/R09/R12；页面数据/注入依赖 → 实例默认值 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)；消费后端结果，随所属切片收敛。 | `deepCloneFor:56`；`agentCatalogFor:60` |
| [workspace_draft_normalizers.js](../web/workspace/workspace_draft_normalizers.js) · 100 | R02/R06/R09/R12；页面数据/注入依赖 → 能力草稿字段规范 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `normalizeWorkspaceToolDraft:27`；`normalizeWorkspaceAgentDraft:42` |
| [workspace_event_stream.js](../web/workspace/workspace_event_stream.js) · 390 | R06/R12；SSE通知 → 原状态合并 → 权威展示刷新 | N13B3a仅退出home运行副本的刷新回调；runs/executionDetail/useChat/monitor等原链保持，无第二订阅/推进器。 | renderRealtimeSurfaces |
| [workspace_execution_lane_rail.js](../web/workspace/workspace_execution_lane_rail.js) · 97 | R02/R06/R09/R12；页面数据/注入依赖 → 只读执行车道 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`contractFromWorkspace:17` |
| [workspace_execution_overview.js](../web/workspace/workspace_execution_overview.js) · 89 | R06/R12；全局API记录/筛选 → 规范化与安全markup → 摘要/run/Job行 | N13B2共用一个无状态转换模块，按钮携精确run/Job/实例IDs，移除无消费者客户端筛选和旧统计卡markup；筛选仍由现有API完成。 | normalizeFilters/filtersMatch/recordMarkup |
| [workspace_execution_overview_actions.js](../web/workspace/workspace_execution_overview_actions.js) · 71 | R12；可见按钮/筛选输入 → 唯一事件路由 → 范围/精确记录/重试回调 | 由config-center迁移并删除旧文件；范围、精确身份、focus重试接入原app，无状态副本或业务推进。 | bind/handlePanelClick |
| [workspace_execution_overview_renderer.js](../web/workspace/workspace_execution_overview_renderer.js) · 65 | R12；显式状态/筛选依赖 → 加载/空/失败/列表投影 → 全局阅读DOM | 由config-center迁移并删除旧文件及同责fallback；仅匹配筛选的响应展示，归一markup不变保留节点/焦点，不另缓存payload；自然主滚动。 | render/updateList |
| [workspace_flow_canvas_controls.js](../web/workspace/workspace_flow_canvas_controls.js) · 178 | R02/R06/R09/R12；页面数据/注入依赖 → 执行板缩放/平移 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `configFor:16`；`boardFor:23` |
| [workspace_flow_tool_state.js](../web/workspace/workspace_flow_tool_state.js) · 76 | R02/R06/R09/R12；页面数据/注入依赖 → 节点工具健康/选择状态 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `workspaceFlowNodeToolStatuses:4`；`workspaceFlowToolStatusLabel:21` |
| [workspace_focus_navigation.js](../web/workspace/workspace_focus_navigation.js) · 441 | R12；工具toolbar滚轮/既有焦点目标 → 原定位内核 → 主内容滚动 | N13B3b1-UI工具toolbar改主scroll shell，app fallback同步；新增/删除复用revealWorkspaceElement，四视口焦点可见。其他定位规则保留。 | revealWorkspaceElement/workspaceHeaderWheelTarget |
| [workspace_form_actions.js](../web/workspace/workspace_form_actions.js) · 51 | R02/R06/R09/R12；用户事件/注入依赖 → 实例高级表单动作路由 → 回调/API 请求 | 删除无 DOM 消费者的 `workspaceRunFlowBtn` 监听；完整运行入口现在由 `workspaceLaunchClosure` 的既有 data-action 委托承接。表单提交、输入与填充 Job 入口保留，不抽第二提交器。 | `element:8`；`fieldName:12` |
| [workspace_help_popover_actions.js](../web/workspace/workspace_help_popover_actions.js) · 79 | R02/R06/R09/R12；用户事件/注入依赖 → 帮助浮层动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `eventTarget:8`；`workspaceHelpTarget:14` |
| [workspace_launcher_actions.js](../web/workspace/workspace_launcher_actions.js) · 92 | R02/R06/R09/R12；用户事件/注入依赖 → 目标输入与实例创建动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:16`；`eventTarget:20` |
| [workspace_model_provider_actions.js](../web/workspace/workspace_model_provider_actions.js) · 91 | R02/R06/R09/R12；用户事件/注入依赖 → 实例模型路由交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_node_actions.js](../web/workspace/workspace_node_actions.js) · 91 | R02/R06/R09/R12；用户事件/注入依赖 → 实例节点交互动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `element:8`；`eventTarget:12` |
| [workspace_node_catalog.js](../web/workspace/workspace_node_catalog.js) · 422 | R02/R06/R09/R12；页面数据/注入依赖 → 实例节点默认/归一化/顺序链 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)、[G14](#g14)；消费后端结果，随所属切片收敛。 | `workspaceNodeMeta:48`；`workspaceNodeLabel:53` |
| [workspace_node_run_state.js](../web/workspace/workspace_node_run_state.js) · 76 | R02/R06/R09/R12；页面数据/注入依赖 → 节点执行方式和运行内容 → 派生状态/界面结果 | 契约/维护关联 [G10](#g10)；消费后端结果，随所属切片收敛。 | `workspaceNodeSupportsAgentRun:32`；`workspaceNodeSupportsJobRun:39` |
| [workspace_run_actions.js](../web/workspace/workspace_run_actions.js) · 85 | R02/R06/R09/R12；用户事件/注入依赖 → 运行列表和筛选交互动作路由 → 回调/API 请求 | N13B1 键盘只激活聚焦的整行本身；原生按钮/summary保留自身动作，Enter/Space与无多余日志请求通过。 | `handleRunListKeydown` |
| [workspace_run_detail_actions.js](../web/workspace/workspace_run_detail_actions.js) · 399 | R02/R06/R09/R12；用户事件/注入依赖 → 详情、回放、比较、导出动作动作路由 → 回调/API 请求 | N07A-UI报告动作先分派，沿用原导出与日志；阅读不触发整行默认日志/执行。N13B1原生事件边界保留；H-UI按原workspace/run/step/attempt/child完整key提交keep_running，成功需持久回执，失败先GET原run，不自动POST，未知只读重查；每个HTTP请求复用config注入等待预算，非总动作deadline；原Job stop只接精确child并移焦点至目标区。G20余项开放。 | `handleRunSurfaceClick`；`toggleRunReplay` |
| [workspace_run_filter.js](../web/workspace/workspace_run_filter.js) · 195 | R02/R06/R09/R12；页面数据/注入依赖 → 运行筛选条件 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:22`；`normalizeFilters:26` |
| [workspace_run_replay.js](../web/workspace/workspace_run_replay.js) · 226 | R02/R06/R09/R12；页面数据/注入依赖 → 摘要回放展示 → 派生状态/界面结果 | N16A-UI接共享notes，原诊断步骤优先后补说明；退出旧裁180字error属性/展示，无已知调用者。仍为摘要预览最多4步，状态/数据来自后端。 J1-UI接显式展示依赖，app核同run非linked/计划身份，只用timeline快照；旧缺字段保留。 | `stepLine`；`previewMarkup`
| [workspace_run_report.js](../web/workspace/workspace_run_report.js) · 188 | R10/R12；run/attempt与API正文/文件元数据 → 有身份的读取、失效与布局 → 独立报告阅读视图 | N07A-UI唯一阅读控制器，显式依赖，无正文持久缓存/轮询；11组件契约、真实主链/15边界/历史读取通过。正文失败清空、旧响应丢弃；文件watch与修复不在本片。 | `statusInfo`；`entryMarkup`；`load`；`sync`；`handleClick` |
| [workspace_run_step_notes.js](../web/workspace/workspace_run_step_notes.js) · 31 | R09/R12；step.detail/error/recorded_error与显式escape/展开依赖 → 安全无状态说明标记 → 当前步骤/回放共同展示 | N16A-UI新增，两个现存消费者；不判状态/清洗错误，无新缓存/轮询。去重/真实错误/原文/长文本/键盘通过；[G25](#g25)已修。 | `hasNotes`；`markup` |
| [workspace_run_state_merge.js](../web/workspace/workspace_run_state_merge.js) · 382 | R02/R06/R09/R12；页面数据/注入依赖 → HTTP/SSE run/step 版本合并 → 派生状态/界面结果 | N16A事件摘要接detail/recorded_error，真实run.updated合并及4局部字段/新attempt契约通过；N13A稳定身份保持，未新增前端错误清洗。G02/G20余项开放。 | `defaultTimestampMs:17`；`timestampMs:22` |
| [workspace_run_summary.js](../web/workspace/workspace_run_summary.js) · 410 | R02/R06/R09/R12；页面数据/注入依赖 → 运行进度/交付摘要 → 派生状态/界面结果 | N07A-UI受管报告按file_verified/incomplete说明交付，退出重复正文摘要；legacy无report_id仍有消费者，保留原摘要。N04-D-UI 新增 actualJobTargetMarkup(job,deps) 纯展示，缺记录有提示，GPU0/空环境/长内容/转义契约通过；N04-F-UI增加options.parentStatus，仅从Job状态显示独立文字，父失败/停止提示与缺记录说明；G-UI增加jobLogHandoffMarkup纯helper，核对run/step/attempt/Job/host与schema，仅读持久output，完整性冲突保守需核对，空完整/旧/缺失/失败分开，正文转义。H-UI增加continuationContext/continuationControlMarkup纯投影，核对停止回执身份、等待资格、未知/拒绝/处理中反馈，子任务停止按钮仅精确引用且父回执确认后显示；不读全局或包默认。不修一般旧声明语义，G06余项开放。 J1-UI新增childSubmissionPresentation供列表/回放，核计划首Agent身份，仅解释三个后端状态。 | `escapeFor:17`；`statusFor:21` |
| [workspace_shell_actions.js](../web/workspace/workspace_shell_actions.js) · 54 | R02/R12；可见编辑/返回动作 → 注入回调 → 独立edit/原页 | N13B3a退出drawer toggle绑定，接唯一编辑/返回按钮；原运行阅读编辑入口复用同回调。 | bind |
| [workspace_template_diff.js](../web/workspace/workspace_template_diff.js) · 282 | R02/R06/R09/R12；页面数据/注入依赖 → 模板/实例差异 → 派生状态/界面结果 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `escapeFor:13`；`diffStatusLabel:17` |
| [workspace_template_migration_actions.js](../web/workspace/workspace_template_migration_actions.js) · 174 | R02/R06/R09/R12；用户事件/注入依赖 → 模板迁移动作动作路由 → 回调/API 请求 | 保留；全文件语法及公开 helper 结构检查未发现独立缺陷；不为抽取而再抽取。 | `selectedWorkspace:8`；`cachedDiff:12` |
| [workspace_tool_catalog.js](../web/workspace/workspace_tool_catalog.js) · 82 | R03/R12；目录/工具ID → 分类与既有能力徽章 → 展示投影 | N13B3b1-UI删除只被旧重复summary调用的函数/export；其他分类/权限消费者仍在。merge推荐及Agent模板调用保留，不将目录数量当执行能力。 | workspaceToolById/workspaceToolCategoryLabel/workspaceToolPolicyBadge |
| [workspace_workflow_submission.js](../web/workspace/workspace_workflow_submission.js) · 89 | R06/R11/R12；工作区/固定范围参数、存储/HTTP/client ID → 提交前持久身份/确认/重发 → 本次 run 或待核对错误 | N03A 新增唯一浏览器直接运行提交组件；sessionStorage 同标签页刷新恢复，未知错误不换键、损坏/不可用不发请求。不推进流程、不猜终态；作用边界见第三部分 2.6。 | `validArguments:6`；`sameArguments:13`；`submit:18` |

### 本地验证与历史文件

用户清理后，tests/ 与旧 dev_work/smokes/ 不再有现存脚本，历史文件可从 Git 读取。N01 新样机集中在本地 dev_work/n01/：common.py 管理配置与模拟外部任务，engines.py 包含 LangGraph/SQLite 对照，cli.py 提供跨进程本地演示，verify.py 验证故障与恢复；这些均不进入正式源码或远端。第三方环境、锁文件、数据库、输出文件同样只保留本地。N02 的存储契约检查、真实服务/HTTP 验证和崩溃注入位于本地 dev_work/n02/，隔离配置位于忽略的 config/n02-local/；它们也不进入正式源码或远端，过程限制见第三部分 2.5。

### 配置、公开样例与测试入口

| 文件 | 检查结论与解决方向 |
| --- | --- |
| [config/servers.toml](../config/servers.toml) | R01/R10/R12/R13/R14；安全本地默认/SSH发现、N07A报告目录示例；N13C2公开status_load_timeout_seconds=30与1–300/重启生效说明，无真实目录/凭据。 |
| [config/user_servers.example.toml](../config/user_servers.example.toml) | R01/R13；保留覆盖模板；后续输入校验统一，实际用户覆盖仍忽略。 |
| [config/secrets.example.toml](../config/secrets.example.toml) | R13；保留 SSH 密码格式示例；不等于推荐明文密码，真实 secrets 不入库。 |
| [data/agent_definitions.json](../data/agent_definitions.json) | R03；保留公开 Agent 目录；与真实 adapter/Provider 绑定校验，关联 G10/G11。 |
| [data/tool_definitions.json](../data/tool_definitions.json) | R03；保留工具 schema；明确建议/真实读取/异步执行级别，关联 G11。 |
| [data/workflow_templates.json](../data/workflow_templates.json) | R02/R05；保留起始链；顺序执行与拓扑预览分开，新增 Transfer 后版本化。 |
| [config/workflow-poc.example.toml](../config/workflow-poc.example.toml) | R06/R13/R14；N01 无密钥配置模板，定义引擎、隔离状态目录和 worker 延迟；仅本地样机读取，正式服务尚未接入。 |
| [pytest.ini](../pytest.ini) | R14；历史 testpaths=tests 与 scratch 排除；当前没有正式测试文件，后续按切片生成本地检查；无用例不算通过。 |
| [requirements.txt](../requirements.txt) | R14/G08；唯一直接运行依赖声明，固定 cryptography/LangGraph/SQLite saver；两个独立 Python 环境安装/HTTP/框架持久化通过。间接依赖仍由 pip 解析；N03B2b 已接单 Job 生产协调器，不用开发工具包扩大启动要求。 |

### 台账完整性与维护

正式代码台账包含 291 行，一文件一行；README.md同步真实能力/报告配置与API，.gitignore增加data/reports/私密运行正文排除；配置/公开数据/依赖与验证入口 9 行；本地样机/安装验证另说明职责，不列为生产源码。代码路径集合来自当前实际源码树，不按历史目录猜测。新增、删除或改职责时同步对应行和 G 问题状态；不把未跑过的场景写成已验收。
### N03B2c2c-UI：ready 隔离执行包的真实启动闭环（已验收）

对应 R06/R12、G10/G11/G26。使用独立 `TOTAL_CONTROL_DATA_DIR`、端口 8771、本机 CPU 主机和显式 `tools=[]` 报告 Agent；夹具先经正式 automation/apply，再用公开工作区更新接口恢复空 allowlist，最后由 `/cockpit` 读取 `execution_bundle.ready_to_execute=true` 且 `missing=[]`。浏览器只通过可见驾驶舱点击，API 仅用于准备、观察和重放核对。

真实 Chromium 在 1440×900 驾驶舱点击“运行工作流”，捕获 `POST /api/workspaces/{id}/run` 201 与 `run_id=20261015-131319-f91dfa71`，随后进入该次运行阅读。31 条状态观测显示 `compute=running/queued`、`report=pending`，再到 `compute=done`、`report=running`、两步 `done`；本机 Job 的实物计数为 1，Agent 只读取本次 Job 结果并返回报告。首个请求在浏览器侧延迟期间再次真实点击只产生 1 个 POST；页面刷新后以原 `request_id` 重发，服务重启后再次以同一原请求体重发，均返回同一 run，工作区最终只有 1 个 run。390×844 页面能看到“打开当前运行”，无 pageerror；桌面/窄屏截图和完整响应观察只存本地 `dev_work/artifacts/n03b2c2c-ui/`。

过程审查保留四次 smoke 自身错误：误进配置中心、对隐藏运行记录选择器操作、对折叠历史入口未展开、等待观测字典断言错误，以及响应已返回后才发起第二次点击。每次均停在本地脚本或页面路径，未改生产状态；修正后才取得通过证据。响应延迟只用于验证 busy guard，受控本机 Provider 只证明适配器接线，不证明真实供应商、真实模型、SSH/GPU/传输或 Agent 工具调用。服务重启验证的是已完成 run 的同键重放，不覆盖外部任务在未知提交窗口中的恢复；完整长报告交付、取消传播和多节点/子任务仍开放。

消融决定：没有新增提交器、轮询器、状态机或配置入口；复用 `workspaceLaunchClosure`、既有 `workspace_workflow_submission.js` request_id 幂等、后端持久 run/Job/Agent 协调器和现有运行阅读器。N03B2c2c-UI 完成后，G10/G11 不因“无工具 Agent 单链”整体关闭，下一片应从 Job→Agent 等待/恢复、工具执行或更长报告交付中选择一个清楚边界。

<!-- FILE_AUDIT_END -->
