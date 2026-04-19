// Sprint FE-04: Backtest query key factory.
// LESSON-005: userId 첫 인자 identity — Clerk JWT 교체 시 cache 격리.
// 호출부는 `useAuth().userId ?? "anon"` 를 맨 앞 인자로 넘긴다.

export interface BacktestListQuery {
  limit: number;
  offset: number;
}

export interface BacktestTradesQuery {
  limit: number;
  offset: number;
}

export const backtestKeys = {
  all: (userId: string) => ["backtests", userId] as const,
  lists: (userId: string) => [...backtestKeys.all(userId), "list"] as const,
  list: (userId: string, query: BacktestListQuery) =>
    [...backtestKeys.lists(userId), query] as const,
  details: (userId: string) => [...backtestKeys.all(userId), "detail"] as const,
  detail: (userId: string, id: string) =>
    [...backtestKeys.details(userId), id] as const,
  progress: (userId: string, id: string) =>
    [...backtestKeys.all(userId), "progress", id] as const,
  trades: (userId: string, id: string, query: BacktestTradesQuery) =>
    [...backtestKeys.all(userId), "trades", id, query] as const,
};
