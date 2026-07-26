# Curious(잠재 고객) Report — QuantBridge Multi-Agent QA 2026-05-13

## Persona

도구 도입 검토 의사결정자. 사전 지식 0. 30분 내 가입 / 유료 전환 결정.
도구: Playwright MCP 만 (UI 기반).
환경: FE http://localhost:3100, BE :8100, Clerk 인증.

## Executive Summary

- **TTFV (Time To First Value): 약 6분 15초** — 가입 후 첫 백테스트 결과 도달까지. 첫 시도에서 60초 폴링 후에도 "대기 중" 상태 유지, 별도 navigation 으로 우회해야 결과 확인 가능.
- **5초 룰: PASS** — 헤드라인 "Pine Script 전략을 자동 트레이딩으로" 즉시 이해 가능
- **30초 룰: PASS** — 핵심 기능 6개 + 사용 흐름 4단계 + Pine Script 코드 예제 노출
- **60초 룰: PASS (단, false trust 동반)** — CTA 3곳 명확, 그러나 잠재 고객을 속이는 marketing claim 포함
- **가입 마찰: 6/10** — Apple/Google OAuth 가능, 그러나 SSO 후 외부 Clerk 도메인 이동 / 한·영 라벨 혼재
- **신뢰 신호: 2/10** — 가짜 수치 + Beta 자가 명시 + 미검증 법무 + sprint 번호 / BL ID 잠재 고객 노출
- **도입 결정: NO** — "내 회사 명의로 $49/월 결제" 의지 형성되지 않음. NPS = 2/10
- **추천 의사: NO** — 동료에게 "한번 봐봐" 절대 안 함

## 시나리오 결과

### 1. 첫인상 (5초 / 30초 / 60초)

루트 `/` 접근 → 잘 디자인된 landing 페이지로 떨어짐 (Hero, Features, How it works, 통계, Pricing, FAQ 6 section). 5/30/60초 모두 PASS — UI 자체는 매우 잘 만들어짐.

그러나 **숫자 신뢰성 즉시 의심**:

- "10,000+ 트레이더 · 156+ 거래소 · 99.97% 가동률"
- 동시에 "Beta 임시본" + "법무 임시 — H2 말 정식 변호사 교체 예정" 자가 명시
- 같은 페이지에 "100+ 거래소" (Hero 통계) vs "156+ 거래소" (sign-in side) 숫자 모순
- "$2.4B+ 총 거래량" — beta 단계 모순

**잠재 고객 결정**: "겉은 그럴듯한데 숫자가 거짓이거나 자사 데이터가 아닌 게 명백 → 첫 신뢰 -3"

### 2. 가입 마찰

- Hero CTA "무료로 시작하기" 클릭 → `/sign-up` 이 아닌 **`/sign-in`** 으로 이동 (의도 mismatch, BL-260)
- `/sign-in` 에 "Sign up" 링크가 외부 도메인 `stunning-chipmunk-35.accounts.dev/sign-up` 으로 — 피싱 의심 (BL-261)
- `/sign-up` 직접 접근하면 Clerk 가입 폼 정상 작동 (Apple/Google OAuth + email/pwd + first/last name optional)
- **언어 일관성 실패**: 사이드 패널 한국어 / Clerk 폼 영어 ("Create your account / Enter your password / Forgot password? / Use another method")
- 사이드 testimonial: "회원가입 5분이면 첫 백테스트 결과를 본다 — 박민하 Beta 사용자" — beta 자가 명시와 "10,000+ 트레이더" 동시 노출 = self-contradiction

**Time To Sign-Up (잠재 고객 가정)**: 폼 입력 ≈ 1~2분, OAuth 시 30초.

### 3. TTFV (Time To First Value)

- 로그인 후 `/` 빈 화면 5초+ "Rendering..." 상태 — Next.js Dev Tools spinner 만 보임 (BL-262). 5초 더 기다린 후에도 동일. **여기서 잠재 고객 절반은 새 탭 닫을 가능성.**
- `/strategies` 직접 접근하면 보임. 즉 "post-signin 자동 redirect 가 dashboard 가 아닌 빈 `/`" 가 첫 큰 마찰.
- 대시보드 클릭 시 nav 에 "곧 출시" 라벨로 비활성 — 결국 가입자에게 보여줄 dashboard 가 부재 (landing page 의 화려한 "포트폴리오 개요 차트" 약속이 깨짐, BL-263)
- 첫 백테스트 결과 도달: 가입 직후 → 전략 작성 wizard (3단계, 약 1분) → `/strategies/{id}/edit?tab=webhook` (왜 webhook 부터? — 백테스트 우선 아닌가) → 백테스트 form (약 30초) → submit → **"대기 중. 30초 간격 폴링" 안내 + 60초 후에도 동일 status** (BL-264).
- 별도 `/backtests?status=completed` navigate 해 보면 결과 row 가 있어 우회로 결과 화면 도달. 약 **6분 15초**.

**잠재 고객 시각**: "약속 = 0.5초 vs 실제 = 90초+ 폴링 = 신뢰 실추."

### 4. 핵심 가치 검증

성공한 부분:

- Pine Script 직접 입력 → Monaco editor + 실시간 파싱 → "감지된 전략 정보 / 감지된 함수 6개 / 진입 1 · 청산 1 / 실행 가능" 즉시 표시 = **매우 인상적 (Wow moment 1)**
- 백테스트 결과: 총 수익률 -2.53% / Sharpe -1.13 / Max DD -4.13% / Profit Factor 0.70 / 승률 32.98% + 자본 곡선 + Buy-and-Hold 비교 + Drawdown chart + 5탭 (개요/성과/거래분석/거래목록/스트레스테스트) = **풀 백테스트 도구 수준** (Wow moment 2)

실패한 부분:

- "Pine Script 파일 업로드" / "TradingView URL 가져오기" 탭 비활성 + 라벨 "곧 지원: .pine 파일 업로드 / TradingView URL — Sprint 7d+" — **"Sprint 7d" 가 뭔지 모르는 잠재 고객에게 내부 용어 노출** (BL-265)
- 백테스트 form 의 "전략" combobox 값이 사용자 작성 이름이 아닌 **UUID literal `d8e3844e-8e2a-4608-83c3-5f41491020f6`** 노출 (BL-266)
- "vectorbt 벡터화 엔진 사용" — 내부 lib 이름 노출. ADR-011 에서 pine_v2 로 강등된 carryover string
- "이어서 작성하시겠어요?" dialog 가 이미 paste 한 코드 위에 강제 노출 — 타이밍 충돌 (BL-267)
- Webhook URL 에 **`http://localhost:8100/api/v1/webhooks/...`** 노출 — production URL 가 아닌 dev URL (BL-268). 잠재 고객: "이게 진짜 동작하는 서비스인가?"

### 5. 도입 결정 요인

가격:

- Landing `#pricing` anchor 만 작동, **`/pricing` 직접 접근 시 404** (BL-269)
- Starter: 무료 / Pro: $49 월 / Enterprise: 문의 — 명확
- 그러나 Pro 와 Enterprise 모두 **"출시 예정"** 마킹 — 핵심 유료 플랜 결제 불가. 잠재 고객 시각: "유료 전환 옵션 없음 = 평가만 가능 = $$ 의사결정 보류"

보안 신호:

- 자물쇠 (HTTPS): localhost 환경이라 N/A
- SOC2 / GDPR / 보안 인증 배지: 없음
- API Key 암호화 설명: FAQ 일부에 있을 가능성 (FAQ 항목 미펼침). 보안 마케팅 weak.
- **Disclaimer 본문에 "[법무 임시 — 법적 효력 제한적]"** 자가 표기 — **잠재 고객의 가장 큰 deal-breaker**

거래소 연동:

- bybit DEMO 1개 연결됨 (사전 데이터) → 잠재 고객 시각: "Bybit 외 거래소는?" — landing 약속 "Binance/Bybit/OKX/Upbit/Bithumb/Coinbase 100+ 거래소" 대비 실제 보이는 건 bybit 1개

기관/팀 사용:

- Enterprise "출시 예정" — 기관 customer 도입 불가

Export:

- 백테스트 결과 화면에 "공유" 버튼만, CSV/JSON/PDF export 없음 (확인 가능 범위 내)

### 6. 도입 결정 (최종)

**결정: NO (Maybe → No)**

이유 (긍정 3):

1. Pine Script 실시간 파싱 + "감지된 함수" 시각화는 진짜 가치 — 다른 도구에서 본 적 없는 UX
2. 백테스트 결과 5탭 (개요/성과/거래분석/거래목록/스트레스테스트) 깊이가 풀 사이즈 도구 수준
3. landing 디자인 자체는 매우 잘 만들어졌고 한국어 번역도 자연스러움

우려 (부정 3):

1. **가짜 신뢰 수치** (10,000+ 트레이더 / $2.4B / 99.97% 가동률 / 7,234명 실전 매매 / "김지훈/박민하" 가짜 testimonial) — 한 번 잡히면 어떤 marketing claim 도 못 믿음
2. **자가 명시한 Beta + 미검증 법무** — Disclaimer 본문에 "법적 효력 제한적" — 회사 명의 결제 절대 불가
3. **핵심 약속 (TTFV) 깨짐** — landing "백테스트 3분이면 끝" / 폼 "0.5초 예상" vs 실제 90초+ 폴링 + post-signin 화면 stuck

가장 인상적인 1건: **Pine Script 실시간 파싱 결과 사이드 패널** — "감지된 전략 정보 / 함수 6개 / 진입·청산 신호 / 실행 가능" 즉시 표시. Wow.

가장 실망스러운 1건: **Optimizer 페이지 제목이 "Optimizer (Sprint 56)"** 이고 본문에 "BL-233 self-impl GA / ADR-013 §6" 내부 ID 노출 + "최근 실행 목록 로드 실패: [...]" 백엔드 500 JSON 그대로 표시 — production product 가 아닌 internal tool 인상.

## 결함 / 마찰 상세

### BL-260 — Hero CTA "무료로 시작하기" 가 /sign-in 으로 이동 (intent mismatch)

- Severity: High
- Confidence: H
- 막힘 시점 (분): 1
- 재현: landing `/` → Hero 의 "무료로 시작하기" 버튼 클릭 → `/sign-in` 도착 (`/sign-up` 기대)
- 영향: 잠재 고객 가입 의도가 로그인 폼으로 redirect → "이미 계정 있나?" 혼동 → 5~10% 이탈
- 추천 fix: hero CTA 의 href 를 `/sign-up` 으로 교정

### BL-261 — Sign-up 링크가 외부 도메인 `stunning-chipmunk-35.accounts.dev` 로 이동

- Severity: Critical (신뢰)
- Confidence: H
- 막힘 시점 (분): 2
- 재현: `/sign-in` → "Don't have an account? Sign up" 링크 클릭 → 외부 Clerk dev domain 으로 이동, 페이지 제목 "My account | quant-bridge"
- 영향: 피싱 의심 → 잠재 고객 절반은 즉시 탭 닫음. Production 환경에서 Clerk custom domain 미설정.
- 추천 fix: Clerk dashboard 에서 accounts.quantbridge.io custom domain 설정 + 또는 sign-up flow 를 `/sign-up` 내부 라우트로 통일

### BL-262 — 로그인 후 root `/` 무한 "Rendering..." (post-signin 화면 stuck)

- Severity: Critical
- Confidence: H
- 막힘 시점 (분): 3
- 재현: 로그인 완료 → Clerk redirect → http://localhost:3100/ → 5초+ 빈 화면, Next.js Dev Tools "Rendering..." spinner. 별도 navigate 강제.
- 영향: 가입 직후 첫 UX 가 빈 화면 → "고장난 서비스" 인상 → 다수 이탈
- 추천 fix: middleware 에서 authenticated user 의 `/` 접근을 `/strategies` 또는 `/dashboard` 로 즉시 redirect

### BL-263 — Dashboard 비활성 ("곧 출시") — landing page 가짜 약속

- Severity: High
- Confidence: H
- 막힘 시점 (분): 4
- 재현: landing 의 hero visual 와 "실시간 트레이딩 대시보드" section 에서 사용자에게 dashboard 약속 / 가입 후 sidebar 의 "대시보드" 항목 비활성, 클릭 불가
- 영향: 약속 깨짐 → 핵심 가치 (한 화면 모니터링) 부재
- 추천 fix: dashboard MVP (포지션 + 봇 + 체결 list) 출시 또는 landing 의 dashboard 약속 제거

### BL-264 — 백테스트 실행 후 60초+ "대기 중" — 약속 (0.5초 / 3분) 깨짐

- Severity: Critical
- Confidence: H
- 막힘 시점 (분): 5
- 재현: 백테스트 form submit → /backtests/{id} 화면 → "대기 중. 30초 간격 폴링" → 60초 후에도 동일 status → 다른 라우트로 우회 시 결과 row 발견됨
- 영향: 핵심 TTFV 실패. 잠재 고객 절반은 90초 안에 포기.
- 추천 fix: 1) Celery worker pool ≥1 항시 유지 2) polling interval 30s → 5s 단축 3) "예상 N초" 카운트다운 progress bar 4) WS push 로 polling 제거

### BL-265 — 잠재 고객에게 내부 sprint / BL ID 노출 ("Sprint 7d+", "Sprint 56", "BL-233", "ADR-013 §6")

- Severity: High (신뢰)
- Confidence: H
- 막힘 시점 (분): 5, 6
- 재현: /strategies/new step1 "곧 지원: .pine 파일 업로드 ... Sprint 7d+" 라벨 / /optimizer 페이지 제목 "Optimizer (Sprint 56)" / 본문 "BL-233 self-impl GA, ADR-013 §6"
- 영향: 잠재 고객 시각 "이건 internal dev tool 인데 왜 production 처럼 광고하지?" → 신뢰 -3
- 추천 fix: 모든 사용자 노출 UI 에서 sprint / BL / ADR id 일괄 제거. 정책 = "잠재 고객이 모르는 internal artifact 는 sidebar 안쪽 dev-only 도구"

### BL-266 — 백테스트 form "전략" combobox 값이 사용자 이름 대신 UUID

- Severity: Medium
- Confidence: H
- 막힘 시점 (분): 5
- 재현: /strategies/new 로 만든 전략 "Curious Test MA Cross" 의 백테스트 form `/backtests/new?strategy_id=...` → 전략 combobox 표기 = `d8e3844e-8e2a-4608-83c3-5f41491020f6`
- 영향: 사용자가 만든 이름을 못 알아봄 → "내가 만든 게 맞나?" 혼동
- 추천 fix: combobox 값 = strategy.name, 옆 작은 monospace 로 UUID 표시 (또는 hover tooltip)

### BL-267 — 코드 입력 단계에서 "이어서 작성하시겠어요?" dialog 가 사용자 paste 직후 강제 노출

- Severity: Low
- Confidence: H
- 막힘 시점 (분): 4
- 재현: /strategies/new step 1 → "다음 단계" → step 2 코드 입력 시 paste 직후 dialog "2026. 5. 14. 오전 4:46:34에 작성 중이던 초안이 있습니다. 새로 시작 / 이어서 작성"
- 영향: 사용자가 갓 paste 한 새 코드와 이전 초안이 충돌. 모드 결정 forced.
- 추천 fix: dialog 노출 timing = code editor mount 직후 (paste 전). 또는 사용자 입력 0 글자일 때만 노출

### BL-268 — Webhook URL 에 localhost:8100 평문 노출

- Severity: High (신뢰)
- Confidence: H
- 막힘 시점 (분): 5
- 재현: /strategies/{id}/edit?tab=webhook → Webhook URL 카드 → `http://localhost:8100/api/v1/webhooks/...` literal 표시
- 영향: 잠재 고객 시각: "production URL 이 localhost? 이건 dev preview 인가 진짜 서비스인가?" → 도입 불가
- 추천 fix: 환경 변수 NEXT_PUBLIC_API_BASE_URL → production https://api.quantbridge.io. dev 환경에선 명시적 "Dev Environment" 배지

### BL-269 — /pricing 직접 접근 시 404

- Severity: Medium
- Confidence: H
- 막힘 시점 (분): 8
- 재현: http://localhost:3100/pricing → 404 페이지
- 영향: landing 의 `#pricing` anchor 는 작동하지만, 외부 링크 (SEO / 공유 / 직접 입력) 모두 404. SEO 영향.
- 추천 fix: `/pricing` 을 landing 의 pricing section 으로 redirect 또는 standalone pricing page 생성

### BL-270 — 가짜 marketing 수치 (10,000+ 트레이더 / 156 거래소 / 99.97% / 7,234명 / $2.4B)

- Severity: Critical (신뢰 / 윤리)
- Confidence: H
- 막힘 시점 (분): 1
- 재현: landing `/` Hero, sign-in side panel, sign-up side panel, "플랫폼 통계" section 등
- 영향: Beta 자가 명시와 명백히 모순. 한 번 잡히면 모든 marketing claim 의심 → 도입 영구 차단. 윤리 / 광고법 리스크 (한국 표시광고법).
- 추천 fix: Beta 기간 동안 모든 수치 제거 또는 "Beta — 10명 미만 dogfooder" 정직 표시. 정식 출시 후 실측 data 만 노출. 가짜 testimonial ("김지훈/박민하") 즉시 제거.

### BL-271 — 가짜 testimonial ("김지훈 — Pro 트레이더", "박민하 — Beta 사용자")

- Severity: Critical (윤리)
- Confidence: H
- 막힘 시점 (분): 1
- 재현: /sign-in side panel "backtest에서 최적화까지 3분이면 끝난다 — 김지훈 Pro 트레이더" / /sign-up side "회원가입 5분이면 첫 백테스트 결과를 본다 — 박민하 Beta 사용자"
- 영향: 가짜 user voice = 한국 표시광고법 위반 + 잠재 고객 신뢰 영구 destruction
- 추천 fix: 즉시 제거. 실제 dogfooder 인터뷰 quote 으로 교체 (Day 7 dogfood 2026-05-16 결과 활용)

### BL-272 — 한·영 라벨 혼재 (Clerk 폼 영어 + 마케팅 한국어)

- Severity: Medium
- Confidence: H
- 막힘 시점 (분): 2
- 재현: /sign-in side 한국어 / Clerk 폼 "Sign in to quant-bridge / Welcome back / Email address / Password / Continue / Forgot password? / Use another method / Don't have an account? / Sign up / Edit"
- 영향: 한국어 marketing 으로 한국 시장 타깃 vs 핵심 인증 폼 영어 → 비전공자 user 마찰
- 추천 fix: Clerk localization 적용 (`localization={{locale: 'ko-KR'}}`)

### BL-273 — Disclaimer / Terms / Privacy "법무 임시 — 법적 효력 제한적" 자가 명시

- Severity: Critical (도입 결정)
- Confidence: H
- 막힘 시점 (분): 9
- 재현: /disclaimer 본문 "[법무 임시 — 법적 효력 제한적] 본 문서는 H2 Beta 단계의 임시 템플릿입니다"
- 영향: 회사 명의 결제 불가. 법적 보호 없는 도구 → 기관 / 팀 도입 영구 차단. H2 말 (2026-06-30) 정식 변호사 검토본까지 기다려야 함.
- 추천 fix: 임시본이라도 "법적 효력 제한적" 자가 명시 제거. 변호사 검토 한 줄짜리 immediate validation 만이라도 받기. 또는 paid tier 만 launch 미루기.

### BL-274 — 보안 헤더 0개 (CSP / HSTS / X-Frame-Options 등)

- Severity: High (CSO)
- Confidence: M (잠재 고객 직접 보지 못함, 그러나 보안 인증 부재 = 우회 신호)
- 막힘 시점 (분): N/A (background)
- 재현: response headers 모두 null
- 영향: clickjacking / XSS / MITM 위험. 기관 도입 시 보안 audit 필수 통과 불가.
- 추천 fix: Next.js `middleware.ts` 에 CSP + HSTS + X-Frame-Options DENY + Referrer-Policy 추가

### BL-275 — Optimizer 페이지 백엔드 500 (목록 로드 실패) JSON 그대로 노출

- Severity: High
- Confidence: H
- 막힘 시점 (분): 7
- 재현: /optimizer → 본문 "최근 실행 목록 로드 실패: [{ "expect... "
- 영향: 사용자에게 raw JSON error 노출 = unprofessional + debug info leak
- 추천 fix: error.tsx fallback + 사용자 친화 메시지 ("일시적 오류, 새로고침 또는 잠시 후 시도")

## 평가 점수 표

| 차원                 | 점수     | 비고                                                                            |
| -------------------- | -------- | ------------------------------------------------------------------------------- |
| TTFV (시간/분)       | 6분 15초 | 첫 시도 폴링 실패 후 우회 navigate 로 도달                                      |
| 5초 룰 (P/F)         | P        | 헤드라인 즉시 이해                                                              |
| 30초 룰 (P/F)        | P        | 핵심 가치 + 흐름 노출                                                           |
| 60초 룰 (P/F)        | P        | CTA 3곳 명확, 단 false trust 동반                                               |
| 가입 마찰 (1-10)     | 6        | OAuth O, 그러나 외부 도메인 + 영한 혼재 + redirect 빈 화면                      |
| 신뢰 신호 (1-10)     | 2        | 가짜 수치 + 가짜 testimonial + 미검증 법무                                      |
| 디자인 전문성 (1-10) | 8        | landing 자체는 매우 잘 만들어짐                                                 |
| 디자인 신뢰감 (1-10) | 3        | 디자인은 신뢰감 있으나 내용은 (sprint id 노출 / localhost URL / Beta 자가 명시) |
| 디자인 모던함 (1-10) | 8        | 2026 표준 부합 (gradient, glassmorphism, hero visual)                           |
| 가격 명확성 (1-10)   | 4        | Starter free / Pro $49 명시, 그러나 두 유료 모두 "출시 예정" + /pricing 404     |
| 도입 결정            | **NO**   | 본인 명의 무료 시도는 가능 / 회사 명의 결제 / 추천 모두 불가                    |

## 강점 (Top 3)

1. **Pine Script 실시간 파싱 UX** — paste 직후 "감지된 전략 정보 + 함수 6개 + 진입·청산 신호 + 실행 가능" 즉시 표시. 다른 도구에서 보기 어려운 wow moment.
2. **백테스트 결과 깊이** — 5탭 구조 (개요/성과 지표/거래 분석/거래 목록/스트레스 테스트) + 자본 곡선 + Buy-and-Hold 비교 + Drawdown — full-size 도구 수준.
3. **landing page design 자체** — 한국어 번역 자연스러움 + Hero / Features 6 / How it works 4 / Pricing 3 / FAQ 6 구조 + Pine Script code preview = 첫인상 디자인 점수 8/10.

## 우려 (Top 3)

1. **가짜 marketing 수치 + 가짜 testimonial (BL-270 / BL-271)** — beta 자가 명시와 명백히 모순. 윤리 / 한국 표시광고법 위반. 한 번 잡히면 모든 claim 의심 → 도입 영구 차단.
2. **자가 명시한 미검증 법무 (BL-273)** — Disclaimer 본문 "법적 효력 제한적" 자가 명시 = 회사 명의 결제 / 기관 도입 영구 차단. H2 말까지 대기.
3. **TTFV 약속 깨짐 (BL-264 + BL-262)** — Hero 약속 "3분", form 약속 "0.5초" vs 실제 60초+ 폴링 + post-signin 빈 화면 5초+ → 잠재 고객 절반 90초 안에 포기.

## 가장 인상적인 1건

**Pine Script paste → 실시간 파싱 결과 사이드 패널** — "감지된 전략 정보 / 함수 6개 / 진입·청산 신호 / 실행 가능" 즉시 표시. landing 에서 약속한 "TradingView 전략을 자동으로 분석하고 Python으로 변환" 의 실제 deliverable. 이거 하나만으로 잠재 고객은 "오, 진짜 동작한다" 신뢰 +5. 만약 이 외의 모든 결함을 다 고치면 도입 결정 yes 가 될 정도.

## 가장 실망스러운 1건

**Optimizer 페이지 제목 "Optimizer (Sprint 56)" + 본문 "BL-233 self-impl GA / ADR-013 §6" + "최근 실행 목록 로드 실패: [JSON error]"** — 잠재 고객 한 명이 이 페이지를 5초 보면 "internal dev tool 인데 왜 public marketing 처럼 광고하지?" 결론 즉시 도달. 도입 결정 NO 의 결정타.
