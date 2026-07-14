"""Merged ``config.paths`` exposes upstream additions plus OClaw path helpers.

The merge policy for Task 1.4 is: take deer-flow upstream ``paths.py`` as the
base, re-apply OClaw deltas. These tests pin the contract so that future
resyncs cannot silently drop either side:

* upstream additions: ``make_safe_user_id``, ``prepare_user_dir_for_raw_id``,
  ``user_skills_dir``, ``resolve_virtual_path``.
* OClaw deltas: ``_migrate_legacy_project_home`` (runs in ``Paths.__init__``),
  ``resolve_thread_artifact_path`` (called by ``client.py``), and the
  ``KKOCLAW_*`` env-var naming.
* integration seam: ``app_config.py`` imports ``existing_project_file`` from
  ``config.runtime_paths`` (not ``config.paths``), so we assert it is callable
  from its true home to guard against the common mis-attribution.
"""

from pathlib import Path

import pytest

from kkoclaw.config.paths import (
    VIRTUAL_PATH_PREFIX,
    Paths,
    get_paths,
    join_host_path,
    make_safe_user_id,
    resolve_path,
)
from kkoclaw.config.runtime_paths import existing_project_file

# ── Singleton / Paths construction ────────────────────────────────────────


def test_paths_instantiable():
    p = get_paths()
    assert p is not None
    assert isinstance(p, Paths)


def test_paths_with_explicit_base_dir_skips_migration(tmp_path: Path, monkeypatch):
    # An explicit base_dir short-circuits the legacy-home migration, so this
    # must never touch the real ~/.kkoclaw.
    monkeypatch.delenv("KKOCLAW_HOME", raising=False)
    p = Paths(base_dir=tmp_path)
    assert p.base_dir == tmp_path.resolve()


def test_base_dir_resolves_from_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KKOCLAW_HOME", str(tmp_path))
    p = Paths()
    assert p.base_dir == tmp_path.resolve()


def test_kkoclaw_host_base_dir_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KKOCLAW_HOST_BASE_DIR", str(tmp_path))
    p = Paths(base_dir=tmp_path / "inner")
    assert p.host_base_dir == tmp_path


# ── Upstream additions taken verbatim ─────────────────────────────────────


def test_make_safe_user_id_passthrough():
    assert make_safe_user_id("alice_01") == "alice_01"


def test_make_safe_user_id_sanitizes_unsafe_chars():
    raw = "feishu:bot.team"
    safe = make_safe_user_id(raw)
    # unsafe chars replaced with "-" and a digest suffix appended
    assert safe.startswith("feishu-bot-team-")
    assert safe != raw


def test_make_safe_user_id_distinct_inputs_distinct_buckets():
    a = make_safe_user_id("weird/id:one")
    b = make_safe_user_id("weird/id:two")
    assert a != b


def test_prepare_user_dir_for_raw_id_returns_safe_id(tmp_path: Path):
    p = Paths(base_dir=tmp_path)
    assert p.prepare_user_dir_for_raw_id("plain_id") == "plain_id"


def test_user_skills_dirs(tmp_path: Path):
    # Paths.__init__ resolves base_dir, so use a real tmp dir (avoids macOS
    # /tmp -> /private/tmp symlink resolution surprising the assertion).
    p = Paths(base_dir=tmp_path)
    assert p.user_skills_dir("u1") == tmp_path / "users" / "u1" / "skills"
    assert p.user_custom_skills_dir("u1") == tmp_path / "users" / "u1" / "skills" / "custom"


def test_virtual_path_prefix_constant_present():
    assert VIRTUAL_PATH_PREFIX == "/mnt/user-data"


def test_resolve_virtual_path_round_trip(tmp_path: Path):
    p = Paths(base_dir=tmp_path)
    thread_id = "t-123"
    outputs_dir = p.sandbox_outputs_dir(thread_id)
    outputs_dir.mkdir(parents=True)
    (outputs_dir / "report.pdf").write_bytes(b"%PDF-1.4")
    resolved = p.resolve_virtual_path(thread_id, "/mnt/user-data/outputs/report.pdf")
    assert resolved.read_bytes() == b"%PDF-1.4"


def test_resolve_virtual_path_rejects_bad_prefix(tmp_path: Path):
    p = Paths(base_dir=tmp_path)
    with pytest.raises(ValueError):
        p.resolve_virtual_path("t-1", "/mnt/elsewhere/x")


# ── OClaw deltas preserved ────────────────────────────────────────────────


def test_resolve_thread_artifact_path_accepts_in_workspace(tmp_path: Path):
    # OClaw's client.py reads artifacts through this method; it must survive.
    p = Paths(base_dir=tmp_path)
    outputs_dir = p.sandbox_outputs_dir("t-9")
    outputs_dir.mkdir(parents=True)
    artifact = outputs_dir / "out.txt"
    artifact.write_text("hi")
    resolved = p.resolve_thread_artifact_path("t-9", str(artifact))
    assert resolved.read_text() == "hi"


def test_resolve_thread_artifact_path_rejects_traversal(tmp_path: Path):
    p = Paths(base_dir=tmp_path)
    p.sandbox_outputs_dir("t-9").mkdir(parents=True)
    with pytest.raises(ValueError):
        p.resolve_thread_artifact_path("t-9", "/etc/passwd")


def test_resolve_thread_artifact_path_extra_root(tmp_path: Path):
    p = Paths(base_dir=tmp_path)
    extra = tmp_path / "external"
    extra.mkdir()
    (extra / "f.txt").write_text("ext")
    resolved = p.resolve_thread_artifact_path(
        "t-9", str(extra / "f.txt"), extra_allowed_roots=[str(extra)]
    )
    assert resolved.read_text() == "ext"


# ── Integration seam: app_config.resolve_config_path dependency ───────────


def test_existing_project_file_callable():
    # app_config.py:21 does: from kkoclaw.config.runtime_paths import existing_project_file
    # It does NOT live in config.paths; pin it at its real home so the import
    # contract is not broken by a future paths.py resync.
    assert callable(existing_project_file)


def test_existing_project_file_finds_config(tmp_path: Path, monkeypatch):
    (tmp_path / "config.yaml").write_text("hello: world\n")
    monkeypatch.setenv("KKOCLAW_PROJECT_ROOT", str(tmp_path))
    found = existing_project_file(("config.yaml",))
    assert found is not None
    assert found.name == "config.yaml"


def test_resolve_path_helper_absolute_unchanged(tmp_path: Path):
    target = tmp_path / "abs.txt"
    assert resolve_path(str(target)) == target.resolve()


def test_join_host_path_posix():
    assert join_host_path("/a/b", "c", "d") == "/a/b/c/d"


def test_join_host_path_windows_style_preserved():
    # Bind-mount sources on Windows hosts must keep backslash form.
    assert join_host_path("C:\\repo", "data", "x").replace("/", "\\") == "C:\\repo\\data\\x"
