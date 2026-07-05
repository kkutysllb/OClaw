# Changelog

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

