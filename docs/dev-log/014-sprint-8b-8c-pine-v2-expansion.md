# ADR-014: Sprint 8b + 8c 합본 회고 — pine_v2 Tier-1 래퍼 + 3-Track Dispatcher

> **상태:** 회고 (사후 기록, 2026-04-23 작성)
> **일자:** 2026-04-18 (8b PR #21 merge `c79b10c`) + 2026-04-19 (8c PR #22 merge)
> **브랜치:** `feat/sprint8b-tier1-corpus-matrix`, `feat/sprint8c-user-function-3track`
> **관련 ADR:** [ADR-011 Pine v4](./011-pine-execution-strategy-v4.md) (Tier 0~5 원안), [ADR-012 Sprint 8a Tier-0](./012-sprint-8a-tier0-final-report.md) (선행)
> **상위 문서:** [`04_architecture/pine-execution-architecture.md`](../04_architecture/pine-execution-architecture.md)
> **합본 이유:** 8b/8c 모두 pine_v2 확장 영역 + 독립 ADR 로 쪼개면 결정의 흐름이 끊김 → 합본으로 변경 근거의 연속성 유지

---

## 1. 배경

Sprint 8a (ADR-012, PR #20) 에서 pine_v2 Tier-0 이 완성됐다. s1_pbr 과 i1_utbot (2/6 corpus) 이 완주 가능한 상태였고, 나머지 4 corpus (s2_utbot, s3_rsid, i2_luxalgo, i3_drfx) 는 차단. ADR-011 원안은 Tier-1 (Alert Hook Parser) 과 Tier-3 (strategy() 네이티브) 를 Sprint 8b 에서 병행 확장하는 로드맵이었으나, 실측 결과 **6/6 corpus 완주** 가 더 시급한 가치로 판단됐다 — dogfood 의 기본 재료이기 때문.

---

## 2. 결정 요약

### 2.1 Sprint 8b 결정

> **"Tier-1 원안의 Alert Hook Parser 대신, 가상 strategy 래퍼 (`VirtualStrategyWrapper`) + 렌더링 Registry 를 우선 구현하여 indicator() 스크립트도 백테스트 파이프라인에 태운다."**

**채택**:

- **VirtualStrategyWrapper**: indicator() + alert 스크립트를 가상의 strategy() 로 감싸 run_backtest_v2 계약과 호환시킴
- **RenderingRegistry**: `plot*`, `box.new`, `line.new`, `label.new`, `table.new` 를 NOP 으로 통과시키되 좌표 getter 는 메모리 스텁으로 제공 (범위 A 정책)
- **v4 alias + iff**: `rma`/`sma`/`ema` 등 prefix 없는 v4 호환, `iff(cond, a, b)` → ternary 변환
- **switch / stdev / variance**: Pine v5 switch expression + stdlib 확장
- **v4 strategy.entry**: `long=true/false` boolean kwarg + `when=` 지원 (기존 v5 direction= 와 공존)
- **time/timestamp 확장**: month/day 반영
- **40+ Pine enum constants**: `color.green`, `shape.arrowup`, `plot.style_line` 등 enum 값 상수화
- **deleted line 정책**: `line.delete()` 후 참조 시 무시 (NOP)

**Opus/Sonnet 교차 hardening**: PR #21 직전 Opus 와 Sonnet 각자 adversarial review 를 돌려 edge case 를 발견 (예: `box.get_top()` 이 삭제된 box 참조 시 KeyError → None 반환으로 변경).

### 2.2 Sprint 8c 결정

> **"user-defined function (`=>` 정의) 과 multi-return tuple 을 full 지원하고, parse_and_run_v2 를 3-Track dispatcher 로 개편한다. s3_rsid 를 strict=True 로 완주시키는 것이 종료 조건."**

**채택**:

- **FunctionDef 등록** (top-level guard): 로컬 scope 에서의 함수 정의 방지
- **scope stack + multi-return tuple unpack**: `[a, b] = ta.supertrend(...)` 같은 패턴
- **ta.barssince / ta.valuewhen**: stateful 순회 기반
- **tostring / request.security**: NOP (MTF 는 Tier-5 로 이연)
- **color.\* NOP / pivothigh/low 3-arg** / **input kwarg 수정**
- **parse_and_run_v2 = S/A/M dispatcher**: ADR-011 §1.3 P3 의 3-Track 을 실제로 분기하는 함수. Track S → 기존 strategy() 실행, Track A → VirtualStrategyWrapper 경유, Track M → 현재는 unsupported 응답 (Tier-4 Variable Explorer 는 Path γ+ 이후)
- **RunResult 확장**: `strategy_state`, `var_series` 외부 노출 → Trust Layer CI 의 P-3 Execution Golden 이 관찰 가능

**성공 기준**: `s3_rsid.pine` strict=True 로 완주 + `trade ≥ 1` 확인. i3_drfx 는 supertrend tuple unpack 검증만 (full 실행은 Y1 Coverage 에서 unsupported reject).

**eng-review 1-pass 반영**:

- Top-level FunctionDef guard (로컬 정의 차단)
- `_exec_reassign` 로컬 frame 단위 테스트 추가 (critical gap)

---

## 3. 테스트 & 결과

| 항목                    | Sprint 8a 말 | Sprint 8b 말 (PR #21) |   Sprint 8c 말 (PR #22)   |
| ----------------------- | :----------: | :-------------------: | :-----------------------: |
| pine_v2 tests           |     169      |       224 (+55)       |         252 (+28)         |
| backend total tests     |      —       |       750 green       |         778 green         |
| 완주 corpus (6 종 기준) | 2/6 (s1, i1) |        **6/6**        | 6/6 + s3_rsid strict=True |
| Ruff / Mypy             |    clean     |         clean         |           clean           |

**6/6 완주** 은 ADR-011 §1.3 P3 의 "Track S/A/M 합산 약 75% 커버리지" 가정을 실측으로 강화 — 최소한 5 corpus (i3 제외) 는 모두 처리 경로 확보.

---

## 4. 원안 대비 변경

| 항목                       | ADR-011 원안 (8b 로드맵)                                                                       | 실제 구현                                                                                             |
| -------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Tier-1                     | AST Alert 수집 + 메시지 분류기 + condition trace + 가상 strategy 래퍼 + 3-Track 라우터 (4단계) | **VirtualStrategyWrapper 중심 + alert_hook v1 (loose mode)** — 메시지 분류기는 현재 simple regex 기반 |
| Tier-3                     | strategy() 네이티브 (`trail_points/offset` 포함)                                               | entry/exit/close_all 만 구현. `trail_points` 는 H2+ 이연 (ADR-011 §6 H1 MVP scope 기준)               |
| Tier-4 (Variable Explorer) | 8c 에서 MVP                                                                                    | **미착수** — Path γ 이후 검토                                                                         |

**이유**: 6 corpus 완주가 "LLM oracle / pre-flight coverage / trust CI" 전체의 prerequisite 이기 때문. Tier-3 의 `trail_points` 같은 고난도 기능보다 **넓은 스크립트 파싱·실행** 이 우선. 이는 2026-04-18 amendment (ADR-011 §6 H1 MVP scope) 에서 공식화됐다.

---

## 5. 학습 (Lessons)

### L-1: Opus/Sonnet 교차 hardening 의 실효성

Sprint 8b 말에 2개 모델로 independent adversarial review 를 돌린 결과, 단일 모델이 놓친 edge case (deleted box 참조, input kwarg 순서) 을 잡음. **Gate-1/2 의 2중 blind evaluator 패턴** 의 근거가 됨 → Path β ADR-013 Gate 에 승계.

### L-2: Multi-return tuple unpack 은 간과되기 쉽다

`[a, b] = foo()` 는 Python 과 문법이 다르고 (대괄호), Pine v5 에서 흔한 패턴. 초기 구현에서 "scalar 복수 반환" 로 처리했다가 `_exec_reassign` 로컬 frame 테스트에서 실패 감지. **eng-review 가 critical gap 을 잡음** — 이후 Sprint 에서 단일 reviewer (codex 또는 opus 단독) 보다 2중 blind 원칙 고수.

### L-3: 3-Track dispatcher 는 기존 run_backtest_v2 API 에 숨길 수 있다

`parse_and_run_v2` 가 외부 호출자에 Track 을 노출하지 않고 내부에서 분기. 호출자 API 호환성 유지 + 내부 구조 자유도 ↑.

### L-4: H1 MVP scope 축소의 정당성

`trail_points` 를 포기하고 6 corpus 완주에 집중한 결정은 dogfood 기준에서 옳았다. Bybit/OKX testnet dogfood 는 TP/SL only 만으로 가능 (Phase -1 DrFX 실측 §13.1 근거). H1 범위 보수적으로 설정 → H2 에서 전문 기능 확장 전략 이 유효.

---

## 6. 영향

### 코드

- pine_v2/ 에 `virtual_strategy.py`, `rendering.py`, `compat.py`, `alert_hook.py` 신규
- `interpreter.py` 2배 확장 (FunctionDef, scope, multi-return)
- `stdlib.py` 9 → 17 지표

### Trust Layer 관점 (Path β 와 연결)

- **RunResult.var_series / strategy_state 노출** 은 **P-3 Execution Golden 의 기반**. Path β 가 이 데이터를 golden digest 로 고정한다.
- **coverage.py SSOT** 가 pine_v2 stdlib/interpreter 과 동기화 유지해야 함 — Path β P-2 가 이를 검증.

### 문서

- `04_architecture/pine-execution-architecture.md` 에 3-Track dispatcher 섹션 추가 필요 (Path β S0-C3 에서 처리)
- ADR-011 §9 신뢰도 9.7 → Sprint 8c 완료 후 9.8 암묵적 상향 (공식 amendment 는 본 회고로 갈음)

---

## 7. 다음 단계

- [x] Path β Stage 0 (본 ADR 포함)
- [ ] Path β Stage 1/2 (Trust Layer CI → pine_v2 변경이 corpus metrics 에 미치는 영향 자동 감지)
- [ ] Sprint 8d Tier-5 (LLM 하이브리드) — H2 이후
- [ ] Tier-4 Variable Explorer — H2 build-in-public 진입 시 (또는 실사용자 피드백으로 재평가)

---

## 8. 변경 이력

| 날짜       | 사유                  | 변경                                                      |
| ---------- | --------------------- | --------------------------------------------------------- |
| 2026-04-23 | 최초 작성 (사후 회고) | Path β Stage 0 Wave B. 8b/8c 의 의사결정 근거와 학습 정리 |
