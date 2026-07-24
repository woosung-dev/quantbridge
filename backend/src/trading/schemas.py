"""trading 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.trading.models import (
    AlertChannel,
    AlertRuleType,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderState,
    OrderType,
)


class RegisterAccountRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exchange: ExchangeName
    mode: ExchangeMode
    api_key: str = Field(min_length=1, max_length=200)
    api_secret: str = Field(min_length=1, max_length=200)
    # Sprint 7d: OKX auth 3요소. Bybit/Binance는 생략 가능.
    passphrase: str | None = Field(default=None, min_length=1, max_length=200)
    label: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _require_passphrase_for_okx(self) -> RegisterAccountRequest:
        if self.exchange == ExchangeName.okx and not self.passphrase:
            raise ValueError("OKX accounts require a passphrase")
        return self


class ExchangeAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exchange: ExchangeName
    mode: ExchangeMode
    label: str | None
    api_key_masked: str
    created_at: AwareDatetime


class OrderRequest(BaseModel):
    """수동 주문 생성 또는 webhook payload에서 변환된 요청."""

    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal = Field(gt=0, decimal_places=8)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    # Sprint 7a: Futures. Spot은 모두 None.
    leverage: int | None = Field(default=None, ge=1, le=125)
    margin_mode: Literal["cross", "isolated"] | None = Field(default=None)
    # MP-1 — close 주문 청산 realized PnL (live-signal event-loop 계산). 손실은 음수이므로
    # 부호 제약 없음. kill-switch 가 Order.realized_pnl 을 SUM 하여 손실 차단기 작동.
    realized_pnl: Decimal | None = Field(default=None)
    # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브 (전부 optional).
    # default None/False = 기존 entry 주문 경로 회귀.
    reduce_only: bool = Field(default=False)
    trigger_price: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    trigger_by: str | None = Field(default=None, max_length=16)
    take_profit: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    stop_loss: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    # Wave 2 (TP/SL placement) — standalone 트리거/트레일링 라이브 param (전부 optional).
    # trigger_direction: Bybit v5 1=가격 RISE 시 트리거 / 2=FALL 시. SL/Trail standalone 방향.
    trigger_direction: int | None = Field(default=None, ge=1, le=2)
    # oco_group_id: OCO 형제 추적 app-side 식별자(거래소 미주입). sibling-cancel DB 조회용.
    oco_group_id: str | None = Field(default=None, max_length=64)
    # trailing_stop: Bybit native trailing 거리(quote). contract 전용.
    trailing_stop: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    # Wave 2 P2 — risk-based position sizing. 자본 x risk_percent% / |entry-stop| 로 서버가
    # max_qty 재계산해 client qty 초과 시 거부. None=가드 skip(회귀 0). 0<x<=100.
    risk_percent: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=4)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None
    state: OrderState
    idempotency_key: str | None
    exchange_order_id: str | None
    filled_price: Decimal | None
    error_message: str | None
    submitted_at: AwareDatetime | None
    filled_at: AwareDatetime | None
    created_at: AwareDatetime
    # Sprint 7a 추가 — Spot 경로는 None.
    leverage: int | None = None
    margin_mode: Literal["cross", "isolated"] | None = None
    # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브.
    reduce_only: bool = False
    trigger_price: Decimal | None = None
    trigger_by: str | None = None
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    # Wave 2 (TP/SL placement).
    trigger_direction: int | None = None
    oco_group_id: str | None = None
    trailing_stop: Decimal | None = None


class KillSwitchEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trigger_type: str
    strategy_id: UUID | None
    exchange_account_id: UUID | None
    trigger_value: Decimal
    threshold: Decimal
    triggered_at: AwareDatetime
    resolved_at: AwareDatetime | None
    resolution_note: str | None


class WebhookRotateResponse(BaseModel):
    secret: str
    webhook_url: str


class PaginationResponse(BaseModel):
    """Sprint 5 M4 pagination drift 준수."""

    total: int
    limit: int
    offset: int


def mask_api_key(plaintext: str) -> str:
    """앞 4자 + ****** + 뒤 4자. 길이 < 8인 경우 전부 마스킹."""
    if len(plaintext) < 8:
        return "*" * len(plaintext)
    return f"{plaintext[:4]}******{plaintext[-4:]}"


class PaginatedExchangeAccounts(BaseModel):
    items: list[ExchangeAccountResponse]
    total: int


class AccountBalanceResponse(BaseModel):
    """GET /exchange-accounts/{account_id}/balance 응답."""

    account_id: UUID
    asset: Literal["USDT"]
    supported: bool
    reason: str | None
    total: Decimal | None
    free: Decimal | None
    fetched_at: AwareDatetime | None


# ── Sprint 26: Live Signal Auto-Trading ────────────────────────────────────


class RegisterLiveSessionRequest(BaseModel):
    """POST /api/v1/live-sessions request body."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str = Field(min_length=1, max_length=32)
    interval: Literal["1m", "5m", "15m", "1h"]


class LiveSessionResponse(BaseModel):
    """Sprint 26 — Live Session 단일 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    interval: str
    is_active: bool
    last_evaluated_bar_time: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    deactivated_at: AwareDatetime | None


class LiveSessionListResponse(BaseModel):
    items: list[LiveSessionResponse]
    total: int


class AlertRuleCreateRequest(BaseModel):
    """POST /live-sessions/{id}/alert-rules 요청."""

    model_config = ConfigDict(extra="forbid")

    rule_type: AlertRuleType
    # 절대 손실률은 100%를 넘을 수 없으므로 DB NUMERIC overflow 전에 차단한다.
    threshold_percent: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=8)
    channel: AlertChannel

    @model_validator(mode="after")
    def _validate_type_threshold(self) -> AlertRuleCreateRequest:
        if self.rule_type == AlertRuleType.loss_limit and self.threshold_percent is None:
            raise ValueError("loss_limit rules require threshold_percent")
        if self.rule_type == AlertRuleType.watchdog and self.threshold_percent is not None:
            raise ValueError("watchdog rules must not set threshold_percent")
        return self


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    rule_type: AlertRuleType
    threshold_percent: Decimal | None
    channel: AlertChannel
    is_active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AlertRuleListResponse(BaseModel):
    items: list[AlertRuleResponse]
    total: int


class LiveSignalStateResponse(BaseModel):
    """GET /api/v1/live-sessions/{id}/state — Detail UI 용.

    Sprint 28 Slice 3 (BL-140b): equity_curve 신규 — cumulative realized PnL timeseries.
    형식: [{"timestamp_ms": int, "cumulative_pnl": str}, ...] ASC sorted by timestamp_ms.
    Frontend 가 dual-axis recharts (entries/closes + equity) 렌더 시 사용.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    evaluated: bool = True
    schema_version: int
    last_strategy_state_report: dict[str, object]
    total_closed_trades: int
    total_realized_pnl: Decimal
    equity_curve: list[dict[str, object]] = []  # Sprint 28 Slice 3 BL-140b
    updated_at: AwareDatetime | None


class LiveSignalEventResponse(BaseModel):
    """GET /api/v1/live-sessions/{id}/events — debug + UI 용."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    bar_time: AwareDatetime
    sequence_no: int
    action: str
    direction: str
    trade_id: str
    qty: Decimal
    comment: str
    status: str
    order_id: UUID | None
    error_message: str | None
    retry_count: int
    created_at: AwareDatetime
    dispatched_at: AwareDatetime | None


class LiveSignalEventListResponse(BaseModel):
    items: list[LiveSignalEventResponse]


class ExchangePositionSchema(BaseModel):
    """거래소에서 조회한 개별 open position leg."""

    side: str
    size: Decimal
    entry_price: Decimal | None
    mark_price: Decimal | None
    unrealized_pnl: Decimal | None
    liquidation_price: Decimal | None
    leverage: Decimal | None


class PositionDiffSchema(BaseModel):
    """로컬 Pine open trade와 거래소 포지션의 읽기 전용 대조 결과."""

    verdict: Literal[
        "match",
        "qty_mismatch",
        "side_mismatch",
        "exchange_only",
        "local_only",
        "unknown",
    ]
    local_source: Literal["strategy_state_report", "none"]


class LiveSessionPositionsResponse(BaseModel):
    """GET /live-sessions/{id}/positions 응답."""

    session_id: UUID
    symbol: str
    market_type: Literal["futures", "spot"]
    supported: bool
    reason: str | None
    fetched_at: AwareDatetime | None
    positions: list[ExchangePositionSchema]
    local_open_trades_snapshot: list[dict[str, object]]
    diff: PositionDiffSchema
