# Sprint 29 v1 → v2 frame pivot — codex + Opus 2-검토 stale diagnosis 차단

> **Date:** 2026-05-04
> **Sprint:** Sprint 29 kickoff
> **Type:** ADR + meta-methodology evidence (LESSON-037 first validation)
> **Trigger:** 본인 dogfood 결과 → "Pine indicator 정확성 부족" → Sprint 29 = Pine Architectural Fix pivot 결정 → plan v1 작성 → **두 독립 검토에서 stale diagnosis 발견** → plan v2 frame change

---

## 0. TL;DR

Sprint 29 plan v1 ("Pine Architectural Fix", 4 Slice, 25-40h) 의 **핵심 가정 다수가 stale** (= 실제 코드 baseline 과 어긋남). codex CLI consult mode (high reasoning, 1.6M tokens) + fresh-context Opus 서브에이전트 2 독립 검토에서 광범위하게 발견. plan v2 ("Coverage Layer Hardening + DrFXGOD Schema", 3 Slice, 16-22h) 로 frame pivot.

**핵심 교훈 (LESSON-037 후보):** Sprint kickoff 첫 step 은 **baseline 재측정 (preflight)** 의무. 본인 dogfood 인상 + 추측 기반 plan v1 가 코드 실측 검증 없이 진행되면 sprint 안에서 다시 발견 → rewrite 비용 두 배.

---

## 1. v1 → v2 frame change 의 trigger

Sprint 28 종료 후 본인 dogfood:

- LuxAlgo SMC indicator 가 안 돌아가거나 부정확하게 보임
- RsiD strategy 가 unstable 한 backtest 결과
- DrFXGOD 같은 큰 indicator 가 reject

→ **plan v1 가정:** Pine transpiler 의 architectural 한계. layer separation + stdlib 확장으로 근본 해결.

→ **plan v1 4 Slice:**

- Slice 1: Drawing Primitives Skip Layer (line.new/delete, table.new, plotshape, hline, fill, bgcolor) — 8-12h
- Slice 2: Pine v5/v6 Syntax Layer (var keyword, switch-case, input.string options, extend.right, location.absolute, strategy.entry comment) — 8-12h
- Slice 3: User-defined function + stdlib 확장 (ta.atr/ema/sma/linreg/variance/stdev/crossunder/crossover, math.abs) — 6-10h
- Slice 4: Coverage Analyzer 강화 (line + workaround) — 3-6h

총 25-40h. 통과율 3/6 (50%) → 5/6 (83%) 목표.

---

## 2. 두 독립 검토 결과

### 2.1 codex CLI consult (high reasoning, 1.6M tokens, FAIL verdict)

검토 prompt: 9 dimension challenge (architectural soundness / hidden whack-a-mole / slice dependency / SSOT sync risk / DrFXGOD feasibility / time estimate / TDD fixture / meta-methodology / Beta prereq alignment).

**codex spot-check 결과:**

- `rendering.py` line/box/label/table 메서드 **이미 거의 다 구현** (line.set_xy1/2, line.delete, table.cell 까지)
- `_eval_switch` (line 407-428) **skeleton 이 아니라 완전 작동** (subject vs pattern matching, default fallback, `_exec_case_body`)
- `_call_user_function` (line 812-869) **완전 작동** (multi-return tuple, scope_stack, ta.\* prefix 격리)
- ta.atr/sma/ema/stdev/variance/crossover/crossunder **이미 stdlib 등록**
- request.security **이미 graceful NOP** (interpreter line 709-715)
- `SUPPORTED_ENUM_CONSTANTS` set **자체가 코드에 없음** (실제: `_ENUM_PREFIXES=13` prefix lookup)
- `tmp_code/pine_code/LuxAlgo*.pine` 와 `backend/tests/fixtures/pine_corpus_v2/i2_luxalgo.pine` **byte-identical**

**codex 9 dimension verdict:**

| #   | Dimension                | Verdict                                         |
| --- | ------------------------ | ----------------------------------------------- |
| 1   | Architectural soundness  | CAUTION (interpreter.py hotspot)                |
| 2   | Hidden whack-a-mole      | **FAIL** (root cause stale, patch list 化)      |
| 3   | Slice dependency         | **FAIL** (coverage.py 4 Slice 모두 공유)        |
| 4   | SSOT 3-set sync risk     | **FAIL** (`SUPPORTED_ENUM_CONSTANTS` fictional) |
| 5   | DrFXGOD feasibility      | CAUTION (CoverageReport schema 부재)            |
| 6   | Time estimate 25-40h     | CAUTION (이미 다 됨 + DrFXGOD analyzer 부족)    |
| 7   | TDD fixture registration | **FAIL** (canonical fixture 이미 존재)          |
| 8   | Type A meta-methodology  | CAUTION (baseline preflight 없음)               |
| 9   | Beta prereq alignment    | **FAIL** (5/6 산식 stale)                       |

**최종 verdict: FAIL** — 계획의 핵심 전제가 실제 코드와 맞지 않고, Sprint 29 목표가 "아키텍처 fix" 가 아니라 stale diagnosis 기반 patch list.

### 2.2 Opus fresh-context subagent (CONDITIONAL PASS verdict)

검토 prompt: 동일 9 dimension + 코드 spot-check 의무.

**Opus spot-check 결과 (codex 와 일치하는 부분):**

- rendering.py base 이미 완비 (LineObject/BoxObject/LabelObject/TableObject + Registry)
- `_eval_switch` 이미 완전 구현
- `_RENDERING_FACTORIES` 16개 메서드 이미 매핑
- `_call_user_function` 완성 (multi-return tuple 까지)
- KNOWN_UNSUPPORTED_FUNCTIONS 7건 정확 일치

**Opus 단독 발견:**

- interpreter.py `_eval_call` dispatcher chain 잘 분리 → 회귀 risk 낮음 (codex 와 의견 충돌)
- SSOT audit test invariant 권장 (`STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS` 등)

**최종 verdict: CONDITIONAL PASS** — Slice 1 over-conservative, 방향성은 옳음.

---

## 3. 일치 발견 (수긍 의무)

| #   | 발견                                                                 | Opus | codex |                  v2 반영                   |
| --- | -------------------------------------------------------------------- | :--: | :---: | :----------------------------------------: |
| A1  | rendering.py 의 line/box/label/table 메서드 이미 거의 다 구현        |  ✅  |  ✅   |      Slice 1 삭제 → §3 baseline 갱신       |
| A2  | `_eval_switch` 완전 작동 (skeleton 아님)                             |  ✅  |  ✅   |          Slice 2 syntax 작업 삭제          |
| A3  | `_call_user_function` 완전 작동 (multi-return 포함)                  |  ✅  |  ✅   |        Slice 3 user-func 작업 삭제         |
| A4  | tmp_code symlink → backend tests 부적절. canonical fixture 사용 권장 |  ✅  |  ✅   | §12 step 3 변경 (canonical fixture 그대로) |

---

## 4. codex 단독 critical 발견 (Opus 도 놓침)

| #      | 발견                                                                                                                                                                                                               | 영향                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| **B1** | `SUPPORTED_ENUM_CONSTANTS` set 자체가 코드에 없음. 실제 구조 = `SUPPORTED_FUNCTIONS=99` / `SUPPORTED_ATTRIBUTES=39` / `_ENUM_PREFIXES=13`                                                                          | ★★★★★ critical (§5 SSOT 명세 fictional) |
| **B2** | LuxAlgo / RsiD 가 실제 coverage 기준 0 unsupported = **이미 runnable**. 진짜 reject = UtBot strategy (4 unsupported) + DrFXGOD (39 unsupported)                                                                    | ★★★★★ critical (§3 진단표 frame change) |
| **B3** | DrFXGOD 39 unsupported 는 request.security 외 array._, ta.wma/alma/mom/bb/dmi, timeframe._, table.cell_set_bgcolor, label.get_x/set_x/set_y 등. workaround dict 만으론 부족 — line-numbered structured schema 필요 | ★★★★ high (Slice B scope 확정)          |
| **B4** | `tmp_code/pine_code/` 와 `backend/tests/fixtures/pine_corpus_v2/` byte-identical. symlink/copy 불필요                                                                                                              | ★★★ medium (§12 step 3 단순화)          |

---

## 5. 의견 충돌 → 본 세션 판단

| 항목                       | Opus                         | codex                    | v2 채택                                               |
| -------------------------- | ---------------------------- | ------------------------ | ----------------------------------------------------- |
| `interpreter.py` 회귀 risk | 낮음 (dispatch chain 분리)   | 높음 (Pine 전체 hotspot) | **codex 보수적 입장** (1448 BE test 보호 dual metric) |
| 시간 estimate 25-40h       | Slice 1 over / Slice 3 under | 전체 over (이미 다 있음) | **codex 입장** (실제 작업 다른 방향, 16-22h 재산정)   |

---

## 6. codex 의 명백한 오류 (반박)

| #   | codex 발언                                             | 반박 근거                                                                                                                   | v2 처리                                                                                                                              |
| --- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | "사용자 지시상 Claude skill 계열은 사용하면 안 됩니다" | filesystem boundary instruction (codex 가 skill 파일 읽지 말라는 뜻) 을 사용자 정책으로 오해                                | plan v2 §6 메타-방법론 (brainstorming/writing-plans/TDD/codex G0/review) 그대로 의무 유지                                            |
| D2  | "Slice 1/2/3 모두 축소 / 작업 삭제"                    | Slice 2 의 input.string(options=[]), extend.right enum coverage parity 는 codex 본인도 "drift 위험" 인정 → 완전 삭제는 over | Slice 1/2/3 작업 대부분 삭제하되, parity audit (Slice C) + UtBot strategy 4 항목 (Slice A) + DrFXGOD schema (Slice B) 로 scope pivot |

---

## 7. plan v2 핵심 변경 요약

| 항목            | v1                                         | v2                                                                     |
| --------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| Title           | Pine Architectural Fix                     | **Pine Coverage Layer Hardening + DrFXGOD Schema**                     |
| Slice 수        | 4 (Drawing/Syntax/Stdlib/Coverage)         | **3** (UtBot 4 unsupported / DrFXGOD schema / SSOT audit)              |
| 시간            | 25-40h                                     | **16-22h** (B 옵션 A‖C → B 병렬)                                       |
| 진입 통과율     | 3/6 (50%) 가정                             | **4/6 (67%)** 실측 baseline                                            |
| 목표 통과율     | 5/6 (83%)                                  | 5/6 (83%) — 동일하나 lever 가 UtBot strategy stable PASS               |
| §3 진단표       | LuxAlgo/RsiD FAIL                          | **LuxAlgo/RsiD 0 unsupported runnable**, UtBot strategy 4 + DrFXGOD 39 |
| §5 SSOT         | `SUPPORTED_ENUM_CONSTANTS=40+` (fictional) | **`_ENUM_PREFIXES=13` + parity audit test 4건**                        |
| §6 메타         | brainstorming + writing-plans + ...        | **+ baseline 재측정 preflight (LESSON-037 후보)**                      |
| §12 fixture     | symlink to tmp_code/                       | **canonical `backend/tests/fixtures/pine_corpus_v2/`** 그대로          |
| heikinashi 처리 | 단순 supported 추가 가정                   | **별도 ADR 결정 의무** (BL-096 Trust Layer 정합)                       |

---

## 8. LESSON-037 후보 (sprint kickoff 첫 step = baseline 재측정 preflight)

### 정의

> Sprint kickoff 의 첫 step = **baseline 재측정** (실측 fixture 통과율 + unsupported 카운트 + 실제 코드 구조 검증). 본인 dogfood 인상 또는 plan v1 가정을 그대로 신뢰하지 말 것. 전 sprint 결과 + 메모리 + 코드 변경 누적이 있으므로 plan 작성 전 실측 obligatory.

### 보강 규칙

- 본인 dogfood + plan 작성 후 **codex G0 (또는 self-review fallback) 1회 의무**. plan v1 의 stale 가정을 기존 코드 spot-check 으로 차단.
- 검토에서 **frame change** (= 핵심 가정 다수 stale 판정) 1회 발생 시 **plan v2 rewrite 의무**. plan v1 그대로 진행하지 말 것.
- 본 LESSON 의 **first validation = Sprint 29** (본 dev-log). second validation 은 Sprint 30+ 자연 검증. 3회 누적 시 `.ai/common/global.md` 또는 `.ai/project/lessons.md` 영구 승격.

### 적용 범위

- Type A (신규 기능) sprint: 의무
- Type B (risk-critical) sprint: 권장 (codex G0 단독으로도 가능)
- Type C (hotfix) sprint: 면제 가능 (단순 fix 일 경우)
- Type D (docs only) sprint: 면제

---

## 9. 본 dev-log 의 효용 (Sprint 30+ 사용 가이드)

### Sprint 30+ kickoff 시 본 파일 참조 필수

1. **baseline 재측정 preflight** 가 LESSON-037 second validation 인지 (3회 누적 trigger)
2. plan v1 가정과 실측 baseline 의 divergence 가 있는가? (codex G0 + fresh-context subagent 2-검토 권장)
3. SSOT 3 집합 (`SUPPORTED_FUNCTIONS=99` / `SUPPORTED_ATTRIBUTES=39` / `_ENUM_PREFIXES=13`) 의 size 가 변동했는가? (Sprint 29 Slice C 후 갱신 verify)
4. canonical fixture (`backend/tests/fixtures/pine_corpus_v2/`) 사용 의무 (symlink 금지)

### Sprint 29 종료 후 본 dev-log update 의무

- Sprint 29 retrospective 회고 안 §X "v1→v2 pivot 영향" 섹션에서 LESSON-037 second validation 결과 + 새 baseline 공식화 + Sprint 30+ 권장 명시
- 본 파일은 history 로 freeze (수정 X). retrospective 가 forward-looking 자료.

---

## 10. 영구 자산

### 본 dev-log 가 보존하는 사료

- codex G0 high reasoning 1.6M tokens 의 9 dimension verdict (FAIL)
- Opus fresh-context spot-check 결과 (CONDITIONAL PASS)
- 일치 발견 4건 / codex 단독 critical 4건 / 의견 충돌 2건 / codex 명백한 오류 2건
- plan v1 → v2 pivot decision rationale
- LESSON-037 후보 정의 + 적용 범위

### Cross-link

- plan v2: `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`
- LESSON 후보: `.ai/project/lessons.md` LESSON-037 entry
- 영구 규칙 출처: `docs/04_architecture/pine-execution-architecture.md` (Slice C 갱신 후)
- baseline snapshot: `docs/dev-log/2026-05-04-sprint29-baseline-snapshot.md` (Slice C 안 작성)
- heikinashi ADR: `docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md` (Slice A 안 작성)

---

**End of Sprint 29 v1→v2 pivot dev-log.**
