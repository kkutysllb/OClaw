"""Per-user custom work-mode configuration resolution.

Merges the builtin work-mode presets (task / coding, shipped via
:func:`kkoclaw.config.extensions_config._default_builtin_work_modes`)
with per-user custom modes stored in the ``user_work_modes`` database
table, producing a :class:`~kkoclaw.config.extensions_config.WorkModesConfig`
that reflects exactly what the requesting user should see.

Resolution model (builtin + per-user custom):

  1. The builtin modes (task / coding) are **always** present for every
     user — they ship with the system and cannot be deleted.
  2. A user's custom modes are loaded from ``user_work_modes`` and
     appended on top. Custom mode ids must not collide with builtin ids.
  3. The resolved config is cached in-process keyed by ``user_id``.
     Call :func:`invalidate_user_work_modes` after any write.

This module mirrors the architecture of
:mod:`kkoclaw.config.user_mcp_config` but is intentionally simpler:
builtin modes are not seeded into the DB (they live in code), so there
is no seed step — only a merge.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from kkoclaw.config.extensions_config import (
    DEFAULT_WORK_MODE_ID,
    WorkModeConfig,
    WorkModesConfig,
    _default_builtin_work_modes,
)
from kkoclaw.runtime.user_context import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process cache: user_id -> WorkModesConfig
# ---------------------------------------------------------------------------

_user_work_modes_cache: dict[str, WorkModesConfig] = {}
_cache_lock = asyncio.Lock()


def invalidate_user_work_modes(user_id: str) -> None:
    """Drop the cached work-modes config for *user_id*.

    Must be called after any write to ``user_work_modes`` for that user.
    """
    _user_work_modes_cache.pop(user_id, None)


def invalidate_all_user_work_modes() -> None:
    """Drop every cached user work-modes config."""
    _user_work_modes_cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _build_repo():
    """Instantiate the repository, raising a clear error if DB is down."""
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode.sql import UserWorkModeRepository

    sf = get_session_factory()
    if sf is None:
        raise RuntimeError(
            "Persistence engine not initialised — cannot resolve per-user work modes. "
            "Ensure init_engine_from_config() has been called."
        )
    return UserWorkModeRepository(sf)


def _builtin_modes() -> dict[str, WorkModeConfig]:
    """Return a fresh copy of the builtin modes dict (task / coding)."""
    return dict(_default_builtin_work_modes().modes)


def _row_to_mode_config(row: dict[str, Any]) -> WorkModeConfig:
    """Convert a repository row dict to a :class:`WorkModeConfig`."""
    return WorkModeConfig(
        id=row["mode_id"],
        name=row.get("name", row["mode_id"]),
        description=row.get("description", ""),
        builtin=False,
        editable=True,
        default_skill_ids=(),
        lead_agent_name="",  # custom modes use the default lead agent
        orchestration_hint=row.get("orchestration_hint", ""),
        focus_areas=tuple(row.get("focus_areas", []) or []),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def resolve_user_work_modes(user_id: str) -> WorkModesConfig:
    """Return the effective :class:`WorkModesConfig` for *user_id*.

    The result merges:
      - Builtin modes (task / coding) — always present.
      - The user's custom modes from ``user_work_modes`` (enabled ones only).

    The result is cached. Call :func:`invalidate_user_work_modes` after
    writes.

    For ``DEFAULT_USER_ID`` (unauthenticated CLI / tests / studio) the
    builtin presets are returned directly with no DB lookup — preserving
    legacy behaviour.
    """
    if user_id == DEFAULT_USER_ID:
        # Legacy / unauthenticated path: builtin modes only.
        return _default_builtin_work_modes()

    # Fast path — no lock needed for a dict read.
    cached = _user_work_modes_cache.get(user_id)
    if cached is not None:
        return cached

    async with _cache_lock:
        # Double-checked locking.
        cached = _user_work_modes_cache.get(user_id)
        if cached is not None:
            return cached

        modes = _builtin_modes()
        try:
            repo = await _build_repo()
            rows = await repo.list_for_user(user_id=user_id)
            for row in rows:
                if not row.get("enabled", True):
                    continue
                mode_id = row["mode_id"]
                if mode_id in modes:
                    # Defensive: should never happen (repo rejects builtin ids),
                    # but skip rather than crash if a stale row exists.
                    logger.warning(
                        "Custom work mode '%s' for user '%s' collides with a builtin id — skipping",
                        mode_id,
                        user_id,
                    )
                    continue
                modes[mode_id] = _row_to_mode_config(row)
        except Exception:
            logger.exception(
                "Failed to load custom work modes for user '%s' — falling back to builtin only",
                user_id,
            )

        result = WorkModesConfig(
            default_mode_id=DEFAULT_WORK_MODE_ID,
            modes=modes,
        )
        _user_work_modes_cache[user_id] = result
        return result


def resolve_user_work_modes_sync(user_id: str) -> WorkModesConfig:
    """Synchronous wrapper for use inside LangGraph nodes / prompt builders.

    Checks the cache first. On miss, runs the async resolution in a
    background thread (same pattern as
    :func:`kkoclaw.config.user_mcp_config.resolve_user_mcp_config_sync`).
    """
    if user_id == DEFAULT_USER_ID:
        return _default_builtin_work_modes()

    cached = _user_work_modes_cache.get(user_id)
    if cached is not None:
        return cached

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, resolve_user_work_modes(user_id))
                return future.result()
        else:
            return loop.run_until_complete(resolve_user_work_modes(user_id))
    except RuntimeError:
        return asyncio.run(resolve_user_work_modes(user_id))


async def get_user_custom_mode_ids(user_id: str) -> set[str]:
    """Return the set of custom mode ids a user has (for collision checks)."""
    config = await resolve_user_work_modes(user_id)
    return {mid for mid, m in config.modes.items() if not m.builtin}
