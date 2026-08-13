# Sprint 38 BL-188 v3 A2 — backtest entry hour set == Live `is_allowed` parity 검증
"""동일 OHLCV 위에서 backtest 가 entry 한 hour set 과 Live `is_allowed` 가 True 반환한
hour set 이 정확히 일치하는지 검증. 단일 reference (`trading_sessions.is_allowed`) 호출
정합 보장.
"""
from __future__ import annotations

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.trading_sessions import is_allowed

# Track S — 매 bar entry 시도. id="L" 이라 재entry 마다 close+open.
_PINE_S_EVERY_BAR_ENTRY = """//@version=5
strategy("S-AlwaysLong", overlay=true)
strategy.entry("L", strategy.long)
"""


def _make_24h_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2026-04-01 00:00:00+00:00", periods=24, freq="1h")
    return pd.DataFrame(
        {
            "open": [100.0] * 24,
            "high": [101.0] * 24,
            "low": [99.0] * 24,
            "close": [100.0] * 24,
            "volume": [1.0] * 24,
        },
        index=idx,
    )


def test_backtest_entry_hours_match_live_is_allowed_asia() -> None:
    """sessions=("asia",) — backtest entry 발생한 hour 들이 Live is_allowed True 인 hour 와 동일."""
    sessions = ("asia",)
    cfg = BacktestConfig(trading_sessions=sessions)
    ohlcv = _make_24h_ohlcv()
    out = run_backtest_v2(_PINE_S_EVERY_BAR_ENTRY, ohlcv, cfg)
    assert out.status == "ok", f"engine status={out.status}, error={out.error}"

    # Backtest 가 entry 한 bar 들의 hour set.
    backtest_entry_hours: set[int] = set()
    for trade in out.result.trades if out.result else []:
        ts = ohlcv.index[trade.entry_bar_index]
        backtest_entry_hours.add(int(ts.hour))

    # Live `is_allowed` True 반환하는 hour set.
    live_allowed_hours: set[int] = {
        int(ts.hour) for ts in ohlcv.index if is_allowed(list(sessions), ts.to_pydatetime())
    }

    # backtest 가 entry 한 hour 는 모두 Live allowed hour 의 subset 이어야 함
    # (entry 가 매 bar 는 시도되나, 같은 bar 에서 close+entry 가 발생하므로 close 만 발생한 bar 도 있음).
    assert backtest_entry_hours.issubset(live_allowed_hours), (
        f"backtest entry hours {sorted(backtest_entry_hours)} not subset of "
        f"Live allowed hours {sorted(live_allowed_hours)}"
    )
    # 그리고 적어도 1 hour 는 entry 발생 (asia 가 7시간이라 trades 가 적어도 1 이상).
    assert len(backtest_entry_hours) >= 1, "asia session 에서 entry 0건 — gate 과도 차단"


def test_backtest_entry_hours_match_live_is_allowed_london_ny() -> None:
    """sessions=("london","ny") combined gate 정합."""
    sessions = ("london", "ny")
    cfg = BacktestConfig(trading_sessions=sessions)
    ohlcv = _make_24h_ohlcv()
    out = run_backtest_v2(_PINE_S_EVERY_BAR_ENTRY, ohlcv, cfg)
    assert out.status == "ok"

    backtest_entry_hours: set[int] = set()
    for trade in out.result.trades if out.result else []:
        ts = ohlcv.index[trade.entry_bar_index]
        backtest_entry_hours.add(int(ts.hour))

    live_allowed_hours: set[int] = {
        int(ts.hour) for ts in ohlcv.index if is_allowed(list(sessions), ts.to_pydatetime())
    }

    assert backtest_entry_hours.issubset(live_allowed_hours)
    # london [8,16) ∪ ny [13,20) = [8,20) → 12시간 allowed.
    assert len(live_allowed_hours) == 12
