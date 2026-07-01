---
name: vertical-slice-development
description: >-
  Use this skill when implementing a feature end-to-end through UI, API,
  service, persistence, tests, and documentation in small reviewable slices.
work_modes: [coding]
---

# Vertical Slice Development

## 适用场景

端到端实现一个功能：贯穿 UI、API、服务、持久化、测试、文档，以小而可 review 的切片交付。

## 核心原则

1. **切片而非层级**：不按"先做完所有 UI 再做所有 API"，而是"一个功能切片贯穿所有层"。
2. **薄切片优先**：第一切片是最小可用路径（happy path），后续切片加厚。
3. **每切片可 review**：每个切片独立可测、可演示、可合并。
4. **端到端贯通**：一个切片必须从 UI 到数据完整打通，不留半截。
5. **测试随切片走**：每个切片自带测试，不积累技术债。

## 执行流程

### 1. 定义切片
将功能拆为端到端的薄切片：
```
功能：用户注册登录
├── 切片 1：注册（UI 表单 → API → DB 写入 → 测试）
├── 切片 2：登录（UI 表单 → API → token 签发 → 测试）
├── 切片 3：会话保持（token 存储 → 路由守卫 → 自动登录）
├── 切片 4：登出
└── 切片 5：密码重置
```
每个切片独立可交付，MVP = 切片 1+2。

### 2. 实现一个切片（端到端）
以"用户注册"切片为例，按数据流方向实现：

**a. 数据层**
- 定义 User 模型 / schema
- 写 migration
- 实现 repository / DAO

**b. 服务层**
- 实现 UserService.create()
- 密码哈希、重复检查、业务规则

**c. API 层**
- 定义 POST /users/register 路由
- 请求/响应 Pydantic 模型
- 错误处理（409 冲突）

**d. UI 层**
- 注册表单组件
- 表单校验 + 提交 + loading/success/error 状态
- 成功后跳转

**e. 测试**
- 服务层单元测试
- API 层集成测试
- UI 交互测试（如适用）

**f. 文档**（如影响接口）
- 更新 API 文档

### 3. 验证切片
- 端到端走通：从 UI 提交 → 数据入库 → 响应正确
- `run_tests` 全通过
- `run_linter` 无新增问题
- 截图/录屏确认 UI 行为

### 4. 提交与 review
- 切片作为独立 commit / PR
- commit message 描述这个切片完成了什么
- 可独立 review 和合并

### 5. 进入下一切片
- 基于已合并的切片继续
- 每个切片在前一个基础上增量

## 切片划分技巧

| 原则 | 说明 |
|---|---|
| 先 happy path | 第一切片只走正常流程，异常后续加 |
| 先读后写 | 列表展示（读）通常比创建（写）简单 |
| 先核心后增强 | 基础功能先，高级特性后 |
| 可独立合并 | 每切片合并后系统仍可用 |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 全栈理解 | `codebase-analysis` | 了解各层 |
| 实现 | `apply_diff` / `write_file` | 各层代码 |
| 测试 | `run_tests` | 每层验证 |
| 验证 | dev server + 截图 | 端到端确认 |

## 检查清单

- [ ] 切片端到端贯通（UI→API→服务→数据）
- [ ] 切片自带测试
- [ ] 每切片可独立 review/合并
- [ ] happy path 先行，增强后续
- [ ] 合并后系统仍可用
- [ ] `run_tests` 全通过

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 按层做（先所有 UI 再所有 API） | 按切片做（一个功能贯穿所有层） |
| 第一切片就追求完美 | 薄切片先行，逐步加厚 |
| 切片不可独立合并 | 每切片可 review 可合并 |
| 切片不带测试 | 测试随切片走 |
| 切片间强耦合 | 切片松耦合，增量叠加 |

## 输出要求

1. **切片划分**：功能的切片清单 + 优先级
2. **当前切片**：实现的切片范围
3. **各层改动**：UI/API/服务/数据的变更
4. **端到端验证**：从 UI 到数据的完整流程
5. **测试结果**：各层测试输出
6. **后续切片**：下一切片的计划
---
name: vertical-slice-development
description: >-
  Use this skill when implementing a feature end-to-end through UI, API,
  service, persistence, tests, and documentation in small reviewable slices.
work_modes: [coding]
---

