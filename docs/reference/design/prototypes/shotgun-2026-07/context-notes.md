<!-- AI-slop 감사 + 3무드 design-shotgun 리디자인 작업의 결정/근거 기록 (2026-07-19 착수) -->

# Redesign Shotgun — Context Notes (2026-07-19)

> 세션이 바뀌어도 이 문서만 읽으면 결정과 근거를 재도출 없이 이어갈 수 있게 유지한다. 계속 append.

## 배경 / 목표

- 사용자 요청: taste-skill(project 설치본 = `design-taste-frontend`)로 **레포 AI-slop 판단** + 멀티에이전트로 전체 구조·UI/UX 리뷰 + **개선 후킹포인트** 도출 + **실제 운영사이트처럼** 디자인.
- 착수 규율: 바로 구현 금지. **프로토타입 먼저** 만들고 그 디자인을 토대로 진행. 디자인 자료조사 필요 시 **인터뷰 우선**.

## 확정 결정 (인터뷰 4Q, 2026-07-19)

1. **대상 화면 = 앱 전체 결속 패스** — 셸(네비/사이드바) + 도메인별 대표 화면을 하나의 언어로.
2. **리디자인 강도 = 대안 2~3안 병렬 비교 (design-shotgun)**.
3. **레퍼런스 무드 = 3무드 전부, 멀티에이전트로** — A 터미널 밀도(Bloomberg/TradingView), B Linear/Vercel 클린, C Stripe/Ramp 핀테크-신뢰.
4. **산출물 형식 = docs/prototypes HTML** (기존 00~11 넘버링 관례 계승, 서브폴더 `shotgun-2026-07/`).

## Design Read (taste-skill §0.B)

데이터 밀집형 프로 퀀트 트레이딩 **프로덕트 UI**(마케팅 사이트 아님, 로컬 데일리드라이버 도구). 이미 'Precision Instrument' 카본/스틸 + 시그널 코퍼 언어 보유. 기존 Tailwind v4 토큰 위에서 보존·샤프닝 + 터미널/프로툴 밀도 지향.

## 범위 한계 (taste-skill §13 — 정직성)

- **마케팅 표면**(`/`, `/pricing`, `/waitlist`, auth, legal, share): 스킬 전체 규칙 적용.
- **프로덕트 UI**(dashboard/backtest/optimizer/trading/orders/strategies/onboarding): **횡단 안티슬롭만**(em-dash, 컬러/셰이프/테마 락, 모션 규율, a11y, 카피). 히어로·섹션반복 등 랜딩 규칙 미적용.

## 시퀀싱

감사(멀티에이전트) → 확정 후킹포인트 보고 → **findings-informed** 3무드 HTML 프로토타입 → 비교 인덱스 → 사용자 픽 → 결속 세트 확장 → (별도 승인) React 이식.

## 비교 단위

- 3무드를 사과-대-사과로 비교하기 위해 **동일 슬라이스를 3벌** 렌더: **앱 셸 + 백테스트 리포트**(`02-backtest-report`, 앱 시그니처 화면).
- 이긴 무드를 결속 세트(대시보드/트레이딩/전략)로 확장.

## 3무드 정의

- **A. 터미널 밀도** — Bloomberg/TradingView. 고밀도, 다크, 1px 헤어라인, mono 숫자, 정보밀도 우선.
- **B. Linear/Vercel 클린** — 여백, 차분, 프리미엄 타입, 밀도↓, 구조/타이포로 승부.
- **C. Stripe/Ramp 핀테크** — 구조적, 데이터 포워드, 신뢰감, 세련된 데이터비즈.

## 베이스라인 사실 (2026-07-19 실측)

- 디자인 SSOT: `frontend/src/styles/globals.css`(토큰), `frontend/src/lib/brand-palette.ts`, `chart-tokens.ts`, `fonts.ts`(Archivo/IBM Plex Mono/Pretendard).
- 셸 컴포넌트: `components/layout/dashboard-{shell,header,sidebar,nav-list}.tsx`, `mobile-nav.tsx`.
- 상태 프리미티브: `empty-state.tsx`, `skeleton.tsx`, `form-error-inline.tsx`. `error.tsx`/`loading.tsx` 다수 존재하나 **optimizer/trading/orders에 error.tsx 부재**.
- 아이콘 = `lucide-react` (taste-skill §3.C는 기본값으로 비권장 — 프로젝트 전역 의존이라 "이미 의존 시 허용"이지만 감사에서 별도 확인).
- 모션 = CSS 키프레임(Motion/GSAP 라이브러리 미사용), 전역 prefers-reduced-motion 리셋 있음.
- 프로토타입 12벌: `00-landing` ~ `11-error-pages`.

## 열린 항목

- [ ] 감사 결과(w4142j5gs) 수신 후 확정 후킹포인트 반영.
- [ ] 결속 세트 확장 범위(어느 화면까지)는 무드 픽 이후 확정.
- [ ] React 이식은 프로토타입 승인 후 별도 사용자 승인.

---

## Phase 5 (2026-07-20) — C 언어 전 화면 확장

### 방식 결정

- **공용 셸 파일화.** `variant-c.html` 에서 토큰·컴포넌트·반응형 CSS + 셸 마크업을 잘라 `_kit.html` 로 만들고, 모든 새 화면은 이걸 복사해서 시작한다. 화면 고유 CSS 는 `PAGE-SPECIFIC` 마커 아래에만 허용.
  근거. 지난 세션에서 B안이 `border-radius` 8종으로 드리프트했다. 빌더가 공용 CSS 를 손대면 무조건 드리프트한다. **바이트 비교로 차단**하는 것이 가장 싸다(preflight C16).
- **자기보고 불신을 도구로 강제.** 빌더 자기보고가 반복적으로 틀렸으므로(반경 "단일"이라며 8종, "순백 0건"이라며 주석에 존재) 판정을 사람 서술이 아니라 명령 출력에 건다.
  - `preflight.py` — 정적 22종. 대시(★HTML 엔티티 포함), 금지색, 팔레트 밖 hex 대비 계산, outline 무력화, nav aria, 벡터화, 가공인물, 폰트 로드, reduced-motion, 반경, 상태 4종, table-wrap, **차트 y축 라벨↔픽셀 공선성**, **공용 CSS 바이트 무결성**, 중복 id.
  - `runtime-check.mjs` — Playwright 실측. 1440/1024/768/375 가로스크롤, **배경 합성 후 실제 렌더 대비**(aria-hidden 제외), **Tab 30회 포커스 링 가시성**, reduced-motion 누수, 콘솔 에러.
  - **베이스라인 보정.** 임계값을 `variant-c.html` 이 PASS 하도록 맞췄다. 검사기가 확정안보다 엄격하면 빌더가 C 를 이탈하게 된다(예: 0.68rem=9.52px 아이브로는 C 의 의도적 선택이므로 tiny 임계는 9.4px).
- **파이프라인 3단.** build -> 독립검증(수정 금지) -> 교정. 검증자는 두 명령을 **자기가 다시 실행**하고 숫자를 **직접 재계산**한다. verdict PASS + blocking 0 이면 교정 에이전트를 띄우지 않는다.
- **2안은 진짜 갈림길에만 5개.** 코크핏(세로 리포트 vs 3-pane 콘솔) · 대시보드(요약 vs 액션 큐) · 백테스트 설정(단일 폼 vs 위저드) · Pine 에디터(좌우 vs 상하) · 옵티마이저 상세(히트맵 우선 vs 리더보드 우선).
- **워크스페이스 캐논.** 화면마다 숫자가 다르면 그 자체가 신뢰 붕괴다. `_KIT.md` §4 에 계정/nav-count/전략 4종/run_2f9c41 성과 전체/세션 sess_8d14 잔고를 고정하고 전 빌더가 공유한다.

### 자기 검사기에서 발견한 자기 버그 (기록 가치 있음)

1. `PAGE-SPECIFIC` 마커가 CSS 주석 안에 있는데, 오탐 방지를 위해 주석을 공백 치환한 뒤 마커를 찾아서 **항상 "마커 없음"** 으로 오판했다. -> 마커 위치는 원본에서 찾고, 주석 blank 가 길이를 보존하므로 인덱스는 그대로 쓴다.
2. `_kit.html` 생성 시 toast div 가 두 번 들어가 **중복 id** 를 유발했다.
3. `<title>` 검사가 kit 헤더 주석 안의 `<title>` 안내 문구를 잡았다. -> 주석 제거본에서 찾는다.
4. 가공 인물 정규식이 "손익비" "이벤트" 같은 일반 한국어를 잡았다. -> 텍스트 노드 전체가 3자 이름이거나 인물 문맥(님/씨/후기/트레이더)일 때만.

교훈. **검사기 자체를 확정안(variant-c)으로 회귀 테스트하지 않으면 검사기의 버그가 빌더의 시간을 태운다.** 새 검사기를 만들면 반드시 known-good 산출물에 먼저 돌린다.

### 실측 조사 — 구 화면의 정직성 문제 (React 이식 시 Track A 와 함께 처리)

**★프로토타입 밖 실제 코드에 살아 있는 것 (즉시 수정 대상)**

- `frontend/src/app/_components/landing-faq.tsx` — "100개 이상의 글로벌 거래소를 지원합니다" 가 배포 코드에 그대로 있다. 실제는 `schemas.ts` 의 `z.enum(["bybit","okx"])`.
- `frontend/src/app/(dashboard)/onboarding/_components/step-4-result.tsx` — `isError` 분기 부재. 결과 조회 실패 시 세 지표가 조용히 `—` 로 남고 "첫 백테스트 완주!" 축하 헤더가 그대로 뜬다. step 2/3 는 에러를 다루는데 4만 없다.
- `optimizer-page-view.tsx` — 드롭다운은 "≤ 50회 평가", 폼 실제 상한은 100. 문구가 낡은 쪽으로 보인다.

**가짜 라이브 상태의 정체 (11-error-pages.html)**

- 500 페이지 하단 `role="status" aria-live="polite"` + 초록 무한 맥동 점 + "시스템 상태: 정상 운영 중". 갱신 로직 0. 500 화면에서 정상이라 주장하는 자기모순. 접근성 라이브 리전 계약까지 위반.
- 503 "약 15분 남음" + 진행률 60%(CSS 하드코딩) + `aria-valuenow="60"` 고정. 카운트다운 스크립트는 `minutes` 를 한 번도 줄이지 않는다. "14:10 시작 · 14:40 완료" 는 15분이 아니라 30분 — 내부 수치끼리도 모순.
- 503 트위터 카드 `@QuantBridge_io · 5분 전`. 언제 열어도 5분 전.
- 500 요청 ID `req_abc123xyz789` 고정값인데 "고객센터에 알려주세요" 안내 + 복사 버튼까지 붙어 신뢰를 강화한다.
- 404 검색 입력에 submit 핸들러 없음, 링크 전부 `href="#"`.

**가짜 소셜 프루프**

- landing `10,000+ 트레이더 · 156+ 거래소 · 99.97% 가동률`, STATS `10,000+ 활성 전략 / 99.97% / $2.4B+ / 4.8`. 같은 `10,000+` 가 히어로에서는 트레이더, STATS 에서는 활성 전략 — 단위조차 안 맞는다.
- login `지금 7,234명이 실전 매매 중입니다` + 맥동 초록 점. 에러 페이지와 **동일한 가짜 라이브 패턴이 최소 3개 파일에 반복**된다.
- `김지훈(KJ)` 이 login 에서는 후기 제공자, onboarding 에서는 로그인한 사용자. 같은 사람이 자기 자신에게 추천사를 쓴 셈.
- 거래소 개수 주장이 한 파일 안에서 156 / 100+ / 100개 이상으로 서로 모순.

**코드베이스에 이미 있는 모범 사례 (설계 원칙으로 승격할 것)**

- `orders-panel.tsx` 청산가 주석 — "체결 주문이 곧 열린 포지션을 뜻하지 않고 positions API 도 없으므로, 과거 주문에 라이브 위험처럼 보이는 청산가를 찍지 않는다(Surface Trust)". **가짜 라이브 금지 원칙이 이미 코드에 명문화돼 있다.**
- `optimizer-oos-evaluation.tsx` — 진짜 walk-forward 설명 + 한계 3가지 명시.
- `waitlist-faq.tsx` — "현재 Bybit (Demo + Mainnet) 와 OKX (Demo) 를 지원합니다. Binance, Bitget 은 H2 로드맵" = 가장 정직한 기존 문구.
- `live-session-form.tsx` — "Bybit Demo 한정 — 가상 자금만 사용. 실제 자금 손실 없음." 범위 한정 리스크 문구.

**반쪽 한글화 정확한 목록**

- `orders-panel.tsx` 헤더 9개 중 7개 영문(Symbol/Side/Qty/State/Price/TP·SL/Broker ID/Error, 청산가만 한글). 셀 값도 원시 `buy`/`filled` 그대로. 같은 앱의 `orders-blotter.tsx` 는 같은 필드를 `매수`/`체결` 로 번역한다.
- `optimizer-run-list.tsx` 헤더 `ID / Status / Objective / Best / Created` 5개 전부 영문.
- 근본 원인. 한국어 매핑 `STATE_META` 가 `_components` 안에 갇혀 재사용 불가. **`features/trading/labels.ts` 공용 레이블 모듈이 필요**하다. `features/onboarding/types.ts` 의 `ONBOARDING_STEP_LABEL` 이 좋은 선례.

**옵티마이저 데이터 모델 (프로토타입 없어 신규 설계의 근거)**

- 실행. `id / backtest_id(완료된 백테스트에 종속) / kind(grid_search|bayesian|genetic) / status(queued|running|completed|failed) / param_space / result|null / error_message|null / created_at / started_at / completed_at`
- 목적 지표는 정확히 3개. `sharpe_ratio | total_return | max_drawdown`, 방향 `maximize | minimize`.
- 상한. 그리드 **최대 9조합**, 베이지안·유전 최대 100회 평가.
- ★**진행률·ETA·현재 회차 필드가 모델에 없다.** running 상태에서 보여줄 게 없다는 뜻이고, 여기서 가짜 진행률 바를 그리고 싶은 충동이 생긴다. 없는 진행률을 만들지 않는 것이 이 화면의 정직성 시험대다.
- 온보딩 실제 스텝은 `환영 → 샘플 전략 → 백테스트 → 결과` (구 프로토타입의 `거래소 연결 → … → 데모 시작` 과 1·4번이 어긋남). TTL 5분 만료 시 1단계로 리셋.

## 2안 픽 확정 (2026-07-20 아침)

| 화면            | 픽              | 오케스트레이터 추천 | 일치 |
| --------------- | --------------- | ------------------- | ---- |
| 트레이딩 코크핏 | A 세로 리포트   | B 3-pane 콘솔       | ✗    |
| 대시보드        | A 성과 요약     | B 액션 큐           | ✗    |
| 백테스트 설정   | A 단일 폼       | A                   | ✓    |
| 전략 편집       | B 상하 분할     | A 좌우 분할         | ✗    |
| 옵티마이저 상세 | B 리더보드 우선 | B                   | ✓    |

**추천 적중 2/5.** 별점은 이 세트에서 신뢰할 신호가 아니었다.

### 중간 가설이 반증된 기록

1~3 이 전부 A안이었을 때 "C 정본과 같은 세로 리포트 구조를 일관되게 선호한다" 는 가설을 세웠고, 4·5 에서 둘 다 B안이 나오며 반증됐다.
**3/5 표본으로 패턴을 선언한 것이 성급했다.**

사후 가설(이것도 5 표본이므로 가설로만 취급).

- 기각된 것 = **주 콘텐츠에서 폭을 빼앗는 배치.** 01b 3-pane / 08a 좌우 분할(코드에서 400px 회수) / 05b 위저드(단계 강제).
- 채택된 것 = **주 콘텐츠에 폭을 주는 배치.** 08b 상하 분할은 코드 전폭, 10b 리더보드는 9행 표를 바로 읽힘.
- 축이 "세로냐 가로냐" 가 아니라 **"그 화면의 주인공에게 폭을 주는가"** 일 수 있다.
- 다음 shotgun 에서 2안 설계 시 **주 콘텐츠 폭** 을 명시적 비교축으로 놓으면 변별력이 오른다.

### 승격 시 발견

채택된 b안을 정본 번호로 rename 한 것은 미관이 아니라 **필수**였다. `screen-06` 의 전략명 링크 12개가 `screen-08-strategy-editor.html` 을 가리키고 있어, 이름을 안 바꿨으면 전부 깨졌다.
rename 후 전 파일 href 스캔으로 깨진 링크 0 을 확인했다.

### 뷰어 버그 2건 (같은 아침)

1. `.pane { display: flex }` 가 UA 기본 `[hidden]{display:none}` 을 이겨 **B 패널이 항상 화면 절반을 빈 채로 점유**. 결과적으로 A 패널이 675px 로 눌려 **모든 화면이 768px 이하 모바일 레이아웃으로 렌더**되고 있었다. 사용자는 데스크톱 레이아웃을 한 번도 못 본 상태로 리뷰할 뻔했다.
2. `python3 -m http.server` 가 캐시 헤더를 안 보내 고친 viewer 가 브라우저 캐시로 반영되지 않았다. `serve.py`(no-store) + iframe `?v=` 캐시버스팅 + **하단 빌드 스탬프** 3중으로 차단.

**교훈. 검증 스크립트가 매번 새 브라우저 컨텍스트를 띄워 캐시 없는 상태로 통과했다. 검증 환경이 실사용 환경보다 깨끗하면 stale 을 놓친다.**
그리고 어제 뷰어 검증에서 iframe 이 "로드됐는지" 만 보고 **폭을 재지 않은 것** 이 1번을 놓친 직접 원인이다.
