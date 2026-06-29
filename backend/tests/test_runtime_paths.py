"""Runtime path policy tests for standalone harness usage."""

from pathlib import Path

import pytest
import yaml

from kkoclaw.config import app_config as app_config_module
from kkoclaw.config import extensions_config as extensions_config_module
from kkoclaw.config.app_config import AppConfig
from kkoclaw.config.extensions_config import ExtensionsConfig
from kkoclaw.config.paths import Paths
from kkoclaw.config.runtime_paths import project_root, runtime_home
from kkoclaw.config.skills_config import SkillsConfig
from kkoclaw.skills.storage import get_or_new_skill_storage


def _clear_path_env(monkeypatch):
    for name in (
        "KKOCLAW_CONFIG_PATH",
        "KKOCLAW_EXTENSIONS_CONFIG_PATH",
        "KKOCLAW_HOME",
        "KKOCLAW_PROJECT_ROOT",
        "KKOCLAW_SKILLS_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_runtime_paths_resolve_from_user_home(tmp_path: Path, monkeypatch):
    """Without ``KKOCLAW_HOME`` or a legacy project fallback, the runtime
    home resolves to the user home directory (``~/.kkoclaw``).

    Note: this is intentionally a sibling of (not a replacement for) the
    legacy monorepo fallback test below — the new default keeps user data
    out of the working tree, while the old behaviour is preserved as a
    one-shot migration in :class:`kkoclaw.config.paths.Paths`.
    """
    _clear_path_env(monkeypatch)
    # No legacy data anywhere → no migration; pure home-dir fallback.
    monkeypatch.chdir(tmp_path)
    # Redirect Path.home() so the test does not touch the real $HOME.
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))

    assert Paths().base_dir == tmp_path / ".kkoclaw"
    assert runtime_home() == tmp_path / ".kkoclaw"


def test_kkoclaw_project_root_overrides_current_directory(tmp_path: Path, monkeypatch):
    _clear_path_env(monkeypatch)
    project_root = tmp_path / "project"
    other_cwd = tmp_path / "other"
    project_root.mkdir()
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    monkeypatch.setenv("KKOCLAW_PROJECT_ROOT", str(project_root))
    # Redirect Path.home() away from real $HOME so migration logic is
    # deterministic and the assertion below is stable.
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))

    (project_root / "config.yaml").write_text(
        yaml.safe_dump({"sandbox": {"use": "kkoclaw.sandbox.local:LocalSandboxProvider"}}),
        encoding="utf-8",
    )
    (project_root / "mcp_config.json").write_text('{"mcpServers": {}, "skills": {}}', encoding="utf-8")

    assert AppConfig.resolve_config_path() == project_root / "config.yaml"
    assert ExtensionsConfig.resolve_config_path() == project_root / "mcp_config.json"
    assert SkillsConfig(path="custom-skills").get_skills_path() == project_root / "custom-skills"
    # Paths.base_dir is now driven by runtime_home() / Path.home() — see
    # test_default_runtime_paths_resolve_from_user_home for that contract.


def test_kkoclaw_skills_path_overrides_project_default(tmp_path: Path, monkeypatch):
    _clear_path_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KKOCLAW_SKILLS_PATH", "team-skills")

    assert SkillsConfig().get_skills_path() == tmp_path / "team-skills"
    assert get_or_new_skill_storage(skills_path=SkillsConfig().get_skills_path()).get_skills_root_path() == tmp_path / "team-skills"


def test_kkoclaw_project_root_must_exist(tmp_path: Path, monkeypatch):
    _clear_path_env(monkeypatch)
    missing_root = tmp_path / "missing"
    monkeypatch.setenv("KKOCLAW_PROJECT_ROOT", str(missing_root))

    with pytest.raises(ValueError, match="does not exist"):
        project_root()


def test_kkoclaw_project_root_must_be_directory(tmp_path: Path, monkeypatch):
    _clear_path_env(monkeypatch)
    project_root_file = tmp_path / "project-root"
    project_root_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("KKOCLAW_PROJECT_ROOT", str(project_root_file))

    with pytest.raises(ValueError, match="not a directory"):
        project_root()


def test_app_config_falls_back_to_legacy_when_project_root_lacks_config(tmp_path: Path, monkeypatch):
    """When KKOCLAW_PROJECT_ROOT is unset and cwd has no config.yaml, the
    legacy backend/repo-root candidates must be used for monorepo compatibility."""
    _clear_path_env(monkeypatch)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    legacy_backend = tmp_path / "legacy-backend"
    legacy_repo = tmp_path / "legacy-repo"
    legacy_backend.mkdir()
    legacy_repo.mkdir()
    legacy_backend_config = legacy_backend / "config.yaml"
    legacy_backend_config.write_text(
        yaml.safe_dump({"sandbox": {"use": "kkoclaw.sandbox.local:LocalSandboxProvider"}}),
        encoding="utf-8",
    )
    repo_root_config = legacy_repo / "config.yaml"
    repo_root_config.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        app_config_module,
        "_legacy_config_candidates",
        lambda: (legacy_backend_config, repo_root_config),
    )

    assert AppConfig.resolve_config_path() == legacy_backend_config


def test_extensions_config_falls_back_to_legacy_when_project_root_lacks_file(tmp_path: Path, monkeypatch):
    """ExtensionsConfig should hit the legacy backend/repo-root locations when
    the caller project root has no extensions_config.json/mcp_config.json."""
    _clear_path_env(monkeypatch)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    fake_backend = tmp_path / "fake-backend"
    fake_repo = tmp_path / "fake-repo"
    fake_backend.mkdir()
    fake_repo.mkdir()
    legacy_extensions = fake_backend / "extensions_config.json"
    legacy_extensions.write_text('{"mcpServers": {}, "skills": {}}', encoding="utf-8")

    fake_paths_module_file = fake_backend / "packages" / "harness" / "kkoclaw" / "config" / "extensions_config.py"
    fake_paths_module_file.parent.mkdir(parents=True)
    fake_paths_module_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(extensions_config_module, "__file__", str(fake_paths_module_file))

    assert ExtensionsConfig.resolve_config_path() == legacy_extensions


# ---------------------------------------------------------------------------
# Web default → user home (~/.kkoclaw) + auto-migration
# ---------------------------------------------------------------------------


def test_default_runtime_home_is_user_home_dot_kkoclaw(tmp_path: Path, monkeypatch):
    """``runtime_home()`` returns ``~/.kkoclaw`` when no env var is set."""
    _clear_path_env(monkeypatch)
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
    assert runtime_home() == tmp_path / ".kkoclaw"


def test_auto_migrates_legacy_project_kkoclaw_to_user_home(tmp_path: Path, monkeypatch, caplog):
    """``Paths()`` moves ``<project_root>/.kkoclaw`` to ``~/.kkoclaw`` once."""
    _clear_path_env(monkeypatch)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: fake_home))

    fake_project = tmp_path / "project"
    fake_project.mkdir()
    legacy_dir = fake_project / ".kkoclaw"
    legacy_dir.mkdir()
    (legacy_dir / "memory.json").write_text('{"legacy": true}', encoding="utf-8")
    (legacy_dir / "threads").mkdir()
    (legacy_dir / "threads" / "t-legacy").mkdir()

    # `paths.py` imports project_root/runtime_home into its own namespace, so
    # we must patch the local bindings, not the runtime_paths module.
    monkeypatch.setattr("kkoclaw.config.paths.project_root", lambda: fake_project)
    monkeypatch.setattr("kkoclaw.config.paths.runtime_home", lambda: fake_home / ".kkoclaw")

    import logging as _logging
    with caplog.at_level(_logging.INFO, logger="kkoclaw.config.paths"):
        target = Paths().base_dir

    assert target == fake_home / ".kkoclaw"
    assert (target / "memory.json").read_text(encoding="utf-8") == '{"legacy": true}'
    assert (target / "threads" / "t-legacy").is_dir()
    assert not legacy_dir.exists(), "legacy project dir should have been moved away"
    assert "Migrated legacy KKOCLAW_HOME" in caplog.text


def test_no_migration_when_kkoclaw_home_explicitly_set(tmp_path: Path, monkeypatch):
    """Explicit ``KKOCLAW_HOME`` overrides the migration entirely."""
    explicit = tmp_path / "custom-home"
    explicit.mkdir()
    monkeypatch.setenv("KKOCLAW_HOME", str(explicit))

    fake_project = tmp_path / "project"
    fake_project.mkdir()
    legacy_dir = fake_project / ".kkoclaw"
    legacy_dir.mkdir()
    (legacy_dir / "memory.json").write_text('{"legacy": true}', encoding="utf-8")

    monkeypatch.setattr("kkoclaw.config.paths.project_root", lambda: fake_project)
    monkeypatch.setattr("kkoclaw.config.paths.runtime_home", lambda: explicit.resolve())

    assert Paths().base_dir == explicit.resolve()
    assert legacy_dir.is_dir(), "legacy dir must stay put when KKOCLAW_HOME is explicit"


def test_no_migration_when_target_already_exists(tmp_path: Path, monkeypatch):
    """If ``~/.kkoclaw`` already exists we do nothing — no overwrite."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    target = fake_home / ".kkoclaw"
    target.mkdir()
    (target / "memory.json").write_text('{"fresh": true}', encoding="utf-8")
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: fake_home))

    fake_project = tmp_path / "project"
    fake_project.mkdir()
    legacy_dir = fake_project / ".kkoclaw"
    legacy_dir.mkdir()
    (legacy_dir / "memory.json").write_text('{"legacy": true}', encoding="utf-8")

    monkeypatch.setattr("kkoclaw.config.paths.project_root", lambda: fake_project)
    monkeypatch.setattr("kkoclaw.config.paths.runtime_home", lambda: target)

    assert Paths().base_dir == target
    assert (target / "memory.json").read_text(encoding="utf-8") == '{"fresh": true}'
    assert legacy_dir.is_dir(), "legacy dir is left alone when target already exists"


def test_migration_skipped_when_explicit_base_dir_passed(tmp_path: Path, monkeypatch):
    """Passing ``base_dir`` to ``Paths(...)`` skips the migration — tests
    and embedded callers control the directory themselves."""
    _clear_path_env(monkeypatch)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: fake_home))

    fake_project = tmp_path / "project"
    fake_project.mkdir()
    legacy_dir = fake_project / ".kkoclaw"
    legacy_dir.mkdir()

    monkeypatch.setattr("kkoclaw.config.paths.project_root", lambda: fake_project)
    monkeypatch.setattr("kkoclaw.config.paths.runtime_home", lambda: fake_home / ".kkoclaw")

    explicit = tmp_path / "scratch"
    explicit.mkdir()
    assert Paths(base_dir=explicit).base_dir == explicit.resolve()
    assert legacy_dir.is_dir(), "explicit base_dir must not trigger migration"
