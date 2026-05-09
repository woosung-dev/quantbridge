<!-- Sprint 42 Day 7 mid-check 골격 — Day 0 카톡 발송일 + 6일 시점 사용자가 채움 -->

# Sprint 42 Day 7 mid-check (= Day 0 발송일 + 6일)

> **상태**: 빈 골격 (Sprint 42 Phase 2 setup 시점 미리 작성, 2026-05-08. Sprint 48 Track 2 Worker D 갱신 2026-05-09).
> **codex Fix #7 (Sprint 48 G.0):** **Day 7 schedule = Day 0 발송일 + 6일**. Day 0 미기록 시 Day 7 고정 금지. 절대 날짜 (예: 2026-05-15, 2026-05-16, 2026-05-17, 2026-05-18, 2026-05-19) 사용 금지. Day 0 = 사용자 manual 카톡 발송 timestamp ([`../dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md) 의 "1-2명 micro-cohort log" 발송일 칸 기록).
> Day 7 도래 시 사용자가 본 파일 채움 + 파일명 `<Day 0 + 6일 실 일자>-sprint42-day7-midcheck.md` 로 rename (실 일자 반영).
> 4중 AND gate 결과 + N=1-2 행동 metric + 분기 결정.

**날짜:** Day 0 발송일 + 6일 (TBD — Day 0 timestamp 기록 후 채움)
**환경:** **\_ (isolated docker `make up-isolated` 또는 사용자 manual)
**점수:** \_**/10 (gate (a) **\_)
**Day 추적:\*\* Sprint 42 dogfood Day 1=Day 0 + 0 → Day 4=Day 0 + 3 → Day 7=Day 0 + 6 (모두 Day 0 발송일 기준 상대 일자)

---

## 1. 4중 AND gate 결과 (영구 기준)

| Gate                                               | 결과                        | 근거                                                                        |
| -------------------------------------------------- | --------------------------- | --------------------------------------------------------------------------- |
| **(a)** self-assess ≥ 7/10 + 근거 ≥ 3              | ☐ PASS / ☐ FAIL (\_\_\_/10) | (3 줄 근거 아래)                                                            |
| **(b)** BL-178 BH curve                            | ☐ PASS / ☐ FAIL             | (main `6d6a836` baseline 변경 X 영역. Day 7 시점 재확인)                    |
| **(c)** BL-180 hand oracle 8                       | ☐ PASS / ☐ FAIL             | (`tests/strategy/pine_v2/test_hand_oracle.py` 무수정 영역. 재확인)          |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | ☐ PASS / ☐ FAIL             | (`docs/dogfood/sprint42-feedback.md` BL 큐 P0 / Sprint 42-caused P1 카운트) |

### Gate (a) 근거 3줄 (사용자 작성)

1. (예: 본인 dogfood 5분 시나리오 **_초 — 목표 300초 _** 도달 / 마찰 \_\_\_건)
2. (예: 1-2명 micro-cohort 가입 **_/2 + 첫 backtest _**/2 + NPS 평균 \_\_\_/10)
3. (예: critical bug ***건 발견 / Resolved ***건 + Beta 본격 진입 신뢰도 \_\_\_)

---

## 2. 행동 metric 슬롯 (사용자 Day 7 시점 채움)

### 본인

- 5분 시나리오 합계: \_\_\_초 (목표 ≤300초)
- Day 1~7 사용 일수: \_\_\_/7
- 발견 bug: P0 ***건 / P1 ***건 / P2 \_\_\_건
- 본인 NPS: \_\_\_/10

### 1-2명 micro-cohort

| 대상     | 발송일 (= Day 0) | 가입      | 첫 backtest | Test Order         | 인터뷰 일정 (= Day 0 + 6일) | NPS     |
| -------- | ---------------- | --------- | ----------- | ------------------ | --------------------------- | ------- |
| Friend 1 | TBD (Day 0)      | ☐ Y / ☐ N | ☐ Y / ☐ N   | ☐ Y / ☐ N / ☐ Skip | TBD (Day 0 + 6일)           | \_\_/10 |
| Friend 2 | TBD (Day 0)      | ☐ Y / ☐ N | ☐ Y / ☐ N   | ☐ Y / ☐ N / ☐ Skip | TBD (Day 0 + 6일)           | \_\_/10 |

- sign-up 비율: \_\_\_/2 (목표 = N=1-2 중 ≥1 sign-up)
- 첫 backtest 완료 비율: \_\_\_/2
- 첫 5분 가치 도달 (정성 응답): \_\_\_
- share link viral coefficient (1-2명 → 그 지인의 지인 view 발생?): ☐ Yes / ☐ No / ☐ Unknown

### Surface Trust 검증 (Sprint 30 ADR-019 영구)

- 가정 박스 5: 본인 + 1-2명 인지 / 의문 \_\_\_
- 24 metric: 본인 + 1-2명 의미 도달 / 부족 \_\_\_
- 차트 정합 (lightweight-charts): 본인 + 1-2명 시각 자연스러움 \_\_\_
- 거래 목록: 본인 + 1-2명 200건 sort/filter 사용 \_\_\_

---

## 3. PASS 확인 항목 (Sprint 41 → 42 개선 효과 회귀 X)

> Sprint 41 산출물 (Worker B 디자인 / E UX / H share / B-2 App Shell + 4 페이지) 가 Day 7 시점에도 작동.

- 디자인 token (`design-tokens.ts` + globals.css `@theme inline`) 일관성: \_\_\_
- EmptyState / Skeleton / FormErrorInline 사용성: \_\_\_
- share link POST → GET → DELETE → 410 flow: \_\_\_
- App Shell sidebar 220px / Full Dark `/trading`: \_\_\_
- og:image 1200×630: \_\_\_

---

## 4. 신규 등록 BL (Sprint 42 dogfood 발견)

> `docs/dogfood/sprint42-feedback.md` 의 BL 큐 candidate ID → REFACTORING-BACKLOG.md BL-XXX 부여.
> Day 7 시점은 candidate 그대로 (close-out Day 14 시점 일괄 부여). 본 섹션 = Day 7 시점 가시성.

| Cand ID         | Priority | trigger | 1-line | 발견자 |
| --------------- | -------- | ------- | ------ | ------ |
| Sprint42-Cand-1 | P?       |         |        |        |

---

## 5. Day 7 분기 결정

> 4중 AND gate 결과에 따라:

- ☐ **gate 4 PASS** → Phase 3 Day 14 close-out 직행 (1주 더 dogfood, Day 14 close-out master 채움)
- ☐ **gate (a) FAIL** (점수 ≤6) → polish iter trigger (Sprint 42-hotfix 또는 Sprint 43 polish 우선)
- ☐ **gate (b)/(c) FAIL** → main 회귀 발생 (시급 hotfix, dogfood 일시 중단)
- ☐ **critical bug ≥1 발견 (gate (d) FAIL)** → 즉시 hotfix 분기 (Sprint 42-hotfix), Day 14 close-out 보류

### 결정 (사용자 작성)

- \_\_\_ (위 4 옵션 중)
- 사유 1-2 줄:

---

## Cross-link

- feedback 누적: [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md)
- Day 14 close-out 골격: [`docs/dev-log/2026-05-XX-sprint42-master.md`](2026-05-08-sprint42-master.md) (Day 14 도래 시 rename)
- Sprint 41 master (직전 완료): [`docs/dev-log/2026-05-07-sprint41-master.md`](2026-05-07-sprint41-master.md)
- Sprint 36 Day 7 양식 참조: [`2026-05-06-dogfood-day7-sprint36.md`](2026-05-06-dogfood-day7-sprint36.md)
