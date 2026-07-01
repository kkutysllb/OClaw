"""Code impact analysis tool for the Coding Agent.

Provides:
- ``analyze_impact``: Given a symbol name or file path, find all files
  that depend on it (directly or transitively) via import graph analysis.
- ``build_dependency_graph``: Internal helper that builds an import graph
  from Python ``import`` / ``from ... import`` statements (AST-based for
  Python, regex for JS/TS/Go).

This answers the question "if I change X, what else might break?" —
which is critical for safe refactoring and code review.

Import parsing strategy
-----------------------
- **Python**: Uses the ``ast`` module for precise import extraction.
  Handles ``import x``, ``import x.y as z``, ``from . import y``,
  ``from ..pkg import z``, etc.
- **JavaScript/TypeScript**: Regex for ``import ... from '...'`` and
  ``require('...')`` and ``export ... from '...'``.
- **Go**: Regex for ``import "..."`` and multi-import blocks.

The graph is built once per project and cached. Impact analysis then
walks the reverse graph (who imports this module?) to find dependents.
"""

from __future__ import annotations

import ast
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

from langchain.tools import tool

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

# Max files to scan for import graph.
_MAX_GRAPH_FILES = 600
# Max depth for transitive dependency walk.
_MAX_DEPTH = 5


# --------------------------------------------------------------------- #
# Import parsing
# --------------------------------------------------------------------- #


def _parse_python_imports(content: str) -> list[str]:
    """Extract module names imported by Python source code.

    Returns a list of module paths like ``["os", "kkoclaw.tools.types",
    ".utils", "..core.base"]``.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                prefix = "." * (node.level or 0)
                modules.append(prefix + node.module)
            elif node.level:
                # Relative import without explicit module: from . import X
                modules.append("." * node.level)
    return modules


# JS/TS: import ... from '...';  require('...');  export ... from '...'
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+[^'"]*?\s+from\s+|require\s*\(\s*|export\s+[^'"]*?\s+from\s+)
        ['"]([^'"]+)['"]""",
    re.VERBOSE | re.MULTILINE,
)

# Go: import "..." and import ( ... "..." ... )
_GO_IMPORT_RE = re.compile(r'"([^"]+)"')


def _parse_js_imports(content: str) -> list[str]:
    """Extract module paths from JS/TS source."""
    return _JS_IMPORT_RE.findall(content)


def _parse_go_imports(content: str) -> list[str]:
    """Extract package paths from Go source.

    Handles both single-line ``import "pkg"`` and multi-line import blocks.
    """
    modules: list[str] = []

    # Multi-line import blocks: import ( ... )
    for block_match in re.finditer(
        r"import\s*\(([^)]*\n)", content, re.MULTILINE
    ):
        for line in block_match.group(1).splitlines():
            m = _GO_IMPORT_RE.search(line)
            if m:
                modules.append(m.group(1))

    # Single-line: import "pkg"
    for m in re.finditer(r"^\s*import\s+([^(].*?)$", content, re.MULTILINE):
        line = m.group(1).strip()
        pkg_match = _GO_IMPORT_RE.search(line)
        if pkg_match:
            modules.append(pkg_match.group(1))

    return modules


def _detect_language(file_path: str) -> str | None:
    """Return the language slug for a file based on its extension."""
    ext_lang = {
        ".py": "python", ".pyi": "python",
        ".js": "javascript", ".jsx": "javascript",
        ".mjs": "javascript", ".cjs": "javascript",
        ".ts": "javascript", ".tsx": "javascript",
        ".go": "go",
    }
    _, ext = os.path.splitext(file_path)
    return ext_lang.get(ext.lower())


def _parse_imports(file_path: str, content: str) -> list[str]:
    """Parse imports from *content* based on *file_path*'s language."""
    lang = _detect_language(file_path)
    if lang == "python":
        return _parse_python_imports(content)
    if lang == "javascript":
        return _parse_js_imports(content)
    if lang == "go":
        return _parse_go_imports(content)
    return []


# --------------------------------------------------------------------- #
# Dependency graph
# --------------------------------------------------------------------- #


def _should_scan(path: str) -> bool:
    """Check if *path* should be included in the import graph scan."""
    import os

    code_exts = {".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go"}
    _, ext = os.path.splitext(path)
    if ext.lower() not in code_exts:
        return False
    lower = path.lower().replace("\\", "/")
    skip_dirs = (
        "/node_modules/", "/.git/", "/.venv/", "/venv/",
        "/__pycache__/", "/dist/", "/build/", "/.next/",
        "/.pytest_cache/", "/.ruff_cache/", "/target/",
    )
    for skip in skip_dirs:
        if skip in lower:
            return False
    return True


@dataclass
class DependencyGraph:
    """Directed import graph: edges go from importer → imported."""

    # adj[file_path] = set of module paths it imports
    adj: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # reverse[file_path] = set of files that import it
    reverse: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # All files in the graph
    files: set[str] = field(default_factory=set)

    def add_edge(self, importer: str, imported: str) -> None:
        self.adj[importer].add(imported)
        self.reverse[imported].add(importer)
        self.files.add(importer)
        self.files.add(imported)

    def dependents(self, target: str, max_depth: int = _MAX_DEPTH) -> list[str]:
        """Find all files that directly or transitively depend on *target*.

        Walks the reverse graph (who imports this?).
        """
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(target, 0)]
        result: list[str] = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            for dep in self.reverse.get(current, set()):
                if dep not in visited:
                    result.append(dep)
                    queue.append((dep, depth + 1))

        return sorted(set(result) - {target})

    def dependencies(self, target: str, max_depth: int = _MAX_DEPTH) -> list[str]:
        """Find all files that *target* depends on (forward walk)."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(target, 0)]
        result: list[str] = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            for dep in self.adj.get(current, set()):
                if dep not in visited:
                    result.append(dep)
                    queue.append((dep, depth + 1))

        return sorted(set(result) - {target})


# Module-level cache: keyed by project_root.
_GRAPH_CACHE: dict[str, DependencyGraph] = {}


def _resolve_relative_import(
    file_path: str,
    module: str,
    project_root: str,
) -> str | None:
    """Resolve a Python relative import to an absolute module/file path.

    Handles ``from . import X`` and ``from ..pkg import Y``.
    """
    if not module.startswith("."):
        return module

    # Determine the package level of the importing file
    rel = os.path.relpath(file_path, project_root)
    parts = rel.replace("\\", "/").split("/")
    # Remove filename
    parts = parts[:-1]

    # Count leading dots
    level = 0
    while level < len(module) and module[level] == ".":
        level += 1

    # Go up (level - 1) directories from the file's package
    if level > len(parts):
        return None
    base_parts = parts[: len(parts) - (level - 1)]
    remaining = module[level:]
    if remaining:
        base_parts.append(remaining.replace(".", "/"))

    return "/".join(base_parts)


def _build_graph(
    sandbox: object,
    project_root: str,
) -> DependencyGraph:
    """Build an import dependency graph by scanning source files."""
    all_files, _ = sandbox.glob(
        project_root, "**/*", include_dirs=False, max_results=_MAX_GRAPH_FILES * 3
    )
    source_files = [fp for fp in all_files if _should_scan(fp)]

    graph = DependencyGraph()

    for fp in source_files:
        graph.files.add(fp)
        try:
            content = sandbox.read_file(fp) or ""
        except Exception:
            continue

        raw_imports = _parse_imports(fp, content)
        for module in raw_imports:
            # Resolve relative imports for Python
            if module.startswith(".") and _detect_language(fp) == "python":
                resolved = _resolve_relative_import(fp, module, project_root)
                if resolved:
                    module = resolved

            # Normalize: convert dots to slashes for module paths
            norm = module.lstrip(".").replace(".", "/")

            # Try to find the actual file in the project
            # Check for .py, .js, .ts, .go, .jsx, .tsx variants
            for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".go"):
                candidate = os.path.join(project_root, norm + ext)
                if os.path.normpath(candidate) in {os.path.normpath(f) for f in source_files}:
                    graph.add_edge(fp, candidate)
                    break
                # Also try as a directory with __init__ or index
                index_candidate = os.path.join(project_root, norm, "__init__" + ext)
                if os.path.normpath(index_candidate) in {os.path.normpath(f) for f in source_files}:
                    graph.add_edge(fp, index_candidate)
                    break
                index_js = os.path.join(project_root, norm, "index" + ext)
                if os.path.normpath(index_js) in {os.path.normpath(f) for f in source_files}:
                    graph.add_edge(fp, index_js)
                    break

    return graph


def _get_or_build_graph(
    sandbox: object,
    project_root: str,
) -> DependencyGraph:
    """Return cached graph or build a new one."""
    cached = _GRAPH_CACHE.get(project_root)
    if cached is not None:
        return cached
    graph = _build_graph(sandbox, project_root)
    _GRAPH_CACHE[project_root] = graph
    return graph


# --------------------------------------------------------------------- #
# Tool
# --------------------------------------------------------------------- #


@tool("analyze_impact", parse_docstring=True)
def analyze_impact_tool(
    runtime: Runtime,
    file_path: str,
    direction: str = "dependents",
    max_depth: int = 3,
) -> str:
    """Analyze the impact of changing a file using import dependency graph.

    Builds an import graph for the project and walks it to answer:

    - ``dependents`` (default): What files **import** this file? Changing
      this file may break them. These are your blast radius.
    - ``dependencies``: What files does this file **import**? These are
      its dependencies — if they change, this file may be affected.

    The graph supports Python (AST-based), JavaScript/TypeScript (regex),
    and Go (regex) projects.

    Use this before refactoring to understand what might break::

        analyze_impact("src/auth/models.py")  # Who depends on this?
        analyze_impact("src/utils/helpers.ts", direction="dependencies")

    Args:
        file_path: Absolute path to the file to analyze.
        direction: ``dependents`` (who imports this) or ``dependencies``
            (what this imports). Default ``dependents``.
        max_depth: Maximum graph traversal depth. Default 3.
    """
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)

        requested_path = file_path
        thread_data = None
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            validate_local_tool_path(file_path, thread_data, read_only=True)
            file_path = _resolve_local_read_path(file_path, thread_data)

        # Determine project root
        from kkoclaw.tools.coding.lsp_tools import _project_root

        project_root = _project_root(runtime)
        if is_local_sandbox(runtime):
            project_root = _resolve_local_read_path(project_root, thread_data)

        # Build or fetch graph
        graph = _get_or_build_graph(sandbox, project_root)

        if file_path not in graph.files:
            # Try normalizing
            norm_path = os.path.normpath(file_path)
            if norm_path not in graph.files:
                return (
                    f"File '{requested_path}' not found in the import graph "
                    f"({len(graph.files)} files scanned). It may not be a "
                    f"source file or may be excluded (node_modules, .git, etc.)."
                )
            file_path = norm_path

        # Walk the graph
        if direction == "dependencies":
            related = graph.dependencies(file_path, max_depth=max_depth)
            label = "dependencies (files this imports)"
        else:
            related = graph.dependents(file_path, max_depth=max_depth)
            label = "dependents (files that import this)"

        if not related:
            return (
                f"No {label} found for '{requested_path}'.\n"
                f"This file is not imported by any other scanned source file."
            )

        # Format output
        lines = [
            f"Impact analysis for '{requested_path}':",
            f"  Found {len(related)} {label}:\n",
        ]
        for fp in related:
            display_fp = fp
            if thread_data is not None:
                display_fp = mask_local_paths_in_output(fp, thread_data)
            lines.append(f"  - {display_fp}")

        lines.append(f"\n  (Graph: {len(graph.files)} files, {sum(len(v) for v in graph.adj.values())} edges)")

        return "\n".join(lines)
    except SandboxError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File not found: {requested_path}"
    except Exception as e:
        return f"Error: Unexpected error analyzing impact: {_sanitize_error(e, runtime)}"


__all__ = ["analyze_impact_tool", "DependencyGraph"]
