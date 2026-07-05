"""add icon column to user_work_modes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-05 19:30:00.000000

Adds the ``icon`` column to ``user_work_modes`` so custom work modes can
carry a Lucide icon name (or emoji) used by the frontend sidebar entry.
Built-in modes are unaffected — their icons are resolved from a hard-coded
map in the router.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_work_modes",
        sa.Column(
            "icon",
            sa.String(64),
            nullable=False,
            server_default="Bot",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_work_modes", "icon")
