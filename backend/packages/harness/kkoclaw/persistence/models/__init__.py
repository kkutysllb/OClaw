"""ORM model registration entry point.

Importing this module ensures all ORM models are registered with
``Base.metadata`` so Alembic autogenerate detects every table.

The actual ORM classes have moved to entity-specific subpackages:
- ``kkoclaw.persistence.thread_meta``
- ``kkoclaw.persistence.run``
- ``kkoclaw.persistence.feedback``
- ``kkoclaw.persistence.user``
- ``kkoclaw.persistence.channel_connections``
- ``kkoclaw.persistence.scheduled_tasks``
- ``kkoclaw.persistence.scheduled_task_runs``

``RunEventRow`` remains in ``kkoclaw.persistence.models.run_event`` because
its storage implementation lives in ``kkoclaw.runtime.events.store.db`` and
there is no matching entity directory.
"""

from kkoclaw.persistence.channel_connections.model import (
    ChannelConnectionRow,
    ChannelConversationRow,
    ChannelCredentialRow,
    ChannelOAuthStateRow,
)
from kkoclaw.persistence.feedback.model import FeedbackRow
from kkoclaw.persistence.mcp_server.model import UserMcpServerRow
from kkoclaw.persistence.models.run_event import RunEventRow
from kkoclaw.persistence.run.model import RunRow
from kkoclaw.persistence.scheduled_task_runs.model import ScheduledTaskRunRow
from kkoclaw.persistence.scheduled_tasks.model import ScheduledTaskRow
from kkoclaw.persistence.thread_meta.model import ThreadMetaRow
from kkoclaw.persistence.user.model import UserRow
from kkoclaw.persistence.work_mode.model import UserWorkModeRow

__all__ = [
    "ChannelConnectionRow",
    "ChannelConversationRow",
    "ChannelCredentialRow",
    "ChannelOAuthStateRow",
    "FeedbackRow",
    "RunEventRow",
    "RunRow",
    "ScheduledTaskRow",
    "ScheduledTaskRunRow",
    "ThreadMetaRow",
    "UserMcpServerRow",
    "UserRow",
    "UserWorkModeRow",
]
