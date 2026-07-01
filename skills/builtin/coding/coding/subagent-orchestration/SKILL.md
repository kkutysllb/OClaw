---
name: subagent-orchestration
description: >-
  Use this skill when a coding task has multiple independent workstreams that
  can be researched, reviewed, or implemented in parallel without shared writes.
work_modes: [coding]
---

# Subagent Orchestration

## 适用场景

- 任务包含多个独立的工作流，可以并行推进
- 需要同时研究多个方向（如同时分析前端和后端代码）
- 需要 Code Review 和测试并行进行
- 大型任务需要拆分为子任务分配给多个 agent

## 核心原则

1. **独立性**：子任务之间没有写依赖（不修改同一文件）
2. **并行化**：独立任务同时执行，最大化效率
3. **明确边界**：每个子 agent 有清晰的输入、输出和范围
4. **结果聚合**：主 agent 负责收集和整合子 agent 的结果
5. **错误隔离**：一个子 agent 失败不影响其他子 agent

## 执行流程

### 1. 评估并行性

```
任务是否可以并行？
- ✅ 可以：子任务 A 修改前端，子任务 B 修改后端（无写冲突）
- ✅ 可以：子任务 A 做代码审查，子任务 B 做安全审查
- ❌ 不行：子任务 A 修改文件 X，子任务 B 也修改文件 X（写冲突）
- ❌ 不行：子任务 B 依赖子任务 A 的输出（串行依赖）
```

### 2. 任务拆分

```python
# 主 agent 拆分任务
subtasks = [
    {
        "id": "research-frontend",
        "type": "research",  # research/review/implement
        "scope": "frontend/src/components/",
        "goal": "分析前端组件结构和状态管理",
        "constraints": "只读取，不修改文件",
        "expected_output": "组件依赖关系图和状态流分析"
    },
    {
        "id": "research-backend",
        "type": "research",
        "scope": "backend/app/",
        "goal": "分析后端 API 结构和数据流",
        "constraints": "只读取，不修改文件",
        "expected_output": "API 端点清单和数据模型分析"
    },
    {
        "id": "security-review",
        "type": "review",
        "scope": "全部代码",
        "goal": "安全审查",
        "constraints": "只审查，不修改",
        "expected_output": "安全发现列表（按严重程度排序）"
    }
]
```

### 3. 分配子 Agent

```
主 Agent：
├── 子 Agent A (research-frontend) → 并行
├── 子 Agent B (research-backend)  → 并行
└── 子 Agent C (security-review)   → 并行

所有子 agent 同时执行，主 agent 等待全部完成。
```

### 4. 子 Agent 任务规范

每个子 agent 的 prompt 应包含：

```
任务描述：[具体目标]
工作范围：[限定目录/文件]
约束条件：[只读/可写/不可越界]
预期输出：[结构化的输出格式]
完成条件：[明确的完成标准]
```

### 5. 结果聚合

```python
# 主 agent 收集所有子 agent 的结果
results = {
    "research-frontend": {
        "status": "completed",
        "findings": "前端使用 Zustand 状态管理，有 23 个组件...",
        "files_analyzed": 23,
    },
    "research-backend": {
        "status": "completed",
        "findings": "后端有 45 个 API 端点，使用 FastAPI...",
        "files_analyzed": 45,
    },
    "security-review": {
        "status": "completed",
        "findings": "发现 2 个 High、3 个 Medium 安全问题...",
        "critical_count": 0,
    }
}

# 整合为统一报告
report = generate_unified_report(results)
```

### 6. 错误处理

| 场景 | 处理 |
|------|------|
| 子 agent 超时 | 标记超时，主 agent 使用部分结果 |
| 子 agent 失败 | 记录失败原因，不影响其他子 agent |
| 子 agent 结果冲突 | 主 agent 仲裁，选择更合理的 |
| 子 agent 超出范围 | 主 agent 修正范围后重新分配 |

## 适用场景示例

### 场景 1：并行研究

```
任务：全面分析项目架构

拆分：
- Agent A：分析前端架构（组件、路由、状态）
- Agent B：分析后端架构（路由、服务、数据模型）
- Agent C：分析 DevOps 配置（CI/CD、Docker、部署）

并行执行后，主 agent 整合为完整的架构分析报告。
```

### 场景 2：并行审查

```
任务：对 PR 进行全面审查

拆分：
- Agent A：代码质量审查（命名、结构、可维护性）
- Agent B：安全审查（输入验证、权限、密钥）
- Agent C：性能审查（查询效率、内存、缓存）

并行执行后，主 agent 合并为统一的审查报告。
```

### 场景 3：并行实现（谨慎）

```
任务：同时实现前端和后端功能

拆分（前提：无文件写冲突）：
- Agent A：实现前端组件（frontend/src/）
- Agent B：实现后端 API（backend/app/）

⚠️ 注意：必须有明确的文件边界，否则会冲突。
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| Task（子 agent） | 启动并行子 agent |
| `read_file` / `grep` | 主 agent 整合结果 |
| `write_file` | 主 agent 输出统一报告 |

## 检查清单

- [ ] 子任务之间无写依赖
- [ ] 每个子 agent 有明确的范围和约束
- [ ] 子 agent 的输出格式结构化
- [ ] 主 agent 负责结果聚合
- [ ] 有错误处理策略（超时/失败）
- [ ] 并行任务数合理（不过多）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 并行修改同一文件 | 确保写操作不冲突 |
| 子 agent 范围模糊 | 明确文件和目录边界 |
| 不等待子 agent 完成 | 主 agent 等待全部完成再聚合 |
| 一个失败全部失败 | 错误隔离，部分结果也可用 |
| 过度并行化 | 只在真正独立时才并行 |

## 输出要求

1. 评估任务的并行可行性
2. 拆分为独立的子任务
3. 分配子 agent 并行执行
4. 收集并整合所有子 agent 的结果
5. 输出统一的报告或实现
---
name: subagent-orchestration
description: >-
  Use this skill when a coding task has multiple independent workstreams that
  can be researched, reviewed, or implemented in parallel without shared writes.
work_modes: [coding]
---

