import asyncio
import json
import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.gateway.deps import get_config
from app.gateway.path_utils import resolve_thread_artifact_path
from kkoclaw.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from kkoclaw.config.app_config import AppConfig
from kkoclaw.config.extensions_config import ExtensionsConfig, SkillStateConfig, get_extensions_config, reload_extensions_config
from kkoclaw.skills import Skill
from kkoclaw.skills.frontmatter import inject_work_modes_frontmatter
from kkoclaw.skills.installer import SkillAlreadyExistsError, SkillSecurityScanError
from kkoclaw.skills.security_scanner import scan_skill_content
from kkoclaw.skills.storage import get_or_new_skill_storage
from kkoclaw.skills.storage.skill_storage import SkillStorage
from kkoclaw.skills.types import SKILL_MD_FILE, SkillCategory
from kkoclaw.skills.work_modes import assert_skill_can_be_disabled, invalidate_builtin_skills_cache

logger = logging.getLogger(__name__)

#: Maximum upload size for the wizard install-upload / support-files endpoints.
#: Mirrors the per-file cap of the thread upload endpoint (50 MiB default),
#: but we read it lazily from config so deployments can override.
_DEFAULT_UPLOAD_MAX_BYTES = 50 * 1024 * 1024

router = APIRouter(prefix="/api", tags=["skills"])


class SkillResponse(BaseModel):
    """Response model for skill information."""

    name: str = Field(..., description="Name of the skill")
    description: str = Field(..., description="Description of what the skill does")
    license: str | None = Field(None, description="License information")
    category: SkillCategory = Field(..., description="Category of the skill (public or custom)")
    enabled: bool = Field(default=True, description="Whether this skill is enabled")
    work_modes: list[str] = Field(default_factory=list, description="Work mode ids this skill is bound to (e.g. ['task', 'coding'])")


class SkillsListResponse(BaseModel):
    """Response model for listing all skills."""

    skills: list[SkillResponse]


class SkillUpdateRequest(BaseModel):
    """Request model for updating a skill."""

    enabled: bool = Field(..., description="Whether to enable or disable the skill")


class SkillInstallRequest(BaseModel):
    """Request model for installing a skill from a .skill file."""

    thread_id: str = Field(..., description="The thread ID where the .skill file is located")
    path: str = Field(..., description="Real host path to the .skill file (e.g., the thread outputs directory + /my-skill.skill)")
    work_modes: list[str] | None = Field(None, description="Optional work mode ids to bind. If omitted and the SKILL.md has no work_modes frontmatter, defaults to ['task'].")


class SkillInstallResponse(BaseModel):
    """Response model for skill installation."""

    success: bool = Field(..., description="Whether the installation was successful")
    skill_name: str = Field(..., description="Name of the installed skill")
    message: str = Field(..., description="Installation result message")


class CustomSkillContentResponse(SkillResponse):
    content: str = Field(..., description="Raw SKILL.md content")


class CustomSkillUpdateRequest(BaseModel):
    content: str = Field(..., description="Replacement SKILL.md content")


class CustomSkillCreateRequest(BaseModel):
    """Request model for creating a custom skill from raw SKILL.md content.

    This endpoint lets the frontend wizard create a skill directly via REST,
    bypassing the Agent. It is NOT gated by ``skill_evolution.enabled``
    because it is an explicit user action (not autonomous agent authoring).
    """

    name: str = Field(..., description="Skill name (hyphen-case; will be normalised and validated).")
    description: str = Field(..., max_length=1024, description="Short human-readable description shown in the skill list.")
    content: str = Field(..., description="Full SKILL.md body (frontmatter + markdown). work_modes will be injected automatically if absent.")
    work_modes: list[str] = Field(default_factory=lambda: ["task"], description="Work mode ids to bind (e.g. ['task', 'coding']).")


class WorkModesUpdateRequest(BaseModel):
    """Request model for updating a custom skill's work mode bindings."""

    work_modes: list[str] = Field(..., description="New work mode ids to bind this skill to (e.g. ['task', 'coding'])")


class CustomSkillHistoryResponse(BaseModel):
    history: list[dict]


class SkillRollbackRequest(BaseModel):
    history_index: int = Field(default=-1, description="History entry index to restore from, defaulting to the latest change.")


def _skill_to_response(skill: Skill) -> SkillResponse:
    """Convert a Skill object to a SkillResponse."""
    return SkillResponse(
        name=skill.name,
        description=skill.description,
        license=skill.license,
        category=skill.category,
        enabled=skill.enabled,
        work_modes=list(skill.work_modes),
    )


@router.get(
    "/skills",
    response_model=SkillsListResponse,
    summary="List All Skills",
    description="Retrieve a list of all available skills from both public and custom directories.",
)
async def list_skills(config: AppConfig = Depends(get_config)) -> SkillsListResponse:
    try:
        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        return SkillsListResponse(skills=[_skill_to_response(skill) for skill in skills])
    except Exception as e:
        logger.error(f"Failed to load skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load skills: {str(e)}")


@router.post(
    "/skills/install",
    response_model=SkillInstallResponse,
    summary="Install Skill",
    description="Install a skill from a .skill file (ZIP archive) located in the thread's user-data directory.",
)
async def install_skill(request: SkillInstallRequest, config: AppConfig = Depends(get_config)) -> SkillInstallResponse:
    try:
        skill_file_path = resolve_thread_artifact_path(request.thread_id, request.path)
        result = await get_or_new_skill_storage(app_config=config).ainstall_skill_from_archive(skill_file_path, work_modes=request.work_modes)
        await refresh_skills_system_prompt_cache_async()
        return SkillInstallResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SkillAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install skill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")


@router.post(
    "/skills/install-upload",
    response_model=SkillInstallResponse,
    summary="Install Skill From Upload",
    description=(
        "Install a skill from a .skill file (ZIP archive) uploaded directly "
        "via multipart/form-data. This endpoint powers the create-skill "
        "wizard's 'install from package' flow and does NOT require a thread "
        "context (unlike ``POST /skills/install`` which reads from a thread's "
        "uploads directory). The archive is unpacked, validated, scanned, "
        "and atomically installed via ``ainstall_skill_from_archive``."
    ),
)
async def install_skill_from_upload(
    file: UploadFile = File(..., description=".skill ZIP archive"),
    work_modes: str | None = Form(
        None, description='JSON-encoded work mode list, e.g. ["task","coding"]. Defaults to ["task"] when omitted or the archive has no work_modes frontmatter.'
    ),
    config: AppConfig = Depends(get_config),
) -> SkillInstallResponse:
    # 1. Validate filename suffix.
    filename = file.filename or ""
    if not filename.lower().endswith(".skill"):
        raise HTTPException(status_code=400, detail="Uploaded file must have a .skill extension.")

    # 2. Parse work_modes (JSON string → list[str] | None).
    parsed_work_modes: list[str] | None = None
    if work_modes:
        try:
            decoded = json.loads(work_modes)
            if isinstance(decoded, list) and all(isinstance(x, str) for x in decoded):
                parsed_work_modes = decoded
            else:
                raise HTTPException(status_code=400, detail="work_modes must be a JSON array of strings.")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="work_modes must be valid JSON.")

    # 3. Read the upload into a temp file. We cap size defensively using the
    #    uploads config; ainstall_skill_from_archive itself also enforces a
    #    512MB zip-bomb limit during extraction.
    max_bytes = _DEFAULT_UPLOAD_MAX_BYTES
    try:
        uploads_cfg = getattr(config, "uploads", None)
        configured = getattr(uploads_cfg, "max_file_size", None) if uploads_cfg else None
        if isinstance(configured, int) and configured > 0:
            max_bytes = configured
    except Exception:
        pass

    tmp = tempfile.NamedTemporaryFile(suffix=".skill", delete=False)
    try:
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                tmp.close()
                os.unlink(tmp.name)
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded .skill file exceeds the {max_bytes}-byte limit.",
                )
            tmp.write(chunk)
        tmp.flush()
        tmp.close()

        # 4. Install via the shared archive installer.
        result = await get_or_new_skill_storage(app_config=config).ainstall_skill_from_archive(
            tmp.name, work_modes=parsed_work_modes
        )
        await refresh_skills_system_prompt_cache_async()
        return SkillInstallResponse(**result)
    except SkillAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (SkillSecurityScanError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to install uploaded skill %s: %s", filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@router.get("/skills/custom", response_model=SkillsListResponse, summary="List Custom Skills")
async def list_custom_skills(config: AppConfig = Depends(get_config)) -> SkillsListResponse:
    try:
        skills = [skill for skill in get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False) if skill.category == SkillCategory.CUSTOM]
        return SkillsListResponse(skills=[_skill_to_response(skill) for skill in skills])
    except Exception as e:
        logger.error("Failed to list custom skills: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list custom skills: {str(e)}")


@router.post(
    "/skills/custom",
    response_model=CustomSkillContentResponse,
    summary="Create Custom Skill",
    description=(
        "Create a new custom skill from raw SKILL.md content. This endpoint "
        "powers the frontend skill-creation wizard and bypasses the Agent. "
        "It is NOT gated by ``skill_evolution.enabled`` because it is an "
        "explicit user action. The flow mirrors the Agent ``skill_manage`` "
        "create action: name normalisation → duplicate check (custom + "
        "builtin) → work_modes frontmatter injection → markdown validation "
        "→ security scan (fail-closed) → atomic write → history record."
    ),
)
async def create_custom_skill(
    request: CustomSkillCreateRequest, config: AppConfig = Depends(get_config)
) -> CustomSkillContentResponse:
    try:
        storage = get_or_new_skill_storage(app_config=config)
        # 1. Normalise + validate the skill name (hyphen-case rules).
        normalised_name = SkillStorage.validate_skill_name(request.name)
        # 2. Reject duplicates — both custom (would clobber) and builtin
        #    (shadowing a builtin name is confusing and forbidden by the
        #    Agent tool too).
        if await asyncio.to_thread(storage.custom_skill_exists, normalised_name):
            raise HTTPException(
                status_code=409,
                detail=f"Custom skill '{normalised_name}' already exists. Use PUT /api/skills/custom/{normalised_name} to edit it.",
            )
        if await asyncio.to_thread(storage.public_skill_exists, normalised_name):
            raise HTTPException(
                status_code=409,
                detail=f"'{normalised_name}' is a built-in skill name. Choose a different name.",
            )
        # 3. Inject work_modes frontmatter so the skill is bound to the
        #    chosen work modes (idempotent if the caller already included it).
        content = inject_work_modes_frontmatter(request.content, request.work_modes)
        # 4. Validate the markdown: frontmatter must have name + description,
        #    and the frontmatter name must match the request name.
        storage.validate_skill_markdown_content(normalised_name, content)
        # 5. Security scan (fail-closed: an unavailable scanner blocks).
        scan = await scan_skill_content(
            content,
            executable=False,
            location=f"{normalised_name}/{SKILL_MD_FILE}",
            app_config=config,
        )
        if scan.decision == "block":
            raise HTTPException(
                status_code=400,
                detail=f"Security scan blocked the skill creation: {scan.reason}",
            )
        # 6. Atomic write + history record (mirrors skill_manage_tool create).
        storage.write_custom_skill(normalised_name, SKILL_MD_FILE, content)
        storage.append_history(
            normalised_name,
            {
                "action": "create",
                "author": "human",
                "thread_id": None,
                "file_path": SKILL_MD_FILE,
                "prev_content": None,
                "new_content": content,
                "scanner": {"decision": scan.decision, "reason": scan.reason},
            },
        )
        await refresh_skills_system_prompt_cache_async()
        return await get_custom_skill(normalised_name, config)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create custom skill %s: %s", request.name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create custom skill: {str(e)}")


@router.get("/skills/custom/{skill_name}", response_model=CustomSkillContentResponse, summary="Get Custom Skill Content")
async def get_custom_skill(skill_name: str, config: AppConfig = Depends(get_config)) -> CustomSkillContentResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name and s.category == SkillCategory.CUSTOM), None)
        if skill is None:
            raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
        return CustomSkillContentResponse(**_skill_to_response(skill).model_dump(), content=get_or_new_skill_storage(app_config=config).read_custom_skill(skill_name))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get custom skill: {str(e)}")


@router.put("/skills/custom/{skill_name}", response_model=CustomSkillContentResponse, summary="Edit Custom Skill")
async def update_custom_skill(skill_name: str, request: CustomSkillUpdateRequest, config: AppConfig = Depends(get_config)) -> CustomSkillContentResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        storage = get_or_new_skill_storage(app_config=config)
        storage.ensure_custom_skill_is_editable(skill_name)
        storage.validate_skill_markdown_content(skill_name, request.content)
        scan = await scan_skill_content(request.content, executable=False, location=f"{skill_name}/{SKILL_MD_FILE}", app_config=config)
        if scan.decision == "block":
            raise HTTPException(status_code=400, detail=f"Security scan blocked the edit: {scan.reason}")
        prev_content = storage.read_custom_skill(skill_name)
        storage.write_custom_skill(skill_name, SKILL_MD_FILE, request.content)
        storage.append_history(
            skill_name,
            {
                "action": "human_edit",
                "author": "human",
                "thread_id": None,
                "file_path": SKILL_MD_FILE,
                "prev_content": prev_content,
                "new_content": request.content,
                "scanner": {"decision": scan.decision, "reason": scan.reason},
            },
        )
        await refresh_skills_system_prompt_cache_async()
        return await get_custom_skill(skill_name, config)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update custom skill: {str(e)}")


@router.patch(
    "/skills/custom/{skill_name}/work-modes",
    response_model=CustomSkillContentResponse,
    summary="Update Custom Skill Work Modes",
    description="Update the work mode bindings for a custom skill by rewriting the work_modes field in the SKILL.md frontmatter.",
)
async def update_custom_skill_work_modes(
    skill_name: str, request: WorkModesUpdateRequest, config: AppConfig = Depends(get_config)
) -> CustomSkillContentResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        storage = get_or_new_skill_storage(app_config=config)
        storage.ensure_custom_skill_is_editable(skill_name)
        prev_content = storage.read_custom_skill(skill_name)
        new_content = inject_work_modes_frontmatter(prev_content, request.work_modes)
        storage.validate_skill_markdown_content(skill_name, new_content)
        storage.write_custom_skill(skill_name, SKILL_MD_FILE, new_content)
        storage.append_history(
            skill_name,
            {
                "action": "update_work_modes",
                "author": "human",
                "thread_id": None,
                "file_path": SKILL_MD_FILE,
                "prev_content": prev_content,
                "new_content": new_content,
                "scanner": {"decision": "allow", "reason": "Work modes update."},
            },
        )
        invalidate_builtin_skills_cache()
        await refresh_skills_system_prompt_cache_async()
        return await get_custom_skill(skill_name, config)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update work modes for %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update work modes: {str(e)}")


@router.post(
    "/skills/custom/{skill_name}/support-files",
    response_model=CustomSkillContentResponse,
    summary="Upload Support Files To Skill",
    description=(
        "Upload scripts / templates / references / assets into an existing "
        "custom skill's support subdirectory. Powers the create-skill "
        "wizard's 'from scripts' flow. Each file is scanned: scripts/ "
        "requires an explicit 'allow' decision (warn is rejected), other "
        "text subdirs accept 'warn', binary files (images etc.) are written "
        "without scanning. Writes are atomic per file and a history record "
        "is appended."
    ),
)
async def upload_support_files(
    skill_name: str,
    files: list[UploadFile] = File(..., description="One or more support files."),
    subdir: str = Form("scripts", description="Target subdirectory under the skill: references | templates | scripts | assets | models | adapters."),
    config: AppConfig = Depends(get_config),
) -> CustomSkillContentResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        storage = get_or_new_skill_storage(app_config=config)
        storage.ensure_custom_skill_is_editable(skill_name)

        # Validate the target subdirectory against the allow-list. Kept in
        # sync with SkillStorage.ensure_safe_support_path (the storage layer
        # re-validates on write, so a mismatch would surface as a 500 —
        # this check gives the client a clean 400 instead).
        _allowed_subdirs = {"references", "templates", "scripts", "assets", "models", "adapters"}
        if subdir not in _allowed_subdirs:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subdir '{subdir}'. Must be one of: {', '.join(sorted(_allowed_subdirs))}.",
            )

        # scripts/ files must pass an executable scan; other text subdirs
        # (references/templates) use a non-executable scan; binary assets
        # are written without scanning (mirrors installer behaviour).
        executable = subdir == "scripts"
        written: list[str] = []

        for upload in files:
            raw_filename = upload.filename or "unnamed"
            # Strip any path components from the client-supplied filename so
            # it lands safely inside the chosen subdir.
            safe_name = os.path.basename(raw_filename)
            if not safe_name or safe_name.startswith("."):
                raise HTTPException(status_code=400, detail=f"Invalid filename: {raw_filename!r}")
            relative_path = f"{subdir}/{safe_name}"

            # Validate the resolved path stays inside the skill dir (defence
            # in depth — basename already stripped traversal, but the storage
            # helper also rejects '..').
            storage.ensure_safe_support_path(skill_name, relative_path)

            content_bytes = await upload.read()
            if len(content_bytes) > _DEFAULT_UPLOAD_MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {safe_name} exceeds the {_DEFAULT_UPLOAD_MAX_BYTES}-byte limit.",
                )

            # Decide whether to scan. We attempt to decode as UTF-8; binary
            # files (UnicodeDecodeError) are written without LLM scanning,
            # matching the installer's behaviour for assets/.
            try:
                content_text = content_bytes.decode("utf-8")
                should_scan = True
            except UnicodeDecodeError:
                should_scan = False
                content_text = None

            if should_scan and content_text is not None:
                scan = await scan_skill_content(
                    content_text,
                    executable=executable,
                    location=f"{skill_name}/{relative_path}",
                    app_config=config,
                )
                if scan.decision == "block":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Security scan blocked {relative_path}: {scan.reason}",
                    )
                # scripts/ uploads via the wizard (support-files endpoint)
                # accept both "allow" and "warn" — unlike the .skill installer
                # (which requires explicit "allow" for executables because the
                # archive may come from an untrusted third-party marketplace),
                # this endpoint is driven by an explicit user action: the user
                # picked the file from their own machine. A "warn" typically
                # flags borderline-but-legitimate patterns like external API
                # references (e.g. a script that calls a documented API with
                # an env-var key), which is exactly what the user intends to
                # upload. Only "block" (clear malicious content) is rejected.
                scan_meta = {"decision": scan.decision, "reason": scan.reason}
                storage.write_custom_skill(skill_name, relative_path, content_text)
            else:
                # Binary file: write via the resolved support path because
                # write_custom_skill only accepts str. We use the same
                # ensure_safe_support_path validator so traversal protection
                # still applies, then atomic-write the raw bytes ourselves.
                scan_meta = {"decision": "allow", "reason": "Binary file; scan skipped."}
                target = storage.ensure_safe_support_path(skill_name, relative_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp_bin = tempfile.NamedTemporaryFile(
                    dir=str(target.parent), delete=False, prefix=".upload-"
                )
                try:
                    tmp_bin.write(content_bytes)
                    tmp_bin.close()
                    os.replace(tmp_bin.name, target)
                finally:
                    try:
                        if os.path.exists(tmp_bin.name):
                            os.unlink(tmp_bin.name)
                    except OSError:
                        pass

            storage.append_history(
                skill_name,
                {
                    "action": "upload_file",
                    "author": "human",
                    "thread_id": None,
                    "file_path": relative_path,
                    "prev_content": None,
                    "new_content": content_text if content_text is not None else f"<binary {len(content_bytes)} bytes>",
                    "scanner": scan_meta,
                },
            )
            written.append(relative_path)

        await refresh_skills_system_prompt_cache_async()
        return await get_custom_skill(skill_name, config)
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (SkillSecurityScanError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to upload support files to %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload support files: {str(e)}")


@router.delete("/skills/custom/{skill_name}", summary="Delete Custom Skill")
async def delete_custom_skill(skill_name: str, config: AppConfig = Depends(get_config)) -> dict[str, bool]:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        storage = get_or_new_skill_storage(app_config=config)
        storage.delete_custom_skill(
            skill_name,
            history_meta={
                "action": "human_delete",
                "author": "human",
                "thread_id": None,
                "file_path": SKILL_MD_FILE,
                "prev_content": None,
                "new_content": None,
                "scanner": {"decision": "allow", "reason": "Deletion requested."},
            },
        )
        await refresh_skills_system_prompt_cache_async()
        return {"success": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete custom skill: {str(e)}")


@router.get("/skills/custom/{skill_name}/history", response_model=CustomSkillHistoryResponse, summary="Get Custom Skill History")
async def get_custom_skill_history(skill_name: str, config: AppConfig = Depends(get_config)) -> CustomSkillHistoryResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        storage = get_or_new_skill_storage(app_config=config)
        if not storage.custom_skill_exists(skill_name) and not storage.get_skill_history_file(skill_name).exists():
            raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
        return CustomSkillHistoryResponse(history=storage.read_history(skill_name))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to read history for %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read history: {str(e)}")


@router.post("/skills/custom/{skill_name}/rollback", response_model=CustomSkillContentResponse, summary="Rollback Custom Skill")
async def rollback_custom_skill(skill_name: str, request: SkillRollbackRequest, config: AppConfig = Depends(get_config)) -> CustomSkillContentResponse:
    try:
        storage = get_or_new_skill_storage(app_config=config)
        if not storage.custom_skill_exists(skill_name) and not storage.get_skill_history_file(skill_name).exists():
            raise HTTPException(status_code=404, detail=f"Custom skill '{skill_name}' not found")
        history = storage.read_history(skill_name)
        if not history:
            raise HTTPException(status_code=400, detail=f"Custom skill '{skill_name}' has no history")
        record = history[request.history_index]
        target_content = record.get("prev_content")
        if target_content is None:
            raise HTTPException(status_code=400, detail="Selected history entry has no previous content to roll back to")
        storage.validate_skill_markdown_content(skill_name, target_content)
        scan = await scan_skill_content(target_content, executable=False, location=f"{skill_name}/{SKILL_MD_FILE}", app_config=config)
        skill_file = storage.get_custom_skill_file(skill_name)
        current_content = skill_file.read_text(encoding="utf-8") if skill_file.exists() else None
        history_entry = {
            "action": "rollback",
            "author": "human",
            "thread_id": None,
            "file_path": SKILL_MD_FILE,
            "prev_content": current_content,
            "new_content": target_content,
            "rollback_from_ts": record.get("ts"),
            "scanner": {"decision": scan.decision, "reason": scan.reason},
        }
        if scan.decision == "block":
            storage.append_history(skill_name, history_entry)
            raise HTTPException(status_code=400, detail=f"Rollback blocked by security scanner: {scan.reason}")
        storage.write_custom_skill(skill_name, SKILL_MD_FILE, target_content)
        storage.append_history(skill_name, history_entry)
        await refresh_skills_system_prompt_cache_async()
        return await get_custom_skill(skill_name, config)
    except HTTPException:
        raise
    except IndexError:
        raise HTTPException(status_code=400, detail="history_index is out of range")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to roll back custom skill %s: %s", skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to roll back custom skill: {str(e)}")


@router.get(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Get Skill Details",
    description="Retrieve detailed information about a specific skill by its name.",
)
async def get_skill(skill_name: str, config: AppConfig = Depends(get_config)) -> SkillResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return _skill_to_response(skill)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get skill: {str(e)}")


@router.put(
    "/skills/{skill_name}",
    response_model=SkillResponse,
    summary="Update Skill",
    description="Update a skill's enabled status by modifying the extensions_config.json file.",
)
async def update_skill(skill_name: str, request: SkillUpdateRequest, config: AppConfig = Depends(get_config)) -> SkillResponse:
    try:
        skill_name = skill_name.replace("\r\n", "").replace("\n", "")
        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        skill = next((s for s in skills if s.name == skill_name), None)

        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # Locked core skills cannot be disabled — they protect the agent's
        # self-bootstrap / skill-discovery / skill-creation loop.
        if not request.enabled:
            assert_skill_can_be_disabled(skill_name)

        extensions_config = get_extensions_config()
        extensions_config.skills[skill_name] = SkillStateConfig(enabled=request.enabled)

        # Use save() for complete serialization — the old manual dict
        # construction silently dropped work_modes, locked_skill_ids, and
        # mode_skill_overrides on every write.
        saved_path = extensions_config.save()
        logger.info(f"Skills configuration updated and saved to: {saved_path}")
        reload_extensions_config()
        await refresh_skills_system_prompt_cache_async()

        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        updated_skill = next((s for s in skills if s.name == skill_name), None)

        if updated_skill is None:
            raise HTTPException(status_code=500, detail=f"Failed to reload skill '{skill_name}' after update")

        logger.info(f"Skill '{skill_name}' enabled status updated to {request.enabled}")
        return _skill_to_response(updated_skill)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {str(e)}")
