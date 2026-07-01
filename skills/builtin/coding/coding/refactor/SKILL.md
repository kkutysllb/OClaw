---
name: refactor
description: >-
  Use this skill when the user asks to refactor, clean up, restructure, or
  improve code quality without changing behavior. Trigger on requests like
  "refactor this", "clean up this code", "simplify this function", "extract
  this method", "reduce duplication", "improve code structure", "remove dead
  code", or when reviewing code that has maintainability issues. Also trigger
  for design-pattern introductions and architecture improvements.
work_modes: [coding]
---

# Code Refactoring

## 适用场景

在不改变外部行为的前提下改善代码内部结构：消除重复、简化复杂逻辑、提取函数/类、引入设计模式、改善命名、调整分层、移除死代码。

## 核心原则

1. **行为保持是底线**：重构前后可观察行为必须完全一致。没有测试网的重构等于盲飞。
2. **小步快跑**：每一步重构都应能独立提交、独立验证。拒绝"一把梭"式大重构。
3. **先绿后重构**：先确保现有测试全绿，重构过程中持续保持绿色。
4. **消除而非搬迁**：真正的重构减少代码量或复杂度，不是把烂代码挪到别处。
5. **命名即文档**：好的命名让代码自解释，减少注释需求。

## 执行流程

### 1. 建立安全网（Secure）
- `run_tests` 确认现有测试全部通过，记录绿色基线
- 如果关键路径无测试覆盖，**先补测试再重构**（用 `test-writer` 技能）
- 对纯函数可加快照测试锁定输出

### 2. 识别坏味道（Smell）
常见需重构的信号：
- **重复代码**：复制粘贴的逻辑 → 提取公共函数/基类
- **过长函数**：超过 40 行或嵌套超 3 层 → 拆分为命名清晰的子函数
- **过大类**：一个类承担过多职责 → 按职责拆分
- **过长参数列表**：超过 4 个参数 → 封装为参数对象
- **发散修改**：一个类因不同原因被频繁修改 → 按变更轴拆分
- **霰弹修改**：一个改动要改多个类 → 合并职责
- **特性依恋**：方法用了别的类多于自己的 → 搬移方法
- **死代码**：永远不会执行的分支 → 删除

### 3. 小步重构（Transform）
每次只做一种变换，改完立即验证：
- **提取函数**：选中一段逻辑 → `apply_diff` 提取为独立函数 → 跑测试
- **内联函数**：简单委托的包装 → 直接内联调用 → 跑测试
- **重命名**：`rename_symbol` 改善命名 → 跑测试
- **搬移方法/字段**：跨类迁移 → 逐个搬移，每步验证
- **以多态取代条件**：用策略/工厂模式替代 switch → 跑测试

### 4. 持续验证（Verify）
- 每一步后 `run_tests`，保持绿色
- 如果某步变红，立即回退该步（`undo_last_edit`），分析原因
- 全部完成后 `run_linter` 确认无新增警告

### 5. 提交（Commit）
- 每个独立的重构步骤单独 commit：`refactor(scope): 描述变换`
- 不要把重构和功能变更混在一个 commit

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 确认测试基线 | `run_tests` | 重构前必须全绿 |
| 重命名符号 | `rename_symbol` | 跨文件安全重命名 |
| 提取函数 | `extract_function` | 自动化提取 |
| 精准编辑 | `apply_diff` / `multi_edit` | 最小改动 |
| 回退误操作 | `undo_last_edit` | 单步撤销 |
| 持续验证 | `run_tests` | 每步后执行 |

## 检查清单

- [ ] 重构前 `run_tests` 全绿（或已补测试）
- [ ] 每一步都是单一变换，可独立描述
- [ ] 每步后 `run_tests` 仍绿
- [ ] 重构减少了代码量或复杂度（非纯搬迁）
- [ ] `run_linter` 无新增警告
- [ ] 每个 commit 只含重构，无功能变更
- [ ] commit message 描述了变换类型

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 无测试就重构 | 先补测试建安全网 |
| 大爆炸式一次性重构 | 小步快跑，逐步验证 |
| 重构夹带功能变更 | 重构和功能变更分开 commit |
| 只挪代码不减复杂度 | 真正消除重复/简化逻辑 |
| 改了一堆没跑测试 | 每步 `run_tests` 验证 |
| 重命名靠全局替换 | 用 `rename_symbol` 跨文件安全改 |

## 输出要求

1. **重构前状态**：测试基线结果
2. **坏味道识别**：列出发现的问题及对应手法
3. **变换步骤**：每步做了什么 + 验证结果
4. **量化对比**：代码行数/圈复杂度/重复率的前后变化
5. **提交记录**：各 commit 的 hash 和 message
