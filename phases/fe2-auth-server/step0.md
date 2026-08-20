# Step 0: server-auth-swallow

## 읽어야 할 파일

- `apps/web/src/lib/auth-server.ts` — **이번 테스트의 대상** (41줄. 주석이 계약 3개를 적고 있다)
- `apps/web/tests/stubs/server-only.ts` — 이 lane 이 성립하는 이유. **읽어라**
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

`getServerAuth()` 는 **구 Clerk `auth()` 의 자리**다([ADR-034]). 서버 컴포넌트가 FastAPI 를
prefetch 할 때 필요한 `{ userId, token }` 을 준다. 호출부는 `app/page.tsx` ·
`(dashboard)/{backtests,strategies}/page.tsx` 셋이다. **테스트는 0건이고 어떤 테스트도 이 파일을
import 하지 않는다.**

이 파일이 주석으로 못박은 **계약 3개**를 아무도 재고 있지 않다:

1. ★**실패를 삼킨다** — 랜딩(`/`)처럼 **공개 라우트에서도 불리는** 함수라, DB 가 없는 환경(CI 의
   공개 e2e)에서 예외가 페이지를 죽이면 안 된다. 여기서의 `null` 은 「보호를 뚫었다」가 아니라
   「프리페치를 못 했다」는 뜻이다
2. ★**두 호출은 서로를 기다리지 않는다**(`Promise.all`) — 순차로 두면 세션 조회 왕복이 토큰 발급
   앞에 그대로 쌓여 SSR prefetch 가 그만큼 늦는다
3. ★**`React.cache` 로 감쌌다** — 한 요청 안에서 두 번 불려도 왕복은 한 번이다

★**이 파일은 최근까지 vitest 에서 import 조차 안 됐다** — `import "server-only"` 가 top-level
throw 였고 `vi.mock` 으로 막히지 않았다. 사전 배치 커밋이 `vitest.config.ts` 에 별칭을 넣어
길을 텄다(2026-08-21 실측). **그 별칭 파일을 건드리지 마라.**

## 작업

`apps/web/src/lib/__tests__/auth-server.test.ts` 를 신설한다.

### 호출 방식

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getSession = vi.fn();
const getToken = vi.fn();

vi.mock("next/headers", () => ({
  headers: async () => new Headers({ cookie: "s=1" }),
}));
vi.mock("@/lib/auth", () => ({
  auth: {
    api: {
      getSession: (...a: unknown[]) => getSession(...a),
      getToken: (...a: unknown[]) => getToken(...a),
    },
  },
}));

// ★`React.cache` 는 요청 스코프 캐시다. 케이스마다 새 모듈 인스턴스를 받아야 앞 케이스의
//   결과가 새지 않는다.
beforeEach(() => {
  vi.resetModules();
  getSession.mockReset();
  getToken.mockReset();
});

const load = async () => (await import("@/lib/auth-server")).getServerAuth;
```

★**`@/lib/auth` 를 반드시 mock 해라. 이유:** 진짜 모듈은 `new Pool()` 로 Postgres 풀을 만들고
`getSession` 이 DB 를 친다. 워크트리는 개발 DB 를 1벌 공유하고 8 lane 이 동시에 돈다.

### 최소한 이 여섯을 덮어라 (케이스 ≥6)

1. **세션 + 토큰 둘 다 있음** — `getSession` → `{ user: { id: "u1" } }`,
   `getToken` → `{ token: "jwt-x" }` ⇒ `{ userId: "u1", token: "jwt-x" }`
2. **세션 없음** — `getSession` → `null` ⇒ `{ userId: null, token: null }`
3. ★**`getSession` 이 throw 해도 삼킨다** — reject 시키면 **throw 하지 않고**
   `{ userId: null, token: null }`. **이것이 「랜딩이 DB 없이 렌더된다」의 계약이다**
4. ★**`getToken` 이 실패해도 `userId` 는 산다** — `getSession` 은 성공, `getToken` 은 reject ⇒
   `{ userId: "u1", token: null }`. **코드가 `getToken` 에만 `.catch(() => null)` 을 단 이유**이고,
   이것이 없으면 토큰 발급 실패가 로그인 상태 자체를 지운다
5. ★**`getToken` 이 `undefined`/`{}` 를 내도 `token: null`** — `issued?.token ?? null` 계약
6. ★★**두 호출이 병렬이다** — `getSession` 을 **느린 promise**(수동 resolve)로 두고,
   `getServerAuth()` 를 부른 **직후(await 전)** `getToken` 이 **이미 불렸는지** 단언해라.
   순차 구현이면 이 시점에 `getToken` 은 0회다. ★이것이 `Promise.all` 계약을 재는 유일한 방법이다 —
   「둘 다 불렸다」만 세면 순차 구현도 통과한다
7. ★**`React.cache` — 한 인스턴스에서 두 번 부르면 왕복은 한 번** —
   같은 모듈 인스턴스에서 `getServerAuth()` 를 연속 2회 부르고 `getSession` 호출 횟수를 재라.
   ★**측정값이 2이면 고치지 말고 `summary` 에 적어라** — `React.cache` 는 요청 스코프가 없는
   테스트 환경에서 다르게 동작할 수 있다. **관측한 것을 적는 것이 이 케이스의 일이다**
8. ★**양성 대조** — `getServerAuth` 가 함수이고 한 번이라도 `getSession` 이 실제로 불렸음을
   단언한다(mock 이 안 걸려 진짜 모듈이 도는 상황을 배제한다)

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/auth-server.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/auth-server.test.ts 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && pnpm exec eslint src/lib/__tests__/auth-server.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **케이스 7 에서 실제로 관측한 `getSession` 호출 횟수**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/auth-server.ts` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**`apps/web/vitest.config.ts` · `apps/web/tests/stubs/server-only.ts` · `tests/setup.ts` 를
  건드리지 마라. 이유:** 8 lane 이 동시에 도는 중이고 그 셋이 유일한 공유 설정이다.
  `server-only` 별칭은 **이미 들어가 있다** — 다시 넣거나 고치면 병합 충돌이 난다
- ★**진짜 Postgres 에 붙지 마라** — `@/lib/auth` mock 없이 돌리지 마라
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
