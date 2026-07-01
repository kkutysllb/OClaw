---
name: release-engineering
description: >-
  Use this skill for versioning, changelogs, release notes, packaging,
  deployment readiness, rollback planning, and release risk checks.
work_modes: [coding]
---

# Release Engineering

## 适用场景

- 版本发布前的准备工作（版本号、changelog、release notes）
- 打包发布（npm publish / PyPI / Docker image / Electron build）
- 发布风险评估和回滚规划
- 多组件协同发布

## 核心原则

1. **语义化版本**：严格遵循 SemVer（MAJOR.MINOR.PATCH）
2. **变更可追溯**：每个版本都有详细的 changelog
3. **发布前验证**：所有 CI 检查通过 + 冒烟测试通过
4. **风险可控**：评估变更影响，制定回滚方案
5. **发布可重复**：发布过程自动化，不依赖手动操作

## 执行流程

### 1. 版本号决策

```
遵循 Semantic Versioning：
- MAJOR (x.0.0)：不兼容的 API 变更
- MINOR (1.x.0)：向后兼容的新功能
- PATCH (1.0.x)：向后兼容的 bug 修复

判断流程：
1. 有 breaking change？ → MAJOR +1, MINOR=0, PATCH=0
2. 有新功能？ → MINOR +1, PATCH=0
3. 只有 bug 修复？ → PATCH +1
```

### 2. 生成 Changelog

```markdown
## [1.2.0] - 2025-07-01

### Added
- 新增用户导出功能 (#123)
- 新增暗黑模式 (#125)

### Changed
- 重构认证模块，使用 JWT 替代 session (#120)

### Fixed
- 修复登录页面在 Safari 下的样式问题 (#128)
- 修复大数据量下分页计算错误 (#130)

### Deprecated
- `oldApiEndpoint` 将在 2.0.0 移除，请使用 `newApiEndpoint`

### Removed
- 移除已废弃的 v1 API 端点

### Security
- 修复 SSRF 漏洞 (#127)
```

### 3. 发布前检查清单

| 检查项 | 状态 |
|-------|------|
| CI 全部通过（lint/test/build） | ☐ |
| 版本号已更新（package.json / pyproject.toml） | ☐ |
| Changelog 已更新 | ☐ |
| Git tag 已创建 | ☐ |
| Breaking changes 已标注 | ☐ |
- Deprecated 功能已记录 | ☐ |
- 安全扫描通过 | ☐ |
- 冒烟测试通过 | ☐ |
- 回滚方案已准备 | ☐ |

### 4. 打包发布

```bash
# npm 发布
npm version 1.2.0
npm run build
npm publish --access public

# Python 发布
bumpversion --new-version 1.2.0 patch
rm -rf dist && python -m build
twine upload dist/*

# Docker 发布
docker build -t app:1.2.0 -t app:latest .
docker push app:1.2.0
docker push app:latest

# Electron 打包
pnpm run build:electron
electron-builder --publish always
```

### 5. 发布流程

```
1. 创建 release 分支 (git checkout -b release/1.2.0)
2. 更新版本号和 changelog
3. 运行完整 CI 验证
4. 创建 Git tag (git tag v1.2.0)
5. 推送 tag 触发发布 CI
6. 验证发布产物
7. 发布 Release Notes
8. 合并 release 分支到 main
```

### 6. 回滚规划

- 如果发布后发现严重问题：
  1. 评估影响范围
  2. 如果可快速修复 → 发布 hotfix（PATCH 版本）
  3. 如果无法快速修复 → 回退到上一个稳定版本
- 回退步骤：
  ```bash
  git tag -d v1.2.0
  git push origin :refs/tags/v1.2.0
  docker pull app:1.1.9  # 上一个稳定版本
  docker tag app:1.1.9 app:latest
  ```

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash | 执行版本号更新、打包、发布命令 |
| `read_file` / `apply_diff` | 更新版本号、changelog |
| `git_status` / `git_log` | 查看自上次发布以来的变更 |
| `run_tests` | 发布前全量测试验证 |

## 检查清单

- [ ] 版本号遵循 SemVer 规范
- [ ] Changelog 覆盖所有重要变更
- [ ] Breaking changes 已标注并提供迁移指南
- [ ] CI 全部通过
- [ ] Git tag 已创建
- [ ] 发布产物已验证
- [ ] Release Notes 已发布
- [ ] 回滚方案已准备

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 随意改版本号 | 严格遵循 SemVer |
| 没有 changelog | 每个版本都有详细变更记录 |
| 发布前不跑测试 | 完整 CI 验证 + 冒烟测试 |
| Breaking change 不标注 | 明确标注并提供迁移指南 |
| 手动发布 | CI 自动化发布流程 |
| 没有回滚方案 | 每次发布都有回退预案 |

## 输出要求

1. 提供版本号决策理由
2. 提供完整的 Changelog
3. 提供发布前检查清单（全部通过）
4. 说明打包和发布命令
5. 提供回滚方案
---
name: release-engineering
description: >-
  Use this skill for versioning, changelogs, release notes, packaging,
  deployment readiness, rollback planning, and release risk checks.
work_modes: [coding]
---

