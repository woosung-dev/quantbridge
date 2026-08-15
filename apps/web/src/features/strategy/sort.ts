// 전략 목록 URL 정렬 옵션과 정규화를 담당하는 서버·클라이언트 공용 순수 모듈.
import type { StrategyListQuery } from "./schemas";

type StrategyOrderBy = NonNullable<StrategyListQuery["order_by"]>;
type StrategyOrder = NonNullable<StrategyListQuery["order"]>;

export const STRATEGY_SORT_OPTIONS = [
  { id: "updated_at", order: "desc", label: "마지막 수정 순" },
  { id: "total_return", order: "desc", label: "수익률 높은 순" },
  { id: "sharpe_ratio", order: "desc", label: "샤프 높은 순" },
  { id: "name", order: "asc", label: "이름 순" },
] as const satisfies ReadonlyArray<{
  id: StrategyOrderBy;
  order: StrategyOrder;
  label: string;
}>;

export function resolveStrategySort(
  orderByParam: string | null | undefined,
  _orderParam: string | null | undefined,
): { order_by: StrategyOrderBy; order: StrategyOrder } {
  const { id: orderBy, order } =
    STRATEGY_SORT_OPTIONS.find(({ id }) => id === orderByParam) ?? STRATEGY_SORT_OPTIONS[0];

  return { order_by: orderBy, order };
}
