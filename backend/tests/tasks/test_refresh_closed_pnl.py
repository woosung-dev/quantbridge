# closedPnl 즉시 갱신 작업의 재시도와 포기 알림을 검증한다.
"""refresh_closed_pnl Celery 재시도 회귀 테스트."""
from __future__ import annotations

import contextlib
from unittest.mock import Mock
from uuid import uuid4

from celery.exceptions import Retry


def _fake_worker_loop(behaviors):
    """전달 coroutine을 닫고 정해진 작업 결과를 순서대로 반환한다."""
    sequence = iter(behaviors)

    def _run(coro):
        with contextlib.suppress(Exception):
            coro.close()
        outcome = next(sequence)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return _run


def _drive_task(monkeypatch, *, retries: int, behaviors):
    from src.tasks import _worker_loop as worker_loop
    from src.tasks.trading import refresh_closed_pnl_task as task

    monkeypatch.setattr(worker_loop, "run_in_worker_loop", _fake_worker_loop(behaviors))
    monkeypatch.setattr(task, "retry", Mock(side_effect=lambda **_kw: Retry()))
    task.push_request(retries=retries)
    try:
        try:
            return task.run(str(uuid4())), task.retry, None
        except Retry as exc:
            return None, task.retry, exc
    finally:
        task.pop_request()


def test_transient_closed_pnl_retries(monkeypatch) -> None:
    """Bybit 정산 지연은 5초 지수 백오프로 재시도한다."""
    _result, retry, raised = _drive_task(
        monkeypatch,
        retries=1,
        behaviors=[{"transient": "closed_pnl_not_yet_available"}],
    )
    assert raised is not None
    assert retry.call_args.kwargs["countdown"] == 10


def test_closed_pnl_provider_failure_retries(monkeypatch) -> None:
    """provider 예외도 같은 지수 백오프 사다리를 사용한다."""
    _result, retry, raised = _drive_task(monkeypatch, retries=0, behaviors=[RuntimeError("offline")])
    assert raised is not None
    assert retry.call_args.kwargs["countdown"] == 5


def test_closed_pnl_transient_exhaustion_alerts(monkeypatch) -> None:
    """정산을 끝내 찾지 못하면 추정 손익 사용 사실을 알리고 재시도하지 않는다."""
    from src.tasks import trading as trading_mod

    alert = Mock(return_value=None)
    monkeypatch.setattr(trading_mod, "_alert_closed_pnl_unbackfilled", alert)
    result, retry, raised = _drive_task(
        monkeypatch,
        retries=trading_mod._CLOSED_PNL_MAX_RETRIES,
        behaviors=[{"transient": "closed_pnl_not_yet_available"}, None],
    )
    assert raised is None
    assert result["failed"] == "closed_pnl_not_yet_available"
    retry.assert_not_called()
    alert.assert_called_once()


def test_closed_pnl_provider_exhaustion_alerts_and_counts(monkeypatch) -> None:
    """provider 장애가 재시도를 소진하면 failed_provider 를 계상하고 알림 뒤 멈춘다."""
    from src.common.metrics import qb_closed_pnl_backfill_total
    from src.tasks import trading as trading_mod

    counter = qb_closed_pnl_backfill_total.labels(outcome="failed_provider")
    before = counter._value.get()
    alert = Mock(return_value=None)
    monkeypatch.setattr(trading_mod, "_alert_closed_pnl_unbackfilled", alert)
    result, retry, raised = _drive_task(
        monkeypatch,
        retries=trading_mod._CLOSED_PNL_MAX_RETRIES,
        behaviors=[RuntimeError("offline"), None],
    )
    assert raised is None
    assert result["failed"] == "provider_error"
    retry.assert_not_called()
    alert.assert_called_once()
    assert counter._value.get() == before + 1


def test_closed_pnl_transient_exhaustion_counts_never_found(monkeypatch) -> None:
    """정산 행을 끝내 못 찾은 경우도 metric 으로 남아야 운영이 감지할 수 있다."""
    from src.common.metrics import qb_closed_pnl_backfill_total
    from src.tasks import trading as trading_mod

    counter = qb_closed_pnl_backfill_total.labels(outcome="never_found")
    before = counter._value.get()
    monkeypatch.setattr(trading_mod, "_alert_closed_pnl_unbackfilled", Mock(return_value=None))
    _drive_task(
        monkeypatch,
        retries=trading_mod._CLOSED_PNL_MAX_RETRIES,
        behaviors=[{"transient": "closed_pnl_not_yet_available"}, None],
    )
    assert counter._value.get() == before + 1


async def test_unbackfilled_alert_goes_to_both_channels(monkeypatch) -> None:
    """추정 손익으로 리스크 게이트가 돈다는 사실은 Slack·Telegram 양쪽으로 알린다."""
    from src.tasks import trading as trading_mod
    from src.trading.models import AlertChannel

    sent: list[dict] = []

    async def _fake(_settings, **kwargs):
        sent.append(kwargs)
        return {"slack": True, "telegram": True}

    monkeypatch.setattr(trading_mod, "send_rule_alert", _fake)
    await trading_mod._alert_closed_pnl_unbackfilled(uuid4(), "provider_error")

    assert len(sent) == 1
    assert sent[0]["channel"] is AlertChannel.both
    assert sent[0]["context"]["reason"] == "provider_error"
