"""Decimal-first 허용 오차 유틸 (Path β Trust Layer CI 용).

Stage 2 실 구현 (Path β, 2026-04-23). ADR-013 §4.3 + §10.2 규약 준수.

정책:
- `max(절대 0.001, 상대 0.1%)` 통과 기준 (within_tolerance)
- 모든 입력/출력은 Decimal. float 전달 시 즉시 `Decimal(str(x))` 로 변환
- Decimal precision: 기본 `getcontext().prec = 28` (opus Gate-0 W4)
  - metric 범위 [1e-4, 1e1] 에 28자리 유효숫자 충분
  - Stage 2 baseline 생성 후 실측 분포로 검증 (opus Gate-1 W-2)
- 직렬화: **8자리 zero-pad** `f"{Decimal(str(val)):.8f}"` (opus Gate-1 W-1)
  - `"0.0832"` / `"0.08320000"` git diff 가짜 변경 방지
  - Bybit 최소 tick 자연수 (`.00000001` BTC)
- Sprint 4 D8 "Decimal-first 합산" 원칙 연장

사용 예::

    from decimal import Decimal
    from tests.strategy.pine_v2._tolerance import (
        to_decimal, within_tolerance, normalize_decimal, digest_sequence,
    )

    # float 안전 변환
    d = to_decimal(0.1532)  # Decimal("0.1532")

    # 허용 오차 비교
    assert within_tolerance(Decimal("0.1532"), Decimal("0.1535"))  # 상대 0.2% 내

    # git-friendly 직렬화
    normalize_decimal(Decimal("0.0832"))  # "0.08320000"

    # 길이 독립 fingerprint
    digest_sequence([1, 2, 3])  # "sha256:..."
"""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, getcontext
from typing import Any

# Path β ADR-013 §4.3 + trust-layer-requirements.md §3.2 공식
ABS_TOL: Decimal = Decimal("0.001")
REL_TOL: Decimal = Decimal("0.001")  # 0.1%

# opus Gate-0 W4 — getcontext().prec == 28 sanity (Stage 2 assert)
EXPECTED_PREC: int = 28

# opus Gate-1 W-1 — Decimal 직렬화 자리수 (8자리 zero-pad)
DEFAULT_DECIMAL_PLACES: int = 8


def assert_decimal_precision() -> None:
    """`getcontext().prec` 이 28 인지 검증. 다른 값이면 RuntimeError.

    Path β SLO 는 prec=28 을 전제. 테스트 모듈 setup 에서 호출 권장.
    """
    actual = getcontext().prec
    if actual != EXPECTED_PREC:
        raise RuntimeError(
            f"Decimal precision drift detected: expected {EXPECTED_PREC}, got {actual}. "
            "Path β SLO (ADR-013 §4.3) 는 기본 prec=28 을 전제. "
            "getcontext().prec 를 변경하는 외부 코드가 있는지 확인하세요."
        )


def to_decimal(value: Any) -> Decimal:
    """어느 타입이든 `Decimal` 로 안전 변환.

    - int/float → `Decimal(str(value))` (float 공간 우회)
    - str → `Decimal(value)`
    - Decimal → 그대로 반환
    - None → raise ValueError
    - NaN/Inf → raise ValueError

    float 는 의도적으로 `str()` 경유 — `Decimal(0.1)` 이 float 오차
    (`0.1000000000000000055511151231257827021181583404541015625`) 를 전파하는 것
    방지.
    """
    if value is None:
        raise ValueError("to_decimal: None 변환 불가")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"to_decimal: non-finite Decimal {value!r}")
        return value
    if isinstance(value, bool):
        # bool is subclass of int — 숫자 취급 금지
        raise ValueError(f"to_decimal: bool {value!r} 변환 불가 (혼동 위험)")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise ValueError(f"to_decimal: non-finite float {value!r}")
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            result = Decimal(value)
        except Exception as exc:
            raise ValueError(f"to_decimal: str 파싱 실패 {value!r}: {exc}") from exc
        if not result.is_finite():
            raise ValueError(f"to_decimal: non-finite str {value!r}")
        return result
    raise ValueError(f"to_decimal: 지원되지 않는 타입 {type(value).__name__}")


def within_tolerance(actual: Any, expected: Any) -> bool:
    """`actual` 과 `expected` 가 허용 오차 내인지 판정.

    정의 (ADR-013 §4.3 + requirements §3.2):
        `max(절대 ABS_TOL, 상대 REL_TOL)` 내 → True

    입력은 Decimal/int/float/str 모두 허용 — 내부에서 `to_decimal` 로 통일.

    expected == 0 인 경우:
        상대 오차 계산 불가 → 절대 오차만 평가
    """
    a = to_decimal(actual)
    e = to_decimal(expected)
    abs_err = abs(a - e)
    if abs_err < ABS_TOL:
        return True
    if e == 0:
        # 절대 오차가 ABS_TOL 이상 + expected==0 → FAIL
        return False
    rel_err = abs_err / abs(e)
    return rel_err < REL_TOL


def normalize_decimal(value: Any, places: int = DEFAULT_DECIMAL_PLACES) -> str:
    """Decimal 을 fixed-point 자리수로 zero-pad 직렬화 (opus Gate-1 W-1 규약).

    git diff 안정성 + 정규화된 JSON 표현. `Decimal("0.0832")` →
    `"0.08320000"` (8자리 default). 비교 시 `Decimal(str)` 왕복 안전.

    places 는 SLO TL-E-3 허용 오차 (1e-3) 보다 작은 1e-8 로 기본 설정.
    너무 작은 값 (≪ 1e-8) 은 `"0.00000000"` 으로 수렴 — 경고 없음 (의도된 손실).

    NOTE: Decimal.quantize() 는 ROUND_HALF_EVEN (bankers' rounding) 기본.
    regen-time 직렬화에는 일관된 라운딩 규칙이 더 중요.
    """
    d = to_decimal(value)
    quantum = Decimal("1").scaleb(-places)  # e.g. 1e-8 for places=8
    quantized = d.quantize(quantum)
    # Decimal 의 f-string format spec 이 sign 을 올바르게 처리 — 별도 분기 불필요
    return f"{quantized:.{places}f}"


def digest_sequence(values: Any, algo: str = "sha256") -> str:
    """임의 JSON 직렬화 가능 값의 sha256 hex digest (prefix 포함).

    - list / dict / 중첩 구조 모두 지원
    - `sort_keys=True` + `separators=(",", ":")` 으로 정규화
    - Decimal 은 `normalize_decimal` 로 변환 후 직렬화
    - None / bool / int / str / float 은 기본 처리

    반환 예: `"sha256:abc123..."` (SLO TL-E-3 digest 필드 포맷 일치).

    ADR-013 §4.3 — var_series / trades / warnings 의 bar-by-bar 기록을
    baseline 에 저장하기 위한 길이 독립 fingerprint.
    """
    normalized = _normalize_for_json(values)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    hasher = hashlib.new(algo)
    hasher.update(encoded.encode("utf-8"))
    return f"{algo}:{hasher.hexdigest()}"


def _normalize_for_json(value: Any) -> Any:
    """JSON 직렬화를 위해 Decimal 등을 정규화. 재귀."""
    if isinstance(value, Decimal):
        return normalize_decimal(value)
    if isinstance(value, dict):
        return {str(k): _normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_for_json(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return normalize_decimal(value)
    return value
