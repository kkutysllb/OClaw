# Changelog

## v0.1.9 - 2026-07-06

Compare: `v0.1.8...v0.1.9`

- 要求用户把凭证 export 在 ~/.zshrc/~/.bash_profile 里（当前机器已满足）。如果用户没在 shell rc 里设置、也没在 ~/.kkoclaw-desktop/.env 里配置，凭证仍会缺失——但那是用户配置问题，不再是系统缺陷。请重新打包桌面端验证。 (a9bb7d4)
- fix(desktop): gateway 继承用户登录 shell 环境变量，修复 agent 工具失效 (009653b)
- docs(config): 修正 token_economy / circuit_breaker 注释与实际行为一致 (a55902f)
- refactor(settings): 移除上下文摘要/Token 经济的前端设置 UI (f145edf)
- fix(config): 上下文压缩/摘要改为内置默认启用，修配置错误值 (a5fbcf9)
- style(queue): 纵向长条列表替代横向卡片 (bbe19de)
- fix(queue): make currentRunId reactive so inject works in packaged build (dda72f9)
- 修复前端权限切换bug (b13423b)

## v0.1.8 - 2026-07-06

Compare: `v0.1.7...v0.1.8`

- fix(chat-box): split layout constants for 2 vs 3 panel modes (a5fe243)
- fix(coding): wrap coding ChatBox with TodosProvider (55e2ea9)

## v0.1.7 - 2026-07-06

Compare: `v0.1.6...v0.1.7`

- fix(threads): defer queue auto-send to isLoading effect to fix duplicate message (bd060a4)
- chore(todo-list): remove dead 'hidden' prop (defe336)
- feat(integration): wire onFinish auto-send + InputBox queue props (108749a)
- test(layout): update disabled-artifacts assertion for two-panel mode (60dd87c)
- refactor(pages): remove inline TodoList floating-bar usage (1a13382)
- feat(layout): three-panel layout (chat | todos | artifacts) (a29cd8d)
- feat(i18n): add queue and todoPanel keys (zh + en) (990ac4c)
- feat(todos): add TodoTrigger button (仿 ArtifactTrigger) (1a09485)
- feat(todos): add TodosProvider context with localStorage persistence (3db4467)
- feat(input): streaming 时发送=入队, 停止按钮独立化 (8391d59)
- feat(ui): add QueuedMessagesBar component (cbc9da4)
- fix(queue): guard autoSendNext against concurrent calls + add retry test (d2a6e6d)
- feat(threads): add useQueueCoordinator hook (865b9fa)
- feat(api): add injectMessage API call for /inject route (de76a7e)
- feat(threads): add queue-store with localStorage persistence (49bb90f)
- feat(agent): register InjectMiddleware in lead_agent chain (bdd3b3b)
- refactor(inject): use inline get_run_manager + add 500 path test (ec6d299)
- feat(gateway): add POST /inject route for mid-run message injection (c41a6cb)
- feat(middleware): add InjectMiddleware for supplement-context injection (0f9ca21)
- test(state): cover keep/None states and within-right dedup (93b0fbb)
- feat(state): add pending_messages field with merge_pending_messages reducer (39d8e65)
- 文件: backend/packages/harness/kkoclaw/skills/validation.py (f599e54)

## v0.1.6 - 2026-07-05

Compare: `v0.1.5...v0.1.6`

- 报错: Security scan rejected executable announcement-search/scripts/__main__.py: Borderline external API references... (ca5f618)

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

