# 격리 강제청산 사실의 RawTrade·메트릭·JSONB 전파를 검증한다.
from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import _build_raw_trades, _compute_metrics
from src.backtest.serializers import metrics_from_jsonb, metrics_to_jsonb
from src.strategy.pine_v2.strategy_state import StrategyState, Trade


def _config(leverage: float) -> BacktestConfig:
    return BacktestConfig(
        init_cash=Decimal("1000"), fees=0.0, slippage=0.0, leverage=leverage
    )


def _closed_trade(*, liquidated: bool = False) -> RawTrade:
    return RawTrade(
        trade_index=0,
        direction="long",
        status="closed",
        entry_bar_index=0,
        exit_bar_index=1,
        entry_price=Decimal("100"),
        exit_price=Decimal("90"),
        size=Decimal("1"),
        pnl=Decimal("-10"),
        return_pct=Decimal("-0.1"),
        fees=Decimal("0"),
        liquidated=liquidated,
    )


def _metrics(*, leverage: float, liquidated: bool):
    return _compute_metrics(
        [_closed_trade(liquidated=liquidated)],
        pd.Series([Decimal("1000"), Decimal("990")]),
        _config(leverage),
    )


def test_1x_metrics_omit_liquidation_jsonb_keys() -> None:
    """1x는 마진 모델 미적용이므로 신규 JSONB 키가 없다."""
    jsonb = metrics_to_jsonb(_metrics(leverage=1.0, liquidated=True))

    assert "liquidation_occurred" not in jsonb
    assert "liquidation_count" not in jsonb


def test_nonfinite_leverage_omits_liquidation_metrics() -> None:
    """엔진과 동일하게 비유한 레버리지는 마진 모델을 활성화하지 않는다."""
    metrics = _metrics(leverage=float("inf"), liquidated=True)

    assert metrics.liquidation_occurred is None
    assert metrics.liquidation_count is None


def test_leveraged_liquidation_sets_metrics() -> None:
    """레버리지 청산 종료 거래는 메트릭에 집계된다."""
    metrics = _metrics(leverage=2.0, liquidated=True)

    assert metrics.liquidation_occurred is True
    assert metrics.liquidation_count == 1


def test_leveraged_without_liquidation_sets_zero_metrics() -> None:
    """레버리지 모델을 적용했지만 청산이 없으면 False와 0이다."""
    metrics = _metrics(leverage=2.0, liquidated=False)

    assert metrics.liquidation_occurred is False
    assert metrics.liquidation_count == 0


def test_build_raw_trades_propagates_liquidated() -> None:
    """StrategyState의 청산 표식이 RawTrade까지 유지된다."""
    state = StrategyState()
    state.closed_trades.append(
        Trade(
            id="liquidated-long",
            direction="long",
            qty=1.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=1,
            exit_price=90.0,
            pnl=-10.0,
            liquidated=True,
        )
    )

    raw_trade = _build_raw_trades(state, _config(2.0))[0]

    assert raw_trade.liquidated is True


def test_liquidation_metrics_jsonb_round_trip() -> None:
    """레버리지 청산 메트릭은 JSONB 왕복 후 동일하다."""
    metrics = _metrics(leverage=2.0, liquidated=True)

    assert metrics_from_jsonb(metrics_to_jsonb(metrics)) == metrics
