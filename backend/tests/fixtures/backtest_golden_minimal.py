# BL-180 골든 오라클 — 손 계산 검증용 최소 fixture (2 시나리오)
from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.strategy_state import StrategyState, Trade

# ── S1: 단일 롱 트레이드 (5 bars) ─────────────────────────────────────────
# entry_bar=0 @ 100, exit_bar=4 @ 120, qty=1, long, fees=0, slip=0
# net_pnl=20, return_pct=0.2
# equity[i] = [1000, 1010, 1005, 1015, 1020]
# BH[i]     = [1000, 1100, 1050, 1150, 1200]


def make_s1_ohlcv() -> pd.DataFrame:
    closes = [100.0, 110.0, 105.0, 115.0, 120.0]
    dates = pd.date_range("2024-01-01", periods=5, freq="1D")
    return pd.DataFrame(
        {
            "open": [c - 1.0 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [1000.0] * 5,
        },
        index=dates,
    )


def make_s1_state() -> StrategyState:
    state = StrategyState()
    state.closed_trades = [
        Trade(
            id="S1T1",
            direction="long",
            qty=1.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=4,
            exit_price=120.0,
            pnl=None,
        )
    ]
    return state


S1_EXPECTED_ENTRIES = [
    {"entry_bar_index": 0, "entry_price": "100", "size": "1", "direction": "long"}
]
S1_EXPECTED_EXITS = [
    {"exit_bar_index": 4, "exit_price": "120", "pnl": "20", "return_pct": "0.2"}
]
S1_EXPECTED_EQUITY_VALS = ["1000", "1010", "1005", "1015", "1020"]
S1_EXPECTED_BH_VALS = ["1000", "1100", "1050", "1150", "1200"]

# ── S2: 롱+숏 2 트레이드 (6 bars) ─────────────────────────────────────────
# T1: long  entry_bar=0 @ 100, exit_bar=1 @ 120 → net_pnl=20
# T2: short entry_bar=2 @  90, exit_bar=4 @  80 → net_pnl=(90-80)*1=10
#     (short gross = (exit-entry)*qty*direction_sign = (80-90)*1*(-1) = 10)
# equity[i] = [1000, 1020, 1020, 1000, 1030, 1030]
# BH[i]     = [1000, 1200,  900, 1100,  800, 1000]


def make_s2_ohlcv() -> pd.DataFrame:
    closes = [100.0, 120.0, 90.0, 110.0, 80.0, 100.0]
    dates = pd.date_range("2024-01-01", periods=6, freq="1D")
    return pd.DataFrame(
        {
            "open": [c - 1.0 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [1000.0] * 6,
        },
        index=dates,
    )


def make_s2_state() -> StrategyState:
    state = StrategyState()
    state.closed_trades = [
        Trade(
            id="S2T1",
            direction="long",
            qty=1.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=1,
            exit_price=120.0,
            pnl=None,
        ),
        Trade(
            id="S2T2",
            direction="short",
            qty=1.0,
            entry_bar=2,
            entry_price=90.0,
            exit_bar=4,
            exit_price=80.0,
            pnl=None,
        ),
    ]
    return state


S2_EXPECTED_ENTRIES = [
    {"entry_bar_index": 0, "entry_price": "100", "size": "1", "direction": "long"},
    {"entry_bar_index": 2, "entry_price": "90", "size": "1", "direction": "short"},
]
S2_EXPECTED_EXITS = [
    {"exit_bar_index": 1, "exit_price": "120", "pnl": "20"},
    {"exit_bar_index": 4, "exit_price": "80", "pnl": "10"},
]
S2_EXPECTED_EQUITY_VALS = ["1000", "1020", "1020", "1000", "1030", "1030"]
S2_EXPECTED_BH_VALS = ["1000", "1200", "900", "1100", "800", "1000"]
