"""전략 목록의 서버 정렬과 페이지네이션 순서를 검증한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.engine.metrics import SHARPE_CONVENTION_MONTHLY
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository

_BASE_TS = datetime(2024, 1, 1, tzinfo=UTC)
_IDS = {
    "zulu": UUID(int=1),
    "alpha": UUID(int=2),
    "charlie": UUID(int=3),
}


async def _seed_strategies(session: AsyncSession) -> tuple[UUID, dict[str, Strategy]]:
    user = User(
        id=UUID(int=10),
        auth_subject="strategy-sort-owner",
        email="strategy-sort@example.com",
    )
    session.add(user)
    await session.flush()

    rows: dict[str, Strategy] = {}
    values = {
        "zulu": ("Zulu", _BASE_TS, "0.2", "0.2"),
        "alpha": ("Alpha", _BASE_TS + timedelta(hours=1), "0.8", "0.8"),
        "charlie": ("Charlie", _BASE_TS + timedelta(hours=1), None, None),
    }
    for key, (name, updated_at, total_return, sharpe) in values.items():
        strategy = Strategy(
            id=_IDS[key],
            user_id=user.id,
            name=name,
            pine_source='//@version=5\nstrategy("sort")',
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
            created_at=_BASE_TS,
            updated_at=updated_at,
        )
        session.add(strategy)
        rows[key] = strategy
    await session.flush()

    for key, (_, updated_at, total_return, sharpe) in values.items():
        strategy = rows[key]
        metrics = None
        if total_return is not None:
            metrics = {
                "total_return": total_return,
                "sharpe_ratio": sharpe,
                "sharpe_convention": SHARPE_CONVENTION_MONTHLY,
            }
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
                metrics=metrics,
                equity_curve=[["2024-01-01T00:00:00Z", "1000"]],
                completed_at=updated_at,
                created_at=updated_at,
            )
        )
    await session.flush()
    return user.id, rows


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["asc", "desc"])
@pytest.mark.parametrize("order_by", ["updated_at", "name", "total_return", "sharpe_ratio"])
async def test_list_by_owner_sorts_before_pagination(
    db_session: AsyncSession,
    order_by: str,
    order: str,
) -> None:
    user_id, rows = await _seed_strategies(db_session)
    repository = StrategyRepository(db_session)

    expected_by_axis = {
        "updated_at": (
            ["zulu", "charlie", "alpha"] if order == "asc" else ["charlie", "alpha", "zulu"]
        ),
        "name": (["alpha", "charlie", "zulu"] if order == "asc" else ["zulu", "charlie", "alpha"]),
        "total_return": (
            ["zulu", "alpha", "charlie"] if order == "asc" else ["alpha", "zulu", "charlie"]
        ),
        "sharpe_ratio": (
            ["zulu", "alpha", "charlie"] if order == "asc" else ["alpha", "zulu", "charlie"]
        ),
    }
    items, total = await repository.list_by_owner(
        user_id,
        limit=20,
        offset=0,
        is_archived=False,
        order_by=order_by,
        order=order,
    )

    assert total == 3
    expected = expected_by_axis[order_by]
    assert [row.id for row in items] == [rows[key].id for key in expected]

    page, _ = await repository.list_by_owner(
        user_id,
        limit=2,
        offset=0,
        is_archived=False,
        order_by=order_by,
        order=order,
    )
    assert [row.id for row in page] == [rows[key].id for key in expected[:2]]
