from __future__ import annotations

import pandas as pd

from scripts.pine_validation.oracles_a import atr_bollinger, rsi_bollinger_long_short


def _bars(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value + 1 for value in closes],
            "low": [value - 1 for value in closes],
            "close": closes,
            "volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="h", tz="UTC"),
    )


def test_atr_bollinger_waits_for_band_break_then_emits_trend_reversals() -> None:
    frame = _bars([10, 10, 12, 12, 10, 8, 8, 12, 12])

    events = atr_bollinger(
        frame, {"BBperiod": 2, "BBdeviation": 0.5, "ATRperiod": 1, "UseATRfilter": False}
    )

    assert [(event.bar_time.hour, event.direction) for event in events] == [
        (5, "short"),
        (7, "long"),
    ]


def test_rsi_bollinger_suppresses_rebuy_without_required_price_drop() -> None:
    frame = _bars([10, 9, 8, 7, 8, 7, 8, 7, 8])
    params = {
        "bbLen": 3,
        "bbMult": 10,
        "rsiLen": 2,
        "rsiBuyLevel": 40,
        "rsiSellLevel": 90,
        "dropPct": 5,
    }

    filtered = rsi_bollinger_long_short(frame, params)
    unfiltered = rsi_bollinger_long_short(frame, {**params, "dropPct": 0})

    assert [(event.bar_time.hour, event.direction) for event in filtered] == [(4, "long")]
    assert [(event.bar_time.hour, event.direction) for event in unfiltered] == [
        (4, "long"),
        (6, "long"),
        (8, "long"),
    ]
