// Optimizer React Query key factory — LESSON-005 userId 첫 인자 identity.

export interface OptimizationRunListQuery {
  limit: number;
  offset: number;
  backtest_id?: string;
}

export const optimizerKeys = {
  all: (userId: string) => ["optimizer", userId] as const,
  lists: (userId: string) => [...optimizerKeys.all(userId), "list"] as const,
  list: (userId: string, query: OptimizationRunListQuery) =>
    [...optimizerKeys.lists(userId), query] as const,
  details: (userId: string) => [...optimizerKeys.all(userId), "detail"] as const,
  detail: (userId: string, id: string) =>
    [...optimizerKeys.details(userId), id] as const,
};
