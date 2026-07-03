"""Tests for kkoclaw.skills.frontmatter — work_modes injection utilities."""

from __future__ import annotations

from kkoclaw.skills.frontmatter import (
    has_work_modes_frontmatter,
    inject_work_modes_frontmatter,
)


_FRONTMATTER = """---
name: demo-skill
description: A demo skill
---

# Demo Skill
"""


class TestInjectWorkModesFrontmatter:
    def test_inject_into_clean_frontmatter(self):
        result = inject_work_modes_frontmatter(_FRONTMATTER, ["task"])
        assert "work_modes: [task]" in result
        assert "# Demo Skill" in result

    def test_inject_multiple_modes(self):
        result = inject_work_modes_frontmatter(_FRONTMATTER, ["task", "coding"])
        assert "work_modes: [task, coding]" in result

    def test_replace_existing_work_modes(self):
        content = _FRONTMATTER.replace(
            "---\n",
            "---\nwork_modes: [old-mode]\n",
            1,
        )
        result = inject_work_modes_frontmatter(content, ["task"])
        assert "work_modes: [task]" in result
        assert "old-mode" not in result

    def test_no_frontmatter_returns_unchanged(self):
        content = "# Just a heading, no frontmatter\n"
        result = inject_work_modes_frontmatter(content, ["task"])
        assert result == content

    def test_empty_work_modes_strips_field(self):
        """Passing an empty list should remove any existing work_modes line."""
        content = _FRONTMATTER.replace(
            "---\n",
            "---\nwork_modes: [task]\n",
            1,
        )
        result = inject_work_modes_frontmatter(content, [])
        assert "work_modes:" not in result
        assert "# Demo Skill" in result


class TestHasWorkModesFrontmatter:
    def test_detects_present_field(self):
        content = _FRONTMATTER.replace(
            "---\n",
            "---\nwork_modes: [task]\n",
            1,
        )
        assert has_work_modes_frontmatter(content) is True

    def test_returns_false_for_missing_field(self):
        assert has_work_modes_frontmatter(_FRONTMATTER) is False

    def test_returns_false_for_no_frontmatter(self):
        assert has_work_modes_frontmatter("# Just markdown") is False
