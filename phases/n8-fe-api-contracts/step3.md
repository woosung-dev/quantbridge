# Step 3: alert-rules-contract — `features/alert-rules` 의 REST 계약을 고정한다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/web/src/features/live-sessions/__tests__/api-contract.test.ts` — **형식 정본.** 이것을 본떠라
- `apps/web/src/features/trading/__tests__/api-contract.test.ts` — 두 번째 참고
- `apps/web/src/features/alert-rules/api.ts` — 이 step 의 대상 (export **3개**)
- `apps/web/src/lib/api-client.ts` — `apiFetch` 의 시그니처

## 배경

12개 feature 중 **3개**(waitlist·live-sessions·trading)만 REST 계약 테스트를 갖는다.
계약이 없으면 **BE 응답 형상이 바뀌어도 화면이 조용히 깨진다** — 타입은 컴파일 타임에만 있고
런타임 응답은 아무도 안 본다.

## 작업

`apps/web/src/features/alert-rules/__tests__/api-contract.test.ts` 를 **새로** 만든다.

### 형식은 정본을 따른다 — 새로 발명하지 마라

`live-sessions/__tests__/api-contract.test.ts` 의 구조를 그대로 쓴다: `vi.hoisted` 로
`apiFetch` mock 을 만들고 `vi.mock("@/lib/api-client", ...)` 로 갈아끼운다. **그 파일을 열어
그대로 본떠라** — 여기에 코드를 베껴 적으면 낡은 사본이 된다.

그 뒤 `../api` 에서 export 를 가져와 **함수마다** 다음 셋을 단언한다:

1. **경로** — `apiFetch` 가 받은 첫 인자(URL)가 정확히 무엇인가. 경로 파라미터가 실제로 박히는가.
2. **메서드·본문** — GET 이면 옵션에 method 가 없거나 GET 인가. POST/PATCH/DELETE 면 method 와
   `body` 의 형상이 맞는가.
3. **응답 스키마** — 모듈 상수로 **대표 응답 fixture** 를 두고, 함수가 그것을 그대로
   통과시키는지(또는 문서화된 변환을 하는지) 단언한다.

### 벗어나면 안 되는 계약

- **`api.ts` 를 수정하지 마라.** 이 step 은 **현재 동작을 고정**하는 것이다. AC 가
  `git diff --quiet -- apps/web/src/features/alert-rules/api.ts` 로 집행한다.
- ★**`api.ts` 가 틀렸다고 판단되면 고치지 말고 `summary` 에 근거와 함께 적어라.**
  계약 테스트가 결함을 계약으로 승격시킨 사고가 이 레포에 있다(2026-08-19 n6 · 2026-08-24 n7).
  **「이렇게 동작한다」와 「이렇게 동작해야 한다」를 테스트 이름으로 구분해라.**
- **네트워크를 타지 마라.** `apiFetch` 를 mock 하는 것이 전부다. 실제 fetch·MSW 금지.
- **fixture 의 필드를 임의로 만들지 마라.** BE 응답 스키마를 근거로 삼아라 —
  `apps/api/src/trading/` 의 `schemas.py` 가 정본이다(경로가 다르면 찾아서 확인해라). **읽기만 해라.**

### 최소 커버리지

export 3개 중 **최소 3개 함수**에 `it(...)` 이 있어야 한다(AC 가 센다).
남은 것을 뺐다면 **왜 뺐는지** `summary` 에 적어라.

## Acceptance Criteria

```bash
test -f apps/web/src/features/alert-rules/__tests__/api-contract.test.ts
cd apps/web && pnpm exec vitest run src/features/alert-rules/__tests__/api-contract.test.ts
test "$(grep -cE '\bit\(' apps/web/src/features/alert-rules/__tests__/api-contract.test.ts)" -ge 3
cd apps/web && pnpm exec biome check src/features/alert-rules/__tests__/api-contract.test.ts
cd apps/web && pnpm exec tsc --noEmit
git diff --quiet -- apps/web/src/features/alert-rules/api.ts
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **테스트 하나를 일부러 깨뜨려 red 를 확인하고 복원한다** — 예: 기대 경로를 한 글자 바꾼다.
   green 만 본 계약 테스트는 무증거다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`api.ts` 를 수정하지 마라.** 이유: 이 step 은 현재 동작을 고정한다. AC 가 집행한다.
- **`it.skip` / `describe.skip` / `.todo` 를 쓰지 마라.** 이유: AC 의 `it(` 개수 하한을
  빈 껍데기로 채우는 길이 된다.
- **다른 feature 디렉터리를 만지지 마라.** 이유: 이 lane 의 다른 step 이 소유한다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
