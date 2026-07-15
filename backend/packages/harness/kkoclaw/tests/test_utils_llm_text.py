"""llm_text utilities behave per upstream contract."""
from kkoclaw.utils.llm_text import (
    strip_think_blocks,
    strip_markdown_code_fence,
    extract_response_text,
)


def test_strip_think_blocks_removes_complete_block():
    text = "before <think>secret</think> after"
    assert strip_think_blocks(text) == "before  after"


def test_strip_think_blocks_truncates_unclosed():
    assert strip_think_blocks("ok <think>truncated") == "ok"


def test_strip_think_blocks_preserves_unclosed_when_asked():
    assert strip_think_blocks("ok <think>truncated", truncate_unclosed=False) == "ok <think>truncated"


def test_strip_markdown_code_fence():
    assert strip_markdown_code_fence("```python\nprint(1)\n```") == "print(1)"
    assert strip_markdown_code_fence("plain text") == "plain text"


def test_extract_response_text_string():
    assert extract_response_text("hello") == "hello"


def test_extract_response_text_blocks():
    blocks = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    assert extract_response_text(blocks) == "a\nb"


def test_extract_response_text_none():
    assert extract_response_text(None) == ""
