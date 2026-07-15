"""All newly-ported upstream config modules import and instantiate."""
from kkoclaw.config.loop_detection_config import LoopDetectionConfig
from kkoclaw.config.token_budget_config import TokenBudgetConfig
from kkoclaw.config.tool_progress_config import ToolProgressConfig
from kkoclaw.config.read_before_write_config import ReadBeforeWriteConfig
from kkoclaw.config.input_polish_config import InputPolishConfig
from kkoclaw.config.auth_config import AuthAppConfig
from kkoclaw.config.channel_connections_config import ChannelConnectionsConfig
from kkoclaw.config.run_ownership_config import RunOwnershipConfig
from kkoclaw.config.skill_scan_config import SkillScanConfig
from kkoclaw.config.suggestions_config import SuggestionsConfig
from kkoclaw.config.scheduler_config import SchedulerConfig
from kkoclaw.config.reload_boundary import (
    STARTUP_ONLY_FIELDS,
    format_field_description,
    is_startup_only_field,
)


def test_defaults_instantiate():
    assert LoopDetectionConfig().enabled is True
    assert TokenBudgetConfig().enabled is False
    assert ToolProgressConfig().enabled is False
    assert ReadBeforeWriteConfig().enabled is True
    assert InputPolishConfig().enabled is True
    assert AuthAppConfig().oidc.enabled is False
    assert ChannelConnectionsConfig() is not None
    assert RunOwnershipConfig() is not None
    assert SkillScanConfig() is not None
    assert SuggestionsConfig() is not None
    assert SchedulerConfig() is not None


def test_loop_detection_validates_thresholds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LoopDetectionConfig(hard_limit=1, warn_threshold=5)


def test_token_budget_validates_thresholds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TokenBudgetConfig(hard_stop_threshold=0.5, warn_threshold=0.8)


def test_reload_boundary_registry():
    assert "database" in STARTUP_ONLY_FIELDS
    assert is_startup_only_field("sandbox") is True
    assert is_startup_only_field("models") is False
    desc = format_field_description("database")
    assert desc.startswith("startup-only:")
