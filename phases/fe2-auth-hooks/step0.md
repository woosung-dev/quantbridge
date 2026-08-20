# Step 0: geo-l3-signup

## 읽어야 할 파일

- `apps/web/src/lib/auth.ts` — **이번 테스트의 대상** (156줄. 주석 절반이 사고 기록이다)
- `apps/web/src/lib/geo.ts` — `isRestrictedCountry` (진짜를 태운다 — mock 하지 마라)
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

이 파일은 **이 앱의 인증 서버 본체**다([ADR-034] — Clerk 를 대체했다). **테스트는 0건이다.**

★**geo-block L3 은 2026-08-17 까지 한 번도 발화한 적이 없었다** — Clerk 시절 BE 는
`public_metadata.country` 를 읽었는데 **그 값을 넣는 코드가 FE 어디에도 없었다**(grep 0건,
[LESSON-114]). 이 훅이 L3 이 처음으로 **실재하게 된 자리**다. 그런데 그 훅을 재는 테스트가 없다.
**「있다고 여겨진 것이 그 경로를 안 지났다」를 이 레포는 이미 4번 밟았다.**

## 작업

`apps/web/src/lib/__tests__/auth-hooks.test.ts` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식 — 착수 전 CONTROL 이 실측해 통과시킨 배선이다)

훅은 `betterAuth()` 설정 안에 있어 export 되지 않는다. **`auth.options` 로 꺼내 직접 부른다.**

```ts
import { describe, expect, it } from "vitest";
import { auth } from "@/lib/auth";

type CreateBefore = (
  user: Record<string, unknown>,
  context: { headers?: Headers; request?: Request } | null,
) => Promise<{ data: Record<string, unknown> } | undefined>;

// better-auth 1.6.29 실측 — betterAuth() 반환값의 키는 handler/api/options/$context/$ERROR_CODES 다.
const createBefore = (
  auth as unknown as {
    options: { databaseHooks: { user: { create: { before: CreateBefore } } } };
  }
).options.databaseHooks.user.create.before;
```

★**`@/lib/auth` 를 import 해도 DB 에 붙지 않는다** — `new Pool()` 은 **지연 연결**이라
쿼리를 날리기 전에는 소켓을 열지 않는다(착수 전 실측). 이 step 의 훅은 헤더만 읽으므로 DB 를 안 친다.

★**진짜 DB 를 치지 마라.** 이유: 워크트리는 개발 DB 를 1벌 공유하고, 8 lane 이 동시에 돈다.
`auth.api.*` 를 이 step 에서는 **아예 부르지 마라**(step 1 이 spy 로 다룬다).

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. ★**제한 국가는 가입이 거부된다** — `cf-ipcountry: US` 로 `createBefore` 를 부르면 **reject**.
   던져지는 것은 better-auth 의 `APIError` 이고 `status` 가 `"FORBIDDEN"`,
   `body.code` 가 `"GEO_BLOCKED_COUNTRY"` 다.
   ★**`return false` 가 아니라 throw 여야 한다** — 주석이 근거를 적고 있다: `return false` 면
   Better Auth 가 **400 FAILED_TO_CREATE_USER** 를 내서 화면이 「가입에 실패했습니다」라는
   엉뚱한 문장을 보여주고 **차단인지 장애인지 사용자가 구분할 수 없다**(2026-08-17 codex P2)
2. ★**소문자 헤더도 차단된다** — `cf-ipcountry: us` (소문자). `toUpperCase()` 계약이다
3. ★**앞뒤 공백도 차단된다** — `cf-ipcountry: " US "`. `trim()` 계약이다
4. **`x-vercel-ip-country` 도 같은 판정** — 헤더 이름만 바꿔 같은 reject.
   그리고 **`cf-ipcountry` 가 우선**임을 재라(둘 다 주고 cf 쪽만 제한 국가면 reject)
5. ★**허용 국가는 통과하고 country 가 심긴다** — `cf-ipcountry: KR` →
   반환값이 `{ data: { ...user, country: "KR" } }`. **원본 user 필드가 보존**되는지도 단언해라
   (`{ email, name }` 을 넣고 둘 다 살아 있는지)
6. ★**헤더가 없으면 차단하지 않는다** — `context` 가 `null` · `headers` 없음 · 헤더는 있으나
   국가 키가 없음 → 셋 다 통과하고 `country` 가 **`null`**.
   주석이 「헤더가 없으면 `null` — 차단하지 않는다(로컬 개발·기존 호환)」로 못박은 계약이다
7. ★**2글자가 아닌 값은 `null` 로 떨어진다** — `cf-ipcountry: "USA"` · `"U"` · `""` →
   통과 + `country: null`. **`"USA"` 가 차단되지 않는 것이 지금 동작이다** — 고치지 말고 고정해라
8. ★**`context.request.headers` 경로도 산다** — `{ request: new Request("http://x", { headers }) }`
   로 줘도 같은 판정(코드가 `context?.headers ?? context?.request?.headers` 로 둘을 받는다)
9. ★**양성 대조** — `createBefore` 가 함수이고 `auth.options.user.deleteUser.beforeDelete` 도
   함수임을 한 케이스에서 단언한다. 경로 오타로 `undefined` 를 부르며 통과할 수 없게 한다

★**`@/lib/geo` 를 mock 하지 마라** — 진짜 제한 국가 목록(US + EU27 + GB, 29개)을 태워야
L3 이 실제로 무엇을 막는지 재진다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/auth-hooks.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/auth-hooks.test.ts 2>/dev/null | grep -c ' > ')" -ge 7
cd apps/web && pnpm exec eslint src/lib/__tests__/auth-hooks.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 **다음 step 이 쓸 것**을 남겨라 — `auth.options` 접근 타입 별칭과 케이스 수.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/auth.ts` · `src/lib/geo.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**진짜 Postgres 에 붙지 마라** — `auth.api.getSession`·`getToken` 을 부르지 마라.
  이유: 개발 DB 는 워크트리 사이에서 1벌 공유이고 8 lane 이 동시에 돈다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
