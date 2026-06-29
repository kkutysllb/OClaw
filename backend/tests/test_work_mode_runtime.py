"""Tests for runtime work-mode skill filtering.

These tests cover the bridge between ``AgentConfig.skills`` (per-agent whitelist)
and ``work_mode_id`` (per-mode whitelist). The end goal is that the effective
skill set fed into the lead agent's prompt is:

- The agent's explicit ``skills`` list intersected with the mode's effective
  set, when both are present.
- The mode's effective set alone, when the agent declares no whitelist.
- The agent's whitelist alone, when no ``work_mode_id`` is specified (backward
  compatible — preserves today's behavior for callers that don't opt in).
"""

from __future__ import annotations

import ast
import pathlib

import pytest


# ---------------------------------------------------------------------------
# Pure-function logic: compute_effective_skills
# ---------------------------------------------------------------------------


class TestComputeEffectiveSkills:
    """The core resolution function called from ``apply_prompt_template``.

    Test matrix — each row is one tuple ``(agent_skills, work_mode_id)``:

    - ``(None, None)`` → ``None`` (no filtering — backward compat)
    - ``(None, "task")`` → mode's effective set
    - ``(None, "coding")`` → mode's effective set
    - ``(["a"], None)`` → ``{"a"}`` (only agent whitelist applied)
    - ``(["a"], "task")`` → ``set(agent) & mode_effective``
    - ``(["x", "y"], "task")`` → intersection
    - ``([], None)`` → ``set()`` (explicitly empty agent whitelist)
    - ``([], "task")`` → ``set()`` (explicit empty overrides mode)
    """

    def test_no_work_mode_no_agent_skills_returns_none(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig()
        result = compute_effective_skills(agent_skills=None, work_mode_id=None, extensions_config=cfg)
        assert result is None

    def test_work_mode_alone_returns_mode_effective_set(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("deep-research",)),
            },
        )
        result = compute_effective_skills(agent_skills=None, work_mode_id="task", extensions_config=cfg)
        assert result is not None
        # Mode default (empty) + added (deep-research) + locked skills
        assert "deep-research" in result
        for locked in ("bootstrap", "find-skills", "skill-creator"):
            assert locked in result

    def test_agent_skills_alone_unions_locked(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig()
        # Even without a work mode, locked core skills survive — they're a
        # global invariant. The agent's whitelist is unioned with locked.
        result = compute_effective_skills(agent_skills=["a", "b"], work_mode_id=None, extensions_config=cfg)
        assert result == {"a", "b", "bootstrap", "find-skills", "skill-creator"}

    def test_both_presents_returns_intersection(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("deep-research", "xlsx-creator")),
            },
        )
        result = compute_effective_skills(
            agent_skills=["deep-research", "missing-skill"],
            work_mode_id="task",
            extensions_config=cfg,
        )
        # Only "deep-research" is in both; "missing-skill" is not in mode
        assert "deep-research" in result
        assert "missing-skill" not in result
        # Locked skills survive (they're in mode, and they intersect with nothing
        # the agent lists — but locked are special-cased)
        assert "bootstrap" in result

    def test_explicit_empty_agent_skills_keeps_only_locked(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("deep-research",)),
            },
        )
        # Agent explicitly opts out of all non-locked skills (skills: [] in
        # config.yaml). The result is the locked core only — non-locked skills
        # from the mode are dropped, but locked skills are a global invariant
        # that survive any per-agent opt-out.
        result = compute_effective_skills(agent_skills=[], work_mode_id="task", extensions_config=cfg)
        assert result == {"bootstrap", "find-skills", "skill-creator"}

    def test_locked_skills_survive_intersection(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import compute_effective_skills

        # Put the user skill into the task mode via overrides so it actually
        # appears in the mode's effective set. Otherwise the default task mode
        # has an empty default_skill_ids and the user skill would be filtered
        # out by the intersection, making this test meaningless.
        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("some-user-skill",)),
            },
        )
        result = compute_effective_skills(
            agent_skills=["some-user-skill"],
            work_mode_id="task",
            extensions_config=cfg,
        )
        assert result is not None
        # Locked skills still appear because they're mode-implicit
        for locked in ("bootstrap", "find-skills", "skill-creator"):
            assert locked in result
        assert "some-user-skill" in result

    def test_unknown_work_mode_falls_back_to_default(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import compute_effective_skills

        cfg = ExtensionsConfig()
        result = compute_effective_skills(
            agent_skills=None,
            work_mode_id="nonexistent",
            extensions_config=cfg,
        )
        # Falls back to default task mode's effective set
        assert result is not None
        for locked in ("bootstrap", "find-skills", "skill-creator"):
            assert locked in result


# ---------------------------------------------------------------------------
# Source-level checks: ensure prompt.py and agent.py wire work_mode_id through.
# ---------------------------------------------------------------------------
#
# We can't import kkoclaw.agents.lead_agent.prompt cleanly because the package's
# __init__ pulls in langchain/langgraph (which has a runtime version mismatch
# in the local conda env). So we verify the wiring by parsing the source AST.


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _function_arg_names(func: ast.FunctionDef) -> set[str]:
    """Return the full set of named arguments (positional + kwonly) of a function."""
    args = func.args
    names = {a.arg for a in args.args}
    names.update(a.arg for a in args.kwonlyargs)
    return names


def _load_module_ast(rel_path: str) -> ast.Module:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    return ast.parse((repo_root / rel_path).read_text(encoding="utf-8"))


class TestPromptTemplateAcceptsWorkModeId:
    def test_apply_prompt_template_accepts_work_mode_id(self):
        """The system-prompt builder must accept ``work_mode_id`` as a kwarg."""
        tree = _load_module_ast("packages/harness/kkoclaw/agents/lead_agent/prompt.py")
        fn = _find_function(tree, "apply_prompt_template")
        assert fn is not None, "apply_prompt_template must be defined in prompt.py"
        assert "work_mode_id" in _function_arg_names(fn), (
            "apply_prompt_template must accept a work_mode_id parameter so callers "
            "can forward the runtime work mode to the skill resolution layer"
        )

    def test_get_skills_prompt_section_accepts_work_mode_id(self):
        """The skills-section builder must accept ``work_mode_id`` as a kwarg."""
        tree = _load_module_ast("packages/harness/kkoclaw/agents/lead_agent/prompt.py")
        fn = _find_function(tree, "get_skills_prompt_section")
        assert fn is not None
        assert "work_mode_id" in _function_arg_names(fn)


class TestLeadAgentReadsWorkModeId:
    def test_make_lead_agent_reads_work_mode_id_from_cfg(self):
        """``_make_lead_agent`` must read ``work_mode_id`` from the runtime config.

        This is the integration seam — Task 1 added ``work_mode_id`` to the
        context-forwarding whitelist, and this test ensures the lead-agent
        factory actually consumes it before constructing the prompt.
        """
        tree = _load_module_ast("packages/harness/kkoclaw/agents/lead_agent/agent.py")
        fn = _find_function(tree, "_make_lead_agent")
        assert fn is not None
        source = ast.unparse(fn)
        assert "work_mode_id" in source, (
            "_make_lead_agent must reference 'work_mode_id' — it must read it "
            "from the runtime config (cfg.get('work_mode_id')) and forward it to "
            "apply_prompt_template"
        )

    def test_make_lead_agent_passes_work_mode_id_to_prompt(self):
        """The agent factory must call ``apply_prompt_template(..., work_mode_id=...)``."""
        tree = _load_module_ast("packages/harness/kkoclaw/agents/lead_agent/agent.py")
        fn = _find_function(tree, "_make_lead_agent")
        assert fn is not None
        source = ast.unparse(fn)
        # We expect to see work_mode_id=... as a kwarg to apply_prompt_template.
        assert "work_mode_id=" in source, (
            "_make_lead_agent must forward work_mode_id to apply_prompt_template"
        )