---
name: pr-review-advanced
description: >-
  Use this skill for PR-level review that needs merge-base context, multiple
  commits, commit intent, aggregate diff, risk grouping, review decision, and
  findings across the full branch.
work_modes: [coding]
---

# Advanced PR Review

## 适用场景

- 需要对完整分支/PR 进行深度审查（不只是单个 commit）
- 需要理解多个 commit 的整体意图和演进逻辑
- 需要按风险等级分组输出审查发现
- 需要给出明确的 Review 决策（Approve / Request Changes / Block）

## 核心原则

1. **整体视角**：审查的是整个分支的累积变更，不是孤立的单个 commit
2. **意图理解**：先理解"为什么改"，再评判"改得对不对"
3. **风险驱动**：按风险等级排序发现，优先报告 Critical/High
4. **建设性反馈**：不只是指出问题，还要提供修复方向
5. **决策明确**：审查结论必须是明确的 Approve / Request Changes / Block

## 执行流程

### 1. 收集分支上下文

```bash
# 找到 merge-base（与主分支的分叉点）
git merge-base HEAD main

# 查看所有 commit 及消息
git log --oneline merge-base..HEAD

# 查看完整累积 diff
git diff merge-base...HEAD

# 按文件查看变更统计
git diff --stat merge-base...HEAD
```

### 2. 理解 commit 意图

- 阅读 commit message 理解每个 commit 的目的
- 理解 commit 的演进逻辑（为什么这个顺序）
- 识别是否包含 WIP/revert/实验性 commit（需要 squash 的信号）

### 3. 审查维度

| 维度 | 审查内容 |
|------|---------|
| **正确性** | 逻辑是否正确？边界条件是否处理？是否有竞态条件？ |
| **安全性** | 是否引入安全漏洞？输入是否验证？权限是否校验？ |
| **性能** | 是否有 N+1 查询？是否有内存泄漏？是否有不必要的循环？ |
| **可维护性** | 代码是否清晰？命名是否合理？是否过度工程？ |
| **测试** | 是否有测试覆盖？测试是否有意义？是否覆盖边界？ |
| **兼容性** | 是否破坏现有 API？数据库 schema 变更是否向后兼容？ |
| **一致性** | 是否遵循项目代码规范？风格是否一致？ |

### 4. 风险分级

| 级别 | 定义 | 示例 | 处理方式 |
|------|------|------|---------|
| **Critical** | 会导致数据丢失/安全漏洞/崩溃 | SQL 注入、删除未备份的数据 | 🔴 Block — 必须修复 |
| **High** | 功能错误/性能严重退化 | 逻辑错误、N+1 查询 1000+ 条 | 🟠 Request Changes |
| **Medium** | 代码质量/可维护性问题 | 缺少错误处理、命名不清晰 | 🟡 建议修复 |
| **Low** | 风格/偏好/微优化 | 变量名可更好、注释可补充 | 🟢 可选 |

### 5. 输出审查报告

```
## PR Review: [分支名]

### 总览
- Commits: N 个
- 变更文件: M 个（+X / -Y 行）
- 整体意图: [一句话总结]

### Review 决策: 🟠 Request Changes

### 发现

#### Critical (必须修复)
1. [文件:行号] [描述] → [修复建议]

#### High (建议修复)
2. [文件:行号] [描述] → [修复建议]

#### Medium (可选改进)
3. [文件:行号] [描述]

#### Low (参考)
4. [风格建议]

### 亮点
- [做得好的地方，鼓励性反馈]
```

### 6. 跨 commit 检查

- 检查是否有 commit 引入然后又回退的代码（浪费 review 时间）
- 检查最终状态是否自洽（中间 commit 可以乱，最终状态必须干净）
- 检查是否有遗漏的调试代码（console.log / print / debugger）

## 工具优先级

| 工具 | 用途 |
|------|------|
| `git_log` / `git_diff` | 查看 commit 历史和累积 diff |
| `read_file` | 深入阅读被修改文件的完整上下文 |
| `find_symbols` / `find_references` | 理解变更的影响范围 |
| `run_tests` | 验证测试是否通过 |
| `run_linter` | 检查代码规范 |

## 检查清单

- [ ] 查看了 merge-base 以来的完整累积 diff
- [ ] 理解了每个 commit 的意图和顺序
- [ ] 审查了正确性（逻辑/边界/并发）
- [ ] 审查了安全性（输入验证/权限/密钥）
- [ ] 审查了性能（查询/内存/循环）
- [ ] 审查了测试覆盖（新增代码是否有测试）
- [ ] 检查了向后兼容性（API/schema 变更）
- [ ] 按风险等级分组输出了发现
- [ ] 给出了明确的 Review 决策

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 只看最后一个 commit | 查看 merge-base 以来的累积 diff |
| 不理解意图就开始挑错 | 先理解"为什么改"再评判 |
| 所有问题混在一起 | 按风险等级分组（Critical/High/Medium/Low） |
| 不给决策 | 明确 Approve / Request Changes / Block |
| 只批评不肯定 | 同时指出做得好的地方 |
| 逐行 nitpick Low 级问题 | 聚焦 Critical 和 High |

## 输出要求

1. 提供 PR 总览（commit 数、变更文件数、整体意图）
2. 按风险等级分组列出所有发现
3. 每个发现附带文件路径、行号、问题描述和修复建议
4. 给出明确的 Review 决策
5. 列出 PR 亮点（建设性反馈）
---
name: pr-review-advanced
description: >-
  Use this skill for PR-level review that needs merge-base context, multiple
  commits, commit intent, aggregate diff, risk grouping, review decision, and
  findings across the full branch.
work_modes: [coding]
---

