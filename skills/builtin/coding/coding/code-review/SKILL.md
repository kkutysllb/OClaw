---
name: code-review
description: >-
  Use this skill when the user asks to review code, check for issues, audit
  quality, or inspect changes. Trigger on requests like "review this code",
  "check this PR", "what's wrong with this code", "audit this change",
  "review my diff", "is this code good", or when the user shares a diff or
  pull request for feedback. Also trigger for security review requests.
work_modes: [coding]
---

# Code Review

## 适用场景

审查代码变更、PR、diff 或既有代码的质量。输出结构化的分级 issue 清单和明确结论。

## 核心原则

1. **基于变更而非全量**：聚焦 diff 中的实际改动，不审查未触碰的旧代码（除非有严重隐患）。
2. **分级输出**：issue 按严重程度分级，让作者知道哪些必须改。
3. **给可执行建议**：每个 issue 附带具体修复方向或代码示例，而非泛泛批评。
4. **区分品味与正确性**：must-fix 是正确性问题，nit 是风格偏好，不要混淆。
5. **赞扬好的实践**：发现优秀设计时明确指出，鼓励正向反馈。

## 执行流程

### 1. 获取变更上下文
- `git_diff` 获取工作区改动，或 `git_show <commit>` 查看特定提交
- `git_log --oneline -10` 了解变更历史和 commit 规范
- `read_file_lines` 读取被改文件的完整上下文（不只看 diff hunk）
- 理解这次变更的业务目标（从 commit message / PR 描述 / 用户说明）

### 2. 分维度审查

**正确性（Correctness）— must-fix 候选**
- 逻辑错误：边界条件、off-by-one、空值未处理
- 并发问题：竞态、死锁、共享状态
- 资源泄漏：未关闭的文件/连接/锁
- 错误处理：吞异常、错误的恢复逻辑
- 数据一致性：事务边界、部分失败

**安全性（Security）— must-fix 候选**
- 输入验证：SQL 注入、XSS、路径穿越、命令注入
- 认证授权：权限绕过、越权访问
- 密钥泄露：硬编码 token、日志中的敏感信息
- 依赖风险：已知漏洞的包版本

**设计（Design）— should-fix 候选**
- 单一职责：类/函数是否承担过多
- 抽象层次：是否混用了不同层级的逻辑
- 耦合度：是否引入了不必要的依赖
- 扩展性：新增同类需求是否需要改动现有代码

**可维护性（Maintainability）— should-fix/nit**
- 命名：是否准确表达意图
- 复杂度：圈复杂度是否过高
- 重复：是否有可提取的公共逻辑
- 注释：是否解释了"为什么"而非"是什么"

**测试（Tests）— should-fix 候选**
- 覆盖率：新增逻辑是否有测试
- 边界用例：是否覆盖了空值、极值、异常路径
- 测试质量：是否真正验证行为而非只是跑通

### 3. 形成结论
给出明确的 review 决策：
- **Approve**：可以直接合并，无 must-fix
- **Request changes**：有 must-fix issue，必须修改后重新 review
- **Block**：存在严重设计缺陷或安全风险，需要讨论方案

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 获取改动 | `git_diff` / `git_show` | 查看 diff |
| 读完整文件 | `read_file_lines` | 理解上下文 |
| 搜索调用方 | `search_code` | 评估影响范围 |
| 交互式审查 | `review_code` | 结构化 review |

## 检查清单

- [ ] 已读取所有变更文件的上下文（非仅 diff hunk）
- [ ] 正确性维度已逐项检查
- [ ] 安全性维度已逐项检查
- [ ] 每个 issue 都有具体建议或代码示例
- [ ] issue 已按严重程度分级
- [ ] 给出了明确的 approve / request changes / block 结论

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 审查全量代码含未改动部分 | 聚焦 diff 中的实际变更 |
| 只批评不给方案 | 每个 issue 附修复建议 |
| 风格偏好当 must-fix | 区分 nit 和 must-fix |
| 没有明确结论 | 给 approve / request changes / block |
| 忽略测试覆盖 | 检查新增逻辑是否有测试 |
| 忽略 commit message 质量 | 检查是否符合 Conventional Commits |

## 输出要求

使用以下结构化格式：

```
## Review 结论：[Approve / Request changes / Block]

### Must-fix（必须修改）
1. **[文件:行号] 问题标题**
   - 问题：具体描述
   - 建议：修复方向或代码示例

### Should-fix（建议修改）
...

### Nit（可选优化）
...

### 亮点
- 值得肯定的设计或实践
```
