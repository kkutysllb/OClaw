"""
Cron job management router.

Cron jobs are stored in an independent ``cron_config.json`` file (not inside
``extensions_config.json``) so that they can be managed independently.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["crons"])

# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------

CRON_CONFIG_FILENAME = "cron_config.json"


def _resolve_cron_config_path() -> Path:
    """Locate or default the cron config file.

    Look for the file in the same parent directory as ``config.yaml``.
    If no config.yaml is found, default to the project root.
    """
    from kkoclaw.config.app_config import AppConfig

    config_path = AppConfig.resolve_config_path()
    if config_path is not None:
        parent_dir = config_path.parent
        return parent_dir / CRON_CONFIG_FILENAME
    # Fallback: project root (one level above the backend directory)
    return Path.cwd().parent / CRON_CONFIG_FILENAME


def _load_cron_config() -> dict[str, Any]:
    """Load the full cron_config.json as a dict.

    Returns ``{"cronJobs": {}}`` when the file is missing OR when it is
    corrupt (invalid UTF-8 / invalid JSON). A corrupt file was observed in
    the wild after a non-atomic concurrent write — see ``_save_cron_config``.
    Logging the corruption once is preferable to crashing the scheduler
    poll loop and the REST handlers that depend on this helper.
    """
    path = _resolve_cron_config_path()
    if not path.exists():
        return {"cronJobs": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {"cronJobs": {}}
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        logger.warning(
            "cron_config.json at %s is corrupt (%s); treating as empty. "
            "The next successful save will overwrite it atomically.",
            path,
            exc,
        )
        return {"cronJobs": {}}


def _save_cron_config(data: dict[str, Any]) -> Path:
    """Write the dict to cron_config.json atomically.

    Writes to a sibling temp file then ``os.replace()``s it into place.
    This guarantees readers (the scheduler poll loop, other REST handlers)
    never observe a half-written file — which previously produced a
    corrupt JSON / invalid UTF-8 blob when two writers raced or a write
    was interrupted.
    """
    import os
    import tempfile

    path = _resolve_cron_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp in the same dir guarantees the rename is atomic on the same
    # filesystem (os.replace is atomic, but only within one fs).
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=".cron_config.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        # Best-effort cleanup of the temp file on failure; the original
        # file is untouched because we haven't replaced it yet.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    logger.info(f"cron_config.json written to {path}")
    return path


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CronJobRequest(BaseModel):
    """Request model for creating or updating a cron job."""

    enabled: bool = Field(default=True, description="Whether the cron job is enabled")
    cron: str = Field(..., description="6-field cron expression: sec min hour day month weekday")
    description: str = Field(default="", description="Human-readable description of the task")
    agent: str = Field(default="lead_agent", description="Agent name to use for this task")
    model: str | None = Field(default=None, description="Model ID to use (optional, uses default if empty)")
    prompt: str = Field(..., description="The prompt/message to send to the agent")


class CronJobResponse(BaseModel):
    """Response model for a single cron job."""

    enabled: bool = Field(default=True, description="Whether the cron job is enabled")
    cron: str = Field(..., description="6-field cron expression")
    description: str = Field(default="", description="Task description")
    agent: str = Field(default="lead_agent", description="Agent name")
    model: str | None = Field(default=None, description="Model ID")
    prompt: str = Field(..., description="The prompt message")


class CronJobsListResponse(BaseModel):
    """Response model for listing all cron jobs."""

    cron_jobs: dict[str, CronJobResponse] = Field(
        default_factory=dict,
        description="Map of cron job name to configuration",
    )


class CronJobToggleRequest(BaseModel):
    """Request model for toggling a cron job's enabled state."""

    enabled: bool = Field(..., description="New enabled state")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/crons",
    response_model=CronJobsListResponse,
    summary="List All Cron Jobs",
    description="Retrieve all configured cron jobs from cron_config.json.",
)
async def list_crons() -> CronJobsListResponse:
    """List all cron jobs."""
    try:
        config = _load_cron_config()
        jobs = config.get("cronJobs", {})
        return CronJobsListResponse(
            cron_jobs={name: CronJobResponse(**job) for name, job in jobs.items()}
        )
    except Exception as e:
        logger.error(f"Failed to list cron jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list cron jobs: {str(e)}")


@router.post(
    "/crons",
    response_model=CronJobResponse,
    status_code=201,
    summary="Create Cron Job",
    description="Add a new cron job and persist to cron_config.json.",
)
async def create_cron(req: CronJobRequest) -> CronJobResponse:
    """Create a new cron job.

    The cron job name is derived from the request body (must include ``name``).
    We use a query parameter for simplicity.
    """
    raise HTTPException(status_code=400, detail="Use POST /api/crons/{name} with a path-based name.")


@router.post(
    "/crons/{name}",
    response_model=CronJobResponse,
    status_code=201,
    summary="Create Cron Job",
    description="Add a new cron job with the given name.",
)
async def create_cron_named(name: str, req: CronJobRequest) -> CronJobResponse:
    """Create a new cron job with a path-based name."""
    try:
        config = _load_cron_config()
        jobs = config.setdefault("cronJobs", {})

        if name in jobs:
            raise HTTPException(status_code=409, detail=f"Cron job '{name}' already exists")

        job_data = req.model_dump()
        jobs[name] = job_data
        _save_cron_config(config)
        logger.info(f"Cron job '{name}' created")
        return CronJobResponse(**job_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create cron job '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create cron job: {str(e)}")


@router.put(
    "/crons/{name}",
    response_model=CronJobResponse,
    summary="Update Cron Job",
    description="Update an existing cron job configuration.",
)
async def update_cron(name: str, req: CronJobRequest) -> CronJobResponse:
    """Update an existing cron job."""
    try:
        config = _load_cron_config()
        jobs = config.get("cronJobs", {})

        if name not in jobs:
            raise HTTPException(status_code=404, detail=f"Cron job '{name}' not found")

        job_data = req.model_dump()
        jobs[name] = job_data
        _save_cron_config(config)
        logger.info(f"Cron job '{name}' updated")
        return CronJobResponse(**job_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update cron job '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update cron job: {str(e)}")


@router.delete(
    "/crons/{name}",
    status_code=204,
    summary="Delete Cron Job",
    description="Remove a cron job from cron_config.json.",
)
async def delete_cron(name: str):
    """Delete a cron job."""
    try:
        config = _load_cron_config()
        jobs = config.get("cronJobs", {})

        if name not in jobs:
            raise HTTPException(status_code=404, detail=f"Cron job '{name}' not found")

        del jobs[name]
        _save_cron_config(config)
        logger.info(f"Cron job '{name}' deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cron job '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete cron job: {str(e)}")


@router.put(
    "/crons/{name}/toggle",
    response_model=CronJobResponse,
    summary="Toggle Cron Job",
    description="Enable or disable a cron job.",
)
async def toggle_cron(name: str, req: CronJobToggleRequest) -> CronJobResponse:
    """Toggle a cron job's enabled state."""
    try:
        config = _load_cron_config()
        jobs = config.get("cronJobs", {})

        if name not in jobs:
            raise HTTPException(status_code=404, detail=f"Cron job '{name}' not found")

        jobs[name]["enabled"] = req.enabled
        _save_cron_config(config)
        logger.info(f"Cron job '{name}' toggled to {req.enabled}")
        return CronJobResponse(**jobs[name])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle cron job '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle cron job: {str(e)}")
