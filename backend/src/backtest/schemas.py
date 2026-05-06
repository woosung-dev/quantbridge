"""Backtest 도메인 Pydantic V2 스키마 — Request/Response DTOs."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.backtest.models import BacktestStatus, TradeDirection, TradeStatus

# --- Request ---

class CreateBacktestRequest(BaseModel):
    """POST /backtests body.

    Sprint 29 codex G2 P0 fix: `allow_degraded_pine` 명시 동의 — Trust Layer 의도적 위반
    함수 (heikinashi / request.security / timeframe.period) 사용 strategy 의 backtest 는
    본 flag 없이는 422 reject. dogfood-first 정합 (사용자가 거짓 양성 risk 명시 인지).

    Sprint 31 BL-162a — TradingView strategy 속성 패턴 대응. 비용 시뮬레이션
    + 마진 사용자 입력 (leverage / fees_pct / slippage_pct / include_funding)
    추가. AssumptionsCard 가 default 표시 → 사용자 입력 시 실제값 graceful upgrade.
    default = Bybit Perpetual taker 표준 (1x 현물 + 0.1% 수수료 + 0.05%
    슬리피지 + 펀딩 ON).
    """

    strategy_id: UUID
    symbol: str = Field(min_length=3, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    period_start: AwareDatetime
    period_end: AwareDatetime
    initial_capital: Decimal = Field(gt=Decimal("0"), max_digits=20, decimal_places=8)
    # Sprint 29 codex G2 P0 — degraded Pine semantic 명시 동의. default False (안전 fallback).
    allow_degraded_pine: bool = False
    # Sprint 31 BL-162a — 비용 시뮬레이션 + 마진 사용자 입력 (TradingView 패턴).
    # leverage 1.0 = 현물, >1.0 = 선물. Bybit 표준 max 125x.
    leverage: Decimal = Field(
        default=Decimal("1.0"),
        ge=Decimal("1.0"),
        le=Decimal("125.0"),
        max_digits=6,
        decimal_places=2,
    )
    # 수수료 0 ~ 1% (Bybit/OKX taker 표준 0.10%).
    fees_pct: Decimal = Field(
        default=Decimal("0.001"),
        ge=Decimal("0"),
        le=Decimal("0.01"),
        max_digits=6,
        decimal_places=5,
    )
    # 슬리피지 0 ~ 1% (호가창 평균 0.05%).
    slippage_pct: Decimal = Field(
        default=Decimal("0.0005"),
        ge=Decimal("0"),
        le=Decimal("0.01"),
        max_digits=6,
        decimal_places=5,
    )
    # 펀딩비 반영 ON/OFF (8h 무기한 선물).
    include_funding: bool = True
    # Sprint 37 BL-188a — 폼 입력 default_qty (Pine 미명시 시 사용).
    # priority chain: Pine strategy(default_qty_type=...) > 폼 입력 > 시스템 default (1.0)
    # default_qty_type=None 시 system fallback (qty=1.0). 사용자 명시 시 backtest engine
    # configure_sizing(default_qty_type, default_qty_value) 호출.
    default_qty_type: Literal[
        "strategy.percent_of_equity", "strategy.cash", "strategy.fixed"
    ] | None = None
    default_qty_value: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=8,
    )

    @model_validator(mode="after")
    def _validate_period(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self

    @model_validator(mode="after")
    def _validate_default_qty(self) -> Self:
        # 둘 다 명시되거나 둘 다 None — 일관성.
        if (self.default_qty_type is None) != (self.default_qty_value is None):
            raise ValueError(
                "default_qty_type 와 default_qty_value 는 함께 명시 또는 함께 None"
            )
        return self


# --- Response: base ---

class BacktestCreatedResponse(BaseModel):
    """POST /backtests → 202 Accepted.

    Sprint 9-6 E2: `replayed=True` 는 Idempotency-Key + body hash 가 기존
    row 와 일치하여 기존 backtest 를 그대로 반환한 경우. Router 는 응답 헤더
    `X-Idempotency-Replayed: true` 를 함께 설정한다.
    """

    backtest_id: UUID
    status: BacktestStatus
    created_at: AwareDatetime
    replayed: bool = False


class BacktestProgressResponse(BaseModel):
    """GET /:id/progress — 경량 폴링 응답."""

    backtest_id: UUID
    status: BacktestStatus
    started_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    error: str | None
    stale: bool = False


class BacktestCancelResponse(BaseModel):
    """POST /:id/cancel → 202 Accepted.

    HTTP 202 + body {status: cancelling, message: ...} — reason phrase는 "Accepted".
    "cancellation_requested"는 semantic label (body 내 message 참조).
    """

    backtest_id: UUID
    status: BacktestStatus
    message: str


# --- Detail / List ---

class BacktestSummary(BaseModel):
    """목록 항목. metrics/equity_curve 미포함."""

    id: UUID
    strategy_id: UUID
    symbol: str
    timeframe: str
    period_start: AwareDatetime
    period_end: AwareDatetime
    status: BacktestStatus
    created_at: AwareDatetime
    completed_at: AwareDatetime | None

    model_config = ConfigDict(from_attributes=True)


class BacktestMetricsOut(BaseModel):
    """engine.types.BacktestMetrics → API 노출 (Decimal → str).

    Sprint 30 gamma-BE: PRD `backtests.results` JSONB 24 metric 정합. 기존 12 + 신규 12.
    신규 필드는 모두 Optional default None (Sprint 28 이전 backtest 호환).
    """

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    num_trades: int
    # 확장 지표 — Optional (기존 완료 백테스트는 None 반환)
    sortino_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    profit_factor: Decimal | None = None
    avg_win: Decimal | None = None
    avg_loss: Decimal | None = None
    long_count: int | None = None
    short_count: int | None = None
    # Sprint 30 gamma-BE 신규 12 필드 (PRD spec)
    avg_holding_hours: Decimal | None = None
    consecutive_wins_max: int | None = None
    consecutive_losses_max: int | None = None
    long_win_rate_pct: Decimal | None = None
    short_win_rate_pct: Decimal | None = None
    monthly_returns: list[tuple[str, Decimal]] | None = None
    drawdown_duration: int | None = None
    annual_return_pct: Decimal | None = None
    total_trades: int | None = None
    avg_trade_pct: Decimal | None = None
    best_trade_pct: Decimal | None = None
    worst_trade_pct: Decimal | None = None
    drawdown_curve: list[tuple[str, Decimal]] | None = None
    # Sprint 32-D BL-156 — MDD 수학 정합 메타. mdd_unit = "equity_ratio" (현재
    # 유일 단위), mdd_exceeds_capital = MDD < -100% 여부 (자본 초과 손실).
    # FE 카드가 leverage 가정과 inline 표시.
    mdd_unit: str | None = None
    mdd_exceeds_capital: bool | None = None
    # Sprint 34 BL-175 — Buy & Hold 정확 계산 (OHLCV 첫/끝 close 기반).
    # init_cash * (close[i] / close[0]) curve. equity_curve 와 timestamp 1:1.
    # fail-closed: OHLCV close 1건이라도 NaN/<=0 시 None → FE BH series hide.
    buy_and_hold_curve: list[tuple[str, Decimal]] | None = None

    @field_serializer(
        "total_return", "sharpe_ratio", "max_drawdown", "win_rate",
        "sortino_ratio", "calmar_ratio", "profit_factor", "avg_win", "avg_loss",
        "avg_holding_hours", "long_win_rate_pct", "short_win_rate_pct",
        "annual_return_pct", "avg_trade_pct", "best_trade_pct", "worst_trade_pct",
    )
    def _decimal_to_str(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)

    @field_serializer("monthly_returns")
    def _monthly_returns_to_jsonable(
        self, v: list[tuple[str, Decimal]] | None
    ) -> list[list[str]] | None:
        """list[(YYYY-MM, Decimal)] → list[[str, str]] (JSON tuple → list)."""
        if v is None:
            return None
        return [[k, str(val)] for k, val in v]

    @field_serializer("drawdown_curve")
    def _drawdown_curve_to_jsonable(
        self, v: list[tuple[str, Decimal]] | None
    ) -> list[list[str]] | None:
        """list[(ISO ts, Decimal)] → list[[str, str]]."""
        if v is None:
            return None
        return [[ts, str(val)] for ts, val in v]

    @field_serializer("buy_and_hold_curve")
    def _buy_and_hold_curve_to_jsonable(
        self, v: list[tuple[str, Decimal]] | None
    ) -> list[list[str]] | None:
        """list[(ISO ts, Decimal)] → list[[str, str]]. drawdown_curve 와 동일 패턴."""
        if v is None:
            return None
        return [[ts, str(val)] for ts, val in v]


class EquityPoint(BaseModel):
    """equity_curve 1 point."""

    timestamp: AwareDatetime
    value: Decimal

    @field_serializer("value")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class BacktestConfigOut(BaseModel):
    """PRD `backtests.config` JSONB 5 가정 — FE AssumptionsCard 노출용.

    Sprint 31 BL-156: leverage / fees / slippage / include_funding 응답 활성화.
    `initial_capital` 은 BacktestDetail 최상위 필드라 본 모델에선 생략.

    leverage 는 *명시적 가정* 으로 노출 — 현재 pine_v2 엔진은 leverage 를
    PnL 계산에 적용하지 않으므로 (qty 가 절대 수량) 사용자가 자본 대비 손실
    한계 (-100%) 를 초과하는 MDD 를 해석할 때 참고. >1.0 는 자연스럽게
    설명 가능.
    """

    leverage: float
    fees: float
    slippage: float
    include_funding: bool


class BacktestDetail(BacktestSummary):
    """GET /:id 상세 — metrics/equity_curve/error/config 포함.

    Sprint 31 BL-156: `config` 필드 활성화 (PRD 5 가정). FE AssumptionsCard
    가 default 표시 graceful degrade → 실제값 응답 으로 graceful upgrade.
    """

    initial_capital: Decimal
    config: BacktestConfigOut | None = None
    metrics: BacktestMetricsOut | None = None
    equity_curve: list[EquityPoint] | None = None
    error: str | None = None

    @field_serializer("initial_capital")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


# --- Trade ---

class TradeItem(BaseModel):
    """GET /:id/trades 항목."""

    trade_index: int
    direction: TradeDirection
    status: TradeStatus
    entry_time: AwareDatetime
    exit_time: AwareDatetime | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    return_pct: Decimal
    fees: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("entry_price", "exit_price", "size", "pnl", "return_pct", "fees")
    def _decimal_to_str(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)
