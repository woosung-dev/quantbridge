# Frontend Rules (Next.js 16)

> ★**이 파일은 모든 하네스 lane 프롬프트에 전문 주입된다**(`tools/harness/execute.py:44`). 담는 것은 루트
> [`AGENTS.md`](../../AGENTS.md) §8 기준 **「구조·경계·금지」뿐**이고 예제·절차·이력은
> [ADR-039](../../docs/adr/039-frontend-biome.md)(lint) · [`DESIGN.md`](../../DESIGN.md)(반응형·앱 셸) · **레포 실물**이 갖는다.
> ★**절 번호·`H-N` id 는 재배치하지 않는다** — `docs/lessons.md`·ADR-009/031/035/039·`biome.jsonc`·코드 주석 26파일이 인용한다.

## 1. Tech Stack

| 항목            | 기술                                                                      |
| --------------- | ------------------------------------------------------------------------- |
| Framework       | Next.js 16 (App Router)                                                   |
| Language        | TypeScript Strict                                                         |
| Styling         | Tailwind CSS v4 (CSS-first, 설정 파일 없음) + shadcn/ui v4                 |
| Package Manager | `pnpm`                                                                    |
| Server State    | React Query (`@tanstack/react-query`)                                     |
| Client State    | Zustand                                                                   |
| Form            | `react-hook-form` + `zod v4` — resolver 는 자체 `lib/zod-v4-resolver.ts` (`@hookform/resolvers` 미설치) |
| Auth            | Better Auth (`better-auth`, 자체 호스팅 — ADR-034)                        |
| 배포            | 오라클 A1 + Cloudflare Tunnel · `output: "standalone"` — ★**Vercel 이 아니다**(서버에 Node 가 없어 `next start` 를 못 쓴다). 절차 = [`frontend-deploy.md`](../../docs/operations/frontend-deploy.md) |

## 2. 인증 — Better Auth ([ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

> Next.js 16 · Zod v4 · shadcn v4 · 반응형 · TS 컨벤션은 **§7~§11**(구 `nextjs-shared.md`, ADR-027 병합).

★**이 앱이 인증 서버 본체다.** `/api/auth/[...all]` 이 로그인·세션·JWKS 를 낸다.

- 인증 보호 = **`proxy.ts`** 하나. 공개 라우트가 아니면 `auth.api.getSession()` 으로 **완전 검증**한다.
  **이유:** 검증을 라우트마다 흩으면 새 라우트가 조용히 공개된다. 집행 = `src/__tests__/proxy-gate.test.ts`
- 클라이언트는 **`useAuthCtx()` 하나만**(`hooks/use-auth-ctx.ts` → `uid`/`userId`/`isSignedIn`/`user`/`getToken`).
  `useSession()`·`getAuthToken()` 을 컴포넌트에서 직접 부르지 마라 — 공급자 교체가 그 seam 하나로 끝난 이유다.
  표시용 이름·이메일도 `user`를 통해 받는다. 집행 = `hooks/__tests__/auth-ctx-boundary.test.ts`
- 서버 컴포넌트 = `getServerAuth()`(`lib/auth-server.ts`) → `{ userId, token }`
- 직접 JWT 파싱 금지 (예외: `auth-client.ts` 가 **캐시 수명 계산에만** `exp` 를 읽는다)
- ★**`getSessionCookie()` 를 인증 게이트로 쓰지 마라** — 쿠키 존재만 본다(공식 문서가 "THIS IS NOT SECURE!").
  `proxy.ts` 의 `/` → `/strategies` **UX 리다이렉트** 전용. 집행 = `proxy-gate.test.ts` 의 `not.toHaveBeenCalled()`

## 3. 컴포넌트 & 상태 관리 패턴

- **Thin Component** — 페이지/UI 컴포넌트 안에 비즈니스 로직 금지. 로직은 `features/[domain]/hooks.ts` 로 분리
- **상태 3단계** — Server State = React Query · Client Global = Zustand(`store/ui-store.ts`) · Client Local =
  `useState`. ★사이드바 접힘은 상태가 아니라 **순수 CSS** 다(§10) — 토글 store 를 새로 만들지 마라
- **React Query** — Query Key 하드코딩 금지 → 도메인별 `query-keys.ts` 팩토리(첫 인자 = `userId`). API 호출은
  `features/[domain]/api.ts` 에 모은다(★예외 **4곳** — `app/share/backtests/[token]/*` 2 · `test-order-webhook.ts` · `lib/auth.ts` 가 자체 `apiBase` 보유. 2026-08-30 실측으로 3→4 정정). 재는 것 없음
- **에러 핸들링** — 라우트 경계는 `error.tsx`(§6)가 이미 ErrorBoundary 다. 이 규칙이 말하는 것은 **컴포넌트
  내부의 `if (isLoading)`/`if (error)` 워터폴을 `Suspense` 로 걷으라**는 것이다. ★규칙이지 현황이 아니다
  (조기 반환 15건 · `<Suspense>` 1곳). 기존 위반을 선례로 읽지 마라

### React Hooks 안전 규칙 (LESSON-004/005/006 승격)

> 셋 다 실전 사고(CPU 100% 무한 루프 / cache 무효화 폭주 / Compiler 충돌)에서 승격됐다. 예외는 별도 ADR 로 기록한다.
> ★**셋 다 [ADR-039] 로 기계 방어선을 잃었다**(무엇을 왜 = 그 ADR §무엇을 잃었나 ⑴⑵⑶).
> **규칙은 유효하고, 지키는 주체가 도구에서 사람으로 바뀐 것이다.**

**H-1. `useEffect` dep 에 불안정한 참조 객체 금지** — React Query `data` · Zustand selector 결과 ·
RHF `watch()` · Zod `.parse()` 결과. **이유:** Fast Refresh / StrictMode 더블 인보크 / 부모 재렌더에서
참조가 흔들려 `setState` → 재렌더 → 새 참조 → 무한 루프. **dev 에서만 재현되므로 vitest jsdom 은 못 잡는다.**
**대신** render-time clamp/compare(`Math.min(index, len - 1)`) · scalar dep(`[items.length]` > `[items]`) · 공식 "reset state on prop change"(`if (prev !== curr) setState(...)`).

- ⚠️남은 기계 방어선은 둘뿐 — `useExhaustiveDependencies`(**빠진 dep 만**, `biome.jsonc:65`)와
  `useHookAtTopLevel`. ★후자는 `biome.jsonc` 에 **이름이 없다**: `domains.react: "recommended"`(`:54`)
  한 줄로만 켜지므로 그 줄을 지우면 **조용히 함께 죽는다**
- **PR 규약** — hooks 를 건드린 PR 은 **dev server live smoke 를 사람이 돌린다.** ⚠️`live-smoke.yml` 은 이 규약의
  자동화가 **아니다**: hooks 판별식이 0줄(경로 glob 뿐)이고 재는 것은 **공개 5라우트의 예기치 않은
  `console.error` 개수**이며 authed 훅은 0회 실행된다. **「green 이니 훅이 안전하다」로 읽지 마라**

**H-2. React Query `queryKey` 에 JWT accessor(`getToken`) 직접 포함 금지** — 함수 참조도, `await getToken()`
결과도. **이유:** `getToken` 은 매 렌더 새 함수 참조라 queryKey identity 가 붕괴해 cache 무효화가 폭주한다.
**대신** `userId` 를 팩토리 첫 인자로(`strategyKeys.list(userId, query)`) + 로그아웃 방어 `userId ?? "anon"` sentinel.

- ⚠️**기계 방어선 0** — `@tanstack/eslint-plugin-query` 가 제거됐고 Biome 대응 규칙이 **0건**이다. 리뷰에서 봐야 한다

**H-3. render body 에서 `ref.current = value` 대입 금지** (React 공식 예시를 따라도 안 됨).
**이유:** Compiler 의 재실행/메모이제이션 가정과 충돌한다. **대신 deps 배열 없는 sync `useEffect`** 로 옮긴다
(매 commit 실행 — render 직후 commit phase 라 기능상 동일). Debouncer 표준 = `useRef` + 그 `useEffect` +
timeout 콜백에서 `ref.current` 읽기. 실물 = `features/strategy/draft.ts:157` · `features/realtime/realtime-bridge.tsx:35`.

- ⚠️**기계 방어선 0** — Biome 대체분 `nursery/useReactCompiler` 는 **한글 파일에서 panic** 한다.
  ★이 항목은 「지금의 버그 방지」가 아니라 **나중에 켤 때를 위한 대비**다 — React Compiler 는 `next.config.ts` 에 꺼져 있다

## 4. Directory Structure (FSD Lite)

> 새 기능은 반드시 아래 구조로 배치한다. ★**배치를 재는 기계는 거의 없다** — 예외 둘은
> `app/(dashboard)/__tests__/thin-routes.test.tsx` 의 **7개 dashboard route**와
> `app/__tests__/public-thin-routes.test.ts` 의 pricing·invite·share route다. 둘은 「metadata/params +
> 단일 feature 위임」을 집행한다. 그 밖의 배치는 여전히 사람이 본다(2026-08-30 정정).

```
src/
├── app/          # 조립층: 라우트·레이아웃·loading·error·metadata + feature 조립
│                 #   ★비즈니스 로직 금지. 화면을 그리는 컴포넌트도 여기 소유가 아니다
├── components/   # 도메인을 **모르는** 공통 UI 만 (ui/ layout/ legal/ charts/ monaco/ …)
│                 #   ★ui/ = shadcn 이식분, 직접 수정 금지(§9) · lint·format 게이트 **밖**이다
├── features/     # ★Business Layer: 도메인 단위 모듈 (현재 12종 — `ls src/features`)
│                 #   <domain>/ = components/(★화면 컴포넌트의 기본 자리) api.ts query-keys.ts
│                 #               hooks.ts schemas.ts store.ts types.ts — 필요한 것만
├── hooks/        # 도메인 무관 공통 훅 (use- 접두사 kebab-case)
├── lib/          # API 클라이언트 · 유틸 · 상수
├── store/        # 앱 전역 Zustand
├── styles/       # ★globals.css 는 여기다 — `app/globals.css` 는 없다 (§10)
├── __tests__/    # 트리 전체를 훑는 검사기 (design-canon-* · proxy-gate 등)
└── proxy.ts      # Next 16 — `middleware.ts` 가 아니다
```

**★`app/**/_components/` 는 언제 쓰나** ([ADR-035](../../docs/adr/035-fe-component-ownership.md)) — 두 라우트 이상이
쓰거나 도메인 로직이 있으면 `features/<domain>/components/`(도메인을 모르면 `components/`).
`app/<route>/_components/` 는 **한 라우트 전용 + 순수 표현 + 5파일 미만**일 때만 허용하고, 현재 실측 **0건**이다.
★**의심스러우면 feature 로 보내라.**

**★레이어 경계 — 아래 층은 `app/` 을 import 하지 않는다** ([ADR-035]) — `features/`·`components/`·`lib/`·
`hooks/`·`store/` 에서 **`@/app/*` 를 import 하면 error** 다(`biome.jsonc:89` `noRestrictedImports`, 정적·동적
`import()` 를 한 규칙이 같이 본다). **이유:** `app/` 은 최상위 조립층이라 아래 층이 거슬러 참조하면 라우트를
못 옮긴다. ⚠️템플릿 리터럴 ``import(`@/app/${x}`)`` 갈래와 **역방향**(`app/` 안에 로직·화면 컴포넌트를 두는 것)은
**아무도 안 잰다.**

**★공유층 역방향 경계** — `components/**`·`lib/**` 는 `features/**` 를 import 하면 error다
(`biome.jsonc` override, alias·상대 경로 모두). 도메인 코드가 필요해지면 shared를 넓히지 말고 해당
`features/<domain>/` 소유로 옮긴다. 테스트는 예외다.

**★컴포넌트를 옮길 때** — `src/__tests__/no-raw-enum-labels.test.ts` 는 스캔 대상을 디렉터리 목록
(`SCOPE_MARKERS`)으로 정의하고 사라진 디렉터리를 만나면 **throw 한다**(`:213`). 목록을 함께 고쳐라.
이동 전후 대조 = `cd apps/web && node scripts/canon-scope-census.mjs`.

## 5. 반응형 — 본문은 §10

> 절 번호는 외부 참조가 걸려 있어 당기지 않는다.

## 6. Next.js 16 패턴 (FastAPI BE 조합)

> FastAPI BE + Next.js FE 구조라 Server Actions / Drizzle 패턴은 직접 적용 불가.

- 기본값 = **Server Component**. `"use client"` 는 진짜 필요할 때만(이벤트 핸들러 · `useState/useEffect` ·
  `useAuthCtx`) 그리고 **말단(leaf) 컴포넌트에만** — layout/page 파일에 금지
- Server Component 는 Client Component import 가능, **반대는 금지**
- Server Component 에서 자체 API Route `fetch()` 호출 금지 — FastAPI BE 직접 호출(`features/[domain]/api.ts`)
- **`error.tsx`** — 그룹 루트 `app/(dashboard)/error.tsx` 가 그 아래 라우트를 **전부 덮는다.** 라우트마다 만들지 마라
  — 고유한 복구 문구·동작이 필요할 때만 자기 것을 둔다. `"use client"` + `reset` 필수. ★예제는 옆 라우트를 복사해라
- **실패 처리 SSOT** — `features/*/api.ts` 는 `apiFetch<T>()` + Zod `.parse()` 로 payload 를 반환하고 실패는
  `lib/api-client.ts` 의 `throw new ApiError(...)` 로 전파한다. UI 는 React Query `isError` + `describeApiError()`.
  ★~~`ActionResult<T>`~~ 는 **2026-08-24 삭제**(레포에 존재한 적 없음 · 원문 `git show 6784fceb:apps/web/AGENTS.md`)

## 7. Next.js 16 필수 패턴

- `params`·`searchParams` 는 **`Promise<>`** → `await` 필수 · `middleware.ts` 대신 **`proxy.ts`** ·
  버전 고유 API 는 `node_modules/next/dist/docs/` 를 열어 확인한다(설치본이 정본)

## 8. Zod v4

- **`import { z } from "zod/v4"` 로 통일한다.** ★일관성 규약이지 정합성 규칙이 아니다 — `zod@4` 에서 bare
  `"zod"` 는 `"zod/v4"` 와 **동일 객체**이고(v3 는 별도 서브패스 `zod/v3`) **재는 것이 없다**. 현재 예외 =
  수기 2건(`features/{realtime,trading}/schemas.ts`) + orval 생성물([ADR-031] 승인 · 검사 제외)
- **Schema First** — 타입 중복 선언 금지. `z.infer<typeof schema>`(필요 시 `z.input`)로 추출해 재사용
- **수동 파싱 금지** — Form 입력(String) ↔ API 요청(Number) 변환을 `onSubmit` 안에서 하지 마라. 스키마 레벨에서
  일원화한다 — 이 트리의 관용구는 **`z.coerce.number()`** 다

## 9. shadcn/ui v4

- 내부 의존성은 `@base-ui/react`(Radix UI 아님). **`@radix-ui/*` 직접 import 금지** —
  예외([ADR-009](../../docs/adr/009-shadcn-v4-form-radix-exception.md)) = registry 에 Base-UI 판이 없을 때의
  `radix-ui` umbrella 뿐이고, 현재 `form.tsx` 1파일이 `Slot`/`Label` 2 primitive 만 쓴다. 추가는 `pnpm dlx shadcn@latest add [component]`
- **`components/ui/` 직접 수정 금지** → 래핑 컴포넌트로 확장. 예외(ADR-009) = DESIGN.md 토큰 reconciliation 이고
  **시각 토큰(Tailwind class)만**이다 — 비즈니스 로직·prop 시그니처·동작 변경은 래핑으로.
  ★제약은 **횟수가 아니라 범위**다(`shadcn add` 마다 반복된다)
- ⚠️**이 금지를 재는 것은 없다.** `biome.jsonc:29` 의 `!src/components/ui` 는 **Biome 이 그 파일을 고치는 것**을
  막는 것이라 방향이 반대이고, 부작용으로 그 디렉터리는 **lint·format 게이트 밖**에 있다

## 10. 반응형 (Responsive Design)

- **신규 Tailwind 컴포넌트 = mobile-first 필수.** 기본이 모바일(320px~)이고 `sm:`/`md:`/`lg:` 로 확장한다
- ★CSS 정본 파일은 **`src/styles/globals.css`** 다(`app/globals.css` 는 없다). 그 안의 **KITPORT
  (`KITPORT-START:966`~`KITPORT-END:1876`)·화면 전용 CSS** 는 **desktop-first 관례**(폭 미디어 31곳 중 30곳이
  `max-width`)를 따른다 — 한 파일에 두 방향을 섞으면 사람이 못 읽는다. 전면 전환은 [BL-647]
- ★**KITPORT 구간엔 주석 한 줄도 넣지 마라** — `src/__tests__/design-canon-kit-port.test.ts` 가 `_kit.html` 과
  **주석까지 포함해** 대조한다. §10 에서 **유일하게 CI 가 집행하는 축**이다

**브레이크포인트 — ★Tailwind v4 기본값이 아니다.** `globals.css:204-211` 의 `@theme` 이 재정의한다:
`sm:` **375**(기본 640) · `md:` 768(**앱 셸 사이드바 숨김 경계**) · `lg:` 1024(**앱 셸 아이콘 레일 경계**) ·
`xl:` **1200**(기본 1280 · 콘텐츠 그리드 2열화) · `2xl:` **1440**(기본 1536 · 실사용 0건).

★**유틸 접두사는 min-width, CSS 미디어는 max-width 다** — 같은 숫자를 반대 방향으로 쓴다. **정확히 그
숫자(768px 등)에서는 둘 다 참**이라 같은 요소를 양쪽에서 숨기면 **데드심**이 난다(2026-08-18 실발화 —
햄버거는 보이는데 드로어가 `md:hidden`). ★Tailwind v4 의 `max-[1024px]:` 는 `width < 1024`(**경계 미포함**)로
컴파일돼 KITPORT `max-width:1024`(포함)와 어긋난다. ⇒ 셸 정합은 **`min-[769px]:` / `min-[1025px]:`** 로 잡는다
(`dashboard-shell.tsx:54` · `mobile-nav.tsx:42`, 회귀 = `layout/__tests__/dashboard-shell.test.tsx:159`).
유틸로 경계 포함이 안 되면 `globals.css` 에 평범한 raw 규칙을 써라(`:4017` 선례).

**앱 셸 · 900px · 완료 체크리스트의 정본은 [`DESIGN.md`](../../DESIGN.md) 다** — 앱 셸 값(`--sidebar-w` 232/64/0 ·
`--topbar-h` 60 · `.page` 1240px)과 **셸 경계가 1024/768 둘뿐**이라는 사실 = **§10.2·§10.6** · `900px` = **§4.3.1** ·
완료 체크리스트 = **§4.3.2**(고정 너비 `w-[Npx]` 금지 · 다열 그리드에 모바일 브레이크포인트 · 320px 무횡스크롤 ·
텍스트 오버플로 처리 · 테이블 `overflow-x-auto` 래퍼 — 기계 집행 **0/5**).
⚠️`e2e/design-canon-responsive.spec.ts` 는 **CI 에서 안 돈다** — 로컬에서 직접 돌려라.

## 11. TypeScript 컨벤션 (구 `typescript.md` 병합)

- **Strict 필수** — `tsconfig.json` 은 `noUncheckedIndexedAccess`·`noImplicitOverride` 까지 켠다. 집행 = CI `tsc --noEmit`
- `any` 금지 (부득이하면 `unknown` + Type Guard). ⚠️**기계로는 경고일 뿐이다** — `noExplicitAny` 는 severity
  **warn** 이고 CI 의 `biome check .` 에 `--error-on-warnings` 가 없어 **`any` 를 넣어도 rc=0** 이다
- 모든 API 응답 타입은 명시적으로 정의 (재는 것 없음)
- 네이밍 — Boolean `is`/`has`/`should` · 핸들러 `handle` · Props 이벤트 `on` 접두사.
  ⚠️Biome 에 **의미 접두사를 보는 규칙이 없다**(`useNamingConvention` 은 case style 만 본다)
- ★파일 케이싱 — **컴포넌트도 kebab-case** 다. 훅은 `use-` 접두사 kebab-case(`use-auth-ctx.ts`), 상수 **값**은
  UPPER_SNAKE_CASE. ⚠️`biome.jsonc` 에 `useFilenamingConvention` 이 **없고** preset 으로도 안 켜진다
- ★**non-null assertion(`!`)은 허용한다 — 린터가 안 막는다.** `noNonNullAssertion` 은 의도적으로 `off` 다
  (`biome.jsonc:79`) — 이 트리가 그 스타일이다. ⇒ **`biome check --write --unsafe` 를 이 규칙에 걸지 마라**: autofix 가
  `foo!.bar` → `foo?.bar` 로 **런타임 의미를 바꾼다**(`!` 는 throw, `?.` 는 `undefined`). 근거 = [ADR-039] §`noNonNullAssertion`
