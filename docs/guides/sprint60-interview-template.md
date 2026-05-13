# Sprint 60 진입 prereq — Day 7 인터뷰 2 tier 카톡 template

> **목적**: dogfood Day 7 (2026-05-16) 인터뷰 진행용. **외부 사용자 부담 최소화** — Tier 1 (30초 객관식) + Tier 2 (선택, 자유 텍스트).
> **결과 기록 위치**: [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md) 의 `Friend 1` / `Friend 2` 섹션 + `Day 7 mid-check row`.
> **인터뷰 후 의사결정**: 4-AND gate 통과 여부 → Sprint 60 분기 (a/b/c/d) 결정. **Tier 1 만으로 분기 가능**.

---

## 카톡 발송 template — 2 tier 구조

### Tier 1: 1차 메시지 (필수, 30초 부담)

```
안녕 [이름]~ 지난주에 QuantBridge 데모 한번 써봐달라고 부탁했었는데, 시간 30초만 줄 수 있어?

객관식 3개만 답해줘 ☕

1. 친한 친구한테 추천할 가능성 0-10점 중 몇 점?
   → 그냥 숫자 하나만!

2. 지난 1주일 동안 얼마나 들어가봤어?
   ① 안 써봤어  ② 1-2번  ③ 3-5번  ④ 거의 매일

3. 한 달 뒤에도 쓸 것 같아?
   ① Yes, 무조건  ② Yes, 좀 더 봐야  ③ Maybe  ④ No

진짜 30초면 돼! 정말 고마워 🙏
```

### Tier 2: Follow-up 메시지 (선택, Tier 1 응답 받은 후만)

> Tier 1 응답 받은 후 흥미/관계 정도에 따라 발송. 답 안 와도 OK.

```
헐 답해줘서 진짜 고마워! ☕

혹시 시간 더 되면 자세히 들려줄래? 솔직한 한 줄이 진짜 도움 돼.
(부담스러우면 그냥 패스해도 돼!)

4. 가장 답답하거나 안 되거나 의도와 다르게 동작한 부분 있어? (없으면 "없음")
5. 이거 있으면 정말 좋겠다 1개 + 이건 진짜 별로다 1개?
6. (3번에 답한 이유) 왜 그렇게 생각해? 1 줄이면 충분해.

답 받으면 무조건 커피 한 잔 살게! 😊
```

---

## 응답 패턴별 처리

| 시나리오    | 받은 응답                    | 행동                                                                           |
| ----------- | ---------------------------- | ------------------------------------------------------------------------------ |
| Best case   | Tier 1 + Tier 2 모두 응답    | 모든 정보 입력 → 4-AND gate + detail 분석                                      |
| Likely case | Tier 1 만 응답 (Tier 2 무시) | Tier 1 만으로 4-AND gate 분기 결정 가능. detail 없이도 진행                    |
| Worst case  | 무응답                       | 24h 후 1회 reminder ("1분만 답해줘~"). 48h 무응답 = 본인 self-assess 단독 분기 |
| 일부 응답   | "안 써봤어" 답변             | Friend 1/2 응답 제외. 본인 + 응답자 평균만 사용                                |

---

## 채점 가이드 (인터뷰 받은 후 메인 세션에서 적용)

> Tier 1 만으로도 4-AND gate 분기 가능. Tier 2 는 bonus detail.

### 4-AND gate (Sprint 60 분기 결정) — Tier 1 기반

| Gate                                    | 기준                        | Tier 1 측정                                                                    |
| --------------------------------------- | --------------------------- | ------------------------------------------------------------------------------ |
| **(a)** self-assess                     | 본인 + 외부 NPS 평균 ≥ 7/10 | Q1 NPS 평균                                                                    |
| **(b)** BL-178 production BH 정상       | 백테스트 BH curve 렌더 정상 | Sprint 35 baseline 유지 = 자동 PASS (Q2 "거의 매일" 답변자가 있으면 추가 확인) |
| **(c)** BL-180 hand oracle 8 test GREEN | CI 자동 검증                | 자동 PASS (Sprint 35 baseline)                                                 |
| **(d)** new P0=0 AND unresolved P1=0    | Q4 답변에 P0 키워드 0건     | Tier 2 응답 분석 (Tier 2 없으면 본인 dogfood 단독 평가)                        |

### NPS 평균 산식 (Q1 만 기반)

```
본인 self-assess + Friend 1 Q1 + Friend 2 Q1
─────────────────────────────────────────────  ≥ 7/10
              응답 수 (1, 2, 또는 3)
```

- "안 써봤어" (Q2 = ①) 응답자는 NPS 평균에서 제외
- N=1만 응답해도 진행 가능 (sample size caveat 명시)
- 본인 self-assess 무게 = Friend 답변과 동일 (founder bias 회피)

### Q2 사용 빈도 → 의미

| 답변        | 의미                                    | gate (b) 영향                                         |
| ----------- | --------------------------------------- | ----------------------------------------------------- |
| ① 안 써봤어 | dropout — 본인 dogfood 단독 진행        | 무관 (해당 응답자 제외)                               |
| ② 1-2번     | 첫인상 단계 머무름 — Q1 NPS 신뢰도 낮음 | 본인 manual 확인 의무                                 |
| ③ 3-5번     | 본격 사용 진입 — Q1 NPS 신뢰도 높음     | 본인 + 응답자 NPS 종합                                |
| ④ 거의 매일 | retention 신호 강함 — 가장 중요한 답변  | gate (b) 자동 신뢰 (사용자가 실제 backtest 화면 봤음) |

### Q3 사용 의지 → 분기 추천

| Q3 답변 다수              | Sprint 60 분기 권장                                                          |
| ------------------------- | ---------------------------------------------------------------------------- |
| ① Yes 무조건 + Q1 ≥ 8     | **(a) Beta 본격 진입** (BL-070~075) — 본인 의지 second gate 만 통과하면 즉시 |
| ② Yes 좀 더 봐야 + Q1 ≥ 7 | **(b) 잔여 active BL** + 1-2주 dogfood iter                                  |
| ③ Maybe + Q1 ≥ 6          | **(b) 잔여 active BL** + Tier 2 detail 분석 후 polish iter                   |
| ④ No                      | **(d) trust-breaking bug fix** 또는 dogfood 가설 재검토                      |

### Tier 2 막힘 카테고리화 (선택, Tier 2 응답 시에만)

| Q4 키워드                                                   | 카테고리                | priority                             |
| ----------------------------------------------------------- | ----------------------- | ------------------------------------ |
| "데이터 사라짐", "로그인 안 됨", "실거래 발생", "돈 사라짐" | **P0**                  | 그 fix 1 sprint 우선 (gate (d) FAIL) |
| "막혔다", "버튼 안 됨", "화면 깨졌다", "느리다 (5초+)"      | **P1**                  | 다음 sprint active BL 추가           |
| "혼란스러웠다", "직관적이지 않다", "예상과 달랐다"          | **P2**                  | polish iter 큐                       |
| "X 기능 있으면 좋겠다" (Q5)                                 | feature request (P2/P3) | BL 등재 후 deferred                  |

---

## 인터뷰 진행 timeline (사용자 manual)

| 시점                    | 작업                                               |
| ----------------------- | -------------------------------------------------- |
| **2026-05-16 오전**     | Tier 1 template 복붙 + N=2-3 명에게 발송           |
| Tier 1 응답 1-2 시간    | 받는 대로 `sprint42-feedback.md` 옮겨 적기         |
| Tier 1 응답 받은 친구만 | Tier 2 follow-up 발송 (선택)                       |
| 응답 수집 완료 (24-48h) | 본인 self-assess Day 7 row 채움                    |
| 4-AND gate 적용         | NPS 평균 + Q2 빈도 + Q3 의지 종합 (Tier 2 = bonus) |
| Sprint 60 분기 결정     | 매트릭스 따라 (a)/(b)/(c)/(d) 중 선택              |
| 메인 세션 진입          | "Sprint 60 (X) 분기 진행해줘"                      |

---

## 응답률 향상 팁

- **Tier 1 1차 메시지에 "30초"** 명시 = 부담 인식 축소
- **Tier 1 객관식만** = 답하기 쉬움 (자유 텍스트 없음)
- **Tier 2 = 선택** 명시 = "패스해도 돼" 강조
- **카톡 발송 시점**: 평일 오후 (점심~저녁) > 주말 > 평일 출근시간
- **친한 친구 ★★★★★** 우선 발송. 알 만한 사람은 Tier 1 만이라도 답해줌

---

## 외부 사용자 privacy

- Friend 답변 안 개인정보 (이름 / 카톡 ID) 는 본 repo 에 기록 X
- 이니셜 또는 별칭 사용 (예: "Friend 1: K", "Friend 2: A")
- repo 가 public 되더라도 외부 사용자 신원 불추적

---

## 관련 cross-link

- [`docs/dogfood/sprint42-feedback.md`](../dogfood/sprint42-feedback.md) — 결과 기록 위치
- [`docs/guides/demo-onboarding.md`](demo-onboarding.md) — 첫 가입 5분 시나리오 가이드
- [`docs/REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) — Sprint 60 진입 후 신규 BL 등재
- [`docs/dev-log/2026-05-13-sprint59-close.md`](../dev-log/2026-05-13-sprint59-close.md) — Sprint 59 결과 + Sprint 60 prereq 명시
