"""Ported bootstrap + migration helpers import cleanly."""


def test_bootstrap_imports():
    from kkoclaw.persistence import bootstrap
    assert bootstrap is not None


def test_migration_helpers_import():
    from kkoclaw.persistence.migrations import _env_filters, _helpers
    assert _env_filters is not None
    assert _helpers is not None
