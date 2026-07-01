---
name: database
description: >-
  Use this skill for schema changes, migrations, SQL, ORM models, indexes,
  transactions, data backfills, and persistence-layer bugs.
work_modes: [coding]
---

# Database

## 适用场景

- 数据库 schema 变更（新增表/列/索引/约束）
- 编写或修改 ORM 模型（SQLAlchemy / Prisma / Django ORM）
- 数据迁移和回填
- 排查查询性能问题、锁、死锁、数据一致性

## 核心原则

1. **Schema 即代码**：所有 schema 变更通过 migration 管理，禁止手动改库
2. **向前兼容**：migration 不破坏正在运行的旧版本代码
3. **事务安全**：关键操作在事务中执行，保证 ACID
4. **索引驱动**：查询性能靠索引保证，慢查询必须有索引支撑
5. **数据安全**：变更前备份，回填时分批次，避免锁表

## 执行流程

### 1. Schema 变更

#### 新增表/列（安全操作）

```python
# Alembic migration
def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.String(512), nullable=True))

    # 分批次回填已有数据
    conn = op.get_bind()
    conn.execute("""
        UPDATE users SET avatar_url = '' WHERE avatar_url IS NULL
    """)

    # 再添加 NOT NULL 约束
    op.alter_column('users', 'avatar_url', nullable=False)

def downgrade():
    op.drop_column('users', 'avatar_url')
```

#### 删除列/表（危险操作）

```
分三步执行（每个部署周期一步）：
1. 第一个版本：停止写入该列（代码不再使用），但列保留
2. 第二个版本：确认无影响后删除列
3. 如有问题：在第一步时代码可随时回退
```

#### 重命名列/表

```
分两步：
1. 新增新名称的列，双写新旧列，同步数据
2. 下一个版本删除旧列
```

### 2. 索引优化

```sql
-- 分析慢查询
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';

-- 添加复合索引（注意顺序：高选择性在前）
CREATE INDEX CONCURRENTLY idx_orders_user_status ON orders(user_id, status);

-- 部分索引（只索引需要的数据）
CREATE INDEX idx_active_users ON users(last_login_at) WHERE deleted_at IS NULL;
```

| 索引策略 | 适用场景 |
|---------|---------|
| B-Tree | 等值查询、范围查询 |
| GIN | 全文搜索、JSONB |
| 部分索引 | 只查询活跃数据 |
| 复合索引 | 多列组合查询 |

### 3. ORM 模型

```python
# SQLAlchemy 模型规范
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # 关系定义
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
```

### 4. 数据回填

```python
# 分批次回填，避免锁表
BATCH_SIZE = 1000

def backfill_data():
    while True:
        batch = session.query(User).filter(User.avatar_url.is_(None)).limit(BATCH_SIZE).all()
        if not batch:
            break

        for user in batch:
            user.avatar_url = generate_default_avatar(user.id)

        session.commit()
        print(f"Backfilled {len(batch)} records...")
```

### 5. 事务管理

```python
from contextlib import contextmanager

@contextmanager
def transaction(session):
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

# 使用
with transaction(session):
    user = User(name="test")
    session.add(user)
    # 异常时自动回滚
```

### 6. 查询性能排查

```sql
-- 找出慢查询
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 检查索引使用情况
SELECT relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;  -- 未使用的索引
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `read_file` | 查看 ORM 模型、migration 文件 |
| `write_file` / `apply_diff` | 编写 migration、修改模型 |
| Bash | 执行 `alembic upgrade/downgrade` |
| `run_tests` | 运行数据库相关测试 |

## 检查清单

- [ ] schema 变更通过 migration 管理
- [ ] migration 可向前和向后执行（upgrade/downgrade）
- [ ] 新增列有默认值或允许 NULL（兼容旧代码）
- [ ] 查询热点列有索引
- [ ] 外键约束正确定义
- [ ] 数据回填分批次执行（避免锁表）
- [ ] 大表操作使用 `CONCURRENTLY` 创建索引
- [ ] 事务范围合理（不过大也不过小）

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 手动改数据库 schema | 通过 migration 管理 |
| SELECT * 查全列 | 只查需要的列 |
| N+1 查询 | 使用 join / eager load |
| 无索引的外键查询 | 为外键添加索引 |
| 大事务锁全表 | 分批次小事务 |
| 直接删除列 | 先停止使用再删除 |
| 字符串拼接 SQL | 参数化查询 |

## 输出要求

1. 提供 migration 文件（upgrade + downgrade）
2. 提供更新后的 ORM 模型
3. 说明索引变更和性能影响
4. 提供数据回填脚本（如需要）
5. 说明向前兼容性策略
---
name: database
description: >-
  Use this skill for schema changes, migrations, SQL, ORM models, indexes,
  transactions, data backfills, and persistence-layer bugs.
work_modes: [coding]
---

