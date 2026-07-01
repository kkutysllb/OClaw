---
name: security-review
description: >-
  Use this skill for security-focused review of code, PRs, architecture,
  authentication, authorization, secrets, input handling, dependencies, and
  deployment configuration.
work_modes: [coding]
---

# Security Review

## 适用场景

安全视角的审查：代码、PR、架构、认证授权、密钥、输入处理、依赖、部署配置。

## 核心原则

1. **假设输入是恶意的**：所有外部输入（用户、API、文件）都必须校验和净化。
2. **最小权限**：默认拒绝，只授予必要的最小权限。
3. **纵深防御**：多层防护，不依赖单一安全机制。
4. **密钥绝不入库**：API key / password / token 永远不入代码、日志、错误信息。
5. **依赖也是攻击面**：第三方包的已知漏洞就是你的漏洞。

## 执行流程

### 1. 认证与授权审查
- **认证**：身份验证机制是否可靠（密码哈希用 bcrypt/argon2，不用 MD5/SHA1）
- **会话**：token 是否安全（JWT 签名、过期、刷新机制）
- **授权**：每个敏感操作是否检查权限（不只是认证）
- **越权**：用户能否访问他人的资源（IDOR 检查）

### 2. 输入处理审查
| 威胁 | 检查点 |
|---|---|
| **SQL 注入** | 是否用参数化查询，不拼 SQL |
| **XSS** | 用户输入是否转义，是否用 CSP |
| **命令注入** | 是否用 subprocess 列表参数，不拼 shell |
| **路径穿越** | 文件路径是否校验 `..` |
| **SSRF** | 外部 URL 是否限制内网访问 |
| **XXE** | XML 解析是否禁用外部实体 |
| **反序列化** | 是否安全反序列化（不用 pickle） |

### 3. 密钥管理审查
- `search_code "password\|secret\|token\|api_key"` 搜索硬编码密钥
- 检查 `.env` 是否在 `.gitignore`
- 日志中是否泄露敏感信息（密码、token、PII）
- 错误信息是否泄露内部结构（堆栈、SQL）

### 4. 依赖审查
- 检查 `package.json` / `requirements.txt` 的依赖版本
- 用 `npm audit` / `pip-audit` / `safety check` 扫描已知漏洞
- 评估新依赖的必要性和维护状态

### 5. 配置审查
- CORS 是否过于宽松（`*` + credentials）
- HTTPS 是否强制（HSTS）
- 安全 Header 是否设置（X-Frame-Options, CSP, X-Content-Type-Options）
- Cookie 是否设 HttpOnly + Secure + SameSite

### 6. 输出发现
按严重程度分级：
| 级别 | 标准 |
|---|---|
| **Critical** | 可直接被利用（RCE、SQL 注入、认证绕过） |
| **High** | 需特定条件利用（XSS、权限提升） |
| **Medium** | 增加攻击面（信息泄露、弱配置） |
| **Low** | 加固建议（最佳实践） |

## OWASP Top 10 检查清单

- [ ] A01 权限失控：每个敏感操作检查授权
- [ ] A02 加密失败：密码哈希、传输加密、密钥存储
- [ ] A03 注入：参数化查询、输入校验
- [ ] A04 不安全设计：威胁建模、最小权限
- [ ] A05 配置错误：默认配置、安全 Header
- [ ] A06 易受攻击组件：依赖扫描
- [ ] A07 认证失败：会话管理、密码策略
- [ ] A08 数据完整性失败：反序列化、CI/CD 安全
- [ ] A09 日志监控不足：安全事件可追溯
- [ ] A10 SSRF：外部请求限制

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 搜密钥 | `search_code "password\|secret\|token"` | 硬编码检查 |
| 读认证代码 | `read_file_lines` | 审查逻辑 |
| 依赖扫描 | `bash "npm audit\|pip-audit"` | 已知漏洞 |
| 配置审查 | `read_file_lines`（config） | 安全配置 |

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 信任用户输入 | 所有输入校验净化 |
| 拼接 SQL | 参数化查询 |
| 明文存密码 | bcrypt/argon2 哈希 |
| 日志打印 token | 脱敏或只记 hash |
| `eval` / `exec` 用户输入 | 安全的替代方案 |
| CORS 设 `*` + credentials | 精确白名单 |

## 输出要求

1. **发现清单**：按 Critical/High/Medium/Low 分级
2. **每条发现**：位置 + 威胁描述 + 修复建议
3. **OWASP 映射**：对应的风险类别
4. **依赖扫描结果**：已知漏洞清单
5. **总体安全评估**：是否可发布
---
name: security-review
description: >-
  Use this skill for security-focused review of code, PRs, architecture,
  authentication, authorization, secrets, input handling, dependencies, and
  deployment configuration.
work_modes: [coding]
---

