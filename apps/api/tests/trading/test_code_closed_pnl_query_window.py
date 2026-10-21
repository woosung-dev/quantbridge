"""거래소 시각 의미를 단정하지 않고 오래 대기한 코드 청산의 조회 범위를 검증한다."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.tasks import trading
from src.trading.models import OrderSide, OrderState
from src.trading.providers import BybitFuturesProvider, ClosedPnlSnapshot, Credentials
from tests.tasks.test_exchange_order_response_metric import _Crypto
from tests.trading import test_code_closed_pnl_evidence as evidence_tests

prepared = evidence_tests.prepared
exit_order = evidence_tests.exit_order
exchange = evidence_tests.exchange


@pytest.mark.parametrize("path", ["refresh", "sweep"])
@pytest.mark.parametrize("row_time", ["order_created", "exit_record_created"])
@pytest.mark.parametrize("terminal", [OrderState.filled, OrderState.cancelled])
async def test_resting_exit_and_late_partial_cancel_use_early_order_window(
    exit_order, db_session, exchange, monkeypatch, path, row_time, terminal
):
    _repo, _live, order, evidence = exit_order
    now = datetime.now(UTC)
    order.created_at = now - timedelta(hours=6)
    order.submitted_at = (
        order.created_at + timedelta(minutes=1) if terminal == OrderState.filled else None
    )
    order.filled_at = now - timedelta(minutes=1)
    order.state = terminal
    await db_session.commit()
    observed_time = order.created_at if row_time == "order_created" else order.filled_at
    observed_ms = int(observed_time.timestamp() * 1000)
    observed_raw = evidence_tests.raw(createdTime=str(observed_ms))

    async def time_filtered_page(request):
        rows = [observed_raw] if request["startTime"] <= observed_ms <= request["endTime"] else []
        return evidence_tests.page(rows)

    exchange.privateGetV5PositionClosedPnl.side_effect = time_filtered_page
    provider = BybitFuturesProvider()
    provider.fetch_closed_pnl_window = AsyncMock(
        return_value=[
            ClosedPnlSnapshot(
                "exit",
                evidence.pnl,
                evidence.quantity,
                None,
                observed_ms,
                symbol="BTCUSDT",
                side="Sell",
                created_at_ms=observed_ms,
                raw=observed_raw,
            )
        ]
    )
    monkeypatch.setattr(trading, "EncryptionService", _Crypto)
    monkeypatch.setattr(trading, "_alert_new_exchange_exits", AsyncMock(return_value=False))

    @asynccontextmanager
    async def sm():
        yield db_session

    if path == "refresh":
        result = await trading._refresh_closed_pnl_with_session(order.id, sm, provider=provider)
        assert result["applied"] == 1
    else:
        result = await trading._sweep_closed_pnl_with_session(sm, provider=provider)
        assert result["backfilled"] == 1
    request = exchange.privateGetV5PositionClosedPnl.await_args.args[0]
    assert request["startTime"] == int(order.created_at.timestamp() * 1000) - 3_600_000
    assert request["endTime"] - request["startTime"] <= 7 * 24 * 60 * 60 * 1000
    assert request["limit"] == 100
    await db_session.refresh(order)
    assert order.realized_pnl == evidence.pnl
    if row_time == "order_created":
        # 종전 filled_at - 1h 하한에서는 이 가상 필터의 주문 생성 시각이 빠진다.
        assert observed_ms < int(order.filled_at.timestamp() * 1000) - 3_600_000


async def test_early_order_start_still_uses_existing_seven_day_cap(exchange):
    exchange.privateGetV5PositionClosedPnl.return_value = evidence_tests.page([])
    result = await BybitFuturesProvider().fetch_code_closed_pnl(
        Credentials("fake", "fake"),
        account_id=uuid4(),
        order_id="exit",
        symbol="BTCUSDT",
        side=OrderSide.sell,
        since=datetime.now(UTC) - timedelta(days=20),
    )
    request = exchange.privateGetV5PositionClosedPnl.await_args.args[0]
    assert request["endTime"] - request["startTime"] == 7 * 24 * 60 * 60 * 1000
    assert result.evidence is None and not result.conflict
