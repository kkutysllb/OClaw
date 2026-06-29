"""Per-user MCP configuration resolution.

Merges the global ``extensions_config.json`` template with per-user
overrides stored in the ``user_mcp_servers`` database table, producing an
:class:`~kkoclaw.config.extensions_config.ExtensionsConfig` that reflects
exactly what the requesting user should see.

Resolution model (system-default + user-override):

  1. The global ``extensions_config.json`` defines the **system-default**
     servers. On a user's first access these are *seeded* into the DB with
     ``is_system_default=True``.
  2. From that point on the DB is the single source of truth for that user.
     The user may toggle ``enabled``, edit config (API key, URL …), or add
     their own custom servers.
  3. System-default servers **cannot be deleted** (the API rejects it);
     they can only be toggled off or reconfigured.

The resolved config is cached in-process keyed by ``user_id``. Call
:func:`invalidate_user_mcp_config` whenever the user's DB rows change.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from kkoclaw.config.extensions_config import ExtensionsConfig, McpServerConfig
from kkoclaw.runtime.user_context import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process cache: user_id -> ExtensionsConfig
# ---------------------------------------------------------------------------

_user_mcp_config_cache: dict[str, ExtensionsConfig] = {}
_cache_lock = asyncio.Lock()


def invalidate_user_mcp_config(user_id: str) -> None:
    """Drop the cached config for *user_id*.

    Must be called after any write to ``user_mcp_servers`` for that user.
    """
    _user_mcp_config_cache.pop(user_id, None)


def invalidate_all_user_mcp_configs() -> None:
    """Drop every cached user config (used on global config reload)."""
    _user_mcp_config_cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_global_mcp_servers_raw() -> dict[str, dict[str, Any]]:
    """Read the raw ``mcpServers`` dict from the global config file.

    Returns the *un-resolved* JSON (no ``$VAR`` substitution) so that
    seeded rows preserve environment-variable placeholders.
    """
    return _read_global_config().get("mcpServers", {})


def _get_global_extra_keys() -> dict[str, Any]:
    """Return top-level keys from the global config that should be inherited.

    Currently only ``mcpInterceptors`` is forwarded — it is a global
    concept applied to all MCP tool calls and is not per-user.
    """
    data = _read_global_config()
    return {k: v for k, v in data.items() if k not in ("mcpServers", "skills")}


def _read_global_config() -> dict[str, Any]:
    """Read and return the raw global extensions_config.json as a dict."""
    from kkoclaw.config.extensions_config import ExtensionsConfig as _EC

    path = _EC.resolve_config_path()
    if path is None or not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read global extensions config from %s: %s", path, exc)
        return {}


async def _build_repo():
    """Instantiate the repository, raising a clear error if DB is down."""
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.mcp_server.sql import UserMcpRepository

    sf = get_session_factory()
    if sf is None:
        raise RuntimeError(
            "Persistence engine not initialised — cannot resolve per-user MCP config. "
            "Ensure init_engine_from_config() has been called."
        )
    return UserMcpRepository(sf)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def resolve_user_mcp_config(user_id: str) -> ExtensionsConfig:
    """Return the effective :class:`ExtensionsConfig` for *user_id*.

    The result is cached. Call :func:`invalidate_user_mcp_config` after
    writes.

    Steps:
      1. Check in-process cache.
      2. Seed system-default servers from the global config if missing.
      3. Read all rows for the user, build ``mcpServers``.
      4. Resolve ``$ENV`` placeholders (same as ExtensionsConfig.from_file).
      5. Construct & cache the ExtensionsConfig.
    """
    # Fast path — no lock needed for a dict read.
    cached = _user_mcp_config_cache.get(user_id)
    if cached is not None:
        return cached

    async with _cache_lock:
        # Double-checked locking.
        cached = _user_mcp_config_cache.get(user_id)
        if cached is not None:
            return cached

        repo = await _build_repo()

        # 2. Seed system defaults (idempotent — skips existing names).
        global_raw = _get_global_mcp_servers_raw()
        if global_raw:
            inserted = await repo.seed_system_defaults(global_raw, user_id=user_id)
            if inserted:
                logger.info("Seeded %d system-default MCP servers for user '%s'", inserted, user_id)

        # 3. Merge: DB rows become the effective mcpServers dict.
        merged_servers_raw = await repo.get_merged_servers(user_id=user_id)

        # 4. Resolve $ENV placeholders so the runtime gets real values.
        config_data: dict[str, Any] = {"mcpServers": merged_servers_raw}
        # Inherit global extra keys (e.g. mcpInterceptors) — these are
        # cross-cutting and not per-user.
        config_data.update(_get_global_extra_keys())
        ExtensionsConfig.resolve_env_variables(config_data)

        # 5. Build ExtensionsConfig.
        try:
            extensions_config = ExtensionsConfig.model_validate(config_data)
        except Exception as exc:
            logger.error("Failed to build ExtensionsConfig for user '%s': %s", user_id, exc)
            extensions_config = ExtensionsConfig(mcp_servers={}, skills={})

        _user_mcp_config_cache[user_id] = extensions_config
        return extensions_config


def resolve_user_mcp_config_sync(user_id: str) -> ExtensionsConfig:
    """Synchronous wrapper for use inside LangGraph nodes.

    Checks the cache first. On miss, runs the async resolution in a
    background thread (same pattern as :func:`mcp.cache.get_cached_mcp_tools`).

    For ``DEFAULT_USER_ID`` (unauthenticated CLI/tests) this function is
    **not** called — callers should fall back to the global config directly.
    """
    cached = _user_mcp_config_cache.get(user_id)
    if cached is not None:
        return cached

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, resolve_user_mcp_config(user_id))
                return future.result()
        else:
            return loop.run_until_complete(resolve_user_mcp_config(user_id))
    except RuntimeError:
        return asyncio.run(resolve_user_mcp_config(user_id))


async def get_user_mcp_server_names(user_id: str) -> set[str]:
    """Return the set of server names a user has (for duplicate detection)."""
    config = await resolve_user_mcp_config(user_id)
    return set(config.mcp_servers.keys())
