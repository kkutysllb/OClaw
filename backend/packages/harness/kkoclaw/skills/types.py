from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SKILL_MD_FILE = "SKILL.md"


class SkillCategory(StrEnum):
    """Source category for a skill.

    - ``PUBLIC`` (value ``"builtin"``): built-in skill bundled with the
      platform, read-only. Physically stored under ``skills/builtin/``
      with sub-directories ``core/``, ``task/``, ``coding/``.
    - ``CUSTOM`` (value ``"custom"``): user-authored skill that can be
      edited or deleted.

    Backward compatibility: the legacy value ``"public"`` is accepted as
    an alias for ``PUBLIC`` via :meth:`_missing_` so old configs and
    persisted state continue to work after the directory migration.
    """

    PUBLIC = "builtin"
    CUSTOM = "custom"

    @classmethod
    def _missing_(cls, value: object) -> "SkillCategory | None":
        """Map legacy value ``'public'`` to :attr:`PUBLIC`.

        Pre-migration configs and extensions_config.json files may still
        reference the old ``'public'`` string. This hook ensures
        ``SkillCategory('public')`` resolves to ``SkillCategory.PUBLIC``
        instead of raising ``ValueError``.
        """
        if isinstance(value, str) and value == "public":
            return cls.PUBLIC
        return None


@dataclass
class Skill:
    """Represents a skill with its metadata and file path"""

    name: str
    description: str
    license: str | None
    skill_dir: Path
    skill_file: Path
    relative_path: Path  # Relative path from category root to skill directory
    category: SkillCategory  # 'builtin' or 'custom'
    enabled: bool = False  # Whether this skill is enabled
    allowed_tools: list[str] | None = None
    # Work-mode binding inferred from the builtin sub-directory layout:
    #   "core"  → skills/builtin/core/   (shared by all modes)
    #   "task"  → skills/builtin/task/   (task/office mode)
    #   "coding"→ skills/builtin/coding/ (coding mode)
    #   None    → custom/ or legacy public/ skills (no auto mode binding)
    # Drives resolve_effective_skill_ids so each work mode only loads the
    # skills physically filed under its directory plus the shared core.
    mode_scope: str | None = None

    @property
    def skill_path(self) -> str:
        """Returns the relative path from the category root (skills/{category}) to this skill's directory"""
        path = self.relative_path.as_posix()
        return "" if path == "." else path

    def get_container_path(self, container_base_path: str = "/mnt/skills") -> str:
        """
        Get the full path to this skill in the container.

        Args:
            container_base_path: Base path where skills are mounted in the container

        Returns:
            Full container path to the skill directory
        """
        category_base = f"{container_base_path}/{self.category}"
        skill_path = self.skill_path
        if skill_path:
            return f"{category_base}/{skill_path}"
        return category_base

    def get_container_file_path(self, container_base_path: str = "/mnt/skills") -> str:
        """
        Get the full path to this skill's main file (SKILL.md) in the container.

        Args:
            container_base_path: Base path where skills are mounted in the container

        Returns:
            Full container path to the skill's SKILL.md file
        """
        return f"{self.get_container_path(container_base_path)}/SKILL.md"

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, description={self.description!r}, category={self.category!r})"
