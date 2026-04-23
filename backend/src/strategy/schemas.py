"""strategy 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from src.strategy.models import ParseStatus, PineVersion
from src.strategy.trading_sessions import validate_session_names


class CreateStrategyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pine_source: str = Field(min_length=1)
    timeframe: str | None = Field(default=None, max_length=16)
    symbol: str | None = Field(default=None, max_length=32)
    tags: list[str] = Field(default_factory=list)
    # Sprint 7d: empty list = 24h. Subset of {"asia","london","ny"}.
    trading_sessions: list[str] = Field(default_factory=list)

    @field_validator("trading_sessions")
    @classmethod
    def _validate_sessions(cls, v: list[str]) -> list[str]:
        return validate_session_names(v)


class UpdateStrategyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pine_source: str | None = Field(default=None, min_length=1)
    timeframe: str | None = Field(default=None, max_length=16)
    symbol: str | None = Field(default=None, max_length=32)
    tags: list[str] | None = None
    trading_sessions: list[str] | None = None
    is_archived: bool | None = None

    @field_validator("trading_sessions")
    @classmethod
    def _validate_sessions(cls, v: list[str] | None) -> list[str] | None:
        return validate_session_names(v) if v is not None else None


class ParseRequest(BaseModel):
    pine_source: str = Field(min_length=1)


class ParseError(BaseModel):
    code: str
    message: str
    line: int | None = None


class ParsePreviewResponse(BaseModel):
    status: ParseStatus
    pine_version: PineVersion
    warnings: list[str] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)
    entry_count: int = 0
    exit_count: int = 0
    # Sprint 7b ISSUE-004: UI 파싱 결과 탭 '감지된 지표/전략 콜' 섹션 렌더링을 위해
    # parser supported_feature_report["functions_used"]를 응답에 노출.
    functions_used: list[str] = Field(default_factory=list)
    # Sprint Y1 (B+D): pre-flight coverage analyzer — 미지원 built-in 명시.
    # `unsupported_builtins` 가 비어있을 때만 backtest 실행 가능 (CLAUDE.md Golden Rule).
    unsupported_builtins: list[str] = Field(default_factory=list)
    # 실행 가능 여부 (FE 가 backtest 버튼 비활성화 + 안내 표시 결정에 사용)
    is_runnable: bool = True


class StrategyListItem(BaseModel):
    """목록 DTO — pine_source/description 제외."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    pine_version: PineVersion
    parse_status: ParseStatus
    parse_errors: list[dict[str, object]] | None = None
    timeframe: str | None = None
    symbol: str | None = None
    tags: list[str] = Field(default_factory=list)
    trading_sessions: list[str] = Field(default_factory=list)
    is_archived: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class StrategyResponse(BaseModel):
    """상세 DTO — 전 필드 포함."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    pine_source: str
    pine_version: PineVersion
    parse_status: ParseStatus
    parse_errors: list[dict[str, object]] | None
    timeframe: str | None
    symbol: str | None
    tags: list[str] = Field(default_factory=list)
    trading_sessions: list[str] = Field(default_factory=list)
    is_archived: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class StrategyListResponse(BaseModel):
    items: list[StrategyListItem]
    total: int
    page: int
    limit: int
    total_pages: int
