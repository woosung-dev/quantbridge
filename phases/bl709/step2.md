# Step 2 — 서버 컴포넌트가 URL 정렬을 읽어 그대로 prefetch 한다 (RSC 축)

이 step 이 [BL-709] 의 본체다. `strategies/page.tsx` 는 Server Component 인데 **`searchParams` 를
받지 않고** `order_by:"updated_at"` · `order:"desc"` 를 하드코딩해 prefetch 한다. 그래서
`/strategies?order_by=sharpe_ratio` 로 진입하면 **서버가 한 번 조회한 결과가 버려지고**
클라이언트가 같은 목록을 다시 가져온다.

이 step 은 **서버 파일 하나만** 고친다. 클라이언트(`_components/`)는 step 3 몫이다.

## 읽어야 할 파일

- `frontend/src/app/(dashboard)/strategies/page.tsx` — 전문. 특히 `:28` 시그니처와 `:32-43` 의
  주석·하드코딩 query, `:53-62` 의 `prefetchQuery`
- `frontend/src/features/strategy/sort.ts` — **step 1 이 만든 파일**. `STRATEGY_SORT_OPTIONS` 와
  `resolveStrategySort` 의 시그니처·기본값 규칙을 그대로 쓴다
- `frontend/src/features/strategy/query-keys.ts` — `strategyKeys.list(uid, query)` 가 query 를
  어떻게 identity 로 쓰는지 (queryKey 가 갈리면 prefetch 는 그대로 버려진다)
- `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx` `:77-92` — client 가
  같은 URL 스칼라로 만드는 query. **읽기만** 한다. 서버가 만드는 query 가 이것과 같아야 한다
- `frontend/AGENTS.md` §7 — Next.js 16 에서 `searchParams` 는 **`Promise<>`** 라 `await` 필수
- `frontend/AGENTS.md` §6 — Server/Client 경계 규칙

## 작업

`frontend/src/app/(dashboard)/strategies/page.tsx` **한 파일만** 고친다.

1. `StrategiesPage` 가 `searchParams` 를 받는다. Next.js 16 이므로 타입은 **`Promise<>`** 이고
   `await` 해야 한다. 시그니처 수준의 계약:
   ```ts
   export default async function StrategiesPage({
     searchParams,
   }: {
     searchParams: Promise<Record<string, string | string[] | undefined>>;
   });
   ```
   배열로 올 수 있다는 것을 잊지 마라(`?order_by=a&order_by=b`). 배열이면 어떻게 다룰지는
   네가 정하되, **화이트리스트를 통과하지 못하는 입력은 전부 기본값으로 정규화**돼야 한다.
2. `resolveStrategySort` 로 검증한 값을 `query` 에 실어 **같은 query 로** `prefetchQuery` 한다.
   `queryKey` 도 그 query 로 만든다 — client hook 과 **같은 키**가 되는 것이 이 step 의 목적이다.
3. `:32-36` 의 주석은 지금 **결함을 설명하는 주석**이다. 결함이 사라졌으므로 그 문장을 지우고,
   대신 「URL 정렬을 어떻게 정규화해 client 와 키를 맞추는가」를 적어라. 확정되지 않은 인과는
   `[가정]` 으로 표기한다.
4. `PAGE_SIZE`·`is_archived`·`offset` 은 **건드리지 마라**. 이 회차가 고치는 축은 정렬 하나다.

## AC (Acceptance Criteria)

★**정본은 `phases/bl709/index.json` 의 step 2 `ac` 배열이다.** 아래는 그것과 **같은 문자열**이다.
러너가 이 커맨드를 **독립적으로 재실행**하고 하나라도 rc≠0 이면 `completed` 를 취소한다.

```bash
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm typecheck
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm lint
cd "$(git rev-parse --show-toplevel)/frontend" && grep -qE 'searchParams: Promise<' 'src/app/(dashboard)/strategies/page.tsx' && grep -q 'await searchParams' 'src/app/(dashboard)/strategies/page.tsx' && grep -q 'resolveStrategySort' 'src/app/(dashboard)/strategies/page.tsx'
cd "$(git rev-parse --show-toplevel)/frontend" && grep -q 'StrategiesPage' 'src/app/(dashboard)/strategies/page.tsx' && ! grep -q 'order_by: "updated_at"' 'src/app/(dashboard)/strategies/page.tsx'
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm test
cd "$(git rev-parse --show-toplevel)" && test -z "$(git diff main --name-only -- 'frontend/src/app/(dashboard)/strategies/_components')"
```

> 4번째의 부정 단언(`! grep`)은 **하드코딩된 기본 정렬이 사라졌는지**를 잰다. 파일이 없어도
> 통과하는 항진명제가 되지 않도록 **같은 파일에 대한 긍정 단언(`StrategiesPage`)을 앞에 뒀다** —
> 순서를 바꾸지 마라.

## 검증 절차

1. 위 AC 6건을 순서대로 실행해 전건 rc=0 을 확인한다.
2. `git diff main -- 'frontend/src/app'` 이 **`page.tsx` 하나만** 담고 있는지 확인한다.
3. 서버가 만드는 query 객체와 `strategy-list.tsx:89-92` 의 client query 를 **눈으로 나란히 놓고**
   같은 URL 에서 같은 값이 되는지 확인한다. 다르면 prefetch 는 여전히 버려진다.
4. `phases/bl709/index.json` 의 step 2 를 `completed` + `summary` 에 **① 배열 파라미터를 어떻게
   다뤘는지 ② 정정한 주석의 요지 ③ client query 와 일치를 무엇으로 확인했는지**를 한 줄로 적는다.

## 금지사항

- `_components/` 아래를 고치지 마라. 이유: 6번째 AC 가 막는다. client 배선은 step 3 이다.
- `strategy-list.tsx` 에서 `SORT_OPTIONS` 를 import 하지 마라. 이유: client 파일은 `"use client"`
  이고 서버가 그걸 끌어오면 경계가 뒤집힌다(`frontend/AGENTS.md` §6). 공유 정본은 step 1 의
  `features/strategy/sort.ts` 다.
- 정렬 이외의 query 축(limit·offset·is_archived·parse_status)을 URL 로 옮기지 마라.
  이유: BL-709 의 범위가 아니고, client 의 로컬 필터와 계약이 갈린다.
- `prefetchQuery` 의 `try/catch` silent degrade 를 없애지 마라. 이유: 서버 조회 실패는
  화면을 죽이지 않고 client 재시도로 흡수하는 것이 현 계약이다(`:59-61`).
- 개발 서버를 띄워 수동 확인하려 하지 마라. 이유: 이 회차 AC 는 전부 무인 실행이고,
  BE(8000)·DB 가 안 떠 있어 목록이 비면 「고쳤는지」를 판별할 수 없다.
