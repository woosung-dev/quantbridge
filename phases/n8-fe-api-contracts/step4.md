# Step 4: coverage-guard-and-selfcheck — 「API 를 부르는 feature 는 계약 테스트를 갖는다」를 기계로 만든다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- `apps/web/src/lib/__tests__/decision-surface-guard.test.ts` — **FE 가드 테스트의 레포 관용구.**
  `node:fs` 로 파일을 읽어 판정하고 양성 대조를 함께 단언하는 형식이다. 이것을 본떠라
- `apps/web/src/features/` — 12개 feature 디렉터리

## 배경

step 0~3 이 4개 feature 에 계약 테스트를 만들었다. 이 step 은 **다음 feature 가 생겼을 때
계약 테스트 없이 지나가지 못하게** 만든다.

## 작업

`apps/web/src/lib/__tests__/api-contract-coverage.test.ts` 를 **새로** 만든다.

### 판정 규칙 — 이 정의는 확정이다

`src/features/<name>/api.ts` **파일이 존재하는** feature 는
`src/features/<name>/__tests__/api-contract.test.ts` 를 가져야 한다.

★**`api.ts` 존재 여부로 판정해라.** 「API 호출 파일 수」 같은 grep 셈으로 판정하지 마라 —
CONTROL 이 후보를 고를 때 쓴 셈이고, 판정 기준으로는 불안정하다(`fetch(` 문자열이 주석·타입에도
걸린다).

### allowlist

`api.ts` 가 없는 feature 는 대상이 아니다(자동 제외). CONTROL 실측 기준 대상은
**7개**(alert-rules · backtest · live-sessions · optimizer · strategy · trading · waitlist)로
예상되지만 **다시 재라.** 실측이 다르면 `summary` 에 적어라.

면제가 필요하면 `_ALLOWLIST_NO_CONTRACT` 상수에 **이유를 주석으로 달아** 넣는다.
★비어 있는 것이 정상이다. 면제를 만들어 통과시키지 마라.

### 이 step 이 남겨야 할 테스트 (3개 이상)

1. **양성 대조** — 스캔한 feature 디렉터리가 **10개 이상**이고, `api.ts` 를 가진 대상이
   **5개 이상**이다. (둘 중 하나가 0이면 판정기가 죽은 것이고 부재 단언은 항진명제가 된다.)
2. **커버리지 가드** — 대상 feature 전부가 `__tests__/api-contract.test.ts` 를 갖는다
   (allowlist 제외).
3. **죽은 allowlist 금지** — `_ALLOWLIST_NO_CONTRACT` 의 원소가 모두 실재하는 feature 이름이다.

### 변이 자가검증

- **변이 ⑴** — `src/features/optimizer/__tests__/api-contract.test.ts` 를 임시로 다른 이름으로
  옮긴다. 가드가 **red** 여야 한다. 복원한다.
- **변이 ⑵ 음성 대조** — `api.ts` 가 없는 feature(예: `marketing` 또는 `auth`)가 계약 테스트가
  없다는 이유로 red 를 만들지 **않는다**는 것을 확인한다.

★복원은 `git status --porcelain` 이 비었는지로 확인해라. 변이 결과는 `summary` 에 적어라.

## Acceptance Criteria

```bash
test -f apps/web/src/lib/__tests__/api-contract-coverage.test.ts
cd apps/web && pnpm exec vitest run src/lib/__tests__/api-contract-coverage.test.ts
test "$(grep -cE '\bit\(' apps/web/src/lib/__tests__/api-contract-coverage.test.ts)" -ge 3
cd apps/web && pnpm exec vitest run src/features/backtest src/features/strategy src/features/optimizer src/features/alert-rules
cd apps/web && pnpm exec biome check src/lib/__tests__/api-contract-coverage.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **변이 ⑴ 이 red 를 만들었는지** 확인한다. 안 만들었으면 가드가 파일을 안 읽는 것이다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`api.ts` 파일들을 수정하지 마라.** 이유: 이 step 은 가드만 세운다.
- **allowlist 로 대상을 비우지 마라.** 이유: 그러면 가드가 항진명제가 된다.
- **변이를 커밋에 남기지 마라.** 이유: 다음 사람이 그것을 코드로 읽는다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
