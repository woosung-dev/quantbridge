"""trading 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderState, OrderType


class RegisterAccountRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exchange: ExchangeName
    mode: ExchangeMode
    api_key: str = Field(min_length=1, max_length=200)
    api_secret: str = Field(min_length=1, max_length=200)
    label: str | None = Field(default=None, max_length=120)


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
