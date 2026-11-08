# 工作台信息架构与交互设计

设计版本：WB01；更新于2026-11-08。状态：WB01职责与字段设计已建立；WB02创建及WB03A运行过程、WB03B历史/报告及WB04A项目资料环境设置、WB04B1模型连接目录、WB04B2既有步骤模型覆盖、WB04C1 Agent基本目录/绑定、WB04C2工具授权/只读目录、WB04D1流程目录/创建往返、WB04D2流程基本编辑/引用保真及WB04E按需Agent辅助对话独立模拟原型已验收；WB05A整体需求/体验证据总核、WB05B1设置分区与唯一诊断、WB05B2创建第三步信息减负、WB05C1日志阅读/精确返回及WB05C2本次报告正文下载/缺失反馈已完成，WB05D1短时通知归属/跨页清理及WB05D2辅助对话失败阅读/重试入口已限定模拟验收，WB05E1已有项目未知流程的资料保存边界已限定模拟验收，WB05E2缺流程身份记录的只读引用防御已限定模拟验收，WB05F1已有运行页的新运行就绪反馈已限定模拟验收，WB05F2无运行准备概览的未确认配置呈现已限定模拟验收，WB05G1准备概览长文本阅读与主操作可达性、WB05G2运行概览提交快照的长标题阅读及WB05H1运行历史最小检索已限定模拟验收，WB05I1首次静态加载与启动失败恢复已限定模拟验收，WB05J1已完成运行的主操作层级已限定模拟验收，唯一下一片WB05K1原型剩余需求与正式接线交接审计，WB05整体体验及正式接线尚未交付，高级节点编辑按实际需求另片，正式页面未迁移。本文是[稳定规格](project-spec.md)的界面设计附件，不是第四份产品状态台账；实际问题和完成状态仍由[当前审查](current-audit.md)及[下一阶段计划](next-stage-plan.md)维护。

## 1. 要让用户完成什么

第一次使用的人能完成：创建项目 → 补齐必要配置 → 启动运行 → 看懂等待/失败 → 获取结果。页面靠名称、布局、字段提示和明确动作指路，不常驻操作手册。先做好完整设计，再按小片验证独立模拟原型；不修改后端，不替换正式页面。

用户已确定：工作台完整闭环、明亮克制、三步创建、对话按需打开。监控/执行/活动仅统一导航与顶栏，不深入改版。Python 3.10兼容暂缓。面向用户称“项目”，实现仍使用workspace_id；项目、模板、一次run、一次attempt、子Job是不同对象，不能改成一张含混的“任务”。

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
全局导航：项目 / 配置中心  （监控、执行、活动保留原入口）
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
| 项目列表/继续；projects[id,name,goal,lastRun,updatedAt] | GET /api/workspaces → {workspaces}；GET /api/workspaces/{id} → {workspace} | state/workspaces/crud.py::list_workspaces、state/monitoring.py::workspace_public_payload。现app.js::loadStatus从状态快照读workspaces并装配renderWorkspaces | **可复用+前置设计**：不是GET /api/execution-overview（后者是跨执行列表）。现列表返回完整公开workspace及派生runs/automation，没有独立轻量列表schema；先只投影所需字段，不为美化立刻新造列表服务。updated_at、inputs目标、最新run取值须按公开字段核，不能照搬原型lastRun文案或用运行创建时间冒充项目更新时间。WB05K2已补限定模拟区域读取；真实列表字段/更新时间与网络仍须接线验收。 |
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

**当前是五大目标的最后一项未收尾，不是所有高级字段、全部后端或任意流程都要在WB05实现。** §2的58控件逐项决定及§7 WB05A的16类/50节点配置保真矩阵继续有效：未展示≠删除，语义不明不合并。原六类页面“项目列表、创建、项目运行、运行详情、项目设置、配置中心”已有模拟入口；区域读取已由K2限定模拟验证，真实读取仍待接线。

- **列表读取设计点已补，限定模拟**：WB05K2已实际验证首次加载、成功空列表、首次失败重试、已有数据刷新失败保旧、旧响应不覆盖较新读取或离开后的页面。正常不占顶栏，手动完成Promise，不用动画假造运行。真实网络取新数据/断线/超时仍待正式接入，不把一个列表区域推广为全站通过。
- **脏稿按现有两种行为验收，不把所有页面改成一种弹窗**：站内离开编辑确认放弃；刷新/整页打开仍可恢复同实体未保存草稿，保存前不得写入项目/目录。已有A/B/C/D/E的限定模拟证据和WB05A整页无确认但保草稿证据可用；没有全站beforeunload承诺。存储失败有错误但跨标签页/关标签后恢复未验，不承诺耐久。最终闭环须检查“继续编辑/放弃/刷新/换项目”各自实际路径，不因缺整页弹窗就预排新功能。
- **高级项已有归属，逐个正式接入时保真**：基本项目设置只留常用值；命令/env管理器/调度/标签/独立idea与notes进项目设置的独立高级编辑，提示词/预算/输出约束归Agent编辑，节点config/输入映射归流程专门编辑，内部ID/幂等键归诊断。没有编辑能力时不放空按钮，保留旧生产专门入口与数据；新只读页不发保存，未来基本保存必须以未编辑字段往返测试作为准入，不为50项补通用CRUD。
- **导航与额外能力分类**：监控/执行/活动页不深入改版，正式首迁片只同步必要进入/返回入口并携带项目/精确run上下文，不把它们复制进演示站；当前没有模拟跨区可点击证据，正式接线验收必须保留此项。完整证据导出/比较、更多筛选、下载极长错误精简是可后置体验/独立职责；长名称能换行不等于全站简洁或真实新手已通过。非当前职责不得假链接或在失败时回落演示数据。
- **WB05关闭还须最终核证**：当前唯一下一WB05L1按原始要求复查创建→补配置→明确模拟启动→等待/失败→报告与已有项目继续，核四宽、键盘、来源返回、隔离与草稿；沿既有证据补缺格而非重跑所有历史脚本。更新本表和正式首片计划，才能判定设计阶段是否完成。K1/K2没有关闭WB05/G40/G26/G27，L1或正式迁移均未执行；不得把待核证写成已通过。

**正式迁移的最小首个职责候选是项目列表只读展示，不是同时接完整闭环。** 准入：上述列表读取体验已验；明确workspace公开字段映射、真实错误/缺值与更新时间；一条唯一列表装配路径，不复制模拟state/runs。该片仅让用户读到真实项目、明确跳回已有生产入口继续，创建/运行/设置仍用原入口；不在正式页挂仍会写fixture的“创建/开始运行”。替换后删除相应旧列表展示，既有选择器若另有消费者列明保留与退出条件；真实浏览器验空/错误/过期响应、精确项目返回与后退/刷新后才通过。不需先补聊天/Profile版本等独立合同，但未满足K2和最终设计核证前不开始接线。

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
| WB05L1 | 原始闭环最终核证、收尾结论与正式首片交接 | 新功能/批量修复、真实接线、重审全部后端 | 唯一下一片，未实施 |
| WB05后续 | 按职责精简视觉、补全链浏览器验收、正式迁移单片计划 | 一次迁移整站或批量实现后端 | 当前仅选定WB05L1最终核证；其余依据§5结论确定范围 |

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

**唯一下一片WB05L1：原始闭环最终核证与正式首片交接（只验收）**。依据§5收尾条件与原用户五项目标，核已有证据/实际网站完整路径，判断设计阶段能否关闭；保留模拟/真实边界、未验格与独立后置项，不边验边批量补功能，不直接接真实后端。本轮未执行L1。

## 8. 参考选择与复用边界

资料查阅日期：2026-11-07。只借鉴产品信息组织，不复制代码、不集成平台，不引入运行依赖；因此没有这些平台的数据迁移、授权或服务退出成本。

| 来源 | 采用 | 舍弃/边界 |
| --- | --- | --- |
| [Kestra UI](https://kestra.io/docs/ui) | 日常执行与资源管理分区 | 不搬其运维/企业配置和完整调度平台 |
| [Dify运行日志](https://docs.dify.ai/en/cloud/use-dify/monitor/logs) | 运行列表→结果→节点追踪；编辑测试与真实运行区分 | 不复制应用搭建器和全套模型服务 |
| [Langfuse观测概览](https://langfuse.com/docs/observability/overview) | 一次执行下分层查看时间、输入输出 | 不将观测层当工作流推进器，不引入追踪平台 |
| 本地frontend-design skill | 信息层级、任务优先、排版及截图自审 | 舍弃营销hero、装饰动画、外部字体及为风格堆组件 |

本地skill来源为`/home/hzj/.codex/skills/frontend-design/SKILL.md`，旁置LICENSE为Apache-2.0；无版本号，审查文本SHA256为`d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3`。此指纹仅识别本次本地指导文本，不声称与第三部分2.14的历史上游固定提交相同。不把开发skill当产品工具，也不引入脚本执行能力。
