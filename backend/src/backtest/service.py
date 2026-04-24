"""BacktestService — HTTP 경로와 Worker 경로 양쪽에서 사용."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pandas as pd

from src.backtest.dispatcher import TaskDispatcher
from src.backtest.engine import run_backtest
from src.backtest.engine.types import RawTrade
from src.backtest.exceptions import (
    BacktestDuplicateIdempotencyKey,
    BacktestNotFound,
    BacktestStateConflict,
    StrategyNotRunnable,
    TaskDispatchError,
)
from src.backtest.models import (
    Backtest,
    BacktestStatus,
    BacktestTrade,
    TradeDirection,
    TradeStatus,
)
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import (
    BacktestCancelResponse,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestMetricsOut,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    EquityPoint,
    TradeItem,
)
from src.backtest.serializers import (
    _parse_utc_iso,
    equity_curve_to_jsonb,
    metrics_from_jsonb,
    metrics_to_jsonb,
)
from src.common.pagination import Page
from src.core.config import settings
from src.market_data.providers import OHLCVProvider
from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.repository import StrategyRepository

logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(
        self,
        *,
        repo: BacktestRepository,
        strategy_repo: StrategyRepository,
        ohlcv_provider: OHLCVProvider,
        dispatcher: TaskDispatcher,
    ) -> None:
        self.repo = repo
        self.strategy_repo = strategy_repo
        self.provider = ohlcv_provider
        self.dispatcher = dispatcher

    # --- HTTP submit path ---

    async def submit(
        self,
        data: CreateBacktestRequest,
        *,
        user_id: UUID,
        idempotency_key: str | None = None,
    ) -> BacktestCreatedResponse:
        body_hash: bytes | None = None
        if idempotency_key is not None:
            body_hash = _compute_body_hash(data, user_id)
            await self.repo.acquire_idempotency_lock(idempotency_key)
            existing = await self.repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                # Sprint 9-6 E2: hash 비교 — 일치 → replay, 불일치(또는 NULL) → 409.
                # 기존 NULL hash row (E1 이전) 은 어떤 body 와도 match 불가 (안전성).
                if (
                    existing.idempotency_payload_hash is not None
                    and existing.idempotency_payload_hash == body_hash
                ):
                    return BacktestCreatedResponse(
                        backtest_id=existing.id,
                        status=existing.status,
                        created_at=existing.created_at,
                        replayed=True,
                    )
                raise BacktestDuplicateIdempotencyKey(
                    detail=(
                        f"Idempotency-Key reused with different payload; "
                        f"existing backtest_id={existing.id}"
                    )
                )

        strategy = await self.strategy_repo.find_by_id_and_owner(data.strategy_id, user_id)
        if strategy is None:
            raise StrategyNotFoundError()

        # Sprint Y1: pre-flight coverage check — 미지원 built-in 발견 시 즉시 reject
        # (whack-a-mole 패턴 종식 — backtest 실행 전에 명확히 안내)
        coverage = analyze_coverage(strategy.pine_source)
        if not coverage.is_runnable:
            unsupported = ", ".join(coverage.all_unsupported)
            raise StrategyNotRunnable(
                detail=(
                    f"Strategy contains unsupported Pine built-ins: {unsupported}. "
                    f"See docs/02_domain/supported-indicators.md for the supported list."
                )
            )

        bt = Backtest(
            user_id=user_id,
            strategy_id=data.strategy_id,
            symbol=data.symbol,
            timeframe=data.timeframe,
            period_start=data.period_start,
            period_end=data.period_end,
            initial_capital=data.initial_capital,
            status=BacktestStatus.QUEUED,
            idempotency_key=idempotency_key,
            idempotency_payload_hash=body_hash,
        )
        await self.repo.create(bt)

        try:
            task_id = self.dispatcher.dispatch_backtest(bt.id)
        except Exception as exc:
            await self.repo.rollback()
            logger.exception("task_dispatch_failed")
            raise TaskDispatchError() from exc

        bt.celery_task_id = task_id
        await self.repo.commit()
        return BacktestCreatedResponse(
            backtest_id=bt.id, status=bt.status, created_at=bt.created_at
        )

    # --- Worker run path (§5.1 3-guard) ---

    async def run(self, backtest_id: UUID) -> None:
        """Worker _execute() 엔트리. 3-guard cancel + finalize_cancelled 수습."""
        bt = await self.repo.get_by_id(backtest_id)
        if bt is None:
            logger.warning(
                "backtest_not_found_in_worker",
                extra={"bt_id": str(backtest_id)},
            )
            return

        # Guard #1: pickup
        if bt.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))
            await self.repo.commit()
            return
        if bt.status != BacktestStatus.QUEUED:
            logger.info(
                "worker_skip_non_queued",
                extra={"bt_id": str(bt.id), "status": bt.status.value},
            )
            return

        # Strategy + OHLCV
        strategy = await self.strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
        if strategy is None:
            await self.repo.fail(
                backtest_id,
                error="Strategy not found at execute time",
                where_status=BacktestStatus.QUEUED,
            )
            await self.repo.commit()
            return

        try:
            ohlcv = await self.provider.get_ohlcv(
                bt.symbol, bt.timeframe, bt.period_start, bt.period_end
            )
        except Exception as exc:
            logger.exception("ohlcv_fetch_failed")
            await self.repo.fail(
                backtest_id,
                error=f"OHLCV fetch failed: {exc}",
                where_status=BacktestStatus.QUEUED,
            )
            await self.repo.commit()
            return

        # Transition queued → running (조건부)
        rows = await self.repo.transition_to_running(backtest_id, started_at=datetime.now(UTC))
        if rows == 0:
            # cancel이 선행됨 → cancelling → finalize_cancelled
            await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))
            await self.repo.commit()
            return
        await self.repo.commit()

        # Guard #2: pre-engine
        bt2 = await self.repo.get_by_id(backtest_id)
        if bt2 is None:
            logger.error(
                "backtest_vanished_pre_engine",
                extra={"bt_id": str(backtest_id)},
            )
            return
        if bt2.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))
            await self.repo.commit()
            return

        # Engine (sync CPU-bound — await 없이 직접 호출)
        outcome = run_backtest(strategy.pine_source, ohlcv)

        # Guard #3: post-engine
        bt3 = await self.repo.get_by_id(backtest_id)
        if bt3 is None:
            logger.error(
                "backtest_vanished_post_engine",
                extra={"bt_id": str(backtest_id)},
            )
            return
        if bt3.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))
            await self.repo.commit()
            return

        # Terminal write (조건부 UPDATE + bulk insert trades):
        # Spec §5.1 Step 10의 begin_nested() savepoint는 commit이 분리될 때의 원자성용.
        # 현재 설계는 complete() + insert_trades_bulk() + commit()을 단일 트랜잭션으로 묶으므로
        # savepoint 없이 atomically correct. 미래에 commit을 중간에 분리하지 말 것.
        if outcome.status == "ok" and outcome.result is not None:
            metrics_jsonb = metrics_to_jsonb(outcome.result.metrics)
            equity_jsonb = equity_curve_to_jsonb(outcome.result.equity_curve)

            completed_rows = await self.repo.complete(
                backtest_id,
                metrics=metrics_jsonb,
                equity_curve=equity_jsonb,
            )
            if completed_rows == 0:
                await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))
                await self.repo.commit()
                return

            trade_models = self._raw_trades_to_models(
                outcome.result.trades, backtest_id, pd.DatetimeIndex(ohlcv.index)
            )
            if trade_models:
                await self.repo.insert_trades_bulk(trade_models)
        else:
            error_str = (
                str(outcome.error)
                if outcome.error is not None
                else (f"engine status={outcome.status}")
            )
            fail_rows = await self.repo.fail(backtest_id, error=error_str)
            if fail_rows == 0:
                await self.repo.finalize_cancelled(backtest_id, completed_at=datetime.now(UTC))

        await self.repo.commit()

    def _raw_trades_to_models(
        self,
        raw_trades: list[RawTrade],
        backtest_id: UUID,
        ohlcv_index: pd.DatetimeIndex,
    ) -> list[BacktestTrade]:
        """RawTrade → BacktestTrade. bar_index → datetime."""
        result: list[BacktestTrade] = []
        for t in raw_trades:
            entry_time = ohlcv_index[t.entry_bar_index].to_pydatetime()
            exit_time = None
            if t.exit_bar_index is not None:
                exit_time = ohlcv_index[t.exit_bar_index].to_pydatetime()
            result.append(
                BacktestTrade(
                    backtest_id=backtest_id,
                    trade_index=t.trade_index,
                    direction=TradeDirection(t.direction),
                    status=TradeStatus(t.status),
                    entry_time=entry_time,
                    exit_time=exit_time,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    size=t.size,
                    pnl=t.pnl,
                    return_pct=t.return_pct,
                    fees=t.fees,
                )
            )
        return result

    # --- HTTP read paths ---

    async def get(self, backtest_id: UUID, *, user_id: UUID) -> BacktestDetail:
        bt = await self._load_owned(backtest_id, user_id)
        return self._to_detail(bt)

    async def list(self, *, user_id: UUID, limit: int, offset: int) -> Page[BacktestSummary]:
        items, total = await self.repo.list_by_user(user_id, limit=limit, offset=offset)
        return Page[BacktestSummary](
            items=[BacktestSummary.model_validate(bt) for bt in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def progress(self, backtest_id: UUID, *, user_id: UUID) -> BacktestProgressResponse:
        bt = await self._load_owned(backtest_id, user_id)
        threshold = settings.backtest_stale_threshold_seconds
        now = datetime.now(UTC)
        is_stale = (
            bt.status in (BacktestStatus.RUNNING, BacktestStatus.CANCELLING)
            and bt.started_at is not None
            and (now - bt.started_at) > timedelta(seconds=threshold)
        )
        return BacktestProgressResponse(
            backtest_id=bt.id,
            status=bt.status,
            started_at=bt.started_at,
            completed_at=bt.completed_at,
            error=bt.error,
            stale=is_stale,
        )

    async def list_trades(
        self, backtest_id: UUID, *, user_id: UUID, limit: int, offset: int
    ) -> Page[TradeItem]:
        await self._load_owned(backtest_id, user_id)  # 404 guard
        items, total = await self.repo.list_trades(backtest_id, limit=limit, offset=offset)
        return Page[TradeItem](
            items=[TradeItem.model_validate(t) for t in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    # --- HTTP mutation paths ---

    async def cancel(self, backtest_id: UUID, *, user_id: UUID) -> BacktestCancelResponse:
        bt = await self._load_owned(backtest_id, user_id)
        if bt.status not in (BacktestStatus.QUEUED, BacktestStatus.RUNNING):
            raise BacktestStateConflict(
                detail=f"Cancel requires queued or running; current: {bt.status.value}"
            )

        # Best-effort revoke
        if bt.celery_task_id:
            try:
                from celery.result import (  # type: ignore[import-untyped]  # 지연 import (순환 방지)
                    AsyncResult,
                )

                from src.tasks.celery_app import celery_app

                AsyncResult(bt.celery_task_id, app=celery_app).revoke(terminate=True)
            except Exception:
                logger.exception("revoke_failed", extra={"bt_id": str(bt.id)})

        rows = await self.repo.request_cancel(backtest_id)
        if rows == 0:
            # Race loser — re-fetch for accurate error detail
            current = await self.repo.get_by_id(backtest_id, user_id=user_id)
            current_status = current.status.value if current else "unknown"
            raise BacktestStateConflict(detail=f"Already terminal: {current_status}")
        await self.repo.commit()

        return BacktestCancelResponse(
            backtest_id=bt.id,
            status=BacktestStatus.CANCELLING,
            message=("Cancellation requested. Final state via GET /:id/progress."),
        )

    async def delete(self, backtest_id: UUID, *, user_id: UUID) -> None:
        bt = await self._load_owned(backtest_id, user_id)
        terminal = (
            BacktestStatus.COMPLETED,
            BacktestStatus.FAILED,
            BacktestStatus.CANCELLED,
        )
        if bt.status not in terminal:
            raise BacktestStateConflict(
                detail=(
                    f"Delete requires terminal state; current: {bt.status.value}. "
                    "Try cancel first and wait for final state."
                )
            )
        await self.repo.delete(backtest_id)
        await self.repo.commit()

    # --- helpers ---

    async def _load_owned(self, backtest_id: UUID, user_id: UUID) -> Backtest:
        bt = await self.repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            raise BacktestNotFound()
        return bt

    def _to_detail(self, bt: Backtest) -> BacktestDetail:
        metrics_out: BacktestMetricsOut | None = None
        equity_out: list[EquityPoint] | None = None
        if bt.status == BacktestStatus.COMPLETED:
            if bt.metrics:
                m = metrics_from_jsonb(bt.metrics)
                metrics_out = BacktestMetricsOut(
                    total_return=m.total_return,
                    sharpe_ratio=m.sharpe_ratio,
                    max_drawdown=m.max_drawdown,
                    win_rate=m.win_rate,
                    num_trades=m.num_trades,
                    sortino_ratio=m.sortino_ratio,
                    calmar_ratio=m.calmar_ratio,
                    profit_factor=m.profit_factor,
                    avg_win=m.avg_win,
                    avg_loss=m.avg_loss,
                    long_count=m.long_count,
                    short_count=m.short_count,
                )
            if bt.equity_curve:
                equity_out = [
                    EquityPoint(
                        timestamp=_parse_utc_iso(ts),
                        value=Decimal(v),
                    )
                    for ts, v in bt.equity_curve
                ]
        return BacktestDetail(
            id=bt.id,
            strategy_id=bt.strategy_id,
            symbol=bt.symbol,
            timeframe=bt.timeframe,
            period_start=bt.period_start,
            period_end=bt.period_end,
            status=bt.status,
            created_at=bt.created_at,
            completed_at=bt.completed_at,
            initial_capital=bt.initial_capital,
            metrics=metrics_out,
            equity_curve=equity_out,
            error=bt.error,
        )


# ---------------------------------------------------------------------------
# Sprint 9-6 E2 — Idempotency body hash.
# ---------------------------------------------------------------------------


def _compute_body_hash(data: CreateBacktestRequest, user_id: UUID) -> bytes:
    """SHA-256(CreateBacktestRequest JSON + user_id).

    user_id 포함으로 cross-user key 재사용을 conflict 로 분류 (user A 가 key=K
    로 제출 후 user B 가 같은 key 로 제출 → 409). `model_dump(mode="json")` 는
    Decimal/datetime 을 JSON-safe string 으로 직렬화해 결정적 bytes 생성.
    """
    payload = {**data.model_dump(mode="json"), "user_id": str(user_id)}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).digest()
