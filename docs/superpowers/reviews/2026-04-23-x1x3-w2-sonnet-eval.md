# W2 Sonnet Independent Evaluation — `ta.sar` Parabolic SAR

**Sprint:** X1+X3 / Worker 2
**Reviewer:** Claude Sonnet 4.6 (독립 리뷰어 — 사전 컨텍스트 없음)
**Date:** 2026-04-23
**Branch:** `worktree-agent-a2493f6f` (base: `stage/x1-x3-indicator-ui`)
**Input files:**

- Plan: `docs/superpowers/plans/2026-04-23-x1x3-w2-ta-sar-parabolic.md`
- Diff: `/tmp/w2-diff.txt`
- Codex self-review: `docs/superpowers/reviews/2026-04-23-x1x3-w2-codex-self.md`

---

## Q1. AC 정량 달성 여부

**판정: PASS (완전 달성)**

Plan §2 정량 기준:

| AC 항목                   | 요구       | 실제                      | 근거                                                                                                                                       |
| ------------------------- | ---------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| unit tests ≥ 5            | ≥ 5개      | **10개**                  | `test_stdlib_sar.py` L32~180 (warmup/uptrend/downtrend/reversal/AF cap/nan/constant/zero-increment/2-bar-clamp-up/2-bar-clamp-down)        |
| i3_drfx strict=False 유지 | PASS       | **PASS**                  | codex-self.md table: "2 passed (회귀 0)" — `test_i3_drfx_runs_all_bars_non_strict` + `test_i3_drfx_virtual_strategy_completes_with_alerts` |
| 기존 ta.\* 전수           | 회귀 0     | **PASS**                  | pine_v2 275 passed (이전 273+2 신규 clamp)                                                                                                 |
| backend 전체              | 934 passed | **934 passed, 1 skipped** | codex-self.md Test Results 섹션                                                                                                            |

i3_drfx.pine L85: `psar = ta.sar(0.02, 0.02, 0.2)` — 실제 호출이 존재하며 E2E 테스트가 `run_historical` + `run_virtual_strategy` 두 경로를 모두 커버한다 (`test_e2e_i3_drfx.py` L46, L57).

---

## Q2. Spurious PASS — Wilder 알고리즘 정확성 검증

**판정: GENUINE PASS — 하지만 inequality 기반 (정확값 assertion 없음)**

### 긍정 증거

codex-self.md 의 12-bar Wilder reference 테이블을 독립 Python 실행으로 재현:

```
bar 0: SAR=nan  bar 1: SAR=98.0000  bar 2: SAR=98.0000
bar 3: SAR=98.2400  bar 4: SAR=98.7056  bar 5: SAR=99.4492
bar 6: SAR=100.5042  bar 7 (반전): SAR=110.0000 (= prev_ep, Wilder 정확)
```

구현 코드(`stdlib.py` L452-469, L471-486)가 reference 테이블과 **수치 완전 일치** — spurious PASS 아님.

### 주의 사항

`test_ta_sar_trend_reversal_resets_to_ep` (`test_stdlib_sar.py` L77-82)는 두 개의 inequality 체크만 한다:

- `sar[6] > sar[4]` — SAR 가 반전 후 올라갔는가
- `sar[6] >= highs[6]` — SAR 가 high 위에 있는가

정확값 체크 (`assert sar[6] == pytest.approx(110.0)`) 가 없다. 이는 **약한 검증**이다. 그러나 2-bar clamp 테스트(`test_stdlib_sar.py` L153, L157, L174, L178)는 정확한 경계값을 assert 하고 있어 알고리즘 핵심 불변 조건은 보호된다.

---

## Q3. TDD 증거

**판정: 불완전 (FAIL→PASS 흔적 없음, 간접 증거만 존재)**

- 직접 증거: codex self-review가 "1차 GO_WITH_FIX → 2차 GO (2-bar clamp 수정)" 흐름을 기록하고 있다. 이는 TDD 정신에 부합하는 수정 사이클이다.
- 간접 증거: `prev2_high`/`prev2_low` 필드가 `SarState` dataclass에 존재(`stdlib.py` L396-397)하고, 2-bar clamp 전용 테스트 2개가 추가된 것은 Red→Green 사이클이 실제로 돌았음을 시사한다.
- 부재 증거: "Step 2 — 실패 확인" 단계(Plan §4 T1)의 CLI 출력 스크린샷/로그가 리뷰 문서에 없다. FAIL 스냅샷이 없으면 엄밀한 TDD 증명이 불가능하다.

**결론:** 코드 변화는 TDD 사이클을 따랐을 가능성이 높으나 증거가 문서화되지 않았다. 신뢰도 6/10.

---

## Q4. 회귀 — `_STDLIB_NAMES` 디스패처 확장 안전성

**판정: SAFE**

`interpreter.py` L698: `"ta.sar"` 을 `_STDLIB_NAMES` frozenset(추정)에 단일 줄 추가. 구조:

```python
# diff L9 (interpreter.py L698)
"ta.sar",  # Sprint X1+X3 W2 (i3_drfx Parabolic SAR)
```

이 확장이 안전한 근거:

1. `_STDLIB_NAMES` 는 set 멤버십 체크용 — 추가 항목이 기존 분기 로직에 영향 없음
2. 실제 실행은 `StdlibDispatcher.call` 의 `if func_name == "ta.sar"` 분기(`stdlib.py` L571-577)에서 처리 — 기존 함수들과 완전 독립적
3. `SarState` 는 `state.buffers[node_id]` 슬롯 격리 (`stdlib.py` L576: `setdefault(node_id, SarState())`) — 다른 함수의 버퍼와 키 충돌 없음
4. `ta.rma` 미추가 확인 — stdlib.py 와 interpreter.py 에서 `ta.rma` 검색 결과 없음 (scope 준수)

---

## Q5. Edge Case 6가지 커버 여부

**판정: 6/6 커버 — 다만 품질 차이 있음**

| Edge Case (Plan §5) | 테스트                                             | 강도                                                            |
| ------------------- | -------------------------------------------------- | --------------------------------------------------------------- |
| 최초 1 bar → nan    | `test_ta_sar_first_bar_is_nan` (L32-35)            | Strong                                                          |
| high==low           | `test_ta_sar_constant_high_low` (L110-118)         | Medium (inf 금지만, SAR 방향 미검증)                            |
| nan high/low        | `test_ta_sar_nan_input_propagates` (L100-107)      | Medium (`sar_ok` 가 nan or finite — 상태 보존 여부 미정밀 검증) |
| AF cap (40+ bar)    | `test_ta_sar_af_capped_at_maximum` (L86-97)        | Strong (`state.acceleration_factor <= 0.2 + 1e-9`)              |
| 급격한 gap 반전     | `test_ta_sar_trend_reversal_resets_to_ep` (L69-83) | Medium (inequality만, 정확값 없음)                              |
| increment=0         | `test_ta_sar_zero_increment` (L121-130)            | Strong (`abs(af - 0.02) < 1e-9`)                                |

추가: 2-bar clamp 테스트 2개(L133-180)는 Plan §5 원래 목록 외 추가 커버리지 — **플러스 알파**.

---

## Q6. ta.rma 미추가 scope 준수

**판정: CONFIRMED CLEAN**

`stdlib.py` 와 `interpreter.py` 전체에서 `ta.rma` 검색 결과 없음. W2 diff는 정확히 3파일만 터치:

- `backend/src/strategy/pine_v2/stdlib.py` (SarState + ta_sar + dispatcher 분기)
- `backend/src/strategy/pine_v2/interpreter.py` (`_STDLIB_NAMES` 1줄)
- `backend/tests/strategy/pine_v2/test_stdlib_sar.py` (신규 10 테스트)

codex self-review 마지막 줄: "i3_drfx strict=True 시도 → ta.rma 미구현으로 차단 (W2 scope 밖)" — 올바른 scope 판단으로 strict=True 을 연기함.

---

## Q7. 최종 Verdict

**GO** / 신뢰도 **8/10**

| 항목                   | 상태                         |
| ---------------------- | ---------------------------- |
| AC 정량                | PASS                         |
| Wilder 알고리즘 정확성 | 수치 검증됨 (독립 재현 일치) |
| 회귀 위험              | 없음                         |
| Edge case              | 6/6 커버 (일부 Medium 강도)  |
| Scope                  | Clean                        |

**감점 요인 (–2점):**

- reversal 테스트가 inequality 기반 (`sar[6] > sar[4]`) — 정확값 assertion 없음 (Minor)
- TDD FAIL 스냅샷 문서화 부재 (Minor)
- constant high==low 테스트가 inf만 금지하고 추세 방향 correctness를 검증하지 않음 (Minor)

이 세 가지는 production 결함을 유발할 수 없으므로 GO 판단에 영향 없음.

---

## Q8. 테스트 커버리지 충분성 (Sonnet 추가 질문)

### (a) Pine Interpreter 레벨 통합 테스트 — 분기 실제 타는가?

**있다 — 단, 결과값 series 검증은 없음.**

`test_e2e_i3_drfx.py::test_i3_drfx_runs_all_bars_non_strict` (L42-50)가 `run_historical(source, ohlcv, strict=False)` 를 통해 실제 interpreter 를 경유하고, i3_drfx.pine L85 의 `ta.sar(0.02, 0.02, 0.2)` 가 dispatcher 분기를 타는 것을 **암묵적으로** 검증한다 (`bars_processed == 40` assertion).

그러나 이 테스트는 "ta.sar 호출이 NotImplementedError 없이 완료됐는가"만 보장한다. SAR 시리즈 값의 정확성(예: `result.var_series["psar"][10] == pytest.approx(...)`)을 assert 하는 테스트는 없다.

즉, interpreter→StdlibDispatcher→ta_sar 경로는 **통합 회로 통전 여부만** 검증됨. 결과값 시리즈는 unit 테스트(`test_stdlib_sar.py`)에서 직접 `ta_sar(state, h, l)` 를 호출하는 방식으로만 검증됨.

### (b) MTF (request.security) 컨텍스트에서 SarState 분리

**현재 미구현 — 이론적 위험 존재, 실제 위험은 낮음.**

`StdlibDispatcher.call` 의 격리 키는 `node_id = id(node)` (`interpreter.py` L706, `stdlib.py` L576). `id(node)` 는 AST 노드의 Python 객체 주소다.

- request.security NOP 처리 확인: Sprint 8c에서 `request.security` 를 NOP 처리한 것이 codex self-review에 언급됨. 즉, **현재 i3_drfx 실행 시 MTF 분기 자체가 실행되지 않는다** — cross-contamination 시나리오가 발생할 수 없다.
- 만약 H2+에서 request.security 를 실제 구현한다면, 동일 AST 노드가 daily+1h context 에서 동일 `node_id` 를 공유할 위험이 있다. 이 경우 `SarState` 가 두 timeframe 간에 공유되는 버그가 발생한다. 단, 이는 미래 문제이며 W2 scope 밖이다.

### 둘 중 production 결함 가능성이 더 높은 것

**(a) Interpreter 레벨 결과값 검증 부재**가 더 높다.

이유:

- MTF 격리 문제는 request.security 가 NOP 상태인 한 발생하지 않는다 — **현재 시스템에서 실체화 불가**
- 반면 interpreter 경유 시 SAR 값이 잘못 계산되는 경우(예: `args` 파싱 오류로 `start=0` 이 주입되는 경우)는 현재 테스트 스위트가 감지하지 못한다. `test_stdlib_sar.py` 는 `ta_sar(state, h, l, ...)` 를 직접 호출하므로 `args[0]` → `float(args[0])` 변환 경로(dispatcher L573)는 미검증.

**권고 (OPTIONAL, GO 조건 아님):** 다음 한 줄 추가로 (a) 위험을 해소할 수 있다:

```python
# test_e2e_i3_drfx.py 또는 별도 test_stdlib_sar_integration.py
def test_ta_sar_via_interpreter_pipeline() -> None:
    """ta.sar 가 interpreter → StdlibDispatcher → ta_sar 경로를 정확한 값으로 통과."""
    src = "psar = ta.sar(0.02, 0.02, 0.2)"
    ohlcv = _make_simple_uptrend()  # 고정 시계열
    result = run_historical(src, ohlcv, strict=False)
    # psar series 의 마지막 값이 기대값 ±1e-6 이내
    assert abs(result.var_series["psar"][-1] - EXPECTED_SAR) < 1e-6
```

이 테스트가 없어도 GO 는 유지된다 (AC 범위 초과). 단, W3+ 에서 추가 권고.

---

## 요약

| 항목             | 결과                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| Q1 AC            | PASS                                                                 |
| Q2 Spurious PASS | GENUINE (수치 일치 독립 확인)                                        |
| Q3 TDD           | 부분 증거 (FAIL 스냅샷 부재)                                         |
| Q4 회귀          | SAFE                                                                 |
| Q5 Edge 6/6      | PASS (일부 Medium 강도)                                              |
| Q6 Scope         | CLEAN (ta.rma 미추가 확인)                                           |
| Q7 Verdict       | **GO / 8/10**                                                        |
| Q8(a)            | Interpreter 결과값 통합 테스트 부재 — 낮은 위험이나 OPTIONAL 권고    |
| Q8(b)            | MTF cross-contamination — 현재 NOP 상태로 실체화 불가, H2+ 시 재검토 |
