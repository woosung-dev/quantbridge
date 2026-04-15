"""vectorbt import 및 Portfolio.from_signals 최소 호출 smoke test."""
from __future__ import annotations

import pandas as pd
import pytest


def test_vectorbt_importable():
    import vectorbt as vbt  # noqa: F401


def test_portfolio_from_signals_minimal():
    """가장 단순한 entries/exits로 Portfolio가 생성되고 total_return이 숫자로 나오는지."""
    import vectorbt as vbt

    close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0], name="close")
    entries = pd.Series([False, True, False, False, False])
    exits = pd.Series([False, False, False, True, False])

    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )
    tr = pf.total_return()
    # total_return은 float 또는 Series(단일 컬럼)
    value = float(tr) if not hasattr(tr, "iloc") else float(tr.iloc[0])
    # 11.0에 진입, 11.5에 청산 → 약 4.5% (수수료/슬리피지 반영 시 ~4.2%). 허용 ±10%
    assert value == pytest.approx((11.5 - 11.0) / 11.0, rel=0.10)
