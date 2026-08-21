# Step 2: 에러·경계 분기 — live-sessions · trading React Query 훅

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/src/features/live-sessions/hooks.ts` — **이번 회차의 대상**
- `apps/web/src/features/trading/hooks.ts` — **이번 회차의 대상**

## 이 lane 이 만드는 파일

- `apps/web/src/features/live-sessions/__tests__/hooks.core.test.tsx`
- `apps/web/src/features/trading/__tests__/hooks.core.test.tsx`

## 착수 전 실측 (2026-08-22 · CONTROL 이 전량 스위트 커버리지로 쟀다)

`live-sessions/hooks.ts` 316 stmt 중 **117 미커버 (63.0%)** · export 15 / `trading/hooks.ts` 217 stmt 중 **63 미커버 (71.0% · 함수 50.0%)** · export 16

## 이 lane 만의 사실

★★**이 lane 은 시작 커버리지가 이미 높다(63%·71%)** — 남은 미커버가 어디인지
  step0 이 **직접 재서** `summary` 에 적어야 한다. 덮인 곳을 또 덮으면 수치가 안 움직인다.
★**순수 함수가 여럿이다** — `liveStateRefetchInterval`·`liveSessionEventsRefetchInterval`·
  `combineLiveSessionPositions`·`closePositionMutationKey`·`computeOrdersRefetchInterval`·
  `useIsOrderDisabledByKs` 는 `renderHook` 없이 부를 수 있는지 먼저 확인해라.
★`ACTIVE_ORDER_STATES`·`OPEN_ORDER_STATES` 는 상수다 — `computeOrdersRefetchInterval` 이
  그 집합을 실제로 쓰는지(활성 주문이 있으면 5초, 없으면 30초) 두 방향 다 단언해라.
★**기존 테스트가 셋 있다** — `close-position.test.tsx`·`cancel-order.test.tsx`·
  `use-open-orders-count.test.tsx`·`live-sessions-list-query-dedupe.test.tsx`. 고치지 마라.

## 작업

**에러와 경계**를 덮는다. 여기가 이 lane 의 값이 나오는 자리다.

1. **`ApiError` 전파** — `apiFetch` 가 throw 하면 래퍼는 그것을 **감싸지도 삼키지도 않고**
   그대로 올린다. `status`·`code` 가 보존되는지 단언해라
2. **스키마 파싱 실패** — 응답이 계약을 어기면 `.parse()` 가 throw 한다. 그것이 **조용히
   통과하지 않는다**는 것이 런타임 파싱을 두는 이유다
3. **`params` 의 `undefined`** — `api-client.ts` 는 `undefined` 값을 쿼리에서 **뺀다**.
   선택 파라미터가 빠졌을 때 URL 에 `key=undefined` 가 안 붙는지 봐라
4. **204 / 빈 응답** — `deleteXxx` 계열은 `void` 를 반환한다
5. **경계값** — 빈 배열 · `total=0` · 페이지 경계 · 0과 음수

케이스 하한 26 · 커버리지 하한 45%.

## Acceptance Criteria

1. `test -f apps/web/src/features/live-sessions/__tests__/hooks.core.test.tsx -a -f apps/web/src/features/trading/__tests__/hooks.core.test.tsx`
2. `cd apps/web && pnpm exec vitest run src/features/live-sessions/__tests__/hooks.core.test.tsx src/features/trading/__tests__/hooks.core.test.tsx --coverage --coverage.include='src/features/live-sessions/hooks.ts' --coverage.include='src/features/trading/hooks.ts' --coverage.reporter=json-summary --coverage.reportsDirectory=coverage/fe6-hooks-live-trading --reporter=json --outputFile=coverage/fe6-hooks-live-trading/results.json`
3. `python3 tools/harness/assert_fe.py apps/web/coverage/fe6-hooks-live-trading --min-cases 26 --target src/features/live-sessions/hooks.ts --min-cov 45 --target src/features/trading/hooks.ts --min-cov 45`
4. `git diff --quiet -- apps/web/src/features/live-sessions/hooks.ts apps/web/src/features/trading/hooks.ts`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `phases/fe6-common.md` 의 금지사항을 어기지 않았는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **대상 소스를 한 줄도 고치지 마라.** 이유: 이 lane 은 커버리지 lane 이고, 소스 변경은
  부채 lane 의 몫이다. 두 lane 이 같은 파일을 고치면 병합이 충돌한다.
  ★소스에 결함이 보이면 **고치지 말고 `summary` 에 적어라** — 5차에서 그렇게 [BL-819] 를 잡았다.
- **기존 테스트 파일을 고치지 마라.** 이유: 그 파일들은 다른 것을 재고 있고, 고치면
  「내 테스트가 통과하도록 남의 단언을 낮춘」 것이 된다.
- 커밋하지 마라(커밋은 러너 소관).
