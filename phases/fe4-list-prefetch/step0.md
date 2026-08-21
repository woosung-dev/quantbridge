# Step 0: list-prefetch

## 읽어야 할 파일

- `apps/web/src/app/(dashboard)/backtests/page.tsx` (59줄) · `apps/web/src/app/(dashboard)/strategies/page.tsx` (76줄)
  — **이번 테스트의 대상 2개**
- `apps/web/src/features/backtest/list-query.ts` — `buildBacktestListQuery` (헤더에 [BL-786] 전말이 있다)
- `apps/web/src/features/backtest/query-keys.ts` · `apps/web/src/features/strategy/query-keys.ts` — 키 팩토리
- `apps/web/src/features/strategy/sort.ts` — `resolveStrategySort`
- `apps/web/src/features/backtest/components/backtest-list.tsx` · `.../strategy/components/strategy-list.tsx`
  — **클라이언트가 같은 키를 어떻게 만드는지**를 여기서 봐라
- `apps/web/src/app/invite/[token]/__tests__/page.test.tsx` — ★**이 레포의 서버 컴포넌트 테스트
  관용구다**(`const el = await Page({...})` → `renderToStaticMarkup(el)`). 같은 모양으로 써라

## 배경

두 페이지는 **세션 JWT 로 React Query 를 서버에서 prefetch 한 뒤 `HydrationBoundary` 로 넘긴다.**
그 계약의 핵심은 **「서버가 심은 키와 클라이언트가 찾는 키가 같아야 한다」**는 것 하나다.

★★**[BL-786] 이 정확히 그 실패였다** — 종전에는 페이지가 `{limit, offset}` 로, `BacktestList` 가
`{limit, offset, order_by, order}` 로 키잉해서 **hydrate 된 캐시를 클라이언트가 한 번도 쓰지 못했고**
같은 목록이 SSR 에서 한 번 · 브라우저에서 한 번 나갔다. **화면은 안 깨진다 — 값만 두 배로 나간다.**
그래서 이 결함은 렌더 테스트로도 e2e 로도 안 잡히고, **키를 직접 비교해야만** 잡힌다.

★**착수 전 CONTROL 실측 (2026-08-21) — 두 페이지의 상태가 다르다. 그대로 관측해서 박아라:**

| 축          | `backtests/page.tsx`                                                                                               | `strategies/page.tsx`                                                                                                                                                                   |
| ----------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 쿼리 생성   | ★**공용 순수 함수** `buildBacktestListQuery(orderBy, order)` — 클라(`backtest-list.tsx:75`)도 **같은 것**을 부른다 | ★**페이지가 객체 리터럴로 직접 조립**(`{limit: PAGE_SIZE, offset: 0, is_archived: false, ...sort}`). 클라(`strategy-list.tsx:77`)도 **자기 리터럴 + 자기 `PAGE_SIZE`** 로 따로 조립한다 |
| 정렬 정규화 | `resolveBacktestSort` (list-query.ts 안)                                                                           | `resolveStrategySort` (sort.ts) — **양쪽이 공유한다**                                                                                                                                   |

⇒ **backtest 는 [BL-786] 처방이 구조적으로 적용됐고, strategy 는 값만 같고 생성자가 둘이다.**
이 테스트는 **지금 두 키가 실제로 같다는 것**을 고정한다. 값이 같은지를 재라 — 구조가 다르다는
사실은 주석으로 남기고, **「고쳐야 한다」는 단언을 테스트로 쓰지 마라**(대상 무변경이 이 lane 의 계약이다).

## 작업

`apps/web/src/app/(dashboard)/__tests__/list-prefetch.test.tsx` **하나**를 신설한다.
두 페이지를 각각 default import 해서 `await Page({ searchParams: Promise.resolve({...}) })` 로 호출한다.

**모킹 지침** — `@/lib/auth-server` 의 `getServerAuth` 와 각 도메인의 `api` 모듈(`listBacktests` ·
`listStrategies`)만 mock 한다. `@tanstack/react-query` 는 **mock 하지 마라** — 실제 `QueryClient` 로
prefetch 한 뒤 `queryClient.getQueryCache().getAll()` 에서 **실제로 심긴 키**를 꺼내 비교하는 것이
이 테스트의 요점이다(mock 하면 키가 심기지 않아 항진명제가 된다).

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★**backtest — 서버가 심은 키 == 클라이언트가 만드는 키.** `searchParams` 를
   `{order_by: "sharpe_ratio", order: "asc"}` 로 주고 페이지를 호출한 뒤, 캐시에 심긴 키가
   `backtestKeys.list(uid, buildBacktestListQuery("sharpe_ratio", "asc"))` 와 **깊은 값 비교로 같다**.
   ★**클라이언트 키를 손으로 적어 넣지 마라** — 그러면 페이지만 재고 계약을 안 잰다. `backtest-list.tsx`
   가 실제로 부르는 그 함수를 테스트도 불러서 비교해라
2. ★★**strategy — 같은 비교를 `strategyKeys.list(uid, {limit:20, offset:0, is_archived:false, ...resolveStrategySort(...)})`
   로** 한다. 위 표대로 **생성자가 둘**이므로, 이 케이스가 두 리터럴이 어긋나는 순간을 잡는 유일한 축이다.
   그 사정을 주석 2줄로 남겨라
3. **정렬 파라미터 미지정** — `searchParams` 가 `{}` 일 때 두 페이지 모두 기본 정렬로 키가 잡힌다
   (값은 각 `resolve*Sort` 를 불러서 얻어라 — 기대값을 손으로 적지 마라)
4. ★**배열 파라미터는 첫 값만 쓴다** — `{order_by: ["total_return", "무시될값"]}` 을 주면
   `"total_return"` 하나만 반영된다. 두 페이지 각각
5. ★**알 수 없는 정렬 값은 기본값으로 떨어진다** — `{order_by: "존재하지않는컬럼"}` 이 던지지 않고
   기본 정렬 키를 만든다. 두 페이지 각각
6. ★★**`token` 이 없으면 prefetch 를 아예 안 한다** — `getServerAuth` 가 `{userId: "u1", token: null}`
   을 주면 `listBacktests`/`listStrategies` 가 **0회 호출**이고 캐시가 비어 있다.
   (로그인 전 사용자에게 인증 요청을 내보내지 않는다는 계약이다)
7. ★★**prefetch 가 던져도 페이지는 렌더된다** — api mock 을 `rejectedValue` 로 두고
   `renderToStaticMarkup` 이 성공한다. **BE 가 죽어도 화면은 나가야 한다**(silent degrade).
   ★이때 콘솔로 새는 것이 있으면 `summary` 에 적어라
8. ★**`userId` 가 `null` 이면 `"anon"` 으로 키잉한다** — 키의 첫 인자가 `"anon"` 이다.
   ([LESSON-005] 의 계약 — uid 가 키 identity 다). 두 페이지 각각
9. **prefetch 에 넘어간 토큰이 `getServerAuth` 가 준 그 값이다** — api mock 의 호출 인자에서 확인한다.
   (엉뚱한 토큰으로 남의 목록을 심는 사고를 잡는다)
10. ★**두 페이지가 `HydrationBoundary` 를 반환한다** — 반환 엘리먼트에 `dehydrate` 결과가 실려 있고
    (`props.state` 가 존재), 자식으로 각 목록 컴포넌트가 있다. 목록 컴포넌트는 mock 해서
    식별 가능한 마커를 렌더하게 해도 좋다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/(dashboard)/__tests__/list-prefetch.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/(dashboard)/__tests__/list-prefetch.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 10
cd apps/web && pnpm exec eslint 'src/app/(dashboard)/__tests__/list-prefetch.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★경로에 `(dashboard)` 괄호가 있으므로 **작은따옴표**로 감쌌다. `\"` 로 바꾸지 마라 — 러너가 AC 를
`bash -c` 로 돌리는데 거기서 `syntax error near unexpected token '('` 로 죽는다.
★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **1·2번 케이스에서 실제로 비교한 키의 모양**을 남겨라.
   ★**예상과 달랐던 것이 있으면 반드시 적어라** — 위 표는 CONTROL 이 잰 것이지만 틀릴 수 있다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`apps/web/src/app/(dashboard)/{backtests,strategies}/page.tsx` 를 수정하지 마라.**
  이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함을 발견하면
  **고치지 말고 `summary` 에 적거나 `blocked` 로 멈춰라**
- ★**`features/**` 의 어떤 파일도 수정하지 마라\*\* — 키 팩토리·정렬 모듈은 이미 테스트가 있고
  이 lane 소유가 아니다
- ★`apps/web/vitest.config.ts` · `apps/web/tests/setup.ts` **무변경.** 이유: 8 lane 이 동시에 도는
  중이라 공유 파일을 건드리면 병합 충돌이 난다
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라. 이유: 그것이 lane 사이의
  유일한 공유 파일이 된다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
