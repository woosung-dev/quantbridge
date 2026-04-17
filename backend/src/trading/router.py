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
from src.trading.dependencies import (
    get_exchange_account_service,
    get_order_service,
    get_webhook_service,
)
from src.trading.repository import (
    ExchangeAccountRepository,
    KillSwitchEventRepository,
    OrderRepository,
)
from src.trading.schemas import (
    ExchangeAccountResponse,
    KillSwitchEventResponse,
    OrderRequest,
    OrderResponse,
    PaginatedExchangeAccounts,
    RegisterAccountRequest,
    mask_api_key,
)
from src.trading.service import ExchangeAccountService, OrderService
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
    await webhook_svc.ensure_authorized(
        strategy_id, token=token, payload=body_bytes
    )

    # ── Parse TV payload ──
    import json

    payload_dict: dict[str, object] = json.loads(body_bytes)
    signal = parse_tv_payload(payload_dict)

    # extract exchange_account_id from payload body
    exchange_account_id_raw = payload_dict.get("exchange_account_id")
    if exchange_account_id_raw is None:
        raise HTTPException(
            422, "Missing required field: exchange_account_id"
        )
    exchange_account_id = UUID(str(exchange_account_id_raw))

    # ── Build OrderRequest ──
    req = OrderRequest(
        strategy_id=strategy_id,
        exchange_account_id=exchange_account_id,
        symbol=signal.symbol,
        side=signal.side,
        type=signal.type,
        quantity=signal.quantity,
        price=signal.price,
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
    items, total = await repo.list_by_user(
        current_user.id, limit=limit, offset=offset
    )
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
) -> OrderResponse:
    """Sprint 6은 DB 상태만 cancelled로 전이. exchange 취소는 Sprint 7+."""
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

    rowcount = await repo.transition_to_cancelled(
        order_id, cancelled_at=datetime.now(UTC)
    )
    await repo.commit()
    if rowcount == 0:
        raise HTTPException(
            status_code=409, detail="cannot cancel in current state"
        )
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
    """Sprint 6: all events (no user scope filter — read-only audit purpose)."""
    repo = KillSwitchEventRepository(session)
    events = await repo.list_recent(limit=limit, offset=offset)
    return {
        "items": [
            KillSwitchEventResponse.model_validate(e).model_dump(mode="json")
            for e in events
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
    raw_note = body.get("note")
    note = str(raw_note) if raw_note is not None else None
    rowcount = await repo.resolve(event_id, note=note)
    await repo.commit()
    if rowcount == 0:
        raise HTTPException(
            status_code=404, detail="event not found or already resolved"
        )
    fetched = await repo.get_by_id(event_id)
    if not fetched:
        raise HTTPException(
            status_code=500, detail="event fetch failed after resolve"
        )
    return KillSwitchEventResponse.model_validate(fetched)
