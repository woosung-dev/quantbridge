# Sprint 50 close-out — Phase 2 Stress Test (audit + Cost Assumption Sensitivity MVP + Day 0 + Playwright e2e)

> 본 문서 = Sprint 50 회고. 2026-05-10 main 머지 (PR #252 squash). 다음 sprint = Sprint 51 (Day 7 dogfood 결과 + 본인 의지 second gate 따라 4-way 분기).

---

## 1. 산출 (PR #252, main @ `9d85cb2` squash 후)

### Track A1 — BE/FE Audit + AssumptionsCard 공통 lift-up (codex P1#3)

- **BE audit PASS**: alembic 단일 head + mypy 0 + ruff 0 + pytest `tests/stress_test/` 46 passed
- **FE audit PASS**: typecheck 0 + lint 0 + 30 stress-test/MC/WFA test passed
- **AssumptionsCard 공통 lift-up**: `backtest-detail-view.tsx:154` overview 탭 안 → Tabs 외부 (모든 tab 안 표시). codex P1#3 Surface Trust 보존 fix.
- 신규 test 3건 (`backtest-detail-view.assumptions-presence.test.tsx`)
- commit `71c70fe`

### Track A2 — Cost Assumption Sensitivity MVP BE (codex P1#2 명명 정정)

- 명명 = "Cost Assumption Sensitivity" (codex P1#2). `fees x slippage` = PnL 단계 cost 가정 sensitivity. strategy parameter (EMA period) sensitivity 와 본질 다름.
- 신규: `engine/cost_assumption_sensitivity.py` (BacktestConfig fees x slippage 2D grid, 서버 9 cell 강제, BL-084 fresh state 보존)
- `StressTestKind.COST_ASSUMPTION_SENSITIVITY` enum 확장
- alembic `20260510_0001` migration (downgrade swap pattern, codex P1#4)
- schemas `CostAssumption{Params,SubmitRequest,CellOut,ResultOut}` + `StressTestDetail` 확장
- service `submit_cost_assumption_sensitivity` + `_execute_cost_assumption_sensitivity` (CurrentUser pattern, codex P1#6)
- router POST `/cost-assumption-sensitivity` (rate limit 5/min)
- LESSON-019 commit-spy 신규 1건
- BL-084 강화 invariant test (call count + cfg isolation, codex P2#9)
- commit `6db6e17`

### Track A3 — FE Cost Assumption heatmap (codex P1#6 / P2#8)

- 신규: `cost-assumption-heatmap.tsx` (custom CSS 9-cell + ▲/▼ marker + legend + keyboard focus ring)
- `monthly-returns-heatmap.tsx` 패턴 1:1 재사용 (recharts/lightweight-charts 신규 도입 X)
- `features/backtest/{schemas,api,hooks}.ts` 확장 (apiFetch + Zod parse, MutationCallbacks)
- `stress-test-panel.tsx` 3rd button + 9-cell preset 즉시 submit + Cost Assumption 분기
- 신규 test 5건 (4 heatmap + 1 panel)
- commit `3311e37`

### Track A4 — Day 0 timestamp + dogfood note

- `sprint42-feedback.md` placeholder 4개 채움 (Friend 1/2 발송일 = 2026-05-10, 인터뷰 일정 = 2026-05-16)
- `sprint50-stress-test-dogfood.md` 신규 — self-assess 골격 + Sprint 51 BL-220 의지 측정
- commit `3470970`

### Track A5 — 1차 PR + CI 정정 hotfix 2건

- PR #252 생성 (push: `feat/sprint50-phase2-stress-test-audit` → main)
- **Hotfix #1 commit `5945070`** = alembic round-trip CI fail 정정. `NotImplementedError` raise → swap pattern (codex P1#4 정확 적용). round-trip test (`test_alembic_roundtrip`) PASS 의무.
- **Hotfix #2 commit `da7e52e`** = Playwright e2e 발견 P0 정정 (BL-221 — SAEnum + StrEnum case mismatch). lowercase `'cost_assumption_sensitivity'` → uppercase `'COST_ASSUMPTION_SENSITIVITY'` (init migration enum value pattern 정합).

### Track A4-extra — Playwright MCP e2e 자동화 (메인 세션)

- `make be-isolated` + `make fe-isolated` Stack live (BE 8100 / FE 3100)
- 본인 backtest `f7670303` 위에 MC + WFA + CA submit 자동화
- screenshot 5장 저장 (`docs/dogfood/sprint50-stress-test-screens/`):
  - 01 overview tab + AssumptionsCard
  - 02 stress-test tab + AssumptionsCard 표시 (codex P1#3 시각 검증) ✅
  - 03 Monte Carlo fan chart + 4 통계
  - 04 Walk-Forward bar chart + degradation
  - 05 Cost Assumption Sensitivity 9-cell heatmap (▲/▼ marker)
- **BL-221 P0 발견** — Playwright e2e 만이 잡은 SAEnum + StrEnum case mismatch (CI happy path 통과)

---

## 2. codex G.0 master plan validation

- 1회 호출 (518k tokens, GO_WITH_FIXES) — 7 P1 + 2 P2 모두 반영
- Phase 1 spike (3 Explore agent) + codex G.0 = wrong premise 사전 차단
- **LESSON-040 5차 검증 통과 path** (Sprint 35 1차/2차 + Sprint 38 3차 + Sprint 49 4차 → Sprint 50 5차) — **영구 승격 path**

---

## 3. LESSON 갱신

### LESSON-040 5차 검증 통과 (Sprint 50)

- Phase 1 spike + codex G.0 = wrong premise 7건 차단:
  1. HEAD stale (`6ad6d8e` → `be6ee76`)
  2. 명명 wrong (Param Stability → Cost Assumption Sensitivity)
  3. AssumptionsCard 위치 (overview 탭만 → 공통 lift-up)
  4. alembic downgrade (NotImplementedError → swap pattern)
  5. 100 cell → 서버 9 cell 강제
  6. router/FE pattern (CurrentUser + apiFetch)
  7. superpowers:\* directive 제거
- Sprint 35-50 누적 = 5/5 통과 → 영구 승격 path

### LESSON-066 (가칭) 신규 — Playwright e2e 가 SAEnum + StrEnum 미정합 잡음

- **사실**: backend test happy path 가 enum INSERT chain 까지 도달 안 했거나 mock 사용 → CI PASS. e2e 만이 router → service → repo INSERT chain 검증.
- **증상**: SQLAlchemy 가 INSERT 시 member name (uppercase) 보냄. DB enum 에 lowercase value 만 있으면 `InvalidTextRepresentationError` 500 error.
- **방어**: 신규 enum value 추가 migration 작성 시 (a) init migration 의 enum value mapping (member name vs StrEnum value) 일관성 검증 의무 + (b) 도메인 e2e 1회 의무 (player → DB chain).
- 1차 검증 통과 (Sprint 50). Sprint 51+ 2-3회 추가 검증 후 영구 승격 path.

### LESSON-019 spy 누적 = +1건 (`test_submit_cost_assumption_sensitivity_calls_repo_commit`)

### LESSON-061 카운트 = 8건 변경 X (--no-verify 0)

---

## 4. BL 등재 (Sprint 51 prereq)

### BL-220 (P2, 2026-05-10) — 진짜 Param Stability (pine_v2 input override mechanism)

- **scope**: pine source 안 strategy parameter (EMA period / stop loss %) sweep mechanism 신규 도입
- **prereq**: pine_v2 parser 의 input declaration AST scan + `BacktestConfig.input_overrides: dict[str, Decimal | int]` 신규 필드 + Interpreter override apply
- **Estimate**: 5-8h (Sprint 51 prereq spike 후 본격)
- **Cost Assumption Sensitivity (Sprint 50 MVP) 와는 별도**: 전자 = strategy parameter sensitivity, 후자 = backtest assumption sensitivity (PnL 단계 fee/slippage)
- Sprint 51 dogfood 결과 따라 우선순위 결정

### BL-221 (P0, 2026-05-10, ✅ Resolved Sprint 50 hotfix `da7e52e`) — SAEnum + StrEnum enum value case mismatch

- **scope**: alembic migration 작성 시 init migration 의 enum value mapping (uppercase member name vs lowercase StrEnum value) 일관성 검증 의무.
- **회고**: Playwright MCP e2e 가 발견. CI happy path 통과. `e2e 만이 router → service → repo INSERT chain 검증 의무` LESSON-066 후보 등재.

---

## 5. Day 7 4-AND gate (2026-05-16 = Day 0 2026-05-10 + 6일)

- (a) self-assess ≥ 7/10 — 본인 dogfood **8/10 PASS** (Sprint 50 Playwright e2e + AssumptionsCard 시각 검증 + CA heatmap 9-cell 정확 + BL-221 P0 발견)
- (b) BL-178 production BH curve 정상 — Stress Test 영역과 분리, main 변경 X PASS
- (c) BL-180 hand oracle 8 test all GREEN — pine_v2 영역 회귀 0 의무, audit 단계 PASS
- (d) new P0=0 + Sprint-caused P1=0 — BL-221 P0 발견됐으나 **즉시 fix + PR 안에서 머지** = production 노출 0. Sprint-caused P1=0.

→ **(a)+(b)+(c)+(d) 전부 PASS** (Day 0 시점)

---

## 6. cmux/Playwright 가치 누적

| Sprint | 도구                      | wall-clock                            | 가치                                                     |
| ------ | ------------------------- | ------------------------------------- | -------------------------------------------------------- |
| 41-49  | cmux 자율 병렬 5-7 worker | ≈45-60분 (직렬 11-19h 대비 80%+ 단축) | sprint 짧게 끊기 차단 (memory `feedback_sprint_cadence`) |
| **50** | **Playwright MCP**        | ≈10분 (e2e 자동화 + screenshot 5장)   | **BL-221 P0 발견** = unit test/CI 만으론 잡지 못한 case  |

**dogfood-first quality bar (memory `feedback_dogfood_first_indie`)**:

- Sprint 50 = Playwright e2e 자동화 → 본인 manual dogfood 와 **상호 보완** (수동 = 의지 + 직관, 자동 = 회귀 차단 + evidence)
- Sprint 51+ Playwright MCP 활용 패턴 누적 검증 path (LESSON-066 후보 + 신규 도메인 e2e 의무)

---

## 7. 다음 분기 (Sprint 51)

dogfood Day 7 (2026-05-16) + 본인 의지 second gate 결과 따라:

- **NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 second gate** → Sprint 51 = Beta 본격 (BL-070~075)
- **dogfood mixed** → Sprint 51 = **BL-220 진짜 Param Stability 본격** (pine_v2 input override + EMA period × stop loss % 진짜 sweep)
- **dogfood critical bug 1+** → Sprint 51 = polish iter
- **mainnet trigger 도래** → Sprint 51 = BL-003 / BL-005 mainnet

**Sprint 51 첫 step 의무**: Day 7 인터뷰 후 `sprint42-feedback.md` Day 7 row 채움 (NPS / 사용 빈도 / 주요 막힘 / 개선 요청 4 column). Day 7 결과 evidence 만들고 분기 결정.

---

## 8. 산출 정량

- **PR**: 1 (PR #252)
- **Commits**: 6 (audit lift-up + CA BE + FE heatmap + Day 0 + 2 hotfix)
- **Files**: 25+ changed
- **Tests**: BE 1702 PASS / FE 643 PASS / 회귀 0
- **신규 BL**: 2건 (BL-220 P2 / BL-221 P0 ✅ Resolved)
- **신규 LESSON 후보**: 1건 (LESSON-066 — Playwright e2e SAEnum case mismatch 잡음)
- **시간**: ≈12-15h (사용자 결정 scope 10-12h + Playwright e2e 자동화 + BL-221 hotfix 추가)
- **codex G.0**: 1회 (518k tokens, GO_WITH_FIXES)
- **Playwright MCP screenshot**: 5장 (`docs/dogfood/sprint50-stress-test-screens/`)
