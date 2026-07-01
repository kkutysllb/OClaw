---
name: using-git-worktrees
description: >-
  Use this skill when coding work needs isolation from the user's dirty working
  tree, parallel implementation paths, risky refactors, or PR-level branch work.
work_modes: [coding]
---

# Git Worktrees

## 适用场景

- 需要在独立的工作树中进行改动，不影响用户当前的脏工作区
- 需要并行开发多个功能（每个功能一个 worktree）
- 进行风险较大的重构，需要隔离试验
- 创建 PR 级别的分支工作空间

## 核心原则

1. **完全隔离**：worktree 有独立的文件系统视图和分支，互不干扰
2. **共享仓库**：所有 worktree 共享同一个 `.git` 目录，节省空间
3. **分支绑定**：每个 worktree 绑定一个分支，切换需注意
4. **用完清理**：worktree 完成后及时移除，避免残留
5. **保护主树**：不修改用户主工作区的文件和分支状态

## 执行流程

### 1. 创建 Worktree

```bash
# 创建新分支的 worktree
git worktree add ../oclaw-feature-x -b feature/x

# 基于现有分支创建 worktree
git worktree add ../oclaw-hotfix hotfix/urgent-bug

# 查看所有 worktree
git worktree list
```

### 2. 在 Worktree 中工作

```bash
cd ../oclaw-feature-x

# 现在在一个完全隔离的工作环境中
# 可以自由修改、测试，不影响主工作区

# 正常的开发流程
git add .
git commit -m "feat: implement feature X"

# 运行测试
pytest tests/ -v
```

### 3. 合并回主分支

```bash
# 回到主工作区
cd /path/to/main-repo

# 确认主工作区状态
git status

# 合并 feature 分支
git merge feature/x

# 或者创建 PR
git push origin feature/x
```

### 4. 清理 Worktree

```bash
# 完成后移除 worktree
git worktree remove ../oclaw-feature-x

# 删除关联的分支（如果已合并）
git branch -d feature/x

# 清理残留的 worktree 引用
git worktree prune

# 确认清理干净
git worktree list
```

### 5. 典型使用模式

#### 模式 A：风险隔离

```
用户主工作区有未提交的修改（dirty tree）。
Agent 需要做一个大重构，不想影响用户的工作。

解决：创建 worktree，在隔离环境中操作。
```

#### 模式 B：并行开发

```
需要同时实现两个独立的功能 A 和 B。

解决：
- worktree-1 → feature/A
- worktree-2 → feature/B
两个 worktree 独立工作，互不干扰。
```

#### 模式 C：PR 准备

```
需要在一个干净的分支上准备 PR（基于最新的 main）。

解决：
git worktree add ../oclaw-pr main
cd ../oclaw-pr
git checkout -b pr/new-feature
# 基于 main 分支进行开发
```

### 6. 注意事项

| 注意点 | 说明 |
|-------|------|
| **不共享未提交的修改** | 各 worktree 的未提交修改是独立的 |
| **共享 .git** | 所有 worktree 共享 Git 对象数据库 |
| **分支独占** | 一个分支同时只能被一个 worktree 检出 |
| **IDE 支持** | 在 IDE 中打开 worktree 目录即可工作 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash（git worktree） | 创建/移除/管理 worktree |
| `read_file` / `apply_diff` | 在 worktree 中工作 |
| `git_status` / `git_diff` | 查看 worktree 中的变更 |

## 检查清单

- [ ] worktree 创建在项目目录外（不污染主工作区）
- [ ] worktree 绑定正确的分支
- [ ] 工作完成后合并回主分支
- [ ] worktree 已移除并清理
- [ ] 关联的临时分支已删除

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 在主工作区做大重构 | 用 worktree 隔离 |
| worktree 用完不移除 | 及时 `git worktree remove` |
| 多个 worktree 用同一分支 | 一个分支一个 worktree |
| worktree 创建在项目内 | 创建在项目目录外 |

## 输出要求

1. 在隔离的 worktree 中进行代码修改
2. 不影响用户的主工作区状态
3. 完成后提供合并/PR 方案
4. 清理 worktree 和临时分支
---
name: using-git-worktrees
description: >-
  Use this skill when coding work needs isolation from the user's dirty working
  tree, parallel implementation paths, risky refactors, or PR-level branch work.
work_modes: [coding]
---

