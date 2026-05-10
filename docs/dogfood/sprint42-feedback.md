<!-- Sprint 42 dogfood feedback master — 본인 + 1-2명 micro-cohort 누적 기록 -->

# Sprint 42 dogfood feedback

> Sprint 42 = 본인 + 1-2명 micro-cohort demo 오픈 (Bybit Demo Trading) + 1-2주 dogfood + Beta 본격 진입 (BL-070~075) trigger 결정.
> 본 파일 = **live 누적 기록** (수정 빈도 높음). Day 7 mid-check / Day 14 close-out 회고는 `docs/dev-log/` 별도 파일.
> 작성 시작: 2026-05-08. 채널: 카톡 DM 직접 인터뷰 + repo markdown.

---

## 본인 dogfood log

> Phase 1.1 (외부 첫인상 polish 9건 PR #183) 이후 본격 1주 사용 기록. Day 1~7 진행하며 채움.

### 5분 시나리오 6 단계 시간 측정 (목표 ≤5분)

| 단계     | 항목                                     | 소요 시간    | 비고                               |
| -------- | ---------------------------------------- | ------------ | ---------------------------------- |
| 1        | Clerk 가입                               | \_\_\_초     |                                    |
| 2        | Bybit Demo + API key 발급                | \_\_\_초     | (Bybit 외부 사이트 시간 별도)      |
| 3        | QuantBridge 거래소 계정 등록 (Demo 모드) | \_\_\_초     | DEMO 배지 확인                     |
| 4        | 첫 backtest 실행                         | \_\_\_초     | Pine Script v5 paste → 실행 → 결과 |
| 5        | share link 공유 (clipboard + og:image)   | \_\_\_초     |                                    |
| 6        | (선택) Test Order Dialog 발송            | \_\_\_초     | KillSwitch 차단 여부               |
| **합계** |                                          | **\_\_\_초** | 5분(300초) 도달 여부               |

### Day-by-Day 사용 기록

#### Day 1 (2026-05-08): 첫 인상 — Sprint 42 Phase 2 setup PR #187 머지 직후

- **시간**: ~10분 (localhost:3100 띄우고 둘러봄)
- **마찰**:
  - **체계적 visual fidelity 갭**: prototypes 12 HTML 디자인 소스 vs 실제 구현 사이 큰 갭 발견. Sprint 41 Worker B-2 가 4 페이지 (strategies / backtests 리스트 / dashboard / trading) 만 App Shell + KPI strip + filter chip 적용. 나머지 핵심 페이지 8개 (`/sign-in` `/sign-up` `/onboarding` `/strategies/new` `/strategies/[id]/edit` `/backtests/new` `/backtests/[id]` `error/not-found`) 가 prototype visual 미반영
  - 사용자 피드백 (verbatim): "프로토타입처럼 안 되어있고.. 너무 사용자들이 쓰기에는 좀 그런것 같은데... 체계적인 개편이 필요할것 같은데"
  - **1-2명 micro-cohort 발송 prereq blocker** — 외부 첫인상 손상 risk
- **의외였던 점**:
  - 디자인 token (`design-tokens.ts` + globals.css `@theme inline`) 자체는 잘 깔려 있음 (Sprint 41 Worker B). 갭의 95% = 페이지별 visual polish 미적용 (component spec 부재)
  - ui-ux-pro-max 스킬 진단 결과 fintech/quant 권장 디자인 시스템 (Inter / `#1E40AF` primary / amber accent / Real-Time Operations Pattern) 과 현재 token 거의 정합
- **이게 부족함**:
  - 5분 시나리오 funnel 4 페이지 (04 Login / 05 Onboarding / 07 Strategy Create / 08 Backtest Setup) 의 prototype-grade visual fidelity. 4 페이지 모두 1-2명 발송 시 첫인상 결정
- **다음 step**:
  - Sprint 42 dogfood phase **일시 중단** (사용자 ★★★★★ 결정)
  - **Sprint 42-polish 분기** = 자율 병렬 cmux 4 worker (W1 Login / W2 Onboarding / W3 Strategy Create / W4 Backtest Setup) — `<repo>/.claude/plans/sprint42-polish-prompt.md`
  - `stage/sprint42-polish` 분기 + push 완료 (bypass 1회 사용자 명시 승인)
  - polish 완료 후 본인 dogfood Day 2 재시작 (5분 시나리오 측정 → ≤300초 + 마찰 0건 = 1-2명 발송 trigger)
  - 02 Backtest Report (이미 양호) + 10 Trades Detail (architecture) + 01 Editor + 11 Error pages = Sprint 43 polish 이관

- **2026-05-08 Day 1 polish-2 완료 후 재시작**:
  - Sprint 42-polish (Wave 1) + polish-2 fidelity (Wave 2) 통합 stage→main 머지 완료 (PR #199, main `9fec5fa`)
  - 4 페이지 prototype 1:1 visual fidelity 적용 (4 페이지 × 2 wave = 8 PR / +2700 lines / 회귀 0)
  - **사용자 manual dogfood 5분 시나리오 funnel OK 회신** (2026-05-08)
  - 다음 step = Phase 1.3 (share link sample 본인 backtest 1-2건 + share token) → 1-2명 micro-cohort 카톡 DM 발송 prereq → Phase 2 dogfood 본격 (1-2주 wall-clock)
  - LESSON-051~053 후보 등재 (`.ai/project/lessons.md`, gitignored): baseline 정리 의무 / Worker prompt pwd 검증 / N=4+ cmux 우선

- **2026-05-08 Sprint 43 완료 — 모든 활성 페이지 prototype-grade**:
  - Sprint 43 = 12 페이지 prototype-grade visual fidelity 일괄 적용 (Wave 1+2+3, 자율 병렬 Agent isolation=worktree 4 × 3 wave). main @ `fa20798` (PR #214)
  - 추가 적용 페이지: landing / strategies-list / backtests-list / strategy-editor / backtest-report / **trades-detail 신규 page** / trading polish / error pages + maintenance / waitlist / 법무 4 / admin/waitlist / share
  - 13 PR / 83 files / +96 신규 tests (501 → 597 PASS, 회귀 0)
  - **isolation 위반 0건** (Sprint 42-polish-2 매 sprint 1건+ → Sprint 43 = 0, **LESSON-055 결정적 검증**)
  - 사전 worktree 12 + branch 12 + node_modules symlink 일괄 생성 + Worker prompt 첫 step `cd <absolute worktree path>` 명시 = 4 조건 충족 시 isolation 위반 0 보장
  - 다음 step = Phase 2 dogfood 본격 (16+ 페이지 모두 visual fidelity 통과) → 1-2명 micro-cohort 카톡 DM 발송 → 1-2주 dogfood → Sprint 44 분기 결정

#### Day 2~3:

- 사용 빈도:
- 발견 bug:
- UX 개선점:

#### Day 4~6:

- 반복 사용성:
- 새로 발견:

#### Day 7 self-assess (≥7/10 = gate (a) PASS)

- 점수: \_\_\_/10
- 근거 3 줄:
  1.
  2.
  3.

---

## 1-2명 micro-cohort log

> 1-2명 카톡 DM 발송 후 응답 옮겨 적기. 본인 인터뷰 노트도 여기.

### Friend 1: \_\_\_ (이니셜 또는 별칭)

- **발송일**: 2026-05-10 (Day 0 = Sprint 49 close-out 머지일과 동일, codex Fix #7)
- **가입 성공**: ☐ Yes / ☐ No (사유: \_\_\_)
- **첫 backtest 완료**: ☐ Yes / ☐ No
- **Test Order 시도**: ☐ Yes / ☐ No / ☐ Skip
- **share link viral**: 그 지인의 지인 view 발생? ☐ Yes / ☐ No / ☐ Unknown
- **인터뷰 일정**: 2026-05-16 (Day 7 = Day 0 + 6일, 30분)
- **NPS (1주 후 0-10)**: \_\_\_
- **NPS reason 1-2줄**:

#### 발견 bug

| ID     | Priority | 설명 | BL 등재 |
| ------ | -------- | ---- | ------- |
| F1-B-1 | P?       |      |         |

#### feature request

| ID     | 영향                          | 설명 |
| ------ | ----------------------------- | ---- |
| F1-R-1 | Beta? / Sprint 43+ / deferred |      |

---

### Friend 2: \_\_\_ (이니셜 또는 별칭, 발송 시 채움)

- **발송일**: 2026-05-10 (Day 0 = Sprint 49 close-out 머지일과 동일, codex Fix #7)
- **가입 성공**: ☐ Yes / ☐ No
- **첫 backtest 완료**: ☐ Yes / ☐ No
- **Test Order 시도**: ☐ Yes / ☐ No / ☐ Skip
- **share link viral**: ☐ Yes / ☐ No / ☐ Unknown
- **인터뷰 일정**: 2026-05-16 (Day 7 = Day 0 + 6일, 30분)
- **NPS (1주 후 0-10)**: \_\_\_
- **NPS reason 1-2줄**:

#### 발견 bug

| ID     | Priority | 설명 | BL 등재 |
| ------ | -------- | ---- | ------- |
| F2-B-1 | P?       |      |         |

#### feature request

| ID     | 영향                          | 설명 |
| ------ | ----------------------------- | ---- |
| F2-R-1 | Beta? / Sprint 43+ / deferred |      |

---

## Day 7 mid-check row (= Day 0 발송일 + 6일)

> **codex Fix #7 (Sprint 48):** Day 7 schedule = Day 0 카톡 발송 timestamp + 6일. **절대 날짜 (예: 2026-05-15) 금지**. Day 0 미기록 시 본 row 채움 금지 — 발송 후 timestamp 먼저 위 "1-2명 micro-cohort log" 발송일 칸에 기입.
> 본 row schema = Day 1 본인 사용 기록 schema 와 일관 (NPS 0-10 / 사용 빈도 / 주요 막힘 / 개선 요청 4 column).

| 대상     | Day 7 도래일 (= Day 0 + 6) | NPS 0-10 (Day 7 mid-check) | 7일 사용 빈도 (며칠/몇 번) | 주요 막힘 (1-2 줄) | 개선 요청 (1-2 줄) |
| -------- | -------------------------- | -------------------------- | -------------------------- | ------------------ | ------------------ |
| 본인     | TBD (Day 0 + 6일)          | \_\_/10                    | \_\_\_일/\_\_\_회          |                    |                    |
| Friend 1 | TBD (Day 0 + 6일)          | \_\_/10                    | \_\_\_일/\_\_\_회          |                    |                    |
| Friend 2 | TBD (Day 0 + 6일)          | \_\_/10                    | \_\_\_일/\_\_\_회          |                    |                    |

---

## NPS 요약 (Day 14 close-out 시점, = Day 0 발송일 + 13일)

| 대상     | NPS         | 핵심 reason                         |
| -------- | ----------- | ----------------------------------- |
| 본인     | \_\_/10     |                                     |
| Friend 1 | \_\_/10     |                                     |
| Friend 2 | \_\_/10     |                                     |
| **평균** | **\_\_/10** | (Day 7 기준 ≥7 = gate 통과 trigger) |

---

## BL 등록 큐 (Sprint 42 → REFACTORING-BACKLOG.md append candidate)

> 본 sprint dogfood 발견분 → close-out 시점에 `docs/REFACTORING-BACKLOG.md` 로 BL-XXX 부여 후 이관.
> 진행 중에는 candidate ID (`Sprint42-Cand-N`) 로 임시 추적.

| Cand ID         | Priority | trigger | 1-line 설명 | 발견자 / Day |
| --------------- | -------- | ------- | ----------- | ------------ |
| Sprint42-Cand-1 | P?       |         |             |              |

---

## critical bug 발견 시 즉시 hotfix 분기 plan

> P0 (실거래 위험 / 데이터 손실 / 인증 우회) 발견 시:
>
> 1. 본 파일 BL 큐 candidate 등록 + Priority P0 명시
> 2. 메인 세션에 즉시 보고 → Sprint 42-hotfix 분기 (별도 PR)
> 3. hotfix 머지 후 본 파일 candidate Resolved 표시
> 4. Sprint 43 = Beta 본격 진입 보류 / polish iter 우선

P1 (UX 막힘 / 일부 페이지 작동 안 함) 발견 시:

- 본 파일 candidate 등록 + Day 7 mid-check 시 종합 평가
- 1건 = polish iter 트리거 X (Day 7 gate (a) 점수 반영)
- ≥3건 = polish iter trigger

---

## Cross-link

- Sprint 42 prompt: [`<repo>/.claude/plans/sprint42-demo-friend-open-prompt.md`](../../.claude/plans/sprint42-demo-friend-open-prompt.md) (gitignored)
- onboarding 가이드 (외부 발송용): [`docs/guides/demo-onboarding.md`](../guides/demo-onboarding.md)
- Day 7 mid-check: [`docs/dev-log/2026-05-XX-sprint42-day7-midcheck.md`](../dev-log/2026-05-08-sprint42-day7-midcheck.md) (Day 7 도래 시 rename)
- Day 14 master: [`docs/dev-log/2026-05-XX-sprint42-master.md`](../dev-log/2026-05-08-sprint42-master.md) (Day 14 도래 시 rename)
- Sprint 41 master (직전 완료): [`docs/dev-log/2026-05-07-sprint41-master.md`](../dev-log/2026-05-07-sprint41-master.md)
