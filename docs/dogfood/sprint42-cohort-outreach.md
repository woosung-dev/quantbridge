<!-- Sprint 42 Phase 2 dogfood — 1-2명 micro-cohort 카톡 DM 발송 raw 텍스트 + 인터뷰 5+5 질문 골격. 사용자 copy-paste 가능 형태. -->

# Sprint 42 Dogfood Phase 2 — Cohort Outreach + 인터뷰 골격

> **위치:** `docs/dogfood/` Track 2 — 본인 + 1-2명 micro-cohort 발송·인터뷰 raw text.
> **작성일:** 2026-05-09 (Sprint 47 kickoff)
> **상위:** [`sprint42-feedback.md`](sprint42-feedback.md) (live 누적 기록), [`../dev-log/2026-05-08-sprint42-day7-midcheck.md`](../dev-log/2026-05-08-sprint42-day7-midcheck.md), [`../dev-log/2026-05-08-sprint42-master.md`](../dev-log/2026-05-08-sprint42-master.md)
> **발송 prereq:** Sprint 41~46 visual fidelity 16+ 페이지 prototype-grade 통과 ✅, 본인 5분 시나리오 OK ✅, share token + 본인 backtest sample 1-2건 (사용자 manual)

---

## 발송 prereq 체크리스트 (사용자 manual)

발송 _전_ 모두 확인:

- [ ] 본인 backtest 샘플 1-2건 실행 + share token 발급 (Pine Script v5 BTC/USDT 1년)
- [ ] share link 클립보드 복사 가능 + og:image 정상 (Sprint 32 Surface Trust 검증된 영역)
- [ ] Bybit Demo Trading 가입 link 정상 (`https://www.bybit.com/en/help-center/article/Demo-Trading`)
- [ ] QuantBridge 가입 페이지 (Clerk) → 거래소 계정 등록 → DEMO 모드 배지 정상
- [ ] 인터뷰 일정 카톡 약속 (Day 0 / Day 7 / Day 14 — 3 시점)

---

## 카톡 DM 발송 메시지 (raw text, 사용자 copy-paste 가능)

### 메시지 1 — 첫 발송 (Day 0)

```
형/누나/[이름] 안녕하세요!

지난 [n]개월 만들고 있던 퀀트 자동매매 플랫폼 QuantBridge,
이제 1-2명 가까운 분들께 먼저 보여드릴 단계가 됐어요.

한 줄로:
"파인스크립트, 그대로 — 진짜 수수료까지 똑같이."

→ TradingView 의 Pine Script 전략을 *바꾸지 않고* QuantBridge 에 paste
→ 진짜 수수료/슬리피지 포함 백테스트 (TV 가 못 함)
→ Bybit *데모* 거래 자동 실행 (실자본 X, 가짜 USDT)
→ 24 metric + 가정박스 + share link 까지

부담 없이 1-2주만 써보고 솔직한 피드백 부탁드려요.
- 가입 link: [QuantBridge URL — Beta 진입 시 도메인 적용]
- 제 backtest 샘플 (먼저 보세요): [share link]
- Bybit Demo 가입: https://www.bybit.com/en/help-center/article/Demo-Trading

쓰면서 막히는 부분 / 이상한 부분 / "이게 뭐지?" 싶은 부분
그냥 카톡으로 막 던져주세요. 문서 정리 안 해도 됩니다.

Day 0 (오늘) / Day 7 / Day 14 — 3번 짧게 통화/카톡 인터뷰 부탁드려요.
각 15분이면 충분합니다.

고맙습니다 🙏
```

### 메시지 2 — Day 7 mid-check 리마인더

```
[이름]님, Sprint 42 dogfood Day 7 됐네요!

10분만 시간 내주실 수 있을까요? 4 질문만 빠르게:

1. 7일 동안 며칠 / 몇 번 사용하셨어요?
2. backtest 결과의 24 metric / 가정박스 — 신뢰가 가나요? 어디가 약한가요?
3. share link 발급/공유 한 번이라도 써보셨나요?
4. 1주 더 쓰실 의향이 있나요? 만약 멈추신다면 결정적인 1가지 이유는?

답장 줄글로 막 써주셔도 OK!
```

### 메시지 3 — Day 14 close-out

```
[이름]님, dogfood 2주 끝나갑니다. 진심으로 감사드립니다 🙏

Day 14 close-out 인터뷰 (15-20분) — 5 질문:

1. NPS — "이 도구를 다른 트레이더에게 추천할 의향" 0~10점 + 이유
2. 14일 사용 중 가장 좋았던 순간 1개 / 가장 이상했던 순간 1개
3. 진짜 수수료 / 1:1 의미론 / Trust Layer — 마케팅 카피로서 공감되는가
4. 만약 paid 라면 월 얼마까지? ($0 / $19 / $29 / $79 / 안 씀)
5. Beta 정식 오픈 시 1순위로 알려드리고 싶은데 OK 인가요?

답변 어떤 형식이든 OK 입니다. 카톡 / 통화 / 직접 만남 모두 가능.
```

---

## 인터뷰 질문 5+5+5 (총 15)

### Day 0 — 첫인상 (15분)

1. 가입 → 첫 backtest 까지 걸린 시간 (5분 시나리오 검증)
2. 가장 어려웠던 단계 1개 + 막힌 시간
3. 첫인상 — "이게 뭐 하는 도구인지" 30초 안에 이해됐나요? 안 됐다면 어디서 막혔나요?
4. 24 metric / 가정박스 — _너무 많다_ vs _적당하다_ vs _부족하다_ ?
5. 한 줄 카피 — "파인스크립트, 그대로 — 진짜 수수료까지 똑같이." 가 정확하다고 느끼는가?

### Day 7 — Mid-check (10분)

1. 7일 동안 사용 빈도 (며칠 / 몇 번)
2. backtest 결과 신뢰도 — 어디가 약한가?
3. 발견한 bug / 이상한 동작 (사진 X 줄글 OK)
4. 1주 더 쓸 의향이 있는가?
5. 1주 동안 _다른 도구_ (TradingView / freqtrade / 3Commas / etc) 쓸 일이 있었나? 있었다면 _왜_ QuantBridge 가 아닌 그 도구를?

### Day 14 — Close-out (15-20분)

1. NPS 0~10 + 이유 (1줄)
2. 가장 좋았던 순간 1개 / 가장 이상했던 순간 1개
3. 마케팅 카피 4 후보 중 어떤 게 가장 정확한가:
   - "Run TradingView Pine on your own infrastructure — 1:1 semantics, real fees, full trust."
   - "백테스트가 거짓말하지 않는 유일한 곳"
   - "파인스크립트, 그대로 — 진짜 수수료까지 똑같이"
   - "Pine to Production — without LLMs, transpilers, or guesswork"
4. paid 의향 + 가격 ($0 / $19 / $29 / $79)
5. Beta 정식 오픈 시 1순위 알림 OK?

---

## raw 저장 위치

- 카톡 raw → `docs/dogfood/sprint42-feedback.md` 의 "외부 cohort feedback" 섹션 (수동 채워 넣음)
- Day 7 정리 → `docs/dev-log/2026-05-08-sprint42-day7-midcheck.md`
- Day 14 정리 → `docs/dev-log/2026-05-08-sprint42-master.md` (Beta trigger 결정)

---

## Day 14 → Beta trigger 결정 알고리즘 (4중 AND gate)

```
모든 조건 충족 시 → Sprint 48~49 = Beta 본격 진입 (BL-070~075)
어느 하나 미달 시 → Sprint 48 = polish iter (회귀 fix) 또는 mainnet 결정 보류

(a) 본인 self-assess ≥ 7/10 (근거 ≥ 3 줄)
(b) BL-178 production BH curve 정상 (회귀 0)
(c) BL-180 hand oracle 8 test all GREEN
(d) Sprint 47 발송 후 신규 P0 = 0 AND unresolved P1 = 0
(e) 1-2명 micro-cohort NPS ≥ 7 / paid 의향 ≥ $19 (신규 추가 — 외부 진실)
```

> Sprint 41 self-assess 8/10 PASS 패턴 + Sprint 46 회귀 0 누적 → (a)(b)(c) 강한 통과 가능성. _(e) 외부 진실_ 만 미지수.

---

## Risk

- 1-2명 = sample size 작음 → NPS 1명 답에 따라 결정 흔들림. mitigation: 카피 / 페인포인트 / paid 의향 _3축 cross-check_
- 카톡 DM = silent ignore 가능 → mitigation: Day 0 발송 후 48h 응답 없으면 1회 nudge, 그 이상 no-pressure
- 첫인상 손상 risk = 발송 prereq 체크리스트 모두 통과 시점에만 발송 (사용자 manual gating)
