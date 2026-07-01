"""Post-edit diagnostic tools for the Coding Agent.

Provides:
- ``get_diagnostics``: Run linter / type-checker on a single file and return
  structured diagnostic results. Optimized for fast post-edit verification.
- ``run_file_diagnostics``: Internal helper used by
  :class:`PostEditVerifyMiddleware` to auto-diagnose edited files and feed
  errors back to the model — rather than merely *reminding* it to check.

Unlike ``run_linter`` (whole-project), these target a single file so the
feedback loop after an edit is sub-second for most projects.
"""

from __future__ import annotations

import json
import logging
import os

from langchain.tools import tool

from kkoclaw.sandbox.tools import (
    _sanitize_error,
    execute_sandbox_command,
    ensure_sandbox_initialized,
    ensure_thread_directories_exist,
)
from kkoclaw.tools.coding.test_tools import (
    _command_with_project_root,
    _parse_linter_issues,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# Per-extension preferred linter ordering. The first available binary wins.
_EXT_LINTERS: dict[str, list[str]] = {
    ".py": ["ruff", "mypy", "flake8", "pylint"],
    ".pyi": ["ruff", "mypy", "flake8", "pylint"],
    ".ts": ["tsc", "eslint"],
    ".tsx": ["tsc", "eslint"],
    ".js": ["eslint", "tsc"],
    ".jsx": ["eslint", "tsc"],
    ".mjs": ["eslint"],
    ".cjs": ["eslint"],
    ".go": ["go vet"],
    ".rs": ["cargo clippy"],
}

# Maximum chars of raw linter output retained in the result.
_OUTPUT_CAP = 3000
# Maximum issues to include (avoids token bloat).
_MAX_ISSUES = 50


def _binary_available(runtime: Runtime, sandbox: object, name: str) -> bool:
    """Check if *name* is an executable available in the sandbox PATH."""
    try:
        result = execute_sandbox_command(
            runtime, sandbox, f"which {name} 2>/dev/null"
        )
        return bool(result.strip()) and "not found" not in result.lower()
    except Exception:
        return False


def detect_linter_for_file(
    runtime: Runtime,
    file_path: str,
) -> str | None:
    """Detect the best available linter for *file_path* based on its extension.

    Falls back to project-level detection from :func:`test_tools._detect_linter`
    when the extension is unknown.
    """
    ext = os.path.splitext(file_path)[1].lower()
    candidates = _EXT_LINTERS.get(ext)
    if not candidates:
        from kkoclaw.tools.coding.test_tools import _detect_linter

        return _detect_linter(runtime)

    sandbox = ensure_sandbox_initialized(runtime)
    ensure_thread_directories_exist(runtime)
    for linter in candidates:
        binary = linter.split()[0]  # "go vet" → "go", "cargo clippy" → "cargo"
        if _binary_available(runtime, sandbox, binary):
            return linter
    return None


def _build_lint_command(
    linter: str,
    file_path: str,
    extra_args: str = "",
) -> str:
    """Build the shell command for *linter* to check *file_path*."""
    extra = extra_args.strip()
    if linter == "ruff":
        return f"ruff check --output-format=concise {extra} '{file_path}'"
    if linter == "flake8":
        return f"flake8 {extra} '{file_path}'"
    if linter == "pylint":
        return f"pylint --output-format=text {extra} '{file_path}'"
    if linter == "mypy":
        return f"mypy {extra} '{file_path}'"
    if linter == "eslint":
        return f"npx eslint --format=compact {extra} '{file_path}'"
    if linter == "tsc":
        # tsc can't check a single file reliably; run project-wide --noEmit.
        return f"npx tsc --noEmit {extra}"
    if linter == "go vet":
        return f"go vet {extra} '{file_path}'"
    if linter == "cargo clippy":
        return f"cargo clippy --message-format=short {extra}"
    return f"{linter} {extra} '{file_path}'"


def run_file_diagnostics(
    runtime: Runtime,
    file_path: str,
    linter: str | None = None,
) -> dict | None:
    """Run diagnostics on a single file.

    Returns a result dict with ``linter``, ``file``, ``clean``,
    ``issue_count``, ``issues``, ``output`` — or ``None`` on failure
    (e.g. no linter available, sandbox error).

    This function is designed to be called from both tool context and
    middleware context. When called from an async middleware, wrap it in
    ``asyncio.to_thread`` to avoid blocking the event loop.
    """
    try:
        ln = linter or detect_linter_for_file(runtime, file_path)
        if not ln:
            return None

        cmd = _command_with_project_root(
            runtime, _build_lint_command(ln, file_path)
        )
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        output = execute_sandbox_command(runtime, sandbox, cmd)

        issues = _parse_linter_issues(output, ln)
        lowered = output.lower()
        has_issues = (
            bool(issues)
            and "no issues" not in lowered
            and "all checks passed" not in lowered
            and "no problems" not in lowered
            and "success: no issues" not in lowered
        )

        return {
            "linter": ln,
            "file": file_path,
            "clean": not has_issues,
            "issue_count": len(issues) if has_issues else 0,
            "issues": issues[:_MAX_ISSUES],
            "output": output[:_OUTPUT_CAP] if output.strip() else "(no output)",
        }
    except Exception as exc:
        logger.debug("run_file_diagnostics failed for %s: %s", file_path, exc)
        return None


@tool("get_diagnostics", parse_docstring=True)
def get_diagnostics_tool(
    runtime: Runtime,
    file_path: str,
    linter: str | None = None,
) -> str:
    """Get lint and type-check diagnostics for a single file.

    Faster than ``run_linter`` for post-edit verification because it only
    checks the specified file instead of scanning the whole project.

    The linter is auto-detected based on the file extension:
      - Python (.py/.pyi): ruff > mypy > flake8 > pylint
      - TypeScript (.ts/.tsx): tsc > eslint
      - JavaScript (.js/.jsx): eslint > tsc
      - Go (.go): go vet
      - Rust (.rs): cargo clippy

    Returns a JSON object with:
      - ``clean``: true if no issues found
      - ``issue_count``: number of issues
      - ``issues``: list of ``{file, line, column, message}`` dicts
      - ``output``: truncated raw linter output

    Args:
        file_path: Absolute path to the file to check.
        linter: Override linter (e.g. ``ruff``, ``mypy``, ``eslint``).
            Auto-detected if None.
    """
    try:
        result = run_file_diagnostics(runtime, file_path, linter)
        if result is None:
            return json.dumps(
                {
                    "file": file_path,
                    "clean": True,
                    "issue_count": 0,
                    "issues": [],
                    "note": "No linter available for this file type.",
                },
                ensure_ascii=False,
                indent=2,
            )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error: Failed to get diagnostics: {_sanitize_error(e, runtime)}"


__all__ = [
    "get_diagnostics_tool",
    "run_file_diagnostics",
    "detect_linter_for_file",
]
