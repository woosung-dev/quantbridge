# QuantBridge — Frontend

Next.js 16 · TypeScript Strict · Tailwind CSS v4 · shadcn/ui v4 · Better Auth(자체 호스팅) · React Query · Zustand · Zod v4.

## 시작하기

```bash
pnpm install
cp .env.example .env.local       # frontend 전용 env (Next.js 자동 로드)
pnpm dev                         # http://localhost:3000
```

> `.env.example`은 **서비스별 분리**. frontend는 `apps/web/.env.example` 사용. apps/api/docker 전체 구조는 [루트 README](../../README.md#2-clone--환경-변수) + [local-setup.md](../../docs/reference/operations/local-setup.md#2-클론--환경-설정) 참조.

## 필수 환경 변수 (`apps/web/.env.example` 참조)

★**이 앱이 인증 서버 본체다**([ADR-034](../../docs/decisions/034-auth-self-host-better-auth.md)) — 그래서 `BETTER_AUTH_*` 는 전부 **서버 전용**이고 브라우저 번들로 나가지 않는다.

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
pnpm dev          # 개발 서버
pnpm build        # 프로덕션 빌드
pnpm start        # 프로덕션 실행
pnpm lint         # ESLint
pnpm typecheck    # tsc --noEmit
pnpm test         # Vitest
pnpm format       # Prettier
```

## 디렉토리 구조 (FSD Lite)

규칙 본문은 [`AGENTS.md`](AGENTS.md) §4 가 정본이다.

```
src/
├── app/                    # 라우트/레이아웃 (비즈니스 로직 금지)
│   ├── (auth)/             # /sign-in · /sign-up (Better Auth)
│   ├── (dashboard)/        # 인증 필요 화면 — Dark Theme 스코프
│   ├── api/auth/[...all]/  # ★Better Auth 서버 엔드포인트 (로그인·세션·JWKS)
│   └── <공개 라우트>       # pricing · terms · privacy · disclaimer · share · waitlist · invite · maintenance · not-available
├── components/
│   ├── ui/                 # shadcn/ui v4 (수정 금지, 래핑으로 확장)
│   ├── layout/             # DashboardShell 등
│   ├── legal/              # 3개 라우트가 공유하는 법무 셸
│   ├── charts/ monaco/ tape/
│   └── providers/          # AppProviders + QueryProvider
├── features/               # 도메인 단위 모듈 (12종) — ★화면 컴포넌트의 기본 자리 (ADR-035)
│                           # alert-rules · auth · backtest · dashboard · live-sessions
│                           # marketing · onboarding · optimizer · realtime · strategy
│                           # trading · waitlist
├── hooks/                  # 도메인 무관 공통 훅
├── lib/                    # api-client · auth · geo · 디자인 토큰 · ws-client
├── store/                  # 전역 Zustand (ui-store)
└── styles/                 # globals.css — DESIGN.md 토큰
```

## 핵심 규칙

- **Next.js 16:** `params`/`searchParams`는 `Promise<>` → `await` 필수. 미들웨어 파일명은 `proxy.ts`.
- **Zod v4:** `import { z } from "zod/v4"` (v3 경로 금지).
- **인증:** `proxy.ts`가 `getSessionCookie` + 자체 `createRouteMatcher`(`lib/route-matcher.ts`)로 공개 라우트를 가르고, 나머지는 세션을 **DB까지** 검증한다. FastAPI 호출용 Bearer JWT는 `/api/auth/token`이 준다.
- **금융 숫자:** JetBrains Mono + `tabular-nums`. float 연산은 백엔드(Decimal)에 위임.
- **테마:** 기본 Light, `(dashboard)` 하위는 `data-theme="dash"`로 Dark Theme 스코프 적용.

## 다음 단계

~~Stage 3 스캐폴딩 3항목(shadcn init · `features/strategy` 연동 · 랜딩 포팅)~~
→ **셋 다 완료됐다.** 다음에 할 일은 [`docs/status.md`](../../docs/status.md)의 「다음 스프린트」 블록이 유일한 진입점이다.
