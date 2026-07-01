---
name: fastapi-backend
description: >-
  Use this skill for FastAPI backend work: routers, Pydantic models, request
  validation, dependency injection, middleware, service boundaries, and route
  tests.
work_modes: [coding]
---

# FastAPI Backend

## 适用场景

FastAPI 后端开发：路由、Pydantic 模型、请求校验、依赖注入、中间件、服务边界、路由测试。

## 核心原则

1. **Pydantic 先行**：用模型定义请求/响应 schema，校验由框架自动完成。
2. **依赖注入组织依赖**：用 `Depends` 管理数据库会话、认证、配置，不手动传参。
3. **路由薄、服务厚**：路由只做参数解析和调用服务，业务逻辑在 service 层。
4. **异步优先**：IO 密集用 `async def`，CPU 密集用 `def`（FastAPI 自动放线程池）。
5. **类型即文档**：利用类型注解自动生成 OpenAPI 文档。

## 执行流程

### 1. 定义 Schema（Pydantic）
```python
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    email: str = Field(..., pattern=r"^[\w.-]+@[\w.-]+$")
    name: str = Field(..., min_length=1, max_length=100)

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime
```

### 2. 编写路由（薄层）
```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return await service.create(payload)
```

### 3. 实现服务层（厚逻辑）
- 业务规则、数据转换、外部调用
- 通过依赖注入获取数据库会话和其他服务
- 服务方法返回领域对象或 DTO

### 4. 依赖注入
```python
def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

def get_user_service(session = Depends(get_db_session)) -> UserService:
    return UserService(session)
```

### 5. 中间件（横切关注点）
- 认证、日志、CORS、错误处理
- 用 `@app.middleware("http")` 或 `add_middleware`

### 6. 错误处理
```python
@router.post("/users")
async def create_user(...):
    raise HTTPException(status_code=409, detail="邮箱已存在")
```

### 7. 测试
```python
async def test_create_user_returns_201():
    response = await client.post("/users", json={"email": "a@b.com", "name": "A"})
    assert response.status_code == 201
```

## 常见模式

| 场景 | 模式 |
|---|---|
| 分页 | `skip: int = 0, limit: int = 20` 参数 + `response_model` 含 total |
| 后台任务 | `BackgroundTasks` 参数注入 |
| WebSocket | `@router.websocket("/ws")` |
| 流式响应 | `StreamingResponse` |
| 文件上传 | `UploadFile` 参数 |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 找现有路由 | `search_code "@router" / "@app"` | 了解约定 |
| 读模型 | `read_file_lines` | 理解 schema |
| 编辑路由/服务 | `apply_diff` / `write_file` | 实现 |
| 测试 | `run_tests` + TestClient | 验证 |

## 检查清单

- [ ] 请求/响应有 Pydantic 模型
- [ ] 路由薄、逻辑在 service 层
- [ ] 依赖用 Depends 注入
- [ ] 异步/同步选择正确
- [ ] 错误用 HTTPException 且状态码合理
- [ ] 路由有测试覆盖
- [ ] 响应模型清晰（response_model）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| 路由里写业务逻辑 | 移到 service 层 |
| 手动传 db session | 用 Depends 注入 |
| 手动校验参数 | 用 Pydantic 模型 |
| 同步阻塞 IO 在 async 里 | 用 async 库或改 def |
| 不设 response_model | 明确声明响应类型 |

## 输出要求

1. **Schema 定义**：请求/响应模型
2. **路由清单**：端点 + 参数 + 响应
3. **服务层说明**：核心逻辑位置
4. **依赖注入图**：关键依赖链
5. **测试结果**：路由测试输出
---
name: fastapi-backend
description: >-
  Use this skill for FastAPI backend work: routers, Pydantic models, request
  validation, dependency injection, middleware, service boundaries, and route
  tests.
work_modes: [coding]
---

