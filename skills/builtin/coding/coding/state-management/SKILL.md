---
name: state-management
description: >-
  Use this skill for frontend or backend state design, query caches, mutation
  invalidation, session state, optimistic updates, task state, and stale data.
work_modes: [coding]
---

# State Management

## 适用场景

前端或后端的状态设计：查询缓存、mutation 失效、会话状态、乐观更新、任务状态、陈旧数据处理。

## 核心原则

1. **状态分层**：UI 状态（局部）vs 共享状态（全局）vs 服务端状态（缓存）。
2. **最小化状态**：能从其他状态/props/URL 派生的不要单独存。
3. **单一数据源**：同一数据只存一处，其他地方引用。
4. **不可变更新**：状态更新返回新对象，不就地修改。
5. **失效优于同步**：mutation 后失效缓存重新获取，比手动同步更可靠。

## 状态分类与方案

| 状态类型 | 特征 | 推荐方案 |
|---|---|---|
| 组件内 UI 状态 | 只当前组件用 | useState / useReducer |
| 表单状态 | 临时、需校验 | react-hook-form |
| URL 状态 | 可分享/书签 | useSearchParams / router |
| 跨组件共享 | 多组件读写 | Context / Zustand |
| 服务端数据 | 来自 API、需缓存 | React Query / SWR |
| 实时状态 | WebSocket 推送 | 订阅 + 本地缓存 |

## 执行流程

### 1. 识别状态
- 列出所有需要存储的数据
- 分类：UI / 共享 / 服务端 / URL

### 2. 选择方案
- 局部优先：能局部就不全局
- 服务端数据用 React Query，不用全局 store

### 3. 定义状态结构
```typescript
// Zustand 示例
interface AppStore {
  user: User | null;
  theme: "light" | "dark";
  setUser: (user: User | null) => void;
  toggleTheme: () => void;
}
```

### 4. mutation 与失效
```typescript
const mutation = useMutation({
  mutationFn: updateUser,
  onSuccess: () => {
    // 失效相关查询，触发重新获取
    queryClient.invalidateQueries({ queryKey: ["user", userId] });
  },
});
```

### 5. 乐观更新（可选）
```typescript
const mutation = useMutation({
  mutationFn: updateUser,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: ["user"] });
    const prev = queryClient.getQueryData(["user"]);
    queryClient.setQueryData(["user"], newData);  // 乐观更新
    return { prev };
  },
  onError: (_err, _newData, context) => {
    queryClient.setQueryData(["user"], context?.prev);  // 回滚
  },
});
```

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找现有状态 | `search_code "useState\|useStore\|create("` | 了解方案 |
| 读 store | `read_file_lines` | 理解结构 |
| 编辑 | `apply_diff` | 修改 |

## 检查清单

- [ ] 状态分层合理（局部优先）
- [ ] 无冗余状态（派生的不存）
- [ ] 服务端数据用缓存方案
- [ ] mutation 后正确失效
- [ ] 乐观更新有回滚机制
- [ ] 不可变更新（不就地改）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 所有状态塞全局 store | 局部优先，按需提升 |
| 存可派生的状态 | 渲染时派生 |
| mutation 后手动同步 | 失效缓存重新获取 |
| 就地修改状态对象 | 返回新对象 |
| 多处存同一数据 | 单一数据源 |

## 输出要求

1. **状态清单**：分类（UI/共享/服务端/URL）
2. **方案选择**：每个状态的管理方式
3. **数据流**：获取→存储→更新→失效
4. **乐观更新策略**（如适用）
5. **变更说明**
---
name: state-management
description: >-
  Use this skill for frontend or backend state design, query caches, mutation
  invalidation, session state, optimistic updates, task state, and stale data.
work_modes: [coding]
---

