"""명시적인 code_v1 저장·검토 API. 기존 Pine DTO에 사용자 코드를 끼워 넣지 않는다."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import CodeLanguage


class SaveCodeStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    symbol: str | None = Field(default=None, max_length=32)
    timeframe: str | None = Field(default=None, max_length=16)
    code: CodeSnapshot


class CodeVersionResponse(BaseModel):
    schema_version: Literal[1] = 1
    execution_policy: Literal["code_v1"]
    language: CodeLanguage
    source_code: str
    warmup_bars: int
    params: dict[str, JsonValue]
    provenance: dict[str, JsonValue]
    id: UUID
    source_hash: str
    execution_hash: str
    created_at: AwareDatetime


class CodeStrategyResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    symbol: str | None
    timeframe: str | None
    is_archived: bool
    version: CodeVersionResponse


class CodeStrategyListResponse(BaseModel):
    items: list[CodeStrategyResponse]
    total: int
