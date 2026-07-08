"""Middleware that injects the real working-directory paths into the agent context.

Phase 3 removed the /mnt/user-data virtual path layer. Agents now operate on
real host absolute paths, but the static system prompt cannot embed per-thread
paths (it is built without thread context). This middleware prepends a
``<working_directory>`` info block containing the real uploads/workspace/outputs
paths to the last human message so the model knows exactly where to read and
write files.
"""

import logging

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class WorkspacePathMiddlewareState(AgentState):
    """State schema for the workspace path middleware (no extra fields)."""


class WorkspacePathMiddleware(AgentMiddleware[WorkspacePathMiddlewareState]):
    """Inject real working-directory paths before agent execution.

    Prepends a ``<working_directory>`` block listing the absolute host paths of
    the thread's uploads/workspace/outputs directories to the last human message.
    """

    state_schema = WorkspacePathMiddlewareState

    def _build_working_directory_block(self, thread_data: dict) -> str | None:
        """Build the <working_directory> info block, or None if no paths are set."""
        workspace = thread_data.get("workspace_path")
        uploads = thread_data.get("uploads_path")
        outputs = thread_data.get("outputs_path")
        if not any((workspace, uploads, outputs)):
            return None

        lines = ["<working_directory>", "Your working directories (real absolute paths):"]
        if uploads:
            lines.append(f"- uploads (user-uploaded files): {uploads}")
        if workspace:
            lines.append(f"- workspace (working directory for temporary files): {workspace}")
        if outputs:
            lines.append(f"- outputs (final deliverables go here): {outputs}")
        lines.append("Use these real absolute paths for read_file/write_file/bash/present_files.")
        lines.append("Prefer relative paths from the workspace (e.g. ../outputs/report.md) when it is the current directory.")
        lines.append("Do NOT use /mnt/user-data paths — they do not exist. Always use the real paths listed above.")
        lines.append("</working_directory>")
        return "\n".join(lines)

    def before_agent(self, state: WorkspacePathMiddlewareState, runtime: Runtime) -> dict | None:
        """Inject the working-directory info block before agent execution.

        The block is prepended to the last human message so it appears in the
        model's context window without polluting the persisted message content
        (the original content is preserved; the block is additive).
        """
        messages = list(state.get("messages", []))
        if not messages:
            return None

        last_message_index = len(messages) - 1
        last_message = messages[last_message_index]

        if not isinstance(last_message, HumanMessage):
            return None

        # thread_data is set into state by ThreadDataMiddleware (which runs
        # before this middleware). Read it from the state dict, not runtime.
        thread_data = state.get("thread_data")
        if not isinstance(thread_data, dict):
            return None

        wd_block = self._build_working_directory_block(thread_data)
        if wd_block is None:
            return None

        original_content = last_message.content
        if isinstance(original_content, str):
            updated_content = f"{wd_block}\n\n{original_content}"
        elif isinstance(original_content, list):
            wd_text_block = {"type": "text", "text": f"{wd_block}\n\n"}
            updated_content = [wd_text_block, *original_content]
        else:
            updated_content = original_content

        updated_message = HumanMessage(
            content=updated_content,
            id=last_message.id,
            name=last_message.name,
            additional_kwargs=last_message.additional_kwargs,
        )

        messages[last_message_index] = updated_message
        return {"messages": messages}
