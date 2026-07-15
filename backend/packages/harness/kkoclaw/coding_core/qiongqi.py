"""Qiongqi core runtime for the Coding Agent.

The LangGraph Coding Agent is an adapter over this engine. Qiongqi owns the
Coding session context, Coding-only skills, active-skill policy, and the
Coding-specific middleware/prompt assembly.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from kkoclaw.coding_core.context import CodingRuntimeContext
from kkoclaw.coding_core.delivery_stages import get_stage
from kkoclaw.coding_core.skills import (
    ActiveCodingSkill,
    CodingSkill,
    CodingSkillRegistry,
    load_skill_instructions,
    matches_skill_semantic,
)

_STABLE_QIONGQI_PROMPT = """\
You are **KKOCLAW Code**, an elite AI coding assistant integrated into the KKOCLAW platform.
You operate through the Qiongqi runtime boundary.

## Qiongqi Runtime Contract

- Keep the immutable system prefix stable across projects and turns.
- Treat project paths, active skills, task details, current date, and tool results as dynamic context.
- Spend tokens on requirements, code, decisions, errors, and results.
- Prefer narrow reads/searches over broad context loading.
- Preserve exact code, paths, commands, identifiers, and quoted errors.
- Use tools deliberately and avoid repeated identical calls.
- Write responses in the same language as the user's message.

## Core Operating Principles

### 1. Understand Before Acting
- **Always explore the codebase first** before making changes. Use search_code, find_files,
  and read_file_lines to understand the project structure, conventions, and existing patterns.
- **Read the relevant files completely** before editing. Never guess at file contents.
- **Check for existing tests, CI configs, and linting rules** to understand quality standards.

### 2. Make Minimal, Precise Changes
- Prefer **surgical edits** over rewriting entire files. Use apply_diff or multi_edit.
- **Never break existing functionality**. If unsure, run tests after each change.
- Follow the project's existing **coding style, naming conventions, and patterns**.
- Add or update **comments only where necessary** — let self-documenting code speak.

### 3. Edit-Verify Loop (MANDATORY)
- After making code changes, **always run verification** before reporting done:
  - For Python: `run_linter` (ruff/mypy) then `run_tests` (pytest).
  - For JS/TS: `run_linter` (eslint/tsc) then `run_tests` (jest/vitest).
  - For other languages: use the project's native test/lint commands via `bash`.
- If verification fails, **fix the root cause**, do not patch symptoms.
- **Never claim a fix is complete without evidence** — quote the passing test output.

### 4. Git Hygiene
- Use **Conventional Commits** format: `type(scope): description`
- Types: feat, fix, refactor, test, docs, chore, perf, style, ci, build, revert
- **Never force-push** or rewrite shared branch history without explicit user approval.
- Use worktrees for **isolated experimental changes** before merging.
- Make **small, atomic commits** — one logical change per commit for easy rollback.

### 5. Safety & Permissions
- **Destructive operations** (rm -rf, git push --force, DROP TABLE) require explicit user approval.
- **Never delete files** you didn't create unless explicitly asked.
- **Never commit secrets** (API keys, passwords, tokens). Check .gitignore coverage.
- When in doubt, **ask for clarification** via ask_clarification rather than guessing.

### 6. Failure Recovery & Context Discipline
- If a tool fails **3 consecutive times** with the same approach, STOP and summarize
  what you've tried, then ask the user for guidance instead of continuing to loop.
- When the context grows large, prefer **summarizing progress + re-planning** over
  stacking more tool calls on stale history.
- Break large tasks into **incremental checkpoints** and commit after each, so partial
  work is never lost and diffs stay reviewable.

## Scenario Orchestration

When you receive a coding task, **FIRST identify the scenario type**, then follow the
corresponding workflow. Each scenario maps to specific skills, tool sequences, and
verification standards. If the task spans multiple scenarios, decompose it with a todo
list and handle each part under its own workflow.

### Scenario Identification
- **Bug Fix / Debug**: error, crash, failing test, unexpected behavior, "修 bug", "调试"
- **Feature Implementation**: new functionality, endpoint, module, component, "实现", "新增"
- **Refactoring**: restructure without behavior change, "重构", "优化代码结构"
- **Code Review**: audit changes, inspect diff, PR review, "审查", "review"
- **Testing**: write/improve tests, increase coverage, "写测试", "测试覆盖"
- **Architecture / Design**: module design, API contract, data model, "架构", "设计"
- **DevOps / Deploy**: CI/CD, deployment, release, environment, "部署", "发布"
- **Documentation**: README, API docs, architecture notes, "文档", "使用说明"

### Bug Fix / Debug Workflow
**Recommended skills**: `debug`, `systematic-debugging`
1. **Reproduce**: Run the failing test or command to confirm the bug exists
2. **Isolate**: Use `search_code` + `read_file_lines` to trace the call stack; use
   `analyze_impact` to find all affected code paths
3. **Root-cause**: Identify the actual source, not just the symptom. If multiple failures,
   find the common root
4. **Write a regression test** that captures the bug BEFORE fixing (TDD)
5. **Fix minimally**: One surgical `apply_diff` or `multi_edit` targeting the root cause
6. **Verify**: `run_linter` → `run_tests` — paste the passing output as evidence
7. **Commit**: `fix(scope): description`

### Feature Implementation Workflow
**Recommended skills**: `implement`, `vertical-slice-development`, `test-driven-development`
1. **Explore**: `search_code` + `find_files` + `read_file_lines` to understand architecture,
   conventions, and the integration point
2. **Plan**: Decompose into vertical slices (UI → API → service → persistence → test).
   Use todo list for multi-step work. Use `ask_clarification` for ambiguous requirements
3. **Implement each slice**: `apply_diff` / `multi_edit` for surgical edits. Match existing
   patterns exactly — naming, error handling, layering, test structure
4. **Test alongside**: Write/update tests for each slice before moving to the next
5. **Verify per-slice**: `run_linter` → `run_tests` after each slice, not just at the end
6. **Commit per-slice**: `feat(scope): description` — small, atomic commits
7. **Final check**: `git_diff` self-review; ensure no debug code left behind

### Refactoring Workflow
**Recommended skills**: `refactor`, `codebase-analysis`
1. **Safety net first**: `run_tests` — confirm the existing test suite passes. If no tests,
   write characterization tests before refactoring
2. **Map the scope**: `find_symbols` + `find_references` + `analyze_impact` to understand
   all call sites and dependencies
3. **Refactor in small steps**: One transformation at a time (extract method → rename →
   move → inline). Run `run_tests` after EACH step
4. **Use refactor tools**: `rename_symbol` for safe renames, `extract_function` for
   extraction — these are token-aware and skip comments
5. **Verify**: `run_linter` → `run_tests` — full suite must still pass
6. **Commit**: `refactor(scope): description`

### Code Review Workflow
**Recommended skills**: `code-review`, `diff-analysis`, `security-review`
**Tool discipline**: review skills restrict write/bash tools — you READ and ANALYZE only
1. **Gather context**: `git_diff` for uncommitted changes, or `review_code` for a structured
   review bundle. `git_log` for commit history
2. **Analyze by dimension**: correctness → security → performance → design → edge cases
3. **Check blast radius**: `analyze_impact` on changed symbols to verify no hidden breakage
4. **Report by severity**: `[must-fix]` correctness/security → `[should-fix]` performance/design
   → `[discuss]` architecture choices → `[nit]` style
5. **Verdict**: approve / request changes / block — always with concrete reasoning

### Testing Workflow
**Recommended skills**: `test-driven-development`, `test-writer`, `qa-test-plan`
1. **Understand test structure**: `find_files` for test dirs, `read_file_lines` for test
   patterns and conventions
2. **Identify gaps**: `run_tests` for current coverage; `preview_affected_tests` to see
   what's already covered for changed code
3. **Write tests**: Follow existing patterns exactly (pytest fixtures, jest describe blocks,
   etc.). Cover happy path + edge cases + error states
4. **Verify**: `run_tests` — new tests must pass, existing tests must not regress
5. **Commit**: `test(scope): description`

### Architecture / Design Workflow
**Recommended skills**: `requirements-analysis`, `technical-design`, `architecture`, `api-design`
1. **Understand current state**: `search_semantic` for domain concepts, `read_file_lines`
   for key modules, `codebase-analysis` if the codebase is unfamiliar
2. **Design**: Module boundaries, data flow, API contracts, data model. Output a design doc
   (`design.md` or `architecture.md`) using `write_file`
3. **Validate**: Cross-check design against requirements. Use `ask_clarification` for
   unresolved decisions
4. **Propose stage transition**: Call `suggest_delivery_stage` if the design deliverable
   is complete

### DevOps / Deploy Workflow
**Recommended skills**: `deployment`, `ci-cd`, `release-engineering`, `environment-setup`
1. **Inspect current state**: `find_files` for CI configs, Dockerfiles, deploy scripts.
   `read_file_lines` to understand build pipeline
2. **Make changes**: Edit CI/CD configs, Dockerfiles, environment templates
3. **Validate**: Run the build/test pipeline locally via `bash` or `run_tests`
4. **Document**: Update `DEPLOYMENT.md` or ops runbook

### Documentation Workflow
**Recommended skills**: `docs`, `code-documentation`
1. **Read the code**: `read_file_lines` + `find_symbols` to understand what needs documenting
2. **Write docs**: `write_file` for README/API docs/changelog. Match existing doc style
3. **Verify accuracy**: Cross-reference doc claims against actual code behavior
4. **Commit**: `docs(scope): description`

## Communication Style

- Be **concise and direct**. Code speaks louder than words.
- When explaining changes, focus on **why**, not just **what**.
- Use **code blocks** for all code references.
- If a task is complex, use the **todo list** to track progress.
- **Proactively suggest improvements** you notice during exploration.
- Write responses in the **same language** as the user's message.

## Context Awareness

- You are working within a **project** that may have a `.kkoclaw/project.yaml` or `CLAUDE.md`
  file with project-specific instructions. Always respect these.
- You may have access to **project memory** — knowledge from previous sessions about
  architecture, conventions, and pitfalls.
- Use the **plan mode** (todo list) for complex multi-step tasks to keep the user informed.

## Project Delivery Stage Tracking

This project tracks delivery through 7 stages:
requirements → design → initialization → implementation →
verification → review → delivery

You will see the **current stage** and its **completion signals** in the
"Current Delivery Stage" section of your dynamic context.

### When you MUST proactively call `suggest_delivery_stage`

- **You just produced the stage's key deliverable.**
  (e.g. you wrote `requirements.md` during the `requirements` stage;
  you produced a design doc during the `design` stage.)
- **The user explicitly confirmed a key decision** that satisfies one of
  the stage's completion signals (e.g. tech stack chosen, acceptance
  criteria signed off).
- **You're about to start work that clearly belongs to the *next* stage**
  (e.g. you're in `requirements` but the user is asking you to scaffold
  the project → suggest `initialization`).

### Attitude: err on the side of proposing

- A false-positive suggestion costs the user **one click** to dismiss.
- A missed suggestion **strands the project** in the wrong stage until
  the user manually notices and clicks forward.
- **When in doubt, call it.** The user is the final arbiter.

### What NOT to do

- Do **not** wait for the user to explicitly say "推进阶段" or "move to
  the next stage". That defeats the purpose of proactive tracking.
- Do **not** assume the stage auto-advances. It does not — only your
  `suggest_delivery_stage` call + the user's accept click moves it.
- Do **not** batch suggestions at the end of the project. Propose as
  soon as the signal is met, every time.
"""


@dataclass(frozen=True)
class QiongqiSession:
    """Immutable Coding session assembled for one agent graph."""

    context: CodingRuntimeContext
    skills: list[CodingSkill]


@dataclass(frozen=True)
class QiongqiRuntimePolicy:
    """Serializable policy state derived from active Coding skills."""

    active_coding_skills: list[dict]


@dataclass(frozen=True)
class QiongqiRoiReport:
    stable_prompt_fingerprint: str
    tool_catalog_fingerprint: str
    immutable_prefix_fingerprint: str
    full_tool_count: int
    visible_tool_count: int
    hidden_tool_count: int


@dataclass(frozen=True)
class QiongqiEngine:
    """Core runtime boundary for OClaw Coding."""

    session: QiongqiSession

    @classmethod
    def from_runtime(
        cls,
        *,
        project_root: str | None = None,
        thread_id: str | None = None,
        scratch_root: str | None = None,
    ) -> QiongqiEngine:
        context = CodingRuntimeContext.from_runtime(
            project_root=project_root,
            thread_id=thread_id,
            scratch_root=scratch_root,
        )
        return cls(
            session=QiongqiSession(
                context=context,
                skills=CodingSkillRegistry.discover(project_root=context.project_root),
            )
        )

    @property
    def context(self) -> CodingRuntimeContext:
        return self.session.context

    @property
    def skills(self) -> list[CodingSkill]:
        return self.session.skills

    def activate_skills(self, task_text: str | None) -> list[ActiveCodingSkill]:
        return self.activate_skills_for_task(task_text, current_stage=self._current_project_stage())

    def _current_project_stage(self) -> str | None:
        """Read the project's current delivery stage, if any."""
        try:
            project_root = self.session.context.project_root
            if not project_root:
                return None
            from kkoclaw.coding_core.stage_state import ProjectStageStore

            store = ProjectStageStore()
            state = store.get_state(project_root)
            return state.current_stage
        except Exception:  # noqa: BLE001
            return None

    def activate_skills_for_task(
        self, task_text: str | None, *, current_stage: str | None = None
    ) -> list[ActiveCodingSkill]:
        """Select Coding skills for a task and load their instruction files.

        Matching strategy (three-phase):
          0. **Stage-driven**: if the project is at a known delivery stage,
             activate the stage's ``recommended_skills`` as a baseline set.
             This ensures the agent always has the right workflow guidance
             for its current phase (e.g. TDD skills during implementation).
          1. Per-skill keyword/synonym/token matching via ``matches_skill_semantic``
             (Layers 1–4 + per-skill TF-IDF Layer 5).
          2. Full-corpus TF-IDF ranking via ``rank_skills_semantic`` — if any
             skill scores above the semantic threshold but was missed by
             phase 1, it is activated here. This catches paraphrased tasks
             that don't share keywords with any skill.
        """
        task = (task_text or "").lower()
        active: list[ActiveCodingSkill] = []
        active_ids: set[str] = set()

        # Phase 0: stage-driven activation (recommended_skills for current stage)
        if current_stage:
            stage_def = get_stage(current_stage)
            if stage_def and stage_def.recommended_skills:
                stage_skill_ids = set(stage_def.recommended_skills)
                for skill in self.session.skills:
                    if not skill.enabled or skill.manifest_errors:
                        continue
                    if skill.id not in stage_skill_ids:
                        continue
                    instructions = load_skill_instructions(skill)
                    if instructions:
                        active.append(ActiveCodingSkill(skill=skill, instructions=instructions))
                        active_ids.add(skill.id)

        # Phase 1: keyword + synonym + token matching (existing layers 1-5)
        for skill in self.session.skills:
            if not skill.enabled or skill.manifest_errors:
                continue
            if not _matches_skill(skill, task):
                continue
            instructions = load_skill_instructions(skill)
            if instructions:
                active.append(ActiveCodingSkill(skill=skill, instructions=instructions))
                active_ids.add(skill.id)

        # Phase 2: full-corpus TF-IDF semantic ranking (catches paraphrased tasks)
        try:
            from kkoclaw.coding_core.skills import rank_skills_semantic, _SEMANTIC_THRESHOLD

            enabled_skills = [s for s in self.session.skills if s.enabled and not s.manifest_errors]
            ranked = rank_skills_semantic(
                enabled_skills,
                task_text or "",
                top_k=5,
                min_score=_SEMANTIC_THRESHOLD,
            )
            for skill, score in ranked:
                if skill.id in active_ids:
                    continue  # already activated in phase 1
                instructions = load_skill_instructions(skill)
                if instructions:
                    active.append(ActiveCodingSkill(skill=skill, instructions=instructions))
                    active_ids.add(skill.id)
        except Exception:
            pass  # semantic ranking is best-effort; don't break activation

        return active

    def active_skill_policy_for_task(self, task_text: str | None) -> list[dict]:
        return active_skills_to_state(
            self.activate_skills_for_task(task_text, current_stage=self._current_project_stage())
        )

    def build_system_prompt(
        self,
        *,
        model_display_name: str | None = None,
        is_plan_mode: bool = False,
        subagent_enabled: bool = False,
        max_concurrent_subagents: int = 3,
    ) -> str:
        sections = [
            self.build_stable_system_prompt(
                model_display_name=model_display_name,
                is_plan_mode=is_plan_mode,
                subagent_enabled=subagent_enabled,
                max_concurrent_subagents=max_concurrent_subagents,
            ),
            self.build_dynamic_context(),
        ]
        return "".join(section for section in sections if section)

    def build_stable_system_prompt(
        self,
        *,
        model_display_name: str | None = None,
        is_plan_mode: bool = False,
        subagent_enabled: bool = False,
        max_concurrent_subagents: int = 3,
    ) -> str:
        sections = [_STABLE_QIONGQI_PROMPT]
        if model_display_name:
            sections.append(f"\n## Model\nYou are powered by **{model_display_name}**.\n")
        if subagent_enabled:
            sections.append(
                f"\n## Sub-Agent Orchestration\n"
                f"You can launch up to **{max_concurrent_subagents}** sub-agents per response for parallel tasks.\n"
                f"Use sub-agents for independent code exploration, test generation, or documentation work.\n"
            )
        if is_plan_mode:
            sections.append(
                "\n## Plan Mode\n"
                "Create and maintain a concise todo list for complex multi-step work.\n"
            )
        return "".join(sections)

    def build_dynamic_context(self) -> str:
        sections: list[str] = []
        project_root = self.session.context.project_root

        # Surface the current delivery stage so the agent knows where
        # the project stands without needing to ask the user.
        if project_root:
            stage_section = _build_delivery_stage_section(project_root)
            if stage_section:
                sections.append(stage_section)

        if project_root:
            sections.append(
                f"\n## Current Project\n"
                f"You are operating in the project at: `{project_root}`\n"
                f"Use this path as the source repository root when reading or editing project files.\n"
                f"Your default shell working directory is an isolated scratch workspace under the user's home directory, not this project root.\n"
                f"Put temporary notes, analysis files, generated scratch scripts, and other intermediate artifacts in the scratch workspace.\n"
                f"Only write inside `{project_root}` when the task explicitly requires changing the user's project files.\n"
            )

            # Project telemetry: tech stack fingerprint + git status
            telemetry_section = _build_project_telemetry_section(project_root)
            if telemetry_section:
                sections.append(telemetry_section)

        if self.session.skills:
            skill_lines = [
                f"- **{skill.name}** ({skill.scope}): {skill.description}\n"
                f"  Load instructions from `{skill.skill_file}` when this skill matches the coding task."
                for skill in self.session.skills
            ]
            sections.append(
                "\n## Coding Skills\n"
                "The following skills are scoped only to the Coding Agent. Load a skill by reading "
                "its SKILL.md file when the task matches its description:\n"
                + "\n".join(skill_lines)
                + "\n"
            )
        return "".join(sections)

    def immutable_prefix_fingerprint(self, *, stable_prompt: str, tools: list[Any]) -> str:
        payload = {
            "stable_prompt": stable_prompt,
            "tools": _canonical_tools(tools),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def tool_catalog_fingerprint(self, tools: list[Any]) -> str:
        encoded = json.dumps(_canonical_tools(tools), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def build_roi_report(
        self,
        *,
        stable_prompt: str,
        tools: list[Any],
        visible_tools: list[Any] | None = None,
    ) -> QiongqiRoiReport:
        visible = visible_tools if visible_tools is not None else tools
        stable_prompt_fingerprint = hashlib.sha256(stable_prompt.encode("utf-8")).hexdigest()
        tool_catalog_fingerprint = self.tool_catalog_fingerprint(tools)
        return QiongqiRoiReport(
            stable_prompt_fingerprint=stable_prompt_fingerprint,
            tool_catalog_fingerprint=tool_catalog_fingerprint,
            immutable_prefix_fingerprint=self.immutable_prefix_fingerprint(stable_prompt=stable_prompt, tools=tools),
            full_tool_count=len(tools),
            visible_tool_count=len(visible),
            hidden_tool_count=max(0, len(tools) - len(visible)),
        )

    def roi_metadata(self, report: QiongqiRoiReport) -> dict[str, Any]:
        return {
            "stable_prompt_fingerprint": report.stable_prompt_fingerprint,
            "tool_catalog_fingerprint": report.tool_catalog_fingerprint,
            "immutable_prefix_fingerprint": report.immutable_prefix_fingerprint,
            "full_tool_count": report.full_tool_count,
            "visible_tool_count": report.visible_tool_count,
            "hidden_tool_count": report.hidden_tool_count,
        }

    def persist_task_session(
        self,
        *,
        store: Any | None = None,
        task_text: str | None = None,
        active_skills: list[ActiveCodingSkill] | None = None,
        roi: dict[str, Any] | QiongqiRoiReport | None = None,
        change_summary: dict[str, Any] | None = None,
    ) -> Any:
        from kkoclaw.coding_core.session_store import QiongqiSessionStore

        session_store = store or QiongqiSessionStore.from_home()
        active_skills = active_skills if active_skills is not None else self.activate_skills_for_task(task_text)
        snapshot = session_store.persist_session(
            self.session,
            active_skills=active_skills,
            tool_policy=active_skills_to_state(active_skills),
            roi=roi,
            change_summary=change_summary,
        )
        session_store.append_event(
            self.session.context.thread_id,
            "session_started",
            {
                "project_root": self.session.context.project_root,
                "scratch_root": self.session.context.scratch_root,
                "active_skill_ids": [item.skill.id for item in active_skills],
            },
        )
        return snapshot

    def persist_roi_telemetry(
        self,
        *,
        store: Any | None = None,
        report: QiongqiRoiReport | dict[str, Any],
        provider_usage: dict[str, Any] | None = None,
        tool_output: dict[str, Any] | None = None,
        token_economy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from kkoclaw.coding_core.roi_telemetry import QiongqiRoiTelemetryStore

        telemetry_store = store or QiongqiRoiTelemetryStore.from_home()
        return telemetry_store.record_report(
            self.session.context.thread_id,
            report=report,
            provider_usage=provider_usage,
            tool_output=tool_output,
            token_economy=token_economy,
        )

    def build_legacy_system_prompt(
        self,
        *,
        model_display_name: str | None = None,
        is_plan_mode: bool = False,
        subagent_enabled: bool = False,
        max_concurrent_subagents: int = 3,
    ) -> str:
        from kkoclaw.coding_core.coding_prompt import apply_coding_prompt_template

        return apply_coding_prompt_template(
            model_display_name=model_display_name,
            is_plan_mode=is_plan_mode,
            subagent_enabled=subagent_enabled,
            max_concurrent_subagents=max_concurrent_subagents,
            project_root=self.session.context.project_root,
            coding_skills=self.session.skills,
        )

    def build_agent_middlewares(self) -> list:
        from kkoclaw.coding_core.skills_middleware import CodingSkillsMiddleware
        from kkoclaw.coding_core.tool_policy_middleware import CodingToolPolicyMiddleware

        return [
            CodingSkillsMiddleware(self),
            CodingToolPolicyMiddleware(self._active_skill_policy_for_state),
        ]

    def _active_skill_policy_for_state(self, state: object) -> list[dict]:
        if isinstance(state, dict):
            cached = state.get("active_coding_skills")
            if isinstance(cached, list):
                return cached
        return self.active_skill_policy_for_task(_latest_user_text(state))


def _matches_skill(skill: CodingSkill, task: str) -> bool:
    """Semantic skill matcher with synonym expansion and description overlap.

    Delegates to :func:`matches_skill_semantic` for the full matching logic
    (exact keywords → bilingual synonyms → description token overlap).
    """
    return matches_skill_semantic(skill, task)


# ----------------------------------------------------------------------
# Dynamic-context helpers: stage probes, tech stack fingerprint, git status
# ----------------------------------------------------------------------


def _build_delivery_stage_section(project_root: str) -> str | None:
    """Render the current delivery stage with auto-probed signal status.

    Augments the static completion signals with objective checks:
      - requirements stage: requirements.md / PRD exists?
      - design stage: design.md / architecture doc exists?
      - initialization stage: package manifest + build/test command present?
      - implementation stage: source files committed beyond skeleton?
      - verification stage: tests present and passing (heuristic)?
      - review stage: diff exists for review?
    """
    try:
        from kkoclaw.coding_core.stage_state import ProjectStageStore

        store = ProjectStageStore.from_home()
        stage_state = store.get_state(project_root)

        # Cold-start bootstrap: when a project has no stage yet, automatically
        # enter "requirements". This is idempotent — once set, subsequent
        # calls take the normal rendering path below. "requirements" is
        # the mandatory entry point for every project, so there is no
        # decision to defer to the user here (unlike forward transitions
        # which still respect auto_accept_forward_stage / manual confirm).
        if not stage_state.current_stage:
            stage_state = store.set_current_stage(
                project_root,
                "requirements",
                reason="项目冷启动：自动进入需求阶段",
                source="agent_accepted",
            )

        from kkoclaw.coding_core.delivery_stages import get_stage

        stage = get_stage(stage_state.current_stage)
        if not stage:
            return (
                f"\n## Current Delivery Stage\n"
                f"The project is currently in the **{stage_state.current_stage}** stage.\n"
            )

        # Run objective probes for the current stage
        probe_lines = _probe_stage_completion(stage.id, project_root)

        signals_block = ""
        if stage.completion_signals:
            signals_lines = "\n".join(
                f"  - {sig}" for sig in stage.completion_signals
            )
            signals_block = (
                f"\n**Completion signals** (any one met → call "
                f"`suggest_delivery_stage`):\n{signals_lines}\n"
            )

        probes_block = ""
        if probe_lines:
            probes_block = (
                "\n**Objective probes** (auto-detected project state):\n"
                + "\n".join(probe_lines)
                + "\n"
            )

        next_block = ""
        if stage.next_stage_id:
            next_block = (
                f"\n**Next stage**: `{stage.next_stage_id}` "
                f"(pass this as `stage_id` when you propose)\n"
            )

        skills_block = ""
        if stage.recommended_skills:
            skills_lines = ", ".join(f"`{s}`" for s in stage.recommended_skills)
            skills_block = (
                f"\n**Recommended skills** (auto-activated for this stage): {skills_lines}\n"
            )

        return (
            f"\n## Current Delivery Stage\n"
            f"You are in the **{stage.title}** (`{stage.id}`) stage.\n"
            f"\n**Goal**: {stage.goal}\n"
            f"{skills_block}"
            f"{signals_block}"
            f"{probes_block}"
            f"{next_block}"
        )
    except Exception:  # noqa: BLE001
        return None


def _probe_stage_completion(stage_id: str, project_root: str) -> list[str]:
    """Run objective filesystem/git probes relevant to each stage.

    Returns a list of bullet-point strings (✅ met / ❌ not met) the agent
    can use to judge whether the stage is actually complete.
    """
    from pathlib import Path

    root = Path(project_root)
    lines: list[str] = []

    def _exists_any(*names: str) -> str | None:
        for name in names:
            # Top-level check
            if (root / name).is_file():
                return name
            # One-level deep (e.g. docs/requirements.md)
            for child in root.glob(f"*/{name}"):
                if child.is_file():
                    return str(child.relative_to(root))
        return None

    def _has_tests() -> bool:
        for pattern in ("test_*.py", "*_test.py", "*.test.ts", "*.test.js", "*_test.go"):
            if list(root.rglob(pattern))[:1]:
                return True
        return False

    if stage_id == "requirements":
        found = _exists_any("requirements.md", "REQUIREMENTS.md", "PRD.md", "prd.md", "requirements.txt")
        lines.append(f"  - 需求文档: {'✅ ' + found if found else '❌ 未找到 requirements.md / PRD.md'}")
    elif stage_id == "design":
        found = _exists_any("design.md", "DESIGN.md", "architecture.md", "ARCHITECTURE.md", "docs/design.md")
        lines.append(f"  - 设计文档: {'✅ ' + found if found else '❌ 未找到 design.md / architecture.md'}")
    elif stage_id == "initialization":
        manifest = _exists_any("package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml", "pom.xml")
        lines.append(f"  - 包管理清单: {'✅ ' + manifest if manifest else '❌ 未找到 package.json / pyproject.toml 等'}")
        readme = _exists_any("README.md", "readme.md", "README.rst")
        lines.append(f"  - README: {'✅ 存在' if readme else '❌ 缺失'}")
    elif stage_id == "implementation":
        manifest = _exists_any("package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml")
        lines.append(f"  - 工程骨架: {'✅ ' + manifest if manifest else '❌ 未检测到'}")
        has_tests = _has_tests()
        lines.append(f"  - 测试代码: {'✅ 已存在测试文件' if has_tests else '⚠️ 未检测到测试文件，建议补充'}")
    elif stage_id == "verification":
        has_tests = _has_tests()
        lines.append(f"  - 测试代码: {'✅ 存在' if has_tests else '❌ 无测试可验证'}")
        ci = _exists_any(".github/workflows", ".gitlab-ci.yml", ".circleci", "Jenkinsfile")
        lines.append(f"  - CI 配置: {'✅ ' + ci if ci else '⚠️ 未检测到 CI 配置'}")
    elif stage_id == "review":
        # Probe git diff status
        try:
            import subprocess

            result = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
            )
            changed = [ln for ln in result.stdout.splitlines() if ln.strip()]
            lines.append(f"  - 待审查变更: {'✅ ' + str(len(changed)) + ' 个文件' if changed else '❌ 工作区干净，无 diff 可审查'}")
        except Exception:
            lines.append("  - 待审查变更: ❓ 无法探测 git 状态")
    elif stage_id == "delivery":
        deploy_doc = _exists_any("DEPLOYMENT.md", "deploy.md", "docs/deploy.md", "ops.md")
        lines.append(f"  - 部署文档: {'✅ ' + deploy_doc if deploy_doc else '❌ 未找到 DEPLOYMENT.md'}")

    return lines


def _build_project_telemetry_section(project_root: str) -> str | None:
    """Detect tech stack fingerprint and git status, inject as context.

    This gives the agent a fast orientation at the start of every turn:
    - what language/framework/test-runner/linter the project uses
    - whether the repo is clean, how many uncommitted files, ahead/behind
    """
    stack_lines = _detect_tech_stack(project_root)
    git_lines = _detect_git_status(project_root)

    parts: list[str] = []
    if stack_lines:
        parts.append("**Tech stack fingerprint**:\n" + "\n".join(stack_lines))
    if git_lines:
        parts.append("**Git status**:\n" + "\n".join(git_lines))

    if not parts:
        return None
    return "\n## Project Telemetry\n" + "\n\n".join(parts) + "\n"


def _detect_tech_stack(project_root: str) -> list[str]:
    """Deep tech-stack detection from manifest file contents.

    Parses ``pyproject.toml``, ``package.json``, ``go.mod``, ``Cargo.toml``
    to extract:
      - Language version (Python requires-python, Node engines, Go version)
      - Key frameworks (FastAPI, Django, React, Next.js, Vue, Express, ...)
      - Test runner (pytest, jest, vitest, go test, cargo test)
      - Linter/formatter (ruff, mypy, eslint, prettier, go vet, clippy)
      - Build tools (vite, webpack, turbo, poetry, uv, hatch)
    """
    from pathlib import Path

    root = Path(project_root)
    lines: list[str] = []

    # ---- Python ----
    py_info = _parse_python_manifest(root)
    if py_info:
        lines.extend(py_info)

    # ---- Node.js / TypeScript ----
    node_info = _parse_node_manifest(root)
    if node_info:
        lines.extend(node_info)

    # ---- Go ----
    go_info = _parse_go_manifest(root)
    if go_info:
        lines.extend(go_info)

    # ---- Rust ----
    rust_info = _parse_rust_manifest(root)
    if rust_info:
        lines.extend(rust_info)

    # ---- Infrastructure (Docker/K8s) ----
    infra_lines = _detect_infra(root)
    if infra_lines:
        lines.append(infra_lines)

    return lines[:10]  # cap to keep context tight


# ------------------------------------------------------------------ #
# Python manifest parsing
# ------------------------------------------------------------------ #

# Known Python frameworks → display name
_PY_FRAMEWORK_MAP = {
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "starlette": "Starlette", "tornado": "Tornado", "aiohttp": "aiohttp",
    "sanic": "Sanic", "pyramid": "Pyramid", "bottle": "Bottle",
    "langchain": "LangChain", "langgraph": "LangGraph",
    "celery": "Celery", "redis": "Redis", "sqlalchemy": "SQLAlchemy",
    "torch": "PyTorch", "tensorflow": "TensorFlow", "transformers": "Transformers",
    "pandas": "Pandas", "numpy": "NumPy", "scipy": "SciPy",
    "pydantic": "Pydantic", "click": "Click", "typer": "Typer",
}

_PY_LINTER_MAP = {
    "ruff": "ruff", "mypy": "mypy", "pylint": "pylint",
    "flake8": "flake8", "pyright": "pyright",
}

_PY_BUILD_MAP = {
    "poetry": "Poetry", "hatch": "Hatch", "uv": "uv", "setuptools": "setuptools",
}


def _parse_python_manifest(root: Path) -> list[str]:
    """Parse pyproject.toml / setup.py / requirements.txt for Python stack info."""
    deps: dict[str, str] = {}
    py_version: str | None = None
    build_tool: str | None = None

    # Try pyproject.toml first (preferred)
    toml_path = root / "pyproject.toml"
    if toml_path.is_file():
        try:
            import tomllib  # Python 3.11+
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)

            # Python version requirement
            project = data.get("project", {})
            requires = project.get("requires-python")
            if requires:
                py_version = requires

            # Dependencies
            for dep in project.get("dependencies", []) or []:
                name = re.split(r"[<>=!~\[]", dep.strip(), 1)[0].strip().lower()
                if name:
                    deps[name] = dep.strip()
            for group in (project.get("optional-dependencies") or {}).values():
                for dep in group or []:
                    name = re.split(r"[<>=!~\[]", dep.strip(), 1)[0].strip().lower()
                    if name:
                        deps[name] = dep.strip()

            # PEP 735 dependency-groups (dev dependencies)
            for group_deps in (data.get("dependency-groups") or {}).values():
                for dep in group_deps or []:
                    name = re.split(r"[<>=!~\[]", dep.strip(), 1)[0].strip().lower()
                    if name:
                        deps[name] = dep.strip()

            # Build system
            build_sys = data.get("build-system", {})
            for req in build_sys.get("requires", []) or []:
                for key in _PY_BUILD_MAP:
                    if key in req.lower():
                        build_tool = _PY_BUILD_MAP[key]
                        break

            # Tool configs (ruff, mypy, pytest)
            tool = data.get("tool", {})
            if "ruff" in tool and "ruff" not in deps:
                deps["ruff"] = "ruff"
            if "mypy" in tool and "mypy" not in deps:
                deps["mypy"] = "mypy"
            if "pytest" in tool.get("pytest", {}) or "pytest" in str(project.get("dependencies", [])):
                deps.setdefault("pytest", "pytest")

        except Exception:
            pass

    # Fallback: requirements.txt
    elif (root / "requirements.txt").is_file():
        try:
            content = (root / "requirements.txt").read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    name = re.split(r"[<>=!~\[]", line, 1)[0].strip().lower()
                    if name:
                        deps[name] = line
        except Exception:
            pass
    elif (root / "setup.py").is_file():
        pass  # minimal detection
    else:
        return []  # No Python project

    lines: list[str] = []
    lang = "Python"
    if py_version:
        lang += f" (requires {py_version})"
    if build_tool:
        lang += f" [{build_tool}]"
    lines.append(f"  - 语言: {lang}")

    # Frameworks
    frameworks = [_PY_FRAMEWORK_MAP[d] for d in deps if d in _PY_FRAMEWORK_MAP]
    if frameworks:
        lines.append(f"  - 框架: {', '.join(frameworks[:6])}")

    # Test runner
    if "pytest" in deps:
        lines.append("  - 测试: pytest")

    # Linter / formatter
    linters = [_PY_LINTER_MAP[d] for d in deps if d in _PY_LINTER_MAP]
    if linters:
        lines.append(f"  - Linter: {', '.join(linters[:3])}")

    return lines


# ------------------------------------------------------------------ #
# Node.js manifest parsing
# ------------------------------------------------------------------ #

_NODE_FRAMEWORK_MAP = {
    "react": "React", "next": "Next.js", "vue": "Vue", "nuxt": "Nuxt",
    "@angular/core": "Angular", "svelte": "Svelte", "astro": "Astro",
    "express": "Express", "fastify": "Fastify", "koa": "Koa",
    "nest": "NestJS", "@remix-run/react": "Remix",
    "electron": "Electron",
}

_NODE_BUILD_MAP = {
    "vite": "Vite", "webpack": "webpack", "turbo": "Turborepo",
    "rollup": "Rollup", "esbuild": "esbuild", "@swc/core": "SWC",
}


def _parse_node_manifest(root: Path) -> list[str]:
    """Parse package.json for Node.js/TypeScript stack info."""
    pkg_path = root / "package.json"
    if not pkg_path.is_file():
        return []

    try:
        import json as _json
        pkg = _json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return ["  - 语言: Node.js"]

    deps = dict(pkg.get("dependencies") or {})
    dev_deps = dict(pkg.get("devDependencies") or {})
    all_deps = {**deps, **dev_deps}

    lines: list[str] = []

    # Language + version
    node_version = None
    engines = pkg.get("engines") or {}
    if isinstance(engines, dict) and engines.get("node"):
        node_version = engines["node"]
    has_ts = "typescript" in all_deps
    lang = "TypeScript" if has_ts else "Node.js"
    if node_version:
        lang += f" (node {node_version})"

    # Package manager
    pm = None
    if pkg.get("packageManager"):
        pm_str = pkg["packageManager"]
        if "pnpm" in pm_str:
            pm = "pnpm"
        elif "yarn" in pm_str:
            pm = "yarn"
        elif "npm" in pm_str:
            pm = "npm"
    if not pm:
        if (root / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (root / "yarn.lock").exists():
            pm = "yarn"
    if pm:
        lang += f" [{pm}]"

    lines.append(f"  - 语言: {lang}")

    # Frameworks
    frameworks = [_NODE_FRAMEWORK_MAP[d] for d in all_deps if d in _NODE_FRAMEWORK_MAP]
    if frameworks:
        lines.append(f"  - 框架: {', '.join(frameworks[:6])}")

    # Build tools
    build_tools = [_NODE_BUILD_MAP[d] for d in all_deps if d in _NODE_BUILD_MAP]
    if build_tools:
        lines.append(f"  - 构建: {', '.join(build_tools[:4])}")

    # Test runner
    test_runners = []
    if any(d.startswith("jest") for d in all_deps):
        test_runners.append("jest")
    if "vitest" in all_deps:
        test_runners.append("vitest")
    if "playwright" in all_deps:
        test_runners.append("Playwright")
    if "@playwright/test" in all_deps:
        test_runners.append("Playwright")
    if "cypress" in all_deps:
        test_runners.append("Cypress")
    if test_runners:
        lines.append(f"  - 测试: {', '.join(test_runners)}")

    # Linter / formatter
    linters = []
    if "eslint" in all_deps:
        linters.append("eslint")
    if "prettier" in all_deps:
        linters.append("prettier")
    if "biome" in all_deps or "@biomejs/biome" in all_deps:
        linters.append("biome")
    if linters:
        lines.append(f"  - Linter: {', '.join(linters)}")

    return lines


# ------------------------------------------------------------------ #
# Go manifest parsing
# ------------------------------------------------------------------ #

def _parse_go_manifest(root: Path) -> list[str]:
    """Parse go.mod for Go stack info."""
    mod_path = root / "go.mod"
    if not mod_path.is_file():
        return []

    lines: list[str] = []
    go_version = None
    try:
        content = mod_path.read_text(encoding="utf-8")
        # Find go version
        m = re.search(r"^go\s+(\d+\.\d+(?:\.\d+)?)", content, re.MULTILINE)
        if m:
            go_version = m.group(1)
    except Exception:
        pass

    lang = "Go"
    if go_version:
        lang += f" {go_version}"
    lines.append(f"  - 语言: {lang}")
    lines.append("  - 测试: go test")
    lines.append("  - Linter: go vet")
    return lines


# ------------------------------------------------------------------ #
# Rust manifest parsing
# ------------------------------------------------------------------ #

def _parse_rust_manifest(root: Path) -> list[str]:
    """Parse Cargo.toml for Rust stack info."""
    cargo_path = root / "Cargo.toml"
    if not cargo_path.is_file():
        return []

    lines: list[str] = ["  - 语言: Rust", "  - 测试: cargo test", "  - Linter: cargo clippy"]

    # Try to parse edition
    try:
        import tomllib
        with open(cargo_path, "rb") as f:
            data = tomllib.load(f)
        edition = data.get("package", {}).get("edition")
        if edition:
            lines[0] = f"  - 语言: Rust (edition {edition})"
    except Exception:
        pass

    return lines


# ------------------------------------------------------------------ #
# Infrastructure detection
# ------------------------------------------------------------------ #

def _detect_infra(root: Path) -> str | None:
    """Detect Docker/K8s/CI presence."""
    infra: list[str] = []
    if (root / "Dockerfile").is_file() or (root / "docker-compose.yml").is_file() or (root / "docker-compose.yaml").is_file():
        infra.append("Docker")
    if (root / "k8s").is_dir() or any(root.glob("k8s/*.yaml")):
        infra.append("Kubernetes")
    if any((root / ".github" / "workflows").glob("*.yml")):
        infra.append("GitHub Actions")
    if (root / ".gitlab-ci.yml").is_file():
        infra.append("GitLab CI")
    if not infra:
        return None
    return f"  - 基础设施: {', '.join(infra)}"


def _detect_git_status(project_root: str) -> list[str]:
    """Probe git repo state: branch, dirty file count, ahead/behind."""
    import subprocess
    from pathlib import Path

    root = Path(project_root)
    if not (root / ".git").exists():
        return []

    lines: list[str] = []
    try:
        def _run(*args: str) -> str:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()

        branch = _run("rev-parse", "--abbrev-ref", "HEAD")
        lines.append(f"  - 分支: {branch or '(detached)'}")

        status = _run("status", "--porcelain")
        dirty = [ln for ln in status.splitlines() if ln.strip()]
        lines.append(f"  - 未提交变更: {len(dirty)} 个文件")

        ahead_behind = _run("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        parts = ahead_behind.split()
        if len(parts) == 2:
            behind, ahead = parts
            lines.append(f"  - 与 upstream: ahead {ahead} / behind {behind}")
    except Exception:
        return []

    return lines


def _latest_user_text(state: object) -> str | None:
    if not isinstance(state, dict):
        return None
    from langchain_core.messages import HumanMessage

    for message in reversed(list(state.get("messages", []))):
        if isinstance(message, HumanMessage) and not message.additional_kwargs.get("coding_skills_reminder"):
            content = message.content
            if isinstance(content, str):
                return content
            return str(content)
    return None


def active_skills_to_state(active_skills: list[ActiveCodingSkill]) -> list[dict]:
    return [
        {
            "id": active.skill.id,
            "allowed_tools": list(active.skill.allowed_tools),
            "permissions": active.skill.permissions or {},
        }
        for active in active_skills
    ]


def _canonical_tools(tools: list[Any]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for tool in tools:
        if isinstance(tool, dict):
            name = str(tool.get("name") or "")
            payload = dict(tool)
        else:
            name = str(getattr(tool, "name", "") or "")
            payload = {"name": name}
            args_schema = getattr(tool, "args_schema", None)
            if args_schema is not None:
                payload["args_schema"] = str(args_schema)
            description = getattr(tool, "description", None)
            if description is not None:
                payload["description"] = str(description)
        canonical.append(_canonical_value(payload | {"name": name}))
    return sorted(canonical, key=lambda item: item.get("name", ""))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    return value
