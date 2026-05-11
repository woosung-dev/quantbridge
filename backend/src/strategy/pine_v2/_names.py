# pine_v2 STDLIB SSOT — 19개 builtin (TA 17 + Utility 2)
"""Single source of truth for pine_v2 stdlib function names.

BL-200 (Sprint 47): pine_v2 STDLIB Triple SSOT 통합 (deepen-modules audit 결론).

이 모듈은 이전에 interpreter.py(`STDLIB_NAMES`) / coverage.py(`_TA_FUNCTIONS` +
`_UTILITY_FUNCTIONS`) 두 군데에 중복 정의되어 있던 19개 stdlib 이름을 단일
소스로 통합한다. interpreter.py 와 coverage.py 는 이제 본 모듈을 re-export 만
한다 (object identity 동일 — `is` 비교 통과).

Import 방향 (cycle 방지):
    _names.py (leaf, 의존성 0)
        ↑
        ├── interpreter.py
        ├── coverage.py
        └── stdlib.py (간접 — runtime dispatch 만 보유, names import X)

새 stdlib 함수 추가 절차:
    1. 본 모듈의 `TA_FUNCTIONS` 또는 `UTILITY_FUNCTIONS` 에 이름 추가.
    2. stdlib.py 의 `_call()` dispatch 분기 1줄 추가.
    3. tests/strategy/pine_v2/test_ssot_invariants.py 4 invariant 자동 검증 통과 확인.

이전 패턴 (interpreter / coverage 양쪽 frozenset literal 동시 갱신) 대비
편집 지점 1곳 + invariant 자동 검증으로 drift 차단.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TA_FUNCTIONS — Pine `ta.*` 종 (interpreter.stdlib._call dispatch 와 1:1).
# 추가 시 stdlib.py 의 `_call` 분기와 본 frozenset 동시 갱신 의무.
# ---------------------------------------------------------------------------
TA_FUNCTIONS: frozenset[str] = frozenset(
    {
        "ta.sma",
        "ta.ema",
        "ta.rma",  # Sprint X1+X3 follow-up (i3_drfx Wilder Running MA)
        "ta.atr",
        "ta.rsi",
        "ta.crossover",
        "ta.crossunder",
        "ta.highest",
        "ta.lowest",
        "ta.change",
        "ta.pivothigh",
        "ta.pivotlow",
        "ta.stdev",
        "ta.variance",
        "ta.sar",  # Sprint X1+X3 W2 (i3_drfx Parabolic SAR)
        "ta.barssince",
        "ta.valuewhen",  # Sprint 8c
        # Sprint 58 BL-241 — real-world indicator 호환성 확장
        "ta.wma",  # Weighted MA (ta.hma 전제)
        "ta.hma",  # Hull MA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
        "ta.bb",  # Bollinger Bands → [upper, basis, lower]
        "ta.cross",  # crossover or crossunder
        "ta.mom",  # Momentum = src - src[length]
        "ta.obv",  # On Balance Volume (attribute 접근 — interpreter 처리)
    }
)

# ---------------------------------------------------------------------------
# UTILITY_FUNCTIONS — Pine `na` / `nz` + Sprint 58 fixnan.
# math.* 는 별도 dispatch (본 set 에 포함 X).
# ---------------------------------------------------------------------------
UTILITY_FUNCTIONS: frozenset[str] = frozenset(
    {
        "na",
        "nz",
        "fixnan",  # Sprint 58 BL-241: 최근 non-nan 값 반환
    }
)

# ---------------------------------------------------------------------------
# STDLIB_NAMES — TA_FUNCTIONS | UTILITY_FUNCTIONS (총 19종, set union).
# interpreter._eval_call 이 Call 노드 디스패치 대상으로 사용.
# ---------------------------------------------------------------------------
STDLIB_NAMES: frozenset[str] = TA_FUNCTIONS | UTILITY_FUNCTIONS
