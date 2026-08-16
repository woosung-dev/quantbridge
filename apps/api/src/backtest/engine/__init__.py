"""백테스트 엔진 공개 API.

pine_v2 엔진 기반으로 마이그레이션됨 — `run_backtest` 는 `v2_adapter.run_backtest_v2`
로 위임한다. 구 Pine 인터프리터 + vectorbt 경로는 제거(의존성도 2026-08-06 제거).
"""

from __future__ import annotations

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.backtest.engine.v2_adapter import run_backtest_v2

PINE_V2_ENGINE_VERSION = "pine_v2"

run_backtest = run_backtest_v2


__all__ = [
    "PINE_V2_ENGINE_VERSION",
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestResult",
    "RawTrade",
    "run_backtest",
]
