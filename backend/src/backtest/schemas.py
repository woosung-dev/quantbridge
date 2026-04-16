"""Backtest 도메인 Pydantic V2 스키마 — Request/Response DTOs."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.backtest.models import BacktestStatus, TradeDirection, TradeStatus

# --- Request ---

class CreateBacktestRequest(BaseModel):
    """POST /backtests body."""

    strategy_id: UUID
    symbol: str = Field(min_length=3, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    period_start: datetime
    period_end: datetime
    initial_capital: Decimal = Field(gt=Decimal("0"), max_digits=20, decimal_places=8)

    @model_validator(mode="after")
    def _validate_period(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self


# --- Response: base ---

class BacktestCreatedResponse(BaseModel):
    """POST /backtests → 202 Accepted."""

    backtest_id: UUID
    status: BacktestStatus
    created_at: datetime


class BacktestProgressResponse(BaseModel):
    """GET /:id/progress — 경량 폴링 응답."""

    backtest_id: UUID
    status: BacktestStatus
    started_at: datetime | None
    completed_at: datetime | None
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
    period_start: datetime
    period_end: datetime
    status: BacktestStatus
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BacktestMetricsOut(BaseModel):
    """engine.types.BacktestMetrics → API 노출 (Decimal → str)."""

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    num_trades: int

    @field_serializer("total_return", "sharpe_ratio", "max_drawdown", "win_rate")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class EquityPoint(BaseModel):
    """equity_curve 1 point."""

    timestamp: datetime
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
    entry_time: datetime
    exit_time: datetime | None
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
