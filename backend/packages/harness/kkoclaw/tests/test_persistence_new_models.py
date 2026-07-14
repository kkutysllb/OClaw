"""Ported upstream persistence models import + register with Base.metadata.

These three model packages are NEW to OClaw (ported from upstream deerflow).
OClaw builds tables via ``Base.metadata.create_all`` (engine.py), so each ORM
model module MUST be imported somewhere loaded at DB-init time or its table is
silently skipped. The aggregation point is ``kkoclaw.persistence.models``.
Importing the Row classes below (via the model modules) is what registers them.
"""
from kkoclaw.persistence.base import Base
from kkoclaw.persistence.channel_connections.model import (
    ChannelConnectionRow,
    ChannelConversationRow,
    ChannelCredentialRow,
    ChannelOAuthStateRow,
)
from kkoclaw.persistence.scheduled_task_runs.model import ScheduledTaskRunRow
from kkoclaw.persistence.scheduled_tasks.model import ScheduledTaskRow


def test_models_register_with_metadata():
    """The new tables must be in Base.metadata so create_all picks them up."""
    table_names = set(Base.metadata.tables.keys())
    # channel_connections package (4 tables)
    assert "channel_connections" in table_names
    assert "channel_credentials" in table_names
    assert "channel_oauth_states" in table_names
    assert "channel_conversations" in table_names
    # scheduled_tasks package (1 table)
    assert "scheduled_tasks" in table_names
    # scheduled_task_runs package (1 table)
    assert "scheduled_task_runs" in table_names


def test_models_inherit_from_base():
    """Sanity: each new ORM row class is mapped on the shared declarative Base."""
    for cls in (
        ChannelConnectionRow,
        ChannelCredentialRow,
        ChannelOAuthStateRow,
        ChannelConversationRow,
        ScheduledTaskRow,
        ScheduledTaskRunRow,
    ):
        assert cls.__tablename__ in Base.metadata.tables
