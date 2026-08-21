# Step 1: 정상 경로 전수 — strategy · optimizer · alert-rules REST 클라이언트

## 읽어야 할 파일

- ★**[`phases/fe6-common.md`](../fe6-common.md) — 이 회차 FE lane 공통 규약. 먼저 읽어라**
- `apps/web/src/features/strategy/api.ts` — **이번 회차의 대상**
- `apps/web/src/features/optimizer/api.ts` — **이번 회차의 대상**
- `apps/web/src/features/alert-rules/api.ts` — **이번 회차의 대상**

## 이 lane 이 만드는 파일

- `apps/web/src/features/strategy/__tests__/api.test.ts`
- `apps/web/src/features/optimizer/__tests__/api.test.ts`
- `apps/web/src/features/alert-rules/__tests__/api.test.ts`

## 착수 전 실측 (2026-08-22 · CONTROL 이 전량 스위트 커버리지로 쟀다)

`strategy/api.ts` 94 stmt 중 **91 미커버 (3.2%)** · export 8 / `optimizer/api.ts` 89 stmt **전부 미커버 (0%)** · export 5 / `alert-rules/api.ts` **36 미커버** · export 3

## 이 lane 만의 사실

★**테스트 파일이 셋이다** — features 디렉터리가 셋이라 한 파일에 묶을 수 없다.
  AC 는 셋을 한 번에 돌리고 커버리지도 셋을 각각 잰다.
★`optimizer/api.ts` 는 grid·bayesian·genetic 세 POST 가 **같은 응답 스키마**를 쓴다 —
  세 경로가 실제로 서로 다른 URL 로 가는지 단언해라. 복붙 오류가 여기서 산다.

## 작업

앞 step 의 `summary` 가 남긴 「안 덮음」 심볼들의 **정상 경로**를 덮는다.

각 함수마다 최소한 이 셋을 단언해라:

1. **외부 경계를 정확한 인자로 불렀다** — 경로 문자열 · HTTP method · `params` 키 이름 ·
   토큰 전달. ★**경로를 문자열 리터럴로 다시 적어 단언해라.** 소스에서 상수를 import 해
   비교하면 그 상수가 틀려도 통과한다(항진명제).
2. **반환값이 그대로 흐르거나, 스키마를 통과한 결과가 나온다**
3. **호출 횟수** — 한 번 부를 것을 두 번 부르지 않는다

케이스 하한 16 · 대상 커버리지 하한 55% 는 AC 가 잰다.

## Acceptance Criteria

1. `test -f apps/web/src/features/strategy/__tests__/api.test.ts -a -f apps/web/src/features/optimizer/__tests__/api.test.ts -a -f apps/web/src/features/alert-rules/__tests__/api.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/strategy/__tests__/api.test.ts src/features/optimizer/__tests__/api.test.ts src/features/alert-rules/__tests__/api.test.ts --coverage --coverage.include='src/features/strategy/api.ts' --coverage.include='src/features/optimizer/api.ts' --coverage.include='src/features/alert-rules/api.ts' --coverage.thresholds.perFile --coverage.thresholds.lines=55`
3. `git diff --quiet -- apps/web/src/features/strategy/api.ts apps/web/src/features/optimizer/api.ts apps/web/src/features/alert-rules/api.ts`

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
