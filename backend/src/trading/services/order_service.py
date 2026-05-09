# trading service — Order 실행 + advisory lock + idempotency 단독 책임

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,  # 예외적 주입 — OrderService.execute advisory lock 전용
)

from src.common.metrics import qb_active_orders, qb_order_rejected_total
from src.core.config import settings
from src.strategy.trading_sessions import is_allowed as _sessions_is_allowed
from src.trading.exceptions import (
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    NotionalExceeded,
    TradingSessionClosed,
)
from src.trading.kill_switch import KillSwitchService
from src.trading.models import Order, OrderState
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest, OrderResponse
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.protocols import OrderDispatcher, StrategySessionsPort

logger = logging.getLogger(__name__)


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

    async def execute(
        self,
        req: OrderRequest,
        *,
        idempotency_key: str | None,
        body_hash: bytes | None = None,
    ) -> tuple[OrderResponse, bool]:
        """Sprint 11 Phase E — idempotency_key 가 있을 때 Service-level RedisLock 감싸기.
        실질 분산 mutex. Redis 장애 시 graceful degrade → PG advisory 가 권위.
        """
        if idempotency_key is None:
            return await self._execute_inner(req, idempotency_key=None, body_hash=None)

        from src.common.redlock import RedisLock

        async with RedisLock(f"idem:trading:{idempotency_key}", ttl_ms=30_000):
            return await self._execute_inner(
                req, idempotency_key=idempotency_key, body_hash=body_hash
            )

    async def _execute_inner(
        self,
        req: OrderRequest,
        *,
        idempotency_key: str | None,
        body_hash: bytes | None,
    ) -> tuple[OrderResponse, bool]:
        """Returns (response, is_replayed).

        Flow (autoplan E9 + E2):
        1. leverage cap 가드 (Sprint 7a 서비스 계층 enforcement)
        2. notional check (Sprint 8+ exchange_service 주입 시)
        3. begin_nested() — advisory lock + gate + insert 동일 tx
        4. idempotency 경로: lock → existing 확인 → hash 비교 → gate → INSERT
        5. commit 후 Celery dispatch (visibility race 방지)
        """
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

        # Sprint 7a: OrderRequest.leverage Field(le=125)는 Bybit 이론 상한.
        # 운영 리스크 관리용 동적 cap은 서비스 계층에서 enforce (4/4 리뷰 컨센서스).
        if req.leverage is not None and req.leverage > settings.bybit_futures_max_leverage:
            qb_order_rejected_total.labels(exchange=_metric_exchange, reason="leverage_cap").inc()
            raise LeverageCapExceeded(
                requested=req.leverage,
                cap=settings.bybit_futures_max_leverage,
            )

        # Sprint 8+ (2026-04-20): notional check. exchange_service 주입 + leverage + price
        # 모두 존재할 때만 enforce. market order(price=None)는 이 게이트 건너뜀 — 진입가
        # 불확실성 때문에 leverage cap으로만 1차 방어. fetch_balance 실패 시 None 반환
        # 하므로 fallback (서비스 중단 금지).
        if (
            self._exchange_service is not None
            and req.leverage is not None
            and req.price is not None
        ):
            available = await self._exchange_service.fetch_balance_usdt(req.exchange_account_id)
            if available is not None and available > Decimal("0"):
                notional = req.quantity * req.price * Decimal(req.leverage)
                max_notional = (
                    available * Decimal(settings.bybit_futures_max_leverage) * Decimal("0.95")
                )
                if notional > max_notional:
                    qb_order_rejected_total.labels(
                        exchange=_metric_exchange, reason="notional"
                    ).inc()
                    raise NotionalExceeded(
                        notional=notional,
                        available=available,
                        leverage=req.leverage,
                        max_notional=max_notional,
                    )

        # Sprint 7d: 전략의 trading_sessions 가드. 비어있으면 24h(통과). 채워진 값이면
        # 현재 UTC hour가 허용 세션 중 하나에 속해야 함. kill switch / advisory lock
        # 이전에 평가하여 DB 사이드이펙트 최소화.
        if self._sessions_port is not None:
            sessions = await self._sessions_port.get_sessions(req.strategy_id)
            now = datetime.now(UTC)
            if not _sessions_is_allowed(sessions, now):
                qb_order_rejected_total.labels(
                    exchange=_metric_exchange, reason="session_closed"
                ).inc()
                raise TradingSessionClosed(
                    sessions=sessions,
                    current_hour_utc=now.hour,
                )

        created_order_id: UUID | None = None
        cached_response: OrderResponse | None = None

        async with self._session.begin_nested():
            if idempotency_key is not None:
                await self._repo.acquire_idempotency_lock(idempotency_key)
                existing = await self._repo.get_by_idempotency_key(idempotency_key)
                if existing:
                    if body_hash is not None and existing.idempotency_payload_hash != body_hash:
                        qb_order_rejected_total.labels(
                            exchange=_metric_exchange, reason="idempotency_conflict"
                        ).inc()
                        raise IdempotencyConflict(
                            f"Idempotency-Key 재사용됐지만 payload가 다름. "
                            f"original_order_id={existing.id}",
                            original_order_id=existing.id,
                        )
                    cached_response = OrderResponse.model_validate(existing)
                else:
                    try:
                        await self._kill_switch.ensure_not_gated(
                            strategy_id=req.strategy_id,
                            account_id=req.exchange_account_id,
                        )
                    except KillSwitchActive:
                        qb_order_rejected_total.labels(
                            exchange=_metric_exchange, reason="kill_switch"
                        ).inc()
                        raise
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
                            # Sprint 23 BL-102: dispatch snapshot (codex G.0 P1 #3 fix).
                            dispatch_snapshot=dispatch_snapshot,
                        )
                    )
                    created_order_id = order.id
            else:
                try:
                    await self._kill_switch.ensure_not_gated(
                        strategy_id=req.strategy_id,
                        account_id=req.exchange_account_id,
                    )
                except KillSwitchActive:
                    qb_order_rejected_total.labels(
                        exchange=_metric_exchange, reason="kill_switch"
                    ).inc()
                    raise
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
        qb_active_orders.inc()

        await self._dispatcher.dispatch_order_execution(created_order_id)
        fetched = await self._repo.get_by_id(created_order_id)
        if fetched is None:
            raise RuntimeError(f"OrderService bug: order {created_order_id} not found after commit")
        return OrderResponse.model_validate(fetched), False
