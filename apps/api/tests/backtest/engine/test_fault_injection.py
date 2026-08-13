"""pine_v2 adapter fault injection — error/parse_failed 분기 커버리지.

이전 구 엔진(vectorbt) 기반 테스트는 run_backtest_v2 마이그레이션과 함께
pine_v2 경로로 재작성됐다 (fault 지점이 변경됨).
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.backtest.engine import run_backtest

SIMPLE_PINE_V5 = """//@version=5
strategy("T", overlay=true)
ema_fast = ta.ema(close, 10)
ema_slow = ta.ema(close, 30)
if ta.crossover(ema_fast, ema_slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(ema_fast, ema_slow)
    strategy.close("L")
"""


@pytest.fixture
def valid_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=100, freq="1h")
    return pd.DataFrame(
        {
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [100.0] * 100,
        },
        index=idx,
    )


class TestRunBacktestFaultInjection:
    def test_parse_and_run_v2_raises_becomes_parse_failed(
        self, valid_ohlcv: pd.DataFrame
    ) -> None:
        """pine_v2 parse/classify 예외 → BacktestOutcome(status='parse_failed')."""
        with patch(
            "src.backtest.engine.v2_adapter.parse_and_run_v2",
            side_effect=RuntimeError("parse boom"),
        ):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "parse_failed"
        assert outcome.result is None
        assert "parse boom" in str(outcome.error)

    def test_build_raw_trades_exception_becomes_error(
        self, valid_ohlcv: pd.DataFrame
    ) -> None:
        """_build_raw_trades 예외 → BacktestOutcome(status='error')."""
        with patch(
            "src.backtest.engine.v2_adapter._build_raw_trades",
            side_effect=RuntimeError("trades boom"),
        ):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert outcome.result is None
        assert "trades boom" in str(outcome.error)

    def test_compute_metrics_exception_becomes_error(
        self, valid_ohlcv: pd.DataFrame
    ) -> None:
        """_compute_metrics 예외 → error status."""
        with patch(
            "src.backtest.engine.v2_adapter._compute_metrics",
            side_effect=ValueError("metrics fail"),
        ):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert "metrics fail" in str(outcome.error)

    def test_malformed_pine_source_becomes_parse_failed(
        self, valid_ohlcv: pd.DataFrame
    ) -> None:
        """pynescript 가 파싱 불가인 소스 → parse_failed (선언조차 없음)."""
        malformed = "this is not pine script at all @@@ $$$"
        outcome = run_backtest(malformed, valid_ohlcv)
        assert outcome.status == "parse_failed"
        assert outcome.result is None

    def test_empty_ohlcv_becomes_error_not_parse_failed(self) -> None:
        """Codex P2: empty OHLCV 는 data 오류 → status=error ('parse_failed' 오분류 방지)."""
        outcome = run_backtest(SIMPLE_PINE_V5, pd.DataFrame(columns=["open", "high", "low", "close", "volume"]))
        assert outcome.status == "error"
        assert outcome.result is None

    def test_failure_outcome_parse_stub_has_error_status(
        self, valid_ohlcv: pd.DataFrame
    ) -> None:
        """Codex P2: 실패 경로의 ParseOutcome stub 은 status='error' 를 반환해야 한다.

        소비자가 out.parse.status 를 읽어 파싱 성공으로 오해하지 않도록 한다.
        """
        malformed = "@@@ bad $$$"
        outcome = run_backtest(malformed, valid_ohlcv)
        assert outcome.status == "parse_failed"
        assert outcome.parse.status == "error"
