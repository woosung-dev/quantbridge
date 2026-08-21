# Step 0: 재료 실사 + 테스트 파일 신설 — strategy · optimizer · alert-rules REST 클라이언트

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

1. **대상을 직접 읽어라.** 위 대상 파일을 전부 열고, export 되는 심볼마다
   「무엇을 하는가 · 외부 경계가 어디인가(무엇을 mock 해야 하는가)」를 한 줄로 정리해라.
2. **커버리지를 네가 직접 재라.** 아래 AC 의 첫 명령이 그것을 한다. 착수 전 수치가
   위 「착수 전 실측」과 크게 다르면 **그 사실을 `summary` 맨 앞에 적어라** —
   5차에서 재료 8개 중 6개가 이 대조로 갈렸다.
   ★**대상이 이미 85% 이상 덮여 있으면 재료가 아니다.** `status` 를 `blocked` 로 하고
   `blocked_reason` 에 측정 명령과 수치를 적고 **즉시 중단**해라.
3. **테스트 파일을 신설한다** — 위 경로 그대로. 이 step 에서는 **가장 확실한 것부터
   최소 6케이스**만 쓴다. 전부 덮으려 하지 마라(그건 step1~2 의 일이다).

## `summary` 에 반드시 담을 것

- 심볼별 「덮음/안 덮음」 표
- 착수 전 실측 커버리지 (AC 첫 명령의 출력 수치)
- mock 을 어디에 걸었는지와 **왜 거기인지**

## Acceptance Criteria

1. `test -f apps/web/src/features/strategy/__tests__/api.test.ts -a -f apps/web/src/features/optimizer/__tests__/api.test.ts -a -f apps/web/src/features/alert-rules/__tests__/api.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/strategy/__tests__/api.test.ts src/features/optimizer/__tests__/api.test.ts src/features/alert-rules/__tests__/api.test.ts --coverage --coverage.include='src/features/strategy/api.ts' --coverage.include='src/features/optimizer/api.ts' --coverage.include='src/features/alert-rules/api.ts' --coverage.reporter=json-summary --coverage.reportsDirectory=coverage/fe6-api-strategy-opt --reporter=json --outputFile=coverage/fe6-api-strategy-opt/results.json`
3. `python3 tools/harness/assert_fe.py apps/web/coverage/fe6-api-strategy-opt --min-cases 6 --target src/features/strategy/api.ts --min-cov 15 --target src/features/optimizer/api.ts --min-cov 15 --target src/features/alert-rules/api.ts --min-cov 15`
4. `git diff --quiet -- apps/web/src/features/strategy/api.ts apps/web/src/features/optimizer/api.ts apps/web/src/features/alert-rules/api.ts`

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
