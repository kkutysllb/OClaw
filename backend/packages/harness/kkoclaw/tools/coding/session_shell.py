"""Session-based persistent shell tool for the Coding Agent.

Provides:
- ``session_shell``: Execute commands in a persistent shell session that
  preserves working directory and environment variables across calls.

Unlike the stateless ``bash`` tool (each call starts fresh),
``session_shell`` maintains session state in ``runtime.state`` so that
``cd`` and ``export`` effects persist between tool invocations within
the same thread.

This avoids the common anti-pattern of repeating
``cd /long/project/path && ...`` on every single command when working
inside a specific subdirectory. It also enables incremental workflows
like::

    session_shell("cd backend")
    session_shell("source .venv/bin/activate")
    session_shell("python manage.py migrate")   # runs in backend/ with venv active

State persistence model
-----------------------
Session data (``cwd`` and ``env``) is stored in
``runtime.state["_session_shell"]``.  The state dict is shared across
all tool calls within the same agent run, so changes are visible to
subsequent ``session_shell`` invocations automatically.
"""

from __future__ import annotations

import logging
import re

from langchain.tools import tool

from kkoclaw.sandbox.exceptions import SandboxError
from kkoclaw.sandbox.security import LOCAL_HOST_BASH_DISABLED_MESSAGE, is_host_bash_allowed
from kkoclaw.sandbox.tools import (
    _sanitize_error,
    _truncate_bash_output,
    ensure_sandbox_initialized,
    ensure_thread_directories_exist,
    execute_sandbox_command,
    get_thread_data,
    is_local_sandbox,
    mask_local_paths_in_output,
    replace_virtual_paths_in_command,
    validate_local_bash_command_paths,
)
from kkoclaw.tools.types import Runtime

logger = logging.getLogger(__name__)

# Key in runtime.state where session data is persisted.
_SESSION_STATE_KEY = "_session_shell"

# Marker appended to every command so we can parse the post-execution cwd.
_CWD_MARKER = "__SESSION_CWD__:"

# Regex to extract export VAR=value from the user's command.
# The unquoted value stops at shell separators: ; & | and quotes/newlines.
_EXPORT_RE = re.compile(
    r'\bexport\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*'
    r'(["\']?)([^;"\'\n&|]+)\2'
)

# Max env vars to track (prevents unbounded growth).
_MAX_TRACKED_ENV = 50
# Default output truncation limit.
_DEFAULT_OUTPUT_MAX = 20000


def _get_session(runtime: Runtime) -> dict:
    """Read session state from runtime, returning a default if absent."""
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return {}
    session = state.get(_SESSION_STATE_KEY)
    if not isinstance(session, dict):
        return {}
    return session


def _save_session(runtime: Runtime, session: dict) -> None:
    """Persist session state into runtime.state."""
    state = getattr(runtime, "state", None)
    if isinstance(state, dict):
        state[_SESSION_STATE_KEY] = session


def _default_cwd(runtime: Runtime, thread_data: dict | None) -> str:
    """Determine the default cwd (project root or workspace)."""
    if thread_data:
        root = thread_data.get("project_root")
        if root:
            return root
        workspace = thread_data.get("workspace_path")
        if workspace:
            return workspace
    return "/mnt/user-data/workspace"


def _parse_exports(command: str) -> dict[str, str]:
    """Extract ``export VAR=value`` pairs from *command*.

    Only well-formed single-line exports are captured. Complex shell
    expansions (``$(...)``, backticks) are kept verbatim — they are
    re-evaluated on each subsequent call.
    """
    exports: dict[str, str] = {}
    for m in _EXPORT_RE.finditer(command):
        var = m.group(1)
        val = m.group(3).strip()
        if var not in exports:
            exports[var] = val
        if len(exports) >= _MAX_TRACKED_ENV:
            break
    return exports


def _parse_cwd_from_output(output: str) -> tuple[str, str]:
    """Extract the ``__SESSION_CWD__`` marker from output.

    Returns ``(cwd_or_empty, cleaned_output)``.
    """
    lines = output.splitlines()
    cwd = ""
    clean_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(_CWD_MARKER):
            cwd = line.strip()[len(_CWD_MARKER):].strip()
        else:
            clean_lines.append(line)
    return cwd, "\n".join(clean_lines)


@tool("session_shell", parse_docstring=True)
def session_shell_tool(
    runtime: Runtime,
    description: str,
    command: str,
) -> str:
    """Execute a command in a persistent shell session that preserves cwd and env.

    Unlike ``bash`` (stateless — each call starts in the workspace root
    with a clean environment), this tool remembers:

    - **Working directory**: ``cd /some/path`` persists across calls.
    - **Environment variables**: ``export VAR=value`` persists across calls.

    Each thread has its own isolated session.

    Typical usage::

        session_shell("cd backend/packages/harness")
        session_shell("source .venv/bin/activate")
        session_shell("python -m pytest tests/")

    All three commands run in the same directory with the venv active.

    Args:
        description: Explain why you are running this command in short
            words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        command: The command to execute.
    """
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        thread_data = get_thread_data(runtime)

        # --- Load session state ---
        session = _get_session(runtime)
        saved_cwd = session.get("cwd") or _default_cwd(runtime, thread_data)
        saved_env: dict[str, str] = session.get("env", {})

        # --- Local sandbox guards (same as bash_tool) ---
        if is_local_sandbox(runtime):
            if not is_host_bash_allowed():
                return f"Error: {LOCAL_HOST_BASH_DISABLED_MESSAGE}"
            if thread_data:
                validate_local_bash_command_paths(command, thread_data)

        # --- Build the full command ---
        # 1. cd to saved cwd
        # 2. re-export saved env vars
        # 3. run user command
        # 4. append cwd tracker
        parts: list[str] = [f'cd "{saved_cwd}"']
        for k, v in saved_env.items():
            parts.append(f'export {k}="{v}"')

        # Replace virtual paths in the user command for local sandbox
        user_cmd = command
        if is_local_sandbox(runtime) and thread_data:
            user_cmd = replace_virtual_paths_in_command(user_cmd, thread_data)

        parts.append(user_cmd)
        # Cwd tracker — always runs, even if user command fails
        parts.append(f'echo "{_CWD_MARKER}$(pwd)"')

        full_cmd = "; ".join(parts)
        output = execute_sandbox_command(runtime, sandbox, full_cmd)

        # --- Parse new cwd from output ---
        new_cwd, clean_output = _parse_cwd_from_output(output)
        if not new_cwd:
            new_cwd = saved_cwd  # keep old if marker was missing

        # --- Parse new env vars from user command ---
        new_env = dict(saved_env)
        new_exports = _parse_exports(command)
        new_env.update(new_exports)
        # Prune: keep only the most recent _MAX_TRACKED_ENV entries
        if len(new_env) > _MAX_TRACKED_ENV:
            # Keep the newest entries (insertion order in Python 3.7+)
            keys = list(new_env.keys())
            for old_key in keys[:-_MAX_TRACKED_ENV]:
                del new_env[old_key]

        # --- Save session state ---
        _save_session(runtime, {"cwd": new_cwd, "env": new_env})

        # --- Mask local paths and truncate ---
        if is_local_sandbox(runtime) and thread_data:
            clean_output = mask_local_paths_in_output(clean_output, thread_data)
            new_cwd_display = mask_local_paths_in_output(new_cwd, thread_data)
        else:
            new_cwd_display = new_cwd

        # Determine output truncation limit
        try:
            from kkoclaw.config.app_config import get_app_config

            sandbox_cfg = get_app_config().sandbox
            max_chars = sandbox_cfg.bash_output_max_chars if sandbox_cfg else _DEFAULT_OUTPUT_MAX
        except Exception:
            max_chars = _DEFAULT_OUTPUT_MAX

        clean_output = _truncate_bash_output(clean_output, max_chars)

        # Append session info
        env_display = ""
        if new_env:
            env_keys = ", ".join(sorted(new_env.keys()))
            env_display = f"  (env: {env_keys})"

        result = clean_output.rstrip()
        if result:
            result += f"\n(session cwd: {new_cwd_display}){env_display}"
        else:
            result = f"(no output)\n(session cwd: {new_cwd_display}){env_display}"

        return result
    except SandboxError as e:
        return f"Error: {e}"
    except PermissionError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: Unexpected error in session shell: {_sanitize_error(e, runtime)}"


__all__ = ["session_shell_tool"]
