# Changelog

## v0.3.2 - 2026-07-18

Compare: `v0.3.1...v0.3.2`

- fix(desktop): enable allow_host_bash by default for desktop local environment (b98c7c1)
- fix(coding-ui): prevent empty-state hint from flashing on stop/resume (4f6cea6)
- fix(title): improve title generation prompt — emphasize user intent over assistant response (7c3a8a5)

## v0.3.1 - 2026-07-16

Compare: `v0.3.0...v0.3.1`

- Version metadata update.

## v0.3.0 - 2026-07-16

Compare: `v0.2.6...v0.3.0`

- fix more bug (85a50e6)
- fix(coding-ui): auto-hide todo panel when all tasks done + manual close button (1dc784e)
- fix(ui): hide scrollbars globally across all pages (not just coding workbench) (ced1a12)
- feat(coding-engine): systematic orchestration strengthening — scenario routing, stage-skill linkage, tool policy activation (d1fb2ee)
- feat(todo-list): improve task status indicators for better visual distinction (382a620)
- fix(coding-ui): remove status bar (Coding Agent label + status badge) from main area (25c13d4)
- feat(coding-ui): add floating TodoList panel below environment info card (ccbc82a)
- fix(coding-ui): force-hide scrollbar with !important + override scrollbar-gutter (811fb8a)
- fix(coding-ui): hide all scrollbars in coding workbench (scoped CSS) (564e823)
- fix(coding-ui): hide scrollbar in environment info floating card (cf1a794)
- refactor(coding-ui): remove 项目Diff and 结果 tabs + components (14a162c)
- fix(coding-ui): move left sidebar toggle to leftmost edge of toolbar (b526cb4)
- fix(coding-ui): fix sidebar toggle direction, remove duplicate terminal button (61b92c5)
- refactor(coding-ui): move ROI/流程/技能 to toolbar icons, remove 对话/session/事件 tabs (6b84321)

## v0.2.6 - 2026-07-15

Compare: `v0.2.5...v0.2.6`

- 修复一些bug (6ff79e0)
- fix(engine): MemoryMiddleware.after_agent get_config() NameError → ensure_config() (0b0e051)
- refactor(engine): merge tools.py with deer-flow (additive) — review_skill_package, sync-tool wrapper, mcp tagging (86a9298)
- feat(engine): port review_skill_package + update_agent tools; add preserve_non_managed_fields (d4fa3b9)
- feat(engine): unblock review/ skills package — add frontmatter/parser symbols (dff6e62)
- feat(engine): unblock + wire read_before_write middleware (e5f7895)
- feat(engine): unblock + wire skill_activation middleware (9485f14)
- chore(engine): Batch 8 (Orchestrator) — context_compaction unblocked; agent/factory/prompt full-merge DEFERRED (82e3664)
- feat(engine): unblock context_compaction — add DeerFlowSummarizationMiddleware alias + create_summarization_middleware factory (943e703)
- test(engine): update dynamic_context test for SystemMessage date reminder (OWASP LLM01) (cbbb95b)
- refactor(engine): complete dynamic_context HumanMessage→SystemMessage migration for reminders (87739af)
- chore(engine): Batch 7 (Community/Sandbox/Scheduler/TUI) complete — 56 files ported, optional-dep buckets deferred (27cb613)
- feat(engine): port community providers + sandbox helpers + scheduler + workspace_changes + TUI from deer-flow (14ae393)
- chore(engine): Batch 6 (Skills) complete — 10/18 ported (incl slash unblocker), review/ deferred; skill_activation narrowed to 1 blocker (SecretRequirement) (83b2d56)
- feat(engine): port skills subsystem from deer-flow (catalog, review, skillscan, slash, user-scoped storage) (7143103)
- chore(engine): Batch 5 (Models) complete — patched_mimo/stepfun ported, factory.py merged (f1ed0e9)
- refactor(engine): merge models/factory.py from deer-flow (tracing dedup) + re-layer OClaw providers (c72d477)
- feat(engine): port patched_mimo + patched_stepfun providers from deer-flow (e84165d)
- chore(engine): Batch 4 (Tools & MCP) — partial complete (d5a5714)
- refactor(engine): merge MCP session_pool + tools from deer-flow (owner-task fix, name canonicalization, path pinning) (f3217d3)
- feat(engine): port tools/mcp_metadata.py from deer-flow (6d11ac4)
- chore(engine): Batch 3 (Middlewares) complete — 9 upstream middlewares wired into canonical chain (gated), 2 deferred; engine.upstream_middlewares flag verified (7831ac6)
- refactor(engine): rebuild _build_middlewares to canonical merged chain (upstream middlewares gated by engine.upstream_middlewares) (eefe6e6)
- feat(engine): add engine.upstream_middlewares feature flag (db9b3a3)
- feat(engine): port 11 upstream middlewares from deer-flow (95042c8)
- test(engine): pin dynamic_context SystemMessage reminder parity (unblocks coalescing middleware) (6ca908f)
- feat(engine): port middleware helpers + thread_state skill/delegation channels + status_contract (b6b1d5a)
- chore(engine): Batch 2 (Runtime & Persistence) complete — runtime modules, persistence models, bootstrap, idempotent migration chain, shared-file merges (0332f6b)
- refactor(engine): merge shared runtime/persistence files to deer-flow main + re-layer OClaw (1018c7d)
- refactor(engine): reconcile alembic chain — idempotent 0001_baseline + 0002-0004 + rebase OClaw migrations to 0005-0007 (061be92)
- feat(engine): port persistence/bootstrap + migration helpers from deer-flow (6d07a0a)
- feat(engine): port upstream persistence models (channel_connections, scheduled_tasks, scheduled_task_runs) (ba16be6)
- feat(engine): port 5 upstream runtime modules (context_compaction, context_keys, goal, secret_context, stream_bridge/redis) (c9da2af)
- chore(engine): Batch 1 (Foundation) complete — config/constants/logging/utils synced to deer-flow (57f0efc)
- refactor(engine): merge deer-flow AppConfig fields into kkoclaw (+13 fields, preserve OClaw fields) (08f7c62)
- feat(engine): port utils/{llm_text,oneshot_llm,messages,file_io} from deer-flow (87fe28a)
- refactor(engine): sync config/paths.py to deer-flow main + re-layer OClaw paths (f8b95e0)
- feat(engine): port 12 standalone config modules from deer-flow (0b0eaa8)
- feat(engine): port trace_context + logging_config from deer-flow (e3fad9b)
- feat(engine): port constants.py from deer-flow (DEFAULT_SKILLS_CONTAINER_PATH) (852e517)
- chore(engine): add engine_parity_diff tool for deer-flow resync (bb68ce9)
- chore: ignore .worktrees/ for isolated worktrees (9c10596)

## v0.2.5 - 2026-07-13

Compare: `v0.2.4...v0.2.5`

- Allow .skill installs when security scan is unavailable (cc4ccbc)

## v0.2.4 - 2026-07-12

Compare: `v0.2.3...v0.2.4`

- feat(input-box): 根据输入内容智能切换停止与发送按钮状态 (fdd68e3)

## v0.2.3 - 2026-07-09

Compare: `v0.2.2...v0.2.3`

- fix: 修复工作区产出路径、历史任务同步删除及命令渲染不全问题 (07f0347)

## v0.2.2 - 2026-07-08

Compare: `v0.2.1...v0.2.2`

- fix(artifacts): percent-encode artifact URLs to fix non-ASCII filenames (ef88e12)

## v0.2.1 - 2026-07-08

Compare: `v0.2.0...v0.2.1`

- feat(settings): remove data import / web-to-desktop migration feature (c1016bc)
- feat(sidebar): prefetch thread state on hover to eliminate switch flicker (0d3a9fa)
- fix(artifacts): restore leading slash stripped by FastAPI path converter (8317829)

## v0.2.0 - 2026-07-08

Compare: `v0.1.9...v0.2.0`

- fix(desktop): .env parser strips shell-style `export` prefix (a3400c7)
- 当前项目发布版本自动更新新版本后点击重启更新，但是需要手动退出后才能完成，无法自动重启更新 (5d557e5)
- refactor(sandbox): remove /mnt/user-data virtual path layer (phase 3) (d5d77e5)
- refactor(sandbox): remove permission_scope + granted_paths auth (phase 2) (91a3434)
- refactor(sandbox): remove Docker/AioSandbox container scheme (phase 1) (ad079c6)

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

