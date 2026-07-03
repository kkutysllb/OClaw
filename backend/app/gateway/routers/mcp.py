import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from kkoclaw.config.extensions_config import ExtensionsConfig, McpServerConfig, get_extensions_config, reload_extensions_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', 'http', or 'streamable-http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")
    is_system_default: bool = Field(default=False, description="Whether this server is a read-only system default (cannot be deleted)")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


_MASKED_VALUE = "***"


def _mask_server_config(server: McpServerConfigResponse) -> McpServerConfigResponse:
    """Return a copy of server config with sensitive fields masked.

    Masks env values, header values, and removes OAuth secrets so they
    are not exposed through the GET API endpoint.
    """
    masked_env = {k: _MASKED_VALUE for k in server.env}
    masked_headers = {k: _MASKED_VALUE for k in server.headers}
    masked_oauth = None
    if server.oauth is not None:
        masked_oauth = server.oauth.model_copy(
            update={
                "client_secret": None,
                "refresh_token": None,
            }
        )
    return server.model_copy(
        update={
            "env": masked_env,
            "headers": masked_headers,
            "oauth": masked_oauth,
        }
    )


def _get_repo():
    """Instantiate the UserMcpRepository from the global session factory."""
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.mcp_server.sql import UserMcpRepository

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Persistence engine not available")
    return UserMcpRepository(sf)


def _merge_preserving_secrets(
    incoming: McpServerConfigResponse,
    existing: McpServerConfigResponse,
) -> McpServerConfigResponse:
    """Merge incoming config with existing, preserving secrets masked by GET.

    When the frontend toggles ``enabled`` it round-trips the full config:
    GET (masked) → modify enabled → PUT (masked values sent back).
    This function ensures masked values (``***``) are replaced with the
    real secrets from the current on-disk config.

    ``***`` is only accepted for keys that already exist in *existing*.
    New keys must provide a real value.

    For OAuth secrets, ``None`` means "preserve the existing stored value"
    so masked GET responses can be safely round-tripped. To explicitly clear
    a stored secret, clients may send an empty string, which is converted
    to ``None`` before persisting.
    """
    merged_env = {}
    for k, v in incoming.env.items():
        if v == _MASKED_VALUE:
            if k in existing.env:
                merged_env[k] = existing.env[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set env key '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_env[k] = v

    merged_headers = {}
    for k, v in incoming.headers.items():
        if v == _MASKED_VALUE:
            if k in existing.headers:
                merged_headers[k] = existing.headers[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set header '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_headers[k] = v

    merged_oauth = incoming.oauth
    if incoming.oauth is not None and existing.oauth is not None:
        # None = preserve (masked round-trip), "" = explicitly clear, else = new value
        merged_client_secret = existing.oauth.client_secret if incoming.oauth.client_secret is None else (None if incoming.oauth.client_secret == "" else incoming.oauth.client_secret)
        merged_refresh_token = existing.oauth.refresh_token if incoming.oauth.refresh_token is None else (None if incoming.oauth.refresh_token == "" else incoming.oauth.refresh_token)
        merged_oauth = incoming.oauth.model_copy(
            update={
                "client_secret": merged_client_secret,
                "refresh_token": merged_refresh_token,
            }
        )
    return incoming.model_copy(
        update={
            "env": merged_env,
            "headers": merged_headers,
            "oauth": merged_oauth,
        }
    )


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the effective MCP server configurations for the current user.",
)
async def get_mcp_configuration() -> McpConfigResponse:
    """Get the effective MCP configuration for the authenticated user.

    Merges system-default servers (seeded from ``extensions_config.json``)
    with the user's own overrides and custom servers.

    Returns:
        The merged configuration with sensitive fields masked.

    For ``DEFAULT_USER_ID`` (unauthenticated CLI/studio) the global
    ``extensions_config.json`` is returned directly, preserving legacy
    behaviour.
    """
    from kkoclaw.config.user_mcp_config import resolve_user_mcp_config
    from kkoclaw.runtime.user_context import DEFAULT_USER_ID, get_effective_user_id

    user_id = get_effective_user_id()

    if user_id == DEFAULT_USER_ID:
        # Legacy: read global config directly.
        from kkoclaw.config.extensions_config import get_extensions_config

        config = get_extensions_config()
        servers = {
            name: _mask_server_config(McpServerConfigResponse(**server.model_dump(), is_system_default=True))
            for name, server in config.mcp_servers.items()
        }
        return McpConfigResponse(mcp_servers=servers)

    # Per-user: resolve from DB.
    config = await resolve_user_mcp_config(user_id)

    # Determine which servers are system-default by checking the DB.
    repo = _get_repo()
    db_rows = {row["server_name"]: row for row in await repo.list_for_user(user_id=user_id)}

    servers = {}
    for name, server in config.mcp_servers.items():
        db_row = db_rows.get(name)
        is_sys = db_row.get("is_system_default", False) if db_row else True
        servers[name] = _mask_server_config(
            McpServerConfigResponse(**server.model_dump(), is_system_default=is_sys)
        )
    return McpConfigResponse(mcp_servers=servers)


@router.put(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Update MCP Configuration",
    description="Update MCP server configurations for the current user.",
)
async def update_mcp_configuration(request: McpConfigUpdateRequest) -> McpConfigResponse:
    """Update the per-user MCP configuration.

    Behaviour:
      * **System-default servers** (``is_system_default=True``) are
        preserved — they cannot be deleted even if omitted from the
        request.  Their ``enabled`` flag and config can be updated.
      * **Custom servers** present in the request are upserted.
      * **Custom servers** absent from the request are deleted.
      * Masked values (``***``) are merged with existing DB secrets so
        the frontend round-trip (GET masked → edit → PUT) is safe.

    After the write, the user's config cache and tool cache are
    invalidated so the next agent run picks up the changes.
    """
    from kkoclaw.config.user_mcp_config import (
        invalidate_all_user_mcp_configs,
        invalidate_user_mcp_config,
        resolve_user_mcp_config,
    )
    from kkoclaw.mcp.cache import reset_mcp_tools_cache_for_user
    from kkoclaw.runtime.user_context import DEFAULT_USER_ID, get_effective_user_id

    user_id = get_effective_user_id()

    # ------------------------------------------------------------------
    # DEFAULT_USER_ID: write to the global extensions_config.json (legacy)
    # ------------------------------------------------------------------
    if user_id == DEFAULT_USER_ID:
        try:
            config_path = ExtensionsConfig.resolve_config_path()
            if config_path is None:
                config_path = Path.cwd().parent / "extensions_config.json"
                logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

            current_config = get_extensions_config()

            raw_servers: dict[str, dict] = {}
            if config_path is not None and config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    raw_data = json.load(f)
                raw_servers = raw_data.get("mcpServers", {})

            merged_servers: dict[str, McpServerConfigResponse] = {}
            for name, incoming in request.mcp_servers.items():
                raw_server = raw_servers.get(name)
                if raw_server is not None:
                    merged_servers[name] = _merge_preserving_secrets(
                        incoming,
                        McpServerConfigResponse(**raw_server),
                    )
                else:
                    merged_servers[name] = incoming

            current_config.mcp_servers = {
                name: McpServerConfig.model_validate(server.model_dump(exclude={"is_system_default"}))
                for name, server in merged_servers.items()
            }
            current_config.save(config_path)

            logger.info(f"MCP configuration updated and saved to: {config_path}")
            reloaded_config = reload_extensions_config()
            invalidate_all_user_mcp_configs()
            servers = {
                name: _mask_server_config(McpServerConfigResponse(**server.model_dump(), is_system_default=True))
                for name, server in reloaded_config.mcp_servers.items()
            }
            return McpConfigResponse(mcp_servers=servers)
        except Exception as e:
            logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")

    # ------------------------------------------------------------------
    # Authenticated user: write to per-user DB
    # ------------------------------------------------------------------
    try:
        repo = _get_repo()

        # Ensure system defaults are seeded so we know which servers
        # are protected from deletion.
        config = await resolve_user_mcp_config(user_id)
        existing_rows = {row["server_name"]: row for row in await repo.list_for_user(user_id=user_id)}

        incoming_names = set(request.mcp_servers.keys())

        # 1. Upsert each server from the request.
        for name, incoming in request.mcp_servers.items():
            existing = existing_rows.get(name)
            # Preserve existing secrets when masked values are sent back.
            if existing is not None:
                existing_config_dict = existing["config"]
                existing_response = McpServerConfigResponse(**existing_config_dict)
                merged = _merge_preserving_secrets(incoming, existing_response)
                config_dict = merged.model_dump(exclude={"is_system_default"})
            else:
                config_dict = incoming.model_dump(exclude={"is_system_default"})

            is_sys = existing.get("is_system_default", False) if existing else False
            await repo.upsert(
                server_name=name,
                config=config_dict,
                enabled=config_dict.get("enabled", True),
                is_system_default=is_sys,
                user_id=user_id,
            )

        # 2. Delete custom servers absent from the request.
        #    System-default servers are always preserved.
        for name, row in existing_rows.items():
            if name not in incoming_names and not row.get("is_system_default", False):
                await repo.delete(name, user_id=user_id)

        # 3. Invalidate caches.
        invalidate_user_mcp_config(user_id)
        reset_mcp_tools_cache_for_user(user_id)

        logger.info(f"MCP configuration updated for user '{user_id}'")

        # 4. Return the merged result.
        merged_config = await resolve_user_mcp_config(user_id)
        db_rows = {row["server_name"]: row for row in await repo.list_for_user(user_id=user_id)}
        servers = {}
        for name, server in merged_config.mcp_servers.items():
            db_row = db_rows.get(name)
            is_sys = db_row.get("is_system_default", False) if db_row else True
            servers[name] = _mask_server_config(
                McpServerConfigResponse(**server.model_dump(), is_system_default=is_sys)
            )
        return McpConfigResponse(mcp_servers=servers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")
