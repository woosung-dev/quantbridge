"""Sprint 12 Phase A — KillSwitchService Slack alert hook TDD.

codex G0 #1 결정: hook 위치 = `KillSwitchService.ensure_not_gated()` 의
event save 직후 (Evaluator 가 아닌 Service layer).

3 시나리오:
1. 첫 gated 전이 시 alert 발송 (`send_critical_alert` 호출)
2. 기존 active 이벤트 있을 때 = alert 발송 없음 (이미 발송됐으므로)
3. Slack alert 실패 (Exception) → KillSwitchActive raise 는 정상 전파
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.trading.exceptions import KillSwitchActive
from src.trading.kill_switch import EvaluationResult, KillSwitchService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    KillSwitchEvent,
    KillSwitchTriggerType,
)
from src.trading.repository import KillSwitchEventRepository


class _StaticEvaluator:
    def __init__(self, result: EvaluationResult) -> None:
        self._r = result

    async def evaluate(self, ctx):  # type: ignore[no-untyped-def]
        return self._r


async def _flush_pending_alerts() -> None:
    """fire-and-forget task 가 완료될 시간 확보."""
    # asyncio loop 가 한 cycle 돌아 done_callback 실행되도록.
    for _ in range(5):
        await asyncio.sleep(0.01)


async def test_first_gated_transition_fires_alert(
    db_session, strategy, user, monkeypatch
):
    """gated=True 첫 전이 → KS event save → asyncio.create_task 로 send_critical_alert 호출."""
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    mock_alert = AsyncMock(return_value=True)
    monkeypatch.setattr("src.trading.kill_switch.send_critical_alert", mock_alert)

    repo = KillSwitchEventRepository(db_session)
    violating = _StaticEvaluator(
        EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )
    )
    svc = KillSwitchService(evaluators=[violating], events_repo=repo)
    with pytest.raises(KillSwitchActive, match="daily_loss"):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    await _flush_pending_alerts()

    assert mock_alert.call_count == 1
    args, kwargs = mock_alert.call_args
    # send_critical_alert(settings, title, message, context, *, client=None)
    title = args[1] if len(args) > 1 else kwargs["title"]
    message = args[2] if len(args) > 2 else kwargs["message"]
    context = args[3] if len(args) > 3 else kwargs.get("context")
    assert "daily_loss" in title
    assert "-600" in message or "500" in message
    assert context is not None
    assert context["trigger_type"] == "daily_loss"
    assert context["account_id"] == str(acc.id)


async def test_existing_active_event_does_not_alert(
    db_session, strategy, user, monkeypatch
):
    """기존 unresolved 이벤트 있으면 evaluator 순회 X + alert 발송 X (재발 방지)."""
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)

    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("12"),
        threshold=Decimal("10"),
    )
    db_session.add(event)
    await db_session.flush()

    mock_alert = AsyncMock(return_value=True)
    monkeypatch.setattr("src.trading.kill_switch.send_critical_alert", mock_alert)

    svc = KillSwitchService(
        evaluators=[_StaticEvaluator(EvaluationResult(gated=False))],
        events_repo=KillSwitchEventRepository(db_session),
    )
    with pytest.raises(KillSwitchActive, match="Active kill switch"):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    await _flush_pending_alerts()

    assert mock_alert.call_count == 0, "기존 active 이벤트는 alert 재발송 금지"


async def test_alert_failure_does_not_block_raise(
    db_session, strategy, user, monkeypatch
):
    """Slack alert 가 Exception 던져도 KillSwitchActive raise 는 정상 전파."""
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    mock_alert = AsyncMock(side_effect=RuntimeError("slack down"))
    monkeypatch.setattr("src.trading.kill_switch.send_critical_alert", mock_alert)

    repo = KillSwitchEventRepository(db_session)
    violating = _StaticEvaluator(
        EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )
    )
    svc = KillSwitchService(evaluators=[violating], events_repo=repo)

    # alert 실패 ≠ raise 차단 (real account FK 충족 위해 acc.id 사용)
    with pytest.raises(KillSwitchActive, match="daily_loss"):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    # alert 호출은 시도됐어야 함
    await _flush_pending_alerts()
    assert mock_alert.call_count == 1


async def test_pending_alerts_set_tracks_task(db_session, strategy, user, monkeypatch):
    """fire-and-forget task 가 module-level _PENDING_ALERTS 에 등록 + 완료 후 자동 제거."""
    from src.common import alert as alert_module

    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    # set 초기 상태 capture
    initial_size = len(alert_module._PENDING_ALERTS)

    # 느린 alert 로 task 가 set 에 머무는 시간 확보
    barrier = asyncio.Event()

    async def slow_alert(*args, **kwargs):  # type: ignore[no-untyped-def]
        await barrier.wait()
        return True

    monkeypatch.setattr("src.trading.kill_switch.send_critical_alert", slow_alert)

    repo = KillSwitchEventRepository(db_session)
    violating = _StaticEvaluator(
        EvaluationResult(
            gated=True,
            trigger_type="cumulative_loss",
            trigger_value=Decimal("12"),
            threshold=Decimal("10"),
        )
    )
    svc = KillSwitchService(evaluators=[violating], events_repo=repo)
    with pytest.raises(KillSwitchActive):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    # task 진입 시간 확보
    await asyncio.sleep(0.01)
    # task 가 _PENDING_ALERTS 에 들어가 있어야 함
    assert len(alert_module._PENDING_ALERTS) > initial_size

    # release → task 완료 → done_callback 으로 set 에서 자동 제거
    barrier.set()
    await _flush_pending_alerts()
    assert len(alert_module._PENDING_ALERTS) == initial_size
