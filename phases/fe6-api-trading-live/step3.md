# Step 3: 자기 변이 검증 + 회귀 — live-sessions · trading · waitlist REST + unrealized 계산

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

1. `test -f apps/web/src/features/live-sessions/__tests__/api-contract.test.ts -a -f apps/web/src/features/trading/__tests__/api-contract.test.ts -a -f apps/web/src/features/waitlist/__tests__/api-contract.test.ts -a -f apps/web/src/features/live-sessions/__tests__/unrealized-branches.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/live-sessions/__tests__/api-contract.test.ts src/features/trading/__tests__/api-contract.test.ts src/features/waitlist/__tests__/api-contract.test.ts src/features/live-sessions/__tests__/unrealized-branches.test.ts --coverage --coverage.include='src/features/live-sessions/api.ts' --coverage.include='src/features/trading/api.ts' --coverage.include='src/features/waitlist/api.ts' --coverage.include='src/features/live-sessions/unrealized.ts' --coverage.reporter=json-summary --coverage.reportsDirectory=coverage/fe6-api-trading-live --reporter=json --outputFile=coverage/fe6-api-trading-live/results.json`
3. `python3 tools/harness/assert_fe.py apps/web/coverage/fe6-api-trading-live --min-cases 32 --target src/features/live-sessions/api.ts --min-cov 78 --target src/features/trading/api.ts --min-cov 78 --target src/features/waitlist/api.ts --min-cov 78 --target src/features/live-sessions/unrealized.ts --min-cov 78`
4. `git diff --quiet -- apps/web/src/features/live-sessions/api.ts apps/web/src/features/trading/api.ts apps/web/src/features/waitlist/api.ts apps/web/src/features/live-sessions/unrealized.ts`
5. `cd apps/web && pnpm exec vitest run`
6. `cd apps/web && pnpm exec tsc --noEmit`
7. `cd apps/web && pnpm exec biome check src/features/live-sessions/__tests__/api-contract.test.ts src/features/trading/__tests__/api-contract.test.ts src/features/waitlist/__tests__/api-contract.test.ts src/features/live-sessions/__tests__/unrealized-branches.test.ts`

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
