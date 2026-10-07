# AEGIS

**Agent Engineering Governance & Integration System**

通过 GitHub Issue 串起多 Agent 软件开发：人提出需求，Agent 按角色认领、设计、开发、独立审查、测试和交付。
跨电脑共享状态，不绑定模型或 Agent 厂商；项目定位是工作流 Skill。

## 给 Agent 的启动指令

```text
读取这个仓库的 skills/aegis-develop/SKILL.md 并执行。
目标项目：https://github.com/OWNER/PROJECT
角色：developer
身份：agent-dev-01（可选；省略时自动生成并保存）
按目标项目配置处理一个符合条件的任务，完成后给出证据或可恢复的阻塞说明。
允许在目标项目认领 Issue、推送任务分支、创建 PR、发表工作流证据。
```

角色可用 `planner`、`developer`、`reviewer`、`qa`；第一次使用先要求 Agent
“按该 Skill 初始化目标项目”。如果目标就是当前目录，可从核实后的 Git remote 推断。
只有 Skill 地址、没有目标项目时，Agent 会询问目标，避免误改 Skill 自身。

## 身份和不同 Agent 的例子

`hermes-laptop-01` 原本只是示例实例名，不是 Hermes 配置，也不是 GitHub 账号。
身份只用于区分认领者、续约和追踪作者；不决定角色、模型或权限。可自由命名，
例如 `agent-dev-01`。省略时，Agent 生成并持久化一个 `agent-<UUID>`。
同一工作实例恢复时沿用身份，并行实例不能共用身份；改名或换模型不构成独立审查。

下面是可互换的分工例子，不要求某个工具固定承担某种角色：

| Agent | 角色例子 | 直接读取 | 实例 ID 例子 |
|---|---|---|---|
| Codex | planner | `skills/aegis-plan/SKILL.md` | `codex-desktop-01` |
| ZCode | developer | `skills/aegis-develop/SKILL.md` | `zcode-workstation-01` |
| Claude | reviewer | `skills/aegis-review/SKILL.md` | `claude-review-01` |
| Hermes | qa | `skills/aegis-qa/SKILL.md` | `hermes-server-01` |

例如给 Claude：

```text
按这个工作流仓库的 skills/aegis-review/SKILL.md 执行。
目标项目：https://github.com/OWNER/PROJECT
角色：reviewer
身份：claude-review-01
独立审查一个符合条件的设计或 PR，允许在目标项目认领及发表审查证据。
```

也可以让 Codex 开发、ZCode 测试、Claude 设计或 Hermes 审查，只需改为相应角色
Skill。角色职责和项目权限保持一致；这些是调用示例，不表示已在所有宿主实测。

## 按角色加载

- [aegis-init](skills/aegis-init/SKILL.md)：初始化项目。
- [aegis-plan](skills/aegis-plan/SKILL.md)：需求整理和设计。
- [aegis-develop](skills/aegis-develop/SKILL.md)：实现及 PR 交付。
- [aegis-review](skills/aegis-review/SKILL.md)：独立设计/代码审查。
- [aegis-qa](skills/aegis-qa/SKILL.md)：串行集成测试和合入把关。

已知角色时直接读该 Skill，只加载共享执行规则与本角色说明。初始化、故障恢复按需读。
原来的 [统一入口](skills/aegis/SKILL.md) 保留为轻量路由。
共享核心保存唯一一份 CLI 和模板。安装时需要“角色目录＋共享核心目录”，
不能只复制单个角色的 SKILL.md；见[安装结构](skills/aegis/references/packaging.md)。

## 已实现

- Feature、Bug、Improvement 表单：背景/收益或复现/预期，优先级及验收条件。
- 非覆盖式项目初始化，保留原文档和 AGENTS.md。
- `gh` + Python 标准库 CLI：注册、扫描、认领、续约、状态交接、释放。
- GitHub 状态文件版本校验，角色状态机、认领 token、仓库级 QA 串行占用。
- 独立设计/代码审查、具体提交的证据绑定、返工与故障恢复说明。
- 无任务先退出，由 Hermes 等宿主定时调度；脚本不调用模型。

[初始化说明](skills/aegis/references/setup.md) ·
[角色职责](skills/aegis/references/roles.md) ·
[操作与恢复](skills/aegis/references/operations.md) ·
[验证边界](docs/validation.md)

自动合入必须配置并验证 GitHub merge queue、required checks 和独立审查规则。
默认人工合入；发布/部署按目标项目授权单独执行。失效锁需确认旧进程停止后恢复，
不会自动抢锁。首次使用应跑真实沙箱 Issue，当前离线验证不等于线上验收。

## 角色操作与固定交付格式

每个角色目录现在包含 `references/runbook.md`（输入、步骤、产物、下一状态）、
`assets/report.md`（必填报告模板）和 `examples/`（填好示例）。执行角色另有
`assets/evidence.json`，用于将已发布报告交给状态 CLI；初始化没有 Issue 状态交接。

从[Coder 操作手册](skills/aegis-develop/references/runbook.md)开始看：明确只认领
`ready` Issue，读取获批设计和返工记录，再实现、验证、更新文档、交付 PR，最后
转交 `code-review`。报告逐项保留 AC 编号、测试结果、日志、文档修改及未完成项。
[Coder 完整示例](skills/aegis-develop/examples/report.md)展示实际应填写的形态。

模板格式是 Agent 的交付要求；当前 CLI 校验状态和提交身份，不自动判定报告的
语义真实性。示例 URL、提交 SHA 和测试结果均为虚构，不可当作执行证据。

## 在 Issue 中查看进度

状态变化会自动同步为 `aegis:new`、`aegis:ready`、`aegis:blocked` 等标签，并发表
包含原因和证据链接的状态评论。可用 `label:aegis:blocked` 筛选阻塞任务。
原有业务标签会保留；手工改状态标签不会更改权威任务状态。

若输出 `sync.status: pending`，状态已提交，但展示同步尚未完成。使用
`aegis.py --repo OWNER/REPO sync --issue N` 修复，不要重做开发或重复 finish。
详见[同步与恢复](skills/aegis/references/issue-visibility.md)。

## 确定性执行与验证

现在可执行配置预检、可信 Issue 准入、依赖/返工预算、证据格式和设计摘要校验、
精确候选的 CI/审查检查，以及受服务端规则约束的合并队列入队。
使用 [单次宿主运行器](skills/aegis/references/policy-and-runner.md) 对接本地 Agent CLI，
运行器负责单任务、锁、超时、续约和日志；不内置模型或常驻调度器。
离线通过不等于 GitHub 账户权限、真实模型调用或线上交付通过，见 [验证记录](docs/validation.md)。
