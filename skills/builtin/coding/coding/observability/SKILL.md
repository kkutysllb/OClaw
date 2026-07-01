---
name: observability
description: >-
  Use this skill for logging, metrics, tracing, diagnostics, runtime events,
  telemetry, audit trails, and debugging visibility.
work_modes: [coding]
---

# Observability

## 适用场景

- 添加或改进日志系统（结构化日志、日志级别、敏感信息过滤）
- 添加监控指标（请求量、延迟、错误率、资源使用）
- 配置分布式追踪（请求链路追踪）
- 审计日志和合规要求

## 核心原则

1. **结构化日志**：JSON 格式，机器可解析，包含时间、级别、上下文
2. **分级输出**：DEBUG/INFO/WARNING/ERROR/CRITICAL，生产环境过滤低级别
3. **关联追踪**：每个请求有 trace_id，可串联完整链路
4. **敏感信息过滤**：密码、token、密钥绝不出现在日志中
5. **可观测优先**：新功能上线前必须先有可观测性（日志 + 指标）

## 执行流程

### 1. 日志规范

```python
import structlog

# 结构化日志配置
logger = structlog.get_logger()

# ✅ 正确：结构化、有上下文
logger.info("user_login",
    user_id=user.id,
    ip_address=request.remote_addr,
    method="password",
    duration_ms=142,
)

# ❌ 错误：非结构化、可能有敏感信息
logger.info(f"User {user.email} logged in from {request.remote_addr}")
```

#### 日志级别使用规范

| 级别 | 使用场景 | 生产输出 |
|------|---------|---------|
| DEBUG | 详细调试信息（变量值、流程步骤） | ❌ 不输出 |
| INFO | 正常业务事件（登录、创建、更新） | ✅ 输出 |
| WARNING | 异常但可处理（重试、降级、限流） | ✅ 输出 |
| ERROR | 错误但系统仍可运行（API 失败、异常捕获） | ✅ 输出 + 告警 |
| CRITICAL | 系统不可用（数据库连接丢失、OOM） | ✅ 输出 + 紧急告警 |

### 2. 敏感信息过滤

```python
# 日志中间件：过滤敏感字段
SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "authorization", "cookie"}

def sanitize_log_data(data: dict) -> dict:
    return {
        k: "***REDACTED***" if k.lower() in SENSITIVE_FIELDS else v
        for k, v in data.items()
    }
```

### 3. 监控指标

```python
# 关键指标（RED 方法）
# Rate - 请求量
request_count = Counter("http_requests_total", ["method", "endpoint", "status"])

# Errors - 错误率
error_count = Counter("http_errors_total", ["endpoint", "error_type"])

# Duration - 延迟
request_duration = Histogram("http_request_duration_seconds", ["endpoint"])

# 使用
@metrics_timer("api_users")
async def get_users():
    request_count.labels(method="GET", endpoint="/api/users", status="200").inc()
    # ...
```

#### 核心指标清单

| 类型 | 指标 | 说明 |
|------|------|------|
| **流量** | 请求量/QPS | 每秒请求数 |
| **延迟** | P50/P95/P99 响应时间 | 百分位延迟 |
| **错误** | 错误率/异常数 | HTTP 5xx、未捕获异常 |
| **饱和度** | CPU/内存/磁盘/连接池 | 资源使用率 |
| **业务** | 活跃用户/任务数/队列长度 | 业务关键指标 |

### 4. 分布式追踪

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_order(order_id):
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)

        with tracer.start_as_current_span("validate_order"):
            # 子操作
            validate(order_id)

        with tracer.start_as_current_span("save_to_db"):
            # 子操作
            save(order_id)
```

### 5. 审计日志

```python
# 审计日志：记录谁在什么时候做了什么操作
audit_logger.info("audit",
    actor=user.id,
    action="delete_resource",
    resource=resource_id,
    timestamp=datetime.utcnow().isoformat(),
    ip=request.remote_addr,
    result="success",
)
```

### 6. 告警规则

| 条件 | 告警级别 | 通知方式 |
|------|---------|---------|
| 错误率 > 5% 持续 5 分钟 | Critical | 即时通知 |
| P95 延迟 > 2s 持续 5 分钟 | High | 即时通知 |
| CPU > 80% 持续 10 分钟 | Medium | 邮件通知 |
| 磁盘 > 90% | Critical | 即时通知 |
| 服务不可达 | Critical | 即时通知 |

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看现有日志/监控代码 |
| `apply_diff` / `multi_edit` | 添加日志、指标、追踪代码 |
| `run_tests` | 验证日志逻辑正确 |
| Bash | 查看日志输出、测试指标 |

## 检查清单

- [ ] 日志使用结构化格式（JSON）
- [ ] 日志级别正确使用（DEBUG/INFO/WARN/ERROR）
- [ ] 敏感信息已过滤（password/token/secret）
- [ ] 关键操作有审计日志
- [ ] 核心指标已埋点（请求量/延迟/错误率）
- [ ] 异常有完整堆栈日志
- [ ] 请求链路可追踪（trace_id）
- [ ] 告警规则已配置

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| `print()` 调试 | 结构化 logger |
| 日志含密码/token | 敏感字段过滤 |
| 所有日志都用 INFO | 按重要性分级 |
| 只记日志没有指标 | 日志 + 指标 + 追踪 |
| 异常吞掉不记日志 | except 中记录 ERROR 日志 |
| 无 trace_id 串联 | 每个请求注入 trace_id |

## 输出要求

1. 提供结构化日志方案（格式 + 级别 + 过滤）
2. 提供核心指标埋点代码
3. 提供审计日志方案（如需要）
4. 提供分布式追踪配置（如需要）
5. 提供告警规则建议
---
name: observability
description: >-
  Use this skill for logging, metrics, tracing, diagnostics, runtime events,
  telemetry, audit trails, and debugging visibility.
work_modes: [coding]
---

