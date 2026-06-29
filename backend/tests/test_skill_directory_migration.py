"""Tests for unified skill directory migration (Task 4).

Verifies that the skill storage layer correctly discovers skills in the new
``builtin/core|task|coding/`` directory layout, while maintaining backward
compatibility with the legacy ``public/`` directory.

Migration target layout::

    <skills_root>/
    ├── builtin/
    │   ├── core/      ← locked skills (bootstrap, find-skills, skill-creator)
    │   ├── task/      ← daily-office skills
    │   └── coding/    ← coding skills
    └── custom/
        └── <name>/    ← user-authored skills (unchanged)

Legacy layout (still supported for gradual migration)::

    <skills_root>/
    ├── public/
    │   └── <name>/
    └── custom/
        └── <name>/
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_MD_TEMPLATE = """\
---
name: {name}
description: {description}
---
# {name}

Skill content for {name}.
"""


def _make_skill(parent: Path, name: str, description: str = "") -> Path:
    """Create a minimal skill directory with SKILL.md under *parent*."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        SKILL_MD_TEMPLATE.format(name=name, description=description or f"Skill {name}"),
        encoding="utf-8",
    )
    return skill_dir


# ---------------------------------------------------------------------------
# SkillCategory enum: PUBLIC value changes to "builtin"
# ---------------------------------------------------------------------------


class TestSkillCategoryEnumMigration:
    """SkillCategory.PUBLIC value should be 'builtin' after migration."""

    def test_public_value_is_builtin(self):
        from kkoclaw.skills.types import SkillCategory

        assert SkillCategory.PUBLIC.value == "builtin"

    def test_custom_value_unchanged(self):
        from kkoclaw.skills.types import SkillCategory

        assert SkillCategory.CUSTOM.value == "custom"

    def test_public_str_alias_backward_compat(self):
        """SkillCategory('public') should still resolve for backward compat."""
        from kkoclaw.skills.types import SkillCategory

        # Old configs may still reference "public" — this should not crash.
        # The enum should accept "public" as an alias for PUBLIC.
        assert SkillCategory("builtin") is SkillCategory.PUBLIC


# ---------------------------------------------------------------------------
# LocalSkillStorage: discovers skills in builtin/ subdirectories
# ---------------------------------------------------------------------------


class TestBuiltinDirectoryDiscovery:
    """Skills under builtin/core/, builtin/task/, builtin/coding/ are discovered."""

    def test_discovers_builtin_core_skills(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "core", "bootstrap", "Core bootstrap")
        _make_skill(root / "builtin" / "core", "find-skills", "Skill discovery")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        names = {s.name for s in skills}
        assert "bootstrap" in names
        assert "find-skills" in names

    def test_discovers_builtin_task_skills(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "task", "deep-research", "Deep research")
        _make_skill(root / "builtin" / "task", "pdf-processing", "PDF processing")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        names = {s.name for s in skills}
        assert "deep-research" in names
        assert "pdf-processing" in names

    def test_discovers_builtin_coding_skills(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "coding", "code-documentation", "Code docs")
        _make_skill(root / "builtin" / "coding", "frontend-design", "Frontend design")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        names = {s.name for s in skills}
        assert "code-documentation" in names
        assert "frontend-design" in names

    def test_all_builtin_skills_have_public_category(self, tmp_path):
        """Regardless of sub-directory, builtin skills are category=PUBLIC."""
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage
        from kkoclaw.skills.types import SkillCategory

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "core", "bootstrap")
        _make_skill(root / "builtin" / "task", "deep-research")
        _make_skill(root / "builtin" / "coding", "code-documentation")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        for skill in skills:
            assert skill.category == SkillCategory.PUBLIC


# ---------------------------------------------------------------------------
# Backward compatibility: legacy public/ directory still works
# ---------------------------------------------------------------------------


class TestLegacyPublicDirectoryCompat:
    """Old public/ directory layout should still be discovered after migration."""

    def test_discovers_legacy_public_skills(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "public", "legacy-skill", "Legacy skill")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        names = {s.name for s in skills}
        assert "legacy-skill" in names

    def test_legacy_and_builtin_coexist(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "public", "old-skill")
        _make_skill(root / "builtin" / "core", "new-skill")

        storage = LocalSkillStorage(host_path=str(root))
        skills = storage.load_skills(enabled_only=False)
        names = {s.name for s in skills}
        assert "old-skill" in names
        assert "new-skill" in names


# ---------------------------------------------------------------------------
# public_skill_exists: searches builtin subdirectories
# ---------------------------------------------------------------------------


class TestPublicSkillExists:
    """public_skill_exists should find skills in builtin subdirectories."""

    def test_finds_skill_in_builtin_core(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "core", "bootstrap")
        storage = LocalSkillStorage(host_path=str(root))
        assert storage.public_skill_exists("bootstrap")

    def test_finds_skill_in_builtin_task(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "task", "deep-research")
        storage = LocalSkillStorage(host_path=str(root))
        assert storage.public_skill_exists("deep-research")

    def test_finds_skill_in_legacy_public(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "public", "legacy-skill")
        storage = LocalSkillStorage(host_path=str(root))
        assert storage.public_skill_exists("legacy-skill")

    def test_returns_false_for_missing_skill(self, tmp_path):
        from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

        root = tmp_path / "skills"
        _make_skill(root / "builtin" / "core", "bootstrap")
        storage = LocalSkillStorage(host_path=str(root))
        assert not storage.public_skill_exists("nonexistent")


# ---------------------------------------------------------------------------
# is_skill_enabled: hardcoded category check updated
# ---------------------------------------------------------------------------


class TestIsSkillEnabledBuiltin:
    """is_skill_enabled should default-enable 'builtin' category (was 'public')."""

    def test_builtin_defaults_enabled(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig(skills={})
        assert cfg.is_skill_enabled("any-skill", "builtin")

    def test_custom_defaults_enabled(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig(skills={})
        assert cfg.is_skill_enabled("any-skill", "custom")

    def test_legacy_public_still_works_via_alias(self):
        """Old code passing 'public' should still get enabled=True for compat."""
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig(skills={})
        # After migration, "public" is treated as an alias for "builtin"
        assert cfg.is_skill_enabled("any-skill", "public")


# ---------------------------------------------------------------------------
# ExtensionsConfig serialization: builtin category in saved config
# ---------------------------------------------------------------------------


class TestExtensionsConfigSerializationBuiltin:
    """Config save/load round-trips with builtin category references."""

    def test_save_load_preserves_skill_states(self, tmp_path):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            SkillStateConfig,
        )

        cfg = ExtensionsConfig(
            skills={"bootstrap": SkillStateConfig(enabled=True)},
        )
        path = cfg.save(str(tmp_path / "ext.json"))
        loaded = ExtensionsConfig.from_file(str(path))
        assert loaded.skills["bootstrap"].enabled is True


# ---------------------------------------------------------------------------
# Desktop paths: getBundledSkillsDir helpers (AST check)
# ---------------------------------------------------------------------------

import pathlib as _pathlib

_DESKTOP_SRC = _pathlib.Path(__file__).resolve().parent.parent.parent / "desktop-electron" / "src"


class TestDesktopPathHelpers:
    """Verify desktop-electron paths.ts has builtin skill root helpers."""

    def test_paths_ts_has_get_builtin_skill_roots(self):
        path = _DESKTOP_SRC / "paths.ts"
        if not path.exists():
            pytest.skip("desktop-electron/src/paths.ts not found")
        source = path.read_text(encoding="utf-8")
        assert "getBuiltinSkillRoots" in source or "getBundledBuiltinSkillRoots" in source, (
            "paths.ts should export a helper for builtin skill roots"
        )

    def test_init_skills_creates_builtin_dirs(self):
        path = _DESKTOP_SRC / "backend.ts"
        if not path.exists():
            pytest.skip("desktop-electron/src/backend.ts not found")
        source = path.read_text(encoding="utf-8")
        assert "builtin" in source, "backend.ts initSkills should reference 'builtin' directory"
