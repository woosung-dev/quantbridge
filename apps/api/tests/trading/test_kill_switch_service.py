"""KillSwitchService — evaluator 순회 + 이벤트 기록 + 재진입 차단."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.trading.exceptions import KillSwitchActive
from src.trading.kill_switch import EvaluationResult, KillSwitchService
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository


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


async def test_ensure_not_gated_records_event_and_raises_on_first_violation(
    db_session, strategy, user
):
    from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName

    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    repo = KillSwitchEventRepository(db_session)
    violating = _StaticEvaluator(
        EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )
    )
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


async def test_gated_event_publishes_to_the_account_owner_through_the_repository(
    db_session, strategy, user, monkeypatch
):
    """실시간 발행 대상 = 계정 소유자. 조회는 **repository 를 통해서만** 한다.

    ★이 경로는 2026-08-30 아키텍처 감사 전까지 **테스트가 0건**이었다 — 그래서 서비스가
    `repo.session` 을 꺼내 쓰던 것(apps/api/AGENTS.md §3 위반)이 오래 남아 있었다.
    구조 게이트는 `tests/common/test_repository_boundary_guard.py` 가 잡고, 여기서는 **동작**을 잰다.
    """
    from unittest.mock import AsyncMock

    from src.trading import kill_switch as kill_switch_module
    from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName

    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    publisher = AsyncMock()
    monkeypatch.setattr(kill_switch_module, "publish_realtime", publisher)

    repo = KillSwitchEventRepository(db_session)
    svc = KillSwitchService(
        evaluators=[
            _StaticEvaluator(
                EvaluationResult(
                    gated=True,
                    trigger_type="daily_loss",
                    trigger_value=Decimal("-600"),
                    threshold=Decimal("500"),
                )
            )
        ],
        events_repo=repo,
    )

    with pytest.raises(KillSwitchActive):
        await svc.ensure_not_gated(strategy_id=strategy.id, account_id=acc.id)

    publisher.assert_awaited_once()
    channel_user_id, event_name, payload = publisher.await_args.args
    assert channel_user_id == str(user.id)
    assert event_name == "kill_switch"
    assert payload["trigger_type"] == "daily_loss"


async def test_account_owner_lookup_returns_none_for_a_missing_account(db_session):
    """계정이 없으면 발행을 건너뛴다 — 서비스의 `if owner_id is not None` 분기 근거."""
    repo = KillSwitchEventRepository(db_session)

    assert await repo.get_account_user_id(uuid4()) is None
