# 알림 규칙 서비스의 소유권·중복·commit 계약을 검증한다

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.strategy.exceptions import StrategyNotFoundError
from src.trading.exceptions import AlertRuleAlreadyActive
from src.trading.models import AlertChannel, LiveSignalInterval, LiveSignalSession
from src.trading.schemas import AlertRuleCreateRequest
from src.trading.services.alert_rule_service import AlertRuleService


def _session(user_id):
    return LiveSignalSession(
        id=uuid4(),
        user_id=user_id,
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
    )


@pytest.mark.asyncio
async def test_create_commits_after_owned_session() -> None:
    user_id = uuid4()
    live_session = _session(user_id)
    repo = AsyncMock()
    repo.create.side_effect = lambda rule: rule
    sessions = AsyncMock()
    sessions.get_by_id.return_value = live_session
    service = AlertRuleService(repo, sessions)

    rule = await service.create(
        user_id,
        live_session.id,
        AlertRuleCreateRequest(
            rule_type="loss_limit", threshold_percent="12.5", channel=AlertChannel.both
        ),
    )

    assert rule.threshold_percent == Decimal("12.5")
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_rejects_foreign_session() -> None:
    repo = AsyncMock()
    sessions = AsyncMock()
    sessions.get_by_id.return_value = _session(uuid4())
    service = AlertRuleService(repo, sessions)

    with pytest.raises(StrategyNotFoundError):
        await service.create(
            uuid4(),
            uuid4(),
            AlertRuleCreateRequest(rule_type="watchdog", channel=AlertChannel.slack),
        )
    repo.create.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_maps_active_type_duplicate_to_409_domain_error() -> None:
    user_id = uuid4()
    live_session = _session(user_id)
    repo = AsyncMock()
    repo.create.side_effect = IntegrityError("insert", {}, Exception("unique"))
    sessions = AsyncMock()
    sessions.get_by_id.return_value = live_session
    service = AlertRuleService(repo, sessions)

    with pytest.raises(AlertRuleAlreadyActive) as exc:
        await service.create(
            user_id,
            live_session.id,
            AlertRuleCreateRequest(rule_type="watchdog", channel=AlertChannel.slack),
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "alert_rule_already_active"
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_awaited()


def test_loss_limit_requires_threshold_and_watchdog_forbids_it() -> None:
    with pytest.raises(ValueError):
        AlertRuleCreateRequest(rule_type="loss_limit", channel="slack")
    with pytest.raises(ValueError):
        AlertRuleCreateRequest(rule_type="watchdog", threshold_percent="1", channel="slack")
