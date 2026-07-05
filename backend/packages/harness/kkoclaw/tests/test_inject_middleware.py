"""Tests for InjectMiddleware."""
from unittest.mock import MagicMock

import pytest

from kkoclaw.agents.middlewares.inject_middleware import InjectMiddleware
from kkoclaw.agents.middlewares.internal_messages import (
    INTERNAL_MIDDLEWARE_MESSAGE_KEY,
)


def _make_middleware():
    return InjectMiddleware()


def _make_state(pending=None, messages=None):
    return {"messages": messages or [], "pending_messages": pending or []}


def _runtime():
    return MagicMock()


class TestInjectMiddleware:
    def test_no_pending_returns_none(self):
        """空 pending → 不做任何改动。"""
        mw = _make_middleware()
        result = mw.before_model(_make_state(pending=[]), _runtime())
        assert result is None

    def test_single_pending_injects_one_message(self):
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": "帮我加个导出"}])
        result = mw.before_model(state, _runtime())
        assert result is not None
        assert len(result["messages"]) == 1
        assert result["pending_messages"] == []  # 清空

    def test_injected_message_is_hide_from_ui(self):
        """注入的消息必须 hide_from_ui=True（前端不重复显示）。"""
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": "x"}])
        result = mw.before_model(state, _runtime())
        msg = result["messages"][0]
        assert msg.additional_kwargs.get("hide_from_ui") is True
        assert msg.additional_kwargs.get(INTERNAL_MIDDLEWARE_MESSAGE_KEY) == "pending_message_inject"

    def test_multiple_pending_merged_into_one_message(self):
        mw = _make_middleware()
        state = _make_state(pending=[
            {"id": "m1", "content": "第一条"},
            {"id": "m2", "content": "第二条"},
        ])
        result = mw.before_model(state, _runtime())
        assert len(result["messages"]) == 1  # 合并为一条
        content = str(result["messages"][0].content)
        assert "第一条" in content
        assert "第二条" in content
        assert result["pending_messages"] == []

    def test_content_wrapped_with_supplement_prefix(self):
        """文案含'任务执行期间追加'引导语。"""
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": "顺便检查下"}])
        result = mw.before_model(state, _runtime())
        content = str(result["messages"][0].content)
        assert "任务执行期间追加" in content
        assert "顺便检查下" in content

    def test_empty_content_skipped(self):
        """content 为空的项被跳过；全空则返回 None。"""
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": ""}, {"id": "m2", "content": "   "}])
        result = mw.before_model(state, _runtime())
        assert result is None

    def test_mixed_empty_and_valid(self):
        """空 content 跳过，有效的正常注入。"""
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": ""}, {"id": "m2", "content": "有效"}])
        result = mw.before_model(state, _runtime())
        content = str(result["messages"][0].content)
        assert "有效" in content

    def test_caps_at_ten_messages(self):
        """超过 10 条只取最新 10 条（防 token 爆炸）。"""
        mw = _make_middleware()
        pending = [{"id": f"m{i}", "content": f"c{i}"} for i in range(15)]
        state = _make_state(pending=pending)
        result = mw.before_model(state, _runtime())
        content = str(result["messages"][0].content)
        # 最新 10 条 = m5..m14
        assert "c5" in content
        assert "c14" in content
        assert "c4" not in content  # 被截断

    @pytest.mark.asyncio
    async def test_async_before_model_same_as_sync(self):
        mw = _make_middleware()
        state = _make_state(pending=[{"id": "m1", "content": "x"}])
        sync_result = mw.before_model(state, _runtime())
        async_result = await mw.abefore_model(state, _runtime())
        # 两者结构一致
        assert sync_result["pending_messages"] == async_result["pending_messages"] == []
        assert len(sync_result["messages"]) == len(async_result["messages"]) == 1
