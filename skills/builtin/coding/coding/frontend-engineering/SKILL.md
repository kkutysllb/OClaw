---
name: frontend-engineering
description: >-
  Use this skill for React, Next.js, state management, data fetching, component
  behavior, hydration bugs, routing, forms, and frontend integration work.
work_modes: [coding]
---

# Frontend Engineering

## 适用场景

React/Next.js 通用前端工程：状态管理、数据获取、组件行为、hydration 问题、路由、表单、前端集成。

## 核心原则

1. **组件单一职责**：一个组件只做一件事（展示 OR 逻辑 OR 布局）。
2. **状态分层**：UI 状态（组件内）、共享状态（全局）、服务端状态（缓存）。
3. **单向数据流**：数据从父到子，事件从子到父。
4. **组合优于继承**：用 props 组合，不用继承扩展。
5. **可访问性内置**：写组件时就考虑 a11y，而非事后补。

## 执行流程

### 1. 组件设计
- 划分展示组件（纯 UI）和容器组件（逻辑）
- 识别可复用部分，提取为独立组件
- 定义清晰的 props 接口

### 2. 状态管理策略
| 状态类型 | 推荐方案 |
|---|---|
| 组件内 UI 状态 | useState / useReducer |
| 跨组件共享 | Context / Zustand / Redux |
| 服务端数据 | React Query / SWR |
| URL 状态 | useSearchParams / router |
| 表单状态 | react-hook-form / 受控组件 |

### 3. 数据获取
- **优先 server component**（Next.js）：直接 await
- **client 端**：React Query 管理加载/错误/缓存状态
- **避免**：useEffect + useState 手动 fetch（除非简单场景）

### 4. 表单处理
- 用 react-hook-form 管理表单状态和校验
- 用 zod / yup 定义 schema
- 提交后正确处理 loading / success / error 状态

### 5. 路由
- App Router：文件即路由
- 动态路由 `[param]`，catch-all `[...slug]`
- 编程导航用 `useRouter().push()`

### 6. 常见问题处理
- **Hydration mismatch**：检查服务端/客户端渲染一致性，避免时间/随机数/window
- **无限渲染**：检查 useEffect 依赖数组
- **props 钻取**：用 Context 或状态库
- **性能**：React.memo / useMemo / useCallback 按需使用

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找组件 | `find_files "**/*.tsx"` | 定位 |
| 读组件 | `read_file_lines` | 理解 |
| 搜索用法 | `search_code "useState"` | 找模式 |
| 编辑 | `apply_diff` / `multi_edit` | 修改 |
| 验证 | dev server + `run_tests` | 确认 |

## 检查清单

- [ ] 组件职责单一
- [ ] 状态分层合理（不过度全局化）
- [ ] 数据流单向清晰
- [ ] 表单有校验和状态处理
- [ ] 无 hydration 风险
- [ ] 无无限渲染循环
- [ ] 可访问性已考虑
- [ ] 组件可复用

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 巨型组件做所有事 | 拆分为职责单一的组件 |
| 所有状态都全局 | 分层管理，局部优先 |
| useEffect 派生数据 | 渲染时直接计算 |
| 手动 fetch + useEffect | 用 React Query / SWR |
| props 钻取 5 层 | 用 Context |
| 滥用 useMemo/useCallback | 按需使用，先测后优化 |

## 输出要求

1. **组件设计**：划分及职责
2. **状态方案**：各状态的管理方式
3. **数据流**：获取→状态→展示
4. **变更说明**：改了什么、为什么
5. **验证**：渲染 + 交互测试
---
name: frontend-engineering
description: >-
  Use this skill for React, Next.js, state management, data fetching, component
  behavior, hydration bugs, routing, forms, and frontend integration work.
work_modes: [coding]
---

