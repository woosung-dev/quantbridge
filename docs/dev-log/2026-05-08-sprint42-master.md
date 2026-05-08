<!-- Sprint 42 master retrospective 골격 — Day 14 도래 시 사용자 + 메인 세션이 채움 -->

# Sprint 42 Master Retrospective — 본인 + 1-2명 micro-cohort demo 오픈 + feedback loop

> **상태**: 빈 골격 (Sprint 42 Phase 2 setup 시점 미리 작성, 2026-05-08).
> Day 14 도래 시 사용자 + 메인 세션이 본 파일 채움 + 파일명 `2026-05-2X-sprint42-master.md` 로 rename (실 일자 반영).
> 직전 Sprint 38/39/41 close-out 패턴에서 빈 골격 채우기 시간 ~1/3 단축 확인.

**기간**: 2026-05-08 (Phase 2 setup) → 2026-05-2\_ (Phase 4 close-out, Day 14 ≈)
**브랜치**: main `6d6a836` (Sprint 41 close-out) → **_ (Sprint 42 close-out PR # _**)
**활성 sprint type**: 본인 + 1-2명 micro-cohort demo 오픈 + feedback loop. **single track + 사용자 manual** (코드 변경 거의 X).
**self-assessment Day 7**: **_/10 (gate (a) _**) — Day 7 mid-check 결과 반영
**self-assessment Day 14**: **_/10 (Phase 4 close-out 시점 재평가)
**다음 분기**: Sprint 43 = _** (3 옵션 중)

---

## 1. Context — 왜 Sprint 42 가 필요했나

> 사용자가 Day 14 시점 fact 기록.

Sprint 41 = 외부 demo 첫인상 패키지 (디자인 + UX + share, 4 PR Wave 1+2 자율 병렬 cmux 5번째 실측) Day 7 = 8/10 PASS. 사용자 방향 = **mainnet 보류 → demo 본격 오픈 N=5** (이후 사용자 prereq 답변에서 "본인 + 1-2명 micro-cohort" 로 축소).

Sprint 42 = \_\_\_ (Day 14 시점 사용자 보강).

---

## 2. 산출물 (Phase 1.1 / 1.2 / 1.3 / Phase 2 dogfood 결과)

### Phase 1.1 (이전 sprint 41 close-out 시점) — 본인 자가 dogfood polish 9건 (PR #183)

> Sprint 41 close-out 후 / Sprint 42 Phase 1.1 로 분류된 9건. 한국어 일관 마찰 9건 hot-fix.
> (PR #183 commit `4d226dc` — `polish: /trading + 차트 한국어 일관 마찰 9건 (외부 demo 첫인상)`)

### Phase 1.2 — onboarding 가이드 (PR #184)

- 신규: `docs/guides/demo-onboarding.md` (86 lines, 5분 시나리오 6 단계)
- 1-2명 카톡 DM 발송용 1 페이지

### Phase 1.3 — share link sample 1-2건 (사용자 manual)

- 본인 backtest **_ (전략 _**, 기간 **_) + share token _**
- 본인 backtest **_ (전략 _**, 기간 **_) + share token _** (선택)

### Phase 2 — 1-2주 dogfood + feedback (`docs/dogfood/sprint42-feedback.md` 누적)

> live 누적 기록 → Day 14 close-out 시점 요약 옮겨 적기.

#### 본인 dogfood 요약

- 5분 시나리오 합계: \_\_\_초 (목표 ≤300초)
- 사용 일수: \_\_\_/14
- 발견 bug: P0 ***건 / P1 ***건 / P2 \_\_\_건
- 본인 NPS: \_\_\_/10

#### 1-2명 micro-cohort 요약

| 대상     | 가입  | 첫 backtest | NPS     |
| -------- | ----- | ----------- | ------- |
| Friend 1 | ☐ Y/N | ☐ Y/N       | \_\_/10 |
| Friend 2 | ☐ Y/N | ☐ Y/N       | \_\_/10 |

- sign-up 비율: \_\_\_/2
- 첫 backtest 비율: \_\_\_/2
- share link viral: ☐ Yes / ☐ No / ☐ Unknown
- NPS 평균: \_\_\_/10

---

## 3. 회귀 / 검증

| 항목                          | baseline (main `6d6a836`)            | Day 14 재측정 | 변동   |
| ----------------------------- | ------------------------------------ | ------------- | ------ |
| BE pytest                     | 1686 PASS / 42 skip / 0 fail         | \_\_\_        | \_\_\_ |
| FE vitest                     | 457 PASS / 74 files                  | \_\_\_        | \_\_\_ |
| ruff / mypy / pnpm lint / tsc | 0 errors                             | \_\_\_        | \_\_\_ |
| idle CPU                      | < 10% (Sprint 41 모든 컨테이너 < 3%) | \_\_\_        | \_\_\_ |

### Playwright 자동 검증 (Sprint 41 10/10 PASS 회귀 X 확인)

| #   | 항목                                                                  | Day 14 결과 |
| --- | --------------------------------------------------------------------- | ----------- |
| 1   | App Shell sidebar 220px / header 64px                                 | ☐           |
| 2   | /strategies / /backtests / /backtests/{id} / /trading 4 페이지 layout | ☐           |
| 3   | /backtests KPI 4 + filter chip 6 + 테이블                             | ☐           |
| 4   | share full flow (POST → GET → POST 멱등 → DELETE → 410)               | ☐           |
| 5   | og:image 1200×630 PNG                                                 | ☐           |
| 6   | 외부 demo 첫인상 polish 9건 (PR #183) 회귀 X                          | ☐           |

---

## 4. Day 7 / Day 14 4중 AND gate 결과

### Day 7 mid-check (≈2026-05-15)

| Gate                                               | 결과                        | 근거                  |
| -------------------------------------------------- | --------------------------- | --------------------- |
| **(a)** self-assess ≥ 7/10                         | ☐ PASS / ☐ FAIL (\_\_\_/10) | (Day 7 midcheck 인용) |
| **(b)** BL-178 BH curve                            | ☐ PASS / ☐ FAIL             |                       |
| **(c)** BL-180 hand oracle 8                       | ☐ PASS / ☐ FAIL             |                       |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | ☐ PASS / ☐ FAIL             |                       |

### Day 14 close-out (≈2026-05-22)

| Gate                                               | 결과                        | 근거 |
| -------------------------------------------------- | --------------------------- | ---- |
| **(a)** self-assess ≥ 7/10 + 근거 ≥ 3              | ☐ PASS / ☐ FAIL (\_\_\_/10) |      |
| **(b)** BL-178 BH curve                            | ☐ PASS / ☐ FAIL             |      |
| **(c)** BL-180 hand oracle 8                       | ☐ PASS / ☐ FAIL             |      |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | ☐ PASS / ☐ FAIL             |      |

### Day 14 (a) 근거 3 줄 (사용자 작성)

1.
2.
3.

---

## 5. 신규 BL 등록 (Sprint 42 dogfood 발견)

> `docs/dogfood/sprint42-feedback.md` 의 BL 큐 candidate → BL-XXX 부여 후 `docs/REFACTORING-BACKLOG.md` 등재.

| BL      | 우선순위 | trigger | 1-line | 발견자                     |
| ------- | -------- | ------- | ------ | -------------------------- |
| BL-19\_ | P?       |         |        | 본인 / Friend 1 / Friend 2 |
| BL-19\_ | P?       |         |        |                            |
| BL-19\_ | P?       |         |        |                            |

**합계 변동**: 90 (Sprint 41 종료 = BL-190/191/192 신규) → *** (Sprint 42 신규 ***개) = **\_\_\_ active BL**.

---

## 6. LESSON 신규 후보 (.ai/project/lessons.md gitignored)

> Sprint 42 = single track + 사용자 manual. 코드 변경 거의 X 라 LESSON 후보 적을 수도 있음. 다만 demo 운영 / feedback 분류 / 인터뷰 패턴에서 신규 가능.

- **LESSON-051 후보 1/3**: \_\_\_ (예: micro-cohort N=1-2 첫인상 vs 본인 dogfood 차이 패턴)
- **LESSON-052 후보 1/3**: \_\_\_ (예: feedback markdown 누적 + Day 7/14 골격 미리 작성 = 채우기 시간 1/3 단축 검증)
- **LESSON-053 후보 1/3**: \_\_\_

---

## 7. Sprint 43 분기 결정

> Day 14 시점 4중 AND gate 결과 + 사용자 의사 결정.

### 옵션

- **A. Beta 본격 진입 (BL-070~075 도메인+DNS / Backend 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)**
  - 조건: Day 14 4중 AND PASS + critical bug 0 + NPS 평균 ≥7
  - 산출물: 6 BL 별도 sprint
- **B. polish iter (Sprint 43 polish)**
  - 조건: dogfood 신규 회귀 발견 / gate (a) FAIL / critical bug ≥1 발견
  - 산출물: 회귀 hotfix 우선
- **C. mainnet 본격 (BL-003 Bybit mainnet runbook / BL-005 본인 1-2주 mainnet dogfood)**
  - 조건: 사용자 명시 결정 (demo dogfood 결과 무관, 별도 trigger)
  - 산출물: mainnet 전환 sprint

### 결정 (사용자 작성)

- \_\_\_ (A / B / C 중)
- 사유 1-2 줄:

---

## Cross-link

- feedback 누적: [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md)
- Day 7 mid-check: [`docs/dev-log/2026-05-XX-sprint42-day7-midcheck.md`](2026-05-08-sprint42-day7-midcheck.md) (Day 7 도래 시 rename)
- onboarding 가이드: [`docs/guides/demo-onboarding.md`](../guides/demo-onboarding.md)
- Sprint 42 prompt: [`<repo>/.claude/plans/sprint42-demo-friend-open-prompt.md`](../../.claude/plans/sprint42-demo-friend-open-prompt.md) (gitignored)
- Sprint 41 master (직전): [`docs/dev-log/2026-05-07-sprint41-master.md`](2026-05-07-sprint41-master.md)
- Sprint 41 close-out PR: #182 (squash)
- Sprint 42 Phase 1 PR #183 (polish 9건) + #184 (onboarding) — Phase 1.1 / 1.2
- Sprint 42 Phase 2 setup PR # \_\_\_ (본 세션 산출 — feedback / midcheck / master 골격 + AGENTS.md 갱신)
- Sprint 42 close-out PR # \_\_\_ (Day 14 시점)
