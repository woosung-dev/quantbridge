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
    """

    strategy_id: UUID
    symbol: str = Field(min_length=3, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    period_start: AwareDatetime
    period_end: AwareDatetime
    initial_capital: Decimal = Field(gt=Decimal("0"), max_digits=20, decimal_places=8)
    # Sprint 29 codex G2 P0 — degraded Pine semantic 명시 동의. default False (안전 fallback).
    allow_degraded_pine: bool = False

    @model_validator(mode="after")
    def _validate_period(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
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
    """engine.types.BacktestMetrics → API 노출 (Decimal → str)."""

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

    @field_serializer(
        "total_return", "sharpe_ratio", "max_drawdown", "win_rate",
        "sortino_ratio", "calmar_ratio", "profit_factor", "avg_win", "avg_loss",
    )
    def _decimal_to_str(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)


class EquityPoint(BaseModel):
    """equity_curve 1 point."""

    timestamp: AwareDatetime
    value: Decimal

    @field_serializer("value")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class BacktestDetail(BacktestSummary):
    """GET /:id 상세 — metrics/equity_curve/error 포함."""

    initial_capital: Decimal
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
