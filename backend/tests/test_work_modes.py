"""Tests for work mode skill contracts and effective skill-set resolution.

Work modes (task / coding) are first-class presets that control which skills are
available to the Lead Agent. A small set of "locked" core skills cannot be
disabled or removed from any mode — they protect the agent's self-bootstrap and
skill-discovery capabilities.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Default work mode configuration
# ---------------------------------------------------------------------------


class TestDefaultWorkModeConfig:
    def test_extensions_config_has_default_work_modes(self):
        """``ExtensionsConfig()`` with no input must ship task + coding modes."""
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        assert set(cfg.work_modes.modes.keys()) == {"task", "coding"}
        assert cfg.work_modes.default_mode_id == "task"

    def test_extensions_config_has_default_locked_skill_ids(self):
        """The three core bootstrap skills must be locked by default."""
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        assert cfg.locked_skill_ids == ("bootstrap", "find-skills", "skill-creator")

    def test_task_mode_default_skill_ids_present(self):
        """task mode (日常办公) must declare its default skill set."""
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        task_mode = cfg.work_modes.modes["task"]
        assert task_mode.id == "task"
        assert task_mode.builtin is True
        # Locked skills are implicitly always present — defaults need not repeat them
        assert isinstance(task_mode.default_skill_ids, tuple)

    def test_coding_mode_default_skill_ids_present(self):
        """coding mode must declare its default skill set."""
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        coding_mode = cfg.work_modes.modes["coding"]
        assert coding_mode.id == "coding"
        assert coding_mode.builtin is True


# ---------------------------------------------------------------------------
# AgentConfig ↔ work mode association
# ---------------------------------------------------------------------------


class TestAgentConfigWorkModeAssociation:
    def test_agent_config_accepts_work_mode_id(self):
        """AgentConfig must accept an optional ``work_mode_id`` field."""
        from kkoclaw.config.agents_config import AgentConfig

        cfg = AgentConfig(name="my-agent", work_mode_id="coding")
        assert cfg.work_mode_id == "coding"

    def test_agent_config_work_mode_id_defaults_none(self):
        """When omitted, ``work_mode_id`` must be None (inherit from caller)."""
        from kkoclaw.config.agents_config import AgentConfig

        cfg = AgentConfig(name="my-agent")
        assert cfg.work_mode_id is None

    def test_agent_config_load_strips_unknown_but_keeps_work_mode_id(self):
        """The YAML loader must preserve ``work_mode_id`` when present."""
        # This is validated through AgentConfig.model_fields — the field must exist
        from kkoclaw.config.agents_config import AgentConfig

        assert "work_mode_id" in AgentConfig.model_fields


# ---------------------------------------------------------------------------
# Runtime context forwarding
# ---------------------------------------------------------------------------


class TestWorkModeIdContextForwarding:
    def test_work_mode_id_in_context_configurable_keys(self):
        """``work_mode_id`` must be in the gateway context whitelist so the
        frontend can pass it through to the agent runtime.

        We read the source directly rather than importing ``app.gateway.services``
        because that module pulls in langchain/langgraph at import time, which
        is fragile in unit-test environments where those packages may not be
        installed at the expected version.
        """
        import ast
        import pathlib

        services_path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "app"
            / "gateway"
            / "services.py"
        )
        source = services_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find the assignment to ``_CONTEXT_CONFIGURABLE_KEYS`` and verify
        # ``work_mode_id`` is one of the string literals inside it.
        found_var = False
        found_key = False
        for node in ast.walk(tree):
            # Handle both ``x = ...`` (Assign) and ``x: T = ...`` (AnnAssign)
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id == "_CONTEXT_CONFIGURABLE_KEYS":
                        found_var = True
                        # Walk the frozenset(...) call args to find string literals.
                        for child in ast.walk(node.value):
                            if isinstance(child, ast.Constant) and child.value == "work_mode_id":
                                found_key = True
        assert found_var, "_CONTEXT_CONFIGURABLE_KEYS must be defined in services.py"
        assert found_key, "'work_mode_id' must be in _CONTEXT_CONFIGURABLE_KEYS"


# ---------------------------------------------------------------------------
# Effective skill-set resolution
# ---------------------------------------------------------------------------


class TestResolveEffectiveSkillIds:
    def test_default_task_mode_includes_locked_skills(self):
        """task mode with no overrides must include all locked skills."""
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig()
        effective = resolve_effective_skill_ids(cfg, "task")
        # Locked skills always win
        for locked in ("bootstrap", "find-skills", "skill-creator"):
            assert locked in effective

    def test_added_skills_appear_in_effective_set(self):
        """Skills added via mode_skill_overrides must show up."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("deep-research",)),
            },
        )
        effective = resolve_effective_skill_ids(cfg, "task")
        assert "deep-research" in effective

    def test_removed_skill_disappears_unless_locked(self):
        """A non-locked skill in removed_skill_ids must not appear."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(
                    added_skill_ids=("deep-research", "xlsx-creator"),
                    removed_skill_ids=("deep-research",),
                ),
            },
        )
        effective = resolve_effective_skill_ids(cfg, "task")
        assert "deep-research" not in effective
        assert "xlsx-creator" in effective

    def test_locked_skills_win_over_removals(self):
        """Removing a locked skill from a mode must be ignored — locked wins."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(removed_skill_ids=("bootstrap",)),
            },
        )
        effective = resolve_effective_skill_ids(cfg, "task")
        assert "bootstrap" in effective  # locked — cannot be removed

    def test_unknown_mode_falls_back_to_default(self):
        """An unknown work_mode_id must fall back to the default mode."""
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig()
        effective = resolve_effective_skill_ids(cfg, "nonexistent-mode")
        # Should equal the default (task) mode's effective set
        default_effective = resolve_effective_skill_ids(cfg, "task")
        assert effective == default_effective


# ---------------------------------------------------------------------------
# Directory-based work-mode auto-binding
# ---------------------------------------------------------------------------
#
# The core architecture change: each work mode automatically binds the
# skills filed under its matching builtin sub-directory, plus the shared
# core directory. This replaces the old empty-default + manual-add model.
#
#   task mode   = core/ skills + task/ directory skills
#   coding mode = core/ skills + coding/ directory skills
#   custom/     → no auto binding (mode_scope=None)


class TestDirectoryAutoBinding:
    """resolve_effective_skill_ids must auto-bind by physical directory."""

    def test_task_mode_includes_core_and_task_directory_skills(self):
        """task mode = core skills + task directory skills."""
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig()
        builtin_by_scope = {
            "core": {"bootstrap", "find-skills", "skill-creator"},
            "task": {"deep-research", "chart-visualization", "pdf-processing"},
            "coding": {"code-review", "typescript"},
        }
        effective = resolve_effective_skill_ids(
            cfg, "task", builtin_skills_by_scope=builtin_by_scope
        )
        effective_set = set(effective)
        # Core shared
        assert {"bootstrap", "find-skills", "skill-creator"} <= effective_set
        # Task directory
        assert {"deep-research", "chart-visualization", "pdf-processing"} <= effective_set
        # Coding directory must NOT leak into task mode
        assert "code-review" not in effective_set
        assert "typescript" not in effective_set

    def test_coding_mode_includes_core_and_coding_directory_skills(self):
        """coding mode = core skills + coding directory skills."""
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig()
        builtin_by_scope = {
            "core": {"bootstrap", "find-skills", "skill-creator"},
            "task": {"deep-research", "chart-visualization"},
            "coding": {"code-review", "typescript", "database"},
        }
        effective = resolve_effective_skill_ids(
            cfg, "coding", builtin_skills_by_scope=builtin_by_scope
        )
        effective_set = set(effective)
        # Core shared
        assert {"bootstrap", "find-skills", "skill-creator"} <= effective_set
        # Coding directory
        assert {"code-review", "typescript", "database"} <= effective_set
        # Task directory must NOT leak into coding mode
        assert "deep-research" not in effective_set
        assert "chart-visualization" not in effective_set

    def test_custom_skills_not_auto_included(self):
        """Skills with mode_scope=None (custom) must not appear in any mode."""
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig()
        # custom_by_scope is not part of builtin_skills_by_scope — custom
        # skills live outside the builtin/ directory and have no auto binding.
        builtin_by_scope = {
            "core": {"bootstrap"},
            "task": {"deep-research"},
            "coding": {"code-review"},
        }
        effective_task = set(
            resolve_effective_skill_ids(cfg, "task", builtin_skills_by_scope=builtin_by_scope)
        )
        effective_coding = set(
            resolve_effective_skill_ids(cfg, "coding", builtin_skills_by_scope=builtin_by_scope)
        )
        # A hypothetical custom skill must not be auto-included
        assert "my-custom-skill" not in effective_task
        assert "my-custom-skill" not in effective_coding

    def test_default_skill_ids_still_added_as_backward_compat(self):
        """User-configured default_skill_ids still get appended on top."""
        from kkoclaw.config.extensions_config import ExtensionsConfig, WorkModeConfig
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            work_modes=ExtensionsConfig().work_modes.model_copy(
                update={
                    "modes": {
                        **ExtensionsConfig().work_modes.modes,
                        "task": WorkModeConfig(
                            id="task",
                            name="日常办公",
                            builtin=True,
                            editable=True,
                            default_skill_ids=("extra-legacy-skill",),
                        ),
                    }
                }
            )
        )
        builtin_by_scope = {
            "core": {"bootstrap"},
            "task": {"deep-research"},
            "coding": set(),
        }
        effective = set(
            resolve_effective_skill_ids(cfg, "task", builtin_skills_by_scope=builtin_by_scope)
        )
        assert "extra-legacy-skill" in effective  # backward-compat addition
        assert "deep-research" in effective  # directory auto-bind
        assert "bootstrap" in effective  # core shared

    def test_override_removes_directory_bound_skill(self):
        """A user can remove a directory-bound (non-locked) skill via override."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(removed_skill_ids=("deep-research",)),
            },
        )
        builtin_by_scope = {
            "core": {"bootstrap"},
            "task": {"deep-research", "chart-visualization"},
            "coding": set(),
        }
        effective = set(
            resolve_effective_skill_ids(cfg, "task", builtin_skills_by_scope=builtin_by_scope)
        )
        assert "deep-research" not in effective  # removed by override
        assert "chart-visualization" in effective  # still present
        assert "bootstrap" in effective  # locked core survives

    def test_override_adds_cross_directory_skill(self):
        """A user can add a coding-directory skill to task mode via override."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import resolve_effective_skill_ids

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("code-review",)),
            },
        )
        builtin_by_scope = {
            "core": {"bootstrap"},
            "task": {"deep-research"},
            "coding": {"code-review"},
        }
        effective = set(
            resolve_effective_skill_ids(cfg, "task", builtin_skills_by_scope=builtin_by_scope)
        )
        assert "code-review" in effective  # cross-added via override
        assert "deep-research" in effective  # own directory still present


# ---------------------------------------------------------------------------
# Locked skill enforcement
# ---------------------------------------------------------------------------


class TestLockedSkillEnforcement:
    def test_assert_skill_can_be_disabled_rejects_locked(self):
        """Disabling a locked skill must raise."""
        from kkoclaw.skills.work_modes import (
            DEFAULT_LOCKED_SKILL_IDS,
            assert_skill_can_be_disabled,
        )

        for locked_id in DEFAULT_LOCKED_SKILL_IDS:
            with pytest.raises(ValueError, match="locked"):
                assert_skill_can_be_disabled(locked_id)

    def test_assert_skill_can_be_disabled_allows_non_locked(self):
        """Non-locked skills can be disabled freely."""
        from kkoclaw.skills.work_modes import assert_skill_can_be_disabled

        # Must not raise
        assert_skill_can_be_disabled("deep-research")
        assert_skill_can_be_disabled("some-custom-skill")

    def test_assert_skill_can_be_removed_from_mode_rejects_locked(self):
        """Removing a locked skill from a mode must raise."""
        from kkoclaw.skills.work_modes import (
            DEFAULT_LOCKED_SKILL_IDS,
            assert_skill_can_be_removed_from_mode,
        )

        for locked_id in DEFAULT_LOCKED_SKILL_IDS:
            with pytest.raises(ValueError, match="required by all work modes"):
                assert_skill_can_be_removed_from_mode(locked_id)

    def test_assert_skill_can_be_removed_from_mode_allows_non_locked(self):
        """Non-locked skills can be removed from a mode."""
        from kkoclaw.skills.work_modes import assert_skill_can_be_removed_from_mode

        assert_skill_can_be_removed_from_mode("deep-research") is None


# ---------------------------------------------------------------------------
# Work mode ID resolution
# ---------------------------------------------------------------------------


class TestResolveWorkModeId:
    def test_explicit_id_returned_as_is(self):
        """An explicit valid work_mode_id must be returned unchanged."""
        from kkoclaw.skills.work_modes import resolve_work_mode_id

        assert resolve_work_mode_id("coding") == "coding"
        assert resolve_work_mode_id("task") == "task"

    def test_none_falls_back_to_default(self):
        """None must fall back to the default mode id."""
        from kkoclaw.skills.work_modes import resolve_work_mode_id

        assert resolve_work_mode_id(None) == "task"

    def test_empty_string_falls_back_to_default(self):
        """Empty string must fall back to the default mode id."""
        from kkoclaw.skills.work_modes import resolve_work_mode_id

        assert resolve_work_mode_id("") == "task"

    def test_unknown_id_falls_back_to_default(self):
        """An unknown mode id must fall back to the default (defensive)."""
        from kkoclaw.skills.work_modes import resolve_work_mode_id

        assert resolve_work_mode_id("nonexistent") == "task"
