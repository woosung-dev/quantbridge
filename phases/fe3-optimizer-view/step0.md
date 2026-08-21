# Step 0: optimizer-page-view

## 읽어야 할 파일

- `apps/web/src/features/optimizer/components/optimizer-page-view.tsx` — **대상** (187줄)
- `apps/web/src/features/optimizer/labels.ts` — 알고리즘 라벨 SSOT
- `apps/web/src/features/optimizer/components/__tests__/` — 이 디렉터리의 기존 테스트 관용구.
  ★**있는 것을 먼저 읽고 mock 방식을 그대로 따라라**

## 배경

`OptimizerPageView` 는 **미커버 컴포넌트 중 가장 크다**(187줄). 옵티마이저 화면의 조립 지점이고
**어떤 테스트도 이 파일을 import 하지 않는다**(전이 폐포 실측 2026-08-21).

★**이 컴포넌트가 하는 일은 렌더가 아니라 판정이다** — `useBacktests` 가 준 목록에서
**완료된 것만 골라** Select 옵션으로 바꾸고(`useMemo`), 고른 알고리즘에 따라 폼 3종
(`grid_search` · `bayesian` · `genetic`) 중 하나를 띄운다. **고르지 못한 상태**(백테스트 미선택)와
**고를 것이 없는 상태**(완료 백테스트 0건)가 갈리는 지점이 여기다.

★**[BL-489] 맥락** — 사이징 재계산 처방이 반증돼 이 화면의 일부는 아직 열려 있다.
**이 lane 은 지금 동작을 고정할 뿐 무엇도 고치지 않는다.**

## 작업

`apps/web/src/features/optimizer/components/__tests__/optimizer-page-view.test.tsx` 를 신설한다.

### 호출 방식

★**`useBacktests` 를 반드시 mock 해라. 이유:** 진짜 훅은 React Query 로 FastAPI 를 친다.
워크트리에는 서버가 없고 8 lane 이 동시에 돈다.

```ts
const useBacktests = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...a: unknown[]) => useBacktests(...a),
}));
```

★**하위 폼 3종(`BayesianSearchForm`·`GeneticSearchForm`·`GridSearchForm`)과 `OptimizerRunList` 는
mock 해라** — 각각 자기 훅과 폼 상태를 갖고 있어 이 lane 의 관심사가 아니다.
`vi.mock("../grid-search-form", () => ({ GridSearchForm: () => <div data-testid="form-grid" /> }))`
식으로 **식별 가능한 더미**를 넣어라(그래야 「어느 폼이 떴나」를 잴 수 있다).

★**`QueryClientProvider` 로 감쌀 필요가 없다** — 훅을 mock 했으므로 React Query 컨텍스트가 안 쓰인다.
만약 렌더가 컨텍스트를 요구하면 그때만 최소 Provider 를 이 파일 안에 세워라.

### 최소한 이 아홉을 덮어라 (케이스 ≥9)

1. ★**로딩 상태에서 던지지 않는다** — `useBacktests` 가 `{ data: undefined, isPending: true }` 를
   내도 렌더가 성공한다
2. ★★**완료된 백테스트만 옵션이 된다** — `completed` 2건 + `running`/`failed` 각 1건을 주면
   Select 옵션이 **2개**다. ★**이것이 이 컴포넌트의 유일한 진짜 필터**다
3. ★**옵션이 0건일 때의 화면** — 전부 `running` 이면 옵션 0. **던지지 않고**, 사용자가
   그것을 알 수 있는 표시가 있는지 관측해 고정해라. ★**없으면 고치지 말고 `summary` 에 적어라**
4. ★**알고리즘 기본값은 `grid_search`** — 초기 렌더에서 grid 더미가 보이고 나머지 둘은 없다
5. ★★**알고리즘을 바꾸면 폼이 바뀐다** — bayesian / genetic 으로 각각 전환해
   **그 폼만 보이고 나머지 둘은 사라진다**를 단언해라. ★세 방향을 다 재라 —
   「전부 렌더하고 CSS 로 숨기는」 구현과 갈리는 지점이다
6. ★**라벨은 `labels.ts` 에서 온다** — 알고리즘 3종의 표시 문자열을 **import 해서** 대조해라.
   ★**문자열을 테스트에 복사하지 마라** — 사본이 되고 라벨 개정이 숨는다
7. ★**`OptimizerRunList` 가 항상 렌더된다** — 알고리즘·선택 상태와 무관하게 목록은 남는다
   (실행 이력은 폼과 독립이다)
8. ★**`PICKER_LIMIT` 이 훅 인자로 전달된다** — `useBacktests` 가 받은 첫 인자에
   `limit` 과 `offset: 0` 이 있다. 목록이 조용히 잘리는 것을 잡는다
9. ★**양성 대조** — `useBacktests` mock 이 **실제로 불렸다**(호출 횟수 ≥1)이고
   렌더 결과 `textContent` 가 비어 있지 않다. mock 이 안 걸려 진짜 훅이 도는 상태를 배제한다

★`afterEach` 에서 `cleanup()` · `vi.clearAllMocks()`.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/features/optimizer/components/__tests__/optimizer-page-view.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/features/optimizer/components/__tests__/optimizer-page-view.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 9
cd apps/web && pnpm exec eslint 'src/features/optimizer/components/__tests__/optimizer-page-view.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **3번에서 관측한 「옵션 0건」 화면**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `optimizer-page-view.tsx` 와 하위 폼·목록 컴포넌트를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**진짜 네트워크 요청을 내지 마라** — `useBacktests` mock 없이 렌더하지 마라
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 더미 컴포넌트는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
