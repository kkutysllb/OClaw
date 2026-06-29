"""Unified database backend configuration.

Controls BOTH the LangGraph checkpointer and the KKOCLAW application
persistence layer (runs, threads metadata, users, etc.). The user
configures one backend; the system handles physical separation details.

SQLite mode: checkpointer and app share a single .db file
({sqlite_dir}/kkoclaw.db) with WAL journal mode enabled on every
connection. WAL allows concurrent readers and a single writer without
blocking, making a unified file safe for both workloads.  Writers
that contend for the lock wait via the default 5-second sqlite3
busy timeout rather than failing immediately.

Postgres mode: both use the same database URL but maintain independent
connection pools with different lifecycles.

Memory mode: checkpointer uses MemorySaver, app uses in-memory stores.
No database is initialized.

Sensitive values (postgres_url) should use $VAR syntax in config.yaml
to reference environment variables from .env:

    database:
      backend: postgres
      postgres_url: $DATABASE_URL

The $VAR resolution is handled by AppConfig.resolve_env_variables()
before this config is instantiated -- DatabaseConfig itself does not
need to do any environment variable processing.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from kkoclaw.config.runtime_paths import runtime_home


class DatabaseConfig(BaseModel):
    backend: Literal["memory", "sqlite", "postgres"] = Field(
        default="memory",
        description=("Storage backend for both checkpointer and application data. 'memory' for development (no persistence across restarts), 'sqlite' for single-node deployment, 'postgres' for production multi-node deployment."),
    )
    sqlite_dir: str = Field(
        default=".kkoclaw/data",
        description=("Directory for the SQLite database file. Both checkpointer and application data share {sqlite_dir}/kkoclaw.db."),
    )
    postgres_url: str = Field(
        default="",
        description=(
            "PostgreSQL connection URL, shared by checkpointer and app. "
            "Use $DATABASE_URL in config.yaml to reference .env. "
            "Example: postgresql://user:pass@host:5432/kkoclaw "
            "(the +asyncpg driver suffix is added automatically where needed)."
        ),
    )
    echo_sql: bool = Field(
        default=False,
        description="Echo all SQL statements to log (debug only).",
    )
    pool_size: int = Field(
        default=5,
        description="Connection pool size for the app ORM engine (postgres only).",
    )

    # -- Derived helpers (not user-configured) --

    @property
    def _resolved_sqlite_dir(self) -> str:
        """Resolve ``sqlite_dir`` to an absolute path.

        The relative-path fallback used to be CWD-relative (``Path(...).resolve()``),
        which dropped a hidden ``backend/.kkoclaw/data/`` directory into the
        working tree on every dev launch from the monorepo. We now anchor
        relative paths to :func:`runtime_home` (``~/.kkoclaw`` on web,
        ``~/.kkoclaw-desktop`` on desktop) so user data never lands inside
        the project tree. Absolute paths are honoured as-is.

        The legacy ``.kkoclaw/...`` prefix is stripped before joining so
        the historic config value ``.kkoclaw/data`` lands at
        ``<runtime_home>/data`` rather than ``<runtime_home>/.kkoclaw/data``
        (i.e. the old CWD-relative behaviour that produced the
        double-nested path). Other relative paths are preserved as-is.
        """
        raw = (self.sqlite_dir or "").strip()
        if not raw:
            return str(runtime_home() / "data")
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve())
        # Strip a leading ``.kkoclaw/`` (or bare ``.kkoclaw``) so historical
        # config values like ``.kkoclaw/data`` do not double-nest under
        # the runtime home. The runtime home is itself the ``.kkoclaw`` dir.
        stripped = re.sub(r"^\.kkoclaw(/|$)", "", raw)
        return str((runtime_home() / stripped).resolve())

    @property
    def sqlite_path(self) -> str:
        """Unified SQLite file path shared by checkpointer and app."""
        return os.path.join(self._resolved_sqlite_dir, "kkoclaw.db")

    # Backward-compatible aliases
    @property
    def checkpointer_sqlite_path(self) -> str:
        """SQLite file path for the LangGraph checkpointer (alias for sqlite_path)."""
        return self.sqlite_path

    @property
    def app_sqlite_path(self) -> str:
        """SQLite file path for application ORM data (alias for sqlite_path)."""
        return self.sqlite_path

    @property
    def app_sqlalchemy_url(self) -> str:
        """SQLAlchemy async URL for the application ORM engine."""
        if self.backend == "sqlite":
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        if self.backend == "postgres":
            url = self.postgres_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        raise ValueError(f"No SQLAlchemy URL for backend={self.backend!r}")
