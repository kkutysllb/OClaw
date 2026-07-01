---
name: skill-authoring
description: >-
  Use this skill when creating, improving, or reviewing OClaw Coding skills,
  including SKILL.md content, activation descriptions, built-in skill coverage,
  and skill registry tests.
work_modes: [coding]
---

# Skill Authoring

## 适用场景

- 创建新的 OClaw Coding Skill（编写 SKILL.md）
- 改进现有 skill 的内容质量或激活描述
- 审查 skill 覆盖度和激活准确性
- 维护 skill 注册表和测试

## 核心原则

1. **激活优先**：skill 的 description 决定何时激活，必须覆盖关键触发词
2. **内容实用**：正文提供可执行的指导，不是泛泛的理论
3. **格式一致**：所有 skill 遵循统一的结构模板
4. **可测试**：skill 的激活和内容可通过测试验证
5. **不冗余**：每个 skill 有明确的边界，不与其他 skill 重叠

## 执行流程

### 1. SKILL.md 结构规范

```markdown
---
name: skill-name
description: >-
  Use this skill when [触发场景]. Trigger on [关键词/同义词].
  Also trigger for [扩展场景].
work_modes: [coding]
---

# Skill Title

## 适用场景
- 列出具体的使用场景

## 核心原则
1-5 条带编号的原则

## 执行流程
分步骤的执行指导

## 工具优先级
| 工具 | 用途 |
表格形式

## 检查清单
- [ ] checkbox 列表

## 反模式
| ❌ 避免 | ✅ 应该 |
对比表格

## 输出要求
1-5 条编号要求
```

### 2. 编写 Description（激活关键）

Description 是 skill 激活的核心，决定了 `matches_skill_semantic` 能否正确匹配。

```yaml
# ✅ 好的 description
description: >-
  Use this skill when the user asks to implement a feature, add functionality,
  or build something new in code. Trigger on requests like "implement this
  feature", "add this function", "create this endpoint", "build this module",
  "write a function that", "add support for", or when the user provides a
  specification, requirements document, or user story for implementation.

# ❌ 差的 description（太短、缺少触发词）
description: >-
  Use this skill for implementing features.
```

#### Description 编写要点

| 要点 | 说明 |
|------|------|
| **列出触发场景** | "Use this skill when..." |
| **包含同义词** | implement/add/create/build/write |
| **包含用户语言** | "implement this feature", "add this function" |
| **覆盖扩展场景** | "Also trigger for..." |
| **长度适中** | 3-6 行，覆盖主要关键词 |

### 3. 正文内容质量标准

| 部分 | 质量标准 |
|------|---------|
| **适用场景** | 3-5 个具体场景，不是泛泛的描述 |
| **核心原则** | 3-5 条原则，每条有明确的"为什么" |
| **执行流程** | 分步骤，每步有具体操作 |
| **工具优先级** | 列出该 skill 最常用的工具及用途 |
| **检查清单** | 5-10 个 checkbox，可验证完成度 |
| **反模式** | 对比表格，帮助避免常见错误 |
| **输出要求** | 明确用户能预期什么输出 |

### 4. 创建新 Skill

```bash
# 1. 创建目录
mkdir -p skills/builtin/coding/coding/new-skill

# 2. 创建 SKILL.md
# 遵循上述结构规范编写

# 3. 验证 frontmatter 格式
# name 必须与目录名一致
# description 必须包含触发词
# work_modes 必须包含 coding
```

### 5. Skill 覆盖度审查

定期检查：
- 是否有常见的用户请求没有被任何 skill 覆盖？
- 是否有多个 skill 的 description 过度重叠（导致歧义激活）？
- 是否有 skill 的 description 缺少关键触发词？

### 6. 测试验证

```python
# skill 注册表测试
def test_skill_registered():
    skills = load_coding_skills()
    assert "new-skill" in [s.name for s in skills]

def test_skill_has_content():
    skill = load_skill("new-skill")
    assert len(skill.content) > 100  # 有实质内容
    assert "## 核心原则" in skill.content
    assert "## 检查清单" in skill.content

def test_skill_activation():
    # 测试关键触发词能激活
    result = matches_skill_semantic("implement this feature", skill)
    assert result.matched
```

## 工具优先级

| 工具 | 用途 |
|------|------|
| `write_file` | 创建/修改 SKILL.md |
| `read_file` | 审查现有 skill 内容 |
| `grep` | 检查触发词覆盖 |
| `run_tests` | 验证 skill 注册和激活 |

## 检查清单

- [ ] frontmatter 格式正确（name/description/work_modes）
- [ ] description 包含充分的触发词和同义词
- [ ] 正文有完整的结构（适用场景/原则/流程/检查清单/反模式）
- [ ] 正文内容实用可执行
- [ ] 与其他 skill 无过度重叠
- [ ] skill 在注册表中正确加载
- [ ] 有对应的测试验证

## 反模式

| ❌ 避免 | ✅ 应该 |
|---------|--------|
| description 只有一句话 | 包含触发词、同义词、用户语言 |
| 正文是空壳 | 有实质的、可执行的指导 |
| 没有检查清单 | 有 5-10 个 checkbox |
| 与其他 skill 高度重叠 | 明确边界和差异化 |
| 没有 frontmatter | 正确的 YAML frontmatter |

## 输出要求

1. 提供格式合规的 SKILL.md（frontmatter + 完整正文）
2. description 覆盖充分的触发场景
3. 正文提供可执行的工程指导
4. 标注与其他 skill 的边界
5. 提供测试验证方案
---
name: skill-authoring
description: >-
  Use this skill when creating, improving, or reviewing OClaw Coding skills,
  including SKILL.md content, activation descriptions, built-in skill coverage,
  and skill registry tests.
work_modes: [coding]
---

