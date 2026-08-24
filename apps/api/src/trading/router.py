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

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.metrics import qb_active_orders
from src.common.metrics_multiproc import record_metric_safely
from src.trading.dependencies import (
    get_alert_rule_service,
    get_balance_service,
    get_close_service,
    get_exchange_account_service,
    get_kill_switch_service,
    get_liquidation_service,
    get_live_session_query_service,
    get_live_signal_session_service,
    get_order_service,
    get_outcome_parity_service,
    get_position_service,
    get_webhook_service,
)
from src.trading.exceptions import ProviderError
from src.trading.kill_switch import KillSwitchService
from src.trading.liquidation_schemas import (
    LiquidationInfoResponse,
    LiquidationPreviewRequest,
)
from src.trading.models import OrderState
from src.trading.outcome_parity_service import OutcomeParityService
from src.trading.realtime_publisher import publish_realtime
from src.trading.schemas import (
    AccountBalanceResponse,
    AccountPositionsResponse,
    AlertRuleCreateRequest,
    AlertRuleListResponse,
    AlertRuleResponse,
    ClosePositionConflictResponse,
    ClosePositionResponse,
    ExchangeAccountResponse,
    KillSwitchEventResponse,
    LiveSessionListResponse,
    LiveSessionPositionsResponse,
    LiveSessionResponse,
    LiveSignalEventListResponse,
    LiveSignalStateResponse,
    OrderRequest,
    OrderResponse,
    OutcomeParityResponse,
    PaginatedExchangeAccounts,
    RegisterAccountRequest,
    RegisterLiveSessionRequest,
)
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.alert_rule_service import AlertRuleService
from src.trading.services.balance_service import AccountBalanceService
from src.trading.services.close_service import ClosePositionService
from src.trading.services.liquidation_service import LiquidationService
from src.trading.services.live_session_query_service import LiveSessionQueryService
from src.trading.services.live_session_service import LiveSignalSessionService
from src.trading.services.order_service import OrderService
from src.trading.services.position_service import PositionService
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

    # ── 거래 파라미터 해결 (BL-474) ──
    # ★HMAC 검증 뒤여야 한다. 앞에 두면 미인증 호출자가 401/422 응답 차이만으로
    # 어느 strategy_id 에 settings 가 있는지 캐낼 수 있다.
    trading_params = await webhook_svc.resolve_trading_params(strategy_id)

    # ── Build OrderRequest ──
    # P1-12 (S5-A) — TV close-alert 가 realized_pnl 포함하면 OrderRequest 로 전파 →
    # OrderService 가 Order.realized_pnl 로 저장 → #305 kill-switch SUM(CumulativeLoss /
    # DailyLoss evaluator) 대상이 됨. 없으면 None (legacy backward-compat).
    #
    # BL-474 — leverage/margin_mode 는 Strategy.settings 에서(SSOT), reduce_only 와
    # TP/SL 은 payload 에서 온다. 이전엔 셋 다 누락돼 webhook 주문이 spot 으로
    # 나갔고, 그 체결은 linear 전용인 청산 원장·코크핏·exchange_exits 어디에도
    # 잡히지 않아 확정 손익을 영원히 못 받았다.
    req = OrderRequest(
        strategy_id=strategy_id,
        exchange_account_id=exchange_account_id,
        symbol=signal.symbol,
        side=signal.side,
        type=signal.type,
        quantity=signal.quantity,
        price=signal.price,
        realized_pnl=signal.realized_pnl,
        leverage=trading_params.leverage,
        margin_mode=trading_params.margin_mode,
        reduce_only=signal.reduce_only,
        take_profit=signal.take_profit,
        stop_loss=signal.stop_loss,
        risk_percent=signal.risk_percent,
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
    # ★[BL-762] 종전 여기에 `await svc._repo.commit()` 이 있었다 — `register()` 가
    #   `account_service.py:47` 에서 이미 커밋하므로 **중복 커밋**이었고, 그 한 줄 때문에
    #   「커밋 책임이 서비스에 있다」는 명제가 이 경로에서만 거짓이었다.
    return ExchangeAccountResponse(
        id=account.id,
        exchange=account.exchange,
        mode=account.mode,
        label=account.label,
        api_key_masked=svc.masked_api_key(account),
        exchange_uid=account.exchange_uid,
        read_only=account.read_only,
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
    accounts = await svc.list_for_user(current_user.id)
    items: list[ExchangeAccountResponse] = []
    for acct in accounts:
        items.append(
            ExchangeAccountResponse(
                id=acct.id,
                exchange=acct.exchange,
                mode=acct.mode,
                label=acct.label,
                api_key_masked=svc.masked_api_key(acct),
                exchange_uid=acct.exchange_uid,
                read_only=acct.read_only,
                created_at=acct.created_at,
            )
        )
    return PaginatedExchangeAccounts(items=items, total=len(items))


@router.get(
    "/exchange-accounts/{account_id}/balance",
    response_model=AccountBalanceResponse,
)
async def get_exchange_account_balance(
    account_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: AccountBalanceService = Depends(get_balance_service),
) -> AccountBalanceResponse:
    try:
        return await service.get_balance(current_user.id, account_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="exchange balance lookup unavailable") from exc


@router.get(
    "/exchange-accounts/{account_id}/positions",
    response_model=AccountPositionsResponse,
)
async def get_exchange_account_positions(
    account_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: PositionService = Depends(get_position_service),
) -> AccountPositionsResponse:
    """BL-498 — 활성 세션이 없어도 계정에 남은 거래소 포지션을 보여준다."""
    try:
        return await service.get_account_positions(current_user.id, account_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="exchange position lookup unavailable") from exc


@router.delete(
    "/exchange-accounts/{account_id}",
    status_code=204,
)
async def delete_exchange_account(
    account_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> None:
    # 소유권 검사·삭제·커밋은 서비스가 한 경계 안에서 소유한다 ([BL-762]).
    await svc.delete_for_user(account_id, current_user.id)


# ── Orders REST ──────────────────────────────────────────────────────


@router.get("/orders")
async def list_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    state: list[OrderState] | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> dict[str, object]:
    items, total = await service.list_for_user(
        current_user.id, limit=limit, offset=offset, states=state
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
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await service.get_for_user(order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return OrderResponse.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse | JSONResponse:
    """CF4: pending(거래소 미발주)은 즉시 DB cancel. submitted(거래소 live)은 DB-only flip
    금지 — cancel_order_task 가 거래소 취소 성공 시에만 cancelled 전이 (orphan position 방지)."""
    outcome = await service.cancel_for_user(order_id, current_user.id)
    if outcome.kind == "not_found":
        raise HTTPException(status_code=404, detail="order not found")
    if outcome.kind == "exchange_requested":
        return JSONResponse(
            status_code=202,
            content={
                "order_id": str(order_id),
                "state": OrderState.submitted.value,
                "detail": "exchange cancel requested",
            },
        )
    if outcome.kind == "conflict":
        raise HTTPException(status_code=409, detail="cannot cancel in current state")
    # Sprint 9 Phase D FIX-D1: cancel path 에서 gauge decrement
    # (service.execute 에서 +1 한 것을 cancelled terminal state 로 전이 시 -1).
    # ★BL-580 — `commit()` 뒤다. 여기서 던지면 **확정된 취소가 HTTP 500 으로 보고**된다
    #   (고장 주입 확인: `tests/trading/test_router_cancel_metric_failure.py`).
    record_metric_safely(qb_active_orders.dec)
    if outcome.order is None:
        raise HTTPException(status_code=500, detail="order fetch failed after cancel")
    return OrderResponse.model_validate(outcome.order)


# ── Liquidation preview (demo-only calc+display, 주문 차단 없음) ───────
@router.post("/liquidation/preview", response_model=LiquidationInfoResponse)
async def preview_liquidation(
    data: LiquidationPreviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: LiquidationService = Depends(get_liquidation_service),
) -> LiquidationInfoResponse:
    """청산가 미리보기 — on-the-fly 순수 계산. 소유 리소스 fetch 없음(인증만 게이트)."""
    return service.preview(data)


# ── KillSwitch REST ──────────────────────────────────────────────────


@router.get("/kill-switch/events")
async def list_kill_switch_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    service: KillSwitchService = Depends(get_kill_switch_service),
) -> dict[str, object]:
    """CF1: 호출자 소유(strategy/account) kill-switch 이벤트만 반환 (cross-tenant IDOR 차단)."""
    events = await service.list_events_for_user(current_user.id, limit=limit, offset=offset)
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
    service: KillSwitchService = Depends(get_kill_switch_service),
) -> KillSwitchEventResponse:
    raw_note = body.get("note")
    note = str(raw_note) if raw_note is not None else None
    outcome = await service.resolve_for_user(event_id, user_id=current_user.id, note=note)
    if outcome.kind == "not_owned":
        raise HTTPException(status_code=404, detail="event not found")
    if outcome.kind == "already_resolved":
        raise HTTPException(status_code=404, detail="event not found or already resolved")

    event = outcome.event
    if event is None:
        raise HTTPException(status_code=500, detail="event fetch failed after resolve")
    await publish_realtime(
        str(current_user.id),
        "kill_switch_resolved",
        {"event_id": str(event_id), "trigger_type": event.trigger_type.value},
    )
    return KillSwitchEventResponse.model_validate(event)


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
    include_inactive: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSignalSessionService = Depends(get_live_signal_session_service),
) -> LiveSessionListResponse:
    sessions = (
        await service.list_active_with_recent_inactive(current_user.id)
        if include_inactive
        else await service.list_active(current_user.id)
    )
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
    "/live-sessions/{session_id}/outcome-parity",
    response_model=OutcomeParityResponse,
)
async def get_live_session_outcome_parity(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: OutcomeParityService = Depends(get_outcome_parity_service),
) -> OutcomeParityResponse:
    """화면 진입 시 한 번 읽는 세션 및 전략 누적 parity 요약이다."""
    return await service.get_parity(current_user.id, session_id)


@router.get(
    "/live-sessions/{session_id}/state",
    response_model=LiveSignalStateResponse,
)
async def get_live_session_state(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSessionQueryService = Depends(get_live_session_query_service),
) -> LiveSignalStateResponse:
    """Sprint 26 — Live Session 의 last strategy_state_report + 누적 PnL.

    UI Detail 페이지의 PnL chart + warnings + open trades 표시용.

    2026-07-01 dogfood 발견 — `LiveSignalState.total_realized_pnl`/`equity_curve`
    는 매 evaluate tick 마다 300-bar Pine 시뮬레이션을 처음부터 재생한 결과라
    실제 거래소 체결 여부와 무관했다(리젝트된 주문도 시뮬레이션 손익을 그대로
    노출). `total_realized_pnl`/`total_closed_trades`/`equity_curve` 는 실제
    체결(state=filled) 주문만으로 재계산해 노출한다. `last_strategy_state_report` 는
    엔진이 파악하는 전략 내부 상태 표시 목적으로 그대로 유지한다.
    """
    state = await service.get_state_for_user(session_id, current_user.id)
    if state is None:
        raise HTTPException(status_code=404, detail="live session not found")
    return state


@router.get(
    "/live-sessions/{session_id}/positions",
    response_model=LiveSessionPositionsResponse,
)
async def get_live_session_positions(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: PositionService = Depends(get_position_service),
) -> LiveSessionPositionsResponse:
    try:
        return await service.get_reconciliation(current_user.id, session_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="exchange position lookup unavailable") from exc


@router.post(
    "/live-sessions/{session_id}/positions/close",
    status_code=202,
    response_model=ClosePositionResponse,
    responses={
        409: {
            "description": "포지션이 없거나 미체결 진입 주문이 남아 청산할 수 없습니다.",
            "model": ClosePositionConflictResponse,
        }
    },
)
async def close_live_session_position(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: ClosePositionService = Depends(get_close_service),
) -> ClosePositionResponse:
    try:
        return await service.close_position(current_user.id, session_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail="exchange position close unavailable") from exc


@router.get(
    "/live-sessions/{session_id}/events",
    response_model=LiveSignalEventListResponse,
)
async def list_live_session_events(
    session_id: UUID = Path(...),
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    service: LiveSessionQueryService = Depends(get_live_session_query_service),
) -> LiveSignalEventListResponse:
    """Sprint 26 — Live Session 의 outbox event log (debug + Detail UI 용)."""
    events = await service.list_events_for_user(session_id, current_user.id, limit=limit)
    if events is None:
        raise HTTPException(status_code=404, detail="live session not found")
    return events


@router.get(
    "/live-sessions/{session_id}/alert-rules",
    response_model=AlertRuleListResponse,
)
async def list_alert_rules(
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: AlertRuleService = Depends(get_alert_rule_service),
) -> AlertRuleListResponse:
    rules = await service.list_active(current_user.id, session_id)
    items = [AlertRuleResponse.model_validate(rule) for rule in rules]
    return AlertRuleListResponse(items=items, total=len(items))


@router.post(
    "/live-sessions/{session_id}/alert-rules",
    status_code=201,
    response_model=AlertRuleResponse,
)
async def create_alert_rule(
    data: AlertRuleCreateRequest,
    session_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: AlertRuleService = Depends(get_alert_rule_service),
) -> AlertRuleResponse:
    return AlertRuleResponse.model_validate(await service.create(current_user.id, session_id, data))


@router.delete(
    "/live-sessions/{session_id}/alert-rules/{rule_id}",
    status_code=204,
)
async def delete_alert_rule(
    session_id: UUID = Path(...),
    rule_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: AlertRuleService = Depends(get_alert_rule_service),
) -> None:
    await service.deactivate(current_user.id, session_id, rule_id)
