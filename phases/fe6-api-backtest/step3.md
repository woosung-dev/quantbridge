# Step 3: 자기 변이 검증 + 회귀 — backtest REST 클라이언트

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/src/features/backtest/api.ts` — **이번 회차의 대상**

## 이 lane 이 만드는 파일

- `apps/web/src/features/backtest/__tests__/api.test.ts`

## 착수 전 실측 (2026-08-22 · CONTROL 이 전량 스위트 커버리지로 쟀다)

`backtest/api.ts` — 185 stmt 중 **182 미커버 (1.6%)** · export 17개

## 이 lane 만의 사실

★이 파일은 `/api/v1/backtests` 와 `/api/v1/stress-tests` **두 경로 상수**를 쓴다(`BACKTESTS_PATH`·`STRESS_TESTS_PATH`). 어느 함수가 어느 쪽인지 **직접 열어 확인해라** —
  `convertIndicator` 만 세 번째 경로(`/api/v1/strategies/convert-indicator`)다.
★`getTradeOhlcv` 는 시그니처가 다르다 — 첫 인자 `_userId` 를 **쓰지 않고**, 토큰을
  `getToken()` **함수로** 받아 안에서 await 한다. 그 비대칭이 이 파일의 유일한 예외다.

## 작업

**네가 쓴 테스트가 실제로 무엇을 잡는지 스스로 증명한다.**

1. **변이를 심어라 (최소 3건).** 대상 소스에 **값·분기 수준**의 변이를 하나씩 넣고
   테스트가 red 가 되는지 확인한 뒤 **원상 복구**한다. 예: 경로 문자열의 한 글자 · method 를
   GET↔POST · `params` 키 이름 · 비교 연산자의 방향.
   ★**타입 수준 변이는 변이가 아니다** — `as unknown` 류는 타입 소거라 런타임이 안 바뀐다.
   ★**복구를 확인해라** — 마지막 AC 의 `git diff --quiet` 가 그것을 강제한다.
2. **red 가 안 나온 변이가 있으면 그 자리를 덮는 케이스를 추가**한다. 변이가 초록으로
   빠져나가는 자리가 바로 네 테스트의 구멍이다.
3. **전체 스위트 회귀** — 마지막 AC 가 `apps/web` 전량 vitest · tsc · biome 을 돌린다.

## `summary` 에 반드시 담을 것

- 심은 변이 3건 각각의 **위치 · 무엇을 바꿨나 · red 였나** (표로)
- red 가 안 났던 변이가 있다면 **무엇을 추가해 잡았는지**
- 최종 커버리지 수치

## Acceptance Criteria

1. `test -f apps/web/src/features/backtest/__tests__/api.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/backtest/__tests__/api.test.ts --coverage --coverage.include='src/features/backtest/api.ts' --coverage.thresholds.perFile --coverage.thresholds.lines=85`
3. `git diff --quiet -- apps/web/src/features/backtest/api.ts`
4. `cd apps/web && pnpm exec vitest run`
5. `cd apps/web && pnpm exec tsc --noEmit`
6. `cd apps/web && pnpm exec biome check src/features/backtest/__tests__/api.test.ts`

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
