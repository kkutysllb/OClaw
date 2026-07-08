"""Shared path resolution for thread artifact paths.

Phase 3 removed the /mnt/user-data virtual path layer. Artifact paths are now
real host absolute paths; this module validates that a requested path resolves
to a location inside the thread's user-data root (workspace/uploads/outputs).
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
