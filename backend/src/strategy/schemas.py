"""strategy 도메인 Pydantic V2 스키마."""

from __future__ import annotations

from typing import Literal
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


# Sprint 29 Slice B: 미지원 호출 상세 응답 schema (line + workaround + category 포함)
class UnsupportedCallResponse(BaseModel):
    """미지원 호출 상세 — DrFXGOD reject 응답에 line 번호 + 우회 안내 포함."""

    name: str
    line: int
    col: int | None = None
    workaround: str | None = None
    category: Literal["drawing", "data", "syntax", "math", "other"]


# Sprint 29 Slice B: CoverageReport 전체 응답 schema (parse-preview API 확장 대상)
class CoverageReportResponse(BaseModel):
    """coverage analyzer 결과 전체 응답 — backward-compat + Slice B 확장 필드."""

    is_runnable: bool
    used_functions: list[str]
    used_attributes: list[str]
    unsupported_functions: list[str]  # 기존 backward-compat
    unsupported_attributes: list[str]  # 기존 backward-compat
    unsupported_calls: list[UnsupportedCallResponse] = Field(
        default_factory=list
    )  # Sprint 29 Slice B
    dogfood_only_warning: str | None = None  # Sprint 29 Slice A


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
    # Sprint 29 Slice B: line 번호 + workaround 포함 상세 응답
    unsupported_calls: list[UnsupportedCallResponse] = Field(default_factory=list)
    # Sprint 29 Slice A: heikinashi Trust Layer 위반 경고
    dogfood_only_warning: str | None = None
    # 실행 가능 여부 (FE 가 backtest 버튼 비활성화 + 안내 표시 결정에 사용)
    is_runnable: bool = True


class StrategySettings(BaseModel):
    """Sprint 26 — Live Signal Auto-Trading 의 trading params.

    schema_version: 향후 schema 변경 시 backward compat 식별 (P3 #2).
    leverage / margin_mode: Bybit Futures dispatch 분기 의무 (Sprint 22 BL-091).
    position_size_pct: 가용 잔고 대비 포지션 크기 (0-100, 100 = all-in).

    extra="forbid" 로 잘못된 필드 422 reject — codex G.0 P2 #4 malformed JSONB 방어.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    leverage: int = Field(ge=1, le=125)
    margin_mode: Literal["cross", "isolated"]
    position_size_pct: float = Field(gt=0, le=100)


def validate_strategy_settings(
    raw: dict[str, object] | None,
) -> StrategySettings | None:
    """JSONB → StrategySettings parse. None = unset (no-op). 실패 시 ValidationError.

    Sprint 26 codex G.0 P2 #4 — read path 에서 모든 strategy.settings 사용 전 검증.
    """
    if raw is None:
        return None
    return StrategySettings.model_validate(raw)


class UpdateStrategySettingsRequest(BaseModel):
    """PUT /strategies/{id}/settings request body. StrategySettings 와 동일 schema."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    leverage: int = Field(ge=1, le=125)
    margin_mode: Literal["cross", "isolated"]
    position_size_pct: float = Field(gt=0, le=100)


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
    settings: dict[str, object] | None = None  # Sprint 26 (P3 #1)
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
    settings: dict[str, object] | None = None  # Sprint 26 (P3 #1)
    is_archived: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class StrategyCreateResponse(StrategyResponse):
    """create 응답 전용. 신규 발급된 webhook_secret plaintext 1회 포함.

    Sprint 13 Phase A.1.4: Strategy 생성 시 atomic auto-issue 된 secret 의 plaintext 를
    1회만 응답에 포함. GET / list 응답에서는 절대 사용 금지 — frontend 는 sessionStorage
    캐시 (TTL 30분) 로 재사용.
    """

    webhook_secret: str | None = None


class StrategyListResponse(BaseModel):
    items: list[StrategyListItem]
    total: int
    page: int
    limit: int
    total_pages: int
