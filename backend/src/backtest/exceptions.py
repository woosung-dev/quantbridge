"""backtest 도메인 예외."""

from __future__ import annotations

from fastapi import status

from src.common.exceptions import AppException

# Sprint 32 E (BL-163) — actionable 422 error UX. coverage._UNSUPPORTED_WORKAROUNDS 가
# 함수별 구체 워크어라운드 SSOT. 본 모듈은 list[str] → 사용자 친화 single message
# (한국어 요약 + ADR-003 supported list 안내) 로 합성.
#
# 분류 우선순위 (corruption > syntax > data > drawing > math > other):
# - corruption: heikinashi/security 등 silent data corruption risk (Trust Layer 위반)
# - syntax: array/matrix/map (Pine v6 collection types — paradigm mismatch)
# - data: request.security_lower_tf / request.dividends 등 외부 데이터 의존
# - drawing: label/box/line 등 시각 NOP (대체 불필요)
# - math/other: ta.alma / ta.bb 등 alternate indicator 권장
_FRIENDLY_CATEGORY_LABEL: dict[str, str] = {
    "corruption": "Trust Layer 위반 (결과 부정확 risk)",
    "syntax": "Pine v6 collection types 미지원 (paradigm mismatch)",
    "data": "외부 데이터 의존 — 단일 timeframe 으로 재구성 권장",
    "drawing": "시각 효과 — backtest 무관 (제거 가능)",
    "math": "alternate indicator 권장",
    "other": "미지원 빌트인",
}

# Sprint 32 E (BL-163): degraded / Trust Layer 위반 함수 (graceful 실행되지만 결과 부정확).
# coverage._DEGRADED_FUNCTIONS / _DEGRADED_ATTRIBUTES 와 동기. 본 set 에 등록된 항목은
# friendly_message 합성 시 _categorize 가 반환하는 prefix-기반 category 보다 우선해
# "corruption" 으로 라벨링 (사용자가 silent data corruption risk 를 명확히 인지하도록).
_CORRUPTION_NAMES: frozenset[str] = frozenset(
    {
        "heikinashi",
        "security",
        "request.security",
        "request.security_lower_tf",
        "timeframe.period",
    }
)


def format_friendly_message(unsupported_builtins: list[str]) -> str:
    """422 응답의 unsupported_builtins list 를 사용자 친화 단일 메시지로 변환.

    coverage._UNSUPPORTED_WORKAROUNDS SSOT 참조 + 카테고리 라벨링. FE 가 inline
    카드로 표시. 빈 list 이면 빈 문자열 반환 (FE fallback root.serverError).

    카테고리 우선순위: `_CORRUPTION_NAMES` 에 명시된 함수는 prefix-기반 분류보다
    "corruption" 라벨로 우선 표시 (사용자에게 silent data corruption risk 명시).

    Args:
        unsupported_builtins: ["heikinashi", "array.new_float"] 등 builtin 이름 list

    Returns:
        "이 strategy 는 다음 미지원 빌트인을 포함합니다: heikinashi (Trust Layer 위반...). "
        "ADR-003 supported list 의 indicator (ta.sma / ta.rsi / ta.atr / ta.crossover 등) "
        "로 대체 가능합니다."
    """
    if not unsupported_builtins:
        return ""

    # 순환 import 회피: 본 함수 호출 시점에만 coverage 의 SSOT 참조.
    from src.strategy.pine_v2.coverage import (
        _UNSUPPORTED_WORKAROUNDS,
        _categorize,
    )

    parts: list[str] = []
    for name in unsupported_builtins:
        # Trust Layer 위반 함수는 corruption 라벨 우선 (prefix 분류 override).
        category = "corruption" if name in _CORRUPTION_NAMES else _categorize(name)
        label = _FRIENDLY_CATEGORY_LABEL.get(category, "미지원 빌트인")
        workaround = _UNSUPPORTED_WORKAROUNDS.get(name)
        if workaround:
            parts.append(f"{name} — {label}: {workaround}")
        else:
            parts.append(f"{name} — {label}.")

    summary = " | ".join(parts)
    return (
        f"이 strategy 는 미지원 Pine 빌트인을 포함합니다. {summary} "
        f"ADR-003 supported list 참조 (docs/02_domain/supported-indicators.md). "
        f"strategy 편집 화면의 Coverage Analyzer pre-flight 에서 자세한 내역 확인 가능."
    )


class BacktestError(AppException):
    """backtest 도메인 베이스."""


class BacktestNotFound(BacktestError):
    """소유자 격리 고려 — 존재하지 않거나 타 사용자 소유 모두 404."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "backtest_not_found"
    detail = "Backtest not found"


class BacktestStateConflict(BacktestError):
    """백테스트 상태가 작업을 허용하지 않음 (예: 완료된 백테스트 재실행)."""

    status_code = status.HTTP_409_CONFLICT
    code = "backtest_state_conflict"
    detail = "Backtest state does not allow this action"


class OHLCVFixtureNotFound(BacktestError):
    """백테스트에 필요한 OHLCV 데이터가 없음."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "ohlcv_fixture_not_found"
    detail = "OHLCV fixture not found"


class TaskDispatchError(BacktestError):
    """Celery 태스크 디스패치 실패 (Redis/Celery 상태 문제)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "task_dispatch_failed"
    detail = "Failed to dispatch background task"


class BacktestDuplicateIdempotencyKey(BacktestError):
    """동일 Idempotency-Key로 backtest가 이미 존재함. detail에 existing_id 포함."""

    status_code = status.HTTP_409_CONFLICT
    code = "backtest_idempotency_conflict"
    detail = "Duplicate Idempotency-Key"


class StrategyNotRunnable(BacktestError):
    """Pine 소스에 미지원 built-in 함수/변수가 있어 backtest 실행 불가.

    Sprint Y1 (B+D): pre-flight coverage analyzer 가 unsupported_builtins 발견 시 raise.
    Sprint 21 (codex G.0 P1 #5): `unsupported_builtins: list[str]` 필드 추가.
    detail 의 string 을 split 하지 않고 FE 가 list 직접 접근 (`{detail: {..., unsupported_builtins: [...]}}`).
    기존 string detail 도 backward compat 유지.

    Sprint 32 E (BL-163): `friendly_message: str` 필드 추가. coverage workaround SSOT
    기반 사용자 친화 단일 메시지. FE 가 toast 또는 inline 카드 헤더로 활용.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "strategy_not_runnable"
    detail = "Strategy contains unsupported Pine built-ins"

    def __init__(
        self,
        detail: str | None = None,
        *,
        unsupported_builtins: list[str] | None = None,
        friendly_message: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.unsupported_builtins: list[str] = list(unsupported_builtins or [])
        # Sprint 32 E (BL-163): friendly_message 미명시 시 list 기반 자동 합성.
        # 명시 시 (예: 호출부가 우선순위 높은 사용자 메시지 주입) 그대로 사용.
        self.friendly_message: str = friendly_message or format_friendly_message(
            self.unsupported_builtins
        )


class StrategyDegraded(BacktestError):
    """Sprint 29 codex G2 P0 fix: Trust Layer 의도적 위반 함수 사용.

    `heikinashi` / `request.security` / `timeframe.period` 등 graceful 실행되지만
    Pine 원본과 결과 차이 가능. backtest submit 시 `allow_degraded_pine=true` 명시
    동의 없으면 본 exception raise. dogfood-first — 사용자가 거짓 양성 risk 명시 인지 후 진행.

    `degraded_calls: list[str]` 필드 — FE 가 명세 list 직접 접근 가능.

    Sprint 32 E (BL-163): `friendly_message: str` 필드 추가 (StrategyNotRunnable parity).
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "strategy_degraded"
    detail = "Strategy uses degraded Pine functions (Trust Layer violation)"

    def __init__(
        self,
        detail: str | None = None,
        *,
        degraded_calls: list[str] | None = None,
        friendly_message: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.degraded_calls: list[str] = list(degraded_calls or [])
        # Sprint 32 E (BL-163): degraded_calls 도 동일 SSOT 사용. corruption category 라벨.
        self.friendly_message: str = friendly_message or format_friendly_message(
            self.degraded_calls
        )


# ---------------------------------------------------------------------------
# Sprint 38 BL-188 v3 — Live Settings mirror canonical 결정 시 422 reject 3종.
# codex G.0 iter 1+2 [P1] must-fix 1 (sizing source 단일화) + must-fix 3 (leverage Nx
# reject) 반영. _resolve_sizing_canonical helper 가 raise.
# ---------------------------------------------------------------------------


class MirrorNotAllowed(BacktestError):
    """Live settings 가 1x equity-basis 외 (Nx leverage 등) 로 mirror 불가.

    Sprint 38 BL-188 v3 (codex must-fix 3): `strategy.settings.leverage != 1` 시 raise.
    Live (Bybit Futures Nx isolated/cross) 와 backtest (1x equity-basis) 비대칭 →
    거짓 trust 신호 차단. BL-186 (풀 leverage/funding/liquidation 모델) 후 unlock.

    `live_leverage` / `live_margin_mode` 필드 — FE 가 사용자 안내 라벨에 활용.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "mirror_not_allowed"
    detail = "Live Settings mirror is not allowed for the current strategy"

    def __init__(
        self,
        detail: str | None = None,
        *,
        live_leverage: int | None = None,
        live_margin_mode: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.live_leverage: int | None = live_leverage
        self.live_margin_mode: str | None = live_margin_mode


class PinePartialDeclaration(BacktestError):
    """Pine `strategy(default_qty_type=...)` / `default_qty_value=...` 일방만 명시.

    Sprint 38 BL-188 v3 (codex iter 1 [P1] #5): 둘 다 명시 또는 둘 다 None 의무.
    type-only 또는 value-only 시 silent fallback (Pine > Live > form chain) 로
    내려가면 "Pine 우선" 의미 깨짐 → reject + 사용자에게 정정 요구.

    `declared_type` / `declared_value` 필드 — FE 가 사용자에게 누락된 항목 명시.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "pine_partial_declaration"
    detail = "Pine strategy(default_qty_type / default_qty_value) partial declaration"

    def __init__(
        self,
        detail: str | None = None,
        *,
        declared_type: str | None = None,
        declared_value: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.declared_type: str | None = declared_type
        self.declared_value: str | None = declared_value


class SizingSourceConflict(BacktestError):
    """`position_size_pct` (Live mirror) + `default_qty_type/value` (manual) 동시 명시.

    Sprint 38 BL-188 v3 (codex iter 1 [P1] #4): canonical 1개 강제. FE 폼 toggle UI
    가 Live mirror / Manual 한 쪽만 fill 하도록 강제. BE 도 동일 정책으로 schema
    validator 가 raise (Pydantic ValidationError → 422 자동 매핑) — 본 클래스는
    service-level fallback (FE 우회 호출 또는 외부 client 방어).
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "sizing_source_conflict"
    detail = "position_size_pct (Live mirror) and default_qty_type/value (manual) cannot coexist"


class BacktestShareRevoked(BacktestError):
    """share_token 은 존재하지만 revoke 된 backtest. HTTP 410 Gone.

    Sprint 41 Worker H — public share endpoint 응답. 토큰 자체는 유지 (재활성화
    불가; 새 share 생성 시 새 토큰 발급). revoke 후 link 를 가진 외부 viewer 는
    "이 링크는 해제됨" 안내를 받음.
    """

    status_code = status.HTTP_410_GONE
    code = "backtest_share_revoked"
    detail = "Backtest share link has been revoked"


class TradingSessionTzNaiveReject(BacktestError):
    """trading_sessions 활성 + OHLCV index 가 tz-naive 또는 non-DatetimeIndex.

    Sprint 38 BL-188 v3 A2 — entry placement gate / fill gate 모두 tz-aware bar
    timestamp 가 필수 (UTC hour 변환). naive index 를 silent UTC 가정으로 처리하면
    Live `is_allowed` (tz-aware 강제) 와 backtest 결과 불일치 risk → fail-closed
    422 reject. sessions 비어있으면 본 reject 미적용 (회귀 0).
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "trading_session_tz_naive_reject"
    detail = "trading_sessions 활성 시 OHLCV index 가 tz-aware DatetimeIndex 필수"
