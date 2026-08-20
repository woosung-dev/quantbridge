# QuantBridge — Frontend

Next.js 16 App Router 로 만든 대시보드이자, **이 레포의 인증 서버 본체**다 ([ADR-034](../../docs/decisions/034-auth-self-host-better-auth.md)). 로그인·세션·JWKS 발급을 이 앱이 담당하고, FastAPI 는 그 JWKS 로 토큰을 검증만 한다.

- 라우트 26 · feature 도메인 12 · Vitest 227파일 · Playwright 31 spec
- 전체 제품 소개와 최초 셋업은 [루트 README](../../README.md) 참조

---

## 화면 목록

### 공개 (인증 불필요)

| 라우트                            | 설명                                                                                     |
| --------------------------------- | ---------------------------------------------------------------------------------------- |
| `/`                               | 랜딩 — 히어로·기능·작동방식·지원현황·성능·FAQ. 로그인 상태면 `/strategies` 로 리다이렉트 |
| `/pricing`                        | 요금제 — 지원/미지원 범위 표기                                                           |
| `/waitlist`                       | 베타 웨이트리스트 신청 (`?email=` 프리필)                                                |
| `/invite/[token]`                 | 초대 링크 착지 페이지                                                                    |
| `/share/backtests/[token]`        | 백테스트 결과 외부 공개 공유 (읽기 전용)                                                 |
| `/terms` `/privacy` `/disclaimer` | 법무 3종 (공통 `LegalPageShell`)                                                         |
| `/not-available`                  | geo-block 안내                                                                           |
| `/maintenance`                    | 점검 페이지 (앱 셸 밖 단독 렌더)                                                         |

### 인증 (`(auth)`)

| 라우트     | 설명                                          |
| ---------- | --------------------------------------------- |
| `/sign-in` | 로그인 — 자체 폼 + 스플릿 스크린 셸           |
| `/sign-up` | 가입 — 제한 국가 차단은 서버 create 훅이 담당 |

### 대시보드 (`(dashboard)` — 세션 필수 · Dark Theme 스코프)

| 라우트                   | 설명                                                                   |
| ------------------------ | ---------------------------------------------------------------------- |
| `/dashboard`             | 포트폴리오 개요 — 라이브 세션·백테스트·전략 집계                       |
| `/strategies`            | 전략 목록 (서버 prefetch + hydrate, CSV 내보내기)                      |
| `/strategies/new`        | 전략 생성 — 좌 기본정보·Pine 소스 / 우 파싱 결과                       |
| `/strategies/[id]/edit`  | 전략 편집 — Monaco 소스 · 진단 · 실행설정 · 메타데이터 · Webhook       |
| `/backtests`             | 백테스트 목록                                                          |
| `/backtests/new`         | 새 백테스트 실행 폼                                                    |
| `/backtests/[id]`        | 백테스트 리포트 상세 (9개 섹션)                                        |
| `/backtests/[id]/trades` | 체결 거래 상세                                                         |
| `/optimizer`             | 최적화 제출 폼 + 실행 목록                                             |
| `/optimizer/[id]`        | 최적화 실행 상세 (히트맵 · 이력 차트 · OOS)                            |
| `/trading`               | 트레이딩 코크핏 (8개 섹션 — 상태·잔고·포지션·제한·주문·계정·세션·알림) |
| `/orders`                | 주문 원장 — 라이브·데모 통합 blotter                                   |
| `/onboarding`            | 4-step 온보딩 위저드                                                   |
| `/admin/waitlist`        | 웨이트리스트 어드민                                                    |

라우트별 `error.tsx` 8개 · `loading.tsx` 9개. 유일한 route handler 는 `app/api/auth/[...all]/route.ts` (Better Auth).

---

## 기술 스택

| 영역            | 기술 / 버전                                                                   |
| --------------- | ----------------------------------------------------------------------------- |
| 프레임워크      | Next.js `^16.2.4` (App Router) · React `^19` · TypeScript `^5.6` Strict       |
| 스타일링        | Tailwind CSS `^4` · shadcn/ui `^4` (Base UI) · Pretendard                     |
| 서버 상태       | TanStack React Query `^5.59`                                                  |
| 클라이언트 상태 | Zustand `^5`                                                                  |
| 폼 · 검증       | React Hook Form `^7.72` · Zod `^4.3` (`zod/v4` 경로 필수)                     |
| 인증            | Better Auth `^1.6` + `pg`                                                     |
| 에디터          | `@monaco-editor/react` `^4.7` — Pine 전용 Monarch 문법·테마 자체 정의         |
| 차트            | `lightweight-charts` `^4.2` (에쿼티·드로다운) · `recharts` `^3.8` (분포·이력) |
| 테스트          | Vitest `^2.1` · Testing Library · Playwright `^1.59`                          |
| 품질            | ESLint 9 (react-compiler · react-hooks · tanstack-query 플러그인) · Prettier  |
| Node            | `>=22`                                                                        |

---

## 시작하기

```bash
pnpm install
cp .env.example .env.local       # frontend 전용 env (Next.js 자동 로드)
pnpm dev                         # http://localhost:3000
```

> 루트에서 `mise run fe` 로도 같은 서버가 뜬다. 인프라·백엔드까지 한 번에 띄우려면 `mise run dev`.
> `.env.example` 은 서비스별 분리다 — 전체 구조는 [루트 README](../../README.md#2-클론--환경-변수) + [local-setup.md](../../docs/reference/operations/local-setup.md) 참조.

## 환경 변수

★**이 앱이 인증 서버 본체다** — 그래서 `BETTER_AUTH_*` 는 전부 **서버 전용**이고 브라우저 번들로 나가지 않는다.

| 변수                       | 용도                                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| `BETTER_AUTH_SECRET`       | 세션 암호화·해싱 키. 32자 이상 (`openssl rand -base64 32`)                                |
| `BETTER_AUTH_URL`          | 이 앱의 공개 origin. JWT 의 `iss`/`aud` 기준. **FastAPI 의 같은 이름 값과 일치해야 한다** |
| `BETTER_AUTH_DATABASE_URL` | `auth_*` 5테이블 전용 Postgres DSN                                                        |
| `NEXT_PUBLIC_API_URL`      | FastAPI 백엔드 URL (기본 `http://localhost:8000`)                                         |
| `NEXT_PUBLIC_WS_URL`       | WebSocket URL (실시간)                                                                    |

> `pnpm e2e:authed` 는 `E2E_AUTH_EMAIL`·`E2E_AUTH_PASSWORD` 도 요구한다 — `e2e/global.setup.ts` 가 그 계정으로 실제 `/sign-in` 폼을 채운다.

## 스크립트

```bash
pnpm dev                  # 개발 서버
pnpm build                # 프로덕션 빌드
pnpm start                # 프로덕션 실행
pnpm lint                 # ESLint
pnpm typecheck            # tsc --noEmit
pnpm format               # Prettier
pnpm test                 # Vitest 1회 실행
pnpm test:watch           # Vitest watch

pnpm e2e                  # Playwright smoke (인증 불요)
pnpm e2e:authed           # 인증 시나리오 (E2E_AUTH_* 필요 · production 모드에서 차단)
pnpm e2e:design-canon     # 디자인 캐논 회귀
pnpm e2e:all              # 전체
pnpm e2e:install          # 브라우저 설치
pnpm screen-evidence      # 화면 증거 스냅샷 대조 (--update 로 갱신)
```

---

## 디렉터리 구조 (FSD Lite)

규칙 본문은 [`AGENTS.md`](AGENTS.md) §4 가 정본이다.

```
src/
├── app/                    # 라우트/레이아웃 (비즈니스 로직 금지 · 화면 컴포넌트 소유 아님)
│   ├── (auth)/             # /sign-in · /sign-up
│   ├── (dashboard)/        # 인증 필요 화면 — Dark Theme 스코프
│   ├── api/auth/[...all]/  # ★Better Auth 서버 엔드포인트 (로그인·세션·JWKS)
│   └── <공개 라우트>       # pricing · terms · privacy · disclaimer · share · waitlist · invite · maintenance
├── components/
│   ├── ui/                 # shadcn/ui v4 (수정 금지, 래핑으로 확장)
│   ├── layout/             # DashboardShell · 사이드바 · 모바일 내비
│   ├── legal/              # 법무 3라우트 공용 셸
│   ├── charts/ monaco/ tape/
│   └── providers/          # AppProviders + QueryProvider
├── features/               # ★화면 컴포넌트의 기본 자리 (ADR-035) — 12 도메인
├── hooks/                  # 도메인 무관 공통 훅
├── lib/                    # api-client · auth · geo · 디자인 토큰 · ws-client
├── store/                  # 전역 Zustand (ui-store)
└── styles/                 # globals.css — DESIGN.md 토큰
```

### `features/` 12 도메인

| 도메인          | 담당                                                                      |
| --------------- | ------------------------------------------------------------------------- |
| `strategy`      | 전략 목록·생성 위저드·편집기(Monaco·진단·webhook), Pine lexicon, 드래프트 |
| `backtest`      | 최대 도메인 — 목록·폼·9섹션 리포트·차트·스트레스 테스트·공유·재실행       |
| `optimizer`     | grid/bayesian/genetic 제출 폼, 히트맵, 이력 차트, OOS 검증                |
| `trading`       | 코크핏, 킬 스위치, 주문 blotter·드로어, 포지션·잔고, 거래소 계정 등록     |
| `live-sessions` | 라이브 세션 목록·생성·상세, 미실현 손익, 활동 타임라인, outcome parity    |
| `alert-rules`   | 세션 알림 규칙 폼 (트레이딩 세션 진단에서 소비)                           |
| `dashboard`     | 워크스페이스 코크핏, 에쿼티 카드                                          |
| `realtime`      | WS 연결 브리지 + ticker 캐시 Zustand 스토어                               |
| `marketing`     | 랜딩 섹션 10종 + pricing                                                  |
| `waitlist`      | 신청 폼 · 어드민 대시보드 · 초대 토큰 판정                                |
| `auth`          | 로그인/가입 폼, 스플릿 스크린 셸                                          |
| `onboarding`    | 4-step 위저드 + progress stepper                                          |

---

## 테스트

| 종류       | 규모                   | 실행                      |
| ---------- | ---------------------- | ------------------------- |
| Vitest     | 227 파일 (jsdom)       | `pnpm test`               |
| Playwright | 31 spec · 프로젝트 7종 | `pnpm e2e` / `e2e:authed` |

Playwright 프로젝트: `chromium` · `chromium-authed` · `chromium-live-smoke` · `chromium-design-canon` · `chromium-screen-evidence(-authed)` + setup 3종(`global.setup.ts` · `identity.setup.ts` · `authed-reachability.setup.ts`).

### 알아 두면 시간을 아끼는 것

- **차트 라이브러리가 2종이다.** 에쿼티·드로다운은 `lightweight-charts`, 분포·이력 차트는 `recharts`. Recharts 는 번들 355KB × N 중복을 막으려고 **단일 dynamic-import 진입점**(`features/backtest/components/charts/recharts-plots.ts`)을 거치게 돼 있다 — 컴포넌트에서 직접 `recharts` 를 import 하지 마라.
- **실시간은 WebSocket + 폴링 하이브리드다.** SSE 는 쓰지 않는다. 폴링 간격 정책의 SSOT 는 `lib/query-poll.ts` (에러 시 폴링 중단 가드 포함).
- **컴포넌트를 옮기기 전에 검사기 스코프를 먼저 재라.** 일부 감사 테스트가 디렉터리 목록으로 스캔 대상을 정의해서, 목록을 안 고치고 옮기면 스코프가 비고 테스트는 초록이 된다 (`node scripts/canon-scope-census.mjs`).

---

## 핵심 규칙

- **Next.js 16** — `params`/`searchParams` 는 `Promise<>` → `await` 필수. 미들웨어 파일명은 `proxy.ts`
- **Zod v4** — `import { z } from "zod/v4"` (v3 경로 금지)
- **인증** — `proxy.ts` 가 공개 라우트를 가르고 나머지는 세션을 **DB까지** 검증한다. 클라이언트는 `useAuthCtx()` 하나만 쓴다
- **금융 숫자** — JetBrains Mono + `tabular-nums`. float 연산은 백엔드(Decimal)에 위임
- **테마** — 기본 Light, `(dashboard)` 하위는 `data-theme="dash"` 로 Dark 스코프

전체 규칙(React Hooks 안전 H-1~H-3 · 반응형 · TS 컨벤션)은 [`AGENTS.md`](AGENTS.md) 가 정본이다.
지금 진행 중인 작업은 [`docs/status.md`](../../docs/status.md) 에 있다.
