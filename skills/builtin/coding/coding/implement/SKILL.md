---
name: implement
description: >-
  Use this skill when the user asks to implement a feature, add functionality,
  or build something new in code. Trigger on requests like "implement this
  feature", "add this function", "create this endpoint", "build this module",
  "write a function that", "add support for", or when the user provides a
  specification, requirements document, or user story for implementation.
work_modes: [coding]
---

# Feature Implementation

## 适用场景

需要向代码库新增功能、端点、模块、组件或行为时使用。涵盖：从规格说明落地代码、为已有模块添加能力、补全用户故事、实现 API 接口、搭建服务层等。

## 核心原则

1. **先理解再动手**：永远不要对未读过的代码做修改。先用 `search_code` / `find_files` / `read_file_lines` 摸清结构和约定。
2. **外科手术式编辑**：优先 `apply_diff` 或 `multi_edit` 做最小改动，绝不整文件重写。
3. **遵循既有模式**：新代码必须与周围代码风格、命名、分层、错误处理方式一致。
4. **测试先行或同步**：在实现的同时补测试，高风险逻辑用 TDD。
5. **增量提交**：每个可独立验证的改动单独 commit，便于回滚和 review。

## 执行流程

### 1. 探索与理解（Explore）
- `search_code "<相关符号或关键词>"` 定位已有实现
- `read_file_lines` 完整读取将被修改或参考的文件
- `find_symbols` 获取类/函数签名概览
- 检查现有测试目录、CI 配置、lint 规则，了解质量基线
- 记录发现：项目用的框架、版本、目录约定、数据流方向

### 2. 设计与分解（Plan）
- 如果改动跨多个模块，先用 todo list 拆解为有序步骤
- 确认接口契约（入参/出参/错误形态）与调用方
- 对有多种实现方案的情况，用 `ask_clarification` 确认方向

### 3. 实现（Implement）
- 用 `apply_diff` / `multi_edit` 做精准编辑
- 每完成一个独立单元立即验证，不要堆砌大段未测代码
- 新增文件时确保符合目录约定（如路由在 routers/、服务在 services/）

### 4. 验证（Verify）— 强制
- Python：`run_linter`（ruff/mypy）→ `run_tests`（pytest）
- JS/TS：`run_linter`（eslint/tsc）→ `run_tests`（jest/vitest）
- 其他语言：用 `bash` 跑项目原生测试命令
- **验证失败必须修根因，不贴症状补丁**
- 验证通过后引用实际输出作为证据

### 5. 收尾（Finish）
- `git_diff` 自查改动范围是否符合预期
- `git_commit` 用 Conventional Commits：`feat(scope): 描述`
- 如果改动影响文档/API，同步更新

## 工具优先级

| 场景 | 首选工具 | 备注 |
|---|---|---|
| 查找已有代码 | `search_code` / `find_files` | 语义搜索 |
| 读取文件 | `read_file_lines` | 支持行范围，省 token |
| 单处编辑 | `apply_diff` | 带上下文校验 |
| 多处编辑 | `multi_edit` | 单次原子提交 |
| 新建文件 | `write_file` | 仅标准工具 |
| 验证 | `run_tests` + `run_linter` | 必须都跑 |

## 检查清单

实现完成前逐项确认：
- [ ] 已读过所有被修改文件的相关上下文
- [ ] 改动遵循项目现有命名和分层约定
- [ ] 新增逻辑有对应测试覆盖
- [ ] `run_linter` 无新增报错
- [ ] `run_tests` 全部通过（引用输出证据）
- [ ] commit message 符合 Conventional Commits
- [ ] 没有引入未提交的调试代码 / print / console.log

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 直接改没读过的文件 | 先 `read_file_lines` 理解上下文 |
| 整文件重写做小改动 | `apply_diff` 做最小精准编辑 |
| 堆完所有代码才测试 | 每个单元立即验证 |
| 跳过 lint 直接跑测试 | lint → test 顺序执行 |
| 用 try/except 吞错误 | 明确错误语义并传播 |
| 报"已完成"但没跑测试 | 引用实际通过的测试输出 |

## 输出要求

最终回复必须包含：
1. **改了什么**：文件清单 + 一句话说明每个文件的改动意图
2. **为什么这样改**：设计决策与替代方案
3. **验证证据**：粘贴 `run_tests` / `run_linter` 的关键输出
4. **后续建议**：待办、风险、可选优化
---
name: implement
description: >-
  Use this skill when the user asks to implement a feature, add functionality,
  or build something new in code. Trigger on requests like "implement this
  feature", "add this function", "create this endpoint", "build this module",
  "write a function that", "add support for", or when the user provides a
  specification, requirements document, or user story for implementation.
work_modes: [coding]
---

