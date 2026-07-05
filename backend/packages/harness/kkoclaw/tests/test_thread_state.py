"""Tests for ThreadState reducers."""
from kkoclaw.agents.thread_state import merge_pending_messages


class TestMergePendingMessages:
    def test_append_to_empty(self):
        msg = {"id": "m1", "content": "hello"}
        result = merge_pending_messages([], [msg])
        assert result == [msg]

    def test_append_to_existing(self):
        existing = [{"id": "m1", "content": "first"}]
        new = [{"id": "m2", "content": "second"}]
        result = merge_pending_messages(existing, new)
        assert result == [{"id": "m1", "content": "first"}, {"id": "m2", "content": "second"}]

    def test_empty_right_clears(self):
        """显式传空 list → 清空（middleware 消费后清空）。"""
        existing = [{"id": "m1", "content": "first"}]
        result = merge_pending_messages(existing, [])
        assert result == []

    def test_dedup_by_id(self):
        """相同 id 的消息不重复追加。"""
        existing = [{"id": "m1", "content": "first"}]
        new = [{"id": "m1", "content": "first-dup"}, {"id": "m2", "content": "second"}]
        result = merge_pending_messages(existing, new)
        # m1 已存在被跳过，只追加 m2
        assert len(result) == 2
        assert result[0]["content"] == "first"  # 原值保留
        assert result[1]["id"] == "m2"

    def test_append_preserves_order(self):
        msgs = [{"id": f"m{i}", "content": str(i)} for i in range(3)]
        result = merge_pending_messages([], msgs)
        assert [m["id"] for m in result] == ["m0", "m1", "m2"]

    def test_message_without_id_always_appended(self):
        """无 id 的消息无法去重，总是追加。"""
        result = merge_pending_messages([], [{"content": "no-id"}])
        assert len(result) == 1

    def test_right_none_keeps_left(self):
        """right=None → 保持 left（superstep 无写入时 reducer 仍可能被调用）。"""
        existing = [{"id": "m1", "content": "first"}]
        result = merge_pending_messages(existing, None)
        assert result == existing

    def test_append_when_left_none(self):
        """首 superstep：left=None 视为空并追加。"""
        msg = {"id": "m1", "content": "hello"}
        result = merge_pending_messages(None, [msg])
        assert result == [msg]

    def test_dedup_within_right_batch(self):
        """right 内部含重复 id 时只保留第一个。"""
        result = merge_pending_messages([], [{"id": "m1", "content": "a"}, {"id": "m1", "content": "b"}])
        assert len(result) == 1
        assert result[0]["content"] == "a"
