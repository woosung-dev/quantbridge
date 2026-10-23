"""명시적인 code_v1 저장·검토 API. 기존 Pine DTO에 사용자 코드를 끼워 넣지 않는다."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import CodeLanguage
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.schemas import StrategySettings


class SaveCodeStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    symbol: str | None = Field(default=None, max_length=32)
    timeframe: str | None = Field(default=None, max_length=16)
    code: CodeSnapshot
    settings: StrategySettings | None = None


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
    settings: StrategySettings | None
    version: CodeVersionResponse


class CodeStrategyListResponse(BaseModel):
    items: list[CodeStrategyResponse]
    total: int


class GenerateCodeStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=10, max_length=2000)
    warmup_bars: int = Field(default=200, ge=1, le=10000)
    params: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bounded_params(self) -> GenerateCodeStrategyRequest:
        validate_source_and_params("preview", self.params)
        return self


class PythonCodeSnapshot(CodeSnapshot):
    language: Literal[CodeLanguage.python] = CodeLanguage.python


class GenerationUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    thinking_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class GenerateCodeStrategyResponse(BaseModel):
    """미저장 preview. 구문 검사는 실제 실행·의미 검증 성공이 아니다."""

    status: Literal["preview"] = "preview"
    code: PythonCodeSnapshot
    assumptions: list[str]
    provider: Literal["gemini"] = "gemini"
    requested_model: str
    actual_model: str | None = None
    usage: GenerationUsage | None = None
