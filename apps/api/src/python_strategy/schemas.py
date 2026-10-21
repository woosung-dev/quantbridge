"""Python 코드 저장은 구문 검사만 하며, 실행·수익성 검증과 구분한다."""

from __future__ import annotations

import ast
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class SavePythonStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=100_000)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    warmup_bars: int = Field(default=200, ge=0, le=10_000)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("전략 이름을 입력하세요.")
        return value.strip()

    @field_validator("source")
    @classmethod
    def parse_without_execution(cls, value: str) -> str:
        from src.strategy.python_runtime.protocol import MAX_SOURCE_BYTES

        if len(value.encode()) > MAX_SOURCE_BYTES:
            raise ValueError("Python 소스의 UTF-8 크기가 실행기 한도를 초과했습니다.")
        try:
            tree = ast.parse(value)
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise ValueError("Python 구문을 확인하세요.") from exc
        if not any(
            isinstance(node, ast.FunctionDef) and node.name == "on_bar" for node in tree.body
        ):
            raise ValueError("on_bar(ctx, state) 함수를 정의하세요.")
        return value

    @field_validator("params")
    @classmethod
    def bounded_params(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 100 or len(json.dumps(value)) > 16_384:
            raise ValueError("파라미터 크기가 한도를 초과했습니다.")
        if any(isinstance(item, float) and not math.isfinite(item) for item in value.values()):
            raise ValueError("파라미터는 유한한 값이어야 합니다.")
        return value


class PythonBacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version_id: UUID | None = None
    symbol: Literal["BTC/USDT", "ETH/USDT"]
    timeframe: Literal["1h", "4h", "1d"]
    period_start: AwareDatetime
    period_end: AwareDatetime
    initial_capital: Decimal = Field(default=Decimal("10000"), gt=0, le=Decimal("1000000000"))
    fees: Decimal = Field(default=Decimal("0.00055"), ge=0, le=Decimal("0.01"))
    slippage: Decimal = Field(default=Decimal("0.00014"), ge=0, le=Decimal("0.01"))

    @model_validator(mode="after")
    def bounded_window(self) -> Self:
        seconds = {"1h": 3600, "4h": 14400, "1d": 86400}[self.timeframe]
        start = self.period_start.astimezone(UTC)
        end = self.period_end.astimezone(UTC)
        if end <= start or (end - start).total_seconds() // seconds > 40_000:
            raise ValueError("평가 기간은 1봉 이상 40,000봉 이하여야 합니다.")
        if start.timestamp() % seconds or end.timestamp() % seconds:
            raise ValueError("기간의 시작과 끝은 UTC 시간봉 경계여야 합니다.")
        first_settlement = math.ceil(start.timestamp() / 28_800) * 28_800
        if first_settlement >= end.timestamp():
            raise ValueError("평가 기간에 UTC 00/08/16시 펀딩 정산이 최소 1회 포함되어야 합니다.")
        if end.timestamp() > (datetime.now(UTC).timestamp() // seconds) * seconds:
            raise ValueError("아직 마감되지 않은 봉은 평가할 수 없습니다.")
        return self


class PythonStrategyDetail(BaseModel):
    id: UUID
    name: str
    source: str
    params: dict[str, Any]
    warmup_bars: int
    version_id: UUID
    source_hash: str
    created_at: datetime
    updated_at: datetime


class PythonRunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_id: UUID
    version_id: UUID
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    request: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class PythonStrategyList(BaseModel):
    items: list[PythonStrategyDetail]


class PythonRunList(BaseModel):
    items: list[PythonRunDetail]


class PythonCapabilities(BaseModel):
    available: bool
    reason: str | None = None
