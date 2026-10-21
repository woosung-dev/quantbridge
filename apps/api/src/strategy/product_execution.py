"""제품 code_v1 실행 입구. 고정 버전을 검증하고 격리 공통 실행기에만 위임한다."""

from __future__ import annotations

import pandas as pd

from src.backtest.engine.types import BacktestConfig, BacktestResult
from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.backtest import run_code_backtest


def run_product_backtest(
    snapshot: CodeSnapshot,
    ohlcv: pd.DataFrame,
    config: BacktestConfig,
    *,
    funding_rates: pd.Series | None,
    execution_ohlcv: pd.DataFrame,
) -> BacktestResult:
    return run_code_backtest(
        snapshot.source_code,
        snapshot.language,
        ohlcv,
        config,
        funding_rates=funding_rates,
        params=snapshot.params,
        warmup_bars=snapshot.warmup_bars,
        execution_ohlcv=execution_ohlcv,
    )
