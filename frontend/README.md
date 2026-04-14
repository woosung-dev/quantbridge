# QuantBridge — Frontend

Next.js 16 · TypeScript Strict · Tailwind CSS v4 · shadcn/ui v4 · Clerk · React Query · Zustand · Zod v4.

## 시작하기

```bash
pnpm install
cp ../.env.example .env.local   # 프로젝트 루트 .env.example 기반으로 값 입력
pnpm dev                         # http://localhost:3000
```

## 필수 환경 변수 (루트 `.env.example` 참조)

| 변수 | 용도 |
|------|------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk 공개 키 |
| `CLERK_SECRET_KEY` | Clerk 시크릿 (서버 전용) |
| `NEXT_PUBLIC_API_URL` | FastAPI 백엔드 URL (기본 `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL |

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

`.ai/rules/frontend.md` 4장 참조.

```
src/
├── app/                    # 라우트/레이아웃 (비즈니스 로직 금지)
│   ├── (auth)/             # Clerk SignIn/SignUp
│   └── (dashboard)/        # 인증 필요 화면 — Dark Theme 스코프
├── components/
│   ├── ui/                 # shadcn/ui v4 (수정 금지)
│   ├── layout/             # DashboardShell 등
│   └── providers/          # ClerkProvider + QueryProvider
├── features/               # 도메인 단위 모듈 (strategy, backtest, trading, exchange)
├── hooks/                  # 공통 훅 (use-debounce 등)
├── lib/                    # api-client, utils
├── store/                  # 전역 Zustand (ui-store)
├── styles/                 # globals.css — DESIGN.md 토큰
└── types/                  # 공통 타입
```

## 핵심 규칙

- **Next.js 16:** `params`/`searchParams`는 `Promise<>` → `await` 필수. 미들웨어 파일명은 `proxy.ts`.
- **Zod v4:** `import { z } from "zod/v4"` (v3 경로 금지).
- **Clerk:** `proxy.ts`에서 `clerkMiddleware` + `createRouteMatcher` 사용. 공개 라우트 외는 `auth.protect()`.
- **금융 숫자:** JetBrains Mono + `tabular-nums`. float 연산은 백엔드(Decimal)에 위임.
- **테마:** 기본 Light, `(dashboard)` 하위는 `data-theme="dash"`로 Dark Theme 스코프 적용.

## 다음 단계 (Stage 3)

1. `pnpm dlx shadcn@latest init` 후 Button/Card/Input 등 기본 컴포넌트 설치
2. `features/strategy/api.ts` + `hooks.ts` — FastAPI `/strategies` 연동
3. 랜딩 페이지 (`docs/prototypes/00-landing.html`) → 실제 컴포넌트로 포팅
