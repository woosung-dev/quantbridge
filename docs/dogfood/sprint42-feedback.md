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

#### Day 1 (2026-05-\_\_): 첫 인상

- **시간**: \_\_\_분
- **마찰**:
  - (해당 없음 또는 채움)
- **의외였던 점**:
- **이게 부족함**:

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

- **발송일**: 2026-05-\_\_
- **가입 성공**: ☐ Yes / ☐ No (사유: \_\_\_)
- **첫 backtest 완료**: ☐ Yes / ☐ No
- **Test Order 시도**: ☐ Yes / ☐ No / ☐ Skip
- **share link viral**: 그 지인의 지인 view 발생? ☐ Yes / ☐ No / ☐ Unknown
- **인터뷰 일정**: 2026-05-\_\_ (30분)
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

- **발송일**: 2026-05-\_\_
- **가입 성공**: ☐ Yes / ☐ No
- **첫 backtest 완료**: ☐ Yes / ☐ No
- **Test Order 시도**: ☐ Yes / ☐ No / ☐ Skip
- **share link viral**: ☐ Yes / ☐ No / ☐ Unknown
- **인터뷰 일정**: 2026-05-\_\_ (30분)
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

## NPS 요약 (Day 14 close-out 시점)

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
