# Changelog

## v0.1.5 - 2026-07-05

Compare: `v0.1.4...v0.1.5`

- 报错: Invalid skill: Unexpected key(s) in SKILL.md frontmatter: keywords (399a643)
- 报错: Security scan rejected executable announcement-search/scripts/__main__.py: Borderline external API references... (7c9fed8)

## v0.1.4 - 2026-07-05

Compare: `v0.1.3...v0.1.4`

- 增加侧边栏自定义工作模式动态菜单功能 (9e9c76b)
- 完成技能创建过程中技能扫描时长 (17981ad)
- 继续修复技能创建的bug (a54aae4)
- 新增的两种技能创建方式 (511cd52)
- 修复桌面端问题 (80cfce5)
- 1. subagent 卡顿根因 —— 错误循环 修复(tool_error_handling_middleware.py):把 Write access blocked by permission_scope、Unsafe absolute paths、outside the project root、Path requires user authorization 等模式加入 _UNRECOVERABLE_ERROR_PATTERNS。模型现在撞权限墙会立刻停止重试,而非耗尽 25 turns。 (1ae3c05)

## v0.1.3 - 2026-07-05

Compare: `v0.1.2...v0.1.3`

- 顺手修好了。现在 pnpm lint 不再扫 frontend/out 生成产物，并且源码里的 lint errors/warnings 也清完了。 (c50c386)
- 修复根因是前端实时流过滤只看了 message 自身字段，但 LangGraph SDK 把流式 metadata 放在 getMessagesMetadata(...).streamMetadata；另外 MiniMax 的 <think> 只在闭合标签出现后才会被旧 regex 剥离，流式半截会进主界面。 (96d59f3)

## v0.1.1 - 2026-07-05

Compare: `v0.1.0...v0.1.1`

- 完成打包脚本的bug修复 (12dd2d2)
- chore: add release lifecycle script (1c63f1f)
- 完成技能安装层面流程问题修复 (c71cc93)

## v0.1.2 - 2026-07-05

Compare: `v0.1.0...v0.1.2`

- chore: add release lifecycle script (1c63f1f)
- 完成技能安装层面流程问题修复 (c71cc93)

