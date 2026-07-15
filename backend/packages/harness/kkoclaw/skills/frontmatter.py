"""Frontmatter manipulation helpers for SKILL.md files.

Centralises the ``work_modes`` field injection logic so that both the
agent tool (``skill_manage_tool``), the HTTP API (``skills`` router) and
the installer (``local_skill_storage``) share one implementation.

Also exposes the deer-flow review-core schema helpers
(``ALLOWED_FRONTMATTER_PROPERTIES``, ``split_skill_markdown``) so the ported
``skills.review`` package shares one frontmatter schema source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

# Matches the opening ``---\n``, the YAML body, and the closing ``\n---\n``.
_FRONTMATTER_RE = re.compile(r'^(---\s*\n)(.*?)(\n---\s*\n)', re.DOTALL)

# Allowed SKILL.md frontmatter properties (deer-flow review schema).
ALLOWED_FRONTMATTER_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "required-secrets",
    "secrets-autonomous",
    "metadata",
    "compatibility",
    "version",
    "author",
    "work_modes",  # OClaw extension
}


@dataclass(frozen=True)
class SkillMarkdownParts:
    """Parsed pieces of a SKILL.md document."""

    metadata: dict[str, Any]
    frontmatter_text: str
    body: str


def split_skill_markdown(content: str) -> tuple[SkillMarkdownParts | None, str | None]:
    """Split a SKILL.md document into frontmatter and body (deer-flow review helper).

    Returns ``(parts, None)`` on success and ``(None, message)`` on failure. The
    message intentionally avoids host paths so callers can reuse it in
    deterministic review output.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None, "No YAML frontmatter found"

    frontmatter_text = match.group(2)
    try:
        metadata = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        return None, f"Invalid YAML in frontmatter: {exc}"

    if not isinstance(metadata, dict):
        return None, "Frontmatter must be a YAML dictionary"

    return (
        SkillMarkdownParts(
            metadata=metadata,
            frontmatter_text=frontmatter_text,
            body=content[match.end():],
        ),
        None,
    )


def has_work_modes_frontmatter(content: str) -> bool:
    """Return ``True`` when the YAML frontmatter already declares ``work_modes``."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return False
    body = match.group(2)
    return any(line.strip().startswith("work_modes:") for line in body.split("\n"))


def inject_work_modes_frontmatter(content: str, work_modes: list[str]) -> str:
    """Inject or replace the ``work_modes`` field in SKILL.md frontmatter.

    Adds a line like ``work_modes: [task, coding]`` to the YAML frontmatter
    block.  If the field already exists it is replaced.  Returns the content
    unchanged when no frontmatter block is found (the validator rejects it).

    Args:
        content: The raw SKILL.md file content.
        work_modes: Ordered list of mode ids to bind (e.g. ``["task", "coding"]``).

    Returns:
        The content with ``work_modes`` injected into the frontmatter.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return content
    opener, body, closer = match.group(1), match.group(2), match.group(3)
    rest = content[match.end():]
    # Strip any existing work_modes line so we don't duplicate the field.
    body_lines = [
        line for line in body.split("\n")
        if not line.strip().startswith("work_modes:")
    ]
    if work_modes:
        modes_str = ", ".join(work_modes)
        body_lines.append(f"work_modes: [{modes_str}]")
    new_body = "\n".join(body_lines)
    return opener + new_body + closer + rest
