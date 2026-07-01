---
name: qiongqi-roi
description: >-
  Use this skill when recording or analyzing Qiongqi ROI telemetry, token
  economy, tool catalog compression, hidden tool counts, provider usage, or
  session-level efficiency reports.
work_modes: [coding]
---

# Qiongqi ROI

## 适用场景

- 分析 Coding Agent 的 token 使用效率和经济性
- 评估工具目录压缩效果（hidden tool counts）
- 生成 session 级别的效率报告
- 优化 agent 的 token 消耗策略

## 核心原则

1. **数据驱动**：基于遥测数据而非主观判断
2. **效率优先**：在保证质量的前提下最小化 token 消耗
3. **可对比**：不同 session/配置之间可横向对比
4. **可追踪**：ROI 指标随时间变化可追踪趋势
5. **可操作**：报告不只是数字，还要有优化建议

## 执行流程

### 1. 收集遥测数据

```python
# Qiongqi 引擎遥测数据
telemetry = {
    "session_id": session_id,
    "total_tokens": {
        "input": input_tokens,
        "output": output_tokens,
        "cached": cached_tokens,
    },
    "tool_calls": {
        "total": total_calls,
        "successful": success_count,
        "failed": fail_count,
        "by_tool": {
            "read_file": 15,
            "apply_diff": 8,
            "grep": 12,
            "run_tests": 3,
        }
    },
    "provider_usage": {
        "claude-sonnet": {"calls": 5, "tokens": 12000},
        "gpt-4o": {"calls": 3, "tokens": 8000},
    },
    "hidden_tools": 28,  # 压缩后隐藏的工具数
    "visible_tools": 12,  # 实际暴露给 LLM 的工具数
    "session_duration_sec": 320,
    "task_completed": True,
}
```

### 2. 计算 ROI 指标

| 指标 | 公式 | 说明 |
|------|------|------|
| **Token 效率** | 任务产出 / 总 token | 每千 token 的有效产出 |
| **工具命中率** | 成功调用 / 总调用 | 工具使用的有效性 |
| **压缩率** | 隐藏工具 / 总工具 | 工具目录压缩效果 |
| **成本效率** | 任务完成度 / API 成本 | 每美元的产出 |
| **时间效率** | 任务完成 / 耗时 | 每分钟的有效操作 |

### 3. 效率报告模板

```markdown
## Qiongqi Session ROI Report

### 基本信息
- Session ID: xxx
- 任务: 实现 JWT 认证模块
- 耗时: 5分20秒
- 状态: ✅ 完成

### Token 经济
| 指标 | 数值 |
|------|------|
| 输入 Token | 45,200 |
| 输出 Token | 8,300 |
| 缓存命中 | 12,000 (21%) |
| 总消耗 | 53,500 |
| 预估成本 | $0.32 |

### 工具使用
| 工具 | 调用次数 | 成功率 |
|------|---------|--------|
| read_file | 15 | 100% |
| grep | 12 | 100% |
| apply_diff | 8 | 87.5% |
| run_tests | 3 | 100% |

### 工具目录压缩
- 总工具数: 40
- 暴露给 LLM: 12 (30%)
- 隐藏: 28 (70%)
- 压缩节省 token: ~8,000

### 优化建议
1. apply_diff 有 1 次失败（stale replacement），建议先 read_file 确认
2. grep 调用 12 次偏多，可合并搜索条件
3. 缓存命中率 21% 偏低，可优化 prompt 结构
```

### 4. 优化策略

| 优化方向 | 具体措施 |
|---------|---------|
| **减少 token** | 工具目录压缩、prompt 缓存、上下文压缩 |
| **提高工具命中率** | 更精准的搜索、先验证再操作 |
| **降低成本** | 简单任务用低成本模型、缓存复用 |
| **提升效率** | 并行工具调用、减少不必要的探索 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash | 读取遥测日志 |
| `read_file` | 查看遥测数据文件 |
| `write_file` | 生成报告 |

## 检查清单

- [ ] 收集了完整的遥测数据
- [ ] 计算了核心 ROI 指标
- [ ] 生成了结构化报告
- [ ] 提供了优化建议
- [ ] 与历史数据对比了趋势

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 只看总 token | 分析 token 构成和效率 |
| 不分析失败原因 | 每次失败都有根因分析 |
| 不提优化建议 | 报告附带可操作的优化方案 |
| 不追踪趋势 | 对比历史数据发现变化 |

## 输出要求

1. 提供完整的遥测数据汇总
2. 计算核心 ROI 指标
3. 生成结构化效率报告
4. 与历史数据对比
5. 提供具体的优化建议
---
name: qiongqi-roi
description: >-
  Use this skill when recording or analyzing Qiongqi ROI telemetry, token
  economy, tool catalog compression, hidden tool counts, provider usage, or
  session-level efficiency reports.
work_modes: [coding]
---

