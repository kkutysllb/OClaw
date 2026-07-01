---
name: docs
description: >-
  Use this skill when writing or updating developer docs, README sections,
  API docs, architecture notes, changelogs, inline usage examples, or migration
  guidance.
work_modes: [coding]
---

# Documentation

## 适用场景

- 编写或更新 README、开发者文档、API 文档
- 编写架构说明、设计决策记录（ADR）
- 更新 changelog 和迁移指南
- 添加代码内联文档和示例

## 核心原则

1. **文档即代码**：文档与代码同仓库、同版本管理、同步更新
2. **面向读者**：根据读者角色（新成员/开发者/用户）调整内容深度
3. **可执行示例**：代码示例可以直接复制运行，不是伪代码
4. **简洁精准**：说清楚必要的，不写显而易见的废话
5. **及时更新**：代码变更时同步更新文档

## 执行流程

### 1. 确定文档类型

| 文档类型 | 读者 | 内容 | 位置 |
|---------|------|------|------|
| **README** | 所有人 | 项目概述、快速开始、核心功能 | 项目根目录 |
| **SETUP** | 新成员 | 环境搭建、依赖安装、运行步骤 | `docs/SETUP.md` |
| **API 文档** | 开发者 | 端点、参数、响应格式、示例 | `docs/API.md` |
| **架构文档** | 开发者 | 系统架构、模块设计、数据流 | `docs/ARCHITECTURE.md` |
| **ADR** | 开发者 | 架构决策记录、为什么这样选 | `docs/adr/` |
| **CHANGELOG** | 所有人 | 版本变更记录 | `CHANGELOG.md` |
| **内联文档** | 开发者 | 函数/类/模块的 docstring | 代码中 |

### 2. README 结构

```markdown
# Project Name

一句话描述项目是什么。

## 快速开始

\`\`\`bash
# 安装
pnpm install

# 配置
cp .env.example .env

# 运行
pnpm dev
\`\`\`

## 核心功能

- 功能 1：简述
- 功能 2：简述

## 文档

- [环境搭建](docs/SETUP.md)
- [API 文档](docs/API.md)
- [架构设计](docs/ARCHITECTURE.md)

## 开发

\`\`\`bash
pnpm test      # 测试
pnpm lint      # 代码检查
pnpm build     # 构建
\`\`\`

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)
```

### 3. API 文档格式

```markdown
## POST /api/users

创建新用户。

### 请求

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | ✅ | 用户邮箱 |
| name | string | ✅ | 用户名 |
| role | string | ❌ | 角色，默认 "user" |

### 请求示例

\`\`\`json
{
  "email": "user@example.com",
  "name": "Test User"
}
\`\`\`

### 响应

**201 Created**

\`\`\`json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "name": "Test User",
  "created_at": "2025-07-01T12:00:00Z"
}
\`\`\`

### 错误响应

| 状态码 | 说明 |
|-------|------|
| 400 | 参数校验失败 |
| 409 | 邮箱已存在 |
```

### 4. 内联文档（docstring）

```python
def calculate_discount(price: float, discount_rate: float, min_price: float = 0) -> float:
    """计算折扣后的价格。

    应用折扣率后确保不低于最低价格。

    Args:
        price: 原始价格，必须为正数。
        discount_rate: 折扣率 (0.0-1.0)，0.1 表示 9 折。
        min_price: 最低价格限制，默认为 0。

    Returns:
        折扣后的价格。

    Raises:
        ValueError: 如果 price 或 discount_rate 不在有效范围内。

    Example:
        >>> calculate_discount(100, 0.2)
        80.0
    """
    if price < 0:
        raise ValueError("Price must be positive")
    if not 0 <= discount_rate <= 1:
        raise ValueError("Discount rate must be between 0 and 1")

    discounted = price * (1 - discount_rate)
    return max(discounted, min_price)
```

### 5. 架构决策记录（ADR）

```markdown
# ADR-001: 使用 LangGraph 作为 Agent 编排引擎

## 状态
已接受

## 背景
需要选择一个 Agent 编排框架，要求支持：
- 多步推理
- 工具调用
- 状态管理
- 流式输出

## 决策
选择 LangGraph，因为：
1. 原生支持有状态的图编排
2. 与 LangChain 生态兼容
3. 支持流式输出和中断恢复

## 后果
- 正面：简化了 Agent 编排逻辑
- 负面：引入了对 LangGraph 的依赖
- 缓解：抽象编排接口，降低耦合
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` / `apply_diff` | 创建/修改文档 |
| `read_file` | 理解代码后写文档 |
| `grep` | 查找需要文档化的函数/模块 |

## 检查清单

- [ ] README 有快速开始和核心功能说明
- [ ] API 文档包含所有公开端点
- [ ] 代码示例可直接运行
- [ ] 公共函数/类有 docstring
- [ ] 文档与代码版本同步
- [ ] 无过时或错误的信息

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 文档写完就忘 | 代码变更时同步更新 |
| 伪代码示例 | 可直接复制运行的示例 |
| 面面俱到像教科书 | 精准覆盖读者需要的信息 |
| 只写不组织 | 有清晰的结构和导航 |
| 文档与代码分离 | 文档即代码，同仓库管理 |

## 输出要求

1. 提供结构化的文档内容
2. 确保代码示例可运行
3. 根据文档类型适配内容和深度
4. 与现有文档风格保持一致
5. 标注需要同步更新的关联文档
---
name: docs
description: >-
  Use this skill when writing or updating developer docs, README sections,
  API docs, architecture notes, changelogs, inline usage examples, or migration
  guidance.
work_modes: [coding]
---

