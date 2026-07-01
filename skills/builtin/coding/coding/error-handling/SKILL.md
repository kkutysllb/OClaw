---
name: error-handling
description: >-
  Use this skill when improving exceptions, API error responses, retries,
  timeout handling, stale-state errors, user-facing failure messages, or
  recoverability.
work_modes: [coding]
---

# Error Handling

## 适用场景

- 改进异常处理策略（精确捕获、合理传播、优雅降级）
- 设计 API 错误响应格式和状态码
- 实现重试、超时、断路器等弹性模式
- 优化用户可见的错误消息

## 核心原则

1. **精确捕获**：捕获具体的异常类型，不用裸 except/catch-all
2. **合理传播**：不可恢复的错误向上传播，可恢复的就近处理
3. **用户友好**：错误消息对用户有意义，不暴露技术细节
4. **可观测**：所有异常都有日志记录，包含完整上下文
5. **优雅降级**：出错时提供合理默认值或备选路径

## 执行流程

### 1. 异常处理策略

```python
# ❌ 键误：裸 except 吞掉所有异常
try:
    do_something()
except:
    pass  # 静默吞掉错误

# ❌ 错误：捕获太宽
try:
    result = api.call()
except Exception:
    return None  # 所有异常都返回 None，掩盖真正的问题

# ✅ 正确：精确捕获 + 合理处理
try:
    result = api.call()
except api.TimeoutError:
    logger.warning("API timeout, retrying", url=url)
    result = retry_with_backoff(api.call)
except api.ConnectionError as e:
    logger.error("API connection failed", url=url, error=str(e))
    raise ServiceUnavailableError("Service temporarily unavailable") from e
except api.AuthenticationError:
    raise  # 不可恢复，向上传播
```

### 2. 自定义异常层次

```python
class AppError(Exception):
    """所有应用异常的基类"""
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class ValidationError(AppError):
    def __init__(self, message, field=None):
        super().__init__(message, "VALIDATION_ERROR", 400)
        self.field = field

class NotFoundError(AppError):
    def __init__(self, resource, resource_id):
        super().__init__(
            f"{resource} '{resource_id}' not found",
            "NOT_FOUND", 404
        )

class AuthenticationError(AppError):
    def __init__(self, message="Authentication required"):
        super().__init__(message, "AUTH_ERROR", 401)
```

### 3. API 错误响应格式

```python
# 统一错误响应格式
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Email format is invalid",
        "field": "email",
        "request_id": "req_abc123"
    }
}

# FastAPI 异常处理器
@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
            }
        }
    )
```

### 4. HTTP 状态码使用

| 状态码 | 场景 | 说明 |
|-------|------|------|
| 400 | 参数校验失败 | 请求格式正确但语义错误 |
| 401 | 未认证 | 需要登录/token |
| 403 | 无权限 | 已登录但无权限 |
| 404 | 资源不存在 | 请求的资源未找到 |
| 409 | 冲突 | 资源已存在/状态冲突 |
| 422 | 业务校验失败 | 参数正确但业务规则不通过 |
| 429 | 限流 | 请求过于频繁 |
| 500 | 服务器内部错误 | 未预期的异常 |

### 5. 弹性模式

#### 重试（指数退避）

```python
import asyncio
from functools import wraps

def retry(max_attempts=3, base_delay=1.0, max_delay=30.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (TimeoutError, ConnectionError) as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"Retry {attempt+1}/{max_attempts} after {delay}s", error=str(e))
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

#### 超时

```python
# 设置合理的超时
async def fetch_with_timeout(url):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url) as response:
            return await response.json()
```

#### 断路器

```python
# 连续失败后熔断，避免级联故障
class CircuitBreaker:
    def __init__(self, threshold=5, reset_timeout=60):
        self.failures = 0
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.opened_at = None

    def call(self, func, *args, **kwargs):
        if self.is_open():
            raise CircuitOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = time.time()
            raise
```

### 6. 优雅降级

```python
# 出错时提供合理默认值
async def get_user_preferences(user_id):
    try:
        return await cache.get(f"prefs:{user_id}")
    except CacheError:
        logger.warning("Cache unavailable, returning defaults")
        return DEFAULT_PREFERENCES  # 降级到默认值

# 出错时提供备选路径
async def get_data(primary_source, fallback_source):
    try:
        return await primary_source.fetch()
    except SourceUnavailableError:
        logger.warning("Primary source down, using fallback")
        return await fallback_source.fetch()
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看现有异常处理代码 |
| `apply_diff` / `multi_edit` | 改进异常处理 |
| `run_tests` | 验证异常场景 |
| `run_linter` | 检查异常处理 lint 规则 |

## 检查清单

- [ ] 无裸 except/catch-all
- [ ] 有自定义异常层次
- [ ] API 错误响应格式统一
- [ ] HTTP 状态码使用正确
- [ ] 外部调用有超时设置
- [ ] 可重试操作有重试逻辑
- [ ] 错误消息对用户友好
- [ ] 异常有完整日志（含上下文和堆栈）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| `except: pass` | 精确捕获 + 日志 + 处理 |
| `except Exception as e: return None` | 区分可恢复和不可恢复 |
| 错误消息暴露内部细节 | 用户友好的错误消息 |
| 无超时的外部调用 | 设置合理超时 |
| 不记录异常上下文 | 日志包含完整上下文 |
| 所有错误都 500 | 按场景返回正确的状态码 |

## 输出要求

1. 提供异常处理改进方案
2. 提供自定义异常类（如需要）
3. 提供统一的 API 错误响应格式
4. 提供弹性模式实现（重试/超时/断路器）
5. 提供优雅降级策略
---
name: error-handling
description: >-
  Use this skill when improving exceptions, API error responses, retries,
  timeout handling, stale-state errors, user-facing failure messages, or
  recoverability.
work_modes: [coding]
---

