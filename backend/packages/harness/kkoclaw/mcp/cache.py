"""Cache for MCP tools, keyed by user_id for per-user isolation.

The cache stores one tool-list per user. ``DEFAULT_USER_ID`` ("default")
preserves the legacy global-config behaviour for unauthenticated paths
(CLI, tests, migration scripts).

Cache invalidation happens in two ways:

1. **Explicit** – :func:`reset_mcp_tools_cache_for_user` (or
   :func:`reset_mcp_tools_cache` for all users) drops the cache after a
   user edits their config via the API.
2. **File-mtime** – when the global ``extensions_config.json`` changes,
   every user's cache is considered stale because system-default seeds
   may have changed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading

from langchain_core.tools import BaseTool

from kkoclaw.runtime.user_context import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

# Per-user caches (user_id → value)
_mcp_tools_cache: dict[str, list[BaseTool]] = {}
_cache_initialized: dict[str, bool] = {}
_config_mtime: dict[str, float | None] = {}

_global_config_mtime_last_seen: float | None = None

# threading.Lock (not asyncio.Lock) so it is safe to acquire from both
# async paths and sync/worker-thread paths — same pattern as session_pool.
_cache_guard = threading.Lock()


def _get_global_config_mtime() -> float | None:
    """Get the modification time of the global extensions config file."""
    from kkoclaw.config.extensions_config import ExtensionsConfig

    config_path = ExtensionsConfig.resolve_config_path()
    if config_path and config_path.exists():
        return os.path.getmtime(config_path)
    return None


def _is_global_config_stale() -> bool:
    """Check if the global config file changed since last check.

    When the global file changes we invalidate *every* user's cache because
    system-default seeds may differ.
    """
    global _global_config_mtime_last_seen

    current = _get_global_config_mtime()
    if _global_config_mtime_last_seen is None:
        _global_config_mtime_last_seen = current
        return False
    if current is not None and current > _global_config_mtime_last_seen:
        logger.info(
            "Global extensions_config.json modified (mtime: %s -> %s), invalidating all per-user MCP caches",
            _global_config_mtime_last_seen,
            current,
        )
        _global_config_mtime_last_seen = current
        return True
    return False


def _is_user_cache_stale(user_id: str) -> bool:
    """Check if a specific user's cache is stale."""
    if not _cache_initialized.get(user_id, False):
        return False  # Not initialised yet
    return _is_global_config_stale()


# ---------------------------------------------------------------------------
# Async initialisation (per user)
# ---------------------------------------------------------------------------


async def initialize_mcp_tools_for_user(
    user_id: str,
    extensions_config=None,
) -> list[BaseTool]:
    """Initialize and cache MCP tools for a specific user.

    Args:
        user_id: The user whose tools to load.
        extensions_config: The already-resolved ExtensionsConfig. When
            ``None`` the global file is read (legacy/DEFAULT_USER_ID path).
    """
    from kkoclaw.mcp.tools import get_mcp_tools

    logger.info("Initializing MCP tools for user '%s'...", user_id)
    tools = await get_mcp_tools(extensions_config=extensions_config)
    with _cache_guard:
        _mcp_tools_cache[user_id] = tools
        _cache_initialized[user_id] = True
        _config_mtime[user_id] = _get_global_config_mtime()
    logger.info(
        "MCP tools initialised for user '%s': %d tool(s) loaded",
        user_id,
        len(tools),
    )
    return tools


async def initialize_mcp_tools() -> list[BaseTool]:
    """Legacy alias — initialises for :data:`DEFAULT_USER_ID`."""
    return await initialize_mcp_tools_for_user(DEFAULT_USER_ID)


# ---------------------------------------------------------------------------
# Synchronous lazy access
# ---------------------------------------------------------------------------


def get_cached_mcp_tools_for_user(user_id: str, extensions_config=None) -> list[BaseTool]:
    """Get cached MCP tools for *user_id* with lazy initialisation.

    If the cache is stale (global config changed) it is reset and
    re-initialised.  The same thread-pool fallback as the legacy
    :func:`get_cached_mcp_tools` is used when an event loop is already
    running.
    """
    if _is_user_cache_stale(user_id):
        logger.info("MCP cache stale for user '%s', resetting...", user_id)
        reset_mcp_tools_cache_for_user(user_id)

    if not _cache_initialized.get(user_id, False):
        logger.info("MCP tools not initialised for user '%s', lazy init...", user_id)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        initialize_mcp_tools_for_user(user_id, extensions_config),
                    )
                    future.result()
            else:
                loop.run_until_complete(
                    initialize_mcp_tools_for_user(user_id, extensions_config)
                )
        except RuntimeError:
            try:
                asyncio.run(initialize_mcp_tools_for_user(user_id, extensions_config))
            except Exception:
                logger.exception("Failed to lazy-initialise MCP tools for user '%s'", user_id)
                return []
        except Exception:
            logger.exception("Failed to lazy-initialise MCP tools for user '%s'", user_id)
            return []

    return _mcp_tools_cache.get(user_id, [])


def get_cached_mcp_tools() -> list[BaseTool]:
    """Legacy entry point — uses :data:`DEFAULT_USER_ID`.

    Maintained for backward compatibility with code paths that don't have
    a user context (CLI, tests, LangGraph Studio).
    """
    return get_cached_mcp_tools_for_user(DEFAULT_USER_ID)


# ---------------------------------------------------------------------------
# Cache reset
# ---------------------------------------------------------------------------


def reset_mcp_tools_cache_for_user(user_id: str) -> None:
    """Reset the MCP tools cache for a single user."""
    with _cache_guard:
        _mcp_tools_cache.pop(user_id, None)
        _cache_initialized.pop(user_id, None)
        _config_mtime.pop(user_id, None)

    # Close pooled sessions for this user so they are recreated with the
    # (possibly updated) connection config.
    try:
        from kkoclaw.mcp.session_pool import get_session_pool

        pool = get_session_pool()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(pool.close_user(user_id), loop).result(timeout=5)
            else:
                loop.run_until_complete(pool.close_user(user_id))
        except RuntimeError:
            asyncio.run(pool.close_user(user_id))
    except Exception:
        logger.debug("Could not close MCP sessions for user '%s' on cache reset", user_id, exc_info=True)

    logger.info("MCP tools cache reset for user '%s'", user_id)


def reset_mcp_tools_cache() -> None:
    """Reset the MCP tools cache for **all** users."""
    with _cache_guard:
        user_ids = list(_cache_initialized.keys())
        for uid in user_ids:
            _mcp_tools_cache.pop(uid, None)
            _cache_initialized.pop(uid, None)
            _config_mtime.pop(uid, None)

    # Also tear down any sessions belonging to users we might have missed.
    try:
        from kkoclaw.mcp.session_pool import get_session_pool, reset_session_pool

        pool = get_session_pool()
        pool.close_all_sync()
        reset_session_pool()
    except Exception:
        logger.debug("Could not close MCP session pool on full cache reset", exc_info=True)

    logger.info("MCP tools cache reset (all users)")
