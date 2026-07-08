import pytest
from pathlib import Path
from langgraph.runtime import Runtime

from kkoclaw.agents.middlewares.thread_data_middleware import ThreadDataMiddleware


def _as_posix(path: str) -> str:
    return path.replace("\\", "/")


class TestThreadDataMiddleware:
    def test_before_agent_returns_paths_when_thread_id_present_in_context(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)

        result = middleware.before_agent(state={}, runtime=Runtime(context={"thread_id": "thread-123"}))

        assert result is not None
        assert _as_posix(result["thread_data"]["workspace_path"]).endswith("threads/thread-123/user-data/workspace")
        assert _as_posix(result["thread_data"]["uploads_path"]).endswith("threads/thread-123/user-data/uploads")
        assert _as_posix(result["thread_data"]["outputs_path"]).endswith("threads/thread-123/user-data/outputs")

    def test_before_agent_uses_thread_id_from_configurable_when_context_is_none(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context=None)
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-from-config"}},
        )

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert _as_posix(result["thread_data"]["workspace_path"]).endswith("threads/thread-from-config/user-data/workspace")
        assert runtime.context is None

    def test_before_agent_uses_thread_id_from_configurable_when_context_missing_thread_id(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context={})
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-from-config"}},
        )

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert _as_posix(result["thread_data"]["uploads_path"]).endswith("threads/thread-from-config/user-data/uploads")
        assert runtime.context == {}

    def test_before_agent_raises_clear_error_when_thread_id_missing_everywhere(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {}},
        )

        with pytest.raises(ValueError, match="Thread ID is required in runtime context or config.configurable"):
            middleware.before_agent(state={}, runtime=Runtime(context=None))

    def test_coding_project_root_uses_home_scratch_workspace(self, tmp_path, monkeypatch):
        project_root = tmp_path / "project"
        project_root.mkdir()
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": "coding-thread", "project_root": str(project_root)}},
        )
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path / "kkoclaw"), lazy_init=True)

        result = middleware.before_agent(state={}, runtime=Runtime(context=None))

        assert result is not None
        thread_data = result["thread_data"]
        assert thread_data["project_root"] == str(project_root)
        assert Path(thread_data["workspace_path"]).resolve() != project_root.resolve()
        assert _as_posix(thread_data["workspace_path"]).endswith(".oclaw-coding/coding-thread/workspace")

    def test_coding_project_root_from_runtime_context_uses_scratch_workspace(self, tmp_path, monkeypatch):
        project_root = tmp_path / "project"
        project_root.mkdir()
        home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {}},
        )
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path / "kkoclaw"), lazy_init=True)

        result = middleware.before_agent(
            state={},
            runtime=Runtime(
                context={
                    "thread_id": "coding-context-thread",
                    "project_root": str(project_root),
                },
            ),
        )

        assert result is not None
        thread_data = result["thread_data"]
        assert thread_data["project_root"] == str(project_root)
        assert Path(thread_data["workspace_path"]).resolve() != project_root.resolve()
        assert _as_posix(thread_data["workspace_path"]).endswith(".oclaw-coding/coding-context-thread/workspace")

    def test_user_workspace_path_redirects_outputs_path(self, tmp_path):
        """When the user selects a workspace directory via WorkspaceSelector,
        ``outputs_path`` is redirected there so deliverables land in the
        user's chosen directory instead of the default sandbox outputs dir.
        ``workspace_path``/``uploads_path`` stay on the internal sandbox.
        """
        user_workspace = tmp_path / "user-project"
        user_workspace.mkdir()
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path / "kkoclaw"), lazy_init=True)

        result = middleware.before_agent(
            state={},
            runtime=Runtime(
                context={
                    "thread_id": "thread-ws",
                    "user_workspace_path": str(user_workspace),
                },
            ),
        )

        assert result is not None
        thread_data = result["thread_data"]
        # outputs_path now points at the user-selected directory
        assert thread_data["outputs_path"] == str(user_workspace)
        assert thread_data["user_workspace_path"] == str(user_workspace)
        # workspace_path / uploads_path remain on the internal sandbox dirs
        assert _as_posix(thread_data["workspace_path"]).endswith("threads/thread-ws/user-data/workspace")
        assert _as_posix(thread_data["uploads_path"]).endswith("threads/thread-ws/user-data/uploads")
        # outputs_path must NOT be the sandbox default
        assert not _as_posix(thread_data["outputs_path"]).endswith("threads/thread-ws/user-data/outputs")

    def test_user_workspace_path_from_configurable_redirects_outputs_path(self, tmp_path, monkeypatch):
        """The workspace path can also arrive via ``config.configurable``
        (e.g. cron scheduler / internal callers). It must redirect
        ``outputs_path`` the same way as the runtime context path.
        """
        user_workspace = tmp_path / "user-project"
        user_workspace.mkdir()
        monkeypatch.setattr(
            "kkoclaw.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"user_workspace_path": str(user_workspace)}},
        )
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path / "kkoclaw"), lazy_init=True)

        result = middleware.before_agent(
            state={},
            runtime=Runtime(context={"thread_id": "thread-ws-cfg"}),
        )

        assert result is not None
        thread_data = result["thread_data"]
        assert thread_data["outputs_path"] == str(user_workspace)
        assert thread_data["user_workspace_path"] == str(user_workspace)
