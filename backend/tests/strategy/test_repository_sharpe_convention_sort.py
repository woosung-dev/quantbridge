"""전략 목록 Sharpe 정렬의 등급·페이지 경계·payload 보존 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.engine.metrics import (
    SHARPE_CONVENTION_DAILY,
    SHARPE_CONVENTION_MONTHLY,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
)
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository
from src.strategy.service import StrategyService

_BASE_TS = datetime(2024, 1, 1, tzinfo=UTC)
_IDS = {
    "high": UUID(int=101),
    "low": UUID(int=102),
    "legacy": UUID(int=103),
    "bankrupt": UUID(int=104),
}


def _metrics(value: str, convention: str | None) -> dict[str, object]:
    metrics: dict[str, object] = {
        "total_return": "0.1",
        "max_drawdown": "-0.1",
        "sharpe_ratio": value,
        "num_trades": 3,
    }
    if convention is not None:
        metrics["sharpe_convention"] = convention
    return metrics


async def _seed_rows(session: AsyncSession) -> tuple[UUID, dict[str, Strategy]]:
    user = User(
        id=UUID(int=110),
        clerk_user_id="strategy-sharpe-owner",
        email="strategy-sharpe@example.com",
    )
    session.add(user)
    await session.flush()

    values = {
        "high": ("High", "0.5", SHARPE_CONVENTION_MONTHLY),
        "low": ("Low", "-0.3", SHARPE_CONVENTION_DAILY),
        "legacy": ("Legacy", "99", None),
        "bankrupt": ("Bankrupt", "0", SHARPE_CONVENTION_NONPOSITIVE_EQUITY),
    }
    rows: dict[str, Strategy] = {}
    for index, (key, (name, value, convention)) in enumerate(values.items(), start=1):
        strategy = Strategy(
            id=_IDS[key],
            user_id=user.id,
            name=name,
            pine_source='//@version=5\nstrategy("sharpe")',
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
            created_at=_BASE_TS,
            updated_at=_BASE_TS + timedelta(minutes=index),
        )
        session.add(strategy)
        rows[key] = strategy
    await session.flush()

    for index, (key, (_, value, convention)) in enumerate(values.items(), start=1):
        strategy = rows[key]
        session.add(
            Backtest(
                user_id=user.id,
                strategy_id=strategy.id,
                symbol="BTCUSDT",
                timeframe="1h",
                period_start=_BASE_TS,
                period_end=_BASE_TS + timedelta(days=1),
                initial_capital=Decimal("1000"),
                status=BacktestStatus.COMPLETED,
                metrics=_metrics(value, convention),
                equity_curve=[["2024-01-01T00:00:00Z", "1000"]],
                completed_at=_BASE_TS + timedelta(minutes=index),
                created_at=_BASE_TS + timedelta(minutes=index),
            )
        )
    await session.flush()
    return user.id, rows


@pytest.mark.asyncio
async def test_grade_order_survives_pagination(db_session: AsyncSession) -> None:
    user_id, rows = await _seed_rows(db_session)
    repository = StrategyRepository(db_session)
    by_id = {strategy.id: name for name, strategy in rows.items()}
    paged: list[str] = []

    for offset in (0, 2):
        items, total = await repository.list_by_owner(
            user_id,
            limit=2,
            offset=offset,
            is_archived=False,
            order_by="sharpe_ratio",
            order="desc",
        )
        assert total == 4
        paged.extend(by_id[item.id] for item in items)

    assert paged == ["high", "low", "legacy", "bankrupt"]


@pytest.mark.asyncio
async def test_payload_sharpe_ratio_is_not_normalized(db_session: AsyncSession) -> None:
    user_id, rows = await _seed_rows(db_session)
    service = StrategyService(
        StrategyRepository(db_session),
        BacktestRepository(db_session),
    )

    response = await service.list(
        owner_id=user_id,
        limit=4,
        offset=0,
        parse_status=None,
        is_archived=False,
        order_by="sharpe_ratio",
        order="desc",
    )
    metrics_by_id = {
        item.id: item.latest_backtest.metrics.sharpe_ratio
        for item in response.items
        if item.latest_backtest is not None and item.latest_backtest.metrics is not None
    }

    assert response.items[0].latest_backtest is not None
    assert response.items[0].latest_backtest.metrics is not None
    assert response.items[0].latest_backtest.metrics.sharpe_ratio == Decimal("0.5")
    assert metrics_by_id[rows["low"].id] == Decimal("-0.3")
    assert metrics_by_id[rows["bankrupt"].id] == Decimal("0")
