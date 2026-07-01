"""Cross-file code navigation tools for the Coding Agent.

Provides:
- ``go_to_definition``: Find where a symbol is defined across the project.
- ``find_references``: Find all references to a symbol across the project.

These tools bridge the gap between single-file ``find_symbols`` / ``read_symbol``
and a full LSP server. They use a hybrid strategy:

1. **Symbol-accurate definition search** — for each candidate file, the
   tree-sitter / regex parser (from :mod:`_symbol_parser`) extracts all
   definitions and matches by name + kind, so ``foo`` as a function is
   distinguished from ``foo`` as a variable.
2. **Token-boundary reference search** — a negative-lookaround regex
   (the same approach as ``rename_symbol``) scans every source file of
   the same language, excluding comment lines by default.

When the binary is available, **pyright** is used as an optional
enhancement for Python files to provide type-aware hover info in the
``go_to_definition`` output.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re

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
from kkoclaw.tools.coding._symbol_parser import (
    detect_language_by_extension,
    parse_symbols,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# Limits to keep tool output manageable.
_MAX_DEFINITION_RESULTS = 20
_MAX_REFERENCE_RESULTS = 100
_MAX_FILES_TO_SCAN = 500

# Language slug → list of file extensions to search.
_LANG_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"],
    "go": [".go"],
    "rust": [".rs"],
}

# Definition kinds that represent "real" definitions (not just references).
_DEFINITION_KINDS = frozenset({
    "function", "method", "class", "interface", "type",
    "struct", "enum", "trait", "const",
})


def _project_root(runtime: Runtime) -> str:
    """Extract the project root from runtime context."""
    thread_data = get_thread_data(runtime)
    project_root = thread_data.get("project_root") if thread_data else None
    return project_root or "/mnt/user-data/workspace"


def _glob_source_files(
    sandbox: object,
    root: str,
    extensions: list[str],
    max_files: int = _MAX_FILES_TO_SCAN,
) -> list[str]:
    """Find all source files with the given extensions under *root*."""
    all_files, _ = sandbox.glob(root, "**/*", include_dirs=False, max_results=max_files * 3)
    filtered: list[str] = []
    for fp in all_files:
        ext = os.path.splitext(fp)[1].lower()
        if ext in extensions:
            filtered.append(fp)
            if len(filtered) >= max_files:
                break
    return filtered


def _try_pyright_definition(
    runtime: Runtime,
    sandbox: object,
    file_path: str,
    symbol_name: str,
) -> str | None:
    """If pyright is available, try to get type info for *symbol_name*.

    Pyright CLI doesn't provide go-to-definition directly, but its
    ``--outputjson`` mode emits symbol diagnostics that can hint at the
    definition location. This is a best-effort enhancement.
    """
    try:
        from kkoclaw.sandbox.tools import execute_sandbox_command

        # Check pyright availability
        check = execute_sandbox_command(runtime, sandbox, "which pyright 2>/dev/null")
        if not check.strip() or "not found" in check.lower():
            return None

        # Run pyright in quick mode to get symbol info
        result = execute_sandbox_command(
            runtime, sandbox,
            f"pyright --outputjson '{file_path}' 2>/dev/null | head -100",
        )
        if not result.strip():
            return None

        # Parse for definition hints (pyright emits ranges with symbol info)
        import json
        try:
            data = json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return None

        # Look for the symbol in the diagnostics
        for diag in data.get("generalDiagnostics", []):
            msg = diag.get("message", "")
            if symbol_name in msg:
                range_info = diag.get("range", {}).get("start", {})
                line = range_info.get("line", 0) + 1
                return f"  (pyright hint: L{line} — {msg[:150]})"
        return None
    except Exception:
        return None


def _mask_path(path: str, thread_data: object | None) -> str:
    """Mask local paths for display."""
    if thread_data is not None:
        return mask_local_paths_in_output(path, thread_data)
    return path


@tool("go_to_definition", parse_docstring=True)
def go_to_definition_tool(
    runtime: Runtime,
    file_path: str,
    symbol_name: str,
) -> str:
    """Find where a symbol is defined across the project.

    Searches all source files of the same language as ``file_path`` for
    the definition of ``symbol_name``. Uses tree-sitter / regex symbol
    parsing for accurate results (distinguishes ``foo`` as a function
    from ``foo`` as a variable).

    Returns each definition with its file path, line number, and kind
    (function / class / method / etc.).

    When pyright is available for Python files, type-aware hints are
    included in the output.

    Args:
        file_path: Path to a file that references the symbol (provides
            language context and search scope).
        symbol_name: The identifier to find the definition of
            (e.g. ``MyClass``, ``calculate_total``, ``UserService``).
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

        language = detect_language_by_extension(file_path)
        if not language:
            return f"Error: Unsupported file extension: {requested_path}"

        extensions = _LANG_EXTENSIONS.get(language, [])
        if not extensions:
            return f"Error: No extensions mapped for language '{language}'"

        project_root = _project_root(runtime)
        if is_local_sandbox(runtime):
            project_root = _resolve_local_read_path(project_root, thread_data)

        # 1. Check the current file first (most common case).
        definitions: list[tuple[str, int, str, str]] = []  # (file, line, kind, name)

        try:
            current_content = sandbox.read_file(file_path) or ""
            for sym in parse_symbols(current_content, language):
                if sym.name == symbol_name and sym.kind in _DEFINITION_KINDS:
                    definitions.append((file_path, sym.line, sym.kind, sym.name))
        except Exception:
            pass

        # 2. Search other source files in the project.
        if len(definitions) < _MAX_DEFINITION_RESULTS:
            source_files = _glob_source_files(sandbox, project_root, extensions)
            for fp in source_files:
                if len(definitions) >= _MAX_DEFINITION_RESULTS:
                    break
                if os.path.abspath(fp) == os.path.abspath(file_path):
                    continue  # already checked
                try:
                    content = sandbox.read_file(fp) or ""
                except Exception:
                    continue
                for sym in parse_symbols(content, language):
                    if sym.name == symbol_name and sym.kind in _DEFINITION_KINDS:
                        entry = (fp, sym.line, sym.kind, sym.name)
                        # Avoid duplicates
                        if not any(d[0] == fp and d[1] == sym.line for d in definitions):
                            definitions.append(entry)
                        if len(definitions) >= _MAX_DEFINITION_RESULTS:
                            break

        if not definitions:
            return (
                f"No definition found for '{symbol_name}' "
                f"({language} files searched in {requested_path}'s project)."
            )

        # Format output
        lines = [f"Found {len(definitions)} definition(s) for '{symbol_name}':\n"]
        for fp, line_no, kind, name in definitions:
            display_fp = _mask_path(fp, thread_data)
            lines.append(f"  {display_fp}  L{line_no}  [{kind}]  {name}")

        # Optional pyright enhancement
        if language == "python":
            pyright_hint = _try_pyright_definition(
                runtime, sandbox, file_path, symbol_name
            )
            if pyright_hint:
                lines.append(f"\n{pyright_hint}")

        return "\n".join(lines)
    except SandboxError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File not found: {requested_path}"
    except Exception as e:
        return f"Error: Unexpected error finding definition: {_sanitize_error(e, runtime)}"


@tool("find_references", parse_docstring=True)
def find_references_tool(
    runtime: Runtime,
    file_path: str,
    symbol_name: str,
    include_comments: bool = False,
) -> str:
    """Find all references to a symbol across the project.

    Uses token-boundary-aware regex search (same approach as
    ``rename_symbol``) so that ``foo`` matches but not ``foobar``,
    ``myfoo``, or ``foo`` inside a longer token.

    Searches all source files of the same language as ``file_path``.
    Returns each usage with its file path, line number, and the matching
    code line.

    Args:
        file_path: Path to a file where the symbol is defined or used
            (provides language context and search scope).
        symbol_name: The identifier to find references for.
        include_comments: If True, include matches inside comment lines.
            Default False (comments are skipped for cleaner results).
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

        language = detect_language_by_extension(file_path)
        if not language:
            return f"Error: Unsupported file extension: {requested_path}"

        extensions = _LANG_EXTENSIONS.get(language, [])
        if not extensions:
            return f"Error: No extensions mapped for language '{language}'"

        project_root = _project_root(runtime)
        if is_local_sandbox(runtime):
            project_root = _resolve_local_read_path(project_root, thread_data)

        # Build token-boundary regex (same as rename_symbol)
        pattern = re.compile(
            r"(?<![A-Za-z0-9_$])" + re.escape(symbol_name) + r"(?![A-Za-z0-9_$])"
        )

        # Comment markers by language
        comment_markers: tuple[str, ...]
        if language == "python":
            comment_markers = ("#",)
        else:
            comment_markers = ("//",)

        source_files = _glob_source_files(sandbox, project_root, extensions)
        references: list[tuple[str, int, str]] = []  # (file, line, content)

        for fp in source_files:
            if len(references) >= _MAX_REFERENCE_RESULTS:
                break
            try:
                content = sandbox.read_file(fp) or ""
            except Exception:
                continue
            for i, line in enumerate(content.splitlines(), start=1):
                if len(references) >= _MAX_REFERENCE_RESULTS:
                    break
                if not include_comments:
                    stripped = line.lstrip()
                    if any(stripped.startswith(m) for m in comment_markers):
                        continue
                if pattern.search(line):
                    references.append((fp, i, line.strip()[:200]))

        if not references:
            return (
                f"No references to '{symbol_name}' found "
                f"({language} files searched in {requested_path}'s project)."
            )

        # Format output
        lines = [f"Found {len(references)} reference(s) to '{symbol_name}':\n"]
        current_file: str | None = None
        for fp, line_no, content_line in references:
            display_fp = _mask_path(fp, thread_data)
            if display_fp != current_file:
                current_file = display_fp
                lines.append(f"\n  {display_fp}:")
            lines.append(f"    L{line_no:>5}  {content_line}")

        if len(references) >= _MAX_REFERENCE_RESULTS:
            lines.append(
                f"\n  ... (showing first {_MAX_REFERENCE_RESULTS} references)"
            )

        return "\n".join(lines)
    except SandboxError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File not found: {requested_path}"
    except Exception as e:
        return f"Error: Unexpected error finding references: {_sanitize_error(e, runtime)}"


__all__ = ["go_to_definition_tool", "find_references_tool"]
