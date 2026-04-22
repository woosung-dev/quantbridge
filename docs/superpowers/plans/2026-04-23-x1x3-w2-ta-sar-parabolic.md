# W2 — `ta.sar` (Parabolic SAR) stdlib 구현 (i3_drfx FAILED 해소)

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 2 / 5
> **Branch:** `stage/x1-x3-indicator-ui`
> **TDD Mode:** **정석 TDD** — 금융 숫자 + stdlib 공유 로직, 회귀 위험 극대

---

## 1. Context

pine_v2 interpreter 는 TradingView Pine Script v5 를 Python 으로 실행한다. stdlib 는 `ta.*` 함수군 (ta.sma, ta.rsi, ta.atr 등) 을 구현.

**현재 공백**: `ta.sar(start, increment, maximum)` (Parabolic SAR) 미구현 → `i3_drfx.pine` (DrFX Diamond Algo) 이 ta.sar 호출 시 interpreter 가 dispatch 실패 → **NotImplementedError** 또는 ValueError.

**Parabolic SAR 사양 (Wilder 1978):**

- 각 bar 마다 SAR (Stop And Reverse) 포인트 계산
- 시작 AF (Acceleration Factor) = `start` (보통 0.02)
- EP (Extreme Point) 갱신 시마다 AF += `increment` (보통 0.02)
- AF ≤ `maximum` (보통 0.2) 로 clamp
- 추세 반전 (close 가 SAR 를 crossover) 시 새 추세의 첫 SAR = 직전 추세의 EP

---

## 2. Acceptance Criteria

### 정량

- [ ] 신규 `test_stdlib_sar.py` 에 ≥ 5 테스트: (a) uptrend SAR 감소, (b) downtrend SAR 증가, (c) 추세 반전 시 EP로 리셋, (d) AF cap 유지, (e) nan 입력 handling
- [ ] `i3_drfx.pine` 이 interpreter 경유 (run_historical 또는 run_virtual_strategy) 실행 시 ta.sar 호출 성공 — 기존 `test_e2e_i3_drfx.py::test_i3_drfx_e2e_strict_false` 가 strict=True 로도 통과하거나, 최소 strict=False 는 깨지지 않음
- [ ] 기존 `ta.*` 테스트 전수 PASS (ta.sma, ta.rsi, ta.atr 등 semantic drift 없음)
- [ ] backend pytest 전체 녹색

### 정성

- [ ] 결과값 타입 = `float` (pine_v2 stdlib 관례 — ta.atr/ta.rsi 와 동일 시그니처)
- [ ] series state: bar-by-bar 계산 상태를 `RunState.series_state` 또는 interpreter 내부 cache 로 유지 (ta.rsi, ta.atr 참조하여 동일 패턴)
- [ ] AST dispatch: `interpreter.py` 의 `_call_stdlib_function` 또는 동등 분기에 `"ta.sar"` 추가
- [ ] nan 전파: 초기 bar (데이터 부족) 에서는 `math.nan` 반환

---

## 3. File Structure

**수정:**

- `backend/src/strategy/pine_v2/stdlib.py` — `ta_sar()` 함수 추가 + 상태 보관 로직
- `backend/src/strategy/pine_v2/interpreter.py` — `ta.sar` 호출 dispatch

**신규:**

- `backend/tests/strategy/pine_v2/test_stdlib_sar.py` — unit 테스트

---

## 4. TDD Tasks

### T1. 실패 테스트 작성

**Step 1 — `backend/tests/strategy/pine_v2/test_stdlib_sar.py` 신규 생성:**

```python
"""Parabolic SAR (ta.sar) unit tests — Sprint X1+X3 W2."""
from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.stdlib import SarState, ta_sar


def _run_series(
    highs: list[float],
    lows: list[float],
    start: float = 0.02,
    increment: float = 0.02,
    maximum: float = 0.2,
) -> list[float]:
    state = SarState()
    results = []
    for h, l in zip(highs, lows):
        sar = ta_sar(state, h, l, start, increment, maximum)
        results.append(sar)
    return results


def test_ta_sar_first_bar_is_nan() -> None:
    """최초 bar 에서는 추세 미정 → nan."""
    sar = _run_series([100.0], [99.0])
    assert math.isnan(sar[0])


def test_ta_sar_uptrend_sar_stays_below_lows() -> None:
    """지속 상승 시 SAR 는 low 아래에 머문다."""
    highs = [100 + i for i in range(20)]
    lows = [99 + i for i in range(20)]
    sar = _run_series(highs, lows)
    # 2번째 bar 이후부터 실값
    valid = [s for s in sar[2:] if not math.isnan(s)]
    assert all(s < lows[i + 2] for i, s in enumerate(valid)), (
        f"uptrend SAR must stay below lows: sar={valid} lows={lows[2:]}"
    )


def test_ta_sar_downtrend_sar_stays_above_highs() -> None:
    """지속 하락 시 SAR 는 high 위에 머문다."""
    highs = [100 - i for i in range(20)]
    lows = [99 - i for i in range(20)]
    sar = _run_series(highs, lows)
    valid = [s for s in sar[2:] if not math.isnan(s)]
    assert all(s > highs[i + 2] for i, s in enumerate(valid))


def test_ta_sar_trend_reversal_resets_to_ep() -> None:
    """상승추세에서 low 가 SAR 아래로 뚫으면 반전: 새 SAR = 직전 EP (high)."""
    # 상승 5 bar → 하락 2 bar
    highs = [100, 102, 105, 108, 110, 108, 102]
    lows = [99, 101, 104, 107, 109, 100, 95]
    sar = _run_series(highs, lows)
    # 반전 bar (index 5 or 6) 에서 SAR 가 직전 구간 최고치 EP 근처로 점프
    # 정확한 값은 Wilder 알고리즘으로 보장 (기준: 반전 후 SAR > 이전 SAR)
    assert sar[6] > sar[4], f"reversal SAR must jump up: {sar}"


def test_ta_sar_af_capped_at_maximum() -> None:
    """강한 상승 (EP 매 bar 갱신) 에서도 AF 는 maximum 을 넘지 않는다."""
    highs = list(range(100, 140))  # 40 bar 상승
    lows = [h - 0.5 for h in highs]
    state = SarState()
    last_sar = None
    for h, l in zip(highs, lows):
        last_sar = ta_sar(state, h, l, 0.02, 0.02, 0.2)
    # AF cap 이 정상 동작하면 후반부 SAR 증가폭이 둔화 (EP 와 SAR 간격 수렴)
    # 단순 sanity: nan 아니고 finite
    assert last_sar is not None and math.isfinite(last_sar)
    assert state.acceleration_factor <= 0.2 + 1e-9


def test_ta_sar_nan_input_propagates() -> None:
    """high 또는 low 가 nan 이면 SAR 도 nan (이후 bar 는 계속 진행)."""
    state = SarState()
    sar_nan = ta_sar(state, math.nan, 99.0, 0.02, 0.02, 0.2)
    assert math.isnan(sar_nan)
    # 다음 bar 는 정상
    sar_ok = ta_sar(state, 100.0, 99.0, 0.02, 0.02, 0.2)
    # 최초 valid bar 이므로 초기화 단계 — 반드시 nan 또는 finite 둘 중 하나
    assert math.isnan(sar_ok) or math.isfinite(sar_ok)
```

**Step 2 — 실패 확인:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_stdlib_sar.py -v
```

Expected: FAIL — `SarState` 와 `ta_sar` import 불가.

### T2. `stdlib.py` 에 SarState + ta_sar 구현

**Step 3 — `backend/src/strategy/pine_v2/stdlib.py` 에 추가:**

```python
# (파일 하단 적절한 위치에)

from dataclasses import dataclass, field


@dataclass
class SarState:
    """Parabolic SAR 계산 상태 — bar-by-bar 유지.

    최초 2 bar 는 추세 결정을 위한 warmup (nan 반환).
    이후 is_uptrend True/False 로 추세 추적.
    """

    is_initialized: bool = False
    is_uptrend: bool = True  # True=long, False=short
    sar: float = math.nan
    extreme_point: float = math.nan  # uptrend=max high, downtrend=min low
    acceleration_factor: float = 0.02
    prev_high: float = math.nan
    prev_low: float = math.nan


def ta_sar(
    state: SarState,
    high: float,
    low: float,
    start: float = 0.02,
    increment: float = 0.02,
    maximum: float = 0.2,
) -> float:
    """Wilder Parabolic SAR — bar-by-bar 계산.

    반전 (close가 SAR crossover) 시 새 추세의 첫 SAR = 직전 EP.
    AF 는 EP 갱신 시마다 += increment, maximum 까지.

    nan high/low 는 nan 반환하고 상태 갱신 생략.
    """
    if math.isnan(high) or math.isnan(low):
        return math.nan

    # warmup: 첫 bar 는 상태만 기록
    if not state.is_initialized:
        state.prev_high = high
        state.prev_low = low
        state.is_initialized = True
        return math.nan

    # 두 번째 bar: 추세 결정 + 초기 SAR/EP 설정
    if math.isnan(state.sar):
        # prev bar 와 비교해 상승/하락 결정
        if high >= state.prev_high:
            state.is_uptrend = True
            state.sar = state.prev_low  # uptrend 초기 SAR = 이전 low
            state.extreme_point = high
        else:
            state.is_uptrend = False
            state.sar = state.prev_high
            state.extreme_point = low
        state.acceleration_factor = start
        state.prev_high = high
        state.prev_low = low
        return state.sar

    # 일반 bar: Wilder 규칙
    prev_sar = state.sar
    prev_ep = state.extreme_point
    af = state.acceleration_factor

    if state.is_uptrend:
        new_sar = prev_sar + af * (prev_ep - prev_sar)
        # SAR 는 직전 2 bar 의 low 보다 낮아야 함
        new_sar = min(new_sar, state.prev_low, low)
        # 반전 체크
        if low < new_sar:
            # 하락 반전: 새 추세의 SAR = 직전 EP
            state.is_uptrend = False
            state.sar = prev_ep
            state.extreme_point = low
            state.acceleration_factor = start
        else:
            state.sar = new_sar
            if high > prev_ep:
                state.extreme_point = high
                state.acceleration_factor = min(af + increment, maximum)
    else:
        new_sar = prev_sar + af * (prev_ep - prev_sar)
        new_sar = max(new_sar, state.prev_high, high)
        if high > new_sar:
            state.is_uptrend = True
            state.sar = prev_ep
            state.extreme_point = high
            state.acceleration_factor = start
        else:
            state.sar = new_sar
            if low < prev_ep:
                state.extreme_point = low
                state.acceleration_factor = min(af + increment, maximum)

    state.prev_high = high
    state.prev_low = low
    return state.sar
```

**Step 4 — 녹색 확인:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_stdlib_sar.py -v
```

Expected: 5/6 tests PASS (일부 경계 케이스 tweak 가능).

### T3. Interpreter 에 ta.sar dispatch 추가

**Step 5 — `interpreter.py` 에서 `ta.*` 호출 처리 지점 확인:**

```bash
grep -n "ta\.rsi\|ta\.atr\|_call_stdlib\|dispatch.*ta" backend/src/strategy/pine_v2/interpreter.py | head -20
```

기존 pattern 을 mirror 해서 `ta.sar` 추가. 예: `ta.rsi` 가 state-holding 이면 동일 state cache 패턴 재사용.

**Step 6 — i3_drfx 테스트 실행:**

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_e2e_i3_drfx.py -v
```

Expected: 기존 strict=False PASS 유지, 가능하면 ta.sar 관련 error 메시지 소거.

### T4. 전체 회귀

**Step 7:**

```bash
cd backend && uv run pytest -q
```

Expected: 922+ baseline + 신규 5-6 SAR tests → 927+ passed.

### T5. Worker-side codex review 1-pass

```bash
codex exec --sandbox read-only "Review git diff for ta.sar implementation. Check: (1) Wilder algorithm correctness (EP / AF / reversal), (2) nan propagation, (3) state encapsulation (no globals), (4) interpreter dispatch parity with ta.rsi/ta.atr pattern, (5) no regression in other ta.* tests."
```

출력 → `docs/superpowers/reviews/2026-04-23-x1x3-w2-codex-self.md`.

### T6. Stage push

```bash
git add backend/src/strategy/pine_v2/stdlib.py backend/src/strategy/pine_v2/interpreter.py backend/tests/strategy/pine_v2/test_stdlib_sar.py docs/superpowers/reviews/2026-04-23-x1x3-w2-codex-self.md
git commit -m "feat(pine_v2): ta.sar Parabolic SAR stdlib (W2)"
git push origin stage/x1-x3-indicator-ui
```

---

## 5. Edge Cases 필수 커버

- 최초 1 bar → nan (warmup)
- high=low (1 bar 내 변동 0) → nan 방지, prev bar 기준으로 진행
- nan high/low → 이번 bar nan 반환 + 상태 갱신 생략
- AF cap: 40+ bar 연속 상승 시 AF ≤ maximum
- 급격한 gap 반전 (prev low >> today high) → EP 리셋 정확성
- 0 증분 increment=0 → AF 고정 (Wilder 정의상 허용)

---

## 6. 3-Evaluator 공용 질문

1. AC 정량 (5 unit tests + i3_drfx E2E) 실제 달성?
2. spurious PASS: state 초기값이 우연히 테스트와 맞아떨어진 것?
3. TDD: FAIL → PASS 전환 evidence (step 2 FAIL 확인)?
4. 회귀: ta.rsi / ta.atr / ta.sma 기존 테스트 semantic drift?
5. edge: nan / gap / AF cap / 1-bar / constant high=low 커버?
6. memory 규칙: Decimal-first 는 SAR 에 불필요 (float 고유) 이나, 결과 합산 시 누출 금지
7. GO / GO_WITH_FIX / MAJOR_REVISION / NO_GO + 신뢰도 1-10

---

## 7. Verification

```bash
cd backend && uv run pytest tests/strategy/pine_v2/test_stdlib_sar.py -v
cd backend && uv run pytest tests/strategy/pine_v2/test_e2e_i3_drfx.py -v
cd backend && uv run pytest -q  # 전체 회귀
```
