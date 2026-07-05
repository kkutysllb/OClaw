"""Unified extensions configuration for MCP servers and skills."""

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from kkoclaw.config.runtime_paths import existing_project_file


class McpOAuthConfig(BaseModel):
    """OAuth configuration for an MCP server (HTTP/SSE transports)."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(
        default="client_credentials",
        description="OAuth grant type",
    )
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token (for refresh_token grant)")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience (provider-specific)")
    token_field: str = Field(default="access_token", description="Field name containing access token in token response")
    token_type_field: str = Field(default="token_type", description="Field name containing token type in token response")
    expires_in_field: str = Field(default="expires_in", description="Field name containing expiry (seconds) in token response")
    default_token_type: str = Field(default="Bearer", description="Default token type when missing in token response")
    refresh_skew_seconds: int = Field(default=60, description="Refresh token this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")
    model_config = ConfigDict(extra="allow")


class McpServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', 'http', or 'streamable-http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfig | None = Field(default=None, description="OAuth configuration (for sse or http type)")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")
    model_config = ConfigDict(extra="allow")


class SkillStateConfig(BaseModel):
    """Configuration for a single skill's state."""

    enabled: bool = Field(default=True, description="Whether this skill is enabled")


# ---------------------------------------------------------------------------
# Work mode skill contracts
# ---------------------------------------------------------------------------
#
# Work modes are first-class presets (task / coding) that control which skills
# are available to the Lead Agent. A small set of "locked" core skills cannot
# be disabled or removed from any mode — they protect the agent's self-bootstrap
# and skill-discovery capabilities.
#
# The contract is intentionally backward-compatible: an ``ExtensionsConfig``
# with no work-mode input still parses and defaults to the builtin task/coding
# presets, so existing ``extensions_config.json`` files keep working unchanged.

#: Core skill ids that cannot be disabled or removed from any work mode.
#: These protect the agent's self-bootstrap, skill-discovery, and skill-creation
#: capabilities — disabling them would leave the system unable to evolve.
DEFAULT_LOCKED_SKILL_IDS: tuple[str, ...] = (
    "bootstrap",
    "find-skills",
    "skill-creator",
)

#: The default work mode id used when none is specified.
DEFAULT_WORK_MODE_ID = "task"


class WorkModeConfig(BaseModel):
    """Configuration for a single work mode (e.g. task, coding).

    A work mode defines a named preset of skills. Built-in modes ship with
    the system; users can add custom modes (future work). ``default_skill_ids``
    lists the skills active in this mode *before* per-mode overrides are
    applied. Locked skills are always implicitly included and need not be
    repeated here.
    """

    id: str = Field(description="Stable work-mode identifier (e.g. 'task', 'coding')")
    name: str = Field(default="", description="Human-readable display name")
    description: str = Field(default="", description="What this mode is for")
    builtin: bool = Field(default=False, description="Whether this is a shipped built-in mode")
    editable: bool = Field(default=True, description="Whether the user can add/remove skills from this mode")
    default_skill_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Skills active in this mode before overrides. Locked skills are implicit.",
    )
    lead_agent_name: str = Field(
        default="",
        description="该模式绑定的 lead agent 显示名（注入到 prompt 让模型知道自己的角色）",
    )
    orchestration_hint: str = Field(
        default="",
        description="该模式的任务编排指导（注入到 prompt 影响模型的风格/决策）",
    )
    focus_areas: tuple[str, ...] = Field(
        default_factory=tuple,
        description="该模式的关注领域标签（注入到 prompt + 前端展示）",
    )
    icon: str = Field(
        default="Bot",
        description="Lucide 图标名或 emoji,前端侧边栏渲染用。内置模式有硬编码默认值。",
    )


class WorkModesConfig(BaseModel):
    """Top-level container for all work modes."""

    default_mode_id: str = Field(
        default=DEFAULT_WORK_MODE_ID,
        description="Work-mode id used when the caller does not specify one.",
    )
    modes: dict[str, WorkModeConfig] = Field(
        default_factory=dict,
        description="Map of work-mode id → config",
    )


class ModeSkillOverridesConfig(BaseModel):
    """Per-mode skill additions/removals on top of ``default_skill_ids``.

    - ``added_skill_ids``: extra skills to activate in this mode.
    - ``removed_skill_ids``: skills to deactivate in this mode. Locked skills
      listed here are ignored (locked always wins).
    """

    added_skill_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Skills to add to this mode beyond its defaults",
    )
    removed_skill_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Skills to remove from this mode (locked skills are protected)",
    )


def _default_builtin_work_modes() -> WorkModesConfig:
    """Build the default shipped work-modes config (task + coding)."""
    return WorkModesConfig(
        default_mode_id=DEFAULT_WORK_MODE_ID,
        modes={
            "task": WorkModeConfig(
                id="task",
                name="日常办公",
                description="General-purpose office mode — the default Lead Agent experience.",
                builtin=True,
                editable=True,
                # task mode is the permissive default: no skill restrictions
                # beyond the locked core. All enabled public skills are available.
                default_skill_ids=(),
                lead_agent_name="KKOCLAW 1.0",
                orchestration_hint=(
                    "You are in **日常办公 (Office)** mode. Favor research, document creation, "
                    "data analysis, and workflow automation tasks. When a task spans multiple "
                    "domains, decompose it into subtasks and orchestrate parallel subagents "
                    "for research-heavy work. Prefer structured outputs (tables, docs, slides) "
                    "and cite sources when available."
                ),
                focus_areas=("research", "documents", "analysis", "automation"),
                icon="CheckSquare",
            ),
            "coding": WorkModeConfig(
                id="coding",
                name="编程",
                description="Software-engineering mode with coding-focused skills.",
                builtin=True,
                editable=True,
                # coding mode will be refined in later tasks; for now it mirrors
                # task so the contract is forward-compatible without changing
                # runtime behavior.
                default_skill_ids=(),
                lead_agent_name="Coding Agent",
                orchestration_hint=(
                    "You are in **编程 (Coding)** mode. Favor code reading, surgical edits, "
                    "test-driven development, and git hygiene. ALWAYS explore the codebase "
                    "before editing, run tests after changes, and follow the project's "
                    "existing conventions. When a task spans multiple modules, decompose it "
                    "into parallel subagents for exploration, but keep edits surgical and "
                    "sequenced to avoid merge conflicts."
                ),
                focus_areas=("code", "debug", "refactor", "testing"),
                icon="Code2",
            ),
        },
    )


class ExtensionsConfig(BaseModel):
    """Unified configuration for MCP servers, skills, and work modes."""

    mcp_servers: dict[str, McpServerConfig] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
        alias="mcpServers",
    )
    skills: dict[str, SkillStateConfig] = Field(
        default_factory=dict,
        description="Map of skill name to state configuration",
    )
    locked_skill_ids: tuple[str, ...] = Field(
        default=DEFAULT_LOCKED_SKILL_IDS,
        description="Core skill ids that cannot be disabled or removed from any work mode.",
    )
    work_modes: WorkModesConfig = Field(
        default_factory=_default_builtin_work_modes,
        description="Work-mode presets controlling per-mode skill availability",
    )
    mode_skill_overrides: dict[str, ModeSkillOverridesConfig] = Field(
        default_factory=dict,
        description="Per-mode skill additions/removals keyed by work-mode id",
    )
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def resolve_config_path(cls, config_path: str | None = None) -> Path | None:
        """Resolve the extensions config file path.

        Priority:
        1. If provided `config_path` argument, use it.
        2. If provided `KKOCLAW_EXTENSIONS_CONFIG_PATH` environment variable, use it.
        3. Otherwise, search the caller project root for `extensions_config.json`, then `mcp_config.json`.
        4. For backward compatibility, also search legacy backend/repository-root defaults.
        5. If not found, return None (extensions are optional).

        Args:
            config_path: Optional path to extensions config file.

        Resolution order:
            1. If provided `config_path` argument, use it.
            2. If provided `KKOCLAW_EXTENSIONS_CONFIG_PATH` environment variable, use it.
            3. Otherwise, search the caller project root for
               `extensions_config.json`, then legacy `mcp_config.json`.
            4. Finally, search backend/repository-root defaults for monorepo compatibility.

        Returns:
            Path to the extensions config file if found, otherwise None.
        """
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Extensions config file specified by param `config_path` not found at {path}")
            return path
        elif os.getenv("KKOCLAW_EXTENSIONS_CONFIG_PATH"):
            path = Path(os.getenv("KKOCLAW_EXTENSIONS_CONFIG_PATH"))
            if not path.exists():
                raise FileNotFoundError(f"Extensions config file specified by environment variable `KKOCLAW_EXTENSIONS_CONFIG_PATH` not found at {path}")
            return path
        else:
            project_config = existing_project_file(("extensions_config.json", "mcp_config.json"))
            if project_config is not None:
                return project_config

            backend_dir = Path(__file__).resolve().parents[4]
            repo_root = backend_dir.parent
            for path in (
                backend_dir / "extensions_config.json",
                repo_root / "extensions_config.json",
                backend_dir / "mcp_config.json",
                repo_root / "mcp_config.json",
            ):
                if path.exists():
                    return path

            # Extensions are optional, so return None if not found
            return None

    @classmethod
    def from_file(cls, config_path: str | None = None) -> "ExtensionsConfig":
        """Load extensions config from JSON file.

        See `resolve_config_path` for more details.

        Args:
            config_path: Path to the extensions config file.

        Returns:
            ExtensionsConfig: The loaded config, or empty config if file not found.
        """
        resolved_path = cls.resolve_config_path(config_path)
        if resolved_path is None:
            # Return empty config if extensions config file is not found
            return cls(mcp_servers={}, skills={})

        try:
            with open(resolved_path, encoding="utf-8") as f:
                config_data = json.load(f)
            cls.resolve_env_variables(config_data)
            return cls.model_validate(config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Extensions config file at {resolved_path} is not valid JSON: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load extensions config from {resolved_path}: {e}") from e

    @classmethod
    def resolve_env_variables(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Recursively resolve environment variables in the config.

        Environment variables are resolved using the `os.getenv` function. Example: $OPENAI_API_KEY

        Args:
            config: The config to resolve environment variables in.

        Returns:
            The config with environment variables resolved.
        """
        for key, value in config.items():
            if isinstance(value, str):
                if value.startswith("$"):
                    env_value = os.getenv(value[1:])
                    if env_value is None:
                        # Unresolved placeholder — store empty string so downstream
                        # consumers (e.g. MCP servers) don't receive the literal "$VAR"
                        # token as an actual environment value.
                        config[key] = ""
                    else:
                        config[key] = env_value
                else:
                    config[key] = value
            elif isinstance(value, dict):
                config[key] = cls.resolve_env_variables(value)
            elif isinstance(value, list):
                config[key] = [cls.resolve_env_variables(item) if isinstance(item, dict) else item for item in value]
        return config

    def get_enabled_mcp_servers(self) -> dict[str, McpServerConfig]:
        """Get only the enabled MCP servers.

        Returns:
            Dictionary of enabled MCP servers.
        """
        return {name: config for name, config in self.mcp_servers.items() if config.enabled}

    def is_skill_enabled(self, skill_name: str, skill_category: str) -> bool:
        """Check if a skill is enabled.

        Args:
            skill_name: Name of the skill
            skill_category: Category of the skill

        Returns:
            True if enabled, False otherwise
        """
        skill_config = self.skills.get(skill_name)
        if skill_config is None:
            # Default to enable for builtin & custom skills. "public" is
            # accepted as a legacy alias for "builtin" (pre-migration).
            return skill_category in ("builtin", "public", "custom")
        return skill_config.enabled

    def save(self, config_path: str | Path | None = None) -> Path:
        """Serialize the full config (all fields) to a JSON file.

        This replaces the manual dict-construction previously used by individual
        route handlers (which silently dropped ``work_modes``, ``locked_skill_ids``,
        and ``mode_skill_overrides`` on every write).

        Args:
            config_path: Target file path. If None, resolves via
                :meth:`resolve_config_path`, falling back to a repository-root
                ``extensions_config.json``.

        Returns:
            The resolved :class:`~pathlib.Path` that was written.
        """
        if config_path is not None:
            resolved_path = Path(config_path)
        else:
            resolved_path = self.resolve_config_path()
            if resolved_path is None:
                resolved_path = Path.cwd().parent / "extensions_config.json"

        data = self.model_dump(by_alias=True, exclude_none=True, mode="json")
        with open(resolved_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return resolved_path


_extensions_config: ExtensionsConfig | None = None


def get_extensions_config() -> ExtensionsConfig:
    """Get the extensions config instance.

    Returns a cached singleton instance. Use `reload_extensions_config()` to reload
    from file, or `reset_extensions_config()` to clear the cache.

    Returns:
        The cached ExtensionsConfig instance.
    """
    global _extensions_config
    if _extensions_config is None:
        _extensions_config = ExtensionsConfig.from_file()
    return _extensions_config


def reload_extensions_config(config_path: str | None = None) -> ExtensionsConfig:
    """Reload the extensions config from file and update the cached instance.

    This is useful when the config file has been modified and you want
    to pick up the changes without restarting the application.

    Args:
        config_path: Optional path to extensions config file. If not provided,
                     uses the default resolution strategy.

    Returns:
        The newly loaded ExtensionsConfig instance.
    """
    global _extensions_config
    _extensions_config = ExtensionsConfig.from_file(config_path)
    return _extensions_config


def reset_extensions_config() -> None:
    """Reset the cached extensions config instance.

    This clears the singleton cache, causing the next call to
    `get_extensions_config()` to reload from file. Useful for testing
    or when switching between different configurations.
    """
    global _extensions_config
    _extensions_config = None


def set_extensions_config(config: ExtensionsConfig) -> None:
    """Set a custom extensions config instance.

    This allows injecting a custom or mock config for testing purposes.

    Args:
        config: The ExtensionsConfig instance to use.
    """
    global _extensions_config
    _extensions_config = config
