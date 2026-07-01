---
name: security-hardening
description: >-
  Use this skill for security-sensitive coding work, including authentication,
  authorization, secrets, input validation, SSRF, CSRF, path traversal, command
  execution, dependency risk, and hardening existing code.
work_modes: [coding]
---

# Security Hardening

## 适用场景

- 用户要求实现或修改认证/授权逻辑（登录、token、权限校验）
- 代码涉及用户输入处理、文件操作、命令执行、网络请求
- 密钥/凭证管理、配置安全、依赖漏洞修复
- 现有代码的安全加固（从安全审查报告转为修复行动）

## 核心原则

1. **永不信任输入**：所有外部数据（HTTP 参数、文件内容、环境变量）必须经过验证和清洗后才可使用
2. **最小权限原则**：代码只授予完成功能所需的最低权限，禁用通配符权限
3. **密钥零泄露**：密钥不在代码中硬编码、不写入日志、不出现在错误响应中
4. **纵深防御**：在多个层面实施安全检查，不依赖单一防护
5. **安全默认值**：所有安全相关配置默认取最严格值，需要时才显式放宽

## 执行流程

### 1. 识别攻击面

- 梳理代码中所有外部输入入口（API 端点、文件读取、命令调用、URL 解析）
- 识别敏感操作（认证、授权、数据持久化、外部请求、文件系统操作）
- 标注数据流向：用户输入 → 处理 → 存储 → 输出

### 2. 分类加固

按威胁类型逐项加固：

| 威胁类型 | 加固措施 |
|---------|---------|
| **注入攻击** | 参数化查询 / 输入白名单验证 / 禁止字符串拼接 SQL 或命令 |
| **XSS** | 输出编码 / CSP 头 / 禁用 dangerouslySetInnerHTML |
| **CSRF** | CSRF Token / SameSite Cookie / 校验 Origin 头 |
| **SSRF** | URL 白名单 / 禁止访问内网 IP / DNS rebinding 防护 |
| **路径穿越** | realpath 校验 / 禁止拼接用户输入到文件路径 |
| **命令注入** | 使用参数化 API（subprocess 列表形式）/ 禁止 shell=True |
| **认证绕过** | Token 校验 / 时间窗口防重放 / 会话过期 |
| **越权访问** | 对象级权限校验（IDOR 防护）/ 默认拒绝 |
| **信息泄露** | 生产关闭调试模式 / 错误响应不含堆栈 / 关闭目录列出 |

### 3. 密钥管理加固

```
✅ 正确：从环境变量 / Secret Manager 加载
❌ 错误：硬编码在源码 / 配置文件明文 / 提交到 Git
```

- 检查 `.env.example` 不含真实密钥
- 日志中间件过滤 Authorization/Cookie/API-Key 字段
- 错误响应不返回数据库结构或内部路径

### 4. 依赖安全

- 运行 `pip audit` / `npm audit` 检查已知漏洞
- 升级有 CVE 的依赖到修复版本
- 锁定依赖版本（lockfile），避免供应链攻击

### 5. 验证

- 编写安全相关测试（注入尝试、越权访问、路径穿越）
- 验证错误响应不含敏感信息
- 确认安全配置在生产环境中生效

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` / `grep` | 查找硬编码密钥、不安全 API 使用 |
| `apply_diff` / `multi_edit` | 应用安全修复补丁 |
| `run_tests` | 运行安全相关测试 |
| `run_linter` | 检查安全 lint 规则 |

## 检查清单

- [ ] 所有外部输入经过验证（类型/长度/格式/范围）
- [ ] SQL 查询使用参数化（无字符串拼接）
- [ ] 命令执行使用列表形式（无 shell=True）
- [ ] 文件路径经过 realpath 校验（防穿越）
- [ ] 外部 URL 请求有白名单或内网过滤（防 SSRF）
- [ ] 密钥从环境变量/Secret Manager 加载
- [ ] 日志过滤了敏感字段
- [ ] 错误响应不含堆栈或内部信息
- [ ] 权限校验在对象级别（防 IDOR）
- [ ] 依赖无已知高危漏洞

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| `eval(user_input)` | 白名单解析 + 类型转换 |
| `shell=True` + 字符串拼接 | `subprocess.run(["cmd", arg])` 列表形式 |
| `f"SELECT ... WHERE id={user_id}"` | `cursor.execute("... WHERE id=?", (user_id,))` |
| 密钥写死在代码里 | `os.environ["API_KEY"]` 或 Secret Manager |
| 全局 try/except 吞掉错误 | 精确异常处理 + 安全日志 |
| `dangerouslySetInnerHTML` 直接渲染 | DOMPurify 清洗后再渲染 |

## 输出要求

1. 列出发现的每个安全问题，标注严重级别（Critical/High/Medium/Low）
2. 对每个问题给出具体修复代码
3. 用 `apply_diff` / `multi_edit` 应用修复
4. 运行测试验证修复有效
5. 提供加固总结：修复了 N 个问题，剩余风险说明
---
name: security-hardening
description: >-
  Use this skill for security-sensitive coding work, including authentication,
  authorization, secrets, input validation, SSRF, CSRF, path traversal, command
  execution, dependency risk, and hardening existing code.
work_modes: [coding]
---

