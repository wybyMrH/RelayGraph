# 工作台信息架构与交互设计

设计版本：UX01G1；更新于2026-11-09。当前是全产品使用需求调查，尚未进入新布局或实现。用户再次指出 UI02 仍隐藏必要信息、操作不便，工作台/配置中心职责与配置设计能力没有充分保留；因此暂停 UI03A，只读原型及历史点击验收不代表产品方向被接受。WB01–WB05 的既有模拟证据保留，正式接线仍未交付；不以这些证据宣称全产品设计完成。本文为[稳定规格](project-spec.md)的统一设计附件，问题事实见[当前审查](current-audit.md)，唯一执行指针见[阶段计划](next-stage-plan.md)。

## 0. 当前路线：先查用户怎样使用，再决定页面

### 产品的两条入口与调查顺序

用户一方面要直接管理主机、GPU、命令、文件和会话，另一方面要围绕研究目标配置项目、设计流程、执行并检查结果。两条入口共用主机、路径、Job、日志与证据，不强迫直接操作先建项目，也不把工作台缩成只看运行。旧界面可以提供需求线索，其拥挤布局和隐式联动不作为新方案依据。

目前 **UX01A巡检、UX01B主机配置、UX01C直接/批量任务、UX01D文件/传输、UX01E终端/tmux及现活动、UX01F1模型连接/路由、UX01F2搜索接入、UX01F3A Agent定义/模型覆盖/授权、UX01F3B工具定义/测试及UX01F4A模板定义/绑定/校验、UX01F4B版本/快照/显式迁移及UX01G1项目入口/目标输入/创建回执调查** 已在各自限定范围内完成。后续调查顺序是项目/流程设计与运行（唯一下一片UX01G2A基本资料/来源/运行设置编辑）、维护。各域调查闭合并交叉核对后，才形成全产品页面合同，再挑一个页面/功能的小片做可操作原型、视觉优化和浏览器验收。每片独立验收、更新文档并安全提交推送，不并行实现多个功能域。

| 功能域 | 要回答的用户问题 | 已有能力必须保留的调查范围 | 当前调查状态 |
| --- | --- | --- | --- |
| 主机与资源巡检 | 哪些机器能连、卡是否有余量、谁在占用、采样可信吗 | 全组 GPU/计算进程、主机资源、筛选、排序/置顶、刷新、完整命令、安全停止入口 | UX01A 已完成下述限定字段/消费者与隔离观察；生产未改 |
| 主机配置 | 没机器时如何添加，连接错了在哪里修 | 发现与自定义来源、增改/别名/检查、隐藏/删除/恢复、条件参数与凭据边界 | UX01B 已完成下述字段/源码链与隔离界面观察；真实配置/SSH未验 |
| 直接及批量任务 | 如何执行一条命令或一组实验，如何确认本次提交 | cwd/env/CPU-GPU/资源等待、task-plan/preset 预览调度、回执/日志、停止/重试/复制/排序/清理 | UX01C 已完成下述字段/源码与隔离观察；真实执行/profile链未验 |
| 文件与传输 | 怎样确认文件位置、处理冲突并知道结果 | host+path、多源集合、浏览/预览/下载、过滤/覆盖/跳过、进度与结果核验 | UX01D已完成下述字段/源码与隔离观察；下载保存、目标选择和真实传输/核验未通过或未验 |
| 终端与现活动 | 如何排查正在执行的任务，关闭到底意味着什么 | Job 日志、tmux 读取、真实终端的打开/输入/中断/结束；选择与输出标签 | UX01E已完成下述字段/源码、纯方法与隔离观察；390创建被挡失败，真实PTY/信号/恢复未验 |
| 全局配置 | 如何定义可复用能力，并检查修改影响 | LLM/Search 连接、目录与调用测试、Agent/工具定义及授权、调试、模板版本与迁移 | UX01F1模型连接/路由、UX01F2搜索接入、UX01F3A Agent定义/授权及UX01F3B工具定义/测试、UX01F4A模板定义/绑定/校验及UX01F4B版本/快照/迁移已限定完成；项目入口/创建已由UX01G1限定调查；只读目录不能替代编辑操作 |
| 项目与流程 | 如何修改项目、设计步骤并执行可支持的计划 | 实例资料/环境/覆盖、节点与 I/O、发现和显式应用、保存/门禁、运行/child/停止后续、历史报告 | UX01G1入口/目标输入/创建回执已限定调查；下一G2A基本资料/来源/运行设置，能力覆盖/逐节点/发现/运行仍待逐片闭合 |
| 维护 | 哪些内容会被清掉，是否影响证据 | 预览缓存、日志文件、持久运行记录，各自设置/预览/清理语义 | 尚待具体字段与服务调查，不视为覆盖完成 |

后端已有而新原型未展示的写操作和条件参数必须单列保留位置或待核原因，不降为未来新功能。每项能力分别标记源码接线、浏览器观察、模拟、真实缺口或未验证；接口存在、截图可见、模拟完成都不能互相替代。

### 页面合同的准入要求（先定规则，不先画布局）

- 工作台与配置中心必须有独立页面身份和直接入口，支持地址直达、刷新、前进后退与准确返回；不能仅给原模式切换换名字。具体页面实现方式待独立验证，不因此整体更换技术栈。
- 每页写清主任务、直接可见信息、编辑字段、动作、反馈和离开/返回行为。用户为比较各卡或找占用者而来时，不应先逐机点两次才能获得原有信息；独立详情也不能成为所有日常操作的强制中转。
- 项目设置、全局可复用配置、浏览器偏好、未保存草稿和本次运行快照分开。选择主机、筛选进程、任务提交主机、终端主机、传输源/目标不是同一个“全局当前主机”。
- 页面必须设计完整输入→校验→保存/提交→反馈→后续操作，包含取消和失败；不以只有状态卡片的原型视为完成。直接提交小片至少带本次任务回执、状态和日志去处，不能依赖后台或手工补记录。
- 实际接线前核对公开 schema、旧记录读取、精确对象与选择来源；复用既有状态合并和恢复。新模拟字段不得变成第二套事实协议，前端不补后端终态。
- 同一事实可服务多个任务投影，并非天然冗余。删除展示/入口前先列消费者，固定输入和故障，对照数据、操作、副作用、证据及路径；低频不等于无用。

### UX01A 的需求和来源

对应 R01/R07/R12、G15/G26/G41。主任务是“打开即可比较全组资源 → 找到占用者 → 阅读准确命令或进入明确的安全操作”，同时为无配置用户保留主机管理入口。本片只调查，不规定最终卡片/表格/详情布局，不执行主机写入或进程停止。

权威链路为 [monitoring.py](../total_control/state/monitoring.py) 的 `status_payload/refresh_server_status` → [app.js](../web/core/app.js) 的 `applyStatusPayload/renderHeader/renderOverview/renderServers/renderGpuRows/renderProcesses`。采集事实来自 [gpu.py](../total_control/infra/shell_pkg/gpu.py) 和 [host.py](../total_control/infra/shell_pkg/host.py)；展示/筛选/动作消费者见 [server_list_markup.js](../web/monitoring/server_list_markup.js)、[monitoring_process_filters.js](../web/monitoring/monitoring_process_filters.js)、[monitoring_table_markup.js](../web/monitoring/monitoring_table_markup.js)、[server_list_actions.js](../web/monitoring/server_list_actions.js)、[monitoring_filter_actions.js](../web/monitoring/monitoring_filter_actions.js) 与 [index.html](../web/index.html)。

下表的“保留”是保留用户需要的事实/操作，位置待全部调查后确定。只读字段统一来自 API；不通过展示写回配置或运行。缺值目标为未知，表内注明的现有 0/空闲回退不能沿用为正确语义。按当前实际控件与 renderer 列清，服务端尚无消费者的值另列，未声称穷举所有未来扩展字段。

| 字段/展示项 | 用途、来源与出现条件 | 当前默认/校验 | 联动与保存影响 | 调查决定 |
| --- | --- | --- | --- | --- |
| `server.id` | 主机身份；API 每条服务器记录必需 | 现选中 ID 不存在时可选首个 online/reachable/首项；不是确认过的新身份 | 决定选中、刷新、tmux、命令阅读与操作目标；不应按名称匹配 | 保留身份；坏链接不能静默换机器 |
| `name` | 人可读主机名；主机目录来源 | 显示名称，非 SSH 地址 | 主机列表、GPU/进程行、选择器共同使用；点击不保存主机配置 | 保留；长名称仍可辨认 |
| `mode`、`target`、`labels` | 连接方式、连接目标、分类；采集 payload | 不是用户应在巡检页再次输入的字段；空值不可伪造目标 | target 用于身份/完整命令上下文；labels 当前 payload 携带但巡检未提供编辑 | 保留来源/诊断，标签的现有编辑边界见下节 UX01B |
| `reachable` | SSH/本机可达性；所有主机 | 非布尔时现回退 `online` | `serverIsReachable` 决定已连接分组、终端可达提示 | 保留；区分未知与不可达 |
| `online` | GPU 采集成功标志，非纯 SSH 状态 | 当前 `onlineServers` 据此选出 GPU/进程数据范围 | 决定 allGpus/allProcesses；可连接但无 nvidia-smi 的主机不因此从目录消失 | 保留含义，不改叫整机在线成功 |
| `monitor_ok` | GPU 采集能力状态；采集端返回 | 当前巡检主要依据 online/reachable 推出异常，没有独立使用此值 | 不应新增前端自造“监控成功”判据 | 保留 API 事实；一致性待正式接线核对 |
| `error`、`error_kind` | 连接/采样失败解释；异常时 | 现主要显示 error，error_kind 未独立呈现 | 主机错误文本、资源异常提示；只读 | 保留分类与原因，长错误单独可读 |
| `collected_at`、`elapsed_ms` | 单机采样时间/耗时；采集端 | collected_at 尚未统一显示在每机巡检摘要；elapsed_ms 无独立巡检消费者 | 不能用全局刷新完成时间代替单机采样时间 | 保留采样可信度；耗时诊断按需 |
| `refresh_skipped`、`refresh_skip_reason`、`refresh_skipped_at` | 连接退避时重用旧采样 | 当前主机列表未清楚说明重用 | `collect_all/mark_status_reused` 返回旧记录，不能当新采样 | 保留来源；新鲜/陈旧阈值和兼容须另核，不发明已有 TTL |
| `refreshed_at`、`status_age_seconds` | 全局快照读取摘要；status payload | `renderHeader` 现 age 缺失回退 0；不能据此证明刚采样 | 全局刷新与选择后 render 会影响顶栏，不写配置 | 保留紧凑可信时间；缺值未知 |
| `host_resources.ok/error/collected_at` | 系统资源采集结果，与 GPU 采集分开 | 空对象→待采集，ok=false→主机资源异常 | 当前主机徽章和资源浮层；单项失败不抹其他资源事实 | 保留来源/异常；浮层交互需后续优化 |
| `cpu.util_percent`、`cores`、`load1/load5/load15` | 判断 CPU 压力和负载 | 徽章显示利用率，浮层显示核数与 load；不是任务进度 | 主机资源纯展示；缺值不当 0 | 保留判断能力，不另建采集器 |
| `memory.used_percent/used_bytes/total_bytes` | 主机内存压力与容量 | 现徽章和浮层共用这些数据 | 不等于 GPU 显存；缺值/单位需区分 | 保留 |
| `swap.used_percent/used_bytes/total_bytes` | 排查交换空间 | 现仅资源浮层 | 数据不存在不能显示“未用交换空间”作为事实 | 保留诊断能力，位置待定 |
| `disks[].mount/device/fs_type/used_percent/used_bytes/total_bytes/free_bytes` | 磁盘容量/挂载点 | 当前主磁盘取首项，列表最多 5 项；device/fs_type 用于 title | 巡检只读，不代表路径存在或有写权限 | 保留完整数据访问需求；不把首项当项目目标盘 |
| `disks[].inode_*` | 排查小文件耗尽 inode；采集端已有 | 当前标题虽写“磁盘 / inode”，renderer 没呈现 inode 值 | 无编辑或保存 | 登记已有数据展示缺口，不假称 inode 已可查 |
| `network.rx_bytes/tx_bytes/interfaces[]` | 网络累计收发量 | 现最多 4 接口；缺接口时显示总量；不是实时速率 | name/rx_bytes/tx_bytes 同快照展示，无采样间隔速率算法 | 保留单位与累计含义；未知不补 0 |
| `gpu.index/name` | 在主机内定位某张卡 | index 需与 host_id 配对；卡号可跨主机重复 | GPU 选中/进程关联主键是 host+index | 保留，跨机比较不只按卡号匹配 |
| `memory_used_mib/memory_total_mib` | 每卡显存量和容量 | MiB 由 formatter 换算，bar 取占用比；缺值现可变 0 | 不是资源预留或整批任务进度 | 保留明确单位、缺值语义 |
| `memory_free_mib` | 可用显存条件与候选参考 | 当前巡检表不直接显示，任务消费者另查 | 不能把采样余量叫已分配/已预留 | 保留跨域需求，任务条件归后续调查 |
| `gpu_util` | 每卡算力利用率 | 当前 `Number(gpu_util ?? 0)`；0%+显存较高显示“显存占用” | 不等于空闲或任务已结束 | 保留真实 0 与未知的区别 |
| `temperature` | 温度判断 | 当前 `?? 0` 显示 °C，未知会变 0°C | 无配置写入 | 保留；不复制缺值回退 |
| `gpu.state` | 采集端按阈值、显存和进程计算 busy/idle | 全局空闲数只算 idle；主机卡按总数减 busy，会把 unknown 当闲 | 影响排序和候选提示，但不是锁 | 保留统一语义，未知不算空闲 |
| `process.pid/gpu_index` | 定位本机 GPU 计算进程 | PID 与主机配对；GPU index 可缺；不是 Job ID | 命令阅读/停止目标；不可猜关联 Job/run | 保留 |
| `process.user/uid`、`current_user/current_uid` | 查占用者和确认停止归属 | UID 优先，缺身份需确认；当前用户可来自 host_resources | 前端确认只作提示，服务端执行前还须实时核对 | 保留；缓存不作为最终授权证据 |
| `process.used_memory_mib` | 进程 GPU 显存占用 | formatter 显示；不等于主机 RAM | 查询/排序/命令详情 | 保留 |
| `command/process_name` | 准确知道执行内容 | command 缺失回退 process_name；搜索可覆盖完整命令 | 点行打开 process 类型输出标签，关闭查看不是停止 | 保留完整阅读与长内容能力 |
| `summaryOnlineServers` | 已连接/配置主机数 | 用 connectedServers，不等同 onlineServers | 与顶栏/目录属于同事实不同任务投影 | 保留总览需求，重复样式可后续消融 |
| `summaryIdleGpus` | 当前采样范围内 idle 卡数 | allGpus 限 online；只算 state=idle | 不计未采集机器，不代表可立即独占 | 保留范围说明 |
| `summaryRunningJobs/summaryTransferJobs` | 本服务任务压力 | running 含 starting/blocked；transfer 含 queued 等活跃状态 | 进程数不能替代 Job 数；Transfer 与 Job kind 边界后续查 | 保留需求，分清状态，不沿用含糊名称 |
| `summaryAlertServers`、趋势 busy/process 序列 | 最近观察到过异常/变化 | serverHistory 仅当前浏览器内最近 8 次记录，不是后台告警或长期时序 | 迷你图和异常数使用内存历史，异常排序另取当前主机字段；刷新周期重复读取也会追加 | 保留诊断意图；不把旧异常冒充当前故障，不伪造趋势 |
| `healthPill/statusLoad*` | 页面读取/连接提示 | 成功仍常驻“状态读取完成/30秒” | 失败/超时保重试，组件启动失败保整页重载 | 正常成功块需求删除；本片不改 UI、不削弱故障恢复 |

以下为本片所有巡检输入与动作。默认值区分初始化和恢复值；偏好保存不等于后端配置保存。主机管理表单的实际写字段见下节 UX01B，不用“入口已在”替代管理能力验收。

| 控件/动作、消费者 | 输入、默认及校验 | 结果/联动 | 保存/副作用及决定 |
| --- | --- | --- | --- |
| `manageServersBtn` → `ServerAdminActions/openServerModal` | 用户显式打开；无主机时也需可达 | 当前管理弹窗含连接管理及运行数据维护，职责混排 | 保留管理/诊断入口；实际写入见下节 UX01B；维护拆分位置待全域调查 |
| `serverSortSelect` → ServerListActions 的 `setServerSort` 回调/`sortedServersForDisplay` | 默认/手动/空闲/异常/GPU数/进程数/名称；恢复浏览器偏好 | 排序主机，不筛掉 GPU/进程；置顶优先 | localStorage，非服务器配置；保留偏好，可逆 |
| 主机 pin → `toggleServerPin` | 合法服务器 ID；无偏好为空数组 | 调整置顶，与手动分组排序结合 | localStorage pins/order；保留；不重复写后端 |
| 主机拖拽 → `moveServerInManualOrder` | 仅 manual；同置顶分组内才移动 | 调整显示顺序 | localStorage；保留需求；键盘替代待后续设计/验收 |
| `offlineServerGroup` | 初始 `offlineServersOpen=true`，同页保留开合状态，选中离线项时展开 | 只折叠不可达主机，不删除配置 | 内存偏好非运行状态；不能让异常对象不可找到 |
| 主机卡点击 → `selectServer` | host_id，重置 selectedGpu=auto | render 全组数据，选中机器并读其 tmux；不修改进程过滤 | 保存 selectedServer；不改连接配置；保留单次选择 |
| GPU 行点击 → `selectGpu/setProcessFocusForGpu` | host_id+index | 选机器/卡，聚焦关联进程；若现过滤挡住目标，改 server/gpu、清 user，必要时清 query | 保存主机，过滤/焦点为 UI 状态；保留定位能力，隐式改过滤需明确反馈/可还原 |
| `processSearch` → `setProcessFilter(query)` | 默认空；匹配主机/卡号/PID/用户/显存/完整命令，不只是占位文案列出的字段 | 仅筛进程；重绘 filter 仍保有效值 | 内存，不写任务；保留，空结果与无采集区分 |
| `processServerFilter` | 默认全部，选项来自在线主机；失效值当前清空 | 筛进程，不等于主机卡选择 | 保留；不能合成全局主机选择 |
| `processUserFilter` | 默认全部，选项来自真实进程用户；失效值清空 | 筛进程；点 GPU 可能清此选择 | 保留，并明确联动 |
| `processGpuFilter` | 默认全部，选项来自有进程的卡号 | 卡号跨机器，不自动加主机条件 | 保留，不把“GPU 0”当全局唯一身份 |
| 进程列标题 → `sortProcessTable` | server/gpu/pid/user/vram/command；默认 server asc，再点反向 | 改进程排序，不改主机顺序 | 内存；保留 |
| 进程列拖宽 → 原 col-resizer 绑定 | 每列最小宽度/窗口约束，恢复保存值 | 仅阅读偏好；不能靠挤列隐藏完整内容 | localStorage 按列；保留需求，移动端方案待定 |
| 主机资源 hover → `showServerResourcePopover` | 目标主机 DOM，鼠标进出控制浮层 | CPU/内存/磁盘/网络阅读，不是配置编辑 | 当前可能遮挡 GPU 点击；保留数据访问需求，交互待改；键盘入口未验收 |
| 点进程行 → `showProcessCommand` | host_id+pid，查当前主机快照内进程 | 完整命令与归属进入 process 输出标签 | 仅查看，不能命名为完整 Job 日志；保留 |
| `refreshBtn` → `loadStatus(true)` | 读取预算来自服务注入 meta；在途按钮限制 | GET refresh 实际后端可采集主机并监测任务，非纯本地重画 | 保留动作与错误重试；调查中只合成接口，不做真实采集 |
| 主机刷新按钮、`refreshSelectedServerBtn` → `refreshServerStatus` | 明确主机 ID，同机在途不重复 | GET 单机 refresh；响应含整份 status+server，现更新主机并恢复阅读位置、读取 tmux | 保留局部失败反馈和对象归属；不创建新状态合并器 |
| 进程“关闭” → `stopProcess/confirmStopProcess` | host+pid；非本人/未知归属先确认，取消不发请求；后端实时核身份 | POST stop，可返回 409 要求重新确认；后端脚本可涉及进程组/tmux pane | 必须保留安全操作与影响说明；不是只隐藏行或仅杀一个 PID；本片未执行 |

跨域主机上下文的实际消费者是 `renderFormOptions/selectedServerFromForm`（命令）、`renderTerminalOptions/selectedTerminalServerFromForm`（终端）、`transferSourceServerId/transferTargetServerId`（传输）及项目节点配置。切页可预填，但不应静默保存或改变另一表单的提交对象；其字段和保存行为分别交后续调查。

### UX01A 实际浏览器观察、冗余判断与交接

2026-11-09 使用 xng 环境 Playwright/Chromium 140，加载当前未修改的 HTML/CSS/JS；页面地址为隔离的 `http://relaygraph-ux01a.invalid/`。所有请求由浏览器路由拦截：静态文件来自当前 web/，仅把两个启动预算占位符替换为 30（模拟 Handler 的注入）；status/refresh/Provider 空目录/tmux 空列表/单机 refresh 全为公开结构的合成数据。未列 API 返回错误，非 GET 不提供写入；没有运行后端、真实 GPU/SSH/Provider 或停止请求。不是新版原型验收，也不是实际采样/恢复能力证明。

- 完成 15 项观察，最终 1028 个拦截请求全为 GET，pageerror 为空。1440 实际点击了主机选择、GPU 关联、搜索/筛选、1660 字符完整命令、非本人停止确认后取消、排序/置顶后刷新，以及单机/全局合成读取失败。选择主机后仍为全组 3 GPU/2 计算进程；没有把它改成单主机视图。
- **保留失败**：首轮点 GPU 被资源浮层持续遮挡而超时。第二轮同路径仍遮挡，截图和错误保留，额外把鼠标移出浮层、等它关闭后才可继续。未 force click、未删 DOM/改 CSS/暂停轮询；不能把后续完成记为原路径顺畅。
- 1024/768/390 仅采集布局和宽度、空/长名称/长错误/未知输入截图，没有声称四宽交互、键盘或实际滚动可达已通过。768 进程表宽 878px、390 的 GPU/进程表为 426/878px；文档宽不溢出不等于无需横向阅读。主代理实看了 1440 遮挡和 390 首屏，后者仍被侧栏及统计区占据。
- 缺数值/unknown 的合成输入显示每卡 0MiB/0%/0°C，主机卡显示 1闲/1卡，但全局空闲数为 0；这是输入消费和两种投影不一致的证据，不声称生产采集自然产生了该坏数据。CPU 可达但 GPU 采集失败的合成输入仍显示已连接/GPU 异常，不能笼统叫整机离线。
- 冗余候选：同一主机反复显示小徽章/趋势/总数，以及正常成功大块；先核使用任务再减。全局健康、机器选择、跨卡比较和占用者分别回答不同问题，不能因为都含 GPU 数字就删掉其中一项。当前不删除任何旧入口/helper/展示。

本地脚本、请求、失败和截图暂存 `/tmp/relaygraph-ux-audit/ux01a/`，不提交；dev_work 路径本轮无法访问，未修复或重建用户目录。后续需补四宽实际任务/键盘/滚动、旧记录和真实接口验收，不能拿本片代替。本片当时交接 UX01B，完成情况见下节；在所有功能域调查闭合前不固定全产品布局。

### UX01B：主机配置与首次配置入口的需求和来源

对应 R01/R12/R13、G09/G19/G26/G41。用户要完成的是“知道已有机器来自哪里 → 添加或修正连接 → 保存后检查 → 回到资源巡检”，并可区分只改显示名称、隐藏发现项、删除自定义项及恢复。不能要求用户先理解覆盖文件，也不能把所有机器当成 SSH。此片仅调查现状与确定后续设计约束，未确定新布局，未实现修复。

源码链：[index.html](../web/index.html) 的 `serverModal/addServerForm` → [server_admin_actions.js](../web/monitoring/server_admin_actions.js) 事件路由 → [app.js](../web/core/app.js) 的 `openServerModal/loadAdminServers/editServer/addServer/saveAlias/checkServerConnection/removeServer/restoreDiscovery` → [GET](../total_control/http_api/get_routes.py)、[POST](../total_control/http_api/post_routes.py)、[DELETE](../total_control/http_api/delete_routes.py) → [ServersMixin](../total_control/state/servers.py) → [config.py](../total_control/config.py)。连接检查继续到 [checks.py](../total_control/infra/checks.py) 与 [ssh.py](../total_control/infra/shell_pkg/ssh.py)；[传输适配器](../total_control/infra/shell_pkg/transfer.py) 的 SSH 参数存在差异，留待 UX01D 交叉核对。此处只读代码，未读取真实主机配置、密码或主密钥。

**配置来源不能合成一种“发现”。** 当前配置加载依次处理基础配置的显式 servers、用户覆盖的 servers、SSH 发现；同 ID 先到者保留。因而用户覆盖与基础配置同 ID 时，写成功未必改变实际连接。别名映射先合并基础及用户值，再按 SSH 别名/ID/地址/user@host 查找，可能盖住 entry.name。发现项须符合 include/exclude 且未被隐藏；解析器只读取简单显式 Host 段，跳过通配/否定 Host，不完整解释 OpenSSH 的 Include/Match。若加载后没有任何主机，会自动补 `Local`。因此“无真实配置”不自然等于 API 返回空数组。

管理接口目前只用 `is_user`（ID 是否在用户覆盖中）区分来源，其他项全标 SSH 发现路径；这会误标基础配置和 Local，且发现路径只读用户覆盖、并不完整反映基础发现配置。新页面须展示可信来源与有效配置，未知来源明确未知，不能让现有错误标签决定可执行动作。

### UX01B 字段清单与保留决定

以下列当前六个可编辑表单字段、行内名称及关联配置/诊断字段；非可编辑项明确注明。默认是当前实现行为，不是承诺正确的产品契约。“保留”表示保留语义/能力，最终入口与布局在全域调查后确定。

| 字段/用途 | 来源、必需条件与当前默认 | 校验、联动与保存影响 | 决定与后续归属 |
| --- | --- | --- | --- |
| `name`：表单“显示别名” | 新增空、编辑回填有效 name；新增/编辑都必需 | HTML required、服务端 trim 后非空；写 entry.name。已有 server_aliases 可覆盖它，故保存后显示名未必改变 | 保留人可读名称；与行内显示名映射统一编辑意图前先确认来源，不直接合并底层值 |
| `host_name`：地址 | 新增空、编辑回填；新增 SSH 与 ssh_alias 至少一项 | 新增由服务端拦截二者皆空；编辑二者皆空沿用旧目标，只有一项非空则按该组新输入重建；user+host 时连接优先 user@host | 保留连接地址；设置负责输入，巡检只读有效目标，不伪造自动继承 |
| `ssh_alias`：SSH Host 名 | 新增空、编辑回填；与地址的条件同上 | 不是显示名；可参与 ID 生成、名称/密码查找和隐藏键。普通 SSH 在 user+host 都有值时不以 alias 作为连接目标，可能不再匹配 alias 的 IdentityFile/ProxyJump | 保留并与显示名称区分；有效目标与参数来源要可核对，不能把三个字段当同义词 |
| `user`：连接用户 | 新增空，编辑回填；非必需 | 新增空时由 SSH 决定；编辑空会保留旧 user，不能用清空输入表示移除；与 host 联动改变实际 target | 保留；后续需明确“继承/保留/移除”，不静默改认证路径 |
| `port`：连接端口 | 新增空、placeholder=22；22并非已保存默认。编辑回填 | 服务端为字符串，主机编辑未见数值/1–65535范围校验；编辑空保留旧端口，否则 SSH 可能自行取配置/默认 | 保留条件参数；前后端校验与清除语义另片修复 |
| `password`：可选认证密码 | 表单每次编辑都空，不回填；留空新增可走 key 或 secrets，编辑则先保留已有密码 | add/update 把非空值写入 user_servers.toml entry；编辑已有非空密码无法靠空输入清除；无独立移除动作 | 保留认证选择与“已配置/来源”反馈；不得显示原值。凭据持久化/公开响应须独立修复后才正式接线 |
| 行内 `.alias-input` / body `alias` | 回填有效 name；独立“保存名称”，允许空 | `/alias` 写 server_aliases，优先 ssh_alias→ID→host 为键；空值移除这些候选映射，不清 entry.name | 保留只改显示名的轻操作；避免与 name 表单形成用户不可理解的两套名称保存 |
| `id` | 服务端 safe_id，新增可从显式 ID/alias/host/name 生成；UI无输入，编辑保留 | 新增命中已有用户 ID 会直接替换而非冲突；跨域 Job/主机选择依赖稳定 ID，不能按名字重建 | 保留稳定身份/只读诊断；重名冲突须明确处理，不能将新增当隐式覆盖 |
| `mode` | 服务端支持 local/ssh；现新增/编辑前端一律写 ssh，无模式控件 | Local 也能载入同一表单；更新又缺少新增的目标二选一校验，可把 Local 存成无目标 SSH，命令随后可能回退 ID | 保留本机能力；新设计不能仅把 Local 的 SSH 字段折叠来掩盖模式错误，真实缺口另修 |
| `enabled`、`labels` | 配置读取，管理响应含 labels；无编辑控件。新增 enabled=true，发现标签含 ssh/地址 | 编辑保留既有 enabled/labels，不应因新版表单不显示而清掉；新增接口本片未提供标签管理 | 保留已有配置值；是否提供新编辑入口在页面合同阶段决定，不虚称旧页已有控件 |
| `ssh_config_path` | 服务端新增/编辑接受，前端表单不收集；编辑空沿用旧值 | 普通 ssh_command_base 不传 -F；rsync 适配器却会用该路径。不能将“发现读取的文件”当成“执行统一使用的配置” | 保留高级配置，UX01D复核消费者；统一含义前不加自动联动 |
| `ssh_discovery.enabled/config_path/include/exclude` | 基础配置+覆盖合并；enabled缺省false，路径默认 ~/.ssh/config，include缺省或空为[*]，exclude为空 | 现页面只展示发现路径，无这些编辑控件；不是编辑某台主机的字段 | 保留发现能力与只读来源；未来唯一配置位置，不能到每台主机重复输入 |
| `is_user/source/discovery_config_path` | 管理 GET 投影，非用户输入 | 当前按用户 ID 集合推断，可能误标；不是安全可靠的删除/隐藏依据 | 保留来源信息需求，登记 API 投影缺口 |
| `disabled_discovery[]` | 用户覆盖文件与 GET 返回；已隐藏列表 | 删除非用户项写 alias或ID；恢复按提交 alias 精确移除；基础显式 servers 不受该过滤 | 保留隐藏/恢复，不把“隐藏”声称能停机/停止任务/删除基础条目 |
| `server_aliases` | GET返回映射，现 UI未直接消费整个映射，行内写 endpoint 消费 | load_config按候选键解析；清映射不等于清基础别名或 entry.name | 保留存量值与解释，不能因 renderer 中 void aliases 就删除底层能力 |
| 检查 `server_id/server_name/target/checked_at/ok/checks[]` | 只读检查回执；checks含 key/label/ok/detail | POST检查已保存ID且body={}，不用未保存草稿。SSH失败则不再执行其余检查；总 ok=all，不等于只测SSH | 保留分项诊断；显示目标/时间/配置关联，GPU不可用不当主机失联 |
| `adminCheckBusy/adminChecks` | 浏览器内按 ID 存在途与结果，非持久配置 | 结果无配置版本失效机制，renderer不显target/checked_at；关闭或编辑不保证清旧结果 | 保留局部加载与历史来源；错误保留、过期标记、迟到响应归属需后续设计/修复 |

**凭据与保存事实（静态源码 E2，不是本片真实凭据试验）：** 表单上方说密码保存至 config/secrets.toml，字段标签却说 user_servers.toml；实际 `add_server/update_server → save_user_overlay → dump_toml` 直接序列化密码到后者，没有自动迁移或加密。显式 entry.password 优先于 secrets 的 alias/ID/host/user@host 查找；把非用户主机编辑成覆盖项时，还可能复制内存中来自 secrets 的旧密码。GET 管理列表不含密码，但新增/编辑返回原始 entry，经 POST 路由 `{"server": entry}` 和 Handler.send_json 直接序列化，存在原始密码公开响应路径，留空编辑也可能返回保留的密码。不能因 GET 不回填或 Provider 已有脱敏而宣称主机链路安全。此问题违反既有 R12/R13，不修改规格降低要求；正式接线前独立修复公开 DTO、凭据保存/兼容与移除语义，不读取或复制用户真实密钥。

`load_user_overlay` 遇坏 TOML 返回空结构；`save_user_overlay` 直接 write_text，无原子替换、锁或版本冲突检查，存在坏配置后覆盖、并行丢更新风险。配置增改、名称、移除和恢复操作都是先保存再同步 refresh_status；前端随后还 loadStatus(true)。因此 HTTP失败可能发生在落盘之后，“保存失败”不能保证原配置没变；新页面需能核对有效配置、区分保存与刷新结果，不能依赖重试掩盖不确定性。

### UX01B 动作、异常与往返契约

| 用户动作与现入口 | 输入/输出与真实作用 | 当前问题与后续必须保证的行为 |
| --- | --- | --- |
| 巡检“管理”→打开/关闭 | 并发 GET /api/admin/servers 与运行维护查询；不是主机只读列表一个请求 | 主机配置与日志/记录清理混排；维护字段交UX01H，不在本片删。关闭直接cancelEdit，没有未保存确认；后续返回巡检保原选择，不能清另一任务草稿 |
| 新增→保存 | POST /api/admin/servers；成功返回server，重读目录/巡检，不创建Job | 必填/条件字段就近反馈；防ID覆盖、区分保存已生效与采样失败。成功文案现被紧随cancelEdit清空；重复提交/不确定响应未真实验 |
| 编辑→保存/取消 | POST /api/admin/servers/{id}/edit；取消仅form.reset，不发保存 | 保留身份、来源/模式与既有高级值；发现/基础/Local都可变成覆盖项但效果不同。迟到回执必须绑定其对象/编辑会话，不清新草稿 |
| 行内保存名称 | POST /api/admin/servers/{id}/alias，body alias；更新名称映射后刷新 | 不应和编辑 name 互相打架；保留轻改名称需求，唯一编辑语义待页面合同确认 |
| 检查连接 | POST /api/admin/servers/{id}/check，body {}；响应分SSH/python3/nvidia-smi/tmux/rsync | 明示检查保存版本，未保存先处理；不是草稿试连。finally重读清掉成功/错误提示，旧checks仍可能留；不能用旧“通过”替新错误 |
| 删除/隐藏→确认或取消 | DELETE /api/admin/servers/{id}；用户项删覆盖，其他写disabled；取消不请求 | 被覆盖发现项删除后可重新发现；基础显式项可能根本没隐藏。影响≠停远程任务；结果须按真实来源解释，不新增假成功 |
| 恢复隐藏项 | POST /api/admin/discovery/restore，body alias | 只移除隐藏键，仍受发现启用/include/exclude限制；不能承诺一定出现、连接或GPU可用 |
| 列表读取失败→重新打开 | GET错误显示原因；关闭/重开重新查询 | 当前恢复入口借窗口开关；后续保就地重试、草稿和返回上下文，不写操作手册补交互 |

### UX01B 实际浏览器观察、边界与交接

2026-11-09，xng/Playwright、Chromium 140.0.7339.16，加载未修改的正式 HTML/CSS/JS，启动预算占位符同 Handler 替换为30。浏览器地址 `http://relaygraph-ux01b.invalid/` 仅用于全量网络拦截的隔离观察，不是可供用户访问的新站点。所有静态/API请求都由本地脚本 fulfill，未知来源阻断、未建模接口报501；主机目录为内存合成数据。未运行后端、读真实配置或访问SSH/GPU/Provider；维护只接空查询，未执行清理。密码日志仅记非空布尔值，不记值。

| 视口/证据 | 实际完成的点击与观察 | 能证明/不能证明 |
| --- | --- | --- |
| 1440，正常及取消 | API空列表→管理→新增；空名称原生拦截；仅名称由API报缺目标；新增后目录/巡检出现；编辑密码空，取消不写；名称保存；取消隐藏不写；合成发现项隐藏→恢复 | 证明旧UI请求/反馈和取消；空响应不证明真实首次配置为空（源码自动Local）。合成源不验证TOML落盘/真实隐藏或连接 |
| 1440，检查与失败 | 改草稿地址仍向已存ID发{}；分项SSH通过/GPU失败；注入check503后提示被finally清空、旧检查仍在；拒绝保存保字段/错误；目录503后重新打开恢复；关窗重开无确认丢草稿 | 证明受控响应下的界面行为；模拟拒绝不证明真实保存失败无落盘。SSH/GPU结果均为fixture，不是真实探测 |
| 1440，迟到响应 | hold主机A保存回执→关闭/重开→编辑B草稿→release旧回执，B草稿被cancelEdit清掉 | 用网络响应延迟注入证明可达竞态，无DOM/业务状态补写；不是自然网络故障实测 |
| 1024/768/390 | 各实际打开管理→编辑→改名称→单次Tab到host_name→取消，均无写请求；有截图 | 仅此往返与局部键盘；未验四宽所有字段/任务/长错误、完整键盘或滚动可达，390仍依赖长弹窗滚动 |

共17项观察、693拦截请求（684 GET/8 POST/1 DELETE），9写仅影响合成目录；pageerror、观察脚本异常、未建模501均0。没有 force点击、改DOM/CSS、关闭门禁或暂停轮询；故障由响应脚本明确注入，正常新增使用现有表单/事件/API请求链，没有手补生产记录。零脚本错误不抵消上述使用问题，不算真实后端验收。主代理实看390编辑和1440迟到回执后的截图，只读监督独立复核脚本/摘要/9写请求及这两图。

本片只修改三份正式文档，旧字段/入口/helper/配置、生产前后端均保留。名称两入口、发现/连接参数和维护混排确有收敛候选，但语义不同或消费者未闭合前不删；不为调查抽新公共组件。证据暂存本地 `/tmp/relaygraph-ux-audit/ux01b/`（dev_work仍不可访问，未修复/重建），脚本、JSON与五图不提交。本片当时交接UX01C，完成情况见下节；全域调查尚未闭合，不能先做只读任务页代替完整任务调查。

### UX01C：直接命令、批量任务与结果入口

对应 R01/R07/R11/R12、G09/G13/G18/G19/G26/G41。本域用户任务是“选对机器与运行条件 → 输入一条命令或展开一批参数 → 明确提交 → 找到这次任务与日志 → 看懂等待/失败并决定停止、修正或重试”。直接操作不要求先建研究项目；从项目节点填来的命令要保留明确来源，但提交一个Job不等于推进完整工作流。本片只调查需求、现有行为及真实缺口，没有画新任务页或实现修复。

权威链路：[index.html](../web/index.html) 的 jobForm/taskPlanForm/任务列表 → [job_form_actions.js](../web/monitoring/job_form_actions.js)、[task_plan_actions.js](../web/monitoring/task_plan_actions.js) → [app.js](../web/core/app.js) 的 submitJob/taskPlanPayload/previewTaskPlan/scheduleTaskPlan/renderJobs/loadJobIntoExecution 与控制动作 → [POST routes](../total_control/http_api/post_routes.py)、[GET routes](../total_control/http_api/get_routes.py)、[DELETE routes](../total_control/http_api/delete_routes.py) → [crud.py](../total_control/state/jobs_pkg/crud.py)、[task_plans.py](../total_control/state/jobs_pkg/task_plans.py)、[execution.py](../total_control/state/jobs_pkg/execution.py)、[scheduler.py](../total_control/state/scheduler.py)。模板展开/命令脚本在 [infra jobs.py](../total_control/infra/shell_pkg/jobs.py)，批量主机路径在 [paths.py](../total_control/state/jobs_pkg/paths.py)，专用预设在 [presets.py](../total_control/state/jobs_pkg/presets.py)/[preset_matrix.py](../total_control/preset_matrix.py)。任务筛选与列表投影复用 [job_state.js](../web/monitoring/job_state.js)/[job_list_markup.js](../web/monitoring/job_list_markup.js)；草稿保存在 [app_runtime.js](../web/core/app_runtime.js) 的浏览器存储逻辑中。

**用户看到的三个入口不能互相替代。** 单命令负责本次输入与提交；批量负责参数展开、明确条件和提交范围；任务列表负责找回Job、查看日志和控制。填回执行只改草稿，复制/重试会新建Job，停止和删除又是两件事。新版要完整保留这些能力，再按任务分区，不能只留只读运行卡片。

### UX01C 输入、默认与保存影响

以下是现有表单全部命名字段及关键无控件参数。默认区分 HTML 初值、浏览器恢复值和API缺省；后两者不能伪称已验证的运行配置。直接与批量输入当前会随input/change保存到localStorage，并非config/后端项目设置；命令中不能鼓励用户填密钥。本片未检查真实浏览器存储内容。

| 字段/用途 | 来源、条件与当前默认 | 校验/联动/保存影响 | 保留或调整决定 |
| --- | --- | --- | --- |
| 单命令 `server_id` | 下拉取当前可见主机，与监控selectedServer联动；无单命令auto选项 | 改主机会重建GPU选项；API缺省local、允许auto、显式主机只验存在。失效选择可能换首项 | 保留明确目标；后续不得静默换机器，不能把任务/巡检/终端选择器当同一语义 |
| 单命令 `gpu_index` | 下拉auto+当前采样GPU，无CPU/none选项 | API识别none/no_gpu/cpu，数字safe_int；填回CPU旧Job会变auto；无GPU主机仍可选auto而等待显卡 | 保留CPU/自动/指定卡的明确选择及有效来源；不沿用填回丢失CPU意图 |
| `cwd` | 工作目录，初值空；手填、项目/旧Job填回 | 空时不cd，非空执行前检查；路径属于目标主机，不能在提交前仅凭文本认定存在 | 保留；不同于批量本机/远程目录，不直接合并清空旧值 |
| `env_name` | 环境名或路径，初值空；两种表单均有 | 空表示不激活指定环境，非空执行前激活失败应退出；不代表环境已安装或自动创建 | 保留条件输入，展示有效环境，不回填假环境名 |
| `command` | 多行文本，初值空；手填/项目节点/旧Job来源 | HTML无required，API trim后非空；自定义shell文本，不在此自动改写；默认Job名取首行前80字符 | 保留完整编辑与阅读，空命令就近拦截；名称不是稳定身份 |
| `min_free_mib` | 单命令空闲显存条件，HTML1024、min0 | JS转Number，API safe_int缺省app配置；用于采样筛选，无原子预留 | 保留单位/范围/来源，CPU时不展示无关阈值，但保留旧草稿 |
| `max_gpu_util` | 单命令/批量最大利用率，HTML10、0–100 | JS数值，API safe_int缺省app配置；仅HTML范围不等于HTTP校验 | 保留GPU条件；不得把满足条件叫资源已锁定 |
| `wait_for_idle` | 单命令checkbox默认true | true入queued；false创建starting并走allow_busy启动，可跳过空闲阈值，auto卡找不到时可回退0；不是只改UI文案 | 保留显式策略及影响说明，后续不默认把取消等待包装为安全立即执行 |
| `workspace_id/workspace_node_id/workspace_node_title` | 单命令隐藏关联；项目运行节点填回时设置 | 提交同时写metadata.workspace_id/node_id/node_title；成功清绑定；浏览器持久化明确跳过三字段。刷新后有命令不代表仍绑定节点 | 保留可见来源/解除关联；项目上下文与独立任务区分，不冒充工作流run/attempt身份 |
| 批量 `template` | HTML默认preset，API默认custom；当前仅preset/custom | 切换重置预览文案，隐藏另一组但FormData仍收所有命名字段；CSS目前令两组都可见 | 保留两种意图；只显示相关输入，避免字段看似都要填 |
| `limit` | 批量任务上限HTML4、min0 | 后端仅preset分支用limit>0截断，0/非正不限；custom分支未应用，不能承诺通用上限 | 保留实际范围说明；未修之前不能在custom声称此值能限制任务数 |
| `datasets` | preset逗号分隔，HTML/API默认dataset_a | 每个非空名称生成20种固定实验，再排序/限额；不验证数据存在/支持，不是通用数据发现 | 保留为专用样例输入，迁为通用模板前验证等价；不假称任意项目可直接用 |
| `command_template` | custom多行，初值空 | API可接受command别名；按每行参数render，缺模板ValueError；当前render缺_TemplateMap而NameError，见下节 | 保留模板能力与错误定位需求；未修不得标custom已可用 |
| `params_text` | custom每行key=value或JSON对象，初值空 | 每行是一条任务，不做笛卡尔积；API另支持params对象列表；空/仅注释生成一行，自动补index/i，JSON坏行报错 | 保留参数表语义、最终条数/命令核对；不能将文本多值误解成自动排列组合 |
| 批量 `server_id/candidate_server_ids` | 页面默认auto；具体候选只含online（GPU采集成功）主机 | auto提交当时online IDs；不包含仅reachable的CPU主机。空候选在find_gpu中意味着不限制候选，不是确定“无候选” | 保留候选范围与过期/空选择反馈，不能显示旧预览而悄换范围 |
| 批量 `gpu_index` | auto跨主机时只有auto，指定主机时加采样卡号 | 后端仅auto或safe_int，传none会退0，不支持直接API的CPU语义；当前没有CPU选项 | 保留现有选择；统一CPU合同另片实现，UI不能自行补已有API不支持的能力 |
| `local_project_dir` | 高级区，本地项目目录，HTML /path/to/project | 存cwd_local，按最终server.mode才选用；不是上传源目录，未自动复制项目 | 保留按运行位置选择的目录含义；占位值不能当已配置事实 |
| `remote_project_dir` | 高级区，HTML /home/{user}/project | 存cwd_remote，执行时替换user/host；空可走API cwd/cwd_remote兼容；不检查传输或主机目录存在 | 保留目标机目录；别与传输目标联动保存 |
| `data_root` | preset数据根，高级区初值空 | preset展开命令时空取 /path/to/datasets；custom无自动替换这项，须显式模板/参数 | 保留条件字段/路径来源，不能默认所有流程必填 |
| `name_template` | 高级区默认“批量任务 {index}” | 作用custom任务名；无独立session_template控件时也用于会话名；preset忽略、用专用名称 | 保留人可读名称；稳定会话身份不应只靠可重复模板名 |
| `profile_command_template` | custom可选、高级区初值空 | 只有profile_first且展开命令非空才建profile；preset有固定smoke命令，不用此输入 | 保留显式前置命令，不能让勾选项无命令却承诺会测量 |
| `max_memory_mib` | 批量显存阈值，HTML0、min0 | preset 0取固定估计；custom优先min_free_mib/max_memory_mib再app缺省，0不是“确定无需显存” | 保留有效阈值/来源；与直接min_free的单位相同但缺省语义不同，不能直接删一个 |
| `profile_safety` | HTML/API1.2、HTML至少1 | 后端max(1,输入)，测得peak乘系数并取整作为训练min_free；不是资源锁/测量可信保证 | 保留需要profile时的高级项；未测到peak必须失败，不能填估计冒充实测 |
| `profile_first` | HTML默认勾选，API缺省false（兼容smoke_first） | preview回显布尔不等实际会建profile；实际依赖闭环有静态阻塞，不能宣称默认链已通过 | 保留有条件前置步骤；默认可用性须独立后端修复/验收 |
| `dry_run` | 无可见输入；预览动作true，调度false | preview只返回items；schedule dry_run=true仍造新ID/Job结构，但不插队列/落盘；bool字符串不严格 | 保留预览/试算/提交三者边界，内部参数不铺默认页面 |
| 其他直接/批量API参数 | name/kind/candidate_server_ids/target_job_ids/profile_key，批量params/session_template/cwd/cwd_local/cwd_remote/profile_min_free_mib等兼容名 | 当前无对应一般编辑控件；消费者含工作流/传输/预设适配，不能因表单不显示而删；target_job_ids当前有双义缺陷 | 保留已有消费者，详情/诊断按需；未来新增入口先核合同，不造通用高级编辑器 |

单命令与批量虽共用调度器、Job列表和日志，**创建路径尚未统一**：普通create_job为queued记录在锁内save、失败撤出内存；批量自己构造两类Job、插入self.jobs后锁外save，失败没有相同回滚。两种POST都没有通用提交幂等键，UI也没有在途禁用；工作流的request_id不能推及这些入口。新页面必须保留明确本次受理结果、未知响应核对和防重复交互；真实幂等/持久化缺口另片修，不能在演示里声称已经解决。

### UX01C 当前阻塞、控制语义与冗余判断

- **custom展开已做实际纯函数复现**：导入未改 `render_task_template('task {index}', {'index':1})` 得到 `NameError: name '_TemplateMap' is not defined`；源码只有此引用，无对应定义/导入。`task_plan_items`在渲染名称时会遇到它。另实际纯调用验证空矩阵→一行、两行参数→两条。没有启动HTTP服务；Handler的POST只捕获RunStoreError/ValueError/JSON错误，本轮合成500封装不能当真实错误码或错误体合同。后续先恢复模板展开、校验缺占位符与最终命令，再验custom正常入口，不给演示注入缺失类以冒充修复。
- **profile循环等待是静态源码闭合，非真实执行验证**：训练先blocked；queued profile的target_job_ids=[train_id]本意为释放目标，但通用job_dependencies_state把它当“前置必须done”。profile等训练、训练等profile，形成闭环。完成分支又未核训练当前状态，可将stopped改queued；profile停止也未见blocked训练的完整终结链。需独立收口前置/后继引用、停止与释放，不能用人工放行或关profile证明默认链正确。本轮profile关闭的preset场景只验证那个显式分支的UI消费。
- **复制、重试和填回不同**：clone清旧提交身份及target_job_ids，但保留kind/profile_key，丢cwd_local/cwd_remote；不重建整批或profile链。原wait_for_idle=false仍保留，可立即start，故“复制入队/重新加入队列”文案不准确。填回只是form草稿，clearJobSourceBinding，不新建；CPU或失效主机/卡的值可能回退，批量运行前cwd尚空时也无法保留两种目录。应提供来源/有效值与明确差异，不能将修复前的行为包装成原样重试。
- **停止回执不证明外部停止**：stop_job发送Ctrl-C/kill但未核最终返回就写stopped，也无统一终态门禁；本轮未操作真实停止。普通CPU脚本仅unset CUDA_VISIBLE_DEVICES，不是禁止用户命令使用GPU；“无需调度GPU”不能宣称强制GPU隔离。
- **采样、资源、目录和环境分开**：GPU选择按最近online快照筛空闲量/利用率，无本服务原子预留；直接取消等待可以跳条件。目录和环境到执行前才检查/激活，不是预览已准备好；每个字段都需有明确失败定位，不能靠操作手册补交互。
- **专用预设是迁移候选，不直接删除**：每数据集20组合、显存估计、train.py/smoke_test_single.py参数及优先级仍硬编码；preset APIs已委托task-plan展开/创建，但不同响应别名/历史记录还有意义。会话名由可重复实验字段生成，无Job唯一后缀，重复批次存在同机tmux重名风险（未真实提交）。未来对照通用模板的命令、阈值、profile、身份和历史读取后才退出专用路径，不先删现有案例。
- **样式重复不等于可删，隐藏失效已经观察**：当前 `.template-fields {display:grid}` 覆盖原生hidden的默认效果；preset/custom两组同时可见，选择意图被冲淡。后续前端片需用作用域明确的显示合同修复并验证切换/草稿/校验；不在本片批量删除CSS或重写表单。预览items数是训练项，不含将追加profile数；摘要“将提交N任务”也不能代表实际总Job数。

### UX01C 动作、输出与页面要求

| 动作/现API | 现有输入与输出 | 后续页面必须保留/纠正 |
| --- | --- | --- |
| 单命令提交 `POST /api/jobs` | 当前表单→公开job回执→刷新status→showLog(回执ID)，不要求预览；原始fetch无该入口专用deadline | 受理不等完成；明确本次ID/状态和日志，防重复、保草稿/错误；刷新/日志失败不能丢受理事实 |
| 批量预览 `POST /api/task-plans/preview` | 当前表单→count/items/阈值/命令，最多显示前24行 | 没核主机/目录/环境，不是就绪门禁。修改字段现不失效，旧请求也无版本检查；后续要能知道预览对应哪份输入 |
| 批量提交 `POST /api/task-plans/schedule` | 重新读当前表单→重新展开→profile_jobs/batch_jobs/jobs，打开首Job日志（可能是profile） | 不要求先预览，没有冻结预览hash；返回批次全部精确引用，不能只看首条就宣称整批成功。旧预览与新提交差异要明确 |
| 专用preset plan/schedule | `/api/presets/plan`、`/schedule`包装task-plan，保experiments/smoke_jobs/train_jobs别名 | 当前页面不再调用这些专用URL；兼容/API消费者未穷尽，不据此立即删除 |
| 点击任务→日志 | GET /api/jobs/{id}/log，tail或offset/chunk；底部输出标签按Job ID | 日志有空、失败、截断/快照与实时来源，不能将无正文当任务失败或完整导出；日志细部与终端交UX01E |
| 填回执行 | 已有Job字段→单命令草稿（传输Job有另一支）→执行页 | 不自动提交，保明确主机/CPU/目录/来源；覆盖草稿要可理解，不悄悄借当前主机替旧目标 |
| 复制/重试 `POST /api/jobs/{id}/copy/retry` | 新Job ID；重试拒活跃态，复制可对现有Job；新记录打开日志 | 不是原attempt恢复。风险/策略与依赖/路径差异要说明，文案不假承诺排队 |
| 停止 `/stop` | 精确Job ID，UI按钮暂禁后重读状态 | 保停止与删记录分离；不能拿本轮合成响应证明外部确实结束 |
| 排队置顶/上移/下移 `/reorder` | direction；waiting含queued/blocked | 后端rank才是排序事实；不与列表“最新优先”偏好混同，失败保恢复操作 |
| 删除/清理 `DELETE /api/jobs/{id}`、`/clear-completed` | 删除先confirm，取消不应请求；批量清done/failed/stopped，服务端保护保留run引用 | 不删除运行中；页面清理统计含受保护项，不等真正删除数，错误/保留原因明确；本片未点击真实/合成删除确认 |
| 查找/筛选/排序 | query查ID/名/命令/错误/主机，server同时匹配requested/实际；状态/类型/日期或队列/耗时；最多100条 | running包含starting，waiting含queued/blocked，失败组含stopped，不能把筛选名称当精确领域状态；无任务/无匹配分开，长名/长错误可读 |
| 刷新、跨区、离开表单 | 浏览器自动保存草稿，三项目关联字段不存；提交成功不清命令 | 不自动重提；草稿/已保存项目/已受理Job分开。独立页面身份、直达/Back与未保存处理在全域合同阶段验证，不称当前已满足 |

### UX01C 实际证据与未验证范围

2026-11-09，xng/Playwright、Chromium 140.0.7339.16，未改正式HTML/CSS/JS；启动预算两个占位按Handler替为30。`http://relaygraph-ux01c.invalid/`仅全量拦截观察地址，不是新站点。全部请求由route.fulfill处理，未知来源阻断，没有真实后端、持久化、SSH、模型或命令；Job受理/控制/日志为内存合成。preview调用从未改源码AST提取的task_plan_items/task_plan_preview/preset_command，提供最小依赖夹具（公开默认配置、现有纯函数，另有本场景未调用的safe_id替身），仅展开文本，不构造状态服务/运行任务；因此只能证明纯展开和UI消费者，不能证明调度成功。

| 证据 | 实际路径与发现 | 验证限度 |
| --- | --- | --- |
| 1440单命令 | 空命令发请求并报API错误；填写目标/卡/目录/环境/命令→合成queued回执→精确日志；拒绝保命令/错误；刷新恢复草稿不重提 | 普通输入/反馈链，不是命令执行、落盘恢复或真正超时核对 |
| 1440在途/复用 | hold提交响应，两个原生点击发两个POST；CPU旧Job填回变auto；搜索无匹配；copy精确旧ID→新ID日志 | 无force/DOM状态写；重复创建/starting回执合成，不证明真实启动次数，复制真实语义另据源码 |
| 1440批量 | preset纯展开4训练项；改limit1仍见旧4项；显式关闭profile后提交→单个合成queued Job/日志；custom展开NameError原样作为合成API错误显示 | 关闭profile是场景边界，不是默认链修复/正常验收；无custom成功、profile运行、整批控制或真实落盘证明；500封装是脚本行为 |
| 1024/768/390 | 各单命令输入/提交→合成queued回执和精确日志；cwd单Tab到env_name；各有截图 | 非完整键盘/长命令/长错误/批量或小屏全表单可用验收。390截图主要为输出区，不能以截图称所有字段清晰可见 |
| 1440定向隐藏检查 | 初始preset→custom→preset三态，hidden=true的字段组仍display:grid且有尺寸，两组同时可见 | 独立只读观察；未修改CSS。preview表格截图含局部横向内容，未验全列键盘/滚动阅读 |

主脚本16项观察、1059请求（1047GET/12POST：8单命令、2预览、1schedule、1copy），pageerror/requestfailed/观察异常/未建模501均0；定向隐藏脚本另3观察/128GET、pageerror0，不混成同一套全流程验收。主代理实看390提交日志与1440预设预览图，只读监督实看390日志、custom错误和隐藏检查图并核脚本/请求。启动脚本曾因/tmp导入路径、AST缺lineno而两次在浏览器前失败，修本地脚本后才运行；保留说明，不是产品修复或业务重试到绿。主脚本没有force点击、停轮询、扩大门禁或手填生产终态。

本片只改三份正式文档，保留所有旧控件、helper、专用preset及API；不抽公共组件或改后端。上述风险与台账同步，独立修复候选先登记。脚本、纯调用结果、请求JSON及七图暂存 `/tmp/relaygraph-ux-audit/ux01c/`（dev_work仍按既有不可访问例外，不修复/重建），不提交。UX01C当时交接 **UX01D：文件与传输需求调查**（本轮调查见下节）；全域调查/页面合同尚未闭合，不提前做新只读任务页，也不宣称前端优化已经交付。

### UX01D：文件浏览、预览和传输的用户任务

对应 R04/R07/R08/R10/R11/R12/R13，关联 G07/G12/G14/G19/G26/G41。用户要做的是“找到正确机器上的文件 → 看内容或加入待传项 → 明确目标和处理冲突 → 提交 → 回看这次任务及结果”。文件操作不要求先创建项目，也不能被只读传输历史卡替代。本片只调查，未改生产界面、后端、配置或真实文件。

必须分清五件事：**源文件的位置、预览用的本机缓存、浏览器下载、rsync传输任务、可交给工作流的验证产物**。它们可互相提供入口，但不共享一个含糊的“完成”。点预览已有缓存/网络副作用，但不等于提交了传输Job；Job受理不等于执行结束，退出0也不等于目标实物已经独立核验。

源码链：[index.html](../web/index.html) `transferForm/filePickerModal/transferConflictModal` → [transfer_surface_actions.js](../web/transfer/transfer_surface_actions.js) 与 [app.js](../web/core/app.js) 的路径、树、预览、冲突、`submitTransfer/loadJobIntoExecution` → [GET路由](../total_control/http_api/get_routes.py)、[POST路由](../total_control/http_api/post_routes.py) → [files.py](../total_control/state/files.py)、[utils.py](../total_control/utils.py)、[transfer.py](../total_control/infra/shell_pkg/transfer.py)；正式任务仍走已有 Job创建/执行/调度与日志，不另建传输队列。下表记录实际字段与消费者，尚不是新布局稿。

### UX01D 输入、来源、条件、保存和处理决定

| 字段或控件 | 用途、来源和必需条件 | 当前默认、校验 | 联动、保存影响与处理决定 |
| --- | --- | --- | --- |
| `transferSourceServerSelect` | 来源主机；独立于监控选中主机，选项来自可见目录；无name，不在FormData中 | 首次取现值/首个可见项；失效项可退首项；不限制必须online | 切机保存前机路径、恢复新机路径，清源树/前进栈，保留多源集合；保留独立host身份，未知不能静默改机 |
| `source` / `transferSourceInput` | 手输路径或浏览选择；无多源集合时才成为提交源 | HTML required；路径按主机记忆；尾`/`会被视为目录；后端拒空/敏感路径/换行/危险开头和未配置远端等 | blur解析endpoint，匹配到主机才切select，却无论匹配与否都剥前缀；已选集合优先仍被required约束。保留手输/浏览，取消额外必填与歧义须另片，不直接合并成无host文本 |
| `state.transfer.sources[]` / 待传源项 | 树/选择器显式加入，支持文件和目录；`serverId/serverName/path/isDir/value/key`；不是额外命名表单字段 | 初始[]；key为host+去尾斜杠路径+文件/目录，实际加载的比较保留大小写；同key不重复加 | 有集合即忽略source输入；选择器加入即时生效，关窗不回滚；成功受理清集合，刷新不恢复。保留可见清单/逐项移除/清空，设计需明确单源与集合的唯一提交依据 |
| `transferTargetServerSelect` | 目标主机；独立于源主机；无name | 首次现值/监控选中/首项，之后保有效值 | 切机独立恢复目标路径、清目标树/导航，不改源集合；保留，不用全局当前主机替代 |
| `target` / `transferTargetInput` | 目标位置，手填或选目录；提交必需 | HTML required；选择目录追加`/`，手输未必是目录；后端target原样交rsync | blur同样解析前缀；路径记忆与源分桶。保留；“复制到目录”和“单文件另名”须准确表达，不能把现目标总叫目录 |
| `exclude` / `transferExcludeInput`、ignore chips | 用户补充排除规则；手输逗号/换行分隔，或点源树忽略 | 初始空；trim/去重；目录模式与相对路径由现helper生成；后端追加固定敏感排除项，不能由UI取消 | chips与单输入互相同步；input/change存浏览器，不写项目/主机。保留一个编辑事实；任意多源共享规则的作用范围需明确，不声称已预览实际排除文件 |
| `size_only` | 快速比较选项，不是已核验内容 | HTML/API默认true；checksum勾选时实际优先checksum；现可两项同时勾 | 浏览器偏好；“全部覆盖”仍携带该值，同尺寸差异可能跳过。保留可理解的比较策略，覆盖语义与选项互斥/提示另片收口 |
| `resume_partial` | partial/append-verify续传选项 | HTML/API默认true；不是失败后的自动重试/回滚 | 浏览器偏好；保留，注明适用边界，不冒称任意残留均可靠恢复 |
| `checksum` | rsync比较文件内容；不是独立传后验收 | HTML/API默认false；开启优先于size_only | 浏览器偏好；保留选项，但“严格校验内容”不能被解释成已有ArtifactRecord/目标哈希回执 |
| `filePickerPathInput`、roots/entries | 临时浏览路径、根入口和文件条目；来源browse API | 默认源/目标当前浏览位置；roots、parent、entries、selected、truncated均来自API；目标请求dirs_only=1 | 打开/Enter/根/目录/上级/返回只导航；源“加入”立即改集合，目标“选择”填回并关窗加载树。保留快捷浏览/明确选择，不让进目录等于提交 |
| favorites / 路径记忆 | 快速重访，手动收藏/输入变化；每主机路径身份 | 收藏最多16项，空路径不可收藏；收藏按host分组、路径记忆再分source/target | localStorage，不是共享主机配置或存在性验证；清树清相应输入并记忆空值，不清多源。保留快捷性，跨入口读同存储，不造第二套收藏 |
| `transfer_spec.sources` | API接字典或字符串；字典以value或path执行，path用于冲突关联，is_dir控制目录 | UI目录value、后端目录normalizer均去源尾斜杠，意图复制目录本身；不是“只拷内容”开关 | UI传server_id，但后端执行按endpoint文本匹配配置主机，未以该ID绑定。保留字段/旧消费者，严格host+path需后续共享适配器修复，不能仅换标签称完成 |
| `target_server_id`、`skip_sources[]` | UI记录目标身份和用户跳过决策；内部字段，不常驻编辑 | skip初始[]；按源path/value字符串排除整个源，非按host+冲突文件；target ID不参与后端路由 | 历史“填回执行”使用这些元数据；跨host同path可能一起跳过。保留兼容读取，修复前不能伪造精确逐文件策略 |
| `options.ignore_existing` | API可接受的跳过已存在策略；当前无独立checkbox | 默认false；不同于UI“跳过重复”的skip_sources | 当前UI只在内部transferOptions传递，不把它冒充已有产品按钮；后续先定文件/目录冲突合同再选实现，不能静默替换 |
| Job外壳 / `kind=transfer` | 当前UI始终从已配置Local启动rsync；CPU none、wait_for_idle=false、cwd/env空、min0/max100 | 缺Local直接报错；远→远明确拒绝；直接Job执行逻辑可立即starting，不等等待式队列 | UI命令是显示/请求文本，后端创建及执行均重建实际命令；API未强制外壳Local，若传SSH外壳，无前缀路径会在那里执行，预检却按服务本机查。此为静态身份缺口，须后端收口，未实跑；保留一个Job生命周期。本片合成queued只核回执消费者，不能据此推导真实调度策略 |

输出也要各归其位，不把内部缓存地址当源文件地址，不把没有检查当没有冲突：

| 现有API输出 | 页面消费者与保存含义 | 限制与保留决定 |
| --- | --- | --- |
| browse的`roots/path/selected/parent/entries/truncated`，条目`name/path/is_dir/size/size_text/mtime` | 选择器和内联树；selected用于文件与目录定位，parent导航，truncated表示列表不完整 | 保留类型/主机上下文/截断反馈；条目大小时间不是传后核验，不能凭名称猜类型或把截断当无更多文件 |
| read的`path/server_id/text/encoding/truncated` | 文本回退显示，读取限额与来源独立于缓存 | 只读正文，不产生download URL；远程来源不因cached=false变本机，不能假称已缓存 |
| fetch的`cache_id/cached/created_at/preview_kind/mime_type/name/path/server_id/size/size_text/mtime`及文本字段、`preview_url/download_url/inline_supported/local_path` | 同一预览投影决定正文类型、打开/下载按钮；路径仍区分原始来源和本机缓存 | local_path暴露本机文件/缓存物理路径，后续公开DTO收口（G19）；URL依赖内存索引不算持久产物；未支持类型仍可明确保存，不强行文本展示 |
| conflicts的`checked/conflicts[]`，每项`source_path/source_value/is_dir/destination/name` | 冲突弹窗与按path的决策；checked=false可表示输入不足未检查 | 现UI只看conflicts数组，不检查checked；后续未检查必须与无冲突分开，不默认放行。后端无host版本/内部文件清单，不能承诺精确文件级覆盖 |
| `/api/jobs`的`job`、status中同ID Job、log的`job_id/log/exists/mode` | 受理回执、本次输出标签和最新传输列表；状态权威仍是Job，日志只作输出/进度依据 | 沿UX01C同一消费者；日志读取失败不推翻已受理事实，不把模拟queued或缓存百分比补成生产终态 |

### UX01D 动作、返回和异常的页面合同

| 当前入口/动作 | 当前行为与实际边界 | 后续页面要求与本片决定 |
| --- | --- | --- |
| 源/目标“浏览”“查看” | 一个弹窗选择器，另有内联双树；树上下级/前进/展开；条目可加入/忽略/快览 | 保留找文件、比较目标和快速选择能力；重叠候选是两套常驻浏览布局及大空框，不直接删定位/多选动作。全域调查后再定一个常规选择入口和按需浏览 |
| 源行加入/取消、集合移除/清空 | 加入不提交；集合优先；清树不清集合；关闭选择器不回滚 | 页面要让人准确知道将传哪些项。浏览路径与待传集合分别表达；不要先要求记住哪个隐藏字段生效。选错后能局部撤销 |
| 文件预览/关闭/打开/下载 | POST fetch为远端下载缓存、本机注册原文件，文本失败可GET read回退；两预览表面共用state.filePreview；打开新标签/下载缓存URL，非Job | 保留一份预览事实；源位置与缓存位置分开，远程文本回退也不能叫“当前本机文件/已缓存”。关闭/切机后拒旧响应；长文本可读，二进制/截断/不可预览有反馈，不把路径表单变阅读器 |
| GET browse/read、POST fetch身份与限额 | 默认空ID或未知ID均可能走本机；browse max300（钳10–1000），read/fetch文本限131072（read钳1–2000000） | G12/G19静态缺口：未知必须明确错误，不能拿本机同名文件证明远端；传输路径原始检查不等resolve后安全。浏览本机允许根/resolve校验不能泛化为传输也已具备 |
| 远程预览缓存 | 先完整rsync到缓存再判目录/读限长；fetch显式传下载预算max(30, remote_timeout_seconds+30)，不是容量上限；local_path直接回传；缓存索引在内存 | G07/G19静态风险：点快览可能拉大文件/目录；需先stat与大小/类型控制，公开缓存不暴露内部路径。缓存清理/过期链接与持久产物分开；维护具体参数留UX01H调查 |
| 加入传输任务/冲突预检 | POST conflicts后才能在UI继续；仅顶层目标存在检查，忽略目录内部、排除项和比较选项；远端test-e非零都当不存在 | 预检失败、未知和无冲突必须三种反馈；检查只作提示，不能声称提交绑定覆盖门禁或真正rsync dry-run。已有API可直接提交绕开预检，后续后端补事实边界 |
| 冲突关闭/全部覆盖/跳过重复/逐份确认 | 关闭取消无Job；全部覆盖仍size-only；跳过整个冲突源，可能整目录；逐份原生confirm确定覆盖、取消跳过，无另存或取消整批选择 | 保留用户决策但纠正文案/策略。应明示影响文件或目录范围，提供整次取消；不编造重命名和文件级预览；空源不提交。跨host冲突身份须完整 |
| 预检/确认期间继续编辑 | pending捕获sources/target/excludes/options但最后又读live checkbox和目标ID；无请求归属/冻结合同 | 静态风险：回执与确认可能混配置；后续确认快照需可对照、改动后重检/失效。与UX01C共用真实请求边界，不能另造前端任务状态机 |
| 提交受理→本次日志/进度 | 成功清集合、存选项、刷新status及进度、showLog精确Job；在途无通用幂等/防重；失败保输入不等没有外部副作用 | 本次回执/跳日志必须直达；不把读日志失败归为提交失败并诱导重提。取消沿原Job stop，未核外部终态前不能称停止完成 |
| 传输列表/历史填回/重试 | 最新20条transfer Job，点卡读Job日志；活跃项取消；填回从metadata恢复集合/目标/排除/3选项，不恢复skip决策；Job copy/retry沿现入口 | 保留本次与历史检索/复用；填回是新草稿，重提须重新核目标/冲突；缺元数据/未知主机不退首项悄悄执行。UI进度不是第二条执行主路径 |
| 百分比/执行完成/交付 | 取日志最后百分比，done强100%；多个rsync会各自重新计数；scheduler只凭tmux消失后日志exit_code判done，无目标stat/hash/ArtifactRecord | 明确“命令执行完成/目标未独立核验”，不能把100%叫交付完整或供下游直接消费。多源是串行非原子，后源失败前源可能已复制；set-e还可跳过共用exit marker，失败不代表未复制 |
| 空/不可达/长内容/刷新与离开 | 空目录与浏览错误已有不同反馈；收藏/路径/选项存浏览器，集合/树/预览/冲突pending内存 | 保留空状态、错误原因/原位置重试。确定后续草稿保存与离开提示，刷新不能无提示换提交来源。长路径/错误/日志不得仅靠title；一次主滚动，预览正文可局部滚动，浏览器Back/跨页返回待后片验证 |

后端现有本机↔远端/本机→本机、文件浏览/读取/缓存、敏感排除、SSH端口及`-F ssh_config_path`、密码runtime命令/公开display分离应保留；不是用新模拟补缺。前端说明命令与后端实际生成、app fallback与独立helper为冗余候选，先追消费者和缺helper行为，再决定保留或退出；不能删后端安全参数，不能按相同标签删除两种不同副作用入口。不引入文件管理/调度平台，当前需要先统一现有host身份、提交与证据合同。

### UX01D 浏览器证据、过程和交接

2026-11-09，xng/Playwright + Chromium140.0.7339.16，正式web未修改，HTML两预算占位按Handler替30；`http://relaygraph-ux01d.invalid/`仅隔离观察地址。目录、缓存响应、冲突和Job回执/日志均合成，所有页面请求拦截，未启动服务、读用户配置/源文件、执行SSH/rsync/Provider或写生产终态。合成Local用于满足产品已有的本机执行前提；不是补一个真实主机配置。预览夹具给Local源返回cached=true，仅核缓存投影/按钮；真实Local fetch注册原文件且cached=false，本轮没有证明其缓存复制。

| 实际检查 | 观察到的结果 | 不能推导的能力 |
| --- | --- | --- |
| 1440浏览→加入→关闭→提交→精确日志 | 选择器关闭仍有集合；清source后required阻止；填另一源路径提交仍用集合内report.txt；收到合成queued及本次ID日志 | 不是真实rsync、等待入队、目标文件存在/一致性、持久受理或真实恢复 |
| 1440冲突/错误 | 关闭不建Job；全部覆盖请求size_only=true；单冲突跳过无源不建空Job；冲突503保稿不提交；重填切机后远→远被拒 | 真实远端冲突检查、覆盖实效、逐文件冲突/逐份confirm、取消外部进程、在途防重均未验 |
| 1440身份/预览 | 未知endpoint失焦去prefix保留Local；fetch503文本read回退仍称已缓存；hold/release后关闭预览又显示旧结果；目录503和空目录有不同反馈 | 未知host后端回退为静态发现；预览迟到是明确延迟注入；未证明自然网络故障/大文件/缓存清理和安全漏洞可利用性 |
| 1440点击下载 | 真实按钮触发Playwright download事件，但save_as canceled；缓存请求未进入route记录，正文未取得 | **下载保存未通过**，原因未定位，不能把事件当端到端下载成功，也不能归因生产后端；打开新标签未验 |
| 1024/768/390 | 各浏览加入→关闭→目标字段Tab到targetBrowseBtn；刷新后集合0项，源路径恢复/demo/；各截图 | 只有这些操作/单Tab，不是四宽提交/冲突/全键盘/长内容或完整前后退。390截图只见顶栏与目标一段，未呈现所有字段，不算小屏可用性通过 |

最终脚本17观察/1567拦截请求（1557GET，10POST=5冲突+2Job+3fetch），pageerror/requestfailed/未捕获观察异常/未建模501均0；下载失败单列，不能用这些0抹平。夹具browse未提供真实schema的selected，回执图源树的无名FILE不能归因产品；夹具dirs_only只识别true而前端发1，本轮全是source browse未触发此分支，**目标目录浏览/选择未验**。首次脚本换源主机后未重填被产品清空的路径，required阻止导致断言失败，原记录保留；第二轮在download保存取消处退出，原记录保留；最终只修本地场景准备与显式记录该失败，未降低业务断言、force点击、停轮询或改DOM/门禁。模拟正常路径没有关检查或手补状态，仍不能证明真实传输已发生。

主代理实看390选择与1440迟到预览图：桌面常驻多树/大空框挤压路径；小屏截图仅一段，不能据点击完成称布局合理。脚本、JSON、两次失败记录、截图暂 `/tmp/relaygraph-ux-audit/ux01d/`，沿dev_work不可访问例外，不修复/重建且不提交。保留全部旧页面/动作/helper，未新增公共组件；问题及逐文件消费者同步第二部分。独立只读监督复核范围与证据后才提交三正式docs。UX01D当时交接 **UX01E：终端/tmux与现活动需求调查**（本轮见下节），仍不开始生产布局或后端修复。

### UX01E：终端、tmux和当前活动的用户任务

对应R01/R07/R11/R12/R13、G19/G26/G41及本片新增G42。开片原列G18是沿上一片任务消费者线索，G18仍归preset，不把终端缺陷并入其中。主任务是“在明确机器上排错/输入 → 看准确输出 → 知道关闭或中断会影响什么 → 回到原任务”。本片只调查；保留已有终端输入、tmux查看和Job日志/停止能力，不将它们缩成只读活动统计。

有四种对象，必须在入口和动作中区分：

| 对象 | 当前事实与来源 | 可以做什么，不能暗示什么 |
| --- | --- | --- |
| 输出标签 | 当前浏览器内存的阅读位置，可引用Job、tmux、进程或终端 | 切换/收起/搜索/保存当前文本；不是持久活动事件，也不是一个任务 |
| 页面终端 | 服务进程内存中的WebTerminal PTY，运行本机登录shell或SSH客户端 | 单行输入、读取、发信号、请求关闭；不是tmux、工作流或完整终端模拟器 |
| tmux会话 | 当前所选主机用户的会话列表，不限本服务创建 | 当前UI只列表/抓取pane快照，无专门attach、输入、kill入口；看到输出不等已经进入交互会话 |
| Job | 持久任务记录，自己的主机、session、日志和执行状态 | 看日志/停止沿原Job入口；浏览器终端是否还活着，不能决定Job是否完成/停止 |

源码链：[index.html](../web/index.html) activity/tmux/terminal及底部输出区 → [output_terminal_actions.js](../web/monitoring/output_terminal_actions.js)、[app.js](../web/core/app.js) `openTerminal/pollTerminalOutput/closeCurrentTerminal/closeOutputTab/loadTmuxSessions/refreshActiveOutput` → [GET](../total_control/http_api/get_routes.py)/[POST](../total_control/http_api/post_routes.py)/[DELETE](../total_control/http_api/delete_routes.py) → [terminals.py](../total_control/state/terminals.py)、[web_terminal.py](../total_control/infra/web_terminal.py)、[execution.py](../total_control/state/jobs_pkg/execution.py)、[tmux.py](../total_control/infra/shell_pkg/tmux.py)。本功能使用HTTP轮询，不是WebSocket终端；工作台SSE不能被当成终端重连协议。

### UX01E 字段、输入与输出归属

以下控件均按当前实际ID调查；terminalInput没有name，不能只扫描FormData就说字段已完整。除注明localStorage者，其余选择、文本和会话引用在浏览器内存，不写项目/运行快照。

| 字段/控件 | 用途、来源、必需条件与默认 | 联动、校验、保存影响与处理决定 |
| --- | --- | --- |
| `terminalServerSelect` | 新终端的目标主机，来自可见目录；当前有效值优先，再取选中/首项 | change经ServerSelectionActions已改监控selectedServer/存ID、重置GPU为auto并读tmux，不只改变创建草稿；可达无GPU仍可用，不可达UI拒开，API另严格查ID。保留独立创建意图与已开会话归属，隐式跨域联动后续需收口 |
| `terminalBtn` / `server_id` | 明确创建一个PTY；POST sessions仅传主机，不传cwd/env/命令/尺寸 | 无在途防重/幂等；每次创建新session。打开后改监控selectedServer并存其ID，但激活旧终端tab本身没有serverId字段，不能据此称所有主机选择已同步 |
| `terminalInput` / `data` | 单行输入，Enter或发送按钮提交；初始空，空串不发，发送追加换行 | 无逐键/方向键/全屏应用能力保证；先清输入再await，拒绝时丢输入且无局部反馈。保留输入能力，后续补发送失败/目标显示；不把输入自动存浏览器/项目，避免留敏感命令 |
| `terminalCtrlCBtn` / `signal` | 当前session发送signal=2；API默认SIGINT，safe_int转换 | 只对alive终端发送；后端os.kill直接PTY子PID，不是写PTY控制字符/前台进程组或远端控制协议。保留准确操作，不能显示“任务已中断” |
| `terminalCloseBtn` / session ID | 当前终端显式DELETE；普通tab×/关闭当前/列表关闭也可能走同一删除 | 无确认；无论失败都清引用，专门按钮仍称已关闭；关闭其他会话时晚到回执可清新选择。保留请求关闭，但结束请求/确认/失败必须分开（G42） |
| `state.terminal`、`terminals[id]` | 当前活动指针及已开PTY本页投影，含id/cursor/alive/serverId/serverName/text/pollTimer | 非服务端会话目录；页面刷新即丢，切终端指针影响读/写/关闭。后续所有异步响应绑定请求时session，不让晚到结果跨会话 |
| `cursor`、`output/alive/exit_code` | GET output默认cursor0；后端回session_id、输出、当前buffer长度、存活和退出码 | 前端不校验返回session_id且忽略exit_code；只更新当前对象。cursor是字节范围而非字符/时间，现非绝对偏移，1MB后会饱和。保留有界读取，后续补绝对游标/截断/归属，不拿有限文本当完整历史 |
| `id/server_id/server_name/cursor/alive/output` 创建回执 | 后端新session ID，初始cursor0/output空，alive固定true | 不是SSH握手成功或shell就绪；保留受理与连接反馈的区别，不新增模拟“已连”状态作为事实 |
| `state.selectedServer` / tmux目标 | 侧栏选中主机，用于list；每个tmux输出tab另有serverId+sessionName | 选主机/GPU可触发list；list响应无主机/请求门禁，迟到可能显示旧机器列表，再点会按当前机器抓取。保留完整身份，不以sessionName独自关联Job |
| `sessions[].name/created/windows/attached` | GET tmux返回；UI显示name、windows和attached，created未展示 | 后端attached仅字符串1为true，多client计数>1会错；部分“failed to connect”文本被当空。保留空/失败/连接数量含义，不从空列表推出无后台任务 |
| `session`、`lines`与`server_id/session/log` | capture请求当前session；UI固定lines50000，HTTP默认10000，service默认2000，最终钳50–50000 | 无window/pane选择、增量游标或全历史保证；GET还会先resize窗口/pane160×80，不能称纯读取。保留快照阅读，副作用/尺寸策略另片核对 |
| `outputTabs` / `activeOutputKey` | 四类引用：job:id、tmux:host:session、process:host:pid、terminal:id | 同key复用，标签不是新任务；Job读取有精确tab检查，不能笼统说全部输出都无归属。保留定位与切换，现不提供地址直达或刷新恢复 |
| `terminalSessionList/Meta`、`terminalActivitySnapshot` | 本页打开标签列表/计数/当前输出及字符长度；不是服务器会话清单 | 与底部tabs重复投影，未知terminal投影也可称运行中；Job tab没serverId时摘要主机可为“-”。候选收敛计数大卡/重复标题，保留直接找回输出与关闭入口，不造全局事件目录 |
| `logSearchInput/Count/PrevBtn/NextBtn` | 当前加载文本搜索，不区分大小写；query初始空或恢复浏览器偏好，命中索引仅内存 | query经localStorage保存、跨标签共用；不是查服务全日志。保留搜索/命中导航；选中/正文更新不应错归另一tab，搜索范围要准确 |
| `logAutoRefresh` | 默认勾选；每3秒只对可见输出的Job/tmux refresh | 不控制terminal1秒轮询；终端只在当前激活alive时轮询，收起面板仍会轮询；目前无统一用户含义。保留实时阅读需求，控件按适用对象显示，勿把取消自动当停任务 |
| `logFollow`、`logFollowHint` | 默认勾选；接近底部时跟随，离开底部保阅读位置，手动刷新forceBottom | 不暂停采集或执行；普通激活终端也forceBottom。保留阅读控制，不让后台刷新抢读长内容；全键盘/大输出交互本片未验 |
| `logRefreshBtn` | Job/tmux显式重读；terminal/process在refreshActiveOutput直接返回 | 不能把同一“刷新”按钮当终端已有重连；重新激活terminal tab会触发单次read，合成503后恢复已观察。保留明确且有效的每对象恢复动作 |
| `logClearBtn` / 收起 | 隐藏输出pane和终端输入控件，保留tab及其对象 | 不DELETE、不stop；重选tab恢复阅读。保留轻量收起，与“关闭/结束”清晰区分 |
| `outputCloseActiveBtn/AllBtn`、tab×/列表关闭 | 阅读tab直接移除；终端tab还DELETE，closeAll批量DELETE但忽略错误后宣称成功 | 不能用统一“关闭标签”掩盖PTY副作用；需要说明作用对象、失败可重查，危险的结束与阅读关闭分别设计；不凭统一标签直接复用不等价动作 |
| `logDownloadBtn` | 创建Blob保存当前activeOutput.content或已显示文本，文件名按title过滤 | 当前终端内容前端超过1,000,000字符裁至900,000，后端又限1MB字节；tmux仅有限快照。保留保存当前输出，不能称完整日志或持久运行导出 |
| `activityTabs`与本页导航 | tasks/tmux/terminal，旧output映射terminal；产品/子页选择存localStorage | 切页不是断开，打开输出不总先切activity；保留原Job/run回程，不用页签同名冒充独立页面身份。跨页/Back精确恢复留后续页面合同验证 |

下面的`{id}`是终端session ID，tmux的`{host}`是服务器ID，两者不能互换。

| method与现有路径 | 请求字段/默认 → 响应 | 当前消费者与副作用边界 |
| --- | --- | --- |
| POST `/api/terminal/open`、POST `/api/terminal/sessions` | body `server_id`默认空、必须匹配配置 → `id/server_id/server_name/cursor=0/alive=true/output=""` | 两个入口都新建PTY；当前web只用sessions，未使用open别名。alive固定初始值不是认证完成；无幂等/恢复参数 |
| GET `/api/terminal/sessions/{id}/output` | query `cursor=0`，safe_int → `session_id/output/cursor/alive/exit_code` | 当前terminal每秒/激活时读；有buffer访问时间更新，不启动新命令；现UI不核session_id、不消费exit_code |
| POST `/api/terminal/sessions/{id}/input` | body `data`默认空、转字符串 → `ok:true` | 单行输入追加换行后调用，后端写PTY；ok只确认写入调用，不是命令执行结束 |
| POST `/api/terminal/sessions/{id}/signal` | body `signal`默认SIGINT=2，safe_int → `ok:true` | Ctrl+C按钮；os.kill直接PTY子PID，非远端任务已中断确认 |
| DELETE `/api/terminal/sessions/{id}` | session ID → `ok:true` | 各终端关闭入口；服务先pop映射，再EOF/kill直接PID；不等远端进程树停止或Job stopped |
| GET `/api/servers/{host}/tmux` | host必需 → `server_id/sessions[]`，项含`name/created/windows/attached` | 选机/刷新读；未知host错误，部分连接错误文字被折为空；不是持久活动目录 |
| GET `/api/servers/{host}/tmux/{session}/capture` | session非空；query `lines`HTTP默认10000、钳50–50000（UI50000） → `server_id/session/log` | tmux tab读快照，GET先resize窗口/pane；无attach/input/kill、pane选择或完整历史保证 |

创建别名不能因为名字像旧就直接删，先核外部调用；CLI本身不调用这两个HTTP入口。input/signal/DELETE成功只回`ok:true`，不是远端完成确认；未知主机/会话ValueError由Handler封为400。后续缺resize、会话列表、恢复/重连、容量/清理合同独立登记，不给模拟原型虚构API；CLI [terminal.py](../total_control/terminal.py) 是真实TTY交互入口，不是本页的备用实现，本片未迁移或删除。

### UX01E 状态、过程与冗余判断

- **选择与回执归属**：terminal读/关闭及tmux list/capture都要保请求时身份。当前终端1秒poll无inflight锁，响应延迟还可能同游标并发、重复追加/游标倒退（静态，未逐项跑并发反证）；Job日志已有按tab检查/增量合并，不另起第二个输出或状态内核。
- **连接与退出**：当前output读取失败就alive=false并停自动轮询，UI称已退出；这不能证明shell退出。创建固定alive=true也不证明连接成功。后续须按已有事实区分“创建受理、正在连接/可读、读取失败、观察到退出”，缺少服务端事实处登记能力缺口，不能前端猜最终状态。
- **关闭与中断**：收起只影响阅读；关Job/tmux/进程tab不结束对象；关terminal tab会请求EOF+kill直接子PID。Ctrl+C接口只发signal2；Job.stop另走关联session的send-keys/kill，再直接写stopped且未核外部最终结果。不同对象不能共用一个“成功停止”含义。服务端terminal先pop映射再close，失败可失去查询依据，服务退出也无遍历终端关闭；实际进程去留未验。
- **会话保留与证据**：后端内存表不持久化、无列表/死亡或闲置回收、无并发上限；created_at/last_access未公开且后者没有清理消费者。刷新浏览器没发DELETE却丢本页引用，服务重启也失去表；不能据此判断tmux/Job或远端子进程是否仍活着。输出有限且可能饱和，不能承诺恢复与全历史下载。
- **终端能力边界**：PTY固定160×80、TERM=dumb，前端stripAnsi后放pre，单行命令输入，不是逐键终端。远程ssh_command_base使用端口/认证但不消费ssh_config_path，区别于rsync的-F；密码/确认提示按chunk匹配且最多一次。UTF-8跨块、MFA、输出回显敏感内容等仍为静态风险，未拿个人凭据试验。
- **保留与收敛**：终端输入/tmux查看/Job日志和动作必须留；顶部tabs与活动列表的查找可服务不同任务，先明确消费者再收敛重复大统计、标题和常驻成功块。新布局应给输入/当前连接和主机足够空间、保持一个主内容滚动区，输出正文可局部滚动，不靠浮层遮挡或藏关键操作换简洁。当前不引入终端库或新平台；若未来需真正逐键终端，再独立核成熟方案/协议和退出成本，不把换库与本轮调查混做。

### UX01E 实际证据与未验证边界

2026-11-09，xng/Playwright、Chromium140.0.7339.16，正式web未改，HTML预算占位按Handler替30；隔离地址`http://relaygraph-ux01e.invalid/`不是新站点。全量拦截请求，terminal/tmux/Job日志均合成，没有真实服务、PTY、shell、SSH、tmux、命令或私密配置。输入回显为夹具“DEMO RECEIVED”，signal回显也仅请求标记，不能当命令执行/中断证明。

| 实际路径 | 结果和发现 | 证明限度 |
| --- | --- | --- |
| 1440正常输入/阅读 | 空标签、离线原门禁拒创建；可达无GPU主机创建合成session→读输出→Enter发送精确ID和换行→signal2→搜索/下一命中→Blob保存当前合成正文；收起/重开不DELETE；专门关闭收到合成回执并移标签 | 不证明本机/远端认证、PTY或信号/进程结束；Blob下载通过仅限本轮当前文本，不沿用UX01D未通过的缓存下载 |
| 1440tmux | 点会话抓快照，关闭输出tab没有写请求 | 不证明实际tmux、GET resize、完整历史、主机迟到list或真实外部kill；tmux空/错误仅静态合同，未动态验 |
| 1440错误/刷新 | 创建503有消息不加tab；input503清输入且产生未处理Promise异常；DELETE503仍称已关闭并遗忘tab，合成服务仍alive；read503误称退出/停止轮询，重选tab读取后可恢复；刷新丢tab且无DELETE | 错误明确注入，不是自然网络故障；刷新后只合成对象存活，真实PTY/远端去留未验；无全套signal/closeAll错误验收 |
| 1440迟到三场景 | hold/release输出A混入激活B；关闭A的回执清B当前指针，B标签仍在/服务alive但输入不发；tmux旧capture覆盖当前terminal标题/正文 | 经过原按钮创建/切换和网络延迟注入，没有DOM/业务状态补写；不代表所有并发、被动关tab或浏览器断开均已验 |
| 1024/768 | 各新建合成终端、输入Enter、单Tab到发送按钮，有截图 | 未验四宽全部关闭/错误/长输出/键盘导航、自动跟随与布局全可读 |
| 390 | 正常点击“新终端标签”被terminalActivitySnapshot统计区挡住，5秒超时，截图保存 | **该宽度创建未通过**；未force点击/隐藏统计/换输入方式绕过，不把其他宽通过称四宽可用 |
| 原始缓冲方法纯验证 | AST提取未改WebTerminal._read_loop/snapshot，1,000,000字节后注入NEW，真实裁剪后尾仍有NEW，但旧cursor=新cursor=1,000,000，delta空 | os/select均最小合成依赖，无构造函数、线程、PTY/服务；只证明原方法游标/裁剪错误，不证明实际长进程、编码/信号或重启行为 |

主浏览器20项观察/1337请求（1318GET、16POST=11创建+4input+1signal、3DELETE），requestfailed/501均0；**pageerror1为刻意input503的未处理拒绝，观察末尾失败1为390真实遮挡超时**，不能记全绿。首次脚本在wait_for_function调用参数写法报TypeError，原脚本记录保留；只修本地arg关键字后运行，未改产品、不停轮询、不force、不补生产终态。第二次执行到390失败后保留，没有重复跑到绿；可达无GPU正常路径未关闭检查。主代理实看390失败与1440跨会话输出图，其他截图/长内容不冒称全人工已看。

本地脚本、纯方法结果、请求JSON、Blob下载、两轮日志与七图暂存 `/tmp/relaygraph-ux-audit/ux01e/`，沿dev_work不可访问例外不修复/重建、不提交。第二部分新增G42并更新相关问题/逐文件消费者，旧页面、helper、API/CLI全部保留；独立只读监督复核后只提交三正式docs。全产品需求仍未闭合，不进入生产改版。原UX01F全局能力域较大，当时下一片拆为UX01F1模型连接与路由诊断调查（现见后文限定完成），Search/Agent工具/模板分别留后续调查，不能同轮批量做完。

### UX01F1：模型连接、测试对象与有效路由

对应R03/R09/R12/R13、G09/G19/G21/G26/G27/G40/G41及新增[G43](current-audit.md#g43)。这一片要回答：我在哪里填一次连接信息；修改的是草稿还是已生效配置；测试究竟用了哪个地址和模型；哪些项目会受影响。只调查LLM连接与路由消费者，Search/Agent工具编辑/模板迁移分别留后片，不改生产代码或新增布局。

源码链：[配置中心AI渲染](../web/config-center/config_center_ai_renderer.js)、[事件](../web/config-center/config_center_provider_actions.js)、[Profile helper](../web/config-center/config_center_provider_profiles.js) → [app.js](../web/core/app.js) 的load/save/updateSelectedProviderProfile与test/models → [registry.py](../total_control/state/registry.py):321–606 → [字段/脱敏](../total_control/state/registry_pkg/provider_profiles.py)、[路由诊断](../total_control/state/registry_pkg/provider_route_health.py)、[LLMClient](../total_control/llm_client.py)。工作台仍有[第二编辑入口](../web/workspace/workspace_model_provider_actions.js)，共用同一state与保存核，不是第二套本地连接目录。

### UX01F1 字段、来源与保存影响

下表既列实际字段，也标出正式页面合同应保留或改变的语义；不是本轮已经实现的行为。所有连接凭据的编辑归配置中心；项目只选择连接并查看有效来源，运行只读本次证据。未确认语义相同的vendor/provider不得直接合并。

| 实际字段/输出 | 用途、来源、条件与当前默认 | 联动、校验、保存/取消影响 | 处理决定 |
| --- | --- | --- | --- |
| `id` / `profile_id` | 连接身份；UI生成client ID，API无ID生成8位，目录创建10位；test/models用profile_id引用 | create同ID替换不是冲突拒绝；PUT不存在为ValueError；前端错误文字匹配404/not found后回POST | ID隐藏于诊断，引用保留；不得把自动重建当恢复合同 |
| `label` ↔ API `name` | 用户可读名称；UI要求非空，创建空名由后端补，更新可空 | 两编辑表面共用内存条目；完整后800ms自动保存，显式保存也走同核；无真正取消编辑按钮 | 保留单一名称；新设计采用清楚的草稿/保存/放弃，不混隐式提交 |
| `kind` / 兼容`profile_type/type` | 当前类型选择LLM或Search；未知归LLM | manage change分支会清vendor/URL/model但保key信息；input也处理select，重绘可能影响change；类型跨域变更有凭据复用风险 | 类型用于目录分类，跨类型变更需独立影响确认；本片不设计Search字段 |
| UI `vendor` ↔ API `provider`、`vendor_id` | UI厂商表含默认URL/免密规则；保存把同一个vendor同时写provider/vendor_id；后端目录中vendor身份与协议不同，例如Gemini用openai兼容协议 | UI读回只取provider，丢vendor_id；未知厂商可保存，client只有anthropic特殊协议，其余OpenAI兼容。换厂商仅当URL空或属于任一预设才改默认URL，保已有key | 保留厂商身份与协议区别；统一公开目录候选，先核自定义厂商兼容再收敛，不复制第三份表 |
| `base_url` | 服务端点；UI非空必填；API trim但不校验URL/scheme | client去尾斜杠且已知provider缺URL可补默认，health仍判缺URL；改地址会改变后续run路由hash；现key沿用 | 明示当前地址与变更影响；换域凭据确认及URL边界列后端缺口，不能只靠UI |
| UI `model` ↔ API `models[]` | UI只读第一项，编辑/点候选写单项数组；API允许多项且无元素/去重校验；LLM实际默认第一项 | 重存会丢其余项；顺序有执行影响，不是fallback池；已保存test优先旧models[0]，忽略payload.model修改 | 保留完整现存数组兼容；区分选用模型与发现候选，不把未支持的多模型调度包装成能力 |
| `api_key` | 用户临时输入；GET原key删去，编辑框空；有新key时test/models发原始草稿，无新key时只发保存ID | update空串保旧，空格truthy再strip可清；create同ID空值也沿用；无正式clear操作。隐藏/显示只是输入框显隐，不回取旧key；换kind/vendor/URL保留旧凭据 | 留空保留、替换、明确移除应分别表达，移除尚无可靠API合同；不采用空格技巧。密钥只在唯一编辑处，不进项目/运行快照 |
| `api_key_masked`、`has_api_key`、`key_required` | 公开遮罩/存在及要求；长key公开前8后4，短key***；has_api_key也可能是免密真值 | UIload从masked/key重算has，未直接取公开has；helper免密由显式false、厂商或URL含localhost/127.0.0.1判断，后端也有字符串推断 | 存在、免密与真实验证分开；本机判断不可把字符串包含当严格hostname验证；不扩散遮罩片段 |
| `is_default` | 同类型默认标记，创建false；设true清同kind其他标记，允许全false | UI仅manage有checkbox；**未发现LLM执行兜底消费者**，不能说未选择项目自动用它 | 保留旧数据含义，名称须不承诺自动路由；真正默认策略留合同阶段决定 |
| `created_at/updated_at` | 后端生成记录时间；UI转换未保留；无revision | 保存失败可能内存已变；没有并发版本冲突拒绝；测试未绑定版本/时间 | 保留可信来源，未来标明保存与验证对象；不伪造revision或最近验证 |
| `status/missing_fields`、目录计数 | health只核URL/models/必要key，ready是字段齐全 | UI另校名称/厂商；`configuredCount>0`会抹effective blocking count；不等本项目能启动或供应商健康 | 分离配置完整、实际请求结果、项目门禁；删除重复“已就绪”大卡，具体缺项仍保留 |
| `providerAvailableModels/providerTestResult` | 模型候选与测试结果，当前全局UI变量；API返回models嵌套或test嵌套 | 未绑定连接/草稿/请求代号；切连接不清结果，迟到能污染另一编辑区；候选点选也会触发自动保存 | 改为当前对象局部反馈/候选；结果可读但不能当持久健康或已采用证明 |
| `model.provider_profile_id` | 模板/项目默认引用；项目由模板复制，不是活链接 | 项目normalizer用current or previous，已选值传空串仍回旧值；UI下拉仅LLM，未知引用不能静默换别项 | 归项目设置选择，显示有效来源/失效原因；清空合同需单独修，不能前端假成功 |
| `model.routing_mode`、`Agent.provider_profile_id` | 两值workspace_default/agent_override；后者且Agent非空才覆盖，否则项目默认 | 没有项目ID时无全局is_default兜底；摘要却可能取当前编辑选中Profile并把Agent计为有路由；同一Agent多个节点不是步骤独立覆盖 | 归项目路由/Agent例外，显示计算后来源；不在连接编辑里重复改授权或造步骤级后端覆盖 |
| `model.chat_agent_id/notes` | 聊天入口选择与路由备注，模板/项目独立保存；notes纯备注 | 当前manage的模板路由表紧挨全局连接，按钮保存整个模板；项目另有保存入口，不能以保存Profile代表保存项目/模板 | 路由归对应模板/项目，连接页仅关联只读去向；聊天/模板全字段后片调查 |
| `provider_route_hash` | run步骤冻结id/kind/provider/URL/models/key_required非秘密hash | 后续重新读取全局profile，hash变化拒绝并要求新run；key/name/default不入hash，轮换key可供后续调用；删除会使后续失败 | 历史证据只读，不拿当前配置填旧事实；解释“项目快照＋路由变更拒绝”，不承诺完整Provider快照 |

当前密钥仍由[paths](../total_control/constants_pkg/paths.py):11–14、[persistence](../total_control/state/persistence.py):16–28和[secrets_crypto](../total_control/secrets_crypto.py):19–68管理：默认data/provider_profiles.json加密副本、data/.master_key，内存明文、兼容旧明文；不符合用户要求的config集中迁移，仍属G09/N00E后续工作。本片没有读文件或迁移密钥。主密钥缺/空会重建，解密失败返回空，需独立验证恢复与不覆盖旧密文；加密不等于损坏已可恢复。

### UX01F1 动作、API和消费者合同

| 现有API（准确方法） | 输入 → 输出/副作用 | 现有消费者与页面要求 |
| --- | --- | --- |
| GET `/api/provider-catalog` | 本地固定预设 → `{provider_catalog}`，含id/name/provider/base_url/models/key_required/website | 当前厂商下拉另用JS静态表，没有发现该GET消费者；不是在线模型发现。保API，不先引入整个平台 |
| GET `/api/provider-profiles`；GET `/api/provider-profiles/{id}` | 全部/单个 → `{provider_profiles}` / `{provider_profile}`；单项不存在404 | 当前load用列表，转换丢vendor_id/多model/时间；失败回退旧localStorage可能冒充已保存。新版失败保旧需注明来源并能重试 |
| POST `/api/provider-profiles` | id可选、kind/name/provider/vendor_id/URL/key/models/default/key_required → `{provider_profile}`，201 | 新增/自动保存；同ID更新替换。完整字段、冲突/空值语义待后端合同，不把201当验证通过 |
| POST `/api/provider-profiles/from-catalog` | vendor_id（兼容id）、key、可选name/models/default → 普通公开profile，201；未知目录/缺必要key400 | 当前手工编辑未调用；只提供预设创建，不保存联网验证，也不新建第二连接模型 |
| PUT或POST `/api/provider-profiles/{id}` | 部分字段 → `{provider_profile}`；先改内存后save加密副本并原子替换 | 当前UI用PUT；手动保存/800ms自动保存共用；无revision，写失败不保证回滚。编辑中/保存中/失败保稿合同需要明确 |
| DELETE `/api/provider-profiles/{id}` | ID → `{ok:true}`；只删连接，不迁移/清理引用、不拦占用 | manage入口有确认但不清当前项目草稿；workspace remove会清当前model/agents草稿，未由该操作持久化。未来应先解释受影响引用并明确处理，**没有enabled/禁用API** |
| POST `/api/provider-profiles/test` | profile_id或原始草稿 → `{test}`；缺保存ID常为200下success=false | 有ID完全取保存配置，首model优先；原始草稿不保存，必须明确测试对象；成功只代表这次请求，非工具/流/全项目支持 |
| POST `/api/provider-profiles/models` | profile_id或provider/URL/key等草稿 → `{models:{success,models,provider,base_url,error}}` | 模型列表不是completion；原始models草稿不消费models数组。当前只读列表长度，不直接核success；候选不应跨连接共享 |
| GET `/api/provider-route-health` | 当前Profiles/Agent/模板/项目 → 计数/status/issues及逐profile静态缺项 | 当前web主要消费status payload的provider_route_health，非不断请求该GET；诊断可给受影响对象入口，不能替代实际节点门禁 |

测试实际发ping、max_tokens=8、timeout=15；失败后再查models（另15秒），没有本操作共用总deadline，不依docstring承诺“1 token/总15秒”。OpenAI兼容GET /models只列id；Anthropic分支直接success=true、空列表及“不支持列表”说明，**没有发请求**。completion非流式缺choices可能空正文无error，属待故障注入风险；错误可能带供应商body、test带正文预览，公开诊断脱敏仍待独立验证，不能用真实key制造证据。

实际执行路由见[拓扑](../total_control/workspace/automation/topology.py):9–41、[Agent调用](../total_control/state/workspaces/agents.py):532–563、[对话消费者](../total_control/state/workspaces/chat.py):302–316/659–671、[模型规范](../total_control/workspace/schema/recipe.py):84–108；[工作流受理](../total_control/state/workspaces/workflow.py):147–229及[冻结记录](../total_control/state/workspaces/workflow_records.py):319–351/427–430核hash与快照。仅核引用和有效模型，不扩展这些页面的编辑设计。

### UX01F1 异常、返回与冗余处理决定

- 新页面需分别表达：草稿、保存结果、字段完整性、模型列表读取、指定模型请求结果、项目有效路由、旧run事实；这些不是同一个成功状态。正常加载不保留顶部“状态读取完成/30秒”块，失败保重试入口，不把说明铺成操作手册。
- 当前两个编辑表面共用内存条目，填全即800ms写全局；切连接/关页无可靠放弃或取消pending，save后列表重读也可冲掉其他草稿。新合同应在唯一配置编辑位置明确保存/取消，变更模型/地址/凭据时说明影响；跨页保项目/run和返回位置，不静默采用。未来实现前需消融所有调用者，不在本片删旧入口。
- 当前test/models/save/load没有连接身份/草稿版本门禁或忙碌防重，候选迟到可显示另一连接；保存、删除及迟到重读可能重建/覆盖（后两项静态风险，未逐一复现）。后续应按连接+请求对象隔离反馈，不能造第二全局状态源或把错误退回缓存叫成功。
- 全局连接页只编辑接入信息；模板默认路由、项目选择与Agent例外各回所属编辑页，显示有效值/来源和只读引用。工作台保选择、修复返回与诊断能力，不再重复输入key；旧路由摘要中“选中编辑对象=默认路由”候选退出，门禁仍以现有后端事实为准。
- 前后端厂商表、完整性规则、项目路由重复解析都是收敛候选，但目录身份/协议/项目优先级语义要先对齐；不凭相同名字删helper。本轮不选LiteLLM，不增加运行依赖；后续若替协议层，先对照错误、预算、模型响应和退出旧路径成本，不引入第二路由/重试所有者。

### UX01F1 浏览器证据与未验证范围

2026-11-09，xng/Playwright、Chromium140.0.7339.16，未改正式web；HTML预算按Handler替30。全部网络拦截，合成公开Profiles/models/test/保存回执；无真实服务、目录/凭据文件、LLM/SSH/GPU调用。夹具test成功是消费者输入，不是本项目或供应商能力证明。

| 实际路径 | 观察结果 | 证明限度 |
| --- | --- | --- |
| 1440保存/测试/模型选择 | 已存遮罩/空key输入；测试发profile_id；清必填名称使草稿不完整、改URL/model后测试仍用保存ID/旧模型；models发保存ID、点候选填草稿；补全名称未按保存即PUT；显式保存重读目录 | 清名是受控不完整草稿用来隔离自动保存，不能称完整草稿天然可安全测试；无真实落盘/供应商请求 |
| 1440错误/竞争 | 保存503保稿、测试503显示原因；删除原生确认取消无DELETE；hold B models→选A→release，B结果/候选显示A编辑区 | 延迟与503由网络拦截注入；没有DOM/业务状态补写/force/关轮询；未验真实并发保存/删除/占用保护 |
| 1440空/新增免密 | 空目录可新增；新未保存ID测试not found；选择Ollama后URL仍空，补合法本地地址和model再显式保存成功 | 选择厂商自动URL**未通过**；明确手填地址是必要补充操作，不隐藏为顺畅流程。没有真实新安装或免密模型服务 |
| 1024/768/390 | 各实际选择A→清名/编辑URL→单Tab到model→刷新重进，未保存不完整草稿丢失 | 三宽仅这些动作，不是四宽完整保存/键盘/长名错误/前后退或整站可用验收；截图部分仅展示顶栏/壳，占屏与多层容器问题仍开放 |

最终18观察/1037请求=1027GET+7POST+3PUT，pageerror/requestfailed/未捕获观察异常/501均0，5图；**零异常不覆盖已观察的自动保存、测试对象错位、迟到污染和厂商联动失败**。首次脚本未限定列表容器，两个真实编辑入口同selector触发strict-mode，保记录后仅修查询范围。第二轮已记录13观察，但假定Ollama自动补URL导致保存等待超时；保现场图，第三轮明确记录失败并手填缺项，未改产品或放宽门禁。第二轮夹具缺ID用400，与实际通常200/test.success=false不符，第三轮修夹具响应并保旧记录；该结果不拿来证明后端HTTP状态。主代理实看390壳、1440迟到候选及第二轮缺URL图，不宣称全图/新手体验已验。

证据、三轮记录、脚本和截图仅本地 `/tmp/relaygraph-ux-audit/ux01f1/`，沿dev_work不可访问例外，不修复/重建、不提交。旧入口/模板路由/项目选择/手工与目录API/helper均保留，无业务代码或数据变更；监督独立只读复核后只提交三docs。调查尚未全域闭合，当时交UX01F2搜索接入调查（现见后文限定完成），不在此顺手改布局、引入框架或修后端。

### UX01F2：搜索配置、有效来源和返回资料

对应R03/R04/R09/R12/R13、G04/G09/G11/G19/G21/G26/G27/G40/G41/G43及新增[G44](current-audit.md#g44)。用户需要配置一次搜索服务，知道当前工具实际用哪条连接，能用自己的查询测试，并分清“搜到了新资料”“没有搜到”“搜索失败，使用项目已有资料”。这与选择LLM模型是独立任务；搜索工具的READ分类不代表离线、免费或不向外部发送查询。

源码链：[Search选项/有效性](../web/config-center/config_center_provider_profiles.js)、[AI编辑](../web/config-center/config_center_ai_renderer.js)、[工具测试编辑](../web/config-center/config_center_tool_renderer.js)/[事件](../web/config-center/config_center_tool_actions.js)、[app.js](../web/core/app.js):20835–20932/21600–21740/25778–25809 → [registry.py](../total_control/state/registry.py):47–78/432–480 → [安全测试包装](../total_control/state/registry_pkg/tool_testing.py) → [Context](../total_control/tools/workspace_executor_pkg/context.py):133–158/[dispatcher](../total_control/tools/workspace_executor_pkg/dispatcher.py):55–62 → [搜索适配器](../total_control/tools/workspace_executor_pkg/web_search.py)。共用连接身份、800ms自动保存、凭据空值/目录与data存储问题沿UX01F1，不再复制一份保存规则；不改代码、Search API或真实配置。

### UX01F2 搜索专属字段、默认和归属

| 字段/控件 | 用途、来源、条件、当前默认/校验 | 联动与保存影响 | 保留/调整决定 |
| --- | --- | --- | --- |
| Profile `kind`、`label/name`、`id` | Search类型、显示名与引用身份；UI需选择search，API接受search/web_search/web-search | 沿F1共享CRUD和草稿核，不另建Search存储；Search保存models为空，不要求model | 全局连接页唯一编辑；模型页与搜索页可按职责分类，不重复key表单 |
| Profile UI `vendor` ↔ `provider/vendor_id` | 选项firecrawl/serper/duckduckgo/endpoint；UI需非空；后端不限制白名单，兼容ddg/generic/http/custom | UIchange分支换厂商填其默认URL、设置key要求；和input重绘关系沿G43风险，不能假定联动可靠。未知provider非空也可能显示字段就绪 | 保留明确供应商，不能用“已填”宣称适配器存在或已联网 |
| Profile `base_url` | Firecrawl/Serper默认端点可选；endpoint必填，可含`{query}`；DDG无需配置URL；API仅trim | 执行先firecrawl/serper，随后任何非空endpoint，再DDG/network；**DDG条目若有URL会走endpoint**，不是DDG HTML。保存会影响后续搜索，不改LLM路由hash | 只在适用厂商显示可编辑端点；保已有自定义值/高级读取，不静默删改 |
| `api_key/key_required/has_api_key` | Firecrawl/Serper UI必需；DDG免密；endpoint可选；API免密规则与UI并非完全同表 | 留空保旧/替换/移除及明文显示沿F1；执行还可能用环境key，字段健康不验证该环境。CRUD对免密空key会填占位key（E2），endpoint可能将其发为Bearer并挡住环境回退（E3影响，未验真实鉴权）；浏览器夹具未模拟这一私密保存转换。Profile默认data存储仍待config迁移 | 凭据只在连接页；免密不显示“已保存密钥”，来源不能靠猜 |
| `is_default` | **Search有真实默认消费者**；无显式ID取默认Search，否则第一条；不筛字段ready | 设默认清其他Search默认；顺序/删除/新增可影响无绑定调用；没有Profile enabled/禁用 | 保留默认标记及影响说明，不把LLM无兜底结论套过来 |
| `manageToolSearchProfileSelect` / tool `provider_profile_id` | web.search全局定义绑定，默认空；工具规范只存字符串，不核连接存在/kind | 改下拉同时改工具草稿和测试JSON；需“保存工具”才持久化绑定。显示值为空时会用默认/第一Search填回；选“自动”也可能显示某条默认 | 归工具能力连接选择，不编辑Agent授权；显示“继承/显式绑定”的真实区别，不能用选中项伪装有效来源 |
| `manageToolTestWorkspaceSelect` / `workspace_id` | 测试上下文；默认当前/首项目，空标签“自动选择最近实例” | 后端显式未知ID也回首项目/空对象，影响默认query及种子；选择上下文不保存项目，UI只清结果/错误，不重算现有query | 测试应显示实际上下文并防串项目；未识别ID应显式处理，不能暗换项目 |
| `manageToolTestArguments` / `query` | 当前用JSON大框，无专用查询输入；默认项目goal/brief/idea、仓库或RelayGraph smoke；运行query空则用context.goal | UI验证JSON必须object；缺查询可被项目目标补，不能把测试文本当已保存工具配置 | 新合同查询/数量为常用字段，JSON进诊断；此为设计需求非本轮新增控件 |
| `limit` | 普通搜索默认5，1–10；float→int，0被or5；Type/Value错误回5；Profile测试默认3、1–5 | 浏览器无专用数值校验；字符串inf在普通搜索转int抛未捕获OverflowError（纯方法已观察） | 两种测试上限说明分开；有限数值校验归后端缺口，不只做HTML限制 |
| 参数 `provider_profile_id/search_provider_profile_id` | 调用级选择，优先于工具绑定；别名也被resolver接受 | 只有canonical字段未知ID被阻断，别名未知会继续参数/env/network；选择“自动”只删canonical，不删别名。reset又填草稿绑定或默认ID | 统一显式引用失败语义；高级参数保兼容，不让双ID/不同默认入口制造隐式换路 |
| 参数 `provider/endpoint/network` | 无Profile或其对应字段空时继续参数/环境；network truthy可触发DDG | 未知provider可因endpoint走通用适配；普通bool使`"false"`也真；不是项目model连接，绑定也不是禁止调用其他连接的权限门禁 | 低频高级输入与实际来源需诊断；不在项目重复放供应商key/环境变量表 |
| Firecrawl参数 `base_url/country/categories/include_domains/includeDomains/exclude_domains/excludeDomains/scrape_options/scrapeOptions` | API/工具JSON支持，无独立表单；列表由_string_list解析；可给地域、域名、抓取选项 | 仅本次调用；URL按Profile→参数base_url→专用环境→默认，非/search结尾加/v2/search；POST Bearer | 保留已有高级能力，不默认铺满表单；常见参数是否提升为字段留合同阶段 |
| Serper `endpoint/location` | endpoint按Profile→参数→专用环境→默认；location可选 | POST q/num/location，X-API-KEY；仅本次调用 | 按厂商条件显示，不合并成不明含义的“上下文” |
| 环境来源 | 通用TOTAL_CONTROL_WEB_SEARCH_PROVIDER/ENDPOINT/API_KEY；Firecrawl/Serper各自key与API_URL/SEARCH_URL；无provider时按环境key推断 | 源码支持旧环境路径，缺Profile key还会用环境；本轮空替代env验证，未读真实环境值 | 保兼容；未来配置归config本地文件，显式来源/迁移另片；API未提供全部来源事实，前端不能猜 |

### UX01F2 选路、测试与执行消费者

1. 调用参数ID优先；无ID时dispatcher读web.search工具绑定。Context先查**当前全局工具定义**，仅全局无同ID才读workspace工具；全局空绑定也会遮住项目旧绑定。
2. 仍无ID时取默认Search Profile，否则第一Search；这里未筛ready，不能理解成自动寻找可用服务。只有Profile无或相应字段为空时才继续参数/环境来源。适配器按Firecrawl→Serper→endpoint→DDG/network→种子/未配置选择；没有失败自动切其他供应商。
3. 工具安全测试发保存tool ID与arguments，不发工具草稿。参数有ID时能测试未保存的选择；参数无ID时仍可能采用已保存工具绑定，而下拉却显示默认连接。reset重新填ID，并不是“清掉所有来源”；用户不应需要读JSON才能发现实际连接。
4. Agent经allowlist/原工具executor调用同一dispatcher；[agents.py](../total_control/state/workspaces/agents.py):587–593在本次Agent调用时复制当前全局Profiles/工具。run的workspace快照不等搜索连接冻结；后续Agent可采用更新的默认/绑定/Profile（E3影响，未真run验证）。LLM的provider_route_hash不能证明搜索已冻结。
5. Profile删除无引用占用保护、不清工具绑定；显式旧ID可能blocked，无显式ID可改选另一条。route-health只统计Search数量/字段齐全数，没有web.search绑定缺失/错kind专项诊断。没有Profile启停API，不把工具enabled混作连接启停。

| 接口/入口 | 输入 → 输出与真实边界 | 现页面需要表达什么 |
| --- | --- | --- |
| GET/POST `/api/provider-profiles`；GET/PUT/POST/DELETE `/api/provider-profiles/{id}` | Search共用公开Profile CRUD，见F1；/from-catalog当前LLM目录创建，非Search专用目录 | 保存连接与保存工具绑定不同；不能承诺删除自动修复引用 |
| POST `/api/provider-profiles/test` | 保存profile_id或原始kind/provider/URL/key/query/limit → `{test}`；有ID全用保存配置。草稿builder不消费create支持的search_provider别名 | 搜索测试无项目种子，默认smoke查询；empty也success=true。返回status/provider_status/count/provenance/rate_limit/error，不含完整results/fallback/message，不保存验证结论 |
| POST `/api/tool-definitions/web.search/test` | `{workspace_id,arguments}` → `{test:{status,safe,side_effect,workspace,arguments,latency_ms,result}}`；保存全局工具/连接参与执行，READ允许联网 | 外层ok/safe仅执行返回与副作用分类，内层可blocked/error/seeded；不能把“测试已完成”当检索成功。未知工具404，未知workspace当前静默回首项 |
| PUT或POST `/api/tool-definitions/web.search` | 当前工具字段含provider_profile_id → `{tool_definition}`，保存可影响后续调用 | 本片只核Search绑定保存，完整工具CRUD/授权归F3，不合并两个领域 |
| Agent工具执行 | 实际工具参数/允许工具/本次context → 搜索观察JSON与trace，非独立Search REST | [agent_trace](../total_control/workspace/execution/agent_trace.py):73–104只按顶层status判断，seeded即使provider_status=error也可tool.result/ok；运行阅读须保留降级来源 |

### UX01F2 结果、失败和页面合同

| 实际搜索情况 | `status` / `provider_status` | `results`与应显示的含义 |
| --- | --- | --- |
| 获得网络条目 | found / found | 网络结果；显示title/url/snippet/source及本次查询，不等可信性已验证 |
| 请求完成但无条目 | empty，或有种子时seeded / empty | 空或已有项目资料；明确“未搜到”，不能用种子数量冒充新结果数 |
| 请求失败/缺query或key | error或blocked，有种子时seeded / error或blocked | 种子只来自repo_urls/paper_urls，source=workspace.input；说明失败/缺项与修复入口 |
| 没有配置 | unconfigured，或有种子时seeded / unconfigured | 已有资料可继续阅读，不代表搜索已接通 |
| canonical显式连接不存在 | blocked / blocked，可带种子 | 早退缺latency_ms/result_count/result_provenance/rate_limit等统一尾部，不把缺计数补0当实测；别名异常行为见G44 |

`provider_configured`是适配器对接入配置的判定，不是生成/检索成功；`fallback_used`表示用了已有项目种子，不是换供应商。结果保留message/error及query以解释本次请求。正常尾部还有provider_profile_id/name、latency_ms、result_count、result_provenance和rate_limit。result_count包含返回种子；rate_limit只是静态提示/max_results，不是实际quota、限流、预留或429重试。结果项source可由供应商覆盖，URL仅非空检查；不当证据认证，也不能不经安全处理生成任意协议链接。Firecrawl/Serper去重，endpoint不去重；malformed或HTTP200错误对象可被解析为空结果，不能以“无异常”推出成功。

Firecrawl/Serper固定同步urllib15秒、endpoint/DDG12秒，read无正文大小/总墙钟门禁；没有Agent剩余deadline/cancel传入搜索调用。Agent前后guard不等在途立即可取消，预算/体积/真正网络失败另片验证。错误有指定key/部分参数脱敏及800字符截断，但任意结果正文没有统一保证，不读真实敏感内容制造证据。

页面职责需求：连接页维护唯一Search配置、显示配置完整性与一次连接测试；工具页选择绑定/查询并显示有效来源、实际上下文与搜索结果；运行页展示本次查询、网络/已有资料来源和异常，配置仅给明确修复返回入口。保查询/结果点击与高级能力，不用裸JSON或常驻手册替代常见操作。候选连接、保存与测试反馈按请求对象归属，未保存/返回/刷新明确，不让迟到搜索结果写另一工具编辑区。未来先收敛重复Profile编辑与“自动”假选择/重复成功卡，不删除尚有消费者的旧入口、适配器或环境兼容；Agent授权编辑独立调查后再定位置。

### UX01F2 实际证据、消融边界与交接

2026-11-09，旧web未改，xng/Chromium140.0.7339.16、HTML预算替30，全部网络由Playwright拦截，公开Search连接/工具定义/结果/保存仅合成，无真实服务、配置/凭据、搜索供应商、SSH/GPU或任务。浏览器夹具没有项目，未用项目种子；正常found回执仅消费者输入。另独立加载原搜索适配器与Context/dispatcher原AST，替代空env、socket拒绝、合成urlopen，13场景/10次假网络调用，仅证明原逻辑输出，不是后端/网络验收。

| 本轮路径 | 实际结果 | 未覆盖/不宣称 |
| --- | --- | --- |
| 1440 Search连接 | 无Model控件；保存ID测试empty显示“接入可用·0结果”，业务error显示未就绪 | 未新增连接或测试真实搜索/凭据，F1保存证据不重记本轮通过 |
| 1440工具测试与保存 | 默认JSON含保存绑定b；坏JSON拒请求；正常found、内部error但外摘要ok；选自动后下拉a/参数无ID，fixture按保存b回；reset填a；显式PUT绑定a；503保参数/可再测 | 后端真实绑定优先级来自E2/纯方法，浏览器仅合成消费；未验真实落盘/默认轮换/权限/配额 |
| 1440延迟 | hold搜索测试→选Repo Inspect→release，搜索结果显示在另一工具编辑区；原测试时按钮disabled | 原生点击和响应延迟，无DOM/业务状态补写或force；未验全部并发/跨项目/取消 |
| 1024/768 | 各选择a→参数单Tab到重置→合成测试→刷新回保存b，截图保结果 | 不是四宽完整流程/全键盘/长名错误/前后退；未保存选择不持久不等完善放弃合同 |
| 390 | 选择a后普通点击参数textarea被工具aside/toolbar遮挡，5秒超时，失败截图保留 | **参数点击/后续测试未通过**；不强制点击/隐藏列表/换方式绕过，也没重跑到绿；图主要是顶栏/壳，不证明字段可读 |
| 13纯逻辑观察 | canonical缺ID阻断/缺尾部，未知alias仍到endpoint；显式参数/全局绑定/默认优先；空/注入失败带种子、200错误误empty；limit99→10/0→5/inf抛OverflowError；占位符不自动附limit | immediate TimeoutError是故障注入，非12/15秒超时/取消/重启；source context和urlopen是替身，没有真实Agent/HTTP入口或供应商 |

浏览器14观察/783请求=773GET+9POST+1PUT，pageerror/requestfailed/501均0；**末390点击失败1**，不记全绿。5图含失败现场；主代理实看1440内部错误/迟到结果和390失败，监督独立只读核脚本、结果/请求与选图，不执行实现/测试。没有前片那种脚本修正重跑，本轮失败原样保留，不将检查器未报pageerror当用户流程通过。

材料仅本地 `/tmp/relaygraph-ux-audit/ux01f2/`，沿dev_work不可访问例外不修复/重建、不提交。正式仅三docs，第二部分登记G44及相关预算/参数/显示问题、逐文件台账；不改稳定规格/AGENTS/业务或数据，无可删除的已替代入口。当前少量HTTP适配器尚不能仅凭维护成本就引入完整搜索平台；成熟SDK候选须在需要替代具体职责时另做预算/错误/许可与退出成本对照，本片不加依赖。下一片 **UX01F3A：Agent定义、模型覆盖与工具授权需求调查**（工具全定义另F3B），全域闭合前不实施新布局或后端修补。

### UX01F3A：Agent定义、模型覆盖与授权的用户任务

本片对应R03/R05/R09/R12/R13、G04/G11/G19/G21/G26/G27/G40/G41/G43/G44及新增[G45](current-audit.md#g45)。用户要能创建可复用Agent，编辑职责、提示词、可用工具和运行边界，再知道哪些项目使用它、修改什么时候生效。不能把“目录有一个Agent”“节点绑定它”“工具被允许”“本次真的调用了”混成一个就绪徽章。此为需求调查，未改正式页面或后端；工具定义全CRUD/测试留F3B，模板版本/迁移留F4，完整调试执行/取消/恢复不在本片。

核心来源为配置中心agent renderer/actions/health，`app.js`的全局草稿/CRUD与项目Agent编辑、`workspace_draft_normalizers.js`；后端`registry.py`、`schema/agents_tools.py`、`state/workspaces/debug.py`与`agents.py`。快照关系仅追到`schema/templates.py::build_template_snapshot`、项目创建/更新及`workflow_records.py`，不据此宣称完整迁移已调查。

### UX01F3A 字段矩阵：编辑什么、何时生效

以下“全局”指可复用定义，“项目”指实例中独立副本；同ID不意味着配置相同。前端先归一再保存，后端还会再次归一；默认值和校验不是前端placeholder承诺。全局实际表单字段11项，另有只读时间；项目表单提供名称/角色/模型覆盖/启用/提示词/工具，保留预算字段在数据里但未给同等编辑控件。

| 字段/用途 | 输入与条件、默认 | 校验/联动事实 | 归属、保存影响与处理决定 |
| --- | --- | --- | --- |
| `id`：稳定引用 | 全局可手填；空由role/name生成；项目新增client ID，项目编辑不直接提供ID框 | JS在归一时立即生成；后端safe_id替非法字符而非拒绝。全局POST同ID是upsert，PUT换ID拒撞另一个定义 | 保留身份/显示名区别，ID编辑放明确高级动作；新建绝不能悄悄变成更新。改ID会改模板引用，见下表；项目/run不自动改 |
| `name`：显示名 | 两处可填，空生成Agent N | 项目编辑同步当前草稿节点handler.name；全局只改name未改ID时不重写模板handler旧名称 | 保留常用编辑；显示名称不承担执行授权/路由；保存前应说明是全局还是本项目 |
| `role`：职责/推荐种子 | 可自定义，空按名称safe_id生成 | 不是固定枚举，也不是权限；ID或role匹配内置preset时可能补缺字段，不能按角色名承诺已有能力 | 保留，避免当状态/能力标签；修改不自动改id，也不应静默重授权 |
| `description`：目录用途 | 全局textarea，空默认空；项目只读来源 | 后端`current or previous`使已有描述无法用空串清除；项目只保留同ID旧存储description，客户端新描述不接受 | 保留全局编辑，记录清空缺口；不可直接并入prompt或项目背景，二者消费者不同 |
| `prompt`：执行指示 | 两处可填，默认空；后端trim，无非空或长度门禁 | 全局更新不改项目副本。调试使用保存版本，UI改prompt未保存不会进入当前调试请求 | 保留完整编辑/阅读，明确保存和测试对象；不是页面常驻手册，也没有任意正文脱敏保证，不能填密钥 |
| `tools`：Agent allowlist | 全局逗号textarea；项目同一数组另有目录checkbox，可双向编辑；显式`[]`为无授权 | JS parse去重；后端目录非空且部分匹配时丢未知项，全未知的显式授权可能保原项。缺字段才可补角色推荐；不代表每项有效 | Agent是授权唯一编辑归属，工具页展示使用关系；项目副本授权不能误写全局。保明确无工具，未知/停用逐项说明，不自动补推荐 |
| `provider_profile_id`：模型例外 | 两处LLM下拉、默认空；不收key | 保存只trim，不核引用/kind/健康；未知ID没有保留option，DOM可能显示空而草稿仍保未知值。真正生效还需项目`routing_mode=agent_override`，否则用项目连接 | 保选择/清除与有效来源提示；key仅连接页。不能把“选了Agent连接”说成一定已覆盖，不能拿任一可用LLM冒充默认路由 |
| `enabled`：是否用于后续选择/就绪 | checkbox默认true | 后端普通bool转换，字符串false为true；完整工作流readiness拒停用Agent，但debug/执行器未统一同一门禁 | 保编辑，区分全局停用和项目副本、已接受run。不是全局立即停止；其余入口拒绝与停止语义需后端独立片 |
| `max_iterations`：迭代预算 | 全局number min1/step1、空placeholder默认10；项目数据可带但表单无同等框 | JS正数或空，后端safe_int正数保存，无上限；节点handler值优先，缺才沿Agent值，Executor最终10；report_only为1 | 保明确有效来源。全局保存空值被JSON省略，PUT先merge旧值，因此不能清已有预算；不是已完成的“恢复默认”动作 |
| `timeout_seconds`：调用时间预算 | 全局number min1/step1，空显示不限制；项目数据可带 | 后端先safe_int>0再float，0.5不保，无上限。全局debug回退Agent值，普通节点执行只取handler→node，未回退Agent值 | 保留但不得宣传所有节点继承；空值同上omit导致旧值保留。实际deadline/cancel沿G04，UI不能用倒计时伪造截止 |
| `output_format`：输出约束 | 全局空/text/json，空标跟随节点；项目数据可带 | 非法值归空；全局debug参数→Agent，普通节点执行仅handler/node，不取Agent默认；保存空可移除旧值 | 不合并节点输出契约；未来显示有效值/来源，先登记消费者不一致，再独立修复 |
| `created_at/updated_at`：来源时间 | 全局生成/保留，项目仅保同ID存储来源，无编辑框 | 全局更新更新时间，项目不能客户端伪造来源；不是配置revision，不支持据此拒绝并发覆盖 | 只读按需显示，不堆实时运行；有用的来源字段保留，不当当前Agent执行状态 |

工具目录与授权列表是两种职责，不因为包含同一ID就合并。当前执行先取Agent.tools与项目工具目录交集；交集与Executor查找只按ID，未过滤tool.enabled。工具“已停用”提醒不能当所有入口的硬拒绝证明（E2）；真实停用工具调用本轮未执行（E3影响待验证）。report_only强制空工具是另一个特定路径，不能泛化为普通Agent安全沙箱。工具adapter、side_effect和真实测试门禁留F3B。

### UX01F3A 动作、API、配置副本与运行的关系

| 动作/输入 | 当前入口与输出 | 消费者/影响及异常 | 后续设计要求/本轮决定 |
| --- | --- | --- | --- |
| 列表/选择/新建 | GET `/api/agent-definitions`→`agent_definitions`，GET `/{id}`→`agent_definition`；旧web主要从status目录装配 | 选择会重建草稿/清debug和dirty；无保存/放弃确认。点新增虽清selected ID，但renderer发现目录非空就选第一项，draft已有new_agent不被替换；保存变旧ID的PUT | 必须区分创建/编辑身份；保新建、编辑，G45先登记不修。浏览器合成证明见下表 |
| 保存定义 | POST `/api/agent-definitions`→201；PUT或POST `/api/agent-definitions/{id}`→200，均`agent_definition`；旧web已有选择用PUT，没选择用POST | 完整草稿payload含tools/enabled/引用，预算空值omit；无busy/revision冲突控制。成功loadStatus重读再select，失败保稿/报错；前端捕获不到持久失败后的可靠回滚事实 | 明确保存对象、有效版本、失败状态和可重试动作；不混入F1连接800ms自动保存规则，Agent编辑没有这条自动保存 |
| 改ID/名称、停用 | PUT body.id可不同；更新全局定义 | rename重写全局模板handler.agent_id/name、agent_ids及chat_agent_id；仅改name不同步旧handler名；普通全局改prompt/授权只供后续快照。停用不改已有副本/run | 保存前显示影响范围，不能把全局编辑当修改所有项目；复用已有复制/应用机制，模板迁移留F4 |
| 删除/取消 | DELETE `/api/agent-definitions/{id}`→`ok`；原生确认取消无DELETE | 无占用检查，删除会清模板handler/chat_agent引用；helper删除分支不直接清agent_ids，不保证所有引用已清。未遍历workspace/run。未保存新草稿点删除变重新新建 | 保危险确认与准确影响提示；取消编辑目前无独立放弃按钮。不能擅删旧API/编造占用门禁，引用诊断与持久补齐独立片 |
| 项目Agent编辑 | `app.js::updateSelectedWorkspaceAgent`改本项目draft，改name联动本草稿节点，保存项目PUT `/api/workspaces/{id}`带agents/tools/model/nodes | 默认/预设合并与手改不同；项目删除Agent至少留一个，清本草稿节点/chat引用；`normalize_workspace_agents([])`还会回填默认。项目选择、预设应用全流程留UX01G | 必须保项目专属覆盖和保存/取消，不做只读角色展示；项目没有全局description写入口不等于丢字段 |
| 创建项目/开始运行 | template snapshot按agent_ids拷贝当前全局定义→新workspace；RunPlan再深拷workspace | 全局更改不持续修改已有项目或冻结run。运行从冻结项目Agent/节点/工具取配置；Provider仍当前全局并核route_hash（F1），Search适配器依赖另见F2 | 显示配置来源/快照边界，不推论所有工具依赖已冻结。显式模板应用是现有能力须保，完整版本迁移尚待F4 |
| 健康/授权/已绑定 | manage health只按enabled、工具是否存在/停用和连接字段齐全生成提示；无覆盖时只找任一可用LLM | “就绪”不检查实际项目路由/绑定/适配器，也没证明模型调用；`workspaceNodeAgentContractMarkup`总优先Agent连接，可能与workspace_default真实路由不同 | 字段完整、绑定、授权、实际执行四种反馈分开；收敛有效配置读取，不能增加第二路由解释器；静态缺口见G11/G21/G43/G45 |

后端`registry.py:185–255`先改内存，再分次保存Agent与模板，没有跨文件事务或配置revision；`persistence.py:36–58`还会归一/去重。保存异常造成两个文件/内存不同步是E3，未本轮故障注入。集合load的默认回填与单条删除最后项即时行为不同，也未实测重启，不能写成“删完必空”或“已恢复”。这些与本轮浏览器合成CRUD严格分开。

### UX01F3A 调试入口的输入和副作用边界（限入口调查）

| 输入/动作 | 旧web真实提交 | 后端输入/输出与影响 | 归属及决定 |
| --- | --- | --- | --- |
| `manageAgentDebugTemplateSelect` / `template_id` | 选模板或无模板，选择Agent时重置到当前/第一模板 | 全局debug以保存模板组装上下文；未知ID静默用临时模板，不是找不到拒绝 | 保选择但必须显示实际采用的模板/上下文，不把fallback称已选模板 |
| `manageAgentDebugInput` / `input` | 默认为空；选Agent清空；项目debug可填入当前项目/节点生成文字 | API兼容text；非空且execute_llm truthy才进入实际调用 | 输入是这次诊断，不直接保存为Agent prompt；项目未保存草稿生成的输入文字不等于Agent配置也已保存 |
| `manageAgentDebugExecuteLlm` / `execute_llm` | checkbox；默认预览，不勾时仍POST但不调用模型 | POST `/api/agent-definitions/{id}/debug`→201，`debug/workspace/agent_definition/effective_config`；执行再有execution。201不表示真实执行或成功 | 保预演与实际调用能力，动作明确费用和允许副作用；当前“不提交任务队列”tooltip不能当无副作用承诺 |
| Agent身份与预算/格式 | 路径优先selected ID；请求另有当前选中模板node_kind，以及草稿max_iterations/timeout_seconds/output_format；**不发草稿prompt/tools/model/enabled** | 使用已保存全局Agent，预算/格式请求值优先并可回退Agent；effective_config无迭代时可显示0，Executor实际默认10 | 当前是保存定义+局部草稿的混合测试；未来明确测试保存版本或草稿的单一合同，不能前端私补。保存后再测不是掩盖产品缺口的验收辅助 |
| API的`tool_ids`及高级上下文 | 全局旧表单不提供subset；API还接受资料/环境/项目连接与routing_mode等 | 全局subset只能缩小已有授权；全局调用未传受控runtime对象，但非runtime工具仍可真实读取/联网或修改临时预览对象，不能称沙箱，也不证明报告实物写入 | 保留高级API能力，不默认铺满常用表单；完整工具副作用边界留F3B |
| 项目debug入口 | POST `/api/workspaces/{workspace_id}/agents/{id}/debug`，web仅input/node_kind/execute_llm，不发Agent草稿 | 用保存项目副本；API还支持node_id/tool_ids。subset仅预览使用，执行未传；显式node_id不核路径Agent与handler.Agent一致，实际可能用另一Agent（E2路径，E3后果未动态验证） | 必须准确定位保存版本/实际目标、展示预演与实际授权；完整运行/事件/取消/重启留后续独立片，不借调查修复 |
| 在途、失败、复制、切换 | busy只改文字没禁用按钮；无请求Agent身份门禁，catch/finally写共享debug对象；可复制完整结果JSON | 503有原因与再测入口；切换Agent后迟到结果可写到新编辑区。调试使用保存definition，本轮合成回执不证明真实调用 | 结果归属明确ID/请求，保稿/重试/返回需合同；复制是诊断能力，不默认常驻长JSON。未测试复制或重复发起的全部后果 |

全局debug另以profile.api_key非空判断，免密Profile可能被拒，与正式health路径不同（E2，未真调用）。其中artifact/report写入或workflow.edit可改临时预览对象，不等于正文落盘或保存项目，完整工具语义留F3B。全局debug仅对停用Agent发预览警告，debug/Executor未统一workflow readiness的enabled门禁。项目debug能执行节点并保存成功后的workspace，所以“调试”不能等同只读查看。实际开关/副作用授权和冻结事实应由后端负责，前端明确展示；本片没有真执行disabled、subset/错node目标或配置/文件工具。

### UX01F3A 页面职责、删保与实际证据

需求层先定归属：配置中心编辑全局Agent及授权、给一次诊断；项目设置编辑本项目副本和例外；流程设计选择执行者/节点覆盖；运行页阅读本次冻结配置/调用结果和精确修复返回。不在这里先画新版多栏或规定所有字段折叠。普通任务要能直接配置、校验、保存再使用；健康徽章不能代替编辑/调试。沿frontend-design已有来源/许可记录，只用任务优先和层级指导，不引入多Agent框架、运行依赖或外部字体。

删保决定：全局和实例Agent虽有同名字段，但保存对象、来源和消费者不同，保两种编辑能力；授权文本与checkbox可在同一Agent编辑责任内收敛输入，不能在工具页再建第二授权编辑。全局debug与项目debug也不能未验证就合并执行器。候选精简的是重复静态健康/路由摘要与混杂的常驻结果卡，未来对照有效值/异常/动作再退出；本片未替代或删除任何旧入口、helper、API、测试或生产文件。

2026-11-09，未改生产web，xng/Chromium140.0.7339.16，HTML两个预算占位仅夹具替30；所有网络拦截，合成公开Agent/LLM/工具及回执，未启后端/Provider/SSH/任务、未读真实配置/密钥。模板/项目为空，只观察全局Agent交互；项目/快照、停用和工具授权执行结论是源码E2，不冒充E1联调。

| 实际路径 | 结果与证据 | 没有证明什么 |
| --- | --- | --- |
| 1440保存与切换 | 改prompt/tools/model/预算3→调试请求只含保存ID/局部预算，合成预览显示保存prompt，编辑仍未保存；切b再回a丢稿；保存503保稿；显式PUT空tools/disabled后重读 | 无真实落盘、后端归一/引用改写、模型或授权执行；没有模板选项/项目夹具 |
| 1440调试异常/迟到 | 停用后按钮仍可点，503在编辑区提示；hold a响应→点b→release，a结果入b；busy按钮is_disabled=false | 不证明重复请求次数或disabled真实模型调用；未验stream/取消/重启 |
| 1440新建/删除/刷新 | 非空目录点新增，draft=new_agent但active=b；保存body.id=new-agent却PUT `/api/agent-definitions/b`。删除确认取消无DELETE；修改prompt后刷新回保存空值。另空目录正常新增POST | 前者是旧web请求错位证据，真实覆盖后果E3；没执行真删除/重启/占用处理；刷新不是草稿恢复通过 |
| 1024/768 | 各普通点名称→fill→单Tab聚焦role→保存合成回执，截图保留 | 仅这一条编辑路径，不是完整键盘/所有字段/调试/长内容/前后退或四宽全流程验收 |
| 390 | 选a后普通名称click被aside/toolbar/模式栏遮挡，5秒超时失败1；保存failure图 | 名称编辑/后续Tab和保存未通过；不force、换路径、隐藏列表或重跑到绿；截图主要是壳 |

共15观察/794请求=785GET+4POST+5PUT，pageerror/requestfailed/未知501为0，**390普通点击失败1，不能记全绿**。无DOM或业务状态补写、无停轮询/门禁放松；fixture含保存/拒绝/延迟仅供消费者观察。5张图，本代理与只读监督实看debug-saved/late-debug/390失败；1440图只露部分结果，保存prompt和迟到归属主要由DOM只读断言/请求JSON支持，不能称截图全面可读。脚本、请求、日志与图仅本地`/tmp/relaygraph-ux-audit/ux01f3a/`，dev_work不可访问例外未修复/重建。文档范围/链接/字段/台账/敏感检查和独立终审后提交；功能缺口开放，调查尚未闭合；本片结束时交接的UX01F3B已在后文完成，当前指针见文首。

### UX01F3B：工具定义、真实能力和测试对象

本片对应R03/R05/R09/R12/R13、G04/G06/G11/G19/G21/G26/G27/G40/G41/G44/G45；本机工具路径还关联G12。用户要能维护工具的名称/用途，知道Agent能否调用、实际做什么、测试采用哪个配置与项目，以及失败后到哪里修。**工具目录不是插件安装器**：名称/描述/能力标签的保存不注册新的实现；固定ID才选中dispatcher分支。不可为了页面简洁丢掉现有配置/测试，也不能用“启用”或“已实现”替代真实能力说明。

源码链：`config_center_tool_renderer/actions`→`app.js`草稿/选择/CRUD/test→HTTP→`state/registry.py`→`schema/agents_tools.py`与`registry_pkg/tool_testing.py`→`tools/registry.py`/`workspace_executor_pkg/dispatcher.py`；项目Tool另由`updateSelectedWorkspaceTool`、项目保存和schema消费者接续。Search独有优先级/参数沿UX01F2；Agent授权入口沿UX01F3A，不复制第二份规则。本片只调查，不改正式代码，完整Agent调试生命周期/模板迁移排除。

### UX01F3B 字段、来源、联动和保存矩阵

全局常用7个字段，web.search条件增加连接选择为第8个；项目也有这8个数据字段，但现表单未提供Provider框。后端另保策略/实现元数据，当前全局和项目draft归一不保这些字段，旧全局payload未发送它们，后端merge可保旧；不能把编辑器未显示策略理解为无策略，也不能在重命名后保证策略与新ID一致。

| 字段/用途 | 输入来源/条件/默认 | 校验、联动与实际消费 | 归属、保存影响/处理决定 |
| --- | --- | --- | --- |
| `id`：引用与实现键 | 全局/项目可编辑；JS空由label→safeId，后端id→name→tool-N并safe_id；preset先匹配id/label/name | 不同于显示名，改ID可切换固定实现或失去实现。工具CRUD没有重复ID/rename撞名拒绝 | 保稳定身份、高级修改和影响提示，普通改名用label；新建/编辑分清，不能悄悄替换原定义 |
| `label` /兼容`display_name`、`name` | 全局文本、项目文本；空后端回id，JS空可回Tool N；这些兼容字段不全是独立UI控件 | 仅显示，后端name还参与ID来源，不能把兼容输入无证据当同义移除 | 保常用显示名，兼容入口留消费者核对；不用于授权或副作用判断 |
| `category`：分类 | 全局自由文本默认general；项目下拉workflow/research/repo/file/host/gpu/env/run/log/artifact/notify/chat/general/custom | 后端不限枚举；目录还能出现data/path等。项目未知值无专门option，显示可能不等草稿值 | 保分类，必须保未知旧值，不能因下拉缺项丢数据；只做组织，不代表能力 |
| `capability`：用途标签 | 默认read；全局自由文本，项目read/write/execute/control/observe下拉 | 后端任意字符串，无执行授权消费；填execute不实现命令，填read不改变固定副作用 | 保易懂用途/只读实际能力区分；不作为安全门禁，不重复Agent授权编辑 |
| `description`、`notes` | 两处textarea默认空，后端trim、可显式清空 | 说明文字不是执行约束；无任意正文脱敏承诺 | 保编辑；与Agent description空串保旧不同，不能复用错误清空规则；不要填密钥 |
| `enabled` | checkbox默认true；后端bool转换，字符串false仍真 | 测试不检查，实际Agent交集/dispatcher也无统一拒绝（F3A）；全局停用不改项目快照 | 保编辑和配置状态文字，不承诺全局停止调用；真正停用门禁单列后端能力 |
| `provider_profile_id` | 默认空，trim；web.search全局条件选择，项目数据保留但表单无框 | schema不验存在/kind；Search选路/全局绑定优先与自动选择错位见F2，其他固定分支没有该字段的相同消费 | 连接页管key，工具选择连接，不给每个工具重复密钥；保未知引用与清除，Search合同不复制 |
| `side_effect` | 后端/API可传，非空优先于静态map，未知默认read；现UI无编辑框 | 无read/mutate_config/mutate_runtime/dangerous枚举校验；测试按保存值exact read放行，但dispatcher按固定ID，trace又取静态map | 作为实现策略应有权威来源；当前不能信任可编辑元数据就是安全保证。未来只读能力说明，强校验/权威合并另片 |
| `implemented` | 静态map中ID默认该值，可被传入bool覆盖；未知ID固定false | 不控制前面的固定执行分支；部分内置分支无map记录仍能返回投影/回显 | 保实现层级解释，不能给“True=完整产品能力”的徽章；新增目录不安装adapter |
| `requires_runtime`、`fallback`、`runtime_control` | 后端/API字段，默认来自静态map；requires_runtime可false覆盖，后两者空值会回静态默认 | bool宽松；描述/来源不是回调注入。fallback=plan_only仍可能实际blocked；global/项目UI不编辑这三项 | 按需只读显示真实上下文可用性，保旧元数据；字段枚举/默认与执行对齐独立片，不前端自行推状态 |
| `created_at/updated_at` | 全局created按旧/当前/now，updated=now；实例只保同身份previous来源时间 | 来源时间不是配置revision；新建API可带created，不等用户修改时间或并发版本 | 只读按需，不堆任务状态；不借时间戳宣称冲突保护已具备 |

schema空工具集合或全无效会回填默认，启动再补缺内置项；这与Agent显式空授权`tools=[]`不同。项目旧说明“自动补配置可能重新加入Agent授权”不能泛化到明确空allowlist；未来移除误导常驻说明时保留准确的工具目录回填事实。当前未删除旧说明，也未改回填逻辑。

### UX01F3B 动作、API与引用影响

| 动作/输入 | 当前API/输出 | 已有消费者、异常与保存影响 | 需求/删保决定 |
| --- | --- | --- | --- |
| 浏览/选择/新建 | GET `/api/tool-definitions`→`tool_definitions`，GET `/api/tool-definitions/{id}`→`tool_definition`或404；web多从status装配 | 选工具重建草稿/清dirty，换ID会重建测试参数；无放弃确认。new草稿id=new-tool非空，renderer自动选目录首项，保存误用旧selected PUT（本轮E1） | 保目录与可编辑定义；修复创建/更新身份，不能以只读卡替代。与Agent同类错位统一记G45，不新增一套草稿存储 |
| 保存/改ID | POST集合→201；PUT或POST `/{id}`→200，返回tool_definition | create直接insert(0)，**不是upsert**；save只write_json不去重。update命中首旧ID，rename不拒撞目标；改ID重写全局Agent.tools，后归一全局Agent；不遍历模板/project/run | 保明确保存/取消、引用影响与失败可重试。重复ID查找首项、模板snapshot字典末项风险E3；不能照抄Agent“撞名拒绝”合同 |
| 删除/重启 | DELETE `/{id}`→ok；原生确认取消无DELETE | 删首项并清全局Agent授权；无占用检查/模板同步/历史迁移。启动归一首项去重并回填缺内置项（base.py:81–86/131–132）；内置删除不等永久卸载 | 保危险确认，解释全局目录/已有副本/内置回填；重复/重启/多文件失败本轮仅E2/E3，非真后端验收 |
| 项目Tool编辑/增删 | `updateSelectedWorkspaceTool`改项目draft并localStorage；保存项目PUT `/api/workspaces/{id}`带tools/agents | 改ID同步本草稿Agent.tools，还可能过滤其他不在目录的引用；删工具至少留一个并清本草稿授权。后端按同ID旧存储保策略/时间，空集合回默认 | 保项目覆盖，不能当全局目录被改；完整项目保存/离开/预设应用留UX01G，不把本轮合成global CRUD泛化 |
| 快照/执行 | 模板snapshot按tool_ids复制当前目录→新项目，RunPlan再冻结项目 | 全局改定义不自动改项目/run；但Search等运行依赖另取当前目录（F2）。ID固定分支仍在，删除目录不是卸载实现 | 来源/有效能力与配置快照分清；模板版本/应用下一域调查，未替代前不删旧API/helper |

全局工具与Agent两个文件依次保存、内存先改，无revision或跨文件事务（registry/persistence）。读取归一/启动回填与CRUD即时行为不同，故“保存成功后目录唯一”“删完下次仍为空”“已冻结全部依赖”均不能承诺；后果仍待独立真实入口实验。该问题不能只用前端换文案解决。

### UX01F3B 测试输入、门禁与返回

| 输入/动作 | 来源/默认与联动 | API/处理/输出 | 页面合同要求 |
| --- | --- | --- | --- |
| `manageToolTestWorkspaceSelect` / `workspace_id` | 当前选中项目或首项，空标“自动选择最近实例”；切工具/reset重置 | 后端ID不存在也静默选首项目，没项目用{}；deepcopy项目/status/jobs/Profiles/tools。不是重新采样，也不保证按更新时间挑最近 | 选定项目与实际采用项目都明确；失效选择应定位错误，不静默冒用上下文；跨页保选择与返回 |
| `manageToolTestArguments` / `arguments` | JSON object；按工具/当前项目生成默认参数，reset重建；数组/坏JSON前端拒请求，后端非dict则{} | POST `/api/tool-definitions/{id}/test`→200 `test`；不存在及ValueError由此路由包装404。请求只含workspace_id/arguments，无整份草稿 | 常见输入应专用字段，JSON留高级诊断；保已有扩展参数，不预定通用插件schema。校验就近且不冒称后端完整参数校验 |
| 测试身份/草稿 | `runGlobalToolTest`优先**草稿ID**，仅检查selected存在；名称/能力/enabled/描述草稿不发 | 未保存改ID可测另一保存定义或找不到；草稿改其他字段仍测保存配置。reset不是保存，也不是无副作用证明 | 明确保存版本或草稿的单一测试对象，含ID和来源；不能让用户先“保存一下”成为掩盖错位的验收辅助 |
| 门禁/实际调用 | safe_test按保存side_effect，只有exact read调用factory；其他blocked/safe=false/result.plan_only | 不核enabled/implemented/Agent allowlist；factory runtime=None，受控提交/控制回调缺失，但读取/联网仍可发生。可编辑READ元数据能放入原本config分支，修改的是复制项目对象 | 请求完成、门禁/副作用层级、内部结果分开；READ不等离线/免费/绝对无副作用。不可由capability标签推断门禁 |
| 结果/错误/复制 | 返回tool_id/status/safe/side_effect/workspace/arguments/latency_ms/result；参数按敏感字段脱敏 | 外层固定ok/safe=true不折算内层blocked/error/missing/draft；非JSON只留首4000文本。前端JSON展示截6000无标记，复制按钮取完整内存result（复制本轮未验） | 显示真实内部状态、来源、截断与完整阅读；输出正文未统一脱敏不等安全保证；保失败与重试，不能常驻裸JSON充当常用功能 |
| 进行中/切换/离开 | 当前busy按钮disabled，但reset/切工具/改ID能重建testState；结果仍共享写入 | F2已E1迟到串编辑区，此轮不重跑同现象；保存/测试503保本次稿/参数；刷新丢未保存内容 | 按工具/请求归属反馈，取消/返回明确；旧global与项目界面保留到有消费者与消融证明再退出 |

### UX01F3B 固定实现的用户含义与参数去处

这些是源码E2，用于保住配置和使用需求，不是全部真实能力验收。全局目录字段不能替代每个工具的业务参数；以下参数进测试/调用区，不堆到目录编辑表单。运行已有受控Job/资源链继续复用，不另造工具执行平台。

| 工具/调用参数 | 固定分支实际输出/条件 | 不应给用户的错误承诺 |
| --- | --- | --- |
| `workflow.plan`、`execution.package`，通常{} | 项目节点/命令/包与readiness投影 | 不推进/提交工作流；部分分支无静态map记录仍可调用，不能只看implemented |
| `file.read`（path/file/target、workspace_dir、limit/max_chars），`repo.read`（path/file、paths），`repo.inspect`（workspace_dir、max_entries） | read_tools读取/扫描本机Path，file.read限制片段1000–24000字符，但先读全文；repo.inspect提供清单/建议，未消费默认测试填的path/focus_paths。相对路径通常按项目目录 | 不是真实远端host_id文件读取；测试不能拿服务本机同名文件冒充远端，关联G12。limit不是IO大小门禁 |
| `file.browse/dir.scan`（path/root、workspace_dir、max_depth/max_entries），`path.resolve`（paths/data_roots/output_roots） | 本机目录/存在性线索，scan深度默认2最多4、条目默认180最多400；路径与敏感限制须沿现helper，具体分支界限不全相同 | READ不等无文件访问，不把所有路径helper视为同一个根目录合同；远端与路径边界另片验证 |
| `dataset.find`（query/data_roots/dataset_hints/workspace_dir），`repo.search`（query/data_roots/dataset_hints） | 前者本机扫描与资料线索；后者仅收集dataset配置/source参考线索，没有仓库搜索实现 | found/ready不等数据集已验证可用或完成代码检索 |
| `gpu.inspect/allocate`（server_id/min_free_mib/min_free_memory_gib） | 前者已有status候选，后者需runtime.bind_gpu；无runtime blocked，已有正式callback可plan_only/persisted=false | 快照不等新探测/资源预留；selected不等已分配 |
| `env.inspect/infer`（manifest_paths/setup_command），`env.prepare/create`、`repo.clone`、`job.run/host.exec`（已有环境/仓库/command/cwd等） | inspect/infer只投影配置；真正执行需submit_job回调、已有路径/资源门禁。无runtime blocked，不因fallback标签变成成功 | 不把命令/清单回显说成安装/执行完成；此处不重写N04受控任务参数协议 |
| `job.stop/reorder`（既有Job选择参数） | 受控control_job；无runtime blocked。默认测试参数latest=true仅作示例 | 不代表已停止外部进程，测试不绕过唯一生命周期入口 |
| `log.read`（默认{}） | 忽略指定Job参数的选择，按项目最近关联Job返回ID/status/显示路径 | 没有日志正文，不保证是用户指定run/attempt的本次日志 |
| `artifact.read`（output_key/key、label、node_kind、path/content_path），`artifact.collect`（artifact_paths/paths、metric_paths） | 声明及可选本机正文片段/目录stat，单项可missing/blocked，整组有记录仍可collected | 不下载/传输，不证明整组实物完整交付 |
| `workflow.edit`（node_id/node_kind、config/patch），`artifact.write/report.write`（目标、label/title、path、content/text、output_key/type等） | 改传入项目对象的白名单配置或产物声明；调用者决定持久化。written无文件写盘/验证，正文>4000只留summary；两目标都传时按遍历先匹配ID或kind，不是严格ID优先 | 不把written当文件交付；参数错ID仍可按kind落另节点，目标身份需明确校验；报告存储已有能力不能据此算所有工具写入已接通 |
| `chat.write`（message）、`notify.user`（message/text/summary、severity/level、requires_user/action_required）、`schedule.plan`（schedule/cron/when、command/run_command） | 回显payload/written/notified、dry_run计划，未实现消息追加/送达/定时任务创建 | 不宣称消息已发/计划已安装。web.search独立沿F2，不重列连接参数 |
| 自定义未知ID | 默认READ/implemented=false，dispatcher最终blocked | 新增目录、改ID或改implemented不能安装工具；不引入任意代码插件平台 |

### UX01F3B 证据、消融与交接范围

2026-11-09，生产web未改，xng/Chromium140.0.7339.16、HTML预算夹具替30，全部网络拦截；公开file.read/job.run及回执仅合成，没有项目/模板夹具、真实配置/密钥/服务/Provider/SSH/文件工具。浏览器18观察/796请求=785GET+6POST+5PUT，pageerror/requestfailed/501为0；**390名称普通click被aside/toolbar/模式栏挡5秒失败1**，不force/改DOM/停轮询/重跑到绿。

1440实际编辑名称/能力/停用后测试只发保存定义ID+参数；JSON数组拒请求、测试/保存503保稿、显式PUT空描述/备注/disabled；未保存ID改不存在发错路径、改job.run测试另一保存定义而列表仍file.read；内部missing外ok、长JSON6000截断；切换丢ID草稿，非空新增PUT旧file.read，删除确认取消无DELETE，刷新回保存名；独立空目录正常POST。未知工具test夹具误给400，实际源码路由404，**只支持错误文字/路径消费观察，不作HTTP状态码验收**；保原记录，未重跑掩盖。1024/768仅名称普通click→fill→单Tab到category→合成保存；390只选工具，名称编辑/后续保存未过。没有完整键盘/前后退/所有字段或四宽全流程通过声明。

另原safe_test/dispatcher AST+原纯内存workspace_mutations，注入无runtime假Context/factory、identity redactor（无敏感fixture）并禁socket，仅操作合成内存项目；不导入服务/真实配置，不读写实物或调用网络。初轮8场景第8错误假定未知node_id必报错，实际按默认node_kind找到节点，断言失败；保初版script/log/JSON，按源码纠正验证预期并加双身份皆缺失场景，第二轮13场景/11次假factory取得预期观察，**不删除首失败、不改产品门禁**。证明外ok内blocked/error、停用/未实现未拦factory、READ元数据放入config分支但无真实落盘、runtime无回调blocked、written仅声明/4001字丢全文、repo.search线索、log/chat/notify边界；不是实际HTTP/真实工具/保存恢复或脱敏验收。

5图（含390失败）；主代理和只读监督核脚本、请求与missing/draft-ID/失败三图，1440结果只部分在视口，结论主要由DOM只读断言/JSON支持，未称截图完整可读。材料仅`/tmp/relaygraph-ux-audit/ux01f3b/`，沿dev_work不可访问例外不修复/重建，脚本/图/结果不提交。无已替代路径可删；全局/项目定义、参数扩展、工具test、原dispatcher/受控runtime及旧API保留。公共草稿/测试归属组件只有在新页面合同和两个真实消费者验证后才抽，不先造通用平台；成熟工具库须替具体职责而非把目录换成完整平台。下一小片F4A查模板定义/绑定/校验，F4B再查版本/迁移，调查闭合后才设计新页。

### UX01F4A：模板定义、执行者绑定与校验

对应R02/R03/R05/R09/R12/R13，关联G10/G11/G14/G17/G19/G21/G26/G27/G40/G41/G43/G45。本片回答“怎样定义一条可复用流程、指定步骤执行者、检查配置并保存”，不重新实现流程引擎。模板是未来项目使用的定义；保存、目录中的`status`、本次`validation.status`和正式运行就绪是四件事。模板没有顶层`enabled`开关，不能沿用WB模拟的“启停模板”描述真实接口。版本历史/差异/升级迁移留UX01F4B，项目发现/应用、各类节点全部config/I/O参数和运行历史留UX01G；这里列出这些字段的消费者和交接，不称全部已审。

权威链路：[index.html](../web/index.html)的17个顶层编辑控件 → [catalog_actions](../web/workflow-template/workflow_template_catalog_actions.js)及[app.js](../web/core/app.js) → [state](../web/workflow-template/workflow_template_state.js)/[draft](../web/workflow-template/workflow_template_draft.js)/[lifecycle_actions](../web/workflow-template/workflow_template_lifecycle_actions.js) → HTTP四routes → [registry.py](../total_control/state/registry.py) → [模板schema](../total_control/workspace/schema/templates.py)、[节点schema](../total_control/workspace/schema/nodes.py)、[recipe/model/handler规则](../total_control/workspace/schema/recipe.py)、[validator/preview](../total_control/state/registry_pkg/workflow_templates.py)。公开投影由[monitoring.py](../total_control/state/monitoring.py)和[cockpit/payload.py](../total_control/workspace/cockpit/payload.py)提供；归一化不等于严格校验或通用敏感文本清洗。

### UX01F4A 顶层字段、输入与保存影响

以下列当前normalizer的全部顶层输出及嵌套子字段。表单字段在输入时即改内存草稿并清旧校验；后端的“空串保旧”与前端“显示已清空”不同。表内E2是源码事实，空值/写盘/重启没有做真实服务验收。保留指保留用户能力，最终页面位置要等全产品调查闭合。

| 字段/实际输入 | 用途、来源、条件与默认 | 联动、校验与保存影响 | 处理决定 |
| --- | --- | --- | --- |
| `id` | 无编辑框；新稿为空，服务端existing.id→payload.id→名称safe_id→随机 | update固定已有ID；create插首无重复ID检查；同名缺省ID也可能撞；不是名称 | 保稳定身份，新增/编辑分开；冲突风险登记G19/G45 |
| `name` / `templateNameInput` | 人可读名称；新稿按Repo/Paper/Idea默认命名 | 服务端空回旧，缺省按来源生成；改名不改ID；草稿无必填校验 | 保留；名称不能代替身份 |
| `description` / `templateDescriptionInput` | 说明适用场景，默认空 | 服务端空回旧/brief，清空不一定生效 | 保留用途；不与brief直接合并，修清空合同 |
| `status` / `templateStatusSelect` | 目录标记；UI ready/draft/blocked，新稿ready；schema接受任意非空字符串 | 不由preview自动改；CRUD不以它阻止保存/执行；未知枚举无对应选项 | 保定义标记，重命名文案区分校验；不推成产品成功 |
| `brief` / `templateBriefInput` | 创建项目的初始摘要，默认空 | 空回旧，参与来源/节点默认；不等模板说明 | 保留，明确进入哪个项目字段 |
| `source.type` / `templateSourceTypeSelect` | repo/paper/idea/mixed，输入为flat `source_type`，默认repo；mixed借idea默认链 | UI改来源立即重建整条nodes，无确认；后端非法来源变idea；不是仅改分类 | 保来源；改分类与“重建步骤”分为显式动作，不能悄悄丢节点 |
| `source.repo_url`、`source.repo_ref` / `templateRepoUrlInput`、`templateRepoRefInput` | 默认仓库及分支/提交，flat输入，默认空 | 空回旧，归一化同步相关首个kind节点；这里不验URL/仓库可访问 | 按仓库语义保留，项目明确覆盖 |
| `source.paper_url`、`source.idea_text` / `templatePaperUrlInput`、`templateIdeaInput` | 默认资料与目标，flat输入，默认空；当前同时常驻 | 空回旧，可补搜索/数据线索；不同语义不合成“背景”大框 | 保留各含义，按流程条件呈现 |
| `workspace_dir` / `templateWorkspaceDirInput` | 默认工作目录，空；模板本身无host字段 | 空回旧，会同步部分节点；没有存在/权限/远程位置验证 | 保留默认，不能叫已确认运行位置；具体host+path交G |
| `env.name/manager/python` / `templateEnvNameInput`、`templateEnvManagerSelect`、`templatePythonVersionInput` | 默认环境；name/Python空、manager空/conda/venv/custom；flat优先，再nested env，再旧值 | 无真实环境或版本探测；空回旧；Python3.11占位不是最低版本声明 | 按需求保留条件项，不能当已安装环境 |
| `recipes[]` | 返回数组，但后端仅生成一项；接收flat `recipe_id/recipe_name/setup_command/run_command/report_command/schedule/recipe_notes/recipe_enabled`，不读payload.recipes | UI取第一启用项否则首项并折成一项；仅发四个命令/调度flat值，不发recipe身份/notes/enabled；无顶层编辑框；后端首旧recipe作基底、文本空保旧，字符串false经bool仍true | 记录往返保真缺口；现节点命令编辑保留，逐参数在G查；不假定数组/禁用完整支持 |
| `model.provider_profile_id` / `templateProviderProfileSelect` | 只选全局LLM连接，不输入key；默认空 | 未知ID仅warning、空不报缺模型；后端空保旧；选项只列当前LLM，失效引用不显式保留 | 唯一连接编辑在F1配置页；这里保引用/有效来源/失效项，不能静默置空 |
| `model.routing_mode` / `templateRoutingModeSelect` | workspace_default/agent_override，默认前者；非法值归默认 | 覆盖逻辑沿F1/F3A，不是每节点另填key | 保路由选择与来源，只有明确例外才编辑覆盖 |
| `model.chat_agent_id` / `templateChatAgentSelect` | 全局对话Agent引用，默认空；显式空可清 | 未知仅warning；与节点handler不是同字段；选项未按enabled过滤 | 保对话职责，不把它设成所有步骤执行者 |
| `model.notes`、`notes` | 无当前顶层编辑控件；归一化/payload保留字符串，默认空 | 后端空保旧；不是新增第二份“背景”；不能因隐藏而删已有内容 | 保读取/往返，是否编辑待页面合同；不直接合并 |
| `tags` / `templateTagsInput` | 逗号列表/parseTagList，默认[] | 显式[]能清；分类偏好不改变运行 | 保留次级信息 |
| `nodes`、`links` | 节点及控制边；新稿默认链，UI保存按nodes重建相邻links | 空图/空边服务端也会补默认；选择即归一化，分支边可能在未保存前已丢于草稿 | 保设计能力，但不假称自由DAG编辑；见下表 |
| `agent_ids`、`tool_ids` | 由最终节点/对话Agent及全局工具派生；不采信同名payload字段 | 公开snapshot过滤失效ID后计数，不代表无失效引用/真实可执行 | 只读关系须保失效诊断；工具权限唯一入口沿F3A |
| `version_history`、`created_at/updated_at` | 历史和时间，无本片普通编辑框；preview归一化也生成新updated_at但不落盘 | UI不发历史/时间；后端可接创建时间/历史；具体版本规则交F4B | 保版本证据，不把预览时间当保存成功；不扩审迁移 |

来源和recipes是**读写形状不对称**：公开GET的nested source/recipes不能原样POST当安全复制。env同时支持两形状，不能据此推其他字段也支持；未知顶层扩展在前端已知字段重建/后端白名单输出时会掉，未确认语义前不合并或批删。目录/来源/环境会经`sync_workspace_nodes_with_overview`同步每个已知kind的首个节点；命令是否强制同步又取决于flat键是否出现。当前没有清楚的“项目默认—节点显式覆盖”合同。后续先定义有效值与来源，再单片修改，不能加第二套默认合并器来遮掩差异。

### UX01F4A 节点身份、执行者和设计动作

| 字段/动作、消费者 | 当前输入、默认及输出 | 能力边界与后续需求 |
| --- | --- | --- |
| `node.id/kind` → node_mutations/schema | id缺则生成；kind由新增种类选择，未知kind保留并warn；无普通ID改框，插入新节点后选择它 | 身份不可用标题替换；重复ID validator阻塞；具体种类参数交G，不把未知kind直接删掉 |
| `title/status` → node_editor | 标题默认种类标题；status选ready/draft/blocked/running/done，服务端无枚举限制 | 模板允许编辑running/done不是运行证据；设计页应区分定义标记和持久运行，不能手写状态冒进度 |
| `handler.mode` | human/agent/system；默认/非法human；模板补推荐但保明确human/system | 真实node_runner按kind+mode+agent_id选agent/job/skip；human不等人工暂停，system不等必须Agent；validator却对所有非human要求Agent，需后续统一合同，不能只改标签 |
| `handler.agent_id/name` | 全局Agent下拉可空；选择Agent同时用其名称覆盖显示name；手改name不换agent_id | 不复制prompt/key进表单；失效/停用必须可识别；validator agent停用blocking/system停用warning，与执行门禁区分 |
| `handler.handoff`、节点`notes` | 交接说明/备注，默认空；纯草稿字段 | 保不同语义，说明不是完成回执，不冒充实际交接 |
| `handler.output_key/max_iterations/timeout_seconds/output_format` | 当前基本编辑器无这四个独立控件；后端归一化保有限合法值，前端workspace_node_catalog归一化仅保mode/id/name/handoff/output_key，丢这三个预算/格式字段（E2） | 输出键与预算来源沿F3A；完整字段往返/I/O交G，保高级编辑需求，不能靠界面隐藏直接丢值 |
| `node.config`、`output_key/input_mapping` → node_editor_actions/通用renderNodeField | 种类定义提供配置控件，映射有结构化和高级文本；编辑即归一化/清校验 | 此处只确定归属/消费者，所有种类参数/映射删除清空/前向引用交G；不称逐参数已闭合 |
| `position/runtime` → schema/前端node normalizer | 存储可含布局及运行痕迹，模板normalizer不自动清历史；拓扑预览按数组自算位置 | 定义与运行分开；复制/新run不能继承旧状态，迁移责任交F4B/G核验 |
| 插入/上移/下移/删除 → toolbar与canvas actions | 按数组改顺序并重建相邻links；至少留一个节点；未保存不发写请求 | 保可操作编辑；重排后的引用是否仍有效要校验，不能只看图连上 |
| 新建/Repo-Paper-Idea seeds/重建starter → app/state | 新建与seed重置草稿；重建覆盖nodes；无脏稿确认/撤销事务 | 应分别表达“新模板”“改来源”“重建步骤”，保未保存离开/取消合同；复制全局模板入口未发现，不凭计划虚构 |
| 节点列表/顺序卡/阶段图/拓扑点选、搜索前后项 → canvas/search/node_list | 同一selected node；搜索改本页内存且可Enter/Shift+Enter；多处可上移/插入 | 保快速定位；重复展示/动作是消融候选，未完成对照前不删；不能变成必须逐层点击 |
| 边检查器/节点映射/补缺映射/建议修复 → canvas、repair_actions | 编辑仍落同一nodes.input_mapping/output_key；repair只改草稿再preview，不自动save；批量patch可部分成功 | I/O面板同事实应统一入口，保显式修复/失败反馈；完整引用语义交G；修复需绑定草稿版本，不能用迟到建议 |

### UX01F4A 顺序编辑、拓扑展示和真实执行

现编辑器叫“顺序链路工作室”有合理边界：`normalizeDraft/payloadForSave`均按nodes重建links，选择已有分支模板时草稿就成为顺序链；两条recipe也被折成一条。后端`normalize_workspace_links`去无效/自环/重复边，有有效子集则保留，否则补顺序链，[]不能代表独立节点。validator读取raw links检查端点/重复，但contract用normalized links；preview拓扑又可读raw links。同一响应不同投影不一定代表同一图。

后端topology_preview可以画branch/join/cyclic和数据引用边，不代表UI能自由连线，也不代表正式推进支持任意图。validator没有把cycle/branch可执行性作为专门blocking；cycle_node_ids是Kahn未访问集合，可能含环下游。正式`state/workspaces/workflow.py`当前按nodes数组取可执行前缀，只支持单Job、Job→eval.report Agent、特定两Agent链；更长/任意DAG、并行、循环执行均不能靠模板ready承诺。这里是E2接口边界核对，没有启动或验收这些流程。

设计上要让用户清楚“顺序编辑能做什么、结构图解释什么、本项目实际支持运行什么”。现有配置/设计能力需要保留，未支持的运行形状显式说明；不能用只读拓扑替代编辑器，也不能引入第二推进器补界面幻觉。

### UX01F4A 动作、API与异常合同

| 用户动作/真实接口 | 当前处理与输出 | 要保留或修正的合同 |
| --- | --- | --- |
| 读目录/单项：GET `/api/workflow-templates`、`/{id}`，status也带目录 | public模板/派生计数；单项缺失404；目录按时间倒序 | 失效引用不能只过滤后显示0；来源/字段完整可读，不把目录状态当本次校验 |
| 校验：POST `/api/workflow-templates/preview` 或 `/{id}/preview`；GET `/{id}/preview` | collection处理未保存body，item合existing；返回workflow_template/validation/preview，不保存/不跑任务；collection ValueError400、item404 | 显示归一化结果、具体问题/节点、恢复入口；绑定请求对象和草稿版本；不能叫真实环境测试 |
| 保存：POST `/api/workflow-templates`；PUT `/{id}`，POST item是保留兼容更新 | UI先preview，只有status严格等blocked才拒；warning允许，缺validation也能继续；CRUD自身不调用validator | 草稿存储与可运行门禁分别设计；现在blocked连draft也存不了，不能称已有“保存任意草稿”；直接API绕开预览不是产品验收路径 |
| 选择/取消/刷新 | 选模板从目录重建草稿并清校验，无确认；没有独立取消按钮，切换/新建不是安全取消；草稿未持久恢复 | 未保存改动明确放弃/保留；返回精确模板/节点，不串项目；浏览器前后退完整路径本片未验 |
| 删除：DELETE `/api/workflow-templates/{id}` | 浏览器confirm，取消无请求；后端删首个匹配，不查项目占用，不级联删项目/run；成功读目录选首项 | 保危险确认和影响说明；项目快照不能被删，失去升级来源的影响F4B查；占用保护非已实现 |
| 复制/应用 | 未发现全局模板clone按钮/API；既有模板→实例快照是另一能力 | 不把“复制历史JSON”或照抄GET当安全克隆；实例应用/冲突交F4B/G独立调查 |

validator查节点身份/重复、非human Agent绑定、required工具、输出键冲突、原始边端点、contract缺输入。未知kind/未知或停用授权工具/失效模型引用等多为warning；空Provider不报缺连接，也不检查真实目录/主机/模型、工具实现和服务可达。它不是完整运行预检。UI的I/O健康、四张概览卡、目录status与服务端validation各有来源；例如概览AI卡可以用“当前选中Profile/全局已配置数量”回退，不能把它当本模板有效路由事实。应减少重复绿灯，同时保具体问题来源；未校验时“没有发现阻塞项”也不能暗示通过。

**新增与保存错位（G45，E1+E2）**：`newDraftState`已清selected id，但`renderWorkspaceWorkbench`总先渲染隐藏的use面板；`renderWorkspaceUseMode`发现没有选中模板就回填第一已存ID。manage renderer本身不自动选首，不能误归因Agent/Tool同一函数。实际非空目录点新建有新Repo草稿，却仍active template-a；保存发preview A、PUT A而非POST。空目录才观察到POST。合成preview明确warning让保存分支可达，不证明真实默认空Agent链一定能过validator，真实覆盖/落盘后果仍E3。

**在途保存竞争（G27/G45，E1+E2）**：save在await preview前捕获payload，await后重新读selected id。实际A编辑→保存→拦截器延迟preview响应→普通点击B→释放响应，最终PUT B携带A的id/name/nodes；后端固定existing.id会保B身份，不能靠body.id救回目标。preview也没有对象/草稿版本检查，busy仅作提示，迟到校验可落到已切换/已编辑草稿。后续需以不可变目标+草稿版本贯穿校验/保存/结果展示，对失效回执拒绝应用；本片没有修代码。

### UX01F4A 实际证据、消融和交接

浏览器Chromium140.0.7339.16，旧生产web全网络拦截，**15观察/809请求=791GET+11POST+7PUT**，pageerror/requestfailed/未知API501均0。1440实际编辑→preview/PUT、分支转顺序/recipe平铺、draft blocked不保存且保稿、warning保存、preview/save503保稿、切换丢稿、在途A→B错位、非空新增误PUT/空目录正常POST、删除取消/刷新；1024/768仅名称原生click→填值→单Tab到来源→合成保存。**390连模板列表普通click也因viewport外超时失败1**，未继续名称编辑/保存；不force/改DOM/停轮询/放宽门禁/重跑到绿，不称四宽全流程或完整键盘通过。长内容、节点控件逐个操作、确认删除、back/forward与真实保存/重启没有验收。

路由合成公开模板、Agent和validation响应，CRUD只是本脚本内存响应，不读真实config/key/runtime，不起后端/Job/Provider/SSH。夹具原有3节点分支/2recipe是用于发现前端写出损失的输入，回执不复制完整后端normalizer、validator和version_history；因此request证据可证明错误目标/形状，不能证明真实定义已被覆盖、真实警告或运行可用。8项首轮观察后记录函数name冲突、第二轮rename遗漏NameError、第三轮dict同名冲突均保原脚本/JSON/log；第四轮仅修本地记录器，保上述390产品失败。7份图（含首轮脚本故障图）与脚本/请求、后端只读报告仅`/tmp/relaygraph-ux-audit/ux01f4a/`；沿dev_work不可访问例外未修复/重建。主代理看race/blocked/390三图，图主要编辑壳和消息，错位由请求与源码证明。

保全部旧生产入口/API、顺序编辑、图/列表投影、映射及诊断修复；无替代实现，不能凭控件多就删设计能力。后续消融固定同一模板及故障，对照节点列表/顺序卡/阶段/拓扑的定位、编辑、状态来源及副作用，再减少重复；全局Agent/工具/模型编辑复用F1–F3，不在模板复制第二套目录。只改三正式docs和本片相关逐文件结论，稳定规格/AGENTS/正式前后端未动；独立只读监督与文档检查后提交推送。唯一下一片F4B核版本/快照/差异/迁移，仍不开始整站画稿；全产品调查及G27/G40/G41/G45保持开放。

### UX01F4B：模板历史、项目快照与明确采用

对应R02/R03/R05/R09/R11/R12/R13，关联G10/G17/G19/G26/G27/G40/G41/G45及新增G46。开片列的G16实际是导入门面问题，不是模板迁移缺口，本片未牵强更新它。用户要知道“模板改了，旧项目会不会变；想采用时会改什么；原运行还能不能回看”。这里区分五个动作：保存全局模板、比较项目模板基线、在原项目采用、另建迁移草稿、复制审计摘要；不能统一叫“更新版本”。本片只调查，不改后端/正式界面，不宣称迁移安全已验。

源码链：[history renderer](../web/workflow-template/workflow_template_version_history.js)/[history actions](../web/workflow-template/workflow_template_version_history_actions.js)和[template_review](../web/workflow-template/template_review_actions.js) → [app.js](../web/core/app.js)；[diff renderer](../web/workspace/workspace_template_diff.js)/[migration actions](../web/workspace/workspace_template_migration_actions.js) → HTTP → [workspace crud](../total_control/state/workspaces/crud.py) → [模板schema](../total_control/workspace/schema/templates.py)。普通保存消费者另见[cockpit payload](../total_control/workspace/cockpit/payload.py)；运行冻结只限核[workflow_records](../total_control/state/workspaces/workflow_records.py)、[types](../total_control/orchestration/types.py)与[run_store](../total_control/orchestration/run_store.py)的已有计划，不扩审所有运行行为。F4A字段、F1–F3模型/能力生效合同继续引用前片。

### UX01F4B 字段与事实来源

| 字段/对象 | 用途、输入来源与默认 | 校验、联动、保存影响与处理决定 |
| --- | --- | --- |
| `version_history[].schema/id/mode/recorded_at` | 全局模板的轻量变更记录；schema固定version_record.v1；mode默认update；缺id按时间/mode生成，产品生成时加template_id | 按recorded_at字符串倒序、最多20条，无ID去重/严格日期/mode枚举；时间精确到秒，同秒同mode可撞ID（E2路径/E3实际并发未验）。不能当发布版本号 |
| 历史`template_id/template_name/from_updated_at/to_updated_at/from_node_count/to_node_count` | 记录当时模板名、前后时间与节点数量；只读摘要，无完整定义查询入口 | id字符串截80，数量safe_int；无revision/hash、作者、前后完整定义或回滚；保可读出处，不能声称可恢复任意版本 |
| 历史`summary/changed_fields/added_nodes/removed_nodes/changed_nodes/warnings` | 结构和metadata变化摘要；summary含变化总数/节点增删改/边增删/拓扑与顺序标志 | changed_fields最多12；三类节点各8、每changed节点字段8、warnings12；不含全文变化值。UI显示前4条，计数仅所保留历史条数，不是项目全部变更次数；保审计，长内容需明确摘要/截断 |
| 模板`updated_at`与历史生成 | create记录创建；update检测diff或name/description/status/brief/tags/notes六metadata后才追加 | 未检测变化可无新record；normalizer/startup也能更新时间。不能以时间变化当不可变版本；无变化更新可接收替换history，有定义变化则用存储旧history追加，非受保护追加日志 |
| `template_snapshot` | 项目保存的采用基线；含template_id/name、source/env/recipes/model/nodes/links、按引用ID从当前全局目录取Agent/Tool深拷贝、created_at | 无模板updated_at/发布revision/hash、独立workspace_dir、metadata全文；created_at是构建时间，每次GET当前diff也会新建，不是模板发布时间。保基线/来源；不能用捕获时间冒发布版本 |
| 项目`template_id/template_name/inputs/nodes/model/agents/tools` | 来源引用、项目输入和实际配置；创建时模板复制，之后项目可独立修改 | diff不比较实际项目覆盖，只比较项目template_snapshot和当前目录快照；模板修改不自动改项目/run。普通PUT可传template_snapshot，无独立采用审计门禁（E2），不当不可篡改基线 |
| `RunPlan.workspace_snapshot/package_snapshot` | 提交时冻结项目及执行包；已有RunStore保存和恢复读取 | migration服务无改旧RunPlan调用；这只是源码边界佐证，未运行真实迁移/恢复。本次项目变化不等于旧run被改，也不能据此说当前项目展示完全一致 |
| diff `schema/status/changed/summary` | GET `/api/workspaces/{id}/template-diff`；status same/changed/missing_template/missing_snapshot；summary计节点/字段/能力集合/边变化 | same只表示有限比较范围内无差异，不表示项目无覆盖、执行等价、已发布同版本或可运行；没有snapshot仍可changed=false而status missing_snapshot，状态与计数分开 |
| diff `workspace_snapshot/current_template` | 比较两端的id/name/捕获时间/节点数/Agent与Tool IDs | 当前端按当前目录能力深拷；同ID能力正文变化不会计入diff。保两端来源，不能把0变化说成所有指令/授权都一致 |
| diff `diff`、`structure_preview/link_preview/topology_preview` | 节点/边增删改、字段名、能力IDs，以及只读结构图 | diff节点/增删边列表最多24，结构/边预览每边最多40；UI再限节点18/边16及少量摘要。复制计划也非完整diff备份；多投影应共用事实和明确截断，不为美观假称全文可用 |
| plan `schema/status/strategy/risk_level/changed_count` | migration_plan.v1；建议状态ready/review/manual_review/blocked与no_action/sync_safe_fields/sync_draft_then_validate/create_new_workspace/manual_rebuild/inspect_changes | 这是后端建议，不是已执行事务或真实检测结果；“安全”命名不能代替覆盖冲突证明。UI对inspect_changes回退逐项检查，保建议与来源 |
| plan `can_auto_apply/can_manual_apply/can_create_draft/apply_scope` | auto始终false；manual=changed且无增删节点/边拓扑或边列表顺序变化；draft=changed或missing_snapshot | recipe/映射/config改变仍可能manual=true，建议先草稿与按钮资格并非同语义；missing_snapshot虽blocked仍能新草稿。scope只是分类摘要，不限制normalizer重建范围；不可据此承诺只改列出的字段 |
| plan `recommended_action/blockers/warnings/steps` | 建议文字、缺来源/链路/映射/能力提示；steps含id/label/status/scope/detail/items/fields/agents/tools | step items至多12，UI显示前4步；validate-before-run是提醒，不会执行validator/门禁。保具体恢复入口，复杂解释放帮助/阅读区 |
| `template_migration_history[]` | apply后最多12条，id/applied_at/mode/template id/name/旧新snapshot捕获时间/diff_summary/apply_scope/risk_level；新草稿附source_workspace id/name | 存在项目JSON而非RunStore追加表；普通保存和部分chat normalizer输出不保此字段，存在丢记录风险E2/E3。保追溯是需求，尚未真实持久化验收 |
| `source_migration` | 新草稿来源项目id/name、created_at、模板id/name；只读 | 普通保存/再次apply无保真保证。不能用仅顶层runs/chat清空推导全部节点runtime已清；新草稿必须列清保留/重建/重置字段 |
| 历史复制payload | schema version_history.copy.v1、copied_at、template id/name、dirty、source_type、node/link/history_count、updated_at和history摘要 | 优先当前草稿标题/节点数，history仍来自已保存摘要；可混dirty标题和旧历史。真实浏览器已复制观察；保标记“审计摘要”，不是备份/复制模板/指定版本采用 |
| 计划复制payload | schema migration_plan.copy.v1、workspace id/name、template id/name、diff_summary和migration_plan | 同workspace缓存有plan就直接复制，无新鲜度/revision检查，不含完整snapshot/结构diff。保诊断导出，但不能写“复制即可拿到全部变化” |

### UX01F4B 差异盲区与采用边界

`workflow_template_snapshot_diff`按节点ID字典比较signature：kind/title、handler mode/agent_id/tool_id/output_key、node output_key/input_mapping/config/runtime。**不比较nodes数组顺序**、节点status/notes/position、handler name/handoff/max_iterations/timeout_seconds/output_format；Agent/Tool只比ID集合，不比同ID指令、预算、模型、授权/停用。source/env/recipes/model/links按字段比较，边的有效集合/列表顺序另算。公开“same”不是完整执行定义等价；节点顺序影响F4A正式执行前缀，这个漏项不能只改文案掩盖。

原AST纯方法17场景实测：同ID Agent指令/Tool停用、handler交接/预算/格式、只倒置nodes保原links，均可same；最后一个结构预览顺序已不同而topology_changed仍false。隔离探针仅改独立顶层workspace_dir、未跑normalizer时，不进snapshot或版本record；真实保存可能先同步node.config而被捕获，该路径未验。改模板名有metadata历史record但项目diff仍same。runtime变化会被计入、links列表反序会被计入；不是所有排序/历史变化都被忽略。缺snapshot blocked仍可draft，recipe变化策略先草稿却manual=true。这些是隔离纯函数观察，不是已修复、API落盘或真实运行证据。

| 动作/接口、输入输出 | 当前处理/门禁/副作用 | 需求、风险及后续验收 |
| --- | --- | --- |
| GET `/api/workspaces/{id}/template-diff` | 取项目template_snapshot，对当前目录+全局能力即时构建快照；项目不存在ValueError→404；不写项目 | 明确比较范围/基线与当前配置覆盖三者；响应按对象+请求版本应用，区内失败保恢复入口 |
| POST `/api/workspaces/{id}/template-migration/apply`，输入`confirm` | 仅真值确认，字符串false也可过；不含expected revision/hash/request_id/字段选择；错误ValueError均400；status same返回200且applied.ok=false/status=same；真正应用返回workspace_id/workspace/diff/applied.record | 应绑定用户审阅版本和项目修订，明确冲突；区分“无需应用”和“已应用”；不把确认框代替幂等/保护 |
| apply服务实际修改 | 锁内重算最新diff，manual资格通过后整份`normalize_workspace_instance_from_template`；按变化选env/recipe，必要恢复旧model/能力，始终恢复旧source，替换基线并记录迁移，锁外save_workspaces | 不是按scope逐字段补丁/三方合并。即使只变model也重建nodes，模板raw config/handler/runtime可能覆盖同ID项目值。没有active-run拒绝、真实校验或跨存储事务；真实覆盖/写失败/并发后果E3待验，旧run计划未被此方法重写 |
| POST `/api/workspaces/{id}/template-migration/create-draft`，输入`confirm/name?` | 原项目/当前模板存在、diff非same且can_create_draft；成功201；ValueError400；返回源workspace_id、新draft_workspace_id/workspace/diff/source_diff/created.record | 名称可自定但现UI不提供；默认旧名截48＋迁移草稿。无expected hash/request_id，重复请求可建多份（E2）；独立验幂等再正式开放 |
| 新草稿来源与重置 | 旧inputs/目录/env/首recipe/notes/tags＋当前模板model/能力/节点；清顶层id/时间/runs/chat/execution/history，再加来源记录 | 是混合草稿，不是完整新模板克隆；existing_seed仍有nodes，模板有runtime则沿模板，否则可能回旧同ID节点，未显式逐节点清历史。保旧项目不变但新草稿仍须检查来源/门禁 |
| 普通项目PUT与chat消费者 | 普通保存用normalizer白名单，未补回migration_history/source_migration；又可接收template_snapshot | 追溯保存边界缺口G46；需实际正式入口正常保存/重启验证，不能靠前端临时缓存补丢失记录；完整编辑在G2调查 |
| 删除/改名全局模板、目录启动 | CRUD不级联项目/RunStore；删除后diff missing_template，不能apply/draft；改名可有历史却diff same，项目名称仍旧；删空目录后启动可重建默认模板 | 保现有项目事实，不暗示删除项目；来源失效显示准确修复动作；删除保护/启动回填本片静态核实，未执行重启。未知创建template_id回退首项留G1核 |

当前历史只保摘要，缺完整定义查询、指定旧版本采用/恢复、全局模板克隆；不得虚构这些能力。是否确需完整版本库应按用户任务单片确定，优先复用既有快照/哈希与持久事实边界，不默认引入Git平台、另一套前端revision或第二迁移器。

### UX01F4B 旧页面实际可达性、错误与返回

正式消费者只有`renderWorkspaceChainInspectPanel`调用`workspaceTemplateDiffMarkup({readOnly:true})`。所以即使plan两资格都true，也**只显示复制计划，没有应用/新草稿按钮**；helper和API存在不等用户可操作。只读诊断职责合理，但产品仍需要一个明确的项目配置采用入口，不能在新版继续漏掉；候选责任归项目流程设置，模板目录仍管全局定义/历史，具体页面合同待全域调查。没有往DOM补按钮来假装旧页可迁移。

GET diff目前按selected workspace ID接回执，能挡别项目结果，却无同ID请求版本；实际旧网页普通两次切入诊断，在第二次新回执显示后释放第一次旧回执，旧文本重新覆盖。失败显示错误但区内无重试，切模板页签再回诊断才触发新GET。复制计划在同项目缓存已有plan时直接使用缓存，不会刷新；没有plan时helper会读取。合成same/changed/missing_template/missing_snapshot均实际显示；用户不能用“快照一致”判断项目没有覆盖。

未接入写操作的helpers另用原JS隔离9场景：apply等待期间假callback选择B，旧回执仍select原A且读B的node选择；same/未应用回执仍提示“已应用”；两次显式createDraft helper调用发两请求；body只有confirm；匹配workspace缓存复制不刷新、错误向app catch传播。这些是**假callback的辅助方法观察**，不是浏览器切换/双击真实迁移；正式写入口不可见，未用强制调用把它冒充可用产品流程。后续应有明确目标/草稿版本、在途操作与准确返回保护，以及unknown响应核对，不能只加按钮。

### UX01F4B 证据、删保与唯一下一步

隔离Python直接抽原schema/工具纯函数AST、无产品import/服务/normalizer/落盘、禁socket，17场景符合预期；原JS helpers VM配假网络/选择/clipboard，9场景符合预期。后端只读报告形成时尚未跑这些探针，保原报告时间边界；正式结论以本节新增证据分级为准。没有真实迁移/配置保存、删除/重启、Provider/SSH/Job/RunStore变更验收。

真实Chromium140.0.7339.16旧web全网络拦截，**13观察/536请求全GET**，pageerror/requestfailed零。1440真实按钮复制历史和计划到浏览器clipboard（loopback权限准备，非改clipboard实现）、5历史显示4/dirty草稿标题与5摘要、只读隐藏写动作、diff503和显式换页恢复、四状态/同项目迟到覆盖/跨项目复制归属。1024/768仅选模板→复制历史→单Tab，不是完整迁移/键盘/长内容验收；**390选模板普通click仍outside viewport超时失败1**，后续未通过，不force/改DOM/停轮询或重跑到绿。

两个项目选择启动了SSE旁路：合成events是关闭的注释流，未建模的events/replay各1次共**2个501**，后续runs返回合成空列表；这是夹具未覆盖的回放链，不是产品API出错，也不影响本片模板diff/clipboard请求证据。没有为清501重跑，不以此宣称SSE/运行回放通过。首轮脚本在runs找use内历史、次轮进入use未开details，均不可见超时；第三轮仅纠正真实驾驶舱→打开历史summary→点项目入口，保两轮源/JSON/log/图，未绕过产品门禁。9图含两张早轮路径错误图，主代理看diff/late/390图；迟到覆盖由DOM观察/请求支持，late图主要壳不冒全文证据。全部脚本/报告/结果/图仅`/tmp/relaygraph-ux-audit/ux01f4b/`，dev_work不可访问例外未修复/重建。

保历史复制、diff读取、现有API/写helpers和快照/RunStore，各有消费者；没有替代实现，不删旧入口。版本历史、基线diff、配置编辑和运行快照是不同事实，不能因都叫“历史/版本”合并；多图/摘要及重复计数是后续固定输入/故障消融候选。新增G46记录差异漏项/迁移覆盖/来源保存缺口，G27另记前端回执/选择；不把文档登记算修复。三docs/台账经独立只读监督和文档检查后提交推送，稳定规格/AGENTS/生产不变。F4B交接时下一片为UX01G1（现已限定调查，当前指针见文首）；G2设置/覆盖、G3节点参数/I/O、G4发现/执行包、G5运行/历史为待拆调查方向，随后H维护，尚未形成全站布局。

### UX01G1：项目入口、目标输入与创建回执

对应R02/R03/R04/R05/R12/R13，关联G09/G10/G12/G17/G19/G26/G27/G40/G41/G46。原开片G14是Transfer交接，不是资料线索或创建问题，本片不牵强更新；G45全局定义新增错用旧对象也不等本片新项目晚回执选择问题，后者归G27。用户要分别完成“继续已有项目”和“从新目标建立草稿”，不是先理解实例、Starter Chain、能力底座和执行包。本片只查字段、动作与已有消费者，不预定整站布局或实现新向导。

源码链：[旧HTML](../web/index.html) → [launcher actions](../web/workspace/workspace_launcher_actions.js)/[shell actions](../web/workspace/workspace_shell_actions.js)/[list actions](../web/workspace/workspace_run_actions.js)/[navigation](../web/core/app_navigation_actions.js) → [app.js](../web/core/app.js) → [POST routes](../total_control/http_api/post_routes.py)/[Handler](../total_control/handler.py) → [create_workspace](../total_control/state/workspaces/crud.py) → [模板实例schema](../total_control/workspace/schema/templates.py)/[普通payload](../total_control/workspace/cockpit/payload.py)/[inputs schema](../total_control/workspace/schema/recipe.py)。发现/推进只核[discovery](../total_control/state/workspaces/discovery.py)/[automation](../total_control/state/workspaces/automation.py)最早副作用与返回，不重审完整算法/运行；公开回执另核[monitoring](../total_control/state/monitoring.py)、[records](../total_control/state/workspaces/workflow_records.py)、[资料计划](../total_control/workspace/cockpit/discovery.py)。

### UX01G1 字段、归属与实际采用

主启动器只有五个文本控件和一个模板选择；没有独立名称、主机、目录、模型或CPU/GPU编辑字段。提交体仅`{template_id, inputs}`，资源区选中主机不会随这个请求发送。高级实例表单是第二个创建消费者：空workspace_id时`submitWorkspace`同样POST集合入口，但它有回执ID检查、旧monitor失效和跨项目选择保护，不能将启动器缺口套给所有保存；其完整字段/覆盖往返留G2。

| 字段/控件 | 用途、输入来源、必需条件与默认 | 联动、校验、保存影响与决定 |
| --- | --- | --- |
| `workspaceTaskGoalInput` → `inputs.goal_text` | 新研究目标；默认空，前端trim；五类输入任一非空即可创建，并非目标独有必填 | 后端goal空串可回退brief/idea/旧goal；空白串先真值选中再trim，和空串不同（原纯方法已观察）。模板路径brief可回退模板brief；不能把模板说明冒充用户已确认目标。保用户目标语义，名称允许生成/后续编辑 |
| `workspaceTaskRepoInput` → `inputs.repo_urls` | 候选仓库多行；可选；前后端trim、去空、去重，保持顺序 | 不按逗号拆，不校验URL/协议/可达；全部存inputs，仅第一项进source.repo_url/默认节点。多候选不等多仓库已接入；保候选与主来源区分 |
| `workspaceTaskPaperInput` → `inputs.paper_urls` | 论文/资料URL多行，可选，同仓库列表解析 | 只存线索，不上传正文/下载PDF或自动解析。第一项进source.paper_url，其余仍可被资料计划消费；保资料入口，不与repo地址直接合并 |
| `workspaceTaskReferenceInput` → `inputs.references` | 数据集名、路径、链接及参考线索，可选 | 模板创建同时复制到项目顶层references；后续资料计划按链接/路径/查询解释，并可能用本机Path判断。不是host_id+path权威数据位置或已验证数据；分清线索与运行输入，后续类型化需求留G3/G4 |
| `workspaceTaskContextInput` → `inputs.context_blocks` | 限制、成功标准、审批要求/已有发现，多行可选 | 不是notes的已证等价字段；含路径/数据关键词还可被发现计划读取。仅context也过hasInput，但source_mode仍idea；保明确用途，不能以简化为由合并成一个无语义大框 |
| `workspaceTemplateSelect` → `template_id` | 默认目录首项；目录空显示暂无模板并disabled；前端要求非空 | 选模板只写selectedWorkflowTemplateId/重绘，不自动改已存项目。创建时复制实际模板snapshot；后端未知ID会静默取首项，必须核响应实际template_id。保流程选择，缺项应指向模板配置唯一维护位置 |
| `inputs`容器及别名 | 后端dict inputs存在时只取该对象；否则读扁平payload；兼容repo_references/paper_references/context | nested空dict不会与顶层typed资料merge。references-only顶层不触发模板创建分支，而context_blocks会；UI不发送这种混用形状。单数repo_url/paper_url是普通表单合同，模板创建不当plural aliases；保持兼容但不能猜合并 |
| `inputs.source_mode` / `source.type` | repo/paper/goal推断repo/paper/idea/mixed，context/reference不参与；显式非法值归idea | mixed的默认链类型映射idea，但选模板的nodes不因来源模式自动换模板。普通创建另有legacy source_type，可能与inputs来源不同；保来源与实际流程区分 |
| 项目`name/brief/id` | 启动器不发name；模板创建默认brief优先目标，再模板brief；name取brief首行60字，再模板名；新ID时间＋随机8位 | 显式API name不限重名/同长度；payload.id不决定新ID。普通创建有repo尾名/Paper/40字等另一规则；201不证明按目标唯一建项。保用户可读名称与稳定身份，内部ID按需诊断 |
| `workspace_dir/env/recipe` | 主启动器不收，模板路径从模板复制，API可按flat目录/env/命令等覆盖 | 创建不查目录/权限/host、不mkdir/clone/装环境或执行命令；普通表单无模板路径另补默认。需按流程显示必要设置，编辑和来源合同G2/G3再核，不能靠创建后全绿掩盖缺项 |
| `model/agents/tools/nodes/links` | 模板创建直接取模板snapshot，**忽略payload中这些覆盖**；普通创建可以接收归一化 | 顶层server_id/provider_profile_id/GPU/data_roots也非项目创建字段，不要添加实际未保存的选择控件。项目覆盖须正式接口接线；模型/密钥仍归全局连接和项目引用，不重复输入key |
| `status`与就绪 | 模板实例缺省ready，普通创建缺省draft，均可接受显式字符串；不做运行readiness校验 | 缺模型/有效主机/目录可存声明，不代表连接、数据或执行可用；“已保存”“需补配置”“可运行”必须分开。坏配置真实创建往返未验，不能把字段被忽略叫校验通过 |
| `template_id/name/snapshot` | 模板路径保存实际所选定义及捕获快照；目录后来修改不自动改实例 | 无模板目录且无显式ID可落普通创建；有显式ID而空目录报错。采用/追溯沿F4B，不把创建时间当revision；优先展示实际来源而不是浏览器请求值 |
| `notes/tags/chat/execution/runs` | notes/tags可API传但主启动器不发；模板创建chat可归一，execution/runs取existing（新建为空） | 普通创建另能接收部分运行投影，但不等RunStore权威证据。此处只标输入边界，不展开历史/聊天编辑；归G2/G5，保留现有消费者 |
| 浏览器草稿/项目选择 | 输入事件调用saveLauncherDraft；实际save/restore都删`tc-workspace-launcher-draft`；selectedWorkspace单独localStorage | 选已有项目或创建回执hydrate调用的函数忽略workspace返回五空值。不能说已存项目inputs丢失；实际丢的是未提交新建输入/草稿恢复。新建草稿与继续项目应分任务管理，是否回填启动器不预先强定 |

后端数据线索的公开计划会汇集全部repo/paper、references、部分context，再作本机路径判断；有线索时dataset计划ready不等数据已下载/远端已验证。create不调用默认回填/执行，但回执不是纯JSON回显：先save，再refresh_workflow_records查询RunStore、生成execution/automation/cockpit及部分本机Path投影。保存后投影失败也可能回400/503；这类实际持久化后果仍E3，不能把所有失败都显示“没有创建”。

### UX01G1 入口、操作与副作用合同

旧工作台由侧栏按钮进入同一index文档；驾驶舱/运行/配置中心/实例编辑仍是同页mode切换，选择记localStorage，无pushState/URL路由/Back合同（E2；本轮记录URL不变，未实际验证整套前后退）。已有项目藏在驾驶舱历史details里，卡上重复模板/来源/节点/Agent/目录/命令/流程/诊断摘要；没有独立项目列表页/创建分步身份。不是让新版删所有摘要：保快速识别/继续，按任务消融多份状态与配置统计。工作台和配置中心独立页面身份仍是目标，尚未实施。

| 动作/接口与输入输出 | 当前处理、异常和保存影响 | 后续需求/删保决定 |
| --- | --- | --- |
| 仅建实例：POST `/api/workspaces` → 201 `{workspace}` | 模板非空且五输入任一非空才过UI；不调启动检查validator。后端按template_id/typed键分模板或普通合同，插内存→save_workspaces→公开投影；不调用发现/Agent/Job | 建立可编辑草稿，不强迫先完成全部运行配置。严格回执身份、实际模板/输入采用值、保存事实与就绪分别确认 |
| 建实例＋发现：上述201后POST `/api/workspaces/{id}/discovery/run`，`{apply_defaults:true,include_source:true}` | 发现服务先可回填并保存默认配置，可能clone/排Job；不是只读检查。第二步失败不回滚已建项目，后端完整发现留G4 | 分阶段显示“项目已保存，发现失败/待核对”，保原项目继续入口；不能让用户再点创建补第二步，也不能靠“安全”文案省略副作用 |
| 建实例＋推进：上述201后POST `/api/workspaces/{id}/advance`，`{force_run:false}` | 不是直接/run；服务可watch/review_failed，或发现、回填再blocked/run。200与201也不能代表整个流程成功 | 给实际下一动作与状态，不暗示创建就运行完；本轮只消费合成watch，不称默认新项目真实推进通过 |
| 启动检查 | 客户端基于输入、Agent绑定、安全kind、资源快照和run节点派生五项，显示就绪/警告/阻塞；不创建、不请求后端校验，创建也不强制先检查 | 可做辅助预览，不能当真实路径/权限/模型预检。保来源和明确修复入口，与已有运行门禁共享权威结果的接线留后续 |
| 创建中与重复提交 | beginAutomationAction有全局busy互斥并disabled三个创建按钮，结束恢复；Reset/输入/选择项目仍可操作。HTTP无request_id/idempotency消费 | 当前页防重复有效，不等多窗口/断线重试去重；绑定创建意图/草稿修订/返回目标，晚回执不能清新输入或抢项目选择 |
| 回执与错误 | 启动器只读created.workspace，未严格要求workspace.id；旧页消费合成201空JSON可走成功文案。异常catch按当前selectedWorkspaceId合并error.payload，统一“创建/推进未完成” | 区分创建未完成/已保存后续失败/未知结果，后续API提供请求查回；错误合并目标风险E2，不称本轮已复现跨对象错误写 |
| Reset / 取消 / 返回 | Reset清五输入、选择/执行节点、事件流并选首模板；没有创建取消/撤销HTTP能力。选项目也清五新建输入；未提交刷新丢输入 | Reset须清楚影响及草稿确认/可恢复性；取消浏览器等待不等取消创建/子任务。不要自动清掉已有运行或暗改配置 |
| 高级表单创建 | workspaceResetBtn清已有选择/编辑草稿，submitWorkspace空ID POST `/api/workspaces`；模板与普通源字段消费不同 | 有真实调用者，先保留；G2核新建/编辑/取消/返回全表单，不能把两个创建路径无条件合并或提前删除 |

后端无同名去重、无创建request_id，重复请求会新建ID；非dict合法JSON会当{}归一化。原create方法配假normalizer/save的分支检查证实：未知模板回首项、空目录显式ID拒绝/无ID走普通、references与context键分流不同、request_id不参与、save异常时内存insert未回滚。这只证明调用/分支/顺序，不证明真实normalizer、HTTP码或磁盘恢复。后端源码显示save之后构建公开回执可能失败，无正式按本次创建请求查回的合同；不能用按名称猜同一个项目。

### UX01G1 观察证据、失败保留与后续

未改旧web全网络拦截、Chromium140.0.7339.16、公开合成目录/项目；主轮**14观察/2115请求=2103GET+12POST**，pageerror/requestfailed/未建模501均0，另有观察脚本超时1。1440原按钮验证空输入/空模板拦截、五输入提交、仅创建不发现、503保输入重试、创建成功后发现503、advance的force_run=false/合成watch、busy防重但Reset/选已有项目晚回执、合成“先存后503”再创建两项。所有受理/保存/后续状态只在夹具内，不证明真实落盘/任务。1024/768/390仅目标原生click/fill/单Tab及刷新丢稿；不称四宽全创建/补充资料/完整键盘/长内容通过。与前片390模板列表失败是不同任务，本片不覆盖或推翻它。

主轮空回执场景预期成功却5秒超时；保截图/原脚本/JSON/log。实看错误为201 `{}`缺application/json头，被产品正确拒绝为非JSON，是夹具错误，不是身份校验已有能力。**独立补观察**只为该场景显式补匹配真实Handler的JSON响应头，不改产品/断言门禁：**1观察/132请求=131GET+1POST**，无pageerror/requestfailed/501/观察失败；此时201空对象实际仍提示“实例已创建”，佐证启动器缺身份检查。主轮失败不抹除，不重跑整套或把合计请求写成一次全绿验收。

原recipe/parse_line_list纯AST＋原create方法配假normalizer/公开投影/save，最终17场景（8个原输入纯函数场景＋9个假normalizer/公开投影/save的创建分支场景）符合预期、禁socket、无产品import。首次2场景时误将空白goal与空串当相同，断言失败；保pure-initial.py/results/log，只修观察预期并增加空串独立对照后17，未改业务或跳过断言。后端只读报告形成时尚未跑这些探针，保原时间边界。10图含主轮响应头错误图；主代理实看390、发现失败后的执行区和补回执图，后两图主要捕获自动定位后的执行壳，具体消息/身份以DOM和请求观察为证，不冒称截图显示全部错误正文。

本片只改三docs/相关台账；全部脚本/报告/结果/图仅`/tmp/relaygraph-ux-audit/ux01g1/`，沿dev_work不可访问例外不修复/重建。没有真实config/key/runtime/服务/Provider/SSH/Job、真实创建/保存/重启或发现恢复验收。保所有创建消费者、列表/输入/编辑/API，不引入框架、第二保存器或新的前端状态事实；启动器多处创建建议/项目卡重复诊断只作消融候选，等页面合同后按固定任务比较。G09/G19/G27/G40/G41等保持开放，不把调查登记算修复。

唯一下一片UX01G2A：项目基本资料、来源与运行设置编辑需求调查，只到基本表单（名称/状态/目标与来源/资料/目录/环境/命令）的读写/保存/取消/返回；G2B项目Agent/工具/模型覆盖、G3逐kind节点参数/I/O、G4发现/执行包、G5运行/历史、H维护为后续待拆方向，全域闭合前不画整站或迁生产。

## 0H. UI02 历史方案与证据（已退出当前执行路线）

以下保留当时设计取舍、接口线索和历史证据便于对照；“当前/下一片”等当时措辞不再作为执行指针。特别是把每卡信息默认下沉主机详情、只读页面先行的安排，须按上述用户任务重新审查，不能直接沿用。

### UI02 当时的页面安排（历史对照）

### 首页的任务：先看机器与运行，再决定下一步

用户否定UI01功能卡首页：它增加查看资源的点击，放大研究工作台而弱化了日常监控。UI01的四宽点击通过只证明入口能用，**不能证明信息优先级或产品方向正确**。当前默认页改为监控台，不再保留大工作台卡或功能介绍首页；研究工作台仍是完整产品的一个功能，并可从所有页顶栏一键进入。稳定规格的组件/状态/输入身份未改变，生产页面暂不迁移。

产品服务个人研究者/小实验室的三类日常任务：① 打开即知道机器是否可用、资源是否紧张、任务在做什么；② 定位主机→GPU/进程→本次任务/日志，决定是否需要操作；③ 从目标开始研究流程，准备文件、等待任务、获取结果。日常查看无需先创建研究项目；有研究流程也不应绕过资源、路径和结果证据约束。

    RelayGraph    监控台 / 研究工作台 / 远程任务 / 文件传输 / 活动 / 配置中心
    监控台                                             刷新快照
    采样时间（紧凑）                       异常时局部反馈，无成功/30秒常驻块
    连接主机 / 空闲GPU（采样范围） / 运行与排队任务 / 需关注主机
    全部主机                                     当前任务（精确链接）
      名称 / 连接 / GPU概况 / CPU内存            传输异常（精确链接）
      点击一行→独立主机详情
    主机详情：CPU/内存、每张GPU显存/利用率、进程、按需完整命令、关联Job

桌面优先让主机清单和当前任务并读，去掉常驻左栏的同一资源摘要/迷你图副本与巨大的功能卡。一个主滚动区，长命令/日志正文局部滚动。1024/手机列表隐藏CPU/内存列以保主机和GPU概况，点击详情读完整值；768有空间会显示。手机先主机清单再具体任务/传输，首屏能看到资源与任务数量，不承诺所有主机、任务名称和明细在同一屏内。没有自动动画/假进度；系统字体、冷灰/白/蓝色和带文字状态沿frontend-design指导。

### 旧设计为何存在，以及本轮如何取舍

| 旧入口/字段组、真实读者 | 原来要完成的任务 | 本轮决定、位置和联动 | 数据/默认/校验与保存影响 |
| --- | --- | --- | --- |
| serverList、renderServers/server_list_markup；id/name/mode/target | 找一台已配置机器，确定主机身份 | 保留为首页完整主机行；连接target/地址不重复放到首页，连接编辑归配置 | 本片固定6台演示，用id作路由；缺/坏id不可用不换主机；无写入 |
| serverSort、pin/order/拖拽、历史mini图 | 高频机器好找，观察短时趋势 | 排序/置顶是可选偏好，后续独立设计；不把它们放在首屏主任务前；趋势只有真实采样才画 | 原生产消费者保留；本片不实现/不宣称已迁移偏好；不造趋势值 |
| online/reachable/error、serverIsReachable/serverHasMonitorIssue | 区分SSH可达、GPU监控故障与离线 | 首页标状态，详情给原因；旧采样不等于离线；GPU异常不能误报全机不可达 | 演示用reachable true/false/null与fresh/stale/unavailable固定分类，不是公开schema完整adapter；真实字段兼容另验 |
| refreshed_at/status_age_seconds、healthPill与反馈 | 判断数据是否可信、能否刷新 | 保采样时间/手动刷新，删除成功大块与重复健康数字；刷新失败保旧快照/原因 | 只显式刷新固定fixture，无后台请求或时间推进；首次失败无快照，不显示0/0；详情直链也不能显示fresh |
| summaryOnlineServers、summaryIdleGpus、summaryAlertServers | 一眼扫全组资源 | 一条紧凑指标带，共享hosts；显示已连接/配置数、当前已采样GPU空闲数及需关注数 | 当前4/6连接、2/6已采样GPU空闲、2台需关注；stale旧GPU不计入分母或空闲；空闲不是预留 |
| summaryRunningJobs/summaryTransferJobs、jobs | 看本服务执行压力，不等于系统进程数 | 运行/排队分别计，当前任务与异常传输有精确入口，不复制完整详情 | 同一jobs/transfers fixture服务首页和原只读详情；本片1运行/1排队，进程3条不能加成3任务；不能照抄旧“含启动等待”标签叫实际运行 |
| gpuRows、allGpus、monitoring_table_markup：index/name/memory_used_mib/total/gpu_util/state/temperature | 比较各卡余量、定位占用 | 保每卡显存/算力/状态到主机详情；温度字段保留在真实接线设计，当前fixture未展示；全部GPU跨主机表作为后续阅读方式，不能默认为已替代完成 | 演示GB为展示值，真实MiB需明确换算；0%算力但显存13GB标显存占用，非空闲；未知值不补0；meter仅采样占用，非任务进度 |
| host_resources.cpu/memory及磁盘网络popover | 看CPU/内存/系统瓶颈 | CPU/内存首页有空间即展示，详情始终可读；磁盘/网络放系统明细候选，不塞常驻小徽章 | 不把缺采样当0；本片cpu%/内存文本固定fixture，非真实归一/阈值算法 |
| processRows、processes：pid/user/gpu_index/used_memory_mib/command | 找谁在占GPU及完整命令 | 独立主机详情显示系统进程；完整命令按需展开，已有job引用才给精确链接 | PID与Job不是同类id；未关联不猜研究run；长命令局部滚动、正文完整 |
| processSearch/server/user/GPU filter、排序/列宽 | 在多进程中定位某条记录 | 保需求，后续任务/进程阅读片验证筛选组合，不在本片复制所有控件 | 过滤不改事实/终态；本片未实现筛选/拖列，不称全监控功能迁移完成 |
| stopProcess及monitoring_process_stop_* | 停止具体系统进程 | 不直接搬首页红色关闭按钮；未来在详情核PID/所有者并确认，独立于停止Job/终端 | 本片没有停止动作；正式旧入口保留，不靠隐藏错误称安全停止已实现 |
| refreshSelectedServerBtn、refreshServerStatus | 单机采样失败不影响其他机器 | 单机刷新需求保留；当前只显式全局模拟重读，真实预算/局部失败/迟到防覆盖待接线 | GET /api/status、/api/servers/{id}/refresh为现API；不新增第二共享状态读者 |
| exec job/plan、transfer、activity tasks/tmux/terminal | 提交/查任务，搬文件、看会话 | 顶栏直达任务/传输/活动，监控只投影定位；配置独立；工作台使用原项目运行 | 依旧单Job生命周期；任务提交/终端/传输冲突与核验交互后续分片，固定示例不是能力实现 |

本表是本轮相关监控字段/控件组的职责审计，未声称已逐个穷举旧前端所有动态控件。工作台58控件/16类50config仍以§2唯一矩阵为准，未显示字段不能被后续保存清空。生产旧入口未替换，因此其可用能力也未被本片删除。

### 全产品职责与跨区规则

- 监控台默认是日常操作入口；监控详情读资源/系统进程，当前任务、传输摘要只由各自同一事实派生，不额外决定终态。
- 研究工作台仍负责项目创建→必要配置→明确启动→等待/结果，运行/历史/设置分开；不重复造项目数据到监控首页，Agent对话按需。
- 远程任务负责单命令/批量与Job/日志；终端/tmux按需进入，持久Job、GPU进程、会话是不同对象。
- 文件传输负责源主机+路径、目标主机+路径、冲突预检、执行与实物验证；可复用路径选择，不能拿本机同名文件代远程。
- 活动只帮助找事件并回精确对象；现全局事件聚合不是现成事实，不能把工作区SSE当全产品事件。
- 配置中心编辑主机连接、流程、Agent、工具、模型及本机维护；本轮只复用已有目录，主机/维护编辑未接入新原型，不放假按钮或真实密钥框。

从主机进任务传精确已知Job引用；不存在关联就明说未关联，不跳“最近任务”。未来筛选、预填和配置返回要显式、可取消，不自动提交或保存。跨文档监控/工作台入口仍不经过工作台站内approveLeave，验证范围是同标签浏览器Back恢复原URL/run/dirty草稿；关闭标签恢复/任意入口精确焦点未承诺。/ 与旧 /monitor 共用同一监控投影；坏主机/坏路径明确不可用。UI01原monitor只读示例/功能卡发现入口退出，旧工作台hash壳继续兼容已存来源，后续迁移验证后再删。

### 模拟字段与现API的对接边界

当前新monitor.js统一提供hosts、jobs、transfers的演示定义，首页/主机详情和任务/传输示例消费这些定义；无网络/持久状态/调度器。演示6主机是虚构，不读取用户截图中的IP/用户名或config。

生产监控沿status_payload→servers/jobs、app.js renderOverview/renderServers/renderGpuRows/renderProcesses，单机刷新仍refreshServerStatus，schema名称/online与reachable兼容、陈旧判定/时间、MiB/百分比/温度和资源监控故障需正式接线前逐项核对。现serverIdleGpuCount有“总数减busy”回退，不能拿该回退证明未知卡必空闲；原gpu_util/temperature缺省0的展示应单独核实，不直接复制到新页。jobs/log和Transfer的kind/metadata.transfer_spec仍走原Job内核；统一Transfer核验、全局活动、主机配置目录等缺口保持开放。演示主机详情的CPU/GPU字段不是新增API或存储schema。

### UI02 当时计划（已暂停）

UI02当时只验默认首页与主机明细阅读，未接真实后端、未迁生产、未实现停止/提交/连接编辑。原定 UI03A 远程任务只读列表/详情及其后的 UI04/UI05 当前暂停，不能按它们继续推进。WB06A 正式列表接线与 Python 兼容暂缓；当前调查路线与唯一下一片见本文§0和阶段计划。

## 1. 要让用户完成什么

第一次使用的人能完成：创建项目 → 补齐必要配置 → 启动运行 → 看懂等待/失败 → 获取结果。页面靠名称、布局、字段提示和明确动作指路，不常驻操作手册。先做好完整设计，再按小片验证独立模拟原型；不修改后端，不替换正式页面。

WB01–WB05当时范围：工作台完整闭环、明亮克制、三步创建、对话按需打开；监控/执行/活动当时仅统一导航。2026-11-09起全产品范围见§0，逐片继续其他区域设计。Python 3.10兼容暂缓。面向用户称“项目”，实现仍使用workspace_id；项目、模板、一次run、一次attempt、子Job是不同对象，不能改成一张含混的“任务”。

### 页面唯一职责

| 页面 | 用户在此完成的任务 | 默认内容/主操作 | 不能放进来 |
| --- | --- | --- | --- |
| 项目列表 | 找到或创建项目 | 名称、目标摘要、最近运行、更新时间；创建项目 | 主机卡、全部字段、拓扑和日志 |
| 三步创建 | 得到可继续配置的项目 | ①目标资料 ②选择流程 ③运行设置；创建项目 | 全局Agent/工具编辑器、历史运行 |
| 项目·运行 | 运行已配置项目，理解当前阻塞 | 当前run、完整步骤、当前动作；未运行时“开始运行” | 创建表单、配置目录、全量历史 |
| 运行详情 | 核对某次执行及结果 | 结果摘要、顺序步骤；选择一步看输入/输出/子Job/日志 | 可编辑历史配置、重复进度卡 |
| 项目·历史 | 找到一次过去执行 | 日期/状态/结果完整性，进入精确run；比较按需 | 另一个独立run状态合并器 |
| 项目·设置 | 修改后续运行的项目配置 | 基本资料、运行环境、流程与显式覆盖；保存 | 实时日志、全局密钥表单 |
| 配置中心 | 维护可复用能力 | 流程、Agent、工具、模型/搜索连接，各自列表→编辑 | 项目实时任务/进度/嵌套运行记录 |

### 导航和布局草图

```text
当前默认监控台，顶栏直达研究工作台 / 任务 / 传输 / 活动 / 配置
工作台内：项目 / 配置中心，有监控台返回
UI01功能卡首页已退出，旧工作台hash路由兼容保留
顶栏：面包屑                                 紧凑更新时间 / 刷新
项目列表：标题 / 创建项目
          搜索（有项目时）
          项目名称   目标摘要   最近运行   更新时间   继续

项目 > 项目名称：运行 | 历史 | 设置
运行：本次状态/当前步骤                         主要操作
      完整步骤列表 → 选中步骤的独立阅读内容
历史：执行列表 → 一次运行详情 → 报告或日志阅读
设置：资料 / 运行环境 / 流程（段内导航，非多层横向页签）
配置中心：资源类别 → 资源列表 → 一个资源的编辑页
```

主机卡不再常驻工作台侧栏；运行位置出现在项目设置/本次执行目标中，资源监控通过明确入口查看。默认一个主滚动区，日志/代码可局部滚动。桌面最多一个列表与一个阅读区；较窄窗口转为列表→详情，不压成三列。独立报告阅读可返回同run/step和滚动位置。Agent对话从相关项目/步骤打开独立页面，保留返回上下文，不固定占一列。

### WB05L2跨区最小布局（限定模拟已验）

```text
桌面侧栏：项目 / 监控 / 执行 / 活动 / 配置中心
小屏：品牌一行，文字导航自然换行；当前区域同时用颜色与文字标识
顶栏：区域面包屑                         演示模式 / 演示场景
正文：区域标题 + 一句用途/演示范围
      来源项目名称（run有冻结快照时取快照）
      本次运行 / 步骤或日志来源
      [返回原项目 / 本次运行 / 原步骤或日志]    唯一主要动作
无来源：未关联项目，[查看项目]；无效来源：来源不可用，[返回项目列表]
```

三处区域正文不复制GPU卡、任务表单或活动列表；不放假运行灯/示例资源数。导航来源是URL/视图上下文，不写入projects/runs。连续跨区携带原始项目路由，不把上一区域再套入from；run/step/job须属于该项目与本run，未知/畸形引用不改用latest。项目根只表示当前项目，历史run保持精确ID。配置中心沿已有编辑/返回入口，导航按原approveLeave处理未保存确认；取消不得先改来源，刷新沿现positions/草稿恢复。统一导航区域标识替换旧两入口硬编码，非另造路由/业务状态核。

## 2. 字段、来源和保存规则

### 读表方法与范围

本次盘点覆盖`web/index.html`工作台区域所有静态input/select/textarea，以及关联renderer中的Agent、工具、连接、节点、输入映射、运行筛选和调试字段；不把监控、独立命令、批量任务、传输表单算入本次重设计。运行只读字段另列。服务端隐藏字段与扩展JSON不得因界面不展示而删除。

表中的“必需/默认/校验”是**新设计目标**，不是声称现有校验已实现。已有记录一律保留原值；placeholder不是默认。新项目不捏造目录、密钥、环境或远端主机。后端能力不足的规则记为接线缺口；模拟只能用于体验验证。

每行同时继承所属组的来源、联动和保存规则，行内例外优先。字段可在创建与设置显示同一值，但只能有一个编辑语义和草稿来源，不能两处各保存副本。

| 组 | 输入来源与保存边界 | 联动与保存影响 |
| --- | --- | --- |
| C 创建草稿 | 用户输入/所选模板快照；创建前独立草稿 | 上一步保留值；创建不直接启动；调用创建成功后进入项目，缺运行条件允许保存草稿 |
| P 项目配置 | workspaceFormPayload→workspacePayloadForSave→创建/更新workspace；从已保存项目回填 | 当前代码同时打包nodes/tools/agents/model/chat；新设计仅显式保存项目修改，不清空未展示字段；G27往返缺口不能冒充已修 |
| T 可复用流程 | WorkflowTemplateDraft.payloadForSave→模板CRUD，独立于项目草稿 | 新项目复制快照；更新模板不悄悄改项目；现有迁移需预览/确认 |
| A Agent | 全局Agent定义或项目agents[]快照，分别保存 | 工具授权唯一编辑在此；空allowlist明确禁止工具，不能自动补回；全局修改不改历史 |
| U 工具 | 全局工具定义或项目tools[]快照，分别保存 | 描述/注册不等于有适配器；工具页使用关系只读，不再反向编辑Agent授权 |
| M 连接 | Provider全局CRUD；项目/模板仅保存连接ID和路由 | 密钥只在连接管理编辑；原型不接收真实密钥；现有Provider私密存储仍在data/，兼容迁移见G08/N00E；本片不搬动，后续配置集中config/且不提交 |
| N 步骤 | 模板nodes[]或项目nodes[]；同字段按作用域独立保存 | 默认来自流程/项目，节点覆盖显式启用；移除覆盖前展示将回到什么值；运行快照不可编辑 |
| V 查看状态 | 当前项目/run/step、API查询和浏览器导航 | 筛选与阅读选择不更新项目、不推进任务；路由携带精确ID；丢失记录显示不可用而非换最新 |
| D 调试/对话 | 用户显式输入，关联项目/Agent/模板上下文 | 独立于保存配置与运行控制；执行调试会有外部调用，需显式动作，不因切页自动执行 |

### 归属和联动的具体决定

- 创建三步：目标与可选资料；选择流程并显示适用任务/所需连接与执行位置/当前能力边界；确认主机+目录、需要时的模型与环境。最终摘要含缺项链接。主动作“创建项目”，进入项目后另点“开始运行”，避免创建即产生任务副作用。
- 项目目标以brief为主要表述；references是资料，约束/成功标准有明确名称。旧idea_text/context_blocks/notes保留各自原值，先分别显示在相应编辑段，不自动拼接覆盖。多个仓库/论文数组不能无声截为一个repo_url/paper_url；其余保留参考资料，映射歧义提示确认。
- 项目默认主机、目录、环境、CPU/GPU只编辑一次；节点显示“来自项目/流程/此步骤”。当前旧代码存在从节点命令补项目recipe、从表单补节点等双向填值，未来接线前需单独契约核查，不能承诺已有单向继承机制。
- Agent模型默认使用项目连接；选择“此Agent单独指定”才显示覆盖。路由已有workspace_default/agent_override语义保持，不由前端偷偷改变；模板AI路由从当前AI页迁至流程设置。
- 工具的ID、能力类别、启用状态不能被误称为授权；授权在Agent工具选择中编辑。搜索工具的连接绑定保留为工具专属配置，不冒充LLM连接。
- 保存修改仅影响后续执行；创建时的模板身份/版本、保存时的effective值与来源、run冻结快照分别表达。现有元数据缺失时显示来源未知，不补伪来源。
- 切页/项目时未保存修改提供“继续编辑/放弃修改”，默认继续；已确认保存后才离开。原型仅本地草稿，刷新可恢复并标草稿；密钥不存localStorage。

### 静态字段逐项清单

来源：`index.html`工作台区域；P组收集/保存见`app.js::workspaceFormPayload/workspacePayloadForSave/selectWorkspace`，C组见`workspaceUseInputsPayload`，T组见`WorkflowTemplateDraft`。同字段的创建/编辑仅为生命周期不同，不删除已有值。

| 当前控件ID | 组/用途 | 必需条件 | 默认 | 校验/风险 | 决定与目标归属 |
| --- | --- | --- | --- | --- | --- |
| `workspaceTaskGoalInput` | C·项目目标 | 创建必填 | 空 | 非空 | 迁移到创建第一步，对应goal_text |
| `workspaceTaskRepoInput` | C·候选仓库 | 可选 | 空数组 | 逐行URL，保留多个 | 创建资料，对应repo_urls |
| `workspaceTaskPaperInput` | C·论文资料 | 可选 | 空数组 | 逐行URL | 创建资料，对应paper_urls |
| `workspaceTaskReferenceInput` | C·数据与参考线索 | 可选 | 空数组 | 路径需保留host语境；普通名称不误判URL | 创建资料，对应references |
| `workspaceTaskContextInput` | C·约束与成功标准 | 可选 | 空数组 | 保留原行 | 创建资料，对应context_blocks，不与notes自动合并 |
| `workspaceTemplateSelect` | C·所选流程 | 创建必填 | 不偷偷选第一个 | ID存在/能力范围 | 迁移创建第二步 |
| `workspaceUseChatAgentSelect` | D·对话Agent | 发送前必选 | 原选择/有效默认 | 属于本项目且启用 | 辅助对话，移出驾驶舱常驻列 |
| `workspaceUseChatInput` | D·对话输入 | 发送时必填 | 空 | 非空，注明发送对象 | 辅助对话 |
| `workspaceRunReaderProjectSelect` | V·项目范围 | 进入项目必需 | URL项目ID | 项目存在 | 项目导航统一来源，不再嵌套选择器 |
| `workspaceExecutionOverviewSearch` | V·历史搜索 | 可选 | 空 | 本地/查询范围清楚 | 历史页搜索 |
| `workspaceExecutionOverviewStatusFilter` | V·历史状态 | 可选 | 全部 | 状态枚举 | 历史筛选按需 |
| `workspaceExecutionOverviewKindFilter` | V·历史类型 | 可选 | 全部 | 类型枚举 | 历史高级筛选 |
| `templateNameInput` | T·名称 | 保存必需 | 空 | 非空 | 配置中心·流程/name；保留独立快照，模型路由从AI页迁回流程 |
| `templateSourceTypeSelect` | T·来源类型 | 保存必需 | 未指定，显式选择 | idea/repo/paper/mixed | 配置中心·流程/source_type；保留独立快照，模型路由从AI页迁回流程 |
| `templateStatusSelect` | T·整理状态 | 保存必需 | ready（整理状态） | 原枚举；不能改运行终态 | 配置中心·流程/status；保留独立快照，模型路由从AI页迁回流程 |
| `templateTagsInput` | T·标签 | 可选 | 空数组 | 标签去重 | 配置中心·流程/tags；保留独立快照，模型路由从AI页迁回流程 |
| `templateDescriptionInput` | T·用途说明 | 可选 | 空 | 原文保留 | 配置中心·流程/description；保留独立快照，模型路由从AI页迁回流程 |
| `templateBriefInput` | T·目标示例 | 可选 | 空 | 原文示例，不冒充用户目标 | 配置中心·流程/brief；保留独立快照，模型路由从AI页迁回流程 |
| `templateRepoUrlInput` | T·仓库示例 | 仓库流程提供示例时 | 空 | URL；实例仍需确认 | 配置中心·流程/repo_url；保留独立快照，模型路由从AI页迁回流程 |
| `templateRepoRefInput` | T·分支示例 | 可选 | 空 | 引用字符串，不猜main | 配置中心·流程/repo_ref；保留独立快照，模型路由从AI页迁回流程 |
| `templatePaperUrlInput` | T·论文示例 | 论文流程提供示例时 | 空 | URL | 配置中心·流程/paper_url；保留独立快照，模型路由从AI页迁回流程 |
| `templateWorkspaceDirInput` | T·目录示例 | 可选示例 | 空 | 路径示例不是可用目录 | 配置中心·流程/workspace_dir；保留独立快照，模型路由从AI页迁回流程 |
| `templateIdeaInput` | T·背景示例 | 可选示例 | 空 | 原文保留 | 配置中心·流程/idea_text；保留独立快照，模型路由从AI页迁回流程 |
| `templateEnvNameInput` | T·环境名默认 | 流程指定环境时 | 空=未指定 | 与管理器配套 | 配置中心·流程/env_name；保留独立快照，模型路由从AI页迁回流程 |
| `templateEnvManagerSelect` | T·环境管理器默认 | 流程指定环境时 | 空=未指定 | 空/conda/venv/custom | 配置中心·流程/env_manager；保留独立快照，模型路由从AI页迁回流程 |
| `templatePythonVersionInput` | T·Python需求 | 可选 | 空 | 版本格式，不证明已安装 | 配置中心·流程/python_version；保留独立快照，模型路由从AI页迁回流程 |
| `templateChatAgentSelect` | T·默认对话Agent | 可选 | 空=未指定 | 有效Agent引用 | 配置中心·流程/model.chat_agent_id；保留独立快照，模型路由从AI页迁回流程 |
| `templateProviderProfileSelect` | T·默认模型连接 | Agent流程需要有效路由 | 空=未指定 | 有效LLM连接；不能填密钥 | 配置中心·流程/model.provider_profile_id；保留独立快照，模型路由从AI页迁回流程 |
| `templateRoutingModeSelect` | T·路由模式 | 配置路由时 | workspace_default | 现路由枚举；不变更覆盖语义 | 配置中心·流程/model.routing_mode；保留独立快照，模型路由从AI页迁回流程 |
| `workflowTemplateNodeKindSelect` | T·添加步骤类型 | 添加步骤时 | 显式选择 | 有效目录类型不等于已支持执行 | 配置中心·流程/nodes[].kind；保留独立快照，模型路由从AI页迁回流程 |
| `workspaceIdInput` | P·项目身份 | 系统提供 | 新建为空 | 只读，回执确认 | 隐藏workspace_id，禁止用户改写 |
| `workspaceNameInput` | P·项目名 | 保存非空 | 目标首句可生成，允许改 | 非空 | 创建摘要/设置基本资料，对应name |
| `workspaceSourceType` | P·来源类型 | 保存需要 | 所选流程/既有值 | idea/repo/paper/mixed | 高级资料，非新手必选题 |
| `workspaceBrief` | P·目标摘要 | 创建必填 | 创建目标 | 非空 | 项目基本资料，对应brief |
| `workspaceReferences` | P·参考资料 | 可选 | 已有值/空 | 逐行保留 | 与创建references同编辑语义 |
| `workspaceTags` | P·标签 | 可选 | 空数组 | 逗号解析去重 | 列表筛选次要字段 |
| `workspaceStatus` | P·项目整理状态 | 可选 | draft | 枚举；不当run终态 | 高级资料，区分项目与运行状态 |
| `workspaceRepoUrl` | P·主仓库 | 流程条件必需 | 已有值/空 | URL | 项目资料，与候选列表确认主项 |
| `workspaceRepoRef` | P·分支或提交 | 可选 | 空，不假定main | 保留引用字符串 | 仓库下的次级字段 |
| `workspacePaperUrl` | P·主论文 | 流程条件必需 | 已有值/空 | URL | 项目资料，不宣称已解析全文 |
| `workspaceDir` | P·工作目录 | 执行流程必需 | 空 | 目标host路径；可写性需真实检查 | 创建第三步/运行环境唯一编辑 |
| `workspaceIdeaText` | P·旧背景说明 | 可选 | 已有值/空 | 原文保留 | 背景段保留，不能自动替换目标 |
| `workspaceNotes` | P·项目备注 | 可选 | 已有值/空 | 原文保留 | 设置次要资料，不能当约束自动执行 |
| `workspaceEnvName` | P·环境名 | 流程条件必需 | 空表示未指定 | 按管理器核对；不自动造环境 | 运行环境高级项 |
| `workspaceEnvManager` | P·环境管理器 | 指定环境时需要 | 空 | 空/conda/venv/custom | 运行环境，与环境名联动 |
| `workspacePythonVersion` | P·期望Python | 可选 | 空 | 版本格式不等于已安装 | 环境需求，仅相关流程显示 |
| `workspaceSetupCommand` | P·环境准备命令 | 流程条件必需 | 空 | 非空与执行门禁 | 流程高级命令，不默认铺创建页 |
| `workspaceRunCommand` | P·运行命令 | 命令流程必需 | 空 | 原执行/权限门禁 | 流程高级命令；显示来源 |
| `workspaceReportCommand` | P·报告命令 | 流程条件必需 | 空 | 命令成功不等于文件交付 | 流程高级配置 |
| `workspaceSchedule` | P·计划说明 | 可选 | 空 | 仅说明，未证为调度器配置 | 保留高级项，不能显示已启用定时 |
| `workspaceNodeKindSelect` | N·添加步骤类型 | 添加时需要 | 明确选择 | 目录类型不等于支持执行图 | 流程编辑添加步骤 |
| `workspaceChatAgentSelect` | D·编辑页对话Agent | 发送前需要 | 已有选择 | 有效Agent | 与辅助对话同上下文，不留第二入口 |
| `workspaceChatInput` | D·编辑页对话输入 | 发送时需要 | 空 | 非空 | 迁移辅助对话，不删除历史chat |
| `workspaceToolSelect` | U·添加工具 | 添加时需要 | 明确选择 | 工具目录/真实实现 | 项目高级工具配置 |
| `workspaceModelProfileSelect` | P·项目模型连接 | Agent流程需要 | 流程快照/空 | 有效LLM Profile | 创建第三步/设置连接引用，不编辑密钥 |
| `workspaceModelRoutingSelect` | P·路由模式 | 有效路由需要 | workspace_default | 原枚举/覆盖语义 | 设置高级项，不并列讲内部英文 |
| `workspaceModelChatAgentSelect` | P·默认对话Agent | 可选 | 空 | 有效Agent或明确未选 | 设置辅助对话默认，空不自动补回 |
| `workspaceModelNotes` | P·模型配置备注 | 可选 | 空 | 原文保留 | 设置高级项，不是prompt |

以上58个静态控件逐项对应；没有把button算作输入字段，动作另见页面/状态表。

### 动态能力字段逐项清单

来源：`config_center_agent_renderer.js`、`config_center_tool_renderer.js`、`config_center_ai_renderer.js`，`app.js::renderWorkspaceAgentEditor/renderWorkspaceToolEditor`相应渲染段及`workspace_draft_normalizers.js`。全局与项目同名字段按A/U组独立保存，表中不表示双方共用可变对象。

| 字段（所属对象） | 用途/必需条件 | 新建默认/校验 | 决定、联动及保存影响 |
| --- | --- | --- | --- |
| A.id | Agent身份；引用必需 | 生成且唯一，旧ID保留 | 高级只读身份；改ID属于引用迁移，不能当改名 |
| A.name | 显示名；保存必需 | 空/非空 | 保留基本项 |
| A.role | 角色分类；可选 | 既有值/空 | 高级，不与显示名要求重复填写 |
| A.description | 全局用途；可选 | 空/原文 | 列表短摘要；项目已有只读元数据不丢 |
| A.prompt | 行为指令；配置Agent时需要 | 流程快照或空/非空 | 独立提示词编辑，不常驻运行页 |
| A.tools | 工具allowlist；可为空 | 新建明确空/ID有效 | 唯一授权编辑；文本框与逐工具复选合成一个选择器，空不补权 |
| A.provider_profile_id | 单Agent模型例外；可选 | 空=继承/有效LLM连接 | 显式“单独指定”才编辑；不输入密钥 |
| A.max_iterations | 调用迭代预算；可选 | 空=跟随实际默认/正整数 | 高级；全局当前提示默认10不等于所有路径已验证 |
| A.timeout_seconds | 总期限；可选 | 空保留原含义/正数 | 高级，展示有效值来源；不能因清空偷偷变成无限 |
| A.output_format | 输出契约；可选覆盖 | 空跟随节点/text或json | 高级，JSON解析不等于业务字段合格 |
| A.enabled | 是否可用 | 新建true/布尔 | 停用提示影响新执行，不改既有run |
| U.id | 工具注册身份；必需 | 唯一ID | 高级编辑；注册不安装实现 |
| U.label | 用户显示名；必需 | 空/非空 | 基本项 |
| U.category | 目录分组；可选 | general/目录值 | 次要项，不伪装成权限 |
| U.capability | read/write/execute边界；必需 | 现规范read/合法枚举 | 配置定义保留；与运行权限诊断区分 |
| U.description | 能力说明；可选 | 空/原文 | 列表短说明 |
| U.notes | 使用边界；可选 | 空/原文 | 工具详细配置，不常驻运行页 |
| U.enabled | 工具可用 | true/布尔 | 停用不擦除历史调用 |
| U.provider_profile_id | 搜索等工具连接；按工具需要 | 空/对应kind连接 | 工具专属绑定保留；实际草稿保存往返需核G27，不假称全部生效 |
| M.id | 连接身份 | 系统生成/唯一 | 隐藏身份，项目只存引用 |
| M.kind | 模型或搜索 | llm/llm或search | 单一连接管理入口；切类型需确认不兼容字段 |
| M.label | 连接名称；必需 | 空/非空 | 列表与选择器显示 |
| M.vendor | 协议厂商；必需 | 不猜厂商/现目录 | 基本项；厂商名不等于已验证完整兼容 |
| M.base_url | 接口地址；模型或自定义搜索需要 | 厂商建议显式填入/URL | 高级地址；与密钥同属连接，不散落项目 |
| M.model | 模型名；LLM必需 | 空/选择或填入 | 拉取失败允许手填；搜索连接不展示 |
| M.api_key | 凭据；依厂商条件 | 空表示不输入新值/不得回显原密钥 | 仅连接管理；保留已存与替换明确区分；清除需单独确认，原型仅虚构凭据状态 |
| M.is_default | 新建时推荐连接 | false/同kind默认唯一 | 不改已有项目/历史的显式引用 |
| M.has_api_key/api_key_masked | 保存状态只读 | 来自公开payload | 不当真实key重新保存，不进项目草稿 |
| M.status/missing_fields | 配置诊断只读 | 来自校验/缺项 | 连接页显示，可跨页修复，不是run状态 |
| model.provider_profile_id | 项目/模板默认连接 | 空或快照/有效ID | P/T组保存，同一引用不在AI页再存一份 |
| model.routing_mode | 覆盖是否有效 | workspace_default/原枚举 | 高级，开启例外才显Agent覆盖；原有效路由不静默改变 |
| model.chat_agent_id | 默认对话对象 | 空/有效Agent | 对话入口使用，和当前临时选中Agent分开 |
| model.notes | 路由说明 | 空/原文 | 高级配置；不当模型系统指令 |
| N.id/kind | 步骤身份和类型 | 创建时生成/目录值 | 编辑器保留，历史只读；类型存在不保证当前执行图支持 |
| N.title | 步骤名称 | 类型名称/非空 | 基本编辑，运行仅展示快照 |
| N.status | 旧手工节点状态 | draft/原枚举 | 从普通配置编辑移出；保留旧值，不允许手填running/done作为真实执行证据 |
| N.handler.mode | 人工/Agent/系统执行 | 来自流程/三枚举 | 仅流程编辑；不再猜执行者覆盖明确选择 |
| N.handler.agent_id | 绑定Agent | 空；Agent模式必需/有效ID | 与mode联动；切换前提示解除关系 |
| N.handler.name | 人工责任人或显示别名 | 空/文本 | 仅有实际用途才显示，不强迫与Agent名重复 |
| N.handler.handoff | 交接说明 | 空/文本 | 高级；不是输入引用或运行结果 |
| N.handler.output_key | 兼容旧输出别名 | 原值/空 | 保留兼容，展示有效输出键；与N.output_key冲突先诊断，不自动抹掉 |
| N.output_key | 命名输出引用 | 来自契约/标识唯一 | 高级，变更列下游影响，不在运行页编辑 |
| N.notes | 步骤备注 | 空/原文 | 流程高级配置，与执行错误分开 |
| N.input_mapping | 输入名→引用 | 契约建议显式确认/原引用语法 | 文本与连线编辑共用一份；验证缺项/前向引用/来源，不新增引用引擎 |
| N.position/links | 编辑画布位置/顺序关系 | 来自顺序/现值 | 仅高级拓扑；运行顺序读冻结plan，不依像素决定 |
| D.executeLlm | 调试是否调用模型/工具 | false/布尔 | 独立调试入口明确副作用；不是保存开关 |
| D.input | 调试输入 | 空或显式示例/非空 | 全局/项目调试独立上下文，结果不写成run成功 |
| D.templateId | 全局调试上下文 | 空/有效模板 | 对应manageAgentDebugTemplateSelect，只影响本次调试 |
| V.status | 运行状态筛选 | 全部/枚举 | 历史页常用筛选，不更新run |
| V.nodeKind | 节点筛选 | 全部/目录 | 历史高级筛选 |
| V.timeRange | 时间范围 | 全部/1h、24h、7d、30d | 历史页，说明按记录时间 |
| V.jobId | Job精确检索 | 空/标识 | 高级筛选，不强迫新手理解ID |
| V.agentExecutionId | Agent调用检索 | 空/标识 | 高级筛选 |

动态选择器覆盖说明：`data-manage-agent-field/number/checkbox`与`data-agent-field/checkbox/tool-toggle`分别映射A表；逐工具toggle和tools文本编辑是同一allowlist的重复控件，不是两套权限。`data-manage-tool-field/checkbox`与`data-tool-field/checkbox`映射U表；`data-manage-provider-field/checkbox`与旧实例`data-provider-field`映射M表，旧实例密钥编辑后续退出。`data-manage-node-field/handler-field`与`data-node-field/handler-field`映射N表。`data-node-input-mapping`、边编辑器`data-edge-input-mapping-name/source/source-select`均编辑N.input_mapping；不另存连线副本。`manageAiTemplateProfileSelect/RoutingSelect/ChatAgentSelect`分别映射T.model三字段，迁回流程编辑。`manageAgentDebugExecuteLlm/TemplateSelect/Input`与项目`data-agent-debug-execute-llm/input`映射D表。选择工具测试参数、输出格式等现有扩展值若未在普通编辑器出现，仍保留原JSON，不能以“未展示”当无用字段删除。

### 节点类型专用配置逐项清单

来源：`workspace_catalog_data.js::WORKSPACE_NODE_TYPES`的全部configFields，`workspace_node_catalog.js::workspaceNodeDefaultConfig`给初始值，`app.js::renderWorkspaceNodeField`渲染`data-config-key`。下表每行属于N组的`nodes[].config.<key>`；同名字段在不同类型下是独立覆盖，不能共享可变对象。

新设计默认：已有值优先，新建显示项目/流程有效值及来源；无来源则空，`notify.user.channel`当前默认ui。条件必需由所选流程/执行者的真实门禁判断，所有字段允许先存未就绪草稿。表中按用途标明执行时的要求，不把目录中的16种节点全部宣称已可串成任意执行图。

| 节点类型 | 字段/用途 | 执行必需条件与校验 | 决定/联动 |
| --- | --- | --- | --- |
| `source.repo` | `repo_url` · 仓库地址 | 来源型流程需要；URL/引用/目标文本；ref可空，不猜默认分支 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `source.repo` | `repo_ref` · 分支 / 提交 | 来源型流程需要；URL/引用/目标文本；ref可空，不猜默认分支 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `source.paper` | `paper_url` · 论文链接 | 论文流程需要；URL合法，空表示未指定 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `source.idea` | `idea_text` · 想法 / 目标 | 想法流程需要；非空目标原文 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `research.search` | `query` · 检索关键词 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `research.search` | `goal` · 检索目标 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `repo.clone` | `repo_url` · 仓库地址 | 来源型流程需要；URL/引用/目标文本；ref可空，不猜默认分支 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `repo.clone` | `repo_ref` · 分支 / 提交 | 来源型流程需要；URL/引用/目标文本；ref可空，不猜默认分支 | 来源资料继承，只在明确改变本步骤输入时覆盖 |
| `repo.clone` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `path.resolve` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `path.resolve` | `data_roots` · 数据根目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `path.resolve` | `output_roots` · 输出根目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `repo.inspect` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `repo.inspect` | `focus_paths` · 重点路径 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `repo.inspect` | `questions` · 检查问题 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `dataset.find` | `query` · 数据集关键词 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `dataset.find` | `dataset_hints` · 路径 / 链接线索 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `dataset.find` | `data_roots` · 搜索根目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `dataset.find` | `expected_layout` · 期望结构 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `env.infer` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `env.infer` | `manifest_paths` · 依赖文件 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `env.infer` | `env_name` · 环境名 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `env.infer` | `python_version` · Python 版本 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `env.prepare` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `env.prepare` | `env_name` · 环境名 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `env.prepare` | `env_manager` · 环境管理 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `env.prepare` | `python_version` · Python 版本 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `env.prepare` | `setup_command` · Setup 命令 | 对应系统/工具执行时需要；原命令/权限/环境门禁，不能由原型执行 | 步骤高级命令；主表只给摘要和编辑入口 |
| `gpu.allocate` | `server_id` · 目标服务器提示 | 需要执行主机；有效host_id，空不猜远端 | 运行环境；CPU隐藏GPU专用项并保留草稿；显存GiB转MiB需适配验证 |
| `gpu.allocate` | `gpu_policy` · GPU 策略 | GPU流程需要；合法策略，与CPU/GPU选择一致 | 运行环境；CPU隐藏GPU专用项并保留草稿；显存GiB转MiB需适配验证 |
| `gpu.allocate` | `min_free_memory_gib` · 最低空闲显存 GiB | GPU流程需要；非负数，单位GiB | 运行环境；CPU隐藏GPU专用项并保留草稿；显存GiB转MiB需适配验证 |
| `gpu.allocate` | `notes` · 调度备注 | 可选原文，保留本类型含义 | 步骤高级备注；不是运行错误或执行状态 |
| `run.command` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `run.command` | `env_name` · 环境名 | 环境型流程按需；管理器枚举/版本；不凭名字推断环境已存在 | 默认来自项目运行环境，高级覆盖保留 |
| `run.command` | `server_id` · 目标服务器提示 | 需要执行主机；有效host_id，空不猜远端 | 运行环境；CPU隐藏GPU专用项并保留草稿；显存GiB转MiB需适配验证 |
| `run.command` | `gpu_policy` · GPU 策略 | GPU流程需要；合法策略，与CPU/GPU选择一致 | 运行环境；CPU隐藏GPU专用项并保留草稿；显存GiB转MiB需适配验证 |
| `run.command` | `run_command` · Run 命令 | 对应系统/工具执行时需要；原命令/权限/环境门禁，不能由原型执行 | 步骤高级命令；主表只给摘要和编辑入口 |
| `run.command` | `schedule` · 定时 / 批量计划 | 可选文本；当前未证明定时调度能力 | 高级计划说明；不显示“已安排执行” |
| `artifact.collect` | `workspace_dir` · 工作目录 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `artifact.collect` | `artifact_paths` · 产物路径 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `artifact.collect` | `metric_paths` · 指标路径 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `artifact.collect` | `notes` · 收集要求 | 可选原文，保留本类型含义 | 步骤高级备注；不是运行错误或执行状态 |
| `eval.report` | `report_command` · Report 命令 | 对应系统/工具执行时需要；原命令/权限/环境门禁，不能由原型执行 | 步骤高级命令；主表只给摘要和编辑入口 |
| `eval.report` | `metric_paths` · 指标文件路径 | 相关读写流程需要；host+路径/存在性与权限真实核验，线索不等于已验证 | 迁移运行环境或步骤高级配置；项目已有默认只显示来源，显式覆盖才编辑 |
| `eval.report` | `notes` · 结果要求 | 可选原文，保留本类型含义 | 步骤高级备注；不是运行错误或执行状态 |
| `notify.user` | `channel` · 通知渠道 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `notify.user` | `message` · 消息模板 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `custom.step` | `goal` · 目标 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |
| `custom.step` | `command` · 可选命令 | 对应系统/工具执行时需要；原命令/权限/环境门禁，不能由原型执行 | 步骤高级命令；主表只给摘要和编辑入口 |
| `custom.step` | `output_expectation` · 输出预期 | 按对应流程输入契约；文本/列表/枚举按原类型；缺项只阻止运行不丢草稿 | 步骤专用高级配置，相关流程才出现，不塞项目创建基本项 |

共16种节点、50个类型/字段组合；初始空值、项目来源和ui默认按本节规则记录，placeholder不当值。自定义额外config键保留并在高级诊断显示，不宣称已穷举服务端扩展字段。

## 3. 运行只读内容、动作与反馈

运行页读取事实，不编辑事实。以下是展示模型，不新增第二个状态机；正式接线须核对响应中的实际键名，不能把这里的概念名直接当API字段。

| 展示内容 | 输入来源 | 展示与联动 | 不得做什么 |
| --- | --- | --- | --- |
| 项目名/目标、所选流程 | 项目配置；历史使用提交快照 | 标明项目与本次运行，长名可换行 | 拿当前配置覆盖历史输入 |
| run/step/attempt身份 | 持久运行记录 | URL携带精确ID；默认显示友好名称，诊断才显示ID | 查不到时静默换最新run |
| 完整步骤和进度 | 提交时完整计划及步骤状态 | 已完成/总步骤，另列等待与未执行；不确定不算完成 | 用计时器、日志字数或子任务submitted推到100% |
| 当前动作/等待原因 | step状态、waiting_on、子任务引用 | “等待子任务完成”；提供该子任务入口 | 给queued贴“已完成” |
| 子任务 | 本次job_id/child_job_ids及关联run | 同一任务去重展示；主机、目录、CPU/GPU、环境是只读执行事实 | 混入项目历史Job或本机同名文件 |
| 输入/输出 | 本次step/attempt的已解析引用与证据 | 摘要→独立阅读；长正文不静默截断，截断须标识 | 把产物声明当文件已写入 |
| 日志 | 精确Job日志入口 | 明确任务、加载范围、截断/断线和重试 | 把旧缓存说成实时输出 |
| 报告/交付 | report状态、正文及实物验证 | 执行结束与交付完整分别显示；缺失列原因 | 无报告仍显示“全部成功” |
| 时间/更新 | 后端时间与实际读取时间 | 常态紧凑更新时间/刷新 | 常驻一整块“状态读取完成” |
| 配置来源 | 模板/项目/节点显式值，历史快照 | 显示有效值和来源；现API缺来源时写“来源未记录” | 猜测继承来源 |

### 页面状态与允许动作

| 场景 | 用户看到 | 主要动作/恢复 | 语义边界 |
| --- | --- | --- | --- |
| 无项目 | 简洁空列表 | 创建项目 | 不插虚构真实项目 |
| 创建中/缺项 | 三步进度、字段旁缺项 | 上一步/下一步，最后创建；缺配置跳唯一入口并返回 | 保存草稿和启动分开，不能丢输入 |
| 无run且已配置 | 项目目标、流程摘要 | 开始运行 | 启动前确认实际范围与缺项 |
| 受理中 | 按钮忙碌和局部反馈 | 防重复提交；失败可重试 | 受理不等于任务开始或完成 |
| 排队/运行 | 本次步骤、当前动作 | 看步骤/日志 | 不自动展开全部详情 |
| 等待子任务 | 等待对象和原因 | 打开子任务；支持时停止后续 | 不提前执行下游 |
| 阻塞/缺条件 | 哪一步缺什么 | 去配置/诊断并返回；依产品契约显式重新提交 | 改配置不自动恢复旧run，不暗示现有通用恢复 |
| 执行失败 | 失败步骤、简短原因、已留证据 | 查看日志；明确启动新run或已支持的重试 | 追加attempt和新run不能含混；不承诺任意失败可续跑 |
| 请求停止后续 | 已提交请求及仍在运行的子任务 | 查看剩余子任务 | 不把请求停止当外部进程已结束 |
| 已停止/后续跳过 | 停在哪一步，保留完成部分 | 查看已有结果/重新运行 | 不把跳过染成成功 |
| 执行结束、交付缺失 | “执行已结束 · 结果不完整” | 查看缺项和已有报告 | 不伪造正文或文件 |
| 完成且交付完整 | 简短结果摘要 | 阅读报告/下载证据 | 下载失败单独反馈，不改任务终态 |
| 区域加载/超时/断线 | 该区域骨架或简短错误 | 重试/重载 | 保留可用内容与更新时间，旧内容明确标旧 |
| 启动失败 | 可理解的失败说明 | 始终保留页面重载入口 | 删正常提示不能顺带隐藏启动故障 |

流程编辑与运行查看分开；默认顺序步骤，拓扑仅按需查看，不因原型能画任意图而宣称引擎支持任意图。危险动作单独确认，说明影响对象。低频导出、诊断、删除放明确次级菜单，不与“开始运行”同权重。

## 4. 要退出的重复展示与保留条件

这里只做删除决定，不在WB01删代码。迁移逐个职责完成，消费者核对、同输入对照和浏览器验收后才退出旧入口。

| 现有入口/消费者 | 问题与决定 | 迁移验收/保留条件 |
| --- | --- | --- |
| index.html工作台目标表单 + app.js保存/启动装配 | 创建、编辑、运行混排；创建迁到独立三步，运行页不再复刻表单 | 多URL、旧背景/备注、隐藏字段保真，创建不启动；正式迁移前旧入口保留 |
| workspaceUseChat与workspaceChat两套输入/选择 | 常驻对话抢空间；合为项目辅助对话入口 | 项目/Agent/历史上下文、返回位置核对后移除重复输入，不删除聊天记录 |
| 项目Agent/工具编辑与全局目录renderer | 外观相似但作用域不同；保留快照区别 | 全局/项目编辑明确标题和影响；不因同名字段删项目覆盖 |
| app.js实例Provider编辑 + config_center_ai_renderer连接管理 | 重复编辑全局密钥；统一配置中心 | 旧调用者全部转向同一连接入口，往返保留项目草稿；不在原型迁密钥 |
| AI页的template routing + 流程编辑 | 路由归属不清；迁入流程设置 | 同一模板草稿来源，连接页仅连接；未保存切页先确认 |
| Agent工具文本框/复选框，工具使用关系 | 授权易被误认为两份；单个Agent授权编辑器 | 保留空allowlist与ID；工具页只读反查使用，不自动补权 |
| 项目默认/节点配置/recipe命令回填 | 当前存在回填，不等于明确继承 | 列出有效值、来源、覆盖；未确认语义不自动合并，缺来源登记API缺口 |
| 运行摘要/阅读区/回放多处状态 | 重复信息且易串run；同一事实投影下按层显示 | 不造新状态合并器；保留历史replay/export及精确子Job入口 |
| 顶部status正常成功说明及30秒说明 | 无用户决策价值；正常态整块退出 | 紧凑更新时间与刷新，加载在局部；超时/断线/启动失败恢复保留 |
| 配置抽屉内运行详情、多层折叠 | 运行进入独立阅读区，配置只编辑 | 浏览器后退、长日志/报告、键盘焦点及窄窗验证；不靠固定高度藏内容 |

不把所有重复CSS或相同字段名当删除依据；不更换当前window.X/静态脚本技术栈。本阶段原型可独立轻量HTML/CSS/JS，正式集成另外定片，避免为设计先换框架。

## 5. 用户内容—模拟数据—现有API—能力缺口

WB05K1核对日期：2026-11-08，源码基线61c3b30。模拟对象使用独立demo ID，无真实Provider、主机和目录。以下是**唯一当前接线主表**；§7各片表格保留当时证据，不作为另一份当前能力清单。本轮只读源码、原型与既有本地证据，没有调用真实API；接口存在是静态事实，不是本轮动态通过。

分类：“可复用”表示现服务已有对应事实，仍须独立接线验收；“前置设计”表示对应页面先补可审查的交互；“前置契约”表示对应写入/控制上线前补后端语义；“后置”不阻塞首个只读职责；“真实验证”不能由模拟证明。同一行可同时有可复用部分与缺口，不要求先补完所有后端才迁一个只读页面。

| 用户内容/动作、模拟字段 | 实际HTTP方法与响应包装 | 权威事实、现生产消费者与源码位置 | 当前决定、缺口与证据边界 |
| --- | --- | --- | --- |
| 项目列表/继续；projects[id,name,goal,lastRun,updatedAt] | 现GET /api/status → payload.workspaces；手动全局刷新可能/api/refresh。GET /api/workspaces → {workspaces}、GET /api/workspaces/{id} → {workspace}仍可用 | state/workspaces/crud.py::list_workspaces、state/monitoring.py::workspace_public_payload。现app.js::loadStatus→applyStatusPayload→state.workspaces→renderWorkspaces；DOM仅#workspaceHistoryList/计数 | **可复用、设计已限定验收、正式展示待接**：不是GET /api/execution-overview（后者是跨执行列表）。现列表返回完整公开workspace及派生runs/automation，没有独立轻量列表schema；先只投影所需字段，不为美化立刻新造列表服务。updated_at、inputs目标、最新run取值须按公开字段核，不能照搬原型lastRun文案或用运行创建时间冒充项目更新时间。WB05K2/L4已验限定模拟区域读取；L4据实际消费者将原候选“新增GET读者”改为复用共享快照，避免双请求/状态副本。workspace:false等共享刷新路径尚不重绘列表，须最小接线并验焦点/草稿；旧drawer只单组件退出，保既有选择/删除和运行reader。真实字段/缺值/更新时间及网络仍须验，具体唯一执行片见第三部分WB06A。 |
| 三步创建/保存；draft、project.goal/repo/paper/data/constraints/flowSelection | POST /api/workspaces → {workspace}，201；POST或PUT /api/workspaces/{id} → {workspace} | crud.py::create_workspace/update_workspace；app.js::submitWorkspace实际用POST，核保存回执id后合并，不以全局刷新代替保存成功 | **可复用+前置契约**：inputs的goal_text/repo_urls/paper_urls/context_blocks与主仓库/论文/独立idea、notes不猜合并。当前未知template_id可回退首模板；更新是浅合并再normalize，不证明局部表单保真或并发安全（G27）。原型缺项可保存、取消/草稿与明确采用已有模拟证据，真实写入须另验；不能把未展示高级值清空。 |
| 流程目录/选择/编辑；flows、flowSelection | GET /api/workflow-templates → {workflow_templates}；GET /api/workflow-templates/{id} → {workflow_template}；POST集合新增、PUT /{id}更新 → {workflow_template}，POST /{id}兼容更新；DELETE /{id} → {ok:true} | state/registry.py模板CRUD；schema/templates.py已有version_history；workflow_template_lifecycle_actions.js先POST集合/preview或/{id}/preview校验，再新增POST/更新PUT保存并核实例迁移差异 | **读可复用、编辑前置契约**：复用既有版本/迁移，不复制flows.revision平台。原型enabled不同于模板status，说明空串会被or回填，删除无完整引用保护。POST /workspaces/{id}/automation/apply会写配置，不是“选择流程”的纯读取。固定两演示流程不证明真实引擎支持任意流程（WB04D1/D2）。 |
| 主机+目录+环境；hostId/path/environment、模拟diagnostics | GET /api/workspaces/{id}/cockpit → {workspace_id,cockpit,execution,automation}；配置值取GET workspace的server_id/workspace_dir/env及节点配置 | state/monitoring.py::workspace_cockpit_payload；cockpit/readiness沿现自动化与主机事实派生；app.js::refreshWorkspaceCockpit/mergeWorkspaceCockpitPayload是现消费者 | **可复用+真实验证**：只显示对应流程必需字段；字符串绝对路径不证明目标主机可写/环境可运行，资源采样不等于预留。模拟repair主机/目录按钮不接成通用修复API，也不通过POST /run探测“纯就绪”。现cockpit不是run提交快照（WB02/04A/F2）。 |
| 模型连接与项目选择；connections、modelConnection | GET /api/provider-profiles → {provider_profiles}；GET /{id}、POST集合、PUT /{id}及兼容POST /{id} → {provider_profile}；DELETE /{id} → {ok:true}。POST /api/provider-profiles/test → {test}，/models → {models} | registry.py::update_provider_profile/delete_provider_profile；registry_pkg/provider_profiles.py::provider_profile_public_payload；app.js::loadProviderProfiles/saveProviderProfile，现更新用PUT | **读可复用、写前置契约**：has_api_key/key_required/status/missing_fields表示字段完整性，不是联网成功；不读取非公开key。enabled/revision/引用占用保护不是现合同，空api_key保留旧值而非删除；现前端PUT 404后POST新增不适用于“记录已删除”的新语义。优先复用provider_route_hash（不含凭据，不当凭据版本）。真实凭据迁config另片，不在原型添加key表单（WB04B1）。 |
| 项目默认与步骤模型覆盖；stepModels[templateId+stepKey]、effective/source | 更新workspace.model；现路由字段provider_profile_id/routing_mode/chat_agent_id/notes，Agent定义可有provider_profile_id；不是stepModels API | schema/recipe.py::normalize_workspace_model；automation/topology.py::workspace_model_route_for_agent；state/workspaces/workflow.py::_workspace_agent_execution_checks | **前置契约**：现为Agent级覆盖，空覆盖回项目默认；同Agent两步骤不能直接表达独立步骤覆盖。项目Profile空串还可能回填旧值。需先定作用域、显式清空/失效不回退及来源，再接原型B2；不再造第二路由解释器，不把现chat_agent_id可清空结论推到Profile。 |
| Agent目录、绑定与唯一工具授权；agents、tools、usageRefs | GET /api/agent-definitions、/api/tool-definitions → {agent_definitions}/{tool_definitions}；GET详情、POST集合、PUT /{id}和兼容POST /{id} → {agent_definition}/{tool_definition}；DELETE → {ok:true} | state/registry.py CRUD；schema/agents_tools.py；app.js::saveGlobalAgentDefinition/saveGlobalToolDefinition。服务端目录及实例快照是事实，公开registry/dispatcher决定可用能力 | **读可复用、编辑前置契约**：工具新页只读，不自动调用preview/test。Agent.tools=[]已有保留逻辑，复用而非另造授权合并器；未知引用保真须按分支验。Agent用途清空可能回填；重命名/删除会重写模板或授权引用，无完整占用保护/显式采用事务。目录注册不等于所有上下文可执行（WB04C1/C2）。 |
| 启动/受理；run.id/plan/status、模拟start | POST /api/workspaces/{id}/run → {workspace,run,run_id,jobs,execution_package,applied,evidence_applied,replayed}，201；readiness冲突409含blocked_checks等 | workflow.py::run_workspace_workflow及workflow_records.py::replay_workflow_response；web/workspace/workspace_workflow_submission.js::submit已有request_id持久重发与参数一致性检查 | **可复用+前置设计/真实验证**：受理不等于完成，传输失败可能结果未知，先用同request_id核对而非生成新run。POST /runs只登记记录，不是启动入口。原型明确演示动作不接生产推进；真实引擎仍受现门禁限制。I1静态重载不覆盖该不确定受理场景。 |
| 当前步骤/完整计划/历史；plan、attempts、waitingOn、run.snapshot | GET /workspaces/{id}/runs → {workspace_id,runs}；/runs/{rid} → {workspace_id,run}；/runs/{rid}/replay → {workspace_id,run_id,replay}，均在/api下 | state/workspaces/runs.py::list/get/replay；execution/run_records.py公开run有steps/progress/execution_plan/attempts/submissions/continuation_stop/package_snapshot/plan_hash。web/workspace/workspace_run_detail_actions.js与app.js合并读者；事件消费者workspace_event_stream.js | **可复用+真实验证**：持久RunStore冻结workspace_snapshot，但公开execution_plan只含schema_version/engine_version/steps，不等于原型完整run.snapshot。标题/目标/Agent/模型等逐字段证实公开快照位置，无字段显示“未记录”，不补当前配置。SSE仅通知重读，404不跳latest。GET可先同步Job/图记录；浏览器只读不代表服务器绝无同步写入（WB03A/B/G2）。 |
| 历史内查找/返回；run.number/snapshot.goal、views.query/y/focus | 上述/runs支持status/node_kind/job_id/agent_execution_id/created_after/created_before；无目标全文q或分页合同。/runs/compare?base=&target= → {workspace_id,base_run_id,target_run_id,compare} | runs.py与execution/run_records.py::filter_workspace_execution_runs；普通public默认limit=50，超出者带plan_hash仍保留；replay/export另外用full_runs投影。现workspace_run_detail_actions.js读compare | **限定可复用、额外筛选/比较后置**：不是硬性“永远最多50条”，也不能称全量搜索。无plan_hash旧记录可能被裁剪；精确详情/report同样先查普通public runs，旧ID未命中可404。原型次数非服务端run字段；按冻结目标检索先证明公开快照来源。H1本地检索已建，不再记“历史检索全部未建”。 |
| 关联子任务/日志；jobs.id/host/path/status/log | GET /api/jobs/{jid}/log，默认lines=200/max_bytes=131072；可传offset读chunk。返回job_id/mode/log与source/exists/line_count/next_offset/file_size，chunk另含截断/跳字节等；缺Job404，部分错误在payload.error | state/jobs_pkg/execution.py::job_log_payload；app.js::refreshJobOutputTab/mergeWorkspaceJobLogDelta；引用须来自本run/step/attempt的job_id/child_job_ids | **可复用+前置设计/真实验证**：保tail/chunk/缓存snapshot区别，不能把空串或缓存当实时全日志，缺字段不猜。远程读取可能SSH并写本地缓存，本轮未调用；原型C1仅静态全文阅读，不能据此证明流、断线恢复或远端文件。 |
| 停止后续、子任务独立状态；stopRequested/childStillRunning | POST /api/workspaces/{id}/runs/{rid}/stop-continuation；输入parent_attempt_id/child_job_id/child_policy=keep_running，返回{run,continuation_stop,replayed,child_policy,child_stop_requested:false}；身份/时序冲突409 | workflow_records.py::stop_workspace_run_continuation只接受已确认N04两步child链；workspace_run_detail_actions.js::controlContinuation已有未知回执后GET原run核对 | **限定可复用+前置契约/真实验证**：不是通用任意阶段停止API。原型blocked/Agent处理等模拟停止不能一律接此路由；未支持状态明确禁用/说明，不假停child，不能放宽门禁补画面。 |
| 报告声明/正文/交付与正文下载；report.declared/body/verification | GET /api/workspaces/{id}/runs/{rid}/report → {workspace_id,run_id,report}；report含file_verified/status/reason/content等，无报告返回incomplete且content=null | runs.py::get_workspace_execution_report只取本run首个eval.report，通过核验才取匹配artifact.content；workspace_run_report.js核workspace/run/step/attempt身份后展示 | **可复用+真实验证**：WB03B/C2模拟正文阅读/下载已建；模拟有正文未核验仍可读与现API不同，正式先只读已核验正文。若要未核验文本另定义来源/授权，不能回退inline answer冒充文件。声明、写入、核验按钮不迁生产。执行100%与交付完整分开，不能只看delivery_closure.status。 |
| 完整证据导出、比较 | GET /api/workspaces/{id}/runs/{rid}/export → {workspace_id,run_id,export}；export含filename/workspace/run/summary/manifest/readme_markdown/replay/logs/artifacts/reports等 | runs.py::get_workspace_execution_run_export；execution/run_export.py；workspace_run_detail_actions.js已有读取/下载消费者 | **可复用、原型新增入口后置**：现API不是“后端完全缺导出”，正文Blob下载也不是完整证据包。manifest有日志/子引用/事件截断和缺失提示，不能命名“完整”就承诺无限日志和所有文件；先核包与脱敏再接。 |
| 首次启动与区域读取失败 | HTML/static assets；原型boot.ready/failed；K2增加独立列表读取视图与手动Promise结果 | 本地boot.js只管首次静态启动；正式app.js::loadStatus/refreshWorkspaceCockpit与现请求预算/错误恢复是另一消费者 | **设计已限定模拟验证、真实接入待验**：I1负责静态启动，K2负责一个列表区域的加载/失败/保旧/重试/过期响应。没有顶栏成功块，重试不启动任务；其余读者迁移时按同一规则各自验收，不把K2当全站网络恢复框架。 |
| 按需辅助聊天；chats[projectId,agentId,draft,messages,pending]、冻结origin | POST /api/workspaces/{id}/chat，text/role/agent_id/use_llm/stream；非流式{workspace,messages,execution?}，stream:true先JSON {workspace,messages,stream:true}再后台发聊天事件，并非该POST本身为token流 | state/workspaces/chat.py；app.js::submitWorkspaceChat/submitWorkspaceUseChat及事件消费者。现会写model.chat_agent_id、可执行Agent授权工具、取整个项目最近10条上下文 | **前置契约，独立后置接入**：无原型run/step冻结来源或消息幂等合同，流式还可重读当前模型/Agent；缺模型可回退规则占位。必须独立无工具用途、隔离、发送快照、重试与真实失败合同；不能直接接作无副作用讨论，也不让此缺口阻塞项目只读列表（WB04E/D2）。 |

以上实际路由见[GET](../total_control/http_api/get_routes.py)、[POST](../total_control/http_api/post_routes.py)、[PUT](../total_control/http_api/put_routes.py)、[DELETE](../total_control/http_api/delete_routes.py)。服务事实见[工作区CRUD](../total_control/state/workspaces/crud.py)、[公开投影](../total_control/state/monitoring.py)、[运行读取](../total_control/state/workspaces/runs.py)、[冻结与停止](../total_control/state/workspaces/workflow_records.py)、[模型路由](../total_control/workspace/automation/topology.py)、[能力目录](../total_control/state/registry.py)、[日志](../total_control/state/jobs_pkg/execution.py)、[辅助聊天](../total_control/state/workspaces/chat.py)。生产入口仍有消费者，K1没有删除任何生产或原型路径；正式替换一个职责并验证后再退出对应旧展示，不保留两个推进器或状态合并器。

### 剩余需求的处理决定与本阶段收尾条件

**当前收尾结论：WB05L4已按原五目标与当前证据收尾，本轮需求/布局/可点击模拟原型完成。** 这不是正式页面或整个研究工作台完成。§2的58控件逐项决定及§7 WB05A的16类/50config保真继续有效：未展示≠删除，语义不明不合并；高级编辑按归属/合同后续接入，不为本轮堆CRUD。项目列表/创建/运行/步骤日志/历史报告/设置/配置中心及按需对话有模拟入口，监控/执行/活动仅必要导航壳；真实读取与控制另片。

- **列表读取设计点已补，限定模拟**：WB05K2已实际验证首次加载、成功空列表、首次失败重试、已有数据刷新失败保旧、旧响应不覆盖较新读取或离开后的页面。正常不占顶栏，手动完成Promise，不用动画假造运行。真实网络取新数据/断线/超时仍待正式接入，不把一个列表区域推广为全站通过。
- **脏稿按现有两种行为验收，不把所有页面改成一种弹窗**：站内离开编辑确认放弃；刷新/整页打开仍可恢复同实体未保存草稿，保存前不得写入项目/目录。已有A/B/C/D/E的限定模拟证据和WB05A整页无确认但保草稿证据可用；没有全站beforeunload承诺。存储失败有错误但跨标签页/关标签后恢复未验，不承诺耐久。最终闭环须检查“继续编辑/放弃/刷新/换项目”各自实际路径，不因缺整页弹窗就预排新功能。
- **高级项已有归属，逐个正式接入时保真**：基本项目设置只留常用值；命令/env管理器/调度/标签/独立idea与notes进项目设置的独立高级编辑，提示词/预算/输出约束归Agent编辑，节点config/输入映射归流程专门编辑，内部ID/幂等键归诊断。没有编辑能力时不放空按钮，保留旧生产专门入口与数据；新只读页不发保存，未来基本保存必须以未编辑字段往返测试作为准入，不为50项补通用CRUD。
- **必要跨区导航已限定模拟验收（WB05L2）**：五入口/当前区/统一顶栏、三区最小导航壳与配置目录连续往返均已实际点击，原项目/精确run/步骤/日志/报告来源可返回；全局无来源不猜最近项目，坏引用明确不可用。小屏品牌与可换行文字导航，不复制监控/执行/活动业务正文。来源沿URL与原视图/离开内核，不另造状态库。此设计阻断已解除；生产`data-view=console/workspace/exec/activity`的真实接线仍独立验收，模拟壳不是真实监控、命令或活动能力。
- **失败页主操作层级已限定模拟验收（WB05L3）**：失败概览只有“查看失败步骤”为primary，取本次status=failed的精确步骤；新运行和原就绪诊断移至证据之后，复用run-next且新运行普通样式。缺失败记录明确不可用，不换其他step/log。四宽网页失败、退出7/下游未执行、历史/两项目、相对路径失效阻启动与修复返回/明确新run均实际点击；不改旧状态/快照/门禁。早轮比较间歇失败未归因与最终证据分开记在§7，不能称可靠性问题已消除。
- **其他后置边界不取消**：完整证据导出/比较、更多筛选、极长下载错误进一步精简属独立职责；高级值保真按上条契约。真实网络、SSE、Provider、SSH/GPU/Transfer、物理交付只在对应真实接线验收，不复制模拟状态核补齐事实。屏幕阅读器/关闭标签后耐久恢复/真实新手研究未验证，不冒称全站通过。
- **WB05限定模拟设计已完成收尾**：L4五目标与原验收场景逐项矩阵、当前四宽完整网页主线、区域读取及精确输入调查见§7。原早轮比较无差异DOM，仍未归因/未证明消除；本轮未复现不当可靠性承诺，不据猜测继续加美化。真实业务/G40/G26/G27仍开放，后续唯一职责见WB06A，不自动将正式迁移纳入本轮完成声明。

**原正式接线候选WB06A仅为单一项目列表展示职责；按UI01暂缓。** L4核现正式消费者后，优先复用loadStatus→applyStatusPayload→state.workspaces，GET /api/workspaces保作可用API而不另造读者/轮询。退出旧#workspaceHistoryList所在drawer及列表行资源/命令/节点重复展示，保同一个列表/计数与原select/delete委派；删除仍是原危险操作/确认，不能说整个组件绝无写动作。创建/运行/设置/配置中心保持原入口，本片不正式搬三步创建。workspace:false共享刷新后列表不会重绘是已核装配缺口，须最小同步且不扰配置草稿/精确run/阅读焦点；记录时间、缺值/未知状态和数据来源按第三部分唯一WB06A合同验。沿现全局刷新不能声称只刷新列表或无主机读取。没有真实环境的格子仍未验；不fallback模拟，不复制fixture/版本/聊天/推进核。

原型adapter只处理本地fixture与演示草稿；禁止访问/api、SSE、真实Provider及真实文件。正式API接线用真实服务读者替换对应fixture职责，不把本地版本/聊天/推进状态机照搬，不设“失败时转模拟成功”的fallback。本轮未引入依赖或开源平台；现HTTP与版本/幂等/投影组件已够完成交接，不为审计新造能力。

## 6. 原型交互与视觉约定

### 三步创建草图

```text
新建项目                              演示模式
1 目标与资料 → 2 选择流程 → 3 运行设置
第一步：目标（必填）
        添加资料（可选）：仓库 / 论文 / 数据位置
        约束与成功标准（可选，不再堆多个同义大框）
第二步：流程名称、用途、将执行哪些步骤、支持范围
第三步：仅该流程需要的连接 / 主机+目录 / 环境或计算策略
        摘要：项目名（可改）、目标、流程、缺项
上一步                                  创建项目
成功 → 项目运行页（尚未开始） → 明确点击“开始运行”
```

名称可由目标首句生成并允许改。切换流程前保留公共输入，移除不适用的专属配置要提示，不静默丢已有值。缺模型/主机/目录时只给一个“去配置”入口，保存returnTo与创建草稿；修复后回到第三步重校验。后续WB04未做前，WB02使用明确标识的最小演示修复面板，不伪称配置中心已交付。

路由保存projectId/runId/stepId与返回页；浏览器前进后退恢复所选对象，刷新重新读演示存储。内存草稿不误保存为项目：离开时继续编辑/放弃明确二选；若使用sessionStorage保存演示草稿需命名空间及版本，只存虚构资料，重置演示可清除。切项目前检查未保存项；不存在的ID显示不可用，不改指向其他项目。保存失败保留用户值；保存回执才更新已保存状态。

演示场景由固定fixture和明确动作切换，不用动画/定时器假造进展：首次空列表、已有项目、缺连接、主机不可用、目录错误、等待子任务、运行失败、停止后续、正常完成、交付不完整、长名称/长错误/长日志、空历史。场景入口放独立“演示场景”菜单，页顶持续小标“演示模式 · 模拟数据”；不要在业务主区放开发面板。模拟修复、模拟完成动作要标明模拟，与用户启动/配置动作分开。

### 视觉基线

| 项目 | 约定 | 验收重点 |
| --- | --- | --- |
| 色彩 | 浅灰背景#f5f7fa、白内容、正文#182230、蓝强调#2459d3；状态色同时配文字 | 正文对比度至少4.5:1；原型实际核对，不凭色号宣称通过 |
| 字体/间距 | 本地系统字体，正文约14–16px、标题20–28px；间距以4/8px节奏 | 长中文/路径换行，无外部字体请求 |
| 分组 | 标题+留白为主，少量分隔线；每区一个主操作 | 不堆同尺寸卡、不多层抽屉、不以隐藏溢出遮内容 |
| 响应式 | 1440完整桌面；1024缩侧栏；768与390顺序单列/详情独立阅读 | 文本与按钮不遮挡；代码日志允许自身横滚，页面不横溢 |
| 键盘 | 原生控件/语义标签，清晰focus-visible；弹层焦点恢复 | Tab顺序跟阅读顺序，Escape/关闭可返回触发点 |
| 反馈 | 局部加载、就近错误、简短恢复动作 | 正常不常驻技术解释；错误长文独立阅读 |

## 7. 切片交付与验收记录方式

| 切片 | 本片交付 | 明确不做 | 当前状态 |
| --- | --- | --- | --- |
| WB01 | 本文完整职责/字段/状态/接口及消融决定，更新正式二三文档 | 原型、生产页面、API及依赖 | 文档覆盖检查及只读审查完成；浏览器未验收 |
| WB02 | 项目列表、三步创建、缺项返回、保存后继续；本地启动说明 | 完整运行结果、全局复杂编辑 | 独立模拟交互已验收，详见下表 |
| WB03A | 当前运行、步骤/子任务日志、等待/阻塞/失败/停止后续 | 历史列表、报告正文、新后端能力 | 独立模拟交互已验收，见下文 |
| WB03B | 历史、报告、结果交付完整/缺失及阅读往返 | 新后端能力、复杂配置编辑 | 独立模拟交互已验收，见下文 |
| WB04A | 项目资料与运行环境设置/保存与取消/来源提示 | 节点覆盖、完整配置中心、真实密钥迁移 | 独立模拟交互已验收，见下文 |
| WB04B1 | 模型连接目录、只读使用关系与项目选择往返 | 真实凭据、其他能力编辑、节点覆盖 | 独立模拟交互已验收，见下文 |
| WB04B2 | 既有Agent步骤模型覆盖/还原项目默认 | 全局Agent/工具、流程增删、DAG | 独立模拟交互已验收，见下文 |
| WB04C1 | Agent基本目录与既有步骤绑定 | 工具授权/目录、预算/输出契约、流程编辑、真实调用 | 独立模拟交互已验收，见下文 |
| WB04C2 | Agent工具授权与只读已知工具目录 | 工具目录编辑/注册、真实调用/安全门禁、流程编辑 | 独立模拟交互已验收，见下文 |
| WB04D1 | 可复用流程只读目录与创建选择往返 | 流程CRUD/DAG、版本库、项目换流程、真实接线 | 独立模拟交互已验收，见下文 |
| WB04D2 | 固定流程名称/说明/启用编辑与项目引用保真 | 新增删除流程、步骤/拓扑编辑、完整版本库、真实接线 | 独立模拟交互已验收，见下文 |
| WB04E | 项目关联、按需Agent辅助对话及来源往返 | 配置自动修改、工作流控制、真实Provider/工具调用 | 独立模拟交互已验收，见下文 |
| 后续候选 | 节点高级编辑/更多流程仅在实际需求证明后拆片 | 为配置齐全堆CRUD、与真实接线混片 | 不是当前执行片；现模拟目录不代表生产能力完成 |
| WB05A | 整体需求/体验证据总核，字段/能力/缺口映射与唯一后续实现片计划 | 后端接线、批量改多页、提前宣称全站通过 | 仅审计/设计交接已完成，见下文 |
| WB05B1 | 项目设置页分区与配置诊断精简 | 创建/目录/运行重排、保存/门禁语义改变、真实API | 限定模拟验收，见下文 |
| WB05B2 | 创建第三步信息减负 | 第一/二步、设置/目录/运行重排、改变保存/门禁 | 限定模拟验收，见下文 |
| WB05C1 | 子任务日志阅读/直接返回本次运行 | 下载导出/历史检索、运行状态内核、真实日志流 | 限定模拟验收，见下文 |
| WB05C2 | 本次报告正文下载/缺失反馈 | 完整证据导出、生成/存储/核验语义、真实文件 | 限定模拟验收，见下文 |
| WB05D1 | 短时通知的页面归属与跨页清理 | 长错误/脏稿策略/历史检索、其他布局或内核 | 限定模拟验收，见下文 |
| WB05D2 | 辅助对话失败阅读/重试入口 | 下载长错、全站错误框架、聊天/运行内核与真实接线 | 限定模拟验收，见下文 |
| WB05E1 | 已有项目未知流程的资料保存边界 | 流程修复/迁移、自动采用、创建/启动门禁、真实接线 | 限定模拟验收，见下文 |
| WB05E2 | 缺流程身份记录的只读引用防御 | 自动补默认/版本、流程迁移、旧run按钮/概览、真实接线 | 限定模拟验收，见下文 |
| WB05F1 | 已有运行页的新运行就绪反馈 | 历史事实/执行内核、无run概览、第二就绪内核、真实接线 | 限定模拟验收，见下文 |
| WB05F2 | 无运行准备概览的未确认配置呈现 | 新门禁/默认迁移、历史run/设置表单、真实接线 | 限定模拟验收，见下文 |
| WB05G1 | 准备概览长文本阅读与主操作可达性 | 有run/全站标题、存储裁剪、语义猜重、门禁/真实接线 | 限定模拟验收，见下文 |
| WB05G2 | 运行概览提交快照的长标题阅读 | step/job/history/chat/report、配置来源/模型诊断/执行内核 | 限定模拟验收，见下文 |
| WB05H1 | 运行历史最小检索与返回恢复 | 状态筛选/分页/跨项目/导出、其他页标题/后端接线 | 限定模拟验收，见下文 |
| WB05I1 | 首次静态加载与启动失败恢复 | API/SSE/超时预算/业务恢复、后端/生产接线 | 限定模拟验收，见下文 |
| WB05J1 | 已完成运行的主操作层级 | 新运行/报告动作及门禁语义、其他状态/页面、真实接线 | 限定模拟验收，见下文 |
| WB05K1 | 剩余需求分类、现HTTP/schema/权威事实与消费者交接、唯一后续片 | 原型/生产实现、真实API/任务、全仓重审 | 只读审计完成，§5为当前主表；未关闭WB05 |
| WB05K2 | 项目列表区域读取与失败恢复模拟 | 真实接线、全站读取框架、业务状态修改 | 限定模拟验收，见下文 |
| WB05L1 | 原始闭环核证与正式首片交接条件 | 新功能/批量修复、真实接线、重审全部后端 | 核证已完成；核心模拟通过，设计阶段未关闭，见下文 |
| WB05L2 | 最小跨区导航/顶栏与精确来源返回模拟 | 深入改版监控/执行/活动正文、真实接线、failed动作改动 | 限定模拟验收，见下文 |
| WB05L3 | failed页先诊断本次失败、次要新运行动作 | 批量改其他状态、真实接线/业务恢复 | 限定模拟验收，见下文；早比较间歇边界未消除 |
| WB05L4 | 原五目标的整体收尾核验、间歇比较调查与正式首片交接 | 新功能/美化、原型或正式业务改动、全仓重审 | 已完成收尾核验，五目标限定模拟设计完成；真实产品仍开放 |
| WB06A | 正式单一项目列表展示，复用共享快照 | 整站/新三步创建/后端迁移、新读取/状态框架 | 按UI01暂缓，原合同保留 |
| UI01 | 原功能卡/只读示例 | 各区完整交互、生产接线 | 历史点击通过；卡片首页被UI02退出 |
| UI02 | 默认监控首页校正及主机详情阅读 | 真实采样/生产迁移/提交或停止 | 限定模拟验收，UI01卡片首页退出 |
| UI03A | 原远程任务列表/详情阅读设计 | 当时将提交/终端写操作/真实后端后置 | 已暂停；当前调查与唯一下一片见§0 |

WB02开始前补本地切片开场记录，明确文件边界（仅dev_work下独立原型及相关文档）。每次完成后审查、更新二三部分、提交推送安全文档；原型/截图/测试不提交。原型入口与命令写在本地README，后续必须给用户可访问链接，而不是只给截图路径。

浏览器验收逐格记录视口、入口、点击路径、fixture版本、截图和真实/模拟来源。必查1440/1024/768/390；鼠标及键盘焦点；首次创建/已有项目继续；缺连接/主机/目录修复返回；正常/等待/阻塞/失败/停止/交付缺失；取消编辑、切项目、前进后退、刷新；长内容/空列表/区域加载与失败。WB01文档片当时所有浏览器格均**未验收**，后续各片的实际证据见下文，文档检查不能替代点击验证。分片只记录实际跑过格子，WB05闭合整体矩阵；静态截图不能冒充交互通过。

### WB02实际验收记录（2026-11-07）

本地入口 `http://127.0.0.1:8933/`，启动：在仓库根执行 `python -m http.server 8933 --bind 127.0.0.1 --directory dev_work/workbench-prototype`。原型与README仅本地；无依赖生产服务、配置、Provider或任务。使用系统字体和静态脚本，没有新增运行依赖。

| 内容/点击路径 | 实际结果与边界 |
| --- | --- |
| 空列表→创建→目标/可选多链接→流程→设置→创建 | 已保存模拟项目，明确尚未开始；开始运行按钮禁用并标下一片，不造run |
| 已有项目→继续；两个项目分别创建/选择/刷新 | 身份和内容不串；列表可搜索，无匹配有提示；未知ID明确不可用 |
| CPU流程↔资料分析 | 按流程显示主机/目录或仅模型；公共资料与不适用设置保留，不隐式清空 |
| 缺模型/主机不可用/目录错误→去配置→模拟修复→返回 | 同一草稿与名称保留，修复页刷新仍能返回；不接收密钥、不访问主机/文件 |
| 保存不完整项目→补齐设置→保存 | 修改同一模拟项目，不创建运行；完整配置编辑仍待WB04 |
| 未保存取消/浏览器后退→拒绝放弃；接受放弃；前进/刷新 | 草稿只在sessionStorage演示命名空间；刷新后3→2→1→离开拒绝及两项目场景均实际验证；放弃不覆盖项目 |
| 保存失败→再次显式保存 | 固定故障首回失败、输入保留，再点击才成功；不自动重试、不补记录 |
| 1440/1024/768/390 | 各宽度列表、创建、流程、长名/长错误、完整创建及刷新后后退通过；无页面横溢；Tab从目标到可选资料顺序、错误焦点及场景弹窗Escape返回触发点通过 |
| 静态/浏览器检查 | 两JS node --check、脚本顺序/资源存在/静态ID唯一通过；Chromium29组行为检查，无pageerror/console错误；网络只有本机静态文件，CSP connect-src none |

证据在本地`dev_work/artifacts/wb02/`（`result.json`、`browser-final.log`、四视口截图）；脚本在`dev_work/smokes/wb02_browser.py`。截图自审发现旧浮层提示遮输入，已改非浮层提示并删除无用重置/成功toast。扩展验证发现最终提交校验能阻止错误URL但不定位字段，已修为统一提交校验并回第一步；复跑通过。另一次harness从未保存草稿跳未知ID未处理确认，浏览器默认拒绝离开；改脚本真实确认并等待导航，未绕产品检查，两次失败日志均保留本地。

本片没有生产旧入口退出：原型独立、旧消费者仍使用正式页面，不能在模拟验收后删生产代码；原型中不保留重复目标表单、聊天列或浮动成功提示。完整键盘无鼠标操作、区域网络加载/断线、运行状态/日志/报告、配置中心复杂编辑、真实后端能力均不在本片通过范围，后续对应切片继续验收；29组通过不代表WB03–WB05完成。

### WB03A实际验收记录（2026-11-07）

WB03按可独立验收的职责拆A/B，不改变完整设计目标：本片只做当前执行过程，下一片才做历史/报告。入口仍为 `http://127.0.0.1:8933/`，本地README已更新操作路径，生产代码和后端未动。

```text
项目（已保存）→ 开始运行（模拟）→ 完整步骤与当前等待
                                      ├ 步骤：输入 / 本次输出 / 子任务入口
                                      └ 子任务日志：主机 / 路径 / CPU / 环境 / 独立日志区
演示动作：子任务返回 → 分析处理 → 执行结束（交付尚未验证）
控制动作：停止后续 → 当前任务仍运行 → 返回结果后跳过后续
```

| 交互/语义 | 本片实际证据 |
| --- | --- |
| WB02创建→明确启动 | 实际点击完整创建，创建时runs为空；双击启动仍只有一个run、完整两步计划、一个child；未配齐设置时按钮禁用 |
| 完整计划/快照 | 单一`run_adapter.js`模拟场景解释器；计划登记事件先于虚构Job生成；快照clone项目和流程，运行标题/目标读取快照；这仅证明原型顺序，不证明真实副作用持久化屏障 |
| 等待/精确阅读 | 等待时后续pending/0完成；时间等待及刷新不推进；精确run/step/job URL；日志与步骤返回同run并恢复步骤焦点；错身份/缺记录显示不可用不fallback |
| 本次交接/结束 | 明确点击模拟Job返回后才绑定同run/job输出并启动分析；再次模拟分析完成后2/2步骤，但交付仍not_verified；不造报告 |
| 阻塞/失败 | 阻塞无Job，显式模拟条件满足后同run提交一次；失败留退出码7与原因、后续skipped，无Agent启动 |
| 停止后续 | 取消确认不改变状态；接受只记stopRequested，child/Agent仍运行；结果到达才收尾，未执行后续保留skipped。阻塞时可停止且不造Job |
| 幂等/快照/旧记录 | 10组本地契约验证重复启动/通知/停止、错归属不变、项目改动不改旧快照、新run新身份。浏览器实际双击、新run后旧run链接与前后退可读，未注入终态 |
| 四视口 | 1440/1024/768/390实际启动/步骤/局部双向滚动长日志/长错误/刷新，无主页面横溢；日志键盘焦点、返回步骤焦点、状态变更标题焦点通过。另4宽度实际反向Tab到“跳到内容”→Enter，保留路由并聚焦主区 |
| 回归与隔离 | WB03A Chromium20组、WB02创建29组回归、10组模拟契约通过；4脚本语法/加载顺序/静态ID/CSP检查通过；网络仅本地静态资源，无console/pageerror。没有真实模型/主机/工作流能力验收 |

过程：实际双击暴露换页后第二击误入步骤（无重复run但意外导航），已限制一个多击序列仅处理首次链接/按钮动作，adapter幂等仍独立保留；失败时主操作由直接日志改为失败步骤入口，保留日志入口。初始harness标题匹配两个元素、新增静态资源未加入旧回归精确清单是脚本问题，修定位与两项资源清单后通过，未关闭网络门禁。截图中负top隐藏skip在full_page采集出现伪影，DOM证据为未聚焦/viewport外，不当成真实遮挡；改标准裁剪隐藏并验实际键盘跳转。步骤输入输出默认中文标签，不默认铺内部ID/嵌套JSON；标识留单独诊断入口。

原型的推进仅在一个adapter，renderer只读，app路由/保存事务；移除新引入的project状态写回副本，列表读同一runs事实。原WB02“下一片运行”禁用按钮已被本片显式启动取代；原型旧准备页仍服务无run项目，无第二份运行面板。生产旧入口仍有调用者，未因模拟验收删除。产物在本地`dev_work/artifacts/wb03a/`，脚本`dev_work/smokes/wb03a_*`；原型、测试、截图不提交。

WB03A当时尚未验收：历史列表/报告正文/交付完整、跨报告返回、配置中心与设置、完整纯键盘闭环、区域网络加载/断线、真实Provider/任务/文件。演示unblock不代表正式后端通用阻塞恢复；新运行不是原run重试，不宣称attempt重试能力。WB03A当时交接WB03B补历史与报告，G40和产品能力缺口继续开放，当前进度见下节。

### WB03B实际验收记录（2026-11-07）

本片接上历史与报告，入口仍 `http://127.0.0.1:8933/`。独立原型，不接生产后端；报告正文确实保存在本地演示状态，核验仍是固定虚构场景，不代表真实文件验证。

```text
项目：运行 / 历史
历史行：第几次 / 时间 / 执行状态 / 交付状态 → 精确运行或报告
报告：返回来源入口
      报告声明 / 正文是否存在 / 模拟核验结果
      独立正文阅读（主页面滚动，保留完整文本）
演示动作：声明 → 写入正文 → 核验；不改变已完成步骤或Job
```

| 实际点击/检查 | 结果和范围 |
| --- | --- |
| 创建→空历史→执行→报告 | 创建仍不启动；执行100%仍尚未验证；声明后无正文、写入后未核验均不完整；显式模拟核验才可完整 |
| 报告各动作与刷新 | 声明/正文/核验分别保存在session演示状态；正文刷新后完整；每步报告动作不改status/snapshot/plan/jobs |
| 历史/多run/多项目 | 同一runs列表只读投影；旧报告不被最新run替代；未知或跨项目显式run拒绝读取，历史为空不混其他项目 |
| 返回位置 | 历史→报告→刷新→历史回原条目焦点；历史→run→step→报告→刷新→step→run→历史保留归属及入口；精确URL前后退可读。项目别名入口返回会规范成同一精确run URL，不称返回原别名URL |
| 长报告 | 120段、超过2万字符、结尾可见；正文自然主滚动，不局部限高/静默截断；刷新恢复阅读位置 |
| 缺正文/核验不可用 | 两种可重复场景均显示不完整；缺正文不能模拟核验通过；有正文但核验不可用仍可阅读而不染成完整 |
| 1440/1024/768/390 | 空历史/长项目名、历史列表、完整长报告与缺正文分别截图；无页面横溢；实际键盘Enter打开报告/返回恢复焦点，刷新保留长文底部位置 |
| 行为/契约/回归 | B浏览器26组、报告10组契约、A浏览器20/契约10、创建29组回归通过；5JS语法/装配/CSP/静态ID检查通过；仅本地静态资源请求，无pageerror/console错误 |

模块仍是一个模拟场景解释器：报告动作在`run_adapter`执行终态门禁前单独分派，只接受成功执行的精确归属；Job/Agent终态不再推进。`reportDelivery`是唯一只读计算规则，历史/运行/报告共享；不写新的delivery副本，旧本地run.delivery即使声称成功也被忽略。新增`history_views`只读，未另建状态合并器。报告from只允许本项目本run、存在步骤或本项目历史；非法外部地址只回到精确run，不可跳其他项目。

设计复核修正：最初缺正文的模拟核验也能标“通过”，虽整体仍不完整但语义矛盾，已要求非空正文，否则核验不可用；去掉缺失提示的重复红字。历史来源现随步骤/日志往返保留。报告来源与焦点/滚动保存只写独立view命名空间，不改业务记录。新静态脚本明确加入装配顺序与精确网络清单，未放开CSP。未复制旧运行页，A的“报告下一片”占位已退出；生产旧入口仍有调用者，未删除。

| 新展示内容 | 模拟字段/规则 | 既有API对应 | 接线边界 |
| --- | --- | --- | --- |
| 历史与精确运行 | runs[projectId,id,number,createdAt,status,snapshot] | GET workspaces/{id}/runs、/runs/{rid}与/replay | 复用持久投影，不用最新配置覆盖历史 |
| 报告声明/正文/核验 | report[declared,body,verification]；reportDelivery | GET workspaces/{id}/runs/{rid}/report | 模拟动作不是新生产API；真实声明、落盘与实物验证沿现服务事实，缺口另立片 |
| 返回与阅读选择 | route精确ID/from + 独立views session的focus/y | 现前端路由/阅读消费者 | 视图选择不写run；历史缺记录不fallback；别名规范化需保留选择 |

证据仅本地`dev_work/artifacts/wb03b/`，脚本`dev_work/smokes/wb03b_*`。实际浏览器通过正常创建及显式模拟动作形成记录，不注入成功状态；契约中的错ID/空白正文/旧delivery伪缓存是隔离故障输入，不当真实用户路径。WB03A/B完成的是运行到报告的模拟体验；WB03B交付时尚未完成WB04设置/配置中心、WB05整体验收，也未验证真实后端、网络失联/区域加载、下载导出、比较和完整纯键盘闭环。当时交接WB04A项目资料与运行环境设置，当前指针见后续条目。

### WB04A实际验收记录（2026-11-07）

本片只补项目设置的“资料与运行环境”，入口仍为 `http://127.0.0.1:8933/`；项目内现在有运行、历史、设置。没有迁移生产页面或接后端，流程编辑、节点覆盖和配置中心仍未交付。对应R02/R06/R11/R12与G40/G26/G27。

```text
项目设置 → 返回原项目运行或历史（保留精确run）
运行 / 历史 / 设置
基本资料：名称、目标；参考资料与约束按需展开，摘要提示已填内容
运行环境：流程只读；模型连接；需要执行任务时才有主机+目录、环境名称
查看当前值与来源（按需）
取消 / 保存设置 → 返回原入口；只影响未来显式新运行
```

| 字段/信息 | 输入、条件与默认 | 校验、联动及保存影响 |
| --- | --- | --- |
| 名称、目标 | 当前项目值；两项必填 | 空值就近报错；已有项目改目标不自动改名，新建自动命名仍保留；显式保存只写该项目 |
| 仓库、论文、数据位置、约束 | 当前资料原文/空；均可选 | 仓库与论文每行http/https；未确认语义相同，不合并成背景大框；资料有错误自动展开，平时只显示已填类别数 |
| 模型连接 | 当前模型引用/空；两个演示流程都需要 | 只选择连接，不录密钥；缺项可保存但不能启动；全局维护入口留下一片，不放假链接 |
| 主机+目录 | CPU流程需要，资料分析不显示；当前值/空 | 目录按所属主机的绝对路径表达；字符串合法不代表真实可写；模拟修复只更新固定fixture诊断，不冒真实检查 |
| 环境名称 | CPU流程可选；旧项目空 | 只保存名称引用，不推断管理器、安装或可用性；显式新run冻结到snapshot、本步input与虚构Job.env；旧run不补字段 |
| 计算方式、流程 | 当前流程固定CPU，资料分析无执行位置；本片只读 | 不增加无实现支撑的GPU选项；不适用字段不参与该流程，流程/节点编辑另片 |
| 当前值与来源 | 来自已保存字段与本次草稿；未记录就明确未知 | 创建填写/目标生成名称/设置修改/模拟修复只按实际变化记录；手工改写修复值重记来源，未动字段不批量重标；无继承来源推断 |

一个草稿按创建或具体项目绑定，创建和设置复用字段、校验及保存内核；写回使用允许字段清单并保留项目身份和未编辑元数据。设置不显示运行卡、日志或历史结果。历史/当前run仍读各自提交快照，保存配置不修改任何已有run/report。来源属于项目输入记录，不另造运行状态缓存。

| 实际点击/检查 | 结果和范围 |
| --- | --- |
| 无run、活动run、已完成run进入设置 | 保存不启动；保存/取消回精确来源，历史来源亦保留；运行/报告整对象比较不变 |
| 后续显式新运行 | 新目标、目录、环境进入新snapshot/Job；旧运行和报告保持原样，不退到latest代替指定run |
| 草稿/项目隔离 | 刷新保留未保存输入但不写项目；取消确认可继续编辑或放弃；跨项目/创建拒绝离开不丢草稿；整页重新打开冲突编辑时明确恢复/放弃，不自动覆盖 |
| 前后退、地址跳转、缺失来源 | 拒绝返回后仍可再次返回原精确run；原生hash条目也有视图索引；显式缺失run显示不可用，不悄悄切最新run |
| 配置缺项与故障 | 可保存缺项，启动仍禁用；唯一修复入口返回同项目设置；确定性“设置写入故障”保留输入和原项目，显式重试才成功 |
| 来源与条件字段 | 旧字段显示未记录，未改来源不变；仅模型流程不出现主机/目录/环境；未保存值有来源提示，模拟修复与手工改写区分 |
| 1440/1024/768/390 | 长名称/长错误、字段错误可见与焦点、刷新/取消、键盘顺序实际点击并截图，无页面横溢；设置返回恢复原导航焦点 |
| 验证 | WB04A浏览器24组，创建29/运行20/历史报告26回归，以及两套10组契约通过；5脚本语法/装配/CSP检查通过，仅本地静态资源，无页面或console错误 |

过程证据区分：浏览器复现并修复干净草稿未退出导致返回旧run、原生hash无索引导致拒绝返回覆盖原历史地址；静态审查发现已有目标沿用创建命名条件与跨项目整页覆盖草稿的风险，补保护并实际回归。以上均属产品行为审查，不归为脚本错误。首轮场景名称与描述的模糊定位冲突属于harness/文案碰撞，场景改为明确“设置写入故障”；失败日志保留。最终实际重跑，没有增加等待掩盖故障，也没有用手填终态或直接修改存储代替正常路径。

截图自审将自动展开的所有参考输入改为一层按需编辑并带数量，错误自动展开；目标和运行环境不隐藏。窄屏缺项的长原因与按钮纵向排，复用同语义缺项组件，避免挤压正文。旧data-edit进入创建第三步的编辑入口已退出，创建只服务新项目；修复页复用同一草稿并按所属上下文返回。生产旧页仍有消费者，保留至真实接线，不因原型通过删除。

| 用户看到的内容 | 模拟字段 | 现有API/消费者 | 后续真实接线要求 |
| --- | --- | --- | --- |
| 项目资料编辑 | project/draft[name,goal,repo,paper,data,constraints] | POST /api/workspaces/{id}，现update_workspace；另有PUT同路径入口 | 沿用现实例输入映射，多个链接与旧背景字段不能猜合并；真实保存保真/缺项能力另验 |
| 模型、位置与环境选择 | model、host、path、environment | 实例model、目标主机/目录、env.name与节点env_name；现readiness消费者 | 名称引用不等于环境准备；正式适配要确认管理器/能力与项目覆盖，不把演示就绪布尔当事实 |
| 来源和精确返回 | fieldSources、草稿editSources/returnTo、视图索引 | 现实例normalizers与前端选择/草稿消费者 | 既有回填不代表权威来源，来源持久契约仍需核实；返回是视图行为，不写run |
| 旧run/新配置隔离 | run.snapshot与新项目值 | 现runs详情/执行包快照 | 用持久后端事实验收，原型整对象不变不能替代真实保存/重启契约 |

证据仅本地 `dev_work/artifacts/wb04a/`，脚本 `dev_work/smokes/wb04a_browser.py`；原型/截图/测试均不提交。WB04A交付时配置中心、流程/节点覆盖及WB05仍未完成，当时交接WB04B1；真实网络/主机/Provider与环境验证不属于原型验收，当前指针见后续条目。

### WB04B1实际验收记录（2026-11-07）

本片只交付配置中心的模型连接目录及项目往返，入口 `http://127.0.0.1:8933/#/connections`。项目仍在创建/设置里选择；连接编辑不保存项目。全局Agent/工具、流程目录、节点覆盖和真实Provider接线均未实施。对应R02/R03/R06/R12/R13、G40/G26/G27。

```text
配置中心 → 模型连接列表 → 独立连接编辑 → 保存/取消回列表
项目创建/设置 → 管理模型连接 → 同一目录 → 返回项目配置
项目中明确选择/采用新版本 → 保存项目 → 后续显式新运行
历史运行与报告：一直读提交快照，不随目录变化
```

| 字段/显示 | 来源、必需条件和默认 | 处理、校验与保存影响 |
| --- | --- | --- |
| 连接名称 | 用户公开描述；必填 | 仅改目录名称，不改已保存项目快照；长名自然换行 |
| 供应商、接口地址、模型名称 | 演示供应商枚举、公开基础地址与模型名；必填 | http/https地址不允许用户密码、查询参数或片段；错误消息不复述输入，输入框仍保留原输入便于修正；不发探测请求 |
| 启用、模拟凭据已配置 | 新连接默认启用、未配置模拟凭据；两个布尔值 | 可保存不完整连接；配置齐全不等于真实可连接，不录实际key；停用/缺模拟凭据阻止新提交，不改既有run |
| 连接身份与版本 | 目录生成稳定demo ID和revision | 无改动保存不升版；变更递增revision并替换当前目录记录，旧项目/运行持有的快照保留（不提供完整目录版本库），项目不会静默采用；模拟版本不是生产API已提供revision的证明 |
| 项目选择/版本 | 同一目录的选项；显式选择捕获modelConnection快照 | 旧版本显示项目所用名称与版本，明确更新后才改草稿；保存项目才用于后续run；未知引用不默认换到demo-model |
| 使用关系 | 由项目、未保存项目草稿、run快照只读反查 | 历史项带所属项目名称和运行序号；任一引用存在便拒绝删除，无引用才可确认删除；不缓存另一份使用计数 |
| 返回与草稿 | state.draft仍是唯一项目草稿；connectionDraft属于另一编辑实体 | 目录context只认同owner的创建步骤/设置来源；不接受URL外部from替代；保存目录不自动选择连接或提交项目 |

两个不同编辑实体的草稿分别保存，不克隆第二份项目草稿。目录取消只放弃目录未保存修改，保留停放的项目输入；之后取消项目也不回滚已保存的全局连接。离开整个上下文会明确确认实际将丢弃的未保存修改。刷新、原生hash、前后退、整页进入另一连接和带查询参数的目录均走一致身份规则。

| 实际点击/检查 | 结果和范围 |
| --- | --- |
| 全局目录/独立编辑 | 新建、校验、保存、取消与未引用删除；有引用显示只读项目/草稿/历史关系且禁删；空目录只有一个新建入口 |
| 变更与显式采用 | 改名/改模型不改项目；新版本阻新提交，明确采用且保存项目才恢复；无改动保存不升版；旧版选择标签保留项目名称，不偷偷换最新名称 |
| 活动run/已完成报告 | 目录停用、重新启用、采用版本、项目保存全过程与原run整对象比较不变；后续显式新运行才冻结新连接；不把模拟凭据当真实测试通过 |
| 缺模型/空目录 | 创建→唯一目录补齐模拟凭据→返回原草稿→明确采用；空目录新建后不会自动选中，项目必须明确选择。旧model修复页不再编辑配置 |
| 取消与故障 | 目录未保存返回可拒绝或放弃，仅影响目录草稿；项目未保存取消不撤销已保存目录；固定连接写入故障保留输入与原目录，显式重试成功 |
| 多项目/浏览器 | 两项目目标不串；停放草稿前后退、目录刷新及返回保留精确设置来源与模型焦点；全局导航拒绝离开保留两份不同实体草稿，确认后才放弃 |
| 错误与兼容 | 整页带query进入另一连接先处理原草稿；外部from不改合法返回上下文；旧model修复书签规范到同一目录；未知旧引用不可用，不补假配置 |
| 1440/1024/768/390 | 长名称列表/编辑、空目录、字段校验/错误消息、键盘顺序及刷新取消均实际点击并截图，无页面横溢；错误消息不重复携凭据URL，输入框本身仍保留输入 |
| 验证 | 本片浏览器30组/纯目录契约12组；创建29/运行20/历史报告26/设置24回归，两套既有10组契约通过；7脚本语法/装配/CSP检查通过，无pageerror/console错误，只请求本地静态文件 |

证据等级与过程：浏览器第二轮复现目录带query时owner识别不一致，导致返回项目入口丢失；统一路由归属后原路径复测通过。静态审查发现旧修复别名来源无效、query编辑身份遗漏、未变化快照按对象引用误记来源等风险，分别修正并用实际路径/契约覆盖。首轮读取尚未落地的空演示存储引发harness空值异常，只修检查脚本，不归为产品失败；失败日志保留。没有通过写入session状态、增加等待掩盖故障或补终态达成通过。

消融：固定模型单选项、modelReady活动标志、旧model修复写入器/卡片已退出；旧书签只做明确兼容重定向。目录定义来自同一fixture工厂，选项/诊断/版本/引用/保存只走一个纯目录内核；renderer只读，app承担路由和事务，不引入SDK、Provider协议、网络重试或第二推进器。modelReady仅在已知旧本地session缺目录时读一次作兼容后移除；只识别固定旧demo定义，不猜任意模型，历史run不补写快照。host/path修复仍有消费者保留。生产旧页面仍有真实调用者，不因原型通过删除。

| 用户看到的内容 | 模拟字段/规则 | 现有API/源码对应 | 正式接线缺口与复用 |
| --- | --- | --- | --- |
| 模型连接目录与公开编辑 | connections[id,revision,label,provider,baseUrl,model] | GET/POST /api/provider-profiles、POST/PUT /api/provider-profiles/{id}；RegistryMixin | 现CRUD可作入口，公开字段映射须按Profile实际结构适配；不把模拟revision直接照搬为另一套生产版本系统 |
| 配置状态 | enabled、credentialConfigured、diagnose | provider_profile_health、公开has_api_key/missing_fields；test/models入口存在 | 真实凭据仍在config本地管理，本片不调用test/models；模拟启用/版本交互需要正式契约，不能冒用has_api_key作为连通证明 |
| 项目采用/历史冻结 | project.modelConnection、run.snapshot | 现model.provider_profile_id、执行包与provider_route_hash | 现已有非密钥路由hash检测endpoint/model变更，优先复用；明确采用、目录显示版本及来源往返仍需独立真实接线验收 |
| 引用与删除保护 | usage(project/draft/run)、remove门禁 | 当前delete_provider_profile仅删除并保存；本轮静态核对 | 当前CRUD未提供本片完整的项目/草稿/历史占用删除保护；后续按真实引用核算，不能只在前端禁用按钮 |

环境来源备注校正（WB04B2静态复核）：保存已对environment缺字段与空字符串归一，初始来源展示也排除这种假变化，因此前述“保存无关字段误标环境来源”的描述缺乏依据。输入事件的fieldChanged仍按原值比较，来源提示边界一致性留WB05独立验证；未浏览器复现，不称已修。不借模型来源验收称全部字段来源已验。

证据在本地 `dev_work/artifacts/wb04b1/`，脚本 `dev_work/smokes/wb04b1_*`。本机预览可直接访问；原型、测试、截图与结果均不提交。正式源码292文件未变，G40/G26/G27及真实Provider能力缺口继续开放。WB04B1当时交接WB04B2既有流程Agent步骤模型覆盖/还原默认；当前指针见后续记录，其他全局能力、流程目录与WB05仍待后续。

### 网站主线复测与待优化观察（2026-11-07）

应用户要求保持本机独立网站 `http://127.0.0.1:8933/` 可访问。对当时已验收的WB04B1原型，以1440/1024/768/390宽度分别实际点击创建、运行、日志、模拟完成、报告声明/写入/核验、历史、设置、配置中心及刷新，四条主线通过，无页面横溢或浏览器错误，仅9个本站静态资源。40张截图、脚本与报告在本地`dev_work/artifacts/site-review-20261107/`、`dev_work/reports/site-review-20261107.md`，没有为了测试注入会话数据；不等于重验所有异常和键盘矩阵，更不证明真实任务可执行。

截图确认日志不再嵌套实例配置，运行/历史/设置职责已分开。也记录WB05体验输入：创建成功提示在4.5秒计时内跨页仍占整行（并非永久残留）；自动名称与目标相同时连续重复；手机设置说明较密、日志正文上方内部标识偏突出。后续精简提示、重复文字与默认技术信息，同时保留有效模型/版本/来源、原始日志和故障恢复。当前不把这些观察混入步骤模型切片。

### WB04B2实际验收记录（2026-11-07）

对应R03/R06/R10，关联G40/G26/G27。本片只让当前两个演示流程的Agent步骤按需指定模型，不做全局Agent/工具、流程编辑、DAG或后端。本机入口不变；右上“演示场景”选“步骤专属模型”，进入项目设置即可体验。未打开覆盖时只读当前有效连接和“继承项目默认”，没有第二个下拉框。

```text
项目默认模型 → 步骤显示有效值和继承来源
步骤点“单独指定模型” → 独立选择 → 保存项目 → 后续新运行冻结有效值
步骤点“恢复项目默认” → 删除该步骤覆盖 → 立即重新检查项目默认
步骤连接需要维护 → 同一配置中心 → 返回原步骤 → 明确采用 → 保存项目
旧运行/报告始终读取提交快照，不随这些编辑改变
```

| 字段/信息 | 用途、输入、条件与默认 | 归属、联动、校验及保存影响 |
| --- | --- | --- |
| templateId + stepKey | 固定流程/步骤身份；cpu-report的experiment(Job)/report(Agent)、reading的analysis(Agent) | 不使用显示名称、数组位置或run随机stepId保存覆盖；steps名称由stepDefinitions派生，保留旧只读消费者形状 |
| 项目model/modelConnection | 沿用B1默认连接及公开版本快照 | 只有当前Agent继承时才是运行必需项；全部Agent明确覆盖时不为未使用默认拦运行。修改默认不会改已有覆盖 |
| stepModels[templateId][stepKey] | 唯一项目草稿/保存对象中的例外；旧项目默认无该键 | 显式启用时复制当前选择为草稿，不静默保存；恢复删除该键而非只隐藏选择器。切创建流程保留另一流程配置，不混入当前流程 |
| 覆盖model/modelConnection | 用户从同一目录选择连接；启用覆盖后必需 | 空/未知/停用/缺模拟凭据/版本待确认均不可用于新run；复用C.select/C.diagnose，不失败后偷偷回退默认 |
| 当前有效值与来源 | F.effectiveModel从当前模板/步骤解析；source=project或step | 默认显示名称、模型、版本与来源；独立选择只有明确启用才出现，仍显示恢复目标。只读投影，不另存有效模型状态 |
| 更新步骤版本 | 目录已变时显示显式采用按钮 | 只更新步骤草稿快照，不更新项目默认或其他流程；保存项目才用于未来运行 |
| 目录返回 | 草稿上下文保存原设置/创建位置和步骤选择框focusId | 维护仍走唯一目录，返回原项目/run来源与正确步骤焦点；保存连接不保存项目，也不自动采用 |
| run.plan.stepKey/modelSelection/input.modelSource | 新run在完整计划阶段克隆有效选择和来源 | 早于虚构Job提交；执行详情按冻结数据读，不实时读目录。旧run缺这些字段不补写，仍按既有可解释内容展示 |
| 连接占用 | 项目默认、全部保留步骤覆盖、停放草稿与历史有效选择反查 | 不适用流程覆盖不参与当前启动门禁，但仍是保留引用不能删除；历史plan.modelSelection单独存在也保护，不另存计数 |

项目设置和创建第三步复用同一步骤编辑区，配置内容仍只在项目草稿中；设置中流程只读，本片没有新增任意节点编辑器。Job步骤只读表明“不使用模型”，避免给不存在的模型配置项。运行详情只显示本步输入和“连接来源”，不再嵌套可编辑配置。配置保存没有启动副作用；运行模拟动作仍由原唯一run_adapter推进。

| 实际点击/检查 | 结果与限制 |
| --- | --- |
| 默认、覆盖、还原 | 旧项目无覆盖继承，不预铺选择器；显式启用、选择空值、刷新、取消确认/放弃均不误存。还原删除覆盖，保存后的新run使用项目默认及对应来源 |
| 历史与新运行 | 覆盖模型出现在Agent步骤输入及来源；完成并生成模拟报告后，还原/保存/新运行不改旧run/report整对象；新run捕获新有效选择 |
| 缺项与版本 | 四种步骤场景分别核缺模拟凭据/停用/旧版/未知引用，启动禁用且“去配置”聚焦对应步骤；不改默认、不回退。显式采用只改草稿，保存后新run才用新版本 |
| 目录往返 | 从步骤维护连接、改模型、保存并返回原设置，焦点落步骤而非默认；草稿仍旧版本，采用/保存后才生效。四宽度实际验目录刷新后返回 |
| 未用默认 | 清空项目默认但保留有效步骤覆盖仍可启动；还原后马上出现默认缺项，活动run保持提交时覆盖 |
| 跨流程/项目 | 创建中在两流程间切换、分别选模型、刷新并保存资料分析项目；只用analysis覆盖，另一个流程覆盖仍保留；返回另一个项目不串选择。草稿/失活覆盖占用有UI展示及独立契约保护 |
| 浏览器历史 | 拒绝离开保留未保存还原；接受返回丢弃，前进读已保存覆盖。沿用B1两实体草稿及精确来源返回 |
| 1440/1024/768/390 | 默认继承、长名称覆盖、旧版本错误、目录刷新返回/焦点、模型选择后Tab和新run步骤输入实际点击并截图；页面无横溢，长名正文完整换行 |
| 验证汇总 | 本片浏览器19组、独立契约15组；目录30/创建29/运行20/报告26/设置24回归，既有目录12/运行10/报告10契约及7JS语法/装配/CSP通过。无pageerror/console错误，仅9个本站静态资源；无真实模型/任务请求 |

首轮浏览器检查器把“长连接名称”目录专用场景误当已有项目，等待不存在的“继续项目”入口超时；这是测试准备错误。改为从已有项目通过网页编辑长名称，再返回明确采用后检查四宽度，第二轮通过；原fixture未为检查器增加项目，失败日志保留。没有向sessionStorage注入覆盖、补终态、增加等待掩盖门禁或用测试辅助冒充恢复能力。

消融决定：移除手写的重复steps名称数组，统一由固定stepDefinitions派生，旧steps消费者兼容保留。有效模型只有F.effectiveModel，目录诊断/引用只有B1内核；不再新增Provider协议、版本库、推进器或通用表单框架。项目默认与步骤覆盖语义不同，保留独立控件但覆盖按需出现。生产旧入口仍有真实消费者，正式接线前不删；292正式源码未变化。长提示密度仍列WB05，不因本片功能通过称视觉全部完成。

| 用户看到的内容 | 模拟字段/规则 | 现有API/源码 | 正式接线缺口与边界 |
| --- | --- | --- | --- |
| 默认与单步骤模型来源 | stepModels及F.effectiveModel | workspace.model.routing_mode/provider_profile_id、workspace.agents[].provider_profile_id；workspace/automation/topology.py::workspace_model_route_for_agent | 现路由按Agent，不是按步骤；同Agent绑定多步骤不能直接写全局定义。须确认项目快照/步骤作用域与迁移，避免多套模型优先级 |
| 显式失效覆盖阻启动 | C.diagnose对实际消费选择诊断 | state/workspaces/workflow.py的readiness逐Agent检查、现Profile health | 现agent_override且Agent Profile为空会回退项目默认，与本片显式空覆盖门禁不同；正式接线单片解决，原型不改真实后端 |
| 新运行冻结有效选择 | plan.modelSelection及input.modelSource | 执行包provider_route_hash、Agent调用前expected_route_hash | 优先复用现hash检测路由变化，不能照搬模拟revision；有效来源/步骤绑定/目录采用仍需持久契约验证 |
| 历史/草稿/失活覆盖引用 | C.usage遍历保留选择 | 现Provider删除及workspace/run存储 | 服务端占用检查仍待实现，前端禁删不证明真实保护；未知历史保持原样，不反填当时未记录来源 |

证据仅本地`dev_work/artifacts/wb04b2/`，脚本`dev_work/smokes/wb04b2_browser.py`和`wb04b2_contract.cjs`。公开提交只包含本次二三文档和设计附件；原型、测试、截图、密钥及本机配置不推送。WB04与G40/G26/G27仍未整体完成。

WB04B2当时交接WB04C1：Agent基本目录与当前既有步骤绑定，只做名称、用途、指令、启用及明确采用/快照；研究目标仍归项目，模型仍用B2唯一来源。不同时实现工具授权、工具目录、预算/输出编辑、流程编排或对话。具体验收与排除范围以[第三部分](next-stage-plan.md)顶部为准。

### WB04C1实际验收记录（2026-11-08）

对应R03/R06/R10，关联G40/G26/G27。入口 `http://127.0.0.1:8933/#/agents`。配置中心分别进入模型连接和Agent目录；本片只编辑执行者基本定义并绑定现有步骤，不实现工具授权、Agent调试/聊天、任意流程或真实调用。名称和指令必填，用途可选，项目研究目标仍只属于项目；模型继续由B2解析，没有在Agent另造Provider配置。

```text
配置中心 → Agent列表 → 新建/编辑基本定义 → 保存/取消
项目步骤 → 选择执行者及其公开快照 → 保存项目 → 后续显式新运行
步骤管理Agent → 同一目录 → 返回原步骤焦点 → 明确采用新版 → 保存项目
运行步骤 → 执行者名称/版本/来源 → 按需阅读本次完整指令快照
```

| 字段/信息 | 输入、用途、条件与默认 | 归属、联动、校验及保存影响 |
| --- | --- | --- |
| agents[].id/revision | 定义稳定身份与模拟版本；新建生成ID、第1版 | 只读身份，不以改名更换ID；内容变更递增当前目录版本，无改动保存不升版。不是生产已有完整版本库的证明 |
| name | 用户名称，必填 | 空白就近报错并聚焦；长名保留全文，不强迫与role同名 |
| description | 用途，可选，默认空 | 与独立指令/项目目标不同，不合并；目录和步骤用途超过120字符用摘录和“查看完整用途”单层展开，编辑与存储全文保留 |
| prompt | 独立分析指令，必填 | 单独正文编辑区；80条长指令完整保存、刷新和快照阅读。不生成Agent.goal，不把固定模拟结果称为执行了这份指令 |
| enabled/role | 新建启用；role保留旧定义 | 停用不删旧运行；原role只读显示，不新增角色管理。工具/预算/输出/Provider字段不在本片原型里；真实迁移必须保留这些已有字段 |
| stepAgents[templateId][stepKey] | 现有固定Agent步骤绑定；agentId、agentSnapshot、source | 创建携带两个已知流程的固定预设及独立快照，source=template；显式选择/采用为project。切流程保留另一流程配置；模型选择和项目目标均不改变 |
| 执行者诊断 | 实际当前步骤绑定及目录定义 | 空/未知/停用/未记录版本/旧版明确不可用于新run，不拿首个目录项替代；缺项可保存，启动仍拦截 |
| 明确采用 | 用户采用目录当前版本 | 只改项目草稿，目录保存不等于项目保存；项目保存后才用于未来run，不批量刷新其他项目 |
| 目录草稿 | 复用connectionDraft作为单一目录编辑事务 | 模型保持原owner；Agent用agent:前缀及entity区分，旧无entity连接草稿保持原语义。两种目录共享离开确认、保存/回滚与冲突恢复，没有第三套草稿推进逻辑 |
| 目录返回 | 共享connectionContext的owner/returnTo/focusId | 从步骤维护保留精确项目/run来源，返回step-agent而非模型框。目录类型互切也保留停放项目，放弃目录编辑不误丢项目草稿 |
| executorSelection | 新run完整计划中冻结执行者ID、公开定义/指令、来源 | Agent步骤输入显示名称/版本/来源；完整定义按需展开，只读本次快照，不查实时目录。旧run缺字段不补造来源 |
| 使用关系与删除 | 全部保留项目/草稿流程绑定、run快照及plan有效执行者反查 | 有任一引用不能删除，包括失活流程；历史plan独立引用也保护。无引用才确认删除，不另存使用次数状态 |

旧本地会话仅在整个stepAgents属性缺失且templateId为已知两个流程时，补固定演示预设；显式空对象、缺当前绑定、未知Agent ID保持缺项，不拿目录最新内容作历史事实。兼容绑定保留两个流程，因此失活配置也占引用；历史run/report始终不迁改。本片没有删除生产Agent编辑入口，正式消费者仍在，不能因原型通过拆掉真实能力。

| 实际点击/检查 | 结果和范围 |
| --- | --- |
| 空目录/基本编辑 | 单一新建动作；空名称/指令报错及焦点，用途留空可存，无改动不升版；未引用定义删除需确认 |
| 绑定、保存与取消 | 预设来源清楚；选另一Agent、刷新只保留草稿，不改项目；取消可拒绝或放弃。保存仅改本项目/步骤，不改默认模型或其他流程 |
| 新运行与历史 | 新plan冻结指令/执行者/来源；步骤可展开提交时定义。完成模拟报告后改目录指令、返回采用/保存并启动新run，旧run/report整对象保持原样 |
| 缺项/版本 | 目录停用、旧版、未知引用、空目录阻新启动；定位唯一步骤选择框。显式清空可保存但仍阻启动，不自动补预设；重新选择才恢复 |
| 目录往返 | 步骤管理→编辑/保存→返回原精确设置来源和步骤焦点；旧快照仍待明确采用。引用中禁止删除，取消目录修改保留项目草稿 |
| 保存故障 | “Agent写入故障”固定首个保存失败，原目录不变且输入保留；明确再次保存才提交第2版。没有测试注入存储或绕过校验 |
| 单目录草稿隔离 | Agent/new和连接/new互访，拒绝离开保留原实体，接受才放弃；刷新和query/hash不串内容。整页重载到另一Agent编辑显示冲突，明确恢复才回原草稿 |
| 两流程/两项目 | 创建中切换CPU/资料分析，分别绑定并刷新保存，只用当前流程执行者；回原项目不串绑定。浏览器拒绝后退保留草稿，接受后退丢弃，前进读已保存定义 |
| 四宽度1440/1024/768/390 | 长名称/80条指令、用途完整展开、空目录/错误/Tab/刷新/返回焦点、提交时定义阅读实际点击并截图；无页面横溢。指令编辑区允许自身滚动，其他正文顺主内容区阅读 |
| 验证 | 浏览器23组、独立契约16组；B1目录30/B2步骤模型19/创建29/运行20/报告26/设置24回归，既有15/12/10/10契约、8JS语法/装配/CSP通过。只请求本站静态文件（含明确的整页重载地址），无pageerror/console错误或真实API/工具请求 |

过程记录：首轮本片检查器精确summary漏“提交时快照”后缀，按页面真实完整标签修正，未删快照提示。B1回归发现共享目录恢复按钮无必要改名，保留原连接文案，Agent使用对应文案后重跑通过。旧B2“步骤区无任何select”已不适用于新增执行者，精确限定“无独立模型select”保留原约束；旧创建故障场景模糊匹配撞到新增Agent故障说明，检查器按标签开头匹配而非删场景/改产品掩盖。失败日志均保留。最终无会话写入注入、手填终态或额外等待来达成通过。

消融：只有一个Agent目录内核、一个binding解析、单一目录草稿事务与已有run解释器。用途的两个现有消费者共用只读purpose投影并删除原全文铺陈；不凭相似CRUD引入通用目录框架。定义目录不重复配置模型、目标和权限，不显示实时运行卡；运行完整指令只读取冻结定义，按需展开。全局Agent指令保存不代表真实模型已采用或执行，仍保持演示标识。

| 用户看到的内容 | 模拟字段 | 现有API/源码 | 正式接线缺口 |
| --- | --- | --- | --- |
| Agent目录/基本编辑 | agents公开定义及revision | GET/POST /api/agent-definitions、GET/PUT/POST/DELETE /api/agent-definitions/{id}；state/registry.py | 复用现CRUD，版本与显式采用持久契约未验；现真实定义含tools/预算/Provider等字段，基本编辑不能按模拟白名单全量覆盖丢失它们 |
| 用途与独立指令 | description/prompt，项目goal独立 | schema/agents_tools.py的全局/项目normalize | 项目description为原身份只读元数据；全局空用途当前会回填旧值，清空语义需接线核对；不能把模型结果当作验证指令生效 |
| 既有步骤绑定 | stepAgents、公开快照与source | node.handler.agent_id、workspace.agents[]；workflow readiness按绑定Agent检查 | Agent身份/项目快照与固定模板stepKey需映射；共享Agent/不同步骤不得静默改全局。模型继续复用B2的独立作用域方案 |
| 新run执行者/指令 | plan.executorSelection及input.executorSource | 接受阶段workspace快照、执行包及Agent调用输入 | 核对真实执行/恢复是否使用提交定义，来源与版本完整契约另片；不补写未知历史执行者 |
| 使用关系与禁删 | 全保留绑定与历史有效选择反查 | registry.delete_agent_definition删除后重写模板引用 | 目前未见本片完整项目/草稿/历史引用占用保护，需真实服务端门禁，前端禁用不算完成 |

证据仅本地`dev_work/artifacts/wb04c1/`；脚本`dev_work/smokes/wb04c1_browser.py`、`wb04c1_contract.cjs`和本地装配检查。原型/测试/截图不提交，生产292源码未变；稳定规格不降要求，WB04/G40/G26/G27仍未整体完成。

WB04C1当时交接WB04C2，随后WB04D1也已限定模拟验收，详见后续记录。当时交接WB04E，该片当时交接WB05A，当时选定WB05B1，当时下一片WB05B2现已限定验收，当前切片的范围和验收以[第三部分](next-stage-plan.md)顶部为准。

### WB04C2 · Agent工具授权与只读能力目录（2026-11-08，限定模拟验收）

本片对齐R03/R06/R10及G40/G26/G27，只实现本地设计原型。普通用户在Agent中决定“允许用哪些工具”；工具目录解释能力和使用关系，不提供另一处授权开关。不提交真实工具请求，也不把列表勾选当成能力可用证明。

```text
项目设置/创建的步骤 → 管理Agent → 编辑指令与工具授权
                                    ↓ 查看工具能力
                              工具目录 → 能力详情
                                    ↓ 返回原Agent授权
                 明确保存 → 回原项目 → 明确采用新版/保存 → 后续新run
```

| 字段/信息 | 输入与默认 | 归属、联动、校验和保存影响 |
| --- | --- | --- |
| tools允许列表 | Agent编辑勾选；新建默认[] | 唯一授权源，按集合去重排序；换序不升版。空就是无权限，不填推荐工具 |
| 旧缺tools | 只读按无工具解释 | 显示“旧定义未记录”；浏览不补写定义/历史，首次明确保存记录[]并升版 |
| 未知工具ID | 旧记录原样保留 | 单独显示能力/副作用未确认，明确移除才删除；新run阻塞，不猜同名或read替代 |
| 工具能力元数据 | registry既有25项只读快照 | ID/副作用/implemented/runtime/fallback逐项AST对齐。已有实现不等于当前可调用；内部控制标识在普通页面翻译为任务队列/任务控制/调度上下文 |
| 故障覆层 | 固定场景模拟暂停或缺适配 | 只改变演示诊断，不篡改真实registry的implemented=True；页面明确演示故障，所选失效项仍可取消 |
| 使用关系 | 定义、Agent草稿、项目/项目草稿全部流程快照、历史snapshot及plan反查 | 只读纯投影；历史每run一次，不另存使用计数，不在工具页反向改授权 |
| 新run授权 | executorSelection.agentSnapshot.tools | 深复制提交快照；目录保存后项目仍旧版，明确采用/保存才影响新run，历史不迁改 |

授权默认一个收起区，不把25个复选框常驻展示。列表→详情独立阅读，一个主滚动区；危险操作配文字，缺运行上下文时明确“阻塞”或“仅生成计划”。未知工具不虚构详情。Agent到工具的短途浏览复用同一目录草稿，独立返回上下文保留原项目/run来源，不另开一套编辑状态。

| 实际验证 | 结果及边界 |
| --- | --- |
| 授权编辑 | 选择后目录未变；刷新保草稿，显式保存升版；清空后无工具；无改动不升版；取消拒绝/接受、两个Agent不串授权 |
| 只读目录 | 25项能力，Agent草稿引用可见；工具详情刷新返回原Agent和焦点。无保存/注册按钮，不执行工具 |
| 完整往返与历史 | 完成模拟run/报告→设置→Agent未保存授权→危险工具详情→Agent→保存→原设置→明确采用/保存→原run→新run；旧完整run/report整对象不变，新run快照才含新授权 |
| 故障与旧值 | 未知/模拟暂停/缺适配阻启动，无回退；未知改名称保存仍保留，明确移除才删。旧缺tools浏览不补权，首次保存明确[]并升版 |
| 导航保护 | 工具前进后退保同一草稿；query切另一Agent可拒绝或放弃；工具详情整页刷新保留原Agent授权，返回焦点正确 |
| 四宽度1440/1024/768/390 | 长Agent、展开25项、目录/危险能力详情、Space键选择、返回焦点实际点击截图，无横溢。展开列表较长但按需，暂不为此造分类系统 |
| 独立检查 | 15组浏览器、14组契约；9JS语法/装配/CSP、25项registry AST元数据精确核对通过。C1浏览器23/契约16，B1 30/12，B2 19/15，创建29、运行20/10、报告26/10、设置24回归通过 |

过程与消融：监督先发现工具引用只检查saved项目/plan，遗漏项目草稿与历史保留的失活流程，修补后独立构造引用契约验证无写入、同run去重；没有再造权限缓存。截图自审把registry与workspace_job_control等普通页面术语改白话，原始元数据未改。新tools.js使旧创建检查器精确静态白名单过期，首轮失败保留，补明确脚本地址后重跑；C1过时“tools应被丢弃”断言改为显式[]，保留Agent不能覆盖model/goal边界，新14契约独立保护授权。未以删断言、注入sessionStorage、手填终态或关闭门禁达成通过。正常路径由可见动作推进固定模拟场景，没有动画计时进展。

| 用户看到的内容 | 模拟字段 | 现有API/消费者 | 正式能力缺口与交接 |
| --- | --- | --- | --- |
| Agent允许工具 | agents[].tools及revision | Agent CRUD；workspace/schema/agents_tools.py、state/workspaces/agents.py | 显式空已有语义，但旧缺字段/known工具过滤的迁移需保真；不能把原型数组全量覆盖真实预算/Provider等字段 |
| 能力/副作用/条件 | WorkbenchTools.definitions | GET /api/tool-definitions及/{id}；tools/registry.py与dispatcher | 目录可复用，但注册元数据不等于当前主机/上下文实现。未知side_effect默认READ不能当安全判断 |
| 暂停/适配缺失 | toolAvailability覆层 | 真实工具定义/执行器诊断 | 仅本地模拟故障，真实状态来源、错误封装及权限门禁须独立验证，不能照搬fixture为事实 |
| 项目采用/运行快照 | stepAgents→executorSelection | 实例agents/节点handler、执行包与Agent工具允许集合 | 正式权限作用域、版本采用、恢复后仍用本次快照另验；Job→报告仍tools=[]，本片不放宽 |
| 工具使用关系 | 全保留快照只读反查 | 现目录CRUD及配置/历史记录 | 后端完整引用查询未验，不靠前端禁用当服务端安全；只读原型不增加工具编辑/删除职责 |

网页预览仍为http://127.0.0.1:8933/，Agent入口`#/agents`，只读工具入口`#/tools`。证据`dev_work/artifacts/wb04c2/`，检查器/报告均本地；生产292源码不改。真实Provider/工具副作用、权限/取消/预算、任意DAG及流程编辑未验收，不把WB04/G40整体关闭。

独立网站测评另实测45项（`dev_work/reports/preview-review-20261108.md`）：项目→运行→日志→报告及四宽度可读。设置页仍长、来源/版本/管理入口多行、日志返回总览经所属步骤需两次点击，登记WB05按任务评估；不在授权片顺手整站改版。工具引用漏报已由本片修补，不继续保留为未修复。该片当时交接WB04D1只读流程目录与创建选择往返；最小流程编辑之后独立设计，不为工具目录补无真实适配器的空CRUD。

### WB04D1 · 只读流程目录与创建选择往返（2026-11-08，限定模拟验收）

要解决的是“先知道这个流程会做什么、要准备什么，再决定用不用”。只展示两种既有固定演示流程，不借目录引入新执行能力。配置中心增加“流程”，创建第二步在单选项之外提供查看按钮，避免点详情时意外切换流程。

```text
配置中心 → 流程列表 → 详情（步骤 / 需要准备 / 预期输出 / 范围）
                         ↓ 明确使用
                  空目标：创建第1步；已有目标：第2步
创建第2步 → 查看流程 → 返回原创建选项与焦点（不改变选择）
```

| 信息/字段 | 来源与默认 | 输入输出、联动及保存影响 |
| --- | --- | --- |
| 流程身份/名称/说明/范围 | F.templates现有两条 | 目录和创建同源；steps从stepDefinitions派生，run继续用同定义。目录只读，不建平行JSON |
| 步骤与必要条件 | stepDefinitions、needsHost/needsModel及同对象inputs | CPU流程需目标、Agent/模型、主机与目录；资料分析不要求主机。输入说明解释既有需求，不造第二诊断器 |
| 预期输出/边界 | 同对象outputs/boundary | 只描述设计预期；实际报告正文/核验依旧独立，资料分析不冒充执行实验、GPU预留或远程核验 |
| 明确选择 | templateId，默认未选 | 创建radio与目录采用共享chooseFlow；只改选择/来源，不清公共资料和两个流程的stepModels/stepAgents分支。radio可逆不再二次确认；详情换已有选项先确认，拒绝整草稿不变 |
| 浏览往返 | flowContext+草稿临时flowBrowseId | 仅认可创建owner、匹配临时身份、精确第2步返回地址与已知焦点；不覆盖模型/Agent返回上下文。仅浏览不makeDraft/创建项目/启动run；临时ID在保存白名单之外 |
| 首次创建 | 明确使用流程时才建草稿 | 空目标先第1步、已选流程保留；已有目标回第2步。正式保存后仍需用户独立启动，不自动运行 |

| 实际浏览器/检查 | 结果及边界 |
| --- | --- |
| 纯目录与首次创建 | 空项目列表从配置中心看两流程/详情不创建草稿、项目或run；明确使用才进入创建。选择资料分析、填写目标/模型、保存无需主机，也不自动启动 |
| 创建往返 | 目标/仓库/论文/数据/主机/目录/两个流程独立Agent绑定和模型覆盖保持；详情刷新/返回恢复精确按钮焦点。换流程拒绝无写入，接受仍保分支，换回CPU恢复其专属值 |
| 路由与归属 | back/forward、整页详情刷新、未知流程恢复实际点击；未知无采用按钮/默认首项。项目设置与Agent脏稿跨入目录可拒绝或放弃，采用不改原项目/串草稿 |
| 四宽度1440/1024/768/390 | 目录、详情、创建长目标及Enter打开/返回焦点实测截图；无横向溢出。流程定义本身固定短名，不把长目标检查说成长流程名动态编辑验收 |
| 正常保存/运行 | 浏览临时标识不进保存项目及run快照；普通配置齐全后启动仍产生既有CPU两步骤计划，不绕门禁或增加推进器 |
| 验证范围 | 16组浏览器/8独立契约，10JS语法/装配/CSP；创建29、运行20、报告26、设置24、模型目录30、步骤覆盖19、Agent23、工具15浏览器回归及10/10/12/15/16/14已有契约通过。仅本机精确静态请求，无pageerror/console错误/API调用 |

过程审查发现首次目录采用空目标直进第2步，测试需手动回第1步才可填写，这是产品路径不合理，已改为保留流程并正常首入第1步。创建radio本身明确且可逆，重复confirm没有保护额外数据，已退出；详情切换确认保留。早期检查器把初次尚未持久的session当dict、未知页面标题错写“未找到”，分别修检查器，不改产品迎合文字。最后保存验证误用long场景（同时设主机不可用），被真实演示门禁正确拦住；切换正常场景并实际输入长目标后重跑成功，未将hostReady注入true/绕过门禁。首轮日志全部保留。

消融：仅新增只读flows投影和同源语义元数据；没有流程CRUD、第二份状态或新执行器。选择逻辑已有两个消费者，抽为chooseFlow并接入radio/目录，删除旧独立radio写法。flowContext是短途访问归属，不另存业务状态；保存只白名单接收业务字段。正式旧页面仍有真实消费者，全部保留待接线，不在本地原型验收后删除生产能力。

| 用户内容 | 模拟字段 | 现有API/组件 | 正式接线与缺口 |
| --- | --- | --- | --- |
| 流程列表/详情 | templates名称/说明、stepDefinitions、inputs/outputs/boundary | GET /api/workflow-templates、GET /api/workflow-templates/{id}、preview；state/monitoring.py公开投影 | 复用真实模板nodes/links与依赖，不能把演示两条当全部支持的执行图；人类可读条件要对齐真实门禁 |
| 创建明确选择 | draft.templateId与各流程分支 | 模板建立workspace与build_template_snapshot | 正式模板含source/env/recipes/model/nodes/links/agents/tools，按字段语义映射，不只写id后实时查全局 |
| 顺序步骤与运行 | 同一stepDefinitions派生完整计划 | 执行包/协调器现有计划与run快照 | 只读介绍不证明任意模板可执行；未知能力保持阻塞，不让前端图替后端判可运行 |
| 修改影响 | 本片无目录写入口 | 已有模板版本记录、snapshot diff和迁移预览 | 下一片基本编辑必须补项目显式采用/快照边界；现原型按templateId动态读取全局，在只读固定场景下成立，开启编辑后不能沿用此假设。复用生产已有版本机制，不再造历史平台 |

预览`http://127.0.0.1:8933/#/flows`；本地证据`dev_work/artifacts/wb04d1/`及smokes/wb04d1_browser.py、wb04d1_contract.cjs。原型/测试/截图/本机配置不提交，生产292源码未变。WB04/G40仍未整体完成。该片当时交接WB04D2固定流程基本编辑与项目引用保真；现已限定模拟验收，步骤拓扑/预算/授权不扩。

### WB04D2 · 固定流程基本编辑与引用保真（2026-11-08，限定模拟验收）

用户可整理两种固定流程的名称、说明和启用状态。目录更新不能顺手改掉项目正在使用的定义；用户回项目明确采用新版并保存后，才影响下一次运行。已有运行及报告仍使用提交时记录。

```text
流程详情 → 基本资料编辑 → 保存目录（项目仍使用原版）
项目设置 → 查看流程目录 → 编辑/返回 → 明确采用新版 → 保存项目 → 新run
已有run / 报告：全程不改写；全局停用仅阻止新选择和新启动
```

| 信息/字段 | 来源与输入 | 处理、校验、归属及保存影响 |
| --- | --- | --- |
| 活动流程目录 | state.flows固定两ID：id/revision/name/description/enabled | 名称必填，说明可清空，启用为bool；仅这些metadata可写，未知ID不创建，拓扑/步骤/条件不可改。相同内容不升版 |
| 固定执行语义 | F.templates的stepDefinitions/needsHost/needsModel/inputs/outputs/boundary | 仅固定演示定义和初始seed，不是第二活动目录；没有任意DAG/节点编辑。未来开放步骤修改前须扩项目快照契约 |
| 项目采用 | flowSelection={flowId,flowSnapshot,source} | 快照含5项公开metadata；项目templateId、flowSelection.flowId及flowSnapshot.id须一致。创建或设置明确选择并记录来源；目录改动不回填项目。saved项目不能借采用接口换流程ID |
| 旧缺版本 | 已知固定ID只用初始语义排版，来源显示未记录 | 不推断已采用当前目录；阻新启动，明确采用/保存才记录。ensure只补整个目录缺失，不改项目/run；显式空目录不重建，未知不落首项 |
| 停用/旧版 | 当前目录准入与已采用快照分别检查 | 全局停用即使项目快照曾启用也阻新选择/启动；旧版提示采用。不会停止已运行任务、重写历史或把请求当实际停止 |
| 新run计划 | FV.projectTemplate(project)叠加固定执行语义 | 先诊断，再由已采用项目定义冻结snapshot.template；忽略调用者传入的实时名称/步骤，不出现“界面旧版、执行新版” |
| 流程编辑草稿 | 单一connectionDraft，entity=flow、owner=flow:id | 与模型/Agent复用事务，query/hash/整页编辑冲突不串草稿；项目来源connectionContext与创建短途flowContext各自保归属，不新增第三套编辑存储 |

消费者已逐项核对：创建列表/目录读取活动metadata；app的template解析、stepFields、issueList、设置、项目、start都读取项目已采用定义；agents.ensure仅按不可变已知ID做原兼容；run_adapter启动自己重新解析采用定义，运行展示只读提交快照。没有保留无消费者的省略state读源来迁就旧检查器。

| 实际验证 | 结果及边界 |
| --- | --- |
| 编辑与取消 | 空名称就地校验和焦点，说明可清空，无改动不升版；两流程不串值。刷新保留草稿，取消可拒绝/放弃，均不误保存 |
| 完整往返与历史 | 完成run/报告→设置→目录编辑→返回精确设置/焦点→采用/保存→原run→新run；旧完整run/report整对象不变，新run名称/版本来自新采用定义，计划仍固定两步 |
| 版本与故障 | 已停用、旧版、未记录及未知阻新启动，不回退；明确恢复启用/采用/保存才修复。固定首写失败保留原目录和输入，再次保存才提交，非后台自动重试 |
| 草稿与路由 | 流程和Agent dirty互访query保护；整页进入不同编辑实体保留原草稿并明确恢复；真实点击编辑后back拒绝保留、接受放弃，forward读已保存值 |
| 四宽度1440/1024/768/390 | 长流程名称/说明、编辑、错误、版本采用、Tab、刷新实际点击截图，无横溢；长说明编辑允许textarea自身滚动，目录摘录可单层看全文 |
| 独立契约与回归 | 17组浏览器/16契约、10JS语法/装配/CSP通过。创建29/运行20/报告26/设置24/模型30/覆盖19/Agent23/工具15/流程往返16浏览器及10/10/12/15/16/14/8既有契约通过。只请求精确本站静态文件，无API/Provider/pageerror/console错误 |

过程审查：最初后退检查用绝对URL直达edit，在带query的文档中变成跨文档导航，不能期待同页popstate离开框。保留失败截图/状态后，改真实点击目录→详情→编辑，再实际按后退/前进；不是延长等待或改产品掩盖。整页进入其他编辑实体已验证冲突保护；整页到只读列表会保草稿但不弹同页确认，未把它写成beforeunload全站保护通过，WB05继续评估。D1契约旧有“省略state固定目录”和“直接修改已保存项目templateId”不再符合职责，改显式活动目录/固定语义检查及合法创建fixture；保留原独立未知/转义/只读不变/同计划覆盖，本16契约另保护新采用门禁。静态检查旧字串路径改为同职责新来源引用，不靠删检查通过。

截图自审：基本编辑只有名称、说明、启用和保存/取消，没有把步骤参数、状态日志或能力选择塞入表单。设置页流程版本说明与底部缺项摘要存在重复且纵向偏长，保留既有定位功能，交WB05统一精简；不在本片扩大整站重排。

| 用户看到的内容 | 模拟字段 | 现有API/源码 | 正式能力差异与交接 |
| --- | --- | --- | --- |
| 名称/说明编辑 | flows.metadata及模拟revision | GET/PUT /api/workflow-templates/{id}，state/registry.py的update与version_record | 复用已有模板更新；normalizer.description用payload or current or brief，明确清空语义需独立修复，不能覆盖丢失其他template字段 |
| 启用/停用 | flows[].enabled | schema/templates.py现status为整理状态 | 目前未证真实enabled持久准入门禁；status不是enabled，不可改标签冒充。正式接线需独立字段/服务端验证和消费者契约 |
| 项目明确采用 | flowSelection.flowSnapshot/source | build_template_snapshot、已有模板version_history和迁移预览 | 原型revision只作演示；接线优先使用真实版本标识/摘要，不另建完整历史平台。语义/拓扑改变要走真实迁移影响确认 |
| 提交计划与回看 | run.snapshot.template/project | 现执行包/Run完整计划与持久快照 | 必须核对恢复/新启动的实际定义来源；原型通过不等真实任意模板执行通过 |

证据`dev_work/artifacts/wb04d2/`、本地browser/contract及开片报告；预览`http://127.0.0.1:8933/#/flows`。生产292源码/正式页面不改，本机配置、原型、测试、截图不提交。WB04/G40/G26/G27仍未整体完成。该片当时交接WB04E，现已限定模拟验收，见下一节；当时交接WB05A先总核证据，现见下文验收；不继续为配置齐全堆高级CRUD。

### WB04E · 按需Agent辅助对话（2026-11-08，限定模拟验收）

需求R03/R09/R10/R12、问题G40/G26/G27。项目/运行只保留一个明确的次级对话入口，相关Agent步骤可直接打开；驾驶舱没有常驻聊天列。独立页面只回答“与谁讨论、依据哪次输入、消息怎样了、如何返回”，不放模型/授权编辑、Agent debug、预算或运行控制。

```text
返回项目 / 原运行 / 原步骤
Agent辅助对话                         所属项目
对话对象与步骤（明确选择，不默认全局第一项）
    版本和来源；按需看目标与有效模型
你 / 模拟回复                          发送时来源
    完整消息正文
原请求来源 / 等待或失败                显式演示动作
消息输入                              发送（模拟）
```

| 字段/组件 | 输入与来源 | 处理、输出及保存影响 |
| --- | --- | --- |
| context(projectId,from,scope,focusId) | 页面真实入口；from仅同项目存在的project/run/Agent-step | 由实体校验归属并派生焦点，非法来源拒绝，不换最新run；query可保from=history |
| target(key,agentId,agentSnapshot,modelSelection,step) | 当前项目只用当前流程实际绑定；历史只用本次plan快照 | 未指定时明确选择；步骤入口可明确带该步目标；旧缺不补当前/首项。模型来源按项目默认/步骤覆盖/未记录分别表达 |
| chats(projectId,agentId,draft,messages,pending) | 用户输入及显式按钮；每项目/Agent独立 | 未发送草稿与配置事务分开，刷新保留；不保存进项目配置，不串项目/Agent。固定流程各一个Agent步骤，不宣称任意多Agent拓扑UI已提供 |
| request(id,text,status,attempt,snapshot) | 显式发送，非空且当前目标未变、目录准入可用 | 冻结project/Agent/step/model/origin/runNumber。只添加一条user；pending禁止再发。失败/重试保留原输入及快照，重试只加attempt，不再添加user |
| complete/retry | 用户点生成模拟回复/失败/重试，精确requestId | 用原请求快照，不跟当前浏览目标；当前目录Agent/模型停用/删除/缺模拟凭据仍拦截。旧revision可明确展示，不采用新版污染历史 |
| sourceLabel | request发送时快照，消息与pending共享只读投影 | 显示“发送时项目配置”或“第N次运行·步骤”；编号/来源缺失写未记录。不另存一份状态，避免同Agent跨run共享会话误认当前上下文 |
| 保存/返回 | 本地sessionStorage由原app事务持久化/回滚；同源hash路由 | 返回原run/step与入口焦点；缺当前模型去唯一项目设置，显式保存回原chat并保草稿。历史缺定义/模型不以改当前设置冒修历史 |

加载/空/异常：本片静态fixture无真实连接加载过程，不宣称API加载/断线已验。未选对象时输入禁用且引导明确选择；缺绑定给唯一项目设置入口，历史缺项给返回当前项目。未启用/删除/缺模型明确阻发。空消息就地校验并聚焦；等待和失败保留原文，成功只清除仍与原发送相同的草稿，不清除等待时另写的下一条。正文与长错误完整换行，一个主滚动区，无自动回复、计时进度或隐藏的背景请求。

| 实际验收 | 结果与证据边界 |
| --- | --- |
| 正常对话 | 项目明确选择→空输入校验→发送→等待→刷新/后退前进不重发→失败→显式重试→回复；单user，新增草稿保留，配置/run/report整对象不变 |
| 选择及隔离 | 两项目同Agent、同项目明确改绑两Agent、未发送草稿与消息均隔离；失活流程Agent不出现在本次目标；停用/未知/目录为空有明确诊断和恢复入口 |
| 历史及来源 | 正常run_adapter建立完成报告后改变当前Agent/模型，原步骤仍用旧快照；旧缺定义/模型不可补当前。项目来源pending后从同Agent新run步骤完成，原请求不改源，消息/pending可读区分发送时项目配置/第1次运行 |
| 导航及配置 | 项目/run/Agent-step精确返回与入口焦点；缺模型设置保存返回并保输入；设置及Agent目录dirty进入chat可拒绝/放弃；跨项目伪from拒绝 |
| 四宽度1440/1024/768/390 | 长问题、48段完整模拟回复、长错误、Tab顺序和刷新有实际点击/截图，无横向溢出；不是全站键盘及真实断线验收 |
| 独立检查与回归 | 23组浏览器/26契约、11JS语法/装配/CSP；创建29/运行20/报告26/设置24/模型30/覆盖19/Agent23/工具15/流程16/流程编辑17浏览器及10/10/12/15/16/14/8/16既有契约通过，仅精确本站静态资源、无page/console错误 |

过程审查：首两浏览器失败分别误用data属性统一恢复链接、把目录为空但已保存绑定快照仍可辨识当成无绑定；修检查器按真实状态选择/核恢复链接，未删门禁或改fixture，原失败json/截图保留。首次契约误认为缺历史Agent的resolve应返回对象，实际已正确拒绝目标为null，按拒绝结果修断言。监督另发现真实设计问题：同Agent跨run共用会话但消息/pending没有原运行标签；已冻结runNumber并复用sourceLabel，新增实际跨来源pending完成检查，复验后才验收。原型场景里的历史完成报告由既有adapter正常演示动作生成，仍是fixture，不当作真实任务证据。

消融与截图自审：没有原型旧聊天路径可删；新增一个chat内核/只读视图，复用既有app保存回滚/导航、唯一项目设置，不另建配置草稿引擎或运行推进器；无场景/消费者的隐式首失败分支退出，固定失败统一走显式动作。生产旧常驻chat有真实消费者，正式接线前保留。网页呈现已分开配置/运行/辅助讨论，桌面消息不套多层卡片；390长错误全文虽可读但占较多高度，留WB05A评估短原因+按需完整详情，不能无声裁剪。旧来源缺值不猜来源。原型消息保存在标签页session，不承诺关闭标签页/服务重启恢复。

| 用户所见 | 模拟字段/行为 | 现有生产入口与真实差异 |
| --- | --- | --- |
| 与实际相关Agent讨论 | context/targets和项目/历史绑定快照 | workspace.agents/nodes/公开run快照可复用；renderWorkspaceUseChat当前列全部Agent并可回退首项，不能直接照接 |
| 发送与回复 | chat request/status/attempt、固定回复，无网络 | POST /api/workspaces/{id}/chat现支持stream/use_llm；ChatMixin会保存model.chat_agent_id，LLM可执行允许工具，辅助用途必须先限定无工具/配置副作用。debug单独用途，不合并 |
| 独立消息与草稿 | 每project+agent行；请求冻结来源 | 当前workspace.chat统一存储，同步chat[-10:]未先按Agent隔离；需要服务端历史上下文、幂等和恢复契约，不能只在页面过滤 |
| 等待/失败 | 显式按钮确定失败/完成，刷新不推进 | 现流式线程/消息事件基础可评估复用，但占位规则回复不能冒充真实Provider成功；真实中断/取消/重启未验，另片验证 |
| 不自动改目标/任务 | 仅chat状态写入 | context reflection另有显式accept写inputs.context_blocks，本片不调用；正式辅助模式不得隐式接受建议或开放副作用工具 |

证据仅本地`dev_work/artifacts/wb04e/`，独立browser/contract与生产静态核查在smokes/reports；预览仍为http://127.0.0.1:8933/，选择已有项目后点对话入口。原型、测试、截图及本机配置不提交；生产292源码与正式页面未改，不能据此关闭G40/G26/G27。该片当时交接WB05A，现已完成证据总核见下文；当时选定WB05B1精简项目设置，现已限定验收；当时下一片WB05B2现已限定验收，当前切片以第三部分顶部为准。

### WB05A · 整体需求、体验与接线证据总核（2026-11-08，仅审计/设计交接）

本片不改原型、生产代码或稳定规格；依据当前11脚本消费者、WB01字段矩阵、已有验收原记录及本次实际网站点击重新核对。结论是**基础模拟闭环已可走通，整体设计与体验阶段仍未完成**；目录齐全不等于字段全覆盖，更不等于真实后端可用。以下覆盖状态用于选择下一片，不降低第一部分要求，不删除原高级字段。

#### 用户要求与证据矩阵

**历史快照说明（WB05K1补注）**：以下“当前/未建/优先”指WB05A审计当时。B1/B2已处理设置和创建减负，C1日志、C2正文下载、D1/D2反馈、E/F/G引用与概览、H1限定历史查找、I1静态启动及J1主操作均已有后片证据；勿继续把它们记作全部未建。区域读取与正式接口差异尚存；唯一当前能力及剩余分类见§5，不逐行重写历史结果。

| 原要求/用户任务 | 页面与当前实际消费者 | 当前证据 | 缺口、决定与交接 |
| --- | --- | --- | --- |
| 明确项目入口/继续已有项目 | app.projectList/projectRows；projects+latest run投影 | WB02创建29组；本次四宽完整键盘主线从空列表开始 | 搜索名称/目标已建；更新时间仅演示保存时间，真实列表轻量投影未接。自动名与目标重复仍需精简，不删除两者独立保存语义 |
| 简短三步创建/条件字段 | app.wizard/validate/saveProject，固定cpu-report/reading | WB02回归与本次四宽键盘创建/保存/启动 | 第3步仍较密；不是未实现创建。多资料→主仓库/论文映射未定，数据位置不等于通用references；不得直接拼接合并 |
| 主机与目录/环境按流程出现 | settings/repair、host+path+environment | WB02/04A原缺主机/路径与返回证据；本次CPU正常键盘 | 模拟检查不是主机可写性/环境发现；旧env_manager/python/命令原值需接线保真。资料分析不出现主机项 |
| 配置与运行分开 | 独立settingsPage、run_views、history_views | 本次四宽设置/运行/日志/报告截图；历史快照原契约 | 默认设置页“运行环境”包揽模型/流程/步骤，分区仍不准确，WB05B1优先；不把实时状态放回设置 |
| 项目有效模型/步骤覆盖/版本 | F.effectiveModel、C/A/FV.diagnose、stepModels/stepAgents | B2/C/D原契约及浏览器覆盖；本次旧Agent诊断重复复现 | 保留唯一解析及显式采用，不新增状态；在设置精简重复文字，不能把未知/失效引用回退为默认 |
| 密钥唯一位置/本地配置 | 原型connections不收真实key；生产Provider仍有旧存储路径 | CSP/no真实API证据；配置目录规范已写第一部分 | 真密钥编辑/清除/迁config、主密钥兼容仍未交付；本片未读取私密配置。连接“模拟凭据已配置”不能当测试成功 |
| Agent/工具/流程目录职责 | agents唯一allowlist、tools只读、flows固定元数据 | WB04C/D限定模拟证据；静态反查消费者 | 工具注册/搜索连接/任意流程编辑未建，不为“完整目录”补空CRUD；未知高级字段保留且需后续专门编辑/诊断设计，不丢原要求 |
| 运行进度/等待/失败/停止 | R唯一模拟解释器，V只读，完整plan+child | WB03A原状态矩阵；本次390阻塞/失败抽样、四宽正常路径 | 停止后续不等于子任务停止；真实attempt恢复/受理失败/SSE重同步未验。不增加自动模拟进度 |
| 结果正文与交付分开 | H.reportPage/R.reportDelivery | WB03B证据；四宽键盘声明→写入→核验；390缺正文/核验不可用 | 正文阅读已建；原型文件下载/证据导出及下载错误未建，须在结果交付单片设计；真实文件验证另片，不改100%含义 |
| 历史检索/回看 | H.historyPage/reportUrl | WB03B多run/隔离/返回；本次四宽历史键盘 | 列表可读，搜索/状态/节点类型等筛选未建；保留设计目标，后续按实际最小检索而非无声删除 |
| 按需辅助聊天/精确返回 | CH.context/targets/消息冻结来源；app路由 | WB04E23浏览器/26契约；本次四宽键盘步骤聊天往返 | 真实chat工具副作用/写默认Agent/混上下文未解；390长错误把重试推远，后续单职责片优化，不混成运行控制 |
| 一主滚动/长内容/响应式 | style系统字体、独立日志/报告阅读 | 本次31图采集+四宽无overflow，旧长报告/日志原证据 | 不是全部页面所有状态的响应式认证。设置过长有实测；不能靠固定高度/多层折叠藏必要字段 |
| 键盘及焦点 | 原生控件、hash路由、返回视图记录 | 本次四宽156个键盘目标，主线全Tab/Space/ArrowDown/Enter；每目标focus-visible | fixture重置鼠标，其后产品主线纯键盘。未因此覆盖缺项修复、危险确认及每个目录编辑；屏幕阅读器/缩放未验，非首次真实用户研究 |
| 取消/前后退/刷新/跨项目 | 单配置草稿事务与CH独立消息草稿 | 原各片；本次整页跳目录保草稿但无确认复现 | 同页离开确认可用；整文档离开无全局beforeunload确认，但不误保存/丢草稿，须另片定策略，不能误报数据丢失 |
| 正常顶栏不放成功/30秒说明 | 原型topbar仅面包屑/演示标识 | HTML/网站图均无“状态读取完成/最多30秒”块 | 本地模拟没有状态采样时间和刷新，不能当真实状态读取交付；保存成功notice仍短时跨页，后续反馈片处理 |
| 区域加载/超时/断线/启动失败恢复 | WB05I1首次静态加载/资源或初始化失败；既有模拟写入/聊天失败 | I1有真实document重载证据，正常/故障分列；CSP禁止connect | 请求受理中/服务失联/读取超时尚未建；永久pending/HTML未到不在I1，静态恢复不能代表API/任务恢复，真实接线另片 |
| 监控/执行/活动必要导航 | 原型全局仅项目/配置；生产旧入口仍在web | index实际导航静态核对 | 深入改版仍排除，但必要入口/顶栏统一设计尚未在独立原型呈现，须补跨区导航设计，不能把整项省略 |
| 开源复用与技术栈约束 | 仅借鉴Kestra/Dify/Langfuse组织；已有frontend-design | 来源/许可见§8；无新增运行依赖/外部字体 | 不引完整平台，不重造推进器。正式接线复用现API/route_hash/模板版本/运行reader；不复制模拟revision/chat状态机 |

#### 本次网站审查与问题优先级

13组调查检查、31张截图采集、156个键盘目标；证据仅本地`dev_work/artifacts/wb05a/`，result包含视口、精确路由、页面尺寸和键盘停靠记录。31是采集数，未宣称逐图独立人工审查。主代理实看默认设置1440，结合WB04E长错误390和来源截图审查；监督核范围/证据，不把工具脚本知道路线等同陌生用户已无需指导。

| 优先/问题 | 本次事实 | 后续边界 |
| --- | --- | --- |
| P1 设置分区/阅读压力 | 默认设置页高1440=2604、1024=2580、768=2701、390=2723px（视口高1000）；“运行环境”内堆模型、位置/环境、流程版本、步骤/覆盖；agent-old同错误≥2处 | 当时选定WB05B1，现已限定验收：项目设置分区及唯一诊断；字段/来源/门禁不减少，不以像素限额强藏内容 |
| P2 短时跨页通知 | 保存项目后立即进目录，notice仍写项目已保存；约4.5秒后清，不是永久状态 | 后续局部反馈片，不在设置片同时重做全站toast |
| P2 全文长错误 | 390聊天错误全文可读，重试在长错误之后 | 短原因+可达全文/恢复动作另片；不无声截断、不把正文藏多层 |
| P2 创建/日志重复信息 | 创建第3步复用目录式版本/用途/摘要；日志展示内部任务ID且回总览需经步骤 | 创建、日志各自独立职责片；不把这些全部塞入WB05B1 |
| P2 整页脏稿策略 | 整文档去只读目录不弹离开确认，草稿和已保存值分开且保留 | 明确同页/整页策略并验收另片，当前不能称全局离开保护 |
| 设计覆盖缺项 | 历史检索/下载导出/故障反馈/必要跨区导航未建；高级命令/映射/预算等无专门完整原型 | 保留原字段与要求。基础闭环不需要的复杂编辑可延期，但要在正式接线计划给出专属位置/保真契约/开放条件，不能从需求表消失 |

六组已核基础文本配色对比度均≥4.5:1（正文白底16.03、次要白底6.33、次要灰底5.90、蓝链接灰底5.68、蓝按钮白字6.10、页脚实际灰底5.90），未扫描全部交互态或做无障碍认证。首次静态把侧栏颜色误套页脚灰底得4.49，实际DOM核页脚为#526173后纠正，未登记为产品缺陷。

本次四宽完整键盘主线：空列表创建CPU项目→设置返回→启动→Job日志→所属步骤→运行/模拟Job完成→Agent步骤/聊天发送回复→运行/模拟Agent完成→报告声明/写入/核验→历史→设置→模型目录返回。异常另在390抽样blocked/failed/缺正文/未核验，不冒称这四种异常本轮也四宽全验。原片其他异常/宽度证据仍保持各自限定，不用本轮取样覆盖全部。

过程审查：检查器首次异常段没在重绘后重开演示动作，第二次把HTML布尔open属性空串当false而误关闭，保留两次失败log/json/截图，改检查器读DOM open布尔值后整条路径复跑；未修改原型、加等待或注入终态。原型没有真实网络，未运行无关Python业务测试或真实Job/Provider。只读现存各片结果与检查源，不能由总PASS数量推断未列场景通过。

#### WB01静态字段的当前原型覆盖（58项，原ID不改）

| 原控件ID | 当前原型实际消费者/字段 | 覆盖边界 | 处理决定及正式接线需要 |
| --- | --- | --- | --- |
| `workspaceTaskGoalInput` | app.js wizard(1)/settingsPage → draft.goal | 模拟覆盖；生产goal_text/brief映射未验 | 保留目标；正式接线不得把两个生产字段未经迁移合一 |
| `workspaceTaskRepoInput` | wizard(1)/settingsPage → draft.repo | 部分：多行URL；主仓库语义未建 | 保留数组与主项区别，正式适配需确认主项 |
| `workspaceTaskPaperInput` | wizard(1)/settingsPage → draft.paper | 部分：多行URL；主论文语义未建 | 保留数组与主项区别 |
| `workspaceTaskReferenceInput` | wizard(1)/settingsPage → draft.data | 部分：仅数据位置文本，不等价完整references | 不得将通用参考资料静默改写成路径；高级旧值保真需接线验收 |
| `workspaceTaskContextInput` | wizard(1)/settingsPage → draft.constraints | 部分：原型单文本，生产context_blocks数组未接 | 保留约束语义及逐行数据；不吞旧背景备注 |
| `workspaceTemplateSelect` | wizard(2) → draft.templateId/flowSelection；flows.js select | 模拟覆盖固定两流程 | 保留选择/快照；任意流程尚未支持 |
| `workspaceUseChatAgentSelect` | chat.js targets/resolve/page → thread Agent选择 | 模拟覆盖辅助对话入口；非生产默认Agent持久化 | 退出重复常驻编辑入口；历史绑定缺失不得猜测 |
| `workspaceUseChatInput` | chat.js page/send → per-project+Agent draft/messages | 模拟覆盖；无真实Provider/工具调用 | 仅按需对话；接线审查会话隔离和副作用 |
| `workspaceRunReaderProjectSelect` | app.js projectRows/projectPage；URL projectId | 模拟项目导航覆盖 | 保留唯一项目范围；不再增加运行内嵌项目选择 |
| `workspaceExecutionOverviewSearch` | history_views.js historyResults + app.js history-search | H1限定模拟：按当前项目次数/提交目标本地查找；不等价完整生产搜索 | 保留原字段语义；正式接线核API加载范围/截断/冻结字段，未接远端全量搜索；状态/类型筛选仍另片 |
| `workspaceExecutionOverviewStatusFilter` | history_views.js history列表，无这些筛选消费者 | 未建；原历史检索设计要求仍保留 | 后续历史检索单片决定最小搜索/筛选，不删除原字段；正式接线先核数据量和语义 |
| `workspaceExecutionOverviewKindFilter` | history_views.js history列表，无这些筛选消费者 | 未建；原历史检索设计要求仍保留 | 后续历史检索单片决定最小搜索/筛选，不删除原字段；正式接线先核数据量和语义 |
| `templateNameInput` | flows.js editor/save → flow.name | 模拟覆盖固定流程元数据 | 保留；历史/项目显式采用版本 |
| `templateSourceTypeSelect` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateStatusSelect` | flows.js enabled仅可用开关，无整理status编辑 | 语义不等价，未建status | 不能用enabled替换draft/ready等整理状态；高级保留 |
| `templateTagsInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateDescriptionInput` | flows.js editor/save → flow.description | 模拟覆盖；生产清空说明契约未验 | 保留原文、摘要与按需全文 |
| `templateBriefInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateRepoUrlInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateRepoRefInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templatePaperUrlInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateWorkspaceDirInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateIdeaInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateEnvNameInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateEnvManagerSelect` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templatePythonVersionInput` | flows.js fixed definitions无对应编辑/保存消费者 | 未建高级模板资料/默认值 | 按真实流程需求再开放；生产既有值须无损保留，不默认置空 |
| `templateChatAgentSelect` | 固定流程Agent预设；项目model/stepModels，非模板model对象 | 模板三字段未建；不能当项目覆盖已替代 | 保留模板默认与项目采用独立边界；正式路由契约另验 |
| `templateProviderProfileSelect` | 固定流程Agent预设；项目model/stepModels，非模板model对象 | 模板三字段未建；不能当项目覆盖已替代 | 保留模板默认与项目采用独立边界；正式路由契约另验 |
| `templateRoutingModeSelect` | 固定流程Agent预设；项目model/stepModels，非模板model对象 | 模板三字段未建；不能当项目覆盖已替代 | 保留模板默认与项目采用独立边界；正式路由契约另验 |
| `workflowTemplateNodeKindSelect` | fixtures.js固定stepDefinitions；无节点编辑器 | 未建自由节点/DAG编辑 | 保留现有节点原JSON；按执行能力逐片证明，不新增空壳CRUD |
| `workspaceIdInput` | URL/项目id；app.js saveProject系统生成 | 模拟隐藏身份覆盖 | 只读诊断保留；生产回执映射未接 |
| `workspaceNameInput` | wizard(3)/settingsPage → draft.name | 模拟覆盖生成+允许改 | 保留；创建默认呈摘要，可明确修改 |
| `workspaceSourceType` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspaceBrief` | app.js wizard(1)/settingsPage → draft.goal | 模拟覆盖；生产goal_text/brief映射未验 | 保留目标；正式接线不得把两个生产字段未经迁移合一 |
| `workspaceReferences` | wizard(1)/settingsPage → draft.data | 部分：仅数据位置文本，不等价完整references | 不得将通用参考资料静默改写成路径；高级旧值保真需接线验收 |
| `workspaceTags` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspaceStatus` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspaceRepoUrl` | wizard(1)/settingsPage → draft.repo | 部分：多行URL；主仓库语义未建 | 保留数组与主项区别，正式适配需确认主项 |
| `workspaceRepoRef` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspacePaperUrl` | wizard(1)/settingsPage → draft.paper | 部分：多行URL；主论文语义未建 | 保留数组与主项区别 |
| `workspaceDir` | wizard(3)/settingsPage/repair → host+draft.path | 模拟字段覆盖；真实主机权限/可写性未验 | 保留host语境；不能用本机同名目录替代 |
| `workspaceIdeaText` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspaceNotes` | app.js saveProject无对应新表单字段 | 未建高级项目字段；spread旧对象不证明生产往返 | 不合并idea/notes/goal；保持生产旧值后另做适配验收 |
| `workspaceEnvName` | settingsPage → draft.environment | 部分：环境引用文本；非完整环境模型 | 保留，勿宣称已安装/验证环境 |
| `workspaceEnvManager` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspacePythonVersion` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspaceSetupCommand` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspaceRunCommand` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspaceReportCommand` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspaceSchedule` | 无对应表单；run_adapter固定模拟Job/报告 | 未建高级配置 | 不删除既有值；命令/预算/调度须真实契约后单片开放 |
| `workspaceNodeKindSelect` | fixtures.js固定stepDefinitions；无节点编辑器 | 未建自由节点/DAG编辑 | 保留现有节点原JSON；按执行能力逐片证明，不新增空壳CRUD |
| `workspaceChatAgentSelect` | chat.js targets/resolve/page → thread Agent选择 | 模拟覆盖辅助对话入口；非生产默认Agent持久化 | 退出重复常驻编辑入口；历史绑定缺失不得猜测 |
| `workspaceChatInput` | chat.js page/send → per-project+Agent draft/messages | 模拟覆盖；无真实Provider/工具调用 | 仅按需对话；接线审查会话隔离和副作用 |
| `workspaceToolSelect` | agents.js tools唯一授权；tools.js只读目录 | 项目tools[]专属配置未建；不等价Agent allowlist | 授权不增加第二入口；项目工具定义/专属连接保留待适配 |
| `workspaceModelProfileSelect` | app.js modelField/stepFields + connections.js；draft.model/modelConnection | 模拟覆盖引用快照；生产profile/route_hash未接 | 唯一模型目录入口；保留默认与显式覆盖 |
| `workspaceModelRoutingSelect` | stepModels显式覆盖是模拟规则，无routing_mode字段 | 未建生产routing枚举 | 不声称等价；已有workspace_default/agent_override往返保留 |
| `workspaceModelChatAgentSelect` | chat.js显式临时Agent选择，未保存model.chat_agent_id | 未建默认对话Agent配置 | 临时选择不写默认；后续按需求证明才显高级项 |
| `workspaceModelNotes` | 无专用消费者 | 未建高级路由备注 | 原值保留，不变prompt |

#### WB01节点配置的当前原型覆盖（16类/50项）

所有以下类型均无通用 `nodes[].config` 编辑器，故不能写成“节点字段已交付”。原型 `fixtures.js` 两种固定流程及 `run_adapter.js` 固定输入投影仅证明设计样例。下表逐kind完整列key；列在一行的key仍分别属于该kind，不自动合并、继承或清空。所有生产自定义额外config亦保留，未证明可删。

| kind（完整key集） | 当前消费者及有限对应 | 覆盖决定/正式接线要求 |
| --- | --- | --- |
| `source.repo`：`source.repo.repo_url`、`source.repo.repo_ref` | draft.repo仅资料文本，不是节点repo_url/ref覆盖 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `source.paper`：`source.paper.paper_url` | draft.paper仅资料文本，不是节点paper_url覆盖 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `source.idea`：`source.idea.idea_text` | draft.goal是项目目标，不能替换独立idea_text | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `research.search`：`research.search.query`、`research.search.goal` | 无查询/检索目标消费者 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `repo.clone`：`repo.clone.repo_url`、`repo.clone.repo_ref`、`repo.clone.workspace_dir` | 无克隆消费者；host/path只运行位置 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `path.resolve`：`path.resolve.workspace_dir`、`path.resolve.data_roots`、`path.resolve.output_roots` | draft.data/path是位置线索，未做解析器或root覆盖 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `repo.inspect`：`repo.inspect.workspace_dir`、`repo.inspect.focus_paths`、`repo.inspect.questions` | 无仓库检查消费者 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `dataset.find`：`dataset.find.query`、`dataset.find.dataset_hints`、`dataset.find.data_roots`、`dataset.find.expected_layout` | draft.data是资料，不是数据集搜索配置 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `env.infer`：`env.infer.workspace_dir`、`env.infer.manifest_paths`、`env.infer.env_name`、`env.infer.python_version` | draft.environment仅环境名引用；不推断依赖或Python | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `env.prepare`：`env.prepare.workspace_dir`、`env.prepare.env_name`、`env.prepare.env_manager`、`env.prepare.python_version`、`env.prepare.setup_command` | 无安装/命令消费者；environment不证明环境准备 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `gpu.allocate`：`gpu.allocate.server_id`、`gpu.allocate.gpu_policy`、`gpu.allocate.min_free_memory_gib`、`gpu.allocate.notes` | 仅CPU固定流，host不等价GPU分配/预留 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `run.command`：`run.command.workspace_dir`、`run.command.env_name`、`run.command.server_id`、`run.command.gpu_policy`、`run.command.run_command`、`run.command.schedule` | run_adapter模拟Job读取host/path/environment；无真实命令或调度 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `artifact.collect`：`artifact.collect.workspace_dir`、`artifact.collect.artifact_paths`、`artifact.collect.metric_paths`、`artifact.collect.notes` | run_adapter报告交付模拟，不是通用文件收集 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `eval.report`：`eval.report.report_command`、`eval.report.metric_paths`、`eval.report.notes` | 模拟报告声明/正文/核验分离，不是report_command执行 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `notify.user`：`notify.user.channel`、`notify.user.message` | app.js notify是页面通知，不等价业务通知节点 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |
| `custom.step`：`custom.step.goal`、`custom.step.command`、`custom.step.output_expectation` | 固定流程步骤不是用户自定义step编辑或执行 | 未建；旧值高级保留。按对应真实流程/执行门禁需求再开片；先验API类型、有效值来源、输入引用与保存保真，不向创建基本项堆字段。 |

#### 动态字段与独立能力边界

| 需求/页面 | 实际消费者 | 已有/未建边界与决定 |
| --- | --- | --- |
| Agent基本定义/配置中心 | agents.js：id/revision/name/description/prompt/enabled/tools | 模拟基本编辑、工具唯一allowlist。role旧值保留但无编辑；max_iterations、timeout_seconds、output_format、provider_profile_id无生产预算/路由表单，不当已完成。步骤model覆盖是另一作用域。 |
| 工具定义/配置中心 | tools.js：25个真实ID的只读目录、上下文/副作用/实现状态/使用关系 | 目录覆盖不等于注册编辑。U.id/label/category/capability/description/notes/enabled及provider_profile_id无通用CRUD；模拟不可用场景不冒充后端。repo.search、gpu.allocate、notify.user、schedule.plan真实能力边界保留。 |
| 模型连接/配置中心 | connections.js及connection_views.js：id/revision/label/provider/baseUrl/model/enabled/credentialConfigured | 只两协议模拟连接；M.kind搜索连接、api_key替换/清除、is_default、实际mask/status/missing_fields、模型发现/真实测试均未接。虚构凭据状态不提供密钥输入。 |
| 步骤与输入/流程编辑 | fixtures.js固定stepDefinitions；stepAgents/stepModels独立覆盖 | N.id/kind/title等仅固定定义/运行快照展示，无完整节点编辑器；N.status、handler.mode/agent_id/name/handoff/output_key、output_key、notes、input_mapping、position/links不因有步骤列表而算编辑交付。stepAgents有明确Agent绑定模拟，不能声称等价完整handler契约。 |
| 调试/辅助对话 | chat.js与run_adapter分离 | D.executeLlm/input/templateId调试入口未建；聊天不是调试或运行控制。每请求冻结Agent/模型/来源，真实后端会话Agent隔离/工具副作用/反思写入另验。 |
| 历史检索 | history_views.js列表/报告阅读 | V.status/nodeKind/timeRange/jobId/agentExecutionId筛选未建；先依据真实数量决定最小筛选，不自动加复杂搜索器。 |
| 运行/步骤/日志/报告 | run_adapter单模拟解释器，run_views/history_views只读 | 完整计划、等待、停止后续、交付不完整模拟可展示；无真实SSE/断线/重启持久化/重试attempt/实物下载能力证明，正式接线必须逐项核对API。 |


#### 复用、消融与接线交接结论

- 继续共用F.effectiveModel、C/A/FV诊断、issueList、项目草稿/保存和run_adapter；modelField/stepFields在创建和设置都有实际消费者，不能为设置精简另造解析器。若新增呈现参数，创建默认输出保持原样。
- 设置重复文字可以消融；项目默认与步骤覆盖、整理status与enabled、通用references与路径、goal与独立idea/notes不是同义项，不能为了表格“全覆盖”合并。Agent授权方向已正确，无需新建第二授权入口。
- 生产旧创建/常驻聊天/运行reader/模板编辑/Provider编辑仍有消费者，原型未接线前全部保留。退出须逐个检查§4消费者与真实相同输入/故障对照，不以模拟新页面存在就删除生产路径。
- §5“用户所见—模拟字段—现API—真实缺口”仍是正式交接主表，本片逐字段覆盖是其范围说明；真实API的存在不证明新用途契约。接线前重点保真未展示字段、有效来源/空值、工具用途、引用保护、历史与幂等；未知扩展JSON不可清空。
- 本片只完成审计/设计交接。WB05统一视觉、未建状态和完整正式接线单片计划仍未完成；当时下一片WB05B1现已限定验收；当前切片范围/验收以第三部分顶部为准。其余候选非并行实施清单，不提前开放预算/任意DAG/高级CRUD。


### WB05B1 · 项目设置分区与唯一诊断（2026-11-08，限定模拟验收）

只优化设置页。布局：项目标题/运行·历史·设置导航 → 缺项定位 → 基本资料 → 运行位置（CPU流程）→ 流程与模型 → 按需来源核对 → 取消/保存。资料分析不显示主机/路径/环境。模型、Agent与覆盖的有效选择/来源直接可见；版本与用途在各对象单层入口查看，不把必要选择控件放入多层折叠。密钥仍只有配置中心职责，原型不收真密钥。

| 内容 | 旧展示/问题 | 本片处理与保持 |
| --- | --- | --- |
| 运行位置 | 模型、位置、流程、步骤挤在“运行环境” | 主机+该机目录+可选环境独立分区，CPU固定说明；没有实时运行状态 |
| 流程/默认模型 | 版本和用途说明常驻占行 | 名称、有效模型、来源可见，版本说明按需；更新版本仍明确点击、保存后生效 |
| 步骤执行者/模型 | 版本/用途/继承信息纵向重复 | 桌面并排、小屏顺序展示Agent与有效模型；覆盖、恢复、采用、管理入口保留，完整用途可读 |
| 缺项诊断 | 完整原因在绑定旁和底部重复 | 一个对象定位摘要，原始原因只在字段处；定位聚焦/滚动，主机路径检查在相应字段处，实时输入同步清除已解决原因 |
| 来源与历史 | 来源总表、草稿、提交快照不可丢 | 完整来源核对保留；未知不猜，改项目不改历史；项目默认和显式步骤覆盖继续独立 |

消费者/消融：共享modelField/stepFields/agentField显式settings分支，创建默认分支仍有真实消费者而保留；updateStepFields、模型局部替换与摘要更新同步使用设置呈现，避免交互后又回旧版。flows.reference只加纯view参数，默认分支/选择/诊断/保存均未改变；这是避免复制渲染器的最小范围扩展。复用F.effectiveModel、C/A/FV、issueList和既有配置事务；没有新推进器/状态/诊断缓存。旧混合环境卡和底部全文错误重复展示退出，生产旧页面未迁移仍保留。

浏览器证据仅本地`dev_work/artifacts/wb05b1/`：15组/28截图采集。四宽1440/1024/768/390真实编辑/保存/取消/刷新、目录返回焦点、覆盖还原与模型重绘、Agent旧版定位/采用及唯一全文、长名称/输入错误、资料分析条件字段；另8种过期/未知流程/模型/Agent或步骤场景、缺模型主机目录修复、完整模拟报告后修改未来设置、前后退拒绝/接受。额外四宽详情展开、长Agent用途原文等值、缺覆盖模型定位、唯一DOM ID/ARIA目标存在检查通过并采4图；主代理实看默认1440和390，不宣称逐图人工审查或全站无障碍。

15种固定输入/故障前后对照：保存结果（仅剔除updatedAt）、原始门禁及成功保存后的门禁、run.snapshot、模拟run创建次数一致；未知流程两边均拒绝保存、原项目不变，不假称该场景保存后可运行。两流程第三步初始/覆盖/恢复共6份DOM逐字相同。对照浏览器仅将app/style/flows三个视图资产换回改前副本，不替换业务服务/门禁，不写session状态；不是生产兼容路径。11JS语法和7套既有确定性契约通过。真实API/SSE/Provider/SSH、后端持久化或任务均未访问。

同一“已有项目”fixture、视口高1000下文档高度（不含展开版本/用途）为1440：2561→2422，1024：2537→2398，768：2658→2677，390：2680→2669。主要收益是职责与诊断清楚；768因分区/单列略增，不能以像素达标隐藏字段，也不能与WB05A另一创建fixture/成功通知高度直接相减。主滚动未加固定高度/裁剪。

过程：对照检查器先后出现route回调参数误用、初始session为空、误以为未知流程能保存；额外详情检查漏确认脏稿场景重置，原失败log保留，修检查器后重新跑完整对应检查，不改产品迎合。未知流程沿用validate(3)的“回第二步”提示不适用于已有项目设置，是原路径设计问题，单独挂账等待后续校验/恢复片，不混当前呈现重做。短时通知跨页、长聊天错误、其他未建要求仍按WB05A开放。

正式292源码、稳定规格/AGENTS未改。本地原型3文件与测试/32截图不推送；仅正式三docs更新提交。当时下一片WB05B2只精简创建第三步，现已限定验收；当前切片以第三部分顶部为准。WB05整体体验与真实接线仍未完成。


### WB05B2 · 创建第三步信息减负（2026-11-08，限定模拟验收）

第三步保留项目名、流程需要的主机+目录、项目模型、Agent绑定和步骤模型来源/覆盖操作；先区分要填写与只需核对的内容。流程名称/来源只呈现一处，连接、执行者版本和用途单层按需读，目标/仓库/论文/数据位置/约束在“核对目标与资料”完整回看。项目名仍由目标生成并允许明确改名，未合并独立数据字段。创建只保存，随后用户明确启动；缺项可以稍后配置先保存，原门禁不降低。

| 内容 | 本片决定 | 保留的边界 |
| --- | --- | --- |
| 项目名与目标 | 名称直接编辑，目标与资料单处按需核对 | 自动名随目标，手改后不覆盖；目标/资料逐字段保存和原校验不变 |
| 运行位置 | 仅CPU流程显示主机+该机目录 | 不是目录可写性实测，不提供GPU/环境安装；资料分析不挤进无关字段 |
| 流程/默认模型/执行者 | 有效值与来源可见，版本/用途按需 | 改全局不悄悄采用；旧版、停用、未知引用仍需明确处理，来源缺失不猜 |
| 默认与步骤例外 | 继承直接可读，明确启用才显示覆盖选择 | 无效显式覆盖不回退；切流程保两套独立值，采用/恢复/目录返回保焦点 |
| 缺项与修复 | 顶部摘要只定位，字段处全文唯一 | 真实修改同步重绘；主机/目录检查和模型目录保存返回是明确演示动作 |

新增一个批准的`creation-legacy`固定场景：已知CPU流程/位置与未知模型/Agent旧草稿输入，不含run或终态。现有unknown场景只改已有项目，正常新建不能自然造未知草稿，故不能沿用已有项目证据冒称创建已验。此场景通过项目列表“继续编辑”经第一/二/三步，未知原选择保持、来源未记录，实际选有效定义后才能完整创建；证明的是模拟旧输入处理，不是真实持久化迁移。

消费者/消融：创建和设置共用同一个紧凑modelField/stepFields/agentField/issues及flow.reference，只在实际不同的来源/呈现上用显式creation/settings参数；动态模型替换、覆盖、继承、采用和摘要跟随本表单，第一/二步不启用第三步样式。本轮创建消费者退出旧default后，重新核所有JS及本地契约，不再有旧渲染调用者，删除五个旧完整default分支及其专属flow/Agent/步骤定位支路；管理/采用/repair等真实动作保留。B1时“创建仍消费default”是当时事实，不能在本片继续当保留理由。继续复用原F.effectiveModel、C/A/FV诊断、issueList、草稿/保存和唯一模拟run_adapter，不加领域副本。

相同紧凑CSS15条用保留各端作用域/优先级的逗号选择器共享，保留位置分区、模型间距与grid gap等真实差异；不为了行数抽新框架。额外三版本对照只在before浏览器换原app/style/flows、premerge只换合并前style，after使用当前静态文件，不替换领域/门禁、不写session状态。四宽创建两流程在常规已配置场景的后代几何/选定computed属性合并前后相同；B1设置四宽同样与本片改前相等，非所有状态/所有CSS认证。

本地证据`dev_work/artifacts/wb05b2/`：主浏览器20组/30截图采集，额外8项详情/16图；设置回归另15组/28图，不混作本片新增能力。四宽1440/1024/768/390两流程创建→明确启动→报告声明/正文/核验，键盘改名/焦点、条件字段、覆盖还原/动态缺项、目录返回/刷新、长内容/错误/取消；另缺模型主机目录修复、保存失败显式重试、自动名与手改、切流程独立覆盖/前后退、目录更新后明确采用以及旧草稿未知引用均实际点击。额外两流程四宽核对目标/多行仓库/论文/数据/多行约束逐字等值，详情无嵌套。未宣称全键盘路径/屏幕阅读器/真实新手试用或后端通过。

14固定输入/故障前后创建payload、门禁、run.snapshot及模拟run创建次数一致；仅归一项目及snapshot根id/updatedAt，nested流程/连接/Agent身份/版本/来源完整保留。10设置初始/模型/覆盖/继承/采用DOM与4份第一/二步DOM逐字相同；不以源码逐字不变替代行为。11JS语法、7套既有确定性契约及上述设置浏览器回归通过。主代理实看CPU1440、reading390、unknown1440及缺模型390代表图，不声称46图逐张人工审核。

同目标/3类资料/约束、视口高1000，未展开详情时文档高度：CPU流程1440 2104→1844、1024 2080→1820、768 2209→2101、390 2319→2215；资料分析1440 1844→1508、1024 1820→1484、768 1858→1673、390 1968→1787。页面仍需滚动，主要减少重复默认信息；不把所有必要控件折叠或固定高度遮住。

过程审查：首轮检查器误以“继续编辑”链接有data-resume-draft按钮属性，保留失败后按真实入口修检查器完整复跑；不加产品替身。监督进一步发现摘要CSS漏#issues包装、旧草稿非空失效模型却称“尚未选择”，修后加四宽实际字号/列表样式/摘要定位/全文唯一和未知来源断言，再完整重跑主browser、前后对照、details和设置回归。先前合并前后computed相同只能说明那些死规则同时没生效，不能当设计正确证据；修后实际命中已核。全程无真实API/SSE/Provider/SSH/任务。

只改本地app/style/flows、一个fixture与README，正式292源码/稳定规格/AGENTS不变；原型、测试、46张主片截图及28张设置回归截图不提交。G40/G26/G27和未建历史检索/下载导出/故障反馈/必要跨区导航等继续开放。该片当时下一片WB05C1现已限定验收；WB05C2本次报告正文下载/缺失反馈亦已限定验收，当前切片以第三部分顶部为准。

### WB05C1 · 子任务日志阅读与精确运行返回（2026-11-08，限定模拟验收）

日志页先提供“返回本次运行”和“返回所属步骤”，标题下看项目提交快照、运行编号、所属步骤及本次job.status；主机+目录在正文前紧凑呈现，长值完整换行。日志保原字符串，长正文才局部滚动。计算方式、环境、Job/run/step内部标识及已有退出码移至单层“任务信息与诊断”，不再先铺长位置卡。停止后续但Job仍运行的提示原样保留。

| 内容/动作 | 来源与条件 | 处理及保存影响 |
| --- | --- | --- |
| 项目/运行/步骤 | run.snapshot.name、run.number、plan与Job双向关联 | 不用当前配置/其他run补来源；缺关联显示不可用，不造步骤链接；无写入 |
| 状态/停止 | job.status、run.stopRequested | 只投影本次记录，停止后续不当外部已停；无写入 |
| 主机/目录 | job.host、job.path | 必需语境不折叠；缺值明示未记录，不代入本机；无写入 |
| 日志 | job.log原字符串 | 不trim或截断；空占位不写回，不据此判断任务完成 |
| 返回 | 精确project/run URL及history来源 | 复用data-focus-step回同run步骤，不查latest；保原步骤入口 |
| 诊断 | 原compute/env/id/run/step/exitCode | 单层按需，含退出码0；无新状态或下载功能 |

获批log-location场景只有长项目名称、虚构主机/目录输入，仍经网页显式启动原adapter生成完整计划与Job；无预置run/终态，不证明主机真可连接。自然adapter总生成日志，空正文/缺关联仅独立view克隆验证，不能当自然异常/恢复全链验收。

本地dev_work/artifacts/wb05c1/：主浏览器19组/25图，四宽1440/1024/768/390正常运行→日志→直接run/步骤返回、刷新/前后退、局部Tab/焦点及诊断展开、停止后续仍running和之后done、长日志/失败/长项目与位置。历史第1次run日志直回第1次，不跳最新；第2次不能借第1次Job，未知路由不可用。正文逐字等于本次job.log，查看往返前后完整project/runs（含report、events、Job）相同；只有本地静态请求，无console/pageerror。

另12项/12图为四宽空正文、缺步骤关联和HTML转义受控投影：克隆记录只替换隔离浏览器main，不写session，不是页面入口产生异常或完整关联修复。5种固定输入running/failed/done/stop-running/empty的新旧正文、状态、run/step/report DOM相同，记录不变；before只换原run_views/style静态资产，不替换adapter。此为只读视图对照，非生命周期/外部副作用或全站布局等价认证。

既有运行浏览器20组/23图回归覆盖实际创建、显式启动/重复点击、等待/阻塞/失败/停止、Agent前置结果、执行100%与交付未验证区分、旧新run/模型单步骤/缺配置门禁；检查器仅同步任务标识详情入口，并用details.open判断展开状态。11JS语法、9套既有确定性契约通过。主片37张与回归23张是截图采集数；主代理实看正常1440、失败390、长位置诊断390，不宣称逐图人工、全键盘/屏幕阅读器或真实新手试用。

过程：两个只读检查器首次Python三引号换行转义使evaluate报JS SyntaxError，保留first-failure.log，仅改raw string后整套复跑；未改产品迎合。设计沿用frontend-design已记录来源/许可，无新依赖。监督仅只读审查，不实现或执行测试。

消融：旧默认位置长卡/内部ID前置退出，字段保全文；app.runRoute仍唯一消费者、jobPage单一投影，run/step日志入口及run-code/run-log保留现消费者。新增样式限日志类，不造组件框架、状态缓存或推进器。实际仅本地run_views/style/fixture/README四文件改变，app、run_adapter及其他目录/视图与前版逐字相同；正式292源码、稳定规格/AGENTS未改。原型/测试/截图/日志不提交，真实API/SSE/断线/文件读取未验，G40/G26/G27继续开放。该片当时交接WB05C2，现已限定验收见下文；当前切片以第三部分顶部为准。

### WB05C2 · 本次报告正文下载与缺失反馈（2026-11-08，限定模拟验收）

用户在标明演示模式的报告页正文前点“下载正文”，取得这次报告原文txt；缺失/空白只说明原因，不生成空文件。执行完成与交付核验继续分开：已有模拟正文即使未核验或核验不可用也能下载，但“结果不完整”不变。入口仍为http://127.0.0.1:8933/；已有项目→开始运行（模拟）→显式完成子任务/分析→阅读本次报告→显式声明/写入正文即可体验，也可选“长报告”“报告正文缺失”“报告核验不可用”场景。页面明确演示，未接真实后端/文件。

| 内容/动作 | 来源与条件 | 处理、反馈及保存影响 |
| --- | --- | --- |
| 可下载条件 | 纯只读H.downloadDescriptor({project,run}) | project.id与run.projectId及report.projectId/runId/id对应；run为done且已声明，report.stepId对应最后已完成Agent步骤，正文非空白；按钮和点击共用，不另存权限状态 |
| 当前来源 | 精确报告路由及按钮project/run/step/report标识 | 点击重读session，不用latest或缓存body；过期/错身份拒绝，原历史/步骤返回照旧 |
| 正文 | 本次report.body原字符串 | Blob按text/plain;charset=utf-8生成，不加BOM、来源头或元数据，不trim/截断/改换行；来源在文件名和页面提供 |
| 文件名 | run.snapshot.name、run.number、完整run.id | 项目名最多32个Unicode字符的安全片段，清路径/控制/bidi字符，附第N次、完整run ID、“演示报告.txt”；不拿当前设置改历史来源 |
| 正常反馈 | 本次下载动作 | 只称“已将本次演示报告正文交给浏览器下载”；不能观测浏览器/系统取消或保证落盘，不提升交付状态 |
| 失败重试 | URL创建/anchor触发异常或过期身份 | 局部role=alert及“重试下载”，不整页render/persist/notify；保正文原节点/滚动/焦点，刷新或切run不保留旧提示 |
| 资源清理 | 临时anchor、object URL | finally删anchor，成功延迟1秒撤销URL，触发失败立即撤销；不写project/run/report |

**实际浏览器与边界**：主检查19组、17个实际接收文件、14原截图；edges另5组、2文件、2视口图，共19个文件以expect_download实际接收保存，UTF8逐字等于body、无BOM、完整run来源，project/run/report不变。主检查另对17个文件追踪URL回收；edges两文件补DOM/滚动/焦点及特殊名检查，不将其说成同样逐个追踪资源回收。包括首次创建显式运行/声明/写入，未核验/已核验/核验不可用，历史旧run、新run、另一项目、错项目URL、刷新/前后退和精确历史/步骤返回。四宽1440/1024/768/390检查长正文全文、缺正文、局部失败重试、换行无横向溢出及局部focus+Enter；特殊长名经创建表单输入并验保DOM/滚动/焦点，不是另行更名。所测自然固定run ID下文件名小于255字节，不外推任意无限ID。

另19项只读投影（15种输入加4宽长名称）克隆记录、不写业务session：缺/空白body、错project/run/step、空ID、步骤未完成、未声明、失败run、错误run ID/number均无可用下载；保原文空格/CRLF及核验不可用语义。这不是自然异常恢复/迁移全链验收。6种固定输入running/done-no-report/declared/written/verified/body-missing对照，只换原history_views.js；去掉下载区后原report/run/step/job/history DOM和记录相同，只归一新生成report ID/createdAt，不当生命周期/外部副作用认证。

既有报告浏览器26组/24图、11JS语法、9套既有契约及11脚本唯一引用/装配顺序/原CSP检查通过。主片原截图20张（14+2+4），另2顶部裁剪只辅助读长图，回归24张另计。主代理实看未核验1440、失败390顶部裁剪及特殊名390视口；监督只读审部分图和证据，未执行测试或实现。没有逐图人工、全Tab/无障碍、真实新手试用、真实API/SSE/文件权限或浏览器取消验收，不把截图数当体验完成率。

**过程审查**：首轮wait_for_function表达式被原CSP拒绝unsafe-eval，改箭头predicate；第二轮evaluate恢复API返回函数被Playwright自动执行导致类型错，改无返回语句；edges首轮Python误用JS.repeat改乘法。失败log留本地，修检查器后整套重跑，未放宽CSP/门禁或写session终态、人工补记录。实现审查先发现漏run done/report declared，冻结前补保护后最终验证。URL.createObjectURL/anchor.click抛错及过期按钮ID是受控浏览器/DOM故障，不是产品自然恢复证据。

**消融与接线**：下载无旧入口要删，原阅读/报告三事实/来源返回仍有消费者；reportDelivery仍唯一交付投影，无第二状态服务/推进器。只改本地history_views/app/style/README，run_adapter及其他原型资产、生产292源码、稳定规格/AGENTS不动，沿已记录frontend-design指导，无新依赖。正式report接口只在file_verified返回artifact.content，否则null，不回退inline answer；C2未核验模拟body不能当真实文件接线。先用已核验content；若另提供未核验文本，须独立来源/类型/授权及契约，不降实物核验要求，完整/export不在本片。

网站入口补测独立于上述主片：新Chromium标签页选择已有项目，实际点击运行→子任务日志→同次运行→显式子任务/分析完成→报告→声明/写入，1440与390无页面异常、390无横向溢出。4张截图另存site-review，不混入20张主片原图。主代理实看项目列表1440、等待运行1440及报告390，主任务与页面分区清楚，小屏单列可读；等待状态在摘要/说明/步骤重复、报告核验提示重复仍有精简空间，记后续呈现观察，不扩本片或当全站体验通过。

证据本地dev_work/artifacts/wb05c2/，过程/消融dev_work/reports/wb05c2-review.md，脚本dev_work/smokes/；原型/截图/下载/结果均不提交。正常截图仍见上一页“项目已创建”通知；app.notify全局notice仅4.5秒清除、路由未清理，承接WB05A问题。该片当时交接WB05D1，现已限定验收见下文，当前切片以第三部分顶部为准。极长下载错误虽完整换行仍占多行，留后续观察；G40/G26/G27、WB05整体体验及正式接线继续开放。

### WB05D1 · 短时通知的页面归属与跨页清理（2026-11-08，限定模拟验收）

创建、修复或保存后，在动作返回的页面看到一次简短结果；进入其他页面后不再带着旧提示。用户取消离开仍在原页，提示不被误清，也不因取消而重新计时。只调整本地通知生命周期，没有改变运行、项目保存、错误恢复或下载语义；入口仍为http://127.0.0.1:8933/。

| 触发/输入 | 页面归属与清理 | 输出/保存影响 |
| --- | --- | --- |
| chooseFlow同页切换、startRun拒绝、引用删除拒绝 | 当前页，4.5秒或下一次接受导航 | #notice只放短事实，缺项/引用等长期诊断原位置保留；无持久消息字段 |
| useFlow、saveProject、saveConnection（连接/Agent/流程）、repair | 原go→notify顺序：归属动作到达页 | 正常创建/保存仍有一次可见结果，不粗暴清掉目的页成功；不改变业务调用 |
| go接受新路由 | approveLeave通过且push成功后clearNotice | 清原DOM/取消timer；同route、取消不清，不影响草稿确认 |
| 浏览器popstate/原生hash | 接受且目标不同后清 | restorePop及取消离开不清，前后退不重播；保原索引/焦点/来源 |
| reset与旧repair/model别名归一化 | 共用clearNotice | 不留孤立timer，兼容别名仍到唯一连接目录；未造第二导航器 |
| notify新消息 | 先取消旧timer并递增代际，再给4.5秒 | 旧回调即使已排队也不能清新提示；同页render不续期，刷新不恢复 |
| 长文本 | 仅#notice overflow-wrap:anywhere | 完整折行，空notice原本无占位；不裁剪、不引入弹窗/嵌套滚动或新依赖 |

主浏览器22组、13张原截图：网页创建→正常显式运行→精确Job日志→本次运行→显式完成→报告声明/写入→实际接收原文下载→历史，配置门禁原样保留；项目/连接/Agent/流程保存和目录采用/主机修复均在目的页反馈，快速进入运行/历史/日志/报告/配置后旧提示消失。自然4.5秒消失、先等2000ms再发新提示且再等2800ms仍保新提示，之后自然过期；不用加速timer代替正常路径。浏览器前后退/刷新、拒绝go或跨owner历史返回保原反馈实际验证。四宽1440/1024/768/390实际创建/保存/空历史、局部focus+Enter后主内容焦点、无横向溢出；4组长notice是DOM-only压力样式，不是自然长原因。

edges6组包括两个经UI创建的项目切换、无demoIndex原生hash取消并恢复路由/提示、保原生调度的timer包装观察reset确实取消、受控重播旧回调不清新消息，以及受控DOM删除/adapter.start=null失败后的原门禁和显式重试。主检查强触disabled启动和Storage异常也是受控防御检查，无业务session写入或人工终态，不能当自然故障恢复。报告局部下载仍独立，不被通知清理吞掉。

7固定输入新旧对照，只替原app/style：保存后页、历史、目录、切流程、取消离开、接受离开、保存失败，完整main DOM及state相同（仅归一保存project.updatedAt），只有接受导航后notice清空是预期差异。不将其外推外部执行生命周期或副作用等价。最终八套独立浏览器回归为创建20、设置15、运行20、模型连接30、Agent23、流程往返16、流程编辑17、报告26，均errors[]；11JS/9既有契约及唯一脚本引用/加载顺序/原CSP通过。最终result单独索引，早期失败日志没有当通过合并。

过程：主检查器先错连接label、误以host场景含已有项目、单次back仍在同草稿owner本来不应弹离开确认；改正确label、从创建修复、跨owner两级返回，未改产品。旧原始回归引用已退出控件，创建/设置/运行改用已有B2/C1当前适配套件；连接仅展开版本详情/改唯一管理入口，Agent仅诊断定位/用途全文入口，保留原断言并完整重跑。所有失败log保留，不放宽门禁/CSP、删除检查或手填结果。只改本地app/style/README，生产292源码/稳定规格/AGENTS、fixture/领域/下载模块不动。

消融：原reset散落清DOM退出，清理集中一个函数服务已有导航/重置/归一化，不新增持久通知状态或通用消息服务。保现notify的任务结果和长期错误分工，未因顶栏精简删除恢复入口。沿已核frontend-design（§8），无新依赖。主代理实看success1440/390与clean-history390；监督只读看success1440、clean-history390、long-notice390及证据，不运行测试/不改实现，不宣称逐13图人工或全Tab/无障碍/真实新手验收。

极长DOM通知390仍可约600px高，只证明完整换行，不是长错误体验解决。WB05A已有“辅助对话失败原因过长推远重试”当时交接WB05D2（现已限定验收见下文），该片只做failed pending短事实/恢复动作前置和单层完整原错误；不从错误中文猜原因码，不改retry/attempt/来源快照。下载长错、状态重复、脏稿/检索及正式接线独立待办，不扩本轮。证据dev_work/artifacts/wb05d1/、过程dev_work/reports/wb05d1-review.md；原型/脚本/截图/结果仅本地，三正式docs提交推送。G40/G26/G27和WB05整体体验未关闭。

### WB05D2 · 辅助对话失败阅读与重试入口（2026-11-08，限定模拟验收）

用户不用先读完长错误才找到恢复动作。入口http://127.0.0.1:8933/，选择“对话长错误”场景，在项目打开辅助对话、发送后显式点“模拟回复失败”即可查看。全部仍为演示数据和动作。

| 输入/动作 | 展示顺序与来源 | 保存影响 |
| --- | --- | --- |
| 来源、失败和尝试号 | 原pending.snapshot/status/attempt | 只读，保发送时来源，不混当前run或Agent |
| 短事实 | 本次回复失败，原消息已保留 | 不解析错误中文猜原因，不承诺已修复 |
| 重试本条消息 | 原data-chat-action及request ID | 原retry/admission判定；同ID追加attempt，单user消息 |
| 完整原因 | 单层details展示原pending.error | 仅escape，不trim/截断；空或缺原因明确未记录 |
| waiting/无pending | 原page分支 | 完整HTML逐字不变，除page外的12个导出方法源码不改 |

本片只修改本地chat.js的page失败投影、4条聊天作用域CSS及README。原请求来源、状态和attempt之后，先显示“本次回复失败，原消息已保留。”和原“重试本条消息”，再用单层“查看完整原因”展示escaped原error。空或缺error如实说明未记录；不trim、不截断、不从中文猜原因码。无固定高度/嵌套滚动，无新错误框架；waiting及no-pending完整HTML逐字不变，除page外的12个导出方法源码原样。app和send/complete/retry/门禁/快照/执行内核不改。

实际主浏览器19组/12原图，四宽1440/1024/768/390长短错误、重试在全文前、局部focus→Tab→Enter展开、刷新/前后退已验证。同request重试attempt加一，用户消息不重复、snapshot不变，只有显式reply才有回复。正常网页启动的run及精确步骤来源返回、显式完成模拟run/report后讨论不改完整业务对象；两固定chat-projects项目及实际设置重绑Agent隔离、缺模型唯一配置修复返回、disabled/unknown/empty门禁、目录实际停用连接后retry拒绝且原错误可读均通过。两项目来自固定场景，不称本片经创建流程创建。只有本地静态资源，无page/console错误，无真实API/SSE/Provider/SSH。

20项受控只读clone投影/12图，另waiting和no-pending两种完整HTML及除page外的12个方法源码对照通过。长/短/HTML/空白换行/CRLF/空或缺error/无空格长token安全完整，session不变；新旧canonical DOM、来源/状态/按钮及pending外整页DOM相同。持久error逐字保留；HTML parser与旧投影相同把CRLF/CR规范成LF，不宣称DOM逐字保CRLF。clone投影不是自然故障恢复或旧数据迁移全链。

chat23/run20/reports26独立浏览器回归最终均errors[]、exit0；11JS的node --check、9套既有契约（含聊天26项）和脚本顺序/唯一ID/原CSP装配通过。聊天回归只同步先展开原因再读全文的选择器，原断言不删。主harness首次把目标option硬编码report，实际值含run/step身份；保browser-first-harness-failure.log，改读取渲染可用值后整套重跑，产品未迎合检查器。没有放宽门禁/CSP、写session终态或人工补记录。实现生成命令有执行前transport语法错误，无副作用；改工具输入后执行。

主代理实看compact390/expanded390/compact1440；监督只读看compact390/expanded1440及证据，不实现、不执行测试。没有全部24图逐张人工、全站键盘/无障碍、真实新手或真实Provider恢复验收。长原因展开仍按主滚动完整阅读，不用裁剪隐藏。证据dev_work/artifacts/wb05d2/，过程dev_work/reports/wb05d2-review.md；原型、测试、截图和结果仍仅本地。

**消融与后端交接**：旧失败全文默认先于动作的展示退出，原来源/说明/事件消费者及app聚焦保留，无新错误分类器/状态服务或重试层。生产292源码、稳定规格/AGENTS不动，沿§8已核frontend-design，无新依赖。§5现API映射不变；真实辅助聊天无副作用/上下文隔离/幂等仍须独立契约，模拟retry不证明真实恢复。

**当时交接WB05E1（现已限定验收见下文）**：未知流程的已有项目可显式保存独立基本资料，保原未知引用/覆盖/扩展及旧run/report，unknown诊断和新启动拒绝继续保留；创建选择及名称/目标/URL校验不降低，不自动采用首项，不把保存称流程修复。详细范围见第三部分，本轮不实施。下载长错、状态重复、脏稿/检索和正式接线仍独立待办，G40/G26/G27及整体WB05不关闭。

### WB05E1 · 已有项目未知流程的资料保存边界（2026-11-08，限定模拟验收）

入口http://127.0.0.1:8933/，选择“流程引用未识别”，进入项目设置，修改资料后显式保存。用户不再因流程未识别而被要求回到不存在的“第二步”；原流程仍待确认，保存资料不会启动或修复流程。

| 输入/动作 | 规则及反馈 | 保存影响 |
| --- | --- | --- |
| draft.editingId | 必须在当前projects确有对应项目，才免除创建式流程选择错误 | 不为伪/孤立editingId扩新迁移能力 |
| 名称/目标/URL | 原非空/格式校验和当前字段定位 | 无效值不提交，未知流程不覆盖name错误 |
| templateId/flowSelection及覆盖/扩展 | 复用原草稿克隆与old spread保存 | 保未知原引用，不自动采用目录首项或补版本 |
| 显式保存 | 短反馈只称项目设置已保存 | 原诊断和issueList/startRun门禁保留，旧run/report不改 |
| 设置页提示 | 原底部一行按是否有模板显示 | 无模板时明确可保存资料、暂不能开始新运行；不添卡片/输入 |
| 创建 | 原选流程及最终校验 | 两种保存都不能用unknown草稿创建替代流程 |

本片限定在独立模拟前端：已有项目的流程引用未识别时，可以显式保存名称、目标和参考资料；原未知流程和运行阻塞保留，不自动选目录首项，不宣称流程修复。名称/目标非空、仓库/论文URL格式仍校验；创建仍须明确选择流程。只改本地app.js两处：validate(3)仅对当前projects确有editingId的项目免除创建式流程选择错误；设置底部在无法取得模板时提示“可保存项目资料；流程尚未确认，暂不能开始新运行。”。复用原makeDraft克隆、old spread/保存白名单及issueList/startRun，保存内核和FV不变。

主浏览器14组/9原图通过：四宽1440/1024/768/390实际unknown项目长名称/资料编辑、草稿刷新、唯一诊断定位、未知目录返回原草稿、显式保存/刷新后原引用和门禁不变；局部Tab到名称/目标与焦点检查。空名称/目标与非法repo/paper仍定位字段，取消/后退拒绝和接受/前进不误存；正常/停用/旧版/legacy基本资料保存不改流程版本或启动资格。正常网页生成的模拟run及报告不被后续设置改写，精确来源保留；已有设置故障显式重试、两种流程创建及两个UI创建项目间草稿隔离通过。检查器无业务session注入或人工终态，无page/console错误，仅静态本地请求。

另6组受控边界通过：以已实际UI生成的run/report为初始克隆，加入未知引用/不透明扩展/停放覆盖，保存后原flowSelection/stepModels/stepAgents/model/位置/扩展及历史整对象不变；初始saveFails输入与Storage.setItem抛错均保输入/旧项目、显式retry才保存；空templateId仍可保存资料且保空；未知创建初始草稿两种保存均拒绝，第二步选择仍必要；强触禁用启动按钮仍被原startRun拒绝。fixture只替静态响应中的初始输入，不写session终态，不称自然导入/迁移或真实故障恢复。edges共3图，其中“缺身份打不开”的观察图不是通过的能力截图。

16种原有场景固定输入前后保存数据/门禁/快照/模拟run次数/目录相同，另6份创建DOM逐字相同；unknown仅资料保存由拒绝变为接受、初始底部hint改变，引用/门禁/目录/run数不变。对照递归归一updatedAt，不外推外部生命周期等价。创建20/设置15/run20/reports26/chat23五套独立浏览器回归、11JS语法/9既有契约及装配/原CSP通过；只替输出目录，保原回归断言。app只两处替换，另12个原型资产逐字不变，无style/新依赖或状态框架。

E1当时未解决边界（现已由E2限定修补见下文）：当templateId和flowSelection两键都完全缺失，设置页显示重载/重置故障页；受控初始输入的old/new真实浏览器均复现同错。流程reference调用adopted，两个undefined相等检查后读取缺失s.revision抛错；projectTemplate本身先返回null，不是触发处。这个输入未通过保存验收，不能外推为所有缺失流程均可保存。当时交接WB05E2修只读流程引用防御，不补默认身份或快照、不放宽启动。已有run的“开始新运行”仍可点但原startRun拒绝，以及unknown运行概览流程/步骤空白、模型显示未选择的呈现，分别登记后续观察，不在本片修改。

过程：先真实UI复现旧name错误“返回第二步”并保before-390；边界检查先假定旧项目有fieldSources、误用旧run按钮名、误以projectTemplate({})会抛错，保失败log后校正初始输入/实际入口/诊断定位并完整重跑，产品未迎合测试。缺身份fallback是实际旧问题，独立old/new确认而非删掉失败场景；在结果中列observations，不混入passed。实现命令一次transport语法错误在执行前拒绝，无副作用。主代理实看unknown-edit390/1440和unknown-saved390；不称全部截图逐张人工、全站Tab/无障碍或真实新手试用。

证据dev_work/artifacts/wb05e1/，过程dev_work/reports/wb05e1-review.md；原型、测试、截图/结果和本报告仅本地。生产292源码、稳定规格/AGENTS及§5真实API映射不变，无真实Provider/SSH/API/SSE验收。G40/G26/G27、WB05整体体验和正式接线保持开放，长期goal保持active，本轮不实施下一片。

**当时交接WB05E2（现已限定验收见下文）**：仅使缺失/畸形流程身份与快照的只读引用投影安全返回未确认，实际设置可打开并保存独立资料；保字段缺失和执行阻塞，不补默认或迁移版本。详细范围/验收以第三部分为准。稳定规格不变，真实后端接线仍独立安排。

### WB05E2 · 缺流程身份记录的只读引用防御（2026-11-08，限定模拟验收）

缺流程身份/快照的记录现在也能打开设置、保存基本资料；界面继续明确流程未确认，不能开始运行。没有自动选流程、补版本或修改历史。本片不新增页面或配置项。

| 输入/消费者 | 处理与输出 | 保存/执行边界 |
| --- | --- | --- |
| adopted私有读取 | 先核非空string身份、非null非数组selection/snapshot，再沿原精确身份/正整数revision/字段类型判定 | 返回原snapshot或null，不trim替换身份、不写回 |
| reference/diagnose | 缺或无效记录沿原未记录来源/未确认诊断，不能因undefined相等读缺snapshot | 显式采用入口仅原unrecorded/outdated；不假采用当前目录 |
| projectTemplate及app/chat/run消费者 | 已知固定步骤结构与采用版本仍分开，unknown自洽快照历史显示保持 | 13导出源码不变不等于行为未变；guard只改变无效读取 |
| 保存资料/刷新 | 原E1保存路径，保字段缺失/原畸形值及未展示扩展 | 无创建副作用，原issueList/startRun继续拒绝 |
| 故障 | 原Storage失败显示输入与重载/重置入口 | 显式重试，不把只读防御当迁移或恢复服务 |

**实际验收**：主14组/9图，在1440/1024/768/390通过隔离fixture静态响应准备缺双键输入，实际点击设置、长名称/资料编辑、草稿刷新、唯一诊断定位/目录返回、保存及刷新保原字段缺失、启动禁用。格式校验/取消/前后退，原正常/disabled/legacy/outdated、正常UI历史run/report保真、原设置故障重试、两流程创建和两UI项目隔离通过。edges13组/2图覆盖8种缺/空/null/畸形selection/snapshot记录、旧UI历史克隆初始输入的扩展/覆盖/Agent保真、真实新运行点击拒绝、初始saveFails/Storage失败回滚与恢复入口、缺身份创建两种保存拒绝和两隔离项目。检查器不注入业务session/终态；受控初始输入与Storage抛错不当自然导入/迁移或真实故障恢复，只有本地静态请求，无page/console错误。

**投影与对照**：42项VM只读输入无mutation，35原输出相同，7实际差异含3旧抛错、4无效空/数值身份或带属性数组不再当已采用；按actualChanged统计，不将预设expectedChange当证据。完整覆盖selection/snapshot缺/空/null/数组/字符串/数值/布尔、身份错配、revision/字段缺失，以及正常/更新/停用/unknown自洽历史。13导出方法源码原样，私有guard改变其闭包调用行为。17原场景实际网页保存/门禁/快照/目录/模拟run次数相同，6创建DOM逐字相同；递归归一updatedAt，不当外部生命周期认证。

**回归与过程**：创建20/设置15/run20/reports26/chat23/流程编辑17/流程往返16/E1主14八套回归，以及11JS语法/9既有契约/脚本装配和原CSP通过。投影首轮跨VM原型误比较，改JSON输出比较；edges首轮inner_text忽略折叠内容，改text_content读原节点，保失败log后完整重跑。未为测试改产品、关闭门禁或人工补结果。主代理实看missing-edit390/1440、storage-failure390；监督只读复核和选图，不执行测试/实现，不称全部11图人工、全站键盘/无障碍/新手或真实API验收。

**消融与接线**：仅本地flows私有adopted加一个guard及README，其他12原型资产/生产292源码/稳定规格/AGENTS不动，无新schema/迁移框架、状态副本或运行依赖，沿§8已核frontend-design指导。旧异常读取支路退出，原诊断/采用/保存/执行消费者保留。§5真实API映射不变；原型不是生产数据修复能力。证据dev_work/artifacts/wb05e2/，过程dev_work/reports/wb05e2-review.md；原型/测试/图/结果仅本地。

**E2当时交接WB05F1（现已限定验收见下文）**：已有终态run页开始新运行的按钮/原因/设置入口使用当前项目原就绪诊断，保这次历史run/snapshot/报告；活动run继续原进度/停止，不拿当前缺项改历史。无run概览的空字段/模型来源另片，详细范围/验收见第三部分。E2未实施F1；G40/G26/G27、整体WB05和正式接线继续开放。


### WB05F1 · 已有运行页的新运行就绪反馈（2026-11-08，限定模拟验收）

历史结果和下一次运行分开：旧run显示原执行/交付事实；当前项目设置有缺项，“开始新运行”提前禁用，旁边给出原因和一个“检查当前项目设置”。处理目录、明确采用并保存后回同次运行，只有再点击才开始新run。活动run仍显示原进度和停止动作，不因当前配置变坏而改写历史。

| 输入/消费者 | 展示/动作 | 保留边界 |
| --- | --- | --- |
| projectPage latest alias / runRoute精确run | 仅!V.isActive时传原issueList(saved project)，active传null | 不读旧snapshot判断新资格，不因活动run新增当前配置诊断依赖 |
| runPage newRunIssues | Array且空才ready；缺项禁用，完整escape原label；缺省/null/非数组提示未确认 | 纯投影，无新增持久字段、校验器或状态副本 |
| 终态操作区 | 原状态+开始新运行→阻塞时一处新运行待配置/设置入口→原解释/进度/报告/步骤 | 不把执行完成改成阻塞，不重复新增历史状态卡 |
| data-edit / 设置及目录往返 | 沿原settings?from精确run/history，处理后采用/保存并返回 | 不自动采用目录变更或启动；原startRun/R.start最终门禁及active去重不动 |

**网站实际验收**：14组主浏览器，先用旧备份资产从实际入口复现“可点但拒绝”；新版正常UI首次创建→明确启动→模拟子任务/Agent完成→报告声明/写入/核验。四宽1440/1024/768/390实际停用流程后旧结果保真、按钮禁用，局部Tab/Enter进入设置→目录恢复→采用/保存→回同次run（含history来源）→显式新run及新版本快照；刷新/前后退、alias、两项目、原R.start已有active去重、waiting/blocked/failed/stopped、允许保存不完整目录但禁止启动均通过。run/report整对象不变；只请求本地静态资产，无page/console错误。模拟状态只靠明确演示动作，不假装实际实验完成。

**隔离边界与对照**：16组初始fixture输入克隆正常UI产生的历史/活动run，只改变当前配置或目录/资源；10种流程/模型/Agent/目录缺项、四宽长原因、active当前path=null两个调用者通过。不是自然导入/迁移/恢复；长原因图的历史标题仍正确取run.snapshot，不能据当前长名声称长历史名覆盖。48人工只读组合+停止请求比较中，active完整HTML相同，终态移除唯一新启动按钮/原因区后其余HTML相同，project/run不变；5其他导出源码同，app只两处输入，不当自然生命周期认证。

**相关回归/过程**：创建20/设置15/运行20/报告26，11JS/9既有契约、11脚本顺序/唯一ID/原CSP通过。四次harness失败保log：route参数绑定、旧页details重绘关闭、原诊断词误写、误判不完整设置不能保存；纠正检查器后整套重跑，未改产品迎合或关闭门禁。主代理实看completed-ready1440/new-run-blocked390，监督只读审证据及选图，不执行测试/实现，不称逐图人工、全站键盘/无障碍或真实新手验收。

**消融/接线**：退出旧终态无条件可用按钮；复用issueList/startRun/R.start及data-edit，没有第二readiness内核或通用框架。旧设置导航仍有消费者，报告/步骤/日志和历史保留。仅本地app/run_views/style/README变，其余10资产、生产292源码、稳定规格/AGENTS不动，沿§8既有frontend-design指导。§5映射保持；真实接线须消费后端当前readiness和提交时快照，不将本地诊断或模拟revision当后端事实。原型/测试/结果仅本地，证据dev_work/artifacts/wb05f1/、易读测评及过程dev_work/reports/wb05f1-review.md；独立预览http://127.0.0.1:8933/只在本机访问。

**F1当时交接WB05F2（现已限定验收见下文）**：无run准备概览的未确认流程/模型来源呈现，修空字段或错误“未选择”暗示，按现有保存记录说明未知/未确认，不新增诊断、自动采用或改配置。名称目标重复/部分状态重复、历史检索/证据导出等继续单独候选；G40/G26/G27、WB05整体及真实后端接线未关闭，详细范围见第三部分。


### WB05F2 · 无运行准备概览的未确认配置呈现（2026-11-08，限定模拟验收）

准备页不再把“流程无法识别”误当成“没有选模型”。未知流程给明确名称/步骤占位，保留已有默认模型并说明实际使用待确认；已知但版本未确认时，步骤只是流程定义，不暗示已采用。配置仍要到原唯一设置位置处理，不能因摘要有值就绕过原启动门禁。

| 事实输入 | 摘要输出 | 不做的推断/写入 |
| --- | --- | --- |
| template(p)为空，templateId无/未知 | 尚未选择流程/未识别流程；步骤在流程确认后显示 | 不用未知自洽快照名冒认已识别、不猜第一流程 |
| known fixed结构、原FV.diagnose非ready | 名称旁流程待确认，步骤标仅流程定义 | 不把固定fallback当已采用、不更改目录/版本 |
| known快照名空/空白 | 流程名称未记录，固定步骤仍显示 | 不误判未知身份，不改adopted/门禁或裁剪存储 |
| known Agent步骤有效选择 | 原stepSelection/modelText及继承项目默认/该步单独指定来源 | 覆盖空值不回退，未确认流程另有来源说明 |
| 无known步骤时的p.model/modelConnection | 项目默认记录，实际使用待流程确认；无记录沿原未选/版本未记录文案 | 不读取停放覆盖；有记录不等于可用，不另造模型诊断 |

**实际浏览器**：19组/16清单图（另旧资产before1），四宽1440/1024/768/390 unknown字段/资料保存/刷新前后退与局部Tab/Enter，CPU/reading两流程四宽从不完整创建保存→唯一设置补齐→明确启动完整计划→模拟子任务/Agent→报告声明/正文/核验→设置取消保旧run/report；实际覆盖还原、legacy/old/disabled、两项目脏稿隔离通过。主浏览器无page/console错误，只有本地静态请求，原模拟演示动作仍手动，不手填终态。

**边界/消融对照**：30组/4图中28是无run输入/视口案例（含四宽同一长压力场景），验证缺失/未知/快照名不冒认、默认记录/未知引用/停放覆盖、known空白名/legacy/错配/停用/移除/旧版、步骤显式空值/reading覆盖/转义；同输入只替静态app，摘要外DOM、完整演示业务state和gate相同。另2种active/done+report克隆来自正常UI，alias与精确run完整DOM/业务state相同；仅受控初始输入，不当自然迁移/恢复。17固定网页场景保存/门禁/快照/目录/模拟run次数及6创建DOM相同，只归一updatedAt，不当外部生命周期认证。

**检查/过程**：创建20/设置15/运行20/报告26回归、11JS/9既有契约/装配/原CSP通过，空白名防御加入后相关验证全按最终实现重跑。第一次edges定位超时原因未确认，独立同输入旧新复查正常，加等待/失败诊断后整套未复现，保原log不擅归因；另一次clone fixture箭头JSON漏括号为harness错误，修脚本整套30组通过，产品不迎合。主代理实看unknown390/CPU-ready1440/legacy390/long390，监督只读审实现/证据及选图，不执行测试/实现，不称逐图人工、全站键盘/无障碍、真实新手或后端通过。

**范围/未完成体验**：仅本地app.projectPage无run摘要/README改变，原latest分支/其他app函数、其余12资产/生产292源码/规格/AGENTS不动，无CSS/helper/新状态或依赖。旧空dd和未知即模型未选的展示退出，原完整issues/设置/启动入口及有run内容保留；复用modelText/stepSelection/FV.diagnose，没有第二就绪或配置内核。证据dev_work/artifacts/wb05f2/，过程dev_work/reports/wb05f2-review.md，入口http://127.0.0.1:8933/仅本机；原型/测试/截图/结果仅本地。§5后端映射不变，真实接线消费后端事实而非本地推断。

极长项目名和模型名虽全文可读、无横向溢出，仍把主要动作推得很远，**不能记简洁可达性已通过**。F2当时交接WB05G1（现已限定验收见下文），只改善准备概览标题/目标/模型的紧凑阅读与单层显式全文，字面一致才去重显示，原记录/缺项/动作不变；历史检索及其他页面标题/状态重复留候选，详细范围见第三部分。G40/G26/G27、整体WB05和真实API/SSE/Provider/SSH/实物交付仍开放。


### WB05G1 · 准备概览长文本阅读与主操作可达性（2026-11-08，限定模拟验收）

长文字先看摘要、需要时读全文。只改变无run准备概览，不裁剪保存值、不隐藏配置缺项或改变运行条件。名称与目标只按trim后字面全等去重复，不按相同前缀或语义推断；完整原文仍可读。

| 输入/判定 | 默认与全文 | 数据/动作边界 |
| --- | --- | --- |
| p.name/p.goal、原modelText(selection) | 名称28/目标64/模型40码点摘要；长值提供全文，trim同raw异也保原文入口 | 只读字符串，不改全局modelText/原值，不把码点当完整emoji字素 |
| 名称目标trim全等、raw也全等 | 默认h1一次；长时全文一次标项目名称与研究目标 | 短值无额外控件；原两个存储字段都保留 |
| trim全等、raw不同 | 默认省重复目标段，完整名称/目标仍分别原样读 | 保首尾空白、Tab/换行；DOM的CR/CRLF规范为LF，存储原样 |
| 名称与目标不同（含相同前缀） | 两个摘要均显示，必要时共用查看完整名称与目标 | 两者不误合并，单层自然主滚动/pre-wrap |
| 模型长值与来源 | 独立查看完整模型连接，继承/单独指定/待确认常驻 | 不折叠原完整issues/补配置/开始动作，无新诊断或状态 |

**主浏览器**：13组/15图，四宽1440/1024/768/390实际网页输入长名/多行目标、目录改长label并明确采用/保存；Tab/Enter两个全文开合、LF全文与原记录一致、来源可见、无横溢、刷新前后退/取消草稿/两项目隔离、短同值/同前缀不同、步骤长模型与长原诊断通过。每宽继续明确run/完整计划→手动模拟子任务与Agent→报告声明/正文/核验，run/report不变。只本地静态请求、page/console错误为空，不手填session终态。原生details跨页重建默认关闭，没有展开持久状态，局部键盘不当全站无障碍验收。

**边界/动作对照**：29组，27无run初始文本/配置案例涵盖trim同raw异、同前缀、长单字段/相同长文本、28/29及64/65/40/41阈值、空/转义/astral/CRLF、unknown/default/停放覆盖、legacy/步骤覆盖/disabled/长诊断；另2种UI生成active/done+report克隆。阅读区以外DOM、业务state、原来源和gate旧新相同，有run alias/精确全DOM/state相同；受控初始fixture不当自然迁移/恢复。12组短/长ready/长blocked×四宽使用同一UI长输入克隆，只替旧新app/CSS；阅读区外DOM/state/source/gate及实际明确启动snapshot/次数相同，原门禁不替换。短样例按钮位置不变，长四宽上移386.73/466.62/435.5/978px；390×1000 ready所需滚动约1110→132px、blocked约1355→377px，证明本组可达性改善，不能称所有输入首屏或全站体验完成。用户主动展开全文/长诊断仍可自然变长。

**检查与消融**：17固定网页保存/门禁/快照/目录/模拟run次数及6创建DOM相同，只归一updatedAt；创建20/设置15/运行20/报告26、11JS/9契约/装配原CSP通过。初选32/72/48经390图自审调整28/64/40，最终实现全部相关验证复跑，未改业务迎合检查。主代理实看初选closed/full-model390与最终closed/短同值390，监督只读审实现/证据及选图，不执行测试/实现，不称全部23图人工、全站键盘或真实新手通过。退出旧长文本常驻/重复目标段，原设置/历史/日志/运行/报告入口保留；局部preview供3个已有文本消费者，不把语义不同的Agent用途/流程说明外提框架，删除一条重复source-label margin。仅本地app无run阅读/局部style/README变，其余11资产、生产292源码/稳定规格/AGENTS不动，无新全局helper/业务状态或依赖。

证据dev_work/artifacts/wb05g1/，易读测评及过程dev_work/reports/wb05g1-review.md，预览http://127.0.0.1:8933/仅本机；原型/脚本/截图/结果本地。§5后端映射/持久事实要求不变，真实API/SSE/Provider/SSH/实物交付未验，G40/G26/G27和整体WB05保持开放。

**G1当时交接WB05G2（现已限定验收见下文）**：运行概览的提交快照标题当时仍全文常驻，只改善这一阅读职责。因准备/运行已是两个真实同语义消费者，可提最小纯名称/目标展示helper，显式输入name/goal/esc/唯一id前缀，接入app/run_views并退出副本，不外提配置/诊断/状态；共享样式和脚本装配须独立验。旧run继续取run.snapshot，当前项目后改名/目标不改历史。step/job/history/chat/report、模型诊断及后端都排除，详第三部分；本轮不实施G2。

### WB05G2 · 运行概览提交快照的长标题阅读（2026-11-08，限定模拟验收）

运行以后，也能先看简短名称和目标，把注意力放在当前步骤；需要核对时点“查看完整名称与目标”。项目后来改名或改目标，旧运行仍显示提交时内容。

```text
返回项目列表
提交时名称摘要 / 不同的目标摘要
查看完整名称与目标（单层全文）
运行 | 历史 | 设置
原运行状态、停止/新运行、完整步骤、日志与结果
```

| 部分 | 本片决定 | 保存和联动 |
| --- | --- | --- |
| 准备概览 | 明确传当前项目name/goal | G1阈值/同值处理及全文不退化，模型来源/完整诊断/动作常驻 |
| 运行概览 | 明确传run.snapshot.name/goal，前缀包含run.id | 设置保存只影响以后新运行；展开/收起不写业务或阅读持久状态 |
| 共用展示 | project_context.js仅导出preview/heading，显式文本/esc/idPrefix | 不选项目、不读全局state、不决定就绪或推进流程；app旧副本删除 |
| 文本和样式 | 名称28/目标64码点后加省略号；原文单层自然展开 | 只trim字面同才省目标，原空白/raw异/转义保留；不称码点能保全部emoji字素簇 |
| 装配 | helper先于run_views与app；样式限上下文及原准备模型 | CSP/系统字体不变，无新增第三方依赖；step/job/history/chat/report标题未迁移 |

**实际网页验收**：13组/15图，1440/1024/768/390四宽从网页创建长名/多行目标、明确启动，到Tab/Enter打开/关闭完整原文、日志与步骤往返；刷新和前后退不推进任务或保存展开。每宽明确模拟子任务/Agent结束、声明/写入/核验报告后，去设置改当前名称/目标，再回旧运行核对完整原文及完整run/report对象；历史来源、刷新与返回焦点保持。390另外实际阻塞、子任务失败、停止后续但先等待当前子任务结束，以及两UI创建项目/短同值无多余控件均通过。只请求本地静态资产、page/console errors为空；无session终态注入、自动进度或真实API/Provider/SSH。

**旧新对照**：37组。27个准备页初始受控输入复用G1边界，闭合/展开全DOM和computed样式、state、门禁一致；10个运行投影是正常UI记录克隆，包括waiting四宽、Agent处理中/完成报告/阻塞/失败/停止请求/已停止390。只替旧新index/app/run_views/CSS，去掉本片标题阅读区后，其余运行DOM、history来源、完整state、步骤/子任务及存在时报告reader全DOM一致；不当自然恢复或真实任务验证。固定长输入的运行概览四宽上移253.95/326.73/299.5/622px，只说明该组可达性改善，不保证所有输入首屏；用户展开全文后仍自然变长。

**检查与过程**：5组独立纯helper检查覆盖不可变输入/无全局state读取、转义身份与正文、空白/同前缀、码点边界和双消费者不同ID；创建20/设置15/运行20/报告26/准备G1主13回归、12JS语法/9既有契约、12脚本顺序/唯一ID/原CSP通过。调用本片验收的静态资源白名单及VM装配只新增helper，不放开网络限制。报告DOM比较两次因既有事件焦点临时h1 tabindex不同失败，原HTML确认只差该属性，最终只归一该焦点属性；修脚本时一次误断言改后目标仍旧值，另复制回归到新目录使两脚本ROOT错误未启动，均保日志并纠正检查器后完整重跑。产品实现未为检查器迎合。

消融：名称/目标只有一个算法；模型仅借纯preview，不外提模型选择/诊断/来源；运行正文及其他导出不变，不扩全站框架。主代理实看closed1440/390和full390；监督只读审实现/证据及选图、不执行测试或实现，不称全15图人工、全站无障碍或新手验收。原型4个既有运行资产、README及1新helper，其他9资产、正式292源码/规格/AGENTS不变。证据dev_work/artifacts/wb05g2/、易读测评dev_work/reports/wb05g2-review.md；预览http://127.0.0.1:8933/仅本机，原型/脚本/截图/结果不提交，正式仅三docs。

**G2当时交接WB05H1（现已限定验收见下文）**：历史当时全部铺开，先加一个按当前项目已展示运行次数/提交目标检索的输入框；空白显示全部，字面匹配，区分无运行/无匹配，跨run/报告往返恢复条件和焦点。优先复用现view记录，保既有来源白名单，不加筛选面板/分页/导出或搜索隐藏字段，详第三部分；本片只计划。运行状态重复等候选保留，§5真实API/持久事实映射不变，真实交付及整体WB05/G40/G26/G27仍开放。

### WB05H1 · 运行历史最小检索与返回恢复（2026-11-08，限定模拟验收）

历史里只增加一件事：输入运行次数或提交目标，找到要回看的那一次。读完运行、日志或报告再返回，查找条件和位置仍在。当前项目后来改目标，旧记录继续按旧目标查找。

```text
既有项目标题 / 运行 | 历史 | 设置
运行历史         共 N 次运行 / 找到 M 条，共 N 次运行
查找运行 [运行次数或提交目标          ] 清除
原倒序记录：第N次 / 日期 / 提交目标 / 执行状态 / 交付 / 报告
```

| 字段/场景 | 决定 | 保存和联动 |
| --- | --- | --- |
| 查找输入query | 去首尾空白、小写后对已显示“第 N 次运行”与snapshot.goal作字面包含，空白全量 | 不搜索隐藏名称/ID、当前项目新目标或另一项目；不添加筛选/分页/导出 |
| 计数/空状态 | 总数与匹配数分开；无运行给去运行，无匹配提示换词或清除 | 只一个外部清除；不在空结果里再放同义按钮 |
| 视图归属 | 原VIEWKEY.positions按canonical historyUrl保存raw query，并保y/focus | 读取query限string，旧视图条目兼容；不写业务KEY、不增加URL条目或来源协议 |
| 输入过程 | 只替计数与结果，不重建input；组合期间延到compositionend | 只作用当前项目；清除回输入；演示reset清旧query，防相同demo ID复用 |
| 行/返回 | 初始页和输入更新共用唯一historyResults，退出旧副本 | 原倒序、状态/交付、run/report链接不变；run_views与from白名单不改 |

**实际网页**：最终12组/10图，四宽1440/1024/768/390分别创建两次不同目标的正常CPU模拟运行及完整报告，后改当前目标，再按大小写/原空白/次数/旧目标查找；无匹配/空白/清除、输入节点/浏览器history长度不变，完整业务记录不变。实际run→步骤→日志→原历史、报告→原历史、焦点/滚动/刷新前后退，以及另一正常创建项目同目标隔离、长转义query、reset后复用demo ID均通过。主浏览器仅本地静态请求，无page/console errors、无session终态注入或真实接口。

edges9项包括8个初始视图条目（旧y/focus、null/数字/数组/对象query、raw空白/大小写/HTML）和实际390 Tab→输入→Tab清除→Enter回输入，另1图。前8用正常UI记录克隆作F.fresh初始fixture，并仅预置视图存储，不当自然迁移。composition是受控DOM事件验证组合期不筛选/结束才应用，保input；没有宣称真实操作系统IME或全站无障碍验收。

**对照与消融**：14纯投影检查含10种检索/空白/隐藏字段不命中、跨项目同目标/空、原始query转义及旧8非列表导出源码保持；四宽旧新浏览器4组只替app/history_views/style，原行全HTML/computed、非历史run DOM、完整业务state一致，实际双击新运行的snapshot/次数/步骤键/状态/事件类型与Job数一致，旧run精确不变（不比较新随机ID/时间）。创建20/设置15/运行20/报告26/G2主13回归、12JS/9既有契约/原12脚本顺序/唯一ID/CSP通过。

监督截图发现初版type=search的原生×与外部清除重复，正式改type=text+role=searchbox，仅留外部清除；原生Escape清除路径随之退出，保初版证据并按最终方案重跑相关检查，不能把只数button当“没有重复”。纯投影检查首轮把旧renderer倒序再反一次而失败，保log修预期后整套14通过，产品未迎合；静态自查在开测前修正搬行的旧project.id闭包引用。主代理实看最终filtered1440/390和no-match390，监督只读审实现/过程/选图，不实现或执行测试。

仅本地app/history_views/style/README四文件变，其他11资产、生产292源码/规格/AGENTS不变，无新依赖/新状态核。长历史目标仍自然全文，未把此片记为全站简洁完成。证据dev_work/artifacts/wb05h1/、易读测评dev_work/reports/wb05h1-review.md；网站http://127.0.0.1:8933/仅本机，原型/脚本/截图/结果不提交。§5补历史检索映射；真实API加载范围/截断/冻结字段须接线核实，不把当前本地过滤称远端全量检索。

**H1当时交接WB05I1（现已限定验收见下文）**：本轮受控阻断app.js后，header存在而main空、没有正文恢复入口（dev_work/reports/wb05i1-static-risk.json）；这是资源故障输入，非自然断网。只补首次静态加载/启动错误的可读正文与真实重载，正常退出占位/启动监听，保session与精确URL、不重放任务；不接管render错误页/业务态或扩到API/SSE/超时预算，具体范围见第三部分。本片不实施I1，真实执行/交付及整体WB05/G40/G26/G27仍开放。

### WB05I1 首次静态加载与启动失败恢复（2026-11-08，限定模拟验收）

网站仍为 http://127.0.0.1:8933/ ，只绑定本机。首次打开先有可读正文；正常加载后占位退出，没有“读取完成”或30秒常驻说明。必需静态组件加载失败、启动异常或加载已结束而未完成初始化时，正文给固定短原因和一个真实“重新加载”。重载重新请求当前document，保完整hash/query和演示会话，不reset或重新运行实验。

```text
HTML正文：正在打开工作台 / 加载页面组件 / 浏览器刷新指引
  → 正常初次render和装配结束：退出占位及启动监听，释放导航
  → 必需资源或初始化失败：固定短原因 + 重新加载（独立真实按钮）
无JS或boot+app都缺失：保留HTML指引，不提供不能工作的JS按钮
```

| 输入/状态 | 处理及输出 | 责任边界 |
| --- | --- | --- |
| 必需script或stylesheet的error | index上的data-boot-required为唯一清单；固定组件失败 | boot本身不在自身监测清单；不反射原错误/URL |
| 首次ready前window同步未捕获异常 | 首因锁存；DOM未到先等DOMContentLoaded再画失败 | 无超时/重试推进器，不声称捕获任意异步错误 |
| window.load结束仍未ready | 显示加载已结束却未完成启动 | 不是等待N秒判断；永久pending不在范围 |
| 正常首次render/事件装配返回 | app通知ready，释放壳，移除error/load/popstate监听 | 原render自己捕获的错误仍归原reload/reset页 |
| 晚期初始化失败 | 主区替换，旧sidebar/topbar/dialog inert；VIEW记录早返；启动先注册的popstate守卫在失败时保留 | 不阻止浏览器URL本身改变；重载以当时URL为准，不回滚业务 |
| 单独boot缺失 / 无JS | app可渐进正常显示 / HTML写启用JS与浏览器刷新 | 同步boot永久pending可能阻塞body解析，不能保证占位可见 |

**实际验收**：主22组，四宽1440/1024/768/390自然加载、真实网页创建CPU项目→明确run→精确日志→手动模拟子任务/Agent完成→报告声明/正文/核验；正常session精确URL重载无残留占位。每宽独立abort app/helper和初始化throw，真实Tab/Enter重载各恰好新增一个document请求，旧完整run/report不变；另实际历史来源的`?from=history`保留。晚期初始化异常后hash/back仍保失败页；空app 200/load补漏、长私有错误固定文案、CSS失败、ready后ErrorEvent不接管均验证。故障前正常beforeunload合法记录焦点/滚动后，追加只读观察冻结输入；故障页至恢复KEY/VIEW逐字不变，未向storage写终态、调用ready或手工补记录。

edges10组：1440/390受控持住app时HTML可读/壳不可操作，放行后自然启动；禁JS、boot+app缺失无假按钮，boot独缺正常渐进。另用受控测试HTML把首个必需script改同步并abort，确证main尚不存在时首因锁存/DCL失败可见；此为测试顺序，发版原12脚本仍defer。既有render注入错误在启动后/直接刷新仍归原错误页，解除后真实重载保一个run；ready后required资源error也不接管。edges所有截图不等待font readiness，用于避免held-app令截图工具等待；CSP禁止外部字体，正常主浏览器未用此设置，不把截图辅助当产品恢复条件。

**对照/回归**：四宽旧新4组仅换index/app/style、使用正常UI生成的完整记录克隆作为fixture初始输入，ready后主DOM、选定computed、历史DOM、完整state及实际双击新run的快照/次数/步骤/事件/Job数相同，旧run精确保留；新随机ID/时间不比较，克隆不当自然恢复。13JS/9既有契约、创建20/设置15/run20/report26/G2主13/H1主12回归通过。新boot同步在首、其余12defer顺序和CSP不变，其他11原资产逐字相同；无外部库/新业务状态核。

**过程与消融**：晚期异常的初版守卫在fail时才注册，实际window-target旧router先执行，失败页被项目列表覆写；调整为启动即先注册、正常ready移除/失败保留，整套主检查复跑。390早期比较VIEW y0→2是正常beforeunload记录，改只读观察基线，保持故障段严格相等；没有改产品迎合。edges字体等待和标题含项目数量的selector两次harness失败保log，修检查器后完整复跑。旧空main退出；原render局部错误页、业务状态、start门禁与运行内核保留，无第二路由/恢复器。

仅本地index/app/style/README四原文件及新boot变；生产292源码/稳定规格/AGENTS未变。主代理实看normal1440/390、app故障1440、late故障/loading/noJS390，监督只读核实现/过程/证据与选图，不实现或测试。证据dev_work/artifacts/wb05i1/，易读测评dev_work/reports/wb05i1-review.md；原型/脚本/结果/截图全本地，正式只三docs。API/SSE断线、Provider/SSH/实物交付、永久加载、完整无障碍/真实新手体验及整体WB05/G40/G26/G27仍开放。

**I1当时交接WB05J1（现已限定验收见下文）**：本轮正常1440/390截图可见done运行同区有两个蓝色主操作，390先见“开始新运行”后见“阅读本次报告”。下一片仅把已完成运行以阅读本次报告为主、新运行为次，保留报告缺失/未核验的真实文字和可达入口，不改变运行/交付判断、新run配置诊断/门禁、URL/快照或其他状态/页面。本片只记录，不实施J1。

### WB05J1 已完成运行的主操作层级（2026-11-08，限定模拟验收）

只调整执行已完成的运行概览。阅读本次报告继续使用原交付投影和蓝色primary；开始新运行成为结果下方普通按钮，相关当前配置缺项跟随它，避免读旧结果先遇到新配置诊断。报告缺失/未核验时仍可进入报告查看具体事实；蓝色表示主要阅读入口，不能据颜色声称已完整交付。

```text
第N次运行 + 原执行状态
原说明 / 完整计划进度
原结果交付文字
[阅读本次报告]  唯一蓝色主操作
────────────
原新运行配置诊断（有缺项时）
[开始新运行（模拟）] 普通次操作，仍受原门禁约束
```

| 输入/动作 | 输出与归属 | 保留的事实/约束 |
| --- | --- | --- |
| run.status=done | 原H.summary与reportUrl不变；新run/诊断从顶部移到其后 | 一个原按钮字符串供两个实际分支消费，旧done顶部入口退出；无新动作框架 |
| 原newRunIssues/null | 原newRunReady/disabled、同一个完整诊断 | 当前配置只影响新提交；不修改旧run/report |
| 阅读报告 | 原run/step来源、hash/query、返回ID/焦点 | 未声明/未写/未核验/完整仍由原reportDelivery决定 |
| 新运行 | 原data-start-project→app.startRun→R.start | 同原校验/持久化/active去重，不改事件或预算 |
| 其他run状态/无run | 原布局/控件/正文 | 不批量重排等待/失败/停止或准备页 |

**实际浏览器**：主14组/20图。四宽1440/1024/768/390从实际长名称/目标创建CPU项目，明确启动→打开精确子日志→模拟完成子任务/Agent；依次核未声明、声明无正文、正文未核验和完整。report始终唯一primary且在普通new-run之前，实际Tab/ShiftTab/Enter可达，原未交付事实可读；没有通过时间或动画推进。另每宽明确选正文缺失/核验不可用场景，done仍显示不完整且可阅读原因。history来源`?from=history`、报告返回焦点/刷新前后退、当前保存相对路径后新run禁用但报告可读、唯一设置修复返回同URL、显式新run保旧报告、原active复用不多建均通过。另实际阻塞、失败、停止请求/等待回执、停止后记录作旧新对照输入。

**对照/冗余检查**：14份UI产生记录×四宽56组，只替旧/新run_views/style及同一初始fixture克隆；非done/无run完整main HTML/state相同。done去掉原/新new-run与诊断容器后其余DOM相同，原报告完整DOM/来源/选定computed、按钮仅去class后的属性和业务state一致；实际双击new-run的快照/次数/步骤/Job数/事件类型一致，旧run精确不变，新随机ID/时间不比较。克隆仅初始对照，不当自然恢复；无storage终态写入。新run按钮仅一个，原动作/门禁/诊断内核未复制，原H.summary保持唯一交付投影。

创建20/设置15/run20/report26/G2主13/H1主12回归、13JS/9既有契约通过。仅本地run_views/style/README三文件变，13其他原资产逐字相同；runPage外代码原样，app/adapter/history/index/boot/原CSP、生产292源码/稳定规格/AGENTS不变。只追加run-next一条局部CSS，无外部依赖/字体。首轮harness误用不存在的expect_url失败保log，改实际Enter后wait_for_url后整套主14通过，未改产品迎合。

主代理实看complete1440/390、blocked-new-run390、report-missing390，监督只读审实现/过程/证据和部分图，不实现/测试。主无page/console errors，只有本机静态请求；未注入状态、调用ready、放宽门禁或补记录。证据dev_work/artifacts/wb05j1/，易读测评dev_work/reports/wb05j1-review.md，入口http://127.0.0.1:8933/；原型/测试/截图/结果均本地，正式只三docs。长设置/其他页、区域API加载/断线、真实后端/实物交付及完整无障碍/真实新手未因此通过，整体WB05/G40/G26/G27仍开放。

**J1当时交接WB05K1（本轮已审计，见下文）**：把原用户设计要求、§2字段/§3状态、§5真实API映射和§7实际验收/剩余项重新对齐，核哪些必须先补独立原型、哪些可直接用已有后端、哪些是真实能力缺口，在既有§5主映射表补齐schema、权威状态与消费者，§7只引用证据，明确阻断接线必需/可后置体验/仅真实运行可验，交付唯一后续小片。沿本文更新，不新增重复映射表或计划体系；不修改原型/生产/后端、不在审计中批量实现或把“未验”改完成。只读源码/历史证据，必要真实浏览器抽查明确来源，不跑真实副作用；不能据静态200宣称API恢复或整体体验完成。本片仅计划K1，不执行。

### WB05K1 剩余需求与正式接线交接审计（2026-11-08，只审计）

本轮只改本文及二三文档。开片基线61c3b30，无用户未提交改动；原型16资产指纹留本地，结束核未变。只读相关HTTP路由、工作区/运行公开投影、冻结账本、日志、目录/路由/聊天和现web消费者；没有重审292文件、读取config/data、调用真实API或重新跑历史浏览器用例。

成果集中于§5：更正项目列表误用execution-overview及“只支持POST”说法，明确实际响应包装；区分公开投影与持久workspace_snapshot、普通历史裁剪和plan_hash例外、核验正文与模拟可读正文、有限N04停止与通用模拟停止。Profile版本/删除保护、步骤覆盖、目录清空及无副作用聊天均登记为对应写入前的合同缺口，不把CRUD存在当交互可用。保留原58字段及16类50配置逐项处理决定，无新增通用编辑器或重复能力表。

| 审计证据类别 | 本轮实际做了什么、能证明什么 |
| --- | --- |
| 静态事实 | 主代理核核心路由/服务/消费者；只读调查代理核目录/模型/聊天，主代理另核关键方法和空值/停止/报告/裁剪分支。证明源码现合同，不能证明真实运行与网络恢复 |
| 既有动态证据 | 查阅WB05A网站调查原报告及J1过程报告/实际结果等既有材料，保留各片四宽/键盘/异常的原限定。未把历史PASS加总为本轮浏览器通过；A的旧“未建”表已标历史快照 |
| 覆盖与无实现变更 | 本地wb01_check核58控件、16类50配置、292源码台账与链接；原型16文件指纹、实际diff/staged scope核只三docs；稳定规格/AGENTS/生产代码不变 |
| 过程与监督 | 开片/白话审计报告位于dev_work/reports/wb05k1-*；独立监督只读检查范围、接口事实、证据和提交，不实现或跑测试。未新建全局状态机/框架，不删除旧消费者 |

**K1当时交接WB05K2（现已限定验收，见下文）**。只证明一个列表区从读取中到空/有结果、失败重试、已有内容更新失败保旧，以及迟到响应不覆盖较新读取或离开后的页面。它不补聊天/后端，不接真实API，不扩成全站加载框架。其后再按§5收尾条件核原闭环与正式首迁计划；本轮不提前宣称整体WB05完成。

### WB05K2 项目列表区域读取与失败恢复（2026-11-08，限定模拟验收）

只改本地app/style/README三个既有资产，无新helper/global脚本/依赖，不改index、CSP、fixture、运行/目录状态核、生产292源码、稳定规格或AGENTS。列表数据仍唯一state.projects；新增闭包视图phase/hasData/error、读取代号与Promise完成句柄，统一render识别初次/实际进入/离开，同页重绘不重发。只有当前代号、活动区域和列表路由都匹配才更新反馈；重入读当前源，reset使原请求失效。退出原同步直接展示，projectRows/业务数据/搜索语义与原消费者保留。

```text
项目列表 → 区域读取中 → 成功有项目 / 确认空列表
                      → 失败 → 重试读取
已有项目 → 刷新 → 更新失败保旧内容 → 继续原项目 / 重试
演示菜单单独提供成功、失败、长原因、较早回执及再发一次读取
```

默认一次微任务读取，手动场景由菜单明确完成Promise，无定时器/网络请求/业务推进。首次读取未完成不冒空成功；失败短句+重试、原原因单层按需展开。后续刷新保搜索输入/结果、链接与读取动作焦点；正常无顶栏成功块，未失败时按钮称刷新、失败才称重试。每次重新进入列表重新读当前演示源；浏览器刷新重建正常读取，不复活手动pending。故意保留的旧pending句柄仅供竞争演示、无生产队列上限或持久化合同，不得搬去接真实网络。

| 本片实际验收 | 证据与范围 |
| --- | --- |
| 四宽1440/1024/768/390 | 主26组/29图：首次等待→失败→实际Tab/Enter重试→成功；已有查找结果刷新失败保旧、长原因收起/全文、精确继续/返回、刷新、空成功与无匹配区分；局部焦点/无横溢通过，不称完整无障碍 |
| 竞争与副作用边界 | 真实菜单/链接：新失败后旧成功不覆盖；离开配置页及前后退；读中创建保存→返回新读成功→旧失败不删新项目；reset后旧成功无影响；刷新不复活pending。主检查不写session或终态，读取动作前后业务记录不变；模拟读取同一源不证明真实取新数据 |
| 旧新对照 | 11份网页正常生成输入×四宽44组，仅替旧新app/style；非列表完整main DOM及标题/动作样式、业务记录相同，列表原rows投影相同。克隆仅固定输入对照，不当自然恢复；44组不宣称旧新双击副作用对照 |
| 相关回归 | 创建20、运行20、报告26及13JS/9既有契约通过，运行回归包含原双击单run、等待/停止/快照等约束。原index脚本顺序/CSP与其他13资产字节不变；只本地静态请求，无page/console error |
| 过程与消融 | 读视图局部更新不重建已有search/links，不造第二项目库/全局请求框架；非列表业务函数保留。主代理实看桌面首次失败、窄屏保旧/加载与长错收起，监督只读核实现/过程/选图，不实现或跑测试 |

检查器失败均保本地：空匹配div误要求visible→改attached/busy；关闭按钮误取可见字→改accessible name；旧回归部分文字“已有项目”撞新场景描述→限定data-scene；一次驱动更新/启动并行误读旧脚本→顺序复跑；对照脚本错报告动作名/route回调默认参数被Request覆盖→修检查器再完整通过。没有改产品迎合断言、关闭门禁或人工补记录。首次按钮措辞自审小改后完整主26及44对照复验。

证据dev_work/artifacts/wb05k2/、白话测评dev_work/reports/wb05k2-review.md，浏览器脚本dev_work/smokes/wb05k2_*，预览http://127.0.0.1:8933/；原型/脚本/截图/结果仅本地，正式仅三docs提交。真实API/SSE/网络中断/自动重连/后端取新内容/Provider/SSH/实物交付未验，G40/G26/G27和整体WB05仍开放。

**K2当时交接WB05L1，现已核证见下文**；核证不预设设计阶段完成，真实接线仍未开始。

### WB05L1 原始闭环核证与正式首片交接条件（2026-11-08，只验收）

以下是L1当时结论；后续L2已解除导航设计阻断，唯一当前剩余分类见§5，L1原证据不改写成当时已完成。

源码基线a7d3502。正式仅修改本附件、二三文档；现有16份原型资产与292生产源码均未改，稳定规格/AGENTS不动。结论：**核心模拟流程达到本轮所列判据，整体WB05仍未完成**。原用户五项中1字段/职责由§2/§7保留可核清单，2创建、3运行结果、4设置配置有限定模拟交付，5整体体验仍缺跨区导航及failed操作层级，不能改写原要求为“核心能点通即可完成”。

| 原要求/验收项 | 本轮实际证据及可沿用内容 | 结论与限制 |
| --- | --- | --- |
| 新人创建→必要设置→明确启动→等待→结果 | 当前1440/1024/768/390四条全键盘产品路径；创建零run，显式启动完整2步、下游pending，刷新不推进；演示完成后独立声明/写入/核验，4个真实浏览器下载文件正文逐字一致 | 核心模拟通过；场景重置用鼠标、结果通过明确演示按钮返回；没有真实任务或物理报告 |
| 日志/子任务/步骤精确返回及辅助对话 | 四宽实际日志→所属步骤→run焦点，Agent步骤进入辅助对话显式发送/模拟回复后返回，报告/历史/设置/连接目录往返 | 本轮键盘165次停靠均检查可见outline；不是屏幕阅读器或全站无障碍认证 |
| 继续已有项目、旧run与历史来源 | 已有项目由固定场景提供，第二项目由网页创建保存；继续项目打开该项目当前run投影；历史链接含?from=history，精确run回看/前后退/刷新与完整run/report不变 | 通过；项目根路由是当前run投影，不能误当固定旧run URL；本轮没有新测多run并发，沿用K2 run回归的限定证据 |
| 缺模型/主机/目录定位、处理、返回 | 三种固定场景从创建开始；模型只到连接编辑并明确采用新版，主机/目录只到各自模拟检查，回原草稿创建零run | 通过模拟交互，未输入真实key；“模拟检查通过”不证明主机可达或目录可写 |
| 未保存/取消/刷新/换项目隔离 | 1440设置修改→取消离开保草稿→刷新→明确放弃；保存新目标不改活动run；第二资料项目不显示host且不串项目 | 本轮抽样通过；四宽长表单/站内后退/整页草稿用WB04A与后片原证据，不把抽样写成每个编辑器本轮重验 |
| 阻塞/失败/停止及长日志 | 390真实演示动作：blocked零child、显式解除同run；退出7不启动Agent；停止后child仍running，child完成后才stopped/后步skipped；长日志可局部滚动且无页面横溢 | 状态语义通过限定模拟；其余宽度沿用当前K2 run回归，未重跑真实后端恢复 |
| 执行结束≠交付完整、缺正文/核验不可用 | 四宽done 2/2先显示尚未验证；390两异常及补核实际verification.status=unavailable，一种无body、一种有body，均不显示完整交付 | 通过模拟；主检查器误读不存在的report.verified，断言不足；补核实际verification字段及正文，不以不存在字段当成功证据 |
| 空/长名称/长错误/长报告、区域读取与启动恢复 | 本轮空列表/长日志/异常截图；检查K2 browser/creation/run/reports结果及源脚本，I1启动、H1历史、J1长标题原证据仍按各自边界引用 | 非本轮全部重跑；K2克隆对照仅证明固定输入展示差异，不证明自然恢复/全部副作用；真实网络未验 |
| 明亮克制、系统字体、一主滚动、正常顶栏精简 | 本轮46截图采集，四宽均无页面横溢；主代理实看waiting1440/settings1440/create390/report390/failed390五图，frontend-design来源/许可沿§8 | 运行与配置分开；设置仍需纵向阅读，不能仅凭高度认定缺陷。没有逐图人工审查或真实新手试用 |
| 一个任务区一个主要操作 | failed390实际同一surface内2个primary：开始新运行、查看当前步骤；补核DOM与源码一致 | **未通过，设计阶段阻断**；先诊断失败/看本次证据，再提供普通新run动作，未来单独片，不降低状态门禁 |
| 监控/执行/活动必要导航及统一顶栏 | 原型index只有项目/配置；生产mainNav有console/workspace/exec/activity，不能替代新原型点击证据 | **未通过，唯一下一片WB05L2**；先补最小跨区模拟壳/项目与精确run来源返回，不深入正文 |

本轮主15组/46图/165键盘停靠/4下载，页面和console错误均零，网络仅原型同源静态资源。补核2个交付异常与1个failed动作层级；补核首轮selector误把.run-overview的后代.surface当本区，得到空集合，纠正为本区并断言两个实际primary后复跑，不拿空集合宣称通过。正常路径不写session/终态，不关门禁、不补证据记录；读取session只用于观察。“全键盘”限产品控件使用Tab/Enter/Space等真实按键；浏览器刷新/前后退使用Playwright reload/go_back/go_forward，不宣称实按Ctrl+R或Alt+方向键。

过程保留：主检查器第一轮误把带?from=history的精确来源URL与无query的原URL比较；第二轮误把“继续项目”的项目根投影当固定run URL。核当前消费者后只改检查器，失败日志/截图均保留，第三轮完整重跑通过；未让原型迎合断言。

证据仅本地dev_work/artifacts/wb05l1/（browser.json、supplement.json、46图及4文件）；失败轮wb05l1-attempt1/2/、supplement-attempt1保留；脚本dev_work/smokes/wb05l1_browser.py与wb05l1_supplement.py，白话报告dev_work/reports/wb05l1-review.md。没有重跑全部历史测试、无Python业务改动，未调用真实API/Provider/SSH。

**正式首迁交接保持候选，尚未准入**：沿§5唯一当前API主表，仅项目列表GET /api/workspaces只读投影；先逐字段证明目标、状态、更新时间/缺值，不把原型用run.createdAt兜底当项目更新时间。错误保旧/重试和迟到结果须真实浏览器验；GET可能同步持久投影，浏览器只读不等于服务完全无写入。创建/设置/运行继续由原生产消费者处理，保留项目/精确run导航，不复制fixture/revision/chat/推进核。替换后退出app.js::renderWorkspaces对应旧列表展示；workspace选择器/运行reader若仍有调用者保留并记录退出条件。不fallback模拟成功；Profile/步骤覆盖/聊天合同留各自写入前处理，不能并入首片。先解除上述两项设计阻断，再核准入；本片不执行接线。

**L1当时交接WB05L2，现已限定模拟验收见下文**。L1核证不预设整体设计完成，WB05/G40/G26/G27仍开放。

### WB05L2 最小跨区导航与返回上下文（2026-11-08，限定模拟验收）

基线1f5b8f6；本地只index/app/style/README及新增navigation.js，其他12份原型资产逐份SHA256相同，292生产源码/后端/规格/AGENTS未改。统一项目/监控/执行/活动/配置入口、当前区标识和顶栏；三区正文仅区域职责/演示范围及单一准确返回动作，不含示例GPU数值、运行灯或提交控制。

**组件与来源**：navigation.js是纯投影，显式接收projects/runs及既有聊天来源解析回调；同一context/carry供导航链接、配置目录和区域视图消费，无存储/请求/推进。from只承载原项目路由，不递归套区域；白名单校验query/编码、项目存在、run归属、step存在和Job的runId/stepId/step.jobId双向关系。历史名称取冻结snapshot，名称/编号/步骤名缺失明确未记录，不用当前数据填空。项目根保持项目投影，不提升为固定旧run。配置仍走原目录草稿/采用/返回规则；catalog无来源仅在原项目编辑上下文有效时复用既有返回，否则不猜项目。

app沿原go/popstate/approveLeave/positions，只装配纯投影；旧两入口nav-current判定退出，项目细分面包屑保留，新区域不维护业务状态。取消离开不改URL/来源/草稿；接受后按原规则明确放弃；整页跳转保留草稿，返回再继续编辑。全局无来源显示未关联项目；坏来源显示不可用与列表出口，不跳最新run。原生产mainNav与消费者仍保留，待正式迁移再退出。

| 本轮实际验收 | 证据与结果 | 限制 |
| --- | --- | --- |
| 四宽正常跨区/返回 | 1440/1024/768/390网页创建→显式模拟启动→日志→监控/执行/活动→配置四类别/连接编辑取消→准确日志；再步骤/报告跨区返回；29次Tab/Enter停靠outline及返回焦点、刷新/前后退，24主图且无横溢 | 不是全键盘完整闭环或无障碍认证；浏览器历史/刷新用Playwright方法 |
| 精确历史与两项目 | 两次网页启动，历史旧run含from=history连续跨区/目录刷新回来；第二项目由网页创建，项目根保持原根路由 | 导航前后完整projects/runs/chats、含报告与模拟事件逐值相同；不是自然并发或真实副作用证明 |
| 无来源/坏引用/草稿 | 三全局直接入口不猜项目；跨项目run、未知run/step/job、非法query/编码/嵌套区域/外部来源等12项经连续区域仍拒绝；脏稿取消/刷新/真实整页跳转保留→返回、明确接受放弃通过 | 主9组浏览器、零页面/console错误、请求仅同源静态资源；无session或终态注入 |
| 目录消费者新增query兼容 | 补核连接编辑保存→原项目明确采用保存、Agent脏指令→tools→原编辑→保存→项目采用再取消、流程详情编辑保存→原项目返回，旧run全对象均不变 | 这些是明确模拟配置写入，不把目录修改说成导航无副作用；未自动采用或保存项目 |
| 防御字段/关联 | 补核在真实UI输入的克隆对象中制造Job错run/step/反向引用三种异常，纯helper拒绝；删冻结标题/编号/步骤名显示未记录 | 只调用纯投影，不写session，非产品恢复证明；补核共4组（3网页目录链+1纯防御组） |
| 新helper启动故障 | 390浏览器abort navigation.js，原安全启动失败/重载入口仍在；移除故障，真实Enter触发document重载，原来源URL/完整业务session不变，2组/2图 | 显式静态资源故障注入，非真实服务断线；boot.js未改，零意外pageerror |
| 消融/回归 | 8网页输入×4宽32固定对照，创建第三步/项目列表/概览/设置/run/step/job/report主DOM及保存state新旧相同；创建20/run20/report26回归与14JS语法/9既有隔离契约通过 | 克隆仅固定输入对照，不当自然恢复/双击副作用比较；现生命周期回归单独保留，未重跑所有历史片 |

主代理实看execute1440、activity390长名称、returned-log768、invalid-origin四张本轮图，未声称26图逐张人工审查。小屏文字导航清楚，长来源换行且返回可达，正文不套多层抽屉/滚动。新增helper前置于app且required，14个脚本路径/顺序与原CSP保持；没有新依赖或技术栈替换，沿§8 frontend-design系统字体与克制排版规则。

过程：第一轮检查器误用完整localhost URL比较hash来源，第二轮把同文档hash goto当整页导航，被正常脏稿保护拒绝；保两轮失败，改检查器来源/用不同document query后完整通过。监督源码审查指出新helper旧快照名/缺字段及Job关联不够严格，已收紧并以最终主轮/专属补核验证；未放宽旧状态门禁/改业务内核或手填终态。旧failed双primary原文件未改，仍按L1挂账。

证据仅dev_work/artifacts/wb05l2/（browser/supplement/boot/comparison、回归结果、26图），白话报告dev_work/reports/wb05l2-review.md；前两失败轮wb05l2-attempt1/2保留。原型与测试结果不推送，正式仅三docs。导航设计阻断解除；L2当时交接WB05L3，现已限定模拟验收见下文；WB05/G40/G26/G27保持开放。其后按原要求/当前证据判收尾，不预排更多零散美化；真实列表仍仅接线候选，§5唯一API映射继续有效。

### WB05L3 失败页主操作层级（2026-11-08，限定模拟验收）

基线d61223c；本地仅run_views.js/README变，style和其他14资产逐份指纹相同，292生产源码/稳定规格/AGENTS不动。输入现run.status/plan/错误与当前项目newRunIssues；只读投影一处“查看失败步骤”primary。failed只find状态为failed的本次步骤，不沿等待/running猜诊断；缺记录明说不可用。错误全文与完整计划进度保留，普通新运行及原配置诊断移至诊断之后，复用done现run-next，不加通用动作框架/CSS/业务状态。

```text
本次运行 / 执行失败
失败步骤与完整原因 → 完整计划进度
[查看失败步骤]（唯一蓝色主操作）
分隔 → 当前项目的新运行诊断（如有）→ [开始新运行]（普通，原门禁）
步骤列表 → 独立步骤/日志阅读；不改执行失败/下游未执行事实
```

| 本轮实际验收 | 结果与证据 | 限制 |
| --- | --- | --- |
| 四宽失败主线与键盘 | 1440/1024/768/390网页新建长名/目标、配置后明确模拟启动，以原run-long动作返回失败；exit7、0/2及后步skipped、没有agent.started。primary只进入精确失败step，再实际Tab/Enter日志/返回，完整错误与退出证据保留，返回精确run及step焦点，刷新/前后退不改完整state | 主10组/16图/16键盘停靠，无页面横溢、page/console错误；场景重置/创建多用鼠标，非全键盘或真实用户研究 |
| 历史/后来配置失效/两项目 | history来源准确到旧run/step/log；当前项目路径改relative并保存后，新运行禁用且唯一设置诊断后置，但旧失败/log仍读；修复保存返回原run，只有明确点击才创建一个新run，新身份，原run全对象不变；旧run再点沿现active去重，第二项目来源不串 | 真实网页编辑的是相对路径，不是目录停用；没有真实目录检查/自动恢复，不把新run称原attempt重试 |
| 固定输入对照与消融 | 14网页输入×4宽56最终旧新比较：非failed/无run及step/job/report/navigation完整main/state相同；failed仅归一被移动new-run/readiness/run-next和主动作文字，原完整错误/进度/步骤/按钮属性/门禁及实际新run快照/步骤/事件/Job次数相同，旧runs逐值保留 | 新随机身份/时间不参与新run签名，克隆隔离输入不证明自然恢复或外部exactly-once；退出旧failed顶部primary，其他有消费者入口保留 |
| 只读防御 | 缺failed但有waiting、空plan、前有waiting Job的Agent失败、failed且child仍running、error空/null，共6纯视图补核；精确失败链接或明确不可用，错误转义/不编原因，输入不变 | 只克隆UI输入传纯view，不写session，不当实际Agent失败或损坏记录恢复 |
| 相关回归/语法 | run20、report26、nav9实际浏览器回归；14JS node检查、9既有隔离契约通过；15其他原型资产、292生产源码指纹相同，原脚本装配/CSP未变 | run回归只把failed主入口预期文案改为新名称，不改执行断言；未重跑所有历史片或无关Python业务测试 |

**早轮比较异常保留**：首轮1024 job主DOM不等，另一复核轮768 failed查询按钮为null，当时未存旧新差异DOM，不能证为产品bug，也不能武断归因harness。补差异/启动故障采集后两完整轮通过；最终另加原产品main启动完成条件（不以任意h1当就绪），56项通过，112次启动采样没有busy/failed；另对job与配置失效failed-invalid-current两输入在1024宽各20轮（40项）定向复查亦通过，未按原768 failed输入定向重现。原失败log保留，后续绿色不证明间歇边界已消除，交L4只读调查/收尾核查。没有改产品去迎合、注入终态或绕门禁；启动条件是观察现页面状态，不是人工补ready。

主代理实看failed1440/390、new-run-blocked768三图，监督另抽failed/log/blocked图；没有宣称逐图人工审查。长错误完整换行使页面变长，用户可阅读完整原因，不用高度阈值再造美化片。沿§8 frontend-design同指纹与Apache2指导，系统字体和原色彩/间距，未新增依赖或外部字体。

证据仅本地dev_work/artifacts/wb05l3/（browser/comparison/comparison-probe、syntax-contracts、三回归及16图），脚本dev_work/smokes/wb05l3_browser.py与wb05l3_compare.py；开片、白话结果在dev_work/reports/wb05l3-opening.md与wb05l3-review.md。仅三份正式docs推送，原型/测试/截图/结果不提交。L1两项明确设计阻断已有L2/L3限定验收；L3当时交接WB05L4只读收尾核验，现已完成见下文；L3本身不构成整体关闭声明，真实G40/G26/G27继续开放。

### WB05L4 原五目标收尾核验与正式首片交接（2026-11-08，只读完成）

基线b4cf18d。本片原型17资产、292生产源码、稳定规格和AGENTS逐份指纹不变，仅三docs；没有为收尾改页面/后端或降低原要求。依据原用户五片与原验收清单，核§1–5当前设计、§7原始源/证据和本轮真实浏览器点击。结论：**本轮需求/布局/独立可点击模拟原型阶段已限定完成**；不是正式前端迁移/整个产品完成，不关闭G40/G26/G27真实缺口。

| 原五目标 | 当前组件与实际证明 | 边界/结论 |
| --- | --- | --- |
| ①职责与字段审计 | §1–4职责/导航/状态与退出决定；§2及WB05A逐58控件、动态能力、16类50config按真实页面/renderer/consumer记录用途/来源/条件/默认/归属/联动/校验/保存影响及保留决定；WB01检查重核覆盖/链接/292台账 | 设计交付满足；高级字段已有归属/保真准入，不是本轮补全CRUD或删除旧数据 |
| ②入口与三步创建 | app.projectList/wizard/validate/saveProject/repair；当前四宽空列表→键盘三步创建，创建零run，明确下一动作；1440三缺项到唯一编辑/模拟检查返回原草稿，继续已有与网页第二项目 | 限定模拟满足；目录/主机/凭据虚构，不是实际连通性/文件检查 |
| ③运行与结果 | run_adapter唯一演示解释器，run_views只读，history_views交付唯一投影；当前四宽完整计划/等待刷新/本次Job日志/Agent步骤与按需对话/报告声明写入核验/历史，4个浏览器下载正文逐字等本次body；390六异常+L3四宽failed/exit7/skipped | 执行完成≠交付完整，停止后child独立，精确来源；满足模拟设计，不冒称真实外部执行、恢复或物理交付 |
| ④设置与配置中心 | app.settings/原草稿事务、connections/agents/tools/flows与显式覆盖；当前四宽设置/目录返回，1440未保存取消拒绝/刷新/明确放弃、改目标不改活动run与两项目隔离。沿L2原实际目录保存/采用/取消、Agent脏稿tools返回，相关helpers/app/index均与本轮同hash；L3九套当前契约及导航9回归，run_views唯一后改由L3/本轮主线验证 | 限定模拟满足；没有声称每个编辑器本轮重跑或真实写合同已接。重复入口/组件的退出或保留原因见§4及各片消融 |
| ⑤统一视觉与完整体验/下一正式片 | 当前1440/1024/768/390主15组/46图/185键盘停靠、跨三区/配置返回精确旧run；列表区域26组/29图；原系统字体/浅色/CSP/单主滚动与日志局部滚动保持，无成功/30秒顶栏块；§8来源/许可未变。§5唯一API映射及第三部分WB06A给实际消费者/字段/缺值/退出和验收 | 满足本轮模拟设计；不是全站无障碍认证、真实新手研究或正式页面迁移 |

**原验收场景与范围**：四宽完整正常产品路径在鼠标场景重置后使用实际Tab/Space/ArrowDown/Enter，不是evaluate.click；浏览器刷新/前后退用Playwright方法。1440实际缺模型→目录模拟凭据保存/明确采用、缺主机/目录→各自模拟检查→原草稿；未自动启动。1440草稿取消/刷新/放弃、两项目与旧run保真；390实际blocked零Job后显式满足同run、failed退出7不启动Agent、停止后child仍running直到自己返回才stopped、缺正文与核验不可用均实际查verification.status/body而非不存在字段。390长日志有独立局部滚动；长名/错误四宽沿L3、120段长报告沿L3当前report26回归，相关资产与本轮相同，不说本轮异常每格都四宽重验。配置目录全部编辑的原限定证据/字段保真继续按各片范围有效。

列表读取26组复核当前源码：四宽初读/空/失败/重试/保旧/键盘及长原因，较早响应不覆盖新值/离页/创建/reset/刷新；都是显式演示Promise，不是网络失联。启动恢复沿L2新helper静态资源abort→真实Enter document重载的2组证据，boot/index/app当前同hash；不是API/永久pending/HTML未到恢复。当前页面布局/标签/动作能由脚本直接定位完成任务，没有口头补救或手填终态；仍不把预知路线的脚本当真实陌生用户研究。

**L3早轮比较调查**：原1024 job与原768 failed精确输入，各12轮旧新=24对48页，完整HTML/state/URL/启动/错误/响应/源码指纹逐页保；本轮均相同，48初读已complete无busy/bootFailed，无page/request错误，只静态200。jobPage旧新函数hash完全相同。源码证实原任意h1也可匹配加载/启动错/业务render catch页面，后者不发pageerror，这是观察缺口；原失败未保存差异DOM，不能据此确定根因或声称消除。保留原失败和未归因风险，不凭未复现新造产品补丁/无限美化；本轮独立自然网页模拟主线与克隆对照严格分开。

**正式首片的复用纠正**：本轮静态核现loadStatus→applyStatusPayload→state.workspaces是列表来源，/api/status与GET /api/workspaces均调用workspace_public_payload。为同职责再加GET会造成双读取/潜在双写，下一片改为复用共享读者；这是据源码优化原候选，不是省略真实接线。workspace:false与resource-only不重绘列表、原列表唯一delete按钮/原确认、全局刷新可能采主机以及选择回填草稿的G27边界均已写入唯一WB06A计划。首片仅列表组件，创建/运行/设置和生产reader仍保留，不复制模拟状态机。

主代理实看waiting1440/settings1440/create390/report390四张当前图，监督另抽样含failed390，不声称75图全人工；长设置自然阅读，不因高度再加无依据美化。主脚本沿L1仅加强实际verification断言、跨区返回与failed单主操作；区域脚本复制时首次输出路径替换断言/缺文件exit2发生产品执行前，保setup说明，仅改目标路径后26组通过，产品/断言没有为通过改低。未调用真实API/Provider/SSH/GPU/Transfer，未读config/data密钥；Python业务未改，不跑无关业务smoke。

证据仅本地dev_work/artifacts/wb05l4/（browser/region-reading、75图、4下载）、wb05l4-investigation/（24对照/48页），原要求逐项表dev_work/reports/wb05l4-requirements.json、白话报告wb05l4-review.md与调查说明wb05l4-compare-investigation.md。原型入口http://127.0.0.1:8933/，启动命令仍在原型README，服务无需后端/真实凭据；原型/脚本/结果/图/本机配置不推送。

后置能力仍按§5及各字段归属保留：真实网络/SSE/Provider/SSH/GPU/Transfer/实物核验、复杂流程与高级编辑、完整证据导出/比较，以及全站无障碍/真实用户/跨标签耐久未因本轮完成而获得通过。**L4当时的下一片WB06A正式列表展示职责迁移，UI01已暂缓，尚未实施**；本轮前端设计目标可在独立终审与三docs提交推送核验后完成，不自动开始下一阶段。

### UI01 全产品总览与功能卡（2026-11-09，限定模拟验收）

范围与全产品字段/草图/现API及缺口见§0，不重复维护第二份工作台字段矩阵。独立入口http://127.0.0.1:8933/overview/，同8933本地静态服务；原工作台根入口继续可用。只新增三overview资产和原index/style/README最小接线，原领域/app/存储、292生产源码与稳定规格/AGENTS未变。旧三常规导航退出，hash兼容保留到逐区迁移核消费者；不存在第二事实投影或模拟流程核。

四宽1440/1024/768/390实际Tab/Enter与点击五卡/配置，主机→精确任务/日志、活动→精确传输/任务、前后退/刷新、返回卡片焦点通过；9检查组/25图。已有fixture项目正常UI启动模拟run/读精确日志→总览→浏览器返回，run不变；设置dirty→总览→Back，原草稿不误保存。前述仅同标签范围，不保证关闭标签或任意入口精确返回。未知记录有单一返回；受控overview.js资源失败保静态工作台/配置链接与刷新说明，四区卡片依赖脚本；显式浏览器刷新恢复。255请求均同源静态GET，唯一预期失败1次，无其他console/page/HTTP错误。源代码不做真实API或密钥读取。

过程：首次CSS箭头进入链接名已用aria-hidden修复；即时URL观察、dirty旧路由场景被保护阻止分别修检查器导航等待/独立页，门禁未动。另次跨文档等待得到空HTML，旧探针未等待导航事件，根因未证；补DOMContentLoaded同步/网络诊断后通过，不称修复产品根因。早日志/HTML保留，非重试到绿。390最初工作台卡偏高，实看后简用途文案/移动三步重复说明，重跑全片；最终主代理看总览1440/390、任务390、传输1440，监督另抽样，不说25图全人工。

证据dev_work/artifacts/ui01/browser.json、25图及原失败；脚本smokes/ui01_browser.py，报告reports/ui01-review.md只本地。沿§8同指纹/Apache-2.0设计指导，取层级和截图自审，不加外部字体/装饰动画/运行依赖。现仅完成全产品入口职责与整体规划，各区完整交互当时尚未交付；UI01当时交接UI02，卡片首页随后由下述UI02退出。WB06A暂缓，G41/G40/真实能力仍开放。

### UI02 默认监控首页与主机明细（2026-11-09，限定模拟验收）

需求校正、旧字段职责/消融、入口草图及API真实缺口唯一维护在§0。UI01历史点击通过保留，但用户否定其首页优先级；当前同http://127.0.0.1:8933/overview/直接进入监控。11组/22图/284静态GET、errors为空，四宽真实Tab/Enter和浏览器历史/刷新；首屏指标/首主机有bounding box，手机详细任务在下方、CPU内存在主机详情。主机GPU/进程/精确Job、传输异常/配置/工作台一键导航和同标签旧run/dirty草稿返回通过，无自动保存/推进。无真实API/采集/Provider/SSH或文件传输。

monitor.js统一演示定义+投影，overview.js装配/白名单路由，首页和任务/传输不重复硬编码事实；/monitor兼容同投影，坏记录不替换主机。首次读失败主机直链不展示fresh；刷新失败保相同主机/指标，重试首次失败仍无快照；无GPU/陈旧/未知有明确语义。初轮空白换行检查失败、监督发现门禁先后问题、长内容自审修正均保过程，修后11组整套复验。脚本受控中断只保工作台/配置跨文档链接和刷新提示，恢复后正常，未说所有导航无脚本可用。

原型三overview资产变并新增monitor.js，根index改返回文案、README更新；原业务JS/fixture/生产292/规格/AGENTS均未改。旧卡DOM/无消费者样式和旧monitor静态示例退出，旧工作台hash壳仍有来源消费者保留；未加入依赖/通用框架。主代理抽看monitor1440/390、host1440/390、long390，监督另看，不说22图全人工。证据dev_work/artifacts/ui02/及本地reports/ui02-review.md，原型/脚本/结果均不提交。当时交接UI03A，现已暂停；跨主机GPU表/温度/系统明细/筛选/停止/真实接线需求继续保留，G41未关闭，当前执行见§0与阶段计划。

## 8. 参考选择与复用边界

资料查阅日期：2026-11-07。只借鉴产品信息组织，不复制代码、不集成平台，不引入运行依赖；因此没有这些平台的数据迁移、授权或服务退出成本。

| 来源 | 采用 | 舍弃/边界 |
| --- | --- | --- |
| [Kestra UI](https://kestra.io/docs/ui) | 日常执行与资源管理分区 | 不搬其运维/企业配置和完整调度平台 |
| [Dify运行日志](https://docs.dify.ai/en/cloud/use-dify/monitor/logs) | 运行列表→结果→节点追踪；编辑测试与真实运行区分 | 不复制应用搭建器和全套模型服务 |
| [Langfuse观测概览](https://langfuse.com/docs/observability/overview) | 一次执行下分层查看时间、输入输出 | 不将观测层当工作流推进器，不引入追踪平台 |
| 本地frontend-design skill | 信息层级、任务优先、排版及截图自审 | 舍弃营销hero、装饰动画、外部字体及为风格堆组件 |

本地skill来源为`/home/hzj/.codex/skills/frontend-design/SKILL.md`，旁置LICENSE为Apache-2.0；无版本号，审查文本SHA256为`d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3`。此指纹仅识别本次本地指导文本，不声称与第三部分2.14的历史上游固定提交相同。不把开发skill当产品工具，也不引入脚本执行能力。
