# Sprint 60 진입 prereq — Day 7 인터뷰 카톡 template

> **목적**: dogfood Day 7 (2026-05-16) 인터뷰 진행용 카톡 메시지 template. 본 파일 그대로 복붙 → N=2-3 명에게 발송.
> **결과 기록 위치**: [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md) 의 `Friend 1` / `Friend 2` 섹션 + `Day 7 mid-check row`.
> **인터뷰 후 의사결정**: 4-AND gate 통과 여부 → Sprint 60 분기 (a/b/c/d) 결정.

---

## 카톡 발송 template (복붙용)

> 친한 정도에 따라 톤 조정 (반말/존댓말). N=2-3 명에게 같은 시점 발송 권장.

```
안녕 [이름]~ 지난주에 [QuantBridge 데모(quantbridge.io)] 한번 써봐달라고 부탁했었는데, 시간 괜찮으면 5-6개 질문만 답해줄 수 있을까?

1주일 정도 됐으니 첫인상이랑 막혔던 부분 솔직히 듣고 싶어. 카톡으로 짧게 답해줘도 되고, 30분 통화/대면도 환영. AI 코딩 도구로 만든 건데 외부 사람 한 명 첫인상이 진짜 중요해.

질문 6개:

1. (NPS) 친한 친구한테 추천할 가능성 0-10점 중 몇 점?
2. (점수 이유) 그 점수 준 가장 큰 이유 1-2 줄?
3. (1주일 사용) 지난 1주일 동안 몇 번 / 며칠 들어가봤어? (예: 3일 / 5번)
4. (막힌 지점) 가장 답답하거나 안 되거나 의도와 다르게 동작한 부분 있어? (1-2 줄, 없으면 "없음")
5. (개선 요청) 이거 있으면 정말 좋겠다 / 이건 진짜 별로다 = 1개씩 (각 1 줄)
6. (사용 의지) 솔직히 한 달 뒤에도 쓸 것 같아? Yes / No / Maybe + 이유 1 줄

답 받으면 무조건 커피라도 한 잔 살게 ☕ 진짜 고마워!
```

---

## 채점 가이드 (인터뷰 받은 후 메인 세션에서 적용)

> 위 6 답변 받은 후 `sprint42-feedback.md` Day 7 row + Friend 1/2 섹션에 옮겨 적고 아래 4-AND gate 적용.

### 4-AND gate (Sprint 60 분기 결정)

| Gate                                    | 기준                                                            | 측정 방법                                                                     |
| --------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **(a)** self-assess                     | 본인 + 외부 NPS 평균 ≥ 7/10                                     | 본인 self-assess + Friend 1/2 NPS Q1 평균                                     |
| **(b)** BL-178 production BH 정상       | 백테스트 BH curve 렌더 (사용자 manual 확인)                     | Friend 가 backtest 1건 실행 했다면 그 결과 화면 확인                          |
| **(c)** BL-180 hand oracle 8 test GREEN | CI 자동 검증 (이미 PASS 확인됨)                                 | Sprint 35 baseline 유지 = 자동 PASS                                           |
| **(d)** new P0=0 AND unresolved P1=0    | Friend Q4 답변 = "막힘 P0 0건" + Q5 = 데이터 손실/인증 우회 0건 | Friend 답변 안 "데이터 사라짐 / 로그인 안 됨 / 실거래 발생" 등 P0 키워드 없음 |

### Sprint 60 분기 매트릭스

| 4-AND gate 결과                | 본인 의지 | Sprint 60 = ?                                                                                   |
| ------------------------------ | --------- | ----------------------------------------------------------------------------------------------- |
| 4/4 PASS + Q6 "Yes" 다수       | **있음**  | **(a) Beta 본격 진입** (BL-070~075 도메인+DNS / BE 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트) |
| 4/4 PASS + Q6 "Yes" 다수       | 보류      | **(b) 잔여 active BL** (BL-003 mainnet runbook / BL-014 partial fill / BL-235 N-dim viz 등)     |
| (a) FAIL (NPS < 7) + 막힘 ≤2건 | —         | **(b) 잔여 active BL** + dogfood iter                                                           |
| (d) FAIL (P0 발견)             | —         | **(d) trust-breaking bug fix** 1 sprint 우선                                                    |
| mainnet trigger 외부 도래      | **있음**  | **(c) BL-003 + BL-005 mainnet 본격**                                                            |

### NPS 평균 산식

```
본인 self-assess + Friend 1 Q1 + Friend 2 Q1
─────────────────────────────────────────────  ≥ 7/10
              3 (또는 응답 수)
```

- N=1만 응답해도 진행 가능 (단, sample size N=1 caveat 의무 명시)
- 본인 self-assess 의 무게 = Friend 답변과 동일 (founder bias 회피)

### 막힘 카테고리화 (Q4 답변)

| 키워드                                                      | 카테고리                | priority                             |
| ----------------------------------------------------------- | ----------------------- | ------------------------------------ |
| "데이터 사라짐", "로그인 안 됨", "실거래 발생", "돈 사라짐" | **P0**                  | 그 fix 1 sprint 우선 (gate (d) FAIL) |
| "막혔다", "버튼 안 됨", "화면 깨졌다", "느리다 (5초+)"      | **P1**                  | 다음 sprint active BL 추가           |
| "혼란스러웠다", "직관적이지 않다", "예상과 달랐다"          | **P2**                  | polish iter 큐                       |
| "X 기능 있으면 좋겠다"                                      | feature request (P2/P3) | BL 등재 후 deferred                  |

---

## 인터뷰 진행 timeline (사용자 manual)

| 시점                | 작업                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| **2026-05-16 오전** | 카톡 template 복붙 + 발송 (N=2-3 명)                                       |
| 발송 후 24-48h      | 응답 수집 + `sprint42-feedback.md` Friend 1/2 섹션 옮겨 적기               |
| 응답 수집 완료      | 본인 self-assess Day 7 row 채움 (5분 시나리오 시간 측정 + 1-7 self-rating) |
| 4-AND gate 적용     | NPS 평균 + 막힘 카테고리화 + Q6 사용 의지 종합                             |
| Sprint 60 분기 결정 | 위 매트릭스 따라 (a)/(b)/(c)/(d) 중 선택                                   |
| 메인 세션 진입      | "Sprint 60 (X) 분기 진행해줘" 또는 "인터뷰 결과 정리해줘"                  |

---

## 응답 안 오는 경우 (24h 이상 무응답)

- 1차 reminder: "지난번 부탁한 거 답 부탁드릴게요~ 1분이면 돼요" (간단 톤)
- 48h 무응답: deferred. N=1만으로 진행 가능. sample size N=1 caveat 의무
- 친구가 "실제로 안 써봤다" 답변: 본 인터뷰 제외 + 본인 self-assess만으로 진행

---

## 외부 사용자 위협 평가 (privacy)

- Friend 답변 안 개인정보 (이름 / 카톡 ID) 는 본 repo 에 기록 X
- 이니셜 또는 별칭 사용 (예: "Friend 1: K", "Friend 2: A")
- repo 가 public 되더라도 외부 사용자 신원 불추적

---

## 관련 cross-link

- [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md) — 결과 기록 위치
- [`docs/guides/demo-onboarding.md`](demo-onboarding.md) — 첫 가입 5분 시나리오 가이드
- [`docs/REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) — Sprint 60 진입 후 신규 BL 등재
- [`docs/dev-log/2026-05-13-sprint59-close.md`](../dev-log/2026-05-13-sprint59-close.md) — Sprint 59 결과 + Sprint 60 prereq 명시
