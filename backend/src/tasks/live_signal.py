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
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from celery import shared_task
from pydantic import ValidationError

from src.common.alert import track_pending_alert
from src.common.metrics import (
    qb_live_signal_dispatch_total,
    qb_live_signal_divergence_total,
    qb_live_signal_eval_duration_seconds,
    qb_live_signal_evaluated_total,
    qb_live_signal_outbox_pending_gauge,
    qb_live_signal_skipped_total,
)
from src.common.redlock import RedisLock
from src.core.config import settings
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.alerting import send_rule_alert
from src.trading.exceptions import (
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    MinNotionalNotMet,
    NotionalExceeded,
    TradingSessionClosed,
)
from src.trading.models import (
    AlertChannel,
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    OrderSide,
    OrderType,
)
from src.trading.realtime_publisher import publish_realtime

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


def _sanitize_for_jsonb(value: Any) -> Any:
    """BL-123 — PostgreSQL JSONB strict 호환 위해 NaN / Infinity → None.

    `run_historical` 의 indicator (ATR/EMA 등) 가 warmup 중 NaN 반환 가능. dict.to_report()
    가 이걸 dict 안에 그대로 두면 `INSERT ... json_value` 시 PG 가
    `InvalidTextRepresentationError: invalid input syntax for type json: Token "NaN"`
    raise. recursive sanitize 로 모든 NaN/Infinity 를 None 으로 정규화.

    Decimal/datetime 등 다른 nonstandard 타입은 별도 처리 (이미 schema 가 str 또는 numeric).
    """
    import math

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _sanitize_for_jsonb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_jsonb(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_for_jsonb(v) for v in value]
    return value


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


def _action_is_reduce_only(action: str) -> bool:
    """Wave 1 C3 — close 주문만 reduce-only.

    close 의 반대편 시장청산 주문이 reduceOnly 없으면 잔여 포지션을 넘겨 over-fill /
    포지션 반전 위험. entry 는 신규 포지션 오픈이므로 reduce_only=False.
    """
    return action == "close"


def _classify_live_divergence(msg: str) -> str:
    """BL-362 — interpreter PineRuntimeError 메시지 → bounded category (≤5 runtime 값).

    W1 `_classify_trailing_failure`(trading.py) 미러: raw 는 절대 metric label 에 안 싣고
    category enum 만. case-insensitive substring ladder — interpreter.py 의 모든 raise-site
    메시지 prefix 대조. 미분류는 unexpected.
    """
    low = msg.lower()
    if "undefined name" in low:
        return "undefined_name"
    if "attribute access not supported" in low:
        return "unsupported_attr"
    if (
        "not supported in current scope" in low
        or "function not supported" in low
        or "method not supported" in low
    ):
        return "unsupported_call"
    if low.startswith("unsupported "):
        return "unsupported_node"
    if "not supported" in low:
        # 일반 구조적 미지원 (Subscript on non-Name / var·varip tuple destructuring 등).
        return "unsupported_node"
    return "unexpected"


async def _alert_live_divergence(
    *,
    session_id: UUID,
    stage: str,
    category: str,
    raw_msg: str,
    error_count: int,
    last_error_bar: int,
) -> None:
    """BL-362 — 발산 감지 → 세션 자동 비활성화 critical alert (무신호 차단 고지).

    raw_msg 는 사용자 본인 Pine 심볼/구조 메시지(거래소 시크릿 아님 — interpreter raise-site
    전수조사로 시장데이터·문자열 리터럴 미포함 검증) → actionable 차원에서 포함하되 [:200]
    truncate(defense-in-depth). 원본 전체·stack 은 호출부 logger.error 가 기록.

    G2 P2#3 — kill_switch `_send_alert_safely` 미러: send 예외는 swallow + log (alert 실패가
    fire-and-forget task 를 unretrieved-exception 으로 남기거나 흐름 깨면 안 됨).
    """
    try:
        await send_rule_alert(
            settings,
            channel=AlertChannel.both,
            title="Live signal divergence — 세션 자동 비활성화 (무신호 차단)",
            message=(
                f"pine_v2 coverage↔interpreter 발산({stage}/{category}) 감지 — 세션을 "
                "비활성화했습니다(오신호 dispatch 차단, 고정 SL/포지션은 거래소측 유지). "
                f"전략 수정 후 재활성화 필요. detail: {raw_msg[:200]}"
            ),
            context={
                "session_id": str(session_id)[:8],
                "stage": stage,
                "category": category,
                "error_count": str(error_count),
                "last_error_bar": str(last_error_bar),
            },
        )
    except Exception as exc:
        logger.warning(
            "live_signal_divergence_alert_failed",
            extra={"session_id": str(session_id)[:8], "error": str(exc)},
        )


def _fire_divergence_alert(
    *,
    session_id: UUID,
    stage: str,
    category: str,
    raw_msg: str,
    error_count: int,
    last_error_bar: int,
) -> None:
    """fire-and-forget alert. `_evaluate_session_inner` 는 이미 persistent `_WORKER_LOOP`
    안이므로 `create_task` + `track_pending_alert` (kill_switch.py 패턴).
    `run_in_worker_loop` 금지 (nested ban §9.4).
    """
    task = asyncio.create_task(
        _alert_live_divergence(
            session_id=session_id,
            stage=stage,
            category=category,
            raw_msg=raw_msg,
            error_count=error_count,
            last_error_bar=last_error_bar,
        )
    )
    track_pending_alert(task)


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


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

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
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

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
            # G3 — per-session 격리: 한 세션의 uncaught 오류(예: analyze_coverage 같은
            # pre-claim 호출)가 batch 전체를 abort 하여 이후 세션을 starve 시키지 않도록 방어.
            try:
                res = await _async_evaluate_session(sess.id, str(sess.interval))
            except Exception:
                logger.exception(
                    "live_signal_eval_session_error", extra={"session_id": str(sess.id)}
                )
                qb_live_signal_skipped_total.labels(reason="eval_error").inc()
                res = {"error": "eval_error"}
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
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

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

            # 3.5 BL-362 — coverage preflight (money-path fail-closed). backtest/service.py 와
            # 동일 게이트: 미지원 builtin(is_runnable=False) 또는 degraded(heikinashi/
            # request.security/timeframe.period — graceful 실행이나 결과 divergence) 감지 시
            # 세션 자동 비활성화. live 엔 allow_degraded_pine 동의 플래그 없음 → 하드 차단.
            # account/demo check 뒤에 배치 — non-demo 세션은 비활성화 아닌 skip 유지 (G1 P1#2).
            cov = analyze_coverage(strategy.pine_source)
            preflight_cat: str | None = None
            preflight_symbols: tuple[str, ...] = ()
            if not cov.is_runnable:
                preflight_cat, preflight_symbols = "coverage_unrunnable", cov.all_unsupported
            elif cov.has_degraded:
                preflight_cat, preflight_symbols = "degraded_unconsented", cov.degraded_calls
            if preflight_cat is not None:
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:  # winner-only dedupe (동시 worker 2nd UPDATE rowcount=0)
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    qb_live_signal_divergence_total.labels(
                        stage="preflight", category=preflight_cat
                    ).inc()
                    qb_live_signal_skipped_total.labels(reason=preflight_cat).inc()
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="preflight",
                        category=preflight_cat,
                        raw_msg=", ".join(preflight_symbols)[:200],
                        error_count=0,
                        last_error_bar=-1,
                    )
                    logger.error(
                        "live_signal_preflight_blocked",
                        extra={
                            "session_id": str(sess.id),
                            "category": preflight_cat,
                            "symbols": list(preflight_symbols),
                        },
                    )
                return {"deactivated": preflight_cat}

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
            try:
                result = run_live(strategy.pine_source, df)
            except Exception as exc:
                # G2 — run_live 가 result.errors 로 surface 안 되는 예외를 raise 하는 경로:
                # parse SyntaxError / 미구현 na-semantics 의 raw ZeroDivisionError(`x/0`) /
                # math domain ValueError(`math.sqrt(-1)`) 등 (strict=False 의 except PineRuntimeError
                # 가 안 잡음). 미처리 시 claim rollback + 세션 active 유지 → 매 tick crash-loop.
                # → 동일 fail-closed: 세션 비활성화 + metric + alert. (interpreter na-semantics
                # 자체 수정은 BL-374 로 분리.)
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    qb_live_signal_divergence_total.labels(
                        stage="runtime", category="run_live_error"
                    ).inc()
                    qb_live_signal_evaluated_total.labels(
                        interval=interval_value, outcome="divergence_blocked"
                    ).inc()
                    # G3 NIT#4 — raw_msg 는 임의 예외 str (구조적 audit 범위 밖). Telegram까지
                    # fan-out하므로 호출부에서 예외 클래스명만 전달한다. 전체 원문은 아래 logger에만 남긴다.
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="runtime",
                        category="run_live_error",
                        raw_msg=type(exc).__name__,
                        error_count=1,
                        last_error_bar=-1,
                    )
                    logger.exception(
                        "live_signal_run_live_crash",
                        extra={"session_id": str(sess.id), "error_type": type(exc).__name__},
                    )
                return {"deactivated": "run_live_error"}

            # 7.5 BL-362 — runtime divergence safety net (money-path fail-closed).
            # run_historical(strict=False) 가 PineRuntimeError 를 삼키고 계속 → state corruption
            # 가능 → 오신호. errors 비어있지 않으면(어느 bar든) 세션 비활성화 + events INSERT/
            # dispatch 차단. claim(UPDATE) + deactivate(UPDATE) 단일 commit (events 안 넣음).
            if result.errors:
                # errors[-1] = 가장 최근(최고 bar) runtime error. block-on-any 라 warmup
                # corruption 도 포착(마지막 bar 만 필터링하지 않음).
                category = _classify_live_divergence(result.errors[-1][1])
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:  # winner-only dedupe
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    qb_live_signal_divergence_total.labels(stage="runtime", category=category).inc()
                    qb_live_signal_evaluated_total.labels(
                        interval=interval_value, outcome="divergence_blocked"
                    ).inc()
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="runtime",
                        category=category,
                        raw_msg=result.errors[-1][1],
                        error_count=len(result.errors),
                        last_error_bar=result.errors[-1][0],
                    )
                    logger.error(
                        "live_signal_runtime_divergence",
                        extra={
                            "session_id": str(sess.id),
                            "category": category,
                            "error_count": len(result.errors),
                            "errors": result.errors[:10],
                        },
                    )
                return {"deactivated": "runtime_divergence", "category": category}

            # 8. transactional outbox — events INSERT + state upsert + commit (P1 #3)
            signals_payload: list[dict[str, object]] = [
                {
                    "action": s.action,
                    "direction": s.direction,
                    "trade_id": s.trade_id,
                    "qty": s.qty,
                    "sequence_no": s.sequence_no,
                    "comment": s.comment,
                    # MP-1 — close signal 의 청산 realized PnL (entry 는 None).
                    "realized_pnl": s.realized_pnl,
                    # Phase 3 — entry signal 의 exit 레벨 (bracket placement + trailing). close 는 None.
                    "take_profit": s.take_profit,
                    "stop_loss": s.stop_loss,
                    "trailing_stop": s.trailing_stop,
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

            # BL-123 — JSONB 호환 sanitize (NaN/Infinity → None). run_historical 의
            # warmup 중 ATR/EMA 등이 NaN 반환 가능 → PG strict JSONB reject.
            sanitized_report = _sanitize_for_jsonb(result.strategy_state_report)
            # Sprint 28 Slice 3 (BL-140b) — equity_curve append.
            # 신규 closed trade 발생 시점 = total_realized_pnl 변동. delta 계산 후
            # equity_calculator.append_equity_point 호출. 변동 없으면 curve 갱신 X.
            # defensive: non-Decimal mock value 도 graceful (None 반환 = skip).
            from src.trading.equity_calculator import append_equity_point

            new_equity_curve: list[dict[str, object]] | None = None
            try:
                existing_state = await sess_repo.get_state(sess.id)
                prev_total_pnl = (
                    Decimal(str(existing_state.total_realized_pnl))
                    if existing_state is not None
                    else Decimal("0")
                )
                curr_total_pnl = Decimal(str(result.total_realized_pnl))
                pnl_delta = curr_total_pnl - prev_total_pnl

                if pnl_delta != Decimal("0"):
                    # 영구 규칙: Decimal-first 합산 (calculator 안에서 처리)
                    prev_curve = (
                        existing_state.equity_curve
                        if existing_state is not None and existing_state.equity_curve is not None
                        else []
                    )
                    new_curve = append_equity_point(
                        prev_curve,  # type: ignore[arg-type]
                        timestamp_ms=int(last_bar_time.timestamp() * 1000),
                        pnl_delta=pnl_delta,
                    )
                    # TypedDict → dict 호환 cast (runtime 동일 구조)
                    new_equity_curve = [dict(p) for p in new_curve]
            except (InvalidOperation, ValueError, TypeError) as exc:
                # Decimal 변환 실패 (mock value / corrupt DB 등) — equity_curve skip + log.
                # KillSwitch eval 자체는 절대 fail 금지 (BL-004 영구 규칙 정합).
                logger.warning("equity_curve_skip session=%s err=%s", sess.id, exc)

            await sess_repo.upsert_state(
                session_id=sess.id,
                last_strategy_state_report=sanitized_report
                if isinstance(sanitized_report, dict)
                else {},
                total_closed_trades=result.total_closed_trades,
                total_realized_pnl=result.total_realized_pnl,
                equity_curve=new_equity_curve,
            )

            # LESSON-019 — claim UPDATE + events INSERT + state upsert 단일 commit
            await sess_repo.commit()
            await publish_realtime(
                str(sess.user_id), "session_state", {"session_id": str(sess.id)}
            )

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
    except (
        KillSwitchActive,
        NotionalExceeded,
        LeverageCapExceeded,
        MinNotionalNotMet,
        TradingSessionClosed,
    ):
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
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository

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
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository

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
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.account_service import ExchangeAccountService
    from src.trading.services.order_service import OrderService

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

            # Phase 3 — 트레일링 가드 (codex gate BLOCKER): 트레일링이 의도된 stop 인데
            #   라이브 placement 미지원(set-trading-stop 엔드포인트라 fill 후 follow-on 필요)
            #   + 폴백 SL 부재 → 무방비 포지션. 안전 우선으로 진입 거부 (정직 defer).
            #   SL 이 있으면 bracket SL 이 보호 → 진입 허용 (트레일링은 drop, SL-only 동작).
            #   실제 트레일링 placement 는 fast-follow (데모 round-trip 검증 후).
            if (
                event.action == "entry"
                and event.trailing_stop is not None
                and event.stop_loss is None
            ):
                await event_repo.mark_failed(
                    event.id, error="trailing_stop_live_placement_unsupported"
                )
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                return {"failed": "trailing_unsupported"}

            # OrderRequest 조립 — DB NUMERIC(18,8) round-trip 후 0/비정상으로 반올림된 exit
            # 레벨 등 모든 ValidationError 를 graceful mark_failed (poison pill 완전 차단,
            # 평가자 게이트 belt-and-suspenders). _to_decimal 의 float-boundary 가드 보완.
            try:
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
                    # MP-1 — close 이벤트 청산 PnL → Order.realized_pnl (kill-switch SUM 대상).
                    realized_pnl=event.realized_pnl,
                    # Wave 1 C3 — close 주문 reduce-only (over-fill/반전 방지). entry=False.
                    reduce_only=_action_is_reduce_only(event.action),
                    # Phase 3 — entry 주문에 TP/SL bracket 부착 → Bybit 포지션 bracket(거래소-네이티브 OCO).
                    # close 이벤트는 None (fold 안 됨). _merge_exit_params 가 takeProfit/stopLoss params 주입.
                    take_profit=event.take_profit,
                    stop_loss=event.stop_loss,
                    # ★ STEP B — trailing_stop 을 Order 에 영속(의도 보존). entry 는 reduce_only=False
                    #   라 tasks/trading 이 create_order 에 미주입(trailingStop 실으면 ccxt 가
                    #   trading-stop 엔드포인트로 라우팅 → entry 깨짐). 체결 후 place_trailing_stop 가
                    #   Order.trailing_stop 을 읽어 set_trading_stop 으로 발주(포지션 open 뒤).
                    #   trailing-only(SL 부재)는 위 가드가 여전히 거부(stage 2 — 무방비 윈도 회피).
                    #   ★ entry 만 영속(Opus A P3 defensive) — close 신호는 trailing=None 계약이나,
                    #   future extractor 가 reduce-only close 에 non-null trailing 을 실으면 ccxt 가
                    #   close 시장가를 trading-stop 으로 재라우팅(flatten 대신 trailing set) → 명시 차단.
                    trailing_stop=event.trailing_stop if event.action == "entry" else None,
                )
            except ValidationError as exc:
                await event_repo.mark_failed(event.id, error=f"invalid_order_request: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                return {"failed": "invalid_order_request"}
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
            except (
                NotionalExceeded,
                LeverageCapExceeded,
                MinNotionalNotMet,
                TradingSessionClosed,
            ) as exc:
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
