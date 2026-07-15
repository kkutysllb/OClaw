"""add icon column to user_work_modes

Revision ID: 0007_work_mode_icon
Revises: 0006_user_work_modes
Create Date: 2026-07-05 19:30:00.000000

Adds the ``icon`` column to ``user_work_modes`` so custom work modes can
carry a Lucide icon name (or emoji) used by the frontend sidebar entry.
Built-in modes are unaffected — their icons are resolved from a hard-coded
map in the router.

Idempotent: OClaw's ORM model already declares ``icon``, so
``Base.metadata.create_all`` provisions the column at engine init. This
``upgrade()`` guards on column existence and is a no-op on an existing OClaw DB.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_work_mode_icon"
down_revision = "0006_user_work_modes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "user_work_modes" not in insp.get_table_names():
        return
    if "icon" in {c["name"] for c in insp.get_columns("user_work_modes")}:
        return
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
