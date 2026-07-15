"""DynamicContextMiddleware injects reminders as SystemMessage (upstream parity)."""
from langchain_core.messages import SystemMessage

from kkoclaw.agents.middlewares.dynamic_context_middleware import (
    is_dynamic_context_reminder,
)


def test_reminder_detector_accepts_system_message():
    """Upstream coalescing expects reminders to be SystemMessages."""
    reminder = SystemMessage(
        content="<current_date>2026-07-15</current_date>",
        additional_kwargs={"dynamic_context_reminder": True},
    )
    assert is_dynamic_context_reminder(reminder) is True
