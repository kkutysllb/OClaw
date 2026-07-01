---
name: using-superpowers
description: >-
  Use this meta-skill at the start of substantial Coding Agent work to decide
  which built-in Coding skills should guide the task. Trigger for multi-step
  changes, bug fixes, reviews, refactors, UI work, testing work, architecture
  changes, or whenever more than one engineering workflow might apply.
work_modes: [coding]
---

# Using Superpowers (Meta-Skill)

## 适用场景

这是元技能：在实质性编码任务开始时使用，判断哪些内置 Coding 技能应该指导当前任务。适用于多步骤变更、bug 修复、review、重构、UI 工作、测试工作、架构变更等可能涉及多个工作流的场景。

## 核心原则

1. **先选技能再动手**：明确任务类型，激活最匹配的技能组合。
2. **组合而非替代**：一个任务可能需要多个技能协作（如先 design 再 implement 再 test）。
3. **避免技能过载**：只激活真正相关的 2-3 个，不要全量加载。
4. **流程感**：按任务的自然阶段顺序激活技能。

## 技能选择决策

根据任务类型选择主导技能 + 辅助技能：

| 任务类型 | 主导技能 | 常见辅助 |
|---|---|---|
| 新功能实现 | `implement` | `test-driven-development`, `verification-before-completion` |
| Bug 修复 | `systematic-debugging` / `debug` | `patch-authoring`, `test-writer` |
| 代码重构 | `refactor` | `test-writer`（补安全网） |
| 代码审查 | `code-review` / `pr-review-advanced` | `diff-analysis` |
| 架构设计 | `architecture` / `technical-design` | `requirements-analysis` |
| 前端开发 | `react-nextjs` / `frontend-engineering` | `ui-polish`, `web-accessibility` |
| 后端 API | `api-design` / `fastapi-backend` | `test-writer`, `security-review` |
| 测试补充 | `test-writer` / `test-driven-development` | `qa-test-plan` |
| 安全加固 | `security-hardening` / `security-review` | — |
| 性能优化 | `performance` | `observability` |
| 数据库变更 | `database` | `migration` |
| 部署发布 | `deployment` / `release-engineering` | `ci-cd` |
| 项目从零开始 | `project-delivery-workflow` | `project-scaffolding` |
| 需求澄清 | `requirements-analysis` / `product-spec` | `acceptance-criteria` |
| 全栈垂直切片 | `vertical-slice-development` | `implement`, `test-writer` |

## 执行流程

### 1. 判断任务类型
- 读完用户请求，归类：实现 / 调试 / 重构 / 审查 / 设计 / 其他
- 评估复杂度：单文件小改 vs 跨模块大改

### 2. 选择技能组合
- 从决策表选主导技能
- 根据任务细节加 1-2 个辅助技能
- 如果任务跨多个阶段，按阶段规划技能

### 3. 按技能指导执行
- 遵循所选技能的流程和检查清单
- 阶段切换时自然过渡到下一个技能

### 4. 兜底：通用原则
如果任务不匹配任何专门技能，遵循通用 Coding 原则：
- 先理解再动手（`codebase-analysis`）
- 外科手术式编辑（`patch-authoring`）
- 改完必验证（`verification-before-completion`）
- 遵循项目约定（`codebase-analysis` 的约定识别）

## 检查清单

- [ ] 任务类型已判断
- [ ] 主导技能已选择
- [ ] 辅助技能按需激活
- [ ] 技能组合不过载（≤3 个）
- [ ] 遵循了所选技能的流程

## 输出要求

1. **任务归类**：这是什么类型的任务
2. **技能选择**：主导 + 辅助技能清单及理由
3. **执行计划**：按技能指导的阶段安排
