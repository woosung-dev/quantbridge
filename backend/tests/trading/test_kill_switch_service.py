"""KillSwitchService — evaluator 순회 + 이벤트 기록 + 재진입 차단."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.trading.exceptions import KillSwitchActive
from src.trading.kill_switch import EvaluationResult, KillSwitchService
from src.trading.repository import KillSwitchEventRepository


class _StaticEvaluator:
    """테스트용 fixture evaluator."""

    def __init__(self, result: EvaluationResult) -> None:
        self._r = result

    async def evaluate(self, ctx):
        return self._r


async def test_ensure_not_gated_passes_when_all_evaluators_clean(db_session, strategy):
    repo = KillSwitchEventRepository(db_session)
    svc = KillSwitchService(
        evaluators=[_StaticEvaluator(EvaluationResult(gated=False))],
        events_repo=repo,
    )
    await svc.ensure_not_gated(strategy_id=strategy.id, account_id=uuid4())


async def test_ensure_not_gated_records_event_and_raises_on_first_violation(db_session, strategy, user):
    from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName

    acc = ExchangeAccount(
        user_id=user.id, exchange=ExchangeName.bybit, mode=ExchangeMode.demo,
        api_key_encrypted=b"k", api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    repo = KillSwitchEventRepository(db_session)
    violating = _StaticEvaluator(EvaluationResult(
        gated=True, trigger_type="daily_loss",
        trigger_value=Decimal("-600"), threshold=Decimal("500"),
    ))
    second = _StaticEvaluator(EvaluationResult(gated=False))

    svc = KillSwitchService(evaluators=[violating, second], events_repo=repo)
    with pytest.raises(KillSwitchActive, match="daily_loss"):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    await repo.commit()

    active = await repo.get_active(strategy_id=strategy.id, account_id=acc.id)
    assert active is not None
    assert active.trigger_type.value == "daily_loss"


async def test_existing_active_event_blocks_without_reevaluation(db_session, strategy, user):
    """기존 unresolved 이벤트가 있으면 evaluator 순회를 건너뛰고 즉시 raise."""
    from src.trading.models import (
        ExchangeAccount,
        ExchangeMode,
        ExchangeName,
        KillSwitchEvent,
        KillSwitchTriggerType,
    )

    acc = ExchangeAccount(
        user_id=user.id, exchange=ExchangeName.bybit, mode=ExchangeMode.demo,
        api_key_encrypted=b"k", api_secret_encrypted=b"s",
    )
    db_session.add(acc)

    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=strategy.id,
        trigger_value=Decimal("12"), threshold=Decimal("10"),
    )
    db_session.add(event)
    await db_session.flush()

    evaluator_called = False

    class _FailIfCalled:
        async def evaluate(self, ctx):
            nonlocal evaluator_called
            evaluator_called = True
            return EvaluationResult(gated=False)

    svc = KillSwitchService(
        evaluators=[_FailIfCalled()],
        events_repo=KillSwitchEventRepository(db_session),
    )
    with pytest.raises(KillSwitchActive, match="Active kill switch"):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    assert evaluator_called is False, "기존 active 이벤트 있을 때 evaluator 호출 금지"
