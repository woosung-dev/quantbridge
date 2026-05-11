# Convert 엔드포인트 요청/응답 스키마

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConvertIndicatorRequest(BaseModel):
    code: str = Field(min_length=10, description="Pine Script 원본 코드")
    strategy_name: str = Field(default="Converted Strategy", max_length=100)
    mode: Literal["full", "sliced"] = Field(
        default="full",
        description="full=전체 코드 전달(B), sliced=슬라이싱 후 전달(C)",
    )


class ConvertIndicatorResponse(BaseModel):
    converted_code: str
    input_tokens: int
    output_tokens: int
    warnings: list[str] = Field(default_factory=list)
    sliced_from: int | None = None
    sliced_to: int | None = None
    token_reduction_pct: float | None = None
