"""Merged AppConfig exposes all upstream + OClaw fields and loads config.yaml."""
from kkoclaw.config.app_config import AppConfig


def test_app_config_has_upstream_fields():
    """Fields ported from deer-flow must be present on AppConfig."""
    cfg = AppConfig(  # minimal construct (sandbox is required)
        sandbox={"use": "kkoclaw.sandbox.local:LocalSandboxProvider"}
    )
    # upstream-new fields
    assert hasattr(cfg, "token_budget")
    assert hasattr(cfg, "loop_detection")
    assert hasattr(cfg, "tool_progress")
    assert hasattr(cfg, "read_before_write")
    assert hasattr(cfg, "input_polish")
    assert hasattr(cfg, "suggestions")
    assert hasattr(cfg, "channel_connections")
    assert hasattr(cfg, "auth")
    assert hasattr(cfg, "scheduler")
    assert hasattr(cfg, "run_ownership")
    assert hasattr(cfg, "skill_scan")
    assert hasattr(cfg, "logging")


def test_app_config_preserves_oclaw_fields():
    """OClaw-specific fields must survive the merge."""
    cfg = AppConfig(sandbox={"use": "kkoclaw.sandbox.local:LocalSandboxProvider"})
    assert hasattr(cfg, "coding_agent")
    assert hasattr(cfg, "cron_management")
    assert hasattr(cfg, "token_economy")
    assert hasattr(cfg, "agent_recursion_limit")
    assert hasattr(cfg, "todo_max_completion_reminders")
    assert hasattr(cfg, "todo_strict_completion")


def test_app_config_loads_real_config_yaml():
    """The repo's config.yaml must load without error (smoke)."""
    cfg = AppConfig.from_file()
    assert cfg.models  # config.yaml defines models
    assert cfg.sandbox is not None
