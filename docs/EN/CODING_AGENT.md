# Coding Agent Implementation Notes

Coding Agent is OClaw's dedicated coding workbench for real code projects. It is not simply connecting normal chat tasks to a project directory; rather, it adds a separate Qiongqi runtime boundary within OClaw: independent sessions, independent memory, independent scratch workspace, independent skills, and independent diff/review/ROI event pipelines.

This document describes the current frontend and backend implementation, data boundaries, core workflows, and known boundaries.

## Design Goals

The goal of Coding Agent is to let the agent complete engineering tasks without polluting normal OClaw tasks or the user's project root directory:

- Project-aware: Bound to a local project path, browse files, view code, read Git diffs.
- Runtime isolation: Coding sessions, active skills, events, ROI, and intermediate files are isolated from normal tasks.
- Engineering closed loop: From requirements, design, implementation, verification, review to delivery, forming reusable workflows.
- Change visibility: Frontend can see project diffs, task changes, Qiongqi events, ROI, and code review conclusions.
- Review executable: Code Review is based on project diffs, task changes, Qiongqi events, and PR context, not just text suggestions.

## Overall Architecture

```text
frontend/src/app/workspace/coding
        |
        v
frontend/src/components/workspace/coding
        |
        v
frontend/src/core/projects/api.ts
        |
        v
backend/app/gateway/routers/*
        |
        v
backend/app/gateway/coding_*_services.py
        |
        v
backend/packages/harness/kkoclaw/coding_core
        |
        v
~/.oclaw-coding/{thread_id}
```

The core boundary is divided into three layers:

- **Gateway API Layer**: HTTP interfaces for projects, files, diffs, sessions, events, changes, ROI, skills, reviews, etc.
- **Qiongqi Core Layer**: `coding_core` handles runtime context, skills, session store, change tracking, events, and ROI telemetry.
- **Coding Agent Adapter Layer**: `agents/coding_agent` connects the Qiongqi runtime into the existing agent graph and middleware.

## Backend Implementation

### Core Directories

Main implementation files:

- `backend/packages/harness/kkoclaw/coding_core/`
  - `qiongqi.py`: QiongqiEngine core runtime boundary (stable prompt + dynamic context + stage completion probes + project telemetry).
  - `context.py`: CodingRuntimeContext and scratch workspace resolution.
  - `session_store.py`: Independent session, events, ROI, change summary persistence.
  - `skills.py`: Coding-only skill registry with enable states (including semantic activation: synonym mapping + description token overlap).
  - `change_tracking.py`: Per-thread/task file change aggregation.
  - `edit_snapshots.py`: Edit transaction snapshot store (append-only jsonl, supports undo).
  - `delivery_stages.py`: 7-stage delivery workflow definitions and completion_signals.
  - `events.py`: Qiongqi event record format.
  - `roi_telemetry.py`: ROI report recording and aggregation.
- `backend/packages/harness/kkoclaw/agents/coding_agent/`
  - `agent.py`: Coding Agent graph adapter (middleware chain registration for PostEditVerifyMiddleware, etc.).
  - `runtime.py`: Runtime context assembly.
  - `skills_middleware.py`: Coding skills injection.
  - `tool_policy_middleware.py`: Tool policy injection.
  - `roi_middleware.py`: ROI telemetry collection.
  - `prompt.py`: Coding prompt assembly.
- `backend/packages/harness/kkoclaw/agents/middlewares/`
  - `post_edit_verify_middleware.py`: Lightweight TDD-first + edit→verify closed-loop middleware
- `backend/packages/harness/kkoclaw/tools/coding/`
  - `file_read.py`, `file_edit.py`, `git_tools.py`, `pr_tools.py`, `test_tools.py`, `worktree.py`
  - `symbol_tools.py`: Symbol-level navigation (find_symbols / read_symbol, supports Python/JS-TS/Go/Rust)
  - `refactor_tools.py`: Structured refactoring (rename_symbol / extract_function)
  - `undo_tools.py`: Edit transaction rollback (undo_last_edit / list_edit_snapshots)

Gateway services:

- `backend/app/gateway/coding_services.py`, `coding_session_services.py`, `coding_event_services.py`, `coding_change_services.py`, `coding_roi_services.py`, `coding_skill_services.py`, `coding_review_services.py`

Corresponding routers: `projects.py`, `coding_sessions.py`, `coding_events.py`, `coding_changes.py`, `coding_roi.py`, `coding_skills.py`, `coding_review.py`

### QiongqiEngine

`QiongqiEngine` is the core boundary of Coding Agent. It organizes the stable system prompt, dynamic project context, Coding skills, tool catalog fingerprint, and ROI metadata needed for coding tasks into an independent runtime.

### Session, Memory & Scratch Isolation

Coding Agent does not reuse normal OClaw task memory. The Qiongqi session store uses an independent directory under the user's home directory:

```text
~/.oclaw-coding/{thread_id}/
├── session.json
├── events.jsonl
├── roi.jsonl
├── changes/
├── reviews/
│   └── {review_id}.json
└── workspace/
```

### Coding Skills

Coding skills are separated from OClaw global skills, independently discovered and managed by `CodingSkillRegistry`. Discovery order: `{project_root}/.oclaw-coding/skills` → `~/.oclaw-coding/skills` → `skills/public/coding`. Currently 59 built-in Coding skills covering the full engineering pipeline.

### API Surface

| Capability | API |
|------|-----|
| Project list/create/delete | `/api/projects` |
| File tree | `/api/projects/{project_id}/files` |
| File content | `/api/projects/{project_id}/file` |
| Project diff | `/api/projects/{project_id}/diff` |
| Discard single file changes | `/api/projects/{project_id}/diff/discard` |
| Worktree management | `/api/projects/{project_id}/worktrees` |
| Qiongqi session | `/api/coding/sessions/{thread_id}` |
| Qiongqi events | `/api/coding/sessions/{thread_id}/events` |
| Task changes | `/api/coding/sessions/{thread_id}/changes` |
| ROI summary | `/api/coding/sessions/{thread_id}/roi/summary` |
| ROI report list | `/api/coding/sessions/{thread_id}/roi` |
| Coding skills | `/api/coding/skills` |
| Code Review | `/api/coding/reviews` |
| Latest Review | `/api/coding/sessions/{thread_id}/review` |
| Apply Review fixes | `/api/coding/reviews/fixes/apply` |

### Project Diff, Task Changes, Events & ROI

The Coding Agent frontend breaks down the task execution process into several auditable perspectives: Project Diff (Git diff), Task Changes (Qiongqi change tracker), Events (Qiongqi event stream), and ROI.

### Code Review & PR Review

`CodingReviewService` supports two review scopes: `project_diff` and `pr`. Review input merges project diff file list, Qiongqi task changes, Qiongqi events, and PR context. Reviews use `decision`: `request_changes`, `needs_review`, or `pass`.

### One-Click Fix Security Model

Deterministic, conservative security fixes: replace hardcoded secrets with env vars, normalize whitespace, add .env to .gitignore, create test skeletons.

### Frontend Workbench

Three-panel workbench: Left (file tree), Center (code, task changes, project diff, results, Code Review), Right (Agent Inspector with conversation, events, session, ROI, workflow, skills).

### Workflow Panel

Breaks down the project delivery process into stages: Requirements → Design → Init → Implement → Verify → Review → Deliver. Cold start auto-enters Requirements stage.

### Current Boundaries & Future Directions

Completed core capabilities include: independent QiongqiEngine, session/memory/scratch isolation, 59 built-in Coding skills, file browsing/diff, symbol-level semantic navigation, structured refactoring tools, edit transaction rollback, PostEditVerifyMiddleware, TDD-first guard, test result structured parsing, Qiongqi events/changes/ROI, diff/task/events/PR context-based Code Review, Python secret one-click fix, three-panel workbench, delivery stage state machine, file_changed custom event, TodoMiddleware user interaction gate, end-to-end state bridging.

Future enhancements: upgrade TDD-first guard to explicit TDD state machine, red-light semantic parsing, TDD state visualization, exception rules for non-production changes, hard mode, cross-branch PR review strategies, precise line mapping, project-private skills governance, cross-file rename.

### Architecture Evolution Proposals (Optional)

**Option B (Optional)**: Hybrid architecture — LangGraph runs loops, Node runs control flow. **Option C (Optional)**: Full migration to Node+Express. Primary recommendation: complete Option A gap-filling first, observe whether architecture bottlenecks remain.
