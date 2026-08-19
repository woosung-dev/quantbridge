# trading service — Order 실행 + advisory lock + idempotency 단독 책임

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,  # 예외적 주입 — OrderService.execute advisory lock 전용
)

from src.common.metrics import qb_active_orders, qb_order_rejected_total
from src.common.metrics_multiproc import _count_safely, record_metric_safely
from src.core.config import settings
from src.strategy.trading_sessions import is_allowed as _sessions_is_allowed
from src.trading.exceptions import (
    AccountOwnershipMismatch,
    BalanceUnverified,
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    MinNotionalNotMet,
    NotionalExceeded,
    OwnerAccountInactive,
    RiskSizingExceeded,
    TradingSessionClosed,
)
from src.trading.kill_switch import KillSwitchService
from src.trading.models import ExchangeMode, Order, OrderState
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest, OrderResponse
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.protocols import OrderDispatcher, StrategySessionsPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CancelOutcome:
    kind: Literal["not_found", "exchange_requested", "cancelled", "conflict"]
    order: Order | None = None


class OrderService:
    """주문 생성 경로. Celery dispatch는 반드시 commit 이후 (visibility race 방지).

    E9: kill_switch.ensure_not_gated — begin_nested 내부, advisory lock 이후, INSERT 이전.
    E2: body_hash — 동일 idempotency_key + 다른 payload → IdempotencyConflict.

    Sprint 7d: strategy.trading_sessions 가드. 현재 UTC hour가 허용 세션 밖이면
    TradingSessionClosed 로 빠르게 실패 (kill switch / advisory lock 이전에 평가).

    Sprint 8+ (2026-04-20): notional check — qty x price x leverage가 계좌 자본 x
    max_leverage x 0.95 초과 시 NotionalExceeded 422. exchange_service 주입 시만 enforce.
    """

    def __init__(
        self,
        session: AsyncSession,
        repo: OrderRepository,
        dispatcher: OrderDispatcher,
        kill_switch: KillSwitchService,
        sessions_port: StrategySessionsPort | None = None,
        exchange_service: ExchangeAccountService | None = None,
    ) -> None:
        self._session = session
        self._repo = repo
        self._dispatcher = dispatcher
        self._kill_switch = kill_switch
        self._sessions_port = sessions_port
        self._exchange_service = exchange_service

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        states: Sequence[OrderState] | None = None,
    ) -> tuple[Sequence[Order], int]:
        return await self._repo.list_by_user(user_id, limit=limit, offset=offset, states=states)

    async def get_for_user(self, order_id: UUID, user_id: UUID) -> Order | None:
        return await self._repo.get_by_id_for_user(order_id, user_id)

    async def cancel_for_user(self, order_id: UUID, user_id: UUID) -> CancelOutcome:
        order = await self._repo.get_by_id_for_user(order_id, user_id)
        if order is None:
            return CancelOutcome("not_found")

        if order.state == OrderState.submitted:
            from src.tasks.trading import cancel_order_task

            cancel_order_task.delay(str(order_id))
            return CancelOutcome("exchange_requested")

        rowcount = await self._repo.transition_pending_to_cancelled(
            order_id, cancelled_at=datetime.now(UTC)
        )
        await self._repo.commit()
        if rowcount == 0:
            return CancelOutcome("conflict")

        return CancelOutcome("cancelled", order=await self._repo.get_by_id(order_id))

    async def execute(
        self,
        req: OrderRequest,
        *,
        idempotency_key: str | None,
        body_hash: bytes | None = None,
        flatten: bool = False,
    ) -> tuple[OrderResponse, bool]:
        """Sprint 11 Phase E — idempotency_key 가 있을 때 Service-level RedisLock 감싸기.
        실질 분산 mutex. Redis 장애 시 graceful degrade → PG advisory 가 권위.
        """
        if flatten and not req.reduce_only:
            raise ValueError("flatten requires reduce_only")
        if idempotency_key is None:
            return await self._execute_inner(
                req, idempotency_key=None, body_hash=None, flatten=flatten
            )

        from src.common.redlock import RedisLock

        async with RedisLock(f"idem:trading:{idempotency_key}", ttl_ms=30_000):
            return await self._execute_inner(
                req, idempotency_key=idempotency_key, body_hash=body_hash, flatten=flatten
            )

    # ★BL-580 (2026-08-03) — 이 클래스의 `qb_order_rejected_total` 10곳은 전부
    #   `.inc()` **직후 도메인 예외를 raise** 한다. 계측이 던지면 그 도메인 예외가 아예
    #   발생하지 않고 OSError 가 대신 올라간다. 9종 전부 AppException(4xx) 이라
    #   `main.py` 의 unhandled 핸들러로 가 **HTTP 500** 이 되고, 그중 6종은 호출자가
    #   **예외 타입으로 분기**하므로 기록·무재시도 분기가 통째로 빠진다.
    #   BL 표의 「blast radius 0」은 고장 주입으로 반증됐다 (10/10).
    #   `.labels()` 도 함께 감싼다 — 새 라벨 조합이 mmap 을 늘리는 지점이다 (BL-536 R2).
    async def _validate_position_size(self, req: OrderRequest) -> None:
        """Wave 2 P2 — 서버 권위 risk-기반 사이징. client qty 를 신뢰하지 않는다.

        max_qty = 자본(USDT 잔고) x risk_percent% / |entry - stop|. req.quantity 가
        max_qty 를 초과하면 RiskSizingExceeded. 한 트레이드 손실이 자본의 risk_percent%
        를 넘지 않도록 강제한다(자본 보존).

        skip(회귀 0, fail-open) 조건:
        - req.risk_percent 미설정 (가드 비활성)
        - exchange_service 미주입 (잔고 조회 불가 — notional 가드와 동일 게이트)
        - stop 미가용: stop = req.stop_loss(bracket) 우선, 없으면 req.trigger_price(standalone SL)
        - entry 미가용: entry = req.price 우선, market(None) 이면 mark price fetch
        - 잔고 None/0 또는 stop_distance 0 (DivisionByZero 차단)
        """
        if req.risk_percent is None or self._exchange_service is None:
            return
        stop = req.stop_loss if req.stop_loss is not None else req.trigger_price
        if stop is None:
            logger.info("risk_sizing_skip_no_stop", extra={"strategy_id": str(req.strategy_id)})
            return
        entry = req.price
        if entry is None:
            entry = await self._exchange_service.fetch_mark_price(
                req.exchange_account_id, req.symbol
            )
        if entry is None or entry <= Decimal("0"):
            return
        stop_distance = abs(entry - stop)
        if stop_distance <= Decimal("0"):
            return
        balance = await self._exchange_service.fetch_balance_usdt(req.exchange_account_id)
        if balance is None or balance <= Decimal("0"):
            return
        risk_budget = balance * req.risk_percent / Decimal("100")
        max_qty = risk_budget / stop_distance
        if req.quantity > max_qty:
            _count_safely(qb_order_rejected_total, exchange="unknown", reason="risk_sizing")
            raise RiskSizingExceeded(
                quantity=req.quantity,
                max_quantity=max_qty,
                risk_percent=req.risk_percent,
                stop_distance=stop_distance,
            )

    async def _execute_inner(
        self,
        req: OrderRequest,
        *,
        idempotency_key: str | None,
        body_hash: bytes | None,
        flatten: bool = False,
    ) -> tuple[OrderResponse, bool]:
        """Returns (response, is_replayed).

        Flow (autoplan E9 + E2):
        1. leverage cap 가드 (Sprint 7a 서비스 계층 enforcement)
        2. notional check (Sprint 8+ exchange_service 주입 시)
        3. begin_nested() — advisory lock + gate + insert 동일 tx
        4. idempotency 경로: lock → existing 확인 → hash 비교 → gate → INSERT
        5. commit 후 Celery dispatch (visibility race 방지)
        """
        # ── TRD-4: cross-tenant ownership gate (모든 side-effect 이전) ──
        # webhook 경로는 strategy HMAC 으로만 인증되고 exchange_account_id 를 caller
        # payload 에서 받으므로, account 소유자 != strategy 소유자면 거부해야 한다
        # (공격자가 타 tenant 계좌의 복호화된 credential 로 주문하는 IDOR 차단).
        # sessions_port + exchange_service 가 모두 주입된 production 경로
        # (get_order_service / live_signal) 에서 강제. 둘 다 없으면 검증 불가 →
        # data-layer 강제는 Phase C(TI-5) 후속.
        if self._sessions_port is not None and self._exchange_service is not None:
            owner_account = await self._exchange_service._repo.get_by_id(req.exchange_account_id)
            strategy_owner = await self._sessions_port.get_owner(req.strategy_id)
            if (
                owner_account is None
                or strategy_owner is None
                or owner_account.user_id != strategy_owner
            ):
                _count_safely(
                    qb_order_rejected_total, exchange="unknown", reason="ownership_mismatch"
                )
                raise AccountOwnershipMismatch(
                    f"exchange_account {req.exchange_account_id} 소유자가 strategy "
                    f"{req.strategy_id} 소유자와 일치하지 않음"
                )
            # ── 2026-08-15 surface-truth (S3): 탈퇴한 소유자의 주문 차단 ──
            # 탈퇴는 `UserService` 의 `user.deleted` 분기가 세션 전량 비활성 + 웹훅 시크릿
            # 전량 revoke 로 **원천**을 닫는다. 여기는 두 번째 문이다 — 시크릿 grace 창,
            # 이미 큐에 들어간 tick, 수기 주문처럼 원천 차단이 한 박자 늦는 자리에서
            # **돈이 나가는 마지막 순간**에 다시 묻는다.
            # ★소유권 대조 **뒤에** 둔다: 소유자를 먼저 확정해야 「누가 비활성인지」가 의미를 갖는다.
            if not await self._sessions_port.is_owner_active(strategy_owner):
                _count_safely(qb_order_rejected_total, exchange="unknown", reason="owner_inactive")
                raise OwnerAccountInactive(
                    f"strategy {req.strategy_id} 소유자 계정이 비활성 상태 — 주문을 발행하지 않음"
                )

        # Sprint 9 Phase D: service 레이어에서 exchange 직접 조회 회피 (async fetch 불필요).
        # 각 reject 카운터는 "unknown" exchange 로 집계 — dashboard 에서는 reason split 으로 충분.
        _metric_exchange = "unknown"

        # Sprint 23 BL-102 — dispatch snapshot 채움 (codex G.0 P1 #3 fix).
        # exchange_service 주입 시 account fetch 후 (exchange, mode, has_leverage) 저장.
        # exchange_service None (test 환경) → snapshot=None → tasks/trading.py legacy fallback.
        # OrderService.execute 의 inner transaction 시작 전에 미리 fetch 하여 양쪽 INSERT 분기
        # (idempotent vs non-idempotent) 모두에서 동일 snapshot 사용.
        dispatch_snapshot: dict[str, object] | None = None
        if self._exchange_service is not None:
            account = await self._exchange_service._repo.get_by_id(req.exchange_account_id)
            if account is not None:
                dispatch_snapshot = {
                    "exchange": account.exchange.value,
                    "mode": account.mode.value,
                    "has_leverage": req.leverage is not None and req.leverage > 0,
                }

        if not flatten:
            # Sprint 7a: OrderRequest.leverage Field(le=125)는 Bybit 이론 상한.
            # 운영 리스크 관리용 동적 cap은 서비스 계층에서 enforce (4/4 리뷰 컨센서스).
            if req.leverage is not None and req.leverage > settings.bybit_futures_max_leverage:
                _count_safely(
                    qb_order_rejected_total, exchange=_metric_exchange, reason="leverage_cap"
                )
                raise LeverageCapExceeded(
                    requested=req.leverage,
                    cap=settings.bybit_futures_max_leverage,
                )

            # Wave 2 P2 — 서버 권위 risk-기반 position sizing. notional 가드 전에 평가하여
            # client qty 가 risk budget 을 넘으면 거래소 round-trip 전에 빠르게 거부.
            # risk_percent 미설정 시 no-op (회귀 0).
            await self._validate_position_size(req)

            # Sprint 8+ (2026-04-20): notional check. exchange_service 주입 + leverage 존재 시 enforce.
            # P1-13 (S5-B, 2026-05-30): market order(price=None) 도 mark price 근사로 가드 적용.
            # live_signal 경로의 전 주문이 market 이라 기존 'price is not None' 게이트만으로는
            # notional 보호가 항상 우회 = #305 CF5 보호가 라이브 시그널에서 실효성 없음.
            # 보수적 버퍼(MARKET_NOTIONAL_BUFFER) 추가로 slippage 헷지. mark price fetch 실패
            # 시 live = fail-closed (BalanceUnverified), demo = fail-open (기존 정책 유지).
            if self._exchange_service is not None and req.leverage is not None:
                effective_price: Decimal | None = req.price
                # 조건부 주문은 mark 가 아니라 **트리거가**에서 집행된다. mark 로 검사하면
                # long 돌파(트리거가 > mark)에서 명목을 과소평가해 게이트를 통과시키고,
                # 정작 트리거 시점에 거래소가 증거금 부족으로 조용히 거부한다.
                if effective_price is None and req.trigger_price is not None:
                    effective_price = req.trigger_price
                if effective_price is None:
                    # P1-13 (S5-B) — market order: mark price 근사 (네트워크 1회 추가)
                    mark = await self._exchange_service.fetch_mark_price(
                        req.exchange_account_id, req.symbol
                    )
                    if mark is not None:
                        # slippage 버퍼 — 보수적 추정 (실제 체결가가 mark 보다 worst 일 수 있음)
                        effective_price = mark * Decimal("1.02")

                if effective_price is not None:
                    # Wave 1 C5 — min-notional 가드. 거래소 최소 주문 cost(limits.cost.min) 미달
                    # 주문은 거래소가 거부하므로 사전 차단. balance 와 독립적으로 평가하며,
                    # min cost 미가용(None) 시 skip(fail-open, demo 정책 일관). max-notional 가드보다 먼저.
                    min_notional = await self._exchange_service.fetch_min_notional(
                        req.exchange_account_id, req.symbol
                    )
                    if min_notional is not None:
                        position_notional = req.quantity * effective_price
                        if position_notional < min_notional:
                            _count_safely(
                                qb_order_rejected_total,
                                exchange=_metric_exchange,
                                reason="min_notional",
                            )
                            raise MinNotionalNotMet(
                                notional=position_notional, min_notional=min_notional
                            )
                    available = await self._exchange_service.fetch_balance_usdt(
                        req.exchange_account_id
                    )
                    if available is not None and available > Decimal("0"):
                        # CF5/MP-3 — Bybit/Binance 표준 initial-margin 모델 (벤치마크: bybit
                        # Order-Cost help-center). position notional = qty * price (leverage 미포함).
                        # 필요 initial margin = notional / leverage 가 available * 0.95 (open/close
                        # fee 버퍼) 이내여야 한다. 즉 notional <= available * leverage * 0.95.
                        # 이전 공식 (qty*price*leverage + max_leverage ceiling) 은 비표준 -
                        # 저레버리지에서 감당 불가 포지션 허용 / 고레버리지에서 정상 포지션 거부.
                        notional = req.quantity * effective_price
                        max_notional = available * Decimal(req.leverage) * Decimal("0.95")
                        if notional > max_notional:
                            _count_safely(
                                qb_order_rejected_total,
                                exchange=_metric_exchange,
                                reason="notional",
                            )
                            raise NotionalExceeded(
                                notional=notional,
                                available=available,
                                leverage=req.leverage,
                                max_notional=max_notional,
                            )
                    elif (
                        dispatch_snapshot is not None
                        and dispatch_snapshot.get("mode") == ExchangeMode.live.value
                    ):
                        # CF5 — live 는 balance 검증 불가(fetch 실패/0) 시 fail-closed (주문 거부).
                        # demo 는 fail-open(skip) 유지 (서비스 중단 금지 — 기존 정책).
                        _count_safely(
                            qb_order_rejected_total,
                            exchange=_metric_exchange,
                            reason="balance_unverified",
                        )
                        raise BalanceUnverified(account_id=req.exchange_account_id)
                elif (
                    req.price is None
                    and dispatch_snapshot is not None
                    and dispatch_snapshot.get("mode") == ExchangeMode.live.value
                ):
                    # P1-13 (S5-B) — market order + live + mark price 추정 실패 = fail-closed.
                    # demo 는 기존 정책대로 fail-open(skip — effective_price=None 이므로
                    # notional/available 분기 자체를 건너뜀).
                    _count_safely(
                        qb_order_rejected_total,
                        exchange=_metric_exchange,
                        reason="balance_unverified",
                    )
                    raise BalanceUnverified(account_id=req.exchange_account_id)

            # Sprint 7d: 전략의 trading_sessions 가드. 비어있으면 24h(통과). 채워진 값이면
            # 현재 UTC hour가 허용 세션 중 하나에 속해야 함. kill switch / advisory lock
            # 이전에 평가하여 DB 사이드이펙트 최소화.
            if self._sessions_port is not None:
                sessions = await self._sessions_port.get_sessions(req.strategy_id)
                now = datetime.now(UTC)
                if not _sessions_is_allowed(sessions, now):
                    _count_safely(
                        qb_order_rejected_total, exchange=_metric_exchange, reason="session_closed"
                    )
                    raise TradingSessionClosed(
                        sessions=sessions,
                        current_hour_utc=now.hour,
                    )

            # ── ASYNC-1: kill-switch gate — order INSERT savepoint *밖*에서 평가 ──
            # 신규 breach 시 ensure_not_gated 가 이벤트 INSERT + commit 후 KillSwitchActive
            # raise. begin_nested 안에서 호출하면 raise 가 savepoint 를 rollback 시켜 audit
            # row 가 유실되고, 매 주문마다 재평가 → alert storm (ASYNC-1). idempotent replay
            # (기존 order 존재) 는 gate skip → cached 반환.
            if idempotency_key is not None:
                pre_existing = await self._repo.get_by_idempotency_key(idempotency_key)
            else:
                pre_existing = None
            if pre_existing is None:
                try:
                    await self._kill_switch.ensure_not_gated(
                        strategy_id=req.strategy_id,
                        account_id=req.exchange_account_id,
                    )
                except KillSwitchActive:
                    # ★BL-580 — bare `raise` 앞이다. 여기서 던지면 KillSwitchActive 가
                    #   **삼켜지고** OSError 가 대신 올라가, 호출자
                    #   (`tasks/live_signal.py:3232` `except KillSwitchActive`) 의
                    #   mark_failed 가 안 돌고 차단된 주문이 3회 재시도된다.
                    #   고장 주입: `tests/trading/test_order_rejected_metric.py`.
                    _count_safely(
                        qb_order_rejected_total, exchange=_metric_exchange, reason="kill_switch"
                    )
                    raise

        created_order_id: UUID | None = None
        cached_response: OrderResponse | None = None

        async with self._session.begin_nested():
            if idempotency_key is not None:
                await self._repo.acquire_idempotency_lock(idempotency_key)
                existing = await self._repo.get_by_idempotency_key(idempotency_key)
                if existing:
                    if body_hash is not None and existing.idempotency_payload_hash != body_hash:
                        # ★BL-580 — BL 표는 이 자리를 「발주 **전** 검증 거절 직후」라 적었지만
                        #   실제로는 `begin_nested()` + advisory lock **안**이다. 그리고
                        #   `live_signal.py:3249` 는 이 타입일 때만 재시도 없이 종결한다.
                        _count_safely(
                            qb_order_rejected_total,
                            exchange=_metric_exchange,
                            reason="idempotency_conflict",
                        )
                        raise IdempotencyConflict(
                            f"Idempotency-Key 재사용됐지만 payload가 다름. "
                            f"original_order_id={existing.id}",
                            original_order_id=existing.id,
                        )
                    cached_response = OrderResponse.model_validate(existing)
                else:
                    # ASYNC-1: kill-switch gate 는 begin_nested 밖에서 이미 평가됨.
                    order = await self._repo.save(
                        Order(
                            strategy_id=req.strategy_id,
                            exchange_account_id=req.exchange_account_id,
                            symbol=req.symbol,
                            side=req.side,
                            type=req.type,
                            quantity=req.quantity,
                            price=req.price,
                            state=OrderState.pending,
                            idempotency_key=idempotency_key,
                            idempotency_payload_hash=body_hash,
                            # Sprint 7a: Futures. Spot은 모두 None.
                            leverage=req.leverage,
                            margin_mode=req.margin_mode,
                            # MP-1: close 주문의 청산 realized PnL → kill-switch SUM 대상.
                            realized_pnl=req.realized_pnl,
                            # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브.
                            reduce_only=req.reduce_only,
                            trigger_price=req.trigger_price,
                            trigger_by=req.trigger_by,
                            take_profit=req.take_profit,
                            stop_loss=req.stop_loss,
                            # Wave 2 (TP/SL placement) — triggerDirection/OCO/trailing.
                            trigger_direction=req.trigger_direction,
                            oco_group_id=req.oco_group_id,
                            trailing_stop=req.trailing_stop,
                            # Sprint 23 BL-102: dispatch snapshot (codex G.0 P1 #3 fix).
                            dispatch_snapshot=dispatch_snapshot,
                        )
                    )
                    created_order_id = order.id
            else:
                # ASYNC-1: kill-switch gate 는 begin_nested 밖에서 이미 평가됨.
                order = await self._repo.save(
                    Order(
                        strategy_id=req.strategy_id,
                        exchange_account_id=req.exchange_account_id,
                        symbol=req.symbol,
                        side=req.side,
                        type=req.type,
                        quantity=req.quantity,
                        price=req.price,
                        state=OrderState.pending,
                        idempotency_key=None,
                        idempotency_payload_hash=None,
                        # Sprint 7a: Futures. Spot은 모두 None.
                        leverage=req.leverage,
                        margin_mode=req.margin_mode,
                        # MP-1: close 주문의 청산 realized PnL → kill-switch SUM 대상.
                        realized_pnl=req.realized_pnl,
                        # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브.
                        reduce_only=req.reduce_only,
                        trigger_price=req.trigger_price,
                        trigger_by=req.trigger_by,
                        take_profit=req.take_profit,
                        stop_loss=req.stop_loss,
                        # Wave 2 (TP/SL placement) — triggerDirection/OCO/trailing.
                        trigger_direction=req.trigger_direction,
                        oco_group_id=req.oco_group_id,
                        trailing_stop=req.trailing_stop,
                        # Sprint 23 BL-102: dispatch snapshot (codex G.0 P1 #3 fix).
                        dispatch_snapshot=dispatch_snapshot,
                    )
                )
                created_order_id = order.id
        # begin_nested 의 context exit 은 SAVEPOINT release 만. outer transaction 은
        # 별도 commit 필요 — 누락 시 session.close() 시 ROLLBACK 으로 INSERT 가
        # 영구 저장 안 됨 (Sprint 6 webhook_secret broken bug 와 동일 패턴).
        # Sprint 13 dogfood Day 2 발견 hotfix.
        await self._session.commit()

        if cached_response is not None:
            return cached_response, True

        if created_order_id is None:
            raise RuntimeError("OrderService bug: created_order_id is None after insert")

        # Sprint 9 Phase D: 신규 pending 주문 생성 → active_orders gauge inc.
        # 터미널 전이 (filled/rejected/canceled) 시 tasks/trading.py 가 dec.
        record_metric_safely(qb_active_orders.inc)

        await self._dispatcher.dispatch_order_execution(created_order_id)
        fetched = await self._repo.get_by_id(created_order_id)
        if fetched is None:
            raise RuntimeError(f"OrderService bug: order {created_order_id} not found after commit")
        return OrderResponse.model_validate(fetched), False
