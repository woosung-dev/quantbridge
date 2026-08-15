"""trading 도메인 Pydantic V2 스키마."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.common.normalized_symbol import NormalizedSymbol
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
    exchange_uid: str | None
    read_only: bool | None
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
    filled_quantity: Decimal | None = None
    # realized_pnl_synced_at 비어 있지 않음 = 거래소가 확정한 net 손익(수수료 포함), 비어 있음 = pine_v2 추정값.
    realized_pnl: Decimal | None = None
    realized_pnl_synced_at: AwareDatetime | None = None
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


class RestingEntryOrder(BaseModel):
    """청산 시점에 거래소에 남아 있던 미체결 진입 주문 1건.

    trigger 주문뿐 아니라 **일반 지정가 진입도 포함**된다. provider 가 비-trigger
    `fetch_open_orders` 와 trigger 주문을 합쳐 반환하기 때문이다 — 이름을
    `Conditional…` 로 좁히지 마라.

    ★수량·가격은 `Decimal` 이다(§2 Decimal-first). 「JSONResponse 가 Decimal 을
    직렬화하지 못한다」는 제약은 **`response_model` 경로에 해당하지 않는다** — 그 경로는
    Pydantic 이 직렬화하고, 같은 파일의 `ExchangePositionSchema` 가 이미 `Decimal` 을
    그대로 낸다. 문자열이 필요한 것은 `HTTPException(detail=<raw dict>)` 로 나가는
    409 경로뿐이고, 거기서만 `str()` 로 담는다(`close_service.py`).
    """

    order_id: str
    side: str
    qty: Decimal | None = None
    trigger_price: Decimal | None = None
    order_link_id: str | None = None

    @classmethod
    def from_snapshot(cls, order: object) -> RestingEntryOrder:
        """`ConditionalOrderSnapshot` → 응답 모델. 409 dict 경로와 필드가 갈라지지 않게 한다."""
        return cls(
            order_id=order.order_id,  # type: ignore[attr-defined]
            side=order.side,  # type: ignore[attr-defined]
            qty=order.qty,  # type: ignore[attr-defined]
            trigger_price=order.trigger_price,  # type: ignore[attr-defined]
            order_link_id=order.order_link_id,  # type: ignore[attr-defined]
        )


class ClosePositionResponse(BaseModel):
    order_id: UUID
    state: OrderState
    detail: str | None = None
    resting_entries: list[RestingEntryOrder] = []
    # 빈 목록만으로는 "잔량 없음"과 "거래소 조회 실패"를 구분할 수 없다.
    resting_entries_unknown: bool = False


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
    # BL-454 — canonical(`BTC/USDT`) 로 정규화해 저장한다. 세션 손익 스코프가
    # `Order.symbol` 과 **정확 문자열 동등**을 쓰므로(`order_repository._session_scope_where`),
    # 표기가 어긋난 주문은 세션 합계에서 조용히 빠지고 loss-limit 알림이 fail-open 한다.
    # 정규화 불가 표기는 Pydantic 이 422 로 거부한다(신규 예외 배관 없음).
    symbol: NormalizedSymbol = Field(min_length=1, max_length=32)
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
    # BL-484 — 왜 죽었는지. 값 집합은 `SessionDeactivationReason` 이 정본이고 화면이
    # 한국어로 옮긴다. 마이그레이션 이전에 죽은 세션은 None (사유 미기록) 이다.
    deactivated_reason: str | None = None
    equity_baseline_usdt: Decimal | None = None


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
    # BL-458 — 출처 소계. `total_realized_pnl` 은 여전히 **둘을 합친 값**이다(필터가
    # 아니라 라벨이다). 항등식 `confirmed + estimated == total` 을 테스트로 고정한다.
    # 추정을 합계에서 빼면 체결부터 스윕 도착까지의 손실이 통째로 사라져 fail-open 한다.
    confirmed_realized_pnl: Decimal = Decimal("0")
    estimated_realized_pnl: Decimal = Decimal("0")
    confirmed_closed_trades: int = 0
    estimated_closed_trades: int = 0
    equity_curve: list[dict[str, object]] = []  # Sprint 28 Slice 3 BL-140b
    updated_at: AwareDatetime | None


class OutcomeParityScope(BaseModel):
    """한 스코프(세션 또는 전략 누적)의 parity 요약이다.

    `round_trip_notional`은 두 leg 합이므로 이를 분모로 한 비용률은 편도다. 왕복 비용
    가정과 비교할 소비자는 `effective_cost_pct_round_trip`만 사용해야 한다.

    `edge_pct_round_trip`와 `cost_to_edge_ratio`는 표본 충분성과 무관하게 계산된다.
    소비자는 두 비율을 표시하기 전에 `ratio_sample_sufficient`를 반드시 확인해야 한다.
    """

    matched_count: int
    expected_gross: Decimal
    actual_net: Decimal
    decomposable_count: int
    decomposable_expected_gross: Decimal | None
    execution_gap: Decimal | None
    cost: Decimal | None
    decomposable_actual_net: Decimal | None
    actual_gross: Decimal | None
    round_trip_notional: Decimal | None
    effective_cost_pct_per_leg: Decimal | None
    effective_cost_pct_round_trip: Decimal | None
    edge_pct_round_trip: Decimal | None
    cost_to_edge_ratio: Decimal | None
    undecomposed_count: int
    undecomposed_net: Decimal
    expected_only_count: int
    expected_only_gross: Decimal
    expected_only_pending_count: int
    expected_only_failed_count: int
    expected_only_dispatched_count: int
    actual_only_count: int
    actual_only_net: Decimal
    ledger_only_count: int
    ledger_only_net: Decimal
    inferred_attribution_count: int
    match_coverage_pct: Decimal | None
    decomposition_coverage_pct: Decimal | None
    sample_n: int
    sample_mean_net: Decimal | None
    sample_sd_net: Decimal | None
    sample_required_n: int | None
    sample_sufficient: bool
    ratio_sample_n: int
    ratio_sample_required_n: int | None
    ratio_sample_sufficient: bool


class OutcomeParityAssumption(BaseModel):
    """비교 기준 비용 가정이다.

    `source="house_default"`는 BacktestConfig 기본값이며 사용자의 백테스트 설정과
    다를 수 있다. `implied_round_trip_pct`는 taker 왕복 기준이라 TP resting limit
    leg의 maker 수수료와 슬리피지 면제를 반영하지 못해 그 경우 비용을 과대계상한다.
    """

    source: Literal["house_default"]
    taker_fee_pct: Decimal
    slippage_pct: Decimal
    maker_fee_pct: Decimal
    implied_round_trip_pct: Decimal


class OutcomeParityResponse(BaseModel):
    """한 라이브 세션과 전략 누적 parity를 함께 반환한다."""

    session_id: UUID
    session: OutcomeParityScope
    strategy: OutcomeParityScope
    unattributed_count: int
    inferred_attribution_count: int
    ledger_supported: bool
    strategy_session_count: int
    assumption: OutcomeParityAssumption


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
    # 이벤트 dispatch 성공과 거래소 주문 수락은 다른 사건이다. 이 값이 없으면 거절된 청산이
    # 화면에서 성공으로 보인다. None은 주문이 아직 없거나 연결되지 않았음을 뜻하며 성공이 아니다.
    order_state: str | None = None
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
    take_profit_prices: list[str]
    stop_loss_prices: list[str]
    has_trailing_stop: bool


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


class AccountPositionRow(BaseModel):
    """BL-498 — 계정에 남아 있는 거래소 포지션 한 줄.

    `closable_session_id` 는 이 계정·심볼로 만든 **가장 최근 세션**(비활성 포함)이다.
    수동 청산은 주문 원장에 기록되고 `Order.strategy_id` 가 NOT NULL 이므로,
    귀속할 세션이 없으면 청산을 제공하지 않고 `close_blocked_reason` 을 남긴다.
    """

    symbol: str
    position: ExchangePositionSchema
    closable_session_id: UUID | None
    close_blocked_reason: (
        Literal[
            "no_owning_session",
            "hedge_unsupported",
            "read_only_key",
            "position_side_unsupported",
        ]
        | None
    )


class AccountPositionsResponse(BaseModel):
    """GET /exchange-accounts/{account_id}/positions 응답.

    세션 스코프 대조(`LiveSessionPositionsResponse`)와 용도가 다르다 — 그쪽은
    발산 감지이고 이쪽은 **잔여 노출 관리**다. 활성 세션이 0건이어도 렌더된다.
    """

    account_id: UUID
    supported: bool
    reason: str | None
    fetched_at: AwareDatetime | None
    rows: list[AccountPositionRow]
    # 조회 범위 고지 — ccxt bybit 는 심볼 없는 조회에서 settleCoin 을 USDT 로
    # 채우므로 USDC 정산 linear 와 inverse 는 여기 잡히지 않는다.
    settle_coin: str
    # 거래소가 "더 있다"(nextPageCursor)고 말했는가. True 면 이 목록이 전부가 아니다.
    truncated: bool
