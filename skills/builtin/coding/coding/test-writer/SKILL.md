---
name: test-writer
description: >-
  Use this skill when the coding task requires adding, fixing, or improving
  automated tests. Trigger on requests mentioning tests, pytest, vitest, jest,
  regression coverage, failing tests, test gaps, snapshots, fixtures, or TDD.
work_modes: [coding]
---

# Test Writer

## 适用场景

需要新增、修复或改进自动化测试：补充测试覆盖、修复失败的测试、设置 fixtures/snapshots、搭建测试基础设施。

## 核心原则

1. **测行为不测实现**：验证公共接口的输入输出，不测私有方法和内部结构。
2. **隔离与可重复**：每个测试独立运行，不依赖其他测试的执行顺序或副作用。
3. **失败信息要可读**：断言失败时应清楚显示期望值与实际值。
4. **快慢分离**：单元测试必须快（毫秒级），集成/E2E 测试单独标记。
5. **真实胜于完美**：一个能捕获真实回归的简单测试，胜过覆盖率高但无意义的测试。

## 执行流程

### 1. 分析测试目标
- `search_code` 找到被测代码的公共接口
- `read_file_lines` 理解接口契约和行为分支
- 检查现有测试目录结构和约定（命名、组织、fixtures）
- 确认测试框架：pytest / vitest / jest / unittest

### 2. 设计测试用例
按维度列举：
- **正常路径**：典型输入 → 期望输出
- **边界值**：空集合、null/None、0、极值、单元素
- **异常路径**：无效输入、资源缺失、权限不足、超时
- **状态/顺序**：多次调用、幂等性、状态机转换
- **并发**（如适用）：多线程安全

### 3. 编写测试
遵循项目现有约定：
- **Python/pytest**：`test_<功能>.py`，函数 `test_<行为>_<条件>`
- **JS/TS**：`*.test.ts` / `*.spec.ts`，`describe` + `it`

测试结构（AAA）：
```python
def test_create_user_rejects_duplicate_email():
    # Arrange
    repo = UserRepository()
    repo.add(User(email="a@b.com"))

    # Act + Assert
    with pytest.raises(DuplicateEmailError):
        repo.create(email="a@b.com")
```

### 4. 设置 Fixtures / Setup
- 公共的构造逻辑提取为 fixture（pytest）或 beforeEach（jest）
- 外部依赖（DB、API）用 fake/stub 替代，不用真实服务
- 测试数据用 factory/builder，不用魔法字符串

### 5. 运行与验证
- `run_tests <新测试文件>` 先单独跑，确认通过
- `run_tests` 跑全套，确认无回归
- 检查覆盖率：`run_tests --cov`（如有）确认目标路径已覆盖

## 测试质量标准

| 维度 | 好测试 | 坏测试 |
|---|---|---|
| 命名 | 描述行为：`test_login_rejects_wrong_password` | `test1` / `test_login` |
| 独立性 | 不依赖其他测试 | 必须按顺序跑 |
| 副作用 | 自带清理/事务回滚 | 污染全局状态 |
| 断言 | 精准断言期望值 | 只断言"不抛异常" |
| 可读性 | 三段式，一目了然 | 巨型测试混杂多事 |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 读被测接口 | `read_file_lines` / `find_symbols` | 理解契约 |
| 看现有测试约定 | `search_code` | 匹配项目风格 |
| 写测试文件 | `write_file` / `apply_diff` | 新建或追加 |
| 运行测试 | `run_tests` | 验证通过 |
| 跑 lint | `run_linter` | 测试代码也要 lint |

## 检查清单

- [ ] 测试遵循项目现有命名和组织约定
- [ ] 每个测试只验证一个行为点
- [ ] 覆盖正常、边界、异常三类用例
- [ ] 外部依赖用 fake/stub，不依赖真实服务
- [ ] 测试独立可重复运行
- [ ] 断言精准，失败信息可读
- [ ] `run_tests` 全部通过
- [ ] 无 flaky（时好时坏）的测试

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 测私有方法 | 通过公共接口间接验证 |
| 测试间有依赖 | 每个测试自带 setup |
| 断言只检查"没抛异常" | 精准断言返回值/状态 |
| 用真实数据库/网络 | 用 fake/in-memory 替代 |
| 一个测试验证 5 件事 | 拆成多个聚焦测试 |
| 忽略 flaky 测试 | 修复或隔离 flaky |

## 输出要求

1. **测试设计**：列出的用例维度和具体用例
2. **新增/修改文件**：清单 + 每个文件的职责
3. **运行结果**：`run_tests` 的通过输出
4. **覆盖说明**：新增测试覆盖了哪些行为路径
5. **已知局限**：哪些路径暂未覆盖及原因
---
name: test-writer
description: >-
  Use this skill when the coding task requires adding, fixing, or improving
  automated tests. Trigger on requests mentioning tests, pytest, vitest, jest,
  regression coverage, failing tests, test gaps, snapshots, fixtures, or TDD.
work_modes: [coding]
---

