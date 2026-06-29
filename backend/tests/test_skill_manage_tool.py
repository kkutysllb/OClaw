import importlib
from types import SimpleNamespace

import anyio
import pytest

skill_manage_module = importlib.import_module("kkoclaw.tools.skill_manage_tool")


def _skill_content(name: str, description: str = "Demo skill") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"


async def _async_result(decision: str, reason: str):
    from kkoclaw.skills.security_scanner import ScanResult

    return ScanResult(decision=decision, reason=reason)


def test_skill_manage_create_and_patch(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={"thread_id": "thread-1"}, config={"configurable": {"thread_id": "thread-1"}})

    result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "create",
        "demo-skill",
        _skill_content("demo-skill"),
    )
    assert "Created custom skill" in result

    # Verify work_modes frontmatter was injected on create
    skill_md = (skills_root / "custom" / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "work_modes:" in skill_md

    patch_result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "patch",
        "demo-skill",
        None,
        None,
        "Demo skill",
        "Patched skill",
        1,
    )
    assert "Patched custom skill" in patch_result
    assert "Patched skill" in (skills_root / "custom" / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert refresh_calls == ["refresh", "refresh"]


def test_skill_manage_patch_replaces_single_occurrence_by_default(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)

    async def _refresh():
        return None

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={"thread_id": "thread-1"}, config={"configurable": {"thread_id": "thread-1"}})
    content = _skill_content("demo-skill", "Demo skill") + "\nRepeated: Demo skill\n"

    anyio.run(skill_manage_module.skill_manage_tool.coroutine, runtime, "create", "demo-skill", content)
    patch_result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "patch",
        "demo-skill",
        None,
        None,
        "Demo skill",
        "Patched skill",
    )

    skill_text = (skills_root / "custom" / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "1 replacement(s) applied, 2 match(es) found" in patch_result
    assert skill_text.count("Patched skill") == 1
    assert skill_text.count("Demo skill") == 1


def test_skill_manage_create_injects_explicit_work_modes(monkeypatch, tmp_path):
    """When work_modes is passed explicitly, it must be injected into frontmatter."""
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)

    async def _refresh():
        return None

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={"thread_id": "t1"}, config={"configurable": {"thread_id": "t1"}})
    result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "create",
        "multi-mode-skill",
        _skill_content("multi-mode-skill"),
        None,  # path
        None,  # find
        None,  # replace
        None,  # expected_count
        ["task", "coding"],  # work_modes
    )
    assert "task" in result and "coding" in result
    skill_md = (skills_root / "custom" / "multi-mode-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "work_modes: [task, coding]" in skill_md


def test_skill_manage_create_uses_context_work_mode(monkeypatch, tmp_path):
    """When work_mode_id is in the runtime context, it must be auto-bound."""
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)

    async def _refresh():
        return None

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(
        context={"thread_id": "t1", "work_mode_id": "coding"},
        config={"configurable": {"thread_id": "t1", "work_mode_id": "coding"}},
    )
    result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "create",
        "coding-skill",
        _skill_content("coding-skill"),
    )
    assert "coding" in result
    skill_md = (skills_root / "custom" / "coding-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "work_modes: [coding]" in skill_md


def test_skill_manage_create_defaults_to_task(monkeypatch, tmp_path):
    """When no work_mode_id is available, default to 'task'."""
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)

    async def _refresh():
        return None

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={}, config={"configurable": {}})
    result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "create",
        "default-skill",
        _skill_content("default-skill"),
    )
    assert "task" in result
    skill_md = (skills_root / "custom" / "default-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "work_modes: [task]" in skill_md


def test_skill_manage_rejects_public_skill_patch(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    public_dir = skills_root / "public" / "deep-research"
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "SKILL.md").write_text(_skill_content("deep-research"), encoding="utf-8")
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)

    runtime = SimpleNamespace(context={}, config={"configurable": {}})

    with pytest.raises(ValueError, match="built-in skill"):
        anyio.run(
            skill_manage_module.skill_manage_tool.coroutine,
            runtime,
            "patch",
            "deep-research",
            None,
            None,
            "Demo skill",
            "Patched",
        )


def test_skill_manage_sync_wrapper_supported(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    refresh_calls = []

    async def _refresh():
        refresh_calls.append("refresh")

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={"thread_id": "thread-sync"}, config={"configurable": {"thread_id": "thread-sync"}})
    result = skill_manage_module.skill_manage_tool.func(
        runtime=runtime,
        action="create",
        name="sync-skill",
        content=_skill_content("sync-skill"),
    )

    assert "Created custom skill" in result
    assert refresh_calls == ["refresh"]


def test_skill_manage_rejects_support_path_traversal(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    config = SimpleNamespace(
        skills=SimpleNamespace(get_skills_path=lambda: skills_root, container_path="/mnt/skills", use="kkoclaw.skills.storage.local_skill_storage:LocalSkillStorage"),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )
    monkeypatch.setattr("kkoclaw.config.get_app_config", lambda: config)
    monkeypatch.setattr("kkoclaw.skills.security_scanner.get_app_config", lambda: config)

    async def _refresh():
        return None

    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _refresh)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", lambda *args, **kwargs: _async_result("allow", "ok"))

    runtime = SimpleNamespace(context={"thread_id": "thread-1"}, config={"configurable": {"thread_id": "thread-1"}})
    anyio.run(skill_manage_module.skill_manage_tool.coroutine, runtime, "create", "demo-skill", _skill_content("demo-skill"))

    with pytest.raises(ValueError, match="parent-directory traversal|selected support directory"):
        anyio.run(
            skill_manage_module.skill_manage_tool.coroutine,
            runtime,
            "write_file",
            "demo-skill",
            "malicious overwrite",
            "references/../SKILL.md",
        )
