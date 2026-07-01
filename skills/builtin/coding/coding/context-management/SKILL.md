---
name: context-management
description: >-
  Use this skill when managing Coding Agent context, long sessions, compressed
  state, project boundaries, task memory, active skills, or preventing unrelated
  context from influencing code changes.
work_modes: [coding]
---

# Context Management

## 适用场景

- 长会话中上下文窗口接近上限，需要压缩或清理
- 多个 skill 同时激活，需要管理优先级
- 任务中途切换，需要保存和恢复上下文
- 防止无关信息干扰当前代码修改决策

## 核心原则

1. **相关性优先**：上下文中只保留与当前任务直接相关的信息
2. **渐进压缩**：长会话定期压缩历史，保留关键决策和状态
3. **结构化状态**：任务状态用结构化格式保存，便于恢复
4. **最小加载**：按需加载信息，不一次性加载所有上下文
5. **边界清晰**：明确当前任务的范围，拒绝范围外的请求

## 执行流程

### 1. 上下文优先级管理

```
上下文窗口内容优先级（从高到低）：

P0 - 必须保留：
├── 当前用户指令
├── 当前任务的目标和约束
└── 正在修改的文件内容

P1 - 尽量保留：
├── 项目编码规范
├── 当前 skill 的 instructions
└── 关键设计决策

P2 - 可以压缩：
├── 已完成的步骤历史
├── 早期探索性搜索结果
└── 已应用过的工具输出

P3 - 可以丢弃：
├── 与当前任务无关的信息
├── 过时的搜索结果
└── 已提交的 diff 详情
```

### 2. 长会话压缩策略

当上下文接近上限时：

```
压缩步骤：
1. 保留最近 3-5 轮对话的完整内容
2. 将早期对话压缩为摘要：
   "之前完成了：分析了项目架构，修改了 auth.py 和 user.py，
    通过了所有测试，用户确认进入下一阶段。"
3. 保留关键文件路径和变更记录
4. 丢弃中间探索性的搜索结果
5. 保留当前任务的核心约束和目标
```

### 3. 任务状态保存与恢复

```python
# 任务状态结构化保存
task_state = {
    "task_id": "impl-auth-module",
    "phase": "implementation",  # exploration/planning/implementation/verification
    "goal": "实现 JWT 认证模块",
    "constraints": [
        "不使用第三方 auth 库",
        "支持 refresh token",
        "兼容现有 session 系统"
    ],
    "completed_steps": [
        "分析了现有 auth 代码",
        "设计了 JWT 工具类",
        "实现了 token 生成和验证"
    ],
    "current_step": "编写认证中间件",
    "pending_steps": [
        "编写认证中间件",
        "添加 API 端点保护",
        "编写测试"
    ],
    "modified_files": [
        "backend/app/core/security.py",
        "backend/app/gateway/middleware/auth.py"
    ],
    "decisions": [
        {"decision": "使用 HS256 算法", "reason": "项目规模不需要 RS256"},
    ]
}
```

### 4. 多 Skill 管理

当多个 skill 同时激活时：

```
Skill 优先级规则：
1. 安全相关 skill（security-review/hardening）最高优先
2. 与用户直接请求匹配的 skill 次之
3. 通用工程实践 skill（code-review/verification）再次
4. 辅助性 skill（docs/handoff）最低

冲突处理：
- 如果两个 skill 的指令冲突，以更具体的 skill 为准
- 如果安全 skill 与其他 skill 冲突，以安全 skill 为准
- 如果不确定，向用户确认
```

### 5. 防止上下文污染

| 风险 | 预防 |
|------|------|
| 旧任务的文件路径被误用于新任务 | 每个任务重新确认文件路径 |
| 探索阶段的临时结论被当作最终决策 | 标注"待验证"的结论 |
| 其他项目的代码风格影响当前项目 | 只加载当前项目的编码规范 |
| 会话历史的错误信息被信任 | 以代码实际内容为准，不信历史中的描述 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 按需加载文件内容，不预加载 |
| SearchMemory | 按需搜索记忆 |
| `grep` | 精确搜索而非全文加载 |
| TodoWrite | 追踪任务状态和进度 |

## 检查清单

- [ ] 上下文中只有当前任务相关的信息
- [ ] 长会话定期压缩历史
- [ ] 任务状态结构化保存
- [ ] 文件路径经过当前任务验证
- [ ] Skill 指令冲突有明确的优先级规则
- [ ] 无过时或无关的信息残留

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 一次性加载所有文件 | 按需加载当前需要的 |
| 保留所有历史对话 | 定期压缩为摘要 |
| 混合多个任务的上下文 | 每个任务独立上下文 |
| 不保存任务状态 | 结构化保存便于恢复 |
| 信任历史中的描述 | 以实际代码为准 |

## 输出要求

1. 确认当前任务的上下文范围
2. 只加载和保留相关信息
3. 长会话定期压缩
4. 任务状态可保存和恢复
5. 标注信息的来源和时效性
---
name: context-management
description: >-
  Use this skill when managing Coding Agent context, long sessions, compressed
  state, project boundaries, task memory, active skills, or preventing unrelated
  context from influencing code changes.
work_modes: [coding]
---

