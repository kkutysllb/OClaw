---
name: react-nextjs
description: >-
  Use this skill for React and Next.js coding: client/server component
  boundaries, hooks, hydration, routing, data fetching, query invalidation,
  layouts, and component composition.
work_modes: [coding]
---

# React & Next.js

## 适用场景

React 和 Next.js 编码：客户端/服务端组件边界、Hooks、水合（hydration）、路由、数据获取、查询失效、布局、组件组合。

## 核心原则

1. **App Router 优先**：Next.js 13+ 用 `app/` 目录，server component 默认。
2. **组件边界清晰**：server component（默认）vs client component（`"use client"`），按需标记。
3. **数据获取在服务端**：能用 server component 获取的就别在 client fetch。
4. **Hooks 规则**：只在顶层调用，不在循环/条件/嵌套函数中调用。
5. **状态最小化**：能从 URL/props 派生的不要存 state。

## 执行流程

### 1. 确认项目结构
- `find_files "**/app/**"` 确认是 App Router 还是 Pages Router
- 读 `next.config.js` 了解配置（特别是 Turbopack/webpack 选择）
- 检查 `package.json` 的 Next/React 版本

### 2. 组件设计
**Server Component（默认）**
- 数据获取、静态渲染、不需要交互
- 不能用 useState/useEffect/事件处理

**Client Component（`"use client"`）**
- 交互（onClick, onChange）、状态、生命周期、浏览器 API
- 尽量下沉到叶子组件，保持父组件为 server component

### 3. 数据获取与缓存
- **Server Component**：直接 `await fetch()` 或调用 service
- **Client Component**：用 SWR / React Query / TanStack Query
- **Next.js fetch**：默认有缓存，按需配置 `{ cache: 'no-store' }` 或 `next: { revalidate: 60 }`

### 4. 查询失效（Cache Invalidation）
- mutation 后用 `router.refresh()` 或 `queryClient.invalidateQueries()`
- 避免手动管理缓存，依赖框架的失效机制

### 5. 路由与布局
- App Router：文件即路由（`app/users/page.tsx` → `/users`）
- `layout.tsx`：共享布局，嵌套生效
- `loading.tsx` / `error.tsx`：加载和错误状态
- 动态路由：`[id]/page.tsx`

### 6. 常见陷阱处理
- **Hydration mismatch**：服务端和客户端渲染不一致 → 避免在渲染中用 Date.now()/Math.random()/window
- **"use client" 漏标**：用了 hooks 但没标 → 加 `"use client"`
- **Turbopack 兼容性**：Next.js 16+ 默认 Turbopack，部分 webpack 配置不兼容 → 必要时显式指定 webpack

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找组件 | `find_files "**/*.tsx"` | 定位组件文件 |
| 读组件 | `read_file_lines` | 理解现有实现 |
| 搜索 hook 用法 | `search_code "use client"` | 确认边界 |
| 编辑组件 | `apply_diff` / `multi_edit` | 精准修改 |
| 验证 | `run_tests` + dev server | 确认渲染正确 |

## 检查清单

- [ ] server/client component 边界正确
- [ ] 数据获取在合适的层（优先 server）
- [ ] client component 用了 `"use client"`
- [ ] 无 hydration mismatch 风险
- [ ] 状态最小化（能派生的不存）
- [ ] mutation 后正确失效缓存
- [ ] 组件可复用、props 清晰

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 整页 `"use client"` | 交互部分下沉为 client 叶子组件 |
| client 组件里 fetch | server component 获取，props 传递 |
| useEffect 做派生计算 | 直接在渲染中计算 |
| useState 存可派生值 | 从 props/URL 派生 |
| 忽略 hydration 一致性 | 保证服务端客户端渲染一致 |
| 手动管理 React Query 缓存 | 用 invalidateQueries |

## 输出要求

1. **组件设计**：server/client 划分及理由
2. **数据流**：获取→传递→展示的路径
3. **状态管理**：哪些是 state，哪些可派生
4. **变更说明**：改了哪些组件、为什么
5. **验证**：渲染结果 + 交互测试
---
name: react-nextjs
description: >-
  Use this skill for React and Next.js coding: client/server component
  boundaries, hooks, hydration, routing, data fetching, query invalidation,
  layouts, and component composition.
work_modes: [coding]
---

