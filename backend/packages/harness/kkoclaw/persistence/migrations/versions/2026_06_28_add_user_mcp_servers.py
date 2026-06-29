"""add user_mcp_servers table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-28 13:40:00.000000

Creates the ``user_mcp_servers`` table for per-user MCP server isolation.

Each row stores one MCP server's full configuration (JSON) scoped to a
single user. ``is_system_default`` marks servers seeded from the global
``extensions_config.json`` template — these are protected from deletion.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
