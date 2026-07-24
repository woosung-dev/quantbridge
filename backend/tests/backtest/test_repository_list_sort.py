# 백테스트 목록 정렬과 대용량 equity_curve 지연 로드를 검증하는 테스트.
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from tests.backtest.test_repository import _seed_bt


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["asc", "desc"])
@pytest.mark.parametrize(
    "order_by", [
        "created_at",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "num_trades",
    ],
)
async def test_list_by_user_sorts_with_nulls_last_and_defers_equity_curve(
    db_session: AsyncSession,
    order_by: str,
    order: str,
) -> None:
    base = await _seed_bt(db_session, BacktestStatus.COMPLETED)
    started_at = datetime(2024, 1, 1, tzinfo=UTC)
    base.created_at = started_at
    base.metrics = None
    base.equity_curve = [["2024-01-01T00:00:00Z", "1000"]]
    records: dict[str, Backtest] = {"missing": base}
    values = {
        "low": "1",
        "tie_old": "2",
        "tie_new": "2",
        "high": "3",
    }
    for index, (name, value) in enumerate(values.items(), start=1):
        metrics = {
            "total_return": value,
            "max_drawdown": value,
            "sharpe_ratio": value,
            "num_trades": int(value),
        }
        record = Backtest(
            id=uuid4(),
            user_id=base.user_id,
            strategy_id=base.strategy_id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=started_at,
            period_end=started_at + timedelta(days=1),
            initial_capital=Decimal("1000"),
            status=BacktestStatus.COMPLETED,
            metrics=metrics,
            equity_curve=[["2024-01-01T00:00:00Z", "1000"]],
            created_at=started_at + timedelta(minutes=index),
        )
        db_session.add(record)
        records[name] = record
    await db_session.flush()
    db_session.expunge_all()

    rows, _ = await BacktestRepository(db_session).list_by_user(
        base.user_id,
        limit=20,
        offset=0,
        order_by=order_by,
        order=order,
    )

    if order_by == "created_at":
        ordered_names = ["missing", "low", "tie_old", "tie_new", "high"]
        if order == "desc":
            ordered_names.reverse()
    else:
        ordered_names = ["low", "tie_new", "tie_old", "high", "missing"]
        if order == "desc":
            ordered_names = ["high", "tie_new", "tie_old", "low", "missing"]

    assert [row.id for row in rows] == [records[name].id for name in ordered_names]
    assert all("equity_curve" in inspect(row).unloaded for row in rows)
