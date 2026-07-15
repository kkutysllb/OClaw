"""The reconciled alembic migration chain runs ``upgrade head`` on a fresh DB
and is idempotent when run against a DB whose tables already exist (the
OClaw ``Base.metadata.create_all`` bootstrap path).

These are the two real-world shapes OClaw's DB can be in when alembic runs:

1. **Fresh / empty DB** (or a brand-new file): alembic applies every revision
   from ``base`` -> ``head``. This exercises the full DDL path of
   ``0001_baseline`` + ``0002``-``0007``.
2. **DB whose baseline tables already exist** (``create_all`` already ran, as
   OClaw's ``persistence/engine.py`` does at init): alembic must NOT raise
   "table already exists". Every ``create_table`` / ``add_column`` is guarded,
   so ``upgrade head`` is a no-op for the parts that already exist.

The chain is linear: single root (``0001_baseline``, down_revision=None),
single head (``0007_work_mode_icon``), no branches or orphans.

Isolation note
--------------

The alembic ``upgrade`` is run in a **child process** (``uv run python``) rather
than in-process via ``alembic.command.upgrade``. ``env.py`` calls
``logging.config.fileConfig(...)``, whose default
``disable_existing_loggers=True`` would permanently reconfigure the test
process's logging and break unrelated ``caplog``-based tests that run later in
the session. A child process keeps that side effect scoped to the child.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "persistence" / "migrations"
_ALEMBIC_INI = _MIGRATIONS_DIR / "alembic.ini"

_BASELINE_TABLES = [
    "channel_connections",
    "channel_conversations",
    "channel_credentials",
    "channel_oauth_states",
    "feedback",
    "run_events",
    "runs",
    "scheduled_tasks",
    "scheduled_task_runs",
    "threads_meta",
    "user_mcp_servers",
    "user_work_modes",
    "users",
]


def _run_alembic(db_url: str, *alembic_args: str) -> None:
    """Run an alembic command against ``db_url`` in an isolated child process.

    The child imports alembic and calls ``command.upgrade``/``command.stamp``
    with the ini URL overridden to ``db_url``. ``env.py`` reads the URL from
    the ini main option, so the override takes effect.
    """
    method = alembic_args[0]
    rest = ", ".join(repr(a) for a in alembic_args[1:])
    call_args = f"cfg, {rest}" if rest else "cfg"
    snippet = f"from alembic import command\nfrom alembic.config import Config\ncfg = Config({str(_ALEMBIC_INI)!r})\ncfg.set_main_option('sqlalchemy.url', {db_url!r})\ncommand.{method}({call_args})\n"
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[4]),  # backend/ (package root on sys.path)
    )
    if result.returncode != 0:
        raise AssertionError(f"alembic {' '.join(alembic_args)!r} failed (rc={result.returncode}):\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}")


def _fresh_sqlite() -> tuple[str, str]:
    db_path = tempfile.mktemp(suffix=".db")
    return f"sqlite+aiosqlite:///{db_path}", db_path


def _tables(db_path: str) -> set[str]:
    return set(inspect(create_engine(f"sqlite:///{db_path}")).get_table_names())


def _columns(db_path: str, table: str) -> set[str]:
    return {c["name"] for c in inspect(create_engine(f"sqlite:///{db_path}")).get_columns(table)}


def test_upgrade_head_on_fresh_db() -> None:
    """Fresh DB: ``upgrade head`` applies the whole chain and creates all tables."""
    url, db_path = _fresh_sqlite()
    try:
        _run_alembic(url, "upgrade", "head")

        tables = _tables(db_path)
        assert "runs" in tables
        assert "users" in tables
        assert "threads_meta" in tables
        assert "channel_connections" in tables
        # 0002 added token_usage_by_model on runs (0001 also has it; either way it exists)
        assert "token_usage_by_model" in _columns(db_path, "runs")
        # 0003 tables
        assert "scheduled_tasks" in tables
        assert "scheduled_task_runs" in tables
        # 0005/0006 tables
        assert "user_mcp_servers" in tables
        assert "user_work_modes" in tables
        # 0007 column
        assert "icon" in _columns(db_path, "user_work_modes")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_upgrade_head_is_idempotent_when_tables_already_exist() -> None:
    """Existing-DB path: ``create_all``-shaped DB then ``upgrade head`` is a no-op.

    This is the OClaw bootstrap shape (``persistence/engine.py`` runs
    ``Base.metadata.create_all`` at init). Every migration must guard its DDL
    so re-running the chain against an already-populated DB does not raise
    "table/column/index already exists".
    """
    url, db_path = _fresh_sqlite()
    try:
        # Seed a DB whose tables already exist (alembic creates them once).
        _run_alembic(url, "upgrade", "head")
        # Stamp back to base so alembic re-runs every revision against the
        # already-populated DB. The guarded upgrade()s must all no-op.
        _run_alembic(url, "stamp", "base")
        # No exception => idempotency holds.
        _run_alembic(url, "upgrade", "head")

        # Still at head, tables intact.
        tables = _tables(db_path)
        for t in _BASELINE_TABLES:
            assert t in tables, f"{t} missing after idempotent re-upgrade"
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_chain_is_linear_single_head_single_base() -> None:
    """Structural check: the migration graph is a single linear chain."""
    from alembic.script import ScriptDirectory

    # ScriptDirectory only inspects the version files; no env.py / fileConfig side effects.
    sd = ScriptDirectory(str(_MIGRATIONS_DIR))
    heads = sd.get_heads()
    bases = sd.get_bases()
    assert len(heads) == 1, f"expected single head, got {heads}"
    assert len(bases) == 1, f"expected single base, got {bases}"
    assert heads[0] == "0007_work_mode_icon"
    assert bases[0] == "0001_baseline"

    revs = {r.revision: r for r in sd.walk_revisions()}
    down_targets = [r.down_revision for r in revs.values() if r.down_revision is not None]
    assert len(down_targets) == len(set(down_targets)), "a revision is pointed to by more than one child (branch)"
    for target in down_targets:
        assert target in revs, f"orphan: down_revision {target!r} has no matching revision"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
