"""trace_context helpers behave per upstream deer-flow contract."""
from kkoclaw.trace_context import (
    TRACE_ID_HEADER,
    generate_trace_id,
    normalize_trace_id,
    request_trace_context,
    get_current_trace_id,
)


def test_trace_id_header_constant():
    assert TRACE_ID_HEADER == "X-Trace-Id"


def test_generate_trace_id_is_hex():
    tid = generate_trace_id()
    assert len(tid) == 32
    int(tid, 16)  # raises if not hex


def test_normalize_rejects_non_ascii_and_controls():
    assert normalize_trace_id("abc-123") == "abc-123"
    assert normalize_trace_id("non ascii ☃") is None
    assert normalize_trace_id("with\x00null") is None
    assert normalize_trace_id("") is None
    assert normalize_trace_id(None) is None


def test_request_trace_context_binds_then_restores():
    assert get_current_trace_id() is None
    with request_trace_context("req-1") as tid:
        assert tid == "req-1"
        assert get_current_trace_id() == "req-1"
    assert get_current_trace_id() is None
