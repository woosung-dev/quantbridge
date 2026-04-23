"""Decimal-first 허용 오차 유틸 (Path β Trust Layer CI 용).

Stage 1 스켈레톤 — Stage 2 에서 실제 구현.

정책:
- `max(절대 0.001, 상대 0.1%)` 를 통과 기준으로 한다.
- 모든 입력/출력은 Decimal. float 전달 시 즉시 변환 (`Decimal(str(x))`).
- Decimal precision 정책: 기본 `getcontext().prec = 28` 유지. metric 범위
  [1e-4 .. 1e1] 에서 28자리 유효숫자는 충분 (opus Gate-0 W4 반영).
- Sprint 4 D8 "Decimal-first 합산" 원칙 연장: 중간 계산도 Decimal 공간.

사용 예 (Stage 2 구현 이후)::

    from decimal import Decimal
    from backend.tests.strategy.pine_v2._tolerance import within_tolerance

    assert within_tolerance(Decimal("0.1532"), Decimal("0.1535"))  # 상대 0.2% 내
"""

from __future__ import annotations

from decimal import Decimal

# Path β ADR-013 §4.3 + trust-layer-requirements.md §3.2 공식
ABS_TOL: Decimal = Decimal("0.001")
REL_TOL: Decimal = Decimal("0.001")  # 0.1%


def to_decimal(value: object) -> Decimal:
    """어느 타입이든 `Decimal` 로 안전 변환.

    Stage 1 스켈레톤 — Stage 2 에서 정책 확정:
    - int/float → `Decimal(str(value))` (float 공간 우회)
    - str → `Decimal(value)`
    - Decimal → 그대로
    - None/NaN → raise ValueError
    """
    del value  # Stage 1 stub — Stage 2 에서 사용
    raise NotImplementedError("Stage 2 구현 예정 (Path β)")


def within_tolerance(actual: Decimal, expected: Decimal) -> bool:
    """`actual` 과 `expected` 가 허용 오차 내인지 판정.

    정의 (ADR-013 §4.3 + requirements §3.2):
        max(절대 ABS_TOL, 상대 REL_TOL) 내 → True

    Stage 1 스켈레톤 — Stage 2 에서 실제 비교 로직.
    """
    del actual, expected  # Stage 1 stub
    raise NotImplementedError("Stage 2 구현 예정 (Path β)")


def digest_sequence(values: object) -> str:
    """`list[...]` 또는 `dict[str, list[...]]` 를 sha256 hex digest 로 직렬화.

    `var_series`, `trades`, `warnings` 의 bar-by-bar 기록을 baseline 에 저장하기 위한
    길이 독립 fingerprint. 실패 시 artifact 로 전체 dump 를 업로드하는 전제.

    Stage 1 스켈레톤 — Stage 2 에서 JSON 정규화 + sha256 구현.
    """
    del values  # Stage 1 stub
    raise NotImplementedError("Stage 2 구현 예정 (Path β)")
