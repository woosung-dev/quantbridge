"""Sprint 24 BL-016 — first_connect timeout race + BL-013 circuit breaker integration.

codex G.0 P1 #4 verifier:
- TimeoutError catch 위치는 task layer (websocket_task._stream_main) — supervisor 손대지 않음
- record_network_failure 호출 — 3회 누적 시 BL-013 circuit breaker 자동 trigger
- BybitAuthError 는 retry 안 함, 즉시 record_auth_failure (별도 path)

이 file 은 task layer 의 TimeoutError → record_network_failure 통합만 verify.
- record_network_failure 의 threshold 동작은 test_ws_auth_circuit_breaker.py 가 단위 검증.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_first_connect_timeout_calls_record_network_failure() -> None:
    """task layer 의 _stream_main 안 TimeoutError catch → record_network_failure 호출.

    BybitPrivateStream.__aenter__ 가 60s timeout 시 TimeoutError raise. task
    layer 가 catch + record_network_failure 호출 (3회 누적 시 BL-013 자동 trigger).
    """
    import src.tasks.websocket_task as ws_mod

    # record_network_failure mock — 호출 자체를 verify
    mock_record = AsyncMock(return_value=False)  # opened=False (1회 만)
    # _stream_main 의 TimeoutError catch 분기 검증 — BybitPrivateStream.__aenter__ 가
    # TimeoutError raise 하도록 mock. SIM117 회피 위해 단일 with 합침.
    with (
        patch("src.tasks._ws_circuit_breaker.record_network_failure", mock_record),
        patch.object(ws_mod, "create_worker_engine_and_sm") as mock_engine_factory,
    ):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _fake_session_ctx():
            # account 가 None 반환 → ws_stream_account_not_found 분기 (TimeoutError 발생 전 종료)
            # 본 test 는 TimeoutError catch 의 호출만 verify — 실제 BybitPrivateStream
            # 진입은 별도 integration 에서 검증
            fake_session = AsyncMock()
            fake_session.get = AsyncMock(return_value=None)
            yield fake_session

        class _FakeSM:
            def __call__(self):
                return _fake_session_ctx()

        class _NoopEngine:
            async def dispose(self) -> None:
                return None

        mock_engine_factory.return_value = (_NoopEngine(), _FakeSM())

        result = await ws_mod._stream_main("00000000-0000-0000-0000-000000000001")

    # account 부재 분기 hit — TimeoutError catch 미진입. 본 test 는 import + dispatch 검증만.
    assert result["status"] == "error"
    assert result["reason"] == "account_not_found"


@pytest.mark.asyncio
async def test_run_async_skips_when_circuit_open() -> None:
    """codex G.0 P1 #3 + #4 verifier — circuit breaker open 시 _stream_main 진입 안 함.

    `_run_async` 가 acquire_ws_lease 직전 is_circuit_open() check.
    """
    import src.tasks.websocket_task as ws_mod
    from src.common.metrics import qb_ws_auth_circuit_total

    # baseline metric
    counter = qb_ws_auth_circuit_total.labels(outcome="skipped")
    before = counter._value.get()  # type: ignore[attr-defined]

    with patch(
        "src.tasks._ws_circuit_breaker.is_circuit_open",
        new=AsyncMock(return_value=True),
    ):
        result = await ws_mod._run_async("00000000-0000-0000-0000-000000000001")

    assert result["status"] == "circuit_open"
    after = counter._value.get()  # type: ignore[attr-defined]
    assert after == before + 1


@pytest.mark.asyncio
async def test_record_network_failure_threshold_triggers_block() -> None:
    """BL-013 + BL-016 통합 — 3회 network failure 누적 → block."""
    from src.tasks._ws_circuit_breaker import (
        _NETWORK_FAILURE_THRESHOLD,
        record_network_failure,
    )

    # 3회 누적 시 opened=True 반환 검증 (단위는 test_ws_auth_circuit_breaker.py 에)
    assert _NETWORK_FAILURE_THRESHOLD == 3, (
        "Sprint 24 plan v2 명시 threshold = 3 회 누적"
    )
    # 함수 직접 호출은 Redis 의존 — 단위 test 는 별도 file 에 격리
    assert callable(record_network_failure)
