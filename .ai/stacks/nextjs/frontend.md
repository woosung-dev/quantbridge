---
description: Next.js 16 및 Frontend 규칙
paths:
  - "frontend/**/*"
---

# Frontend Rules (Next.js 16)

---

## 1. Tech Stack

| 항목            | 기술                                  |
| --------------- | ------------------------------------- |
| Framework       | Next.js 16 (App Router)               |
| Language        | TypeScript Strict                     |
| Styling         | Tailwind CSS v4 + shadcn/ui v4        |
| Package Manager | `pnpm`                                |
| Server State    | React Query (`@tanstack/react-query`) |
| Client State    | Zustand                               |
| Form            | `react-hook-form` + `zod v4`          |
| Auth            | Clerk (`@clerk/nextjs`)               |
| 배포            | Vercel                                |

---

## 2. 핵심 제약 사항 (Strict Rules)

> Next.js 16, Zod v4, shadcn/ui v4, 반응형 패턴은 **`.ai/rules/nextjs-shared.md`** 참조.

### Clerk (Next.js 16)

- 인증 보호: **`proxy.ts`** 에서 `clerkMiddleware()` 처리
- 서버 컴포넌트: `auth()` 또는 `currentUser()`
- 클라이언트 컴포넌트: `useAuth()`, `useUser()`
- 직접 JWT 파싱 금지

```typescript
// proxy.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});
```

---

## 3. 컴포넌트 & 상태 관리 패턴

### Thin Component

- 페이지/UI 컴포넌트 내부에 비즈니스 로직 직접 작성 금지
- 비즈니스 로직은 커스텀 훅(`features/[domain]/hooks.ts`)으로 분리

### 상태 관리 3단계

| 종류          | 도구        | 예시          |
| ------------- | ----------- | ------------- |
| Server State  | React Query | API 데이터    |
| Client Global | Zustand     | 사이드바 토글 |
| Client Local  | useState    | 모달 상태     |

- **React Query:** Query Key 하드코딩 금지 → 도메인별 팩토리 패턴. API 호출은 `features/[domain]/api.ts`에 집중
- **Zustand:** 전역 상태는 최소화 — 컴포넌트 트리를 넓게 넘나드는 상태만 관리

### 에러 핸들링

- `if (isLoading)` / `if (error)` 남발 금지 → `Suspense` + `ErrorBoundary`로 위임

### React Hooks 안전 규칙 (LESSON-004/005/006 승격, 2026-04-23)

> 세 규칙은 실전 CPU 100% 무한 루프 / ESLint 우회 유혹 / React Compiler panic 을 유발한 실측 교훈에서 승격됐다. 예외 시 별도 ADR 로 기록해야 한다.

#### H-1. `useEffect` dep 에 "불안정한 참조 객체" 를 쓰지 말 것

- **금지**: React Query `data`, Zustand selector 결과, RHF `watch()`, Zod `.parse()` 결과를 `useEffect` dep 로 직접 사용
- **이유**: Fast Refresh / StrictMode 더블 인보크 / 부모 재렌더 경계에서 참조가 흔들리며 `setState` → 재렌더 → 새 참조 → 무한 루프 발생. dev 에서만 재현되므로 vitest jsdom 은 못 잡음
- **대신**:
  - "prop change 시 state 초기화" 패턴은 render-time clamp/compare 로 대체 (예: `const clamped = Math.min(index, len - 1)`)
  - 부득이할 때 scalar dep 선호 (`[items.length]` > `[items]`)
  - React 공식 "reset state on prop change" 패턴 (`if (prev !== curr) setState(...)`) 사용
- **Lint 규약**: `react-hooks/set-state-in-effect` 경고는 **override 절대 금지**. 해당 lint 는 바로 이 패턴을 차단하기 위해 존재
- **PR 규약**: hooks diff 가 있는 PR 은 **dev server live smoke 5분 이상** 필수. unit test 만으로 green 인정 안 됨

#### H-2. React Query `queryKey` 에 Clerk JWT accessor (`getToken`) 직접 포함 금지

- **금지**: `queryKey: [..., await getToken()]` 또는 `getToken` 함수 참조 자체를 queryKey 에 포함
- **이유**:
  - `getToken` 은 매 렌더마다 새 함수 참조 → queryKey identity 망가짐 → cache 무효화 폭주
  - `@tanstack/eslint-plugin-query`의 `exhaustive-deps` rule 이 closure capture 추적으로 차단 (`reference.resolved?.scope`). 동일 스코프 alias 우회 불가
- **대신**:
  - `userId` identity 를 queryKey factory 첫 인자로 사용 (`strategyKeys.list(userId, query)`)
  - 로그아웃 방어: 호출부에서 `userId ?? "anon"` sentinel
  - queryFn 은 **모듈-level factory** 호출식으로 분리 (`queryFn: makeListFetcher(query, getToken)`) — rule 이 `CallExpression` 에선 내부 capture 검사 skip
- **Lint 규약**: `@tanstack/query/exhaustive-deps` override 금지. 우회 패턴 (factory 추출) 이 있음

#### H-3. React Compiler 호환 — render body 에서 `ref.current = value` 대입 금지

- **금지**: 함수형 컴포넌트 render phase 에서 `ref.current = x` 직접 대입 (React 공식 "latest state in closures" 예시 따라도 안 됨)
- **이유**: `eslint-plugin-react-compiler` 가 "Cannot access refs during render" 로 error 차단. Compiler 의 재실행/메모이제이션 가정과 충돌
- **대신**: **dependency array 없는 sync `useEffect`** 로 이동 (매 commit 후 실행). 기능상 render 직후 commit phase 라 동일
  ```tsx
  const latest = useRef(value);
  useEffect(() => { latest.current = value; });  // deps 없음 = 매 commit
  ```
- **Debouncer 패턴**: `useRef` + sync useEffect + timeout 콜백에서 `ref.current` 읽기 조합이 표준

---

## 4. Directory Structure (FSD Lite)

> 에이전트는 새로운 기능 개발 시 반드시 아래 구조를 준수하여 파일을 배치한다.

```
src/
├── app/                    # View Layer: 라우트, 레이아웃, 페이지 (비즈니스 로직 작성 금지)
├── components/             # Shared UI: 도메인을 모르는 공통 UI
│   ├── ui/                 # shadcn/ui 컴포넌트 (수정 금지, 래핑으로 확장)
│   └── layout/             # Header, Sidebar 등 공통 레이아웃
├── features/               # ★ Business Layer: 도메인 기능 단위 모듈 (응집도 최상)
│   └── [domain]/           # ex) users, orders, payments
│       ├── components/     # 도메인 종속 UI (UserCard, OrderForm 등)
│       ├── api.ts          # API 호출 함수 + Query Key Factory
│       ├── hooks.ts        # React Query 래핑 훅 + 비즈니스 로직
│       ├── schemas.ts      # Zod 스키마 + z.infer 타입 추출
│       ├── store.ts        # 도메인 전용 Zustand (필요 시)
│       └── types.ts        # API Request/Response 타입
├── hooks/                  # 도메인 무관 공통 훅 (useDebounce 등)
├── lib/                    # Utility: API 클라이언트, 유틸리티, 상수
├── store/                  # Global State: 앱 전역 Zustand (Theme 등)
└── types/                  # 전역 공통 타입 (UUID, Timestamped 등)
```

## 5. 반응형 (Responsive Design)

> 반응형 규칙은 **`.ai/rules/nextjs-shared.md`** 참조.

---

## 6. Next.js 16 차용 패턴 (FastAPI BE 조합)

> QuantBridge 는 FastAPI BE + Next.js FE 구조라 Server Actions / Drizzle 패턴은 직접 적용 불가. 아래 3 패턴만 차용.

### Server Component vs Client Component 경계

- 기본값 = Server Component. `"use client"` 는 진짜 필요할 때만 (이벤트 핸들러, `useState/useEffect`, Clerk client hook 등).
- `"use client"` 는 **말단(leaf) 컴포넌트** 에만. layout/page 파일에 금지.
- Server Component 는 Client Component import 가능, **반대는 금지**.
- Server Component 에서 자체 API Route `fetch()` 호출 금지 — FastAPI BE 직접 호출 (`features/[domain]/api.ts`).

### `error.tsx` Route Error Boundary

- 주요 dashboard route 마다 `error.tsx` 의무 (`"use client"` 필수). "다시 시도" 메커니즘 포함.
- `if (isLoading) / if (error)` 워터폴 금지 → `Suspense + ErrorBoundary` 위임.

```typescript
// app/(dashboard)/<route>/error.tsx
"use client";
export default function RouteError({
  error,
  reset,
}: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <h2 className="text-xl font-bold">문제가 발생했습니다</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <button onClick={reset} className="btn btn-primary">다시 시도</button>
    </div>
  );
}
```

### `ActionResult<T>` 타입 — throw 금지, 직렬화 가능 결과

- FastAPI 호출 wrapper (`features/[domain]/api.ts`) 가 `throw` 대신 `ActionResult<T>` 반환 권장 — 클라이언트 크래시 방지 + 타입 안정성.

```typescript
// features/[domain]/types.ts 또는 lib/types.ts
export type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string | z.ZodFlattenedError };
```

- React Query `mutation.onError` 가 throw 처리하더라도, API wrapper 레이어는 `ActionResult` 로 typed result 노출. UI 가 `result.success` 분기로 disambiguate.
