"""Tests for Skill.work_modes — the frontmatter-declared work-mode binding.

Each skill carries a ``work_modes`` tuple (e.g. ``("task",)`` or
``("core",)``) read from its ``SKILL.md`` YAML frontmatter.  This replaces
the old directory-inferred ``mode_scope`` string.

Key behaviours:
  - Skills with ``work_modes: [core]`` are shared across all modes
  - Skills with ``work_modes: [task]`` appear only in task mode
  - Skills with ``work_modes: [coding]`` appear only in coding mode
  - A skill can be bound to multiple modes (``work_modes: [task, coding]``)
  - Builtin skills without frontmatter fall back to directory inference
  - Custom skills without frontmatter default to ``("task",)`` (lazy migration)
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(skill_dir: Path, name: str, description: str = "desc", work_modes: str | None = None) -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    frontmatter = f"---\nname: {name}\ndescription: {description}\n"
    if work_modes:
        frontmatter += f"work_modes: [{work_modes}]\n"
    frontmatter += "---\n\n"
    md.write_text(frontmatter + f"# {name}\n", encoding="utf-8")
    return md


class TestSkillWorkModesField:
    """The Skill dataclass must carry a work_modes field and mode_scope property."""

    def test_skill_dataclass_has_work_modes_field(self):
        """work_modes must be a dataclass field."""
        from kkoclaw.skills.types import Skill
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(Skill)}
        assert "work_modes" in field_names, "Skill dataclass must have a 'work_modes' field"

    def test_skill_mode_scope_is_not_a_field(self):
        """mode_scope must NOT be a dataclass field — it's a computed property now."""
        from kkoclaw.skills.types import Skill
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(Skill)}
        assert "mode_scope" not in field_names, "mode_scope should be a property, not a field"

    def test_skill_work_modes_defaults_empty(self):
        """work_modes defaults to an empty tuple."""
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
        assert skill.work_modes == ()
        assert skill.mode_scope is None

    def test_skill_mode_scope_returns_first_work_mode(self):
        """mode_scope property returns the first work_mode or None."""
        from kkoclaw.skills.types import Skill, SkillCategory

        skill = Skill(
            name="x",
            description="d",
            license=None,
            skill_dir=Path("/tmp"),
            skill_file=Path("/tmp/SKILL.md"),
            relative_path=Path("x"),
            category=SkillCategory.CUSTOM,
            work_modes=("task", "coding"),
        )
        assert skill.mode_scope == "task"
        assert skill.work_modes == ("task", "coding")


class TestLoadSkillsInfersWorkModes:
    """load_skills must populate work_modes from frontmatter or directory fallback."""

    def test_core_skill_has_core_mode(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "core", "bootstrap", "Bootstrap skill", work_modes="core")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "bootstrap" in by_name
        assert "core" in by_name["bootstrap"].work_modes

    def test_task_skill_has_task_mode(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "task", "deep-research", "Research skill", work_modes="task")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "task" in by_name["deep-research"].work_modes

    def test_coding_skill_has_coding_mode(self, tmp_path: Path):
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "coding", "code-review", "Review skill", work_modes="coding")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "coding" in by_name["code-review"].work_modes

    def test_skill_with_multiple_work_modes(self, tmp_path: Path):
        """A skill can declare work_modes: [task, coding] for one-to-many binding."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "task", "shared-skill", "Shared", work_modes="task, coding")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "shared-skill" in by_name
        assert set(by_name["shared-skill"].work_modes) == {"task", "coding"}

    def test_nested_coding_skill_falls_back_to_directory(self, tmp_path: Path):
        """Skills nested deeper (coding/sub-pkg) without frontmatter fall back to directory inference."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "builtin" / "coding" / "sub-pkg", "database", "DB skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "database" in by_name
        assert "coding" in by_name["database"].work_modes

    def test_custom_skill_without_frontmatter_defaults_to_task(self, tmp_path: Path):
        """Custom skills without work_modes frontmatter default to ('task',) via lazy migration."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "custom", "my-skill", "Custom skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "my-skill" in by_name
        assert by_name["my-skill"].work_modes == ("task",)

    def test_legacy_public_skill_has_no_work_modes(self, tmp_path: Path):
        """Legacy skills under the old public/ layout have no inferred work_modes."""
        from kkoclaw.skills.storage import get_or_new_skill_storage

        root = tmp_path / "skills"
        _write_skill(root / "public", "legacy-skill", "Legacy skill")
        skills = get_or_new_skill_storage(skills_path=root).load_skills(enabled_only=False)
        by_name = {s.name: s for s in skills}
        assert "legacy-skill" in by_name
        assert by_name["legacy-skill"].work_modes == ()
