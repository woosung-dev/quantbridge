"""StressTestService — HTTP submit 경로 + Worker run 경로.

Router → Service → Repository 3-Layer. AsyncSession 직접 import 금지.

- submit_monte_carlo / submit_walk_forward: Backtest ownership + COMPLETED 검증,
  StressTest 레코드 생성, Celery task dispatch.
- run(stress_test_id): Worker 엔트리. backtest equity_curve / ohlcv 를 읽어
  순수 엔진 호출 → result JSONB 저장.
- get / list: ownership 격리된 조회.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from src.backtest.config_mapper import build_engine_config_from_db
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.common.pagination import Page
from src.market_data.providers import OHLCVProvider
from src.optimizer.models import OptimizationKind
from src.optimizer.schemas import ParamSpace
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import StressTaskDispatcher
from src.stress_test.engine import (
    run_cost_assumption_sensitivity,
    run_monte_carlo,
    run_param_stability,
    run_walk_forward,
    run_walk_forward_optimization,
)
from src.stress_test.exceptions import (
    BacktestNotCompletedForStressTest,
    StressTestNotFound,
    StressTestTaskDispatchError,
)
from src.stress_test.models import (
    StressTest,
    StressTestKind,
    StressTestStatus,
)
from src.stress_test.repository import StressTestRepository
from src.stress_test.schemas import (
    CostAssumptionSubmitRequest,
    GridSweepMetricsResultOut,
    MonteCarloResultOut,
    MonteCarloSubmitRequest,
    ParamStabilitySubmitRequest,
    StressTestCreatedResponse,
    StressTestDetail,
    StressTestSummary,
    WalkForwardResultOut,
    WalkForwardSubmitRequest,
)
from src.stress_test.serializers import (
    equity_curve_values,
    grid_metrics_result_from_jsonb,
    grid_metrics_result_to_jsonb,
    mc_result_from_jsonb,
    mc_result_to_jsonb,
    wf_result_from_jsonb,
    wf_result_to_jsonb,
)

if TYPE_CHECKING:
    import pandas as pd

    from src.backtest.engine.types import BacktestConfig
    from src.strategy.models import Strategy
    from src.stress_test.engine import GridSweepMetricsResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _RunContext:
    """WF/CA/PS 공통 실행 컨텍스트 — strategy + ohlcv + parent backtest_config.

    BL-363 — 이전엔 3 execute 메서드가 strategy 로드 / ohlcv fetch /
    `build_engine_config_from_db(bt)` prefix 를 복붙했고, BL-222 가 CA/PS 에만
    config 를 추가하고 WF 를 누락 → silent money-path corruption. 단일 helper 로
    config 전달을 single-site 화해 drift class 를 구조적으로 제거한다.
    """

    strategy: Strategy
    ohlcv: pd.DataFrame
    backtest_config: BacktestConfig


class StressTestService:
    def __init__(
        self,
        *,
        repo: StressTestRepository,
        backtest_repo: BacktestRepository,
        strategy_repo: StrategyRepository,
        ohlcv_provider: OHLCVProvider,
        dispatcher: StressTaskDispatcher,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo
        self.strategy_repo = strategy_repo
        self.provider = ohlcv_provider
        self.dispatcher = dispatcher

    # ---------- HTTP submit ----------

    async def submit_monte_carlo(
        self,
        data: MonteCarloSubmitRequest,
        *,
        user_id: UUID,
    ) -> StressTestCreatedResponse:
        bt = await self._load_owned_backtest(data.backtest_id, user_id)
        self._ensure_completed(bt)
        return await self._submit(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.MONTE_CARLO,
            params={
                "n_samples": data.params.n_samples,
                "seed": data.params.seed,
            },
        )

    async def submit_walk_forward(
        self,
        data: WalkForwardSubmitRequest,
        *,
        user_id: UUID,
    ) -> StressTestCreatedResponse:
        bt = await self._load_owned_backtest(data.backtest_id, user_id)
        self._ensure_completed(bt)
        return await self._submit(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.WALK_FORWARD,
            params={
                "train_bars": data.params.train_bars,
                "test_bars": data.params.test_bars,
                "step_bars": data.params.step_bars,
                "max_folds": data.params.max_folds,
                # C13 fixed-param fallback — best_params 를 JSONB 저장 (Decimal → str). 없으면 None.
                "best_params": (
                    {k: str(v) for k, v in data.params.best_params.items()}
                    if data.params.best_params
                    else None
                ),
                # C13 진짜 OOS — fold별 재최적화 spec (param_space JSONB + kind str). 없으면 None.
                "optimizer_param_space": (
                    data.params.optimizer_param_space.model_dump(mode="json")
                    if data.params.optimizer_param_space
                    else None
                ),
                "optimizer_kind": (
                    data.params.optimizer_kind.value if data.params.optimizer_kind else None
                ),
            },
        )

    async def submit_cost_assumption_sensitivity(
        self,
        data: CostAssumptionSubmitRequest,
        *,
        user_id: UUID,
    ) -> StressTestCreatedResponse:
        """Sprint 50 — fees x slippage 9-cell grid sweep submit."""
        bt = await self._load_owned_backtest(data.backtest_id, user_id)
        self._ensure_completed(bt)
        return await self._submit(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.COST_ASSUMPTION_SENSITIVITY,
            params={
                # JSONB 직렬화 — Decimal → str.
                "param_grid": {k: [str(v) for v in vs] for k, vs in data.params.param_grid.items()},
            },
        )

    async def submit_param_stability(
        self,
        data: ParamStabilitySubmitRequest,
        *,
        user_id: UUID,
    ) -> StressTestCreatedResponse:
        """Sprint 51 BL-220 — pine_v2 input override 9-cell grid sweep submit."""
        bt = await self._load_owned_backtest(data.backtest_id, user_id)
        self._ensure_completed(bt)
        return await self._submit(
            user_id=user_id,
            backtest_id=bt.id,
            kind=StressTestKind.PARAM_STABILITY,
            params={
                # JSONB 직렬화 — Decimal → str.
                "param_grid": {k: [str(v) for v in vs] for k, vs in data.params.param_grid.items()},
            },
        )

    async def _submit(
        self,
        *,
        user_id: UUID,
        backtest_id: UUID,
        kind: StressTestKind,
        params: dict[str, object],
    ) -> StressTestCreatedResponse:
        st = StressTest(
            user_id=user_id,
            backtest_id=backtest_id,
            kind=kind,
            status=StressTestStatus.QUEUED,
            params=params,
        )
        await self.repo.create(st)

        try:
            task_id = self.dispatcher.dispatch_stress_test(st.id)
        except Exception as exc:
            await self.repo.rollback()
            logger.exception("stress_task_dispatch_failed")
            raise StressTestTaskDispatchError() from exc

        st.celery_task_id = task_id
        await self.repo.commit()
        return StressTestCreatedResponse(
            stress_test_id=st.id,
            kind=st.kind,
            status=st.status,
            created_at=st.created_at,
        )

    # ---------- Worker run ----------

    async def run(self, stress_test_id: UUID) -> None:
        """Worker entrypoint — params JSONB 기반으로 엔진 호출."""
        st = await self.repo.get_by_id(stress_test_id)
        if st is None:
            logger.warning(
                "stress_test_not_found_in_worker",
                extra={"stress_test_id": str(stress_test_id)},
            )
            return
        if st.status != StressTestStatus.QUEUED:
            logger.info(
                "worker_skip_non_queued_stress",
                extra={"stress_test_id": str(st.id), "status": st.status.value},
            )
            return

        # 원본 backtest 로드 + 가드
        bt = await self.backtest_repo.get_by_id(st.backtest_id)
        if bt is None or bt.status != BacktestStatus.COMPLETED:
            await self.repo.fail(
                stress_test_id,
                error=("Referenced backtest unavailable or not COMPLETED at execute time"),
            )
            await self.repo.commit()
            return

        # QUEUED → RUNNING
        rows = await self.repo.transition_to_running(stress_test_id, started_at=datetime.now(UTC))
        if rows == 0:
            logger.info(
                "stress_test_state_changed_before_run",
                extra={"stress_test_id": str(stress_test_id)},
            )
            return
        await self.repo.commit()

        # Kind 별 분기
        try:
            if st.kind == StressTestKind.MONTE_CARLO:
                result_jsonb = await self._execute_monte_carlo(st, bt)
            elif st.kind == StressTestKind.WALK_FORWARD:
                result_jsonb = await self._execute_walk_forward(st, bt)
            elif st.kind == StressTestKind.COST_ASSUMPTION_SENSITIVITY:
                result_jsonb = await self._execute_cost_assumption_sensitivity(st, bt)
            elif st.kind == StressTestKind.PARAM_STABILITY:
                result_jsonb = await self._execute_param_stability(st, bt)
            else:  # pragma: no cover — exhaustiveness guard
                raise ValueError(f"unknown stress_test kind: {st.kind}")
        except Exception as exc:
            logger.exception("stress_test_execution_failed")
            await self.repo.fail(
                stress_test_id,
                error=str(exc),
                where_status=StressTestStatus.RUNNING,
            )
            await self.repo.commit()
            return

        completed_rows = await self.repo.complete(stress_test_id, result=result_jsonb)
        if completed_rows == 0:
            logger.warning(
                "stress_test_complete_no_rows",
                extra={"stress_test_id": str(stress_test_id)},
            )
        await self.repo.commit()

    async def _execute_monte_carlo(self, st: StressTest, bt: Backtest) -> dict[str, object]:
        curve = equity_curve_values(bt.equity_curve)
        if len(curve) < 2:
            raise ValueError("Backtest equity_curve is empty or too short for Monte Carlo")
        n_samples_raw = st.params.get("n_samples", 1000)
        seed_raw = st.params.get("seed", 42)
        n_samples = int(n_samples_raw) if n_samples_raw is not None else 1000
        seed = int(seed_raw) if seed_raw is not None else 42

        mc = run_monte_carlo(curve, n_samples=n_samples, seed=seed)
        return mc_result_to_jsonb(mc)

    async def _load_run_context(self, bt: Backtest, *, kind_label: str) -> _RunContext:
        """WF/CA/PS 공통 prefix — strategy + ohlcv + parent backtest_config 로드 (BL-363).

        `build_engine_config_from_db(bt)` single-site 화 → BL-222 config-drift class
        구조적 제거 (이전엔 3 execute 메서드가 복붙 → CA/PS 에만 추가하고 WF 누락하던
        silent money-path corruption 전적). MC 는 equity_curve 기반이라 비대상.
        `kind_label` 은 strategy-missing 에러 메시지의 kind-specific 표면 보존용.
        """
        strategy = await self.strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
        if strategy is None:
            raise ValueError(f"Strategy no longer available for {kind_label}")
        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        return _RunContext(
            strategy=strategy,
            ohlcv=ohlcv,
            backtest_config=build_engine_config_from_db(bt),
        )

    async def _execute_walk_forward(self, st: StressTest, bt: Backtest) -> dict[str, object]:
        """Sprint 49 — Walk-Forward worker entry.

        전체 정검 S3 (BL-222 follow-up): parent backtest_config 를 IS/OOS 백테스트에
        전달 (`_load_run_context` 가 strategy/ohlcv/config prefix 를 single-site 로 제공).
        """
        ctx = await self._load_run_context(bt, kind_label="walk-forward")
        train_bars = int(st.params["train_bars"])
        test_bars = int(st.params["test_bars"])
        step_raw = st.params.get("step_bars")
        step_bars = int(step_raw) if step_raw is not None else None
        max_folds_raw = st.params.get("max_folds", 20)
        max_folds = int(max_folds_raw) if max_folds_raw is not None else 20

        backtest_config = ctx.backtest_config

        # C13 진짜 OOS — optimizer spec 동봉 시 fold별 train 재최적화(true WFO).
        # param_space/kind 는 스키마 validator 로 항상 함께 저장 (한쪽만 = reject).
        opt_param_space_raw = st.params.get("optimizer_param_space")
        opt_kind_raw = st.params.get("optimizer_kind")
        if opt_param_space_raw and opt_kind_raw:
            wf = run_walk_forward_optimization(
                ctx.strategy.pine_source,
                ctx.ohlcv,
                train_bars=train_bars,
                test_bars=test_bars,
                step_bars=step_bars,
                max_folds=max_folds,
                param_space=ParamSpace.model_validate(opt_param_space_raw),
                kind=OptimizationKind(opt_kind_raw),
                backtest_config=backtest_config,
            )
            return wf_result_to_jsonb(wf)

        # C13 fixed-param fallback — best_params (있으면) 를 전 fold 고정 적용.
        # JSONB 저장값(str) → Decimal 복원. build_engine_config_from_db 는
        # input_overrides=None 이므로 단순 replace.
        best_params_raw = st.params.get("best_params")
        if best_params_raw:
            overrides = {k: Decimal(str(v)) for k, v in best_params_raw.items()}
            backtest_config = replace(backtest_config, input_overrides=overrides)
        wf = run_walk_forward(
            ctx.strategy.pine_source,
            ctx.ohlcv,
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
            max_folds=max_folds,
            backtest_config=backtest_config,
        )
        return wf_result_to_jsonb(wf)

    async def _execute_cost_assumption_sensitivity(
        self, st: StressTest, bt: Backtest
    ) -> dict[str, object]:
        """Sprint 50 — Cost Assumption Sensitivity worker entry (thin delegator → _execute_grid_sweep)."""
        return await self._execute_grid_sweep(
            st,
            bt,
            engine_fn=run_cost_assumption_sensitivity,
            kind_label="cost assumption sensitivity",
        )

    async def _execute_param_stability(self, st: StressTest, bt: Backtest) -> dict[str, object]:
        """Sprint 51 BL-220 — Param Stability worker entry (thin delegator → _execute_grid_sweep)."""
        return await self._execute_grid_sweep(
            st, bt, engine_fn=run_param_stability, kind_label="param stability"
        )

    async def _execute_grid_sweep(
        self,
        st: StressTest,
        bt: Backtest,
        *,
        engine_fn: Callable[..., GridSweepMetricsResult],
        kind_label: str,
    ) -> dict[str, object]:
        """CA/PS 공통 2D grid sweep worker (BL-363/BL-392).

        parent backtest_config 전달 + param_grid 파싱 + 통합 serializer 를 single-site 화.
        `engine_fn` 만 주입 — 엔진 _의미_(CA=fees x slippage cost / PS=pine input override)는
        엔진 함수 내부에 분리 유지 (over-abstraction 가드).
        """
        ctx = await self._load_run_context(bt, kind_label=kind_label)
        raw_grid = st.params["param_grid"]
        param_grid: dict[str, list[Decimal]] = {
            k: [Decimal(v) for v in vs] for k, vs in raw_grid.items()
        }
        result = engine_fn(
            ctx.strategy.pine_source,
            ctx.ohlcv,
            param_grid=param_grid,
            backtest_config=ctx.backtest_config,
        )
        return grid_metrics_result_to_jsonb(result)

    # ---------- HTTP read ----------

    async def get(self, stress_test_id: UUID, *, user_id: UUID) -> StressTestDetail:
        st = await self._load_owned(stress_test_id, user_id)
        return self._to_detail(st)

    async def list(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
        backtest_id: UUID | None = None,
    ) -> Page[StressTestSummary]:
        items, total = await self.repo.list_by_user(
            user_id, limit=limit, offset=offset, backtest_id=backtest_id
        )
        return Page[StressTestSummary](
            items=[StressTestSummary.model_validate(s) for s in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ---------- helpers ----------

    async def _load_owned(self, stress_test_id: UUID, user_id: UUID) -> StressTest:
        st = await self.repo.get_by_id(stress_test_id, user_id=user_id)
        if st is None:
            raise StressTestNotFound()
        return st

    async def _load_owned_backtest(self, backtest_id: UUID, user_id: UUID) -> Backtest:
        bt = await self.backtest_repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            # 소유자 격리 — 없거나 타 사용자 모두 404 (StressTestNotFound 남용 대신
            # 명확한 "참조 backtest 미발견" 은 BacktestNotFound 를 재사용).
            from src.backtest.exceptions import BacktestNotFound

            raise BacktestNotFound()
        return bt

    @staticmethod
    def _ensure_completed(bt: Backtest) -> None:
        if bt.status != BacktestStatus.COMPLETED:
            raise BacktestNotCompletedForStressTest(
                detail=(
                    f"Backtest must be COMPLETED for stress test; current status: {bt.status.value}"
                )
            )

    def _to_detail(self, st: StressTest) -> StressTestDetail:
        mc_out: MonteCarloResultOut | None = None
        wf_out: WalkForwardResultOut | None = None
        ca_out: GridSweepMetricsResultOut | None = None
        ps_out: GridSweepMetricsResultOut | None = None
        if st.status == StressTestStatus.COMPLETED and st.result is not None:
            if st.kind == StressTestKind.MONTE_CARLO:
                mc_out = MonteCarloResultOut.model_validate(mc_result_from_jsonb(st.result))
            elif st.kind == StressTestKind.WALK_FORWARD:
                wf_out = WalkForwardResultOut.model_validate(wf_result_from_jsonb(st.result))
            elif st.kind == StressTestKind.COST_ASSUMPTION_SENSITIVITY:
                ca_out = GridSweepMetricsResultOut.model_validate(
                    grid_metrics_result_from_jsonb(st.result)
                )
            elif st.kind == StressTestKind.PARAM_STABILITY:
                ps_out = GridSweepMetricsResultOut.model_validate(
                    grid_metrics_result_from_jsonb(st.result)
                )
        return StressTestDetail(
            id=st.id,
            backtest_id=st.backtest_id,
            kind=st.kind,
            status=st.status,
            params=dict(st.params) if st.params else {},
            monte_carlo_result=mc_out,
            walk_forward_result=wf_out,
            cost_assumption_result=ca_out,
            param_stability_result=ps_out,
            error=st.error,
            created_at=st.created_at,
            started_at=st.started_at,
            completed_at=st.completed_at,
        )
