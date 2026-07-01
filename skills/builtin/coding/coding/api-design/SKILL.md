---
name: api-design
description: >-
  Use this skill when adding or changing HTTP APIs, RPC endpoints, request and
  response schemas, pagination, validation, status codes, or backwards-compatible
  API behavior.
work_modes: [coding]
---

# API Design

## 适用场景

新增或修改 HTTP/RPC API：端点设计、请求/响应 schema、分页、校验、状态码、版本兼容、错误格式。

## 核心原则

1. **资源导向**：URL 表达资源，HTTP 方法表达动作（RESTful）。
2. **契约先行**：先定义 request/response schema，再写实现。
3. **向后兼容**：新增字段可选，删除字段先废弃。破坏性变更要版本化。
4. **错误可机器消费**：错误响应是结构化的，含 code/message/details，不只是字符串。
5. **幂等优先**：写操作尽量设计为幂等（PUT/DELETE 天然幂等，POST 用幂等键）。

## 执行流程

### 1. 定义资源与端点
- 识别核心资源（名词）：users, orders, documents
- 映射 HTTP 方法：
  - `GET /resources` — 列表
  - `GET /resources/{id}` — 单个
  - `POST /resources` — 创建
  - `PUT /resources/{id}` — 全量更新（幂等）
  - `PATCH /resources/{id}` — 部分更新
  - `DELETE /resources/{id}` — 删除（幂等）

### 2. 设计 Schema
**请求 Schema**
- 必填 vs 可选字段明确
- 字段类型、约束（长度/范围/格式）
- 嵌套对象和数组

**响应 Schema**
- 统一外层格式：`{ "data": ..., "meta": {...} }` 或直接返回
- 分页：`{ "data": [...], "pagination": {"page", "pageSize", "total"} }`
- 时间用 ISO 8601 字符串（UTC）
- ID 用字符串（避免数值精度问题）

### 3. 状态码规范
| 场景 | 状态码 |
|---|---|
| 创建成功 | 201 |
| 成功（无特殊） | 200 |
| 无内容（DELETE） | 204 |
| 参数错误 | 400 |
| 未认证 | 401 |
| 无权限 | 403 |
| 资源不存在 | 404 |
| 冲突（重复） | 409 |
| 前置条件失败 | 412 |
| 限流 | 429 |
| 服务器错误 | 500 |

### 4. 错误格式
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "邮箱格式无效",
    "details": [{"field": "email", "issue": "invalid_format"}],
    "request_id": "req_xxx"
  }
}
```

### 5. 版本与兼容
- **版本策略**：URL 前缀 `/v1/` 或 Header `Accept: application/vnd.api+json;version=1`
- **向后兼容变更**（不需要新版本）：
  - 新增可选请求字段
  - 新增响应字段
  - 新增端点
- **破坏性变更**（需要新版本）：
  - 删除/重命名字段
  - 改变字段类型
  - 改变必填性

### 6. 实现与文档
- 用 Pydantic / Zod / OpenAPI 定义 schema
- 自动生成 API 文档（Swagger / ReDoc）
- 写端点测试（用 `test-writer` 技能）

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 读现有 API | `search_code "@router" / "@app.get"` | 了解约定 |
| 设计 schema | `write_file` | 定义 Pydantic/Zod 模型 |
| 实现端点 | `apply_diff` / `write_file` | 写路由 |
| 测试端点 | `run_tests` + HTTP client | 验证响应 |

## 检查清单

- [ ] 端点遵循 RESTful 命名（资源用名词复数）
- [ ] HTTP 方法语义正确（GET 无副作用）
- [ ] 请求/响应有明确 schema 定义
- [ ] 状态码使用符合规范
- [ ] 错误响应是结构化的
- [ ] 分页/过滤/排序已设计（列表端点）
- [ ] 向后兼容性已评估
- [ ] 端点有测试覆盖

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 动词在 URL：`/getUser` | 资源+方法：`GET /users/{id}` |
| GET 修改数据 | 用 POST/PUT/PATCH |
| 错误返回纯字符串 | 结构化 error 对象 |
| 无分页的列表端点 | 支持 pagination 参数 |
| 时间用时间戳数字 | ISO 8601 字符串 |
| 破坏性变更不版本化 | 新版本或废弃流程 |

## 输出要求

1. **端点清单**：method + path + 简述
2. **Schema 定义**：请求/响应的完整字段
3. **错误契约**：可能的状态码和错误格式
4. **兼容性说明**：是新增还是破坏性变更
5. **示例**：成功和失败的请求/响应样例
---
name: api-design
description: >-
  Use this skill when adding or changing HTTP APIs, RPC endpoints, request and
  response schemas, pagination, validation, status codes, or backwards-compatible
  API behavior.
work_modes: [coding]
---

