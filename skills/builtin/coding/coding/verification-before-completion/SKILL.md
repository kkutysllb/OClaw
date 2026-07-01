---
name: verification-before-completion
description: >-
  Use this skill before claiming a coding task is done, fixed, passing, or
  ready. Trigger at the end of implementations, bug fixes, refactors, review
  improvements, UI changes, and backend API changes.
work_modes: [coding]
---

# Verification Before Completion

## 适用场景

在声称任务"完成/修复/通过/就绪"之前强制执行验证。适用于任何编码任务的收尾阶段：实现、bug 修复、重构、review 改进、UI 变更、后端 API 变更。

## 核心原则

1. **证据先于断言**：永远不要说"应该可以了"，要么有证据，要么还没完成。
2. **实际运行胜于推理**：跑了测试通过 ≠ 推理出"应该通过"。必须实际执行。
3. **验证完整闭环**：改了代码 → 跑了测试 → 看了输出 → 确认通过。缺一环不算完成。
4. **诚实报告失败**：如果验证没通过，明确说"未完成"，不要美化。
5. **验证范围匹配变更范围**：小改至少跑相关测试，大改跑全套 + lint + typecheck。

## 强制验证流程

声明"完成"前，必须按序完成：

### 1. 代码自检（Self-check）
- `git_diff` 审查自己的所有改动
- 确认没有遗留的调试代码（print / console.log / TODO / FIXME）
- 确认没有误提交的文件（.env / 临时文件 / node_modules）
- 确认改动范围与任务目标一致（无多余、无遗漏）

### 2. 静态检查（Lint + Type）
- `run_linter` 执行项目的 lint 工具
  - Python：ruff / mypy / flake8
  - JS/TS：eslint / tsc --noEmit
- 确认**无新增**错误和警告（已有的可以单独处理）
- 如果有 typecheck，必须通过

### 3. 测试验证（Tests）
- `run_tests` 执行测试套件
- 确认：
  - [ ] 所有测试通过（exit code 0）
  - [ ] 没有跳过的测试（除非有明确理由）
  - [ ] 新增逻辑有对应测试
  - [ ] 复现 bug 的测试现在通过
- 引用实际输出作为证据

### 4. 行为验证（Behavior）
针对变更类型做针对性验证：
| 变更类型 | 验证方式 |
|---|---|
| API 变更 | 调用端点，确认请求/响应正确 |
| UI 变更 | 启动 dev server，截图确认渲染 |
| CLI 变更 | 运行命令，确认输出 |
| 配置变更 | 确认被正确加载和应用 |
| 数据库变更 | 确认 schema/migration 生效 |

### 5. 影响面确认（Impact）
- `search_code` 搜索被改符号的调用方
- 确认调用方不会因这次变更而破坏
- 如果是破坏性变更，确认已迁移所有调用方

## 完成声明模板

只有当上述全部通过后，才能声明完成。声明必须包含：

```
## 完成确认

### 改动清单
- file_a.py：修改了 X 函数，原因是 Y
- file_b.py：新增了 Z 模块

### 验证证据
- Lint：run_linter 通过，无新增警告
  [粘贴关键输出]
- Tests：run_tests 全部通过（N passed, 0 failed）
  [粘贴关键输出]
- 行为验证：[描述或截图]

### 已知局限
- [如有未覆盖的情况，明确列出]
```

## 常见"假完成"陷阱

| 陷阱 | 真正的完成 |
|---|---|
| "代码写完了，应该能用" | 实际运行验证过 |
| "测试加了，应该通过" | run_tests 看到 passed |
| "lint 应该没问题" | run_linter 实际执行，无新增 |
| "只改了一行，不用跑全套" | 即使一行也跑相关测试 |
| "本地能跑，CI 应该也能" | 确认本地环境与 CI 一致 |
| 跳过验证直接 commit | commit 前验证，commit 后看 CI |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 审查改动 | `git_diff` / `git_status` | 自检改动范围 |
| Lint | `run_linter` | 静态检查 |
| 测试 | `run_tests` | 动态验证 |
| 影响面 | `search_code` | 调用方检查 |
| 行为验证 | `bash` | 运行命令/服务 |

## 检查清单

声明完成前逐项确认：
- [ ] `git_diff` 已自查，无遗留调试代码
- [ ] 改动范围与任务目标一致
- [ ] `run_linter` 无新增错误/警告
- [ ] typecheck 通过（如适用）
- [ ] `run_tests` 全部通过（引用输出）
- [ ] 新增逻辑有测试覆盖
- [ ] 被改符号的调用方已检查
- [ ] 行为已实际验证（非推理）
- [ ] 已知局限已明确列出

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| "应该可以了" | 引用实际通过的输出 |
| 跳过 lint 只跑测试 | lint + test 都要跑 |
| 本地通过就完事 | 确认与 CI 环境一致 |
| 隐藏失败 | 诚实报告未通过的项 |
| 不验证就 commit | commit 前完整验证 |
| "小改不用验证" | 任何改动都要验证 |

## 输出要求

最终回复必须包含"完成确认"区块：
1. **改动清单**：每个文件 + 改动意图
2. **验证证据**：lint + test 的实际输出片段
3. **行为验证**：实际运行的结果/截图
4. **影响面**：调用方检查结论
5. **已知局限**：诚实列出未覆盖项
6. **后续建议**：可选的改进方向
---
name: verification-before-completion
description: >-
  Use this skill before claiming a coding task is done, fixed, passing, or
  ready. Trigger at the end of implementations, bug fixes, refactors, review
  improvements, UI changes, and backend API changes.
work_modes: [coding]
---

