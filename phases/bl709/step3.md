# Step 3 — 클라이언트가 같은 화이트리스트를 쓴다 (1벌 공유 확정)

step 1 이 `features/strategy/sort.ts` 를, step 2 가 서버 prefetch 를 맞췄다. 지금 화이트리스트는
**2벌**이다 — 공유 모듈 1벌 + `strategy-list.tsx` 안의 로컬 `SORT_OPTIONS` 1벌.
이 step 은 로컬을 버리고 **1벌로 합친다**. 합치지 않으면 정렬 축을 추가할 때 서버와 클라이언트가
조용히 갈린다(그게 BL-709 를 만든 기전이다).

## 읽어야 할 파일

- `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx` — 전문.
  특히 `SORT_OPTIONS`(`:55-64`) · URL 검증(`:77-82`) · `pushSort`(`:133-140`) · select 렌더(`:251-263`)
- `frontend/src/features/strategy/sort.ts` — **step 1 이 만든 정본**
- `frontend/src/app/(dashboard)/strategies/page.tsx` — **step 2 가 고친 서버 쪽**.
  같은 URL 에서 같은 query 가 나와야 한다
- `frontend/AGENTS.md` §3 H-1/H-2 — hooks 안전 규칙 (`useMemo` dep 은 스칼라 우선, queryKey identity)

## 작업

`frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx` **한 파일만** 고친다.

1. 로컬 `SORT_OPTIONS` 정의(`:55-64`)를 **지우고** `features/strategy/sort.ts` 의
   `STRATEGY_SORT_OPTIONS` 를 import 해 쓴다. select 렌더·`pushSort` 의 조회도 그것으로 바꾼다.
2. URL 값 검증(`:77-82`)을 `resolveStrategySort` 호출로 바꾼다. **서버와 같은 함수로 정규화되는 것**이
   이 step 의 목적이다. 직접 `.some(...)` 로 다시 검증하지 마라 — 그러면 2벌이 이름만 바뀐 채 남는다.
3. `useMemo` 의 dep 은 지금처럼 **스칼라 2개**(`orderBy`·`order`)를 유지해라. `resolveStrategySort`
   가 돌려주는 **객체를 dep 에 직접 넣지 마라** — 매 렌더 새 참조라 queryKey 가 흔들린다
   (`frontend/AGENTS.md` §3 H-1).
4. 화면에 보이는 것(라벨·select 순서·`data-testid`)은 **하나도 바뀌면 안 된다**. 이 step 은
   내부 배선만 바꾼다.

## AC (Acceptance Criteria)

★**정본은 `phases/bl709/index.json` 의 step 3 `ac` 배열이다.** 아래는 그것과 **같은 문자열**이다.
러너가 이 커맨드를 **독립적으로 재실행**하고 하나라도 rc≠0 이면 `completed` 를 취소한다.

```bash
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm typecheck
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm lint
cd "$(git rev-parse --show-toplevel)/frontend" && grep -q 'features/strategy/sort' 'src/app/(dashboard)/strategies/_components/strategy-list.tsx' && ! grep -q 'const SORT_OPTIONS' 'src/app/(dashboard)/strategies/_components/strategy-list.tsx'
cd "$(git rev-parse --show-toplevel)/frontend" && test "$(grep -rn 'const STRATEGY_SORT_OPTIONS' src | wc -l | tr -d ' ')" = "1"
cd "$(git rev-parse --show-toplevel)/frontend" && grep -q 'data-testid="strategy-sort"' 'src/app/(dashboard)/strategies/_components/strategy-list.tsx'
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm test
```

> 4번째는 **정의가 1곳뿐**임을 잰다. ★`src/app/(dashboard)/backtests/_components/trades/trade-filter-row.tsx:59`
> 에 **무관한 `SORT_OPTIONS` 가 하나 더** 있다(백테스트 체결 표 정렬). 그래서 이름을
> `STRATEGY_SORT_OPTIONS` 로 재는 것이다 — 그 파일을 건드리면 이 AC 가 거짓 red 를 낸다.
> 3번째의 부정 단언은 파일이 없어도 통과하지 않도록 **같은 파일 긍정 단언을 앞에 뒀다**.

## 검증 절차

1. 위 AC 6건을 순서대로 실행해 전건 rc=0 을 확인한다.
2. `git diff main -- 'frontend/src/app'` 이 **`page.tsx` + `strategy-list.tsx` 둘만** 담고 있는지 확인한다.
3. 같은 URL(`?order_by=sharpe_ratio&order=desc`)에서 서버(`page.tsx`)와 클라이언트가 만드는
   query 객체가 **필드별로 같은지** 코드를 나란히 놓고 확인한다.
4. `phases/bl709/index.json` 의 step 3 을 `completed` + `summary` 에 **① 지운 로컬 정의
   ② 검증 경로가 공유 함수로 바뀐 지점 ③ 화면 표기 무변경을 무엇으로 확인했는지**를 한 줄로 적는다.

## 금지사항

- `trade-filter-row.tsx` 를 건드리지 마라. 이유: 이름만 같은 **무관한** 정렬 옵션이다.
  거기까지 통합하는 것은 이 BL 의 범위가 아니고, 4번째 AC 를 거짓 red 로 만든다.
- 라벨·select 순서·`data-testid` 를 바꾸지 마라. 이유: e2e 캐논과 기존 vitest 가 그 문자열을 잡는다.
- `page.tsx` 를 다시 고치지 마라. 이유: step 2 가 이미 닫았다. 여기서 또 고치면 어느 step 이
  결과를 냈는지 원장이 못 가린다. 서버 쪽에 문제가 남았으면 status 를 `blocked` 로 하고 적어라.
- `useMemo`/`useState` 를 새로 추가하지 마라. 이유: 정렬은 URL 스칼라가 정본이고, 로컬 state 를
  하나 더 두면 URL 과 두 벌이 된다(H-1).
- 검색·심볼·parse_status 필터를 손대지 마라. 이유: 이 회차의 축은 정렬 하나다.
