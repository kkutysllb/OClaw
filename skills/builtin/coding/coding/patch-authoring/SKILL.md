---
name: patch-authoring
description: >-
  Use this skill when producing code patches, one-click fixes, deterministic
  automatic fixes, minimal diffs, stale-safe replacements, or applyable changes.
work_modes: [coding]
---

# Patch Authoring

## 适用场景

产出可应用的代码补丁：精准修复、最小 diff、确定性自动修复、stale-safe（容忍上下文漂移）的替换。强调 diff 的可应用性和最小性。

## 核心原则

1. **最小 diff 原则**：只包含必要的变更行，不夹带格式调整、未相关重构。
2. **上下文锚定**：diff 必须带足够的上下文行（通常 3 行），确保能定位到正确位置。
3. **stale-safe**：上下文用稳定锚点（函数签名、不变行），不用易变行（注释、空行）。
4. **原子性**：一个 patch 解决一个问题，多个独立问题拆成多个 patch。
5. **可回滚**：每个 patch 都应能用 `undo_last_edit` 或 `git checkout` 回退。

## 执行流程

### 1. 精确定位
- `read_file_lines` 读取目标位置的完整上下文（前后各 10-20 行）
- 确认行号和缩进（空格 vs Tab）
- 记录原文，作为 diff 的 `-` 行和验证基准

### 2. 设计最小变更
- 只改必须改的行
- 保持周围代码的缩进、引号风格、命名约定
- 如果需要新增多行，考虑是否提取为函数更清晰

### 3. 构造 Patch

**使用 apply_diff（统一 diff 格式）**
```
@@ -10,5 +10,5 @@
 def get_user(user_id):
-    user = db.find(user_id)
-    return user
+    user = db.find(user_id)
+    return user or None
+    # 新增的边界处理
```
- hunk 头 `@@ -old,count +new,count @@` 行号必须准确
- 上下文行（` `开头）必须与原文**逐字符匹配**（含缩进）
- 删除行（`-`）和新增行（`+`）成对出现

**使用 multi_edit（多文件/多处编辑）**
- 每个 edit 是 `{file_path, old_string, new_string}`
- `old_string` 必须在文件中唯一存在
- 多个 edit 在单次原子操作中应用

**使用 insert_at_line**
- 适合纯插入（不替换已有内容）
- 指定行号 + 插入内容

### 4. 验证可应用性
- 应用后 `read_file_lines` 确认改动正确
- `run_tests` 确认行为符合预期
- `run_linter` 确认无新增问题

### 5. 提交
- `git_diff` 确认改动范围符合预期
- `git_commit` 描述修复内容

## stale-safe 技巧

当目标代码可能已被其他改动触碰时：
- **用函数签名做锚点**：`def get_user(user_id):` 比 `    return user` 更稳定
- **避免用空行/注释做上下文**：它们最容易被改动
- **用多行唯一片段**：3-5 行的组合比单行更难撞车
- **优先用 multi_edit 的 old_string**：它要求全文匹配，更严格

## 工具优先级

| 场景 | 工具 | 优势 |
|---|---|---|
| 精准替换 | `apply_diff` | 统一 diff，带上下文校验 |
| 多处编辑 | `multi_edit` | 原子性，单次多文件 |
| 纯插入 | `insert_at_line` | 行号定位 |
| 读取上下文 | `read_file_lines` | 确认原文 |
| 验证改动 | `git_diff` / `read_file_lines` | 确认结果 |
| 回退 | `undo_last_edit` | 单步撤销 |

## 检查清单

- [ ] diff 只包含必要变更，无无关格式调整
- [ ] 上下文行（3 行）与原文逐字符匹配
- [ ] 缩进风格（空格/Tab）与原文件一致
- [ ] 引号、命名约定与周围代码一致
- [ ] 应用后 `read_file_lines` 确认改动正确
- [ ] `run_tests` 通过
- [ ] 改动可被 `undo_last_edit` 或 `git checkout` 回退

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 整文件重写做小改 | `apply_diff` 最小 hunk |
| 上下文不足（0-1 行） | 至少 3 行稳定上下文 |
| 用空行/注释做锚点 | 用函数签名/不变代码 |
| 混合多个无关变更 | 一个 patch 一个问题 |
| 改完不验证 | read + test 确认 |
| 缩进不匹配 | 严格复制原文件缩进 |

## 输出要求

1. **目标定位**：文件 + 行号 + 原文片段
2. **变更设计**：为什么这样改、改了哪些行
3. **Patch 内容**：apply_diff 的 hunk 或 multi_edit 的 edits
4. **验证结果**：应用后的文件片段 + 测试输出
5. **回滚方式**：如何撤销此 patch
---
name: patch-authoring
description: >-
  Use this skill when producing code patches, one-click fixes, deterministic
  automatic fixes, minimal diffs, stale-safe replacements, or applyable changes.
work_modes: [coding]
---

