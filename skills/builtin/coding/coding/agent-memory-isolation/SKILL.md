---
name: agent-memory-isolation
description: >-
  Use this skill when Coding Agent memory, session state, project state, or
  task history must be isolated from other OClaw tasks, global memory, or
  unrelated conversations.
work_modes: [coding]
---

# Agent Memory Isolation

## 适用场景

- Coding Agent 需要与全局记忆/其他任务的记忆隔离
- 多项目并行时，每个项目的上下文不能互相污染
- 需要确保任务状态、代码变更历史、决策记录的隔离
- 防止不相关的对话上下文影响代码修改

## 核心原则

1. **项目边界**：每个项目的记忆、状态、历史严格隔离
2. **任务隔离**：不同任务的任务状态互不干扰
3. **最小暴露**：只加载当前任务相关的上下文，不加载无关记忆
4. **显式共享**：跨项目/跨任务的信息共享必须显式声明
5. **可清理**：任务完成后可清理临时记忆，保留持久化结论

## 执行流程

### 1. 理解 OClaw 记忆体系

```
OClaw 记忆层次：
├── 全局记忆（Global Memory）
│   ├── 用户偏好（user_info / user_hobby / user_behavior）
│   └── 通用知识（跨项目复用）
├── 项目记忆（Project Memory）
│   ├── 项目架构（project_introduction）
│   ├── 技术栈（project_tech_stack）
│   ├── 编码规范（development_code_specification）
│   └── 经验教训（lessons_learned）
├── 任务记忆（Task Memory）
│   ├── 任务状态（当前进度、已完成步骤）
│   ├── 代码变更历史（修改了哪些文件）
│   └── 决策记录（为什么这样实现）
└── 会话记忆（Session Memory）
    ├── 对话历史
    └── 临时上下文
```

### 2. 隔离策略

#### 项目级隔离

```python
# 每个项目使用独立的记忆命名空间
memory_namespace = f"project:{project_id}"

# 只加载当前项目的记忆
project_memories = search_memory(
    namespace=memory_namespace,
    query="architecture and conventions"
)

# 不加载其他项目的记忆（默认行为）
```

#### 任务级隔离

```python
# 每个任务有独立的 session 和 state
task_context = {
    "task_id": task_id,
    "project_id": project_id,
    "work_mode": "coding",
    "session_id": session_id,
    "modified_files": [],  # 只追踪当前任务修改的文件
    "decisions": [],       # 只记录当前任务的决策
}
```

### 3. 防止上下文污染

| 污染场景 | 预防措施 |
|---------|---------|
| 项目 A 的架构知识影响项目 B 的决策 | 使用项目命名空间隔离记忆 |
| 任务 1 的修改历史干扰任务 2 的 diff | 每个任务独立的变更追踪 |
| 旧任务的临时上下文干扰新任务 | 任务结束后清理临时记忆 |
| 全局偏好覆盖项目特定规范 | 项目记忆优先级高于全局 |

### 4. 记忆加载策略

```
任务启动时的记忆加载顺序：
1. 加载项目级记忆（架构、技术栈、规范）
2. 加载当前任务的历史状态（如恢复中断的任务）
3. 不加载其他项目的记忆
4. 不加载其他任务的状态

上下文窗口优先级：
1. 当前任务指令（最高优先级）
2. 项目编码规范
3. 项目架构概览
4. 全局用户偏好（最低优先级）
```

### 5. 安全边界检查

- 修改文件前确认：文件是否属于当前项目范围？
- 应用记忆中的规范时确认：规范是否来自当前项目？
- 使用历史决策时确认：决策是否来自当前任务？

## 工具优先级

| 工具 | 用途 |
|------|------|
| SearchMemory | 在正确的命名空间中搜索记忆 |
| `read_file` | 读取当前项目文件 |
| `git_status` / `git_diff` | 确认当前修改范围 |

## 检查清单

- [ ] 当前任务的项目边界已确认
- [ ] 只加载了当前项目的记忆
- [ ] 不引用其他项目的架构/规范
- [ ] 任务状态独立追踪
- [ ] 文件修改限定在项目范围内
- [ ] 临时上下文在任务结束后可清理

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 加载所有项目的记忆 | 只加载当前项目的 |
| 跨项目引用架构决策 | 使用项目命名空间隔离 |
| 任务间共享修改状态 | 每个任务独立的变更追踪 |
| 混淆全局偏好和项目规范 | 项目规范优先于全局偏好 |

## 输出要求

1. 确认当前任务的项目边界和记忆范围
2. 只在正确的命名空间内操作记忆
3. 标注记忆来源（哪个项目/哪个任务）
4. 任务完成后标注可清理的临时记忆
---
name: agent-memory-isolation
description: >-
  Use this skill when Coding Agent memory, session state, project state, or
  task history must be isolated from other OClaw tasks, global memory, or
  unrelated conversations.
work_modes: [coding]
---

