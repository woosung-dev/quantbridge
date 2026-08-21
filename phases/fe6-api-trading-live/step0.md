# Step 0: 재료 실사 + 테스트 파일 신설 — live-sessions · trading · waitlist REST + unrealized 계산

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

1. `test -f apps/web/src/features/live-sessions/__tests__/api-contract.test.ts -a -f apps/web/src/features/trading/__tests__/api-contract.test.ts -a -f apps/web/src/features/waitlist/__tests__/api-contract.test.ts -a -f apps/web/src/features/live-sessions/__tests__/unrealized-branches.test.ts`
2. `cd apps/web && pnpm exec vitest run src/features/live-sessions/__tests__/api-contract.test.ts src/features/trading/__tests__/api-contract.test.ts src/features/waitlist/__tests__/api-contract.test.ts src/features/live-sessions/__tests__/unrealized-branches.test.ts --coverage --coverage.include='src/features/live-sessions/api.ts' --coverage.include='src/features/trading/api.ts' --coverage.include='src/features/waitlist/api.ts' --coverage.include='src/features/live-sessions/unrealized.ts' --coverage.reporter=json-summary --coverage.reportsDirectory=coverage/fe6-api-trading-live --reporter=json --outputFile=coverage/fe6-api-trading-live/results.json`
3. `python3 tools/harness/assert_fe.py apps/web/coverage/fe6-api-trading-live --min-cases 6 --target src/features/live-sessions/api.ts --min-cov 12 --target src/features/trading/api.ts --min-cov 12 --target src/features/waitlist/api.ts --min-cov 12 --target src/features/live-sessions/unrealized.ts --min-cov 12`
4. `git diff --quiet -- apps/web/src/features/live-sessions/api.ts apps/web/src/features/trading/api.ts apps/web/src/features/waitlist/api.ts apps/web/src/features/live-sessions/unrealized.ts`

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
