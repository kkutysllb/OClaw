---
name: scratch-workspace
description: >-
  Use this skill when the Coding Agent needs temporary files, analysis outputs,
  generated intermediate artifacts, logs, scripts, or task workspaces that must
  not pollute the user's project root.
work_modes: [coding]
---

# Scratch Workspace

## 适用场景

- Agent 需要生成临时分析文件、中间脚本、调试输出
- 需要暂存中间结果（代码片段、搜索结果、分析报告）
- 需要运行临时脚本但不想污染用户项目目录
- 需要为子任务创建独立的工作空间

## 核心原则

1. **不污染项目**：临时文件放在专用目录，不放在用户项目根目录
2. **可清理**：临时文件任务完成后可安全删除
3. **有组织**：按任务/日期组织临时文件，便于查找和清理
4. **明确标注**：临时文件标注用途和创建时间
5. **体积可控**：限制临时文件大小，避免占用过多磁盘

## 执行流程

### 1. 确定临时文件需求

| 需求类型 | 示例 | 存放位置 |
|---------|------|---------|
| 分析输出 | 代码统计、依赖分析 | `.scratch/analysis/` |
| 中间脚本 | 临时数据处理脚本 | `.scratch/scripts/` |
| 调试输出 | 日志、堆栈、变量值 | `.scratch/debug/` |
| 生成代码 | 代码片段草稿 | `.scratch/drafts/` |
| 测试数据 | 临时测试 fixture | `.scratch/test-data/` |

### 2. 目录结构

```
项目根目录/
├── .scratch/              # 临时工作区（加入 .gitignore）
│   ├── analysis/          # 分析输出
│   │   ├── dep-tree.txt
│   │   └── codebase-stats.md
│   ├── scripts/           # 临时脚本
│   │   ├── check-deps.py
│   │   └── migrate-data.py
│   ├── debug/             # 调试输出
│   │   └── error-trace.log
│   ├── drafts/            # 代码草稿
│   │   └── new-module-draft.py
│   └── README.md          # 说明这是临时目录
├── src/                   # 用户项目代码
└── ...
```

### 3. .gitignore 配置

```gitignore
# Scratch workspace - 临时文件
.scratch/
```

### 4. 使用规范

```python
# 创建临时分析文件
import pathlib

scratch_dir = pathlib.Path(".scratch/analysis")
scratch_dir.mkdir(parents=True, exist_ok=True)

# 写入分析结果
output = scratch_dir / "dependency-analysis.txt"
output.write_text(analysis_result)

# 标注用途
header = f"""
# 临时文件 - 依赖分析
# 创建时间: {datetime.now()}
# 任务: 分析项目依赖树
# 可安全删除
"""
output.write_text(header + analysis_result)
```

### 5. 清理策略

```bash
# 任务完成后清理临时文件
rm -rf .scratch/

# 或保留一段时间后清理（如 7 天后）
find .scratch/ -mtime +7 -delete
```

### 6. 何时使用临时文件

| 场景 | 使用临时文件？ | 理由 |
|------|--------------|------|
| 生成分析报告供用户查看 | ✅ 是 | 中间产物，不需要入版本库 |
| 编写项目正式脚本 | ❌ 否 | 应放在 `scripts/` 目录 |
| 临时数据处理 | ✅ 是 | 一次性操作 |
| 编写测试 | ❌ 否 | 应放在 `tests/` 目录 |
| 调试输出 | ✅ 是 | 临时排查用 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 创建临时文件 |
| Bash | 创建目录、清理临时文件 |
| `read_file` | 读取临时文件内容 |

## 检查清单

- [ ] 临时文件放在 `.scratch/` 目录（不污染项目根目录）
- [ ] `.scratch/` 已加入 `.gitignore`
- [ ] 临时文件标注用途和创建时间
- [ ] 任务完成后清理临时文件
- [ ] 临时文件不进入版本控制

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 临时文件放在项目根目录 | 放在 `.scratch/` 目录 |
| 临时文件提交到 Git | 加入 `.gitignore` |
| 不清理临时文件 | 任务完成后清理 |
| 临时文件无标注 | 标注用途和时间 |
| 正式代码放临时目录 | 临时目录只放临时文件 |

## 输出要求

1. 在 `.scratch/` 目录中创建临时文件
2. 确保不污染用户项目目录
3. 临时文件有用途标注
4. 任务完成后提供清理方案
---
name: scratch-workspace
description: >-
  Use this skill when the Coding Agent needs temporary files, analysis outputs,
  generated intermediate artifacts, logs, scripts, or task workspaces that must
  not pollute the user's project root.
work_modes: [coding]
---

