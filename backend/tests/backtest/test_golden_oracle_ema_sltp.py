# strategy.exit OCO TP/SL 손계산 오라클 — 엔진 출력을 독립 hand-calc 로 검증(anti-circular).
"""T0-pine-oco C7 — golden hand-oracle (BL-022, LESSON-039 anti-circular).

엔진으로 엔진을 검증하지 않는다. 통제된 소형 시나리오의 기대값을 **손으로** 계산해
하드코딩하고, 엔진 출력이 그 손계산과 일치하는지 확인한다. 이 오라클이 PASS 해야만
전체 golden expected.json 을 (신뢰된) 엔진으로 재생성할 자격이 생긴다.

시나리오 (default cfg: taker_fee=0.001, slippage=0.0005, maker_fee=0.0002, qty=1):
  bar0: flat. bar1: long entry @ close=100. bar2: TP limit 110 도달(high=111).
  → exit @ max(open=102, 110)=110, kind=TAKE_PROFIT(maker).

손계산:
  gross_pnl = (110 - 100) * 1 = 10
  entry leg (taker): fee = 100*0.001 = 0.1, slip = 100*0.0005 = 0.05
  exit leg (TP=maker): fee = 110*0.0002 = 0.022, slip = 0 (limit 면제)
  total_fees = 0.1 + 0.022 = 0.122
  total_slippage = 0.05
  net_pnl = 10 - (0.122 + 0.05) = 9.828
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine import run_backtest
from src.strategy.pine_v2.exit_orders import ExitOrderKind

_SOURCE = """//@version=5
strategy("oracle ema sltp")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", stop=95.0, limit=110.0)
"""

_ROWS = [
    (100.0, 101.0, 99.0, 100.0),
    (100.0, 101.0, 99.0, 100.0),  # bar1 entry @ 100
    (102.0, 111.0, 101.0, 109.0),  # bar2 → TP 110 fill
    (110.0, 111.0, 109.0, 110.0),
]


def _ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [r[0] for r in _ROWS],
            "high": [r[1] for r in _ROWS],
            "low": [r[2] for r in _ROWS],
            "close": [r[3] for r in _ROWS],
            "volume": [1000.0] * len(_ROWS),
        },
        index=pd.date_range("2026-01-01", periods=len(_ROWS), freq="1h", tz="UTC"),
    )


def test_engine_matches_hand_oracle_tp_exit() -> None:
    out = run_backtest(_SOURCE, _ohlcv())
    assert out.status == "ok", out.error
    assert out.result is not None
    trades = out.result.trades
    # 정확히 1 closed trade.
    assert len(trades) == 1
    t = trades[0]
    # 손계산 기대값 (엔진 무관).
    assert t.exit_price == Decimal("110")
    assert t.exit_kind == ExitOrderKind.TAKE_PROFIT
    assert t.pnl == Decimal("9.828")  # net
    m = out.result.metrics
    assert m.total_fees is not None and m.total_slippage is not None
    assert m.total_fees == Decimal("0.122")
    assert m.total_slippage == Decimal("0.050")
    # C14 불변식.
    assert m.total_fees + m.total_slippage == t.fees
