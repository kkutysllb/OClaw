"""Tests that InjectMiddleware is registered in the lead_agent chain."""
from langchain_core.runnables import RunnableConfig

from kkoclaw.agents.middlewares.inject_middleware import InjectMiddleware
from kkoclaw.agents.middlewares.clarification_middleware import ClarificationMiddleware
from kkoclaw.agents.lead_agent.agent import _build_middlewares
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
