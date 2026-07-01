---
name: webapp-testing
description: >-
  Use this skill when verifying local web applications, frontend interactions,
  browser console errors, layout regressions, hydration errors, route behavior,
  and end-to-end UI workflows.
work_modes: [coding]
---

# Web Application Testing

## 适用场景

- 前端修改后需要验证页面是否正常渲染、交互是否正常
- 排查浏览器控制台错误、hydration 不匹配、路由跳转异常
- 验证响应式布局在不同视口下是否正确
- 端到端 UI 流程验证（登录 → 操作 → 结果确认）

## 核心原则

1. **先启动后验证**：确保 dev server 正常运行，再执行浏览器验证
2. **覆盖关键路径**：不只是"能打开"，要验证实际交互流程
3. **捕获证据**：截图 + console 日志 + 网络请求，形成可追溯的验证记录
4. **关注控制台**：黄色警告和红色错误都是回归信号
5. **多视口检查**：至少覆盖桌面和移动端两种宽度

## 执行流程

### 1. 准备环境

- 确认 dev server 正在运行（`npm run dev` / `pnpm dev`）
- 确认后端 API 可达（如需要）
- 记录测试 URL 和预期行为

### 2. 基础检查

| 检查项 | 方法 |
|-------|------|
| 页面加载 | 访问 URL，确认 HTTP 200，页面正常渲染 |
| 控制台错误 | 打开 DevTools Console，检查是否有红色错误 |
| Hydration | React/Next.js 项目检查是否有 hydration mismatch 警告 |
| 网络请求 | DevTools Network 面板，检查 API 请求状态码和响应 |
| 路由跳转 | 点击导航链接，确认 URL 变化和页面更新 |

### 3. 交互验证

按用户流程逐步验证：

```
1. 打开目标页面
2. 执行用户操作（点击/输入/提交）
3. 观察响应（UI 变化/错误提示/加载状态）
4. 验证结果（数据正确/状态更新/跳转正确）
5. 截图记录
```

### 4. 视口响应式

- 桌面宽度（1280px+）：布局完整，无溢出
- 平板宽度（768px）：布局适配，导航可用
- 移动端宽度（375px）：内容可读，触摸目标 ≥ 44px

### 5. 异常场景

- 空数据状态：列表为空时显示占位
- 加载状态：骨架屏/Spinner 正常显示
- 错误状态：API 返回错误时显示友好的错误提示
- 表单验证：必填项/格式校验/提交后反馈

### 6. 记录结果

- 每个检查点标注 ✅ 通过 / ❌ 失败
- 失败项附带截图和错误描述
- 提供修复建议

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash（启动 dev server） | `npm run dev` / `pnpm dev` |
| 浏览器/Playwright | 页面访问、截图、交互验证 |
| `read_file` | 查看组件源码，定位问题 |
| `apply_diff` / `multi_edit` | 修复发现的问题 |

## 检查清单

- [ ] 页面正常加载（HTTP 200，无白屏）
- [ ] 控制台无红色错误
- [ ] 无 React hydration 警告
- [ ] 核心 API 请求返回正确状态码
- [ ] 关键交互流程可用（点击/输入/提交）
- [ ] 响应式布局在桌面和移动端正常
- [ ] 空状态/加载状态/错误状态正确显示
- [ ] 截图已保存作为验证证据

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 只看"页面能打开"就认为没问题 | 执行实际交互流程，检查控制台和网络请求 |
| 忽略 console warning | 每个 warning 都可能是潜在问题 |
| 只测桌面宽度 | 至少覆盖桌面 + 移动端 |
| 不截图 | 每个关键状态截图留证 |
| 修改后不重新验证 | 每次修改后重新走验证流程 |

## 输出要求

1. 列出验证的环境信息（URL、浏览器、视口宽度）
2. 逐项报告检查结果（✅/❌）
3. 对失败项提供截图和错误描述
4. 给出修复方案并应用
5. 修复后重新验证并确认通过
---
name: webapp-testing
description: >-
  Use this skill when verifying local web applications, frontend interactions,
  browser console errors, layout regressions, hydration errors, route behavior,
  and end-to-end UI workflows.
work_modes: [coding]
---

