---
name: project-scaffolding
description: >-
  Use this skill when creating a new project structure, package layout,
  initial app skeleton, routes, service layers, test directories, or starter
  configuration.
work_modes: [coding]
---

# Project Scaffolding

## 适用场景

- 从零创建新项目（前端、后端、全栈）
- 搭建项目初始结构和目录布局
- 初始化配置文件（ESLint / Prettier / ruff / tsconfig / pyproject）
- 搭建测试框架和 CI 基础

## 核心原则

1. **约定优于配置**：遵循社区标准的目录结构和命名约定
2. **最小可用**：脚手架生成后立即可运行（`dev` 可启动、`test` 可跑）
3. **工具链完备**：lint + format + typecheck + test 一条龙配置
4. **可扩展**：目录结构支持后续增长，不需要大规模重构
5. **文档就绪**：README 有快速开始指南

## 执行流程

### 1. 前端项目脚手架（Next.js）

```
project/
├── src/
│   ├── app/              # App Router 页面
│   │   ├── layout.tsx    # 根布局
│   │   ├── page.tsx      # 首页
│   │   └── api/          # API Routes
│   ├── components/        # 可复用组件
│   │   ├── ui/           # 基础 UI 组件
│   │   └── features/     # 功能组件
│   ├── hooks/            # 自定义 Hooks
│   ├── lib/              # 工具函数
│   ├── stores/           # 状态管理
│   └── types/            # TypeScript 类型
├── public/               # 静态资源
├── tests/                # 测试
│   ├── unit/
│   └── e2e/
├── .env.example          # 环境变量模板
├── next.config.js
├── tsconfig.json
├── package.json
└── README.md
```

### 2. 后端项目脚手架（FastAPI）

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py           # 应用入口
│   ├── gateway/          # API 路由
│   │   ├── __init__.py
│   │   ├── routers/      # 路由模块
│   │   └── middleware/    # 中间件
│   ├── models/           # 数据模型
│   ├── services/         # 业务逻辑
│   ├── schemas/          # 请求/响应 schema
│   ├── core/             # 核心配置
│   │   ├── config.py     # 配置管理
│   │   ├── security.py   # 安全工具
│   │   └── database.py   # 数据库连接
│   └── utils/            # 工具函数
├── tests/
│   ├── conftest.py       # 测试 fixtures
│   ├── unit/
│   └── integration/
├── alembic/              # 数据库迁移
├── pyproject.toml
├── Makefile
└── README.md
```

### 3. 全栈 Monorepo 脚手架

```
project/
├── frontend/             # 前端
├── backend/              # 后端
├── desktop-electron/     # 桌面应用（可选）
├── docker/               # Docker 配置
│   ├── nginx/
│   └── docker-compose.yaml
├── docs/                 # 文档
├── scripts/              # 脚本
├── .github/workflows/    # CI/CD
├── pnpm-workspace.yaml   # Monorepo 配置
├── Makefile              # 顶层命令
├── .env.example
└── README.md
```

### 4. 配置文件初始化

#### 前端

```json
// package.json scripts
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint . --fix",
    "format": "prettier --write .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  }
}
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "incremental": true,
    "sourceMap": true
  }
}
```

#### 后端

```toml
# pyproject.toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

```makefile
# Makefile
.PHONY: dev build test lint format clean

dev:
\tuvicorn app.main:app --reload

test:
\tpytest tests/ -v --cov=app

lint:
\truff check . && ruff format --check .

format:
\truff format .

clean:
\trm -rf __pycache__ .pytest_cache .ruff_cache
```

### 5. 环境变量模板

```bash
# .env.example
# === App ===
APP_ENV=development
APP_PORT=8000

# === Database ===
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# === Auth ===
JWT_SECRET=change-me-in-production

# === External APIs ===
API_KEY=your-api-key
```

### 6. 验证脚手架

```bash
# 前端
pnpm install && pnpm dev      # 可启动
pnpm test                     # 测试可跑
pnpm lint                     # Lint 可跑
pnpm typecheck                # 类型检查可跑

# 后端
uv sync && uv run uvicorn app.main:app  # 可启动
uv run pytest tests/                     # 测试可跑
uv run ruff check .                      # Lint 可跑
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 创建项目文件和配置 |
| Bash | 初始化项目（CLI 工具） |
| `read_file` | 参考现有项目结构 |

## 检查清单

- [ ] 目录结构遵循社区约定
- [ ] 配置文件完备（lint/format/typecheck/test）
- [ ] `dev` 命令可启动
- [ ] `test` 命令可运行
- [ ] `lint` 命令可运行
- [ ] `.env.example` 模板已创建
- [ ] README 有快速开始指南
- [ ] `.gitignore` 配置正确
- [ ] CI 基础配置已搭建（如需要）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 过度设计目录结构 | 遵循社区标准，够用就好 |
| 只创建代码不配工具链 | lint + format + test 一并配置 |
| 没有 `.env.example` | 创建模板让其他人知道需要什么变量 |
| 所有代码在一个目录 | 按职责分目录（routes/models/services） |
| 不验证就交付 | 创建后立即验证可运行 |

## 输出要求

1. 提供完整的目录结构
2. 提供所有配置文件
3. 提供环境变量模板
4. 验证 `dev` / `test` / `lint` 命令可运行
5. 提供 README 快速开始
---
name: project-scaffolding
description: >-
  Use this skill when creating a new project structure, package layout,
  initial app skeleton, routes, service layers, test directories, or starter
  configuration.
work_modes: [coding]
---

