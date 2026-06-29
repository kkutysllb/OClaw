"""SQLAlchemy-backed per-user custom work mode storage.

Each method acquires its own short-lived session, mirroring
:class:`~kkoclaw.persistence.mcp_server.sql.UserMcpRepository`.

The repository operates on plain dicts (with ``focus_areas`` as a list)
so the SQL layer has no hard dependency on the Pydantic
:class:`~kkoclaw.config.extensions_config.WorkModeConfig` model.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kkoclaw.persistence.work_mode.model import UserWorkModeRow
from kkoclaw.runtime.user_context import AUTO, _AutoSentinel, resolve_user_id

#: Mode ids that cannot be used for custom modes — they are reserved for
#: the builtin presets shipped with the system. Attempting to create a
#: custom mode with one of these ids raises ``ValueError`` from the router.
BUILTIN_MODE_IDS: frozenset[str] = frozenset({"task", "coding", "core"})


def _row_to_dict(row: UserWorkModeRow) -> dict[str, Any]:
    """Convert an ORM row to a plain dict, deserialising ``focus_areas_json``."""
    focus_areas: list[str] = []
    if row.focus_areas_json:
        try:
            parsed = json.loads(row.focus_areas_json)
            if isinstance(parsed, list):
                focus_areas = [str(x) for x in parsed]
        except (json.JSONDecodeError, TypeError):
            focus_areas = []
    return {
        "mode_id": row.mode_id,
        "name": row.name,
        "description": row.description or "",
        "orchestration_hint": row.orchestration_hint or "",
        "focus_areas": focus_areas,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class UserWorkModeRepository:
    """CRUD repository for per-user custom work modes."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_for_user(
        self,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> list[dict[str, Any]]:
        """Return all custom work mode rows belonging to *user_id*."""
        resolved = resolve_user_id(user_id, method_name="UserWorkModeRepository.list_for_user")
        stmt = select(UserWorkModeRow).where(UserWorkModeRow.user_id == resolved)
        stmt = stmt.order_by(UserWorkModeRow.created_at.asc())
        async with self._sf() as session:
            result = await session.execute(stmt)
            return [_row_to_dict(r) for r in result.scalars()]

    async def get_mode(
        self,
        mode_id: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, Any] | None:
        """Return a single work mode row, or ``None`` if not found."""
        resolved = resolve_user_id(user_id, method_name="UserWorkModeRepository.get_mode")
        stmt = select(UserWorkModeRow).where(
            UserWorkModeRow.user_id == resolved,
            UserWorkModeRow.mode_id == mode_id,
        )
        async with self._sf() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return _row_to_dict(row) if row is not None else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert(
        self,
        *,
        mode_id: str,
        name: str,
        description: str = "",
        orchestration_hint: str = "",
        focus_areas: list[str] | None = None,
        enabled: bool = True,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, Any]:
        """Create or update a single custom work mode row.

        Raises ``ValueError`` if *mode_id* collides with a builtin id
        (``task`` / ``coding`` / ``core``).
        """
        if mode_id in BUILTIN_MODE_IDS:
            raise ValueError(
                f"Mode id '{mode_id}' is reserved for builtin modes and cannot be used for a custom mode."
            )
        resolved = resolve_user_id(user_id, method_name="UserWorkModeRepository.upsert")
        focus_areas = focus_areas or []
        focus_areas_json = json.dumps(focus_areas, ensure_ascii=False)
        now = datetime.now(UTC)

        async with self._sf() as session:
            stmt = select(UserWorkModeRow).where(
                UserWorkModeRow.user_id == resolved,
                UserWorkModeRow.mode_id == mode_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is not None:
                row.name = name
                row.description = description
                row.orchestration_hint = orchestration_hint
                row.focus_areas_json = focus_areas_json
                row.enabled = enabled
                row.updated_at = now
            else:
                row = UserWorkModeRow(
                    id=str(uuid.uuid4()),
                    user_id=resolved,
                    mode_id=mode_id,
                    name=name,
                    description=description,
                    orchestration_hint=orchestration_hint,
                    focus_areas_json=focus_areas_json,
                    enabled=enabled,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

            await session.commit()
            await session.refresh(row)
            return _row_to_dict(row)

    async def delete(
        self,
        mode_id: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> bool:
        """Delete a custom work mode row.

        Returns ``False`` (without raising) if the mode does not exist.
        Builtin ids are rejected with ``ValueError`` — they can never be
        deleted via this table.
        """
        if mode_id in BUILTIN_MODE_IDS:
            raise ValueError(
                f"Mode id '{mode_id}' is a builtin mode and cannot be deleted."
            )
        resolved = resolve_user_id(user_id, method_name="UserWorkModeRepository.delete")
        async with self._sf() as session:
            stmt = select(UserWorkModeRow).where(
                UserWorkModeRow.user_id == resolved,
                UserWorkModeRow.mode_id == mode_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True
