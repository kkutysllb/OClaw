"""Tests for work-mode HTTP API helpers and locked-skill enforcement.

Task 3 covers:
- ``ExtensionsConfig.save()`` for complete serialization (replaces the manual
  dict-construction in the old ``update_skill`` route that lost work-mode fields).
- ``add_skill_to_mode`` / ``remove_skill_from_mode`` pure helpers for the
  ``/api/work-modes/{mode_id}/skills/{skill_name}`` endpoints.
- AST-based seam checks for route registration and locked-skill enforcement in
  ``skills.py`` (these modules pull in langchain imports that are unavailable in
  the test environment, so we inspect source via AST instead of importing).
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest


# ---------------------------------------------------------------------------
# ExtensionsConfig.save() — full round-trip serialization
# ---------------------------------------------------------------------------


class TestExtensionsConfigSave:
    """``save()`` must round-trip all fields including work-mode data."""

    def test_save_creates_file(self, tmp_path):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        path = cfg.save(str(tmp_path / "ext.json"))
        assert pathlib.Path(path).exists()

    def test_save_round_trips_work_modes(self, tmp_path):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        path = cfg.save(str(tmp_path / "ext.json"))
        loaded = ExtensionsConfig.from_file(str(path))
        assert loaded.work_modes.default_mode_id == "task"
        assert "task" in loaded.work_modes.modes
        assert "coding" in loaded.work_modes.modes

    def test_save_round_trips_mode_overrides(self, tmp_path):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("news-search",)),
            },
        )
        path = cfg.save(str(tmp_path / "ext.json"))
        loaded = ExtensionsConfig.from_file(str(path))
        assert loaded.mode_skill_overrides["task"].added_skill_ids == ("news-search",)

    def test_save_round_trips_locked_skill_ids(self, tmp_path):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        path = cfg.save(str(tmp_path / "ext.json"))
        loaded = ExtensionsConfig.from_file(str(path))
        assert set(loaded.locked_skill_ids) == {"bootstrap", "find-skills", "skill-creator"}

    def test_save_preserves_mcp_and_skills(self, tmp_path):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            McpServerConfig,
            SkillStateConfig,
        )

        cfg = ExtensionsConfig(
            mcp_servers={"test-server": McpServerConfig(command="echo", enabled=True)},
            skills={"my-skill": SkillStateConfig(enabled=False)},
        )
        path = cfg.save(str(tmp_path / "ext.json"))
        loaded = ExtensionsConfig.from_file(str(path))
        assert "test-server" in loaded.mcp_servers
        assert loaded.skills["my-skill"].enabled is False

    def test_save_produces_valid_json(self, tmp_path):
        from kkoclaw.config.extensions_config import ExtensionsConfig

        cfg = ExtensionsConfig()
        path = cfg.save(str(tmp_path / "ext.json"))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "workModes" in data or "work_modes" in data


# ---------------------------------------------------------------------------
# add_skill_to_mode / remove_skill_from_mode — pure helpers
# ---------------------------------------------------------------------------


class TestAddSkillToMode:
    """``add_skill_to_mode`` updates ``mode_skill_overrides`` in a new config copy."""

    def test_add_skill_creates_override(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import add_skill_to_mode

        cfg = ExtensionsConfig()
        result = add_skill_to_mode(cfg, "task", "news-search")
        assert "news-search" in result.mode_skill_overrides["task"].added_skill_ids

    def test_add_skill_is_idempotent(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import add_skill_to_mode

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("news-search",)),
            },
        )
        result = add_skill_to_mode(cfg, "task", "news-search")
        assert result.mode_skill_overrides["task"].added_skill_ids == ("news-search",)

    def test_add_skill_clears_removal(self):
        """Adding a previously-removed skill should clear it from removed_skill_ids."""
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import add_skill_to_mode

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(removed_skill_ids=("news-search",)),
            },
        )
        result = add_skill_to_mode(cfg, "task", "news-search")
        assert "news-search" not in result.mode_skill_overrides["task"].removed_skill_ids
        assert "news-search" in result.mode_skill_overrides["task"].added_skill_ids

    def test_add_skill_does_not_mutate_original(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import add_skill_to_mode

        cfg = ExtensionsConfig()
        add_skill_to_mode(cfg, "task", "news-search")
        assert len(cfg.mode_skill_overrides) == 0


class TestRemoveSkillFromMode:
    """``remove_skill_from_mode`` updates ``mode_skill_overrides`` and rejects locked skills."""

    def test_remove_locked_skill_raises(self):
        from kkoclaw.config.extensions_config import ExtensionsConfig
        from kkoclaw.skills.work_modes import remove_skill_from_mode

        cfg = ExtensionsConfig()
        with pytest.raises(ValueError, match="required by all work modes"):
            remove_skill_from_mode(cfg, "task", "bootstrap")

    def test_remove_skill_creates_removal(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import remove_skill_from_mode

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(added_skill_ids=("news-search",)),
            },
        )
        result = remove_skill_from_mode(cfg, "task", "news-search")
        assert "news-search" not in result.mode_skill_overrides["task"].added_skill_ids
        assert "news-search" in result.mode_skill_overrides["task"].removed_skill_ids

    def test_remove_skill_is_idempotent(self):
        from kkoclaw.config.extensions_config import (
            ExtensionsConfig,
            ModeSkillOverridesConfig,
        )
        from kkoclaw.skills.work_modes import remove_skill_from_mode

        cfg = ExtensionsConfig(
            mode_skill_overrides={
                "task": ModeSkillOverridesConfig(removed_skill_ids=("news-search",)),
            },
        )
        result = remove_skill_from_mode(cfg, "task", "news-search")
        assert result.mode_skill_overrides["task"].removed_skill_ids == ("news-search",)


# ---------------------------------------------------------------------------
# AST-based checks: route registration
# ---------------------------------------------------------------------------

_BACKEND = pathlib.Path(__file__).resolve().parent.parent


class TestWorkModeRouteRegistration:
    """Verify work-modes routes exist and are registered via AST inspection."""

    def test_work_modes_router_file_exists(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        assert path.exists(), "work_modes.py router file must exist"

    def test_work_modes_router_in_init(self):
        init_path = _BACKEND / "app" / "gateway" / "routers" / "__init__.py"
        source = init_path.read_text(encoding="utf-8")
        assert "work_modes" in source, "work_modes router must be registered in __init__.py"

    def test_get_work_modes_endpoint(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if _decorator_matches_route(dec, "get", "/work-modes"):
                        found = True
        assert found, "GET /api/work-modes endpoint must exist"

    def test_delete_work_mode_endpoint_exists(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if _decorator_matches_route(dec, "delete", "/work-modes/{mode_id}"):
                        found = True
        assert found, "DELETE /api/work-modes/{mode_id} endpoint must exist"

    def test_put_mode_skill_endpoint(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if _decorator_matches_route(dec, "put", "skills"):
                        found = True
        assert found, "PUT .../skills/{skill_name} endpoint must exist"

    def test_delete_mode_skill_endpoint(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if _decorator_matches_route(dec, "delete", "skills"):
                        found = True
        assert found, "DELETE .../skills/{skill_name} endpoint must exist"


# ---------------------------------------------------------------------------
# AST-based checks: locked-skill enforcement in skills.py
# ---------------------------------------------------------------------------


class TestLockedSkillEnforcementInSkillsRoute:
    """Verify that skills.py routes enforce locked-skill protection."""

    def test_update_skill_calls_assert_skill_can_be_disabled(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "skills.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "assert_skill_can_be_disabled"
            for node in ast.walk(tree)
        )
        assert found, "skills.py must call assert_skill_can_be_disabled"

    def test_skills_imports_locked_skill_helper(self):
        path = _BACKEND / "app" / "gateway" / "routers" / "skills.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "assert_skill_can_be_disabled":
                        found = True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "assert_skill_can_be_disabled":
                        found = True
        assert found, "skills.py must import assert_skill_can_be_disabled"

    def test_update_skill_uses_config_save(self):
        """The update_skill route should use config.save() not manual dict construction."""
        path = _BACKEND / "app" / "gateway" / "routers" / "skills.py"
        source = path.read_text(encoding="utf-8")
        # Look for .save( call on extensions_config
        assert ".save(" in source, "skills.py should call extensions_config.save()"


# ---------------------------------------------------------------------------
# WorkModeDetailResponse extended fields (lead agent / orchestration / focus)
# ---------------------------------------------------------------------------


class TestWorkModeDetailResponseExtendedFields:
    """The API response must carry mode-awareness data for the frontend drawer."""

    def test_response_model_has_lead_agent_name(self):
        from app.gateway.routers.work_modes import WorkModeDetailResponse

        field = WorkModeDetailResponse.model_fields.get("lead_agent_name")
        assert field is not None, "WorkModeDetailResponse must declare lead_agent_name"

    def test_response_model_has_orchestration_hint(self):
        from app.gateway.routers.work_modes import WorkModeDetailResponse

        field = WorkModeDetailResponse.model_fields.get("orchestration_hint")
        assert field is not None, "WorkModeDetailResponse must declare orchestration_hint"

    def test_response_model_has_focus_areas(self):
        from app.gateway.routers.work_modes import WorkModeDetailResponse

        field = WorkModeDetailResponse.model_fields.get("focus_areas")
        assert field is not None, "WorkModeDetailResponse must declare focus_areas"

    def test_response_model_has_skill_count(self):
        from app.gateway.routers.work_modes import WorkModeDetailResponse

        field = WorkModeDetailResponse.model_fields.get("skill_count")
        assert field is not None, "WorkModeDetailResponse must declare skill_count"

    def test_list_work_modes_populates_extended_fields(self):
        """The ``list_work_modes`` handler must populate the new fields."""
        path = _BACKEND / "app" / "gateway" / "routers" / "work_modes.py"
        source = path.read_text(encoding="utf-8")
        # The handler should reference all four new field names as kwargs.
        for field in (
            "lead_agent_name",
            "orchestration_hint",
            "focus_areas",
            "skill_count",
        ):
            assert field in source, (
                f"list_work_modes must populate {field} in WorkModeDetailResponse"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decorator_matches_route(dec: ast.expr, method: str, path_fragment: str) -> bool:
    """Check if a decorator is ``@router.<method>(...)`` with *path_fragment* in args."""
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    if not (isinstance(func, ast.Attribute) and func.attr == method):
        return False
    # Check path fragments in decorator args
    for arg in dec.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if path_fragment in arg.value:
                return True
    return False
