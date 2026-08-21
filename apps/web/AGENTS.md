# Frontend Rules (Next.js 16)

---

## 1. Tech Stack

의존성·버전의 정본은 [`package.json`](./package.json) 이다 — 그 파일에 없는 것은 **배포처 = Vercel** 하나다.

스택 고유의 함정은 절별로 있다: §2(이 앱이 인증 서버 본체다) · §3(상태 3단계 · Hooks 안전 H-1~H-3) ·
§7(Next.js 16 — `params` 는 `Promise`, `middleware.ts` 아니라 `proxy.ts`) · §8(`zod/v4` 경로 필수) ·
§9(shadcn v4 는 Radix 아니라 `@base-ui/react`) · §10(★**브레이크포인트가 Tailwind 기본값이 아니다**).

---

## 2. 핵심 제약 사항 (Strict Rules)

> Next.js 16, Zod v4, shadcn/ui v4, 반응형·TS 컨벤션은 본 문서 **§7~§11**(구 `nextjs-shared.md`, ADR-027 병합) 참조.

### 인증 — Better Auth (Next.js 16 · [ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

★**이 앱이 인증 서버 본체다.** `/api/auth/[...all]` 이 로그인·세션·JWKS 를 낸다.

- 인증 보호: **`proxy.ts`** — 공개 라우트가 아니면 `auth.api.getSession()` 으로 **완전 검증**
- 클라이언트: **`useAuthCtx()` 하나만 쓴다**(`hooks/use-auth-ctx.ts`).
  `useSession()`·`getAuthToken()` 을 컴포넌트에서 직접 부르지 마라 — 공급자 교체가 그 seam 하나로
  끝난 이유가 그것이다
- 서버 컴포넌트: `getServerAuth()`(`lib/auth-server.ts`) → `{ userId, token }`
- 직접 JWT 파싱 금지 (예외: `auth-client.ts` 가 **캐시 수명 계산에만** `exp` 를 읽는다)

★**`getSessionCookie()` 를 인증 게이트로 쓰지 마라** — 쿠키의 존재만 본다(공식 문서가
"THIS IS NOT SECURE!" 라고 적는다). `proxy.ts` 에서 `/` → `/strategies` **UX 리다이렉트**에만 쓴다.

```typescript
// proxy.ts — 요지
if (!isPublicRoute(pathname)) {
  const session = await auth.api.getSession({ headers: req.headers });
  if (!session) return NextResponse.redirect(signInUrl);
}
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
- ⚠️**Lint 규약 (2026-08-22 변경)**: 종전엔 `react-hooks/set-state-in-effect` 가 이 패턴을 **차단**했다.
  [ADR-039] 로 ESLint 를 제거하면서 **그 규칙이 사라졌다** — Biome 523 규칙에 대응물이 없고
  GritQL 복원도 실패했다(실트리 11/11 오탐). **지금 이 항목은 기계가 아니라 사람이 지킨다.**
  대신 Biome 이 `useExhaustiveDependencies`(빠진 dep)와 `useHookAtTopLevel` 은 계속 잡는다
- **PR 규약**: hooks diff 가 있는 PR 은 **dev server live smoke 5분 이상** 필수. unit test 만으로 green 인정 안 됨

#### H-2. React Query `queryKey` 에 JWT accessor (`getToken`) 직접 포함 금지

- **금지**: `queryKey: [..., await getToken()]` 또는 `getToken` 함수 참조 자체를 queryKey 에 포함
- **이유**:
  - `getToken` 은 매 렌더마다 새 함수 참조 → queryKey identity 망가짐 → cache 무효화 폭주
  - ⚠️종전엔 `@tanstack/eslint-plugin-query` 의 `exhaustive-deps` 가 closure capture 추적으로 차단했다.
    [ADR-039] 로 **그 플러그인이 제거됐다** — Biome 에 대응 규칙이 0건이라 **기계 방어선이 없다**
- **대신**:
  - `userId` identity 를 queryKey factory 첫 인자로 사용 (`strategyKeys.list(userId, query)`)
  - 로그아웃 방어: 호출부에서 `userId ?? "anon"` sentinel
  - queryFn 은 **모듈-level factory** 호출식으로 분리 (`queryFn: makeListFetcher(query, getToken)`) — rule 이 `CallExpression` 에선 내부 capture 검사 skip
- ⚠️**Lint 규약 (2026-08-22 변경)**: 이 축을 **재는 도구가 없다**([ADR-039]). 규칙은 유효하고
  우회 패턴(factory 추출)도 그대로지만, 위반해도 CI 가 안 잡는다 — 리뷰에서 봐야 한다

#### H-3. React Compiler 호환 — render body 에서 `ref.current = value` 대입 금지

- **금지**: 함수형 컴포넌트 render phase 에서 `ref.current = x` 직접 대입 (React 공식 "latest state in closures" 예시 따라도 안 됨)
- **이유**: Compiler 의 재실행/메모이제이션 가정과 충돌한다.
  > ⚠️**2026-08-22 — 이 축의 기계 방어선이 없다**([ADR-039](../../docs/adr/039-frontend-biome.md)).
  > 종전 문장은 「`eslint-plugin-react-compiler` 가 "Cannot access refs during render" 로
  > **error 차단**한다」였는데, 실측 결과 ⑴ 그 핀(19.1.0-rc.2)에서 **그 모양은 애초에 발화하지
  > 않았고**(최소 재현 rc=0 · props 변이만 잡혔다) ⑵ 그 뒤 ESLint 자체가 제거됐다.
  > Biome 대체분(`nursery/useReactCompiler`)은 **한글 파일에서 panic** 해 못 쓴다.
  > ⇒ **권고는 유효하다. 다만 사람이 지킨다.** 참고로 React Compiler 는 `next.config.ts` 에
  > 켜져 있지도 않다 — 이 항목은 「지금의 버그 방지」가 아니라 「나중에 켤 때를 위한 대비」다.
- **대신**: **dependency array 없는 sync `useEffect`** 로 이동 (매 commit 후 실행). 기능상 render 직후 commit phase 라 동일
  ```tsx
  const latest = useRef(value);
  useEffect(() => {
    latest.current = value;
  }); // deps 없음 = 매 commit
  ```
- **Debouncer 패턴**: `useRef` + sync useEffect + timeout 콜백에서 `ref.current` 읽기 조합이 표준

---

## 4. Directory Structure (FSD Lite)

> 에이전트는 새로운 기능 개발 시 반드시 아래 구조를 준수하여 파일을 배치한다.

```
src/
├── app/                    # 조립층: 라우트·레이아웃·loading·error·metadata + feature 조립
│                           #   ★비즈니스 로직 금지. 화면을 그리는 컴포넌트도 여기 소유가 아니다
├── components/             # Shared UI: 도메인을 모르는 공통 UI
│   ├── ui/                 # shadcn/ui 컴포넌트 (수정 금지, 래핑으로 확장)
│   ├── layout/             # Header, Sidebar 등 공통 레이아웃
│   └── legal/              # 여러 라우트가 공유하는 법무 셸
├── features/               # ★ Business Layer: 도메인 기능 단위 모듈 (응집도 최상)
│   └── [domain]/           # 현재 12종: alert-rules · auth · backtest · dashboard ·
│       │                   #   live-sessions · marketing · onboarding · optimizer ·
│       │                   #   realtime · strategy · trading · waitlist
│       ├── components/     # 도메인 종속 UI — ★화면 컴포넌트의 기본 자리다
│       ├── api.ts          # API 호출 함수 + Query Key Factory
│       ├── hooks.ts        # React Query 래핑 훅 + 비즈니스 로직
│       ├── schemas.ts      # Zod 스키마 + z.infer 타입 추출
│       ├── store.ts        # 도메인 전용 Zustand (필요 시)
│       └── types.ts        # API Request/Response 타입
├── hooks/                  # 도메인 무관 공통 훅 (useDebounce 등)
├── lib/                    # Utility: API 클라이언트, 유틸리티, 상수
└── store/                  # Global State: 앱 전역 Zustand (Theme 등)
```

### ★ `app/**/_components/` 는 언제 쓰나 ([ADR-035](../../docs/adr/035-fe-component-ownership.md))

2026-08-16 에 `_components/` **234파일을 `features/` 로 옮겼다.** 금지는 아니지만 기본이 아니다.

| 상황                                    | 자리                                                            |
| --------------------------------------- | --------------------------------------------------------------- |
| 두 개 이상 라우트가 쓴다                | `features/<domain>/components/` 또는 `components/`(도메인 무지) |
| 한 라우트 전용 + 도메인 로직 있음       | `features/<domain>/components/`                                 |
| 한 라우트 전용 + 순수 표현 + 5파일 미만 | `app/<route>/_components/` 허용                                 |

★**의심스러우면 feature 로 보내라.**

### ★ 레이어 경계는 **Biome 이** 집행한다 ([ADR-039], 2026-08-22)

`features/`·`components/`·`lib/`·`hooks/`·`store/` 에서 **`@/app/*` 를 import 하면 error** 다.
`app/` 은 최상위 조립층이라 아래 층이 그것을 거슬러 참조하면 라우트를 못 옮긴다.

| 우회 갈래 | 집행자 |
| --- | --- |
| 정적 `import`·`export from` | `biome.jsonc` `style/noRestrictedImports` |
| 동적 `import("@/app/x")` | 같은 규칙 — Biome 은 동적 import 를 **네이티브로** 본다 |
| 템플릿 리터럴 ``import(`@/app/${x}`)`` | ⚠️**없다.** ESLint 제거로 이 갈래는 **사람이 지킨다** |

### ★ 컴포넌트를 옮기기 전에 — 검사기 스코프를 먼저 재라

`src/__tests__/no-raw-enum-labels.test.ts` 는 스캔 대상을 **디렉터리 목록**으로 정의하고
없는 디렉터리를 조용히 건너뛴다. 목록을 안 고치고 옮기면 **스코프가 비고 테스트는 초록**이다.

```bash
cd apps/web && node scripts/canon-scope-census.mjs   # 이동 전후로 돌려 수치를 대조한다
```

## 5. 반응형 — 본문은 §10

> 반응형 규칙 본문은 병합된 **§10**(구 `nextjs-shared.md` §4)에 있다. 절 번호는
> 외부 참조(ADR·reference)가 걸려 있어 당기지 않는다.

---

## 6. Next.js 16 차용 패턴 (FastAPI BE 조합)

> QuantBridge 는 FastAPI BE + Next.js FE 구조라 Server Actions / Drizzle 패턴은 직접 적용 불가. 아래 3 패턴만 차용.

### Server Component vs Client Component 경계

- 기본값 = Server Component. `"use client"` 는 진짜 필요할 때만 (이벤트 핸들러, `useState/useEffect`, `useAuthCtx` 등).
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

---

## 7. Next.js 16 필수 패턴

- `params`, `searchParams`는 **`Promise<>`** 타입 → `await` 필수
- `middleware.ts` 대신 **`proxy.ts`** 사용
- `node_modules/next/dist/docs/` 참조 필수

```typescript
// ✅ Next.js 16
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail id={id} />;
}
```

---

## 8. Zod v4

- `import { z } from "zod/v4"` 필수 (v3 경로 `"zod"` 금지)
- **Schema First:** 타입 중복 선언 금지 → `z.infer<typeof schema>` (필요 시 `z.input`)로 추출하여 재사용
- **Transform 강제:** Form 입력 타입(String)과 API 요청 타입(Number 등)이 다를 경우, `onSubmit` 내부에서 수동 파싱 금지 → 스키마 레벨에서 `.transform()`으로 일원화

```typescript
// ✅ 스키마에서 변환
const priceSchema = z.string().transform((v) => Number(v));

// ❌ onSubmit에서 수동 변환
const handleSubmit = (data: FormData) => {
  api.create({ price: Number(data.price) }); // 금지
};
```

---

## 9. shadcn/ui v4

- 내부 의존성: `@base-ui/react` (Radix UI 아님)
- `@radix-ui/*` 직접 import 금지
  - **예외 (ADR 009, 2026-04-17):** Nova preset registry에 Base-UI 버전이 미포함된 경우에 한해 `radix-ui` umbrella package 허용. 현재 `form.tsx` 1개 파일이 `Slot`/`Label` 2개 primitive만 사용. Sprint 7d+에서 registry 업데이트 시 Base-UI로 마이그레이션
- 추가: `pnpm dlx shadcn@latest add [component]`
- `components/ui/` 직접 수정 금지 → 래핑 컴포넌트
  - **예외 (ADR 009):** 초기 설치 직후 **1회성 DESIGN.md 토큰 reconciliation** 한해 허용 (Tailwind class 높이/간격 등 시각 토큰만). 비즈니스 로직·prop 시그니처·동작 변경은 여전히 래핑 컴포넌트로 처리

---

## 10. 반응형 (Responsive Design)

### 핵심 원칙: Mobile-First — ★사거리 주의

- **신규 Tailwind 컴포넌트 = mobile-first 필수.** 기본 스타일이 모바일(320px~)이고 `sm:`/`md:`/`lg:` 로 확장한다
- **적용 대상:** 사용자 대면 페이지는 필수. 어드민/내부 도구는 프로젝트 요구사항에 따름

> ★★**2026-08-08 실측 — 이 원칙은 CSS 파일에는 적용돼 있지 않다.** `globals.css` 의
> `@media` **30곳이 전부 `max-width`** 이고 `min-width` 는 **0건**이다(= 100% desktop-first).
> C 이식 CSS 는 `_kit.html`(desktop-first)의 바이트 정본이라 구조적으로 그렇다. 종전 문장
> 「데스크탑 기준으로 먼저 작성하는 방식 금지」는 **레포 절반과 정면으로 어긋나 있었다.**
> ⇒ 규칙의 사거리를 좁힌다:
>
> - **신규 Tailwind 컴포넌트** — mobile-first 필수 (위 항목)
> - **KITPORT(`globals.css` 의 `KITPORT-START`~`KITPORT-END` 센티넬 구간) · 화면 전용 CSS 수정** — 그 파일의 desktop-first 관례를
>   따른다. 한 파일 안에 두 방향을 섞으면 어느 쪽이 이기는지 사람이 못 읽는다
>
> 전면 전환 여부는 [BL-647].

### 브레이크포인트 기준 — ★**Tailwind v4 기본값이 아니다**

`globals.css:204-211` 의 `@theme` 블록이 재정의한다. 종전의 「Tailwind v4 기본값」 표기는
틀렸고, `sm:` 은 실사용 **36건**이라 화면에 실제로 영향을 준다.

| 접두사 | **이 레포** | Tailwind v4 기본 | 주요 용도                                 |
| ------ | ----------- | ---------------- | ----------------------------------------- |
| (없음) | 0px         | 0px              | 모바일 기본                               |
| `sm:`  | **375px**   | ~~640px~~        | 소형 모바일 (사용 36건)                   |
| `md:`  | 768px       | 768px            | 태블릿 · **앱 셸 사이드바 숨김 경계**     |
| `lg:`  | 1024px      | 1024px           | 데스크탑 · **앱 셸 아이콘 레일 경계**     |
| `xl:`  | **1200px**  | ~~1280px~~       | 콘텐츠 그리드 2열화 (사용 1건)            |
| `2xl:` | **1440px**  | ~~1536px~~       | 와이드 (유틸 사용 0건 · raw `@media` 0건) |

★유틸 접두사는 **min-width**, CSS 미디어는 **max-width** 다. 같은 숫자를 반대 방향으로 쓰므로
섞어 읽지 마라. **정확히 그 숫자(768px 등)에서는 둘 다 참**이라 같은 요소를 양쪽에서 숨기면
데드심이 난다 — 2026-08-18 실발화(햄버거는 보이는데 드로어가 `md:hidden`). 셸 쪽 정합은
`min-[769px]:` 로 잡는다. ★**Tailwind v4 의 `max-[1024px]:` 는 `width < 1024`(경계 미포함)로
컴파일**되어 KITPORT `max-width:1024`(포함)와 스택 변형으로 정렬하면 정확히 1024px 에서
off-by-one 이 난다(2026-08-18 postcss 실측) — 경계 포함이 필요하면 raw 미디어 변형
`[@media(min-width:769px)_and_(max-width:1024px)]:` 을 써라(`account-button.tsx` 선례).

★**`900px` 는 더 이상 미등재가 아니다** (2026-08-17 정정, [BL-602] 종결 시 동승).
종전 문장은 「미등재 경계 `@media (max-width: 900px)` 5곳은 [BL-646]」이었는데 [BL-646] 은
**Resolved** 이고 `DESIGN.md §4.3.1` 이 900 을 **콘텐츠 그리드 전용 6번째 경계로 등재**했다.
실사용은 여전히 `globals.css` 의 raw `@media` **5곳**(`:1972`·`:2042`·`:2175`·`:2271`·`:3300`)이고
Tailwind 접두사는 없다 — 위 사다리 표에 행이 없는 이유가 그것이다.

### 앱 셸 고유 값 (정본 `globals.css` · 사본 `DESIGN.md` §10.2/§10.6)

| 값                | `>1024px` | `≤1024px` | `≤768px`         |
| ----------------- | --------- | --------- | ---------------- |
| `--sidebar-w`     | 232px     | 64px      | 0px (→ drawer)   |
| `--topbar-h`      | 60px      | 60px      | 60px             |
| `.page` max-width | 1240px    | 1240px    | 1240px (패딩만↓) |

★셸 경계는 **1024 / 768 둘뿐**이다. 사이드바 접힘은 **순수 CSS** 이고 토글 상태는 없다
(`components/layout/dashboard-sidebar.tsx:3`). 경계 실측 집행 =
`e2e/design-canon-responsive.spec.ts`.

### 완료 체크리스트

> UI 컴포넌트 작성 후 아래 항목을 자가 검증한다.

- [ ] 페이지 레이아웃에 고정 너비(`w-[Npx]`) 없음 — `max-w-[Npx]`는 허용
- [ ] 다열 그리드/플렉스에 모바일 브레이크포인트 적용 (`grid-cols-1 md:grid-cols-N`)
- [ ] 모바일(320px)에서 가로 스크롤 발생하지 않음
- [ ] 텍스트 오버플로우 처리 (`truncate` 또는 `break-words`)
- [ ] 테이블은 `overflow-x-auto` 래퍼로 감싸기

---

## 11. TypeScript 컨벤션 (구 `typescript.md` 병합)

- **Strict 모드 필수**, `any` 사용 엄격히 금지 (부득이한 경우 `unknown` + Type Guard)
- 모든 API 응답 타입은 명시적으로 정의
- 네이밍 — Boolean: `is`/`has`/`should` 접두사 · 이벤트 핸들러: `handle` 접두사 · Props 이벤트: `on` 접두사
- ★파일 케이싱 — **컴포넌트도 kebab-case** 다 (2026-08-22 정정: 종전 문장은 「PascalCase」였고 트리와 반대였다).
  실측 `components/ui/` 제외 `.tsx` **388개 중 372개(96%)가 kebab-case** — `dashboard-sidebar.tsx`·`account-button.tsx`.
  훅은 `use-` 접두사 kebab-case(`use-auth-ctx.ts`), 상수 **값**은 UPPER_SNAKE_CASE.
  ⚠️`biome.jsonc` 에 `useFilenamingConvention` 이 **없다** — 이 축은 기계가 아니라 사람이 지킨다.
- ★**non-null assertion(`!`)은 허용한다 — 린터가 안 막는다.** `noNonNullAssertion` 은 의도적으로
  `off` 다([ADR-039], 실측 291건). 규칙이 틀린 게 아니라 이 트리가 그 스타일이고, **되살릴 때
  쓰라는 autofix 가 `foo!.bar` → `foo?.bar` 로 런타임 의미를 바꾼다** — `!` 는 null 이면 throw,
  `?.` 는 `undefined` 를 반환한다. 백테스트·옵티마이저·트레이딩에 자동 적용하면 에러가 조용한
  `undefined` 가 된다. ⇒ **`biome check --write --unsafe` 를 이 규칙에 걸지 마라.**
  대신 사람이 지킨다 — `!` 는 「그 위 몇 줄에서 non-null 이 이미 보장된 곳」에만 쓴다.
