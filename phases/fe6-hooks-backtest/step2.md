# Step 2: 에러·경계 분기 — backtest React Query 훅

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/src/features/backtest/hooks.ts` — **이번 회차의 대상**

## 이 lane 이 만드는 파일

- `apps/web/src/features/backtest/__tests__/hooks.core.test.tsx`

## 착수 전 실측 (2026-08-22 · CONTROL 이 전량 스위트 커버리지로 쟀다)

`backtest/hooks.ts` — 290 stmt 중 **213 미커버 (26.6% · 함수 12.0%)** · export 23개

## 이 lane 만의 사실

★★**기존 테스트 두 개가 이 파일의 일부를 이미 덮는다** — `hooks.all-trades.test.ts`
  (`makeAllTradesFetcher`) 와 `hooks.stress-test.test.ts`. **그 둘을 고치지 마라.**
  새 파일 이름이 `hooks.core.test.tsx` 인 이유다. 단, **커버리지 AC 는 새 파일만으로 잰다** —
  기존 파일이 덮은 몫은 네 점수에 **안 들어간다.** 그래서 하한(45%→62%)은 전량 스위트
  기준 26.6% 와 비교할 값이 아니다 — **네 파일 하나가 그만큼 덮어야 한다**는 뜻이다.
★모듈 레벨로 export 된 **비-훅 심볼**이 먼저다 — `makeAllTradesFetcher`(이미 덮임)·
  `stressTestRefetchInterval`·`stressTestHistoryRefetchInterval` 은 `renderHook` 없이 부를 수 있다.
★[LESSON-004] — polling 훅의 `refetchInterval` 은 **error 일 때 false** 여야 한다.
  그것이 무한 루프·CPU 100% 를 막는 계약이다. 그 분기를 반드시 단언해라.

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

케이스 하한 20 · 커버리지 하한 45%.

## Acceptance Criteria

1. `test -f apps/web/src/features/backtest/__tests__/hooks.core.test.tsx`
2. `cd apps/web && pnpm exec vitest run src/features/backtest/__tests__/hooks.core.test.tsx --coverage --coverage.include='src/features/backtest/hooks.ts' --coverage.thresholds.perFile --coverage.thresholds.lines=45`
3. `git diff --quiet -- apps/web/src/features/backtest/hooks.ts`

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
