"""Batch 7 import smoke tests.

Verifies that the ported upstream modules import cleanly. Providers behind an
optional third-party dependency use ``pytest.importorskip`` so the suite stays
green in environments where that dependency is not installed; this records
exactly which providers are importable now versus deferred.
"""

from __future__ import annotations

import importlib

import pytest

# ---------------------------------------------------------------------------
# Sandbox helpers (stdlib only) — must always import.
# ---------------------------------------------------------------------------


def test_sandbox_env_policy_imports() -> None:
    mod = importlib.import_module("kkoclaw.sandbox.env_policy")
    assert hasattr(mod, "build_sandbox_env")
    assert hasattr(mod, "is_blocked_env_name")


def test_sandbox_path_patterns_imports() -> None:
    mod = importlib.import_module("kkoclaw.sandbox.path_patterns")
    # Module exposes pattern-matching helpers; just assert it loaded.
    assert mod is not None


# ---------------------------------------------------------------------------
# Community providers — pure stdlib or already-installed deps (langchain,
# httpx, firecrawl are present in the base environment).
# ---------------------------------------------------------------------------


def test_community_brave_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.brave")
    assert hasattr(mod, "web_search_tool")


def test_community_groundroute_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.groundroute")
    assert hasattr(mod, "web_search_tool")


def test_community_searxng_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.searxng")
    assert hasattr(mod, "web_search_tool")


def test_community_crawl4ai_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.crawl4ai")
    assert hasattr(mod, "Crawl4AiClient")


def test_community_browserless_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.browserless")
    assert hasattr(mod, "BrowserlessClient")


def test_community_fastcrw_imports() -> None:
    # fastcrw is a single-file package (tools.py) — no __init__.py in upstream.
    mod = importlib.import_module("kkoclaw.community.fastcrw.tools")
    assert mod is not None


def test_community_url_safety_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.url_safety")
    assert hasattr(mod, "validate_public_http_url")


def test_community_warm_pool_lifecycle_imports() -> None:
    mod = importlib.import_module("kkoclaw.community.warm_pool_lifecycle")
    assert mod is not None


# ---------------------------------------------------------------------------
# Community providers behind OPTIONAL deps — deferred via importorskip.
# ---------------------------------------------------------------------------


def test_community_aio_sandbox_imports() -> None:
    # Requires the optional `agent_sandbox` SDK.
    pytest.importorskip("agent_sandbox")
    mod = importlib.import_module("kkoclaw.community.aio_sandbox")
    assert hasattr(mod, "AioSandboxProvider")


def test_community_e2b_sandbox_imports() -> None:
    # Requires the optional `e2b_code_interpreter` SDK.
    pytest.importorskip("e2b_code_interpreter")
    mod = importlib.import_module("kkoclaw.community.e2b_sandbox")
    assert hasattr(mod, "E2BSandboxProvider")


def test_community_boxlite_imports() -> None:
    # boxlite itself is lazy-imported, but importing the provider may pull in
    # other optional bits; guard on the runtime dep.
    pytest.importorskip("boxlite")
    mod = importlib.import_module("kkoclaw.community.boxlite")
    assert hasattr(mod, "BoxliteProvider")


# ---------------------------------------------------------------------------
# scheduler + workspace_changes — stdlib + croniter (installed).
# ---------------------------------------------------------------------------


def test_scheduler_imports() -> None:
    # croniter is a declared dependency; guard defensively anyway.
    pytest.importorskip("croniter")
    mod = importlib.import_module("kkoclaw.scheduler")
    assert hasattr(mod, "normalize_cron_expression")
    assert hasattr(mod, "next_run_at")


def test_workspace_changes_imports() -> None:
    mod = importlib.import_module("kkoclaw.workspace_changes")
    assert hasattr(mod, "compare_snapshots")
    assert hasattr(mod, "scan_workspace_roots")


# ---------------------------------------------------------------------------
# TUI — the submodules need `textual` + `rich` (optional).
# ---------------------------------------------------------------------------


def test_tui_package_imports() -> None:
    # tui/__init__.py is a pure docstring — always importable.
    mod = importlib.import_module("kkoclaw.tui")
    assert mod is not None


def test_tui_app_imports() -> None:
    # The full TUI stack needs textual + rich.
    pytest.importorskip("textual")
    pytest.importorskip("rich")
    importlib.import_module("kkoclaw.tui.app")
