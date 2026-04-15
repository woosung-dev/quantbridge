"""SignalResult → vectorbt Portfolio.from_signals kwargs 변환기 검증."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest.engine.adapter import _price_to_sl_ratio, to_portfolio_kwargs
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

    S3-04: entry bar에서만 sl_stop 적용 — non-entry bar는 NaN 마스킹.
    carry-forward된 bars에서 sl_price > close → 음수 ratio → silent mis-stop 방지.
    """
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    # close = [10, 11, 12, 11.5, 13]; sl_stop at entry=11 → 10.0 (9.09% 하락)
    # idx=1이 entry bar (_minimal_signal: entries=[F, T, F, F, F])
    sl_price = pd.Series([float("nan"), 10.0, 10.0, float("nan"), float("nan")], index=ohlcv.index)
    signal.sl_stop = sl_price
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert "sl_stop" in kwargs
    sl = kwargs["sl_stop"]
    # entry bar(idx=1): close=11, sl_price=10 → ratio = (11 - 10) / 11 ≈ 0.0909
    assert sl.iloc[1] == pytest.approx((11.0 - 10.0) / 11.0, rel=1e-9)
    # non-entry bars → NaN (S3-04: entry bar only 마스킹)
    assert math.isnan(sl.iloc[0])
    assert math.isnan(sl.iloc[2])
    assert math.isnan(sl.iloc[3])


def test_adapter_converts_tp_limit_price_to_ratio():
    """tp_stop은 비율만 받으므로, 가격 Series를 (target/close - 1)로 변환.

    S3-04: entry bar에서만 tp_limit 적용 (sl_stop과 동일한 이유).
    """
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    # close = [10, 11, 12, 11.5, 13]; tp_limit at entry=11 → 13.2 (20% 위)
    # idx=1이 entry bar (_minimal_signal: entries=[F, T, F, F, F])
    signal.tp_limit = pd.Series(
        [float("nan"), 13.2, 13.2, float("nan"), float("nan")], index=ohlcv.index
    )
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    tp = kwargs["tp_stop"]
    # entry bar(idx=1): close=11, target=13.2 → ratio = (13.2 - 11) / 11 = 0.2
    assert tp.iloc[1] == pytest.approx(0.2, rel=1e-9)
    # non-entry bars → NaN (S3-04: entry bar only 마스킹)
    assert math.isnan(tp.iloc[0])
    assert math.isnan(tp.iloc[2])
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


def test_adapter_masks_carry_forward_sl_above_close() -> None:
    """carry-forward sl_price가 non-entry bar에서 close를 초과해도 ValueError 발생 안 함.

    masking이 없으면: 음수 ratio → ValueError 발생.
    masking이 있으면: non-entry bar NaN 처리 → 통과 (carry-forward 방지).

    regression test: masking 제거 시 이 test가 실패해 즉시 감지.
    """
    # OHLCV: close = [10, 11, 12, 11.5, 13]
    idx = pd.date_range("2024-01-01", periods=5, freq="1h")
    ohlcv = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0, 11.5, 13.0],
            "high": [10.5, 11.5, 12.5, 12.0, 13.5],
            "low": [9.5, 10.5, 11.5, 11.0, 12.5],
            "close": [10.0, 11.0, 12.0, 11.5, 13.0],
            "volume": [100.0] * 5,
        },
        index=idx,
    )

    entries = pd.Series([False, True, False, False, False], index=idx)
    exits = pd.Series([False, False, False, False, True], index=idx)

    # idx=2 (non-entry): sl_price=12.5 > close=12.0 → 음수 ratio without masking
    sl_price = pd.Series(
        [float("nan"), 10.0, 12.5, float("nan"), float("nan")], index=idx
    )

    signal = SignalResult(
        entries=entries,
        exits=exits,
        sl_stop=sl_price,
        tp_limit=None,
        position_size=None,
        warnings=[],
    )

    # should NOT raise — masking zeroes out non-entry sl_price before ratio calc
    kwargs = to_portfolio_kwargs(signal, ohlcv, BacktestConfig())

    # idx=2 sl_stop이 NaN인지 확인 (masked out)
    assert math.isnan(kwargs["sl_stop"].iloc[2])
    # idx=1 entry bar는 정상 ratio (10 → (11 - 10) / 11 ≈ 0.0909)
    assert kwargs["sl_stop"].iloc[1] == pytest.approx((11 - 10) / 11)


class TestPriceToSlRatio:
    """adapter._price_to_sl_ratio S3-04 회귀 방지 테스트."""

    def test_valid_positive_ratio(self) -> None:
        """sl_price < close → 양수 ratio."""
        close = pd.Series([100.0, 110.0, 120.0])
        sl = pd.Series([95.0, 104.5, 114.0])
        result = _price_to_sl_ratio(sl, close)
        assert result.tolist() == pytest.approx([0.05, 0.05, 0.05])

    def test_nan_preserved(self) -> None:
        """NaN (signal 없는 bar) 는 NaN 유지."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([95.0, float("nan")])
        result = _price_to_sl_ratio(sl, close)
        assert result.iloc[0] == pytest.approx(0.05)
        assert pd.isna(result.iloc[1])

    def test_negative_ratio_raises(self) -> None:
        """sl_price > close → ValueError (silent mis-stop 방지)."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([95.0, 115.0])  # 2번째 bar는 sl > close
        with pytest.raises(ValueError, match="Invalid SL price"):
            _price_to_sl_ratio(sl, close)

    def test_all_nan_no_error(self) -> None:
        """전체 NaN은 error 아님."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([float("nan"), float("nan")])
        result = _price_to_sl_ratio(sl, close)
        assert pd.isna(result).all()
