"""GET /api/v1/backtests/:id/trades — pagination + Decimal str."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


@pytest.mark.asyncio
async def test_trades_pagination_and_decimal_str(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    user = mock_clerk_auth
    strategy = Strategy(
        id=uuid4(), user_id=user.id, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    bt = Backtest(
        id=uuid4(), user_id=user.id, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"), status=BacktestStatus.COMPLETED,
    )
    db_session.add(bt)
    await db_session.flush()
    # 5 trades seed
    for i in range(5):
        db_session.add(BacktestTrade(
            id=uuid4(), backtest_id=bt.id, trade_index=i,
            direction=TradeDirection.LONG, status=TradeStatus.CLOSED,
            entry_time=datetime(2024, 1, 1, i, tzinfo=UTC),
            exit_time=datetime(2024, 1, 1, i + 1, tzinfo=UTC),
            entry_price=Decimal("100.12345678"), exit_price=Decimal("102.00000001"),
            size=Decimal("10"), pnl=Decimal("18.87654321"), return_pct=Decimal("0.018765"),
            fees=Decimal("0.10000000"),
        ))
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}/trades?limit=3&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert body["limit"] == 3
    assert body["offset"] == 0
    assert len(body["items"]) == 3

    first = body["items"][0]
    # Decimal → 문자열 직렬화 검증
    assert first["entry_price"] == "100.12345678"
    assert first["pnl"] == "18.87654321"
    assert first["direction"] == "long"
    assert first["status"] == "closed"


@pytest.mark.asyncio
async def test_trades_unknown_backtest_404(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    r = await client.get(f"/api/v1/backtests/{uuid4()}/trades")
    assert r.status_code == 404
