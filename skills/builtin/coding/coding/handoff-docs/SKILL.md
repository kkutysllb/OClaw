---
name: handoff-docs
description: >-
  Use this skill when preparing project handoff documentation, implementation
  summaries, maintenance notes, known limitations, next steps, or onboarding
  material for another engineer or user.
work_modes: [coding]
---

# Handoff Documentation

## 适用场景

- 项目交付时需要编写交接文档
- 任务完成后需要总结实现内容
- 团队成员变更时需要 onboarding/offboarding 文档
- 需要记录已知问题和后续改进方向

## 核心原则

1. **完整自包含**：接手者无需询问前开发者就能理解项目
2. **重点突出**：架构决策和关键约束比实现细节更重要
3. **可操作**：后续步骤和改进方向具体可执行
4. **诚实透明**：已知问题和风险不隐瞒
5. **结构清晰**：从概述到细节，层次分明

## 执行流程

### 1. 交接文档结构

```markdown
# [项目名] 交接文档

## 1. 项目概述
- 一句话描述项目目的
- 当前状态（开发中/已上线/维护中）
- 关键指标（用户数、请求量、SLA）

## 2. 架构概览
- 系统架构图
- 核心模块和职责
- 技术栈
- 外部依赖

## 3. 关键设计决策
- 为什么选这个方案？
- 尝试过什么替代方案？
- 有什么约束？

## 4. 本地开发
- 环境搭建步骤
- 开发命令
- 常见问题

## 5. 部署运维
- 部署流程
- 环境配置
- 监控和告警
- 备份恢复

## 6. 已知问题
- 技术债务
- 已知 bug
- 性能瓶颈

## 7. 后续计划
- 待完成功能
- 建议改进
- 优先级建议

## 8. 联系信息
- 相关人员
- 文档链接
```

### 2. 实现摘要

```markdown
## 本次实现摘要

### 完成的功能
1. **用户认证模块**：JWT + Refresh Token，支持多设备登录
2. **权限系统**：RBAC 模型，支持角色和权限的动态配置
3. **API 网关**：FastAPI + 速率限制 + 请求日志

### 技术选择
| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 编排 | LangGraph | 有状态图编排 + 流式输出 |
| 前端框架 | Next.js 14 | SSR + API Routes + 生态完善 |
| 数据库 | PostgreSQL | 事务支持 + JSONB + 全文搜索 |
| 缓存 | Redis | 高性能 + 数据结构丰富 |

### 关键代码位置
- Agent 核心逻辑：`backend/packages/harness/kkoclaw/`
- 认证中间件：`backend/app/gateway/middleware/auth.py`
- 前端状态管理：`frontend/src/stores/`
- 配置文件：`config.yaml` / `.env`
```

### 3. 维护注意事项

```markdown
## 维护注意事项

### 定期操作
- 数据库 VACUUM：每周执行
- 日志清理：每日执行（超过 30 天的日志）
- SSL 证书续期：每 90 天检查
- 依赖安全扫描：每周执行

### 注意事项
- 修改 `config.yaml` 后需要重启服务
- 数据库 migration 必须向前兼容
- 前端构建后需要清理 `.next/cache`
- WebSocket 连接数限制为 1000/实例

### 监控关键指标
- API P95 延迟 < 500ms
- 错误率 < 1%
- CPU 使用率 < 80%
- 磁盘空间 > 20% 可用
```

### 4. 已知问题和风险

```markdown
## 已知问题

| 问题 | 严重程度 | 影响 | 临时方案 |
|------|---------|------|---------|
| 大量并发时 WebSocket 断连 | Medium | 用户需要重连 | 前端自动重连已实现 |
| 搜索功能不支持中文分词 | Low | 中文搜索结果不精确 | 可后续接入 Elasticsearch |
| 日志文件增长过快 | Medium | 磁盘空间 | 已配置 logrotate |
```

### 5. 后续改进建议

```markdown
## 后续改进建议

### P0 - 必须做
- [ ] 添加数据库读写分离
- [ ] 实现消息队列异步处理

### P1 - 建议做
- [ ] 接入 APM（如 Datadog / Sentry）
- [ ] 添加 API 速率限制（目前只有基础版）
- [ ] 前端性能优化（代码分割 + 图片优化）

### P2 - 可选
- [ ] 支持多语言（i18n）
- [ ] 添加 GraphQL API
- [ ] 移动端适配
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 编写交接文档 |
| `read_file` | 回顾项目代码，确保文档准确 |
| `git_log` | 查看 commit 历史，梳理变更 |
| `grep` | 查找 TODO/FIXME/HACK 标记 |

## 检查清单

- [ ] 项目概述清晰（一句话能说清楚做什么）
- [ ] 架构图和核心模块说明
- [ ] 关键设计决策有记录
- [ ] 本地开发和部署步骤可执行
- [ ] 已知问题诚实列出
- [ ] 后续改进建议有优先级
- [ ] 关键代码位置标注
- [ ] 维护注意事项涵盖日常操作

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 只列实现不讲设计 | 重点讲架构决策和约束 |
| 隐藏已知问题 | 诚实列出并标注严重程度 |
| 后续计划模糊 | 具体可执行的待办清单 |
| 不标关键代码位置 | 列出核心文件和模块路径 |
| 过于详细像说明书 | 重点突出，细节有链接 |

## 输出要求

1. 提供完整的交接文档
2. 包含实现摘要（功能 + 技术选择 + 代码位置）
3. 列出已知问题和风险
4. 提供后续改进建议（按优先级）
5. 标注维护注意事项
---
name: handoff-docs
description: >-
  Use this skill when preparing project handoff documentation, implementation
  summaries, maintenance notes, known limitations, next steps, or onboarding
  material for another engineer or user.
work_modes: [coding]
---

