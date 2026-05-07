"""BacktestService — HTTP 경로와 Worker 경로 양쪽에서 사용."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

import pandas as pd

from src.backtest.dispatcher import TaskDispatcher
from src.backtest.engine import run_backtest
from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.exceptions import (
    BacktestDuplicateIdempotencyKey,
    BacktestNotFound,
    BacktestShareRevoked,
    BacktestStateConflict,
    MirrorNotAllowed,
    PinePartialDeclaration,
    SizingSourceConflict,
    StrategyDegraded,
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
    BacktestConfigOut,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestMetricsOut,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    EquityPoint,
    ShareTokenResponse,
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
from src.strategy.models import Strategy
from src.strategy.pine_v2.compat import _extract_default_qty
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings

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
        """Sprint 11 Phase E — idempotency_key 가 있을 때 Service-level RedisLock 으로 감싼다.
        실질 분산 mutex. Redis 장애 시 RedisLock 이 graceful degrade → PG advisory 가 권위.
        """
        if idempotency_key is None:
            return await self._submit_inner(data, user_id=user_id, idempotency_key=None)

        from src.common.redlock import RedisLock

        async with RedisLock(f"idem:backtest:{idempotency_key}", ttl_ms=30_000):
            return await self._submit_inner(
                data, user_id=user_id, idempotency_key=idempotency_key
            )

    async def _submit_inner(
        self,
        data: CreateBacktestRequest,
        *,
        user_id: UUID,
        idempotency_key: str | None,
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
            unsupported_list = list(coverage.all_unsupported)
            unsupported_str = ", ".join(unsupported_list)
            raise StrategyNotRunnable(
                detail=(
                    f"Strategy contains unsupported Pine built-ins: {unsupported_str}. "
                    f"See docs/02_domain/supported-indicators.md for the supported list."
                ),
                unsupported_builtins=unsupported_list,
            )

        # Sprint 29 codex G2 P0 fix: degraded Pine semantic gate.
        # heikinashi / request.security / timeframe.period 는 supported 로 graceful 실행되지만
        # Pine 원본과 결과 차이 가능 (Trust Layer 위반). dogfood-first — 사용자 명시 동의 없이
        # 본 strategy backtest 차단.
        if coverage.has_degraded and not data.allow_degraded_pine:
            degraded_list = list(coverage.degraded_calls)
            degraded_str = ", ".join(degraded_list)
            raise StrategyDegraded(
                detail=(
                    f"Strategy uses degraded Pine functions: {degraded_str}. "
                    f"Set `allow_degraded_pine=true` in request body to acknowledge "
                    f"that backtest results may differ from Pine source. "
                    f"See docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md."
                ),
                degraded_calls=degraded_list,
            )

        # Sprint 31 BL-162a — 사용자 입력 BacktestConfig 5 가정 (TradingView 패턴).
        # Backtest.config JSONB 컬럼에 저장 → BacktestDetail.config 응답이 default
        # 가 아닌 사용자 입력값 → AssumptionsCard 가 (기본) 마크 자동 제거 (graceful upgrade).
        # Sprint 38 BL-188 v3 — sizing canonical helper 결정 + Live mirror metadata.
        # codex G.0 iter 1+2 must-fix 1 (sizing source 단일화) + must-fix 3 (leverage Nx
        # reject) + D2 (manual override) 반영. helper 가 Pine partial / Live Nx / double
        # sizing 모두 422 reject 책임.
        sizing_canonical = _resolve_sizing_canonical(data, strategy)

        config_payload: dict[str, Any] = {
            "leverage": float(data.leverage),
            "fees": float(data.fees_pct),
            "slippage": float(data.slippage_pct),
            "include_funding": bool(data.include_funding),
            # BL-188 v3 — sizing canonical metadata (BacktestConfig 5 신규 필드 → JSONB).
            "sizing_source": sizing_canonical["sizing_source"],
            "sizing_basis": sizing_canonical["sizing_basis"],
            "leverage_basis": sizing_canonical["leverage_basis"],
        }
        if sizing_canonical["default_qty_type"] is not None:
            config_payload["default_qty_type"] = sizing_canonical["default_qty_type"]
            config_payload["default_qty_value"] = sizing_canonical["default_qty_value"]
        if sizing_canonical["live_position_size_pct"] is not None:
            config_payload["live_position_size_pct"] = sizing_canonical[
                "live_position_size_pct"
            ]
        # BL-188 v3 — trading_sessions canonical (request 우선, strategy 다음, 빈값 = 24h).
        trading_sessions_canonical: list[str] = list(data.trading_sessions) or list(
            strategy.trading_sessions or []
        )
        if trading_sessions_canonical:
            config_payload["trading_sessions"] = trading_sessions_canonical

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
            config=config_payload,
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
        # Sprint 31 BL-162a — 사용자 입력 BacktestConfig 적용 (TradingView 패턴).
        # bt.config NULL (legacy) 시 engine default fallback.
        config = self._build_engine_config(bt)
        outcome = run_backtest(strategy.pine_source, ohlcv, config=config)

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

    def _build_engine_config(self, bt: Backtest) -> BacktestConfig:
        """Sprint 31 BL-162a — Backtest row 의 사용자 입력 config + initial_capital + timeframe →
        engine BacktestConfig.

        bt.config NULL (legacy / Sprint 30 이전) 시 engine default 사용 (init_cash /
        freq 만 bt 값 적용). bt.config 채워진 경우 leverage/fees/slippage/include_funding
        모두 사용자 입력값으로 override.

        Sprint 38 BL-188 v3 (codex iter 2 [P1] #3) — submit() 시점 helper 가 결정한
        sizing canonical 5 필드 + trading_sessions 를 BacktestConfig 로 propagate.
        본 매핑 누락 시 worker 가 Live mirror 결정 silent ignore = 거짓 trust 회복 실패.
        """
        default = BacktestConfig()
        cfg_dict: dict[str, Any] = bt.config if bt.config is not None else {}
        # BL-188a: 폼 입력 default_qty_type / default_qty_value 도 engine 으로 전달.
        # BL-188 v3 의 service helper 가 결정한 결과는 동일 키에 저장 (Pine 명시 시 Pine
        # 값, 폼 manual 시 사용자 입력값, Live mirror 시 None — live_position_size_pct
        # 만 채움). priority chain 최종 적용은 compat.parse_and_run_v2 에서.
        form_qty_type_raw = cfg_dict.get("default_qty_type")
        form_qty_value_raw = cfg_dict.get("default_qty_value")
        form_qty_type: str | None = (
            str(form_qty_type_raw) if form_qty_type_raw is not None else None
        )
        form_qty_value: float | None = (
            float(form_qty_value_raw) if form_qty_value_raw is not None else None
        )
        # BL-188 v3 — Live mirror canonical 5 필드 (codex iter 2 [P1] #3 매핑).
        live_pct_raw = cfg_dict.get("live_position_size_pct")
        live_pct: float | None = (
            float(live_pct_raw) if live_pct_raw is not None else None
        )
        sessions_raw = cfg_dict.get("trading_sessions") or []
        trading_sessions_tuple: tuple[str, ...] = tuple(sessions_raw)
        # sizing_source / sizing_basis Literal validation (legacy NULL → fallback).
        sizing_source_raw = cfg_dict.get("sizing_source") or "fallback"
        if sizing_source_raw not in {"pine", "live", "form", "fallback"}:
            sizing_source_raw = "fallback"
        sizing_source = cast(
            Literal["pine", "live", "form", "fallback"], sizing_source_raw
        )
        sizing_basis_raw = cfg_dict.get("sizing_basis") or "fallback_qty1"
        if sizing_basis_raw not in _VALID_SIZING_BASIS:
            sizing_basis_raw = "fallback_qty1"
        sizing_basis = cast(
            Literal[
                "pine_native",
                "live_available_balance_approx_equity",
                "form_equity",
                "fallback_qty1",
            ],
            sizing_basis_raw,
        )
        leverage_basis: float = float(
            cfg_dict.get("leverage_basis", default.leverage_basis)
        )
        return BacktestConfig(
            init_cash=bt.initial_capital,
            fees=float(cfg_dict.get("fees", default.fees)),
            slippage=float(cfg_dict.get("slippage", default.slippage)),
            freq=_timeframe_to_freq(bt.timeframe),
            trading_sessions=trading_sessions_tuple,
            leverage=float(cfg_dict.get("leverage", default.leverage)),
            include_funding=bool(
                cfg_dict.get("include_funding", default.include_funding)
            ),
            default_qty_type=form_qty_type,
            default_qty_value=form_qty_value,
            live_position_size_pct=live_pct,
            sizing_source=sizing_source,
            sizing_basis=sizing_basis,
            leverage_basis=leverage_basis,
        )

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
        # Sprint 31-E (BL-155): direction count consistency.
        # metrics.long_count/short_count 는 vectorbt `trades.long.count()` 기반으로
        # closed only 만 집계 → FE `trades.length` (open + closed) 와 1건 mismatch.
        # COMPLETED 상태일 때 trades 테이블에서 재집계해 사용자 시점 ("거래 목록"
        # 탭과 동일 모수) 으로 일관성 유지. 다른 상태는 trades 0건 → fallback.
        direction_counts: tuple[int, int, int] | None = None
        if bt.status == BacktestStatus.COMPLETED:
            direction_counts = await self.repo.count_trades_by_direction(bt.id)
        return self._to_detail(bt, direction_counts=direction_counts)

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

    # --- Sprint 41 Worker H — share link (public read-only + revoke) ---

    async def create_share(
        self, backtest_id: UUID, *, user_id: UUID
    ) -> ShareTokenResponse:
        """Owner 가 share_token 생성. 멱등 — 이미 active token 있으면 그대로 반환.

        codex P2 race condition fix: 동시 POST 2개가 둘 다 share_token=NULL 읽고
        다른 토큰 commit 하는 last-writer-wins race 차단. SELECT ... FOR UPDATE 로
        row lock → 직렬화. 두번째 요청은 첫 commit 대기 후 active 토큰 그대로 반환.

        revoke 후 재생성 시 새 토큰 발급 (기존 토큰은 영구 dead).
        """
        # 404 owner check 는 lock 없이 fast path 검증 (불필요한 lock 회피).
        await self._load_owned(backtest_id, user_id)
        # SELECT ... FOR UPDATE — race 직렬화. fresh state 로 active token 재확인.
        bt = await self.repo.get_by_id_for_update(backtest_id, user_id=user_id)
        if bt is None:
            raise BacktestNotFound()
        if bt.share_token is not None and bt.share_revoked_at is None:
            return ShareTokenResponse(
                backtest_id=bt.id,
                share_token=bt.share_token,
                share_url_path=f"/share/backtests/{bt.share_token}",
                revoked=False,
            )
        # 신규 또는 revoke 후 재생성 — 새 토큰. token_urlsafe(32) = 256-bit entropy.
        token = secrets.token_urlsafe(32)
        bt.share_token = token
        bt.share_revoked_at = None
        await self.repo.commit()
        return ShareTokenResponse(
            backtest_id=bt.id,
            share_token=token,
            share_url_path=f"/share/backtests/{token}",
            revoked=False,
        )

    async def revoke_share(self, backtest_id: UUID, *, user_id: UUID) -> None:
        """Owner 가 share_token 비활성화. 토큰 자체는 유지 (재활성화 불가).

        share_revoked_at = now(). 이후 view_share 가 410 Gone.
        """
        bt = await self._load_owned(backtest_id, user_id)
        if bt.share_token is None:
            # 토큰 없는데 revoke 호출 — no-op (idempotent).
            return
        bt.share_revoked_at = datetime.now(UTC)
        await self.repo.commit()

    async def view_share(self, token: str) -> BacktestDetail:
        """Public read-only — 인증 없음. owner check 안함 (토큰이 capability).

        Returns:
            BacktestDetail with `error=None` (민감 필드 strip).

        Raises:
            BacktestNotFound (404): token 매칭 row 없음.
            BacktestShareRevoked (410): row 있으나 revoke.
        """
        bt = await self.repo.get_by_share_token(token)
        if bt is None:
            raise BacktestNotFound()
        if bt.share_revoked_at is not None:
            raise BacktestShareRevoked()
        # 보안 — error stack trace 등 민감 정보 strip. status 만 노출.
        # Sprint 31-E direction count override 도 적용 (FE detail 페이지와 parity).
        direction_counts: tuple[int, int, int] | None = None
        if bt.status == BacktestStatus.COMPLETED:
            direction_counts = await self.repo.count_trades_by_direction(bt.id)
        detail = self._to_detail(bt, direction_counts=direction_counts)
        # 민감 필드 strip — public viewer 에 error 상세 노출 X.
        detail.error = None
        return detail

    # --- helpers ---

    async def _load_owned(self, backtest_id: UUID, user_id: UUID) -> Backtest:
        bt = await self.repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            raise BacktestNotFound()
        return bt

    def _to_detail(
        self,
        bt: Backtest,
        *,
        direction_counts: tuple[int, int, int] | None = None,
    ) -> BacktestDetail:
        """Backtest → BacktestDetail Pydantic 변환.

        Args:
            bt: ORM 인스턴스.
            direction_counts: optional (total, long, short). 제공 시 metrics
                num_trades/long_count/short_count 를 본 값으로 override
                (Sprint 31-E BL-155 — FE trades 목록과 사용자 시점 일관성).
                None 이면 JSONB 저장 값 (closed only) 그대로 사용 — 레거시
                fallback. trades 0건 (legacy 또는 trades 미저장) 일 때도 None
                전달해 JSONB 값 유지 권장.
        """
        metrics_out: BacktestMetricsOut | None = None
        equity_out: list[EquityPoint] | None = None
        # Sprint 31 BL-156 + BL-162a: config 5 가정 응답.
        # bt.config (사용자 입력 JSONB, BL-162a) 우선 사용 → 사용자가 BacktestForm
        # 에 입력한 비용/마진 값이 그대로 응답 → AssumptionsCard 가 (기본) 마크
        # 자동 제거 (graceful upgrade). bt.config NULL (legacy / Sprint 30 이전)
        # 시 engine BacktestConfig default fallback (graceful degrade).
        _default = BacktestConfig()
        if bt.config is not None:
            # 사용자 입력값 — float coerce + 누락 키는 default 로 fallback (방어).
            cfg_dict = bt.config
            config_out = BacktestConfigOut(
                leverage=float(cfg_dict.get("leverage", _default.leverage)),
                fees=float(cfg_dict.get("fees", _default.fees)),
                slippage=float(cfg_dict.get("slippage", _default.slippage)),
                include_funding=bool(
                    cfg_dict.get("include_funding", _default.include_funding)
                ),
            )
        else:
            config_out = BacktestConfigOut(
                leverage=_default.leverage,
                fees=_default.fees,
                slippage=_default.slippage,
                include_funding=_default.include_funding,
            )
        if bt.status == BacktestStatus.COMPLETED:
            if bt.metrics:
                m = metrics_from_jsonb(bt.metrics)
                # Sprint 31-E: direction count override.
                # trades 테이블에 1건 이상 있을 때만 override (0건 = legacy 또는
                # trades 비저장 케이스 → JSONB 값 유지로 backward-compat).
                if direction_counts is not None and direction_counts[0] > 0:
                    num_trades_out = direction_counts[0]
                    long_count_out: int | None = direction_counts[1]
                    short_count_out: int | None = direction_counts[2]
                else:
                    num_trades_out = m.num_trades
                    long_count_out = m.long_count
                    short_count_out = m.short_count
                metrics_out = BacktestMetricsOut(
                    total_return=m.total_return,
                    sharpe_ratio=m.sharpe_ratio,
                    max_drawdown=m.max_drawdown,
                    win_rate=m.win_rate,
                    num_trades=num_trades_out,
                    sortino_ratio=m.sortino_ratio,
                    calmar_ratio=m.calmar_ratio,
                    profit_factor=m.profit_factor,
                    avg_win=m.avg_win,
                    avg_loss=m.avg_loss,
                    long_count=long_count_out,
                    short_count=short_count_out,
                    # Sprint 30 gamma-BE: PRD 24 metric spec 정합 — 신규 12 필드 전달.
                    avg_holding_hours=m.avg_holding_hours,
                    consecutive_wins_max=m.consecutive_wins_max,
                    consecutive_losses_max=m.consecutive_losses_max,
                    long_win_rate_pct=m.long_win_rate_pct,
                    short_win_rate_pct=m.short_win_rate_pct,
                    monthly_returns=m.monthly_returns,
                    drawdown_duration=m.drawdown_duration,
                    annual_return_pct=m.annual_return_pct,
                    # total_trades 는 PRD parity alias — num_trades override 시
                    # 함께 갱신 (legacy fallback 시 m.total_trades 그대로).
                    total_trades=(
                        num_trades_out
                        if direction_counts is not None and direction_counts[0] > 0
                        else m.total_trades
                    ),
                    avg_trade_pct=m.avg_trade_pct,
                    best_trade_pct=m.best_trade_pct,
                    worst_trade_pct=m.worst_trade_pct,
                    drawdown_curve=m.drawdown_curve,
                    # Sprint 32-D BL-156: MDD 수학 정합 메타.
                    mdd_unit=m.mdd_unit,
                    mdd_exceeds_capital=m.mdd_exceeds_capital,
                    # Sprint 34 BL-175: Buy & Hold curve (OHLCV 첫/끝 close 기반).
                    # 본 spread 누락 시 silent BUG = JSONB 에 저장된 BH curve 가
                    # FE 응답에 0건 → 거짓 trust 회복 실패 (P1-2 R-2 회귀 hotspot).
                    buy_and_hold_curve=m.buy_and_hold_curve,
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
            config=config_out,
            metrics=metrics_out,
            equity_curve=equity_out,
            error=bt.error,
        )


# ---------------------------------------------------------------------------
# Sprint 31 BL-162a — timeframe → pandas offset alias.
# ---------------------------------------------------------------------------


# CreateBacktestRequest 의 6 timeframe Literal 과 정합. v2_adapter 의
# `_FREQ_HOURS_V2` 와 정합 (avg_holding_hours 변환 매핑 한 쌍).
_TIMEFRAME_TO_FREQ: dict[str, str] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


def _timeframe_to_freq(timeframe: str) -> str:
    """timeframe Literal → pandas offset alias. 미매핑 시 '1D' fallback (안전)."""
    return _TIMEFRAME_TO_FREQ.get(timeframe, "1D")


# ---------------------------------------------------------------------------
# Sprint 38 BL-188 v3 — sizing canonical 결정 helper (codex G.0 iter 1+2 fix 반영).
# must-fix 1 (sizing source 단일화) + must-fix 3 (leverage Nx reject) + D2 (manual override).
# ---------------------------------------------------------------------------


_VALID_SIZING_BASIS: frozenset[str] = frozenset(
    {
        "pine_native",
        "live_available_balance_approx_equity",
        "form_equity",
        "fallback_qty1",
    }
)


def _resolve_sizing_canonical(
    request: CreateBacktestRequest,
    strategy: Strategy,
) -> dict[str, Any]:
    """submit 시점 sizing canonical 결정 (Pine > 폼 manual > Live > fallback).

    codex G.0 iter 1 must-fix 1+3 + iter 2 [P1] #1 (D2 결정) 반영. helper 가
    `Backtest.config` JSONB 에 저장될 5 필드 (sizing_source / sizing_basis /
    leverage_basis / live_position_size_pct / default_qty_*) 를 결정.

    Priority chain (D2 manual override 가능):
      1. Pine `strategy(default_qty_type=..., default_qty_value=...)` 명시 → tier 1
      2. request.default_qty_type/value 명시 (사용자 manual override) → tier 2
      3. request.position_size_pct OR strategy.settings.position_size_pct (Live, 1x only) → tier 3
      4. None → fallback (qty=1.0)

    422 reject:
      - Pine partial declaration (type-only / value-only) → PinePartialDeclaration
      - position_size_pct + default_qty_* 동시 명시 → SizingSourceConflict
        (schema validator 가 1차 차단, 본 helper 는 외부 client / 우회 호출 방어)
      - Live mirror 의도 + leverage != 1 → MirrorNotAllowed (BL-186 후 unlock)
    """
    # 1. Pine declaration 추출 + partial reject (codex iter 1 [P1] #5)
    pine_qty_type, pine_qty_value = _extract_default_qty(strategy.pine_source)
    if (pine_qty_type is None) != (pine_qty_value is None):
        raise PinePartialDeclaration(
            detail=(
                f"Pine strategy declaration partial: "
                f"default_qty_type={pine_qty_type!r}, default_qty_value={pine_qty_value!r}. "
                f"둘 다 명시 또는 둘 다 생략 의무 (BL-188 v3)."
            ),
            declared_type=pine_qty_type,
            declared_value=str(pine_qty_value) if pine_qty_value is not None else None,
        )

    # 2. Pine tier 1 (override 0순위)
    if pine_qty_type is not None and pine_qty_value is not None:
        return _canonical_dict(
            source="pine",
            qty_type=pine_qty_type,
            qty_value=pine_qty_value,
            live_pct=None,
            basis="pine_native",
        )

    # 3. Service-level 2차 방어 (codex must-fix 1) — 외부 client / FE 우회 호출 시.
    #    schema validator `_no_double_sizing` 이 1차 차단하지만 helper 도 동일 판정.
    request_form_explicit = (
        request.default_qty_type is not None and request.default_qty_value is not None
    )
    request_live_explicit = request.position_size_pct is not None
    if request_live_explicit and request_form_explicit:
        raise SizingSourceConflict(
            detail=(
                "position_size_pct (Live mirror) 와 default_qty_type/value (manual) "
                "동시 명시 불가. canonical 1개 선택 의무 (BL-188 v3)."
            )
        )

    # 4. Manual override tier 2 (D2 결정 — form > Live)
    if request_form_explicit:
        # mypy 위해 None 안전 cast — 위 조건에서 둘 다 not None 보장.
        assert request.default_qty_type is not None
        assert request.default_qty_value is not None
        return _canonical_dict(
            source="form",
            qty_type=request.default_qty_type,
            qty_value=float(request.default_qty_value),
            live_pct=None,
            basis="form_equity",
        )

    # 5. Live mirror tier 3 (1x equity-basis only)
    live_settings: StrategySettings | None = None
    if strategy.settings is not None:
        live_settings = StrategySettings.model_validate(strategy.settings)

    live_implicit = live_settings is not None and not request_live_explicit
    if request_live_explicit or live_implicit:
        if live_settings is None:
            # request.position_size_pct 명시했으나 strategy.settings 비어있음.
            raise MirrorNotAllowed(
                detail=(
                    "position_size_pct 명시했으나 strategy.settings 가 비어있음. "
                    "Live settings 등록 후 mirror 가능."
                ),
                live_leverage=None,
                live_margin_mode=None,
            )
        if live_settings.leverage != 1:
            # codex must-fix 3 — leverage Nx 시 거짓 mirror 차단 (BL-186 후 unlock).
            raise MirrorNotAllowed(
                detail=(
                    f"Live leverage {live_settings.leverage}x ({live_settings.margin_mode}) "
                    f"와 backtest 1x equity-basis 비대칭 → mirror 불가. "
                    f"BL-186 (풀 leverage/funding/liquidation 모델) 후 unlock."
                ),
                live_leverage=live_settings.leverage,
                live_margin_mode=live_settings.margin_mode,
            )
        # live mirror 1x — request 우선, 없으면 strategy.settings 값 사용.
        if request.position_size_pct is not None:
            live_pct_resolved = float(request.position_size_pct)
        else:
            live_pct_resolved = float(live_settings.position_size_pct)
        return _canonical_dict(
            source="live",
            qty_type=None,
            qty_value=None,
            live_pct=live_pct_resolved,
            basis="live_available_balance_approx_equity",
        )

    # 6. Fallback (qty=1.0 — pre-BL-185 호환)
    return _canonical_dict(
        source="fallback",
        qty_type=None,
        qty_value=None,
        live_pct=None,
        basis="fallback_qty1",
    )


def _canonical_dict(
    *,
    source: str,
    qty_type: str | None,
    qty_value: float | None,
    live_pct: float | None,
    basis: str,
) -> dict[str, Any]:
    """sizing canonical 결과 dict 빌더 (BacktestConfig 5 필드 + default_qty_* 호환).

    Sprint 38 = leverage_basis 항상 1.0 (Nx mirror reject. BL-186 후 unlock).
    """
    return {
        "default_qty_type": qty_type,
        "default_qty_value": qty_value,
        "live_position_size_pct": live_pct,
        "sizing_source": source,
        "sizing_basis": basis,
        "leverage_basis": 1.0,
    }


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
