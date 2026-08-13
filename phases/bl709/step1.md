# Step 1 — 정렬 화이트리스트를 `features/strategy/` 로 올린다 (추가만, 화면 파일 무변경)

[BL-709] 은 전략 목록의 **서버 prefetch 가 URL 정렬을 안 읽어** 정렬 링크로 진입할 때마다
클라이언트 왕복이 하나 더 드는 문제다. 기능은 옳고 **비용만** 든다.

처방의 핵심은 「화이트리스트를 두 벌로 만들지 않는 것」이다. 이 step 은 그 **1벌**을 만든다.
화면 파일(`page.tsx` · `strategy-list.tsx`)은 **한 글자도 건드리지 않는다** — 그건 step 2·3 몫이다.

## 읽어야 할 파일

- `frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx` — 특히 `SORT_OPTIONS`(`:55-64`)와
  그것으로 URL 값을 검증하는 `:77-82`. **읽기만** 한다
- `frontend/src/features/strategy/schemas.ts` `:165-173` — `StrategyListQuerySchema` 의
  `order_by` enum(`updated_at`·`name`·`total_return`·`sharpe_ratio`) 과 `order` enum(`asc`·`desc`)
- `frontend/src/features/strategy/labels.ts` — 이 도메인의 표기 SSOT 관례
- `frontend/src/features/strategy/__tests__/query-keys.test.ts` — 이 폴더의 vitest 작성 관례
- `docs/backlog.md` 의 `### BL-709` 섹션 — 원인·영향·권장 접근
- `frontend/AGENTS.md` §4(FSD Lite) · §11(TS 컨벤션)

## 작업

**새 파일 2개만 만든다.** 기존 파일 수정 0.

1. `frontend/src/features/strategy/sort.ts`
   - `export const STRATEGY_SORT_OPTIONS` — `strategy-list.tsx:55-64` 의 4항목(id·order·label)을
     **값 그대로** 옮긴다. 라벨 문자열을 바꾸지 마라(화면 회귀).
   - `export function resolveStrategySort(orderByParam, orderParam)` — **순수 함수**.
     URL 스칼라 2개(각각 `string | null | undefined`)를 받아
     `{ order_by, order }` 를 돌려준다. 타입은 `StrategyListQuery` 의 필드 타입에서 파생한다
     (새로 손으로 적지 마라 — `NonNullable<StrategyListQuery["order_by"]>` 관례가 `:53-54` 에 이미 있다).
   - 계약: 화이트리스트 **밖**이거나 값이 없으면 기본값 `updated_at` / `desc` 로 정규화한다.
     `order` 는 `asc` 만 `asc` 이고 나머지는 전부 `desc` 다(현재 `strategy-list.tsx:82` 의 규칙과 동일).
   - ★**서버·클라이언트 양쪽에서 import 된다.** `"use client"` 를 붙이지 말고, 브라우저 전용 API
     (`window`·`next/navigation`)를 참조하지 마라.
2. `frontend/src/features/strategy/__tests__/sort.test.ts` — **파일명 그대로**.
   최소한 아래 4가지를 덮어라: ⑴ 화이트리스트 안의 값은 그대로 통과 ⑵ 화이트리스트 밖 값
   (`"; DROP"` 같은 임의 문자열)은 기본값으로 정규화 ⑶ `null`/`undefined` 는 기본값
   ⑷ `STRATEGY_SORT_OPTIONS` 의 모든 id 가 `resolveStrategySort` 를 통과해 자기 자신으로 돌아온다.

## AC (Acceptance Criteria)

★**정본은 `phases/bl709/index.json` 의 step 1 `ac` 배열이다.** 아래는 그것과 **같은 문자열**이다.
러너가 이 커맨드를 **독립적으로 재실행**하고 하나라도 rc≠0 이면 `completed` 를 취소한다 —
자기신고만으로는 통과하지 못한다. 직접 순서대로 돌려 전건 rc=0 을 확인해라.

```bash
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm typecheck
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm lint
cd "$(git rev-parse --show-toplevel)/frontend" && test -f src/features/strategy/sort.ts && grep -q 'export const STRATEGY_SORT_OPTIONS' src/features/strategy/sort.ts && grep -q 'export function resolveStrategySort' src/features/strategy/sort.ts
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm test src/features/strategy/__tests__/sort.test.ts
cd "$(git rev-parse --show-toplevel)/frontend" && pnpm test
cd "$(git rev-parse --show-toplevel)" && test -z "$(git diff main --name-only -- frontend/src/app)"
```

> 착수 전 실측(2026-08-12): 5번째 전체 회귀는 **210 files / 1347 tests 초록**이 baseline 이고,
> `pnpm lint` 는 **에러 0 · 경고 2** 로 rc=0 이다. 이 둘이 red 면 네가 깨뜨린 것이다.

## 검증 절차

1. 위 AC 6건을 순서대로 실행해 전건 rc=0 을 확인한다.
2. `git diff main --stat` 이 `frontend/src/features/strategy/` **2파일만** 담고 있는지 눈으로 확인한다.
3. `phases/bl709/index.json` 의 step 1 을 `completed` + `summary` 에
   **① 만든 export 이름 ② 화이트리스트 밖 입력을 무엇으로 정규화했는지 ③ 테스트 건수**를 한 줄로 적는다.

## 금지사항

- `frontend/src/app/` 아래 **어떤 파일도** 고치지 마라. 이유: 6번째 AC 가 그것을 막는다.
  화면 배선은 step 2(서버)·step 3(클라이언트) 몫이고, 지금 같이 고치면 「모듈이 옳아서 초록인지
  화면을 같이 고쳐서 초록인지」를 다음 step 이 구분할 수 없다.
- `strategy-list.tsx` 의 `SORT_OPTIONS` 를 **지우지 마라**. 이유: 이 step 이 끝난 시점에는
  일부러 2벌이다. 1벌로 합치는 것은 step 3 이고, 그 step 의 AC 가 「정의 1곳」을 잰다.
- 라벨 문자열·정렬 기본값을 「개선」하지 마라. 이유: BL-709 는 성능 결함이고 표기 변경이 아니다.
  화면 문자열이 바뀌면 e2e 캐논 기준선이 흔들린다.
- `schemas.ts` 의 enum 을 바꾸지 마라. 이유: BE 계약이다. 화이트리스트는 그 enum 의 **부분집합**이어야 한다.
- 새 스크립트·설정 파일을 만들지 마라. 이유: 이 step 의 산출물은 파일 2개다.
