# 청산가 미리보기 요청/응답 Pydantic 스키마 (schemas.py 미편집 — disjoint 계약 신규 파일)

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.trading.models import OrderSide


class LiquidationPreviewRequest(BaseModel):
    """청산가 미리보기 입력 — 명시 파라미터만(소유 리소스 fetch 없음 → IDOR 표면 0)."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    side: OrderSide
    entry_price: Decimal = Field(gt=0)
    leverage: int = Field(gt=0)
    # None 이면 service 가 DEFAULT_MAINTENANCE_MARGIN_RATE 적용. fraction(0.005=0.5%).
    maintenance_margin_rate: Decimal | None = Field(default=None, ge=0)


class LiquidationInfoResponse(BaseModel):
    """청산가 계산 결과."""

    symbol: str
    entry_price: Decimal
    side: OrderSide
    leverage: int
    liquidation_price: Decimal
    maintenance_margin_rate: Decimal
    distance_pct: Decimal
