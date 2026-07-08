"""Semantic code search tool for the Coding Agent.

Provides:
- ``search_semantic``: Find code by meaning, not by exact text.

Unlike ``search_code`` (regex pattern matching), this tool uses TF-IDF
vector space ranking to find files whose *content* is semantically
related to the query. This catches queries like::

    search_semantic("authentication and login flow")

which would match files containing ``oauth``, ``jwt``, ``session``,
``verify_password`` etc. — without requiring the exact words to appear.

Index caching
-------------
The TF-IDF index is built once per project and cached in-memory. It is
rebuilt only when the file tree changes (detected via file count or
mtime spot-checks). This makes repeated semantic searches near-instant.
"""

from __future__ import annotations

import logging
import os
import time

from langchain.tools import tool

from kkoclaw.coding_core.tfidf_engine import (
    SearchResult,
    TfidfIndex,
    _INDEX_CACHE,
    _MAX_INDEXED_FILES,
    _should_index,
)
from kkoclaw.sandbox.exceptions import SandboxError
from kkoclaw.sandbox.tools import (
    _sanitize_error,
    _resolve_local_read_path,
    ensure_sandbox_initialized,
    ensure_thread_directories_exist,
    get_thread_data,
    is_local_sandbox,
    mask_local_paths_in_output,
    validate_local_tool_path,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# Preview length per result (chars).
_PREVIEW_CHARS = 300
# Stale-check: if file count changes by more than this ratio, rebuild.
_STALE_FILE_RATIO = 0.15


def _project_root(runtime: Runtime) -> str:
    """Extract the project root from runtime context."""
    thread_data = get_thread_data(runtime)
    project_root = thread_data.get("project_root") if thread_data else None
    if project_root:
        return project_root
    if thread_data:
        workspace = thread_data.get("workspace_path")
        if workspace:
            return workspace
    return os.getcwd()


def _collect_source_files(
    sandbox: object,
    root: str,
) -> list[str]:
    """Glob all indexable source files under *root*."""
    all_files, _ = sandbox.glob(
        root, "**/*", include_dirs=False, max_results=_MAX_INDEXED_FILES * 3
    )
    return [fp for fp in all_files if _should_index(fp)]


def _index_signature(files: list[str]) -> dict[str, float]:
    """Quick staleness signature: file count + a sample of mtimes.

    We don't stat every file (too slow for large projects). Instead we
    sample ~20 files spread evenly across the list.
    """
    import json

    sig: dict[str, float] = {"_count": float(len(files))}
    if not files:
        return sig
    # Sample 20 files evenly
    step = max(1, len(files) // 20)
    for i in range(0, len(files), step):
        sig[files[i]] = float(os.path.getmtime(files[i])) if os.path.exists(files[i]) else 0.0
    return sig


def _index_is_stale(
    cached_sig: dict[str, float],
    current_sig: dict[str, float],
) -> bool:
    """Check if the cached index is stale enough to warrant rebuild."""
    cached_count = cached_sig.get("_count", 0)
    current_count = current_sig.get("_count", 0)
    if current_count == 0:
        return True
    ratio = abs(current_count - cached_count) / current_count
    if ratio > _STALE_FILE_RATIO:
        return True
    # Check sampled mtimes
    for key, mtime in current_sig.items():
        if key == "_count":
            continue
        if cached_sig.get(key, 0) != mtime:
            return True
    return False


def _build_index(
    sandbox: object,
    files: list[str],
) -> TfidfIndex:
    """Build a TF-IDF index over *files* using *sandbox* to read content."""
    index = TfidfIndex()
    for fp in files:
        try:
            content = sandbox.read_file(fp)
            if content:
                index.add(fp, content)
        except Exception:
            continue  # skip unreadable files
    index.finalize()
    return index


def _get_or_build_index(
    runtime: Runtime,
    sandbox: object,
    project_root: str,
) -> tuple[TfidfIndex, list[str]]:
    """Return the cached index for *project_root*, building if needed.

    Returns ``(index, source_files)``.
    """
    files = _collect_source_files(sandbox, project_root)
    current_sig = _index_signature(files)

    cached = _INDEX_CACHE.get(project_root)
    if cached is not None:
        cached_index, cached_sig = cached
        if not _index_is_stale(cached_sig, current_sig):
            return cached_index, files

    # Build new index
    logger.info(
        "Building semantic index for %s (%d files)",
        project_root,
        len(files),
    )
    start = time.monotonic()
    index = _build_index(sandbox, files)
    elapsed = time.monotonic() - start
    logger.info(
        "Semantic index built in %.2fs (%d docs)",
        elapsed,
        index.size,
    )
    _INDEX_CACHE[project_root] = (index, current_sig)
    return index, files


def _build_preview(
    sandbox: object,
    file_path: str,
    query_terms: list[str],
) -> str:
    """Extract a short preview from *file_path* highlighting query terms."""
    try:
        content = sandbox.read_file(file_path) or ""
    except Exception:
        return ""

    lines = content.splitlines()
    if not lines:
        return ""

    # Find the line with the most query-term hits
    best_line = 0
    best_score = 0
    query_lower = [t.lower() for t in query_terms]
    for i, line in enumerate(lines[:500]):  # only scan first 500 lines
        line_lower = line.lower()
        score = sum(1 for term in query_lower if term in line_lower)
        if score > best_score:
            best_score = score
            best_line = i

    # Return 3 lines centered on best_line
    start = max(0, best_line - 1)
    end = min(len(lines), best_line + 2)
    preview_lines = []
    for j in range(start, end):
        marker = ">>" if j == best_line else "  "
        preview_lines.append(f"{marker} L{j+1}: {lines[j][:150]}")
    return "\n".join(preview_lines)


@tool("search_semantic", parse_docstring=True)
def search_semantic_tool(
    runtime: Runtime,
    query: str,
    path: str | None = None,
    max_results: int = 10,
) -> str:
    """Find code by meaning using semantic (TF-IDF) search.

    Unlike ``search_code`` (exact regex matching), this tool ranks files
    by semantic similarity to your query. It finds files that *talk
    about* the same concept even if they use different words.

    Example queries::

        search_semantic("authentication and login flow")
        search_semantic("database connection pool management")
        search_semantic("retry logic with exponential backoff")
        search_semantic("用户认证和权限控制")

    The index is built once per project and cached, so subsequent
    searches are near-instant.

    Args:
        query: Natural language description of what you're looking for.
        path: Root directory to search under. Defaults to the project root.
        max_results: Maximum results to return. Default 10.
    """
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)

        project_root = path or _project_root(runtime)
        thread_data = None
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            if path:
                validate_local_tool_path(path, thread_data, read_only=True)
                project_root = _resolve_local_read_path(path, thread_data)
            else:
                project_root = _resolve_local_read_path(project_root, thread_data)

        # Build or retrieve cached index
        index, source_files = _get_or_build_index(runtime, sandbox, project_root)
        if index.size == 0:
            return (
                f"No indexable source files found under {project_root}. "
                f"Try a different path."
            )

        # Search
        results = index.search(query, top_k=max_results, min_score=0.01)
        if not results:
            return (
                f"No semantic matches for '{query}' "
                f"(searched {index.size} files in {project_root})."
            )

        # Format output with previews
        from kkoclaw.coding_core.tfidf_engine import tokenize as _tokenize

        query_terms = _tokenize(query)
        lines = [
            f"Found {len(results)} semantic match(es) for '{query}' "
            f"(score range {results[-1].score:.2f}–{results[0].score:.2f}):\n"
        ]
        for result in results:
            display_path = result.doc_id
            if thread_data is not None:
                display_path = mask_local_paths_in_output(result.doc_id, thread_data)
            lines.append(f"  [{result.score:.3f}]  {display_path}")
            preview = _build_preview(sandbox, result.doc_id, query_terms)
            if preview:
                if thread_data is not None:
                    preview = mask_local_paths_in_output(preview, thread_data)
                lines.append(f"    {preview}")
            lines.append("")

        return "\n".join(lines)
    except SandboxError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except Exception as e:
        return f"Error: Unexpected error in semantic search: {_sanitize_error(e, runtime)}"


__all__ = ["search_semantic_tool"]
