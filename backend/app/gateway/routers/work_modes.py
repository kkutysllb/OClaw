"""Work mode API endpoints.

These endpoints expose the work-mode presets (task / coding + per-user
custom modes) and allow per-mode skill management. Locked core skills
are enforced via helpers from ``kkoclaw.skills.work_modes`` so the
agent's self-bootstrap loop is never broken from the UI.

Per-user isolation
------------------
Built-in modes (task / coding) are always visible to every user. Custom
modes are stored per-user in the ``user_work_modes`` table and merged
at resolve time. For ``DEFAULT_USER_ID`` (unauthenticated CLI / tests /
studio) only the builtin presets are returned, preserving legacy
behaviour.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.gateway.deps import get_config
from kkoclaw.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from kkoclaw.config.app_config import AppConfig
from kkoclaw.config.extensions_config import (
    WorkModeConfig,
    get_extensions_config,
    reload_extensions_config,
)
from kkoclaw.config.user_work_modes_config import (
    invalidate_user_work_modes,
    resolve_user_work_modes,
)
from kkoclaw.runtime.user_context import DEFAULT_USER_ID, get_effective_user_id
from kkoclaw.skills.work_modes import (
    DEFAULT_LOCKED_SKILL_IDS,
    add_skill_to_mode,
    remove_skill_from_mode,
    resolve_effective_skill_ids,
    resolve_work_mode_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["work-modes"])

#: Slug pattern for custom work-mode ids. Mirrors the agent-name pattern
#: but additionally forbids upper-case so ids read uniformly.
_MODE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class WorkModeSkillEntry(BaseModel):
    """A single skill entry within a work mode."""

    skill_id: str = Field(..., description="Skill identifier")
    locked: bool = Field(default=False, description="Whether this is a locked core skill")


class WorkModeDetailResponse(BaseModel):
    """Detailed information about a single work mode."""

    id: str
    name: str
    description: str
    builtin: bool
    editable: bool
    is_default: bool = Field(default=False, description="Whether this is the default mode")
    skills: list[WorkModeSkillEntry] = Field(default_factory=list)
    lead_agent_name: str = Field(default="", description="Display name of the bound lead agent")
    orchestration_hint: str = Field(default="", description="Mode-specific task orchestration guidance")
    focus_areas: list[str] = Field(default_factory=list, description="Focus area tags for this mode")
    skill_count: int = Field(default=0, description="Total number of effective skills in this mode")


class WorkModesListResponse(BaseModel):
    """Response model for listing all work modes."""

    default_mode_id: str
    modes: list[WorkModeDetailResponse]


class WorkModeSkillActionResponse(BaseModel):
    """Response model for add/remove skill from mode actions."""

    success: bool
    mode_id: str
    skill_name: str
    action: str = Field(..., description='"added" or "removed"')


class CustomWorkModeCreateRequest(BaseModel):
    """Request body for creating a custom work mode."""

    id: str = Field(
        ...,
        description=(
            "Slug-style unique identifier (e.g. 'research', 'finance'). "
            "Must match ^[a-z0-9][a-z0-9_-]*$ and must not collide with "
            "builtin ids ('task', 'coding', 'core')."
        ),
    )
    name: str = Field(..., min_length=1, max_length=128, description="Human-readable display name")
    description: str = Field(default="", max_length=200, description="One-line summary for humans")
    orchestration_hint: str = Field(
        default="",
        max_length=4000,
        description="Mode-specific task orchestration guidance injected into the lead agent's system prompt",
    )
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Focus area tags (e.g. ['research', 'papers'])",
    )


class CustomWorkModeUpdateRequest(BaseModel):
    """Request body for updating an existing custom work mode.

    All fields are optional; only the provided fields are updated.
    The ``id`` cannot be changed — delete and re-create if a rename is
    needed.
    """

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=200)
    orchestration_hint: str | None = Field(default=None, max_length=4000)
    focus_areas: list[str] | None = Field(default=None)


class CustomWorkModeActionResponse(BaseModel):
    """Response model for custom work-mode CRUD actions."""

    success: bool
    mode_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_work_mode_repo():
    """Instantiate the UserWorkModeRepository from the global session factory."""
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode.sql import UserWorkModeRepository

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Persistence engine not available")
    return UserWorkModeRepository(sf)


def _build_mode_detail(
    mode_id: str,
    mode_cfg: WorkModeConfig,
    *,
    default_mode_id: str,
    locked_set: set[str],
    ext_config,
) -> WorkModeDetailResponse:
    """Build a ``WorkModeDetailResponse`` from a mode config + skill resolution."""
    effective = resolve_effective_skill_ids(ext_config, mode_id)
    skills = [
        WorkModeSkillEntry(skill_id=s, locked=s in locked_set)
        for s in effective
    ]
    return WorkModeDetailResponse(
        id=mode_cfg.id,
        name=mode_cfg.name,
        description=mode_cfg.description,
        builtin=mode_cfg.builtin,
        editable=mode_cfg.editable,
        is_default=(mode_id == default_mode_id),
        skills=skills,
        lead_agent_name=mode_cfg.lead_agent_name,
        orchestration_hint=mode_cfg.orchestration_hint,
        focus_areas=list(mode_cfg.focus_areas),
        skill_count=len(effective),
    )


# ---------------------------------------------------------------------------
# Endpoints — list & detail
# ---------------------------------------------------------------------------


@router.get(
    "/work-modes",
    response_model=WorkModesListResponse,
    summary="List Work Modes",
    description="Retrieve all work modes (builtin + per-user custom) with their effective skill sets.",
)
async def list_work_modes(config: AppConfig = Depends(get_config)) -> WorkModesListResponse:
    user_id = get_effective_user_id()
    ext_config = get_extensions_config()
    locked_set = set(ext_config.locked_skill_ids)

    # Resolve the effective work-modes config for this user (builtin + custom).
    wm_config = await resolve_user_work_modes(user_id)

    modes: list[WorkModeDetailResponse] = []
    for mode_id, mode_cfg in wm_config.modes.items():
        modes.append(
            _build_mode_detail(
                mode_id,
                mode_cfg,
                default_mode_id=wm_config.default_mode_id,
                locked_set=locked_set,
                ext_config=ext_config,
            )
        )
    return WorkModesListResponse(
        default_mode_id=wm_config.default_mode_id,
        modes=modes,
    )


# ---------------------------------------------------------------------------
# Endpoints — custom work-mode CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/work-modes",
    response_model=WorkModeDetailResponse,
    summary="Create Custom Work Mode",
    description=(
        "Create a per-user custom work mode. The mode id must not collide "
        "with builtin ids ('task', 'coding', 'core') or any of the user's "
        "existing custom modes. After creation, the caller is expected to "
        "navigate to the skills page and bind skills to the new mode by "
        "creating skills under it."
    ),
)
async def create_custom_work_mode(
    request: CustomWorkModeCreateRequest,
    config: AppConfig = Depends(get_config),
) -> WorkModeDetailResponse:
    user_id = get_effective_user_id()
    if user_id == DEFAULT_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="Custom work modes require an authenticated user.",
        )

    mode_id = request.id.strip()
    if not _MODE_ID_PATTERN.match(mode_id):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid mode id '{mode_id}'. Must match ^[a-z0-9][a-z0-9_-]*$ "
                "(lowercase letters, digits, hyphens, underscores; must start "
                "alphanumerically)."
            ),
        )

    repo = _get_work_mode_repo()

    # Collision check: reject if the id is already taken by a builtin or
    # one of the user's existing custom modes.
    existing_ids = await get_user_custom_mode_ids_for_router(user_id)
    reserved = {"task", "coding", "core"}
    if mode_id in reserved or mode_id in existing_ids:
        raise HTTPException(
            status_code=409,
            detail=f"A work mode with id '{mode_id}' already exists.",
        )

    try:
        row = await repo.upsert(
            mode_id=mode_id,
            name=request.name.strip(),
            description=request.description.strip(),
            orchestration_hint=request.orchestration_hint,
            focus_areas=request.focus_areas,
            enabled=True,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    invalidate_user_work_modes(user_id)

    # Return the freshly created mode detail. Resolve the merged config so
    # the response includes effective skills (empty for a brand-new mode
    # apart from locked core skills).
    ext_config = get_extensions_config()
    wm_config = await resolve_user_work_modes(user_id)
    mode_cfg = wm_config.modes.get(mode_id)
    if mode_cfg is None:  # defensive — should never happen after upsert
        raise HTTPException(status_code=500, detail="Failed to load created work mode.")
    return _build_mode_detail(
        mode_id,
        mode_cfg,
        default_mode_id=wm_config.default_mode_id,
        locked_set=set(ext_config.locked_skill_ids),
        ext_config=ext_config,
    )


@router.put(
    "/work-modes/{mode_id}",
    response_model=WorkModeDetailResponse,
    summary="Update Custom Work Mode",
    description=(
        "Update an existing custom work mode. Builtin modes (task / coding) "
        "cannot be edited through this endpoint. Only the provided fields "
        "are updated; the mode id is immutable."
    ),
)
async def update_custom_work_mode(
    mode_id: str,
    request: CustomWorkModeUpdateRequest,
    config: AppConfig = Depends(get_config),
) -> WorkModeDetailResponse:
    user_id = get_effective_user_id()
    if user_id == DEFAULT_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="Custom work modes require an authenticated user.",
        )

    repo = _get_work_mode_repo()
    existing = await repo.get_mode(mode_id, user_id=user_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Custom work mode '{mode_id}' not found.",
        )

    # Merge provided fields with existing values.
    new_name = request.name if request.name is not None else existing["name"]
    new_description = request.description if request.description is not None else existing["description"]
    new_hint = request.orchestration_hint if request.orchestration_hint is not None else existing["orchestration_hint"]
    new_focus = request.focus_areas if request.focus_areas is not None else existing["focus_areas"]

    try:
        await repo.upsert(
            mode_id=mode_id,
            name=new_name,
            description=new_description,
            orchestration_hint=new_hint,
            focus_areas=new_focus,
            enabled=existing.get("enabled", True),
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    invalidate_user_work_modes(user_id)

    ext_config = get_extensions_config()
    wm_config = await resolve_user_work_modes(user_id)
    mode_cfg = wm_config.modes.get(mode_id)
    if mode_cfg is None:
        raise HTTPException(status_code=500, detail="Failed to load updated work mode.")
    return _build_mode_detail(
        mode_id,
        mode_cfg,
        default_mode_id=wm_config.default_mode_id,
        locked_set=set(ext_config.locked_skill_ids),
        ext_config=ext_config,
    )


@router.delete(
    "/work-modes/{mode_id}",
    response_model=CustomWorkModeActionResponse,
    summary="Delete Work Mode",
    description=(
        "Delete a custom work mode. Built-in modes (task / coding) cannot be "
        "deleted. Skills previously bound to the deleted mode (via their "
        "SKILL.md ``work_modes`` frontmatter) will simply no longer be "
        "activated by it — their frontmatter is left untouched."
    ),
)
async def delete_work_mode(
    mode_id: str,
    config: AppConfig = Depends(get_config),
) -> CustomWorkModeActionResponse:
    user_id = get_effective_user_id()
    if user_id == DEFAULT_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="Custom work modes require an authenticated user.",
        )

    # Reject builtin ids up front.
    if mode_id in {"task", "coding", "core"}:
        raise HTTPException(
            status_code=403,
            detail=f"Built-in work mode '{mode_id}' cannot be deleted.",
        )

    repo = _get_work_mode_repo()
    try:
        deleted = await repo.delete(mode_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Custom work mode '{mode_id}' not found.",
        )

    invalidate_user_work_modes(user_id)
    return CustomWorkModeActionResponse(success=True, mode_id=mode_id)


# ---------------------------------------------------------------------------
# Endpoints — per-mode skill add / remove (unchanged behaviour)
# ---------------------------------------------------------------------------


@router.put(
    "/work-modes/{mode_id}/skills/{skill_name}",
    response_model=WorkModeSkillActionResponse,
    summary="Add Skill to Work Mode",
    description="Add a skill to a work mode's effective set via mode overrides.",
)
async def add_skill_to_work_mode(
    mode_id: str,
    skill_name: str,
    config: AppConfig = Depends(get_config),
) -> WorkModeSkillActionResponse:
    resolved = resolve_work_mode_id(mode_id)
    try:
        ext_config = get_extensions_config()
        updated = add_skill_to_mode(ext_config, resolved, skill_name)
        updated.save()
        reload_extensions_config()
        await refresh_skills_system_prompt_cache_async()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add skill %s to mode %s: %s", skill_name, mode_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add skill to work mode: {e}")
    return WorkModeSkillActionResponse(
        success=True,
        mode_id=resolved,
        skill_name=skill_name,
        action="added",
    )


@router.delete(
    "/work-modes/{mode_id}/skills/{skill_name}",
    response_model=WorkModeSkillActionResponse,
    summary="Remove Skill from Work Mode",
    description="Remove a skill from a work mode. Locked skills cannot be removed.",
)
async def remove_skill_from_work_mode(
    mode_id: str,
    skill_name: str,
    config: AppConfig = Depends(get_config),
) -> WorkModeSkillActionResponse:
    resolved = resolve_work_mode_id(mode_id)
    try:
        ext_config = get_extensions_config()
        updated = remove_skill_from_mode(ext_config, resolved, skill_name)
        updated.save()
        reload_extensions_config()
        await refresh_skills_system_prompt_cache_async()
    except ValueError as e:
        # Locked skill → 403
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove skill %s from mode %s: %s", skill_name, mode_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove skill from work mode: {e}")
    return WorkModeSkillActionResponse(
        success=True,
        mode_id=resolved,
        skill_name=skill_name,
        action="removed",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def get_user_custom_mode_ids_for_router(user_id: str) -> set[str]:
    """Return the user's existing custom mode ids (for collision checks)."""
    from kkoclaw.config.user_work_modes_config import get_user_custom_mode_ids

    return await get_user_custom_mode_ids(user_id)
