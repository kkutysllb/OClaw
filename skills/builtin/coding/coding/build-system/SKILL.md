---
name: build-system
description: >-
  Use this skill for build tooling, package scripts, monorepo workspaces,
  bundlers, TypeScript compilation, Python packaging, task runners, and build
  failures.
work_modes: [coding]
---

# Build System

## 适用场景

- 配置或修复构建工具链（Webpack / Vite / Turbopack / tsc / setuptools / uv）
- 管理项目构建脚本（package.json scripts / Makefile / pyproject.toml）
- 配置 monorepo workspace（pnpm workspace / turborepo / nx）
- 排查构建失败、构建性能优化

## 核心原则

1. **确定性**：相同输入产生相同输出，构建结果可复现
2. **快速增量**：只重新构建变更的部分，支持增量编译
3. **清晰报错**：构建失败时错误信息清晰可定位
4. **开发体验**：dev 模式有 HMR，构建模式有 source map
5. **锁定版本**：依赖版本锁定，避免构建环境差异

## 执行流程

### 1. 分析构建配置

- 前端：`next.config.js` / `vite.config.ts` / `webpack.config.js`
- 后端：`pyproject.toml` / `setup.py` / `Makefile`
- Monorepo：`pnpm-workspace.yaml` / `turbo.json` / `nx.json`

### 2. 前端构建

#### Next.js / Vite

```javascript
// next.config.js 关键配置
module.exports = {
  // 构建优化
  swcMinify: true,
  poweredByHeader: false,

  // 路径别名
  webpack: (config) => {
    config.resolve.alias['@'] = path.join(__dirname, 'src');
    return config;
  },

  // 环境变量
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};
```

#### TypeScript 编译

```json
// tsconfig.json 关键配置
{
  "compilerOptions": {
    "strict": true,              // 严格模式
    "noEmit": false,             // 构建时输出 JS
    "sourceMap": true,           // 生成 source map
    "incremental": true,         // 增量编译
    "paths": { "@/*": ["./src/*"] }
  }
}
```

### 3. 后端构建

#### Python 打包

```toml
# pyproject.toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 4. Monorepo Workspace

```yaml
# pnpm-workspace.yaml
packages:
  - 'frontend'
  - 'backend'
  - 'desktop-electron'
  - 'packages/*'
```

```json
// turbo.json - 构建管道
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "test": {
      "dependsOn": ["build"]
    }
  }
}
```

### 5. 构建脚本管理

```json
// package.json scripts 规范
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  }
}
```

```makefile
# Makefile 规范
.PHONY: dev build test lint clean

dev:
\tuvicorn gateway_main:app --reload

build:
\tpython -m build

test:
\tpytest tests/ -v

lint:
\truff check . && ruff format --check .

clean:
\trm -rf dist build .pytest_cache
```

### 6. 构建失败排查

| 错误类型 | 排查方向 |
|---------|---------|
| **模块未找到** | 检查 import 路径 / 路径别名 / 依赖安装 |
| **类型错误** | 运行 `tsc --noEmit` 定位类型问题 |
| **内存溢出** | 增加 Node.js 内存 `NODE_OPTIONS=--max-old-space-size=4096` |
| **构建太慢** | 分析构建 `ANALYZE=true next build` / 启用缓存 |
| **环境差异** | 检查 Node/Python 版本一致性 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看构建配置文件 |
| `write_file` / `apply_diff` | 修改构建配置 |
| Bash | 运行构建命令、查看构建输出 |
| `run_tests` | 验证构建产物 |

## 检查清单

- [ ] 构建配置正确（前端 bundler + 后端 packaging）
- [ ] TypeScript / Python 类型检查通过
- [ ] 构建脚本清晰规范（dev/build/test/lint）
- [ ] 路径别名配置正确
- [ ] 环境变量在构建时正确注入
- [ ] 构建产物可用（dist/.next/build）
- [ ] 无构建警告（或已处理）
- [ ] 构建可重复（lockfile 锁定版本）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 构建配置散落多处 | 统一在一个配置文件中管理 |
| 构建脚本含义不清 | 脚本名语义化 + 文档说明 |
| 忽略构建警告 | 每个警告都检查并处理 |
| 不锁定依赖版本 | 使用 lockfile 锁定 |
| dev 和 build 配置混用 | 分离 dev/build 配置 |

## 输出要求

1. 提供正确的构建配置文件
2. 说明构建流程和命令
3. 列出构建产物和部署路径
4. 标注关键配置项的作用
5. 提供构建失败排查指南
---
name: build-system
description: >-
  Use this skill for build tooling, package scripts, monorepo workspaces,
  bundlers, TypeScript compilation, Python packaging, task runners, and build
  failures.
work_modes: [coding]
---

