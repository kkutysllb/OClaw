"""Tests for POST /api/threads/{thread_id}/runs/{run_id}/inject route.

Unit-tests the route handler ``inject_message`` directly with mocked
dependencies — no ASGI server, no real agent construction. Mirrors the
unit-test style used by the other tests in this directory.

Auth bypass: the ``@require_permission`` / ``@require_auth`` decorators
detect ``request._kkoclaw_test_bypass_auth = True`` and short-circuit to
calling the underlying function (see app/gateway/authz.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Make 'app' and 'kkoclaw' importable (mirrors tests/conftest.py setup,
# but this directory has no conftest of its own).
_BACKEND = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "packages" / "harness"))

from app.gateway.routers.thread_runs import InjectRequest, inject_message  # noqa: E402
from kkoclaw.runtime import RunStatus  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request() -> MagicMock:
    """A request stub that bypasses authz decorators + exposes app.state."""
    request = MagicMock()
    request._kkoclaw_test_bypass_auth = True
    request.app.state.checkpointer = MagicMock(name="shared-checkpointer")
    return request


def _make_record(
    *,
    thread_id: str = "t1",
    run_id: str = "r1",
    status: RunStatus = RunStatus.running,
) -> MagicMock:
    record = MagicMock()
    record.thread_id = thread_id
    record.run_id = run_id
    record.status = status
    return record


def _make_run_mgr(record) -> MagicMock:
    mgr = MagicMock()
    mgr.get = AsyncMock(return_value=record)
    return mgr


def _make_agent() -> MagicMock:
    """A fake agent whose aupdate_state is an AsyncMock we can assert on."""
    agent = MagicMock()
    agent.aupdate_state = AsyncMock()
    return agent


def _make_body(
    *,
    content: str = "顺便检查下日志",
    message_id: str = "m1",
    queued_at: int = 1,
    attachments: list | None = None,
) -> InjectRequest:
    return InjectRequest(
        content=content,
        message_id=message_id,
        queued_at=queued_at,
        attachments=attachments,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inject_run_not_found():
    """run_mgr.get returns None → 404."""
    from fastapi import HTTPException

    request = _make_request()
    run_mgr = _make_run_mgr(None)

    with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
        gc.return_value = MagicMock()
        with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
            mk.return_value = _make_agent()
            with pytest.raises(HTTPException) as exc:
                await inject_message(
                    "t1",
                    "r1",
                    _make_body(),
                    request=request,
                    run_mgr=run_mgr,
                )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_inject_run_already_ended():
    """run status is terminal (success/interrupted/error) → 409 with detail.code == 'run_not_active'."""
    from fastapi import HTTPException

    for status in (RunStatus.success, RunStatus.interrupted, RunStatus.error):
        request = _make_request()
        run_mgr = _make_run_mgr(_make_record(status=status))

        with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
            gc.return_value = MagicMock()
            with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
                mk.return_value = _make_agent()
                with pytest.raises(HTTPException) as exc:
                    await inject_message("t1", "r1", _make_body(), request=request, run_mgr=run_mgr)

        assert exc.value.status_code == 409, f"status={status}"
        detail = exc.value.detail
        assert isinstance(detail, dict)
        assert detail["code"] == "run_not_active"


@pytest.mark.asyncio
async def test_inject_empty_content():
    """content is whitespace → 422."""
    from fastapi import HTTPException

    request = _make_request()
    run_mgr = _make_run_mgr(_make_record())

    with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
        gc.return_value = MagicMock()
        with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
            mk.return_value = _make_agent()
            with pytest.raises(HTTPException) as exc:
                await inject_message(
                    "t1",
                    "r1",
                    _make_body(content="   "),
                    request=request,
                    run_mgr=run_mgr,
                )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_inject_thread_mismatch():
    """record.thread_id != path thread_id → 404 (mismatch = not found)."""
    from fastapi import HTTPException

    request = _make_request()
    # record belongs to a different thread
    run_mgr = _make_run_mgr(_make_record(thread_id="other-thread"))

    with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
        gc.return_value = MagicMock()
        with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
            mk.return_value = _make_agent()
            with pytest.raises(HTTPException) as exc:
                await inject_message("t1", "r1", _make_body(), request=request, run_mgr=run_mgr)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_inject_success():
    """valid running run → 202, body correct, aupdate_state called with right config + payload."""
    from fastapi.responses import JSONResponse

    request = _make_request()
    run_mgr = _make_run_mgr(_make_record(status=RunStatus.running))
    fake_agent = _make_agent()

    with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
        shared_saver = MagicMock(name="shared-saver")
        gc.return_value = shared_saver
        with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
            mk.return_value = fake_agent

            resp = await inject_message(
                "t1",
                "r1",
                _make_body(content="帮我加个导出", message_id="m-xyz", queued_at=99),
                request=request,
                run_mgr=run_mgr,
            )

    # ① Response shape
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 202
    body = json.loads(resp.body.decode())
    assert body["status"] == "accepted"
    assert body["message_id"] == "m-xyz"
    assert body["run_id"] == "r1"

    # ② make_lead_agent constructed, shared checkpointer attached
    assert mk.called
    assert fake_agent.checkpointer is shared_saver

    # ③ aupdate_state called with correct config + payload
    fake_agent.aupdate_state.assert_awaited_once()
    call_args = fake_agent.aupdate_state.await_args
    config_arg, payload = call_args.args
    assert config_arg["configurable"]["thread_id"] == "t1"
    assert config_arg["configurable"].get("checkpoint_ns") == ""
    pending = payload["pending_messages"]
    assert len(pending) == 1
    msg = pending[0]
    assert msg["id"] == "m-xyz"
    assert msg["content"] == "帮我加个导出"
    assert msg["queued_at"] == 99
    assert msg["source"] == "inject"


@pytest.mark.asyncio
async def test_inject_pending_status_allowed():
    """pending (not yet running) is also a valid inject target → 202."""
    from fastapi.responses import JSONResponse

    request = _make_request()
    run_mgr = _make_run_mgr(_make_record(status=RunStatus.pending))
    fake_agent = _make_agent()

    with patch("app.gateway.routers.thread_runs.get_checkpointer") as gc:
        gc.return_value = MagicMock()
        with patch("kkoclaw.agents.lead_agent.agent.make_lead_agent") as mk:
            mk.return_value = fake_agent
            resp = await inject_message("t1", "r1", _make_body(), request=request, run_mgr=run_mgr)

    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 202
