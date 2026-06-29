"""Tests for work-mode context injection into the lead agent system prompt.

The lead agent must be explicitly aware of which work mode it is operating
under. These tests verify that ``apply_prompt_template`` injects a
``<work_mode_context>`` block into the system prompt when a ``work_mode_id``
is supplied, and that the block contains:

- The mode's display name (e.g. "日常办公")
- The bound lead agent name
- The skill count
- The orchestration hint keywords

When ``work_mode_id`` is None, no mode context block should appear (backward
compatibility).
"""

from __future__ import annotations

import re

import pytest

from kkoclaw.agents.lead_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
    _build_work_mode_context,
    apply_prompt_template,
)
from kkoclaw.config.extensions_config import ExtensionsConfig, WorkModeConfig


class TestWorkModePromptInjection:
    """Verify the system prompt carries explicit mode awareness."""

    def test_task_mode_prompt_contains_mode_context(self):
        """task mode → prompt contains <work_mode_context> + 日常办公."""
        prompt = apply_prompt_template(
            work_mode_id="task",
            available_skills={"bootstrap", "find-skills", "skill-creator"},
        )
        assert "<work_mode_context>" in prompt
        assert "</work_mode_context>" in prompt
        assert "日常办公" in prompt

    def test_coding_mode_prompt_contains_mode_context(self):
        """coding mode → prompt contains 编程 + coding-related keywords."""
        prompt = apply_prompt_template(
            work_mode_id="coding",
            available_skills={"bootstrap", "find-skills", "skill-creator"},
        )
        assert "<work_mode_context>" in prompt
        assert "编程" in prompt

    def test_none_mode_omits_context(self):
        """work_mode_id=None → no <work_mode_context> block."""
        prompt = apply_prompt_template(
            work_mode_id=None,
            available_skills={"bootstrap"},
        )
        assert "<work_mode_context>" not in prompt

    def test_mode_context_lists_skill_count(self):
        """The block reports how many skills are bound to the mode.

        After the fix, ``_build_work_mode_context`` derives the skill set
        from ``compute_effective_skills`` (same logic as the skill-system
        block) rather than the raw ``available_skills`` argument. So the
        count always reflects the mode's directory-bound + locked skill
        set, never 0.
        """
        prompt = apply_prompt_template(
            work_mode_id="task",
            available_skills={"bootstrap", "find-skills", "skill-creator", "deep-research"},
        )
        # Use regex to extract the exact count — plain substring "0 skill(s)"
        # is a false-positive substring of "20 skill(s)" etc.
        match = re.search(r"\*\*Bound skills\*\*: (\d+) skill", prompt)
        assert match is not None, "Bound skills line not found in prompt"
        skill_count = int(match.group(1))
        assert skill_count > 0, f"Expected >0 skills, got {skill_count}"

    def test_mode_context_skill_count_nonzero_with_none_available_skills(self):
        """Regression: default lead agent (available_skills=None) must not
        report 0 skills.

        Before the fix, ``_build_work_mode_context`` used the raw
        ``available_skills`` argument directly, which is None for the
        default lead agent (no per-agent whitelist). This caused the
        context block to say "0 skill(s) loaded" even though the
        skill-system section below listed the mode's real skills.
        """
        prompt = apply_prompt_template(
            work_mode_id="task",
            available_skills=None,
        )
        assert "<work_mode_context>" in prompt
        # Regex-extract the count to avoid substring false positives
        # ("0 skill(s)" is a substring of "20 skill(s)").
        match = re.search(r"\*\*Bound skills\*\*: (\d+) skill", prompt)
        assert match is not None, "Bound skills line not found in prompt"
        skill_count = int(match.group(1))
        assert skill_count > 0, f"Expected >0 skills, got {skill_count}"

    def test_template_has_work_mode_context_placeholder(self):
        """SYSTEM_PROMPT_TEMPLATE must reserve a slot for mode context."""
        assert "{work_mode_context}" in SYSTEM_PROMPT_TEMPLATE

    def test_build_work_mode_context_with_empty_id_returns_empty(self):
        """Defensive: empty/None work_mode_id → empty string."""
        assert _build_work_mode_context(None, None, None) == ""
        assert _build_work_mode_context("", None, None) == ""

    def test_build_work_mode_context_unknown_id_returns_empty(self):
        """Unknown mode id → empty (falls back gracefully)."""
        cfg = ExtensionsConfig()
        assert _build_work_mode_context("nonexistent-mode", cfg, {"bootstrap"}) == ""

    def test_build_work_mode_context_contains_lead_agent_name(self):
        """The block mentions the lead agent name so the model knows its role."""
        cfg = ExtensionsConfig()
        result = _build_work_mode_context("task", cfg, {"bootstrap"})
        assert "Lead Agent" in result
        # Default task mode should reference the configured lead agent name
        task_cfg = cfg.work_modes.modes["task"]
        if task_cfg.lead_agent_name:
            assert task_cfg.lead_agent_name in result

    def test_coding_mode_hint_mentions_test_driven(self):
        """The coding orchestration hint should guide test-driven development."""
        prompt = apply_prompt_template(
            work_mode_id="coding",
            available_skills={"bootstrap"},
        )
        # The hint should contain coding-relevant guidance keywords
        assert "test" in prompt.lower() or "code" in prompt.lower()

    def test_focus_areas_appear_in_context(self):
        """Focus areas should be listed in the mode context block."""
        prompt = apply_prompt_template(
            work_mode_id="task",
            available_skills={"bootstrap"},
        )
        # Prompt uses markdown bold: **Focus areas**: ...
        assert "Focus areas" in prompt
        assert "research" in prompt  # one of the task focus areas
