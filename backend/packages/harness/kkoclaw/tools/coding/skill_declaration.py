"""Skill declaration tool for the Coding Agent.

Provides:
- ``declare_skill``: Let the model explicitly activate a coding skill.

The Qiongqi engine's keyword+TF-IDF matcher is good, but it cannot
catch every case — especially when the model has deeper context about
*why* a skill is needed that wasn't present in the original task text.

This tool closes that gap. The model can declare::

    declare_skill("security-review")

and the skill's instructions will be injected on the next middleware
pass, regardless of whether the task text matched the skill's keywords.

Anti-abuse: declared skills are recorded in ``runtime.state`` and
respected by ``CodingSkillsMiddleware`` on subsequent turns. They are
**additive** — they never remove auto-activated skills.
"""

from __future__ import annotations

import logging

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from kkoclaw.coding_core.skills import (
    CodingSkill,
    CodingSkillRegistry,
    load_skill_instructions,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# State key for model-declared skills.
_DECLARED_SKILLS_KEY = "_declared_coding_skills"

# Maximum skills the model can declare at once (prevents prompt flooding).
_MAX_DECLARED = 5


def get_declared_skills(runtime: Runtime) -> list[str]:
    """Read the list of model-declared skill ids from runtime state."""
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return []
    declared = state.get(_DECLARED_SKILLS_KEY)
    if not isinstance(declared, list):
        return []
    return [s for s in declared if isinstance(s, str)]


def add_declared_skill(runtime: Runtime, skill_id: str) -> None:
    """Add a skill id to the declared-skills state."""
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return
    declared = state.get(_DECLARED_SKILLS_KEY)
    if not isinstance(declared, list):
        declared = []
    if skill_id not in declared:
        declared.append(skill_id)
        # Cap to last N
        if len(declared) > _MAX_DECLARED:
            declared = declared[-_MAX_DECLARED:]
    state[_DECLARED_SKILLS_KEY] = declared


@tool("declare_skill", parse_docstring=True)
def declare_skill_tool(
    runtime: Runtime,
    skill_id: str,
    reason: str = "",
) -> str:
    """Explicitly activate a coding skill by its id.

    Use this when you recognize that a specific skill's guidance would
    help, even if the task text didn't auto-trigger it via keywords.

    For example, when reviewing code you might realize security concerns
    are relevant::

        declare_skill("security-review", "found potential SQL injection")

    The skill's instructions will be loaded and injected into the next
    middleware pass. Declared skills are additive — they supplement but
    never replace auto-activated skills.

    To discover available skill ids, use ``list_coding_skills``.

    Args:
        skill_id: The skill identifier (e.g. ``security-review``,
            ``test-driven-development``, ``refactoring``).
        reason: Short explanation of why this skill is being declared.
            Helps with auditability and skill-ROI tracking.
    """
    # Normalize
    skill_id = skill_id.strip()

    # Look up the skill in the registry
    context = getattr(runtime, "context", None) or {}
    config = getattr(runtime, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    project_root = context.get("project_root") or configurable.get("project_root")

    try:
        all_skills = CodingSkillRegistry.discover(project_root=project_root)
    except Exception as exc:
        logger.warning("declare_skill: failed to discover skills: %s", exc)
        return f"Error: Could not load skill registry: {exc}"

    # Find the target skill
    target: CodingSkill | None = None
    for skill in all_skills:
        if skill.id == skill_id:
            target = skill
            break

    if target is None:
        # Suggest similar skill ids
        from kkoclaw.coding_core.skills import rank_skills_semantic

        ranked = rank_skills_semantic(all_skills, skill_id, top_k=3, min_score=0.05)
        suggestions = ", ".join(f"'{s.id}' (score {score:.2f})" for s, score in ranked)
        return (
            f"Error: Skill '{skill_id}' not found. "
            + (f"Did you mean: {suggestions}?" if ranked else "No similar skills found.")
        )

    if not target.enabled:
        return f"Error: Skill '{skill_id}' is disabled (manifest errors: {target.manifest_errors})."

    # Verify instructions load
    instructions = load_skill_instructions(target)
    if not instructions:
        return f"Error: Skill '{skill_id}' has no instructions content."

    # Record in runtime state
    add_declared_skill(runtime, skill_id)

    reason_text = f" (reason: {reason})" if reason else ""
    result_msg = (
        f"Skill '{skill_id}' ({target.name}) declared active{reason_text}. "
        f"Its instructions ({len(instructions)} chars) will be loaded "
        f"on the next context update."
    )

    # If we have a tool_call_id, return via Command to update state
    tool_call_id = getattr(runtime, "tool_call_id", None)
    if tool_call_id:
        return Command(
            update={
                _DECLARED_SKILLS_KEY: get_declared_skills(runtime),
                "messages": [
                    ToolMessage(
                        content=result_msg,
                        tool_call_id=tool_call_id,
                    ),
                ],
            },
        )

    return result_msg


@tool("list_coding_skills", parse_docstring=True)
def list_coding_skills_tool(
    runtime: Runtime,
    query: str = "",
) -> str:
    """List available coding skills, optionally filtered by semantic query.

    Without a query, returns all registered skill ids with their names
    and descriptions. With a query, returns only skills that semantically
    match (using TF-IDF cosine similarity), sorted by relevance.

    Use this to discover skill ids before calling ``declare_skill``.

    Args:
        query: Optional natural-language filter. When provided, only
            semantically matching skills are returned (sorted by score).
            When omitted, all skills are listed alphabetically.
    """
    context = getattr(runtime, "context", None) or {}
    config = getattr(runtime, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    project_root = context.get("project_root") or configurable.get("project_root")

    try:
        all_skills = CodingSkillRegistry.discover(project_root=project_root)
    except Exception as exc:
        return f"Error: Could not load skill registry: {exc}"

    if not all_skills:
        return "No coding skills registered."

    if query.strip():
        # Semantic ranking
        from kkoclaw.coding_core.skills import rank_skills_semantic

        ranked = rank_skills_semantic(all_skills, query, top_k=10, min_score=0.05)
        if not ranked:
            return f"No skills semantically matching '{query}'."

        lines = [f"Skills matching '{query}' (top {len(ranked)}):\n"]
        for skill, score in ranked:
            status = "✅" if skill.enabled else "❌"
            lines.append(f"  {status} [{score:.2f}] {skill.id} — {skill.name}")
            desc = (skill.description or "")[:120]
            if desc:
                lines.append(f"           {desc}")
        return "\n".join(lines)

    # No query — list all
    enabled = [s for s in all_skills if s.enabled]
    disabled = [s for s in all_skills if not s.enabled]

    lines = [f"Registered coding skills ({len(enabled)} enabled, {len(disabled)} disabled):\n"]
    for skill in sorted(enabled, key=lambda s: s.id):
        desc = (skill.description or "")[:100]
        lines.append(f"  ✅ {skill.id} — {skill.name}")
        if desc:
            lines.append(f"     {desc}")

    if disabled:
        lines.append(f"\n  Disabled skills ({len(disabled)}):")
        for skill in sorted(disabled, key=lambda s: s.id):
            errors = ", ".join(skill.manifest_errors[:2]) if skill.manifest_errors else ""
            lines.append(f"  ❌ {skill.id} — {errors}")

    return "\n".join(lines)


__all__ = [
    "declare_skill_tool",
    "list_coding_skills_tool",
    "get_declared_skills",
    "add_declared_skill",
]
