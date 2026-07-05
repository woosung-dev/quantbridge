"""GET /api/v1/live-sessions/{id}/state — 실현손익 실체결 기준 재계산 (2026-07-01 dogfood).

`LiveSignalState.total_realized_pnl`/`equity_curve` 는 Pine 시뮬레이션 재생
결과라 실제 거래소 체결과 무관했다. 엔드포인트가 실제 filled 주문 기준으로
재계산해 반환하는지 검증.

Uses mock_clerk_auth fixture from conftest.py for auth bypass.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    LiveSignalState,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


async def _seed_session(db_session, user):
    strategy = Strategy(
        user_id=user.id,
        name="s",
        pine_source="//",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add(session)
    await db_session.flush()

    # 시뮬레이션 재생 결과(잘못된 값) — 실제로는 이 값이 그대로 노출되면 안 된다.
    state = LiveSignalState(
        session_id=session.id,
        last_strategy_state_report={"position_size": 0.0},
        last_open_trades_snapshot={},
        total_closed_trades=153,
        total_realized_pnl=Decimal("-1007.70"),
        equity_curve=[{"timestamp_ms": 1782894780000, "cumulative_pnl": "-1007.70"}],
    )
    db_session.add(state)
    await db_session.commit()
    return strategy, account, session


@pytest.mark.asyncio
async def test_state_uses_real_filled_pnl_not_simulation(client, mock_clerk_auth, db_session):
    """rejected 주문의 시뮬레이션 pnl은 무시하고, filled 주문의 실현손익만 반영."""
    user = mock_clerk_auth
    strategy, account, session = await _seed_session(db_session, user)

    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.rejected,
            realized_pnl=Decimal("-1007.70"),
            filled_at=datetime(2026, 7, 1, 8, 34, 27, tzinfo=UTC),
        )
    )
    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal("42.50"),
            filled_at=datetime(2026, 7, 1, 8, 40, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert Decimal(str(body["total_realized_pnl"])) == Decimal("42.50")
    assert body["total_closed_trades"] == 1
    assert len(body["equity_curve"]) == 1
    assert body["equity_curve"][0]["timestamp_ms"] == int(
        datetime(2026, 7, 1, 8, 40, 0, tzinfo=UTC).timestamp() * 1000
    )
    assert Decimal(str(body["equity_curve"][0]["cumulative_pnl"])) == Decimal("42.50")
    # Pine 엔진 내부 상태 표시는 그대로 유지 (변경 대상 아님)
    assert body["last_strategy_state_report"] == {"position_size": 0.0}


@pytest.mark.asyncio
async def test_state_returns_zero_when_no_filled_orders_yet(client, mock_clerk_auth, db_session):
    """체결된 실주문이 아직 없으면(예: 첫 신호가 리젝트) 0으로 보여야 한다."""
    user = mock_clerk_auth
    strategy, account, session = await _seed_session(db_session, user)

    db_session.add(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.rejected,
            realized_pnl=Decimal("-1007.70"),
            filled_at=datetime(2026, 7, 1, 8, 34, 27, tzinfo=UTC),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/live-sessions/{session.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert Decimal(str(body["total_realized_pnl"])) == Decimal("0")
    assert body["total_closed_trades"] == 0
    assert body["equity_curve"] == []
