"""GET /api/v1/backtests — pagination + ownership isolation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_backtest(
    session: AsyncSession,
    user_id,
    symbol: str = "BTCUSDT",
    *,
    status: BacktestStatus = BacktestStatus.COMPLETED,
    metrics: dict[str, object] | None = None,
) -> Backtest:
    """테스트용 Strategy + Backtest 시드 생성 헬퍼."""
    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()  # FK constraint: backtests.strategy_id 삽입 전 strategies 먼저
    bt = Backtest(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        symbol=symbol,
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("1000"),
        status=status,
        metrics=metrics,
    )
    session.add(bt)
    return bt


@pytest.mark.asyncio
async def test_list_empty(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user,
) -> None:
    """백테스트 없음 → 빈 목록 + 기본 페이지네이션 값."""
    _: User = mock_authed_user

    r = await client.get("/api/v1/backtests")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user,
) -> None:
    """3건 시드, limit=2 → items=2 반환, total=3."""
    authed_user: User = mock_authed_user

    for _ in range(3):
        await _seed_backtest(db_session, authed_user.id)
    await db_session.commit()

    r = await client.get("/api/v1/backtests?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_ownership_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user,
) -> None:
    """타 유저 backtest는 목록에 노출되지 않음."""
    authed_user: User = mock_authed_user

    other_user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(other_user)
    await _seed_backtest(db_session, other_user.id, symbol="OTHER")
    await _seed_backtest(db_session, authed_user.id, symbol="MINE")
    await db_session.commit()

    r = await client.get("/api/v1/backtests")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "MINE"


@pytest.mark.asyncio
async def test_list_projects_metrics_summary_and_sorts_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user,
) -> None:
    user: User = mock_authed_user
    completed = await _seed_backtest(
        db_session,
        user.id,
        symbol="HIGH",
        metrics={
            "total_return": "0.20",
            "net_profit_abs": "200",
            "sharpe_ratio": "1.5",
            "max_drawdown": "-0.10",
            "num_trades": 7,
            "total_open_trades": 1,
        },
    )
    await _seed_backtest(
        db_session,
        user.id,
        symbol="LOW",
        metrics={
            "total_return": "0.10",
            "sharpe_ratio": "1.0",
            "max_drawdown": "-0.20",
            "num_trades": 3,
        },
    )
    pending = await _seed_backtest(
        db_session,
        user.id,
        symbol="PENDING",
        status=BacktestStatus.QUEUED,
    )
    await db_session.commit()

    response = await client.get("/api/v1/backtests?order_by=total_return&order=desc")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["symbol"] for item in items] == ["HIGH", "LOW", "PENDING"]
    completed_item = next(item for item in items if item["id"] == str(completed.id))
    pending_item = next(item for item in items if item["id"] == str(pending.id))
    assert completed_item["metrics_summary"] == {
        "total_return": "0.20",
        "net_profit_abs": "200",
        "sharpe_ratio": "1.5",
        # BL-398: 구 실행 JSONB 에는 sharpe_convention 키가 없다 → None.
        # FE 가 이걸 보고 "구 기준(봉 수익률 · 무위험 0%)" 으로 표기한다.
        "sharpe_convention": None,
        "max_drawdown": "-0.10",
        "num_trades": 7,
        "total_open_trades": 1,
    }
    assert pending_item["metrics_summary"] is None


@pytest.mark.asyncio
async def test_list_rejects_unknown_sort_axis(
    client: AsyncClient,
    mock_authed_user,
) -> None:
    response = await client.get("/api/v1/backtests?order_by=bad")

    assert response.status_code == 422
