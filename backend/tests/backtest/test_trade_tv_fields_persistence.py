# TV Trades parity 신규 trade 필드 — 모델 매핑/직렬화/DB round-trip 검증
"""RawTrade 확장 필드(runup/drawdown/bars/fee split/exit_kind/comment/cumulative)가
BacktestTrade → TradeItem 까지 전달되고, 구 row(NULL) 는 graceful 한지 고정."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pandas as pd
import pytest

from src.backtest.engine.types import RawTrade
from src.backtest.models import Backtest, BacktestStatus, BacktestTrade
from src.backtest.schemas import TradeItem
from src.backtest.service import BacktestService
from src.strategy.pine_v2.exit_orders import ExitOrderKind


def _full_raw_trade() -> RawTrade:
    return RawTrade(
        trade_index=0,
        direction="long",
        status="closed",
        entry_bar_index=0,
        exit_bar_index=1,
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        size=Decimal("2"),
        pnl=Decimal("19.5"),
        return_pct=Decimal("0.0975"),
        fees=Decimal("0.5"),
        exit_kind=ExitOrderKind.TAKE_PROFIT,
        runup_abs=Decimal("24"),
        runup_pct=Decimal("0.12"),
        drawdown_abs=Decimal("4"),
        drawdown_pct=Decimal("0.02"),
        bars_in_trade=1,
        fee_paid=Decimal("0.3"),
        slippage_paid=Decimal("0.2"),
        comment="Long",
        cumulative_pnl=Decimal("19.5"),
    )


def _service() -> BacktestService:
    return BacktestService(
        repo=cast(Any, None),
        strategy_repo=cast(Any, None),
        ohlcv_provider=cast(Any, None),
        dispatcher=cast(Any, None),
    )


def test_raw_trade_maps_all_tv_fields_to_model() -> None:
    idx = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    [model] = _service()._raw_trades_to_models([_full_raw_trade()], uuid4(), idx)
    assert model.runup_abs == Decimal("24")
    assert model.runup_pct == Decimal("0.12")
    assert model.drawdown_abs == Decimal("4")
    assert model.drawdown_pct == Decimal("0.02")
    assert model.bars_in_trade == 1
    assert model.fee_paid == Decimal("0.3")
    assert model.slippage_paid == Decimal("0.2")
    assert model.exit_kind == "take_profit"  # wire 문자열 (PG enum 회피)
    assert model.comment == "Long"
    assert model.cumulative_pnl == Decimal("19.5")


def test_trade_item_serializes_tv_fields() -> None:
    idx = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    [model] = _service()._raw_trades_to_models([_full_raw_trade()], uuid4(), idx)
    item = TradeItem.model_validate(model)
    dumped = item.model_dump(mode="json")
    assert dumped["runup_abs"] == "24"
    assert dumped["drawdown_pct"] == "0.02"
    assert dumped["bars_in_trade"] == 1
    assert dumped["fee_paid"] == "0.3"
    assert dumped["slippage_paid"] == "0.2"
    assert dumped["exit_kind"] == "take_profit"
    assert dumped["comment"] == "Long"
    assert dumped["cumulative_pnl"] == "19.5"


def test_trade_item_graceful_on_legacy_row_without_tv_fields() -> None:
    """구 row (신규 컬럼 NULL) → TradeItem 파싱/직렬화 graceful."""
    legacy = BacktestTrade(
        backtest_id=uuid4(),
        trade_index=0,
        direction="long",
        status="closed",
        entry_time=datetime(2024, 1, 1, tzinfo=UTC),
        exit_time=datetime(2024, 1, 2, tzinfo=UTC),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        size=Decimal("1"),
        pnl=Decimal("10"),
        return_pct=Decimal("0.1"),
        fees=Decimal("0"),
    )
    item = TradeItem.model_validate(legacy)
    dumped = item.model_dump(mode="json")
    assert dumped["runup_abs"] is None
    assert dumped["exit_kind"] is None
    assert dumped["cumulative_pnl"] is None


@pytest.mark.asyncio
async def test_db_round_trip_tv_fields(db_session) -> None:  # type: ignore[no-untyped-def]
    """insert_trades_bulk → list_trades DB round-trip 에서 신규 컬럼 보존."""
    from src.backtest.repository import BacktestRepository
    from tests.backtest.test_service import _seed_user_and_strategy

    user, strat = await _seed_user_and_strategy(db_session)
    bt = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strat.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        created_at=datetime.now(UTC),
    )
    db_session.add(bt)
    await db_session.flush()

    repo = BacktestRepository(db_session)
    idx = pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC")
    models = _service()._raw_trades_to_models([_full_raw_trade()], bt.id, idx)
    await repo.insert_trades_bulk(models)
    await db_session.flush()

    rows, total = await repo.list_trades(bt.id, limit=10, offset=0)
    assert total == 1
    row = rows[0]
    assert row.runup_abs == Decimal("24")
    assert row.drawdown_abs == Decimal("4")
    assert row.fee_paid == Decimal("0.3")
    assert row.slippage_paid == Decimal("0.2")
    assert row.exit_kind == "take_profit"
    assert row.comment == "Long"
    assert row.cumulative_pnl == Decimal("19.5")
    assert row.bars_in_trade == 1
