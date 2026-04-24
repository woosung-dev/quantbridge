"""Walk-Forward pre-flight coverage — 미지원 Pine built-in 포함 시 즉시 reject.

Sprint H2 Phase A iter-1 (FIX-1):
- run_walk_forward 은 `run_backtest` 을 직접 호출하므로 backtest.service 레이어의
  coverage preflight 가 bypass 된다. unsupported 1개라도 있으면 명시적으로 차단.
- backtest.service.BacktestService.submit 과 동일 정책 (Golden Rule: 부분 실행 금지).
"""

from __future__ import annotations

import pytest

from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import make_sine_ohlcv

# `request.security` 는 `coverage._KNOWN_UNSUPPORTED_FUNCTIONS` 에 포함됨.
UNSUPPORTED_PINE = """//@version=5
strategy("WF Unsupported", overlay=true)
daily_close = request.security(syminfo.tickerid, "D", close)
if close > daily_close
    strategy.entry("L", strategy.long)
"""


def test_walk_forward_rejects_unsupported_pine() -> None:
    """미지원 built-in 포함 시 fold 루프 진입 전에 ValueError."""
    ohlcv = make_sine_ohlcv(n_bars=500)
    with pytest.raises(ValueError, match="unsupported"):
        run_walk_forward(
            UNSUPPORTED_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
        )


def test_walk_forward_unsupported_message_includes_builtin_name() -> None:
    """에러 메시지는 실제 미지원 이름을 포함 — 사용자가 무엇을 고쳐야 할지 명시."""
    ohlcv = make_sine_ohlcv(n_bars=500)
    with pytest.raises(ValueError) as exc_info:
        run_walk_forward(
            UNSUPPORTED_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
        )
    assert "request.security" in str(exc_info.value)
