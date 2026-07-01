---
name: requirements-analysis
description: >-
  Use this skill when clarifying user needs, business goals, constraints,
  user roles, workflows, edge cases, and project scope before implementation.
work_modes: [coding]
---

# Requirements Analysis

## 适用场景

在实现前澄清需求：用户需要什么、业务目标是什么、有哪些约束、角色与工作流、边界用例、项目范围。

## 核心原则

1. **需求先于方案**：先搞清楚"要解决什么问题"，再想"怎么解决"。
2. **显式化隐含假设**：用户没说的不等于不需要，要主动追问。
3. **区分必须与可选**：MVP 范围必须明确，避免范围蔓延。
4. **边界用例决定成败**：正常路径人人会做，边界和异常才是难点。
5. **可测试**：每条需求都应能转化为可验证的验收条件。

## 执行流程

### 1. 澄清核心目标
- 这个需求要解决谁的什么问题？
- 成功长什么样？如何衡量？
- 不做的后果是什么？

### 2. 识别用户角色
| 角色 | 目标 | 场景 |
|---|---|---|
| 普通用户 | 完成 X 操作 | 登录后点击... |
| 管理员 | 管理 Y 资源 | 后台配置... |

### 3. 梳理工作流
- 主流程：正常情况下的步骤
- 替代流程：条件不满足时的分支
- 异常流程：出错时如何处理

### 4. 枚举边界用例
- 空数据 / 单条数据 / 海量数据
- 并发操作 / 重复提交
- 权限不足 / 未登录 / 会话过期
- 网络中断 / 超时 / 服务不可用
- 数据格式异常 / 非法输入

### 5. 明确约束
- **技术约束**：必须用的框架、兼容性要求
- **业务约束**：合规、安全、性能 SLA
- **资源约束**：时间、人力、预算

### 6. 划定范围
- **MVP（必须）**：最小可发布的功能集
- **V2（应该）**：增强体验但不阻塞发布
- **Backlog（可以）**：未来考虑，本次不做

### 7. 转化为验收条件
每条需求产出可测试的验收条件（配合 `acceptance-criteria` 技能）。

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 理解现有能力 | `read_file_lines` / `search_code` | 评估实现基础 |
| 澄清歧义 | `ask_clarification` | 向用户确认 |
| 记录需求 | `write_file` | 产出需求文档 |

## 检查清单

- [ ] 核心目标一句话清晰
- [ ] 用户角色已识别
- [ ] 主流程 + 替代 + 异常流程已梳理
- [ ] 边界用例已枚举
- [ ] 约束已明确
- [ ] MVP 范围已划定
- [ ] 每条需求可转化为验收条件
- [ ] 不确定的地方已用 ask_clarification 确认

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 直接开始编码 | 先澄清需求 |
| 假设用户意图 | 用 ask_clarification 确认 |
| 范围无限蔓延 | 明确 MVP 边界 |
| 只考虑正常路径 | 枚举边界和异常 |
| 需求不可测试 | 转化为验收条件 |

## 输出要求

1. **核心目标**：一句话 + 衡量标准
2. **角色清单**：用户角色与目标
3. **工作流**：主/替代/异常流程
4. **边界用例**：枚举清单
5. **约束**：技术/业务/资源
6. **范围划分**：MVP / V2 / Backlog
7. **开放问题**：待确认的疑点
---
name: requirements-analysis
description: >-
  Use this skill when clarifying user needs, business goals, constraints,
  user roles, workflows, edge cases, and project scope before implementation.
work_modes: [coding]
---

