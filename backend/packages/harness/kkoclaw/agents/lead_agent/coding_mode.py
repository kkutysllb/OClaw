"""Coding-mode runtime helpers for the unified Lead Agent.

Historically the project shipped a separate ``coding_agent`` LangGraph graph.
That graph has been retired — the Lead Agent now serves the coding work mode
directly. This module groups the coding-specific assembly logic (tools,
middlewares, prompt) so :func:`make_lead_agent` can pull them in when
``work_mode_id == "coding"`` without polluting the default office path.

The helpers here are thin orchestrators: the heavy lifting (qiongqi engine,
coding tools, coding skills middleware) still lives in ``coding_core`` and
``tools.coding``. This module just wires them together for the Lead Agent
factory.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from kkoclaw.agents.middlewares.post_edit_verify_middleware import PostEditVerifyMiddleware
from kkoclaw.coding_core.qiongqi import QiongqiEngine

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from kkoclaw.config.app_config import AppConfig

logger = logging.getLogger(__name__)


def get_coding_mode_tools(
    *,
    app_config: AppConfig,
    model_name: str | None,
    subagent_enabled: bool,
) -> list[Any]:
    """Assemble the full tool list for coding mode.

    Combines:
    - Standard tools from config (file, web, bash groups)
    - Coding-specific tools (read_file_range, grep_files, apply_diff, git_*, etc.)
    - Built-in tools (present_file, ask_clarification)

    Coding tools override standard tools of the same name (e.g. the
    coding-optimised ``read_file`` replaces the generic one).
    """
    from kkoclaw.tools import get_available_tools
    from kkoclaw.tools.builtins import ask_clarification_tool, present_file_tool

    tools: list[Any] = []

    # 1. Standard tools — coding mode gets every standard group.
    standard_tools = get_available_tools(
        model_name=model_name,
        subagent_enabled=subagent_enabled,
        app_config=app_config,
    )
    tools.extend(standard_tools)

    # 2. Coding-specific tools — override same-named standard tools.
    try:
        from kkoclaw.tools.coding import get_coding_tools

        coding_tools = get_coding_tools()
        existing_names = {t.name for t in tools}
        for ct in coding_tools:
            if ct.name in existing_names:
                tools = [ct if t.name == ct.name else t for t in tools]
            else:
                tools.append(ct)
        logger.info("Loaded %d coding-specific tools", len(coding_tools))
    except ImportError:
        logger.warning(
            "Coding tools module not available — coding mode will use standard tools only"
        )
    except Exception:
        logger.exception("Failed to load coding tools")

    # 3. Essential built-ins must be present.
    builtin_names = {t.name for t in tools}
    if present_file_tool.name not in builtin_names:
        tools.append(present_file_tool)
    if ask_clarification_tool.name not in builtin_names:
        tools.append(ask_clarification_tool)

    return tools


def build_coding_mode_prompt(
    *,
    qiongqi_engine: QiongqiEngine,
    model_display_name: str | None,
    is_plan_mode: bool,
    subagent_enabled: bool,
    max_concurrent_subagents: int,
) -> str:
    """Build the coding-mode system prompt via the qiongqi engine.

    The qiongqi engine composes the stable coding prompt (project context,
    coding skills, operating principles) with its dynamic context snapshot
    (file tree, git state, etc.).
    """
    stable_prompt = qiongqi_engine.build_stable_system_prompt(
        model_display_name=model_display_name,
        is_plan_mode=is_plan_mode,
        subagent_enabled=subagent_enabled,
        max_concurrent_subagents=max_concurrent_subagents,
    )
    return stable_prompt + qiongqi_engine.build_dynamic_context()


def build_coding_mode_middlewares(
    *,
    qiongqi_engine: QiongqiEngine,
    app_config: AppConfig,
    stable_prompt: str,
    tools: list[Any],
) -> list[Any]:
    """Build the coding-specific middleware chain.

    Returns the middlewares that coding mode injects on top of the Lead
    Agent's standard middleware stack:
    - ``CodingSkillsMiddleware`` + ``CodingToolPolicyMiddleware`` (from the
      qiongqi engine)
    - ``PostEditVerifyMiddleware`` (edit → lint → test reminder loop)
    - ``QiongqiRoiTelemetryMiddleware`` (ROI telemetry)

    The caller is expected to pass this list as ``custom_middlewares`` to
    :func:`lead_agent.agent._build_middlewares` so they land before the
    ClarificationMiddleware tail.
    """
    from kkoclaw.coding_core.roi_telemetry_middleware import QiongqiRoiTelemetryMiddleware

    coding_middlewares: list[Any] = [
        *qiongqi_engine.build_agent_middlewares(),
    ]

    coding_config = getattr(app_config, "coding_agent", None)
    post_edit_verify_enabled = (
        getattr(coding_config, "post_edit_verify_enabled", True) if coding_config else True
    )
    post_edit_verify_mode = (
        getattr(coding_config, "post_edit_verify_mode", "soft") if coding_config else "soft"
    )
    if post_edit_verify_enabled:
        coding_middlewares.append(PostEditVerifyMiddleware(mode=post_edit_verify_mode))

    roi_report = qiongqi_engine.build_roi_report(
        stable_prompt=stable_prompt,
        tools=tools,
        visible_tools=_visible_tools_for_roi(tools, app_config),
    )
    coding_middlewares.append(
        QiongqiRoiTelemetryMiddleware(
            qiongqi_engine,
            report=qiongqi_engine.roi_metadata(roi_report),
        )
    )
    return coding_middlewares


def _visible_tools_for_roi(tools: list[Any], app_config: AppConfig) -> list[Any]:
    """Filter the tool list for ROI reporting.

    When tool-search is enabled, deferred tools are excluded from the
    visible-tools set so the ROI report reflects what the model actually
    sees at bind time.
    """
    if not getattr(getattr(app_config, "tool_search", None), "enabled", False):
        return tools
    try:
        from kkoclaw.tools.builtins.tool_search import get_deferred_registry
    except Exception:
        return tools
    registry = get_deferred_registry()
    if registry is None:
        return tools
    deferred_names = registry.deferred_names
    return [tool for tool in tools if getattr(tool, "name", None) not in deferred_names]


def build_coding_system_prompt_for_metadata(
    *,
    qiongqi_engine: QiongqiEngine,
    model_display_name: str | None,
    is_plan_mode: bool,
    subagent_enabled: bool,
    max_concurrent_subagents: int,
) -> str:
    """Return just the stable coding prompt (without dynamic context).

    Used for ROI metadata reporting where we need the stable portion only.
    """
    return qiongqi_engine.build_stable_system_prompt(
        model_display_name=model_display_name,
        is_plan_mode=is_plan_mode,
        subagent_enabled=subagent_enabled,
        max_concurrent_subagents=max_concurrent_subagents,
    )
