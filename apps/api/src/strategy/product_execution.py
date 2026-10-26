"""제품 코드 전략의 두 단계 입력 준비와 격리 실행을 소유한다."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Self

import pandas as pd

from src.backtest.config_mapper import timeframe_to_freq
from src.strategy.code_contract import read_code_version
from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.exceptions import CodeStrategyPolicyError

if TYPE_CHECKING:
    from src.backtest.engine.types import BacktestConfig, BacktestResult
    from src.backtest.models import Backtest
    from src.market_data.providers import OHLCVProvider
    from src.strategy.models import StrategyVersion


class CodeBacktestExecution:
    """prepare 성공 후 사용한다. 상태 전이와 commit은 caller가 소유한다."""

    def __init__(
        self,
        backtest: Backtest,
        version: StrategyVersion,
        provider: OHLCVProvider,
        signal_ohlcv: pd.DataFrame,
    ) -> None:
        self._backtest = backtest
        self._version = version
        self._provider = provider
        self._signal_ohlcv = signal_ohlcv

    @classmethod
    async def prepare(
        cls,
        backtest: Backtest,
        version: StrategyVersion,
        *,
        provider: OHLCVProvider,
    ) -> Self:
        """QUEUED에서 부모 봉을 준비하고 조회 전·후의 버전 검증을 유지한다."""
        signal_ohlcv = await provider.get_ohlcv(
            backtest.symbol,
            backtest.timeframe,
            backtest.period_start
            - timedelta(
                seconds=(
                    read_code_version(version).warmup_bars
                    * pd.Timedelta(timeframe_to_freq(backtest.timeframe)).total_seconds()
                )
            ),
            backtest.period_end,
        )
        warmup = read_code_version(version).warmup_bars
        width = pd.Timedelta(timeframe_to_freq(backtest.timeframe))
        expected = pd.date_range(
            backtest.period_start - warmup * width,
            backtest.period_end,
            freq=width,
            inclusive="left",
        )
        if not signal_ohlcv.index.equals(expected):
            raise CodeStrategyPolicyError("워밍업과 평가 봉의 연속된 전체 범위가 필요합니다")
        return cls(backtest, version, provider, signal_ohlcv)

    @property
    def signal_ohlcv(self) -> pd.DataFrame:
        return self._signal_ohlcv

    async def run(
        self, config: BacktestConfig, *, funding_rates: pd.Series | None
    ) -> BacktestResult:
        """caller의 RUNNING 전환·취소 확인 뒤에 버전과 실행 입력을 다시 검증한다."""
        snapshot = read_code_version(self._version, strategy_id=self._backtest.strategy_id)
        if (self._backtest.config or {}).get("execution_hash") != snapshot.execution_hash:
            raise CodeStrategyPolicyError()
        execution_ohlcv = await self._provider.get_ohlcv(
            self._backtest.symbol,
            "1m",
            self._backtest.period_start,
            self._backtest.period_end,
        )
        return await asyncio.to_thread(
            run_code_backtest,
            snapshot.source_code,
            snapshot.language,
            self._signal_ohlcv,
            config,
            funding_rates=funding_rates,
            params=snapshot.params,
            warmup_bars=snapshot.warmup_bars,
            execution_ohlcv=execution_ohlcv,
            research_policy=snapshot.research_execution,
        )
