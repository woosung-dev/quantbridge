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
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.backtest.config_mapper import build_engine_config_from_db
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.common.pagination import Page
from src.market_data.providers import OHLCVProvider
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import StressTaskDispatcher
from src.stress_test.engine import (
    run_cost_assumption_sensitivity,
    run_monte_carlo,
    run_param_stability,
    run_walk_forward,
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
    CostAssumptionResultOut,
    CostAssumptionSubmitRequest,
    MonteCarloResultOut,
    MonteCarloSubmitRequest,
    ParamStabilityResultOut,
    ParamStabilitySubmitRequest,
    StressTestCreatedResponse,
    StressTestDetail,
    StressTestSummary,
    WalkForwardResultOut,
    WalkForwardSubmitRequest,
)
from src.stress_test.serializers import (
    ca_result_from_jsonb,
    ca_result_to_jsonb,
    equity_curve_values,
    mc_result_from_jsonb,
    mc_result_to_jsonb,
    ps_result_from_jsonb,
    ps_result_to_jsonb,
    wf_result_from_jsonb,
    wf_result_to_jsonb,
)

logger = logging.getLogger(__name__)


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
                "param_grid": {
                    k: [str(v) for v in vs]
                    for k, vs in data.params.param_grid.items()
                },
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
                "param_grid": {
                    k: [str(v) for v in vs]
                    for k, vs in data.params.param_grid.items()
                },
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
                error=(
                    "Referenced backtest unavailable or not COMPLETED at execute time"
                ),
            )
            await self.repo.commit()
            return

        # QUEUED → RUNNING
        rows = await self.repo.transition_to_running(
            stress_test_id, started_at=datetime.now(UTC)
        )
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
                result_jsonb = await self._execute_cost_assumption_sensitivity(
                    st, bt
                )
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

        completed_rows = await self.repo.complete(
            stress_test_id, result=result_jsonb
        )
        if completed_rows == 0:
            logger.warning(
                "stress_test_complete_no_rows",
                extra={"stress_test_id": str(stress_test_id)},
            )
        await self.repo.commit()

    async def _execute_monte_carlo(
        self, st: StressTest, bt: Backtest
    ) -> dict[str, object]:
        curve = equity_curve_values(bt.equity_curve)
        if len(curve) < 2:
            raise ValueError(
                "Backtest equity_curve is empty or too short for Monte Carlo"
            )
        n_samples_raw = st.params.get("n_samples", 1000)
        seed_raw = st.params.get("seed", 42)
        n_samples = int(n_samples_raw) if n_samples_raw is not None else 1000
        seed = int(seed_raw) if seed_raw is not None else 42

        mc = run_monte_carlo(curve, n_samples=n_samples, seed=seed)
        return mc_result_to_jsonb(mc)

    async def _execute_walk_forward(
        self, st: StressTest, bt: Backtest
    ) -> dict[str, object]:
        strategy = await self.strategy_repo.find_by_id_and_owner(
            bt.strategy_id, bt.user_id
        )
        if strategy is None:
            raise ValueError("Strategy no longer available for walk-forward")

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        train_bars = int(st.params["train_bars"])
        test_bars = int(st.params["test_bars"])
        step_raw = st.params.get("step_bars")
        step_bars = int(step_raw) if step_raw is not None else None
        max_folds_raw = st.params.get("max_folds", 20)
        max_folds = int(max_folds_raw) if max_folds_raw is not None else 20

        wf = run_walk_forward(
            strategy.pine_source,
            ohlcv,
            train_bars=train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
            max_folds=max_folds,
        )
        return wf_result_to_jsonb(wf)

    async def _execute_cost_assumption_sensitivity(
        self, st: StressTest, bt: Backtest
    ) -> dict[str, object]:
        """Sprint 50 — Cost Assumption Sensitivity worker entry.

        Sprint 52 BL-222 P1 (2026-05-11): parent backtest config 전달. fees/slippage
        grid 가 override 하지만 init_cash / freq / trading_sessions / BL-188 v3 sizing
        5필드 등 cell 마다 보존 의무.
        """
        strategy = await self.strategy_repo.find_by_id_and_owner(
            bt.strategy_id, bt.user_id
        )
        if strategy is None:
            raise ValueError(
                "Strategy no longer available for cost assumption sensitivity"
            )

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        raw_grid = st.params["param_grid"]
        param_grid: dict[str, list[Decimal]] = {
            k: [Decimal(v) for v in vs] for k, vs in raw_grid.items()
        }
        backtest_config = build_engine_config_from_db(bt)
        ca = run_cost_assumption_sensitivity(
            strategy.pine_source,
            ohlcv,
            param_grid=param_grid,
            backtest_config=backtest_config,
        )
        return ca_result_to_jsonb(ca)

    async def _execute_param_stability(
        self, st: StressTest, bt: Backtest
    ) -> dict[str, object]:
        """Sprint 51 BL-220 — Param Stability worker entry.

        Sprint 52 BL-222 P1 (2026-05-11): parent backtest config 전달. input_overrides
        grid 가 cell 마다 sweep key 갱신하지만, init_cash / freq / fees / slippage /
        trading_sessions / BL-188 v3 sizing 5필드 등 그 외는 보존 의무.
        """
        strategy = await self.strategy_repo.find_by_id_and_owner(
            bt.strategy_id, bt.user_id
        )
        if strategy is None:
            raise ValueError("Strategy no longer available for param stability")

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        raw_grid = st.params["param_grid"]
        param_grid: dict[str, list[Decimal]] = {
            k: [Decimal(v) for v in vs] for k, vs in raw_grid.items()
        }
        backtest_config = build_engine_config_from_db(bt)
        ps = run_param_stability(
            strategy.pine_source,
            ohlcv,
            param_grid=param_grid,
            backtest_config=backtest_config,
        )
        return ps_result_to_jsonb(ps)

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
                    f"Backtest must be COMPLETED for stress test; "
                    f"current status: {bt.status.value}"
                )
            )

    def _to_detail(self, st: StressTest) -> StressTestDetail:
        mc_out: MonteCarloResultOut | None = None
        wf_out: WalkForwardResultOut | None = None
        ca_out: CostAssumptionResultOut | None = None
        ps_out: ParamStabilityResultOut | None = None
        if (
            st.status == StressTestStatus.COMPLETED
            and st.result is not None
        ):
            if st.kind == StressTestKind.MONTE_CARLO:
                mc_out = MonteCarloResultOut.model_validate(
                    mc_result_from_jsonb(st.result)
                )
            elif st.kind == StressTestKind.WALK_FORWARD:
                wf_out = WalkForwardResultOut.model_validate(
                    wf_result_from_jsonb(st.result)
                )
            elif st.kind == StressTestKind.COST_ASSUMPTION_SENSITIVITY:
                ca_out = CostAssumptionResultOut.model_validate(
                    ca_result_from_jsonb(st.result)
                )
            elif st.kind == StressTestKind.PARAM_STABILITY:
                ps_out = ParamStabilityResultOut.model_validate(
                    ps_result_from_jsonb(st.result)
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
