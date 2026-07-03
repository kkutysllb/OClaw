import json
import importlib.util
from pathlib import Path

import pytest


def _load_mcp_router_module():
    module_path = Path(__file__).resolve().parents[1] / "app" / "gateway" / "routers" / "mcp.py"
    spec = importlib.util.spec_from_file_location("mcp_router_direct", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.anyio
async def test_default_user_mcp_update_preserves_work_mode_fields(monkeypatch, tmp_path):
    mcp_router = _load_mcp_router_module()
    from kkoclaw.config.extensions_config import (
        ExtensionsConfig,
        McpServerConfig,
        ModeSkillOverridesConfig,
        SkillStateConfig,
    )
    from kkoclaw.runtime.user_context import DEFAULT_USER_ID

    config_file = tmp_path / "extensions_config.json"
    current_config = ExtensionsConfig(
        mcp_servers={
            "old-server": McpServerConfig(
                enabled=True,
                type="stdio",
                command="echo",
                env={"TOKEN": "secret"},
            )
        },
        skills={"existing-skill": SkillStateConfig(enabled=False)},
        locked_skill_ids=("bootstrap", "custom-lock"),
        mode_skill_overrides={
            "coding": ModeSkillOverridesConfig(added_skill_ids=("coding-helper",)),
        },
    )
    current_config.save(config_file)

    monkeypatch.setattr(mcp_router.ExtensionsConfig, "resolve_config_path", classmethod(lambda cls, config_path=None: Path(config_path) if config_path else config_file))
    monkeypatch.setattr(mcp_router, "get_extensions_config", lambda: current_config)
    monkeypatch.setattr("kkoclaw.runtime.user_context.get_effective_user_id", lambda: DEFAULT_USER_ID)
    monkeypatch.setattr(mcp_router, "invalidate_all_user_mcp_configs", lambda: None, raising=False)

    def _reload():
        return ExtensionsConfig.from_file(str(config_file))

    monkeypatch.setattr(mcp_router, "reload_extensions_config", _reload)

    request = mcp_router.McpConfigUpdateRequest(
        mcp_servers={
            "old-server": mcp_router.McpServerConfigResponse(
                enabled=False,
                type="stdio",
                command="echo",
                env={"TOKEN": "***"},
            )
        }
    )

    response = await mcp_router.update_mcp_configuration(request)

    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert saved["locked_skill_ids"] == ["bootstrap", "custom-lock"]
    assert saved["mode_skill_overrides"]["coding"]["added_skill_ids"] == ["coding-helper"]
    assert saved["work_modes"]["default_mode_id"] == "task"
    assert saved["skills"]["existing-skill"]["enabled"] is False
    assert saved["mcpServers"]["old-server"]["env"]["TOKEN"] == "secret"
    assert response.mcp_servers["old-server"].env["TOKEN"] == "***"
