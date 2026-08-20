# Step 0: public-and-geo-verdict

## 읽어야 할 파일

- `apps/web/src/proxy.ts` — **이번 테스트의 대상** (110줄 전량. 목록 주석이 근거다)
- `apps/web/src/lib/route-matcher.ts` — 목록을 컴파일하는 술어 (14줄)
- `apps/web/src/lib/geo.ts` — `isRestrictedCountry` (제한 국가 판정)
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

`proxy.ts` 는 **이 앱의 인증 경계**다([ADR-034] 가 Clerk 미들웨어를 대신한 자리).
공개 라우트가 아닌 모든 요청에서 세션을 **DB 까지 검증**하고, 제한 국가를 `/not-available` 로 보낸다.
**테스트는 0건이고 어떤 테스트도 이 파일을 import 하지 않는다**(2026-08-21 전이 폐포 실측).

목록 두 개(`isPublicRoute` · `isGeoExemptRoute`)는 **모듈 private** 이라 밖에서 못 부른다.
그래서 이 lane 은 목록이 아니라 **`proxy()` 자체를 부른다.**

★**이 파일의 주석이 계약을 적고 있다** — 「공개 라우트에서 DB 를 안 치는 것이 목적이다(CI 의 공개
e2e 는 DB 없이 돈다)」. 그 문장이 참인지 아무도 재고 있지 않다. 이 step 이 그것을 잰다.

## 작업

`apps/web/src/__tests__/proxy-gate.test.ts` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식 — 착수 전 CONTROL 이 실측해 통과시킨 배선이다)

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const getSession = vi.fn();
vi.mock("@/lib/auth", () => ({
  auth: { api: { getSession: (...a: unknown[]) => getSession(...a) } },
}));

const getSessionCookie = vi.fn();
vi.mock("better-auth/cookies", () => ({
  getSessionCookie: (...a: unknown[]) => getSessionCookie(...a),
}));

const req = (path: string, headers: Record<string, string> = {}) =>
  new NextRequest(new URL(`http://localhost:3000${path}`), {
    headers: new Headers(headers),
  });
```

★**`@/lib/auth` 를 반드시 mock 해라. 이유:** 진짜 모듈은 `new Pool()` 로 Postgres 커넥션 풀을
만들고 `auth.api.getSession` 이 DB 를 친다. 워크트리에서 DB 를 겨누면 다른 lane 과 개발 DB 를 다툰다.

★**`NextRequest` 를 손수 만든 스텁으로 바꾸지 마라. 이유:** `proxy()` 는 `req.nextUrl.clone()` 과
`NextResponse.redirect` 의 실제 동작(307 + `location` 헤더)에 의존한다. 가짜 객체로 재면
**리다이렉트가 실제로 나가는지**를 재지 못하고 테스트가 자기 스텁을 재게 된다.
CONTROL 이 착수 전에 `next/server` 가 vitest 에서 resolve 되고 3케이스가 green 임을 실측했다.

### 최소한 이 아홉을 덮어라 (케이스 ≥9)

1. ★**공개 라우트는 세션 조회를 0회 한다** — `/`·`/sign-in`·`/sign-up`·`/waitlist`·`/pricing`·
   `/maintenance`·`/disclaimer`·`/terms`·`/privacy` 를 parametrize 로 돌려
   **매번 `expect(getSession).not.toHaveBeenCalled()`** 와 `res.status === 200`.
   이것이 「CI 의 공개 e2e 는 DB 없이 돈다」 계약이다
2. **와일드카드 공개 라우트** — `/api/auth/session`·`/api/webhooks/tv/abc`·`/invite/tok123`·
   `/share/backtests/tok123`·`/qb-canon-404-probe` 도 세션 조회 0회로 통과
3. ★**음성 대조 — 공개가 아닌 것** — `/strategies`·`/dashboard`·`/orders`·`/api/v1/backtests`
   는 세션 조회를 **탄다**. `getSession` 이 불렸음을 단언해라.
   **이 케이스가 없으면 「전부 통과」인 항진명제가 된다**
4. **제한 국가 + 비면제 → `/not-available`** — `CF-IPCountry: US` 로 `/strategies` 를 치면
   status 307 · `location` 의 pathname 이 `/not-available`
5. **`X-Vercel-IP-Country` 도 같은 판정을 낸다** — 헤더 이름만 바꿔 같은 결과
6. ★**제한 국가여도 면제 목록은 통과** — `/`·`/not-available`·`/disclaimer`·`/terms`·`/privacy`·
   `/waitlist`·`/pricing`·`/maintenance`·`/api/webhooks/x`·`/api/auth/x`·`/share/backtests/x`
   **11개 전건**을 `CF-IPCountry: US` 로 돌려 리다이렉트가 **안 난다**
7. ★★**`/invite/<token>` 은 공개지만 geo 면제가 아니다** — 파일 주석이 「일부러 넣지 않았다」고
   적은 **의도된 비대칭**이다. 헤더 없이는 통과하고, `CF-IPCountry: US` 면 `/not-available` 로 간다.
   두 방향을 다 단언해라
8. **허용 국가는 통과** — `CF-IPCountry: KR` 로 `/waitlist` → 리다이렉트 없음
9. ★**양성 대조 — 대상에 실제로 닿았는지 재라.** `proxy` 의 default export 가 함수이고
   `config.matcher` 가 **2개 패턴**을 갖는지 한 케이스에서 단언한다.
   이것이 없으면 import 오타로 아무것도 안 불린 채 통과할 수 있다

★**국가 코드는 `lib/geo.ts` 를 mock 하지 마라** — 진짜 판정을 태워야 헤더 파싱과 목록이 함께 재진다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/__tests__/proxy-gate.test.ts
cd apps/web && test "$(pnpm exec vitest list src/__tests__/proxy-gate.test.ts 2>/dev/null | grep -c ' > ')" -ge 9
cd apps/web && pnpm exec eslint src/__tests__/proxy-gate.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다
(CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 **다음 step 이 쓸 것**을 남겨라 — `req()` 헬퍼와 mock 두 개의 시그니처, 케이스 수.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/proxy.ts` · `src/lib/route-matcher.ts` · `src/lib/geo.ts` 를 **수정하지 마라.**
  결함을 찾으면 `it.fails(...)` 가 아니라 **`summary` 에 한 줄로 적고 넘어가라**
  (「이 코드가 틀렸다」는 주장은 사람이 코드 대조로 판정한다 — [LESSON-121])
- ★**`apps/web/vitest.config.ts` · `apps/web/tests/setup.ts` 를 건드리지 마라. 이유:**
  8 lane 이 동시에 도는 중이고 그 둘이 유일한 공유 설정이다. 고치면 병합 충돌이 난다
- **공용 헬퍼 모듈(`src/__tests__/_helpers.ts` 같은 것)을 만들지 마라** — 같은 이유다.
  헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- **서버를 띄우지 마라**(`pnpm dev`·`pnpm build`) — 포트가 lane 사이에서 충돌한다
- 커밋하지 마라(커밋은 러너 소관)
