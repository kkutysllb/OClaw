---
name: codebase-analysis
description: >-
  Use this skill before modifying unfamiliar code, when analyzing project
  architecture, finding feature ownership, tracing data flow, or assessing how
  an existing implementation works.
work_modes: [coding]
---

# Codebase Analysis

## 适用场景

修改不熟悉的代码前，或需要分析项目架构、定位功能归属、追踪数据流、评估现有实现时使用。是动手前的"侦察"环节。

## 核心原则

1. **先读再改**：对不熟悉的代码，先花时间理解再动手，避免盲改。
2. **自顶向下**：从入口点（main/router/cli）开始，逐层深入。
3. **追踪数据流**：理解数据如何在模块间流动，比理解单个函数更重要。
4. **记录发现**：边读边记录架构地图，形成可复用的认知。
5. **识别约定**：每个项目有自己的约定，理解约定才能写出一致的代码。

## 执行流程

### 1. 全局概览
- `find_files` 查看目录结构，识别分层（src/tests/config/docs）
- 读 README / CONTRIBUTING / 架构文档
- 检查 `package.json` / `pyproject.toml` 了解技术栈和脚本
- 理解构建和运行方式

### 2. 入口点追踪
找到程序的入口：
- **Web 应用**：router/app 定义（`search_code "@app" / "@router"`）
- **CLI**：main 函数 / argparse 定义
- **库**：`__init__.py` 的公共导出

从入口沿调用链向下追踪，理解请求/命令如何流转。

### 3. 模块与分层
- 识别分层模式：router → service → persistence（或类似）
- `search_code "<import pattern>"` 理解模块依赖
- 找到核心域模型（业务实体）

### 4. 功能定位
找到某个功能的实现位置：
- `search_code "<功能关键词>"` 搜索
- 从 UI/API 入口反向追踪
- 检查路由表、配置注册

### 5. 数据流追踪
对于特定功能，追踪数据如何流动：
- **输入**：请求从哪里进来
- **处理**：经过哪些函数/中间件
- **存储**：读写哪些表/文件
- **输出**：响应如何组装

### 6. 约定识别
记录项目的编码约定：
- 命名规范（文件、函数、类）
- 错误处理模式
- 日志方式
- 测试组织

### 7. 产出分析报告
输出可复用的架构认知（配合 `architecture` 技能）。

## 分析工具优先级

| 目标 | 工具 | 用途 |
|---|---|---|
| 目录结构 | `find_files` | 了解组织 |
| 符号定义 | `find_symbols` | 类/函数签名 |
| 文本搜索 | `search_code` | 定位实现 |
| 读代码 | `read_file_lines` | 理解细节 |
| 依赖关系 | `search_code "import"` | 模块依赖 |

## 检查清单

- [ ] 理解了目录结构和分层
- [ ] 找到了入口点
- [ ] 追踪了核心功能的调用链
- [ ] 理解了数据流（输入→处理→存储→输出）
- [ ] 识别了项目的编码约定
- [ ] 记录了架构地图（文字或图）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 直接改不熟悉的代码 | 先分析再动手 |
| 只读单个函数 | 理解调用链和数据流 |
| 忽略约定 | 识别并遵循项目约定 |
| 分析完不记录 | 输出架构地图 |
| 猜测实现 | 用工具读实际代码 |

## 输出要求

1. **架构概览**：目录结构 + 分层 + 技术栈
2. **入口点**：程序/请求的入口和流转
3. **功能归属**：相关功能在哪些文件
4. **数据流**：核心功能的输入→处理→存储→输出
5. **编码约定**：命名/错误处理/日志/测试规范
6. **修改建议**：基于分析给出的改动方向
---
name: codebase-analysis
description: >-
  Use this skill before modifying unfamiliar code, when analyzing project
  architecture, finding feature ownership, tracing data flow, or assessing how
  an existing implementation works.
work_modes: [coding]
---

