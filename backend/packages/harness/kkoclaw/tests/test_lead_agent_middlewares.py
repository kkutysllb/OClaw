"""Tests that InjectMiddleware is registered in the lead_agent chain."""

from langchain_core.runnables import RunnableConfig

from kkoclaw.agents.lead_agent.agent import _build_middlewares
from kkoclaw.agents.middlewares.clarification_middleware import ClarificationMiddleware
from kkoclaw.agents.middlewares.inject_middleware import InjectMiddleware
from kkoclaw.config import get_app_config


def _build():
    cfg = RunnableConfig(configurable={})
    return _build_middlewares(cfg, model_name=None, app_config=get_app_config())


def test_inject_middleware_registered():
    """_build_middlewares 必须包含 InjectMiddleware 实例。"""
    middlewares = _build()
    types = [type(m) for m in middlewares]
    assert InjectMiddleware in types, f"InjectMiddleware missing from chain: {types}"


def test_inject_middleware_before_clarification():
    """InjectMiddleware 必须在 ClarificationMiddleware 之前（后者必须最后）。"""
    middlewares = _build()
    inject_idx = next(i for i, m in enumerate(middlewares) if isinstance(m, InjectMiddleware))
    clarify_idx = next(i for i, m in enumerate(middlewares) if isinstance(m, ClarificationMiddleware))
    assert inject_idx < clarify_idx, "InjectMiddleware must come before ClarificationMiddleware"


# ── Canonical merged middleware chain (deer-flow resync Batch 3) ───────────


def test_clarification_always_last():
    middlewares = _build()
    assert isinstance(middlewares[-1], ClarificationMiddleware)


def test_inject_before_clarification():
    middlewares = _build()
    names = [type(m).__name__ for m in middlewares]
    assert names.index("InjectMiddleware") < names.index("ClarificationMiddleware")


def test_upstream_middlewares_present_when_enabled():
    """With engine.upstream_middlewares=True (default), the importable upstream
    middlewares gated only by that flag are in the chain.

    The 5 asserted here are gated solely by ``engine.upstream_middlewares``
    (config.yaml default True). ``LoopDetectionMiddleware`` is additionally
    gated by ``loop_detection.enabled`` (class default True), so it is asserted
    separately. ``TokenBudgetMiddleware`` / ``ToolProgressMiddleware`` are
    gated by flags that default OFF, so they are NOT asserted here.
    """
    middlewares = _build()
    types = set(type(m).__name__ for m in middlewares)
    # gated only by engine.upstream_middlewares
    assert "SystemMessageCoalescingMiddleware" in types
    assert "TerminalResponseMiddleware" in types
    assert "InputSanitizationMiddleware" in types
    assert "ToolResultSanitizationMiddleware" in types
    assert "DurableContextMiddleware" in types
    assert "McpRoutingMiddleware" in types


def test_loop_detection_present_when_enabled():
    """loop_detection.enabled defaults to True, so LoopDetectionMiddleware is wired."""
    middlewares = _build()
    types = set(type(m).__name__ for m in middlewares)
    assert "LoopDetectionMiddleware" in types


def test_token_budget_and_tool_progress_not_wired_by_default():
    """token_budget.enabled / tool_progress.enabled default to False, so these
    are NOT wired unless their per-middleware flag is turned on."""
    middlewares = _build()
    types = set(type(m).__name__ for m in middlewares)
    assert "TokenBudgetMiddleware" not in types
    assert "ToolProgressMiddleware" not in types
