# RelayGraph 开发文档

项目目标：把 GPU 监控、远程任务、文件传输和 Agent 工作流串成可执行、可追溯的研究工作台。

正式开发文档只维护三个部分，按顺序阅读：

| 文档 | 回答的问题 | 更新方式 |
| --- | --- | --- |
| [第一部分：目标、需求与核心契约](project-spec.md) | 项目最终做什么；组件接收什么、如何处理、输出什么；失败如何处理 | 稳定基线，日常只小修；改变语义须说明影响与迁移 |
| [第二部分：现状与逐文件审查](current-audit.md) | 当前代码离目标差什么；能力缺口、冗余、伪成功与风险在哪里 | 随实际代码维护，包含 285 个正式代码文件和本地验证边界说明 |
| [第三部分：下一阶段实施计划](next-stage-plan.md) | 先解决哪个功能点；复用什么；如何小步实现、验收与删除旧路径 | 每轮只执行一个切片，验收后更新状态 |

开发约束集中在根目录 [AGENTS.md](../AGENTS.md)，启动与配置说明见 [README](../README.md)。

## 旧文档归并

2026-10-11 完成归并，删除以下重复的正式文件，不保留内容相同的跳转壳：

| 旧文件 | 内容去向 |
| --- | --- |
| features.md、architecture.md | 第一部分的功能需求、组件和边界；实际差距进第二部分 |
| development-guide.md、testing.md | AGENTS.md 的实现/验证规则；第一部分的部署要求；第三部分的测试收敛 |
| development-stage.md、review-status.md | 第二部分的当前事实；第三部分的切片状态与质量门槛 |
| development-roadmap.md | 第三部分的优先级、技术评估和开发切片 |
| 本地 current-implementation.md、future-roadmap.md、current-limitations.md | 有效需求与未完成项进入三部分，旧阶段状态/过期路径/历史 agent id 退役 |

旧正式版本可从 Git 历史找回。本地复现报告和 smoke 证据仍可留在 dev_work/，但不是当前产品规范或完成证明。正式文档不存放个人配置、Provider 密钥、真实日志或私有主机资料。
