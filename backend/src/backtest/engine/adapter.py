"""SignalResult → vectorbt Portfolio.from_signals() kwargs 변환."""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.strategy.pine.types import SignalResult


def to_portfolio_kwargs(
    signal: SignalResult,
    ohlcv: pd.DataFrame,
    config: BacktestConfig,
) -> dict[str, Any]:
    """SignalResult + OHLCV + config → Portfolio.from_signals kwargs.

    항상 포함: close, entries, exits, init_cash, fees, slippage, freq
    조건부 포함 (None이면 생략):
      - sl_stop  : signal.sl_stop 가격 → entry bar만 비율로 변환 ((close - sl_price) / close).
                   non-entry bar는 NaN 마스킹 (carry-forward 방지, Pine strategy.exit semantics).
      - tp_stop  : signal.tp_limit 가격 → entry bar만 비율로 변환 ((target - close) / close).
                   non-entry bar는 NaN 마스킹 (carry-forward TP target이 close를 넘어서 false-positive
                   TP 발동되는 것 방지).
      - size     : signal.position_size
    """
    _assert_aligned(signal, ohlcv)

    kwargs: dict[str, Any] = {
        "close": ohlcv["close"],
        "entries": signal.entries,
        "exits": signal.exits,
        "init_cash": float(config.init_cash),
        "fees": config.fees,
        "slippage": config.slippage,
        "freq": config.freq,
    }

    if signal.sl_stop is not None:
        # vectorbt 0.28.x sl_stop 시맨틱스 확인 (smoke check):
        # sl_stop은 비율(ratio)로 해석됨. 절대 가격 Series를 전달하면 SL이 작동하지 않음.
        # 따라서 가격 → 비율 변환 필수: ratio = (close - sl_price) / close
        # S3-04: entry bar에서만 stop price 적용 — carry-forward된 bars에서 sl_price > close가
        # 되면 음수 ratio가 생겨 silent mis-stop 발생. entry bar only 마스킹으로 방지.
        sl_entry_only = signal.sl_stop.where(signal.entries)
        kwargs["sl_stop"] = _price_to_sl_ratio(sl_entry_only, ohlcv["close"])

    if signal.tp_limit is not None:
        # carry-forward TP target 위를 close가 넘으면 비율이 0 또는 음수 → 거짓 TP 발동 가능.
        # entry bar에서만 TP 적용 — Pine strategy.exit(limit=...) semantics.
        tp_entry_only = signal.tp_limit.where(signal.entries)
        kwargs["tp_stop"] = _price_to_ratio(tp_entry_only, ohlcv["close"])

    if signal.position_size is not None:
        kwargs["size"] = signal.position_size

    return kwargs


def _assert_aligned(signal: SignalResult, ohlcv: pd.DataFrame) -> None:
    """entries/exits 인덱스가 OHLCV 인덱스와 일치하는지 검증."""
    if not signal.entries.index.equals(ohlcv.index):
        raise ValueError(
            "SignalResult.entries index must align with OHLCV index "
            f"(got {signal.entries.index!r} vs {ohlcv.index!r})"
        )
    if not signal.exits.index.equals(ohlcv.index):
        raise ValueError(
            "SignalResult.exits index must align with OHLCV index "
            f"(got {signal.exits.index!r} vs {ohlcv.index!r})"
        )


def _price_to_ratio(target_price: pd.Series, close: pd.Series) -> pd.Series:
    """tp_stop 비율 변환: (target_price - close) / close. NaN은 NaN 유지."""
    return (target_price - close) / close


def _price_to_sl_ratio(sl_price: pd.Series, close: pd.Series) -> pd.Series:
    """sl_stop 비율 변환: (close - sl_price) / close.

    smoke check 결과: vectorbt 0.28.x는 sl_stop을 비율로 해석함.
    절대 가격 Series를 직접 전달하면 SL이 작동하지 않음.
    NaN은 NaN 유지.
    음수 ratio (sl_price > close) 는 silent mis-stop 방지를 위해 ValueError.
    """
    ratio = (close - sl_price) / close
    # NaN < 0 은 False이므로 dropna 불필요. 음수만 감지.
    invalid_mask = ratio < 0
    if invalid_mask.any():
        bad_idx = ratio.index[invalid_mask]
        raise ValueError(
            f"Invalid SL price: sl_price exceeds close at index {list(bad_idx[:3])} "
            f"(would produce negative stop ratio, silent mis-stop). "
            f"stop price must be below close at entry bar — check strategy.exit(stop=...) value."
        )
    return ratio
