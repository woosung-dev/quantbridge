"""strategy 도메인 Pydantic V2 스키마."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from src.backtest.schemas import BacktestMetricsSummary
from src.strategy.models import ParseStatus, PineVersion
from src.strategy.trading_sessions import validate_session_names


class StrategyLifecycle(StrEnum):
    """전략 목록에서 계산하는 파생 수명주기."""

    draft = "draft"
    validated = "validated"
    deployed = "deployed"


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


# [ADR-040] Stage 1 — 파라미터 표의 데이터. `ast_extractor.extract_content()` 가
# 뽑아 두고 있었으나 응답에 실리지 않아 FE 가 표를 못 그렸다
# (`diagnostics-strip.tsx` 의 「파라미터」 탭이 빈 슬롯으로 대기 중이었다).
class InputDeclResponse(BaseModel):
    """Pine `input.*()` 선언 하나.

    ★`var_name` 은 장식이 아니라 **override 키**다 — 엔진은 `input_overrides[var_name]`
    으로 값을 갈아끼우고(`pine_v2/interpreter.py` 의 `_assignment_target_stack`),
    Optimizer / Param-Stability 의 pre-validate 가 같은 이름으로 대조한다.
    """

    input_type: str  # int / float / bool / string / source / timeframe / generic ...
    var_name: str
    defval: str | None = None
    title: str | None = None


class DeclarationResponse(BaseModel):
    """스크립트 선언부(`strategy()` / `indicator()` / `library()`) 요약."""

    kind: Literal["strategy", "indicator", "library", "unknown"]
    title: str | None = None
    default_qty_type: str | None = None
    default_qty_value: str | None = None
    pyramiding: int | None = None


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
    # [ADR-040] Stage 1 — 선언부 + input 선언 전량. 파싱 실패 시 둘 다 비어 있다
    # (`None` / `[]`) — 이 필드들이 없다고 파싱 성공이 취소되지는 않는다.
    declaration: DeclarationResponse | None = None
    inputs: list[InputDeclResponse] = Field(default_factory=list)


# ── [ADR-040] 전략 브리핑 ─────────────────────────────────────────────────────
# ★**판정어는 전부 결정론 층이 낸다.** 이 응답에 LLM 이 만든 값은 하나도 없다 —
#   해설 층은 별 엔드포인트(`/brief/narrative`)이고, 실패해도 이 응답으로 화면이 완결된다.
class BriefArg(BaseModel):
    """주문 호출의 인자 하나. `name=None` 이면 positional."""

    name: str | None = None
    value: str


class BriefOrderCall(BaseModel):
    """`strategy.entry` / `exit` / `close` / `close_all` 호출 한 건 + **소스 줄번호**."""

    name: str
    line: int | None = None
    args: list[BriefArg] = Field(default_factory=list)


class StrategyBriefResponse(BaseModel):
    """백테스트 **제출 전에** 「이 전략이 무엇을 하는가」를 답하는 결정론 응답.

    `parse` 를 **품는다** — 판정·미지원 목록·파라미터·지표는 `POST /strategies/parse` 와
    같은 값이어야 하므로 필드를 복제하지 않고 그 스키마를 그대로 담는다.
    """

    strategy_id: UUID
    # Stage 4 의 해설 캐시 키 = **분석한 소스의 sha256**(`repository.create_version` 과 같은 식).
    # ★`StrategyVersion` 을 조회하지 않고 `Strategy.pine_source` 에서 직접 계산한다 —
    #   백테스트 제출이 그 소스를 스냅샷으로 고정하므로 「지금 제출하면 무엇이 도는가」와 일치한다.
    source_hash: str | None = None
    # `ast_classifier` 의 실행 경로 분류. 파싱 실패 시 None.
    track: Literal["S", "A", "M"] | None = None
    parse: ParsePreviewResponse
    orders: list[BriefOrderCall] = Field(default_factory=list)
    # `SignalExtractor` 가 찾은 신호 변수.
    # ★★**Track S 의 `if cond` 형태에서는 비어 있는 것이 정상이다.** 그 추출기는
    #   `strategy.entry(..., when=v)` · `plotshape` · `alertcondition(v, ..)` ·
    #   `label.new(v ? ..)` 네 형태만 본다(`_find_signal_vars_ast`) — 즉 indicator 계열에서만
    #   값이 나온다. **소비자는 빈 배열을 「신호 없음」으로 읽으면 안 된다.**
    #   계약 고정 = `tests/strategy/test_strategy_brief.py`(빈 단언 + Track A 양성 대조).
    signals: list[str] = Field(default_factory=list)


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
    max_trigger_breach_pct: float | None = Field(default=None, gt=0)
    # BL-516 안 3 — 부호가 교차하는 조건부 진입(청산+진입이 주문 1건으로 합쳐지는 반전)의
    # `주문수량 / |목표 포지션|` 상한. 기본 None = 비활성 = 기존 동작 그대로.
    # ★BL-562 — **등재 시점 근사**다. 조건부 주문 등재 순간의 포지션으로만 평가하고
    # 트리거까지 재평가하지 않는다(그 시점엔 주문이 이미 거래소에 있어 크기를 못 바꾼다).
    # 켜기 전에 BL-562 를 읽어라 — 근사임을 모르고 쓰면 "체결 시 반전 크기 보장"으로 읽힌다.
    max_reversal_overshoot_ratio: float | None = Field(default=None, gt=0)
    fill_timing: Literal["bar_close", "next_bar_open"] = "bar_close"


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
    max_trigger_breach_pct: float | None = Field(default=None, gt=0)
    max_reversal_overshoot_ratio: float | None = Field(default=None, gt=0)
    fill_timing: Literal["bar_close", "next_bar_open"] = "bar_close"


class LatestBacktestSummary(BaseModel):
    """전략 목록에 노출하는 최신 완료 백테스트 요약."""

    backtest_id: UUID
    completed_at: AwareDatetime | None
    metrics: BacktestMetricsSummary | None


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
    backtest_count: int = 0
    latest_backtest: LatestBacktestSummary | None = None
    param_count: int = 0
    lifecycle: StrategyLifecycle = StrategyLifecycle.draft


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
