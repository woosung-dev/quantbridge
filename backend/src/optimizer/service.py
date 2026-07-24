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

from pydantic import ValidationError

from src.backtest.config_mapper import build_engine_config_from_db
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.common.pagination import Page
from src.market_data.providers import OHLCVProvider
from src.optimizer.dispatcher import OptimizationTaskDispatcher
from src.optimizer.engine.select import run_optimizer_by_kind
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
from src.optimizer.serializers import optimizer_result_to_jsonb
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

    async def submit_genetic(
        self,
        data: CreateOptimizationRunRequest,
        *,
        user_id: UUID,
    ) -> OptimizationRunResponse:
        """Sprint 56 Phase 3 — Genetic executor submit (BL-233, Bayesian 1:1 mirror)."""
        if data.kind != OptimizationKindOut.GENETIC:
            raise OptimizationKindUnsupportedError(data.kind.value)
        # cross-field validator (schemas) 가 1차 강제. defensive 재확인.
        if data.param_space.schema_version != 2:
            raise OptimizationKindUnsupportedError(
                f"genetic:schema_version={data.param_space.schema_version}"
            )
        return await self._submit_optimization(
            data,
            user_id=user_id,
            kind=OptimizationKind.GENETIC,
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
        return self._to_response(run, bt)

    # ---------- Worker run ----------

    async def run(self, run_id: UUID) -> None:
        """Worker entrypoint — Grid Search executor 호출."""
        row = await self.repo.get_by_id(run_id)
        if row is None:
            logger.warning(
                "optimization_run_not_found_in_worker",
                extra={"run_id": str(run_id)},
            )
            return
        run, backtest = row
        if run.status != OptimizationStatus.QUEUED:
            logger.info(
                "worker_skip_non_queued_optimization",
                extra={"run_id": str(run.id), "status": run.status.value},
            )
            return

        if backtest is None or backtest.status != BacktestStatus.COMPLETED:
            await self.repo.fail(
                run_id,
                error_message=truncate_error_message(
                    "Referenced backtest unavailable or not COMPLETED at execute time"
                ),
            )
            await self.repo.commit()
            return

        bt = backtest

        rows = await self.repo.transition_to_running(run_id, started_at=datetime.now(UTC))
        if rows == 0:
            logger.info(
                "optimization_state_changed_before_run",
                extra={"run_id": str(run_id)},
            )
            return
        await self.repo.commit()

        try:
            result_jsonb = await self._execute(run, bt)
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

    async def _execute(self, run: OptimizationRun, bt: Backtest) -> dict[str, object]:
        """공통 executor 경로 — strategy/ohlcv/config load 후 엔진 선택 SSOT 위임.

        optimizer-deepen A: 잔여 `match run.kind` 를 engine.select.run_optimizer_by_kind
        (walk_forward 와 공유)로, runner→serializer 페어링을 optimizer_result_to_jsonb 로
        흡수. 테스트 monkeypatch seam 은 runner 3이름 → 본 모듈의
        ``run_optimizer_by_kind`` 1이름으로 축소 (test_service_commits.py).
        """
        strategy = await self.strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
        if strategy is None:
            raise OptimizationExecutionError(
                message_public="Strategy no longer available for optimization.",
                message_internal=(f"strategy_id={bt.strategy_id} owner={bt.user_id} not found"),
            )

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )
        # JSONB → ParamSpace pydantic (schema_version lock 안전성 보장).
        param_space = ParamSpace.model_validate(run.param_space)
        backtest_config = build_engine_config_from_db(bt)
        pine = strategy.pine_source

        result = run_optimizer_by_kind(
            run.kind, pine, ohlcv, param_space=param_space, backtest_config=backtest_config
        )
        return optimizer_result_to_jsonb(result)

    # ---------- HTTP read ----------

    async def get(self, run_id: UUID, *, user_id: UUID) -> OptimizationRunResponse:
        run, backtest = await self._load_owned(run_id, user_id)
        response = self._to_response_or_none(run, backtest)
        if response is None:
            # deepen C-min: 손상 row (Sprint 50-52 retro-incorrect param_space) 는
            # list 에서 skip 되므로 상세 조회도 500 대신 404 로 대칭 처리.
            raise OptimizationNotFoundError(run_id)
        return response

    async def list(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
        backtest_id: UUID | None = None,
    ) -> Page[OptimizationRunResponse]:
        # Sprint 62 T-1 (BL-350/354): row-level resilience. Sprint 50-52 retro-incorrect row
        # + 53-55 schema tightening 합집합으로 _to_response 가 Pydantic ValidationError raise 시
        # 응답 전체 500 fail. 손상 row 방어는 _to_response_or_none SSOT (deepen C-min, get 대칭).
        items, total = await self.repo.list_by_user(
            user_id, limit=limit, offset=offset, backtest_id=backtest_id
        )
        valid_items = [
            response
            for run, backtest in items
            if (response := self._to_response_or_none(run, backtest)) is not None
        ]
        return Page[OptimizationRunResponse](
            items=valid_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ---------- helpers ----------

    async def _load_owned(
        self, run_id: UUID, user_id: UUID
    ) -> tuple[OptimizationRun, Backtest | None]:
        row = await self.repo.get_by_id(run_id, user_id=user_id)
        if row is None:
            raise OptimizationNotFoundError(run_id)
        return row

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

    def _to_response_or_none(
        self, run: OptimizationRun, backtest: Backtest | None = None
    ) -> OptimizationRunResponse | None:
        """손상 row 방어 SSOT (deepen C-min) — get/list 대칭. 변환 실패 시 WARN + None.

        catch 는 손상 row 가 실제로 내는 예외로 한정 — ValidationError(retro-incorrect
        param_space) + ValueError(구 enum 값 등). 그 외 프로그래밍 버그는 기존처럼
        시끄럽게 500 으로 표면 (적대 리뷰 P2-2: broad except 는 미래 버그를 404 로 위장).
        """
        try:
            return self._to_response(run, backtest)
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "optimizer_run_skip_invalid_schema run_id=%s err=%s",
                run.id,
                exc,
            )
            return None

    @staticmethod
    def _to_response(
        run: OptimizationRun, backtest: Backtest | None = None
    ) -> OptimizationRunResponse:
        return OptimizationRunResponse(
            id=run.id,
            user_id=run.user_id,
            backtest_id=run.backtest_id,
            strategy_id=backtest.strategy_id if backtest is not None else None,
            backtest_symbol=backtest.symbol if backtest is not None else None,
            backtest_timeframe=backtest.timeframe if backtest is not None else None,
            backtest_period_start=backtest.period_start if backtest is not None else None,
            backtest_period_end=backtest.period_end if backtest is not None else None,
            kind=OptimizationKindOut(run.kind.value),
            status=run.status.value,  # type: ignore[arg-type]  # StrEnum → Literal mirror
            param_space=ParamSpace.model_validate(run.param_space),
            result=run.result,
            error_message=run.error_message,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
