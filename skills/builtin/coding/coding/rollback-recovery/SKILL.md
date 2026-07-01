---
name: rollback-recovery
description: >-
  Use this skill when a patch fails, an automatic fix becomes stale, a generated
  change is wrong, files need to be restored, or the agent must recover from a
  bad intermediate state without discarding user work.
work_modes: [coding]
---

# Rollback & Recovery

## 适用场景

- Agent 生成的 patch 应用失败或产生了错误结果
- apply_diff/multi_edit 的替换文本与实际文件不匹配（stale replacement）
- 中间步骤引入了问题，需要回退到已知良好状态
- 用户要求撤销最近的修改

## 核心原则

1. **保护用户工作**：回滚时绝对不能丢弃用户的手动修改
2. **精确定位**：回滚到具体的错误 commit/hunk，不做过度回滚
3. **可验证**：回滚后确认系统恢复到预期状态
4. **记录原因**：每次回滚记录原因，避免重复犯错
5. **渐进恢复**：优先尝试最小范围回滚（undo → revert → reset）

## 执行流程

### 1. 评估损坏程度

```
问题分类：
- 单文件错误 → 用 undo_last_edit 回退该文件
- 多文件关联错误 → 用 git checkout 恢复相关文件
- 整个 commit 错误 → 用 git revert 撤销该 commit
- 分支状态混乱 → 考虑 git reset 到安全点
```

### 2. 选择恢复策略

| 场景 | 策略 | 命令/工具 |
|------|------|----------|
| 刚编辑的单个文件有误 | 撤销最后一次编辑 | `undo_last_edit` 工具 |
| 多个文件需要恢复 | Git checkout 恢复 | `git checkout -- <files>` |
| 需要撤销某个 commit | Git revert（保留历史） | `git revert <commit>` |
| 需要回到某个安全点 | Git reset（谨慎） | `git reset --hard <safe-commit>` |
| Stale replacement | 手动修复文件内容 | `read_file` → `apply_diff` |
| 工作区被污染 | 从 stash/branch 恢复 | `git stash pop` / `git checkout <branch>` |

### 3. 执行回滚

#### 3a. 撤销最后一次编辑（最安全）

```
使用 undo_last_edit 工具回退最近一次文件修改
适用：刚用 apply_diff/multi_edit 改了文件，发现改错了
```

#### 3b. Git 文件级恢复

```bash
# 查看哪些文件被修改了
git status

# 恢复特定文件到最后一次 commit 的状态
git checkout -- path/to/file.py

# 恢复多个文件
git checkout -- file1.py file2.ts
```

#### 3c. Git commit 级回滚

```bash
# 查看最近的 commit 历史
git log --oneline -10

# 安全撤销某个 commit（创建反向 commit，不改写历史）
git revert <bad-commit-hash>

# 如果 bad commit 是最新的，可以 reset（谨慎！）
git reset --soft HEAD~1  # 保留修改在暂存区
git reset --hard HEAD~1  # 完全丢弃修改（确认无用户工作！）
```

#### 3d. Stale Replacement 恢复

当 apply_diff 报告"文本不匹配"时：

```
1. read_file 查看文件当前实际内容
2. 对比预期的 old_text 和实际内容，找出差异
3. 用正确的 old_text 重新 apply_diff
4. 或手动修复文件到正确状态
```

### 4. 保护用户工作

- 回滚前先检查 `git status` 和 `git stash list`
- 如果有未提交的用户修改，先 `git stash` 保存
- 回滚完成后再 `git stash pop` 恢复用户修改
- 绝不使用 `git clean -fd`（会删除未跟踪的用户文件）

### 5. 验证恢复

```bash
# 确认文件恢复到预期状态
git diff  # 应显示预期内容或无差异

# 运行测试确认功能正常
npm test / pytest

# 检查应用是否正常运行
```

### 6. 记录与改进

- 记录回滚原因（哪个操作导致的错误）
- 分析根因（是搜索不充分？替换文本过时？逻辑错误？）
- 调整策略避免重复（下次先验证再应用？分步应用？）

## 工具优先级

| 工具 | 用途 |
|------|------|
| `undo_last_edit` | 撤销最近一次编辑（最安全） |
| `git_status` / `git_diff` | 评估当前状态 |
| `git_log` | 查看 commit 历史 |
| Bash（git revert/reset/checkout） | 执行 Git 级回滚 |
| `read_file` | 确认文件当前内容 |
| `apply_diff` | 修复 stale replacement |

## 检查清单

- [ ] 评估了损坏范围（单文件 vs 多文件 vs 整个 commit）
- [ ] 检查了未提交的用户修改（git status）
- [ ] 选择了最小范围的回滚策略
- [ ] 执行了回滚操作
- [ ] 验证了文件恢复到预期状态
- [ ] 运行了测试确认功能正常
- [ ] 记录了回滚原因和根因

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| `git reset --hard` 不检查用户修改 | 先 stash 用户修改再 reset |
| `git clean -fd` 清除未跟踪文件 | 只恢复已知被修改的文件 |
| 直接重写文件忽略 Git | 用 Git 操作保持历史可追溯 |
| 回滚后不验证 | 运行测试确认恢复成功 |
| 回滚后不分析原因 | 记录根因，避免重复犯错 |
| 整个分支 reset 回退 | 优先 revert 单个 commit |

## 输出要求

1. 描述问题：什么操作导致了需要回滚
2. 评估范围：受影响的文件和 commit
3. 执行回滚：说明使用的策略和命令
4. 验证结果：确认恢复成功
5. 根因分析：为什么会出错，如何避免
---
name: rollback-recovery
description: >-
  Use this skill when a patch fails, an automatic fix becomes stale, a generated
  change is wrong, files need to be restored, or the agent must recover from a
  bad intermediate state without discarding user work.
work_modes: [coding]
---

