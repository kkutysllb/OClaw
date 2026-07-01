---
name: test-driven-development
description: >-
  Use this skill when implementing behavior changes or bug fixes where a
  focused failing test can be written first. Trigger on TDD, regression test,
  bug fix, behavior change, edge case, or when tests are missing for risky code.
work_modes: [coding]
---

# Test-Driven Development

## 适用场景

实现行为变更或 bug 修复时，先写失败测试再写实现。特别适合：新功能开发、bug 修复（测试即复现）、边界用例覆盖、高风险逻辑加固。

## 核心原则

1. **红-绿-重构**：写失败测试（红）→ 最小实现使其通过（绿）→ 重构保持绿色。
2. **测试描述行为而非实现**：测"做了什么"，不测"怎么做的"，避免实现耦合。
3. **小步前进**：每个测试只验证一个行为点，失败原因应该一目了然。
4. **测试是文档**：好的测试名就是行为规约，读测试就能理解接口契约。
5. **先写最难的**：边界和异常用例先写，快乐路径最后。

## 执行流程

### 1. 理解行为规约（Specify）
- 明确要实现的**行为**（输入 → 期望输出/副作用）
- 列出用例：快乐路径、边界值（空/null/极值）、异常路径
- 确认现有接口契约，测试要匹配真实调用方式

### 2. 写第一个失败测试（Red）
```python
def test_get_user_returns_none_when_not_found():
    repo = UserRepository()
    assert repo.get_user("nonexistent-id") is None
```
- 测试名清晰描述行为：`test_<动作>_<条件>_<期望>`
- 运行确认它**因为正确原因失败**（不是 import 错误等）
- `run_tests` 看到红色失败

### 3. 最小实现使其通过（Green）
- 写**最简单**的让测试通过的代码，不要过度设计
- 允许"硬编码返回值"在第一步，后续测试会逼出真实逻辑
- `run_tests` 看到绿色通过

### 4. 补充更多用例（Red-Green 循环）
逐个添加：
- 边界值：空字符串、0、null、极值
- 异常路径：无效输入、资源不存在、权限不足
- 状态相关：多次调用、顺序依赖

每加一个测试，先确认红，再扩展实现到绿。

### 5. 重构（Refactor）
- 测试全绿后，改善实现和测试代码质量
- 提取公共 setup、消除重复、改善命名
- 每次重构后 `run_tests` 保持绿色

## 测试设计要点

**测试结构（Arrange-Act-Assert）**
```
# Arrange - 准备
# Act - 执行
# Assert - 验证
```
三段分明，读测试像读规约。

**命名规范**
- `test_<被测方法>_<条件>_<期望结果>`
- 例：`test_parse_date_raises_on_invalid_format`
- 中文项目可用：`test_解析日期_格式非法时抛出异常`

**用例覆盖维度**
| 维度 | 用例 |
|---|---|
| 正常 | 典型输入，期望输出 |
| 边界 | 空、null、0、最大值、最小值 |
| 异常 | 无效输入、资源缺失、权限不足 |
| 并发 | 多线程/多次调用 |
| 幂等 | 重复调用结果一致 |

**Mock 策略**
- Mock 外部依赖（DB、API、文件系统），不 mock 被测对象
- Mock 行为而非实现（mock "返回 X"，不 mock "第 3 行调用 Y"）
- 优先用 fake/stub，减少 mock 框架耦合

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 写测试 | `write_file` / `apply_diff` | 新建或追加测试 |
| 运行测试 | `run_tests` | 确认红/绿状态 |
| 读被测代码 | `read_file_lines` | 理解接口 |
| 重构 | `apply_diff` + `run_tests` | 保持绿色 |

## 检查清单

- [ ] 测试名清晰描述行为规约
- [ ] 每个测试只验证一个行为点
- [ ] 覆盖了正常、边界、异常三类用例
- [ ] 测试先失败（红）后通过（绿）
- [ ] 实现是最小可用版本，未过度设计
- [ ] 测试不依赖实现细节（如私有方法）
- [ ] 重构后测试仍全绿

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 先写实现再补测试 | 先写失败测试 |
| 一个测试验证多个行为 | 一个测试一个行为点 |
| 测试名是 test1/test2 | 描述行为的清晰命名 |
| Mock 被测对象本身 | Mock 外部依赖 |
| 只测快乐路径 | 覆盖边界和异常 |
| 过度 mock 导致测试脆弱 | 用 fake/stub 减少耦合 |

## 输出要求

1. **行为规约**：列出要实现的用例（正常/边界/异常）
2. **红-绿记录**：关键测试从失败到通过的输出
3. **实现说明**：最小实现的设计决策
4. **覆盖率**：新增测试覆盖的路径
5. **重构说明**：如有重构，说明变换内容
---
name: test-driven-development
description: >-
  Use this skill when implementing behavior changes or bug fixes where a
  focused failing test can be written first. Trigger on TDD, regression test,
  bug fix, behavior change, edge case, or when tests are missing for risky code.
work_modes: [coding]
---

