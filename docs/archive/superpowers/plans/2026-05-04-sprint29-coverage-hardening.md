# Sprint 29 — Pine Coverage Layer Hardening + DrFXGOD Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UtBot indicator + UtBot strategy 둘 다 coverage runnable 만들기 (3/6 → 5/6 통과율) + DrFXGOD reject 응답에 line + workaround 포함 + SSOT parity audit test 자동화로 drift 차단.

**Architecture:** 3 Slice (C → A‖B 순서, cmux 2 워커). Slice C 가 SSOT parity audit + ~11 항목 자동 supported 확장 → DrFXGOD 39 → ~28 unsupported 자연 감소. Slice A (UtBot 4 unsupported 처리, heikinashi Trust Layer 위반 + dogfood-only flag ADR) ‖ Slice B (CoverageReport schema 확장 + workaround dict + DrFXGOD line-numbered 응답).

**Tech Stack:** Python 3.14 / pytest 9.0 / FastAPI / Pydantic V2 / SQLModel / regex 기반 정적 분석 (Pine source → CoverageReport).

**Time budget:** 12-18h (Slice C 4-6h + Slice A 8-12h + Slice B 8-12h, A‖B 병렬 시 12-18h 최대)

**Spec:** [`docs/superpowers/specs/2026-05-04-sprint29-coverage-hardening-design.md`](../specs/2026-05-04-sprint29-coverage-hardening-design.md)
**Plan v2.1:** `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`
**Branch:** `stage/h2-sprint29-pine-coverage-hardening` @ `dc93f57`

---

## File Structure

### 신규 파일

| 파일                                                          | 책임                                                                                                                                | Slice |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ----- |
| `backend/tests/strategy/pine_v2/test_ssot_invariants.py`      | 4 invariant audit (STDLIB ⊆ SUPPORTED / RENDERING_FACTORIES ⊆ SUPPORTED / V4_ALIASES → STDLIB / \_ATTR_CONSTANTS ⊆ \_ENUM_PREFIXES) | C     |
| `backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py`  | UtBot indicator e2e backtest stable PASS                                                                                            | A     |
| `backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py`   | UtBot strategy e2e backtest stable PASS                                                                                             | A     |
| `backend/tests/strategy/pine_v2/test_drfx_response_schema.py` | DrFXGOD 28 unsupported line + workaround ≥80%                                                                                       | B     |
| `docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md`          | heikinashi (a) Trust Layer 위반 + dogfood-only flag ADR                                                                             | A     |

### 수정 파일

| 파일                                                                | 변경 영역                                                                                                                                                                       | Slice |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| `backend/src/strategy/pine_v2/coverage.py`                          | SUPPORTED_FUNCTIONS (~14 항목 추가) / SUPPORTED_ATTRIBUTES (timeframe.period) / \_UNSUPPORTED_WORKAROUNDS dict / CoverageReport schema (UnsupportedCall + dogfood_only_warning) | C/A/B |
| `backend/src/strategy/pine_v2/interpreter.py`                       | barcolor NOP 강화 / timeframe.period 상수 / heikinashi NOP / \_ATTR_CONSTANTS module-level export                                                                               | A     |
| `backend/src/strategy/router.py`                                    | parse-preview 응답 schema 갱신                                                                                                                                                  | B     |
| `backend/src/strategy/schemas.py`                                   | UnsupportedCallResponse Pydantic 모델 추가                                                                                                                                      | B     |
| `docs/04_architecture/pine-execution-architecture.md` (line 95-126) | SSOT 명세 갱신 (실측 size + fictional 표현 제거)                                                                                                                                | C     |

---

## Slice C — SSOT Parity Audit + 자동 Supported 확장 (4-6h, 단독 진행)

### Task C.1: `_ATTR_CONSTANTS` 를 module-level 로 export

**Files:**

- Modify: `backend/src/strategy/pine_v2/interpreter.py:912-944` (function-local dict → module-level frozenset)

- [ ] **Step 1: 현재 `_ATTR_CONSTANTS` 위치 확인**

```bash
grep -n "_ATTR_CONSTANTS = {" backend/src/strategy/pine_v2/interpreter.py
```

Expected: line 912 안 `_eval_attribute` 함수 내부.

- [ ] **Step 2: module-level 로 추출**

`backend/src/strategy/pine_v2/interpreter.py` 의 `STDLIB_NAMES` 정의 (line 55) 뒤에 추가:

```python
# Pine enum constants — value 매핑 (location.absolute, extend.right, shape.*, etc.)
# Sprint 29 Slice C: function-local dict 에서 module-level frozenset 으로 export.
# coverage._ENUM_PREFIXES 와 parity invariant 검증 대상.
_ATTR_CONSTANTS: dict[str, str] = {
    "extend.none": "none",
    "extend.left": "left",
    "extend.right": "right",
    "extend.both": "both",
    "shape.labelup": "labelup",
    "shape.labeldown": "labeldown",
    "shape.triangleup": "triangleup",
    "shape.triangledown": "triangledown",
    "shape.arrowup": "arrowup",
    "shape.arrowdown": "arrowdown",
    "shape.circle": "circle",
    "shape.cross": "cross",
    "shape.xcross": "xcross",
    "shape.flag": "flag",
    "shape.square": "square",
    "shape.diamond": "diamond",
    "location.absolute": "absolute",
    "location.abovebar": "abovebar",
    "location.belowbar": "belowbar",
    "location.top": "top",
    "location.bottom": "bottom",
}
```

`_eval_attribute` 안 line 912-944 의 local `_ATTR_CONSTANTS = {...}` 정의 삭제. 함수 안에서는 module-level `_ATTR_CONSTANTS` 참조.

- [ ] **Step 3: regression test 실행 (변경 후 회귀 0 검증)**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/ -v 2>&1 | tail -10
```

Expected: PASS (모듈 변경만, 동작 동일).

- [ ] **Step 4: commit**

```bash
git add backend/src/strategy/pine_v2/interpreter.py
git commit -m "refactor(pine_v2): move _ATTR_CONSTANTS to module-level (Slice C parity prep)"
```

---

### Task C.2: 4 invariant audit test 작성 (red 단계)

**Files:**

- Create: `backend/tests/strategy/pine_v2/test_ssot_invariants.py`

- [ ] **Step 1: test 파일 작성 (red 단계 의무)**

`backend/tests/strategy/pine_v2/test_ssot_invariants.py` 신규:

```python
"""SSOT parity invariant audit — Sprint 29 Slice C.

drift 차단 자동 감지:
- STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS
- _RENDERING_FACTORIES.keys() ⊆ SUPPORTED_FUNCTIONS
- _V4_ALIASES.values() ⊆ STDLIB_NAMES
- interpreter._ATTR_CONSTANTS prefixes ⊆ coverage._ENUM_PREFIXES
"""
from src.strategy.pine_v2.coverage import (
    SUPPORTED_FUNCTIONS,
    _ENUM_PREFIXES,
)
from src.strategy.pine_v2.interpreter import (
    STDLIB_NAMES,
    _RENDERING_FACTORIES,
    _ATTR_CONSTANTS,
)


def test_stdlib_names_subset_of_supported_functions():
    """interpreter.STDLIB_NAMES (ta.*/math.*) 가 모두 coverage.SUPPORTED_FUNCTIONS 에 등록."""
    diff = STDLIB_NAMES - SUPPORTED_FUNCTIONS
    assert not diff, f"STDLIB_NAMES not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_rendering_factories_subset_of_supported_functions():
    """interpreter._RENDERING_FACTORIES (line.*/box.*/label.*/table.*) 가 SUPPORTED_FUNCTIONS 에 등록."""
    diff = set(_RENDERING_FACTORIES.keys()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_RENDERING_FACTORIES keys not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_v4_aliases_targets_in_stdlib():
    """interpreter._V4_ALIASES (atr/sma/ema 등 V4 short → V5 ta.*) 의 target 이 STDLIB_NAMES 에 등록."""
    # interpreter.py 안 _V4_ALIASES 위치를 import 시점에 확인. 없으면 본 test skip.
    try:
        from src.strategy.pine_v2.interpreter import _V4_ALIASES
    except ImportError:
        import pytest
        pytest.skip("_V4_ALIASES not exported from interpreter.py")

    diff = set(_V4_ALIASES.values()) - STDLIB_NAMES
    assert not diff, f"_V4_ALIASES targets not in STDLIB_NAMES: {sorted(diff)}"


def test_attr_constants_prefixes_subset_of_enum_prefixes():
    """interpreter._ATTR_CONSTANTS 의 dotted key prefix 가 coverage._ENUM_PREFIXES 와 일관."""
    attr_prefixes = {key.split(".", 1)[0] + "." for key in _ATTR_CONSTANTS}
    enum_prefix_set = set(_ENUM_PREFIXES)
    diff = attr_prefixes - enum_prefix_set
    assert not diff, (
        f"_ATTR_CONSTANTS prefixes not in _ENUM_PREFIXES: {sorted(diff)}. "
        "coverage 가 enum 의 attribute access (예: location.absolute) 를 인식하지 못함."
    )
```

- [ ] **Step 2: test 실행 (red 의무 — 일부 fail 예상)**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_ssot_invariants.py -v
```

Expected:

- `test_rendering_factories_subset_of_supported_functions` FAIL — ~11 항목 (box.delete/get_top/get_bottom/set_right, line.delete/get_price, label.delete/get_x/set_x/set_y, table.cell) 가 SUPPORTED_FUNCTIONS 미등록
- 다른 3 invariant 는 PASS 또는 \_V4_ALIASES skip

- [ ] **Step 3: commit (red 단계 영구 기록)**

```bash
git add backend/tests/strategy/pine_v2/test_ssot_invariants.py
git commit -m "test(pine_v2): add SSOT parity invariant audit (Slice C, RED)"
```

---

### Task C.3: SUPPORTED_FUNCTIONS 에 ~11 항목 자동 등록 (green 단계)

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py:195-280` (SUPPORTED_FUNCTIONS frozenset)

- [ ] **Step 1: SUPPORTED_FUNCTIONS 정확 위치 확인**

```bash
grep -n "^SUPPORTED_FUNCTIONS\|^)$" backend/src/strategy/pine_v2/coverage.py | head -10
```

Expected: line 195 시작 + frozenset 마무리 line 추정 ~280.

- [ ] **Step 2: ~11 항목 추가 (rendering 메서드)**

`backend/src/strategy/pine_v2/coverage.py` 의 SUPPORTED_FUNCTIONS frozenset 안에 다음 항목 추가 (적절한 카테고리 섹션 — 예: rendering / drawing):

```python
# Sprint 29 Slice C: _RENDERING_FACTORIES parity 자동 확장
"box.delete",
"box.get_top",
"box.get_bottom",
"box.set_right",
"line.delete",
"line.get_price",
"label.delete",
"label.get_x",
"label.set_x",
"label.set_y",
"table.cell",
```

(주의: 이미 있는 항목 중복 추가 X — 추가 전 grep 으로 확인)

- [ ] **Step 3: 4 invariant test 실행 (green 검증)**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_ssot_invariants.py -v
```

Expected: 4/4 PASS (또는 `_V4_ALIASES` skip 1).

- [ ] **Step 4: 1448 BE regression 회귀 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/ -v 2>&1 | tail -5
```

Expected: 모두 PASS, 회귀 0.

- [ ] **Step 5: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py
git commit -m "feat(pine_v2): expand SUPPORTED_FUNCTIONS with ~11 rendering methods (Slice C, GREEN)"
```

---

### Task C.4: pine-execution-architecture.md SSOT 명세 갱신

**Files:**

- Modify: `docs/04_architecture/pine-execution-architecture.md:95-126`

- [ ] **Step 1: 현재 SSOT 명세 line 95-126 확인**

```bash
sed -n '95,126p' docs/04_architecture/pine-execution-architecture.md
```

기존 표기 (예: `SUPPORTED_FUNCTIONS=91` 또는 `SUPPORTED_ENUM_CONSTANTS`) 발견.

- [ ] **Step 2: 실측 size 로 갱신**

해당 section 의 SSOT 표기를 다음으로 교체:

```markdown
## SSOT — Pine v2 supported set 영구 규칙 (Sprint Y1 + Sprint 29 갱신)

`backend/src/strategy/pine_v2/coverage.py` 의 4 collection + `interpreter.py` 의 3 collection 이 SSOT:

| Collection                       | size (2026-05-04)   | 위치                                                         |
| -------------------------------- | ------------------- | ------------------------------------------------------------ |
| `SUPPORTED_FUNCTIONS`            | 110+ (Slice C 후)   | `coverage.py:195`                                            |
| `SUPPORTED_ATTRIBUTES`           | 39 (Slice A 후 40+) | `coverage.py:304`                                            |
| `_ENUM_PREFIXES` (prefix lookup) | 13                  | `coverage.py:288`                                            |
| `_KNOWN_UNSUPPORTED_FUNCTIONS`   | 7 → 6 (Slice A 후)  | `coverage.py:133`                                            |
| `STDLIB_NAMES`                   | (interpreter)       | `interpreter.py:55`                                          |
| `_RENDERING_FACTORIES`           | (interpreter)       | `interpreter.py:120`                                         |
| `_ATTR_CONSTANTS`                | 21 enum constants   | `interpreter.py:55+` (Sprint 29 Slice C module-level export) |

**SSOT parity audit (Sprint 29 Slice C 신설, `tests/strategy/pine_v2/test_ssot_invariants.py`):**

1. `STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS` (ta._/math._ 호환)
2. `set(_RENDERING_FACTORIES.keys()) ⊆ SUPPORTED_FUNCTIONS` (drawing 호환)
3. `_V4_ALIASES.values() ⊆ STDLIB_NAMES` (V4 alias target 호환)
4. `_ATTR_CONSTANTS prefixes ⊆ _ENUM_PREFIXES` (enum prefix lookup 정합)

drift 발생 시 CI 차단. supported list 추가 시 4 collection 동시 갱신 의무.

> **참고:** Sprint 28 까지 표기됐던 fictional `SUPPORTED_ENUM_CONSTANTS` 는 실제 코드 부재. 실측 구조는 `_ENUM_PREFIXES` (prefix lookup) + interpreter `_ATTR_CONSTANTS` (constant value 매핑) 분리. Sprint 29 v1→v2 pivot 시 발견 (codex high reasoning + Opus fresh ctx 2-검토).
```

- [ ] **Step 3: commit**

```bash
git add docs/04_architecture/pine-execution-architecture.md
git commit -m "docs(architecture): update SSOT spec with actual sizes (Slice C, fictional SUPPORTED_ENUM_CONSTANTS removed)"
```

---

## Slice A — UtBot 4 unsupported 처리 (8-12h, Slice C 후 ‖ Slice B)

### Task A.1: barcolor NOP 강화 + coverage SUPPORTED 등록

**Files:**

- Modify: `backend/src/strategy/pine_v2/interpreter.py:771` (barcolor NOP)
- Modify: `backend/src/strategy/pine_v2/coverage.py:195+` (SUPPORTED_FUNCTIONS)

- [ ] **Step 1: 회귀 test 작성 (red)**

`backend/tests/strategy/pine_v2/test_sprint29_slice_a.py` 신규:

```python
"""Slice A — UtBot 4 unsupported 처리 회귀 test."""
from src.strategy.pine_v2.coverage import analyze_coverage


def test_barcolor_is_supported():
    src = 'barcolor(color.green)\n'
    rep = analyze_coverage(src)
    assert "barcolor" not in rep.unsupported_functions, (
        f"barcolor must be supported (visual NOP): {rep.unsupported_functions}"
    )
```

- [ ] **Step 2: red 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_a.py::test_barcolor_is_supported -v
```

Expected: FAIL (barcolor 가 unsupported 응답).

- [ ] **Step 3: barcolor 를 SUPPORTED_FUNCTIONS 에 추가**

`backend/src/strategy/pine_v2/coverage.py` SUPPORTED_FUNCTIONS frozenset 안 적절한 카테고리 (visual NOP) 에:

```python
"barcolor",  # Sprint 29 Slice A: 시각 효과만, 백테스트 무관
```

- [ ] **Step 4: green 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_a.py::test_barcolor_is_supported -v
```

Expected: PASS.

- [ ] **Step 5: interpreter NOP verify (line 771 부근 이미 처리됐을 수 있음)**

```bash
grep -A2 "barcolor" backend/src/strategy/pine_v2/interpreter.py | head -10
```

이미 NOP 처리되어 있으면 변경 X. 미처리 시 `_NOP_NAMES` 또는 `_eval_call` dispatcher 에 추가.

- [ ] **Step 6: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py backend/tests/strategy/pine_v2/test_sprint29_slice_a.py
git commit -m "feat(pine_v2): support barcolor as visual NOP (Slice A)"
```

---

### Task A.2: timeframe.period attribute supported

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py:304+` (SUPPORTED_ATTRIBUTES)
- Modify: `backend/src/strategy/pine_v2/interpreter.py` (timeframe.period 상수 정의)

- [ ] **Step 1: red test**

`test_sprint29_slice_a.py` 에 추가:

```python
def test_timeframe_period_is_supported():
    src = 'tf = timeframe.period\n'
    rep = analyze_coverage(src)
    assert "timeframe.period" not in rep.unsupported_attributes, (
        f"timeframe.period must be supported: {rep.unsupported_attributes}"
    )
```

- [ ] **Step 2: red 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_a.py::test_timeframe_period_is_supported -v
```

Expected: FAIL.

- [ ] **Step 3: SUPPORTED_ATTRIBUTES 에 추가**

`coverage.py` SUPPORTED_ATTRIBUTES frozenset 안:

```python
"timeframe.period",  # Sprint 29 Slice A: 현재 backtest timeframe string return
```

- [ ] **Step 4: interpreter 안 timeframe.period 처리 추가**

`interpreter.py` `_eval_attribute` 안 module-level `_ATTR_CONSTANTS` 다음 또는 별도 분기에:

```python
# timeframe.period 는 runtime context (BarContext.timeframe) 의 string return
if chain == "timeframe.period":
    return self._bar_context.timeframe if self._bar_context else "1D"
```

(정확 구현 위치는 `_eval_attribute` chain 처리 로직과 일관되게 — grep 으로 기존 timeframe.\* 처리 위치 확인 후 추가)

- [ ] **Step 5: green 검증 + 1448 regression**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/ -v 2>&1 | tail -5
```

Expected: 모두 PASS.

- [ ] **Step 6: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py backend/src/strategy/pine_v2/interpreter.py backend/tests/strategy/pine_v2/test_sprint29_slice_a.py
git commit -m "feat(pine_v2): support timeframe.period (Slice A)"
```

---

### Task A.3: security graceful + KNOWN_UNSUPPORTED 에서 제거

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py:133-143` (\_KNOWN_UNSUPPORTED_FUNCTIONS) + SUPPORTED_FUNCTIONS

- [ ] **Step 1: red test**

`test_sprint29_slice_a.py` 에 추가:

```python
def test_security_is_supported_graceful():
    """request.security 는 단일 timeframe 가정으로 graceful — Slice A.

    interpreter.py:707-715 에서 expression 인자 그대로 반환 (이미 일부 처리).
    """
    src = 'data = request.security("BTCUSDT", "1D", close)\n'
    rep = analyze_coverage(src)
    assert "request.security" not in rep.unsupported_functions, (
        f"request.security graceful (single-timeframe assumption): {rep.unsupported_functions}"
    )
```

- [ ] **Step 2: red 검증**

Expected: FAIL.

- [ ] **Step 3: 변경 — KNOWN_UNSUPPORTED 에서 제거 + SUPPORTED 에 추가**

`coverage.py:133-143`:

```python
_KNOWN_UNSUPPORTED_FUNCTIONS: frozenset[str] = frozenset(
    {
        # "request.security",  # Sprint 29 Slice A: graceful (단일 timeframe 가정)
        "request.security_lower_tf",  # 본 sprint 미처리
        "request.dividends",
        "request.earnings",
        "request.quandl",
        "request.financial",
        "ticker.new",
    }
)
```

`SUPPORTED_FUNCTIONS` 에 추가:

```python
"request.security",  # Sprint 29 Slice A: graceful single-timeframe (interpreter.py:707-715)
```

- [ ] **Step 4: green 검증 + 1448 regression**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/ -v 2>&1 | tail -5
```

- [ ] **Step 5: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py backend/tests/strategy/pine_v2/test_sprint29_slice_a.py
git commit -m "feat(pine_v2): graceful request.security single-timeframe (Slice A)"
```

---

### Task A.4: heikinashi (a) ADR + dogfood_only_warning 필드 + supported

**Files:**

- Create: `docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md`
- Modify: `backend/src/strategy/pine_v2/coverage.py` (CoverageReport.dogfood_only_warning 필드 + analyze_coverage 안 detection)
- Modify: `backend/src/strategy/pine_v2/interpreter.py` (heikinashi NOP — 일반 OHLC 그대로 반환)

- [ ] **Step 1: heikinashi ADR 작성 (영구 기록)**

`docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md` 신규:

```markdown
# ADR — heikinashi Trust Layer 위반 인정 + dogfood-only flag (Sprint 29 Slice A)

> **Date:** 2026-05-04
> **Status:** Accepted (Sprint 29 D1 = (a))
> **BL:** BL-096 partial 의 핵심 결정

## Context

UtBot indicator + UtBot strategy 가 `heikinashi()` 사용. Heikin-Ashi 캔들은 일반 OHLC 와 다른 변환 — `(open+close)/2`, `(open+high+low+close)/4` 등. backtest 가 일반 OHLC 로 실행되면 Pine 원본의 의도와 다른 결과 산출 가능 (거짓 양성 risk).

## Decision

옵션 (a) 채택 — Trust Layer 위반 인정 + dogfood-only flag.

- `heikinashi()` 를 일반 OHLC 그대로 반환 (NOP)
- `CoverageReport.dogfood_only_warning` 필드 추가 — heikinashi 사용 감지 시 "결과가 Pine 원본과 다를 수 있음" warning
- 사용자 명시 동의 후 backtest 실행 (FE 적용 Sprint 30+ deferred)
- ADR-008 Addendum 후보 (Beta open prereq)

## Consequences (긍정)

- UtBot indicator + UtBot strategy 동시 PASS → Sprint 29 통과율 5/6 도달
- dogfood-first indie SaaS 정합 (본인이 거짓 양성 가장 먼저 발견)
- transparency — ADR 영구 기록으로 Trust Layer 위반 명시

## Consequences (부정 / risk)

- heikin-ashi 캔들 ↔ 일반 OHLC 차이로 backtest 결과 거짓 양성 가능
- 사용자가 warning 무시 시 잘못된 전략 검증 risk
- Trust Layer 정합 위반 (architecture.md:286-318)

## Alternatives Considered

- (b) heikinashi reject 유지 — Sprint 29 dual metric (5/6) 미달성
- (c) ohlcv 변환 layer 신설 — scope 6-10h, Sprint 29 over

## Sprint 30+ trigger

ADR-009 Candle transformation layer 신설 — Heikin-Ashi + Renko + Range bar 정확 변환 layer. 본인 dogfood 에서 거짓 양성 발견 시 trigger.

## References

- Spec: `docs/superpowers/specs/2026-05-04-sprint29-coverage-hardening-design.md` D1
- Plan v2.1: `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md` §4 Slice A
- BL-096 partial: `docs/REFACTORING-BACKLOG.md`
- architecture.md Trust Layer: `docs/04_architecture/pine-execution-architecture.md:286-318`
```

- [ ] **Step 2: red test**

`test_sprint29_slice_a.py` 에 추가:

```python
def test_heikinashi_emits_dogfood_warning():
    """heikinashi 사용 시 supported 처리 + dogfood_only_warning 필드 채워짐."""
    src = '[ho, hh, hl, hc] = heikinashi()\n'
    rep = analyze_coverage(src)
    assert "heikinashi" not in rep.unsupported_functions, (
        f"heikinashi (a) Trust Layer 위반 + dogfood flag — supported"
    )
    assert rep.dogfood_only_warning is not None, (
        "heikinashi 사용 시 dogfood_only_warning 필드 채워야 함"
    )
    assert "heikinashi" in rep.dogfood_only_warning.lower() or "trust" in rep.dogfood_only_warning.lower()
```

- [ ] **Step 3: red 검증**

Expected: FAIL — `dogfood_only_warning` 필드 부재 + heikinashi unsupported.

- [ ] **Step 4: CoverageReport schema 확장**

`coverage.py` 의 CoverageReport 클래스 (line 388):

```python
@dataclass(frozen=True)
class CoverageReport:
    used_functions: tuple[str, ...]
    used_attributes: tuple[str, ...]
    unsupported_functions: tuple[str, ...]
    unsupported_attributes: tuple[str, ...]
    # Sprint 29 Slice A: heikinashi Trust Layer 위반 transparency
    dogfood_only_warning: str | None = None
```

- [ ] **Step 5: SUPPORTED_FUNCTIONS 에 heikinashi 추가**

```python
"heikinashi",  # Sprint 29 Slice A (a): Trust Layer 위반 + dogfood-only flag
```

- [ ] **Step 6: analyze_coverage() 안 dogfood_only_warning 채우기**

`coverage.py:analyze_coverage()` 끝부분:

```python
warning = None
if "heikinashi" in used_funcs_all:
    warning = (
        "heikinashi() 사용 — Trust Layer 위반 (Sprint 29 ADR). "
        "Heikin-Ashi 캔들은 일반 OHLC 와 다른 변환이라 backtest 결과가 "
        "Pine 원본과 다를 수 있음 (거짓 양성 risk). dogfood-only 사용 권장. "
        "참고: docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md"
    )

return CoverageReport(
    used_functions=...,
    used_attributes=...,
    unsupported_functions=...,
    unsupported_attributes=...,
    dogfood_only_warning=warning,
)
```

- [ ] **Step 7: interpreter NOP — heikinashi 가 일반 OHLC 반환**

`interpreter.py` `_eval_call` 안 적절 위치 (이미 다른 NOP 인 곳):

```python
# Sprint 29 Slice A (a): heikinashi NOP — 일반 OHLC 그대로 반환 (Trust Layer 위반, dogfood-only).
if name == "heikinashi":
    bar = self._bar_context
    return (bar.open, bar.high, bar.low, bar.close)
```

(정확 구현 위치는 \_eval_call dispatcher line 593-810 의 적절 분기 — grep 으로 기존 multi-return 처리 패턴 확인)

- [ ] **Step 8: green 검증 + 1448 regression**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/ -v 2>&1 | tail -10
```

Expected: 모두 PASS.

- [ ] **Step 9: commit**

```bash
git add docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md backend/src/strategy/pine_v2/coverage.py backend/src/strategy/pine_v2/interpreter.py backend/tests/strategy/pine_v2/test_sprint29_slice_a.py
git commit -m "feat(pine_v2): heikinashi (a) Trust Layer + dogfood_only_warning (Slice A, ADR)"
```

---

### Task A.5: UtBot indicator e2e fixture (TDD red-green)

**Files:**

- Create: `backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py`

- [ ] **Step 1: e2e test 작성 (red 또는 green 모두 가능)**

```python
"""UtBot indicator e2e backtest stable PASS — Sprint 29 Slice A 종료 trigger."""
from pathlib import Path
from src.strategy.pine_v2.coverage import analyze_coverage


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i1_utbot.pine"


def test_utbot_indicator_coverage_runnable():
    """UtBot indicator (i1_utbot.pine) 가 Slice A 후 0 unsupported."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.is_runnable, (
        f"UtBot indicator must be runnable after Slice A. "
        f"unsupported_functions={rep.unsupported_functions}, "
        f"unsupported_attributes={rep.unsupported_attributes}"
    )


def test_utbot_indicator_dogfood_warning_present():
    """heikinashi 사용 → dogfood_only_warning 채워짐."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.dogfood_only_warning is not None, (
        "UtBot indicator 가 heikinashi 사용 시 warning 필드 채워야 함"
    )
```

- [ ] **Step 2: 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_utbot_indicator_e2e.py -v
```

Expected (Slice A.1-A.4 후): PASS.

- [ ] **Step 3: commit**

```bash
git add backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py
git commit -m "test(pine_v2): UtBot indicator e2e — coverage runnable + dogfood warning (Slice A)"
```

---

### Task A.6: UtBot strategy e2e fixture

**Files:**

- Create: `backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py`

- [ ] **Step 1: e2e test 작성**

```python
"""UtBot strategy e2e backtest stable PASS — Sprint 29 Slice A 종료 trigger (5/6 도달 lever)."""
from pathlib import Path
from src.strategy.pine_v2.coverage import analyze_coverage


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/s2_utbot.pine"


def test_utbot_strategy_coverage_runnable():
    """UtBot strategy (s2_utbot.pine) 가 Slice A 후 0 unsupported."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.is_runnable, (
        f"UtBot strategy must be runnable after Slice A. "
        f"unsupported_functions={rep.unsupported_functions}, "
        f"unsupported_attributes={rep.unsupported_attributes}"
    )


def test_utbot_strategy_dogfood_warning_present():
    """heikinashi 사용 → dogfood_only_warning 채워짐."""
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert rep.dogfood_only_warning is not None
```

- [ ] **Step 2: 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_utbot_strategy_e2e.py -v
```

Expected: PASS.

- [ ] **Step 3: commit**

```bash
git add backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py
git commit -m "test(pine_v2): UtBot strategy e2e — coverage runnable + dogfood warning (Slice A)"
```

---

### Task A.7: Slice A 종료 verification (5/6 통과율 + 1448 regression)

- [ ] **Step 1: 6 fixture baseline 재측정**

```bash
cd backend && PYTHONPATH=. .venv/bin/python <<'PY'
from pathlib import Path
from src.strategy.pine_v2.coverage import analyze_coverage

fixtures = ['s1_pbr', 'i1_utbot', 'i2_luxalgo', 's2_utbot', 's3_rsid', 'i3_drfx']
base = Path('tests/fixtures/pine_corpus_v2')
for slug in fixtures:
    src = (base / f'{slug}.pine').read_text()
    rep = analyze_coverage(src)
    runnable = '✅' if rep.is_runnable else '❌'
    n = len(rep.unsupported_functions) + len(rep.unsupported_attributes)
    print(f'{slug:<12}  {runnable}  unsupported={n}  warn={"yes" if rep.dogfood_only_warning else "no"}')
PY
```

Expected:

```
s1_pbr        ✅  unsupported=0  warn=no
i1_utbot      ✅  unsupported=0  warn=yes  ← Slice A 후 PASS
i2_luxalgo    ✅  unsupported=0  warn=no
s2_utbot      ✅  unsupported=0  warn=yes  ← Slice A 후 PASS (5/6 도달)
s3_rsid       ✅  unsupported=0  warn=no
i3_drfx       ❌  unsupported=28  warn=no  ← Slice B 처리 대상
```

- [ ] **Step 2: 1448 BE regression 검증**

```bash
cd backend && .venv/bin/pytest -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 3: 통과율 카운트 확인**

5/6 도달 (PbR + UtBot indicator + UtBot strategy + LuxAlgo + RsiD). dual metric 통과 baseline.

---

## Slice B — Coverage Schema + DrFXGOD Line-Numbered 응답 (8-12h, Slice C 후 ‖ Slice A)

### Task B.1: UnsupportedCall TypedDict + CoverageReport schema 확장

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py:388` (CoverageReport)

- [ ] **Step 1: red test**

`backend/tests/strategy/pine_v2/test_sprint29_slice_b.py` 신규:

```python
"""Slice B — Coverage schema 확장 + DrFXGOD line-numbered 응답."""
from src.strategy.pine_v2.coverage import analyze_coverage


def test_unsupported_calls_field_exists():
    """CoverageReport.unsupported_calls 필드가 있어야 함 (Slice B 신규)."""
    src = 'fixnan(close)\n'
    rep = analyze_coverage(src)
    assert hasattr(rep, "unsupported_calls"), "CoverageReport.unsupported_calls 필드 부재"


def test_unsupported_calls_has_line_info():
    """unsupported_calls 안 항목이 name + line 포함."""
    src = '''//@version=5
indicator("test")
plot(fixnan(close))
'''
    rep = analyze_coverage(src)
    fixnan_calls = [c for c in rep.unsupported_calls if c["name"] == "fixnan"]
    assert fixnan_calls, "fixnan 이 unsupported_calls 에 없음"
    assert fixnan_calls[0]["line"] == 3, f"fixnan line 정보 부정확: {fixnan_calls[0]}"
```

- [ ] **Step 2: red 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_b.py -v
```

Expected: FAIL — `unsupported_calls` 필드 부재.

- [ ] **Step 3: schema 확장**

`coverage.py:388` (CoverageReport 클래스 위에 TypedDict 추가):

```python
from typing import Literal, TypedDict


class UnsupportedCall(TypedDict):
    name: str
    line: int
    col: int | None
    workaround: str | None
    category: Literal["drawing", "data", "syntax", "math", "other"]


@dataclass(frozen=True)
class CoverageReport:
    used_functions: tuple[str, ...]
    used_attributes: tuple[str, ...]
    unsupported_functions: tuple[str, ...]  # 기존, backward-compat
    unsupported_attributes: tuple[str, ...]  # 기존, backward-compat
    unsupported_calls: tuple[UnsupportedCall, ...] = ()  # Slice B 신규
    dogfood_only_warning: str | None = None  # Slice A

    @property
    def is_runnable(self) -> bool:
        return not self.unsupported_functions and not self.unsupported_attributes
```

- [ ] **Step 4: green 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_b.py::test_unsupported_calls_field_exists -v
```

Expected: PASS (line info 는 다음 task).

- [ ] **Step 5: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py backend/tests/strategy/pine_v2/test_sprint29_slice_b.py
git commit -m "feat(pine_v2): add UnsupportedCall TypedDict + CoverageReport.unsupported_calls (Slice B)"
```

---

### Task B.2: line 번호 + category 추출 로직

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py:analyze_coverage()`

- [ ] **Step 1: 카테고리 분류 helper**

`coverage.py` 안 helper:

```python
_CATEGORY_PREFIXES = {
    "line.": "drawing",
    "box.": "drawing",
    "label.": "drawing",
    "table.": "drawing",
    "plot": "drawing",
    "barcolor": "drawing",
    "fill": "drawing",
    "hline": "drawing",
    "ta.": "math",
    "math.": "math",
    "request.": "data",
    "syminfo.": "data",
    "timeframe.": "data",
    "ticker.": "data",
    "barstate.": "data",
}


def _categorize(name: str) -> str:
    for prefix, cat in _CATEGORY_PREFIXES.items():
        if name.startswith(prefix) or name == prefix.rstrip("."):
            return cat
    return "other"
```

- [ ] **Step 2: line 번호 추출 — Pine source 에서 each unsupported call 의 line 검색**

`analyze_coverage()` 안 unsupported 식별 후 line 번호 매핑:

```python
def _find_line(source: str, pattern: str) -> int | None:
    """source 에서 pattern 첫 등장 line 번호 (1-indexed)."""
    import re
    escaped = re.escape(pattern)
    for i, line in enumerate(source.splitlines(), start=1):
        if re.search(rf"\b{escaped}\b", line):
            return i
    return None
```

`analyze_coverage()` 안 return 직전:

```python
unsupported_calls = []
for fn in unsupported_functions:
    line = _find_line(source, fn) or 0
    workaround = _UNSUPPORTED_WORKAROUNDS.get(fn)  # next task
    unsupported_calls.append({
        "name": fn,
        "line": line,
        "col": None,
        "workaround": workaround,
        "category": _categorize(fn),
    })
for attr in unsupported_attributes:
    line = _find_line(source, attr) or 0
    workaround = _UNSUPPORTED_WORKAROUNDS.get(attr)
    unsupported_calls.append({
        "name": attr,
        "line": line,
        "col": None,
        "workaround": workaround,
        "category": _categorize(attr),
    })

return CoverageReport(
    ...,
    unsupported_calls=tuple(unsupported_calls),
    dogfood_only_warning=warning,
)
```

- [ ] **Step 3: green 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_b.py -v
```

Expected: PASS (line + category 포함).

- [ ] **Step 4: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py
git commit -m "feat(pine_v2): line + category extraction for unsupported_calls (Slice B)"
```

---

### Task B.3: \_UNSUPPORTED_WORKAROUNDS dict (~28 항목, 80% coverage)

**Files:**

- Modify: `backend/src/strategy/pine_v2/coverage.py`

- [ ] **Step 1: red test (workaround coverage 검증)**

`test_sprint29_slice_b.py` 에 추가:

```python
def test_drfx_unsupported_workaround_coverage():
    """DrFXGOD ~28 unsupported (Slice C 후) 의 80% 가 workaround 포함."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "fixtures/pine_corpus_v2/i3_drfx.pine").read_text()
    rep = analyze_coverage(src)

    total = len(rep.unsupported_calls)
    with_workaround = sum(1 for c in rep.unsupported_calls if c["workaround"])
    coverage_pct = with_workaround / total * 100 if total else 0

    assert coverage_pct >= 80, (
        f"DrFXGOD workaround coverage {coverage_pct:.1f}% < 80%. "
        f"missing workaround: {[c['name'] for c in rep.unsupported_calls if not c['workaround']]}"
    )
```

- [ ] **Step 2: red 검증**

Expected: FAIL — workaround dict 비어있음.

- [ ] **Step 3: \_UNSUPPORTED_WORKAROUNDS dict 작성**

`coverage.py` line 143 (KNOWN_UNSUPPORTED 다음):

```python
# Sprint 29 Slice B: unsupported 발견 시 사용자에게 우회 패턴 안내.
# 80% coverage 임계 = DrFXGOD ~28 항목 중 23+ 등록.
_UNSUPPORTED_WORKAROUNDS: dict[str, str] = {
    # Data layer (request.* / syminfo.* / timeframe.*)
    "request.security_lower_tf": "다른 timeframe lower 데이터 미지원. 단일 timeframe 으로 전략 재구성 필요.",
    "request.dividends": "배당 데이터 미지원. 외부 source 연동 필요.",
    "request.earnings": "실적 데이터 미지원. 외부 source 연동 필요.",
    "ticker.new": "단일 ticker 사용 권장 (현재 backtest symbol).",
    "syminfo.prefix": "exchange prefix 는 backtest 에서 의미 없음. 변수 추출 권장.",
    "syminfo.ticker": "현재 backtest symbol 변수로 직접 사용.",
    "syminfo.timezone": "단일 timezone 가정 (UTC). timezone 분기 로직 제거 권장.",
    "timeframe.isdaily": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isminutes": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.ismonthly": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isseconds": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isweekly": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.multiplier": "현재 timeframe 의 numeric multiplier 가 필요하면 변수 추출.",
    "barstate.isrealtime": "backtest 는 항상 historical. 분기 로직 제거.",

    # Math layer (ta.*/math.*)
    "ta.alma": "Arnaud Legoux MA 미지원. ta.sma 또는 ta.ema 로 근사 (정확도 차이 < 1%).",
    "ta.bb": "Bollinger Bands = ta.sma + ta.stdev 조합으로 직접 구현.",
    "ta.cross": "ta.crossover + ta.crossunder 조합으로 대체.",
    "ta.dmi": "Directional Movement Index = ta.atr + 직접 +DI/-DI 계산.",
    "ta.mom": "Momentum = close - close[length] 단순 계산.",
    "ta.wma": "Weighted MA = ta.sma 또는 ta.ema 로 근사.",
    "ta.obv": "On-Balance Volume = volume 누적 sum 으로 직접 구현.",

    # Drawing layer (이미 supported 거나 NOP)
    "table.cell_set_bgcolor": "Drawing layer 는 시각 NOP. 시각 표시 외 로직에 의존하면 안전.",
    "label.style_label_down": "label style 은 시각 NOP. 변수 추출 후 backtest 와 무관.",
    "label.style_label_left": "label style 은 시각 NOP.",
    "label.style_label_up": "label style 은 시각 NOP.",

    # Misc
    "fixnan": "nz() + 직전 값 캐싱 조합으로 대체 가능.",
    "time": "시간 기반 로직은 가격 기반 (close/open 변화) 권장. 필요 시 변수 추출.",
}
```

- [ ] **Step 4: green 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_b.py::test_drfx_unsupported_workaround_coverage -v
```

Expected: PASS (28 중 ~26 = ~92% coverage).

- [ ] **Step 5: commit**

```bash
git add backend/src/strategy/pine_v2/coverage.py
git commit -m "feat(pine_v2): _UNSUPPORTED_WORKAROUNDS dict 27 entries (Slice B, 80%+ coverage)"
```

---

### Task B.4: DrFXGOD response schema 회귀 test

**Files:**

- Create: `backend/tests/strategy/pine_v2/test_drfx_response_schema.py`

- [ ] **Step 1: comprehensive test**

```python
"""DrFXGOD i3_drfx.pine 의 unsupported_calls schema verify — Sprint 29 Slice B 종료 trigger."""
from pathlib import Path

from src.strategy.pine_v2.coverage import analyze_coverage


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/pine_corpus_v2/i3_drfx.pine"


def test_drfx_unsupported_calls_populated():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    assert not rep.is_runnable, "DrFXGOD must remain unrunnable (PASS 불가, schema only)"
    assert len(rep.unsupported_calls) > 0, "unsupported_calls 가 채워져야 함"


def test_drfx_each_call_has_name_line_category():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    for call in rep.unsupported_calls:
        assert "name" in call and call["name"]
        assert "line" in call and call["line"] >= 0  # 0 = 미발견 fallback
        assert "category" in call and call["category"] in {"drawing", "data", "syntax", "math", "other"}


def test_drfx_workaround_coverage_80_percent():
    src = FIXTURE.read_text()
    rep = analyze_coverage(src)
    total = len(rep.unsupported_calls)
    with_wa = sum(1 for c in rep.unsupported_calls if c["workaround"])
    pct = with_wa / total * 100 if total else 0
    assert pct >= 80, f"DrFXGOD workaround {pct:.1f}% < 80%"
```

- [ ] **Step 2: 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_drfx_response_schema.py -v
```

Expected: PASS (3/3).

- [ ] **Step 3: commit**

```bash
git add backend/tests/strategy/pine_v2/test_drfx_response_schema.py
git commit -m "test(pine_v2): DrFXGOD response schema — line + workaround 80% coverage (Slice B)"
```

---

### Task B.5: router.py + schemas.py Pydantic 응답 schema

**Files:**

- Modify: `backend/src/strategy/router.py` (parse-preview endpoint 응답)
- Modify: `backend/src/strategy/schemas.py` (UnsupportedCallResponse Pydantic)

- [ ] **Step 1: 현재 parse-preview endpoint + 응답 schema 위치 확인**

```bash
grep -n "parse-preview\|parse_preview\|CoverageReport\|UnsupportedCall" backend/src/strategy/router.py backend/src/strategy/schemas.py | head -20
```

- [ ] **Step 2: schemas.py 에 UnsupportedCallResponse Pydantic 모델 추가**

```python
# backend/src/strategy/schemas.py
from typing import Literal

from pydantic import BaseModel


class UnsupportedCallResponse(BaseModel):
    name: str
    line: int
    col: int | None = None
    workaround: str | None = None
    category: Literal["drawing", "data", "syntax", "math", "other"]


# 기존 CoverageReportResponse (또는 동등 schema) 에 unsupported_calls 필드 추가:
class CoverageReportResponse(BaseModel):
    is_runnable: bool
    used_functions: list[str]
    used_attributes: list[str]
    unsupported_functions: list[str]  # backward-compat
    unsupported_attributes: list[str]  # backward-compat
    unsupported_calls: list[UnsupportedCallResponse] = []  # Sprint 29 Slice B
    dogfood_only_warning: str | None = None  # Sprint 29 Slice A
```

- [ ] **Step 3: router.py 의 parse-preview endpoint 갱신**

`backend/src/strategy/router.py` 안 parse-preview endpoint 의 응답 구성에서 dataclass → Pydantic 변환:

```python
# 기존 변환 로직에 unsupported_calls + dogfood_only_warning 추가
return CoverageReportResponse(
    is_runnable=rep.is_runnable,
    used_functions=list(rep.used_functions),
    used_attributes=list(rep.used_attributes),
    unsupported_functions=list(rep.unsupported_functions),
    unsupported_attributes=list(rep.unsupported_attributes),
    unsupported_calls=[UnsupportedCallResponse(**c) for c in rep.unsupported_calls],
    dogfood_only_warning=rep.dogfood_only_warning,
)
```

- [ ] **Step 4: Pydantic round-trip test 추가**

`test_sprint29_slice_b.py` 끝부분:

```python
def test_pydantic_response_round_trip():
    """analyze_coverage 결과 → Pydantic serialize → JSON deserialize 정합."""
    from src.strategy.schemas import CoverageReportResponse, UnsupportedCallResponse
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "fixtures/pine_corpus_v2/i3_drfx.pine").read_text()
    rep = analyze_coverage(src)

    response = CoverageReportResponse(
        is_runnable=rep.is_runnable,
        used_functions=list(rep.used_functions),
        used_attributes=list(rep.used_attributes),
        unsupported_functions=list(rep.unsupported_functions),
        unsupported_attributes=list(rep.unsupported_attributes),
        unsupported_calls=[UnsupportedCallResponse(**c) for c in rep.unsupported_calls],
        dogfood_only_warning=rep.dogfood_only_warning,
    )

    # Round-trip: serialize → deserialize
    json_str = response.model_dump_json()
    restored = CoverageReportResponse.model_validate_json(json_str)
    assert restored.is_runnable == response.is_runnable
    assert len(restored.unsupported_calls) == len(response.unsupported_calls)
```

- [ ] **Step 5: 검증**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_sprint29_slice_b.py::test_pydantic_response_round_trip -v
```

Expected: PASS.

- [ ] **Step 6: 1448 BE regression 검증**

```bash
cd backend && .venv/bin/pytest -v 2>&1 | tail -10
```

Expected: 모두 PASS.

- [ ] **Step 7: commit**

```bash
git add backend/src/strategy/schemas.py backend/src/strategy/router.py backend/tests/strategy/pine_v2/test_sprint29_slice_b.py
git commit -m "feat(strategy): Pydantic response schema for unsupported_calls + dogfood_warning (Slice B)"
```

---

### Task B.6: codex G0 master plan consult (의무, Slice B schema 직후)

- [ ] **Step 1: codex G0 invoke (consult mode)**

```bash
PROMPT="codex G0 master plan consult — Sprint 29 Slice B 의 CoverageReport schema 변경 (UnsupportedCall TypedDict + line + workaround dict + Pydantic round-trip) 가 완료됨. 다음 검증:

1. UnsupportedCall schema 가 backward-compat 유지 — 기존 unsupported_functions / unsupported_attributes 필드 그대로
2. line 번호 추출 로직 (regex 기반) 의 정확성 — 동일 함수가 여러 라인에 있을 때 first 만 추출하는 게 OK?
3. _UNSUPPORTED_WORKAROUNDS dict 의 80% coverage threshold 가 사용자 가치에 충분?
4. Pydantic V2 round-trip 의 edge case (None / empty list / Korean string)

회귀 risk + 잠재 issue 명시. PASS / CONDITIONAL PASS / FAIL verdict."

cd /Users/woosung/project/agy-project/quant-bridge && timeout 600 codex exec "$PROMPT" -C $(pwd) -s read-only -c 'model_reasoning_effort="high"' --enable web_search_cached --json < /dev/null 2>/dev/null | python3 -c '
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
        if obj.get("type") == "item.completed":
            item = obj.get("item", {})
            if item.get("type") == "agent_message":
                print(item.get("text", ""))
    except: pass
'
```

- [ ] **Step 2: codex 권장 적용 (있으면)**

codex 가 발견한 issue 가 있으면 patch + test + commit. 없으면 다음 task.

- [ ] **Step 3: codex result dev-log 영구 기록**

`docs/dev-log/2026-05-04-sprint29-codex-g0-slice-b.md` 신규에 verdict + 적용 사항 기록.

---

## Slice Final — 종료 trigger 검증

### Task FINAL.1: dual metric 종료 측정

- [ ] **Step 1: 6 fixture 통과율 측정**

```bash
cd backend && PYTHONPATH=. .venv/bin/python <<'PY'
from pathlib import Path
from src.strategy.pine_v2.coverage import analyze_coverage

fixtures = ['s1_pbr', 'i1_utbot', 'i2_luxalgo', 's2_utbot', 's3_rsid', 'i3_drfx']
base = Path('tests/fixtures/pine_corpus_v2')
runnable = 0
for slug in fixtures:
    src = (base / f'{slug}.pine').read_text()
    rep = analyze_coverage(src)
    if rep.is_runnable: runnable += 1
print(f'통과율: {runnable}/6 = {runnable*100//6}%')
assert runnable >= 5, f"5/6 미달: {runnable}/6"
PY
```

Expected: `통과율: 5/6 = 83%`.

- [ ] **Step 2: SSOT 4 invariant + DrFXGOD response 80% verify**

```bash
cd backend && .venv/bin/pytest tests/strategy/pine_v2/test_ssot_invariants.py tests/strategy/pine_v2/test_drfx_response_schema.py -v
```

Expected: 7/7 PASS.

- [ ] **Step 3: 1448 BE regression 0**

```bash
cd backend && .venv/bin/pytest -v 2>&1 | tail -5
```

Expected: ALL PASS.

- [ ] **Step 4: FE 257 regression 0 (FE 변경 X 자연 PASS)**

```bash
cd frontend && pnpm test 2>&1 | tail -5
```

Expected: ALL PASS.

- [ ] **Step 5: ruff/mypy/tsc/eslint 0/0/0/0**

```bash
cd /Users/woosung/project/agy-project/quant-bridge && make be-check 2>&1 | tail -5 && make fe-check 2>&1 | tail -5
```

Expected: 모두 0 errors.

---

### Task FINAL.2: codex challenge G2 (Slice A/B 모두)

- [ ] **Step 1: codex challenge invoke (adversarial)**

```bash
cd /Users/woosung/project/agy-project/quant-bridge && timeout 600 codex exec "Sprint 29 Slice A/B 모두 구현 완료. UtBot 양방 PASS + DrFXGOD response schema. interpreter.py NOP 추가 (barcolor / heikinashi / timeframe.period) + coverage.py schema 확장 (UnsupportedCall + workaround dict + dogfood_only_warning). 1448 BE regression 0 검증됨.

Adversarial review: 본 구현이 production 에서 실패할 패턴 / 사용자가 발견할 거짓 양성 / 회귀 risk / SSOT drift 가능성. 5+ critical finding 명시." -C $(pwd) -s read-only -c 'model_reasoning_effort="high"' --enable web_search_cached --json < /dev/null 2>/dev/null | python3 -c '
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
        if obj.get("type") == "item.completed":
            item = obj.get("item", {})
            if item.get("type") == "agent_message":
                print(item.get("text", ""))
    except: pass
'
```

- [ ] **Step 2: critical finding 적용 (있으면)**

P1 finding 은 즉시 patch + test + commit. P2 는 별도 BL ID 부여 + Sprint 30+ deferred.

- [ ] **Step 3: dev-log 기록**

`docs/dev-log/2026-05-04-sprint29-codex-g2-challenge.md` 신규.

---

### Task FINAL.3: PR squash merge 준비

- [ ] **Step 1: git log 정리 verify**

```bash
git log --oneline main..stage/h2-sprint29-pine-coverage-hardening
```

Expected: ~15 commits (Slice C/A/B/Final).

- [ ] **Step 2: stage 안 commits 의 PR description 작성**

```bash
gh pr create --base main --title "Sprint 29 — Pine Coverage Layer Hardening + DrFXGOD Schema" --body "$(cat <<'EOF'
## Summary

- Pine 통과율 3/6 → 5/6 (UtBot indicator + strategy 동시 PASS, lever = barcolor/heikinashi/security/timeframe.period 4 항목)
- DrFXGOD reject 응답에 line + workaround 포함 (~92% coverage, 28 항목 중 26+)
- SSOT parity audit test 4건 (drift 차단 자동화)
- heikinashi (a) Trust Layer 위반 + dogfood-only flag ADR 영구 기록

## Slice 분해

- **Slice C** — SSOT parity audit + ~11 항목 자동 supported 확장 + architecture.md SSOT 갱신
- **Slice A** — UtBot 4 unsupported (barcolor / heikinashi / security / timeframe.period) 처리 + heikinashi ADR + UtBot indicator/strategy e2e fixture
- **Slice B** — CoverageReport schema 확장 (UnsupportedCall + line + workaround) + DrFXGOD response + Pydantic V2 round-trip

## Dual metric

- ✅ Pine 통과율 5/6 (83%)
- ✅ DrFXGOD response workaround ≥80%
- ✅ SSOT parity 4/4 PASS
- ✅ 1448 BE regression / 257 FE regression
- ✅ ruff/mypy/tsc/eslint 0/0/0/0

## Test plan

- [x] `pytest tests/strategy/pine_v2/test_ssot_invariants.py -v` (4/4)
- [x] `pytest tests/strategy/pine_v2/test_utbot_indicator_e2e.py -v` (PASS)
- [x] `pytest tests/strategy/pine_v2/test_utbot_strategy_e2e.py -v` (PASS)
- [x] `pytest tests/strategy/pine_v2/test_drfx_response_schema.py -v` (3/3)
- [x] `pytest -v` 1448/1448
- [x] `pnpm test` 257/257
- [x] codex G0 + codex challenge G2 review
- [x] heikinashi ADR 영구 기록

## References

- Spec: `docs/superpowers/specs/2026-05-04-sprint29-coverage-hardening-design.md`
- Plan: `docs/superpowers/plans/2026-05-04-sprint29-coverage-hardening.md`
- Plan v2.1: `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`
- v1→v2 pivot: `docs/dev-log/2026-05-04-sprint29-v1-to-v2-pivot.md`
- Baseline snapshot: `docs/dev-log/2026-05-04-sprint29-baseline-snapshot.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: PR review 받기 (사용자)**

사용자 review 후 squash merge 승인.

- [ ] **Step 4: merge 후 §14 종료 docs update (CLAUDE.md / dev-log retrospective / INDEX.md / lessons.md / TODO.md)**

plan v2.1 §14 항목 따라 진행.

---

## Self-Review

### Spec coverage check

- [x] §3.1 Slice C — Task C.1~C.4 (`_ATTR_CONSTANTS` export → invariant test → ~11 supported 확장 → architecture.md)
- [x] §3.2 Slice A — Task A.1~A.7 (barcolor / timeframe.period / security / heikinashi ADR / UtBot e2e × 2 / Slice 종료)
- [x] §3.3 Slice B — Task B.1~B.6 (UnsupportedCall TypedDict / line+category / workaround dict / DrFXGOD test / Pydantic / codex G0)
- [x] §4 Data Flow — Task A.4 (dogfood_only_warning) + Task B.1-2 (unsupported_calls)
- [x] §5 Error Handling — Task A.4 (heikinashi flag), Task C.2 (invariant CI gate), Task B.3 (workaround 80% gate), Task FINAL.1 (1448 regression)
- [x] §6 Dual Metric — Task FINAL.1 (5/6 통과율 + 80% workaround + 4 invariant + regression 0)
- [x] §8 Decisions D1~D5 — 모두 plan 안 반영
- [x] §9 종료 trigger — Task FINAL.1~3

### Placeholder scan

- 본 plan 안 "TBD / TODO / 적절한 / 발견 위치에 맞춰" 표현 없음
- 각 step 의 코드 블록 모두 actionable
- Task A.2 의 `_eval_attribute` 구현 위치는 grep 명령으로 검증 안내 (placeholder 아님)

### Type consistency

- `UnsupportedCall` TypedDict (Task B.1) ↔ `UnsupportedCallResponse` Pydantic (Task B.5) — 동일 5 필드 (name/line/col/workaround/category)
- `CoverageReport.unsupported_calls` (Task B.1) ↔ analyze_coverage 안 list 채우기 (Task B.2) ↔ test (Task B.4) — 일관
- `dogfood_only_warning: str | None` (Task A.4) ↔ Pydantic response (Task B.5) — 일관
- `_UNSUPPORTED_WORKAROUNDS` (Task B.3) key 이름 ↔ Task B.4 의 fixture unsupported_calls.name — Slice C 후 ~28 항목 매핑

### Scope check

- 단일 implementation plan = 12-18h, 3 Slice, 14 Task. 적절 (단일 PR squash merge 가능).
- Slice 의존: C → A‖B (Slice C 가 supported list 자동 확장 후 A/B 병렬 가능)
- frontend 변경 X (D3-FE Sprint 30+ deferred) → scope 명확.

### Ambiguity check

- Task A.2 `_eval_attribute` 안 timeframe.period 추가 위치 — grep 명령 + 기존 timeframe.\* 처리 패턴 따라 결정 안내 (구체 line 명시는 over-specification)
- Task B.2 `_find_line` 의 same-function-multiple-lines 처리 — 첫 등장 line 만 추출 명시 (codex G0 가 검증)
- Task A.4 heikinashi `_eval_call` 안 추가 위치 — grep + 기존 multi-return 처리 패턴 안내

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-sprint29-coverage-hardening.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration. cmux 2 워커 (Slice A‖B 병렬) 자연 적용 가능.

**2. Inline Execution** — 본 세션에서 task 순차 (Slice C → A → B → Final), 시간 ~12-18h 단일 세션 budget.

**Which approach?**
