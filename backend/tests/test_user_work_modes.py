"""Tests for per-user custom work mode CRUD + config resolver merging.

Covers:
  1. UserWorkModeRepository — create/upsert, list, get, delete, builtin-id rejection
  2. User isolation — two users cannot see each other's custom modes
  3. resolve_user_work_modes — builtin + custom merge, DEFAULT_USER_ID shortcut
  4. _resolve_extensions_config_for_user — prompt injection resolves per-user config
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from kkoclaw.runtime.user_context import reset_current_user, set_current_user

USER_A = SimpleNamespace(id="user-a", email="a@test.local")
USER_B = SimpleNamespace(id="user-b", email="b@test.local")


async def _make_engines(tmp_path):
    """Initialize the shared engine against a per-test SQLite DB."""
    from kkoclaw.persistence.engine import close_engine, init_engine

    url = f"sqlite+aiosqlite:///{tmp_path / 'work_modes.db'}"
    await init_engine("sqlite", url=url, sqlite_dir=str(tmp_path))
    return close_engine


def _as_user(user):
    """Context manager that set/reset the user contextvar."""

    class _Ctx:
        def __enter__(self):
            self._token = set_current_user(user)
            return user

        def __exit__(self, *exc):
            reset_current_user(self._token)

    return _Ctx()


# ═══════════════════════════════════════════════════════════════════════════
# Repository CRUD
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_create_and_read(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        created = await repo.upsert(
            user_id="user-a",
            mode_id="research",
            name="Research",
            description="Deep research mode",
            orchestration_hint="Focus on analysis and fact-checking",
            focus_areas=["research", "documents"],
        )
        assert created["mode_id"] == "research"
        assert created["name"] == "Research"
        assert created["orchestration_hint"] == "Focus on analysis and fact-checking"
        assert created["focus_areas"] == ["research", "documents"]

        row = await repo.get_mode("research", user_id="user-a")
        assert row is not None
        assert row["name"] == "Research"
        assert row["focus_areas"] == ["research", "documents"]
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_update_via_upsert(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        await repo.upsert(
            user_id="user-a",
            mode_id="review",
            name="Review",
            description="Code review",
        )

        updated = await repo.upsert(
            user_id="user-a",
            mode_id="review",
            name="Code Review Pro",
            description="Enhanced code review",
            orchestration_hint="Pay attention to edge cases",
            focus_areas=["review", "security"],
        )
        assert updated["name"] == "Code Review Pro"
        assert updated["orchestration_hint"] == "Pay attention to edge cases"
        assert updated["focus_areas"] == ["review", "security"]
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_list_for_user(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        await repo.upsert(user_id="user-a", mode_id="research", name="Research")
        await repo.upsert(user_id="user-a", mode_id="review", name="Review")

        modes = await repo.list_for_user(user_id="user-a")
        assert len(modes) == 2
        ids = {m["mode_id"] for m in modes}
        assert ids == {"research", "review"}
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_delete(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        await repo.upsert(user_id="user-a", mode_id="research", name="Research")
        deleted = await repo.delete("research", user_id="user-a")
        assert deleted is True

        # Second delete returns False (already gone)
        deleted_again = await repo.delete("research", user_id="user-a")
        assert deleted_again is False

        row = await repo.get_mode("research", user_id="user-a")
        assert row is None
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_rejects_builtin_ids(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        with pytest.raises(ValueError, match="reserved for builtin"):
            await repo.upsert(user_id="user-a", mode_id="task", name="Task")

        with pytest.raises(ValueError, match="reserved for builtin"):
            await repo.upsert(user_id="user-a", mode_id="coding", name="Coding")

        with pytest.raises(ValueError, match="builtin mode"):
            await repo.delete("task", user_id="user-a")
    finally:
        await cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# Per-user isolation
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_user_isolation(tmp_path):
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        await repo.upsert(user_id="user-a", mode_id="research", name="Research A")
        await repo.upsert(user_id="user-b", mode_id="review", name="Review B")

        # User A sees only their mode
        modes_a = await repo.list_for_user(user_id="user-a")
        assert len(modes_a) == 1
        assert modes_a[0]["mode_id"] == "research"

        # User B sees only their mode
        modes_b = await repo.list_for_user(user_id="user-b")
        assert len(modes_b) == 1
        assert modes_b[0]["mode_id"] == "review"

        # Cross-user get returns None
        assert await repo.get_mode("research", user_id="user-b") is None
        assert await repo.get_mode("review", user_id="user-a") is None
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_repo_user_isolation_with_contextvar(tmp_path):
    """Verify that AUTO user_id resolution from contextvar works correctly."""
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        with _as_user(USER_A):
            await repo.upsert(mode_id="research", name="Research A")
            modes = await repo.list_for_user()
            assert len(modes) == 1
            assert modes[0]["mode_id"] == "research"

        with _as_user(USER_B):
            # User B sees nothing
            modes = await repo.list_for_user()
            assert len(modes) == 0

            # User B cannot read User A's mode
            row = await repo.get_mode("research")
            assert row is None
    finally:
        await cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# Config resolver — builtin + custom merge
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_resolve_merges_builtin_and_custom(tmp_path):
    from kkoclaw.config.user_work_modes_config import (
        invalidate_user_work_modes,
        resolve_user_work_modes,
    )
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())
        await repo.upsert(
            user_id="user-a",
            mode_id="research",
            name="Research",
            description="Deep research mode",
            orchestration_hint="Focus on thorough analysis",
            focus_areas=["research", "documents"],
        )
        invalidate_user_work_modes("user-a")

        config = await resolve_user_work_modes("user-a")
        mode_ids = set(config.modes.keys())

        # Must contain builtin presets + the custom mode
        assert "task" in mode_ids
        assert "coding" in mode_ids
        assert "research" in mode_ids

        # Custom mode carries the right metadata
        research = config.modes["research"]
        assert research.builtin is False
        assert research.name == "Research"
        assert research.orchestration_hint == "Focus on thorough analysis"
        assert research.focus_areas == ("research", "documents")
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_resolve_default_user_returns_only_builtins(tmp_path):
    from kkoclaw.config.user_work_modes_config import resolve_user_work_modes
    from kkoclaw.runtime.user_context import DEFAULT_USER_ID

    cleanup = await _make_engines(tmp_path)
    try:
        config = await resolve_user_work_modes(DEFAULT_USER_ID)
        mode_ids = set(config.modes.keys())
        # Must contain builtin presets only
        assert "task" in mode_ids
        assert "coding" in mode_ids
        # No custom modes for DEFAULT_USER_ID (no DB lookup)
        assert all(config.modes[mid].builtin for mid in mode_ids)
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_resolve_cache_invalidation(tmp_path):
    from kkoclaw.config.user_work_modes_config import (
        invalidate_user_work_modes,
        resolve_user_work_modes,
    )
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())

        # First resolve — empty (no custom modes)
        invalidate_user_work_modes("user-a")
        config1 = await resolve_user_work_modes("user-a")
        assert "research" not in config1.modes

        # Create a custom mode
        await repo.upsert(user_id="user-a", mode_id="research", name="Research")

        # Without invalidation, cache returns stale result
        config2 = await resolve_user_work_modes("user-a")
        assert "research" not in config2.modes

        # After invalidation, the new mode appears
        invalidate_user_work_modes("user-a")
        config3 = await resolve_user_work_modes("user-a")
        assert "research" in config3.modes
    finally:
        await cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# Prompt injection — _resolve_extensions_config_for_user
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_prompt_resolver_default_user(tmp_path):
    """For DEFAULT_USER_ID, _resolve_extensions_config_for_user returns
    the global config with builtin modes only (no DB lookup)."""
    from kkoclaw.agents.lead_agent.prompt import _resolve_extensions_config_for_user
    from kkoclaw.runtime.user_context import DEFAULT_USER_ID

    cleanup = await _make_engines(tmp_path)
    try:
        with _as_user(SimpleNamespace(id=DEFAULT_USER_ID, email="default")):
            cfg = _resolve_extensions_config_for_user()
            mode_ids = set(cfg.work_modes.modes.keys())
            assert "task" in mode_ids
            assert "coding" in mode_ids
    finally:
        await cleanup()


@pytest.mark.anyio
@pytest.mark.no_auto_user
async def test_prompt_resolver_authenticated_user(tmp_path):
    """For an authenticated user, _resolve_extensions_config_for_user
    returns a config whose work_modes includes the user's custom modes."""
    from kkoclaw.agents.lead_agent.prompt import _resolve_extensions_config_for_user
    from kkoclaw.config.user_work_modes_config import invalidate_user_work_modes
    from kkoclaw.persistence.engine import get_session_factory
    from kkoclaw.persistence.work_mode import UserWorkModeRepository

    cleanup = await _make_engines(tmp_path)
    try:
        repo = UserWorkModeRepository(get_session_factory())
        await repo.upsert(
            user_id="user-a",
            mode_id="research",
            name="Research",
            orchestration_hint="Analyze deeply",
            focus_areas=["research"],
        )
        invalidate_user_work_modes("user-a")

        with _as_user(USER_A):
            cfg = _resolve_extensions_config_for_user()
            mode_ids = set(cfg.work_modes.modes.keys())
            # Builtin + custom
            assert "task" in mode_ids
            assert "coding" in mode_ids
            assert "research" in mode_ids

            # The custom mode's orchestration_hint is available
            research = cfg.work_modes.modes["research"]
            assert research.orchestration_hint == "Analyze deeply"
    finally:
        await cleanup()
