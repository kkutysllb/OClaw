---
name: deployment
description: >-
  Use this skill when preparing deployment, hosting configuration, environment
  variables, build artifacts, release rollout, smoke checks, or rollback
  strategy.
work_modes: [coding]
---

# Deployment

## 适用场景

- 配置部署流程（Docker / Kubernetes / Vercel / VPS）
- 管理环境变量、secrets、配置文件
- 执行发布 rollout 和冒烟测试
- 制定回滚策略

## 核心原则

1. **可重复**：部署过程完全自动化，不依赖手动步骤
2. **环境隔离**：dev / staging / production 配置严格分离
3. **零停机**：优先使用滚动部署或蓝绿部署
4. **可回滚**：每次部署都有明确的回滚方案
5. **冒烟验证**：部署后立即验证关键功能，快速发现问题

## 执行流程

### 1. 准备部署清单

- 确认构建产物正确（已通过 CI 全部检查）
- 确认环境变量和 secrets 已配置
- 确认数据库 migration 已准备
- 确认回滚方案就绪

### 2. 部署策略选择

| 策略 | 适用场景 | 优点 | 风险 |
|------|---------|------|------|
| **滚动更新** | K8s / Docker Swarm | 零停机、渐进 | 短暂版本共存 |
| **蓝绿部署** | 需要快速回滚 | 秒级切换、秒级回滚 | 需要双倍资源 |
| **金丝雀** | 高风险变更 | 渐进暴露风险 | 配置复杂 |
| **重建** | 简单项目 | 简单 | 有停机时间 |

### 3. 环境变量管理

```yaml
# .env.production（不入 Git）
DATABASE_URL=postgresql://...
JWT_SECRET=<random-64-chars>
API_KEY=<from-secret-manager>

# docker-compose.prod.yaml
services:
  app:
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    env_file:
      - .env.production
```

- 生产 secrets 从 Secret Manager / CI Secrets 注入
- `.env.example` 只包含键名不包含值
- 不同环境使用不同的 `.env` 文件

### 4. 数据库 Migration

```bash
# 部署前执行 migration
alembic upgrade head    # Python
npx prisma migrate deploy  # Node.js

# 确认 migration 是向前兼容的（不破坏旧版本）
```

### 5. 部署执行

```bash
# Docker 部署
docker compose -f docker-compose.prod.yaml up -d

# Kubernetes 部署
kubectl apply -f k8s/
kubectl rollout status deployment/app

# Vercel 部署
vercel --prod
```

### 6. 冒烟测试

部署后立即验证：

| 检查项 | 方法 |
|-------|------|
| 服务存活 | `curl https://app.com/health` 返回 200 |
| 数据库连接 | 查询一个简单记录 |
| 关键 API | 核心端点返回正确数据 |
| 前端加载 | 页面可访问，无白屏 |
| 日志正常 | 无错误级别日志 |

### 7. 回滚策略

```bash
# Docker 回滚
docker compose -f docker-compose.prod.yaml down
docker tag app:previous app:latest
docker compose -f docker-compose.prod.yaml up -d

# Kubernetes 回滚
kubectl rollout undo deployment/app

# 数据库回滚（如果 migration 有问题）
alembic downgrade -1
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看部署配置文件 |
| `write_file` / `apply_diff` | 创建/修改部署配置 |
| Bash | 执行部署命令、冒烟测试 |
| `run_tests` | 部署前验证 |

## 检查清单

- [ ] 构建产物已通过 CI 全部检查
- [ ] 环境变量/secrets 已在目标环境配置
- [ ] 数据库 migration 已测试（向前兼容）
- [ ] 部署脚本可重复执行
- [ ] 冒烟测试通过（health check + 关键 API）
- [ ] 回滚方案已准备并测试
- [ ] 日志可观测（无异常错误）
- [ ] 生产 secrets 不在代码仓库中

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 手动 SSH 部署 | 自动化部署脚本/CI |
| 生产 secret 提交到 Git | Secret Manager / CI Secrets |
| 部署后不验证 | 立即执行冒烟测试 |
| 没有回滚方案 | 每次部署都有回滚预案 |
| dev/prod 配置混用 | 环境严格隔离 |
| migration 破坏旧版本 | 向前兼容 migration |

## 输出要求

1. 提供部署配置文件（Dockerfile / docker-compose / k8s yaml）
2. 列出环境变量清单（键名 + 说明 + 来源）
3. 说明部署步骤和命令
4. 提供冒烟测试方案
5. 提供回滚方案
---
name: deployment
description: >-
  Use this skill when preparing deployment, hosting configuration, environment
  variables, build artifacts, release rollout, smoke checks, or rollback
  strategy.
work_modes: [coding]
---

