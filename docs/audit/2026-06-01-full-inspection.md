# QuantBridge 전체 심층 검사 — 2026-06-01

> **범위:** 전체 코드 검토(FE Vercel React 베스트프랙티스 전수 + BE FastAPI 최신 스펙 context7 대조) · 전체 화면/기능 검토(Playwright MCP 라이브 구동 + ui-ux-pro-max) · 로드맵 잔여 구현가능 기능 정리.
> **베이스라인:** `main` 분기 작업 브랜치 `stage/inspection-2026-06-01` / BE 1852 테스트·FE 723 테스트 green / ruff·mypy(183 파일)·tsc·eslint clean.
> **직전 감사:** [`2026-05-30-full-inspection.md`](2026-05-30-full-inspection.md) (148 발견, 이틀 전). 본 패스 = **신규 독립 재검사 + 교차참조** — 해소 항목 제외, #311~319 수정 라이브 재검증.

---

## 0. Executive Summary

| 차원                | 방법                                                                                                            | 결과                                         |
| ------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **코드 검토**       | 13 슬라이스 병렬 에이전트(FE 7 vercel + BE 6 context7) + P0/P1 적대적 검증 (18 에이전트 / 1.86M 토큰)           | **P0:0 / P1:2 / P2:30 / P3:67** (rejected 1) |
| **화면/UI·UX**      | Playwright MCP ~32 스크린샷(데스크톱+모바일+언인증) → ui-ux-pro-max 99룰 5 화면군 분석 (5 에이전트 / 341k 토큰) | **P0:0 / P1:8 / P2:19 / P3:21**              |
| **기능 end-to-end** | 라이브 구동 — 전략 생성→파싱→백테스트→거래목록→메트릭 + #311~319 재검증                                         | **핵심 파이프라인 전부 작동 ✅**             |

**판정:** **P0 = 0 (즉시 손실/크래시 없음).** 머니패스·백테스트·인터프리터·인증 등 핵심 기능은 라이브에서 정상 작동하며, 직전 #311~319 P1 수정도 라이브 재검증 통과. 신규 발견은 **방어공백/하드닝/컨벤션** 위주이며, 가장 시급한 신규 P1 2건은 모두 **이미 검증된 #319 zodResolver 버그 클래스의 미적용 잔여**(optimizer 폼 + live-session 폼)다.

**헤드라인 신규 P1:**

1. **optimizer 3폼(grid/bayesian/genetic) plain zodResolver** → zod v4 검증 실패 시 unhandled ZodError throw, 필드 에러 무표시 (실측 재현). #319 hotfix 가 register-dialog 만 고침.
2. **live-session-form 동일 버그** → 본 세션에서 **이미 수정 적용**(zodV4Resolver 교체, FormMessage 구조라 안전).

---

## 1. 방법 & 환경

- **스택 구동:** 격리 포트(5433)가 타 프로젝트(`ffwpu-postgres`) 점유 → **base 스택(:3000/:8000)으로 inline env override 부팅**(`.env.local` DATABASE_URL 이 5433 기본값이라 5432 override). Docker fresh 볼륨(`down -v`) → migrate 26개 적용 → uvicorn(:8000) + Next(:3000) + Celery 워커(docker). 워커 이미지 `--build` 로 최신화.
- **인증:** Clerk dev(`@clerk/testing` storageState) — Playwright MCP 브라우저 영속 세션으로 authed 라우트 직접 구동.
- **OHLCV:** `OHLCV_PROVIDER=timescale` + CCXTProvider 가 백테스트 시 Bybit 에서 BTC/USDT 1h **자동 패치** → 라이브 백테스트 실제 실행 성공.
- **코드 검토 기준:** `/vercel-react-best-practices`(70룰) · `context7` FastAPI 0.135.3/Starlette 1.0.0/Pydantic 2.13.0/SQLAlchemy 2.0.49/Celery 5.6.3 최신 문서 대조.
- **화면 검토 기준:** `ui-ux-pro-max`(99룰: 접근성/터치/성능/스타일/레이아웃/타이포/애니/폼/네비/차트).
- **증거:** `qa-2026-06-01/` (스크린샷 ~34장). 원본 findings JSON = 세션 워크플로 출력(아래 부록).

---

## 2. Severity 집계 + 2026-05-30 대비

|                   | P0    | P1     | P2     | P3     | 합계    |
| ----------------- | ----- | ------ | ------ | ------ | ------- |
| 코드 검토         | 0     | 2      | 30     | 67     | 99      |
| UI/UX             | 0     | 8      | 19     | 21     | 48      |
| **합계**          | **0** | **10** | **49** | **88** | **147** |
| (2026-05-30 참고) | 0     | 14     | 58     | 76     | 148     |

> 발견 수는 유사하나 **성격이 다름** — 2026-05-30 은 머니패스/메트릭 정확성 P1 위주(이후 #311~319 로 해소), 본 패스는 **해소 후 잔여 + 신규 영역**(zodResolver 미적용 잔여, 코드 컨벤션, UI 일관성/접근성). P0 0건은 양 패스 공통.

---

## 3. P1 발견 (상세)

### 코드 P1

#### [P1-A] optimizer 3폼 plain zodResolver → 검증 silent 실패 + console 오염

- **파일:** `frontend/src/app/(dashboard)/optimizer/_components/{grid,bayesian,genetic}-search-form.tsx`
- **근거(실측 재현):** 세 폼 모두 `zodResolver(FormSchema)` 사용. 설치본 `@hookform/resolvers@3.10.0`(dist 가 `Array.isArray(e?.errors)` 검사) + `zod@4.3.6`(ZodError 는 `.issues` 만, `.errors` undefined) → 분기 실패 → `throw`. var_name 누락 / min>max / budget 초과(genetic superRefine) 제출 시 필드 에러 0 + unhandled console ZodError + submit silent no-op. **#319 hotfix(zodV4Resolver)가 register-dialog 에 대해 고친 것과 정확히 동일 버그 클래스, optimizer 폼엔 미적용.**
- **권고:** `zodV4Resolver` 로 교체 + 세 폼은 raw `<input>` 구조라 **필드별 에러 표시 UI 동반 필요**(`formState.errors.parameters?.[idx]?.max?.message`). resolver 교체만으로 console 오염은 즉시 차단.
- **상태:** **BL 등재(safe_fix 아님 — 에러 UI 동반 필요). 본 세션 미적용.** → `BL-365`

#### [P1-B] live-session-form 동일 zodResolver 버그 → **본 세션 수정 적용 ✅**

- **파일:** `frontend/src/features/live-sessions/components/live-session-form.tsx`
- **근거:** 동일 메커니즘. strategy/account Select 미선택(`z.uuid()` 실패) 또는 symbol 빈값/33자 제출 시 무피드백 + console ZodError. 이 폼은 **이미 shadcn Form/FormMessage 구조**라 resolver 교체만으로 정상 표시.
- **조치:** `zodResolver` → `zodV4Resolver(LiveSessionFormSchema)` 교체 (import 포함). **적용 완료, tsc/lint/test 회귀 0.**

### UI/UX P1 (실제 prod 영향)

| ID          | 화면            | 발견                                                                                                                      | 권고                                         | 상태                |
| ----------- | --------------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------------- |
| **F-01**    | optimizer       | 페이지 제목 영어 **"Optimizer"** vs 사이드바 "최적화" (나머지 3화면은 일치)                                               | "최적화"로 통일                              | **본 세션 수정 ✅** |
| **LAND-02** | landing         | "실시간 모니터링"·"백테스트 성과 비교"에 구체 수익률(+12.4% 등) **"예시" 미표기** — 바로 아래 목업은 "(샘플 데이터)" 표기 | 동일 "예시 데이터" 라벨 추가                 | BL → `BL-366`       |
| **LAND-03** | landing         | 푸터 면책·"(준비 중)" 링크 **대비 2.34:1** (WCAG AA 미달) — 투자자문 면책이 비가독                                        | `--text-muted`→어두운 토큰, 비활성 색-비의존 | BL → `BL-367`       |
| **LGL-01**  | privacy/terms   | 법무 본문 회색 텍스트 저대비(<4.5:1 추정)                                                                                 | 본문 gray-700+ 상향                          | BL → `BL-367`(묶음) |
| **M-01**    | privacy(모바일) | 개인정보 페이지가 **모바일 리플로우 안됨** — 데스크톱 밀도로 축소되어 본문 판독 불가                                      | 모바일 컨테이너(max-w+px-4)+반응형 타이포    | BL → `BL-368`       |

**dev-only(prod 무관, 교차참조):** `LAND-01`·`M-03`(좌하단 "N" = Next.js dev indicator + 우하단 야자수 = TanStack Query devtools) → **프로덕션 빌드에서 자동 제거**. 신규 결함 아님.
**기존 이연(production deploy 자동해소):** `LAND-04`(Clerk "Development mode" + 소문자 "quant-bridge") = **BL-320/321/352** 영역(이미 deferred, deploy 시점 해소).

---

## 4. P2 발견 (하드닝 — 그룹)

### Backend (FastAPI/async/보안)

- **be-ratelimit-1** ★: `rate_limit_key` 가 `request.state.user_id` 를 읽지만 인증 dependency 가 이를 세팅 안 함 → **user 기반 rate-limit 영구 비활성(IP fallback only)**. (`common/rate_limit.py:78`)
- **be-mw-1/2/3:** 500 unhandled 응답에 CORS·보안헤더 누락(미들웨어 순서) / CORS `allow_credentials=True`+`["*"]` 과대허용 / rate-limit `swallow_errors` fail-open(Redis 장애 시 무제한 통과).
- **be-asyncdb-1** ★: OHLCV `get_range` 무제한 `.scalars().all()` + 백테스트 기간 상한 부재 → 메모리/DoS. (`market_data/repository.py` + `backtest/schemas.py`)
- **be-routing-1:** trading `list_orders`/`list_kill_switch_events` 가 `response_model` 없이 raw dict + Router 가 Repository 직접 접근(레이어 위반).
- **be-routing-7:** `register_exchange_account` 응답 직전 평문 API key 복호화(마스킹용) — 평문이 직렬화 경로에 일시 노출.
- **be-stream-2:** webhook `Content-Length` 무방어 `int()` 캐스팅 → 조작 헤더로 500.
- **be-clerk-1:** Clerk `authenticate_request` sync blocking I/O 를 async dependency 에서 직접 호출 → 이벤트 루프 차단. **be-clerk-2:** JWT `aud` 미검증(azp 만).
- **be-celery-1:** Redis broker + acks_late + long-running ws_stream 인데 `visibility_timeout` 미설정 → 1h 재배달 churn.
- **be-asyncdb-2:** 워커 per-call 엔진 NullPool/pool_pre_ping 미설정. **be-pydantic-1:** optimizer `json_encoders`(deprecated). **be-pydantic-6:** `position_size_pct` float (Decimal-first 규칙 경계).

### Frontend (성능/구조)

- **fe-approuter-1/2/3:** page.tsx 5개 `'use client'`(leaf 분리 규칙 위반) / loading.tsx 1개뿐(streaming 미활용) / optimizer·trading·admin·onboarding error.tsx 부재.
- **fe-strategy-1:** `editor-view.tsx` set-state-in-effect ESLint disable 불필요(render-time 파생 가능, H-1 규칙 위반). **fe-strategy-2:** `?tab=` 무검증 `as TabKey` 캐스팅 → invalid 탭 빈 화면.
- **fe-strategy-8:** optimizer genetic/grid 폼 필드 에러 미표시(P1-A 와 연결). **fe-resolver-1:** zodV4Resolver flat key 매핑 → nested 필드 에러 위험.
- **fe-perf-1:** optimizer SVG 차트 `hsl(var(--primary))` 색상 깨짐(프로젝트 변수는 hex). **fe-perf-2/3 + fe-components-1/2:** recharts/lightweight-charts 정적 barrel import(next/dynamic 미적용) + TradingChart 매 렌더 새 literal prop → data effect 재실행.

### UI/UX

- **F-04** optimizer 상단 헤더바 비어 페이지명 누락 / **F-03** optimizer 빈 상태 저품질(카드/CTA 없음) / **F-06** 스탯카드 "0" 글리프 굵은 외곽선 깨짐 / **F-07** 사이드바 비활성 메뉴 대비 부족.
- **F-01~03(backtests_new)** 필수 필드 required 인디케이터 전무 / 라벨 한·영 혼용 / 헬퍼 저대비.
- **M-04** Beta 배너 링크 터치타깃·간격 부족(모바일) / **M-05** 필터 칩 우측 잘림 / **M-06** stage 라벨 세로 깨짐.
- **ADM-01** admin 403 권한안내는 안전(양호)하나 검색·필터 컨트롤 비활성 안내 없이 활성 잔존. **LAND-05/07** 인증·pricing 페이지 글로벌 헤더/홈 링크 부재.

> P3 88건(코드 67 + UI/UX 21)은 컨벤션/폴리시 — 전체 목록은 부록 워크플로 출력 참조. 대표: zod v3 import 경로 1건(trading/schemas.ts, **본 세션 수정 ✅**), non-null 단언 다수, 한국어 콜론 종결, geo-banner 영어(US/EU 대상자용 의도적).

---

## 5. rejected (적대적 검증 차단 — false positive)

- **be-stream-1**(P1→reject): "webhook Idempotency-Key 를 쿼리스트링으로 파싱 → 멱등성 무력화" 주장. **반증:** TradingView alert 는 커스텀 HTTP 헤더 불가(URL+body 만) → query 채널이 TV 가 쓸 수 있는 **유일** 채널이고 FE 테스트주문도 query 로 일관 전송 → 멱등성 end-to-end 실작동. 영향 정반대. 잔여는 OpenAPI 문서 "header" 표기와의 **명명 drift(P3)** 뿐.

---

## 6. 기능 end-to-end 검증 (라이브)

| 기능                       | 검증                                             | 결과                                                             |
| -------------------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| Pine 파싱(pine_v2)         | SMA Cross 전략 입력 → 실시간 파싱                | ✅ "변환 완료 / Pine v5 / 진입·청산 1 / 6함수 / 실행가능"        |
| 전략 CRUD                  | POST /strategies 201 → edit 리다이렉트           | ✅ 정상, 웹훅 시크릿 1회성 표시+rotation                         |
| 백테스트 파이프라인        | BTC/USDT 1h 6개월 → Celery → pine_v2 → 24 metric | ✅ 완료, OHLCV CCXT 자동패치, 85 실거래                          |
| **P1-5 avg_holding(#311)** | 성과지표 평균 보유 시간                          | ✅ **"1.0일"(24h 24m)** — 이전 288배 과대계산 해소 확인          |
| 거래목록                   | 85건(21승/63패/25%) + CSV + 페이지네이션         | ✅ 정상                                                          |
| 트레이딩 대시보드          | 스탯카드/킬스위치/계정등록 다이얼로그            | ✅ 렌더·상호작용 정상                                            |
| 전 라우트 console          | ~24 라우트 desktop+mobile sweep                  | ✅ 0 에러(admin 403 = 비관리자 정상 / Clerk dev 경고 = dev only) |
| 모바일 가로 오버플로       | 10 라우트 @390px                                 | ✅ **전부 0px**(과거 BL-339/340 해소 확인)                       |

**#311~319 재검증 종합:** P1-5(avg_holding) 라이브 통과. 나머지 P1 수정(P1-10/13 Trust Layer / P1-7 WF config / P1-9 categorical / P1-2/12/14 머니패스 / #319 passphrase)은 코드리뷰 슬라이스가 코드 레벨 정상 확인 + 회귀 테스트 green. #319 자체는 register-dialog 에 정상 적용 확인(단 형제 폼 미적용 = P1-A/B 신규 발견).

---

## 7. 2026-05-30 감사 교차참조

- **해소 확인(리포트 제외):** P1-5 avg_holding(라이브), 머니패스 P1 묶음(#315), Pine Trust Layer(#312), 모바일 깨짐(BL-339/340, 오버플로 0 확인).
- **기존 이연 재확인:** Clerk Development mode/앱명(BL-320/321/352), custom domain(BL-261), server header(BL-347) = production deploy 시점 자동해소.
- **dev-only 오탐 식별:** Next.js dev indicator + TanStack devtools = 프로덕션 무관.
- **신규(2026-05-30 미포착):** P1-A/B zodResolver 형제 폼 잔여, be-ratelimit-1(user rate-limit 비활성), be-asyncdb-1(OHLCV 무제한), F-01 optimizer 영어제목, M-01 privacy 모바일.

---

## 8. 이번 세션 적용 안전수정 (브랜치 `stage/inspection-2026-06-01`)

| 파일                                             | 변경                                         | 근거                                                    |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------- |
| `optimizer/page.tsx`                             | h1 `"Optimizer"` → `"최적화"`                | F-01, 언어정책(UI=한국어)                               |
| `live-sessions/components/live-session-form.tsx` | `zodResolver` → `zodV4Resolver`(import 포함) | **P1-B**, #319 검증 패턴 동일, FormMessage 구조라 안전  |
| `features/trading/schemas.ts`                    | `from "zod"` → `from "zod/v4"`               | P3, nextjs-shared.md §2 규칙(z.uuid() v4 API 이미 사용) |

**회귀 0:** FE tsc·eslint clean + vitest **723 passed**(베이스라인 동일).
**보류(BL 등재):** optimizer 3폼(에러 UI 동반 필요), 대비 토큰(전역 영향+design-system 테스트), 가짜수익률 라벨(마케팅 카피 판단), privacy 모바일(레이아웃 조사), maintenance 콜론·geo-banner(공유 컴포넌트/의도적).

---

## 9. Decision Log

| ID    | 결정                                            | 근거                                                                                           |
| ----- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| DEC-1 | 격리(5433) 대신 base(5432) inline override 부팅 | ffwpu-postgres 점유, 타 프로젝트 비중단                                                        |
| DEC-2 | DB 볼륨 fresh(`down -v`)                        | 비번 불일치(stale 볼륨) 결정적 차단, 검사용 throwaway                                          |
| DEC-3 | 안전수정 3건만 적용, 나머지 BL                  | 사용자 "안전한 것만" 정책 + 토큰/카피/레이아웃은 deliberate 결정 영역                          |
| DEC-4 | optimizer "≤50 eval" 카피 변경 보류             | `_MAX_BAYESIAN_EVALUATIONS=50` 실제값 — finding 이 PICKER_LIMIT(100) 혼동 추정, 추측 수정 금지 |
| DEC-5 | geo-banner 영어 유지                            | US/EU 비대상자 안내 = 의도적 영어                                                              |
| DEC-6 | be-stream-1(idempotency) reject                 | TV 헤더 불가 → query 가 유일 채널, 영향 정반대                                                 |
| DEC-7 | #319 라이브 재검증은 코드리뷰로 대체            | custom combobox 구동 비용 과다, 코드 레벨 확정 + Phase C QA 스크린샷 기존 존재                 |

---

## 10. 로드맵 잔여 — 구현 가능 기능 (Phase G)

> 사용자 요청대로 **외부 의존(도메인/배포/이메일/mainnet 키) 제외, 코드로 구현 가능한 기능만** 한정. 기존 백로그(BL-364 까지) + 본 검사 신규(BL-365~368).

### Tier 0 — 즉시(반나절, 신규 발견 高가치)

- **BL-365 (P1)** optimizer 3폼 zodV4Resolver 교체 + 필드 에러 UI — _P1-A, 본 검사 헤드라인. live-session(P1-B)은 본 세션 해소._
- **BL-366 (P1)** landing "실시간 모니터링/성과비교" 섹션 "예시 데이터" 라벨 — _컴플라이언스._
- **BL-367 (P1)** 푸터·법무 본문 대비 4.5:1 상향(디자인 토큰) — _WCAG/면책 가독._

### Tier 1 — 단기(1~2일, 기존 active P1)

- **BL-022** golden expectations 재생성 (pine_v2 strategy.exit 지원 완료)
- **BL-026** mutation fixture 회귀 활성화
- **BL-309** trading dispatch(registry/webhook/fees) test 0→80%
- **BL-368 (P1)** privacy 모바일 리플로우 수정
- **BL-308** trading websocket test 4→70%

### Tier 2 — 중기(기존 active P2 + 본 검사 하드닝)

- **BL-186** 풀 레버리지+펀딩+청산 모델 / **BL-235** N-dim viz / **BL-236** objective_metric whitelist
- 본 검사 P2: be-ratelimit-1(user rate-limit 활성화) · be-asyncdb-1(OHLCV 기간 상한) · be-mw(CORS/500 헤더/fail-open) · fe-approuter(loading.tsx/error.tsx 보강) · fe-perf(차트 next/dynamic) · F-04/F-06(optimizer 헤더/스탯카드 글리프)

### Tier 3 — 트리거 도래 시(기존 active P1, 의존 충족 후)

- **BL-014** partial fill / **BL-015** OKX WS(Bybit Demo 1주 안정 후) / **BL-023** KIND-B/C mutation / **BL-024** real_broker E2E(creds 준비 후) / **BL-025** parallel-sprints patch

### Tier 4 — 폴리시(P3)

- **BL-195** form-slide 애니 / **BL-190** PDF export / **BL-362/363/364** observability/boilerplate/string-category / **BL-306/307** CLAUDE.md lint / 본 검사 P3 88건(non-null 단언, 한국어 콜론, 한·영 혼용 등)

### ❌ 제외 — 외부 의존/사용자 결정(구현 가능 범위 밖)

- **G1** TimescaleDB Cloud SQL 미지원(DB 호스팅 재결정) · **G7/G8** healthz/Celery 배포 토폴로지
- **BL-070** 도메인+DNS / **BL-071** prod 배포 / **BL-072** Resend 이메일 / **BL-073~075** 캠페인·인터뷰·H2 / **BL-003** Bybit mainnet
- production deploy 자동해소: **BL-320/321/352/347/261**(Clerk dev mode·앱명·server header·custom domain)

---

## 11. 부록 — 증거

- **스크린샷:** `qa-2026-06-01/` (데스크톱 16 + 모바일 10 + 언인증 6 + 동적 4: strategy-edit / backtest-detail / backtest-trades)
- **원본 findings JSON(세션 워크플로):**
  - 코드 검토: `qb-code-review-2026-06-01` (sliceSummaries + confirmed 99 + rejected 1)
  - UI/UX: `qb-uiux-analysis-2026-06-01` (groupSummaries + findings 48)
- **베이스라인:** BE 1852 / FE 723 green @ `stage/inspection-2026-06-01` 분기 시점.
