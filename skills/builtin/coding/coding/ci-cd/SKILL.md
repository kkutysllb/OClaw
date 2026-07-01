---
name: ci-cd
description: >-
  Use this skill for CI pipelines, build scripts, test workflows, lint/typecheck
  gates, release jobs, caching, artifacts, and environment setup.
work_modes: [coding]
---

# CI/CD Pipeline

## 适用场景

- 创建或修改 CI/CD 流水线配置（GitHub Actions / GitLab CI / Jenkins）
- 配置构建、测试、lint、typecheck 门禁
- 优化 CI 缓存策略、并行执行、构建产物管理
- 排查 CI 失败、流水线性能问题

## 核心原则

1. **快速反馈**：CI 应在 5-10 分钟内给出结果，关键检查优先
2. **失败即阻塞**：lint/typecheck/test 失败必须阻止合并
3. **缓存优先**：依赖缓存 + 构建缓存，避免重复下载和编译
4. **环境隔离**：CI 环境与开发/生产环境一致，避免"本地能跑 CI 不行"
5. **可观测**：CI 日志清晰可读，失败原因一目了然

## 执行流程

### 1. 分析现有流水线

- 查看现有 CI 配置文件（`.github/workflows/`、`.gitlab-ci.yml`、`Jenkinsfile`）
- 识别阶段：lint → typecheck → build → test → e2e → deploy
- 找出瓶颈：哪个阶段最慢？哪个最常失败？

### 2. 标准 CI 流水线设计

```yaml
# GitHub Actions 示例结构
jobs:
  lint:        # 最快，先跑
    - ESLint / Ruff
    - Prettier / Black 格式检查
  typecheck:   # 类型安全
    - tsc --noEmit
    - mypy / pyright
  build:       # 构建验证
    - npm run build / pip build
    - 构建产物上传
  test:        # 单元 + 集成测试
    - pytest / vitest
    - 覆盖率报告
  e2e:         # 端到端（可选，较慢）
    - Playwright
  deploy:      # 部署（仅 main 分支）
    - 条件触发
```

### 3. 门禁规则

| 门禁 | 触发条件 | 失败处理 |
|------|---------|---------|
| Lint 通过 | 每次 PR | ❌ 阻止合并 |
| TypeCheck 通过 | 每次 PR | ❌ 阻止合并 |
| 单元测试通过 | 每次 PR | ❌ 阻止合并 |
| 构建成功 | 每次 PR | ❌ 阻止合并 |
| E2E 通过 | main 分支 | ⚠️ 警告但不阻塞 |
| 覆盖率不降 | 每次 PR | ⚠️ 警告 |

### 4. 缓存优化

```yaml
# 依赖缓存
- name: Cache node_modules
  uses: actions/cache@v3
  with:
    path: node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('pnpm-lock.yaml') }}

# Python 缓存
- name: Cache pip
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('uv.lock') }}

# 构建缓存（Next.js）
- name: Cache .next
  uses: actions/cache@v3
  with:
    path: .next/cache
    key: next-${{ hashFiles('pnpm-lock.yaml') }}-${{ hashFiles('**/*.ts') }}
```

### 5. 并行化

- 将独立 job 并行执行（lint / typecheck / test 可同时跑）
- 测试分片：`pytest --shard-id ${{ matrix.shard }}` 分散执行
- 使用 matrix 策略多版本测试（Python 3.11/3.12、Node 18/20）

### 6. 产物管理

- 构建产物上传到 artifact store
- Docker 镜像推送到 registry
- 版本号与 commit hash 关联

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看现有 CI 配置 |
| `write_file` / `apply_diff` | 创建/修改 CI 配置 |
| Bash | 本地验证 CI 步骤（act / 本地运行 lint/test） |
| `run_tests` / `run_linter` | 验证 CI 步骤本地可过 |

## 检查清单

- [ ] Lint 门禁配置正确
- [ ] TypeCheck 门禁配置正确
- [ ] 单元测试门禁配置正确
- [ ] 构建步骤验证通过
- [ ] 依赖缓存配置正确
- [ ] 并行化已优化
- [ ] 失败时日志清晰可读
- [ ] 部署只在正确分支触发
- [ ] Secrets 通过 CI secrets 注入（不硬编码）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| CI 跑 30 分钟 | 并行化 + 缓存，目标 < 10 分钟 |
| 失败信息不清晰 | 每步输出清晰的标题和结果 |
| 所有步骤串行 | 独立步骤并行执行 |
| 不缓存依赖 | 缓存 lockfile 对应的依赖 |
| Secret 写在 YAML | 用 CI secrets 环境变量 |
| CI 过了但生产挂了 | CI 环境与生产环境一致 |

## 输出要求

1. 提供完整的 CI 配置文件
2. 说明每个 job 的作用和触发条件
3. 标注缓存策略和并行化方案
4. 列出门禁规则
5. 提供本地验证方法
---
name: ci-cd
description: >-
  Use this skill for CI pipelines, build scripts, test workflows, lint/typecheck
  gates, release jobs, caching, artifacts, and environment setup.
work_modes: [coding]
---

