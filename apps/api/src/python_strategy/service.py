"""코드 저장·실행 원장과 격리 실행기를 연결한다. 사용자 Python은 여기서 실행하지 않는다."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

import httpx

from src.backtest.engine.types import BacktestConfig
from src.common.exceptions import NotFoundError
from src.market_data.providers import OHLCVProvider
from src.python_strategy.data_window import complete_funding, complete_window
from src.python_strategy.exceptions import (
    PythonRunConflict,
    PythonRunnerUnavailable,
    PythonVersionConflict,
)
from src.python_strategy.models import PythonBacktest, PythonStrategy, PythonStrategyVersion, now
from src.python_strategy.repository import PythonStrategyRepository
from src.python_strategy.schemas import (
    PythonBacktestRequest,
    PythonCapabilities,
    PythonRunDetail,
    PythonStrategyDetail,
    SavePythonStrategy,
)
from src.trading.repositories.funding_rate_repository import FundingRateRepository

logger = logging.getLogger(__name__)


class PythonStrategyService:
    def __init__(
        self,
        repo: PythonStrategyRepository,
        provider: OHLCVProvider,
        funding_repo: FundingRateRepository,
        *,
        runner_url: str,
        runner_token: str,
        dispatch: Callable[[str], None],
    ) -> None:
        self.repo = repo
        self.provider = provider
        self.funding_repo = funding_repo
        self.runner_url = runner_url.rstrip("/")
        self.runner_token = runner_token
        self.dispatch = dispatch

    async def capabilities(self) -> PythonCapabilities:
        if not self.runner_url or not self.runner_token:
            return PythonCapabilities(
                available=False, reason="격리 Python 실행기가 아직 연결되지 않았습니다."
            )
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                response = await client.get(
                    f"{self.runner_url}/healthz",
                    headers={"Authorization": f"Bearer {self.runner_token}"},
                )
                response.raise_for_status()
                data = response.json()
            if data.get("available") is True:
                return PythonCapabilities(available=True)
        except (httpx.HTTPError, ValueError, AttributeError):
            pass
        return PythonCapabilities(
            available=False, reason="격리 실행기의 상태를 확인할 수 없습니다."
        )

    @staticmethod
    def detail(strategy: PythonStrategy, version: PythonStrategyVersion) -> PythonStrategyDetail:
        return PythonStrategyDetail(
            id=strategy.id,
            name=strategy.name,
            source=version.source,
            params=version.params,
            warmup_bars=version.warmup_bars,
            version_id=version.id,
            source_hash=version.source_hash,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
        )

    async def list_strategies(self, user_id: UUID) -> list[PythonStrategyDetail]:
        return [
            self.detail(strategy, version)
            for strategy, version in await self.repo.strategies(user_id)
        ]

    async def get(self, strategy_id: UUID, user_id: UUID) -> PythonStrategyDetail:
        strategy = await self.repo.strategy(strategy_id, user_id)
        if strategy is None or strategy.version_id is None:
            raise NotFoundError()
        version = await self.repo.version(strategy.version_id)
        if version is None:
            raise NotFoundError()
        return self.detail(strategy, version)

    async def save(
        self, data: SavePythonStrategy, user_id: UUID, strategy_id: UUID | None = None
    ) -> PythonStrategyDetail:
        strategy = (
            await self.repo.strategy(strategy_id, user_id)
            if strategy_id is not None
            else PythonStrategy(user_id=user_id, name=data.name)
        )
        if strategy is None:
            raise NotFoundError()
        strategy.name = data.name
        strategy.updated_at = now()
        await self.repo.save(strategy)
        version = PythonStrategyVersion(
            strategy_id=strategy.id,
            source=data.source,
            source_hash=hashlib.sha256(data.source.encode()).hexdigest(),
            params=data.params,
            warmup_bars=data.warmup_bars,
        )
        await self.repo.save(version)
        strategy.version_id = version.id
        await self.repo.save(strategy)
        await self.repo.commit()
        return self.detail(strategy, version)

    async def submit(
        self, strategy_id: UUID, data: PythonBacktestRequest, user_id: UUID
    ) -> PythonRunDetail:
        strategy = await self.get(strategy_id, user_id)
        if data.expected_version_id is not None and data.expected_version_id != strategy.version_id:
            raise PythonVersionConflict()
        capabilities = await self.capabilities()
        if not capabilities.available:
            raise PythonRunnerUnavailable(capabilities.reason)
        await self.repo.lock_user(user_id)
        if await self.repo.active_count(user_id):
            raise PythonRunConflict()
        run = PythonBacktest(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=strategy.version_id,
            request=data.model_dump(mode="json"),
        )
        await self.repo.save(run)
        await self.repo.commit()
        try:
            self.dispatch(str(run.id))
        except Exception:
            await self.repo.transition(
                run.id, ["pending"], "failed", error="실행 대기열에 등록하지 못했습니다."
            )
            await self.repo.commit()
            raise PythonRunnerUnavailable("실행 대기열에 등록하지 못했습니다.") from None
        return PythonRunDetail.model_validate(run)

    async def get_run(self, run_id: UUID, user_id: UUID) -> PythonRunDetail:
        run = await self.repo.run(run_id, user_id)
        if run is None:
            raise NotFoundError()
        return PythonRunDetail.model_validate(run)

    async def runs(self, strategy_id: UUID, user_id: UUID) -> list[PythonRunDetail]:
        await self.get(strategy_id, user_id)
        return [
            PythonRunDetail.model_validate(run)
            for run in await self.repo.runs(strategy_id, user_id)
        ]

    async def cancel(self, run_id: UUID, user_id: UUID) -> PythonRunDetail:
        run = await self.get_run(run_id, user_id)
        if run.status not in {"pending", "running"}:
            return run
        if run.status == "pending":
            if await self.repo.transition(run_id, ["pending"], "cancelled"):
                await self.repo.commit()
                return await self.get_run(run_id, user_id)
            run = await self.get_run(run_id, user_id)
            if run.status != "running":
                return run
        if run.status == "running":
            try:
                async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                    response = await client.post(
                        f"{self.runner_url}/v1/backtests/{run_id}/cancel",
                        headers={"Authorization": f"Bearer {self.runner_token}"},
                    )
                    response.raise_for_status()
            except httpx.HTTPError:
                raise PythonRunnerUnavailable(
                    "취소를 실행기에 전달하지 못했습니다. 다시 시도하세요."
                ) from None
        await self.repo.transition(run_id, ["running"], "cancelled")
        await self.repo.commit()
        return await self.get_run(run_id, user_id)

    async def execute(self, run_id: UUID) -> None:
        run = await self.repo.run(run_id)
        if run is None or not await self.repo.transition(run_id, ["pending"], "running"):
            return
        await self.repo.commit()
        try:
            version = await self.repo.version(run.version_id)
            if version is None:
                raise ValueError("고정된 Python 전략 버전이 없습니다.")
            request = PythonBacktestRequest.model_validate(run.request)
            seconds = {"1h": 3600, "4h": 14400, "1d": 86400}[request.timeframe]
            start = request.period_start - timedelta(seconds=seconds * version.warmup_bars)
            frame = await self.provider.get_ohlcv(
                request.symbol, request.timeframe, start, request.period_end
            )
            frame = complete_window(frame, start, request.period_end, request.timeframe)
            rates = await self.funding_repo.get_funding_series(
                "bybit", f"{request.symbol}:USDT", request.period_start, request.period_end
            )
            rates = complete_funding(rates, request.period_start, request.period_end)
            await self.repo.commit()
            config = BacktestConfig(
                init_cash=request.initial_capital,
                freq=request.timeframe,
                fees=float(request.fees),
                slippage=float(request.slippage),
                include_funding=True,
                leverage=1.0,
                fill_timing="next_bar_open",
                default_qty_type="strategy.percent_of_equity",
                default_qty_value=100.0,
            )
            from src.strategy.python_runtime.client import run_remote_python_backtest_payload

            result: dict[str, Any] = await asyncio.to_thread(
                run_remote_python_backtest_payload,
                version.source,
                frame,
                config,
                rates,
                version.params,
                version.warmup_bars,
                base_url=self.runner_url,
                token=self.runner_token,
                job_id=str(run_id),
            )
            result["validation"] = {"status": "research_only", "holdout_passed": False}
            result["data_assumptions"] = {
                "funding_status": "observed_settlements_only",
                "historical_schedule_assumption": "BTC/ETH UTC 00/08/16 settlements",
                "requested_start": request.period_start.isoformat(),
                "requested_end_exclusive": request.period_end.isoformat(),
            }
            await self.repo.transition(run_id, ["running"], "completed", result=result)
        except Exception as exc:
            logger.warning(
                "python_backtest_failed run_id=%s error_type=%s", run_id, type(exc).__name__
            )
            await self.repo.transition(run_id, ["running"], "failed", error=str(exc)[:2000])
        await self.repo.commit()
