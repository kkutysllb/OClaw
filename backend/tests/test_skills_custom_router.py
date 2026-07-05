import errno
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import skills as skills_router
from kkoclaw.skills.storage import get_or_new_skill_storage
from kkoclaw.skills.types import Skill


def _skill_content(name: str, description: str = "Demo skill") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"


async def _async_scan(decision: str, reason: str):
    from kkoclaw.skills.security_scanner import ScanResult

    return ScanResult(decision=decision, reason=reason)


def _make_skill(name: str, *, enabled: bool) -> Skill:
    skill_dir = Path(f"/tmp/{name}")
    return Skill(
        name=name,
        description=f"Description for {name}",
        license="MIT",
        skill_dir=skill_dir,
        skill_file=skill_dir / "SKILL.md",
        relative_path=Path(name),
        category="public",
        enabled=enabled,
    )


def _make_test_app(config) -> FastAPI:
    app = FastAPI()
    app.state.config = config
    app.include_router(skills_router.router)
    return app


def _make_skill_archive(tmp_path: Path, name: str, content: str | None = None) -> Path:
    archive = tmp_path / f"{name}.skill"
    skill_content = content or _skill_content(name)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(f"{name}/SKILL.md", skill_content)
    return archive


def test_install_skill_archive_runs_security_scan(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    archive = _make_skill_archive(tmp_path, "archive-skill")
    scan_calls = []
    refresh_calls = []

    async def _scan(content, *, executable, location, app_config=None):
        from kkoclaw.skills.security_scanner import ScanResult

        scan_calls.append({"content": content, "executable": executable, "location": location})
        return ScanResult(decision="allow", reason="ok")

    async def _refresh():
        refresh_calls.append("refresh")

    from types import SimpleNamespace

    from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

    storage = LocalSkillStorage(host_path=str(skills_root))
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr(skills_router, "resolve_thread_virtual_path", lambda thread_id, path: archive)
    monkeypatch.setattr(skills_router, "get_or_new_skill_storage", lambda **kw: storage)
    monkeypatch.setattr("kkoclaw.skills.installer.scan_skill_content", _scan)
    monkeypatch.setattr(skills_router, "refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post("/api/skills/install", json={"thread_id": "thread-1", "path": "mnt/user-data/outputs/archive-skill.skill"})

    assert response.status_code == 200
    assert response.json()["skill_name"] == "archive-skill"
    assert (skills_root / "custom" / "archive-skill" / "SKILL.md").exists()
    assert scan_calls == [
        {
            "content": _skill_content("archive-skill"),
            "executable": False,
            "location": "archive-skill/SKILL.md",
        }
    ]
    assert refresh_calls == ["refresh"]


def test_install_skill_archive_security_scan_block_returns_400(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    archive = _make_skill_archive(tmp_path, "blocked-skill")
    refresh_calls = []

    async def _scan(*args, **kwargs):
        from kkoclaw.skills.security_scanner import ScanResult

        return ScanResult(decision="block", reason="prompt injection")

    async def _refresh():
        refresh_calls.append("refresh")

    from types import SimpleNamespace

    from kkoclaw.skills.storage.local_skill_storage import LocalSkillStorage

    storage = LocalSkillStorage(host_path=str(skills_root))
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr(skills_router, "resolve_thread_virtual_path", lambda thread_id, path: archive)
    monkeypatch.setattr(skills_router, "get_or_new_skill_storage", lambda **kw: storage)
    monkeypatch.setattr("kkoclaw.skills.installer.scan_skill_content", _scan)
    monkeypatch.setattr(skills_router, "refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post("/api/skills/install", json={"thread_id": "thread-1", "path": "mnt/user-data/outputs/blocked-skill.skill"})

    assert response.status_code == 400
    assert "Security scan blocked skill 'blocked-skill': prompt injection" in response.json()["detail"]
    assert not (skills_root / "custom" / "blocked-skill").exists()
    assert refresh_calls == []


def test_custom_skills_router_lifecycle(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "demo-skill"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "SKILL.md").write_text(_skill_content("demo-skill"), encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", lambda *args, **kwargs: _async_scan("allow", "ok"))
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.get("/api/skills/custom")
        assert response.status_code == 200
        assert response.json()["skills"][0]["name"] == "demo-skill"

        get_response = client.get("/api/skills/custom/demo-skill")
        assert get_response.status_code == 200
        assert "# demo-skill" in get_response.json()["content"]

        update_response = client.put(
            "/api/skills/custom/demo-skill",
            json={"content": _skill_content("demo-skill", "Edited skill")},
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Edited skill"

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["action"] == "human_edit"

        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 200
        assert rollback_response.json()["description"] == "Demo skill"
        assert refresh_calls == ["refresh", "refresh"]


def test_custom_skill_rollback_blocked_by_scanner(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "demo-skill"
    custom_dir.mkdir(parents=True, exist_ok=True)
    original_content = _skill_content("demo-skill")
    edited_content = _skill_content("demo-skill", "Edited skill")
    (custom_dir / "SKILL.md").write_text(edited_content, encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    history_file = get_or_new_skill_storage(app_config=config).get_skill_history_file("demo-skill")
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        '{"action":"human_edit","prev_content":' + json.dumps(original_content) + ',"new_content":' + json.dumps(edited_content) + "}\n",
        encoding="utf-8",
    )

    async def _refresh():
        return None

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    async def _scan(*args, **kwargs):
        from kkoclaw.skills.security_scanner import ScanResult

        return ScanResult(decision="block", reason="unsafe rollback")

    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", _scan)

    app = _make_test_app(config)

    with TestClient(app) as client:
        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 400
        assert "unsafe rollback" in rollback_response.json()["detail"]

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["scanner"]["decision"] == "block"


def test_custom_skill_delete_preserves_history_and_allows_restore(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "demo-skill"
    custom_dir.mkdir(parents=True, exist_ok=True)
    original_content = _skill_content("demo-skill")
    (custom_dir / "SKILL.md").write_text(original_content, encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", lambda *args, **kwargs: _async_scan("allow", "ok"))
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        delete_response = client.delete("/api/skills/custom/demo-skill")
        assert delete_response.status_code == 200
        assert not (custom_dir / "SKILL.md").exists()

        history_response = client.get("/api/skills/custom/demo-skill/history")
        assert history_response.status_code == 200
        assert history_response.json()["history"][-1]["action"] == "human_delete"

        rollback_response = client.post("/api/skills/custom/demo-skill/rollback", json={"history_index": -1})
        assert rollback_response.status_code == 200
        assert rollback_response.json()["description"] == "Demo skill"
        assert (custom_dir / "SKILL.md").read_text(encoding="utf-8") == original_content
        assert refresh_calls == ["refresh", "refresh"]


def test_custom_skill_delete_continues_when_history_write_is_readonly(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "demo-skill"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "SKILL.md").write_text(_skill_content("demo-skill"), encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    def _readonly_history(*args, **kwargs):
        raise OSError(errno.EROFS, "Read-only file system", str(skills_root / "custom" / ".history"))

    monkeypatch.setattr("kkoclaw.skills.storage.local_skill_storage.LocalSkillStorage.append_history", _readonly_history)
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        delete_response = client.delete("/api/skills/custom/demo-skill")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True}
    assert not custom_dir.exists()
    assert refresh_calls == ["refresh"]


def test_custom_skill_delete_fails_when_skill_dir_removal_fails(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "demo-skill"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "SKILL.md").write_text(_skill_content("demo-skill"), encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    def _fail_rmtree(*args, **kwargs):
        raise PermissionError(errno.EACCES, "Permission denied", str(custom_dir))

    monkeypatch.setattr("kkoclaw.skills.storage.local_skill_storage.shutil.rmtree", _fail_rmtree)
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(config)

    with TestClient(app) as client:
        delete_response = client.delete("/api/skills/custom/demo-skill")

    assert delete_response.status_code == 500
    assert "Failed to delete custom skill" in delete_response.json()["detail"]
    assert custom_dir.exists()
    assert refresh_calls == []


def test_update_skill_refreshes_prompt_cache_before_return(monkeypatch, tmp_path):
    config_path = tmp_path / "extensions_config.json"
    enabled_state = {"value": True}
    refresh_calls = []

    def _load_skills(*, enabled_only: bool):
        skill = _make_skill("demo-skill", enabled=enabled_state["value"])
        if enabled_only and not skill.enabled:
            return []
        return [skill]

    async def _refresh():
        refresh_calls.append("refresh")
        enabled_state["value"] = False

    mock_storage = SimpleNamespace(load_skills=_load_skills)
    monkeypatch.setattr("app.gateway.routers.skills.get_or_new_skill_storage", lambda **kwargs: mock_storage)
    monkeypatch.setattr("app.gateway.routers.skills.get_extensions_config", lambda: SimpleNamespace(mcp_servers={}, skills={}))
    monkeypatch.setattr("app.gateway.routers.skills.reload_extensions_config", lambda: None)
    monkeypatch.setattr(skills_router.ExtensionsConfig, "resolve_config_path", staticmethod(lambda: config_path))
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)

    app = _make_test_app(SimpleNamespace())

    with TestClient(app) as client:
        response = client.put("/api/skills/demo-skill", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert refresh_calls == ["refresh"]
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"mcpServers": {}, "skills": {"demo-skill": {"enabled": False}}}


# ---------------------------------------------------------------------------
# POST /api/skills/custom — wizard-driven skill creation
# ---------------------------------------------------------------------------


def _create_config(skills_root: Path) -> SimpleNamespace:
    """Build a minimal config SimpleNamespace that the skills router accepts."""
    return SimpleNamespace(
        skills=SimpleNamespace(
            get_skills_path=lambda: skills_root,
            container_path="/mnt/skills",
            use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage",
        ),
        skill_evolution=SimpleNamespace(enabled=False, moderation_model_name=None),
    )


def _patch_create_dependencies(monkeypatch, *, scan_decision: str = "allow", scan_reason: str = "ok"):
    """Patch scan + prompt-cache refresh for the create endpoint."""
    from kkoclaw.skills.security_scanner import ScanResult

    scan_calls: list[dict] = []
    refresh_calls: list[str] = []

    async def _scan(content, *, executable, location, app_config=None):
        scan_calls.append({"content": content, "executable": executable, "location": location})
        return ScanResult(decision=scan_decision, reason=scan_reason)

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr("app.gateway.routers.skills.scan_skill_content", _scan)
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: None)
    return scan_calls, refresh_calls


def test_create_custom_skill_succeeds(monkeypatch, tmp_path):
    """POST /api/skills/custom creates the skill, injects work_modes, scans, and records history."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    (skills_root / "public").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)

    scan_calls, refresh_calls = _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "my-wizard-skill",
                "description": "Created via the wizard",
                "content": "---\nname: my-wizard-skill\ndescription: Created via the wizard\n---\n# my-wizard-skill\nBody here.\n",
                "work_modes": ["task", "coding"],
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "my-wizard-skill"
    assert body["description"] == "Created via the wizard"
    assert body["category"] == "custom"

    # File was written atomically.
    skill_file = skills_root / "custom" / "my-wizard-skill" / "SKILL.md"
    assert skill_file.exists()
    written = skill_file.read_text(encoding="utf-8")
    # work_modes frontmatter was injected.
    assert "work_modes:" in written
    # History was recorded.
    history_file = skills_root / "custom" / ".history" / "my-wizard-skill.jsonl"
    assert history_file.exists()
    assert '"action": "create"' in history_file.read_text(encoding="utf-8")
    # Security scan ran with the injected content.
    assert len(scan_calls) == 1
    assert scan_calls[0]["location"] == "my-wizard-skill/SKILL.md"
    # Prompt cache was refreshed.
    assert refresh_calls == ["refresh"]


def test_create_custom_skill_defaults_work_modes_to_task(monkeypatch, tmp_path):
    """Omitting work_modes defaults to ['task'] (mirrors skill_manage_tool)."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "task-default-skill",
                "description": "Should bind to task",
                "content": "---\nname: task-default-skill\ndescription: Should bind to task\n---\n# task-default-skill\n",
            },
        )

    assert response.status_code == 200, response.text
    written = (skills_root / "custom" / "task-default-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "work_modes:" in written
    assert "task" in written


def test_create_custom_skill_normalises_name(monkeypatch, tmp_path):
    """Uppercase / underscores / spaces are normalised to hyphen-case."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "My_Cool Skill",
                "description": "Normalisation test",
                "content": "---\nname: my-cool-skill\ndescription: Normalisation test\n---\n# my-cool-skill\n",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "my-cool-skill"
    assert (skills_root / "custom" / "my-cool-skill" / "SKILL.md").exists()


def test_create_custom_skill_rejects_duplicate_custom(monkeypatch, tmp_path):
    """409 when a custom skill with the same name already exists."""
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "dup-skill"
    custom_dir.mkdir(parents=True)
    (custom_dir / "SKILL.md").write_text(_skill_content("dup-skill"), encoding="utf-8")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "dup-skill",
                "description": "Duplicate",
                "content": _skill_content("dup-skill"),
            },
        )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_custom_skill_rejects_builtin_name(monkeypatch, tmp_path):
    """409 when the name collides with a built-in (public) skill."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    builtin_dir = skills_root / "public" / "planning"
    builtin_dir.mkdir(parents=True)
    (builtin_dir / "SKILL.md").write_text(_skill_content("planning"), encoding="utf-8")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "planning",
                "description": "Shadowing a builtin",
                "content": _skill_content("planning"),
            },
        )

    assert response.status_code == 409
    assert "built-in" in response.json()["detail"]


def test_create_custom_skill_rejects_frontmatter_name_mismatch(monkeypatch, tmp_path):
    """400 when the frontmatter `name` does not match the request name."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "outer-name",
                "description": "Mismatched",
                "content": "---\nname: different-name\ndescription: Mismatched\n---\n# different-name\n",
            },
        )

    assert response.status_code == 400
    assert not (skills_root / "custom" / "outer-name").exists()


def test_create_custom_skill_blocked_by_scanner_returns_400(monkeypatch, tmp_path):
    """400 when the security scan decision is 'block' — no file written."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch, scan_decision="block", scan_reason="prompt injection detected")

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "blocked-skill",
                "description": "Should be blocked",
                "content": "---\nname: blocked-skill\ndescription: Should be blocked\n---\n# blocked-skill\n",
            },
        )

    assert response.status_code == 400
    assert "prompt injection detected" in response.json()["detail"]
    assert not (skills_root / "custom" / "blocked-skill").exists()


def test_create_custom_skill_not_gated_by_skill_evolution(monkeypatch, tmp_path):
    """The wizard endpoint works even with skill_evolution.enabled=False."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = SimpleNamespace(
        skills=SimpleNamespace(
            get_skills_path=lambda: skills_root,
            container_path="/mnt/skills",
            use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage",
        ),
        skill_evolution=SimpleNamespace(enabled=False, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom",
            json={
                "name": "user-created",
                "description": "Explicit user action",
                "content": "---\nname: user-created\ndescription: Explicit user action\n---\n# user-created\n",
            },
        )

    assert response.status_code == 200, response.text
    assert (skills_root / "custom" / "user-created" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# POST /api/skills/install-upload — wizard-driven package install (功能 A)
# ---------------------------------------------------------------------------


def _make_skill_zip_bytes(name: str, *, nested: bool = False, content: str | None = None) -> bytes:
    """Build a .skill ZIP in memory. ``nested`` mirrors the "wrapped in a single
    top-level dir" archive shape that the installer also accepts."""
    import io

    skill_md = content or _skill_content(name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if nested:
            zf.writestr(f"{name}/SKILL.md", skill_md)
        else:
            zf.writestr("SKILL.md", skill_md)
    return buf.getvalue()


def _patch_install_upload_deps(monkeypatch, *, scan_decision: str = "allow"):
    """Patch scanner + prompt-cache refresh for install-upload tests."""
    from kkoclaw.skills.security_scanner import ScanResult

    refresh_calls: list[str] = []

    async def _scan(*args, **kwargs):
        return ScanResult(decision=scan_decision, reason="ok" if scan_decision == "allow" else "flagged")

    async def _refresh():
        refresh_calls.append("refresh")

    # The installer calls scan_skill_content via the module-level import.
    monkeypatch.setattr("kkoclaw.skills.installer.scan_skill_content", _scan)
    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: None)
    return refresh_calls


def test_install_upload_succeeds_flat_archive(monkeypatch, tmp_path):
    """A flat .skill archive (SKILL.md at root) installs via multipart upload."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    refresh_calls = _patch_install_upload_deps(monkeypatch)

    app = _make_test_app(config)
    archive = _make_skill_zip_bytes("upload-flat-skill")

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/install-upload",
            files={"file": ("upload-flat-skill.skill", archive, "application/zip")},
            data={"work_modes": '["task"]'},
        )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    assert response.json()["skill_name"] == "upload-flat-skill"
    assert (skills_root / "custom" / "upload-flat-skill" / "SKILL.md").exists()
    assert refresh_calls == ["refresh"]


def test_install_upload_succeeds_nested_archive(monkeypatch, tmp_path):
    """An archive wrapping files under a single top-level dir also installs."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_install_upload_deps(monkeypatch)

    app = _make_test_app(config)
    archive = _make_skill_zip_bytes("upload-nested-skill", nested=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/install-upload",
            files={"file": ("upload-nested-skill.skill", archive, "application/zip")},
        )

    assert response.status_code == 200, response.text
    assert (skills_root / "custom" / "upload-nested-skill" / "SKILL.md").exists()


def test_install_upload_rejects_non_skill_extension(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/install-upload",
            files={"file": ("not-a-skill.zip", b"pk\x03\x04", "application/zip")},
        )

    assert response.status_code == 400
    assert ".skill" in response.json()["detail"]


def test_install_upload_rejects_duplicate(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_dir = skills_root / "custom" / "dup-upload"
    custom_dir.mkdir(parents=True)
    (custom_dir / "SKILL.md").write_text(_skill_content("dup-upload"), encoding="utf-8")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_install_upload_deps(monkeypatch)

    app = _make_test_app(config)
    archive = _make_skill_zip_bytes("dup-upload")

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/install-upload",
            files={"file": ("dup-upload.skill", archive, "application/zip")},
        )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_install_upload_rejects_bad_frontmatter(monkeypatch, tmp_path):
    """An archive whose SKILL.md lacks required frontmatter is rejected with 400."""
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_install_upload_deps(monkeypatch)

    app = _make_test_app(config)
    # No frontmatter at all → validator rejects.
    archive = _make_skill_zip_bytes("bad-skill", content="# bad-skill\nno frontmatter here\n")

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/install-upload",
            files={"file": ("bad-skill.skill", archive, "application/zip")},
        )

    assert response.status_code == 400
    assert not (skills_root / "custom" / "bad-skill").exists()


# ---------------------------------------------------------------------------
# POST /api/skills/custom/{name}/support-files — wizard scripts upload (功能 B)
# ---------------------------------------------------------------------------


def _prepare_existing_skill(skills_root: Path, name: str) -> None:
    custom_dir = skills_root / "custom" / name
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "SKILL.md").write_text(_skill_content(name), encoding="utf-8")


def test_support_files_upload_script_succeeds(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "scripted-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch, scan_decision="allow")

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/scripted-skill/support-files",
            files={"files": ("run.sh", b"#!/bin/sh\necho ok\n", "text/x-shellscript")},
            data={"subdir": "scripts"},
        )

    assert response.status_code == 200, response.text
    script_file = skills_root / "custom" / "scripted-skill" / "scripts" / "run.sh"
    assert script_file.exists()
    assert script_file.read_text(encoding="utf-8") == "#!/bin/sh\necho ok\n"
    history_file = skills_root / "custom" / ".history" / "scripted-skill.jsonl"
    assert '"action": "upload_file"' in history_file.read_text(encoding="utf-8")


def test_support_files_upload_asset_binary_skips_scan(monkeypatch, tmp_path):
    """Binary files (non-UTF-8) under assets/ are written without LLM scan."""
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "asset-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    scan_calls = _patch_create_dependencies(monkeypatch)[0]

    app = _make_test_app(config)
    # PNG header + garbage → not valid UTF-8.
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0cIHDR"

    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/asset-skill/support-files",
            files={"files": ("logo.png", png_bytes, "image/png")},
            data={"subdir": "assets"},
        )

    assert response.status_code == 200, response.text
    assert (skills_root / "custom" / "asset-skill" / "assets" / "logo.png").exists()
    # Binary files must NOT trigger the LLM scan.
    assert scan_calls == []


def test_support_files_rejects_unknown_skill(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    (skills_root / "custom").mkdir(parents=True)
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/no-such-skill/support-files",
            files={"files": ("run.sh", b"echo", "text/plain")},
            data={"subdir": "scripts"},
        )

    assert response.status_code == 400
    assert "Use action='create'" in response.json()["detail"] or "does not exist" in response.json()["detail"]


def test_support_files_rejects_invalid_subdir(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "subdir-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/subdir-skill/support-files",
            files={"files": ("run.sh", b"echo", "text/plain")},
            data={"subdir": "executables"},
        )

    assert response.status_code == 400
    assert "Invalid subdir" in response.json()["detail"]


def test_support_files_scripts_warn_accepted(monkeypatch, tmp_path):
    """scripts/ uploads via the wizard accept 'warn' (borderline but legitimate).

    The support-files endpoint is driven by an explicit user action (the user
    picked the file from their own machine), so a 'warn' verdict — typically
    flagging borderline-but-legitimate patterns like external API references
    — is accepted. Only 'block' (clear malicious content) is rejected. This
    is intentionally more permissive than the .skill installer, which
    requires explicit 'allow' for executables because archives may come from
    untrusted third-party marketplaces.
    """
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "warn-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch, scan_decision="warn")

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/warn-skill/support-files",
            files={"files": ("run.sh", b"#!/bin/sh\necho hi\n", "text/plain")},
            data={"subdir": "scripts"},
        )

    assert response.status_code == 200, response.text
    # The warn verdict did NOT block the upload — the script landed on disk.
    assert (skills_root / "custom" / "warn-skill" / "scripts" / "run.sh").exists()


def test_support_files_scripts_block_still_rejected(monkeypatch, tmp_path):
    """Only 'block' is rejected for scripts via the wizard."""
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "block-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch, scan_decision="block", scan_reason="prompt injection")

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/block-skill/support-files",
            files={"files": ("evil.sh", b"#!/bin/sh\nrm -rf /\n", "text/plain")},
            data={"subdir": "scripts"},
        )

    assert response.status_code == 400
    assert "blocked" in response.json()["detail"].lower()
    assert not (skills_root / "custom" / "block-skill" / "scripts" / "evil.sh").exists()


def test_support_files_strips_path_components(monkeypatch, tmp_path):
    """Client-supplied filenames with path components are stripped to basename."""
    skills_root = tmp_path / "skills"
    _prepare_existing_skill(skills_root, "strip-skill")
    config = _create_config(skills_root)
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    _patch_create_dependencies(monkeypatch)

    app = _make_test_app(config)
    with TestClient(app) as client:
        response = client.post(
            "/api/skills/custom/strip-skill/support-files",
            files={"files": ("../../../etc/passwd", b"root:x:0:0\n", "text/plain")},
            data={"subdir": "references"},
        )

    # basename is "passwd" → must land inside references/, NOT escape the skill dir.
    assert response.status_code == 200, response.text
    assert (skills_root / "custom" / "strip-skill" / "references" / "passwd").exists()
    assert not (skills_root / "custom" / "strip-skill" / "etc").exists()
