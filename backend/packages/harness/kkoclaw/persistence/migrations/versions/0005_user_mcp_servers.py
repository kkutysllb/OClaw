"""add user_mcp_servers table

Revision ID: 0005_user_mcp_servers
Revises: 0004_run_ownership
Create Date: 2026-06-28 13:40:00.000000

Creates the ``user_mcp_servers`` table for per-user MCP server isolation.

Each row stores one MCP server's full configuration (JSON) scoped to a
single user. ``is_system_default`` marks servers seeded from the global
``extensions_config.json`` template — these are protected from deletion.

Idempotent: OClaw provisions this table via ``Base.metadata.create_all`` at
engine init, so ``upgrade()`` guards on table existence and is a no-op on an
existing OClaw DB.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_user_mcp_servers"
down_revision = "0004_run_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "user_mcp_servers" in existing_tables:
        return
    op.create_table(
        "user_mcp_servers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("server_name", sa.String(128), nullable=False),
        sa.Column("config_json", sa.Text, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "is_system_default",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "server_name", name="uq_user_mcp_user_server"),
    )


def downgrade() -> None:
    op.drop_table("user_mcp_servers")
