---
name: migration
description: >-
  Use this skill for code migrations, framework upgrades, API transitions,
  data/schema migrations, file layout moves, and compatibility shims.
work_modes: [coding]
---

# Migration

## 适用场景

- 框架/库版本升级（Next.js 14→15、Python 3.11→3.12、React 17→18）
- API 版本迁移（REST→GraphQL、v1→v2 端点）
- 代码结构迁移（单体→微服务、JS→TS、CJS→ESM）
- 数据格式迁移（文件格式、配置格式、数据 schema）

## 核心原则

1. **渐进式迁移**：大迁移拆成小步骤，每步可验证可回退
2. **双写过渡**：迁移期间新旧路径同时工作，数据双写保证一致
3. **兼容层优先**：先加兼容 shim，验证新路径，再删旧代码
4. **自动化验证**：迁移有测试覆盖，确保行为不变
5. **文档追踪**：记录迁移计划、进度和决策

## 执行流程

### 1. 评估迁移范围

```
迁移评估清单：
- 涉及哪些文件/模块？
- 有多少处需要修改？（grep 统计）
- 是否有 breaking change？
- 迁移期间能否保持运行？
- 回退方案是什么？
```

### 2. 渐进式迁移策略

```
阶段 1：准备
├── 新增目标实现（新版本/新路径/新格式）
├── 添加兼容层/shim
└── 新功能使用新路径

阶段 2：迁移
├── 逐模块切换到新路径
├── 双写保证数据一致
└── 每步验证 + 测试

阶段 3：清理
├── 确认无代码使用旧路径
├── 删除旧代码和兼容层
└── 更新文档
```

### 3. 常见迁移模式

#### 框架升级

```bash
# 1. 查看迁移指南
# 2. 在新分支上升级
pnpm add next@15

# 3. 运行 codemod 自动迁移
npx @next/codemod@latest upgrade

# 4. 修复手动问题
# 5. 测试
pnpm test && pnpm build
```

#### JS → TypeScript

```
1. 配置 allowJs: true + checkJs: false
2. 逐文件重命名 .js → .ts
3. 添加类型注解
4. 逐步开启严格模式（strict: true）
5. 最终移除 allowJs
```

#### CJS → ESM

```javascript
// 兼容方案：同时支持 CJS 和 ESM
// package.json
{
  "exports": {
    "import": "./dist/index.mjs",
    "require": "./dist/index.cjs"
  }
}

// 逐步将 require() 改为 import
```

#### API 版本迁移

```python
# 兼容层模式
@app.route("/api/v1/users")  # 旧版本，保留
async def get_users_v1():
    return await user_service.get_users_v1()

@app.route("/api/v2/users")  # 新版本
async def get_users_v2():
    return await user_service.get_users_v2()

# v1 标记 deprecated，添加迁移提示
```

#### 数据格式迁移

```python
# 读取时自动迁移格式
def load_config(path):
    data = json.load(open(path))
    version = data.get("version", 1)

    if version == 1:
        data = migrate_v1_to_v2(data)
        version = 2

    if version == 2:
        data = migrate_v2_to_v3(data)
        version = 3

    return data
```

### 4. 迁移验证

| 验证项 | 方法 |
|-------|------|
| **功能等价** | 迁移前后行为一致（对比测试） |
| **性能不退化** | 基准测试对比 |
| **API 兼容** | 旧客户端仍可工作 |
| **数据完整** | 数据量/校验和一致 |
| **无遗漏** | grep 确认无旧 API 调用残留 |

### 5. 回退方案

- 每个阶段都有独立的 Git commit/tag
- 如果新阶段出现问题，`git revert` 回到上一阶段
- 双写期间数据可双向同步

## 工具优先级

| 工具 | 用途 |
|------|------|
| `grep` | 统计旧 API/模式的使用数量 |
| `read_file` | 理解旧代码逻辑 |
| `apply_diff` / `multi_edit` | 批量替换 |
| `run_tests` | 每步迁移后验证 |
| `run_linter` | 检查新代码规范 |

## 检查清单

- [ ] 评估了迁移范围和影响
- [ ] 制定了渐进式迁移计划
- [ ] 添加了兼容层/shim（如需要）
- [ ] 每步迁移后有测试验证
- [ ] 旧代码在确认无使用后删除
- [ ] 文档已更新
- [ ] 回退方案已准备

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| 一次性大爆炸迁移 | 渐进式迁移，每步可验证 |
| 迁移期间删除旧代码 | 先确认新代码工作再删旧 |
| 不写测试就迁移 | 先补测试锁定行为，再迁移 |
| 不记录迁移进度 | 追踪计划、进度和决策 |
| 忽略 breaking change | 明确标注并提供迁移指南 |

## 输出要求

1. 提供迁移评估报告（范围、风险、计划）
2. 提供渐进式迁移步骤
3. 每步提供验证方法
4. 提供兼容层代码（如需要）
5. 提供回退方案
---
name: migration
description: >-
  Use this skill for code migrations, framework upgrades, API transitions,
  data/schema migrations, file layout moves, and compatibility shims.
work_modes: [coding]
---

