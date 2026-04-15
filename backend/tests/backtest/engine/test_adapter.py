"""SignalResult → vectorbt Portfolio.from_signals kwargs 변환기 검증."""
from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.types import BacktestConfig
from src.strategy.pine.types import SignalResult


def _ohlcv(n: int = 5) -> pd.DataFrame:
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0][:n])
    return pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5, "close": close, "volume": 100.0}
    )


def _minimal_signal(idx: pd.Index) -> SignalResult:
    return SignalResult(
        entries=pd.Series([False, True, False, False, False], index=idx),
        exits=pd.Series([False, False, False, True, False], index=idx),
    )


def test_adapter_passes_required_kwargs():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert kwargs["close"] is ohlcv["close"]
    pd.testing.assert_series_equal(kwargs["entries"], signal.entries)
    pd.testing.assert_series_equal(kwargs["exits"], signal.exits)
    assert kwargs["init_cash"] == 10000.0
    assert kwargs["fees"] == 0.001
    assert kwargs["slippage"] == 0.0005
    assert kwargs["freq"] == "1D"


def test_adapter_omits_optional_fields_when_none():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    for k in ("sl_stop", "tp_stop", "size"):
        assert k not in kwargs, f"{k} should be omitted when SignalResult field is None"


def test_adapter_converts_sl_stop_price_to_ratio():
    """sl_stop은 vectorbt 0.28.x에서 비율로 해석되므로, 가격 Series를 (close - sl_price) / close로 변환.

    smoke check 확인:
    - sl_stop=10.5 (절대 가격)로 전달 시 SL 미작동 (Exit Status=Open)
    - sl_stop=0.05 (5% 비율)로 전달 시 SL 정상 작동 (bar3 exit, Return≈-0.14)
    """
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    # close = [10, 11, 12, 11.5, 13]; sl_stop at entry=11 → 10.0 (9.09% 하락)
    sl_price = pd.Series([float("nan"), 10.0, 10.0, float("nan"), float("nan")], index=ohlcv.index)
    signal.sl_stop = sl_price
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert "sl_stop" in kwargs
    sl = kwargs["sl_stop"]
    # close=11, sl_price=10 → ratio = (11 - 10) / 11 ≈ 0.0909
    assert sl.iloc[1] == pytest.approx((11.0 - 10.0) / 11.0, rel=1e-9)
    assert sl.iloc[2] == pytest.approx((12.0 - 10.0) / 12.0, rel=1e-9)
    assert math.isnan(sl.iloc[0])
    assert math.isnan(sl.iloc[3])


def test_adapter_converts_tp_limit_price_to_ratio():
    """tp_stop은 비율만 받으므로, 가격 Series를 (target/close - 1)로 변환."""
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    # close = [10, 11, 12, 11.5, 13]; tp_limit at entry=11 → 13.2 (20% 위)
    signal.tp_limit = pd.Series(
        [float("nan"), 13.2, 13.2, float("nan"), float("nan")], index=ohlcv.index
    )
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    tp = kwargs["tp_stop"]
    # close=11, target=13.2 → ratio = (13.2 - 11) / 11 = 0.2
    assert tp.iloc[1] == pytest.approx(0.2, rel=1e-9)
    assert tp.iloc[2] == pytest.approx((13.2 - 12.0) / 12.0, rel=1e-9)
    assert math.isnan(tp.iloc[0])
    assert math.isnan(tp.iloc[3])


def test_adapter_passes_position_size_as_size():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    signal.position_size = pd.Series([2.0] * 5, index=ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert "size" in kwargs
    pd.testing.assert_series_equal(kwargs["size"], signal.position_size)


def test_adapter_raises_on_index_misalignment():
    ohlcv = _ohlcv()
    signal = SignalResult(
        entries=pd.Series([False, True], index=[99, 100]),
        exits=pd.Series([False, True], index=[99, 100]),
    )
    cfg = BacktestConfig()

    with pytest.raises(ValueError, match="index"):
        to_portfolio_kwargs(signal, ohlcv, cfg)
