# 청산가 미리보기 서비스 — 순수 calc (AsyncSession/Repository 0, mutation 0)

from __future__ import annotations

from src.trading.liquidation import (
    DEFAULT_MAINTENANCE_MARGIN_RATE,
    calculate_liquidation_price,
    liquidation_distance_pct,
)
from src.trading.liquidation_schemas import (
    LiquidationInfoResponse,
    LiquidationPreviewRequest,
)


class LiquidationService:
    """청산가 on-the-fly 계산 — DB 미접근 순수 read. demo-only calc+display."""

    def preview(self, req: LiquidationPreviewRequest) -> LiquidationInfoResponse:
        mmr = (
            req.maintenance_margin_rate
            if req.maintenance_margin_rate is not None
            else DEFAULT_MAINTENANCE_MARGIN_RATE
        )
        liquidation_price = calculate_liquidation_price(
            entry_price=req.entry_price,
            side=req.side,
            leverage=req.leverage,
            maintenance_margin_rate=mmr,
        )
        distance_pct = liquidation_distance_pct(
            entry_price=req.entry_price,
            liquidation_price=liquidation_price,
        )
        return LiquidationInfoResponse(
            symbol=req.symbol,
            entry_price=req.entry_price,
            side=req.side,
            leverage=req.leverage,
            liquidation_price=liquidation_price,
            maintenance_margin_rate=mmr,
            distance_pct=distance_pct,
        )
