---
name: typescript
description: >-
  Use this skill for TypeScript typing, strictness errors, generics, React prop
  types, API contracts, discriminated unions, and type-safe refactors.
work_modes: [coding]
---

# TypeScript

## 适用场景

TypeScript 类型工作：类型定义、严格模式错误、泛型、React props 类型、API 契约、可辨识联合（discriminated unions）、类型安全重构。

## 核心原则

1. **严格模式优先**：`strict: true`，让编译器帮你抓错。
2. **类型驱动**：先定义类型/接口，再写实现。
3. **避免 any**：用 `unknown` + 类型守卫，或具体的联合类型。
4. **类型即文档**：好的类型定义就是最好的 API 文档。
5. **不过度抽象类型**：类型层应匹配业务复杂度，别为了炫技搞复杂泛型。

## 执行流程

### 1. 确认 tsconfig
- 检查 `strict` / `noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` 等严格选项
- 理解项目的类型严格程度基线

### 2. 定义类型
**基础类型**
```typescript
interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "user";  // 字面量联合
  metadata?: Record<string, unknown>;
}
```

**可辨识联合（Discriminated Unions）**
```typescript
type Result<T> =
  | { status: "success"; data: T }
  | { status: "error"; error: string };

// 使用时类型守卫
if (result.status === "success") {
  console.log(result.data);  // T
}
```

**泛型**
```typescript
async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  return res.json() as T;
}
```

### 3. React 组件类型
```typescript
interface ButtonProps {
  variant?: "primary" | "secondary";
  size?: "sm" | "md" | "lg";
  onClick: () => void;
  children: React.ReactNode;
}

function Button({ variant = "primary", size = "md", ... }: ButtonProps) { }
```

### 4. API 契约类型
- 请求/响应用 Zod / valibot 运行时校验 + 类型推导
```typescript
const UserSchema = z.object({ id: z.string(), email: z.string().email() });
type User = z.infer<typeof UserSchema>;
```

### 5. 常见类型错误修复
| 错误 | 修复 |
|---|---|
| `Object is possibly 'null'` | 加空值检查或 `?.` 可选链 |
| `Property does not exist on type` | 检查类型定义或用类型守卫收窄 |
| `Type 'X' is not assignable to 'Y'` | 理解类型不兼容的根因，不要用 as 强转 |
| `Element implicitly has 'any' type` | 显式声明数组/对象类型 |

## 工具优先级

| 场景 | 工具 | 用途 |
|---|---|---|
| 类型检查 | `run_linter`（tsc --noEmit） | 发现类型错误 |
| 找类型定义 | `search_code "interface\|type "` | 现有类型 |
| 读类型 | `read_file_lines` | 理解 |
| 编辑 | `apply_diff` | 修改 |

## 检查清单

- [ ] tsconfig strict 模式开启
- [ ] 无 any（必要的用 unknown）
- [ ] 接口/类型定义清晰
- [ ] 联合类型有判别字段（可辨识）
- [ ] `run_linter`（tsc）无错误
- [ ] React props 有明确类型

## 反模式

| ❌ 避免 | ✅ 应该 |
|---|---|
| `any` 图省事 | `unknown` + 类型守卫 |
| `as` 强转绕过类型 | 修复类型不兼容的根因 |
| 类型定义和实现脱节 | 类型驱动开发 |
| 过度复杂的泛型 | 匹配业务复杂度 |
| 不启用 strict | 开启 strict 选项 |

## 输出要求

1. **类型定义**：核心 interface/type
2. **严格模式状态**：tsconfig 关键选项
3. **类型错误修复**：遇到的错误及修复
4. **验证**：tsc --noEmit 无错误的输出
---
name: typescript
description: >-
  Use this skill for TypeScript typing, strictness errors, generics, React prop
  types, API contracts, discriminated unions, and type-safe refactors.
work_modes: [coding]
---

