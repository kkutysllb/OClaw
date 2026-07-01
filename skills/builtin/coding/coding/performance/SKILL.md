---
name: performance
description: >-
  Use this skill when the user asks to improve speed, latency, throughput,
  memory use, rendering performance, query efficiency, or startup time.
work_modes: [coding]
---

# Performance Optimization

## 适用场景

- 用户反馈页面加载慢、API 响应慢、操作卡顿
- 需要优化数据库查询效率、减少内存使用
- 前端渲染性能优化（首屏加载、交互延迟）
- 后端吞吐量和延迟优化

## 核心原则

1. **测量先行**：优化前必须有基线数据，优化后必须有对比数据
2. **瓶颈驱动**：只在真正的瓶颈处优化，遵循 Amdahl 定律
3. **渐进优化**：每次只优化一个维度，验证效果后再继续
4. **不过度优化**：满足性能目标后停止，不为微优化牺牲可读性
5. **回归保护**：优化后必须有测试保证功能正确

## 执行流程

### 1. 建立基线

```bash
# 后端 API 响应时间
time curl -s http://localhost:8000/api/endpoint

# 前端性能（Lighthouse）
npx lighthouse http://localhost:3000 --output json --output-path ./lighthouse-report.json

# 数据库慢查询
# 启用 pg_stat_statements 或 EXPLAIN ANALYZE

# 内存使用
# Python: tracemalloc / memory_profiler
# Node.js: --inspect + Chrome DevTools Memory
```

### 2. 前端性能优化

| 优化方向 | 具体措施 |
|---------|---------|
| **首屏加载** | 代码分割（dynamic import）、SSR/SSG、预加载关键资源 |
| **包体积** | Tree shaking、按需引入、分析 bundle（webpack-bundle-analyzer） |
| **渲染性能** | 虚拟列表（大数据量）、useMemo/useCallback、避免不必要的 re-render |
| **图片优化** | next/image、WebP/AVIF、lazy loading、响应式图片 |
| **缓存** | HTTP 缓存头、SWR/React Query 客户端缓存 |
| **字体** | font-display: swap、preload 关键字体 |

```javascript
// 代码分割
const DynamicComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false,  // 不需要 SEO 的重量级组件
});

// 虚拟列表（大数据量）
import { FixedSizeList } from 'react-window';
<FixedSizeList height={600} itemCount={10000} itemSize={35}>
  {Row}
</FixedSizeList>
```

### 3. 后端性能优化

| 优化方向 | 具体措施 |
|---------|---------|
| **数据库查询** | 添加索引、避免 N+1、批量查询、SELECT 指定列 |
| **缓存** | Redis 缓存热点数据、内存缓存计算结果 |
| **并发** | 异步 I/O（async/await）、连接池、批量处理 |
| **序列化** | 高效序列化（orjson 替代 json） |
| **CDN** | 静态资源走 CDN |

```python
# 避免 N+1 查询
# ❌ 慢：每个 order 都查一次 user
for order in orders:
    print(order.user.name)

# ✅ 快：一次 join 查询
orders = session.query(Order).options(joinedload(Order.user)).all()

# Redis 缓存
@cache(ttl=300)
def get_user_stats(user_id):
    return expensive_computation(user_id)

# 异步批量处理
async def process_batch(items):
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)
```

### 4. 数据库性能

```sql
-- 分析慢查询
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
JOIN users ON orders.user_id = users.id
WHERE orders.status = 'pending'
ORDER BY orders.created_at DESC LIMIT 20;

-- 常见优化
-- 1. 添加缺失索引
CREATE INDEX CONCURRENTLY idx_orders_status_created
ON orders(status, created_at DESC);

-- 2. 避免全表扫描
-- 3. 限制返回行数（LIMIT）
-- 4. 避免 SELECT *
```

### 5. 验证优化效果

```
优化前基线：
- API 响应：500ms
- 首屏加载：3.2s
- Lighthouse 性能分：65

优化后：
- API 响应：120ms ✅（-76%）
- 首屏加载：1.5s ✅（-53%）
- Lighthouse 性能分：92 ✅（+27）
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| Bash | 运行性能测试、分析工具 |
| `read_file` | 阅读被优化代码 |
| `apply_diff` / `multi_edit` | 应用优化修改 |
| `run_tests` | 确保优化不破坏功能 |

## 检查清单

- [ ] 建立了优化前基线数据
- [ ] 识别了真正的性能瓶颈
- [ ] 每次只优化一个维度
- [ ] 优化后有数据对比
- [ ] 功能测试全部通过
- [ ] 无内存泄漏引入
- [ ] 达到了性能目标

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 不测量就优化 | 先建立基线，找到瓶颈 |
| 微优化低频路径 | 集中优化高频关键路径 |
| 牺牲可读性换性能 | 除非证明是瓶颈，否则优先可读性 |
| 一次性大改 | 每次一个优化，逐步验证 |
| 不写性能回归测试 | 关键路径加性能断言 |

## 输出要求

1. 提供优化前基线数据
2. 分析性能瓶颈及根因
3. 提供优化方案和代码修改
4. 提供优化后对比数据
5. 说明是否达到性能目标
---
name: performance
description: >-
  Use this skill when the user asks to improve speed, latency, throughput,
  memory use, rendering performance, query efficiency, or startup time.
work_modes: [coding]
---

