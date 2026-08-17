// 백테스트 목록 URL 정렬 정규화 + 목록 쿼리 생성 — 서버·클라이언트 공용 순수 모듈.
//
// ★[BL-786] 이 모듈이 생긴 이유. 종전에는 페이지(Server Component)가 SSR prefetch 를
//   `{limit, offset}` 로 키잉하고, `BacktestList` 는 `{limit, offset, order_by, order}` 로
//   키잉했다. 두 키가 달라 **hydrate 된 캐시를 클라이언트가 한 번도 쓰지 못했고**, 같은 목록이
//   SSR 에서 한 번 · 브라우저에서 한 번, 한 화면 로드에 BE 를 두 번 쳤다.
//   `features/strategy/sort.ts` 가 이미 쓰던 「양쪽이 같은 순수 함수를 부른다」 관례를 그대로 따른다.
import type { BacktestListQuery } from "./query-keys";

export type BacktestOrderBy = NonNullable<BacktestListQuery["order_by"]>;
export type BacktestOrder = NonNullable<BacktestListQuery["order"]>;

export const BACKTEST_PAGE_SIZE = 20;

export const BACKTEST_ORDER_BY: readonly BacktestOrderBy[] = [
  "created_at",
  "total_return",
  "max_drawdown",
  "sharpe_ratio",
  "num_trades",
];

export function resolveBacktestSort(
  orderByParam: string | null | undefined,
  orderParam: string | null | undefined,
): { order_by: BacktestOrderBy; order: BacktestOrder } {
  const order_by: BacktestOrderBy = BACKTEST_ORDER_BY.some((column) => column === orderByParam)
    ? (orderByParam as BacktestOrderBy)
    : "created_at";
  return { order_by, order: orderParam === "asc" ? "asc" : "desc" };
}

/**
 * 목록 queryKey 와 요청 파라미터의 **유일한** 생성자.
 *
 * ★키를 두 곳에서 각자 조립하지 않는 것이 요점이다 — 한쪽만 필드를 늘리면 캐시가 조용히
 * 어긋나고, 증상은 「요청이 두 번 나간다」로만 보인다([BL-786]).
 */
export function buildBacktestListQuery(
  orderByParam: string | null | undefined,
  orderParam: string | null | undefined,
): BacktestListQuery {
  return {
    limit: BACKTEST_PAGE_SIZE,
    offset: 0,
    ...resolveBacktestSort(orderByParam, orderParam),
  };
}
