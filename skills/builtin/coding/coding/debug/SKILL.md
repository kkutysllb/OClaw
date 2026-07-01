---
name: debug
description: >-
  Use this skill when the user reports a bug, error, crash, or unexpected behavior in code. Trigger on requests like "debug this", "fix this bug", "why is this erroring", "something is wrong", "it's not working", "investigate this issue", or when a stack trace, error message, or test failure is shared. Also trigger when the user asks to diagnose performance problems or memory leaks.
work_modes: [coding]
---

# Bug Debugging

## 适用场景

用户报告 bug、错误、崩溃、异常行为、测试失败、性能问题或内存泄漏时使用。需要根因定位而非表面修补。

## 核心原则

1. **先复现再修复**：无法稳定复现的 bug 无法确认修复。先建立最小复现路径。
2. **假设驱动调试**：每次只验证一个假设，用证据证实或证伪，不要同时改多处。
3. **追根因不贴症状**：`except Exception: pass` 式修补是债务，必须找到真正的触发点。
4. **二分定位**：大范围问题用二分法（注释/禁用一半代码）快速缩小可疑区域。
5. **证据优先**：所有结论基于日志、堆栈、测试输出，不基于猜测。

## 执行流程

### 1. 收集症状（Reproduce）
- 让用户提供或自己构造最小复现步骤
- 记录：错误信息全文、堆栈跟踪、环境（OS/版本/依赖）、触发条件
- 如果能写失败测试复现，立即写（这是最好的回归保护）

### 2. 定位根因（Isolate）
- `read_file_lines` 读取堆栈指向的文件和行
- `search_code` 搜索相关符号、错误信息、异常类
- `find_symbols` 理解调用链结构
- 对可疑区域用二分法：注释掉一半，看 bug 是否消失
- 检查最近改动：`git_log -- <文件>` 看是否是回归

### 3. 形成假设（Hypothesize）
- 基于证据写出明确假设："当 X 为 null 时，Y 分支不执行，导致 Z"
- 设计一个能证伪该假设的验证（加日志、加断言、写测试）

### 4. 验证假设（Verify）
- 加临时日志/断言运行，观察实际行为是否符合假设
- 如果不符合，回到第 2 步重新定位
- 如果符合，进入修复

### 5. 最小修复（Fix）
- 只改导致 bug 的最小代码，不顺手重构
- 用 `apply_diff` 做精准编辑
- 删除临时调试代码（日志/断言/print）

### 6. 回归验证（Regression）
- 运行复现该 bug 的测试，确认现在通过
- `run_tests` 跑相关测试套件，确认没引入新问题
- 提交：`fix(scope): 描述根因和修复`

## 常见 bug 类型与定位策略

| Bug 类型 | 定位策略 |
|---|---|
| **空值/类型错误** | 搜索赋值点，加断言，检查数据流源头 |
| **竞态/并发** | 加时间戳日志，检查锁/共享状态，复现并发场景 |
| **状态污染** | 对比单次调用 vs 多次调用，检查全局/类变量 |
| **环境差异** | 对比本地/CI/生产的环境变量、依赖版本、文件路径 |
| **回归（之前好的）** | `git_log` + `git_diff` 找引入 commit，二分 bisect |
| **性能问题** | 先 profiling 定位热点，不要盲目优化 |
| **内存泄漏** | 用内存分析工具，检查未释放的引用/闭包/缓存 |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 读堆栈指向的代码 | `read_file_lines` | 精准读取 |
| 搜索错误信息来源 | `search_code` | 找抛出点 |
| 查看最近改动 | `git_log` / `git_diff` | 排查回归 |
| 运行复现命令 | `bash` | 执行测试/脚本 |
| 加临时日志后运行 | `bash` | 观察运行时状态 |
| 跑测试验证 | `run_tests` | 确认修复 |

## 检查清单

- [ ] 已建立可复现路径（命令或测试）
- [ ] 根因已用证据确认（日志/断言/堆栈）
- [ ] 修复是最小改动，未夹带无关重构
- [ ] 临时调试代码已全部删除
- [ ] 复现测试现在通过
- [ ] 相关测试套件无新增失败
- [ ] commit message 说明了根因

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 不复现就改代码 | 先建立复现路径 |
| 同时改多处猜哪个生效 | 每次只验证一个假设 |
| `try/except` 吞掉异常 | 找到抛出点修根因 |
| 改完不删 print 调试 | 用 `apply_diff` 清理 |
| 修完不跑测试 | `run_tests` 确认回归 |
| 报"应该修好了" | 引用通过的测试输出 |

## 输出要求

1. **根因**：一句话说明 bug 的真正触发条件
2. **证据**：堆栈/日志/测试输出片段
3. **修复**：改了什么文件、为什么这样改
4. **验证**：复现测试从失败到通过的输出对比
5. **预防**：建议如何避免同类问题（类型检查/测试/断言）
---
name: debug
description: >-
  Use this skill when the user reports a bug, error, crash, or unexpected behavior
  in code. Trigger on requests like "debug this", "fix this bug", "why is this
  erroring", "something is wrong", "it's not working", "investigate this issue",
  or when a stack trace, error message, or test failure is shared. Also trigger
  when the user asks to diagnose performance problems or memory leaks.
work_modes: [coding]
---

