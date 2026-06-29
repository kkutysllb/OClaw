"""Work mode API endpoints.

These endpoints expose the work-mode presets (task / coding) and allow
per-mode skill management. Locked core skills are enforced via helpers from
``kkoclaw.skills.work_modes`` so the agent's self-bootstrap loop is never
broken from the UI.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.gateway.deps import get_config
from kkoclaw.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from kkoclaw.config.app_config import AppConfig
from kkoclaw.config.extensions_config import (
    get_extensions_config,
    reload_extensions_config,
)
from kkoclaw.skills.work_modes import (
    DEFAULT_LOCKED_SKILL_IDS,
    add_skill_to_mode,
    remove_skill_from_mode,
    resolve_effective_skill_ids,
    resolve_work_mode_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["work-modes"])


# ---------------------------------------------------------------------------
# Response models
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/work-modes",
    response_model=WorkModesListResponse,
    summary="List Work Modes",
    description="Retrieve all work modes with their effective skill sets.",
)
async def list_work_modes(config: AppConfig = Depends(get_config)) -> WorkModesListResponse:
    ext_config = get_extensions_config()
    modes: list[WorkModeDetailResponse] = []
    for mode_id, mode_cfg in ext_config.work_modes.modes.items():
        effective = resolve_effective_skill_ids(ext_config, mode_id)
        locked_set = set(ext_config.locked_skill_ids)
        skills = [
            WorkModeSkillEntry(skill_id=s, locked=s in locked_set)
            for s in effective
        ]
        modes.append(
            WorkModeDetailResponse(
                id=mode_cfg.id,
                name=mode_cfg.name,
                description=mode_cfg.description,
                builtin=mode_cfg.builtin,
                editable=mode_cfg.editable,
                is_default=(mode_id == ext_config.work_modes.default_mode_id),
                skills=skills,
                lead_agent_name=mode_cfg.lead_agent_name,
                orchestration_hint=mode_cfg.orchestration_hint,
                focus_areas=list(mode_cfg.focus_areas),
                skill_count=len(effective),
            )
        )
    return WorkModesListResponse(
        default_mode_id=ext_config.work_modes.default_mode_id,
        modes=modes,
    )


@router.delete(
    "/work-modes/{mode_id}",
    summary="Delete Work Mode",
    description="Delete a custom work mode. Built-in modes cannot be deleted.",
)
async def delete_work_mode(mode_id: str, config: AppConfig = Depends(get_config)):
    ext_config = get_extensions_config()
    mode_cfg = ext_config.work_modes.modes.get(mode_id)
    if mode_cfg is not None and mode_cfg.builtin:
        raise HTTPException(
            status_code=403,
            detail=f"Built-in work mode '{mode_id}' cannot be deleted.",
        )
    # Currently all modes are built-in. Custom mode deletion can be added later.
    raise HTTPException(
        status_code=403,
        detail=f"Work mode '{mode_id}' cannot be deleted.",
    )


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
