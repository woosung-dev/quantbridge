# dogfood Day 6 — Sprint 33 7 PR 머지 후 self-assess

**날짜:** 2026-05-05 (Sprint 33 종료 직후)
**환경:** isolated docker (5433/6380) + `make be-isolated` + `make fe-isolated`
**점수:** **5/10 (사용자 직관, 부문별 세부 채점 생략)**
**Day 추적:** Day 3=4 → Day 4=5 → Day 5=6~7 borderline → **Day 6=5 (regression -1.5~2)**

---

## 1. self-assess 점수

**5/10** — Day 5 borderline 대비 -1.5~2 regression.

### regression 원인 (사용자 dogfood 중 critical BUG 3건 발견)

| BUG                                               | 영향                                                               | 처리                                                             |
| ------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| **BL-175** Buy & Hold legend mismatch             | Surface Trust 직접 위반 — legend 와 chart 데이터 불일치 trust 박살 | ✅ 즉시 hotfix PR #146 (BH series + legend 자동 hide)            |
| **BL-176** SelectWithDisplayName Runtime ZodError | dropdown 조작 시 사용자 화면에 ZodError 폭발 = 동선 fail           | ✅ 즉시 hotfix PR #147 (`v=null` skip)                           |
| **BL-177** chart marker readability               | 157+ trade marker text 겹쳐 읽을 수 X (BL-171 follow-up)           | Sprint 34 defer (M 3-4h, marker count limit / cluster / shorten) |

**Sprint 33 의 5 BL Resolved + 2 hotfix 효과 (+ portion)** vs **dogfood 발견 BUG 3건 (- portion)** = **net -1.5~2 점**.

### 정직성 vs production quality

dogfood = automated test (vitest 398 + e2e all pass) 가 잡지 못하는 critical BUG 발견 mechanism 검증. **본 sprint 단독 BUG 3건** = surface trust pillar (Sprint 30 ADR-019) 의 마지막 gate 로 dogfood 의 가치 확정. 5점 = **정직한 측정** — production-quality 미달 명시.

### 비교: Sprint 32 와의 차이

- Sprint 32 (Day 5 = 6~7) = surface trust 명시 우선 sprint, BUG 발견 X (dogfood 자체가 plan 단계 안에서 진행 안 됨)
- Sprint 33 (Day 6 = 5) = polish + Beta prep + tooling 분산 + dogfood 가 sprint 종료 직후 진행 → BUG 3건 발견 → 점수 하락

= **dogfood 가 sprint 종료 직후가 아닌 sprint 안 mid-check 로 진행됐다면 BUG 발견 + 즉시 fix 의 cycle 이 sprint 안에서 마무리 가능**. Sprint 34+ 의 운영 패턴 후보.

---

## 2. Sprint 34 분기 결정

≥7 안정 미달 → **polish iter 2 (Beta 본격 진입 미루기)**.

### Sprint 34 우선순위

1. **BL-175 본격 fix** — backend `BacktestMetrics.buy_and_hold_curve` 신규 + OHLCV 첫/끝 가격 기반 정확 계산 + frontend 자체 계산 폐기 (M 3-4h)
2. **BL-177 chart marker readability** — zoom 영역 따라 marker count limit / cluster / text shorten / hover tooltip (M 3-4h, BL-171 follow-up)
3. **BL-166** uvicorn watch list `.env*` 미포함 root cause fix (Makefile 1 line + 검증 — S 1-2h)
4. **BL-176 follow-up** — SelectWithDisplayName clear 동선 정합화 (form 측 nullable schema 또는 별도 clear button — S 1-2h)
5. **BL-174 detail 분기** — live-session-detail Empty/Failed/Loading 통일 (Sprint 33 list-only scope 외 — S 1-2h)

### Sprint 34 후 dogfood Day 7 재측정 → ≥7 도달 시 → Sprint 35 Beta 본격 진입 (BL-070 도메인 + BL-071 + BL-072)

---

## 3. lesson 강화

1. **dogfood = sprint 안 mid-check 로 진행 후보** — 본 sprint 처럼 종료 직후 dogfood 시 BUG 발견 후 hotfix 추가 PR sequence = 후속 sprint scope 침범 risk. mid-sprint dogfood 가 BUG 발견 → 즉시 plan 안에서 fix 가능. Sprint 34+ 검증 후보
2. **automated test 100% pass 와 production quality 의 격차** — 본 sprint 398 tests pass + tsc/lint clean + e2e/live-smoke green 상태에서 critical BUG 3건 발견. test coverage 가 trust 보장의 충분조건이 아님. dogfood 영구 의무 step 강화 lesson
3. **신규 helper component 작성 시 base-ui callback edge case (null / undefined / clear) 검증 의무** (BL-176 lesson) — Worker prompt 강화 후보
4. **plan/retro URL 안내 검증 의무** — `/live-sessions/*` 잘못 명시 사례. plan agent critical files 명시 + 사용자-facing URL 도 동시 검증

---

## Cross-link

- Sprint 33 retro: `docs/dev-log/2026-05-05-sprint33-master-retrospective.md`
- BL-175 hotfix PR #146 / BL-176 hotfix PR #147 / BL-177 신규 등록
- BACKLOG: `docs/REFACTORING-BACKLOG.md` 변경 이력 entry
