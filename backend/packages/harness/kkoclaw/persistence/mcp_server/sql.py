"""SQLAlchemy-backed per-user MCP server configuration storage.

Each method acquires its own short-lived session, mirroring
:class:`~kkoclaw.persistence.feedback.sql.FeedbackRepository`.

The repository operates on *raw* ``config_json`` strings (the full
``McpServerConfig`` dict serialised as JSON) so that the SQL layer has no
hard dependency on the Pydantic model.  Conversion to/from
:class:`~kkoclaw.config.extensions_config.McpServerConfig` is the caller's
responsibility — this keeps the persistence layer lightweight and testable.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kkoclaw.persistence.mcp_server.model import UserMcpServerRow
from kkoclaw.runtime.user_context import AUTO, _AutoSentinel, resolve_user_id


def _row_to_dict(row: UserMcpServerRow) -> dict[str, Any]:
    """Convert an ORM row to a plain dict, deserialising ``config_json``."""
    config: dict[str, Any] = {}
    if row.config_json:
        try:
            config = json.loads(row.config_json)
        except (json.JSONDecodeError, TypeError):
            config = {}
    return {
        "server_name": row.server_name,
        "config": config,
        "enabled": row.enabled,
        "is_system_default": row.is_system_default,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class UserMcpRepository:
    """CRUD repository for per-user MCP server configurations."""

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
        """Return all MCP server rows belonging to *user_id*."""
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.list_for_user")
        stmt = select(UserMcpServerRow).where(UserMcpServerRow.user_id == resolved)
        stmt = stmt.order_by(UserMcpServerRow.created_at.asc())
        async with self._sf() as session:
            result = await session.execute(stmt)
            return [_row_to_dict(r) for r in result.scalars()]

    async def get_server(
        self,
        server_name: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, Any] | None:
        """Return a single server row, or ``None`` if not found."""
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.get_server")
        stmt = select(UserMcpServerRow).where(
            UserMcpServerRow.user_id == resolved,
            UserMcpServerRow.server_name == server_name,
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
        server_name: str,
        config: dict[str, Any],
        enabled: bool = True,
        is_system_default: bool = False,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, Any]:
        """Create or update a single server row.

        If a row with ``(user_id, server_name)`` already exists it is
        updated in place; otherwise a new row is inserted.
        """
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.upsert")
        config_json = json.dumps(config, ensure_ascii=False)
        now = datetime.now(UTC)

        async with self._sf() as session:
            stmt = select(UserMcpServerRow).where(
                UserMcpServerRow.user_id == resolved,
                UserMcpServerRow.server_name == server_name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is not None:
                row.config_json = config_json
                row.enabled = enabled
                # Preserve existing is_system_default flag on update —
                # a user toggling a system-default server keeps the flag
                # so it remains protected from deletion.
                row.is_system_default = row.is_system_default or is_system_default
                row.updated_at = now
            else:
                row = UserMcpServerRow(
                    id=str(uuid.uuid4()),
                    user_id=resolved,
                    server_name=server_name,
                    config_json=config_json,
                    enabled=enabled,
                    is_system_default=is_system_default,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

            await session.commit()
            await session.refresh(row)
            return _row_to_dict(row)

    async def set_enabled(
        self,
        server_name: str,
        enabled: bool,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> bool:
        """Toggle ``enabled`` for a server. Returns ``True`` if updated."""
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.set_enabled")
        async with self._sf() as session:
            stmt = select(UserMcpServerRow).where(
                UserMcpServerRow.user_id == resolved,
                UserMcpServerRow.server_name == server_name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False
            row.enabled = enabled
            row.updated_at = datetime.now(UTC)
            await session.commit()
            return True

    async def delete(
        self,
        server_name: str,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> bool:
        """Delete a server row.

        Returns ``False`` (without raising) if the server does not exist
        or is marked ``is_system_default=True`` — system defaults are
        protected from deletion.
        """
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.delete")
        async with self._sf() as session:
            stmt = select(UserMcpServerRow).where(
                UserMcpServerRow.user_id == resolved,
                UserMcpServerRow.server_name == server_name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False
            if row.is_system_default:
                return False
            await session.delete(row)
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # System-default seeding
    # ------------------------------------------------------------------

    async def seed_system_defaults(
        self,
        global_servers: dict[str, dict[str, Any]],
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> int:
        """Insert system-default servers for a user, skipping existing names.

        ``global_servers`` is the ``mcpServers`` dict from the global
        ``extensions_config.json`` — ``{server_name: config_dict}``.

        Servers whose ``(user_id, server_name)`` already exist in the DB
        are left untouched so that user modifications are preserved.

        Returns the number of rows actually inserted.
        """
        resolved = resolve_user_id(user_id, method_name="UserMcpRepository.seed_system_defaults")
        if not global_servers:
            return 0

        async with self._sf() as session:
            # Fetch existing server names for this user in one query.
            existing_names: set[str] = set()
            stmt = select(UserMcpServerRow.server_name).where(
                UserMcpServerRow.user_id == resolved
            )
            result = await session.execute(stmt)
            for (name,) in result:
                existing_names.add(name)

            now = datetime.now(UTC)
            inserted = 0
            for server_name, config in global_servers.items():
                if server_name in existing_names:
                    continue
                row = UserMcpServerRow(
                    id=str(uuid.uuid4()),
                    user_id=resolved,
                    server_name=server_name,
                    config_json=json.dumps(config, ensure_ascii=False),
                    enabled=config.get("enabled", True),
                    is_system_default=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                inserted += 1

            if inserted:
                await session.commit()
            return inserted

    # ------------------------------------------------------------------
    # Merged view (system defaults + user overrides + custom)
    # ------------------------------------------------------------------

    async def get_merged_servers(
        self,
        *,
        user_id: str | None | _AutoSentinel = AUTO,
    ) -> dict[str, dict[str, Any]]:
        """Return the effective MCP server config for a user.

        The returned dict has the same shape as the ``mcpServers`` section
        of ``extensions_config.json`` — ``{server_name: {enabled, type, ...}}``.

        Resolution:
          1. All rows for *user_id* are loaded from the DB.
          2. Each row's ``config_json`` is deserialised and merged with the
             row's ``enabled`` flag (the DB-level flag wins).
        """
        rows = await self.list_for_user(user_id=user_id)
        merged: dict[str, dict[str, Any]] = {}
        for row in rows:
            config = dict(row["config"])
            config["enabled"] = row["enabled"]
            merged[row["server_name"]] = config
        return merged
