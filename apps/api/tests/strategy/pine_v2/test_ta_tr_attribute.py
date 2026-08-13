"""ta.tr (True Range built-in series) attribute access — Sprint X1+X3 follow-up.

Pine v5 의 `ta.tr` 은 함수가 아닌 series 변수: 매 bar 의 True Range.
- ta.tr = max(high - low, |high - close[1]|, |low - close[1]|)
- 첫 bar (close[1] = na) → high - low 만 사용
"""

from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical

PINE_TA_TR = """
//@version=5
strategy("ta.tr smoke", overlay=true)

tr_now = ta.tr
plot(tr_now, "TR")
"""


def _ohlcv() -> pd.DataFrame:
    # 5 bar — high-low + gap 으로 True Range 검증
    return pd.DataFrame(
        {
            "open": [100.0, 102.0, 110.0, 105.0, 95.0],
            "high": [105.0, 108.0, 115.0, 110.0, 100.0],
            "low": [99.0, 101.0, 109.0, 95.0, 90.0],  # bar 3 gap down (95 < prev_close 110)
            "close": [102.0, 107.0, 110.0, 96.0, 92.0],
            "volume": [1000.0] * 5,
        },
        index=pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC"),
    )


def test_ta_tr_attribute_access_runs_to_completion() -> None:
    """ta.tr 가 attribute access 로 호출돼도 'Attribute access not supported' 에러 없이 진행."""
    result = run_historical(PINE_TA_TR, _ohlcv())
    # ta.tr 관련 에러가 없어야 함 (다른 unsupported 함수는 별개)
    errors_text = " ".join(getattr(result, "errors", []) or [])
    assert "ta.tr" not in errors_text, (
        f"ta.tr should be supported as attribute access. Errors: {errors_text}"
    )
