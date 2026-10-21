import type { PythonRun, PythonStrategy } from "../schemas";

export const STRATEGY: PythonStrategy = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "이동평균 실험",
  source: 'def on_bar(ctx, state):\n    return {"action": "hold"}',
  params: { period: 20 },
  warmup_bars: 100,
  version_id: "22222222-2222-4222-8222-222222222222",
  source_hash: "a".repeat(64),
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
};
export function makeRun(overrides: Partial<PythonRun> = {}): PythonRun {
  return {
    id: "33333333-3333-4333-8333-333333333333",
    strategy_id: STRATEGY.id,
    version_id: STRATEGY.version_id,
    status: "running",
    request: {
      symbol: "BTC/USDT",
      timeframe: "4h",
      period_start: "2026-01-01T00:00:00Z",
      period_end: "2026-07-01T00:00:00Z",
      initial_capital: "10000",
      fees: "0.00055",
      slippage: "0.00014",
    },
    result: null,
    error: null,
    created_at: "2026-10-21T00:00:00Z",
    completed_at: null,
    ...overrides,
  };
}
