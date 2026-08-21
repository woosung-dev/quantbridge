# Step 1: 정상 경로 전수 — live-sessions · trading · waitlist REST + unrealized 계산

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/src/features/live-sessions/api.ts` — **이번 회차의 대상**
- `apps/web/src/features/trading/api.ts` — **이번 회차의 대상**
- `apps/web/src/features/waitlist/api.ts` — **이번 회차의 대상**
- `apps/web/src/features/live-sessions/unrealized.ts` — **이번 회차의 대상**

## 이 lane 이 만드는 파일

- `apps/web/src/features/live-sessions/__tests__/api-contract.test.ts`
- `apps/web/src/features/trading/__tests__/api-contract.test.ts`
- `apps/web/src/features/waitlist/__tests__/api-contract.test.ts`
- `apps/web/src/features/live-sessions/__tests__/unrealized-branches.test.ts`

## 착수 전 실측 (2026-08-22 · CONTROL 이 전량 스위트 커버리지로 쟀다)

`live-sessions/api.ts` **73 미커버 (26.3%)** · export 9 / `trading/api.ts` **40 미커버 (60.8%)** · export 9 / `waitlist/api.ts` **42 미커버 (25.0%)** · export 4 / `live-sessions/unrealized.ts` **70 미커버 (24.7%)** · export 3

## 이 lane 만의 사실

★★**기존 테스트 두 개가 이름만 맞다** — `live-sessions/__tests__/api-state.test.ts` 와
  `waitlist/__tests__/api.test.ts` 는 **스키마와 query-keys 만** 본다. 그래서 파일 이름을
  `api-contract.test.ts` 로 새로 잡았다. **기존 두 파일을 고치지 마라** — 다른 것을 재고 있다.
★`unrealized.ts` 는 성격이 다르다 — `computeUnrealizedPnl` 은 **순수 함수**이고
  `useUnrealizedPnlEstimate` 만 훅이다. 순수 함수를 먼저 덮으면 커버리지가 크게 오른다.
  `OpenTradeSchema` 는 zod 스키마라 파싱 실패 케이스가 판별력을 만든다.
★★**`unrealized.test.ts` 는 이미 있다**(그래서 새 파일은 `unrealized-branches.test.ts` 다).
  그 파일이 있는데도 커버리지가 24.7% 라는 것은 **덮은 것이 일부뿐**이라는 뜻이다 —
  열어서 무엇을 이미 재는지 보고 **겹치지 않는 갈래**를 골라라. 그 파일을 고치지 마라.

## 작업

앞 step 의 `summary` 가 남긴 「안 덮음」 심볼들의 **정상 경로**를 덮는다.

각 함수마다 최소한 이 셋을 단언해라:

1. **외부 경계를 정확한 인자로 불렀다** — 경로 문자열 · HTTP method · `params` 키 이름 ·
   토큰 전달. ★**경로를 문자열 리터럴로 다시 적어 단언해라.** 소스에서 상수를 import 해
   비교하면 그 상수가 틀려도 통과한다(항진명제).
2. **반환값이 그대로 흐르거나, 스키마를 통과한 결과가 나온다**
3. **호출 횟수** — 한 번 부를 것을 두 번 부르지 않는다

케이스 하한 22 · 대상 커버리지 하한 45% 는 AC 가 잰다.

## Acceptance Criteria

1. `test -f apps/web/src/features/live-sessions/__tests__/api-contract.test.ts -a -f apps/web/src/features/trading/__tests__/api-contract.test.ts -a -f apps/web/src/features/waitlist/__tests__/api-contract.test.ts -a -f apps/web/src/features/live-sessions/__tests__/unrealized-branches.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/live-sessions/__tests__/api-contract.test.ts src/features/trading/__tests__/api-contract.test.ts src/features/waitlist/__tests__/api-contract.test.ts src/features/live-sessions/__tests__/unrealized-branches.test.ts --coverage --coverage.include='src/features/live-sessions/api.ts' --coverage.include='src/features/trading/api.ts' --coverage.include='src/features/waitlist/api.ts' --coverage.include='src/features/live-sessions/unrealized.ts' --coverage.thresholds.perFile --coverage.thresholds.lines=45`
3. `git diff --quiet -- apps/web/src/features/live-sessions/api.ts apps/web/src/features/trading/api.ts apps/web/src/features/waitlist/api.ts apps/web/src/features/live-sessions/unrealized.ts`

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
