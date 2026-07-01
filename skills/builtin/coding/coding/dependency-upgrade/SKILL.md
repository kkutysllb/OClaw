---
name: dependency-upgrade
description: >-
  Use this skill for dependency upgrades, package manager changes, vulnerability
  remediation, lockfile updates, SDK migrations, and version compatibility work.
work_modes: [coding]
---

# Dependency Upgrade

## 适用场景

- 升级项目依赖（框架、库、工具链）
- 修复有安全漏洞的依赖
- 包管理器迁移（npm→pnpm、pip→uv）
- SDK 版本迁移（API v1→v2）

## 核心原则

1. **最小变更**：一次只升级一个依赖，便于定位问题
2. **锁定版本**：升级后更新 lockfile，确保可复现
3. **测试驱动**：升级后必须运行完整测试套件验证
4. **渐进升级**：大版本升级分步进行（先 minor，再 major）
5. **记录变更**：记录升级原因、版本变化、兼容性调整

## 执行流程

### 1. 评估升级需求

```bash
# 检查过时的依赖
npm outdated          # npm/pnpm
pip list --outdated   # Python

# 检查安全漏洞
npm audit             # npm/pnpm
pip audit             # Python
safety check          # Python（备选）

# 查看当前版本
cat package.json | grep -A 5 dependencies
cat pyproject.toml | grep -A 10 dependencies
```

### 2. 升级策略

| 场景 | 策略 | 风险 |
|------|------|------|
| Patch 升级（1.2.3→1.2.4） | 直接升级，运行测试 | 🟢 低风险 |
| Minor 升级（1.2→1.3） | 查看 changelog，升级，测试 | 🟡 中风险 |
| Major 升级（1.x→2.x） | 阅读 migration guide，逐项适配 | 🔴 高风险 |
| 安全漏洞修复 | 优先升级到修复版本 | 🔴 紧急 |

### 3. 执行升级

#### Patch/Minor 升级

```bash
# pnpm
pnpm update package-name
pnpm test  # 验证

# uv
uv pip install --upgrade package-name
pytest tests/  # 验证
```

#### Major 升级

```bash
# 1. 创建专用分支
git checkout -b upgrade/nextjs-15

# 2. 阅读 migration guide
# https://nextjs.org/docs/app/building-your-application/upgrading

# 3. 升级主版本
pnpm add next@15 react@19

# 4. 运行 codemod（如果有）
npx @next/codemod@latest upgrade

# 5. 逐个修复 breaking changes
# 6. 运行完整测试
pnpm test && pnpm build

# 7. 手动验证关键功能
```

### 4. 兼容性检查

```python
# 检查依赖兼容性矩阵
# Python: 检查 pyproject.toml 的 requires-python
# Node: 检查 package.json 的 engines

# 运行类型检查发现 API 变更
tsc --noEmit        # 前端
mypy app/            # 后端

# 运行 lint 发现 deprecated API
pnpm lint
ruff check .
```

### 5. 锁文件管理

```bash
# 更新 lockfile
pnpm install --frozen-lockfile  # CI 中使用（确保一致）
pnpm install                     # 本地更新 lockfile

# Python
uv lock          # 更新 uv.lock
uv sync          # 同步安装
```

### 6. 回退方案

```bash
# 如果升级后出问题
git checkout package.json pnpm-lock.yaml  # 恢复依赖文件
pnpm install                                # 重新安装

# 或回退到上一个 commit
git revert HEAD
```

### 7. 安全漏洞修复

```bash
# npm 自动修复
npm audit fix            # 自动修复兼容的漏洞
npm audit fix --force    # 强制修复（可能有 breaking change）

# 手动修复
# 1. 查看 advisory 详情
npm audit

# 2. 手动升级到修复版本
pnpm add vulnerable-package@fixed-version

# 3. 如果修复版本有 breaking change
# 需要同时修改使用该包的代码
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash | 执行升级命令、audit |
| `read_file` / `grep` | 查找受影响的代码 |
| `apply_diff` / `multi_edit` | 适配 breaking changes |
| `run_tests` | 验证升级后功能正常 |
| `run_linter` | 检查 deprecated API |

## 检查清单

- [ ] 评估了升级的必要性和风险
- [ ] 创建了专用分支
- [ ] 阅读了 migration guide（major 升级）
- [ ] 升级后更新了 lockfile
- [ ] 运行了完整测试套件
- [ ] 类型检查通过
- [ ] Lint 通过
- [ ] 手动验证了关键功能
- [ ] 记录了升级变更

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 一次性升级所有依赖 | 逐个升级，便于定位问题 |
| 不看 changelog 就升级 | 阅读 migration guide |
| 升级后不测试 | 完整测试 + 手动验证 |
| 不更新 lockfile | 同步更新 lockfile |
| 安全漏洞不修复 | 优先修复安全漏洞 |
| Major 升级直接上 main | 在专用分支上验证 |

## 输出要求

1. 列出升级的依赖和版本变化
2. 说明 breaking changes 和适配方案
3. 提供测试验证结果
4. 更新 lockfile
5. 提供回退方案
---
name: dependency-upgrade
description: >-
  Use this skill for dependency upgrades, package manager changes, vulnerability
  remediation, lockfile updates, SDK migrations, and version compatibility work.
work_modes: [coding]
---

