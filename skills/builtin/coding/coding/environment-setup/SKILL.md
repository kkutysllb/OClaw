---
name: environment-setup
description: >-
  Use this skill when setting up local development, environment variables,
  dependency installation, dev servers, Docker/devcontainers, secrets templates,
  or onboarding commands.
work_modes: [coding]
---

# Environment Setup

## 适用场景

- 新成员 onboarding：从零搭建本地开发环境
- 配置环境变量、secrets 模板
- 修复"在我机器上跑不了"的环境问题
- 配置 Docker 开发环境 / devcontainer

## 核心原则

1. **一键启动**：理想状态是克隆后一条命令启动所有服务
2. **版本锁定**：Python/Node/系统依赖版本明确指定
3. **配置模板化**：`.env.example` 提供所有必需变量的模板
4. **文档即代码**：SETUP 文档与项目代码同步维护
5. **可验证**：提供健康检查命令确认环境就绪

## 执行流程

### 1. 依赖安装

```bash
# 前端（pnpm）
pnpm install

# 后端（uv）
cd backend && uv sync

# 全栈 monorepo
pnpm install && cd backend && uv sync
```

### 2. 环境变量配置

```bash
# .env.example（入 Git，不含真实值）
# === Database ===
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379

# === Auth ===
JWT_SECRET=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256

# === API Keys ===
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>

# === Frontend ===
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# 复制并填充
cp .env.example .env
# 填入真实值后...
```

### 3. 开发服务器

```bash
# 前端 dev server
pnpm dev          # Next.js → http://localhost:3000

# 后端 dev server
cd backend
uv run uvicorn gateway_main:app --reload --port 8000

# 或通过 Makefile
make dev-frontend
make dev-backend
make dev-all       # 同时启动前后端
```

### 4. Docker 开发环境

```yaml
# docker-compose-dev.yaml
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports: ["6379:6379"]

  nginx:
    image: nginx:latest
    ports: ["80:80"]
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
```

### 5. 数据库初始化

```bash
# 启动数据库
docker compose -f docker-compose-dev.yaml up -d postgres

# 执行 migration
cd backend
alembic upgrade head

# 导入测试数据（可选）
python scripts/load_memory_sample.py
```

### 6. 验证环境就绪

```bash
# 健康检查
curl http://localhost:8000/health     # 后端
curl http://localhost:3000            # 前端

# 运行测试确认环境正常
cd backend && pytest tests/ -x -q
cd frontend && pnpm test

# 运行 lint 确认工具链正常
cd backend && ruff check .
cd frontend && pnpm lint
```

### 7. 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 端口被占用 | 其他进程占用 | `lsof -i :3000` 找到并 kill |
| 模块未找到 | 依赖未安装 | `pnpm install` / `uv sync` |
| 数据库连接失败 | PostgreSQL 未启动 | `docker compose up -d postgres` |
| Python 版本不对 | pyenv 未切换 | `pyenv local 3.11` |
| Node 版本不对 | nvm 未切换 | `nvm use 20` |
| CORS 错误 | 前后端 URL 不匹配 | 检查 `.env` 中的 API URL |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` / `apply_diff` | 创建/修改配置文件、SETUP 文档 |
| Bash | 安装依赖、启动服务、验证环境 |
| `read_file` | 查看现有配置 |

## 检查清单

- [ ] 所有依赖可一键安装（pnpm install / uv sync）
- [ ] `.env.example` 包含所有必需变量
- [ ] 数据库和中间件可通过 Docker 启动
- [ ] 前后端 dev server 可正常启动
- [ ] 健康检查通过
- [ ] 测试可通过
- [ ] SETUP 文档与实际环境一致

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 没有环境变量模板 | `.env.example` 列出所有变量 |
| 手动安装系统依赖 | Docker 提供一致环境 |
| 没有验证步骤 | 提供健康检查命令 |
| SETUP 文档过时 | 文档与配置同步维护 |
| 版本不明确 | `python_requires` / `engines.node` 锁定 |

## 输出要求

1. 提供完整的环境搭建步骤（从克隆到运行）
2. 提供环境变量模板（`.env.example`）
3. 提供 Docker 开发环境配置（如需要）
4. 提供验证命令确认环境就绪
5. 列出常见问题及解决方案
---
name: environment-setup
description: >-
  Use this skill when setting up local development, environment variables,
  dependency installation, dev servers, Docker/devcontainers, secrets templates,
  or onboarding commands.
work_modes: [coding]
---

