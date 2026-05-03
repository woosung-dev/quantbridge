"""Sprint 26 — Live Signal Auto-Trading 의 evaluate + dispatch Celery tasks.

두 task 분리 (codex G.0 P1 #3 transactional outbox):

1. `evaluate_live_signals_task` (Beat 1분 fire) — interval 별 due session 평가:
   - RedisLock contention 차단 (P1 #4 ttl_ms=60_000 + heartbeat extend 20s)
   - try_claim_bar winner-only (P2 #3) — 같은 bar 두 번 평가 race 방어
   - CCXT fetch_ohlcv(limit_bars=300) closed-bar (P1 #6)
   - run_live (warmup replay, Option B) → LiveSignalEvent INSERT (status=pending)
   - state upsert + session UPDATE + commit 단일 트랜잭션 (P1 #3 outbox)
   - 신규 INSERT 된 event 만 dispatch task apply_async

2. `dispatch_live_signal_event_task` (apply_async 받음) — pending event 1건:
   - sessions_port=_StrategySessionsAdapter 의무 주입 (P1 #5)
   - idempotency_key with sequence_no (P2 #5)
   - OrderService.execute → mark_dispatched / mark_failed
   - max_retries=3, default_retry_delay=15s

Sprint 18 BL-080 prefork-safe: 모든 task 가 `run_in_worker_loop` (asyncio.run 금지),
per-call `create_worker_engine_and_sm()` + `await engine.dispose()` finally.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from celery import shared_task
from pydantic import ValidationError

from src.common.metrics import (
    qb_live_signal_dispatch_total,
    qb_live_signal_eval_duration_seconds,
    qb_live_signal_evaluated_total,
    qb_live_signal_outbox_pending_gauge,
    qb_live_signal_skipped_total,
)
from src.common.redlock import RedisLock
from src.core.config import settings
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.exceptions import (
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    NotionalExceeded,
    TradingSessionClosed,
)
from src.trading.models import (
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ohlcv_rows_to_dataframe(rows: list[list[Any]]) -> Any:
    """CCXT raw OHLCV [[ts_ms, o, h, l, c, v], ...] → DataFrame (timestamp column).

    `run_live` 가 마지막 bar timestamp 추출 시 'timestamp' 컬럼 우선 사용.
    Decimal 변환은 run_historical 내부에서 처리.
    """
    import pandas as pd

    df = pd.DataFrame(rows, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    return df.drop(columns=["timestamp_ms"])


def _build_idempotency_key(
    *, session_id: UUID, bar_time: datetime, sequence_no: int, action: str, trade_id: str
) -> str:
    """Sprint 26 codex G.0 P2 #5 — sequence_no 포함 idempotency_key.

    같은 bar 안 entry+close 동시 발생 시 sequence_no 가 두 event 를 분리하여
    OrderService 가 별개 Order INSERT 보장.
    """
    return f"live:{session_id}:{bar_time.isoformat()}:{sequence_no}:{action}:{trade_id}"


def _signal_to_order_side(action: str, direction: str) -> OrderSide:
    """Pine signal (action, direction) → CCXT OrderSide.

    entry+long  → buy   (open long)
    entry+short → sell  (open short)
    close+long  → sell  (close long position)
    close+short → buy   (close short position)
    """
    if action == "entry":
        return OrderSide.buy if direction == "long" else OrderSide.sell
    if action == "close":
        return OrderSide.sell if direction == "long" else OrderSide.buy
    raise ValueError(f"Unsupported live-signal action: {action!r}")


async def _heartbeat_extend(lock: RedisLock, *, period_s: float, ttl_ms: int) -> None:
    """RedisLock heartbeat — TTL 만료 전 token CAS 로 PEXPIRE.

    codex G.0 P1 #4 fix: ttl_ms=60_000 + 20s 마다 heartbeat. evaluate task 가 60s
    이상 걸려도 lock 안 풀림. 호출자가 finally 에서 task.cancel() 의무.
    extend 실패 (token mismatch) 시 즉시 종료 — 다른 worker 가 lock 빼앗은 상황.
    """
    try:
        while True:
            await asyncio.sleep(period_s)
            ok = await lock.extend(ttl_ms)
            if not ok:
                logger.warning(
                    "live_signal_heartbeat_extend_failed",
                    extra={"key": getattr(lock, "_key", None)},
                )
                return
    except asyncio.CancelledError:
        return


def create_worker_engine_and_sm() -> tuple[Any, Any]:
    """Sprint 18 BL-080 — per-call engine + sessionmaker (test 가 monkeypatch).

    `funding.py` 와 동일 패턴 — 매 task 호출 시 새 engine 생성 + finally dispose.
    `_WORKER_LOOP` 영속 loop 와 함께 사용 시 stale loop 문제 없음.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


# ---------------------------------------------------------------------------
# Task #1: evaluate_live_signals_task (Beat 1분 fire)
# ---------------------------------------------------------------------------


@shared_task(name="live_signal.evaluate_all", max_retries=0)  # type: ignore[untyped-decorator]
def evaluate_live_signals_task() -> dict[str, Any]:
    """Sprint 26 — 1분 Beat fire. interval 별 due session 평가.

    Beat schedule entry: `evaluate-live-signals` (60s schedule, expires=50).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_evaluate_all())


async def _async_evaluate_all() -> dict[str, Any]:
    """due session list → 각 session 별 _evaluate_session_inner 순차 실행.

    sequential 처리: 5건 quota cap 안에서 충분 — 동시성 늘리려면 asyncio.gather
    가능하나 asyncpg pool / Redis lock pool 소모 증가하여 보수적 채택.
    """
    from src.trading.repository import LiveSignalEventRepository, LiveSignalSessionRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalSessionRepository(session)
            due_sessions = list(await repo.list_active_due(now=datetime.now(UTC)))
            event_repo = LiveSignalEventRepository(session)
            pending = await event_repo.list_pending(limit=10_000)
            qb_live_signal_outbox_pending_gauge.set(len(pending))

        if not due_sessions:
            return {"due_count": 0, "evaluated": 0}

        results: list[dict[str, Any]] = []
        for sess in due_sessions:
            # Sprint 26 Phase D fix — interval/status 가 String 컬럼이라 SQLAlchemy 가
            # raw str 반환. StrEnum cast 가 자동 안 되므로 str() 으로 정규화.
            res = await _async_evaluate_session(sess.id, str(sess.interval))
            results.append({"session_id": str(sess.id), **res})

        return {"due_count": len(due_sessions), "evaluated": len(results), "results": results}
    finally:
        await engine.dispose()


async def _async_evaluate_session(session_id: UUID, interval_value: str) -> dict[str, Any]:
    """단일 session 평가 — RedisLock + heartbeat + per-call engine.

    interval_value 는 metric label cardinality cap 위해 caller 에서 str 로 전달.
    """
    started = time.monotonic()
    lock = RedisLock(f"live:eval:{session_id}", ttl_ms=60_000)
    heartbeat: asyncio.Task[None] | None = None
    try:
        async with lock as acquired:
            if not acquired:
                qb_live_signal_skipped_total.labels(reason="contention").inc()
                return {"skipped": "contention"}

            heartbeat = asyncio.create_task(_heartbeat_extend(lock, period_s=20.0, ttl_ms=60_000))
            try:
                outcome = await _evaluate_session_inner(session_id, interval_value)
            finally:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat
            return outcome
    finally:
        qb_live_signal_eval_duration_seconds.labels(interval=interval_value).observe(
            time.monotonic() - started
        )


async def _evaluate_session_inner(session_id: UUID, interval_value: str) -> dict[str, Any]:
    """Lock 안에서 실행되는 핵심 평가 로직.

    Flow:
    1. session fetch + active 검증
    2. strategy + StrategySettings.model_validate (P2 #4)
    3. account + Bybit Demo 강제 (P2 #1)
    4. CCXTProvider.fetch_ohlcv(limit_bars=300, ...) (P1 #6)
    5. last_bar_time 비교 → no new bar skip
    6. try_claim_bar winner-only (P2 #3)
    7. run_live (warmup replay, Option B)
    8. transactional outbox: events INSERT + state upsert + session.last_evaluated commit (P1 #3)
    9. 신규 INSERT 된 event 만 dispatch task apply_async
    """
    from src.strategy.pine_v2.event_loop import run_live
    from src.strategy.repository import StrategyRepository
    from src.tasks.celery_app import get_ccxt_provider_for_worker
    from src.trading.repository import (
        ExchangeAccountRepository,
        LiveSignalEventRepository,
        LiveSignalSessionRepository,
    )

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            sess_repo = LiveSignalSessionRepository(session)
            event_repo = LiveSignalEventRepository(session)
            account_repo = ExchangeAccountRepository(session)
            strategy_repo = StrategyRepository(session)

            # 1. session fetch
            sess = await sess_repo.get_by_id(session_id)
            if sess is None or not sess.is_active:
                qb_live_signal_skipped_total.labels(reason="session_inactive").inc()
                return {"skipped": "session_inactive"}

            # 2. strategy + settings validate (P2 #4)
            strategy = await strategy_repo.find_by_id_and_owner(sess.strategy_id, sess.user_id)
            if strategy is None:
                qb_live_signal_skipped_total.labels(reason="strategy_missing").inc()
                return {"skipped": "strategy_missing"}
            try:
                parsed_settings: StrategySettings | None = validate_strategy_settings(
                    strategy.settings
                )
            except ValidationError as exc:
                qb_live_signal_skipped_total.labels(reason="invalid_settings").inc()
                logger.warning(
                    "live_signal_invalid_settings",
                    extra={"session_id": str(sess.id), "error": str(exc)},
                )
                return {"skipped": "invalid_settings"}
            if parsed_settings is None:
                qb_live_signal_skipped_total.labels(reason="invalid_settings").inc()
                return {"skipped": "settings_unset"}

            # 3. account + Bybit Demo 강제 (P2 #1)
            account = await account_repo.get_by_id(sess.exchange_account_id)
            if (
                account is None
                or account.exchange != ExchangeName.bybit
                or account.mode != ExchangeMode.demo
            ):
                qb_live_signal_skipped_total.labels(reason="non_demo_account").inc()
                return {"skipped": "non_demo_account"}

            # 4. CCXT fetch_ohlcv (P1 #6 closed-bar)
            provider = get_ccxt_provider_for_worker()
            ohlcv_rows = await provider.fetch_ohlcv(sess.symbol, str(sess.interval), limit_bars=300)
            if not ohlcv_rows:
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="no_new_bar"
                ).inc()
                return {"skipped": "empty_ohlcv"}

            # 5. last_bar_time → no new bar skip
            last_bar_ms = int(ohlcv_rows[-1][0])
            last_bar_time = datetime.fromtimestamp(last_bar_ms / 1000, tz=UTC)
            if (
                sess.last_evaluated_bar_time is not None
                and last_bar_time <= sess.last_evaluated_bar_time
            ):
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="no_new_bar"
                ).inc()
                return {"skipped": "no_new_bar"}

            # 6. try_claim_bar winner-only (P2 #3)
            won = await sess_repo.try_claim_bar(sess.id, last_bar_time, uuid4())
            if not won:
                # 다른 worker 가 이미 같은 bar claim 한 상태 — UPDATE no-op rollback
                await session.rollback()
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="claim_lost"
                ).inc()
                return {"skipped": "claim_lost"}

            # 7. run_live (warmup replay, Option B)
            df = _ohlcv_rows_to_dataframe(ohlcv_rows)
            result = run_live(strategy.pine_source, df)

            # 8. transactional outbox — events INSERT + state upsert + commit (P1 #3)
            signals_payload: list[dict[str, object]] = [
                {
                    "action": s.action,
                    "direction": s.direction,
                    "trade_id": s.trade_id,
                    "qty": s.qty,
                    "sequence_no": s.sequence_no,
                    "comment": s.comment,
                }
                for s in result.signals
            ]
            existing_events = await event_repo.list_by_session(sess.id, limit=1000)
            existing_keys = {
                (e.bar_time, e.sequence_no, e.action, e.trade_id) for e in existing_events
            }
            inserted_or_existing = await event_repo.insert_pending_events(
                session_id=sess.id, bar_time=last_bar_time, signals=signals_payload
            )
            new_events = [
                e
                for e in inserted_or_existing
                if (e.bar_time, e.sequence_no, e.action, e.trade_id) not in existing_keys
            ]

            # state upsert (last_open_trades_snapshot 은 strategy_state_report 의 open_trades 발췌)
            open_trades_snapshot = (
                result.strategy_state_report.get("open_trades", {})
                if isinstance(result.strategy_state_report, dict)
                else {}
            )
            await sess_repo.upsert_state(
                session_id=sess.id,
                last_strategy_state_report=result.strategy_state_report,
                last_open_trades_snapshot=open_trades_snapshot
                if isinstance(open_trades_snapshot, dict)
                else {},
                total_closed_trades=result.total_closed_trades,
                total_realized_pnl=result.total_realized_pnl,
            )

            # LESSON-019 — claim UPDATE + events INSERT + state upsert 단일 commit
            await sess_repo.commit()

        # 9. dispatch task enqueue — outbox commit 후 (visibility race 방지)
        for ev in new_events:
            if ev.status == LiveSignalEventStatus.pending:
                dispatch_live_signal_event_task.apply_async(
                    args=[str(ev.id)],
                    expires=300,
                )

        qb_live_signal_evaluated_total.labels(interval=interval_value, outcome="success").inc()
        return {
            "evaluated": True,
            "events_inserted": len(new_events),
            "last_bar_time": last_bar_time.isoformat(),
        }
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task #2: dispatch_live_signal_event_task (per event)
# ---------------------------------------------------------------------------


@shared_task(  # type: ignore[untyped-decorator]
    name="live_signal.dispatch_event",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def dispatch_live_signal_event_task(self: Any, event_id: str) -> dict[str, Any]:
    """Sprint 26 — 단일 LiveSignalEvent → OrderService.execute.

    eval task 가 commit 후 apply_async 로 enqueue. broker 발주 후 mark_dispatched
    / mark_failed. 일시 장애 시 max_retries=3 (15s/30s/45s exponential).

    codex G.2 P1 #10 fix — retry 소진 시 event 가 status=pending 으로 영구 잔류
    하지 않도록 max_retries 도달 시 mark_failed(error='max_retries_exhausted')
    + commit. `dispatch_pending_live_signal_events_task` Beat 가 별도로 잔여 pending
    회수.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    try:
        return run_in_worker_loop(_async_dispatch_event(UUID(event_id)))
    except (KillSwitchActive, NotionalExceeded, LeverageCapExceeded, TradingSessionClosed):
        # 재시도해도 풀리지 않는 deterministic reject — _async_dispatch_event 가 이미
        # mark_failed + commit 처리 후 raise 했으므로 retry 안 함.
        return {"failed": "deterministic_reject"}
    except Exception as exc:  # BLE001 — 재시도 가능 일시 장애
        # codex G.2 P1 #10 — retry 소진 시 event 영구 stuck 차단
        retries_so_far = getattr(self.request, "retries", 0) or 0
        if retries_so_far >= getattr(self, "max_retries", 3):
            logger.exception(
                "live_signal_dispatch_max_retries_exhausted_marking_failed",
                extra={"event_id": event_id, "retries": retries_so_far},
            )
            try:
                run_in_worker_loop(
                    _async_mark_event_failed(UUID(event_id), error="max_retries_exhausted")
                )
            except Exception:
                logger.exception(
                    "live_signal_dispatch_mark_failed_on_exhaustion_failed",
                    extra={"event_id": event_id},
                )
            qb_live_signal_dispatch_total.labels(
                action="unknown", outcome="max_retries_exhausted"
            ).inc()
            return {"failed": "max_retries_exhausted"}
        logger.exception("live_signal_dispatch_failed_will_retry", extra={"event_id": event_id})
        raise self.retry(exc=exc) from exc


async def _async_mark_event_failed(event_id: UUID, *, error: str) -> None:
    """codex G.2 P1 #10 helper — retry 소진 시 mark_failed + commit (per-call engine)."""
    from src.trading.repository import LiveSignalEventRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalEventRepository(session)
            await repo.mark_failed(event_id, error=error)
            await repo.commit()
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task #3: dispatch_pending_live_signal_events_task (Beat 5min — outbox 회수)
# ---------------------------------------------------------------------------


@shared_task(  # type: ignore[untyped-decorator]
    name="live_signal.dispatch_pending",
    max_retries=0,
)
def dispatch_pending_live_signal_events_task() -> dict[str, Any]:
    """Sprint 26 — codex G.2 P1 #10 fix — outbox pending 회수 Beat.

    5분 주기 fire. status=pending 인 event 를 list_pending(limit=50) 으로 조회하여
    `dispatch_live_signal_event_task.apply_async` 재발행. eval task 의 dispatch enqueue
    가 worker crash / Redis broker 일시 장애로 유실됐을 때 회수 안전망.

    중복 fire 위험 (같은 event 가 in-flight + pending 시 두 번 발행) 은 dispatch task
    내부의 `if event.status != pending: skipped='already_terminal'` 가드 로 차단.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_dispatch_pending())


async def _async_dispatch_pending() -> dict[str, Any]:
    from src.trading.repository import LiveSignalEventRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalEventRepository(session)
            pending = await repo.list_pending(limit=50)
        qb_live_signal_outbox_pending_gauge.set(len(pending))
        for ev in pending:
            dispatch_live_signal_event_task.apply_async(
                args=[str(ev.id)],
                expires=300,
            )
        return {"reenqueued": len(pending)}
    finally:
        await engine.dispose()


async def _async_dispatch_event(event_id: UUID) -> dict[str, Any]:
    """Per-call engine + dispose. OrderService 조립 + execute + mark_dispatched/failed.

    중요 의무:
    - sessions_port=_StrategySessionsAdapter 주입 (P1 #5 — bypass 차단)
    - idempotency_key with sequence_no (P2 #5 — 같은 bar entry+close 분리)
    - mark_failed 도 commit 의무 (LESSON-019)
    """
    from src.strategy.repository import StrategyRepository
    from src.trading.dependencies import _CeleryOrderDispatcher, _StrategySessionsAdapter
    from src.trading.encryption import EncryptionService
    from src.trading.kill_switch import (
        CumulativeLossEvaluator,
        DailyLossEvaluator,
        KillSwitchEvaluator,
        KillSwitchService,
    )
    from src.trading.providers import BybitFuturesProvider
    from src.trading.repository import (
        ExchangeAccountRepository,
        KillSwitchEventRepository,
        LiveSignalEventRepository,
        LiveSignalSessionRepository,
        OrderRepository,
    )
    from src.trading.schemas import OrderRequest
    from src.trading.service import ExchangeAccountService, OrderService

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            event_repo = LiveSignalEventRepository(session)
            event = await event_repo.get_by_id(event_id)
            if event is None:
                logger.warning(
                    "live_signal_dispatch_missing_event", extra={"event_id": str(event_id)}
                )
                return {"skipped": "missing"}
            if event.status != LiveSignalEventStatus.pending:
                # 이미 dispatched / failed — duplicate apply_async 방어
                return {"skipped": "already_terminal", "status": str(event.status)}

            sess_repo = LiveSignalSessionRepository(session)
            sess = await sess_repo.get_by_id(event.session_id)
            if sess is None or not sess.is_active:
                await event_repo.mark_failed(event.id, error="session_inactive")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="session_inactive"
                ).inc()
                return {"failed": "session_inactive"}

            # strategy + settings (P2 #4)
            strategy_repo = StrategyRepository(session)
            strategy = await strategy_repo.find_by_id_and_owner(sess.strategy_id, sess.user_id)
            if strategy is None:
                await event_repo.mark_failed(event.id, error="strategy_missing")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="strategy_missing"
                ).inc()
                return {"failed": "strategy_missing"}
            try:
                parsed_settings = validate_strategy_settings(strategy.settings)
            except ValidationError as exc:
                await event_repo.mark_failed(event.id, error=f"invalid_settings: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="invalid_settings"
                ).inc()
                return {"failed": "invalid_settings"}
            if parsed_settings is None:
                await event_repo.mark_failed(event.id, error="settings_unset")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="settings_unset"
                ).inc()
                return {"failed": "settings_unset"}

            # OrderService 조립 (P1 #5: sessions_port 의무)
            order_repo = OrderRepository(session)
            account_repo = ExchangeAccountRepository(session)
            kse_repo = KillSwitchEventRepository(session)
            crypto = EncryptionService(settings.trading_encryption_keys)
            bybit_provider = BybitFuturesProvider()
            exchange_svc = ExchangeAccountService(
                repo=account_repo,
                crypto=crypto,
                bybit_futures_provider=bybit_provider,
            )
            evaluators: list[KillSwitchEvaluator] = [
                CumulativeLossEvaluator(
                    order_repo,
                    threshold_percent=settings.kill_switch_cumulative_loss_percent,
                    capital_base=settings.kill_switch_capital_base_usd,
                    balance_provider=exchange_svc,
                ),
                DailyLossEvaluator(
                    order_repo,
                    threshold_usd=settings.kill_switch_daily_loss_usd,
                ),
            ]
            ks_svc = KillSwitchService(evaluators=evaluators, events_repo=kse_repo)

            order_svc = OrderService(
                session=session,
                repo=order_repo,
                dispatcher=_CeleryOrderDispatcher(),
                kill_switch=ks_svc,
                sessions_port=_StrategySessionsAdapter(session),  # P1 #5 fix
                exchange_service=exchange_svc,
            )

            # OrderRequest 조립
            req = OrderRequest(
                strategy_id=sess.strategy_id,
                exchange_account_id=sess.exchange_account_id,
                symbol=sess.symbol,
                side=_signal_to_order_side(event.action, event.direction),
                type=OrderType.market,
                quantity=Decimal(str(event.qty)),
                price=None,  # market order
                leverage=parsed_settings.leverage,
                margin_mode=parsed_settings.margin_mode,
            )
            idempotency_key = _build_idempotency_key(
                session_id=sess.id,
                bar_time=event.bar_time,
                sequence_no=event.sequence_no,
                action=event.action,
                trade_id=event.trade_id,
            )

            try:
                response, _replayed = await order_svc.execute(
                    req, idempotency_key=idempotency_key, body_hash=None
                )
            except KillSwitchActive:
                await event_repo.mark_failed(event.id, error="kill_switched")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="kill_switched"
                ).inc()
                raise
            except (NotionalExceeded, LeverageCapExceeded, TradingSessionClosed) as exc:
                await event_repo.mark_failed(event.id, error=str(exc))
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                raise
            except IdempotencyConflict as exc:
                # 같은 idempotency_key 가 다른 payload — 복구 불가, mark_failed
                await event_repo.mark_failed(event.id, error=f"idempotency_conflict: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="idempotency_conflict"
                ).inc()
                return {"failed": "idempotency_conflict"}

            # OrderService.execute 가 self._session.commit() 내부 호출 — Order INSERT 영구화 완료.
            await event_repo.mark_dispatched(event.id, order_id=response.id)
            await event_repo.commit()
            qb_live_signal_dispatch_total.labels(action=event.action, outcome="dispatched").inc()
            return {"dispatched": str(response.id), "replayed": _replayed}
    finally:
        await engine.dispose()
