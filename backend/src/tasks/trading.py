"""execute_order_task — Celery shared_task + prefork-safe per-call engine.

Task 16: pending → submitted → provider.create_order → filled/rejected.
3-guard transitions via OrderRepository (Sprint 4 패턴).

Sprint 17 Phase C (codex G.0 P1 #1 격상): module-level _worker_engine 제거.
매 task 마다 fresh engine + finally dispose (backtest.py / funding.py mirror).

Sprint 22 BL-091: provider dispatch 가 (account.exchange, account.mode,
has_leverage) 3-tuple 기반 dynamic. settings.exchange_provider 는 dispatch path
에서 더 이상 참조 안 됨 (test_config.py 호환용 dead config).
- `_provider_for_account_and_leverage(exchange, mode, has_leverage)` = 본체
- `_build_exchange_provider(account, submit)` = create_order path public dispatcher
- fetch 분기는 OrderSubmit 부재 → Order.leverage 직접 사용
- UnsupportedExchangeError(ProviderError) → line 214 except 자동 catch (graceful rejected)
"""

from __future__ import annotations

import contextlib
import logging
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from src.common.alert import send_critical_alert
from src.common.metrics import (
    qb_active_orders,
    qb_closed_pnl_backfill_total,
    qb_exchange_exit_rows_total,
    qb_partial_fill_total,
    qb_trailing_placement_total,
)
from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.trading.alerting import send_rule_alert
from src.trading.encryption import EncryptionService
from src.trading.exceptions import (
    OrderNotFound,
    ProviderError,
    TrailingContractError,
    UnsupportedExchangeError,
)
from src.trading.exit_attribution import OrderFact, attribute_exit, classify_exit
from src.trading.models import (
    AlertChannel,
    ExchangeAccount,
    ExchangeExit,
    ExchangeMode,
    ExchangeName,
    ExitAttribution,
    ExitClassification,
    Order,
    OrderSide,
    OrderState,
)
from src.trading.providers import (
    BybitFuturesProvider,
    ClosedOrderMeta,
    Credentials,
    ExchangeProvider,
    OrderSubmit,
)
from src.trading.realtime_publisher import publish_realtime
from src.trading.registry import dispatch as _dispatch_provider
from src.trading.repositories.alert_rule_repository import AlertRuleRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.exchange_exit_repository import ExchangeExitRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.position_service import position_snapshot_cache_key

# Sprint 15 Phase A.2 — submitted watchdog (BL-001) 상수.
_WATCHDOG_ALERT_TTL_SECONDS = 3600  # 1h Redis throttle (G.0 P1 #2)
_WATCHDOG_RETRY_BASE_SECONDS = 15
_WATCHDOG_MAX_ATTEMPTS = 3
_CLOSED_PNL_MAX_RETRIES = 4
_CLOSED_PNL_RETRY_BASE_SECONDS = 5
_CLOSED_PNL_ENQUEUE_COUNTDOWN = 5
_EXIT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

logger = logging.getLogger(__name__)


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
# broker side effect (실제 거래소 주문) ↔ DB 상태 분기 위험 영역 — per-call engine 의무.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# ---------------------------------------------------------------------------
# ExchangeProvider dynamic dispatch — Sprint 22 BL-091
# ---------------------------------------------------------------------------
# 기존 module-level `_exchange_provider: ExchangeProvider | None` lazy singleton 제거.
# multi-account 사용자가 demo / live 동시 운용 시 process env 기반 라우팅이
# silent broker bypass 일으킴 (Sprint 20 dogfood Day 0 발견).
# 이제 (account.exchange, account.mode, has_leverage) 3-tuple 로 호출마다 dispatch.


def _has_leverage(submit_or_order: Any) -> bool:
    """leverage 가 not null AND numeric > 0 일 때만 futures.

    P2 #1 보정 (Sprint 22 G.0): OrderRequest schema 는 leverage Field(ge=1) 강제하지만,
    DB 컬럼 자체에는 CHECK 제약 없음. legacy/zero row 또는 service 우회 직접 INSERT 방어.

    P2 #2 보정 (Sprint 22 G.2): legacy/manual mutation 으로 leverage 가 string ("0")
    Decimal 등 비-int 타입이면 `lev > 0` 이 TypeError → ProviderError catch 밖 전파
    → task 실패. int/Decimal/float 만 허용, 그 외 type 은 spot (False) 로 분류.
    """
    from decimal import Decimal

    lev = getattr(submit_or_order, "leverage", None)
    if lev is None:
        return False
    if not isinstance(lev, (int, Decimal, float)):
        return False
    if isinstance(lev, bool):  # bool is subclass of int → 명시 제외
        return False
    return lev > 0


def _provider_for_account_and_leverage(
    exchange: ExchangeName,
    mode: ExchangeMode,
    has_leverage: bool,
) -> ExchangeProvider:
    """Dispatch 본체. (exchange, mode, has_leverage) 3-tuple → concrete provider.

    Sprint 47 BL-202: 본체는 `src.trading.registry.dispatch` 로 이관됐다. 본 함수는
    backwards-compat wrapper — `monkeypatch.setattr(task_mod,
    "_provider_for_account_and_leverage", ...)` 패턴을 사용하는 기존 테스트가
    그대로 작동하도록 symbol 을 유지한다.

    호출자는 OrderSubmit 또는 Order 어느 쪽이든 leverage 추출 후 호출.
    fetch_order 분기는 OrderSubmit 부재 → Order.leverage 직접 사용.

    실패 정책 (P1 #2):
    - 미지원 조합 → UnsupportedExchangeError(ProviderError) raise (registry 책임)
    - 호출처 (`_execute_with_session` line 214 / `_fetch_order_status_with_session`)
      의 `except ProviderError` 가 자동 catch → Order graceful `rejected` 전이.
    """
    return _dispatch_provider(exchange, mode, has_leverage)


def _build_exchange_provider(account: ExchangeAccount, submit: OrderSubmit) -> ExchangeProvider:
    """Public dispatcher for create_order path.

    fetch 분기는 `_provider_for_account_and_leverage(account.exchange, account.mode,
    _has_leverage(order))` 를 직접 호출 (OrderSubmit 부재).
    """
    return _provider_for_account_and_leverage(account.exchange, account.mode, _has_leverage(submit))


# ---------------------------------------------------------------------------
# Sprint 23 BL-102 — Order.dispatch_snapshot 우선 dispatch + legacy fallback
# ---------------------------------------------------------------------------


def _parse_order_dispatch_snapshot(
    raw: dict[str, object] | None,
) -> tuple[ExchangeName, ExchangeMode, bool] | None:
    """JSONB snapshot → (exchange, mode, has_leverage) tuple. 엄격 검증.

    invalid snapshot (missing key / unknown enum / non-bool / non-dict) → None
    반환. 호출자는 None 받으면 `qb_order_snapshot_fallback_total{reason="invalid"}`
    inc 후 legacy fallback. ValueError/KeyError task 밖 전파 차단.

    codex G.0 P1 #4 fix (Sprint 23):
    - `bool("false") == True` 위험 → `isinstance(bool)` 강제
    - `ExchangeName("BAD")` ValueError → try/except 로 None
    - JSONB manual mutation (`{"exchange": "BAD"}`) → graceful fallback
    """
    if not raw or not isinstance(raw, dict):
        return None
    try:
        exch_str = raw["exchange"]
        mode_str = raw["mode"]
        has_lev = raw["has_leverage"]
        if not isinstance(exch_str, str) or not isinstance(mode_str, str):
            return None
        if not isinstance(has_lev, bool):  # bool("false") == True 회피
            return None
        return (ExchangeName(exch_str), ExchangeMode(mode_str), has_lev)
    except (KeyError, ValueError):
        return None


def _provider_from_order_snapshot_or_fallback(
    order: Any,
    account: ExchangeAccount,
    submit: OrderSubmit | None = None,
) -> ExchangeProvider:
    """Order.dispatch_snapshot 우선 사용, 부재/invalid 시 legacy fallback.

    Sprint 23 BL-102 (codex G.2 P2 #3 fix):
    - DB manual mutation 으로 Order.leverage / account.mode 변경 시에도 snapshot
      우선 → spot/futures 분기 일관성
    - legacy row (Sprint 23 이전 생성, snapshot=NULL) → account 현재값 + leverage
      fallback (graceful degrade)
    - `qb_order_snapshot_fallback_total{reason}` 으로 Sprint 24+ legacy row tracking

    Sprint 23 codex G.2 P1 #1 (critical security fix): snapshot 의 (exchange, mode)
    가 현재 account 와 다르면 silent broker bypass 위험 (snapshot=demo + account=live
    시 BybitDemoProvider 선택 + creds.environment=live → live endpoint 호출).
    credentials 는 항상 account 현재값이므로 mismatch 시 UnsupportedExchangeError
    raise → graceful rejected. mode drift 허용하려면 credentials 까지 immutable
    snapshot 필요 — 본 sprint scope 초과. reject 가 안전한 정책.
    """
    from src.common.metrics import qb_order_snapshot_fallback_total

    parsed = _parse_order_dispatch_snapshot(getattr(order, "dispatch_snapshot", None))
    if parsed is not None:
        exch, mode, has_lev = parsed
        # codex G.2 P1 #1 — drift 검증. snapshot vs current account mismatch
        # 시 reject (creds 가 account 현재값이라 silent broker bypass 위험).
        if exch != account.exchange or mode != account.mode:
            qb_order_snapshot_fallback_total.labels(reason="drift").inc()
            raise UnsupportedExchangeError(
                (
                    "snapshot",
                    f"{exch.value}/{mode.value}",
                    "vs account",
                    f"{account.exchange.value}/{account.mode.value}",
                )
            )
        return _provider_for_account_and_leverage(exch, mode, has_lev)

    # Legacy fallback (Sprint 23 이전 row 또는 invalid snapshot)
    reason = "missing" if not getattr(order, "dispatch_snapshot", None) else "invalid"
    qb_order_snapshot_fallback_total.labels(reason=reason).inc()
    has_lev_fallback = _has_leverage(submit) if submit is not None else _has_leverage(order)
    return _provider_for_account_and_leverage(account.exchange, account.mode, has_lev_fallback)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
@shared_task(name="trading.execute_order", max_retries=0)  # type: ignore[untyped-decorator]
def execute_order_task(order_id: str) -> dict[str, Any]:
    """Sync Celery entry point — Sprint 18 BL-080 Option C run_in_worker_loop."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_execute(UUID(order_id)))


async def _async_execute(order_id: UUID) -> dict[str, Any]:
    """Core logic: pending → submitted → provider.create_order → filled/rejected.

    Returns dict with order state for Celery result backend.

    Sprint 17 Phase C (codex G.0 P1 #1): per-call engine + finally dispose.
    """
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _execute_with_session(order_id, sm)
    finally:
        await engine.dispose()


async def _execute_with_session(
    order_id: UUID, sm: async_sessionmaker[AsyncSession]
) -> dict[str, Any]:
    async with sm() as session:
        repo = OrderRepository(session)

        # 1. Fetch order
        order = await repo.get_by_id(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        # Guard: only process pending orders
        if order.state != OrderState.pending:
            logger.warning(
                "order_not_pending",
                extra={"order_id": str(order_id), "state": order.state},
            )
            return {"order_id": str(order_id), "state": order.state, "skipped": True}

        # 2. Transition: pending → submitted
        now = datetime.now(UTC)
        rows = await repo.transition_to_submitted(order_id, submitted_at=now)
        if rows == 0:
            logger.warning(
                "concurrent_transition_submitted",
                extra={"order_id": str(order_id)},
            )
            return {"order_id": str(order_id), "state": "conflict", "skipped": True}
        await session.commit()
        account = None
        with contextlib.suppress(Exception):
            account = await session.get(ExchangeAccount, order.exchange_account_id)
        if account is not None:
            await publish_realtime(
                str(account.user_id),
                "order_update",
                {
                    "order_id": str(order.id),
                    "state": OrderState.submitted.value,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "source": "rest",
                },
            )

        # 3. Decrypt credentials
        try:
            crypto = EncryptionService(settings.trading_encryption_keys)
            account = await session.get(ExchangeAccount, order.exchange_account_id)
            if account is None:
                raise OrderNotFound(order_id)  # account missing — treat as error

            passphrase_pt = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase_pt,
                environment=account.mode,
            )
        except Exception as e:
            error_msg = f"credential_decrypt_failed: {type(e).__name__}"
            logger.error(
                "credential_decrypt_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            # Sprint 16 BL-027 (codex G.0 P1 #2): winner-only dec.
            # 다른 path (WS / reconciler / watchdog / user-cancel) 가 먼저 terminal
            # 전이 시 rowcount=0 loser 도 dec → 음수 drift. rowcount==1 winner 만 dec.
            rows = await repo.transition_to_rejected(
                order_id, error_message=error_msg, failed_at=datetime.now(UTC)
            )
            await session.commit()
            if rows == 1:
                qb_active_orders.dec()  # Sprint 9 Phase D: terminal state
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "error_message": error_msg,
            }

        # 4. Call exchange provider — Sprint 22 BL-091 dynamic dispatch.
        try:
            order_submit = OrderSubmit(
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                quantity=order.quantity,
                price=order.price,
                # Sprint 7a: Futures. Spot은 모두 None. DB는 str로 저장되지만
                # OrderRequest schema validator가 insert 시점에 Literal 검증 완료.
                leverage=order.leverage,
                margin_mode=order.margin_mode,  # type: ignore[arg-type]
                # Sprint 12 Phase C-pre: Order.id (UUID4) → exchange orderLinkId/clOrdId.
                # WebSocket order event 가 이 값으로 local DB row 매핑.
                client_order_id=str(order.id),
                # Wave 1 (TP/SL order primitives) — DB 에 저장된 라이브 손익보호 프리미티브를
                # provider params 로 전달. 기존 entry row 는 전부 default(None/False) 회귀.
                reduce_only=order.reduce_only,
                trigger_price=order.trigger_price,
                trigger_by=order.trigger_by,
                take_profit=order.take_profit,
                stop_loss=order.stop_loss,
                # Wave 2 (TP/SL placement) — triggerDirection/OCO/trailing.
                trigger_direction=order.trigger_direction,
                oco_group_id=order.oco_group_id,
                # ★ STEP B — trailing 은 reduce_only(보호) 주문에서만 create_order 에 전달.
                #   entry(reduce_only=False)는 None → trailingStop 미주입(entry 깨짐 차단).
                #   entry 의 trailing 의도는 Order.trailing_stop 에 영속되어 체결 후
                #   place_trailing_stop 가 set_trading_stop 으로 발주(create_order 미경유).
                trailing_stop=order.trailing_stop if order.reduce_only else None,
            )
            # Sprint 22 BL-091 + Sprint 23 BL-102: snapshot 우선 dispatch.
            # snapshot 부재 (legacy row) 또는 invalid (DB manual mutation) → account 현재값
            # fallback. UnsupportedExchangeError(ProviderError) / BybitLiveProvider stub /
            # OkxFuturesUnsupported 모두 아래 except ProviderError 가 graceful 처리.
            provider = _provider_from_order_snapshot_or_fallback(
                order, account, submit=order_submit
            )
            receipt = await provider.create_order(creds, order_submit)
        except ProviderError as e:
            error_msg = f"provider_failure: {e}"
            logger.error(
                "provider_create_order_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            # Sprint 16 BL-027 (codex G.0 P1 #2): winner-only dec.
            rows = await repo.transition_to_rejected(
                order_id, error_message=error_msg, failed_at=datetime.now(UTC)
            )
            await session.commit()
            if rows == 1:
                qb_active_orders.dec()  # Sprint 9 Phase D: terminal state
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "error_message": error_msg,
            }

        # 5. Transition based on receipt.status (Sprint 14 Phase C — codex G.0 P1 #1 fix).
        #    receipt.status 는 _map_ccxt_status() 의 결과:
        #      - "filled"    → CCXT status="closed"|"filled"  → DB filled 전이
        #      - "rejected"  → CCXT status="canceled"|"rejected" → DB rejected 전이
        #      - "submitted" → CCXT status="open"|"pending"|null  → submitted 유지
        #                       (WS order event / reconciler 가 terminal evidence 시 전이)
        #
        #    이 분기 추가 전엔 status="submitted" 도 무조건 transition_to_filled() 호출하여
        #    DB 거짓 양성 발생 (REST 주문 접수 ≠ 실제 체결). dogfood Day 2 가 broker
        #    실체결 미검증으로 끝난 원인 중 하나. Bybit Demo limit 주문이나 시장가 주문의
        #    "WaitForFill" 상태는 status="open" 으로 받음.
        if receipt.status == "filled":
            filled_at = datetime.now(UTC)
            rows = await repo.transition_to_filled(
                order_id,
                exchange_order_id=receipt.exchange_order_id,
                filled_price=receipt.filled_price,
                filled_quantity=receipt.filled_quantity,
                filled_at=filled_at,
            )
            if rows == 0:
                logger.warning(
                    "concurrent_transition_filled",
                    extra={"order_id": str(order_id)},
                )
                return {"order_id": str(order_id), "state": "conflict", "skipped": True}
            await session.commit()
            await publish_realtime(
                str(account.user_id),
                "order_update",
                {
                    "order_id": str(order.id),
                    "state": OrderState.filled.value,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "source": "rest",
                },
            )
            qb_active_orders.dec()  # Sprint 9 Phase D: terminal state (filled)
            if order.reduce_only:
                try:
                    sessions = await LiveSignalSessionRepository(session).list_active_by_account(
                        account.id
                    )
                    redis = get_redis_lock_pool()
                    for live_session in sessions:
                        await redis.delete(position_snapshot_cache_key(live_session.id))
                except Exception:
                    logger.warning(
                        "position_snapshot_cache_delete_failed",
                        extra={"order_id": str(order_id)},
                        exc_info=True,
                    )
            # STEP B — 동기 fill winner: trailing 의도 entry 면 place_trailing_stop enqueue.
            if (
                receipt.filled_quantity is not None
                and receipt.filled_quantity.is_finite()
                and receipt.filled_quantity < order.quantity
            ):
                qb_partial_fill_total.labels(source="rest").inc()
            _enqueue_trailing_if_intended(order)
            _enqueue_closed_pnl_refresh(order)
            logger.info(
                "order_executed",
                extra={
                    "order_id": str(order_id),
                    "exchange_order_id": receipt.exchange_order_id,
                    "filled_price": str(receipt.filled_price) if receipt.filled_price else None,
                },
            )
            return {
                "order_id": str(order_id),
                "state": "filled",
                "exchange_order_id": receipt.exchange_order_id,
                "filled_price": str(receipt.filled_price) if receipt.filled_price else None,
            }

        if receipt.status == "rejected":
            error_msg = "exchange_rejected_at_submission"
            # Sprint 16 BL-027 (codex G.0 P1 #2): winner-only dec.
            rows = await repo.transition_to_rejected(
                order_id, error_message=error_msg, failed_at=datetime.now(UTC)
            )
            await session.commit()
            if rows == 1:
                qb_active_orders.dec()  # Sprint 9 Phase D: terminal state
            logger.info(
                "order_rejected_by_exchange",
                extra={
                    "order_id": str(order_id),
                    "exchange_order_id": receipt.exchange_order_id,
                },
            )
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "exchange_order_id": receipt.exchange_order_id,
                "error_message": error_msg,
            }

        # status == "submitted" — exchange_order_id 만 attach. submitted 유지.
        # WS order event 가 orderLinkId(=Order.id) 또는 exchange_order_id 로 매칭하여
        # terminal 시 transition_to_filled / transition_to_rejected 호출.
        await repo.attach_exchange_order_id(order_id, receipt.exchange_order_id)
        await session.commit()
        # Sprint 15 Phase A.2 — submitted watchdog (BL-001) enqueue.
        # WS event 유실 / OKX private WS 부재 / Bybit 응답 손상 시 영구 submitted 고착 회피.
        # countdown=15s → 첫 fetch_order_status_task 호출 시점은 broker 응답 안정화 후.
        fetch_order_status_task.apply_async(args=[str(order_id)], countdown=15)
        logger.info(
            "order_submitted_pending_fill",
            extra={
                "order_id": str(order_id),
                "exchange_order_id": receipt.exchange_order_id,
            },
        )
        return {
            "order_id": str(order_id),
            "state": "submitted",
            "exchange_order_id": receipt.exchange_order_id,
        }


# ---------------------------------------------------------------------------
# Sprint 15 Phase A.2 — fetch_order_status_task (BL-001 submitted watchdog)
# ---------------------------------------------------------------------------


def _get_redis_lock_pool_for_alert() -> Any:
    """Redis pool indirection — test 가 monkeypatch 가능. 운영은 lock pool 그대로."""
    return get_redis_lock_pool()


def _get_redis_lock_pool_for_rule_alert() -> Any:
    """규칙 팬아웃 dedupe의 테스트 가능한 Redis pool 간접 함수."""
    return get_redis_lock_pool()


async def _try_rule_fanout_watchdog(session_db: AsyncSession, order: Any, reason: str) -> None:
    """이벤트로 정확히 귀속된 live session의 watchdog 규칙만 fan-out한다."""
    try:
        live_session = await LiveSignalSessionRepository(session_db).find_active_by_order_id(
            order.id
        )
        if live_session is None:
            return
        rules = await AlertRuleRepository(session_db).find_active_watchdog_rules_for(
            live_session.id
        )
        for rule in rules:
            can_fire = bool(
                await _get_redis_lock_pool_for_rule_alert().set(
                    f"qb_rule_alert:{rule.id}:{order.id}".encode(),
                    b"1",
                    nx=True,
                    ex=_WATCHDOG_ALERT_TTL_SECONDS,
                )
            )
            if can_fire:
                await send_rule_alert(
                    settings,
                    channel=rule.channel,
                    title="Live session order watchdog gave up",
                    message=(
                        f"Order watchdog gave up. Reason: {reason}. "
                        "Scope: the matching live session order."
                    ),
                    context={
                        "rule_id": str(rule.id)[:8],
                        "session_id": str(live_session.id)[:8],
                        "order_id": str(order.id)[:8],
                        "reason": reason,
                    },
                )
    except Exception:
        logger.exception("alert_rule_watchdog_fanout_failed", extra={"order_id": str(order.id)})


async def _try_watchdog_alert_throttled(
    order_id: UUID,
    exchange_order_id: str | None,
    attempt: int,
    reason: str,
) -> bool:
    """codex G.0 P1 #2 — Redis SET NX EX 3600 throttle. 동일 order 의 두 번째 alert 차단.

    Returns True if alert fired, False if throttled (Redis key 이미 존재).
    """
    pool = _get_redis_lock_pool_for_alert()
    key = f"qb_watchdog_alert:{order_id}".encode()
    can_fire = bool(await pool.set(key, b"1", nx=True, ex=_WATCHDOG_ALERT_TTL_SECONDS))
    if not can_fire:
        logger.info("watchdog_alert_throttled", extra={"order_id": str(order_id)})
        return False

    await send_critical_alert(
        settings,
        title=f"Order stuck submitted (attempt={attempt})",
        message=(
            f"Watchdog gave up after {attempt} fetch attempts. "
            f"Order remains submitted at exchange. Reason: {reason}"
        ),
        context={
            "order_id": str(order_id)[:8],
            "exchange_order_id": exchange_order_id or "<null>",
            "attempt": str(attempt),
            "reason": reason,
        },
    )
    return True


async def _async_fetch_order_status(order_id: UUID, attempt: int) -> dict[str, Any]:
    """Sprint 15 Phase A.2 — submitted watchdog core (BL-001).

    Flow:
    1. Fetch order; not_found / already_terminal / not_submitted 시 skip
    2. exchange_order_id IS NULL skip (G.0 P1 #3 — fetch 호출 불가)
    3. Decrypt creds; account missing 시 skip
    4. provider.fetch_order — ProviderError graceful skip (Celery layer 가 retry 결정)
    5. status 분기:
       - filled/rejected/cancelled → transition_* + commit + qb_active_orders.dec()
         단, rowcount=1 일 때만 dec (G.0 P1 #1 — race winner only)
       - submitted + attempt < max → watchdog_retry signal
       - submitted + attempt >= max → throttled alert + watchdog_giveup signal

    Sprint 17 Phase C (codex G.0 P1 #1): per-call engine + finally dispose.
    """
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _fetch_order_status_with_session(order_id, attempt, sm)
    finally:
        await engine.dispose()


async def _fetch_order_status_with_session(
    order_id: UUID,
    attempt: int,
    sm: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    async with sm() as session:
        repo = OrderRepository(session)
        order = await repo.get_by_id(order_id)
        if order is None:
            return {"order_id": str(order_id), "skipped": "not_found"}

        if order.state in (
            OrderState.filled,
            OrderState.rejected,
            OrderState.cancelled,
        ):
            return {
                "order_id": str(order_id),
                "state": order.state.value,
                "skipped": "already_terminal",
            }

        if order.state != OrderState.submitted:
            return {
                "order_id": str(order_id),
                "state": order.state.value,
                "skipped": "not_submitted",
            }

        if order.exchange_order_id is None:
            # G.0 P1 #3 — submitted + null exchange_order_id (transition_to_submitted commit
            # ~ attach_exchange_order_id 윈도우 또는 worker crash). fetch 호출 불가.
            # orphan_scanner (Phase A.3) 가 별도 alert/manual cleanup 처리.
            return {
                "order_id": str(order_id),
                "skipped": "no_exchange_order_id",
            }

        try:
            crypto = EncryptionService(settings.trading_encryption_keys)
            account = await session.get(ExchangeAccount, order.exchange_account_id)
            if account is None:
                return {"order_id": str(order_id), "skipped": "account_missing"}

            passphrase_pt = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase_pt,
                environment=account.mode,
            )
        except Exception as e:
            logger.error(
                "watchdog_credential_decrypt_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            return {"order_id": str(order_id), "skipped": "decrypt_failed"}

        # Sprint 22 BL-091 + Sprint 23 BL-102: snapshot 우선 dispatch (fetch 분기).
        # OrderSubmit 부재 → snapshot 부재 시 Order.leverage fallback.
        # UnsupportedExchangeError(ProviderError) 도 아래 except 가 자동 catch
        # → silent skip → watchdog retry → max attempts 후 alert.
        try:
            provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
            status_fetch = await provider.fetch_order(creds, order.exchange_order_id, order.symbol)
        except ProviderError as e:
            # codex G.2 P1 #2 fix — provider 일시 장애 (rate limit / auth /
            # network) 가 silent skip 되면 영원히 submitted 고착. 따라서
            # retry signal 발사 (max attempts 후 alert).
            logger.error(
                "watchdog_fetch_order_failed",
                extra={
                    "order_id": str(order_id),
                    "attempt": attempt,
                    "error": str(e),
                },
            )
            if attempt < _WATCHDOG_MAX_ATTEMPTS:
                countdown = _WATCHDOG_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                return {
                    "order_id": str(order_id),
                    "skipped": "provider_error",
                    "error": str(e),
                    "watchdog_retry": True,
                    "next_attempt": attempt + 1,
                    "countdown": countdown,
                }
            await _try_watchdog_alert_throttled(
                order_id,
                order.exchange_order_id,
                attempt,
                reason=f"provider_error:{type(e).__name__}",
            )
            await _try_rule_fanout_watchdog(session, order, f"provider_error:{type(e).__name__}")
            return {
                "order_id": str(order_id),
                "skipped": "provider_error",
                "error": str(e),
                "watchdog_giveup": True,
            }

        now = datetime.now(UTC)

        # codex G.0 P1 #1 — rowcount=1 일 때만 dec gauge. WS / reconciler / 다른 watchdog
        # task 가 winner 일 수 있어 rowcount=0 = race loser, dec 호출 차단.
        if status_fetch.status == "filled":
            rows = await repo.transition_to_filled(
                order_id,
                exchange_order_id=order.exchange_order_id,
                filled_price=status_fetch.filled_price,
                filled_quantity=status_fetch.filled_quantity,
                filled_at=now,
            )
            if rows == 1:
                await session.commit()
                await publish_realtime(
                    str(account.user_id),
                    "order_update",
                    {
                        "order_id": str(order.id),
                        "state": OrderState.filled.value,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "source": "watchdog",
                    },
                )
                qb_active_orders.dec()
                # STEP B — watchdog fill winner (WS 유실 fallback): trailing enqueue.
                if (
                    status_fetch.filled_quantity is not None
                    and status_fetch.filled_quantity.is_finite()
                    and status_fetch.filled_quantity < order.quantity
                ):
                    qb_partial_fill_total.labels(source="watchdog").inc()
                _enqueue_trailing_if_intended(order)
                _enqueue_closed_pnl_refresh(order)
                logger.info(
                    "watchdog_filled",
                    extra={
                        "order_id": str(order_id),
                        "filled_price": (
                            str(status_fetch.filled_price) if status_fetch.filled_price else None
                        ),
                    },
                )
                return {"order_id": str(order_id), "state": "filled"}
            logger.info("watchdog_race_skip_filled", extra={"order_id": str(order_id)})
            return {
                "order_id": str(order_id),
                "state": "filled",
                "skipped": "race",
            }

        if status_fetch.status == "rejected":
            rows = await repo.transition_to_rejected(
                order_id,
                error_message="exchange_rejected_after_submission",
                failed_at=now,
            )
            if rows == 1:
                await session.commit()
                await publish_realtime(
                    str(account.user_id),
                    "order_update",
                    {
                        "order_id": str(order.id),
                        "state": OrderState.rejected.value,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "source": "watchdog",
                    },
                )
                qb_active_orders.dec()
                return {"order_id": str(order_id), "state": "rejected"}
            return {
                "order_id": str(order_id),
                "state": "rejected",
                "skipped": "race",
            }

        if status_fetch.status == "cancelled":
            rows = await repo.transition_to_cancelled(order_id, cancelled_at=now)
            if rows == 1:
                await session.commit()
                await publish_realtime(
                    str(account.user_id),
                    "order_update",
                    {
                        "order_id": str(order.id),
                        "state": OrderState.cancelled.value,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "source": "watchdog",
                    },
                )
                qb_active_orders.dec()
                return {"order_id": str(order_id), "state": "cancelled"}
            return {
                "order_id": str(order_id),
                "state": "cancelled",
                "skipped": "race",
            }

        # status == "submitted" — exchange 가 여전히 미체결 보고.
        if attempt < _WATCHDOG_MAX_ATTEMPTS:
            # backoff: 15s → 30s → 60s (이전 attempt 의 누적 wait 후 재시도)
            countdown = _WATCHDOG_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
            return {
                "order_id": str(order_id),
                "state": "submitted",
                "watchdog_retry": True,
                "next_attempt": attempt + 1,
                "countdown": countdown,
            }

        # attempt >= max — Redis throttle 안에서 alert 발화.
        await _try_watchdog_alert_throttled(
            order_id,
            order.exchange_order_id,
            attempt,
            reason="still_submitted_after_max_attempts",
        )
        await _try_rule_fanout_watchdog(session, order, "still_submitted_after_max_attempts")
        return {
            "order_id": str(order_id),
            "state": "submitted",
            "watchdog_giveup": True,
        }


def _build_watchdog_retry_kwargs(order_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
    """codex G.2 P1 #1 fix — Celery retry args/kwargs 정확히 빌드.

    원본 positional args 보존 시 duplicate keyword argument TypeError → retry chain
    깨짐. 명시적 args=[order_id] + kwargs={attempt:N} 로 회피. None = no retry.
    Pure function — test 가 직접 호출 가능.
    """
    if not result.get("watchdog_retry"):
        return None
    return {
        "args": [order_id],
        "kwargs": {"attempt": result["next_attempt"]},
        "countdown": result["countdown"],
    }


@shared_task(name="trading.fetch_order_status", bind=True, max_retries=_WATCHDOG_MAX_ATTEMPTS)  # type: ignore[untyped-decorator]
def fetch_order_status_task(self: Any, order_id: str, attempt: int = 1) -> dict[str, Any]:
    """Sprint 15 Phase A.2 — Celery sync entry. submitted watchdog (BL-001).

    _async_fetch_order_status 가 watchdog_retry 신호 반환 시 self.retry() 로
    Celery 가 backoff 재enqueue. giveup 신호 시 result dict 만 반환 (alert 는 inner).

    Sprint 18 BL-080: asyncio.run → run_in_worker_loop (Option C).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    result = run_in_worker_loop(_async_fetch_order_status(UUID(order_id), attempt))
    retry_kwargs = _build_watchdog_retry_kwargs(order_id, result)
    if retry_kwargs is not None:
        raise self.retry(**retry_kwargs)
    return result


# ---------------------------------------------------------------------------
# CF4 — cancel_order_task (submitted 주문 거래소 취소; DB-only orphan 방지)
# ---------------------------------------------------------------------------


@shared_task(name="trading.cancel_order", max_retries=0)  # type: ignore[untyped-decorator]
def cancel_order_task(order_id: str) -> dict[str, Any]:
    """Sync Celery entry — submitted 주문을 거래소에서 취소 후 DB cancelled 전이.

    Sprint 18 BL-080: run_in_worker_loop (Option C). CF4 — provider.cancel_order
    성공 시에만 DB flip (실패 시 submitted 유지 → false cancel / orphan position 방지).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_cancel_order(UUID(order_id)))


async def _async_cancel_order(order_id: UUID) -> dict[str, Any]:
    """Sprint 17 Phase C 패턴 — per-call engine + finally dispose."""
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _cancel_order_with_session(order_id, sm)
    finally:
        await engine.dispose()


async def _cancel_order_with_session(order_id: UUID, sm: Any) -> dict[str, Any]:
    async with sm() as session:
        repo = OrderRepository(session)
        order = await repo.get_by_id(order_id)
        if order is None:
            return {"order_id": str(order_id), "skipped": "not_found"}
        if order.state != OrderState.submitted:
            return {
                "order_id": str(order_id),
                "state": order.state.value,
                "skipped": "not_submitted",
            }
        if order.exchange_order_id is None:
            # 거래소 미발주 (pre-ack window). 취소 호출 불가 — orphan_scanner 가 처리.
            return {"order_id": str(order_id), "skipped": "no_exchange_order_id"}

        try:
            crypto = EncryptionService(settings.trading_encryption_keys)
            account = await session.get(ExchangeAccount, order.exchange_account_id)
            if account is None:
                return {"order_id": str(order_id), "skipped": "account_missing"}
            passphrase_pt = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase_pt,
                environment=account.mode,
            )
        except Exception as e:
            logger.error(
                "cancel_credential_decrypt_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            return {"order_id": str(order_id), "skipped": "decrypt_failed"}

        try:
            provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
            # functional-parity 2026-07-23 — symbol 미전달로 실거래소 취소가 전부
            # ArgumentsRequired 였던 결함 수정 (provider 가 시장별 정규화 담당).
            await provider.cancel_order(creds, order.exchange_order_id, order.symbol)
        except ProviderError as e:
            # CF4 fail-closed: 거래소 취소 실패 시 DB flip 금지. 주문 submitted 유지
            # (reconciler / watchdog 가 terminal evidence 확보 시 전이).
            logger.error(
                "cancel_order_provider_failed",
                extra={"order_id": str(order_id), "error": str(e)},
            )
            return {"order_id": str(order_id), "skipped": "provider_error", "error": str(e)}

        rows = await repo.transition_to_cancelled(order_id, cancelled_at=datetime.now(UTC))
        if rows == 1:
            await session.commit()
            await publish_realtime(
                str(account.user_id),
                "order_update",
                {
                    "order_id": str(order.id),
                    "state": OrderState.cancelled.value,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "source": "cancel",
                },
            )
            qb_active_orders.dec()  # terminal 전이 — active gauge dec
            logger.info("order_cancelled_on_exchange", extra={"order_id": str(order_id)})
            return {"order_id": str(order_id), "state": "cancelled"}
        # race: 취소 호출과 fill/reject reconcile 겹침 — 이중 전이 금지.
        logger.info("cancel_race_skip", extra={"order_id": str(order_id)})
        return {"order_id": str(order_id), "skipped": "race"}


# ---------------------------------------------------------------------------
# STEP B — place_trailing_stop (체결된 포지션에 native trailing-stop 부착)
# ---------------------------------------------------------------------------
# 트레일링은 포지션 속성(별도 주문 아님) — entry create_order 에 실으면 ccxt 가
# trading-stop 엔드포인트로 라우팅해 entry 가 깨짐. 그래서 fill-transition 후 별도
# 발주. enqueue 는 winner-only fill 전이(동기/WS/watchdog/reconciler) 4곳 → 구조적으로 1회만.
# kill-switch/risk 우회(보호 주문 — 엔드포인트가 포지션을 늘릴 수 없음, 본질 reduce-only).
_TRAILING_MAX_RETRIES = 3
_TRAILING_RETRY_BASE_SECONDS = 10
# STEP B — fast-fill REST-lag 가드. 체결 직후 Bybit 포지션 엔드포인트가 fill 보다 늦게
#   materialize 될 수 있어, fetch_position None 을 즉시 진짜 flat 으로 단정하지 않고 이 횟수만큼
#   transient 재시도 후에야 concede(trailing silent 미부착 차단). MAX_RETRIES 미만으로 둬
#   network 재시도 예산을 남긴다.
_TRAILING_FLAT_RETRY_LIMIT = 2
# BL-372 same-side stale — close→동일방향 reopen 이 placement 창(countdown+retry) 안에
#   일어나면 fetch_position 이 side 일치 포지션을 반환해 flip 가드를 통과한다. 옛 order 의
#   trailing 이 무관한 새 trade 에 오부착(다른 trade exit policy 변경 = money-path). position
#   createdTime > our fill_at + 이 tolerance 면 reopened 로 보고 skip. tolerance 는 거래소-서버
#   clock skew 흡수용(정상 open 은 createdTime ≤ filled_at 이 자연 성립). `>` strict (경계=부착).
_TRAILING_REOPEN_TOLERANCE = timedelta(seconds=2)


def _is_position_zero_error(exc: ProviderError) -> bool:
    """retCode 110017 / position-zero = benign (체결→placement 사이 포지션 닫힘 race)."""
    msg = str(exc).lower()
    return "110017" in msg or "position is zero" in msg or "position not exist" in msg


def _classify_trailing_failure(exc: Exception) -> str:
    """원본 예외 텍스트(거래소 응답/내부 경로 누설) 대신 alert 에 실을 안전한 분류 문자열.

    substring 검사로 category 만 결정 — 원본은 절대 echo 안 함(호출부 logger.exception 으로 기록).
    """
    if isinstance(exc, TrailingContractError):
        return exc.reason
    if isinstance(exc, ProviderError):
        low = str(exc).lower()
        if any(k in low for k in ("timeout", "network", "connection", "temporarily")):
            return "network_error"
        return "exchange_rejected"
    return "unexpected"


def _enqueue_trailing_if_intended(order: Any) -> None:
    """fill-transition winner 가 trailing 의도 entry 면 place_trailing_stop enqueue.

    winner-only 전이(동기/WS/watchdog/reconciler 중 rowcount==1 한 곳)라 정확히 1회만
    발화 = 구조적 dedup(idempotency 컬럼 불요). countdown 으로 포지션 거래소 정착 시간 확보.

    entry(reduce_only=False)만 대상 — reduce-only close/manual 주문(P2 codex/Opus B)은
    체결 시 포지션이 닫히는 중이라 trailing 부착 불필요(불필요 task 차단).
    """
    if getattr(order, "trailing_stop", None) is None or getattr(order, "reduce_only", False):
        return
    place_trailing_stop_task.apply_async(args=[str(order.id)], countdown=2)


def _enqueue_closed_pnl_refresh(order: Any) -> None:
    """fill-transition winner 가 reduce-only 주문이면 거래소 확정 손익 조회를 예약한다."""
    if not getattr(order, "reduce_only", False):
        return
    refresh_closed_pnl_task.apply_async(
        args=[str(order.id)], countdown=_CLOSED_PNL_ENQUEUE_COUNTDOWN
    )


async def _do_place_trailing_stop(
    *,
    order_id: UUID,
    symbol: str,
    entry_side: OrderSide,
    distance: Decimal,
    creds: Credentials,
    provider: Any,
    order_filled_at: datetime | None = None,
) -> dict[str, Any]:
    """순수 오케스트레이션 — stale-position 가드 → set_trading_stop → 결과 분류.

    money-path: 무방비 방지가 목표. position flat/flip/reopened 는 benign skip(stale task 가
    신규/없는/무관 포지션에 오부착 차단). network/exchange 실패는 raise → 상위 task 가
    bounded retry + 최종 실패 시 critical alert(포지션 무방비 표면화).

    ``order_filled_at`` = 이 order 의 fill 처리 시각(BL-372 same-side stale 가드). None 이면
    (또는 pos.created_at None 이면) 비교 불가 → side-only 로 degrade(현행 동작).
    """
    # entry 포지션 방향 ↔ 청산(exit) side. ccxt 가 side/qty 는 드롭하지만 시그니처용.
    expected_side = "long" if entry_side == OrderSide.buy else "short"
    exit_side = OrderSide.sell if entry_side == OrderSide.buy else OrderSide.buy

    pos = await provider.fetch_position(creds, symbol)
    if pos is None:
        # STEP B — fetch_position None 은 "2s 내 실제 청산"과 "fill REST 미전파"가 구분 불가.
        #   즉시 benign flat 단정 = fast-fill 케이스에서 trailing silent 미부착(money-path hole).
        #   transient 분류 반환 → place_trailing_stop_task 가 bounded 재시도 후에야 concede.
        #   side-mismatch 가드가 flip 오부착을 막으므로 재시도는 안전.
        logger.info("trailing_position_not_visible", extra={"order_id": str(order_id)})
        qb_trailing_placement_total.labels(outcome="skipped_position_flat_premature").inc()
        return {"transient": "position_not_visible"}
    if pos.side != expected_side:
        # close + reopen flip → stale task. 신규 포지션에 잘못된 trailing 부착 차단.
        logger.warning(
            "trailing_skip_position_mismatch",
            extra={"order_id": str(order_id), "expected": expected_side, "actual": pos.side},
        )
        qb_trailing_placement_total.labels(outcome="skipped_position_mismatch").inc()
        return {"skipped": "position_mismatch"}

    # BL-372 same-side stale — side 는 같지만 우리 fill *후* 생성된(close→동일방향 reopen)
    #   포지션이면 무관한 trade 에 trailing 오부착이 된다. createdTime > filled_at + tol →
    #   reopened 로 판정해 benign skip. 타임스탬프 결측 시 비교 불가 → side-only degrade.
    #   이 가드는 placement 창의 *common*(>tol) 구간을 닫는 mitigation. 잔여(전부 BL-375):
    #     (a) sub-tolerance reopen: fill 후 2s 내 close+reopen 은 미탐(2s 는 clock-skew 흡수용).
    #     (b) TOCTOU: 이 createdTime read 와 set_trading_stop 사이 ms 윈도의 reopen(inherent).
    #     (c) reconcile-lag: filled_at 이 실제 거래소 fill 보다 늦게 기록되면 createdTime<filled_at.
    #     (d) clock-skew: worker clock 이 거래소보다 >tol 느리면 정상 open 도 false-skip.
    #   근본 fix(BL-375) = 거래소 fill-time 소싱. 데모 기간엔 고정 bracket SL floor 가 보호.
    if (
        pos.created_at is not None
        and order_filled_at is not None
        and pos.created_at > order_filled_at + _TRAILING_REOPEN_TOLERANCE
    ):
        logger.warning(
            "trailing_skip_position_reopened",
            extra={
                "order_id": str(order_id),
                "pos_created_at": pos.created_at.isoformat(),
                "order_filled_at": order_filled_at.isoformat(),
            },
        )
        qb_trailing_placement_total.labels(outcome="skipped_position_reopened").inc()
        return {"skipped": "position_reopened"}
    if pos.created_at is None or order_filled_at is None:
        logger.debug(
            "trailing_reopen_guard_skipped_no_timestamp",
            extra={"order_id": str(order_id)},
        )

    try:
        await provider.set_trading_stop(
            creds, symbol=symbol, side=exit_side, qty=pos.size, distance=distance
        )
    except ProviderError as exc:
        if _is_position_zero_error(exc):
            logger.info("trailing_skip_position_zero", extra={"order_id": str(order_id)})
            qb_trailing_placement_total.labels(outcome="skipped_position_zero").inc()
            return {"skipped": "position_zero"}
        if isinstance(exc, TrailingContractError):
            # contract 위반은 task 가 failed_contract 로 단일 집계 → 여기서 이중카운트 회피.
            raise
        # network/exchange 실패 = 포지션 무방비 → raise(상위 retry + alert).
        qb_trailing_placement_total.labels(outcome="failed").inc()
        raise

    logger.info("trailing_placed", extra={"order_id": str(order_id)})
    qb_trailing_placement_total.labels(outcome="placed").inc()
    return {"placed": True}


async def _place_trailing_stop_with_session(
    order_id: UUID, sm: async_sessionmaker[AsyncSession], *, provider: Any = None
) -> dict[str, Any]:
    async with sm() as session:
        repo = OrderRepository(session)
        order = await repo.get_by_id(order_id)
        if order is None:
            return {"skipped": "order_missing"}
        if order.trailing_stop is None:
            qb_trailing_placement_total.labels(outcome="skipped_no_intent").inc()
            return {"skipped": "no_trailing_intent"}
        crypto = EncryptionService(settings.trading_encryption_keys)
        account = await session.get(ExchangeAccount, order.exchange_account_id)
        if account is None:
            return {"skipped": "account_missing"}
        # P2(codex) — 트레일링은 Bybit linear(futures) 전용. 비-Bybit/spot 주문에 trailing_stop
        #   이 붙어도(manual API 경로) BybitFuturesProvider 발주 차단(doomed task / wrong creds).
        if account.exchange != ExchangeName.bybit or order.leverage is None:
            logger.info(
                "trailing_skip_unsupported_exchange",
                extra={"order_id": str(order_id), "exchange": str(account.exchange)},
            )
            qb_trailing_placement_total.labels(outcome="skipped_unsupported").inc()
            return {"skipped": "unsupported_exchange"}
        passphrase_pt = (
            crypto.decrypt(account.passphrase_encrypted)
            if account.passphrase_encrypted is not None
            else None
        )
        creds = Credentials(
            api_key=crypto.decrypt(account.api_key_encrypted),
            api_secret=crypto.decrypt(account.api_secret_encrypted),
            passphrase=passphrase_pt,
            environment=account.mode,
        )
        # exchange IO 전에 필요한 필드만 추출 (detached instance 회피).
        symbol = order.symbol
        entry_side = order.side
        distance = order.trailing_stop
        order_filled_at = order.filled_at  # BL-372 same-side stale 가드 입력

    if provider is None:
        # 트레일링은 Bybit linear 전용(set_trading_stop). dispatch 와 동일 직접 생성.
        from src.trading.providers import BybitFuturesProvider

        provider = BybitFuturesProvider()
    return await _do_place_trailing_stop(
        order_id=order_id,
        symbol=symbol,
        entry_side=entry_side,
        distance=distance,
        creds=creds,
        provider=provider,
        order_filled_at=order_filled_at,
    )


async def _async_place_trailing_stop(order_id: UUID) -> dict[str, Any]:
    """Sprint 17 Phase C 패턴 — per-call engine + finally dispose."""
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _place_trailing_stop_with_session(order_id, sm)
    finally:
        await engine.dispose()


async def _alert_trailing_unprotected(order_id: UUID, reason: str) -> None:
    # Opus A P3 — 트레일링 entry 는 항상 고정 bracket SL 동반(live_signal 가드)이라
    # SL 바닥은 유효 = 완전 무방비 아님. trailing "업그레이드"만 미부착(profit-lock 손실).
    await send_critical_alert(
        settings,
        title="Trailing stop placement failed — TRAILING 미부착 (고정 bracket SL 은 유효)",
        message=(
            "place_trailing_stop gave up — 포지션에 TRAILING stop 미부착"
            "(고정 bracket SL 바닥은 active — 완전 무방비 아님). "
            f"Reason: {reason}"
        ),
        context={"order_id": str(order_id)[:8], "reason": reason},
    )


@shared_task(  # type: ignore[untyped-decorator]
    name="trading.place_trailing_stop", bind=True, max_retries=_TRAILING_MAX_RETRIES
)
def place_trailing_stop_task(self: Any, order_id: str) -> dict[str, Any]:
    """STEP B — 체결된 entry 포지션에 native trailing-stop 부착 (fill-transition 후 enqueue).

    Sprint 18 BL-080: run_in_worker_loop (Option C). network/exchange 실패는
    bounded retry; 최종 실패 시 critical alert(포지션 무방비 표면화). benign skip
    (position flat/flip/zero)은 retry/alert 없음.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    try:
        result = run_in_worker_loop(_async_place_trailing_stop(UUID(order_id)))
    except Exception as exc:
        # Opus A P2 — 모든 예외를 bounded retry + 최종 critical alert 로 라우팅(silent FAILED 차단).
        #   benign skip(110017/flip)은 dict 반환이라 여기 미도달.
        # BL-372 — TrailingContractError(버전/degenerate/hedge)는 결정적 = 재시도 무의미 → 즉시 give up.
        if isinstance(exc, TrailingContractError):
            logger.exception("trailing_contract_violation", extra={"order_id": order_id})
            run_in_worker_loop(_alert_trailing_unprotected(UUID(order_id), reason=exc.reason))
            qb_trailing_placement_total.labels(outcome="failed_contract").inc()
            return {"failed": exc.reason, "order_id": order_id}
        if self.request.retries >= _TRAILING_MAX_RETRIES:
            # BL-372 #7 — 원본 str(exc) 는 logger.exception 으로만, Slack 엔 분류 문자열.
            logger.exception("trailing_unprotected_giveup", extra={"order_id": order_id})
            run_in_worker_loop(
                _alert_trailing_unprotected(UUID(order_id), reason=_classify_trailing_failure(exc))
            )
            return {"failed": "trailing_unprotected", "order_id": order_id}
        raise self.retry(
            exc=exc,
            countdown=_TRAILING_RETRY_BASE_SECONDS * (2**self.request.retries),
        ) from exc

    # STEP B — fast-fill REST-lag false-flat: 포지션이 아직 REST 에 안 보임(transient). bounded
    #   재시도로 "fill 미전파"와 "진짜 청산"을 구분 — 한도 내엔 재시도, 초과 시 benign concede
    #   (완전 무방비 아님 — 고정 bracket SL floor 유효라 critical alert 불요). silent 미부착 차단.
    if result.get("transient") == "position_not_visible":
        if self.request.retries < _TRAILING_FLAT_RETRY_LIMIT:
            raise self.retry(countdown=_TRAILING_RETRY_BASE_SECONDS * (2**self.request.retries))
        logger.warning("trailing_concede_position_flat", extra={"order_id": order_id})
        qb_trailing_placement_total.labels(outcome="skipped_position_flat_confirmed").inc()
        return {"skipped": "position_flat", "order_id": order_id}
    return result


async def _alert_closed_pnl_unbackfilled(order_id: UUID, reason: str) -> None:
    """거래소 확정 손익 미반영을 운영자에게 명시한다.

    같은 스프린트의 divergence 알림과 동일하게 Slack+Telegram 양쪽으로 보낸다 — 리스크
    게이트가 추정값으로 돌고 있다는 사실은 발산 경고 못지않게 money-critical 이라
    한 채널만 보는 시간대에 놓치면 안 된다. 채널별 실패는 send_rule_alert 가 격리한다.
    """
    await send_rule_alert(
        settings,
        channel=AlertChannel.both,
        title="거래소 확정 청산 손익 미반영",
        message=(
            "closedPnl 조회를 포기했습니다. 이 주문 행은 pine_v2 추정 손익을 유지하고 있으며 "
            "Kill Switch도 해당 추정값을 사용 중입니다. "
            f"사유: {reason}"
        ),
        context={"order_id": str(order_id)[:8], "reason": reason},
    )


async def _refresh_closed_pnl_with_session(
    order_id: UUID,
    sm: async_sessionmaker[AsyncSession],
    *,
    provider: Any = None,
) -> dict[str, Any]:
    """단일 reduce-only 체결 주문의 Bybit 확정 손익을 조건부로 교체한다."""
    async with sm() as session:
        repo = OrderRepository(session)
        order = await repo.get_by_id(order_id)
        if order is None:
            return {"skipped": "order_missing", "order_id": str(order_id)}
        if order.state != OrderState.filled:
            return {"skipped": "not_filled", "order_id": str(order_id)}
        if not order.reduce_only:
            return {"skipped": "not_reduce_only", "order_id": str(order_id)}
        # 아래 세 갈래는 "정상 no-op"(경합/미지원)이 아니라 데이터 이상이다 — 조용히
        # 반환하면 해당 체결 청산이 추정 손익으로 남는데 운영이 알 방법이 없다.
        if order.exchange_order_id is None:
            qb_closed_pnl_backfill_total.labels(outcome="skipped_incomplete").inc()
            return {"skipped": "no_exchange_order_id", "order_id": str(order_id)}
        account = await session.get(ExchangeAccount, order.exchange_account_id)
        if account is None:
            qb_closed_pnl_backfill_total.labels(outcome="skipped_incomplete").inc()
            return {"skipped": "account_missing", "order_id": str(order_id)}
        if account.exchange != ExchangeName.bybit or order.leverage is None:
            qb_closed_pnl_backfill_total.labels(outcome="skipped_unsupported").inc()
            return {"skipped": "unsupported_exchange", "order_id": str(order_id)}
        try:
            crypto = EncryptionService(settings.trading_encryption_keys)
            passphrase_pt = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase_pt,
                environment=account.mode,
            )
        except Exception as exc:
            logger.error(
                "closed_pnl_credential_decrypt_failed",
                extra={"order_id": str(order_id), "error": str(exc)},
            )
            # 키 회전 실패 등 — 계정 전체가 영향받으므로 metric 으로 반드시 표면화한다.
            qb_closed_pnl_backfill_total.labels(outcome="failed_provider").inc()
            return {"skipped": "decrypt_failed", "order_id": str(order_id)}
        symbol = order.symbol
        exchange_order_id = order.exchange_order_id
        filled_at = order.filled_at

    if filled_at is None:
        qb_closed_pnl_backfill_total.labels(outcome="skipped_incomplete").inc()
        return {"skipped": "no_filled_at", "order_id": str(order_id)}
    if provider is None:
        from src.trading.providers import BybitFuturesProvider

        provider = BybitFuturesProvider()
    snapshot = await provider.fetch_closed_pnl(
        creds, symbol, order_id=exchange_order_id, since=filled_at
    )
    if snapshot is None:
        return {
            "transient": "closed_pnl_not_yet_available",
            "order_id": str(order_id),
        }

    async with sm() as session:
        rows = await OrderRepository(session).backfill_exchange_realized_pnl(
            order_id,
            realized_pnl=snapshot.closed_pnl,
            synced_at=datetime.now(UTC),
        )
        if rows == 1:
            await session.commit()
            qb_closed_pnl_backfill_total.labels(outcome="applied").inc()
            return {"applied": True, "order_id": str(order_id)}
    qb_closed_pnl_backfill_total.labels(outcome="already_synced").inc()
    return {"skipped": "already_synced", "order_id": str(order_id)}


async def _async_refresh_closed_pnl(order_id: UUID) -> dict[str, Any]:
    """작업 호출마다 엔진을 만들고 확정 손익 조회 뒤 반드시 폐기한다."""
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _refresh_closed_pnl_with_session(order_id, sm)
    finally:
        await engine.dispose()


@shared_task(  # type: ignore[untyped-decorator]
    name="trading.refresh_closed_pnl", bind=True, max_retries=_CLOSED_PNL_MAX_RETRIES
)
def refresh_closed_pnl_task(self: Any, order_id: str) -> dict[str, Any]:
    """체결 직후 Bybit closedPnl이 정착되면 pine_v2 추정 손익을 교체한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    try:
        result = run_in_worker_loop(_async_refresh_closed_pnl(UUID(order_id)))
    except Exception as exc:
        if self.request.retries >= _CLOSED_PNL_MAX_RETRIES:
            logger.exception("closed_pnl_backfill_provider_giveup", extra={"order_id": order_id})
            qb_closed_pnl_backfill_total.labels(outcome="failed_provider").inc()
            run_in_worker_loop(_alert_closed_pnl_unbackfilled(UUID(order_id), "provider_error"))
            return {"failed": "provider_error", "order_id": order_id}
        raise self.retry(
            exc=exc,
            countdown=_CLOSED_PNL_RETRY_BASE_SECONDS * (2**self.request.retries),
        ) from exc

    if result.get("transient") == "closed_pnl_not_yet_available":
        if self.request.retries < _CLOSED_PNL_MAX_RETRIES:
            raise self.retry(countdown=_CLOSED_PNL_RETRY_BASE_SECONDS * (2**self.request.retries))
        logger.warning("closed_pnl_backfill_never_found", extra={"order_id": order_id})
        qb_closed_pnl_backfill_total.labels(outcome="never_found").inc()
        run_in_worker_loop(
            _alert_closed_pnl_unbackfilled(UUID(order_id), "closed_pnl_not_yet_available")
        )
        return {"failed": "closed_pnl_not_yet_available", "order_id": order_id}
    return result


def _datetime_to_ms(value: datetime) -> int:
    """Aware UTC 시각을 부동소수점 없이 epoch 밀리초로 바꾼다."""
    delta = value.astimezone(UTC) - _UNIX_EPOCH
    return ((delta.days * 86_400 + delta.seconds) * 1_000) + delta.microseconds // 1_000


def _ms_to_datetime(value: int) -> datetime:
    """epoch 밀리초를 aware UTC 시각으로 바꾼다."""
    return _UNIX_EPOCH + timedelta(milliseconds=value)


def _datetime_from_ms(value: int | None) -> datetime | None:
    """epoch 밀리초를 aware UTC 시각으로 바꾼다. 값이 없으면 None."""
    return None if value is None else _ms_to_datetime(value)


def _order_facts(orders: Sequence[Order]) -> list[OrderFact]:
    """영속 Order를 귀속 순수 함수의 최소 입력으로 축소한다."""
    return [
        OrderFact(
            order_id=order.id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side_is_buy=order.side == OrderSide.buy,
            reduce_only=order.reduce_only,
            quantity=order.quantity,
            filled_price=order.filled_price,
            filled_at=order.filled_at,
        )
        for order in orders
        if order.filled_at is not None
    ]


async def _alert_new_exchange_exits(
    sm: async_sessionmaker[AsyncSession], account_id: UUID, row_hashes: Sequence[str]
) -> bool:
    """새 비앱 청산 행을 계정별 한 번만 운영자에게 알린다.

    조회까지 try 안에 둔다 — 원장은 이미 커밋됐고 provider 도 정상인데 알림 조회 실패가
    계정 핸들러로 새면 outcome="failed_provider" 로 잘못 계상된다.
    """
    # 원장 UNIQUE가 "본 적 있음"을 영속하므로 같은 행은 재조회되어도 다시 발화하지 않는다.
    try:
        async with sm() as session:
            rows = await ExchangeExitRepository(session).list_by_row_hashes(account_id, row_hashes)
        external_rows = [row for row in rows if row.classification != ExitClassification.ours]
        if not external_rows:
            return False
        # ★list_by_row_hashes 는 새 세션으로 DB 를 재조회한다. `classification` 컬럼은
        # 평문 String(24) 이라 SQLAlchemy 가 재수화할 때 str 그대로 온다(ExitClassification
        # StrEnum 으로 다시 캐스팅하지 않는다) — row 가 방금 만든 메모리 객체일 때만 진짜
        # enum 이다. `.value` 는 plain str 에 없어 AttributeError 로 던지고 이 함수 전체가
        # except 로 삼켜 알림이 조용히 죽는다. StrEnum.__str__ 은 값 자체를 돌려주므로
        # str() 은 두 경우 모두 안전하다.
        classifications = Counter(str(row.classification) for row in external_rows)
        total_pnl = sum((row.closed_pnl for row in external_rows), Decimal("0"))
        symbols = sorted({row.symbol for row in external_rows})
        await send_rule_alert(
            settings,
            channel=AlertChannel.both,
            title="거래소 청산 원장 신규 비앱 청산",
            message=(
                f"거래소에만 있던 청산 {len(external_rows)}건을 적재했습니다. "
                f"순손익 {total_pnl}, 분류 {dict(classifications)}, 심볼 {', '.join(symbols)}."
            ),
            context={
                "account_id": str(account_id)[:8],
                "count": len(external_rows),
                "closed_pnl": str(total_pnl),
                "classifications": dict(classifications),
                "symbols": symbols,
            },
        )
    except Exception:
        # 알림 실패가 이미 커밋된 원장 적재를 되돌려서는 안 된다.
        logger.exception("exchange_exit_alert_failed", extra={"account_id": str(account_id)})
        return False
    return True


async def _sweep_closed_pnl_with_session(
    sm: async_sessionmaker[AsyncSession], *, provider: Any = None, now: datetime | None = None
) -> dict[str, int]:
    """Bybit 계정별 청산 원장을 채우고 원장 합계로 우리 주문 손익을 보정한다."""
    current = now or datetime.now(UTC)
    now_ms = _datetime_to_ms(current)
    summary = {
        "accounts": 0,
        "inserted": 0,
        "backfilled": 0,
        "resynced": 0,
        "alerted": 0,
    }
    async with sm() as session:
        accounts = await ExchangeAccountRepository(session).list_by_exchange(ExchangeName.bybit)

    for account in accounts:
        summary["accounts"] += 1
        try:
            if account.exchange != ExchangeName.bybit:
                qb_closed_pnl_backfill_total.labels(outcome="skipped_unsupported").inc()
                continue
            try:
                account_provider = provider or BybitFuturesProvider()
            except UnsupportedExchangeError:
                qb_closed_pnl_backfill_total.labels(outcome="skipped_unsupported").inc()
                continue
            crypto = EncryptionService(settings.trading_encryption_keys)
            passphrase = (
                crypto.decrypt(account.passphrase_encrypted)
                if account.passphrase_encrypted is not None
                else None
            )
            creds = Credentials(
                api_key=crypto.decrypt(account.api_key_encrypted),
                api_secret=crypto.decrypt(account.api_secret_encrypted),
                passphrase=passphrase,
                environment=account.mode,
            )
            # 원장은 최근 7일 한 창만 담는다. 과거로 훑던 창과 워터마크는 범위 축소로
            # 걷어냈다 — 그보다 오래된 거래소 청산은 원장에 들어오지 않는다(의도된 계약).
            start_ms = now_ms - _EXIT_WINDOW_MS
            end_ms = now_ms
            snapshots = await account_provider.fetch_closed_pnl_window(
                creds,
                None,
                start_ms=start_ms,
                end_ms=end_ms,
                log_context={"account_id": str(account.id)},
            )
            exchange_order_ids = list({snapshot.order_id for snapshot in snapshots})
            async with sm() as session:
                matched_orders = await OrderRepository(session).list_by_exchange_order_ids(
                    account.id, exchange_order_ids
                )
            matched_by_exchange_id = {
                order.exchange_order_id: order
                for order in matched_orders
                if order.exchange_order_id is not None
            }
            unmatched_ids = [
                snapshot.order_id
                for snapshot in snapshots
                if snapshot.order_id not in matched_by_exchange_id
            ]
            meta_by_order_id: dict[str, ClosedOrderMeta] = {}
            attribution_facts: list[OrderFact] = []
            if unmatched_ids:
                try:
                    meta_by_order_id = await account_provider.fetch_closed_order_meta(
                        creds, None, start_ms=start_ms, end_ms=end_ms
                    )
                except Exception:
                    logger.warning(
                        "closed_order_meta_fetch_failed",
                        exc_info=True,
                        extra={"account_id": str(account.id)},
                    )
                async with sm() as session:
                    attribution_orders = await OrderRepository(session).list_filled_for_attribution(
                        account.id
                    )
                attribution_facts = _order_facts(attribution_orders)

            rows: list[ExchangeExit] = []
            for snapshot in snapshots:
                exchange_created_at = _datetime_from_ms(
                    snapshot.created_at_ms
                    if snapshot.created_at_ms is not None
                    else snapshot.updated_at_ms
                )
                if exchange_created_at is None or snapshot.symbol is None or snapshot.side is None:
                    # 원장 필수 필드를 못 만든 행은 적재할 수 없다. 로그만 남기면
                    # 이 소실이 관측되지 않으므로 malformed_row 로 표면화한다.
                    qb_closed_pnl_backfill_total.labels(outcome="malformed_row").inc()
                    logger.warning(
                        "closed_pnl_ledger_row_skipped",
                        extra={"account_id": str(account.id), "order_id": snapshot.order_id},
                    )
                    continue
                matched_order = matched_by_exchange_id.get(snapshot.order_id)
                if matched_order is None:
                    attribution, strategy_id = attribute_exit(
                        symbol=snapshot.symbol,
                        avg_entry_price=snapshot.avg_entry_price,
                        exit_at=exchange_created_at,
                        our_filled_orders=attribution_facts,
                    )
                else:
                    attribution = ExitAttribution.exact
                    strategy_id = matched_order.strategy_id
                raw: dict[str, object] = dict(snapshot.raw or {})
                rows.append(
                    ExchangeExit(
                        exchange_account_id=account.id,
                        exchange_order_id=snapshot.order_id,
                        row_hash=ExchangeExit.compute_row_hash(
                            # raw 가 비어도 축퇴하지 않도록 항상 존재하는 스냅샷 id 를 쓴다.
                            snapshot.order_id,
                            raw.get("createdTime"),
                            raw.get("updatedTime"),
                            raw.get("closedSize"),
                            raw.get("closedPnl"),
                            raw.get("avgEntryPrice"),
                            raw.get("avgExitPrice"),
                            raw.get("cumExitValue"),
                        ),
                        symbol=snapshot.symbol,
                        side=snapshot.side,
                        closed_pnl=snapshot.closed_pnl,
                        closed_size=snapshot.closed_size,
                        avg_entry_price=snapshot.avg_entry_price,
                        avg_exit_price=snapshot.avg_exit_price,
                        exchange_created_at=exchange_created_at,
                        exchange_updated_at=_datetime_from_ms(snapshot.updated_at_ms),
                        classification=classify_exit(
                            matched_order_id=(
                                matched_order.id if matched_order is not None else None
                            ),
                            meta=meta_by_order_id.get(snapshot.order_id),
                        ),
                        create_type=(
                            meta_by_order_id[snapshot.order_id].create_type
                            if snapshot.order_id in meta_by_order_id
                            else None
                        ),
                        stop_order_type=(
                            meta_by_order_id[snapshot.order_id].stop_order_type
                            if snapshot.order_id in meta_by_order_id
                            else None
                        ),
                        order_link_id=(
                            meta_by_order_id[snapshot.order_id].order_link_id
                            if snapshot.order_id in meta_by_order_id
                            else None
                        ),
                        matched_order_id=(matched_order.id if matched_order is not None else None),
                        attributed_strategy_id=strategy_id,
                        attribution_confidence=attribution,
                        raw=raw,
                    )
                )
            async with sm() as session:
                new_hashes = await ExchangeExitRepository(session).upsert_rows(rows)
                await session.commit()
            # 커밋 성공 뒤에만 새 행을 계상해 실패한 트랜잭션을 완료로 보지 않는다.
            # ★알림·백필은 아래에서 새 세션으로 되읽으므로 이 커밋이 빠지면 둘 다
            # 조용히 아무 일도 하지 않는다(테스트가 커밋 호출을 검증한다).
            summary["inserted"] += len(new_hashes)
            new_hash_set = set(new_hashes)
            for row in rows:
                if row.row_hash in new_hash_set:
                    # BL-453 — classification 은 StrEnum + 평문 String 컬럼이라 재조회된
                    # 행에서는 plain str 로 온다. 여기 `rows` 는 아직 메모리 객체지만
                    # `.value` 를 남겨두면 소스가 재조회 경로로 바뀌는 순간 조용히 죽는다.
                    # `str()` 은 양쪽 모두 안전하다(StrEnum.__str__ 이 값 자체를 돌려준다).
                    qb_exchange_exit_rows_total.labels(classification=str(row.classification)).inc()
                    new_hash_set.remove(row.row_hash)

            async with sm() as session:
                order_repo = OrderRepository(session)
                exit_repo = ExchangeExitRepository(session)
                unsynced_orders = await order_repo.list_unsynced_reduce_only(account.id)
                sums = await exit_repo.aggregate_closed_pnl(
                    account.id,
                    [
                        order.exchange_order_id
                        for order in unsynced_orders
                        if order.exchange_order_id is not None
                    ],
                )
                applied = 0
                already_synced = 0
                resynced = 0
                for order in unsynced_orders:
                    if order.exchange_order_id is None:
                        continue
                    realized_pnl = sums.get(order.exchange_order_id)
                    if realized_pnl is None:
                        continue
                    if (
                        await order_repo.backfill_exchange_realized_pnl(
                            order.id, realized_pnl=realized_pnl, synced_at=current
                        )
                        == 1
                    ):
                        applied += 1
                    else:
                        already_synced += 1
                # ★체결 직후 refresh 는 원장을 거치지 않고 단일 조회 결과를 CAS 한다.
                # 분할 행 중 일부만 보이는 순간에 걸리면 부분합이 synced 로 고정되고
                # 미동기화 술어를 쓰는 위 경로는 그 주문을 영영 건너뛴다. 원장 합계와
                # 다르면 정정한다(값이 같으면 rowcount 0 이라 멱등).
                synced_orders = await order_repo.list_synced_reduce_only(account.id)
                synced_sums = await exit_repo.aggregate_closed_pnl(
                    account.id,
                    [
                        order.exchange_order_id
                        for order in synced_orders
                        if order.exchange_order_id is not None
                    ],
                )
                for order in synced_orders:
                    if order.exchange_order_id is None:
                        continue
                    ledger_pnl = synced_sums.get(order.exchange_order_id)
                    if ledger_pnl is None:
                        continue
                    if (
                        await order_repo.resync_exchange_realized_pnl(
                            order.id, realized_pnl=ledger_pnl, synced_at=current
                        )
                        == 1
                    ):
                        resynced += 1
                await session.commit()
            # 단일 fetch 결과가 아니라 원장 전체를 집계하므로 분할 행이 7일 창 경계에 갈려도
            # 부분합이 CAS로 영구 고정되지 않는다.
            summary["backfilled"] += applied
            summary["resynced"] += resynced
            for _ in range(applied + resynced):
                qb_closed_pnl_backfill_total.labels(outcome="applied").inc()
            for _ in range(already_synced):
                qb_closed_pnl_backfill_total.labels(outcome="already_synced").inc()
            if await _alert_new_exchange_exits(sm, account.id, new_hashes):
                summary["alerted"] += 1
        except Exception:
            qb_closed_pnl_backfill_total.labels(outcome="failed_provider").inc()
            logger.exception(
                "closed_pnl_sweep_account_failed", extra={"account_id": str(account.id)}
            )
    return summary


async def _async_sweep_closed_pnl() -> dict[str, int]:
    """스윕 작업 호출마다 엔진을 만들고 완료 뒤 폐기한다."""
    engine, sm = create_worker_engine_and_sm()
    try:
        return await _sweep_closed_pnl_with_session(sm)
    finally:
        await engine.dispose()


@shared_task(name="trading.sweep_closed_pnl")  # type: ignore[untyped-decorator]
def sweep_closed_pnl_task() -> dict[str, int]:
    """최근 청산 주문의 Bybit closedPnl 미반영분을 주기적으로 보완한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_sweep_closed_pnl())
