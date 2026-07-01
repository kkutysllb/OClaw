---
name: playwright-verification
description: >-
  Use this skill when verifying frontend changes with Playwright-style browser
  automation, screenshots, console logs, network requests, interactions, and
  responsive viewport checks.
work_modes: [coding]
---

# Playwright Verification

## 适用场景

- 前端代码修改后需要自动化浏览器验证
- 需要截图对比、控制台日志采集、网络请求监控
- 验证多视口响应式布局（桌面/平板/移动）
- 验证用户交互流程（点击、输入、导航、表单提交）

## 核心原则

1. **确定性优先**：测试步骤可重复执行，结果一致
2. **等待策略**：用 Playwright 的自动等待（waitForSelector/waitForResponse），不用固定 sleep
3. **断言明确**：每个步骤有明确预期，不靠目测
4. **隔离执行**：每次测试从干净状态开始，不依赖前序测试副作用
5. **证据完备**：截图 + trace + console 日志 + 网络请求，失败时可追溯

## 执行流程

### 1. 准备

- 确认 dev server 运行中
- 确认 Playwright 已安装（`npx playwright install`）
- 准备测试 URL 和预期行为清单

### 2. 编写验证脚本

```typescript
// 基本结构
import { test, expect } from '@playwright/test';

test('feature works correctly', async ({ page }) => {
  // 1. 导航到目标页面
  await page.goto('http://localhost:3000/target');

  // 2. 采集控制台错误
  const consoleErrors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  // 3. 采集网络请求失败
  const networkFailures: string[] = [];
  page.on('requestfailed', req => networkFailures.push(req.url()));

  // 4. 执行交互
  await page.click('button[data-testid="submit"]');
  await expect(page.locator('.success')).toBeVisible();

  // 5. 断言无错误
  expect(consoleErrors).toEqual([]);
  expect(networkFailures).toEqual([]);

  // 6. 截图
  await page.screenshot({ path: 'screenshots/feature-verified.png' });
});
```

### 3. 多视口验证

```typescript
const viewports = [
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 667 },
];

for (const vp of viewports) {
  test(`layout correct at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto(url);
    await page.screenshot({ path: `screenshots/${vp.name}.png` });
  });
}
```

### 4. 关键验证点

| 验证类别 | 具体内容 |
|---------|---------|
| **渲染** | 页面可见、布局无溢出、字体/颜色正确 |
| **交互** | 按钮/链接可点击、表单可提交、导航正常 |
| **数据** | API 请求成功、数据正确渲染、分页/筛选工作 |
| **控制台** | 无红色错误、无 React hydration 警告 |
| **网络** | API 请求返回 2xx、无 CORS 错误、无 404 资源 |
| **响应式** | 多视口下布局正确、导航可用、文字可读 |

### 5. 执行与报告

- 运行测试：`npx playwright test --reporter=html`
- 查看报告：`npx playwright show-report`
- 失败时查看 trace：`npx playwright show-trace trace.zip`

### 6. 持久化

- 将验证脚本保存到 `tests/e2e/` 目录
- 截图保存到 `screenshots/` 目录
- 可加入 CI 流水线

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash | 安装 Playwright、运行测试、查看报告 |
| `write_file` / `apply_diff` | 编写/修改测试脚本 |
| `read_file` | 查看被测组件源码、分析失败原因 |
| `apply_diff` / `multi_edit` | 修复发现的问题 |

## 检查清单

- [ ] 测试脚本覆盖目标功能的核心流程
- [ ] 使用 data-testid 定位元素（不依赖 CSS class）
- [ ] 采集了控制台错误和网络失败
- [ ] 至少覆盖桌面 + 移动两种视口
- [ ] 截图已保存
- [ ] 测试通过（exit code 0）
- [ ] 无控制台红色错误
- [ ] 无网络请求失败

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| `page.waitForTimeout(5000)` | `await expect(locator).toBeVisible()` |
| 用 CSS class 定位元素 | 用 `data-testid` |
| 只测一种视口 | 至少桌面 + 移动 |
| 忽略控制台错误 | 采集并断言无错误 |
| 测试间共享状态 | 每个 test 独立 |
| 不截图 | 关键步骤截图留证 |

## 输出要求

1. 提供可执行的 Playwright 测试脚本
2. 报告测试执行结果（通过/失败 + 原因）
3. 附带截图路径
4. 对失败项给出修复方案
5. 修复后重新执行并确认通过
---
name: playwright-verification
description: >-
  Use this skill when verifying frontend changes with Playwright-style browser
  automation, screenshots, console logs, network requests, interactions, and
  responsive viewport checks.
work_modes: [coding]
---

