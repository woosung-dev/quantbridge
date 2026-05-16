# Curious (잠재 고객) — Sprint 60 → 61 Multi-Agent QA

**일자**: 2026-05-17 (Day 8 of dogfood)
**환경**: Isolated mode (FE :3100 / BE :8100)
**페르소나**: Curious — 도구 도입 검토 의사결정자, 사전 지식 0 (Pine Script 만 안다는 수준)
**깊이**: Exhaustive (실측 ~50분)
**경쟁사 비교**: skip (QuantBridge 단독 평가)

---

## 첫인상 평가 (5초 / 30초 / 1분 룰)

| 차원         | 점수 (1-10) | 코멘트                                                                                                                                                                                                                                                                                                                                                                 |
| ------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5초 룰       | 8           | Hero "Pine Script 전략을 자동 트레이딩으로" 메시지 즉시 파악. Pine Script 안다는 가정 하 ★★★★. 단 Pine Script 모르는 일반 트레이더는 hero copy 만으로는 무엇인지 추정 어려움 (1줄 sub-copy 가 부족 보완)                                                                                                                                                               |
| 30초 룰      | 8           | "백테스트 → 최적화 → 스트레스 테스트 → 데모/라이브 매매" 4단계 가치 흐름 hero + "어떻게 작동하나요" 섹션에서 명확. 핵심 기능 6종 카드 + 4단계 플로우 + 한눈에 보는 플랫폼 4영역 카드 = 진입 매끄럽다                                                                                                                                                                   |
| 1분 룰       | 7           | "Beta 단계 + Bybit Demo Trading 환경에서 위험 없이" 메시지 = 정직함. 시작 의도 있음. 단 "Asia-Pacific only" 배너 (US/EU 제한) + Disclaimer/Terms/Privacy 황색 alert = "본격 운영 아직 X" 인상 누적. **결정 보류 행동 유발**                                                                                                                                            |
| Trust signal | 7           | (a) **가짜 testimonial 없음** — Sprint 60 BL-270/271/273 회귀 0 PASS. **JKMHYSDWSJ 라는 익명 영문 4-7자 placeholder 만 노출** — 진짜 dogfooder 닉네임으로 추정되나 신뢰성 ★★ 인상. (b) Logo wall 없음 (Binance/Bybit/OKX 등 거래소 logo 만). (c) Press / 보안 인증 (SOC 2 Type II "준비 중" 명시). (d) "심플한 요금제 - 인기 Pro $49/월" 명확 — Beta 단계 가격 노출 OK |
| Hero copy    | 8           | "Pine Script 전략을 자동 트레이딩으로" + sub copy 명확. CTA "무료로 시작하기 / 라이브 데모" 2종 well-formed. v2.0 출시 배지 = 모멘텀 신호                                                                                                                                                                                                                              |

**스크린샷**: `curious-01-landing-desktop.png` (1440x900), `curious-02-landing-mobile.png` (375x812)

---

## 가입 마찰 (1-10): 5.0

**마찰 분해**:

- ★★★★ OAuth 2종 (Apple + Google) — 마찰 낮음
- ★★★ Field: First name (optional) + Last name (optional) + Email + Password — 4 fields, 2 optional. OAuth path 면 1-click
- ★ **언어 불일치**: 한국어 사이트인데 Clerk form 만 영어 ("Create your account / Sign in with Apple / Already have an account?"). 한국어 사용자 인상 ★★ (BL-318)
- ★ **외부 dev 도메인 leak**: 로그인 클릭 → `stunning-chipmunk-35.accounts.dev` 임시 도메인 redirect. 잠재 고객 view 에서 **신뢰성 치명타**. 결제 의사 절반 떨어진다 (BL-319)
- ★ **"Development mode" 주황 배지** Clerk form 하단 노출. Sprint 60 P0 fix 누락 가능성 (BL-265 회귀?) (BL-320)
- ★ 페이지 제목 "Sign in to **quant-bridge**" — 브랜드 inconsistency (QuantBridge vs quant-bridge slug) (BL-321)

**Clerk dev instance 4 종 이슈 = 가입 직전 신뢰 손실 클러스터.** 가입 자체는 30초 완료지만 "이 회사 진짜 운영 중인가?" 의문 → 결정 보류.

**스크린샷**: `curious-04-signup.png`, `curious-05-signin.png`

---

## TTFV: 추정 ~3-5분 (조건부)

**측정 한계**: 본 페르소나는 기존 계정 (Curious Test MA Cross 전략 3개 이미 존재) 으로 진입 → 진짜 신규 사용자 TTFV 측정 불가.

**추론**:

- 로그인 → `/strategies` 자동 redirect (단 `/dashboard` 진입 의도 무시. 신규 사용자가 "어디서 시작" 혼란)
- "새 전략" CTA 명확 (우상단 파란 버튼) → 3-step wizard "업로드 방식 → 코드 입력 → 확인" **★★★★ UX**
- 단 **파일 업로드 + TradingView URL 가져오기 가 disabled** ("곧 지원 / 준비 중"). Hero 카피 "TradingView 전략을 업로드하면" 과 **불일치** = 신규 사용자 1차 좌절 (BL-322)
- Pine Script 직접 입력 (텍스트 paste) 만 가능. 코드 paste → 파싱 → 백테스트 form → 24-metric 결과 까지 추정 5분.

**기존 백테스트 결과 화면 인상** (curious-09-backtest-detail.png):

- 5 KPI 카드: 총 수익률 -2.53% / Sharpe -1.13 / Max DD -4.13% / Profit Factor 0.70 / 승률 32.98% · 94 trades
- TradingView Lightweight charts equity curve + Buy & Hold 비교 + Drawdown 영역 = **professional**
- 탭 5종 (개요 / 성과 지표 / 거래 분석 / 거래 목록 / 스트레스 테스트)
- 스트레스 테스트 4 sub-탭 (Monte Carlo / Walk-Forward / Cost Assumption Sensitivity / Param Stability) = 차별점
- **TTFV 결과 화면 신뢰도 ★★★★★** — 음수 수익률 솔직 노출 = "진짜 백테스트 엔진" 인상

**스크린샷**: `curious-06-dashboard.png` (=strategies), `curious-07-new-strategy.png`, `curious-09-backtest-detail.png`, `curious-10-stress.png`

---

## 핵심 가치 검증

- **Hero feature 1 (Pine Script 파싱)**: PARTIAL — 직접 입력만 가능, 파일/URL "곧 지원". Hero 카피 vs 실제 기능 GAP. 단 직접 입력 path 는 정상 작동 (Curious Test MA Cross 카드 "파싱 성공" 표시)
- **Hero feature 2 (벡터화 백테스트)**: PASS — 24-metric 결과 화면 강력. TradingView charts 통합. -2.53% 음수 결과 솔직
- **Hero feature 3 (스트레스 테스트)**: PASS (UI 노출만 확인) — Monte Carlo + Walk-Forward + Cost Assumption + Param Stability 4종 노출 (실 실행은 미실시)
- **Hero feature 4 (파라미터 최적화 Grid/Bayesian/Genetic)**: 미검증 — 사이드바 메뉴 없음 (`/optimizer` 추정). 잠재 고객 view 에서는 메뉴 부재 = "기능 진짜 있나?" 의문 (BL-323)
- **Hero feature 5 (데모 트레이딩)**: 미검증 — 사이드바 "트레이딩" 메뉴 존재
- **Hero feature 6 (라이브 트레이딩 Bybit Demo)**: PARTIAL — "Beta: Bybit Demo" 정직하게 명시

**페르소나 view 결론**:

- "이거 진짜 돈 벌게 해줄까?" → **★★★ (Maybe).** 백테스트 엔진 자체는 신뢰 가나, Live trading Bybit Demo 단일 = 결제 의사결정 보류
- "TradingView 대신 이걸 쓸 이유" → **있다.** Pine Script 자동 백테스트 + 24-metric + 스트레스 테스트 = TradingView 백테스터 기능 ★★ 부족 영역 보완

---

## 디자인 인상

- **전문성**: 8 / 10 — Inter 폰트 + 파란 primary + 그리드 카드 일관성 + TradingView 차트 통합. 모던 SaaS landing 평균 이상. AI slop 없음
- **신뢰성**: 6 / 10 — 가짜 testimonial 0 + 정직한 Beta 안내 ★★★★ BUT Clerk dev 도메인 leak + Development mode 배지 + 한영 혼용 (Cost Assumption Sensitivity) + 익명 placeholder ("JKMHYSDWSJ") = 신뢰 -2점
- **모던**: 7 / 10 — 2026 트렌드 (bento grid 카드 4×4) 일부 적용 + 황색 Disclaimer alert + 파란 primary 단조. minimalist editorial 까지는 X. glassmorphism / asymmetric / micro-motion 없음 = 평균 SaaS 수준

---

## 도입 결정 (Yes / No / Maybe)

**결론**: **Maybe** (조건부 Yes)

**이유**:

- **Yes 신호** (3):
  - 24-metric 백테스트 결과 화면 + TradingView charts 통합 = professional engine 인상
  - 4종 스트레스 테스트 (Monte Carlo / Walk-Forward / Cost Assumption / Param Stability) = TradingView 대비 차별점
  - 가짜 testimonial / marketing 숫자 0 = 정직한 Beta (Sprint 60 fix 회귀 0)
- **No 신호** (4):
  - **Clerk dev 도메인 leak** (`accounts.dev` redirect) → 신뢰성 -3점. 본 issue 만으로 결제 의사 50% 손실
  - **Development mode 배지** Clerk form 하단 노출
  - **Hero copy vs 실제 기능 GAP** — TradingView URL / .pine 파일 업로드 "준비 중", 직접 입력만 가능
  - **사이드바 Optimizer 메뉴 부재** — Hero 에서 광고한 Grid/Bayesian/Genetic 3종 어디서 쓰나
- **Maybe 신호** (2):
  - Live trading Bybit Demo 단일 = 본격 자본 투입 의사결정 보류
  - 모바일 햄버거 드롭다운 시트 크기 좁음 (full-screen sheet X) = 모바일 UX 평균

**친구 추천도**: ★★★ (5점 만점) — "Beta 인 거 알고 가입해봐. 백테스트 엔진은 좋아 보이지만 실제 자본 투입은 아직" 식 추천

---

## 신규 BL (BL-317 ~)

### BL-317 [Medium] [H] 익명 placeholder "JKMHYSDWSJ" hero 옆 dogfooder 카드 노출

**증거**: `curious-01-landing-desktop.png` — Hero 우측 "Bybit Demo 연동" 카드 위 영문 7자 무작위 닉네임 ("JKMHYSDWSJ"). 진짜 dogfooder 이니셜로 추정.
**페르소나 영향**: 신뢰성 ★★ 인상. "왜 진짜 이름이 아니라 알파벳 무작위?" 의문.
**제안**: (a) 진짜 닉네임 ("@quant_jang" 식) (b) avatar circle 만 + 익명 라벨 ("dogfooder 14인") (c) 제거 후 Logo wall (거래소 logo) 대체.

### BL-318 [Medium] [H] Clerk sign-up/sign-in form 한영 혼용 (한국어 사이트, 영어 form)

**증거**: `curious-04-signup.png` "Create your account / Welcome! Please fill in the details to get started. / Sign in with Apple / Sign in with Google / First name (optional) / Continue / Already have an account? Sign in"
**페르소나 영향**: 한국어 본 사이트 → 영어 form. 마찰 ★ + 신뢰성 -1.
**제안**: Clerk `localization` prop 으로 ko 적용 (`@clerk/localizations`).

### BL-319 [High] [H] Clerk dev 도메인 leak — `stunning-chipmunk-35.accounts.dev` 임시 도메인 redirect (Sign-in path)

**증거**: `curious-05-signin.png` URL bar `https://stunning-chipmunk-35.accounts.dev/sign-in`. "Sign in" 링크 클릭 시 외부 임시 도메인으로 전체 redirect.
**페르소나 영향**: **잠재 고객 view 신뢰성 -3점. 결제 의사결정 50% 손실.** "이 회사 진짜 운영 중인가?" 의문 직접 발생. dev instance 가 production env 에 사용 중 = Sprint 60 P0 누락.
**제안**: Clerk production instance 발급 + `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` production key 교체 + custom domain (`auth.quantbridge.io` 식) 설정. 자체 도메인 sign-in form 호스팅 (Clerk Hosted Pages 사용 시).

### BL-320 [High] [M] Clerk "Development mode" 주황 배지 노출 — Sign-up + Sign-in 양쪽

**증거**: `curious-04-signup.png`, `curious-05-signin.png` 하단 "Secured by clerk" 아래 주황색 "Development mode" 텍스트.
**페르소나 영향**: 결제 의사결정 시 "dev 환경에서 돈 받는 회사" 인상. Sprint 60 BL-265 (★★★ 내부 상태 노출) 회귀 가능성.
**제안**: BL-319 와 통합 — production Clerk instance 교체 시 자동 제거.

### BL-321 [Low] [H] Clerk page title 브랜드 inconsistency — "Sign in to quant-bridge"

**증거**: `curious-05-signin.png` "Sign in to **quant-bridge**" (slug 형식, 본 사이트 브랜드 "QuantBridge")
**페르소나 영향**: 브랜드 -1점. dev 환경 인상 누적.
**제안**: Clerk dashboard application name "QuantBridge" 로 갱신.

### BL-322 [Medium] [H] Hero 카피 vs 실제 기능 GAP — "TradingView 전략을 업로드하면" but 직접 입력만 가능

**증거**: Hero copy "TradingView 전략을 업로드하면 백테스트, 최적화, 스트레스 테스트를 거쳐...". 실제 `/strategies/new` 페이지에서는 "Pine Script 직접 입력" 만 enable, "파일 업로드 / TV URL 가져오기" disabled "곧 지원 / 준비 중" 표시 (`curious-07-new-strategy.png`).
**페르소나 영향**: 신규 사용자 1차 좌절. Hero 약속 vs 실제 기능 불일치 = 신뢰성 -2점.
**제안**: (a) Hero copy 수정 ("TradingView Pine Script를 복사·붙여넣기 하면..." 식) (b) 실제 .pine 파일 업로드 / TV URL 가져오기 구현 우선순위 상향 (BL 등재). H1 Track 후보.

### BL-323 [Medium] [M] Hero "파라미터 최적화 (Grid·Bayesian·Genetic)" 광고 vs 사이드바 Optimizer 메뉴 부재

**증거**: Hero feature 카드 4번 "Grid·Bayesian·Genetic 알고리즘으로 최적의 파라미터를 자동 탐색". 사이드바 메뉴: 대시보드 / 전략 / 템플릿 / 백테스트 / 트레이딩 / 거래소 (6 메뉴) — **Optimizer 없음** (`curious-06-dashboard.png`, `curious-08-backtests.png`).
**페르소나 영향**: "광고한 기능 어디서 쓰나" 의문. 사이드바 link 부재 = 기능 발견성 ★ (BL Optimizer access path).
**제안**: 사이드바 "최적화" 메뉴 추가 + `/optimizer` 페이지 active. 또는 백테스트 상세 페이지 내부 "최적화 실행" 버튼 추가 (전략→백테스트→최적화 흐름).

### BL-324 [Low] [M] 모바일 햄버거 메뉴 = 작은 dropdown, full-screen sheet 아님

**증거**: `curious-03-mobile-hamburger.png` — 메뉴 클릭 시 우상단 좁은 dropdown 패널 (~200x250px) 펼침. 모바일 표준 패턴 = full-screen sheet 또는 left/right slide drawer.
**페르소나 영향**: 모바일 UX 평균 이하. 터치 영역 좁음 + 6개 항목 빽빽함.
**제안**: shadcn/ui `Sheet` 또는 `Drawer` 컴포넌트로 교체. left/right slide 또는 bottom sheet pattern.

### BL-325 [Low] [H] 인증 후 landing 페이지 진입 불가 — pricing 보려면 로그아웃 필요

**증거**: 로그인 상태 `http://localhost:3100/#pricing` 또는 `/` 진입 시 자동 `/strategies` redirect. Pricing 정보 보려면 로그아웃 필요.
**페르소나 영향**: 신규 사용자가 가입 후 "Pro $49/월 vs Starter 무료" 비교 어려움. 마찰 ★.
**제안**: (a) 로그인 후에도 `/` 접근 시 redirect 하지 않음 (b) 사이드바 또는 user menu 에 "요금제" link 추가 (c) `/pricing` 전용 페이지 추출.

### BL-326 [Low] [M] 한영 혼용 — "Cost Assumption Sensitivity" 영어 그대로 (한국어 사이트)

**증거**: `curious-10-stress.png` 스트레스 테스트 4 sub-탭 중 "Cost Assumption Sensitivity 실행" 만 영어. 나머지 3종 "Monte Carlo 실행 / Walk-Forward 실행 / Param Stability 실행" 도 동일 패턴.
**페르소나 영향**: 한영 혼용 마찰 ★. 한국어 사용자에게 "비용 가정 민감도" 식 한국어 라벨 적합.
**제안**: 일관된 한국어 라벨 정책 — "Monte Carlo (몬테카를로) / Walk-Forward (워크-포워드) / Cost Assumption Sensitivity (비용 민감도) / Param Stability (파라미터 안정성)" 식 한영 병기.

---

## Summary

- **Composite Curious 점수**: **6.5 / 10** (도입 결정도 가중)
  - 첫인상 7.5 / 가입 마찰 5.0 / TTFV ★★★★ (조건부) / 핵심 가치 7.5 / 디자인 7.0 / 결정 ★★★
- **TTFV**: 추정 ~3-5분 (페르소나 한계로 정확 측정 불가)
- **결정**: **Maybe** (조건부 Yes — Clerk production instance 교체 + Hero copy 수정 + Optimizer 메뉴 추가 시 ★★★★)
- **핵심 차별점**:
  - 24-metric 백테스트 + TradingView charts 통합 (TradingView 백테스터 대비 ★★)
  - 4종 스트레스 테스트 (Monte Carlo / Walk-Forward / Cost Assumption / Param Stability) — TradingView 부재 영역
  - 가짜 marketing 0 + 정직한 Beta 안내 (Sprint 60 fix 회귀 0 PASS)
- **마찰 1순위**: **Clerk dev 도메인 leak (BL-319)** + **Development mode 배지 (BL-320)** = 가입 직전 신뢰 손실 클러스터. 본 issue 만으로 결제 의사 50% 손실.
- **마찰 2순위**: Hero copy vs 실제 기능 GAP (BL-322) — TradingView URL / 파일 업로드 "준비 중", 직접 입력만
- **마찰 3순위**: Optimizer 메뉴 부재 (BL-323) — Hero 광고 vs 발견성 GAP

**Sprint 60 회귀 검증**: BL-270 (가짜 testimonial) / BL-271 (가짜 marketing 숫자) / BL-273 (가짜 disclaimer) / BL-285 (모바일 햄버거 dead) / BL-300 (UserButton 0x0) / BL-305 (모바일 navigation) **모두 회귀 0 PASS**. 단 BL-265 (★★★ 내부 상태 노출) 인접 영역 = Clerk "Development mode" 배지 회귀 가능성 (BL-320).

**Sprint 61 권고 (Curious 페르소나 입장)**:

- **P0 / High**: BL-319 (Clerk production instance) + BL-320 (Development mode 배지) — 결제 의사 회복 conditional
- **P1 / Medium**: BL-322 (Hero copy GAP) + BL-323 (Optimizer 메뉴) + BL-317 (익명 placeholder) + BL-318 (Clerk form 한국어)
- **P2 / Low**: BL-321 (브랜드 inconsistency) + BL-324 (모바일 sheet) + BL-325 (pricing 접근) + BL-326 (한영 혼용)

**총 신규 BL**: 10건 (High 2 / Medium 4 / Low 4)
