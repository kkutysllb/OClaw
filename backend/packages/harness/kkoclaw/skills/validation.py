"""Skill frontmatter validation utilities.

Pure-logic validation of SKILL.md frontmatter — no FastAPI or HTTP dependencies.
"""

import re
from pathlib import Path

import yaml

from kkoclaw.skills.types import SKILL_MD_FILE

# Allowed properties in SKILL.md frontmatter
ALLOWED_FRONTMATTER_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility", "version", "author", "work_modes"}

# Mode ids that are always valid regardless of config extensions.
# "core" means shared by all modes; task/coding are the built-in presets.
_BUILTIN_MODE_IDS = {"core", "task", "coding"}

# Cross-platform compatibility keys that are normalised into metadata.compat
# rather than rejected outright.  These keys appear in skill templates from
# other platforms (Claude Code, Qoder, Anthropic skill marketplace, etc.) and
# should degrade gracefully. Common ones:
#   - capabilities / inputs / permissions / requires / tags: Claude Code skills
#   - category: skill-marketplace categorisation (e.g. "coding", "productivity")
#   - package: packaging-tool provenance metadata
#   - keywords: search/discovery tags used by skill marketplaces
#   - dependencies: declares runtime dependencies on other skills/packages
_COMPAT_FRONTMATTER_KEYS = {
    "capabilities",
    "inputs",
    "permissions",
    "requires",
    "tags",
    "category",
    "package",
    "keywords",
    "dependencies",
}


def _normalise_skill_frontmatter(frontmatter: dict) -> dict:
    """Normalise frontmatter for cross-platform compatibility.

    Moves recognised compatibility keys into ``metadata.compat`` so that
    skills authored for other platforms are accepted without loss of
    information.  Keys that are already in the allowed set or that are
    unknown are left untouched — the caller is responsible for rejecting
    truly unknown keys.
    """
    compat_values: dict[str, object] = {}
    for key in _COMPAT_FRONTMATTER_KEYS:
        if key in frontmatter:
            compat_values[key] = frontmatter.pop(key)
    if compat_values:
        metadata = frontmatter.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            # If metadata is present but not a dict, wrap it so we don't
            # destroy existing data.
            metadata = {"_value": metadata}
            frontmatter["metadata"] = metadata
        compat_ns = metadata.setdefault("compat", {})
        if isinstance(compat_ns, dict):
            compat_ns.update(compat_values)
    return frontmatter


def _validate_skill_frontmatter(skill_dir: Path) -> tuple[bool, str, str | None]:
    """Validate a skill directory's SKILL.md frontmatter.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.

    Returns:
        Tuple of (is_valid, message, skill_name).
    """
    skill_md = skill_dir / SKILL_MD_FILE
    if not skill_md.exists():
        return False, f"{SKILL_MD_FILE} not found", None

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found", None

    # Extract frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format", None

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary", None
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}", None

    # Normalise cross-platform compatibility keys into metadata.compat
    frontmatter = _normalise_skill_frontmatter(frontmatter)

    # Check for unexpected properties
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_PROPERTIES
    if unexpected_keys:
        return False, f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}", None

    # Check required fields
    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter", None
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter", None

    # Validate name
    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}", None
    name = name.strip()
    if not name:
        return False, "Name cannot be empty", None

    # Normalise to hyphen-case: lowercase + underscores/spaces → hyphens.
    # This mirrors SkillStorage.validate_skill_name so that skills authored
    # with underscores (e.g. "backtrader_strategies") are accepted and
    # silently normalised to "backtrader-strategies" rather than rejected.
    # The caller (installer / router) receives the normalised name via the
    # return tuple and uses it for the on-disk directory.
    name = name.lower()
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")

    # Check naming convention (hyphen-case: lowercase with hyphens)
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)", None
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens", None
    if len(name) > 64:
        return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters.", None

    # Validate description
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}", None
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)", None
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters.", None

    # Validate work_modes (optional, one-to-many mode binding)
    raw_modes = frontmatter.get("work_modes")
    if raw_modes is not None:
        if isinstance(raw_modes, str):
            mode_list = [raw_modes]
        elif isinstance(raw_modes, list):
            mode_list = raw_modes
        else:
            return False, f"work_modes must be a list or string, got {type(raw_modes).__name__}", None
        for entry in mode_list:
            if not isinstance(entry, str) or not entry.strip():
                return False, "work_modes entries must be non-empty strings", None
            mid = entry.strip()
            # Allow built-in ids (core/task/coding) plus future custom mode
            # ids that match the same naming convention as skill names.
            if mid not in _BUILTIN_MODE_IDS and not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", mid):
                return False, f"work_modes entry '{mid}' is not a valid mode id", None

    return True, "Skill is valid!", name
