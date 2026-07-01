---
name: operations-runbook
description: >-
  Use this skill when creating operational runbooks, support docs, incident
  response steps, monitoring notes, backup/restore guidance, or maintenance
  procedures.
work_modes: [coding]
---

# Operations Runbook

## 适用场景

- 创建运维手册（部署、监控、故障排查、备份恢复）
- 编写事件响应流程（告警处理、故障定位、恢复步骤）
- 制定维护操作规范（日常巡检、定期维护、容量规划）

## 核心原则

1. **可执行**：每个步骤都是具体可执行的命令，不是抽象描述
2. **可追溯**：记录操作时间、执行人、操作结果
3. **分级响应**：按严重程度分 P0-P3，不同级别不同响应标准
4. **预防优先**：日常监控和巡检比事后救火更重要
5. **持续更新**：每次事件后更新 runbook，沉淀经验

## 执行流程

### 1. 运维手册结构

```markdown
# [系统名] Operations Runbook

## 1. 系统概述
- 架构图
- 关键组件
- 依赖关系

## 2. 日常运维
### 2.1 健康检查
### 2.2 日志查看
### 2.3 监控面板

## 3. 部署操作
### 3.1 常规部署
### 3.2 回滚操作

## 4. 事件响应
### 4.1 P0 - 系统不可用
### 4.2 P1 - 核心功能异常
### 4.3 P2 - 非核心功能异常

## 5. 备份与恢复

## 6. 维护计划
```

### 2. 健康检查

```bash
# 服务存活检查
curl -f http://localhost:8000/health || echo "BACKEND DOWN"

# 进程检查
ps aux | grep -E "uvicorn|next" | grep -v grep

# 端口检查
lsof -i :8000  # 后端
lsof -i :3000  # 前端
lsof -i :5432  # 数据库
lsof -i :6379  # Redis

# 磁盘空间
df -h | grep -E "^/dev"

# 内存使用
free -h
```

### 3. 日志查看

```bash
# 实时日志
tail -f logs/gateway.log
tail -f logs/frontend.log

# 错误日志
grep -i "error\|exception\|traceback" logs/gateway.log | tail -50

# 特定时间段
awk '/2025-07-01 10:00/,/2025-07-01 11:00/' logs/gateway.log

# Docker 日志
docker compose logs -f --tail=100 gateway
```

### 4. 事件响应流程

#### P0 - 系统不可用（响应时间：立即）

```
1. 确认影响范围（全站？部分功能？）
2. 检查服务状态：
   - curl health endpoints
   - 检查进程存活
   - 检查数据库连接
3. 尝试快速恢复：
   - 重启服务：docker compose restart gateway
   - 回滚到上一版本
4. 如果无法快速恢复：
   - 通知相关人员
   - 启动详细排查
5. 恢复后验证：
   - 冒烟测试
   - 确认监控恢复正常
6. 编写事件报告
```

#### P1 - 核心功能异常（响应时间：15分钟）

```
1. 复现问题（确认影响范围）
2. 查看相关日志和监控
3. 定位根因
4. 修复或临时缓解
5. 验证修复
6. 记录事件
```

### 5. 备份与恢复

```bash
# 数据库备份
pg_dump -U user -d dbname > backups/db_$(date +%Y%m%d_%H%M%S).sql

# 数据库恢复
psql -U user -d dbname < backups/db_20250701_120000.sql

# 配置文件备份
cp config.yaml config.yaml.bak.$(date +%Y%m%d)

# Redis 备份
redis-cli SAVE
cp /var/lib/redis/dump.rdb backups/redis_$(date +%Y%m%d).rdb
```

### 6. 维护操作

| 操作 | 频率 | 命令 |
|------|------|------|
| 日志轮转 | 每日 | `logrotate /etc/logrotate.d/oclaw` |
| 磁盘清理 | 每周 | `find /tmp -mtime +7 -delete` |
| 数据库 VACUUM | 每周 | `vacuumdb --analyze -U user dbname` |
| 依赖安全扫描 | 每周 | `pip audit` / `npm audit` |
| SSL 证书检查 | 每月 | `openssl s_client -connect host:443` |
| 备份验证 | 每月 | 从备份恢复到测试环境验证 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 编写运维手册 |
| Bash | 执行运维命令、健康检查 |
| `read_file` | 查看配置文件、日志 |

## 检查清单

- [ ] 系统架构图和组件清单已文档化
- [ ] 健康检查命令可执行
- [ ] 日志查看方法已说明
- [ ] 部署和回滚步骤已文档化
- [ ] 事件响应流程按 P0-P3 分级
- [ ] 备份和恢复步骤已验证
- [ ] 维护计划有明确频率和命令

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| "检查一下服务" | 具体的 `curl` / `ps` / `lsof` 命令 |
| 没有事件分级 | 按 P0-P3 分级，明确响应标准 |
| 备份不验证恢复 | 定期从备份恢复到测试环境 |
| 事件后不更新 runbook | 每次事件后补充经验 |
| 只靠事后救火 | 日常监控和巡检 |

## 输出要求

1. 提供结构化的运维手册
2. 每个操作步骤都是可执行的命令
3. 事件响应按严重程度分级
4. 备份恢复方案已验证
5. 维护计划有明确频率
---
name: operations-runbook
description: >-
  Use this skill when creating operational runbooks, support docs, incident
  response steps, monitoring notes, backup/restore guidance, or maintenance
  procedures.
work_modes: [coding]
---

