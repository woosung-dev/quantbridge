import { DEFAULT_FEES_PCT, DEFAULT_SLIPPAGE_PCT } from "@/features/backtest/cost-defaults";
import type { PythonBacktestDraft, PythonStrategy, PythonStrategyDraft } from "./schemas";

// 연구 성과로 제시하지 않는 실행 계약 확인용 단순 이동평균 예제다.
const SAMPLE_SOURCE = `def on_bar(ctx, state):
    period = int(ctx["params"].get("period", 20))
    history = ctx["history"]
    if len(history) < period + 1:
        return {"action": "hold"}
    closes = [float(bar["close"]) for bar in history[-period:]]
    average = sum(closes) / period
    close = float(ctx["bar"]["close"])
    direction = ctx["position"]["direction"]
    if close > average and direction != "long":
        return {"action": "long"}
    if close < average and direction == "long":
        return {"action": "close"}
    return {"action": "hold"}
`;

export function strategyDraft(strategy: PythonStrategy | null): PythonStrategyDraft {
  return strategy
    ? {
        name: strategy.name,
        source: strategy.source,
        params_json: JSON.stringify(strategy.params, null, 2),
        warmup_bars: strategy.warmup_bars,
      }
    : {
        name: "이동평균 예제",
        source: SAMPLE_SOURCE,
        params_json: '{"period": 20}',
        warmup_bars: 100,
      };
}

export function backtestDraft(now = new Date()): PythonBacktestDraft {
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const start = new Date(end);
  start.setUTCMonth(start.getUTCMonth() - 6);
  return {
    symbol: "BTC/USDT",
    timeframe: "4h",
    period_start: start.toISOString().slice(0, 10),
    period_end: end.toISOString().slice(0, 10),
    initial_capital: "10000",
    fees: String(DEFAULT_FEES_PCT),
    slippage: String(DEFAULT_SLIPPAGE_PCT),
  };
}
