# Frontend Rules (Next.js 16)

> 코드가 말하지 못하는 것만 적는다([ADR-047](../../docs/adr/047-agent-rules-as-enforcer-table.md)). 예제는 옆 파일을 본다.
> lint 의 이유는 [ADR-039](../../docs/adr/039-frontend-biome.md)와 `biome.jsonc` 주석이, 반응형·앱 셸 값은
> [`DESIGN.md`](../../DESIGN.md)가 갖는다. 어느 규칙을 무엇이 집행하는지는 맨 아래 표에 있다.
> **절 번호와 `H-N` id 는 옮기지 않는다** — `docs/lessons.md`·ADR·`biome.jsonc`·코드 주석이 인용한다.

## 1. Tech Stack

정본은 `package.json` 이다. 이름만 봐서는 틀리기 쉬운 것:

- Tailwind v4 는 CSS-first 라 설정 파일이 없다. shadcn v4 의 내부 의존성은 Radix 가 아니라 `@base-ui/react` 다(§9).
- RHF resolver 는 자체 `lib/zod-v4-resolver.ts` 다. `@hookform/resolvers` 는 설치돼 있지 않다.
- 배포는 Vercel 이 아니라 오라클 A1 + Cloudflare Tunnel 이고 `output: "standalone"` 이다. 서버에 Node 가 없어
  `next start` 를 못 쓴다. 절차 = [`frontend-deploy.md`](../../docs/operations/frontend-deploy.md)

## 2. 인증 — Better Auth ([ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

이 앱이 인증 서버 본체다. `/api/auth/[...all]` 이 로그인·세션·JWKS 를 낸다.

- 인증 보호는 `proxy.ts` 하나가 한다. 공개 라우트가 아니면 `auth.api.getSession()` 으로 완전 검증한다.
  검증을 라우트마다 흩으면 새 라우트가 조용히 공개된다.
- 클라이언트는 `useAuthCtx()` 하나만 쓴다(`hooks/use-auth-ctx.ts`). `useSession()`·`getAuthToken()` 을 직접 부르지 않는다.
  표시용 이름·이메일도 `user` 로 받는다. 공급자 교체가 이 seam 하나로 끝난다.
- 서버 신원 조회는 `getServerSession()`(`lib/auth-server.ts`)이다. FastAPI prefetch 에 JWT 가 필요할 때만 `getServerAuth()` 를 쓴다.
- JWT 를 직접 파싱하지 않는다. 예외는 `auth-client.ts` 가 캐시 수명 계산에 `exp` 를 읽는 것뿐이다.
- `getSessionCookie()` 를 인증 게이트로 쓰지 않는다. 쿠키 존재만 본다. `proxy.ts` 의 `/` → `/strategies` UX 리다이렉트 전용이다.

## 3. 컴포넌트 & 상태 관리 패턴

- **Thin Component** — 페이지·UI 컴포넌트 안에 비즈니스 로직을 두지 않는다. `features/[domain]/hooks.ts` 로 뺀다.
- **상태 3단계** — Server State 는 React Query, Client Global 은 Zustand(`store/ui-store.ts`), Client Local 은 `useState` 다.
  사이드바 접힘은 상태가 아니라 순수 CSS 다(§10). 토글 store 를 새로 만들지 않는다.
- **React Query** — Query Key 를 하드코딩하지 않고 도메인별 `query-keys.ts` 팩토리를 쓴다(첫 인자 = `userId`).
  API 호출은 `features/[domain]/api.ts` 에 모으고 `apiFetch` 를 지난다. `apiFetch` 밖에서 FastAPI 를 직접 `fetch` 하는
  곳은 등재된 예외다 — `getApiBase()`/`API_BASE_URL` 를 쓰는 `fetch(` 를 grep 하면 나온다. 새로 만들지 않는다.
- **에러 핸들링** — 라우트 경계는 `error.tsx`(§6)가 ErrorBoundary 다. 컴포넌트 안의 `if (isLoading)`/`if (error)`
  워터폴은 `Suspense` 로 걷는다. 규칙이지 현황이 아니다 — 기존 조기 반환을 선례로 읽지 않는다.

### React Hooks 안전 규칙

셋 다 실전 사고(CPU 100% 무한 루프 · cache 무효화 폭주 · Compiler 충돌)에서 나왔고 기계 방어선이 거의 없다([ADR-039]).
리뷰에서 사람이 본다. 예외는 ADR 로 기록한다.

**H-1. `useEffect` dep 에 불안정한 참조 객체를 넣지 않는다** — React Query `data` · Zustand selector 결과 ·
RHF `watch()` · Zod `.parse()` 결과. Fast Refresh, StrictMode 더블 인보크, 부모 재렌더에서 참조가 흔들려
`setState` → 재렌더 → 새 참조 → 무한 루프가 된다. dev 에서만 재현돼 vitest jsdom 은 못 잡는다.
대신 render-time clamp/compare(`Math.min(index, len - 1)`), scalar dep(`[items.length]`), 공식 "reset state on prop change"
(`if (prev !== curr) setState(...)`)를 쓴다.

- 기계가 보는 것은 빠진 dep(`useExhaustiveDependencies`)과 `useHookAtTopLevel` 뿐이다. 후자는 `biome.jsonc` 의
  `domains.react: "recommended"` 한 줄로만 켜져서 그 줄을 지우면 함께 꺼진다.
- hooks 를 건드린 PR 은 dev server live smoke 를 사람이 돌린다. `live-smoke.yml` 은 공개 라우트의 `console.error`
  개수만 재므로 그 초록을 「훅이 안전하다」로 읽지 않는다.

**H-2. React Query `queryKey` 에 JWT accessor(`getToken`)를 넣지 않는다** — 함수 참조도, `await getToken()` 결과도.
`getToken` 은 매 렌더 새 함수 참조라 queryKey identity 가 무너져 cache 무효화가 폭주한다.
대신 `userId` 를 팩토리 첫 인자로 넘기고(`strategyKeys.list(userId, query)`) 로그아웃은 `userId ?? "anon"` 으로 막는다.

**H-3. render body 에서 `ref.current = value` 를 대입하지 않는다** (React 공식 예시를 따라도 안 된다).
Compiler 의 재실행·메모이제이션 가정과 충돌한다. deps 배열 없는 sync `useEffect` 로 옮긴다.
Debouncer 표준은 `useRef` + 그 `useEffect` + timeout 콜백에서 `ref.current` 읽기다.
실물 = `features/strategy/draft.ts` · `features/realtime/realtime-bridge.tsx`.

- React Compiler 가 켜져 있다(`next.config.ts`). 이 규칙을 어긴 컴포넌트는 컴파일러가 조용히 건너뛰어 자동 메모이제이션이 빠진다.
- react-hook-form v7 을 만지는 모듈은 `"use client";` 바로 아래에 `"use no memo";` 를 둔다. `form.watch()`·`formState` 는
  참조가 고정돼 컴파일러가 낡은 값을 캐시한다. 부모만 빼면 `errors` 를 prop 으로 받는 자식이 낡는다.
  예외는 `components/ui/form.tsx` 다. RHF v8 로 가면 이 줄을 걷는다.

## 4. Directory Structure (FSD Lite)

구조는 `ls src` 가 정본이다. 층마다 넣을 수 있는 것:

- `app/` — 조립층이다. 라우트·레이아웃·loading·error·metadata 와 feature 조립만 둔다. 비즈니스 로직과 화면 컴포넌트를 두지 않는다.
- `components/` — 도메인을 모르는 공통 UI 만 둔다. `ui/` 는 shadcn 이식분이라 직접 고치지 않고(§9) lint·format 게이트 밖이다.
- `features/<domain>/` — 도메인 단위 모듈이다. 화면 컴포넌트의 기본 자리는 `components/` 이고, 나머지는
  `api.ts`·`query-keys.ts`·`hooks.ts`·`schemas.ts`·`store.ts`·`types.ts` 중 필요한 것만 둔다.
- `hooks/` · `lib/` · `store/` — 도메인과 무관한 공통 훅(`use-` 접두사 kebab-case) · API 클라이언트와 유틸 · 앱 전역 Zustand.
- `styles/globals.css` 가 CSS 정본이다. `app/globals.css` 는 없다(§10).
- `proxy.ts` 를 쓴다. `middleware.ts` 가 아니다.

**`app/**/_components/`** ([ADR-035](../../docs/adr/035-fe-component-ownership.md)) — 한 라우트 전용이고 순수 표현이며 5파일 미만일 때만 쓴다.
두 라우트 이상이 쓰거나 도메인 로직이 있으면 `features/<domain>/components/`, 도메인을 모르면 `components/` 다.
의심스러우면 feature 로 보낸다.

**레이어 경계** ([ADR-035]) — `features/`·`components/`·`lib/`·`hooks/`·`store/` 는 `@/app/*` 를 import 하지 않는다.
`app/` 은 최상위 조립층이라 아래 층이 거슬러 참조하면 라우트를 못 옮긴다. `components/`·`lib/` 는 `features/` 도
import 하지 않는다. 도메인 코드가 필요해지면 공유층을 넓히지 말고 그 `features/<domain>/` 으로 옮긴다.
템플릿 리터럴 ``import(`@/app/${x}`)`` 와 역방향(`app/` 안에 로직·화면 컴포넌트를 두는 것)은 lint 가 보지 못한다.

**컴포넌트를 옮길 때** — `src/__tests__/no-raw-enum-labels.test.ts` 는 스캔 대상을 디렉터리 목록(`SCOPE_MARKERS`)으로
정의하고 사라진 디렉터리를 만나면 throw 한다. 목록을 함께 고친다. 이동 전후 대조 = `node scripts/canon-scope-census.mjs`.

## 5. 반응형 — 본문은 §10

## 6. Next.js 16 패턴 (FastAPI BE 조합)

FastAPI BE + Next.js FE 구조라 Server Actions 와 Drizzle 패턴은 쓰지 않는다.

- 기본값은 Server Component 다. `"use client"` 는 이벤트 핸들러·`useState/useEffect`·`useAuthCtx` 가 필요한
  말단(leaf) 컴포넌트에만 붙인다. layout/page 파일에는 붙이지 않는다.
- Server Component 는 Client Component 를 import 할 수 있고 반대는 안 된다.
- Server Component 에서 자체 API Route 를 `fetch()` 하지 않는다. FastAPI BE 를 직접 부른다(`features/[domain]/api.ts`).
- 그룹 루트 `app/(dashboard)/error.tsx` 가 그 아래 라우트를 전부 덮는다. 라우트마다 만들지 않는다 — 고유한 복구
  문구·동작이 필요할 때만 자기 것을 둔다. `"use client"` 와 `reset` 이 필요하다.
- 실패 처리는 한 길이다. `features/*/api.ts` 는 `apiFetch<T>()` + Zod `.parse()` 로 payload 를 돌려주고 실패는
  `lib/api-client.ts` 의 `ApiError` 로 던진다. UI 는 React Query `isError` 와 `describeApiError()` 를 쓴다.

## 7. Next.js 16 필수 패턴

- `params`·`searchParams` 는 `Promise<>` 라 `await` 한다. 버전 고유 API 는 `node_modules/next/dist/docs/` 를 열어 확인한다(설치본이 정본).

## 8. Zod v4

- `import { z } from "zod/v4"` 로 통일한다. 생성물(`generated/`)은 예외다([ADR-031]).
- **Schema First** — 타입을 따로 선언하지 않고 `z.infer<typeof schema>`(필요하면 `z.input`)로 뽑아 쓴다.
- Form 입력(String) ↔ API 요청(Number) 변환을 `onSubmit` 안에서 하지 않는다. 스키마에서 `z.coerce.number()` 로 한다.

## 9. shadcn/ui v4

- `@radix-ui/*` 와 `radix-ui` 를 직접 import 하지 않는다. 컴포넌트는 `pnpm dlx shadcn@latest add [component]` 로
  `components/ui/` 에 들인다. registry 에 Base-UI 판이 없을 때만 그 안에서 `radix-ui` umbrella 를 쓴다
  ([ADR-009](../../docs/adr/009-shadcn-v4-form-radix-exception.md)).
- `components/ui/` 를 직접 고치지 않고 래핑 컴포넌트로 확장한다. 예외는 DESIGN.md 토큰 reconciliation 이고
  시각 토큰(Tailwind class)만이다(ADR-009). 비즈니스 로직·prop 시그니처·동작 변경은 래핑으로 한다.

## 10. 반응형 (Responsive Design)

- 신규 Tailwind 컴포넌트는 mobile-first 다. 기본이 모바일(320px~)이고 `sm:`/`md:`/`lg:` 로 넓힌다.
- `src/styles/globals.css` 의 KITPORT 구간과 화면 전용 CSS 는 desktop-first(`max-width`) 관례를 따른다.
  한 파일에 두 방향을 섞지 않는다. 전면 전환은 [BL-647] 이다.
- KITPORT 구간에는 주석 한 줄도 넣지 않는다. `_kit.html` 과 주석까지 포함해 대조된다.

**브레이크포인트는 Tailwind v4 기본값이 아니다.** `globals.css` 의 `@theme` 이 재정의한다(`sm:` 이 640 이 아니다).
`md:` 768 이 앱 셸 사이드바 숨김 경계, `lg:` 1024 가 아이콘 레일 경계다.

**유틸 접두사는 min-width, CSS 미디어는 max-width 다** — 같은 숫자를 반대 방향으로 쓴다. 정확히 그 숫자(768px 등)에서는
둘 다 참이라 같은 요소를 양쪽에서 숨기면 데드심이 난다. Tailwind v4 의 `max-[1024px]:` 는 경계를 포함하지 않아
KITPORT 의 `max-width:1024`(포함)와 어긋난다. 셸 정합은 `min-[769px]:` / `min-[1025px]:` 로 잡는다
(`dashboard-header.tsx` · `mobile-nav.tsx`). 유틸로 경계 포함이 안 되면 `globals.css` 에 raw 규칙을 쓴다.

앱 셸 값, 900px, 완료 체크리스트의 정본은 [`DESIGN.md`](../../DESIGN.md) 다(§10.2·§10.6 · §4.3.1 · §4.3.2).
체크리스트(고정 너비 `w-[Npx]` 금지 · 다열 그리드에 모바일 브레이크포인트 · 320px 무횡스크롤 · 텍스트 오버플로 처리 ·
테이블 `overflow-x-auto` 래퍼)는 기계가 재지 않는다. CI 가 도는 브라우저 검증 범위 = `docs/development/ci-cd.md`.

## 11. TypeScript 컨벤션

- Strict 다. `tsconfig.json` 이 `noUncheckedIndexedAccess`·`noImplicitOverride` 까지 켠다.
- `any` 를 쓰지 않는다. 부득이하면 `unknown` + Type Guard 로 간다.
- API 응답 타입은 명시적으로 정의한다.
- 네이밍 — Boolean 은 `is`/`has`/`should`, 핸들러는 `handle`, Props 이벤트는 `on` 접두사다.
- 파일은 컴포넌트도 kebab-case 다. 훅은 `use-` 접두사, 상수 값은 UPPER_SNAKE_CASE 다.
- non-null assertion(`!`)은 허용한다. `noNonNullAssertion` 은 의도적으로 꺼져 있다. 그래서 `biome check --write --unsafe` 를
  돌리지 않는다 — autofix 가 `foo!.bar` 를 `foo?.bar` 로 바꿔 런타임 의미가 달라진다(`!` 는 throw, `?.` 는 `undefined`).

## 규칙 ↔ 집행

집행기가 있는 규칙은 그 테스트·lint 가 정본이다. 「없음」인 규칙을 다시 어기게 되면 집행기를 만든다(루트 `AGENTS.md` §4).

| 규칙 | 집행 | 스코프 |
| --- | --- | --- |
| §2 인증 게이트 = `proxy.ts` · `getSessionCookie` 를 게이트로 쓰지 않음 | `src/__tests__/proxy-gate.test.ts` | `proxy.ts` |
| §2 `useAuthCtx()` seam | `src/hooks/__tests__/auth-ctx-boundary.test.ts` | `src` 전체의 `useSession`·`getAuthToken` import |
| §3 H-1 빠진 dep · hook 호출 위치 | `biome` `useExhaustiveDependencies` · `useHookAtTopLevel` | 불안정 참조 자체는 보지 못한다 |
| §4 `@/app/*` import · 공유층 → `features/` import | `biome` `noRestrictedImports` | 정적·동적 import. 템플릿 리터럴과 역방향은 보지 못한다 |
| §4 route 는 metadata/params + 단일 feature 위임 | `app/(dashboard)/__tests__/thin-routes.test.tsx` · `app/__tests__/public-thin-routes.test.ts` | dashboard route 와 pricing·invite·share. 그 밖의 배치는 사람이 본다 |
| §8 `zod/v4` · §9 Radix 직접 import | `biome` `noRestrictedImports` | lint 대상 전체(`components/ui`·`generated` 제외) |
| §10 KITPORT 구간 무수정 | `src/__tests__/design-canon-kit-port.test.ts` | `globals.css` 의 KITPORT 구간 |
| §10 셸 경계 정합 | `features/dashboard/components/__tests__/dashboard-shell.test.tsx` | 앱 셸 |
| §11 strict · `any` | CI `tsc --noEmit` · `biome` `noExplicitAny` | lint 대상 전체 |
| §2 JWT 직접 파싱 · §3 Thin Component · query-keys 팩토리 · `apiFetch` 경유 · Suspense | 없음 | — |
| §3 H-2 · H-3 · `"use no memo"` | 없음 — 리뷰 | — |
| §6 `"use client"` 위치 · `error.tsx` 범위 | 없음 | — |
| §9 `components/ui/` 직접 수정 | 없음(`biome.jsonc` 의 `!src/components/ui` 는 Biome 이 그 파일을 고치지 않게 하는 것이다) | — |
| §10 mobile-first · 체크리스트 | 없음 | — |
| §11 API 응답 타입 · 네이밍 접두사 · 파일 케이싱 | 없음 | — |
