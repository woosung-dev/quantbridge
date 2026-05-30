"""trading HTTP 라우터 — ExchangeAccount + Webhook + Orders + KillSwitch endpoints.

URL prefix 없음 — main.py에서 /api/v1로 include.
T19: Webhook POST (public, HMAC auth) + CSO-6 body cap.
T20: Orders (list/get/cancel) + KillSwitch (events/resolve) REST endpoints.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.database import get_async_session
from src.common.metrics import qb_active_orders
from src.trading.dependencies import (
    get_exchange_account_service,
    get_live_signal_session_service,
    get_order_service,
    get_webhook_service,
)
from src.trading.models import OrderState
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import (
    ExchangeAccountResponse,
    KillSwitchEventResponse,
    LiveSessionListResponse,
    LiveSessionResponse,
    LiveSignalEventListResponse,
    LiveSignalEventResponse,
    LiveSignalStateResponse,
    OrderRequest,
    OrderResponse,
    PaginatedExchangeAccounts,
    RegisterAccountRequest,
    RegisterLiveSessionRequest,
    mask_api_key,
)
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.live_session_service import LiveSignalSessionService
from src.trading.services.order_service import OrderService
from src.trading.webhook import WebhookService, parse_tv_payload

router = APIRouter(tags=["trading"])

# CSO-6: webhook body size cap (64 KB)
MAX_WEBHOOK_BODY = 64 * 1024


# ── Webhook POST (PUBLIC — no JWT, HMAC is the auth) ──────────────────


@router.post(
    "/webhooks/{strategy_id}",
    status_code=201,
    response_model=OrderResponse,
)
async def receive_webhook(
    request: Request,
    strategy_id: UUID = Path(...),
    token: str = Query(..., description="HMAC-SHA256 hex digest"),
    idempotency_key: str | None = Query(None, alias="Idempotency-Key"),
    webhook_svc: WebhookService = Depends(get_webhook_service),
    order_svc: OrderService = Depends(get_order_service),
) -> OrderResponse | JSONResponse:
    """TradingView webhook receiver.

    - CSO-6: Content-Length + post-read body size cap
    - HMAC token verification (WebhookService.ensure_authorized)
    - TV payload parsing -> OrderRequest -> OrderService.execute
    - Idempotency: body_hash (SHA-256) for E2 conflict detection
    """
    # ── CSO-6: body size guard ──
    content_length = int(request.headers.get("content-length", 0))
    if content_length > MAX_WEBHOOK_BODY:
        raise HTTPException(413, f"body too large (max {MAX_WEBHOOK_BODY}B)")

    body_bytes = await request.body()
    if len(body_bytes) > MAX_WEBHOOK_BODY:
        raise HTTPException(413, "body too large")

    # ── HMAC verification ──
    await webhook_svc.ensure_authorized(strategy_id, token=token, payload=body_bytes)

    # ── Parse TV payload ──
    import json

    payload_dict: dict[str, object] = json.loads(body_bytes)
    signal = parse_tv_payload(payload_dict)

    # extract exchange_account_id from payload body
    exchange_account_id_raw = payload_dict.get("exchange_account_id")
    if exchange_account_id_raw is None:
        raise HTTPException(422, "Missing required field: exchange_account_id")
    exchange_account_id = UUID(str(exchange_account_id_raw))

    # ── Build OrderRequest ──
    # P1-12 (S5-A) — TV close-alert 가 realized_pnl 포함하면 OrderRequest 로 전파 →
    # OrderService 가 Order.realized_pnl 로 저장 → #305 kill-switch SUM(CumulativeLoss /
    # DailyLoss evaluator) 대상이 됨. 없으면 None (legacy backward-compat).
    req = OrderRequest(
        strategy_id=strategy_id,
        exchange_account_id=exchange_account_id,
        symbol=signal.symbol,
        side=signal.side,
        type=signal.type,
        quantity=signal.quantity,
        price=signal.price,
        realized_pnl=signal.realized_pnl,
    )

    # ── Execute order (tuple unpack: T15 correction) ──
    body_hash = hashlib.sha256(body_bytes).digest() if idempotency_key else None
    response, is_replayed = await order_svc.execute(
        req,
        idempotency_key=idempotency_key,
        body_hash=body_hash,
    )

    if is_replayed:
        return JSONResponse(
            status_code=200,
            content=response.model_dump(mode="json"),
            headers={"Idempotency-Replayed": "true"},
        )
    return response  # 201 via status_code on route


# ── ExchangeAccount CRUD ──────────────────────────────────────────────


@router.post(
    "/exchange-accounts",
    status_code=201,
    response_model=ExchangeAccountResponse,
)
async def register_exchange_account(
    body: RegisterAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> ExchangeAccountResponse:
    account = await svc.register(user_id=current_user.id, req=body)
    await svc._repo.commit()
    # Decrypt api_key for masking (plain text never stored, only encrypted)
    plaintext_key = svc._crypto.decrypt(account.api_key_encrypted)
    return ExchangeAccountResponse(
        id=account.id,
        exchange=account.exchange,
        mode=account.mode,
        label=account.label,
        api_key_masked=mask_api_key(plaintext_key),
        created_at=account.created_at,
    )


@router.get(
    "/exchange-accounts",
    response_model=PaginatedExchangeAccounts,
)
async def list_exchange_accounts(
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> PaginatedExchangeAccounts:
    accounts = await svc._repo.list_by_user(current_user.id)
    items: list[ExchangeAccountResponse] = []
    for acct in accounts:
        plaintext_key = svc._crypto.decrypt(acct.api_key_encrypted)
        items.append(
            ExchangeAccountResponse(
                id=acct.id,
                exchange=acct.exchange,
                mode=acct.mode,
                label=acct.label,
                api_key_masked=mask_api_key(plaintext_key),
                created_at=acct.created_at,
            )
        )
    return PaginatedExchangeAccounts(items=items, total=len(items))


@router.delete(
    "/exchange-accounts/{account_id}",
    status_code=204,
)
async def delete_exchange_account(
    account_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> None:
    # Ownership check: only delete if the account belongs to the current user
    account = await svc._repo.get_by_id(account_id)
    if account is None or account.user_id != current_user.id:
        from src.trading.exceptions import AccountNotFound

        raise AccountNotFound(account_id)
    await svc._repo.delete(account_id)
    await svc._repo.commit()


# ── Orders REST ──────────────────────────────────────────────────────


@router.get("/orders")
async def list_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, object]:
    repo = OrderRepository(session)
    items, total = await repo.list_by_user(current_user.id, limit=limit, offset=offset)
    return {
        "items": [OrderResponse.model_validate(o).model_dump(mode="json") for o in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrderResponse:
    order_repo = OrderRepository(session)
    acc_repo = ExchangeAccountRepository(session)

    order = await order_repo.get_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    acc = await acc_repo.get_by_id(order.exchange_account_id)
    if acc is None or acc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="order not found")
    return OrderResponse.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrderResponse | JSONResponse:
    """CF4: pending(거래소 미발주)은 즉시 DB cancel. submitted(거래소 live)은 DB-only flip
    금지 — cancel_order_task 가 거래소 취소 성공 시에만 cancelled 전이 (orphan position 방지)."""
    from datetime import UTC, datetime

    repo = OrderRepository(session)
    acc_repo = ExchangeAccountRepository(session)

    order = await repo.get_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    # Ownership check
    acc = await acc_repo.get_by_id(order.exchange_account_id)
    if acc is None or acc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="order not found")

    # CF4: submitted 주문은 거래소에 live 가능 → DB-only cancel 금지. 거래소 취소 task 위임.
    if order.state == OrderState.submitted:
        from src.tasks.trading import cancel_order_task

        cancel_order_task.delay(str(order_id))
        return JSONResponse(
            status_code=202,
            content={
                "order_id": str(order_id),
                "state": OrderState.submitted.value,
                "detail": "exchange cancel requested",
            },
        )

    # pending(거래소 미발주)만 즉시 DB cancel — state==pending 조건부 (pending→submitted
    # race 시 거래소 live 주문을 cancel 하지 않도록). terminal/raced → rowcount 0 → 409.
    rowcount = await repo.transition_pending_to_cancelled(order_id, cancelled_at=datetime.now(UTC))
    await repo.commit()
    if rowcount == 0:
        raise HTTPException(status_code=409, detail="cannot cancel in current state")
    # Sprint 9 Phase D FIX-D1: cancel path 에서 gauge decrement
    # (service.execute 에서 +1 한 것을 cancelled terminal state 로 전이 시 -1).
    qb_active_orders.dec()
    fetched = await repo.get_by_id(order_id)
    if not fetched:
        raise HTTPException(status_code=500, detail="order fetch failed after cancel")
    return OrderResponse.model_validate(fetched)


# ── KillSwitch REST ──────────────────────────────────────────────────


@router.get("/kill-switch/events")
async def list_kill_switch_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, object]:
    """CF1: 호출자 소유(strategy/account) kill-switch 이벤트만 반환 (cross-tenant IDOR 차단)."""
    repo = KillSwitchEventRepository(session)
    events = await repo.list_recent_by_user(
        user_id=current_user.id, limit=limit, offset=offset
    )
    return {
        "items": [
            KillSwitchEventResponse.model_validate(e).model_dump(mode="json") for e in events
        ],
        "total": len(events),
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/kill-switch/events/{event_id}/resolve",
    response_model=KillSwitchEventResponse,
)
async def resolve_kill_switch(
    event_id: UUID = Path(...),
    body: dict[str, object] = Body(default={}),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> KillSwitchEventResponse:
    repo = KillSwitchEventRepository(session)
    # CF1: ownership gate — 호출자 소유 이벤트가 아니면 404 (타 tenant safety gate 해제 차단).
    owned = await repo.get_owned(event_id, user_id=current_user.id)
    if owned is None:
        raise HTTPException(status_code=404, detail="event not found")
    raw_note = body.get("note")
    note = str(raw_note) if raw_note is not None else None
    rowcount = await repo.resolve(event_id, note=note)
    await repo.commit()
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="event not found or already resolved")
    fetched = await repo.get_by_id(event_id)
    if not fetched:
        raise HTTPException(status_code=500, detail="event fetch failed after resolve")
    return KillSwitchEventResponse.model_validate(fetched)


# ── Sprint 26: Live Signal Auto-Trading ────────────────────────────────────


@router.post("/live-sessions", status_code=201, response_model=LiveSessionResponse)
async def create_live_session(
    data: RegisterLiveSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSignalSessionService = Depends(get_live_signal_session_service),
) -> LiveSessionResponse:
    """Sprint 26 — Live Session 등록.

    Bybit Demo 한정 (BL-003 mainnet runbook 완료 전까지). 사용자별 ≤ 5 active.
    Strategy.settings (leverage/margin_mode/position_size_pct) 사전 설정 의무.
    """
    sess = await service.register(current_user.id, data)
    return LiveSessionResponse.model_validate(sess)


@router.get("/live-sessions", response_model=LiveSessionListResponse)
async def list_live_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSignalSessionService = Depends(get_live_signal_session_service),
) -> LiveSessionListResponse:
    sessions = await service.list_active(current_user.id)
    items = [LiveSessionResponse.model_validate(s) for s in sessions]
    return LiveSessionListResponse(items=items, total=len(items))


@router.delete("/live-sessions/{session_id}", status_code=204)
async def delete_live_session(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSignalSessionService = Depends(get_live_signal_session_service),
) -> None:
    await service.deactivate(current_user.id, session_id)


@router.get(
    "/live-sessions/{session_id}/state",
    response_model=LiveSignalStateResponse,
)
async def get_live_session_state(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> LiveSignalStateResponse:
    """Sprint 26 — Live Session 의 last strategy_state_report + 누적 PnL.

    UI Detail 페이지의 PnL chart + warnings + open trades 표시용.
    """
    repo = LiveSignalSessionRepository(session)
    sess = await repo.get_by_id(session_id)
    if sess is None or sess.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="live session not found")
    state = await repo.get_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="live signal state not yet evaluated")
    return LiveSignalStateResponse.model_validate(state)


@router.get(
    "/live-sessions/{session_id}/events",
    response_model=LiveSignalEventListResponse,
)
async def list_live_session_events(
    session_id: UUID = Path(...),
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> LiveSignalEventListResponse:
    """Sprint 26 — Live Session 의 outbox event log (debug + Detail UI 용)."""
    sess_repo = LiveSignalSessionRepository(session)
    sess = await sess_repo.get_by_id(session_id)
    if sess is None or sess.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="live session not found")
    event_repo = LiveSignalEventRepository(session)
    events = await event_repo.list_by_session(session_id, limit=limit)
    return LiveSignalEventListResponse(
        items=[LiveSignalEventResponse.model_validate(e) for e in events]
    )
