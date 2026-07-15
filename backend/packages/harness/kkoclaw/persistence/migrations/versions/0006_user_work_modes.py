"""add user_work_modes table

Revision ID: 0006_user_work_modes
Revises: 0005_user_mcp_servers
Create Date: 2026-06-29 10:00:00.000000

Creates the ``user_work_modes`` table for per-user custom work mode
isolation.

Each row stores one custom work mode's configuration (id / name /
description / orchestration_hint / focus_areas) scoped to a single user.
Built-in modes (task / coding) are **not** stored here — they ship with
the system and are merged at resolve time.

Idempotent: OClaw provisions this table via ``Base.metadata.create_all`` at
engine init, so ``upgrade()`` guards on table existence and is a no-op on an
existing OClaw DB.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_user_work_modes"
down_revision = "0005_user_mcp_servers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "user_work_modes" in existing_tables:
        return
    op.create_table(
        "user_work_modes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("mode_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("orchestration_hint", sa.Text, nullable=False, server_default=""),
        sa.Column("focus_areas_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "mode_id", name="uq_user_work_mode_user_mode"),
    )


def downgrade() -> None:
    op.drop_table("user_work_modes")
