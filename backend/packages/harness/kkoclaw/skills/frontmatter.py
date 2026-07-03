"""Frontmatter manipulation helpers for SKILL.md files.

Centralises the ``work_modes`` field injection logic so that both the
agent tool (``skill_manage_tool``), the HTTP API (``skills`` router) and
the installer (``local_skill_storage``) share one implementation.
"""

from __future__ import annotations

import re

# Matches the opening ``---\n``, the YAML body, and the closing ``\n---\n``.
_FRONTMATTER_RE = re.compile(r'^(---\s*\n)(.*?)(\n---\s*\n)', re.DOTALL)


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
