---
name: ui-polish
description: >-
  Use this skill for focused UI refinement: layout density, spacing, responsive
  states, button placement, toolbars, tabs, empty states, and visual consistency.
work_modes: [coding]
---

# UI Polish

## 适用场景

聚焦的 UI 打磨：布局密度、间距、响应式状态、按钮放置、工具栏、标签页、空状态、视觉一致性。

## 核心原则

1. **一致性优先**：同类元素用同样的间距、颜色、圆角、字号。
2. **间距有体系**：用设计 token（4px/8px/16px/24px），不写魔法数字。
3. **响应式默认**：移动优先，从小屏往大屏增强。
4. **状态完整**：每个交互元素都有 default/hover/active/focus/disabled 状态。
5. **空状态不是空白**：列表为空、加载中、出错时都要有明确的视觉反馈。

## 执行流程

### 1. 审查现状
- 启动 dev server，截图当前状态
- 识别不一致：间距、颜色、字号、圆角、按钮样式
- 检查响应式：手机/平板/桌面三档

### 2. 间距与密度
- 统一用 spacing token：`gap-2`（8px）/ `gap-4`（16px）/ `gap-6`（24px）
- 信息密度：列表/表格紧凑，详情页宽松
- 对齐：网格对齐，不手动调像素

### 3. 交互状态
每个可交互元素检查：
- default：默认外观
- hover：鼠标悬停（颜色加深/边框/阴影）
- active：按下（缩小/颜色更深）
- focus：键盘聚焦（outline 环，可访问性必需）
- disabled：禁用（降低透明度 + cursor-not-allowed）

### 4. 空状态与反馈
| 状态 | 处理 |
|---|---|
| 空列表 | 插图 + 说明 + 引导操作按钮 |
| 加载中 | Skeleton / Spinner，不要空白 |
| 出错 | 友好错误信息 + 重试按钮 |
| 无权限 | 说明 + 联系引导 |
| 成功操作 | Toast 轻提示，不打断 |

### 5. 视觉一致性
- 颜色：只用设计系统的色板（primary/secondary/muted/destructive）
- 字号：用预设层级（text-xs/sm/base/lg/xl/2xl）
- 圆角：统一（rounded-md / rounded-lg）
- 阴影：预设层级（shadow-sm/md/lg）

### 6. 响应式调整
- 断点：sm(640) / md(768) / lg(1024) / xl(1280)
- 移动优先写法：`className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"`
- 触摸目标：移动端按钮至少 44x44px

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找组件 | `find_files "**/*.tsx"` | 定位 |
| 读样式 | `read_file_lines` | 理解现有 token |
| 编辑 | `apply_diff` | 修改 className |
| 验证 | dev server + 截图 | 确认视觉效果 |

## 检查清单

- [ ] 间距用 token，无魔法数字
- [ ] 颜色/字号/圆角来自设计系统
- [ ] 交互元素有完整 5 状态
- [ ] 空状态有引导
- [ ] 加载有 skeleton/spinner
- [ ] 响应式三档（手机/平板/桌面）正常
- [ ] focus 状态可见（可访问性）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 魔法数字间距（margin: 13px） | 设计 token（gap-3 = 12px） |
| 只写桌面，移动自适应 | 移动优先，逐级增强 |
| 忽略 focus 状态 | 可见的 focus outline |
| 空列表什么都不显示 | 空状态 + 引导 |
| 到处用不同圆角/阴影 | 统一预设 |

## 输出要求

1. **审查发现**：不一致的问题清单
2. **修改清单**：每个文件改了什么
3. **token 使用**：间距/颜色/字号的体系化
4. **状态覆盖**：交互元素的 5 状态
5. **验证截图**：修改前后对比
---
name: ui-polish
description: >-
  Use this skill for focused UI refinement: layout density, spacing, responsive
  states, button placement, toolbars, tabs, empty states, and visual consistency.
work_modes: [coding]
---

