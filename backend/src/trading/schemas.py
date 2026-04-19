"""trading 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderState, OrderType


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
