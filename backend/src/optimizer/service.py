"""OptimizerService — HTTP submit 경로 + Worker run 경로 (Sprint 54 Phase 3).

Router → Service → Repository 3-Layer. **AsyncSession import 절대 금지** (backend.md §3).

- submit_grid_search: Backtest ownership + COMPLETED 검증, OptimizationRun 레코드 생성,
  Celery task dispatch.
- run(run_id): Worker 엔트리. backtest config + ohlcv + strategy pine 로드 → engine 호출 →
  result_jsonb 저장. BL-230: error_message 는 internal 메시지 truncate 후 저장.
- get / list: ownership 격리된 조회.

stress_test/service.py pattern 1:1 mirror.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from src.backtest.config_mapper import build_engine_config_from_db
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.common.pagination import Page
from src.market_data.providers import OHLCVProvider
from src.optimizer.dispatcher import OptimizationTaskDispatcher
from src.optimizer.engine import run_bayesian_search, run_grid_search
from src.optimizer.exceptions import (
    BacktestNotCompletedForOptimization,
    OptimizationExecutionError,
    OptimizationKindUnsupportedError,
    OptimizationNotFoundError,
    OptimizationTaskDispatchError,
    truncate_error_message,
)
from src.optimizer.models import (
    OptimizationKind,
    OptimizationRun,
    OptimizationStatus,
)
from src.optimizer.repository import OptimizationRepository
from src.optimizer.schemas import (
    CreateOptimizationRunRequest,
    OptimizationKindOut,
    OptimizationRunResponse,
    ParamSpace,
)
from src.optimizer.serializers import (
    bayesian_search_result_to_jsonb,
    grid_search_result_to_jsonb,
)
from src.strategy.repository import StrategyRepository

logger = logging.getLogger(__name__)


class OptimizerService:
    def __init__(
        self,
        *,
        repo: OptimizationRepository,
        backtest_repo: BacktestRepository,
        strategy_repo: StrategyRepository,
        ohlcv_provider: OHLCVProvider,
        dispatcher: OptimizationTaskDispatcher,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo
        self.strategy_repo = strategy_repo
        self.provider = ohlcv_provider
        self.dispatcher = dispatcher

    # ---------- HTTP submit ----------

    async def submit_grid_search(
        self,
        data: CreateOptimizationRunRequest,
        *,
        user_id: UUID,
    ) -> OptimizationRunResponse:
        """Sprint 54 Phase 3 — Grid Search MVP submit."""
        if data.kind != OptimizationKindOut.GRID_SEARCH:
            raise OptimizationKindUnsupportedError(data.kind.value)
        return await self._submit_optimization(
            data,
            user_id=user_id,
            kind=OptimizationKind.GRID_SEARCH,
        )

    async def submit_bayesian(
        self,
        data: CreateOptimizationRunRequest,
        *,
        user_id: UUID,
    ) -> OptimizationRunResponse:
        """Sprint 55 Phase 3 — Bayesian executor submit (ADR-013 §6 #5)."""
        if data.kind != OptimizationKindOut.BAYESIAN:
            raise OptimizationKindUnsupportedError(data.kind.value)
        # cross-field validator (schemas) 가 1차 강제. defensive 재확인.
        if data.param_space.schema_version != 2:
            raise OptimizationKindUnsupportedError(
                f"bayesian:schema_version={data.param_space.schema_version}"
            )
        return await self._submit_optimization(
            data,
            user_id=user_id,
            kind=OptimizationKind.BAYESIAN,
        )

    async def _submit_optimization(
        self,
        data: CreateOptimizationRunRequest,
        *,
        user_id: UUID,
        kind: OptimizationKind,
    ) -> OptimizationRunResponse:
        """공통 submit path — Backtest ownership + COMPLETED + dispatch."""
        bt = await self._load_owned_backtest(data.backtest_id, user_id)
        self._ensure_completed(bt)

        run = OptimizationRun(
            user_id=user_id,
            backtest_id=bt.id,
            kind=kind,
            status=OptimizationStatus.QUEUED,
            param_space=data.param_space.model_dump(mode="json"),
        )
        await self.repo.create(run)

        try:
            task_id = self.dispatcher.dispatch_optimization(run.id)
        except Exception as exc:
            await self.repo.rollback()
            logger.exception("optimizer_task_dispatch_failed")
            raise OptimizationTaskDispatchError() from exc

        run.celery_task_id = task_id
        await self.repo.commit()
        return self._to_response(run)

    # ---------- Worker run ----------

    async def run(self, run_id: UUID) -> None:
        """Worker entrypoint — Grid Search executor 호출."""
        run = await self.repo.get_by_id(run_id)
        if run is None:
            logger.warning(
                "optimization_run_not_found_in_worker",
                extra={"run_id": str(run_id)},
            )
            return
        if run.status != OptimizationStatus.QUEUED:
            logger.info(
                "worker_skip_non_queued_optimization",
                extra={"run_id": str(run.id), "status": run.status.value},
            )
            return

        bt = await self.backtest_repo.get_by_id(run.backtest_id)
        if bt is None or bt.status != BacktestStatus.COMPLETED:
            await self.repo.fail(
                run_id,
                error_message=truncate_error_message(
                    "Referenced backtest unavailable or not COMPLETED at execute time"
                ),
            )
            await self.repo.commit()
            return

        rows = await self.repo.transition_to_running(
            run_id, started_at=datetime.now(UTC)
        )
        if rows == 0:
            logger.info(
                "optimization_state_changed_before_run",
                extra={"run_id": str(run_id)},
            )
            return
        await self.repo.commit()

        try:
            if run.kind == OptimizationKind.GRID_SEARCH:
                result_jsonb = await self._execute_grid_search(run, bt)
            elif run.kind == OptimizationKind.BAYESIAN:
                result_jsonb = await self._execute_bayesian(run, bt)
            else:  # pragma: no cover — exhaustiveness guard
                raise OptimizationKindUnsupportedError(run.kind.value)
        except OptimizationExecutionError as exc:
            logger.exception("optimizer_execution_failed")
            await self.repo.fail(
                run_id,
                error_message=truncate_error_message(exc.message_internal),
                where_status=OptimizationStatus.RUNNING,
            )
            await self.repo.commit()
            return
        except Exception as exc:
            logger.exception("optimizer_unexpected_failure")
            await self.repo.fail(
                run_id,
                error_message=truncate_error_message(str(exc)),
                where_status=OptimizationStatus.RUNNING,
            )
            await self.repo.commit()
            return

        completed_rows = await self.repo.complete(run_id, result=result_jsonb)
        if completed_rows == 0:
            logger.warning(
                "optimization_complete_no_rows",
                extra={"run_id": str(run_id)},
            )
        await self.repo.commit()

    async def _execute_grid_search(
        self, run: OptimizationRun, bt: Backtest
    ) -> dict[str, object]:
        """Grid Search 실행 entry — param_space JSONB → ParamSpace → executor."""
        strategy = await self.strategy_repo.find_by_id_and_owner(
            bt.strategy_id, bt.user_id
        )
        if strategy is None:
            raise OptimizationExecutionError(
                message_public="Strategy no longer available for optimization.",
                message_internal=(
                    f"strategy_id={bt.strategy_id} owner={bt.user_id} not found"
                ),
            )

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        # JSONB → ParamSpace pydantic (schema_version=1 lock 안전성 보장).
        param_space = ParamSpace.model_validate(run.param_space)
        backtest_config = build_engine_config_from_db(bt)

        gs_result = run_grid_search(
            strategy.pine_source,
            ohlcv,
            param_space=param_space,
            backtest_config=backtest_config,
        )
        return grid_search_result_to_jsonb(gs_result)

    async def _execute_bayesian(
        self, run: OptimizationRun, bt: Backtest
    ) -> dict[str, object]:
        """Bayesian 실행 entry — _execute_grid_search mirror, run_bayesian_search 호출."""
        strategy = await self.strategy_repo.find_by_id_and_owner(
            bt.strategy_id, bt.user_id
        )
        if strategy is None:
            raise OptimizationExecutionError(
                message_public="Strategy no longer available for optimization.",
                message_internal=(
                    f"strategy_id={bt.strategy_id} owner={bt.user_id} not found"
                ),
            )

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        param_space = ParamSpace.model_validate(run.param_space)
        backtest_config = build_engine_config_from_db(bt)

        bs_result = run_bayesian_search(
            strategy.pine_source,
            ohlcv,
            param_space=param_space,
            backtest_config=backtest_config,
        )
        return bayesian_search_result_to_jsonb(bs_result)

    # ---------- HTTP read ----------

    async def get(
        self, run_id: UUID, *, user_id: UUID
    ) -> OptimizationRunResponse:
        run = await self._load_owned(run_id, user_id)
        return self._to_response(run)

    async def list(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
        backtest_id: UUID | None = None,
    ) -> Page[OptimizationRunResponse]:
        items, total = await self.repo.list_by_user(
            user_id, limit=limit, offset=offset, backtest_id=backtest_id
        )
        return Page[OptimizationRunResponse](
            items=[self._to_response(r) for r in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ---------- helpers ----------

    async def _load_owned(self, run_id: UUID, user_id: UUID) -> OptimizationRun:
        run = await self.repo.get_by_id(run_id, user_id=user_id)
        if run is None:
            raise OptimizationNotFoundError(run_id)
        return run

    async def _load_owned_backtest(self, backtest_id: UUID, user_id: UUID) -> Backtest:
        bt = await self.backtest_repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            from src.backtest.exceptions import BacktestNotFound

            raise BacktestNotFound()
        return bt

    @staticmethod
    def _ensure_completed(bt: Backtest) -> None:
        if bt.status != BacktestStatus.COMPLETED:
            raise BacktestNotCompletedForOptimization(
                detail=(
                    f"Backtest must be COMPLETED for optimization; "
                    f"current status: {bt.status.value}"
                )
            )

    @staticmethod
    def _to_response(run: OptimizationRun) -> OptimizationRunResponse:
        return OptimizationRunResponse(
            id=run.id,
            user_id=run.user_id,
            backtest_id=run.backtest_id,
            kind=OptimizationKindOut(run.kind.value),
            status=run.status.value,  # type: ignore[arg-type]  # StrEnum → Literal mirror
            param_space=ParamSpace.model_validate(run.param_space),
            result=run.result,
            error_message=run.error_message,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
