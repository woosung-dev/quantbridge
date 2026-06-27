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

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from src.common.alert import send_critical_alert
from src.common.metrics import qb_active_orders, qb_trailing_placement_total
from src.common.redis_client import get_redis_lock_pool
from src.core.config import settings
from src.trading.encryption import EncryptionService
from src.trading.exceptions import (
    OrderNotFound,
    ProviderError,
    UnsupportedExchangeError,
)
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderState,
)
from src.trading.providers import Credentials, ExchangeProvider, OrderSubmit
from src.trading.registry import dispatch as _dispatch_provider
from src.trading.repositories.order_repository import OrderRepository

# Sprint 15 Phase A.2 — submitted watchdog (BL-001) 상수.
_WATCHDOG_ALERT_TTL_SECONDS = 3600  # 1h Redis throttle (G.0 P1 #2)
_WATCHDOG_RETRY_BASE_SECONDS = 15
_WATCHDOG_MAX_ATTEMPTS = 3

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
                filled_at=filled_at,
            )
            if rows == 0:
                logger.warning(
                    "concurrent_transition_filled",
                    extra={"order_id": str(order_id)},
                )
                return {"order_id": str(order_id), "state": "conflict", "skipped": True}
            await session.commit()
            qb_active_orders.dec()  # Sprint 9 Phase D: terminal state (filled)
            # STEP B — 동기 fill winner: trailing 의도 entry 면 place_trailing_stop enqueue.
            _enqueue_trailing_if_intended(order)
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
                qb_active_orders.dec()
                # STEP B — watchdog fill winner (WS 유실 fallback): trailing enqueue.
                _enqueue_trailing_if_intended(order)
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
            await provider.cancel_order(creds, order.exchange_order_id)
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


def _is_position_zero_error(exc: ProviderError) -> bool:
    """retCode 110017 / position-zero = benign (체결→placement 사이 포지션 닫힘 race)."""
    msg = str(exc).lower()
    return "110017" in msg or "position is zero" in msg or "position not exist" in msg


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


async def _do_place_trailing_stop(
    *,
    order_id: UUID,
    symbol: str,
    entry_side: OrderSide,
    distance: Decimal,
    creds: Credentials,
    provider: Any,
) -> dict[str, Any]:
    """순수 오케스트레이션 — stale-position 가드 → set_trading_stop → 결과 분류.

    money-path: 무방비 방지가 목표. position flat/flip 은 benign skip(stale task 가
    신규/없는 포지션에 오부착 차단). network/exchange 실패는 raise → 상위 task 가
    bounded retry + 최종 실패 시 critical alert(포지션 무방비 표면화).
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

    try:
        await provider.set_trading_stop(
            creds, symbol=symbol, side=exit_side, qty=pos.size, distance=distance
        )
    except ProviderError as exc:
        if _is_position_zero_error(exc):
            logger.info("trailing_skip_position_zero", extra={"order_id": str(order_id)})
            qb_trailing_placement_total.labels(outcome="skipped_position_zero").inc()
            return {"skipped": "position_zero"}
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
            f"place_trailing_stop gave up after {_TRAILING_MAX_RETRIES} retries. "
            f"포지션에 TRAILING stop 미부착(고정 bracket SL 바닥은 active — 완전 무방비 아님). "
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
        # Opus A P2 — ProviderError(network/exchange) 뿐 아니라 DB outage / decrypt 실패 /
        #   engine 생성 실패 등 모든 예외를 bounded retry + 최종 critical alert 로 라우팅.
        #   미포착 시 Celery FAILED silent → trailing 미부착 무신호(money-path hole).
        #   benign skip(110017/flip)은 dict 반환이라 여기 미도달.
        if self.request.retries >= _TRAILING_MAX_RETRIES:
            run_in_worker_loop(_alert_trailing_unprotected(UUID(order_id), str(exc)))
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
            raise self.retry(
                countdown=_TRAILING_RETRY_BASE_SECONDS * (2**self.request.retries)
            )
        logger.warning("trailing_concede_position_flat", extra={"order_id": order_id})
        qb_trailing_placement_total.labels(outcome="skipped_position_flat_confirmed").inc()
        return {"skipped": "position_flat", "order_id": order_id}
    return result
