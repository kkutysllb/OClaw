"""Tests for Skill.mode_scope — the directory-derived work-mode binding tag.

Each builtin skill carries a ``mode_scope`` ("core" / "task" / "coding")
inferred from its physical location under ``skills/builtin/``. This tag
drives the work-mode → skill-set auto-binding so that:
  - task mode = core + task directory skills
  - coding mode = core + coding directory skills
  - custom / legacy-public skills have mode_scope = None
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(skill_dir: Path, name: str, description: str = "desc") -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f"""---
name: {name}
description: {description}
---
# {name}
""",
        encoding="utf-8",
    )
    return md


class TestSkillModeScopeField:
    """The Skill dataclass must carry a mode_scope attribute."""

    def test_skill_dataclass_has_mode_scope_field(self):
        from kkoclaw.skills.types import Skill, SkillCategory
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(Skill)}
        assert "mode_scope" in field_names, "Skill dataclass must have a 'mode_scope' field"

    def test_skill_mode_scope_defaults_none(self):
        from kkoclaw.skills.types import Skill, SkillCategory

        skill = Skill(
            name="x",
            description="d",
            license=None,
            skill_dir=Path("/tmp"),
            skill_file=Path("/tmp/SKILL.md"),
            relative_path=Path("x"),
            category=SkillCategory.CUSTOM,
        )
        assert skill.mode_scope is None


class TestLoadSkillsInfersModeScope:
    """load_skills must populate mode_scope from the builtin sub-directory."""

    def test_core_skill_has_core_scope(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "core", "bootstrap", "Bootstrap skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "bootstrap" in by_name
        assert by_name["bootstrap"].mode_scope == "core"

    def test_task_skill_has_task_scope(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "task", "deep-research", "Research skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert by_name["deep-research"].mode_scope == "task"

    def test_coding_skill_has_coding_scope(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "coding", "code-review", "Review skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert by_name["code-review"].mode_scope == "coding"

    def test_nested_coding_skill_has_coding_scope(self, tmp_path: Path):
        """Skills nested deeper (coding/coding/database) still scope to 'coding'."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "coding" / "sub-pkg", "database", "DB skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "database" in by_name
        assert by_name["database"].mode_scope == "coding"

    def test_custom_skill_has_none_scope(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "custom", "my-skill", "Custom skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "my-skill" in by_name
        assert by_name["my-skill"].mode_scope is None

    def test_legacy_public_skill_has_none_scope(self, tmp_path: Path):
        """Legacy skills under the old public/ layout have no mode_scope."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "public", "legacy-skill", "Legacy skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "legacy-skill" in by_name
        assert by_name["legacy-skill"].mode_scope is None
