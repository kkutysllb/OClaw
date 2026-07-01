"""Smart test selection tool for the Coding Agent.

Provides:
- ``run_affected_tests``: Run only the tests that are affected by the current
  uncommitted changes (``git diff``), rather than the full test suite.

This saves significant time and token budget on large projects. The selection
strategy combines three signals:

1. **Direct test changes**: If ``test_foo.py`` itself was modified, run it.
2. **Source → test mapping**: If ``src/foo.py`` was modified, find and run
   the corresponding test file (``test_foo.py``, ``foo_test.go``, etc.).
3. **Import-graph reverse traversal**: If ``src/base.py`` was modified, and
   ``src/foo.py`` imports it, then ``test_foo.py`` should also be run because
   the change might affect ``foo``'s behavior.

If no changes are detected (clean working tree) or the mapping yields no test
files, the tool falls back to running the full test suite with a note.

Supported frameworks:
  - pytest (Python): ``test_*.py``, ``*_test.py``
  - jest/vitest (Node): ``*.test.ts/js``, ``*.spec.ts/js``
  - go test (Go): ``*_test.go``

The tool is best-effort — it never *skips* tests silently. If it cannot
determine affected tests, it runs everything and tells the model.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from kkoclaw.sandbox.tools import (
    _sanitize_error,
    ensure_sandbox_initialized,
    ensure_thread_directories_exist,
    execute_sandbox_command,
    get_thread_data,
)
from kkoclaw.tools.coding.test_tools import (
    _build_test_result_command,
    _detect_test_framework,
    _parse_jest_text,
    _parse_generic_text,
    _run_pytest_structured,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# Maximum number of test-file paths to collect before bailing out.
_MAX_TEST_TARGETS = 30
# Maximum files to scan when doing co-located test discovery.
_MAX_SCAN_FILES = 1000

# Patterns that identify test files by extension/convention.
_TEST_FILE_PATTERNS = [
    re.compile(r"(^|/)test_[^/]+\.pyi?$"),          # test_foo.py
    re.compile(r"(^|/)[^/]+_test\.pyi?$"),           # foo_test.py
    re.compile(r"(^|/)[^/]+\.(test|spec)\.(ts|js|tsx|jsx)$"),  # foo.test.ts
    re.compile(r"(^|/)[^/]+_test\.go$"),             # foo_test.go
    re.compile(r"(^|/)tests/[^/]+\.rs$"),            # Rust tests/ dir
]


# ------------------------------------------------------------------ #
# Git diff: find changed files
# ------------------------------------------------------------------ #


def _get_changed_files(project_root: str, staged_only: bool = False) -> list[str]:
    """Return a list of changed file paths relative to *project_root*.

    Uses ``git diff --name-only`` against HEAD (or ``--cached`` for staged).
    Falls back to an empty list if git is unavailable or the directory is
    not a git repo.
    """
    root = Path(project_root)
    if not (root / ".git").exists():
        return []

    args = ["git", "-C", str(root), "diff", "--name-only"]
    if not staged_only:
        args.append("HEAD")
    else:
        args = ["git", "-C", str(root), "diff", "--cached", "--name-only"]

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            # HEAD might not exist (initial commit) — try untracked + unstaged
            result = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        files = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith(".")
        ]
        return files
    except Exception:
        return []


def _is_test_file(file_path: str) -> bool:
    """Check if a file path matches any test-file convention."""
    return any(p.search(file_path) for p in _TEST_FILE_PATTERNS)


# ------------------------------------------------------------------ #
# Source → test file mapping
# ------------------------------------------------------------------ #


def _source_to_test_candidates(source_file: str) -> list[str]:
    """Generate plausible test-file paths for a given source file.

    For ``src/foo/bar.py``:
      → ``src/foo/test_bar.py``
      → ``tests/test_bar.py``
      → ``src/foo/bar_test.py``

    For ``src/components/Button.tsx``:
      → ``src/components/Button.test.tsx``
      → ``src/components/Button.spec.tsx``
      → ``tests/components/Button.test.tsx``

    Returns a list of candidate paths; the caller checks which exist.
    """
    p = Path(source_file)
    stem = p.stem
    parent = p.parent
    ext = p.suffix

    candidates: list[str] = []

    if ext in (".py", ".pyi"):
        # Co-located: test_bar.py in same dir
        candidates.append(str(parent / f"test_{stem}.py"))
        candidates.append(str(parent / f"{stem}_test.py"))
        # tests/ directory siblings
        candidates.append(str(parent / "tests" / f"test_{stem}.py"))
        candidates.append(str(parent / "tests" / f"{stem}_test.py"))
        # Top-level tests/ dir
        candidates.append(f"tests/test_{stem}.py")
        candidates.append(f"test/test_{stem}.py")

    elif ext in (".ts", ".tsx", ".js", ".jsx"):
        for suffix in (".test", ".spec"):
            candidates.append(str(parent / f"{stem}{suffix}{ext}"))
            candidates.append(str(parent / "__tests__" / f"{stem}{suffix}{ext}"))
            candidates.append(f"tests/{stem}{suffix}{ext}")

    elif ext == ".go":
        candidates.append(str(parent / f"{stem}_test.go"))

    elif ext == ".rs":
        candidates.append(str(parent / "tests" / f"{stem}.rs"))
        candidates.append(str(parent / f"{stem}.rs"))

    return candidates


def _find_existing_tests(
    project_root: str,
    source_files: list[str],
) -> list[str]:
    """For each source file, check which candidate test files actually exist.

    Returns a deduplicated list of test file paths (relative to project root).
    """
    root = Path(project_root)
    found: set[str] = set()

    for src in source_files:
        for candidate in _source_to_test_candidates(src):
            full = root / candidate
            if full.is_file():
                # Normalize to relative path
                found.add(candidate)

    return sorted(found)


# ------------------------------------------------------------------ #
# Import-graph reverse traversal
# ------------------------------------------------------------------ #


def _find_dependents_of(
    project_root: str,
    changed_files: list[str],
) -> list[str]:
    """Find source files that import any of the changed files.

    Uses AST/regex import parsing to build a lightweight reverse dependency
    map, then returns all source files that transitively depend on any
    changed file.
    """
    try:
        return _build_local_dependents(project_root, changed_files)
    except Exception:
        logger.debug("Import graph traversal failed, skipping", exc_info=True)
        return []


def _build_local_dependents(
    project_root: str,
    changed_files: list[str],
) -> list[str]:
    """Scan the project for imports and find dependents of changed files.

    This uses the filesystem directly (``Path.glob``) rather than going
    through the sandbox abstraction, since smart test selection is always
    used in a local development context.
    """
    from kkoclaw.tools.coding.impact_analysis import (
        _parse_python_imports,
        _parse_js_imports,
        _parse_go_imports,
        _detect_language,
        _should_scan,
    )

    root = Path(project_root)

    # Build a set of changed file basenames (without extension) for matching
    changed_stems = set()
    changed_paths_norm = set()
    for cf in changed_files:
        changed_stems.add(Path(cf).stem)
        changed_paths_norm.add(os.path.normpath(cf))

    # Scan source files for imports that reference changed files
    dependents: set[str] = set()
    scanned = 0
    for src_path in root.rglob("*"):
        if scanned >= _MAX_SCAN_FILES:
            break
        if not src_path.is_file():
            continue
        rel = str(src_path.relative_to(root))
        if not _should_scan(rel):
            continue
        scanned += 1

        try:
            content = src_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lang = _detect_language(rel)
        if lang == "python":
            imports = _parse_python_imports(content)
        elif lang in ("javascript", "typescript"):
            imports = _parse_js_imports(content)
        elif lang == "go":
            imports = _parse_go_imports(content)
        else:
            continue

        # Check if any import matches a changed file
        for imp in imports:
            imp_stem = imp.replace(".", "/").rsplit("/", 1)[-1].lstrip(".")
            if imp_stem in changed_stems:
                dependents.add(rel)
                break
            # Also check if the import path matches a changed file path
            imp_norm = imp.lstrip(".").replace(".", "/")
            for cf in changed_files:
                cf_stem = Path(cf).stem
                if imp_norm.endswith(cf_stem) or cf_stem in imp_norm.split("/"):
                    dependents.add(rel)
                    break

    return sorted(dependents)


# ------------------------------------------------------------------ #
# Main selection logic
# ------------------------------------------------------------------ #


def select_affected_tests(
    project_root: str,
    changed_files: list[str] | None = None,
) -> dict:
    """Select which test files to run based on changed files.

    Returns a dict with:
      - ``test_files``: list of test file paths to run
      - ``changed_source_files``: non-test files that changed
      - ``changed_test_files``: test files that changed directly
      - ``mapped_tests``: test files found via source→test mapping
      - ``graph_tests``: test files found via import-graph traversal
      - ``reason``: human-readable explanation
    """
    if changed_files is None:
        changed_files = _get_changed_files(project_root)

    changed_test_files = [f for f in changed_files if _is_test_file(f)]
    changed_source_files = [f for f in changed_files if not _is_test_file(f)]

    # Direct test file changes → run them
    targets: set[str] = set(changed_test_files)

    # Source → test mapping
    mapped = _find_existing_tests(project_root, changed_source_files)
    targets.update(mapped)

    # Import-graph reverse traversal: find files that depend on changed sources,
    # then find their test files too
    graph_dependents = _find_dependents_of(project_root, changed_source_files)
    if graph_dependents:
        # Filter to only source files that have tests
        graph_tests = _find_existing_tests(project_root, graph_dependents)
        targets.update(graph_tests)
    else:
        graph_tests = []

    # If we have too many targets, fall back to full suite
    if len(targets) > _MAX_TEST_TARGETS:
        return {
            "test_files": [],
            "changed_source_files": changed_source_files,
            "changed_test_files": changed_test_files,
            "mapped_tests": mapped,
            "graph_tests": graph_tests,
            "reason": (
                f"Too many affected test files ({len(targets)} > {_MAX_TEST_TARGETS}). "
                "Running full test suite instead."
            ),
            "fallback_to_all": True,
        }

    # If nothing changed, fall back to full suite
    if not targets and not changed_files:
        return {
            "test_files": [],
            "changed_source_files": [],
            "changed_test_files": [],
            "mapped_tests": [],
            "graph_tests": [],
            "reason": "No uncommitted changes detected. Running full test suite.",
            "fallback_to_all": True,
        }

    if not targets:
        return {
            "test_files": [],
            "changed_source_files": changed_source_files,
            "changed_test_files": changed_test_files,
            "mapped_tests": [],
            "graph_tests": [],
            "reason": (
                f"Changed {len(changed_source_files)} source file(s) but found no "
                "corresponding test files. Running full test suite."
            ),
            "fallback_to_all": True,
        }

    return {
        "test_files": sorted(targets),
        "changed_source_files": changed_source_files,
        "changed_test_files": changed_test_files,
        "mapped_tests": mapped,
        "graph_tests": graph_tests,
        "reason": _build_reason(
            changed_test_files, changed_source_files, mapped, graph_tests, sorted(targets),
        ),
        "fallback_to_all": False,
    }


def _build_reason(
    direct_tests: list[str],
    source_files: list[str],
    mapped: list[str],
    graph_tests: list[str],
    all_targets: list[str],
) -> str:
    """Build a concise human-readable explanation of the selection."""
    parts: list[str] = []
    if direct_tests:
        parts.append(f"{len(direct_tests)} directly changed test file(s)")
    if mapped:
        parts.append(f"{len(mapped)} mapped from changed source(s)")
    if graph_tests:
        parts.append(f"{len(graph_tests)} from import-graph dependents")
    selection = ", ".join(parts) or "all"
    return (
        f"Running {len(all_targets)} affected test file(s) ({selection}). "
        f"Changed: {len(source_files)} source + {len(direct_tests)} test files."
    )


# ------------------------------------------------------------------ #
# Tool
# ------------------------------------------------------------------ #


@tool("run_affected_tests", parse_docstring=True)
def run_affected_tests_tool(
    runtime: Runtime,
    extra_args: str = "",
    staged_only: bool = False,
) -> str:
    """Run only the tests affected by current uncommitted changes.

    Uses ``git diff`` to find changed files, maps source files to their
    test files (by convention), and also traverses the import graph to
    find tests that might break due to dependency changes.

    If the selection is empty or too broad, falls back to running the
    full test suite with an explanation.

    This is much faster than ``run_tests`` on large projects where you
    only changed a few files.

    Args:
        extra_args: Additional CLI arguments for the test runner.
        staged_only: If True, only consider staged changes (git diff --cached).
            Default False considers all changes vs HEAD.
    """
    try:
        project_root = _get_project_root(runtime)
        if not project_root:
            return "Error: No project root configured. Cannot determine changed files."

        selection = select_affected_tests(project_root)
        framework = _detect_test_framework(runtime)

        if not framework:
            return "Error: Could not auto-detect test framework."

        # Fallback to full suite
        if selection["fallback_to_all"]:
            if framework == "pytest":
                result = _run_pytest_structured(runtime, None, extra_args)
                result["smart_selection"] = {"reason": selection["reason"], "fallback": True}
                return _build_test_result_command(runtime, result)
            # For other frameworks, run with no target
            target = None
        else:
            target = " ".join(selection["test_files"])

        # Build the command and run
        if framework == "pytest":
            result = _run_pytest_structured(runtime, target, extra_args)
            result["smart_selection"] = {
                "reason": selection["reason"],
                "test_files": selection["test_files"],
                "changed_source_files": selection["changed_source_files"],
                "changed_test_files": selection["changed_test_files"],
                "fallback": False,
            }
            return _build_test_result_command(runtime, result)

        if framework in ("jest", "vitest"):
            runner = "npx jest" if framework == "jest" else "npx vitest"
            cmd = f"{runner} --verbose {extra_args}"
            if target:
                cmd += f" {target}"
            sandbox = ensure_sandbox_initialized(runtime)
            ensure_thread_directories_exist(runtime)
            output = execute_sandbox_command(runtime, sandbox, _cmd_with_cd(runtime, cmd))
            result = _parse_jest_text(output, cmd)
            result["smart_selection"] = {
                "reason": selection["reason"],
                "test_files": selection["test_files"],
                "fallback": False,
            }
            return _build_test_result_command(runtime, result)

        # go test / cargo test / others
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        cmd = f"{framework} {extra_args}"
        if target:
            cmd += f" {target}"
        output = execute_sandbox_command(runtime, sandbox, _cmd_with_cd(runtime, cmd))
        result = _parse_generic_text(output, cmd, framework)
        result["smart_selection"] = {
            "reason": selection["reason"],
            "test_files": selection["test_files"],
            "fallback": False,
        }
        return _build_test_result_command(runtime, result)

    except Exception as e:
        return f"Error: Failed to run affected tests: {_sanitize_error(e, runtime)}"


@tool("preview_affected_tests", parse_docstring=True)
def preview_affected_tests_tool(runtime: Runtime) -> str:
    """Preview which test files would be run by ``run_affected_tests``.

    This is a read-only preview: it shows the git diff, the source→test
    mapping, and the import-graph traversal results without actually
    running any tests. Useful for understanding why certain tests were
    selected (or why the full suite was chosen as fallback).

    Returns a structured JSON summary.
    """
    import json

    project_root = _get_project_root(runtime)
    if not project_root:
        return "Error: No project root configured."

    changed_files = _get_changed_files(project_root)
    if not changed_files:
        return json.dumps(
            {
                "changed_files": [],
                "message": "No uncommitted changes detected. 'run_affected_tests' will run the full suite.",
            },
            indent=2,
            ensure_ascii=False,
        )

    selection = select_affected_tests(project_root, changed_files)
    return json.dumps(selection, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _get_project_root(runtime: Runtime) -> str | None:
    """Get the project root from runtime thread data."""
    thread_data = get_thread_data(runtime)
    if thread_data:
        root = thread_data.get("project_root")
        if root:
            return root
    return None


def _cmd_with_cd(runtime: Runtime, cmd: str) -> str:
    """Prefix a command with ``cd project_root &&`` if available."""
    project_root = _get_project_root(runtime)
    if project_root:
        return f'cd "{project_root}" && {cmd}'
    return cmd
