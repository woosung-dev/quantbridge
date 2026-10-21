export const pythonStrategyKeys = {
  all: (userId: string) => ["python-strategies", userId] as const,
  capabilities: (userId: string) => [...pythonStrategyKeys.all(userId), "capabilities"] as const,
  list: (userId: string) => [...pythonStrategyKeys.all(userId), "list"] as const,
  runs: (userId: string, id: string) => [...pythonStrategyKeys.all(userId), "runs", id] as const,
  run: (userId: string, id: string) => [...pythonStrategyKeys.all(userId), "run", id] as const,
};
