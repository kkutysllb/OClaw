"""Shared path resolution for thread artifact paths.

Phase 3 removed the /mnt/user-data virtual path layer. Artifact paths are now
real host absolute paths; this module validates that a requested path resolves
to a location inside the thread's user-data root (workspace/uploads/outputs).

When the user selected a workspace directory via the WorkspaceSelector, the
agent's ``outputs_path`` is redirected to that directory (see
``ThreadDataMiddleware``). The async resolver reads ``thread_data`` from the
checkpointer so artifacts written into the user-selected directory can be
served too.
"""

from pathlib import Path

from fastapi import HTTPException

from kkoclaw.config.paths import get_paths
from kkoclaw.runtime.user_context import get_effective_user_id


def resolve_thread_artifact_path(thread_id: str, path: str) -> Path:
    """Resolve an artifact path to the actual filesystem path under thread user-data.

    Args:
        thread_id: The thread ID.
        path: Real host path (e.g. {base}/threads/{tid}/user-data/outputs/file.txt).

    Returns:
        The resolved filesystem path.

    Raises:
        HTTPException: If the path is invalid (400), outside the thread
            workspace (403), or contains a traversal attempt (403).
    """
    try:
        return get_paths().resolve_thread_artifact_path(thread_id, path, user_id=get_effective_user_id())
    except ValueError as e:
        status = 403 if "traversal" in str(e) or "outside" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e))


async def resolve_thread_artifact_path_async(thread_id: str, path: str, request) -> Path:
    """Resolve an artifact path, also accepting the thread's user-selected workspace.

    Reads ``thread_data`` from the latest checkpoint to learn the
    ``outputs_path`` / ``user_workspace_path`` that ``ThreadDataMiddleware``
    recorded for this thread. When the user selected a workspace directory,
    ``outputs_path`` is redirected there, so artifacts written into it must be
    servable — this passes those roots as ``extra_allowed_roots`` to
    :meth:`Paths.resolve_thread_artifact_path`.

    Falls back to the synchronous resolver (user-data root only) when the
    checkpoint or ``thread_data`` is unavailable, preserving prior behaviour.
    """
    extra_roots = await _load_thread_extra_allowed_roots(thread_id, request)
    try:
        return get_paths().resolve_thread_artifact_path(
            thread_id,
            path,
            user_id=get_effective_user_id(),
            extra_allowed_roots=extra_roots,
        )
    except ValueError as e:
        status = 403 if "traversal" in str(e) or "outside" in str(e) else 400
        raise HTTPException(status_code=status, detail=str(e))


async def _load_thread_extra_allowed_roots(thread_id: str, request) -> list[str]:
    """Return extra artifact-allowed roots from the thread's persisted state.

    Reads ``thread_data.outputs_path`` and ``thread_data.user_workspace_path``
    from the latest checkpoint. Both may point at a user-selected workspace
    when the user picked one via the WorkspaceSelector. Returns an empty list
    on any failure so callers fall back to the default user-data root check.
    """
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if checkpointer is None:
        return []
    try:
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
    except Exception:
        return []
    if checkpoint_tuple is None:
        return []
    checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}
    channel_values = checkpoint.get("channel_values", {}) or {}
    thread_data = channel_values.get("thread_data")
    if not isinstance(thread_data, dict):
        return []
    roots: list[str] = []
    for key in ("outputs_path", "user_workspace_path"):
        value = thread_data.get(key)
        if isinstance(value, str) and value:
            roots.append(value)
    return roots
