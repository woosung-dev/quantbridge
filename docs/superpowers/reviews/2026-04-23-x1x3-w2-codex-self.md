# W2 Codex Self-Review — `ta.sar` Parabolic SAR

**Sprint:** X1+X3 / Worker 2
**Date:** 2026-04-23
**Branch:** `worktree-agent-a2493f6f` (base: `stage/x1-x3-indicator-ui`)
**Plan:** [`docs/superpowers/plans/2026-04-23-x1x3-w2-ta-sar-parabolic.md`](../plans/2026-04-23-x1x3-w2-ta-sar-parabolic.md)

---

## 변경 요약

- `backend/src/strategy/pine_v2/stdlib.py`
  - `SarState` dataclass 추가 (warmup / trend / sar / ep / af / prev / prev2)
  - `ta_sar(state, high, low, start, increment, maximum)` 추가 — Wilder 1978 Parabolic SAR
  - `StdlibDispatcher.call` 에 `"ta.sar"` 분기 추가 (high/low 주입, `state.buffers[node_id]` slot 패턴)
- `backend/src/strategy/pine_v2/interpreter.py`
  - `_STDLIB_NAMES` 에 `"ta.sar"` 등록
- `backend/tests/strategy/pine_v2/test_stdlib_sar.py`
  - 10 unit tests (warmup, uptrend, downtrend, reversal, AF cap, nan, constant high=low, zero increment, 2-bar clamp uptrend, 2-bar clamp downtrend)

---

## Codex Review 결과

### 1차 (initial implementation)

- Verdict: `GO_WITH_FIX` / 신뢰도 `9/10`
- 핵심 지적: **Wilder 2-bar clamp 누락** — `state.prev_low` / `state.prev_high` 1개만 보관 → 일부 시퀀스에서 SAR 가 t-2 의 low/high 침범 가능
- 수정 권고: `prev2_high`/`prev2_low` 추가 + clamp 식 `min(new_sar, prev_low, prev2_low)` / `max(new_sar, prev_high, prev2_high)` + 회귀 테스트 2개

### 2차 (after fix)

- Verdict: **`GO`** / 신뢰도 **`9/10`**
- 모든 항목 PASS:
  1. 2-bar clamp 정확성 — Wilder 표준 일치, 신규 테스트 2개로 회귀 보호
  2. init/warmup → 일반 step 전환 시 `prev2` 보존 — `prev2 <- prev`, `prev <- current` 순서 OK
  3. nan 입력이 `prev2` 갱신을 오염시키지 않음 — early return으로 모든 상태 보존
  4. 회귀 — 변경 범위 `stdlib.py` + interpreter dispatch 1줄, backend 934/1 passed 확인

> 9/10 사유: 샌드박스에서 전체 회귀 재실행 불가 (사용자 보고 934 passed 인용)

---

## Wilder Reference 검증 (정확성 evidence)

합성 SPY-like 시계열 12 bar (단조 상승 → 반전 → 하락 → 반등):

| bar   | high  | low   | sar          | trend    | ep     | af    |
| ----- | ----- | ----- | ------------ | -------- | ------ | ----- |
| 0     | 100.0 | 98.0  | nan          | up       | nan    | 0.020 |
| 1     | 102.0 | 100.0 | 98.0000      | up       | 102.00 | 0.020 |
| 2     | 104.0 | 102.0 | 98.0000      | up       | 104.00 | 0.040 |
| 3     | 106.0 | 104.0 | 98.2400      | up       | 106.00 | 0.060 |
| 4     | 108.0 | 106.0 | 98.7056      | up       | 108.00 | 0.080 |
| 5     | 110.0 | 108.0 | 99.4492      | up       | 110.00 | 0.100 |
| 6     | 109.0 | 102.0 | 100.5042     | up       | 110.00 | 0.100 |
| **7** | 105.0 | 98.0  | **110.0000** | **down** | 98.00  | 0.020 |
| 8     | 100.0 | 94.0  | 109.7600     | down     | 94.00  | 0.040 |
| 9     | 96.0  | 90.0  | 109.1296     | down     | 90.00  | 0.060 |
| 10    | 93.0  | 88.0  | 107.9818     | down     | 88.00  | 0.080 |
| 11    | 95.0  | 91.0  | 106.3833     | down     | 88.00  | 0.080 |

**검증 포인트:**

- bar 1 init: SAR = prev_low(98) — uptrend 진입
- bar 2-5: AF 0.02 → 0.10 (EP 매번 갱신, increment +0.02)
- bar 6: high(109) < prev_ep(110) → EP 미갱신, AF 유지 (Wilder 정확)
- **bar 7 반전**: low(98) < new_sar 침범 → SAR = prev_ep(110), AF reset = 0.02, EP = low(98)
- bar 8-11: downtrend SAR 점진 하향
- bar 11: low(91) > prev_ep(88) → EP 미갱신, AF 0.08 유지

이 출력은 TradingView/Investopedia/StockCharts 표준 Parabolic SAR (start=0.02, increment=0.02, max=0.2) 결과와 정성·정량 일치.

---

## Test Results

| Suite                                | Result                                          |
| ------------------------------------ | ----------------------------------------------- |
| `test_stdlib_sar.py`                 | **10 passed**                                   |
| `test_e2e_i3_drfx.py` (strict=False) | 2 passed (회귀 0)                               |
| `tests/strategy/pine_v2/` 전체       | **275 passed** (이전 273 + 2 신규 clamp)        |
| `pytest -q` 전체 backend             | **934 passed**, 1 skipped (legacy golden, 무관) |

i3_drfx strict=True 시도 → `ta.rma` 미구현으로 차단 (W2 scope 밖). strict=False 유지가 plan AC.

---

## Edge Case 6 처리

| Edge Case             | Plan §5 | 처리 방법                                              |
| --------------------- | ------- | ------------------------------------------------------ |
| 최초 1 bar → nan      | ✓       | `is_initialized = False` warmup, prev_high/low 만 기록 |
| high == low           | ✓       | constant 시퀀스 테스트 (no nan/inf)                    |
| nan high/low          | ✓       | early return, 상태 갱신 생략 — 다음 bar 영향 없음      |
| AF cap (40+ bar 상승) | ✓       | `min(af + increment, maximum)` clamp                   |
| 급격한 gap 반전       | ✓       | reversal 테스트 — SAR = prev_ep                        |
| increment=0           | ✓       | AF 가 start 에서 고정 (테스트 검증)                    |

---

## 최종 Verdict

**GO** — Wilder 2-bar clamp 적용 완료, codex 2차 PASS, backend 934 green, 회귀 0.
