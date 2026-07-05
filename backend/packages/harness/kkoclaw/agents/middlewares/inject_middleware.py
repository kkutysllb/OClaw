"""Middleware that injects pending user messages as supplement context mid-run.

When a user sends a new message via the "inject" API while a run is in progress,
the message is written to ThreadState.pending_messages (via agent.aupdate_state,
which does NOT interrupt the running worker). This middleware reads pending_messages
at each model call, wraps them as a single hide_from_ui HumanMessage containing
supplement context, appends it to the model's messages, and clears the queue.

Semantics:
- Does NOT interrupt the current subtask (aupdate_state only affects the next superstep).
- Guides the model to treat these as supplemental context, not a hard restart.
- The injected message is hidden from the UI (hide_from_ui=True) to avoid duplication
  with the frontend queue's "injected" status badge.
"""

import logging
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from kkoclaw.agents.middlewares.internal_messages import internal_human_message
from kkoclaw.agents.thread_state import ThreadState

logger = logging.getLogger(__name__)

# Cap to avoid token explosion if a user spams the inject button.
_MAX_PENDING = 10

_SUPPLEMENT_PREFIX = (
    "[用户补充信息 · 任务执行期间追加]\n"
    "以下是用户在当前任务执行期间补充的需求/说明，"
    "请在当前工作的后续步骤中适当考虑（无需从头重启，"
    "可在完成当前子任务后纳入规划）：\n\n"
)


class InjectMiddlewareState(ThreadState):
    """Reuse ThreadState so the pending_messages reducer annotation is preserved."""


class InjectMiddleware(AgentMiddleware[InjectMiddlewareState]):
    """Injects pending_messages as a single supplement-context HumanMessage before model calls.

    Reads state["pending_messages"] (written by the /inject route via aupdate_state),
    wraps non-empty entries into one hide_from_ui HumanMessage, appends to messages,
    and clears the queue. Returns None when there is nothing to inject.
    """

    state_schema = InjectMiddlewareState

    def _build_supplement_message(self, pending: list[dict]) -> HumanMessage | None:
        # Filter out empty/whitespace-only content
        valid = [m for m in pending if (m.get("content") or "").strip()]
        if not valid:
            return None
        # Cap at most recent _MAX_PENDING entries to avoid token bloat
        if len(valid) > _MAX_PENDING:
            valid = valid[-_MAX_PENDING:]
            logger.warning(
                "inject_middleware: %d pending messages capped to last %d",
                len(pending),
                _MAX_PENDING,
            )

        if len(valid) == 1:
            body = valid[0]["content"]
        else:
            body = "\n".join(f"{i + 1}. {m['content']}" for i, m in enumerate(valid))

        content = f"{_SUPPLEMENT_PREFIX}{body}"
        return internal_human_message(
            content=content,
            marker="pending_message_inject",
            name="pending_message",
        )

    def _inject(self, state: InjectMiddlewareState) -> dict | None:
        pending = state.get("pending_messages") or []
        if not pending:
            return None
        wrapped = self._build_supplement_message(pending)
        if wrapped is None:
            return None
        logger.debug(
            "inject_middleware: injecting %d pending message(s) as supplement context",
            len(pending),
        )
        return {
            "messages": [wrapped],
            "pending_messages": [],  # trigger reducer clear
        }

    @override
    def before_model(self, state: InjectMiddlewareState, runtime: Runtime) -> dict | None:
        return self._inject(state)

    @override
    async def abefore_model(self, state: InjectMiddlewareState, runtime: Runtime) -> dict | None:
        return self._inject(state)
