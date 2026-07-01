---
name: web-accessibility
description: >-
  Use this skill for accessibility work: keyboard navigation, ARIA labels,
  semantic HTML, focus management, contrast, reduced motion, and screen reader
  compatibility.
work_modes: [coding]
---

# Web Accessibility

## 适用场景

可访问性工作：键盘导航、ARIA 标签、语义化 HTML、焦点管理、对比度、减少动画、屏幕阅读器兼容。

## 核心原则

1. **语义化 HTML 优先**：用 `<button>` 而非 `<div onClick>`，语义自带可访问性。
2. **键盘可达**：所有交互必须能用键盘操作（Tab/Enter/Esc/方向键）。
3. **ARIA 补充而非替代**：语义 HTML 不够时才用 ARIA，不要过度标注。
4. **可见焦点**：键盘聚焦时必须有视觉指示（outline）。
5. **不依赖颜色**：信息不只通过颜色传达，加图标/文字。

## 执行流程

### 1. 语义化结构
```html
<!-- ✅ 好 -->
<nav><ul><li><a href="/">首页</a></li></ul></nav>
<button onClick={save}>保存</button>

<!-- ❌ 差 -->
<div class="nav"><div class="item" onClick="go('/')">首页</div></div>
<div class="btn" onClick={save}>保存</div>
```

### 2. ARIA 标注
**何时需要 ARIA**
- 语义 HTML 无法表达时（如 tabs, accordion, dialog）
- 动态内容更新需要通知屏幕阅读器（aria-live）

**常用 ARIA**
| 属性 | 用途 |
|---|---|
| `aria-label` | 无文字元素的描述（图标按钮） |
| `aria-labelledby` | 引用其他元素作为标签 |
| `aria-describedby` | 引用描述元素 |
| `aria-expanded` | 展开/折叠状态 |
| `aria-hidden` | 对屏幕阅读器隐藏（装饰性元素） |
| `role` | 明确角色（dialog, alert, tab） |
| `aria-live="polite"` | 动态更新通知 |

### 3. 焦点管理
- **可见 outline**：不要 `outline: none` 不提供替代
- **模态框**：打开时聚焦内部第一个元素，关闭后恢复触发元素
- **跳转链接**：提供"跳到主内容"的快捷链接
- **焦点陷阱**：模态框内限制 Tab 不外溢

### 4. 键盘交互
| 组件 | 键盘操作 |
|---|---|
| 按钮/链接 | Enter / Space 激活 |
| 模态框 | Esc 关闭 |
| 标签页 | 方向键切换 |
| 下拉菜单 | 方向键导航，Enter 选择 |
| 表格 | Tab 逐个可交互元素 |

### 5. 对比度与视觉
- 文本对比度：普通文本 ≥ 4.5:1，大文本 ≥ 3:1（WCAG AA）
- 不只靠颜色传达信息：错误状态加图标 + 文字
- 支持减少动画：`@media (prefers-reduced-motion: reduce)`

### 6. 表单可访问性
- 每个 input 有关联的 `<label>`
- 错误信息用 `aria-describedby` 关联
- 必填字段用 `aria-required`

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找组件 | `find_files` | 定位 |
| 检查语义 | `read_file_lines` | 看 HTML 结构 |
| 编辑 | `apply_diff` | 加 ARIA/改语义 |
| 验证 | dev server + 键盘测试 | 确认可操作 |

## 检查清单

- [ ] 用语义化 HTML（button/nav/main/section）
- [ ] 所有交互键盘可达
- [ ] 焦点 outline 可见
- [ ] 图标按钮有 aria-label
- [ ] 动态组件有正确 ARIA（tabs/dialog 等）
- [ ] 表单 input 有关联 label
- [ ] 对比度达标（4.5:1）
- [ ] 支持减少动画

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| `<div onClick>` 当按钮 | `<button onClick>` |
| `outline: none` 无替代 | 保留或自定义可见 focus 样式 |
| 只用颜色表示错误 | 颜色 + 图标 + 文字 |
| 模态框无焦点管理 | 打开聚焦、关闭恢复 |
| 过度 ARIA 标注 | 语义 HTML 优先 |

## 输出要求

1. **可访问性问题**：发现的障碍清单
2. **修复内容**：语义化/ARIA/键盘/焦点的改动
3. **验证**：键盘操作流程 + 屏幕阅读器测试（如可行）
---
name: web-accessibility
description: >-
  Use this skill for accessibility work: keyboard navigation, ARIA labels,
  semantic HTML, focus management, contrast, reduced motion, and screen reader
  compatibility.
work_modes: [coding]
---

