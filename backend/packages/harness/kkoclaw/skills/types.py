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
    # Work-mode bindings declared in SKILL.md frontmatter (one-to-many).
    #   ("task",)              → only active in task mode
    #   ("task", "coding")     → active in both task and coding modes
    #   ("core",)              → shared by ALL modes (global baseline)
    #   ()                     → uncategorised, not auto-loaded in any mode
    #
    # This is the single source of truth for mode membership — the physical
    # directory layout (builtin/core, builtin/task, builtin/coding) is only a
    # development-time organisational hint, not a runtime binding mechanism.
    # ``resolve_effective_skill_ids`` selects skills whose ``work_modes``
    # contains the active mode id or "core".
    work_modes: tuple[str, ...] = ()

    @property
    def mode_scope(self) -> str | None:
        """Backward-compat shim: first declared work mode, or None.

        Legacy callers that still expect a single ``mode_scope`` string get
        the first entry of :attr:`work_modes`. Returns ``None`` when the skill
        is uncategorised (empty tuple).
        """
        return self.work_modes[0] if self.work_modes else None

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
